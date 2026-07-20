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
import csv
import json
from datetime import date, datetime, timedelta, time
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
import astro_trading as at
import astrohora_loader as ahl
import telegram_signals as tg
import volume_fetcher as vf
import india_market_intel as imi
import harmonic_patterns as hp
import sentiment_index as senti
import browser_cookie_helper as bch
import stock_council as council

try:
    from ta.momentum import RSIIndicator
except ImportError:
    sys.exit("Run:  py -3 -m pip install ta")

BASE_DIR = sp.BASE_DIR

st.set_page_config(page_title="Trading Bramha Dashboard", layout="wide")

# Base URL of THIS dashboard, used to build "Analyze" deep-links that open the
# Stock Analyzer (with the 3-POV Council) in a new browser tab. Mirrors the
# hardcoded localhost:5001 chart-server convention already used across the app.
DASHBOARD_BASE = "http://localhost:8501"


def _analyze_url(sym) -> str | None:
    """Deep-link that opens the Stock Analyzer on `sym` in a fresh tab."""
    s = str(sym).strip().upper().replace(".NS", "")
    if not s or s.startswith("^"):
        return None
    return f"{DASHBOARD_BASE}/?nav=analyze&symbol={s}"


def _analyze_colcfg() -> "st.column_config.LinkColumn":
    return st.column_config.LinkColumn(
        "Analyze", help="Open the 3-POV Council analysis in a new tab",
        display_text="Analyze ↗", width="small",
    )


def _with_analyze_col(df, symbol_col: str, after: str | None = "Chart"):
    """Return a copy of df with an 'Analyze' deep-link column inserted right
    after `after` (or appended if that column is absent)."""
    out = df.copy()
    urls = out[symbol_col].map(_analyze_url)
    pos = (out.columns.get_loc(after) + 1) if (after in out.columns) else len(out.columns)
    out.insert(pos, "Analyze", urls)
    return out

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:10px;
                padding:14px 4px 10px 4px;margin-bottom:4px;
                border-bottom:1px solid #f0e0cc;">
      <span style="font-size:26px;">📈</span>
      <span style="font-size:22px;font-weight:800;color:#3a2a1e;">Trading</span>
      <span style="font-size:22px;font-weight:800;color:#ea580c;">Bramha</span>
      <span style="font-size:13px;color:#9a8778;margin-left:8px;">Screener &amp; Analysis Dashboard</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────────────────────────────────────
# Cached wrappers around network-hitting functions (avoid re-fetching on every
# Streamlit rerun caused by widget interaction elsewhere on the page)
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_ohlcv(symbol: str, days: int = 300):
    # Try enhanced volume fetcher first
    try:
        volume_fetcher = vf.VolumeFetcher(verbose=False)
        df = volume_fetcher.fetch_with_volume(symbol, days=days, validate=True)
        if df is not None:
            return df
    except Exception as e:
        st.warning(f"Volume fetcher error: {e}")

    # Fallback to screener_pipeline
    return sp.fetch_ohlcv(symbol, days=days)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_fetch_bhavcopy_universe(top_n: int) -> list[str]:
    return sp.fetch_bhavcopy_top_volume(top_n)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fno_symbols() -> set[str]:
    """NSE F&O (derivative-eligible) symbols for the Scanner Hub 'F&O only'
    filter. Reads tools/cache/fno_symbols.json (bare NSE codes). Returns an
    empty set if the file is missing/unreadable, in which case the pill hides."""
    path = Path(__file__).resolve().parent / "cache" / "fno_symbols.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        syms = data["symbols"] if isinstance(data, dict) else data
        return {str(s).strip().upper().replace(".NS", "") for s in syms if str(s).strip()}
    except Exception:
        return set()


@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_nifty50(days: int = 300):
    return sp.fetch_nifty50(days=days)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_fundamentals(symbol: str) -> dict:
    return council.fetch_fundamentals(symbol)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_safe_symbols(sessionid: str, max_pledge_pct: float = 5.0) -> set[str]:
    return ss.fetch_fundamental_safe_symbols(sessionid, max_pledge_pct=max_pledge_pct)


# Unique NSE sector index tickers and their display labels
SECTOR_DISPLAY_NAMES = {
    "^NSEBANK":            "Banking",
    "NIFTY_FIN_SERVICE.NS": "Fin Services",
    "^CNXIT":              "IT / Telecom",
    "^CNXPHARMA":          "Pharma",
    "^CNXAUTO":            "Auto",
    "^CNXFMCG":            "FMCG / Chem",
    "^CNXMETAL":           "Metals",
    "^CNXREALTY":          "Realty",
    "^CNXINFRA":           "Infra",
    "^CNXENERGY":          "Energy",
    "^CNXCONSUM":          "Cons. Durables",
}


