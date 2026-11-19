"""Live chrome — the parts of the desk that say "this is running right now".

Three pieces, all fed by data the desk already had (no new fetch on load beyond
widening the one ribbon download):

  * the ticker tape under the nav — a CSS-only scroll of index quotes;
  * the Home hero band — market-status pill, verdict line, index tiles with a
    one-month sparkline;
  * the freshness dot beside every "Last run" caption.

Honesty rules carried over from the rest of the desk: a quote that could not be
read renders "—", never a zero or a flat line; the tape is DAILY bars, so
intraday it shows the last close, and it says so.

Every <style> block is emitted on its own: dashboard_app hides element
containers whose markdown holds a <style>, so CSS mixed with visible markup
would vanish with it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import escape

import streamlit as st

log = logging.getLogger(__name__)

#: (yahoo ticker, tape label). The first three are the hero tiles, in order.
TAPE: list[tuple[str, str]] = [
    ("^NSEI", "NIFTY 50"), ("^NSEBANK", "BANK NIFTY"), ("^INDIAVIX", "INDIA VIX"),
    ("^CNXIT", "NIFTY IT"), ("^CNXSC", "SMALLCAP"), ("^CNXPHARMA", "PHARMA"),
    ("^CNXAUTO", "AUTO"), ("^CNXMETAL", "METAL"), ("^CNXFMCG", "FMCG"),
    ("^CNXREALTY", "REALTY"), ("^CNXENERGY", "ENERGY"),
    ("^GSPC", "S&P 500"), ("^IXIC", "NASDAQ"), ("^DJI", "DOW"),
    ("^FTSE", "FTSE 100"), ("^GDAXI", "DAX"), ("^N225", "NIKKEI 225"),
    ("^HSI", "HANG SENG"),
]

#: Readable on the dark band/tape (the light-theme tokens are too dark there).
_UP, _DOWN, _MUTED, _ABSENT = "#4ade80", "#f87171", "#94a3b8", "#64748b"


@dataclass(frozen=True)
class Quote:
    label: str
    last: float | None
    chg_pct: float | None
    closes: tuple[float, ...] = ()


def fetch_tape(_bucket: int) -> list[Quote]:
    """Last close, day change and ~1 month of closes for TAPE. ONE yfinance call.

    `_bucket` only busts the caller's cache (see the call site: a minute while
    the session is live, a quarter-hour otherwise). Every failure yields None
    values, so the tape renders "—" rather than an invented number.
    """
    try:
        import yfinance as yf
        data = yf.download([t for t, _ in TAPE], period="1mo", interval="1d",
                           progress=False, group_by="ticker", auto_adjust=False,
                           threads=True)
    except Exception as e:
        log.warning("tape fetch failed: %s", e)
        return [Quote(lbl, None, None) for _, lbl in TAPE]
    out = []
    for tkr, lbl in TAPE:
        try:
            closes = data[tkr]["Close"].dropna()
            last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
            out.append(Quote(lbl, last, (last - prev) / prev * 100.0,
                             tuple(float(c) for c in closes)))
        except Exception:
            out.append(Quote(lbl, None, None))
    return out


def _num(q: Quote) -> str:
    return f"{q.last:,.2f}" if "VIX" in q.label else f"{q.last:,.0f}"


# ── Freshness dot ─────────────────────────────────────────────────────────────

def freshness(run_at: datetime, *, stale: bool, live: bool,
              now: datetime | None = None) -> str:
    """'green' | 'orange' | 'red' for a stored run.

    During the session the clock is what matters: under 15 minutes is current,
    under an hour is ageing, older is stale. Outside it, a run is current until
    a close has happened since (`stale`, from snapshot_store.is_stale) — an
    evening run of a closed market is not "old".
    """
    if not live:
        return "red" if stale else "green"
    age = (now or datetime.now()) - run_at
    if age <= timedelta(minutes=15):
        return "green"
    if age <= timedelta(hours=1):
        return "orange"
    return "red"


def fresh_dot(run_at: datetime, *, stale: bool, live: bool,
              now: datetime | None = None) -> str:
    """The dot as Streamlit markdown, for st.caption."""
    return f":{freshness(run_at, stale=stale, live=live, now=now)}[●]"


# ── Ticker tape ───────────────────────────────────────────────────────────────

_TAPE_CSS = """
<style>
  @keyframes tb-tape { from { transform: translateX(0); } to { transform: translateX(-50%); } }
  @keyframes tb-pulse { 0% { box-shadow: 0 0 0 0 rgba(74,222,128,.7); }
                        70% { box-shadow: 0 0 0 7px rgba(74,222,128,0); }
                        100% { box-shadow: 0 0 0 0 rgba(74,222,128,0); } }
  .tb-tape { overflow: hidden; background: #0b0f14; border-bottom: 1px solid #1c2430;
             margin-left: -2rem; margin-right: -2rem; height: 28px;
             display: flex; align-items: center;
             -webkit-mask-image: linear-gradient(90deg, transparent, #000 3%, #000 97%, transparent);
             mask-image: linear-gradient(90deg, transparent, #000 3%, #000 97%, transparent); }
  .tb-tape-track { display: flex; width: max-content; animation: tb-tape 90s linear infinite; }
  .tb-tape:hover .tb-tape-track { animation-play-state: paused; }
  .tb-tape-item { display: inline-flex; gap: 6px; align-items: baseline; padding: 0 18px;
                  font-size: 11.5px; white-space: nowrap; font-variant-numeric: tabular-nums;
                  border-right: 1px solid #1c2430; }
  .tb-pulse { animation: tb-pulse 2s infinite; }
  @media (prefers-reduced-motion: reduce) {
    .tb-tape-track, .tb-pulse { animation: none; }
  }
</style>
"""


def tape_html(quotes: list[Quote]) -> str:
    items = []
    for q in quotes:
        lbl = f'<span style="color:{_MUTED};font-weight:600;">{escape(q.label)}</span>'
        if q.last is None or q.chg_pct is None:
            items.append(f'<span class="tb-tape-item">{lbl}'
                         f'<span style="color:{_ABSENT};">—</span></span>')
            continue
        tone = _UP if q.chg_pct >= 0 else _DOWN
        arrow = "▲" if q.chg_pct >= 0 else "▼"
        items.append(
            f'<span class="tb-tape-item">{lbl}'
            f'<span style="color:#e2e8f0;">{_num(q)}</span>'
            f'<span style="color:{tone};">{arrow} {q.chg_pct:+.2f}%</span></span>')
    row = "".join(items)
    # Two copies + translateX(-50%) is a seamless loop with no JS.
    return (f'<div class="tb-tape" title="Daily closes — intraday this is the last '
            f'close, not a live tick. Hover to pause.">'
            f'<div class="tb-tape-track">{row}{row}</div></div>')


def render_tape(quotes: list[Quote]) -> None:
    st.markdown(_TAPE_CSS, unsafe_allow_html=True)
    st.markdown(tape_html(quotes), unsafe_allow_html=True)


# ── Hero band (Home) ──────────────────────────────────────────────────────────

def sparkline_svg(closes: tuple[float, ...], colour: str,
                  w: int = 120, h: int = 34) -> str:
    """Inline SVG polyline of closes; '' with fewer than two points."""
    if len(closes) < 2:
        return ""
    lo, hi = min(closes), max(closes)
    span = (hi - lo) or 1.0
    step = w / (len(closes) - 1)
    pts = " ".join(f"{i * step:.1f},{h - 2 - (c - lo) / span * (h - 4):.1f}"
                   for i, c in enumerate(closes))
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'preserveAspectRatio="none" style="display:block;">'
            f'<polyline points="{pts}" fill="none" stroke="{colour}" '
            f'stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/></svg>')


def _tile(q: Quote) -> str:
    if q.last is None or q.chg_pct is None:
        body = f'<div style="font-size:20px;color:{_ABSENT};">—</div>' \
               f'<div style="font-size:11px;color:{_ABSENT};">data n/a</div>'
        spark = ""
    else:
        # VIX up is risk up, so its colour is inverted.
        good = (q.chg_pct >= 0) != ("VIX" in q.label)
        tone = _UP if good else _DOWN
        body = (f'<div style="font-size:21px;font-weight:700;color:#f8fafc;'
                f'font-variant-numeric:tabular-nums;">{_num(q)}</div>'
                f'<div style="font-size:12px;color:{tone};font-variant-numeric:tabular-nums;">'
                f'{q.chg_pct:+.2f}% <span style="color:{_ABSENT};">1-day</span></div>')
        spark = sparkline_svg(q.closes, tone)
    return (f'<div style="flex:1 1 170px;min-width:150px;background:rgba(255,255,255,.04);'
            f'border:1px solid #1f2a37;border-radius:12px;padding:12px 14px;">'
            f'<div style="font-size:10.5px;letter-spacing:.08em;color:{_MUTED};'
            f'font-weight:600;margin-bottom:4px;">{escape(q.label)}</div>'
            f'<div style="display:flex;align-items:flex-end;justify-content:space-between;gap:10px;">'
            f'<div>{body}</div>{spark}</div></div>')


def hero_html(*, market_state: str, market_label: str, verdict: str,
              instruction: str, verdict_tone: str, regime: str,
              tiles: list[Quote], today: str) -> str:
    live = market_state == "LIVE"
    dot = {"LIVE": _UP, "PRE-OPEN": "#fb923c"}.get(market_state, _ABSENT)
    pill_label = {"LIVE": "Market live", "PRE-OPEN": "Pre-open"}.get(
        market_state, "Market closed")
    pill = (f'<span style="display:inline-flex;align-items:center;gap:7px;'
            f'background:rgba(255,255,255,.06);border:1px solid #243041;border-radius:999px;'
            f'padding:3px 11px;font-size:11px;font-weight:600;color:#e2e8f0;">'
            f'<span class="{"tb-pulse" if live else ""}" style="width:7px;height:7px;'
            f'border-radius:50%;background:{dot};display:inline-block;"></span>'
            f'{pill_label} <span style="color:{_MUTED};font-weight:400;">'
            f'· {escape(market_label.split("·")[-1].strip())}</span></span>')
    vcol = {"good": _UP, "risk": _DOWN, "warn": "#fb923c"}.get(verdict_tone, "#e2e8f0")
    reg = ""
    if regime in ("RISK-ON", "RISK-OFF"):
        rc = _UP if regime == "RISK-ON" else _DOWN
        reg = (f'<span style="font-size:11px;color:{rc};border:1px solid {rc}55;'
               f'border-radius:999px;padding:2px 9px;margin-left:8px;">'
               f'NIFTY {regime} · 200 SMA</span>')
    return (
        f'<div style="background:radial-gradient(1200px 300px at 15% 0%,#1e293b 0%,'
        f'#0b0f14 60%);border-bottom:1px solid #1c2430;margin:0 -2rem 18px;'
        f'padding:22px 2rem 20px;">'
        f'<div style="display:flex;flex-wrap:wrap;gap:24px;align-items:center;'
        f'justify-content:space-between;">'
        f'<div style="flex:1 1 380px;min-width:300px;">'
        f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">{pill}'
        f'<span style="font-size:11px;letter-spacing:.08em;color:{_MUTED};">'
        f'{escape(today.upper())}</span></div>'
        f'<div style="margin-top:12px;font-size:12px;color:{_MUTED};letter-spacing:.06em;">'
        f'TODAY\'S VERDICT{reg}</div>'
        f'<div style="font-size:28px;font-weight:700;color:{vcol};line-height:1.2;'
        f'margin-top:4px;">{escape(verdict)}</div>'
        f'<div style="font-size:13px;color:#cbd5e1;margin-top:6px;max-width:640px;'
        f'line-height:1.5;">{escape(instruction)}</div></div>'
        f'<div style="flex:2 1 520px;display:flex;flex-wrap:wrap;gap:12px;">'
        f'{"".join(_tile(q) for q in tiles)}</div>'
        f'</div></div>')


def render_hero(**kw) -> None:
    st.markdown(hero_html(**kw), unsafe_allow_html=True)


# ── Pane widths (Home) ────────────────────────────────────────────────────────

#: Fixed side panes, fluid centre. Only above 900px: below that Streamlit
#: stacks columns, and a 300px stacked pane would be a narrow strip.
PANE_CSS = """
<style>
  [data-testid="stElementContainer"]:has(.tb-pane-mark) { display: none !important; }
  @media (min-width: 900px) {
    [data-testid="stColumn"]:has(#tb-pane-left)  { flex: 0 0 300px !important; width: 300px !important; max-width: 300px !important; }
    [data-testid="stColumn"]:has(#tb-pane-right) { flex: 0 0 290px !important; width: 290px !important; max-width: 290px !important; }
    [data-testid="stColumn"]:has(#tb-pane-centre){ flex: 1 1 0 !important; width: auto !important; min-width: 0 !important; }
  }
</style>
"""


def pane_mark(name: str) -> str:
    return f'<div id="tb-pane-{name}" class="tb-pane-mark"></div>'
