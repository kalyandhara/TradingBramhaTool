"""B-186a — why B-41m's bullish sweep is +0.51% and the chart tour's is ordinary.

Pre-registered at trading-wiki/wiki/analyses/Sweep-Reconciliation-Pre-Registration.md
(commit d05b294, before this file existed). A diagnosis, not an edge test: walk
from B-41m's harness run to the tour's method one change at a time and see
where mean20 falls.

    S1  harness as shipped (LIQUID_50, all-mode, next-open entry, pooled, net)
    S2  same signal bars, the tour's statistic (log close-to-close excess over
        the symbol's own span mean, per-symbol mean, t across symbols, gross)
    S3  the tour's event rule (first bar each sweep is visible), full history
    S4  the tour's period (last 750 bars)
    S5  the tour's universe (nifty500[:300])
    S6  the tour's 260-bar detection window = the tour's method in full

Run:  python -X utf8 tools/sweep_reconcile_study.py [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import backtest as bt  # noqa: E402
import chart_tour as ct  # noqa: E402
import scanner_templates as sc  # noqa: E402
import tour_base_rates as tbr  # noqa: E402

KEY = "liquidity_sweep_bull"
SCANNER = "Liquidity Sweep"
HORIZONS = tbr.HORIZONS            # (5, 20, 60)
HARNESS_WARMUP = bt.WARMUP_BARS    # 210
HARNESS_MIN_GAP = bt.DEFAULT_MIN_GAP
HARNESS_MAX_H = max(bt.DEFAULT_HORIZONS)
FULL_WINDOW = 10 ** 6
EVAL_BARS = tbr.EVAL_BARS          # 750
MIN_BARS = EVAL_BARS + 60          # the tour's own floor
OUT = HERE / "cache" / "sweep_reconcile.json"
FRAMES = HERE / "cache" / "sweep_reconcile_frames.pkl"


# --------------------------------------------------------------------------- #
# Pieces (tested)
# --------------------------------------------------------------------------- #

def clean(df: pd.DataFrame) -> pd.DataFrame:
    """The harness's own cleaning (dropna on h/l/c/v), keeping the dates."""
    d = df.rename(columns=str.lower)
    if "date" in d.columns:
        d = d.set_index(pd.to_datetime(d.pop("date")))
    d = d[["open", "high", "low", "close", "volume"]].astype(float)
    return d.dropna(subset=["high", "low", "close", "volume"])


def harness_events(df: pd.DataFrame, fn, warmup: int = HARNESS_WARMUP,
                   min_gap: int = HARNESS_MIN_GAP, max_h: int = HARNESS_MAX_H) -> list[int]:
    """The signal bars `backtest_scanner` records in its default "all" mode:
    scan df.iloc[:t+1] from `warmup` to n - max_h - 2, skip `min_gap` after a hit."""
    d = clean(df).reset_index(drop=True)
    last_eval = len(d) - max_h - 2
    out, t = [], warmup
    while t <= last_eval:
        try:
            hit = fn(d.iloc[:t + 1])
        except Exception:                              # noqa: BLE001 - as the harness does
            hit = None
        if hit:
            out.append(t)
            t += min_gap
        else:
            t += 1
    return out


def outcome_rows(sym: str, df: pd.DataFrame, bars: list[int], start: int, end: int) -> list[dict]:
    """The tour's outcome: log forward return at each bar minus the symbol's mean
    forward return over bars [start, end) (NaN where the horizon runs off)."""
    c = df["close"].to_numpy(float)
    n = len(c)
    fwd, base = {}, {}
    for h in HORIZONS:
        r = np.full(n, np.nan)
        r[:n - h] = np.log(c[h:] / c[:n - h])
        fwd[h] = r
        span = r[start:end]
        span = span[np.isfinite(span)]
        base[h] = float(span.mean()) if len(span) else np.nan
    rows = []
    for b in bars:
        row = {"sym": sym, "key": KEY, "date": df.index[b], "bar": b}
        for h in HORIZONS:
            row[f"x{h}"] = fwd[h][b] - base[h] if np.isfinite(fwd[h][b]) else np.nan
        rows.append(row)
    return rows


def tour_rows(sym: str, df: pd.DataFrame, start: int, window: int) -> list[dict]:
    """The tour's event rule for the sweep card, with a chosen start and window."""
    evs = tbr.detector_events(df, {KEY: ct.DETECTORS[KEY]}, start, window)
    bars = [e["bar"] for e in evs if e["key"] == KEY and e["tone"] != "down"]
    return outcome_rows(sym, df, bars, start, len(df))


