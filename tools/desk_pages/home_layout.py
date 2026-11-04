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


#: Height of the rail's list (px). Tall enough to run alongside the centre
#: pane (verdict, market bar, action map ≈ 1,600 px) instead of stopping at
#: half its height and leaving the left column blank.
RAIL_HEIGHT = 1350

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
        height=RAIL_HEIGHT, hide_index=True, width="stretch",
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


_SEARCH: Any = None


def _search_component():
    """The ribbon's typeahead (components/symbol_search), reused as the rail's
    "+ Add stock" box. None when its folder is missing."""
    global _SEARCH
    if _SEARCH is None:
        import pathlib
        import streamlit.components.v1 as components
        path = pathlib.Path(__file__).resolve().parent.parent / "components" / "symbol_search"
        try:
            if not (path / "index.html").exists():
                raise FileNotFoundError(path / "index.html")
            _SEARCH = components.declare_component("tb_rail_symsearch", path=str(path))
        except Exception as e:
            log.warning("rail symbol search unavailable: %s", e)
            _SEARCH = False
    return _SEARCH or None


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _company_names() -> dict[str, str]:
    """Symbol -> company name from the symbol directory (disk), for the rail's
    second line. {} when unavailable: the line is then just blank."""
    try:
        import symbol_directory as symdir
        return {str(e["display"]).upper(): str(e.get("name") or "")
                for e in symdir.get_directory() if e.get("display")}
    except Exception as e:
        log.warning("company names unavailable: %s", e)
        return {}


def _month_closes(symbols: list[str]) -> dict[str, list[float]]:
    """One batched yfinance call: ~1 month of daily closes per symbol. Only
    ever called from a button — Home never fetches on load."""
    import yfinance as yf
    tick = {wr.chart_symbol(s): s for s in symbols}
    data = yf.download(list(tick), period="1mo", interval="1d", progress=False,
                       group_by="ticker", auto_adjust=False, threads=True)
    out: dict[str, list[float]] = {}
    for t, s in tick.items():
        try:
            # group_by="ticker" keeps the ticker level even for ONE ticker;
            # the flat shape is the fallback for older yfinance.
            col = data[t]["Close"] if t in data.columns.get_level_values(0) else data["Close"]
            if hasattr(col, "columns"):
                col = col.iloc[:, 0]
            out[s] = [float(v) for v in col.dropna()]
        except Exception:
            continue
    return out


def _go_to(page: str, symbol: str) -> None:
    """The same jump `?nav=analyze` makes, without a new tab. `page` is kept
    for the rail's old "predict" button value: Predictive Analysis was merged
    into the Stock Analyzer, so both land there."""
    st.session_state["current_page"] = "Stock Analyzer"
    st.session_state["selected_symbol"] = symbol
    st.session_state["last_analyzed"] = symbol   # triggers the auto-run


def scan_table(df, extra_cols: list[dict], *, key: str, close_col: str,
               pct_col: str, pct_label: str = "Close · Day",
               no_check: bool = False, pct_plain: bool = False) -> list[str] | None:
    """A scan's hits in the watch_rail component: the rail's rows and hover
    chart, plus the scan's own columns. Returns the ticked symbols, or None
    when the component is unavailable so the caller draws its plain table.

    `no_check` drops the ticks, for tables with nothing to do with a selection;
    `pct_plain` draws the % uncoloured, for a distance rather than a move."""
    comp = _rail_component()
    if comp is None:
        return None
    rows = wr.scan_rows(df, extra_cols, close_col=close_col, pct_col=pct_col,
                        names=_company_names(), sparks=wr.read_sparks())
    t = rs.TOKENS
    value = comp(
        rows=rows, show_heart=False, extra_cols=extra_cols, pct_label=pct_label,
        no_check=no_check, pct_plain=pct_plain,
        good=rs.tone_colors("good")[0], risk=rs.tone_colors("risk")[0],
        theme={"surface": t["surface"], "surface_alt": t["surface_alt"],
               "border": t["border"], "text": t["text"],
               "muted": t["text_muted"], "link": t["info"],
               "grid": t["surface_alt"], "sma20": t["info"],
               "sma50": t["accent"]},
        chart_api="http://localhost:5001/api/ohlcv",
        analyze_base=uit.DASHBOARD_BASE + "/?nav=analyze&symbol=",
        height=min(520, 28 + 45 * max(len(rows), 1)),
        key=key, default={"picked": [], "open": None})
    shown = {r["symbol"] for r in rows}
    value = value or {}
    req = value.get("open")
    if (isinstance(req, dict) and req.get("symbol") in shown
            and req.get("page") in ("predict", "analyze")
            and req.get("n") != st.session_state.get(f"_{key}_open_n")):
        st.session_state[f"_{key}_open_n"] = req.get("n")
        _go_to(req["page"], req["symbol"])
        st.rerun()
    return [s for s in value.get("picked", []) if s in shown]


