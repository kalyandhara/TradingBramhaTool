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
import timeframe_board as tfb
import horizon_geometry as hgeo
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
import index_strip as istrip
import desk_pages as dpages
from desk_pages.stock_panels import (  # B-171 extraction
    _axis_tone,
    _compare,
    _cr,
    _flag_col,
    _FLAG_TONE,
    _FLAG_WORD,
    _gauge_svg,
    _peer_head_to_head,
    _period_return,
    _q,
    _QTR_ANOMALY_PCT,
    _render_thesis,
    _tone_signed,
    _volume_profile,
    cached_ownership,
    fmt_money,
    fmt_pct,
    gain_loss_badge,
    render_condition_table,
    render_fundamental_header,
    render_fundamental_history,
    render_fundamental_signals,
    render_horizon_geometry,
    render_momentum_meter,
    render_ownership_flow,
    render_pattern_metrics,
    render_red_flags)
from desk_pages.table_cells import (  # B-171 extraction
    _card_trade_fundamentals_html,
    _confluence_chips,
    _fam_of,
    _pct_tone,
    _pw,
    _rating_color,
    _rs_walk_cell,
    _rs_walk_lookup,
    _scanner_stats_html,
    _svp_caption,
    _svp_cells,
    _wl_rs_mom)
import breadth_strip as bstrip
import block_deal_intel as bdi
import deal_infographic as dinf
import nse_oi_momentum as oim
import browser_cookie_helper as bch
import portfolio_risk as prisk
import position_sizing as psz
import ui_tables as uit
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
import pa_report
import pcr
import price_levels as plv
import rrg as rrg_mod
import ownership_cache as ocache
import concalls
import snapshot_store as snapstore
import snapshot_registry as snapreg

# Beginner-friendly help system
import ui_help as help
import help_panels

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
import out_paths as _out

# Sidebar starts collapsed: navigation moved to a horizontal top bar, so the
# sidebar now holds nothing. Left expandable rather than hidden outright so
# Streamlit's own controls stay reachable.
st.set_page_config(page_title="Trading Bramha Dashboard", layout="wide",
                   initial_sidebar_state="collapsed")

# Base URL of THIS dashboard, used to build "Analyze" deep-links that open the
# Stock Analyzer (with the 3-POV Council) in a new browser tab. Mirrors the
# hardcoded localhost:5001 chart-server convention already used across the app.
DASHBOARD_BASE = uit.DASHBOARD_BASE


_analyze_url = uit.analyze_url


_chart_url = uit.chart_url
_analyze_colcfg = uit.analyze_colcfg
_with_analyze_col = uit.with_analyze_col

# Chart-icon family for dataframes lives in ui_tables so extracted pages can use
# it without importing this module (which would re-run the whole app).
_CHART_FAMILY_COLS = uit.CHART_FAMILY_COLS
_chart_family_urls = uit.chart_family_urls
_with_chart_family = uit.with_chart_family
_chart_family_colcfg = uit.chart_family_colcfg


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
            parts.append(f'<span style="color:#166534;font-weight:600;">{score}</span>')
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
    st.iframe(
        f"""
        <div id="tbcard-{key}">{card_html}</div>
        <div style="margin-top:10px;">
          <button id="tbbtn-{key}" onclick="tbCopy_{key}()"
            style="background:#ea580c;color:#fff;border:none;border-radius:8px;
                   padding:7px 14px;cursor:pointer;font-size:13px;font-weight:600;">
            📋 Copy card
          </button>
          <span id="tbmsg-{key}" style="margin-left:10px;font-size:12px;color:#166534;"></span>
        </div>
        <script>
        function tbCopy_{key}() {{
          var card = document.getElementById('tbcard-{key}');
          var msg  = document.getElementById('tbmsg-{key}');
          var plain = {plain_js};
          var html = card.innerHTML;
          function ok()  {{ msg.style.color='#166534';
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
    st.iframe(
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
          <span id="tbplmsg-{key}" style="margin-left:10px;font-size:12px;color:#166534;"></span>
        </div>
        <script>
        function tbPlain_{key}() {{
          var ta  = document.getElementById('tbpl-{key}');
          var msg = document.getElementById('tbplmsg-{key}');
          var txt = {txt_js};
          function ok()  {{ msg.style.color='#166534';
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
    )


# FR-0 style primitive — one token block for every HTML surface on the page.
# Injected once, before anything that calls the rs.* helpers.
st.markdown(rs.report_css(), unsafe_allow_html=True)

# ── Widget chrome ─────────────────────────────────────────────────────────────
# Streamlit exposes no Python API for how a button LOOKS — `type=` picks
# primary/secondary and `width="stretch"` stretches it, and that is the whole
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
        /* Full-bleed needs the WIDTH, not just the margins. A block element's
           width is already resolved before margins apply, so margin-left:-2rem
           shifted the bar 32px left while margin-right:-2rem did nothing to its
           own box - it only affects what follows. The bar ended up content-width
           but offset: page content at 32..1238, ribbon at 0..1206, visibly out of
           line with the cards under it at BOTH ends. Adding 4rem of width makes
           the two negative margins actually cancel the container's padding. */
        margin-left:  -2rem !important;
        margin-right: -2rem !important;
        width: calc(100% + 4rem) !important;
        /* ...and the width alone is still not enough. The wrapper inherits
           max-width:100% (which clamps 1270 straight back to the 1206 content
           width) and it is a FLEX ITEM, so it would shrink again anyway. All
           three declarations are load-bearing; drop any one and the bar snaps
           back to being 32px out of line. */
        max-width: none !important;
        flex: 0 0 auto !important;
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
        with st.popover("● Signed in", width="stretch"):
            st.caption(f"Signed in as **{st.session_state.get('auth_user', 'user')}**. "
                       "Sign-in is optional — no page is gated on it today.")
            if st.button("Sign out", key="tb_signout", width="stretch"):
                st.session_state["logged_in"] = False
                st.session_state.pop("auth_user", None)
                st.rerun()
        return

    with st.popover("Sign in", width="stretch"):
        st.caption("Optional — everything is browsable without it. Signing in "
                   "only records who you are for now.")
        with st.form("tb_login_form", border=False):
            _un = st.text_input("Username", placeholder="Enter username")
            _pw = st.text_input("Password", placeholder="Enter password", type="password")
            if st.form_submit_button("Sign in →", width="stretch",
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
                         "Breakout Scans", "High-Growth Screener", "SVP Structure"],
    "Market Intel":     ["Market Sentiment", "India Market Intel", "OI Momentum"],
    "Research":         ["Predictive Analysis", "Stock Analyzer", "Sector wise Navigation", "Strategy Hub", "Sector Map", "Astro Timing", "Telegram Signals", "Glossary"],
    "Portfolio & Risk": ["Portfolio", "Watchlist", "Alerts"],
    "Ops":              ["Pipeline Log", "Scheduler Hub"],
}

#: One line per page, shown as the tooltip on its nav-popover button (Home no
#: longer cards the pages). Kept factual — each says what the page DOES, not how
#: good it is. Any page missing from here still routes fine, just without a hint.
#: Each starts with its pipeline stage (SCAN → SIGNAL → PLAN → RISK → MONITOR,
#: per analyses/Pipeline-Alignment-Audit) and "start here" marks the canonical
#: entry point (B-108, owner chose option b 2026-10-17). Routing is unchanged.
PAGE_BLURBS = {
    "Opportunity Hub":      "SIGNAL — start here · Ranked daily shortlist across every scanner",
    "Delete Funnel":        "SCAN · Technofunda 8-filter noise sieve — deletes to a shortlist",
    "Hidden Treasures":     "SCAN · Small/micro-cap conviction screen — ownership + quality",
    "Screener":             "SCAN — start here · The core NSE screen with the saved pipeline",
    "Other Screeners":      "SCAN · Ownership pipeline, sector rotation, bulk data",
    # COMPUTED, not typed. This read "24 pattern scanners" against a registry of  # claims-lint: checked B-79
    # 46 -- stale since whenever the 25th shipped, and sitting one hover away
    # from a Home tile that counts the registry correctly (B-79).
    "Scanner Hub":          f"SIGNAL · {len(sc.SCANNERS)} pattern scanners, run on any universe",
    "Breakout Scans":       "SCAN · New-high breakout feeds — yfinance 6M–10Y or TradingView",
    "High-Growth Screener": "SCAN · Quality growth names on ROE / ROCE / OPM floors",
    "SVP Structure":        "SIGNAL (bystander) · Volume-profile structure — not in the shortlist ranking",
    "Market Sentiment":     "SCAN · market · 0–100 composite regime gauge, with coverage",
    "India Market Intel":   "SCAN · market · Bulk & block deals, insider trades, gap scanner",
    "OI Momentum":          "SCAN · market · Open-interest build-up and unwinding",
    "Predictive Analysis":  "SIGNAL · Consolidated rating, chart and intel per stock",
    "Glossary":             "REFERENCE · Plain-English guide to every term, in learning order",
    "Stock Analyzer":       "RESEARCH · Full fundamental + technical deep dive",
    "Sector Map":           "SCAN · sectors · Relative Rotation Graph and sector orbit",
    "Sector wise Navigation":         "RESEARCH · Every industry peer in a ribbon — step through one by one",
    "Astro Timing":         "CONTEXT · Reversal calendar — context, never an entry",
    "Telegram Signals":     "SIGNAL · third-party · Ingested channel calls, parsed and tabulated",
    "Portfolio":            "RISK · Open positions, capital at risk, heat",
    "Watchlist":            "PLAN · Tracked names and their trade plans",
    "Alerts":               "MONITOR · Price and metric alerts you have armed",
    "Pipeline Log":         "MONITOR · What the 4:05 PM batch did, and whether it failed",
    "Scheduler Hub":        "MONITOR · Batch jobs & the live alert bot — schedule, run, monitor",
    "Strategy Hub":         "SIGNAL · Chart patterns, trading strategies, and fundamental scores",
}

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"

# Deep-link: a table's "Analyze ↗" link opens ?nav=analyze&symbol=SYM in a new
# tab. Consume the params once, route to the Stock Analyzer, pre-load the symbol
# and prime an auto-run, then clear the URL so sidebar navigation isn't pinned.
# ?nav=predict does the same for Predictive Analysis (Sector Lobby's openers,
# so they can be right-click -> "Open in new tab" links rather than buttons).
if st.query_params.get("nav") in ("analyze", "predict") and st.query_params.get("symbol"):
    _dl_sym = st.query_params["symbol"].strip().upper()
    if st.query_params["nav"] == "predict":
        st.session_state["current_page"] = "Predictive Analysis"
        st.session_state["pa_symbol"] = _dl_sym
    else:
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
# search · sign-in · help. The current-page label used to live here; it is a breadcrumb,
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
_nav = st.columns([1.4, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0, 0.1, 2.0, 0.95, 0.5],
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
    if st.button("Home", key="nav_Home", width="stretch",
                 type="primary" if st.session_state["current_page"] == "Home" else "secondary"):
        st.session_state["current_page"] = "Home"
        st.rerun()

for _i, (_gname, _gpages) in enumerate(PAGE_GROUPS.items()):
    with _nav[2 + _i]:
        _active_here = st.session_state["current_page"] in _gpages
        with st.popover(f"{_gname} ▾", width="stretch",
                        type="primary" if _active_here else "secondary"):
            for _p in _gpages:
                _is_active = st.session_state["current_page"] == _p
                if st.button(_p, key=f"nav_{_p}", width="stretch",
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

# Beginner mode toggle (the Glossary is a page: Research → Glossary)
with _nav[10]:
    beginner_mode = help.beginner_mode_toggle(key="nav_beginner_mode")

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
st.iframe(
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
    height=1,    # st.iframe rejects 0; a 1px frame is as invisible as the old 0px one
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

def _smc_cells(df) -> dict:
    """SMC state columns for one symbol's bars (smc_state.py). A failure is blank
    cells for that row — a context column must not take the table down."""
    try:
        import smc_state as _smc
        return _smc.row(df)
    except Exception:
        return {}


def _notes_table(df, key: str, symbol_col: str, *, column_config=None,
                 page_size: int = 200, select_col: str | None = None,
                 preselect: "set[str] | None" = None):
    """A table whose ONLY editable cells are the note and an optional tick-box.

    UI-2 (2026-09-10). Generalises the pattern B-63b proved on the Watchlist so
    the Scanner Hub tables get it too, against ONE note store
    (`portfolio_db.symbol_notes`) rather than a second one keyed differently.

    Everything computed is `disabled`, so the table stays a working surface for
    the one field that is genuinely yours without becoming a place where a stray
    keystroke rewrites a price. Writes go through `db.set_symbol_note`, which is
    NOT scoped to watchlist membership — a note about a name you are not
    watching is still a note.

    `select_col` adds an editable tick-box as the FIRST column and nothing else:
    it persists nothing and means nothing here. The caller reads the returned
    frame and decides what a tick is for — on the Watchlist it is "remove this
    row". Kept in this helper rather than built beside it because the alternative
    is a second `st.data_editor` over the same frame, and two editors against one
    table is the drift `columns.py` exists to stop.

    `preselect` starts those symbols ticked. It is still only a tick: the
    caller's own button is what acts on it, so a suggestion stays a suggestion.

    Returns the edited frame so a caller can keep using it.
    """
    import columns as _cols
    notes = db.get_symbol_notes([str(x) for x in df[symbol_col]])
    work = df.copy()
    work["notes"] = [notes.get(str(sym).strip().upper(), "")
                     for sym in work[symbol_col]]
    if select_col:
        # Front of the frame, which RENDERS second: `symbol` is pinned=True in
        # the registry, so it stays leftmost whatever the column order is, and
        # the tick lands immediately beside it. That is the placement wanted --
        # a destructive control at the far right of ~25 columns is a control
        # aimed at whichever row you happened to scroll to. Verified in the
        # running dashboard rather than inferred from the insert position.
        _pre = {str(x).strip().upper() for x in (preselect or ())}
        work.insert(0, select_col, [str(x).strip().upper() in _pre
                                    for x in work[symbol_col]])
    before = dict(zip((str(x).strip().upper() for x in work[symbol_col]),
                      work["notes"]))

    cfg = dict(column_config or {})
    cfg.update(_cols.configure("notes"))
    if select_col:
        cfg[select_col] = st.column_config.CheckboxColumn(
            select_col, help="Tick rows, then use the button below the table.",
            width="small", default=False)
    # `st.data_editor` DOES accept a Styler — its own docs say the styles apply
    # to NON-EDITABLE columns, and here every column except the note is disabled.
    # So the editable table keeps the tint pairs; nothing had to be traded away
    # for making the note writable. (Verified against streamlit 1.58's source
    # rather than assumed: an earlier version of this helper passed a plain frame
    # on the belief that editors could not be styled.)
    try:
        painted = _cols.tint(work)
    except Exception:
        painted = work
    edited = st.data_editor(
        painted, key=key, hide_index=True, width="stretch",
        column_config=cfg, row_height=_cols.ROW_HEIGHT,
        disabled=[c for c in work.columns
                  if c != "notes" and c != select_col],
    )
    changed = []
    for sym, note in zip(edited[symbol_col], edited["notes"]):
        s_ = str(sym).strip().upper()
        n_ = "" if pd.isna(note) else str(note)
        if n_ != before.get(s_, ""):
            changed.append((s_, n_))
    if changed:
        for s_, n_ in changed:
            db.set_symbol_note(s_, n_)
        st.success(f"Saved note{'s' if len(changed) > 1 else ''} for "
                   f"{', '.join(s for s, _ in changed[:5])}"
                   f"{'…' if len(changed) > 5 else ''}.")
        st.rerun()
    return edited


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

    `enforce_liquidity=False` drops the 10-day average turnover floor. That
    floor belongs to SCANNING — it keeps names you cannot trade out of a
    2,000-symbol sweep — and both fetchers applied it to every caller, so a page
    that had been handed one symbol by name returned "no usable data" for a
    stock yfinance serves perfectly well. CENTUM reported as "not on yfinance"
    while the Opportunity Hub was linking to it, which is the same app refusing
    to open a door it just pointed at.

    Bar-count and NaN validation still apply either way: those say there is no
    data, not that the data is not worth scanning.

    ── When to pass enforce_liquidity=False (audited 2026-09-09) ──────────────
    **The floor is a SCAN filter.** Keep it ON where a symbol arrived from a
    sweep and the point is to exclude what cannot be traded. Turn it OFF
    wherever the symbol was NAMED — by the user, by a holding, by an alert, by a
    curated list — because there the page is refusing to price something it is
    already showing, and a blank row reads as "no data" rather than "filtered".

    Seven call sites were switched during that audit: portfolio valuation and
    the positions table (you already OWN it), alert evaluation (an alert that
    CANNOT fire looks exactly like one that has not fired), the watchlist and
    its quick-add prefill, the peer-comparison technical columns, the bulk/block
    deal price context (where the floor was reporting thin NSE names as "not
    NSE-listed" — false), and the institutional-footprint lookup.
    """
    # Try enhanced volume fetcher first
    try:
        volume_fetcher = vf.VolumeFetcher(verbose=False)
        if not enforce_liquidity:
            volume_fetcher.MIN_TURNOVER = 0   # instance attr shadows the class floor
        df = volume_fetcher.fetch_with_volume(symbol, days=days, validate=True)
        if df is not None:
            return _drop_unusable_bars(df)
    except Exception as e:
        _log.warning("VolumeFetcher error for %s: %s", symbol, e)

    # Fallback to screener_pipeline
    return _drop_unusable_bars(
        sp.fetch_ohlcv(symbol, days=days,
                       min_turnover=None if enforce_liquidity else 0))


def _thin_volume_note(df, symbol: str) -> None:
    """Warn when a single-symbol page is looking at a name below the screen floor.

    The gate is off for these pages, which means the number has to be visible
    instead: an analysis of a stock turning over a few lakh a day is not wrong,
    but every level on it is worth less than the same level on a liquid name.

    Reported as traded value because that is what the floor measures — quoting
    a share count here would be quoting a number nothing enforces.
    """
    try:
        avg_turnover = float((df["close"] * df["volume"]).tail(10).mean())
    except Exception:
        return
    if avg_turnover >= sp.MIN_TURNOVER:
        return
    st.warning(
        f"**{symbol}** turns over ~₹{avg_turnover / 1e7:,.2f} cr/day over the "
        f"last 10 sessions — below the ₹{sp.MIN_TURNOVER / 1e7:,.0f} cr floor the "
        f"screeners use, so it never reaches a scan. Everything below is computed "
        f"normally; treat levels as indicative and assume slippage.",
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

    **What this number is NOT, for every downstream consumer of it:** B-66
    measured all four inputs and the composite against NIFTY's forward returns
    and found no discrimination anywhere (tercile spreads -0.01% to -0.12%,
    rho ~ 0, the two deepest inputs covering 18-19 years). It describes the
    current tape; it does not forecast. Anything reading this for DIRECTION is
    reading it for something it has been measured not to have.
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


# Unique NSE sector index tickers and their display labels — owned by
# snapshot_registry so the headless snapshot job and the page fetch the same set.
SECTOR_DISPLAY_NAMES = snapreg.SECTOR_DISPLAY_NAMES


# ──────────────────────────────────────────────────────────────────────────────
# Persisted report snapshots (snapshot_store / snapshot_registry)
# ------------------------------------------------------------------------------
# Every "generate on demand" surface that used to live in session state now
# loads the LAST STORED run on page open, shows when it ran, and refreshes on
# demand through the per-session job queue (so a click never blocks the page).
# The scheduled job (Scheduler Hub → Report Snapshot Refresh) rewrites them
# after the close; a start-up thread fills in any that are stale.
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, max_entries=64)
def _snapshot_payload(name: str, run_at: str):
    """Unpickle once per (name, run_at): a refresh changes run_at, busting it."""
    return snapstore.load_latest(name)[1]


def snapshot_get(name: str):
    """(meta, payload) of the newest OK snapshot, or (None, None)."""
    meta = snapstore.latest_meta(name, ok_only=True)
    if meta is None:
        return None, None
    return meta, _snapshot_payload(name, meta.run_at)


def _snapshot_job_label(name: str) -> str:
    return f"Refresh · {snapreg.SNAPSHOTS[name].label}"


def snapshot_refresh(name: str) -> bool:
    """Queue a recompute of `name` on the session job queue. False if one is
    already queued/running."""
    return ui_jobs.submit_unique(_snapshot_job_label(name), snapreg.run_one, name) is not None


def snapshot_panel(name: str, *, key: str, compact: bool = False,
                   button_label: str = "↻ Refresh now", help: str | None = None):
    """Last-run badge + refresh button for one snapshot. Returns (meta, payload).

    Consumes a finished refresh job for this snapshot (toast / error) so the
    outcome is shown exactly once, then reads the newest stored run.
    """
    spec = snapreg.SNAPSHOTS[name]
    label = _snapshot_job_label(name)
    q = ui_jobs.get_queue()
    done = q.take_result(label)
    if done is not None:
        if done.status == "error":
            st.error(f"{spec.label}: refresh failed — {done.error}")
        elif done.result is not None and not done.result.ok:
            st.error(f"{spec.label}: refresh failed — {done.result.error}")
        else:
            st.toast(f"✅ {spec.label} refreshed")
            if name == "sentiment":
                cached_latest_sentiment.clear()

    meta, payload = snapshot_get(name)
    running = q.is_active(label)
    last_meta = snapstore.latest_meta(name)          # may be an error row
    c1, c2 = st.columns([1, 4] if not compact else [1, 3])
    with c1:
        if st.button(button_label, key=f"{key}_snap_refresh", width="stretch",
                     disabled=running,
                     help=help or f"Recompute {spec.label} now (runs in the "
                                  f"background; the page stays live)."):
            snapshot_refresh(name)
            st.rerun()
    with c2:
        bits = []
        if running:
            bits.append("⏳ refreshing in the background…")
        if meta is None:
            bits.append("**No stored run yet** — press ↻ or wait for the scheduled "
                        "Report Snapshot Refresh (Scheduler Hub).")
        else:
            when = meta.run_at_dt.strftime("%d %b %Y %H:%M")
            stale = snapstore.is_stale(meta)
            bits.append(f"Last run **{when}**" + (" · ⚠ older than the last close"
                                                  if stale else "") +
                        (f" · {meta.elapsed:.0f}s" if meta.elapsed >= 1 else ""))
        if last_meta is not None and last_meta.error and (
                meta is None or last_meta.run_at >= meta.run_at):
            bits.append(f"⚠ last attempt failed: {last_meta.error}")
        st.caption(" · ".join(bits))
    return meta, payload


# ── "→ Predictive Analysis": hand a whole table over as the candidate set ────
# Any table (Home's institutional-volume and volume-shocker lists, the
# Watchlist) can push its symbols to Research › Predictive Analysis for a
# side-by-side read. The list persists in the settings table so it is still
# there after a restart, until replaced or cleared on the PA page.
_PA_SENT_KEY = "pa_sent_candidates"


def _pa_sent_load() -> dict | None:
    if _PA_SENT_KEY in st.session_state:
        return st.session_state[_PA_SENT_KEY]
    raw = db.get_setting(_PA_SENT_KEY, "") or ""
    try:
        data = json.loads(raw) if raw else None
    except Exception:                                    # noqa: BLE001
        data = None
    st.session_state[_PA_SENT_KEY] = data
    return data


def _pa_sent_save(data: dict | None) -> None:
    st.session_state[_PA_SENT_KEY] = data
    db.set_setting(_PA_SENT_KEY, json.dumps(data) if data else "")


def _pa_send_button(key: str, source: str, df, symbol_col: str,
                    note_fn=None, *, label: str | None = None) -> None:
    """One button under a table: make its symbols the Predictive Analysis
    candidate list (replacing the previous sent list) and jump there."""
    if df is None or getattr(df, "empty", True) or symbol_col not in df.columns:
        return
    items, seen = [], set()
    for i in range(len(df)):
        row = df.iloc[i]
        sym = str(row[symbol_col]).strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        note = ""
        if note_fn is not None:
            try:
                note = str(note_fn(row) or "")
            except Exception:                            # noqa: BLE001
                note = ""
        items.append({"symbol": sym, "note": note})
    if not items:
        return
    if st.button(label or f"→ Predictive Analysis ({len(items)})", key=f"{key}_to_pa",
                 help=f"Open Research › Predictive Analysis with these {len(items)} "
                      f"names as the candidate list for a side-by-side read."):
        _pa_sent_save({"source": source,
                       "sent_at": datetime.now().isoformat(timespec="minutes"),
                       "items": items})
        st.session_state["pa_symbol"] = items[0]["symbol"]
        st.session_state["current_page"] = "Predictive Analysis"
        st.rerun()


@st.cache_resource(show_spinner=False)
def _snapshot_startup_fill() -> list[str]:
    """Once per process: recompute, in a daemon thread, every snapshot whose
    stored run is older than the last close. Non-blocking; Home still opens
    instantly and shows whatever is stored until the thread lands."""
    import threading
    if (db.get_setting("snapshot_startup_fill", "1") or "1") != "1":
        return []
    names = [s.name for s in snapreg.ordered()
             if snapstore.is_stale(snapstore.latest_meta(s.name, ok_only=True))]
    if names:
        threading.Thread(target=snapreg.run_all, args=(names,),
                         name="snapshot-startup-fill", daemon=True).start()
    return names


try:
    _snapshot_startup_fill()
except Exception:                                    # noqa: BLE001 — never block the app
    pass


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


_VERDICT_STYLE = {
    "BUY":   ("🟢", "success"),
    "WATCH": ("🟡", "warning"),
    "AVOID": ("🔴", "error"),
}


@st.cache_data(ttl=1800, show_spinner=False)
def _cached_hourly(symbol: str) -> "pd.DataFrame":
    """Hourly bars for the timeframe board. Cached separately from daily because
    it is a second download and the board is the only thing that needs it."""
    import yfinance as yf
    tk = symbol if "." in symbol else f"{symbol}.NS"
    h = yf.download(tk, period="730d", interval="1h", progress=False,
                    auto_adjust=False)
    if h is None or h.empty:
        return pd.DataFrame()
    if isinstance(h.columns, pd.MultiIndex):
        h.columns = h.columns.get_level_values(0)
    h.columns = [str(c).lower() for c in h.columns]
    return h[[c for c in ("open", "high", "low", "close", "volume") if c in h.columns]]


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _cached_daily_max(symbol: str) -> "pd.DataFrame":
    """Full listed daily history for the timeframe board. The page's own `df`
    is a short analysis window (~1y), which starves Half-yearly / Yearly / Y-on-Y
    of bars — those panels refused with "1.2y listed" on decades-old names."""
    import yfinance as yf
    tk = symbol if "." in symbol else f"{symbol}.NS"
    d = yf.download(tk, period="max", interval="1d", progress=False,
                    auto_adjust=False)
    if d is None or d.empty:
        return pd.DataFrame()
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d.columns = [str(c).lower() for c in d.columns]
    return d[[c for c in ("open", "high", "low", "close", "volume") if c in d.columns]]


def _board_daily(symbol: str, df: "pd.DataFrame") -> "pd.DataFrame":
    """Longest daily frame available: full history if the download works, else
    the page's window — so a network failure degrades to today's behaviour."""
    try:
        full = _cached_daily_max(symbol)
    except Exception:
        full = pd.DataFrame()
    if full is not None and not full.empty and (df is None or len(full) > len(df)):
        return full
    return df


def render_timeframe_board(symbol: str, df: "pd.DataFrame") -> None:
    """Six horizons of one company, side by side — Hourly to Yearly plus Y-on-Y.

    Perspective, not signal. A daily chart in a downtrend and a yearly chart in a
    decade-long base are both true, and reading either alone is how a position
    gets sized against the wrong picture. No triggers, same stance as the
    momentum meter directly above.

    Lazy behind a button: the hourly panel is a second yfinance download, and
    this page already spends its patience budget on fundamentals and statements.
    """
    st.markdown(rs.section("Six horizons"), unsafe_allow_html=True)
    key = f"tfboard_{symbol}"
    if not st.session_state.get(key):
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("Show 6 horizons", key=f"btn_{key}",
                         width="stretch"):
                st.session_state[key] = True
                st.rerun()
        with c2:
            st.caption(
                "Hourly · Daily · Monthly · Half-yearly · Yearly · Year-on-year, "
                "from one daily download plus one hourly. Runs on request — the "
                "hourly pull is a second network call."
            )
        return

    with st.spinner("Building six horizons..."):
        panels = tfb.build(symbol, daily=_board_daily(symbol, df),
                           hourly=_cached_hourly(symbol))

    for row in (panels[:3], panels[3:]):
        cols = st.columns(3)
        for col, p in zip(cols, row):
            with col:
                st.markdown(f"**{p.name}**")
                if not p.ok:
                    # A stated reason, not an empty box. "Four yearly candles"
                    # would look like a trend and read like one.
                    st.markdown(rs.callout("Not shown.", p.note or "no data",
                                           tone="absent"), unsafe_allow_html=True)
                    continue
                if p.lines:
                    fig = go.Figure()
                    newest = max(p.lines)
                    for label in sorted(p.lines):
                        s_ = p.lines[label]
                        is_now = label == newest
                        fig.add_trace(go.Scatter(
                            x=s_.index, y=s_.values, name=label, mode="lines",
                            line=dict(width=2.6 if is_now else 1.0,
                                      color=rs.TOKENS["accent"] if is_now
                                      else rs.TOKENS["absent"]),
                            opacity=1.0 if is_now else 0.55))
                    fig.add_hline(y=0, line_width=1,
                                  line_color=rs.TOKENS["border_strong"])
                    fig.update_layout(xaxis_title="day of year",
                                      yaxis_title="% from 1 Jan")
                else:
                    d = p.df
                    fig = go.Figure(go.Candlestick(
                        x=d.index, open=d["open"], high=d["high"],
                        low=d["low"], close=d["close"],
                        increasing_line_color=rs.TOKENS["good"],
                        decreasing_line_color=rs.TOKENS["risk"], showlegend=False))
                    fig.update_layout(xaxis_rangeslider_visible=False)
                fig.update_layout(height=260, margin=dict(l=4, r=4, t=6, b=4),
                                  showlegend=bool(p.lines),
                                  legend=dict(font=dict(size=9), orientation="h",
                                              y=-0.22))
                st.plotly_chart(fig, width="stretch",
                                key=f"tf_{symbol}_{p.name}")
                if p.note:
                    st.caption(p.note)

    st.caption(
        "**Context, not a signal.** Half-yearly and yearly are resampled from "
        "daily bars — exact, since an OHLC aggregate of daily bars *is* the true "
        "period candle, and Yahoo offers no interval coarser than 3 months. "
        "Year-on-year rebases every calendar year to its own 1 January, so it "
        "compares SHAPE and says nothing about absolute performance — that is "
        "what the other five panels are for."
    )
    render_horizon_geometry(symbol, df)


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
            if st.button("Compare peers", key=f"btn_{key}", width="stretch"):
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
                lambda s: cached_fetch_ohlcv(s, days=400, enforce_liquidity=False), _nifty,
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
                            width="stretch",
                            key=f"peer_radar_{anchor}")
        except Exception as exc:
            st.warning(f"Radar unavailable: {exc}")

    # ── FP-4 · the "vs anchor" drill ──
    if compare:
        _peer_head_to_head(anchor, compare, df, want_tech)


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


