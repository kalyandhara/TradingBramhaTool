#!/usr/bin/env python3
"""profit_walk_ui.py — the Streamlit mount for the quarterly profit walk (B-75).

The arithmetic is `row_metrics.profit_qoq_walk`; this is only the part that knows
about tables, session state and a button. It lives outside `dashboard_app.py`
deliberately: the B-87 ratchet's rule is that new UI code does not land in the
monolith, and four helpers that were about to is exactly the growth that ratchet
exists to catch.

── Why a button and not a render-time column ──────────────────────────────────
The walk reads `derive_fundamentals`, which is four yfinance statement calls per
symbol. A Hub table can carry eighty names, so computing it on render would make
an unrelated widget click pay for three hundred network calls. Same shape as the
price columns and the pledge fetch already on those pages: a button fills a
session-state cache, and the column appears once it has.

── Absent means NOT COMPUTED ──────────────────────────────────────────────────
A table that has not been filled does not get the column at all, rather than a
column of blanks. The two read completely differently: blank-everywhere says "no
quarterly history exists for any of these", which would be false.

CLI:
    py -3 -X utf8 tools/profit_walk_ui.py RELIANCE JAMNAAUTO
"""
from __future__ import annotations

import sys
from typing import Any, Callable, Optional

#: Session-state key holding {table_key: {SYMBOL: walk-string}}. Keyed per table
#: because the summary and confluence tables hold different symbol sets and one
#: must not silently serve the other's rows.
STATE_KEY = "profit_walk_cells"

#: The frame column the walk is written to — the `columns.py` registry id, so the
#: label, width and tooltip travel with it to every table that mounts it.
COLUMN = "profit_qoq_walk"


def _st():
    import streamlit as st
    return st


def _default_fetch(symbol: str) -> dict[str, Any]:
    import fundamentals_deep as fdeep
    return fdeep.derive_fundamentals(symbol)


def _norm(symbols) -> list[str]:
    return [t for s in symbols if (t := str(s).strip().upper()) and t != "—"]


def walk_for(symbol: str, fetch: Optional[Callable[[str], dict]] = None) -> str:
    """The walk cell for one symbol, `""` when there is nothing to show.

    `""` rather than None at this boundary on purpose: the store uses presence to
    mean "already looked", so a name with no quarterly history must record an
    answer or it stays in the button's pending count forever.
    """
    import row_metrics as rm
    try:
        deep = (fetch or _default_fetch)(symbol)
        return rm.profit_qoq_walk(deep.get("quarters") or []) or ""
    except Exception:
        return ""


def cells(symbols, key: str, state: dict | None = None) -> dict[str, str]:
    """{SYMBOL: walk} for whatever has already been fetched for this table."""
    store = (state if state is not None else _st().session_state).setdefault(STATE_KEY, {})
    have = store.setdefault(key, {})
    return {s: have[s] for s in _norm(symbols) if s in have}


def pending(symbols, key: str, state: dict | None = None) -> list[str]:
    """Symbols in this table with no stored answer yet."""
    store = (state if state is not None else _st().session_state).get(STATE_KEY, {})
    have = store.get(key, {})
    return [s for s in dict.fromkeys(_norm(symbols)) if s not in have]


def fill(symbols, key: str, fetch: Optional[Callable[[str], dict]] = None,
         state: dict | None = None, progress: Callable[[int, int], None] | None = None) -> int:
    """Fetch and store the walk for `symbols`. Returns how many were computed."""
    store = (state if state is not None else _st().session_state).setdefault(STATE_KEY, {})
    have = store.setdefault(key, {})
    todo = pending(symbols, key, state)
    for n, sym in enumerate(todo, 1):
        have[sym] = walk_for(sym, fetch)
        if progress:
            progress(n, len(todo))
    return len(todo)


def attach(df, symbol_col: str, key: str, state: dict | None = None):
    """Mount the column on a table — only once it has been filled."""
    if df is None or getattr(df, "empty", True) or symbol_col not in df.columns:
        return df
    have = cells(df[symbol_col], key, state)
    if not have:
        return df
    df = df.copy()
    df[COLUMN] = [have.get(str(s).strip().upper(), "") for s in df[symbol_col]]
    return df


def fill_button(symbols, key: str, label: str,
                fetch: Optional[Callable[[str], dict]] = None) -> None:
    """The button that fills this table's cache, then reruns the page."""
    st = _st()
    todo = pending(symbols, key)
    if not todo:
        return
    if st.button(f"Add profit walk ({len(todo)} names)", key=f"{key}_pqw",
                 help="Quarter-on-quarter net profit change per name, oldest "
                      "first. Reads the quarterly statements (four calls per "
                      "symbol, cached an hour), which is why it is not computed "
                      "on every render. SEQUENTIAL, so it is a shape and not a "
                      "growth rate — see the column's own tooltip."):
        prog = st.progress(0.0, text=f"0/{len(todo)}")
        got = fill(symbols, key, fetch,
                   progress=lambda n, t: prog.progress(n / t, text=f"{n}/{t}"))
        prog.empty()
        st.success(f"{label}: profit walk ready for {got} name(s).")
        st.rerun()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    syms = sys.argv[1:] or ["RELIANCE"]
    for s in syms:
        print(f"{s:14} {walk_for(s) or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
