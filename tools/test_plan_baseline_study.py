"""B-183 study script: Holm, symbol clustering, verdict rules, placebo (no network)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import plan_baseline_study as sps


def _tr(sym, d, *, exp_r=0.0, date="2024-01-01", outcome="time", p_target=0.3, p_stop=0.4):
    return {"symbol": sym, "r": exp_r + d if exp_r is not None else d, "exp_r": exp_r,
            "p_target": p_target, "p_stop": p_stop, "outcome": outcome,
            "entry_date": pd.Timestamp(date)}


def test_holm_matches_the_textbook_example():
    assert sps.holm({"a": 0.01, "b": 0.04, "c": 0.03}) == {"a": True, "b": False, "c": False}
    assert sps.holm({"a": 0.01, "b": 0.02}) == {"a": True, "b": True}


def test_stats_cluster_by_symbol():
    trades = [_tr("BIG", 1.0) for _ in range(200)] + [_tr(f"S{i}", -0.1) for i in range(40)]
    s = sps.scanner_stats(trades)
    assert s["n_symbols"] == 41 and s["n_trades"] == 240
    assert s["mean_d"] == pytest.approx((1.0 + 40 * -0.1) / 41)


def test_unbaselined_trades_are_counted_not_dropped():
    trades = [_tr("A", 0.5), _tr("B", 0.5), _tr("C", 0.5, exp_r=None)]
    s = sps.scanner_stats(trades)
    assert s["n_trades"] == 3 and s["n_unbaselined"] == 1 and s["n_symbols"] == 2


def test_thirds_follow_entry_date_order():
    trades = ([_tr("A", -1.0, date="2022-01-01")] * 3 + [_tr("A", 2.0, date="2023-01-01")] * 3
              + [_tr("A", 3.0, date="2024-01-01")] * 3)
    assert sps.scanner_stats(list(reversed(trades)))["thirds"] == [-1.0, 2.0, 3.0]


def test_secondaries():
    trades = [_tr("A", 0, outcome="target", p_target=0.5, p_stop=0.7),
              _tr("B", 0, outcome="stop", p_target=0.1, p_stop=0.2)]
    s = sps.scanner_stats(trades)
    assert s["realised_target_rate"] == 0.5 and s["mean_p_target"] == pytest.approx(0.3)
    assert s["noise_stop_share"] == 0.5


def _st(**kw):
    base = {"n_symbols": 40, "n_trades": 500, "n_unbaselined": 0, "mean_d": 0.2,
            "thirds": [0.1, 0.3, 0.1]}
    return {**base, **kw}


def test_verdict_floors_and_stability():
    assert sps.verdict(_st(n_symbols=29), True) == "THIN"
    assert sps.verdict(_st(n_trades=120, n_unbaselined=30), True) == "THIN"   # 90 baselined
    assert sps.verdict(_st(thirds=[0.1, -0.1, -0.2]), True) == "AT BASELINE"
    assert sps.verdict(_st(thirds=[0.1, 0.3, -0.1]), True) == "BEATS BASELINE"
    assert sps.verdict(_st(mean_d=-0.2, thirds=[-0.1, -0.3, 0.1]), True) == "BELOW BASELINE"
    assert sps.verdict(_st(), False) == "AT BASELINE"


def test_placebo_gate():
    assert sps.placebo_passes({"mean_d": 0.04, "p": 0.001})
    assert sps.placebo_passes({"mean_d": 0.2, "p": 0.3})
    assert not sps.placebo_passes({"mean_d": -0.08, "p": 0.01})


def test_placebo_scanner_is_registered_and_fires_every_fifth_bar():
    import scanner_templates as sc
    sps._register_placebo()
    try:
        fn = sc.SCANNERS[sps.PLACEBO]["fn"]
        rng = np.random.default_rng(0)
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 60)))
        df = pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c,
                           "volume": 1e6})
        hits = [n for n in range(30, 61) if fn(df.iloc[:n]) is not None]
        assert hits == [n for n in range(30, 61) if n % 5 == 0]
        h = fn(df.iloc[:50])
        atr = float(sc._atr_series(df.iloc[:50], 14).iloc[-1])
        assert h["stop"] == pytest.approx(h["entry"] - atr)
        assert h["target"] == pytest.approx(h["entry"] + 2 * atr) and h["time_stop"] == 10
    finally:
        sc.SCANNERS.pop(sps.PLACEBO, None)


def test_harness_frame_matches_the_harness():
    df = pd.DataFrame({"open": [1.0, 2, 3], "high": [1.0, np.nan, 3], "low": [1.0, 2, 3],
                       "close": [1.0, 2, 3], "volume": [1.0, 1, 1]},
                      index=pd.bdate_range("2024-01-01", periods=3))
    f = sps._harness_frame(df)
    assert list(f["close"]) == [1.0, 3.0] and list(f.index) == [0, 1]


def test_never_plan_scanners_are_skipped_by_the_census():
    census = {"scanners": {"A": {"fired": 10, "with_plan": 0}, "B": {"fired": 10, "with_plan": 4},
                           "C": {"fired": 0, "with_plan": 0}}}
    assert sps.planning_scanners(["A", "B", "C", "_x"], census) == ["B", "C"]


# ── B-183c: winsorized d, strict gate, placebo-noise label ───────────────────

def test_d_cap_clips_each_trade_before_the_symbol_mean():
    trades = [_tr("A", 40.0), _tr("A", 1.0), _tr("B", -25.0)]
    raw = sps.scanner_stats(trades)
    cap = sps.scanner_stats(trades, d_cap=3.0)
    assert raw["mean_d"] == pytest.approx(((40 + 1) / 2 + -25) / 2)
    assert cap["mean_d"] == pytest.approx(((3 + 1) / 2 + -3) / 2)
    assert cap["thirds"] == [3.0, 1.0, -3.0]


def test_strict_gate_has_no_p_escape():
    assert sps.placebo_passes({"mean_d": 0.31, "p": 0.24})                 # the old rule
    assert not sps.placebo_passes_strict({"mean_d": 0.31, "p": 0.24})
    assert sps.placebo_passes_strict({"mean_d": -0.04, "p": 0.0001})
    assert not sps.placebo_passes_strict({"mean_d": None, "p": 0.9})


def test_within_placebo_noise():
    assert sps.within_placebo_noise({"mean_d": 0.07}, {"mean_d": 0.04})       # 0.07 <= 0.08
    assert not sps.within_placebo_noise({"mean_d": 0.18}, {"mean_d": 0.04})
    assert not sps.within_placebo_noise({"mean_d": -0.20}, {"mean_d": -0.04})
