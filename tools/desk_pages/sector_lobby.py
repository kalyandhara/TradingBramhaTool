"""Sector Lobby — walk a whole industry, one peer at a time (SL-1).

New page, not an extraction: it was written here rather than in the monolith,
which is the direction `desk_pages/__init__.py` asks every page to move.
Logic lives in `tools/sector_lobby.py`; this module is only layout and state.

State keys (all prefixed `sl_`):
    sl_anchor   symbol whose industry defines the lobby
    sl_active   symbol whose detail panel is showing
    sl_pick     the jump-pill widget (kept in step with sl_active every run)
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import logging
from pathlib import Path

import fld_confluence as fc
import sector_lobby as sl
import symbol_directory as symdir

_log = logging.getLogger(__name__)
_MARKER = "sl-pill-marker"

# The same live typeahead the Stock Analyzer and the ribbon search use: same
# component directory, same symbol_directory payload, so "what is a valid NSE
# symbol" has one answer on every page. Declared here rather than imported from
# dashboard_app because desk pages may not reach into the monolith's globals.
try:
    _SYMSEARCH = components.declare_component(
        "sl_symbol_search",
        path=str(Path(__file__).resolve().parent.parent / "components" / "symbol_search"),
    )
except Exception as _e:            # pragma: no cover - packaging accident
    _log.warning("sector lobby: symbol search component unavailable: %s", _e)
    _SYMSEARCH = None


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _symbol_payload() -> str:
    """NSE stocks as "DISPLAY|Name" lines — the typeahead filters these locally."""
    try:
        entries = [e for e in symdir.get_directory()
                   if e.get("exchange") == "NSE" and e.get("type") == "stock"]
    except Exception as e:
        _log.warning("sector lobby: symbol directory unavailable: %s", e)
        return ""
    return "\n".join(f"{e['display']}|{(e.get('name') or '')[:44]}" for e in entries)


def _anchor_picker() -> str | None:
    """Typeahead over the NSE list; returns a newly picked symbol or None.
    Falls back to a plain box when the component or directory is unavailable."""
    payload = _symbol_payload() if _SYMSEARCH is not None else ""
    if _SYMSEARCH is None or not payload:
        typed = st.text_input("Anchor symbol (NSE)", value=st.session_state["sl_anchor"],
                              key="sl_anchor_input").strip().upper().replace(".NS", "")
        return typed if typed and typed != st.session_state["sl_anchor"] else None
    st.caption("Anchor symbol — type a name or NSE code")
    picked = _SYMSEARCH(options=payload, placeholder="Type a name or NSE code…",
                        key="sl_symsearch", default=None)
    # The component's value persists across reruns; act only on a new pick.
    if isinstance(picked, dict) and picked.get("symbol"):
        if picked.get("n") != st.session_state.get("_sl_pick_n"):
            st.session_state["_sl_pick_n"] = picked["n"]
            return picked["symbol"].strip().upper().replace(".NS", "")
    return None


_SOURCES = {"Auto (Yahoo industry → screener.in)": "auto",
            "NSE basic industry (screener.in)": "screener"}


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _members(anchor: str, source: str = "auto") -> dict:
    return sl.lobby_members(anchor, source=source)


@st.cache_data(ttl=300, show_spinner=False)
def _frames(symbols: tuple[str, ...]) -> dict:
    # 3 years: the 160-bar FLD needs ~1.5 cycles before it reads at all, and the
    # per-stock hit rate needs past signals to count.
    return sl.fetch_frames(list(symbols), period="3y")


@st.cache_data(ttl=300, show_spinner=False)
def _fld_scores(symbols: tuple[str, ...], model_key: str) -> dict:
    frames = _frames(symbols)
    model = fc.load_model()
    out = {}
    for sym in symbols:
        try:
            out[sym] = fc.score(frames.get(sym), model)
        except Exception as e:                  # one bad frame never blanks the page
            _log.warning("FLD score failed for %s: %s", sym, e)
            out[sym] = None
    return out


def _model_key() -> str:
    m = fc.load_model()
    return m.get("trained_at", "model") if m else "default"


def _fld_section(sym: str, f: dict | None, frame) -> None:
    """Confluence row, per-cycle table and FLD chart for the active stock."""
    model = fc.load_model()
    tag = (f'<span style="color:#166534">calibrated</span> · {model.get("universe", "")}'
           if model else '<span style="color:#a14a0b">uncalibrated — default weights</span>')
    st.markdown(f'<div style="font-size:12px;color:#7a6858;margin-top:6px">'
                f'FLD CONFLUENCE (HURST, CYCLES {"/".join(map(str, fc.CYCLES))}) · {tag}</div>',
                unsafe_allow_html=True)
    if not f:
        st.caption("No FLD setup: too little history, or no cycle has a target still ahead "
                   "of price.")
        return
    up = f["side"] > 0
    col = sl.GOOD if up else sl.RISK
    tgt_pct = (f["target"] / f["price"] - 1) * 100
    _row([
        _stat("Direction", ("LONG ▲" if up else "SHORT ▼"), col,
              sub=f"vote D {f['D']:+.2f} · trigger {f['trigger_cycle']}-bar"),
        _stat("Probability", f"{f['P']:.0%}", None,
              sub=f"own hit rate {f['n_hits']}/{f['n_signals']} past signals"),
        _stat("Target", sl.fmt_price(f["target"]), col,
              sub=f"{tgt_pct:+.1f}% · {f['reward']:.1f} ATR · within {f['horizon']} bars"),
        _stat("Invalidation", sl.fmt_price(f["stop"]),
              sub=f"close beyond the {f['trigger_cycle']}-bar FLD · {f['risk']:.1f} ATR"),
        _stat("Expected value", f"{f['EV']:+.2f} ATR", sl.tone(f["EV"]),
              sub=f"clustering {f['TC']:.2f} · phase {f['PA']:.1f}"),
    ])
    import pandas as pd
    with st.expander("Per-cycle readings", expanded=False):
        st.dataframe(pd.DataFrame([{
            "Cycle (bars)": s["cycle"], "Side": "above ▲" if s["side"] > 0 else "below ▼",
            "Bars since cross": s["bars"], "Freshness": round(s["fresh"], 2),
            "Target": round(s["target"], 2), "FLD now": round(s["fld_now"], 2),
            "Since trough (cycles)": round(s["since_trough"], 2),
            "Since peak (cycles)": round(s["since_peak"], 2)} for s in f["states"]]),
            hide_index=True, width="stretch")
    if frame is None or frame.empty:
        return
    view = frame.iloc[-260:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=view.index, y=view["close"], name="Close",
                             line=dict(color="#3a2a1e", width=1.6)))
    palette = {20: "#93c5fd", 40: "#60a5fa", 80: "#2563eb", 160: "#1e3a8a"}
    for c in fc.CYCLES:
        known, fwd = fc.fld_series(frame, c)
        known = known.loc[view.index[0]:]
        shown = c == f["trigger_cycle"] or c == max(fc.CYCLES)
        fig.add_trace(go.Scatter(x=known.index, y=known.values, name=f"FLD {c}",
                                 line=dict(color=palette.get(c, "#2563eb"), width=1.2),
                                 visible=True if shown else "legendonly"))
        fig.add_trace(go.Scatter(x=fwd.index, y=fwd.values, name=f"FLD {c} forward",
                                 line=dict(color=palette.get(c, "#2563eb"), width=1.2, dash="dash"),
                                 visible=True if shown else "legendonly", showlegend=False))
    fig.add_hline(y=f["target"], line=dict(color=col, dash="dot"),
                  annotation_text=f"Target {f['target']:,.0f}", annotation_position="top left")
    fig.add_hline(y=f["stop"], line=dict(color="#636a75", dash="dot"),
                  annotation_text=f"Invalidation {f['stop']:,.0f}",
                  annotation_position="bottom left")
    fig.add_vline(x=view.index[-1], line=dict(color="#a855f7", dash="dash", width=1))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10),
                      title=dict(text=f"{sym} · FLDs with forward projection", font=dict(size=13)),
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
                      plot_bgcolor="#fffdf8", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _calibration_panel(frames: dict, label: str) -> None:
    model = fc.load_model()
    with st.expander("FLD model calibration", expanded=False):
        if model:
            sk = model.get("oos_skill")
            st.markdown(
                f"**Current model:** {model.get('universe') or 'unnamed'} · "
                f"{model['n']:,} signals from {model.get('n_symbols', '?')} stocks · "
                f"trained {model.get('trained_at', '?')} · base hit rate "
                f"{model['base_rate']:.0%} · out-of-sample skill vs base rate "
                f"{'n/a' if sk is None else f'{sk:+.1%}'}")
            _reliability_table(model.get("reliability_oos") or [])
        else:
            st.markdown("**No model yet.** Probabilities use default weights and are not "
                        "probabilities in any measured sense until a fit exists.")
        st.caption("Best: calibrate on the whole universe from a terminal — "
                   "`python tools/fld_confluence.py calibrate` (~750 stocks, a few minutes "
                   "of downloading). The button below fits on this lobby only, which is "
                   "quicker but a much smaller sample, and it REPLACES the saved model.")
        if st.button(f"Calibrate on this lobby ({label})", key="sl_fld_calibrate"):
            with st.spinner("Backtesting every FLD signal in the lobby…"):
                res = fc.calibrate(frames, label=f"lobby: {label}")
            if res["ok"]:
                _fld_scores.clear()
                st.success(f"Fitted on {res['n']:,} signals. Out-of-sample skill "
                           f"{res['oos_skill']:+.1%} vs always guessing the base rate.")
                _reliability_table(res["reliability_oos"])
            else:
                st.warning(res["reason"])


def _reliability_table(rel: list[dict]) -> None:
    if not rel:
        return
    import pandas as pd
    st.caption("Out-of-sample reliability — the later 30% of the timeline, never seen "
               "by the fit. Predicted should track actual; if it doesn't, the "
               "probabilities are not to be trusted.")
    st.dataframe(pd.DataFrame([{"P bucket": r["bucket"], "Signals": r["n"],
                                "Predicted": f"{r['predicted']:.0%}",
                                "Actual hit rate": f"{r['actual']:.0%}"} for r in rel]),
                 hide_index=True, width="stretch")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _valuations(symbols: tuple[str, ...], last: tuple[tuple[str, float | None], ...]) -> dict:
    return sl.fetch_valuations(list(symbols), last=dict(last))


def _step(order: list[str], delta: int) -> None:
    cur = st.session_state.get("sl_active")
    i = order.index(cur) if cur in order else 0
    st.session_state["sl_active"] = order[(i + delta) % len(order)]


def _pick() -> None:
    v = st.session_state.get("sl_pick")
    if v:
        st.session_state["sl_active"] = v


def _stat(label: str, value: str, color: str | None = None, sub: str = "") -> str:
    c = f"color:{color};" if color else ""
    s = f'<div style="font-size:11px;color:#636a75">{sub}</div>' if sub else ""
    return (f'<div style="flex:1;min-width:120px;background:#fffdf8;border:1px solid '
            f'#f0e0cc;border-radius:10px;padding:8px 12px">'
            f'<div style="font-size:11px;color:#7a6858;text-transform:uppercase;'
            f'letter-spacing:.04em">{label}</div>'
            f'<div style="font-family:ui-monospace,Consolas,monospace;font-size:16px;'
            f'font-weight:600;{c}">{value}</div>{s}</div>')


def _row(cells: list[str]) -> None:
    st.markdown(f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 10px">'
                f'{"".join(cells)}</div>', unsafe_allow_html=True)


def _rank_high(vals: dict, sym: str, field: str) -> tuple:
    pool = sorted((s for s, v in vals.items() if v.get(field) is not None),
                  key=lambda s: vals[s][field], reverse=True)
    return (pool.index(sym) + 1 if sym in pool else None, len(pool))


def _rank_low(vals: dict, sym: str, field: str) -> tuple:
    pool = sorted((s for s, v in vals.items() if v.get(field) is not None),
                  key=lambda s: vals[s][field])
    return (pool.index(sym) + 1 if sym in pool else None, len(pool))


def _rank_txt(r: tuple) -> str:
    i, n = r
    return sl.NA if i is None else f"{i} / {n}"


def render() -> None:
    """The Sector Lobby page. Called by `desk_pages.render`."""
    st.subheader("Sector wise Navigation")
    st.caption("Every listed peer in one industry, lined up in a ribbon. Step through "
               "them with ‹ Prev / Next › or the arrow keys, or click a card.")

    if "sl_anchor" not in st.session_state:
        st.session_state["sl_anchor"] = (st.session_state.get("selected_symbol")
                                         or "AEQUS").strip().upper()

    c1, c2, c2b, c3 = st.columns([2, 1.4, 1.6, 3])
    with c1:
        typed = _anchor_picker()
    with c2:
        sort_by = st.selectbox("Order ribbon by", list(sl.SORT_OPTIONS), key="sl_sort")
    with c2b:
        source = _SOURCES[st.selectbox(
            "Peer source", list(_SOURCES), key="sl_source",
            help="Auto uses Yahoo's industry (NSE sector first, then across sectors) "
                 "and falls back to screener.in when that finds too few peers. "
                 "screener.in lists NSE's basic industry, small caps included.")]
    if typed and typed != st.session_state["sl_anchor"]:
        st.session_state["sl_anchor"] = typed
        st.session_state["sl_active"] = typed

    anchor = st.session_state["sl_anchor"]
    with st.spinner(f"Resolving {anchor}'s industry peers…"):
        lob = _members(anchor, source)
    if not lob["ok"]:
        st.warning(f"**{anchor}** — " + (lob["reason"] or "no peer group could be built."))
        return

    members = lob["members"]
    with st.spinner(f"Fetching prices for {len(members)} names…"):
        frames = _frames(tuple(members))
    with st.spinner("Scoring FLD confluence…"):
        fld = _fld_scores(tuple(members), _model_key())
    cards = sl.sort_cards(sl.attach_fld(sl.build_cards(members, frames, lob["tags"]), fld),
                          sort_by)
    order = [c["symbol"] for c in cards]
    if st.session_state.get("sl_active") not in order:
        st.session_state["sl_active"] = anchor if anchor in order else order[0]
    active = st.session_state["sl_active"]

    with c3:
        lvl = "industry" if lob["level"] == "industry" else "industry family"
        if lob.get("source") == "screener.in":
            lvl = "NSE basic industry, via screener.in"
        elif lob.get("off_index"):
            lvl += f", {anchor} is outside NIFTY Total Market — peers matched by industry"
        elif lob.get("cross_sector"):
            lvl += ", found across NSE sectors"
        st.markdown(
            f'<div style="padding-top:26px;color:#5c4a3a">'
            f'Anchor <b style="color:#a14a0b">{anchor}</b> · <b>{lob["label"]}</b> <span style="color:#636a75">({lvl} · NSE '
            f'{lob["macro_sector"] or "—"})</span> · {len(order)} names</div>',
            unsafe_allow_html=True)

    # ── Ribbon ────────────────────────────────────────────────────────────────
    st.iframe(sl.ribbon_html(cards, active, pill_marker=_MARKER), height=186)

    pos = order.index(active) + 1
    n1, n2, n3 = st.columns([1, 1, 6])
    n1.button("‹ Prev", on_click=_step, args=(order, -1), width="stretch")
    n2.button("Next ›", on_click=_step, args=(order, 1), width="stretch")
    n3.markdown(f'<div style="padding-top:8px;color:#7a6858">'
                f'<b style="color:#3a2a1e">{pos} / {len(order)}</b> · {sort_by}</div>',
                unsafe_allow_html=True)

    # Jump pills: the real widget behind a card click. Synced to the active card
    # BEFORE the widget is created, which is the one moment Streamlit allows it.
    st.markdown(f'<span id="{_MARKER}"></span>', unsafe_allow_html=True)
    st.session_state["sl_pick"] = active
    st.pills("Jump to", order, selection_mode="single", key="sl_pick",
             on_change=_pick, label_visibility="collapsed")

    # ── Detail panel ──────────────────────────────────────────────────────────
    card = next(c for c in cards if c["symbol"] == active)
    ctx = sl.sector_context(cards, active)
    chg = card["chg_1d"]
    abs_txt = "" if card["chg_abs"] is None else f" ({card['chg_abs']:+,.2f})"
    st.markdown(
        f'<div style="margin-top:14px;display:flex;align-items:baseline;gap:14px;'
        f'flex-wrap:wrap"><span style="font-size:22px;font-weight:600;color:#3a2a1e">'
        f'{card["name"]}</span><span style="color:#7a6858">{active}:NSE</span></div>'
        f'<div style="display:flex;align-items:baseline;gap:12px">'
        f'<span style="font-family:ui-monospace,Consolas,monospace;font-size:28px;'
        f'font-weight:600">{sl.fmt_price(card["last"])}</span>'
        f'<span style="font-size:16px;font-weight:600;color:{sl.tone(chg)}">'
        f'{sl.fmt_pct(chg)}{abs_txt} today</span>'
        f'<span style="color:#636a75;font-size:12px">as of {card["asof"] or "—"}</span>'
        f'</div>', unsafe_allow_html=True)

    _row([
        _stat("1M", sl.fmt_pct(card["ret_1m"]), sl.tone(card["ret_1m"])),
        _stat("6M", sl.fmt_pct(card["ret_6m"]), sl.tone(card["ret_6m"])),
        _stat("52W high", sl.fmt_price(card["hi52"]),
              sub=f"{sl.fmt_pct(card['off_high'])} from high"),
        _stat("52W low", sl.fmt_price(card["lo52"])),
        _stat("Mkt cap", sl.NA if card["mcap_cr"] is None
              else f"₹{card['mcap_cr']:,.0f} Cr"),
    ])
    st.markdown('<div style="font-size:12px;color:#7a6858;margin-top:4px">'
                'IN THE SECTOR</div>', unsafe_allow_html=True)
    _row([
        _stat("Rank today", _rank_txt(ctx["rank_chg_1d"])),
        _stat("Rank 1M", _rank_txt(ctx["rank_ret_1m"])),
        _stat("Rank 6M", _rank_txt(ctx["rank_ret_6m"])),
        _stat("Sector avg today", sl.fmt_pct(ctx["avg_1d"]), sl.tone(ctx["avg_1d"]),
              sub=f"{ctx['advancers']}▲ · {ctx['decliners']}▼ of {ctx['n_priced']}"),
        _stat("Sector avg 6M", sl.fmt_pct(ctx["avg_6m"]), sl.tone(ctx["avg_6m"])),
    ])

    with st.spinner("Loading P/E, EPS and OPM for the lobby…"):
        vals = _valuations(tuple(order), tuple((c["symbol"], c["last"]) for c in cards))
    # screener.in's listing carries P/E; use it only where Yahoo had none.
    vals = {k: dict(v) for k, v in vals.items()}
    for sym, t in lob["tags"].items():
        if sym in vals and vals[sym].get("pe") is None and t.get("screener_pe"):
            vals[sym]["pe"] = t["screener_pe"]
    v = vals.get(active) or {}
    med_pe = sl.median([x.get("pe") for x in vals.values()])
    med_opm = sl.median([x.get("opm") for x in vals.values()])
    n_pe = sum(1 for x in vals.values() if x.get("pe") is not None)
    st.markdown('<div style="font-size:12px;color:#7a6858;margin-top:4px">'
                'VALUATION &amp; MARGIN (TTM)</div>', unsafe_allow_html=True)
    pe_tone = None
    if v.get("pe") is not None and med_pe:
        pe_tone = sl.GOOD if v["pe"] < med_pe else sl.RISK if v["pe"] > med_pe * 1.25 else None
    opm_tone = None
    if v.get("opm") is not None and med_opm is not None:
        opm_tone = sl.GOOD if v["opm"] >= med_opm else sl.RISK
    _row([
        _stat("P/E", sl.NA if v.get("pe") is None else f"{v['pe']:.1f}×", pe_tone,
              sub=("loss-making — no P/E" if v.get("pe") is None and (v.get("eps") or 0) < 0
                   else f"sector median {med_pe:.1f}× ({n_pe} names)" if med_pe else "")),
        _stat("EPS", sl.NA if v.get("eps") is None else f"₹{v['eps']:,.2f}",
              None if v.get("eps") is None else sl.tone(v["eps"]), sub="trailing 12 months"),
        _stat("OPM", sl.NA if v.get("opm") is None else f"{v['opm']:.1f}%", opm_tone,
              sub=f"sector median {med_opm:.1f}%" if med_opm is not None else ""),
        _stat("Rank P/E (cheapest)", _rank_txt(_rank_low(vals, active, "pe"))),
        _stat("Rank OPM", _rank_txt(_rank_high(vals, active, "opm"))),
    ])

    _fld_section(active, fld.get(active), frames.get(active))

    own, avg = sl.relative_series(frames, active, order)
    if own is not None:
        fig = go.Figure()
        if avg is not None:
            fig.add_trace(go.Scatter(x=avg.index, y=avg.values, name="Rest of lobby (avg)",
                                     line=dict(color="#636a75", width=1.5, dash="dot")))
        fig.add_trace(go.Scatter(x=own.index, y=own.values, name=active,
                                 line=dict(color=sl.tone(card["ret_6m"]), width=2)))
        fig.add_hline(y=100, line=dict(color="#e5cfae", width=1))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10),
                          title=dict(text="6M, rebased to 100", font=dict(size=13)),
                          legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
                          plot_bgcolor="#fffdf8", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    else:
        st.info(f"No price history resolved for {active} — {sl.NA}.")

    # Real links, not buttons: left-click opens in this tab, and the browser's
    # own right-click menu offers "Open link in new tab". Routed by the
    # ?nav=analyze / ?nav=predict deep-link handler in dashboard_app.py.
    st.markdown(sl.opener_links(active), unsafe_allow_html=True)

    # ── Whole lobby at a glance ───────────────────────────────────────────────
    with st.expander(f"All {len(order)} names in {lob['label']}", expanded=False):
        import pandas as pd
        st.dataframe(pd.DataFrame([{
            "#": i, "Symbol": c["symbol"], "Name": c["name"],
            "Price": c["last"], "Today %": c["chg_1d"], "1M %": c["ret_1m"],
            "6M %": c["ret_6m"], "From 52W high %": c["off_high"],
            "Mkt cap (Cr)": c["mcap_cr"],
            "P/E": (vals.get(c["symbol"]) or {}).get("pe"),
            "EPS": (vals.get(c["symbol"]) or {}).get("eps"),
            "OPM %": (vals.get(c["symbol"]) or {}).get("opm"),
        } for i, c in enumerate(cards, 1)]), hide_index=True, width="stretch",
            column_config={k: st.column_config.NumberColumn(format="%.2f")
                           for k in ("Price", "Today %", "1M %", "6M %",
                                     "From 52W high %", "P/E", "EPS", "OPM %")})
        st.caption("Membership comes from the same industry resolution as the Stock "
                   "Analyzer's peer table, without its 12-name cap. Pin or exclude "
                   "names per group in `tools/cache/lobby_overrides.json`, e.g. "
                   '`{"Aerospace & Defense": {"pin": ["AZAD"], "exclude": []}}`.')

    _calibration_panel(frames, lob["label"] or anchor)