def candidate_table(lst: dict, *, key: str, current: str | None) -> str | None:
    """One Stock Analyzer candidate list (`watch_rail.candidate_lists`) as rail
    rows: no ticks, the current stock highlighted, a ticker click loads it here.

    Returns the clicked symbol, "" when nothing was clicked, or None when the
    component is unavailable so the caller draws its old buttons."""
    comp = _rail_component()
    if comp is None:
        return None
    df = wr.with_closes(lst["df"], wr.read_closes()[0])
    cols = []
    if lst["df"]["rating"].notna().any():
        cols.append({"key": "rating", "label": "Rtg", "fmt": "num", "width": 30})
    if lst["tag"]:
        cols.append({"key": "note", "label": "Note", "fmt": "text", "width": 96})
    rows = wr.scan_rows(df, cols, close_col="close", pct_col="day_pct",
                        names=_company_names(), sparks=wr.read_sparks())
    t = rs.TOKENS
    value = comp(
        rows=rows, show_heart=False, extra_cols=cols, no_check=True,
        link_mode="select", current=(current or "").upper(),
        good=rs.tone_colors("good")[0], risk=rs.tone_colors("risk")[0],
        theme={"surface": t["surface"], "surface_alt": t["surface_alt"],
               "border": t["border"], "text": t["text"],
               "muted": t["text_muted"], "link": t["info"],
               "grid": t["surface_alt"], "sma20": t["info"],
               "sma50": t["accent"]},
        chart_api="http://localhost:5001/api/ohlcv",
        analyze_base=uit.DASHBOARD_BASE + "/?nav=analyze&symbol=",
        # The panel sits in a 680 px box with the switcher and caption above it;
        # taller and the box scrolls the switcher out of sight.
        height=min(530, 28 + 45 * max(len(rows), 1)),
        key=key, default={"picked": [], "open": None})
    req = (value or {}).get("open")
    shown = {r["symbol"] for r in rows}
    if (isinstance(req, dict) and req.get("symbol") in shown
            and req.get("page") in ("select", "analyze")
            and req.get("n") != st.session_state.get(f"_{key}_open_n")):
        st.session_state[f"_{key}_open_n"] = req.get("n")
        return req["symbol"]
    return ""


@st.dialog("Watchlists")
def _list_dialog(db, source: str, lists) -> None:
    """Create, rename and delete named lists. A dialog, not a popover: every
    popover in the app is styled as the nav's two-column page menu, and a
    popover stays open across the rerun that follows an action."""
    with st.form("home_rail_new_form", clear_on_submit=True, border=False):
        new = st.text_input("New watchlist", placeholder="e.g. Swing picks",
                            max_chars=db.WATCHLIST_NAME_MAX)
        if st.form_submit_button("＋ Create list", type="primary"):
            try:
                lid = db.create_watchlist(new)
            except ValueError as e:
                st.error(str(e))
            else:
                st.session_state["home_rail_src_key"] = wr.list_key(lid)
                _clear_selection()
                st.rerun()
    lid = wr.list_id_of(source)
    if lid is None:
        st.caption("Pick one of your lists in the rail to rename or delete it. "
                   "♥ Your watchlist is the default and stays.")
        return
    current = next((n for i, n, _ in lists if i == lid), "")
    st.divider()
    st.markdown(f"**{current}**")
    name = st.text_input("Rename", value=current, key=f"home_rail_rename|{lid}",
                         max_chars=db.WATCHLIST_NAME_MAX)
    if st.button("Rename", key="home_rail_rename_btn",
                 disabled=not name.strip() or name.strip() == current):
        try:
            db.rename_watchlist(lid, name)
        except ValueError as e:
            st.error(str(e))
        else:
            st.rerun()
    sure = st.checkbox(f"Yes, delete \"{current}\" and its stocks",
                       key=f"home_rail_del_ok|{lid}")
    if st.button("Delete list", key="home_rail_delete", disabled=not sure):
        db.delete_watchlist(lid)
        st.session_state["home_rail_src_key"] = wr.WATCHLIST_KEY
        _clear_selection()
        st.rerun()


