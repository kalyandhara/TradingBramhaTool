#!/usr/bin/env python3
"""ml_cross_section_study.py — B-177: is anything learnable that single-feature tests missed?

Pre-registered in trading-wiki/wiki/analyses/Cross-Sectional-ML-Experiment.md before any
forward return was computed. Eight point-in-time features, ranked cross-sectionally on
each 21-session rebalance date; LOGIT and a shallow GBM refit at every test date on an
expanding, purged + embargoed window; IC vs the desk's RS rank alone.

    py -3 -X utf8 tools/ml_cross_section_study.py
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

import residual_momentum_study as b175

N_SYMBOLS, DAYS = b175.N_SYMBOLS, b175.DAYS
STEP, H, WARM, LOOK = b175.STEP, b175.H, b175.WARM, b175.LOOK
FEATURES = ("rs", "resid", "r21", "vol63", "dist_hi", "atr_pct", "vol_ratio", "beta")
MIN_FEATURES = 6
GAP = 2            # train only on rebalance dates <= t - GAP (1 purge + 1 embargo)
MIN_TRAIN = 24
ALPHA = 0.025      # Bonferroni over the two models
OUT = Path(__file__).resolve().parent / "cache" / "ml_cross_section_study.json"


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
        return s, {k: pd.Series(d[k].to_numpy(float), idx) for k in ("open", "high", "low", "close", "volume")}

    with ThreadPoolExecutor(8) as ex:
        got = {s: v for s, v in ex.map(get, syms) if v}
    panel = {k: pd.DataFrame({s: v[k] for s, v in got.items()}).sort_index() for k in ("open", "high", "low", "close", "volume")}
    nifty = sp.fetch_nifty50(days=0)
    nc = pd.Series(np.asarray(nifty["close"]).ravel(), index=pd.to_datetime(nifty.index).tz_localize(None).normalize())
    panel["nifty"] = nc[~nc.index.duplicated()].reindex(panel["close"].index)
    return panel


def _beta(r: np.ndarray, m: np.ndarray) -> float | None:
    ok = np.isfinite(r) & np.isfinite(m)
    if ok.sum() < b175.MIN_SHARED:
        return None
    mm, rr = m[ok], r[ok]
    return float(mm @ rr / (mm @ mm)) if mm @ mm > 0 else None


def features_at(panel: dict, i: int) -> pd.DataFrame:
    """Raw features for every name on bar i, using bars <= i only."""
    import scanner_templates as sc
    c, h, l, v = (panel[k] for k in ("close", "high", "low", "volume"))
    lr = np.log(c).diff()
    lm = np.log(panel["nifty"]).diff()
    m = lm.iloc[i - LOOK + 1:i + 1].to_numpy()
    rows = {}
    for s in c.columns:
        cs = c[s].iloc[:i + 1].dropna()
        if len(cs) < WARM:
            continue
        r = lr[s].iloc[i - LOOK + 1:i + 1].to_numpy()
        hs, ls = h[s].iloc[:i + 1], l[s].iloc[:i + 1]
        tr = pd.concat([hs - ls, (hs - cs.shift()).abs(), (ls - cs.shift()).abs()], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
        vs = v[s].iloc[:i + 1]
        v20, v120 = vs.iloc[-20:].mean(), vs.iloc[-120:].mean()
        last = float(cs.iloc[-1])
        rows[s] = {
            "rs": sc._weighted_trailing_return(cs),
            "resid": b175.resid_score(r, m),
            "r21": last / float(cs.iloc[-22]) - 1,
            "vol63": float(np.nanstd(r[-63:], ddof=1)),
            "dist_hi": last / float(hs.iloc[-252:].max()) - 1,
            "atr_pct": float(atr) / last if last > 0 else None,
            "vol_ratio": float(v20 / v120) if v120 > 0 else None,
            "beta": _beta(r, m),
        }
    return pd.DataFrame.from_dict(rows, orient="index", columns=list(FEATURES)).astype(float)


def rank_features(raw: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional percentile ranks; missing -> 0.5; drop names with < MIN_FEATURES."""
    keep = raw.notna().sum(axis=1) >= MIN_FEATURES
    return raw[keep].rank(pct=True).fillna(0.5)


def build_dates(panel: dict) -> list[dict]:
    o, c = panel["open"], panel["close"]
    out = []
    for i in range(WARM, len(c.index) - H - 1, STEP):
        X = rank_features(features_at(panel, i))
        fwd = (c.iloc[i + H] / o.iloc[i + 1] - 1).reindex(X.index)
        ok = fwd.notna() & np.isfinite(fwd)
        X, fwd = X[ok], fwd[ok]
        if len(X) < 50:
            continue
        exit_px, entry_px = c.iloc[i + H].reindex(X.index), o.iloc[i + 1].reindex(X.index)
        out.append({"date": str(c.index[i].date()), "X": X, "y": fwd, "entry": entry_px, "exit": exit_px})
    return out


