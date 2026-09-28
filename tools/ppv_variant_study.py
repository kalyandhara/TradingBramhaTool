"""PPV variant study: does a HIGHER volume threshold or a SETUP GATE add edge?

Follows up the standalone PPV null (ppv_edge_study.py). Three variants:

  A. RVOL >= 3x MA  (volume shocker, ~top third of PPV bars)
  B. RVOL >= 5x MA  (extreme volume, rare events)
  C. PPV + price near 20d high (within 3%) — a proxy for "PPV in a breakout
     context" without importing the full scanner stack.

Same paired design: per-symbol mean forward return vs the all-bar baseline,
one-sample t-test on the differences, Bonferroni alpha.

Run:
  py -3 tools/ppv_variant_study.py
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
HIGH20_PCT = 3.0  # within 3% of 20-day high for variant C


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
    if t + h >= len(close):
        return None
    raw = (close[t + h] / close[t] - 1) * 100
    return raw - COST_BPS / 100


def run():
    t0 = time.time()
    symbols = _load_symbols()
    print(f"Loaded {len(symbols)} symbols from cache\n")

    variants = {
        "A: PPV & RVOL>=3x": {},
        "B: PPV & RVOL>=5x": {},
        "C: PPV & near-20d-high": {},
    }
    signal_counts = {k: 0 for k in variants}

    for sym, df in symbols:
        classified = sv.classify(df)
        close = df["close"].values if "close" in df.columns else df["Close"].values
        high = df["high"].values if "high" in df.columns else df["High"].values
        kinds = classified["kind"].values
        vols = classified["volume"].values
        mas = classified["ma"].values
        n = len(close)

        # Precompute 20-day rolling high
        high20 = np.full(n, np.nan)
        for i in range(19, n):
            high20[i] = np.max(high[i - 19:i + 1])

        # Collect PPV indices per variant
        var_indices = {k: [] for k in variants}
        for i in range(WARMUP, n - max(HORIZONS)):
            if kinds[i] != "ppv":
                continue
            m = mas[i]
            v = vols[i]
            rvol = v / m if (not np.isnan(m) and m > 0) else 0

            if rvol >= 3.0:
                var_indices["A: PPV & RVOL>=3x"].append(i)
            if rvol >= 5.0:
                var_indices["B: PPV & RVOL>=5x"].append(i)
            if not np.isnan(high20[i]) and high20[i] > 0:
                dist_from_high = (high20[i] - close[i]) / high20[i] * 100
                if dist_from_high <= HIGH20_PCT:
                    var_indices["C: PPV & near-20d-high"].append(i)

        # Baseline
        base_rets = {h: [] for h in HORIZONS}
        for i in range(WARMUP, n - max(HORIZONS)):
            for h in HORIZONS:
                r = _fwd_return(close, i, h)
                if r is not None:
                    base_rets[h].append(r)

        for vname, indices in var_indices.items():
            if not indices:
                continue
            signal_counts[vname] += len(indices)
            rec = {"n_signals": len(indices), "n_bars": n - WARMUP}
            for h in HORIZONS:
                sig_rets = [_fwd_return(close, i, h) for i in indices]
                sig_rets = [r for r in sig_rets if r is not None]
                if sig_rets and base_rets[h]:
                    rec[f"sig_mean_{h}"] = np.mean(sig_rets)
                    rec[f"base_mean_{h}"] = np.mean(base_rets[h])
                    rec[f"sig_win_{h}"] = sum(1 for r in sig_rets if r > 0) / len(sig_rets)
            variants[vname][sym] = rec

        counts_str = " / ".join(
            f"{len(var_indices[k])}" for k in variants
        )
        print(f"  {sym} ({n} bars) ... A/B/C = {counts_str}")

    elapsed = time.time() - t0

    for vname, per_sym in variants.items():
        n_syms = len(per_sym)
        total_sig = signal_counts[vname]
        print(f"\n{'='*60}")
        print(f"Variant {vname}")
        print(f"Symbols: {n_syms}, signals: {total_sig}")
        print(f"alpha = {ALPHA:.4f} (Bonferroni)")
        print(f"{'='*60}")

        if n_syms < MIN_SYMBOLS:
            print(f"  INCONCLUSIVE -- only {n_syms} symbols (floor: {MIN_SYMBOLS})")
            continue

        for h in HORIZONS:
            diffs = []
            for sym, rec in per_sym.items():
                sk = f"sig_mean_{h}"
                bk = f"base_mean_{h}"
                if sk in rec and bk in rec:
                    diffs.append(rec[sk] - rec[bk])

            if len(diffs) < 3:
                print(f"  @{h}d: too few paired symbols ({len(diffs)})")
                continue

            diffs = np.array(diffs)
            mean_d = np.mean(diffs)
            t_stat, p_two = sp_stats.ttest_1samp(diffs, 0)
            p_one = p_two / 2 if t_stat > 0 else 1 - p_two / 2
            verdict = "SIGNAL BEATS BASELINE" if p_one < ALPHA and mean_d > 0 else "NO DIFFERENCE"

            print(f"  @{h}d: mean(sig - base) = {mean_d:+.3f}%, t = {t_stat:.3f}, p = {p_one:.4f} -> {verdict}")

        # Win rates
        for h in HORIZONS:
            wins = [rec.get(f"sig_win_{h}") for rec in per_sym.values() if f"sig_win_{h}" in rec]
            if wins:
                print(f"  @{h}d win rate: {np.mean(wins)*100:.1f}%")

    print(f"\nElapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    run()
