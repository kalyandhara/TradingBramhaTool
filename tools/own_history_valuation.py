"""own_history_valuation.py — B-143: a stock's price against EPS x ITS OWN median
multiple. The Fast Graphs construct, rebuilt from the desk's data. DISPLAY ONLY.

Makes no claim, votes in nothing, scores nothing. It states a level and what it
rests on.

THE REFUSAL IS THE FEATURE. A "normal" multiple is a median over many years. B-141
measured that the desk holds a TTM-EPS history of >= 8 years for 1.6% of the
NIFTY 500 and a median of 5.0 years. So this returns `None` (and says why) below
MIN_YEARS rather than fitting a median to a handful of points and drawing it as if
it were a norm. Drawing nothing is the correct output for most names today.

Definitions
  TTM EPS    sum of four consecutive reported quarters (eps_history_probe.ttm_series).
  multiple   close at the TTM date / TTM EPS, only where TTM EPS > 0.
  normal     MEDIAN of those multiples over the whole window (a median, not a mean:
             one loss-recovery year with a 300x multiple must not move the norm).
  fair price normal x current TTM EPS. Not a target and not intrinsic value; it is
             "where price would sit if the stock traded at its own historical
             median multiple on today's earnings".
"""
from __future__ import annotations

import statistics
from typing import Any, Sequence

MIN_YEARS = 8.0
MIN_POINTS = 24          # quarterly TTM points; 8 years = ~29
JUMP = 4.0               # TTM step beyond this is treated as a split/unit artefact


def _years(ser: Sequence[tuple[str, float]]) -> float:
    import datetime as dt
    if len(ser) < 2:
        return 0.0
    return (dt.date.fromisoformat(ser[-1][0]) - dt.date.fromisoformat(ser[0][0])).days / 365.25


def band(ttm: Sequence[tuple[str, float]], price_at: dict[str, float],
         price_now: float, min_years: float = MIN_YEARS) -> dict[str, Any]:
    """`ttm`: [(iso date, TTM EPS)] oldest first. `price_at`: iso date -> close.

    Always returns a dict with `ok`. When not ok, `reason` says exactly why, so the
    caller can show the refusal instead of a blank.
    """
    if not ttm:
        return {"ok": False, "reason": "no reported-EPS history"}
    yrs = _years(ttm)
    if yrs < min_years or len(ttm) < MIN_POINTS:
        return {"ok": False, "years": round(yrs, 1), "points": len(ttm),
                "reason": f"only {yrs:.1f} years / {len(ttm)} quarterly points of EPS; "
                          f"a normal multiple needs {min_years:.0f}+ years"}
    for (_, a), (_, b) in zip(ttm, ttm[1:]):
        if a > 0 and b > 0 and (b / a > JUMP or a / b > JUMP):
            return {"ok": False, "years": round(yrs, 1), "points": len(ttm),
                    "reason": "EPS series has a >4x jump — likely a split or unit break"}
    mult = [price_at[d] / e for d, e in ttm if e > 0 and d in price_at and price_at[d] > 0]
    if len(mult) < MIN_POINTS:
        return {"ok": False, "years": round(yrs, 1), "points": len(mult),
                "reason": "too few profitable quarters with a price to form a multiple"}
    eps_now = ttm[-1][1]
    if eps_now <= 0:
        return {"ok": False, "years": round(yrs, 1), "points": len(mult),
                "reason": "current TTM EPS is not positive; a multiple of a loss is undefined"}
    normal = statistics.median(mult)
    fair = normal * eps_now
    return {"ok": True, "years": round(yrs, 1), "points": len(mult),
            "normal_multiple": round(normal, 1), "current_multiple": round(price_now / eps_now, 1),
            "eps_ttm": round(eps_now, 2), "fair_price": round(fair, 2),
            "price_vs_fair_pct": round((price_now / fair - 1) * 100, 1),
            "low_multiple": round(min(mult), 1), "high_multiple": round(max(mult), 1)}


def caption(b: dict[str, Any]) -> str:
    if not b.get("ok"):
        return f"Own-history valuation not shown: {b.get('reason', 'unavailable')}."
    return (f"Over {b['years']} years the stock's median multiple was {b['normal_multiple']}× "
            f"(range {b['low_multiple']}–{b['high_multiple']}×); today it is {b['current_multiple']}×. "
            f"On today's earnings its own median multiple would put price near {b['fair_price']:,.0f}. "
            f"That is a statement about the stock's past, not a target and not intrinsic value.")
