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


# ── EXPOSURE — the component the reference pipeline names and the desk lacked ──
# B-107. This REPORTS and does not judge. Every threshold here would be a
# statement about the owner's risk appetite (how concentrated is too
# concentrated?), and that is a decision to be made once, deliberately, by them —
# not a default smuggled in by whoever wrote the function. The numbers are the
# deliverable; the lines in the sand are not ours to draw.
def exposure(open_pos: "pd.DataFrame", price_fn, total_capital: float,
             sectors: "dict[str, str] | None" = None) -> dict[str, Any]:
    """Concentration of the open book: by position, by sector, and how much of
    the capital is deployed at all.

    ``sectors`` maps SYMBOL -> sector name. A symbol the map has never seen is
    counted in ``unmapped_pct`` rather than bucketed into "Other" — the same rule
    `sector_column` holds, because an invented sector is worse than a blank one.
    """
    empty = dict(deployed_pct=0.0, n_positions=0, largest_symbol=None,
                 largest_pct=0.0, top3_pct=0.0, by_sector={},
                 largest_sector=None, largest_sector_pct=0.0, unmapped_pct=0.0,
                 cash_pct=100.0, unpriced=0)
    if open_pos is None or getattr(open_pos, "empty", True):
        return empty
    cap = float(total_capital)
    sect = {str(k).upper(): v for k, v in (sectors or {}).items()}

    values: list[tuple[str, float]] = []
    unpriced = 0
    for _, pos in open_pos.iterrows():
        sym = str(pos["symbol"])
        px = price_fn(sym)
        if px is None:
            unpriced += 1
            continue
        values.append((sym, float(px[0]) * float(pos["quantity"])))
    if not values:
        return {**empty, "unpriced": unpriced, "n_positions": int(len(open_pos))}

    deployed = sum(v for _, v in values)
    # Percentages are of CAPITAL, not of the deployed book. "40% of what I have
    # deployed" flatters a book that is mostly in cash, and the question a
    # concentration number answers is what happens to the ACCOUNT when one name
    # gaps. Falls back to share-of-book only when capital is unset.
    denom = cap if cap > 0 else deployed
    pct = lambda v: (v / denom * 100.0) if denom else 0.0

    ranked = sorted(values, key=lambda kv: kv[1], reverse=True)
    by_sector: dict[str, float] = {}
    unmapped = 0.0
    for sym, v in values:
        name = sect.get(sym.upper()) or sect.get(sym.upper().replace(".NS", ""))
        if name:
            by_sector[name] = by_sector.get(name, 0.0) + pct(v)
        else:
            unmapped += pct(v)
    top_sector = max(by_sector.items(), key=lambda kv: kv[1], default=(None, 0.0))

    return dict(
        deployed_pct=pct(deployed),
        n_positions=int(len(open_pos)),
        largest_symbol=ranked[0][0],
        largest_pct=pct(ranked[0][1]),
        top3_pct=sum(pct(v) for _, v in ranked[:3]),
        by_sector={k: round(v, 2) for k, v in sorted(
            by_sector.items(), key=lambda kv: kv[1], reverse=True)},
        largest_sector=top_sector[0],
        largest_sector_pct=top_sector[1],
        unmapped_pct=unmapped,
        # What is NOT at risk, which a book of five positions reads very
        # differently from a book of twenty-five.
        cash_pct=max(0.0, 100.0 - pct(deployed)) if cap > 0 else 0.0,
        unpriced=unpriced,
    )


