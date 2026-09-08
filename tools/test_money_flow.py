"""Tests for money_flow.py (B-60), offline.

Two things are worth pinning here.

The arithmetic has exact endpoints — a close ON the high must give CMF = +1 and a
close ON the low must give -1 — so the multiplier's sign convention cannot silently
invert, which is the kind of error that looks plausible on a heatmap forever.

And the AGGREGATION, which is the actual design decision: summing money-flow
volume across a sector must not degenerate into averaging its members, because
that is what lets a tiny illiquid name outvote an index heavyweight.
"""
import numpy as np
import pandas as pd
import pytest

import money_flow as mf


def _bars(n=40, *, close_at="high", volume=1000.0):
    """Bars whose closes sit at a controlled place inside their range."""
    hi = np.full(n, 110.0)
    lo = np.full(n, 90.0)
    if close_at == "high":
        c = hi.copy()
    elif close_at == "low":
        c = lo.copy()
    else:
        c = (hi + lo) / 2.0
    return pd.DataFrame({"high": hi, "low": lo, "close": c,
                         "open": c, "volume": np.full(n, volume)})


# ── the arithmetic, at its endpoints ─────────────────────────────────────────

def test_closing_on_the_high_every_bar_is_plus_one():
    assert mf.cmf(_bars(close_at="high")) == pytest.approx(1.0)


def test_closing_on_the_low_every_bar_is_minus_one():
    assert mf.cmf(_bars(close_at="low")) == pytest.approx(-1.0)


def test_closing_at_the_midpoint_is_zero():
    assert mf.cmf(_bars(close_at="mid")) == pytest.approx(0.0)


def test_a_zero_range_bar_contributes_nothing_but_still_counts_its_volume():
    """0/0 is undefined, not +1. It must not quietly become accumulation."""
    d = _bars(close_at="high", volume=1000.0).copy()
    d.loc[:9, ["high", "low", "close"]] = 100.0        # 10 limit-locked bars
    got = mf.cmf(d, n=40)
    # 30 bars of +1 x 1000 over 40 bars of volume.
    assert got == pytest.approx(30_000 / 40_000, abs=1e-6)


def test_too_little_history_returns_none_not_a_partial_window():
    assert mf.cmf(_bars(n=10), n=21) is None
    assert mf.cmf(None) is None


def test_offset_reads_an_earlier_window():
    d = pd.concat([_bars(21, close_at="low"), _bars(21, close_at="high")],
                  ignore_index=True)
    assert mf.cmf(d, n=21, offset=0) == pytest.approx(1.0)
    assert mf.cmf(d, n=21, offset=21) == pytest.approx(-1.0)


# ── the aggregation: the design decision this module exists to get right ─────

def test_a_heavyweight_dominates_a_smallcap_by_volume_not_by_headcount():
    """One huge accumulating name vs three tiny distributing ones.

    Volume-weighted, the sector is accumulating — that is where the money went.
    Averaged, the three smallcaps outvote it 3-to-1 and the sector reads
    negative. Both are computed so the difference is visible, not asserted.
    """
    members = {
        "BIG": _bars(close_at="high", volume=10_000_000.0),
        "S1": _bars(close_at="low", volume=1_000.0),
        "S2": _bars(close_at="low", volume=1_000.0),
        "S3": _bars(close_at="low", volume=1_000.0),
    }
    weighted = mf.sector_cmf(members)
    averaged = mf.sector_cmf(members, mode="mean_of_members")
    assert weighted > 0.99, "volume weighting must follow the money"
    assert averaged < 0, "the naive mean inverts the reading"


def test_sector_cmf_stays_inside_the_bound():
    members = {"A": _bars(close_at="high"), "B": _bars(close_at="low")}
    v = mf.sector_cmf(members)
    assert -1.0 <= v <= 1.0
    assert v == pytest.approx(0.0), "equal volume, opposite ends, cancels"


def test_members_with_too_little_history_are_skipped_not_fatal():
    members = {"OK": _bars(close_at="high"), "SHORT": _bars(n=5)}
    assert mf.sector_cmf(members) == pytest.approx(1.0)


def test_empty_sector_is_none():
    assert mf.sector_cmf({}) is None


# ── the trend label ──────────────────────────────────────────────────────────

def test_all_positive_is_accumulation_and_all_negative_is_distribution():
    assert mf.trend_label([0.1, 0.08, 0.05, 0.02]) == "Accumulation"
    assert mf.trend_label([-0.1, -0.08, -0.05, -0.02]) == "Distribution"


def test_a_monotone_climb_through_zero_is_increasing():
    # Displayed newest-first: today +0.05 back to -0.10 a month ago.
    assert mf.trend_label([0.05, 0.01, -0.04, -0.10]) == "Increasing"


def test_a_monotone_fall_through_zero_is_decreasing():
    assert mf.trend_label([-0.05, -0.01, 0.04, 0.10]) == "Decreasing"


def test_a_mixed_shape_is_flat_rather_than_forced_into_a_label():
    assert mf.trend_label([0.05, -0.02, 0.04, -0.01]) == "-"


def test_too_few_readings_is_flat():
    assert mf.trend_label([None, None, None, 0.05]) == "-"


# ── the guardrails that keep this a VIEW ─────────────────────────────────────

def test_the_gap_caveat_travels_with_the_module():
    """The page must not be able to drift from the caveat."""
    assert "ignores the previous close" in mf.CAVEAT
    assert "gap" in mf.CAVEAT.lower()


def test_the_heat_clip_is_the_practical_range_not_the_theoretical_bound():
    """Scaling to +-1 renders every real reading near-white."""
    assert mf.HEAT_CLIP == pytest.approx(0.25)


def test_it_is_not_registered_as_a_scanner():
    """B-60 ships as a view: never a confluence vote."""
    import scanner_templates as sc
    names = " ".join(sc.SCANNERS).lower()
    assert "money flow" not in names or "mfi" in names
    assert not hasattr(mf, "scan_money_flow")
