#!/usr/bin/env python3
"""harmonic_tier_recheck.py — B-132r: B-129r's promotion check, re-run with the
AB=CD plan stop B-132 shipped (D - 2 x ATR14).

    py -3 -X utf8 tools/harmonic_tier_recheck.py      # writes cache/harmonic_tier_recheck.json

PRE-REGISTRATION: trading-wiki/wiki/analyses/ABCD-Stop-Study.md, section "B-132r",
written 2026-10-14 before this file was first run. In short:

  * R0 reproduction gate exactly as B-129r (XABCD-only, LIQUID_50, signal_mode
    "all", fill "assumed"); if it fails the panel is not read.
  * Panel: nifty500 first 300 names (B-129r's; B-132 chose the stop on 301-500),
    1500 days, COST_INDIAN, fresh signals, next-open fills, 3 windows.
  * Arm P only — the registered scanner as it votes today, AB=CD plans on the
    new stop. B-129r's five conditions via its own decide(), unchanged.
  * Plan % of entry (R x risk / entry) is descriptive, outside the rule.
  * Output is a RECOMMENDATION. opportunity_hub tiers are not touched.

Everything that decides is imported from harmonic_bull_remeasure, not copied, so
the rule cannot drift from the one pre-registered on 2026-10-05.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

import backtest as bt
import harmonic_bull_remeasure as hb   # registers the arms and the shared memo
import scanner_templates as sc

OUT = Path(__file__).resolve().parent / "cache" / "harmonic_tier_recheck.json"
B129R_P = {"avg_R": -0.176, "windows20": [0.27, -0.03, 1.22], "rule": "STAYS WEAK"}


def plan_pct(trades: list[dict]) -> dict[str, Any]:
    """Descriptive plan read in % of entry, as B-132 measured it."""
    pcts = [float(t["r"]) * abs(float(t["entry_px"]) - float(t["stop"]))
            / float(t["entry_px"]) * 100.0 for t in trades]
    n = len(trades)
    outc = [t.get("outcome") for t in trades]
    return {"n_trades": n,
            "mean_plan_pct": round(float(np.mean(pcts)), 3) if pcts else None,
            "target_rate": round(outc.count("target") / n, 3) if n else None,
            "stop_rate": round(outc.count("stop") / n, 3) if n else None,
            "time_rate": round((outc.count("time") + outc.count("open")) / n, 3) if n else None}


def main() -> int:
    import nse_universe as nu
    import screener_pipeline as sp
    assert sc.ABCD_STOP_ATR == 2.0, "the stop under test is B-132's D - 2 x ATR14"
    cache: dict = {}

    def fetch(s):
        if s not in cache:
            try:
                cache[s] = sp.fetch_ohlcv(s, days=hb.DAYS)
            except Exception:
                cache[s] = None
        return cache[s]

    out: dict[str, Any] = {"preregistered": "2026-10-14", "horizon": hb.H,
                           "abcd_stop_atr": sc.ABCD_STOP_ATR, "b129r_P": B129R_P}

    # ── R0: B-129r's reproduction gate, unchanged ───────────────────────────
    r0 = bt.walk_forward_scanner(hb.ARMS["PX"], list(bt.LIQUID_50), fetch,
                                 n_windows=hb.N_WINDOWS, cost_model=bt.COST_INDIAN,
                                 signal_mode="all", fill_model="assumed")
    s0 = hb.summarise(r0)
    n0 = (s0["pooled"].get(hb.H) or {}).get("n", 0)
    e0 = (s0["pooled"].get(hb.H) or {}).get("edge")
    ok0 = (abs(n0 - hb.R0_N) <= hb.R0_N_TOL * hb.R0_N
           and e0 is not None and abs(e0 - hb.R0_EDGE) <= hb.R0_EDGE_TOL)
    out["R0"] = {"n20": n0, "edge20": e0, "windows20": s0["windows"][hb.H], "pass": ok0}
    print(f"R0 reproduction: n={n0} (B-129 {hb.R0_N}), @20d {e0} (B-129 +{hb.R0_EDGE}) "
          f"-> {'PASS' if ok0 else 'FAIL'}", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not ok0:
        out["verdict"] = "R0 FAILED - not read"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print(f"\nR0 failed; panel NOT run. written {OUT}")
        return 1

    # ── Panel: arm P on B-129r's 300 names ──────────────────────────────────
    syms = list(nu.symbols("nifty500"))[:hb.N_SYMBOLS]
    common = dict(cost_model=bt.COST_INDIAN, signal_mode="fresh", fill_model="market")
    name = hb.ARMS["P"]
    wf = bt.walk_forward_scanner(name, syms, fetch, n_windows=hb.N_WINDOWS, **common)
    s = hb.summarise(wf)
    cl = hb.clustered(name, syms, fetch, **common)
    v, lines = hb.decide(s, cl)
    full = bt.backtest_scanner(name, syms, fetch, keep_trades=True, **common)
    desc = plan_pct(full.get("trades") or [])
    out.update({"symbols_requested": len(syms), "P": {**s, "clustered": cl, "rule": v,
                "checks": lines, "plan_pct_descriptive": desc}})
    out["recommendation"] = v

    p20 = s["pooled"].get(hb.H) or {}
    pl = s["plans"] or {}
    print(f"\nP {name}: {v}", flush=True)
    print(f"   n={s['n_signals']}  @20d edge {p20.get('edge')}  windows {s['windows'][hb.H]}")
    print(f"   10d {s['windows'][10]}  60d {s['windows'][60]}")
    print(f"   clustered {cl}")
    print(f"   plan n={pl.get('n_with_plan')} avg_R={pl.get('avg_R')} (B-129r {B129R_P['avg_R']}) "
          f"tgt={pl.get('target_rate')} stop={pl.get('stop_rate')} "
          f"unfilled={pl.get('plans_unfilled')} through_stop={pl.get('plans_fill_through_stop')}")
    print(f"   descriptive plan % {desc}")
    print("\n".join(lines))
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nRECOMMENDATION (owner decides the tier): {v}\nwritten {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
