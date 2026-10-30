"""Breadth strip — the market's internals as five two-sided bars.

Sits under the index strip on Home. The index charts say what the headline did;
these say how many stocks did it, which is the part a headline hides — an index
can close green on eight heavyweights while four hundred names fall.

Five bars, and each one states the universe it was measured over, because they
are NOT all the same universe and pretending otherwise would be the easy lie:

  1. Advancing / Declining   whole EQ market, from today's NSE bhavcopy. This is
                             the SAME number the verdict card's breadth flag
                             uses (sentiment_index._advance_decline), read off
                             the same bhavcopy — two different Adv/Decl counts
                             on one page would be a contradiction the reader has
                             to resolve, so there is only one.
  2. New High / New Low      NIFTY 500, 52-week, on the close
  3. Above / Below SMA50     NIFTY 500
  4. Above / Below SMA200    NIFTY 500
  5. Bull / Bear             the desk's own sentiment index (0-100) restated as
                             a split, NOT a survey. Labelled as the desk's
                             reading, since "BULL 45% / BEAR 55%" with no source
                             reads as a poll of somebody.

A bar whose inputs could not be read renders DATA N/A. Nothing here is
back-filled to 50/50: an unknown breadth is not a balanced one.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

import report_style as rs

#: Bars 2-4 are measured over this index. 500 names in one batched yfinance
#: call (~10s), which is why the whole strip is cached rather than recomputed
#: on every Streamlit rerun.
UNIVERSE = "nifty500"
UNIVERSE_LABEL = "NIFTY 500"
#: 52 weeks of NSE sessions — 250 is what a 1y daily fetch actually returns.
LOOKBACK_52W = 250
HISTORY_PERIOD = "1y"


@dataclass(frozen=True)
class BreadthBar:
    """One two-sided bar. `left` is the bullish side by convention."""
    title: str
    left_label: str
    right_label: str
    left: int | None
    right: int | None
    universe: str
    note: str | None = None

    @property
    def total(self) -> int | None:
        if self.left is None or self.right is None:
            return None
        return self.left + self.right

    @property
    def left_pct(self) -> float | None:
        t = self.total
        return None if not t else self.left / t * 100.0

    @property
    def right_pct(self) -> float | None:
        t = self.total
        return None if not t else self.right / t * 100.0

    @property
    def available(self) -> bool:
        return bool(self.total)


# ──────────────────────────────────────────────────────────────────────────────
# Measurement
# ──────────────────────────────────────────────────────────────────────────────
def advance_decline_bar(ad: dict | None, as_of: str | None = None) -> BreadthBar:
    """Bar 1, straight off the reading sentiment_index already computed.

    `as_of` is the sentiment reading's date, and it is printed rather than
    assumed to be today: the desk persists one reading per run, so this bar can
    legitimately be three sessions old — the same staleness the verdict card
    above raises as a caution flag. A stale count labelled "today" would be the
    one actively misleading thing on the strip.
    """
    adv = decl = None
    if ad and (ad.get("advances") or ad.get("declines")):
        adv, decl = int(ad["advances"]), int(ad["declines"])
    return BreadthBar("Advancing / Declining", "Advancing", "Declining",
                      adv, decl, f"NSE EQ · bhavcopy {as_of or '—'}")


def _closes(df: pd.DataFrame | None) -> pd.Series | None:
    if df is None or getattr(df, "empty", True):
        return None
    col = ("Close" if "Close" in df.columns
           else "close" if "close" in df.columns else None)
    if col is None:
        return None
    s = df[col].dropna()
    return s if len(s) else None


def sma_bar(hist: dict[str, pd.DataFrame], window: int) -> BreadthBar:
    """How many of the universe closed above their own `window`-day SMA.

    A name with fewer than `window` closes is excluded rather than judged on a
    short average — a 200-day mean of 60 bars is a different statistic wearing
    the same label.
    """
    above = below = 0
    for df in hist.values():
        c = _closes(df)
        if c is None or len(c) < window:
            continue
        if c.iloc[-1] >= c.tail(window).mean():
            above += 1
        else:
            below += 1
    covered = above + below
    return BreadthBar(
        f"Above / Below SMA{window}", "Above", "Below",
        above if covered else None, below if covered else None,
        UNIVERSE_LABEL,
        note=None if covered else f"no name had {window} closes")


def high_low_bar(hist: dict[str, pd.DataFrame]) -> BreadthBar:
    """52-week new highs and new lows, counted on the CLOSE.

    Closing highs, not intraday highs: a spike that closed back inside the range
    is not a name at a new high by the evening, and this strip is read after the
    close.
    """
    highs = lows = covered = 0
    for df in hist.values():
        c = _closes(df)
        if c is None or len(c) < LOOKBACK_52W:
            continue
        covered += 1
        window = c.tail(LOOKBACK_52W)
        last = window.iloc[-1]
        if last >= window.max():
            highs += 1
        elif last <= window.min():
            lows += 1
    # 0 highs and 0 lows is a real mid-range reading, not a failure — but only
    # when names were actually measured. No coverage renders DATA N/A.
    return BreadthBar("New High / New Low", "New High", "New Low",
                      highs if covered else None, lows if covered else None,
                      f"{UNIVERSE_LABEL} · 52w close",
                      note=None if covered else "no name had a year of closes")


def sentiment_bar(reading: dict | None) -> BreadthBar:
    """Bar 5 — the desk's 0-100 sentiment score split into bull and bear.

    The score is the whole of it: 45 means BULL 45 / BEAR 55. That is a
    restatement of one number, not a second measurement, and the universe line
    under the bar says so.
    """
    if not reading or reading.get("score") is None:
        return BreadthBar("Bull / Bear", "Bull", "Bear", None, None,
                          "desk sentiment index", note="no reading computed")
    bull = int(round(float(reading["score"])))
    bull = max(0, min(100, bull))
    band = (reading.get("band") or "").strip()
    return BreadthBar("Bull / Bear", "Bull", "Bear", bull, 100 - bull,
                      f"desk sentiment index{' · ' + band if band else ''}")


def build_bars(hist: dict[str, pd.DataFrame],
               reading: dict | None) -> list[BreadthBar]:
    """The five bars. `reading` is the persisted sentiment reading, which owns
    both the Adv/Decl counts (bar 1) and the score (bar 5)."""
    reading = reading or {}
    ad = (reading.get("inputs") or {}).get("advance_decline")
    return [
        advance_decline_bar(ad, reading.get("reading_date")),
        high_low_bar(hist),
        sma_bar(hist, 50),
        sma_bar(hist, 200),
        sentiment_bar(reading),
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Markup
# ──────────────────────────────────────────────────────────────────────────────
def bar_html(b: BreadthBar) -> str:
    """Labels, counts and the split bar itself, in one card."""
    good, _ = rs.tone_colors("good")
    risk, _ = rs.tone_colors("risk")
    head = (f'<div class="tb-micro" style="text-align:center;">{b.title}</div>')
    if not b.available:
        return rs.card(
            head
            + f'<div class="tb-stat-val tb-na" style="text-align:center;">'
              f'{rs.NA}</div>'
            + f'<div class="tb-micro" style="text-align:center;">'
              f'{b.note or "not measured"}</div>')
    row = (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;gap:8px;margin-top:3px;">'
        f'<span style="font-size:11.5px;font-weight:700;color:{good};">'
        f'▲ {b.left_label}</span>'
        f'<span style="font-size:11.5px;font-weight:700;color:{risk};">'
        f'{b.right_label} ▼</span></div>'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;gap:8px;">'
        f'<span class="tb-mono" style="font-size:12px;color:{good};">'
        f'{b.left_pct:.1f}% ({b.left:,})</span>'
        f'<span class="tb-mono" style="font-size:12px;color:{risk};">'
        f'({b.right:,}) {b.right_pct:.1f}%</span></div>')
    # Both sides are always drawn, so a 100/0 split reads as a bar that filled
    # rather than as a bar that failed to render. B-162: red vs green alone is the
    # commonest colour-vision confusion, so the sides also carry ▲/▼ and the two
    # segments are split by a surface-coloured gap that marks where one ends.
    bar = (
        f'<div style="display:flex;height:9px;border-radius:5px;overflow:hidden;'
        f'margin-top:5px;background:{rs.TOKENS["absent_soft"]};">'
        f'<div style="width:{b.left_pct:.2f}%;background:{good};"></div>'
        f'<div style="width:2px;flex-shrink:0;background:{rs.TOKENS["surface"]};"></div>'
        f'<div style="width:{b.right_pct:.2f}%;background:{risk};"></div></div>')
    foot = (f'<div class="tb-micro" style="text-align:center;margin-top:5px;">'
            f'{b.universe}</div>')
    return rs.card(head + row + bar + foot)


# ──────────────────────────────────────────────────────────────────────────────
# The Streamlit surface
# ──────────────────────────────────────────────────────────────────────────────
# Same split as index_strip: dashboard_app.py says WHERE this goes, everything
# else is here, so the monolith does not grow another page body.
def fetch_history() -> dict[str, pd.DataFrame]:
    """One batched download of the whole NIFTY 500, a year of daily bars.

    ~10s and one HTTP request. Five hundred per-symbol fetches would be a page
    nobody waits for, which is why this reuses the batched downloader the
    sector pages already run on.
    """
    try:
        import nse_universe as nu
        import trending_stocks as ts
    except Exception:
        return {}
    cons = nu.fetch_constituents(UNIVERSE)
    symbols = [str(r["symbol"]).strip() for r in cons if r.get("symbol")]
    if not symbols:
        return {}
    try:
        return ts._batch_history(symbols, period=HISTORY_PERIOD)
    except Exception:
        return {}


def render(reading: dict | None) -> None:
    """Five columns of bars, plus the coverage line under them."""
    import streamlit as st

    hist = st.cache_data(
        ttl=900, show_spinner="Measuring NIFTY 500 breadth …")(fetch_history)()
    bars = build_bars(hist, reading)
    for col, b in zip(st.columns(len(bars)), bars):
        with col:
            st.markdown(bar_html(b), unsafe_allow_html=True)
    st.expander("How this is measured — breadth bars").caption(
        "Each bar names its own universe — they are not the same one. "
        "Advancing/Declining is the whole EQ market from the bhavcopy of the "
        "sentiment reading dated under that bar — the same count the verdict "
        "above flags, and as old as that reading is; the three middle bars are "
        "the "
        f"{UNIVERSE_LABEL} ({len(hist)} of 500 names loaded), measured on "
        "closes; Bull/Bear is this desk's own sentiment score restated as a "
        "split, not a survey of anyone. Cached 15 minutes."
    )