def _list_manager(db, source: str, lists) -> None:
    if st.button("⋯", key="home_rail_menu", width="stretch",
                 help="New / rename / delete watchlists"):
        _list_dialog(db, source, lists)


def _add_stock_box(db, source: str, search_options: str, label: str) -> None:
    """Typeahead that adds the picked stock to the list on screen."""
    comp = _search_component()
    if comp is None or not search_options:
        return
    picked = comp(options=search_options, placeholder=f"＋ Add stock to {label}", theme="light",
                  key=f"home_rail_add_search|{source}", default=None)
    # The value persists across reruns; act only when its counter moves.
    if not (isinstance(picked, dict) and picked.get("symbol")):
        return
    if picked.get("n") == st.session_state.get("_home_rail_add_n"):
        return
    st.session_state["_home_rail_add_n"] = picked.get("n")
    sym = str(picked["symbol"]).strip().upper()
    if not wr.is_safe_symbol(sym):
        st.toast("Not a ticker symbol")
        return
    lid = wr.list_id_of(source)
    if lid is None:
        wl_df = db.get_watchlist()
        added = wl_df is None or sym not in set(wl_df["symbol"])
        if added:
            db.add_watchlist_symbol(sym, "Home rail")
    else:
        added = db.add_watchlist_item(lid, sym)
    if added:
        wr.refresh_sparks([sym], _month_closes)      # a user action: one fetch
    st.toast(f"Added {sym}" if added else f"{sym} is already on {label}")
    _clear_selection()
    st.rerun()


