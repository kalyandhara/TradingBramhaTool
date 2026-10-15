#!/usr/bin/env python3
"""score_calibration_study.py — B-172: does each scanner's own score rank its hits?

Pre-registered in trading-wiki/wiki/analyses/Scanner-Score-Calibration.md before
the census was run. Every registered scanner, as shipped, on every 5th bar of the
first 150 nifty500 names; a hit counts if its card has a numeric `score`.
Outcome: next-open → close+20 return minus the symbol's mean 20-session return
(secondary: 60). Per scanner: top-tercile minus bottom-tercile spread of its own
score; symbol-cluster bootstrap, Bonferroni over qualifying scanners.

    py -3 -X utf8 tools/score_calibration_study.py --procs 7
"""
from __future__ import annotations

import argparse
import json
import logging
from multiprocessing import Pool
from pathlib import Path

import numpy as np

N_SYMBOLS = 150
DAYS = 1500
STRIDE = 5
WARMUP = 300
HORIZONS = (20, 60)
DRAWS = 2000
SEED = 172
MIN_HITS = 90
MIN_SYMBOLS = 15
OUT = Path(__file__).resolve().parent / "cache" / "score_calibration_study.json"


def _scan_symbol(sym: str) -> list[dict]:
    """(scanner, symbol, score, fwd20, fwd60) for every scored hit — fwd returns
    already de-meaned by the symbol's own mean over the evaluation span."""
    logging.disable(logging.WARNING)
    import screener_pipeline as sp
    import scanner_templates as sc
    try:
        df = sp.fetch_ohlcv(sym, days=DAYS)
    except Exception:
        return []
    if df is None or len(df) < WARMUP + max(HORIZONS) + 10:
        return []
    df = df.reset_index(drop=True)
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = len(df)
    last_t = n - 1 - max(HORIZONS)
    evals = list(range(WARMUP, last_t + 1, STRIDE))
    fwd = {h: np.array([c[t + h] / o[t + 1] - 1 for t in evals]) for h in HORIZONS}
    mean = {h: float(np.nanmean(fwd[h])) for h in HORIZONS}
    rows = []
    for k, t in enumerate(evals):
        sl = df.iloc[:t + 1]
        for name, spec in sc.SCANNERS.items():
            try:
                card = spec["fn"](sl)
            except Exception:
                card = None
            if not card or not isinstance(card.get("score"), (int, float)):
                continue
            s = float(card["score"])
            if not np.isfinite(s):
                continue
            rows.append({"scanner": name, "symbol": sym, "score": s,
                         **{f"fwd{h}": float(fwd[h][k] - mean[h]) for h in HORIZONS}})
    return rows


def tercile_spread(scores: np.ndarray, y: np.ndarray) -> float | None:
    """Mean y of the top tercile minus the bottom tercile, by rank (ties by order)."""
    m = len(scores)
    if m < 3:
        return None
    order = np.argsort(scores, kind="stable")
    k = m // 3
    return float(y[order[-k:]].mean() - y[order[:k]].mean())


def bootstrap(rows: list[dict], key: str, rng, draws: int = DRAWS) -> np.ndarray:
    """Symbol-cluster bootstrap of the tercile spread."""
    by = {}
    for r in rows:
        by.setdefault(r["symbol"], []).append(r)
    syms = list(by)
    out = []
    for _ in range(draws):
        pick = rng.choice(len(syms), len(syms), replace=True)
        rr = [x for i in pick for x in by[syms[i]]]
        v = tercile_spread(np.array([x["score"] for x in rr]), np.array([x[key] for x in rr]))
        if v is not None:
            out.append(v)
    return np.array(out)


def label(rows: list[dict], key: str, risk: bool, alpha: float, rng) -> dict:
    n, n_sym = len(rows), len({r["symbol"] for r in rows})
    distinct = len({round(r["score"], 6) for r in rows})
    base = {"hits": n, "symbols": n_sym, "distinct_scores": distinct}
    if distinct < 3:
        return {**base, "label": "NO SPREAD"}
    if n < MIN_HITS or n_sym < MIN_SYMBOLS:
        return {**base, "label": "INSUFFICIENT"}
    spread = tercile_spread(np.array([r["score"] for r in rows]), np.array([r[key] for r in rows]))
    b = bootstrap(rows, key, rng)
    lo, hi = np.percentile(b, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    useful_pos = not risk
    if (lo > 0 and useful_pos) or (hi < 0 and not useful_pos):
        lab = "RANKS"
    elif (hi < 0 and useful_pos) or (lo > 0 and not useful_pos):
        lab = "INVERTED"
    else:
        lab = "NO EVIDENCE"
    return {**base, "spread_pp": round(100 * spread, 2),
            "ci_pp": [round(100 * float(lo), 2), round(100 * float(hi), 2)], "label": lab}


def analyse(rows: list[dict], risk_scanners: set[str]) -> dict:
    by = {}
    for r in rows:
        by.setdefault(r["scanner"], []).append(r)
    qualifying = [s for s, rr in by.items()
                  if len(rr) >= MIN_HITS and len({x["symbol"] for x in rr}) >= MIN_SYMBOLS
                  and len({round(x["score"], 6) for x in rr}) >= 3]
    k = max(1, len(qualifying))
    alpha = 0.05 / k
    rng = np.random.default_rng(SEED)
    res = {}
    for s in sorted(by):
        risk = s in risk_scanners
        res[s] = {"risk_scanner": risk,
                  **{f"h{h}": label(by[s], f"fwd{h}", risk, alpha, rng) for h in HORIZONS}}
    prim = [res[s]["h20"]["label"] for s in qualifying]
    ranks = sum(lbl == "RANKS" for lbl in prim)
    return {"qualifying": len(qualifying), "alpha_two_sided": alpha, "ranks_h20": ranks,
            "inverted_h20": sorted(s for s in qualifying if res[s]["h20"]["label"] == "INVERTED"),
            "decision": ("FILE B-172r — OWNER: should best_score keep 30% of rank_score?"
                         if ranks < len(qualifying) / 4 else "no follow-up owed"),
            "scanners": res}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--symbols", type=int, default=N_SYMBOLS)
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    import nse_universe as nu
    import opportunity_hub as oh
    syms = list(nu.symbols("nifty500"))[:a.symbols]
    with Pool(a.procs) as p:
        rows = [r for rr in p.imap_unordered(_scan_symbol, syms) for r in rr]
    res = analyse(rows, set(getattr(oh, "RISK_SCANNERS", ())))
    res["symbols_requested"] = len(syms)
    res["symbols_with_hits"] = len({r["symbol"] for r in rows})
    res["scored_hits"] = len(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"scored hits {len(rows)} · qualifying scanners {res['qualifying']} · "
          f"RANKS @20 {res['ranks_h20']} · INVERTED {res['inverted_h20']}")
    for s, v in res["scanners"].items():
        h = v["h20"]
        print(f"  {s:42s} {h['label']:13s} hits {h['hits']:5d}  "
              f"spread {h.get('spread_pp', '—')}  ci {h.get('ci_pp', '—')}")
    print("DECISION:", res["decision"])
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
