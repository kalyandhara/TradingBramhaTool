"""Tests for the yearly opening range — B-98.

Nothing here claims the construct WORKS; it has not been measured yet, and the
pre-registration (`analyses/Yearly-Opening-Range-Pre-Registration`) is deliberately
written before the study. What is pinned is that the calendar arithmetic is
calendar arithmetic:

  * the range comes from JANUARY, not from the first N bars of whatever frame it
    was handed — the failure this module would have if it followed the desk's
    usual offset-only convention;
  * an undated frame RAISES rather than guessing, because the scanner path calls
    `reset_index(drop=True)` and a silent fallback there would produce a
    plausible number off the wrong bars;
  * the event is the FIRST close outside, and "never left" is a real answer
    rather than a missing row.
"""
import numpy as np
import pandas as pd
import pytest

import calendar_anchor as ca


def _frame(bars):
    """bars = {date-string: (high, low, close)}"""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in bars])
    hi = [v[0] for v in bars.values()]
    lo = [v[1] for v in bars.values()]
    cl = [v[2] for v in bars.values()]
    return pd.DataFrame({"open": cl, "high": hi, "low": lo, "close": cl,
                         "volume": np.full(len(cl), 1e6)}, index=idx)


def _year(jan=(110, 90), after=None, year=2024):
    """A January that ranges `jan`, then February bars at the given closes."""
    bars = {}
    for i, d in enumerate(pd.bdate_range(f"{year}-01-01", periods=20)):
        # One bar prints the high, one the low, the rest sit inside.
        h, l = (jan[0], jan[0] - 1) if i == 3 else (jan[1] + 1, jan[1]) if i == 7 else (105, 95)
        bars[d.strftime("%Y-%m-%d")] = (h, l, 100)
    for i, d in enumerate(pd.bdate_range(f"{year}-02-01", periods=len(after or []))):
        px = after[i]
        bars[d.strftime("%Y-%m-%d")] = (px + 1, px - 1, px)
    return _frame(bars)


# ── the range is January's, not the frame's first bars ────────────────────────
def test_the_range_is_januarys_high_and_low():
    r = ca.yearly_opening_range(_year(jan=(110, 90), after=[100]), 2024)
    assert (r["high"], r["low"]) == (110.0, 90.0)
    assert r["sessions"] == 20


def test_february_bars_do_not_widen_the_range():
    """The whole construct is that the anchor STOPS at the end of January. A
    February spike is what the range is measured against, never part of it."""
    r = ca.yearly_opening_range(_year(jan=(110, 90), after=[500, 5]), 2024)
    assert (r["high"], r["low"]) == (110.0, 90.0)


def test_another_years_january_is_a_different_range():
    df = pd.concat([_year(jan=(110, 90), after=[100], year=2023),
                    _year(jan=(210, 190), after=[200], year=2024)])
    assert ca.yearly_opening_range(df, 2023)["high"] == 110.0
    assert ca.yearly_opening_range(df, 2024)["high"] == 210.0


def test_a_year_with_no_january_returns_none_not_a_guess():
    """None means 'this frame does not cover that January'. A caller must not
    read it as 'no range' and fall back to the bars it does have."""
    df = _year(after=[100], year=2024)
    assert ca.yearly_opening_range(df, 2021) is None


def test_a_partial_january_still_counts_and_says_so():
    """A mid-month listing has a real, thin range. Reporting the session count
    lets a reader judge it; silently dropping it would lose the year."""
    bars = {d.strftime("%Y-%m-%d"): (105, 95, 100)
            for d in pd.bdate_range("2024-01-18", periods=5)}
    bars.update({d.strftime("%Y-%m-%d"): (101, 99, 100)
                 for d in pd.bdate_range("2024-02-01", periods=3)})
    r = ca.yearly_opening_range(_frame(bars), 2024)
    assert r["sessions"] == 5 and r["high"] == 105.0


# ── dates are not optional ────────────────────────────────────────────────────
def test_an_undated_frame_raises():
    """`_clean_ohlc` and `backtest_scanner` both reset the index. Guessing that
    bar 0 is the year's first session would produce a plausible number from the
    wrong bars — the exact failure this module refuses to have."""
    df = _year(after=[100]).reset_index(drop=True)
    with pytest.raises(ca.UndatedFrame):
        ca.yearly_opening_range(df, 2024)


def test_an_empty_frame_raises():
    with pytest.raises(ca.UndatedFrame):
        ca.yearly_opening_range(pd.DataFrame(), 2024)


# ── state ─────────────────────────────────────────────────────────────────────
def test_state_reads_above_below_and_inside():
    assert ca.state_at(_year(after=[120]), 2024)["state"] == "ABOVE"
    assert ca.state_at(_year(after=[80]), 2024)["state"] == "BELOW"
    assert ca.state_at(_year(after=[100]), 2024)["state"] == "INSIDE"


def test_distance_is_measured_to_the_boundary_not_the_middle():
    """A reader asking 'how far' means how far from the level that matters."""
    s = ca.state_at(_year(jan=(110, 90), after=[121]), 2024)
    assert s["state"] == "ABOVE"
    assert s["distance_pct"] == pytest.approx((121 - 110) / 121 * 100, abs=0.01)


def test_january_itself_has_no_state():
    """Inside the anchor month the range is still being formed; a state there
    would be scored against a boundary that has not finished existing."""
    assert ca.state_at(_year(after=[]), 2024) is None


# ── the event ─────────────────────────────────────────────────────────────────
def test_the_event_is_the_first_close_outside():
    ev = ca.detect_yearly_opening_range(_year(after=[100, 105, 115, 130]), 2024)
    assert ev["broke"] and ev["direction"] == "up"
    assert ev["sessions_into_year"] == 3          # the 115 close, not the 130
    assert ev["break_close"] == 115.0


def test_a_downside_break_is_the_same_event_mirrored():
    ev = ca.detect_yearly_opening_range(_year(after=[100, 85]), 2024)
    assert ev["broke"] and ev["direction"] == "down" and ev["sessions_into_year"] == 2


def test_a_range_that_was_never_left_is_an_answer_not_a_missing_row():
    """Counting only the breaks would quietly condition the whole study on the
    thing it is trying to measure."""
    ev = ca.detect_yearly_opening_range(_year(after=[100, 101, 99, 100]), 2024)
    assert ev["broke"] is False and ev["direction"] is None
    assert ev["sessions_into_year"] == 4


def test_a_break_that_came_back_inside_is_flagged():
    """'Broke in February' and 'is outside today' are different facts, and a
    measured-move claim leans on the second one."""
    ev = ca.detect_yearly_opening_range(_year(after=[115, 100]), 2024)
    assert ev["broke"] and ev["still_outside"] is False
    held = ca.detect_yearly_opening_range(_year(after=[115, 125]), 2024)
    assert held["still_outside"] is True


def test_touching_the_boundary_is_not_a_break():
    """`> high`, not `>= high`. A close exactly at the level has not left the
    range, and admitting it would count a touch as an event."""
    ev = ca.detect_yearly_opening_range(_year(jan=(110, 90), after=[110, 90]), 2024)
    assert ev["broke"] is False


def test_years_covered_lists_only_years_with_an_anchor_month():
    df = pd.concat([_year(after=[100], year=2023), _year(after=[100], year=2024)])
    assert ca.years_covered(df) == [2023, 2024]
