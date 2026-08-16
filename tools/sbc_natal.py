#!/usr/bin/env python3
"""
sbc_natal.py — Natal (birth) chart + Tara Bala personal overlay for SBC.

Two things the SBC tool's "Birth Kundli" panel needs:

1. compute_natal(birth_dt_utc, lat, lon) — sidereal planet positions at birth,
   the Lagna (ascendant), and each planet's house (North-Indian, whole-sign
   from the Lagna). Reuses sarvatobhadra_chakra.compute_planets for positions;
   adds the ascendant, which needs the birth place + time.

2. tara_bala(birth_nakshatra, moon_nakshatra) — the classical 9-fold day
   filter: count from the native's birth nakshatra to today's Moon nakshatra;
   the tara (1..9) says whether the day's lunar energy works FOR or AGAINST the
   native. This is the personalised trade-timing layer (see the "Tara Bala
   Trading Filter" in the reference tool).

Ascendant formula: standard tropical Asc from RAMC (local sidereal time),
obliquity, and geographic latitude; converted to sidereal via Lahiri.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

try:
    import ephem
    HAS_EPHEM = True
except ImportError:  # pragma: no cover
    HAS_EPHEM = False

from sarvatobhadra_chakra import (
    NAKSHATRAS, compute_planets, lahiri_ayanamsa, PlanetState,
)

RASHIS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
          "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

OBLIQUITY_DEG = 23.4367

# Tara Bala — the 9 taras and their trade verdict (per the reference tool's
# "Tara Bala Trading Filter"): green = trade, yellow = caution, red = avoid.
TARA_NAMES = {1: "Janma", 2: "Sampat", 3: "Vipat", 4: "Kshema", 5: "Pratyari",
              6: "Sadhaka", 7: "Vadha", 8: "Mitra", 9: "Ati-Mitra"}
TARA_MEANING = {1: "Birth star — emotional volatility", 2: "Wealth",
                3: "Danger/loss", 4: "Well-being/safety", 5: "Obstacle",
                6: "Achievement", 7: "Danger/harm", 8: "Friend",
                9: "Best friend"}
_TARA_GREEN = {2, 4, 6, 8, 9}
_TARA_YELLOW = {1}


@dataclass
class NatalChart:
    when_utc: datetime
    lat: float
    lon: float
    lagna_sidereal: float          # ascendant longitude (sidereal deg)
    lagna_rashi: str
    lagna_rashi_index: int         # 0=Aries
    lagna_nakshatra: str
    planets: Dict[str, PlanetState]
    house_of: Dict[str, int]       # planet -> house 1..12 (whole-sign)
    moon_nakshatra: str


def ascendant_sidereal(dt_utc: datetime, lat: float, lon: float) -> float:
    """Sidereal ascendant longitude (deg, Lahiri) for a time + place."""
    if not HAS_EPHEM:
        raise RuntimeError("PyEphem required for ascendant")
    obs = ephem.Observer()
    obs.date = ephem.Date(dt_utc)
    obs.lat = str(lat)
    obs.lon = str(lon)
    ramc = float(obs.sidereal_time())              # radians, local sidereal
    obl = math.radians(OBLIQUITY_DEG)
    phi = math.radians(lat)
    # Standard tropical ascendant: A = atan2( cos θ, -(sin θ cos ε + tan φ sin ε) )
    y = math.cos(ramc)
    x = -(math.sin(ramc) * math.cos(obl) + math.tan(phi) * math.sin(obl))
    asc_trop = math.degrees(math.atan2(y, x)) % 360.0
    return (asc_trop - lahiri_ayanamsa(dt_utc)) % 360.0


def _rashi_of(sidereal_lon: float) -> int:
    return int(sidereal_lon // 30.0) % 12


def compute_natal(birth_dt_utc: datetime, lat: float, lon: float) -> NatalChart:
    planets = compute_planets(birth_dt_utc)
    lagna = ascendant_sidereal(birth_dt_utc, lat, lon)
    lagna_idx = _rashi_of(lagna)
    lagna_nak = NAKSHATRAS[int(lagna // (360.0 / 27.0)) % 27]
    house_of: Dict[str, int] = {}
    for name, ps in planets.items():
        pr = _rashi_of(ps.sidereal_lon)
        house_of[name] = ((pr - lagna_idx) % 12) + 1
    return NatalChart(
        when_utc=birth_dt_utc, lat=lat, lon=lon,
        lagna_sidereal=round(lagna, 2), lagna_rashi=RASHIS[lagna_idx],
        lagna_rashi_index=lagna_idx, lagna_nakshatra=lagna_nak,
        planets=planets, house_of=house_of,
        moon_nakshatra=planets["Moon"].nakshatra,
    )


@dataclass
class TaraBala:
    count: int                     # 1..27 from birth nak to Moon nak
    tara: int                      # 1..9
    tara_name: str
    meaning: str
    verdict: str                   # FAVOURABLE | CAUTION | AVOID
    color: str                     # green | yellow | red


def tara_bala(birth_nakshatra: str, moon_nakshatra: str) -> TaraBala:
    bi = NAKSHATRAS.index(birth_nakshatra)
    mi = NAKSHATRAS.index(moon_nakshatra)
    count = ((mi - bi) % 27) + 1
    tara = ((count - 1) % 9) + 1
    if tara in _TARA_GREEN:
        verdict, color = "FAVOURABLE", "green"
    elif tara in _TARA_YELLOW:
        verdict, color = "CAUTION", "yellow"
    else:
        verdict, color = "AVOID", "red"
    return TaraBala(count=count, tara=tara, tara_name=TARA_NAMES[tara],
                    meaning=TARA_MEANING[tara], verdict=verdict, color=color)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    # sample: 1990-01-15 08:30 IST, Delhi (28.61N, 77.21E) -> UTC 03:00
    bt = datetime(1990, 1, 15, 3, 0, 0)
    ch = compute_natal(bt, 28.61, 77.21)
    print(f"Lagna: {ch.lagna_rashi} ({ch.lagna_sidereal}°), "
          f"nak {ch.lagna_nakshatra}")
    print("Houses:")
    for n, ps in ch.planets.items():
        print(f"  {n:8s} {ps.nakshatra:16s} H{ch.house_of[n]}")
    from sarvatobhadra_chakra import compute_planets as cp
    today_moon = cp()["Moon"].nakshatra
    tb = tara_bala(ch.moon_nakshatra, today_moon)
    print(f"\nTara Bala (birth {ch.moon_nakshatra} -> today {today_moon}): "
          f"#{tb.count} {tb.tara_name} ({tb.tara}) -> {tb.verdict}")