def render_rail(db, search_options: str = "") -> None:
    """The left rail: list picker + manager, add-stock box, filter, rows
    (Google Finance style), footer actions."""
    smap = wr.rail_sector_map()
    wl_df = db.get_watchlist()
    wl = [] if wl_df is None or wl_df.empty else [str(s) for s in wl_df["symbol"]]
    try:
        lists_df = db.get_watchlists()
        lists = [(int(r.id), str(r.name), int(r.n)) for r in lists_df.itertuples()]
    except Exception as e:
        log.warning("named watchlists unavailable: %s", e)
        lists = []

    labels = {k: lab for lab, k in wr.sector_options(smap, wl, lists)}
    keys = list(labels)
    pick_col, menu_col = st.columns([5, 1], gap="small", vertical_alignment="center")
    with pick_col:
        source = st.selectbox(
            "Watch", keys, format_func=labels.get, label_visibility="collapsed",
            index=wr.pick_index(keys, st.session_state.get("home_rail_src_key")),
            # Labels carry counts, so a keyed widget whose labels changed is a
            # new widget: `index` from the stored key keeps the choice.
            key=f"home_rail_src|{hash(tuple(labels.values()))}") or wr.WATCHLIST_KEY
    st.session_state["home_rail_src_key"] = source
    with menu_col:
        _list_manager(db, source, lists)

    lid = wr.list_id_of(source)
    members = db.get_watchlist_items(lid) if lid is not None else None
    in_list = wr.is_list_source(source)
    list_label = ("your watchlist" if source == wr.WATCHLIST_KEY
                  else next((n for i, n, _ in lists if i == lid), "this list"))
    if in_list:
        _add_stock_box(db, source, search_options, list_label)
    if not smap:
        st.caption("Sector map unavailable")
    query = st.text_input("Filter", key="home_rail_q", placeholder="Filter TCS",
                          label_visibility="collapsed")
    closes, trade_date = wr.read_closes()
    st.caption(f"Closes as of {trade_date} · 1M line from ↻" if closes
               else "No prices yet — press ↻")

    picked: list[str] = []
    shown_syms: list[str] = []
    if source == wr.WATCHLIST_KEY and not wl:
        st.info("Watchlist is empty — add a stock above, or tick rows in a scan and press ♥.")
    elif lid is not None and not members:
        st.info("This list is empty — add a stock above.")
    else:
        frame = wr.rail_frame(source, wl, smap, closes, query, members=members)
        shown_syms = [str(s) for s in frame["Symbol"]]
        key = wr.table_key(source, query, trade_date,
                           st.session_state.get("home_rail_nonce", 0))
        comp = _rail_component()
        if comp is None:
            picked = _rail_table_fallback(frame, source, key)
        else:
            t = rs.TOKENS
            value = comp(
                rows=wr.rail_rows(frame, source, _company_names(), wr.read_sparks()),
                show_heart=not in_list,
                good=rs.tone_colors("good")[0], risk=rs.tone_colors("risk")[0],
                theme={"surface": t["surface"], "surface_alt": t["surface_alt"],
                       "border": t["border"], "text": t["text"],
                       "muted": t["text_muted"], "link": t["info"],
                       "grid": t["surface_alt"], "sma20": t["info"],
                       "sma50": t["accent"]},
                chart_api="http://localhost:5001/api/ohlcv",
                analyze_base=uit.DASHBOARD_BASE + "/?nav=analyze&symbol=",
                height=RAIL_HEIGHT, key=key, default={"picked": [], "open": None})
            shown = set(shown_syms)
            value = value or {}
            picked = [s for s in value.get("picked", []) if s in shown]
            req = value.get("open")
            if (isinstance(req, dict) and req.get("symbol") in shown
                    and req.get("page") in ("predict", "analyze")
                    and req.get("n") != st.session_state.get("_home_rail_open_n")):
                st.session_state["_home_rail_open_n"] = req.get("n")
                _go_to(req["page"], req["symbol"])
                st.rerun()

    with st.container(horizontal=True, gap="small"):
        if st.button("↻", key="home_rail_refresh",
                     help="Refresh closes from NSE and the 1-month lines for the rows shown"):
            import trending_stocks
            with st.spinner("Fetching closes…"):
                ok, msg = wr.refresh_closes(trending_stocks.load_bhav)
                if shown_syms:
                    _, smsg = wr.refresh_sparks(shown_syms, _month_closes)
                    msg = f"{msg} · {smsg}"
            st.toast(msg)
            st.rerun()
        if in_list:
            if st.button(f"✕ Remove {len(picked) or ''}".strip(), key="home_rail_rm",
                         disabled=not picked):
                for s in picked:
                    if lid is None:
                        db.remove_watchlist_symbol(s)
                    else:
                        db.remove_watchlist_item(lid, s)
                _clear_selection()
                st.toast(f"Removed {len(picked)}")
                st.rerun()
        else:
            target = wr.WATCHLIST_KEY
            if lists:
                tkeys = [wr.WATCHLIST_KEY] + [wr.list_key(i) for i, _, _ in lists]
                tnames = {wr.WATCHLIST_KEY: "♥ Watchlist",
                          **{wr.list_key(i): n for i, n, _ in lists}}
                target = st.selectbox("Add to", tkeys, format_func=tnames.get,
                                      key="home_rail_add_target",
                                      label_visibility="collapsed")
            tid = wr.list_id_of(target)
            have = wl if tid is None else db.get_watchlist_items(tid)
            to_add = wr.names_to_add(picked, have)
            if st.button(f"♥ Add {len(to_add) or ''}".strip(), key="home_rail_add",
                         disabled=not to_add):
                for s in to_add:
                    if tid is None:
                        db.add_watchlist_symbol(s, "Home sector rail")
                    else:
                        db.add_watchlist_item(tid, s)
                _clear_selection()
                st.toast(f"Added {len(to_add)}")
                st.rerun()
        if st.button("Open Watchlist →", key="home_wl_open"):
            st.session_state["current_page"] = "Watchlist"
            st.rerun()


# ── Right-rail thumbnail cards ────────────────────────────────────────────────