# Two years of sessions for the pattern-metrics panel, plus RSI warm-up.
PM_HISTORY_BARS = 520


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
        # B-107: the per-trade size now passes through the MARKET verdict's
        # throttle before it is shown. The two numbers both already existed —
        # `council.RISK_PER_TRADE_PCT` sizing off the stop, and the verdict's
        # 0/50/100% multiplier plus its max-trades cap — and never met, so a
        # STAND DOWN day ("no size, no exceptions") left this line unchanged.
        # `verdict` and `portfolio_summary` are module-level and computed on
        # every page render, well before any council card is drawn.
        _rec = prisk.reconcile_size(card.size_pct, verdict,
                                    portfolio_summary.get("open_count", 0))
        lines.append(f"{prisk.size_note(_rec)}  ·  **Horizon** {card.horizon}")
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
        st.dataframe(pd.DataFrame(fact_rows), width="stretch", hide_index=True)
        if bundle.has_fundamentals:
            fu = bundle.facts.get("fundamentals", {})
            st.caption("Fundamentals (yfinance): "
                       + " · ".join(f"{k}={v}" for k, v in fu.items() if v is not None))
        else:
            st.caption("No fundamentals available — technical-only verdict.")


CHART_TOOL_PORT = 5001
CHART_SERVER_LOG = Path(__file__).resolve().parent / "logs" / "chart_server.log"


def _chart_server_up(timeout: float = 0.4) -> bool:
    try:
        socket.create_connection(("127.0.0.1", CHART_TOOL_PORT), timeout=timeout).close()
        return True
    except OSError:
        return False


@st.cache_resource(show_spinner=False)
def _chart_server_autostart() -> str:
    """Once per Streamlit process: bring up the Chart Tool (chart_server.py on
    :5001) if nothing is listening there, so `streamlit run dashboard_app.py`
    is the only command needed.

    The child is detached (own process group / session), so Ctrl-C in the
    Streamlit console does not take the chart down — the installed PWA on a
    phone keeps working, and the next desk start finds it already up. Turn the
    behaviour off with the `chart_server_autostart` setting = "0". Output goes
    to tools/logs/chart_server.log; the probe warning in render_chart_tool
    points there when the port stays closed (e.g. Flask not installed).
    """
    if _chart_server_up():
        return "already running"
    if (db.get_setting("chart_server_autostart", "1") or "1") != "1":
        return "disabled"
    import os
    import subprocess
    import time as _time
    script = Path(__file__).resolve().parent / "chart_server.py"
    if not script.is_file():
        return "chart_server.py not found"
    CHART_SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(CHART_SERVER_LOG, "ab")                 # noqa: SIM115 — child owns it
    kw: dict = {"stdout": log_fh, "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL,
                "cwd": str(script.parent)}
    if os.name == "nt":
        kw["creationflags"] = (subprocess.CREATE_NEW_PROCESS_GROUP
                               | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        kw["start_new_session"] = True
    try:
        proc = subprocess.Popen([sys.executable, str(script)], **kw)
    except Exception as e:                                # noqa: BLE001
        return f"launch failed: {e}"
    for _ in range(40):                                   # ≤ 8 s for Flask to bind
        if _chart_server_up(0.2):
            return f"started (pid {proc.pid})"
        if proc.poll() is not None:
            return f"exited with code {proc.returncode} — see {CHART_SERVER_LOG}"
        _time.sleep(0.2)
    return f"launched (pid {proc.pid}), port not open yet"


try:
    _chart_server_autostart()
except Exception:                                         # noqa: BLE001 — never block the desk
    pass


def render_chart_tool(symbol: str, height: int = 620, caption: bool = True,
                      query: str = "") -> bool:
    """Embed the Chart Tool for `symbol`; returns whether it rendered.

    Extracted from the Predictive Analysis page (M4) when the Stock Analyzer
    became a second caller — two copies of the port probe would have drifted.
    The probe matters: `st.iframe` against a dead port renders a silent
    blank rectangle, so the page has to say what's wrong instead.
    """
    chart_sym = symbol if ("." in symbol or symbol.startswith("^")) else f"{symbol}.NS"
    if not _chart_server_up():
        _auto = _chart_server_autostart()
        st.warning(
            f"Chart Tool server (port {CHART_TOOL_PORT}) is not running — the desk "
            f"tried to start it on launch ({_auto}). Check `{CHART_SERVER_LOG}` "
            "or start it by hand with `py tools/chart_server.py`."
        )
        return False
    st.iframe(
        f"http://localhost:{CHART_TOOL_PORT}/?symbol={chart_sym}&tf=1d"
        + (f"&{query}" if query else ""),
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
    """Live P&L + BOTH risk numbers over all open positions. Cheap to call
    repeatedly — cached_fetch_ohlcv handles the network-call caching underneath.

    The arithmetic lives in `portfolio_risk`, not here (B-106). It used to be
    inline and it computed risk from `entry_price - stop_loss`: INITIAL risk,
    frozen at entry, on a page showing live prices. Being inside this file also
    meant it could not be tested, because importing this module runs the app.
    """
    open_pos = db.get_open_positions()
    total_capital = float(db.get_setting("total_capital", "0") or 0)

    def _price(symbol: str):
        df = cached_fetch_ohlcv(symbol, enforce_liquidity=False)
        if df is None or df.empty:
            return None
        last = float(df["close"].iloc[-1])
        prev = float(df["close"].iloc[-2]) if len(df) > 1 else last
        return last, prev

    return prisk.summarise(open_pos, _price, total_capital)


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

    df = cached_fetch_ohlcv(alert["symbol"], enforce_liquidity=False)
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
    # OPEN risk (live price vs stop), not the initial risk this showed until
    # 2026-09-21 — see `portfolio_risk` / B-106. Value, sub-line and tone all come
    # from `prisk.risk_card`, which is tested; the same logic written here would
    # not be. The walrus keeps it inside THIS statement rather than adding a
    # module-level assignment the monolith ratchet would rightly count.
    rs.stat_card(
        "Capital at Risk",
        fmt_pct((_rc := prisk.risk_card(
            portfolio_summary, mvd.CAPITAL_AT_RISK_CAUTION_PCT))[0]).replace("+", ""),
        _rc[1], tone=_rc[2]),
    rs.stat_card(
        "Alerts Triggered", f"{triggered_count}/{len(active_alerts)}",
        "active alerts firing",
        tone="warn" if triggered_count else "neutral"),
]
_slots = dpages.home_header(_ov_cards, current_page == "Home")

# ── Regime + today's verdict — ONE card ───────────────────────────────────────
_show_regime = current_page == "Home"
# B-179: the verdict card and its controls open Home's centre pane.
with _slots.verdict:
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
        # Qullamaggie's switch for momentum longs: NIFTY SMA10 vs SMA20.
        _ml = regime_info.get("momentum_longs")
        if _ml is not None:
            bits.append(f'Momentum longs <b>{"ON" if _ml else "OFF"}</b> — SMA10 '
                        f'<span class="tb-mono">{regime_info["sma10"]:,.0f}</span> '
                        f'{"above" if _ml else "below"} SMA20 '
                        f'<span class="tb-mono">{regime_info["sma20"]:,.0f}</span>')
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

# ── Index + breadth strips — the market context, AFTER the decision (B-162) ───
# Home only: on working pages four charts above the fold would push the page the
# reader navigated to off the first screen. They sat ABOVE the verdict until
# 2026-10-13, which put the day's one decision two-thirds down the first screen.
# Breadth reads `_senti_reading`, the same object the verdict used, so the two
# cannot disagree. Everything else lives in index_strip.py / breadth_strip.py.
if _show_regime:
    with _slots.market:
        istrip.render()
        bstrip.render(_senti_reading)
        st.divider()

# B-161: the ring prints the score IN this colour, so every step must read as
# text (>= 4.5:1). The 600-level steps (#65a30d, #ca8a04, #ea580c) measured
# ~2.9-3.6 on the cream card; the whole scale moved to its 800 level together
# so the gradient stays even.
_SIGNAL_COLORS = {
    "Very Strong": "#166534", "Strong": "#3f6212", "Moderate": "#854d0e",
    "Watch": "#9a3412", "Weak": "#b91c1c",
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


def _card_action_links(sym: str, analyze: bool = True) -> str:
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
    _an = _analyze_url(sym) if analyze else None
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
    # B-101. Deliberately NOT the risk tone: this is not a bearish read, it is
    # the absence of a direction, and colouring it red would make a coil look
    # like a warning.
    "neutral":    ("neutral", "⚖ ", "BILATERAL — direction unknown until it breaks; "
                                    "never counts as confluence either way"),
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
            f'color:#a14a0b;border:1px solid #f0e0cc;margin-left:4px;">'
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
         f'<span style="color:#166534;font-weight:700;margin-right:5px;flex-shrink:0;">✓</span>'
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
                     width="stretch"):
            db.save_scanner_hit(sym, scanner_name, card.get("pattern_type", ""))
            st.toast(f"★ Saved {sym_clean}")
    with _b2:
        if st.button("♥", key=f"sc_wl_{sym}_{scanner_name}_{_kseq}",
                     help=f"Add {sym_clean} to Watchlist",
                     width="stretch"):
            db.add_watchlist_symbol(sym_clean, f"Scanner Hub — {scanner_name}")
            st.toast(f"♥ {sym_clean} → Watchlist")
    with _b3:
        if st.button("↗", key=f"sc_an_{sym}_{scanner_name}_{_kseq}",
                     help=f"Open {sym_clean} in Stock Analyzer",
                     width="stretch"):
            st.session_state["current_page"] = "Stock Analyzer"
            st.session_state["sa_symbol_override"] = sym_clean
            st.rerun()
    with _b4:
        if st.button("⊕", key=f"sc_ro_{sym}_{scanner_name}_{_kseq}",
                     help=f"Add {sym_clean} to Analyzer Roster (batch queue)",
                     width="stretch"):
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
                             width="stretch")
    with c2:
        want_png = st.button("🖼 Build share card", key=f"{key}_png_go",
                             width="stretch")
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
        f'<span class="tb-chip" title="Rank score — 0.45×Overall Rating + 0.30×best scanner '
        f'score (UNMEASURED as a ranking input, B-172) + 0.25×family-capped confluence" '
        f'style="background:{rs.TOKENS["surface_alt"]};'
        f'color:{rs.TOKENS["text_body"]};">score '
        f'{(hit.get("rank_score") or 0):.1f}</span></div>'
        f'{_scanner_source_chips(", ".join(hit["scanners"]))}{warn}')
    card = dict(hit["best_card"] or {})
    card["symbol"] = sym
    card["overall"] = hit.get("overall")
    card["overall_breakdown"] = hit.get("overall_breakdown") or {}
    _render_scanner_card(card, best, header_html=header_html)
    _render_pead_walk(hit.get("pead"))


def _render_pead_walk(walk: dict | None) -> None:
    """The last-4-quarter post-earnings drift walk, under the pipeline card.

    A small fixed GRID, not a card and not a dataframe. This is the one shape
    the cards-not-tables rule does not cover: it is the SAME three measurements
    repeated over four dates for ONE name, and the whole point is reading down a
    column to see whether the drift keeps its sign. Four sub-cards would hide
    exactly that. It stays inside the parent card's column, so the 3-column hit
    grid is untouched.

    `None` (or a walk with no events) renders NOTHING — no placeholder, no
    dashes. A name whose calendar this desk does not have should look like a
    name without the section, not like a name that drifts zero.
    """
    if not walk or not walk.get("events"):
        return
    _m = rs.TOKENS["text_muted"]
    _b = rs.TOKENS["text_body"]

    def _cell(v):
        return (f'<span style="color:{_pct_tone(v)};">'
                f'{"—" if v is None else f"{v:+.1f}%"}</span>')

    rows = ""
    for e in walk["events"]:
        _snap = (f' <span style="color:{_m};" title="event date snapped forward '
                 f'{e["snapped_days"]}d to the first trading session">*</span>'
                 if e.get("snapped_days") else "")
        _run = ("" if e.get("complete") else
                f' <span style="color:{_m};" title="drift window still running '
                f'— the frame ends before +20 sessions">…</span>')
        # The archived-card path (daily_opportunity_cards) round-trips the hit
        # through JSON, where a `date` becomes a string. Both shapes reach this
        # renderer, so format the date only when it still is one.
        _d = e["date"]
        _d = f"{_d:%Y-%m-%d}" if hasattr(_d, "year") else str(_d)[:10]
        rows += (f'<tr><td style="color:{_b};padding:1px 8px 1px 0;">'
                 f'{_d}{_snap}{_run}</td>'
                 f'<td style="text-align:right;padding:1px 8px;">{_cell(e.get("d1"))}</td>'
                 f'<td style="text-align:right;padding:1px 8px;">{_cell(e.get("d5"))}</td>'
                 f'<td style="text-align:right;padding:1px 0 1px 8px;">'
                 f'{_cell(e.get("d20"))}</td></tr>')

    _cons = walk.get("consistency")
    _agree = walk.get("agreeable") or 0
    foot = (f'{_cons}/{_agree} quarters drifted the same way as their reaction bar'
            if _cons is not None and _agree
            else 'not enough completed windows to judge consistency')

    st.markdown(
        f'<div style="margin:-6px 0 10px;padding:7px 10px;border-radius:8px;'
        f'background:{rs.TOKENS["surface_alt"]};font-size:11.5px;">'
        f'<div style="color:{_m};margin-bottom:3px;" '
        f'title="D+1 is the session after the results date — the reaction for a '
        f'post-close announcement. D+5 and D+20 are the drift FROM the '
        f'close of that bar, so the reaction itself is not counted as drift.">'
        f'PEAD walk · last {len(walk["events"])} results</div>'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<tr style="color:{_m};"><td style="padding:1px 8px 1px 0;">results</td>'
        f'<td style="text-align:right;padding:1px 8px;">D+1</td>'
        f'<td style="text-align:right;padding:1px 8px;">→+5</td>'
        f'<td style="text-align:right;padding:1px 0 1px 8px;">→+20</td></tr>'
        f'{rows}</table>'
        f'<div style="color:{_m};margin-top:4px;">{foot} · context only, '
        f'nothing is scored or ranked on it</div></div>',
        unsafe_allow_html=True)


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
# Sector money flow (CMF) — B-60. Shared window, used on Sector Map AND Home.
# ------------------------------------------------------------------------------
# One definition, two mount points, no drift — the same arrangement the Darvas
# window uses. Home renders from the SAME cached frame the page computes and can
# never trigger its own fetch, because Home must stay cheap to open.
#
# A TABLE, deliberately, against the cards-not-tables convention that governs
# Scanner Hub. That convention is about scanner RESULTS, where each hit is an
# object with its own reasons. This is one metric across ~20 sectors and 4 dates
# and the reader's job is to scan a column for the outlier — which is the job
# cards are worst at.
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def _sector_money_flow(universe: str = "nifty500", n: int = 21):
    import money_flow as _mf
    return _mf.sector_grid(universe, n=n)


def _money_flow_window(key_prefix: str, *, compact: bool = False):
    """Render the sector money-flow grid.

    `compact` is the Home mounting: the positive-flow strip only, scan on click.
    """
    import money_flow as _mf

    if compact:
        st.markdown("#### 💸 Sector money flow · positive today")
    else:
        st.markdown("#### 💸 Sector money flow · Chaikin Money Flow")

    # Stored snapshot (scheduled refresh / ↻). Home shows the last run on load
    # and never computes here — the refresh is a background job.
    _mf_meta, grid = snapshot_panel("sector_money_flow", key=key_prefix,
                                    compact=compact)
    if grid is None:
        st.info("No stored money-flow run yet — press ↻ to compute it in the background.")
        return
    if grid.get("error"):
        st.warning(f"Sector money flow unavailable: {grid['error']}")
        return
    df = grid.get("rows")
    if df is None or df.empty:
        st.info("No sector had enough constituents with history to compute.")
        return

    cols = grid["columns"]

    if compact:
        pos = _mf.positive_sectors(grid, top_n=5)
        if pos.empty:
            st.caption("**No sector is showing positive money flow today.** "
                       "That is a reading, not an absence of one.")
        else:
            st.dataframe(
                pos[["sector", cols[0], "trend"]],
                hide_index=True, width="stretch",
                column_config={
                    cols[0]: st.column_config.NumberColumn("CMF today", format="%.3f"),
                    "trend": st.column_config.TextColumn("Trend"),
                })
        st.caption("Where money went, not where it will go — a reading order, "
                   "not a buy list. Nothing here has been measured.")
        return

    # Full grid: red → white → green, clipped at the practical range so ordinary
    # readings use the whole scale instead of hugging white (CMF is bounded ±1
    # but lives inside roughly ±0.25).
    clip = grid["clip"]
    show = df[["sector", "members"] + cols + ["trend"]]
    styled = show.style.background_gradient(
        cmap="RdYlGn", subset=cols, vmin=-clip, vmax=clip
    ).format({c: "{:.3f}" for c in cols}, na_rep="—")
    st.dataframe(styled, hide_index=True, width="stretch")

    st.caption(
        f"**CMF({grid['n']})** per sector — money-flow volume summed across "
        f"constituents ÷ their summed volume, so a heavyweight counts for what it "
        f"traded rather than one vote. {grid['n_covered']}/{grid['n_symbols']} "
        f"symbols had history. Colour clipped at ±{clip:.2f}."
    )
    st.caption(
        "⚠️ **The four columns are overlapping 21-bar windows** (5 trading days "
        "apart, so consecutive columns share ~16 bars). A row agreeing across all "
        "four is one measurement smeared, **not four confirmations**."
    )
    st.caption(f"⚠️ {grid['caveat']}")
    _thin = df[df["low_coverage"]] if "low_coverage" in df else None
    if _thin is not None and not _thin.empty:
        st.caption("Computed from under half their constituents (read with that "
                   "discount): **" + ", ".join(_thin["sector"]) + "**.")


