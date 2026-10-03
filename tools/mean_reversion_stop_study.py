#!/usr/bin/env python3
"""mean_reversion_stop_study.py — settle the Connors contradiction (B-8).

Two sources, one setup, opposite rules:

  * [[strategies/Quantified-MA-Mean-Reversion]] uses **NO STOP**, and says why —
    its own backtests found that stops removed the edge.
  * [[sources/ForexTester-Mean-Reversion-Guide]] makes **1-2 ATR stops
    mandatory**.

And the desk has already taken a side without measuring it.
`scanner_templates.scan_mean_reversion` ships `stop = session_low x 0.995` with
`time_stop: 10`. That is the ForexTester answer, adopted by inheritance. This
scores all three policies on the same signals.

══ THE METRIC, AND WHY IT IS NOT R ═════════════════════════════════════════════

`backtest._simulate_plan` reports **R-multiples**, and R is the one metric that
CANNOT be used here. R normalises by `entry - stop`, so the stop is in the
denominator: widening the stop shrinks every R mechanically, and the "no stop"
arm has no R at all. Comparing R across stop policies compares different units
and would report a tighter stop as better by construction.

So the metric is **realised return in per cent** on the same trade, with the same
entry, the same target and the same time stop. The only thing that varies is
where (or whether) the trade is cut.

══ WHAT IS HELD FIXED ══════════════════════════════════════════════════════════

Entry at the next bar's open, the scanner's own SMA20 target, the scanner's own
`time_stop` of 10 bars, and `COST_INDIAN` on every arm. A policy that exits more
often pays more cost, and that is a real difference between the policies rather
than a nuisance to net out.

══ PRE-REGISTERED DECISION RULE ════════════════════════════════════════════════

Primary: mean realised return per policy, over the same signal set.

  * If **NO STOP** beats both stopped arms, Connors is right on this universe and
    the shipped stop is costing the desk return. The consequence is NOT to remove
    the stop silently: it is to record the finding and put the number where the
    scanner's plan is rendered.
  * If **2-ATR** beats NO STOP, ForexTester is right and the shipped
    session-low stop should be compared against it directly.
  * If the arms are within noise of each other, the contradiction is **not
    settled by this data** and the shipped stop stays on the grounds that it
    bounds the loss -- which is a risk argument, not a return argument, and must
    be stated as such.

A difference is only called when the paired t-test on per-signal differences
clears p < 0.05. Paired, because every arm sees the SAME signals, and pairing
removes the signal-selection variance that would otherwise swamp the comparison.
It also removes most of the cross-sectional problem: two signals on different
names on the same date share the market's move, but that move lands on BOTH arms
of each pair, so it largely cancels in the difference the test actually reads.

**FLOOR added after the first run, and it can only ever weaken a claim.** The
desk's standing floor is 200 signals (the B-58 precedent, where 53 events against
that floor was reported as INCONCLUSIVE rather than as a null). This setup is
rare, so the floor is enforced here as a LABEL on the verdict rather than as a
veto: below 200 the result is reported as provisional and the write-up says so.
Adding a rule after seeing data is normally the thing pre-registration exists to
stop; it is admissible in this one direction because it can only downgrade a
finding, never promote one.

CLI:
  py -3 -X utf8 tools/mean_reversion_stop_study.py
  py -3 -X utf8 tools/mean_reversion_stop_study.py --symbols 20
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

import backtest as bt
import scanner_templates as sc

#: The registered name, pinned rather than matched by substring: "Mean Reversion"
#: alone also matches "VWAP Mean Reversion", which is a different setup.
SCANNER = "Mean Reversion (Connors RSI2)"

#: Bars of history the scanner needs before its first evaluation.
WARMUP = 220

#: ATR lookback for the ForexTester arm. Wilder's standard.
ATR_N = 14

#: The two ATR multiples the source names. 2.0 is the primary; 1.0 is reported
#: because the guide says "1-2" and picking only the wide end would be choosing
#: the arm most likely to behave like no stop at all.
ATR_MULTS = (1.0, 2.0)


def _atr(df: pd.DataFrame, n: int = ATR_N) -> np.ndarray:
    """Wilder's ATR as a numpy array aligned to df's rows."""
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    prev = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    out = np.full(len(tr), np.nan)
    if len(tr) < n:
        return out
    out[n - 1] = tr[:n].mean()
    for i in range(n, len(tr)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def _run_one(df: pd.DataFrame, entry_idx: int, entry: float,
             stop: float | None, target: float, time_stop: int,
             cm) -> dict:
    """Walk one trade forward under one stop policy. Returns realised %.

    `stop=None` is the Connors arm: the trade runs to the target or to the time
    stop, whichever comes first, and nothing cuts it in between. That arm is the
    reason this cannot reuse `_simulate_plan`, which refuses a non-positive risk.

    Conservative tie-break, inherited from the shared simulator: when one bar's
    range spans both the stop and the target, the stop is assumed to have filled
    first. Never credit a win that daily bars cannot prove came first.
    """
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    close = df["close"].to_numpy(float)
    end = min(len(df) - 1, entry_idx + time_stop)
    for i in range(entry_idx, end + 1):
        if stop is not None and low[i] <= stop:
            px = stop
            return {"outcome": "stop", "pct": (px / entry - 1) * 100
                    - cm.round_trip_pct(entry, px), "bars": i - entry_idx}
        if high[i] >= target:
            px = target
            return {"outcome": "target", "pct": (px / entry - 1) * 100
                    - cm.round_trip_pct(entry, px), "bars": i - entry_idx}
    px = close[end]
    return {"outcome": "time", "pct": (px / entry - 1) * 100
            - cm.round_trip_pct(entry, px), "bars": end - entry_idx}


def collect(symbols: list[str], fetch_fn, stride: int = 1) -> list[dict]:
    """Replay `scan_mean_reversion` and simulate every arm on each signal.

    One pass, so every arm sees exactly the same signals — which is what makes
    the comparison paired.
    """
    spec = sc.SCANNERS.get(SCANNER)
    if spec is None:
        raise RuntimeError(f"scanner {SCANNER!r} is not registered")
    fn = spec["fn"]
    cm = bt.COST_INDIAN

    rows: list[dict] = []
    for sym in symbols:
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        df = df.dropna(subset=["high", "low", "close", "volume"]).reset_index(drop=True)
        if len(df) < WARMUP + 40 or "open" not in df.columns:
            continue
        atr = _atr(df)
        openp = df["open"].to_numpy(float)
        last = len(df) - 15
        t = WARMUP
        while t < last:
            if stride > 1 and (t - WARMUP) % stride != 0:
                t += 1
                continue
            try:
                hit = fn(df.iloc[:t + 1])
            except Exception:
                hit = None
            if not hit:
                t += 1
                continue
            entry_idx = t + 1
            entry = float(openp[entry_idx])
            tgt = bt._to_float(hit.get("target"))
            shipped = bt._to_float(hit.get("stop"))
            ts = int(hit.get("time_stop") or 10)
            a = atr[t]
            if not (entry > 0) or tgt is None or not np.isfinite(a) or a <= 0:
                t += 1
                continue
            rec = {"symbol": sym, "i": t, "entry": entry, "atr": float(a)}
            rec["none"] = _run_one(df, entry_idx, entry, None, tgt, ts, cm)
            if shipped is not None and shipped < entry:
                rec["shipped"] = _run_one(df, entry_idx, entry, shipped, tgt, ts, cm)
            for m in ATR_MULTS:
                rec[f"atr{m:g}"] = _run_one(df, entry_idx, entry,
                                            entry - m * float(a), tgt, ts, cm)
            rows.append(rec)
            # Skip past the trade so overlapping entries on one name are not
            # counted as independent signals.
            t += ts + 1
    return rows


ARMS = ["none", "shipped", "atr1", "atr2"]
LABELS = {"none": "NO STOP (Connors)", "shipped": "session low x0.995 (shipped)",
          "atr1": "1-ATR (ForexTester)", "atr2": "2-ATR (ForexTester)"}


def summarise(rows: list[dict]) -> dict:
    out = {"n": len(rows), "arms": {}, "paired": {}}
    for arm in ARMS:
        vals = [r[arm]["pct"] for r in rows if arm in r]
        if not vals:
            continue
        outcomes = [r[arm]["outcome"] for r in rows if arm in r]
        out["arms"][arm] = {
            "n": len(vals), "mean": float(np.mean(vals)),
            "median": float(np.median(vals)),
            "win": 100.0 * sum(v > 0 for v in vals) / len(vals),
            "stopped": 100.0 * outcomes.count("stop") / len(outcomes),
            "target": 100.0 * outcomes.count("target") / len(outcomes),
            "timed": 100.0 * outcomes.count("time") / len(outcomes),
        }
    for arm in ARMS:
        if arm == "none" or arm not in out["arms"]:
            continue
        pairs = [(r["none"]["pct"], r[arm]["pct"]) for r in rows if arm in r]
        d = np.array([b - a for a, b in pairs], float)
        if len(d) < 10:
            continue
        t, p = bt._ttest_1samp(d, 0.0)
        out["paired"][arm] = {"n": len(d), "diff": float(d.mean()),
                              "t": float(t), "p": float(p)}
    return out


#: The desk's standing signal floor (B-58 precedent). Below it a verdict is
#: labelled provisional rather than suppressed — see the module docstring.
FLOOR = 200


def verdict(s: dict) -> tuple[str, str]:
    """The pre-registered rule, applied mechanically."""
    arms = s["arms"]
    if "none" not in arms:
        return "NO DATA", "no signals collected"
    thin = (" [PROVISIONAL — {n} signals, below the desk's {f} floor]"
            .format(n=s["n"], f=FLOOR)) if s["n"] < FLOOR else ""
    sig = [(a, v) for a, v in s["paired"].items() if v["p"] < 0.05]
    if not sig:
        return ("NOT SETTLED" + thin,
                "no stop policy differs from NO STOP at p<0.05 — the "
                "contradiction is not resolved by this data, and the shipped "
                "stop stands on a RISK argument, not a return one")
    better = [(a, v) for a, v in sig if v["diff"] > 0]
    worse = [(a, v) for a, v in sig if v["diff"] < 0]
    if worse and not better:
        a, v = min(worse, key=lambda kv: kv[1]["diff"])
        return ("CONNORS" + thin,
                f"stops COST return — worst is {LABELS[a]} at "
                f"{v['diff']:+.2f}pp (p={v['p']:.3f})")
    if better and not worse:
        a, v = max(better, key=lambda kv: kv[1]["diff"])
        return ("FOREXTESTER" + thin,
                f"{LABELS[a]} beats NO STOP by {v['diff']:+.2f}pp "
                f"(p={v['p']:.3f})")
    return ("MIXED" + thin,
            "stop policies differ from NO STOP in both directions")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(description="B-8 · mean-reversion stop policy")
    ap.add_argument("--symbols", type=int, default=50)
    ap.add_argument("--universe", default="liquid50",
                    help="liquid50 (the locked harness basket) or nifty500")
    ap.add_argument("--stride", type=int, default=1)
    a = ap.parse_args()

    import screener_pipeline as sp
    if a.universe == "nifty500":
        import nse_universe as nu
        syms = list(nu.symbols("nifty500"))[:a.symbols]
    else:
        syms = bt.LIQUID_50[:a.symbols]

    # Same fetch the shared harness uses. `days` is BARS, not calendar days --
    # 5000 reaches ~20 years, twice the harness default, because this setup is
    # rare and the first run returned only 73 signals.
    # The signal set is the one `backtest.py` would produce on the same names.
    def fetch(sym):
        return sp.fetch_ohlcv(sym, days=5000)

    print(f"Replaying the mean-reversion scanner over {len(syms)} names…")
    rows = collect(syms, fetch, stride=a.stride)
    s = summarise(rows)
    print(f"\n{s['n']} signals, non-overlapping per name.\n")

    print(f"{'policy':<30} {'n':>6} {'mean %':>8} {'med %':>8} {'win%':>6} "
          f"{'stop%':>6} {'tgt%':>6} {'time%':>6}")
    for arm in ARMS:
        v = s["arms"].get(arm)
        if not v:
            continue
        print(f"{LABELS[arm]:<30} {v['n']:>6} {v['mean']:>+8.2f} "
              f"{v['median']:>+8.2f} {v['win']:>6.1f} {v['stopped']:>6.1f} "
              f"{v['target']:>6.1f} {v['timed']:>6.1f}")

    print("\nPaired against NO STOP (same signals, so the pairing removes "
          "signal-selection variance):")
    for arm, v in s["paired"].items():
        print(f"  {LABELS[arm]:<30} {v['diff']:>+7.2f}pp   t={v['t']:>6.2f}  "
              f"p={v['p']:.4f}  n={v['n']}")

    vd, why = verdict(s)
    print(f"\nVERDICT (pre-registered): {vd}\n  {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
