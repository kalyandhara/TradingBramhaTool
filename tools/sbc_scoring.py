#!/usr/bin/env python3
"""
sbc_scoring.py — Veda casting, market bias, sector scoring, reversal windows.

Sits on top of `sarvatobhadra_chakra.py` (planet placement) + `sbc_grid.py`
(authentic 81-cell board + geometric vedha) and turns raw nakshatra positions
into the trading-facing outputs the tool renders.

VEDA MODEL — now authentic (2026-08-16 rebuild)
-----------------------------------------------
The vedas are NO LONGER invented index offsets. Each graha casts its
vedha ray(s) geometrically across the real board, and WHICH ray it casts is
gated on its live motion state (the documented SBC rule):

    mean/normal speed -> front  (Sammukha, straight through centre)
    swift & direct    -> left   (Vaama, one diagonal)
    retrograde        -> right   (Dakshina, the other diagonal)
    Sun + Rahu + Ketu -> all three simultaneously

Vedha by benefics (Mo, Me, Ju, Ve) is favourable; by malefics
(Su, Ma, Sa, Ra, Ke) unfavourable. Everything downstream (bias, sector scores)
is a pure function of the board geometry + live positions.

See sbc_grid.py for the classical construction + sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sarvatobhadra_chakra import (
    NAKSHATRAS, NAKSHATRA_SPAN_DEG, IST_OFFSET,
    PlanetState, compute_planets, _nakshatra_of,
)
import sbc_grid as grid
import sbc_nama as nama

# Front vedha is the direct confrontation (strongest); the diagonals are
# secondary. Weights let the score reflect that hierarchy.
VEDA_WEIGHT = {"sammukha": 1.0, "vama": 0.6, "dakshina": 0.6}

# Speed thresholds (deg/day) above which a planet counts as "swift" -> casts
# the left/Vaama vedha instead of the front. Below = mean motion -> front.
FAST_THRESHOLD = {
    "Moon": 13.2, "Mercury": 1.2, "Venus": 1.2, "Mars": 0.6, "Sun": 1.0,
    "Jupiter": 0.08, "Saturn": 0.06, "Rahu": 1.0, "Ketu": 1.0,
}
CASTS_ALL = {"Sun", "Rahu", "Ketu"}

_BOARD = grid.build_board()


def _planet_directions(ps: PlanetState) -> List[str]:
    fast = abs(ps.speed_deg_per_day) > FAST_THRESHOLD.get(ps.name, 0.05)
    return grid.active_directions(ps.retrograde, fast, ps.name in CASTS_ALL)


@dataclass
class Veda:
    planet: str
    nature: str                # malefic | benefic
    veda_type: str             # sammukha | vama | dakshina
    target_index: int          # nakshatra index 0..26 (Abhijit -> -1)
    target_nakshatra: str
    weight: float


def cast_vedas(planets: Dict[str, PlanetState]) -> List[Veda]:
    """Every geometric vedha cast by every planet onto the board."""
    vedas: List[Veda] = []
    for ps in planets.values():
        dirs = _planet_directions(ps)
        hits = grid.nakshatra_vedhas(_BOARD, ps.nakshatra, dirs)
        for vtype, targets in hits.items():
            for nak in targets:
                try:
                    idx = NAKSHATRAS.index(nak)
                except ValueError:      # Abhijit — not one of the 27
                    idx = -1
                vedas.append(Veda(
                    planet=ps.name, nature=ps.nature, veda_type=vtype,
                    target_index=idx, target_nakshatra=nak,
                    weight=VEDA_WEIGHT[vtype],
                ))
    return vedas


@dataclass
class MarketBias:
    malefic_score: float
    benefic_score: float
    net: float                 # (benefic - malefic) / total, -1..+1
    label: str                 # BEARISH | BULLISH | MIXED
    malefic_count: int
    benefic_count: int


def market_bias(vedas: List[Veda]) -> MarketBias:
    mal = sum(v.weight for v in vedas if v.nature == "malefic")
    ben = sum(v.weight for v in vedas if v.nature == "benefic")
    total = mal + ben or 1.0
    net = (ben - mal) / total
    if net <= -0.15:
        label = "BEARISH"
    elif net >= 0.15:
        label = "BULLISH"
    else:
        label = "MIXED"
    return MarketBias(
        malefic_score=round(mal, 2), benefic_score=round(ben, 2),
        net=round(net, 3), label=label,
        malefic_count=sum(1 for v in vedas if v.nature == "malefic"),
        benefic_count=sum(1 for v in vedas if v.nature == "benefic"),
    )


# --- Nama-nakshatra sector mapping (via sbc_nama, first-syllable resolver) ---
# The tradeable universe scored on the board. Each resolves to a nakshatra by
# its leading sound; vedas striking that nakshatra drive the instrument score.
SECTORS: List[str] = [
    "NIFTY 50", "Bank NIFTY", "NIFTY IT", "NIFTY Auto", "NIFTY FMCG",
    "NIFTY Pharma", "NIFTY Metal", "NIFTY Energy", "Defense",
    "Gold", "Silver", "Crude Oil", "Copper", "USD/INR",
    "Bitcoin", "Ethereum",
]


@dataclass
class SectorScore:
    sector: str
    nakshatra: str
    malefic_hits: float
    benefic_hits: float
    score: float               # -1..+1
    label: str                 # BULLISH | BEARISH | NEUTRAL
    hitting_planets: List[str]


def sector_scores(vedas: List[Veda],
                  sectors: Optional[List[str]] = None) -> List[SectorScore]:
    sectors = sectors or SECTORS
    by_nak: Dict[str, List[Veda]] = {}
    for v in vedas:
        by_nak.setdefault(v.target_nakshatra, []).append(v)

    out: List[SectorScore] = []
    for sector in sectors:
        resolved = nama.resolve_nakshatra(sector)
        nak = resolved[0] if resolved else ""
        hits = by_nak.get(nak, [])
        mal = sum(v.weight for v in hits if v.nature == "malefic")
        ben = sum(v.weight for v in hits if v.nature == "benefic")
        total = mal + ben
        score = 0.0 if total == 0 else (ben - mal) / total
        if score <= -0.2:
            label = "BEARISH"
        elif score >= 0.2:
            label = "BULLISH"
        else:
            label = "NEUTRAL"
        out.append(SectorScore(
            sector=sector, nakshatra=nak or "?",
            malefic_hits=round(mal, 2), benefic_hits=round(ben, 2),
            score=round(score, 3), label=label,
            hitting_planets=sorted({v.planet for v in hits}),
        ))
    out.sort(key=lambda s: s.score, reverse=True)
    return out


# --- Reversal windows -------------------------------------------------------
# The Moon crosses a nakshatra (or pada) boundary -> the vedas it casts shift.
# That transition is a candidate intraday reversal window.
@dataclass
class ReversalWindow:
    center_ist: datetime
    start_ist: datetime
    end_ist: datetime
    from_nakshatra: str
    to_nakshatra: str
    tolerance_min: int


def _moon_pada_key(t_utc: datetime) -> Tuple[int, int, str]:
    moon = compute_planets(t_utc)["Moon"]
    return moon.nakshatra_index, moon.pada, moon.nakshatra


def moon_reversal_windows(day: date, tolerance_min: int = 10,
                          scan_hours: int = 24,
                          granularity: str = "pada") -> List[ReversalWindow]:
    """Moon boundary crossings within `day` (IST) as reversal windows.

    granularity='nakshatra' -> ~1 window/day; 'pada' -> ~4 windows/day.
    """
    start_ist = datetime(day.year, day.month, day.day, 0, 0)
    windows: List[ReversalWindow] = []
    step = timedelta(minutes=5)
    prev_idx: Optional[int] = None
    prev_pada: Optional[int] = None
    prev_nak = ""
    t = start_ist
    end = start_ist + timedelta(hours=scan_hours)
    while t <= end:
        idx, pada, nak = _moon_pada_key(t - IST_OFFSET)
        if prev_idx is not None:
            crossed_nak = idx != prev_idx
            crossed_pada = crossed_nak or pada != prev_pada
            hit = crossed_nak if granularity == "nakshatra" else crossed_pada
            if hit:
                center = t - step / 2
                windows.append(ReversalWindow(
                    center_ist=center,
                    start_ist=center - timedelta(minutes=tolerance_min),
                    end_ist=center + timedelta(minutes=tolerance_min),
                    from_nakshatra=(prev_nak if crossed_nak
                                    else f"{nak} p{prev_pada}"),
                    to_nakshatra=(nak if crossed_nak else f"{nak} p{pada}"),
                    tolerance_min=tolerance_min,
                ))
        prev_idx, prev_pada, prev_nak = idx, pada, nak
        t += step
    return windows


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    planets = compute_planets()
    vedas = cast_vedas(planets)
    bias = market_bias(vedas)
    print(f"MARKET BIAS: {bias.label}  net={bias.net:+.3f}  "
          f"(malefic {bias.malefic_score} / benefic {bias.benefic_score})")
    print("\nSECTOR SCORES (nama-nakshatra)")
    for s in sector_scores(vedas):
        pl = " ".join(s.hitting_planets)
        print(f"  {s.sector:14s} {s.nakshatra:16s} {s.label:8s} "
              f"{s.score:+.2f}  [{pl}]")
    print("\nREVERSAL WINDOWS (today IST)")
    for w in moon_reversal_windows(date.today()):
        print(f"  {w.start_ist:%H:%M}-{w.end_ist:%H:%M}  "
              f"{w.from_nakshatra} -> {w.to_nakshatra}")
