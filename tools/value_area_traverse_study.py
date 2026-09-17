#!/usr/bin/env python3
"""value_area_traverse_study.py — the Volume Profile "80% rule" (B-9).

THE CLAIM, as the source states it: price entering the value area and holding
**two consecutive 30-minute bars** inside it has roughly an **80% chance** of a
full traverse to the opposite value-area boundary.

A vendor claim with no data behind it, and stated precisely enough to be
falsified — which is the only reason it earned a backlog entry.

══ THE DATA, AND WHY THIS WAS NEVER ACTUALLY BLOCKED ═══════════════════════════

The backlog carried this as "testable on NSE 30-min data" and nothing followed,
which read as a data gap. It is not one. `intraday_store` holds **15-minute bars
over ~85 sessions for 6 liquid names**, and 30-minute bars aggregate from 15s by
pairing. Counting what is already stored beat waiting, again.

══ THE DEFINITION THAT DECIDES THE ANSWER ══════════════════════════════════════

"Value area" is ambiguous and the choice is not cosmetic:

  * **PRIOR session's value area** — fixed before the session starts, so an entry
    into it is a real-time decision a trader could act on.
  * **CURRENT session's developing value area** — recomputed as the session runs,
    which means the boundary you "enter" is partly determined by the bars you are
    about to trade. That is lookahead wearing a costume.

This study uses the **PRIOR session's** value area. It is the only version that
can be traded, and it is the version the rule's own framing implies ("price
returns to value").

══ WHAT COUNTS AS A TRAVERSE ═══════════════════════════════════════════════════

Entry: price is OUTSIDE the prior VA, then closes INSIDE it for two consecutive
30-minute bars. The trigger bar is the second one.

Success: before the session ends, price reaches the FAR boundary — the one
opposite the side it entered from. Entering from below and tagging VAL again is
not a traverse; it is a failed entry, and counting it would make the rule
unfalsifiable.

Failure: the session ends without reaching the far boundary, or price leaves the
value area back through the side it came from and never returns to complete.

══ THE BASELINE, WHICH THE CLAIM DOES NOT MENTION ══════════════════════════════

80% sounds impressive until you ask how often a full traverse happens ANYWAY. The
control here is every session where price was inside the prior VA at some point,
measured for the same full-traverse outcome without requiring the two-bar hold.
**A rule that scores 80% against a base rate of 78% has found nothing.** Reporting
the hit rate alone would be the error this control exists to prevent.

CLI:
  py -3 -X utf8 tools/value_area_traverse_study.py
  py -3 -X utf8 tools/value_area_traverse_study.py --interval 15m
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

import intraday_store as store
import volume_profile as vp

#: The claim is stated on 30-minute bars, so that is the primary. 15m is offered
#: as a sensitivity check, not as an alternative answer.
PRIMARY_INTERVAL = "30m"

#: Consecutive bars that must close inside the value area to arm the setup.
HOLD_BARS = 2

#: The claimed hit rate, so the report can state the gap rather than make the
#: reader compute it.
CLAIMED = 80.0


def sessions(df: pd.DataFrame) -> list[pd.DataFrame]:
    """Split an intraday frame into one frame per trading date, in order."""
    if df is None or df.empty:
        return []
    return [g for _d, g in df.groupby(df.index.date, sort=True) if len(g) >= 4]


def to_30m(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 15-minute bars to 30 by pairing within each session.

    Two things here are load-bearing, and a test pins each:

    **Group by date first.** Resampling the whole frame would bridge the
    overnight gap and glue 15:15 to the next day's 09:15 into one "bar". That is
    not a 30-minute bar, it is a fiction, and it would invent value-area
    crossings that never happened.

    **Anchor on the session open, not on the hour.** NSE opens at 09:15, so a
    plain `resample("30min")` snaps to 09:00 and the first "30-minute bar" of
    every session contains a single 15-minute bar. `origin` on the day's first
    timestamp gives 09:15-09:45, 09:45-10:15 and so on, which is what a 30-minute
    bar on this exchange actually is.
    """
    out = []
    for day in sessions(df):
        g = day.resample("30min", origin=day.index[0]).agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "volume": "sum"}).dropna()
        out.append(g)
    return pd.concat(out) if out else df.iloc[:0]


