"""Tests for the CVD data probe — B-48.

The probe's own numbers live in `analyses/CVD-Data-Probe`. What is pinned here
is the machinery that produced them, and in particular the three ways a probe
like this flatters itself:

  * a symbol with NO VOLUME (an index quote) agrees with itself trivially on
    every session — it contributed 87 free sessions of 100% to the first run;
  * the two proxies are not interchangeable, and a test that only ever exercised
    one would never say so;
  * the pass bar is pre-committed, so `verdict()` must apply it mechanically
    rather than by judgement.
"""
import numpy as np
import pandas as pd
import pytest

import cvd_data_probe as cvd


def _bars(rows, start="2026-01-01 09:15", freq="5min"):
    """rows = [(open, high, low, close, volume)]"""
    a = np.asarray(rows, dtype=float)
    idx = pd.date_range(start, periods=len(a), freq=freq)
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1], "low": a[:, 2],
                         "close": a[:, 3], "volume": a[:, 4]}, index=idx)


# ── the proxies ───────────────────────────────────────────────────────────────
def test_the_sign_proxy_follows_the_bar_direction():
    df = _bars([(100, 101, 99, 101, 1000),      # up
                (101, 102, 100, 100, 500)])     # down
    assert cvd.signed_volume(df, "sign").tolist() == [1000.0, -500.0]


def test_a_doji_signs_nothing_under_the_sign_proxy():
    df = _bars([(100, 101, 99, 100, 1000)])
    assert cvd.signed_volume(df, "sign").tolist() == [0.0]


def test_the_range_proxy_reads_where_the_close_sits():
    """Close at the high is all buying, at the low all selling, mid is zero —
    which is a different claim from 'the bar was up', and that is the point."""
    df = _bars([(100, 102, 100, 102, 1000),     # closes at the high
                (100, 102, 100, 100, 1000),     # closes at the low
                (100, 102, 100, 101, 1000)])    # closes mid
    out = cvd.signed_volume(df, "range").tolist()
    assert out[0] == pytest.approx(1000.0)
    assert out[1] == pytest.approx(-1000.0)
    assert out[2] == pytest.approx(0.0)


def test_the_two_proxies_disagree_on_a_bar_that_rose_and_faded():
    """An up bar that closed near its low: 'sign' calls it buying, 'range' calls
    it selling. Neither is order flow, and the choice between them is a decision
    every package that ships 'CVD' makes silently."""
    df = _bars([(100, 106, 99, 100.5, 1000)])
    assert cvd.signed_volume(df, "sign").iloc[0] > 0
    assert cvd.signed_volume(df, "range").iloc[0] < 0


def test_a_zero_range_bar_does_not_divide_by_zero():
    df = _bars([(100, 100, 100, 100, 1000)])
    assert cvd.signed_volume(df, "range").tolist() == [0.0]


def test_an_unknown_proxy_is_refused():
    with pytest.raises(ValueError):
        cvd.signed_volume(_bars([(1, 1, 1, 1, 1)]), "vwap-ish")


# ── sessions ──────────────────────────────────────────────────────────────────
def test_session_cvd_sums_within_the_day_not_across_it():
    df = pd.concat([_bars([(100, 101, 99, 101, 1000)], start="2026-01-01 09:15"),
                    _bars([(100, 101, 99, 99, 400)], start="2026-01-02 09:15")])
    out = cvd.session_cvd(df, "sign")
    assert len(out) == 2 and out.tolist() == [1000.0, -400.0]


# ── the trap the first run walked into ────────────────────────────────────────
def test_a_volumeless_series_is_not_evidence():
    """`^NSEI` has no volume, so every delta is zero and every session 'agrees'.
    The first run counted 87 such sessions as 100% agreement and lifted the
    pooled number by four points."""
    flat = _bars([(100, 101, 99, 101, 0), (101, 102, 100, 100, 0)])
    assert cvd.has_volume(flat) is False
    assert cvd.has_volume(_bars([(100, 101, 99, 101, 5)])) is True


def test_the_volumeless_symbol_is_excluded_and_named():
    def read(sym, interval):
        return (_bars([(100, 101, 99, 101, 0)] * 10) if sym == "INDEX"
                else _bars([(100, 101, 99, 101, 100)] * 10))
    res = cvd.run(["INDEX", "REAL"], read)
    assert res["no_volume"] == ["INDEX"]
    assert "INDEX" not in res["per_symbol"]


# ── the pre-committed bar ─────────────────────────────────────────────────────
def _res(agree, corr):
    return {"proxies": {"sign": {"sign_agreement": agree, "correlation": corr,
                                 "n_symbol_sessions": 400}}}


def test_the_verdict_applies_the_written_thresholds():
    assert cvd.verdict(_res(0.95, 0.95)).startswith("PASS")
    assert cvd.verdict(_res(0.89, 0.95)).startswith("FAIL")   # agreement short
    assert cvd.verdict(_res(0.95, 0.89)).startswith("FAIL")   # correlation short


def test_the_thresholds_are_the_ones_the_write_up_quotes():
    assert cvd.MIN_SIGN_AGREEMENT == 0.90
    assert cvd.MIN_CORRELATION == 0.90


def test_an_empty_probe_is_incomplete_not_a_pass():
    assert cvd.verdict({"proxies": {}}).startswith("INCOMPLETE")


def test_too_few_shared_sessions_reports_none_rather_than_a_number():
    fine = _bars([(100, 101, 99, 101, 100)] * 3)
    assert cvd.compare(fine, fine, "sign")["sign_agreement"] is None