def render_scanner_hub_thumb(hits: list[dict], scanner_name: str) -> None:
    """Compact Scanner Hub summary card for the right rail.

    Shows the scanner name, hit count, and up to 8 symbol chips so the user
    can see at a glance what the last run found. The full grid lives on
    Scanner Hub; this is the thumbnail only."""
    t = rs.TOKENS
    band = f'background:{t["surface_alt"]};border:1px solid {t["border"]};'
    band += f'border-radius:8px;padding:8px 10px 6px;margin-bottom:8px;'
    name_html = (
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.07em;'
        f'text-transform:uppercase;color:{t["text_muted"]};margin-bottom:4px;">'
        f'Scanner Hub</div>'
        f'<div style="font-size:12px;font-weight:600;color:{t["text"]};'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'
        f'margin-bottom:4px;" title="{scanner_name}">{scanner_name}</div>'
    )
    n = len(hits)
    if not hits:
        body_html = (f'<div style="font-size:11px;color:{t["text_muted"]};">'
                     f'No results — run a scanner.</div>')
    else:
        chip_css = (f'display:inline-block;font-size:11px;font-weight:600;'
                    f'background:{t["surface"]};border:1px solid {t["border"]};'
                    f'border-radius:4px;padding:1px 5px;margin:1px 2px 1px 0;'
                    f'color:{t["text"]};')
        chips = "".join(
            f'<span style="{chip_css}">'
            f'{h["symbol"].upper().replace(".NS","")}</span>'
            for h in hits[:8]
        )
        more = f' <span style="font-size:10px;color:{t["text_muted"]};">+{n-8} more</span>' if n > 8 else ""
        body_html = (
            f'<div style="font-size:11px;color:{t["text_muted"]};margin-bottom:4px;">'
            f'{n} hit{"s" if n != 1 else ""}</div>'
            f'<div style="line-height:1.6;">{chips}{more}</div>'
        )
    st.markdown(f'<div style="{band}">{name_html}{body_html}</div>',
                unsafe_allow_html=True)
    if st.button("Scanner Hub →", key="home_right_scan_nav", width="stretch"):
        st.session_state["current_page"] = "Scanner Hub"
        st.rerun()


def render_oi_momentum_thumb(recs: list[dict], trade_date) -> None:
    """Compact OI Momentum summary card for the right rail.

    Shows a bullish/bearish breadth bar and up to 4 names per key quadrant.
    The full page has filters, tables and index futures; this is the
    thumbnail only."""
    import nse_oi_momentum as oim
    t = rs.TOKENS
    band = (f'background:{t["surface_alt"]};border:1px solid {t["border"]};'
            f'border-radius:8px;padding:8px 10px 6px;margin-bottom:8px;')
    date_str = trade_date.strftime("%d %b") if hasattr(trade_date, "strftime") else str(trade_date or "")
    header_html = (
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.07em;'
        f'text-transform:uppercase;color:{t["text_muted"]};margin-bottom:4px;">'
        f'OI Momentum · {date_str}</div>'
    )
    if not recs:
        body_html = (f'<div style="font-size:11px;color:{t["text_muted"]};">'
                     f'F&amp;O bhavcopy unavailable.</div>')
    else:
        b = oim.breadth(recs)
        lb = b[oim.LONG_BUILDUP]
        sb = b[oim.SHORT_BUILDUP]
        sc = b[oim.SHORT_COVERING]
        lu = b[oim.LONG_UNWINDING]
        total = lb + sb + sc + lu or 1
        bull_pct = round((lb + sc) / total * 100)
        bear_pct = 100 - bull_pct
        # Mini breadth bar
        bar_html = (
            f'<div style="display:flex;height:5px;border-radius:3px;overflow:hidden;'
            f'margin-bottom:6px;">'
            f'<div style="flex:{bull_pct};background:#22c55e;"></div>'
            f'<div style="flex:{bear_pct};background:#ef4444;"></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:10px;color:{t["text_muted"]};margin-bottom:6px;">'
            f'<span>&#x25B2; {lb} built · {sc} cov</span>'
            f'<span>{sb} built · {lu} unw &#x25BC;</span>'
            f'</div>'
        )
        # Top names per quadrant
        def _chips(quadrant: str, color: str) -> str:
            names = [r["symbol"].replace(".NS", "")
                     for r in recs if r.get("reading") == quadrant][:4]
            if not names:
                return ""
            chip_css = (f'display:inline-block;font-size:10px;font-weight:600;'
                        f'background:{t["surface"]};border:1px solid {color}44;'
                        f'border-radius:4px;padding:1px 4px;margin:1px 2px 1px 0;'
                        f'color:{color};')
            return "".join(f'<span style="{chip_css}">{s}</span>' for s in names)

        lb_chips = _chips(oim.LONG_BUILDUP, "#22c55e")
        sb_chips = _chips(oim.SHORT_BUILDUP, "#ef4444")
        body_html = bar_html
        if lb_chips:
            body_html += (f'<div style="font-size:9px;color:{t["text_muted"]};'
                          f'margin:2px 0 1px;">Long build-up</div>{lb_chips}')
        if sb_chips:
            body_html += (f'<div style="font-size:9px;color:{t["text_muted"]};'
                          f'margin:4px 0 1px;">Short build-up</div>{sb_chips}')
    st.markdown(f'<div style="{band}">{header_html}{body_html}</div>',
                unsafe_allow_html=True)
    if st.button("OI Momentum →", key="home_right_oi_nav", width="stretch"):
        st.session_state["current_page"] = "OI Momentum"
        st.rerun()


