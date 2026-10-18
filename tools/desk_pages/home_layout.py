"""Home as a trading terminal (B-179) — the three panes and the left rail.

Home is NOT a registered page: its body stays in dashboard_app.py. What lives
here is the frame it is poured into. `header` runs where the shared stat strip
used to be drawn, so the panes exist before the verdict card renders; the
monolith then fills them with `with _slots.<pane>:` blocks. Streamlit draws a
container where it was CREATED, not where it is filled, which is what lets the
verdict (rendered early) and the Home body (rendered late) share one column.

The rail reads disk only — the close snapshot and the monthly sector map —
because Home never fetches on load. ↻ is the one network call, and the user
presses it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import report_style as rs
import streamlit as st
import ui_tables as uit
import watch_rail as wr


@dataclass
class Slots:
    """Where each part of Home renders. Off Home all four are one container,
    so code written against the slots behaves exactly as it did before."""
    market: Any
    left: Any
    centre: Any
    right: Any


def header(cards: list[str], is_home: bool) -> Slots:
    """Draw the stat cards and return the panes.

    `cards` is `_ov_cards`: Nifty 50, vs 200 SMA, Portfolio P&L, Capital at
    Risk, Alerts Triggered. Off Home they stay one five-up strip; on Home the
    two market cards head the market bar and the three account cards stack in
    the right rail.
    """
    if not is_home:
        st.markdown(rs.strip(cards, cols=5), unsafe_allow_html=True)
        c = st.container()
        return Slots(c, c, c, c)
    market = st.container()
    market.markdown(rs.strip(cards[:2], cols=2), unsafe_allow_html=True)
    left, centre, right = st.columns([1.1, 3.4, 1], gap="small")
    right.markdown(rs.strip(cards[2:], cols=1), unsafe_allow_html=True)
    return Slots(market, left, centre, right)


def _day_colour(v: float) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)) or v == 0:
        return ""
    return f"color: {rs.tone_colors('good' if v > 0 else 'risk')[0]}"


def render_rail(db) -> None:
    """The left rail: picker, filter, scrolling rows, footer actions."""
    try:
        import sectors
        smap = sectors.lookup()
    except Exception:
        smap = {}
    wl_df = db.get_watchlist()
    wl = [] if wl_df is None or wl_df.empty else [str(s) for s in wl_df["symbol"]]

    opts = wr.sector_options(smap, wl)
    choice = st.selectbox("Watch", opts, format_func=lambda o: o[0],
                          key="home_rail_src", label_visibility="collapsed")
    source = choice[1] if choice else wr.WATCHLIST_KEY
    if not smap:
        st.caption("Sector map unavailable")
    query = st.text_input("Filter", key="home_rail_q", placeholder="TCS",
                          label_visibility="collapsed")
    closes, trade_date = wr.read_closes()
    st.caption(f"Closes as of {trade_date}" if closes else "No prices yet — press ↻")

    picked: list[str] = []
    if source == wr.WATCHLIST_KEY and not wl:
        st.info("Watchlist is empty — tick rows in a scan and press ♥.")
    else:
        frame = wr.rail_frame(source, wl, smap, closes, query)
        show = frame.copy()
        show["Symbol"] = [uit.analyze_url(s) for s in frame["Symbol"]]
        event = st.dataframe(
            show.style.map(_day_colour, subset=["Day %"]),
            height=520, hide_index=True, width="stretch",
            key="home_rail_tbl", on_select="rerun", selection_mode="multi-row",
            column_config={
                "Symbol": st.column_config.LinkColumn(
                    "Symbol", display_text=r"symbol=([^&]+)",
                    help="Click the ticker to analyze it (opens in a new tab)"),
                "Close": st.column_config.NumberColumn("Close", format="%.2f"),
                "Day %": st.column_config.NumberColumn("Day %", format="%+.2f%%"),
                "♥": st.column_config.CheckboxColumn("♥", width="small"),
            })
        try:
            rows = list(event.selection.rows)
        except Exception:
            rows = []
        picked = [str(frame.iloc[i]["Symbol"]) for i in rows if i < len(frame)]

    with st.container(horizontal=True, gap="small"):
        if st.button("↻", key="home_rail_refresh", help="Refresh closes from NSE"):
            import trending_stocks
            with st.spinner("Fetching closes…"):
                df, _ = trending_stocks.load_bhav()
            if df is None:
                st.toast("Couldn't reach NSE for prices. The last snapshot stays.")
            else:
                st.rerun()
        if source == wr.WATCHLIST_KEY:
            if st.button(f"✕ Remove {len(picked) or ''}".strip(), key="home_rail_rm",
                         disabled=not picked):
                for s in picked:
                    db.remove_watchlist_symbol(s)
                st.toast(f"Removed {len(picked)}")
                st.rerun()
        else:
            if st.button(f"♥ Add {len(picked) or ''}".strip(), key="home_rail_add",
                         disabled=not picked):
                for s in picked:
                    db.add_watchlist_symbol(s, "Home sector rail")
                st.toast(f"Added {len(picked)} to watchlist")
                st.rerun()
        if st.button("Open Watchlist →", key="home_wl_open"):
            st.session_state["current_page"] = "Watchlist"
            st.rerun()
