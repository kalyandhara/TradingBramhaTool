"""Breadth strip — the market's internals as two-sided bars, plus the verdict
card's 50/200 SMA quadrant row (`sma_quadrants` / `quadrant_html`).

The SMA50 and SMA200 bars (3 and 4 below) moved INTO the verdict card as one
four-bucket row — above both / 50 only / 200 only / below both — so the strip
now draws bars 1, 2 and 5. The notes below still describe them.

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
#: 52 weeks of NSE sessions.
LOOKBACK_52W = 250
#: 2y, not 1y: a 1y fetch returns ~248 sessions, one short of LOOKBACK_52W, so
#: the New High / New Low bar read DATA N/A for every name. 2y also leaves the
#: 200 SMA a full window on names that listed inside the last two years.
HISTORY_PERIOD = "2y"


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


#: The four SMA quadrants, bullish first. (key, label, glyph, reading)
QUADRANTS = (
    ("both",      "Above both",      "▲▲", "uptrend intact"),
    ("fast_only", "Above 50 only",   "▲",  "recovering"),
    ("slow_only", "Above 200 only",  "△",  "pulling back"),
    ("neither",   "Below both",      "▼▼", "downtrend"),
)


def _classify(df: pd.DataFrame | None, fast: int, slow: int) -> dict | None:
    """One name's bucket and distances, or None if it has < `slow` closes."""
    c = _closes(df)
    if c is None or len(c) < slow:
        return None
    last = float(c.iloc[-1])
    m_fast, m_slow = float(c.tail(fast).mean()), float(c.tail(slow).mean())
    above_fast, above_slow = last >= m_fast, last >= m_slow
    bucket = ("both" if above_fast and above_slow else
              "fast_only" if above_fast else
              "slow_only" if above_slow else "neither")
    prev = float(c.iloc[-2]) if len(c) > 1 else None
    return {"bucket": bucket, "close": last,
            "vs_fast": (last / m_fast - 1) * 100.0,
            "vs_slow": (last / m_slow - 1) * 100.0,
            "chg_1d": (last / prev - 1) * 100.0 if prev else None}


#: Bullish buckets list the names furthest ABOVE the 50 SMA first (leaders);
#: bearish buckets the names furthest BELOW it first (weakest). Same column,
#: each bucket's own direction.
_RANK_DESC = {"both": True, "fast_only": True, "slow_only": False, "neither": False}


def quadrant_members(hist: dict[str, pd.DataFrame], fast: int = 50, slow: int = 200,
                     members: set[str] | None = None,
                     top: int | None = None) -> dict[str, pd.DataFrame]:
    """The names in each quadrant, ranked by % from the `fast` SMA in that
    bucket's own direction (see `_RANK_DESC`). Same eligibility as
    `sma_quadrants`, so each table's length before `top` equals its count.

    Columns: Symbol, Close, "% vs SMA{fast}", "% vs SMA{slow}", "1D %".
    """
    universe = hist if members is None else {s: hist.get(s) for s in members}
    rows: dict[str, list] = {k: [] for k, *_ in QUADRANTS}
    for sym, df in universe.items():
        r = _classify(df, fast, slow)
        if r is not None:
            rows[r["bucket"]].append((sym, r["close"], r["vs_fast"], r["vs_slow"],
                                      r["chg_1d"]))
    cols = ["Symbol", "Close", f"% vs SMA{fast}", f"% vs SMA{slow}", "1D %"]
    out = {}
    for k, rs_ in rows.items():
        df = pd.DataFrame(rs_, columns=cols).sort_values(
            cols[2], ascending=not _RANK_DESC[k], kind="mergesort")
        out[k] = (df.head(top) if top else df).reset_index(drop=True)
    return out


def sma_quadrants(hist: dict[str, pd.DataFrame], fast: int = 50, slow: int = 200,
                  members: set[str] | None = None) -> dict:
    """Each name's last close against its OWN `fast` and `slow` SMA, crossed.

    One denominator for all four buckets: names with at least `slow` closes.
    A name too young for the slow SMA is excluded from every bucket rather than
    counted on the fast one alone, so the four always sum to `covered`. The
    plain above-SMA50 / above-SMA200 counts are the sums of two buckets each.

    `members` restricts the count to a sub-index (e.g. NIFTY 50 inside the
    NIFTY 500 download); names in `members` with no history count as missing.
    """
    counts = {k: 0 for k, *_ in QUADRANTS}
    covered = short = 0
    universe = hist if members is None else {s: hist.get(s) for s in members}
    for df in universe.values():
        row = _classify(df, fast, slow)
        if row is None:
            short += 1
            continue
        counts[row["bucket"]] += 1
        covered += 1
    pcts = {k: (v / covered * 100.0 if covered else None) for k, v in counts.items()}
    return {"counts": counts, "pcts": pcts, "covered": covered,
            "excluded": short, "fast": fast, "slow": slow}


