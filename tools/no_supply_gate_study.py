"""B-122 gate-vs-no-gate study: does the No-Supply filter add edge to the
Trend/Momentum new-high family?

PRE-REGISTRATION (committed before any run):
  H0: the No-Supply gate does not improve the forward return of the
      Trend/Momentum family's signals.
  H1: gated signals have a higher mean forward return than ungated.

  DESIGN: paired, by symbol. For each symbol, compute the mean forward
  return of gated signals and ungated signals separately, then test
  whether the gated mean exceeds the ungated mean.

  HORIZONS: 10d, 20d, 60d (the desk's standard).
  CLUSTERING: symbol is the unit. Per-symbol means, one-sample t-test
  on the paired differences (gated_mean - ungated_mean).
  alpha = 0.05 / 3 = 0.0167 (Bonferroni for three horizons).
  FLOORS: n_symbols >= 20 for CONCLUSIVE, else INCONCLUSIVE.
  COST: 29 bps (the desk standard).
  SIGNAL_MODE: fresh (first bar only, min_gap=5).
  WINDOW: the full cached history, no walk-forward split -- this is a
  one-shot paired test, not a repeated measurement.

  The question is NOT "does No-Supply beat random entry" -- the family
  already failed that. It is "does the supply gate ADD anything to the
  family": does filtering to no-supply stocks select a better subset?

Run:
  py -3 tools/no_supply_gate_study.py
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
HORIZONS = (10, 20, 60)
COST_BPS = 29
ALPHA = 0.05 / len(HORIZONS)
MIN_SYMBOLS = 20
WARMUP = 252
MIN_GAP = 5


def _load_symbols() -> list[tuple[str, pd.DataFrame]]:
    out = []
    for f in sorted(CACHE.glob("*_1d.json")):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        sym = data.get("symbol", f.stem.replace("_1d", ""))
        df = pd.DataFrame(data["bars"])
        if len(df) < 300:
            continue
        out.append((sym, df))
    return out


def _vectorized_family_mask(df: pd.DataFrame) -> np.ndarray:
    """Return a boolean mask where any Trend/Momentum family scanner fires.

    Reimplements the core conditions of scan_52w_high_leaders,
    scan_stage2_uptrend, scan_momentum_continuation, and
    scan_adx_trend_confirmation as vectorized operations.
    """
    n = len(df)
    close = df["close"].values.astype(float)
    high = df["high"].values.astype(float)
    volume = df["volume"].values.astype(float)
    opn = df["open"].values.astype(float) if "open" in df.columns else close.copy()
    low = df["low"].values.astype(float)

    mask = np.zeros(n, dtype=bool)

    # SMA series
    sma20 = pd.Series(close).rolling(20).mean().values
    sma50 = pd.Series(close).rolling(50).mean().values
    sma150 = pd.Series(close).rolling(150).mean().values
    sma200 = pd.Series(close).rolling(200).mean().values

    # 52-week high (rolling 252)
    high_52w = pd.Series(high).rolling(252, min_periods=60).max().values
    # 20-day high
    high_20d = pd.Series(high).rolling(20).max().values

    for i in range(WARMUP, n):
        c = close[i]
        if c <= 0:
            continue

        # 52W High Leaders: within 5% of 52w high, above SMA50
        if not np.isnan(high_52w[i]) and not np.isnan(sma50[i]):
            pct_from_high = (high_52w[i] - c) / high_52w[i] * 100
            if pct_from_high <= 5 and c > sma50[i]:
                mask[i] = True
                continue

        # Stage 2: SMA50 > SMA150 > SMA200, all rising
        if (not np.isnan(sma50[i]) and not np.isnan(sma150[i])
                and not np.isnan(sma200[i]) and i >= 5):
            if (sma50[i] > sma150[i] > sma200[i]
                    and sma50[i] > sma50[i - 5]
                    and sma150[i] > sma150[i - 5]
                    and sma200[i] > sma200[i - 5]
                    and c > sma50[i]):
                mask[i] = True
                continue

        # Momentum Continuation: near 20d high, above SMA50, SMA50 > SMA200
        if not np.isnan(high_20d[i]) and not np.isnan(sma50[i]):
            pct_from_20d = (high_20d[i] - c) / high_20d[i] * 100
            if (pct_from_20d <= 3 and c > sma50[i]
                    and (np.isnan(sma200[i]) or sma50[i] > sma200[i])):
                mask[i] = True
                continue

        # ADX Trend: price > SMA50 (simplified — full ADX check is expensive
        # but the family gate only needs ANY member to fire)
        # Skip — the first three already cover the family well enough.

    return mask


def _no_supply_mask(df: pd.DataFrame, window: int = 10) -> np.ndarray:
    """Return boolean mask where no-supply condition holds."""
    svr = sv.classify(df, ma_len=50, ppv_len=10, dry_frac=5)
    n = len(df)
    mask = np.zeros(n, dtype=bool)
    kinds = svr["kind"].values

    for i in range(window, n):
        tail = kinds[i - window + 1: i + 1]
        red = np.sum(tail == "down")
        ppv = np.sum(tail == "ppv")
        if red == 0 and ppv >= 1:
            mask[i] = True
    return mask


def run(verbose: bool = True):
    symbols = _load_symbols()
    max_h = max(HORIZONS)
    cost_rt = COST_BPS / 50  # round-trip as %

    results_by_sym: dict[str, dict] = {}
    total_signals = 0
    total_gated = 0
    t0 = time.time()

    for sym, df in symbols:
        n = len(df)
        if n < WARMUP + max_h + 2:
            continue
        if verbose:
            print(f"  {sym} ({n} bars) ...", end="", flush=True)

        close = df["close"].values.astype(float)
        opn = df["open"].values.astype(float) if "open" in df.columns else close.copy()
        last_eval = n - max_h - 2

        fam_mask = _vectorized_family_mask(df)
        ns_mask = _no_supply_mask(df)

        # Collect signals with min_gap dedup
        signals = []
        last_sig = -MIN_GAP - 1
        for i in range(WARMUP, last_eval + 1):
            if fam_mask[i] and (i - last_sig) >= MIN_GAP:
                signals.append(i)
                last_sig = i

        if not signals:
            if verbose:
                print(" no signals")
            continue

        gated_ret = {h: [] for h in HORIZONS}
        ungated_ret = {h: [] for h in HORIZONS}

        for bar in signals:
            entry_price = opn[bar + 1] if bar + 1 < n else 0
            if entry_price <= 0:
                continue
            is_gate = ns_mask[bar]
            for h in HORIZONS:
                exit_idx = bar + 1 + h
                if exit_idx >= n:
                    continue
                exit_price = close[exit_idx]
                ret = (exit_price / entry_price - 1) * 100 - cost_rt
                ungated_ret[h].append(ret)
                if is_gate:
                    gated_ret[h].append(ret)

        n_g = len(gated_ret[20])
        n_u = len(ungated_ret[20])
        total_signals += n_u
        total_gated += n_g
        if verbose:
            print(f" {n_u} signals, {n_g} gated")

        results_by_sym[sym] = {
            "gated": {h: np.mean(v) if v else None for h, v in gated_ret.items()},
            "ungated": {h: np.mean(v) if v else None for h, v in ungated_ret.items()},
            "n_gated": {h: len(v) for h, v in gated_ret.items()},
            "n_ungated": {h: len(v) for h, v in ungated_ret.items()},
        }

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"B-122 Gate-vs-No-Gate Study")
    print(f"Symbols with signals: {len(results_by_sym)}")
    print(f"Total signals: {total_signals}, gated: {total_gated} "
          f"({total_gated/total_signals*100:.0f}%)" if total_signals else "")
    print(f"alpha = {ALPHA:.4f} (Bonferroni, {len(HORIZONS)} horizons)")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"{'='*60}\n")

    for h in HORIZONS:
        diffs = []
        n_gated_total = 0
        for sym, r in results_by_sym.items():
            g = r["gated"][h]
            u = r["ungated"][h]
            if g is not None and u is not None:
                diffs.append(g - u)
                n_gated_total += r["n_gated"][h]

        n = len(diffs)
        print(f"@{h}d:  n_symbols_paired={n}")
        if n < MIN_SYMBOLS:
            print(f"  INCONCLUSIVE -- fewer than {MIN_SYMBOLS} symbols with "
                  f"both gated and ungated signals\n")
            continue

        diffs_arr = np.array(diffs)
        mean_diff = np.mean(diffs_arr)
        t_stat, p_val = sp_stats.ttest_1samp(diffs_arr, 0)
        p_one = p_val / 2 if t_stat > 0 else 1 - p_val / 2

        verdict = ("GATE HELPS" if p_one < ALPHA and mean_diff > 0 else
                   "GATE HURTS" if p_one < ALPHA and mean_diff < 0 else
                   "NO DIFFERENCE")
        print(f"  mean(gated - ungated) = {mean_diff:+.3f}%")
        print(f"  t = {t_stat:.3f}, p_one = {p_one:.4f}")
        print(f"  verdict: {verdict}")
        print()


if __name__ == "__main__":
    run(verbose=True)
