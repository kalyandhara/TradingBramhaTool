"""Tests for the two-sided harness — `_simulate_plan(side=…)` and `absolute_move`.

B-102, raised out of B-101 when the bilateral symmetrical triangle shipped with
no way to score it. The harness was long-only, and the cost of that was not a
missing feature but a SILENT one: a short-side plan returned None and landed in
`plans_unsimulated`, so a bearish scanner's R-block read as "nothing measurable"
rather than as "nobody built this". Three studies had already written their own
mirror to get around it.

The load-bearing tests here are the EQUIVALENCE ones. `order_block_rules_backtest`
and `flag_pole_edge` each carry an independent short-side simulator whose numbers
are already published in the wiki; if the new shared one disagrees with them on
the same bars, either those results move or this is wrong — and that has to be a
failing test rather than a discovery six months later. They also make folding the
copies back in a mechanical step instead of an act of faith.
"""
import numpy as np
import pandas as pd
import pytest

import backtest as bt
import flag_pole_edge as fpe
import order_block_rules_backtest as obr


def _frame(bars):
    """bars = [(open, high, low, close)]"""
    a = np.asarray(bars, dtype=float)
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1],
                         "low": a[:, 2], "close": a[:, 3],
                         "volume": np.full(len(a), 1e6)})


def _flat(n, px):
    return [(px, px * 1.002, px * 0.998, px)] * n


# ── the short side is a mirror, not a sign flip ───────────────────────────────
def test_short_target_is_hit_below_the_entry():
    """Entry 100, stop 105, target 90. A bar trading down to 89 is a WIN."""
    df = _frame(_flat(2, 100.0) + [(100.0, 101.0, 89.0, 90.0)] + _flat(5, 90.0))
    r = bt._simulate_plan(df, 2, 100.0, 105.0, 90.0, 20, side="short")
    assert r and r["outcome"] == "target" and r["r"] > 0


def test_short_stop_is_hit_above_the_entry():
    df = _frame(_flat(2, 100.0) + [(100.0, 106.0, 99.0, 105.5)] + _flat(5, 105.0))
    r = bt._simulate_plan(df, 2, 100.0, 105.0, 90.0, 20, side="short")
    assert r and r["outcome"] == "stop" and r["r"] < 0


def test_the_pessimistic_tie_break_holds_on_the_short_side_too():
    """A bar spanning both levels counts as the stop, whichever way you face.
    This is the assumption daily bars force, and a mirror that quietly dropped
    it would make every short look better than it was."""
    df = _frame(_flat(2, 100.0) + [(100.0, 106.0, 89.0, 95.0)] + _flat(5, 95.0))
    r = bt._simulate_plan(df, 2, 100.0, 105.0, 90.0, 20, side="short")
    assert r and r["outcome"] == "stop"


def test_a_long_whose_stop_sits_above_its_entry_is_refused():
    """Not a trade with a side — a typo. The caller counts it, as before."""
    df = _frame(_flat(10, 100.0))
    assert bt._simulate_plan(df, 2, 100.0, 105.0, 120.0, 20) is None


def test_a_short_whose_stop_sits_below_its_entry_is_refused():
    df = _frame(_flat(10, 100.0))
    assert bt._simulate_plan(df, 2, 100.0, 95.0, 90.0, 20, side="short") is None


def test_the_long_side_is_unchanged():
    """Every published R number in the wiki came through this path. The side
    parameter must default to the behaviour that produced them."""
    df = _frame(_flat(2, 100.0) + [(100.0, 111.0, 99.5, 110.0)] + _flat(5, 110.0))
    r = bt._simulate_plan(df, 2, 100.0, 95.0, 110.0, 20)
    explicit = bt._simulate_plan(df, 2, 100.0, 95.0, 110.0, 20, side="long")
    assert r == explicit
    assert r["outcome"] == "target" and r["r"] > 0


def test_short_r_is_not_the_long_r_negated():
    """The mirror reads different BARS, not the same walk with a minus sign. A
    frame that rallies then collapses stops a short out before the fall it would
    otherwise have been credited with."""
    df = _frame(_flat(2, 100.0)
                + [(100.0, 106.0, 99.0, 105.0)]      # stops the short out
                + [(105.0, 105.5, 85.0, 86.0)]       # the fall it never saw
                + _flat(5, 86.0))
    short = bt._simulate_plan(df, 2, 100.0, 105.0, 90.0, 20, side="short")
    assert short["outcome"] == "stop"
    assert short["bars"] == 0


