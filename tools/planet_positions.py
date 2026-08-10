#!/usr/bin/env python3
"""planet_positions.py — selectable planetary longitudes, declinations and paths.

The offline equivalent of the data layer in "Path of the Planets
[BlueprintResearch]" (see ``sources/BlueprintResearch-Path-of-the-Planets-Pine``),
built because that indicator's whole output is computable locally from `ephem` —
the same finding that produced ``panchang.py``. No vendor, no API, no rate limit.

**Per-planet selection is the point of the API.** Every entry point takes a
`bodies=` list; the `PLANETS` registry is the selection surface, so a UI can
render a checkbox per planet and pass the chosen subset straight through.

    positions(bodies=["Mars", "Saturn"])          # just those two
    path("Jupiter", start, end, step_days=7)      # a time series to plot
    out_of_bounds(bodies=["Moon", "Mars"])        # declination beyond the limit

What this covers that the rest of the repo did not
--------------------------------------------------
Audited 2026-08-09, before writing this:

* **Declination: zero occurrences repo-wide.** Nothing computed it, despite
  ``concepts/Out-of-Bounds-Planets`` being an entirely declination-based concept.
* **Heliocentric: zero occurrences.** Nothing computed it.
* **Outer planets:** Uranus/Neptune/Pluto existed only as *orbital-period
  constants* in `financial_astrology_methods.py` (84.01 / 164.79 / 247.94 years),
  never as positions.
* **Planetary longitude** was either parsed from an AstroHora CSV export
  (`astrohora_loader.py`) or computed only for the Moon, for nakshatra
  (`panchang.py`). Nothing computed a general planetary longitude.

Conventions, inherited deliberately from `panchang.py`
------------------------------------------------------
* **Ecliptic longitude is taken at the epoch OF DATE** (`epoch=` on both
  `compute()` and `Ecliptic`). Omitting it silently leaves the precession since
  J2000 in the answer — ~0.36 deg by 2026 — which is the bug that put a pada
  boundary 44 minutes late during the panchang work. It returns plausible wrong
  numbers, not errors.
* **Timestamps are tz-aware IST**, never naive. `ephem.localtime` is never used:
  it converts to the *machine's* timezone, which on this host is US Eastern.
* **Sidereal longitude reuses `panchang._lahiri_ayanamsa`** rather than
  re-deriving it, so the two modules cannot drift apart on ayanamsa.

Nothing here is a signal. These are ephemeris facts. The repo's only measured
astro findings to date are nulls — see ``analyses/FA-2-Rahu-Kaal-Measured``.

Run `python tools/planet_positions.py` for a positions table.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Any, Iterable, NamedTuple

import ephem

from panchang import IST, _lahiri_ayanamsa, _to_ephem

DEG = 180.0 / math.pi

#: Obliquity of the ecliptic — the Sun's maximum declination. A body beyond this
#: is "out of bounds" (``concepts/Out-of-Bounds-Planets``).
OOB_LIMIT = 23.4392911


class Body(NamedTuple):
    name: str
    factory: Any
    symbol: str
    colour: str          # matches the Pine script's palette, for UI parity
    heliocentric: bool   # Sun has no meaningful heliocentric position of its own


#: The selection surface. A UI renders one row per entry; callers pass names.
PLANETS: tuple[Body, ...] = (
    Body("Sun",     ephem.Sun,     "☉", "#FFD700", False),
    Body("Moon",    ephem.Moon,    "☽", "#E0E0E0", False),
    Body("Mercury", ephem.Mercury, "☿", "#00BFFF", True),
    Body("Venus",   ephem.Venus,   "♀", "#FF69B4", True),
    Body("Mars",    ephem.Mars,    "♂", "#FF4500", True),
    Body("Jupiter", ephem.Jupiter, "♃", "#FFA500", True),
    Body("Saturn",  ephem.Saturn,  "♄", "#DAA520", True),
    Body("Uranus",  ephem.Uranus,  "⛢", "#00FFFF", True),
    Body("Neptune", ephem.Neptune, "♆", "#9370DB", True),
    Body("Pluto",   ephem.Pluto,   "♇", "#FF00FF", True),
)

BY_NAME: dict[str, Body] = {b.name: b for b in PLANETS}

ZODIAC = ("♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓")
ZODIAC_NAMES = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
                "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")


def resolve(bodies: Iterable[str] | None) -> list[Body]:
    """Names -> Body records. `None` means all. Raises on an unknown name.

    Deliberately strict: a typo'd planet name silently returning nothing would
    look identical to "that planet has no data", which is the class of silent
    failure this repo keeps getting bitten by.
    """
    if bodies is None:
        return list(PLANETS)
    out = []
    for n in bodies:
        key = str(n).strip().capitalize()
        if key not in BY_NAME:
            raise KeyError(f"unknown body {n!r}; choose from {sorted(BY_NAME)}")
        out.append(BY_NAME[key])
    return out


def zodiac_of(longitude_deg: float) -> dict[str, Any]:
    """Sign, index and degrees-within-sign for an ecliptic longitude."""
    norm = longitude_deg % 360.0
    idx = int(norm // 30)
    return {"sign": ZODIAC[idx], "sign_name": ZODIAC_NAMES[idx],
            "degrees_in_sign": norm - idx * 30}


def _retrograde(body: Body, when: dt.datetime) -> bool:
    """Is the body retrograde? Finite difference on ecliptic longitude ±6h."""
    def lon(t: dt.datetime) -> float:
        e = _to_ephem(t)
        b = body.factory()
        b.compute(e, epoch=e)
        return float(ephem.Ecliptic(b, epoch=e).lon)
    before, after = lon(when - dt.timedelta(hours=6)), lon(when + dt.timedelta(hours=6))
    delta = (after - before + math.pi) % (2 * math.pi) - math.pi
    return delta < 0


def position(body: str | Body, when: dt.datetime | None = None) -> dict[str, Any]:
    """Everything the Pine indicator plots, for one body at one instant."""
    b = body if isinstance(body, Body) else BY_NAME[str(body).capitalize()]
    when = when or dt.datetime.now(IST)
    if when.tzinfo is None:
        when = when.replace(tzinfo=IST)

    e = _to_ephem(when)
    obj = b.factory()
    obj.compute(e, epoch=e)                      # epoch= is load-bearing

    geo_lon = float(ephem.Ecliptic(obj, epoch=e).lon) * DEG % 360.0
    dec = float(obj.dec) * DEG
    sidereal = (geo_lon - _lahiri_ayanamsa(when)) % 360.0

    helio_lon = helio_lat = None
    if b.heliocentric:
        try:
            helio_lon = float(obj.hlon) * DEG % 360.0
            helio_lat = float(obj.hlat) * DEG
        except AttributeError:                   # not all bodies expose it
            pass

    return {
        "body": b.name, "symbol": b.symbol, "colour": b.colour, "when": when,
        "geo_longitude": geo_lon,
        "sidereal_longitude": sidereal,
        "declination": dec,
        "out_of_bounds": abs(dec) > OOB_LIMIT,
        "helio_longitude": helio_lon,
        "helio_latitude": helio_lat,
        "retrograde": _retrograde(b, when),
        **{f"tropical_{k}": v for k, v in zodiac_of(geo_lon).items()},
    }


def positions(when: dt.datetime | None = None,
              bodies: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Positions for the selected bodies (default: all ten)."""
    when = when or dt.datetime.now(IST)
    return [position(b, when) for b in resolve(bodies)]


