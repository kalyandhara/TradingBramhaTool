#!/usr/bin/env python3
"""bull_trap_study.py — B-182: does a bull trap warn of a weak next month?

Pre-registered in trading-wiki/wiki/analyses/Bull-Trap-Detector.md before any
forward return was computed. Events from `scanner_templates.bull_trap_events`
(the registered `Bull Trap` scanner's own detector) on the B-165 panel
(nifty500 first 300, last 750 bars, `crt_sweep_overlap._fetch`).

Arms:
  TRAP     full bull traps (failed breakout + weak volume + RSI divergence)
  FB_ONLY  failed breakouts that are NOT full traps (context)
Entry next open after the trap bar, exit close h sessions later, net of
COST_INDIAN; edge = event return − the symbol's all-bars mean over the same
span. Per-symbol mean edges, one-sample t. 20 sessions primary. A RISK flag
wants a NEGATIVE edge.

    py -3 -X utf8 tools/bull_trap_study.py --procs 7
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
ALPHA = 0.025
MIN_SYMBOLS, MIN_EVENTS = 30, 100
OUT = Path(__file__).resolve().parent / "cache" / "bull_trap_study.json"


def events_with_edges(df: pd.DataFrame, start: int, cost) -> list[dict]:
    """Detector events whose trap bar is in the evaluation span, with edges."""
    import scanner_templates as sc
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    n = len(df)
    dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").tolist()

    def ret(t: int, h: int) -> float | None:
        if t + 1 + h >= n or not (o[t + 1] > 0 and c[t + 1 + h] > 0):
            return None
        return (c[t + 1 + h] / o[t + 1] - 1) * 100 - cost.round_trip_pct(o[t + 1], c[t + 1 + h])

    base = {}
    for h in HORIZONS:
        v = [r for t in range(start, n) if (r := ret(t, h)) is not None]
        base[h] = float(np.mean(v)) if v else None
    out = []
    for e in sc.bull_trap_events(df):
        t = e["trap_bar"]
        if t < start:
            continue
        out.append({"date": dates[t], "full": e["full"], "weak_vol": e["weak_vol"],
                    "divergence": e["divergence"],
                    "edge": {h: (None if (r := ret(t, h)) is None or base[h] is None
                                 else r - base[h]) for h in HORIZONS}})
    return out


def one(sym: str) -> dict | None:
    import backtest as bt
    df = ov._fetch(sym)
    if df is None:
        return None
    return {"symbol": sym,
            "events": events_with_edges(df, len(df) - ov.EVAL_BARS, bt.COST_INDIAN)}


def evaluate(rows: list[dict], keep) -> dict:
    """Per-symbol mean edges per horizon, t-test, 3-window signs, verdict."""
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
            "symbols_negative_pct": (round(100 * float(np.mean([m < 0 for m in means])), 1)
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
    out["verdict"] = verdict(out)
    return out


def verdict(res: dict) -> str:
    """Pre-registered: TOO FEW / WARNS / NOT ESTABLISHED (risk flag: negative wanted)."""
    prim = res["by_h"][PRIMARY]
    if prim["symbols"] < MIN_SYMBOLS or prim["events"] < MIN_EVENTS:
        return "TOO FEW"
    neg_windows = sum(1 for w in res.get("windows_pct", []) if w is not None and w < 0)
    if (prim["mean_edge_pct"] is not None and prim["mean_edge_pct"] < 0
            and prim["p"] is not None and prim["p"] < ALPHA and neg_windows >= 2):
        return "WARNS"
    return "NOT ESTABLISHED"


def paired(rows: list[dict]) -> dict:
    """Descriptive: per symbol with both arms, mean(TRAP) − mean(FB_ONLY) at 20."""
    diffs = []
    for r in rows:
        a = [e["edge"][PRIMARY] for e in r["events"] if e["full"] and e["edge"][PRIMARY] is not None]
        b = [e["edge"][PRIMARY] for e in r["events"]
             if not e["full"] and e["edge"][PRIMARY] is not None]
        if a and b:
            diffs.append(float(np.mean(a)) - float(np.mean(b)))
    t, p = ce.t_test(diffs)
    return {"symbols": len(diffs),
            "mean_diff_pct": round(float(np.mean(diffs)), 3) if diffs else None,
            "t": None if math.isnan(t) else round(t, 2),
            "p": None if math.isnan(p) else round(p, 4)}


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
           "TRAP": evaluate(rows, lambda e: e["full"]),
           "FB_ONLY": evaluate(rows, lambda e: not e["full"]),
           "TRAP_minus_FB_ONLY_20d": paired(rows)}
    res["decision"] = res["TRAP"]["verdict"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