@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_sector_data() -> dict:
    import yfinance as yf
    results = {}
    for ticker in SECTOR_DISPLAY_NAMES:
        try:
            df = yf.download(ticker, period="2y", interval="1d",
                             progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                results[ticker] = df
        except Exception:
            pass
    return results


def _period_return(df: pd.DataFrame, days: int) -> float | None:
    col = next((c for c in ("Close", "close") if c in df.columns), None)
    if col is None or len(df) < 2:
        return None
    close = df[col]
    idx = max(0, len(close) - 1 - days)
    start, end = float(close.iloc[idx]), float(close.iloc[-1])
    return round((end / start - 1) * 100, 2) if start != 0 else None


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


def render_condition_table(mv_conds: dict, tf_conds: dict,
                            canslim_conds: dict | None = None) -> None:
    rows = [{"Strategy": "Minervini", "Condition": k, "Pass": "✅" if v else "❌"}
            for k, v in mv_conds.items()]
    rows += [{"Strategy": "TechnoFunda", "Condition": k, "Pass": "✅" if v else "❌"}
             for k, v in tf_conds.items()]
    if canslim_conds:
        rows += [{"Strategy": "CANSLIM", "Condition": k,
                  "Pass": ("✅" if v else "❌") if v is not None else "—"}
                 for k, v in canslim_conds.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


_VERDICT_STYLE = {
    "BUY":   ("🟢", "success"),
    "WATCH": ("🟡", "warning"),
    "AVOID": ("🔴", "error"),
}


def _render_thesis(title: str, thesis, accent: str) -> None:
    st.markdown(f"**{title} — conviction {thesis.conviction}/10**")
    rows = [{"Pillar": p.name, "Score": f"{p.score:.0f}/100",
             "Weight": p.weight, "Reasoning": p.reason} for p in thesis.pillars]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if thesis.breakers:
        st.caption("⚠️ Thesis-breakers: " + "; ".join(thesis.breakers))


_TONE_DOT   = {"good": "🟢", "neutral": "🟡", "bad": "🔴"}
_TONE_COLOR = {"good": "green", "neutral": "orange", "bad": "red"}


def render_setup_intelligence(intel) -> None:
    """Scannable plain-language setup panel derived from the council's evidence."""
    with st.container(border=True):
        st.markdown("#### ⭐ Setup Intelligence")
        st.caption("Structured setup analysis · research only")

        dot = _TONE_DOT.get(intel.status_tone, "⚪")
        color = _TONE_COLOR.get(intel.status_tone, "gray")
        st.markdown(f"{dot} **Setup status · :{color}[{intel.status_label}]**")

        # Chips
        chip_cols = st.columns(len(intel.chips))
        for col, (label, value, tone) in zip(chip_cols, intel.chips):
            with col:
                with st.container(border=True):
                    st.caption(label.upper())
                    st.markdown(f"**:{_TONE_COLOR.get(tone, 'gray')}[{value}]**")

        # Factor lists
        c_bull, c_risk = st.columns(2)
        with c_bull:
            with st.container(border=True):
                st.markdown(":green[**BULLISH FACTORS**]")
                if intel.bullish_factors:
                    st.markdown("\n".join(f"- {x}" for x in intel.bullish_factors))
                else:
                    st.caption("None detected.")
        with c_risk:
            with st.container(border=True):
                st.markdown(":red[**RISK FACTORS**]")
                if intel.risk_factors:
                    st.markdown("\n".join(f"- {x}" for x in intel.risk_factors))
                else:
                    st.caption("None detected.")

        st.caption("OVERALL VIEW")
        st.markdown(intel.overall_view)
        st.caption(
            "Derived automatically from historical market data by our research "
            "algorithms. May be incomplete or inaccurate and can change between "
            "scans. Research and educational study only — not investment advice "
            "or a recommendation to buy, sell, or hold any security."
        )


def render_council(bundle, bull, bear, card) -> None:
    """Render the Bull/Bear/Judge council as a trade card + drill-downs."""
    emoji, kind = _VERDICT_STYLE.get(card.verdict, ("⚪", "info"))

    # ── Trade card (top, always visible) ──
    msg = getattr(st, kind)
    header = (f"### {emoji} {card.verdict} — conviction {card.conviction}/10  "
              f"(net {card.net_score:+.0f})")
    lines = [header]
    if card.verdict == "AVOID":
        lines.append("**No long trade suggested.** Levels below are reference only.")
    if card.entry is not None:
        label = "**Ref price**" if card.verdict == "AVOID" else "**Entry**"
        lines.append(
            f"{label} ₹{card.entry:,.2f}  ·  **Stop** "
            + (f"₹{card.stop:,.2f} ({card.risk_pct}% risk)" if card.stop else "—")
        )
    if card.targets:
        tgt = "  ·  ".join(f"T{i+1} ₹{t:,.2f} (R:R {r})"
                           for i, (t, r) in enumerate(zip(card.targets, card.rr)))
        lines.append(f"**Targets** {tgt}")
    if card.size_pct is not None and card.verdict != "AVOID":
        lines.append(f"**Suggested size** {card.size_pct}% of capital "
                     f"(at {council.RISK_PER_TRADE_PCT}% risk rule)  ·  **Horizon** {card.horizon}")
    lines.append(f"🟢 **Bull's best:** {card.bull_top}")
    lines.append(f"🔴 **Bear's best:** {card.bear_top}")
    lines.append(f"🧭 {card.regime_note}")
    if card.invalidations:
        lines.append("**Invalidation:** " + "; ".join(card.invalidations))
    msg("  \n".join(lines))

    c1, c2 = st.columns(2)
    with c1:
        with st.expander(f"🟢 Bull thesis ({bull.conviction}/10)", expanded=False):
            _render_thesis("Bull case", bull, "green")
    with c2:
        with st.expander(f"🔴 Bear thesis ({bear.conviction}/10)", expanded=False):
            _render_thesis("Bear case", bear, "red")

    with st.expander("📊 Raw evidence bundle (audit trail)", expanded=False):
        skip = {"minervini_conds", "technofunda_conds", "fundamentals"}
        fact_rows = [{"Metric": k, "Value": (f"{v:,.2f}" if isinstance(v, float) else str(v))}
                     for k, v in bundle.facts.items() if k not in skip]
        st.dataframe(pd.DataFrame(fact_rows), use_container_width=True, hide_index=True)
        if bundle.has_fundamentals:
            fu = bundle.facts.get("fundamentals", {})
            st.caption("Fundamentals (yfinance): "
                       + " · ".join(f"{k}={v}" for k, v in fu.items() if v is not None))
        else:
            st.caption("No fundamentals available — technical-only verdict.")


def _compute_canslim(df: pd.DataFrame, nifty_df: pd.DataFrame | None) -> tuple:
    """
    Returns (score, conds, rs_pct, rs_line) where:
      score    — int, number of CANSLIM conditions that pass (max 4 computable)
      conds    — dict of condition_label → True/False/None
      rs_pct   — float, stock 12m return minus Nifty 12m return (outperformance %)
      rs_line  — pd.Series (normalized to 100 at start) or None
    """
    conds: dict = {}
    rs_pct: float = 0.0
    rs_line = None

    last = float(df["close"].iloc[-1])

    # N — New High: within 15% of 52-week high
    high_52 = float(df["high"].tail(252).max()) if len(df) >= 60 else float(df["high"].max())
    conds["N — Near 52w High (<15% below)"] = (high_52 - last) / high_52 < 0.15

    # S — Supply/Demand: today's volume ≥ 50-day average
    vol50 = float(df["volume"].tail(50).mean())
    vol_last = float(df["volume"].iloc[-1])
    conds["S — Volume ≥ 50d Average"] = vol_last >= vol50

    # M — Market direction: Nifty50 above its SMA200
    if nifty_df is not None and len(nifty_df) >= 200:
        nifty_sma200 = float(nifty_df["close"].rolling(200).mean().iloc[-1])
        conds["M — Market Above SMA200 (Uptrend)"] = float(nifty_df["close"].iloc[-1]) > nifty_sma200
    else:
        conds["M — Market Above SMA200 (Uptrend)"] = None

    # L — Leader: stock 12m return > Nifty 12m return (RS outperformance)
    if nifty_df is not None:
        nifty_aligned = nifty_df["close"].reindex(df.index, method="ffill")
        nifty_aligned = nifty_aligned.bfill()

        # RS Line normalized to 100 at first available point
        rs_raw = df["close"] / nifty_aligned.replace(0, float("nan"))
        rs_line = (rs_raw / rs_raw.iloc[0]) * 100

        lookback = min(252, len(df) - 1)
        if lookback >= 21:
            stock_12m = (float(df["close"].iloc[-1]) / float(df["close"].iloc[-lookback]) - 1) * 100
            nifty_12m = (float(nifty_aligned.iloc[-1]) / float(nifty_aligned.iloc[-lookback]) - 1) * 100
            rs_pct = stock_12m - nifty_12m

        conds["L — RS Leader (outperforms Nifty50)"] = rs_pct > 0
    else:
        conds["L — RS Leader (outperforms Nifty50)"] = None

    score = sum(1 for v in conds.values() if v is True)
    return score, conds, rs_pct, rs_line


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


def build_chart(symbol: str, df: pd.DataFrame, ew: dict,
                nifty_df: pd.DataFrame | None = None,
                harmonic: dict | None = None) -> go.Figure:
    rsi9  = RSIIndicator(df["close"], window=9).rsi()
    sma50  = df["close"].rolling(50).mean()
    sma150 = df["close"].rolling(150).mean()
    sma200 = df["close"].rolling(200).mean()

    ema9  = df["close"].ewm(span=9,  adjust=False).mean()
    ema21 = df["close"].ewm(span=21, adjust=False).mean()
    ema50 = df["close"].ewm(span=50, adjust=False).mean()

    # MACD (12, 26, 9)
    macd_line   = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist   = macd_line - macd_signal
    hist_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in macd_hist]

    # TSI (25, 13) + signal(13) — double-smoothed momentum (William Blau)
    price_change = df["close"].diff()
    abs_change   = price_change.abs()
    pcs   = price_change.ewm(span=25, adjust=False).mean().ewm(span=13, adjust=False).mean()
    apcs  = abs_change.ewm(span=25, adjust=False).mean().ewm(span=13, adjust=False).mean()
    tsi        = 100 * pcs / apcs.replace(0, float("nan"))
    tsi_signal = tsi.ewm(span=13, adjust=False).mean()

    # RS Line vs Nifty50
    rs_line = None
    if nifty_df is not None:
        nifty_aligned = nifty_df["close"].reindex(df.index, method="ffill").bfill()
        rs_raw = df["close"] / nifty_aligned.replace(0, float("nan"))
        rs_line = (rs_raw / rs_raw.iloc[0]) * 100

    # CPR (Central Pivot Range) — daily, from prior bar's H/L/C, plotted stepwise
    prev_h = df["high"].shift(1)
    prev_l = df["low"].shift(1)
    prev_c = df["close"].shift(1)
    cpr_p  = (prev_h + prev_l + prev_c) / 3.0
    cpr_bc = (prev_h + prev_l) / 2.0
    cpr_tc = 2.0 * cpr_p - cpr_bc
    cpr_top = cpr_tc.combine(cpr_bc, max)
    cpr_bot = cpr_tc.combine(cpr_bc, min)
    cpr_r1 = 2.0 * cpr_p - prev_l
    cpr_s1 = 2.0 * cpr_p - prev_h

    bin_centers, vap = _volume_profile(df)
    vap_max = vap.max() if vap.max() > 0 else 1.0

    n_rows = 6 if rs_line is not None else 5
    heights = [0.38, 0.10, 0.14, 0.14, 0.12, 0.12] if rs_line is not None else [0.42, 0.10, 0.16, 0.16, 0.16]
    titles  = (symbol, "Volume", "RSI(9)", "MACD (12,26,9)", "TSI (25,13,13)", "RS Line vs Nifty50") \
              if rs_line is not None else (symbol, "Volume", "RSI(9)", "MACD (12,26,9)", "TSI (25,13,13)")

    fig = make_subplots(
        rows=n_rows, cols=1, shared_xaxes=True,
        row_heights=heights, vertical_spacing=0.03,
        subplot_titles=titles,
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

    # CPR — pivot (solid), TC/BC bounds (dashed), R1/S1 (dotted)
    fig.add_trace(go.Scatter(x=df.index, y=cpr_p, name="CPR Pivot",
                              line=dict(color="#fdd835", width=1.2, shape="hv")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=cpr_top, name="CPR TC",
                              line=dict(color="#fdd835", width=1, dash="dash", shape="hv")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=cpr_bot, name="CPR BC",
                              line=dict(color="#fdd835", width=1, dash="dash", shape="hv"),
                              fill="tonexty", fillcolor="rgba(253,216,53,0.08)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=cpr_r1, name="CPR R1",
                              line=dict(color="#ff8a65", width=1, dash="dot", shape="hv"),
                              visible="legendonly"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=cpr_s1, name="CPR S1",
                              line=dict(color="#81c784", width=1, dash="dot", shape="hv"),
                              visible="legendonly"), row=1, col=1)

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

    # Harmonic pattern overlay (XABCD polyline + PRZ + entry/stop/targets)
    if harmonic:
        pts = harmonic["points"]
        color = "#00e5ff" if harmonic["direction"] == "bullish" else "#ff5252"
        xs = [df.index[pts[k]["idx"]] for k in ("X", "A", "B", "C", "D")]
        ys = [pts[k]["price"] for k in ("X", "A", "B", "C", "D")]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers+text", name=f"{harmonic['pattern']} ({harmonic['direction']})",
            line=dict(color=color, width=2),
            marker=dict(size=9, color=color),
            text=["X", "A", "B", "C", "D"], textposition="top center",
        ), row=1, col=1)
        trade = harmonic["trade"]
        fig.add_hline(y=trade["entry"], row=1, col=1, line_color=color, line_width=1.5,
                       annotation_text=f"Entry {trade['entry']}", annotation_position="right")
        fig.add_hline(y=trade["stop"], row=1, col=1, line_color="#ef5350", line_dash="dash",
                       annotation_text=f"Stop {trade['stop']}", annotation_position="right")
        for i, t in enumerate(trade["targets"], 1):
            fig.add_hline(y=t, row=1, col=1, line_color="#66bb6a", line_dash="dot",
                           annotation_text=f"T{i} {t}", annotation_position="right")

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

    # MACD row
    fig.add_trace(go.Bar(
        x=df.index, y=macd_hist, name="MACD Hist",
        marker_color=hist_colors, showlegend=True,
    ), row=4, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=macd_line, name="MACD",
        line=dict(color="#2196f3", width=1.5),
    ), row=4, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=macd_signal, name="Signal",
        line=dict(color="#ff9800", width=1.5, dash="dot"),
    ), row=4, col=1)
    fig.add_hline(y=0, row=4, col=1, line_dash="dot", line_color="gray", line_width=1)

    # TSI row (row 5) — TSI line + signal line + zero + ±25 bands
    tsi_row = 5
    fig.add_trace(go.Scatter(
        x=df.index, y=tsi, name="TSI(25,13)",
        line=dict(color="#ab47bc", width=1.5),
    ), row=tsi_row, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=tsi_signal, name="TSI Signal(13)",
        line=dict(color="#ffa726", width=1.25, dash="dot"),
    ), row=tsi_row, col=1)
    fig.add_hline(y=0, row=tsi_row, col=1, line_dash="dot", line_color="gray", line_width=1)
    fig.add_hline(y=25, row=tsi_row, col=1, line_dash="dot", line_color="gray", line_width=0.5)
    fig.add_hline(y=-25, row=tsi_row, col=1, line_dash="dot", line_color="gray", line_width=0.5)

    # RS Line (row 6, only when Nifty data is available)
    if rs_line is not None:
        rs_ma30 = rs_line.rolling(30).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=rs_line, name="RS Line",
            line=dict(color="#00bcd4", width=1.5), fill="tozeroy",
            fillcolor="rgba(0,188,212,0.08)",
        ), row=6, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=rs_ma30, name="RS MA(30)",
            line=dict(color="#ff9800", width=1, dash="dot"), showlegend=True,
        ), row=6, col=1)
        fig.add_hline(y=100, row=6, col=1, line_dash="dash", line_color="gray", line_width=1)

    chart_height = 1250 if rs_line is not None else 1150
    fig.update_layout(height=chart_height, xaxis_rangeslider_visible=False,
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

_SIGNAL_COLORS = {
    "Very Strong": "#16a34a", "Strong": "#65a30d", "Moderate": "#ca8a04",
    "Watch": "#ea580c", "Weak": "#dc2626",
}


def _score_ring_html(score: float, signal: str) -> str:
    """Circular score badge (0-100) coloured by signal band — the 'card ring'."""
    color = _SIGNAL_COLORS.get(signal, "#9a8778")
    deg = max(0.0, min(float(score), 100.0)) / 100 * 360
    return (
        f'<div style="flex-shrink:0;text-align:center;">'
        f'<div style="width:48px;height:48px;border-radius:50%;'
        f'background:conic-gradient({color} {deg}deg,#efe6d8 {deg}deg);'
        f'display:flex;align-items:center;justify-content:center;">'
        f'<div style="width:38px;height:38px;border-radius:50%;background:#fffdfa;'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:14px;font-weight:700;color:{color};">{score:.0f}</div></div>'
        f'<div style="font-size:9px;color:{color};font-weight:600;margin-top:2px;'
        f'text-transform:uppercase;letter-spacing:.3px;">{signal}</div></div>'
    )


def _scanner_stats_html(card: dict) -> str:
    """Compact stat row (RS · Vol Q · From pivot · Vol ×50d) + fail-risk chips.
    Renders only the fields the card actually carries, so scanners that don't
    emit the richer metadata degrade to nothing."""
    def chip(label: str, value: str, color: str = "#5c4a3a") -> str:
        return (
            f'<span style="display:inline-block;background:#f7efe3;border-radius:6px;'
            f'padding:2px 8px;margin:0 6px 4px 0;font-size:11px;color:{color};">'
            f'<b style="color:#9a8778;font-weight:600;">{label}</b> {value}</span>'
        )

    parts = []
    if "rs_rank" in card:
        rs = card["rs_rank"]
        parts.append(chip("RS", f"{rs:.0f}", "#16a34a" if rs >= 80 else "#5c4a3a"))
    if "base_q" in card:
        bq = card["base_q"]
        parts.append(chip("Base Q", f"{bq:.0f}", "#16a34a" if bq >= 65 else "#5c4a3a"))
    if card.get("vol_q"):
        parts.append(chip("Vol Q", card["vol_q"]))
    if "from_pivot" in card:
        parts.append(chip("From pivot", f'{card["from_pivot"]:+.1f}%'))
    if "vol_x50d" in card:
        vx = card["vol_x50d"]
        parts.append(chip("Vol ×50d", f"{vx:.1f}×", "#16a34a" if vx >= 1.5 else "#5c4a3a"))
    stats = "".join(parts)

    risks = card.get("fail_risk") or []
    risk_html = "".join(
        f'<span style="display:inline-block;background:#fef2f2;color:#b45309;'
        f'border:1px solid #fde0c0;border-radius:6px;padding:2px 8px;'
        f'margin:0 6px 4px 0;font-size:11px;">⚠ {r}</span>'
        for r in risks
    )
    if not stats and not risk_html:
        return ""
    return (f'<div style="margin:8px 0 4px 0;">{stats}{risk_html}</div>')


def _render_scanner_card(card: dict, scanner_name: str) -> None:
    sym = card["symbol"]
    pattern_type = card.get("pattern_type", scanner_name)
    metrics_html = "  ·  ".join(
        f'<span style="font-size:12px;color:#9a8778;">{t}</span>'
        for t in card.get("tags", [])
    )
    reasons_html = "".join(
        (f'<div style="display:flex;margin-bottom:6px;font-size:13px;color:#b45309;">'
         f'<span style="font-weight:bold;margin-right:6px;">⚠</span>{r.lstrip("⚠").strip()}</div>')
        if r.startswith("⚠") else
        (f'<div style="display:flex;margin-bottom:6px;font-size:13px;color:#5c4a3a;">'
         f'<span style="color:#16a34a;font-weight:bold;margin-right:6px;">✓</span>{r}</div>')
        for r in card.get("reasons", [])
    )
    # Score ring shows only when the scanner emits a graded 0-100 score + signal.
    ring_html = (
        _score_ring_html(card["score"], card["signal"])
        if "signal" in card and "score" in card else ""
    )
    stats_html = _scanner_stats_html(card)
    st.markdown(
        f"""
        <div style="border:1px solid #f0e0cc;border-radius:10px;padding:16px;
                    margin-bottom:4px;background:#fffdfa;
                    box-shadow:0 1px 3px rgba(120,80,40,0.06);">
          <div style="display:flex;align-items:center;margin-bottom:2px;">
            <div style="width:36px;height:36px;border-radius:8px;
                        background:linear-gradient(135deg,#fbbf24,#ea580c);
                        color:white;display:flex;align-items:center;
                        justify-content:center;font-weight:bold;
                        margin-right:10px;flex-shrink:0;">{sym[0]}</div>
            <div style="flex-grow:1;">
              <div style="font-size:16px;font-weight:700;color:#3a2a1e;">{sym}</div>
              <div style="margin-top:2px;">
                <span style="background:#fff1e0;color:#c2410c;padding:2px 9px;
                            border-radius:99px;font-size:11px;font-weight:600;
                            margin-right:8px;">{pattern_type}</span>{metrics_html}
              </div>
            </div>
            {ring_html}
          </div>
          {stats_html}
          {reasons_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([5, 1, 1])
    with c1:
        analyze_href = _analyze_url(sym)
        if analyze_href:
            st.link_button("↗ Analyze Setup", url=analyze_href, type="primary",
                           use_container_width=True,
                           help="Open the 3-POV Council analysis in a new tab")
    with c2:
        if st.button("★", key=f"sc_s_{sym}_{scanner_name}", help="Save",
                     use_container_width=True):
            db.save_scanner_hit(sym, scanner_name, card.get("pattern_type", ""))
            st.success(f"Saved {sym}")
    with c3:
        # Eye icon opens the multi-chart tool in a new tab (chart_server on :5001).
        # Bare NSE tickers are the scanner-hub norm — add .NS so yfinance resolves.
        chart_sym = sym if ("." in sym or sym.startswith("^")) else f"{sym}.NS"
        st.link_button(
            "👁",
            url=f"http://localhost:5001/?symbol={chart_sym}&tf=1d",
            help="Open in Chart Tool",
            use_container_width=True,
        )


with st.expander("Daily Workflow (IST)"):
    st.markdown(
        "| Time | Action |\n|---|---|\n"
        "| **8:30 AM** | Review news/earnings calendar, check overnight alerts, build watchlist |\n"
        "| **9:15 AM** | Monitor index + existing portfolio at open; watch for new pattern breakouts |\n"
        "| **9:15 – 3:30 PM** | Execute confirmed breakouts; manage stops/targets; monitor live alerts |\n"
        "| **3:30 PM onward** | Review fills, update portfolio, mark next day's candidates |"
    )
    st.caption("Screener pipeline auto-runs at 4:05 PM — aligned with the post-market review window.")

# ──────────────────────────────────────────────────────────────────────────────
# Navigation — left sidebar page router (replaces st.tabs; Streamlit can't
# switch tabs programmatically, so a real "click sidebar item -> jump to page"
# flow needs session_state + an if/elif router instead). Each PAGE_GROUPS entry
# must match a "if current_page == '...':" block below exactly.
# ──────────────────────────────────────────────────────────────────────────────
PAGE_GROUPS = {
    "Screening":        ["Screener", "Other Screeners", "Scanner Hub", "Breakout Screener",
                         "High-Growth Screener", "TradingView Screener"],
    "Market Intel":     ["Market Sentiment", "India Market Intel"],
    "Research":         ["Stock Analyzer", "Sector Map", "Astro Timing", "Telegram Signals"],
    "Portfolio & Risk": ["Portfolio", "Watchlist", "Alerts"],
    "Ops":              ["Pipeline Log"],
}

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Screener"

# Deep-link: a table's "Analyze ↗" link opens ?nav=analyze&symbol=SYM in a new
# tab. Consume the params once, route to the Stock Analyzer, pre-load the symbol
# and prime an auto-run, then clear the URL so sidebar navigation isn't pinned.
if st.query_params.get("nav") == "analyze" and st.query_params.get("symbol"):
    _dl_sym = st.query_params["symbol"].strip().upper()
    st.session_state["current_page"] = "Stock Analyzer"
    st.session_state["selected_symbol"] = _dl_sym
    st.session_state["last_analyzed"] = _dl_sym   # triggers auto-run in the tab
    st.query_params.clear()

with st.sidebar:
    st.markdown(
        '<div style="font-size:15px;font-weight:800;color:#3a2a1e;margin-bottom:12px;">'
        '📈 Trading <span style="color:#ea580c;">Bramha</span></div>',
        unsafe_allow_html=True,
    )
    for group_name, pages in PAGE_GROUPS.items():
        st.caption(group_name.upper())
        for p in pages:
            is_active = st.session_state["current_page"] == p
            if st.button(p, key=f"nav_{p}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state["current_page"] = p
                st.rerun()
        st.write("")

current_page = st.session_state["current_page"]


# ──────────────────────────────────────────────────────────────────────────────
# Tab 1 — Screener
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Screener":
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

        # Prepend a click-through "Chart" column that opens the multi-chart
        # tool at localhost:5001 for each row. Bare NSE symbols get .NS so
        # yfinance resolves (indices with a leading ^ pass through).
        view = view.copy()
        def _chart_url(s):
            s = str(s).strip().upper()
            if not s: return None
            return f"http://localhost:5001/?symbol={s if ('.' in s or s.startswith('^')) else s + '.NS'}&tf=1d"
        view.insert(1, "Chart", view["Symbol"].map(_chart_url))
        view = _with_analyze_col(view, "Symbol", after="Chart")

        st.dataframe(
            view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Chart": st.column_config.LinkColumn(
                    "Chart", help="Open in Chart Tool", display_text="Open ↗", width="small",
                ),
                "Analyze": _analyze_colcfg(),
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
if current_page == "Stock Analyzer":
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

    tf_choice = st.select_slider(
        "Chart lookback",
        options=["3M", "6M", "1Y", "2Y", "5Y", "10Y", "Max"],
        value="Max",
    )
    _tf_map = {"3M": 90, "6M": 180, "1Y": 365, "2Y": 730, "5Y": 1825, "10Y": 3650, "Max": 0}
    tf_days = _tf_map[tf_choice]

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
                nifty_df = cached_fetch_nifty50(days=tf_days)
                mv_score, mv_conds = sp.score_minervini(df, nifty_df=nifty_df)
                tf_score, tf_conds = sp.score_technofunda(df)
                ew = ew_module.analyze_ew(df)
                cs_score, cs_conds, rs_pct, _ = _compute_canslim(df, nifty_df)

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Minervini", f"{mv_score}/8")
                c2.metric("TechnoFunda", f"{tf_score}/6")
                c3.metric("Total", f"{mv_score + tf_score}/14")
                c4.metric("EW Confidence", f"{ew['confidence']}%")
                c5.metric("CANSLIM (RS)", f"{cs_score}/4",
                           delta=f"{rs_pct:+.1f}% vs Nifty",
                           delta_color="normal")

                st.info(
                    f"**Wave Position:** {ew['wave_pos']}  |  "
                    f"**Extension Risk:** {ew['ext_risk']}  |  "
                    f"**OWL:** {ew['owl_signal']}  |  **PTF:** {ew['ptf_signal']}  \n"
                    f"{ew['note']}"
                )

                show_harmonic = st.checkbox(
                    "Show Harmonic Pattern (Gartley/Bat/Butterfly/Crab)",
                    key="sa_harmonic",
                    help="Detects the most recent completed XABCD harmonic pattern "
                         "with a valid PRZ within the last ~10 bars. Plots entry, "
                         "stop (beyond X), and 0.382 / 0.618 / 1.0-of-AD targets.",
                )
                harmonic = hp.detect_last_pattern(df) if show_harmonic else None
                if show_harmonic:
                    if harmonic:
                        t = harmonic["trade"]
                        st.success(
                            f"**{harmonic['pattern']} ({harmonic['direction']})** — "
                            f"Entry {t['entry']} · Stop {t['stop']} · "
                            f"T1 {t['targets'][0]} / T2 {t['targets'][1]} / T3 {t['targets'][2]} · "
                            f"R:R to T2 = {t['rr_to_t2']} · D pivot {harmonic['age_bars']} bars ago"
                        )
                    else:
                        st.caption("No active harmonic pattern completing in the last 10 bars.")

                st.plotly_chart(build_chart(symbol, df, ew, nifty_df=nifty_df, harmonic=harmonic),
                                use_container_width=True)
                render_condition_table(mv_conds, tf_conds, cs_conds)

                # ── 3-POV Council: Bull / Bear / Judge ──
                st.divider()
                with st.spinner("Running deterministic council..."):
                    fundamentals = cached_fetch_fundamentals(symbol)
                    bundle, bull, bear, card = council.run_council(
                        symbol, df, nifty_df, fundamentals, regime=nifty_regime
                    )

                # Plain-language summary first, then the Bull/Bear/Judge drill-down.
                render_setup_intelligence(
                    council.setup_intelligence(bundle, bull, bear, card)
                )

                st.markdown("### 🧭 Council Verdict — Bull vs Bear vs Judge")
                render_council(bundle, bull, bear, card)

                if st.button("Add to Watchlist", key="sa_wl"):
                    db.add_watchlist_symbol(symbol, "From Stock Analyzer")
                    st.success(f"{symbol} added to watchlist.")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 3 — Portfolio
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Portfolio":
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
if current_page == "Watchlist":
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
if current_page == "Alerts":
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
if current_page == "Other Screeners":
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
        sessionid, browser = bch.get_screener_sessionid()
        if sessionid:
            st.caption(f"Using screener.in session from local browser ({browser}).")
        else:
            st.warning(
                "No screener.in `sessionid` cookie found in your local browsers "
                "(Chrome / Edge / Brave / Firefox). Log into screener.in in your "
                "default browser once, then re-run."
            )
        query = st.text_area("Query", value=default_query, height=120)

        if st.button("Run", type="primary"):
            if not sessionid:
                st.warning("No local browser cookie available — cannot query screener.in.")
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
if current_page == "Pipeline Log":
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
if current_page == "Scanner Hub":
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
        universe_mode = st.radio(
            "Universe",
            ["Full Market (Bhavcopy)", "Screener results", "Manual symbols"],
            key="hub_universe_mode",
            help="Full Market pulls NSE's daily bhavcopy (whole exchange) and takes "
                 "the top-N most-traded symbols — not limited to the ~250-stock daily "
                 "pipeline list.",
        )

        universe: list[str] = []
        if universe_mode == "Full Market (Bhavcopy)":
            bhav_top_n = st.slider(
                "Top N by traded value", min_value=50, max_value=1000, value=300, step=50,
                key="hub_bhav_top_n",
                help="Higher = broader market coverage but slower (one OHLCV fetch per symbol).",
            )
            universe = st.session_state.get("hub_bhav_universe", [])
            st.caption(
                f"{len(universe)} symbols loaded" if universe
                else "Click **Load Market Universe** below, then Run Scanner."
            )
            if st.button("Load Market Universe", key="hub_load_bhav"):
                with st.spinner("Fetching NSE bhavcopy…"):
                    try:
                        universe = cached_fetch_bhavcopy_universe(bhav_top_n)
                        st.session_state["hub_bhav_universe"] = universe
                    except Exception as exc:
                        st.error(f"Bhavcopy fetch failed: {exc}")
                st.rerun()
        elif universe_mode == "Screener results":
            if screener_res is not None and not screener_res.empty:
                universe = sorted(screener_res["Symbol"].unique())
                st.caption(f"Universe: {len(universe)} stocks from screener")
            else:
                st.caption("No screener results yet — run the Daily Screener Pipeline first.")
        else:
            raw = st.text_area("Symbols (comma / newline)", key="hub_manual", height=80)
            universe = [s.strip().upper() for s in raw.replace(",", "\n").splitlines() if s.strip()]

        if st.button("Run Scanner", type="primary", key="hub_run"):
            # Full Market mode used to require a separate "Load Market Universe"
            # click first and just refused to run otherwise — auto-load here
            # instead, so "Run Scanner" always does something sensible in one click.
            if not universe and universe_mode == "Full Market (Bhavcopy)":
                with st.spinner("Loading market universe…"):
                    try:
                        universe = cached_fetch_bhavcopy_universe(bhav_top_n)
                        st.session_state["hub_bhav_universe"] = universe
                    except Exception as exc:
                        st.error(f"Bhavcopy fetch failed: {exc}")

            if not universe:
                st.warning("No universe loaded — pick a source above "
                           "(Screener results needs the pipeline run first; "
                           "Manual symbols needs at least one symbol typed in).")
            else:
                # Nifty50 benchmark → scanners that grade RS (Darvas, Base
                # Formation) rank on excess return vs the index, not absolute.
                try:
                    bench_df = cached_fetch_nifty50()
                except Exception:
                    bench_df = None
                with st.spinner(f"Running {selected_scanner} on {len(universe)} symbols…"):
                    hits = sc.run_scanner(selected_scanner, universe, cached_fetch_ohlcv,
                                          benchmark_df=bench_df)
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
            # Filter pills only narrow what's on screen — they don't re-run the
            # scan. Shown only for scanners that emit the richer score/RS metadata.
            has_meta = any("signal" in h for h in hits)
            shown = hits
            if has_meta:
                # Tag pill options come from the cards themselves (filter_tags):
                # Breakout/Near breakout/Active for Darvas, VCP/Vol Dry/HTF for
                # Base Formation — so one control adapts to whatever scanner ran.
                tag_opts = sorted({
                    t for h in hits for t in h.get("filter_tags", [])
                })
                fc1, fc2 = st.columns(2)
                with fc1:
                    strength = st.pills(
                        "Strength", ["All", "Strongest", "Moderate", "Vol Confirmed", "Leading RS"],
                        default="All", key="hub_strength",
                        help="Strongest = score ≥ 65 · Moderate = 45–65 · "
                             "Vol Confirmed = vol ≥ 1× 50-day · Leading RS = RS rank ≥ 80",
                    ) or "All"
                with fc2:
                    tag_pick = (st.pills(
                        "Tag", ["Any", *tag_opts], default="Any", key="hub_tag",
                    ) or "Any") if tag_opts else "Any"

                # F&O toggle — only shown when a symbol master is present.
                fno_set = cached_fno_symbols()
                fno_only = st.toggle(
                    "F&O only", key="hub_fno",
                    help="Limit to NSE F&O (derivative-eligible) names "
                         f"({len(fno_set)} in tools/cache/fno_symbols.json)",
                ) if fno_set else False

                def _keep(h: dict) -> bool:
                    sc_ = h.get("score", 0)
                    if strength == "Strongest" and sc_ < 65:
                        return False
                    if strength == "Moderate" and not (45 <= sc_ < 65):
                        return False
                    if strength == "Vol Confirmed" and h.get("vol_x50d", 0) < 1.0:
                        return False
                    if strength == "Leading RS" and h.get("rs_rank", 0) < 80:
                        return False
                    if tag_pick != "Any" and tag_pick not in h.get("filter_tags", []):
                        return False
                    if fno_only and h.get("symbol", "").upper().replace(".NS", "") not in fno_set:
                        return False
                    return True

                shown = [h for h in hits if _keep(h)]

            filt_note = "" if len(shown) == len(hits) else f" ({len(hits)} matched)"
            st.caption(f"Showing {len(shown)} stocks{filt_note} · sorted by score")
            if not shown:
                st.info("No stocks match the current filter pills — widen the filter above.")
            cols_n = 3
            for i in range(0, len(shown), cols_n):
                batch = shown[i:i + cols_n]
                cols = st.columns(cols_n)
                for col, card in zip(cols, batch):
                    with col:
                        _render_scanner_card(card, selected_scanner)


# ──────────────────────────────────────────────────────────────────────────────
# Tab 9 — Sector Map (live heatmap + rotation quadrant + orbit chart)
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Sector Map":
    st.subheader("Sector Map")

    if st.button("Fetch / Refresh Sector Data", type="primary"):
        cached_fetch_sector_data.clear()
        with st.spinner("Fetching sector index data from yfinance…"):
            st.session_state["sector_data"] = cached_fetch_sector_data()

    if "sector_data" not in st.session_state:
        st.info("Click **Fetch / Refresh Sector Data** to load live sector index data.")
    else:
        sector_data: dict = st.session_state["sector_data"]
        if not sector_data:
            st.warning("No sector index data could be fetched — check your internet connection.")
        else:
            # ── Row 1: heatmap + rotation quadrant ────────────────────────────
            hm_col, rq_col = st.columns(2)

            # ── Heatmap ───────────────────────────────────────────────────────
            with hm_col:
                st.markdown("#### Sector Performance Heatmap")
                period_choice = st.radio(
                    "Period", ["1D", "1W", "1M", "3M", "1Y"],
                    horizontal=True, key="sm_period",
                )
                period_days = {"1D": 1, "1W": 5, "1M": 21, "3M": 63, "1Y": 252}
                days = period_days[period_choice]

                hm_rows = []
                for ticker, name in SECTOR_DISPLAY_NAMES.items():
                    df_s = sector_data.get(ticker)
                    if df_s is None:
                        continue
                    ret = _period_return(df_s, days)
                    if ret is not None:
                        hm_rows.append({"Sector": name, "Return": ret})

                if hm_rows:
                    hm_df = pd.DataFrame(hm_rows).sort_values("Return", ascending=False)

                    fig_hm = go.Figure(go.Treemap(
                        labels=hm_df["Sector"],
                        parents=[""] * len(hm_df),
                        values=[abs(r) + 0.5 for r in hm_df["Return"]],
                        customdata=hm_df[["Return"]],
                        texttemplate="%{label}<br>%{customdata[0]:.2f}%",
                        hovertemplate="%{label}<br>Return: %{customdata[0]:.2f}%<extra></extra>",
                        marker=dict(
                            colors=hm_df["Return"],
                            colorscale=[[0, "#ef5350"], [0.5, "#f0f0f0"], [1, "#26a69a"]],
                            cmid=0,
                            showscale=True,
                            colorbar=dict(title="Return %", len=0.8),
                        ),
                    ))
                    fig_hm.update_layout(
                        height=420, margin=dict(t=4, l=0, r=0, b=0),
                    )
                    st.plotly_chart(fig_hm, use_container_width=True)

                    # Sorted table — with an "Open ↗" Chart column that opens
                    # each sector index in the multi-chart tool (`^` and `.NS`
                    # tickers pass through unchanged).
                    tbl = hm_df.copy()
                    tbl["Return"] = tbl["Return"].apply(fmt_pct)
                    _name_to_ticker = {n: t for t, n in SECTOR_DISPLAY_NAMES.items()}
                    tbl.insert(1, "Chart", tbl["Sector"].map(
                        lambda n: f"http://localhost:5001/?symbol={_name_to_ticker.get(n, '')}&tf=1d"
                        if _name_to_ticker.get(n) else None
                    ))
                    st.dataframe(
                        tbl, use_container_width=True, hide_index=True,
                        column_config={
                            "Chart": st.column_config.LinkColumn(
                                "Chart", help="Open in Chart Tool",
                                display_text="Open ↗", width="small",
                            ),
                        },
                    )

            # ── Rotation quadrant ─────────────────────────────────────────────
            with rq_col:
                st.markdown("#### Sector Rotation Quadrant")
                st.caption("X = 1Y index return (strength)  ·  Y = 1M return (recent momentum)")

                rq_rows = []
                for ticker, name in SECTOR_DISPLAY_NAMES.items():
                    df_s = sector_data.get(ticker)
                    if df_s is None:
                        continue
                    ret_1y = _period_return(df_s, 252)
                    ret_1m = _period_return(df_s, 21)
                    if ret_1y is not None and ret_1m is not None:
                        rq_rows.append({"Sector": name, "1Y": ret_1y, "1M": ret_1m})

                if rq_rows:
                    rq_df = pd.DataFrame(rq_rows)

                    dot_colors, quadrant_labels = [], []
                    for _, row in rq_df.iterrows():
                        x, y = row["1Y"], row["1M"]
                        if x >= 0 and y >= 0:
                            dot_colors.append("#26a69a"); quadrant_labels.append("Leading")
                        elif x < 0 and y >= 0:
                            dot_colors.append("#ffa726"); quadrant_labels.append("Improving")
                        elif x >= 0 and y < 0:
                            dot_colors.append("#ff7043"); quadrant_labels.append("Weakening")
                        else:
                            dot_colors.append("#ef5350"); quadrant_labels.append("Lagging")
                    rq_df["Quadrant"] = quadrant_labels

                    x_pad = max(10, abs(rq_df["1Y"].max() - rq_df["1Y"].min()) * 0.18)
                    y_pad = max(3,  abs(rq_df["1M"].max() - rq_df["1M"].min()) * 0.22)
                    x0 = rq_df["1Y"].min() - x_pad;  x1 = rq_df["1Y"].max() + x_pad
                    y0 = rq_df["1M"].min() - y_pad;  y1 = rq_df["1M"].max() + y_pad

                    fig_rq = go.Figure()

                    # Quadrant background fills
                    _fills = [
                        (0, x1, 0, y1, "rgba(38,166,154,0.07)"),   # Leading
                        (x0, 0, 0, y1, "rgba(255,167,38,0.07)"),    # Improving
                        (0, x1, y0, 0, "rgba(255,112,67,0.07)"),    # Weakening
                        (x0, 0, y0, 0, "rgba(239,83,80,0.07)"),     # Lagging
                    ]
                    for fx0, fx1, fy0, fy1, fc in _fills:
                        fig_rq.add_shape(type="rect", x0=fx0, x1=fx1, y0=fy0, y1=fy1,
                                          fillcolor=fc, line_width=0, layer="below")

                    fig_rq.add_hline(y=0, line_dash="dash",
                                      line=dict(color="rgba(90,90,90,0.35)", width=1))
                    fig_rq.add_vline(x=0, line_dash="dash",
                                      line=dict(color="rgba(90,90,90,0.35)", width=1))

                    fig_rq.add_trace(go.Scatter(
                        x=rq_df["1Y"], y=rq_df["1M"],
                        mode="markers+text",
                        text=rq_df["Sector"],
                        textposition="top center",
                        textfont=dict(size=10, color="#333"),
                        marker=dict(color=dot_colors, size=14,
                                    line=dict(color="white", width=1.5)),
                        customdata=rq_df[["Quadrant"]],
                        hovertemplate=(
                            "<b>%{text}</b><br>"
                            "1Y: %{x:.1f}%<br>"
                            "1M: %{y:.1f}%<br>"
                            "Quadrant: %{customdata[0]}<extra></extra>"
                        ),
                    ))

                    _qlabels = [
                        (x1 * 0.97, y1 * 0.92, "Leading",   "#26a69a", "right"),
                        (x0 * 0.97 if x0 < 0 else x0 + 1, y1 * 0.92,
                         "Improving", "#e6900a", "left"),
                        (x1 * 0.97, y0 * 0.92, "Weakening", "#e05530", "right"),
                        (x0 * 0.97 if x0 < 0 else x0 + 1, y0 * 0.92,
                         "Lagging",   "#c0392b", "left"),
                    ]
                    annotations = [
                        dict(x=lx, y=ly, text=f"<b>{lt}</b>", showarrow=False,
                             font=dict(color=lc, size=11), xanchor=la)
                        for lx, ly, lt, lc, la in _qlabels
                    ]

                    fig_rq.update_layout(
                        height=420,
                        xaxis=dict(title="1Y Return (%)", range=[x0, x1], zeroline=False),
                        yaxis=dict(title="1M Return (%)", range=[y0, y1], zeroline=False),
                        showlegend=False,
                        annotations=annotations,
                        margin=dict(t=20, l=60, r=20, b=60),
                    )
                    st.plotly_chart(fig_rq, use_container_width=True)

    # ── Row 2: historical orbit chart ─────────────────────────────────────────
    st.divider()
    st.markdown("#### Historical Sector Rotation Orbit Chart")
    st.caption(
        "Generated by **Pipeline → Sector Rotation** in the Other Screeners tab. "
        "Requires a screener.in export with FII_<quarter> columns."
    )

    # Regenerate directly from the most recent screener export (no detour to Other Screeners)
    export_files = sorted(BASE_DIR.glob("screener_export_*.csv"), reverse=True)
    col_regen, col_src = st.columns([1, 3])
    with col_regen:
        regen_clicked = st.button(
            "🔄 Regenerate",
            disabled=not export_files,
            help=(
                "Re-run sector_rotation + sector_rotation_trail on the most recent "
                "screener export to produce a fresh dated orbit map."
                if export_files else
                "No screener_export_*.csv found. Run a screener.in query in "
                "Other Screeners → Pipeline → Sector Rotation first."
            ),
        )
    with col_src:
        if export_files:
            st.caption(f"Regenerate source: `{export_files[0].name}`")
        else:
            st.caption("No screener export found yet — run one in **Other Screeners** first.")

    if regen_clicked and export_files:
        try:
            with st.spinner("Running sector_rotation + sector_rotation_trail..."):
                secrot.run(export_files[0])
                secrot_trail.run(export_files[0])
        except Exception as exc:
            st.error(f"Sector rotation pipeline failed: {exc}")
        else:
            st.success("Regenerated a fresh orbit map. Reloading…")
            st.rerun()

    selected_name = None
    html_files = sorted(BASE_DIR.glob("sector_rotation_orbit_*.html"), reverse=True)
    if html_files:
        names = [f.name for f in html_files]
        selected_name = st.selectbox(
            "Orbit chart snapshot",
            names,
            index=0,
            help="Newest first. Each file is a dated snapshot from a past pipeline run.",
        )
        selected_html = BASE_DIR / selected_name
        components.html(selected_html.read_text(encoding="utf-8"), height=740, scrolling=True)
    else:
        st.info(
            "No orbit chart found yet. "
            "Go to **Other Screeners** → run a screener.in query → **Pipeline → Sector Rotation** "
            "to generate it."
        )

    # Saved sector rotation table — follow the selected orbit snapshot's date when possible
    xlsx_files = sorted(BASE_DIR.glob("sector_rotation_*.xlsx"), reverse=True)
    if xlsx_files:
        table_path = xlsx_files[0]
        if selected_name:
            # sector_rotation_orbit_YYYYMMDD.html -> sector_rotation_YYYYMMDD.xlsx
            date_suffix = selected_name.replace("sector_rotation_orbit_", "").replace(".html", "")
            matched = BASE_DIR / f"sector_rotation_{date_suffix}.xlsx"
            if matched.exists():
                table_path = matched
        with st.expander("Saved Sector Rotation Table"):
            try:
                df_sr = pd.read_excel(table_path, sheet_name="Sector Rotation")
                st.caption(f"Source: `{table_path.name}`")
                st.dataframe(df_sr, use_container_width=True, hide_index=True)
            except Exception as e:
                st.warning(f"Could not load table: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 10 — Astro Timing
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Astro Timing":
    st.subheader("Astrological Trading Timing")
    st.caption(
        "Lunar cycles, solar timing, and market intensity indicators. "
        "Based on Vedic astrology principles for optimal entry/exit timing."
    )

    # City selector
    col_city, col_date = st.columns(2)
    with col_city:
        city = st.selectbox("Select Location", list(at.AstroIndicators.CITIES.keys()), index=0)
    with col_date:
        analysis_date = st.date_input("Analysis Date", value=date.today())

    ai = at.AstroIndicators(city=city)
    timing = ai.get_trading_timing(analysis_date)

    # Daily summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Lunar Phase",
            timing['lunar_phase']['phase'].title(),
            f"{timing['lunar_phase']['illumination']}% illuminated"
        )
    with col2:
        st.metric(
            "Market Intensity",
            f"{timing['market_intensity']}/100",
            "Volatility indicator"
        )
    with col3:
        st.metric(
            "Cycle Day",
            f"{timing['lunar_phase']['cycle_day']:.1f}",
            f"of {timing['lunar_phase']['cycle_length']:.1f}"
        )
    with col4:
        st.metric("Location", city, "")

    # Solar timing
    st.subheader("Solar Timing (IST)")
    scol1, scol2, scol3, scol4 = st.columns(4)
    with scol1:
        st.metric("Sunrise", timing['solar_timing']['sunrise'])
    with scol2:
        st.metric("Sunset", timing['solar_timing']['sunset'])
    with scol3:
        st.metric("Optimal Entry", timing['solar_timing']['optimal_entry'], "15 min post-sunrise")
    with scol4:
        st.metric("Optimal Exit", timing['solar_timing']['optimal_exit'], "15 min pre-sunset")

    # Recommendations
    st.subheader("Trading Recommendations")
    for i, rec in enumerate(timing['recommendations'], 1):
        st.info(f"**{i}.** {rec}")

    # Weekly calendar
    st.subheader("Weekly Astro Calendar")
    today = date.today()
    weekly = ai.get_weekly_calendar(today, days=7)

    # Format for display
    display_cols = ['date', 'lunar_phase', 'illumination', 'market_intensity', 'sunrise', 'sunset']
    display_df = weekly[display_cols].copy()
    display_df.columns = ['Date', 'Lunar Phase', 'Illumination %', 'Market Intensity', 'Sunrise', 'Sunset']

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Lunar phase chart
    st.subheader("Lunar Phase Progression")

    dates_list = []
    illumination_list = []
    intensity_list = []

    for i in range(30):
        d = date.today() + timedelta(days=i)
        dates_list.append(d.strftime('%m-%d'))
        lunar = ai.get_lunar_phase(d)
        illumination_list.append(lunar['illumination'])
        timing_temp = ai.get_trading_timing(d)
        intensity_list.append(timing_temp['market_intensity'])

    fig_astro = go.Figure()
    fig_astro.add_trace(go.Scatter(
        x=dates_list,
        y=illumination_list,
        mode='lines+markers',
        name='Lunar Illumination %',
        line=dict(color='gold', width=2),
        yaxis='y1'
    ))
    fig_astro.add_trace(go.Scatter(
        x=dates_list,
        y=intensity_list,
        mode='lines+markers',
        name='Market Intensity',
        line=dict(color='crimson', width=2),
        yaxis='y2'
    ))

    fig_astro.update_layout(
        title="30-Day Lunar & Market Intensity Forecast",
        hovermode='x unified',
        xaxis_title="Date",
        yaxis=dict(title="Lunar Illumination %", side='left'),
        yaxis2=dict(title="Market Intensity", side='right', overlaying='y'),
        height=500
    )

    st.plotly_chart(fig_astro, use_container_width=True)

    # AstroHora integration section
    st.subheader("AstroHora Chart Data Integration")
    st.caption("Load birth charts or event data from AstroHora for deeper astrological analysis.")

    upload_col, manual_col = st.columns(2)

    with upload_col:
        st.write("**Upload AstroHora Data**")
        uploaded_file = st.file_uploader(
            "Load CSV/Excel export from AstroHora",
            type=['csv', 'xlsx'],
            key='astro_upload'
        )

        if uploaded_file:
            aha = ahl.AstroHoraData()
            try:
                if uploaded_file.name.endswith('.csv'):
                    import io
                    stringio = io.StringIO(uploaded_file.getvalue().decode("utf8"))
                    csv_reader = csv.DictReader(stringio)
                    for row in csv_reader:
                        aha._parse_row(row)
                else:
                    # Excel handling
                    import io
                    df = pd.read_excel(uploaded_file)
                    aha._parse_astro_dataframe(df)

                st.success("✓ Chart data loaded")

                summary = aha.get_summary()
                st.json(summary, expanded=False)

            except Exception as e:
                st.error(f"Error loading file: {e}")

    with manual_col:
        st.write("**Or Enter Chart Details**")
        chart_type = st.selectbox("Chart Type", ["natal", "prashna"], key='chart_type_select')
        birth_location = st.text_input("Location (e.g., Mumbai, India)", value="Mumbai, India")

        if st.button("Load Example Chart", key='example_chart_btn'):
            from datetime import time

            aha = ahl.AstroHoraData()
            example_chart = {
                'chart_type': 'natal',
                'birth_date': date(1990, 6, 15),
                'birth_time': time(14, 30),
                'location': birth_location,
                'chart_data': {
                    'Sun': {'sign': 'Gemini', 'longitude': 84.5, 'house': '11'},
                    'Moon': {'sign': 'Libra', 'longitude': 207.2, 'house': '3'},
                    'Mars': {'sign': 'Leo', 'longitude': 123.8, 'house': '1'},
                    'Mercury': {'sign': 'Gemini', 'longitude': 91.3, 'house': '11'},
                    'Jupiter': {'sign': 'Cancer', 'longitude': 99.5, 'house': '12'},
                    'Venus': {'sign': 'Cancer', 'longitude': 108.7, 'house': '12'},
                    'Saturn': {'sign': 'Capricorn', 'longitude': 286.4, 'house': '6'},
                }
            }
            aha.load_from_dict(example_chart)

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.write("**Planetary Positions**")
                for planet, data in aha.get_planetary_positions().items():
                    st.text(f"{planet}: {data['sign']} {data['degree']}°")

            with col_b:
                st.write("**Strong Planets**")
                for planet, status in aha.get_strong_planets():
                    st.text(f"{planet}: {status}")

            with col_c:
                st.write("**Major Aspects**")
                for aspect in aha.get_aspectarian():
                    st.text(f"{aspect['planet1']} {aspect['aspect']} {aspect['planet2']}")

            st.write("**Dasha Analysis**")
            dasha = aha.get_vimshottari_dasha(date(1990, 6, 15))
            dasha_col1, dasha_col2, dasha_col3 = st.columns(3)
            with dasha_col1:
                st.metric("Current Dasha", dasha['current_dasha'])
            with dasha_col2:
                st.metric("Years Remaining", f"{dasha['years_remaining']:.1f}")
            with dasha_col3:
                st.metric("Period Length", f"{dasha['period_years']} yrs")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 11 — Telegram Signals
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Telegram Signals":
    st.subheader("Telegram Trading Signals")
    st.caption(
        "Track trading signals from Telegram channels (Rohan Das RPCI, TechnoFunda, etc). "
        "Manually add signals, track entries/exits, and measure performance."
    )

    # Initialize signal manager
    ts = tg.TelegramSignals()

    # Tab sections
    signal_tab1, signal_tab_fetch, signal_tab2, signal_tab3, signal_tab4 = st.tabs(
        ["Add Signal", "Fetch from Channel", "Active Signals", "Signal History", "Statistics"]
    )

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Fetch from public Telegram preview
    with signal_tab_fetch:
        st.subheader("Fetch from Public Telegram Preview")
        st.caption(
            "Pulls the ~20 most recent posts from `t.me/s/<channel>` (no auth). "
            "Preview truncates long posts — verify on Telegram before saving."
        )
        fetch_col1, fetch_col2 = st.columns([3, 1])
        with fetch_col1:
            fetch_channel_name = st.text_input(
                "Channel username (without @)",
                value="FinanceWithSunil",
                key="fetch_tg_channel",
            )
        with fetch_col2:
            st.write("")
            st.write("")
            do_fetch = st.button("Fetch posts", type="primary", key="fetch_tg_btn")

        if do_fetch:
            try:
                import telegram_preview_scraper as tps
                with st.spinner(f"Fetching @{fetch_channel_name}..."):
                    posts = tps.fetch_channel(fetch_channel_name)
                st.session_state["tg_fetched_posts"] = [p.to_dict() for p in posts]
                st.session_state["tg_fetched_channel"] = fetch_channel_name
                st.success(f"Fetched {len(posts)} posts.")
            except Exception as e:
                st.error(f"Fetch failed: {e}")

        posts_cache = st.session_state.get("tg_fetched_posts", [])
        if posts_cache:
            channel_label = f"@{st.session_state.get('tg_fetched_channel', fetch_channel_name)}"
            st.markdown(f"**{len(posts_cache)} posts from {channel_label}** (newest last)")
            for idx, p in enumerate(posts_cache):
                header = f"[{p.get('posted_at', '?')}] {' · '.join(p.get('tickers') or []) or '(no ticker detected)'}"
                with st.expander(header, expanded=False):
                    st.write(p.get("text", ""))
                    if p.get("url"):
                        st.markdown(f"[Open on Telegram]({p['url']})")
                    tickers = p.get("tickers") or []
                    if tickers:
                        pick = st.selectbox(
                            "Symbol to save",
                            tickers,
                            key=f"tg_pick_{idx}",
                        )
                        if st.button("Save as PENDING signal", key=f"tg_save_{idx}"):
                            try:
                                posted = None
                                if p.get("posted_at"):
                                    posted = datetime.fromisoformat(
                                        p["posted_at"].replace("Z", "+00:00")
                                    ).date()
                            except Exception:
                                posted = date.today()
                            sig = ts.add_signal_from_dict({
                                "symbol": pick,
                                "channel": channel_label,
                                "posted_date": posted or date.today(),
                                "strategy": "",
                                "signal_source": "OTHER",
                                "timeframe": "",
                                "confidence": 5,
                                "notes": (p.get("text") or "") + (f"\n\nSource: {p['url']}" if p.get("url") else ""),
                                "metadata": {"source_url": p.get("url"), "posted_at": p.get("posted_at")},
                            })
                            st.success(f"Saved {sig.signal_id}")

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Add New Signal
    with signal_tab1:
        st.subheader("Add Signal from Telegram")

        col1, col2 = st.columns(2)

        with col1:
            channel = st.text_input(
                "Telegram Channel",
                value="Rohan Das (@rohaninvestor)",
                placeholder="e.g., Rohan Das (@rohaninvestor)"
            )
            symbol = st.text_input(
                "Stock Symbol",
                value="",
                placeholder="e.g., MOTHERSON, RELIANCE, TCS"
            ).upper()
            signal_date = st.date_input("Signal Posted Date", value=date.today())
            strategy = st.text_input(
                "Strategy/Indicator",
                value="RPCI",
                placeholder="e.g., RPCI, TechnoFunda, Chart Pattern"
            )

        with col2:
            timeframe = st.selectbox(
                "Timeframe",
                ["Intraday", "Short-term (1-3 days)", "Medium-term (1-4 weeks)", "Long-term (1-3 months)"]
            )
            confidence = st.slider("Confidence Level", min_value=1, max_value=10, value=5)
            entry_price = st.number_input("Entry Price (Optional)", value=0.0, step=0.01)
            target_price = st.number_input("Target Price (Optional)", value=0.0, step=0.01)
            stop_loss = st.number_input("Stop Loss (Optional)", value=0.0, step=0.01)

        notes = st.text_area(
            "Notes/Analysis",
            height=150,
            placeholder="Paste signal details, analysis, or key points from Telegram post..."
        )

        # Pre-filled Rohan Das RPCI example
        if st.button("Load Example: Rohan Das RPCI (MOTHERSON)", key='example_rpci'):
            symbol = 'MOTHERSON'
            strategy = 'RPCI Indicator'
            channel = 'Rohan Das (@rohaninvestor)'
            signal_date = date(2026, 6, 25)
            confidence = 8
            timeframe = 'Medium-term (1-4 weeks)'
            notes = (
                "RPCI identified MOTHERSON before SEBI RA recommendation.\n"
                "Stock recommended for next week accumulation.\n"
                "RPCI simplifies technical analysis with rule-based signals.\n"
                "Used by 1500+ traders including SEBI registered users.\n\n"
                "SEBI RA confirmation: 27 June for next week accumulation."
            )

            st.session_state.signal_symbol = symbol
            st.session_state.signal_channel = channel
            st.session_state.signal_strategy = strategy
            st.session_state.signal_date = signal_date
            st.session_state.signal_confidence = confidence
            st.session_state.signal_timeframe = timeframe
            st.session_state.signal_notes = notes
            st.rerun()

        if st.button("Add Signal", type="primary", key='add_signal_btn'):
            if not symbol or not channel:
                st.error("Symbol and Channel are required")
            else:
                signal_data = {
                    'symbol': symbol,
                    'channel': channel,
                    'posted_date': signal_date,
                    'strategy': strategy,
                    'signal_source': strategy.upper().replace(' ', '_') if strategy else 'OTHER',
                    'timeframe': timeframe,
                    'confidence': confidence,
                    'entry_price': entry_price if entry_price > 0 else None,
                    'target_price': target_price if target_price > 0 else None,
                    'stop_loss': stop_loss if stop_loss > 0 else None,
                    'notes': notes,
                    'metadata': {
                        'added_on': datetime.now().isoformat(),
                        'manual_entry': True,
                    }
                }

                signal = ts.add_signal_from_dict(signal_data)
                st.success(f"Signal added: {signal.signal_id}")
                st.balloons()

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Active Signals
    with signal_tab2:
        st.subheader("Active & Pending Signals")

        active = ts.get_active_signals()

        if not active:
            st.info("No active signals. Add one above.")
        else:
            for signal in active:
                with st.expander(f"{signal.symbol} — {signal.strategy} (Confidence: {signal.confidence}/10)", expanded=False):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Symbol", signal.symbol)
                        st.metric("Channel", signal.channel[:30])
                        st.metric("Status", signal.status.value.title())

                    with col2:
                        st.metric("Entry Price", f"₹{signal.entry_price}" if signal.entry_price else "—")
                        st.metric("Target", f"₹{signal.target_price}" if signal.target_price else "—")
                        st.metric("Stop Loss", f"₹{signal.stop_loss}" if signal.stop_loss else "—")

                    with col3:
                        st.metric("Timeframe", signal.timeframe or "—")
                        st.metric("Confidence", f"{signal.confidence}/10")
                        st.metric("Posted", signal.posted_date.strftime('%d-%b') if signal.posted_date else "—")

                    if signal.notes:
                        st.write("**Notes:**")
                        st.caption(signal.notes)

                    # Update signal status
                    col_update1, col_update2, col_update3, col_update4 = st.columns(4)
                    with col_update1:
                        if st.button("Mark Active", key=f"active_{signal.signal_id}"):
                            ts.update_signal(signal.signal_id, status=tg.SignalStatus.ACTIVE, entry_date=date.today())
                            st.rerun()
                    with col_update2:
                        if st.button("Partial Exit", key=f"partial_{signal.signal_id}"):
                            ts.update_signal(signal.signal_id, status=tg.SignalStatus.PARTIAL)
                            st.rerun()
                    with col_update3:
                        exit_return = st.number_input("Return %", value=0.0, step=0.1, key=f"return_{signal.signal_id}")
                        if st.button("Close", key=f"close_{signal.signal_id}"):
                            ts.update_signal(
                                signal.signal_id,
                                status=tg.SignalStatus.CLOSED,
                                exit_date=date.today(),
                                realized_return=exit_return
                            )
                            st.rerun()
                    with col_update4:
                        if st.button("Cancel", key=f"cancel_{signal.signal_id}"):
                            ts.update_signal(signal.signal_id, status=tg.SignalStatus.CANCELLED)
                            st.rerun()

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Signal History
    with signal_tab3:
        st.subheader("All Signals History")

        if not ts.signals:
            st.info("No signals recorded yet.")
        else:
            # Display as table
            signal_list = []
            for sig_id, signal in ts.signals.items():
                signal_list.append({
                    'Symbol': signal.symbol,
                    'Channel': signal.channel[:20],
                    'Strategy': signal.strategy,
                    'Status': signal.status.value.title(),
                    'Confidence': f"{signal.confidence}/10",
                    'Entry': f"₹{signal.entry_price}" if signal.entry_price else "—",
                    'Target': f"₹{signal.target_price}" if signal.target_price else "—",
                    'Return %': f"{signal.realized_return}%" if signal.realized_return else "—",
                    'Posted': signal.posted_date.strftime('%d-%b-%y') if signal.posted_date else "—",
                })

            df_signals = pd.DataFrame(signal_list)
            st.dataframe(df_signals, use_container_width=True, hide_index=True)

            # Export option
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                csv_export = ts.export_to_csv()
                if csv_export:
                    st.success(f"Exported to: `{csv_export}`")

    # ──────────────────────────────────────────────────────────────────────────────
    # Subsection: Statistics
    with signal_tab4:
        st.subheader("Signal Performance Statistics")

        stats = ts.get_signal_statistics()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Signals", stats['total_signals'])
        with col2:
            st.metric("Active/Pending", stats['active_signals'])
        with col3:
            st.metric("Closed", stats['closed_signals'])
        with col4:
            st.metric("Win Rate", f"{stats['win_rate']}%" if stats['closed_signals'] > 0 else "—")

        col5, col6, col7 = st.columns(3)
        with col5:
            st.metric("Avg Return", f"{stats['avg_return']}%" if stats['closed_signals'] > 0 else "—")
        with col6:
            st.metric("Total Return", f"{stats['total_return']}%" if stats['closed_signals'] > 0 else "—")
        with col7:
            st.metric("Best Signal", stats['best_return'] if stats['best_signal'] else "—")

        # By channel breakdown
        st.subheader("Signals by Channel")
        channels = {}
        for signal in ts.signals.values():
            if signal.channel not in channels:
                channels[signal.channel] = 0
            channels[signal.channel] += 1

        if channels:
            channel_df = pd.DataFrame(
                list(channels.items()),
                columns=['Channel', 'Signal Count']
            ).sort_values('Signal Count', ascending=False)
            st.dataframe(channel_df, use_container_width=True, hide_index=True)

        # By strategy breakdown
        st.subheader("Signals by Strategy")
        strategies = {}
        for signal in ts.signals.values():
            if signal.strategy not in strategies:
                strategies[signal.strategy] = 0
            strategies[signal.strategy] += 1

        if strategies:
            strategy_df = pd.DataFrame(
                list(strategies.items()),
                columns=['Strategy', 'Signal Count']
            ).sort_values('Signal Count', ascending=False)
            st.dataframe(strategy_df, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────────────────────
# Tab 12 — Breakout Screener  (live Chartink fetch across entire market)
# ──────────────────────────────────────────────────────────────────────────────
import chartink_scraper as ck

if current_page == "Breakout Screener":
    st.subheader("Breakout Screener — Live via Chartink")
    st.caption(
        "Runs directly against **chartink.com** across the entire cash market. "
        "No stock list needed — Chartink scans every listed stock server-side. "
        "Paste your `_chartink_session` cookie once; it lasts for months."
    )

    _CK_SCANNERS = {
        "6M Consolidation Breakout": {"color": "#58a6ff", "lookback": "6 months"},
        "1Y All-Time Breakout":      {"color": "#3fb950", "lookback": "1 year"},
        "3Y Breakout":               {"color": "#d29922", "lookback": "3 years"},
        "5Y Breakout":               {"color": "#f0883e", "lookback": "5 years"},
        "10Y Breakout":              {"color": "#f85149", "lookback": "10 years"},
    }

    bk_left, bk_main = st.columns([1, 3])

    with bk_left:
        # ── Session cookie ─────────────────────────────────────────────────
        st.markdown("**Chartink Session Cookie**")
        st.caption(
            "Open chartink.com → F12 → Application → Cookies → chartink.com "
            "→ copy the value of `_chartink_session`."
        )
        ck_cookie = st.text_input(
            "_chartink_session",
            value=st.session_state.get("ck_cookie", ""),
            type="password",
            key="ck_cookie_input",
            placeholder="paste cookie value here",
        )
        if ck_cookie:
            st.session_state["ck_cookie"] = ck_cookie

        st.divider()

        # ── Scanner selector ───────────────────────────────────────────────
        st.markdown("**Breakout Timeframe**")
        for bk_name in _CK_SCANNERS:
            lbl = f"{bk_name}  ({_CK_SCANNERS[bk_name]['lookback']})"
            if st.button(lbl, key=f"ck_sel_{bk_name}", use_container_width=True):
                st.session_state["ck_scanner"] = bk_name
                st.session_state.pop("ck_results", None)

        selected_ck = st.session_state.get("ck_scanner", "1Y All-Time Breakout")
        st.divider()
        color_ck = _CK_SCANNERS[selected_ck]["color"]
        st.markdown(
            f"**Selected:** <span style='color:{color_ck}'>{selected_ck}</span>",
            unsafe_allow_html=True,
        )
        full_clause = ck.SCAN_CLAUSES.get(selected_ck, "")
        st.caption(full_clause[:180] + ("…" if len(full_clause) > 180 else ""))

        # ── Copy scan clause to clipboard ──────────────────────────────────
        if full_clause:
            # Use a JS snippet injected via st.components to copy to clipboard
            import streamlit.components.v1 as _components
            safe = full_clause.replace("\\", "\\\\").replace("`", "\\`")
            _components.html(
                f"""
                <button onclick="navigator.clipboard.writeText(`{safe}`)
                  .then(()=>this.textContent='✓ Copied!')
                  .catch(()=>this.textContent='⚠ Failed')"
                  style="background:#238636;color:#fff;border:none;border-radius:5px;
                         padding:5px 12px;cursor:pointer;font-size:12px;width:100%">
                  📋 Copy Scan Clause
                </button>
                """,
                height=38,
            )

        st.divider()

        # ── Custom clause ──────────────────────────────────────────────────
        with st.expander("Custom scan clause (advanced)"):
            custom_clause = st.text_area(
                "Paste any Chartink scan clause",
                height=120,
                key="ck_custom_clause",
                placeholder="( {cash} ( daily close > ... ) )",
            )

        # ── Run buttons ────────────────────────────────────────────────────
        if st.button("▶ Run Selected Scan", type="primary", key="ck_run"):
            cookie = st.session_state.get("ck_cookie", "").strip()
            if not cookie:
                st.error("Paste your `_chartink_session` cookie first.")
            else:
                clause = custom_clause.strip() if custom_clause.strip() else None
                with st.spinner(f"Querying Chartink — {selected_ck}…"):
                    try:
                        if clause:
                            rows = ck.run_chartink_scan(clause, cookie)
                            ran_name = "Custom Clause"
                        else:
                            rows = ck.run_named_scan(selected_ck, cookie)
                            ran_name = selected_ck
                        st.session_state["ck_results"]     = rows
                        st.session_state["ck_scanner_ran"] = ran_name
                        st.session_state.pop("ck_all_results", None)
                    except Exception as exc:
                        st.error(f"Chartink fetch failed: {exc}")

        if st.button("▶ Run All 5 Timeframes", key="ck_run_all", type="primary"):
            cookie = st.session_state.get("ck_cookie", "").strip()
            if not cookie:
                st.error("Paste your `_chartink_session` cookie first.")
            else:
                all_ck: dict[str, list] = {}
                failed = []
                for bk_n in _CK_SCANNERS:
                    with st.spinner(f"Scanning {bk_n}…"):
                        try:
                            all_ck[bk_n] = ck.run_named_scan(bk_n, cookie)
                        except Exception as exc:
                            all_ck[bk_n] = []
                            failed.append(f"{bk_n}: {exc}")
                st.session_state["ck_all_results"] = all_ck
                st.session_state.pop("ck_results", None)
                if failed:
                    st.warning("Some scans failed:\n" + "\n".join(failed))

    # ── Right panel — results ──────────────────────────────────────────────────
    with bk_main:

        _CHART_SERVER = "http://localhost:5001"

        def _render_ck_table(rows: list[dict], scan_label: str, color: str) -> None:
            """Render Chartink result rows with chart-launch links + CSV export."""
            if not rows:
                st.info(f"No stocks matched **{scan_label}**.")
                return

            df_res = pd.DataFrame(rows)

            # Normalise Chartink column names.
            # Chartink returns "price" for LTP (not "close"), and sometimes
            # both exist — prefer "price" if present.
            col_map = {
                "nsecode":         "Symbol",
                "bsecode":         "BSE Code",
                "per_chg":         "% Chg",
                "close":           "Price",   # fallback if price absent
                "price":           "Price",   # Chartink primary field
                "volume":          "Volume",
                "series":          "Series",
                "market_cap_full": "Mkt Cap (Cr)",
            }
            df_res = df_res.rename(columns={k: v for k, v in col_map.items() if k in df_res.columns})
            # Drop duplicate Price column that can appear when both close+price exist
            df_res = df_res.loc[:, ~df_res.columns.duplicated()]

            # Coerce numerics
            for num_col in ["Price", "% Chg", "Volume", "Mkt Cap (Cr)"]:
                if num_col in df_res.columns:
                    df_res[num_col] = pd.to_numeric(df_res[num_col], errors="coerce")

            # Build chart URL: NSE code + ".NS" suffix → opens chart dashboard
            if "Symbol" in df_res.columns:
                df_res["Chart"] = df_res["Symbol"].apply(
                    lambda s: f"{_CHART_SERVER}/?symbol={s}.NS&tf=1d"
                )
                df_res["Analyze"] = df_res["Symbol"].map(_analyze_url)

            df_res = df_res.sort_values("% Chg", ascending=False).reset_index(drop=True)

            # Column order — Chart + Analyze links first so they're always visible
            keep = [c for c in ["Chart", "Analyze", "Symbol", "Price", "% Chg",
                                 "Volume", "Mkt Cap (Cr)", "BSE Code", "Series"]
                    if c in df_res.columns]

            st.markdown(
                f"<span style='color:{color};font-weight:700;font-size:15px;'>"
                f"▶ {scan_label} — {len(rows)} stocks</span>",
                unsafe_allow_html=True,
            )
            st.caption("Click **Chart** to open the live chart dashboard in a new tab.")

            col_cfg = {}
            if "Chart" in df_res.columns:
                col_cfg["Chart"] = st.column_config.LinkColumn(
                    "Chart",
                    display_text="Open Chart",   # plain text — emoji causes pencil icon bug
                    help="Opens Trading Bramha live chart for this stock (chart server must be running on :5001)",
                    width="small",
                )
            if "Analyze" in df_res.columns:
                col_cfg["Analyze"] = _analyze_colcfg()
            if "% Chg" in df_res.columns:
                col_cfg["% Chg"] = st.column_config.NumberColumn(
                    "% Chg", format="%.2f%%"
                )
            if "Price" in df_res.columns:
                col_cfg["Price"] = st.column_config.NumberColumn(
                    "Price", format="%.2f"
                )
            if "Volume" in df_res.columns:
                col_cfg["Volume"] = st.column_config.NumberColumn(
                    "Volume", format="%d"
                )

            st.dataframe(
                df_res[keep],
                use_container_width=True,
                hide_index=True,
                column_config=col_cfg,
            )

            csv = df_res[[c for c in keep if c not in ("Chart", "Analyze")]].to_csv(index=False).encode()
            st.download_button(
                f"⬇ Download {scan_label} CSV",
                data=csv,
                file_name=f"chartink_{scan_label.replace(' ', '_')}.csv",
                mime="text/csv",
                key=f"ck_dl_{scan_label}",
            )

        # Combined "Run All" view
        if "ck_all_results" in st.session_state and "ck_results" not in st.session_state:
            all_res: dict = st.session_state["ck_all_results"]
            total = sum(len(v) for v in all_res.values())
            st.markdown(f"### All Timeframes — **{total}** hits")
            for bk_n, rows in all_res.items():
                _render_ck_table(rows, bk_n, _CK_SCANNERS[bk_n]["color"])
                st.divider()

        # Single scan view
        elif "ck_results" in st.session_state:
            rows    = st.session_state["ck_results"]
            ran     = st.session_state.get("ck_scanner_ran", selected_ck)
            color_r = _CK_SCANNERS.get(ran, {}).get("color", "#58a6ff")
            _render_ck_table(rows, ran, color_r)

        else:
            st.info(
                "1. Paste your `_chartink_session` cookie on the left.\n"
                "2. Pick a breakout timeframe.\n"
                "3. Click **Run Selected Scan** — results scan the **entire NSE cash market** via Chartink."
            )

    st.divider()

    # ── Pre-Breakout Screener (conviction score + pledge/cash-flow gate) ────────
    st.subheader("Pre-Breakout Screener — Conviction ≥ 60%, Pledge & Cash-Flow Safe")
    st.caption(
        "Chartink finds stocks coiled just under a 20-day high — 1-2 sessions from a "
        "possible breakout — then each candidate is scored 0-100 (proximity to the "
        "trigger, volatility contraction, RSI, trend/volume) using its own OHLCV. "
        "Only score ≥ 60 survives. Chartink has no pledge% or cash-flow fields, so "
        "that red-flag check runs separately against screener.in (optional below)."
    )

    pb_left, pb_main = st.columns([1, 3])

    with pb_left:
        st.markdown("**screener.in Session (optional)**")
        pb_screener_cookie, pb_browser = bch.get_screener_sessionid()
        if pb_screener_cookie:
            st.session_state["pb_screener_cookie"] = pb_screener_cookie
            st.caption(
                f"✅ Using screener.in session from local browser ({pb_browser}) — "
                "auto-drops stocks with promoter pledge ≥ 5% or negative operating cash flow."
            )
        else:
            pb_screener_cookie = ""
            st.caption(
                "⚠️ No screener.in `sessionid` cookie in your local browsers. Log into "
                "screener.in in your default browser to auto-drop pledged / negative-cash-flow "
                "stocks; otherwise results show a manual check-link instead."
            )

        st.divider()
        pb_min_conviction = st.slider(
            "Minimum conviction %", min_value=0, max_value=100, value=60, step=5,
            key="pb_min_conviction",
            help="Lower this to see more (weaker) candidates while testing.",
        )
        pb_max_pledge = st.slider(
            "Max pledge %", min_value=0.0, max_value=25.0, value=5.0, step=0.5,
            key="pb_max_pledge",
            help="Only used if a screener.in cookie is pasted above.",
        )

        st.divider()
        if st.button("▶ Run Pre-Breakout Scan", type="primary", key="pb_run"):
            cookie = st.session_state.get("ck_cookie", "").strip()
            if not cookie:
                st.error("Paste your `_chartink_session` cookie above first.")
            else:
                with st.spinner("Querying Chartink for pre-breakout candidates…"):
                    try:
                        candidates = ck.run_named_scan("Pre-Breakout Setup (1-2 Day)", cookie)
                    except Exception as exc:
                        candidates = None
                        st.error(f"Chartink fetch failed: {exc}")

                if candidates is not None:
                    safe_symbols = None
                    if pb_screener_cookie.strip():
                        with st.spinner("Checking pledge % / cash flow on screener.in…"):
                            try:
                                safe_symbols = cached_fetch_safe_symbols(
                                    pb_screener_cookie.strip(), max_pledge_pct=pb_max_pledge,
                                )
                            except Exception as exc:
                                st.warning(f"screener.in fundamental check failed: {exc}")

                    funnel = {"chartink": len(candidates), "conviction": 0, "fundamentals": 0}
                    scored = []
                    with st.spinner(f"Scoring conviction on {len(candidates)} candidates…"):
                        for row in candidates:
                            sym = row.get("nsecode", "").strip().upper()
                            if not sym:
                                continue
                            try:
                                df_pb = cached_fetch_ohlcv(f"{sym}.NS", days=90)
                            except Exception:
                                continue
                            if df_pb is None or df_pb.empty:
                                continue
                            hit = sc.compute_pre_breakout_conviction(df_pb)
                            if hit is None or hit["conviction"] < pb_min_conviction:
                                continue
                            funnel["conviction"] += 1
                            if safe_symbols is not None:
                                hit["fundamentals_safe"] = sym in safe_symbols
                                if not hit["fundamentals_safe"]:
                                    continue
                                funnel["fundamentals"] += 1
                            else:
                                hit["fundamentals_safe"] = None
                            hit["symbol"] = sym
                            hit["price"] = row.get("price") or row.get("close")
                            hit["pct_chg"] = row.get("per_chg")
                            scored.append(hit)

                    st.session_state["pb_results"] = sorted(
                        scored, key=lambda h: h["conviction"], reverse=True
                    )
                    st.session_state["pb_funnel"] = funnel

        pb_funnel = st.session_state.get("pb_funnel")
        if pb_funnel:
            funnel_line = (
                f"Chartink: **{pb_funnel['chartink']}** → "
                f"conviction ≥{pb_min_conviction}%: **{pb_funnel['conviction']}**"
            )
            if pb_funnel["fundamentals"] or pb_screener_cookie.strip():
                funnel_line += f" → pledge/cash-flow safe: **{pb_funnel['fundamentals']}**"
            st.caption(funnel_line)

        st.divider()
        st.caption(
            "screener.in field names confirmed via its public "
            "`/api/ratio/search/` endpoint: **Pledged percentage** and "
            "**Cash from operations last year**."
        )

    with pb_main:
        pb_results = st.session_state.get("pb_results")
        if pb_results is None:
            st.info(
                "Uses the `_chartink_session` cookie from the left panel above. "
                "Click **Run Pre-Breakout Scan** to look for stocks 1-2 sessions "
                "from a breakout."
            )
        elif not pb_results:
            st.info(
                "No candidates cleared both the Chartink pre-breakout filter and "
                "the ≥60% conviction score right now."
            )
        else:
            df_pb_res = pd.DataFrame(pb_results)
            df_pb_res["Chart"] = df_pb_res["symbol"].apply(
                lambda s: f"{_CHART_SERVER}/?symbol={s}.NS&tf=1d"
            )
            df_pb_res["Analyze"] = df_pb_res["symbol"].map(_analyze_url)
            if df_pb_res["fundamentals_safe"].isna().all():
                df_pb_res["Pledge/CF Check"] = df_pb_res["symbol"].apply(
                    lambda s: f"https://www.screener.in/company/{s}/consolidated/#shareholding"
                )
                pledge_note = "manual — paste a screener.in cookie to automate"
            else:
                # Only rows that already passed the pledge/cash-flow gate reach
                # here (flagged candidates were dropped when the list was built).
                df_pb_res["Pledge/CF Check"] = "✅ Verified Safe"
                pledge_note = "auto-verified via screener.in"

            df_pb_res = df_pb_res.rename(columns={
                "symbol": "Symbol", "price": "Price", "pct_chg": "% Chg",
                "conviction": "Conviction %", "distance_pct": "Dist to Trigger %",
                "rsi": "RSI",
            })
            for c in ["Price", "% Chg", "Conviction %", "Dist to Trigger %", "RSI"]:
                df_pb_res[c] = pd.to_numeric(df_pb_res[c], errors="coerce")

            st.caption(f"{len(df_pb_res)} candidates · pledge/cash-flow check: {pledge_note}")

            col_cfg_pb = {
                "Chart": st.column_config.LinkColumn(
                    "Chart", display_text="Open Chart", width="small",
                ),
                "Analyze": _analyze_colcfg(),
                "Conviction %": st.column_config.ProgressColumn(
                    "Conviction %", min_value=0, max_value=100, format="%.0f%%",
                ),
                "% Chg": st.column_config.NumberColumn("% Chg", format="%.2f%%"),
                "Price": st.column_config.NumberColumn("Price", format="%.2f"),
            }
            if pledge_note.startswith("manual"):
                col_cfg_pb["Pledge/CF Check"] = st.column_config.LinkColumn(
                    "Pledge/CF Check", display_text="Verify", width="small",
                )

            keep_pb = ["Chart", "Analyze", "Symbol", "Price", "% Chg", "Conviction %",
                       "Dist to Trigger %", "RSI", "Pledge/CF Check"]
            st.dataframe(
                df_pb_res[[c for c in keep_pb if c in df_pb_res.columns]],
                use_container_width=True, hide_index=True, column_config=col_cfg_pb,
            )


# ──────────────────────────────────────────────────────────────────────────────
# Page — TradingView Screener (BrkoutGeek: Horz Break replica via public scan API)
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "TradingView Screener":
    st.subheader("TradingView Screener — BrkoutGeek: Horz Break (replica)")
    st.caption(
        "Replicates saved screener uPUJdiD5 via TradingView's public scan endpoint — "
        "no login. NSE-only, breaks 1-month high, filtered by Chg %, Rel Vol, and "
        "traded turnover. Adjust thresholds below and click Refresh."
    )

    try:
        import tv_screener as tvs
    except ImportError as exc:
        st.error(f"tv_screener import failed: {exc}")
        st.stop()

    tv_c1, tv_c2, tv_c3 = st.columns(3)
    tv_min_chg = tv_c1.number_input("Min Chg %", 0.0, 20.0, 2.0, step=0.5, key="tv_min_chg")
    tv_min_rv  = tv_c2.number_input("Min Rel Vol", 0.5, 20.0, 1.5, step=0.1, key="tv_min_rv")
    tv_min_tv  = tv_c3.number_input("Min Turnover ₹ (Cr)", 0.0, 500.0, 1.0, step=0.5,
                                    key="tv_min_tv", help="Traded turnover today")

    if st.button("🔄 Refresh TradingView scan", type="primary", key="tv_refresh"):
        with st.spinner("Fetching TradingView scan…"):
            df_tv = tvs.fetch_brkoutgeek(
                min_chg=tv_min_chg,
                min_rel_vol=tv_min_rv,
                min_price_vol_inr=tv_min_tv * 1e7,   # Cr → INR
            )
            st.session_state["tv_scan_df"] = df_tv

    df_tv = st.session_state.get("tv_scan_df")
    if df_tv is None:
        st.info("Click **Refresh** to run the scan.")
    elif df_tv.empty:
        st.warning("No hits at these thresholds.")
    else:
        # Excel-style filter (same UX as Bulk Deals)
        q = st.text_input(
            "Filter symbol / company / industry (comma-separated, substring match)",
            key="tv_filter",
            placeholder="e.g. BANK, PHARMA, RELIANCE",
        ).strip()
        view = df_tv.copy()
        if q:
            terms = [t.strip().upper() for t in q.split(",") if t.strip()]
            hay_cols = [c for c in ["Symbol", "Company", "Industry", "Sector"]
                        if c in view.columns]
            hay = view[hay_cols].astype(str).agg(" | ".join, axis=1).str.upper()
            mask = pd.Series(False, index=view.index)
            for t in terms:
                mask |= hay.str.contains(t, na=False, regex=False)
            view = view[mask]

        st.caption(f"{len(view)} hit(s)")
        if "Symbol" in view.columns:
            view = _with_analyze_col(view, "Symbol", after="Chart")
        tv_cfg = {}
        if "Chart" in view.columns:
            tv_cfg["Chart"] = st.column_config.LinkColumn("Chart", display_text="📈 Open", width="small")
        if "Analyze" in view.columns:
            tv_cfg["Analyze"] = _analyze_colcfg()
        if "Turnover ₹" in view.columns:
            tv_cfg["Turnover ₹"] = st.column_config.NumberColumn("Turnover ₹", format="%.0f")
        if "Mkt Cap ₹" in view.columns:
            tv_cfg["Mkt Cap ₹"] = st.column_config.NumberColumn("Mkt Cap ₹", format="%.0f")
        st.dataframe(view, use_container_width=True, hide_index=True, column_config=tv_cfg)


# ──────────────────────────────────────────────────────────────────────────────
# Page — High-Growth Screener (screener.in fundamentals + IBD-style RS rank +
# %R Trend Exhaustion signal)
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "High-Growth Screener":
    st.subheader("High-Growth Screener — Sustained Growth + Quality Gates")
    st.caption(
        "Pure fundamental screen against screener.in — sustained 5-year sales/profit growth "
        "gated by ROE/ROCE/OPM quality plus a YoY quarterly-profit acceleration kicker "
        "(screener.in has no analyst-consensus 'profit surprise' field; YoY qtr profit growth "
        "is the closest real proxy). No technical filters, no RS/exhaustion/validation "
        "columns — those live on the Scanner Hub cards; this page is fundamental-only."
    )

    hg_left, hg_main = st.columns([1, 3])

    with hg_left:
        st.markdown("**screener.in Session**")
        hg_cookie, hg_browser = bch.get_screener_sessionid()
        if hg_cookie:
            st.session_state["pb_screener_cookie"] = hg_cookie
            st.caption(f"✅ Using screener.in session from local browser ({hg_browser}).")
        else:
            st.caption(
                "⚠️ No screener.in `sessionid` cookie found in your local browsers. "
                "Log into screener.in in your default browser once, then re-run."
            )

        st.divider()
        st.markdown("**Growth & Quality Thresholds**")
        hg_sales5y = st.slider("Min 5Y Sales Growth %", 0, 50, 15, step=1, key="hg_sales5y")
        hg_profit5y = st.slider("Min 5Y Profit Growth %", 0, 80, 15, step=1, key="hg_profit5y")
        hg_yoyq = st.slider("Min YoY Qtr Profit Growth % (surprise proxy)", -20, 100, 15,
                             step=5, key="hg_yoyq")
        hg_roe = st.slider("Min ROE %", 0, 40, 15, step=1, key="hg_roe")
        hg_roce = st.slider("Min ROCE %", 0, 40, 15, step=1, key="hg_roce")
        hg_opm = st.slider("Min OPM %", 0, 50, 10, step=1, key="hg_opm")

        st.divider()
        if st.button("▶ Run High-Growth Screen", type="primary", key="hg_run"):
            cookie = (hg_cookie or "").strip() or st.session_state.get("pb_screener_cookie", "").strip()
            if not cookie:
                st.error("No screener.in `sessionid` cookie found — log into screener.in "
                         "in your default browser, then re-run.")
            else:
                with st.spinner("Querying screener.in…"):
                    try:
                        hg_df = ss.fetch_high_growth_stocks(
                            cookie, min_sales_growth_5y=hg_sales5y, min_profit_growth_5y=hg_profit5y,
                            min_yoy_qtr_profit_growth=hg_yoyq, min_roe=hg_roe, min_roce=hg_roce,
                            min_opm=hg_opm,
                        )
                    except Exception as exc:
                        hg_df = None
                        st.error(f"screener.in fetch failed: {exc}")

                if hg_df is not None:
                    if hg_df.empty:
                        st.session_state["hg_results"] = []
                    else:
                        # Pure fundamental screen — no technical enrichment. Every
                        # column here comes straight from the screener.in query
                        # response; no yfinance fetch, no RS/%R/validation compute.
                        results = []
                        for _, row in hg_df.iterrows():
                            sym = str(row.get("_slug") or row.get("Name", "")).strip().upper()
                            if not sym:
                                continue
                            rec = {"symbol": sym}
                            for col in hg_df.columns:
                                if col not in ("Name", "_slug"):
                                    rec[col] = row.get(col)
                            results.append(rec)

                        # Sort by 5Y profit growth (falls back to sales growth,
                        # then YoY qtr) — pure fundamental ranking now that RS
                        # Rank is gone.
                        def _sort_key(r):
                            for col in ("Profit growth 5Years", "Sales growth 5Years",
                                        "YOY Quarterly profit growth"):
                                v = pd.to_numeric(r.get(col), errors="coerce")
                                if pd.notna(v):
                                    return -float(v)
                            return 0.0
                        st.session_state["hg_results"] = sorted(results, key=_sort_key)

    with hg_main:
        hg_results = st.session_state.get("hg_results")
        if hg_results is None:
            st.info(
                "Adjust thresholds and click **Run High-Growth Screen**. The screener.in "
                "session is read automatically from your local browser — just stay logged "
                "into screener.in there."
            )
        elif not hg_results:
            st.info(
                "screener.in returned 0 rows for these thresholds. With nominal "
                "settings that usually means the sessionid cookie has expired "
                "(re-paste it and rerun) rather than genuinely no matches — an "
                "expired cookie now raises an error instead, so if you're seeing "
                "this after a clean run, the thresholds really matched nothing."
            )
        else:
            df_hg_res = pd.DataFrame(hg_results)
            df_hg_res["Chart"] = df_hg_res["symbol"].apply(
                lambda s: f"http://localhost:5001/?symbol={s}.NS&tf=1d"
            )
            df_hg_res["Analyze"] = df_hg_res["symbol"].map(_analyze_url)

            rename_map = {
                "symbol": "Symbol",
                "Current Price": "Price",
                "Sales growth 5Years": "Sales Gr 5Y %",
                "Profit growth 5Years": "Profit Gr 5Y %",
                "YOY Quarterly profit growth": "YoY Qtr Profit %",
                "Return on equity": "ROE %",
                "Return on capital employed": "ROCE %",
                "OPM": "OPM %",
            }
            df_hg_res = df_hg_res.rename(
                columns={k: v for k, v in rename_map.items() if k in df_hg_res.columns}
            )

            keep_hg = ["Chart", "Analyze", "Symbol", "Price", "Sales Gr 5Y %", "Profit Gr 5Y %",
                       "YoY Qtr Profit %", "ROE %", "ROCE %", "OPM %"]
            keep_hg = [c for c in keep_hg if c in df_hg_res.columns]

            st.caption(
                f"{len(df_hg_res)} stocks passed the growth/quality gate · "
                "sorted by 5Y profit growth"
            )
            col_cfg_hg = {
                "Chart": st.column_config.LinkColumn(
                    "Chart", display_text="Open Chart", width="small",
                ),
                "Analyze": _analyze_colcfg(),
            }
            st.dataframe(
                df_hg_res[keep_hg], use_container_width=True, hide_index=True,
                column_config=col_cfg_hg,
            )
            st.caption(
                "Columns showing blank came back missing from screener.in's response for that "
                "field (its raw-query columns can vary); re-check that stock on screener.in directly."
            )


# ──────────────────────────────────────────────────────────────────────────────
# Page — Market Sentiment (Phase 1: 4-input composite gauge)
# Backed by tools/sentiment_index.py. Composite 0-100 score → Strong Sell / Sell
# / Neutral / Buy / Strong Buy band. Inputs: Advance-Decline (bhavcopy),
# Sector Performance (yfinance sector indices), NIFTY vs SMA200 regime, PMax
# direction on NIFTY 1H. See wiki: concepts/Market-Sentiment-Index.md and
# analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14.md for the design.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Market Sentiment":
    st.subheader("Market Sentiment Index")
    st.caption(
        "0-100 composite regime gauge for NIFTY. Phase 1 uses four home-data "
        "inputs — Advance/Decline, Sector Performance, NIFTY vs SMA200, and "
        "PMax direction on NIFTY 1H. Phase 2 adds PCR when the option-chain "
        "scraper lands."
    )

    col_run, col_peek = st.columns([1, 3])
    with col_run:
        run_now = st.button("Refresh Sentiment", type="primary", key="senti_run")

    reading = None
    if run_now:
        with st.spinner("Computing sentiment…"):
            try:
                reading = senti.compute_sentiment(persist=True)
            except Exception as e:
                st.error(f"Sentiment compute failed: {e}")
    else:
        # Show today's persisted reading if it exists, otherwise the newest row.
        try:
            hist = senti.history(days=1)
            if not hist.empty:
                row = hist.iloc[-1]
                reading = {
                    "reading_date": row["reading_date"].date().isoformat(),
                    "score": float(row["score"]),
                    "band":  row["band"],
                    "inputs": json.loads(row["inputs_json"]),
                }
        except Exception:
            reading = None

    if reading is None:
        st.info("No sentiment reading yet — click **Refresh Sentiment**.")
    else:
        # Band → colour used for the gauge + summary chip.
        band_colors = {
            "Strong Sell": "#b71c1c", "Sell": "#e53935", "Neutral": "#9e9e9e",
            "Buy": "#1e88e5",         "Strong Buy": "#0d47a1",
        }
        band_color = band_colors.get(reading["band"], "#9e9e9e")

        gauge_col, chip_col = st.columns([3, 2])
        with gauge_col:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=reading["score"],
                number={"suffix": " / 100", "font": {"size": 34}},
                gauge={
                    "axis":  {"range": [0, 100], "tickwidth": 1, "tickcolor": "#888"},
                    "bar":   {"color": band_color, "thickness": 0.25},
                    "steps": [
                        {"range": [0, 20],  "color": "#b71c1c"},
                        {"range": [20, 40], "color": "#e53935"},
                        {"range": [40, 55], "color": "#9e9e9e"},
                        {"range": [55, 80], "color": "#1e88e5"},
                        {"range": [80, 100], "color": "#0d47a1"},
                    ],
                    "threshold": {"line": {"color": "white", "width": 4},
                                   "thickness": 0.75,
                                   "value": reading["score"]},
                },
                domain={"x": [0, 1], "y": [0, 1]},
            ))
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=20, b=20),
                              paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with chip_col:
            st.markdown(
                f"""
                <div style="padding:16px;border-radius:12px;background:{band_color}22;
                            border:1px solid {band_color}55;text-align:center;">
                  <div style="font-size:12px;color:#666;">READING · {reading['reading_date']}</div>
                  <div style="font-size:32px;font-weight:800;color:{band_color};margin-top:6px;">
                    {reading['band']}
                  </div>
                  <div style="font-size:14px;color:#555;margin-top:4px;">
                    Score {reading['score']:.1f} / 100
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Breakdown table ───────────────────────────────────────────────────
        st.markdown("#### Sentiment Breakdown")
        rows = []
        for key, label in [
            ("advance_decline",     "Advance / Decline (bhavcopy)"),
            ("sector_performance",  "Sector Performance (NIFTY indices)"),
            ("regime_sma200",       "NIFTY vs SMA200 (regime)"),
            ("pmax_nifty_1h",       "PMax direction — NIFTY 1H"),
        ]:
            inp = reading["inputs"].get(key, {})
            weight = inp.get("weight", 0)
            score  = inp.get("score", 0)
            rows.append({
                "Indicator": label,
                "Reading": inp.get("reading", "n/a"),
                "Weight": weight,
                "Score": round(float(score), 1),
                # Streamlit's ProgressColumn format string is a plain Python
                # printf template that receives the raw cell value — so `%.0f%%`
                # on 0.24 prints "0%". Convert to 0-100 space here.
                "Fill %": (float(score) / weight * 100.0) if weight else 0.0,
            })
        rows.append({
            "Indicator": "TOTAL", "Reading": "",
            "Weight": senti.W_TOTAL, "Score": reading["score"],
            "Fill %": (reading["score"] / senti.W_TOTAL * 100.0),
        })
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True, use_container_width=True,
            column_config={
                "Fill %": st.column_config.ProgressColumn(
                    "Fill", format="%.0f%%", min_value=0.0, max_value=100.0,
                ),
            },
        )

        # ── Sector detail expander ────────────────────────────────────────────
        sector_inp = reading["inputs"].get("sector_performance", {})
        sector_details = sector_inp.get("details") or []
        if sector_details:
            with st.expander(f"Sector detail — {sector_inp.get('reading', '')}"):
                sec_df = pd.DataFrame(sector_details)
                # Chart column: sector index tickers (^CNXIT, ^NSEBANK, .NS…)
                # pass through unchanged.
                sec_df.insert(1, "chart", sec_df["ticker"].map(
                    lambda t: f"http://localhost:5001/?symbol={t}&tf=1d" if t else None
                ))
                st.dataframe(
                    sec_df,
                    hide_index=True, use_container_width=True,
                    column_config={
                        "chart": st.column_config.LinkColumn(
                            "Chart", help="Open in Chart Tool",
                            display_text="Open ↗", width="small",
                        ),
                    },
                )

        # ── History chart ─────────────────────────────────────────────────────
        try:
            hist_df = senti.history(days=90)
        except Exception:
            hist_df = pd.DataFrame()
        if len(hist_df) >= 2:
            st.markdown("#### History (last 90 days)")
            fig_h = go.Figure()
            fig_h.add_trace(go.Scatter(
                x=hist_df["reading_date"], y=hist_df["score"],
                mode="lines+markers", line=dict(color="#ea580c", width=2),
                marker=dict(size=6),
            ))
            # Band shading
            for lo, hi, _label in senti.BANDS:
                fig_h.add_hrect(y0=lo, y1=hi if hi <= 100 else 100,
                                fillcolor=band_colors.get(_label, "#9e9e9e"),
                                opacity=0.08, line_width=0)
            fig_h.update_layout(
                height=280, margin=dict(l=20, r=20, t=20, b=20),
                yaxis=dict(range=[0, 100], title="Score"),
                xaxis=dict(title=""),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_h, use_container_width=True)

    # ── Global Context — Finviz (US market snapshot) ──────────────────────────
    st.markdown("---")
    st.markdown("### Global Context — US Market (Finviz)")
    st.caption(
        "Scraped live from finviz.com — US breadth and signal tables. Adds "
        "risk-on/risk-off context to complement the NIFTY reading above."
    )
    if st.button("🔄 Refresh Finviz snapshot", key="finviz_refresh"):
        try:
            import finviz_sentiment as fvz
            with st.spinner("Fetching finviz data…"):
                st.session_state["fvz_indices"] = fvz.fetch_index_snapshot()
                st.session_state["fvz_breadth"] = fvz.fetch_breadth()
        except Exception as e:
            st.error(f"Finviz fetch failed: {e}")

    fvz_idx = st.session_state.get("fvz_indices")
    fvz_br  = st.session_state.get("fvz_breadth", {})

    if fvz_idx is not None and not fvz_idx.empty:
        # 4 index chips
        idx_cols = st.columns(4)
        for i, (_, r) in enumerate(fvz_idx.iterrows()):
            pct = r.get("chg_pct")
            color = "#22c55e" if (pct or 0) > 0 else ("#ef4444" if (pct or 0) < 0 else "#888")
            pct_str = f"{pct:+.2f}%" if pct is not None else "n/a"
            last_str = f"{r['last']:,.2f}" if r.get("last") else ""
            idx_cols[i].markdown(
                f"""<div style="padding:10px;border-radius:8px;background:{color}22;
                              border:1px solid {color}55;text-align:center;">
                  <div style="font-size:11px;color:#666;">{r['index']}</div>
                  <div style="font-size:18px;font-weight:700;">{last_str}</div>
                  <div style="font-size:14px;color:{color};font-weight:600;">{pct_str}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    if fvz_br:
        st.markdown("#### Breadth (US market)")
        br_rows = []
        adv = fvz_br.get("advancing", {})
        dec = fvz_br.get("declining", {})
        nh  = fvz_br.get("new_high", {})
        nl  = fvz_br.get("new_low", {})
        if adv or dec:
            br_rows.append({"Metric": "Advancing", "Pct": adv.get("pct"), "Count": adv.get("count")})
            br_rows.append({"Metric": "Declining", "Pct": dec.get("pct"), "Count": dec.get("count")})
        if nh or nl:
            br_rows.append({"Metric": "New High",  "Pct": nh.get("pct"),  "Count": nh.get("count")})
            br_rows.append({"Metric": "New Low",   "Pct": nl.get("pct"),  "Count": nl.get("count")})
        for sma in ["sma50", "sma200"]:
            if f"above_{sma}" in fvz_br:
                br_rows.append({"Metric": f"Above {sma.upper()}",
                                "Pct": fvz_br[f"above_{sma}"], "Count": None})
                br_rows.append({"Metric": f"Below {sma.upper()}",
                                "Pct": fvz_br[f"below_{sma}"], "Count": None})
        if "bull_pct" in fvz_br:
            br_rows.append({"Metric": "BULL signals", "Pct": fvz_br["bull_pct"], "Count": None})
            br_rows.append({"Metric": "BEAR signals", "Pct": fvz_br["bear_pct"], "Count": None})
        if br_rows:
            st.dataframe(pd.DataFrame(br_rows), hide_index=True, use_container_width=True,
                         column_config={
                             "Pct": st.column_config.ProgressColumn(
                                 "Pct", format="%.1f%%", min_value=0, max_value=100),
                         })

    # Signal tables (on-demand)
    with st.expander("US signal tables (Top Gainers / Losers / New Highs / Unusual Vol / Insider Buy)"):
        try:
            import finviz_sentiment as fvz
            sig_choice = st.selectbox(
                "Signal", ["Top Gainers", "Top Losers", "New 52W High",
                           "Unusual Volume", "Insider Buying"], key="fvz_sig_choice",
            )
            if st.button("Load signal table", key="fvz_sig_load"):
                with st.spinner(f"Fetching {sig_choice}…"):
                    df_sig = fvz.fetch_signal_table(sig_choice, limit=25)
                if df_sig.empty:
                    st.info("No rows returned.")
                else:
                    st.dataframe(df_sig, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Signal fetch failed: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Page — India Market Intel (bulk/block deals, insider trading, gap & volume)
# India-only by design — no US SEC EDGAR data, scoped out on request.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "India Market Intel":
    st.subheader("India Market Intel — Bulk/Block Deals, Insider Trading, Gap & Volume")
    st.caption(
        "NSE + BSE bulk/block deals and BSE insider trading (SEBI PIT disclosures), both "
        "confirmed working via reverse-engineered public APIs — no login needed. Rows marked "
        "**NEW** appeared since the last time you refreshed this page (these feeds have no "
        "history endpoint, so this isn't a true day-over-day diff — just 'new since last check'). "
        "Corporate announcements aren't wired up yet — the whole-market feed is very high volume "
        "without a watchlist filter to scope it to."
    )

    intel_tabs = st.tabs(["Bulk Deals", "Block Deals", "Insider Trading", "Gap & Volume Scanner"])

    def _highlight_deals(df_deals: pd.DataFrame, min_value_lakh: float, buy_col: str,
                         filter_key: str = "imi_deal_filter") -> None:
        if df_deals.empty:
            st.info("No deals returned.")
            return
        df_deals = df_deals.copy()
        # Excel-style scrip filter: comma-separated substrings, case-insensitive,
        # matches across ScripName / Symbol / Security Name / CLIENT_NAME / Client Name.
        query = st.text_input(
            "Filter scrip / client (comma-separated, substring match)",
            key=filter_key, placeholder="e.g. RELIANCE, HDFC, MUTUAL FUND",
        ).strip()
        if query:
            terms = [t.strip().upper() for t in query.split(",") if t.strip()]
            search_cols = [c for c in ["ScripName", "Symbol", "Security Name",
                                       "CLIENT_NAME", "Client Name"] if c in df_deals.columns]
            if search_cols and terms:
                haystack = df_deals[search_cols].astype(str).agg(" | ".join, axis=1).str.upper()
                mask = pd.Series(False, index=df_deals.index)
                for t in terms:
                    mask |= haystack.str.contains(t, na=False, regex=False)
                df_deals = df_deals[mask]
                if df_deals.empty:
                    st.info(f"No rows match: {query}")
                    return
        df_deals["Value (₹L)"] = (df_deals["QUANTITY"] * df_deals["PRICE"] / 1e5).round(1) \
            if "QUANTITY" in df_deals.columns and "PRICE" in df_deals.columns else float("nan")
        if "Quantity Traded" in df_deals.columns:
            price_col = next((c for c in df_deals.columns if "Price" in c), None)
            if price_col:
                df_deals["Value (₹L)"] = (
                    pd.to_numeric(df_deals["Quantity Traded"], errors="coerce")
                    * pd.to_numeric(df_deals[price_col], errors="coerce") / 1e5
                ).round(1)
        sym_col = next((c for c in ["Symbol", "ScripName"] if c in df_deals.columns), None)
        if sym_col:
            is_nse = "Exchange" in df_deals.columns and str(df_deals["Exchange"].iloc[0]).upper() == "NSE"
            exch = "NSE" if is_nse else "BSE"
            df_deals["Chart"] = df_deals[sym_col].apply(
                lambda s: f"http://localhost:5001/?symbol={str(s).strip()}&exchange={exch}&tf=1d"
            )
            if is_nse:   # analyzer is yfinance/.NS-based — only NSE tickers resolve
                df_deals["Analyze"] = df_deals[sym_col].map(_analyze_url)
        df_deals = df_deals.sort_values("Value (₹L)", ascending=False, na_position="last")
        big = df_deals[df_deals["Value (₹L)"] >= min_value_lakh] if "Value (₹L)" in df_deals.columns else pd.DataFrame()
        if not big.empty:
            st.markdown(f"**{len(big)} deal(s) above ₹{min_value_lakh:.0f}L:**")

        def _row_color(row):
            val = str(row.get(buy_col, "")).strip().upper()
            if val in ("B", "BUY"):
                return ["background-color: rgba(63,185,80,0.15)"] * len(row)
            if val in ("S", "SELL"):
                return ["background-color: rgba(248,81,73,0.15)"] * len(row)
            return [""] * len(row)

        col_config = {}
        if "Chart" in df_deals.columns:
            col_config["Chart"] = st.column_config.LinkColumn("Chart", display_text="📈 Open", width="small")
        if "Analyze" in df_deals.columns:
            col_config["Analyze"] = _analyze_colcfg()
        st.dataframe(df_deals.style.apply(_row_color, axis=1), use_container_width=True, hide_index=True,
                     column_config=col_config)

    with intel_tabs[0]:
        min_val_bulk = st.slider("Highlight bulk deals above (₹ Lakh)", 5, 500, 50, step=5, key="imi_bulk_min")
        if st.button("🔄 Refresh Bulk Deals", key="imi_bulk_refresh"):
            with st.spinner("Fetching BSE + NSE bulk deals…"):
                try:
                    bse_bulk = imi.fetch_bse_bulk_deals()
                    bse_bulk = imi.mark_new_rows(
                        bse_bulk, "bse_bulk", ["DEAL_DATE", "SCRIP_CODE", "CLIENT_NAME", "QUANTITY", "PRICE"]
                    ) if not bse_bulk.empty else bse_bulk
                except Exception as exc:
                    bse_bulk = pd.DataFrame()
                    st.warning(f"BSE bulk deals fetch failed: {exc}")
                try:
                    nse_bulk = imi.fetch_nse_bulk_deals()
                    nse_bulk = imi.mark_new_rows(
                        nse_bulk, "nse_bulk", ["Date", "Symbol", "Client Name", "Quantity Traded"]
                    ) if not nse_bulk.empty else nse_bulk
                except Exception as exc:
                    nse_bulk = pd.DataFrame()
                    st.warning(f"NSE bulk deals fetch failed: {exc}")
                st.session_state["imi_bulk_bse"] = bse_bulk
                st.session_state["imi_bulk_nse"] = nse_bulk

        st.markdown("**BSE**")
        _highlight_deals(st.session_state.get("imi_bulk_bse", pd.DataFrame()),
                         min_val_bulk, "TRANSACTION_TYPE", filter_key="imi_bulk_bse_filter")
        st.markdown("**NSE**")
        _highlight_deals(st.session_state.get("imi_bulk_nse", pd.DataFrame()),
                         min_val_bulk, "Buy/Sell", filter_key="imi_bulk_nse_filter")

    with intel_tabs[1]:
        min_val_block = st.slider("Highlight block deals above (₹ Lakh)", 5, 2000, 100, step=25, key="imi_block_min")
        if st.button("🔄 Refresh Block Deals", key="imi_block_refresh"):
            with st.spinner("Fetching BSE + NSE block deals…"):
                try:
                    bse_block = imi.fetch_bse_block_deals()
                    bse_block = imi.mark_new_rows(
                        bse_block, "bse_block", ["DEAL_DATE", "SCRIP_CODE", "CLIENT_NAME", "QUANTITY", "PRICE"]
                    ) if not bse_block.empty else bse_block
                except Exception as exc:
                    bse_block = pd.DataFrame()
                    st.warning(f"BSE block deals fetch failed: {exc}")
                try:
                    nse_block = imi.fetch_nse_block_deals()
                    nse_block = imi.mark_new_rows(
                        nse_block, "nse_block", ["Date", "Symbol", "Client Name", "Quantity Traded"]
                    ) if not nse_block.empty else nse_block
                except Exception as exc:
                    nse_block = pd.DataFrame()
                    st.warning(f"NSE block deals fetch failed: {exc}")
                st.session_state["imi_block_bse"] = bse_block
                st.session_state["imi_block_nse"] = nse_block

        st.markdown("**BSE**")
        _highlight_deals(st.session_state.get("imi_block_bse", pd.DataFrame()),
                         min_val_block, "TRANSACTION_TYPE", filter_key="imi_block_bse_filter")
        st.markdown("**NSE**")
        _highlight_deals(st.session_state.get("imi_block_nse", pd.DataFrame()),
                         min_val_block, "Buy/Sell", filter_key="imi_block_nse_filter")

    with intel_tabs[2]:
        ins_col1, ins_col2 = st.columns(2)
        ins_from = ins_col1.date_input("From", value=date.today() - timedelta(days=7), key="imi_ins_from")
        ins_to = ins_col2.date_input("To", value=date.today(), key="imi_ins_to")
        if st.button("🔄 Refresh Insider Trading", key="imi_ins_refresh"):
            with st.spinner("Fetching BSE insider trading (SEBI PIT disclosures)…"):
                try:
                    ins_df = imi.fetch_bse_insider_trading(
                        ins_from.strftime("%d/%m/%Y"), ins_to.strftime("%d/%m/%Y")
                    )
                    if not ins_df.empty:
                        ins_df = imi.mark_new_rows(
                            ins_df, "bse_insider",
                            ["Fld_ID"] if "Fld_ID" in ins_df.columns else ins_df.columns[:3].tolist(),
                        )
                    st.session_state["imi_insider"] = ins_df
                except Exception as exc:
                    st.error(f"BSE insider trading fetch failed: {exc}")

        ins_results = st.session_state.get("imi_insider")
        if ins_results is None:
            st.info("Pick a date range and click **Refresh Insider Trading**.")
        elif ins_results.empty:
            st.info("No insider trading disclosures in this date range.")
        else:
            keep_cols = [c for c in [
                "New", "Companyname", "Fld_PromoterName", "Fld_PersonCatgName", "Fld_TransactionType",
                "Fld_PercentofShareholdingPre", "Fld_PercentofShareholdingPost",
                "Fld_FromDate", "Fld_ToDate", "Fld_TradeExchange",
            ] if c in ins_results.columns]
            ins_display = ins_results[keep_cols].copy()
            # Δ Holding % — post minus pre. Positive = accumulation, negative = disposal.
            if {"Fld_PercentofShareholdingPre", "Fld_PercentofShareholdingPost"}.issubset(ins_display.columns):
                pre = pd.to_numeric(ins_display["Fld_PercentofShareholdingPre"], errors="coerce")
                post = pd.to_numeric(ins_display["Fld_PercentofShareholdingPost"], errors="coerce")
                ins_display["Δ Holding %"] = (post - pre).round(4)
                # Optional direction tag for quick eyeballing
                ins_display["Direction"] = ins_display["Δ Holding %"].apply(
                    lambda x: "▲ Buy" if pd.notna(x) and x > 0
                    else ("▼ Sell" if pd.notna(x) and x < 0 else "—")
                )
                # Sort/filter controls
                dir_col1, dir_col2 = st.columns([1, 1])
                dir_filter = dir_col1.radio(
                    "Direction filter", ["All", "Buys only (▲)", "Sells only (▼)"],
                    horizontal=True, key="imi_ins_dir",
                )
                min_abs = dir_col2.number_input(
                    "Min |Δ Holding %|", min_value=0.0, value=0.0, step=0.1, key="imi_ins_minabs",
                )
                if dir_filter == "Buys only (▲)":
                    ins_display = ins_display[ins_display["Δ Holding %"] > 0]
                elif dir_filter == "Sells only (▼)":
                    ins_display = ins_display[ins_display["Δ Holding %"] < 0]
                if min_abs > 0:
                    ins_display = ins_display[ins_display["Δ Holding %"].abs() >= min_abs]
                ins_display = ins_display.sort_values("Δ Holding %", ascending=False, na_position="last")

            if "Companyname" in ins_display.columns:
                ins_display["Chart"] = ins_display["Companyname"].apply(
                    lambda s: f"http://localhost:5001/?symbol={str(s).strip()}&exchange=BSE&tf=1d"
                )
            st.caption(f"{len(ins_display)} disclosure(s)")
            ins_col_config = {}
            if "Chart" in ins_display.columns:
                ins_col_config["Chart"] = st.column_config.LinkColumn("Chart", display_text="📈 Open", width="small")
            if "Δ Holding %" in ins_display.columns:
                ins_col_config["Δ Holding %"] = st.column_config.NumberColumn(
                    "Δ Holding %", format="%+.4f", help="Post − Pre shareholding percentage",
                )

            def _dir_color(row):
                v = row.get("Δ Holding %")
                if pd.isna(v):
                    return [""] * len(row)
                if v > 0:
                    return ["background-color: rgba(63,185,80,0.12)"] * len(row)
                if v < 0:
                    return ["background-color: rgba(248,81,73,0.12)"] * len(row)
                return [""] * len(row)

            styled = ins_display.style.apply(_dir_color, axis=1) \
                if "Δ Holding %" in ins_display.columns else ins_display
            st.dataframe(styled, use_container_width=True, hide_index=True, column_config=ins_col_config)

    with intel_tabs[3]:
        st.caption(
            "Gap-up/gap-down and unusual-volume scan over the bhavcopy universe (reuses the same "
            "Full-Market source as Scanner Hub)."
        )
        gv_col1, gv_col2, gv_col3 = st.columns(3)
        gv_top_n = gv_col1.slider("Universe size (top N by traded value)", 50, 500, 150, step=50, key="imi_gv_topn")
        gv_gap_pct = gv_col2.slider("Min gap %", 1.0, 15.0, 3.0, step=0.5, key="imi_gv_gap")
        gv_vol_mult = gv_col3.slider("Min volume × 20d avg", 1.0, 10.0, 2.0, step=0.5, key="imi_gv_vol")

        if st.button("🔄 Run Gap & Volume Scan", type="primary", key="imi_gv_run"):
            with st.spinner("Loading market universe…"):
                try:
                    gv_universe = cached_fetch_bhavcopy_universe(gv_top_n)
                except Exception as exc:
                    gv_universe = []
                    st.error(f"Bhavcopy fetch failed: {exc}")

            gv_hits = []
            with st.spinner(f"Scanning {len(gv_universe)} symbols for gaps/volume…"):
                for sym in gv_universe:
                    try:
                        df_gv = cached_fetch_ohlcv(f"{sym}.NS", days=40)
                    except Exception:
                        continue
                    if df_gv is None or len(df_gv) < 21:
                        continue
                    close_col = "close" if "close" in df_gv.columns else "Close"
                    open_col = "open" if "open" in df_gv.columns else "Open"
                    vol_col = "volume" if "volume" in df_gv.columns else "Volume"
                    prev_close = float(df_gv[close_col].iloc[-2])
                    today_open = float(df_gv[open_col].iloc[-1])
                    if prev_close <= 0:
                        continue
                    gap_pct = (today_open - prev_close) / prev_close * 100
                    vol_avg20 = float(df_gv[vol_col].iloc[-21:-1].mean())
                    vol_today = float(df_gv[vol_col].iloc[-1])
                    vol_ratio = vol_today / vol_avg20 if vol_avg20 > 0 else 0
                    if abs(gap_pct) >= gv_gap_pct or vol_ratio >= gv_vol_mult:
                        gv_hits.append({
                            "Symbol": sym, "Gap %": round(gap_pct, 2),
                            "Vol × 20d Avg": round(vol_ratio, 2),
                            "Close": round(float(df_gv[close_col].iloc[-1]), 2),
                        })
            st.session_state["imi_gv_results"] = sorted(
                gv_hits, key=lambda h: abs(h["Gap %"]) + h["Vol × 20d Avg"], reverse=True
            )

        gv_results = st.session_state.get("imi_gv_results")
        if gv_results is None:
            st.info("Click **Run Gap & Volume Scan**.")
        elif not gv_results:
            st.info("No stocks met the gap/volume thresholds — try loosening them.")
        else:
            df_gv_res = pd.DataFrame(gv_results)
            df_gv_res["Chart"] = df_gv_res["Symbol"].apply(
                lambda s: f"http://localhost:5001/?symbol={s}.NS&tf=1d"
            )
            df_gv_res = _with_analyze_col(df_gv_res, "Symbol", after="Chart")
            st.caption(f"{len(df_gv_res)} stocks flagged")
            st.dataframe(
                df_gv_res, use_container_width=True, hide_index=True,
                column_config={
                    "Chart": st.column_config.LinkColumn("Chart", display_text="Open Chart", width="small"),
                    "Analyze": _analyze_colcfg(),
                    "Gap %": st.column_config.NumberColumn("Gap %", format="%.2f%%"),
                },
            )
