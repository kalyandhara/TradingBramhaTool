#!/usr/bin/env python3
"""
dashboard_app.py
Manual-trigger Streamlit dashboard for the screener pipeline + per-stock analyzer.

Wraps the existing CLI tools (screener_pipeline.py, screener_scraper.py,
multibagger_candidates.py, promoter_profit_surprise.py, nse_shareholding_fetch.py,
sector_rotation.py, sector_rotation_trail.py, ew_module.py) without duplicating
their logic — every tab below just calls the same functions those scripts already
expose, then renders the result.

Run:  py -3 -m streamlit run tools/dashboard_app.py
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent))

import screener_pipeline as sp
import ew_module
import scanner_templates as sc
import screener_scraper as ss
import multibagger_candidates as mb
import promoter_profit_surprise as pps
import nse_shareholding_fetch as nse
import sector_rotation as secrot
import sector_rotation_trail as secrot_trail
import portfolio_db as db

try:
    from ta.momentum import RSIIndicator
except ImportError:
    sys.exit("Run:  py -3 -m pip install ta")

BASE_DIR = sp.BASE_DIR

st.set_page_config(page_title="Trading Bramha Dashboard", layout="wide")
st.title("Trading Bramha — Screener & Analysis Dashboard")


# ──────────────────────────────────────────────────────────────────────────────
# Cached wrappers around network-hitting functions (avoid re-fetching on every
# Streamlit rerun caused by widget interaction elsewhere on the page)
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_ohlcv(symbol: str, days: int = 300):
    return sp.fetch_ohlcv(symbol, days=days)


@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_nifty50(days: int = 300):
    return sp.fetch_nifty50(days=days)


def fmt_money(x: float) -> str:
    if x is None or pd.isna(x):
        return "—"
    sign = "-" if x < 0 else ""
    return f"{sign}₹{abs(x):,.0f}"


def fmt_pct(x: float) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:+.2f}%"


def gain_loss_badge(x: float) -> str:
    """Icon + sign, never color alone (accessibility — see Lollypop UX research)."""
    if x is None or pd.isna(x):
        return "—"
    arrow = "▲" if x >= 0 else "▼"
    return f"{arrow} {x:+.2f}%"


def render_condition_table(mv_conds: dict, tf_conds: dict) -> None:
    rows = [{"Strategy": "Minervini", "Condition": k, "Pass": "✅" if v else "❌"}
            for k, v in mv_conds.items()]
    rows += [{"Strategy": "TechnoFunda", "Condition": k, "Pass": "✅" if v else "❌"}
             for k, v in tf_conds.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _volume_profile(df: pd.DataFrame, n_bins: int = 50):
    """Return (bin_centers, volume_at_price) arrays across the full price range."""
    lo_p, hi_p = df["low"].min(), df["high"].max()
    bins = np.linspace(lo_p, hi_p, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    highs   = df["high"].values.astype(float)
    lows    = df["low"].values.astype(float)
    volumes = df["volume"].values.astype(float)
    ranges  = np.where(highs - lows > 0, highs - lows, 1e-9)
    vap = np.zeros(n_bins)
    for i in range(n_bins):
        overlaps = np.maximum(0.0, np.minimum(highs, bins[i + 1]) - np.maximum(lows, bins[i]))
        vap[i] = np.sum(volumes * overlaps / ranges)
    return bin_centers, vap


def build_chart(symbol: str, df: pd.DataFrame, ew: dict) -> go.Figure:
    rsi9  = RSIIndicator(df["close"], window=9).rsi()
    sma50  = df["close"].rolling(50).mean()
    sma150 = df["close"].rolling(150).mean()
    sma200 = df["close"].rolling(200).mean()

    ema9  = df["close"].ewm(span=9,  adjust=False).mean()
    ema21 = df["close"].ewm(span=21, adjust=False).mean()
    ema50 = df["close"].ewm(span=50, adjust=False).mean()

    bin_centers, vap = _volume_profile(df)
    vap_max = vap.max() if vap.max() > 0 else 1.0

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.15, 0.30], vertical_spacing=0.03,
        subplot_titles=(symbol, "Volume", "PTF RSI(9)"),
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name=symbol,
    ), row=1, col=1)

    # SMAs
    fig.add_trace(go.Scatter(x=df.index, y=sma50,  name="SMA50",
                              line=dict(color="#1f77b4", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sma150, name="SMA150",
                              line=dict(color="#ff7f0e", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sma200, name="SMA200",
                              line=dict(color="#9467bd", width=1)), row=1, col=1)

    # 3 EMAs
    fig.add_trace(go.Scatter(x=df.index, y=ema9,  name="EMA9",
                              line=dict(color="#00e676", width=1, dash="dot")),  row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ema21, name="EMA21",
                              line=dict(color="#26c6da", width=1)),               row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ema50, name="EMA50",
                              line=dict(color="#ef5350", width=1, dash="dash")), row=1, col=1)

    # Volume Profile — horizontal bars on a secondary x-axis that shares the price y-axis
    fig.add_trace(go.Bar(
        x=vap, y=bin_centers, orientation="h",
        name="Vol Profile",
        marker=dict(color="rgba(120, 100, 220, 0.25)", line_width=0),
        xaxis="x2", yaxis="y",
        showlegend=True,
    ))
    fig.update_layout(
        xaxis2=dict(
            overlaying="x", side="right",
            showticklabels=False, showgrid=False, zeroline=False,
            range=[0, vap_max * 5],  # widest bar = 20 % of pane width
        )
    )

    # Elliott Wave structural levels
    level_specs = [
        ("w1_start", "W1 start", "gray"),
        ("w1_high", "W1 high", "gray"),
        ("w2_low", "W2 low / stop", "red"),
        ("stop_zone", "Stop zone", "red"),
    ]
    for key, label, color in level_specs:
        val = ew.get(key)
        if val is not None:
            fig.add_hline(y=val, row=1, col=1, line_dash="dot", line_color=color,
                           annotation_text=label, annotation_position="right")

    for price, prob, label in ew.get("w3_targets") or []:
        fig.add_hline(y=price, row=1, col=1, line_dash="dash", line_color="green",
                       annotation_text=f"W3 {label} ({prob}%)", annotation_position="right")
    for price, prob, label in ew.get("w5_targets") or []:
        fig.add_hline(y=price, row=1, col=1, line_dash="dash", line_color="teal",
                       annotation_text=f"W5 {label} ({prob}%)", annotation_position="right")

    fig.add_trace(go.Bar(x=df.index, y=df["volume"], name="Volume",
                          marker_color="#888"), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=rsi9, name="RSI(9)",
                              line=dict(color="#d62728", width=1)), row=3, col=1)
    fig.add_hline(y=80, row=3, col=1, line_dash="dot", line_color="gray")
    fig.add_hline(y=20, row=3, col=1, line_dash="dot", line_color="gray")

    fig.update_layout(height=850, xaxis_rangeslider_visible=False,
                       legend=dict(orientation="h", yanchor="bottom", y=1.02))
    return fig


def compute_portfolio_summary() -> dict:
    """Live P&L + capital-at-risk over all open positions. Cheap to call repeatedly —
    cached_fetch_ohlcv handles the network-call caching underneath."""
    open_pos = db.get_open_positions()
    total_capital = float(db.get_setting("total_capital", "0") or 0)

    if open_pos.empty:
        return dict(invested=0.0, current_value=0.0, pl=0.0, pl_pct=0.0,
                     capital_at_risk_pct=0.0, total_capital=total_capital,
                     day_pl_pct=0.0, open_count=0)

    invested = 0.0
    current_value = 0.0
    risk_amount = 0.0
    day_pl = 0.0
    for _, pos in open_pos.iterrows():
        df = cached_fetch_ohlcv(pos["symbol"])
        if df is None or df.empty:
            continue
        last = float(df["close"].iloc[-1])
        prev = float(df["close"].iloc[-2]) if len(df) > 1 else last
        qty = float(pos["quantity"])
        invested += pos["entry_price"] * qty
        current_value += last * qty
        day_pl += (last - prev) * qty
        if pos["stop_loss"] is not None and not pd.isna(pos["stop_loss"]):
            risk_amount += max(0.0, pos["entry_price"] - pos["stop_loss"]) * qty

    pl = current_value - invested
    pl_pct = (pl / invested * 100) if invested else 0.0
    day_pl_pct = (day_pl / current_value * 100) if current_value else 0.0
    capital_at_risk_pct = (risk_amount / total_capital * 100) if total_capital else 0.0

    return dict(invested=invested, current_value=current_value, pl=pl, pl_pct=pl_pct,
                 capital_at_risk_pct=capital_at_risk_pct, total_capital=total_capital,
                 day_pl_pct=day_pl_pct, open_count=len(open_pos))


def check_alert(alert: pd.Series, portfolio_summary: dict) -> tuple[bool, str]:
    """Structured, no eval() — compares a fixed metric against operator/threshold."""
    category = alert["category"]

    if category == "Earnings":
        if not alert["target_date"]:
            return False, "no target date set"
        try:
            tgt = datetime.strptime(alert["target_date"], "%Y-%m-%d").date()
        except ValueError:
            return False, "invalid date"
        days = (tgt - date.today()).days
        return (0 <= days <= 7), f"{days}d to {alert['target_date']}"

    if category == "Performance":
        value = portfolio_summary.get("pl_pct", 0.0)
        return _compare(value, alert["operator"], alert["threshold"]), f"{value:+.2f}%"

    df = cached_fetch_ohlcv(alert["symbol"])
    if df is None or df.empty:
        return False, "no data"

    if category == "Price":
        value = float(df["close"].iloc[-1])
        return _compare(value, alert["operator"], alert["threshold"]), f"{value:.2f}"

    if category == "Volume":
        avg20 = df["volume"].rolling(20).mean().iloc[-1]
        value = float(df["volume"].iloc[-1] / avg20) if avg20 else 0.0
        return _compare(value, alert["operator"], alert["threshold"]), f"{value:.2f}x"

    if category == "Pattern":
        if alert["metric"] == "wave_pos":
            ew = ew_module.analyze_ew(df)
            value = ew["wave_pos"]
        else:
            nifty_df = cached_fetch_nifty50()
            mv_score, _ = sp.score_minervini(df, nifty_df=nifty_df)
            tf_score, _ = sp.score_technofunda(df)
            value = mv_score + tf_score
        return _compare(value, alert["operator"], alert["threshold"]), str(value)

    return False, "unknown category"


def _compare(value, operator: str, threshold) -> bool:
    try:
        if isinstance(value, str):
            return (value == threshold) if operator == "==" else False
        v, t = float(value), float(threshold)
    except (TypeError, ValueError):
        return False
    return {">": v > t, "<": v < t, ">=": v >= t, "<=": v <= t, "==": v == t}.get(operator, False)


# ──────────────────────────────────────────────────────────────────────────────
# Overview panel — rendered above the tabs, always visible regardless of which
# tab is selected (Streamlit has no true CSS-sticky; this is the practical
# equivalent — see analyses/Dashboard-UX-Operational-Requirements.md)
# ──────────────────────────────────────────────────────────────────────────────
nifty_overview = cached_fetch_nifty50()
portfolio_summary = compute_portfolio_summary()

nifty_last = nifty_day_chg = None
nifty_regime = "Unknown"
if nifty_overview is not None and len(nifty_overview) > 1:
    nifty_last = float(nifty_overview["close"].iloc[-1])
    nifty_prev = float(nifty_overview["close"].iloc[-2])
    nifty_day_chg = (nifty_last - nifty_prev) / nifty_prev * 100
    sma200 = nifty_overview["close"].rolling(200).mean().iloc[-1]
    if not pd.isna(sma200):
        nifty_regime = "RISK-ON" if nifty_last >= sma200 else "RISK-OFF"

active_alerts = db.get_alerts(active_only=True)
triggered_count = 0
if not active_alerts.empty:
    for _, a in active_alerts.iterrows():
        triggered, _ = check_alert(a, portfolio_summary)
        triggered_count += int(triggered)

ov1, ov2, ov3, ov4, ov5 = st.columns(5)
ov1.metric("Nifty 50", f"{nifty_last:,.0f}" if nifty_last else "—",
           f"{nifty_day_chg:+.2f}%" if nifty_day_chg is not None else None)
ov2.metric("Regime", nifty_regime)
ov3.metric("Portfolio P&L", fmt_money(portfolio_summary["pl"]),
           fmt_pct(portfolio_summary["pl_pct"]))
if nifty_day_chg is not None and portfolio_summary["open_count"] > 0:
    ov3.caption(f"Today: portfolio {gain_loss_badge(portfolio_summary['day_pl_pct'])} "
                f"vs Nifty {gain_loss_badge(nifty_day_chg)}")
ov4.metric("Capital at Risk", fmt_pct(portfolio_summary["capital_at_risk_pct"]).replace("+", ""))
ov5.metric("Active Alerts Triggered", f"{triggered_count}/{len(active_alerts)}")

with st.expander("Set total capital (used for % capital-at-risk)"):
    new_cap = st.number_input(
        "Total capital (₹)", min_value=0.0,
        value=portfolio_summary["total_capital"], step=10000.0,
    )
    if st.button("Save total capital"):
        db.set_setting("total_capital", str(new_cap))
        st.success("Saved — refresh metrics above.")

st.divider()

def _render_scanner_card(card: dict, scanner_name: str) -> None:
    sym = card["symbol"]
    tag_html = " ".join(
        f'<span style="background:#eef2ff;color:#4f46e5;padding:2px 8px;'
        f'border-radius:4px;font-size:12px;margin-right:4px;">{t}</span>'
        for t in card.get("tags", [])
    )
    reasons_html = "".join(
        f'<div style="display:flex;margin-bottom:6px;font-size:13px;color:#444;">'
        f'<span style="color:#10b981;font-weight:bold;margin-right:6px;">✓</span>{r}</div>'
        for r in card.get("reasons", [])
    )
    st.markdown(
        f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;
                    margin-bottom:4px;background:white;">
          <div style="display:flex;align-items:center;margin-bottom:10px;">
            <div style="width:36px;height:36px;border-radius:6px;
                        background:linear-gradient(135deg,#667eea,#764ba2);
                        color:white;display:flex;align-items:center;
                        justify-content:center;font-weight:bold;
                        margin-right:10px;flex-shrink:0;">{sym[0]}</div>
            <span style="font-size:16px;font-weight:600;">{sym}</span>
          </div>
          <div style="margin-bottom:10px;">{tag_html}</div>
          <div style="font-size:11px;color:#888;font-weight:600;margin-bottom:6px;
                      text-transform:uppercase;letter-spacing:0.5px;">Why it's interesting</div>
          {reasons_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([3, 2, 2])
    with c1:
        if st.button("Analyze →", key=f"sc_a_{sym}_{scanner_name}"):
            st.session_state["selected_symbol"] = sym
            st.info("Switch to **Stock Analyzer** tab.")
    with c2:
        if st.button("+ Watchlist", key=f"sc_w_{sym}_{scanner_name}"):
            db.add_watchlist_symbol(sym, card.get("pattern_type", scanner_name))
            st.success(f"Added {sym}")
    with c3:
        if st.button("★ Save", key=f"sc_s_{sym}_{scanner_name}"):
            db.save_scanner_hit(sym, scanner_name, card.get("pattern_type", ""))
            st.success(f"Saved {sym}")


with st.expander("Daily Workflow (IST)"):
    st.markdown(
        "| Time | Action |\n|---|---|\n"
        "| **8:30 AM** | Review news/earnings calendar, check overnight alerts, build watchlist |\n"
        "| **9:15 AM** | Monitor index + existing portfolio at open; watch for new pattern breakouts |\n"
        "| **9:15 – 3:30 PM** | Execute confirmed breakouts; manage stops/targets; monitor live alerts |\n"
        "| **3:30 PM onward** | Review fills, update portfolio, mark next day's candidates |"
    )
    st.caption("Screener pipeline auto-runs at 4:05 PM — aligned with the post-market review window.")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    ["Screener", "Stock Analyzer", "Portfolio", "Watchlist", "Alerts",
     "Other Screeners", "Pipeline Log", "Scanner Hub"]
)


# ──────────────────────────────────────────────────────────────────────────────
# Tab 1 — Screener
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Daily Screener Pipeline")
    st.caption(
        "Normally runs automatically at 4:05 PM via Task Scheduler. "
        "Use this to trigger it manually (~3-4 min for ~200-250 stocks)."
    )

    today_path = BASE_DIR / f"screener_{date.today():%Y%m%d}.xlsx"

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Run Screener Pipeline Now", type="primary"):
            with st.spinner("Fetching Bhavcopy + Chartink, scoring stocks..."):
                results = sp.run_pipeline()
            if results is None or results.empty:
                st.error("Pipeline produced no results — check Pipeline Log tab.")
            else:
                st.session_state["screener_results"] = results
                st.success(f"Scored {len(results)} stocks.")

    with col_b:
        if today_path.exists():
            if st.button("Load Today's Saved Results"):
                st.session_state["screener_results"] = pd.read_excel(
                    today_path, sheet_name="Shortlist"
                )
        else:
            st.caption("No saved results for today yet.")

    results = st.session_state.get("screener_results")
    if results is not None and not results.empty:
        filt = st.text_input("Filter by symbol contains")
        view = results
        if filt:
            view = view[view["Symbol"].str.contains(filt.upper(), na=False)]

        st.dataframe(
            view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Minervini /8": st.column_config.ProgressColumn(min_value=0, max_value=8),
                "TechnoFunda /6": st.column_config.ProgressColumn(min_value=0, max_value=6),
                "Total /14": st.column_config.ProgressColumn(min_value=0, max_value=14),
            },
        )

        if today_path.exists():
            st.download_button(
                "Download Excel", data=today_path.read_bytes(),
                file_name=today_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        pick = st.selectbox("Send a symbol to Stock Analyzer", sorted(results["Symbol"].unique()))
        if st.button("Analyze →"):
            st.session_state["selected_symbol"] = pick
            st.info("Symbol set — switch to the **Stock Analyzer** tab above.")

        with st.expander("Bulk-add to Watchlist"):
            bulk_picks = st.multiselect(
                "Select symbols to add", sorted(results["Symbol"].unique()),
                key="bulk_wl_picks",
            )
            if st.button("Add selected to Watchlist", key="bulk_wl_add"):
                for sym in bulk_picks:
                    db.add_watchlist_symbol(sym, "From Screener")
                st.success(f"Added {len(bulk_picks)} symbol(s) to watchlist.")
    else:
        st.info("No results yet — run the pipeline or load today's saved file.")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 2 — Stock Analyzer
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Individual Stock Analyzer")

    screener_symbols = sorted(st.session_state["screener_results"]["Symbol"].unique()) \
        if st.session_state.get("screener_results") is not None else []

    col_a, col_b = st.columns(2)
    with col_a:
        default_idx = 0
        sel_symbol = st.session_state.get("selected_symbol")
        if screener_symbols:
            if sel_symbol in screener_symbols:
                default_idx = screener_symbols.index(sel_symbol)
            from_screener = st.selectbox(
                "From screener results", screener_symbols, index=default_idx
            )
        else:
            from_screener = None
            st.caption("Run the screener in Tab 1 to populate this list.")
    with col_b:
        manual_symbol = st.text_input(
            "Or enter any NSE symbol manually (no .NS suffix)",
            value="" if from_screener else (sel_symbol or ""),
        )

    symbol = (manual_symbol or from_screener or "").strip().upper()

    tf_days = st.select_slider(
        "Chart lookback (days)", options=[90, 180, 300, 365], value=300
    )

    if st.button("Analyze", type="primary") or st.session_state.get("last_analyzed") == symbol:
        if not symbol:
            st.warning("Enter or pick a symbol first.")
        else:
            st.session_state["last_analyzed"] = symbol
            with st.spinner(f"Fetching {symbol}..."):
                df = cached_fetch_ohlcv(symbol, days=tf_days)
            if df is None:
                st.error(f"No usable data for {symbol} (illiquid, too short, or not on yfinance).")
            else:
                nifty_df = cached_fetch_nifty50()
                mv_score, mv_conds = sp.score_minervini(df, nifty_df=nifty_df)
                tf_score, tf_conds = sp.score_technofunda(df)
                ew = ew_module.analyze_ew(df)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Minervini", f"{mv_score}/8")
                c2.metric("TechnoFunda", f"{tf_score}/6")
                c3.metric("Total", f"{mv_score + tf_score}/14")
                c4.metric("EW Confidence", f"{ew['confidence']}%")

                st.info(
                    f"**Wave Position:** {ew['wave_pos']}  |  "
                    f"**Extension Risk:** {ew['ext_risk']}  |  "
                    f"**OWL:** {ew['owl_signal']}  |  **PTF:** {ew['ptf_signal']}  \n"
                    f"{ew['note']}"
                )

                st.plotly_chart(build_chart(symbol, df, ew), use_container_width=True)
                render_condition_table(mv_conds, tf_conds)

                if st.button("Add to Watchlist", key="sa_wl"):
                    db.add_watchlist_symbol(symbol, "From Stock Analyzer")
                    st.success(f"{symbol} added to watchlist.")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 3 — Portfolio
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Portfolio / Position Tracker")

    with st.form("add_position_form", clear_on_submit=True):
        st.caption("Add a position")
        c1, c2, c3 = st.columns(3)
        p_symbol = c1.text_input("Symbol").strip().upper()
        p_entry = c2.number_input("Entry price", min_value=0.0, step=0.5)
        p_qty = c3.number_input("Quantity", min_value=0.0, step=1.0)
        c4, c5, c6 = st.columns(3)
        p_date = c4.date_input("Entry date", value=date.today())
        p_stop = c5.number_input("Stop loss", min_value=0.0, step=0.5)
        p_target = c6.number_input("Target", min_value=0.0, step=0.5)
        p_notes = st.text_input("Notes (setup, thesis, etc.)")
        if st.form_submit_button("Add Position", type="primary"):
            if not p_symbol or p_entry <= 0 or p_qty <= 0:
                st.warning("Symbol, entry price, and quantity are required.")
            else:
                db.add_position(p_symbol, p_entry, p_qty, p_date.isoformat(),
                                 stop_loss=p_stop or None, target=p_target or None,
                                 notes=p_notes)
                st.success(f"Added {p_symbol}.")

    open_pos = db.get_open_positions()
    if open_pos.empty:
        st.info("No open positions.")
    else:
        rows = []
        for _, pos in open_pos.iterrows():
            df = cached_fetch_ohlcv(pos["symbol"])
            current = float(df["close"].iloc[-1]) if df is not None and not df.empty else None
            pl_pct = ((current - pos["entry_price"]) / pos["entry_price"] * 100
                      ) if current else None
            r_mult = None
            has_stop = pd.notna(pos["stop_loss"]) and pos["stop_loss"] not in (None, 0)
            if current is not None and has_stop and pos["entry_price"] != pos["stop_loss"]:
                r_mult = (current - pos["entry_price"]) / (pos["entry_price"] - pos["stop_loss"])
            rows.append({
                "id": pos["id"], "Symbol": pos["symbol"], "Entry": pos["entry_price"],
                "Qty": pos["quantity"], "Current": current,
                "P&L %": gain_loss_badge(pl_pct) if pl_pct is not None else "—",
                "R-Multiple": f"{r_mult:.2f}R" if r_mult is not None else "—",
                "Stop": pos["stop_loss"], "Target": pos["target"],
                "Entry Date": pos["entry_date"], "Notes": pos["notes"],
            })
        st.dataframe(pd.DataFrame(rows).drop(columns=["id"]), use_container_width=True, hide_index=True)

        st.caption("Close a position")
        close_id = st.selectbox(
            "Position", open_pos["id"],
            format_func=lambda i: f"#{i} — {open_pos.loc[open_pos['id'] == i, 'symbol'].iloc[0]}",
        )
        cc1, cc2, cc3 = st.columns(3)
        close_price = cc1.number_input("Closed price", min_value=0.0, step=0.5)
        close_date_in = cc2.date_input("Closed date", value=date.today())
        if cc3.button("Close Position"):
            if close_price <= 0:
                st.warning("Enter the closed price.")
            else:
                db.close_position(close_id, close_price, close_date_in.isoformat())
                st.success(f"Closed position #{close_id}.")

    with st.expander("Trade journal (closed positions)"):
        closed_pos = db.get_closed_positions()
        if closed_pos.empty:
            st.caption("No closed positions yet.")
        else:
            closed_pos = closed_pos.copy()
            closed_pos["P&L %"] = (
                (closed_pos["closed_price"] - closed_pos["entry_price"])
                / closed_pos["entry_price"] * 100
            ).apply(gain_loss_badge)
            closed_pos["Result"] = closed_pos["closed_price"].ge(closed_pos["entry_price"]).map(
                {True: "Win", False: "Loss"}
            )
            st.dataframe(
                closed_pos[["symbol", "entry_price", "closed_price", "quantity",
                            "P&L %", "Result", "entry_date", "closed_date", "notes"]],
                use_container_width=True, hide_index=True,
            )


# ──────────────────────────────────────────────────────────────────────────────
# Tab 4 — Watchlist
# ──────────────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader("Watchlist")

    with st.form("add_watchlist_form", clear_on_submit=True):
        c1, c2 = st.columns([1, 2])
        w_symbol = c1.text_input("Symbol").strip().upper()
        w_notes = c2.text_input("Notes")
        if st.form_submit_button("Add to Watchlist", type="primary"):
            if not w_symbol:
                st.warning("Enter a symbol.")
            else:
                db.add_watchlist_symbol(w_symbol, w_notes)
                st.success(f"Added {w_symbol}.")

    watch = db.get_watchlist()
    if watch.empty:
        st.info("Watchlist is empty.")
    else:
        nifty_wl = cached_fetch_nifty50()
        rows = []
        for _, w in watch.iterrows():
            df = cached_fetch_ohlcv(w["symbol"])
            if df is None or df.empty:
                rows.append({"Symbol": w["symbol"], "Price": "—", "Day %": "—",
                             "Minervini": "—", "TechnoFunda": "—", "Notes": w["notes"]})
                continue
            last = float(df["close"].iloc[-1])
            prev = float(df["close"].iloc[-2]) if len(df) > 1 else last
            day_chg = (last - prev) / prev * 100 if prev else 0.0
            mv_score, _ = sp.score_minervini(df, nifty_df=nifty_wl)
            tf_score, _ = sp.score_technofunda(df)
            rows.append({
                "Symbol": w["symbol"], "Price": f"{last:,.2f}",
                "Day %": gain_loss_badge(day_chg),
                "Minervini": f"{mv_score}/8", "TechnoFunda": f"{tf_score}/6",
                "Notes": w["notes"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        wc1, wc2 = st.columns(2)
        with wc1:
            remove_sym = st.selectbox("Remove from watchlist", watch["symbol"])
            if st.button("Remove"):
                db.remove_watchlist_symbol(remove_sym)
                st.success(f"Removed {remove_sym}.")
        with wc2:
            jump_sym = st.selectbox("Send to Stock Analyzer", watch["symbol"], key="wl_jump")
            if st.button("Analyze →", key="wl_analyze"):
                st.session_state["selected_symbol"] = jump_sym
                st.info("Symbol set — switch to the **Stock Analyzer** tab above.")

        with st.expander("Quick-add to portfolio"):
            qa_sym = st.selectbox("Symbol", watch["symbol"], key="wl_qa_sym")
            qa_df = cached_fetch_ohlcv(qa_sym)
            qa_price = float(qa_df["close"].iloc[-1]) if qa_df is not None and not qa_df.empty else 0.0
            st.caption(f"Current price: ₹{qa_price:,.2f}")
            qc1, qc2 = st.columns(2)
            qa_qty = qc1.number_input("Quantity", min_value=1.0, step=1.0, key="wl_qa_qty")
            qa_stop = qc2.number_input("Stop loss (optional)", min_value=0.0, step=0.5, key="wl_qa_stop")
            if st.button("Add to Portfolio", key="wl_qa_add"):
                if qa_price <= 0:
                    st.warning("Could not fetch current price for this symbol.")
                else:
                    db.add_position(qa_sym, qa_price, qa_qty, date.today().isoformat(),
                                    stop_loss=qa_stop or None)
                    st.success(f"Added {qa_sym} @ ₹{qa_price:,.2f} × {qa_qty:.0f}.")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 5 — Alerts
# ──────────────────────────────────────────────────────────────────────────────
with tab5:
    st.subheader("Alerts")
    st.caption(
        "Checked on-demand each time this dashboard loads/refreshes — no background "
        "process or push notifications, consistent with the manual-trigger model."
    )

    with st.form("add_alert_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        a_symbol = c1.text_input("Symbol (ignored for Performance)").strip().upper()
        a_category = c2.selectbox("Category", db.ALERT_CATEGORIES)

        if a_category == "Earnings":
            a_target_date = st.date_input("Target date (earnings/event)",
                                            value=date.today() + timedelta(days=7))
            a_metric = a_operator = None
            a_threshold = None
        else:
            metrics = db.ALERT_METRICS[a_category]
            c3, c4, c5 = st.columns(3)
            a_metric = c3.selectbox("Metric", metrics) if metrics else None
            a_operator = c4.selectbox("Operator", db.ALERT_OPERATORS)
            if a_metric == "wave_pos":
                a_threshold = c5.selectbox("Wave", ["W1", "W2", "W3", "W4", "W5", "ABC", "unclear"])
            else:
                a_threshold = c5.number_input("Threshold", step=0.5)
            a_target_date = None

        a_note = st.text_input("Note")
        if st.form_submit_button("Create Alert", type="primary"):
            if a_category != "Performance" and not a_symbol:
                st.warning("Symbol is required for this category.")
            else:
                db.add_alert(
                    a_symbol or "PORTFOLIO", a_category, metric=a_metric, operator=a_operator,
                    threshold=a_threshold,
                    target_date=a_target_date.isoformat() if a_target_date else None,
                    note=a_note,
                )
                st.success("Alert created.")

    alerts_df = db.get_alerts(active_only=True)
    if alerts_df.empty:
        st.info("No active alerts.")
    else:
        rows = []
        for _, a in alerts_df.iterrows():
            triggered, detail = check_alert(a, portfolio_summary)
            rows.append({
                "id": a["id"], "Status": "🔴 TRIGGERED" if triggered else "⚪ Watching",
                "Symbol": a["symbol"], "Category": a["category"],
                "Condition": (f"{a['metric']} {a['operator']} {a['threshold']}"
                              if a["category"] != "Earnings" else f"by {a['target_date']}"),
                "Current": detail, "Note": a["note"],
            })
        alerts_view = pd.DataFrame(rows).sort_values("Status")
        st.dataframe(alerts_view.drop(columns=["id"]), use_container_width=True, hide_index=True)

        del_id = st.selectbox(
            "Deactivate/delete alert", alerts_df["id"],
            format_func=lambda i: f"#{i} — {alerts_df.loc[alerts_df['id'] == i, 'symbol'].iloc[0]} "
                                   f"({alerts_df.loc[alerts_df['id'] == i, 'category'].iloc[0]})",
        )
        dc1, dc2 = st.columns(2)
        if dc1.button("Deactivate"):
            db.deactivate_alert(del_id)
            st.success(f"Deactivated alert #{del_id}.")
        if dc2.button("Delete"):
            db.delete_alert(del_id)
            st.success(f"Deleted alert #{del_id}.")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 6 — Other Screeners (with chained pipelining into Sector Rotation)
# ──────────────────────────────────────────────────────────────────────────────
with tab6:
    st.subheader("Other Screeners")

    choice = st.selectbox(
        "Screener",
        ["Multibagger Candidates", "GARP / Promoter-Profit Surprise",
         "NSE Shareholding (Free, no login)", "Custom Screener.in Query"],
    )

    SESSION_BACKED = {
        "Multibagger Candidates": (mb, mb.QUERY),
        "GARP / Promoter-Profit Surprise": (pps, pps.QUERY),
        "Custom Screener.in Query": (ss, ss.DEFAULT_QUERY),
    }

    if choice in SESSION_BACKED:
        module, default_query = SESSION_BACKED[choice]
        sessionid = st.text_input(
            "Screener.in session cookie", type="password",
            help="Grab from browser dev tools after logging into screener.in. "
                 "Kept only in this session, never written to disk.",
        )
        query = st.text_area("Query", value=default_query, height=120)

        if st.button("Run", type="primary"):
            if not sessionid:
                st.warning("Session cookie is required for screener.in-backed queries.")
            else:
                try:
                    with st.spinner("Querying screener.in..."):
                        df = module.build_dataset(sessionid, query)
                except Exception as exc:
                    st.error(f"Run failed: {exc}")
                    df = None
                if df is not None:
                    if df.empty:
                        st.warning("Query returned no rows.")
                    else:
                        st.session_state["other_screener_df"] = df
                        st.session_state["other_screener_kind"] = choice
                        st.success(f"Fetched {len(df)} rows.")

    else:  # NSE Shareholding — free, no session needed
        top200 = st.checkbox("Use Top 200 by traded value (Bhavcopy)", value=True)
        manual_syms = ""
        if not top200:
            manual_syms = st.text_area("Symbols (comma or newline separated)")

        if st.button("Run", type="primary"):
            if top200:
                with st.spinner("Fetching Bhavcopy top 200..."):
                    symbols = sp.fetch_bhavcopy_top_volume()
            else:
                symbols = [s.strip().upper() for s in manual_syms.replace(",", "\n").splitlines() if s.strip()]
            if not symbols:
                st.warning("No symbols to process.")
            else:
                with st.spinner(f"Fetching shareholding data for {len(symbols)} symbols..."):
                    df = nse.build_dataset(symbols)
                if df.empty:
                    st.warning("No data fetched.")
                else:
                    st.session_state["other_screener_df"] = df
                    st.session_state["other_screener_kind"] = choice
                    st.success(f"Fetched {len(df)} rows.")

    other_df = st.session_state.get("other_screener_df")
    other_kind = st.session_state.get("other_screener_kind")
    if other_df is not None and other_kind == choice:
        st.dataframe(other_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download CSV", data=other_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{choice.lower().replace(' ', '_')}_{date.today():%Y%m%d}.csv",
            mime="text/csv",
        )

        can_chain = other_kind in SESSION_BACKED and "Industry" in other_df.columns
        if can_chain:
            st.divider()
            st.caption(
                "Pipeline this result into Sector Rotation analysis "
                "(requires Industry + FII-holding columns, present in screener.in-backed results)."
            )
            if st.button("Pipeline → Sector Rotation"):
                export_path = BASE_DIR / f"screener_export_{date.today():%Y%m%d}.csv"
                other_df.to_csv(export_path, index=False)
                try:
                    with st.spinner("Running sector_rotation + sector_rotation_trail..."):
                        secrot.run(export_path)
                        secrot_trail.run(export_path)
                except Exception as exc:
                    st.error(f"Sector rotation pipeline failed: {exc}")
                else:
                    date_str = date.today().strftime("%Y%m%d")
                    xlsx_path = BASE_DIR / f"sector_rotation_{date_str}.xlsx"
                    html_path = BASE_DIR / f"sector_rotation_orbit_{date_str}.html"
                    if xlsx_path.exists():
                        st.dataframe(pd.read_excel(xlsx_path), use_container_width=True)
                    if html_path.exists():
                        components.html(
                            html_path.read_text(encoding="utf-8"), height=700, scrolling=True
                        )


# ──────────────────────────────────────────────────────────────────────────────
# Tab 7 — Pipeline Log
# ──────────────────────────────────────────────────────────────────────────────
with tab7:
    st.subheader("Pipeline Log")
    st.caption(f"Tail of {sp.LOG_FILE}")
    if sp.LOG_FILE.exists():
        lines = sp.LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        st.code("\n".join(lines[-200:]), language=None)
    else:
        st.info("No log file yet — run the pipeline at least once.")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 8 — Scanner Hub (SwingEdge-inspired pre-built pattern scanners)
# ──────────────────────────────────────────────────────────────────────────────
with tab8:
    st.subheader("Scanner Hub")
    st.caption("Pre-built pattern scanners — choose a scanner, select a universe, run.")

    hub_left, hub_main = st.columns([1, 3])

    with hub_left:
        st.markdown("**Pre-Built Scanners**")
        by_cat: dict[str, list[str]] = {}
        for name, spec in sc.SCANNERS.items():
            by_cat.setdefault(spec["category"], []).append(name)
        for cat in ["Pattern", "Momentum", "Trend", "Entry", "Risk"]:
            if cat not in by_cat:
                continue
            st.markdown(f"<span style='font-size:11px;color:#888;font-weight:600;text-transform:uppercase;'>{cat}</span>", unsafe_allow_html=True)
            for name in by_cat[cat]:
                if st.button(name, key=f"hub_sel_{name}", use_container_width=True):
                    st.session_state["hub_scanner"] = name
                    st.session_state.pop("hub_results", None)

        selected_scanner = st.session_state.get("hub_scanner", list(sc.SCANNERS.keys())[0])
        st.divider()
        st.markdown(f"**Selected:** {selected_scanner}")
        st.caption(sc.SCANNERS[selected_scanner]["description"])

        st.divider()
        screener_res = st.session_state.get("screener_results")
        if screener_res is not None and not screener_res.empty:
            universe = sorted(screener_res["Symbol"].unique())
            st.caption(f"Universe: {len(universe)} stocks from screener")
        else:
            st.caption("No screener results — enter symbols manually:")
            raw = st.text_area("Symbols (comma / newline)", key="hub_manual", height=80)
            universe = [s.strip().upper() for s in raw.replace(",", "\n").splitlines() if s.strip()]

        if st.button("Run Scanner", type="primary", key="hub_run"):
            if not universe:
                st.warning("Run the screener first (Tab 1) or enter symbols above.")
            else:
                with st.spinner(f"Running {selected_scanner} on {len(universe)} symbols..."):
                    hits = sc.run_scanner(selected_scanner, universe, cached_fetch_ohlcv)
                st.session_state["hub_results"] = hits
                st.session_state["hub_scanner_ran"] = selected_scanner

        saved_df = db.get_saved_scanner_hits(selected_scanner)
        if not saved_df.empty:
            st.divider()
            st.markdown(f"**Saved ({len(saved_df)})**")
            for _, row in saved_df.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(row["symbol"])
                if c2.button("✕", key=f"hub_del_{row['symbol']}"):
                    db.remove_scanner_hit(row["symbol"], selected_scanner)
                    st.rerun()

    with hub_main:
        hits = st.session_state.get("hub_results")
        ran_for = st.session_state.get("hub_scanner_ran", "")

        if hits is None:
            st.info("Choose a scanner on the left and click **Run Scanner**.")
        elif ran_for != selected_scanner:
            st.info(f"Last run was for **{ran_for}**. Click **Run Scanner** to scan with **{selected_scanner}**.")
        elif not hits:
            st.info(f"No stocks matched **{selected_scanner}** in this universe.")
        else:
            st.caption(f"{len(hits)} stocks matched · sorted by score")
            cols_n = 3
            for i in range(0, len(hits), cols_n):
                batch = hits[i:i + cols_n]
                cols = st.columns(cols_n)
                for col, card in zip(cols, batch):
                    with col:
                        _render_scanner_card(card, selected_scanner)
