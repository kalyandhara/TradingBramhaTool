#!/usr/bin/env python3
"""sweep_plan_study.py — B-41p: is the STOP the reason the sweep edge does not convert?

B-41m measured Liquidity Sweep at +0.51% @20d (p=0.005) and +0.91% @60d (p=0.002)
net of costs, walk-forward sign-stable at 10/20/60d — and its shipped trade plan
returns **+0.06R after costs**, win 39.2%, target hit 549 times against stop 842.

The signal carries forward information and the plan throws it away. This asks
whether that is the STOP specifically, and it is written to make a flattering
answer hard to obtain.

══ PRE-REGISTRATION — written and committed before the first run ════════════

  THE ARMS (three, fixed; no others will be added after seeing results)

    A  SHIPPED     entry/stop/target exactly as scan_liquidity_sweep emits them.
                   The incumbent. Everything is measured against this.

    B  ATR STOP    identical to A except the stop is entry - 1.5 x ATR(14).
                   Rationale, a priori: the shipped stop sits below the sweep
                   wick, and a sweep wick's DEPTH is arbitrary — a violent sweep
                   gives a wide stop, a shallow one a tight stop — so risk per
                   trade varies with something unrelated to the thesis. ATR
                   normalises it. k=1.5 is the convention, chosen before running
                   and NOT swept.

    C  TIME ONLY   no stop, no target; exit at the close 20 bars after entry.
                   This is the arm that actually answers the question. The
                   forward-return study IS a time exit, so if C converts the edge
                   and A does not, the stop is the whole problem — with no
                   parameter to tune and nothing to overfit. 20d is fixed because
                   that is the horizon B-41m measured, not because it was chosen
                   from results.

  STATISTIC   mean R per trade, paired on identical signals (all arms see the
              same entries, so the comparison is within-signal).

  UNCERTAINTY block bootstrap resampling SYMBOLS with replacement, 2000 draws.
              Trades overlap in time and cluster within a name, so a plain t-test
              on 1400 trades would treat correlated outcomes as independent —
              the same error _rotation_p exists to avoid in gamma_regime_backtest.

  PASS BAR    an alternative beats SHIPPED by >= +0.15R AND its own mean R is
              positive AND the paired bootstrap CI for the difference excludes
              zero at Bonferroni-corrected 97.5% (two arms compared, so 0.05/2).
              Anything less is a null: the plan is not the problem, or not
              fixably so by this route.

  PRIOR       C beats A; B lands between them. Stated so it can be wrong: if B
              wins and C does not, this write-up says the prior was wrong rather
              than quietly reporting B.

  SCOPE       A pass licenses ONE thing: re-examining the shipped stop under a
              pre-registered follow-up. It does NOT promote the scanner to
              MEASURED_EDGE — that needs the new plan measured on its own
              walk-forward, not on the sample that selected it.

══ B-41w PRE-REGISTRATION — the follow-up B-41p's scope clause licensed ═════

B-41p showed arm C (time-only) beats the shipped plan by +0.564R. Its scope
clause allowed exactly one further pre-registered test, and this is it: **does
arm C hold up across time, or does it live in one period?**

That question is not answered by B-41p. Its bootstrap resamples SYMBOLS, so it
speaks to cross-sectional robustness and says nothing about whether the effect is
stable across eras. B-19's lesson is precisely that: 11 scanners showed positive
pooled 20d edge and every one was unstable across windows.

  TEST        split the trades CHRONOLOGICALLY into 3 equal windows (by trade
              date, not by symbol), and compute arm C's mean R and the C-minus-A
              improvement in each.

  PASS BAR    arm C mean R > 0 in ALL THREE windows AND the C-A improvement
              positive in all three. Sign consistency, matching the criterion
              `backtest.walk_forward_scanner` already uses, so this verdict is
              comparable to every other stability verdict on the desk.

  PRIOR       C is positive in all three but the MAGNITUDE is uneven, because
              B-41m's forward walk-forward had window 2 at +0.06% — near zero.
              If window 2 comes back negative in R terms, that is the honest
              answer and it downgrades B-41p from "the stop is the constraint" to
              "the stop is the constraint in two eras of three".

  SCOPE       A pass still does NOT promote the scanner. Arm C has uncapped
              downside; a tradeable plan needs a risk control that is not a stop,
              and that is a design question this test does not touch.

══ WHY NOT JUST SWEEP STOP MULTIPLES ════════════════════════════════════════
Because that finds a winner every time. With ~1400 trades and a dozen stop
settings, the best one clears p<0.05 by construction; the desk has already been
burned by a subgroup that looked real (B-34r4's drifting window carried the whole
of Hidden Treasures' apparent edge). Three arms with stated reasons, one pass bar,
one correction.

══ OUTCOME 2026-09-06 — C PASSES, B DOES NOT ════════════════════════════════

  4,854 trades · 50 symbols · 29bps · 2,000-draw symbol bootstrap

    A  SHIPPED     -0.059R   win 43.2%      —
    B  ATR STOP    -0.047R   win 50.8%   +0.012R  [-0.077, +0.102]  includes 0
    C  TIME ONLY   +0.504R   win 54.9%   +0.564R  [+0.337, +0.798]  EXCLUDES 0

  **It is not WHERE the stop is. It is that there is one.** Swapping the wick
  stop for an ATR-derived one moves the result by +0.012R with a CI straddling
  zero. Removing the stop turns -0.059R into +0.504R. The shipped stop is not
  badly placed — a 20-day hold on this signal cannot survive a stop of that
  magnitude at all, and the drawdown path is part of the edge. B-41m's -7.3%
  average MAE already implied it.

  The registered prior was "C beats A; B lands between". C did; B did not — it
  was indistinguishable from A. The wrong half is the informative half, because
  it rules out stop PLACEMENT as the lever.

  Arm C is B-41m's forward study expressed in R (buy next open, exit 20d close),
  so it is not independent evidence of profit. The new information is the
  comparison: same signal, same horizon, +0.50R unstopped vs -0.06R stopped.

  NOT a licence to trade C. Its downside is uncapped where the other arms lose at
  most 1R; a better mean with an unbounded tail is a different risk profile, not
  a better one. Per the scope clause above, this licenses one further
  pre-registered test and NOT promotion to MEASURED_EDGE.

CLI:
  py -3 tools/sweep_plan_study.py
  py -3 tools/sweep_plan_study.py --symbols RELIANCE TCS   # smoke test
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import backtest as bt
import scanner_templates as sc
import screener_pipeline as sp

HORIZON = 20          # bars, arm C's exit — B-41m's measured horizon
ATR_K = 1.5           # arm B's stop multiple, pre-registered
ATR_N = 14
COST_BPS = 29.0       # Indian delivery, matching B-41m's net numbers
N_BOOT = 2000
PASS_DELTA = 0.15     # R improvement required over SHIPPED
WARMUP = 60


def _simulate(df: pd.DataFrame, i: int, entry: float, stop: float | None,
              target: float | None, horizon: int) -> float | None:
    """R multiple for one trade, walked bar by bar from i+1. Causal.

    Stop is checked BEFORE target when a single bar spans both: intrabar order is
    unknowable from daily data, and assuming the good fill would inflate every
    arm that has a stop — including the two being promoted.
    """
    risk = None if stop is None else entry - stop
    if stop is not None and not (risk and risk > 0):
        return None
    hi, lo, cl = df["high"].values, df["low"].values, df["close"].values
    last = min(i + horizon, len(df) - 1)
    for t in range(i + 1, last + 1):
        if stop is not None and lo[t] <= stop:
            return -1.0
        if target is not None and hi[t] >= target:
            return (target - entry) / risk if risk else 0.0
    out = cl[last]
    if risk:
        return (out - entry) / risk
    # Arm C has no risk unit, so R is expressed against the SAME denominator the
    # other arms use (the shipped stop distance). Otherwise "R" would mean two
    # different things across the table and the comparison would be meaningless.
    return None


def collect(symbols: list[str]) -> pd.DataFrame:
    rows = []
    for si, sym in enumerate(symbols, 1):
        try:
            df = sp.fetch_ohlcv(sym, days=1500)
        except Exception:
            continue
        if df is None or len(df) < WARMUP + HORIZON + 5:
            continue
        dates = (df.index.astype(str).tolist() if not isinstance(df.index, pd.RangeIndex)
                 else [""] * len(df))
        df = df.reset_index(drop=True)
        atr = sc._atr_series(df, ATR_N)
        last_eval = len(df) - HORIZON - 2
        for i in range(WARMUP, last_eval + 1):
            hit = sc.scan_liquidity_sweep(df.iloc[:i + 1])
            if not hit:
                continue
            entry = hit.get("entry")
            stop = hit.get("stop")
            target = hit.get("target")
            if not all(isinstance(v, (int, float)) for v in (entry, stop, target)):
                continue
            a_risk = entry - stop
            if not (a_risk > 0):
                continue
            atr_v = float(atr.iloc[i]) if np.isfinite(atr.iloc[i]) else None
            if atr_v is None or atr_v <= 0:
                continue

            r_a = _simulate(df, i, entry, stop, target, HORIZON)
            r_b = _simulate(df, i, entry, entry - ATR_K * atr_v, target, HORIZON)
            # Arm C: exit at the horizon close, expressed in the SHIPPED risk unit
            # so all three arms share one R denominator.
            cl = df["close"].values
            last = min(i + HORIZON, len(df) - 1)
            r_c = (cl[last] - entry) / a_risk

            if r_b is not None:
                # Rescale B into the shipped risk unit for the same reason.
                b_risk = ATR_K * atr_v
                r_b = r_b * b_risk / a_risk

            if r_a is None or r_b is None:
                continue
            cost_r = (COST_BPS / 10000.0) * 2 * entry / a_risk   # in/out, in R
            rows.append({"symbol": sym, "i": i, "date": str(dates[i])[:10],
                         "A": r_a - cost_r, "B": r_b - cost_r, "C": r_c - cost_r})
        print(f"  [{si}/{len(symbols)}] {sym}: {len(rows)} trades so far", flush=True)
    return pd.DataFrame(rows)


def _boot_diff(df: pd.DataFrame, arm: str, rng: np.random.Generator):
    """Bootstrap CI for mean(arm) - mean(A), resampling SYMBOLS."""
    syms = df["symbol"].unique()
    by = {s: g for s, g in df.groupby("symbol")}
    diffs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.choice(syms, size=len(syms), replace=True)
        d = np.concatenate([(by[s][arm] - by[s]["A"]).values for s in pick])
        diffs[b] = d.mean()
    return float(np.percentile(diffs, 1.25)), float(np.percentile(diffs, 98.75))



def walk_forward(df: pd.DataFrame, n_windows: int = 3) -> None:
    """B-41w — arm C across chronological windows. See the pre-registration above."""
    d = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    if len(d) < n_windows * 20:
        print("too few dated trades for a walk-forward")
        return
    edges = np.array_split(np.arange(len(d)), n_windows)
    print()
    print(f"=== B-41w · arm C across {n_windows} chronological windows ===")
    print(f"  {'window':>7} {'trades':>7} {'from':>11} {'to':>11} "
          f"{'C mean R':>9} {'A mean R':>9} {'C-A':>8}")
    c_pos, imp_pos = [], []
    for w, idx in enumerate(edges, 1):
        g = d.iloc[idx]
        c, a_ = g["C"].mean(), g["A"].mean()
        c_pos.append(c > 0)
        imp_pos.append((c - a_) > 0)
        print(f"  {w:>7} {len(g):>7} {g['date'].iloc[0]:>11} {g['date'].iloc[-1]:>11} "
              f"{c:>+9.3f} {a_:>+9.3f} {c - a_:>+8.3f}")
    ok = all(c_pos) and all(imp_pos)
    print()
    print(f"  arm C positive:    {sum(c_pos)}/{n_windows}")
    print(f"  C beats A:         {sum(imp_pos)}/{n_windows}")
    print("VERDICT:", "STABLE — C positive and ahead of A in every window"
          if ok else
          f"UNSTABLE — pre-registered bar not met "
          f"(C positive {sum(c_pos)}/{n_windows}, ahead {sum(imp_pos)}/{n_windows})")


def main() -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="B-41p: pre-registered sweep-plan test")
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--cache", type=Path,
                    default=Path(__file__).resolve().parent / "cache" / "b41p_trades.csv")
    ap.add_argument("--refresh", action="store_true", help="re-collect, ignoring cache")
    ap.add_argument("--walk-forward", action="store_true",
                    help="B-41w: arm C across 3 chronological windows")
    args = ap.parse_args()

    symbols = args.symbols or bt.LIQUID_50
    # Collection is the whole cost of this study (one scanner call per bar per
    # symbol). Cache it so any FURTHER pre-registered test on the same trades is
    # free — which is the difference between a follow-up that gets run and one
    # that gets talked about.
    if args.cache.exists() and not args.refresh:
        df = pd.read_csv(args.cache)
        print(f"B-41p — {len(df)} cached trades from {args.cache}", flush=True)
    else:
        print(f"B-41p — collecting trades over {len(symbols)} symbols...", flush=True)
        df = collect(symbols)
        if not df.empty:
            args.cache.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(args.cache, index=False)
            print(f"  cached {len(df)} trades -> {args.cache}", flush=True)
    if df.empty:
        print("no trades collected")
        return 1

    print()
    print("=== B-41p · Is the STOP why the sweep edge does not convert? ===")
    print(f"trades={len(df)}  symbols={df['symbol'].nunique()}  "
          f"horizon={HORIZON}d  costs={COST_BPS:.0f}bps  bootstrap={N_BOOT}")
    print()
    names = {"A": "SHIPPED (wick stop + pool target)",
             "B": f"ATR STOP ({ATR_K}x ATR{ATR_N}, same target)",
             "C": f"TIME ONLY (no stop, exit {HORIZON}d close)"}
    base = df["A"].mean()
    print(f"  {'arm':<40} {'mean R':>8} {'win%':>7} {'vs A':>8}  97.5% CI")
    for arm in ("A", "B", "C"):
        m = df[arm].mean()
        w = (df[arm] > 0).mean() * 100
        if arm == "A":
            print(f"  {names[arm]:<40} {m:>+8.3f} {w:>6.1f}% {'—':>8}")
        else:
            rng = np.random.default_rng(20260906)
            lo, hi = _boot_diff(df, arm, rng)
            excl = "excludes 0" if (lo > 0 or hi < 0) else "includes 0"
            print(f"  {names[arm]:<40} {m:>+8.3f} {w:>6.1f}% {m - base:>+8.3f}  "
                  f"[{lo:+.3f}, {hi:+.3f}] {excl}")

    if args.walk_forward:
        walk_forward(df)

    print()
    passed = []
    for arm in ("B", "C"):
        rng = np.random.default_rng(20260906)
        lo, hi = _boot_diff(df, arm, rng)
        if (df[arm].mean() - base) >= PASS_DELTA and df[arm].mean() > 0 and lo > 0:
            passed.append(arm)
    print(f"PASS BAR: beat SHIPPED by >= {PASS_DELTA:+.2f}R, own mean R > 0, "
          f"Bonferroni 97.5% CI excludes 0")
    print("VERDICT:", (f"{', '.join(passed)} PASSES — the stop is the constraint; "
                       f"a pre-registered follow-up on the plan is licensed")
          if passed else
          "NULL — no arm clears the bar; the plan is not fixably the problem "
          "by this route, and B-41m's +0.06R stands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
