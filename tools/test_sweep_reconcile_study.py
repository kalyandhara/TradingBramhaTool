"""Tests for the B-186a sweep reconciliation ladder (offline, synthetic bars)."""
import numpy as np
import pandas as pd
import pytest

import backtest as bt
import scanner_templates as sc
import sweep_reconcile_study as srs


def _bars(n=400, seed=3):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, n)))
    idx = pd.date_range("2022-01-03", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c,
                         "volume": 1000.0}, index=idx)


def _stub(hits):
    """A scanner that fires on the bars in `hits` (by the slice's last index)."""
    return lambda d: {"entry": None} if len(d) - 1 in hits else None


def test_harness_events_start_at_warmup_skip_min_gap_and_stop_at_last_eval():
    df = _bars(400)
    hits = {5, 210, 212, 216, 300, 337, 338, 339}
    got = srs.harness_events(df, _stub(hits), warmup=210, min_gap=5, max_h=60)
    # 5 is before warmup; 212 falls inside 210's gap; 216 is clear of it;
    # last_eval = 400 - 60 - 2 = 338, so 339 is never evaluated
    assert got == [210, 216, 300, 337]


def test_harness_events_match_the_harness_signal_count(monkeypatch):
    df = _bars(420, seed=9)
    hits = set(range(215, 350, 7)) | {351, 352, 353}
    monkeypatch.setitem(sc.SCANNERS, "Stub Sweep", {"fn": _stub(hits), "category": "Entry"})
    res = bt.backtest_scanner("Stub Sweep", ["X"], lambda s: df)
    assert len(srs.harness_events(df, _stub(hits))) == res["n_signals"]


def test_outcome_rows_are_log_excess_over_the_symbol_span_mean():
    c = np.array([100.0 * 1.01 ** i for i in range(120)])
    df = pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1.0},
                      index=pd.date_range("2024-01-01", periods=120, freq="B", tz="UTC"))
    df.loc[df.index[30], "close"] = 90.0          # one odd bar moves its own forward return
    rows = srs.outcome_rows("X", df, bars=[30], start=10, end=50)
    r20 = np.log(df["close"].iloc[50] / 90.0)
    fwd = np.log(df["close"].to_numpy()[20:] / df["close"].to_numpy()[:-20])
    assert rows[0]["x20"] == pytest.approx(r20 - fwd[10:50].mean())
    assert rows[0]["key"] == srs.KEY and rows[0]["sym"] == "X"


def test_outcome_rows_nan_when_the_horizon_runs_off_the_end():
    df = _bars(100)
    rows = srs.outcome_rows("X", df, bars=[90], start=0, end=100)   # 90+5 fits, 90+20 does not
    assert np.isnan(rows[0]["x20"]) and np.isfinite(rows[0]["x5"])


def test_step_summary_reports_change_from_previous():
    a = {"mean20": 0.005, "n_events": 10}
    b = {"mean20": -0.002, "n_events": 8}
    out = srs.with_deltas([("S1", a), ("S2", b)])
    assert out[0]["d_mean20"] is None
    assert out[1]["d_mean20"] == pytest.approx(-0.007)