def _models():
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression
    return {"LOGIT": LogisticRegression(C=1.0, max_iter=1000),
            "GBM": HistGradientBoostingRegressor(max_depth=3, max_iter=200, learning_rate=0.05, random_state=0)}


def walk_forward(dates: list[dict]) -> list[dict]:
    import backtest as bt
    cm = bt.COST_INDIAN
    rows, prev_top = [], {"LOGIT": set(), "GBM": set()}
    for t in range(len(dates)):
        train = dates[:max(0, t - GAP + 1)]
        if len(train) < MIN_TRAIN:
            continue
        Xtr = pd.concat([d["X"] for d in train]).to_numpy()
        yrk = pd.concat([d["y"].rank(pct=True) for d in train]).to_numpy()
        test = dates[t]
        Xte, y = test["X"].to_numpy(), test["y"].to_numpy()
        row = {"date": test["date"], "n": len(y),
               "ic_rs": float(stats.spearmanr(test["X"]["rs"].to_numpy(), y)[0])}
        univ = float(np.mean(y)) * 100
        for name, mdl in _models().items():
            if name == "LOGIT":
                mdl.fit(Xtr, (yrk > 2 / 3).astype(int))
                pred = mdl.predict_proba(Xte)[:, 1]
            else:
                mdl.fit(Xtr, yrk)
                pred = mdl.predict(Xte)
            row[f"ic_{name}"] = float(stats.spearmanr(pred, y)[0])
            k = max(1, len(y) // 5)
            top_idx = np.argsort(-pred)[:k]
            names = test["X"].index[top_idx]
            gross = float(np.mean(y[top_idx])) * 100
            new = [s for s in names if s not in prev_top[name]]
            cost = (sum(cm.round_trip_pct(float(test["entry"][s]), float(test["exit"][s])) for s in new) / k) if new else 0.0
            row[f"xs_net_{name}"] = gross - univ - cost
            prev_top[name] = set(names)
        rows.append(row)
    return rows


def _t(xs):
    a = np.asarray(xs, float)
    if len(a) < 2 or a.std(ddof=1) == 0:
        return float("nan"), float("nan")
    t = a.mean() / (a.std(ddof=1) / math.sqrt(len(a)))
    return float(t), float(2 * stats.t.sf(abs(t), len(a) - 1))


def summarise(rows: list[dict]) -> dict:
    out = {"test_dates": len(rows), "first": rows[0]["date"] if rows else None,
           "last": rows[-1]["date"] if rows else None, "models": {}}
    t_rs, p_rs = _t([r["ic_rs"] for r in rows])
    out["ic_rs"] = {"mean": round(float(np.mean([r["ic_rs"] for r in rows])), 4), "p": round(p_rs, 4)}
    k = len(rows)
    learnable = []
    for name in ("LOGIT", "GBM"):
        ic = [r[f"ic_{name}"] for r in rows]
        dic = [r[f"ic_{name}"] - r["ic_rs"] for r in rows]
        xs = [r[f"xs_net_{name}"] for r in rows]
        _, p_ic = _t(ic)
        _, p_d = _t(dic)
        _, p_x = _t(xs)
        win = [round(float(np.mean(w)), 4) for w in (dic[:k // 3], dic[k // 3:2 * k // 3], dic[2 * k // 3:]) if w]
        m = {"ic": round(float(np.mean(ic)), 4), "p_ic": round(p_ic, 4),
             "delta_ic": round(float(np.mean(dic)), 4), "p_delta": round(p_d, 4),
             "delta_windows": win, "top_q_net_excess_pct": round(float(np.mean(xs)), 3), "p_excess": round(p_x, 4)}
        ok = (m["delta_ic"] > 0 and m["p_delta"] < ALPHA and m["ic"] > 0 and m["p_ic"] < ALPHA
              and sum(w > 0 for w in win) >= 2 and m["top_q_net_excess_pct"] > 0)
        m["passes"] = ok
        out["models"][name] = m
        if ok:
            learnable.append(name)
    out["verdict"] = f"LEARNABLE ({', '.join(learnable)}) — file B-177r" if learnable else "NOTHING LEARNABLE"
    return out


def main() -> int:
    dates = build_dates(build_panel())
    rows = walk_forward(dates)
    res = {"rebalance_dates": len(dates), **summarise(rows), "rows": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
