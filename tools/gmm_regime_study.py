#!/usr/bin/env python3
"""gmm_regime_study.py — B-174: does a learned regime beat the rule and the naive vol?

Pre-registered in trading-wiki/wiki/analyses/GMM-Regime-vs-Verdict.md before any
data was loaded. Predictors (point-in-time): P(stressed) from gmm_regime, the
verdict's VOLATILE flag, trailing 20-day vol. Targets: forward 20-day vol
(primary) and forward 20-day drawdown. Spearman rho; 60-day moving-block
bootstrap (2,000 draws, seed 174) on the differences.

    py -3 -X utf8 tools/gmm_regime_study.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import gmm_regime as gm

H = 20
BLOCK = 60
DRAWS = 2000
SEED = 174
VERDICT_BARS = 400        # classify_regime reads at most ~273 trailing bars
OUT = Path(__file__).resolve().parent / "cache" / "gmm_regime_study.json"


def load_close() -> pd.Series:
    import screener_pipeline as sp
    df = sp.fetch_nifty50(days=0)
    c = df["close"] if "close" in df.columns else df.iloc[:, 0]
    c = pd.Series(np.asarray(c, dtype=float).ravel(), index=pd.to_datetime(df.index))
    return c[~c.index.duplicated()].dropna().sort_index()


def volatile_flags(close: pd.Series, days: pd.DatetimeIndex) -> pd.Series:
    import market_verdict as mv
    pos = {d: i for i, d in enumerate(close.index)}
    out = {}
    for d in days:
        i = pos[d]
        w = close.iloc[max(0, i - VERDICT_BARS + 1):i + 1].to_frame("close")
        out[d] = 1.0 if mv.classify_regime(w)["label"] == "VOLATILE" else 0.0
    return pd.Series(out)


def targets(close: pd.Series) -> pd.DataFrame:
    r = np.log(close).diff()
    fwd_vol = r[::-1].rolling(H).std()[::-1].shift(-1)          # std of r[t+1..t+H]
    fut_min = close[::-1].rolling(H).min()[::-1].shift(-1)       # min close[t+1..t+H]
    fwd_dd = (-(fut_min / close - 1)).clip(lower=0)
    return pd.DataFrame({"fwd_vol": fwd_vol, "fwd_dd": fwd_dd})


def block_boot(a: np.ndarray, b: np.ndarray, y: np.ndarray, rng) -> np.ndarray:
    """Bootstrap of rho(a,y) - rho(b,y) with contiguous 60-day blocks."""
    n = len(y)
    starts = np.arange(n - BLOCK + 1)
    k = int(np.ceil(n / BLOCK))
    diffs = np.empty(DRAWS)
    for i in range(DRAWS):
        idx = np.concatenate([np.arange(s, s + BLOCK) for s in rng.choice(starts, k)])[:n]
        diffs[i] = spearmanr(a[idx], y[idx])[0] - spearmanr(b[idx], y[idx])[0]
    return diffs


def main() -> int:
    close = load_close()
    p = gm.rolling_stress(close)
    feat = gm.features(close)
    tg = targets(close)
    df = pd.DataFrame({"p_stress": p, "trail_vol": feat["v"]}).join(tg).dropna()
    df["volatile"] = volatile_flags(close, df.index)
    rng = np.random.default_rng(SEED)
    res = {"days": int(len(df)), "from": str(df.index[0].date()), "to": str(df.index[-1].date()),
           "pct_days_stressed_gt_0_5": round(float((df["p_stress"] > 0.5).mean() * 100), 1),
           "pct_days_volatile": round(float(df["volatile"].mean() * 100), 1),
           "targets": {}}
    for tgt in ("fwd_vol", "fwd_dd"):
        y = df[tgt].to_numpy()
        rho = {k: round(float(spearmanr(df[k], y)[0]), 3) for k in ("p_stress", "trail_vol", "volatile")}
        row = {"rho": rho, "vs": {}}
        for comp in ("trail_vol", "volatile"):
            d = block_boot(df["p_stress"].to_numpy(), df[comp].to_numpy(), y, rng)
            lo, hi = np.percentile(d, [2.5, 97.5])
            row["vs"][comp] = {"diff": round(rho["p_stress"] - rho[comp], 3),
                               "ci95": [round(float(lo), 3), round(float(hi), 3)],
                               "beats": bool(lo > 0)}
        row["verdict"] = ("ADDS INFORMATION" if all(v["beats"] for v in row["vs"].values())
                          else "DOES NOT ADD INFORMATION")
        res["targets"][tgt] = row
    res["decision"] = ("FILE B-174r (HMM variant; P(stressed) as Home context)"
                       if res["targets"]["fwd_vol"]["verdict"] == "ADDS INFORMATION"
                       else "CLOSE B-174 — regime stays rule-based")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
