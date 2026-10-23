#!/usr/bin/env python3
"""vwap_ema_agreement_study.py — B-90 measurement.

PRE-REGISTERED (written before any forward return was computed):
  STATE   on a 15m bar close: ABOVE_BOTH (close > session VWAP and > EMA20),
          BELOW_BOTH (close < both), MIXED otherwise. Session VWAP resets daily,
          typical price (H+L+C)/3 weighted by volume. EMA20 on closes, continuous
          across sessions (span 20 bars). First 4 bars of each session excluded
          (VWAP unstable, EMA carries overnight gap).
  EVENT-FREE: a STATE, scored on every bar in it.
  RETURN  entry = next bar open, exit = close of bar t+1+H, H in {4 (1h), 8 (2h)},
          never crossing the session end (such bars dropped). Percent, gross.
  BASELINE every eligible bar, same symbol and session.
  STATISTIC per session: mean(state bars) - mean(all bars), averaged over symbols;
          t-test ACROSS SESSIONS (session = unit; bars within a session are
          autocorrelated). Primary H=4.
  FRAMING EXIT/AVOID: the rule's usable form for a cash book is BELOW_BOTH.
          Hypothesis: BELOW_BOTH excess < 0. PASS needs p<0.05 at H=4 with the
          same sign at H=8. ABOVE_BOTH reported as the mirror.
  FLOOR   >= 60 sessions with both arms present, else INCONCLUSIVE.
  PRIOR   skeptical: 'below both averages' selects downtrends/momentum already in
          the bar; expect ~0 after the baseline.
  Universe: stocks with volume only (^NSEI has no volume -> VWAP undefined, excluded).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import intraday_store as st  # noqa: E402

SYMS = ["HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "RELIANCE.NS", "TCS.NS"]
HORIZONS = (4, 8)
SKIP = 4
MIN_SESSIONS = 60


def t_p(x):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    n = len(x)
    if n < 3 or x.std(ddof=1) == 0:
        return float("nan"), float("nan"), n
    t = x.mean() / (x.std(ddof=1) / math.sqrt(n))
    df = n - 1
    g = np.linspace(0, abs(t), 20001)
    lc = math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi)
    pdf = np.exp(lc - (df + 1) / 2 * np.log1p(g * g / df))
    area = float(np.sum((pdf[1:] + pdf[:-1]) / 2 * np.diff(g)))
    return float(x.mean()), float(min(1, max(0, 1 - 2 * area))), n


def symbol_rows(sym):
    df = st.read_bars(sym, "15m")
    df = df[df["volume"] > 0].copy()
    day = df.index.date
    tp = (df["high"] + df["low"] + df["close"]) / 3
    pv = (tp * df["volume"]).groupby(day).cumsum()
    vv = df["volume"].groupby(day).cumsum()
    df["vwap"] = pv / vv
    df["ema"] = df["close"].ewm(span=20, adjust=False).mean()
    df["day"] = day
    df["pos"] = df.groupby("day").cumcount()
    rows = []
    o = df["open"].to_numpy(); c = df["close"].to_numpy()
    d = df["day"].to_numpy(); pos = df["pos"].to_numpy()
    vw = df["vwap"].to_numpy(); em = df["ema"].to_numpy()
    n = len(df)
    for t in range(n - 1):
        if pos[t] < SKIP:
            continue
        state = ("ABOVE" if c[t] > vw[t] and c[t] > em[t]
                 else "BELOW" if c[t] < vw[t] and c[t] < em[t] else "MIXED")
        rec = {"sym": sym, "day": d[t], "state": state}
        ok = True
        for h in HORIZONS:
            e = t + 1 + h
            if e >= n or d[e] != d[t] or o[t + 1] <= 0:
                rec[h] = np.nan
            else:
                rec[h] = (c[e] / o[t + 1] - 1) * 100
        rows.append(rec)
    return rows


def main():
    rows = []
    for s in SYMS:
        rows += symbol_rows(s)
    df = pd.DataFrame(rows)
    print(f"bars scored: {len(df)}; sessions: {df['day'].nunique()}")
    print(df.groupby("state").size().to_dict())
    for h in HORIZONS:
        print(f"\n== H={h} bars ({h*15} min) ==")
        for arm in ("BELOW", "ABOVE"):
            per = []
            ns = 0
            for dday, g in df.groupby("day"):
                ex = []
                for s, gs in g.groupby("sym"):
                    a = gs.loc[gs.state == arm, h].dropna()
                    b = gs[h].dropna()
                    if len(a) and len(b):
                        ex.append(a.mean() - b.mean())
                if ex:
                    per.append(np.mean(ex))
            m, p, n = t_p(per)
            raw = df.loc[df.state == arm, h].mean()
            base = df[h].mean()
            tag = "" if n >= MIN_SESSIONS else " INCONCLUSIVE"
            print(f"{arm}_BOTH: excess {m:+.4f}pp  p={p:.3f}  sessions={n}  "
                  f"(raw mean {raw:+.4f}% vs baseline {base:+.4f}%, bars {int((df.state==arm).sum())}){tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