# ──────────────────────────────────────────────────────────────────────────────
# Sector turnover-share rotation — B-62. Sits DIRECTLY under the money-flow grid.
# ------------------------------------------------------------------------------
# The pairing is the point and the two must not be separated: turnover is
# UNSIGNED, so delta-share says WHERE the attention went and CMF says which side
# of the range it closed on. Read alone, a sector taking share on falling price
# reads as accumulation or distribution with equal ease.
#
# A table for the same reason the CMF grid is one: two metrics across ~20 sectors
# where the job is to scan a column for the outlier. The cards-not-tables
# convention governs scanner RESULTS, where each hit is an object with its own
# reasons — not this.
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def _rs_walk_compute(universe: str = "nifty500", extra: tuple = ()):
    """Compute the universe-wide RS-rank walk and cache it in the DB.

    Expensive (the whole universe, 2y of bars), so it is never called on page
    load — the Watchlist reads the stored grid and offers a button when there is
    none for today. The DB row is a CACHE: the walk is recomputable from price
    history at any time, so a missing run_date costs a recompute, not a hole.

    `extra` are symbols to rank AGAINST the universe without joining it. It
    exists because the first version shipped with an empty column: a personal
    watchlist is made of exactly the small names that are not nifty500
    constituents (7 of 8 here), and a percentile against a universe you are not
    in is still a perfectly good reading — the universe is the yardstick.
    """
    import rs_walk as _rw
    try:
        bench = sp.fetch_nifty50(days=760)
    except Exception:
        bench = None
    extra_hist = {}
    if extra:
        # Batched, not one fetch per symbol: the Scanner Hub can hand this a few
        # hundred names, and 300 sequential downloads is minutes of waiting for
        # a column. Same downloader money_flow and turnover_share already use.
        try:
            import trending_stocks as _ts
            _h = _ts._batch_history(sorted(set(extra)), period="2y")
            extra_hist = {k: v for k, v in (_h or {}).items() if v is not None}
        except Exception as _e:
            _log.warning("rs walk extras batch failed: %s", _e)
    g = _rw.walk_grid(universe, benchmark=bench, extra_hist=extra_hist)
    if not g.get("error") and g.get("ranks"):
        try:
            db.save_rs_walk(g["ranks"], universe=universe)
        except Exception as _e:                              # pragma: no cover
            _log.warning("rs walk save failed: %s", _e)
    return g


def _earn_cols(symbol, df) -> dict:
    """The earnings-reaction group for one row. Cache-only, so it never fetches.

    Returns the five columns plus nothing else — `snapped_days` is deliberately
    NOT surfaced as a column: it would be blank on almost every row and it is a
    property of the measurement rather than of the company. It stays available
    to any caller that wants to caption a snapped reading.
    """
    try:
        import earnings_reaction as _erx
        r = _erx.reaction(str(symbol), df)
    except Exception:
        return {}
    return {
        "next_earn": r["next_earn"],
        "past_earn": r["past_earn"],
        "earn_d_minus_1": r["earn_d_minus_1"],
        "earn_day": r["earn_day"],
        "earn_d_plus_1": r["earn_d_plus_1"],
    }


def _earnings_fill_button(symbols, key: str) -> None:
    """Button that fetches the results CALENDAR for symbols missing from cache.

    `_earn_cols` is cache-only by design — a table render must not fetch. But the
    shipped cache covers ~400 larger names, so on a watchlist of micro-caps the
    whole group renders blank, which is honest and useless. This offers the fetch
    explicitly, with the count, the way the price and pledge columns already do.

    Only MISSING symbols are fetched. A cached calendar is reused whatever its
    age: a past results date does not change, and the next date is captioned as
    of its cache rather than silently refreshed on every render.
    """
    try:
        import earnings_reaction as _erx
        import earnings_calendar as _ecx
    except Exception:
        return
    missing = [s for s in {str(x).strip().upper() for x in symbols}
               if s and s != "—" and _erx._read_any(s) is None]
    if not missing:
        return
    if st.button(f"Fetch earnings dates ({len(missing)} names)",
                 key=f"{key}_earn",
                 help="Results calendar per symbol from yfinance, disk-cached. "
                      "Fills the Next earn. / Past earn. / −1D% / E-day% / +1D% "
                      "columns. Only names with no cached calendar are fetched."):
        ok, errs = 0, []
        prog = st.progress(0.0, text=f"0/{len(missing)}")
        for n, sym in enumerate(missing, 1):
            try:
                if _ecx.fetch_earnings(sym):
                    ok += 1
            except Exception as e:
                errs.append(f"{sym}: {e}")
            prog.progress(n / len(missing), text=f"{n}/{len(missing)}")
        prog.empty()
        if ok:
            st.success(f"Results calendar cached for {ok} of {len(missing)} name(s).")
        else:
            # "Nothing came back" has two very different causes and they must not
            # be reported as one. An earlier version of this message asserted the
            # data-absence explanation outright — and it was WRONG: every symbol
            # was failing because `lxml` was missing, which yfinance reports as an
            # import error swallowed inside fetch_earnings. Blaming micro-cap
            # coverage for a dependency bug would have sent the reader looking in
            # the wrong place, so this now says both and names the check.
            st.warning(
                f"No results calendar returned for any of the {len(missing)} "
                f"name(s). Two possible causes and they need different fixes: "
                f"yfinance may genuinely carry no calendar for these listings, "
                f"**or** the fetch is failing. Check the latter first — "
                f"`py -3 -c \"import lxml\"` must succeed, since yfinance parses "
                f"the earnings table with `pandas.read_html` and returns nothing "
                f"at all when lxml is absent.")
        st.rerun()


def _cap_bucket_map(symbols):
    """{SYMBOL: LC|MC|SC|Mic} from NSE index membership. Free — cached lists.

    Costs no network call in the common case, which is why it is applied to Hub
    tables unconditionally while the price-derived columns sit behind a button.
    """
    try:
        import smallcap_universe as _capu
        return _capu.cap_bucket([str(x) for x in symbols])
    except Exception:
        return {}


def _hub_price_cols(symbols, key: str) -> dict:
    """RSI / % from 20EMA / EMA stack / RS (mom) per symbol, computed ON DEMAND.

    These four need daily bars, and a Hub table can carry 80 names. Computing
    them on every render would make an unrelated widget click pay for 80 fetches,
    so this follows the pattern the page already uses for pledge % and the RS
    walk: a button fills a session-state cache, and the columns appear once it
    has. A table that has not been enriched simply does not show them, which
    reads as "not computed" rather than as "no reading" — the same distinction
    the `rs_walk` column already makes by dropping itself when the grid is empty.

    Cached per table key, because the summary and confluence tables hold
    different symbol sets and one should not silently serve the other's rows.
    """
    store = st.session_state.setdefault("hub_price_cols", {})
    have = store.setdefault(key, {})
    out = {}
    for sym in symbols:
        s_ = str(sym).strip().upper()
        if s_ in have:
            out[s_] = have[s_]
    return out


def _hub_price_fill(symbols, key: str) -> int:
    """Fill the cache above for `symbols`. Returns how many were computed."""
    import row_metrics as _rmx
    store = st.session_state.setdefault("hub_price_cols", {})
    have = store.setdefault(key, {})
    n = 0
    for sym in symbols:
        s_ = str(sym).strip().upper()
        if s_ in have or not s_ or s_ == "—":
            continue
        try:
            # Named by a scan that already applied the liquidity floor, so the
            # floor is moot here — but these arrive BY NAME, and the swept rule
            # is that a by-name caller does not inherit the scan filter.
            df = cached_fetch_ohlcv(s_, enforce_liquidity=False)
        except Exception:
            df = None
        if df is None or len(df) < 30:
            have[s_] = {}
            continue
        # The earnings group rides along on the SAME frame — it is cache-only and
        # costs no extra fetch, so a user who paid for the bars gets it free.
        have[s_] = {
            "rsi": _rmx.rsi(df),
            "pct_from_20ema": _rmx.pct_from_ema(df),
            "ema_stack": _rmx.ema_stack(df),
            "rs_momentum": _wl_rs_mom(df),
            **_earn_cols(s_, df),
        }
        n += 1
    return n


def _hub_enrich(df, symbol_col: str, key: str):
    """Attach Cap (always) and the price columns (when computed) to a Hub table."""
    if df is None or df.empty or symbol_col not in df.columns:
        return df
    syms = [str(x).strip().upper() for x in df[symbol_col]]
    caps = _cap_bucket_map(syms)
    df = df.copy()
    df["cap_bucket"] = [caps.get(s, "") for s in syms]
    px = _hub_price_cols(syms, key)
    if px:
        for col in ("rsi", "pct_from_20ema", "ema_stack", "rs_momentum",
                    "next_earn", "past_earn", "earn_d_minus_1", "earn_day",
                    "earn_d_plus_1"):
            vals = [px.get(s, {}).get(col) for s in syms]
            if any(v is not None for v in vals):
                df[col] = vals
    # Cap and Sector beside the symbol; both are identity, not measurements.
    import sector_column as _sc
    return _sc.attach(df, symbol_col)


def _hub_price_button(symbols, key: str, label: str) -> None:
    """The button that fills `_hub_price_cols` for one table."""
    pending = [s for s in {str(x).strip().upper() for x in symbols}
               if s and s != "—"
               and s not in st.session_state.get("hub_price_cols", {}).get(key, {})]
    if not pending:
        return
    if st.button(f"Add price columns ({len(pending)} names)", key=f"{key}_px",
                 help="Fetches daily bars for these names and adds RSI, "
                      "% from 20EMA, the EMA stack and RS momentum. Cached "
                      "symbols are free; this is why the columns are not "
                      "computed on every render."):
        with st.spinner(f"Reading bars for {len(pending)} names…"):
            got = _hub_price_fill(pending, key)
        st.success(f"{label}: price columns ready for {got} name(s).")
        st.rerun()


@st.cache_data(ttl=600, show_spinner=False)
def _svp_screen_lookup() -> dict:
    """The SVP screen file, read-only. `{}` when it has never been built.

    Cached briefly rather than not at all: it is a 500-row CSV read, cheap but
    pointless to repeat per table on one page. Read through `svp_screen`, which
    exposes STRUCTURE only — the composite score and its direction measured a
    clean negative on 2026-08-29 and stay off these tables.
    """
    try:
        import svp_screen as _svp
        return _svp.load()
    except Exception as _e:                                  # pragma: no cover
        _log.warning("svp screen unavailable: %s", _e)
        return {}


def _cols_mod():
    """The shared column registry (B-63a) — imported lazily, like every other
    heavy tool module on this page."""
    import columns as _cols
    return _cols


@st.cache_data(ttl=1800, show_spinner=False)
def _sector_turnover_share(universe: str = "nifty500"):
    import turnover_share as _tsx
    return _tsx.rotation_grid(universe)


def _turnover_share_window(key_prefix: str = "tsh_page"):
    """Render the sector turnover-share rotation grid."""
    st.markdown("#### 🔄 Sector rotation · share of market turnover")

    _ts_meta, grid = snapshot_panel("sector_turnover_share", key=key_prefix)
    if grid is None:
        st.info("No stored turnover-share run yet — press ↻ to compute it in the background.")
        return
    if grid.get("error"):
        st.warning(f"Turnover share unavailable: {grid['error']}")
        return
    df = grid.get("rows")
    if df is None or df.empty:
        st.info("No sector had enough constituents with history to compute.")
        return

    show = df[["sector", "members", "turnover_cr", "share_pct",
               "d_share_d", "d_share_w"]]
    styled = _cols_mod().formatted(show.style.background_gradient(
        cmap="RdYlGn", subset=["d_share_d", "d_share_w"], vmin=-3.0, vmax=3.0
    ))  # numbers are formatted by columns.py, not here — one formatter, not two
    st.dataframe(
        styled, hide_index=True, width="stretch",
        column_config=_cols_mod().configure_df(show))

    st.caption(
        f"**Rotation in money, not price.** Each sector's turnover as a share of "
        f"the universe's, and the change in that share in percentage points. "
        f"{grid['n_covered']}/{grid['n_symbols']} symbols across "
        f"{grid['n_sectors']} sectors."
    )
    st.caption(
        "**Zero-sum by construction** — the shares sum to 100%, so the Δ column "
        "sums to zero and every sector that gains attention takes it from named "
        "others. A sector-return column has no such constraint: on a broad day "
        "everything is green and the ranking says little."
    )
    st.caption(f"⚠️ {grid['unsigned_note']}")
    st.caption(f"⚠️ {grid['turnover_note']}")
    st.caption("A VIEW, not a signal — no entry, stop or target, and **nothing "
               "here has been measured**. The prior is low: turnover spikes on "
               "news, index rebalances, block deals and expiry, none of which is "
               "rotation in the sense a trader means.")
    _thin = df[df["low_coverage"]] if "low_coverage" in df else None
    if _thin is not None and not _thin.empty:
        st.caption("Computed from under half their constituents (read with that "
                   "discount): **" + ", ".join(_thin["sector"]) + "**.")


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
# Home must stay cheap to open, so nothing is fetched here: the window reads the
# STORED volume-shockers snapshot and only ↻ (a background job) recomputes it.
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
    # Do NOT overwrite the scan's own trade_date — when the yfinance overlay led,
    # it is TODAY's session and the bhavcopy's date would report it as stale.
    _r.setdefault("trade_date", None)
    if not _r.get("trade_date"):
        _r["trade_date"] = _trend_bhav()[1]
    return _r


@st.cache_data(ttl=1800, show_spinner=False)
def _darvas_from_snapshot(run_at: str, top_n: int, vol_mult: float, move_pct: float,
                          min_turnover_cr: float):
    """The Darvas scan at non-default thresholds, off the STORED bhavcopy frame
    (`run_at` keys the cache to the snapshot, so a refresh recomputes)."""
    import trending_stocks as _ts
    _, payload = snapstore.load_latest("volume_shockers")
    bhav = None if payload is None else payload.get("bhav")
    if bhav is None:
        return {"error": "no stored bhavcopy frame", "rows": None}
    _r = _ts.darvas_volume_shockers(
        bhav, top_n=top_n, vol_mult=vol_mult, move_pct=move_pct,
        min_turnover=float(min_turnover_cr) * 1e7)
    _r.setdefault("trade_date", None)
    if not _r.get("trade_date"):
        _r["trade_date"] = payload.get("bhav_date")
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
    import sector_column as _sc
    out = _sc.attach(df.copy(), "symbol")
    out = _with_chart_family(out, "symbol")
    import columns as _cols
    cfg = dict(_chart_family_colcfg())
    # One definition per column (B-63a). `multiple` resolves to the shared
    # `rvol` spec — the same ratio this table labelled "x SMA10" and the
    # trending tables labelled "x avg vol".
    cfg.update(_cols.configure_df(out))
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

    _show = _cols.formatted(out.style.map(_chg_color, subset=["chg_pct"]))
    _sel = st.dataframe(_show, width="stretch", hide_index=True, column_config=cfg,
                        key=f"{key_prefix}_tbl", on_select="rerun",
                        selection_mode="multi-row")
    try:
        _rows = list(_sel.selection.rows)
    except Exception:
        _rows = []
    _picked = [str(df.iloc[i]["symbol"]) for i in _rows if i < len(df)]

    _wc1, _wc3, _wc2 = st.columns([1, 1, 2])
    with _wc3:
        _pa_send_button(key_prefix, "Volume Shockers · Darvas", df, "symbol",
                        note_fn=lambda r: " · ".join(
                            x for x in (
                                f"{r.get('multiple')}x vol" if r.get("multiple") is not None else "",
                                f"{float(r.get('chg_pct') or 0):+.1f}%" if r.get("chg_pct") is not None else "",
                                str(r.get("dir") or ""),
                            ) if x))
    with _wc1:
        if st.button(f"♥ Add {len(_picked) or ''} to watchlist".replace("  ", " "),
                     key=f"{key_prefix}_addwl", disabled=not _picked,
                     width="stretch", type="primary" if _picked else "secondary"):
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

    `compact` is the Home mounting: no sliders, the stored snapshot at the
    default thresholds. Both mountings read the persisted snapshot; ↻ queues a
    background recompute (see snapshot_panel).
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

    # The scan reads the STORED volume-shockers snapshot: the bhavcopy frame
    # plus the default-threshold result. Default sliders → the stored result,
    # no compute; any other setting re-runs the scan off the stored bhavcopy.
    _vs_meta, _vs_payload = snapshot_panel("volume_shockers", key=key_prefix,
                                           compact=compact)
    if _vs_payload is None:
        st.info("No stored volume-shocker run yet — press ↻ to scan in the background.")
        return

    if compact:
        _top, _mult, _move, _minto = 60, 2.0, 5.0, 0.0
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

    _dp = _vs_payload.get("default_params") or {}
    if (int(_top), float(_mult), float(_move), float(_minto)) == (
            _dp.get("top_n"), _dp.get("vol_mult"), _dp.get("move_pct"),
            _dp.get("min_turnover_cr")):
        _res = _vs_payload["default"]
    else:
        with st.spinner("Re-scanning the stored bhavcopy at these thresholds…"):
            _res = _darvas_from_snapshot(_vs_meta.run_at, int(_top), float(_mult),
                                         float(_move), float(_minto))

    if _res.get("error"):
        st.warning(f"Scan unavailable: {_res['error']}")
        return

    # Which source actually supplied today's row decides whether this list is
    # comparable to Chartink at all, so it is stated first and in the open rather
    # than buried in a tooltip. yfinance leads; the bhavcopy is the floor beneath
    # it, and any name yfinance could not freshen is still reading EOD.
    _ov = _res.get("overlay") or {}
    _n_live = int(_ov.get("n_overlaid") or 0)
    if _n_live:
        _src = (f"**{_n_live}** of {_ov.get('n_asked', 0)} scanned names on live "
                f"yfinance bars, the rest on the NSE EOD bhavcopy "
                f"({_ov.get('bhav_date') or '—'}).")
    else:
        _src = ("NSE EOD bhavcopy — yfinance had nothing newer, so this is the "
                "last completed session.")
    st.caption(f"Session **{_res.get('trade_date') or '—'}**. " + _src +
               " Chartink runs intraday — compare like sessions before "
               "concluding the filters differ.")
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
               "promoter conduct, pledge penalty) from free NSE shareholding data. "
               "Quality overlay adds ROCE / OPM / D/E from yfinance and runs the "
               "FR-4 red-flag checklist, which can **veto** on governance flags "
               "(negative FCF only penalises — B-34r2). "
               "**Unvalidated** — a discovery lens, not an edge. B-34r4 measured "
               "the ranking at −0.12% @60d (p=0.94) / +0.20% @120d (p=0.94) once "
               "the drifting promoter window is bounded — the earlier +2.5% was "
               "that artefact. Coverage, not edge.")
    
    # Beginner-friendly help
    help_panels.render("hidden_treasures")
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
        _ht_veto = st.checkbox("Red-flag veto", value=False, key="ht_veto",
                               disabled=not _ht_enrich,
                               help="OFF by default since B-34r5: measured across two "
                                    "universes, the first governance-flagged name ranks "
                                    "128th (Smallcap-250) and 60th (Microcap-250), so the "
                                    "gate cannot reach a list of 100 or fewer. Flagged "
                                    "names are MARKED in the cards instead. Turn it on to "
                                    "drop them outright.")
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
                # Always store the top 100 (the slider's max) so every "Show
                # top N" position is served from the stored run below.
                _ht_live = scd.discover(kind=_ht_kind_val, limit=100,
                                        enrich=_ht_enrich,
                                        veto_critical=_ht_veto)
                _ht_today = date.today().isoformat()
                _saved_n = db.save_hidden_treasures_run(
                    _ht_live["hits"],
                    universe_kind=_ht_kind_val,
                    universe_size=_ht_live.get("universe", 0),
                    run_date=_ht_today)
                db.save_hidden_treasures_meta(_ht_today, {
                    "universe_kind": _ht_kind_val,
                    "universe": _ht_live.get("universe", 0),
                    "scanned": _ht_live.get("scanned", 0),
                    "cached": _ht_live.get("cached", 0),
                    "veto_active": _ht_live.get("veto_active", False),
                    "vetoed": _ht_live.get("vetoed") or [],
                    "enrich": bool(_ht_enrich), "source": "manual"})
                st.session_state["ht_run_date"] = _ht_today
                st.toast(f"💾 {_saved_n} hits saved to history")
            except Exception as _e:
                st.error(f"Discovery failed: {_e}")

    # ── The list shown is always a STORED run ─────────────────────────────────
    # Discover above and the scheduled Hidden Treasures job (Scheduler Hub)
    # both write the hidden_treasures table, so the page opens on the latest
    # run instead of an empty screen, and older runs stay one pick away. The
    # table keeps one run per date: a Discover replaces that day's run.
    _ht_res = None
    _ht_dates = db.get_hidden_treasures_dates()
    _kind_label = {v: k for k, v in _kind_map.items()}
    if _ht_dates:
        if st.session_state.get("ht_run_date") not in _ht_dates:
            st.session_state["ht_run_date"] = _ht_dates[0]

        def _ht_date_label(d):
            _m = db.get_hidden_treasures_meta(d)
            _parts = [d]
            if _m.get("universe_kind"):
                _parts.append(_kind_label.get(_m["universe_kind"], _m["universe_kind"]))
            if _m.get("source"):
                _parts.append(_m["source"])
            return " · ".join(_parts)

        _ht_sel = st.selectbox("Stored run", _ht_dates, key="ht_run_date",
                               format_func=_ht_date_label,
                               help="Written by Discover and by the scheduled "
                                    "Hidden Treasures job. One run per date.")
        _ht_cards = db.get_hidden_treasures_run(_ht_sel)
        _ht_meta = db.get_hidden_treasures_meta(_ht_sel)
        if _ht_cards:
            _ht_res = {
                "hits": _ht_cards[:_ht_limit],
                "universe": _ht_meta.get("universe", len(_ht_cards)),
                "cached": _ht_meta.get("cached"),   # None on runs stored before meta
                "scanned": _ht_meta.get("scanned", len(_ht_cards)),
                "vetoed": _ht_meta.get("vetoed") or [],
                "veto_active": _ht_meta.get("veto_active", False),
            }
            if _ht_meta.get("universe_kind") and _kind_map.get(_ht_kind) != _ht_meta["universe_kind"]:
                st.caption(f"Showing the stored **{_kind_label.get(_ht_meta['universe_kind'], _ht_meta['universe_kind'])}** "
                           f"run. Press Discover to run **{_ht_kind}** instead.")
    else:
        st.info("No stored run yet. Press **Discover**, or register the Hidden "
                "Treasures job in Scheduler Hub (Ops) to run it after each close.",
                icon="ℹ️")

    if _ht_res is not None:
        # The veto is the only HARD gate in this lane, so what it removed has to
        # be visible. A silent exclusion is indistinguishable from a name that was
        # never in the universe, and this one drops a large minority of it.
        _ht_vetoed = _ht_res.get("vetoed") or []
        _ht_marked = sum(1 for _h in _ht_res["hits"]
                         if (_h.get("red_flags") or {}).get("vetoed"))
        if not _ht_res.get("veto_active"):
            st.info(
                f"Red-flag veto is OFF — flagged names are **marked, not removed** "
                f"({_ht_marked} in this list). B-34r5 measured the gate as unable to "
                f"reach a top-100: the score already costs −15 for promoter selling and "
                f"−20 for pledge, so a flagged name does not rank that high. Removing "
                f"them looked like protection the list was not actually getting.",
                icon="ℹ️")
        elif _ht_vetoed:
            _ht_total = len(_ht_vetoed) + _ht_res["scanned"]
            st.warning(
                f"**{len(_ht_vetoed)} of {_ht_total}** scoreable names vetoed on a "
                f"vetoing red flag — promoter selling, pledge, or heavy dilution. "
                f"Negative FCF is a penalty rather than a veto (B-34r2): it caused "
                f"most exclusions, could not be backtested point-in-time, and is "
                f"often a reinvesting small-cap's business model.", icon="⛔")
            with st.expander(f"Vetoed — {len(_ht_vetoed)} names and why", expanded=False):
                for _v in _ht_vetoed[:60]:
                    st.markdown(
                        f"**{_v['symbol']}** ({_v.get('name') or '—'}) · would have "
                        f"scored {_v['score']}  \n"
                        + "  \n".join(f"&nbsp;&nbsp;⛔ {_r}" for _r in _v["reasons"]),
                        unsafe_allow_html=True)
                if len(_ht_vetoed) > 60:
                    st.caption(f"…and {len(_ht_vetoed) - 60} more.")
        _ht_cached_txt = (f" ({_ht_res['cached']} cached)"
                          if _ht_res.get("cached") is not None else "")
        st.markdown(rs.section(f"Top {len(_ht_res['hits'])} of {_ht_res['universe']}"
                               f"{_ht_cached_txt}"),
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

                    # B-34r5: with the gate off, a flagged name stays in the list and
                    # says so on its own card. The count in the banner is a summary;
                    # this is what tells you WHICH name and WHY, at the point of use.
                    _rf_h = _h.get("red_flags") or {}
                    _flag_s = ""
                    if _rf_h.get("vetoed"):
                        _why = "; ".join(f["label"] for f in (_rf_h.get("veto_flags") or []))
                        _flag_s = (f'<div style="font-size:11px;color:{rs.TOKENS["risk"]};'
                                   f'font-weight:600;">⛔ {_why or "critical red flag"}</div>')

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
                            f'color:#a14a0b;border:1px solid #f0e0cc;margin-left:4px;">'
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
                            f'{_qual_chips}{_mcap_s}{_pledge_s}{_flag_s}',
                            emphasis=False),
                        unsafe_allow_html=True)

                    _b1, _b2 = st.columns(2)
                    with _b1:
                        if st.button("♥ Watchlist", key=f"ht_wl_{_sym}", width="stretch"):
                            db.add_watchlist_symbol(_sym, "Hidden Treasures")
                            st.toast(f"♥ {_sym} → Watchlist")
                    with _b2:
                        if st.button("↗ Analyze", key=f"ht_an_{_sym}", width="stretch"):
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

    # Stored snapshot first (scheduled / ↻): at the page defaults every lens
    # reads the stored run and nothing is fetched. Move a slider and that lens
    # computes live, exactly as before.
    _tr_meta, _tr_snap = snapshot_panel("trending", key=key_prefix)
    _TR_DEFAULTS = (15, 200, 5.0)
    if _tr_snap is not None:
        _tr_bhav, _tr_date = True, _tr_snap.get("bhav_date")
    else:
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
        _at_defaults = (_tr_snap is not None
                        and (int(_tr_top), int(_tr_uni), float(_tr_minto)) == _TR_DEFAULTS)
        st.caption(f"Session **{_tr_date or '—'}**"
                   + (" · stored snapshot" if _at_defaults else
                      " · live compute (sliders off default)" if _tr_snap is not None
                      else f" · {len(_tr_bhav):,} EQ rows"))

        def _lens_movers():
            return (_tr_snap["movers"] if _at_defaults
                    else _trend_movers(_tr_top, float(_tr_minto) * 1e7))

        def _lens_volume():
            if _at_defaults and _tr_snap.get("volume") is not None:
                return _tr_snap["volume"]
            return _trend_volume(_tr_top)

        def _lens_extremes():
            return (_tr_snap["extremes"] if _at_defaults
                    else _trend_extremes(_tr_uni, _tr_top, 2.0))

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
            import sector_column as _sc
            out = _sc.attach(df.copy(), "symbol")
            out = _with_chart_family(out, "symbol")
            import columns as _cols
            colcfg = dict(_chart_family_colcfg())
            # Raw-rupee turnover is RENAMED on conversion rather than aliased:
            # `turnover` and `turnover_cr` differ by 1e7, and columns.py refuses
            # to treat them as one id for exactly that reason.
            if "turnover" in out.columns:
                out["turnover_cr"] = out["turnover"] / 1e7
                out = out.drop(columns=["turnover"])
            # The live movers lens carries the PREVIOUS session's traded value
            # beside a live price (yfinance intraday volume is not an NSE traded
            # value). It keeps its own labels rather than borrowing the shared
            # turnover id — the whole point of the rename is that a reader can
            # see which number is a day old.
            if "turnover_prev" in out.columns:
                out["turnover_prev"] = out["turnover_prev"] / 1e7
            colcfg.update(_cols.configure_df(out))
            # Bespoke to this lens and used nowhere else, so left inline rather
            # than promoted to a shared id no other table would ask for.
            for c, lbl, fmt in (("range_high", "High", "%.2f"),
                                ("range_low", "Low", "%.2f"),
                                ("turnover_prev", "Turnover ₹Cr (prev)", "%.2f"),
                                ("volume_prev", "Volume (prev)", "%d")):
                if c in out.columns:
                    colcfg[c] = st.column_config.NumberColumn(lbl, format=fmt)
            drop = [c for c in ("reasons", "avg_volume", "baseline_days", "trade_date",
                                "n_deals", "churn_share", "pct_mcap", "bars") if c in out.columns]
            out = out.drop(columns=drop)
            st.dataframe(out, width="stretch", hide_index=True, column_config=colcfg)

        with _t_mv:
            _mv = _lens_movers()
            st.caption(f"**{_mv['n_filtered']:,}** of {_mv['n_universe']:,} names clear "
                       f"the ₹{_tr_minto:.0f} Cr turnover floor.")
            # Three disclosures, all of which were missing when the list was
            # showing a −3.22% "worst loser" against a real cross-section that
            # held −17% names (fixed 2026-09-11):
            #   what the % is measured from, how wide the universe is, and
            #   which of the two sources actually produced these rows.
            if _mv.get("source") == "yfinance_realtime":
                st.caption(
                    f"Live prices (yfinance intraday) vs the **previous session "
                    f"close** from the {_mv.get('bhav_date') or '—'} bhavcopy — the "
                    f"overnight gap is included. Ranked within the **top "
                    f"{_mv.get('universe_n', 0)} names by traded value**, so this is "
                    f"the worst of the most-traded, not of the whole market. "
                    f"Turnover and volume are that previous session's.")
            else:
                st.caption("**EOD bhavcopy** — the live intraday feed was "
                           "unreachable, so these are last session's closes.")
            st.markdown("**Top gainers**")
            _tr_table(_mv["gainers"])
            st.markdown("**Top losers**")
            _tr_table(_mv["losers"])
            # The caveat belongs ON the page, not in a wiki drawer. B-67,
            # tools/movers_edge.py, 1,215 sessions of NIFTY-500 (2021-2026).
            st.caption(
                ":grey[**Measured 2026-09-11: neither list predicts anything.** "
                "Against the same day's own liquid universe, the losers list "
                "returned **−0.03% at 5 days** (rotation p=0.92) and the gainers "
                "list −0.15% (p=0.53) — a clean null on 1,215 sessions, with the "
                "planted-effect control confirming the test can see an edge when "
                "one exists. These are **attention lists**: a starting point for "
                "'why did this move?', not a shortlist.]")

        def _render_anomaly_spikes():
            with st.spinner("Attributing volume spikes to a cause…"):
                _vol = _lens_volume()
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

                # B-37: volume share-card export
                _vol_rows = _vol.get("raw", {}).get("rows") or _vol.get("rows")
                if _vol_rows is not None and not (hasattr(_vol_rows, "empty") and _vol_rows.empty):
                    _vol_list = (_vol_rows.to_dict("records")
                                 if hasattr(_vol_rows, "to_dict") else _vol_rows)
                    if _vol_list:
                        _vc1, _vc2 = st.columns([1, 2])
                        with _vc1:
                            _want_vs = st.button("🖼 Build volume share card",
                                                 key=f"{key_prefix}_vs_card",
                                                 width="stretch")
                        with _vc2:
                            _vs_top = st.slider("Names on card", 1, 2, 2,
                                                key=f"{key_prefix}_vs_top",
                                                help="The card shows one or two stocks.")
                        if _want_vs:
                            with st.spinner("Rendering volume story card…"):
                                try:
                                    _names = _company_names()
                                    def _q_fn(sym):
                                        try:
                                            return cached_fundamentals_deep(sym).get("quarters", [])
                                        except Exception:
                                            return []
                                    def _mc_fn(sym):
                                        try:
                                            f = cached_fetch_fundamentals(sym)
                                            return f.get("market_cap")
                                        except Exception:
                                            return None
                                    _vs_stocks = orep.volume_stocks_from_scan(
                                        _vol_list,
                                        fundamentals_fn=_q_fn,
                                        name_fn=lambda s: _names.get(s, s),
                                        mcap_fn=_mc_fn,
                                        top_n=_vs_top,
                                    )
                                    if _vs_stocks:
                                        _td = _vol.get("trade_date") or _vol.get("raw", {}).get("trade_date")
                                        _as_of = None
                                        if _td:
                                            try:
                                                _as_of = date.fromisoformat(str(_td)[:10])
                                            except (ValueError, TypeError):
                                                _as_of = None
                                        _vs_png = orep.render_volume_story(_vs_stocks, as_of=_as_of)
                                        st.image(_vs_png, width="stretch")
                                        _stamp = (_as_of or date.today()).isoformat()
                                        st.download_button(
                                            f"⬇ volume-story-{_stamp}.png", _vs_png,
                                            file_name=f"volume-story-{_stamp}.png",
                                            mime="image/png", type="primary",
                                            key=f"{key_prefix}_vs_dl")
                                    else:
                                        st.info("No stocks have enough data for a card.")
                                except Exception as _e:
                                    st.error(f"Card render failed: {_e}")

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
                _ext = _lens_extremes()
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
                _ext = _ext or _lens_extremes()
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
                 key: str, *, empty: str = "", tickers: bool = False) -> None:
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
                                             width="stretch"):
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
            if tickers:
                for a, b in rows[:3]:
                    _sub = str(b).replace("&middot;", "·")
                    if st.button(f"**{a}** :gray[{_sub}]", key=f"am_{key}_{a}",
                                 type="tertiary", help=f"Open {a} in Predictive Analysis"):
                        st.session_state["pa_symbol"] = a
                        st.session_state["current_page"] = "Predictive Analysis"
                        st.rerun()
                return
            cells = "".join(
                f'<div style="background:{t["surface_alt"]};border-radius:6px;'
                f'padding:7px 10px;margin-bottom:6px;">'
                f'<div style="font-size:12.5px;font-weight:700;color:{t["text"]};">'
                f'{a}</div>'
                f'<div style="font-size:10px;color:{t["text_muted"]};">{b}</div></div>'
                for a, b in rows[:3])
            st.markdown(cells, unsafe_allow_html=True)


