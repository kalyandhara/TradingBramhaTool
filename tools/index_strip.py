"""Index strip — four intraday mini-charts for the top of the desk's Home page.

One card per index: last value, the change against the PREVIOUS SESSION's close,
and the current session's 5-minute candles with that previous close drawn in as
a dashed reference line. Nothing here is a signal; it is the context line the
desk was missing — "what is the market doing right now" — which until now had to
be read off a 300-bar daily NIFTY chart further down the page.

Two honesty rules carried over from the rest of the desk:

  * NIFTY NEXT 50 has no Yahoo index symbol with intraday data (^NSEJUNIOR,
    ^CNXNIFTYJR and NIFTY_NEXT_50.NS all return nothing). JUNIORBEES, the
    Nifty Next 50 ETF, does — so the card plots the ETF and is LABELLED as the
    ETF. A proxy that is not named as a proxy is a wrong number.
  * A card whose fetch returned nothing renders DATA N/A, not a flat line and
    not a zero. An index that could not be read must look unread.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

import report_style as rs

#: (display label, yahoo symbol, proxy note or None). Order is the display order.
INDICES: list[tuple[str, str, str | None]] = [
    ("NIFTY 50",       "^NSEI",         None),
    ("NIFTY BANK",     "^NSEBANK",      None),
    ("NIFTY NEXT 50",  "JUNIORBEES.NS", "ETF"),
    ("NIFTY SMALLCAP", "^CNXSC",        None),
]

INTERVAL = "5m"
#: 5 calendar days is the shortest window that still contains a full previous
#: session across a long weekend or an NSE holiday.
PERIOD = "5d"


@dataclass(frozen=True)
class IndexQuote:
    label: str
    symbol: str
    proxy: str | None
    #: current session's intraday bars, or None when the fetch came back empty
    bars: pd.DataFrame | None
    last: float | None
    prev_close: float | None
    session: str | None          # ISO date of the session plotted

    @property
    def change(self) -> float | None:
        if self.last is None or not self.prev_close:
            return None
        return self.last - self.prev_close

    @property
    def change_pct(self) -> float | None:
        if self.change is None:
            return None
        return self.change / self.prev_close * 100.0

    @property
    def tone(self) -> str:
        c = self.change
        if c is None:
            return "absent"
        return "good" if c >= 0 else "risk"


def _flatten(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance returns a MultiIndex column frame for a single ticker too."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    return df


def split_sessions(df: pd.DataFrame) -> tuple[pd.DataFrame | None, float | None]:
    """Last session's bars, and the close of the session before it.

    The previous close is taken from the intraday frame rather than a second
    daily fetch: one request per index, and the two are then guaranteed to come
    from the same snapshot of Yahoo's data.
    """
    if df is None or df.empty:
        return None, None
    df = _flatten(df).dropna(subset=["Close"])
    if df.empty:
        return None, None
    days = pd.Index(df.index.date)
    last_day = days[-1]
    today = df[days == last_day]
    earlier = df[days < last_day]
    prev = float(earlier["Close"].iloc[-1]) if not earlier.empty else None
    return today, prev


def build_quote(label: str, symbol: str, proxy: str | None,
                df: pd.DataFrame | None) -> IndexQuote:
    bars, prev = split_sessions(df) if df is not None else (None, None)
    last = float(bars["Close"].iloc[-1]) if bars is not None and not bars.empty else None
    session = str(bars.index[-1].date()) if bars is not None and not bars.empty else None
    return IndexQuote(label=label, symbol=symbol, proxy=proxy, bars=bars,
                      last=last, prev_close=prev, session=session)


def mini_figure(q: IndexQuote, height: int = 150) -> go.Figure:
    """Candles for the session, previous close as a dashed reference.

    Deliberately axis-light: the number that matters is printed in the card
    header above the chart, so the figure carries shape only — no x title, no
    legend, no range slider, and the y axis on the right where the reference
    price sits, the way the reference layout in the brief has it.
    """
    d = q.bars
    fig = go.Figure(go.Candlestick(
        x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"],
        increasing_line_color=rs.TOKENS["good"],
        decreasing_line_color=rs.TOKENS["risk"],
        increasing_fillcolor=rs.TOKENS["good"],
        decreasing_fillcolor=rs.TOKENS["risk"],
        line=dict(width=1), showlegend=False))
    if q.prev_close:
        fig.add_hline(y=q.prev_close, line_width=1, line_dash="dot",
                      line_color=rs.TOKENS["absent"])
    fig.update_layout(
        height=height, margin=dict(l=2, r=2, t=2, b=2),
        xaxis_rangeslider_visible=False, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=rs.MONO, size=9, color=rs.TOKENS["text_muted"]),
        hovermode="x unified")
    # Intraday frames carry only trading hours, so the gap between sessions and
    # the overnight break would otherwise be drawn as empty space.
    fig.update_xaxes(showgrid=False, rangebreaks=[dict(bounds=["sat", "mon"])],
                     tickformat="%H:%M", nticks=5,
                     linecolor=rs.TOKENS["border"])
    fig.update_yaxes(side="right", showgrid=True,
                     gridcolor=rs.TOKENS["border"], nticks=4, tickformat=",.0f")
    return fig


def header_html(q: IndexQuote) -> str:
    """Name · proxy tag · session date on one line, value and change below."""
    fg, _ = rs.tone_colors(q.tone)
    proxy = (f'<span class="tb-micro" style="color:{rs.TOKENS["text_muted"]};">'
             f'{q.proxy}</span>' if q.proxy else "")
    if q.last is None:
        value = f'<div class="tb-stat-val tb-na">{rs.NA}</div>'
    else:
        arrow = "▲" if (q.change or 0) >= 0 else "▼"
        value = (
            f'<div style="display:flex;align-items:baseline;gap:8px;">'
            f'<span class="tb-mono" style="font-size:19px;font-weight:700;'
            f'color:{rs.TOKENS["text"]};">{q.last:,.2f}</span>'
            f'<span class="tb-mono" style="font-size:12.5px;font-weight:700;'
            f'color:{fg};">{arrow} {q.change:+,.2f} '
            f'({q.change_pct:+.2f}%)</span></div>')
    return (
        f'<div style="display:flex;align-items:baseline;gap:7px;flex-wrap:wrap;">'
        f'<span style="font-size:13px;font-weight:700;letter-spacing:.02em;'
        f'color:{rs.TOKENS["text"]};">{q.label}</span>{proxy}'
        f'<span class="tb-micro" style="margin-left:auto;">{q.session or ""}</span>'
        f'</div>{value}')


def absent_html(q: IndexQuote) -> str:
    """What a card renders when the fetch returned nothing."""
    return rs.callout(
        f"{q.label} not loaded.",
        f"Yahoo returned no {INTERVAL} bars for {q.symbol}. The card is left "
        f"empty rather than drawn flat.", tone="absent")


# ──────────────────────────────────────────────────────────────────────────────
# The Streamlit surface
# ──────────────────────────────────────────────────────────────────────────────
# Kept here rather than in dashboard_app.py: the monolith ratchet
# (test_monolith_ratchet.py) exists precisely so that a new surface arrives as a
# module with one call site, not as another forty lines of module-scope page
# body. dashboard_app.py says WHERE the strip goes; this file is everything else.
def fetch_quotes() -> list[IndexQuote]:
    """One yfinance request per index. Cached by `render` for five minutes —
    the strip is the top of one page, and refetching four indices on every
    Streamlit rerun would cost four round-trips per widget click."""
    import yfinance as yf
    out = []
    for label, symbol, proxy in INDICES:
        try:
            df = yf.download(symbol, period=PERIOD, interval=INTERVAL,
                             progress=False, auto_adjust=False)
        except Exception:
            df = None
        out.append(build_quote(label, symbol, proxy, df))
    return out


def render() -> None:
    """Four columns: a toned header card over the session's candles."""
    import streamlit as st

    quotes = st.cache_data(ttl=300, show_spinner=False)(fetch_quotes)()
    for col, q in zip(st.columns(len(quotes)), quotes):
        with col:
            st.markdown(rs.card(header_html(q), tone=q.tone),
                        unsafe_allow_html=True)
            if q.bars is None or q.bars.empty:
                st.markdown(absent_html(q), unsafe_allow_html=True)
            else:
                st.plotly_chart(mini_figure(q), width="stretch",
                                config={"displayModeBar": False},
                                key=f"idxstrip_{q.symbol}")
    st.caption(
        f"{INTERVAL} bars, latest session; the dotted line is the previous "
        "session's close, which is also what the % is measured against. "
        "NIFTY NEXT 50 has no Yahoo index feed with intraday data, so that card "
        "plots JUNIORBEES, the Next 50 ETF — a proxy, and labelled as one. "
        "Cached 5 minutes.")
