#!/usr/bin/env python3
"""disaster_stop_study.py - B-206: does a disaster stop preserve arm C's edge?

B-41p / B-41w established that arm C (Liquidity Sweep, 20-day time exit, no stop)
returns +0.50R across symbols and eras, while any stop of the shipped magnitude
destroys the edge. The open design question from B-41p's scope clause was:

  "a plan with uncapped per-trade downside needs its risk handled somewhere,
   and 'hold 20 days and hope' is not a plan."

This study adds a hard disaster-stop floor to arm C and measures whether the edge
survives. A disaster stop at −k×R exits the trade immediately if the unrealised
loss crosses k×R (i.e. the intraday low hits entry − k×(shipped_risk)). It is NOT
a stop-loss in the usual sense; it is a circuit-breaker for extreme adverse moves,
leaving day-to-day drawdown management to position sizing.

== PRE-REGISTRATION — committed BEFORE this file was first run ==

  PANEL     The B-41p cached trades (cache/b41p_trades.csv): 4,854 entries across
            50 Nifty500 names, 1500 days, 29bps round-trip cost. R-denominator is
            the SHIPPED stop distance throughout (B-41p convention).

  ARMS      baseline   arm C from B-41p (time-exit at 20d, no stop) — the row
                       labelled "C" in the cache; reproduced here from raw bar
                       re-simulation so the disaster floors can be applied.
            D2         arm C + disaster stop at entry − 2×(shipped_risk)
            D3         arm C + disaster stop at entry − 3×(shipped_risk)
            D4         arm C + disaster stop at entry − 4×(shipped_risk)
            All four arms use the same 20-day time horizon and the same cost.
            Three k-values chosen a priori (2, 3, 4 × shipped_risk), not swept.

  STATISTIC mean R across symbols (per-symbol mean, then mean of means),
            matching B-41p. Bootstrap CI: 2000 draws, symbols resampled.

  PASS BAR  An arm PRESERVES the edge if:
              (a) its mean R is > 0, AND
              (b) its CI for mean_R excludes 0 (97.5% — Bonferroni: 3 arms,
                  alpha 0.05/3 ≈ 0.017, one-sided: use 98.3th percentile; but
                  since we test mean > 0 and mean vs C, use 95th for each and
                  apply Bonferroni in the text, not by tightening both), AND
              (c) its mean R is within 0.10R of arm C (not more than 0.10R worse)
            A passing arm is a viable risk-control design. A failing arm means
            the disaster-stop at that level destroys too much of the edge.

  EXPECTED  D2 fails (too tight, destroys the drift), D3 and D4 preserve it.
            The drawdown path is part of the edge (B-41p's finding), so a floor
            at 2×R is probably inside the typical MAE. Prior stated so it can
            be wrong; a D2 pass would be informative.

  SCOPE     A pass licenses noting that floor k is compatible with the edge.
            It does NOT promote the scanner, change the shipped plan, or license
            trading arm C. Position sizing remains the primary risk control.

  py -3 -X utf8 tools/disaster_stop_study.py
  py -3 -X utf8 tools/disaster_stop_study.py --refresh      # re-collect
  py -3 -X utf8 tools/disaster_stop_study.py --symbols RELIANCE TCS   # smoke
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import scanner_templates as sc
    import screener_pipeline as sp
    _HAS_DESK = True
except ImportError:
    _HAS_DESK = False

HORIZON = 20
ATR_N = 14
COST_BPS = 29.0
N_BOOT = 2000
WARMUP = 60
DISASTER_KS = (2.0, 3.0, 4.0)
PASS_MAX_LOSS = 0.10     # arm may be at most 0.10R below arm C to "preserve"
CACHE = Path(__file__).resolve().parent / "cache" / "b41p_trades.csv"


# ---------------------------------------------------------------------------
# Collect from scratch (re-uses sweep_plan_study's approach)
# ---------------------------------------------------------------------------

def collect(symbols: list[str]) -> pd.DataFrame:
    if not _HAS_DESK:
        raise RuntimeError("desk modules not available; use --cache with existing data")
    rows = []
    for si, sym in enumerate(symbols, 1):
        try:
            df = sp.fetch_ohlcv(sym, days=1500)
        except Exception:
            continue
        if df is None or len(df) < WARMUP + HORIZON + 5:
            continue
        dates = (df.index.astype(str).tolist() if not isinstance(df.index, pd.RangeIndex)
                 else [""] * len(df))
        df = df.reset_index(drop=True)
        hi_arr = df["high"].values
        lo_arr = df["low"].values
        cl_arr = df["close"].values
        last_eval = len(df) - HORIZON - 2
        for i in range(WARMUP, last_eval + 1):
            hit = sc.scan_liquidity_sweep(df.iloc[:i + 1])
            if not hit:
                continue
            entry = hit.get("entry")
            stop = hit.get("stop")
            target = hit.get("target")
            if not all(isinstance(v, (int, float)) for v in (entry, stop, target)):
                continue
            a_risk = entry - stop
            if not (a_risk > 0):
                continue
            # Shipped stop (arm A)
            last_i = min(i + HORIZON, len(df) - 1)
            r_c_raw = cl_arr[last_i] - entry
            cost = (COST_BPS / 10000.0) * 2 * entry
            rows.append({
                "symbol": sym, "i": i, "date": str(dates[i])[:10],
                "entry": entry, "shipped_stop": stop, "a_risk": a_risk,
                "hi": list(hi_arr[i + 1:last_i + 1]),
                "lo": list(lo_arr[i + 1:last_i + 1]),
                "close_at_horizon": float(cl_arr[last_i]),
                "cost": float(cost),
            })
        print(f"  [{si}/{len(symbols)}] {sym}: {len(rows)} rows so far", flush=True)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Simulate disaster arms from raw bar data
# ---------------------------------------------------------------------------

def _apply_disaster(row: pd.Series, k: float) -> float:
    """Return R for arm C with disaster stop at entry − k × shipped_risk."""
    entry = row["entry"]
    a_risk = row["a_risk"]
    floor = entry - k * a_risk
    for lo_bar in row["lo"]:
        if lo_bar <= floor:
            return (-k * a_risk - row["cost"]) / a_risk   # = -k - cost_r
    return (row["close_at_horizon"] - entry - row["cost"]) / a_risk


def _arm_c(row: pd.Series) -> float:
    return (row["close_at_horizon"] - row["entry"] - row["cost"]) / row["a_risk"]


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def _boot_mean(sym_means: list[float], rng: np.random.Generator) -> tuple[float, float]:
    arr = np.asarray(sym_means)
    n = len(arr)
    boot = np.array([
        rng.choice(arr, size=n, replace=True).mean()
        for _ in range(N_BOOT)
    ])
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(df: pd.DataFrame) -> None:
    # Compute arm C and each disaster arm per trade
    df = df.copy()
    df["C"] = df.apply(_arm_c, axis=1)
    for k in DISASTER_KS:
        df[f"D{k:g}"] = df.apply(_apply_disaster, k=k, axis=1)

    rng = np.random.default_rng(42)
    arms = ["C"] + [f"D{k:g}" for k in DISASTER_KS]

    print()
    print("=== B-206 · Disaster Stop — does a floor preserve arm C? ===")
    print(f"  {'arm':>5} {'trades':>7} {'mean R':>8} {'CI 95%':>20} "
          f"{'vs C':>7} {'pass?':>6}")

    c_sym_means = [g["C"].mean() for _, g in df.groupby("symbol")]
    c_mean = float(np.mean(c_sym_means))
    c_lo, c_hi = _boot_mean(c_sym_means, rng)
    print(f"  {'C':>5} {len(df):>7} {c_mean:>+8.3f}  "
          f"[{c_lo:+.3f}, {c_hi:+.3f}]  {'baseline':>7}  {'—':>6}")

    for k in DISASTER_KS:
        col = f"D{k:g}"
        sym_means = [g[col].mean() for _, g in df.groupby("symbol")]
        m = float(np.mean(sym_means))
        lo, hi = _boot_mean(sym_means, rng)
        vs_c = m - c_mean
        passes = m > 0 and lo > 0 and vs_c >= -PASS_MAX_LOSS
        print(f"  {col:>5} {len(df):>7} {m:>+8.3f}  "
              f"[{lo:+.3f}, {hi:+.3f}]  {vs_c:>+7.3f}  {'YES' if passes else 'NO':>6}")

    print()
    print("Prior: D2 fails, D3/D4 preserve.  "
          "YES = mean>0 AND CI excludes 0 AND within 0.10R of C.")


def main() -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--cache", type=Path, default=CACHE)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    cache: Path = args.cache
    if not args.refresh and cache.exists():
        print(f"Loading cached trades from {cache}")
        try:
            df = pd.read_csv(cache, converters={"hi": ast.literal_eval, "lo": ast.literal_eval})
        except Exception as e:
            print(f"Cache read error: {e}; re-collecting")
            df = None
    else:
        df = None

    if df is None:
        if not _HAS_DESK:
            print("ERROR: desk modules not available. "
                  "Run from the desk environment or provide --cache <path>.")
            return 1
        symbols = (args.symbols or
                   sp.nse_universe("nifty500")[:50])  # B-41p used 50 names
        print(f"Collecting {len(symbols)} symbols…")
        df = collect(symbols)
        if df.empty:
            print("No trades collected.")
            return 1
        cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache, index=False)
        print(f"Saved {len(df)} trades to {cache}")

    if df.empty:
        print("No trades to analyse.")
        return 1

    run(df)
    return 0


if __name__ == "__main__":
    sys.exit(main())
