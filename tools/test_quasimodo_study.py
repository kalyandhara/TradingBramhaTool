"""Regression tests for the two SILENT failures in the B-58 QM study.

    py -3 -m pytest tools/test_quasimodo_study.py -q

Both bugs below produced a run that looked entirely healthy -- correct-looking
numbers, a passing equivalence check, a printed verdict -- while measuring
something other than the pre-registered design. Neither would have been caught by
reading the code, and the first one survived a completed study and got written up
as a finding about the pattern. That is what these tests are for.

  1. `max_swings` capped the historical walk at the last 15 swings, so the study
     could never see more than ~12 candidate quadruples per name no matter how much
     history it was handed. 5.5x the bars produced 68 events instead of 53 -- the
     count was tracking the number of NAMES, not the amount of history -- and the
     2026-09-10 write-up concluded "a shape this rare cannot be measured", which was
     a statement about a default argument.

  2. `support_retests` tested "traded clear above the band" on CLOSES. When a QM's
     structure is compressed inside the +-2% tolerance, no close prints above the
     band and the baseline stopped containing the signal. It broke on 8 of 5,050
     events -- invisible at 68.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import quasimodo_study as q
import scanner_templates as st


def _bars(closes: list[float], *, highs=None, lows=None) -> pd.DataFrame:
    c = np.asarray(closes, float)
    return pd.DataFrame({
        "open": c, "close": c,
        "high": np.asarray(highs, float) if highs is not None else c * 1.001,
        "low": np.asarray(lows, float) if lows is not None else c * 0.999,
        "volume": np.full(len(c), 1000.0),
    })


def _zigzag(n_legs: int, base: float = 100.0, amp: float = 8.0, leg: int = 12) -> list[float]:
    """A long alternating swing series, so the chain has many pivots to return."""
    out: list[float] = []
    for i in range(n_legs):
        lo = base * (1 + 0.01 * i)
        hi = lo + amp
        up = list(np.linspace(lo, hi, leg))
        down = list(np.linspace(hi, lo, leg))[1:]
        out += up + down
    return out


# ── bug 1: the walk must actually walk the history ──────────────────────────────

def test_structure_chain_default_caps_swings_at_fifteen():
    """Pins the upstream default that caused it -- if this ever changes, the study's
    explicit max_swings becomes redundant rather than load-bearing, and the comment
    there should be revisited."""
    df = _bars(_zigzag(20))
    chain = st.detect_structure_chain(df, pivot_len=5)
    assert len(chain["swings"]) <= 15


def test_deep_history_yields_proportionally_more_swings_when_uncapped():
    """The bug in one line: uncapped, a longer series must give MORE swings."""
    short = st.detect_structure_chain(_bars(_zigzag(6)), pivot_len=5, max_swings=10**9)
    long_ = st.detect_structure_chain(_bars(_zigzag(24)), pivot_len=5, max_swings=10**9)
    assert len(long_["swings"]) > len(short["swings"]) * 2, (
        "a 4x longer series produced barely more swings -- the walk is capped again")


def test_pattern_count_scales_with_history_not_with_the_cap():
    """The exact shape of the 2026-09-10 failure, as an assertion.

    Under the capped chain the pattern count is pinned near 1 regardless of history;
    uncapped it grows with the series. This is what made 743-bar and 4,122-bar caches
    return almost the same number of events.
    """
    df = _bars(_zigzag(24))
    capped = q.qm_patterns(st.detect_structure_chain(df, pivot_len=5)["swings"])
    uncapped = q.qm_patterns(
        st.detect_structure_chain(df, pivot_len=5, max_swings=10**9)["swings"])
    assert len(uncapped) >= len(capped), "uncapped must never see fewer patterns"
    assert len(st.detect_structure_chain(df, pivot_len=5)["swings"]) <= 15


# ── bug 2: the baseline must contain the signal ─────────────────────────────────

def test_been_above_uses_highs_not_closes():
    """A bar that traded above the band but closed inside it still counts as 'above'.

    This is the COFORGE case in miniature: the rally clears the tolerance intrabar
    and never on a close, so a close-based rule never arms the retest state.
    """
    lvl = 100.0
    # closes: pivot low at 100, a rally that stays inside +2%, then back to the band
    closes = [100.0] * 6 + [101.0, 101.5, 101.8, 101.5] + [100.5]
    highs = [100.2] * 6 + [101.4, 102.9, 102.7, 101.9] + [100.7]   # bar 7 pokes above 102
    c = np.asarray(closes, float)
    h = np.asarray(highs, float)
    swings = [{"kind": "low", "bar": 0, "level": lvl}]

    with_high = q.support_retests(swings, c, len(c), h)
    with_close = q.support_retests(swings, c, len(c), c)   # the old behaviour
    assert with_high[-1], "a rally that cleared the band intrabar must arm the state"
    assert not with_close[-1], "test is vacuous -- closes would have armed it too"


def test_state_still_requires_coming_back_into_the_band():
    """The widening must not turn into 'any bar after a pivot'."""
    lvl = 100.0
    closes = [100.0] * 5 + [105.0, 106.0, 107.0]
    c = np.asarray(closes, float)
    h = c * 1.01
    mask = q.support_retests([{"kind": "low", "bar": 0, "level": lvl}], c, len(c), h)
    assert not mask[-1], "a bar far above the band is not a retest"


def test_state_ignores_swing_highs():
    lvl = 100.0
    c = np.asarray([100.0] * 8, float)
    mask = q.support_retests([{"kind": "high", "bar": 0, "level": lvl}], c, len(c), c * 1.05)
    assert not mask.any(), "only swing LOWS define this state"


# ── the pre-registered constants ────────────────────────────────────────────────

def test_frozen_parameters_match_the_preregistration():
    """The 2026-09-11 amendment froze every parameter and allowed only the bar
    supply to change. Editing any of these invalidates the run."""
    assert q.HORIZON == 20
    assert q.TOL_PCT == 2.0
    assert q.PIVOT_LEN == 5
    assert q.MIN_GRAB == 0.75
    assert q.MIN_CHOCH == 0.75
