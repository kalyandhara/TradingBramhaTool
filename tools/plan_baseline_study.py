#!/usr/bin/env python3
"""plan_baseline_study.py — B-183: does any scanner's PLAN beat a no-edge baseline?

    py -3 -X utf8 tools/plan_baseline_study.py      # writes cache/plan_baseline_study.json

PRE-REGISTRATION: trading-wiki/wiki/analyses/Plan-Odds-Baseline-Pre-Registration.md,
committed 2026-10-25 (082f73f) before any trade was scored. In short:

  * Harness: backtest_scanner, COST_INDIAN, signal_mode="fresh", fill_model="market",
    keep_trades=True, horizons unchanged (max 60), fixed exit.
  * Panel: nifty500[0:300], 1500 calendar days.
  * Per trade: d = r - exp_r, exp_r from plan_baseline.null_plan_odds (block
    bootstrap of the stock's own pre-entry bars, same plan, same cost model).
  * Statistic: per-symbol mean d, one-sample t across symbols; Holm-Bonferroni
    across scanners that clear the floors, family alpha 0.05, two-sided.
  * Floors: >= 30 symbols and >= 100 baselined trades, else THIN.
  * Stability: the sign of mean d agrees in >= 2 of 3 entry-date thirds.
  * Gate: the `_B183 Placebo` arm (every 5th bar, stop 1 ATR, target 2 ATR, time
    stop 10) must have |mean d| <= 0.05R or p >= 0.05, else NO verdict is written.
    Amendment 2 (2026-11-03): the engine's pool is drift-free, and the gate is read
    on the disjoint panel nifty500[300:500] first; the main panel's placebo is
    context only.
  * Verdicts: BEATS / BELOW / AT BASELINE / THIN. No tier or weight changes.
  * Prior: >= 80% AT BASELINE; none BEATS after Holm.

Scanners the plan census shows NEVER emit a plan (fired, 0 with a plan) are not
replayed: a plan is a property of the scanner (scanner_plans.py), so they would
contribute zero trades. Amendment recorded on the pre-registration page before
the run.
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

import backtest as bt
import plan_baseline as pb
import scanner_templates as sc

PANEL = (0, 300)
#: Amendment 2 (2026-11-03): the placebo gate is read on a panel the zero-drift
#: diagnosis never touched, BEFORE any scanner result.
GATE_PANEL = (300, 500)
DAYS = 1500
MIN_SYMBOLS, MIN_TRADES = 30, 100
ALPHA = 0.05
PLACEBO_MAX_D = 0.05
NOISE_STOP = 0.60
PLACEBO = "_B183 Placebo"
HERE = Path(__file__).resolve().parent
OUT = HERE / "cache" / "plan_baseline_study.json"
#: The panel's frames, fetched once by main() and handed to the worker processes.
#: Written and read only by this script (same machine, same run), never fetched
#: from elsewhere, which is why pickle is acceptable here.
FRAMES = HERE / "cache" / "plan_baseline_frames.pkl"
GATE_FRAMES = HERE / "cache" / "plan_baseline_gate_frames.pkl"
CENSUS = HERE / "scanner_plan_coverage.json"
COMMON = dict(cost_model=bt.COST_INDIAN, signal_mode="fresh", fill_model="market",
              keep_trades=True)


# ── The placebo arm ──────────────────────────────────────────────────────────
def _placebo(df: pd.DataFrame) -> dict | None:
    """Fires on every 5th bar; entry = last close (filled next open by the
    harness), stop 1 x ATR14 below, target 2 x ATR14 above, time stop 10."""
    if len(df) % 5 != 0:
        return None
    atr = float(sc._atr_series(df, 14).iloc[-1])
    if not atr > 0:
        return None
    entry = float(df["close"].iloc[-1])
    return {"pattern_type": "B-183 placebo", "entry": entry, "stop": entry - atr,
            "target": entry + 2.0 * atr, "time_stop": 10, "score_base": 0,
            "reasons": ["placebo"]}


def _register_placebo() -> None:
    """From main()/workers only — registered at import, it would leak into
    test_scanner_plans' census check (the B-132 lesson)."""
    sc.SCANNERS[PLACEBO] = {"fn": _placebo, "description": "B-183 placebo arm",
                            "category": "Entry"}