def path(body: str, start: dt.datetime, end: dt.datetime, *,
         step_days: float = 1.0, field: str = "declination") -> list[tuple[dt.datetime, float]]:
    """A time series of one field for one body — the 'path' the Pine script draws.

    Works identically for past and future dates: an ephemeris is not a forecast,
    so projecting forward costs nothing and carries no uncertainty. That is the
    one respect in which an astro overlay is better-posed than a price
    projection — the *positions* are exact even though their market meaning is
    unmeasured.
    """
    if field not in ("declination", "geo_longitude", "sidereal_longitude",
                     "helio_longitude", "helio_latitude"):
        raise KeyError(f"unknown field {field!r}")
    out: list[tuple[dt.datetime, float]] = []
    t, step = start, dt.timedelta(days=step_days)
    while t <= end:
        v = position(body, t)[field]
        if v is not None:
            out.append((t, v))
        t += step
    return out


def out_of_bounds(when: dt.datetime | None = None,
                  bodies: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Bodies whose |declination| exceeds the obliquity limit.

    Makes ``concepts/Out-of-Bounds-Planets`` computable for the first time — the
    page has existed since before this module and nothing calculated it.
    """
    return [p for p in positions(when, bodies) if p["out_of_bounds"]]


def main() -> None:                                    # pragma: no cover
    now = dt.datetime.now(IST)
    print(f"Planetary positions — {now:%Y-%m-%d %H:%M} IST\n")
    hdr = (f"{'':2} {'body':<9} {'geo lon':>9} {'sidereal':>9} {'sign':<12} "
           f"{'declin':>8} {'helio lon':>10} {'R':>2} {'OOB':>4}")
    print(hdr); print("-" * len(hdr))
    for p in positions(now):
        h = f"{p['helio_longitude']:10.2f}" if p["helio_longitude"] is not None else f"{'—':>10}"
        print(f"{p['symbol']:2} {p['body']:<9} {p['geo_longitude']:9.2f} "
              f"{p['sidereal_longitude']:9.2f} "
              f"{p['tropical_sign'] + ' ' + p['tropical_sign_name']:<12} "
              f"{p['declination']:8.2f} {h} "
              f"{'R' if p['retrograde'] else '':>2} "
              f"{'OOB' if p['out_of_bounds'] else '':>4}")
    oob = out_of_bounds(now)
    print(f"\nout of bounds (|dec| > {OOB_LIMIT}°): "
          + (", ".join(f"{p['body']} {p['declination']:+.2f}°" for p in oob) or "none"))
    print("\nEphemeris facts only — no market claim. This repo's measured astro"
          "\nfindings to date are nulls (analyses/FA-2-Rahu-Kaal-Measured).")


if __name__ == "__main__":                             # pragma: no cover
    main()
