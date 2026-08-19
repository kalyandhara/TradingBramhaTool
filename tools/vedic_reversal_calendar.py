#!/usr/bin/env python3
"""
vedic_reversal_calendar.py — structured spine of the third-party
"Vedic Astro Market Reversal Calendar 2026-2027" PDF, plus a forward-window view.

WHY THIS EXISTS
---------------
The PDF is prose. This module turns its major, dated events (eclipses, nodal
ingresses, retrograde stations, cluster windows, standing backdrops) into a small
deterministic dataset so the SBC dashboard can render a *forward-looking* reversal
card for any "today", instead of pasting a static image.

HONESTY
-------
These are the CALENDAR'S claims, not validated signals. Our own 18-year event study
(`sbc_vedha_backtest.py`) found SBC daily vedha has no timing edge on NIFTY. This
calendar uses a broader event set, none of it validated here. The card built on this
data is an explicitly HYPOTHETICAL watch-flag, never a trade signal. Direction is not
implied; price + risk rules decide. Source self-disclaims as speculative.

Distinct from `reversal_calendar.py` (the yoga+lunar SQLite builder) — different data,
different purpose.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class AstroEvent:
    day: date
    kind: str                 # solar_eclipse|lunar_eclipse|station|ingress|cluster|state
    title: str
    place: str                # sign / nakshatra
    sectors: Tuple[str, ...]
    bias: str                 # bearish|bullish|mixed
    tier: int                 # 1 = major catalyst, 2 = secondary
    window: Optional[Tuple[date, date]]  # watch window (or envelope for cluster/state)
    note: str = ""


def _d(s: str) -> date:
    return date.fromisoformat(s)


# --- The calendar's spine (2026-2027) --------------------------------------- #
# Pinpoint catalysts (tier 1 = eclipses / major stations)
EVENTS: List[AstroEvent] = [
    # 2026 eclipses
    AstroEvent(_d("2026-02-17"), "solar_eclipse", "Annular Solar Eclipse",
               "Aquarius / Shatabhisha", ("IT", "Pharma", "PSU Banks"),
               "bearish", 1, (_d("2026-02-14"), _d("2026-02-20")),
               "Major trigger near Rahu; tech/pharma/PSU reversal possible."),
    AstroEvent(_d("2026-03-03"), "lunar_eclipse", "Total Lunar Eclipse",
               "Leo / Magha", ("Gold/MCX", "PSU Banks", "Metals"),
               "bearish", 1, (_d("2026-02-28"), _d("2026-03-06")),
               "Metals & gold reversal zone; PSU bank stress near Ketu."),
    AstroEvent(_d("2026-08-12"), "solar_eclipse", "Total Solar Eclipse",
               "Leo-Cancer cusp / Ashlesha (near Ketu)",
               ("Nifty Bank", "Large Cap", "Real Estate"),
               "bearish", 1, (_d("2026-08-09"), _d("2026-08-16")),
               "Calendar's #1 watch date of 2026 — highest-impact single event; "
               "expect 5%+ index moves."),
    AstroEvent(_d("2026-08-28"), "lunar_eclipse", "Partial Lunar Eclipse",
               "Aquarius / Dhanishtha (Rahu phase)",
               ("Metals", "PSU Banks", "Defense"),
               "bearish", 1, (_d("2026-08-25"), _d("2026-08-31")),
               "Metals & PSU correction adds pressure."),
    AstroEvent(_d("2026-11-13"), "station", "Double Direct — Mercury & Venus",
               "same-day direct stations",
               ("Banking", "Gold", "Auto", "FMCG"),
               "bullish", 1, (_d("2026-11-11"), _d("2026-11-15")),
               "Rare double-direct station — explosive bullish reversal / best "
               "Q4 re-entry window; banking & gold primary recovery targets."),
    # 2027 eclipses
    AstroEvent(_d("2027-02-06"), "solar_eclipse", "Annular Solar Eclipse",
               "Capricorn / Dhanishtha", ("PSU Banks", "Metals", "Infrastructure"),
               "bearish", 1, (_d("2027-02-03"), _d("2027-02-09")), "Near Rahu."),
    AstroEvent(_d("2027-02-20"), "lunar_eclipse", "Penumbral Lunar Eclipse",
               "Leo / Purva Phalguni", ("Large Cap", "Auto", "Luxury"),
               "mixed", 2, (_d("2027-02-18"), _d("2027-02-22")), "Residual Ketu."),
    AstroEvent(_d("2027-07-18"), "lunar_eclipse", "Penumbral Lunar Eclipse",
               "Sagittarius / Purva Ashadha", ("Commodities", "Oil", "Gold"),
               "mixed", 2, (_d("2027-07-16"), _d("2027-07-20")), "Far from nodes."),
    AstroEvent(_d("2027-08-02"), "solar_eclipse", "Total Solar Eclipse (conjunct Ketu)",
               "Cancer / Pushya-Ashlesha", ("Nifty Bank", "FMCG", "Real Estate"),
               "bearish", 1, (_d("2027-07-30"), _d("2027-08-06")),
               "Most technically significant event of 2027 — eclipse on Ketu = "
               "sudden sharp correction in banking & FMCG."),
    AstroEvent(_d("2027-08-17"), "lunar_eclipse", "Penumbral Lunar Eclipse",
               "Aquarius / Shatabhisha", ("IT", "PSU", "Airlines"),
               "mixed", 2, (_d("2027-08-15"), _d("2027-08-19")), "Near Rahu zone."),

    # Cluster envelopes (tier 1 windows)
    AstroEvent(_d("2026-07-26"), "cluster", "Cluster B — heaviest stack of 2026",
               "Saturn Rx + Jupiter combust + 2 eclipses",
               ("Nifty 50", "Nifty Bank", "Real Estate", "FMCG"),
               "bearish", 1, (_d("2026-07-26"), _d("2026-08-28")),
               "4-5 weeks extreme volatility; calendar cites potential 5-10% "
               "index correction."),
    AstroEvent(_d("2026-10-03"), "cluster", "Cluster C",
               "Venus Rx + Mercury Rx (Scorpio)",
               ("Nifty 50", "Auto", "Luxury"),
               "bearish", 2, (_d("2026-10-03"), _d("2026-11-29")),
               "8-week retrograde cluster into the Nov 13 double-direct turn."),
    AstroEvent(_d("2027-06-03"), "cluster", "Cluster F — critical 2027 cluster",
               "Mercury Rx + Total Solar Eclipse on Ketu + Saturn Rx",
               ("Nifty Bank", "Real Estate", "Infrastructure"),
               "bearish", 1, (_d("2027-06-03"), _d("2027-08-17")),
               "10 weeks; peak stress Aug 2 +/-5 days."),

    # Standing backdrops (states active over a span)
    AstroEvent(_d("2026-01-01"), "state", "Saturn in Pisces (full year)",
               "Uttara Bhadrapada / Revati",
               ("Banking", "Infrastructure", "Metals"),
               "bearish", 2, (_d("2026-01-01"), _d("2026-12-31")),
               "Karmic pressure on the financial sector; debt-restructuring themes."),
    AstroEvent(_d("2026-07-14"), "state", "Jupiter Combust",
               "near Sun", ("Large Cap", "Banking"),
               "bearish", 2, (_d("2026-07-14"), _d("2026-08-12")),
               "Benefic support suppressed by Sun proximity."),
    AstroEvent(_d("2026-08-03"), "state", "Rahu enters Dhanishtha",
               "Dhanishtha (Aquarius)", ("Metals", "Mining"),
               "bearish", 2, (_d("2026-08-03"), _d("2026-12-05")),
               "Amplified metals & mining volatility."),
]

# Month bias table (calendar's stated monthly lean) where documented.
MONTH_BIAS = {
    (2026, 8): ("STRONGLY BEARISH", "Double-eclipse month — the calendar's most "
                                    "critical month of 2026."),
    (2026, 9): ("CONSOLIDATION / BEARISH", "No major triggers; Saturn Rx keeps "
                                           "pressure on."),
    (2026, 11): ("BULLISH REVERSAL", "Nov 13 double-direct station — best Q4 "
                                     "re-entry window."),
    (2027, 8): ("STRONGLY BEARISH", "Aug 2 Total Solar Eclipse conjunct Ketu."),
}


def _overlaps(w: Optional[Tuple[date, date]], a: date, b: date) -> bool:
    return w is not None and w[0] <= b and w[1] >= a


def forward_window_view(today: date, days: int = 7) -> dict:
    """The calendar's forward-`days` read from `today` (inclusive window)."""
    end = today + timedelta(days=days)
    catalysts = [e for e in EVENTS if e.tier == 1
                 and e.kind in ("solar_eclipse", "lunar_eclipse", "station")]

    in_window = sorted(
        [e for e in EVENTS
         if e.kind in ("solar_eclipse", "lunar_eclipse", "station")
         and today <= e.day <= end],
        key=lambda e: e.day)
    prev_cat = max((e for e in catalysts if e.day < today),
                   key=lambda e: e.day, default=None)
    next_cat = min((e for e in catalysts if e.day >= today),
                   key=lambda e: e.day, default=None)
    clusters = [e for e in EVENTS if e.kind == "cluster"
                and _overlaps(e.window, today, today)]
    states = [e for e in EVENTS if e.kind == "state"
              and _overlaps(e.window, today, today)]

    # bias: documented month bias, else active cluster bias, else mixed
    mb = MONTH_BIAS.get((today.year, today.month))
    if mb:
        bias_label, bias_note = mb
    elif clusters:
        bias_label = clusters[0].bias.upper()
        bias_note = clusters[0].title
    else:
        bias_label, bias_note = "MIXED / NO MAJOR TRIGGER", ""

    # sectors in focus: union from bracketing catalysts + active states/clusters
    sectors: List[str] = []
    for e in [prev_cat, next_cat, *clusters, *states]:
        if e:
            for s in e.sectors:
                if s not in sectors:
                    sectors.append(s)

    return {
        "today": today,
        "window": (today, end),
        "in_window": in_window,        # pinpoint events inside the forward window
        "prev_catalyst": prev_cat,     # last major catalyst before today
        "next_catalyst": next_cat,     # next major catalyst on/after today
        "clusters": clusters,          # active envelope(s)
        "states": states,              # standing backdrops today
        "bias_label": bias_label,
        "bias_note": bias_note,
        "sectors": sectors[:6],
    }


def _fmt(e: AstroEvent) -> str:
    return f"{e.day:%d %b %Y} · {e.title} ({e.place})"


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    t = date.today()
    if len(sys.argv) > 1:
        t = date.fromisoformat(sys.argv[1])
    v = forward_window_view(t)
    print(f"Forward window {v['window'][0]:%d %b}–{v['window'][1]:%d %b %Y}")
    print(f"Bias: {v['bias_label']} — {v['bias_note']}")
    print(f"In-window pinpoint events: "
          f"{[_fmt(e) for e in v['in_window']] or 'none'}")
    print(f"Prev catalyst: {_fmt(v['prev_catalyst']) if v['prev_catalyst'] else '-'}")
    print(f"Next catalyst: {_fmt(v['next_catalyst']) if v['next_catalyst'] else '-'}")
    print(f"Active clusters: {[e.title for e in v['clusters']] or 'none'}")
    print(f"Backdrop states: {[e.title for e in v['states']] or 'none'}")
    print(f"Sectors: {v['sectors']}")
