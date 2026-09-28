#!/usr/bin/env python3
"""
sbc_forecast.py — forward-looking SBC views ported from the SBC_Tool project.

Three features, rebuilt on THIS repo's engine (sarvatobhadra_chakra ephem
positions + sbc_scoring geometric vedhas + sbc_panchang) rather than copying
SBC_Tool's swisseph/confluence stack:

* monthly_heatmap   — sector x day net vedha for the next N days, plus a lunar
                      timing strip (Purnima/Amavasya/Ekadashi/Ashtami) and
                      whether Bhadra falls inside market hours.
                      (SBC_Tool: sbc/monthly_heatmap.py)
* crash_analysis    — the Jupiter/Saturn/Ketu/Mars angle signatures and their
                      weighted score. (SBC_Tool: sbc/crash_analyzer.py)
  crash_backtest    — the same signatures on the historical crash dates AND on
                      every ordinary day, so a "hit" can be compared with how
                      often the signature is simply on. SBC_Tool only reported
                      the crash-date side (3/7), which cannot show an edge.
* weekly_commentary — a plain-text week-ahead synthesis of the above.
                      (SBC_Tool: sbc/weekly_commentary.py)

The sector net is the same number the "Broad Vedha Pressure" panel shows
(benefic weight - malefic weight on the sector's nama-nakshatra, clamped to
+/-6), so the heatmap's today column matches that panel.

Everything here is a watch calendar. The daily vedha backtest was a clean
null (reports/sbc_vedha_*), and nothing in this module changes that.

Crash signatures, measured 2026-09-27: on SBC_Tool's own 7 crash dates a
score >= 35 flags 6/7 against 9% of all weeks since 1990 — but those dates are
the ones the signatures were picked from. On peaks nobody chose (every
250-day high followed by a >=10% fall within 120 sessions) it flags 0/14 on
^NSEI (2008-2026) and 2/14 on ^GSPC (1991-2026, base 9%). In-sample fit, no
out-of-sample edge. OOS_RESULT below is what the dashboard quotes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

from sarvatobhadra_chakra import IST_OFFSET, NAKSHATRAS, compute_planets
import sbc_nama as nama
import sbc_panchang as sbcp
import sbc_scoring as sbcs

# --- shared helpers ---------------------------------------------------------

NET_CLAMP = 6.0
MARKET_OPEN, MARKET_CLOSE = time(9, 15), time(15, 30)


def _planets_at(day: date, at: time = time(12, 0)):
    """Positions at a given IST clock time on `day`."""
    return compute_planets(datetime.combine(day, at) - IST_OFFSET)


def _angle(a: float, b: float) -> float:
    """Shortest separation between two longitudes, 0..180."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def sector_nets(vedas, sectors: Optional[List[str]] = None) -> Dict[str, float]:
    """Net vedha per sector (benefic - malefic weight), clamped to +/-6.

    Same arithmetic as the dashboard's Broad Vedha Pressure panel.
    """
    by_nak: Dict[str, list] = {}
    for v in vedas:
        by_nak.setdefault(v.target_nakshatra, []).append(v)
    out = {}
    for sector in sectors or sbcs.SECTORS:
        r = nama.resolve_nakshatra(sector)
        hits = by_nak.get(r[0] if r else "", [])
        ben = sum(v.weight for v in hits if v.nature == "benefic")
        mal = sum(v.weight for v in hits if v.nature == "malefic")
        out[sector] = round(max(-NET_CLAMP, min(NET_CLAMP, ben - mal)), 2)
    return out


# --- 1. monthly heatmap -----------------------------------------------------

def lunar_events(tithi: int) -> List[str]:
    """Lunar-timing labels for a tithi number (1..30)."""
    ev = []
    if tithi == 15:
        ev.append("Purnima")
    elif tithi == 30:
        ev.append("Amavasya")
    elif tithi in (14, 16):
        ev.append("Full-moon window")
    elif tithi in (29, 1):
        ev.append("New-moon window")
    if tithi in (11, 26):
        ev.append("Ekadashi")
    if tithi in (8, 23):
        ev.append("Ashtami")
    return ev


