#!/usr/bin/env python3
"""portfolio_risk.py — what the open book is actually risking (B-106).

Extracted from `dashboard_app.compute_portfolio_summary`, which computed one
risk number and computed it from a price that is no longer live:

    risk_amount += (entry_price - stop_loss) * qty

That is **INITIAL** risk — what the trade risked on the day it was opened,
frozen there forever. A position up 30% with a stop raised above entry still
reported its day-one risk; a position under water with an untouched stop
reported less than it was actually risking. The number fed Home's "Capital at
Risk" card *and* `market_verdict`'s 6% caution flag, so the flag that throttles
the whole desk was reading entry prices on a page full of live ones.

── Two numbers, because the gap between them is the read ─────────────────────
**Initial risk** is not wrong, it is a different question, and it is the one
that answers "how much did I put at stake?". **Open risk** answers "how much is
still at stake if every stop fills today?" — which is the question a caution
flag is asking. Both are returned. The gap between them is how much of the
original risk the book has already retired, which is a fact neither number tells
you on its own.

── Why a stop above the current price is ZERO, not negative ──────────────────
A position whose stop sits above the live price is in locked-in profit: a stop
fill there is a WIN, not a loss. Reporting it as negative risk would let it net
off against another position's real exposure — one winner could hide two losers
— so each position's open risk is floored at zero before summing. The portfolio
number is "what I lose if every stop fills", and no position can contribute
less than nothing to that.

This module is deliberately pure: frames and a price lookup in, numbers out, no
Streamlit and no database. That is what makes it testable, which the monolith
version was not (importing `dashboard_app` runs the app).
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

import pandas as pd


def position_risk(entry: float, stop: float | None, last: float,
                  qty: float) -> dict[str, float]:
    """Initial and open risk for ONE position, in currency.

    ``initial`` = (entry - stop) x qty, floored at 0 — a stop placed above the
    entry never risked anything to begin with.
    ``open``    = (last - stop) x qty, floored at 0 — see the module docstring
    for why the floor matters more here than it looks.
    A position with **no stop** has unbounded risk and is reported as 0 with
    ``has_stop`` False, so a caller can count those separately instead of
    treating "no stop" as "no risk" — which is the precise inversion of the
    truth.
    """
    if stop is None or (isinstance(stop, float) and stop != stop):      # NaN
        return {"initial": 0.0, "open": 0.0, "has_stop": 0.0}
    q = float(qty)
    return {
        "initial": max(0.0, (float(entry) - float(stop))) * q,
        "open": max(0.0, (float(last) - float(stop))) * q,
        "has_stop": 1.0,
    }


def summarise(open_pos: pd.DataFrame,
              price_fn: Callable[[str], "tuple[float, float] | None"],
              total_capital: float) -> dict[str, Any]:
    """Live P&L + BOTH risk numbers over the open book.

    ``price_fn(symbol)`` returns ``(last, prev_close)`` or None when the symbol
    cannot be priced. A position that cannot be priced contributes nothing and is
    counted in ``unpriced`` rather than silently skipped — a book that is half
    unpriced must not report a comfortable risk number.
    """
    empty = dict(invested=0.0, current_value=0.0, pl=0.0, pl_pct=0.0,
                 capital_at_risk_pct=0.0, open_risk_pct=0.0,
                 risk_retired_pct=0.0, no_stop_count=0, unpriced=0,
                 total_capital=float(total_capital), day_pl_pct=0.0, open_count=0)
    if open_pos is None or getattr(open_pos, "empty", True):
        return empty

    invested = current_value = day_pl = 0.0
    initial_risk = open_risk = 0.0
    no_stop = unpriced = 0

    for _, pos in open_pos.iterrows():
        px = price_fn(str(pos["symbol"]))
        if px is None:
            unpriced += 1
            continue
        last, prev = float(px[0]), float(px[1])
        qty = float(pos["quantity"])
        entry = float(pos["entry_price"])
        invested += entry * qty
        current_value += last * qty
        day_pl += (last - prev) * qty

        stop = pos.get("stop_loss")
        r = position_risk(entry, stop, last, qty)
        initial_risk += r["initial"]
        open_risk += r["open"]
        if not r["has_stop"]:
            no_stop += 1

    pl = current_value - invested
    cap = float(total_capital)
    initial_pct = (initial_risk / cap * 100) if cap else 0.0
    open_pct = (open_risk / cap * 100) if cap else 0.0
    return dict(
        invested=invested, current_value=current_value, pl=pl,
        pl_pct=(pl / invested * 100) if invested else 0.0,
        # The legacy key KEEPS its legacy meaning (initial risk). Silently
        # changing what an existing key means is how a number ends up read two
        # ways by two callers; the new question gets a new name.
        capital_at_risk_pct=initial_pct,
        open_risk_pct=open_pct,
        # How much of the original risk the book has already retired. Negative
        # when the book is under water — open risk has grown past what was put
        # at stake, which is exactly when a reader wants to be told.
        risk_retired_pct=((initial_risk - open_risk) / initial_risk * 100
                          if initial_risk > 0 else 0.0),
        no_stop_count=no_stop,
        unpriced=unpriced,
        total_capital=cap,
        day_pl_pct=(day_pl / current_value * 100) if current_value else 0.0,
        open_count=int(len(open_pos)),
    )


def live_risk_pct(summary: dict[str, Any] | None) -> float | None:
    """The number a caution flag should read: open risk, falling back to initial.

    The fallback is for callers holding a summary built before this module
    existed (a stored row, an older cache). Preferring the new key when it is
    present and the old one when it is not keeps both readable without either
    pretending to be the other.
    """
    if not summary:
        return None
    for key in ("open_risk_pct", "capital_at_risk_pct"):
        v = summary.get(key)
        if v is not None:
            return float(v)
    return None


def risk_card(summary: dict[str, Any] | None, caution_pct: float) -> tuple[float, str, str]:
    """(value, sub-line, tone) for Home's "Capital at Risk" card.

    This lives here rather than inline on the page for the reason the monolith
    ratchet exists: a conditional written at module scope in `dashboard_app` is
    unreachable from a test, and this one decides which of three things the
    reader is told. Moving it costs the page one import and buys the branch a
    test each.

    The sub-line is a priority, not a format string. A position with NO STOP has
    unbounded risk and is not in the number at all, so that warning outranks the
    retired-risk note — silence there would read as safety.
    """
    s = summary or {}
    value = live_risk_pct(s) or 0.0
    initial = float(s.get("capital_at_risk_pct") or 0.0)
    retired = float(s.get("risk_retired_pct") or 0.0)
    no_stop = int(s.get("no_stop_count") or 0)
    unpriced = int(s.get("unpriced") or 0)

    if no_stop:
        sub = f"⚠ {no_stop} position(s) with NO STOP — not counted here"
    elif unpriced:
        sub = f"⚠ {unpriced} position(s) could not be priced — risk understated"
    elif initial > 0:
        sub = f"open risk · {retired:.0f}% of initial {initial:.1f}% retired"
    else:
        sub = f"caution above {caution_pct:.0f}%"

    tone = "risk" if (value > caution_pct or no_stop or unpriced) else "neutral"
    return value, sub, tone
