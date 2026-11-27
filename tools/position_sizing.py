#!/usr/bin/env python3
"""position_sizing.py — one place for "how big, given this stop" (LuxAlgo R&E step 1).

The desk sized positions in two places with the same arithmetic written twice:
`stock_council.judge` (size as % of capital so a stop-out loses
``RISK_PER_TRADE_PCT``) and `portfolio_sim` (notional so a stop-out loses
``risk_pct`` of closed equity). Both are fixed-fractional sizing — the R-multiple
framework's rule that 1R is a known slice of the account — and two copies of one
rule is how they drift. The chart's risk box (`risk_box.js`) is the third reader;
it mirrors these functions in JS and a parity test holds the two together.

── What this is, and what it is not ───────────────────────────────────────────
Bookkeeping, not an edge claim. Sizing off the stop makes every trade risk the
same slice of capital; it does not make any trade better. The **2% default is a
PRIOR** — the owner's stated risk appetite, never measured on this desk — and it
lives here so changing it changes every reader at once.

── R is defined by the INITIAL stop ──────────────────────────────────────────
``r_multiple`` takes the stop the trade was opened with. A stop raised later is a
management decision, not a redefinition of what -1R meant on day one (see
`portfolio_db.positions.initial_stop`).

Pure: numbers in, numbers out. No Streamlit, no database.
"""
from __future__ import annotations

import math

#: % of total capital a stop-out may cost. A PRIOR (owner's appetite), unmeasured.
RISK_PER_TRADE_PCT = 2.0

#: A position may not exceed this % of capital however tight the stop — a 0.1%
#: stop at 2% risk would otherwise ask for 20x the account. No leverage.
MAX_POSITION_PCT = 100.0


def _valid(entry, stop) -> bool:
    try:
        e, s = float(entry), float(stop)
    except (TypeError, ValueError):
        return False
    return (math.isfinite(e) and math.isfinite(s) and e > 0 and s > 0
            and e != s)


def stop_distance_pct(entry, stop) -> float | None:
    """|entry - stop| as % of entry, or None when either is missing / equal."""
    if not _valid(entry, stop):
        return None
    return abs(float(entry) - float(stop)) / float(entry) * 100.0


def size_pct_from_stop_pct(stop_pct, risk_pct: float = RISK_PER_TRADE_PCT,
                           cap_pct: float = MAX_POSITION_PCT) -> float | None:
    """Position size as % of capital so a stop-out loses ``risk_pct`` of capital.

    ``stop_pct`` is the stop distance in % of entry. Rounded to 0.1, capped at
    ``cap_pct`` — the exact form `stock_council` has always printed.
    """
    if stop_pct is None or not stop_pct or stop_pct <= 0:
        return None
    return round(min(cap_pct, risk_pct / stop_pct * 100), 1)


def size_pct_of_capital(entry, stop, risk_pct: float = RISK_PER_TRADE_PCT,
                        cap_pct: float = MAX_POSITION_PCT) -> float | None:
    """`size_pct_from_stop_pct` straight from prices."""
    return size_pct_from_stop_pct(stop_distance_pct(entry, stop), risk_pct, cap_pct)


def notional_for_risk(capital, entry, stop, risk_pct: float) -> float | None:
    """₹ of position whose stop-out costs ``risk_pct`` of ``capital``. Uncapped —
    callers apply their own caps (the sim has cash and slot caps of its own)."""
    if not _valid(entry, stop):
        return None
    want_risk = float(capital) * risk_pct / 100.0
    risk_frac = abs(float(entry) - float(stop)) / float(entry)
    return want_risk / risk_frac


def shares_for_risk(capital, entry, stop, risk_pct: float = RISK_PER_TRADE_PCT,
                    cap_pct: float = MAX_POSITION_PCT) -> dict | None:
    """Whole shares for a stop-out to cost at most ``risk_pct`` of ``capital``.

    Returns ``qty`` (floored — rounding up would risk more than asked),
    ``r_per_share``, ``risk_amount`` (qty x R, ≤ the budget), ``notional``,
    ``position_pct`` and ``capped`` (True when the % cap, not the risk budget,
    set the size). None when the inputs cannot define a risk.
    """
    if not _valid(entry, stop):
        return None
    cap = float(capital)
    if not math.isfinite(cap) or cap <= 0:
        return None
    e = float(entry)
    r = abs(e - float(stop))
    budget = cap * risk_pct / 100.0
    qty_risk = math.floor(budget / r)
    qty_cap = math.floor(cap * cap_pct / 100.0 / e)
    qty = max(0, min(qty_risk, qty_cap))
    return {
        "qty": qty,
        "r_per_share": r,
        "risk_amount": qty * r,
        "risk_budget": budget,
        "notional": qty * e,
        "position_pct": qty * e / cap * 100.0,
        "capped": qty_cap < qty_risk,
    }


def r_multiple(entry, initial_stop, price, side: str = "long") -> float | None:
    """(price - entry) / (entry - initial_stop) for a long; mirrored for a short.

    None when there is no initial stop or it sits on the wrong side of entry — a
    'risk' that was never at risk has no R to measure in.
    """
    if price is None or not _valid(entry, initial_stop):
        return None
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(p):
        return None
    e, s = float(entry), float(initial_stop)
    if side == "short":
        return (e - p) / (s - e) if s > e else None
    return (p - e) / (e - s) if e > s else None
