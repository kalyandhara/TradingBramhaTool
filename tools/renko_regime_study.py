#!/usr/bin/env python3
"""renko_regime_study.py — B-43r: does the Renko flip work once sideways chop is cut?

B-43 measured the brick flip at a clean null. The follow-up hypothesis, raised from
watching the chart: flips *look* convincing when the market is trending and worthless
when it is sideways, so gating on trend strength should recover an edge.

That is a real, testable claim. It is also the shape of claim that most often produces
a false positive, so this module is written to make that hard.

══ PRE-REGISTRATION — written before the first run, per B-44r's precedent ═══════

  PRIMARY TEST (the only one that decides anything)
    signal    LONG brick flips (dir=+1) whose flip bar has ADX(14) >= 25
    baseline  EVERY bar with ADX(14) >= 25          <- the whole point, see below
    horizon   20 trading days, entry at next open
    statistic mean(signal) - mean(baseline), in percent
    p-value   circular-rotation test (Welch is invalid here, see _rotation_p)
    PASS BAR  edge > 0 AND p_rot < 0.05.  Anything else is a null and B-43 stands.

  DIRECTIONAL CONTROL (expected null; if it "works", the harness is broken)
    Down-flips scored as longs under the same ADX filter. B-43 found the down leg
    carried nothing; a trend filter should not change that. If this lights up, the
    filter is selecting trending periods rather than informative flips, and the
    primary number means nothing either.

  SECONDARY (reported but NOT decisive, and only meaningful if PRIMARY clears)
    - brick-run length: flips ending a run of >= 3 same-colour bricks
    - both filters together
    These are follow-ups, not independent confirmations. Three tests on one dataset
    is already three chances to be fooled; they are here to describe a surviving
    effect, not to hunt for one.

══ WHY THE BASELINE IS ALSO FILTERED — the mistake this module exists to avoid ══

Gate flips on ADX >= 25, compare against an UNCONDITIONAL every-bar baseline, and a
positive edge is close to guaranteed: trending periods pay in general, whatever you
buy in them. That measures the regime, not the flip.

This is structurally the same trap that killed B-44r — Black-Scholes gamma carries
1/sigma, so "high gamma" was silently proxying for "low volatility", and controls
halved the effect to insignificance. And the same shape as B-34r4, where a drifting
promoter window made names look worse as the cache deepened and the ranking was
partly sorting on the artefact.

So the baseline is drawn from the SAME filtered bars as the signal. Signal is
"flips in a trend"; baseline is "bars in a trend". The difference isolates the flip.

The unconditional comparison is still computed and printed, labelled REGIME CONTRAST,
because the gap between the two is precisely the size of the illusion — the number
you would have reported if you had not matched the baseline.

══ WHAT B-43 ALREADY SETTLES, AND WHY THE PRIOR IS LOW ═══════════════════════════

The chart type is ALREADY a noise filter. B-43 recorded that Renko flips fire ~40%
less often than the EVWMA cross and still measure zero — "noise reduction without
edge". Filtering has therefore been tried once on this exact signal and did not
help. This study applies a second filter to the output of the first. That is a
reasonable next step, not a fresh idea, and the prior should be low accordingly.

Prior, recorded before running: expect a null, with the ADX-filtered number looking
better than B-43's only in the REGIME CONTRAST column.

══ OUTCOME 2026-09-06 — FAILED THE BAR, AND IN THE OPPOSITE DIRECTION ═══════════

The prior was half right: it is not an edge. It is worse than that.

  PRIMARY   flip_up, ADX-matched   n=576   edge = -1.01%   p_rot = 0.000
  CONTROL   flip_dn as long        n=655   edge = +0.38%   p_rot = 0.331  (null, good)
  SECONDARY flip_up, run >= 3      n=394   edge = -1.30%
  B-43 reproduced, no filter       n=1766  edge = -0.02%

Inside a trend, a flip marks a moment measurably WORSE than an average moment in that
same trend. The mechanism is legible, which is why the sign is believable: an up-flip
REQUIRES price to have first fallen enough to print down bricks and then turned back
up, so it selects the instant just after a counter-move -- part of the run already
given back, at the point where a pullback is hardest to distinguish from a reversal.
The matched baseline, "any bar in a trend", is simply already long and holding.
Holding beats re-entering, and the brick-run secondary sharpens it: the longer the
counter-run, the more of the trend was missed and the worse the entry.

The prior was also wrong about where the illusion lived. REGIME CONTRAST came back at
-0.48%, so even an unmatched baseline would not have shown an edge here. The
convincing appearance was VISUAL, not arithmetic -- in a strong trend everything looks
right in hindsight because the trend was right. No baseline correction catches that
kind; only a measurement does.

This does NOT license fading flips. The pre-registered bar was `edge > 0`, so a
significant negative fails it. "Flips are contrarian in trends" is a new claim that
needs its own pre-registration, and -1% would not survive costs on the short side.
Limitations: 22 symbols, one threshold, survivorship in the basket.

CLI:
  py -3 tools/renko_regime_study.py
  py -3 tools/renko_regime_study.py --adx 20 --horizon 10   # exploratory ONLY
"""  # claims-lint: checked B-43r
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

