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

import logging
import math
from dataclasses import dataclass
from typing import Any

import live_chrome as lc
import report_style as rs
import streamlit as st
import ui_tables as uit
import watch_rail as wr

log = logging.getLogger(__name__)


@dataclass
class Slots:
    """Where each part of Home renders. Off Home all four are one container,
    so code written against the slots behaves exactly as it did before."""
    market: Any
    left: Any
    centre: Any
    right: Any
    verdict: Any
    #: Full-width dark band above the panes (live chrome).
    hero: Any
    #: Full width UNDER the panes: wide tables live here, not in the centre
    #: pane, where a 10-column scan scrolled sideways.
    band: Any


def header(cards: list[str], is_home: bool) -> Slots:
    """Draw the stat cards and return the panes.

    `cards` is `_ov_cards`: Nifty 50, vs 200 SMA, Portfolio P&L, Capital at
    Risk, Alerts Triggered. Off Home they stay one five-up strip; on Home the
    two market cards head the market bar (centre pane, under the verdict) and
    the three account cards stack in the right rail.
    """
    if not is_home:
        st.markdown(rs.strip(cards, cols=5), unsafe_allow_html=True)
        c = st.container()
        return Slots(c, c, c, c, c, c, c)
    # The market bar sits in the centre pane, AFTER the verdict, not across the
    # top: full width, the index charts and breadth bars measured ~450 px and
    # pushed the watchlist rail off the first screen — and B-162 already put
    # the strips after the decision for the same reason.
    hero = st.container()
    st.markdown(lc.PANE_CSS, unsafe_allow_html=True)
    # Ratios are only the fallback: PANE_CSS pins the rails to fixed pixel
    # widths and gives the centre everything else, so a wider page widens the
    # centre instead of fattening the rails.
    left, centre, right = st.columns([1.1, 3.4, 1], gap="small")
    for pane, name in ((left, "left"), (centre, "centre"), (right, "right")):
        pane.markdown(lc.pane_mark(name), unsafe_allow_html=True)
    verdict = centre.container()
    market = centre.container()
    market.markdown(rs.strip(cards[:2], cols=2), unsafe_allow_html=True)
    body = centre.container()
    right.markdown(rs.strip(cards[2:], cols=1), unsafe_allow_html=True)
    band = st.container()
    return Slots(market, left, body, right, verdict, hero, band)


def _day_colour(v: float) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)) or v == 0:
        return ""
    return f"color: {rs.tone_colors('good' if v > 0 else 'risk')[0]}"


def _clear_selection() -> None:
    """New table key on the next run, so no row is pre-selected after an action."""
    st.session_state["home_rail_nonce"] = st.session_state.get("home_rail_nonce", 0) + 1


_COMPONENT: Any = None


def _rail_component():
    """The watch_rail component (B-180): rows with hover charts. Declared once,
    lazily; None when its folder is missing, so the rail falls back to the
    plain table instead of failing."""
    global _COMPONENT
    if _COMPONENT is None:
        import pathlib
        import streamlit.components.v1 as components
        path = pathlib.Path(__file__).resolve().parent.parent / "components" / "watch_rail"
        try:
            if not (path / "index.html").exists():
                raise FileNotFoundError(path / "index.html")
            _COMPONENT = components.declare_component("tb_watch_rail", path=str(path))
        except Exception as e:
            log.warning("watch_rail component unavailable: %s", e)
            _COMPONENT = False
    return _COMPONENT or None


