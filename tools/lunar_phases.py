"""
lunar_phases.py — Full Moon (Purnima) and New Moon (Amavasya) dates.

Source: PyEphem's astronomical solver (already a project dep — see
astro_trading.py). No network calls, no scraping — these are exact
astronomical events to-the-minute.

Public API:
    from lunar_phases import lunar_events_for_range
    events = lunar_events_for_range(date(2026,1,1), date(2027,12,31))
    # → [{'phase': 'new_moon', 'utc': datetime(...), 'local': datetime(...)}, ...]

Each event is a single instant; the docs render it as the calendar day it
falls on in the given local timezone (Asia/Kolkata by default, since the
yoga calendar is India-anchored).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Iterator

import ephem  # already installed for astro_trading.py
import pytz

log = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


def _iter_phase_instants(start: date, end: date, kind: str) -> Iterator[datetime]:
    """Yield UTC datetimes of each full/new moon in [start, end] inclusive.

    `kind` is "full" or "new". Uses PyEphem's next_full_moon / next_new_moon
    iterative solver — robust across centuries and timezone-independent."""
    fn = ephem.next_full_moon if kind == "full" else ephem.next_new_moon

    # Start one day before to catch a phase that falls right on `start`.
    cursor = ephem.Date(datetime.combine(start - timedelta(days=1),
                                          datetime.min.time()))
    end_ephem = ephem.Date(datetime.combine(end + timedelta(days=1),
                                             datetime.min.time()))

    # ephem.next_full_moon(d) returns an ephem.Date in TT (very close to UTC
    # for this purpose). Convert to a tz-aware UTC datetime.
    while True:
        next_d = fn(cursor)
        if next_d > end_ephem:
            return
        py_dt = next_d.datetime().replace(tzinfo=timezone.utc)
        if py_dt.date() >= start and py_dt.date() <= end:
            yield py_dt
        # Advance just past this event to make the next call return the next one.
        cursor = ephem.Date(next_d + 0.1)


def lunar_events_for_range(start: date, end: date) -> list[dict]:
    """All Full Moon + New Moon instants inside [start, end] inclusive.

    Returns a list of dicts (instead of a custom dataclass) so the shape is
    JSON-serialisable and trivially mixable with yoga_dates output downstream
    in build_reversal_calendar.py.
    """
    events: list[dict] = []

    for kind, label in (("full", "full_moon"), ("new", "new_moon")):
        for utc_dt in _iter_phase_instants(start, end, kind):
            local_dt = utc_dt.astimezone(IST)
            events.append({
                "phase":    label,
                "utc":      utc_dt,
                "local":    local_dt,
                "date":     local_dt.date(),
                "weekday":  local_dt.strftime("%A"),
            })

    events.sort(key=lambda e: e["utc"])
    return events


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("year", type=int, help="calendar year (e.g. 2026)")
    args = p.parse_args()

    start = date(args.year, 1, 1)
    end   = date(args.year, 12, 31)
    events = lunar_events_for_range(start, end)

    print(f"Lunar events {args.year} (IST) — {len(events)} total\n")
    print(f"{'Date (IST)':<12} {'Time (IST)':<8} Phase       Weekday")
    print("-" * 50)
    for e in events:
        print(f"{e['date'].isoformat():<12} "
              f"{e['local'].strftime('%H:%M'):<8} "
              f"{e['phase']:<11} {e['weekday']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
