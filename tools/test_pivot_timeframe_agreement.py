"""Tests for B-97's pivot-timeframe agreement study.

    py -3 -m pytest tools/test_pivot_timeframe_agreement.py -q

What these pin is the ARITHMETIC and the pre-registered bands, not the result.
The result is a measurement and belongs in the write-up; a test that asserted
"side agreement is 53.9%" would fail the next time the market moved and would
be pinning the tape rather than the code.

The one that matters most is `test_rotation_baseline_is_the_base_rate`: the
whole point of the chance correction is that two columns with skewed label
distributions agree a lot for free, and if the baseline did not reproduce that,
the lift would be measuring nothing.
"""
from __future__ import annotations

import pandas as pd
import pytest

import pivot_timeframe_agreement as pta


# ── the side collapse ────────────────────────────────────────────────────────
@pytest.mark.parametrize("zone,expected", [
    ("R1", "ABOVE"), ("R1-PP", "ABOVE"), ("Near R1", "ABOVE"),
    ("PP-S1", "BELOW"), ("S1", "BELOW"), ("Near S1", "BELOW"),
    ("Near Pivot", "AT"),
    (None, None), ("nonsense", None),
])
def test_side_collapse(zone, expected):
    assert pta.side(zone) == expected


def test_near_pivot_is_its_own_side():
    """`Near Pivot` must not fold into ABOVE or BELOW.

    It is the one label that declines to pick a direction. Folding it either
    way would invent a direction the column deliberately withheld, and it would
    also silently change the opposite-side rate the verdict turns on.
    """
    assert pta.side("Near Pivot") not in ("ABOVE", "BELOW")


# ── the statistics ───────────────────────────────────────────────────────────
def test_perfect_agreement():
    pairs = [("R1", "R1")] * 50
    s = pta.summarise(pairs)
    assert s["zone_pct"] == 100.0
    assert s["side_pct"] == 100.0
    assert s["opposite_pct"] == 0.0


def test_opposite_counts_only_above_versus_below():
    pairs = [("R1", "S1"),          # opposite
             ("R1", "Near Pivot"),  # disagree, NOT opposite
             ("R1", "R1-PP")]       # same side
    s = pta.summarise(pairs)
    assert s["opposite_pct"] == pytest.approx(100.0 / 3)
    assert s["side_pct"] == pytest.approx(100.0 / 3)


def test_rotation_baseline_is_the_base_rate():
    """A skewed column agrees with itself by chance, and the baseline sees it.

    90 of 100 names on each side read `R1`, paired at random. Independent
    columns with that distribution agree ~0.9*0.9 + 0.1*0.1 = 82% of the time
    for free, so an observed 82% would be worth nothing. The baseline has to
    report ~82, not ~14 (which is what a uniform-random null would say).
    """
    dailies = ["R1"] * 90 + ["S1"] * 10
    weeklies = ["R1"] * 90 + ["S1"] * 10
    # Interleave so the pairing is not already sorted into agreement.
    pairs = list(zip(dailies, weeklies[::-1]))
    base = pta.rotation_baseline(pairs, rotations=40)
    assert 70.0 < base["zone"] < 95.0


def test_rotation_preserves_both_label_distributions():
    """A rotation is a permutation — neither column's multiset may change."""
    pairs = [("R1", "S1"), ("R1-PP", "PP-S1"), ("Near Pivot", "R1")] * 10
    n = len(pairs)
    weeklies = [p[1] for p in pairs]
    for k in range(1, 5):
        rotated = weeklies[k:] + weeklies[:k]
        assert sorted(rotated) == sorted(weeklies)
        assert len(rotated) == n


def test_summarise_of_nothing_says_nothing():
    assert pta.summarise([]) == {"n": 0}


# ── the pre-registered bands ─────────────────────────────────────────────────
def test_verdict_bands_are_the_registered_ones():
    cosmetic = pta.summarise([("R1", "R1")] * 100)
    assert pta.verdict(cosmetic)[0] == "COSMETIC"

    # 75% same side, 25% opposite -> REAL BUT NARROW, and the opposite rate
    # clears the contradiction threshold independently of the band.
    narrow = pta.summarise([("R1", "R1-PP")] * 75 + [("R1", "S1")] * 25)
    band, contra, _ = pta.verdict(narrow)
    assert band == "REAL BUT NARROW"
    assert contra == "CONTRADICTION"

    split = pta.summarise([("R1", "R1")] * 50 + [("R1", "S1")] * 50)
    assert pta.verdict(split)[0] == "TWO DIFFERENT READINGS"


def test_too_few_names_is_inconclusive_not_a_verdict():
    """Under 30 names must not produce a band. An agreement rate over a handful
    of names is a number, not a reading, and B-58 is on this page because an
    underpowered run was nearly read as a null."""
    assert pta.verdict(pta.summarise([("R1", "R1")] * 5))[0] == "INCONCLUSIVE"


# ── the read itself ──────────────────────────────────────────────────────────
def _frame(n: int = 120, start: float = 100.0) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    close = pd.Series([start + i * 0.5 for i in range(n)], index=idx)
    return pd.DataFrame({"open": close, "high": close * 1.01,
                         "low": close * 0.99, "close": close}, index=idx)


def test_read_pair_returns_both_timeframes():
    p = pta.read_pair(_frame())
    assert p is not None
    d, w = p
    assert pta.side(d) is not None and pta.side(w) is not None


def test_a_frame_too_short_for_a_weekly_pivot_is_excluded_not_counted():
    """The exclusion rule, which is load-bearing: a name that cannot produce
    both reads is dropped, never recorded as a disagreement. Counting it would
    manufacture the very split the study is measuring."""
    assert pta.read_pair(_frame(n=1)) is None
    assert pta.read_pair(None) is None
