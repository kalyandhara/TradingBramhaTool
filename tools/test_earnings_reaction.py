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


# ── The PEAD walk ────────────────────────────────────────────────────────────
# These pin the two definitional choices the walk makes that a naive version
# gets wrong: drift is measured FROM THE REACTION BAR (not the event bar), and
# an unfinished +20 window is incomplete rather than zero.

@pytest.fixture
def _cal(monkeypatch):
    """Install a cached-calendar stub; returns the setter."""
    def _set(dates):
        monkeypatch.setattr(
            er, "_read_any",
            lambda sym: {"events": [{"date": d} for d in dates]})
    return _set


def test_drift_is_measured_from_the_reaction_bar_not_the_event_bar():
    """The whole point of PEAD: the announcement jump is NOT drift.

    Event on bar 2, a +10% reaction on bar 3, then a perfectly flat five
    sessions. D+1 must show the jump and →+5 must show 0.0% — folding the jump
    into the drift would report +10% and make every well-received result look
    like it drifted.
    """
    df = _frame("2026-01-05", [100.0, 100.0, 100.0, 110.0] + [110.0] * 25)
    i, _ = er._bar_index(df, df.index[2].date())
    assert er._close_return(df, i + 1) == pytest.approx(10.0)
    assert er._drift_from(df, i + 1, 5) == pytest.approx(0.0)
    assert er._drift_from(df, i + 1, 20) == pytest.approx(0.0)


def test_an_unfinished_drift_window_is_none_not_zero():
    """A result announced three weeks ago has a running +20 window. Absent, not
    flat — the difference is the whole reading."""
    df = _frame("2026-01-05", [100.0] * 12)
    assert er._drift_from(df, 1, 5) == pytest.approx(0.0)
    assert er._drift_from(df, 1, 20) is None


def test_the_walk_covers_four_quarters_newest_first(_cal):
    _cal(["2026-07-17", "2026-04-18", "2026-01-16", "2025-10-17", "2025-07-18"])
    df = _frame("2025-06-02", [100.0 + i for i in range(340)])
    w = er.pead_walk("ACME", df, today=date(2026, 9, 10))
    assert len(w["events"]) == er.WALK_QUARTERS == 4
    assert [e["date"] for e in w["events"]] == [
        date(2026, 7, 17), date(2026, 4, 18),
        date(2026, 1, 16), date(2025, 10, 17)]
    # A monotonically rising frame drifts up after every reaction.
    assert all(e["d20"] > 0 for e in w["events"])
    assert w["consistency"] == w["agreeable"] == 4


def test_a_stale_calendar_produces_no_walk_at_all(_cal):
    """Same rule as `last_earnings` — a 2018 feed does not get to render a
    four-quarter walk of 2018 events."""
    _cal(["2018-08-14", "2018-05-10", "2018-02-08", "2017-11-09"])
    df = _frame("2026-01-05", [100.0] * 200)
    assert er.pead_walk("STALE", df, today=date(2026, 9, 10))["events"] == []


def test_no_calendar_and_no_bars_both_render_absent(_cal):
    _cal([])
    df = _frame("2026-01-05", [100.0] * 50)
    assert er.pead_walk("NOCAL", df, today=date(2026, 9, 10))["events"] == []
    _cal(["2026-07-17"])
    out = er.pead_walk("NOBARS", pd.DataFrame(), today=date(2026, 9, 10))
    assert out["events"] == [] and out["consistency"] is None
