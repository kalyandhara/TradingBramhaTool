#!/usr/bin/env python3
"""plan_on_demand.py — the trade plan, on the page a name is chosen from (B-109).

`stock_council.build_trade_card` is the richest PLAN object on this desk — entry,
stop, three targets with R:R, horizon, invalidations, a suggested size and a
BUY/WATCH/AVOID verdict — and it rendered on exactly two research pages. The
Opportunity Hub, which is the ranked shortlist a reader actually acts from,
showed a rank and whatever entry/stop/target the firing scanner happened to
carry: **20 of the 49 observed scanners carry one, 29 carry none** (the PR-2
census), so better than half the rows arrived with no plan at all.

── Why a click-through and not a column ─────────────────────────────────────
The council is not cheap: it gathers evidence, fetches fundamentals and scores
two theses per name. Running it for twenty shortlist rows to fill a column would
turn a page that loads into a page that waits, and it would spend that cost on
nineteen names the reader was never going to trade.

It is also a **shortlist**. A ranked list whose every row carries a full trade
plan is not a shortlist any more, it is twenty trade plans — and the pipeline
this desk is organised around (SCAN → SIGNAL → **PLAN** → RISK → …) puts PLAN
*after* the reader has chosen. So: one name, on demand, when asked.

── What this module does and does not own ───────────────────────────────────
It owns the SELECTION and the framing. The council, the card renderer and the
size reconciliation are passed in, because they already exist and having two
copies of "how a trade card looks" is how the two would drift apart.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

import streamlit as st

#: Shown above the picker. States the trade being made — a plan costs a fetch and
#: a few seconds, so it is asked for rather than rendered twenty times.
BLURB = ("The shortlist ranks; it does not plan. Pick one name to run the full "
         "council on it — verdict, entry, stop, targets, invalidations and a "
         "size already scaled by today's market verdict.")


def eligible_symbols(shortlist, column: str = "symbol") -> list[str]:
    """Symbols from a shortlist frame, de-duplicated, order preserved.

    Order matters: the shortlist arrives ranked, and re-sorting the picker
    alphabetically would quietly hide which name the desk put first.
    """
    if shortlist is None or getattr(shortlist, "empty", True):
        return []
    if column not in getattr(shortlist, "columns", []):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for v in shortlist[column]:
        # None/NaN must be skipped BEFORE str(): `str(None)` is "NONE", which
        # would offer the reader a symbol that does not exist and send the
        # council off to fetch it.
        if v is None or (isinstance(v, float) and v != v):
            continue
        s = str(v).strip().upper()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def council_result(symbol: str, *, fetch_ohlcv, fetch_index,
                   fetch_fundamentals, run, regime=None, days: int = 400,
                   min_bars: int = 60):
    """Run the council on ONE symbol with the caller's fetchers.

    Every dependency is injected rather than imported: this module must not
    reach into `dashboard_app` (circular) and must not import `stock_council`
    (which pulls the whole fundamentals stack into any test that touches the
    picker). Returns None when there is not enough history to judge — which the
    caller renders as "not enough history", never as "no setup".
    """
    df = fetch_ohlcv(symbol)
    if df is None or getattr(df, "empty", True) or len(df) < min_bars:
        return None
    return run(symbol, df, fetch_index(), fetch_fundamentals(symbol),
               regime=regime)


def render(shortlist, *, run_council: Callable[[str], Any],
           render_card: Callable[[Any], None], key: str,
           column: str = "symbol") -> None:
    """The picker + the card. Returns nothing; draws into the current container.

    ``run_council(symbol)`` returns whatever ``render_card`` accepts — the page
    owns both, so this module never learns the council's shape.
    """
    symbols = eligible_symbols(shortlist, column)
    if not symbols:
        return
    with st.expander("📋 Plan a name from this list", expanded=False):
        st.caption(BLURB)
        c1, c2 = st.columns([3, 1])
        sym = c1.selectbox("Name", symbols, key=f"plan_pick_{key}",
                           label_visibility="collapsed")
        go = c2.button("Build plan", key=f"plan_go_{key}", type="primary",
                       width="stretch")
        if not go:
            return
        with st.spinner(f"Running the council on {sym}…"):
            try:
                result = run_council(sym)
            except Exception as exc:                        # noqa: BLE001
                # A failed plan says so. A blank expander would read as "no
                # setup here", which is a different and false claim.
                st.warning(f"Could not build a plan for {sym}: {exc}")
                return
        if result is None:
            st.warning(f"Not enough history to plan {sym}.")
            return
        render_card(result)
