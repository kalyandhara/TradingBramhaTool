"""Tests for the plan scoreboard in the walk-forward path — B-116.

`_aggregate` has always built an `r_block` — target_hits, stop_hits, win_rate,
avg_R — and `format_report` has always printed it. `walk_forward_scanner`
dropped it, so the B-19 batch computed target-vs-stop for 44 scanners and threw
it away 44 times; every saved verdict in `cache/b19_verdicts/` shows edges and
stability and not one R line.

The load-bearing test is the pooling one: three windows are not three equal
opinions about a hit rate.
"""
import pytest

import backtest as bt


def _block(n, target, stop, avg_r=0.0, **kw):
    return {"n_with_plan": n, "target_hits": target, "stop_hits": stop,
            "open_exits": kw.get("open_exits", 0),
            "time_exits": kw.get("time_exits", 0), "avg_R": avg_r,
            "plans_seen": kw.get("plans_seen", n),
            "plans_unsimulated": kw.get("plans_unsimulated", 0)}


def test_counts_sum_and_rates_are_recomputed_from_the_sums():
    """THE case. A 4-plan window that went 4-for-4 must not get the same say as
    a 400-plan window that went 1-in-4: averaging the rates says 50%, and the
    truth is 25.7%."""
    pooled = bt._pool_r_blocks([_block(4, 4, 0, 2.0),
                               _block(40, 10, 30, -0.5),
                               _block(400, 100, 300, -0.4)])
    assert pooled["n_with_plan"] == 444
    assert pooled["target_hits"] == 114 and pooled["stop_hits"] == 330
    assert pooled["win_rate"] == pytest.approx(0.257, abs=0.001)
    naive = (1.0 + 0.25 + 0.25) / 3
    assert abs(pooled["win_rate"] - naive) > 0.2       # and it is nowhere near


def test_avg_r_is_weighted_by_the_plans_behind_it():
    pooled = bt._pool_r_blocks([_block(1, 1, 0, 10.0), _block(99, 0, 99, -1.0)])
    assert pooled["avg_R"] == pytest.approx((10.0 - 99.0) / 100, abs=0.001)


def test_windows_with_no_plans_are_ignored_not_counted_as_zeros():
    """A window where the scanner never fired with a plan says nothing about the
    hit rate. Counting it as 0-for-0 would be fine; counting it as a loss would
    not, and neither should shift the total."""
    pooled = bt._pool_r_blocks([_block(10, 5, 5, 0.1), _block(0, 0, 0, 0.0)])
    assert pooled["n_with_plan"] == 10 and pooled["win_rate"] == 0.5


def test_no_plans_anywhere_returns_none_rather_than_a_zero_scoreboard():
    """A scanner that emits no plans must not render a 0% hit rate — that reads
    as 'it never reaches target' when the truth is 'it never states one'."""
    assert bt._pool_r_blocks([]) is None
    assert bt._pool_r_blocks([None, None]) is None


def test_unsimulatable_plans_are_carried_not_hidden():
    pooled = bt._pool_r_blocks([_block(10, 5, 5, 0.1, plans_seen=14,
                                       plans_unsimulated=4)])
    assert pooled["plans_unsimulated"] == 4 and pooled["plans_seen"] == 14


# ── the report line ───────────────────────────────────────────────────────────
def _result(plans):
    return {"scanner": "X", "n_windows": 1, "windows": [],
            "pooled": {"n_signals": 10, "horizons": {}},
            "plans": plans,
            "stability": {"per_horizon": {}, "all_stable": True, "verdict": "STABLE"},
            "degradation": {}, "cost_label": "test"}


def test_the_walk_forward_report_now_prints_target_vs_stop():
    out = bt.format_walk_forward(_result(
        {"n_with_plan": 200, "target_hits": 74, "stop_hits": 103,
         "open_exits": 13, "time_exits": 10, "target_rate": 0.37,
         "stop_rate": 0.515, "win_rate": 0.37, "avg_R": 0.36,
         "plans_seen": 200, "plans_unsimulated": 0}))
    assert "target 37.0%" in out and "stop 51.5%" in out and "+0.36R" in out


def test_a_scanner_with_no_simulatable_plan_says_so():
    out = bt.format_walk_forward(_result({"n_with_plan": 0, "plans_seen": 12}))
    assert "none simulatable" in out


def test_a_scanner_with_no_plans_at_all_prints_no_plan_line():
    out = bt.format_walk_forward(_result(None))
    assert "plan" not in out.lower().split("stability")[0].replace("plan:", "")


# ── end-to-end, because the key name was wrong and nothing said so ────────────
def test_the_plan_line_survives_a_real_walk_forward(monkeypatch):
    """The first cut read `w["r_block"]` — the name of the local variable inside
    `_aggregate`, which stores it as `r_metrics`. Every window pooled to None,
    the report printed nothing, and "no plan line" is indistinguishable from
    "this scanner has no plans". Only running the real path catches that, so
    this test runs it.
    """
    import numpy as np
    import pandas as pd
    import scanner_templates as sc

    name = "_test_plan_stub"
    # A scanner that always fires WITH a plan: entry at the close, a stop 5%
    # below and a target 5% above, so some trades hit each side.
    def _fn(df):
        c = float(df["close"].iloc[-1])
        return {"pattern_type": "stub", "entry": c,
                "stop": round(c * 0.95, 2), "target": round(c * 1.05, 2)}

    sc.SCANNERS[name] = {"fn": _fn, "description": "test", "category": "Pattern"}
    try:
        rng = np.random.default_rng(5)
        px = 100 * np.cumprod(1 + rng.normal(0.0005, 0.02, 700))
        df = pd.DataFrame({"open": px, "high": px * 1.01, "low": px * 0.99,
                           "close": px, "volume": np.full(len(px), 1e6)})
        res = bt.walk_forward_scanner(name, ["A"], lambda s_: df, n_windows=2,
                                      stride=7)
        plans = res.get("plans") or {}
        assert plans.get("n_with_plan", 0) > 0, (
            "the walk-forward result carried no plan scoreboard — check the key "
            "`_aggregate` stores it under")
        assert plans["target_hits"] + plans["stop_hits"] > 0
        assert "target" in bt.format_walk_forward(res)
    finally:
        sc.SCANNERS.pop(name, None)
