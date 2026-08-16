#!/usr/bin/env python3
"""
sbc_aspects.py — Vedic graha drishti (planetary aspects) for the Aspect Map.

The SBC chakra shows nakshatra *vedhas* (cell-geometry piercing). This module
provides the complementary classical layer: *graha drishti* — which planet
aspects which, by whole-sign distance.

Drishti rules (full aspects), sign distance counted inclusively from the
planet's own sign (1 = same sign, 7 = opposite):

  * every planet          -> 7th   (opposition, direct confrontation)
  * Mars                  -> 4, 7, 8
  * Jupiter               -> 5, 7, 9   (the benefic "wisdom" trines)
  * Saturn                -> 3, 7, 10
  * Rahu / Ketu           -> 5, 7, 9   (common convention; school-dependent)
  * Sun/Moon/Mercury/Venus-> 7 only

A malefic's aspect applies pressure; a benefic's aspect gives support. This is
sign-based Jyotish drishti, not degree-orb Western aspects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from sarvatobhadra_chakra import PlanetState

# special full-aspect sign distances per planet (7th implied for all)
SPECIAL_DRISHTI: Dict[str, List[int]] = {
    "Mars": [4, 8],
    "Jupiter": [5, 9],
    "Saturn": [3, 10],
    "Rahu": [5, 9],
    "Ketu": [5, 9],
}

RASHIS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
          "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

ASPECT_LABEL = {3: "3rd", 4: "4th", 5: "5th", 7: "7th", 8: "8th", 9: "9th",
                10: "10th"}


@dataclass
class Aspect:
    source: str
    target: str
    distance: int              # sign distance 1..12
    kind: str                  # e.g. "7th", "Mars 8th"
    nature: str                # malefic | benefic (of the source)
    special: bool              # True if not the plain 7th


def _rashi_index(sidereal_lon: float) -> int:
    return int(sidereal_lon // 30.0) % 12


def aspect_distances(planet: str) -> List[int]:
    return sorted(set([7] + SPECIAL_DRISHTI.get(planet, [])))


def compute_aspects(planets: Dict[str, PlanetState]) -> List[Aspect]:
    """All graha-drishti aspects between the placed planets."""
    rashi = {n: _rashi_index(ps.sidereal_lon) for n, ps in planets.items()}
    out: List[Aspect] = []
    for src, ps in planets.items():
        dists = aspect_distances(src)
        for tgt, tps in planets.items():
            if tgt == src:
                continue
            offset = ((rashi[tgt] - rashi[src]) % 12) + 1   # 1..12
            if offset in dists:
                special = offset != 7
                kind = (f"{src} {ASPECT_LABEL[offset]}" if special
                        else "7th")
                out.append(Aspect(source=src, target=tgt, distance=offset,
                                  kind=kind, nature=ps.nature, special=special))
    return out


def aspect_summary(planets: Dict[str, PlanetState]) -> Dict[str, List[str]]:
    """Per-planet list of 'Target (kind)' aspect strings, for a table."""
    asp = compute_aspects(planets)
    by_src: Dict[str, List[str]] = {n: [] for n in planets}
    for a in asp:
        by_src[a.source].append(f"{a.target} ({a.kind})")
    return by_src


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    from sarvatobhadra_chakra import compute_planets
    p = compute_planets()
    print("GRAHA DRISHTI (aspects between placed planets):")
    for src, targets in aspect_summary(p).items():
        print(f"  {src:8s} -> {', '.join(targets) or '(none)'}")
