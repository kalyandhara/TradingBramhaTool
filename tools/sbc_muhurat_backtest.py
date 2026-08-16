#!/usr/bin/env python3
"""
sbc_muhurat_backtest.py — does Abhijit MUHURAT precede a Nifty reversal?

Abhijit Muhurat (distinct from the monthly Abhijit *nakshatra*) is the daily
8th-of-15 muhurta, a ~48-minute window centred on LOCAL SOLAR NOON. Hypothesis
under test (user's, refined): the muhurat does not mark the reversal exactly —
it PRECEDES one, in the following ~30-60 minutes. So we test a forward window
[muhurat_start, muhurat_start + LOOKAHEAD] and ask whether a reversal lands
inside it more often than a same-length window placed randomly in the session.

Reversal definitions (both reported):
  * DAILY EXTREME : the session's high bar or low bar falls in the window
  * SWING PIVOT   : any local extreme over +/-k bars falls in the window

Market-closed rule: if the muhurat falls outside the Nifty session (weekend /
holiday / pre-open), the "energy extends to the next open" — we shift the
forward window to begin at the next session open.

Baseline is computed per-day by sliding a same-length window across that day's
session (brute force), so the lift is against that day's own pivot density, not
a global average. Honest limits: ~60 trading days of 15m data (Yahoo cap);
yfinance 15m ~ TradingView not identical.

CLI:
  py -3 tools/sbc_muhurat_backtest.py --lookahead 60 --mode extreme
  py -3 tools/sbc_muhurat_backtest.py --lookahead 30 --mode swing --pivot-k 3
"""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timedelta, timezone, time
from typing import List, Optional, Tuple

import ephem
import pandas as pd
import yfinance as yf

IST = timezone(timedelta(hours=5, minutes=30))
MUMBAI_LAT, MUMBAI_LON = "19.076", "72.8777"
SESSION_OPEN, SESSION_CLOSE = time(9, 15), time(15, 30)
BAR = timedelta(minutes=15)


def solar_noon_ist(day: datetime) -> Tuple[datetime, float]:
    """(solar noon IST, daylength minutes) at Mumbai for a calendar day."""
    obs = ephem.Observer()
    obs.lat, obs.lon = MUMBAI_LAT, MUMBAI_LON
    obs.date = ephem.Date(datetime(day.year, day.month, day.day, 0, 0))
    noon_utc = obs.next_transit(ephem.Sun()).datetime()
    obs.date = ephem.Date(datetime(day.year, day.month, day.day, 0, 0))
    rise = obs.next_rising(ephem.Sun()).datetime()
    sett = obs.next_setting(ephem.Sun()).datetime()
    daylen = (sett - rise).total_seconds() / 60.0
    return noon_utc.replace(tzinfo=timezone.utc).astimezone(IST), daylen


def abhijit_window(day: datetime) -> Tuple[datetime, datetime]:
    """Abhijit muhurat [start,end] IST = solar noon +/- (daylength/30)."""
    noon, daylen = solar_noon_ist(day)
    half = timedelta(minutes=daylen / 30.0)     # muhurta = daylen/15, half each side
    return noon - half, noon + half


def swing_pivot_times(day_df: pd.DataFrame, k: int) -> List[pd.Timestamp]:
    highs, lows, idx = day_df["High"].values, day_df["Low"].values, day_df.index
    out = []
    for i in range(k, len(day_df) - k):
        if highs[i] == highs[i - k:i + k + 1].max() or \
           lows[i] == lows[i - k:i + k + 1].min():
            out.append(idx[i])
    return out


def _reversal_times(day_df: pd.DataFrame, mode: str, k: int) -> List[pd.Timestamp]:
    if mode == "extreme":
        return [day_df["High"].idxmax(), day_df["Low"].idxmin()]
    return swing_pivot_times(day_df, k)


def run(lookahead: int, mode: str, pivot_k: int) -> None:
    print("Downloading ^NSEI 60d 15m ...")
    df = yf.download("^NSEI", period="60d", interval="15m", progress=False,
                     auto_adjust=False)
    if df.empty:
        print("No data.")
        return
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(IST)

    day_keys = sorted({ts.normalize() for ts in df.index})
    la = timedelta(minutes=lookahead)

    obs_hits = 0
    exp_sum = 0.0
    n_days = 0
    muhurat_in_session = 0
    for dk in day_keys:
        day_df = df[df.index.normalize() == dk]
        if len(day_df) < 6:
            continue
        n_days += 1
        revs = _reversal_times(day_df, mode, pivot_k)

        a_start, a_end = abhijit_window(dk.to_pydatetime().replace(tzinfo=IST))
        # forward window begins at muhurat start; if muhurat before open, clamp
        sess_start = day_df.index.min()
        sess_end = day_df.index.max()
        if a_start < sess_start:              # muhurat pre-open -> extends to open
            w_start = sess_start
        else:
            w_start = a_start
            muhurat_in_session += 1
        w_end = w_start + la
        obs = any(w_start <= r <= w_end for r in revs)
        obs_hits += 1 if obs else 0

        # per-day baseline: slide same-length window across the session
        positions, hit_positions = 0, 0
        t = sess_start
        while t + la <= sess_end:
            positions += 1
            if any(t <= r <= t + la for r in revs):
                hit_positions += 1
            t += BAR
        exp_sum += (hit_positions / positions) if positions else 0.0

    obs_rate = obs_hits / n_days if n_days else 0.0
    base_rate = exp_sum / n_days if n_days else 0.0
    lift = obs_rate / base_rate if base_rate else 0.0
    # significance: observed hits vs Poisson-binomial mean exp_sum
    var = exp_sum  # approx (sum p(1-p) <= sum p); conservative upper bound on z
    # use proper sum p(1-p): recompute would need storing; approximate with mean
    sd = math.sqrt(max(exp_sum * (1 - base_rate), 1e-9))
    z = (obs_hits - exp_sum) / sd if sd else 0.0
    pval = 0.5 * math.erfc(z / (2 ** 0.5)) if z > 0 else 1.0
    sig = ("SIGNIFICANT" if pval < 0.05 else
           "marginal" if pval < 0.10 else "not significant")

    print(f"\nAbhijit Muhurat -> Nifty reversal  ·  mode={mode}"
          f"{' k='+str(pivot_k) if mode=='swing' else ''}  ·  lookahead={lookahead}m")
    print(f"  trading days              : {n_days} "
          f"({muhurat_in_session} muhurat in-session)")
    print(f"  OBSERVED hit rate         : {obs_rate:6.1%}  ({obs_hits}/{n_days})")
    print(f"  BASELINE (random window)  : {base_rate:6.1%}")
    print(f"  LIFT                      : {lift:5.2f}x")
    print(f"  z = {z:+.2f} · one-tailed p = {pval:.3f} -> {sig}")


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookahead", type=int, default=60)
    ap.add_argument("--mode", choices=["extreme", "swing"], default="extreme")
    ap.add_argument("--pivot-k", type=int, default=3)
    a = ap.parse_args()
    run(a.lookahead, a.mode, a.pivot_k)