def session_bhadra(day: date, step_min: int = 15) -> Optional[str]:
    """'HH:MM-HH:MM' if Bhadra (Vishti karana) overlaps market hours, else None."""
    t = datetime.combine(day, MARKET_OPEN)
    end = datetime.combine(day, MARKET_CLOSE)
    first = last = None
    while t <= end:
        if sbcp.compute_panchang(t).bhadra_active:
            first = first or t
            last = t
        t += timedelta(minutes=step_min)
    if first is None:
        return None
    return f"{first:%H:%M}-{last:%H:%M}"


@dataclass
class HeatmapDay:
    day: date
    nets: Dict[str, float]
    bias_label: str
    bias_net: float
    tithi: int
    tithi_name: str
    moon_nakshatra: str
    events: List[str]
    bhadra: Optional[str]


def monthly_heatmap(start: Optional[date] = None, days: int = 30,
                    trading_days_only: bool = True) -> List[HeatmapDay]:
    """Sector x day net vedha + lunar strip, evaluated at 12:00 IST each day."""
    start = start or (datetime.utcnow() + IST_OFFSET).date()
    out: List[HeatmapDay] = []
    for i in range(days):
        d = start + timedelta(days=i)
        if trading_days_only and d.weekday() >= 5:
            continue
        planets = _planets_at(d)
        vedas = sbcs.cast_vedas(planets)
        bias = sbcs.market_bias(vedas)
        p = sbcp.compute_panchang(datetime.combine(d, time(12, 0)))
        out.append(HeatmapDay(
            day=d, nets=sector_nets(vedas), bias_label=bias.label,
            bias_net=bias.net, tithi=p.tithi_num, tithi_name=p.tithi_name,
            moon_nakshatra=p.nakshatra, events=lunar_events(p.tithi_num),
            bhadra=session_bhadra(d),
        ))
    return out


# --- 2. crash signatures ----------------------------------------------------

KETU_NAKSHATRAS = {"Ashwini", "Magha", "Mula"}
JS_ORB = 15.0          # Jupiter-Saturn aspect orb (SBC_Tool value)
NODE_ORB = 10.0        # Mars/Saturn conjunct Ketu
PUSHYA_MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}

# name -> (weight, description). Weights are SBC_Tool's, derived by eye from
# 8 crash dates; they are priors, not fitted values.
CRASH_SIGNATURES = {
    "jupiter_ketu_nakshatra": (0.35, "Jupiter in a Ketu-ruled nakshatra (Ashwini/Magha/Mula)"),
    "jupiter_saturn_conjunction": (0.30, "Jupiter-Saturn conjunction (0°±15°)"),
    "jupiter_saturn_opposition": (0.20, "Jupiter-Saturn opposition (180°±15°)"),
    "jupiter_saturn_trine": (0.15, "Jupiter-Saturn trine (120°±15°)"),
    "mars_ketu_conjunction": (0.15, "Mars conjunct Ketu (0°±10°)"),
    "saturn_ketu_conjunction": (0.08, "Saturn conjunct Ketu (0°±10°)"),
    "pushya_malefic_cluster": (0.10, "Two or more malefics in Pushya"),
}

OOS_RESULT = ("Out of sample it flagged 0 of 14 NIFTY peaks before a 10% fall "
              "(2008–2026) and 2 of 14 S&P 500 peaks (base rate 9%) — the "
              "in-sample hits come from picking signatures off the same dates.")

CRASH_BANDS = [(60, "CRASH RISK"), (35, "CORRECTION RISK"),
               (20, "ELEVATED"), (0, "NORMAL")]

HISTORICAL_CRASHES = [
    ("Black Monday", date(1987, 10, 19)),
    ("Harshad Mehta", date(1992, 4, 28)),
    ("Dot-com peak", date(2000, 3, 10)),
    ("2008 peak", date(2008, 1, 8)),
    ("Lehman", date(2008, 9, 15)),
    ("2011 correction", date(2011, 11, 7)),
    ("COVID", date(2020, 2, 19)),
]