def _render_institutional_volume(key_prefix: str) -> None:
    """PPV bars with RVOL >= 5x in the last 5 trading sessions."""
    t = rs.TOKENS
    st.markdown(
        f'<div style="font-size:11px;font-weight:700;letter-spacing:.08em;'
        f'text-transform:uppercase;color:{t["text_muted"]};padding-top:6px;">'
        f'Institutional volume (last 5 sessions &middot; PPV &ge; 5x RVOL)'
        f'</div>',
        unsafe_allow_html=True)
    st.caption("Pocket pivot bars where volume exceeded 5x the 50-day average. "
               "Context, not a signal — measured edge is zero (ppv_edge_study).")

    # Stored snapshot (written by the 16:30 job or ↻); the ~500-name scan
    # never runs on page load.
    _iv_meta, _iv_snap = snapshot_panel("institutional_volume", key=key_prefix,
                                        compact=True, button_label="↻ Rescan nifty500")
    if _iv_snap is None:
        st.info("No stored scan yet — press ↻ to scan nifty500 in the background.")
        return

    df = _iv_snap.get("df")
    if df is None or (hasattr(df, "empty") and df.empty):
        st.info("No PPV bars with RVOL >= 5x found in the last 5 sessions.")
        return

    import columns as _cols
    import sector_column as _sc

    out = df.copy()
    out = out.rename(columns={"change_pct": "chg_pct"})
    out = _sc.attach(out, "symbol")
    out = _with_chart_family(out, "symbol")

    display_cols = ["symbol", "date", "close", "chg_pct", "rvol",
                    "sector"] + _CHART_FAMILY_COLS
    out = out[[c for c in display_cols if c in out.columns]]

    cfg = dict(_chart_family_colcfg())
    cfg.update(_cols.configure_df(out))

    def _chg_color(v):
        if v is None or pd.isna(v):
            return ""
        return (f"color:{t['good']};font-weight:600" if v > 0
                else f"color:{t['risk']};font-weight:600" if v < 0
                else "")

    styled = _cols.formatted(out.style.map(_chg_color, subset=["chg_pct"]))
    st.dataframe(styled, width="stretch", hide_index=True,
                 column_config=cfg, key=f"{key_prefix}_tbl")

    _pa_send_button(key_prefix, "Institutional volume · PPV ≥ 5x RVOL", out, "symbol",
                    note_fn=lambda r: f"{r.get('rvol', '')}x rvol · "
                                      f"{float(r.get('chg_pct') or 0):+.1f}% · {r.get('date', '')}")


