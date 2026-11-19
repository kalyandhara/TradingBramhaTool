#!/usr/bin/env python3
"""htf_sweep_study.py — B-166: do higher-timeframe liquidity sweeps beat the daily sweep?

Pre-registered in trading-wiki/wiki/analyses/HTF-Liquidity-Sweep.md before any
forward return was computed. HTF pools (prior-week low, prior-month low, weekly
equal lows) swept on a daily bar by the daily detector's own rules; arm H = HTF
sweeps with no registered `Liquidity Sweep` event within ±2 sessions, arm D =
the scanner. Per-symbol 20-session edge, net costs, one-sample t.

    py -3 -X utf8 tools/htf_sweep_study.py --procs 7
"""
from __future__ import annotations

import argparse
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

import crt_edge_study as ce
import crt_sweep_overlap as ov

MIN_PIERCE, MAX_PIERCE, MIN_WICK = 0.05, 2.0, 0.5
GAP = 5
D_TOL = 2
CACHE = Path(__file__).resolve().parent / "cache"
OUT = CACHE / "htf_sweep_study.json"


def htf_levels(df: pd.DataFrame) -> dict[int, list[float]]:
    """{daily bar index: HTF pool levels known before that bar} — prior completed
    week's low, prior completed month's low, weekly equal-lows pools on completed weeks."""
    import crt_weekly as crt
    import scanner_templates as sc
    dates = pd.DatetimeIndex(df["date"])
    w = crt.weekly_bars(df, drop_last_partial=False)
    m = df.set_index(dates)["low"].groupby(pd.Grouper(freq="ME")).min()
    week_of = dates.to_period("W-FRI")
    month_of = dates.to_period("M")
    wk_periods = w.index.to_period("W-FRI")
    pools_by_week: dict = {}
    out: dict[int, list[float]] = {}
    for i in range(len(df)):
        wp, mp = week_of[i], month_of[i]
        k = int(np.searchsorted(wk_periods, wp))          # weeks strictly before this one
        lv = []
        if k >= 1:
            lv.append(float(w["low"].iloc[k - 1]))
        if k not in pools_by_week:
            wb = w.iloc[:k][["open", "high", "low", "close"]]
            pools_by_week[k] = ([p["level"] for p in sc.detect_liquidity_pools(
                wb, pivot_len=2, eq_tol_pct=0.75, min_touches=2, max_pools=0)
                if p["kind"] == "low"] if len(wb) >= 25 else [])
        lv += pools_by_week[k]
        prev_m = m.index.to_period("M") < mp
        if prev_m.any():
            lv.append(float(m[prev_m].iloc[-1]))
        out[i] = lv
    return out


def htf_sweeps(df: pd.DataFrame, start: int) -> list[int]:
    """Bar indices (>= start) of HTF sweeps, at most one per GAP sessions."""
    import scanner_templates as sc
    atr = sc._atr_series(df, 14).to_numpy()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    levels = htf_levels(df)
    hits, last = [], -10**9
    for i in range(max(start, 1), len(df)):
        a, rng = atr[i], h[i] - l[i]
        if not (a > 0 and rng > 0) or i - last < GAP:
            continue
        if (min(o[i], c[i]) - l[i]) / rng < MIN_WICK:
            continue
        for L in levels[i]:
            if L >= c[i - 1]:                      # pool must be below the prior close
                continue
            pierce = (L - l[i]) / a
            if MIN_PIERCE <= pierce <= MAX_PIERCE and c[i] > L:
                hits.append(i); last = i
                break
    return hits


def one(sym: str) -> dict | None:
    import backtest as bt
    df = ov._fetch(sym)
    if df is None:
        return None
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    n, start = len(df), len(df) - ov.EVAL_BARS
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    pos = {d: i for i, d in enumerate(dates)}
    cm = bt.COST_INDIAN

    def ret(t, h):
        if t + 1 + h >= n or not (o[t + 1] > 0 and c[t + 1 + h] > 0):
            return None
        return (c[t + 1 + h] / o[t + 1] - 1) * 100 - cm.round_trip_pct(o[t + 1], c[t + 1 + h])

    base = {h: float(np.mean([r for t in range(start, n) if (r := ret(t, h)) is not None]))
            for h in ce.HORIZONS}
    d_dates = ov.sweep_dates(df, None)
    d_idx = [pos[s] for s in d_dates if s in pos]
    h_idx = [i for i in htf_sweeps(df, start) if not any(abs(i - j) <= D_TOL for j in d_idx)]

    def evs(idx, kind):
        return [{"date": dates[i], "covered": kind == "D",
                 "edge": {h: (None if (r := ret(i, h)) is None else r - base[h]) for h in ce.HORIZONS}}
                for i in idx]
    return {"symbol": sym, "d_dates": d_dates, "events": evs(d_idx, "D") + evs(h_idx, "H")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--symbols", type=int, default=ov.N_SYMBOLS)
    ap.add_argument("--procs", type=int, default=7)
    a = ap.parse_args()
    import nse_universe as nu
    syms = list(nu.symbols("nifty500"))[:a.symbols]
    with Pool(a.procs) as p:
        rows = [r for r in p.imap_unordered(one, syms) if r]
    CACHE.mkdir(exist_ok=True)
    (CACHE / "sweep_dates.json").write_text(json.dumps({r["symbol"]: r["d_dates"] for r in rows}), encoding="utf-8")
    # crt_edge_study.evaluate: "UNCOVERED" = events with covered False = arm H; split D explicitly.
    h_rows = [{"symbol": r["symbol"], "events": [e for e in r["events"] if not e["covered"]]} for r in rows]
    d_rows = [{"symbol": r["symbol"], "events": [e for e in r["events"] if e["covered"]]} for r in rows]
    H, D = ce.evaluate(h_rows, "ALL"), ce.evaluate(d_rows, "ALL")
    hm, dm = H["by_h"][20]["mean_edge_pct"], D["by_h"][20]["mean_edge_pct"]
    adds = H["verdict"] == "EDGE" and hm is not None and dm is not None and hm >= dm
    res = {"symbols_used": len(rows), "H": H, "D_context": D,
           "verdict": "HTF ADDS — file B-166r" if adds else "NO CHANGE"}
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
