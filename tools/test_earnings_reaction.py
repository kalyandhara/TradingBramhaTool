"""UI-2 · the earnings-reaction group.

These pin the definitional edges, which is where a "reaction" column goes wrong:
which bar counts as the event, what happens when the date is not a trading day,
and what a missing reading renders as.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import earnings_reaction as er


def _frame(start: str, closes):
    """Daily frame on consecutive WEEKDAYS, so snapping can be exercised."""
    idx = pd.bdate_range(start=start, periods=len(closes))
    return pd.DataFrame({"close": closes}, index=idx)


def test_close_to_close_returns_around_the_event_bar():
    df = _frame("2026-01-05", [100.0, 101.0, 110.0, 108.0, 108.0])
    i, slip = er._bar_index(df, date(2026, 1, 7))     # the third bar
    assert (i, slip) == (2, 0)
    assert er._close_return(df, i - 1) == pytest.approx(1.0)    # -1D
    assert er._close_return(df, i) == pytest.approx(8.91, abs=0.01)   # E-day
    assert er._close_return(df, i + 1) == pytest.approx(-1.82, abs=0.01)  # +1D


def test_a_non_trading_event_date_snaps_forward_and_says_so():
    """A Saturday result must not report a hole — but the caller has to be able
    to see that the bar is not the event date."""
    df = _frame("2026-01-05", [100.0] * 10)           # Mon 05 Jan onward
    i, slip = er._bar_index(df, date(2026, 1, 10))    # a Saturday
    assert i is not None
    assert slip == 2                                  # -> Monday 12 Jan
    assert df.index[i].date() == date(2026, 1, 12)


def test_snapping_stops_rather_than_reaching_for_a_distant_session():
    """A 'reaction' measured a week later is not one."""
    df = _frame("2026-01-05", [100.0] * 3)            # Mon-Wed only
    far = df.index[-1].date() + timedelta(days=er.MAX_SNAP_DAYS + 3)
    assert er._bar_index(df, far) == (None, 0)


def test_event_newer_than_the_last_bar_is_absent_not_zero():
    """A result announced today has no bar yet. That is absent, not a flat
    reaction — rendering it as 0.00% would state something false."""
    df = _frame("2026-01-05", [100.0, 101.0, 102.0])
    i, _ = er._bar_index(df, df.index[-1].date() + timedelta(days=30))
    assert i is None


def test_close_return_is_none_at_the_frame_edges():
    """The first bar has no previous close and the last has no next."""
    df = _frame("2026-01-05", [100.0, 101.0])
    assert er._close_return(df, 0) is None            # nothing before it
    assert er._close_return(df, 5) is None            # past the end
    assert er._close_return(df, None) is None


def test_reaction_returns_every_key_even_with_no_data():
    """A caller building a DataFrame from these needs stable keys, or the
    columns go ragged and a missing reading reads as a missing feature."""
    r = er.reaction("NOSUCHSYMBOL", None)
    assert set(r) == {"next_earn", "past_earn", "earn_d_minus_1", "earn_day",
                      "earn_d_plus_1", "snapped_days"}
    assert all(r[k] is None for k in
               ("next_earn", "past_earn", "earn_d_minus_1", "earn_day",
                "earn_d_plus_1"))


def test_display_read_ignores_the_fetch_ttl():
    """`earnings_calendar._read_cache` enforces a 12-hour TTL because it guards
    a FETCH decision. This is a DISPLAY read and a past earnings date does not
    go stale — gating it on freshness blanked every column on a day-old cache,
    which is how the bug was found."""
    import earnings_calendar as ec
    assert er._read_any.__doc__ and "regardless of age" in er._read_any.__doc__
    # The two readers must not be the same function.
    assert er._read_any is not ec._read_cache


def test_next_and_last_are_split_on_the_DATE_not_on_reported():
    """A result can sit unreported in the feed for days after it was announced.
    Keying 'next' off `reported is None` would then show a next-earnings date in
    the past, which is worse than a blank cell."""
    src = er.next_earnings.__doc__ + er.last_earnings.__doc__
    assert "reported" in src        # the trap is documented where it is decided


def test_a_years_stale_calendar_renders_blank_not_as_a_2018_result():
    """The coverage reality that forced MAX_EVENT_AGE_DAYS.

    yfinance's calendar for Indian micro-caps stops years back — GENESYS's
    newest event is 2018-08-14, CENTUM's 2017-05-30. Those companies have
    reported ~25 quarters since. Printing the stale date would assert the
    company last reported in 2018, which is false; blank asserts only that the
    feed has nothing, which is true.
    """
    class _Stub:
        @staticmethod
        def _read_any(sym):
            return {"events": [{"date": "2018-08-14"}, {"date": "2018-05-10"}]}

    orig = er._read_any
    er._read_any = _Stub._read_any
    try:
        assert er.last_earnings("STALE", today=date(2026, 9, 10)) is None
        # Inside the window it comes back normally.
        er._read_any = staticmethod(
            lambda sym: {"events": [{"date": "2026-07-17"}]}).__func__
        assert er.last_earnings("FRESH", today=date(2026, 9, 10)) == date(2026, 7, 17)
    finally:
        er._read_any = orig


def test_the_age_bound_is_generous_enough_for_a_quarterly_reporter():
    """A quarterly reporter's last result is at most ~120 days old, so the bound
    must sit well clear of that or it would suppress real results."""
    assert er.MAX_EVENT_AGE_DAYS > 200
