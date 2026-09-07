"""Regression tests for the yfinance-first session overlay (offline).

The overlay's whole safety property is the one thing worth pinning: yfinance
leads, but a bar that is NOT newer than the bhavcopy may never overwrite it --
the 2026-08-28 MASTEK/OAL failure, where a silently stale quote turned a 43.9x
volume day into 0.9x.
"""
import pandas as pd
import pytest

import trending_stocks as ts

BHAV_DATE = "2026-09-04"
LIVE_DATE = "2026-09-07"


def _bhav():
    return pd.DataFrame({
        "symbol": ["FRESH", "STALE", "NOHIST"],
        "close": [100.0, 50.0, 10.0],
        "prev_close": [99.0, 49.0, 9.9],
        "volume": [1000.0, 2000.0, 3000.0],
        "turnover": [1e8, 9e7, 8e7],
        "trade_date": [BHAV_DATE] * 3,
    })


def _hist(last_date, vols, closes):
    base = pd.date_range("2026-06-10", periods=len(vols) - 1, freq="B")
    idx = pd.DatetimeIndex(list(base) + [pd.Timestamp(last_date)])
    return pd.DataFrame({"Close": closes, "Volume": vols}, index=idx)


def _hists():
    return {
        "FRESH": _hist(LIVE_DATE, [1000.0] * 61 + [10000.0], [100.0] * 61 + [108.0]),
        "STALE": _hist(BHAV_DATE, [2000.0] * 62, [50.0] * 62),
    }


def test_newer_bar_overwrites_and_older_one_does_not():
    d, _ = ts.yf_session_overlay(_bhav(), ["FRESH", "STALE", "NOHIST"], hist=_hists())
    by = d.set_index("symbol")
    assert by.loc["FRESH", "src"] == "yf"
    assert by.loc["FRESH", "volume"] == 10000.0
    assert by.loc["FRESH", "trade_date"] == LIVE_DATE
    # A same-day yfinance bar is the silent-stale case: bhavcopy must survive.
    assert by.loc["STALE", "src"] == "bhav"
    assert by.loc["STALE", "volume"] == 2000.0
    # No history at all is not an error, just no overlay.
    assert by.loc["NOHIST", "src"] == "bhav"
    ov = d.attrs["overlay"]
    assert (ov["n_overlaid"], ov["n_stale"], ov["yf_date"]) == (1, 1, LIVE_DATE)


def test_no_yfinance_history_leaves_the_frame_alone():
    d, _ = ts.yf_session_overlay(_bhav(), ["FRESH"], hist={})
    assert set(d["src"]) == {"bhav"}
    assert d.attrs["overlay"]["n_overlaid"] == 0


def test_since_beats_a_mixed_trade_date_column():
    """After one pass the frame's dates are mixed; row 0 must not set the floor."""
    d, _ = ts.yf_session_overlay(_bhav(), ["FRESH"], hist=_hists())
    # d now carries LIVE_DATE on row 0. Without `since`, STALE's floor would be
    # LIVE_DATE; with it, the floor stays the real bhavcopy date.
    d2, _ = ts.yf_session_overlay(d, ["STALE"], hist=_hists(), since=BHAV_DATE)
    assert d2.attrs["overlay"]["bhav_date"] == BHAV_DATE
    assert d2.set_index("symbol").loc["FRESH", "src"] == "yf"   # not reset


def test_darvas_uses_the_live_bar_and_excludes_it_from_its_own_average():
    r = ts.darvas_volume_shockers(_bhav(), hist=_hists(), min_turnover=0, live=True)
    rows = r["rows"]
    assert list(rows["symbol"]) == ["FRESH"]
    assert rows.loc[0, "src"] == "yf"
    # SMA10 = (9 prior sessions of 1000 + today's 10000) / 10 = 1900.
    assert rows.loc[0, "sma_vol10"] == 1900
    assert rows.loc[0, "multiple"] == pytest.approx(5.3, abs=0.05)
    assert r["trade_date"] == LIVE_DATE


def test_live_false_stays_entirely_on_the_bhavcopy():
    r = ts.darvas_volume_shockers(_bhav(), hist=_hists(), min_turnover=0,
                                  live=False, move_pct=0.5)
    assert r["overlay"] == {}
    # No overlay ran, so nothing was tagged and no history was fetched: the
    # injected `hist` is the whole universe, and FRESH's stale bhavcopy volume
    # of 1000 against an SMA of 1900 is not a shocker.
    assert r["rows"].empty