# ── equivalence with the two hand-written mirrors ─────────────────────────────
def _random_frames(seed=7, n_frames=60, n_bars=40):
    rng = np.random.default_rng(seed)
    for _ in range(n_frames):
        px = 100.0 * np.cumprod(1 + rng.normal(0, 0.02, n_bars))
        hi = px * (1 + abs(rng.normal(0, 0.01, n_bars)))
        lo = px * (1 - abs(rng.normal(0, 0.01, n_bars)))
        op = px * (1 + rng.normal(0, 0.003, n_bars))
        yield _frame(list(zip(op, hi, lo, px)))


def test_matches_the_order_block_mirror_on_both_sides():
    """`order_block_rules_backtest.simulate` is an independent implementation
    whose numbers are published (B-76). Same bars, same plan, same answer — or
    one of the two is wrong."""
    cm = bt.COST_INDIAN
    for df in _random_frames():
        entry = float(df["close"].iloc[5])
        for direction, side in (("bull", "long"), ("bear", "short")):
            stop = entry * (0.97 if direction == "bull" else 1.03)
            target = entry * (1.06 if direction == "bull" else 0.94)
            mine = bt._simulate_plan(df, 6, entry, stop, target, 30,
                                     cost_model=cm, side=side)
            theirs = obr.simulate(df, 6, entry, stop, target, direction, cm,
                                  max_bars=30)
            assert (mine is None) == (theirs is None)
            if mine is None:
                continue
            assert mine["outcome"] == theirs["outcome"]
            assert mine["bars"] == theirs["bars"]
            assert mine["r"] == pytest.approx(theirs["r"], abs=1e-9)


def test_matches_the_flag_pole_mirror_on_both_sides():
    """`flag_pole_edge.walk_plan` is the other independent copy (B-92). It names
    the tail outcome `timeout` where the harness says `open`; everything that
    decides a number has to agree."""
    cm = bt.COST_INDIAN
    for df in _random_frames(seed=11):
        h = df["high"].to_numpy(float)
        l = df["low"].to_numpy(float)
        c = df["close"].to_numpy(float)
        entry = float(c[5])
        for bull, side in ((True, "long"), (False, "short")):
            stop = entry * (0.97 if bull else 1.03)
            target = entry * (1.06 if bull else 0.94)
            mine = bt._simulate_plan(df, 6, entry, stop, target, 30,
                                     cost_model=cm, side=side)
            theirs = fpe.walk_plan(h, l, c, 6, entry, stop, target, bull, cm,
                                   max_bars=30)
            assert (mine is None) == (theirs is None)
            if mine is None:
                continue
            assert mine["bars"] == theirs["bars"]
            assert mine["r"] == pytest.approx(theirs["r"], abs=1e-9)
            if theirs["outcome"] == "timeout":
                assert mine["outcome"] in ("open", "time")
            else:
                assert mine["outcome"] == theirs["outcome"]


# ── absolute move: the unit a coil is scored in ───────────────────────────────
def test_absolute_move_is_direction_free():
    """A 10% fall and a 10% rise are the same expansion. That is the whole
    point: a bilateral pattern predicts SIZE, not side."""
    # Signal on bar 2. Entry is bar 3's open (100), exit bar 6's close.
    up = _frame(_flat(4, 100.0) + _flat(5, 110.0))
    dn = _frame(_flat(4, 100.0) + _flat(5, 90.0))
    a = bt.absolute_move(up, 2, 3, cost_model=bt.COST_GROSS)
    b = bt.absolute_move(dn, 2, 3, cost_model=bt.COST_GROSS)
    assert a > 0 and b > 0
    assert a == pytest.approx(b, abs=0.25)


def test_absolute_move_pays_the_round_trip():
    """A move that does not clear costs is worth less than nothing, and the
    number has to say so — otherwise a coil that twitches 0.1% scores as a win."""
    flat = _frame(_flat(12, 100.0))
    assert bt.absolute_move(flat, 2, 5, cost_model=bt.COST_INDIAN) < 0
    assert bt.absolute_move(flat, 2, 5, cost_model=bt.COST_GROSS) == pytest.approx(0.0, abs=1e-9)


def test_absolute_move_returns_none_without_a_full_horizon():
    """No partial windows. A coil measured over four bars of a five-bar horizon
    is a different measurement, and silently shortening it is how a sample gets
    biased toward whatever the last bars did."""
    df = _frame(_flat(8, 100.0))
    assert bt.absolute_move(df, 5, 10) is None


def test_absolute_move_enters_on_the_next_open():
    """Same clock as every other signal here — never the signal bar's own close,
    which is not a price anyone could have traded on that signal."""
    df = _frame(_flat(2, 100.0) + [(100.0, 100.5, 99.5, 100.0)]
                + [(50.0, 50.5, 49.5, 55.0)] + _flat(4, 55.0))
    # Entry is the 50.0 open, exit the 55.0 close one bar later: +10%.
    assert bt.absolute_move(df, 2, 1, cost_model=bt.COST_GROSS) == pytest.approx(10.0, abs=1e-9)