def with_deltas(steps: list[tuple[str, dict]]) -> list[dict]:
    out, prev = [], None
    for name, r in steps:
        row = {"step": name, **r}
        m = r.get("mean20")
        row["d_mean20"] = None if prev is None or m is None else m - prev
        prev = m if m is not None else prev
        out.append(row)
    return out


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def fetch_frames(syms: list[str]) -> dict[str, pd.DataFrame]:
    import logging
    import screener_pipeline as sp
    logging.disable(logging.WARNING)
    # Local, git-ignored cache that only this function writes (one fetch per
    # symbol, reused across steps); never read from anywhere else.
    cached = pickle.loads(FRAMES.read_bytes()) if FRAMES.exists() else {}
    for k, s in enumerate(syms, 1):
        if s not in cached:
            try:
                cached[s] = sp.fetch_ohlcv(s, days=1500)
            except Exception:                          # noqa: BLE001 - a missing name is skipped
                cached[s] = None
        if k % 50 == 0:
            print(f"  fetched {k}/{len(syms)}", flush=True)
    FRAMES.write_bytes(pickle.dumps(cached))
    return cached


def _harness_summary(res: dict) -> dict:
    m = (res.get("horizons") or {}).get(20) or (res.get("horizons") or {}).get("20") or {}
    tt = m.get("edge_ttest") or {}
    return {"n_events": res.get("n_signals"), "n_symbols": res.get("n_symbols"),
            "edge20_pct": m.get("edge"), "p20": tt.get("p")}


def _worker(args):
    sym, raw, in_a, in_b = args
    out = {"S2": [], "S3": [], "S4": [], "S5": [], "S6": []}
    if raw is None:
        return out
    df = clean(raw)
    n = len(df)
    if in_a:
        bars = harness_events(raw, sc.SCANNERS[SCANNER]["fn"])
        out["S2"] = outcome_rows(sym, df, bars, HARNESS_WARMUP, n - HARNESS_MAX_H - 1)
        out["S3"] = tour_rows(sym, df, HARNESS_WARMUP, FULL_WINDOW)
        if n >= MIN_BARS:
            out["S4"] = tour_rows(sym, df, n - EVAL_BARS, FULL_WINDOW)
    if in_b and n >= MIN_BARS:
        out["S5"] = tour_rows(sym, df, n - EVAL_BARS, FULL_WINDOW)
        out["S6"] = tour_rows(sym, df, n - EVAL_BARS, ct.DETECTOR_WINDOW)
    return out


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    a = ap.parse_args(argv)
    import nse_universe as nu
    uni_a = list(bt.LIQUID_50)
    uni_b = tbr.panel_symbols(nu.symbols("nifty500"), 0, 300)
    frames = fetch_frames(sorted(set(uni_a) | set(uni_b)))
    fetch = lambda s: frames.get(s)                      # noqa: E731 - the harness wants a callable

    print("S1 harness, net ...", flush=True)
    s1 = _harness_summary(bt.backtest_scanner(SCANNER, uni_a, fetch, cost_model=bt.COST_INDIAN))
    s1g = _harness_summary(bt.backtest_scanner(SCANNER, uni_a, fetch))

    rows = {k: [] for k in ("S2", "S3", "S4", "S5", "S6")}
    tasks = [(s, frames.get(s), s in uni_a, s in uni_b) for s in sorted(set(uni_a) | set(uni_b))]
    from multiprocessing import Pool
    with Pool(a.workers) as pool:
        for k, part in enumerate(pool.imap_unordered(_worker, tasks, chunksize=2), 1):
            for s in rows:
                rows[s] += part[s]
            if k % 50 == 0:
                print(f"  {k}/{len(tasks)} symbols", flush=True)

    def agg(r):
        x = tbr.aggregate(r, [KEY])[KEY]
        return {kk: x[kk] for kk in ("n_events", "n_symbols", "mean5", "mean20", "mean60", "p20", "thirds")}

    s1_frac = {**s1, "mean20": None if s1["edge20_pct"] is None else s1["edge20_pct"] / 100}
    steps = with_deltas([("S1", s1_frac)] + [(s, agg(rows[s])) for s in ("S2", "S3", "S4", "S5", "S6")])
    published = json.loads((HERE / "cache" / "tour_base_rates.json").read_text(encoding="utf-8"))
    payload = {
        "asOf": date.today().isoformat(),
        "preregistration": "trading-wiki/wiki/analyses/Sweep-Reconciliation-Pre-Registration.md (d05b294)",
        "s1_gross": s1g,
        "s2_parity": {"harness_n_signals": s1["n_events"], "replay_events": len(rows["S2"])},
        "s6_published_mean20": published["detectors"][KEY]["mean20"],
        "steps": steps,
    }
    OUT.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    for r in steps:
        m, d = r.get("mean20"), r.get("d_mean20")
        print(f"{r['step']}  n={r.get('n_events')!s:>6} syms={r.get('n_symbols')!s:>4} "
              f"mean20={'' if m is None else f'{m * 100:+.2f}%':>8} "
              f"d={'' if d is None else f'{d * 100:+.2f}pp':>9} p={r.get('p20')}")
    print("S1 gross:", s1g, "| parity:", payload["s2_parity"],
          "| published S6:", payload["s6_published_mean20"])
    print(OUT)
    return payload


if __name__ == "__main__":
    main()