def render_money_flow_thumb(grid) -> None:
    """Compact Sector Money Flow card for the right rail.

    Shows a bullish/bearish sector-breadth bar and the top positive and
    bottom negative sectors as colour-coded chips. Full ridgeline and
    full grid live on the Sector Money Flow page."""
    t = rs.TOKENS
    band = (f'background:{t["surface_alt"]};border:1px solid {t["border"]};'
            f'border-radius:8px;padding:8px 10px 6px;margin-bottom:8px;')
    header_html = (
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.07em;'
        f'text-transform:uppercase;color:{t["text_muted"]};margin-bottom:4px;">'
        f'Sector Money Flow · last month</div>'
    )
    if grid is None or grid.get("error") or (grid.get("rows") is None):
        body_html = (f'<div style="font-size:11px;color:{t["text_muted"]};">'
                     f'No data yet — press ↻.</div>')
    else:
        df = grid["rows"]
        if df.empty:
            body_html = (f'<div style="font-size:11px;color:{t["text_muted"]};">'
                         f'No sectors with enough history.</div>')
        else:
            col0 = grid["columns"][0]
            pos_df = df[df[col0] > 0].head(4)
            neg_df = df[df[col0] <= 0].tail(3)
            n_pos = int((df[col0] > 0).sum())
            n_tot = len(df)
            bull_pct = round(n_pos / n_tot * 100) if n_tot else 0
            bear_pct = 100 - bull_pct
            bar_html = (
                f'<div style="display:flex;height:5px;border-radius:3px;overflow:hidden;'
                f'margin-bottom:4px;">'
                f'<div style="flex:{bull_pct};background:#22c55e;"></div>'
                f'<div style="flex:{bear_pct};background:#ef4444;"></div>'
                f'</div>'
                f'<div style="font-size:10px;color:{t["text_muted"]};margin-bottom:5px;">'
                f'{n_pos} of {n_tot} sectors positive</div>'
            )

            def _chip(name: str, cmf: float, color: str) -> str:
                label = name[:14] + "…" if len(name) > 14 else name
                chip_css = (f'display:inline-block;font-size:10px;font-weight:500;'
                            f'background:{t["surface"]};border:1px solid {color}44;'
                            f'border-radius:4px;padding:1px 5px;margin:1px 2px 1px 0;'
                            f'color:{color};white-space:nowrap;')
                return f'<span style="{chip_css}" title="{name} CMF {cmf:.3f}">{label}</span>'

            pos_chips = "".join(_chip(r["sector"], r[col0], "#22c55e")
                                for _, r in pos_df.iterrows())
            neg_chips = "".join(_chip(r["sector"], r[col0], "#ef4444")
                                for _, r in neg_df.iterrows())
            body_html = bar_html
            if pos_chips:
                body_html += (f'<div style="font-size:9px;color:{t["text_muted"]};'
                              f'margin:2px 0 1px;">In-flow</div>{pos_chips}')
            if neg_chips:
                body_html += (f'<div style="font-size:9px;color:{t["text_muted"]};'
                              f'margin:4px 0 1px;">Out-flow</div>{neg_chips}')
    st.markdown(f'<div style="{band}">{header_html}{body_html}</div>',
                unsafe_allow_html=True)
    if st.button("Sector Map →", key="home_right_mf_nav", width="stretch"):
        st.session_state["current_page"] = "Sector Map"
        st.rerun()


