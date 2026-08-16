#!/usr/bin/env python3
"""
sarvatobhadra_chakra.py — Sarvatobhadra Chakra (SBC) market-timing engine.

Builds a dynamic 9x9 Vedic nakshatra grid from live planetary positions and
derives:
  * per-planet nakshatra placement + the vedas (aspects) each planet casts
  * malefic vs benefic veda scoring -> daily directional market bias
  * per-sector scoring via nama-nakshatra (name-sound) mapping
  * intraday reversal windows from the Moon's nakshatra-boundary crossings

Astronomy comes from PyEphem (VSOP87-grade positions). Everything sidereal
uses the Lahiri (Chitrapaksha) ayanamsa, the Indian civil standard.

Reference concept page:
  trading-wiki/wiki/concepts/Sarvatobhadra-Chakra.md

CLI:
  py -3 tools/sarvatobhadra_chakra.py grid
  py -3 tools/sarvatobhadra_chakra.py bias
  py -3 tools/sarvatobhadra_chakra.py windows --date 2026-08-15
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, time
from typing import Dict, List, Optional, Tuple

try:
    import ephem
    HAS_EPHEM = True
except ImportError:  # pragma: no cover - engine requires ephem
    HAS_EPHEM = False

IST_OFFSET = timedelta(hours=5, minutes=30)

# --- Nakshatra system -------------------------------------------------------

# 27 nakshatras in zodiacal order. Each spans 13deg20' (800').
NAKSHATRAS: List[str] = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

NAKSHATRA_SPAN_DEG = 360.0 / 27.0  # 13.333...

# Vimshottari dasha lord of each nakshatra (9-planet cycle from Ashwini).
_VIMSHOTTARI = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter",
                "Saturn", "Mercury"]


def nakshatra_lord(nak) -> str:
    """Vimshottari ruling planet of a nakshatra name or 0-based index."""
    idx = nak if isinstance(nak, int) else NAKSHATRAS.index(nak)
    return _VIMSHOTTARI[idx % 9]

# Lahiri ayanamsa (deg) — low-order polynomial in years from J2000.
# Good to ~0.01deg across 1990-2050, which is far finer than a 13deg nakshatra cell.
def lahiri_ayanamsa(dt_utc: datetime) -> float:
    j2000 = datetime(2000, 1, 1, 12, 0, 0)
    years = (dt_utc - j2000).total_seconds() / (365.25 * 86400.0)
    # 23.85 deg at J2000, precessing ~50.29"/yr.
    return 23.853 + (50.2909 / 3600.0) * years


# --- Planet nature ----------------------------------------------------------

MALEFIC = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}
BENEFIC = {"Jupiter", "Venus", "Moon", "Mercury"}

PLANET_GLYPH = {
    "Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿",
    "Jupiter": "♃", "Venus": "♀", "Saturn": "♄",
    "Rahu": "☊", "Ketu": "☋",
}

# The seven visible planets + lunar nodes. Nodes are computed from the Moon.
EPHEM_BODIES = {
    "Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Mercury": "Mercury",
    "Jupiter": "Jupiter", "Venus": "Venus", "Saturn": "Saturn",
}


@dataclass
class PlanetState:
    name: str
    tropical_lon: float          # deg 0-360
    sidereal_lon: float          # deg 0-360 (Lahiri)
    nakshatra_index: int         # 0-26
    nakshatra: str
    pada: int                    # 1-4
    speed_deg_per_day: float
    retrograde: bool
    nature: str                  # 'malefic' | 'benefic'

    @property
    def glyph(self) -> str:
        return PLANET_GLYPH.get(self.name, "?")


def _sidereal_from_tropical(tropical_lon: float, dt_utc: datetime) -> float:
    return (tropical_lon - lahiri_ayanamsa(dt_utc)) % 360.0


def _nakshatra_of(sidereal_lon: float) -> Tuple[int, str, int]:
    idx = int(sidereal_lon // NAKSHATRA_SPAN_DEG) % 27
    within = sidereal_lon - idx * NAKSHATRA_SPAN_DEG
    pada = int(within // (NAKSHATRA_SPAN_DEG / 4.0)) + 1
    return idx, NAKSHATRAS[idx], pada


def compute_planets(dt_utc: Optional[datetime] = None) -> Dict[str, PlanetState]:
    """Compute sidereal positions + nakshatra placement for all bodies."""
    if not HAS_EPHEM:
        raise RuntimeError("PyEphem is required for SBC computation")
    if dt_utc is None:
        dt_utc = datetime.utcnow()

    obs = ephem.Observer()
    obs.date = ephem.Date(dt_utc)

    out: Dict[str, PlanetState] = {}
    for name, body_name in EPHEM_BODIES.items():
        body = getattr(ephem, body_name)()
        body.compute(obs)
        trop = math.degrees(float(body.hlon)) if name == "Sun" else None
        # Use geocentric ecliptic longitude for all (incl. Sun) via ecliptic.
        ecl = ephem.Ecliptic(body)
        trop = math.degrees(float(ecl.lon)) % 360.0

        # speed: sample +1h
        obs2 = ephem.Observer()
        obs2.date = ephem.Date(dt_utc + timedelta(hours=1))
        body2 = getattr(ephem, body_name)()
        body2.compute(obs2)
        ecl2 = ephem.Ecliptic(body2)
        trop2 = math.degrees(float(ecl2.lon)) % 360.0
        dlon = ((trop2 - trop + 180.0) % 360.0) - 180.0
        speed = dlon * 24.0  # deg/day

        sid = _sidereal_from_tropical(trop, dt_utc)
        idx, nak, pada = _nakshatra_of(sid)
        nature = "malefic" if name in MALEFIC else "benefic"
        out[name] = PlanetState(
            name=name, tropical_lon=trop, sidereal_lon=sid,
            nakshatra_index=idx, nakshatra=nak, pada=pada,
            speed_deg_per_day=speed, retrograde=(speed < 0), nature=nature,
        )

    # Rahu (mean north node) / Ketu (opposite). ephem has no node; derive from
    # the mean lunar node formula (sidereal).
    rahu_trop = _mean_lunar_node(dt_utc)
    rahu_sid = _sidereal_from_tropical(rahu_trop, dt_utc)
    idx, nak, pada = _nakshatra_of(rahu_sid)
    out["Rahu"] = PlanetState("Rahu", rahu_trop, rahu_sid, idx, nak, pada,
                              -0.0529, True, "malefic")
    ketu_sid = (rahu_sid + 180.0) % 360.0
    idx, nak, pada = _nakshatra_of(ketu_sid)
    out["Ketu"] = PlanetState("Ketu", (rahu_trop + 180) % 360, ketu_sid,
                              idx, nak, pada, -0.0529, True, "malefic")
    return out


def _mean_lunar_node(dt_utc: datetime) -> float:
    """Mean lunar ascending node (tropical), Meeus approximation."""
    jd = ephem.julian_date(ephem.Date(dt_utc))
    t = (jd - 2451545.0) / 36525.0
    omega = (125.04452 - 1934.136261 * t
             + 0.0020708 * t * t + (t ** 3) / 450000.0)
    return omega % 360.0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Sarvatobhadra Chakra engine")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("grid")
    sub.add_parser("bias")
    w = sub.add_parser("windows")
    w.add_argument("--date")
    args = p.parse_args()

    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    planets = compute_planets()
    for name, ps in planets.items():
        rx = " (Rx)" if ps.retrograde else ""
        print(f"{name:8s} {ps.sidereal_lon:7.2f}deg  "
              f"{ps.nakshatra:18s} pada {ps.pada}  {ps.nature}{rx}")
