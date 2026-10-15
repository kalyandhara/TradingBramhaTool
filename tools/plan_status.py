#!/usr/bin/env python3
"""plan_status.py — is a watchlist name's trade plan still alive? (LuxAlgo R&E step 2)

The Watchlist's only removal tool was a manual tick: nothing told the reader that
a name's plan had already stopped out, hit its target, or run past the time stop
its own scanner declared. A watchlist that only grows is the funnel's delete step
missing, and the names whose plan is finished crowd out the ones still forming.

── Where the plan comes from ──────────────────────────────────────────────────
`scanner_run_cache` — every scanner card the desk has produced, frozen with its
run date. A name's plan is the NEWEST cached card that carries a full
entry/stop/target (actionable first, so a WATCH card does not shadow a live one
from the same day). The watchlist row does not record which plan a name was added
from, so this never claims to be "the plan you added it on": the row shows which
scanner and which date it is judging.

── How a plan is judged: exactly the way the harness scores one ──────────────
Two harness functions, reused rather than re-written, so the Watchlist and the
backtests cannot disagree about what happened to a plan:

  1. `backtest.resolve_fill(..., "touch")` (B-121). The card's entry is an ORDER:
     above the card-day close it is a buy-stop, below it a buy-limit (shorts
     mirror). It waits 5 sessions and is then cancelled. A first try that walked
     from the next open instead booked GALLANTT's Harmonic card as "+19.6R
     target hit" — its entry is the D price, days old, and the move had already
     happened. That is the stale-fill case B-121 exists for.
  2. `backtest._simulate_plan` from the fill: stop-first when one bar spans both
     levels, short side mirrored, the card's own ``time_stop``.

    STOP HIT      the stop traded (or the fill gapped through it) -> suggest removal
    TARGET HIT    the target traded after the fill                -> suggest removal
    EXPIRED       ran past its own time stop                      -> suggest removal
    NOT FILLED    the entry never traded within 5 sessions        -> suggest removal
    MISSED        the fill came only past the target: the move happened first
                                                                  -> suggest removal
    PENDING       entry not traded yet, still inside the 5-session window
    LIVE          filled, none of the above yet
    WATCH ONLY    the card says actionable: False (B-128) — levels, not a plan
    NO PLAN       no cached card with entry/stop/target
    NO DATA       no bars around the run date, or degenerate levels

── This SUGGESTS, it never deletes ───────────────────────────────────────────
Removal stays the owner's two-step tick-then-press. "Plan finished" is
housekeeping, not a judgement that the stock is done: a name can stop out and set
up again. Nothing here is an edge claim.
"""
from __future__ import annotations

import json
from typing import Any, Iterable

import pandas as pd

#: Statuses that suggest the row has done its job on the watchlist.
REMOVE_SUGGESTED = frozenset({"STOP HIT", "TARGET HIT", "EXPIRED",
                              "NOT FILLED", "MISSED"})

#: Upper bound on a walk when a plan has no time stop. Not a decision: it only
#: stops a stale card being walked across years of bars.
MAX_WALK_BARS = 250

BADGE = {
    "STOP HIT": "🔴 STOP HIT", "TARGET HIT": "🎯 TARGET HIT", "EXPIRED": "⌛ EXPIRED",
    "NOT FILLED": "⨯ NOT FILLED", "MISSED": "↷ MISSED", "PENDING": "⏳ PENDING",
    "LIVE": "🟢 LIVE", "WATCH ONLY": "👁 WATCH ONLY", "NO PLAN": "— no plan",
    "NO DATA": "… no data",
}


def has_plan(card: dict) -> bool:
    try:
        return all(float(card.get(k) or 0) > 0 for k in ("entry", "stop", "target"))
    except (TypeError, ValueError):
        return False


def side_of(card: dict) -> str:
    """Long when the stop sits below the entry — the same rule the harness uses
    to tell a short card from a long one without trusting a ``direction`` field
    most scanners do not emit."""
    return "short" if float(card["stop"]) > float(card["entry"]) else "long"


def pick_plan(rows: Iterable[tuple[str, str, dict]]) -> tuple[str, str, dict] | None:
    """Newest ``(run_date, scanner, card)`` with a full plan; on the same date an
    actionable card beats a watch-only one, then scanner name for a stable pick."""
    best = None
    for run_date, scanner, card in rows:
        if not has_plan(card):
            continue
        key = (str(run_date), card.get("actionable", True) is not False, str(scanner))
        if best is None or key > best[0]:
            best = (key, (str(run_date), str(scanner), card))
    return best[1] if best else None


def _dates(df: pd.DataFrame) -> pd.Series:
    if "date" in df.columns:
        return pd.to_datetime(df["date"]).dt.normalize()
    return pd.Series(pd.to_datetime(df.index).normalize(), index=df.index)


