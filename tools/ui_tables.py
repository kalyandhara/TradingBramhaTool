#!/usr/bin/env python3
"""ui_tables.py — the desk's one table render path.

Lifted verbatim out of `dashboard_app` (B-87r), where it was a module-level
helper shared by nine call sites across seven pages. It had to move before the
Telegram Signals page could: an extracted page may not reach back into the
monolith, and this was that page's only coupling to it.

Nothing about the rendering changed in the move. The docstring below is the
original's, and it still owns the same two decisions — where the table's LOOK
comes from, and when pagination kicks in.
"""
from __future__ import annotations

from urllib.parse import quote

import pandas as pd
import streamlit as st

DASHBOARD_BASE = "http://localhost:8501"


def analyze_url(sym) -> str | None:
    s = str(sym).strip().upper().replace(".NS", "")
    if not s or s.startswith("^"):
        return None
    return f"{DASHBOARD_BASE}/?nav=analyze&symbol={quote(s, safe='')}"


def chart_url(sym) -> str | None:
    """Deep-link that opens the multi-chart tool (chart_server on :5001) on `sym`."""
    s = str(sym).strip().upper()
    if not s:
        return None
    tkr = s if ("." in s or s.startswith("^")) else f"{s}.NS"
    return f"http://localhost:5001/?symbol={quote(tkr, safe='^')}&tf=1d"


#: The chart-icon family as dataframe LinkColumns (Title-Case column names).
CHART_FAMILY_COLS = ["Chart", "Analyze", "TView", "Screener", "GFin"]


def chart_family_urls(sym) -> dict[str, "str | None"]:
    s = str(sym).strip().upper().replace(".NS", "")
    if not s or s.startswith("^"):
        return {c: None for c in CHART_FAMILY_COLS}
    return {
        "Chart":    chart_url(sym),
        "Analyze":  analyze_url(sym),
        "TView":    f"https://www.tradingview.com/chart/?symbol=NSE%3A{s}",
        "Screener": f"https://www.screener.in/company/{s}/consolidated/",
        "GFin":     f"https://www.google.com/finance/quote/{s}:NSE",
    }


def with_chart_family(df, symbol_col: str):
    """Copy of df with the chart-icon family appended, keyed off `symbol_col`."""
    out = df.copy()
    fam = [chart_family_urls(s) for s in out[symbol_col]]
    for c in CHART_FAMILY_COLS:
        out[c] = [f[c] for f in fam]
    return out


def chart_family_colcfg() -> dict:
    """Column config for the family, mapped from the `columns` registry ids."""
    import columns as _cols
    cfg = _cols.configure(*_cols.CHART_FAMILY)
    return {c: cfg[i] for c, i in zip(CHART_FAMILY_COLS, _cols.CHART_FAMILY)}


def ticker_link(sym, size: int = 15) -> str:
    """The ticker itself as the Analyze link, for tickers inside HTML cards."""
    import report_style as rs
    t = rs.TOKENS
    href = analyze_url(sym)
    if not href:
        return f'<b style="font-size:{size}px;">{sym}</b>'
    return (f'<a href="{href}" target="_blank" rel="noopener" '
            f'title="Analyze {sym} — opens in a new tab" '
            f'style="font-size:{size}px;font-weight:700;color:{t["text"]};'
            f'text-decoration:none;border-bottom:1px dotted {t["border"]};">{sym}</a>')


def analyze_colcfg() -> "st.column_config.LinkColumn":
    return st.column_config.LinkColumn(
        "Analyze", help="Open the 3-POV Council analysis in a new tab",
        display_text="Analyze ↗", width="small",
    )


def with_analyze_col(df, symbol_col: str, after: str | None = "Chart"):
    out = df.copy()
    urls = out[symbol_col].map(analyze_url)
    pos = (out.columns.get_loc(after) + 1) if (after in out.columns) else len(out.columns)
    out.insert(pos, "Analyze", urls)
    return out

def paginated_df(df: "pd.DataFrame", key: str, page_size: int = 25,
                  tint: bool = True, **kwargs) -> None:
    """Render a DataFrame with pagination when it exceeds page_size rows.

    UI-2 (2026-09-10): this is also where the desk's table LOOK is applied, for
    the same reason `columns.py` owns the labels — one render path, one answer.
    Two things happen here that used to happen nowhere:

    * **row_height** is set from `columns.ROW_HEIGHT`, which is what makes a wide
      table scannable. Streamlit's grid is a canvas, so CSS cannot touch it and
      this parameter is the only way in.
    * **tint pairs** are applied from each column's registry `tone` — positive on
      a green wash, negative on red, volume heat above its floor, rank at the
      extremes. Colouring the CELL rather than the number is the single biggest
      readability difference measured against screeningmantis.com
      (analyses/ScreeningMantis-Table-Gap-Analysis.md).

    `tint=False` opts a table out — used where the frame is already a Styler, or
    where a caller has its own colour logic that has not been migrated yet.
    Passing a Styler in is safe either way: `columns.tint` only accepts frames,
    so a Styler falls through untouched.
    """
    import columns as _cols
    kwargs.setdefault("row_height", _cols.ROW_HEIGHT)

    def _paint(frame):
        if not tint or not hasattr(frame, "columns"):
            return frame
        try:
            return _cols.tint(frame)
        except Exception:
            # A tint failure must never cost the user the table. The numbers are
            # the point; the wash is decoration.
            return frame

    n = len(df)
    if n <= page_size:
        st.dataframe(_paint(df), use_container_width=True, hide_index=True, **kwargs)
        return
    n_pages = (n + page_size - 1) // page_size
    _pk = f"_pg_{key}"
    if _pk not in st.session_state:
        st.session_state[_pk] = 1
    pc1, pc2, pc3 = st.columns([1, 3, 1])
    with pc1:
        if st.button("◀ Prev", key=f"{_pk}_prev",
                     disabled=st.session_state[_pk] <= 1):
            st.session_state[_pk] = max(1, st.session_state[_pk] - 1)
            st.rerun()
    with pc2:
        new_page = st.number_input(
            "Page", 1, n_pages, st.session_state[_pk],
            key=f"{_pk}_num", label_visibility="collapsed",
        )
        if int(new_page) != st.session_state[_pk]:
            st.session_state[_pk] = int(new_page)
    with pc3:
        if st.button("Next ▶", key=f"{_pk}_next",
                     disabled=st.session_state[_pk] >= n_pages):
            st.session_state[_pk] = min(n_pages, st.session_state[_pk] + 1)
            st.rerun()
    start = (st.session_state[_pk] - 1) * page_size
    end = min(start + page_size, n)
    st.dataframe(_paint(df.iloc[start:end]), use_container_width=True,
                 hide_index=True, **kwargs)
    st.caption(f"Page {st.session_state[_pk]}/{n_pages} · rows {start + 1}–{end} of {n}")