# ── Shared helpers for Sector Map thumbnails ──────────────────────────────────

def _sm_band_html(t: dict, title: str) -> str:
    return (f'<div style="background:{t["surface_alt"]};border:1px solid {t["border"]};'
            f'border-radius:8px;padding:8px 10px 6px;margin-bottom:8px;">'
            f'<div style="font-size:10px;font-weight:700;letter-spacing:.07em;'
            f'text-transform:uppercase;color:{t["text_muted"]};margin-bottom:4px;">'
            f'{title}</div>')


def _sm_chips(names: list[str], values: list[float | None], color: str, t: dict,
              fmt: str = "{:+.1f}%") -> str:
    chip_css = (f'display:inline-flex;align-items:center;gap:3px;font-size:10px;'
                f'font-weight:500;background:{t["surface"]};border:1px solid {color}44;'
                f'border-radius:4px;padding:1px 5px;margin:1px 2px 1px 0;color:{color};'
                f'white-space:nowrap;')
    out = ""
    for name, val in zip(names, values):
        label = name[:13] + "…" if len(name) > 13 else name
        val_str = (fmt.format(val) if val is not None else "")
        out += (f'<span style="{chip_css}" title="{name}">'
                f'{label}'
                f'{"&nbsp;<span style=\'font-size:9px;opacity:.8\'>" + val_str + "</span>" if val_str else ""}'
                f'</span>')
    return out


def _sm_not_built(t: dict) -> str:
    return (f'<div style="font-size:11px;color:{t["text_muted"]};">'
            f'Not built yet — visit Sector Map.</div>')


def render_sector_heatmap_thumb(sector_data: dict) -> None:
    """Compact 1D sector performance heatmap card for the right rail."""
    t = rs.TOKENS
    html = _sm_band_html(t, "Sector Heatmap · 1D")
    if not sector_data:
        html += _sm_not_built(t)
    else:
        import snapshot_registry as _snapreg
        from desk_pages.stock_panels import _period_return  # noqa: PLC0415
        rows = []
        for ticker, name in _snapreg.SECTOR_DISPLAY_NAMES.items():
            df_s = sector_data.get(ticker)
            if df_s is None:
                continue
            ret = _period_return(df_s, 1)
            if ret is not None:
                rows.append((name, ret))
        rows.sort(key=lambda x: x[1], reverse=True)
        top = rows[:3]
        bot = rows[-3:]
        if top:
            names_t, vals_t = zip(*top)
            html += (f'<div style="font-size:9px;color:{t["text_muted"]};margin:2px 0 1px;">'
                     f'Top</div>' + _sm_chips(list(names_t), list(vals_t), "#22c55e", t))
        if bot:
            names_b, vals_b = zip(*bot)
            html += (f'<div style="font-size:9px;color:{t["text_muted"]};margin:4px 0 1px;">'
                     f'Bottom</div>' + _sm_chips(list(names_b), list(vals_b), "#ef4444", t))
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    if st.button("Sector Map →", key="home_right_hm_nav", width="stretch"):
        st.session_state["current_page"] = "Sector Map"
        st.rerun()


