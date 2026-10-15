#!/usr/bin/env python3
"""crt_sweep_overlap.py — B-165: is weekly CRT a subset of the Liquidity Sweep scanner?

AN OVERLAP CHECK, NOT AN EDGE TEST. Pre-registered in
trading-wiki/wiki/analyses/Weekly-CRT-Sweep-Overlap.md before the first run.
No forward return is computed. The decision rule (≥ 80% of CRT events covered at
d = 5 → SUBSET, close B-165; otherwise file B-165r) lives in that page, and the
verdict printed here applies it unchanged.

    py -3 -X utf8 tools/crt_sweep_overlap.py --parity      # 10-name window check first
    py -3 -X utf8 tools/crt_sweep_overlap.py               # the registered run

The scanner is `scanner_templates.scan_liquidity_sweep` AS SHIPPED, replayed on
every daily bar of the evaluation span. Each call sees a trailing 500-bar window
(a speed concession declared in the pre-registration and checked by --parity).
"""
from __future__ import annotations

import argparse
import json
import logging
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

N_SYMBOLS = 300
DAYS = 1500
EVAL_BARS = 750
WINDOW = 500
TOLS = (0, 2, 5, 10)
DECIDE_TOL = 5
SUBSET_AT = 0.80
MIN_EVENTS = 150
PARITY_N = 10
PARITY_MAX_DIFF = 0.02
OUT = Path(__file__).resolve().parent / "cache" / "crt_sweep_overlap.json"


def _fetch(sym: str):
    logging.disable(logging.WARNING)
    import screener_pipeline as sp
    try:
        df = sp.fetch_ohlcv(sym, days=DAYS)
    except Exception:
        return None
    if df is None or len(df) < EVAL_BARS + 60:
        return None
    df = df.reset_index(drop="date" in df.columns)
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    return df.reset_index(drop=True)


def sweep_dates(df: pd.DataFrame, window: int | None) -> list[str]:
    """Swept-bar dates of every bullish Liquidity Sweep firing in the eval span."""
    import scanner_templates as sc
    n = len(df)
    seen: set[str] = set()
    for t in range(n - EVAL_BARS, n):
        lo = 0 if window is None else max(0, t - window + 1)
        win = df.iloc[lo:t + 1]
        if not sc.scan_liquidity_sweep(win):
            continue
        ev = sc.detect_liquidity_sweep(win, pivot_len=5)
        if ev:
            seen.add(df["date"].iloc[t - ev["bars_ago"]].strftime("%Y-%m-%d"))
    return sorted(seen)


def crt_events(df: pd.DataFrame) -> list[dict]:
    import crt_weekly as crt
    import scanner_templates as sc
    atr = sc._atr_series(df, 14)
    atr.index = pd.DatetimeIndex(df["date"])
    first = df["date"].iloc[len(df) - EVAL_BARS]
    return [{"start": e["start"].strftime("%Y-%m-%d"), "end": e["end"].strftime("%Y-%m-%d"),
             "pierce_atr": e["pierce_atr"]}
            for e in crt.bullish_events(df, atr) if e["start"] >= first]


def one(args) -> dict | None:
    sym, window = args
    df = _fetch(sym)
    if df is None:
        return None
    return {"symbol": sym, "dates": df["date"].dt.strftime("%Y-%m-%d").tolist(),
            "sweeps": sweep_dates(df, window), "crt": crt_events(df)}


def coverage(rows: list[dict]) -> dict:
    """Direction-matched, windowed containment both ways, per tolerance."""
    out = {"crt_events": 0, "sweep_events": 0, "by_tol": {}}
    for d in TOLS:
        crt_cov = sw_cov = 0
        n_crt = n_sw = 0
        for r in rows:
            pos = {dt: i for i, dt in enumerate(r["dates"])}
            sw = [pos[s] for s in r["sweeps"] if s in pos]
            spans = [(pos[e["start"]] - d, pos[e["end"]] + d) for e in r["crt"]
                     if e["start"] in pos and e["end"] in pos]
            n_crt += len(spans)
            n_sw += len(sw)
            crt_cov += sum(any(a <= p <= b for p in sw) for a, b in spans)
            sw_cov += sum(any(a <= p <= b for a, b in spans) for p in sw)
        out["crt_events"], out["sweep_events"] = n_crt, n_sw
        out["by_tol"][d] = {
            "crt_covered": crt_cov, "crt_covered_pct": round(100 * crt_cov / n_crt, 1) if n_crt else None,
            "sweeps_in_crt": sw_cov, "sweeps_in_crt_pct": round(100 * sw_cov / n_sw, 1) if n_sw else None}
    return out


def verdict(cov: dict) -> str:
    if cov["crt_events"] < MIN_EVENTS:
        return "TOO RARE — close B-165"
    pct = cov["by_tol"][DECIDE_TOL]["crt_covered_pct"]
    return ("SUBSET — close B-165, no edge test owed" if pct >= 100 * SUBSET_AT
            else "NOT A SUBSET — file B-165r (pre-registered edge test)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--parity", action="store_true")
    ap.add_argument("--symbols", type=int, default=N_SYMBOLS)
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    import nse_universe as nu
    syms = list(nu.symbols("nifty500"))[:a.symbols]

    if a.parity:
        names = syms[:PARITY_N]
        with Pool(a.procs) as p:
            win = [r for r in p.map(one, [(s, WINDOW) for s in names]) if r]
            full = [r for r in p.map(one, [(s, None) for s in names]) if r]
        a_set = {(r["symbol"], d) for r in win for d in r["sweeps"]}
        b_set = {(r["symbol"], d) for r in full for d in r["sweeps"]}
        diff = len(a_set ^ b_set) / max(1, len(b_set))
        print(f"parity: window {len(a_set)} events, full {len(b_set)}, "
              f"symmetric difference {len(a_set ^ b_set)} = {diff:.1%} "
              f"-> {'OK, use the window' if diff <= PARITY_MAX_DIFF else 'FAIL, use full history'}")
        return 0

    with Pool(a.procs) as p:
        rows = [r for r in p.imap_unordered(one, [(s, WINDOW) for s in syms]) if r]
    cov = coverage(rows)
    piers = sorted(e["pierce_atr"] for r in rows for e in r["crt"] if e["pierce_atr"] is not None)
    res = {"symbols_requested": len(syms), "symbols_used": len(rows), **cov,
           "crt_pierce_atr_median": piers[len(piers) // 2] if piers else None,
           "verdict": verdict(cov)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"symbols {res['symbols_used']}/{len(syms)} · CRT events {cov['crt_events']} · "
          f"sweep events {cov['sweep_events']} · median CRT pierce {res['crt_pierce_atr_median']} ATR")
    for d in TOLS:
        b = cov["by_tol"][d]
        print(f"  d={d:>2}: CRT covered by a sweep {b['crt_covered_pct']}% · "
              f"sweeps inside a CRT week {b['sweeps_in_crt_pct']}%")
    print(f"VERDICT (d={DECIDE_TOL}, bar {SUBSET_AT:.0%}): {res['verdict']}")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