def _render_cpr_vp(key_prefix: str) -> None:
    """Home › CPR × Volume Profile confluence — stored scan, ↻ in the background."""
    import cpr_vp as _cv
    t = rs.TOKENS
    st.markdown(
        f'<div style="font-size:11px;font-weight:700;letter-spacing:.08em;'
        f'text-transform:uppercase;color:{t["text_muted"]};padding-top:6px;">'
        f'CPR &times; Volume Profile (last bar &middot; top-turnover names)'
        f'</div>',
        unsafe_allow_html=True)
    st.caption("Where yesterday's Central Pivot Range meets the 60-bar volume profile: "
               "names whose CPR band sits inside a high-volume node, or whose last bar "
               "held above / retested / rejected the band with volume. Context, not a "
               "signal — none of these setups has been measured here.")

    _meta, _snap = snapshot_panel("cpr_vp_scan", key=key_prefix, compact=True,
                                  button_label="↻ Rescan")
    if _snap is None:
        st.info("No stored scan yet — press ↻ to scan the top-turnover names in the background.")
        return
    rows = _snap.get("rows") or []
    if not rows:
        st.info(f"Nothing fired on the last bar across {_snap.get('scanned_n', 0)} names — "
                "a quiet reading, which is normal.")
        return

    import columns as _cols
    import sector_column as _sc
    out = pd.DataFrame(rows)
    out = _sc.attach(out, "Symbol")
    out = _with_chart_family(out, "Symbol")
    show_cols = ["Symbol", "Close", "Chg %", "RVOL", "CPR", "Band", "Confluence",
                 "Setups", "Bias", "sector"] + _CHART_FAMILY_COLS
    out = out[[c for c in show_cols if c in out.columns]]
    cfg = dict(_chart_family_colcfg())
    cfg.update(_cols.configure_df(out))

    def _bias_color(v):
        return (f"color:{t['good']};font-weight:600" if v == "bullish"
                else f"color:{t['risk']};font-weight:600" if v == "bearish"
                else f"color:{t['text_muted']}" if v == "mixed" else "")

    def _chg_color(v):
        if v is None or pd.isna(v):
            return ""
        return (f"color:{t['good']};font-weight:600" if v > 0
                else f"color:{t['risk']};font-weight:600" if v < 0 else "")

    styled = _cols.formatted(out.style.map(_chg_color, subset=["Chg %"]).map(_bias_color, subset=["Bias"]))  # B-164
    st.dataframe(styled, width="stretch", hide_index=True, column_config=cfg,
                 key=f"{key_prefix}_tbl")
    st.caption(f"{len(rows)} of {_snap.get('scanned_n', '?')} names scanned · "
               f"setups: {', '.join(_cv.SETUP_LABELS.values())}.")
    _pa_send_button(key_prefix, "CPR × Volume Profile", out, "Symbol",
                    note_fn=lambda r: " · ".join(x for x in (
                        str(r.get("Setups") or r.get("Confluence") or ""),
                        f"RVOL {r.get('RVOL')}x" if r.get("RVOL") is not None else "") if x))


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
        if st.button("Open full map", key="am_full", width="stretch"):
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
        # A run that is merely "not today" is normal before the 16:20 job fires.
        # A run with a whole weekday between it and today means the job did NOT
        # fire — which is how the shortlist silently aged a week (2026-09-07 →
        # 09-14) while this caption read like a timing note. Count the weekdays
        # strictly between the two dates: one or more is a missed session, and
        # that is a red chip naming the job, not a grey caption.
        try:
            _missed = len(pd.bdate_range(
                pd.Timestamp(_run) + pd.Timedelta(days=1),
                pd.Timestamp(date.today()) - pd.Timedelta(days=1)))
        except Exception:
            _missed = 0
        if _missed >= 1:
            st.markdown(
                rs.callout(
                    f"Shortlist is stale — {_missed} session(s) missed since {_run}.",
                    "The TradingBramha-OpportunityDaily job did not run. Check it on "
                    "the Scheduler Hub (Ops) or run the Hub by hand. Price levels "
                    "decay; these names are history until it does.",
                    tone="risk"),
                unsafe_allow_html=True)
        else:
            st.caption(f"Newest stored run is **{_run}**, not today - these are that "
                       f"day's names. Price levels decay; treat them as history.")

    # Row 1 - the shortlist, its sectors, its strongest movers
    c1, c2, c3 = st.columns(3)

    _rank_rows = [(r["symbol"], _nm(r["symbol"]) or f"score {r['score']:.0f}")
                  for _, r in _df.sort_values("rank").head(3).iterrows()]
    _action_card(c1, "Today's shortlist",
                 "Ranked across every scanner by the stored daily run.",
                 _rank_rows, "Opportunity Hub", "rank", tickers=True)

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
                 _mom_rows, "Opportunity Hub", "mom", tickers=True)

    # Row 2 - rating, confluence, what actually fired
    c4, c5, c6 = st.columns(3)

    _rat_rows = []
    if "overall_rating" in _df.columns:
        _rat_rows = [(r["symbol"], f"M1 rating {r['overall_rating']:.0f}/100")
                     for _, r in _df.sort_values("overall_rating", ascending=False).head(3).iterrows()
                     if pd.notna(r.get("overall_rating"))]
    _action_card(c4, "Highest rated",
                 "The M1 technical Overall Rating - a different lens from the "
                 "shortlist score.", _rat_rows, "Predictive Analysis", "rat", tickers=True)

    _conf_rows = []
    if "confluence" in _df.columns:
        _conf_rows = [(r["symbol"], f"{int(r['confluence'])} scanners agree")
                      for _, r in _df.sort_values("confluence", ascending=False).head(3).iterrows()
                      if pd.notna(r.get("confluence"))]
    _action_card(c5, "Most confluence",
                 "Most scanners firing on one name. Measured co-fire lift is "
                 "significant only at 60d - a lead, not an edge.",
                 _conf_rows, "Scanner Hub", "conf", tickers=True)

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

    # B-179: the call-to-action row became the right rail's quick actions, under
    # the account cards. Real buttons rather than styled anchors, because
    # navigation here is session_state + rerun.
    with _slots.right:
        st.caption("Quick actions")
        if st.button("Open screener dashboard", key="home_cta_screen",
                     type="primary", width="stretch"):
            st.session_state["current_page"] = "Opportunity Hub"
            st.rerun()
        if st.button("View top movers", key="home_cta_movers", width="stretch"):
            # The section sits a few screens down, so setting the flag alone
            # looked like a dead button. Also queue a one-shot scroll to it.
            st.session_state["home_trending_open"] = True
            st.session_state["home_trending_scroll"] = True
            st.rerun()
        if st.button("Scanner Hub", key="home_cta_hub", width="stretch"):
            st.session_state["current_page"] = "Scanner Hub"
            st.rerun()
        st.markdown(
            f'<div style="font-size:11px;color:{_t["text_muted"]};margin:8px 0 18px;">'
            f'No sign-in required to browse. '
            f'<b>For research and educational purposes only — not investment advice.</b>'
            f'</div>', unsafe_allow_html=True)

    # B-179: the watchlist roster that closed Home became the left rail.
    with _slots.left:
        dpages.home_rail(db)

    # Centre pane, below the verdict card and market bar the header put there.
    with _slots.centre:
        # ── The action map — stored state only, so it costs nothing on load ──────
        render_action_map()
        st.write("")

        # Home used to be a card grid of every page. It is now a working surface: the
        # scan that was buried three clicks deep, then the roster it feeds. Navigation
        # lives in the top ribbon, where it was already complete.
        _darvas_window("home_vs", compact=True)
        st.write("")

        _mf_col, _iv_col = st.columns(2)
        with _mf_col:
            # Sector money flow, positive side only (B-60). Where the day's names sit in
            # the bigger flow picture -- deliberately AFTER the shockers, because it is
            # context for that list rather than a list of its own. Scan-on-click, same as
            # above: Home never fetches on load.
            _money_flow_window("home_smf", compact=True)
            st.write("")
        with _iv_col:
            # ── Institutional volume (PPV >= 5x RVOL, last 5 sessions) ───────────────
            # Context, not a signal: ppv_edge_study.py showed no forward-return edge at
            # any RVOL threshold. This answers "where did institutions show up" — a
            # screen, not an alert.
            _render_institutional_volume("home_iv")
            st.write("")

        _render_cpr_vp("home_cpr")
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
        st.markdown('<div id="tb-home-movers"></div>', unsafe_allow_html=True)
        st.markdown("#### 📈 What moved today")
        if st.session_state.pop("home_trending_scroll", False):
            # st.markdown strips <script>, so — as with the ⌘K binding — a 1px
            # same-origin iframe reaches into the parent. Retries because the
            # sections above are still painting when it first runs; fails silently.
            st.iframe(
                """
                <script>
                (function () {
                  let n = 0;
                  (function go() {
                    const doc = window.parent.document;
                    const el = doc.getElementById('tb-home-movers');
                    if (el) {
                      // Clear the sticky top ribbon, measured rather than assumed:
                      // it wraps taller on narrow screens.
                      let p = doc.elementFromPoint(window.parent.innerWidth / 2, 5);
                      while (p && getComputedStyle(p).position !== 'sticky') p = p.parentElement;
                      el.style.scrollMarginTop = ((p ? p.getBoundingClientRect().bottom : 0) + 12) + 'px';
                      el.scrollIntoView({block: 'start'});   // smooth was a no-op in stMain
                      return;
                    }
                    if (++n < 40) setTimeout(go, 100);
                  })();
                })();
                </script>
                """,
                height=1,
            )
        _tr_key = "home_trending_open"
        if _tr_key not in st.session_state:
            # Open by default when a stored run exists — showing a snapshot costs
            # no fetch, which is the only thing Home ever refused to do on load.
            st.session_state[_tr_key] = snapstore.latest_meta("trending", ok_only=True) is not None
        if not st.session_state.get(_tr_key):
            _tc_a, _tc_b = st.columns([1, 4])
            with _tc_a:
                if st.button("Load", key="home_trending_btn", width="stretch"):
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

        # ── About this desk — the hero, moved to the foot of Home (B-162) ─────────
        # A landing-page hero is for a first visit; mid-page on a daily-use surface it
        # pushed the scans a full screen down. "Last sentiment" was dropped from its
        # fact row: the verdict card at the top already states that reading.
        try:
            _n_scanners = len(sc.SCANNERS)
        except Exception:
            _n_scanners = None
        st.markdown(
            f'<div style="background:linear-gradient(135deg,{_t["surface_warm"]} 0%,'
            f'{_t["surface_alt"]} 55%,{_t["surface"]} 100%);'
            f'border:1px solid {_t["border_strong"]};border-radius:16px;'
            f'padding:22px 28px;margin:2px 0 14px;">'
            f'<div class="tb-micro" style="color:{_t["accent"]};">TRADING BRAMHA</div>'
            f'<div style="font-size:22px;font-weight:800;line-height:1.25;'
            f'color:{_t["text"]};margin-top:6px;">Screening, research and risk — '
            f'<span style="color:{_t["accent"]};">in one place.</span></div>'
            f'<div style="font-size:14px;color:{_t["text_body"]};margin:10px 0 14px;'
            f'max-width:620px;line-height:1.55;">'
            f'A personal NSE swing-trading desk. Every number on it is computed from '
            f'filed data or measured history — where something could not be measured, '
            f'the page says so rather than guessing.</div>'
            + rs.strip([
                rs.stat_card("Pattern scanners",
                             str(_n_scanners) if _n_scanners is not None else None,
                             "backtest-measured where marked", tone="info"),
                rs.stat_card("Pages", str(_n_pages),
                             f"across {len(PAGE_GROUPS)} sidebar groups", tone="neutral"),
            ], cols=2)
            + '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div style="border-top:1px solid {_t["border"]};margin-top:6px;padding-top:14px;'
            f'font-size:11.5px;color:{_t["text_muted"]};line-height:1.65;max-width:900px;">'
            f'<b style="color:{_t["text_body"]};">Research notice.</b> Scores, signals and '
            f'ratings on this dashboard are automated outputs computed from historical '
            f'market data and filed disclosures. They are <b>not investment advice</b> and '
            f'not a recommendation to buy, sell or hold. Scanner edges shown as measured '
            # This said "a single backtest window and no significance test yet" for
            # five weeks after both became false -- B-20a added the t-test and CI
            # (2026-08-12), B-21 added walk-forward pooling and B-29 the cost model
            # (2026-09-01). The correction is not a softening: the honest sentence is
            # a STRONGER warning than the stale one, because what the measurement
            # found was 0 of 41 stable (B-19). A caveat that understates the work
            # also understates the result. (B-79)
            f'are walk-forward and net of Indian delivery costs, with a significance '
            f'test — and of the {len(oh.pipeline_scanners())} scanners measured that '
            f'way, <b>none was stable across every horizon</b>. Treat them as leads, '
            f'not signals. Nothing here executes trades.'
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

    today_path = (_out.resolve(f"screener_{date.today():%Y%m%d}.xlsx")
                  or _out.out_path(f"screener_{date.today():%Y%m%d}.xlsx"))

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

        uit.paginated_df(
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
    
    # Beginner-friendly help
    help_panels.render("stock_analyzer")
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
                             width="stretch",
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
                                 width="stretch",
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
        # Same live typeahead as the ribbon search, over the same
        # symbol_directory index — so "what is a valid symbol" has ONE answer on
        # this page and in the bar. Typing a company name resolves to its NSE
        # code, which the plain box could never do: it took a code or nothing.
        #
        # It reports a pick rather than firing _symbol_jump: the ribbon's job is
        # to NAVIGATE to the analyzer, and this box is already on it. Jumping
        # would rerun the page to where it already is and drop the picked symbol.
        manual_symbol = st.session_state.get("_sa_manual", "")
        if _SYMSEARCH is not None:
            st.caption("Or enter any NSE symbol manually (no .NS suffix)")
            _picked = _SYMSEARCH(options=_symbol_payload(),
                                 placeholder="Type a name or NSE code…",
                                 key="sa_symsearch", default=None)
            if isinstance(_picked, dict) and _picked.get("symbol"):
                # Nonce-guarded like the ribbon: `picked` is the component's
                # current VALUE and persists across reruns, so acting on it
                # directly would re-select on every rerun and pin the page to
                # one symbol.
                if _picked.get("n") != st.session_state.get("_sa_pick_n"):
                    st.session_state["_sa_pick_n"] = _picked["n"]
                    st.session_state["_sa_manual"] = _picked["symbol"]
                    st.rerun()
            if manual_symbol:
                st.caption(f"Selected **{manual_symbol}** — pick another to change it.")
        else:
            # Component missing is a packaging accident, not a reason to lose the
            # ability to analyse an arbitrary symbol.
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
                width="stretch",
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
                width="stretch",
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
                render_momentum_meter(df)
                render_timeframe_board(symbol, df)
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
                        width="stretch")
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
                        width="stretch")

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
                    st.iframe(_chart_inline_url, height=460)
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

                # ── PDF of this analysis (same report as Predictive Analysis) ──
                st.divider()
                _sa_c1, _sa_c2 = st.columns([1, 3], vertical_alignment="center")
                _sa_c2.caption("One PDF of this analysis — scores, council, six "
                               "horizons, horizon geometry and every fundamental "
                               "section, with a static price chart.")
                if _sa_c1.button(f"📄 Build PDF — {symbol}", key="sa_pdf_go",
                                 width="stretch"):
                    with st.spinner("Rendering the report…"):
                        try:
                            _sa_pdf = pa_report.render_pdf(_pa_pdf_model(
                                symbol, df, nifty_df, None, None, _fund, _deep,
                                bull, bear, card,
                                council.setup_intelligence(bundle, bull, bear, card),
                                df, page_title="Stock Analyzer",
                                analyzer_scores={
                                    "pairs": [("Minervini", f"{mv_score}/8"),
                                              ("TechnoFunda", f"{tf_score}/6"),
                                              ("Total", f"{mv_score + tf_score}/14"),
                                              ("EW confidence", f"{ew['confidence']}%"),
                                              ("CANSLIM (RS)", f"{cs_score}/4 "
                                               f"({rs_pct:+.1f}% vs Nifty)")],
                                    "ew": (f"Wave position: {ew['wave_pos']} | "
                                           f"Extension risk: {ew['ext_risk']} | "
                                           f"OWL: {ew['owl_signal']} | PTF: "
                                           f"{ew['ptf_signal']}. {ew['note']}")}))
                        except Exception as exc:
                            st.error(f"PDF render failed: {exc}")
                            _sa_pdf = None
                    if _sa_pdf:
                        _sa_fn = pa_report.file_name(symbol, page="stock-analyzer")
                        st.download_button(f"⬇ {_sa_fn}", _sa_pdf, file_name=_sa_fn,
                                           mime="application/pdf", type="primary",
                                           key="sa_pdf_dl")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 3 — Portfolio
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Portfolio":
    st.subheader("Portfolio / Position Tracker")
    
    # Beginner-friendly help
    help_panels.render("portfolio")
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

    import equity_curve as _ec      # B-110: drawdown, recorded or reconstructed
    try:
        _dd_html, _dd_caps = _ec.portfolio_strip(
            db, lambda s: cached_fetch_ohlcv(s, days=1500, enforce_liquidity=False))
    except Exception as _e:         # a card must not take the tracker down with it
        _dd_html, _dd_caps = "", [f"Drawdown unavailable — {type(_e).__name__}: {_e}"]
    st.markdown(_dd_html, unsafe_allow_html=True)
    for _c in _dd_caps:
        st.caption(_c)

    open_pos = db.get_open_positions()
    if open_pos.empty:
        st.info("No open positions.")
    else:
        # ── Exposure (B-107) — the component the reference pipeline names and
        # the desk did not have. It REPORTS and does not judge: every threshold
        # here would be a statement about risk appetite, which is the owner's to
        # make once and deliberately, not a default smuggled in by a card.
        import sector_column as _sc

        def _last_px(sym: str):
            _d = cached_fetch_ohlcv(sym, enforce_liquidity=False)
            if _d is None or _d.empty:
                return None
            return float(_d["close"].iloc[-1]), 0.0     # prev close unused here

        _exp = prisk.exposure(open_pos, _last_px,
                              portfolio_summary["total_capital"],
                              sectors=_sc.symbol_sectors(
                                  open_pos["symbol"].tolist()))
        _cards, _caps = prisk.exposure_strip(_exp)
        st.markdown(_cards, unsafe_allow_html=True)
        for _c in _caps:
            st.caption(_c)
        # B-173: what sector labels miss — which holdings move as one.
        import book_correlation as _bc
        _bc.render(st, open_pos["symbol"].tolist(),
                   lambda s_: cached_fetch_ohlcv(s_, enforce_liquidity=False),
                   weights={r["symbol"]: float(r["entry_price"]) * float(r["quantity"])
                            for _, r in open_pos.iterrows()}, key="pf_corr")

        rows = []
        for _, pos in open_pos.iterrows():
            df = cached_fetch_ohlcv(pos["symbol"], enforce_liquidity=False)
            current = float(df["close"].iloc[-1]) if df is not None and not df.empty else None
            pl_pct = ((current - pos["entry_price"]) / pos["entry_price"] * 100
                      ) if current else None
            # R against the stop the trade was OPENED with (positions.initial_stop),
            # not today's stop: a raised stop shrinks entry - stop, and R measured
            # against it inflates every winner. Falls back to stop_loss for a row
            # whose initial stop is unknown.
            _r_stop = pos.get("initial_stop")
            if _r_stop is None or pd.isna(_r_stop):
                _r_stop = pos["stop_loss"]
            r_mult = psz.r_multiple(pos["entry_price"], _r_stop, current)
            rows.append({
                "id": pos["id"], "Symbol": pos["symbol"], "Entry": pos["entry_price"],
                "Qty": pos["quantity"], "Current": current,
                "P&L %": gain_loss_badge(pl_pct) if pl_pct is not None else "—",
                "R-Multiple": f"{r_mult:.2f}R" if r_mult is not None else "—",
                "Stop": pos["stop_loss"], "Initial stop": pos.get("initial_stop"),
                "Target": pos["target"],
                "Entry Date": pos["entry_date"], "Notes": pos["notes"],
            })
        uit.paginated_df(pd.DataFrame(rows).drop(columns=["id"]), key="portfolio_open")

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
            # Realised R against the opening stop. Blank, not 0, when the trade had
            # no stop: an unbounded risk has no R, and 0R would read as a scratch.
            _r = [psz.r_multiple(e, s0, x) for e, s0, x in zip(
                closed_pos["entry_price"],
                closed_pos.get("initial_stop", closed_pos["stop_loss"]),
                closed_pos["closed_price"])]
            closed_pos["R"] = [f"{v:+.2f}R" if v is not None else "—" for v in _r]
            _rs = [v for v in _r if v is not None]
            if _rs:
                st.caption(f"Realised R over {len(_rs)} closed trade(s) with a stop: "
                           f"mean **{sum(_rs) / len(_rs):+.2f}R**, "
                           f"total **{sum(_rs):+.2f}R**. 1R = entry − the stop the "
                           f"trade was opened with.")
            uit.paginated_df(
                closed_pos[["symbol", "entry_price", "closed_price", "quantity",
                            "P&L %", "R", "Result", "entry_date", "closed_date", "notes"]],
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
        # B-63b — the technical row. Every column here describes state that is
        # already computed from bars this page ALREADY fetches; none of it is a
        # signal and none of it has been measured. The columns that matter are
        # the time-derivative ones (EMA-cross age, BO date, Gain% since): the
        # rest of this desk prints whether a condition is true, never how long
        # it has been true.
        import row_metrics as _rmx
        _cols = _cols_mod()

        _wl_ref = st.date_input(
            "Re-base on", value=None, key="wl_since_date", format="DD/MM/YYYY",
            help="Pick a date and the Hist. price / Gain% since columns re-base "
                 "the whole list on it — 'how has my watchlist done since the "
                 "day I looked'. Leave empty to hide those two columns.")

        # RS-rank walk (B-63b). Read the STORED grid — never compute on load:
        # it ranks the whole universe over two years of bars. The button below
        # is the only thing that triggers a run.
        import rs_walk as _rwx
        _wl_walk = _rs_walk_lookup()
        _wl_svp = _svp_screen_lookup()
        _wl_walk_date = next(iter(_wl_walk.values()), {}).get("run_date") if _wl_walk else None

        _rw_c1, _rw_c2 = st.columns([1, 3])
        with _rw_c1:
            if st.button("Compute RS rank walk", key="wl_rs_walk_run",
                         help="Ranks the WHOLE nifty500 universe at T-30 / T-15 "
                              "/ T-5 / today. Takes a minute — it is never run "
                              "on page load."):
                with st.spinner("Ranking the universe at four dates…"):
                    # The watchlist's own names ride along as guests, so the
                    # column is populated for the names actually on this page.
                    _g = _rs_walk_compute(extra=tuple(watch["symbol"]))
                if _g.get("error"):
                    st.error(f"RS walk failed: {_g['error']}")
                else:
                    st.success(f"Ranked {min(_g['n_ranked'].values())}–"
                               f"{max(_g['n_ranked'].values())} names per column.")
                    st.rerun()
        with _rw_c2:
            if _wl_walk_date:
                st.caption(f"RS walk stored for **{_wl_walk_date}** "
                           f"({len(_wl_walk)} names ranked).")
            else:
                st.caption("No RS walk stored yet — the column appears once "
                           "you compute one.")

        nifty_wl = cached_fetch_nifty50()
        rows = []
        for _, w in watch.iterrows():
            # enforce_liquidity=False: the Rs 1 cr floor belongs to SCANNING,
            # where it keeps untradeable names out of a 2,000-symbol sweep. A
            # watchlist is curated BY HAND — the user typed these symbols — so
            # applying a scan filter here silently blanked three of eight rows
            # (AKI 0.71 cr, MARALOVER 0.37 cr, PRAENG 0.50 cr against the 1.00
            # cr floor) while the page kept listing the names. Same failure the
            # docstring of cached_fetch_ohlcv records for CENTUM. The
            # illiquidity is not hidden: it is shown as the Turnover column and
            # named in the caption below.
            df = cached_fetch_ohlcv(w["symbol"], enforce_liquidity=False)
            if df is None or df.empty:
                rows.append({"Symbol": w["symbol"], "Notes": w["notes"]})
                continue
            last = float(df["close"].iloc[-1])
            prev = float(df["close"].iloc[-2]) if len(df) > 1 else last
            day_chg = (last - prev) / prev * 100 if prev else 0.0
            mv_score, _ = sp.score_minervini(df, nifty_df=nifty_wl)
            tf_score, _ = sp.score_technofunda(df)
            m = _rmx.row(df, ref_date=_wl_ref)
            _age = m["ema_cross_age"]
            _to_cr = float((df["close"] * df["volume"]).tail(10).mean()) / 1e7
            rows.append({
                "Symbol": w["symbol"],
                "close": last,
                "chg_pct": day_chg,
                "turnover_cr": round(_to_cr, 2),
                "gap_pct": m["gap_pct"],
                "rsi": m["rsi"],
                "pct_from_20ema": m["pct_from_20ema"],
                "ema_stack": m["ema_stack"],
                # The RAW weighted trailing return behind rs_rank's percentile.
                # rs_walk shows where the name RANKS; this shows what it actually
                # returned, and a rank of 90 in a flat market is a different fact
                # from a rank of 90 in a strong one.
                "rs_momentum": _wl_rs_mom(df),
                **_earn_cols(w["symbol"], df),
                # Direction travels WITH the age: "12" alone does not say
                # whether the cross was up or down, and the sign of that is the
                # whole reading.
                "ema_cross_age": (None if _age is None else
                                  (_age if m["ema_cross_dir"] == "up" else -_age)),
                "pivot_d": m["pivot_d"],
                "pivot_w": m["pivot_w"], "pivot_agree": m.get("pivot_agree"),
                "from_52w_high_pct": m["from_52w_high_pct"],
                "bo_gain_pct": m["bo_gain_pct"],
                "bo_date": m["bo_date"],
                "hist_price": m["hist_price"],
                "gain_since_pct": m["gain_since_pct"],
                # A guest (not a nifty500 constituent) is marked with a
                # trailing * — the rank is against the index, not within it,
                # and that is worth one character rather than a footnote.
                "rs_walk": _rs_walk_cell(w["symbol"], _wl_walk),
                **_svp_cells(w["symbol"], _wl_svp),
                "minervini": f"{mv_score}/8",
                "technofunda": f"{tf_score}/6",
                # SMC state (smc_state.py, B-42r Option C): one ST/SW agreement
                # reading, P/D in the swing band, liquidity at pivot 5.
                **_smc_cells(df),
                # NOTE deliberately absent: `_notes_table` sources it from the
                # shared per-symbol store and appends it, so the page cannot show
                # a note from one place while writing to another.
            })
        # CAP buckets come from NSE index membership, resolved ONCE for the whole
        # table rather than per row — the four constituent lists are cached, and
        # a per-row lookup would re-read them ten times for ten symbols.
        try:
            import smallcap_universe as _capu
            _cap_map = _capu.cap_bucket([r["Symbol"] for r in rows])
        except Exception:
            # A cap label is decoration; the table must not fail without it.
            _cap_map = {}
        for _r in rows:
            _r["cap_bucket"] = _cap_map.get(str(_r["Symbol"]).strip().upper(), "")

        # Plan status (LuxAlgo R&E step 2, plan_status.py). The newest cached
        # scanner plan per name, judged by the harness's own walk. Bars come from
        # the same cached fetch the rows above used, so this costs no new fetch.
        import plan_status as _pst
        try:
            _pconn = db.get_connection()
            try:
                _wl_plans = _pst.watchlist_status(
                    [r["Symbol"] for r in rows],
                    lambda s_: _pst.cache_rows_from_db(_pconn, s_),
                    lambda s_: cached_fetch_ohlcv(s_, enforce_liquidity=False))
            finally:
                _pconn.close()
        except Exception as _e:           # a status column must not take the page down
            _wl_plans = {}
            st.caption(f"Plan status unavailable — {type(_e).__name__}: {_e}")
        for _r in rows:
            _p = _wl_plans.get(_r["Symbol"], {})
            _r["plan_status"] = _pst.label(_p) if _p else ""
            _r["plan_from"] = _pst.plan_source(_p)
        _wl_done = [s_ for s_, p_ in _wl_plans.items()
                    if p_.get("status") in _pst.REMOVE_SUGGESTED]

        _wl_df = pd.DataFrame(rows)
        # Cap is an IDENTITY attribute, not a measurement, so it belongs beside
        # the symbol rather than wherever dict insertion order left it — which
        # was the far right, past a horizontal scroll, where it read as missing.
        # The card's chart-icon family (Chart / Analyze / TView / Screener /
        # GFin). Every other symbol table on the desk carries it; this one did
        # not, so the page you keep open all day was the one page with no way to
        # open a chart. Placed beside the identity columns rather than appended,
        # because at ~25 columns "appended" means "behind a horizontal scroll".
        import sector_column as _sc
        _wl_df = _sc.attach(_wl_df, "Symbol")
        _wl_df = _with_chart_family(_wl_df, "Symbol")
        # Plan status sits with the identity columns: it is what the removal tick
        # beside the symbol is most often deciding on.
        _head = ["Symbol"] + [c for c in ("cap_bucket", "sector")
                              if c in _wl_df.columns] + _CHART_FAMILY_COLS +                 [c for c in ("plan_status", "plan_from") if c in _wl_df.columns]
        _wl_df = _wl_df[_head + [c for c in _wl_df.columns if c not in _head]]
        # A symbol whose history failed to load contributes only Symbol/Notes,
        # which leaves the numeric columns as object dtype holding None — and
        # Streamlit renders that as the literal string "None" in every cell.
        # Coercing makes them NaN, which renders as an empty cell: an absent
        # reading should look absent, not like a value.
        for _c in ("close", "chg_pct", "turnover_cr", "gap_pct", "ema_cross_age",
                   "svp_factors", "ssl_atr", "bsl_atr",
                   "from_52w_high_pct", "bo_gain_pct", "hist_price",
                   "gain_since_pct", "rsi", "pct_from_20ema", "rs_momentum",
                   "earn_d_minus_1", "earn_day", "earn_d_plus_1"):
            if _c in _wl_df.columns:
                _wl_df[_c] = pd.to_numeric(_wl_df[_c], errors="coerce")
        if not _wl_walk and "rs_walk" in _wl_df.columns:
            _wl_df = _wl_df.drop(columns=["rs_walk"])
        for _c in ("pivot_d", "pivot_w", "pivot_agree", "bo_date", "rs_walk", "minervini",
                   "technofunda", "ema_stack", "cap_bucket", "sector",
                   "svp_hist_8w", "plan_status", "plan_from",
                   "smc_structure", "pd_swing", "swept_recent"):
            if _c in _wl_df.columns:
                _wl_df[_c] = _wl_df[_c].where(_wl_df[_c].notna(), "")
        if _wl_ref is None and not _wl_df.empty:
            _wl_df = _wl_df.drop(columns=[c for c in ("hist_price", "gain_since_pct")
                                          if c in _wl_df.columns])
        # autofit=True: widths measured from the values in THIS frame rather
        # than the registry's general-case small/medium/large. At ~25 columns
        # the three guesses cost more screen than they save.
        _wl_df = _pw().attach(_wl_df, "Symbol", "wl")
        _wl_cfg = _cols.configure_df(
            _wl_df, autofit=True,
            overrides={"close": {"label": f"LTP ({date.today():%d %b})"}})
        # The family's columns are Title-Case in the frame and lower-case in the
        # registry, so their config comes from the shared helper, not configure_df.
        _wl_cfg.update(_chart_family_colcfg())

        # In-row note editing (B-63b), through the SHARED path since UI-2.
        # This page had its own `st.data_editor` and its own write logic; the
        # Scanner Hub then needed the same thing, and two editors against one
        # store is the drift `columns.py` exists to stop. `_notes_table` is now
        # the single implementation: every computed column disabled, the note
        # persisted per symbol, and the tint pairs preserved because a Styler
        # applies to an editor's non-editable columns.
        #
        # What changed for this page: the note is no longer read from
        # `watchlist.notes`. Removing a name from the watchlist no longer
        # destroys what you wrote about it, which is the behaviour the old
        # membership-scoped column had.
        _earnings_fill_button(_wl_df["Symbol"], "wl")
        _pw().fill_button(_wl_df["Symbol"], "wl", "Watchlist",
                          fetch=cached_fundamentals_deep)
        # Removal SUGGESTIONS from the Plan column. Pressing this only ticks the
        # finished rows; the existing two-step remove button still does the
        # removing, so nothing leaves the list without a second, deliberate click.
        if _wl_done:
            _sg1, _sg2 = st.columns([3, 1])
            _sg1.info(f"**{len(_wl_done)}** name(s) have a finished plan "
                      f"(stop or target hit, past the time stop, or the entry "
                      f"never filled): "
                      f"{', '.join(_wl_done[:10])}{'…' if len(_wl_done) > 10 else ''}. "
                      f"Finished plan ≠ finished stock — review before removing.")
            if _sg2.button(f"Tick these {len(_wl_done)}", key="wl_tick_done",
                           help="Ticks the finished-plan rows in the ✕ column. "
                                "Nothing is removed until you press Remove."):
                st.session_state["wl_preselect"] = list(_wl_done)
                # A fresh editor key so the new defaults show instead of the
                # editor's remembered (unticked) state.
                st.session_state["wl_editor_gen"] = st.session_state.get("wl_editor_gen", 0) + 1
                st.rerun()
        _wl_edited = _notes_table(
            _wl_df, key=f"wl_notes_editor_{st.session_state.get('wl_editor_gen', 0)}",
            symbol_col="Symbol", column_config=_wl_cfg, select_col="✕",
            preselect=set(st.session_state.get("wl_preselect", [])))
        _pa_send_button("wl", "Watchlist", _wl_df, "Symbol",
                        note_fn=lambda r: str(r.get("Notes") or r.get("notes") or "watchlist"))
        # Per-row removal, replacing the detached "Remove from watchlist"
        # dropdown that used to sit under the table. The dropdown made you name
        # a symbol you were already looking at, and it could only take one.
        #
        # Two steps on purpose: ticking does nothing until the button is pressed,
        # because this is the one destructive control on the page and a
        # single mis-click on a 25-column grid should not delete a name.
        _wl_picked = [str(_s).strip().upper()
                      for _s, _f in zip(_wl_edited["Symbol"], _wl_edited["✕"])
                      if bool(_f)]
        if _wl_picked:
            st.warning(f"**{len(_wl_picked)}** ticked for removal: "
                       f"{', '.join(_wl_picked[:8])}"
                       f"{'…' if len(_wl_picked) > 8 else ''}")
            if st.button(f"✕ Remove {len(_wl_picked)} from watchlist",
                         key="wl_remove_ticked", type="primary"):
                for _s in _wl_picked:
                    db.remove_watchlist_symbol(_s)
                # Notes are deliberately NOT deleted: `symbol_notes` is keyed by
                # symbol, not by membership, so re-adding a name brings back what
                # you wrote about it. That is the behaviour B-63b chose when it
                # moved notes off `watchlist.notes`, and removal must not quietly
                # reverse it.
                st.success(f"Removed {', '.join(_wl_picked)} from the watchlist. "
                           f"Notes kept.")
                # The rows shifted, so remembered ticks would land on the wrong
                # names: drop the suggestion set and start a fresh editor.
                st.session_state.pop("wl_preselect", None)
                st.session_state["wl_editor_gen"] = st.session_state.get("wl_editor_gen", 0) + 1
                st.rerun()
        st.caption(
            "**EMA cross (d)** is signed: **+12** = the 10-EMA crossed ABOVE the "
            "20-EMA twelve sessions ago, **−3** = crossed below three sessions "
            "ago, blank = no cross in the last 250 sessions (not 'never'). "
            "**BO gain%** is measured from the last close above its prior 20-bar "
            "high — read it beside **BO date**, because +3% from last week and "
            "+3% from four months ago are not the same situation, and a faded "
            "breakout shows here as a negative."
        )
        # B-173: how many independent bets the watchlist really is.
        import book_correlation as _bc
        _bc.render(st, [r["Symbol"] for r in rows],
                   lambda s_: cached_fetch_ohlcv(s_, enforce_liquidity=False), key="wl_corr")
        _thin = [r["Symbol"] for r in rows
                 if r.get("turnover_cr") is not None
                 and r["turnover_cr"] < sp.MIN_TURNOVER / 1e7]
        if _thin:
            st.caption(
                f"⚠️ Below the ₹{sp.MIN_TURNOVER / 1e7:.0f} cr screen floor: "
                f"**{', '.join(_thin)}**. They are shown here because a "
                f"watchlist is curated by hand — the floor exists to keep "
                f"untradeable names out of a 2,000-symbol *scan*, not to hide a "
                f"name you asked for. Every level on a stock turning over a few "
                f"lakh a day is still worth less than the same level on a liquid "
                f"one, and a position may be hard to exit."
            )
        _svp_cap = _svp_caption(_wl_svp)
        if _svp_cap:
            st.caption(_svp_cap)
        if _wl_walk:
            st.caption(
                r"**RS walk** reads oldest → newest. A trailing **\*** means the "
                "name is not a nifty500 constituent, so it is ranked **against** "
                "that universe rather than within it — the index is the "
                "yardstick, and membership is not required to be measured by it. "
                "**?** means the name lacked history that far back, which is not "
                "the same as ranking weak."
            )
            st.caption(f"⚠️ **RS walk:** {_rwx.SURVIVORSHIP_NOTE}")
        st.caption("Descriptions of state, not signals — none of these columns "
                   "has been measured, and none casts a vote anywhere. "
                   "**Notes is editable** — click a cell, type, press Enter — "
                   "and **✕ ticks a row for removal** (nothing happens until you "
                   "press the button that appears). Every other column is "
                   "read-only.")

        # The "Remove from watchlist" dropdown that stood here was replaced by the
        # in-row ✕ tick above: same action, aimed at the row you are reading, and
        # able to take more than one name at a time.
        wc1, wc2 = st.columns(2)
        with wc2:
            jump_sym = st.selectbox("Send to Stock Analyzer", watch["symbol"], key="wl_jump")
            if st.button("Analyze →", key="wl_analyze"):
                st.session_state["selected_symbol"] = jump_sym
                st.info("Symbol set — switch to the **Stock Analyzer** tab above.")

        with st.expander("Quick-add to portfolio"):
            qa_sym = st.selectbox("Symbol", watch["symbol"], key="wl_qa_sym")
            qa_df = cached_fetch_ohlcv(qa_sym, enforce_liquidity=False)
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
        uit.paginated_df(alerts_view.drop(columns=["id"]), key="alerts_main")

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
    
    # Beginner-friendly help
    help_panels.render("opportunity_hub")
    
    # ── Regime posture banner (B-36) — the one-line "what do I do today?" ──────

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
    # it like today" rather than "which scanner should I try".
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
                            col = ("#166534" if v <= green_thr
                                   else "#a14a0b" if v <= amber_thr else "#b91c1c")
                        else:
                            col = ("#166534" if v >= green_thr
                                   else "#a14a0b" if v >= amber_thr else "#b91c1c")
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
                        f'{uit.ticker_link(_sym)}'
                        f'{_rating_badge_html({"overall": _rt, "overall_breakdown": {}})}'
                        f'<span class="tb-chip" style="background:{rs.TOKENS["surface_alt"]};'
                        f'color:{rs.TOKENS["text_body"]};">score {row["score"]:.1f}</span>'
                        f'{_confluence_chips(int(row["confluence"]), _fam_of(row))}'
                        f'<span style="margin-left:auto;display:inline-flex;'
                        f'align-items:center;gap:8px;">{_plan}'
                        f'{_card_action_links(_sym, analyze=False)}</span></div>'
                        f'<div class="tb-micro" style="margin-top:5px;">'
                        f'{row.get("industry") or "—"} · {row.get("sector") or "—"}</div>'
                        f'{_chips}'
                        f'{_fund_html}'
                        f'<div style="font-size:11.5px;color:{rs.TOKENS["text_body"]};'
                        f'margin-top:5px;line-height:1.45;">{_notes}</div>'
                    ),
                    unsafe_allow_html=True)

            # B-109 — the PLAN stage, on the page a name is chosen from. The
            # council is expensive and this is a shortlist, so it is one name on
            # demand rather than a column: the pipeline puts PLAN *after* the
            # reader has chosen, not twenty plans before they have. Imported
            # inside the page block, the way `sector_column` and the other
            # page-scoped helpers are, so the monolith ratchet does not pay for
            # a module-level import that only one page uses.
            import plan_on_demand as _plan_od

            _plan_od.render(
                _shortlist,
                run_council=lambda _s: _plan_od.council_result(
                    _s,
                    fetch_ohlcv=lambda x: cached_fetch_ohlcv(
                        x, days=400, enforce_liquidity=False),
                    fetch_index=cached_fetch_nifty50,
                    fetch_fundamentals=cached_fetch_fundamentals,
                    run=council.run_council, regime=nifty_regime),
                render_card=lambda r: render_council(*r),
                key=f"od_{_sel_date}")

            _render_export_controls(orep.model_from_stored(_shortlist),
                                    key=f"od_{_sel_date}")

            st.caption(
                "Ranked by **0.45 × Overall Rating + 0.30 × best scanner score + "
                "0.25 × confluence**. Confluence weights scanners by *measured* "
                "backtest edge — Falling Wedge, Harmonic Reversal and Order Block "
                "count double, because the harness found the others at or below a "
                "random-entry baseline. **The scanner-score term is unmeasured as a "
                "ranking input:** B-172 found a scanner's own 0–100 score separates "
                "better hits from worse for only 1–2 of the 41 it could test (inverted for "
                "Downside Risk), and no-score scanners such as Liquidity Sweep count as "
                "0. Kept by owner decision (B-172r), not by evidence. Every name here "
                "already sits in a leading sector **and** industry; that is a filter, "
                "not a bonus. This is a shortlist to research, not a buy list.")

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
                st.dataframe(sr, width="stretch", hide_index=True,
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
                    st.dataframe(ir, width="stretch", hide_index=True,
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
        if st.button("♥ Watchlist", key=f"df_wl_{sym}", width="stretch"):
            db.add_watchlist_symbol(sym, "Delete Funnel survivor")
            st.toast(f"♥ {sym} → Watchlist")
    with b2:
        if st.button("↗ Analyze", key=f"df_an_{sym}", width="stretch"):
            st.session_state["current_page"] = "Stock Analyzer"
            st.session_state["sa_symbol_override"] = sym
            st.rerun()
    with b3:
        if st.button("⊕ Roster", key=f"df_ro_{sym}", width="stretch"):
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
        st.dataframe(pd.DataFrame(_rows), hide_index=True, width="stretch")

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
                             width="stretch")

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
    
    # Beginner-friendly help
    help_panels.render("scanner_hub")
    __import__("scanner_plans").render()      # PR-2 · trade-plan coverage census


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
                        width="stretch",
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
                                width="stretch"):
                _cached = db.get_scanner_run(selected_scanner, _load_date)
                if _cached:
                    st.session_state["hub_results"] = _cached
                    st.session_state["hub_scanner_ran"] = selected_scanner
                    st.session_state["hub_cache_loaded_date"] = _load_date
                    st.rerun()
                else:
                    st.warning("Cache entry is empty — run the scanner to populate it.")
            if _col_del.button("Delete this cache entry", key="hub_cache_del",
                               width="stretch"):
                db.delete_scanner_run(selected_scanner, _load_date)
                st.rerun()

    _run_single = (
        (hub_mode == "Single scanner" and st.button(
            "Run Scanner", type="primary", key="hub_run", width="stretch"))
        or (_hub_run_immediately is not None)
    )
    if _hub_run_immediately:
        selected_scanner = _hub_run_immediately
    _run_pipeline = hub_mode == "Pipeline — all scanners" and st.button(
        "Run All Scanners", type="primary", key="hub_run_pipeline",
        width="stretch",
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
                # RS walk for each scanner's TOP symbol — read from the stored
                # grid, never computed here: ranking the universe takes a minute
                # and the Scanner Hub must not pay that on render. Compute it on
                # the Watchlist page; every table that shows the column reads the
                # same stored run.
                _hub_walk = _rs_walk_lookup()
                if _hub_walk:
                    _sum_df["rs_walk"] = [_rs_walk_cell(s, _hub_walk)
                                          for s in _sum_df["Top Symbol"]]
                # Same two SVP cells, for each scanner's top symbol.
                _hub_svp = _svp_screen_lookup()
                if _hub_svp.get("n"):
                    _svp_pairs = [_svp_cells(s, _hub_svp)
                                  for s in _sum_df["Top Symbol"]]
                    _sum_df["svp_hist_8w"] = [c["svp_hist_8w"] for c in _svp_pairs]
                    _sum_df["svp_factors"] = [c["svp_factors"] for c in _svp_pairs]
                # UI-2: notes are editable here and stored per SYMBOL, so a note
                # written on the Hub is the same note the Watchlist shows.
                _sum_df = _hub_enrich(_sum_df, "Top Symbol", "summary")
                _sum_df = _pw().attach(_sum_df, "Top Symbol", "summary")
                _hub_price_button(_sum_df["Top Symbol"], "summary", "Summary")
                _earnings_fill_button(_sum_df["Top Symbol"], "hub_summary")
                _pw().fill_button(_sum_df["Top Symbol"], "summary", "Summary",
                                  fetch=cached_fundamentals_deep)
                _notes_table(
                    _sum_df, key="hub_summary_notes", symbol_col="Top Symbol",
                    column_config={**_chart_family_colcfg(),
                                   **_cols_mod().configure_df(_sum_df,
                                                              autofit=True)},
                )
                _hub_missing = [s for s in _sum_df["Top Symbol"]
                                if str(s).strip().upper() not in _hub_walk]
                _hub_svp_cap = _svp_caption(_hub_svp)
                if _hub_svp_cap:
                    st.caption(_hub_svp_cap)
                if _hub_walk:
                    _hub_walk_date = next(iter(_hub_walk.values()), {}).get("run_date")
                    st.caption(
                        f"**RS walk** is the TOP SYMBOL's universe-wide rank at "
                        f"T-30 / T-15 / T-5 / today (stored run **{_hub_walk_date}**), "
                        f"oldest first. `*` = ranked against the nifty500 rather "
                        f"than within it; blank = not in that run."
                    )
                # A full-market scan surfaces names outside the nifty500 by
                # design, so a blank here is expected rather than broken — but a
                # column that is blank for half its rows is not much of a column.
                # This ranks THIS run's names against the same universe, as
                # guests, and stores them alongside it.
                if _hub_missing:
                    # Every symbol this run touched — the confluence set is
                    # computed further down the page, so derive it here from the
                    # results rather than reaching forward to a name that does
                    # not exist yet (it would NameError on the first render).
                    from collections import Counter as _HubCounter
                    _hub_counts = _HubCounter(
                        card["symbol"] for cards in _pl_res.values()
                        for card in cards)
                    _hub_extra = sorted(
                        {str(s).strip().upper() for s in _sum_df["Top Symbol"]}
                        | {s for s, n in _hub_counts.items() if n >= 2})
                    if st.button(
                            f"Rank this run's names ({len(_hub_missing)} top "
                            f"symbols unranked)", key="hub_rs_walk_run",
                            help="Ranks the nifty500 universe, then places this "
                                 "run's names into that distribution as guests. "
                                 "Takes a minute; never runs on load."):
                        with st.spinner(f"Ranking the universe + "
                                        f"{len(_hub_extra)} names from this run…"):
                            _g = _rs_walk_compute(extra=tuple(_hub_extra))
                        if _g.get("error"):
                            st.error(f"RS walk failed: {_g['error']}")
                        else:
                            st.success(f"Ranked {_g['n_symbols']} constituents "
                                       f"+ {_g['n_guests']} guests.")
                            st.rerun()

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
                # Hoisted: one DB read for the table, not one per row.
                _conf_walk = _rs_walk_lookup()
                _conf_svp = _svp_screen_lookup()
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
                        # Where a name sits in the market, beside how many
                        # scanners liked it: confluence says how MANY agree,
                        # the walk says whether the market has been agreeing.
                        "rs_walk": _rs_walk_cell(sym, _conf_walk),
                        **_svp_cells(sym, _conf_svp),
                    })
                _conf_rows.sort(key=lambda r: r["Count"], reverse=True)
                import pandas as _pd_conf
                _conf_df = _pd_conf.DataFrame(_conf_rows)
                if not _conf_walk and "rs_walk" in _conf_df.columns:
                    # An empty column reads as "every name unranked"; no column
                    # reads as "not computed", which is what is true.
                    _conf_df = _conf_df.drop(columns=["rs_walk"])
                _conf_df = _with_chart_family(_conf_df, "Symbol")
                _conf_df = _hub_enrich(_conf_df, "Symbol", "confluence")
                _conf_df = _pw().attach(_conf_df, "Symbol", "confluence")
                _hub_price_button(_conf_df["Symbol"], "confluence", "Confluence")
                _earnings_fill_button(_conf_df["Symbol"], "hub_conf")
                _pw().fill_button(_conf_df["Symbol"], "confluence", "Confluence",
                                  fetch=cached_fundamentals_deep)
                _conf_colcfg = {
                    **_chart_family_colcfg(),
                    **_cols_mod().configure_df(_conf_df, autofit=True),
                    "Pledge %": st.column_config.NumberColumn(
                        "Pledge %", format="%.1f%%",
                        help="Promoter pledge (screener.in). Blank = not fetched "
                             "yet — use the pledge expander above.",
                    ),
                }
                _notes_table(_conf_df, key="hub_conf_notes", symbol_col="Symbol",
                             column_config=_conf_colcfg)

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
                                     width="stretch"):
                            st.session_state[_pg_key] = 0
                            st.rerun()
                    with _pc2:
                        if st.button("◀", key="hub_pg_prev",
                                     disabled=_page == 0,
                                     help="Previous page",
                                     width="stretch"):
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
                                     width="stretch"):
                            st.session_state[_pg_key] = _page + 1
                            st.rerun()
                    with _pc5:
                        if st.button("⏭", key="hub_pg_last",
                                     disabled=_page >= _total_pages - 1,
                                     help="Last page",
                                     width="stretch"):
                            st.session_state[_pg_key] = _total_pages - 1
                            st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# PDF export for one Predictive Analysis ticker — every section of the page,
