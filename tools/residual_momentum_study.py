#!/usr/bin/env python3
"""residual_momentum_study.py — B-175: residual momentum vs the desk's RS rank.

Pre-registered in trading-wiki/wiki/analyses/Residual-Momentum-vs-RS.md before any
forward return was computed. Monthly (21-session) cross-sectional Spearman IC of
each predictor with the next-21-session return; mean IC and ΔIC t-tests across
dates; 3-window sign stability.

    py -3 -X utf8 tools/residual_momentum_study.py
"""
from __future__ import annotations

import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

N_SYMBOLS, DAYS = 300, 1500
STEP, H = 21, 21
LOOK, SKIP, MIN_SHARED = 252, 21, 200
WARM = 273
OUT = Path(__file__).resolve().parent / "cache" / "residual_momentum_study.json"


def resid_score(r: np.ndarray, m: np.ndarray) -> float | None:
    """12-1 residual momentum from aligned daily log returns (last LOOK days,
    newest last). Sum of residuals excluding the newest SKIP, over their std."""
    ok = np.isfinite(r) & np.isfinite(m)
    if ok.sum() < MIN_SHARED:
        return None
    # NO intercept, on purpose: with an intercept fitted over this same window the
    # residuals sum to ~0 across it, and "sum over all but the last month" would
    # just be minus the last month — a reversal signal, not momentum. The
    # intercept is the name's own drift, which is what this score is meant to keep.
    mm, rr = m[ok], r[ok]
    beta = float(mm @ rr / (mm @ mm)) if mm @ mm > 0 else 0.0
    e = r - beta * m
    e_form = e[:-SKIP]
    e_form = e_form[np.isfinite(e_form)]
    sd = e_form.std(ddof=1)
    return float(e_form.sum() / sd) if sd > 0 else None


def build_panel():
    logging.disable(logging.WARNING)
    import nse_universe as nu
    import screener_pipeline as sp
    syms = list(nu.symbols("nifty500"))[:N_SYMBOLS]

    def get(s):
        try:
            df = sp.fetch_ohlcv(s, days=DAYS)
        except Exception:
            return s, None
        if df is None or len(df) < WARM + H + 5:
            return s, None
        d = df.reset_index(drop="date" in df.columns)
        idx = pd.to_datetime(d["date"] if "date" in d.columns else d.iloc[:, 0]).dt.tz_localize(None).dt.normalize()
        return s, (pd.Series(d["open"].to_numpy(float), idx), pd.Series(d["close"].to_numpy(float), idx))

    with ThreadPoolExecutor(8) as ex:
        got = dict(ex.map(get, syms))
    opens = pd.DataFrame({s: v[0] for s, v in got.items() if v}).sort_index()
    closes = pd.DataFrame({s: v[1] for s, v in got.items() if v}).sort_index()
    nifty = sp.fetch_nifty50(days=0)
    nc = pd.Series(np.asarray(nifty["close"]).ravel(), index=pd.to_datetime(nifty.index).tz_localize(None).normalize())
    nc = nc[~nc.index.duplicated()].reindex(closes.index)
    return opens, closes, nc


def run(opens: pd.DataFrame, closes: pd.DataFrame, nifty: pd.Series) -> dict:
    import scanner_templates as sc
    lr = np.log(closes).diff()
    lm = np.log(nifty).diff()
    dates = closes.index
    rows = []
    for i in range(WARM, len(dates) - H - 1, STEP):
        d = dates[i]
        fwd = closes.iloc[i + H] / opens.iloc[i + 1] - 1
        rs, rd = {}, {}
        for s in closes.columns:
            c = closes[s].iloc[:i + 1].dropna()
            if len(c) < WARM or not np.isfinite(fwd.get(s, np.nan)):
                continue
            rs[s] = sc._weighted_trailing_return(c)
            v = resid_score(lr[s].iloc[i - LOOK + 1:i + 1].to_numpy(), lm.iloc[i - LOOK + 1:i + 1].to_numpy())
            if v is not None:
                rd[s] = v
        common = [s for s in rd if s in rs]
        if len(common) < 50:
            continue
        y = fwd[common].to_numpy(float)
        ic_rs = stats.spearmanr([rs[s] for s in common], y)[0]
        ic_rd = stats.spearmanr([rd[s] for s in common], y)[0]
        rows.append({"date": str(d.date()), "n": len(common), "ic_rs": float(ic_rs), "ic_resid": float(ic_rd)})
    return summarise(rows)


def _t(xs):
    a = np.asarray(xs, float)
    t = a.mean() / (a.std(ddof=1) / math.sqrt(len(a)))
    return float(t), float(2 * stats.t.sf(abs(t), len(a) - 1))


def summarise(rows: list[dict]) -> dict:
    ic_rs = [r["ic_rs"] for r in rows]
    ic_rd = [r["ic_resid"] for r in rows]
    dic = [b - a for a, b in zip(ic_rs, ic_rd)]
    k = len(rows)
    thirds = [dic[:k // 3], dic[k // 3:2 * k // 3], dic[2 * k // 3:]]
    out = {"dates": k, "first": rows[0]["date"] if rows else None, "last": rows[-1]["date"] if rows else None,
           "median_names": int(np.median([r["n"] for r in rows])) if rows else 0}
    for name, xs in (("ic_rs", ic_rs), ("ic_resid", ic_rd), ("delta_ic", dic)):
        t, p = _t(xs)
        out[name] = {"mean": round(float(np.mean(xs)), 4), "t": round(t, 2), "p": round(p, 4),
                     "pct_dates_positive": round(100 * float(np.mean([x > 0 for x in xs])), 1)}
    out["delta_ic_windows"] = [round(float(np.mean(w)), 4) for w in thirds if w]
    adds = (out["delta_ic"]["mean"] > 0 and out["delta_ic"]["p"] < 0.05
            and out["ic_resid"]["mean"] > 0 and out["ic_resid"]["p"] < 0.05
            and sum(w > 0 for w in out["delta_ic_windows"]) >= 2)
    out["verdict"] = "RESID ADDS — file B-175r" if adds else "NO CHANGE"
    out["rows"] = rows
    return out


def main() -> int:
    res = run(*build_panel())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