def _va(day: pd.DataFrame) -> tuple[float, float] | None:
    p = vp.compute_profile(day)
    if not p or not p.get("value_area"):
        return None
    va = p["value_area"]
    lo, hi = float(va["low"]), float(va["high"])
    return (lo, hi) if hi > lo else None


def evaluate_session(cur: pd.DataFrame, lo: float, hi: float) -> dict:
    """One session against a fixed value-area band. The whole rule lives here.

    Split out of `analyse_symbol` so it can be tested on a hand-built session:
    the arming condition and the far-boundary requirement are the two places a
    bug would quietly confirm the claim, and neither is reachable through the
    store-backed entry point.
    """
    c = cur["close"].to_numpy(float)
    h = cur["high"].to_numpy(float)
    l = cur["low"].to_numpy(float)
    inside = (c >= lo) & (c <= hi)

    rec = {
        # Control: did the session touch the band at all, and did it cross the
        # band end to end regardless of any hold condition?
        "touched": bool(((l <= hi) & (h >= lo)).any()),
        "ctrl_traverse": bool((l <= lo).any() and (h >= hi).any()),
        "armed": False, "traversed": None, "side": None,
    }

    run, armed_at, side = 0, None, None
    for i in range(len(c)):
        if inside[i]:
            if run == 0:
                # Which side did it come from? The last close outside the band.
                prior = [j for j in range(i) if not inside[j]]
                side = ("below" if prior and c[prior[-1]] < lo
                        else "above" if prior else None)
            run += 1
            if run >= HOLD_BARS and side is not None:
                armed_at = i
                break
        else:
            run = 0
    if armed_at is None or side is None:
        return rec

    rec["armed"] = True
    rec["side"] = side
    # The FAR boundary — the one opposite the side it entered from. Accepting a
    # return to the near boundary would make the rule unfalsifiable.
    rest_h, rest_l = h[armed_at + 1:], l[armed_at + 1:]
    rec["traversed"] = (bool((rest_h >= hi).any()) if side == "below"
                        else bool((rest_l <= lo).any()))
    return rec


def analyse_symbol(symbol: str, interval: str) -> list[dict]:
    """One row per session, carrying both the setup outcome and the control."""
    raw = store.read_bars(symbol, "15m")
    if raw is None or raw.empty:
        return []
    df = to_30m(raw) if interval == "30m" else raw
    days = sessions(df)
    rows = []
    for prev, cur in zip(days, days[1:]):
        band = _va(prev)
        if band is None:
            continue
        lo, hi = band
        rec = evaluate_session(cur, lo, hi)
        rec.update({"symbol": symbol, "date": str(cur.index[0].date()),
                    "va_low": lo, "va_high": hi})
        rows.append(rec)
    return rows


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval, in per cent. Honest at small n where the normal
    approximation puts a bound outside [0,1]."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100.0 * max(0.0, c - half), 100.0 * min(1.0, c + half))