# the expander contents included, gathered from what the page already computed
# (or from the same cached fetchers) and laid out by pa_report.render_pdf.
def _pa_pdf_model(sym, df, bench, rating, breakdown, fund, deep,
                  bull, bear, card, intel, pm_df, size_note=None,
                  page_title="Predictive Analysis", analyzer_scores=None) -> dict:
    close = df["close"].astype(float)
    price = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) > 1 else price
    win = close.tail(252)
    lo52, hi52 = float(win.min()), float(win.max())
    tail = close.tail(60)
    sup = float(tail.min()) if len(tail) >= 20 and float(tail.min()) < price else None
    res = float(tail.max()) if len(tail) >= 20 and float(tail.max()) > price else None

    m: dict = {"symbol": sym, "as_of": str(df.index[-1])[:10],
               "generated_at": datetime.now(), "regime": str(nifty_regime).upper(),
               "long_name": (deep or {}).get("long_name"), "price": price,
               "chg_pct": (price / prev - 1) * 100 if prev else None,
               "rating": rating, "rating_breakdown": breakdown or {}, "df": df,
               "bull": bull, "bear": bear, "card": card, "intel": intel,
               "size_note": size_note, "deep": deep or {},
               "page_title": page_title, "analyzer_scores": analyzer_scores}
    try:        # Six horizons: same build the page uses (hourly is cached there)
        m["horizon_panels"] = tfb.build(sym, daily=_board_daily(sym, df),
                                        hourly=_cached_hourly(sym))
    except Exception:
        m["horizon_panels"] = None

    try:
        mv, conds = sp.score_minervini(df, nifty_df=bench)
        m["summary"] = {"lo52": lo52, "hi52": hi52,
                        "pct_from_high": (price / hi52 - 1) * 100 if hi52 else 0.0,
                        "mv": mv, "stage": pa_report.stage_label(mv)[0],
                        "conds": conds, "support": sup, "resistance": res,
                        "patterns": db.get_symbol_patterns(sym) or []}
    except Exception:
        _log.debug("PA PDF: chart reading section skipped", exc_info=True)
    try:
        import money_flow as _mf
        flow = pa_report.smart_money(df)
        obv = _mf.obv(df).tail(60).values
        flow["obv_trend"] = "rising" if float(obv[-1]) > float(obv[0]) else "falling"
        flow["cmf"] = _mf.cmf(df, n=21)
        m["flow"] = flow
    except Exception:
        _log.debug("PA PDF: money flow section skipped", exc_info=True)
    try:
        import pattern_metrics as _pm
        m["pattern_metrics"] = _pm.compute_all(pm_df, bench)
    except Exception:
        _log.debug("PA PDF: pattern metrics section skipped", exc_info=True)

    f, d = fund or {}, deep or {}
    d2e = f.get("debt_to_equity")
    m["fundamentals"] = {
        "statements": bool(d.get("available")),
        "valuation": [
            ("P / E", _q(f.get("pe"), "x") or "-"), ("P / B", _q(f.get("pb"), "x") or "-"),
            ("D / E", "-" if d2e is None else f"{d2e / 100:,.2f}x"),
            ("ROE", _q(f.get("roe"), "%") or "-"), ("ROCE", _q(d.get("roce"), "%") or "-"),
            ("EPS TTM", _q(f.get("eps_ttm") if f.get("eps_ttm") is not None
                           else d.get("eps_ttm")) or "-"),
            ("Div yield", _q(f.get("dividend_yield"), "%") or "-"),
            ("Mkt cap", _cr(f.get("market_cap")) or "-"),
            ("Sector", f.get("sector") or "-")],
        "growth": [
            ("Rev CAGR 3Y", _q(d.get("revenue_cagr_3y"), "%") or "-"),
            ("Profit CAGR 3Y", _q(d.get("profit_cagr_3y"), "%") or "-"),
            ("Net margin", _q(d.get("net_margin"), "%") or "-"),
            ("OPM", _q(d.get("opm"), "%") or "-"),
            ("Free cash flow", _cr(d.get("fcf")) or "-"),
            ("Debtor days", _q(d.get("debtor_days"), "d", 0) or "-")]
        if d.get("available") else [],
    }
    try:
        m["signals"] = fscore.score_all(fund, deep)
    except Exception:
        _log.debug("PA PDF: fundamental signals section skipped", exc_info=True)
    try:
        rsi_v = float(sc._rsi_series(close, 14).iloc[-1])
        adx_v = float(sc._adx_di_series(df, 14)[0].iloc[-1])
        rsi_v = rsi_v if np.isfinite(rsi_v) else None
        adx_v = adx_v if np.isfinite(adx_v) else None
        m["momentum"] = {
            "rsi": rsi_v, "adx": adx_v,
            "rsi_word": None if rsi_v is None else ("OVERSOLD" if rsi_v < 30 else
                                                    "OVERBOUGHT" if rsi_v > 70 else "NEUTRAL"),
            "adx_word": None if adx_v is None else ("NO TREND" if adx_v < 20 else
                                                    "FORMING" if adx_v < 25 else "TRENDING")}
    except Exception:
        _log.debug("PA PDF: momentum words section skipped", exc_info=True)
    for k, fn in (("red_flags", lambda: cached_red_flags(sym)),
                  ("scenarios", lambda: scen.build(deep)),
                  ("concalls", lambda: cached_concalls(sym))):
        try:
            m[k] = fn()
        except Exception:
            m[k] = None
    return m


