"""Rule B re-run with the one control the pooled test cannot give: clustering.

``order_block_rules_backtest`` pools every stride bar, and a stacked-zone lean
PERSISTS — the same regime supplies dozens of consecutive observations on one
name. So n=8948 is nowhere near 8948 independent draws and the pooled t-stat is
inflated by an unknown factor. The pooled SIGN is still the finding; the pooled
p-value is not evidence on its own, and a retirement decision must not rest on it.

This re-runs Rule B only, keeping the per-symbol mean, and tests across the 50
SYMBOLS as the unit — 50 clusters, one number each. It is the conservative test:
if the inversion survives here it is not an artefact of counting the same regime
many times.

    python tools/ob_bias_clustered.py [--stride 10]
"""
from __future__ import annotations

import sys
import time

import numpy as np

import backtest as bt
import scanner_templates as sc
from order_block_rules_backtest import PIVOT_LEN, WARMUP, fwd_returns

H = 20


def main(stride: int = 10, days: int = 1500) -> None:
    import screener_pipeline as sp
    cm = bt.COST_GROSS
    rows = []
    t0 = time.time()

    for si, sym in enumerate(bt.LIQUID_50):
        try:
            df = sp.fetch_ohlcv(sym, days=days)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        df = df.dropna(subset=["high", "low", "close", "volume"]).reset_index(drop=True)
        n = len(df)
        if n < WARMUP + 62:
            continue
        close = df["close"].to_numpy(dtype=float)
        openp = (df["open"].to_numpy(dtype=float) if "open" in df.columns else close)
        last_eval = n - 62

        base, bull, bear = [], [], []
        for t in range(WARMUP, last_eval + 1):
            e = openp[t + 1]
            if e > 0:
                base.append((close[t + 1 + H] / e - 1.0) * 100.0)

        for t in range(WARMUP, last_eval + 1, stride):
            try:
                zones, _ = sc.detect_order_blocks(df.iloc[:t + 1], pivot_len=PIVOT_LEN)
            except Exception:
                continue
            live = [z for z in zones if z["state"] != "violated"]
            if not live:
                continue

            def w(d):
                zs = [z for z in live if z["dir"] == d]
                fresh = sum(1 for z in zs if z["state"] == "fresh")
                return fresh * 2 + (len(zs) - fresh)
            lean = w("bull") - w("bear")
            if lean == 0:
                continue
            d = "bull" if lean > 0 else "bear"
            fr = fwd_returns(df, t, d, cm).get(H)
            if fr is None:
                continue
            (bull if d == "bull" else bear).append(fr)

        if not base or (not bull and not bear):
            continue
        bm = float(np.mean(base))
        # Edge against the DIRECTION-MATCHED benchmark: long a random bar for a
        # bullish lean, short a random bar for a bearish one.
        rows.append({
            "sym": sym, "base": bm,
            "bull_edge": (float(np.mean(bull)) - bm) if bull else np.nan,
            "bear_edge": (float(np.mean(bear)) + bm) if bear else np.nan,
            "n_bull": len(bull), "n_bear": len(bear),
        })
        print(f"  [{si+1}/50] {sym:<13} bull {rows[-1]['bull_edge']:+7.3f} "
              f"(n={len(bull):3d})  bear {rows[-1]['bear_edge']:+7.3f} "
              f"(n={len(bear):3d})  {time.time()-t0:.0f}s", flush=True)

    print("\n" + "=" * 70)
    print(f"RULE B — CLUSTERED BY SYMBOL ({len(rows)} clusters, stride {stride}, @{H}d)")
    print("Unit of analysis is the SYMBOL, not the bar. One number per name.")
    print("=" * 70)
    for key, label in (("bull_edge", "bullish lean (vs long-random)"),
                       ("bear_edge", "bearish lean (vs short-random)")):
        v = np.asarray([r[key] for r in rows], dtype=float)
        v = v[~np.isnan(v)]
        if v.size < 3:
            continue
        t, p = bt._ttest_1samp(v)
        neg = int((v < 0).sum())
        print(f"\n{label}")
        print(f"  mean edge {v.mean():+.3f}pp   median {np.median(v):+.3f}pp")
        print(f"  t={t:+.2f}  p={p:.4f}  n_clusters={v.size}")
        print(f"  symbols with NEGATIVE edge: {neg}/{v.size}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    st = 10
    if "--stride" in sys.argv:
        st = int(sys.argv[sys.argv.index("--stride") + 1])
    main(stride=st)