def _rail_table_fallback(frame, source: str, key: str) -> list[str]:
    """The hover-less rail table (B-179), used when the watch_rail component
    folder is missing. Returns the ticked symbols."""
    show = frame.copy()
    show["Symbol"] = [uit.analyze_url(s) for s in frame["Symbol"]]
    if source == wr.WATCHLIST_KEY:
        show = show.drop(columns=["♥"])   # every row is watched; the rail is narrow
    event = st.dataframe(
        # Styler formats Close / Day % (not column_config) because only it
        # has na_rep: a NumberColumn renders a missing price as "None".
        show.style.map(_day_colour, subset=["Day %"])
            .format({"Close": "{:.2f}", "Day %": "{:+.2f}%"}, na_rep="—"),
        height=520, hide_index=True, width="stretch",
        key=key,
        on_select="rerun", selection_mode="multi-row",
        column_config={
            # Pixel widths: the rail is ~280 px wide and auto-sized
            # columns clipped four-digit closes ("6184.50" read "184.50").
            "Symbol": st.column_config.LinkColumn(
                "Symbol", display_text=r"symbol=([^&]+)", width=84,
                help="Click the ticker to analyze it (opens in a new tab)"),
            "Close": st.column_config.Column("Close", width=62),
            "Day %": st.column_config.Column("Day %", width=58),
            "♥": st.column_config.CheckboxColumn("♥", width=28),
        })
    try:
        rows = list(event.selection.rows)
    except Exception:
        rows = []
    return [str(frame.iloc[i]["Symbol"]) for i in rows if i < len(frame)]


def render_rail(db) -> None:
    """The left rail: picker, filter, scrolling rows, footer actions."""
    smap = wr.rail_sector_map()
    wl_df = db.get_watchlist()
    wl = [] if wl_df is None or wl_df.empty else [str(s) for s in wl_df["symbol"]]

    labels = {k: lab for lab, k in wr.sector_options(smap, wl)}
    keys = list(labels)
    source = st.selectbox(
        "Watch", keys, format_func=labels.get, label_visibility="collapsed",
        index=wr.pick_index(keys, st.session_state.get("home_rail_src_key")),
        # The label carries a count, so a keyed widget whose label changed
        # (Add/Remove) is a new widget: `index` from the stored key keeps it.
        key=f"home_rail_src|{len(wl)}") or wr.WATCHLIST_KEY
    st.session_state["home_rail_src_key"] = source
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
        key = wr.table_key(source, query, trade_date,
                           st.session_state.get("home_rail_nonce", 0))
        comp = _rail_component()
        if comp is None:
            picked = _rail_table_fallback(frame, source, key)
        else:
            t = rs.TOKENS
            value = comp(
                rows=wr.rail_rows(frame, source),
                show_heart=source != wr.WATCHLIST_KEY,
                good=rs.tone_colors("good")[0], risk=rs.tone_colors("risk")[0],
                theme={"surface": t["surface"], "surface_alt": t["surface_alt"],
                       "border": t["border"], "text": t["text"],
                       "muted": t["text_muted"], "link": t["info"],
                       "grid": t["surface_alt"], "sma20": t["info"],
                       "sma50": t["accent"]},
                chart_api="http://localhost:5001/api/ohlcv",
                analyze_base=uit.DASHBOARD_BASE + "/?nav=analyze&symbol=",
                height=520, key=key, default={"picked": []})
            shown = set(frame["Symbol"])
            picked = [s for s in (value or {}).get("picked", []) if s in shown]

    with st.container(horizontal=True, gap="small"):
        if st.button("↻", key="home_rail_refresh", help="Refresh closes from NSE"):
            import trending_stocks
            with st.spinner("Fetching closes…"):
                ok, msg = wr.refresh_closes(trending_stocks.load_bhav)
            if ok:
                st.rerun()
            st.toast(msg)
        if source == wr.WATCHLIST_KEY:
            if st.button(f"✕ Remove {len(picked) or ''}".strip(), key="home_rail_rm",
                         disabled=not picked):
                for s in picked:
                    db.remove_watchlist_symbol(s)
                _clear_selection()
                st.toast(f"Removed {len(picked)}")
                st.rerun()
        else:
            to_add = wr.names_to_add(picked, wl)
            if st.button(f"♥ Add {len(to_add) or ''}".strip(), key="home_rail_add",
                         disabled=not to_add):
                for s in to_add:
                    db.add_watchlist_symbol(s, "Home sector rail")
                _clear_selection()
                st.toast(f"Added {len(to_add)} to watchlist")
                st.rerun()
        if st.button("Open Watchlist →", key="home_wl_open"):
            st.session_state["current_page"] = "Watchlist"
            st.rerun()