# ──────────────────────────────────────────────────────────────────────────────
# Predictive Analysis (Milestone 4) — the consolidated "should I take this
# trade" surface. PURE COMPOSITION of shipped pieces: M1's Overall Rating
# (ranked candidate rail from the last Scanner Hub run) + the Chart Tool iframe
# carrying M2 pattern overlays and the M3 price-projection line + the Setup
# Intelligence / Council engine from the Stock Analyzer. No new backend.
# See wiki/analyses/Dashboard-UI-Roadmap.md §Milestone 4.
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Predictive Analysis":
    # Override the global 1440px cap — this page needs the full viewport for the
    # chart iframe, same reason TradingView uses edge-to-edge layout.
    st.markdown(
        """<style>
        [data-testid="stMainBlockContainer"] {
            max-width: 100% !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        /* Scrollable candidates panel */
        .pa-candidates {
            max-height: calc(100vh - 180px);
            overflow-y: auto;
            padding-right: 6px;
        }
        .pa-candidates::-webkit-scrollbar { width: 5px; }
        .pa-candidates::-webkit-scrollbar-thumb {
            background: #d4c8b8; border-radius: 4px;
        }
        </style>""",
        unsafe_allow_html=True,
    )
    st.subheader("Predictive Analysis")
    st.caption(
        "One screen: ranked candidates (left) → annotated chart + ratings + setup "
        "intelligence (right). Candidates come from the last **Scanner Hub** run, "
        "from any table sent here with **→ Predictive Analysis**, and from the "
        "Watchlist; the chart carries the pattern overlays and price projection "
        "from the Chart Tool."
    )

    pa_left, pa_main = st.columns([1, 3.5], gap="medium")

    with pa_left:
        _pa_scroll = st.container(height=680)
    with _pa_scroll:
        hits = st.session_state.get("hub_results") or []
        ran_for = st.session_state.get("hub_scanner_ran", "")

        # Auto-load from DB when no in-session results exist.
        if not hits:
            _db_name, _db_date, _db_cards = db.get_latest_scanner_run()
            if _db_cards:
                hits = _db_cards
                ran_for = f"{_db_name} ({_db_date})"

        ranked = sorted(
            hits,
            key=lambda h: (h.get("overall") is not None, h.get("overall") or 0),
            reverse=True,
        )
        st.markdown("**Candidates**")
        if not ranked:
            st.info("No scanner results found — run a scanner in the Scanner Hub, "
                    "or type a symbol below.")
        else:
            st.caption(f"{len(ranked)} from **{ran_for}** · ranked by Overall Rating")
            for h in ranked[:30]:
                _sym = h["symbol"]
                rcol, tcol, pcol = st.columns([1.2, 1.8, 3.0], gap="small",
                                              vertical_alignment="center")
                rcol.markdown(_rating_badge_html(h), unsafe_allow_html=True)
                if tcol.button(f"**{_sym}**", key=f"pa_view_{_sym}", type="tertiary",
                               help=f"Analyze {_sym}"):
                    st.session_state["pa_symbol"] = _sym
                pcol.badge(str(h.get("pattern_type", ran_for)), color="orange")

        # ── A table sent here with "→ Predictive Analysis" ───────────────
        _pa_sent = _pa_sent_load()
        if _pa_sent and _pa_sent.get("items"):
            st.divider()
            _sh1, _sh2 = st.columns([4, 1], vertical_alignment="center")
            _sh1.markdown(f"**📤 {_pa_sent.get('source', 'Sent list')}** "
                          f"({len(_pa_sent['items'])})")
            _sh1.caption("sent " + str(_pa_sent.get("sent_at", ""))[:16].replace("T", " "))
            if _sh2.button("✕", key="pa_sent_clear", type="tertiary",
                           help="Clear this sent list"):
                _pa_sent_save(None)
                st.rerun()
            for _it in _pa_sent["items"][:60]:
                _ss = _it["symbol"]
                _stc, _snc = st.columns([1.9, 3.7], gap="small",
                                        vertical_alignment="center")
                if _stc.button(f"**{_ss}**", key=f"pa_sent_{_ss}", type="tertiary",
                               help=f"Analyze {_ss}"):
                    st.session_state["pa_symbol"] = _ss
                _snc.badge(str(_it.get("note") or _pa_sent.get("source", "")),
                           color="blue")

        # ── Watchlist as candidates ──────────────────────────────────────
        _pa_wl = db.get_watchlist()
        if _pa_wl is not None and not _pa_wl.empty:
            _scanner_syms = {h["symbol"] for h in ranked} if ranked else set()
            # …and not already listed in the sent block above
            if _pa_sent and _pa_sent.get("items"):
                _scanner_syms |= {it["symbol"] for it in _pa_sent["items"]}
            _wl_only = _pa_wl[~_pa_wl["symbol"].isin(_scanner_syms)]
            if not _wl_only.empty:
                st.divider()
                st.markdown(f"**♥ Watchlist** ({len(_wl_only)})")
                for _, _wr in _wl_only.iterrows():
                    _ws = _wr["symbol"]
                    _wtc, _wnc = st.columns([1.9, 3.7], gap="small",
                                            vertical_alignment="center")
                    if _wtc.button(f"**{_ws}**", key=f"pa_wl_{_ws}", type="tertiary",
                                   help=f"Analyze {_ws}"):
                        st.session_state["pa_symbol"] = _ws
                    _wn = _wr.get("notes") or ""
                    _wnc.badge(f"watchlist · {_wn}" if _wn else "watchlist", color="green")

    with pa_left:
        if _SYMSEARCH is not None:
            _pa_pick = _SYMSEARCH(options=_symbol_payload(),
                                  placeholder="Search symbol…",
                                  key="pa_symsearch", default=None)
            if isinstance(_pa_pick, dict) and _pa_pick.get("symbol"):
                if _pa_pick.get("n") != st.session_state.get("_pa_pick_n"):
                    st.session_state["_pa_pick_n"] = _pa_pick["n"]
                    st.session_state["pa_symbol"] = _pa_pick["symbol"].strip().upper()
                    st.rerun()
        else:
            mcol1, mcol2 = st.columns([3, 1])
            pa_manual = mcol1.text_input("Any symbol", key="pa_manual",
                                         placeholder="e.g. TITAN",
                                         label_visibility="collapsed")
            if mcol2.button("Go", key="pa_go", width="stretch") and pa_manual.strip():
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

                # ── B-130 + B-131: Stock Summary & Smart Money Flow ──────
                _card_l, _card_r = st.columns(2)
                with _card_l:
                    try:
                        _pa_close = pa_df["close"]
                        _pa_price = float(_pa_close.iloc[-1])
                        _pa_win = _pa_close.tail(252)
                        _pa_lo52, _pa_hi52 = float(_pa_win.min()), float(_pa_win.max())
                        _pa_tail = _pa_close.tail(60)
                        _pa_marks = []
                        if len(_pa_tail) >= 20:
                            _pa_sup, _pa_res = float(_pa_tail.min()), float(_pa_tail.max())
                            if _pa_sup < _pa_price:
                                _pa_marks.append((_pa_sup, f"Sup {_pa_sup:,.0f}"))
                            if _pa_res > _pa_price:
                                _pa_marks.append((_pa_res, f"Res {_pa_res:,.0f}"))
                        _pa_spectrum = rs.range_spectrum(_pa_lo52, _pa_hi52, _pa_price, marks=_pa_marks)
                        _pa_pct_from_high = (_pa_price / _pa_hi52 - 1) * 100 if _pa_hi52 else 0
                        _pa_mv, _pa_conds = sp.score_minervini(pa_df, nifty_df=pa_bench)
                        _pa_stage_label, _pa_stage_color = pa_report.stage_label(_pa_mv)
                        _pa_cond_chips = "".join(
                            f'<span style="background:{"#dcfce7" if v else "#fef2f2"};'
                            f'color:{"#166534" if v else "#991b1b"};border-radius:4px;'
                            f'padding:1px 6px;font-size:10px;margin:1px 2px;'
                            f'display:inline-block;">{"✓" if v else "✗"} {k.split(" ",1)[1]}</span>'
                            for k, v in _pa_conds.items()
                        )
                        _pa_patterns = db.get_symbol_patterns(pa_sym)
                        _pa_pat_chips = "".join(
                            f'<span style="background:#fef3c7;color:#92400e;border-radius:4px;'
                            f'padding:2px 8px;font-size:11px;margin:2px 3px;'
                            f'display:inline-block;font-weight:600;">{p}</span>'
                            for p in _pa_patterns
                        ) if _pa_patterns else '<span style="color:#636a75;font-size:11px;">No patterns detected in latest scan</span>'
                        st.markdown(rs.card(
                            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
                            f'<div><span style="font-size:22px;font-weight:700;">₹{_pa_price:,.2f}</span>'
                            f'<span style="color:#6b7280;font-size:12px;margin-left:8px;">'
                            f'{_pa_pct_from_high:+.1f}% from 52W high</span></div>'
                            f'<span style="background:{_pa_stage_color};color:#fff;border-radius:6px;'
                            f'padding:3px 10px;font-size:12px;font-weight:700;">'
                            f'{_pa_stage_label} ({_pa_mv}/8)</span></div>'
                            f'{_pa_spectrum}'
                            f'<div style="margin-top:8px;">{_pa_cond_chips}</div>'
                            f'<div style="margin-top:10px;"><b style="font-size:12px;color:#374151;">'
                            f'Detected Patterns</b><div style="margin-top:4px;">{_pa_pat_chips}</div></div>',
                            title="Stock Summary",
                        ), unsafe_allow_html=True)
                    except Exception:
                        pass
                with _card_r:
                    try:
                        import money_flow as _mf
                        _smf = pa_report.smart_money(pa_df)
                        _smf_bars, _smf_acc, _smf_dist = _smf["bars"], _smf["acc"], _smf["dist"]
                        _smf_n = _smf["n"]
                        _smf_verdict, _smf_vc = _smf["verdict"], _smf["color"]
                        _smf_bar_w = max(1, int(100 / max(_smf_n, 1)))
                        _smf_strip = "".join(
                            f'<div style="flex:1;height:32px;background:{c};'
                            f'margin-right:1px;border-radius:1px;"></div>'
                            for c in _smf_bars
                        )
                        _smf_obv = _mf.obv(pa_df)
                        _smf_obv_tail = _smf_obv.tail(60).values
                        _smf_obv_min, _smf_obv_max = float(min(_smf_obv_tail)), float(max(_smf_obv_tail))
                        _smf_obv_range = _smf_obv_max - _smf_obv_min or 1
                        _smf_obv_pts = []
                        for idx, val in enumerate(_smf_obv_tail):
                            x = idx / max(len(_smf_obv_tail) - 1, 1) * 200
                            y = 40 - (float(val) - _smf_obv_min) / _smf_obv_range * 38
                            _smf_obv_pts.append(f"{x:.1f},{y:.1f}")
                        _smf_obv_line = " ".join(_smf_obv_pts)
                        _smf_obv_trend = "rising" if float(_smf_obv_tail[-1]) > float(_smf_obv_tail[0]) else "falling"
                        _smf_obv_color = "#166534" if _smf_obv_trend == "rising" else "#b91c1c"
                        _smf_cmf = _mf.cmf(pa_df, n=21)
                        _smf_cmf_str = f"{_smf_cmf:+.3f}" if _smf_cmf is not None else "n/a"
                        _smf_cmf_color = "#166534" if (_smf_cmf or 0) > 0 else "#b91c1c" if (_smf_cmf or 0) < 0 else "#6b7280"
                        st.markdown(rs.card(
                            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                            f'<span style="font-weight:700;color:{_smf_vc};">{_smf_verdict}</span>'
                            f'<span style="font-size:12px;color:#6b7280;">'
                            f'{_smf_acc} acc · {_smf_dist} dist · {_smf_n - _smf_acc - _smf_dist} neutral'
                            f' (last {_smf_n} sessions)</span></div>'
                            f'<div style="display:flex;align-items:flex-end;height:32px;">{_smf_strip}</div>'
                            f'<div style="display:flex;gap:20px;margin-top:12px;align-items:center;">'
                            f'<div style="flex:1;"><b style="font-size:11px;color:#374151;">'
                            f'OBV Trend <span style="color:{_smf_obv_color};">({_smf_obv_trend})</span></b>'
                            f'<svg width="100%" height="42" viewBox="0 0 200 42" style="display:block;margin-top:2px;">'
                            f'<polyline points="{_smf_obv_line}" fill="none" stroke="{_smf_obv_color}" '
                            f'stroke-width="1.5" stroke-linejoin="round"/></svg></div>'
                            f'<div style="text-align:center;"><b style="font-size:11px;color:#374151;">CMF (21)</b>'
                            f'<div style="font-size:20px;font-weight:700;color:{_smf_cmf_color};">'
                            f'{_smf_cmf_str}</div></div></div>'
                            f'<div style="margin-top:8px;font-size:10px;color:#636a75;">'
                            f'Session flow is a bar-level heuristic (close vs open + above-average volume) '
                            f'— not institutional delivery data, not measured against forward returns.</div>',
                            title="Smart Money Flow",
                        ), unsafe_allow_html=True)
                    except Exception:
                        pass

                # Annotated chart — the Chart Tool iframe carries every overlay the
                # user has enabled there (M2 base zones, harmonic, trendlines, M3
                # price projection, MA Bias, …). Indicator selection persists in
                # the Chart Tool's own localStorage, so it survives reloads.
                import pa_chart_focus as _pcf
                _ctx, _note = _pcf.render_pin_bar(pa_sym)
                st.caption(_note)
                render_chart_tool(pa_sym, height=1080, query=_pcf.chart_query(
                    pa_sym, _ctx, st.session_state.get("pa_pins", [])))

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

                # ── Historical pattern metrics (overhead · extension · VCP ·
                #    radar · exceptional volume) — from the bars already loaded.
                st.divider()
                # The RSI percentile and exceptional-volume average are defined
                # over two years (500 sessions); the page's own frame is 300,
                # so give this panel its own longer frame (+20 for RSI warm-up).
                # The council keeps pa_df, so its outputs are unchanged.
                _pm_df = cached_fetch_ohlcv(pa_sym, days=PM_HISTORY_BARS,
                                            enforce_liquidity=False)
                if _pm_df is None or len(_pm_df) < len(pa_df):
                    _pm_df = pa_df
                render_pattern_metrics(_pm_df, pa_bench, key="pa_pm")

                # ── Reused Stock Analyzer sections ───────────────────────
                st.divider()
                with st.spinner("Fetching fundamentals & statements…"):
                    _pa_deep = cached_fundamentals_deep(pa_sym)
                render_fundamental_header(pa_sym, pa_df, pa_fund, _pa_deep)
                render_fundamental_signals(fscore.score_all(pa_fund, _pa_deep))
                render_ownership_flow(pa_sym)

                render_momentum_meter(pa_df)
                render_timeframe_board(pa_sym, pa_df)

                with st.expander("Fundamental history"):
                    render_fundamental_history(_pa_deep)
                with st.expander("Peer comparison"):
                    render_peer_comparison(pa_sym)
                with st.expander("Red flags"):
                    _pa_rf = cached_red_flags(pa_sym)
                    render_red_flags(_pa_rf)
                with st.expander("Scenario analysis"):
                    render_scenarios(scen.build(_pa_deep), _pa_deep)
                with st.expander("Conference calls"):
                    render_concalls(cached_concalls(pa_sym))

                if st.button("Add to Watchlist", key="pa_wl"):
                    db.add_watchlist_symbol(pa_sym, "From Predictive Analysis")
                    st.success(f"{pa_sym} added to watchlist.")

                # ── PDF of the whole page, collapsed sections expanded ───
                # Built on request, like the Opportunity Hub export:
                # download_button needs the bytes up front, and most visits
                # never export.
                st.divider()
                _pdf_c1, _pdf_c2 = st.columns([1, 3], vertical_alignment="center")
                _pdf_c2.caption("One PDF of this page for this ticker — every "
                                "collapsed section expanded, six horizons and "
                                "horizon geometry included, a static price chart "
                                "in place of the Chart Tool. Text is selectable "
                                "and searchable.")
                if _pdf_c1.button(f"📄 Build PDF — {pa_sym}", key="pa_pdf_go",
                                  width="stretch"):
                    with st.spinner("Rendering the report…"):
                        try:
                            _pa_size = None
                            if pa_card.size_pct is not None:
                                _pa_size = prisk.size_note(prisk.reconcile_size(
                                    pa_card.size_pct, verdict,
                                    portfolio_summary.get("open_count", 0)))
                            _pa_pdf = pa_report.render_pdf(_pa_pdf_model(
                                pa_sym, pa_df, pa_bench, pa_rating, pa_bd,
                                pa_fund, _pa_deep, pa_bull, pa_bear, pa_card,
                                council.setup_intelligence(pa_bundle, pa_bull,
                                                           pa_bear, pa_card),
                                _pm_df, size_note=_pa_size))
                        except Exception as exc:
                            st.error(f"PDF render failed: {exc}")
                            _pa_pdf = None
                    if _pa_pdf:
                        _pa_fn = pa_report.file_name(pa_sym)
                        st.download_button(f"⬇ {_pa_fn}", _pa_pdf, file_name=_pa_fn,
                                           mime="application/pdf", type="primary",
                                           key="pa_pdf_dl")
                        st.caption(f"{len(_pa_pdf) / 1024:.0f} KB")


