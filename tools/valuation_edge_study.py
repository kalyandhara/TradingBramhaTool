#!/usr/bin/env python3
"""valuation_edge_study.py — B-142 (THIN version): does cheapness at entry predict
forward return on NSE?

PRE-REGISTERED here, before any forward return was computed.

  STATE     At each month-end t: earnings yield EY = TTM EPS / close(t), where TTM
            EPS is the sum of the last four REPORTED quarters whose report dates are
            all <= t (so it was published by t). Names with TTM EPS <= 0 are
            EXCLUDED and counted (a negative yield is not "expensive").
  GROUPS    Quintiles of EY within each date (Q5 = highest yield = "cheapest").
  RETURN    close(t) -> close(t+H), H = 12 months (primary), 6 months (secondary).
            Gross; every group is differenced against the same date so costs cancel.
  STAT      Per date: mean(Q5) - mean(Q1), percent. One spread per DATE.
  TEST      t-test across dates AND the count of INDEPENDENT windows, because
            monthly dates with a 12m horizon overlap 11/12 of the time. The
            independent-window count (non-overlapping 12m blocks) decides power.
  FLOOR     fewer than 8 independent 12-month windows -> INCONCLUSIVE, not a null.
            STATED PRIOR: this will be INCONCLUSIVE (the earnings cache starts ~2021).
  BASE RATE the video's missing piece: of the most EXPENSIVE quintile (Q1), the share
            whose 12m return was negative vs the whole date's share.

KNOWN BIASES (stated, not fixed)
  * Prices are split/bonus-ADJUSTED retroactively; reported EPS is as published then.
    After a split the yield is overstated. Names with a >4x TTM jump are dropped as a
    partial guard; this cannot catch every case.
  * Survivors only (today's NIFTY 500): every result is an UPPER BOUND on a buyer.
  * Consolidated vs standalone EPS is not distinguished.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eps_history_probe as probe  # noqa: E402

DEEP = HERE / "cache" / "cardinality_deep"
EARN = HERE / "cache" / "earnings"
MIN_NAMES = 60          # per date, or the date is skipped
MIN_INDEP = 8


def t_p(x):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    n = len(x)
    if n < 3 or x.std(ddof=1) == 0:
        return float("nan"), float("nan"), n
    t = x.mean() / (x.std(ddof=1) / math.sqrt(n)); df = n - 1
    g = np.linspace(0, abs(t), 20001)
    lc = math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi)
    pdf = np.exp(lc - (df + 1) / 2 * np.log1p(g * g / df))
    return float(x.mean()), float(min(1, max(0, 1 - 2 * np.sum((pdf[1:] + pdf[:-1]) / 2 * np.diff(g))))), n


def load():
    out = {}
    for p in sorted(EARN.glob("*.json")):
        s = p.stem
        q = DEEP / f"{s}_1d.json"
        if not q.exists():
            continue
        ev = json.loads(p.read_text(encoding="utf-8")).get("events", [])
        ser = probe.ttm_series(ev)
        if len(ser) < 4 or probe.artefacts(ser):
            continue
        b = json.loads(q.read_text(encoding="utf-8"))["bars"]
        px = pd.Series([x["close"] for x in b],
                       index=pd.to_datetime([x["time"] for x in b], unit="s").normalize()).sort_index()
        px = px[~px.index.duplicated()]
        out[s] = (ser, px)
    return out


def main() -> int:
    panel = load()
    print(f"names with a TTM series, a price history and no split artefact: {len(panel)}")
    first = min(pd.Timestamp(ser[0][0]) for ser, _ in panel.values())
    last_px = max(px.index[-1] for _, px in panel.values())
    dates = pd.date_range(first + pd.DateOffset(months=3), last_px, freq="ME")
    rows = {6: [], 12: []}
    neg_excluded = 0
    base = []
    for t in dates:
        recs = []
        for s, (ser, px) in panel.items():
            known = [(d, v) for d, v in ser if pd.Timestamp(d) <= t]
            if not known or (t - pd.Timestamp(known[-1][0])).days > 200:   # stale TTM -> skip
                continue
            eps = known[-1][1]
            p0 = px[:t]
            if p0.empty or (t - p0.index[-1]).days > 7:
                continue
            if eps <= 0:
                neg_excluded += 1
                continue
            rec = {"ey": eps / p0.iloc[-1]}
            for H in (6, 12):
                te = t + pd.DateOffset(months=H)
                p1 = px[:te]
                rec[H] = (p1.iloc[-1] / p0.iloc[-1] - 1) * 100 if (len(p1) and p1.index[-1] >= te - pd.Timedelta(days=7)) else np.nan
            recs.append(rec)
        if len(recs) < MIN_NAMES:
            continue
        df = pd.DataFrame(recs)
        df["q"] = pd.qcut(df["ey"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        for H in (6, 12):
            g = df.dropna(subset=[H])
            if len(g) < MIN_NAMES:
                continue
            a = g.loc[g.q == 5, H].mean(); b = g.loc[g.q == 1, H].mean()
            rows[H].append((t, a - b, a, b, len(g)))
            if H == 12:
                base.append(((g.loc[g.q == 1, H] < 0).mean(), (g[H] < 0).mean()))
    print(f"excluded for TTM EPS <= 0 (counted, not scored): {neg_excluded} name-dates\n")
    for H in (12, 6):
        r = rows[H]
        if not r:
            print(f"H={H}m: no dates with >= {MIN_NAMES} names"); continue
        sp = [x[1] for x in r]
        m, p, n = t_p(sp)
        span_m = (r[-1][0] - r[0][0]).days / 30.4
        indep = int(span_m // H) + (1 if r else 0)
        verdict = "INCONCLUSIVE (independent windows < %d)" % MIN_INDEP if indep < MIN_INDEP else ""
        print(f"H={H:>2}m: dates={n} ({r[0][0].date()} .. {r[-1][0].date()}), ~{indep} independent windows")
        print(f"       Q5(cheapest) - Q1(dearest) = {m:+.2f}pp  p={p:.3f} (dates overlap -> p overstated)  "
              f"cheap mean {np.mean([x[2] for x in r]):+.1f}%  dear mean {np.mean([x[3] for x in r]):+.1f}%  {verdict}")
        yrs = {}
        for t, s, *_ in r:
            yrs.setdefault(t.year, []).append(s)
        print("       by calendar year of entry: " + ", ".join(f"{y}:{np.mean(v):+.1f}" for y, v in sorted(yrs.items())))
    if base:
        print(f"\nBASE RATE (12m): share of the DEAREST quintile with a negative return = "
              f"{np.mean([a for a, _ in base])*100:.0f}%, vs {np.mean([b for _, b in base])*100:.0f}% of all names on the same dates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
