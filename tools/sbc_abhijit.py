#!/usr/bin/env python3
"""
sbc_abhijit.py — Abhijit Nakshatra calendar (the 28th, intercalary nakshatra).

Abhijit is the extra nakshatra placed on the SBC board's West side. As a Moon
transit it is a short arc in sidereal Capricorn — classically 6°40' to
10°53'20" of Makara, i.e. sidereal longitude 276°40' to 280°53'20"
(276.6667° to 280.8889°). "Abhijit" = "victorious"; the transit is treated as a
high-significance timing point.

This module computes Abhijit Moon-transit windows with PyEphem (location-
independent, exact) and cross-checks them against the drikpanchang.com
published calendar (see ABHIJIT_2026_DRIK, sourced 2026, DC local time).

CLI:
  py -3 tools/sbc_abhijit.py 2026          # list 2026 windows (IST)
  py -3 tools/sbc_abhijit.py verify        # cross-check vs drikpanchang
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import ephem

from sarvatobhadra_chakra import lahiri_ayanamsa, IST_OFFSET

ABHIJIT_START = 276.0 + 40.0 / 60.0            # 276.6667°
ABHIJIT_END = 280.0 + 53.0 / 60.0 + 20.0 / 3600.0  # 280.8889°

# drikpanchang.com published 2026 Abhijit calendar, as fetched (Washington DC
# local time, DST-adjusted). Kept as the intake reference for cross-checking.
# (date, start_local, end_local) — display strings only.
ABHIJIT_2026_DRIK = [
    ("2026-01-18", "19:00", "2026-01-19 03:04"),
    ("2026-02-15", "02:58", "2026-02-15 10:59"),
    ("2026-03-14", "12:56", "2026-03-14 21:00"),
    ("2026-04-10", "21:40", "2026-04-11 05:53"),
    ("2026-05-08", "05:13", "2026-05-08 13:35"),
    ("2026-06-04", "11:32", "2026-06-04 19:57"),
    ("2026-07-01", "17:19", "2026-07-02 01:43"),
    ("2026-07-28", "23:32", "2026-07-29 07:52"),
    ("2026-08-25", "06:47", "2026-08-25 15:06"),
    ("2026-09-21", "15:01", "2026-09-21 23:22"),
    ("2026-10-18", "23:28", "2026-10-19 07:55"),
    ("2026-12-12", "12:55", "2026-12-12 21:30"),
]


def _moon_sidereal(dt_utc: datetime) -> float:
    m = ephem.Moon()
    m.compute(ephem.Date(dt_utc))
    trop = float(ephem.Ecliptic(m).lon) * 180.0 / 3.141592653589793
    return (trop - lahiri_ayanamsa(dt_utc)) % 360.0


def _in_abhijit(lon: float) -> bool:
    return ABHIJIT_START <= lon < ABHIJIT_END


@dataclass
class AbhijitWindow:
    start_ist: datetime
    end_ist: datetime

    @property
    def duration_min(self) -> int:
        return int((self.end_ist - self.start_ist).total_seconds() // 60)


def abhijit_windows(year: int, step_min: int = 10) -> List[AbhijitWindow]:
    """All Abhijit Moon-transit windows in `year` (IST), via ephem scan."""
    t = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)
    step = timedelta(minutes=step_min)
    out: List[AbhijitWindow] = []
    prev_in = False
    start_utc: Optional[datetime] = None
    while t <= end:
        inside = _in_abhijit(_moon_sidereal(t))
        if inside and not prev_in:
            start_utc = t
        elif not inside and prev_in and start_utc is not None:
            out.append(AbhijitWindow(start_utc + IST_OFFSET, t + IST_OFFSET))
            start_utc = None
        prev_in = inside
        t += step
    return out


def next_abhijit(now_utc: Optional[datetime] = None) -> Optional[AbhijitWindow]:
    if now_utc is None:
        now_utc = datetime.utcnow()
    now_ist = now_utc + IST_OFFSET
    for w in abhijit_windows(now_ist.year):
        if w.end_ist >= now_ist:
            return w
    return None


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    cmd = sys.argv[1] if len(sys.argv) > 1 else "2026"
    if cmd == "verify":
        wins = abhijit_windows(2026)
        print(f"ephem found {len(wins)} Abhijit windows in 2026; "
              f"drikpanchang lists {len(ABHIJIT_2026_DRIK)}.")
        print(f"{'ephem (IST)':40s} | drik date")
        for w, drik in zip(wins, ABHIJIT_2026_DRIK):
            print(f"{w.start_ist:%Y-%m-%d %H:%M}–{w.end_ist:%H:%M}"
                  f"  ({w.duration_min}m)   | {drik[0]}")
    else:
        year = int(cmd)
        for w in abhijit_windows(year):
            print(f"{w.start_ist:%Y-%m-%d %H:%M}–{w.end_ist:%H:%M} IST "
                  f"({w.duration_min}m)")
