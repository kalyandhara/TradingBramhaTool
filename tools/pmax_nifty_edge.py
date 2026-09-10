#!/usr/bin/env python3
"""pmax_nifty_edge.py — B-65r: does the sentiment index's PMax factor discriminate?

Runs the design pre-registered in `analyses/Open-Backlog.md` §B-65r, committed at
`96dbc93` BEFORE this scorer existed. Nothing here may change the design; if
something has to change, the entry changes first and says why.

══ THE CLAIM, AS THE CODE MAKES IT ══════════════════════════════════════════════

`sentiment_index._pmax_direction_nifty_1h` returns `factor = 1.0` when PMax
direction on NIFTY 1H is up and `0.0` when it is down, and that factor is
multiplied by `W_PMAX_1H = 20` -- a FIFTH of the sentiment score.

So the assertion is NOT "the up-state earns a positive return". It is that **the
two states are different**. A factor scoring 20 for up and 0 for down claims to
DISCRIMINATE, and the statistic that matches that claim is a SPREAD:

    mean(fwd | dir = +1) - mean(fwd | dir = -1)

Testing up-vs-all instead would let a factor that never discriminates pass on
market drift alone -- the exact confound B-65's state arm was written to expose,
and the one it then failed to be saved by.

══ PRE-REGISTERED DESIGN (mirrored from the entry; do not edit here) ════════════

  PRIMARY   ^NSEI 1H, 730d (the yfinance ceiling), the shipped port's own
            parameters, spread at 5 trading days (~34 bars), entry next bar's
            open, circular-rotation p.
            PASS BAR: spread > 0 AND p_rot < 0.05
  descriptive  the same spread at ~1 day and ~20 days; up-vs-all and down-vs-all
            reported separately.

  POWER, declared in advance because it IS the problem here: this is ONE series,
  not a cross-section -- roughly 150 independent windows at the primary horizon.
  **A null does NOT retire the factor.** It means the exact claim is
  unvalidatable at the depth free data allows, which is a different and more
  honest statement.

  SECOND ARM  ^NSEI DAILY, longest history available, same parameters, same
            spread at 20 days. NOT the factor's claim (the factor is 1H) and it
            cannot pass or fail W_PMAX_1H on its own. It answers the question
            standing behind it: does PMax direction on this index discriminate at
            all, over a sample containing more than one regime?

  REGIME CAVEAT: the 1H window (2023-10 -> 2026-09) is substantially one bull
            regime. A positive 1H result reads as "unfalsified in one regime",
            never as validation.

  PRIOR: genuinely uncertain -- the one place on that page where skepticism is
  not the automatic call. B-32 measured that regime carries real information
  (+0.22% RISK-ON vs -1.78% RISK-OFF, p<0.005), while B-65's daily-equity state
  arm points the other way. Two pieces of this desk's own evidence disagree.

══ ONE RATCHET, NOT TWO ═════════════════════════════════════════════════════════

The direction series comes from `sentiment_index._pmax_walk` -- the loop that was
extracted from `_pmax_direction_nifty_1h` itself, which now calls it and takes the
last element. So this scores THE factor, not a reimplementation of it. Copying the
ratchet here would have let the measurement drift from the thing measured.

CLI:
    py -3 tools/pmax_nifty_edge.py
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

import sentiment_index as si

try:
    import yfinance as yf
except Exception as e:  # pragma: no cover
    sys.exit(f"yfinance required: {e}")

# ── pre-registered constants. Changing one changes the study. ────────────────
BARS_PER_DAY = 7          #: NIFTY 1H bars per session (9:15-15:30)
PRIMARY_H = 5 * BARS_PER_DAY   #: 5 trading days, the primary horizon
DESC_H = [BARS_PER_DAY, 20 * BARS_PER_DAY]   #: ~1 day and ~20 days, descriptive
DAILY_H = 20              #: the second arm's horizon, in daily bars
ROT_STEP = 7
ROT_MIN_STATS = 20


def direction_series(high, low, close, atr_len=10, atr_mult=3.0, ma_len=10):
    """PMax direction per bar, via the SHIPPED ratchet (`si._pmax_walk`).

    ATR and the hl2 EMA are recomputed here exactly as `_pmax_direction_nifty_1h`
    computes them; only the ratchet -- the part with state, and therefore the part
    that could drift -- is imported rather than repeated.
    """
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                    abs(high[i] - close[i - 1]),
                    abs(low[i] - close[i - 1]))
    atr = np.zeros(n)
    atr[atr_len - 1] = tr[:atr_len].mean()
    for i in range(atr_len, n):
        atr[i] = (atr[i - 1] * (atr_len - 1) + tr[i]) / atr_len

    src = (high + low) / 2
    alpha = 2 / (ma_len + 1)
    ema = np.zeros(n)
    ema[0] = src[0]
    for i in range(1, n):
        ema[i] = alpha * src[i] + (1 - alpha) * ema[i - 1]

    dirs, _, _ = si._pmax_walk(ema, atr, atr_mult, warm=max(atr_len, ma_len))
    return dirs


def forward(o, c, horizon):
    """Next-bar open -> close `horizon` bars later, percent. NaN where unavailable."""
    n = len(c)
    fwd = np.full(n, np.nan)
    for t in range(n - horizon - 2):
        if o[t + 1] > 0:
            fwd[t] = (c[t + 1 + horizon] / o[t + 1] - 1.0) * 100.0
    return fwd


def spread(dirs, fwd):
    up = fwd[(dirs == 1) & np.isfinite(fwd)]
    dn = fwd[(dirs == -1) & np.isfinite(fwd)]
    if len(up) < 20 or len(dn) < 20:
        return None
    return {"n_up": len(up), "n_dn": len(dn),
            "up": float(up.mean()), "dn": float(dn.mean()),
            "spread": float(up.mean() - dn.mean()),
            "all": float(fwd[np.isfinite(fwd)].mean()),
            "hit_up": float((up > 0).mean() * 100.0),
            "hit_dn": float((dn > 0).mean() * 100.0)}


def rotation_p(dirs, fwd, observed):
    """Rotate the STATE vector; recompute the same spread each time.

    The state is long, contiguous runs and the returns overlap heavily, so an
    i.i.d. null would be meaningless. Rotation preserves the run-length structure
    and the up/down proportions and destroys only the alignment with returns --
    "this direction series, offset in time", which is the honest null for
    "does the state carry information about what happens next".
    """
    n = len(dirs)
    stats = []
    for s in range(ROT_STEP, n - ROT_STEP, max(ROT_STEP, n // 120)):
        r = spread(np.roll(dirs, s), fwd)
        if r is not None:
            stats.append(abs(r["spread"]))
    if len(stats) < ROT_MIN_STATS:
        return None, len(stats)
    return float(np.mean(np.asarray(stats) >= abs(observed))), len(stats)


def _row(label, r, p, nrot):
    if r is None:
        return f"  {label:<34} (too few observations)"
    ptxt = "     -" if p is None else f"{p:6.3f}"
    star = "*" if (p is not None and p < 0.05) else " "
    return (f"  {label:<34} up={r['up']:+6.2f}% (n={r['n_up']:5d})  "
            f"dn={r['dn']:+6.2f}% (n={r['n_dn']:5d})  "
            f"spread={r['spread']:+6.2f}%  hit={r['hit_up']:4.1f}/{r['hit_dn']:4.1f}  "
            f"p_rot={ptxt}{star}")


def load(interval, period):
    h = yf.Ticker("^NSEI").history(period=period, interval=interval, auto_adjust=False)
    h = h.dropna(subset=["Close"])
    return (h.index[0], h.index[-1], len(h),
            h["High"].astype(float).values, h["Low"].astype(float).values,
            h["Close"].astype(float).values, h["Open"].astype(float).values)


def main() -> int:
    ap = argparse.ArgumentParser(description="B-65r - does the PMax sentiment factor discriminate?")
    ap.add_argument("--period", default="730d")
    args = ap.parse_args()

    print("B-65r - PMax direction on NIFTY: does the sentiment factor DISCRIMINATE?")
    print("PRIMARY statistic is a SPREAD (up minus down), because the factor scores")
    print(f"20 for up and 0 for down -- it claims the two states differ.\n")

    # ── ARM 1: the factor's actual claim ────────────────────────────────────
    t0, t1, n, hi, lo, cl, op = load("1h", args.period)
    dirs = direction_series(hi, lo, cl)
    print(f"ARM 1 - ^NSEI 1H, {n} bars, {t0.date()} -> {t1.date()} "
          f"({int((dirs == 1).sum())} up / {int((dirs == -1).sum())} down)")
    primary = None
    for h, label in [(PRIMARY_H, f"PRIMARY  spread @{PRIMARY_H} bars (~5d)"),
                     (DESC_H[0], f"desc     spread @{DESC_H[0]} bars (~1d)"),
                     (DESC_H[1], f"desc     spread @{DESC_H[1]} bars (~20d)")]:
        fwd = forward(op, cl, h)
        r = spread(dirs, fwd)
        p, nrot = (None, 0) if r is None else rotation_p(dirs, fwd, r["spread"])
        print(_row(label, r, p, nrot))
        if h == PRIMARY_H:
            primary = (r, p)

    # ── ARM 2: same question, real power, different timeframe ───────────────
    t0d, t1d, nd, hid, lod, cld, opd = load("1d", "max")
    dird = direction_series(hid, lod, cld)
    print(f"\nARM 2 - ^NSEI DAILY, {nd} bars, {t0d.date()} -> {t1d.date()} "
          f"({int((dird == 1).sum())} up / {int((dird == -1).sum())} down)")
    print("        NOT the factor's claim (that is 1H) -- this asks whether PMax")
    print("        direction on this index discriminates at all, with real power.")
    fwdd = forward(opd, cld, DAILY_H)
    rd = spread(dird, fwdd)
    pd_, nrotd = (None, 0) if rd is None else rotation_p(dird, fwdd, rd["spread"])
    print(_row(f"SECOND   spread @{DAILY_H}d", rd, pd_, nrotd))

    # ── verdict ─────────────────────────────────────────────────────────────
    print()
    r, p = primary
    if r is None:
        print("VERDICT: INCONCLUSIVE - the primary arm produced too few observations.")
        return 0
    passed = r["spread"] > 0 and p is not None and p < 0.05
    daily_disc = rd is not None and pd_ is not None and pd_ < 0.05 and rd["spread"] > 0

    print(f"PRIMARY (the factor's own claim): {'PASS' if passed else 'FAIL'} - "
          f"spread={r['spread']:+.2f}%, p_rot={'n/a' if p is None else f'{p:.3f}'}")
    print(f"SECOND  (the question behind it): "
          f"{'discriminates' if daily_disc else 'does NOT discriminate'}"
          + ("" if rd is None else f" - spread={rd['spread']:+.2f}%, "
             f"p_rot={'n/a' if pd_ is None else f'{pd_:.3f}'}"))
    print()

    if passed and daily_disc:
        print("READING: both arms discriminate. The factor is SUPPORTED. Leave W_PMAX_1H")
        print("         alone and record it as measured rather than assumed.")
    elif not passed and daily_disc:
        print("READING: the daily arm discriminates and the 1H arm does not. That is a")
        print("         POWER result, not an absence -- one series and ~150 independent")
        print("         windows cannot resolve what a decades-long daily sample can.")
        print("         The factor stays, on inherited plausibility.")
    elif passed and not daily_disc:
        print("READING: the 1H arm discriminates where the longer daily sample does not.")
        print("         Treat with suspicion, not celebration: the 1H window is largely")
        print("         one bull regime, and the pre-registration says a positive there")
        print("         reads as 'unfalsified in one regime', never as validation.")
    else:
        print("READING: NEITHER arm discriminates. The 20 points W_PMAX_1H contributes")
        print("         to the sentiment score rest on something nobody has shown --")
        print("         and the daily arm has the power to say so, which the 1H arm")
        print("         alone would not have had.")
        print("         NOTHING IS DELETED ON THIS RESULT, the same rule as B-59r and")
        print("         B-65. What changes is that RE-WEIGHTING the sentiment index is")
        print("         now a live proposal with evidence behind it, and that proposal")
        print("         is its own entry.")

    print("\nLIMITS: the 1H window is substantially ONE bull regime, which is exactly")
    print("        when a direction factor looks harmless; ^NSEI 1H is capped at 730d")
    print("        by the data source, so the primary arm cannot be deepened without")
    print("        paying for data; rotation grids are coarse, so p is indicative.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