# ── Data ─────────────────────────────────────────────────────────────────────
def _harness_frame(df: pd.DataFrame) -> pd.DataFrame:
    """The frame backtest_scanner indexes trades into: NaN rows dropped, reset."""
    return df.dropna(subset=["high", "low", "close", "volume"]).reset_index(drop=True)


def planning_scanners(names, census: dict) -> list[str]:
    """Registered, non-private scanners minus those the census saw fire without
    ever carrying a plan. UNSEEN scanners (never fired in the census) stay in."""
    s = census.get("scanners", census)
    out = []
    for n in names:
        if n.startswith("_"):
            continue
        c = s.get(n) or {}
        if c.get("fired", 0) > 0 and c.get("with_plan", 0) == 0:
            continue
        out.append(n)
    return out


# ── Per-trade baseline ───────────────────────────────────────────────────────
def attach_baseline(trades: list[dict], frames: dict[str, pd.DataFrame]) -> list[dict]:
    for tr in trades:
        df = frames.get(tr["symbol"])
        nb = None
        if df is not None:
            nb = pb.null_plan_odds(
                _harness_frame(df), tr["entry_idx"], tr["entry_px"], tr["stop"],
                tr["target"], tr["max_bars"], tr.get("time_stop"), side=tr["side"],
                cost_model=bt.COST_INDIAN, seed=pb.trade_seed(tr["symbol"], tr["entry_idx"]))
        tr["exp_r"] = None if nb is None else nb["exp_r"]
        tr["p_target"] = None if nb is None else nb["p_target"]
        tr["p_stop"] = None if nb is None else nb["p_stop"]
    return trades


# ── Statistics ───────────────────────────────────────────────────────────────
def _ttest(xs) -> tuple[float | None, float | None]:
    a = np.asarray(list(xs), dtype=float)
    if len(a) < 2 or float(a.std(ddof=1)) == 0:
        return None, None
    t = float(a.mean()) / (float(a.std(ddof=1)) / math.sqrt(len(a)))
    from scipy import stats
    return t, float(2 * stats.t.sf(abs(t), df=len(a) - 1))


def _d(t: dict, d_cap: float | None) -> float:
    d = float(t["r"]) - float(t["exp_r"])
    return d if d_cap is None else max(-d_cap, min(d_cap, d))


def scanner_stats(trades: list[dict], d_cap: float | None = None) -> dict:
    """`d_cap` (B-183c) winsorizes each trade's d to [-d_cap, +d_cap] before the
    symbol means, the thirds and the t-test; None is B-183's raw d."""
    based = [t for t in trades if t.get("exp_r") is not None]
    by: dict[str, list[float]] = {}
    for t in based:
        by.setdefault(t["symbol"], []).append(_d(t, d_cap))
    means = [float(np.mean(v)) for v in by.values()]
    t_, p_ = _ttest(means)
    ordered = sorted(based, key=lambda t: pd.Timestamp(t.get("entry_date") or 0))
    thirds = [round(float(np.mean([_d(t, d_cap) for t in part])), 4)
              if len(part) else None for part in np.array_split(np.array(ordered, dtype=object), 3)]
    n = len(based)
    return {
        "n_trades": len(trades), "n_unbaselined": len(trades) - n, "n_symbols": len(by),
        "mean_d": float(np.mean(means)) if means else None,     # unrounded: the verdict reads it
        "t": None if t_ is None else round(t_, 3), "p": p_,
        "thirds": thirds,
        "mean_r": round(float(np.mean([t["r"] for t in based])), 4) if n else None,
        "mean_exp_r": round(float(np.mean([t["exp_r"] for t in based])), 4) if n else None,
        "realised_target_rate": round(sum(t["outcome"] == "target" for t in based) / n, 4) if n else None,
        "mean_p_target": round(float(np.mean([t["p_target"] for t in based])), 4) if n else None,
        "noise_stop_share": round(sum(t["p_stop"] >= NOISE_STOP for t in based) / n, 4) if n else None,
    }


