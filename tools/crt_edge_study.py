#!/usr/bin/env python3
"""crt_edge_study.py — B-165r: does a weekly bullish CRT carry forward edge?

Pre-registered in trading-wiki/wiki/analyses/Weekly-CRT-Sweep-Overlap.md (section
B-165r) before any forward return was computed. Reuses B-165's fetch, CRT and
sweep functions from `crt_sweep_overlap` unchanged, on the same panel and span.

Entry next open after candle 2's last day, exit close h sessions later, net of
COST_INDIAN; edge = event return − the symbol's all-bars mean over the same
span. Per-symbol mean edges, one-sample t across symbols. 20 sessions primary,
alpha 0.025 per population (ALL / UNCOVERED); 3-window sign stability.

    py -3 -X utf8 tools/crt_edge_study.py --procs 7
"""
from __future__ import annotations

import argparse
import json
import math
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

import crt_sweep_overlap as ov

HORIZONS = (10, 20, 60)
PRIMARY = 20
ALPHA = 0.025
COVER_TOL = 5
MIN_SYMBOLS, MIN_EVENTS = 30, 300
OUT = Path(__file__).resolve().parent / "cache" / "crt_edge_study.json"


def one(sym: str) -> dict | None:
    import backtest as bt
    df = ov._fetch(sym)
    if df is None:
        return None
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = len(df)
    start = n - ov.EVAL_BARS
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    pos = {d: i for i, d in enumerate(dates)}
    cm = bt.COST_INDIAN

    def ret(t: int, h: int) -> float | None:
        if t + 1 + h >= n or not (o[t + 1] > 0 and c[t + 1 + h] > 0):
            return None
        e, x = o[t + 1], c[t + 1 + h]
        return (x / e - 1.0) * 100.0 - cm.round_trip_pct(e, x)

    base = {}
    for h in HORIZONS:
        v = [r for t in range(start, n) if (r := ret(t, h)) is not None]
        base[h] = float(np.mean(v)) if v else None
    sweeps = [pos[s] for s in ov.sweep_dates(df, None) if s in pos]
    events = []
    for e in ov.crt_events(df):
        if e["start"] not in pos or e["end"] not in pos:
            continue
        a, b = pos[e["start"]], pos[e["end"]]
        covered = any(a - COVER_TOL <= p <= b + COVER_TOL for p in sweeps)
        edges = {}
        for h in HORIZONS:
            r = ret(b, h)
            edges[h] = None if r is None or base[h] is None else r - base[h]
        events.append({"date": e["end"], "covered": covered, "edge": edges})
    return {"symbol": sym, "events": events}


def t_test(xs: list[float]) -> tuple[float, float]:
    a = np.asarray(xs, float)
    if len(a) < 2 or a.std(ddof=1) == 0:
        return float("nan"), float("nan")
    t = float(a.mean() / (a.std(ddof=1) / math.sqrt(len(a))))
    from scipy import stats
    return t, float(2 * stats.t.sf(abs(t), df=len(a) - 1))


def evaluate(rows: list[dict], population: str) -> dict:
    keep = (lambda e: True) if population == "ALL" else (lambda e: not e["covered"])
    evs = [(r["symbol"], e) for r in rows for e in r["events"] if keep(e)]
    out = {"events": len(evs), "symbols": len({s for s, _ in evs}), "by_h": {}}
    for h in HORIZONS:
        per = {}
        for s, e in evs:
            if e["edge"][h] is not None:
                per.setdefault(s, []).append(e["edge"][h])
        means = [float(np.mean(v)) for v in per.values()]
        t, p = t_test(means)
        out["by_h"][h] = {"symbols": len(means),
                          "events": int(sum(len(v) for v in per.values())),
                          "mean_edge_pct": round(float(np.mean(means)), 3) if means else None,
                          "symbols_positive_pct": round(100 * float(np.mean([m > 0 for m in means])), 1) if means else None,
                          "t": round(t, 2) if not math.isnan(t) else None,
                          "p": round(p, 4) if not math.isnan(p) else None}
    dated = [(pd.Timestamp(e["date"]), e["edge"][PRIMARY]) for _, e in evs if e["edge"][PRIMARY] is not None]
    if dated:
        d0, d1 = min(d for d, _ in dated), max(d for d, _ in dated)
        cuts = [d0 + (d1 - d0) * k / 3 for k in (1, 2)]
        win = [[], [], []]
        for d, v in dated:
            win[0 if d < cuts[0] else 1 if d < cuts[1] else 2].append(v)
        out["windows_pct"] = [round(float(np.mean(w)), 3) if w else None for w in win]
    prim = out["by_h"][PRIMARY]
    ok = (prim["mean_edge_pct"] is not None and prim["mean_edge_pct"] > 0
          and prim["p"] is not None and prim["p"] < ALPHA
          and sum(1 for w in out.get("windows_pct", []) if w is not None and w > 0) >= 2
          and prim["symbols"] >= MIN_SYMBOLS and prim["events"] >= MIN_EVENTS)
    out["verdict"] = "EDGE" if ok else "NULL"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--symbols", type=int, default=ov.N_SYMBOLS)
    ap.add_argument("--procs", type=int, default=7)
    a = ap.parse_args()
    import nse_universe as nu
    syms = list(nu.symbols("nifty500"))[:a.symbols]
    with Pool(a.procs) as p:
        rows = [r for r in p.imap_unordered(one, syms) if r]
    res = {"symbols_used": len(rows),
           "ALL": evaluate(rows, "ALL"), "UNCOVERED": evaluate(rows, "UNCOVERED")}
    res["decision"] = ("FILE B-165s (register weekly CRT at unmeasured weight + plan study)"
                       if "EDGE" in (res["ALL"]["verdict"], res["UNCOVERED"]["verdict"])
                       else "CLOSE B-165r — CRT stays a detector")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