def _two_prop_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided z-test on two proportions.

    Used ONLY for the lift over the base rate, never for the 80% claim: that one
    is decided by whether 80 falls inside the hit rate's confidence interval,
    which needs no second sample.
    """
    if n1 == 0 or n2 == 0:
        return float("nan")
    p1, p2 = k1 / n1, k2 / n2
    pp = (k1 + k2) / (n1 + n2)
    se = np.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    if se == 0:
        return float("nan")
    z = (p1 - p2) / se
    # Normal two-sided tail without scipy, matching the repo's fallback style.
    from math import erfc, sqrt
    return float(erfc(abs(z) / sqrt(2)))


def summarise(rows: list[dict]) -> dict:
    armed = [r for r in rows if r["armed"]]
    hits = [r for r in armed if r["traversed"]]
    ctrl_pool = [r for r in rows if r["touched"]]
    ctrl_hits = [r for r in ctrl_pool if r["ctrl_traverse"]]
    rate = 100.0 * len(hits) / len(armed) if armed else float("nan")
    base = 100.0 * len(ctrl_hits) / len(ctrl_pool) if ctrl_pool else float("nan")
    by_side = {}
    for s in ("below", "above"):
        a = [r for r in armed if r["side"] == s]
        by_side[s] = {"n": len(a),
                      "rate": (100.0 * sum(bool(r["traversed"]) for r in a) / len(a))
                              if a else float("nan")}
    ci = _wilson(len(hits), len(armed))
    return {"n_sessions": len(rows), "n_armed": len(armed), "n_hits": len(hits),
            "rate": rate, "ci": ci, "n_ctrl": len(ctrl_pool), "base": base,
            "n_ctrl_hits": len(ctrl_hits), "lift": rate - base,
            "lift_p": _two_prop_p(len(hits), len(armed),
                                  len(ctrl_hits), len(ctrl_pool)),
            "by_side": by_side}


def verdict(s: dict) -> tuple[str, str]:
    """Pre-registered rule: the claim is about 80%, and lift is what decides it."""
    if s["n_armed"] < 30:
        return ("INCONCLUSIVE - UNDERPOWERED",
                f"{s['n_armed']} armed setups; too few to score")
    lo, hi = s["ci"]
    parts = [f"hit {s['rate']:.1f}% (95% CI {lo:.1f}-{hi:.1f}, n={s['n_armed']})"]
    # The claim is falsified when 80 sits OUTSIDE the interval. That needs no
    # control and no second sample -- it is a statement about one proportion.
    if not (lo <= CLAIMED <= hi):
        tag = "CLAIM FALSIFIED"
        parts.append(f"the {CLAIMED:.0f}% claim lies outside that interval")
    else:
        tag = "CLAIM NOT EXCLUDED"
    # The lift is a SEPARATE question and gets its own test, because "worse than
    # doing nothing" is a stronger statement than "not 80%" and must not ride in
    # on the first one's significance.
    p = s["lift_p"]
    if np.isfinite(p) and p < 0.05:
        parts.append(f"and it UNDERPERFORMS the base rate {s['base']:.1f}% "
                     f"(lift {s['lift']:+.1f}pp, p={p:.3f})")
    else:
        parts.append(f"lift over base {s['lift']:+.1f}pp is not significant "
                     f"(p={p:.3f}) -- no claim either way on that")
    return tag, "; ".join(parts)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(description="B-9 · the volume-profile 80% rule")
    ap.add_argument("--interval", default=PRIMARY_INTERVAL, choices=("30m", "15m"))
    a = ap.parse_args()

    cov = store.coverage()
    syms = sorted({str(s) for s in cov["symbol"]}) if cov is not None else []
    print(f"Symbols in the intraday store: {len(syms)} — {', '.join(syms)}")
    print(f"Interval: {a.interval} (the claim is stated on 30-minute bars)\n")

    rows: list[dict] = []
    for sym in syms:
        r = analyse_symbol(sym, a.interval)
        rows.extend(r)
        s = summarise(r)
        print(f"  {sym:<14} sessions {s['n_sessions']:>4}  armed {s['n_armed']:>4}  "
              f"hit {s['rate']:>5.1f}%  base {s['base']:>5.1f}%")

    s = summarise(rows)
    print(f"\nPOOLED  sessions {s['n_sessions']}  armed {s['n_armed']}  "
          f"control pool {s['n_ctrl']}")
    print(f"  traverse after a {HOLD_BARS}-bar hold : {s['rate']:.1f}%  "
          f"({s['n_hits']}/{s['n_armed']})")
    print(f"       95% CI (Wilson)                 : {s['ci'][0]:.1f}% - {s['ci'][1]:.1f}%")
    print(f"  traverse WITHOUT the hold (base)     : {s['base']:.1f}%  "
          f"({s['n_ctrl_hits']}/{s['n_ctrl']})")
    print(f"  lift                                 : {s['lift']:+.1f}pp  "
          f"(p={s['lift_p']:.3f})")
    print(f"  the claim                            : {CLAIMED:.0f}%")
    print(f"\n  entered from below : n={s['by_side']['below']['n']:<4} "
          f"{s['by_side']['below']['rate']:.1f}%")
    print(f"  entered from above : n={s['by_side']['above']['n']:<4} "
          f"{s['by_side']['above']['rate']:.1f}%")

    v, why = verdict(s)
    print(f"\nVERDICT: {v}\n  {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
