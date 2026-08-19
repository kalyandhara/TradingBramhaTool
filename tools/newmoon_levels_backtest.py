#!/usr/bin/env python3
"""
newmoon_levels_backtest.py — are new-moon-day highs/lows better S/R than an
ordinary adjacent day's highs/lows?

This is the test the wiki page [[New-Moon Levels]] flagged as make-or-break: ANY
recent high/low acts as some support/resistance, so the honest null is NOT a random
price — it is a *prior-day extreme*. Here the control for each new-moon day is the
IMMEDIATELY PRECEDING trading day's high & low. Same regime, same neighbourhood;
the only difference is 'lunar day' vs 'ordinary day'.

Method (matched, look-ahead-free)
---------------------------------
1. New-moon dates via ephem -> mapped to the NIFTY trading day (IST).
2. TREATMENT levels  = that day's High and Low.
   CONTROL   levels  = the prior trading day's High and Low (paired by H/L).
   All levels known at their creation close; touches only counted strictly after.
3. First touch of a level: first later day whose [low,high] enters +/-eps of price P.
   Approach side from the prior close; outcome N days later:
     resistance (approached from below): REJECTED if close_{t+N} < P else BROKEN.
     support   (approached from above): REJECTED if close_{t+N} > P else BROKEN.
   Rejection = the level held (price pushed back to the approach side).
4. Compare rejection rate: new-moon levels vs prior-day levels.
     lift = rej_rate(newmoon) / rej_rate(prior-day)
5. Null: paired permutation — within each (event, H/L) pair, randomly swap the
   treatment/control label 5000x. p = P(perm diff >= observed). This holds the
   market regime fixed and asks only whether the LUNAR label carries extra S/R.

A lift ~1.0 / p>0.1 means new-moon extremes are just ordinary S/R — no lunar edge.
Educational, not advice.

CLI:
  py -3 tools/newmoon_levels_backtest.py
  py -3 tools/newmoon_levels_backtest.py --phase full --symbol ^NSEI
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import ephem

IST = timezone(timedelta(hours=5, minutes=30))


def phase_dates(start: datetime, end: datetime, phase: str) -> List[datetime]:
    """UTC datetimes of each new (or full) moon in [start, end]."""
    nxt = ephem.next_new_moon if phase == "new" else ephem.next_full_moon
    out, d = [], ephem.Date(start)
    while True:
        d = nxt(d)
        dt = d.datetime()
        if dt > end:
            break
        out.append(dt)
    return out


def map_to_trading_day(ist_date, index: pd.DatetimeIndex,
                       max_gap: int = 2) -> Optional[int]:
    """Position of the trading day nearest `ist_date` (within max_gap days)."""
    target = pd.Timestamp(ist_date)
    pos = index.searchsorted(target)
    cands = []
    for p in (pos - 1, pos):
        if 0 <= p < len(index):
            cands.append((abs((index[p] - target).days), p))
    if not cands:
        return None
    gap, p = min(cands)
    return p if gap <= max_gap else None


def first_touch_rejected(levels_price: float, create_pos: int,
                         high: np.ndarray, low: np.ndarray, close: np.ndarray,
                         eps: float, horizon: int, lookfwd: int
                         ) -> Optional[bool]:
    """First touch after create_pos -> True if level REJECTED, False if BROKEN.

    None if never touched (or no room for the horizon).
    """
    P = levels_price
    lo_b, hi_b = P * (1 - eps), P * (1 + eps)
    n = len(close)
    end = min(create_pos + lookfwd, n)
    for t in range(create_pos + 1, end):
        if low[t] <= hi_b and high[t] >= lo_b:        # day entered the band
            if t + horizon >= n:
                return None
            prev = close[t - 1]
            if prev < P:                              # resistance from below
                return close[t + horizon] < P
            if prev > P:                              # support from above
                return close[t + horizon] > P
            return None                               # sitting on the level
    return None


def build_pairs(df: pd.DataFrame, events: List[datetime], eps: float,
                horizon: int, lookfwd: int):
    """For each phase event: (treat H/L touched+rejected, control H/L ...).

    Returns arrays for the paired-permutation test, one row per (event, H/L type).
    """
    idx = df.index
    high, low, close = (df["High"].to_numpy(), df["Low"].to_numpy(),
                        df["Close"].to_numpy())
    rows = []  # (t_touched, t_rej, c_touched, c_rej)
    for ev_utc in events:
        ist_date = (ev_utc.replace(tzinfo=timezone.utc).astimezone(IST)).date()
        pos = map_to_trading_day(ist_date, idx)
        if pos is None or pos == 0:
            continue
        cpos = pos - 1                                 # prior trading day (control)
        for htype in ("H", "L"):
            tP = high[pos] if htype == "H" else low[pos]
            cP = high[cpos] if htype == "H" else low[cpos]
            tr = first_touch_rejected(tP, pos, high, low, close, eps, horizon, lookfwd)
            cr = first_touch_rejected(cP, cpos, high, low, close, eps, horizon, lookfwd)
            rows.append((tr is not None, bool(tr), cr is not None, bool(cr)))
    a = np.array(rows, dtype=bool)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3]          # t_touch,t_rej,c_touch,c_rej


def _rate(touched: np.ndarray, rej: np.ndarray) -> float:
    n = touched.sum()
    return float((rej & touched).sum() / n) if n else 0.0


def permutation_p(tt, tr, ct, cr, n_boot=5000, seed=11) -> Tuple[float, float, float, float]:
    obs = _rate(tt, tr) - _rate(ct, cr)
    rng = np.random.default_rng(seed)
    n = len(tt)
    ge = 0
    for _ in range(n_boot):
        s = rng.random(n) < 0.5
        att = np.where(s, ct, tt); atr = np.where(s, cr, tr)
        bct = np.where(s, tt, ct); bcr = np.where(s, tr, cr)
        diff = _rate(att, atr) - _rate(bct, bcr)
        if diff >= obs:
            ge += 1
    p = ge / n_boot
    return _rate(tt, tr), _rate(ct, cr), obs, p


def run(args) -> None:
    import yfinance as yf
    print(f"Downloading {args.symbol} daily from {args.start} ...")
    df = yf.download(args.symbol, start=args.start, interval="1d",
                     progress=False, auto_adjust=False)
    if df.empty:
        raise SystemExit("No data.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=["High", "Low", "Close"])
    idx = df.index
    start = datetime(idx[0].year, idx[0].month, idx[0].day)
    end = datetime(idx[-1].year, idx[-1].month, idx[-1].day)
    events = phase_dates(start, end, args.phase)
    print(f"{len(df)} trading days {idx[0].date()}..{idx[-1].date()} · "
          f"{len(events)} {args.phase}-moons")
    print(f"Null = prior-trading-day High/Low (matched). "
          f"Permutations = {args.bootstrap}\n")

    print(f"{'eps':>6} {'N':>3} {'pairs':>6} {'nm_touch':>8} {'nm_rej':>7} "
          f"{'pd_rej':>7} {'lift':>6} {'diff':>7} {'p':>6}")
    print("-" * 62)
    any_pass = False
    for eps in args.eps:
        for N in args.horizon:
            tt, tr, ct, cr = build_pairs(df, events, eps / 100.0, N, args.lookfwd)
            nm_rate, pd_rate, diff, p = permutation_p(
                tt, tr, ct, cr, args.bootstrap)
            lift = (nm_rate / pd_rate) if pd_rate else 0.0
            flag = ""
            if lift >= 1.15 and p < 0.01:
                flag = "  <-- clears bar"; any_pass = True
            print(f"{eps:6.2f} {N:3d} {int(tt.sum()):6d} {int(tt.sum()):8d} "
                  f"{nm_rate:7.1%} {pd_rate:7.1%} {lift:6.2f} {diff:+7.1%} "
                  f"{p:6.3f}{flag}")

    print("\nPre-registered pass bar: lift >= 1.15 AND p < 0.01, robust across "
          "eps/horizon.\nA lift ~1.0 with p>0.1 = new-moon extremes are just "
          "ordinary S/R (no lunar edge).")
    print("VERDICT:", "SOME CONFIG CLEARS THE BAR — inspect for robustness."
          if any_pass else "NULL — no lunar S/R edge over prior-day extremes.")
    print("Tests S/R reaction only; direction/PnL not modelled. Educational, not advice.")


def main() -> None:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="^NSEI")
    ap.add_argument("--start", default="2007-09-17")
    ap.add_argument("--phase", default="new", choices=["new", "full"])
    ap.add_argument("--eps", type=float, nargs="+", default=[0.15, 0.25, 0.50],
                    help="touch tolerance band, percent")
    ap.add_argument("--horizon", type=int, nargs="+", default=[3, 5, 10],
                    help="days after touch to judge reject/break")
    ap.add_argument("--lookfwd", type=int, default=120,
                    help="max trading days to wait for first touch")
    ap.add_argument("--bootstrap", type=int, default=5000)
    run(ap.parse_args())


if __name__ == "__main__":
    main()
