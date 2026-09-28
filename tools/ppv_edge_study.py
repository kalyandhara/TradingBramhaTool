"""Pocket Pivot Volume (blue bar) edge study.

PRE-REGISTRATION (committed before any run):
  H0: a pocket pivot bar does not predict above-average forward returns.
  H1: forward returns after a PPV bar exceed the all-bar baseline.

  DESIGN: paired, by symbol. For each symbol, compute the mean forward
  return starting from PPV bars, and the mean forward return starting
  from ALL bars (the baseline). Test whether PPV means exceed baseline.

  HORIZONS: 5d, 10d, 20d (shorter than the desk's usual 10/20/60
  because a volume event is a short-lived catalyst, not a regime).
  CLUSTERING: symbol is the unit. Per-symbol means, one-sample t-test
  on the paired differences (ppv_mean - baseline_mean).
  alpha = 0.05 / 3 = 0.0167 (Bonferroni for three horizons).
  FLOORS: n_symbols >= 20 for CONCLUSIVE, else INCONCLUSIVE.
  COST: 29 bps round-trip (the desk standard).
  SIGNAL_MODE: every PPV bar (no de-duplication — a cluster of blues
  is itself informative, and thinning would impose a lookback choice).
  WARMUP: 252 bars (one year) so the 50-bar volume MA is settled and
  early noise is excluded.

  SECONDARY (descriptive, not hypothesis-tested):
    - Win rate of PPV signals vs baseline.
    - Mean PPV bar volume as a multiple of the 50-bar MA (characterisation).
    - PPV frequency: how many PPV bars per 1000 bars.

Run:
  py -3 tools/ppv_edge_study.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import simple_volume as sv

CACHE = HERE / "cache" / "backtest"
HORIZONS = (5, 10, 20)
COST_BPS = 29
ALPHA = 0.05 / len(HORIZONS)
MIN_SYMBOLS = 20
WARMUP = 252


def _load_symbols() -> list[tuple[str, pd.DataFrame]]:
    out = []
    for f in sorted(CACHE.glob("*_1d.json")):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        sym = data.get("symbol", f.stem.replace("_1d", ""))
        bars = data.get("bars", [])
        if len(bars) < WARMUP + max(HORIZONS) + 1:
            continue
        df = pd.DataFrame(bars)
        for c in ("open", "high", "low", "close", "volume"):
            if c not in df.columns:
                C = c.capitalize()
                if C in df.columns:
                    df[c] = df[C]
        if "volume" not in df.columns or "close" not in df.columns:
            continue
        out.append((sym, df))
    return out


def _fwd_return(close: np.ndarray, t: int, h: int) -> float | None:
    """Return from close[t] to close[t+h], minus round-trip cost."""
    if t + h >= len(close):
        return None
    raw = (close[t + h] / close[t] - 1) * 100
    return raw - COST_BPS / 100


def run():
    t0 = time.time()
    symbols = _load_symbols()
    print(f"Loaded {len(symbols)} symbols from cache\n")

    # Per-symbol collection
    per_sym: dict[str, dict] = {}

    for sym, df in symbols:
        classified = sv.classify(df)
        close = df["close"].values if "close" in df.columns else df["Close"].values
        kinds = classified["kind"].values
        vols = classified["volume"].values
        mas = classified["ma"].values
        n = len(close)

        ppv_indices = []
        for i in range(WARMUP, n - max(HORIZONS)):
            if kinds[i] == "ppv":
                ppv_indices.append(i)

        if not ppv_indices:
            continue

        # PPV forward returns
        ppv_rets = {h: [] for h in HORIZONS}
        ppv_rvols = []
        for i in ppv_indices:
            for h in HORIZONS:
                r = _fwd_return(close, i, h)
                if r is not None:
                    ppv_rets[h].append(r)
            m = mas[i]
            if not np.isnan(m) and m > 0:
                ppv_rvols.append(vols[i] / m)

        # Baseline: ALL bars in the same range
        base_rets = {h: [] for h in HORIZONS}
        for i in range(WARMUP, n - max(HORIZONS)):
            for h in HORIZONS:
                r = _fwd_return(close, i, h)
                if r is not None:
                    base_rets[h].append(r)

        rec = {"n_bars": n - WARMUP, "n_ppv": len(ppv_indices)}
        for h in HORIZONS:
            if ppv_rets[h] and base_rets[h]:
                rec[f"ppv_mean_{h}"] = np.mean(ppv_rets[h])
                rec[f"base_mean_{h}"] = np.mean(base_rets[h])
                rec[f"ppv_win_{h}"] = sum(1 for r in ppv_rets[h] if r > 0) / len(ppv_rets[h])
                rec[f"base_win_{h}"] = sum(1 for r in base_rets[h] if r > 0) / len(base_rets[h])
        rec["mean_rvol"] = np.mean(ppv_rvols) if ppv_rvols else None
        per_sym[sym] = rec
        n_ppv = len(ppv_indices)
        rate = n_ppv / (n - WARMUP) * 1000
        print(f"  {sym} ({n} bars) ... {n_ppv} PPV bars ({rate:.1f} per 1000)")

    # ── Aggregate ────────────────────────────────────────────────────────
    n_syms = len(per_sym)
    elapsed = time.time() - t0

    print(f"\n{'='*60}")
    print(f"Pocket Pivot Volume (PPV) Edge Study")
    print(f"Symbols with PPV bars: {n_syms}")
    total_ppv = sum(r["n_ppv"] for r in per_sym.values())
    total_bars = sum(r["n_bars"] for r in per_sym.values())
    print(f"Total PPV bars: {total_ppv} of {total_bars} ({total_ppv/total_bars*100:.1f}%)")
    print(f"alpha = {ALPHA:.4f} (Bonferroni, {len(HORIZONS)} horizons)")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"{'='*60}\n")

    if n_syms < MIN_SYMBOLS:
        print(f"INCONCLUSIVE — only {n_syms} symbols (floor: {MIN_SYMBOLS})")
        return

    for h in HORIZONS:
        diffs = []
        for sym, rec in per_sym.items():
            pk = f"ppv_mean_{h}"
            bk = f"base_mean_{h}"
            if pk in rec and bk in rec:
                diffs.append(rec[pk] - rec[bk])

        diffs = np.array(diffs)
        n_paired = len(diffs)
        mean_d = np.mean(diffs)
        t_stat, p_two = sp_stats.ttest_1samp(diffs, 0)
        p_one = p_two / 2 if t_stat > 0 else 1 - p_two / 2

        verdict = "PPV BEATS BASELINE" if p_one < ALPHA and mean_d > 0 else "NO DIFFERENCE"

        print(f"@{h}d:  n_symbols_paired={n_paired}")
        print(f"  mean(ppv - baseline) = {mean_d:+.3f}%")
        print(f"  t = {t_stat:.3f}, p_one = {p_one:.4f}")
        print(f"  verdict: {verdict}")
        print()

    # ── Secondary descriptives ───────────────────────────────────────────
    print("-- Secondary (descriptive) --")
    rvols = [r["mean_rvol"] for r in per_sym.values() if r.get("mean_rvol")]
    if rvols:
        print(f"  Mean PPV bar RVOL: {np.mean(rvols):.1f}x the 50-bar MA")
    rates = [r["n_ppv"] / r["n_bars"] * 1000 for r in per_sym.values()]
    print(f"  PPV frequency: {np.mean(rates):.1f} per 1000 bars (median {np.median(rates):.1f})")

    for h in HORIZONS:
        ppv_wins = [r.get(f"ppv_win_{h}", 0) for r in per_sym.values() if f"ppv_win_{h}" in r]
        base_wins = [r.get(f"base_win_{h}", 0) for r in per_sym.values() if f"base_win_{h}" in r]
        if ppv_wins and base_wins:
            print(f"  @{h}d win rate: PPV {np.mean(ppv_wins)*100:.1f}% vs baseline {np.mean(base_wins)*100:.1f}%")


if __name__ == "__main__":
    run()
