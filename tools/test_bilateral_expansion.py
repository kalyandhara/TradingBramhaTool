"""Tests for the bilateral expansion study — B-101/B-102.

The study's own numbers are not asserted here; they are whatever the walk found
and they live in `cache/bilateral_expansion/result.json` and the backlog. What is
pinned is the MACHINERY that produced them, because a pre-registered test is only
worth the fidelity of the code applying it:

  * the event is DETECTION, not every bar a coil happens to be present on — a
    per-bar count would inflate n by the length of the coil and make a null look
    powered;
  * `verdict()` applies the pre-registered bar mechanically, including the
    INCONCLUSIVE floor that stops an underpowered run being written up as a null;
  * resolution is FIRST TOUCH, not the sign of the forward move — otherwise
    claim C quietly becomes a momentum test.
"""
import numpy as np
import pandas as pd
import pytest

import bilateral_expansion_study as bx


def _frame(rows):
    a = np.asarray(rows, dtype=float)
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1],
                         "low": a[:, 2], "close": a[:, 3],
                         "volume": np.full(len(a), 1e6)})


def _flat(n, px):
    return [(px, px * 1.002, px * 0.998, px)] * n


# ── the event is detection, not presence ──────────────────────────────────────
def _fake_scan(hit_bars):
    """A scanner stub that fires on a known set of evaluation lengths."""
    def scan(sub):
        return ({"apex_progress_pct": 60.0, "up_entry": 110.0, "down_entry": 90.0}
                if (len(sub) - 1) in hit_bars else None)
    return scan


def test_a_coil_present_for_many_bars_is_one_event():
    """The detector returns a hit on every bar the coil exists. Counting each of
    them would multiply n by the coil's length and make an underpowered study
    look powered — the opposite of what the INCONCLUSIVE floor is for."""
    df = _frame(_flat(400, 100.0))
    evals = list(range(bx.WARMUP, len(df) - 60 - 2, bx.STRIDE))
    scan = _fake_scan(set(evals[:8]))          # eight consecutive eval bars
    assert len(bx._events(df, scan, 60)) == 1


def test_a_second_coil_after_a_gap_is_a_second_event():
    df = _frame(_flat(400, 100.0))
    evals = list(range(bx.WARMUP, len(df) - 60 - 2, bx.STRIDE))
    scan = _fake_scan({evals[0], evals[6]})    # two, with a no-hit bar between
    assert len(bx._events(df, scan, 60)) == 2


def test_no_events_without_a_hit():
    df = _frame(_flat(400, 100.0))
    assert bx._events(df, _fake_scan(set()), 60) == []


# ── resolution is first touch ─────────────────────────────────────────────────
def test_resolution_is_the_first_line_touched():
    df = _frame(_flat(3, 100.0)
                + [(100.0, 111.0, 99.0, 110.0)]     # touches the upper line
                + [(110.0, 112.0, 85.0, 88.0)]      # and later the lower one
                + _flat(20, 88.0))
    assert bx._resolution(df, 2, 110.0, 90.0) == "up"


def test_a_coil_that_breaks_up_and_fades_still_resolved_up():
    """Scoring by the h=20 SIGN would call this a downward resolution. It is not:
    the coil broke upward and then failed, which is a different fact."""
    df = _frame(_flat(3, 100.0)
                + [(100.0, 111.0, 99.0, 110.0)]
                + _flat(20, 80.0))
    assert bx._resolution(df, 2, 110.0, 90.0) == "up"


def test_a_bar_spanning_both_lines_is_not_credited_to_either():
    """Daily bars cannot say which side was touched first. `both` is the honest
    label — the same refusal as the harness's pessimistic tie-break."""
    df = _frame(_flat(3, 100.0) + [(100.0, 112.0, 88.0, 100.0)] + _flat(20, 100.0))
    assert bx._resolution(df, 2, 110.0, 90.0) == "both"


def test_an_unresolved_coil_returns_none():
    df = _frame(_flat(30, 100.0))
    assert bx._resolution(df, 2, 110.0, 90.0) is None


# ── the pre-registered pass bar, applied mechanically ─────────────────────────
def _res(n, edges, p):
    return {"n_signals": n,
            "A": {str(h): {"edge": e, "p": p, "n": n} for h, e in zip(bx.HORIZONS, edges)},
            "B": {}, "C": {"up": 0, "down": 0, "both": 0}}


def test_an_underpowered_run_is_inconclusive_not_null():
    """The distinction this desk keeps making: NOT MEASURED is not a finding.
    A 40-signal run that happens to land near zero must not be written up as
    'no effect'."""
    v = bx.verdict(_res(40, [0.1, 0.1, 0.1, 0.1], 0.9))
    assert v.startswith("INCONCLUSIVE")


def test_a_positive_primary_needs_the_sign_to_hold_everywhere():
    """One significant horizon among four is what a fishing expedition looks
    like. The pre-registration asked for sign stability across all of them."""
    mixed = bx.verdict(_res(500, [-0.2, 0.1, 0.4, -0.3], 0.01))
    assert mixed.startswith("NULL")
    clean = bx.verdict(_res(500, [0.2, 0.3, 0.4, 0.5], 0.01))
    assert clean.startswith("POSITIVE")


def test_a_significant_negative_is_its_own_verdict():
    """The registered prior was that a coil precedes a SMALLER move. That
    outcome has to be sayable, not collapsed into 'no edge'."""
    v = bx.verdict(_res(500, [-0.2, -0.3, -0.4, -0.5], 0.001))
    assert v.startswith("NEGATIVE")


def test_an_insignificant_primary_is_null():
    v = bx.verdict(_res(500, [0.2, 0.3, 0.4, 0.5], 0.4))
    assert v.startswith("NULL")


def test_the_floor_matches_the_pre_registration():
    """200, as written in analyses/Bilateral-Expansion-Pre-Registration. If this
    number ever moves, it moves in the page first."""
    assert bx.MIN_N == 200
    assert bx.PRIMARY_H == 20
    assert bx.APEX_BAND == (0.50, 0.75)
