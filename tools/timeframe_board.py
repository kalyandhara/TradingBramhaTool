#!/usr/bin/env python3
"""timeframe_board.py — one company across six horizons, on one screen.

Six panels: Hourly · Daily · Monthly · Half-yearly · Yearly · Year-on-year.

The point is PERSPECTIVE, not signal. A daily chart in a downtrend and a yearly
chart in a decade-long base are both true, and reading either alone is how a
position gets sized against the wrong picture. Nothing here emits a trigger; it
is deliberately the same "context, not a signal" stance the momentum meter takes.

── Where the bars come from, and the one hard limit ─────────────────────────
Yahoo's coarsest interval is ``3mo``. There is no 6-month or yearly interval, so
those panels are RESAMPLED from daily bars. That is exact rather than an
approximation — an OHLC aggregate of daily bars *is* the true half-yearly candle
(first open, max high, min low, last close) — and it has the side benefit that
half-yearly, yearly and daily all come from ONE download instead of three.

The real constraint is the other end: **Yahoo serves roughly 730 trading SESSIONS
of hourly bars** — measured, not assumed (see YF_HOURLY_MAX_SESSIONS). In calendar
terms that is about three years, not the two that "730d" suggests. The module
cannot widen it, so the hourly panel reports the span it actually received rather
than implying more. `intraday_store.py` exists precisely because that window is
lost if nobody accumulates it.

── Sparse panels say so instead of drawing four candles ─────────────────────
A 2021 listing has four yearly bars. Four candles rendered as a chart look like a
chart and invite the same reading as forty; the panel therefore refuses below
``MIN_BARS`` and states the years available. A refusal is information; a
four-candle "yearly trend" is not.

── The Y-on-Y panel is a comparison, not an interval ────────────────────────
Every calendar year replotted from its own first session = 100, overlaid on one
axis. It answers "is this year tracking above or below how this name usually
goes", which no single-interval panel can. The current year is drawn heavy and
every prior year light: with ten equal lines the eye cannot find today.

Rebasing to each year's OWN start (not to a common date) is what makes the lines
comparable — it removes the price level so a ₹700 year and a ₹25 year sit on the
same axis. It also means the panel says nothing about absolute performance, which
is what the other five panels are for.

CLI:
  py -3 tools/timeframe_board.py UCOBANK
  py -3 tools/timeframe_board.py MOLDTKPAC --out board.png
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

#: Panels, in reading order: fast to slow, then the comparison.
PANELS: tuple[str, ...] = ("Hourly", "Daily", "Monthly",
                           "Half-yearly", "Yearly", "Year-on-year")

#: Below this many bars a candle panel refuses rather than drawing a stub.
#: Six is the point where a reader stops seeing "a few bars" and starts seeing
#: "a trend", which is exactly the misreading to prevent.
MIN_BARS = 6

#: pandas offset aliases for the resampled panels. "2QE" is half-yearly anchored
#: on quarter ends, "YE" calendar-yearly. Both are period-END anchored so a
#: partial current period shows as a partial bar rather than being dropped.
RESAMPLE = {"Half-yearly": "2QE", "Yearly": "YE"}

#: Yahoo's hourly window, in TRADING SESSIONS rather than calendar days —
#: measured 2026-09-06 on UCOBANK, not assumed: period="730d" returned 5,053 bars
#: over 724 unique sessions spanning 1,074 calendar days. Calling it "730 days"
#: implies two years and delivers three, so the unit is stated.
YF_HOURLY_MAX_SESSIONS = 730


@dataclass
class Panel:
    """One rendered panel, or one honest refusal."""
    name: str
    df: "pd.DataFrame | None" = None          # OHLC, DatetimeIndex
    lines: dict = field(default_factory=dict)  # Y-on-Y: {label: Series}
    note: str | None = None                    # why it is empty / what to know
    ok: bool = False


def _ohlc_resample(daily: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Daily bars -> coarser OHLC. Exact, not approximate."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in daily.columns:
        agg["volume"] = "sum"
    out = daily.resample(rule).agg(agg)
    return out.dropna(subset=["open", "high", "low", "close"])


def _year_on_year(daily: pd.DataFrame, max_years: int = 6) -> dict[str, pd.Series]:
    """Each calendar year rebased to its own first session = 100.

    Indexed by day-of-year so the lines superimpose. Rebasing to each year's own
    start is deliberate: it strips the price level, which is the only way a year
    trading at 700 and a year trading at 25 can share an axis.
    """
    out: dict[str, pd.Series] = {}
    close = daily["close"].astype(float)
    for year, grp in close.groupby(close.index.year):
        if len(grp) < 20:                      # a stub year is noise on this panel
            continue
        base = float(grp.iloc[0])
        if not (base > 0):
            continue
        s = (grp / base - 1.0) * 100.0
        s.index = grp.index.dayofyear
        out[str(year)] = s
    if len(out) > max_years:                   # keep the most recent N, newest last
        for k in sorted(out)[:-max_years]:
            del out[k]
    return out


def build(symbol: str, *, daily: pd.DataFrame | None = None,
          hourly: pd.DataFrame | None = None) -> list[Panel]:
    """Six panels for `symbol`. Frames may be injected, which is how this is tested.

    Every panel is independent: one empty source degrades that panel and no other.
    A board that renders five of six with a stated reason for the sixth is more
    useful than one that raises.
    """
    panels: list[Panel] = []

    if daily is None or daily.empty:
        return [Panel(n, note="no daily history for this symbol") for n in PANELS]

    daily = daily.copy()
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()

    # ── Hourly ───────────────────────────────────────────────────────────────
    if hourly is not None and not hourly.empty and len(hourly) >= MIN_BARS:
        h = hourly.copy()
        h.index = pd.to_datetime(h.index)
        span = (h.index.max() - h.index.min()).days
        sessions = h.index.normalize().nunique()
        panels.append(Panel("Hourly", df=h.sort_index(), ok=True,
                            note=f"{len(h):,} bars · {sessions} sessions over {span}d "
                                 f"(Yahoo caps hourly near "
                                 f"{YF_HOURLY_MAX_SESSIONS} sessions)"))
    else:
        panels.append(Panel("Hourly",
                            note=f"no hourly bars — Yahoo caps hourly near "
                                 f"{YF_HOURLY_MAX_SESSIONS} sessions and returned none"))

    # ── Daily ────────────────────────────────────────────────────────────────
    panels.append(Panel("Daily", df=daily.tail(250), ok=len(daily) >= MIN_BARS,
                        note=None if len(daily) >= MIN_BARS else "too few daily bars"))

    # ── Monthly / Half-yearly / Yearly, all resampled from the one daily frame ──
    for name, rule in (("Monthly", "ME"), *RESAMPLE.items()):
        r = _ohlc_resample(daily, rule)
        if len(r) >= MIN_BARS:
            years = (daily.index.max() - daily.index.min()).days / 365.25
            panels.append(Panel(name, df=r, ok=True,
                                note=f"{len(r)} bars from {years:.1f}y of daily history"))
        else:
            years = (daily.index.max() - daily.index.min()).days / 365.25
            panels.append(Panel(
                name,
                note=f"needs ~{MIN_BARS} bars, history gives {len(r)} "
                     f"({years:.1f}y listed) — too few to read as a trend"))

    # ── Year-on-year ─────────────────────────────────────────────────────────
    lines = _year_on_year(daily)
    if len(lines) >= 2:
        panels.append(Panel("Year-on-year", lines=lines, ok=True,
                            note=f"{len(lines)} years, each rebased to its own "
                                 f"1 Jan = 0%"))
    else:
        panels.append(Panel("Year-on-year",
                            note="needs two full calendar years to compare"))

    order = {n: i for i, n in enumerate(PANELS)}
    return sorted(panels, key=lambda p: order[p.name])


def _fetch(symbol: str):
    """Daily + hourly for the CLI. Kept out of `build` so tests need no network."""
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    import yfinance as yf
    tk = symbol if "." in symbol else f"{symbol}.NS"
    daily = yf.download(tk, period="max", interval="1d",
                        progress=False, auto_adjust=False)
    hourly = yf.download(tk, period="730d", interval="1h",
                         progress=False, auto_adjust=False)

    def _flat(df):
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower() for c in df.columns]
        return df[[c for c in ("open", "high", "low", "close", "volume")
                   if c in df.columns]]

    return _flat(daily), _flat(hourly)


def main() -> int:
    ap = argparse.ArgumentParser(description="Six-horizon board for one symbol")
    ap.add_argument("symbol")
    ap.add_argument("--out", help="write a PNG here instead of printing a summary")
    args = ap.parse_args()

    daily, hourly = _fetch(args.symbol)
    panels = build(args.symbol, daily=daily, hourly=hourly)
    for p in panels:
        n = 0 if p.df is None else len(p.df)
        n = n or len(p.lines)
        print(f"  {p.name:<14} {'OK ' if p.ok else '-- '} n={n:<6d} {p.note or ''}")
    if args.out:
        print(f"(PNG export not implemented — the dashboard renders these with plotly)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
