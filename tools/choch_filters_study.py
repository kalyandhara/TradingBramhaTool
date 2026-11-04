#!/usr/bin/env python3
"""choch_filters_study.py - does CHoCH work as a TRIGGER inside a filter?

Follow-up to choch_study.py (bare CHoCH: FAIL, +0.24% @20d, p_rot 0.511).

PRE-REGISTERED DESIGN (2026-10-07, written before the first run; do not edit here)
  Same walk, panel, harness (renko_regime_study._edge/_rotation_p), bars
  (cache/cardinality_deep, 459 names), pivot 5, entry next open, HORIZON 20.
  Two tests, so the pass bar is Bonferroni-corrected: edge > 0 AND p_rot < 0.025
  AND n >= 200.

  TEST A  TREND REGIME (primary)
    regime   close > SMA200 AND SMA200 > SMA200 twenty bars earlier
    signal   CHoCH bars inside the regime
    baseline bearish-structure bars ALSO inside the regime (state-matched both
             ways - the test is "does the CHoCH select within an uptrend
             pullback", not "do uptrends go up")
  TEST B  SELL-SIDE SWEEP
    sweep    a bar whose low trades below the last confirmed swing low but
             CLOSES back above it (stop run, rejected)
    signal   CHoCH with a sweep in the prior 20 bars
    baseline bearish-structure bars with a sweep in the prior 20 bars
  CONTEXT (decide nothing)
    C1 CHoCH in regime vs ALL regime bars
    C2 CHoCH OUTSIDE regime vs bearish-outside-regime bars (should be <= A)
    C3 regime bars vs ALL bars (size of the trend effect itself)

CLI:  py -3 tools/choch_filters_study.py [--horizon 20]
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
import renko_regime_study as reg
from choch_study import CACHE, WARMUP, PIVOT_LEN, _load, walk

HORIZON = 20; SWEEP_WIN = 20; ALPHA = 0.025; MIN_EVENTS = 200


def sma(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        cs = np.cumsum(np.insert(x, 0, 0.0))
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def sweeps(h, l, c, pivot_len=PIVOT_LEN):
    """Bars that pierce the last confirmed swing low and close back above it."""
    m = len(c); sw = np.zeros(m, bool); sl = None
    for i in range(pivot_len * 2, m):
        j = i - pivot_len
        if j >= pivot_len and l[j] == l[j - pivot_len: j + pivot_len + 1].min():
            sl = l[j]
        if sl is not None:
            if l[i] < sl and c[i] >= sl:
                sw[i] = True
            elif c[i] < sl:
                sl = None          # broken on a close - the walk's bearish break
    return sw


def recent(flag, k):
    """True at t if flag fired in [t-k, t-1]."""
    cs = np.cumsum(np.insert(flag.astype(int), 0, 0))
    idx = np.arange(len(flag))
    lo = np.maximum(idx - k, 0)
    return (cs[idx] - cs[lo]) > 0


def build(paths, horizon):
    out = []
    for p in paths:
        sym, o, h, l, c = _load(p)
        m = len(c)
        if m < max(WARMUP, 220) + horizon + 3:
            continue
        fwd = np.full(m, np.nan); last = m - horizon - 2
        idx = np.arange(WARMUP, last + 1); idx = idx[o[idx + 1] > 0]
        fwd[idx] = (c[idx + 1 + horizon] / o[idx + 1] - 1.0) * 100.0
        choch, bos, bear, disp, live = walk(o, h, l, c)
        s200 = sma(c, 200)
        prev = np.full(m, np.nan); prev[20:] = s200[:-20]
        regime = (c > s200) & (s200 > prev)          # NaN compares False
        swp = recent(sweeps(h, l, c), SWEEP_WIN)
        rng = np.zeros(m, bool); rng[max(WARMUP, 220):last + 1] = True
        st = (bear | choch) & rng                    # CHoCH bars are bearish going in
        out.append({"sym": sym, "fwd": fwd, "all": rng,
                    "A": choch & regime & rng, "A_base": st & regime,
                    "B": choch & swp & rng, "B_base": st & swp,
                    "C2": choch & ~regime & rng, "C2_base": st & ~regime,
                    "reg": regime & rng, "regall": regime & rng})
    return out


def arm(panel, key, base):
    fn = lambda d: d[base]
    r = reg._edge(panel, key, fn)
    if r is None:
        return None, None, 0
    p, n = reg._rotation_p(panel, key, fn, r["edge"])
    return r, p, n


def verdict(r, p):
    if r is None or r["n_sig"] < MIN_EVENTS:
        return "INCONCLUSIVE - UNDERPOWERED"
    return "PASS" if (r["edge"] > 0 and p is not None and p < ALPHA) else "FAIL"


def main():
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError): pass
    ap = argparse.ArgumentParser(); ap.add_argument("--horizon", type=int, default=HORIZON)
    a = ap.parse_args()
    panel = build(sorted(CACHE.glob("*_1d.json")), a.horizon)
    print(f"{len(panel)} names | horizon {a.horizon}d | pass: edge>0 & p_rot<{ALPHA} & n>={MIN_EVENTS}")
    res = {}
    for label, key, base in [("TEST A  CHoCH in uptrend regime", "A", "A_base"),
                             ("TEST B  CHoCH after SSL sweep", "B", "B_base"),
                             ("C1     CHoCH in regime vs ALL reg", "A", "regall"),
                             ("C2     CHoCH outside regime", "C2", "C2_base"),
                             ("C3     regime bars vs ALL bars", "reg", "all")]:
        r, p, n = arm(panel, key, base)
        print(reg._row(label, r, p, n)); res[key + base] = (r, p)
    print(f"\nVERDICT A (trend regime): {verdict(*res['AA_base'])}")
    print(f"VERDICT B (sell-side sweep): {verdict(*res['BB_base'])}")


if __name__ == "__main__":
    main()