import evwma_vwap_macd_backtest as base
import renko_backtest as rk

HERE = Path(__file__).resolve().parent
WARMUP = rk.WARMUP

#: Shifts enumerated by the rotation test. Bounded to keep the run to seconds; the
#: grid is coarse (every 3rd offset) rather than exhaustive, which is stated in the
#: output so nobody reads p as exact the way gamma_regime_backtest's is.
ROT_STEP = 3
ROT_MAX = 400


def _load_ohlc(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    bars = doc["bars"]
    return (doc["symbol"],
            np.array([b["open"] for b in bars], float),
            np.array([b["high"] for b in bars], float),
            np.array([b["low"] for b in bars], float),
            np.array([b["close"] for b in bars], float))


def _wilder(x: np.ndarray, n: int) -> np.ndarray:
    """Wilder's smoothing — causal, seeded on the first n-sum."""
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    s = np.nansum(x[:n])
    out[n - 1] = s
    for i in range(n, len(x)):
        s = s - (s / n) + x[i]
        out[i] = s
    return out


def adx_series(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:
    """ADX(14), Wilder. Uses only bars <= i, so a value at i is known at i's close."""
    m = len(c)
    tr = np.zeros(m)
    dmp = np.zeros(m)
    dmm = np.zeros(m)
    for i in range(1, m):
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        dmp[i] = up if (up > dn and up > 0) else 0.0
        dmm[i] = dn if (dn > up and dn > 0) else 0.0
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    str_, sdp, sdm = _wilder(tr, n), _wilder(dmp, n), _wilder(dmm, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        pdi = 100.0 * sdp / str_
        mdi = 100.0 * sdm / str_
        dx = 100.0 * np.abs(pdi - mdi) / (pdi + mdi)
    adx = np.full(m, np.nan)
    ok = np.isfinite(dx)
    if ok.sum() >= n:
        idx = np.flatnonzero(ok)
        seed = idx[0] + n - 1
        if seed < m:
            adx[seed] = np.nanmean(dx[idx[0]:seed + 1])
            for i in range(seed + 1, m):
                if np.isfinite(dx[i]) and np.isfinite(adx[i - 1]):
                    adx[i] = (adx[i - 1] * (n - 1) + dx[i]) / n
    return adx


def _panel(paths: list[Path], horizon: int, adx_n: int):
    """Per symbol: forward returns, the ADX filter mask, and flip event vectors."""
    out = []
    for p in paths:
        sym, o, h, l, c = _load_ohlc(p)
        m = len(c)
        if m < WARMUP + horizon + 3:
            continue
        adx = adx_series(h, l, c, adx_n)

        fwd = np.full(m, np.nan)
        last = m - horizon - 2
        for t in range(WARMUP, last + 1):
            if o[t + 1] > 0:
                fwd[t] = (c[t + 1 + horizon] / o[t + 1] - 1.0) * 100.0

        up = np.zeros(m, bool)
        dn = np.zeros(m, bool)
        run = np.zeros(m, int)
        for r in rk.signals_for(p):
            t = r["index"]
            if WARMUP <= t <= last:
                (up if r["dir"] == 1 else dn)[t] = True
                run[t] = r.get("bricks_in_prior", 0)

        out.append({"sym": sym, "fwd": fwd, "adx": adx, "up": up, "dn": dn,
                    "run": run, "lo": WARMUP, "hi": last})
    return out


def _edge(panel, event_key, mask_fn):
    """Pooled mean(signal) - mean(baseline), both drawn from mask_fn's bars."""
    sig, bas = [], []
    for d in panel:
        keep = mask_fn(d) & np.isfinite(d["fwd"])
        ev = d[event_key] & keep
        sig.append(d["fwd"][ev])
        bas.append(d["fwd"][keep])
    sig = np.concatenate(sig) if sig else np.array([])
    bas = np.concatenate(bas) if bas else np.array([])
    if len(sig) < 5 or len(bas) < 50:
        return None
    return {"n_sig": len(sig), "n_base": len(bas),
            "sig": float(sig.mean()), "base": float(bas.mean()),
            "edge": float(sig.mean() - bas.mean()),
            "hit": float((sig > 0).mean() * 100.0),
            "hit_base": float((bas > 0).mean() * 100.0)}


def _rotation_p(panel, event_key, mask_fn, observed: float) -> tuple[float | None, int]:
    """Rotate the EVENT vector against returns; recompute the same edge each time.

    The events are sparse and clustered, and the returns are autocorrelated by a
    20-day overlap. Rotation preserves both — the null it builds is "these flips,
    happening at other times" rather than "independent draws", which is the honest
    null for "does flip TIMING carry information beyond flip frequency".

    Rotated per symbol by the same offset so the cross-sectional structure survives.
    """
    stats = []
    for s in range(ROT_STEP, ROT_MAX, ROT_STEP):
        sig, bas = [], []
        for d in panel:
            keep = mask_fn(d) & np.isfinite(d["fwd"])
            ev = np.roll(d[event_key], s) & keep
            if ev.sum() == 0:
                continue
            sig.append(d["fwd"][ev])
            bas.append(d["fwd"][keep])
        if not sig:
            continue
        sig = np.concatenate(sig)
        bas = np.concatenate(bas)
        if len(sig) < 5:
            continue
        stats.append(abs(float(sig.mean() - bas.mean())))
    if len(stats) < 20:
        return None, len(stats)
    return float(np.mean(np.asarray(stats) >= abs(observed))), len(stats)


def _row(label, r, p=None, nrot=None):
    if r is None:
        return f"  {label:<34} (too few observations)"
    ptxt = "     -" if p is None else f"{p:6.3f}"
    star = "*" if (p is not None and p < 0.05) else " "
    return (f"  {label:<34} n={r['n_sig']:<5d} sig={r['sig']:+6.2f}%  "
            f"base={r['base']:+6.2f}%  edge={r['edge']:+6.2f}%  "
            f"hit={r['hit']:4.1f}/{r['hit_base']:4.1f}  p_rot={ptxt}{star}")


def main() -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="B-43r: Renko flip under a trend filter")
    ap.add_argument("--adx", type=float, default=25.0, help="ADX(14) floor (pre-registered 25)")
    ap.add_argument("--adx-n", type=int, default=14)
    ap.add_argument("--horizon", type=int, default=20, help="pre-registered 20")
    ap.add_argument("--run", type=int, default=3, help="brick-run length for the secondary")
    args = ap.parse_args()

    paths = sorted(base.CACHE.glob("*_1d.json"))
    paths = [p for p in paths if not p.name.startswith("_")]   # drop index files
    if not paths:
        print(f"no cached bars in {base.CACHE} — run renko_backtest.py --export first")
        return 1

    panel = _panel(paths, args.horizon, args.adx_n)
    if not panel:
        print("no symbol had enough history")
        return 1

    trend = lambda d: np.nan_to_num(d["adx"], nan=-1.0) >= args.adx
    allbars = lambda d: np.ones(len(d["fwd"]), bool)

    print(f"=== B-43r · Renko flip under a trend filter ===")
    print(f"symbols={len(panel)}  horizon={args.horizon}d  "
          f"filter=ADX({args.adx_n})>={args.adx:g}  entry=next open")
    print()

    print("PRIMARY — long flips vs a baseline drawn from the SAME trending bars")
    r = _edge(panel, "up", trend)
    p, nrot = _rotation_p(panel, "up", trend, r["edge"]) if r else (None, 0)
    print(_row("flip_up | ADX-matched baseline", r, p))
    passed = bool(r and r["edge"] > 0 and p is not None and p < 0.05)
    print()

    print("DIRECTIONAL CONTROL — expected null; if this fires, distrust the primary")
    rc = _edge(panel, "dn", trend)
    pc, _ = _rotation_p(panel, "dn", trend, rc["edge"]) if rc else (None, 0)
    print(_row("flip_dn as long | ADX-matched", rc, pc))
    print()

    print("REGIME CONTRAST — the same flips against an UNFILTERED baseline.")
    print("  The gap vs PRIMARY is how much apparent edge is the regime, not the flip.")
    ru = _edge(panel, "up", allbars)
    naive = None
    if r and ru:
        # flips-in-trend scored against all bars: the number a careless run reports
        sig, bas = [], []
        for d in panel:
            keep = np.isfinite(d["fwd"])
            ev = d["up"] & trend(d) & keep
            sig.append(d["fwd"][ev]); bas.append(d["fwd"][keep])
        sig, bas = np.concatenate(sig), np.concatenate(bas)
        naive = float(sig.mean() - bas.mean())
        print(f"  flip_up(ADX-gated) vs ALL bars      edge={naive:+6.2f}%   "
              f"<- unmatched baseline, NOT a result")
    print(_row("flip_up (all) | all-bar baseline", ru))
    print()

    print(f"SECONDARY — reported only; decisive only if PRIMARY cleared "
          f"({'it did' if passed else 'it did NOT'})")
    # brick-run filter applies to the EVENT, not the baseline bars: a baseline bar has
    # no brick run of its own, so the matched baseline stays "bars in a trend".
    sig = []
    for d in panel:
        keep = trend(d) & np.isfinite(d["fwd"])
        sig.append(d["fwd"][d["up"] & keep & (d["run"] >= args.run)])
    sig = np.concatenate(sig) if sig else np.array([])
    if len(sig) >= 5 and r:
        bas = []
        for d in panel:
            keep = trend(d) & np.isfinite(d["fwd"])
            bas.append(d["fwd"][keep])
        bas = np.concatenate(bas)
        print(f"  flip_up | run>={args.run} | ADX-matched    n={len(sig):<5d} "
              f"sig={sig.mean():+6.2f}%  base={bas.mean():+6.2f}%  "
              f"edge={sig.mean() - bas.mean():+6.2f}%  hit={(sig > 0).mean() * 100:4.1f}%")
    else:
        print("  (too few flips with that brick run)")
    print()

    print(f"rotation grid: every {ROT_STEP} bars to {ROT_MAX} ({nrot} usable shifts) — "
          f"a GRID, so p is approximate, not exact")
    print("VERDICT:", "PASSES the pre-registered bar — inspect for robustness"
          if passed else
          "NULL — pre-registered bar not met; B-43 stands and the flip is not a trigger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
