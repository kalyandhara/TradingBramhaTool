#!/usr/bin/env python3
"""
sbc_hora.py — planetary hours (hora) for best-time trade windows.

Each day (sunrise->sunset) and night (sunset->sunrise) is split into 12 equal
"horas". The first day-hora is ruled by the weekday lord; consecutive horas
cycle the Chaldean order [Sun, Venus, Mercury, Moon, Saturn, Jupiter, Mars].
Benefic-ruled horas (Jupiter, Venus, Mercury, Moon) are the favourable
("best time") windows; malefic-ruled (Saturn, Mars, Sun) are caution windows.

Used by the Trading Signals panel to print per-sector best-entry windows like
"09:04-10:03 (Jupiter)".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, time
from typing import List, Optional

import ephem

IST = timezone(timedelta(hours=5, minutes=30))

# consecutive-hora Chaldean order (so day+1 first hora lands on next weekday lord)
HORA_ORDER = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]
# weekday (Mon=0..Sun=6) -> ruling planet of that day's first hora
WEEKDAY_LORD = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
GLYPH = {"Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿",
         "Jupiter": "♃", "Venus": "♀", "Saturn": "♄"}


@dataclass
class Hora:
    start_ist: datetime
    end_ist: datetime
    lord: str
    is_day: bool

    @property
    def benefic(self) -> bool:
        return self.lord in BENEFIC


def _sun_events(day: datetime, lat: str, lon: str):
    obs = ephem.Observer()
    obs.lat, obs.lon = lat, lon
    obs.date = ephem.Date(datetime(day.year, day.month, day.day, 0, 0))
    rise = obs.next_rising(ephem.Sun()).datetime().replace(tzinfo=timezone.utc)
    sett = obs.next_setting(ephem.Sun()).datetime().replace(tzinfo=timezone.utc)
    obs.date = ephem.Date(sett)
    next_rise = obs.next_rising(ephem.Sun()).datetime().replace(tzinfo=timezone.utc)
    return rise.astimezone(IST), sett.astimezone(IST), next_rise.astimezone(IST)


def compute_horas(day: datetime, lat: str = "19.076",
                  lon: str = "72.8777") -> List[Hora]:
    """The 24 horas (12 day + 12 night) for a calendar day at a location."""
    rise, sett, next_rise = _sun_events(day, lat, lon)
    day_len = (sett - rise) / 12
    night_len = (next_rise - sett) / 12
    weekday = day.weekday()
    first_lord = WEEKDAY_LORD[weekday]
    start_idx = HORA_ORDER.index(first_lord)

    horas: List[Hora] = []
    for i in range(12):                       # day horas
        s = rise + day_len * i
        horas.append(Hora(s, s + day_len,
                          HORA_ORDER[(start_idx + i) % 7], True))
    for i in range(12):                       # night horas
        s = sett + night_len * i
        horas.append(Hora(s, s + night_len,
                          HORA_ORDER[(start_idx + 12 + i) % 7], False))
    return horas


def best_windows(day: datetime, session_open=time(9, 15),
                 session_close=time(15, 30),
                 lat: str = "19.076", lon: str = "72.8777") -> List[Hora]:
    """Benefic-ruled horas overlapping the trading session."""
    out = []
    for h in compute_horas(day, lat, lon):
        if not h.benefic:
            continue
        if h.end_ist.time() <= session_open or h.start_ist.time() >= session_close:
            continue
        out.append(h)
    return out


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    d = datetime.now(IST)
    print(f"Horas for {d:%Y-%m-%d} ({d:%A}) — Mumbai:")
    for h in compute_horas(d)[:12]:
        tag = "BENEFIC" if h.benefic else "caution"
        print(f"  {h.start_ist:%H:%M}-{h.end_ist:%H:%M}  "
              f"{GLYPH[h.lord]} {h.lord:8s} {tag}")
    print("\nBest (benefic) session windows:")
    for h in best_windows(d):
        print(f"  {h.start_ist:%H:%M}-{h.end_ist:%H:%M} {h.lord}")