def crash_signatures(planets) -> Dict[str, tuple]:
    """{signature: (active, detail)} from raw sidereal positions."""
    ju, sa = planets["Jupiter"], planets["Saturn"]
    ma, ke = planets["Mars"], planets["Ketu"]
    js = _angle(ju.sidereal_lon, sa.sidereal_lon)
    mk = _angle(ma.sidereal_lon, ke.sidereal_lon)
    sk = _angle(sa.sidereal_lon, ke.sidereal_lon)
    pushya = [n for n, p in planets.items()
              if p.nakshatra == "Pushya" and n in PUSHYA_MALEFICS]
    return {
        "jupiter_ketu_nakshatra": (ju.nakshatra in KETU_NAKSHATRAS,
                                   f"Jupiter in {ju.nakshatra}"),
        "jupiter_saturn_conjunction": (js <= JS_ORB, f"Jup-Sat {js:.1f}°"),
        "jupiter_saturn_opposition": (abs(js - 180) <= JS_ORB, f"Jup-Sat {js:.1f}°"),
        "jupiter_saturn_trine": (abs(js - 120) <= JS_ORB, f"Jup-Sat {js:.1f}°"),
        "mars_ketu_conjunction": (mk <= NODE_ORB, f"Mars-Ketu {mk:.1f}°"),
        "saturn_ketu_conjunction": (sk <= NODE_ORB, f"Sat-Ketu {sk:.1f}°"),
        "pushya_malefic_cluster": (len(pushya) >= 2,
                                   "Pushya: " + (", ".join(pushya) or "none")),
    }


@dataclass
class CrashAnalysis:
    day: date
    score: float
    band: str
    signatures: Dict[str, tuple] = field(default_factory=dict)

    @property
    def active(self) -> List[str]:
        return [k for k, (on, _) in self.signatures.items() if on]


def crash_score(sigs: Dict[str, tuple]) -> float:
    return round(sum(CRASH_SIGNATURES[k][0] * 100
                     for k, (on, _) in sigs.items() if on), 1)


def crash_band(score: float) -> str:
    return next(label for floor, label in CRASH_BANDS if score >= floor)


def crash_analysis(day: Optional[date] = None) -> CrashAnalysis:
    day = day or (datetime.utcnow() + IST_OFFSET).date()
    sigs = crash_signatures(_planets_at(day, MARKET_OPEN))
    s = crash_score(sigs)
    return CrashAnalysis(day=day, score=s, band=crash_band(s), signatures=sigs)


def crash_backtest(start: date = date(1990, 1, 1), end: Optional[date] = None,
                   step_days: int = 7, threshold: float = 35.0) -> dict:
    """Crash-date hits vs how often the same reading occurs on any day.

    A signature that is on for 40% of all weeks "catching" 3 of 7 crashes is
    what chance gives. `lift` = crash-date rate / all-days rate; ~1 means the
    signature does not single out crashes.
    """
    end = end or (datetime.utcnow() + IST_OFFSET).date()
    crash_rows = [(name, d, crash_analysis(d)) for name, d in HISTORICAL_CRASHES]

    n = 0
    base_hits = {k: 0 for k in CRASH_SIGNATURES}
    base_flag = 0
    d = start
    while d <= end:
        a = crash_analysis(d)
        n += 1
        for k in a.active:
            base_hits[k] += 1
        base_flag += a.score >= threshold
        d += timedelta(days=step_days)

    m = len(crash_rows)
    per_sig = []
    for k in CRASH_SIGNATURES:
        hit = sum(1 for _, _, a in crash_rows if k in a.active)
        base = base_hits[k] / n if n else 0.0
        per_sig.append({
            "signature": k, "crash_hits": hit, "crashes": m,
            "crash_rate": hit / m if m else 0.0, "base_rate": base,
            "lift": (hit / m) / base if base else None,
        })
    flagged = sum(1 for _, _, a in crash_rows if a.score >= threshold)
    base_rate = base_flag / n if n else 0.0
    return {
        "crashes": [{"name": nm, "date": dd, "score": a.score, "band": a.band,
                     "active": a.active} for nm, dd, a in crash_rows],
        "signatures": per_sig,
        "threshold": threshold,
        "flagged": flagged,
        "flag_rate_crash": flagged / m if m else 0.0,
        "flag_rate_all": base_rate,
        "sample_days": n,
    }


