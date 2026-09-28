"""Tests for B-19r(VCP)'s pre-registered bands — written BEFORE the run.

These pin the verdict function against synthetic inputs, which is the only thing
that makes a pre-registration worth anything: once the real numbers are on the
screen it is very easy to discover that the band "obviously" meant something
slightly different. A band with a test cannot be re-read after the fact.

Nothing here asserts a result for VCP Coiling. It asserts what the bands DO.
"""
from __future__ import annotations

import pytest

import vcp_remeasure as V


def _flags(*rows):
    """{20: [...], 60: [...]} from two per-window lists."""
    return {20: list(rows[0]), 60: list(rows[1])}


def _call(e20, e60, w20, w60, r20=(False, False, False), r60=(False, False, False),
          n=500):
    return V.classify({20: e20, 60: e60},
                      _flags(w20, w60),
                      _flags(r20, r60),
                      n)


# ── the floor ────────────────────────────────────────────────────────────────

def test_too_few_signals_changes_nothing():
    v, why = _call(+2.0, +3.0, (1, 1, 1), (1, 1, 1),
                   r20=(True, True, True), n=V.MIN_SIGNALS - 1)
    assert v == V.TOO_FEW
    assert str(V.MIN_SIGNALS) in why[0]


def test_the_signal_floor_is_the_pre_registered_one():
    """Pinned so it cannot be lowered to rescue a thin result."""
    assert V.MIN_SIGNALS == 100
    assert V.DECIDING == (20, 60)


# ── MEASURED needs all three conditions, not two ─────────────────────────────

def test_measured_requires_positive_stable_and_significant():
    v, _ = _call(+1.2, +2.0, (0.9, 1.1, 1.6), (1.4, 2.2, 2.4),
                 r20=(False, True, False))
    assert v == V.MEASURED


def test_positive_and_stable_but_not_significant_is_only_weak():
    """The bar is not 'looks good in three windows'."""
    v, why = _call(+1.2, +2.0, (0.9, 1.1, 1.6), (1.4, 2.2, 2.4))
    assert v == V.WEAK
    assert any("p<0.05" in w for w in why)


def test_positive_and_significant_but_unstable_is_only_weak():
    """B-19's headline was that 11 scanners showed a positive 20d edge and ALL
    were unstable. Sign consistency across windows is the thing that separates
    an edge from a window that happened to be kind."""
    v, _ = _call(+1.2, +2.0, (-0.4, 1.1, 1.6), (1.4, 2.2, 2.4),
                 r20=(True, True, True))
    assert v == V.WEAK


def test_one_positive_horizon_is_not_enough():
    v, _ = _call(+1.2, -0.3, (0.9, 1.1, 1.6), (-0.1, -0.4, -0.5),
                 r20=(True, False, False))
    assert v == V.WEAK


# ── EXCLUDE is symmetric with MEASURED ───────────────────────────────────────

def test_stable_significant_negative_is_excluded():
    """The VWAP Reclaim/Support precedent — 0.25 is not low enough for a
    detector measured significantly negative, because a weak weight still counts
    toward FULL_CONFLUENCE."""
    v, _ = _call(-0.8, -1.4, (-0.5, -0.9, -1.0), (-1.1, -1.5, -1.6),
                 r60=(True, False, False))
    assert v == V.EXCLUDE


def test_negative_but_not_significant_is_weak_not_excluded():
    """Retiring a scanner from the vote is a bigger step than demoting it, so it
    needs the significance the demotion does not."""
    v, _ = _call(-0.8, -1.4, (-0.5, -0.9, -1.0), (-1.1, -1.5, -1.6))
    assert v == V.WEAK


def test_negative_but_unstable_is_weak_not_excluded():
    v, _ = _call(-0.8, -1.4, (0.5, -0.9, -1.0), (-1.1, -1.5, -1.6),
                 r60=(True, True, True))
    assert v == V.WEAK


# ── the old reading is context, never an input ───────────────────────────────

def test_the_retired_figure_does_not_enter_the_verdict():
    """`OLD` is printed for context. If it ever reaches `classify`, the run has
    quietly become a comparison against a different population — which the
    module docstring rules out explicitly."""
    import inspect
    src = inspect.getsource(V.classify)
    assert "OLD" not in src


def test_the_retired_figure_is_recorded_as_it_was_published():
    """So a later reader can check the context line against B-19's own file."""
    assert V.OLD["signals"] == 1951
    assert V.OLD[20] == -0.59 and V.OLD[60] == -1.07


# ── the R-simulation must not be able to decide anything ─────────────────────

def test_classify_cannot_see_the_r_simulation():
    """~80% of this scanner's hits are WATCH, whose entry is a pivot that may
    never have been reached; `_simulate_plan` would book those as real trades.
    The verdict function is given no R input at all, which is the enforcement."""
    import inspect
    params = set(inspect.signature(V.classify).parameters)
    assert params == {"pooled", "per_window", "reliable", "n_signals"}


def test_each_verdict_names_the_code_change_it_implies():
    """A verdict that does not map onto a weight is an adjective."""
    import inspect
    src = inspect.getsource(V.main)
    assert "MEASURED_EDGE_SCANNERS" in src
    assert "MEASURED_WEAK_SCANNERS" in src
    assert "PIPELINE_EXCLUDED" in src