# ──────────────────────────────────────────────────────────────────────────────
# Tab 9 — Sector Map (live heatmap + rotation quadrant + orbit chart)
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Sector Map":
    st.subheader("Sector Map")

    import sector_indices_table as _sit
    _sit.render()
    st.divider()
    import sector_ranking as _srk
    _srk.render()
    st.divider()
    import sector_rs_leadership as _rsl
    _rsl.render()
    st.divider()
    import sector_turnover_heatmap as _tah
    _tah.render()
    st.divider()

    # Money flow first: it answers "where is money going" from the constituents
    # themselves, and needs no sector-index fetch, so it renders before the RRG
    # block that is gated behind a button.
    _money_flow_window("smf_page")
    st.divider()

    # Directly beneath, deliberately: delta-share is unsigned and CMF is signed,
    # so the two answer half a question each.
    _turnover_share_window("tsh_page")
    st.divider()

    # Sector index frames come from the stored snapshot (yfinance, 2y daily,
    # written by the scheduled refresh or the ↻ button) — the page opens with
    # the last run instead of an empty prompt.
    st.markdown("#### Sector index data")
    _sd_meta, _sd_payload = snapshot_panel("sector_index_data", key="sm_sector",
                                           button_label="↻ Refresh sector data")

    if _sd_payload is None:
        st.info("No sector index snapshot stored yet — press **↻ Refresh sector "
                "data** to fetch it now (runs in the background).")
    else:
        sector_data: dict = _sd_payload.get("sector_data") or {}
        _sd_bench = _sd_payload.get("benchmark")
        if not sector_data:
            st.warning("The stored snapshot holds no sector index data — refresh it.")
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
                    st.plotly_chart(fig_hm, width="stretch")

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
                        tbl, width="stretch", hide_index=True,
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
                    st.plotly_chart(fig_rq, width="stretch")

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

            rrg_bench = _sd_bench if _sd_bench is not None else cached_fetch_benchmark()
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
                st.plotly_chart(fig_rrg, width="stretch")

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
                _nse_csv = _out.out_path(
                    f"nse_ownership_wide_{date.today():%Y%m%d}.csv")
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
    export_files = _out.find("screener_export_*.csv")
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
    html_files = _out.find("sector_rotation_orbit_*.html")
    if html_files:
        names = [f.name for f in html_files]
        selected_name = st.selectbox(
            "Orbit chart snapshot",
            names,
            index=0,
            help="Newest first. Each file is a dated snapshot from a past pipeline run.",
        )
        selected_html = BASE_DIR / selected_name
        st.iframe(selected_html.read_text(encoding="utf-8"), height=740)
    else:
        st.info(
            "No orbit chart found yet. "
            "Go to **Other Screeners** → run a screener.in query → **Pipeline → Sector Rotation** "
            "to generate it."
        )

    # Saved sector rotation table — follow the selected orbit snapshot's date when possible
    xlsx_files = _out.find("sector_rotation_*.xlsx")
    if xlsx_files:
        table_path = xlsx_files[0]
        if selected_name:
            # sector_rotation_orbit_YYYYMMDD.html -> sector_rotation_YYYYMMDD.xlsx
            date_suffix = selected_name.replace("sector_rotation_orbit_", "").replace(".html", "")
            matched = _out.resolve(f"sector_rotation_{date_suffix}.xlsx")
            if matched is not None:
                table_path = matched
        with st.expander("Saved Sector Rotation Table"):
            try:
                df_sr = pd.read_excel(table_path, sheet_name="Sector Rotation")
                st.caption(f"Source: `{table_path.name}`")
                uit.paginated_df(df_sr, key="sector_rotation_saved")
            except Exception as e:
                st.warning(f"Could not load table: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Extracted pages (B-87r) — Tab 10 (Astro Timing) lives in tools/pages/ now
# ──────────────────────────────────────────────────────────────────────────────
# One dispatch for every page that has been moved into tools/desk_pages/, paid for
# once. Each future extraction deletes an `if current_page == "..."` block from
# this file and adds nothing here, so the module-statement ratchet now falls
# with each one instead of creeping up. See tools/desk_pages/__init__.py.
if dpages.handles(current_page):
    dpages.render(current_page)


# ──────────────────────────────────────────────────────────────────────────────
# Tab 11 — Telegram Signals
# ──────────────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────────────
# Breakout Scans · yfinance source — replaced the Chartink feed 2026-10-06.
# Chartink needed a `_chartink_session` cookie pasted by hand whenever it
# expired. This runs the repo's own breakout engine on yfinance history over
# the NSE-bhavcopy universe: no login, no cookie. Engine: breakout_scan.py.
# ──────────────────────────────────────────────────────────────────────────────
import breakout_scan as bks


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _bks_frames(top_n: int, as_of: str) -> dict:
    """Full yfinance history for the top-N bhavcopy names. Keyed on the date so
    a new session forces a fresh download; cached six hours within a day."""
    syms = cached_fetch_bhavcopy_universe(top_n)
    return bks.download_history(list(syms), period="max")


# ──────────────────────────────────────────────────────────────────────────────
# Page — Breakout Scans (B-36r fold, 2026-08-27). One page, two sources: the
# yfinance engine (formerly Chartink) and the TradingView BrkoutGeek replica.
# Invariant: both feeds stay reachable, nothing lost.
# ──────────────────────────────────────────────────────────────────────────────
_BKS_YF = "yfinance (no login)"
if current_page == "Breakout Scans":
    st.subheader("Breakout Scans — new-high breakout feeds")
    st.caption("Two no-login breakout feeds, same idea (a stock clearing a prior "
               "high) from different engines. Pick a source.")
    if st.session_state.get("bscan_src") not in (_BKS_YF, "TradingView"):
        st.session_state["bscan_src"] = _BKS_YF      # old "Chartink" value
    st.radio(
        "Source", [_BKS_YF, "TradingView"], horizontal=True, key="bscan_src",
        help="yfinance: 6M → 10Y consolidation breakouts on NSE-bhavcopy names, "
             "computed here. TradingView: BrkoutGeek 1-month-high replica.",
    )

if current_page == "Breakout Scans" and st.session_state.get("bscan_src") == _BKS_YF:
    st.markdown("**6M → 10Y consolidation breakouts — yfinance history, no login**")
    st.caption(
        "Universe: the top names by traded value from today's **NSE bhavcopy**. "
        "Bars: full **yfinance** daily history. Rules: the same consolidation-"
        "breakout engine the Scanner Hub runs (close above the period high, above "
        "EMA50, traded-value floor, and a per-duration range gate). Results differ "
        "from Chartink on purpose — Chartink's clauses had no real consolidation "
        "test — and cover the top-N liquid names rather than the whole market."
    )

    # Ramp walks info → good → accent → risk as the base lengthens: a longer
    # base is a rarer, heavier claim. Reading order, not decoration.
    _BKS_COLOR = {"6-Month": rs.TOKENS["info"], "1-Year": rs.TOKENS["good"],
                  "3-Year": rs.TOKENS["accent"], "5-Year": "#c2410c",
                  "10-Year": rs.TOKENS["risk"]}
    _BKS_LABELS = [lab for _d, lab, _f in reversed(sc.BREAKOUT_TIERS)]

    bk_left, bk_main = st.columns([1, 3])
    with bk_left:
        bks_top = st.select_slider("Universe (top N by traded value)",
                                   options=[200, 500, 1000, 2000], value=500,
                                   key="bks_top",
                                   help="First run downloads full history for "
                                        "these names (~1–3 min for 500); "
                                        "cached for six hours after.")
        bks_tiers = st.multiselect("Durations", _BKS_LABELS,
                                   default=["10-Year", "5-Year", "3-Year", "1-Year"],
                                   key="bks_tiers")
        st.caption("3-Year uses a 65% range gate interpolated between the 1Y and "
                   "5Y gates — not measured.")
        if st.button("▶ Run breakout scan", type="primary", key="bks_run",
                     width="stretch"):
            with st.spinner(f"Downloading history for the top {bks_top} NSE names "
                            f"and scanning…"):
                try:
                    _fr = _bks_frames(int(bks_top), date.today().isoformat())
                    st.session_state["bks_results"] = {
                        "rows": bks.breakouts(_fr, bks_tiers),
                        "n": len(_fr), "top": int(bks_top),
                        "tiers": list(bks_tiers),
                        "short_10y": len(bks.short_history(_fr, 2520)),
                        "short_5y": len(bks.short_history(_fr, 1260)),
                    }
                except Exception as exc:
                    st.error(f"Breakout scan failed: {exc}")

    with bk_main:
        _res = st.session_state.get("bks_results")
        if not _res:
            st.info("Pick a universe size and durations, then **Run breakout "
                    "scan**. No cookie or login needed.")
        else:
            st.caption(
                f"{len(_res['rows'])} breakout(s) among {_res['n']} of the top "
                f"{_res['top']} names yfinance served · durations: "
                f"{', '.join(_res['tiers'])} · {_res['short_10y']} names have under "
                f"10 years of history and {_res['short_5y']} under 5, so those "
                f"tiers cannot fire for them.")
            if not _res["rows"]:
                st.info("No stock cleared the selected durations today.")
            else:
                _bdf = pd.DataFrame(_res["rows"])
                _bdf.insert(0, "Chart", _bdf["symbol"].map(
                    lambda s: f"http://localhost:5001/?symbol={s}.NS&tf=1d"))
                _bdf.insert(1, "Analyze", _bdf["symbol"].map(_analyze_url))
                _bdf = _bdf.rename(columns={
                    "symbol": "Symbol", "longest": "Longest", "tiers": "Cleared",
                    "price": "Price", "chg_pct": "% Chg", "broke_level": "Broke",
                    "breakout_pct": "Above %", "range_pct": "Range %",
                    "vol_ratio": "Vol ×", "years_history": "Years"})
                st.markdown(" · ".join(
                    f"<span style='color:{_BKS_COLOR[lab]};font-weight:700;'>"
                    f"{lab} {int((_bdf['Longest'] == lab).sum())}</span>"
                    for lab in _res["tiers"]), unsafe_allow_html=True)
                _keep = ["Chart", "Analyze", "Symbol", "Longest", "Cleared", "Price",
                         "% Chg", "Broke", "Above %", "Range %", "Vol ×", "Years"]
                st.dataframe(
                    _bdf[_keep], width="stretch", hide_index=True,
                    column_config={
                        "Chart": st.column_config.LinkColumn(
                            "Chart", display_text="Open Chart", width="small"),
                        "Analyze": _analyze_colcfg(),
                        "% Chg": st.column_config.NumberColumn(format="%.2f%%"),
                        "Above %": st.column_config.NumberColumn(format="%.1f%%"),
                        "Range %": st.column_config.NumberColumn(format="%.0f%%"),
                    })
                st.download_button(
                    "⬇ Download CSV",
                    _bdf[[c for c in _keep if c not in ("Chart", "Analyze")]]
                    .to_csv(index=False).encode(),
                    file_name=f"breakouts_{date.today().isoformat()}.csv",
                    mime="text/csv", key="bks_dl")
                _pa_send_button("bks", "Breakout Scans (yfinance)", _bdf, "Symbol",
                                note_fn=lambda r: r["Longest"])

    st.divider()

    # ── Pre-Breakout Screener (conviction score + pledge/cash-flow gate) ────────
    st.subheader("Pre-Breakout Screener — Conviction ≥ 60%, Pledge & Cash-Flow Safe")
    st.caption(
        "Finds stocks coiled just under a 20-day high — 1-2 sessions from a possible "
        "breakout — using the same five gates as Chartink's pre-breakout clause, "
        "evaluated locally on yfinance bars (no login). Each candidate is then "
        "scored 0-100 (proximity to the trigger, volatility contraction, RSI, "
        "trend/volume); only scores at or above the slider survive. The pledge / "
        "cash-flow red-flag check runs against screener.in using your browser's "
        "existing login, if there is one."
    )

    pb_left, pb_main = st.columns([1, 3])
    with pb_left:
        pb_screener_cookie, pb_browser = bch.get_screener_sessionid()
        if pb_screener_cookie:
            st.caption(f"✅ screener.in session found in {pb_browser} — stocks with "
                       "promoter pledge above the limit or negative operating cash "
                       "flow are dropped automatically.")
        else:
            pb_screener_cookie = ""
            st.caption("⚠️ Not logged into screener.in in a local browser — results "
                       "show a manual check-link instead of auto-dropping pledged / "
                       "negative-cash-flow stocks.")
        pb_min_conviction = st.slider("Minimum conviction %", 0, 100, 60, 5,
                                      key="pb_min_conviction",
                                      help="Lower this to see more (weaker) candidates.")
        pb_max_pledge = st.slider("Max pledge %", 0.0, 25.0, 5.0, 0.5,
                                  key="pb_max_pledge",
                                  help="Only applied when a screener.in session exists.")
        st.caption(f"Universe: top {st.session_state.get('bks_top', 500)} NSE names "
                   "(the slider above); reuses the downloaded history.")
        if st.button("▶ Run Pre-Breakout Scan", type="primary", key="pb_run",
                     width="stretch"):
            _top = int(st.session_state.get("bks_top", 500))
            with st.spinner(f"Scanning the top {_top} NSE names for pre-breakouts…"):
                try:
                    _fr = _bks_frames(_top, date.today().isoformat())
                    gated = bks.pre_breakouts(_fr, 0)
                except Exception as exc:
                    gated = None
                    st.error(f"Pre-breakout scan failed: {exc}")
            if gated is not None:
                safe_symbols = None
                if pb_screener_cookie:
                    with st.spinner("Checking pledge % / cash flow on screener.in…"):
                        try:
                            safe_symbols = cached_fetch_safe_symbols(
                                pb_screener_cookie, max_pledge_pct=pb_max_pledge)
                        except Exception as exc:
                            st.warning(f"screener.in fundamental check failed: {exc}")
                funnel = {"gate": len(gated), "conviction": 0, "fundamentals": 0}
                scored = []
                for hit in gated:
                    if hit["conviction"] < pb_min_conviction:
                        continue
                    funnel["conviction"] += 1
                    if safe_symbols is not None:
                        hit["fundamentals_safe"] = hit["symbol"] in safe_symbols
                        if not hit["fundamentals_safe"]:
                            continue
                        funnel["fundamentals"] += 1
                    else:
                        hit["fundamentals_safe"] = None
                    scored.append(hit)
                st.session_state["pb_results"] = scored
                st.session_state["pb_funnel"] = funnel

        pb_funnel = st.session_state.get("pb_funnel")
        if pb_funnel:
            line = (f"Pre-breakout gates: **{pb_funnel.get('gate', 0)}** → "
                    f"conviction ≥{pb_min_conviction}%: **{pb_funnel['conviction']}**")
            if pb_screener_cookie:
                line += f" → pledge/cash-flow safe: **{pb_funnel['fundamentals']}**"
            st.caption(line)

    with pb_main:
        pb_results = st.session_state.get("pb_results")
        if pb_results is None:
            st.info("Click **Run Pre-Breakout Scan** to look for stocks 1-2 sessions "
                    "from a breakout. No cookie needed.")
        elif not pb_results:
            st.info("No candidate cleared both the pre-breakout gates and the "
                    "conviction floor right now.")
        else:
            df_pb_res = pd.DataFrame(pb_results)
            df_pb_res["Chart"] = df_pb_res["symbol"].apply(
                lambda s: f"http://localhost:5001/?symbol={s}.NS&tf=1d")
            df_pb_res["Analyze"] = df_pb_res["symbol"].map(_analyze_url)
            if df_pb_res["fundamentals_safe"].isna().all():
                df_pb_res["Pledge/CF Check"] = df_pb_res["symbol"].apply(
                    lambda s: f"https://www.screener.in/company/{s}/consolidated/#shareholding")
                pledge_note = "manual — log into screener.in in your browser to automate"
            else:
                df_pb_res["Pledge/CF Check"] = "✅ Verified Safe"
                pledge_note = "auto-verified via screener.in"
            df_pb_res = df_pb_res.rename(columns={
                "symbol": "Symbol", "price": "Price", "pct_chg": "% Chg",
                "conviction": "Conviction %", "distance_pct": "Dist to Trigger %",
                "rsi": "RSI"})
            st.caption(f"{len(df_pb_res)} candidates · pledge/cash-flow check: {pledge_note}")
            col_cfg_pb = {
                "Chart": st.column_config.LinkColumn("Chart", display_text="Open Chart",
                                                     width="small"),
                "Analyze": _analyze_colcfg(),
                "Conviction %": st.column_config.ProgressColumn(
                    "Conviction %", min_value=0, max_value=100, format="%.0f%%"),
                **_cols_mod().configure("% Chg", "Price"),
            }
            if pledge_note.startswith("manual"):
                col_cfg_pb["Pledge/CF Check"] = st.column_config.LinkColumn(
                    "Pledge/CF Check", display_text="Verify", width="small")
            keep_pb = ["Chart", "Analyze", "Symbol", "Price", "% Chg", "Conviction %",
                       "Dist to Trigger %", "RSI", "Pledge/CF Check"]
            st.dataframe(df_pb_res[[c for c in keep_pb if c in df_pb_res.columns]],
                         width="stretch", hide_index=True, column_config=col_cfg_pb)


# ──────────────────────────────────────────────────────────────────────────────
# Breakout Scans · TradingView source (BrkoutGeek: Horz Break replica, public scan API)
# ──────────────────────────────────────────────────────────────────────────────
if current_page == "Breakout Scans" and st.session_state.get("bscan_src") == "TradingView":
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

    # Stored snapshot at the default thresholds; the button below runs the scan
    # live at whatever thresholds are set and shows that until the next rerun.
    _tv_meta, _tv_snap = snapshot_panel("tv_scan", key="tv",
                                        button_label="↻ Refresh (defaults)")
    if st.button("Run scan at these thresholds", key="tv_refresh"):
        with st.spinner("Fetching TradingView scan…"):
            df_tv = tvs.fetch_brkoutgeek(
                min_chg=tv_min_chg,
                min_rel_vol=tv_min_rv,
                min_price_vol_inr=tv_min_tv * 1e7,   # Cr → INR
            )
            st.session_state["tv_scan_df"] = df_tv

    df_tv = st.session_state.get("tv_scan_df")
    if df_tv is None and _tv_snap is not None:
        df_tv = _tv_snap.get("df")
        _tvp = _tv_snap.get("params") or {}
        st.caption(f"Stored scan at min chg {_tvp.get('min_chg')}% · rel vol "
                   f"{_tvp.get('min_rel_vol')} · turnover ₹{_tvp.get('min_tv_cr')} Cr.")
    if df_tv is None:
        st.info("No stored scan yet — press ↻ or run it at your thresholds.")
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
        st.dataframe(view, width="stretch", hide_index=True, column_config=tv_cfg)


# ──────────────────────────────────────────────────────────────────────────────
# Page — High-Growth Screener (screener.in fundamentals + IBD-style RS rank +
# %R Trend Exhaustion signal)
# ──────────────────────────────────────────────────────────────────────────────
# SVP Structure — EXTRACTED to tools/desk_pages/svp_structure.py (B-87r).
# Dispatched by the desk_pages registry block above.


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
    
    # Beginner-friendly help
    help_panels.render("market_sentiment")
    # B-145 · index valuation with its window stated; never labelled cheap/expensive.
    __import__("index_valuation_card").render()
    # B-66 measured all four inputs AND the composite against NIFTY's forward
    # returns and found no discrimination anywhere. The page is not being removed
    # — a null is not evidence of harm, and a description of today's tape is worth
    # having — but it must not read as a forecast, which the band names
    # ("Strong Buy") otherwise do. This is the caption that entry hands forward.
    st.warning(
        "**This describes today's tape. It does not forecast tomorrow's.** "
        "Measured 2026-09-10 (B-66): none of the four inputs, and not the "
        "composite either, shows any relationship with NIFTY's next-5-day return "
        "— tercile spreads −0.01% to −0.12%, all rank correlations ≈ 0, and the "
        "two deepest inputs cover 18–19 years including 2008, 2020 and 2022. "
        "The band names are labels for the current reading, **not** buy or sell "
        "advice. Read this as a summary of where the market stands, and take "
        "direction from something that has been measured.",
        icon="⚠️",
    )

    # The reading is computed by the sentiment snapshot job (scheduled / ↻) and
    # persisted by sentiment_index itself; this page only ever READS the newest
    # persisted row. The panel busts the overview ribbon's cache on completion.
    snapshot_panel("sentiment", key="senti", button_label="↻ Refresh sentiment")

    reading = None
    if True:
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
    _mh_meta, _mh_snap = snapshot_panel(
        "market_health", key="mh_basket", button_label="↻ Refresh basket",
        help=f"Fetches {MH_BASKET_SIZE} liquid names to measure 'breakouts working' "
             f"and 'leaders strong', plus NIFTY / VIX. ~30-60s, in the background.")

    _mh_frames = _mh_requested = None
    _mh_nifty = _mh_vix = None
    if _mh_snap is not None:
        _mh_frames = _mh_snap.get("basket_frames")
        _mh_requested = _mh_snap.get("basket_requested")
        _mh_nifty, _mh_vix = _mh_snap.get("nifty"), _mh_snap.get("vix")
    if _mh_nifty is None:
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
            st.plotly_chart(fig, width="stretch")

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
            hide_index=True, width="stretch",
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
                    hide_index=True, width="stretch",
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
            st.plotly_chart(fig_h, width="stretch")

    # ── Global Context — Finviz (US market snapshot) ──────────────────────────
    st.markdown("---")
    st.markdown("### Global Context — US Market (Finviz)")
    st.caption(
        "Scraped live from finviz.com — US breadth and signal tables. Adds "
        "risk-on/risk-off context to complement the NIFTY reading above."
    )
    _fvz_meta, _fvz_snap = snapshot_panel("finviz", key="finviz",
                                          button_label="↻ Refresh Finviz")
    fvz_idx = None if _fvz_snap is None else _fvz_snap.get("indices")
    fvz_br  = {} if _fvz_snap is None else (_fvz_snap.get("breadth") or {})

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
            st.dataframe(pd.DataFrame(br_rows), hide_index=True, width="stretch",
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
                    st.dataframe(df_sig, hide_index=True, width="stretch")
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
                    hide_index=True, width="stretch",
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

    # Built by the market_brief snapshot (with sector breadth, on the persisted
    # sentiment reading — the same row this page shows above).
    _brief_meta, model = snapshot_panel("market_brief", key="brief",
                                        button_label="↻ Rebuild brief")
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
                hide_index=True, width="stretch",
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
                hide_index=True, width="stretch", height=320,
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
        "**Corporate filings are now wired up** (below) — the whole-market feed IS high volume, "
        "which is why it is bucketed and de-noised rather than left raw: 1,262 filings over four "
        "days reduce to 226 material ones."
    )

    # ── Material corporate filings, market-wide (B-111) ───────────────────────
    # The stream this page said was "not wired up because it is high volume".
    # Bucketing is the answer to the volume; the render lives in the module so a
    # test can reach the classification, which is the part that decides what a
    # reader is told is material.
    import nse_filings_feed as _ff

    st.markdown("#### Material corporate filings")
    _ff.render(days=st.select_slider("Window (days)", [1, 2, 3, 5, 7], value=2,
                                     key="mi_filing_days"), key="mi")
    st.divider()

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

                    The liquidity floor is OFF here, and the paragraph above is
                    why: with it on, an NSE-listed name that merely trades thin
                    ALSO returned None and was reported as "not NSE-listed" —
                    a different and false statement. Bulk/block deals happen in
                    illiquid scrips more often than liquid ones, so the floor
                    was biting hardest exactly where this page looks.
                    """
                    try:
                        pdf = cached_fetch_ohlcv(sym, days=90, enforce_liquidity=False)
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
                _tbl, width="stretch", hide_index=True,
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
        uit.paginated_df(df_deals.style.apply(_row_color, axis=1), key="deals_main",
                      column_config=col_config)

    with intel_tabs[0]:
        min_val_bulk = st.slider("Highlight bulk deals above (₹ Lakh)", 5, 500, 50, step=5, key="imi_bulk_min")
        _bulk_meta, _bulk_snap = snapshot_panel("bulk_deals", key="imi_bulk",
                                                button_label="↻ Refresh bulk deals")
        if _bulk_snap is not None:
            st.session_state["imi_bulk_bse"] = _bulk_snap.get("bse", pd.DataFrame())
            st.session_state["imi_bulk_nse"] = _bulk_snap.get("nse", pd.DataFrame())
            for _ex, _err in (_bulk_snap.get("errors") or {}).items():
                st.warning(f"{_ex.upper()} bulk deals fetch failed in the stored run: {_err}")

        st.markdown("**BSE**")
        _highlight_deals(st.session_state.get("imi_bulk_bse", pd.DataFrame()),
                         min_val_bulk, "TRANSACTION_TYPE", filter_key="imi_bulk_bse_filter")
        st.markdown("**NSE**")
        _highlight_deals(st.session_state.get("imi_bulk_nse", pd.DataFrame()),
                         min_val_bulk, "Buy/Sell", filter_key="imi_bulk_nse_filter")

    with intel_tabs[1]:
        min_val_block = st.slider("Highlight block deals above (₹ Lakh)", 5, 2000, 100, step=25, key="imi_block_min")
        _block_meta, _block_snap = snapshot_panel("block_deals", key="imi_block",
                                                  button_label="↻ Refresh block deals")
        if _block_snap is not None:
            st.session_state["imi_block_bse"] = _block_snap.get("bse", pd.DataFrame())
            st.session_state["imi_block_nse"] = _block_snap.get("nse", pd.DataFrame())
            for _ex, _err in (_block_snap.get("errors") or {}).items():
                st.warning(f"{_ex.upper()} block deals fetch failed in the stored run: {_err}")

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
        _ins_meta, _ins_snap = snapshot_panel("insider_trading", key="imi_ins",
                                              button_label="↻ Refresh (last 7 days)")
        if _ins_snap is not None and "imi_insider" not in st.session_state:
            st.session_state["imi_insider"] = _ins_snap.get("df")
            st.caption(f"Stored range {_ins_snap.get('from')} → {_ins_snap.get('to')}; "
                       "pick other dates and fetch to override for this session.")
        if st.button("Fetch this date range", key="imi_ins_refresh"):
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
            st.info("No stored run yet — press ↻, or pick a date range and fetch it.")
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
            uit.paginated_df(styled, key="insider_main", column_config=ins_col_config)

    with intel_tabs[3]:
        st.caption(
            "Gap-up/gap-down and unusual-volume scan over the bhavcopy universe (reuses the same "
            "Full-Market source as Scanner Hub)."
        )
        gv_col1, gv_col2, gv_col3 = st.columns(3)
        gv_top_n = gv_col1.slider("Universe size (top N by traded value)", 50, 5000, 500, step=50, key="imi_gv_topn")
        gv_gap_pct = gv_col2.slider("Min gap %", 1.0, 15.0, 3.0, step=0.5, key="imi_gv_gap")
        gv_vol_mult = gv_col3.slider("Min volume × 20d avg", 1.0, 10.0, 2.0, step=0.5, key="imi_gv_vol")

        _gv_meta, _gv_snap = snapshot_panel("gap_volume", key="imi_gv",
                                            button_label="↻ Refresh (defaults)")
        if st.button("Run scan at these thresholds", type="primary", key="imi_gv_run"):
            with st.spinner("Loading market universe…"):
                try:
                    gv_universe = cached_fetch_bhavcopy_universe(gv_top_n)
                except Exception as exc:
                    gv_universe = []
                    st.error(f"Bhavcopy fetch failed: {exc}")
            with st.spinner(f"Scanning {len(gv_universe)} symbols for gaps/volume…"):
                # One scan, shared with the headless snapshot job.
                st.session_state["imi_gv_results"] = snapreg.gap_volume_scan(
                    gv_universe, cached_fetch_ohlcv,
                    gap_pct=gv_gap_pct, vol_mult=gv_vol_mult)

        gv_results = st.session_state.get("imi_gv_results")
        if gv_results is None and _gv_snap is not None:
            gv_results = _gv_snap.get("hits")
            _gvp = _gv_snap.get("params") or {}
            st.caption(f"Stored scan: top {_gvp.get('top_n')} by traded value · "
                       f"gap ≥ {_gvp.get('gap_pct')}% or volume ≥ {_gvp.get('vol_mult')}× "
                       f"20d avg · {_gv_snap.get('universe_n', 0)} names.")
        if gv_results is None:
            st.info("No stored scan yet — press ↻ or run it at your thresholds.")
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
                df_gv_res, width="stretch", hide_index=True,
                column_config={
                    "Chart": st.column_config.LinkColumn("Chart", display_text="Open Chart", width="small"),
                    "Analyze": _analyze_colcfg(),
                    **_cols_mod().configure("Gap %"),
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
                st.iframe(_html, height=min(4200, 620 + 26 * _rows))
                _stem = f"deal_board_{date.today():%Y%m%d}"
                _dl1, _dl2, _dl3 = st.columns([1, 1, 2])
                with _dl1:
                    st.download_button(
                        "⬇ HTML", data=_html, file_name=f"{_stem}.html",
                        mime="text/html", key="imi_db_dl", width="stretch")
                # PNG is rendered on demand, not with every board: it launches
                # headless Chromium (~2-4s). Rendering it here rather than in the
                # browser means the image is produced by the SAME engine that
                # displays the board — a canvas library re-implements CSS and
                # would ship a subtly different picture.
                with _dl2:
                    if st.button("🖼 Render image", key="imi_db_png",
                                 width="stretch"):
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
                            width="stretch")
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
                             width="stretch"):
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
                _tbl, width="stretch", hide_index=True,
                column_config={
                    "Chart": st.column_config.LinkColumn(
                        "Chart", display_text="📈 Open", width="small"),
                    "Analyze": _analyze_colcfg(),
                    # B-63a: these three now come from the registry, which
                    # carries the tooltip that used to live only here — the
                    # index table below rendered the same columns WITHOUT it.
                    **_cols_mod().configure("Price %", "OI %", "RVol"),
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
                                width="stretch",
                            )
                        with _h3:
                            _au = _analyze_url(r["symbol"])
                            if _au:
                                st.link_button(
                                    "↗ Analyze", url=_au,
                                    help="Open the 3-POV Council analysis in a new tab",
                                    width="stretch",
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
                    width="stretch", hide_index=True,
                    column_config=_cols_mod().configure("Price %", "OI %", "RVol"),
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
                    width="stretch", hide_index=True,
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
        return "#166534"
    if agreement in _L4_NEG:
        return "#b91c1c"
    if agreement == "bought_now_selling":
        return "#a14a0b"                     # amber — the warning divergence
    return "#6b7280"                         # neutral / no data


def _l4_signed_bar(label: str, v: float) -> str:
    """A signed −1…+1 driver as a bar diverging from a centre line."""
    v = max(-1.0, min(1.0, float(v)))
    half = abs(v) * 50.0
    left = 50.0 if v >= 0 else 50.0 - half
    color = "#166534" if v >= 0 else "#b91c1c"
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
            f"<span style='color:#b91c1c;font-weight:600;'>⚠ Promoter pledge "
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
        ohlcv = cached_fetch_ohlcv(sym, days=90, enforce_liquidity=False)
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
        f"Chart patterns (detections {_SNAP_DATE}, prices live) · "
        f"trading strategies + fundamental scores ({_SNAP_DATE} snapshot)"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Smart-Money Confluence (Layer 4) — live, per-symbol ───────────────────
    with st.container(border=True):
        _render_layer4_panel()

    # ── 1. Chart Patterns ─────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### Chart Patterns  ·  Major Stocks")
        st.caption(
            "**Detections are a fixed sample** captured from StockEdge in August "
            "2026 (EOD, AI + Human hybrid) \u2014 a record of what a third party "
            "called and when, not a live feed. **The prices are live:** LTP is "
            "fetched from the same batched source the rest of the desk uses, and "
            "Move % is derived from it rather than stored (PR-1)."
        )

        import pandas as pd
        import pattern_reports as _pr

        _pat_px = _pr.cached_prices()
        _pat_df = pd.DataFrame(_pr.build_rows(_pat_px), columns=list(_pr.COLUMNS))
        # A None in an object-dtype column renders as the literal string "None".
        # Coercing makes it NaN, which renders as an EMPTY cell -- an absent
        # reading must look absent, not like a value. Same fix the Watchlist
        # applies to its own numeric columns.
        for _c in ("Pub Price ₹", "LTP ₹", "Move %"):
            _pat_df[_c] = pd.to_numeric(_pat_df[_c], errors="coerce")

        _pat_filter = st.radio(
            "Filter", ["All", "Bullish", "Bearish", "Neutral"],
            horizontal=True, key="sh_pat_filter",
        )
        _pat_view = _pat_df if _pat_filter == "All" else _pat_df[_pat_df["Bias"] == _pat_filter]

        st.dataframe(
            _pat_view.drop(columns=["Bias"]),
            width="stretch",
            hide_index=True,
            column_config={
                # The symbol is shown, not hidden: it is what the price was
                # fetched against, so a reader can check the name-to-ticker
                # mapping rather than trust it.
                "Symbol":      st.column_config.TextColumn("Symbol", width="small"),
                "Stock":       st.column_config.TextColumn("Stock", width="medium"),
                "Pattern":     st.column_config.TextColumn("Pattern", width="medium"),
                "Published":   st.column_config.TextColumn("Published", width="small"),
                # "Pub Price ₹" stays inline — a singleton, used only here. Blank
                # means the source published no price point, so the row carries a
                # detection but cannot carry a move.
                # "Pub Price ₹" stays inline -- a singleton, used only here.
                #
                # The three price-less rows render a grey "None" in these
                # columns, not an empty cell. That is STREAMLIT's missing-value
                # placeholder, not our data: the values are verified NaN
                # (float64) before they reach the grid, and dropping the printf
                # format does not change it. Tested both ways on the running
                # page rather than assumed. The caption under the table names
                # the three rows and why they cannot carry a move, which is
                # where the explanation belongs; the same placeholder shows up
                # on the Watchlist's SVP column and is tracked separately.
                "Pub Price ₹": st.column_config.NumberColumn("Pub Price ₹", format="₹%.2f"),
                **_cols_mod().configure("LTP ₹"),
                "Move %":      st.column_config.NumberColumn("Move %", format="%+.1f%%"),
            },
        )
        _sb = _pr.scoreboard(_pat_view.to_dict("records"))
        _unpriced = len(_pr.symbols()) - len(_pat_px)
        st.caption(
            f"**{_sb['above']}** above publish price · **{_sb['below']}** below · "
            f"scored on **{_sb['scored']} of {_sb['total']}** shown"
            + (f" \u2014 {_sb['total'] - _sb['scored']} have no publish price, so they "
               f"carry a detection but no move" if _sb['scored'] < _sb['total'] else "")
            + (f" · {_unpriced} symbol(s) could not be priced" if _unpriced else "")
            + " · Major Stocks filter · activeness-status=200"
        )

    # ── 2. Trading Strategies ─────────────────────────────────────────────────
    with st.container(border=True):
        # "Live Counts" until 2026-09-17, over a hardcoded literal dated 11 Aug
        # (PR-1b). The heading was the boldest claim on the page and the one
        # thing here that was never true.
        st.markdown("#### Trading Strategies  ·  Snapshot")
        st.caption(
            f"**A fixed snapshot from {_SNAP_DATE}, not a live count** — these "
            "scans are a third party's and nothing on this desk re-runs them. "
            "The descriptions and horizons are a record of what each scan is; "
            "the stock counts are what it returned on that date."
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

        # The "Net: N bullish vs M bearish · bullish skew is consistent" line was
        # removed 2026-09-17 (PR-1b). It summed the frozen counts above and read
        # as a finding about the market; it was a finding about a literal. A
        # scoreboard is only worth printing when something is measuring it.

    # ── 3. Fundamentals (PR-1c) ───────────────────────────────────────────────
    # Was `_FS_DATA`, a literal of six rows carrying a /100 shield, an EPS CAGR,
    # a PE band, LTP and day change -- all hardcoded under a caption claiming the
    # scores were "computed from the last fundamental data pull". It printed a
    # PE of 62x for Piramal Pharma, whose TTM EPS is -2.4: not stale, meaningless.
    with st.container(border=True):
        __import__("fundamental_panel").render(rs.TOKENS)


# ──────────────────────────────────────────────────────────────────────────────
# Background-job poll — MUST be the last thing the script does. If any queued /
# running job exists, sleep briefly then rerun, so the status panel and any
# completed results refresh on their own. The full page above has already
# rendered, so the user keeps interacting (new clicks queue) while a job runs.
# ──────────────────────────────────────────────────────────────────────────────
ui_jobs.autorefresh()
