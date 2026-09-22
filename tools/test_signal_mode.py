"""Tests for `signal_mode` — B-120.

Most detectors here describe a STATE that persists, not an instant. The shared
harness counted every bar of that state as a new signal, de-duplicated only by
`min_gap`, so `scan_flag_pole` (runs of ~4 consecutive bars, longest measured 8)
had the same breakout entered four times at four different prices.

That is defensible for an EDGE question — do bars in this state outperform? —
and indefensible for a PLAN question — was the stated target reachable from the
stated entry? Three studies each wrote their own freshness rule rather than use
the harness (flag_pole_edge, bilateral_expansion, sbc_reading); this puts one in
the harness and makes every result say which it used.
"""
import numpy as np
import pandas as pd
import pytest

import backtest as bt
import scanner_templates as sc


@pytest.fixture
def run_stub():
    """A scanner that fires on a KNOWN set of bar indices, so the difference
    between the two modes is arithmetic rather than luck."""
    made = []

    def _make(fire_at, with_plan=False):
        name = f"_test_mode_stub_{len(made)}"
        made.append(name)

        def _fn(df):
            i = len(df) - 1
            if i not in fire_at:
                return None
            c = float(df["close"].iloc[-1])
            return ({"pattern_type": "s", "entry": c, "stop": c * 0.95,
                     "target": c * 1.05} if with_plan else {"pattern_type": "s"})

        sc.SCANNERS[name] = {"fn": _fn, "description": "t", "category": "Pattern"}
        return name

    try:
        yield _make
    finally:
        for n in made:
            sc.SCANNERS.pop(n, None)


def _frame(n=500, seed=3):
    rng = np.random.default_rng(seed)
    px = 100 * np.cumprod(1 + rng.normal(0.0004, 0.015, n))
    return pd.DataFrame({"open": px, "high": px * 1.01, "low": px * 0.99,
                         "close": px, "volume": np.full(n, 1e6)})


def test_a_persisting_state_is_many_signals_in_all_mode_and_one_in_fresh(run_stub):
    """THE case. One event that stays true for 8 bars: 'all' sees several
    entries at several prices, 'fresh' sees the one bar it appeared on."""
    run = set(range(300, 308))               # 8 consecutive bars
    name = run_stub(run)
    df = _frame()
    all_ = bt.backtest_scanner(name, ["A"], lambda s: df, signal_mode="all")
    fresh = bt.backtest_scanner(name, ["A"], lambda s: df, signal_mode="fresh")
    assert fresh["n_signals"] == 1
    assert all_["n_signals"] > fresh["n_signals"]


def test_two_separate_events_are_two_fresh_signals(run_stub):
    name = run_stub({300, 301, 302, 400, 401})
    df = _frame()
    fresh = bt.backtest_scanner(name, ["A"], lambda s: df, signal_mode="fresh")
    assert fresh["n_signals"] == 2


def test_fresh_mode_does_not_let_min_gap_swallow_a_new_event(run_stub):
    """`min_gap` de-duplicates in 'all' mode. In 'fresh' mode the transition
    rule already did that, and skipping ahead would DROP a genuine new break
    that happens within min_gap bars — which is the case this pins."""
    name = run_stub({300, 302})              # two events, 2 bars apart
    df = _frame()
    fresh = bt.backtest_scanner(name, ["A"], lambda s: df,
                                signal_mode="fresh", min_gap=5)
    assert fresh["n_signals"] == 2


def test_the_default_is_unchanged_so_published_numbers_are_not_redefined(run_stub):
    """Every number this desk has published came through 'all'. Flipping the
    default would silently redefine 44 verdicts instead of re-measuring them."""
    name = run_stub({300, 301, 302})
    df = _frame()
    default = bt.backtest_scanner(name, ["A"], lambda s: df)
    explicit = bt.backtest_scanner(name, ["A"], lambda s: df, signal_mode="all")
    assert default["n_signals"] == explicit["n_signals"]
    assert default["signal_mode"] == "all"


def test_the_mode_travels_with_the_result_and_into_the_report(run_stub):
    """A hit rate from 'all' and one from 'fresh' answer different questions, so
    the number must never be quoted without saying which."""
    name = run_stub({300, 301, 302, 400}, with_plan=True)
    df = _frame()
    res = bt.walk_forward_scanner(name, ["A"], lambda s: df, n_windows=2,
                                  signal_mode="fresh")
    assert res["signal_mode"] == "fresh"
    out = bt.format_walk_forward(res)
    assert "signals=fresh" in out and "counts ONCE" in out


def test_an_unknown_mode_is_refused_rather_than_silently_treated_as_all(run_stub):
    name = run_stub({300})
    with pytest.raises(ValueError):
        bt.backtest_scanner(name, ["A"], lambda s: _frame(), signal_mode="latest")