def build_bars(hist: dict[str, pd.DataFrame],
               reading: dict | None) -> list[BreadthBar]:
    """The strip's bars. `reading` is the persisted sentiment reading, which
    owns both the Adv/Decl counts and the score.

    The separate SMA50 / SMA200 bars are gone: the verdict card's quadrant row
    (`sma_quadrants`) carries both, crossed, over the same download.
    """
    reading = reading or {}
    ad = (reading.get("inputs") or {}).get("advance_decline")
    return [
        advance_decline_bar(ad, reading.get("reading_date")),
        high_low_bar(hist),
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


#: Segment fills, bullish → bearish. Lime sits between good and accent so the
#: two green segments stay apart; the glyphs carry the order for readers who
#: cannot separate the hues (B-162).
_QUAD_FILL = {"both": rs.TOKENS["good"], "fast_only": "#4d7c0f",
              "slow_only": rs.TOKENS["accent"], "neither": rs.TOKENS["risk"]}
_QUAD_TEXT = {"both": rs.TOKENS["good"], "fast_only": rs.TOKENS["good"],
              "slow_only": rs.TOKENS["accent"], "neither": rs.TOKENS["risk"]}


def _quad_inline(q: dict) -> str:
    """`22 · 9 · 5 · 14` with each count in its bucket's colour."""
    return " · ".join(
        f'<span class="tb-mono" style="color:{_QUAD_TEXT[k]};">{g} {q["counts"][k]}</span>'
        for k, _, g, _ in QUADRANTS)


def quadrant_html(q: dict, universe: str, as_of: str | None = None,
                  sub: tuple[str, dict] | None = None) -> str:
    """The Breadth row inside the verdict card. No card of its own: it is a
    section of the verdict card, separated by the same rule as Regime.

    Labelled "context — does not vote": `build_verdict` never reads it, and the
    label says so, so a red split under a TRADE verdict is not read as a veto.
    `sub` is an optional (label, quadrants) for a sub-index, shown as one line.
    """
    t = rs.TOKENS
    rule = (f'border-top:1px solid {t["border"]};margin-top:10px;padding-top:8px;')
    covered, excl = q["covered"], q["excluded"]
    head = (
        f'<div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;">'
        f'<span class="tb-micro">Breadth</span>'
        f'<span style="font-size:12px;color:{t["text_body"]};">{universe} · each stock '
        f'vs its own {q["fast"]} / {q["slow"]} SMA</span>'
        f'<span style="font-size:11px;color:{t["text_muted"]};">'
        + (f'close {as_of} · ' if as_of else "")
        + f'<span class="tb-mono">{covered}</span> measured'
        + (f', <span class="tb-mono">{excl}</span> under {q["slow"]} sessions excluded'
           if excl else "")
        + '</span>'
        f'<span style="margin-left:auto;font-size:11px;color:{t["text_muted"]};'
        f'font-style:italic;">context — does not vote</span></div>')
    if not covered:
        return (f'<div style="{rule}">{head}<div class="tb-stat-val tb-na">{rs.NA}</div>'
                f'</div>')
    segs = []
    for i, (k, *_r) in enumerate(QUADRANTS):
        p = q["pcts"][k] or 0.0
        if i:
            segs.append(f'<div style="width:2px;flex-shrink:0;background:{t["surface"]};"></div>')
        segs.append(f'<div style="width:{p:.2f}%;background:{_QUAD_FILL[k]};"></div>')
    bar = (f'<div style="display:flex;height:10px;border-radius:5px;overflow:hidden;'
           f'margin-top:6px;background:{t["absent_soft"]};">{"".join(segs)}</div>')
    cols = "".join(
        f'<div style="flex:1 1 0;min-width:110px;">'
        f'<div style="font-size:11.5px;font-weight:700;color:{_QUAD_TEXT[k]};">{g} {label}</div>'
        f'<div class="tb-mono" style="font-size:13px;color:{_QUAD_TEXT[k]};">'
        f'{q["pcts"][k]:.1f}% <span style="font-size:11px;">({q["counts"][k]:,})</span></div>'
        f'<div style="font-size:11px;color:{t["text_muted"]};">{reading}</div></div>'
        for k, label, g, reading in QUADRANTS)
    sub_line = ""
    if sub and sub[1]["covered"]:
        sub_line = (f'<div style="font-size:11.5px;color:{t["text_muted"]};margin-top:4px;">'
                    f'{sub[0]} ({sub[1]["covered"]} measured): {_quad_inline(sub[1])}</div>')
    return (f'<div style="{rule}">{head}{bar}'
            f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px;">{cols}</div>'
            f'{sub_line}</div>')


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


def cached_history() -> dict[str, pd.DataFrame]:
    """`fetch_history` behind one 15-minute cache, shared by the verdict card's
    quadrant row and the strip, so Home downloads the NIFTY 500 once."""
    import streamlit as st

    return st.cache_data(
        ttl=900, show_spinner="Measuring NIFTY 500 breadth …")(fetch_history)()


def nifty50_members() -> set[str]:
    """NIFTY 50 symbols (constituent CSV, cached by nse_universe). Empty set if
    unreachable — the sub-index line is then simply not drawn."""
    try:
        import nse_universe as nu
        return {str(r["symbol"]).strip() for r in nu.fetch_constituents("nifty50")
                if r.get("symbol")}
    except Exception:
        return set()


def last_close_date(hist: dict[str, pd.DataFrame]) -> str | None:
    """Newest bar date across the download, as YYYY-MM-DD, or None."""
    newest = None
    for df in hist.values():
        if df is None or getattr(df, "empty", True):
            continue
        ix = df.index[-1]
        if isinstance(ix, pd.Timestamp) and (newest is None or ix > newest):
            newest = ix
    return newest.strftime("%Y-%m-%d") if newest is not None else None


#: The bucket tables' own columns after Close · 1D, in the watch_rail
#: component's {key, label, fmt, width} shape (B-180 hover rows).
BUCKET_COLUMNS = [
    {"key": "% vs SMA50", "label": "vs SMA50", "fmt": "pct", "width": 68},
    {"key": "% vs SMA200", "label": "vs SMA200", "fmt": "pct", "width": 72},
]


def _bucket_table(k: str, df: pd.DataFrame, fmt: dict) -> None:
    """One bucket as B-180 hover rows (ticker, sparkline, hover chart,
    Analyze link); the plain dataframe when the component is unavailable."""
    import streamlit as st
    import desk_pages as dpages

    shown = dpages.home_scan_table(
        df.rename(columns={"Symbol": "symbol"}), BUCKET_COLUMNS, key=f"bq_{k}_hv",
        close_col="Close", pct_col="1D %", pct_label="Close · 1D", no_check=True)
    if shown is None:
        st.dataframe(df, hide_index=True, column_config=fmt, use_container_width=True)


def render_members(hist: dict[str, pd.DataFrame], nifty50: set[str]) -> None:
    """Expander under the verdict card: the top N names in each quadrant.

    Context like the row above it — a list of who is where, not a buy list.
    """
    import streamlit as st

    with st.expander("Top names in each breadth bucket"):
        c1, c2 = st.columns([2, 1])
        with c1:
            uni = st.radio("Universe", [UNIVERSE_LABEL, "NIFTY 50"], horizontal=True,
                           key="bq_universe", disabled=not nifty50)
        with c2:
            n = st.radio("Show top", [5, 10], index=1, horizontal=True, key="bq_top")
        tables = quadrant_members(
            hist, members=nifty50 if uni == "NIFTY 50" else None, top=n)
        fmt = {"Close": st.column_config.NumberColumn(format="%.2f"),
               "% vs SMA50": st.column_config.NumberColumn(format="%+.1f%%"),
               "% vs SMA200": st.column_config.NumberColumn(format="%+.1f%%"),
               "1D %": st.column_config.NumberColumn(format="%+.2f%%")}
        for row in (QUADRANTS[:2], QUADRANTS[2:]):
            for col, (k, label, g, reading) in zip(st.columns(2), row):
                with col:
                    order = "furthest above" if _RANK_DESC[k] else "furthest below"
                    st.markdown(
                        f'<div style="font-size:12.5px;font-weight:700;color:{_QUAD_TEXT[k]};">'
                        f'{g} {label} <span style="font-weight:400;color:'
                        f'{rs.TOKENS["text_muted"]};">· {reading} · {order} the 50 SMA first'
                        f'</span></div>', unsafe_allow_html=True)
                    if tables[k].empty:
                        st.caption("No names in this bucket.")
                    else:
                        _bucket_table(k, tables[k], fmt)
        st.caption(
            "Ranked by % from each stock's own 50-day SMA, in the bucket's direction: "
            "the two above-50 buckets list the strongest first, the two below-50 "
            "buckets the weakest first. Hover a ticker for its chart; Analyze opens "
            "it in the Stock Analyzer. Last close of the cached download — "
            "intraday this is the forming bar. Context only; not a recommendation.")


def render(reading: dict | None) -> None:
    """The strip's bars, plus the coverage line under them."""
    import streamlit as st

    hist = cached_history()
    bars = build_bars(hist, reading)
    for col, b in zip(st.columns(len(bars)), bars):
        with col:
            st.markdown(bar_html(b), unsafe_allow_html=True)
    st.expander("How this is measured — breadth bars").caption(
        "Each bar names its own universe — they are not the same one. "
        "Advancing/Declining is the whole EQ market from the bhavcopy of the "
        "sentiment reading dated under that bar — the same count the verdict "
        "above flags, and as old as that reading is; New High/New Low is the "
        f"{UNIVERSE_LABEL} ({len(hist)} of 500 names loaded), measured on "
        "closes — the same download as the verdict card's 50/200 SMA breadth "
        "row; Bull/Bear is this desk's own sentiment score restated as a "
        "split, not a survey of anyone. Cached 15 minutes."
    )
