"""Live chrome — the parts of the desk that say "this is running right now".

Two pieces, all fed by data the desk already had (no new fetch on load beyond
widening the one ribbon download):

  * the ticker tape under the nav — a CSS-only scroll of index quotes;
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

#: (yahoo ticker, tape label).
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
