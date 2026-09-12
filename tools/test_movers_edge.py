"""test_movers_edge.py — the study's honesty-critical mechanics.

Not a test of the RESULT (a measurement is not a unit test). These pin the three
things that would silently turn a null into a false positive:

  1. no look-ahead — the rank uses day t, the trade starts at t+1's open;
  2. the baseline is the same day's own universe, not a drifting benchmark;
  3. a planted effect is actually detected, so a null cannot be an artefact of a
     study that can't see anything.

(3) is the one most often skipped, and it is the one that makes the null
believable: a test harness that reports "no edge" on data engineered to contain
a large edge is measuring its own plumbing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import movers_edge as me


def _bars(n_days: int = 40, n_syms: int = 40, seed: int = 0,
          loser_bump: float = 0.0) -> pd.DataFrame:
    """Synthetic universe. `loser_bump` adds a forward drift to whichever names
    fell most on the previous day — a planted, known effect."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n_days)
    syms = [f"S{i:03d}" for i in range(n_syms)]
    px = {s: 100.0 for s in syms}
    rows = []
    prev_ret = {s: 0.0 for s in syms}
    for d in dates:
        rets = {s: float(rng.normal(0, 0.02)) for s in syms}
        if loser_bump:
            worst = sorted(prev_ret, key=prev_ret.get)[:5]
            for s in worst:
                rets[s] += loser_bump
        for s in syms:
            o = px[s]
            px[s] = o * (1 + rets[s])
            rows.append({"date": d, "symbol": s, "open": o, "close": px[s],
                         "volume": 1e7})
        prev_ret = rets
    return pd.DataFrame(rows)


# ── look-ahead ───────────────────────────────────────────────────────────────

def test_forward_return_starts_at_the_next_open():
    """Hand-checked arithmetic on one name, so the convention is pinned to a
    number rather than to itself."""
    bars = pd.DataFrame({
        "date": pd.bdate_range("2024-01-01", periods=4).repeat(2),
        "symbol": ["A", "B"] * 4,
        "open":  [100, 50, 90, 50, 95, 50, 99, 50],
        "close": [100, 50, 88, 50, 99, 50, 99, 50],
        "volume": [1e9] * 8,
    })
    panel = me.build_panel(bars, top_n=1, universe_n=2,
                           min_turnover=0.0, horizons=(1,))
    losers = panel[panel["leg"] == "losers"]
    assert not losers.empty
    # Day 2: A fell 100→88, so A is the loser. Entry at day 3's open (95),
    # exit at day 3's close (99) for h=1 → +4.21%.
    row = losers.iloc[0]
    assert row["sig_1"] == pytest.approx((99 / 95 - 1) * 100, abs=0.01)


def test_last_day_is_not_scored():
    """There is no next open on the final bar; a study that scored it would be
    reading a NaN as a zero."""
    bars = _bars(n_days=12, n_syms=20)
    panel = me.build_panel(bars, top_n=3, universe_n=10,
                           min_turnover=0.0, horizons=(1,))
    assert panel["date"].max() < bars["date"].max()


# ── the baseline ─────────────────────────────────────────────────────────────

def test_universe_mean_is_the_same_days_own_cross_section():
    bars = _bars(n_days=30, n_syms=30, seed=3)
    panel = me.build_panel(bars, top_n=5, universe_n=20,
                           min_turnover=0.0, horizons=(5,))
    # The two legs of one day share a universe: same day, same control.
    for _, day in panel.groupby("date"):
        if len(day) == 2:
            assert day["uni_5"].nunique() == 1


def test_a_flat_universe_has_zero_spread():
    """Every name identical → the losers ARE the universe → spread must be 0,
    not a small number from an off-by-one."""
    dates = pd.bdate_range("2024-01-01", periods=20)
    rows = [{"date": d, "symbol": s, "open": 100.0, "close": 100.0,
             "volume": 1e7} for d in dates for s in [f"S{i}" for i in range(10)]]
    panel = me.build_panel(pd.DataFrame(rows), top_n=3, universe_n=10,
                           min_turnover=0.0, horizons=(1,))
    if not panel.empty:
        assert (panel["sig_1"] - panel["uni_1"]).abs().max() == pytest.approx(0, abs=1e-9)


# ── can the study see an effect at all? ──────────────────────────────────────

def test_a_planted_edge_is_detected():
    """The control for the null. A +1%/day drift planted on the losers must show
    up as a large positive spread — otherwise 'no edge' means 'no detector'."""
    # universe_n covers every name, so the planted set and the ranked loser set
    # coincide exactly. With a narrower universe some bumped names fall outside
    # it and the measured spread dilutes — real, but it would make this test
    # about the fixture rather than about the detector.
    bars = _bars(n_days=200, n_syms=40, seed=7, loser_bump=0.01)
    panel = me.build_panel(bars, top_n=5, universe_n=40,
                           min_turnover=0.0, horizons=(1,))
    res = me.score(panel, "losers", horizons=(1,))
    # ~1% plant, less the 5/40 of it that leaks into the universe mean.
    assert res["horizons"][1]["spread_pct"] > 0.5
    assert res["horizons"][1]["rot_p"] is not None


def test_no_planted_edge_gives_a_small_spread():
    bars = _bars(n_days=200, n_syms=40, seed=7, loser_bump=0.0)
    panel = me.build_panel(bars, top_n=5, universe_n=40,
                           min_turnover=0.0, horizons=(1,))
    res = me.score(panel, "losers", horizons=(1,))
    assert abs(res["horizons"][1]["spread_pct"]) < 0.5


# ── the decision rule is mechanical ──────────────────────────────────────────

def test_verdict_is_underpowered_below_the_floor():
    res = {"n_days": me.MIN_EVENT_DAYS - 1, "horizons": {5: {"spread_pct": 9.0,
                                                             "rot_p": 0.001}}}
    assert me.verdict(res).startswith("UNDERPOWERED")


def test_verdict_null_when_p_is_not_significant():
    res = {"n_days": 999, "horizons": {5: {"spread_pct": 0.4, "rot_p": 0.3}}}
    assert me.verdict(res).startswith("NULL")


def test_verdict_fail_on_a_significant_negative_spread():
    res = {"n_days": 999, "horizons": {5: {"spread_pct": -0.4, "rot_p": 0.01}}}
    assert me.verdict(res).startswith("FAIL")


def test_verdict_pass_on_a_significant_positive_spread():
    res = {"n_days": 999, "horizons": {5: {"spread_pct": 0.4, "rot_p": 0.01}}}
    assert me.verdict(res).startswith("PASS")


# ── costs ────────────────────────────────────────────────────────────────────

def test_cost_is_reported_and_cancels_in_the_spread():
    """The claim the CLI prints. Both legs pay it, so it cannot manufacture or
    hide a spread — only move the absolute return."""
    bars = _bars(n_days=60, n_syms=30, seed=11)
    panel = me.build_panel(bars, top_n=5, universe_n=20,
                           min_turnover=0.0, horizons=(5,))
    gross = me.score(panel, "losers", horizons=(5,), cost_model=me.bt.COST_GROSS)
    net = me.score(panel, "losers", horizons=(5,), cost_model=me.bt.COST_INDIAN)
    assert gross["cost_pct"] == 0
    assert net["cost_pct"] > 0
    assert gross["horizons"][5]["spread_pct"] == net["horizons"][5]["spread_pct"]
    assert net["horizons"][5]["leg_net_pct"] < gross["horizons"][5]["leg_net_pct"]