# --- 3. weekly commentary ---------------------------------------------------

def _week_ingresses(start: date, days: int = 7) -> List[str]:
    """Slow-planet nakshatra changes and retrograde stations inside the week."""
    notes = []
    prev = _planets_at(start - timedelta(days=1))
    for i in range(days):
        d = start + timedelta(days=i)
        cur = _planets_at(d)
        for name in ("Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"):
            a, b = prev[name], cur[name]
            if a.nakshatra != b.nakshatra:
                notes.append(f"{d:%a %d %b}: {name} enters {b.nakshatra}")
            if name not in ("Sun", "Rahu") and a.retrograde != b.retrograde:
                notes.append(f"{d:%a %d %b}: {name} stations "
                             f"{'retrograde' if b.retrograde else 'direct'}")
        prev = cur
    return notes


def weekly_commentary(start: Optional[date] = None) -> str:
    """Plain-text week-ahead note built from the heatmap + crash signatures."""
    today = (datetime.utcnow() + IST_OFFSET).date()
    start = start or today
    week = monthly_heatmap(start, days=7)
    crash = crash_analysis(start)
    lines = [f"SBC WEEK AHEAD — {start:%d %b %Y}", ""]

    if week:
        labels = [d.bias_label for d in week]
        dom = max(set(labels), key=labels.count)
        lo, hi = (min(d.bias_net for d in week), max(d.bias_net for d in week))
        rng = f"{lo:+.2f}" if lo == hi else f"{lo:+.2f} to {hi:+.2f}"
        lines.append(f"Index vedha: {dom} on {labels.count(dom)} of {len(week)} "
                     f"sessions (net {rng}).")
        avg = {s: sum(d.nets[s] for d in week) / len(week) for s in week[0].nets}
        ranked = sorted(avg.items(), key=lambda kv: kv[1], reverse=True)
        lines.append("Least stressed: " + ", ".join(
            f"{s} {v:+.1f}" for s, v in ranked[:3]))
        lines.append("Most stressed: " + ", ".join(
            f"{s} {v:+.1f}" for s, v in ranked[-3:][::-1]))
        lines.append("")
        lines.append("Timing:")
        for d in week:
            bits = d.events + ([f"Bhadra {d.bhadra}"] if d.bhadra else [])
            if bits:
                lines.append(f"  {d.day:%a %d %b}: {', '.join(bits)} "
                             f"(Moon in {d.moon_nakshatra})")

    moves = _week_ingresses(start)
    if moves:
        lines.append("")
        lines.append("Transits:")
        lines += [f"  {m}" for m in moves]

    lines.append("")
    lines.append(f"Crash signatures: {crash.score:.0f} ({crash.band})"
                 + (f" — {', '.join(a.replace('_', ' ') for a in crash.active)}"
                    if crash.active else ""))
    lines.append("")
    lines.append("Watch calendar only: the daily vedha backtest found no timing "
                 "edge on NIFTY, so none of this is a signal.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(weekly_commentary())
    if "--backtest" in sys.argv:
        r = crash_backtest()
        print(f"\nCrash backtest ({r['sample_days']} weekly samples)")
        for c in r["crashes"]:
            print(f"  {c['name']:16s} {c['date']}  {c['score']:5.1f} {c['band']}")
        print(f"  score>={r['threshold']:.0f}: crashes {r['flag_rate_crash']:.0%} "
              f"vs all weeks {r['flag_rate_all']:.0%}")
        for s in r["signatures"]:
            lift = f"{s['lift']:.2f}x" if s["lift"] else "n/a"
            print(f"  {s['signature']:28s} {s['crash_hits']}/{s['crashes']} "
                  f"base {s['base_rate']:.0%}  lift {lift}")
