#!/usr/bin/env python3
"""failed_breakdown_study.py — B-203: does the two-candle stop run carry an edge?

Pre-registered in trading-wiki/wiki/analyses/Failed-Breakdown-Sweep.md before
any forward return was computed. Events from
`scanner_templates.failed_breakdown_events` (the registered `Failed Breakdown
(2-bar sweep)` scanner's own detector) on the B-165 panel (nifty500 first 300,
last 750 bars, `crt_sweep_overlap._fetch`).

Arms (decision):
  ALL    every two-candle failed breakdown
  POOL   those whose support was a >= 2-touch pool of equal lows
Context (descriptive, never a verdict): WEAK_VOL and DIVERGENCE subsets, and the
registered one-candle `Liquidity Sweep` on the same panel and span.

Entry next open after the reclaim bar, exit close h sessions later, net of
COST_INDIAN; edge = event return − the symbol's all-bars mean over the span.
Per-symbol mean edges, one-sample t. 20 sessions primary. A long signal wants a
POSITIVE edge.

    py -3 -X utf8 tools/failed_breakdown_study.py --procs 7
"""
from __future__ import annotations

import argparse
import json
import math
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

import crt_edge_study as ce
import crt_sweep_overlap as ov

HORIZONS = (10, 20, 60)
PRIMARY = 20
ALPHA = 0.025                      # per decision arm (two arms)
MIN_SYMBOLS = 30
MIN_EVENTS = {"ALL": 300, "POOL": 100}
OUT = Path(__file__).resolve().parent / "cache" / "failed_breakdown_study.json"


def _ret_fn(df: pd.DataFrame, cost):
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    n = len(df)

    def ret(t: int, h: int) -> float | None:
        if t + 1 + h >= n or not (o[t + 1] > 0 and c[t + 1 + h] > 0):
            return None
        return (c[t + 1 + h] / o[t + 1] - 1) * 100 - cost.round_trip_pct(o[t + 1], c[t + 1 + h])
    return ret


def events_with_edges(df: pd.DataFrame, start: int, cost) -> list[dict]:
    """Detector events whose reclaim bar is in the evaluation span, with edges."""
    import scanner_templates as sc
    ret = _ret_fn(df, cost)
    n = len(df)
    dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").tolist()
    base = {}
    for h in HORIZONS:
        v = [r for t in range(start, n) if (r := ret(t, h)) is not None]
        base[h] = float(np.mean(v)) if v else None
    out = []
    for e in sc.failed_breakdown_events(df):
        t = e["reclaim_bar"]
        if t < start:
            continue
        out.append({"date": dates[t], "kind": "FB", "pool": e["pool"],
                    "weak_vol": e["weak_vol"], "divergence": e["divergence"],
                    "edge": {h: (None if (r := ret(t, h)) is None or base[h] is None
                                 else r - base[h]) for h in HORIZONS}})
    return out, base


def one(sym: str) -> dict | None:
    import backtest as bt
    df = ov._fetch(sym)
    if df is None:
        return None
    start = len(df) - ov.EVAL_BARS
    evs, base = events_with_edges(df, start, bt.COST_INDIAN)
    # Context: the registered one-candle Liquidity Sweep on the same span.
    ret = _ret_fn(df, bt.COST_INDIAN)
    pos = {d: i for i, d in enumerate(pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d"))}
    for d in ov.sweep_dates(df, None):
        t = pos.get(d)
        if t is None or t < start:
            continue
        evs.append({"date": d, "kind": "SWEEP", "pool": None, "weak_vol": None,
                    "divergence": None,
                    "edge": {h: (None if (r := ret(t, h)) is None or base[h] is None
                                 else r - base[h]) for h in HORIZONS}})
    return {"symbol": sym, "events": evs}


def evaluate(rows: list[dict], keep, min_events: int) -> dict:
    evs = [(r["symbol"], e) for r in rows for e in r["events"] if keep(e)]
    out = {"events": len(evs), "symbols": len({s for s, _ in evs}), "by_h": {}}
    for h in HORIZONS:
        per: dict[str, list[float]] = {}
        for s, e in evs:
            if e["edge"][h] is not None:
                per.setdefault(s, []).append(e["edge"][h])
        means = [float(np.mean(v)) for v in per.values()]
        t, p = ce.t_test(means)
        out["by_h"][h] = {
            "symbols": len(means), "events": int(sum(len(v) for v in per.values())),
            "mean_edge_pct": round(float(np.mean(means)), 3) if means else None,
            "symbols_positive_pct": (round(100 * float(np.mean([m > 0 for m in means])), 1)
                                     if means else None),
            "t": None if math.isnan(t) else round(t, 2),
            "p": None if math.isnan(p) else round(p, 4)}
    dated = [(pd.Timestamp(e["date"]), e["edge"][PRIMARY]) for _, e in evs
             if e["edge"][PRIMARY] is not None]
    if dated:
        d0, d1 = min(d for d, _ in dated), max(d for d, _ in dated)
        cuts = [d0 + (d1 - d0) * k / 3 for k in (1, 2)]
        win: list[list[float]] = [[], [], []]
        for d, v in dated:
            win[0 if d < cuts[0] else 1 if d < cuts[1] else 2].append(v)
        out["windows_pct"] = [round(float(np.mean(w)), 3) if w else None for w in win]
    out["verdict"] = verdict(out, min_events)
    return out


def verdict(res: dict, min_events: int) -> str:
    """Pre-registered: TOO FEW / EDGE / NULL (a long signal: positive wanted)."""
    prim = res["by_h"][PRIMARY]
    if prim["symbols"] < MIN_SYMBOLS or prim["events"] < min_events:
        return "TOO FEW"
    pos = sum(1 for w in res.get("windows_pct", []) if w is not None and w > 0)
    if (prim["mean_edge_pct"] is not None and prim["mean_edge_pct"] > 0
            and prim["p"] is not None and prim["p"] < ALPHA and pos >= 2):
        return "EDGE"
    return "NULL"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--symbols", type=int, default=ov.N_SYMBOLS)
    ap.add_argument("--procs", type=int, default=7)
    a = ap.parse_args()
    import nse_universe as nu
    syms = list(nu.symbols("nifty500"))[:a.symbols]
    with Pool(a.procs) as p:
        rows = [r for r in p.imap_unordered(one, syms) if r]
    fb = lambda e: e["kind"] == "FB"                                   # noqa: E731
    res = {"symbols_used": len(rows),
           "ALL": evaluate(rows, fb, MIN_EVENTS["ALL"]),
           "POOL": evaluate(rows, lambda e: fb(e) and e["pool"], MIN_EVENTS["POOL"]),
           "context": {
               "WEAK_VOL": evaluate(rows, lambda e: fb(e) and e["weak_vol"], 0),
               "DIVERGENCE": evaluate(rows, lambda e: fb(e) and e["divergence"], 0),
               "LIQUIDITY_SWEEP_1_CANDLE": evaluate(rows, lambda e: e["kind"] == "SWEEP", 0)}}
    res["decision"] = ("EDGE -- file B-203r (owner: let it vote?)"
                       if "EDGE" in (res["ALL"]["verdict"], res["POOL"]["verdict"])
                       else f"{res['ALL']['verdict']} / {res['POOL']['verdict']} -- stays screen-only")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