def render_sector_ranking_thumb() -> None:
    """Compact Sector Ranking card — only renders data if already built this session."""
    t = rs.TOKENS
    html = _sm_band_html(t, "Sector Ranking · rotation + health")
    if not st.session_state.get("srk_ran"):
        html += _sm_not_built(t)
    else:
        try:
            import sector_ranking as _srk
            g = _srk.ranking_grid(_srk.GROUPINGS.get(
                st.session_state.get("srk_group", "industry"), "nifty500"),
                smap=_srk.group_map(st.session_state.get("srk_group", "industry")))
            df = g.get("rows")
            if g.get("error") or df is None or df.empty:
                html += (f'<div style="font-size:11px;color:{t["text_muted"]};">'
                         f'{g.get("error") or "No data."}</div>')
            else:
                top = df.head(3)
                bot = df.tail(3)
                html += (f'<div style="font-size:9px;color:{t["text_muted"]};margin:2px 0 1px;">'
                         f'Inflow</div>' +
                         _sm_chips(list(top["sector"]), list(top["chg_d"]), "#22c55e", t))
                html += (f'<div style="font-size:9px;color:{t["text_muted"]};margin:4px 0 1px;">'
                         f'Outflow</div>' +
                         _sm_chips(list(bot["sector"]), list(bot["chg_d"]), "#ef4444", t))
        except Exception:
            html += _sm_not_built(t)
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    if st.button("Sector Map →", key="home_right_srk_nav", width="stretch"):
        st.session_state["current_page"] = "Sector Map"
        st.rerun()


def render_rs_leadership_thumb() -> None:
    """Compact RS Leadership card — only renders data if already built this session."""
    t = rs.TOKENS
    html = _sm_band_html(t, "RS Leadership")
    if not st.session_state.get("rsl_ran"):
        html += _sm_not_built(t)
    else:
        try:
            import sector_rs_leadership as _rsl
            g = _rsl.grid(st.session_state.get("srk_group", "industry"))
            df = g.get("rows") if isinstance(g, dict) else g
            if df is None or (hasattr(df, "empty") and df.empty):
                html += _sm_not_built(t)
            else:
                top = df.head(3)
                html += (f'<div style="font-size:9px;color:{t["text_muted"]};margin:2px 0 1px;">'
                         f'Leading (RS T-0)</div>' +
                         _sm_chips(list(top["group"]), list(top["rs_t0"]),
                                   "#22c55e", t, fmt="{:.0f}"))
                rising = df[df["change"] > 0].sort_values("change", ascending=False).head(3)
                if not rising.empty:
                    html += (f'<div style="font-size:9px;color:{t["text_muted"]};margin:4px 0 1px;">'
                             f'Rising ▲</div>' +
                             _sm_chips(list(rising["group"]), list(rising["change"]),
                                       "#22c55e", t, fmt="{:+.1f}"))
        except Exception:
            html += _sm_not_built(t)
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    if st.button("Sector Map →", key="home_right_rsl_nav", width="stretch"):
        st.session_state["current_page"] = "Sector Map"
        st.rerun()


def render_turnover_heatmap_thumb() -> None:
    """Compact Turnover Heatmap card — only renders data if already built this session."""
    t = rs.TOKENS
    html = _sm_band_html(t, "Turnover Heatmap · last 15 sessions")
    if not st.session_state.get("tah_ran"):
        html += _sm_not_built(t)
    else:
        try:
            import sector_turnover_heatmap as _tah
            g = _tah.grid(st.session_state.get("srk_group", "sector"))
            if g.get("error"):
                html += (f'<div style="font-size:11px;color:{t["text_muted"]};">'
                         f'{g["error"]}</div>')
            else:
                ad = g["ad"]
                # first column = today, sort by it
                col0 = ad.columns[0]
                today = ad[col0].dropna().sort_values(ascending=False)
                top = today.head(3)
                bot = today.tail(3)
                html += (f'<div style="font-size:9px;color:{t["text_muted"]};margin:2px 0 1px;">'
                         f'A/D top</div>' +
                         _sm_chips(list(top.index), list(top.values), "#22c55e", t,
                                   fmt="{:+.0f}%"))
                html += (f'<div style="font-size:9px;color:{t["text_muted"]};margin:4px 0 1px;">'
                         f'A/D bottom</div>' +
                         _sm_chips(list(bot.index), list(bot.values), "#ef4444", t,
                                   fmt="{:+.0f}%"))
        except Exception:
            html += _sm_not_built(t)
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    if st.button("Sector Map →", key="home_right_tah_nav", width="stretch"):
        st.session_state["current_page"] = "Sector Map"
        st.rerun()
