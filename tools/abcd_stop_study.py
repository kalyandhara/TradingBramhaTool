#!/usr/bin/env python3
"""abcd_stop_study.py — B-132: is the AB=CD edge given away by its stop?

    py -3 -X utf8 tools/abcd_stop_study.py        # writes cache/abcd_stop_study.json

PRE-REGISTRATION: trading-wiki/wiki/analyses/ABCD-Stop-Study.md, written 2026-10-14
before this file touched the data. In short:

  * Signals: B-129r's AB=CD-only arm of `Harmonic Reversal (XABCD)` (bullish, the
    card's R:R gate unchanged). Entry = D, target = T2, time stop 10 bars.
    Harness: backtest_scanner, COST_INDIAN, signal_mode="fresh", fill_model="market".
  * Arms — ONLY the stop changes: A0 card (D - 0.5% of D), A1 D - 1.0 x ATR14,
    A2 D - 2.0 x ATR14 (ATR14 on the signal bar).
  * Fresh panel: nifty500 names 301-500 (B-129r used the first 300), 1500 days.
  * Measure: plan return in % of entry = R x (entry - stop) / entry (net of costs).
  * Primary: per-symbol (arm % - A0 %), one-sample t, alpha 0.025 per arm.
  * SHIPS if beats A0 at p<0.025 AND own plan % > 0 pooled and per-symbol
    (p<0.05) AND >= 30 symbols, >= 150 trades. Otherwise NO CHANGE. No tier change.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

import backtest as bt
import scanner_templates as sc

BASE = "Harmonic Reversal (XABCD)"
ARMS = {"A0": ("_B132 AB=CD card stop", None),
        "A1": ("_B132 AB=CD stop 1.0 ATR", 1.0),
        "A2": ("_B132 AB=CD stop 2.0 ATR", 2.0)}
PANEL = (300, 500)            # nifty500 slice [300:500] — names 301-500
DAYS = 1500
ALPHA_ARM, ALPHA_OWN = 0.025, 0.05
MIN_SYMBOLS, MIN_TRADES = 30, 150
OUT = Path(__file__).resolve().parent / "cache" / "abcd_stop_study.json"

_base_fn = sc.SCANNERS[BASE]["fn"]
_memo: dict = {}


def _abcd(df):
    """The registered scanner's AB=CD hits, detected ONCE per (symbol, bar) and
    shared by every arm (same memo key as harmonic_bull_remeasure)."""
    k = (len(df), float(df["close"].iloc[0]), float(df["close"].iloc[-1]),
         float(df["high"].iloc[-1]), float(df["low"].iloc[-1]))
    if k not in _memo:
        h = _base_fn(df)
        _memo[k] = h if (h is not None and "AB=CD" in str(h.get("pattern_type", ""))) else None
    return _memo[k]


def _arm(k_atr: float | None):
    def fn(df):
        h = _abcd(df)
        if h is None or k_atr is None:
            return h
        atr = float(sc._atr_series(df, 14).iloc[-1])
        if not atr > 0:
            return None
        return {**h, "stop": round(float(h["entry"]) - k_atr * atr, 2)}
    return fn


for _tag, (_name, _k) in ARMS.items():
    sc.SCANNERS[_name] = {**sc.SCANNERS[BASE], "fn": _arm(_k)}


def _ttest(xs) -> tuple[float | None, float | None]:
    a = np.asarray(list(xs), dtype=float)
    if len(a) < 2 or float(a.std(ddof=1)) == 0:
        return None, None
    t = float(a.mean()) / (float(a.std(ddof=1)) / math.sqrt(len(a)))
    from scipy import stats
    return round(t, 3), float(2 * stats.t.sf(abs(t), df=len(a) - 1))


def _pct(tr: dict) -> float:
    e, s = float(tr["entry_px"]), float(tr["stop"])
    return float(tr["r"]) * abs(e - s) / e * 100.0


def main() -> int:
    import nse_universe as nu
    import screener_pipeline as sp
    cache: dict = {}

    def fetch(s):
        if s not in cache:
            try:
                cache[s] = sp.fetch_ohlcv(s, days=DAYS)
            except Exception:
                cache[s] = None
        return cache[s]

    syms = list(nu.symbols("nifty500"))[PANEL[0]:PANEL[1]]
    common = dict(cost_model=bt.COST_INDIAN, signal_mode="fresh", fill_model="market",
                  keep_trades=True)
    out: dict[str, Any] = {"preregistered": "2026-10-14", "panel": f"nifty500[{PANEL[0]}:{PANEL[1]}]",
                           "symbols_requested": len(syms), "arms": {}}
    per_sym: dict[str, dict[str, list[float]]] = {}
    for tag, (name, k) in ARMS.items():
        r = bt.backtest_scanner(name, syms, fetch, **common)
        trades = r.get("trades") or []
        pcts = [_pct(t) for t in trades]
        by = {}
        for t, p in zip(trades, pcts):
            by.setdefault(t["symbol"], []).append(p)
        per_sym[tag] = by
        pl = r.get("r_metrics") or r.get("plans") or {}
        n = len(trades)
        outc = [t.get("outcome") for t in trades]
        t_own, p_own = _ttest(np.mean(v) for v in by.values())
        out["arms"][tag] = {
            "stop_rule": "card D-0.5%" if k is None else f"D - {k} x ATR14",
            "n_trades": n, "n_symbols": len(by),
            "mean_plan_pct": round(float(np.mean(pcts)), 3) if pcts else None,
            "per_symbol_mean_pct": round(float(np.mean([np.mean(v) for v in by.values()])), 3) if by else None,
            "per_symbol_t": t_own, "per_symbol_p": p_own,
            "avg_R": round(float(np.mean([t["r"] for t in trades])), 3) if trades else None,
            "target_rate": round(outc.count("target") / n, 3) if n else None,
            "stop_rate": round(outc.count("stop") / n, 3) if n else None,
            "time_rate": round((outc.count("time") + outc.count("open")) / n, 3) if n else None,
            "plans_unfilled": pl.get("plans_unfilled"),
            "plans_fill_through_stop": pl.get("plans_fill_through_stop"),
            "signal_edge": {h: (r.get("horizons") or {}).get(h, {}).get("edge") for h in (10, 20, 60)},
            "n_signals": r.get("n_signals"),
        }
        print(f"{tag} {out['arms'][tag]}", flush=True)

    a0 = per_sym["A0"]
    ships = {}
    for tag in ("A1", "A2"):
        arm = per_sym[tag]
        common_syms = [s for s in arm if s in a0]
        diffs = [np.mean(arm[s]) - np.mean(a0[s]) for s in common_syms]
        t, p = _ttest(diffs)
        a = out["arms"][tag]
        cmp = {"n_symbols": len(diffs),
               "mean_diff_pct": round(float(np.mean(diffs)), 3) if diffs else None,
               "t": t, "p": p}
        ok = (p is not None and p < ALPHA_ARM and (cmp["mean_diff_pct"] or 0) > 0
              and (a["mean_plan_pct"] or 0) > 0 and (a["per_symbol_mean_pct"] or 0) > 0
              and a["per_symbol_p"] is not None and a["per_symbol_p"] < ALPHA_OWN
              and a["n_symbols"] >= MIN_SYMBOLS and a["n_trades"] >= MIN_TRADES)
        a["vs_A0"] = cmp
        a["ships"] = bool(ok)
        if ok:
            ships[tag] = cmp["mean_diff_pct"]
    out["decision"] = (f"SHIP {max(ships, key=ships.get)}" if ships else "NO CHANGE")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nDECISION: {out['decision']}\nwritten {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