def holm_adjusted(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, run, out = len(items), 0.0, {}
    for k, (name, p) in enumerate(items):
        run = max(run, min(1.0, (m - k) * p))
        out[name] = run
    return out


def holm(pvals: dict[str, float], alpha: float = ALPHA) -> dict[str, bool]:
    adj = holm_adjusted(pvals)
    return {k: adj[k] < alpha for k in pvals}


def verdict(stats: dict, significant: bool) -> str:
    baselined = stats["n_trades"] - stats.get("n_unbaselined", 0)
    if stats["n_symbols"] < MIN_SYMBOLS or baselined < MIN_TRADES:
        return "THIN"
    md = stats["mean_d"]
    agree = sum(1 for x in stats["thirds"] if x is not None and md is not None
                and np.sign(x) == np.sign(md) and x != 0)
    if significant and agree >= 2 and md is not None and md != 0:
        return "BEATS BASELINE" if md > 0 else "BELOW BASELINE"
    return "AT BASELINE"


def placebo_passes_strict(stats: dict) -> bool:
    """B-183c: |mean d| <= PLACEBO_MAX_D, with no p-value escape."""
    md = stats.get("mean_d")
    return md is not None and abs(md) <= PLACEBO_MAX_D


def within_placebo_noise(stats: dict, placebo: dict) -> bool:
    """B-183c label: |mean d| within 2x the main panel placebo's |mean d|."""
    md, pd_ = stats.get("mean_d"), placebo.get("mean_d")
    return md is not None and pd_ is not None and abs(md) <= 2 * abs(pd_)


def placebo_passes(stats: dict) -> bool:
    md, p = stats.get("mean_d"), stats.get("p")
    return (md is not None and abs(md) <= PLACEBO_MAX_D) or (p is not None and p >= ALPHA)


# ── Workers ──────────────────────────────────────────────────────────────────
_FR: dict = {}
_DCAP: float | None = None


def _init(path: str, d_cap: float | None = None) -> None:
    global _FR, _DCAP
    with open(path, "rb") as fh:
        _FR = pickle.load(fh)
    _DCAP = d_cap
    _register_placebo()


def _run_one(name: str) -> dict:
    t0 = time.time()
    syms = list(_FR)
    try:
        res = bt.backtest_scanner(name, syms, lambda s: _FR.get(s), **COMMON)
    except Exception as e:                      # noqa: BLE001 — recorded, not hidden
        return {"name": name, "error": f"{type(e).__name__}: {e}"}
    trades = attach_baseline(res.get("trades") or [], _FR)
    st = scanner_stats(trades, _DCAP)
    st.update(name=name, n_signals=res.get("n_signals"), elapsed_s=round(time.time() - t0, 1))
    return st


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--procs", type=int, default=7)
    ap.add_argument("--d-cap", type=float, default=None,
                    help="B-183c: winsorize per-trade d at +/- this many R")
    ap.add_argument("--strict-gate", action="store_true",
                    help="B-183c: placebo gate |mean d| <= 0.05R with no p escape")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    gate_ok = placebo_passes_strict if a.strict_gate else placebo_passes
    import nse_universe as nu
    import screener_pipeline as sp
    universe = list(nu.symbols("nifty500"))

    def _load(lo: int, hi: int, path: Path) -> dict:
        frames = {}
        for s in universe[lo:hi]:
            try:
                df = sp.fetch_ohlcv(s, days=DAYS)
            except Exception:
                df = None
            if df is not None and not df.empty:
                frames[s] = df
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump(frames, fh)
        print(f"panel [{lo}:{hi}]: {len(frames)} of {hi - lo} symbols loaded", flush=True)
        return frames

    gate_frames = _load(*GATE_PANEL, GATE_FRAMES)
    with Pool(a.procs, initializer=_init, initargs=(str(GATE_FRAMES), a.d_cap)) as pool:
        gate = pool.apply(_run_one, (PLACEBO,))
    print(f"placebo gate [{GATE_PANEL[0]}:{GATE_PANEL[1]}]: {gate}", flush=True)
    frames = _load(*PANEL, FRAMES)

    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    names = planning_scanners(list(sc.SCANNERS), census)
    out: dict = {"preregistered": "2026-10-25", "pre_registration_commit": "082f73f",
                 "amendment": "2 (2026-11-03): zero-drift pool; gate on nifty500[300:500]",
                 "b183c": {"d_cap": a.d_cap, "strict_gate": a.strict_gate},
                 "gate_panel": f"nifty500[{GATE_PANEL[0]}:{GATE_PANEL[1]}]",
                 "gate_symbols_loaded": len(gate_frames), "placebo_gate": gate,
                 "panel": f"nifty500[{PANEL[0]}:{PANEL[1]}]", "days": DAYS,
                 "symbols_loaded": len(frames), "harness": {k: str(v) for k, v in COMMON.items()},
                 "engine": {"replays": pb.REPLAYS, "block": pb.BLOCK, "lookback": pb.LOOKBACK,
                            "min_pool": pb.MIN_POOL, "seed": pb.SEED},
                 "skipped_never_plan": sorted(set(n for n in sc.SCANNERS if not n.startswith("_"))
                                              - set(names))}
    if "error" in gate or not gate_ok(gate):
        out["placebo_failed"] = True
        a.out.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("PLACEBO GATE FAILED -- the baseline is miscalibrated; no scanner verdict written.")
        return 1
    out["placebo_failed"] = False
    with Pool(a.procs, initializer=_init, initargs=(str(FRAMES), a.d_cap)) as pool:
        plc = pool.apply(_run_one, (PLACEBO,))
        out["placebo"] = plc                    # main-panel placebo: context only
        print(f"placebo (main panel, context): {plc}", flush=True)
        rows = []
        for st in pool.imap_unordered(_run_one, names):
            rows.append(st)
            print(f"  {st.get('name')}: n={st.get('n_trades')} sym={st.get('n_symbols')} "
                  f"d={st.get('mean_d')} p={st.get('p')} {st.get('error', '')}", flush=True)

    ok = {r["name"]: r for r in rows if "error" not in r and r.get("n_trades")}
    floors = {n: r for n, r in ok.items()
              if r["n_symbols"] >= MIN_SYMBOLS and r["n_trades"] - r["n_unbaselined"] >= MIN_TRADES
              and r["p"] is not None}
    adj = holm_adjusted({n: r["p"] for n, r in floors.items()})
    for n, r in ok.items():
        r["holm_p"] = adj.get(n)
        r["verdict"] = verdict(r, n in adj and adj[n] < ALPHA)
        r["within_placebo_noise"] = within_placebo_noise(r, out["placebo"])
    out["scanners"] = dict(sorted(ok.items()))
    out["no_plans"] = sorted(r["name"] for r in rows if "error" not in r and not r.get("n_trades"))
    out["errors"] = {r["name"]: r["error"] for r in rows if "error" in r}
    counts: dict[str, int] = {}
    for r in ok.values():
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    out["verdict_counts"] = counts
    a.out.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"verdict_counts": counts}, indent=2))
    for n, r in sorted(ok.items(), key=lambda kv: kv[1]["verdict"]):
        print(f"{r['verdict']:15} {n:40} n={r['n_trades']:5} sym={r['n_symbols']:3} "
              f"d={r['mean_d']} holm={r['holm_p']} thirds={r['thirds']}"
              + ("  [within placebo noise]" if r["within_placebo_noise"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