# ── SIZING — reconciling two numbers that already exist ───────────────────────
# B-107 again, and note what this does NOT do: it invents no new rule. The desk
# already states a per-trade size (`stock_council.RISK_PER_TRADE_PCT`, sized off
# the stop) and a market-wide throttle (`market_verdict`'s 0/50/100% multiplier
# and its max-trades cap). They simply never met, so a STAND DOWN day left the
# suggested size untouched and the trade cap was never checked against the book.
# Multiplying one by the other is arithmetic the owner already authored twice.
def reconcile_size(council_size_pct: float | None,
                   verdict: dict[str, Any] | None,
                   open_count: int = 0) -> dict[str, Any]:
    """The per-trade size AFTER the market verdict's throttle, plus slots left.

    Returns ``size_pct`` (None when the council gave none), the multiplier that
    was applied, whether the throttle actually bit, and how many trades the cap
    still allows. ``at_cap`` is reported separately from the size because they
    fail differently: a 50% size still lets you take the trade, and being at the
    cap does not.
    """
    v = verdict or {}
    mult = v.get("size_pct")
    mult = 100.0 if mult is None else float(mult)
    max_trades = v.get("max_trades")
    slots = None if max_trades is None else max(0, int(max_trades) - int(open_count))

    sized = (None if council_size_pct is None
             else round(float(council_size_pct) * mult / 100.0, 1))
    return {
        "size_pct": sized,
        "raw_size_pct": (None if council_size_pct is None
                         else round(float(council_size_pct), 1)),
        "multiplier_pct": mult,
        "throttled": mult < 100.0 and council_size_pct is not None,
        "verdict": v.get("verdict"),
        "max_trades": max_trades,
        "slots_left": slots,
        "at_cap": (slots == 0) if slots is not None else False,
    }


def size_note(rec: dict[str, Any]) -> str:
    """One line for the trade card, saying WHICH rule moved the number.

    A size that silently halves is a number the reader cannot argue with. Naming
    the verdict that halved it is what makes it a decision rather than a display.
    """
    if rec.get("size_pct") is None:
        return ""
    bits = [f"**Suggested size** {rec['size_pct']}% of capital"]
    if rec.get("throttled"):
        bits.append(f"— {rec['raw_size_pct']}% at the {RISK_RULE_LABEL}, "
                    f"scaled to {rec['multiplier_pct']:.0f}% by today's "
                    f"**{rec.get('verdict')}** verdict")
    if rec.get("at_cap"):
        bits.append(f"· ⚠ already at today's cap of {rec['max_trades']} trade(s)")
    elif rec.get("slots_left") is not None:
        bits.append(f"· {rec['slots_left']} of {rec['max_trades']} trade slot(s) left")
    return "  ".join(bits)


#: Named here so the card and the tests agree on what the per-trade rule is
#: called without either importing `stock_council` (which pulls in the whole
#: fundamentals stack).
RISK_RULE_LABEL = "per-trade risk rule"


def exposure_strip(exp: dict[str, Any], cols: int = 4) -> tuple[str, list[str]]:
    """(cards HTML, caption lines) for the Portfolio page's exposure block.

    Built here rather than on the page for the same reason `risk_card` is: the
    monolith ratchet counts what the page carries, and a block written there is
    a block no test can reach. `report_style` renders HTML strings and imports
    no Streamlit, so this stays importable from a test.
    """
    import report_style as rs

    cards = [
        rs.stat_card("Deployed", f"{exp['deployed_pct']:.1f}%",
                     f"{exp['n_positions']} position(s) · "
                     f"{exp['cash_pct']:.0f}% uncommitted"),
        rs.stat_card("Largest position", f"{exp['largest_pct']:.1f}%",
                     exp["largest_symbol"] or "—"),
        rs.stat_card("Top 3", f"{exp['top3_pct']:.1f}%",
                     "of capital in the three biggest"),
        rs.stat_card("Largest sector",
                     (f"{exp['largest_sector_pct']:.1f}%"
                      if exp["largest_sector"] else None),
                     exp["largest_sector"] or "no sector map for these names"),
    ]
    captions = []
    if exp.get("by_sector"):
        line = " · ".join(f"{k} {v:.1f}%" for k, v in exp["by_sector"].items())
        if exp.get("unmapped_pct"):
            line += f" · unmapped {exp['unmapped_pct']:.1f}%"
        captions.append("By sector — " + line)
    if exp.get("unpriced"):
        captions.append(f"⚠ {exp['unpriced']} position(s) could not be priced — "
                        "every number here is understated.")
    captions.append(
        "Percentages are of TOTAL CAPITAL, not of the deployed book — a share of "
        "what is deployed flatters a book that is mostly in cash, and the question "
        "is what happens to the account when one name gaps. No thresholds are "
        "applied: what counts as too concentrated is yours to set (B-107).")
    return rs.strip(cards, cols=cols), captions
