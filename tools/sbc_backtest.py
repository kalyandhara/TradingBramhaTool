#!/usr/bin/env python3
"""
sbc_backtest.py — do SBC Moon reversal windows land on real 15-min reversals?

Cross-checks the SBC reversal-window forecast against actual intraday swing
pivots on 15-minute candles (yfinance OHLC — the same series a TradingView 15m
chart shows). BTC-USD is the cleanest test bed: it trades 24/7, so EVERY
reversal window (any hour) is testable, not just an exchange session.

Method
------
1. Pull 60d of 15m OHLC; convert timestamps to IST.
2. Detect swing pivots: a bar whose high is the max (or low the min) over
   ±PIVOT_K bars — these are the actual intraday reversals.
3. For each day, compute SBC reversal windows (Moon pada / nakshatra boundary
   crossings), fast Moon-only ephem.
4. Match: a pivot "hits" if its time is within MATCH_TOL min of a window centre.
5. Score vs a random baseline:
     coverage   = fraction of the day the windows (±MATCH_TOL) cover
     recall     = fraction of pivots that hit a window
     lift       = recall / coverage   (>1 = forecast beats chance)
   Lift ~1 means no signal; lift >>1 means windows cluster real reversals.

Honest limits: 60 days is a small sample; yfinance 15m ≈ TradingView but not
identical; pivots are one definition of "reversal". Reported, not hidden.

CLI:
  py -3 tools/sbc_backtest.py BTC-USD --granularity pada
  py -3 tools/sbc_backtest.py GC=F --granularity nakshatra --pivot-k 3
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

import ephem
import pandas as pd
import yfinance as yf

from sarvatobhadra_chakra import lahiri_ayanamsa

IST = timezone(timedelta(hours=5, minutes=30))
NAK_SPAN = 360.0 / 27.0
PADA_SPAN = NAK_SPAN / 4.0


def _moon_idx_pada(dt_utc: datetime) -> Tuple[int, int]:
    m = ephem.Moon()
    m.compute(ephem.Date(dt_utc))
    trop = float(ephem.Ecliptic(m).lon) * 180.0 / 3.141592653589793
    sid = (trop - lahiri_ayanamsa(dt_utc)) % 360.0
    idx = int(sid // NAK_SPAN) % 27
    within = sid - idx * NAK_SPAN
    pada = int(within // PADA_SPAN) + 1
    return idx, pada


def reversal_centers(day_ist: datetime, granularity: str) -> List[datetime]:
    """IST datetimes of Moon boundary crossings within `day_ist` (tz-aware)."""
    start = day_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    centers: List[datetime] = []
    step = timedelta(minutes=5)
    prev = None
    t = start
    end = start + timedelta(hours=24)
    while t <= end:
        idx, pada = _moon_idx_pada(t.astimezone(timezone.utc).replace(tzinfo=None))
        if prev is not None:
            crossed = (idx != prev[0]) if granularity == "nakshatra" \
                else (idx != prev[0] or pada != prev[1])
            if crossed:
                centers.append(t - step / 2)
        prev = (idx, pada)
        t += step
    return centers


def swing_pivots(df: pd.DataFrame, k: int) -> List[pd.Timestamp]:
    """Timestamps of swing highs/lows (local extreme over +/-k bars)."""
    highs, lows = df["High"].values, df["Low"].values
    idxs = df.index
    piv: List[pd.Timestamp] = []
    for i in range(k, len(df) - k):
        win_h = highs[i - k:i + k + 1]
        win_l = lows[i - k:i + k + 1]
        if highs[i] == win_h.max() or lows[i] == win_l.min():
            piv.append(idxs[i])
    return piv


def daily_extreme_pivots(df: pd.DataFrame) -> List[pd.Timestamp]:
    """The bar of the day's high and the day's low — 2 pivots/day.

    This is the strict SBC claim: the SESSION high/low should land in a window.
    """
    piv: List[pd.Timestamp] = []
    for _, day in df.groupby(df.index.normalize()):
        piv.append(day["High"].idxmax())
        piv.append(day["Low"].idxmin())
    return piv


def run_backtest(symbol: str, granularity: str, pivot_k: int,
                 match_tol: int, daily_extremes: bool = False) -> None:
    print(f"Downloading {symbol} 60d 15m ...")
    df = yf.download(symbol, period="60d", interval="15m", progress=False,
                     auto_adjust=False)
    if df.empty:
        print("No data.")
        return
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # to IST
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(IST)

    days = sorted({ts.normalize() for ts in df.index})
    pivots = (daily_extreme_pivots(df) if daily_extremes
              else swing_pivots(df, pivot_k))
    ptype = "daily H/L extremes" if daily_extremes else f"swing pivots k={pivot_k}"
    print(f"{len(df)} bars · {len(days)} days · {len(pivots)} {ptype}")

    # collect all window centres across the sample
    all_centers: List[datetime] = []
    for d in days:
        all_centers.extend(reversal_centers(d.to_pydatetime(), granularity))

    # match pivots to nearest window centre
    tol = timedelta(minutes=match_tol)
    hits = 0
    for p in pivots:
        p_dt = p.to_pydatetime()
        if any(abs(p_dt - c) <= tol for c in all_centers):
            hits += 1
    recall = hits / len(pivots) if pivots else 0.0

    # baseline coverage: union of [center-tol, center+tol] over total span
    span_min = (df.index.max() - df.index.min()).total_seconds() / 60.0
    covered = _union_minutes(all_centers, match_tol)
    coverage = covered / span_min if span_min else 0.0
    lift = (recall / coverage) if coverage else 0.0

    # precision: windows (within data span) that caught a pivot
    lo, hi = df.index.min().to_pydatetime(), df.index.max().to_pydatetime()
    in_span = [c for c in all_centers if lo <= c <= hi]
    pivset = [p.to_pydatetime() for p in pivots]
    win_hits = sum(1 for c in in_span
                   if any(abs(pp - c) <= tol for pp in pivset))
    precision = win_hits / len(in_span) if in_span else 0.0

    # significance: is `hits` out of len(pivots) above the null coverage p?
    n, p = len(pivots), coverage
    exp = n * p
    sd = (n * p * (1 - p)) ** 0.5 if n and 0 < p < 1 else 0.0
    z = (hits - exp) / sd if sd else 0.0
    # one-tailed normal p-value
    import math
    pval = 0.5 * math.erfc(z / (2 ** 0.5)) if z > 0 else 1.0
    sig = ("SIGNIFICANT" if pval < 0.05 else
           "not significant" if pval > 0.10 else "marginal")

    print(f"\nGranularity={granularity} · match_tol=+/-{match_tol}m")
    print(f"  windows in span : {len(in_span)}")
    print(f"  RECALL  (pivots within a window) : {recall:6.1%}  "
          f"({hits}/{n})")
    print(f"  baseline coverage (random)       : {coverage:6.1%}  "
          f"(exp {exp:.1f})")
    print(f"  LIFT   (recall / coverage)       : {lift:5.2f}x")
    print(f"  z = {z:+.2f} · one-tailed p = {pval:.3f} -> {sig}")
    print(f"  PRECISION (windows with a pivot) : {precision:6.1%}")


def _union_minutes(centers: List[datetime], tol: int) -> float:
    if not centers:
        return 0.0
    ivals = sorted((c - timedelta(minutes=tol), c + timedelta(minutes=tol))
                   for c in centers)
    total = 0.0
    cs, ce = ivals[0]
    for s, e in ivals[1:]:
        if s <= ce:
            ce = max(ce, e)
        else:
            total += (ce - cs).total_seconds() / 60.0
            cs, ce = s, e
    total += (ce - cs).total_seconds() / 60.0
    return total


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", nargs="?", default="BTC-USD")
    ap.add_argument("--granularity", default="pada",
                    choices=["pada", "nakshatra"])
    ap.add_argument("--pivot-k", type=int, default=2)
    ap.add_argument("--match-tol", type=int, default=15)
    ap.add_argument("--daily-extremes", action="store_true",
                    help="test only each day's high/low bar (strict SBC claim)")
    a = ap.parse_args()
    run_backtest(a.symbol, a.granularity, a.pivot_k, a.match_tol,
                 a.daily_extremes)
