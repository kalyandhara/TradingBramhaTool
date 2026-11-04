#!/usr/bin/env python3
"""sweep_confirm_study.py — B-167: does CISD/BOS confirmation after a sweep help?

Pre-registered in trading-wiki/wiki/analyses/Sweep-Confirmation-Filter.md before any
forward return was computed. Sweep events come from cache/sweep_dates.json (saved by
B-166's full-history replay of the registered scanner). No stop in any arm.

    py -3 -X utf8 tools/sweep_confirm_study.py --procs 7
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

WAIT = 5
PIVOT = 5
HORIZONS = (10, 20, 60)
PRIMARY = 20
CACHE = Path(__file__).resolve().parent / "cache"
OUT = CACHE / "sweep_confirm_study.json"


def cisd_bar(o: np.ndarray, c: np.ndarray, s: int, wait: int = WAIT) -> int | None:
    """First bar in s+1..s+wait closing above the OPEN of the first candle of the
    last consecutive down-close run ending at or before s."""
    j = s
    while j >= 0 and not (c[j] < o[j]):
        j -= 1
    if j < 0:
        return None
    k = j
    while k - 1 >= 0 and c[k - 1] < o[k - 1]:
        k -= 1
    level = o[k]
    for i in range(s + 1, min(len(c), s + wait + 1)):
        if c[i] > level:
            return i
    return None


def bos_bar(h: np.ndarray, c: np.ndarray, s: int, wait: int = WAIT, p: int = PIVOT) -> int | None:
    """First bar in s+1..s+wait closing above the latest swing high CONFIRMED as of
    that bar (a pivot high at index q is confirmed at q + p)."""
    for i in range(s + 1, min(len(c), s + wait + 1)):
        hi = None
        for q in range(i - p - 1, p - 1, -1):
            if q + p > i - 1:
                continue
            if h[q] == max(h[q - p:q + p + 1]):
                hi = h[q]
                break
        if hi is not None and c[i] > hi:
            return i
    return None


def one(args) -> dict | None:
    sym, sweeps = args
    import backtest as bt
    df = ov._fetch(sym)
    if df is None:
        return None
    o, h, c = (df[k].to_numpy(float) for k in ("open", "high", "close"))
    n, start = len(df), len(df) - ov.EVAL_BARS
    pos = {d: i for i, d in enumerate(df["date"].dt.strftime("%Y-%m-%d"))}
    cm = bt.COST_INDIAN

    def ret(t, hz):
        if t + 1 + hz >= n or not (o[t + 1] > 0 and c[t + 1 + hz] > 0):
            return None
        return (c[t + 1 + hz] / o[t + 1] - 1) * 100 - cm.round_trip_pct(o[t + 1], c[t + 1 + hz])

    base = {hz: float(np.mean([r for t in range(start, n) if (r := ret(t, hz)) is not None]))
            for hz in HORIZONS}

    def edge(t):
        return {hz: (None if (r := ret(t, hz)) is None else r - base[hz]) for hz in HORIZONS}

    out = []
    for d in sweeps:
        s = pos.get(d)
        if s is None or s < start:
            continue
        cands = [x for x in (cisd_bar(o, c, s), bos_bar(h, c, s)) if x is not None]
        conf = min(cands) if cands else None
        out.append({"date": d, "conf": conf is not None,
                    "edge_arm": edge(conf if conf is not None else s + WAIT),
                    "edge_sweep": edge(s)})
    return {"symbol": sym, "events": out}


def _t(xs):
    a = np.asarray([x for x in xs if x is not None], float)
    if len(a) < 2 or a.std(ddof=1) == 0:
        return float("nan"), float("nan")
    from scipy import stats
    t = a.mean() / (a.std(ddof=1) / math.sqrt(len(a)))
    return float(t), float(2 * stats.t.sf(abs(t), len(a) - 1))


def analyse(rows: list[dict]) -> dict:
    res = {"by_h": {}}
    for hz in HORIZONS:
        diffs, conf_m, all_m = [], [], []
        dated = []
        for r in rows:
            cv = [e["edge_arm"][hz] for e in r["events"] if e["conf"] and e["edge_arm"][hz] is not None]
            uv = [e["edge_arm"][hz] for e in r["events"] if not e["conf"] and e["edge_arm"][hz] is not None]
            av = [e["edge_sweep"][hz] for e in r["events"] if e["edge_sweep"][hz] is not None]
            if cv:
                conf_m.append(float(np.mean(cv)))
            if av:
                all_m.append(float(np.mean(av)))
            if cv and uv:
                diffs.append(float(np.mean(cv) - np.mean(uv)))
            if hz == PRIMARY:
                dated += [(e["date"], e["edge_arm"][hz], e["conf"]) for e in r["events"] if e["edge_arm"][hz] is not None]
        td, pd_ = _t(diffs)
        tc, pc = _t(conf_m)
        ta, pa = _t(all_m)
        res["by_h"][hz] = {
            "paired_symbols": len(diffs), "mean_conf_minus_unconf": round(float(np.mean(diffs)), 3) if diffs else None,
            "t_diff": round(td, 2), "p_diff": round(pd_, 4),
            "conf_symbols": len(conf_m), "conf_edge": round(float(np.mean(conf_m)), 3) if conf_m else None, "p_conf": round(pc, 4),
            "all_at_sweep_edge": round(float(np.mean(all_m)), 3) if all_m else None, "p_all": round(pa, 4)}
        if hz == PRIMARY and dated:
            ds = sorted(dated)
            k = len(ds)
            win = []
            for part in (ds[:k // 3], ds[k // 3:2 * k // 3], ds[2 * k // 3:]):
                cv = [v for _, v, cf in part if cf]
                uv = [v for _, v, cf in part if not cf]
                win.append(round(float(np.mean(cv) - np.mean(uv)), 3) if cv and uv else None)
            res["windows_diff"] = win
    p = res["by_h"][PRIMARY]
    n_events = sum(len(r["events"]) for r in rows)
    res["events"] = n_events
    res["confirmed_pct"] = round(100 * sum(e["conf"] for r in rows for e in r["events"]) / max(1, n_events), 1)
    helps = (p["mean_conf_minus_unconf"] is not None and p["mean_conf_minus_unconf"] > 0 and p["p_diff"] < 0.05
             and p["conf_edge"] is not None and p["conf_edge"] > 0 and p["p_conf"] < 0.05
             and sum(1 for w in res.get("windows_diff", []) if w is not None and w > 0) >= 2
             and p["paired_symbols"] >= 30)
    res["verdict"] = "FILTER HELPS — file B-167r" if helps else "NO FILTER"
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--procs", type=int, default=7)
    a = ap.parse_args()
    sweeps = json.loads((CACHE / "sweep_dates.json").read_text(encoding="utf-8"))
    with Pool(a.procs) as p:
        rows = [r for r in p.imap_unordered(one, list(sweeps.items())) if r]
    res = {"symbols_used": len(rows), **analyse(rows)}
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
