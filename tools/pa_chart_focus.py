#!/usr/bin/env python3
"""pa_chart_focus.py — which charts the Predictive Analysis grid shows.

  pane 1   the focus: the ticker just clicked (replaced on every click)
  pane 2   its context: the stock's sector index, or Nifty 50
  pane 3+  only what the user pinned to compare — nothing arrives uninvited

The grid never becomes a trail of recent clicks: eight unrelated charts are not
a comparison. Pane counts the chart tool offers are 1/2/4/6/8, so a spare slot
is filled with a market benchmark rather than whatever the pane last held.

Sector context is limited to indices the chart server can actually draw: yfinance
serves full history only for these (B-80; the rest return one bar), so any other
sector falls back to Nifty 50 and the caption says so.
"""
from __future__ import annotations

from urllib.parse import urlencode

MAX_PINS = 6
PANE_COUNTS = (1, 2, 4, 6, 8)
BENCHMARK = ("^NSEI", "Nifty 50")

#: NSE macro sector -> (chartable index ticker, label). Verified 2026-09-26
#: against the chart server's /api/ohlcv: 300 bars each; the others return 1.
CHARTABLE_SECTOR_INDEX = {
    "Information Technology": ("^CNXIT", "Nifty IT"),
    "Telecommunication": ("^CNXIT", "Nifty IT"),
    "Healthcare": ("^CNXPHARMA", "Nifty Pharma"),
}
_FILLERS = ["^NSEI", "^NSEBANK", "^CNXIT", "^CNXPHARMA"]


def context_for(sector: str | None) -> tuple[str, str, bool]:
    """(ticker, label, is_sector_index) for pane 2."""
    if sector in CHARTABLE_SECTOR_INDEX:
        t, label = CHARTABLE_SECTOR_INDEX[sector]
        return t, label, True
    return BENCHMARK[0], BENCHMARK[1], False


def pane_symbols(focus: str, context: str, pins: list[str]) -> list[str]:
    """Panes 2..N in order, padded with benchmarks up to an offered pane count."""
    rest = [context] + [p for p in pins if p not in (focus, context)][:MAX_PINS]
    n = next(c for c in PANE_COUNTS if c >= 1 + len(rest))
    for f in _FILLERS:
        if len(rest) >= n - 1:
            break
        if f not in rest:
            rest.append(f)
    return rest[: n - 1]


def chart_query(focus: str, context: str, pins: list[str]) -> str:
    """Query string for the chart tool: own layout, focus, compares, pane count."""
    rest = pane_symbols(focus, context, pins)
    return urlencode({"layout": "pa", "compare": ",".join(_nse(s) for s in rest),
                      "charts": 1 + len(rest)}, safe=",^")


def _nse(sym: str) -> str:
    s = sym.strip().upper()
    return s if ("." in s or s.startswith("^")) else f"{s}.NS"


def stock_sector(sym: str) -> str | None:
    try:
        import nse_universe as nu
        return nu.industry_map("niftytotalmarket").get(sym.strip().upper())
    except Exception:
        return None


def render_pin_bar(sym: str) -> tuple[str, str]:
    """Pin controls above the chart. Returns (context ticker, caption text)."""
    import streamlit as st
    pins: list[str] = st.session_state.setdefault("pa_pins", [])
    ctx, label, is_sector = context_for(stock_sector(sym))

    c1, c2 = st.columns([1.3, 4], vertical_alignment="center")
    if sym in pins:
        if c1.button(f"📌 Unpin {sym}", key="pa_unpin_focus", type="secondary"):
            pins.remove(sym)
            st.rerun()
    elif c1.button(f"📌 Pin {sym} to compare", key="pa_pin_focus",
                   disabled=len(pins) >= MAX_PINS,
                   help=f"Keeps {sym} in the grid after you click another ticker "
                        f"(max {MAX_PINS})"):
        pins.append(sym)
        st.rerun()
    with c2:
        if pins:
            pc = st.columns(len(pins) + 1)
            for i, p in enumerate(pins):
                if pc[i].button(f"✕ {p}", key=f"pa_unpin_{p}", type="tertiary",
                                help=f"Remove {p} from the comparison"):
                    pins.remove(p)
                    st.rerun()
            if pc[-1].button("Clear", key="pa_pins_clear", type="tertiary"):
                pins.clear()
                st.rerun()
    note = (f"Chart 2: **{label}** (its sector index)" if is_sector else
            f"Chart 2: **{label}** — no chartable sector index for this stock's sector")
    extra = f" · pinned: {', '.join(pins)}" if pins else " · pin tickers to add more charts"
    return ctx, note + extra
