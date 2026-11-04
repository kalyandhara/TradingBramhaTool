"""qullamaggie_breakout_retest.py — B-147b: confirmatory re-test of the Breakout lead.

    py -3 tools/qullamaggie_breakout_retest.py       # full run, writes cache/qm147b_result.json

PRE-REGISTRATION: trading-wiki/wiki/analyses/Qullamaggie-Edge-Study.md, section
"B-147b", written 2026-10-14 before this file touched the data. In short:

  * Out-of-sample universe: names with a daily file in multibagger_bars /
    cardinality / svp_bars and NO file in cardinality_deep (B-147 never saw them);
    the longest file per name; funds excluded; B-147's `_load`.
  * Signals: B-147's `_signals` unchanged (Breakout only). Entry = signal close.
  * (a) DECISIVE: B-147's percent plan (stop = signal low, trail on the first close
    below SMA10, max 60 sessions, 29 bps) vs the same plan on ordinary bars with a
    stop-matched stop = entry - k * ATR14. k = median (close - low) / ATR14 over the
    IN-SAMPLE (cardinality_deep) breakout signals — geometry only, no outcomes.
    Paired by symbol, one-sample t, two-sided, alpha 0.025.
  * (b) secondary: net 60d forward return paired by symbol vs the all-bar 60d mean,
    alpha 0.025; reported beside the verdict, does not change it.
  * Descriptive: bootstrap CI, the OOS signals' own k, 60 bps costs, a trend-matched
    baseline (close > SMA10 > SMA20), and the in-sample re-read of (a).

B-147's script is imported, never edited: its loader, signal code and plan are reused
as-is. `_plan_at` below is the same plan with the stop passed in; with stop = the
signal-day low it reproduces `qes._plan` exactly (test_qullamaggie_breakout_retest.py).
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qullamaggie_edge_study as qes  # noqa: E402

CACHE = HERE / "cache"
IN_SAMPLE = CACHE / "cardinality_deep"
OOS_DIRS = ("multibagger_bars", "cardinality", "svp_bars")   # tie-break order
OUT = CACHE / "qm147b_result.json"

ALPHA = 0.05 / 2
MIN_SYMBOLS = 20
COST = qes.COST
COST_HI = 0.0060              # descriptive: small-cap realism
H60 = 60
ATR_N = 14
BASE_PER_SYM = 100
SEED = 1472
BOOT = 2000


def _is_fund(sym: str) -> bool:
    return sym in qes.SKIP or sym.endswith("BEES") or "ETF" in sym


def oos_files() -> list[Path]:
    """One file per unseen name: the most bars, ties broken by OOS_DIRS order."""
    seen = {f.stem.replace("_1d", "") for f in IN_SAMPLE.glob("*_1d.json")}
    best: dict[str, tuple[int, int, Path]] = {}
    for rank, d in enumerate(OOS_DIRS):
        for f in sorted((CACHE / d).glob("*_1d.json")):
            sym = f.stem.replace("_1d", "")
            if sym in seen or _is_fund(sym):
                continue
            n = len(json.loads(f.read_text(encoding="utf-8")).get("bars") or [])
            cur = best.get(sym)
            if cur is None or (n, -rank) > (cur[0], -cur[1]):
                best[sym] = (n, rank, f)
    return [best[s][2] for s in sorted(best)]


def in_sample_files() -> list[Path]:
    return [f for f in sorted(IN_SAMPLE.glob("*_1d.json"))
            if not _is_fund(f.stem.replace("_1d", ""))]


def _atr(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Simple 14-bar mean of true range ending on each bar (NaN until 14 TRs)."""
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    tr[0] = np.nan
    out = np.full(len(c), np.nan)
    cs = np.cumsum(np.nan_to_num(tr))
    out[ATR_N:] = (cs[ATR_N:] - cs[:-ATR_N]) / ATR_N
    return out


def _plan_at(h, l, c, sma10, t: int, stop: float, cost: float = COST) -> float | None:
    """B-147's plan with the stop given: percent return, net of `cost`."""
    entry = c[t]
    if not entry - stop > 0 or t + qes.PLAN_MAX >= len(c):
        return None
    exit_px = None
    for j in range(t + 1, t + qes.PLAN_MAX + 1):
        if l[j] <= stop:                       # stop first when both touch one day
            exit_px = stop
            break
        if c[j] < sma10[j]:
            exit_px = c[j]
            break
    if exit_px is None:
        exit_px = c[t + qes.PLAN_MAX]
    return exit_px / entry - 1 - cost


def _arrays(df):
    c, h, l = (df[x].to_numpy() for x in ("close", "high", "low"))
    sma10 = df["close"].rolling(10).mean().to_numpy()
    sma20 = df["close"].rolling(20).mean().to_numpy()
    return c, h, l, sma10, sma20, _atr(h, l, c)


def signal_k(files: list[Path]) -> tuple[float | None, int, dict]:
    """Median (close - low) / ATR14 on breakout signal days. Geometry only."""
    ks, sigs = [], {}
    for f in files:
        df = qes._load(f)
        if df is None:
            continue
        c, h, l, _, _, atr = _arrays(df)
        ts = qes._signals(df)["breakout"]
        sigs[f.stem.replace("_1d", "")] = (df, ts)
        ks += [(c[t] - l[t]) / atr[t] for t in ts if atr[t] > 0]
    return (float(np.median(ks)) if ks else None), len(ks), sigs


