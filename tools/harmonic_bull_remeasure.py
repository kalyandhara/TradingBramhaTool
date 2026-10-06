#!/usr/bin/env python3
"""harmonic_bull_remeasure.py - B-129 follow-up: can bullish-only Harmonic earn
its tier back?

B-129 (2026-09-23) demoted Harmonic Reversal to the weak tier (0.25) and made
the scanner bullish-only. The pooled +0.88% @20d that had kept it in
MEASURED_EDGE_SCANNERS mixed a failing short thesis with a long one that was
+1.07% @20d but positive in only 2 of 3 windows. The owner's condition for a
higher tier: "a bullish-only re-measure that is stable across windows, on
next-open fills."

One thing moved after B-129 and must be stated, not absorbed: on 2026-09-28
(`48535a7`) the detector gained the four-point AB=CD family, so the scanner
that votes TODAY is not the hit set B-129 split. This study measures both.

== PRE-REGISTRATION -- written 2026-10-05 BEFORE this file was first run ==

  R0  REPRODUCTION GATE (read first; if it fails, NOTHING below is read)
      XABCD-only bullish (AB=CD hits filtered out -- the hit set B-129 saw),
      under B-129's own settings: backtest.LIQUID_50, 3 windows, COST_INDIAN,
      signal_mode="all", fill_model="assumed", 1500 days.
      B-129 reported n=116, +1.07% @20d. PASS if n is within +/-15% and the
      pooled @20d edge within +/-0.30pp. A fail means the data or the code
      moved since 2026-09-23, and that gets diagnosed before any verdict.

  PANEL (P, the decision)
      nse_universe "nifty500", first 300 names, 1500 days daily, COST_INDIAN,
      signal_mode="fresh" (B-120), fill_model="market" (next open -- B-121,
      the owner's condition), fixed exits with the card's time stop, 3
      non-overlapping walk-forward windows. B-124's panel, so the plan-R
      number is comparable to its -0.15R control.

  ARMS
      P    the registered scanner as it votes today (bullish XABCD + AB=CD)
           -- THIS ONE carries the tier decision
      PX   XABCD only           -- descriptive, same rule applied
      PA   AB=CD only           -- descriptive, same rule applied

  PROMOTE to MEASURED_EDGE_SCANNERS (weight 1.0) only if ALL hold on P:
      1. floors: >= 150 signals and >= 30 symbols with a signal
      2. pooled edge @20d > 0 AND positive in 3 of 3 windows @20d
      3. sign-stable positive in 3/3 windows at one more of {10d, 60d}
         (Falling Wedge, the tier's only member, is stable at 10/20/60)
      4. clustered: per-symbol mean edge @20d > 0, one-sample t across
         symbols, p < 0.05 -- a name that fires ten times is one opinion
      5. pooled plan avg_R > 0 under market fill
  RECOMMEND EXCLUSION (owner call, the VWAP Reclaim precedent) if on P the
      pooled @20d edge < 0, negative in 3/3 windows, AND clustered p < 0.05.
  Otherwise STAYS WEAK (0.25). INCONCLUSIVE if floor 1 fails.

  If PX would promote and P would not, that is a finding about AB=CD, and
  it goes to the owner -- it does NOT promote the scanner, because PX is not
  what votes.

  EXPECTED (prior, written down so a positive has to beat it)
      STAYS WEAK. B-129's bullish split was unstable at every horizon, and
      B-124's next-open control on this scanner was -0.15R, which fails 5.

  py -3 -X utf8 tools/harmonic_bull_remeasure.py
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

import backtest as bt
import scanner_templates as sc

BASE = "Harmonic Reversal (XABCD)"
ARMS = {"P": BASE, "PX": "_B129r XABCD only", "PA": "_B129r AB=CD only"}
N_SYMBOLS = 300
DAYS = 1500
N_WINDOWS = 3
H = 20
MIN_SIGNALS, MIN_SYMBOLS = 150, 30
R0_N, R0_EDGE = 116, 1.07
R0_N_TOL, R0_EDGE_TOL = 0.15, 0.30
OUT = Path(__file__).resolve().parent / "cache" / "harmonic_bull_remeasure.json"

_base_fn = sc.SCANNERS[BASE]["fn"]
_memo: dict = {}


def _base(df):
    """The registered scanner, memoised on the slice so every arm shares ONE
    detection pass. The key is the slice's length plus its first and last bars,
    which is unique per (symbol, bar) in practice."""
    k = (len(df), float(df["close"].iloc[0]), float(df["close"].iloc[-1]),
         float(df["high"].iloc[-1]), float(df["low"].iloc[-1]))
    if k not in _memo:
        _memo[k] = _base_fn(df)
    return _memo[k]


def _is_abcd(hit) -> bool:
    return "AB=CD" in str(hit.get("pattern_type", ""))


def _xabcd_only(df):
    h = _base(df)
    return None if (h is None or _is_abcd(h)) else h


def _abcd_only(df):
    h = _base(df)
    return h if (h is not None and _is_abcd(h)) else None


sc.SCANNERS[BASE] = {**sc.SCANNERS[BASE], "fn": _base}
sc.SCANNERS[ARMS["PX"]] = {**sc.SCANNERS[BASE], "fn": _xabcd_only}
sc.SCANNERS[ARMS["PA"]] = {**sc.SCANNERS[BASE], "fn": _abcd_only}


def _t_test(xs: list[float]) -> tuple[float, float]:
    a = np.asarray(xs, dtype=float)
    n = len(a)
    if n < 2:
        return float("nan"), float("nan")
    sd = float(a.std(ddof=1))
    if sd == 0:
        return float("nan"), float("nan")
    t = float(a.mean()) / (sd / math.sqrt(n))
    try:
        from scipy import stats
        p = float(2 * stats.t.sf(abs(t), df=n - 1))
    except Exception:
        p = float(math.erfc(abs(t) / math.sqrt(2)))
    return t, p


def clustered(name: str, symbols, fetch, **kw) -> dict[str, Any]:
    """Per-symbol @20d edge (signal mean minus that symbol's own random-entry
    mean), then a one-sample t across the symbols that fired."""
    per = []
    for s in symbols:
        r = bt.backtest_scanner(name, [s], fetch, **kw)
        m = (r.get("horizons") or {}).get(H) or {}
        if m.get("n"):
            per.append(float(m["edge"]))
    t, p = _t_test(per)
    return {"symbols": len(per),
            "mean_edge": round(float(np.mean(per)), 3) if per else None,
            "median_edge": round(float(np.median(per)), 3) if per else None,
            "symbols_positive": int(sum(e > 0 for e in per)),
            "t": None if math.isnan(t) else round(t, 2),
            "p": None if math.isnan(p) else round(p, 4)}


def summarise(wf: dict) -> dict[str, Any]:
    st = wf["stability"]["per_horizon"]
    pooled = wf["pooled"]["horizons"]
    return {"n_signals": wf["pooled"]["n_signals"],
            "pooled": {h: pooled.get(h) for h in bt.DEFAULT_HORIZONS},
            "windows": {h: st[h]["window_edges"] for h in bt.DEFAULT_HORIZONS},
            "plans": wf.get("plans"),
            "stability_verdict": wf["stability"]["verdict"]}


def decide(s: dict, cl: dict) -> tuple[str, list[str]]:
    w = s["windows"]
    e20 = (s["pooled"].get(H) or {}).get("edge")
    avg_r = (s["plans"] or {}).get("avg_R")
    checks = {
        "1 floors": s["n_signals"] >= MIN_SIGNALS and cl["symbols"] >= MIN_SYMBOLS,
        "2 @20d >0 and 3/3": e20 is not None and e20 > 0 and all(x > 0 for x in w[H]),
        "3 10d or 60d 3/3 positive": any(all(x > 0 for x in w[h]) for h in (10, 60)),
        "4 clustered p<0.05 positive": (cl["p"] is not None and cl["p"] < 0.05
                                        and (cl["mean_edge"] or 0) > 0),
        "5 plan avg_R > 0": avg_r is not None and avg_r > 0,
    }
    lines = [f"  [{'x' if ok else ' '}] {k}" for k, ok in checks.items()]
    if not checks["1 floors"]:
        return "INCONCLUSIVE", lines
    if all(checks.values()):
        return "PROMOTE", lines
    if (e20 is not None and e20 < 0 and all(x < 0 for x in w[H])
            and cl["p"] is not None and cl["p"] < 0.05 and (cl["mean_edge"] or 0) < 0):
        return "RECOMMEND EXCLUSION", lines
    return "STAYS WEAK", lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--symbols", type=int, default=N_SYMBOLS)
    a = ap.parse_args()
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

    out: dict[str, Any] = {"preregistered": "2026-10-05", "horizon": H}

    # ── R0: reproduction gate ────────────────────────────────────────────────
    r0 = bt.walk_forward_scanner(ARMS["PX"], list(bt.LIQUID_50), fetch,
                                 n_windows=N_WINDOWS, cost_model=bt.COST_INDIAN,
                                 signal_mode="all", fill_model="assumed")
    s0 = summarise(r0)
    n0 = (s0["pooled"].get(H) or {}).get("n", 0)
    e0 = (s0["pooled"].get(H) or {}).get("edge")
    ok0 = (abs(n0 - R0_N) <= R0_N_TOL * R0_N
           and e0 is not None and abs(e0 - R0_EDGE) <= R0_EDGE_TOL)
    out["R0"] = {**s0, "n20": n0, "edge20": e0, "pass": ok0}
    print(f"R0 reproduction: n={n0} (B-129 {R0_N}), @20d {e0} (B-129 +{R0_EDGE}) "
          f"-> {'PASS' if ok0 else 'FAIL'}", flush=True)
    print(f"   windows @20d {s0['windows'][H]}", flush=True)
    if not ok0:
        out["verdict"] = "R0 FAILED - not read"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print(f"\nR0 failed; primary NOT run. written {OUT}")
        return 1

    # ── Panel ────────────────────────────────────────────────────────────────
    syms = list(nu.symbols("nifty500"))[:a.symbols]
    out["symbols_requested"] = len(syms)
    common = dict(cost_model=bt.COST_INDIAN, signal_mode="fresh", fill_model="market")
    out["arms"] = {}
    for tag, name in ARMS.items():
        wf = bt.walk_forward_scanner(name, syms, fetch, n_windows=N_WINDOWS, **common)
        s = summarise(wf)
        cl = clustered(name, syms, fetch, **common)
        v, lines = decide(s, cl)
        out["arms"][tag] = {"scanner": name, **s, "clustered": cl, "rule": v,
                            "checks": lines}
        p20 = s["pooled"].get(H) or {}
        pl = s["plans"] or {}
        print(f"\n{tag} {name}: {v}", flush=True)
        print(f"   n={s['n_signals']}  @20d edge {p20.get('edge')}  "
              f"windows {s['windows'][H]}", flush=True)
        print(f"   10d {s['windows'][10]}  60d {s['windows'][60]}", flush=True)
        print(f"   clustered {cl}", flush=True)
        print(f"   plan n={pl.get('n_with_plan')} avg_R={pl.get('avg_R')} "
              f"tgt={pl.get('target_rate')} stop={pl.get('stop_rate')} "
              f"unfilled={pl.get('plans_unfilled')} "
              f"through_stop={pl.get('plans_fill_through_stop')}", flush=True)
        print("\n".join(lines), flush=True)

    out["verdict"] = out["arms"]["P"]["rule"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nVERDICT (P, the scanner that votes): {out['verdict']}\nwritten {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