def judge(card: dict, run_date: str, df: pd.DataFrame | None,
          last: float | None = None) -> dict[str, Any]:
    """Status of one plan against the bars after ``run_date``.

    Returns ``status``, ``bars`` (bars after the fill), ``r`` (R from the fill
    price at the exit, or at the last close while LIVE — gross of costs: this is
    a status line, not a measurement), ``side`` and ``time_stop``.
    """
    import backtest

    out: dict[str, Any] = {"status": "NO PLAN", "bars": None, "r": None,
                           "side": None, "time_stop": None}
    if not card or not has_plan(card):
        return out
    side = side_of(card)
    ts = card.get("time_stop")
    out.update(side=side, time_stop=ts)
    if card.get("actionable", True) is False:
        out["status"] = "WATCH ONLY"
        return out
    if df is None or getattr(df, "empty", True):
        out["status"] = "NO DATA"
        return out
    # Dates read BEFORE the index is dropped: bars may carry them as a column or
    # as a DatetimeIndex. The walk itself is positional.
    upto = (_dates(df) <= pd.Timestamp(run_date)).to_numpy().nonzero()[0]
    df = df.reset_index(drop=True)
    if not len(upto) or int(upto[-1]) >= len(df) - 1:
        out["status"] = "NO DATA"            # card day not in the bars, or nothing after it
        return out
    sig = int(upto[-1])                      # the card-day bar
    entry, stop, target = (float(card[k]) for k in ("entry", "stop", "target"))
    fill = backtest.resolve_fill(df, sig, entry, side, "touch")
    if fill["status"] != "filled":
        waited = len(df) - 1 - sig
        out["bars"] = waited
        out["status"] = ("PENDING" if waited < backtest.FILL_MAX_WAIT
                         else "NOT FILLED")
        return out
    f_idx, f_px = int(fill["idx"]), float(fill["px"])
    short = side == "short"
    if (f_px >= stop) if short else (f_px <= stop):
        # The order filled at a price already beyond the stop. The harness counts
        # this as fill-through and never scores it, so no R is claimed here.
        out.update(status="STOP HIT", bars=0)
        return out
    if (f_px <= target) if short else (f_px >= target):
        out.update(status="MISSED", bars=0)
        return out
    res = backtest._simulate_plan(
        df, f_idx, f_px, stop, target, max_bars=MAX_WALK_BARS,
        time_stop=(float(ts) if ts else None), side=side)
    if res is None:
        out["status"] = "NO DATA"            # degenerate levels — not judged
        return out
    out["bars"] = res["bars"]                # bars after entry — time_stop's own unit
    out["r"] = res["r"]
    out["status"] = {"stop": "STOP HIT", "target": "TARGET HIT",
                     "time": "EXPIRED"}.get(res["outcome"], "LIVE")
    return out


def watchlist_status(symbols: Iterable[str], cache_rows_for, fetch_bars
                     ) -> dict[str, dict[str, Any]]:
    """``{symbol: status dict + plan_date, scanner, entry, stop, target}``.

    ``cache_rows_for(symbol)`` yields ``(run_date, scanner, card)``;
    ``fetch_bars(symbol)`` returns daily bars. Both injected so this stays free
    of the database and the network. A failure on one name is that name's
    NO DATA, never the page's.
    """
    result: dict[str, dict[str, Any]] = {}
    for sym in symbols:
        try:
            plan = pick_plan(cache_rows_for(sym))
            if plan is None:
                result[sym] = judge({}, "", None)
                continue
            run_date, scanner, card = plan
            needs_bars = card.get("actionable", True) is not False
            st = judge(card, run_date, fetch_bars(sym) if needs_bars else None)
            st.update(plan_date=run_date, scanner=scanner,
                      entry=float(card["entry"]), stop=float(card["stop"]),
                      target=float(card["target"]))
            result[sym] = st
        except Exception as exc:                       # one row, not the page
            result[sym] = {"status": "NO DATA", "bars": None, "r": None,
                           "side": None, "time_stop": None, "error": str(exc)}
    return result


def label(st: dict[str, Any]) -> str:
    """One cell: badge, then what was judged and how far it got."""
    s = st.get("status", "NO PLAN")
    bits = [BADGE.get(s, s)]
    if st.get("r") is not None and s in ("STOP HIT", "TARGET HIT", "EXPIRED", "LIVE"):
        bits.append(f"{st['r']:+.1f}R")
    if s == "PENDING" and st.get("bars") is not None:
        import backtest
        bits.append(f"order {st['bars']}/{backtest.FILL_MAX_WAIT} sessions")
    elif s == "NOT FILLED":
        bits.append("entry never traded")
    elif st.get("bars") is not None:
        ts = st.get("time_stop")
        bits.append(f"{st['bars']}/{int(ts)} bars" if ts else f"{st['bars']} bars")
    return " · ".join(bits)


def plan_source(st: dict[str, Any]) -> str:
    if not st.get("scanner"):
        return ""
    return f"{st['scanner']} · {st.get('plan_date', '')}"


def cache_rows_from_db(conn, symbol: str) -> list[tuple[str, str, dict]]:
    """``scanner_run_cache`` rows for one symbol, parsed. Kept here (not in
    portfolio_db) because only this reader needs every card for a name."""
    rows = conn.execute(
        "SELECT run_date, scanner_name, card_json FROM scanner_run_cache "
        "WHERE symbol = ?", (symbol.upper(),)).fetchall()
    out = []
    for run_date, scanner, cj in rows:
        try:
            out.append((run_date, scanner, json.loads(cj)))
        except (TypeError, ValueError):
            continue
    return out
