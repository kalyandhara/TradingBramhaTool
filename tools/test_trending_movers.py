"""test_trending_movers.py — the change BASIS of the live movers list.

Regression cover for the 2026-09-11 fix. `price_movers_realtime` measured the
day's move from the FIRST 5-minute candle of the session, which silently deleted
the overnight gap — the part of a big loser's move that matters most. On the day
it was caught, the panel's worst "top loser" was −3.22% while the real
cross-section held names at −17%, and MVELECTRO showed −3.09% against an actual
−9.72%.

The bug was invisible to every existing test because nothing asserted what the
percentage was measured AGAINST. That is what these pin down, and it is why the
gap is built explicitly into the fixture rather than left to whatever yfinance
happens to return.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trending_stocks as ts


BHAV_DAY = "2026-09-10"


def _bhav() -> pd.DataFrame:
    """Two names, both far above any turnover floor.

    GAPPER closed at 100 and reopens at 90 — a −10% gap — then drifts down to
    89. The buggy basis sees only 90 → 89 (−1.1%); the correct one sees
    100 → 89 (−11%).
    """
    df = pd.DataFrame({
        "symbol": ["GAPPER", "STEADY"],
        "close": [100.0, 200.0],          # the PREVIOUS session's close
        "prev_close": [101.0, 199.0],     # the session before that
        "turnover": [1e10, 9e9],
        "volume": [1_000_000, 900_000],
        "trade_date": [BHAV_DAY, BHAV_DAY],
    })
    df.attrs["turnover_is_qty"] = False
    return df


def _intraday(day: str) -> pd.DataFrame:
    """MultiIndex frame shaped like `yf.download(..., group_by='ticker')`."""
    idx = pd.to_datetime([f"{day} 09:20", f"{day} 09:25", f"{day} 15:25"])
    cols = pd.MultiIndex.from_product([["GAPPER.NS", "STEADY.NS"], ["Close"]])
    return pd.DataFrame(
        [[90.0, 200.5], [89.5, 200.2], [89.0, 201.0]], index=idx, columns=cols)


@pytest.fixture
def patched(monkeypatch):
    """Stub yfinance so the basis logic is tested without the network."""
    def _install(day: str):
        import yfinance as yf
        monkeypatch.setattr(yf, "download",
                            lambda *a, **k: _intraday(day), raising=False)
        monkeypatch.setattr(ts, "UNIVERSE_N", 10, raising=False)
    return _install


# ── The bug itself ───────────────────────────────────────────────────────────

def test_overnight_gap_is_included(patched):
    """The regression. −11%, not −1.1%."""
    patched("2026-09-11")                       # session AFTER the bhavcopy
    r = ts.price_movers_realtime(_bhav(), top_n=5)
    row = r["losers"].set_index("symbol").loc["GAPPER"]
    assert row["chg_pct"] == pytest.approx(-11.0, abs=0.01)
    assert row["chg"] == pytest.approx(-11.0, abs=0.01)


def test_the_gapper_outranks_the_drifter(patched):
    """The bug did not merely misprint a number, it picked the wrong NAMES —
    under the first-candle basis GAPPER reads −1.1% and STEADY +0.25%, so the
    ordering survives here but the magnitudes do not. This asserts the name that
    actually fell furthest is the one at the top of the losers list."""
    patched("2026-09-11")
    r = ts.price_movers_realtime(_bhav(), top_n=5)
    assert r["losers"].iloc[0]["symbol"] == "GAPPER"
    assert r["gainers"].iloc[0]["symbol"] == "STEADY"


def test_basis_is_prev_close_when_bhavcopy_is_the_same_session(patched):
    """If the bhavcopy already covers the intraday day, its `close` IS today —
    measuring against it would report ~0 for every name. The previous session is
    then `prev_close` (101 → 89 = −11.88%)."""
    patched(BHAV_DAY)
    r = ts.price_movers_realtime(_bhav(), top_n=5)
    row = r["losers"].set_index("symbol").loc["GAPPER"]
    assert row["chg_pct"] == pytest.approx((89.0 / 101.0 - 1) * 100, abs=0.01)


# ── What the result must disclose ────────────────────────────────────────────

def test_stale_columns_are_renamed_not_passed_through(patched):
    """Bhavcopy turnover/volume are a session old. They may be shown; they may
    not sit unlabelled next to a live price."""
    patched("2026-09-11")
    r = ts.price_movers_realtime(_bhav(), top_n=5)
    cols = set(r["losers"].columns)
    assert {"turnover_prev", "volume_prev"} <= cols
    assert not ({"turnover", "volume"} & cols)


def test_result_reports_its_basis_and_universe(patched):
    patched("2026-09-11")
    r = ts.price_movers_realtime(_bhav(), top_n=5)
    assert r["basis"] == "previous session close (bhavcopy)"
    assert r["bhav_date"] == BHAV_DAY
    assert r["universe_n"] == ts.UNIVERSE_N
    assert r["source"] == "yfinance_realtime"


def test_name_absent_from_bhavcopy_is_dropped(patched):
    """No bhavcopy row means no previous close. Such a row must not fall back to
    an intraday basis — one row measured off a different clock than the rest is
    worse than a missing row, because the table is a RANKING."""
    patched("2026-09-11")
    bhav = _bhav()
    bhav = bhav[bhav["symbol"] != "GAPPER"].copy()
    bhav.attrs["turnover_is_qty"] = False
    r = ts.price_movers_realtime(bhav, top_n=5)
    assert "GAPPER" not in set(r["losers"]["symbol"])


# ── The EOD path, which was never wrong — guard against "fixing" it too ──────

def test_eod_movers_measure_against_prev_close():
    r = ts.price_movers(_bhav(), top_n=5, min_turnover=1.0)
    row = r["losers"].set_index("symbol").loc["GAPPER"]
    assert row["chg_pct"] == pytest.approx((100.0 / 101.0 - 1) * 100, abs=0.01)
