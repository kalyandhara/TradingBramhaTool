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
import time as _time
import json
import logging
import socket
from datetime import date, datetime, timedelta, time
from pathlib import Path
from urllib.parse import quote

_log = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent))

import screener_pipeline as sp
import symbol_directory as symdir
import ew_module
import scanner_templates as sc
import opportunity_hub as oh
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
import market_verdict as mvd
import block_deal_intel as bdi
import deal_infographic as dinf
import nse_oi_momentum as oim
import browser_cookie_helper as bch
import stock_council as council
import fundamentals_deep as fdeep
import fundamental_score as fscore
import peer_comparison as pcmp
import smart_money as smm
import red_flags as rflags
import technofunda_funnel as tff
import funnel_backtest as fbt
import smallcap_discovery as scd
import ui_jobs
import scenarios as scen
import rating
import opportunity_daily as od
import market_health as mh
import report_style as rs
import sector_card as scard
import opportunity_report as orep
import pcr
import price_levels as plv
import rrg as rrg_mod
import ownership_cache as ocache
import concalls

# The M1 rating lives in rating.py so the headless daily Opportunity Hub job
# scores with the SAME code the interactive Hub shows. Aliased to the old
# private names so every existing call site here is untouched.
OVERALL_WEIGHTS = rating.OVERALL_WEIGHTS
_compute_canslim = rating.compute_canslim
_overall_rating = rating.overall_rating

try:
    from ta.momentum import RSIIndicator
except ImportError:
    sys.exit("Run:  py -3 -m pip install ta")

BASE_DIR = sp.BASE_DIR

# Sidebar starts collapsed: navigation moved to a horizontal top bar, so the
# sidebar now holds nothing. Left expandable rather than hidden outright so
# Streamlit's own controls stay reachable.
st.set_page_config(page_title="Trading Bramha Dashboard", layout="wide",
                   initial_sidebar_state="collapsed")

# Base URL of THIS dashboard, used to build "Analyze" deep-links that open the
# Stock Analyzer (with the 3-POV Council) in a new browser tab. Mirrors the
# hardcoded localhost:5001 chart-server convention already used across the app.
DASHBOARD_BASE = "http://localhost:8501"


def _analyze_url(sym) -> str | None:
    """Deep-link that opens the Stock Analyzer on `sym` in a fresh tab."""
    s = str(sym).strip().upper().replace(".NS", "")
    if not s or s.startswith("^"):
        return None
    # Percent-encode: NSE tickers legitimately contain "&" (M&M, GVT&D), which
    # unescaped ends the symbol parameter early and silently deep-links to the
    # wrong stock rather than failing visibly.
    return f"{DASHBOARD_BASE}/?nav=analyze&symbol={quote(s, safe='')}"


def _chart_url(sym) -> str | None:
    """Deep-link that opens the multi-chart tool (chart_server on :5001) on `sym`.
    Bare NSE tickers are the norm across this app — add .NS so yfinance resolves;
    indices (leading ^) and already-suffixed symbols pass through."""
    s = str(sym).strip().upper()
    if not s:
        return None
    tkr = s if ("." in s or s.startswith("^")) else f"{s}.NS"
    return f"http://localhost:5001/?symbol={quote(tkr, safe='^')}&tf=1d"


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


# ── Chart-icon family for dataframes ──────────────────────────────────────────
# st.dataframe cells can't render the card's HTML action-icon row, so the same
# family (in-app Chart 👁 / Analyze ↗ + TradingView / Screener / Google Finance)
# is surfaced as a set of LinkColumns. display_text keeps a word alongside the
# emoji — emoji-ONLY display_text triggers Streamlit's spurious edit-pencil bug.
_CHART_FAMILY_COLS = ["Chart", "Analyze", "TView", "Screener", "GFin"]


def _chart_family_urls(sym) -> dict[str, "str | None"]:
    s = str(sym).strip().upper().replace(".NS", "")
    if not s or s.startswith("^"):
        return {c: None for c in _CHART_FAMILY_COLS}
    return {
        "Chart":    _chart_url(sym),
        "Analyze":  _analyze_url(sym),
        "TView":    f"https://www.tradingview.com/chart/?symbol=NSE%3A{s}",
        "Screener": f"https://www.screener.in/company/{s}/consolidated/",
        "GFin":     f"https://www.google.com/finance/quote/{s}:NSE",
    }


def _with_chart_family(df, symbol_col: str):
    """Return a copy of df with the card's chart-icon family appended as
    LinkColumns, keyed off the symbols in `symbol_col`."""
    out = df.copy()
    fam = [_chart_family_urls(s) for s in out[symbol_col]]
    for c in _CHART_FAMILY_COLS:
        out[c] = [f[c] for f in fam]
    return out


def _chart_family_colcfg() -> dict:
    return {
        "Chart":    st.column_config.LinkColumn(
            "Chart", help="Chart Tool (in-app, :5001)",
            display_text="👁 Chart", width="small"),
        "Analyze":  st.column_config.LinkColumn(
            "Analyze", help="Stock Analyzer (in-app)",
            display_text="↗ Analyze", width="small"),
        "TView":    st.column_config.LinkColumn(
            "TView", help="Open on TradingView",
            display_text="📈 TV", width="small"),
        "Screener": st.column_config.LinkColumn(
            "Screener", help="Open on Screener.in",
            display_text="📊 Screener", width="small"),
        "GFin":     st.column_config.LinkColumn(
            "GFin", help="Open on Google Finance",
            display_text="G Finance", width="small"),
    }


# ── Shareable "copy as card" for Telegram / social ────────────────────────────
# st.dataframe can't be copied with links intact, so we build a self-contained
# HTML card (inline styles + <a> links → survive a rich-text paste into Telegram,
# email, etc.) and a plain-text twin (URLs spelled out → survives platforms that
# strip HTML, e.g. WhatsApp/X). Symbol links point at PUBLIC destinations only
# (TradingView / Screener) — never the localhost :5001 chart, which is useless to
# a recipient.
def _share_card_html(title: str, subtitle: str, items: list[dict]) -> tuple[str, str]:
    """Build (card_html, plain_text) from row items.
    Each item: {label, sym, score, meta} — any field optional."""
    rows_html: list[str] = []
    rows_txt: list[str] = []
    for it in items:
        label = it.get("label") or ""
        sym = it.get("sym") or ""
        score = it.get("score")
        meta = it.get("meta") or ""
        tv = _chart_family_urls(sym).get("TView") if sym else None

        parts = []
        if label:
            parts.append(f'<span style="font-weight:700;">{label}</span>')
        if sym:
            link = (f'<a href="{tv}" style="color:#ea580c;text-decoration:none;'
                    f'font-weight:600;">{sym}</a>') if tv else f'<b>{sym}</b>'
            parts.append(("— " if label else "") + link)
        if score is not None and score != "":
            parts.append(f'<span style="color:#16a34a;font-weight:600;">{score}</span>')
        if meta:
            parts.append(f'<span style="color:#8a7a68;">· {meta}</span>')
        rows_html.append(
            '<div style="padding:5px 0;border-top:1px solid #f1e9dd;font-size:13px;'
            f'color:#3a2a1e;">{" ".join(parts)}</div>'
        )

        tparts = [p for p in (label, sym, ("" if score in (None, "") else str(score)),
                              (f"({meta})" if meta else "")) if p]
        line = " ".join(tparts)
        rows_txt.append(line + (f"\n{tv}" if tv else ""))

    card_html = (
        '<div style="font-family:\'Segoe UI\',system-ui,sans-serif;'
        'border:1px solid #f0e0cc;border-radius:12px;padding:14px 16px;'
        'max-width:560px;background:#fffdfa;">'
        f'<div style="font-weight:700;font-size:15px;color:#ea580c;">{title}</div>'
        f'<div style="font-size:11px;color:#8a7a68;margin-bottom:4px;">{subtitle}</div>'
        + "".join(rows_html)
        + '<div style="margin-top:8px;font-size:10px;color:#b0a290;">'
          'via Trading Bramha</div>'
        '</div>'
    )
    plain_text = f"{title}\n{subtitle}\n" + "\n".join(rows_txt) + "\n— via Trading Bramha"
    return card_html, plain_text


def _render_copy_card(card_html: str, plain_text: str, key: str) -> None:
    """Render the card as a live preview + a Copy button. Copy uses an
    execCommand selection first (reliable inside Streamlit's iframe), then falls
    back to the async Clipboard API with an explicit text/html + text/plain item."""
    import json as _json
    plain_js = _json.dumps(plain_text)
    n_rows = card_html.count('border-top:1px solid')
    height = 150 + min(n_rows, 60) * 24
    components.html(
        f"""
        <div id="tbcard-{key}">{card_html}</div>
        <div style="margin-top:10px;">
          <button id="tbbtn-{key}" onclick="tbCopy_{key}()"
            style="background:#ea580c;color:#fff;border:none;border-radius:8px;
                   padding:7px 14px;cursor:pointer;font-size:13px;font-weight:600;">
            📋 Copy card
          </button>
          <span id="tbmsg-{key}" style="margin-left:10px;font-size:12px;color:#16a34a;"></span>
        </div>
        <script>
        function tbCopy_{key}() {{
          var card = document.getElementById('tbcard-{key}');
          var msg  = document.getElementById('tbmsg-{key}');
          var plain = {plain_js};
          var html = card.innerHTML;
          function ok()  {{ msg.style.color='#16a34a';
                            msg.textContent='✓ Copied — paste into Telegram / email'; }}
          function bad() {{ msg.style.color='#b45309';
                            msg.textContent='⚠ Blocked — select the card and press Ctrl+C'; }}
          try {{
            var range = document.createRange();
            range.selectNode(card);
            var sel = window.getSelection();
            sel.removeAllRanges(); sel.addRange(range);
            var done = document.execCommand('copy');
            sel.removeAllRanges();
            if (done) {{ ok(); return; }}
          }} catch (e) {{}}
          if (navigator.clipboard && window.ClipboardItem) {{
            var item = new ClipboardItem({{
              'text/html':  new Blob([html],  {{type:'text/html'}}),
              'text/plain': new Blob([plain], {{type:'text/plain'}})
            }});
            navigator.clipboard.write([item]).then(ok, bad);
          }} else {{ bad(); }}
        }}
        </script>
        """,
        height=height,
        scrolling=True,
    )


def _share_card_plain(title: str, subtitle: str, items: list[dict],
                      bullet: str = "•") -> str:
    """Emoji-bulleted plain text — no HTML at all — for WhatsApp / Telegram,
    which strip rich cards. URLs go on their own line so every client makes
    them tappable."""
    lines = [title, subtitle, ""]
    for it in items:
        label = it.get("label") or ""
        sym = it.get("sym") or ""
        score = it.get("score")
        meta = it.get("meta") or ""
        tv = _chart_family_urls(sym).get("TView") if sym else None
        head = f"{label} — {sym}" if (label and sym) else (label or sym)
        tail = " · ".join(
            p for p in (("" if score in (None, "") else str(score)), meta) if p
        )
        lines.append(f"{bullet} {head}" + (f" · {tail}" if tail else ""))
        if tv:
            lines.append(f"   {tv}")
    lines.append("— via Trading Bramha")
    return "\n".join(lines)


def _render_copy_plain(text: str, key: str) -> None:
    """Read-only preview box + a Copy button for the plain-text share format."""
    import json as _json
    txt_js = _json.dumps(text)
    esc = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    n_lines = text.count("\n") + 1
    ta_h = min(n_lines, 40) * 18 + 20
    height = ta_h + 70
    components.html(
        f"""
        <textarea id="tbpl-{key}" readonly
          style="width:100%;box-sizing:border-box;height:{ta_h}px;
                 font-family:ui-monospace,Consolas,monospace;font-size:12px;
                 line-height:1.5;border:1px solid #f0e0cc;border-radius:10px;
                 padding:10px;background:#fffdfa;color:#3a2a1e;resize:vertical;"
          >{esc}</textarea>
        <div style="margin-top:8px;">
          <button id="tbplbtn-{key}" onclick="tbPlain_{key}()"
            style="background:#0ea5e9;color:#fff;border:none;border-radius:8px;
                   padding:7px 14px;cursor:pointer;font-size:13px;font-weight:600;">
            💬 Copy plain text
          </button>
          <span id="tbplmsg-{key}" style="margin-left:10px;font-size:12px;color:#16a34a;"></span>
        </div>
        <script>
        function tbPlain_{key}() {{
          var ta  = document.getElementById('tbpl-{key}');
          var msg = document.getElementById('tbplmsg-{key}');
          var txt = {txt_js};
          function ok()  {{ msg.style.color='#16a34a';
                            msg.textContent='✓ Copied — paste into WhatsApp / Telegram'; }}
          function bad() {{ msg.style.color='#b45309';
                            msg.textContent='⚠ Blocked — tap the box and press Ctrl+C'; }}
          try {{
            ta.focus(); ta.select();
            var done = document.execCommand('copy');
            ta.setSelectionRange(0, 0); ta.blur();
            if (done) {{ ok(); return; }}
          }} catch (e) {{}}
          if (navigator.clipboard) {{ navigator.clipboard.writeText(txt).then(ok, bad); }}
          else {{ bad(); }}
        }}
        </script>
        """,
        height=height,
        scrolling=True,
    )


# FR-0 style primitive — one token block for every HTML surface on the page.
# Injected once, before anything that calls the rs.* helpers.
st.markdown(rs.report_css(), unsafe_allow_html=True)

# ── Widget chrome ─────────────────────────────────────────────────────────────
# Streamlit exposes no Python API for how a button LOOKS — `type=` picks
# primary/secondary and `use_container_width=` stretches it, and that is the whole
# surface. Everything else is CSS, and the hook is that Streamlit stamps stable
# `data-testid` attributes on its widgets: stBaseButton-secondary,
# stBaseButton-primary, stPopoverButton. Targeting those is the supported-ish way
# to restyle, and it is why this block exists rather than a config setting.
#
# Two caveats worth knowing before leaning on it. The `st-emotion-cache-*` classes
# beside those testids are BUILD HASHES and change between Streamlit versions —
# never select on them. And `!important` is needed because Streamlit's own rules
# are more specific than a plain selector here.
#
# The defaults run tall (~40px) with heavy borders; these bring buttons down to a
# 32px row, 13px label, softer radius, and give secondary buttons a real hover.
st.markdown(
    """
    <style>
      /* ── Page-content buttons (not the nav ribbon) ─────────────────────────── */
      [data-testid="stBaseButton-secondary"],
      [data-testid="stBaseButton-primary"],
      [data-testid="stPopoverButton"] {
        min-height: 32px !important;
        height: 32px !important;
        padding: 0 12px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        line-height: 1 !important;
        transition: background .12s ease-out, border-color .12s ease-out;
      }
      [data-testid="stBaseButton-secondary"],
      [data-testid="stPopoverButton"] {
        border: 1px solid var(--tb-border) !important;
        background: var(--tb-surface) !important;
        color: var(--tb-text-body) !important;
      }
      [data-testid="stBaseButton-secondary"]:hover,
      [data-testid="stPopoverButton"]:hover {
        background: var(--tb-surface-alt) !important;
        border-color: var(--tb-border-strong) !important;
        color: var(--tb-text) !important;
      }
      [data-testid="stBaseButton-secondary"]:active,
      [data-testid="stPopoverButton"]:active {
        transform: scale(0.97) !important;
        opacity: 0.8 !important;
        transition: transform 60ms ease-out, opacity 60ms ease-out !important;
      }
      [data-testid="stBaseButton-primary"] {
        border: 1px solid var(--tb-accent) !important;
        box-shadow: none !important;
      }

      /* ── Nav dropdown mega-panel ─────────────────────────────────────────────
         Dark glass panel. stPopoverBody and ALL its Streamlit-generated inner
         containers must be transparent so the panel's own background shows.
      ── */
      [data-testid="stPopoverBody"] {
        background: rgba(14,10,6,0.93) !important;
        backdrop-filter: blur(20px) saturate(140%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(140%) !important;
        border: 1px solid rgba(234,88,12,0.28) !important;
        border-radius: 16px !important;
        padding: 14px 10px 10px !important;
        min-width: 360px !important;
        max-width: 440px !important;
        box-shadow:
          0 2px 4px rgba(0,0,0,0.30),
          0 16px 40px rgba(0,0,0,0.65),
          inset 0 1px 0 rgba(255,255,255,0.05) !important;
        overflow: visible !important;
      }
      /* Kill every Streamlit inner wrapper's white background */
      [data-testid="stPopoverBody"] > div,
      [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"],
      [data-testid="stPopoverBody"] [data-testid="stHorizontalBlock"],
      [data-testid="stPopoverBody"] [data-testid="stElementContainer"],
      [data-testid="stPopoverBody"] [class*="block-container"],
      [data-testid="stPopoverBody"] [class*="element-container"] {
        background: transparent !important;
        background-color: transparent !important;
      }

      /* ── Popover header strip — group name ───────────────────── */
      [data-testid="stPopoverBody"]::before {
        content: "Pages";
        display: block;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.12em;
        color: rgba(234,88,12,0.75);
        text-transform: uppercase;
        padding: 0 6px 10px;
        border-bottom: 1px solid rgba(234,88,12,0.14);
        margin-bottom: 8px;
      }

      /* ── 2-column grid for the link list ────────────────────── */
      [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 1px 4px !important;
      }

      /* Each cell: full width inside its grid column */
      [data-testid="stPopoverBody"] [data-testid="stElementContainer"] {
        min-width: 0 !important;
      }

      /* ── Menu items as text links (no button chrome) ─────────── */
      [data-testid="stPopoverBody"] [data-testid="stBaseButton-secondary"],
      [data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"] {
        background: transparent !important;
        border: none !important;
        border-bottom: 1px solid transparent !important;
        border-radius: 4px !important;
        color: rgba(255,240,220,0.72) !important;
        font-size: 13px !important;
        font-weight: 450 !important;
        letter-spacing: 0em !important;
        min-height: unset !important;
        height: auto !important;
        padding: 5px 8px !important;
        justify-content: flex-start !important;
        text-align: left !important;
        box-shadow: none !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        width: 100% !important;
        line-height: 1.4 !important;
        transition: color 0.1s ease-out, border-bottom-color 0.1s ease-out !important;
      }

      /* Hover — just brightens the text + faint underline */
      [data-testid="stPopoverBody"] [data-testid="stBaseButton-secondary"]:hover {
        background: transparent !important;
        color: #fff5eb !important;
        border-bottom-color: rgba(234,88,12,0.45) !important;
      }
      [data-testid="stPopoverBody"] [data-testid="stBaseButton-secondary"]:active {
        opacity: 0.65 !important;
        transition: opacity 60ms ease-out !important;
      }

      /* Active / current page — amber text + left dot */
      [data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"] {
        background: transparent !important;
        color: #fb923c !important;
        font-weight: 650 !important;
        border-bottom-color: transparent !important;
        padding-left: 14px !important;
        position: relative !important;
      }
      [data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"]::before {
        content: "·";
        position: absolute;
        left: 4px;
        color: #ea580c;
        font-size: 16px;
        line-height: 1;
        top: 50%;
        transform: translateY(-50%);
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Page chrome — headings, alerts, expanders ─────────────────────────────────
# Every page title on the dashboard is an `st.subheader`, which renders in
# Streamlit's own type scale and blue-grey — beside the cream/amber report
# components it reads as a different application. Same story for `st.info` /
# `st.warning` / `st.success`, whose default palette is Streamlit blue on a cream
# page. There are 32 subheaders and ~60 alert calls across the app, so restyling
# them HERE fixes every page at once instead of touching ~90 call sites and
# risking a regression in each.
#
# Selectors verified live against the running app rather than assumed:
# stHeading, stAlert / stAlertContainer / stAlertContent{Info,Warning,Success,
# Error}, stExpander. Interpolated from rs.TOKENS so the palette stays
# single-sourced — change a token, this follows.
_T = rs.TOKENS
st.markdown(
    f"""
    <style>
      /* Page + section titles */
      [data-testid="stHeading"] h1,
      [data-testid="stHeading"] h2,
      [data-testid="stHeading"] h3 {{
        color: {_T['text']} !important;
        font-weight: 800 !important;
        font-optical-sizing: auto !important;
        padding: 0 !important;
        margin: 2px 0 10px !important;
      }}
      [data-testid="stHeading"] h1 {{
        letter-spacing: -0.022em !important;
        line-height: 1.06 !important;
      }}
      [data-testid="stHeading"] h2 {{
        font-size: 25px !important;
        letter-spacing: -0.014em !important;
        line-height: 1.12 !important;
      }}
      [data-testid="stHeading"] h3 {{
        font-size: 19px !important;
        font-weight: 700 !important;
        letter-spacing: -0.006em !important;
        line-height: 1.18 !important;
      }}

      /* Alerts: token palette, flat, tighter than the default pill */
      [data-testid="stAlertContainer"] {{
        border-radius: 12px !important;
        border-left: 3px solid transparent !important;
        padding: 10px 14px !important;
        font-size: 13px !important;
        box-shadow: none !important;
      }}
      [data-testid="stAlertContentInfo"] {{
        background: {_T['info_soft']} !important;
        border-left-color: {_T['info']} !important;
        color: {_T['text_body']} !important;
      }}
      [data-testid="stAlertContentWarning"] {{
        background: {_T['surface_warm']} !important;
        border-left-color: {_T['accent']} !important;
        color: {_T['text_body']} !important;
      }}
      [data-testid="stAlertContentSuccess"] {{
        background: {_T['good_soft']} !important;
        border-left-color: {_T['good']} !important;
        color: {_T['text_body']} !important;
      }}
      [data-testid="stAlertContentError"] {{
        background: {_T['risk_soft']} !important;
        border-left-color: {_T['risk']} !important;
        color: {_T['text_body']} !important;
      }}

      /* Expanders — the side panels on every screener page use these */
      [data-testid="stExpander"] details {{
        border: 1px solid {_T['border']} !important;
        border-radius: 12px !important;
        background: {_T['surface']} !important;
      }}
      [data-testid="stExpander"] summary {{
        font-size: 13px !important;
        font-weight: 600 !important;
        color: {_T['text_body']} !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Content-width constraint ───────────────────────────────────────────────────
# layout="wide" is kept so the 5-column metric strip and scanner card grid have
# room to breathe on large monitors, but raw "wide" fills every pixel edge-to-edge
# on a 4K/ultrawide display — uncomfortable to read and scan. Clamping the main
# block container to 1 440 px and centering it gives the best of both: wide-mode
# Streamlit widgets stay proportional at their natural widths, while the whole
# column sits comfortably in the viewport center at any resolution above that.
#
# The selector [data-testid="stMainBlockContainer"] wraps the entire main-content
# column that Streamlit renders inside the wide layout. The sidebar is a sibling
# element, so constraining this testid leaves sidebar behaviour unchanged.
st.markdown(
    """
    <style>
      [data-testid="stMainBlockContainer"] {
        max-width: 1440px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ribbon CSS ─────────────────────────────────────────────────────────
# We identify the nav HorizontalBlock via a sentinel <div id="tb-navstart">
# injected immediately before st.columns(). The :has() selector then targets
# exactly that sibling — safe in Chrome 105+/Firefox 121+ (personal tool only).
#
# The ribbon bleeds full-width by counteracting the 2rem side padding on
# stMainBlockContainer with negative margins. We keep padding so content inside
# the columns still aligns with the rest of the page.
st.markdown(
    """
    <style>
      /* ── Suppress Streamlit chrome (deploy/share bar + top decoration) ─── */
      [data-testid="stHeader"]     { display: none !important; }
      [data-testid="stDecoration"] { display: none !important; }
      [data-testid="stToolbar"]    { display: none !important; }
      /* Remove the top padding that Streamlit reserves for its hidden header */
      [data-testid="stMainBlockContainer"] { padding-top: 0 !important; }
      section.main > div:first-child { padding-top: 0 !important; }

      /* Every st.markdown("<style>…") leaves a zero-height element container
         behind, and the vertical block's 16px flex gap still applies to each —
         six of them stacked 96px of dead white space ABOVE the ribbon. Collapse
         style-only containers (no st.markdown in this app mixes <style> with
         visible content) and the nav sentinel, so the bar sits flush at the top
         and its sticky position is actually at y=0. */
      [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style),
      [data-testid="stElementContainer"]:has(#tb-navstart),
      [data-testid="stElementContainer"]:has(#tb-searchslot) {
        display: none !important;
      }

      /* The typeahead's dropdown lives INSIDE its component iframe, and an
         iframe clips its own content — so the iframe has to be as tall as the
         open list. Left in flow that would stretch the 48px bar to ~310px, so
         the search column becomes a positioning context and the iframe hangs
         out of flow beneath it. The component sets its own frame height: 34px
         closed, taller while the list is open, so it only covers the page
         below while there is actually a list to show. */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stColumn"]:has(#tb-searchslot) {
        position: relative !important;
        overflow: visible !important;
        /* Absolutely-positioned child + hidden sentinel = a zero-height column,
           which would anchor the box to the bar's centre LINE and leave it
           hanging below the bar. Give the column the bar's height so `top` is
           measured from the bar's top and the list grows downward from there. */
        height: 48px !important;
      }
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stColumn"]:has(#tb-searchslot)
        [data-testid="stElementContainer"]:has(iframe) {
        position: absolute !important;
        top: 9px !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 1200 !important;
      }
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stColumn"]:has(#tb-searchslot) iframe {
        width: 100% !important;
        border: none !important;
        background: transparent !important;
        color-scheme: normal !important;
      }

      /* ── Nav ribbon ──────────────────────────────────────────────────────────
         DOM in Streamlit 1.57: stVerticalBlock
           > stElementContainer (wraps stMarkdown > #tb-navstart)  ← sentinel
           > stLayoutWrapper                                         ← nav columns
               > stHorizontalBlock > stColumn × N
         We use :has(#tb-navstart) on the stElementContainer, then + stLayoutWrapper
         to reach the nav wrapper without touching any other row.
      ── */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] {
        background: rgba(11,15,20,0.94) !important;
        backdrop-filter: blur(20px) saturate(140%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(140%) !important;
        margin-left:  -2rem !important;
        margin-right: -2rem !important;
        border-bottom: 1px solid #1c2430 !important;
        /* Sticky: navigation must survive a scroll down a 200-row scanner table. */
        position: sticky !important;
        top: 0 !important;
        z-index: 999 !important;
        /* The typeahead hangs below the bar; a clipped ribbon would cut it. */
        overflow: visible !important;
      }
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stHorizontalBlock"] {
        padding: 0 2rem !important;
        min-height: 48px !important;
        overflow: visible !important;
        align-items: stretch !important;
        gap: 0 !important;
      }

      /* Each column inside the ribbon */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stColumn"] {
        justify-content: center !important;
        padding: 0 !important;
      }

      /* Nav buttons: transparent, bold green text */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stBaseButton-secondary"],
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stBaseButton-primary"],
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stPopoverButton"] {
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        color: rgba(255,255,255,0.62) !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        min-height: 48px !important;
        height: 48px !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        letter-spacing: 0.01em !important;
        padding: 0 10px !important;
        transition: background .12s ease-out, color .12s ease-out, border-color .12s ease-out !important;
      }

      /* Hover: lighter green + green underline */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stBaseButton-secondary"]:hover,
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stPopoverButton"]:hover {
        background: rgba(255,255,255,0.05) !important;
        color: #ffffff !important;
        border-bottom-color: rgba(234,88,12,0.45) !important;
      }

      /* Active group/home: white text + green underline */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stBaseButton-primary"] {
        color: #ffffff !important;
        border-bottom: 2px solid #ea580c !important;
        font-weight: 700 !important;
      }

      /* Active group. A popover trigger keeps data-testid="stPopoverButton"
         whatever its type, so the primary state is carried on `kind` — which
         is enough specificity to beat the base rule above without !important
         gymnastics. Matches the active Home button exactly. */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stPopoverButton"][kind="primary"] {
        color: #ffffff !important;
        border-bottom: 2px solid #ea580c !important;
        font-weight: 700 !important;
      }

      /* Search box — a field, not a button, so it needs its own treatment:
         the bar's ground with a hairline, not Streamlit's light input chrome. */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stTextInput"] input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid #1c2430 !important;
        border-radius: 6px !important;
        color: #f8fafc !important;
        font-size: 12px !important;
        height: 30px !important;
        min-height: 30px !important;
        padding: 0 9px !important;
      }
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stTextInput"] input::placeholder {
        color: rgba(255,255,255,0.40) !important;
      }
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stTextInput"] input:focus {
        border-color: rgba(234,88,12,0.55) !important;
        box-shadow: none !important;
      }
      /* Streamlit wraps the input in a BaseWeb root that paints its own light
         ground (#f0f2f6). Styling only the <input> leaves that showing as a
         white slab in the dark bar — clear the wrapper too. */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stTextInputRootElement"],
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stTextInputRootElement"] > div,
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stTextInput"] > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
      }

      /* Streamlit stacks its own `expand_more` glyph UNDER the popover label,
         which is what made the bar 62px tall and the labels look wrapped. Hide
         it; the ▾ in the label carries the affordance on one line. */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stPopoverButton"] [data-testid="stIconMaterial"],
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stPopoverButton"] span[class*="material-icons"] {
        display: none !important;
      }
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stPopoverButton"] > div,
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stBaseButton-secondary"] > div,
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"] [data-testid="stBaseButton-primary"] > div {
        flex-direction: row !important;
        align-items: center !important;
        gap: 4px !important;
        white-space: nowrap !important;
      }

      /* Nav button press feedback */
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stBaseButton-secondary"]:active,
      [data-testid="stElementContainer"]:has(#tb-navstart) + [data-testid="stLayoutWrapper"]
        [data-testid="stPopoverButton"]:active {
        transform: scale(0.97) !important;
        opacity: 0.75 !important;
        transition: transform 60ms ease-out, opacity 60ms ease-out !important;
      }

      /* Respect OS reduced-motion preference */
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
          transition-duration: 50ms !important;
          animation-duration:  50ms !important;
          animation-iteration-count: 1 !important;
        }
        [data-testid^="stBaseButton"],
        [data-testid="stPopoverButton"] {
          transform: none !important;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# Sign-in — OPTIONAL (2026-09-04). Browsing no longer requires it.
# ──────────────────────────────────────────────────────────────────────────────
# This used to be a hard gate: an unauthenticated visitor got a full-page login
# and `st.stop()`, so nothing rendered until they signed in. It is now a control
# in the top-right of the ribbon, and the dashboard renders regardless.
#
# What signing in currently unlocks: NOTHING. The gate was all-or-nothing, so
# removing it leaves `logged_in` as a session flag with no consumer. It is kept
# rather than deleted so a future per-page gate has something to read, and so
# the credential check does not have to be rebuilt — but nobody should assume
# this flag is protecting anything today.
#
# Credentials still come from .streamlit/secrets.toml ([auth] username/password).
def _auth_check(username: str, password: str) -> bool:
    _u = st.secrets.get("auth", {}).get("username", "bramha")
    _p = st.secrets.get("auth", {}).get("password", "trading2024")
    return username == _u and password == _p


def _signin_control() -> None:
    """Ribbon sign-in popover. Renders the form, or who is signed in."""
    if st.session_state.get("logged_in"):
        with st.popover("● Signed in", use_container_width=True):
            st.caption(f"Signed in as **{st.session_state.get('auth_user', 'user')}**. "
                       "Sign-in is optional — no page is gated on it today.")
            if st.button("Sign out", key="tb_signout", use_container_width=True):
                st.session_state["logged_in"] = False
                st.session_state.pop("auth_user", None)
                st.rerun()
        return

    with st.popover("Sign in", use_container_width=True):
        st.caption("Optional — everything is browsable without it. Signing in "
                   "only records who you are for now.")
        with st.form("tb_login_form", border=False):
            _un = st.text_input("Username", placeholder="Enter username")
            _pw = st.text_input("Password", placeholder="Enter password", type="password")
            if st.form_submit_button("Sign in →", use_container_width=True,
                                     type="primary"):
                if _auth_check(_un, _pw):
                    st.session_state["logged_in"] = True
                    st.session_state["auth_user"] = _un
                    st.rerun()
                else:
                    st.error("Incorrect username or password.", icon="🔒")


@st.cache_data(ttl=3600, show_spinner=False)
def _symbol_matches(query: str, limit: int = 8) -> list[dict]:
    """NSE equity matches for `query`, from the chart tool's symbol directory.

    symbol_directory is the same index the chart's typeahead runs on — the live
    NSE equity list, cached to disk for 24h with a curated fallback — so both
    tools agree on what a symbol is instead of each keeping its own idea.

    Filtered to NSE because this Analyzer is NSE-only: sp.fetch_ohlcv builds
    "{symbol}.NS", so offering a BSE-only scrip would be offering a dead end.
    The first call may fetch the list; every later one is served from cache.
    """
    try:
        hits = symdir.search(query, limit=limit * 3)
    except Exception as e:
        _log.warning("symbol directory search failed for %r: %s", query, e)
        return []
    return [h for h in hits if h.get("exchange") == "NSE"][:limit]


def _symbol_jump(raw: str) -> None:
    """Resolve `raw` through the symbol directory, then route to the Analyzer.

    Priming the same session keys the "Analyze ↗" deep-link sets — one entry
    path, so an auto-run that works for a table link works for the box too.

    A typed prefix is the normal case, not an error: "KOPRA" is what you get
    when you know the name and not the ticker. An exact ticker runs straight
    through; anything else parks the candidates for the Analyzer to offer,
    rather than guessing between them or failing with "no usable data".

    Does not rerun: the component path reruns explicitly after this returns,
    and the text-box fallback is a widget callback, which Streamlit reruns
    after on its own.
    """
    sym = raw.strip().upper().replace(".NS", "")
    st.session_state["tb_search_input"] = ""   # leave the box ready for the next
    if not sym:
        return

    st.session_state["current_page"] = "Stock Analyzer"
    st.session_state.pop("tb_search_matches", None)
    st.session_state.pop("tb_search_miss", None)
    st.session_state.pop("tb_search_resolved", None)

    matches = _symbol_matches(sym)
    exact = next((m for m in matches if m["display"].upper() == sym), None)

    if exact or not matches:
        # Straight through on an exact hit — and also when the directory knows
        # nothing, because it can be stale on a fresh listing and the Analyzer's
        # own "no usable data" is a better answer than refusing to look.
        st.session_state["selected_symbol"] = sym
        st.session_state["last_analyzed"] = sym   # triggers the auto-run
        if not matches:
            st.session_state["tb_search_miss"] = sym
        return

    if len(matches) == 1:
        # One candidate is not ambiguity, it is a typo or a prefix — "KOPRA"
        # has exactly one NSE answer. Go, and say what it resolved to rather
        # than silently analysing a different ticker than the one typed.
        only = matches[0]["display"]
        st.session_state["selected_symbol"] = only
        st.session_state["last_analyzed"] = only
        st.session_state["tb_search_resolved"] = (sym, only, matches[0].get("name", ""))
        return

    # Genuinely ambiguous: show the candidates instead of analysing a guess.
    st.session_state["tb_search_matches"] = (sym, matches)
    st.session_state["selected_symbol"] = ""
    st.session_state.pop("last_analyzed", None)


#: The typeahead component. declare_component wants a directory holding
#: index.html; None if it is missing, in which case _search_control falls back
#: to a plain box rather than taking the ribbon down with it.
try:
    _SYMSEARCH = components.declare_component(
        "tb_symbol_search",
        path=str(Path(__file__).resolve().parent / "components" / "symbol_search"),
    )
except Exception as _e:            # pragma: no cover - packaging accident
    _log.warning("symbol search component unavailable: %s", _e)
    _SYMSEARCH = None


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _symbol_payload() -> str:
    """The NSE stock list as "DISPLAY|Name" lines, for the typeahead to filter.

    Sent to the browser so filtering is per-keystroke and local. It has to be:
    a Streamlit widget only reports on Enter or blur, so a round trip to Python
    per character is not just slow, it is not available at all.

    ~2,570 rows, ~90 KB. That crosses the socket on every rerun, which is the
    honest cost of this feature; on localhost it is noise next to the dataframes
    this app already ships. Names are cut to 44 chars because the row ellipsises
    long ones anyway.
    """
    try:
        entries = [e for e in symdir.get_directory()
                   if e.get("exchange") == "NSE" and e.get("type") == "stock"]
    except Exception as e:
        _log.warning("symbol directory unavailable for typeahead: %s", e)
        return ""
    return "\n".join(f"{e['display']}|{(e.get('name') or '')[:44]}" for e in entries)


def _search_control() -> None:
    """Ribbon symbol jump: a live typeahead over the NSE list.

    The component filters in the browser and reports one pick, so this costs a
    single rerun per search instead of one per keystroke. Everything it offers
    comes from symbol_directory — the same index behind the chart tool's
    typeahead — so both agree on what a symbol is.

    Falls back to a plain box if the component did not load: the ribbon losing
    its search would be worse than the search losing its dropdown.
    """
    if _SYMSEARCH is None:
        st.text_input("Symbol", key="tb_search_input", placeholder="Search ⌘K",
                      label_visibility="collapsed", on_change=_symbol_jump_from_box,
                      help="NSE code — Enter opens the Stock Analyzer")
        return

    # Sentinel: the ribbon CSS lifts this column's iframe out of flow so the
    # dropdown can hang below a 48px bar without stretching it.
    st.markdown('<div id="tb-searchslot"></div>', unsafe_allow_html=True)
    picked = _SYMSEARCH(options=_symbol_payload(), placeholder="Search ⌘K",
                        key="tb_symsearch", default=None)

    # `picked` persists across reruns — it is the component's current value, not
    # an event — so act on the nonce changing, or every rerun would re-jump.
    if isinstance(picked, dict) and picked.get("symbol"):
        if picked.get("n") != st.session_state.get("_tb_pick_n"):
            st.session_state["_tb_pick_n"] = picked["n"]
            _symbol_jump(picked["symbol"])
            st.rerun()


def _symbol_jump_from_box() -> None:
    _symbol_jump(st.session_state.get("tb_search_input", ""))


# ──────────────────────────────────────────────────────────────────────────────
# Navigation — left sidebar page router (replaces st.tabs; Streamlit can't
# switch tabs programmatically, so a real "click sidebar item -> jump to page"
# flow needs session_state + an if/elif router instead). Each PAGE_GROUPS entry
# must match a "if current_page == '...':" block below exactly.
# ──────────────────────────────────────────────────────────────────────────────
PAGE_GROUPS = {
    "Screening":        ["Opportunity Hub", "Delete Funnel", "Hidden Treasures", "Screener", "Other Screeners", "Scanner Hub",
                         "Breakout Scans", "High-Growth Screener"],
    "Market Intel":     ["Market Sentiment", "India Market Intel", "OI Momentum"],
    "Research":         ["Predictive Analysis", "Stock Analyzer", "Strategy Hub", "Sector Map", "Astro Timing", "Telegram Signals"],
    "Portfolio & Risk": ["Portfolio", "Watchlist", "Alerts"],
    "Ops":              ["Pipeline Log", "Scheduler Hub"],
}

#: One line per page, shown as the tooltip on its nav-popover button (Home no
#: longer cards the pages). Kept factual — each says what the page DOES, not how
#: good it is. Any page missing from here still routes fine, just without a hint.
PAGE_BLURBS = {
    "Opportunity Hub":      "Ranked daily shortlist across every scanner",
    "Delete Funnel":        "Technofunda 8-filter noise sieve — deletes to a shortlist",
    "Hidden Treasures":     "Small/micro-cap conviction screen — ownership + quality",
    "Screener":             "The core NSE screen with the saved pipeline",
    "Other Screeners":      "Ownership pipeline, sector rotation, bulk data",
    "Scanner Hub":          "24 pattern scanners, run on any universe",
    "Breakout Scans":       "External new-high breakout feeds — Chartink or TradingView",
    "High-Growth Screener": "Quality growth names on ROE / ROCE / OPM floors",
    "Market Sentiment":     "0–100 composite regime gauge, with coverage",
    "India Market Intel":   "Bulk & block deals, insider trades, gap scanner",
    "OI Momentum":          "Open-interest build-up and unwinding",
    "Predictive Analysis":  "Consolidated rating, chart and intel per stock",
    "Stock Analyzer":       "Full fundamental + technical deep dive",
    "Sector Map":           "Relative Rotation Graph and sector orbit",
    "Astro Timing":         "Reversal calendar — context, never an entry",
    "Telegram Signals":     "Ingested channel calls, parsed and tabulated",
    "Portfolio":            "Open positions, capital at risk, heat",
    "Watchlist":            "Tracked names and their trade plans",
    "Alerts":               "Price and metric alerts you have armed",
    "Pipeline Log":         "What the 4:05 PM batch did, and whether it failed",
    "Scheduler Hub":        "Batch jobs & the live alert bot — schedule, run, monitor",
    "Strategy Hub":         "Chart patterns, trading strategies, and fundamental scores",
}

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"

# Deep-link: a table's "Analyze ↗" link opens ?nav=analyze&symbol=SYM in a new
# tab. Consume the params once, route to the Stock Analyzer, pre-load the symbol
# and prime an auto-run, then clear the URL so sidebar navigation isn't pinned.
if st.query_params.get("nav") == "analyze" and st.query_params.get("symbol"):
    _dl_sym = st.query_params["symbol"].strip().upper()
    st.session_state["current_page"] = "Stock Analyzer"
    st.session_state["selected_symbol"] = _dl_sym
    st.session_state["last_analyzed"] = _dl_sym   # triggers auto-run in the tab
    st.query_params.clear()

# ── Ribbon status: market session + data freshness ──────────────────
# What a trading bar is FOR is telling you whether what you are looking at is
# current. Two facts, both cheap: is the NSE session on, and how old is the
# batch that produced these tables.
_NSE_TZ = "Asia/Kolkata"


def _market_status() -> tuple[str, str, str]:
    """(state, dot_colour, label) for the NSE session, in IST.

    HOLIDAY-UNAWARE, deliberately: this repo has no exchange holiday calendar,
    and inventing one that silently goes stale is worse than a dot that reads
    LIVE on Diwali. It answers "is it a weekday inside session hours", nothing
    more. Anyone gating an order on this needs a real calendar first.
    """
    from datetime import datetime as _dt, time as _t
    try:
        from zoneinfo import ZoneInfo
        now = _dt.now(ZoneInfo(_NSE_TZ))
    except Exception:
        return ("UNKNOWN", _T["absent"], "session unknown")
    hhmm = now.strftime("%H:%M")
    if now.weekday() >= 5:
        return ("CLOSED", _T["absent"], f"weekend · {hhmm} IST")
    t = now.time()
    if _t(9, 0) <= t < _t(9, 15):
        return ("PRE-OPEN", _T["accent"], f"pre-open · {hhmm} IST")
    if _t(9, 15) <= t <= _t(15, 30):
        return ("LIVE", _T["good"], f"live · {hhmm} IST")
    return ("CLOSED", _T["absent"], f"closed · {hhmm} IST")


def _batch_freshness() -> str:
    """Age of the last pipeline run, from the log file's mtime.

    The mtime is the honest signal here — it moves whenever the batch writes,
    whether it succeeded or failed. It says "the pipeline last did something
    at X", NOT "the data is good"; Pipeline Log is where you check the latter.
    """
    from datetime import datetime as _dt
    try:
        ts = sp.LOG_FILE.stat().st_mtime
    except Exception:
        return "no batch run yet"
    age = _dt.now().timestamp() - ts
    when = _dt.fromtimestamp(ts).strftime("%H:%M")
    if age < 3600:
        rel = f"{int(age // 60)}m ago"
    elif age < 86400:
        rel = f"{int(age // 3600)}h ago"
    else:
        rel = f"{int(age // 86400)}d ago"
    return f"batch {when} · {rel}"


#: (yahoo ticker, ribbon label). Three is the ceiling: the strip shares a line
#: with the breadcrumb, and a fourth starts truncating the page name on a laptop.
_RIBBON_INDICES = [("^NSEI", "NIFTY"), ("^NSEBANK", "BANKNIFTY"), ("^INDIAVIX", "VIX")]


@st.cache_data(ttl=3600, show_spinner=False)
def _ribbon_quotes(_bucket: int):
    """Last close and day change for the ribbon indices. ONE yfinance call.

    `_bucket` is a time bucket the caller passes in purely to bust this cache —
    the long ttl is a backstop, the bucket is the real clock. That indirection
    buys a refresh cadence that changes with the session (see the call site):
    a fixed short ttl would re-download the same closed-market numbers all
    evening, and a fixed long one would freeze the strip during a live session.

    Daily bars, so intraday this is the LAST CLOSE, not a live tick — the same
    basis as the Nifty stat card on Home. Every failure returns None values and
    the strip renders "—" rather than a stale or invented number.
    """
    try:
        import yfinance as yf
        data = yf.download(
            [t for t, _ in _RIBBON_INDICES], period="7d", interval="1d",
            progress=False, group_by="ticker", auto_adjust=False, threads=True,
        )
    except Exception as e:
        _log.warning("ribbon quotes fetch failed: %s", e)
        return [(lbl, None, None) for _, lbl in _RIBBON_INDICES]

    out = []
    for tkr, lbl in _RIBBON_INDICES:
        try:
            closes = data[tkr]["Close"].dropna()
            last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
            out.append((lbl, last, (last - prev) / prev * 100.0))
        except Exception:
            out.append((lbl, None, None))
    return out


# ── Horizontal top nav ────────────────────────────────────────────────────────
# Sentinel div → dark ribbon CSS targets the next sibling HorizontalBlock.
# Brand · Home · one popover per group · current-page label, all in one row.
#
# The sentinel approach avoids fragile :nth-child selectors: we inject a hidden
# <div id="tb-navstart"> via st.markdown, then CSS :has(#tb-navstart) + stHorizontalBlock
# gives us a precise handle on just the nav row without touching anything else.

# Sentinel — CSS ribbon targets the stHorizontalBlock that immediately follows this
st.markdown('<div id="tb-navstart"></div>', unsafe_allow_html=True)

# Widths, left to right: brand · Home · the five group popovers · spacer ·
# search · sign-in. The current-page label used to live here; it is a breadcrumb,
# and it now sits on the strip below the bar where a breadcrumb belongs.
#
# The quote strip is NOT in this row: width here is scarce (at these weights
# "Portfolio & Risk ▾" is already near its label width) and three quotes need
# ~330px that would have to come out of the group labels. It rides the
# breadcrumb line below instead, which is mostly empty.
#
# The search column is wide (2.0) because the typeahead's dropdown is the width
# of its column, and at 1.15 the company names were cut to a few characters with
# a horizontal scrollbar under them. The width comes out of the brand and the
# spacer, not the group labels — those are already near their text width.
_nav = st.columns([1.4, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0, 0.1, 2.0, 0.95],
                   gap="small", vertical_alignment="center")

with _nav[0]:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:8px;height:48px;">'
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
        'stroke="#ea580c" stroke-width="2.4" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8"/>'
        '<path d="M21 7h-5v5"/></svg>'
        '<span style="font-size:15px;font-weight:700;color:#f8fafc;'
        'letter-spacing:-0.01em;white-space:nowrap;">'
        'Trading<span style="color:#ea580c;"> Bramha</span></span>'
        '</div>',
        unsafe_allow_html=True,
    )

with _nav[1]:
    if st.button("Home", key="nav_Home", use_container_width=True,
                 type="primary" if st.session_state["current_page"] == "Home" else "secondary"):
        st.session_state["current_page"] = "Home"
        st.rerun()

for _i, (_gname, _gpages) in enumerate(PAGE_GROUPS.items()):
    with _nav[2 + _i]:
        _active_here = st.session_state["current_page"] in _gpages
        with st.popover(f"{_gname} ▾", use_container_width=True,
                        type="primary" if _active_here else "secondary"):
            for _p in _gpages:
                _is_active = st.session_state["current_page"] == _p
                if st.button(_p, key=f"nav_{_p}", use_container_width=True,
                             help=PAGE_BLURBS.get(_p),
                             type="primary" if _is_active else "secondary"):
                    st.session_state["current_page"] = _p
                    st.rerun()

# Sign-in sits at the far right of the ribbon, where a sign-in belongs and where
# it is out of the way of a tool that no longer requires it.
with _nav[8]:
    _search_control()

with _nav[9]:
    _signin_control()

# ── Breadcrumb + status strip ────────────────────────────────────
# One 30px line under the bar: where you are on the left, whether the data is
# current on the right. Rendered as a single markdown flex row rather than
# st.columns — it is static text, and a column row would cost another
# stHorizontalBlock plus the vertical block's 16px gap on both sides of it.
#
# The clock is as-of-render: it moves on the next rerun, not on a timer. A
# self-updating clock would need an autorefresh, and paying a full script rerun
# per second to animate a timestamp is not a trade worth making.
_cp = st.session_state["current_page"]
_crumb_group = next((g for g, ps in PAGE_GROUPS.items() if _cp in ps), None)
# Home is the trail root, so on Home itself the trail is just "Home" — not
# "Home › Home". The group sits between only when the page has one.
_lead = [] if _cp == "Home" else ["Home"] + ([_crumb_group] if _crumb_group else [])
_trail = "".join(
    f'<span style="color:{_T["text_muted"]};">{_seg}</span>'
    f'<span style="color:{_T["absent"]};margin:0 6px;">›</span>'
    for _seg in _lead
)
_mkt_state, _mkt_dot, _mkt_label = _market_status()

# Refresh cadence follows the session: a minute while the tape is running,
# a quarter-hour once it is not. Passing the bucket in (rather than setting a
# short ttl) is what lets one cached function have two cadences.
_q_bucket = int(_time.time() // (60 if _mkt_state in ("LIVE", "PRE-OPEN") else 900))
_quote_html = ""
for _lbl, _val, _chg in _ribbon_quotes(_q_bucket):
    if _val is None:
        _quote_html += (
            f'<span style="display:inline-flex;gap:5px;align-items:baseline;">'
            f'<span style="color:{_T["text_muted"]};font-weight:600;">{_lbl}</span>'
            f'<span style="color:{_T["absent"]};">—</span></span>'
        )
        continue
    _tone = _T["good"] if _chg >= 0 else _T["risk"]
    _num = f"{_val:,.0f}" if _lbl != "VIX" else f"{_val:,.2f}"
    _quote_html += (
        f'<span style="display:inline-flex;gap:5px;align-items:baseline;">'
        f'<span style="color:{_T["text_muted"]};font-weight:600;">{_lbl}</span>'
        f'<span style="color:{_T["text"]};font-variant-numeric:tabular-nums;">{_num}</span>'
        f'<span style="color:{_tone};font-variant-numeric:tabular-nums;">{_chg:+.2f}%</span>'
        f'</span>'
    )

st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:space-between;'
    f'gap:16px;height:30px;font-size:11.5px;margin:0;'
    f'border-bottom:1px solid {_T["border"]};">'
    f'  <div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
    f'    {_trail}'
    f'    <span style="color:{_T["text"]};font-weight:600;">{_cp}</span>'
    f'  </div>'
    f'  <div style="display:flex;align-items:center;gap:14px;white-space:nowrap;'
    f'color:{_T["text_muted"]};">'
    f'    {_quote_html}'
    f'    <span style="color:{_T["border_strong"]};">|</span>'
    f'    <span style="display:inline-flex;align-items:center;gap:5px;">'
    f'      <span style="width:6px;height:6px;border-radius:50%;'
    f'background:{_mkt_dot};display:inline-block;"></span>{_mkt_label}</span>'
    f'    <span style="color:{_T["border_strong"]};">|</span>'
    f'    <span>{_batch_freshness()}</span>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── ⌘K / Ctrl-K ───────────────────────────────────────────────────
# Streamlit gives no keyboard API, and st.markdown strips <script>, so the only
# way to bind a global shortcut is a zero-height component iframe reaching into
# the parent document. Same-origin, so this is allowed — but it is a hack on
# Streamlit's DOM, and it is written to FAIL SILENTLY: if the markup changes
# under it, the shortcut stops working and the box still does.
#
# It finds the box by its aria-label rather than a generated key, because
# Streamlit's element keys are not stable selectors.
components.html(
    """
    <script>
    (function () {
      const doc = window.parent && window.parent.document;
      if (!doc || doc.__tbSearchHotkey) return;   // bind once per page load
      doc.__tbSearchHotkey = true;
      // Enter commits the box. Streamlit does this natively on Enter, and this
      // listener is belt-and-braces: a blur commits too, and if the native
      // path already fired, the value is unchanged so nothing happens twice.
      // Kept because Enter could NOT be verified from this side — the test
      // harness delivers character keys to the page but not Enter or Ctrl-K,
      // which is also why ⌘K needed a human to confirm it.
      doc.addEventListener('keydown', function (e) {
        if (e.key !== 'Enter') return;
        const el = doc.activeElement;
        if (!el || el.getAttribute('aria-label') !== 'Symbol') return;
        el.blur();   // fallback box only; the component handles its own Enter
      });

      doc.addEventListener('keydown', function (e) {
        const combo = (e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey);
        // Chrome also owns Ctrl/Cmd-K (omnibox search), so the question was
        // whether preventDefault gets there first. It does — ⌘K confirmed
        // working in a real browser, 2026-09-05. "/" stays as a second binding
        // anyway: it needs no modifier and no browser claims it. Ignored while
        // typing, or the key would be unusable in every text field here.
        const el = doc.activeElement;
        const typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA'
                              || el.isContentEditable);
        const slash = e.key === '/' && !typing && !e.metaKey && !e.ctrlKey && !e.altKey;
        if (!combo && !slash) return;
        // The box lives inside the typeahead's component iframe now. Same
        // origin (Streamlit serves it), so we can reach in; if that ever stops
        // being true, contentDocument throws and the key falls through to the
        // browser rather than dying here.
        let box = null;
        try {
          for (const f of doc.querySelectorAll('iframe')) {
            const inner = f.contentDocument && f.contentDocument.getElementById('box');
            if (inner) { box = inner; break; }
          }
        } catch (err) { return; }
        if (!box) box = doc.querySelector('input[aria-label="Symbol"]');  // fallback box
        if (!box) return;            // markup moved — leave the key to the browser
        e.preventDefault();
        box.focus();
        box.select();
      });
    })();
    </script>
    """,
    height=0,
)

current_page = st.session_state["current_page"]

# A page that no longer exists must not render a blank screen. This happens to a
# session that was open across a deploy which removed a page — "Trending Stocks"
# folded into Home on 2026-09-04 — where session_state still names the old page
# and no router branch matches it.
_VALID_PAGES = {"Home", *(p for g in PAGE_GROUPS.values() for p in g)}
if current_page not in _VALID_PAGES:
    current_page = st.session_state["current_page"] = "Home"

# Background-job status panel (see ui_jobs). Long tasks (funnel run, sentiment
# refresh) run on a per-session SERIAL queue off the script thread, so clicking a
# second action while one runs QUEUES it instead of cancelling the running one.
# The panel is drawn here (top); `ui_jobs.autorefresh()` polls at the very bottom.
ui_jobs.render_panel()


# ──────────────────────────────────────────────────────────────────────────────
# Pagination helper — wraps st.dataframe with prev/next page controls.
# page_size=25 keeps result tables legible without scrolling; any table with
# ≤ page_size rows renders as a plain dataframe (no controls shown).
# ──────────────────────────────────────────────────────────────────────────────

def _paginated_df(df: "pd.DataFrame", key: str, page_size: int = 25, **kwargs) -> None:
    """Render a DataFrame with pagination when it exceeds page_size rows."""
    n = len(df)
    if n <= page_size:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)
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
    st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True, **kwargs)
    st.caption(f"Page {st.session_state[_pk]}/{n_pages} · rows {start + 1}–{end} of {n}")


# ──────────────────────────────────────────────────────────────────────────────
# Cached wrappers around network-hitting functions (avoid re-fetching on every
# Streamlit rerun caused by widget interaction elsewhere on the page)
# ──────────────────────────────────────────────────────────────────────────────

def _drop_unusable_bars(df):
    """Drop rows that carry no close price.

    During a live session yfinance returns a bar for TODAY with volume but NaN
    OHLC. A single NaN last close then poisons everything downstream at once:
    the price header renders ₹nan, `score_minervini` fails every comparison
    against it (0/8), the CANSLIM RS reads +nan%, and EW confidence collapses.

    This exact class of bug has been fixed three separate times downstream in
    this repo — `scan_pead`, `volume_profile`, and the Opportunity Hub momentum
    ranking each grew their own `dropna`. Doing it once at the fetch means every
    page inherits the fix instead of the next consumer rediscovering it.
    """
    if df is None or "close" not in getattr(df, "columns", []):
        return df
    return df[df["close"].notna()]


@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_ohlcv(symbol: str, days: int = 300, enforce_liquidity: bool = True):
    """Daily bars for one symbol, via VolumeFetcher then screener_pipeline.

    `enforce_liquidity=False` drops the 100k 10-day average volume floor. That
    floor belongs to SCANNING — it keeps names you cannot trade out of a
    2,000-symbol sweep — and both fetchers applied it to every caller, so a page
    that had been handed one symbol by name returned "no usable data" for a
    stock yfinance serves perfectly well. CENTUM (~55k/day) reported as "not on
    yfinance" while the Opportunity Hub was linking to it, which is the same
    app refusing to open a door it just pointed at.

    Bar-count and NaN validation still apply either way: those say there is no
    data, not that the data is not worth scanning.
    """
    # Try enhanced volume fetcher first
    try:
        volume_fetcher = vf.VolumeFetcher(verbose=False)
        if not enforce_liquidity:
            volume_fetcher.MIN_VOLUME = 0   # instance attr shadows the class floor
        df = volume_fetcher.fetch_with_volume(symbol, days=days, validate=True)
        if df is not None:
            return _drop_unusable_bars(df)
    except Exception as e:
        _log.warning("VolumeFetcher error for %s: %s", symbol, e)

    # Fallback to screener_pipeline
    return _drop_unusable_bars(
        sp.fetch_ohlcv(symbol, days=days,
                       min_volume=None if enforce_liquidity else 0))


def _thin_volume_note(df, symbol: str) -> None:
    """Warn when a single-symbol page is looking at a name below the screen floor.

    The gate is off for these pages, which means the number has to be visible
    instead: an analysis of a stock trading 55k shares a day is not wrong, but
    every level on it is worth less than the same level on a liquid name.
    """
    try:
        avg_vol = float(df["volume"].tail(10).mean())
    except Exception:
        return
    if avg_vol >= sp.MIN_VOLUME:
        return
    st.warning(
        f"**{symbol}** trades ~{avg_vol:,.0f} shares/day over the last 10 "
        f"sessions — below the {sp.MIN_VOLUME:,} floor the screeners use, so it "
        f"never reaches a scan. Everything below is computed normally; treat "
        f"levels as indicative and assume slippage.",
        icon="⚠",
    )


def _scanner_fetch_fn(scanner_name: str):
    """Fetch fn for run_scanner. Scanners flagged ``needs_full_history`` (ATH /
    IPO-base breakout) get the full listing history; every other scanner keeps the
    default ~300-bar window. Used by both the Scanner Hub and the Opportunity Hub."""
    if sc.SCANNERS.get(scanner_name, {}).get("needs_full_history"):
        return lambda s: cached_fetch_ohlcv(s, days=6000)
    return cached_fetch_ohlcv


@st.cache_data(ttl=1800, show_spinner=False)
def cached_fetch_bhavcopy_universe(top_n: int) -> list[str]:
    return sp.fetch_bhavcopy_top_volume(top_n)


# ── Market-health gate (Crash-Proof Filter A) caches ──────────────────────────
#: Basket size for the two stock-level conditions. 60 liquid names is enough for
#: a breakout sample without another 200-symbol fan-out at Yahoo.
MH_BASKET_SIZE = 60


@st.cache_data(ttl=900, show_spinner=False)
def cached_health_indices():
    """^NSEI + ^INDIAVIX for conditions 1 and 5. Two fetches per 15 min."""
    return mh.fetch_indices()


@st.cache_data(ttl=1800, show_spinner=False)
def cached_health_basket(size: int):
    """Basket frames for conditions 3 and 4, plus how many were requested.

    Uses sp.fetch_ohlcv directly rather than cached_fetch_ohlcv: the loader fans
    out across threads, and calling an st.cache_data function off the main
    thread has no ScriptRunContext. This whole result is cached instead.
    """
    symbols = sp.fetch_bhavcopy_top_volume(size)
    frames = mh.load_basket(symbols, lambda s: sp.fetch_ohlcv(s, days=260))
    return frames, len(symbols)


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


@st.cache_data(ttl=3600, show_spinner=False)
def cached_oi_momentum_scan(include_no_read: bool = False):
    """Stock-futures price-vs-OI readings for the most recent settled session.

    Cached for an hour because the underlying F&O bhavcopy is END-OF-DAY — it
    does not change intraday, so a shorter TTL would only re-download the same
    ~1.2 MB zip. Returns (records, trade_date); an empty list with a None date
    means nothing was reachable in the lookback window.
    """
    raw, trade_date = cached_fo_bhavcopy_raw()
    if raw.empty:
        return [], None
    stf = raw[raw["FinInstrmTp"] == oim.STOCK_FUTURE].copy()
    if stf.empty:
        return [], None
    return oim.scan(stf, trade_date, include_no_read=include_no_read,
                    volume_baseline=cached_volume_baseline()), trade_date


@st.cache_data(ttl=3600, show_spinner=False)
def cached_oi_momentum_index():
    """The same four quadrants over INDEX futures, on index floors.

    A separate cached call, not extra rows on the stock scan: index and stock OI
    percentages are not comparable (an index 3% build is an ordinary day where a
    stock's would be strong), and there are five index underlyings against ~210
    stocks. Kept apart for the same reason pcr.py keeps the two option classes
    apart.
    """
    raw, trade_date = cached_fo_bhavcopy_raw()
    if raw.empty:
        return [], None
    idf = raw[raw["FinInstrmTp"] == oim.INDEX_FUTURE].copy()
    if idf.empty:
        return [], None
    base = oim.fetch_volume_baseline(before=trade_date,
                                     instrument=oim.INDEX_FUTURE)
    return oim.scan_index(idf, trade_date, include_no_read=True,
                          volume_baseline=base), trade_date


@st.cache_data(ttl=3600, show_spinner=False)
def cached_volume_baseline():
    """Per-symbol median futures volume over the sessions BEFORE the scan date.

    The expensive one on this page: it downloads five extra settled bhavcopies
    to build a per-symbol participation baseline, which is the only way to say
    whether a stock traded more than IT normally does. Cached for an hour like
    everything else here — the files are settled and never change — so the cost
    lands on one page load per hour, not every rerun.

    Returns an empty baseline on any failure, which the scan treats as
    participation UNMEASURED rather than normal.
    """
    _raw, trade_date = cached_fo_bhavcopy_raw()
    if trade_date is None:
        return {"median": {}, "sessions": 0, "dates": []}
    return oim.fetch_volume_baseline(before=trade_date)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fo_bhavcopy_raw():
    """The whole F&O bhavcopy once per hour, futures AND option chains.

    Both the OI-momentum scan (STF rows) and PCR (STO/IDO rows) read this file.
    Caching the raw frame rather than each consumer's slice is what makes the
    "one download, two consumers" claim in pcr.py actually true — otherwise the
    same ~1.2 MB zip would be pulled twice per page load.
    """
    return oim.fetch_fo_bhavcopy_raw()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_pcr():
    """Stock and index PCR tables + the stock cross-sectional calibration.

    Returns a dict keyed by symbol for the stock side, since the OI-momentum
    table joins on symbol. Index readings stay separate and unbanded — see
    pcr.py on why the two classes cannot share a calibration.
    """
    raw, _day = cached_fo_bhavcopy_raw()
    if raw is None or raw.empty:
        return {}, None, pd.DataFrame()
    stock = pcr.build_pcr_table(raw, pcr.CLASS_STOCK)
    index = pcr.build_pcr_table(raw, pcr.CLASS_INDEX)
    calib = pcr.calibrate_stock(stock)
    by_sym = {r["symbol"]: r for r in stock.to_dict("records")}
    return by_sym, calib, index


@st.cache_data(ttl=1800, show_spinner=False)
def cached_normalized_deals():
    """Today's NSE+BSE bulk & block deals, flattened to one frame. Cached 30 min
    because the feeds update through the day. Feeds the Smart-Money Layer-4 panel
    (per-symbol slice → block_deal_intel.summarize_company)."""
    return bdi.normalize_deals(
        imi.fetch_nse_bulk_deals(), imi.fetch_nse_block_deals(),
        imi.fetch_bse_bulk_deals(), imi.fetch_bse_block_deals(),
    )


@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_nifty50(days: int = 300):
    # Same forming-bar hazard as the per-symbol fetch: a NaN last close on the
    # index turns every relative-strength reading into nan.
    return _drop_unusable_bars(sp.fetch_nifty50(days=days))


@st.cache_data(ttl=300, show_spinner=False)
def cached_latest_sentiment():
    """Newest PERSISTED sentiment reading, for the overview ribbon.

    Deliberately a DB read, never a compute: compute_sentiment() takes ~24s
    (bhavcopy + sector indices + PMax), and the ribbon renders on every single
    Streamlit rerun. Returns None when nothing has been persisted yet — the
    verdict engine treats that as a caution flag rather than a green light.
    Refreshing happens on the Market Sentiment page, which owns that button.
    """
    try:
        hist = senti.history(days=1)
        if hist.empty:
            return None
        row = hist.iloc[-1]
        return {
            "reading_date": row["reading_date"].date().isoformat(),
            "score": float(row["score"]),
            "band":  row["band"],
            "inputs": json.loads(row["inputs_json"]),
        }
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_fundamentals(symbol: str) -> dict:
    return council.fetch_fundamentals(symbol)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fundamentals_deep(symbol: str) -> dict:
    """FR-1 statement layer. Four yfinance statement calls, so cache it hard —
    annual/quarterly filings change quarterly at best, never intraday."""
    return fdeep.derive_fundamentals(symbol)


def resolve_screener_sessionid() -> str | None:
    """Screener.in sessionid, in priority order: (1) auto-grabbed from a local
    browser cookie, (2) the value manually saved in the DB (Plan B — for when
    the browser auto-grab finds nothing). None if neither is available."""
    try:
        sid, _browser = bch.get_screener_sessionid()
        if sid:
            return sid
    except Exception:
        pass
    try:
        import portfolio_db as _db
        return _db.get_setting("screener_sessionid") or None
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_red_flags(symbol: str, sessionid: str | None) -> dict:
    """Cached core, keyed on (symbol, sessionid) so saving a sessionid (Plan B)
    invalidates the entry and the screener-gated checks re-run."""
    _own = cached_nse_ownership(symbol)
    _pledge = ((_own["pledge_pct"], _own["pledge_as_of"])
               if _own.get("pledge_pct") is not None else None)
    return rflags.evaluate(symbol, cached_fetch_fundamentals(symbol),
                           cached_fundamentals_deep(symbol), sessionid,
                           promoter_series=_own["series"],
                           promoter_pledge=_pledge,
                           auditor_scan=cached_nse_auditor_scan(symbol))


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def cached_nse_auditor_scan(symbol: str):
    """Plan A (auditor) — scan free NSE announcements for an auditor-resignation
    or adverse/qualified-opinion filing. Returns (state, detail, as_of) or None
    on import/lookup failure (→ the check stays NOT_CHECKED, no source)."""
    try:
        import nse_announcements as _na
        return _na.scan_auditor(symbol)
    except Exception:
        return None


def cached_red_flags(symbol: str) -> dict:
    """FR-4 checks. The session lookup is best-effort — with no cookie the
    screener-gated checks come back NOT_CHECKED, the honest answer, and the user
    can paste a sessionid via the 'Unlock screener.in checks' panel."""
    return _cached_red_flags(symbol, resolve_screener_sessionid())


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_nse_ownership(symbol: str) -> dict:
    """Free/official promoter data for the FR-4 checks (Plan A — no screener.in
    cookie): promoter-holding history [(period, pct)] oldest→newest PLUS the
    latest promoter-pledge %. Disk cache first (ownership_cache), then a single
    bounded live NSE fetch if the cache is thin or lacks pledge."""
    import datetime as _dt
    out = {"series": [], "pledge_pct": None, "pledge_as_of": None}
    try:
        import ownership_cache as _oc
        import nse_shareholding_fetch as _nsf
    except Exception:
        return out

    def _key(period):
        d = _nsf._period_date(period)
        return d or _dt.datetime.min

    q = (_oc.load(symbol).get("quarters") or {})
    disk = sorted(((p, v) for p, v in q.items()), key=lambda t: _key(t[0]))
    series = [(p, float(v["promoter"])) for p, v in disk
              if isinstance(v.get("promoter"), (int, float))]
    pledge_pct, pledge_as_of = None, None
    if disk:
        _latest_p, _latest_v = disk[-1]
        if isinstance(_latest_v.get("promoter_pledge_pct"), (int, float)):
            pledge_pct, pledge_as_of = float(_latest_v["promoter_pledge_pct"]), _latest_p
    if len(series) >= 2 and pledge_pct is not None:
        return {"series": series, "pledge_pct": pledge_pct, "pledge_as_of": pledge_as_of}

    try:                                    # single bounded live fetch (cached here)
        res = _nsf.fetch_ownership(symbol, quarters=5)
        if res:
            qs = sorted(res.get("quarters", []), key=lambda d: _key(d.get("period")))
            live = [(d.get("period"), float(d["promoter"])) for d in qs
                    if isinstance(d.get("promoter"), (int, float))]
            if len(live) >= 2:
                series = live
            latest = res.get("latest") or (qs[-1] if qs else None)
            if latest and isinstance(latest.get("promoter_pledge_pct"), (int, float)):
                pledge_pct, pledge_as_of = float(latest["promoter_pledge_pct"]), latest.get("period")
    except Exception:
        pass
    return {"series": series, "pledge_pct": pledge_pct, "pledge_as_of": pledge_as_of}


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


@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_benchmark(ticker: str = "^NSEI") -> pd.DataFrame | None:
    """NIFTY 50 for the RRG, fetched the same way as the sector frames.

    Deliberately not `cached_fetch_nifty50()`: that returns 300 rows with a
    lowercase `close`, while the sector frames carry 2y with yfinance's `Close`.
    The RRG divides one by the other, so they have to be the same shape and the
    same length — a 300-row benchmark would silently truncate every tail.
    """
    import yfinance as yf
    try:
        df = yf.download(ticker, period="2y", interval="1d",
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        return df
    except Exception:
        return None


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


def _cr(v: float | None, currency: str | None = "INR") -> str | None:
    """Indian-crore formatting for statement figures (1 Cr = 1e7).

    Non-INR reporting currencies are left in millions rather than silently
    converted — yfinance reports some cross-listed names in USD and a crore
    label on a dollar figure would be wrong, not just unusual.
    """
    if v is None:
        return None
    if (currency or "INR").upper() != "INR":
        return f"{v/1e6:,.0f}M {currency}"
    return f"₹{v/1e7:,.0f} Cr"


def _q(v: float | None, suffix: str = "", dp: int = 2) -> str | None:
    """Format a number, preserving None so stat_card can render DATA N/A."""
    return None if v is None else f"{v:,.{dp}f}{suffix}"


def render_fundamental_header(symbol: str, df: pd.DataFrame,
                              fundamentals: dict, deep: dict) -> None:
    """FR-1 — sticky identity header + the 9-metric strip, plus the growth and
    quality figures that only exist now that statements are fetched.

    Tone discipline: colour is applied only where this repo already has a stated
    threshold (D/E, ROE, ROCE — the High-Growth Screener sliders and the
    multibagger query use exactly these floors). Valuation bands (P/E, P/B) are
    deliberately left neutral here: band-scoring is FR-2's job and must live in
    ONE shared scorer feeding both these figures and the radar's axes, or the
    page grows a fourth competing "overall" verdict.
    """
    f, d = fundamentals or {}, deep or {}
    cur = d.get("currency") or "INR"

    price = float(df["close"].iloc[-1])
    prev = float(df["close"].iloc[-2]) if len(df) > 1 else price
    chg = (price / prev - 1) * 100 if prev else 0.0
    as_of = str(df.index[-1])[:10]
    # A move that rounds to 0.00% is flat, not a down day — an unqualified ▼ on
    # "-0.00%" reads as a rendering fault.
    if chg > 0.005:
        chg_arrow, chg_col = "▲", rs.TOKENS["good"]
    elif chg < -0.005:
        chg_arrow, chg_col = "▼", rs.TOKENS["risk"]
    else:
        chg_arrow, chg_col = "•", rs.TOKENS["text_muted"]

    # ── Identity header ──
    chips = []
    if f.get("sector"):
        chips.append(rs.chip(f["sector"], "info"))
    if f.get("industry"):
        chips.append(rs.chip(f["industry"], "neutral"))
    mcap = f.get("market_cap")
    if mcap:
        # NSE convention: >₹20,000 Cr large, ₹5,000-20,000 Cr mid, below small.
        cr = mcap / 1e7
        band = "LARGE CAP" if cr >= 20000 else ("MID CAP" if cr >= 5000 else "SMALL CAP")
        chips.append(rs.chip(band, "neutral"))
    cov = d.get("coverage") or {}
    if cov:
        cov_tone = "good" if cov.get("have", 0) >= cov.get("total", 11) - 2 else "warn"
        chips.append(rs.chip("STATEMENT FIELDS", cov_tone,
                             f"{cov.get('have', 0)}/{cov.get('total', 0)}"))
    if not d.get("available"):
        chips.append(rs.chip("NO STATEMENTS", "absent"))

    st.markdown(
        f"""
        <div style="position:sticky;top:0;z-index:99;background:{rs.TOKENS['surface_warm']};
                    border:1px solid {rs.TOKENS['border']};border-radius:12px;
                    padding:11px 15px;margin:4px 0 10px 0;">
          <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;">
            <span style="font-family:Georgia,'Times New Roman',serif;font-size:23px;
                         font-weight:700;color:{rs.TOKENS['accent']};">{symbol}</span>
            <span style="font-size:13px;color:{rs.TOKENS['text_body']};">
              {d.get('long_name') or ''}</span>
            <span class="tb-mono" style="font-size:26px;font-weight:700;
                         color:{rs.TOKENS['text']};margin-left:auto;">₹{price:,.2f}</span>
            <span class="tb-mono" style="font-size:14px;font-weight:700;color:{chg_col};">
              {chg_arrow} {chg:+.2f}%</span>
          </div>
          <div style="margin-top:7px;">{''.join(chips)}</div>
          <div class="tb-micro" style="margin-top:2px;">
            PRICE AS OF {as_of} · STATEMENTS AS OF {d.get('as_of') or '—'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 9-metric strip ──
    d2e, roe, roce = f.get("debt_to_equity"), f.get("roe"), d.get("roce")
    # 52W range is computed from the loaded frame, but only when the frame
    # actually covers a year. On a 3M lookback a 60-bar high/low labelled
    # "52W RANGE" would be a quietly wrong number, so it renders DATA N/A.
    if len(df) >= 252:
        hi = float(df["high"].tail(252).max())
        lo = float(df["low"].tail(252).min())
    else:
        hi = lo = None
    cells = [
        rs.stat_card("P / E", _q(f.get("pe"), "×")),
        rs.stat_card("P / B", _q(f.get("pb"), "×")),
        # yfinance reports debtToEquity as a percentage (50 = 0.50×).
        rs.stat_card("D / E", None if d2e is None else f"{d2e/100:,.2f}×",
                     tone=("good" if (d2e is not None and d2e < 50)
                           else "risk" if (d2e is not None and d2e > 100) else "neutral")),
        rs.stat_card("ROE", _q(roe, "%"),
                     tone="good" if (roe is not None and roe >= 15) else "neutral"),
        rs.stat_card("ROCE", _q(roce, "%"),
                     sub=None if d.get("roce_prev") is None else f"prev {d['roce_prev']:.1f}%",
                     tone="good" if (roce is not None and roce >= 15) else "neutral"),
        rs.stat_card("EPS TTM", _q(f.get("eps_ttm") if f.get("eps_ttm") is not None
                                   else d.get("eps_ttm"))),
        rs.stat_card("DIV YIELD", _q(f.get("dividend_yield"), "%")),
        rs.stat_card("MKT CAP", _cr(mcap, cur)),
        rs.stat_card("52W RANGE",
                     None if (hi is None or lo is None) else f"{lo:,.0f}–{hi:,.0f}"),
    ]
    st.markdown(rs.section("Valuation & Quality"), unsafe_allow_html=True)
    # Both rows on a 5-column grid: the second row holds 4 cards and simply
    # leaves the fifth slot empty, so card widths stay identical down the page.
    st.markdown(rs.strip(cells[:5], cols=5) + rs.strip(cells[5:], cols=5),
                unsafe_allow_html=True)

    # ── Statement-derived figures (the layer FR-1 adds) ──
    if d.get("available"):
        g = [
            rs.stat_card("REV CAGR 3Y", _q(d.get("revenue_cagr_3y"), "%"),
                         sub=_q(d.get("revenue_cagr_5y"), "% (5Y)") or "5Y n/a"),
            rs.stat_card("PROFIT CAGR 3Y", _q(d.get("profit_cagr_3y"), "%"),
                         sub=_q(d.get("profit_cagr_5y"), "% (5Y)") or "5Y n/a"),
            rs.stat_card("NET MARGIN", _q(d.get("net_margin"), "%"),
                         sub=_q(d.get("opm"), "% OPM")),
            rs.stat_card("FREE CASH FLOW", _cr(d.get("fcf"), cur),
                         sub=(f"{d['fcf_negative_streak']}y negative streak"
                              if d.get("fcf_negative_streak") else None),
                         tone="risk" if d.get("fcf_negative_streak") else "neutral"),
            rs.stat_card("DEBTOR DAYS", _q(d.get("debtor_days"), "d", 0),
                         sub=_q(d.get("wc_days"), "d working cap", 0)),
        ]
        st.markdown(rs.section("Growth & Quality — from financial statements"),
                    unsafe_allow_html=True)
        st.markdown(rs.strip(g, cols=5), unsafe_allow_html=True)
        miss = (d.get("coverage") or {}).get("missing") or []
        st.caption(
            f"{d.get('annual_periods', 0)} annual / {d.get('quarterly_periods', 0)} "
            f"quarterly periods available from yfinance"
            + (f" · not computable: {', '.join(miss)}" if miss else "")
            + " · a 5Y CAGR needs six annual columns; fewer means it is genuinely "
              "unavailable, not zero."
        )
    else:
        st.markdown(
            rs.callout("No financial statements.",
                       "yfinance returned no income statement, balance sheet or "
                       "cash-flow for this symbol — common for newly-listed and "
                       "thin BSE/SME names. Growth, ROCE and working-capital "
                       "figures are not shown rather than estimated.",
                       tone="absent"),
            unsafe_allow_html=True)


def _axis_tone(score: int | None) -> str:
    """Score band -> semantic tone. Absent scores are grey, never a middling
    amber that would read as 'average' when it means 'unknown'."""
    if score is None:
        return "absent"
    if score >= 70:
        return "good"
    if score >= 45:
        return "warn"
    return "risk"


def render_fundamental_signals(score: dict) -> None:
    """FR-2 — six signal donuts, the coverage dial, and the good-business vs
    bad-entry split, all off the one shared scorer in fundamental_score.py.

    No overall number is rendered here on purpose. The page already carries the
    M1 technical Overall Rating and the council verdict; a fourth /100 badged
    "fundamental" would be read as a competing master score. The split is two
    words instead.
    """
    axes, cov = score.get("axes") or {}, score.get("coverage") or {}
    biz, entry = score.get("business") or {}, score.get("entry") or {}

    st.markdown(rs.section("Fundamental signals"), unsafe_allow_html=True)

    # ── Verdict chips + coverage dial ──
    biz_tone = _axis_tone(biz.get("score"))
    entry_tone = _axis_tone(entry.get("score"))
    chips = (
        rs.chip("Business", biz_tone, biz.get("word") or rs.NA) +
        rs.chip("Entry", entry_tone, entry.get("word") or rs.NA)
    )
    have, total = cov.get("have", 0), cov.get("total", 0)
    dial = rs.donut(f"{have}/{total}" if total else None, "Scored inputs",
                    pct=(have / total * 100) if total else None,
                    tone="good" if (total and have / total >= 0.8) else "warn")
    st.markdown(
        rs.card(
            f'<div style="display:flex;align-items:center;gap:18px;">'
            f'  <div style="flex:1;">{chips}'
            f'    <div style="font-size:12px;color:{rs.TOKENS["text_body"]};margin-top:6px;">'
            f'      A good business and a good entry price are separate questions — '
            f'      this page answers them separately and never merges them into one '
            f'      number. Fundamental read only; the technical Overall Rating '
            f'      /100 is a different lens.</div>'
            f'  </div>{dial}</div>'
        ),
        unsafe_allow_html=True,
    )

    # ── Six donuts ──
    cells = []
    for name in fscore.AXES:
        a = axes.get(name) or {}
        s = a.get("score")
        cells.append(
            f'<div style="flex:1;min-width:120px;">'
            f'{rs.donut(None if s is None else str(s), a.get("label", name), a.get("verdict"), pct=s, tone=_axis_tone(s))}'
            f'<div style="font-size:9.5px;color:{rs.TOKENS["text_muted"]};'
            f'text-align:center;margin-top:2px;line-height:1.35;">'
            f'{a.get("drivers") or "no inputs available"}</div></div>'
        )
    st.markdown(
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 6px 0;">'
        f'{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Bands are calibrated for NSE listed equity and live in one place "
        "(`fundamental_score.py`) so this page and the fundamental radar can "
        "never disagree. Earnings Consistency measures **realised** results "
        "(profitable years, growth years, margin stability) — consensus "
        "estimates have no free NSE source, so this is not a beat/miss record."
    )


@st.cache_data(ttl=3600, show_spinner=False)
def cached_peer_score(symbol: str) -> dict:
    """One peer's six axes, through the SAME scorer the anchor uses. Cached at the
    same TTL as the statement layer it reads — the peer table's cost is entirely
    network, and a peer of one stock is usually a peer of the next one too."""
    return fscore.score_all(council.fetch_fundamentals(symbol),
                            fdeep.derive_fundamentals(symbol))


def render_peer_comparison(anchor: str) -> None:
    """FP-1 — the anchor against its industry peers, on the same six axes.

    Lazy on purpose. Twelve peers is ~48 yfinance calls, which would make it the
    slowest thing on this page; it therefore sits behind a button and never runs
    on the default Analyze path. See wiki/analyses/Analyzer-Radar-Peers-Roadmap.md.
    """
    st.markdown(rs.section("Peer comparison"), unsafe_allow_html=True)
    key = f"peers_{anchor}"

    if not st.session_state.get(key):
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("Compare peers", key=f"btn_{key}", use_container_width=True):
                st.session_state[key] = True
                st.rerun()
        with c2:
            st.caption(
                f"Scores up to {pcmp.MAX_PEERS} same-industry names through the same "
                "scorer as the donuts above, so 'cheaper than its peers' means exactly "
                "what Valuation means. Runs on request — it is several dozen network "
                "calls."
            )
        return

    prog = st.progress(0.0, text="Resolving peer group...")
    try:
        res = pcmp.build(
            anchor, cached_peer_score,
            tag_progress=lambda d, t: prog.progress(min(d / max(t, 1), 1.0) * 0.6,
                                                    text=f"Tagging industries {d}/{t}..."),
            score_progress=lambda d, t: prog.progress(0.6 + min(d / max(t, 1), 1.0) * 0.4,
                                                      text=f"Scoring peers {d}/{t}..."),
        )
    except Exception as exc:
        prog.empty()
        st.markdown(rs.callout("Peer comparison failed.", str(exc), tone="risk"),
                    unsafe_allow_html=True)
        return
    prog.empty()

    if not res.get("ok"):
        st.markdown(
            rs.callout(f"No peer group for {anchor}.",
                       (res.get("reason") or "")
                       + " Industry tags come from yfinance and are coarse or absent "
                         "for many NSE mid- and small-caps; a thin group is a data "
                         "limit, not a verdict on the company.",
                       tone="absent"),
            unsafe_allow_html=True)
        return

    df, med = res["table"], res["median"] or {}

    # ── What group is this, and how honest is it ──
    widened = res.get("group_level") == "family"
    chips = (
        rs.chip("Group", "info", res.get("group_label")) +
        rs.chip("Names", "neutral", str(len(df))) +
        (rs.chip("Widened", "warn", f"only {res['n_same_industry']} in {res['industry']}")
         if widened else "")
    )
    st.markdown(
        rs.card(
            f'{chips}<div style="font-size:12px;color:{rs.TOKENS["text_body"]};'
            f'margin-top:6px;">'
            + (f'yfinance tags <b>{anchor}</b> as <i>{res["industry"]}</i>, which holds '
               f'only {res["n_same_industry"]} other NSE name(s) — too thin to compare '
               f'against, so the group was widened one rung to <b>{res["group_label"]}</b>. '
               'Read it as a sector-adjacent group, not a like-for-like one. '
               if widened else
               f'Peers are the NSE names yfinance tags <i>{res["industry"]}</i>, '
               'ranked by market cap. ')
            + 'Fundamental axes only — no technical or timing content here, and no '
              'overall peer score: this ranks measured business characteristics, and '
              'none of it is backtested as an edge.</div>'
        ),
        unsafe_allow_html=True,
    )

    ranks = res.get("ranks") or {}

    # ── FP-3 · where the anchor stands INSIDE the group ──
    # Rank, never percentile: in a group of six to twelve names a percentile is a
    # weak statistic wearing a precise costume.
    ax_ranks = ranks.get("axes") or {}
    rank_chips = "".join(
        rs.chip(fscore.AXIS_LABELS[a], _axis_tone(i["anchor_score"]),
                f'{i["rank"]}/{i["n"]}')
        for a in fscore.AXES
        if (i := ax_ranks.get(a)) and i.get("rank")
    )
    if ranks.get("headline") or rank_chips:
        st.markdown(
            rs.card(
                f'<div style="font-size:12.5px;color:{rs.TOKENS["text"]};'
                f'margin-bottom:6px;">{ranks.get("headline", "")}</div>{rank_chips}'
                f'<div style="font-size:11px;color:{rs.TOKENS["text_muted"]};'
                f'margin-top:6px;">Chips are <b>peer-relative</b> — the anchor\'s rank '
                f'out of the names that scored on that axis. The table\'s numbers stay '
                f'<b>absolute</b>. "Strongest business profile" averages the five '
                f'business axes and deliberately excludes Valuation: leading a peer '
                f'group must not mean being the cheapest. Nothing here is backtested.</div>'
            ),
            unsafe_allow_html=True,
        )

    # ── FP-4 · the optional technical pass ──
    tech_key = f"peers_tech_{anchor}"
    tcol1, tcol2 = st.columns([1, 4])
    with tcol1:
        want_tech = st.toggle("Technicals", key=f"tg_{tech_key}",
                              value=bool(st.session_state.get(tech_key)))
    with tcol2:
        st.caption("Adds RS · RSI · ADX · 52w · Stage · Pivot — a **second** network "
                   "pass (one price history per peer) on top of the statements.")

    if want_tech:
        tprog = st.progress(0.0, text="Fetching peer price history...")
        try:
            _nifty = cached_fetch_nifty50(days=400)
        except Exception:
            _nifty = None
        try:
            tech = pcmp.technical_columns(
                df["symbol"].tolist(),
                lambda s: cached_fetch_ohlcv(s, days=400), _nifty,
                progress_cb=lambda d, t: tprog.progress(
                    min(d / max(t, 1), 1.0), text=f"Technicals {d}/{t}..."))
            df = pcmp.attach_technicals(df, tech)
            st.session_state[tech_key] = True
        except Exception as exc:
            st.warning(f"Technical pass failed: {exc}")
            want_tech = False
        tprog.empty()

    # ── The table: sticky header, frozen ticker column, in-cell bars ──
    # Markup lives in peer_comparison.table_html, not here: it is pure
    # df -> HTML with no Streamlit in it, so it can be rendered and eyeballed
    # from a script without standing up the app behind its login.
    st.markdown(pcmp.table_html(df, med, anchor, tone_fn=_axis_tone,
                                ranks=ranks, with_technicals=want_tech),
                unsafe_allow_html=True)
    st.caption(
        f"Sorted by market cap with **{anchor}** pinned first. The six axis numbers "
        "are the same measured 0–100 scores as the donuts above (55 = the median NSE "
        "company); ★ marks the best in this group and is the only peer-relative mark "
        "in the table. `n/a` is a missing input, never a zero — **Cov.** says how much "
        "of each row was actually measured, so a sparsely-covered peer is not read as "
        "a weak one. Median rather than mean, because one loss-maker moves a mean "
        "somewhere no company in the group actually sits."
    )

    # ── FP-2 · the radar, as an overlay ──
    st.markdown(rs.section("Profile vs the peer group"), unsafe_allow_html=True)
    rc1, rc2 = st.columns([3, 2])
    with rc2:
        others = [s for s in df["symbol"].tolist() if s != anchor]
        compare = st.selectbox("Overlay one peer (optional)", ["—"] + others,
                               key=f"peers_cmp_{anchor}")
        compare = None if compare == "—" else compare
        st.caption(
            "Two traces by default, three at most. Radar charts degrade past about "
            "four overlaid series, so this one is capped below that.\n\n"
            "**Read the shape, not the area.** Polygon area scales as the square of "
            "the values and depends on axis order, so it is not a quantity — the "
            "donuts and the table remain the precise readout. What the overlay adds "
            "is the one thing they cannot show: whether this profile is normal for "
            "this industry."
        )
    with rc1:
        try:
            st.plotly_chart(pcmp.radar_figure(df, med, anchor, compare=compare),
                            use_container_width=True,
                            key=f"peer_radar_{anchor}")
        except Exception as exc:
            st.warning(f"Radar unavailable: {exc}")

    # ── FP-4 · the "vs anchor" drill ──
    if compare:
        _peer_head_to_head(anchor, compare, df, want_tech)


def _peer_head_to_head(anchor: str, other: str, df, with_technicals: bool) -> None:
    """Two names, axis by axis, with the gap stated in the direction that matters.

    The mockup's "vs ANCHOR" link. It reuses the rows already scored for the table
    rather than re-fetching, so the drill costs nothing and — more importantly —
    cannot disagree with the table it was opened from.
    """
    a_row = df[df["symbol"] == anchor]
    b_row = df[df["symbol"] == other]
    if not len(a_row) or not len(b_row):
        return
    a_row, b_row = a_row.iloc[0], b_row.iloc[0]

    rows = []
    for ax in fscore.AXES:
        av, bv = pcmp._score_or_none(a_row[ax]), pcmp._score_or_none(b_row[ax])
        if av is None or bv is None:
            gap_txt, tone = rs.NA, "absent"
        else:
            gap = av - bv
            gap_txt = f"{gap:+d}"
            tone = "good" if gap > 5 else ("risk" if gap < -5 else "neutral")
        fg = rs.tone_colors(tone)[0]
        rows.append(
            f'<tr><td style="padding:3px 8px;font-size:11.5px;">'
            f'{fscore.AXIS_LABELS[ax]}</td>'
            f'<td class="tb-mono" style="text-align:right;padding:3px 8px;">'
            f'{"—" if av is None else av}</td>'
            f'<td class="tb-mono" style="text-align:right;padding:3px 8px;">'
            f'{"—" if bv is None else bv}</td>'
            f'<td class="tb-mono" style="text-align:right;padding:3px 8px;'
            f'color:{fg};font-weight:600;">{gap_txt}</td></tr>'
        )
    if with_technicals and "stage_label" in df.columns:
        for col, label, _d in pcmp.TECH_COLUMNS:
            av, bv = a_row.get(col), b_row.get(col)
            # Same formatter as the table: the drill must not render 52w as a
            # bare 3.2 while the row above it says -3.2%.
            fmt = lambda v: pcmp.tech_text(v, col)
            rows.append(
                f'<tr><td style="padding:3px 8px;font-size:11.5px;color:'
                f'{rs.TOKENS["text_muted"]};">{label}</td>'
                f'<td class="tb-mono" style="text-align:right;padding:3px 8px;">{fmt(av)}</td>'
                f'<td class="tb-mono" style="text-align:right;padding:3px 8px;">{fmt(bv)}</td>'
                f'<td></td></tr>'
            )

    st.markdown(
        rs.card(
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr>'
            f'<th style="text-align:left;font-size:10px;text-transform:uppercase;'
            f'letter-spacing:.04em;color:{rs.TOKENS["text_muted"]};padding:3px 8px;"></th>'
            f'<th style="text-align:right;font-size:11px;padding:3px 8px;">{anchor}</th>'
            f'<th style="text-align:right;font-size:11px;padding:3px 8px;">{other}</th>'
            f'<th style="text-align:right;font-size:10px;text-transform:uppercase;'
            f'letter-spacing:.04em;color:{rs.TOKENS["text_muted"]};padding:3px 8px;">Gap</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
            f'<div style="font-size:11px;color:{rs.TOKENS["text_muted"]};margin-top:6px;">'
            f'Gap is {anchor} minus {other} in score points, so positive favours '
            f'{anchor}. Technical rows carry no gap column on purpose — a 12-point '
            f'RSI difference is not comparable to a 12-point axis difference.</div>',
            title=f"{anchor} vs {other}",
        ),
        unsafe_allow_html=True,
    )


_SCENARIO_TONE = {"Bull": "good", "Base": "info", "Bear": "risk"}


def render_scenarios(res: dict | None, deep: dict | None) -> None:
    """FR-5 — bull/base/bear business-size scenarios with the arithmetic shown.

    Kept deliberately distinct from the chart's projection line. That one
    projects PRICE from Elliott-Wave and measured-move geometry; this projects
    the SIZE OF THE BUSINESS from filed revenue and margin. Different objects,
    different units — the copy says so, because a reader who conflates them
    would think two independent methods agreed.
    """
    st.markdown(rs.section("Forward scenarios — business size"), unsafe_allow_html=True)

    if not res:
        n = len((deep or {}).get("annual") or [])
        st.markdown(
            rs.callout("Not enough filed history for scenarios.",
                       f"Projecting a range needs at least {scen.MIN_ANNUAL} annual "
                       f"periods with revenue and margin; yfinance returned {n}. "
                       f"Nothing is extrapolated from a single growth observation.",
                       tone="absent"),
            unsafe_allow_html=True)
        return

    rows = res["scenarios"]
    peak = max((r["revenue"] or 0) for r in rows) or 1.0

    bars = []
    for r in rows:
        tone = _SCENARIO_TONE.get(r["name"], "neutral")
        profit_txt = _cr(r["profit"]) or "—"
        bars.append(rs.bar_row(
            f'{r["name"]} case (revenue {r["growth_pct"]:+.1f}%/yr · margin {r["margin_pct"]:.1f}%)',
            f'{_cr(r["revenue"])}  |  net profit est. {profit_txt}',
            pct=(r["revenue"] or 0) / peak * 100,
            tone=tone,
            right=r["how"],
            footnote=r["derivation"],
        ))

    st.markdown(rs.card("".join(bars)), unsafe_allow_html=True)

    notes = []
    if res.get("bull_capped"):
        notes.append(
            f"Growth is capped at {res['growth_cap_pct']:.0f}%/yr for the "
            f"projection (observed best: {res['bull_growth_raw']:+.1f}%). Compounding "
            f"an exceptional year for {res['horizon_years']} years is how a bar chart "
            f"turns into a cartoon — the same plausibility guard the chart's price "
            f"projection uses.")
    if res.get("outlier_margin"):
        notes.append(res["outlier_margin"]["note"])
    for n in notes:
        st.markdown(rs.callout("Guard applied.", n, tone="warn"), unsafe_allow_html=True)

    # "1 Thing to Track" — the highest-emphasis card on the page, used once.
    d = res["driver"]
    st.markdown(
        rs.card(
            f'<div style="font-size:12.5px;color:{rs.TOKENS["text_body"]};line-height:1.5;">'
            f'<b style="color:{rs.TOKENS["accent"]};">{d["threshold"]}</b><br>{d["detail"]}'
            f'</div>',
            title=f'1 thing to track — {d["which"]}', emphasis=True),
        unsafe_allow_html=True)

    st.caption(
        f"**Arithmetic extrapolation, not a forecast.** Every bar is the filed "
        f"{res['base_period'][:4]} revenue compounded forward {res['horizon_years']} years "
        f"at a rate this company has actually printed, times a margin it has actually "
        f"earned — the derivation under each bar can be redone by hand. The band is built "
        f"from only {res['growth_observations']} growth observations, so it is wide and "
        f"noisy. This projects the **size of the business**, and is a different object from "
        f"the chart tool's **price** projection (Elliott-Wave / measured moves) — neither "
        f"confirms the other."
    )


_FLAG_TONE = {
    ("FLAG", "critical"): "risk",
    ("FLAG", "watch"):    "warn",
    ("CLEAN", "critical"): "good",
    ("CLEAN", "watch"):    "good",
}
_FLAG_WORD = {"FLAG": "FLAG", "CLEAN": "CHECKED · CLEAN", "NOT_CHECKED": "NOT CHECKED"}


def render_red_flags(res: dict) -> None:
    """FR-4 — the three-state red-flag list.

    Ordered FLAG → NOT CHECKED → CLEAN, which is deliberately not the flattering
    order. The unchecked items sit second, above the clean ones, because an
    unexamined governance surface deserves more of the reader's attention than a
    check that passed.
    """
    flags = res.get("flags") or []
    c = res.get("counts") or {}
    if not flags:
        return

    st.markdown(rs.section("Red flags"), unsafe_allow_html=True)

    ran = c.get("flagged", 0) + c.get("clean", 0)
    total = len(flags)
    header_chips = (
        rs.chip("Flagged", "risk" if c.get("flagged") else "neutral", str(c.get("flagged", 0)))
        + rs.chip("Checked & clean", "good", str(c.get("clean", 0)))
        + rs.chip("Not checked", "absent", str(c.get("not_checked", 0)))
    )

    # The source mockup shows a green "No Critical Red Flags" panel. It is only
    # honest when every critical check actually ran, which — with three
    # unsourceable governance items — it never does here.
    if res.get("no_critical_flags"):
        verdict = rs.callout("No critical red flags.",
                             "Every critical check ran and came back clean.", tone="good")
    else:
        verdict = rs.callout(
            f"{ran} of {total} checks could run.",
            "This is not a clean bill of health. Auditor qualifications, "
            "related-party transactions and revenue concentration live in "
            "annual-report prose that nothing here parses, so they are shown as "
            "<b>not checked</b> rather than omitted — an unexamined risk is not "
            "an absent one.",
            tone="warn")
    st.markdown(rs.card(f'<div style="margin-bottom:8px;">{header_chips}</div>{verdict}'),
                unsafe_allow_html=True)

    # Plan C — a "verify" deep link per gray-zone flag, so a NOT CHECKED item is
    # actionable (go look here) rather than a dead end. Screener's consolidated
    # page carries promoter/pledge tables AND the annual-report documents; the
    # NSE quote page carries the official shareholding pattern.
    from urllib.parse import quote as _q
    _sym = res.get("symbol", "")
    _scr = f"https://www.screener.in/company/{_q(_sym)}/consolidated/"
    _nseq = f"https://www.nseindia.com/get-quotes/equity?symbol={_q(_sym)}"
    _verify_links = {
        "promoter_holding":      [("screener.in ↗", _scr), ("NSE filing ↗", _nseq)],
        "promoter_pledge":       [("screener.in ↗", _scr), ("NSE filing ↗", _nseq)],
        "auditor_qualification": [("Annual report ↗", _scr)],
        "related_party_txns":    [("Annual report ↗", _scr)],
        "revenue_concentration": [("Annual report ↗", _scr)],
    }
    _link_col = rs.TOKENS.get("accent", "#3fb950")

    order = {"FLAG": 0, "NOT_CHECKED": 1, "CLEAN": 2}
    rows = []
    for f in sorted(flags, key=lambda x: (order.get(x["state"], 9),
                                          0 if x["severity"] == "critical" else 1)):
        tone = _FLAG_TONE.get((f["state"], f["severity"]), "absent")
        fg, bg = rs.tone_colors(tone)
        sev = ("critical" if f["severity"] == "critical" else "watch")
        _lk = _verify_links.get(f["key"])
        links_html = ""
        if _lk:
            anchors = " · ".join(
                f'<a href="{u}" target="_blank" rel="noopener" '
                f'style="color:{_link_col};text-decoration:none;">{t}</a>' for t, u in _lk)
            links_html = (f'<div class="tb-micro" style="margin-top:3px;">'
                          f'Verify manually: {anchors}</div>')
        rows.append(
            f'<div style="display:flex;gap:10px;align-items:flex-start;padding:7px 0;'
            f'border-top:1px solid {rs.TOKENS["border"]};">'
            f'<span class="tb-chip" style="background:{bg};color:{fg};'
            f'border:1px solid {fg}33;min-width:118px;text-align:center;flex-shrink:0;">'
            f'{_FLAG_WORD.get(f["state"], f["state"])}</span>'
            f'<div style="flex:1;min-width:0;">'
            f'<b style="font-size:12.5px;color:{rs.TOKENS["text"]};">{f["label"]}</b>'
            f'<span class="tb-micro" style="margin-left:7px;">{sev} · {f["source"]}</span>'
            f'<div style="font-size:12px;color:{rs.TOKENS["text_body"]};line-height:1.45;">'
            f'{f["detail"]}</div>{links_html}</div></div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def _render_screener_unlock(res: dict) -> None:
    """Plan B — paste a screener.in sessionid to unlock the screener-gated checks
    (promoter pledge, deeper history) when the browser auto-grab found none.
    Only shown when such a gap actually exists. Stored in the DB like the digest
    Gmail credentials; clearing the field removes it."""
    flags = res.get("flags") or []
    gaps = [f for f in flags
            if f.get("source") == "screener.in" and f.get("state") == "NOT_CHECKED"]
    if not gaps:
        return
    try:
        import portfolio_db as _db
        saved = _db.get_setting("screener_sessionid") or ""
    except Exception:
        _db, saved = None, ""
    if _db is None:
        return

    with st.expander("🔓 Unlock screener.in checks (promoter pledge, deeper history)"):
        st.caption(
            "These need a screener.in `sessionid` cookie and none was found in a "
            "local browser. Log in to screener.in → DevTools → Application ▸ "
            "Cookies ▸ https://www.screener.in → copy the **sessionid** value and "
            "paste it here. It expires periodically — re-paste if checks stop "
            "resolving. Stored locally in your dashboard DB, only sent to "
            "screener.in."
        )
        val = st.text_input("screener.in sessionid", value=saved, type="password",
                            key="rf_screener_sid")
        c1, c2 = st.columns(2)
        if c1.button("Save & re-check", key="rf_sid_save", type="primary"):
            try:
                _db.set_setting("screener_sessionid", (val or "").strip())
                _cached_red_flags.clear()
                st.success("Saved — re-running screener checks…")
                st.rerun()
            except Exception as e:
                st.error(f"Could not save: {e}")
        if saved and c2.button("Clear saved sessionid", key="rf_sid_clear"):
            try:
                _db.set_setting("screener_sessionid", "")
                _cached_red_flags.clear()
                st.success("Cleared."); st.rerun()
            except Exception as e:
                st.error(f"Could not clear: {e}")


#: |YoY| beyond this on a quarter is annotated rather than left for the reader
#: to spot. Wide enough that ordinary Indian seasonality doesn't trip it.
_QTR_ANOMALY_PCT = 40.0


def render_fundamental_history(deep: dict) -> None:
    """FR-3 — the annual table and the quarterly EPS card grid.

    Two different surfaces on purpose. Years are a *comparison* (how did margin
    trend over five years) and a table is the honest shape for that. Quarters
    are read one at a time, with their own annotations, so they get cards.

    Nothing here is fetched: FR-1's `derive_fundamentals()` already returns
    `annual` and `quarters` with date-matched YoY.
    """
    d = deep or {}
    annual, quarters = d.get("annual") or [], d.get("quarters") or []
    cur = d.get("currency") or "INR"
    if not annual and not quarters:
        return

    if annual:
        st.markdown(rs.section("Annual financials"), unsafe_allow_html=True)
        rows = []
        for a in annual:
            rows.append({
                "Year":        a["period"],
                "Revenue":     _cr(a.get("revenue"), cur) or "—",
                "Rev YoY":     "—" if a.get("revenue_yoy") is None else f"{a['revenue_yoy']:+.1f}%",
                "Net Profit":  _cr(a.get("net_income"), cur) or "—",
                "Profit YoY":  "—" if a.get("profit_yoy") is None else f"{a['profit_yoy']:+.1f}%",
                "Net Margin":  "—" if a.get("net_margin") is None else f"{a['net_margin']:.1f}%",
                "OPM":         "—" if a.get("opm") is None else f"{a['opm']:.1f}%",
                "EPS":         "—" if a.get("eps") is None else f"{a['eps']:,.2f}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if quarters:
        n = len(quarters)
        st.markdown(rs.section(f"Quarterly earnings — last {n} reported"),
                    unsafe_allow_html=True)

        revs = [q.get("revenue") for q in quarters if q.get("revenue") is not None]
        best_rev = max(revs) if revs else None

        cells = []
        for q in quarters:
            eps, yoy = q.get("eps"), q.get("profit_yoy")
            tone = "neutral" if yoy is None else ("good" if yoy >= 0 else "risk")
            # "Highest of the N shown" — NOT "record quarter". yfinance returns
            # about six quarters, so an all-time claim would be unsupported.
            is_best = (best_rev is not None and q.get("revenue") == best_rev)

            sub_bits = []
            if q.get("revenue") is not None:
                sub_bits.append(_cr(q["revenue"], cur))
            if yoy is not None:
                sub_bits.append(f"{'▲' if yoy >= 0 else '▼'} {yoy:+.1f}% profit YoY")
            elif q.get("revenue_yoy") is None:
                sub_bits.append("no year-ago quarter filed")

            card_tone = "good" if is_best else tone
            body = rs.stat_card(
                fdeep.fiscal_quarter_label(q["period"]),
                None if eps is None else f"{eps:,.2f}",
                sub=" · ".join(b for b in sub_bits if b),
                tone=card_tone,
            )
            flags = ""
            if is_best:
                flags += rs.chip(f"Highest revenue of the {n} shown", "good")
            if yoy is not None and abs(yoy) >= _QTR_ANOMALY_PCT:
                flags += rs.chip("Outlier" if yoy > 0 else "Sharp drop",
                                 "good" if yoy > 0 else "risk",
                                 f"{yoy:+.0f}% YoY")
            cells.append(f'<div style="flex:1;min-width:165px;">{body}'
                         f'<div style="margin-top:4px;">{flags}</div></div>')

        st.markdown(
            f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin:4px 0;">'
            f'{"".join(cells)}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Card value is **EPS**; revenue and profit-YoY sit underneath. YoY is "
            "matched to the same quarter a year earlier **by date** — yfinance's "
            "quarterly frames have gaps, and counting four columns back would "
            "compare a March quarter against the previous December."
        )

    # The honest panel the source mockup shipped, kept as copy rather than built.
    st.markdown(
        rs.callout(
            "Consensus data unavailable.",
            "There is no free NSE analyst-consensus feed, so this page cannot show "
            "a beat/miss record or an estimate-revision trend — and does not "
            "approximate one. What is shown above is entirely reported actuals: "
            "filed revenue, profit, margin and EPS, with year-on-year changes "
            "computed from the filings themselves.",
            tone="risk"),
        unsafe_allow_html=True,
    )


#: FR-6. Announcements land continuously, so this is cached far shorter than the
#: statement layer — a results-day transcript appearing is the whole point.
@st.cache_data(ttl=1800, show_spinner=False)
def cached_concalls(symbol: str) -> dict:
    return concalls.concall_items(symbol, limit=12)


_CONCALL_ICON = {"transcript": "📄", "audio": "🎧", "presentation": "📊",
                 "press": "📰", "intimation": "🗓", "other": "•"}


def render_concalls(data: dict) -> None:
    """FR-6 — dated links to the company's own concall material.

    Deliberately a **link list, not a summary**. The roadmap's instruction for
    this phase is "do not let a template pretend to be analysis", and with no LLM
    configured the honest product is the primary document plus its date. No
    sentiment, no extracted "management tone", no generated prose.
    """
    if not data:
        return
    st.markdown(rs.section("Earnings calls & investor material"), unsafe_allow_html=True)

    if data.get("state") != "OK":
        st.markdown(
            rs.callout("Concall feed unavailable.",
                       f"{data.get('note') or 'NSE announcements could not be read'}. "
                       "This is 'we could not ask', not 'the company has filed nothing'.",
                       tone="risk"),
            unsafe_allow_html=True)
        return

    items = data.get("items") or []
    if not items:
        st.caption(f"No concall or investor-meet filings found among "
                   f"{data.get('n_total', 0)} NSE announcements for this symbol.")
        return

    latest = data.get("latest_transcript")
    st.caption(
        f"**{data.get('n_concall', 0)}** concall / investor-meet filings of "
        f"{data.get('n_total', 0)} NSE announcements · "
        f"**{data.get('n_transcripts', 0)}** transcripts · "
        f"latest transcript **{latest or '—'}**. "
        "Links go to NSE's own archive. Documents are listed, never summarised — "
        "there is no LLM configured, and a generated 'narrative' over a concall "
        "would be invention rather than analysis."
    )

    for i in items:
        icon = _CONCALL_ICON.get(i.get("kind"), "•")
        label = (i.get("text") or i.get("subject") or "").strip() or "(no description)"
        if len(label) > 150:
            label = label[:150].rstrip() + "…"
        date = i.get("date") or "—"
        size = f" · {i['size']}" if i.get("size") else ""
        link = (f' — <a href="{i["file"]}" target="_blank">open PDF</a>'
                if i.get("file") else "")
        st.markdown(
            f'<div style="margin:2px 0;line-height:1.45;">{icon} '
            f'<b>{date}</b> <span style="opacity:.65;">[{i.get("kind","")}]</span>{size}<br>'
            f'<span style="opacity:.85;">{label}</span>{link}</div>',
            unsafe_allow_html=True,
        )


_TONE_DOT   = {"good": "🟢", "neutral": "🟡", "bad": "🔴"}
_TONE_COLOR = {"good": "green", "neutral": "orange", "bad": "red"}


# ── Filter C — ownership flow (DS-2) ──────────────────────────────────────────
#: Cached a full day: the underlying filing is QUARTERLY, so anything shorter
#: re-downloads two ~500 KB XBRLs from NSE to redraw an identical card.
@st.cache_data(ttl=86400, show_spinner=False)
def cached_ownership(symbol: str):
    return nse.fetch_ownership(symbol)


def render_ownership_flow(symbol: str) -> None:
    """Filter C of the Crash-Proof system — the quarter-over-quarter rotation.

    Behind a button because each read pulls two multi-hundred-KB XBRL filings
    from NSE, and because the data only changes once a quarter — paying that on
    every analyzer run would be pure waste.
    """
    st.markdown(rs.section("Filter C — ownership flow (quarterly)"),
                unsafe_allow_html=True)
    _key = f"own_{symbol}"
    if not st.session_state.get(_key):
        if st.button("Fetch shareholding pattern", key=f"own_btn_{symbol}",
                     help="Reads the last two quarterly SEBI shareholding filings "
                          "from NSE (~10s)."):
            st.session_state[_key] = True
            st.rerun()
        st.caption("Not fetched — the ownership leg is unmeasured until you pull it.")
        return

    with st.spinner("Reading the last two shareholding filings…"):
        try:
            own = cached_ownership(symbol)
        except Exception as exc:
            own = None
            st.warning(f"Shareholding fetch failed — {exc}")
    if not own:
        st.info("No readable shareholding filing for this symbol. The ownership "
                "leg stays unmeasured — that is not the same as 'no institutions'.")
        return

    rot = nse.interpret_rotation(own["change"])
    _fg, _bg = rs.tone_colors(rot["tone"])

    # The filing period leads the card. A shareholding read presented without its
    # quarter invites being taken as current positioning, which it never is.
    st.markdown(
        rs.callout(f'{rot["headline"]} — as of {own["as_of"]}'
                   + (f' (vs {own["prev_as_of"]})' if own["prev_as_of"]
                      else ' · no prior quarter to compare'),
                   rot["detail"], tone=rot["tone"]),
        unsafe_allow_html=True)

    if not own["reconciles"]:
        st.warning("This filing did **not** reconcile against NSE's own promoter / "
                   "public figures — treat the split below as unverified.")

    _latest = own["latest"]
    _labels = {"fii": "FII / FPI", "dii": "DII", "mf": "Mutual funds",
               "retail": "Retail", "promoter": "Promoter"}
    for _col, _leg in zip(st.columns(len(nse.HEADLINE_LEGS)), nse.HEADLINE_LEGS):
        _held, _chg = _latest.get(_leg), own["change"].get(_leg)
        _dir = nse.direction(_chg)
        _dc = {"up": rs.TOKENS["good"], "down": rs.TOKENS["risk"],
               "flat": rs.TOKENS["text_muted"], "unknown": rs.TOKENS["absent"]}[_dir]
        with _col:
            st.markdown(
                rs.card(
                    f'<div class="tb-micro">{_labels[_leg]}</div>'
                    f'<div class="tb-mono" style="font-size:17px;font-weight:700;'
                    f'margin-top:2px;">'
                    + (rs.NA if _held is None else f'{_held:.2f}%') + '</div>'
                    f'<div style="font-size:11px;color:{_dc};font-weight:600;'
                    f'margin-top:2px;">{nse.ARROWS[_dir]} '
                    + ("no prior quarter" if _chg is None else f'{_chg:+.2f} pp') +
                    '</div>'),
                unsafe_allow_html=True)

    _marks = {nse.MET: ("✓", rs.TOKENS["good"]), nse.NOT_MET: ("✗", rs.TOKENS["risk"]),
              nse.UNKNOWN: ("?", rs.TOKENS["absent"])}
    _crit = "".join(
        f'<span class="tb-chip" style="background:{_marks[c["state"]][1]}1a;'
        f'color:{_marks[c["state"]][1]};border:1px solid {_marks[c["state"]][1]}33;">'
        f'{_marks[c["state"]][0]} {c["label"]}</span>'
        for c in rot["criteria"])
    st.markdown(
        f'<div style="margin-top:6px;"><span class="tb-micro" '
        f'style="margin-right:6px;">FILTER C CRITERIA</span>{_crit}</div>',
        unsafe_allow_html=True)

    st.caption(
        f"Read straight from the SEBI shareholding-pattern XBRL (the regulatory "
        f"filing, not an aggregator). **Mutual funds are a subset of DII** — those "
        f"two bars overlap and do not add. Moves under "
        f"{rot['flat_band_pp']:.2f} pp read as flat (filing noise). "
        "**Quarterly and lagging**: this describes the register on the filing date, "
        "not today's positioning. It is the *structural* leg only — the framework "
        "reads it against market health (DS-3) and price+volume (DS-4) before it "
        "means buy or avoid. On its own, FII↑ into a falling price is a watchlist, "
        "not a signal.")


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


CHART_TOOL_PORT = 5001


def render_chart_tool(symbol: str, height: int = 620, caption: bool = True) -> bool:
    """Embed the Chart Tool for `symbol`; returns whether it rendered.

    Extracted from the Predictive Analysis page (M4) when the Stock Analyzer
    became a second caller — two copies of the port probe would have drifted.
    The probe matters: `components.iframe` against a dead port renders a silent
    blank rectangle, so the page has to say what's wrong instead.
    """
    chart_sym = symbol if ("." in symbol or symbol.startswith("^")) else f"{symbol}.NS"
    try:
        socket.create_connection(("127.0.0.1", CHART_TOOL_PORT), timeout=0.4).close()
    except OSError:
        st.warning(
            f"Chart Tool server (port {CHART_TOOL_PORT}) is not running — start it "
            "with `start.bat` (or `py tools/chart_server.py`) to embed the "
            "annotated chart here."
        )
        return False
    components.iframe(
        f"http://localhost:{CHART_TOOL_PORT}/?symbol={chart_sym}&tf=1d",
        height=height,
    )
    if caption:
        st.caption(
            "Overlays follow the indicator set saved in the Chart Tool — "
            "enable Price Projection / VCP / Rounding Bottom there once and "
            "every load carries them."
        )
    return True


#: Sizing bounds PER CHART MODE, because the two are not the same object. The
#: classic chart stacks five or six panes, so 900 is roughly where the
#: oscillators stop being legible. The Chart Tool is a single pane whose shipped
#: default is 620 — a floor of 900 there would put the default BELOW the minimum,
#: which Streamlit silently coerces rather than rejecting, leaving a slider whose
#: stated range is a lie. Ceiling is a tall portrait monitor's worth for both.
CHART_H_MAX = 2400
CHART_H_MIN_CLASSIC, CHART_H_DEFAULT_CLASSIC = 900, 1250
CHART_H_MIN_TOOL, CHART_H_DEFAULT_TOOL = 400, 620
#: Upper bound on the price pane's share. Past this the oscillators below it
#: compress into strips — at 0.65 on a 1250px figure RSI still gets ~100px,
#: which is about the limit of useful.
PRICE_SHARE_MAX = 0.65


def build_chart(symbol: str, df: pd.DataFrame, ew: dict,
                nifty_df: pd.DataFrame | None = None,
                harmonic: dict | None = None,
                height: int | None = None,
                price_share: float | None = None) -> go.Figure:
    """The classic multi-pane Plotly chart.

    `height` and `price_share` are both optional and both default to the values
    this chart has always used, so a caller that passes neither gets a
    byte-identical figure. They are separate levers on purpose: raising the
    height scales every pane together, which does not help if the complaint is
    that the CANDLES are cramped — the price pane is only 38% of the figure, so
    it stays 38% of whatever height you pick. `price_share` is the one that
    actually buys candle room, by taking it from the oscillators.
    """
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
    if price_share is not None:
        # Give the price pane `price_share` and rescale the rest to fill what is
        # left, preserving their proportions to each other — Plotly requires
        # row_heights to sum to 1, and the sub-panes' relative sizing was chosen
        # deliberately (volume thin, RSI/MACD equal). Clamped at the floor to the
        # chart's own default, so asking for less than it already had is a no-op
        # rather than a way to shrink the candles.
        p = min(max(float(price_share), heights[0]), PRICE_SHARE_MAX)
        scale = (1.0 - p) / (1.0 - heights[0])
        heights = [p] + [h * scale for h in heights[1:]]
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

    chart_height = int(height) if height else (1250 if rs_line is not None else 1150)
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
        elif alert["metric"] == "rsi_60_40":
            # Fires when the RSI 60-40 with-trend setup is live; the compared
            # value is the setup's standalone quality (score_base 0-100), else 0.
            hit = sc.scan_rsi_60_40(df)
            value = hit["score_base"] if hit else 0.0
            detail = (f"{hit['pattern_type'].split('·')[-1].strip()} {value:.0f}"
                      if hit else "no setup")
            return _compare(value, alert["operator"], alert["threshold"]), detail
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

# The overview strip was the last native `st.metric` row on the page: cold grey
# labels, a proportional face on the figures, and no semantic colour, sitting
# directly above a token-styled verdict card. It now uses the same stat cards as
# everything else, so the numbers line up in mono and each one states its own
# verdict through tone rather than being uniformly black.
def _tone_signed(v, *, good_when_positive=True):
    """Tone for a signed number; neutral when it is missing or flat."""
    if v is None or pd.isna(v) or abs(float(v)) < 1e-9:
        return "neutral"
    up = float(v) > 0
    return "good" if up == good_when_positive else "risk"


_cap_risk = portfolio_summary["capital_at_risk_pct"]
_ov_cards = [
    rs.stat_card(
        "Nifty 50",
        f"{nifty_last:,.0f}" if nifty_last else None,
        (f"{nifty_day_chg:+.2f}% today" if nifty_day_chg is not None else None),
        tone=_tone_signed(nifty_day_chg)),
    # Labelled by its actual basis, not "Regime": the banner below owns that word
    # and answers a different question (50 SMA + vol → trending/ranging). Two
    # adjacent boxes both saying "Regime" with different answers read as a bug.
    rs.stat_card(
        "vs 200 SMA", nifty_regime if nifty_regime != "Unknown" else None,
        "long-term regime",
        tone={"RISK-ON": "good", "RISK-OFF": "risk"}.get(nifty_regime, "absent")),
    rs.stat_card(
        "Portfolio P&L", fmt_money(portfolio_summary["pl"]),
        (f"Today {gain_loss_badge(portfolio_summary['day_pl_pct'])} vs Nifty "
         f"{gain_loss_badge(nifty_day_chg)}"
         if (nifty_day_chg is not None and portfolio_summary["open_count"] > 0)
         else fmt_pct(portfolio_summary["pl_pct"])),
        tone=_tone_signed(portfolio_summary["pl"])),
    # Capital at risk is caution-only: more of it is never good news, so it
    # cannot read green. Amber past the same 6% the verdict engine flags.
    rs.stat_card(
        "Capital at Risk",
        fmt_pct(_cap_risk).replace("+", ""),
        f"caution above {mvd.CAPITAL_AT_RISK_CAUTION_PCT:.0f}%",
        tone=("risk" if (_cap_risk or 0) > mvd.CAPITAL_AT_RISK_CAUTION_PCT
              else "neutral")),
    rs.stat_card(
        "Alerts Triggered", f"{triggered_count}/{len(active_alerts)}",
        "active alerts firing",
        tone="warn" if triggered_count else "neutral"),
]
st.markdown(rs.strip(_ov_cards, cols=5), unsafe_allow_html=True)

# ── Regime + today's verdict — ONE card ───────────────────────────────────────
_show_regime = current_page != "Scanner Hub"  # hidden on Scanner Hub
# These were two stacked cards and between them they owned most of the first
# screen on every page. They are now one, because they are one thought: the
# regime is the CONTEXT and the verdict is the DECISION taken in it, and the
# reader was scrolling past both to reach the page they asked for.
#
# The old code already carried the rule that makes the merge safe — "two
# coloured surfaces stacked would read as two verdicts, and only one of these is
# a decision". One card with the verdict's tone on its border keeps exactly one
# decision on screen; the regime sits inside it as a labelled context line.
#
# Compaction is layout only. No flag, number or sentence is dropped: the
# caution / favorable / not-checked blocks moved from stacked full-width lists
# into three columns, which is where most of the height went.
regime_info = mvd.classify_regime(nifty_overview)

_senti_reading = cached_latest_sentiment()
# A reading from three sessions ago must not read as today's green light.
_stale_flags = []
_senti_age = None
if _senti_reading and _senti_reading.get("reading_date"):
    _senti_age = (date.today() - date.fromisoformat(_senti_reading["reading_date"])).days
    if _senti_age >= 1:
        # The instruction used to be "refresh Market Sentiment", pointing at
        # another page. There is a button directly under this card now, so the
        # flag states the fact and the button owns the fix.
        _stale_flags.append(
            f"Sentiment reading is {_senti_age} day(s) old "
            f"(dated {_senti_reading['reading_date']})")
verdict = mvd.build_verdict(_senti_reading, portfolio_summary, _stale_flags)

_vfg, _ = rs.tone_colors(verdict["tone"])


def _flag_col(items: list[str], label: str, tone: str, mark: str) -> str:
    """One flag column — micro header in the tone, then the flags themselves.

    Empty columns still render (as a dash) so the three keep their widths and
    the reader can see that a category is empty rather than missing.
    """
    fg, _bg = rs.tone_colors(tone)
    rows = "".join(
        f'<div style="font-size:11.5px;color:{fg};line-height:1.5;">{mark} {i}</div>'
        for i in items) or (
        f'<div style="font-size:11.5px;color:{rs.TOKENS["absent"]};'
        f'line-height:1.5;">—</div>')
    return (f'<div style="flex:1;min-width:150px;">'
            f'<div class="tb-micro" style="color:{fg};">{label}</div>{rows}</div>')


def _regime_line() -> str:
    """The regime as a context strip inside the verdict card, or '' if unknown."""
    if regime_info["label"] == "UNKNOWN":
        return ""
    bits = []
    if regime_info["vol"] is not None and regime_info["vol_baseline"] is not None:
        bits.append(f'Vol <span class="tb-mono">{regime_info["vol"]:.2f}%</span> vs '
                    f'<span class="tb-mono">{regime_info["vol_baseline"]:.2f}%</span> baseline')
    if regime_info["dist_pct"] is not None:
        bits.append(f'within <span class="tb-mono">'
                    f'{abs(regime_info["dist_pct"]):.1f}%</span> of the 50 SMA')
    return (
        f'<div style="border-top:1px solid {rs.TOKENS["border"]};margin-top:10px;'
        f'padding-top:8px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;">'
        f'<span class="tb-micro">Regime</span>'
        + rs.chip(regime_info["label"], tone=regime_info["tone"])
        + f'<span style="font-size:12.5px;color:{rs.TOKENS["text_body"]};">'
          f'{regime_info["playbook"]}</span>'
        + (f'<span style="font-size:11px;color:{rs.TOKENS["text_muted"]};">'
           f'{" · ".join(bits)}</span>' if bits else "")
        + '</div>'
    )


# One bordered card: the verdict, the regime it was formed in, and the flags that
# produced it are a single object. The border colour is where the decision is
# stated (report_style's `tone` rule — a value's colour states its verdict).
if _show_regime:
    st.markdown(
        rs.card(
            '<div style="display:flex;align-items:flex-start;gap:16px;">'
            '<div style="flex:1;min-width:0;">'
            '<div class="tb-micro">Today\'s verdict</div>'
            f'<div style="font-size:24px;font-weight:800;color:{_vfg};'
            f'line-height:1.15;letter-spacing:-.01em;">{verdict["verdict"]}</div>'
            f'<div style="font-size:13px;color:{rs.TOKENS["text_body"]};'
            f'margin-top:2px;">{verdict["instruction"]}</div>'
            '</div>'
            '<div style="text-align:right;flex-shrink:0;">'
            '<div class="tb-micro">Position size</div>'
            f'<div class="tb-mono" style="font-size:24px;font-weight:800;'
            f'color:{_vfg};line-height:1.15;">{verdict["size_pct"]}%</div>'
            f'<div style="font-size:11px;color:{rs.TOKENS["text_muted"]};">'
            f'max <span class="tb-mono">{verdict["max_trades"]}</span> trade(s) today</div>'
            '</div></div>'
            + _regime_line()
            # Components that could not be measured abstain from the vote (B-1),
            # so the verdict above was formed on LESS than the full weight. Shown
            # explicitly — otherwise the only visible difference between a
            # complete verdict and a partial one is that it has fewer flags.
            + f'<div style="border-top:1px solid {rs.TOKENS["border"]};margin-top:10px;'
              f'padding-top:8px;display:flex;gap:18px;flex-wrap:wrap;">'
            + _flag_col(verdict["caution"], "Caution", "risk", "✗")
            + _flag_col(verdict["favorable"], "Favorable", "good", "✓")
            + _flag_col(verdict.get("not_checked") or [], "Not checked", "neutral", "—")
            + '</div>',
            tone=verdict["tone"]),
        unsafe_allow_html=True,
    )

# ── Inline sentiment refresh ────────────────────────────────────────────
if _show_regime and (_senti_reading is None or (_senti_age or 0) >= 1):
    _rf1, _rf2 = st.columns([1, 3])
    with _rf1:
        _do_refresh = st.button(
            "↻ Refresh sentiment", key="ov_senti_refresh",
            help="Recomputes breadth, sector participation, the 200-SMA regime "
                 "and NIFTY PMax, then re-reads this verdict. Takes ~25s.")
    with _rf2:
        st.caption(
            "No sentiment reading has been computed yet — the verdict above is "
            "running on a missing input." if _senti_reading is None else
            f"Reading is **{_senti_age} day(s) old** (dated "
            f"{_senti_reading['reading_date']}). The verdict above counts that "
            "as a caution flag, so refreshing may change it.")

    if _do_refresh:
        # Queue the ~25s compute on the serial job queue rather than running it
        # inline — so a funnel run in progress is NOT cancelled, and vice-versa.
        _sjid = ui_jobs.submit_unique("Refresh sentiment", senti.compute_sentiment,
                                      persist=True)
        if _sjid is None:
            st.info("A sentiment refresh is already running — click ignored.")
        st.rerun()

    # Consume a completed sentiment refresh (fires once on completion). The cache
    # bust + rerun must happen on the MAIN thread, so it lives here, not in the job.
    _sfin = ui_jobs.get_queue().take_result("Refresh sentiment")
    if _sfin is not None:
        if _sfin.status == "error":
            st.error(f"Sentiment compute failed: {_sfin.error}")
        else:
            cached_latest_sentiment.clear()   # else the ribbon serves stale for ~5 min
            st.session_state["ov_senti_refreshed"] = True

if _show_regime and st.session_state.pop("ov_senti_refreshed", False):
    st.success("Sentiment recomputed — the verdict above reflects the new reading.")

if _show_regime:
    with st.expander("Why this verdict?"):
        # stat_card, not st.metric: the native metric renders its value in the
        # proportional face with its own grey label, which is the one thing on this
        # page that never matched the rest of the figures.
        st.markdown(
            rs.strip([
                rs.stat_card("Min conviction required", verdict["min_conviction"],
                             tone="warn" if verdict["min_conviction"] == "HIGH" else "neutral"),
                rs.stat_card("Caution flags", str(verdict["n_caution"]),
                             tone="risk" if verdict["n_caution"] else "neutral"),
                rs.stat_card("Favorable flags", str(verdict["n_favorable"]),
                             tone="good" if verdict["n_favorable"] else "neutral"),
            ], cols=3),
            unsafe_allow_html=True,
        )
        if verdict["score"] is not None:
            st.caption(f"Sentiment score {verdict['score']} ({verdict['band']}) "
                       f"· reading dated {verdict['as_of']}")
        st.markdown("**Decision rule**")
        for line in verdict["rule"]:
            st.markdown(f"- {line}")
        st.caption(
            "Each sentiment component votes once, by the share of its own weight it "
            "earned. Portfolio heat and stale data can only add caution, never "
            "conviction. Thresholds are defaults — tune them against Verdict "
            "Calibration before trusting the ladder with size."
        )

if _show_regime:
    with st.expander("Set total capital (used for % capital-at-risk)"):
        new_cap = st.number_input(
            "Total capital (₹)", min_value=0.0,
            value=portfolio_summary["total_capital"], step=10000.0,
        )
        if st.button("Save total capital"):
            db.set_setting("total_capital", str(new_cap))
            st.success("Saved — refresh metrics above.")

if _show_regime:
    st.divider()

_SIGNAL_COLORS = {
    "Very Strong": "#16a34a", "Strong": "#65a30d", "Moderate": "#ca8a04",
    "Watch": "#ea580c", "Weak": "#dc2626",
}


def _score_ring_html(score: float, signal: str) -> str:
    """Circular score badge (0-100) coloured by signal band — the 'card ring'."""
    color = _SIGNAL_COLORS.get(signal, "#7a6858")
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


# ── Overall Rating (M1) — one cross-system quality score /100 ──────────────────
# Fuses the four scoring frameworks already computed elsewhere in the app into a
# single triage number, independent of which scanner matched. Weights bias toward
# Minervini as the most-referenced framework on the wiki; tune them in the Scanner
# Hub sidebar (changes apply on the next scan). See
# wiki/analyses/Dashboard-UI-Roadmap.md Milestone 1.
def _rating_color(r: int | None) -> str:
    """Color scale for the Overall Rating badge (matches Market Terminal source)."""
    if r is None:
        return "#7a6858"
    if r >= 85:
        return "#16a34a"   # green
    if r >= 70:
        return "#d97706"   # amber
    if r >= 50:
        return "#6b7280"   # grey
    return "#dc2626"       # red


def _rating_badge_html(card: dict) -> str:
    """Overall Rating pill for the scanner card header. Empty when not computed."""
    if card.get("overall") is None:
        return ""
    r = card["overall"]
    bd = card.get("overall_breakdown", {})
    tip = " · ".join(f"{k} {v}" for k, v in bd.items())
    return (
        f'<span title="Overall Rating (M/TF/C/EW): {tip}" '
        f'style="display:inline-block;background:{_rating_color(r)};color:#fff;'
        f'border-radius:99px;padding:2px 10px;font-size:12px;font-weight:700;'
        f'margin-right:8px;flex-shrink:0;">{r}<span style="font-weight:500;'
        f'opacity:.8;font-size:10px;">/100</span></span>'
    )


def _scanner_stats_html(card: dict) -> str:
    """Compact stat row (RS · Vol Q · From pivot · Vol ×50d) + fail-risk chips.
    Renders only the fields the card actually carries, so scanners that don't
    emit the richer metadata degrade to nothing."""
    def chip(label: str, value: str, color: str = "#5c4a3a") -> str:
        return (
            f'<span style="display:inline-block;background:#f7efe3;border-radius:6px;'
            f'padding:2px 8px;margin:0 6px 4px 0;font-size:11px;color:{color};">'
            f'<b style="color:#7a6858;font-weight:600;">{label}</b> {value}</span>'
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


def _card_action_links(sym: str) -> str:
    """Analyze + chart icons as anchors INSIDE a card's HTML.

    st.link_button can only be placed after a card, which costs a full Streamlit
    row per row rendered — at a hundred rows that is a hundred button rows of
    vertical space and a hundred column containers. As plain <a> tags they cost
    no layout at all and ride along in the card header.
    """
    def icon(href: str, glyph: str, tip: str) -> str:
        return (
            f'<a href="{href}" target="_blank" rel="noopener" title="{tip}" '
            f'style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:23px;height:23px;border-radius:6px;text-decoration:none;'
            f'font-size:12px;line-height:1;background:{rs.TOKENS["surface_alt"]};'
            f'color:{rs.TOKENS["accent"]};border:1px solid {rs.TOKENS["border"]};'
            f'">{glyph}</a>')

    parts = []
    _an = _analyze_url(sym)
    if _an:
        parts.append(icon(_an, "↗", "Analyze — open the 3-POV Council in a new tab"))
    _ch = _chart_url(sym)
    if _ch:
        parts.append(icon(_ch, "👁", "Open in Chart Tool"))
    return "".join(parts)


#: Chip styling per scanner tier (opportunity_hub.scanner_tier). The colour is
#: the message: a row of grey chips is visibly weaker evidence than one with a
#: green chip in it, and an amber chip says "we measured this and it did NOT
#: beat a coin flip" — which a raw count would otherwise hide.
_TIER_CHIP = {
    "measured":   ("good",    "✓ ", "measured to BEAT a random-entry baseline — full weight"),
    "unmeasured": ("neutral", "",   "never backtested — plausible but unproven, half weight"),
    "weak":       ("warn",    "~ ", "measured AT OR BELOW a random-entry baseline — quarter weight"),
    "risk":       ("risk",    "⚠ ", "BEARISH read on the same chart — never counts as confluence"),
}


def _scanner_source_chips(scanners: str | None) -> str:
    """One chip per scanner that fired on a name.

    The count is a single number and the notes are a sentence; neither tells you
    *which* scanners agreed, which is the actual clue — "Falling Wedge + Order
    Block" and "52-Week High + Near Pivot" are the same confluence count and
    completely different reads. Chips carry the tier the ranking applies, and
    the family in the tooltip, so it is visible when five chips are really one
    read repeated.
    """
    names = [s.strip() for s in str(scanners or "").split(",") if s.strip()]
    if not names:
        return ""
    out = []
    for n in names:
        tier = oh.scanner_tier(n)
        tone, mark, tip = _TIER_CHIP[tier]
        fg, bg = rs.tone_colors(tone)
        fam = oh.scanner_family(n)
        title = f"{n}" + (f" · {fam} family" if fam else "") + f" — {tip}"
        out.append(
            f'<span class="tb-chip" title="{title}" '
            f'style="background:{bg};color:{fg};border:1px solid {fg}33;'
            f'margin:0 5px 4px 0;">{mark}{n}</span>')
    return (f'<div style="margin-top:6px;"><span class="tb-micro" '
            f'style="margin-right:6px;">FIRED BY</span>{"".join(out)}</div>')


def _fam_of(row) -> list[str]:
    """Family list for a stored shortlist row.

    Rows written before the family columns existed carry NULL there, so the
    families are re-derived from the stored scanner list rather than rendering
    a blank — the mapping is deterministic, so an old row and a new one show
    the same thing.
    """
    stored = row.get("family_names") if hasattr(row, "get") else None
    if stored and pd.notna(stored):
        return [f.strip() for f in str(stored).split(",") if f.strip()]
    fired = [s.strip() for s in str(row.get("scanners") or "").split(",") if s.strip()]
    fams, _pts, _risk = oh.tally_evidence(fired)
    return fams


def _confluence_chips(n_scanners: int, families: list[str] | int | None) -> str:
    """The headline pair — raw scanner count beside the independent-family count.

    Both are shown on purpose. The raw count is what you asked the pipeline for;
    the family count is what the ranking actually spends, and the gap between
    them is the point: "7 scanners · 2 families" says six of those seven were
    reading the same fact about the chart.
    """
    if isinstance(families, int):
        fam_n, fam_list = families, []
    else:
        fam_list = list(families or [])
        fam_n = len(fam_list)
    detail = (" — " + ", ".join(fam_list)) if fam_list else ""
    # One family = no confluence at all, however many scanners fired.
    fam_tone = "good" if fam_n >= 3 else ("warn" if fam_n == 2 else "neutral")
    ffg, fbg = rs.tone_colors(fam_tone)
    return (
        f'<span class="tb-chip" title="Scanners that fired on this name" '
        f'style="background:{rs.TOKENS["surface_alt"]};'
        f'color:{rs.TOKENS["text_body"]};">{n_scanners} scanners</span>'
        f'<span class="tb-chip" title="Independent scanner families{detail}. '
        f'Correlated scanners are capped at their best member — this is what '
        f'the score spends." style="background:{fbg};color:{ffg};'
        f'font-weight:600;">{fam_n} famil{"y" if fam_n == 1 else "ies"}</span>')


def _card_trade_fundamentals_html(sym: str, card: dict) -> str:
    """CMP · PMax T1/T2/T3 (derived from trade plan) · PE — compact info strip."""
    def _cell(label: str, value: str, color: str = "#5c4a3a") -> str:
        return (
            f'<div style="display:inline-block;background:#f7efe3;border-radius:6px;'
            f'padding:3px 9px;margin:0 5px 4px 0;font-size:11px;">'
            f'<span style="color:#7a6858;font-weight:600;">{label}</span>'
            f'<span style="color:{color};font-weight:700;margin-left:4px;">{value}</span></div>'
        )

    parts: list[str] = []

    # CMP — last close (entry ≈ last close for all scanners)
    cmp = card.get("entry") or card.get("close")
    if cmp is not None:
        parts.append(_cell("CMP", f"₹{cmp:,.1f}"))

    # PMax targets derived from the trade plan emitted by the scanner.
    # T1 = primary target, T2 = 2R extension, T3 = 3R extension.
    entry = card.get("entry") or cmp
    stop  = card.get("stop")
    t1    = card.get("target")
    t2    = card.get("target2")
    if entry is not None and stop is not None and t1 is not None:
        risk = entry - stop
        if risk > 0:
            t2 = t2 or round(entry + 2 * risk, 1)
            t3 = round(entry + 3 * risk, 1)
            parts.append(_cell("T1", f"₹{t1:,.1f}", "#16a34a"))
            parts.append(_cell("T2", f"₹{t2:,.1f}", "#16a34a"))
            parts.append(_cell("T3", f"₹{t3:,.1f}", "#16a34a"))

    # Fundamentals — from cached yfinance .info (disk cache, not network).
    try:
        fund = sc.fetch_fundamentals_yf(sym) or {}
    except Exception:
        fund = {}

    pe = fund.get("pe")
    if pe is not None:
        pe_color = "#b45309" if pe > 40 else ("#16a34a" if pe < 20 else "#5c4a3a")
        parts.append(_cell("PE", f"{pe:.1f}×", pe_color))

    # PEG — <1 cheap-for-growth (green), >2 pricey (amber). 'calc' = derived from
    # PE/earnings-growth rather than the vendor's own ratio (marked with ~).
    peg = fund.get("peg")
    if peg is not None:
        peg_color = "#16a34a" if peg < 1 else ("#b45309" if peg > 2 else "#5c4a3a")
        peg_txt = f"{'~' if fund.get('peg_src') == 'calc' else ''}{peg:.2f}"
        parts.append(_cell("PEG", peg_txt, peg_color))

    eps = fund.get("eps")
    if eps is not None:
        parts.append(_cell("EPS", f"₹{eps:,.2f}", "#16a34a" if eps > 0 else "#b45309"))

    ebitda_cr = fund.get("ebitda_cr")
    if ebitda_cr is not None:
        # ≥1 lakh-crore → abbreviate to "L Cr", else plain "₹N Cr".
        _eb = (f"₹{ebitda_cr / 1e5:,.2f}L Cr" if abs(ebitda_cr) >= 1e5
               else f"₹{ebitda_cr:,.0f} Cr")
        parts.append(_cell("EBITDA", _eb, "#16a34a" if ebitda_cr > 0 else "#b45309"))

    # Cash-flow margin (OCF ÷ revenue). Positive & fat = cash-generative (green);
    # negative = burning operating cash (amber).
    cfm = fund.get("cf_margin_pct")
    if cfm is not None:
        parts.append(_cell("CF%", f"{cfm:.1f}%",
                           "#16a34a" if cfm > 0 else "#b45309"))

    # Promoter pledge — not in yfinance. Read the screener.in disk cache (pure
    # local read, no network); populated by the Scanner Hub "Fetch pledge %"
    # button. High pledge is a risk flag → red above 5%.
    pledge = fund.get("pledge_pct")
    if pledge is None:
        try:
            _plrec = ss.read_pledge_cache(sym)
            if _plrec is not None:
                pledge = _plrec.get("pledge_pct")
        except Exception:
            pledge = None
    if pledge is not None:
        parts.append(_cell("Pledge", f"{pledge:.1f}%",
                           "#dc2626" if pledge > 5 else "#16a34a"))

    if not parts:
        return ""
    return f'<div style="margin:6px 0 2px 0;">{"".join(parts)}</div>'


# Per-render sequence for scanner-card widget keys. Reset every rerun (Streamlit
# re-executes this whole script top-to-bottom), so keys are deterministic and
# stable across identical reruns, yet unique even when the SAME symbol+scanner
# legitimately renders in more than one section of a single page (e.g. the
# Opportunity-Hub pipeline funnel and the single-scanner list both surfacing the
# same hit) — which otherwise collides on key=f"sc_s_{sym}_{scanner_name}".
_scanner_card_key_seq = {"n": 0}


def _render_scanner_card(card: dict, scanner_name: str, header_html: str = "") -> None:
    sym = card["symbol"]
    sym_clean = sym.upper().replace(".NS", "")
    pattern_type = card.get("pattern_type", scanner_name)
    _scanner_card_key_seq["n"] += 1
    _kseq = _scanner_card_key_seq["n"]

    # ── Inline action icons (header row, all open in new tab) ─────────────
    def _icon_link(href: str, glyph: str, tip: str, small: bool = False) -> str:
        sz = "11px" if small else "13px"
        w = "22px" if small else "24px"
        return (
            f'<a href="{href}" target="_blank" rel="noopener" title="{tip}"'
            f' style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:{w};height:{w};border-radius:6px;text-decoration:none;'
            f'font-size:{sz};line-height:1;background:#f7efe3;'
            f'color:#d97706;border:1px solid #f0e0cc;margin-left:4px;">'
            f'{glyph}</a>'
        )

    action_icons = ""
    _ch = _chart_url(sym)
    if _ch:
        action_icons += _icon_link(_ch, "👁", "Chart Tool (in-app)")
    _an = _analyze_url(sym)
    if _an:
        action_icons += _icon_link(_an, "↗", "Stock Analyzer (in-app)")
    # External links
    _tv_url = f"https://www.tradingview.com/chart/?symbol=NSE%3A{sym_clean}"
    action_icons += _icon_link(_tv_url, "📈", "Open on TradingView")
    _sc_url = f"https://www.screener.in/company/{sym_clean}/consolidated/"
    action_icons += _icon_link(_sc_url, "S", "Open on Screener.in", small=True)
    _gf_url = f"https://www.google.com/finance/quote/{sym_clean}:NSE"
    action_icons += _icon_link(_gf_url, "G", "Open on Google Finance", small=True)
    _tweet = (f"https://twitter.com/intent/tweet?text=%23{sym_clean}+%23NSE+"
              f"{pattern_type.replace(' ', '+')}+scanner+hit+via+%23TradingBramha")
    action_icons += _icon_link(_tweet, "𝕏", "Share on X / Twitter", small=True)

    # Tags shown as a compact row of muted spans
    metrics_html = "  ·  ".join(
        f'<span style="font-size:11px;color:#7a6858;">{t}</span>'
        for t in card.get("tags", [])
    )

    # Reasons: warning lines in amber, confirmation lines in green — each on its
    # own row inside the card body.
    reasons_html = "".join(
        (f'<div style="display:flex;align-items:baseline;margin-bottom:4px;'
         f'font-size:12px;color:#b45309;">'
         f'<span style="font-weight:700;margin-right:5px;flex-shrink:0;">⚠</span>'
         f'{r.lstrip("⚠").strip()}</div>')
        if r.startswith("⚠") else
        (f'<div style="display:flex;align-items:baseline;margin-bottom:4px;'
         f'font-size:12px;color:#5c4a3a;">'
         f'<span style="color:#16a34a;font-weight:700;margin-right:5px;flex-shrink:0;">✓</span>'
         f'{r}</div>')
        for r in card.get("reasons", [])
    )

    # Score ring only when the card carries a graded score + signal.
    ring_html = (
        _score_ring_html(card["score"], card["signal"])
        if "signal" in card and "score" in card else ""
    )

    stats_html  = _scanner_stats_html(card)
    trade_html  = _card_trade_fundamentals_html(sym, card)

    # ── Horizontal card layout ──────────────────────────────────────────────
    #  ┌─────────────────────────────────────────────────────────────────────┐
    #  │ [avatar] [Symbol  badge  tags]             [score ring] [↗] [👁]   │
    #  │ [stats chips row]                                                   │
    #  │ [CMP · T1 · T2 · T3 · PE strip]                                    │
    #  │ [reasons]                                                           │
    #  └─────────────────────────────────────────────────────────────────────┘
    st.markdown(
        f'<div style="border:1px solid #f0e0cc;border-radius:12px;padding:14px 16px;'
        f'margin-bottom:4px;background:#fffdfa;'
        f'box-shadow:0 1px 3px rgba(120,80,40,0.06);">'
        # Optional confluence header (Opportunity-Hub pipeline) rides INSIDE the
        # card so it sits flush on top. Passing it here instead of a separate
        # st.markdown avoids Streamlit's inter-element gap, which otherwise reads
        # as an extra blank line between the chips and the card. Empty for every
        # other caller, so their cards are unchanged.
        f'{header_html}'
        # Header row: avatar · identity · right cluster.
        # flex-wrap + a real min-width on the identity column so that in a narrow
        # 3-up card the fixed-width ring+icons cluster DROPS to its own line
        # instead of starving the identity column to ~0px (which forced the text
        # to wrap character-by-character — "1.2% fro m 52w high").
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;'
        f'flex-wrap:wrap;">'
        # Avatar
        f'<div style="width:34px;height:34px;border-radius:8px;flex-shrink:0;'
        f'background:linear-gradient(135deg,#fbbf24,#ea580c);color:#fff;'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-weight:700;font-size:15px;">{sym[0]}</div>'
        # Identity column — never collapses below a readable width.
        f'<div style="flex:1 1 150px;min-width:130px;">'
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;">'
        f'{_rating_badge_html(card)}'
        f'<span style="font-size:15px;font-weight:700;color:#3a2a1e;">{sym}</span>'
        f'<span style="background:#fff1e0;color:#c2410c;padding:1px 8px;'
        f'border-radius:99px;font-size:11px;font-weight:600;">{pattern_type}</span>'
        f'</div>'
        f'<div style="margin-top:3px;">{metrics_html}</div>'
        f'</div>'
        # Right cluster: score ring + action icons. margin-left:auto right-aligns
        # it on a wide card; flex-wrap lets it (and the icons) drop cleanly to
        # their own line on a narrow one rather than overflowing.
        f'<div style="display:flex;align-items:center;flex-shrink:0;gap:2px;'
        f'flex-wrap:wrap;justify-content:flex-end;margin-left:auto;">'
        f'{ring_html}{action_icons}'
        f'</div>'
        f'</div>'
        # Stats + trade plan + reasons
        f'{stats_html}'
        f'{trade_html}'
        f'{reasons_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
    # Action buttons row — Streamlit widgets (server callbacks)
    _b1, _b2, _b3, _b4 = st.columns(4)
    with _b1:
        if st.button("★", key=f"sc_s_{sym}_{scanner_name}_{_kseq}",
                     help=f"Save {sym} to scanner hits",
                     use_container_width=True):
            db.save_scanner_hit(sym, scanner_name, card.get("pattern_type", ""))
            st.toast(f"★ Saved {sym_clean}")
    with _b2:
        if st.button("♥", key=f"sc_wl_{sym}_{scanner_name}_{_kseq}",
                     help=f"Add {sym_clean} to Watchlist",
                     use_container_width=True):
            db.add_watchlist_symbol(sym_clean, f"Scanner Hub — {scanner_name}")
            st.toast(f"♥ {sym_clean} → Watchlist")
    with _b3:
        if st.button("↗", key=f"sc_an_{sym}_{scanner_name}_{_kseq}",
                     help=f"Open {sym_clean} in Stock Analyzer",
                     use_container_width=True):
            st.session_state["current_page"] = "Stock Analyzer"
            st.session_state["sa_symbol_override"] = sym_clean
            st.rerun()
    with _b4:
        if st.button("⊕", key=f"sc_ro_{sym}_{scanner_name}_{_kseq}",
                     help=f"Add {sym_clean} to Analyzer Roster (batch queue)",
                     use_container_width=True):
            roster = st.session_state.setdefault("sa_roster", [])
            if sym_clean not in roster:
                roster.append(sym_clean)
            st.toast(f"⊕ {sym_clean} → Roster ({len(roster)})")


def _render_export_controls(model: dict, key: str) -> None:
    """Export strip for a day's funnel: detailed PDF, shareable PNG, chat text.

    Rendering is lazy — the PDF and PNG are only built when their button is
    pressed, because both cost real work and most visits to this page will not
    export anything. Streamlit's `download_button` needs the bytes up front, so
    the two sit behind a build toggle rather than being produced on every rerun.
    """
    st.markdown(rs.section("Export this day"), unsafe_allow_html=True)
    st.caption("Every export carries the market regime it was produced in, the "
               "scanner tiers, and the confluence caveat — a shortlist that "
               "leaves this machine has to explain itself without you standing "
               "next to it.")

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        want_pdf = st.button("📄 Build detailed PDF", key=f"{key}_pdf_go",
                             use_container_width=True)
    with c2:
        want_png = st.button("🖼 Build share card", key=f"{key}_png_go",
                             use_container_width=True)
    with c3:
        card_top = st.slider("Names on the card", 3, 15, 8, key=f"{key}_top",
                             help="The PDF always contains every name; this "
                                  "only caps the shareable image.")

    stamp = model["as_of"].isoformat()
    if want_pdf:
        with st.spinner("Rendering the report…"):
            try:
                pdf = orep.render_pdf(model)
            except Exception as exc:
                st.error(f"PDF render failed: {exc}")
                pdf = None
        if pdf:
            st.download_button(
                f"⬇ opportunity-funnel-{stamp}.pdf", pdf,
                file_name=f"opportunity-funnel-{stamp}.pdf",
                mime="application/pdf", type="primary", key=f"{key}_pdf_dl")
            st.caption(f"{len(pdf) / 1024:.0f} KB · every name, with the "
                       f"scanners grouped by family and their measured tier · "
                       f"text is selectable and searchable.")

    if want_png:
        with st.spinner("Drawing the card…"):
            try:
                png = orep.render_png(model, top=int(card_top))
            except Exception as exc:
                st.error(f"Card render failed: {exc}")
                png = None
        if png:
            st.download_button(
                f"⬇ opportunity-card-{stamp}.png", png,
                file_name=f"opportunity-card-{stamp}.png",
                mime="image/png", type="primary", key=f"{key}_png_dl")
            st.caption(f"{len(png) / 1024:.0f} KB · 1080px wide — the size X, "
                       f"LinkedIn and WhatsApp accept without downscaling.")
            st.image(png, width=520)

    with st.expander("Copy as text (WhatsApp / Telegram)"):
        st.code(orep.render_text(model, top=int(card_top)), language=None)


def _render_pipeline_card(hit: dict) -> None:
    """One Opportunity-Hub pipeline result: the confluence header, then the
    normal scanner card for the strongest pattern that fired.

    Deliberately still a CARD in the 3-column grid — the confluence data rides
    on top of the existing card rather than flattening the results into a table,
    because the reasons/levels under each hit are the part you act on.
    """
    sym = hit["symbol"]
    best = hit["best_scanner"] or ""
    risk = hit.get("risk_flags") or []
    warn = ""
    if risk:
        _rfg, _rbg = rs.tone_colors("risk")
        warn = (f'<div style="margin-top:6px;padding:5px 8px;border-radius:6px;'
                f'background:{_rbg};color:{_rfg};font-size:11.5px;">'
                f'⚠ <b>{", ".join(risk)}</b> also fired — there is a bearish read '
                f'on this same chart. Not counted as confluence.</div>')
    # The confluence header rides on top of the card. It is handed to
    # _render_scanner_card as header_html so it renders inside the SAME markdown
    # block as the card — one element, no Streamlit inter-element gap. Rendering
    # it as its own st.markdown (as before) left an extra blank line between the
    # chips and the card in the Opportunity-Hub pipeline output.
    header_html = (
        f'<div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;'
        f'margin-bottom:4px;">'
        f'{_confluence_chips(len(hit["scanners"]), hit["families"])}'
        f'<span class="tb-chip" title="Rank score — 0.45×Overall Rating + '
        f'0.30×best scanner score + 0.25×family-capped confluence" '
        f'style="background:{rs.TOKENS["surface_alt"]};'
        f'color:{rs.TOKENS["text_body"]};">score '
        f'{(hit.get("rank_score") or 0):.1f}</span></div>'
        f'{_scanner_source_chips(", ".join(hit["scanners"]))}{warn}')
    card = dict(hit["best_card"] or {})
    card["symbol"] = sym
    card["overall"] = hit.get("overall")
    card["overall_breakdown"] = hit.get("overall_breakdown") or {}
    _render_scanner_card(card, best, header_html=header_html)


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
# Volume Shockers (Darvas) — shared window, used twice on Home
# ------------------------------------------------------------------------------
# The lens was buried three clicks deep (Market Intel ▸ Trending Stocks ▸ tab 2),
# which is also why that page has since folded into Home entirely,
# so it now renders on Home as well. Both call the SAME function — one definition,
# two mount points, no drift.
#
# Criteria are Chartink's Darvas volume-shocker scan verbatim (see
# trending_stocks.darvas_volume_shockers): volume > 2x SMA(volume,10) AND a >=5%
# move in either direction. The knobs are exposed because the reference scan's
# 2x/5% are conventions, not measured thresholds.
#
# Home must stay cheap to open, so the scan runs only when asked: the button
# flips a session flag, the cached result is reused for 30 minutes after that.
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=900, show_spinner=False)
def _trend_bhav():
    import trending_stocks as _ts
    return _ts.load_bhav()


@st.cache_data(ttl=1800, show_spinner=False)
def _darvas_volume(top_n: int, vol_mult: float, move_pct: float, min_turnover_cr: float):
    import trending_stocks as _ts
    bhav, _ = _trend_bhav()
    if bhav is None:
        return {"error": "no bhavcopy frame", "rows": None}
    _r = _ts.darvas_volume_shockers(
        bhav, top_n=top_n, vol_mult=vol_mult, move_pct=move_pct,
        min_turnover=float(min_turnover_cr) * 1e7)
    _r["trade_date"] = _trend_bhav()[1]
    return _r


def _darvas_rows_table(df, key_prefix: str):
    """The hit list, with the same chart-icon link family the other tables use,
    plus row-select → ♥ add to watchlist.

    Streamlit cannot put a real button INSIDE a dataframe cell, so the icon is a
    row selection followed by one ♥ button — which is also the cheaper gesture
    when the answer is usually "these three", not "this one".
    """
    if df is None or getattr(df, "empty", True):
        st.info("No name clears both conditions in this session. "
                "That is a normal reading — the scan is meant to be quiet.")
        return
    out = _with_chart_family(df.copy(), "symbol")
    cfg = dict(_chart_family_colcfg())
    cfg["symbol"] = st.column_config.TextColumn("Symbol", width="small")
    cfg["close"] = st.column_config.NumberColumn("LTP", format="%.2f")
    cfg["chg_pct"] = st.column_config.NumberColumn("Chg%", format="%.2f%%")
    cfg["direction"] = st.column_config.TextColumn("Dir", width="small")
    cfg["volume"] = st.column_config.NumberColumn("Volume", format="%d")
    cfg["sma_vol10"] = st.column_config.NumberColumn("SMA vol(10)", format="%d")
    cfg["multiple"] = st.column_config.NumberColumn("x SMA10", format="%.1f")
    cfg["turnover_cr"] = st.column_config.NumberColumn("Turnover ₹Cr", format="%.1f")
    # Green/red on Chg%. Colour is REDUNDANT here, never load-bearing: the Dir
    # column already says UP/DOWN and the number carries its own sign, so the
    # table still reads correctly in greyscale or with colour-blindness — the
    # same rule gain_loss_badge() follows.
    def _chg_color(v):
        if v is None or pd.isna(v):
            return ""
        return (f"color:{rs.TOKENS['good']};font-weight:600" if v > 0
                else f"color:{rs.TOKENS['risk']};font-weight:600" if v < 0
                else "")

    _show = out.style.map(_chg_color, subset=["chg_pct"])
    _sel = st.dataframe(_show, width="stretch", hide_index=True, column_config=cfg,
                        key=f"{key_prefix}_tbl", on_select="rerun",
                        selection_mode="multi-row")
    try:
        _rows = list(_sel.selection.rows)
    except Exception:
        _rows = []
    _picked = [str(df.iloc[i]["symbol"]) for i in _rows if i < len(df)]

    _wc1, _wc2 = st.columns([1, 3])
    with _wc1:
        if st.button(f"♥ Add {len(_picked) or ''} to watchlist".replace("  ", " "),
                     key=f"{key_prefix}_addwl", disabled=not _picked,
                     use_container_width=True, type="primary" if _picked else "secondary"):
            for _s in _picked:
                db.add_watchlist_symbol(_s, "Volume Shockers · Darvas")
            st.toast(f"♥ {len(_picked)} → Watchlist")
            st.rerun()
    with _wc2:
        st.caption("Tick one or more rows, then ♥ — they land on the Watchlist "
                   "tagged with the scan that found them."
                   + (f"  Selected: **{', '.join(_picked)}**" if _picked else ""))


def _darvas_window(key_prefix: str, *, compact: bool = False):
    """Render the Volume Shockers (Darvas) window.

    `compact` is the Home mounting: no sliders, scan runs on click only.
    """
    st.markdown("#### 📊 Volume Shockers · Darvas")
    st.caption(
        "Chartink's *Volume Shockers (rising volumes) — Darvas* scan, computed "
        "locally: **volume > 2× SMA(volume,10)** *and* a **≥5% move** up or down "
        "vs the previous close. An attention list, not a signal — a box only "
        "breaks on conviction volume, but volume alone is a question, not an entry."
    )
    # Chartink applies NO liquidity floor, so its list carries names trading a few
    # thousand shares (SURYALA: 3,061). The floor defaults to 0 here for parity —
    # raise it when you want a list you can actually take size in.

    def _refresh():
        """Drop the cached bhavcopy AND the cached scan, then re-run.

        Both, not just the scan: the scan is a pure function of the bhavcopy, so
        clearing it alone would recompute the same numbers off the same cached
        frame and look broken during the hour after the close, which is exactly
        when a refresh is worth pressing.
        """
        _trend_bhav.clear()
        _darvas_volume.clear()
        st.session_state[f"{key_prefix}_refreshed"] = datetime.now().strftime("%H:%M:%S")
        st.rerun()

    if compact:
        _top, _mult, _move, _minto = 60, 2.0, 5.0, 0.0
        _go = st.session_state.get(f"{key_prefix}_ran", False)
        if not _go:
            if st.button("Run volume shocker scan", key=f"{key_prefix}_run",
                         type="primary"):
                st.session_state[f"{key_prefix}_ran"] = True
                st.rerun()
            st.caption("Not run yet — Home never fetches on load.")
            return
        _rc1, _rc2 = st.columns([1, 4])
        with _rc1:
            if st.button("↻ Refresh", key=f"{key_prefix}_refresh",
                         use_container_width=True,
                         help="Re-download the bhavcopy and re-run the scan. "
                              "Results are cached for 30 minutes otherwise."):
                _refresh()
        with _rc2:
            _last = st.session_state.get(f"{key_prefix}_refreshed")
            st.caption(f"Refreshed at **{_last}**." if _last else
                       "Cached for 30 minutes — press ↻ for a fresh pull.")
    else:
        _c1, _c2, _c3, _c4 = st.columns(4)
        with _c1:
            _top = st.slider("Rows", 10, 200, 60, step=10, key=f"{key_prefix}_top",
                             help="A cap on the TABLE, not on the scan — the hit "
                                  "count beside it is always the full number.")
        with _c2:
            _mult = st.slider("× SMA(volume,10)", 1.5, 10.0, 2.0, step=0.5,
                              key=f"{key_prefix}_mult",
                              help="Chartink's scan uses 2×. Raise it to shorten the list.")
        with _c3:
            _move = st.slider("Min move %", 1.0, 15.0, 5.0, step=0.5,
                              key=f"{key_prefix}_move",
                              help="Chartink's scan uses ±5%, either direction.")
        with _c4:
            _minto = st.number_input("Min turnover ₹Cr", 0.0, 500.0, 0.0, step=1.0,
                                     key=f"{key_prefix}_minto",
                                     help="Liquidity floor. 0 = Chartink parity "
                                          "(it applies none). Raise it to drop names "
                                          "whose 5% move is arithmetic on 3,000 shares.")

    if not compact:
        _rc1, _rc2 = st.columns([1, 4])
        with _rc1:
            if st.button("↻ Refresh", key=f"{key_prefix}_refresh",
                         use_container_width=True,
                         help="Re-download the bhavcopy and re-run the scan."):
                _refresh()
        with _rc2:
            _last = st.session_state.get(f"{key_prefix}_refreshed")
            st.caption(f"Refreshed at **{_last}**." if _last else
                       "Cached for 30 minutes — press ↻ for a fresh pull.")

    with st.spinner("Scanning the bhavcopy, then 10-day volume history…"):
        _res = _darvas_volume(int(_top), float(_mult), float(_move), float(_minto))

    if _res.get("error"):
        st.warning(f"Scan unavailable: {_res['error']}")
        return

    # The bhavcopy is EOD and publishes after the close, so on any intraday run
    # this scan is YESTERDAY's session while Chartink is showing today's. That is
    # the single most likely reason two lists disagree, so it is stated first and
    # in the open, not buried in a tooltip.
    st.caption(f"Session **{_res.get('trade_date') or '—'}** (NSE EOD bhavcopy). "
               f"Chartink runs intraday — compare like sessions before concluding "
               f"the filters differ.")
    _n_hits = _res.get("n_hits", 0)
    _n_shown = 0 if _res.get("rows") is None else len(_res["rows"])
    _n_price = _res.get("n_price", 0)
    _n_scanned = _res.get("n_scanned", 0)
    st.caption(
        f"**{_n_hits}** hits"
        + (f" (showing {_n_shown} — raise *Rows*)" if _n_shown < _n_hits else "")
        + f" · {_n_price} names cleared the ±{_res.get('move_pct', 5)}% price gate "
        f"out of {_res.get('n_liquid', 0):,} of {_res.get('n_universe', 0):,} EQ rows "
        f"· {_n_scanned} of those had 9 prior sessions of volume history to test the "
        f"{_res.get('vol_mult', 2)}× condition."
    )
    if _n_price and _n_scanned < _n_price:
        # This is the one gap Chartink does not have: it holds its own volume
        # history, we fetch ours. A name too new (or unmatched on yfinance) is
        # NOT reported as "no spike" — it is reported as untested.
        st.caption(f"⚠ {_n_price - _n_scanned} name(s) could not be tested — no "
                   f"10-session volume history from the feed. Untested, not rejected.")
    _darvas_rows_table(_res.get("rows"), key_prefix)


# ──────────────────────────────────────────────────────────────────────────────
# Home — the landing page
# ------------------------------------------------------------------------------
# The app used to open straight into Screener, which meant the first screen was a
# working tool with no map of the other seventeen pages. Home is that map.
#
# Layout language borrowed from a public SaaS pricing page the user supplied as a
# reference — gradient hero card, headline + subtitle, a grid of bordered cards
# with tick-listed contents, quiet disclaimer footer. Only the LAYOUT was taken:
# colours come from report_style.TOKENS (the cream/amber system the rest of the
# dashboard already uses), not from the reference's purple, and no branding,
# wording or pricing was copied.
#
# Deliberately cheap to render: no network calls, no scans. The only dynamic
# figures are a scanner count read from the in-process registry and the last
# PERSISTED sentiment row (a DB read the ribbon already does). Home must never be
# the reason the app feels slow to open.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Hidden Treasures":
    st.subheader("Hidden Treasures")
    st.caption("Small and micro-cap names the main funnel structurally misses — "
               "ranked by **institutional conviction** (FII+DII accumulation rate, "
               "promoter conduct, pledge veto) from free NSE shareholding data. "
               "Quality overlay adds ROCE / OPM / D/E from yfinance. "
               "**Unvalidated** — a discovery lens, not an edge.")

    _ht_c1, _ht_c2 = st.columns([2, 1])
    with _ht_c1:
        _ht_kind = st.radio("Universe",
                            ["NSE Both", "Smallcap-250", "Microcap-250",
                             "BSE Both", "BSE SmallCap", "BSE MicroCap",
                             "All (NSE+BSE)"],
                            horizontal=True, key="ht_kind")
    with _ht_c2:
        _ht_enrich = st.checkbox("Quality overlay (slower)", value=True, key="ht_enrich",
                                 help="Adds ROCE/OPM/D/E/Market Cap from yfinance — one call per name")
    _ht_limit = st.slider("Show top N", min_value=5, max_value=100, value=25,
                           step=5, key="ht_limit")
    _kind_map = {
        "NSE Both": "both", "Smallcap-250": "smallcap250", "Microcap-250": "microcap250",
        "BSE Both": "bse", "BSE SmallCap": "bse_smallcap", "BSE MicroCap": "bse_microcap",
        "All (NSE+BSE)": "all",
    }

    if st.button("Discover", type="primary", key="ht_run"):
        with st.spinner("Scoring small/micro-cap universe…"):
            try:
                _ht_kind_val = _kind_map[_ht_kind]
                _ht_res = scd.discover(kind=_ht_kind_val,
                                       limit=_ht_limit,
                                       enrich=_ht_enrich)
                st.session_state["ht_result"] = _ht_res
                _saved_n = db.save_hidden_treasures_run(
                    _ht_res["hits"],
                    universe_kind=_ht_kind_val,
                    universe_size=_ht_res.get("universe", 0))
                st.toast(f"💾 {_saved_n} hits saved to history")
            except Exception as _e:
                st.error(f"Discovery failed: {_e}")

    _ht_res = st.session_state.get("ht_result")
    if _ht_res is not None:
        st.markdown(rs.section(f"Top {len(_ht_res['hits'])} of {_ht_res['universe']} "
                               f"({_ht_res['cached']} cached)"),
                    unsafe_allow_html=True)

        for _i in range(0, len(_ht_res["hits"]), 3):
            _cols = st.columns(3)
            for _col, _h in zip(_cols, _ht_res["hits"][_i:_i + 3]):
                with _col:
                    _sym = _h["symbol"]
                    _q = _h.get("quality") or {}
                    _qual_chips = ""
                    if _q:
                        _qparts = []
                        if _q.get("roce") is not None:
                            _c = rs.TOKENS["good"] if _q["roce"] >= scd.ROCE_GOOD else rs.TOKENS["text"]
                            _qparts.append(f'<span style="color:{_c};">ROCE {_q["roce"]:.1f}%</span>')
                        if _q.get("opm") is not None:
                            _c = rs.TOKENS["good"] if _q["opm"] >= scd.OPM_GOOD else rs.TOKENS["text"]
                            _qparts.append(f'<span style="color:{_c};">OPM {_q["opm"]:.1f}%</span>')
                        if _q.get("debt_to_equity") is not None:
                            _c = rs.TOKENS["risk"] if _q["debt_to_equity"] > scd.DE_MAX else rs.TOKENS["text"]
                            _qparts.append(f'<span style="color:{_c};">D/E {_q["debt_to_equity"]:.2f}</span>')
                        _qual_chips = '<div style="margin-top:4px;font-size:11px;">' + \
                                      " · ".join(_qparts) + '</div>'

                    _pledge_s = ""
                    if _h.get("pledge_flag"):
                        _pledge_s = f'<div style="font-size:11px;color:{rs.TOKENS["risk"]};">⚠ Pledge {_h["pledge_pct"]:.1f}%</div>'
                    elif _h.get("pledge_pct") is not None:
                        _pledge_s = f'<div style="font-size:11px;">Pledge {_h["pledge_pct"]:.1f}%</div>'

                    # Market cap chip
                    _mcap_s = ""
                    if _q and _q.get("market_cap_cr") is not None:
                        _mc_cr = _q["market_cap_cr"]
                        _mc_label = (f"₹{_mc_cr/100:.1f}K Cr" if _mc_cr >= 10000
                                     else f"₹{_mc_cr:.0f} Cr")
                        _mcap_s = f'<div style="font-size:11px;color:{rs.TOKENS["text"]};">MCap {_mc_label}</div>'

                    _pd = _h.get("promoter_delta")
                    _prom_s = f'Prom {_pd:+.2f}pp' if _pd is not None else 'Prom —'

                    # Action icon row (same family as Scanner Hub cards)
                    _sym_clean = _sym.upper().replace(".NS", "")
                    def _ht_icon(href, glyph, tip, small=False):
                        sz = "11px" if small else "13px"
                        w = "22px" if small else "24px"
                        return (
                            f'<a href="{href}" target="_blank" rel="noopener" title="{tip}"'
                            f' style="display:inline-flex;align-items:center;justify-content:center;'
                            f'width:{w};height:{w};border-radius:6px;text-decoration:none;'
                            f'font-size:{sz};line-height:1;background:#f7efe3;'
                            f'color:#d97706;border:1px solid #f0e0cc;margin-left:4px;">'
                            f'{glyph}</a>')
                    _ht_icons = ""
                    _ht_ch = _chart_url(_sym)
                    if _ht_ch:
                        _ht_icons += _ht_icon(_ht_ch, "👁", "Chart Tool (in-app)")
                    _ht_an = _analyze_url(_sym)
                    if _ht_an:
                        _ht_icons += _ht_icon(_ht_an, "↗", "Stock Analyzer (in-app)")
                    _ht_icons += _ht_icon(f"https://www.tradingview.com/chart/?symbol=NSE%3A{_sym_clean}", "📈", "Open on TradingView")
                    _ht_icons += _ht_icon(f"https://www.screener.in/company/{_sym_clean}/consolidated/", "S", "Open on Screener.in", small=True)
                    _ht_icons += _ht_icon(f"https://www.google.com/finance/quote/{_sym_clean}:NSE", "G", "Open on Google Finance", small=True)
                    _ht_icons += _ht_icon(f"https://twitter.com/search?q=%23{_sym_clean}+%23NSE&src=typed_query", "𝕏", "Search on X / Twitter", small=True)

                    st.markdown(
                        rs.card(
                            f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                            f'<div style="display:flex;align-items:baseline;gap:8px;">'
                            f'<span style="font-weight:700;font-size:15px;color:{rs.TOKENS["text"]};">'
                            f'{_sym}</span>'
                            f'<span style="font-size:12px;color:{rs.TOKENS["accent"]};">'
                            f'{_h["score"]:.0f}</span>'
                            f'</div>'
                            f'<div style="display:flex;align-items:center;flex-wrap:wrap;">'
                            f'{_ht_icons}</div>'
                            f'</div>'
                            f'<div style="font-size:11px;color:{rs.TOKENS["text"]};">'
                            f'{_h.get("name", "")}</div>'
                            f'<div style="margin-top:4px;font-size:11px;">'
                            f'FII+DII {_h["inst_delta"]:+.2f}pp · {_prom_s}'
                            f'</div>'
                            f'{_qual_chips}{_mcap_s}{_pledge_s}',
                            emphasis=False),
                        unsafe_allow_html=True)

                    _b1, _b2 = st.columns(2)
                    with _b1:
                        if st.button("♥ Watchlist", key=f"ht_wl_{_sym}", use_container_width=True):
                            db.add_watchlist_symbol(_sym, "Hidden Treasures")
                            st.toast(f"♥ {_sym} → Watchlist")
                    with _b2:
                        if st.button("↗ Analyze", key=f"ht_an_{_sym}", use_container_width=True):
                            st.session_state["current_page"] = "Stock Analyzer"
                            st.session_state["sa_symbol_override"] = _sym
                            st.rerun()

                    with st.expander("reasons"):
                        for _r in _h.get("reasons", []):
                            st.markdown(f"- {_r}")


# What moved today — four lenses (see trending_stocks.py)
#
# This was its own "Trending Stocks" page until 2026-09-04. It is now a lazy
# section on Home: the page was one nav click that only ever led here, and Home
# already rendered one of its four lenses.
# ──────────────────────────────────────────────────────────────────────────────
# Deliberately a TABLE, not the Scanner Hub card grid. A ranked "what moved" list
# is a different job from confluence results: the reader scans a column to find
# the outlier, which cards make harder. The cards-not-tables convention stays
# where it belongs — on Scanner Hub.

@st.cache_data(ttl=300, show_spinner=False)
def _trend_movers(top_n: int, min_turnover: float):
    import trending_stocks as _ts
    bhav, _ = _trend_bhav()
    # Use real-time yfinance data as the leading source, with fallback to bhavcopy
    return _ts.price_movers_realtime(bhav, top_n=top_n, min_turnover=min_turnover)


@st.cache_data(ttl=1800, show_spinner=False)
def _trend_volume(top_n: int):
    import trending_stocks as _ts
    bhav, _ = _trend_bhav()
    return _ts.volume_shockers(top_n=top_n, bhav=bhav)


@st.cache_data(ttl=1800, show_spinner=False)
def _trend_extremes(universe_n: int, top_n: int, near_pct: float):
    """Both range lenses off ONE batched history download — two calls would be
    two minutes for the same bytes."""
    import trending_stocks as _ts
    bhav, _ = _trend_bhav()
    uni = _ts.liquid_universe(bhav, universe_n)
    hist = _ts._batch_history(uni, period="max")
    return {
        "week52": _ts.range_extremes(uni, window=_ts.WEEK52_BARS, near_pct=near_pct,
                                     top_n=top_n, hist=hist),
        "alltime": _ts.range_extremes(uni, window=None, near_pct=near_pct,
                                      top_n=top_n, hist=hist),
        "n_history": len(hist),
        "universe_n": len(uni),
    }


def render_trending_stocks(key_prefix: str = "tr", *, include_volume: bool = True) -> None:
    """The four "what moved today" lenses.

    Extracted from its own page so it can mount on Home, which is where it now
    lives — the page was one nav click that only ever led here, and Home already
    carried one of the four lenses (`_darvas_window`).

    `include_volume=False` drops the Volume Shockers tab for the Home mounting,
    where the Darvas window is already rendered above this section. The
    cause-attributed spike scan travels with the section either way, since it
    answers a different question ("why did this spike?") and has no other home.

    `key_prefix` namespaces the widget keys: Home and any future mounting must
    not collide on `st.slider(key=...)`.
    """
    st.caption("Real-time movers from yfinance (refreshes every 5 min). "
               "**Attention lists, not signals** — a move or a spike is a *question* "
               "(\"why did this happen?\"), not a position.")

    _tr_bhav, _tr_date = _trend_bhav()
    if _tr_bhav is None:
        st.error("No NSE bhavcopy reachable — markets may be closed or the feed is down.")
    else:
        _tc1, _tc2, _tc3 = st.columns([1, 1, 1])
        with _tc1:
            _tr_top = st.slider("Rows per list", 5, 40, 15, step=5, key=f"{key_prefix}_top")
        with _tc2:
            _tr_uni = st.slider("Universe (52W/ATH)", 50, 400, 200, step=50, key=f"{key_prefix}_uni",
                                help="Top N by traded value. NSE publishes no 52-week "
                                     "columns, so these two lenses compute from history "
                                     "— one download per name, hence a bounded universe.")
        with _tc3:
            _tr_minto = st.number_input("Min turnover (₹ Cr)", 0.0, 500.0, 5.0, step=1.0,
                                        key=f"{key_prefix}_minto",
                                        help="Without a floor the movers list is almost "
                                             "entirely penny stocks: a ₹3 share moving "
                                             "19% is arithmetic, not information.")
        st.caption(f"Session **{_tr_date or '—'}** · {len(_tr_bhav):,} EQ rows")

        # The Volume Shockers tab is dropped on Home, where `_darvas_window` is
        # already rendered above this section — the same lens twice on one screen
        # would be the "menu of a menu" mistake Home was cleaned up to avoid.
        _labels = (["Price Movers"] + (["Volume Shockers"] if include_volume else [])
                   + ["52 Week High Low", "All Time High Low"])
        _tabs = st.tabs(_labels)
        _t_mv = _tabs[0]
        _t_vol = _tabs[1] if include_volume else None
        _t_52, _t_ath = _tabs[-2], _tabs[-1]

        def _tr_table(df):
            """Render one lens as a table with the chart-icon link family."""
            if df is None or df.empty:
                st.info("Nothing qualifies in this session.")
                return
            out = df.copy()
            out = _with_chart_family(out, "symbol")
            colcfg = dict(_chart_family_colcfg())
            colcfg["symbol"] = st.column_config.TextColumn("Symbol", width="small")
            if "close" in out.columns:
                colcfg["close"] = st.column_config.NumberColumn("LTP", format="%.2f")
            if "chg" in out.columns:
                colcfg["chg"] = st.column_config.NumberColumn("Chg", format="%.2f")
            if "chg_pct" in out.columns:
                colcfg["chg_pct"] = st.column_config.NumberColumn("Chg%", format="%.2f%%")
            if "turnover" in out.columns:
                out["turnover"] = out["turnover"] / 1e7
                colcfg["turnover"] = st.column_config.NumberColumn("Turnover ₹Cr", format="%.1f")
            if "volume" in out.columns:
                colcfg["volume"] = st.column_config.NumberColumn("Volume", format="%d")
            for c, lbl, fmt in (("multiple", "x avg vol", "%.1f"),
                                ("day_pct", "Chg%", "%.2f%%"),
                                ("turnover_cr", "Turnover ₹Cr", "%.1f"),
                                ("range_high", "High", "%.2f"),
                                ("range_low", "Low", "%.2f"),
                                ("from_high_pct", "From high %", "%.2f%%"),
                                ("from_low_pct", "From low %", "%.2f%%")):
                if c in out.columns:
                    colcfg[c] = st.column_config.NumberColumn(lbl, format=fmt)
            if "cause" in out.columns:
                colcfg["cause"] = st.column_config.TextColumn("Cause", width="medium")
            drop = [c for c in ("reasons", "avg_volume", "baseline_days", "trade_date",
                                "n_deals", "churn_share", "pct_mcap", "bars") if c in out.columns]
            out = out.drop(columns=drop)
            st.dataframe(out, width="stretch", hide_index=True, column_config=colcfg)

        with _t_mv:
            _mv = _trend_movers(_tr_top, float(_tr_minto) * 1e7)
            st.caption(f"**{_mv['n_filtered']:,}** of {_mv['n_universe']:,} names clear "
                       f"the ₹{_tr_minto:.0f} Cr turnover floor.")
            st.markdown("**Top gainers**")
            _tr_table(_mv["gainers"])
            st.markdown("**Top losers**")
            _tr_table(_mv["losers"])

        def _render_anomaly_spikes():
            with st.spinner("Attributing volume spikes to a cause…"):
                _vol = _trend_volume(_tr_top)
            if _vol.get("error"):
                st.warning(f"Volume scan unavailable: {_vol['error']}")
            else:
                _tal = _vol.get("tally") or {}
                st.caption(
                    f"**{_vol.get('n_hits', 0)}** spikes across {_vol.get('universe', 0):,} names — "
                    + " · ".join(f"{k.replace('_', ' ').lower()} **{n}**"
                                 for k, n in _tal.items() if n)
                    + ".  Each spike is attributed to a filing, prop churn, deal activity, "
                      "or nothing — the list answers *why*, not only *what*.")
                _tr_table(_vol["rows"])

        if _t_vol is not None:
            with _t_vol:
                _darvas_window(f"{key_prefix}_vs")

                st.divider()
                # The cause-attributed scan is a different question ("why did this
                # spike?") on a different filter, so it stays — one level down,
                # because the Darvas criteria are now what the tab means.
                with st.expander("Cause-attributed spikes (volume_anomaly) — why, not what"):
                    _render_anomaly_spikes()
        else:
            # Home mounting: the Darvas window sits above, so only the cause
            # attribution needs a home down here.
            with st.expander("Cause-attributed spikes (volume_anomaly) — why, not what"):
                _render_anomaly_spikes()

        _ext = None
        with _t_52:
            with st.spinner(f"Computing 52-week extremes over the top {_tr_uni} names…"):
                _ext = _trend_extremes(_tr_uni, _tr_top, 2.0)
            _w = _ext["week52"]
            st.caption(f"{_w['n_scanned']} of the top {_ext['universe_n']} by turnover, "
                       f"within {_w['near_pct']}% of the extreme"
                       + (f" · {_w.get('n_cash_equivalents', 0)} cash-equivalent ETFs excluded"
                          if _w.get("n_cash_equivalents") else "") + ".")
            st.markdown("**At / near 52-week highs**")
            _tr_table(_w["highs"])
            st.markdown("**At / near 52-week lows**")
            _tr_table(_w["lows"])

        with _t_ath:
            with st.spinner(f"Computing all-time extremes over the top {_tr_uni} names…"):
                _ext = _ext or _trend_extremes(_tr_uni, _tr_top, 2.0)
            _a = _ext["alltime"]
            st.caption(f"{_a['n_scanned']} of the top {_ext['universe_n']} by turnover, "
                       f"within {_a['near_pct']}% of the extreme"
                       + (f" · {_a.get('n_cash_equivalents', 0)} cash-equivalent ETFs excluded"
                          if _a.get("n_cash_equivalents") else "")
                       + ". History is bounded by what yfinance serves, so \"all-time\" "
                         "means \"as far back as the feed goes\".")
            st.markdown("**At / near all-time highs**")
            _tr_table(_a["highs"])
            st.markdown("**At / near all-time lows**")
            _tr_table(_a["lows"])

        st.divider()
        st.caption(
            "**No \"Most Visited\" lens.** That is crowd page-view data from a site's own "
            "traffic logs, and there is no free NSE or public feed for retail attention. "
            "A proxy (delivery spikes, rank churn) would measure something else while "
            "wearing the same label, so it is left out rather than faked.")


# ──────────────────────────────────────────────────────────────────────────────
# Home — "where the action is today" card map
# ──────────────────────────────────────────────────────────────────────────────
# Modelled on a commercial screener's landing page (user screenshot, 2026-09-04):
# a hero, then a grid of small cards each showing three names under a heading,
# with a "View" link into the page that owns that lens.
#
# THE HARD CONSTRAINT, and the reason this differs from the mockup:
# Home must not fetch on load. The commercial page can afford nine live lenses
# because it serves precomputed server-side lists; we have one machine and a
# daily job. So every card here reads STORED state - the persisted daily
# shortlist, the offline constituent file - and a card with no stored data says
# so instead of being padded with whatever is nearby.
#
# The mockup's nine cards are also not nine independent facts for us: a RISK-OFF
# regime caps the stored shortlist at five names, so nine "top 3" cards off that
# one table would be the same five names rearranged. Each card below therefore
# answers a different question from a different column.

def _company_names() -> dict:
    """symbol -> company name, from the offline NSE constituent files.

    Reuses peer_comparison's loader: a file read with no network, which is the
    only kind of lookup Home is allowed to do on load.
    """
    try:
        return {k: (v.get("name") or k) for k, v in pcmp._constituents().items()}
    except Exception:
        return {}


def _action_card(col, title: str, blurb: str, rows: list, target_page,
                 key: str, *, empty: str = "") -> None:
    """One card: heading + View link, a one-line blurb, then up to three rows.

    `rows` is [(bold line, muted sub-line)] - usually (symbol, company), but the
    sector card passes (sector, "N names"), which is why this takes text rather
    than symbols.
    """
    t = rs.TOKENS
    with col:
        with st.container(border=True):
            # 3:1 wrapped the button label onto two lines at Home's card width
            # (three cards across a ~940px pane leaves the action column ~75px).
            _h1, _h2 = st.columns([1.9, 1.15])
            with _h1:
                st.markdown(
                    f'<div style="font-size:13.5px;font-weight:700;color:{t["text"]};">'
                    f'{title}</div>', unsafe_allow_html=True)
            with _h2:
                if target_page and st.button("View", key=f"am_{key}",
                                             use_container_width=True):
                    st.session_state["current_page"] = target_page
                    st.rerun()
            st.markdown(
                f'<div style="font-size:11px;color:{t["text_muted"]};'
                f'line-height:1.45;margin:2px 0 8px;">{blurb}</div>',
                unsafe_allow_html=True)
            if not rows:
                st.markdown(
                    f'<div style="font-size:11.5px;color:{t["absent"]};'
                    f'font-style:italic;padding:10px 0 4px;">'
                    f'{empty or "No stored data."}</div>', unsafe_allow_html=True)
                return
            cells = "".join(
                f'<div style="background:{t["surface_alt"]};border-radius:6px;'
                f'padding:7px 10px;margin-bottom:6px;">'
                f'<div style="font-size:12.5px;font-weight:700;color:{t["text"]};">'
                f'{a}</div>'
                f'<div style="font-size:10px;color:{t["text_muted"]};">{b}</div></div>'
                for a, b in rows[:3])
            st.markdown(cells, unsafe_allow_html=True)


def render_action_map() -> None:
    """The card grid. Reads stored state only - no network, no scan."""
    t = rs.TOKENS
    try:
        _dates = db.get_opportunity_run_dates()
    except Exception:
        _dates = []
    _run = _dates[0] if _dates else None
    try:
        _df = db.get_daily_opportunities(_run) if _run else pd.DataFrame()
    except Exception:
        _df = pd.DataFrame()
    _names = _company_names()

    def _nm(sym):
        return _names.get(str(sym).upper(), "")

    _hdr_l, _hdr_r = st.columns([3, 1])
    with _hdr_l:
        _date_bit = (f'<span style="color:{t["text_muted"]};font-weight:500;"> &middot; '
                     f'{_run}</span>' if _run else "")
        st.markdown(
            f'<div style="font-size:11px;font-weight:700;letter-spacing:.08em;'
            f'text-transform:uppercase;color:{t["good"]};padding-top:6px;">'
            f'&#9679; Where the action is today{_date_bit}</div>',
            unsafe_allow_html=True)
    with _hdr_r:
        if st.button("Open full map", key="am_full", use_container_width=True):
            st.session_state["current_page"] = "Opportunity Hub"
            st.rerun()

    if _df is None or _df.empty:
        st.markdown(
            rs.callout("No stored shortlist yet.",
                       "These cards read the persisted daily run rather than "
                       "scanning on load. Run it from the Opportunity Hub (or let "
                       "the scheduled job do it) and this map fills in.",
                       tone="absent"),
            unsafe_allow_html=True)
        return

    if _run != date.today().isoformat():
        st.caption(f"Newest stored run is **{_run}**, not today - these are that "
                   f"day's names. Price levels decay; treat them as history.")

    # Row 1 - the shortlist, its sectors, its strongest movers
    c1, c2, c3 = st.columns(3)

    _rank_rows = [(r["symbol"], _nm(r["symbol"]) or f"score {r['score']:.0f}")
                  for _, r in _df.sort_values("rank").head(3).iterrows()]
    _action_card(c1, "Today's shortlist",
                 "Ranked across every scanner by the stored daily run.",
                 _rank_rows, "Opportunity Hub", "rank")

    _sec_rows = []
    if "sector" in _df.columns:
        _sec = (_df.groupby("sector")["momentum"].agg(["count", "mean"])
                .sort_values(["count", "mean"], ascending=False))
        _sec_rows = [(str(ix), f"{int(r['count'])} name(s) &middot; avg momentum {r['mean']:.0f}")
                     for ix, r in _sec.head(3).iterrows()]
    _action_card(c2, "Sectors in the shortlist",
                 "Where today's names cluster - counted from the shortlist, not "
                 "a separate sector scan.", _sec_rows, "Sector Map", "sect")

    _mom_rows = []
    if "momentum" in _df.columns:
        _mom_rows = [(r["symbol"],
                      f"momentum {r['momentum']:.0f} &middot; {r.get('industry') or '-'}")
                     for _, r in _df.sort_values("momentum", ascending=False).head(3).iterrows()
                     if pd.notna(r.get("momentum"))]
    _action_card(c3, "Strongest momentum",
                 "IBD-style weighted trailing return, highest first.",
                 _mom_rows, "Opportunity Hub", "mom")

    # Row 2 - rating, confluence, what actually fired
    c4, c5, c6 = st.columns(3)

    _rat_rows = []
    if "overall_rating" in _df.columns:
        _rat_rows = [(r["symbol"], f"M1 rating {r['overall_rating']:.0f}/100")
                     for _, r in _df.sort_values("overall_rating", ascending=False).head(3).iterrows()
                     if pd.notna(r.get("overall_rating"))]
    _action_card(c4, "Highest rated",
                 "The M1 technical Overall Rating - a different lens from the "
                 "shortlist score.", _rat_rows, "Predictive Analysis", "rat")

    _conf_rows = []
    if "confluence" in _df.columns:
        _conf_rows = [(r["symbol"], f"{int(r['confluence'])} scanners agree")
                      for _, r in _df.sort_values("confluence", ascending=False).head(3).iterrows()
                      if pd.notna(r.get("confluence"))]
    _action_card(c5, "Most confluence",
                 "Most scanners firing on one name. Measured co-fire lift is "
                 "significant only at 60d - a lead, not an edge.",
                 _conf_rows, "Scanner Hub", "conf")

    _tally = {}
    for _sc in _df.get("scanners", pd.Series(dtype=str)).dropna():
        for _one in str(_sc).split(","):
            _one = _one.strip()
            if _one:
                _tally[_one] = _tally.get(_one, 0) + 1
    _scan_rows = [(k, f"fired on {v} of {len(_df)} names")
                  for k, v in sorted(_tally.items(), key=lambda kv: -kv[1])[:3]]
    _action_card(c6, "Scanners firing",
                 "Which detectors actually produced today's list.",
                 _scan_rows, "Scanner Hub", "scan")


# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Home":
    _t = rs.TOKENS
    _n_pages = sum(len(v) for v in PAGE_GROUPS.values())

    st.markdown(
        f'<div style="background:linear-gradient(135deg,{_t["surface_warm"]} 0%,'
        f'{_t["surface_alt"]} 55%,{_t["surface"]} 100%);'
        f'border:1px solid {_t["border_strong"]};border-radius:16px;'
        f'padding:30px 34px;margin:2px 0 20px;">'
        f'<div class="tb-micro" style="color:{_t["accent"]};">TRADING BRAMHA</div>'
        f'<div style="font-size:30px;font-weight:800;line-height:1.22;'
        f'color:{_t["text"]};margin-top:8px;">Screening, research and risk —<br>'
        f'<span style="color:{_t["accent"]};">in one place.</span></div>'
        f'<div style="font-size:14px;color:{_t["text_body"]};margin-top:12px;'
        f'max-width:620px;line-height:1.55;">'
        f'A personal NSE swing-trading desk. Every number on it is computed from '
        f'filed data or measured history — where something could not be measured, '
        f'the page says so rather than guessing.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Call-to-action row, as in the reference layout. Real buttons rather than
    # styled anchors, because navigation here is session_state + rerun.
    _cta1, _cta2, _cta3, _cta4 = st.columns([1.15, 1, 1, 3])
    with _cta1:
        if st.button("Open screener dashboard", key="home_cta_screen",
                     type="primary", use_container_width=True):
            st.session_state["current_page"] = "Opportunity Hub"
            st.rerun()
    with _cta2:
        if st.button("View top movers", key="home_cta_movers",
                     use_container_width=True):
            st.session_state["home_trending_open"] = True
            st.rerun()
    with _cta3:
        if st.button("Scanner Hub", key="home_cta_hub", use_container_width=True):
            st.session_state["current_page"] = "Scanner Hub"
            st.rerun()
    st.markdown(
        f'<div style="font-size:11px;color:{_t["text_muted"]};margin:8px 0 18px;">'
        f'No sign-in required to browse. '
        f'<b>For research and educational purposes only — not investment advice.</b>'
        f'</div>', unsafe_allow_html=True)

    # Three genuinely cheap facts. Nothing here fetches.
    try:
        _n_scanners = len(sc.SCANNERS)
    except Exception:
        _n_scanners = None
    _senti = None
    try:
        _senti = cached_latest_sentiment()
    except Exception:
        _senti = None

    _senti_val = f"{_senti['score']:.0f} · {_senti['band']}" if _senti else None
    _senti_sub = f"as of {_senti['reading_date']}" if _senti else "never refreshed"
    _senti_tone = "neutral"
    if _senti and str(_senti.get("band")) == "NOT_CHECKED":
        _senti_tone = "absent"

    st.markdown(
        rs.strip([
            rs.stat_card("Pattern scanners",
                         str(_n_scanners) if _n_scanners is not None else None,
                         "backtest-measured where marked", tone="info"),
            rs.stat_card("Pages", str(_n_pages), "across five groups", tone="neutral"),
            rs.stat_card("Last sentiment", _senti_val, _senti_sub, tone=_senti_tone),
        ], cols=3),
        unsafe_allow_html=True,
    )
    st.write("")

    # ── The action map — stored state only, so it costs nothing on load ──────
    render_action_map()
    st.write("")

    # Home used to be a card grid of every page. It is now a working surface: the
    # scan that was buried three clicks deep, then the roster it feeds. Navigation
    # lives in the top ribbon, where it was already complete.
    _darvas_window("home_vs", compact=True)
    st.write("")

    # ── What moved today (was the Trending Stocks page) ──────────────────────
    # Folded in because the page was a single nav click that only ever led here,
    # and Home already carried one of its four lenses (the Darvas window above).
    #
    # LAZY ON PURPOSE. Home's rule is that it must not fetch on load, and these
    # lenses are the most expensive fetches in the app: Price Movers pulls the
    # whole-market bhavcopy plus live quotes, and the 52W/ATH pair downloads
    # history for a few hundred names. Rendering them eagerly would put a
    # minutes-long wait on the landing page.
    st.markdown("#### 📈 What moved today")
    _tr_key = "home_trending_open"
    if not st.session_state.get(_tr_key):
        _tc_a, _tc_b = st.columns([1, 4])
        with _tc_a:
            if st.button("Load", key="home_trending_btn", use_container_width=True):
                st.session_state[_tr_key] = True
                st.rerun()
        with _tc_b:
            st.caption("Price movers, 52-week and all-time extremes, and the "
                       "cause-attributed volume spikes. Runs on request — the "
                       "range lenses download history for a few hundred names.")
    else:
        render_trending_stocks("home_tr", include_volume=False)
        if st.button("Hide", key="home_trending_hide"):
            st.session_state[_tr_key] = False
            st.rerun()
    st.write("")

    # The nav-card grid is gone: every page is already one click away in the top
    # ribbon, so carding them twice made Home a menu of a menu. Home now shows the
    # two things you actually act on — today's volume shockers, and what you are
    # already tracking.
    st.markdown("#### ♥ Watchlist")
    _wl = db.get_watchlist()
    if _wl is None or _wl.empty:
        st.info("Watchlist is empty — tick rows in the scan above and press ♥.")
    else:
        # Deliberately NOT price-enriched here: the Watchlist page fetches OHLCV
        # per symbol to score Minervini/TechnoFunda, and Home must not fetch on
        # load. This is the roster; the scored view is one click away.
        _wl_out = _wl.rename(columns={"symbol": "Symbol", "added_date": "Added",
                                      "notes": "Notes"})
        _wl_out = _with_chart_family(_wl_out, "Symbol")
        _wl_cfg = dict(_chart_family_colcfg())
        _wl_cfg["Symbol"] = st.column_config.TextColumn("Symbol", width="small")
        _wl_cfg["Added"] = st.column_config.TextColumn("Added", width="small")
        _wl_cfg["Notes"] = st.column_config.TextColumn("Notes", width="medium")
        _wl_sel = st.dataframe(_wl_out, width="stretch", hide_index=True,
                               column_config=_wl_cfg, key="home_wl_tbl",
                               on_select="rerun", selection_mode="multi-row")
        try:
            _wl_rows = list(_wl_sel.selection.rows)
        except Exception:
            _wl_rows = []
        _wl_pick = [str(_wl.iloc[i]["symbol"]) for i in _wl_rows if i < len(_wl)]

        _h1, _h2, _h3 = st.columns([1, 1, 2])
        with _h1:
            if st.button(f"Remove {len(_wl_pick) or ''}".strip(), key="home_wl_rm",
                         disabled=not _wl_pick, use_container_width=True):
                for _s in _wl_pick:
                    db.remove_watchlist_symbol(_s)
                st.toast(f"Removed {len(_wl_pick)}")
                st.rerun()
        with _h2:
            if st.button("Open Watchlist →", key="home_wl_open",
                         use_container_width=True):
                st.session_state["current_page"] = "Watchlist"
                st.rerun()
        with _h3:
            st.caption(f"{len(_wl)} tracked. Scores and trade plans live on the "
                       f"Watchlist page.")

    st.write("")

    st.markdown(
        f'<div style="border-top:1px solid {_t["border"]};margin-top:6px;padding-top:14px;'
        f'font-size:11.5px;color:{_t["text_muted"]};line-height:1.65;max-width:900px;">'
        f'<b style="color:{_t["text_body"]};">Research notice.</b> Scores, signals and '
        f'ratings on this dashboard are automated outputs computed from historical '
        f'market data and filed disclosures. They are <b>not investment advice</b> and '
        f'not a recommendation to buy, sell or hold. Scanner edges shown as measured '
        f'come from a single backtest window and carry no significance test yet — '
        f'treat them as leads, not signals. Nothing here executes trades.'
        f'</div>',
        unsafe_allow_html=True,
    )


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

        _paginated_df(
            view, key="screener_main",
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

    # Candidates parked by the ribbon search when what was typed was a prefix
    # rather than a ticker. This is the chart tool's typeahead dropdown, one
    # step later: Streamlit cannot filter a list per keystroke (a widget only
    # reports on Enter or blur), so the choice is offered after submit instead
    # of during typing. Same directory, same ranking, same NSE/BSE reality.
    _sa_typed, _sa_matches = st.session_state.get("tb_search_matches", (None, []))
    if _sa_matches:
        st.caption(f"No exact NSE ticker for **{_sa_typed}** — {len(_sa_matches)} match"
                   f"{'es' if len(_sa_matches) != 1 else ''}:")
        _mc = st.columns(min(len(_sa_matches), 4))
        for _mi, _m in enumerate(_sa_matches):
            with _mc[_mi % 4]:
                if st.button(f"{_m['display']}", key=f"tb_match_{_m['display']}",
                             use_container_width=True,
                             help=_m.get("name") or _m["display"]):
                    st.session_state["selected_symbol"] = _m["display"]
                    st.session_state["last_analyzed"] = _m["display"]
                    st.session_state.pop("tb_search_matches", None)
                    st.rerun()
                st.caption(f"<span style='font-size:10.5px;color:{_T['text_muted']}'>"
                           f"{(_m.get('name') or '')[:34]}</span>",
                           unsafe_allow_html=True)
        if st.button("✕ Dismiss", key="tb_match_clear"):
            st.session_state.pop("tb_search_matches", None)
            st.rerun()

    # Resolved a prefix/typo to a single ticker. Worth one line: the page is
    # about to show a company nobody typed the exact name of.
    _sa_res = st.session_state.pop("tb_search_resolved", None)
    if _sa_res:
        _typed, _to, _nm = _sa_res
        st.caption(f"**{_typed}** → **{_to}**{f' · {_nm}' if _nm else ''} "
                   f"(only NSE match)")

    # Typed something the directory has never heard of. Say so once — the
    # analysis below still runs, and its own failure message is the detail.
    _sa_miss = st.session_state.pop("tb_search_miss", None)
    if _sa_miss:
        st.caption(f"**{_sa_miss}** is not in the NSE symbol directory — analysing "
                   f"it anyway, in case the directory is behind on a new listing.")

    # Consume symbol pushed from Scanner Hub card "↗ Analyze" button
    _sa_override = st.session_state.pop("sa_symbol_override", None)
    if _sa_override:
        st.session_state["selected_symbol"] = _sa_override
        st.session_state["last_analyzed"] = _sa_override

    # Show Analyzer Roster if any symbols queued from Scanner Hub cards
    _sa_roster = st.session_state.get("sa_roster", [])
    if _sa_roster:
        with st.expander(f"Analyzer Roster — {len(_sa_roster)} symbol(s)", expanded=True):
            _rc = st.columns(min(len(_sa_roster), 6))
            for _ri, _rsym in enumerate(_sa_roster):
                with _rc[_ri % 6]:
                    if st.button(_rsym, key=f"roster_pick_{_rsym}",
                                 use_container_width=True,
                                 help=f"Analyze {_rsym}"):
                        st.session_state["selected_symbol"] = _rsym
                        st.session_state["last_analyzed"] = _rsym
                        st.rerun()
            if st.button("✕ Clear roster", key="roster_clear"):
                st.session_state["sa_roster"] = []
                st.rerun()

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

    # ── Prev / Next navigation ────────────────────────────────────────────────
    if screener_symbols:
        _cur_idx = screener_symbols.index(symbol) if symbol in screener_symbols else -1
        _nav_c1, _nav_c2, _nav_c3 = st.columns([1, 6, 1])
        with _nav_c1:
            _at_start = _cur_idx <= 0
            if st.button(
                "◀ Prev",
                key="sa_prev",
                disabled=_at_start,
                use_container_width=True,
                help=(screener_symbols[_cur_idx - 1] if _cur_idx > 0 else ""),
            ):
                _prev = screener_symbols[_cur_idx - 1]
                st.session_state["selected_symbol"] = _prev
                st.session_state["last_analyzed"] = _prev
                st.rerun()
        with _nav_c2:
            if _cur_idx >= 0:
                st.caption(
                    f"{_cur_idx + 1} / {len(screener_symbols)} — **{symbol}**",
                )
        with _nav_c3:
            _at_end = _cur_idx >= len(screener_symbols) - 1 or _cur_idx < 0
            if st.button(
                "Next ▶",
                key="sa_next",
                disabled=_at_end,
                use_container_width=True,
                help=(screener_symbols[_cur_idx + 1] if not _at_end else ""),
            ):
                _next = screener_symbols[_cur_idx + 1]
                st.session_state["selected_symbol"] = _next
                st.session_state["last_analyzed"] = _next
                st.rerun()

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
                # enforce_liquidity=False: the user asked for THIS symbol.
                df = cached_fetch_ohlcv(symbol, days=tf_days, enforce_liquidity=False)
            if df is None:
                st.error(f"No usable data for {symbol} — fewer than {sp.MIN_BARS} "
                         f"daily bars, or not on yfinance under that NSE code.")
            else:
                _thin_volume_note(df, symbol)
                # FR-1 — identity header + valuation/quality strip lead the page:
                # who is this company and what does it cost, before any signal.
                with st.spinner("Fetching fundamentals & statements..."):
                    _fund = cached_fetch_fundamentals(symbol)
                    _deep = cached_fundamentals_deep(symbol)
                render_fundamental_header(symbol, df, _fund, _deep)
                render_fundamental_signals(fscore.score_all(_fund, _deep))
                render_fundamental_history(_deep)
                render_peer_comparison(symbol)
                _rf_res = cached_red_flags(symbol)
                render_red_flags(_rf_res)
                _render_screener_unlock(_rf_res)
                render_scenarios(scen.build(_deep), _deep)
                render_concalls(cached_concalls(symbol))

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

                # UI-2 — the Chart Tool is the default chart here, as it already
                # is on Predictive Analysis. The classic Plotly chart stays one
                # click away because it is not strictly a subset: RS Line, TSI
                # and CPR exist only there. Until those are ported, dropping it
                # outright would lose three indicators to gain a nicer canvas.
                classic_chart = st.toggle(
                    "Classic chart (RS Line · TSI · CPR)",
                    key="sa_classic_chart",
                    help="The Chart Tool is richer — live crosshair, volume "
                         "profile, Elliott/VCP/harmonic overlays, price "
                         "projection — but it does not yet carry the RS Line, "
                         "TSI or CPR panes. Flip this when you need those.",
                )

                # ── Chart sizing ──────────────────────────────────────────────
                # Applies to whichever chart is showing. Both renderers are
                # fixed-height by construction — the Chart Tool is an iframe and
                # Plotly figures carry an explicit height — so vertical size is
                # the one dimension `use_container_width` cannot solve, and the
                # right value depends on the monitor rather than on the data.
                # Defaults are exactly what each chart used before this control
                # existed, so an untouched page renders identically.
                with st.expander("Chart size"):
                    _sz1, _sz2 = st.columns(2)
                    with _sz1:
                        _h_min, _h_def = ((CHART_H_MIN_CLASSIC, CHART_H_DEFAULT_CLASSIC)
                                          if classic_chart
                                          else (CHART_H_MIN_TOOL, CHART_H_DEFAULT_TOOL))
                        sa_chart_h = st.slider(
                            "Chart height (px)", _h_min, CHART_H_MAX, _h_def, 50,
                            key=f"sa_chart_h_{'classic' if classic_chart else 'tool'}",
                            help="Vertical size of the chart. The two chart modes "
                                 "keep separate values — the Chart Tool is one "
                                 "pane and the classic chart stacks six, so they "
                                 "do not want the same number.")
                    with _sz2:
                        if classic_chart:
                            sa_price_share = st.slider(
                                "Price pane share (%)", 38, int(PRICE_SHARE_MAX * 100),
                                38, 1, key="sa_price_share",
                                help="How much of the figure the candles get. The "
                                     "default 38% is why raising height alone can "
                                     "feel like it did not help — everything grows "
                                     "together. Raising this takes room from the "
                                     "oscillators instead.")
                        else:
                            sa_price_share = None
                            st.caption("Pane share applies to the classic chart — "
                                       "the Chart Tool manages its own sub-panes.")

                if classic_chart:
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

                    st.plotly_chart(
                        build_chart(symbol, df, ew, nifty_df=nifty_df,
                                    harmonic=harmonic, height=sa_chart_h,
                                    price_share=(sa_price_share / 100.0
                                                 if sa_price_share else None)),
                        use_container_width=True)
                # Harmonic lives on the Chart Tool's own indicator menu, so the
                # checkbox above would be a second switch for the same overlay —
                # it stays with the chart it drives.
                elif not render_chart_tool(symbol, height=sa_chart_h):
                    # Server down. Fall back to the classic chart rather than
                    # leaving the page chartless behind a warning — this is the
                    # analysis surface, and every read below assumes you have
                    # looked at the price.
                    #
                    # The height carries over, but NOT the pane share: this path
                    # is reached with the Chart Tool selected, so `sa_price_share`
                    # is None and the classic chart keeps its own default.
                    st.plotly_chart(
                        build_chart(symbol, df, ew, nifty_df=nifty_df,
                                    height=sa_chart_h),
                        use_container_width=True)

                # ── Side-by-side: condition table (left) + chart preview (right) ──
                sa_cond_col, sa_chart_col = st.columns([1, 1.4], gap="medium")
                with sa_cond_col:
                    render_condition_table(mv_conds, tf_conds, cs_conds)
                with sa_chart_col:
                    # Embed the Chart Tool iframe beside the condition table so
                    # the pattern context is visible while reading the scores.
                    _chart_inline_url = (
                        f"http://localhost:{CHART_TOOL_PORT}/?symbol="
                        f"{symbol if ('.' in symbol or symbol.startswith('^')) else symbol + '.NS'}"
                        f"&tf=1d"
                    )
                    st.markdown("**Chart preview**")
                    st.components.v1.iframe(_chart_inline_url, height=460, scrolling=False)
                    st.caption(
                        f"[Open full chart ↗]({_chart_inline_url}) · "
                        "Chart Tool must be running on :5001"
                    )

                # ── 3-POV Council: Bull / Bear / Judge ──
                st.divider()
                with st.spinner("Running deterministic council..."):
                    fundamentals = _fund          # already fetched for the header
                    bundle, bull, bear, card = council.run_council(
                        symbol, df, nifty_df, fundamentals, regime=nifty_regime
                    )

                # Plain-language summary first, then the Bull/Bear/Judge drill-down.
                render_setup_intelligence(
                    council.setup_intelligence(bundle, bull, bear, card)
                )

                # Ownership sits directly under the setup read: the structural
                # leg that says who has been buying the thing the setup likes.
                render_ownership_flow(symbol)

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
        _paginated_df(pd.DataFrame(rows).drop(columns=["id"]), key="portfolio_open")

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
            _paginated_df(
                closed_pos[["symbol", "entry_price", "closed_price", "quantity",
                            "P&L %", "Result", "entry_date", "closed_date", "notes"]],
                key="portfolio_closed",
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
        _paginated_df(pd.DataFrame(rows), key="watchlist_main")

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
        _paginated_df(alerts_view.drop(columns=["id"]), key="alerts_main")

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
                # build_dataset raises when every symbol failed, and the message
                # names which lookup died. It used to return an empty frame, so
                # a dead endpoint rendered as "No data fetched" — indistinguishable
                # from a quiet market. That is how the quote-equity 403 hid.
                df = None
                try:
                    with st.spinner(f"Fetching shareholding data for {len(symbols)} symbols..."):
                        df = nse.build_dataset(symbols)
                except RuntimeError as exc:
                    st.error(str(exc))

                if df is not None:
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
# Scheduler Hub — manage batch jobs as Windows Scheduled Tasks. Generalises the
# Scanner Hub's one-off scheduler panel (scheduler_core.JOBS registry). Star job:
# the live Alert Bot (alert_watcher.js), run every N min during market hours.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Scheduler Hub":
    import json as _sched_json
    import scheduler_core as sched

    st.subheader("Scheduler Hub")
    st.caption(
        "Batch jobs registered as Windows Scheduled Tasks. **Register / Remove / "
        "Run now change persistent OS scheduled tasks.** The Alert Bot runs the live "
        "SVP / indicator signal engine each interval during market hours and fires on "
        "pattern-buildup transitions."
    )
    st.info(
        "Jobs read live bars from the chart server (http://127.0.0.1:5001) and the "
        "dashboard cache — keep the chart server running during market hours so the "
        "Alert Bot has data.", icon="ℹ️",
    )

    for _jid, _job in sched.JOBS.items():
        _stt = sched.status(_job)
        _reg = _stt.get("registered")
        with st.container(border=True):
            _hdr = st.columns([3, 1])
            _hdr[0].markdown(f"### {_job.label}")
            _hdr[0].caption(_job.desc)
            _hdr[1].markdown(f"**{'🟢 registered' if _reg else '⚪ not registered'}**")
            _hdr[1].caption(f"`{_job.task_name}`")

            if _reg:
                _m = st.columns(4)
                _m[0].metric("State", _stt.get("state", "—"))
                _m[1].metric("Next run", _stt.get("next_run", "—"))
                _m[2].metric("Last run", _stt.get("last_run", "—"))
                _m[3].metric("Last result", _stt.get("last_result", "—"))

            # Schedule configuration
            if _job.kind == "interval":
                _c = st.columns(3)
                _v_st = _c[0].text_input("Start (HH:MM)", value=_job.default_time, key=f"sch_{_jid}_st")
                _v_et = _c[1].text_input("End (HH:MM)", value=_job.default_end, key=f"sch_{_jid}_et")
                _v_mo = _c[2].number_input("Every N min", 1, 240, int(_job.default_interval), key=f"sch_{_jid}_mo")
                _sched_kw = dict(time=_v_st, end=_v_et, interval=int(_v_mo))
            else:
                _c = st.columns(3)
                _v_t = _c[0].text_input("Run time (HH:MM)", value=_job.default_time, key=f"sch_{_jid}_t")
                _sched_kw = dict(time=_v_t)

            _b = st.columns(4)
            if _b[0].button("Register / Update", key=f"sch_{_jid}_reg", type="primary"):
                _ok, _msg = sched.register(_job, **_sched_kw)
                if _ok:
                    st.success(_msg); st.rerun()
                else:
                    st.error(_msg)
                    st.code(" ".join(sched.register_argv(_job, **_sched_kw)), language="bat")
                    st.caption("If it's a permissions error, run the command above in an elevated terminal.")
            if _b[1].button("Run now", key=f"sch_{_jid}_run", disabled=not _reg):
                _ok, _msg = sched.run_now(_job)
                (st.success if _ok else st.error)(_msg)
            if _b[2].button("Remove", key=f"sch_{_jid}_del", disabled=not _reg):
                _ok, _msg = sched.remove(_job)
                (st.success if _ok else st.warning)(_msg); st.rerun()

            with st.expander("Log tail", expanded=False):
                st.code(sched.tail_log(_job, 40), language=None)

            # Alert-bot specifics: config summary, delivery status, recent alerts.
            if _jid == "alert_watcher":
                _cfg_path = sched.HERE / "alert_config.json"
                try:
                    _cfg = _sched_json.loads(_cfg_path.read_text(encoding="utf-8"))
                except Exception:
                    _cfg = {}
                _delivery = _cfg.get("delivery", [])
                if not _delivery or _delivery == ["log"]:
                    st.warning(
                        "Delivery is **dry-run** (log only) — no email/Telegram channel wired "
                        "yet. Fired alerts go to `tools/cache/alerts/alerts.jsonl`.", icon="⚠️",
                    )
                _watch = _cfg.get("watch", [])
                if _watch:
                    st.caption("Watchlist: " + " · ".join(f"{w.get('symbol')}·{w.get('tf')}" for w in _watch)
                               + "   |   Rules: " + ", ".join(r.get("id", "?") for r in _cfg.get("rules", [])))
                _feed = sched.HERE / "cache" / "alerts" / "alerts.jsonl"
                if _feed.exists():
                    _rows = [r for r in _feed.read_text(encoding="utf-8").splitlines() if r.strip()][-10:]
                    if _rows:
                        with st.expander(f"Recent alerts ({len(_rows)})", expanded=False):
                            for _r in reversed(_rows):
                                try:
                                    _a = _sched_json.loads(_r)
                                    st.markdown(f"- `{_a.get('ts','')}` — **{_a.get('headline','')}**")
                                except Exception:
                                    pass


# ──────────────────────────────────────────────────────────────────────────────
# Opportunity Hub — top-down Sector→Industry→Stock→Pattern→Entry funnel (Phase 1)
# Composition of shipped pieces: sector/industry strength is derived bottom-up
# from constituents' momentum (opportunity_hub.py), then the EXISTING Scanner Hub
# scanners run on just the leading stocks. See wiki Opportunity-Hub-Roadmap.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Opportunity Hub":
    st.subheader("Opportunity Hub")
    st.caption("Top-down funnel — **Right Sector → Right Industry → Right Stock → "
               "Right Pattern → Right Entry**. Leading sectors & industries are "
               "ranked bottom-up from their constituents' momentum, then a pattern "
               "scanner runs on just the leaders. The Hub narrows & ranks — you "
               "validate the setup and manage the risk.")

    # ── Regime posture banner (B-36) — the one-line "what do I do today?" ──────
    # Driven by the SAME regime + conviction gate B-32/B-33 validated, so the
    # banner states the posture the gate will actually enforce. Puts the
    # behavioural thesis (do LESS in a hostile tape) at the top of the page rather
    # than burying it — the anti-over-trading nudge, felt, not filed.
    try:
        _mkt_now = od._market_context(cached_fetch_nifty50(days=400))
    except Exception:
        _mkt_now = {"regime": "UNKNOWN", "verdict": "Benchmark unavailable — regime not assessed."}
    _rg = _mkt_now["regime"]
    _gcfg = od.REGIME_GATE.get(_rg, od.REGIME_GATE["UNKNOWN"])
    _cap_txt = "full shortlist" if _gcfg["max_names"] is None else f"≤ {_gcfg['max_names']} names"
    _rate_txt = (f"rating ≥ {_gcfg['min_rating']:.0f}" if _gcfg.get("min_rating") else "no rating floor")
    _ptone, _plabel = {
        "RISK-ON":  ("good",   "RISK-ON · full run"),
        "MIXED":    ("warn",   "MIXED · raised bar"),
        "RISK-OFF": ("risk",   "RISK-OFF · capital preservation"),
        "UNKNOWN":  ("absent", "REGIME UNKNOWN · cautious"),
    }.get(_rg, ("absent", "REGIME UNKNOWN"))
    _pfg, _pbg = rs.tone_colors(_ptone)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;'
        f'background:{_pbg};border-left:5px solid {_pfg};border-radius:8px;'
        f'padding:10px 14px;margin:4px 0 12px 0;">'
        f'<span style="font-weight:800;font-size:14px;color:{_pfg};letter-spacing:.02em;'
        f'white-space:nowrap;">{_plabel}</span>'
        f'<span style="font-size:12.5px;color:{rs.TOKENS["text_body"]};">'
        f'{_cap_txt}, {_rate_txt}. {_gcfg["note"]}</span>'
        f'<span style="margin-left:auto;font-size:11.5px;color:{rs.TOKENS["text_muted"]};'
        f'max-width:38%;text-align:right;">{_mkt_now["verdict"]}</span>'
        f'</div>', unsafe_allow_html=True)

    # ── Daily shortlist (stored) ──────────────────────────────────────────────
    # The manual funnel below is five steps and keeps nothing. This runs the same
    # funnel unattended and stores the result, so the daily question is "what did
    # it like today" rather than "which of 24 scanners should I try".
    st.markdown(rs.section("Daily shortlist — stored"), unsafe_allow_html=True)

    _dates = db.get_opportunity_run_dates()
    dl, dr = st.columns([3, 1])
    with dr:
        _sel_date = st.selectbox("Run date", _dates, index=0,
                                 key="od_date") if _dates else None
        _od_uni = st.number_input("Universe size", 40, 5000, 500, 50, key="od_uni",
                                  help="Top N by traded value. 500 takes a few minutes.")
        if st.button("Run daily shortlist now", type="primary", key="od_run"):
            # Submit to the serial job queue instead of running inline, so a click
            # elsewhere (e.g. Refresh sentiment) queues behind this run rather than
            # cancelling it. od.run persists to the DB, so the shortlist below picks
            # it up on the next poll-rerun; here we only need to report completion.
            _jid = ui_jobs.submit_unique(
                "Daily shortlist", od.run, universe_size=int(_od_uni), top_n=100,
                progress_kw="progress_cb")
            if _jid is None:
                st.info("A daily-shortlist run is already in progress — click ignored.")
            st.rerun()
        # Consume a completed run (fires once when the background job finishes).
        _fin = ui_jobs.get_queue().take_result("Daily shortlist")
        if _fin is not None:
            if _fin.status == "error":
                st.error(f"Run failed — {_fin.error}")
            else:
                _res = _fin.result or {}
                if not _res.get("ok"):
                    st.error(f"Run failed — {_res.get('reason')}")
                elif not _res.get("rows"):
                    st.warning(f"No shortlist: {_res.get('reason')}")
                else:
                    st.success(f"Stored {len(_res['rows'])} names for {_res['run_date']}.")

    with dl:
        _shortlist = db.get_daily_opportunities(_sel_date) if _sel_date else pd.DataFrame()
        if _shortlist.empty:
            st.info("No stored shortlist yet. Click **Run daily shortlist now**, or "
                    "schedule `py -3 tools/opportunity_daily.py` after market close.")
        else:
            _r0 = _shortlist.iloc[0]
            _regime = str(_r0.get("market_regime") or "UNKNOWN")
            _tone = {"RISK-ON": "good", "MIXED": "warn"}.get(_regime, "risk")
            st.markdown(
                rs.callout(f"{_sel_date} · market {_regime}.",
                           str(_r0.get("market_verdict") or ""), tone=_tone),
                unsafe_allow_html=True)

            # ── Archived funnel cards (full frozen detail for this run date) ────
            # Rendered from the snapshot stored at run time, so a historical date
            # shows exactly what fired then — scanners, reasons, levels — rather
            # than re-deriving from today's prices. Older dates without a snapshot
            # simply skip this and keep the summary list below.
            _arch = db.get_opportunity_cards(_sel_date) if _sel_date else []
            if _arch:
                import json as _arch_json
                with st.expander(f"📇 Archived funnel cards — {_sel_date} "
                                 f"({len(_arch)} snapshots, as they fired)"):
                    for _i in range(0, len(_arch), 3):
                        _cols = st.columns(3)
                        for _col, _rec in zip(_cols, _arch[_i:_i + 3]):
                            with _col:
                                try:
                                    _render_pipeline_card(_arch_json.loads(_rec["card_json"]))
                                except Exception as _e:
                                    st.caption(f"{_rec['symbol']}: snapshot unreadable ({_e})")

            # ── Sort control ───────────────────────────────────────────────────
            _sort_by = st.radio(
                "Sort by",
                ["Score (default)", "Quality — green first (Overall Rating ↑)",
                 "Confluence (edge points)", "Momentum"],
                horizontal=True, key="od_sort",
                help="'Green first' surfaces stocks whose cross-system Overall Rating "
                     "is ≥85 (the green band) before amber and grey rated names.",
            )
            if _sort_by == "Quality — green first (Overall Rating ↑)":
                _shortlist = _shortlist.copy()
                _shortlist["_rt_sort"] = pd.to_numeric(
                    _shortlist["overall_rating"], errors="coerce").fillna(0)
                _shortlist = _shortlist.sort_values("_rt_sort", ascending=False)
            elif _sort_by == "Confluence (edge points)":
                _shortlist = _shortlist.copy()
                _shortlist["_ep_sort"] = pd.to_numeric(
                    _shortlist["edge_points"], errors="coerce").fillna(0)
                _shortlist = _shortlist.sort_values("_ep_sort", ascending=False)
            elif _sort_by == "Momentum":
                _shortlist = _shortlist.copy()
                _shortlist["_mom_sort"] = pd.to_numeric(
                    _shortlist["momentum"], errors="coerce").fillna(0)
                _shortlist = _shortlist.sort_values("_mom_sort", ascending=False)
            # else: keep original rank order (score)

            for _, row in _shortlist.iterrows():
                _sym = str(row["symbol"])
                _rt = int(row["overall_rating"]) if pd.notna(row.get("overall_rating")) else None
                _plan = ""
                if pd.notna(row.get("entry")) and pd.notna(row.get("stop")):
                    _plan = (f'<span class="tb-mono" style="font-size:11px;">Entry '
                             f'{row["entry"]:.2f} · Stop {row["stop"]:.2f}'
                             + (f' · Target {row["target"]:.2f}'
                                if pd.notna(row.get("target")) else "") + '</span>')

                _chips = _scanner_source_chips(row.get("scanners"))
                # The stored note opens with "N scanners fired (A, B, C); …" —
                # exactly what the chips now show, and in a less usable form.
                # Drop that clause only when the chips actually rendered, so a
                # row with no scanner list still reads as a full sentence.
                _notes = str(row.get("notes") or "")
                if _chips:
                    _seg = _notes.split("; ")
                    if len(_seg) > 1 and "scanner" in _seg[0] and "fired" in _seg[0]:
                        _notes = "; ".join(_seg[1:])
                        _notes = _notes[:1].upper() + _notes[1:]

                # ── Fundamentals strip — PEG · OPM% · Cash Flow ───────────────
                _fund = None
                try:
                    _fund = sc.fetch_fundamentals_yf(_sym) or {}
                except Exception:
                    _fund = {}

                def _fchip(label: str, val, fmt: str, lo_good: bool = True,
                            green_thr=None, amber_thr=None) -> str:
                    """Compact fundamentals chip with traffic-light color."""
                    if val is None:
                        return ""
                    try:
                        v = float(val)
                    except (TypeError, ValueError):
                        return ""
                    txt = fmt.format(v)
                    if green_thr is not None and amber_thr is not None:
                        if lo_good:
                            col = ("#16a34a" if v <= green_thr
                                   else "#d97706" if v <= amber_thr else "#dc2626")
                        else:
                            col = ("#16a34a" if v >= green_thr
                                   else "#d97706" if v >= amber_thr else "#dc2626")
                    else:
                        col = "#5c4a3a"
                    return (f'<span style="display:inline-block;background:#f7efe3;'
                            f'border-radius:6px;padding:2px 8px;margin:0 5px 3px 0;'
                            f'font-size:11px;">'
                            f'<b style="color:#7a6858;font-weight:600;">{label}</b>'
                            f'<span style="color:{col};font-weight:700;margin-left:3px;">'
                            f'{txt}</span></span>')

                _peg_v = _fund.get("peg")
                _peg_lbl = "PEG~" if _fund.get("peg_src") == "calc" else "PEG"
                _opm_v  = _fund.get("opm_pct")
                _fcf_v  = _fund.get("fcf_cr")
                _ocf_v  = _fund.get("ocf_cr")

                _fund_parts = "".join(filter(None, [
                    _fchip(_peg_lbl, _peg_v, "{:.2f}×",
                           lo_good=True, green_thr=1.0, amber_thr=2.0),
                    _fchip("OPM%", _opm_v, "{:.1f}%",
                           lo_good=False, green_thr=20.0, amber_thr=10.0),
                    # Cash flow: positive FCF = green; use OCF as fallback label
                    (_fchip("FCF ₹cr", _fcf_v, "{:+,.0f}",
                            lo_good=False, green_thr=0.0, amber_thr=-500.0)
                     if _fcf_v is not None else
                     _fchip("OCF ₹cr", _ocf_v, "{:+,.0f}",
                            lo_good=False, green_thr=0.0, amber_thr=-500.0)),
                ]))
                _fund_html = (
                    f'<div style="margin:5px 0 3px;">{_fund_parts}</div>'
                    if _fund_parts else ""
                )

                st.markdown(
                    rs.card(
                        f'<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;">'
                        f'<span class="tb-mono" style="font-size:15px;font-weight:700;'
                        f'color:{rs.TOKENS["text_muted"]};">#{int(row["rank"])}</span>'
                        f'<b style="font-size:15px;">{_sym}</b>'
                        f'{_rating_badge_html({"overall": _rt, "overall_breakdown": {}})}'
                        f'<span class="tb-chip" style="background:{rs.TOKENS["surface_alt"]};'
                        f'color:{rs.TOKENS["text_body"]};">score {row["score"]:.1f}</span>'
                        f'{_confluence_chips(int(row["confluence"]), _fam_of(row))}'
                        f'<span style="margin-left:auto;display:inline-flex;'
                        f'align-items:center;gap:8px;">{_plan}'
                        f'{_card_action_links(_sym)}</span></div>'
                        f'<div class="tb-micro" style="margin-top:5px;">'
                        f'{row.get("industry") or "—"} · {row.get("sector") or "—"}</div>'
                        f'{_chips}'
                        f'{_fund_html}'
                        f'<div style="font-size:11.5px;color:{rs.TOKENS["text_body"]};'
                        f'margin-top:5px;line-height:1.45;">{_notes}</div>'
                    ),
                    unsafe_allow_html=True)

            _render_export_controls(orep.model_from_stored(_shortlist),
                                    key=f"od_{_sel_date}")

            st.caption(
                "Ranked by **0.45 × Overall Rating + 0.30 × best scanner score + "
                "0.25 × confluence**. Confluence weights scanners by *measured* "
                "backtest edge — Falling Wedge, Harmonic Reversal and Order Block "
                "count double, because the harness found the others at or below a "
                "random-entry baseline. Every name here already sits in a leading "
                "sector **and** industry; that is a filter, not a bonus. This is a "
                "shortlist to research, not a buy list.")

    st.divider()
    st.markdown("**Manual funnel** — drive the same steps yourself")

    _pct_cols = {
        "avg_momentum": st.column_config.NumberColumn("Avg Mom %", format="%.1f"),
        "median_momentum": st.column_config.NumberColumn("Median %", format="%.1f"),
        "breadth_pct": st.column_config.NumberColumn("Breadth %", format="%.0f"),
        "count": st.column_config.NumberColumn("# Stocks", format="%d"),
    }

    oh_left, oh_main = st.columns([1, 3])

    with oh_left:
        st.markdown("**1 · Universe**")
        oh_mode = st.radio(
            "Source", ["Full Market (Bhavcopy)", "Screener results", "Manual symbols"],
            key="oh_universe_mode",
            help="Each stock needs a sector tag + OHLCV — 200–300 names is a good "
                 "balance of coverage vs speed (results cache after the first run).")
        oh_universe: list[str] = []
        oh_top_n = 200
        if oh_mode == "Full Market (Bhavcopy)":
            oh_top_n = st.slider("Top N by traded value", 50, 5000, 500, 50, key="oh_bhav_n")
        elif oh_mode == "Screener results":
            _sr = st.session_state.get("screener_results")
            if _sr is not None and not _sr.empty:
                oh_universe = sorted(_sr["Symbol"].unique())
                st.caption(f"{len(oh_universe)} stocks from screener")
            else:
                st.caption("No screener results yet — run the Daily Screener Pipeline first.")
        else:
            _raw = st.text_area("Symbols (comma / newline)", key="oh_manual", height=80)
            oh_universe = [s.strip().upper() for s in _raw.replace(",", "\n").splitlines() if s.strip()]

        if st.button("Build Funnel", type="primary", key="oh_build"):
            if oh_mode == "Full Market (Bhavcopy)":
                with st.spinner("Loading market universe…"):
                    try:
                        oh_universe = cached_fetch_bhavcopy_universe(oh_top_n)
                    except Exception as exc:
                        st.error(f"Bhavcopy fetch failed: {exc}")
            if not oh_universe:
                st.warning("No universe loaded — pick a source above.")
            else:
                prog = st.progress(0.0, text="Tagging sectors + momentum…")
                def _oh_prog(i, total):
                    prog.progress(min(i / total, 1.0),
                                  text=f"Tagging sectors + momentum… {i}/{total}")
                with st.spinner("Building the funnel…"):
                    tbl = oh.build_constituent_table(
                        oh_universe, cached_fetch_ohlcv, progress_cb=_oh_prog)
                prog.empty()
                st.session_state["oh_table"] = tbl
                for _k in ("oh_hits", "oh_hits_scanner", "oh_pipe", "oh_pipe_meta"):
                    st.session_state.pop(_k, None)

        st.divider()
        st.markdown("**Step 4 — how to scan**")
        oh_mode_scan = st.radio(
            "Mode", ["All scanners (pipeline)", "One scanner"], key="oh_scan_mode",
            help="The pipeline runs every registered scanner over the leaders in "
                 "one pass and reports how many independent reads landed on each "
                 "name. One scanner answers 'does THIS pattern fire' instead.")
        _pipe_names = oh.pipeline_scanners()
        if oh_mode_scan.startswith("All"):
            oh_scanner = None
            st.caption(f"{len(_pipe_names)} scanners · "
                       f"{len(oh.SCANNER_FAMILIES)} families. "
                       f"**{', '.join(oh.RISK_SCANNERS)}** runs too but only as a "
                       f"warning — a bearish hit is never confluence.")
        else:
            oh_scanner = st.selectbox(
                "Scanner", list(sc.SCANNERS.keys()), key="oh_scanner",
                help="Runs on the leading-industry stocks only.")
            st.caption(sc.SCANNERS[oh_scanner]["description"])

    with oh_main:
        tbl = st.session_state.get("oh_table")
        if tbl is None:
            st.info("Pick a universe on the left and click **Build Funnel**.")
        elif tbl.empty:
            st.warning("No stocks could be placed (each needs a yfinance sector tag "
                       "+ a computable momentum). Try a different / larger universe.")
        else:
            st.caption(f"{len(tbl)} stocks placed across {tbl['sector'].nunique()} "
                       f"sectors · {tbl['industry'].nunique()} industries.")

            # ── 2 · Right Sector ───────────────────────────────────────────────
            st.markdown("#### 2 · Right Sector")
            sr = oh.rank_groups(tbl, "sector", min_constituents=3)
            if sr.empty:
                st.info("No sector has ≥3 constituents in this universe — widen it.")
            else:
                st.dataframe(sr, use_container_width=True, hide_index=True,
                             column_config=_pct_cols)
                _pos = sr[sr["avg_momentum"] > 0]["sector"].head(3).tolist()
                _def_sec = _pos or sr["sector"].head(3).tolist()
                sel_sectors = st.multiselect(
                    "Leading sectors to drill into", sr["sector"].tolist(),
                    default=_def_sec, key="oh_sectors")

                # ── 3 · Right Industry ─────────────────────────────────────────
                if sel_sectors:
                    st.markdown("#### 3 · Right Industry")
                    sub = tbl[tbl["sector"].isin(sel_sectors)]
                    ir = oh.rank_groups(sub, "industry", min_constituents=1)
                    st.dataframe(ir, use_container_width=True, hide_index=True,
                                 column_config=_pct_cols)
                    _def_ind = (ir[ir["avg_momentum"] > 0]["industry"].tolist()
                                or ir["industry"].tolist())
                    sel_inds = st.multiselect(
                        "Leading industries", ir["industry"].tolist(),
                        default=_def_ind, key="oh_industries")

                    # ── 4 · Right Stock → Pattern → Entry ──────────────────────
                    stocks = oh.stocks_in_groups(sub, "industry", sel_inds)
                    st.markdown(f"#### 4 · Right Stock → Pattern → Entry "
                                f"· {len(stocks)} candidates in the leaders")

                    # FP-5 — the peer comparison, drilled from the industry
                    # ranking. The Hub goes sector → industry → constituents;
                    # peer comparison fixes one constituent and turns the same
                    # group side-on. Same component as the Stock Analyzer's,
                    # called with a different anchor — built once, surfaced twice.
                    if stocks:
                        with st.expander("Compare one candidate against its peers",
                                         expanded=False):
                            _pc_pick = st.selectbox(
                                "Anchor", sorted(stocks), key="oh_peer_anchor",
                                help="Scores this name and its industry peers on the "
                                     "six fundamental axes.")
                            if _pc_pick:
                                render_peer_comparison(_pc_pick)

                    # ---- Pipeline: every scanner in one pass -----------------
                    if oh_scanner is None:
                        if stocks and st.button(
                                f"Run all {len(_pipe_names)} scanners on "
                                f"{len(stocks)} leading stocks",
                                type="primary", key="oh_pipe_run"):
                            try:
                                _bench = cached_fetch_nifty50()
                            except Exception:
                                _bench = None
                            _pp = st.progress(0.0, text="Starting the pipeline…")
                            def _pipe_prog(i, total, name):
                                _pp.progress(min(i / total, 1.0),
                                             text=f"Scanner {i}/{total} — {name}")
                            _pipe = oh.run_scanner_pipeline(
                                stocks, _scanner_fetch_fn, benchmark_df=_bench,
                                progress_cb=_pipe_prog)
                            _pp.empty()
                            _ow = st.session_state.get("hub_overall_weights",
                                                       OVERALL_WEIGHTS)
                            for _sym, _h in _pipe.items():
                                try:
                                    _r, _bd = _overall_rating(
                                        cached_fetch_ohlcv(_sym), _bench, _ow)
                                except Exception:
                                    _r, _bd = None, {}
                                _h["overall"] = _r
                                _h["overall_breakdown"] = _bd
                                # The score the ranking spends, same formula as the
                                # stored daily shortlist (opportunity_daily).
                                _h["rank_score"] = (
                                    od.W_RATING * (_r or 0)
                                    + od.W_SCANNER * min(_h["best_score"], 100)
                                    + od.W_CONFLUENCE * oh.confluence_pct(_h["edge_points"]))
                            st.session_state["oh_pipe"] = _pipe
                            st.session_state["oh_pipe_meta"] = {
                                "n_scanners": len(_pipe_names),
                                "n_stocks": len(stocks),
                                # Regime is read from the SAME benchmark frame
                                # this run scanned against, via the same scorer
                                # the headless job uses. Never borrowed from the
                                # last stored shortlist — that could be days old,
                                # and a stale regime on a fresh export is exactly
                                # the misread the stored rows exist to prevent.
                                "market": od._market_context(_bench),
                            }

                        _pipe = st.session_state.get("oh_pipe")
                        _meta = st.session_state.get("oh_pipe_meta", {})
                        if _pipe is not None:
                            if not _pipe:
                                st.info(f"None of the {_meta.get('n_scanners', 0)} "
                                        "scanners fired on any leading-industry "
                                        "stock. That is a real answer about today's "
                                        "tape — widen the sectors/industries or "
                                        "come back tomorrow.")
                            else:
                                shown = sorted(_pipe.values(),
                                               key=lambda h: h.get("rank_score") or 0,
                                               reverse=True)
                                # B-32/B-33: regime-prescriptive conviction gate —
                                # shrinks the list by itself, and HARD in RISK-OFF
                                # where bullish signals were measured to lose
                                # (regime_backtest.py). Same gate as the stored
                                # shortlist, on the live pipeline's rank_score.
                                _regime = (_meta.get("market") or {}).get("regime", "UNKNOWN")
                                _pre_gate = len(shown)
                                shown, _gate = od._apply_regime_gate(
                                    shown, _regime, top_n=100, score_key="rank_score",
                                    rating_key="overall")
                                _multi = sum(1 for h in shown if len(h["families"]) > 1)
                                if _gate["n_before"] != _gate["n_after"]:
                                    _gtone = "risk" if _regime == "RISK-OFF" else "warn"
                                    st.markdown(rs.callout(
                                        f"Regime gate [{_regime}]",
                                        f"{_pre_gate} candidates → **{len(shown)}** kept "
                                        f"({_gate['gate_txt']}). {_gate['note']}", tone=_gtone),
                                        unsafe_allow_html=True)
                                st.caption(
                                    f"**{len(shown)}** of {_meta.get('n_stocks', 0)} "
                                    f"leaders survived the {_regime} conviction gate · "
                                    f"**{_multi}** span more than one independent "
                                    f"family · sorted by the same score the stored "
                                    f"daily shortlist uses.")
                                for i in range(0, len(shown), 3):
                                    cols = st.columns(3)
                                    for col, h in zip(cols, shown[i:i + 3]):
                                        with col:
                                            _render_pipeline_card(h)
                                # Export the live funnel too, carrying the
                                # sectors/industries this run actually drilled —
                                # provenance the stored path cannot know.
                                _mkt = _meta.get("market") or {}
                                _render_export_controls(
                                    orep.model_from_pipeline(
                                        _pipe,
                                        regime=_mkt.get("regime"),
                                        verdict=_mkt.get("verdict"),
                                        candidates=_meta.get("n_stocks"),
                                        lead_sectors=sel_sectors,
                                        lead_industries=sel_inds,
                                        n_scanners=_meta.get("n_scanners")),
                                    key="oh_pipe_export")

                                st.caption(
                                    "**Reading the two counts.** *N scanners* is the "
                                    "raw catch count. *N families* collapses scanners "
                                    "that read the same fact — five trend scanners on "
                                    "one uptrending chart are one read, not five — and "
                                    "the family count is what the score actually "
                                    "spends. Green chips were measured to beat a "
                                    "random-entry baseline; amber chips were measured "
                                    "and did **not**; grey were never measured. "
                                    "Agreement is not evidence: no backtest yet shows "
                                    "that confluence itself predicts anything.")

                    # ---- Single scanner (the original step 4) ----------------
                    elif stocks and st.button(
                            f"Scan {len(stocks)} leading stocks with {oh_scanner}",
                            type="primary", key="oh_scan"):
                        try:
                            _bench = cached_fetch_nifty50()
                        except Exception:
                            _bench = None
                        with st.spinner(f"Running {oh_scanner} on {len(stocks)} leaders…"):
                            _hits = sc.run_scanner(oh_scanner, stocks,
                                                   _scanner_fetch_fn(oh_scanner),
                                                   benchmark_df=_bench)
                        _ow = st.session_state.get("hub_overall_weights", OVERALL_WEIGHTS)
                        for _h in _hits:
                            try:
                                _r, _bd = _overall_rating(
                                    cached_fetch_ohlcv(_h["symbol"]), _bench, _ow)
                            except Exception:
                                _r, _bd = None, {}
                            _h["overall"] = _r
                            _h["overall_breakdown"] = _bd
                        st.session_state["oh_hits"] = _hits
                        st.session_state["oh_hits_scanner"] = oh_scanner

                    if oh_scanner is not None:
                        _hits = st.session_state.get("oh_hits")
                        _ran = st.session_state.get("oh_hits_scanner", "")
                        if _hits is not None:
                            if not _hits:
                                st.info(f"No **{_ran}** matches among the leading stocks. "
                                        "Try another scanner, or widen the sectors/industries.")
                            else:
                                shown = sorted(
                                    _hits,
                                    key=lambda h: (h.get("overall") is not None,
                                                   h.get("overall") or 0),
                                    reverse=True)
                                st.caption(f"{len(shown)} matches from **{_ran}** on the "
                                           f"leaders · sorted by Overall Rating")
                                for i in range(0, len(shown), 3):
                                    cols = st.columns(3)
                                    for col, card in zip(cols, shown[i:i + 3]):
                                        with col:
                                            _render_scanner_card(card, _ran)


# ──────────────────────────────────────────────────────────────────────────────
# Delete Funnel — the technofunda 8-filter subtractive sieve (B-38).
# Wraps technofunda_funnel: each filter can only DELETE; survivors are a
# shortlist, not a buy list. The chart legs (F6-F8) are the ones backtested
# separately (funnel_backtest.py); the fundamental legs are gathered live.
# ──────────────────────────────────────────────────────────────────────────────
_FUNNEL_TONE = {tff.PASS: "good", tff.CAVEAT: "warn", tff.DELETE: "risk"}


@st.cache_data(ttl=900, show_spinner=False)
def _funnel_bench_12m() -> float | None:
    """Nifty trailing ~12-month return (fraction) for the F7 relative-strength
    leg. Cached so a whole funnel run shares one benchmark read."""
    try:
        c = cached_fetch_nifty50(days=520)["close"].dropna()
        n = tff.Thresholds().rs_lookback
        if len(c) > n:
            return float(c.iloc[-1] / c.iloc[-1 - n] - 1.0)
    except Exception:
        pass
    return None


def _funnel_context(symbol: str, bench_ret_12m: float | None) -> dict:
    """Assemble one symbol's funnel context from the existing cached fetchers.
    Fundamentals + red-flags are the slow legs; both are already st.cache_data."""
    try:
        # The DEEP statement payload (CAGRs, ROCE, FCF, D/E, interest coverage) —
        # NOT cached_fetch_fundamentals, which is the yfinance .info snapshot.
        deep = cached_fundamentals_deep(symbol)
    except Exception:
        deep = None
    try:
        flags = cached_red_flags(symbol)
    except Exception:
        flags = None
    try:
        price = cached_fetch_ohlcv(symbol, days=520)   # ≥252 bars for RS + 200DMA
    except Exception:
        price = None
    return tff.build_context(symbol, deep=deep, flags=flags, price=price,
                             bench_ret_12m=bench_ret_12m)


def _render_funnel_survivor(result) -> None:
    """One survivor card: the eight filter chips (pass/caveat) + action buttons.
    Survivors carry no DELETE outcome by definition, so every chip is green or
    amber; the reason strings (which carry the numbers) sit in a 'why' expander."""
    sym = result.symbol
    chips = "".join(
        rs.chip(o.fid, _FUNNEL_TONE.get(o.verdict, "neutral")) for o in result.outcomes)
    cav = (f'<div style="margin-top:4px;font-size:11px;color:{rs.TOKENS["accent"]};">'
           f'⚠ {len(result.caveats)} caveat(s) — unverified, not confirmed clean</div>'
           if result.caveats else "")
    st.markdown(
        rs.card(f'<div style="display:flex;align-items:baseline;gap:8px;">'
                f'<span style="font-weight:700;font-size:15px;color:{rs.TOKENS["text"]};">'
                f'{sym}</span>'
                f'<span style="font-size:11px;color:{rs.TOKENS["good"]};">survives all 8</span>'
                f'</div><div style="margin-top:6px;">{chips}</div>{cav}',
                emphasis=False),
        unsafe_allow_html=True)
    with st.expander("why it survived"):
        for o in result.outcomes:
            st.markdown(f"- **{o.fid} {o.label}** — {o.reason}")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("♥ Watchlist", key=f"df_wl_{sym}", use_container_width=True):
            db.add_watchlist_symbol(sym, "Delete Funnel survivor")
            st.toast(f"♥ {sym} → Watchlist")
    with b2:
        if st.button("↗ Analyze", key=f"df_an_{sym}", use_container_width=True):
            st.session_state["current_page"] = "Stock Analyzer"
            st.session_state["sa_symbol_override"] = sym
            st.rerun()
    with b3:
        if st.button("⊕ Roster", key=f"df_ro_{sym}", use_container_width=True):
            roster = st.session_state.setdefault("sa_roster", [])
            if sym not in roster:
                roster.append(sym)
            st.toast(f"⊕ {sym} → Roster ({len(roster)})")


if current_page == "Delete Funnel":
    st.subheader("Delete Funnel")
    st.caption("The technofunda 8-filter **delete** sieve — each filter can only "
               "*remove* a name; what survives is a shortlist, **not a buy list**. "
               "Fundamentals first (growth · cash · leverage · returns · governance), "
               "then price (>200 DMA · relative strength · accumulation). "
               "Unvalidated as a whole — the chart legs are backtested in "
               "`funnel_backtest.py`; passing means *investable and confirmed*, not "
               "*buy today*.")

    _fc1, _fc2 = st.columns([2, 1])
    with _fc1:
        _src = st.radio("Universe to sieve", ["Watchlist", "Paste symbols",
                        "Top-volume universe"], horizontal=True, key="df_src")
    with _fc2:
        _strict = st.checkbox("Strict", value=True, key="df_strict",
                              help="A filter that can't be evaluated DELETES the name "
                                   "(burden of proof). Off = it passes with a caveat.")

    _syms: list[str] = []
    if _src == "Watchlist":
        try:
            _wl = db.get_watchlist()
            _syms = [str(s).upper() for s in _wl["symbol"].tolist()] if not _wl.empty else []
        except Exception:
            _syms = []
        if not _syms:
            st.info("Your Watchlist is empty — add names on the Watchlist page, or "
                    "pick another universe.")
    elif _src == "Paste symbols":
        _txt = st.text_area("Symbols (comma / space / newline separated)",
                            key="df_paste", height=90, placeholder="TITAN, CDSL, KPITTECH")
        _norm = (_txt or "").replace(",", " ").replace("\n", " ").replace("\t", " ")
        _syms = [t.strip().upper() for t in _norm.split() if t.strip()]
    else:
        _n = st.number_input("Top-volume names", min_value=5, max_value=60, value=25,
                             step=5, key="df_topn")
        if st.checkbox("Load universe", key="df_load_univ"):
            try:
                _syms = cached_fetch_bhavcopy_universe(int(_n))
            except Exception as _e:
                st.error(f"Could not load the top-volume universe: {_e}")

    # The two fundamental legs fan out to yfinance statements + NSE ownership per
    # name, so a big list is slow. Cap hard and say so, rather than hang.
    _CAP = 50
    if len(_syms) > _CAP:
        st.warning(f"{len(_syms)} names — sieving the first {_CAP} "
                   f"(fundamentals + red-flags are fetched per name).")
        _syms = _syms[:_CAP]

    with st.expander("Thresholds (defaults match the strategy page)"):
        _t = tff.Thresholds()
        _cta, _ctb, _ctc = st.columns(3)
        with _cta:
            _t.min_rev_cagr_3y = st.number_input("Min rev CAGR 3Y %", value=float(_t.min_rev_cagr_3y), key="df_t_rev")
            _t.min_profit_cagr_3y = st.number_input("Min profit CAGR 3Y %", value=float(_t.min_profit_cagr_3y), key="df_t_pro")
        with _ctb:
            _t.max_de = st.number_input("Max D/E", value=float(_t.max_de), step=0.1, key="df_t_de")
            _t.min_interest_cov = st.number_input("Min interest cover ×", value=float(_t.min_interest_cov), step=0.5, key="df_t_cov")
        with _ctc:
            _t.min_roce = st.number_input("Min ROCE %", value=float(_t.min_roce), key="df_t_roce")
            _t.max_base_range = st.number_input("Max base range (F8)", value=float(_t.max_base_range), step=0.01, key="df_t_base")

    if st.button("Run the funnel", type="primary", disabled=not _syms, key="df_run"):
        _bench = _funnel_bench_12m()
        if _bench is None:
            st.warning("Nifty benchmark unavailable — the relative-strength leg (F7) "
                       "will delete every name under strict. Consider unchecking Strict.")
        _prog = st.progress(0.0, text="Sieving…")
        _ctxs = []
        for _i, _s in enumerate(_syms):
            _prog.progress((_i + 1) / len(_syms), text=f"{_s}  ({_i + 1}/{len(_syms)})")
            _ctxs.append(_funnel_context(_s, _bench))
        _prog.empty()
        _fr = tff.run_funnel(_ctxs, thresholds=_t, strict=_strict)
        st.session_state["df_result"] = _fr
        st.session_state["df_result_bench"] = _bench

    _fr = st.session_state.get("df_result")
    if _fr is not None:
        st.markdown(rs.section("Funnel drop-off"), unsafe_allow_html=True)
        st.caption(f"**{_fr.n_in}** in → **{_fr.n_out}** survive. Each row is where "
                   f"the universe died — a name is deleted by the *first* filter it fails.")
        _remaining = _fr.n_in
        _rows = []
        for _fid, _label, _killed in _fr.dropoff:
            _remaining -= _killed
            _rows.append({"Filter": f"{_fid} {_label}", "Deleted here": _killed,
                          "Left": _remaining})
        st.dataframe(pd.DataFrame(_rows), hide_index=True, use_container_width=True)

        if _fr.survivors:
            st.markdown(rs.section(f"Survivors ({len(_fr.survivors)})"),
                        unsafe_allow_html=True)
            _surv = [_fr.results[s] for s in _fr.survivors]
            for _i in range(0, len(_surv), 3):
                _cols = st.columns(3)
                for _col, _r in zip(_cols, _surv[_i:_i + 3]):
                    with _col:
                        _render_funnel_survivor(_r)
        else:
            st.info("Nothing survived all eight filters. In a subtractive sieve that "
                    "is a real answer — widen the universe, relax a threshold, or "
                    "uncheck Strict if too much was deleted for missing data.")

        _deleted = [(s, r) for s, r in _fr.results.items() if not r.survived]
        if _deleted:
            with st.expander(f"Deleted names ({len(_deleted)}) — the reject ledger"):
                _drows = []
                for _s, _r in _deleted:
                    _kill = next((o for o in _r.outcomes if o.verdict == tff.DELETE), None)
                    _drows.append({"Symbol": _s, "Deleted at": _r.deleted_at,
                                   "Reason": _kill.reason if _kill else "—"})
                st.dataframe(pd.DataFrame(_drows), hide_index=True,
                             use_container_width=True)

    # ── Backtest the price legs — the part of the claim that IS testable ───────
    with st.expander("Backtest the price legs (F6 ∧ F7 ∧ F8)"):
        st.caption("Does requiring all three chart footprints beat a random bar in "
                   "the same tape — and beat any single leg? Point-in-time replay "
                   "over the universe above. **The fundamental legs F1–F5 are not "
                   "point-in-time testable** (yfinance serves only current "
                   "statements), so this measures the chart half only.")
        if not _syms:
            st.info("Pick a universe above first.")
        elif st.button("Run price-legs backtest", key="df_bt_run"):
            with st.spinner(f"Replaying F6∧F7∧F8 over {len(_syms)} names…"):
                try:
                    _bench_df = cached_fetch_nifty50(days=1500)
                    _res = fbt.backtest_price_funnel(
                        _syms, lambda s: cached_fetch_ohlcv(s, days=1500), _bench_df)
                    st.session_state["df_bt_result"] = fbt.format_funnel_backtest(_res)
                except Exception as _e:
                    st.session_state["df_bt_result"] = f"Backtest failed: {_e}"
        if st.session_state.get("df_bt_result"):
            st.code(st.session_state["df_bt_result"], language=None)


# Hidden Treasures — small/micro-cap conviction discovery lane (B-34).
# Tab 8 — Scanner Hub (SwingEdge-inspired pre-built pattern scanners)
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Scanner Hub":
    st.subheader("Scanner Hub")
    st.caption("Pre-built pattern scanners — choose a scanner, select a universe, run.")


    # ── Scanner card grid (full-width, replaces left panel) ──────────────────
    hub_mode = st.radio(
        "Run mode",
        ["Single scanner", "Pipeline — all scanners"],
        key="hub_mode",
        horizontal=True,
        help="Single: run one scanner and see its cards. "
             "Pipeline: run every scanner in sequence, save all hits to the DB "
             "fact table, and see a consolidated view.",
    )

    # Default the card grid to the CORE list. `oh.COVERED_SCANNERS` are the ones measured
    # to contribute zero unique (symbol, as-of) cells — every hit they produce is already
    # flagged by something else on the list (analyses/Scanner-Overlap-Audit). They are
    # hidden, not removed: one toggle brings them back, and they remain runnable,
    # backtestable and active in the pipeline. Coverage is not quality, so this reduces
    # what you have to read, not what the system knows.
    _covered = [n for n in sc.SCANNERS if n in oh.COVERED_SCANNERS]
    _show_covered = False
    if _covered:
        _show_covered = st.checkbox(
            f"Show {len(_covered)} covered scanners",
            key="hub_show_covered",
            help="Measured to add no unique hits — everything they flag is already "
                 "flagged by another scanner on the list. Hidden by default to cut "
                 "reading, not capability: they still run, backtest and score.",
        )
    _visible = set(sc.SCANNERS) if _show_covered else set(oh.core_scanners())
    # A session saved before this change (or a deep link) can have a covered scanner
    # selected. Keep its card on screen regardless, or the caption below describes a
    # scanner the user can see no card for and cannot deselect.
    _sel_now = st.session_state.get("hub_scanner")
    if _sel_now in sc.SCANNERS:
        _visible.add(_sel_now)

    by_cat: dict[str, list[str]] = {}
    for name, spec in sc.SCANNERS.items():
        if name in _visible:
            by_cat.setdefault(spec["category"], []).append(name)

    selected_scanner = st.session_state.get("hub_scanner", list(sc.SCANNERS.keys())[0])
    if selected_scanner not in sc.SCANNERS:
        selected_scanner = list(sc.SCANNERS.keys())[0]
        st.session_state["hub_scanner"] = selected_scanner

    _hub_run_immediately = None  # set to scanner name when ▶ clicked

    if hub_mode == "Single scanner":
        st.markdown("""<style>
.hub-cat-label {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .06em; color: #7a6858; margin: 14px 0 6px;
    padding-bottom: 4px; border-bottom: 1px solid #f0e0cc;
}
/* Tighten gap between card div and the ▶ button beneath it */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]
    > div[data-testid="stMarkdownContainer"] + div[data-testid="stButton"] {
    margin-top: -8px;
}
div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]
    > div[data-testid="stButton"] > button {
    border-radius: 0 0 8px 8px !important;
    border-top: none !important;
    font-size: 12px !important;
    padding: 3px 8px !important;
}
</style>""", unsafe_allow_html=True)
        for cat in ["Pattern", "Momentum", "Trend", "Entry", "Risk"]:
            if cat not in by_cat:
                continue
            st.markdown(f'<div class="hub-cat-label">{cat}</div>', unsafe_allow_html=True)
            _names = by_cat[cat]
            _card_cols = st.columns(3)
            for _ci, _cname in enumerate(_names):
                with _card_cols[_ci % 3]:
                    _is_sel = _cname == selected_scanner
                    _desc = sc.SCANNERS[_cname]["description"]
                    _short = (_desc[:72] + "…") if len(_desc) > 72 else _desc
                    _border = (f"2px solid {rs.TOKENS['accent']}" if _is_sel
                               else f"1px solid {rs.TOKENS['border']}")
                    _bg = rs.TOKENS["accent_soft"] if _is_sel else rs.TOKENS["surface"]
                    # Card: name + description. Flat bottom edge merges with ▶ button below.
                    st.markdown(
                        f'<div style="border:{_border};border-bottom:none;'
                        f'border-radius:8px 8px 0 0;'
                        f'padding:10px 12px 10px;background:{_bg};min-height:80px;">'
                        f'<div style="font-size:13px;'
                        f'font-weight:{"700" if _is_sel else "600"};'
                        f'color:{rs.TOKENS["accent"] if _is_sel else rs.TOKENS["text"]};'
                        f'margin-bottom:5px;line-height:1.3;">{_cname}</div>'
                        f'<div style="font-size:11px;color:{rs.TOKENS["text_muted"]};'
                        f'line-height:1.4;">{_short}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    # ▶ Run button fused to card bottom — no Select button
                    if st.button(
                        "▶  Run" if _is_sel else "▶",
                        key=f"hub_run_now_{_cname}",
                        help=f"Select and run {_cname}",
                        type="primary" if _is_sel else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["hub_scanner"] = _cname
                        _hub_run_immediately = _cname

    st.divider()
    st.caption(sc.SCANNERS[selected_scanner]["description"])

    # Quality Small-Cap PEAD (Phase 5.1) carries its own fundamentals gate,
    # tuned here. Stored in session_state and read by the Run handler.
    is_quality_pead = sc.SCANNERS[selected_scanner].get("quality_pead", False)
    if is_quality_pead:
        with st.expander("Quality gate (fundamentals)", expanded=True):
            st.caption("yfinance fundamentals — no login. Applied to the "
                       "universe BEFORE the drift scan. Cards show "
                       "ROE · OPM · PE · PEG · market cap.")
            q_allcaps = st.toggle(
                "All market caps", value=True, key="qp_allcaps",
                help="On: no market-cap limit (all caps). Off: restrict to a "
                     "small/mid-cap ceiling set below.")
            q_mcap = None
            if not q_allcaps:
                q_mcap = st.slider("Max market cap (₹ Cr) — cap ceiling",
                                   500, 50000, 20000, step=500, key="qp_mcap")
            q_de = st.slider("Max Debt/Equity (0.10 ≈ zero debt)",
                             0.0, 2.0, 0.10, step=0.05, key="qp_de")
            q_roe = st.slider("Min ROE %", 0, 40, 15, step=1, key="qp_roe")
            q_opm = st.slider("Min OPM %", 0, 50, 10, step=1, key="qp_opm")
            st.caption("Valuation caps (0 = no limit):")
            q_max_pe = st.slider("Max PE (0 = off)", 0, 150, 0, step=1, key="qp_max_pe")
            q_max_peg = st.slider("Max PEG (0 = off)", 0.0, 5.0, 0.0, step=0.1,
                                  key="qp_max_peg",
                                  help="Includes the computed ~PEG (PE÷growth) "
                                       "when yfinance's vendor PEG is absent.")
            q_complete = st.toggle(
                "Require complete fundamentals", value=True, key="qp_complete",
                help="On: drop names whose debt/ROE/OPM/PE/PEG yfinance can't "
                     "confirm (honest — can't call a name 'zero-debt' unseen). "
                     "Off: keep them, skipping only the missing checks.")
            st.session_state["qp_params"] = {
                "max_market_cap_cr": q_mcap, "max_de_ratio": q_de,
                "min_roe_pct": float(q_roe), "min_opm_pct": float(q_opm),
                "max_pe": (float(q_max_pe) if q_max_pe > 0 else None),
                "max_peg": (float(q_max_peg) if q_max_peg > 0 else None),
                "require_complete": q_complete,
            }
            st.caption("⚠ Fetches fundamentals per symbol — prefer the "
                       "**Screener results** universe or a smaller Top-N; a "
                       "full 300+ market scan is slow on the first run "
                       "(results cache after).")

    with st.expander("Overall Rating weights"):
        st.caption("Tune the /100 cross-system rollup. Applies on the next scan.")
        _wm = st.slider("Minervini", 0.0, 1.0, OVERALL_WEIGHTS["minervini"], 0.05, key="ow_m")
        _wt = st.slider("TechnoFunda", 0.0, 1.0, OVERALL_WEIGHTS["technofunda"], 0.05, key="ow_tf")
        _wc = st.slider("CANSLIM", 0.0, 1.0, OVERALL_WEIGHTS["canslim"], 0.05, key="ow_c")
        _we = st.slider("Elliott Wave", 0.0, 1.0, OVERALL_WEIGHTS["ew"], 0.05, key="ow_ew")
        _wtot = _wm + _wt + _wc + _we
        if _wtot > 0:
            st.session_state["hub_overall_weights"] = {
                "minervini": _wm / _wtot, "technofunda": _wt / _wtot,
                "canslim": _wc / _wtot, "ew": _we / _wtot,
            }
            st.caption(f"Normalised (raw sum {_wtot:.2f} → 1.00)")

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
            "Top N by traded value", min_value=50, max_value=5000, value=500, step=50,
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

    # ── Cached results ────────────────────────────────────────────────────
    _cached_dates = db.get_scanner_run_dates(selected_scanner)
    if _cached_dates:
        with st.expander(f"Cached results — {len(_cached_dates)} run(s) stored", expanded=False):
            _load_date = st.selectbox(
                "Load results from", _cached_dates,
                key="hub_cache_date",
                help="Pick a past run to restore its results without re-fetching data.",
            )
            _col_load, _col_del = st.columns(2)
            if _col_load.button("Load from cache", key="hub_cache_load", type="primary",
                                use_container_width=True):
                _cached = db.get_scanner_run(selected_scanner, _load_date)
                if _cached:
                    st.session_state["hub_results"] = _cached
                    st.session_state["hub_scanner_ran"] = selected_scanner
                    st.session_state["hub_cache_loaded_date"] = _load_date
                    st.rerun()
                else:
                    st.warning("Cache entry is empty — run the scanner to populate it.")
            if _col_del.button("Delete this cache entry", key="hub_cache_del",
                               use_container_width=True):
                db.delete_scanner_run(selected_scanner, _load_date)
                st.rerun()

    _run_single = (
        (hub_mode == "Single scanner" and st.button(
            "Run Scanner", type="primary", key="hub_run", use_container_width=True))
        or (_hub_run_immediately is not None)
    )
    if _hub_run_immediately:
        selected_scanner = _hub_run_immediately
    _run_pipeline = hub_mode == "Pipeline — all scanners" and st.button(
        "Run All Scanners", type="primary", key="hub_run_pipeline",
        use_container_width=True,
        help="Runs every pipeline scanner in sequence and saves hits to the "
             "scanner_run_cache fact table in the database.",
    )

    # ── Pipeline run ──────────────────────────────────────────────────────
    if _run_pipeline:
        if not universe and universe_mode == "Full Market (Bhavcopy)":
            with st.spinner("Loading market universe…"):
                try:
                    universe = cached_fetch_bhavcopy_universe(bhav_top_n)
                    st.session_state["hub_bhav_universe"] = universe
                except Exception as exc:
                    st.error(f"Bhavcopy fetch failed: {exc}")

        if not universe:
            st.warning("No universe loaded — pick a source above.")
        else:
            try:
                bench_df = cached_fetch_nifty50()
            except Exception:
                bench_df = None

            # ── Batch pre-fetch (the key speed fix) ───────────────────────
            # One yf.download for all symbols → in-memory dict → scanners do
            # µs dict lookups instead of 500 × individual network calls.
            # auto_adjust=True matches VolumeFetcher (the single-scan path).
            _pl_prog = st.progress(0.0, text="Pre-fetching universe data (batch download)…")
            import yfinance as _yf
            import pandas as _pd_pipe
            _tickers_yf = [
                (s if s.endswith(".NS") else s + ".NS") for s in universe
            ]
            _prefetch_cache: dict[str, _pd_pipe.DataFrame | None] = {}
            _batch_ok = False
            try:
                _raw = _yf.download(
                    _tickers_yf,
                    period="2y",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )
                _raw_mb = _raw.memory_usage(deep=True).sum() / 1_048_576
                _pl_prog.progress(
                    0.05,
                    text=f"Downloaded {_raw_mb:.1f} MB — slicing {len(_tickers_yf)} symbols…",
                )
                _avail = set(_raw.columns.get_level_values(0))
                for _sym, _ticker in zip(universe, _tickers_yf):
                    try:
                        if _ticker not in _avail:
                            _prefetch_cache[_sym] = None
                            continue
                        _frame = _raw[_ticker].copy()
                        _frame.columns = [c.lower() for c in _frame.columns]
                        _frame = _frame.dropna(subset=["close"])
                        _prefetch_cache[_sym] = _frame if not _frame.empty else None
                    except Exception:
                        _prefetch_cache[_sym] = None
                _batch_ok = True
            except Exception as _exc:
                st.warning(f"Batch download failed ({_exc}) — falling back to per-symbol fetch (slower).")

            # Full-history scanners (ATH, IPO breakout) need 6000-bar history.
            # Batch pre-fetch uses 2y which is enough for most; those scanners
            # fall back to the cached per-symbol fetch.
            def _pl_fetch(scanner_name: str):
                if sc.SCANNERS.get(scanner_name, {}).get("needs_full_history"):
                    return _scanner_fetch_fn(scanner_name)  # per-symbol (cached)
                def _lookup(sym):
                    if sym in _prefetch_cache:
                        return _prefetch_cache[sym]
                    # Symbol not in batch (illiquid / missing) — fall back to cache
                    return cached_fetch_ohlcv(sym)
                return _lookup

            _pl_names = oh.pipeline_scanners()
            _pl_hits: dict[str, list] = {}
            for _pi, _pname in enumerate(_pl_names, 1):
                _pl_prog.progress(
                    _pi / (len(_pl_names) + 1),
                    text=f"[{_pi}/{len(_pl_names)}] {_pname}…",
                )
                try:
                    _pcards = sc.run_scanner(
                        _pname, universe,
                        _pl_fetch(_pname),
                        benchmark_df=bench_df,
                    )
                except Exception:
                    _pcards = []
                _pl_hits[_pname] = _pcards
                if _pcards:
                    try:
                        db.save_scanner_run(_pname, _pcards)
                    except Exception:
                        pass
            _pl_prog.empty()
            st.session_state["hub_pipeline_results"] = _pl_hits
            st.session_state.pop("hub_pipeline_cache_date", None)
            total_hits = sum(len(v) for v in _pl_hits.values())
            st.success(
                f"Pipeline complete — {len(_pl_names)} scanners · "
                f"{total_hits} hits · saved to DB"
            )

    if _run_single:
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
            if sc.SCANNERS[selected_scanner].get("quality_pead", False):
                # Phase 5.1 composite — quality fundamentals gate ∩ Proxy-PEAD.
                qp = st.session_state.get("qp_params", {})
                prog = st.progress(0.0, text="Screening fundamentals…")
                def _qp_progress(i, total):
                    prog.progress(min(i / total, 1.0),
                                  text=f"Screening fundamentals… {i}/{total}")
                with st.spinner(f"Running {selected_scanner} on {len(universe)} symbols…"):
                    hits = sc.run_quality_pead(
                        universe, cached_fetch_ohlcv, benchmark_df=bench_df,
                        progress_cb=_qp_progress, **qp)
                prog.empty()
            else:
                with st.spinner(f"Running {selected_scanner} on {len(universe)} symbols…"):
                    hits = sc.run_scanner(selected_scanner, universe,
                                          _scanner_fetch_fn(selected_scanner),
                                          benchmark_df=bench_df)
            # M1 — attach a cross-system Overall Rating to each hit once, here
            # at scan time (reuses the OHLCV the scanner just fetched — cached).
            # bench_df is the Nifty50 benchmark used for RS-based sub-scores.
            _ow = st.session_state.get("hub_overall_weights", OVERALL_WEIGHTS)
            if hits:
                with st.spinner(f"Scoring {len(hits)} matches…"):
                    for _h in hits:
                        try:
                            _r, _bd = _overall_rating(
                                cached_fetch_ohlcv(_h["symbol"]), bench_df, _ow)
                        except Exception:
                            _r, _bd = None, {}
                        _h["overall"] = _r
                        _h["overall_breakdown"] = _bd
            st.session_state["hub_results"] = hits
            st.session_state["hub_scanner_ran"] = selected_scanner
            st.session_state.pop("hub_cache_loaded_date", None)
            # Auto-save to DB so results survive a browser refresh or restart.
            try:
                db.save_scanner_run(selected_scanner, hits)
            except Exception:
                pass

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

    # ── Daily Scheduler ───────────────────────────────────────────────────
    st.divider()
    with st.expander("Daily Scanner Scheduler", expanded=False):
        st.caption(
            "Register a Windows Scheduled Task that runs all scanners "
            "automatically after market close (default 16:15 IST). "
            "Requires the dashboard Python interpreter and writes results "
            "to a dated JSON in `tools/cache/`."
        )
        _sched_time = st.text_input(
            "Run time (HH:MM, 24h)", value="16:15", key="hub_sched_time",
            help="Time in your local clock. 16:15 = 15 min after NSE close.",
        )
        _sched_universe = st.radio(
            "Universe for scheduled run",
            ["Full Market (Bhavcopy Top 300)", "Screener results (today's pipeline)"],
            key="hub_sched_universe",
        )
        _sched_scanners = st.multiselect(
            "Scanners to include",
            list(sc.SCANNERS.keys()),
            default=list(sc.SCANNERS.keys()),
            key="hub_sched_scanners",
            help="Leave all selected to run the full suite.",
        )

        _RUNNER_BAT = BASE_DIR / "tools" / "scanner_daily.bat"
        _RUNNER_PY  = BASE_DIR / "tools" / "scanner_daily_runner.py"
        _PYTHON_EXE = r"C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe"
        _TASK_NAME  = "TradingBramha-DailyScanner"

        if st.button("Generate runner + register task", key="hub_sched_reg",
                     type="primary"):
            try:
                # The runner is a CHECKED-IN module (tools/scanner_daily_runner.py),
                # not generated source. It used to be written here from an
                # f-string template, and the template was broken: an un-indented
                # `for` body (so it never parsed) plus imports of three modules
                # that do not exist. Generated Python is invisible to import,
                # py_compile, linting and tests, which is precisely how that
                # survived. All this panel writes now is the .bat, and the
                # universe choice travels as an argument.
                _universe_arg = ("--universe bhavcopy --top-n 300"
                                 if "Bhavcopy" in _sched_universe
                                 else "--universe screener")
                # An explicit scanner list is passed ONLY when it is a real
                # subset; "all selected" stays as the runner's own default so the
                # task does not silently freeze today's registry into the .bat.
                _scanners_arg = ""
                if _sched_scanners and len(_sched_scanners) < len(sc.SCANNERS):
                    _scanners_arg = " --scanners " + " ".join(
                        f'"{_s}"' for _s in _sched_scanners)

                # Write the .bat wrapper
                _bat_src = (
                    f"@echo off\n"
                    f"set PYTHON={_PYTHON_EXE}\n"
                    f"set REPO=%~dp0..\n"
                    f"set LOG=%~dp0scanner_daily.log\n"
                    f"cd /d \"%REPO%\"\n"
                    f"echo. >> \"%LOG%\"\n"
                    f"echo ===== %DATE% %TIME% - daily scanner starting ===== >> \"%LOG%\"\n"
                    f"\"%PYTHON%\" \"%~dp0scanner_daily_runner.py\" {_universe_arg}{_scanners_arg} >> \"%LOG%\" 2>&1\n"
                    f"if errorlevel 1 (\n"
                    f"    echo ***** FAILED ***** >> \"%LOG%\"\n"
                    f") else (\n"
                    f"    echo ----- ok ----- >> \"%LOG%\"\n"
                    f")\n"
                )
                _RUNNER_BAT.write_text(_bat_src, encoding="utf-8")

                # Register the Windows Scheduled Task
                import subprocess
                _h, _m = _sched_time.strip().split(":")
                _schtasks_create = [
                    "schtasks", "/create", "/f",
                    "/tn", _TASK_NAME,
                    "/tr", str(_RUNNER_BAT),
                    "/sc", "DAILY",
                    "/st", f"{int(_h):02d}:{int(_m):02d}",
                    "/rl", "HIGHEST",
                ]
                _res = subprocess.run(
                    _schtasks_create, shell=False,
                    capture_output=True, text=True,
                )
                if _res.returncode == 0:
                    st.success(
                        f"Task **{_TASK_NAME}** registered — runs daily at {_sched_time}. "
                        f"Runner: `tools/scanner_daily_runner.py` "
                        f"`{_universe_arg}{_scanners_arg}` · "
                        f"Log: `tools/scanner_daily.log`"
                    )
                else:
                    st.error(f"schtasks failed: {_res.stderr or _res.stdout}")
                    st.code(" ".join(_schtasks_create), language="bat")
                    st.caption("Run the command above in an elevated CMD/PowerShell.")
            except Exception as _exc:
                st.error(f"Setup failed: {_exc}")

        if st.button("Remove scheduled task", key="hub_sched_del"):
            import subprocess
            _r = subprocess.run(
                ["schtasks", "/delete", "/f", "/tn", _TASK_NAME],
                shell=False, capture_output=True, text=True,
            )
            if _r.returncode == 0:
                st.success(f"Task {_TASK_NAME} removed.")
            else:
                st.warning(_r.stderr or _r.stdout or "Task not found — may not have been registered.")

    # ── Results (full-width) ───────────────────────────────────────────────
    # ── Pipeline mode results ─────────────────────────────────────────────
    if hub_mode == "Pipeline — all scanners":
        _pl_res = st.session_state.get("hub_pipeline_results")
        _pl_cache_date = st.session_state.get("hub_pipeline_cache_date")

        # Pipeline cached-run loader — shows dates stored in DB for any scanner
        _pl_dates = db.get_scanner_run_dates(oh.pipeline_scanners()[0]) if oh.pipeline_scanners() else []
        if _pl_dates:
            with st.expander(f"Load past pipeline run ({len(_pl_dates)} stored)", expanded=False):
                _pl_load_date = st.selectbox(
                    "Run date", _pl_dates, key="hub_pl_cache_date_pick",
                )
                if st.button("Load pipeline run from cache", key="hub_pl_cache_load"):
                    _loaded: dict[str, list] = {}
                    for _pn in oh.pipeline_scanners():
                        _cached = db.get_scanner_run(_pn, _pl_load_date)
                        if _cached:
                            _loaded[_pn] = _cached
                    if _loaded:
                        st.session_state["hub_pipeline_results"] = _loaded
                        st.session_state["hub_pipeline_cache_date"] = _pl_load_date
                        st.rerun()
                    else:
                        st.warning("No pipeline cache found for that date — run the pipeline first.")

        if not _pl_res:
            st.info("Select a universe on the left and click **Run All Scanners**.")
        else:
            if _pl_cache_date:
                st.caption(f"Showing cached pipeline run from **{_pl_cache_date}**.")

            # ── Summary table ─────────────────────────────────────────────
            _pl_summary = [
                {"Scanner": name, "Hits": len(cards),
                 "Top Symbol": (cards[0]["symbol"] if cards else "—"),
                 "Top Score": (cards[0].get("score", 0) if cards else 0)}
                for name, cards in _pl_res.items()
                if cards
            ]
            _pl_empty = [name for name, cards in _pl_res.items() if not cards]

            total_pl_hits = sum(r["Hits"] for r in _pl_summary)
            st.markdown(
                f"**{len(_pl_summary)} scanners fired** · "
                f"{total_pl_hits} total hits · "
                f"{len(_pl_empty)} scanners empty"
            )

            # ── Promoter pledge % enrichment (screener.in) ────────────────
            # yfinance has no pledge field; this fetches it per symbol from
            # screener.in (quarterly, disk-cached ~45 days) so the cards can
            # show a Pledge cell. Prioritises confluence symbols and caps live
            # fetches per click so a big universe fills the cache over runs
            # instead of hammering screener in one go.
            with st.expander("🔒 Promoter pledge % (screener.in)", expanded=False):
                from collections import Counter as _PCounter
                _pl_all_counts = _PCounter(
                    c["symbol"] for cards in _pl_res.values() for c in cards
                )
                # confluence symbols first (most scanners → most interesting)
                _pl_syms_ranked = [s for s, _ in _pl_all_counts.most_common()]
                _cached_n = sum(
                    1 for s in _pl_syms_ranked if ss.read_pledge_cache(s) is not None
                )
                st.caption(
                    f"{len(_pl_syms_ranked)} unique symbols · "
                    f"{_cached_n} already cached. Absent pledge row on "
                    f"screener.in = treated as 0% (unpledged)."
                )
                _pl_cap = st.slider(
                    "Max new fetches this click", 10, 200, 40,
                    key="hub_pledge_cap",
                    help="Cached symbols are free; this caps only fresh "
                         "screener.in fetches (~1.5s each) to stay under rate limits.",
                )
                if st.button("Fetch pledge %", key="hub_fetch_pledge"):
                    _sid, _br = bch.get_screener_sessionid()
                    if not _sid:
                        st.warning(
                            "No screener.in `sessionid` cookie found in your local "
                            "browsers — log into screener.in in Chrome/Edge/Firefox "
                            "and click again."
                        )
                    else:
                        with st.spinner(
                            f"Fetching pledge % from screener.in "
                            f"(≤{_pl_cap} new, {_br})…"
                        ):
                            try:
                                _recs = ss.refresh_pledge(
                                    _pl_syms_ranked, _sid, limit=_pl_cap,
                                )
                                st.session_state["hub_pledge_fetched"] = len(_recs)
                                st.success(
                                    f"Pledge % ready for {len(_recs)} symbols "
                                    f"(cached). Reopen a scanner group to see the "
                                    f"Pledge cell on cards."
                                )
                            except Exception as _pexc:
                                st.error(f"screener.in pledge fetch failed: {_pexc}")
                        st.rerun()

            if _pl_summary:
                import pandas as _pd_pl
                _sum_df = _pd_pl.DataFrame(_pl_summary).sort_values("Hits", ascending=False)
                _sum_df = _with_chart_family(_sum_df, "Top Symbol")
                st.dataframe(
                    _sum_df, hide_index=True, use_container_width=True,
                    column_config=_chart_family_colcfg(),
                )

                # Shareable card — top scanners, symbol linked to TradingView
                with st.expander("📋 Copy as shareable card (Telegram / social)",
                                 expanded=False):
                    _sum_n = st.slider(
                        "Rows to include", 5, min(50, len(_pl_summary)),
                        min(15, len(_pl_summary)), key="hub_sum_card_n",
                    )
                    _sum_sorted = _pd_pl.DataFrame(_pl_summary).sort_values(
                        "Top Score", ascending=False
                    ).head(_sum_n)
                    _sub = (f"{_pl_cache_date or date.today().isoformat()} · "
                            f"{len(_pl_summary)} scanners fired · {total_pl_hits} hits")
                    _items = [
                        {"label": r["Scanner"], "sym": r["Top Symbol"],
                         "score": r["Top Score"], "meta": f"{r['Hits']} hits"}
                        for r in _sum_sorted.to_dict("records")
                    ]
                    _sum_tabs = st.tabs(["🃏 Rich card", "💬 Plain text"])
                    with _sum_tabs[0]:
                        _ch, _tx = _share_card_html(
                            "📊 Trading Bramha — Scanner Hub", _sub, _items,
                        )
                        _render_copy_card(_ch, _tx, key="sumcard")
                    with _sum_tabs[1]:
                        _pl = _share_card_plain(
                            "📊 Trading Bramha — Scanner Hub",
                            f"🗓 {_sub}", _items, bullet="📈",
                        )
                        _render_copy_plain(_pl, key="sumplain")

            # ── Confluence view: symbols in 2+ scanners ───────────────────
            from collections import Counter as _Counter
            _sym_counts = _Counter(
                card["symbol"]
                for cards in _pl_res.values()
                for card in cards
            )
            _confluence = {sym for sym, cnt in _sym_counts.items() if cnt >= 2}
            if _confluence:
                st.divider()
                st.markdown(
                    f"**Confluence signals** — {len(_confluence)} symbol(s) "
                    f"fired in 2+ scanners"
                )
                _conf_rows = []
                for sym in sorted(_confluence):
                    scanners_fired = [
                        name for name, cards in _pl_res.items()
                        if any(c["symbol"] == sym for c in cards)
                    ]
                    # Pledge % from the screener.in disk cache (no network) —
                    # blank until fetched via the pledge expander above.
                    _plrec = ss.read_pledge_cache(sym)
                    _conf_rows.append({
                        "Symbol": sym,
                        "Scanners": ", ".join(scanners_fired),
                        "Count": len(scanners_fired),
                        "Pledge %": (_plrec.get("pledge_pct") if _plrec else None),
                    })
                _conf_rows.sort(key=lambda r: r["Count"], reverse=True)
                import pandas as _pd_conf
                _conf_df = _with_chart_family(
                    _pd_conf.DataFrame(_conf_rows), "Symbol",
                )
                _conf_colcfg = {
                    **_chart_family_colcfg(),
                    "Pledge %": st.column_config.NumberColumn(
                        "Pledge %", format="%.1f%%",
                        help="Promoter pledge (screener.in). Blank = not fetched "
                             "yet — use the pledge expander above.",
                    ),
                }
                st.dataframe(
                    _conf_df, hide_index=True, use_container_width=True,
                    column_config=_conf_colcfg,
                )

                # Shareable card — top confluence symbols by scanner count
                with st.expander("📋 Copy as shareable card (Telegram / social)",
                                 expanded=False):
                    _cf_n = st.slider(
                        "Symbols to include", 5, min(50, len(_conf_rows)),
                        min(15, len(_conf_rows)), key="hub_conf_card_n",
                    )
                    _cf_sub = (f"{_pl_cache_date or date.today().isoformat()} · "
                               f"{len(_confluence)} symbols in 2+ scanners")
                    _cf_items = [
                        {"sym": r["Symbol"], "meta": f"{r['Count']} scanners"}
                        for r in _conf_rows[:_cf_n]
                    ]
                    _cf_tabs = st.tabs(["🃏 Rich card", "💬 Plain text"])
                    with _cf_tabs[0]:
                        _cf_ch, _cf_tx = _share_card_html(
                            "🎯 Trading Bramha — Confluence", _cf_sub, _cf_items,
                        )
                        _render_copy_card(_cf_ch, _cf_tx, key="confcard")
                    with _cf_tabs[1]:
                        _cf_pl = _share_card_plain(
                            "🎯 Trading Bramha — Confluence",
                            f"🗓 {_cf_sub}", _cf_items, bullet="🔸",
                        )
                        _render_copy_plain(_cf_pl, key="confplain")

            # ── Per-scanner card groups ───────────────────────────────────
            st.divider()
            st.markdown("**Results by scanner**")
            for _pname, _pcards in _pl_res.items():
                if not _pcards:
                    continue
                with st.expander(f"{_pname} — {len(_pcards)} hit(s)", expanded=False):
                    cols_n = 3
                    for _pi in range(0, len(_pcards), cols_n):
                        _batch = _pcards[_pi:_pi + cols_n]
                        _cols = st.columns(cols_n)
                        for _col, _card in zip(_cols, _batch):
                            with _col:
                                _render_scanner_card(_card, _pname)

    else:
        # ── Single scanner mode results ───────────────────────────────────
        hits = st.session_state.get("hub_results")
        ran_for = st.session_state.get("hub_scanner_ran", "")

        if hits is None:
            st.info("Choose a scanner on the left and click **Run Scanner**.")
        elif ran_for != selected_scanner:
            st.info(f"Last run was for **{ran_for}**. Click **Run Scanner** to scan with **{selected_scanner}**.")
        elif not hits:
            st.info(f"No stocks matched **{selected_scanner}** in this universe.")
        else:
            _cache_date = st.session_state.get("hub_cache_loaded_date")
            if _cache_date:
                st.caption(f"Showing cached results from **{_cache_date}** — run the scanner again to refresh.")
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

            # M1 — Overall Rating floor + sort (scored names first, highest first).
            has_overall = any(h.get("overall") is not None for h in shown)
            sort_label = "scanner score"
            if has_overall:
                min_overall = st.slider(
                    "Min Overall Rating", 0, 100, 0, 5, key="hub_min_overall",
                    help="Cross-system /100 rollup (Minervini + TechnoFunda + CANSLIM + EW). "
                         "0 = show all.",
                )
                if min_overall > 0:
                    shown = [h for h in shown if (h.get("overall") or 0) >= min_overall]
                shown = sorted(
                    shown,
                    key=lambda h: (h.get("overall") is not None, h.get("overall") or 0),
                    reverse=True,
                )
                sort_label = "Overall Rating"

            # Combined consolidation-breakout scan: longest duration outranks
            # any score — a 10-year breakout is a rarer, bigger statement than
            # a high-scoring 6-month one. Re-sort AFTER the Overall Rating
            # block above so duration stays the primary key. Presentation
            # stays the standard 3-column card grid (user decision, see memory
            # scanner-results-card-presentation): duration is tags[0] on each
            # card, so the ordering + label carry the duration story.
            has_duration = any("duration_days" in h for h in shown)
            if has_duration:
                shown = sorted(
                    shown,
                    key=lambda h: (h.get("duration_days", 0),
                                   h.get("overall") or 0,
                                   h.get("score", 0)),
                    reverse=True,
                )
                sort_label = "breakout duration (longest first)"

            filt_note = "" if len(shown) == len(hits) else f" ({len(hits)} matched)"
            if not shown:
                st.info("No stocks match the current filter pills — widen the filter above.")
            else:
                # ── Pagination ────────────────────────────────────────────────
                _PAGE_SZ = 30
                _total_cards = len(shown)
                _total_pages = max(1, (_total_cards + _PAGE_SZ - 1) // _PAGE_SZ)
                # Reset page when scanner or filter changes
                _pg_key = f"hub_page_{selected_scanner}"
                _page = st.session_state.get(_pg_key, 0)
                if _page >= _total_pages:
                    _page = 0
                    st.session_state[_pg_key] = 0
                _page_start = _page * _PAGE_SZ
                _page_shown = shown[_page_start: _page_start + _PAGE_SZ]

                # Caption + roster badge
                _roster = st.session_state.get("sa_roster", [])
                _roster_badge = (f" · **{len(_roster)} in roster**" if _roster else "")
                st.caption(
                    f"Showing {_total_cards} stocks{filt_note} · sorted by {sort_label}"
                    f" · page {_page + 1}/{_total_pages}{_roster_badge}"
                )

                # Card grid
                cols_n = 3
                for i in range(0, len(_page_shown), cols_n):
                    batch = _page_shown[i:i + cols_n]
                    cols = st.columns(cols_n)
                    for col, card in zip(cols, batch):
                        with col:
                            _render_scanner_card(card, selected_scanner)

                # Pagination controls
                if _total_pages > 1:
                    _pc1, _pc2, _pc3, _pc4, _pc5 = st.columns([1, 1, 2, 1, 1])
                    with _pc1:
                        if st.button("⏮", key="hub_pg_first",
                                     disabled=_page == 0,
                                     help="First page",
                                     use_container_width=True):
                            st.session_state[_pg_key] = 0
                            st.rerun()
                    with _pc2:
                        if st.button("◀", key="hub_pg_prev",
                                     disabled=_page == 0,
                                     help="Previous page",
                                     use_container_width=True):
                            st.session_state[_pg_key] = _page - 1
                            st.rerun()
                    with _pc3:
                        _jump = st.number_input(
                            "Go to page", min_value=1, max_value=_total_pages,
                            value=_page + 1, step=1, key="hub_pg_jump",
                            label_visibility="collapsed",
                        )
                        if int(_jump) - 1 != _page:
                            st.session_state[_pg_key] = int(_jump) - 1
                            st.rerun()
                    with _pc4:
                        if st.button("▶", key="hub_pg_next",
                                     disabled=_page >= _total_pages - 1,
                                     help="Next page",
                                     use_container_width=True):
                            st.session_state[_pg_key] = _page + 1
                            st.rerun()
                    with _pc5:
                        if st.button("⏭", key="hub_pg_last",
                                     disabled=_page >= _total_pages - 1,
                                     help="Last page",
                                     use_container_width=True):
                            st.session_state[_pg_key] = _total_pages - 1
                            st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Predictive Analysis (Milestone 4) — the consolidated "should I take this
# trade" surface. PURE COMPOSITION of shipped pieces: M1's Overall Rating
# (ranked candidate rail from the last Scanner Hub run) + the Chart Tool iframe
# carrying M2 pattern overlays and the M3 price-projection line + the Setup
# Intelligence / Council engine from the Stock Analyzer. No new backend.
# See wiki/analyses/Dashboard-UI-Roadmap.md §Milestone 4.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Predictive Analysis":
    st.subheader("Predictive Analysis")
    st.caption(
        "One screen: ranked candidates (left) → annotated chart + ratings + setup "
        "intelligence (right). Candidates come from the last **Scanner Hub** run; "
        "the chart carries the pattern overlays and price projection from the Chart Tool."
    )

    pa_left, pa_main = st.columns([1, 2.6], gap="medium")

    with pa_left:
        hits = st.session_state.get("hub_results") or []
        ran_for = st.session_state.get("hub_scanner_ran", "")
        ranked = sorted(
            hits,
            key=lambda h: (h.get("overall") is not None, h.get("overall") or 0),
            reverse=True,
        )
        st.markdown("**Candidates**")
        if not ranked:
            st.info("No Scanner Hub results in this session — run a scanner there "
                    "first, or type a symbol below.")
        else:
            st.caption(f"{len(ranked)} from **{ran_for}** · ranked by Overall Rating")
            for h in ranked[:30]:
                _sym = h["symbol"]
                bcol, vcol = st.columns([4, 1])
                with bcol:
                    st.markdown(
                        f'<div style="display:flex;align-items:center;padding:3px 0;">'
                        f'{_rating_badge_html(h)}'
                        f'<b style="color:#3a2a1e;margin-right:8px;">{_sym}</b>'
                        f'<span style="background:#fff1e0;color:#c2410c;padding:1px 8px;'
                        f'border-radius:99px;font-size:10.5px;">'
                        f'{h.get("pattern_type", ran_for)}</span></div>',
                        unsafe_allow_html=True,
                    )
                with vcol:
                    if st.button("→", key=f"pa_view_{_sym}", help=f"Analyze {_sym}"):
                        st.session_state["pa_symbol"] = _sym

        st.divider()
        mcol1, mcol2 = st.columns([3, 1])
        pa_manual = mcol1.text_input("Any symbol", key="pa_manual",
                                     placeholder="e.g. TITAN",
                                     label_visibility="collapsed")
        if mcol2.button("Go", key="pa_go", use_container_width=True) and pa_manual.strip():
            st.session_state["pa_symbol"] = pa_manual.strip().upper()

    with pa_main:
        pa_sym = st.session_state.get("pa_symbol")
        if not pa_sym:
            st.info("Pick a candidate on the left (→) or type a symbol to load the "
                    "annotated chart, ratings breakdown, and setup intelligence.")
        else:
            pa_df = cached_fetch_ohlcv(pa_sym, enforce_liquidity=False)
            if pa_df is None:
                st.error(f"No usable data for {pa_sym} — fewer than {sp.MIN_BARS} "
                         f"daily bars, or not on yfinance under that NSE code.")
            else:
                _thin_volume_note(pa_df, pa_sym)
                pa_bench = cached_fetch_nifty50()
                _pa_w = st.session_state.get("hub_overall_weights", OVERALL_WEIGHTS)
                pa_rating, pa_bd = _overall_rating(pa_df, pa_bench, _pa_w)
                pa_chips = "".join(
                    f'<span style="background:#f7efe3;border-radius:6px;padding:2px 8px;'
                    f'margin-right:6px;font-size:11px;color:#5c4a3a;">'
                    f'<b style="color:#7a6858;font-weight:600;">{k}</b> {v}</span>'
                    for k, v in (pa_bd or {}).items()
                )
                st.markdown(
                    f'<div style="display:flex;align-items:center;flex-wrap:wrap;'
                    f'margin-bottom:4px;">'
                    f'{_rating_badge_html({"overall": pa_rating, "overall_breakdown": pa_bd or {}})}'
                    f'<span style="font-size:20px;font-weight:800;color:#3a2a1e;'
                    f'margin-right:12px;">{pa_sym}</span>{pa_chips}</div>',
                    unsafe_allow_html=True,
                )

                # Annotated chart — the Chart Tool iframe carries every overlay the
                # user has enabled there (M2 base zones, harmonic, trendlines, M3
                # price projection, MA Bias, …). Indicator selection persists in
                # the Chart Tool's own localStorage, so it survives reloads.
                render_chart_tool(pa_sym)

                # Setup Intelligence + Council — same engine as the Stock Analyzer.
                st.divider()
                with st.spinner("Running deterministic council…"):
                    pa_fund = cached_fetch_fundamentals(pa_sym)
                    pa_bundle, pa_bull, pa_bear, pa_card = council.run_council(
                        pa_sym, pa_df, pa_bench, pa_fund, regime=nifty_regime
                    )
                render_setup_intelligence(
                    council.setup_intelligence(pa_bundle, pa_bull, pa_bear, pa_card)
                )
                with st.expander("Council drill-down (Bull / Bear / Judge)"):
                    render_council(pa_bundle, pa_bull, pa_bear, pa_card)


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

            # ── SR-6: Relative Rotation Graph ─────────────────────────────────
            # The quadrant above plots 1Y vs 1M *absolute* return, so in a market
            # that rises together every sector piles into the top-right and the
            # picture stops discriminating. This measures each sector against the
            # benchmark and adds the second derivative, which is what turns four
            # corners into a cycle. Price-only by design — it needs none of the
            # ownership data the orbit chart is still blocked on (SR-2).
            st.divider()
            st.markdown("#### Relative Rotation Graph (vs NIFTY 50)")

            rg1, rg2, rg3 = st.columns([1, 1, 1])
            with rg1:
                rrg_freq = st.radio("Bars", ["Weekly", "Daily"], horizontal=True,
                                    key="sm_rrg_freq",
                                    help="RRG is conventionally read weekly; "
                                         "daily is materially noisier.")
            with rg2:
                rrg_tail = st.slider("Tail length", 3, 20, 8, key="sm_rrg_tail")
            with rg3:
                rrg_window = st.slider("Z-score window", 8, 30, rrg_mod.DEFAULT_WINDOW,
                                       key="sm_rrg_window")

            rrg_bench = cached_fetch_benchmark()
            rrg_res = rrg_mod.compute(
                sector_data, SECTOR_DISPLAY_NAMES, rrg_bench,
                freq="W" if rrg_freq == "Weekly" else "D",
                window=rrg_window, tail=rrg_tail,
            )

            if not rrg_res["sectors"]:
                st.warning(
                    f"Nothing to plot — {rrg_res['reason'] or 'not enough history'}. "
                    f"Skipped: {', '.join(rrg_res['skipped']) or 'none'}."
                )
            else:
                _QCOL = {"Leading": rs.TOKENS["good"], "Weakening": rs.TOKENS["accent"],
                         "Lagging": rs.TOKENS["risk"], "Improving": rs.TOKENS["info"]}
                fig_rrg = go.Figure()

                # Axis span padded around 100 so the quadrant cross always sits
                # in view even when every sector happens to sit on one side.
                _vals = [p[k] for s in rrg_res["sectors"] for p in s["points"]
                         for k in ("rs_ratio", "rs_momentum")]
                _span = max(1.2, max(abs(v - 100) for v in _vals) * 1.15)
                _lo, _hi = 100 - _span, 100 + _span

                for _x0, _x1, _y0, _y1, _c in (
                        (100, _hi, 100, _hi, rs.TOKENS["good"]),      # Leading
                        (100, _hi, _lo, 100, rs.TOKENS["accent"]),    # Weakening
                        (_lo, 100, _lo, 100, rs.TOKENS["risk"]),      # Lagging
                        (_lo, 100, 100, _hi, rs.TOKENS["info"])):     # Improving
                    fig_rrg.add_shape(type="rect", x0=_x0, x1=_x1, y0=_y0, y1=_y1,
                                      fillcolor=_c, opacity=0.07, line_width=0,
                                      layer="below")
                fig_rrg.add_hline(y=100, line=dict(color="#999", width=1, dash="dot"))
                fig_rrg.add_vline(x=100, line=dict(color="#999", width=1, dash="dot"))

                for s in rrg_res["sectors"]:
                    xs = [p["rs_ratio"] for p in s["points"]]
                    ys = [p["rs_momentum"] for p in s["points"]]
                    col = _QCOL[s["quadrant"]]
                    # Tail fades toward the past: the head is the reading, the
                    # tail is only how it got there.
                    fig_rrg.add_trace(go.Scatter(
                        x=xs, y=ys, mode="lines+markers", name=s["name"],
                        line=dict(color=col, width=1.5),
                        marker=dict(size=4, color=col, opacity=0.45),
                        hovertext=[f'{s["name"]} · {p["date"]}' for p in s["points"]],
                        hovertemplate="%{hovertext}<br>RS-Ratio %{x:.2f}"
                                      "<br>RS-Mom %{y:.2f}<extra></extra>",
                        showlegend=False,
                    ))
                    fig_rrg.add_trace(go.Scatter(
                        x=[xs[-1]], y=[ys[-1]], mode="markers+text",
                        text=[s["name"]], textposition="top center",
                        textfont=dict(size=10),
                        marker=dict(size=12, color=col,
                                    line=dict(color="white", width=1.5)),
                        hovertemplate=f'<b>{s["name"]}</b><br>{s["quadrant"]}'
                                      "<br>RS-Ratio %{x:.2f}<br>RS-Mom %{y:.2f}"
                                      "<extra></extra>",
                        showlegend=False,
                    ))

                _ann = [dict(x=_hi, y=_hi, text="<b>Leading</b>", showarrow=False,
                             xanchor="right", yanchor="top",
                             font=dict(color=rs.TOKENS["good"], size=11)),
                        dict(x=_hi, y=_lo, text="<b>Weakening</b>", showarrow=False,
                             xanchor="right", yanchor="bottom",
                             font=dict(color=rs.TOKENS["accent"], size=11)),
                        dict(x=_lo, y=_lo, text="<b>Lagging</b>", showarrow=False,
                             xanchor="left", yanchor="bottom",
                             font=dict(color=rs.TOKENS["risk"], size=11)),
                        dict(x=_lo, y=_hi, text="<b>Improving</b>", showarrow=False,
                             xanchor="left", yanchor="top",
                             font=dict(color=rs.TOKENS["info"], size=11))]
                fig_rrg.update_layout(
                    height=520, margin=dict(t=20, l=60, r=20, b=60),
                    xaxis=dict(title="RS-Ratio (relative trend)", range=[_lo, _hi],
                               zeroline=False),
                    yaxis=dict(title="RS-Momentum (rate of change)", range=[_lo, _hi],
                               zeroline=False),
                    annotations=_ann, showlegend=False,
                )
                st.plotly_chart(fig_rrg, use_container_width=True)

                _by_q = {}
                for s in rrg_res["sectors"]:
                    _by_q.setdefault(s["quadrant"], []).append(s["name"])
                st.markdown(rs.strip([
                    rs.stat_card(q, str(len(_by_q.get(q, []))) if q in _by_q else "0",
                                 ", ".join(_by_q.get(q, [])) or "—",
                                 tone=rrg_mod.QUADRANTS[q]["tone"])
                    for q in ("Leading", "Weakening", "Lagging", "Improving")
                ], cols=4), unsafe_allow_html=True)

                if rrg_res["skipped"]:
                    st.caption("Not enough history to place: "
                               + ", ".join(rrg_res["skipped"]))
                st.caption(
                    f"Rotation reads clockwise: Improving → Leading → Weakening → "
                    f"Lagging. {rrg_freq.lower()} bars · z-score window "
                    f"{rrg_res['window']} · momentum over {rrg_res['mom_period']} "
                    f"periods · tail {rrg_res['tail']}"
                    + (f" · through {rrg_res['as_of']}" if rrg_res["as_of"] else "")
                    + ". **This is a price-relative measure, not a flow measure** — "
                    "it says a sector is outperforming, not that money is moving "
                    "into it. JdK's exact RS-Ratio/RS-Momentum formulas are "
                    "proprietary; this is the standard public approximation, and "
                    "each sector is standardised against **its own** history, so "
                    "read the quadrant and direction of travel rather than "
                    "comparing coordinates between sectors."
                )

            # ── Shareable card ────────────────────────────────────────────────
            # The three surfaces above are interactive Plotly and never leave
            # the tab. This renders the same read as a PNG that can be posted.
            # Its own period selector rather than the heatmap's: the card you
            # want to share is often not the period you happen to be studying.
            st.divider()
            st.markdown("#### Shareable Card")
            st.caption(
                "Rendered from the sector frames already loaded above — no extra "
                "fetch. The market-breadth footer rides the last **persisted** "
                "sentiment reading; refresh it on Market Sentiment if the card "
                "flags it as stale."
            )

            cd_left, cd_right = st.columns([1, 2])
            with cd_left:
                card_period = st.radio(
                    "Period", ["1D", "1W", "1M", "3M", "1Y"],
                    horizontal=True, key="sm_card_period",
                )
                card_2x = st.checkbox(
                    "2× resolution", value=False, key="sm_card_2x",
                    help="2160px wide — sharper on retina timelines, ~4× the file size.",
                )

            card_days = {"1D": 1, "1W": 5, "1M": 21, "3M": 63, "1Y": 252}[card_period]
            card_model = scard.build_model(
                sector_data, SECTOR_DISPLAY_NAMES, _period_return,
                card_days, card_period, cached_latest_sentiment(), date.today(),
            )

            if not card_model["sectors"]:
                st.warning(
                    "No sector index returned enough history for this period — "
                    "nothing to put on a card."
                )
            else:
                card_png = scard.render_png(card_model, scale=2 if card_2x else 1)
                with cd_right:
                    st.download_button(
                        "⬇ Download PNG", card_png,
                        file_name=(f"sector-breadth-{date.today().isoformat()}"
                                   f"-{card_period.lower()}.png"),
                        mime="image/png", type="primary",
                    )
                    st.caption(f"{len(card_png) / 1024:.0f} KB · "
                               f"{2160 if card_2x else 1080}px wide")
                st.image(card_png, width=540)
                with st.expander("Copy as text (WhatsApp / Telegram)"):
                    st.code(scard.render_text(card_model), language=None)

    # ── Row 2: historical orbit chart ─────────────────────────────────────────
    st.divider()
    st.markdown("#### Historical Sector Rotation Orbit Chart")
    st.caption(
        "Ownership axis from **NSE's SEBI shareholding XBRL** — no login, no "
        "screener.in export. A legacy `screener_export_*.csv` still works and is "
        "offered below when one exists."
    )

    # ── SR-4: rebuild straight from the cached NSE filings ────────────────────
    # This is the whole point of SR-1…SR-5: the orbit chart no longer needs a
    # hand-driven browser session. The cache is authoritative and the emit costs
    # no network call for the ownership side; only the quarter-end prices for
    # SR-5's historical cap weighting are fetched, and those batch.
    _oc_status = ocache.status()
    nse_col1, nse_col2 = st.columns([1, 3])
    with nse_col1:
        nse_rebuild = st.button(
            "🛰 Rebuild from NSE filings", type="primary",
            disabled=_oc_status["symbols"] == 0,
            help=("Emit the wide frame from the ownership cache and re-run the "
                  "trail." if _oc_status["symbols"] else
                  "Ownership cache is empty — run the backfill first (see below)."),
        )
    with nse_col2:
        if _oc_status["symbols"]:
            st.caption(
                f"Cache: **{_oc_status['symbols']} symbols · "
                f"{_oc_status['quarters_total']} quarters** · "
                f"{_oc_status['periods'][0]} → {_oc_status['periods'][-1]}"
                + (f" · ⚠ {_oc_status['non_reconciling']} rows failed their "
                   "promoter/public cross-check and will be excluded"
                   if _oc_status["non_reconciling"] else " · all rows reconcile"))
        else:
            st.caption("Ownership cache empty. Backfill it first:")
            st.code("python tools/ownership_cache.py --backfill --quarters 8", language="bash")

    # The result is stashed rather than written straight out, because the rerun
    # below is what makes the orbit chart pick up the newly dated file — and a
    # st.success() immediately before st.rerun() is discarded before anyone sees
    # it. Render it on the next pass instead.
    if st.session_state.pop("nse_rebuild_msg", None):
        st.success(st.session_state.pop("nse_rebuild_text", "Rebuilt."))

    if nse_rebuild:
        try:
            with st.spinner("Emitting wide frame from the ownership cache…"):
                _nse_csv = BASE_DIR / f"nse_ownership_wide_{date.today():%Y%m%d}.csv"
                _wide = ocache.emit_csv(_nse_csv, quarters=8)
            with st.spinner(f"Running the trail over {len(_wide)} symbols…"):
                secrot_trail.run(_nse_csv)
            _nq = len([c for c in _wide.columns if c.startswith("FII_")])
            _nc = len([c for c in _wide.columns if c.startswith("CAP_")])
            st.session_state["nse_rebuild_msg"] = True
            st.session_state["nse_rebuild_text"] = (
                f"Rebuilt from {len(_wide)} symbols across {_nq} quarters "
                f"({_nc} weighted by their own historical cap) — "
                f"source `{_nse_csv.name}`.")
            st.rerun()
        except Exception as exc:
            st.error(f"NSE rebuild failed: {exc}")

    st.divider()

    # Legacy path — kept working rather than deleted: an existing screener.in
    # export is still a valid input, and `load_wide_export` reads both shapes.
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
                _paginated_df(df_sr, key="sector_rotation_saved")
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

    # City selector + share button
    col_city, col_date, col_share = st.columns([2, 2, 1])
    with col_city:
        city = st.selectbox("Select Location", list(at.AstroIndicators.CITIES.keys()), index=0)
    with col_date:
        analysis_date = st.date_input("Analysis Date", value=date.today())
    with col_share:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        _gen_card = st.button("📷 Share Card", use_container_width=True,
                              help="Generate a weekly astro infographic and copy PNG to clipboard")

    ai = at.AstroIndicators(city=city)
    timing = ai.get_trading_timing(analysis_date)

    # Daily summary. AW-0: the lunar figures are None outside the reversal
    # calendar's coverage, and a date we cannot place must render as unplaced
    # rather than as a confident number — that is the whole point of the fix.
    _lun = timing['lunar_phase']
    _unknown = _lun.get('phase') == 'unknown' or _lun.get('cycle_day') is None
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Lunar Phase",
            "—" if _unknown else _lun['phase'].title(),
            "outside calendar coverage" if _unknown
            else f"{_lun['illumination']}% illuminated"
        )
    with col2:
        st.metric(
            "Market Intensity",
            "—" if timing['market_intensity'] is None
            else f"{timing['market_intensity']}/100",
            "Volatility indicator"
        )
    with col3:
        st.metric(
            "Cycle Day",
            "—" if _unknown else f"{_lun['cycle_day']:.1f}",
            "no lunation to measure against" if _unknown
            else f"of {_lun['cycle_length']:.1f}"
        )
    with col4:
        st.metric("Location", city, "")

    if _unknown:
        st.warning(
            f"No lunation covers {analysis_date}. The reversal calendar holds "
            "new/full moons for a fixed window; extend it with "
            "`py -3 tools/reversal_calendar.py build --years …` (needs `ephem`)."
        )
    elif _lun.get("source") == "reversal_calendar":
        st.caption(
            "Lunar figures read from the reversal-calendar DB (PyEphem-derived "
            "instants), not from a mean-cycle approximation."
        )

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

    # ── Nakshatra Sector Forecast ──────────────────────────────────────────────
    st.subheader("Nakshatra Sector Forecast — 7-Day Forward")
    st.caption(
        "Moon's nakshatra (lunar mansion) for each trading day ahead. "
        "Each nakshatra rules specific commodities and NSE sectors — use as a "
        "directional bias, not an entry signal."
    )

    _nk_today = ai.get_nakshatra(analysis_date)
    _nk_df = pd.DataFrame()   # always defined; populated below if nakshatra succeeds

    if "error" in _nk_today:
        st.warning(f"Nakshatra engine: {_nk_today['error']}")
    else:
        # Today's nakshatra at a glance
        nk_c1, nk_c2, nk_c3, nk_c4 = st.columns(4)
        with nk_c1:
            st.metric("Today's Nakshatra", _nk_today["nakshatra"],
                      f"#{_nk_today['index']} of 27")
        with nk_c2:
            st.metric("Ruling Planet", _nk_today["planet"],
                      f"{_nk_today['pct']}% through")
        with nk_c3:
            st.metric("Sectors to Watch", " · ".join(_nk_today["sectors"][:2]),
                      _nk_today["sectors"][2] if len(_nk_today["sectors"]) > 2 else "")
        with nk_c4:
            st.metric("Moon Longitude (sid.)", f"{_nk_today['sidereal_lon']}°",
                      f"{_nk_today['deg_in']}° in nakshatra")

        st.info(f"**Commodity theme today:** {_nk_today['theme']}")

        # 7-day table
        _nk_df = ai.get_nakshatra_forecast(analysis_date, days=7)
        if isinstance(_nk_df, list):
            import pandas as _pd_nk
            _nk_df = _pd_nk.DataFrame(_nk_df)

        # Highlight today (first row)
        def _nk_row_style(row):
            if row.name == 0:
                return [f"background:rgba(74,222,128,0.12)" for _ in row]
            return ["" for _ in row]

        st.dataframe(
            _nk_df.style.apply(_nk_row_style, axis=1),
            use_container_width=True,
            hide_index=True,
        )

        # Sector heatmap — count how many days each sector appears
        from collections import Counter as _Counter
        _sector_days: _Counter = _Counter()
        for _, row in _nk_df.iterrows():
            for _s in row["Watch Sectors"].split(" / "):
                _sector_days[_s] += 1

        st.markdown("**Sector appearance frequency (next 7 days)**")
        _hm_cols = st.columns(min(len(_sector_days), 6))
        for _ci, (_sec, _cnt) in enumerate(sorted(_sector_days.items(), key=lambda x: -x[1])):
            with _hm_cols[_ci % len(_hm_cols)]:
                _pct_bar = int(_cnt / 7 * 100)
                st.markdown(
                    f'<div style="background:rgba(74,222,128,{_cnt/7:.2f});'
                    f'border-radius:8px;padding:8px 12px;margin:2px 0;'
                    f'font-size:13px;font-weight:600;">'
                    f'{_sec}<br>'
                    f'<span style="font-size:11px;font-weight:400;">{_cnt}/7 days</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Jupiter Crash Signal ───────────────────────────────────────────────────
    st.subheader("Jupiter Crash Signal Monitor")
    st.caption(
        "Three-factor model: Jupiter in Ketu's nakshatra + Shashtashtak Yoga "
        "(6/8 axis) with malefics + Rahu-Ketu nodal influence. "
        "All 4 major Indian crashes (1992/2000/2008/2020) had all three active. "
        "No single factor alone predicts a crash."
    )

    _jp = ai.get_jupiter_position(analysis_date)

    if "error" in _jp:
        st.warning(f"Jupiter engine: {_jp['error']}")
    else:
        # ── Signal banner ──────────────────────────────────────────────────────
        _sig_colors = {
            "CRASH SIGNAL":  ("rgba(220,38,38,0.18)",  "#fca5a5", "🔴"),
            "ELEVATED RISK": ("rgba(234,88,12,0.18)",  "#fdba74", "🟠"),
            "WATCH":         ("rgba(234,179,8,0.15)",  "#fde047", "🟡"),
            "CLEAR":         ("rgba(74,222,128,0.12)", "#86efac", "🟢"),
        }
        _bg, _border_col, _icon = _sig_colors[_jp["signal"]]
        _factors_desc = []
        if _jp["is_ketu_nakshatra"]:
            _factors_desc.append(f"Jupiter in Ketu's nakshatra ({_jp['nakshatra']})")
        if _jp["shashtashtak_with"]:
            _factors_desc.append(f"Shashtashtak with {', '.join(_jp['shashtashtak_with'])}")
        if _jp["nodal_influence"]:
            _factors_desc.append(
                f"Rahu-Ketu nodal influence "
                f"(Rahu {_jp['rahu_arc']}° / Ketu {_jp['ketu_arc']}°)"
            )
        _factors_text = " · ".join(_factors_desc) if _factors_desc else "No active factors"

        st.markdown(
            f'<div style="background:{_bg};border:1px solid {_border_col};'
            f'border-radius:12px;padding:14px 18px;margin:8px 0;">'
            f'<span style="font-size:20px;">{_icon}</span> '
            f'<strong style="font-size:16px;">{_jp["signal"]}</strong> — '
            f'{_jp["factors_active"]}/3 factors active<br>'
            f'<span style="font-size:13px;opacity:0.85;">{_factors_text}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Jupiter position metrics ───────────────────────────────────────────
        jp_c1, jp_c2, jp_c3, jp_c4 = st.columns(4)
        with jp_c1:
            st.metric("Jupiter Sign", _jp["sign"].split("(")[0].strip(),
                      f"Sign #{_jp['sign_index']}")
        with jp_c2:
            _ketu_tag = " ⚠ Ketu's star" if _jp["is_ketu_nakshatra"] else ""
            st.metric("Jupiter Nakshatra", _jp["nakshatra"] + _ketu_tag,
                      f"Ruled by {_jp['nakshatra_planet']}")
        with jp_c3:
            _s6_8 = ", ".join(_jp["shashtashtak_with"]) if _jp["shashtashtak_with"] else "None"
            st.metric("Shashtashtak With", _s6_8, "6th/8th axis malefic")
        with jp_c4:
            st.metric("Jupiter Longitude", f"{_jp['sidereal_lon']}°",
                      "sidereal (Lahiri)")

        # ── Factor checklist ───────────────────────────────────────────────────
        _check = lambda ok: "✅" if ok else "⬜"
        st.markdown(
            f"**Crash signal factors:**  "
            f"{_check(_jp['is_ketu_nakshatra'])} Ketu nakshatra &nbsp;&nbsp;"
            f"{_check(_jp['shashtashtak_with'])} Shashtashtak w/ malefic &nbsp;&nbsp;"
            f"{_check(_jp['nodal_influence'])} Rahu-Ketu nodal influence"
        )

        # ── Historical context note ────────────────────────────────────────────
        with st.expander("Historical crash setups (reference)"):
            st.markdown(
                "| Year | Event | Jupiter Nakshatra | Key Combo | Outcome |\n"
                "|------|-------|-------------------|-----------|--------|\n"
                "| 1992 | Harshad Mehta crash | Magha (Ketu) | Shashtashtak Saturn+Sun; Rahu+Mars | Sensex −57%, 20m recovery |\n"
                "| 2000 | Dot-com bust | Ashwini (Ketu) | Conjunction Saturn; Rahu-Ketu axis | Nifty −53%, 34m recovery |\n"
                "| 2008 | Global financial crisis | Mula (Ketu) | Sun+Mars+Ketu aspect; 8th from Saturn | Nifty −64%, 71m recovery |\n"
                "| 2020 | Covid crash | Mula (Ketu) | Saturn+Sun+Mercury; eclipse; Ketu | Nifty −39%, fast recovery |\n"
                "| **Nov 2026** | **Prediction** | **Magha (Ketu)** | **Rahu-Ketu axis; 8th from Saturn** | **Major crash predicted** |\n"
                "\n"
                "*Exception rule:* Ketu nakshatra alone is NOT sufficient. "
                "1995 (+7%), 2003 (+20%), 2023 (+12%) were all bullish despite "
                "Jupiter in Ketu's star — because Shashtashtak and/or nodal influence was absent."
            )

    # ── India Degree-Matching Alerts ──────────────────────────────────────────
    st.subheader("India Chart — Degree-Matching Alerts (9:15 AM IST)")
    st.caption(
        "Transiting planets within ±2° of India's Independence Chart sensitive degrees "
        "(Aug 15, 1947). When a karaka planet hits these degrees it historically "
        "marks trend acceleration or reversal. Malefics (Saturn/Sun/Rahu/Mars) = bullish "
        "signal; Benefics (Jupiter/Moon/Mercury/Venus) = correction risk."
    )

    _orb_input = st.slider("Orb (degrees)", min_value=0.5, max_value=3.0,
                           value=2.0, step=0.5, key="india_orb")
    _alerts = ai.get_india_chart_alerts(analysis_date, orb=_orb_input)

    if _alerts and "error" in _alerts[0]:
        st.warning(f"India chart engine: {_alerts[0]['error']}")
    elif not _alerts:
        st.success(f"No planets within ±{_orb_input}° of any India chart sensitive degree today.")
    else:
        # Summary count strip
        _bull_alerts = [a for a in _alerts if a["bias"] == "bullish"]
        _bear_alerts = [a for a in _alerts if a["bias"] == "bearish"]
        _amb_alerts  = [a for a in _alerts if a["bias"] == "ambiguous"]

        ia_c1, ia_c2, ia_c3, ia_c4 = st.columns(4)
        with ia_c1:
            st.metric("Active Alerts", len(_alerts), f"within ±{_orb_input}°")
        with ia_c2:
            st.metric("Bullish Signals", len(_bull_alerts),
                      "Saturn/Sun/Rahu/Mars hitting India degrees")
        with ia_c3:
            st.metric("Bearish Signals", len(_bear_alerts),
                      "Jupiter/Moon/Mercury/Venus hitting India degrees")
        with ia_c4:
            st.metric("Ambiguous", len(_amb_alerts), "Ketu")

        # Net bias
        _net = len(_bull_alerts) - len(_bear_alerts)
        if _net > 0:
            _net_label = f"Net BULLISH (+{_net})"
            _net_color = "rgba(74,222,128,0.15)"
            _net_border = "#4ade80"
        elif _net < 0:
            _net_label = f"Net BEARISH ({_net})"
            _net_color = "rgba(220,38,38,0.15)"
            _net_border = "#f87171"
        else:
            _net_label = "Balanced (no edge)"
            _net_color = "rgba(234,179,8,0.12)"
            _net_border = "#fde047"

        st.markdown(
            f'<div style="background:{_net_color};border:1px solid {_net_border};'
            f'border-radius:8px;padding:10px 16px;margin:6px 0;">'
            f'<strong>{_net_label}</strong> — {len(_alerts)} degree matches active'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Alert cards
        _bias_icon = {"bullish": "🟢", "bearish": "🔴", "ambiguous": "🟡"}
        _bias_bg   = {
            "bullish":   "rgba(74,222,128,0.10)",
            "bearish":   "rgba(220,38,38,0.10)",
            "ambiguous": "rgba(234,179,8,0.10)",
        }
        _bias_border = {
            "bullish":   "rgba(74,222,128,0.4)",
            "bearish":   "rgba(220,38,38,0.4)",
            "ambiguous": "rgba(234,179,8,0.4)",
        }

        for _a in _alerts:
            _icon  = _bias_icon.get(_a["bias"], "⬜")
            _bg    = _bias_bg.get(_a["bias"], "transparent")
            _brd   = _bias_border.get(_a["bias"], "rgba(255,255,255,0.1)")
            _exact = " ✦ EXACT" if _a["exact"] else ""
            st.markdown(
                f'<div style="background:{_bg};border:1px solid {_brd};'
                f'border-radius:8px;padding:10px 16px;margin:4px 0;">'
                f'{_icon} <strong>{_a["planet"]}</strong> at '
                f'<strong>{_a["deg_in_sign"]:.1f}°</strong> {_a["sign"]} '
                f'→ matches India <strong>{_a["india_point"]} ({_a["india_deg"]}°)</strong> '
                f'<span style="opacity:0.7;">orb {_a["orb_actual"]}°{_exact}</span><br>'
                f'<span style="font-size:12px;opacity:0.75;">'
                f'Bias: {_a["bias"].upper()} &nbsp;|&nbsp; '
                f'Karaka: {_a["karaka"]}'
                f'</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # India chart degree reference (collapsed)
        with st.expander("India Independence Chart — sensitive degrees reference"):
            _ref_rows = [
                f"| {pt} | {deg}° | ±{_orb_input}° orb = {max(0,deg-_orb_input):.1f}°–{min(30,deg+_orb_input):.1f}° |"
                for pt, deg in ai.INDIA_CHART_DEGREES.items()
            ]
            st.markdown(
                "| Chart Point | Degree | Active Window |\n"
                "|-------------|--------|---------------|\n" +
                "\n".join(_ref_rows)
            )
            st.caption(
                "India Independence Chart: Aug 15, 1947, 12:00 AM, New Delhi. "
                "D1 = Rashi chart. D9 = Navamsa chart. "
                "Degree matching checks the transiting planet's position within its current "
                "sign (lon mod 30°) against these fixed reference degrees."
            )

    # ── Weekly Astro Infographic Card ─────────────────────────────────────────
    if _gen_card:
        try:
            from PIL import Image as _PILImage, ImageDraw as _PILDraw, ImageFont as _PILFont
        except ImportError:
            st.error("Pillow is not installed. Run `pip install Pillow` and restart the app.")
            _PILImage = None
        import io as _io
        import base64 as _b64
        import streamlit.components.v1 as _components
        if _PILImage is None:
            pass
        else:
            # ── palette ───────────────────────────────────────────────────────
            _C = {
                "bg":    (15,  10,  6),
                "panel": (28,  20,  16),
                "amber": (234, 88,  12),
                "green": (74,  222, 128),
                "red":   (239, 68,  68),
                "yellow":(253, 224, 71),
                "text":  (255, 245, 235),
                "muted": (168, 133, 106),
                "white": (255, 255, 255),
                "card_b":(38,  28,  20),
            }

            def _font(size, bold=False):
                try:
                    return _PILFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
                except OSError:
                    return _PILFont.load_default()

            W, H = 1080, 1350
            img = _PILImage.new("RGB", (W, H), _C["bg"])
            dr  = _PILDraw.Draw(img)

            def _rect(x0, y0, x1, y1, fill, r=12):
                dr.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill)

            def _txt(x, y, text, fnt, fill, anchor="la"):
                dr.text((x, y), str(text), font=fnt, fill=fill, anchor=anchor)

            # ── header ────────────────────────────────────────────────────────
            _rect(0, 0, W, 120, _C["amber"], r=0)
            _txt(40,      30, "Trading Bramha",          _font(38, True), _C["white"])
            _txt(40,      76, "ASTRO WEEKLY SNAPSHOT",   _font(18),       _C["white"])
            _txt(W - 40,  30, analysis_date.strftime("%d %b %Y"),
                 _font(28, True), _C["white"], anchor="ra")
            _txt(W - 40,  76, analysis_date.strftime("Week of %a %d %b"),
                 _font(16), _C["white"], anchor="ra")

            # ── running y cursor ───────────────────────────────────────────────
            _cy = [140]

            def _section_lbl(title):
                _txt(40, _cy[0], title.upper(), _font(13), _C["muted"])
                _cy[0] += 28

            def _open_panel(h):
                y0 = _cy[0]
                _rect(30, y0, W - 30, y0 + h, _C["panel"])
                return 30 + 20, y0 + 20

            def _close_panel(h):
                _cy[0] += h + 16

            # ── Moon Nakshatra ─────────────────────────────────────────────────
            _section_lbl("Moon Nakshatra Today")
            if "error" not in _nk_today:
                _ph = 160
                _px, _py = _open_panel(_ph)
                _txt(_px, _py,      _nk_today["nakshatra"],          _font(36, True), _C["text"])
                _txt(_px, _py + 44, f"Ruled by {_nk_today['planet']}  •  #{_nk_today['index']} of 27",
                     _font(18), _C["muted"])
                _txt(_px, _py + 72, "Sectors: " + " / ".join(_nk_today["sectors"]),
                     _font(16), _C["green"])
                _txt(_px, _py + 96, _nk_today["theme"][:70], _font(14), _C["muted"])
                _bw = W - 30 - 20 - _px
                _rect(_px, _py + 122, _px + _bw, _py + 132, _C["card_b"], r=4)
                _filled = max(4, int(_bw * _nk_today["pct"] / 100))
                _rect(_px, _py + 122, _px + _filled, _py + 132, _C["amber"], r=4)
                _txt(_px + _bw + 6, _py + 122, f"{_nk_today['pct']}%", _font(12), _C["muted"])
                _close_panel(_ph)
            else:
                _cy[0] += 60

            # ── Jupiter Crash Signal ───────────────────────────────────────────
            _section_lbl("Jupiter Crash Signal")
            if "error" not in _jp:
                _sig_col = {"CRASH SIGNAL": _C["red"], "ELEVATED RISK": _C["amber"],
                            "WATCH": _C["yellow"], "CLEAR": _C["green"]}.get(_jp["signal"], _C["muted"])
                _ph = 130
                _px, _py = _open_panel(_ph)
                _txt(_px, _py,      f"{_jp['signal']}  —  {_jp['factors_active']}/3 factors",
                     _font(30, True), _sig_col)
                _txt(_px, _py + 44, f"Jupiter in {_jp['nakshatra']} ({_jp['sign'].split('(')[0].strip()})",
                     _font(18), _C["text"])
                _active_parts = []
                if _jp["is_ketu_nakshatra"]:  _active_parts.append("Ketu nakshatra")
                if _jp["shashtashtak_with"]:  _active_parts.append(f"Shashtashtak w/ {', '.join(_jp['shashtashtak_with'])}")
                if _jp["nodal_influence"]:    _active_parts.append("Rahu-Ketu nodal")
                _txt(_px, _py + 70, "  ".join(_active_parts) or "No factors active",
                     _font(14), _C["muted"])
                _txt(_px, _py + 96, "Red flag: Nov 2026 full crash signal — mirrors 1992 & 2008",
                     _font(13), _C["red"])
                _close_panel(_ph)
            else:
                _cy[0] += 40

            # ── India Chart Alerts ─────────────────────────────────────────────
            _section_lbl("India Chart — Top Degree Alerts (9:15 AM IST)")
            _top_al = [a for a in _alerts if "error" not in a][:5]
            if _top_al:
                _bull_n = sum(1 for a in _top_al if a["bias"] == "bullish")
                _bear_n = sum(1 for a in _top_al if a["bias"] == "bearish")
                _net_t  = (f"Net BULLISH +{_bull_n - _bear_n}" if _bull_n > _bear_n else
                           f"Net BEARISH {_bull_n - _bear_n}"  if _bear_n > _bull_n else "Balanced")
                _net_c  = _C["green"] if _bull_n > _bear_n else _C["red"] if _bear_n > _bull_n else _C["yellow"]
                _ph = 36 + len(_top_al) * 24 + 20
                _px, _py = _open_panel(_ph)
                _txt(_px, _py, _net_t, _font(22, True), _net_c)
                for _i, _a in enumerate(_top_al):
                    _ac = (_C["green"] if _a["bias"] == "bullish"
                           else _C["red"] if _a["bias"] == "bearish" else _C["yellow"])
                    _line = (f"{_a['planet']:8s}  {_a['deg_in_sign']:4.1f}°  "
                             f"→ {_a['india_point']:12s} ({_a['india_deg']}°)  orb {_a['orb_actual']}°")
                    _txt(_px, _py + 36 + _i * 24, _line, _font(15), _ac)
                _close_panel(_ph)
            else:
                _cy[0] += 40

            # ── 7-Day Nakshatra Forecast ───────────────────────────────────────
            _section_lbl("7-Day Nakshatra Forecast")
            _nk_df_c = (_nk_df if not isinstance(_nk_df, list)
                        else pd.DataFrame(_nk_df))
            if not _nk_df_c.empty:
                _row_h = 38
                _col_ratios = [0.18, 0.28, 0.16, 0.38]
                _ph = 26 + len(_nk_df_c) * _row_h + 10
                _px, _py = _open_panel(_ph)
                _col_w = [(W - 30 - 20 - _px) * r for r in _col_ratios]
                _hdrs  = ["Date", "Nakshatra", "Planet", "Sectors"]
                _hx = _px
                for _h, _cw in zip(_hdrs, _col_w):
                    _txt(_hx, _py, _h, _font(13), _C["muted"])
                    _hx += _cw
                for _ri, (_, _row) in enumerate(_nk_df_c.iterrows()):
                    _ry = _py + 26 + _ri * _row_h
                    if _ri == 0:
                        _rect(_px - 8, _ry - 4, W - 30 - 20 + 8, _ry + _row_h - 6, (38, 55, 38), r=6)
                    _cx2 = _px
                    _cells = [_row.get("Date", ""), _row.get("Nakshatra", ""),
                              _row.get("Ruling Planet", ""), str(_row.get("Watch Sectors", ""))[:35]]
                    for _cell, _cw in zip(_cells, _col_w):
                        _txt(_cx2, _ry, str(_cell), _font(14, bold=(_ri == 0)),
                             _C["green"] if _ri == 0 else _C["text"])
                        _cx2 += _cw
                _close_panel(_ph)
            else:
                _cy[0] += 40

            # ── footer ────────────────────────────────────────────────────────
            _rect(0, H - 60, W, H, _C["panel"], r=0)
            _txt(W // 2, H - 38,
                 "Trading Bramha  •  Astro Timing Dashboard  •  For reference only",
                 _font(14), _C["muted"], anchor="mm")
            _txt(W // 2, H - 18, "Context, not signal. Always verify with price action.",
                 _font(12), _C["muted"], anchor="mm")

            # ── export ────────────────────────────────────────────────────────
            _buf = _io.BytesIO()
            img.save(_buf, format="PNG", optimize=True)
            _png_bytes = _buf.getvalue()
            _b64_str   = _b64.b64encode(_png_bytes).decode()

            st.image(img, caption="Weekly Astro Card — copy or download below",
                     use_container_width=False, width=540)

            st.download_button(
                label="⬇ Download PNG",
                data=_png_bytes,
                file_name=f"trading_bramha_astro_{analysis_date.strftime('%Y%m%d')}.png",
                mime="image/png",
                use_container_width=False,
            )

            _components.html(f"""
            <button onclick="copyCard()" style="
                background:#ea580c;color:#fff;border:none;border-radius:8px;
                padding:8px 20px;font-size:14px;font-weight:700;cursor:pointer;">
                \U0001f4cb Copy PNG to Clipboard
            </button>
            <span id="cs" style="margin-left:12px;font-size:13px;"></span>
            <script>
            async function copyCard() {{
                try {{
                    const res  = await fetch("data:image/png;base64,{_b64_str}");
                    const blob = await res.blob();
                    await navigator.clipboard.write([new ClipboardItem({{"image/png": blob}})]);
                    const s = document.getElementById("cs");
                    s.style.color = "#4ade80"; s.textContent = "Copied!";
                    setTimeout(() => s.textContent = "", 3000);
                }} catch(e) {{
                    const s = document.getElementById("cs");
                    s.style.color = "#ef4444";
                    s.textContent = "Copy failed — use Download (" + e.message + ")";
                }}
            }}
            </script>
            """, height=56)

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
            _paginated_df(df_signals, key="telegram_signals")

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
# Breakout Scans · Chartink source  (live Chartink fetch across entire market)
# ──────────────────────────────────────────────────────────────────────────────
import chartink_scraper as ck

# ──────────────────────────────────────────────────────────────────────────────
# Page — Breakout Scans (B-36r fold, 2026-08-27). Formerly two sibling nav pages
# — "Breakout Screener" (Chartink) and "TradingView Screener" — collapsed into one
# page with a source toggle. Same task (external new-high breakout feed), two
# providers, so the split was structural redundancy, not two distinct tools. The
# two bodies below are unchanged; they now guard on `bscan_src` instead of being
# separate top-level pages. Invariant: both feeds stay reachable, nothing lost.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Breakout Scans":
    st.subheader("Breakout Scans — external new-high feeds")
    st.caption(
        "Two login-light breakout feeds, same idea (a stock clearing a prior high) "
        "from different providers. Pick a source."
    )
    st.radio(
        "Source",
        ["Chartink", "TradingView"],
        horizontal=True,
        key="bscan_src",
        help="Chartink: 6M–10Y consolidation breakouts (needs a session cookie). "
             "TradingView: BrkoutGeek 1-month-high replica, no login.",
    )

if current_page == "Breakout Scans" and st.session_state.get("bscan_src", "Chartink") == "Chartink":
    st.markdown("**Chartink — 6M → 10Y consolidation breakouts**")
    st.caption(
        "Runs directly against **chartink.com** across the entire cash market. "
        "No stock list needed — Chartink scans every listed stock server-side. "
        "Paste your `_chartink_session` cookie once; it lasts for months."
    )

    # Colours come from rs.TOKENS, not literals. These were GitHub's dark-theme
    # palette (#58a6ff / #3fb950 / #d29922 / #f0883e / #f85149) sitting on a
    # cream dashboard — the same off-palette hard-coding backlog B-16 records for
    # OI Momentum. The RAMP is deliberate and is the point: lookback lengthens
    # 6M → 10Y, so the colour walks info → good → accent → risk, i.e. a longer
    # base is a rarer, heavier claim. Reading order, not decoration.
    _CK_SCANNERS = {
        "6M Consolidation Breakout": {"color": rs.TOKENS["info"],   "lookback": "6 months"},
        "1Y All-Time Breakout":      {"color": rs.TOKENS["good"],   "lookback": "1 year"},
        "3Y Breakout":               {"color": rs.TOKENS["accent"], "lookback": "3 years"},
        "5Y Breakout":               {"color": "#c2410c",           "lookback": "5 years"},
        "10Y Breakout":              {"color": rs.TOKENS["risk"],   "lookback": "10 years"},
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
                  style="background:{rs.TOKENS['accent']};color:#fff;border:none;
                         border-radius:8px;padding:6px 12px;cursor:pointer;
                         font-size:12px;font-weight:600;width:100%">
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
            color_r = _CK_SCANNERS.get(ran, {}).get("color", rs.TOKENS["info"])
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
# Breakout Scans · TradingView source (BrkoutGeek: Horz Break replica, public scan API)
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Breakout Scans" and st.session_state.get("bscan_src", "Chartink") == "TradingView":
    st.markdown("**TradingView — BrkoutGeek: Horz Break (replica)**")
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
                # The overview ribbon reads this through a 5-minute cache. Without
                # an explicit bust, refreshing here leaves the verdict above still
                # flagging a stale reading that no longer exists.
                cached_latest_sentiment.clear()
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

    # ── Filter A — market-health gate (DS-1) ──────────────────────────────────
    # The framework's five named conditions with its own 2-of-5 rule. Rendered
    # ABOVE the composite because it answers the prior question: the index score
    # says how the tape feels, this says whether you are allowed to trade at all.
    st.markdown(rs.section("Filter A — market health gate"), unsafe_allow_html=True)
    _mh_head_l, _mh_head_r = st.columns([3, 1])
    with _mh_head_r:
        if st.button("Run basket checks", key="mh_basket_run", use_container_width=True,
                     help=f"Fetches {MH_BASKET_SIZE} liquid names to measure "
                          f"'breakouts working' and 'leaders strong'. Takes ~30-60s; "
                          f"cached 30 min."):
            st.session_state["mh_basket_on"] = True

    _mh_frames = _mh_requested = None
    if st.session_state.get("mh_basket_on"):
        with st.spinner(f"Fetching {MH_BASKET_SIZE} names for the basket conditions…"):
            try:
                _mh_frames, _mh_requested = cached_health_basket(MH_BASKET_SIZE)
            except Exception as _e:
                st.warning(f"Basket fetch failed — the two stock-level conditions "
                           f"stay unmeasured. ({_e})")
    try:
        _mh_nifty, _mh_vix = cached_health_indices()
    except Exception:
        _mh_nifty = _mh_vix = None

    _gate = mh.evaluate(nifty_df=_mh_nifty, vix_df=_mh_vix,
                        sentiment_reading=reading, basket_frames=_mh_frames,
                        basket_requested=_mh_requested, fetch_indices=False)

    _lamp = {mh.PASS: rs.TOKENS["good"], mh.FAIL: rs.TOKENS["risk"],
             mh.NOT_CHECKED: rs.TOKENS["absent"]}
    for _col, _c in zip(st.columns(5), _gate["conditions"]):
        with _col:
            st.markdown(
                rs.card(
                    f'<div style="display:flex;align-items:center;gap:7px;">'
                    f'<span style="width:9px;height:9px;border-radius:50%;flex-shrink:0;'
                    f'background:{_lamp[_c["state"]]};"></span>'
                    f'<b style="font-size:11.5px;line-height:1.25;">{_c["label"]}</b></div>'
                    f'<div style="font-size:10px;color:{rs.TOKENS["text_body"]};'
                    f'margin-top:6px;line-height:1.45;">{_c["reading"]}</div>'
                ),
                unsafe_allow_html=True)

    _gate_tone = ("risk" if _gate["verdict"] == "STAND DOWN" else
                  "absent" if _gate["verdict"] == "NOT ASSESSED" else
                  "warn" if (_gate["n_fail"] or _gate["n_unchecked"]) else "good")
    st.markdown(
        rs.callout(f'{_gate["verdict"]} — {_gate["n_fail"]} of '
                   f'{_gate["n_checked"]} checked failed'
                   + (f', {_gate["n_unchecked"]} not checked.'
                      if _gate["n_unchecked"] else '.'),
                   _gate["instruction"], tone=_gate_tone),
        unsafe_allow_html=True)
    st.caption(
        f"Filter A of the **Crash-Proof 3-Filter System** — *{_gate['rule']}*. "
        "This is a **second opinion beside** the verdict in the header ribbon, not "
        "folded into it: breadth and regime feed both, so adding these failures to "
        "that caution count would penalise the same weakness twice. Note the two "
        "read different levels — this gate uses the **50 EMA** the framework "
        "specifies, the ribbon uses the 200 SMA. Unmeasured conditions never count "
        "as passes. None of these thresholds are backtested.")
    st.divider()

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

    # ── NSE Index Futures Basis ───────────────────────────────────────────
    # Basis = (near-month futures close − spot) / spot × 100.  Positive basis
    # (contango) = cost-of-carry; a sustained negative basis (backwardation)
    # signals hedging pressure or bearish positioning.
    # Data source: NSE F&O EOD bhavcopy (same file used by OI Momentum).
    # UndrlygPric in the IDF rows IS the spot close — no second yfinance fetch.
    st.divider()
    st.markdown("### NSE Index Futures Basis")
    st.caption(
        "Near-month futures close vs spot (UndrlygPric from NSE EOD bhavcopy). "
        "Positive = contango (cost-of-carry expected); negative = backwardation "
        "(hedging pressure or bearish bias). OI is summed across all expiries."
    )
    try:
        _idf_raw, _idf_date = oim.fetch_fo_bhavcopy_raw()
        if _idf_raw.empty or _idf_date is None:
            st.info("Index futures basis: no recent bhavcopy available.")
        else:
            _idf = _idf_raw[_idf_raw["FinInstrmTp"] == "IDF"].copy()
            if _idf.empty:
                st.info("No index futures rows in this session's bhavcopy.")
            else:
                _idf["XpryDt"] = pd.to_datetime(_idf["XpryDt"], errors="coerce")
                _idf = _idf.dropna(subset=["XpryDt"])
                # Near-month contract = earliest expiry per symbol
                _near = (
                    _idf.sort_values("XpryDt")
                    .groupby("TckrSytm", as_index=False)
                    .first()
                )
                # OI sum across all expiries
                _oi_total = (
                    _idf.groupby("TckrSytm", as_index=False)
                    .agg(oi_total=("OpnIntrst", "sum"),
                         oi_chg_total=("ChngInOpnIntrst", "sum"))
                )
                _basis_df = _near.merge(_oi_total, on="TckrSytm", how="left")
                _basis_df["basis_pct"] = (
                    (_basis_df["ClsPric"] - _basis_df["UndrlygPric"])
                    / _basis_df["UndrlygPric"].replace(0, float("nan")) * 100
                )
                _basis_display = pd.DataFrame({
                    "Index":      _basis_df["TckrSytm"],
                    "Spot":       _basis_df["UndrlygPric"].round(2),
                    "Futures":    _basis_df["ClsPric"].round(2),
                    "Basis %":    _basis_df["basis_pct"].round(3),
                    "Expiry":     _basis_df["XpryDt"].dt.strftime("%d-%b-%Y"),
                    "OI (total)": _basis_df["oi_total"].astype(int),
                    "OI Chg":     _basis_df["oi_chg_total"].astype(int),
                }).sort_values("OI (total)", ascending=False).reset_index(drop=True)
                st.dataframe(
                    _basis_display,
                    hide_index=True, use_container_width=True,
                    column_config={
                        "Basis %": st.column_config.NumberColumn("Basis %", format="%.3f%%"),
                    },
                )
                st.caption(f"Bhavcopy date: {_idf_date.strftime('%d-%b-%Y')}")
    except Exception as _basis_exc:
        st.warning(f"Index futures basis unavailable: {_basis_exc}")

    # ──────────────────────────────────────────────────────────────────────
    # Morning Market Brief — global quote strip + constituent breadth + the
    # full panchang for the day. Modelled on a published "morning brief" card.
    #
    # Two deliberate departures from that card's format:
    #  * Breadth is computed from Nifty 500 CONSTITUENTS, not sector indices.
    #    Yahoo froze 8 of 11 NSE sector index feeds on 2026-07-17 and they
    #    return stale bars rather than erroring, so an index-based count is a
    #    confident number built on three survivors.
    #  * The astro block states almanac facts ONLY — no bias, no "avoid fresh
    #    buying". Rahu Kaal being inauspicious is a traditional assertion with
    #    no measured backing here; FA-2 has never been run. Printing a
    #    directional call next to a clock time is the one thing this page must
    #    not do.
    # ──────────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Morning Market Brief")
    st.caption(
        "Global cues, constituent-based sector breadth, and the day's panchang. "
        "Astro entries are almanac facts — none of them is measured against "
        "market outcomes in this repo."
    )

    mb_col1, mb_col2 = st.columns([1, 3])
    with mb_col1:
        brief_go = st.button("Build brief", type="primary", key="brief_go")
    with mb_col2:
        want_breadth = st.checkbox(
            "Include sector breadth (500 constituents, ~6s)",
            value=True, key="brief_breadth",
        )

    if brief_go:
        import market_brief as mbrief
        with st.spinner("Fetching global cues, breadth and panchang…"):
            try:
                st.session_state["brief_model"] = mbrief.build_brief(
                    include_breadth=want_breadth,
                    sentiment=reading,          # reuse THIS page's reading
                )
            except Exception as exc:
                st.error(f"Brief build failed: {type(exc).__name__}: {exc}")

    model = st.session_state.get("brief_model")
    if model:
        import market_brief as mbrief
        pan = model.get("panchang")

        tone_tone = {"WEAK": "🔴", "CAUTIOUS": "🟠",
                     "STRONG": "🟢"}.get(model["tone"], "⚪")
        st.markdown(
            f"#### {tone_tone} {model['tone']} — "
            f"{model['as_of'].strftime('%d %B %Y, %A')} · "
            f"snapshot {model['as_of'].strftime('%H:%M')} IST"
        )
        qmeta = model["quotes_meta"]
        if qmeta["error"]:
            st.warning(f"Quote fetch problem: {qmeta['error']}")
        if qmeta["missing"] or qmeta["stale"]:
            st.warning(
                f"{qmeta['missing']} quote(s) missing, {qmeta['stale']} stale "
                "(shown struck through). A stale feed returns an old bar rather "
                "than erroring — it is excluded from the tone, not averaged in."
            )

        # ── Quote strip, grouped as the source card groups them ──
        for group in ("india", "asia", "us", "us_futures", "commodity", "fx"):
            rows = [q for q in model["quotes"] if q["group"] == group]
            if not rows:
                continue
            st.markdown(f"**{mbrief.GROUP_LABELS[group]}**")
            cols = st.columns(len(rows))
            for col, q in zip(cols, rows):
                with col:
                    if q["missing"]:
                        st.metric(q["label"], "—", help="no data returned")
                    elif q["stale"]:
                        st.metric(f"~~{q['label']}~~", f"{q['last']:,.2f}",
                                  delta=f"{q['change_pct']:+.2f}% (stale)",
                                  delta_color="off",
                                  help=f"last bar {q['bar_age_days']}d old — "
                                       f"excluded from the tone")
                    else:
                        st.metric(q["label"], f"{q['last']:,.2f}",
                                  delta=f"{q['change_pct']:+.2f}%")

        # ── Breadth ──
        br = model["breadth"]
        if br.get("error"):
            st.warning(f"Breadth unavailable: {br['error']}")
        elif br.get("total"):
            cov = br["coverage"]
            b1, b2 = st.columns([1, 3])
            with b1:
                st.metric("Sectors red", f"{br['red']} / {br['total']}",
                          delta=f"{br['green']} green", delta_color="off")
            with b2:
                st.caption(
                    f"From **{cov['scored']} of {cov['universe_size']}** "
                    f"{br['universe']} constituents grouped by NSE macro-sector. "
                    f"A sector is red when its **median** constituent is down — "
                    f"median, so one collapsing name cannot paint a sector. "
                    f"Excluded: {cov['stale_excluded']} stale, {cov['missing']} "
                    f"missing."
                    + (f" Thin (<5 scored, not counted): "
                       f"{', '.join(cov['thin_sectors'])}."
                       if cov.get("thin_sectors") else "")
                )
            st.dataframe(
                pd.DataFrame([{
                    "Sector": s["sector"],
                    "Median %": round(s["median_change_pct"], 2),
                    "Mean %": round(s["mean_change_pct"], 2),
                    "Constituents": s["constituents"],
                    "% Green": round(s["pct_green"], 0),
                } for s in br["sectors"]]),
                hide_index=True, use_container_width=True,
            )

    # ── Panchang: the almanac block. Optional — the market half above renders
    # without it, because `ephem` is not installed in every interpreter that can
    # run this app and an optional dependency must not erase the whole card.
    if model and not pan:
        st.warning(
            f"Astro block unavailable — {model.get('panchang_error') or 'unknown reason'}",
            icon="🌘")

    if model and pan:
        st.markdown("#### Panchang — {} · {}".format(
            pan["place"], pan["date"].strftime("%d %b %Y")))
        st.caption(
            "Computed locally from `ephem` (no vendor, no API). Verified against "
            "a published card to the minute — run `python tools/panchang.py`. "
            "**Facts only: no window here carries a measured market effect.**"
        )

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Sunrise", pan["sunrise"].strftime("%H:%M"))
        p2.metric("Sunset", pan["sunset"].strftime("%H:%M"))
        p3.metric("Weekday lord", pan["day_lord"])
        tt = pan["tithi"]
        p4.metric("Tithi", f"{tt['paksha']} {tt['name']}",
                  delta=f"{tt['pct_complete']:.0f}% elapsed", delta_color="off")

        nk = pan["nakshatra"]
        n1, n2, n3 = st.columns(3)
        n1.metric("Nakshatra", nk["nakshatra"],
                  delta=f"pada {nk['pada']}", delta_color="off")
        n2.metric("Nakshatra lord", nk["lord"])
        n3.metric("Sub-lord (KP)", nk["sub_lord"])
        st.caption(
            f"Moon at {nk['longitude']:.2f}° sidereal "
            f"({nk['pct_through_nakshatra']:.0f}% through {nk['nakshatra']}, "
            f"ayanamsa {nk['ayanamsa']:.2f}°). "
            + (f"Pada {nk['pada']} ends {nk['pada_ends'].strftime('%H:%M')}; "
               if nk["pada_ends"] else "")
            + (f"{nk['nakshatra']} ends "
               f"{nk['nakshatra_ends'].strftime('%H:%M on %d %b')}."
               if nk["nakshatra_ends"] else "")
        )

        cur, nxt = pan["hora_current"], pan["hora_next"]
        h1, h2, h3 = st.columns(3)
        h1.metric("Current hora", cur["lord"] if cur else "—",
                  delta=(f"{cur['start'].strftime('%H:%M')}–"
                         f"{cur['end'].strftime('%H:%M')}" if cur else "outside day"),
                  delta_color="off")
        h2.metric("Next hora", nxt["lord"] if nxt else "—",
                  delta=(f"from {nxt['start'].strftime('%H:%M')}" if nxt else ""),
                  delta_color="off")
        lp = pan["lunar_phase"]
        h3.metric("Moon phase", (lp or {}).get("phase", "unknown").title(),
                  delta=(f"{lp['illumination']:.0f}% lit" if lp else "no data"),
                  delta_color="off")

        w1, w2, w3 = st.columns(3)
        for col, key, label in ((w1, "rahu_kaal", "Rahu Kaal"),
                                (w2, "yamaganda", "Yamaganda"),
                                (w3, "gulika", "Gulika")):
            w = pan[key]
            col.metric(label,
                       f"{w['start'].strftime('%H:%M')}–{w['end'].strftime('%H:%M')}",
                       delta=f"part {w['part']} of 8", delta_color="off")
        st.caption(
            "These three are the classical inauspicious windows — equal 1/8 "
            "divisions of sunrise→sunset, assigned by weekday. **This repo has "
            "never measured whether NIFTY behaves differently inside them** "
            "(roadmap FA-2). Shown because they are computable and exact, not "
            "because they are known to matter."
        )

        retro = [k for k, v in pan["retrogrades"].items() if v]
        st.markdown(
            f"**Retrograde now:** {', '.join(retro) if retro else 'none'}  ·  "
            f"**Hora sequence** below runs sunrise→next sunrise."
        )
        with st.expander("Full 24-block hora sequence"):
            st.dataframe(
                pd.DataFrame([{
                    "#": h["index"], "Lord": h["lord"],
                    "Start": h["start"].strftime("%H:%M"),
                    "End": h["end"].strftime("%H:%M"),
                    "Phase": h["phase"],
                    "Now": "◀" if cur and h["index"] == cur["index"] else "",
                } for h in pan["hora_sequence"]]),
                hide_index=True, use_container_width=True, height=320,
            )

    # Disclaimer belongs to the whole card, so it sits outside the astro block —
    # it must still show when the panchang half is unavailable.
    if model:
        st.info(model["disclaimer"], icon="⚠️")


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

    # ── Deal Intelligence (CEAVET) ────────────────────────────────────────────
    # The tables below are complete and say nothing at a glance: 190 deal rows
    # do not tell you which company an institution actually accumulated. This
    # aggregates per company above a value floor and answers it in six parts.
    # Rendered above the tabs because it is the summary the tables are evidence
    # for. All rules live in block_deal_intel.py — nothing here is a model.
    st.markdown("### Deal Intelligence — CEAVET summary")
    di_c1, di_c2 = st.columns([1, 3])
    with di_c1:
        di_min_lakh = st.number_input(
            "Min deal value per company (₹ lakh)", min_value=50.0, max_value=100000.0,
            value=500.0, step=50.0, key="imi_ceavet_min",
            help="Aggregate buy+sell value across all of a company's deals today.",
        )
    di_run = st.button("Analyze deals", key="imi_ceavet_run")

    if di_run:
        with st.spinner("Aggregating deals and checking price context…"):
            try:
                _n_bulk  = imi.fetch_nse_bulk_deals()
                _n_block = imi.fetch_nse_block_deals()
                _b_bulk  = imi.fetch_bse_bulk_deals()
                _b_block = imi.fetch_bse_block_deals()
                _deals = bdi.normalize_deals(_n_bulk, _n_block, _b_bulk, _b_block)

                def _deal_price_ctx(sym: str):
                    """CMP / volume / post-deal return for one scrip.

                    Only NSE-listed tickers resolve through the yfinance-backed
                    fetcher, so BSE-only scrips legitimately return None and the
                    Evaluate section reports the gap instead of inventing one.
                    """
                    try:
                        pdf = cached_fetch_ohlcv(sym, days=90)
                    except Exception:
                        return None
                    if pdf is None or pdf.empty or "close" not in pdf.columns:
                        return None
                    ctx = {"cmp": float(pdf["close"].iloc[-1])}
                    if "volume" in pdf.columns and len(pdf) >= 21:
                        avg20 = float(pdf["volume"].iloc[-21:-1].mean())
                        if avg20:
                            ctx["vol_ratio"] = float(pdf["volume"].iloc[-1]) / avg20
                    # Post-deal action, only when the deal actually predates the
                    # latest bar — same-day deals have nothing to evaluate yet.
                    try:
                        sym_dates = pd.to_datetime(
                            _deals.loc[_deals["symbol"] == sym, "date"],
                            dayfirst=True, errors="coerce").dropna()
                        if len(sym_dates):
                            deal_day = sym_dates.max().normalize()
                            idx = pd.to_datetime(pdf.index).normalize()
                            prior = pdf[idx <= deal_day]
                            if len(prior) and idx.max() > deal_day:
                                base = float(prior["close"].iloc[-1])
                                if base:
                                    ctx["ret_since_pct"] = (ctx["cmp"] - base) / base * 100.0
                                    ctx["bars_since"] = int((idx > deal_day).sum())
                    except Exception:
                        pass
                    return ctx

                st.session_state["imi_ceavet"] = bdi.summarize_all(
                    _deals, min_value=di_min_lakh * 1e5, price_ctx_fn=_deal_price_ctx)
            except Exception as e:
                st.error(f"Deal analysis failed: {e}")

    _ceavet = st.session_state.get("imi_ceavet")
    if _ceavet is not None:
        if not _ceavet:
            st.info(f"No company had aggregate deal value above ₹{di_min_lakh:.0f} lakh.")
        else:
            # Semantic tones, not hexes — these were the last off-palette colours
            # on this page (#2e7d32 / #1565c0 / #b8860b …), so a HIGH badge sat
            # next to token-green text in a different green. report_style owns
            # what a verdict looks like; this only says which verdict it is.
            _strength_tone = {
                "HIGH": "good", "INFORMATIVE": "info", "MODERATE": "warn",
                "BEARISH": "risk", "WEAK": "neutral", "LOW": "neutral",
                "NOISE": "absent",
            }
            # Lead with the count that matters: how many of these are actually
            # worth a look versus how many are churn wearing a big number.
            _actionable = [r for r in _ceavet
                           if r["strength"] in bdi.ACTIONABLE_STRENGTHS]
            st.caption(
                f"{len(_ceavet)} company(ies) above ₹{di_min_lakh:.0f}L · "
                f"**{len(_actionable)}** carry an ownership signal · "
                f"{len(_ceavet) - len(_actionable)} are self-crossing or intermediary churn. "
                f"Ordered by signal strength, so churn sinks below real signal "
                f"regardless of headline size."
            )

            def _deal_chart_url(rec) -> str:
                # Deals arrive under the exchange's own ticker, so route each
                # scrip to the venue it actually traded on — a BSE scrip name
                # will not resolve as an NSE symbol.
                exch = rec["venues"][0] if rec.get("venues") else "NSE"
                return (f"http://localhost:5001/?symbol={rec['symbol']}"
                        f"&exchange={exch}&tf=1d")

            # The Stock Analyzer resolves NSE symbols only, so the deep-link is
            # offered for scrips that actually traded on NSE and withheld for
            # BSE-only names — the same reason `_deal_chart_url` routes by venue.
            # A link that opens an analyzer with nothing to analyse is worse than
            # no link.
            def _deal_analyze_url(rec) -> str | None:
                return (_analyze_url(rec["symbol"])
                        if "NSE" in (rec.get("venues") or []) else None)

            _tbl = pd.DataFrame([{
                "Scrip":       r["symbol"],
                "Value (₹L)":  round(r["total_value"] / 1e5, 1),
                "Signal":      r["strength"],
                "Action":      r["action"],
                "Venue":       "/".join(r["venues"]),
                "Chart":       _deal_chart_url(r),
                "Analyze":     _deal_analyze_url(r),
            } for r in _ceavet])
            st.dataframe(
                _tbl, use_container_width=True, hide_index=True,
                column_config={
                    "Chart": st.column_config.LinkColumn(
                        "Chart", help="Open in Chart Tool",
                        display_text="📈 Open", width="small",
                    ),
                    "Analyze": _analyze_colcfg(),
                },
            )
            for r in _ceavet:
                _tone = _strength_tone.get(r["strength"], "absent")
                head = (f"{r['symbol']} — ₹{r['total_value']/1e5:,.0f}L · "
                        f"{r['strength']} · {r['action']}")
                with st.expander(head, expanded=(r is _ceavet[0])):
                    _badge_col, _wl_col = st.columns([4, 1])
                    with _badge_col:
                        _links = (f"<a href='{_deal_chart_url(r)}' target='_blank' "
                                  f"style='font-size:12px;color:{rs.TOKENS['info']};'>"
                                  f"📈 Open chart</a>")
                        _an = _deal_analyze_url(r)
                        if _an:
                            _links += (f"&nbsp;&nbsp;<a href='{_an}' target='_blank' "
                                       f"style='font-size:12px;color:{rs.TOKENS['info']};'>"
                                       f"🔬 Analyze ↗</a>")
                        st.markdown(
                            rs.chip(f"{r['strength']} — {r['action']}", tone=_tone)
                            + f"&nbsp;&nbsp;{_links}",
                            unsafe_allow_html=True)
                    with _wl_col:
                        # Watchlist add can't ride an HTML <a> — it needs a Python
                        # call, so it's a compact button beside the chart link.
                        if st.button("★ Watchlist", key=f"imi_ceavet_wl_{r['symbol']}",
                                     help="Add this scrip to your watchlist"):
                            db.add_watchlist_symbol(
                                r["symbol"], f"From Deal Intel — {r['strength']}")
                            st.success(f"{r['symbol']} added to watchlist.")
                    for letter, label, key in [
                        ("C", "Context", "C"), ("E", "Event", "E"),
                        ("A", "Analysis — institutional motive", "A"),
                        ("V", "Value — actionable clues", "V"),
                        ("E", "Evaluate — confirmation", "E2"),
                        ("T", "Takeaway", "T"),
                    ]:
                        st.markdown(f"**{letter} · {label}** — {r['ceavet'][key]}")
            # The caveat is the last thing read and the easiest to skim past, so
            # it gets the accent rail rather than st.caption's grey — it is a
            # standing limitation of the data, not a footnote about it.
            st.markdown(
                rs.callout(
                    "Rule-based, not advice.",
                    "This classifies public deal disclosures by rule; the takeaway "
                    "grades the strength of the <b>signal</b>, and the position "
                    "decision remains yours. Deal feeds expose no history endpoint, "
                    "so this reflects <b>today's disclosures only</b> — absence "
                    "here is not evidence that nothing happened.",
                    tone="warn"),
                unsafe_allow_html=True)
    st.divider()

    intel_tabs = st.tabs(["Bulk Deals", "Block Deals", "Insider Trading",
                          "Gap & Volume Scanner", "📰 Deal Board"])

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
        _paginated_df(df_deals.style.apply(_row_color, axis=1), key="deals_main",
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
            _paginated_df(styled, key="insider_main", column_config=ins_col_config)

    with intel_tabs[3]:
        st.caption(
            "Gap-up/gap-down and unusual-volume scan over the bhavcopy universe (reuses the same "
            "Full-Market source as Scanner Hub)."
        )
        gv_col1, gv_col2, gv_col3 = st.columns(3)
        gv_top_n = gv_col1.slider("Universe size (top N by traded value)", 50, 5000, 500, step=50, key="imi_gv_topn")
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

    # ── Deal Board — the shareable infographic ────────────────────────────────
    # The four tabs above are working tables; this is the one artefact you send
    # someone. All assembly lives in deal_infographic.py — this only runs it and
    # hands back the HTML, so the board is identical from the CLI and the page.
    with intel_tabs[4]:
        st.caption(
            "One board for the session: every scrip that had a bulk or block deal, "
            "ranked by market cap, with what the price did, how much of the day's "
            "tape the deal was, and how much of that quantity was actually "
            "**delivered**. A disclosure that someone traded — not evidence they "
            "were right, and not a recommendation."
        )
        _db_c1, _db_c2 = st.columns([1, 2])
        with _db_c1:
            _db_mcap = st.checkbox("Look up market caps", value=True, key="imi_db_mcap",
                                   help="One yfinance call per scrip (~10s for a "
                                        "typical day). Off = the tables still build, "
                                        "sorted by delivery value instead.")
        with _db_c2:
            _db_run = st.button("📰 Build deal board", type="primary", key="imi_db_run")

        if _db_run:
            with st.spinner("Fetching deals, delivery file and market caps…"):
                try:
                    _db_deals = dinf.collect_deals()
                    st.session_state["imi_deal_board"] = dinf.build(
                        _db_deals, with_mcap=_db_mcap)
                    # A new board makes any previously rendered image stale.
                    st.session_state.pop("imi_deal_board_png", None)
                except Exception as e:
                    st.error(f"Deal board failed: {e}")
                    st.session_state.pop("imi_deal_board", None)

        _board = st.session_state.get("imi_deal_board")
        if _board is not None:
            if _board.get("error"):
                st.warning(_board["error"])
            else:
                _html = dinf.render_html(_board)
                # Height scales with the row count: a fixed iframe either clips a
                # 70-scrip day or leaves a void on a 5-scrip one.
                _rows = _board.get("n_symbols", 0)
                components.html(_html, height=min(4200, 620 + 26 * _rows),
                                scrolling=True)
                _stem = f"deal_board_{date.today():%Y%m%d}"
                _dl1, _dl2, _dl3 = st.columns([1, 1, 2])
                with _dl1:
                    st.download_button(
                        "⬇ HTML", data=_html, file_name=f"{_stem}.html",
                        mime="text/html", key="imi_db_dl", use_container_width=True)
                # PNG is rendered on demand, not with every board: it launches
                # headless Chromium (~2-4s). Rendering it here rather than in the
                # browser means the image is produced by the SAME engine that
                # displays the board — a canvas library re-implements CSS and
                # would ship a subtly different picture.
                with _dl2:
                    if st.button("🖼 Render image", key="imi_db_png",
                                 use_container_width=True):
                        with st.spinner("Rendering PNG…"):
                            try:
                                st.session_state["imi_deal_board_png"] =                                     dinf.render_png(_html)
                            except RuntimeError as e:
                                st.session_state.pop("imi_deal_board_png", None)
                                st.error(str(e))
                _png = st.session_state.get("imi_deal_board_png")
                with _dl3:
                    if _png:
                        st.download_button(
                            f"⬇ Download image (PNG · {len(_png) / 1e6:.1f} MB)",
                            data=_png, file_name=f"{_stem}.png", mime="image/png",
                            key="imi_db_dlpng", type="primary",
                            use_container_width=True)
                st.caption(
                    f"{_board.get('n_deals', 0)} deal rows · {_board.get('n_symbols', 0)} "
                    f"scrips ({_board.get('n_index', 0)} index / "
                    f"{_board.get('n_other', 0)} beyond) · session "
                    f"{_board.get('session') or '—'}. Delivery % is NSE's own "
                    f"published DELIV_PER, not a derived figure — boards elsewhere "
                    f"that print a different number are computing something else."
                )
        else:
            st.info("Not built yet — press **Build deal board**.")



# ──────────────────────────────────────────────────────────────────────────────
# Page — OI Momentum (price change vs open-interest change, stock futures)
# The reading NSE's own "Change in Open Interest" page is built around, taken
# from the F&O bhavcopy instead: same fields, no Akamai block, and the
# stock-vs-index filter is mechanical rather than done by eye. All rules live in
# nse_oi_momentum.py — nothing here is a model.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "OI Momentum":

    def _oi_chart_url(sym: str) -> str:
        """Chart-tool link for an F&O underlying.

        Every name here is an NSE F&O underlying, so the .NS suffix always
        resolves and no exchange branch is needed (unlike the deal tables, which
        carry BSE scrips). The symbol is percent-encoded because NSE tickers
        legitimately contain "&" — M&M and GVT&D both trade in F&O, and raw they
        would truncate the query parameter and open the wrong chart.
        """
        return f"http://localhost:5001/?symbol={quote(f'{sym}.NS', safe='')}&tf=1d"

    st.subheader("OI Momentum — is the move built, or just vacated?")
    st.caption(
        "Price change paired with **open-interest change** across the stock-futures "
        "universe. Price alone says where a contract traded; OI says how much "
        "conviction is still sitting behind it. Rising OI means fresh positions are "
        "backing the move; falling OI means it is running on exits. "
        "**End-of-day only** — the F&O bhavcopy is a settled file, so this is last "
        "session's positioning, not a live feed. Observation tool, not a "
        "buy/sell recommendation."
    )

    _oi_recs, _oi_date = cached_oi_momentum_scan()

    if not _oi_recs:
        st.warning(
            "No F&O bhavcopy was reachable in the last 7 calendar days. Holidays and "
            "long weekends make this normal; NSE archives can also lag late in the "
            "evening on a settlement day."
        )
    else:
        _dte = _oi_recs[0]["days_to_expiry"]
        st.caption(
            f"Session **{_oi_date:%d %b %Y}** · {len(_oi_recs)} of ~210 stock futures "
            f"cleared the materiality floors "
            f"(|price| ≥ {oim.MIN_PRICE_PCT}%, |OI| ≥ {oim.MIN_OI_PCT}%) · "
            f"{_dte} session(s) to near-month expiry."
        )
        if _dte <= oim.EXPIRY_NOISE_DAYS:
            st.warning(
                f"Expiry is {_dte} session(s) away. OI drains out of the front "
                f"contract into the next one regardless of what anyone thinks of the "
                f"stock, so every reading below is graded UNRELIABLE this week."
            )

        # ── Breadth ───────────────────────────────────────────────────────────
        # A universe-wide tilt is worth more than any single name and costs
        # nothing to read, so it goes above the table.
        _b = oim.breadth(_oi_recs)
        _bull_built = _b[oim.LONG_BUILDUP]
        _bear_built = _b[oim.SHORT_BUILDUP]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Long build-up", _bull_built, help="Price up + OI up — supported")
        m2.metric("Short covering", _b[oim.SHORT_COVERING],
                  help="Price up + OI down — running on exits")
        m3.metric("Short build-up", _bear_built, help="Price down + OI up — supported")
        m4.metric("Long unwinding", _b[oim.LONG_UNWINDING],
                  help="Price down + OI down — holders leaving")
        if _bull_built or _bear_built:
            _tilt = ("bullish" if _bull_built > _bear_built else
                     "bearish" if _bear_built > _bull_built else "evenly split")
            st.caption(
                f"Fresh positioning is **{_tilt}**: {_bull_built} names had longs "
                f"built into them versus {_bear_built} that had shorts built into "
                f"them. Covering and unwinding are excluded from that count on "
                f"purpose — they are positions leaving, not conviction arriving."
            )

        # ── Filters ───────────────────────────────────────────────────────────
        fc1, fc2 = st.columns([2, 1])
        with fc1:
            _readings = st.multiselect(
                "Readings", [oim.LONG_BUILDUP, oim.SHORT_COVERING,
                             oim.SHORT_BUILDUP, oim.LONG_UNWINDING],
                default=[oim.LONG_BUILDUP, oim.SHORT_COVERING],
                key="oim_readings",
                help="Defaults to the two up-move cases: build-up versus covering.",
            )
        with fc2:
            _supported_only = st.checkbox(
                "Supported moves only", value=False, key="oim_supported",
                help="Keep only names where OI ROSE — fresh positions backing the "
                     "move — and drop covering/unwinding entirely.",
            )

        _view = [r for r in _oi_recs if r["reading"] in _readings]
        if _supported_only:
            _view = [r for r in _view if r["supported"]]

        if not _view:
            st.info("No names match the current filters.")
        else:
            _strength_color = {
                "STRONG": rs.TOKENS["good"], "MODERATE": rs.TOKENS["info"],
                "UNSUPPORTED": rs.TOKENS["accent"], "UNRELIABLE": rs.TOKENS["absent"],
            }
            _actionable = [r for r in _view
                           if r["strength"] in oim.ACTIONABLE_STRENGTHS]
            st.caption(
                f"{len(_view)} name(s) shown · **{len(_actionable)}** are supported "
                f"by fresh positioning · ordered by signal strength, so a large "
                f"unsupported move sinks below a smaller built one."
            )

            # ── Options-side positioning, as a SEPARATE column ────────────────
            # PCR sits beside the verdict, never inside it. The quadrant is a
            # futures-OI statement; PCR is an options-OI one, and merging them
            # would produce a label that can no longer be traced back to either.
            # It is also directionally ambiguous (a high PCR reads bullish to a
            # trend-follower and crowded to a contrarian), so letting it move the
            # verdict would import that ambiguity into the one number here that
            # currently has none.
            # ── Level context, on demand ──────────────────────────────────────
            # Behind a button because it is the only thing on this page costing a
            # fetch PER SYMBOL — every other column rides the bhavcopy already
            # downloaded. Results are held per scan date, so filter changes and
            # reruns are free once it has been run.
            _lvl_key = f"oim_levels_{_oi_date}"
            _levels = st.session_state.get(_lvl_key, {})
            _lc1, _lc2 = st.columns([1, 3])
            with _lc1:
                if st.button(f"📐 Check levels ({len(_view)})", key="oim_lvl_go",
                             use_container_width=True):
                    _prog = st.progress(0.0, text="Fetching price history…")
                    _new = {}
                    for _i, _r in enumerate(_view, 1):
                        _prog.progress(_i / len(_view),
                                       text=f"Levels {_i}/{len(_view)} — {_r['symbol']}")
                        try:
                            _d = cached_fetch_ohlcv(_r["symbol"])
                        except Exception:
                            _d = None
                        _new[_r["symbol"]] = plv.locate(_d)
                    _prog.empty()
                    st.session_state[_lvl_key] = _new
                    _levels = _new
            with _lc2:
                if _levels:
                    _got = sum(1 for v in _levels.values() if v)
                    _at = sum(1 for v in _levels.values() if v and v["at_level"])
                    st.caption(
                        f"**{_got}** of {len(_levels)} names located in their "
                        f"{plv.DEFAULT_WINDOW}-bar range · **{_at}** sitting at an "
                        f"extreme, the rest mid-range. This answers what an OI print "
                        f"cannot on its own: fresh longs at a three-month high are a "
                        f"breakout being bought; the same OI mid-range is the same "
                        f"money with nothing to push against."
                    )
                else:
                    st.caption(
                        f"Adds a **Level** column — where each close sits in its "
                        f"{plv.DEFAULT_WINDOW}-bar range, and whether the OI build "
                        f"happened at one. Costs one price fetch per symbol, so it "
                        f"is opt-in."
                    )

            def _level_cells(sym: str, reading: str) -> dict:
                loc = _levels.get(sym)
                if not loc:
                    return {"Level": None, "Range %": None, "Lvl": ""}
                tag = plv.tag_against_oi(loc, reading)
                return {
                    "Level": loc["state"],
                    "Range %": loc["range_pos"],
                    "Lvl": tag["tag"] if tag else "",
                }

            _pcr_by_sym, _pcr_calib, _pcr_index = cached_pcr()

            def _pcr_cells(sym: str, price_pct: float) -> dict:
                p = _pcr_by_sym.get(sym)
                if not p or not p.get("liquid") or not np.isfinite(p.get("pcr", float("nan"))):
                    return {"PCR": None, "PCR %ile": None, "ΔPCR": None, "Options": ""}
                _tag = pcr.price_pcr_tag(price_pct, p.get("pcr_chg"))
                _pct = pcr.stock_percentile(p["pcr"], _pcr_calib)
                return {
                    "PCR": round(float(p["pcr"]), 2),
                    "PCR %ile": round(_pct) if _pct is not None else None,
                    "ΔPCR": (round(float(p["pcr_chg"]), 2)
                             if p.get("pcr_chg") is not None
                             and np.isfinite(p["pcr_chg"]) else None),
                    "Options": _tag["tag"] if _tag else "",
                }

            _tbl = pd.DataFrame([{
                "Symbol":    r["symbol"],
                "Reading":   r["reading"],
                "Strength":  r["strength"],
                "Price %":   round(r["price_pct"], 2),
                "OI %":      round(r["oi_pct"], 2),
                "RVol":      (round(r["rvol"], 2) if r.get("rvol") is not None else None),
                **_level_cells(r["symbol"], r["reading"]),
                **_pcr_cells(r["symbol"], r["price_pct"]),
                "OI":        int(r["oi"]),
                "Turnover (₹cr)": round(r["turnover"] / 1e7, 0),
                "Chart":     _oi_chart_url(r["symbol"]),
            } for r in _view])
            _tbl = _with_analyze_col(_tbl, "Symbol", after="Chart")
            st.dataframe(
                _tbl, use_container_width=True, hide_index=True,
                column_config={
                    "Chart": st.column_config.LinkColumn(
                        "Chart", display_text="📈 Open", width="small"),
                    "Analyze": _analyze_colcfg(),
                    "Price %": st.column_config.NumberColumn("Price %", format="%.2f%%"),
                    "OI %": st.column_config.NumberColumn("OI %", format="%.2f%%"),
                    "RVol": st.column_config.NumberColumn(
                        "RVol", format="%.2fx",
                        help="Today's futures volume ÷ the symbol's own median "
                             "over the prior 5 settled sessions. 1.00x means it "
                             "traded exactly as much as it usually does. Blank "
                             "means no baseline was available — unmeasured, not "
                             "normal."),
                    "Level": st.column_config.TextColumn(
                        "Level", width="small",
                        help="Where the close sits in its 60-bar range: NEW HIGH / "
                             "AT RESISTANCE / MID-RANGE / AT SUPPORT / NEW LOW. "
                             "Position only — it is not a direction."),
                    "Range %": st.column_config.NumberColumn(
                        "Range %", format="%d",
                        help="0 = at the 60-bar low, 100 = at the 60-bar high."),
                    "Lvl": st.column_config.TextColumn(
                        "Lvl", width="small",
                        help="Whether the level CONFIRMS or DIVERGES from the OI "
                             "reading — longs built at resistance confirm, longs "
                             "built at support diverge. Blank for mid-range names, "
                             "which is most of them. A separate opinion: it does "
                             "not feed Reading or Strength."),
                    "PCR": st.column_config.NumberColumn(
                        "PCR", format="%.2f",
                        help="Put OI ÷ Call OI, all expiries. Blank where option "
                             "OI is too thin to read."),
                    "PCR %ile": st.column_config.NumberColumn(
                        "PCR %ile", format="%d",
                        help="Rank within TODAY'S liquid stock cross-section. "
                             "Stock PCR runs structurally lower than index PCR, so "
                             "the usual <0.70/>1.30 bands do not apply here — the "
                             "median NSE stock sits near 0.68."),
                    "ΔPCR": st.column_config.NumberColumn(
                        "ΔPCR", format="%.2f",
                        help="One-day change, reconstructed from ChngInOpnIntrst. "
                             "More informative than the level, which is largely "
                             "structural."),
                    "Options": st.column_config.TextColumn(
                        "Options", width="small",
                        help="Whether the options side CONFIRMS or DIVERGES from "
                             "the price move. A separate opinion — it does not "
                             "feed the Reading or Strength columns."),
                },
            )
            _vb = cached_volume_baseline()
            _dg = [r["symbol"] for r in _view if r.get("thin_participation")]
            st.caption(
                f"**RVol** is today's volume against the symbol's own median over "
                f"the prior **{_vb.get('sessions', 0)}** settled session(s) — "
                f"\"high volume\" only means anything relative to what that name "
                f"normally trades. It can **downgrade** a STRONG reading to "
                f"MODERATE when a large move on a large OI build happened without "
                f"the participation to back it, but it never promotes: volume is "
                f"a veto, not a vote. "
                + (f"Today it held back **{', '.join(_dg)}**."
                   if _dg else
                   "Today it downgraded nothing — measured across a recent "
                   "session, STRONG names already ran ~4x their normal volume, "
                   "so this fires rarely by construction.")
            )
            st.caption(
                "**PCR columns are a separate, options-side opinion** — they do "
                "not feed *Reading* or *Strength*, which remain pure futures-OI "
                "readings. PCR has no fixed sign (a high reading is confirmation "
                "to a trend-follower and crowding to a contrarian), and it is "
                "**not backtested here**, so it is shown as context rather than "
                "allowed to move a verdict. Ranking is against today's liquid "
                "stock cross-section, never against index PCR — index puts carry "
                "portfolio-hedging demand single-stock options do not, which "
                "makes the two scales genuinely different."
            )

            # ── Per-name reads ────────────────────────────────────────────────
            # Grouped by reading, not a flat top-N slice. Covering and unwinding
            # are graded UNSUPPORTED by construction, so a global cap sorted by
            # strength would let build-ups fill every slot and silently hide a
            # whole category the user explicitly asked to see.
            st.markdown("#### What each reading means")
            _PER_READING = 8
            for _reading in _readings:
                _group = [r for r in _view if r["reading"] == _reading]
                if not _group:
                    continue
                st.markdown(
                    f"**{_reading}** — {len(_group)} name(s)"
                    + (f", showing the {_PER_READING} with the largest OI change"
                       if len(_group) > _PER_READING else "")
                )
                for r in _group[:_PER_READING]:
                    col = _strength_color.get(r["strength"], "#9e9e9e")
                    with st.expander(
                        f"{r['symbol']} — {r['strength']} · "
                        f"price {r['price_pct']:+.2f}% · OI {r['oi_pct']:+.2f}%"
                    ):
                        _h1, _h2, _h3 = st.columns([3, 1, 1])
                        with _h1:
                            st.markdown(
                                f"<span style='color:{col};font-weight:700'>"
                                f"{r['reading']} · {r['bias']}</span>",
                                unsafe_allow_html=True,
                            )
                        with _h2:
                            st.link_button(
                                "📈 Chart", url=_oi_chart_url(r["symbol"]),
                                help="Open in Chart Tool",
                                use_container_width=True,
                            )
                        with _h3:
                            _au = _analyze_url(r["symbol"])
                            if _au:
                                st.link_button(
                                    "↗ Analyze", url=_au,
                                    help="Open the 3-POV Council analysis in a new tab",
                                    use_container_width=True,
                                )
                        st.write(r["detail"])
                        st.caption(
                            f"Futures close ₹{r['close']:,.2f} · spot ₹{r['spot']:,.2f} · "
                            f"series OI {r['oi']:,.0f} ({r['oi_chg']:+,.0f}) · "
                            f"turnover ₹{r['turnover']/1e7:,.0f} crore · "
                            f"{r['days_to_expiry']} session(s) to expiry."
                        )
                        # Level context, its own sentence for the same reason as
                        # the options line below: it is beside the reading, not in it.
                        _loc = _levels.get(r["symbol"])
                        if _loc:
                            _lt = plv.tag_against_oi(_loc, r["reading"])
                            st.markdown(
                                f"**Level (separate read):** {_loc['state']} — "
                                f"{_loc['range_pos']:.0f}% of the "
                                f"{_loc['window']}-bar range "
                                f"({_loc['range_low']:,.2f}–{_loc['range_high']:,.2f}), "
                                f"{abs(_loc['to_high_pct']):.1f}% below the high.")
                            if _lt:
                                st.caption(f"**{_lt['tag']}** — {_lt['note']} "
                                           f"This does not change the reading above.")
                        # Options side, stated as its own sentence so it can never
                        # be mistaken for part of the futures reading above.
                        _p = _pcr_by_sym.get(r["symbol"])
                        if _p and _p.get("liquid") and np.isfinite(_p.get("pcr", float("nan"))):
                            _pct = pcr.stock_percentile(_p["pcr"], _pcr_calib)
                            _tag = pcr.price_pcr_tag(r["price_pct"], _p.get("pcr_chg"))
                            _line = (f"**Options side (separate read):** PCR "
                                     f"{_p['pcr']:.2f}")
                            if _pct is not None:
                                _line += (f" — p{_pct:.0f} of today's liquid stock "
                                          f"cross-section, "
                                          f"{pcr.classify_stock(_p['pcr'], _pcr_calib)}")
                            if _p.get("pcr_chg") is not None and np.isfinite(_p["pcr_chg"]):
                                _line += f" · one-day change {_p['pcr_chg']:+.2f}"
                            st.markdown(_line + ".")
                            if _tag:
                                st.caption(f"**{_tag['tag']}** — {_tag['note']} "
                                           f"This does not change the reading above.")
                        for c in r["caveats"]:
                            st.warning(c)

        st.caption(
            "OI is summed across **every listed expiry**, not just the front month. "
            "Near expiry, OI drains out of the front contract and reappears in the "
            "next one — reading the front month alone turns ordinary rollover into a "
            "confident and entirely fictitious short-covering signal."
        )

        # ── Index, deliberately in its own section ────────────────────────────
        # Everything index-level lives here and nowhere else. Index and stock
        # readings are not comparable on either axis: an index OI build of 3% is
        # an ordinary day where a stock's would be strong, and index puts carry
        # portfolio-hedging demand single-stock options do not. Merging either
        # into the tables above would invite exactly the comparison the separate
        # floors exist to prevent.
        with st.expander("Index futures & options — separate scale, own floors"):
            _idx_recs, _idx_date = cached_oi_momentum_index()
            st.markdown("**Index futures — price vs OI**")
            if not _idx_recs:
                st.info("No index futures in this session's bhavcopy.")
            else:
                _f = oim.INDEX_FLOORS
                st.dataframe(
                    pd.DataFrame([{
                        "Index":    r["symbol"],
                        "Reading":  r["reading"],
                        "Strength": r["strength"],
                        "Price %":  round(r["price_pct"], 2),
                        "OI %":     round(r["oi_pct"], 2),
                        "RVol":     (round(r["rvol"], 2)
                                     if r.get("rvol") is not None else None),
                        "Series OI": int(r["oi"]),
                    } for r in _idx_recs]),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "Price %": st.column_config.NumberColumn("Price %", format="%.2f%%"),
                        "OI %": st.column_config.NumberColumn("OI %", format="%.2f%%"),
                        "RVol": st.column_config.NumberColumn("RVol", format="%.2fx"),
                    },
                )
                st.caption(
                    f"**Index floors, not stock floors.** A reading needs "
                    f"|price| ≥ {_f['min_price_pct']}% and |OI| ≥ {_f['min_oi_pct']}%; "
                    f"STRONG needs {_f['strong_price_pct']}% and "
                    f"{_f['strong_oi_pct']}%. Measured over 12 sessions, an index "
                    f"moves about 58% as much as a single stock on price while its "
                    f"OI swings roughly twice as hard, so the stock floors are wrong "
                    f"in both directions. Calibrated on the **liquid** indices only "
                    f"— FINNIFTY and NIFTYNXT50 swing 20%+ on twenty-odd thousand "
                    f"contracts, and pooling them inflated the cut so far that "
                    f"STRONG could never be earned. Anything under "
                    f"{_f['min_oi']:,.0f} contracts is graded UNRELIABLE for that "
                    f"reason."
                )
                _unrel = [r["symbol"] for r in _idx_recs if r["strength"] == "UNRELIABLE"]
                if _unrel:
                    st.caption(f"Below the liquidity floor this session: "
                               f"**{', '.join(_unrel)}**.")

            st.divider()
            st.markdown("**Index PCR**")
            _idx_recs = [pcr.index_reading(_pcr_index, s)
                         for s in _pcr_index["symbol"].tolist()] if not _pcr_index.empty else []
            _idx_recs = [x for x in _idx_recs if x]
            if not _idx_recs:
                st.info("No index option rows in this session's bhavcopy.")
            else:
                st.dataframe(
                    pd.DataFrame([{
                        "Index": x["symbol"],
                        "PCR": round(x["pcr"], 3),
                        "ΔPCR": (round(x["pcr_chg"], 3)
                                 if x["pcr_chg"] is not None else None),
                        "Option OI": int(x["total_oi"]),
                        "Readable": "yes" if x["liquid"] else "too thin",
                    } for x in _idx_recs]),
                    use_container_width=True, hide_index=True,
                )
                st.caption(
                    "**No sentiment band is shown here, on purpose.** A stock's "
                    "PCR can be ranked against 200-odd peers on the same day; "
                    "an index can only be ranked against its own history, and "
                    "none is stored yet. Borrowing the stock cross-section would "
                    "compare instruments whose PCR differs structurally — index "
                    "puts are the standard portfolio hedge, single-stock options "
                    "are not. Level and one-day change are honest to report; a "
                    "label would not be."
                )

# ──────────────────────────────────────────────────────────────────────────────
# Smart-Money Confluence — the Layer-4 panel (institutional-flow assembly point).
# smart_money.smart_money() is pure/offline; this is the impure caller that feeds
# it the live tape (deals + OI) and renders the drivers. Never a bare number.
# ──────────────────────────────────────────────────────────────────────────────
_L4_POS = {"confirmed_accumulation", "slow_accumulation", "fast_accumulation",
           "fresh_buying", "accumulated_quiet", "early_reversal"}
_L4_NEG = {"confirmed_distribution", "slow_distribution", "fast_distribution",
           "fresh_selling", "distributed_quiet"}


def _l4_color(agreement: str) -> str:
    if agreement in _L4_POS:
        return "#16a34a"
    if agreement in _L4_NEG:
        return "#dc2626"
    if agreement == "bought_now_selling":
        return "#d97706"                     # amber — the warning divergence
    return "#6b7280"                         # neutral / no data


def _l4_signed_bar(label: str, v: float) -> str:
    """A signed −1…+1 driver as a bar diverging from a centre line."""
    v = max(-1.0, min(1.0, float(v)))
    half = abs(v) * 50.0
    left = 50.0 if v >= 0 else 50.0 - half
    color = "#16a34a" if v >= 0 else "#dc2626"
    return (
        '<div style="display:flex;align-items:center;gap:8px;font-size:11px;margin:3px 0;">'
        f'<span style="width:112px;color:#7a6858;">{label}</span>'
        '<div style="flex:1;height:8px;background:#efe7db;border-radius:4px;position:relative;">'
        '<div style="position:absolute;left:50%;top:-1px;bottom:-1px;width:1px;background:#c9b9a4;"></div>'
        f'<div style="position:absolute;left:{left}%;width:{half}%;top:0;bottom:0;'
        f'background:{color};border-radius:4px;"></div></div>'
        f'<span style="width:40px;text-align:right;color:{color};font-weight:600;">{v:+.2f}</span></div>'
    )


def _render_smart_money_result(res: dict, include_fast: bool) -> None:
    ag = res["agreement"]
    color = _l4_color(ag)
    st.markdown(
        f'<div style="border-left:5px solid {color};background:#fbf7f0;'
        f'padding:10px 14px;border-radius:8px;margin:6px 0 10px 0;">'
        f'<span style="font-size:15px;font-weight:700;color:{color};">{res["headline"]}</span>'
        f'<span style="float:right;font-size:11px;color:#7a6858;">confidence: '
        f'{res["confidence"]}</span></div>',
        unsafe_allow_html=True,
    )

    col_s, col_f = st.columns(2)
    with col_s:
        slow = res["slow"]
        if slow:
            st.metric("Slow-Flow · ownership", slow["score"], slow["trajectory"])
            st.caption(f"as of {slow['as_of']} · {slow['coverage']} · lagging")
            for leg, lbl in (("fii", "FII"), ("dii", "DII"), ("promoter", "Promoter")):
                v = slow["legs"].get(leg)
                if v is not None:
                    st.markdown(_l4_signed_bar(lbl, v), unsafe_allow_html=True)
        else:
            st.metric("Slow-Flow · ownership", "—")
            st.caption("no cached ownership quarters — run "
                       "`ownership_cache.py --backfill`")

    with col_f:
        fast = res["fast"]
        if fast:
            st.metric("Fast-Flow · live tape", fast["score"])
            st.caption(f"{fast['window']} · {fast['coverage']} families")
            for fam, lbl in (("deals", "Block/bulk deals"), ("derivs", "OI regime")):
                v = fast["families"].get(fam)
                if v is not None:
                    st.markdown(_l4_signed_bar(lbl, v), unsafe_allow_html=True)
        else:
            st.metric("Fast-Flow · live tape", "—")
            st.caption("no deals/OI for this name today"
                       if include_fast else
                       "toggle **Include live tape** to load deals + OI")

    veto = res["veto"]
    if veto["status"] == "pledged":
        st.markdown(
            f"<span style='color:#dc2626;font-weight:600;'>⚠ Promoter pledge "
            f"{veto['pledge_pct']:.1f}% — governance risk</span>",
            unsafe_allow_html=True,
        )
    elif veto["status"] == "clean":
        st.caption("✓ Promoter pledge: clean (0%)")
    elif veto["status"] == "low":
        st.caption(f"Promoter pledge: {veto['pledge_pct']:.1f}%")
    else:
        st.caption("Promoter pledge: not fetched (Scanner Hub → Fetch pledge %)")

    for f in res["flags"]:
        if "governance" not in f:                # already surfaced above
            st.caption(f"• {f}")


def _render_layer4_panel() -> None:
    st.markdown("#### Smart-Money Confluence  ·  Layer 4")
    st.caption(
        "Is institutional money behind this name? Slow-flow (ownership trend) + "
        "live tape (block/bulk deals + OI regime), with promoter pledge as a "
        "governance veto. Confirmation-only — never a standalone entry."
    )
    c1, c2 = st.columns([3, 2])
    with c1:
        sym = st.text_input(
            "Symbol", value=st.session_state.get("selected_symbol", ""),
            key="l4_symbol", placeholder="e.g. RELIANCE",
        ).strip().upper().replace(".NS", "")
    with c2:
        include_fast = st.toggle(
            "Include live tape", value=False, key="l4_fast",
            help="Fetches today's bulk/block deals + F&O OI (cached ~1h). "
                 "Slower on first load; needed for a two-sided verdict.",
        )
    if not sym:
        st.info("Enter a symbol to read its institutional footprint.")
        return

    ohlcv = None
    try:
        ohlcv = cached_fetch_ohlcv(sym, days=90)
    except Exception:
        ohlcv = None

    deals_summary = oi_rec = None
    if include_fast:
        with st.spinner("Loading live tape (deals + OI)…"):
            try:
                _oi_recs, _ = cached_oi_momentum_scan(include_no_read=True)
                oi_rec = next((r for r in _oi_recs if r.get("symbol") == sym), None)
            except Exception:
                oi_rec = None
            try:
                _deals = cached_normalized_deals()
                if _deals is not None and not _deals.empty:
                    _slice = _deals[_deals["symbol"] == sym]
                    if not _slice.empty:
                        deals_summary = bdi.summarize_company(sym, _slice)
            except Exception:
                deals_summary = None

    res = smm.smart_money(sym, deals_summary=deals_summary, oi=oi_rec, ohlcv=ohlcv)
    _render_smart_money_result(res, include_fast)


# ──────────────────────────────────────────────────────────────────────────────
# Strategy Hub
# Three-section page mirroring StockEdge's analytics layout:
#   1. Chart Patterns — recent major-stock detections with outcome tracking
#   2. Trading Strategies — live category counts by strategy family and horizon
#   3. Fundamental Scores — top-scored names with badge + EPS/PE sparklines
# Data is sourced from the last wiki ingest (EOD snapshot); date shown in header.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Strategy Hub":

    _SNAP_DATE = "11 Aug 2026"

    st.markdown(
        f"<h2 style='margin-bottom:2px;'>Strategy Hub</h2>"
        f"<div style='font-size:12px;color:{rs.TOKENS['text_muted']};margin-bottom:16px;'>"
        f"Snapshot: {_SNAP_DATE} · Chart patterns + trading strategies + fundamental scores"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Smart-Money Confluence (Layer 4) — live, per-symbol ───────────────────
    with st.container(border=True):
        _render_layer4_panel()

    # ── 1. Chart Patterns ─────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### Chart Patterns  ·  Major Stocks")
        st.caption("Past detections from StockEdge (EOD, AI + Human hybrid). "
                   "Outcome = LTP vs published price point.")

        import pandas as pd

        _PATTERNS = [
            # (Stock, Pattern, Bias, Published, Pub Price, LTP, Move%)
            ("CE Info Systems",      "Double Top",          "Bearish",  "04 Aug", 1231.95, 1013.30, -17.7),
            ("Zee Entertainment",    "Double Top",          "Bearish",  "03 Aug",  118.35,   91.56, -22.6),
            ("Supreme Petrochem",    "Double Top",          "Bearish",  "29 Jul",  788.00,  685.25, -13.0),
            ("Gallantt Ispat",       "Bearish Flag",        "Bearish",  "21 Jul",  618.50,  593.50,  -4.0),
            ("Hero MotoCorp",        "Falling Channel",     "Bearish",  "20 Jul", 4942.38, 5865.50, +18.7),
            ("Mahindra & Mahindra",  "Falling Channel",     "Bearish",  "21 Jul", 3172.73, 3460.10,  +9.1),
            ("PNB Housing Finance",  "Rising Wedge",        "Bearish",  "23 Jul", 1073.38, 1142.10,  +6.4),
            ("Pine Labs",            "Double Top",          "Bearish",  "16 Jul",  164.40,  167.58,  +1.9),
            ("Muthoot Finance",      "Falling Wedge",       "Bearish",  "21 Jul", 3068.97, 2915.90,  -5.0),
            ("Jubilant FoodWorks",   "Double Bottom",       "Bullish",  "27 Jul",  408.55,  488.20, +19.5),
            ("Sapphire Foods",       "Sym. Triangle",       "Bullish",  "27 Jul",  182.94,  236.02, +29.0),
            ("LTM Ltd.",             "Sym. Triangle",       "Bullish",  "28 Jul", 4192.58, 4850.00, +15.7),
            ("Piramal Pharma",       "Sym. Triangle",       "Bullish",  "17 Jul",  177.18,  214.19, +20.9),
            ("RR Kabel",             "Sym. Triangle",       "Bullish",  "22 Jul", 2386.29, 2812.80, +17.9),
            ("Clean Science & Tech", "Sym. Triangle",       "Bullish",  "20 Jul",  756.03,  810.00,  +7.1),
            ("Hyundai Motor India",  "Ascending Triangle",  "Bullish",  "31 Jul", 2064.80, 2200.00,  +6.5),
            ("CRISIL",               "Ascending Triangle",  "Bullish",  "21 Jul", 4250.00, 4480.80,  +5.4),
            ("Blue Star",            "Sym. Triangle",       "Neutral",  "03 Aug",    None,    None, -13.0),
            ("Zee Entertainment",    "Sym. Triangle",       "Neutral",  "27 Jul",    None,    None, -15.3),
            ("Supreme Petrochem",    "Falling Channel",     "Bearish",  "27 Jul",    None,    None,  -9.0),
        ]

        _pat_df = pd.DataFrame(_PATTERNS, columns=[
            "Stock", "Pattern", "Bias", "Published", "Pub Price ₹", "LTP ₹", "Move %",
        ])

        def _bias_badge(b: str) -> str:
            colors = {"Bullish": "#2e7d32", "Bearish": "#c62828", "Neutral": "#5c6bc0"}
            return f'<span style="background:{colors.get(b,"#666")};color:#fff;' \
                   f'border-radius:4px;padding:1px 6px;font-size:11px;">{b}</span>'

        _pat_filter = st.radio(
            "Filter", ["All", "Bullish", "Bearish", "Neutral"],
            horizontal=True, key="sh_pat_filter",
        )
        _pat_view = _pat_df if _pat_filter == "All" else _pat_df[_pat_df["Bias"] == _pat_filter]

        st.dataframe(
            _pat_view.drop(columns=["Bias"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Stock":       st.column_config.TextColumn("Stock", width="medium"),
                "Pattern":     st.column_config.TextColumn("Pattern", width="medium"),
                "Published":   st.column_config.TextColumn("Published", width="small"),
                "Pub Price ₹": st.column_config.NumberColumn("Pub Price ₹", format="₹%.2f"),
                "LTP ₹":       st.column_config.NumberColumn("LTP ₹", format="₹%.2f"),
                "Move %":      st.column_config.NumberColumn("Move %", format="%.1f%%"),
            },
        )
        _total = len(_pat_view)
        _bull_pats = (_pat_view["Move %"] > 0).sum()
        _bear_pats = (_pat_view["Move %"] < 0).sum()
        st.caption(
            f"{_total} pattern(s) shown · "
            f"**{_bull_pats}** above publish price · **{_bear_pats}** below · "
            f"Major Stocks filter · activeness-status=200"
        )

    # ── 2. Trading Strategies ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### Trading Strategies  ·  Live Counts")
        st.caption(
            "Predefined combination scans re-run EOD by 7 PM. "
            f"Counts as of {_SNAP_DATE}."
        )

        _STRATEGIES = [
            # (name, horizon, direction, stocks, description, locked)
            ("Cannon",   "One Day",    "Bullish",    7, "Momentum breakout with volume surge",         False),
            ("Eagle",    "One Day",    "Bearish",    0, "Intraday reversal with distribution signal",  False),
            ("Falcon",   "Swing",      "Bullish",   10, "Multi-day trend continuation setup",          False),
            ("Surfing",  "Swing",      "Bearish",    2, "Bearish continuation on swing timeframe",     False),
            ("Sword",    "Positional", "Bullish",    3, "Multi-week breakout with fundamental filter", True),
            ("Dove",     "Positional", "Bearish",    0, "Long-duration distribution pattern",          True),
        ]

        _hor_colors  = {"One Day": "#1565c0", "Swing": "#2e7d32", "Positional": "#6a1b9a"}
        _dir_colors  = {"Bullish": "#2e7d32", "Bearish": "#c62828"}
        _dir_icons   = {"Bullish": "▲", "Bearish": "▼"}

        _sg_cols = st.columns(3)
        for _si, (_sname, _shor, _sdir, _scount, _sdesc, _slocked) in enumerate(_STRATEGIES):
            with _sg_cols[_si % 3]:
                _lock_html = (
                    ' <span style="font-size:11px;opacity:0.6;">🔒 Pro</span>'
                    if _slocked else ""
                )
                st.markdown(
                    f'<div style="border:1px solid {rs.TOKENS["border"]};border-radius:8px;'
                    f'padding:14px 16px;margin-bottom:12px;">'
                    f'<div style="font-size:15px;font-weight:700;margin-bottom:4px;">'
                    f'{_sname}{_lock_html}</div>'
                    f'<div style="margin-bottom:8px;">'
                    f'<span style="background:{_hor_colors[_shor]};color:#fff;'
                    f'border-radius:4px;padding:1px 7px;font-size:11px;margin-right:4px;">'
                    f'{_shor}</span>'
                    f'<span style="background:{_dir_colors[_sdir]};color:#fff;'
                    f'border-radius:4px;padding:1px 7px;font-size:11px;">'
                    f'{_dir_icons[_sdir]} {_sdir}</span>'
                    f'</div>'
                    f'<div style="font-size:12px;color:{rs.TOKENS["text_muted"]};'
                    f'margin-bottom:10px;">{_sdesc}</div>'
                    f'<div style="font-size:22px;font-weight:800;'
                    f'color:{_dir_colors[_sdir]};">{_scount}'
                    f'<span style="font-size:12px;font-weight:400;'
                    f'color:{rs.TOKENS["text_muted"]};margin-left:4px;">stocks</span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        _bull_total = sum(s[3] for s in _STRATEGIES if s[2] == "Bullish")
        _bear_total = sum(s[3] for s in _STRATEGIES if s[2] == "Bearish")
        st.caption(
            f"Net: **{_bull_total} bullish** signals vs **{_bear_total} bearish** · "
            f"Bullish skew in strategy engine is consistent — chart patterns are "
            f"backward-looking; strategies are forward-looking EOD signals."
        )

    # ── 3. Fundamental Scores ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### Fundamental Scores  ·  Top Picks")
        st.caption(
            "Scores computed from the last fundamental data pull. "
            "Shield color: green ≥ 70 · amber 50–69 · red < 50."
        )

        _FS_DATA = [
            # (stock, sector, mcap_cr, fund_score, eps_cagr_3y, pe_min, pe_max, pe_now, ltp, ltp_chg)
            ("DCM Shriram",    "Chemicals",      9_800,  75, -2.15,  12.1, 28.4, 14.2, 1143.50, +1.2),
            ("Vedanta",        "Metals",        1_52_000, 72, +16.10, 6.3, 18.7,  9.1,  465.80, +0.8),
            ("Jubilant FW",    "Consumer",      12_500,  68, +8.40,  32.0, 58.2, 41.0,  488.20, +2.1),
            ("CRISIL",         "Financials",    32_400,  81, +11.20, 28.5, 45.0, 36.8, 4480.80, +0.4),
            ("Hyundai India",  "Auto",         1_20_000, 65, +4.50,  18.0, 32.0, 22.1, 2200.00, +0.6),
            ("Piramal Pharma", "Pharma",        14_200,  59, -1.80,  40.0, 95.0, 62.0,  214.19, +3.2),
        ]

        def _shield_color(score: int) -> str:
            if score >= 70:
                return "#2e7d32"
            if score >= 50:
                return "#e65100"
            return "#c62828"

        def _pe_bar_html(pe_min, pe_max, pe_now, width=90) -> str:
            if pe_max <= pe_min:
                return "—"
            pct = max(0.0, min(1.0, (pe_now - pe_min) / (pe_max - pe_min)))
            filled = int(pct * width)
            marker = filled
            return (
                f'<div style="position:relative;width:{width}px;height:8px;'
                f'background:#e0e0e0;border-radius:4px;display:inline-block;">'
                f'<div style="width:{filled}px;height:8px;background:#1565c0;'
                f'border-radius:4px;"></div>'
                f'<div style="position:absolute;top:-2px;left:{marker}px;'
                f'width:3px;height:12px;background:#ff6f00;border-radius:2px;"></div>'
                f'</div><span style="font-size:10px;margin-left:5px;">{pe_now:.1f}x</span>'
            )

        for (_fstock, _fsec, _fmcap, _fscore, _feps, _fpe_min, _fpe_max, _fpe_now,
             _fltp, _fchg) in _FS_DATA:
            _sc = _shield_color(_fscore)
            _chg_color = "#2e7d32" if _fchg >= 0 else "#c62828"
            _chg_sign  = "+" if _fchg >= 0 else ""
            _eps_color = "#2e7d32" if _feps >= 0 else "#c62828"

            fc1, fc2, fc3, fc4, fc5, fc6 = st.columns([2.5, 1.2, 1.0, 1.8, 1.8, 1.2])
            with fc1:
                st.markdown(
                    f'<div style="padding-top:4px;font-weight:600;">{_fstock}</div>'
                    f'<div style="font-size:11px;color:{rs.TOKENS["text_muted"]};">'
                    f'{_fsec} · ₹{_fmcap/100:,.0f}Cr MCap</div>',
                    unsafe_allow_html=True,
                )
            with fc2:
                st.markdown(
                    f'<div style="padding-top:4px;">'
                    f'<span style="background:{_sc};color:#fff;border-radius:6px;'
                    f'padding:3px 10px;font-weight:700;font-size:13px;">🛡 {_fscore}</span>'
                    f'<span style="font-size:10px;color:{rs.TOKENS["text_muted"]};'
                    f'margin-left:4px;">/100</span></div>',
                    unsafe_allow_html=True,
                )
            with fc3:
                st.markdown(
                    f'<div style="padding-top:6px;font-size:12px;">'
                    f'<span style="color:{_eps_color};font-weight:600;">'
                    f'{_chg_sign if _feps >= 0 else ""}{_feps:.2f}%</span>'
                    f'<br><span style="font-size:10px;color:{rs.TOKENS["text_muted"]};">'
                    f'EPS 3Y CAGR</span></div>',
                    unsafe_allow_html=True,
                )
            with fc4:
                st.markdown(
                    f'<div style="padding-top:8px;">'
                    f'{_pe_bar_html(_fpe_min, _fpe_max, _fpe_now)}</div>'
                    f'<div style="font-size:10px;color:{rs.TOKENS["text_muted"]};">'
                    f'PE 3Y range {_fpe_min:.0f}–{_fpe_max:.0f}x</div>',
                    unsafe_allow_html=True,
                )
            with fc5:
                st.markdown(
                    f'<div style="padding-top:4px;font-size:14px;font-weight:700;">'
                    f'₹{_fltp:,.2f}</div>'
                    f'<div style="font-size:11px;color:{_chg_color};">'
                    f'{_chg_sign}{_fchg:.2f}% today</div>',
                    unsafe_allow_html=True,
                )
            with fc6:
                _qs_url = f"?nav=analyze&symbol={_fstock.replace(' ','%20').split()[0].upper()}"
                st.markdown(
                    f'<div style="padding-top:6px;">'
                    f'<a href="{_qs_url}" target="_self" style="font-size:11px;">'
                    f'Analyze ↗</a></div>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                f'<hr style="border:none;border-top:1px solid {rs.TOKENS["border"]};'
                f'margin:4px 0;">',
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────────────────────────────────────
# Background-job poll — MUST be the last thing the script does. If any queued /
# running job exists, sleep briefly then rerun, so the status panel and any
# completed results refresh on their own. The full page above has already
# rendered, so the user keeps interacting (new clicks queue) while a job runs.
# ──────────────────────────────────────────────────────────────────────────────
ui_jobs.autorefresh()