def _paired(sig: dict[str, list[float]], base: dict[str, list[float]]) -> dict:
    diffs = [np.mean(sig[s]) - np.mean(base[s]) for s in sorted(sig) if sig[s] and base.get(s)]
    if len(diffs) < 2:
        return {"n_sym": len(diffs)}
    t, p = sp_stats.ttest_1samp(diffs, 0.0)
    return {"n_sym": len(diffs), "mean_diff_pct": round(float(np.mean(diffs)) * 100, 3),
            "median_diff_pct": round(float(np.median(diffs)) * 100, 3),
            "pos_share": round(float(np.mean(np.array(diffs) > 0)), 3),
            "t": round(float(t), 3), "p": float(p)}


def _boot(sig: dict[str, list[float]], base: dict[str, list[float]]) -> list[float] | None:
    syms = [s for s in sorted(sig) if sig[s] and base.get(s)]
    if len(syms) < 2:
        return None
    rng = np.random.default_rng(SEED)
    out = []
    for _ in range(BOOT):
        pick = rng.choice(syms, size=len(syms), replace=True)
        out.append(np.concatenate([sig[s] for s in pick]).mean()
                   - np.concatenate([base[s] for s in pick]).mean())
    return [round(float(np.percentile(out, 2.5)) * 100, 3), round(float(np.percentile(out, 97.5)) * 100, 3)]


def _pool_mean(d: dict[str, list[float]]) -> float | None:
    xs = [x for v in d.values() for x in v]
    return round(float(np.mean(xs)) * 100, 3) if xs else None


def measure(sigs: dict, k: float) -> dict:
    """(a), (b) and the descriptive arms over one universe of pre-computed signals."""
    rng = np.random.default_rng(SEED)
    arms = {a: ({}, {}) for a in ("a", "a_cost60", "a_trend")}
    fwd_sig, fwd_base = {}, {}
    n_sig = 0
    for sym in sorted(sigs):
        df, ts = sigs[sym]
        c, h, l, sma10, sma20, atr = _arrays(df)
        idx = np.arange(qes.WARMUP, len(c) - qes.PLAN_MAX)
        idx = idx[atr[idx] > 0]
        sample = (np.sort(rng.choice(idx, size=min(BASE_PER_SYM, len(idx)), replace=False))
                  if len(idx) else np.array([], dtype=int))
        trend = idx[(c[idx] > sma10[idx]) & (sma10[idx] > sma20[idx])]
        tsample = (np.sort(rng.choice(trend, size=min(BASE_PER_SYM, len(trend)), replace=False))
                   if len(trend) else np.array([], dtype=int))

        def base(ix, cost):
            return [x for x in (_plan_at(h, l, c, sma10, int(t), c[t] - k * atr[t], cost) for t in ix)
                    if x is not None]

        def sig(cost):
            return [x for x in (_plan_at(h, l, c, sma10, t, l[t], cost) for t in ts) if x is not None]

        arms["a"][1][sym] = base(sample, COST)
        arms["a_cost60"][1][sym] = base(sample, COST_HI)
        arms["a_trend"][1][sym] = base(tsample, COST)
        if ts:
            n_sig += len(ts)
            arms["a"][0][sym] = sig(COST)
            arms["a_cost60"][0][sym] = sig(COST_HI)
            arms["a_trend"][0][sym] = arms["a"][0][sym]
            f = [r for r in (qes._fwd(c, t, H60) for t in ts) if r is not None]
            if f and len(c) > qes.WARMUP + H60:
                fwd_sig[sym] = f
                fwd_base[sym] = [float(np.mean(c[qes.WARMUP + H60:] / c[qes.WARMUP:len(c) - H60] - 1) - COST)]
    out = {"n_symbols": len(sigs), "n_signals": n_sig}
    for a, (s, b) in arms.items():
        s = {x: v for x, v in s.items() if v}
        out[a] = {**_paired(s, b), "signal_mean_pct": _pool_mean(s),
                  "baseline_mean_pct": _pool_mean({x: b[x] for x in b}),
                  "n_trades": sum(map(len, s.values())), "boot_ci95_pct": _boot(s, b)}
    out["b_fwd60"] = _paired(fwd_sig, fwd_base)
    return out


def verdict(a: dict) -> str:
    if a.get("n_sym", 0) < MIN_SYMBOLS:
        return "INCONCLUSIVE"
    if a["p"] < ALPHA:
        return "PASS" if a["mean_diff_pct"] > 0 else "NEGATIVE"
    return "NULL"


def run() -> dict:
    t0 = time.time()
    k, n_k, is_sigs = signal_k(in_sample_files())
    print(f"  in-sample k = {k:.4f} from {n_k} breakout signals · {time.time() - t0:.0f}s", flush=True)
    oos = oos_files()
    k_oos, n_k_oos, oos_sigs = signal_k(oos)
    print(f"  OOS: {len(oos)} files, {len(oos_sigs)} usable · {time.time() - t0:.0f}s", flush=True)
    res_oos = measure(oos_sigs, k)
    res_is = measure(is_sigs, k)
    result = {
        "run": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "k_in_sample": round(k, 4), "k_in_sample_n": n_k,
        "k_oos_signals": round(k_oos, 4) if k_oos is not None else None, "k_oos_n": n_k_oos,
        "oos_files": len(oos),
        "oos_first_signal": min((str(df.index[t].date()) for df, ts in oos_sigs.values() for t in ts), default=None),
        "alpha": ALPHA,
        "verdict": verdict(res_oos["a"]),
        "b_passes": bool(res_oos["b_fwd60"].get("p", 1) < ALPHA and res_oos["b_fwd60"].get("mean_diff_pct", 0) > 0),
        "oos": res_oos,
        "in_sample_reread": res_is,
        "elapsed_s": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    return result


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print(json.dumps(run(), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
