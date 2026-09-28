#!/usr/bin/env python3
"""pivot_timeframe_agreement.py — do `pivot_d` and `pivot_w` agree? (B-97)

The desk has printed both columns side by side since B-63b and has never asked
whether they say the same thing. This asks, and the answer decides how B-96
should present the three timeframes it wants to add.

══ THIS FILE IS THE PRE-REGISTRATION ═══════════════════════════════════════════

Committed BEFORE it was run, and the thresholds below were written before any
number came back — the B-42r precedent, where the verdict bands were fixed in
advance so the reading could not be invented from the result. Nothing in the
DESIGN section may be edited after the first run; if something has to change,
the change and its reason go in the backlog entry first.

══ WHY THIS IS AN AGREEMENT TEST AND NOT AN EDGE TEST ══════════════════════════

Same reasoning as B-42r, which this copies deliberately. A pivot zone is a
DEFINITION — which band the last close sits in — not a signal. The question is
not "which timeframe is more profitable" but "are these two the same reading or
two different ones", and that needs no forward return at all. Running an edge
sweep first would be parameter-fitting on columns with no established edge:
B-19 measured 0 of 41 scanners stable after costs.

══ WHY A CHANCE BASELINE, AND WHAT THE BACKLOG'S "ROTATION P" MEANS HERE ═══════

The B-97 entry says to use a rotation p-value, citing the autocorrelated-state
trap (`gamma_regime_backtest._rotation_p`: a known null printed p=0.031 under
Welch and 0.32 under rotation). That instruction was written for scoring a state
against FORWARD RETURNS, which this does not do — so applying it literally would
be a test of nothing.

What survives of it, and what this file implements, is the part that actually
bites: **a raw agreement rate is mostly base rate.** If 55% of all names sit in
`PP-S1` on both timeframes, two independent columns agree ~35% of the time for
free. That is exactly what B-59's v2 re-run found when it added a rotation null
and the raw coverage turned out to be mostly chance.

So the statistic is **agreement LIFT over a chance baseline**, where chance is
built by rotating the weekly labels against the daily ones across the
cross-section (symbol i's daily zone paired with symbol i+k's weekly zone). The
rotation preserves each column's own label distribution exactly — which is the
whole point, since the base rate lives in that distribution — and destroys only
the pairing. Reported with the raw rate, never instead of it.

══ PRE-REGISTERED DESIGN ══════════════════════════════════════════════════════

  UNIVERSE   NIFTY 500 constituents, daily bars, `--days` of history.
             A name that cannot produce both reads is EXCLUDED, not counted as
             a disagreement.
  READS      daily  = row_metrics.pivot_zone(df)
             weekly = row_metrics.pivot_zone(row_metrics.weekly_frame(df))
             Both are the SHIPPED functions. Nothing is reimplemented here —
             the B-59 rule, so the study cannot measure a different thing from
             what the table prints.
  PRIMARY    agreement rate on the 7-label zone, and its lift over the rotation
             baseline.
  SECONDARY  (a) SIDE agreement — the three labels above PP collapsed to ABOVE,
                 the three below to BELOW, `Near Pivot` to AT. This is the
                 direction a reader takes away, and two columns can disagree on
                 the exact band while agreeing on the side.
             (b) OPPOSITE rate — one reads ABOVE while the other reads BELOW.
                 The B-42r analogue of its 17.6%, and the number that decides
                 whether B-96 is a perspective or a contradiction.
  ROTATION   ROTATIONS offsets, k = 1 .. ROTATIONS, mean agreement across them.

  VERDICT BANDS, fixed in advance, on SIDE agreement (the reader's takeaway):
    >= 90%   COSMETIC          — one column would do; the second is noise
    >= 70%   REAL BUT NARROW   — a visible split, most readers see the same side
    <  70%   TWO DIFFERENT READINGS
  and, independently, on the OPPOSITE rate:
    >= 20%   CONTRADICTION     — B-96 must not ship five columns side by side
                                 without saying which one governs

  Neither band is a pass/fail for the columns. Both already ship; this decides
  how the NEXT three are presented.

CLI:
  py -3 -X utf8 tools/pivot_timeframe_agreement.py
  py -3 -X utf8 tools/pivot_timeframe_agreement.py --symbols 200 --days 800
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

import row_metrics as rm

#: The seven labels `pivot_zone` can return, grouped by the side of PP a reader
#: takes away from them. `Near Pivot` is its own side: it is the one label that
#: declines to pick a direction, and folding it either way would invent one.
ABOVE = ("R1", "R1-PP", "Near R1")
BELOW = ("PP-S1", "S1", "Near S1")
AT = ("Near Pivot",)

#: Cross-sectional rotations used to build the chance baseline.
ROTATIONS = 25

#: Fixed in advance. See the DESIGN block.
COSMETIC_PCT = 90.0
NARROW_PCT = 70.0
CONTRADICTION_PCT = 20.0


def side(zone: str | None) -> str | None:
    if zone in ABOVE:
        return "ABOVE"
    if zone in BELOW:
        return "BELOW"
    if zone in AT:
        return "AT"
    return None


def read_pair(df) -> tuple[str, str] | None:
    """(daily zone, weekly zone) through the shipped functions, or None.

    None means the name could not be read on one of the two timeframes — an
    exclusion, never a disagreement. A short listing has no prior weekly bar to
    take a pivot from, and counting that as a split would manufacture one.
    """
    try:
        d = rm.pivot_zone(df)
        wk = rm.weekly_frame(df)
        w = rm.pivot_zone(wk) if wk is not None else None
    except Exception:
        return None
    if d is None or w is None:
        return None
    return d, w


def rotation_baseline(pairs: list[tuple[str, str]],
                      rotations: int = ROTATIONS) -> dict[str, float]:
    """Agreement expected by chance, holding both label distributions fixed.

    Rotating rather than shuffling is deliberate and is the same choice
    `gamma_regime_backtest._rotation_p` makes: a rotation is a permutation that
    preserves the exact multiset of labels on each side, so the baseline it
    produces is the base rate and nothing else.
    """
    n = len(pairs)
    if n < 2:
        return {"zone": float("nan"), "side": float("nan")}
    dailies = [p[0] for p in pairs]
    weeklies = [p[1] for p in pairs]
    z_hits, s_hits, trials = 0, 0, 0
    for k in range(1, min(rotations, n - 1) + 1):
        rotated = weeklies[k:] + weeklies[:k]
        for d, w in zip(dailies, rotated):
            z_hits += (d == w)
            s_hits += (side(d) == side(w))
            trials += 1
    if not trials:
        return {"zone": float("nan"), "side": float("nan")}
    return {"zone": 100.0 * z_hits / trials, "side": 100.0 * s_hits / trials}


def summarise(pairs: list[tuple[str, str]]) -> dict:
    n = len(pairs)
    out: dict = {"n": n}
    if not n:
        return out
    out["zone_pct"] = 100.0 * sum(1 for d, w in pairs if d == w) / n
    out["side_pct"] = 100.0 * sum(1 for d, w in pairs if side(d) == side(w)) / n
    out["opposite_pct"] = 100.0 * sum(
        1 for d, w in pairs
        if {side(d), side(w)} == {"ABOVE", "BELOW"}) / n
    out["pairs"] = Counter(pairs)
    out["daily_dist"] = Counter(d for d, _ in pairs)
    out["weekly_dist"] = Counter(w for _, w in pairs)
    base = rotation_baseline(pairs)
    out["base_zone"] = base["zone"]
    out["base_side"] = base["side"]
    out["lift_zone"] = out["zone_pct"] - base["zone"]
    out["lift_side"] = out["side_pct"] - base["side"]
    return out


def verdict(s: dict) -> tuple[str, str, str]:
    """(band, contradiction flag, sentence). Thresholds are the ones above."""
    if s.get("n", 0) < 30:
        return ("INCONCLUSIVE", "—",
                f"{s.get('n', 0)} names is too few to count")
    sp = s["side_pct"]
    if sp >= COSMETIC_PCT:
        band = "COSMETIC"
        why = (f"daily and weekly put the name on the same side of the pivot "
               f"{sp:.1f}% of the time — the second column is close to free, "
               f"and B-96 can add three more without confusing anyone")
    elif sp >= NARROW_PCT:
        band = "REAL BUT NARROW"
        why = (f"side agrees {sp:.1f}% of the time — the split is visible but "
               f"most readers take away the same direction")
    else:
        band = "TWO DIFFERENT READINGS"
        why = (f"side agrees only {sp:.1f}% of the time — daily and weekly are "
               f"describing different things, and B-96 must say which governs "
               f"rather than printing five peers")
    contra = ("CONTRADICTION" if s["opposite_pct"] >= CONTRADICTION_PCT
              else "no")
    return band, contra, why


# ══ ROBUSTNESS CHECK — added 2026-09-19, AFTER the primary run ═══════════════
#
# Declared as post-hoc, because it is. The primary run is a ONE-DATE
# cross-section (the design above, unchanged), and its label distribution came
# back badly skewed: 50% of names at `R1` on daily against 40% at `PP-S1` on
# weekly. That is exactly what a snapshot taken three sessions into a bounce off
# a seven-week decline would look like — price above yesterday's pivot and below
# last week's — which would inflate disagreement by construction rather than
# because the two columns mean different things.
#
# B-74r is the precedent: "does the demotion hold across eras?" is a question
# the desk asks of its own findings. This re-runs the identical statistic on
# past as-of dates by truncating the same frames, so nothing new is downloaded
# and nothing in the design moves. The primary number is NOT restated by it.
def as_of_pairs(hist: dict, syms: list[str], asof, days: int
                ) -> list[tuple[str, str]]:
    """The same read, with every frame truncated to `asof`."""
    out = []
    for sym in syms:
        df = hist.get(sym)
        if df is None or len(df) < 60:
            continue
        df = df.rename(columns={c: c.lower() for c in df.columns})
        cut = df[df.index <= asof]
        if len(cut) < 60:
            continue
        p = read_pair(cut.tail(days))
        if p is not None:
            out.append(p)
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(
        description="B-97 · do pivot_d and pivot_w agree?")
    ap.add_argument("--symbols", type=int, default=500)
    ap.add_argument("--days", type=int, default=800)
    ap.add_argument("--across-dates", type=int, default=0, metavar="N",
                    help="post-hoc robustness check: re-run the same statistic "
                         "on N past month-end dates (see the ROBUSTNESS block)")
    a = ap.parse_args()

    import nse_universe as nu
    import trending_stocks as ts

    syms = list(nu.symbols("nifty500"))[:a.symbols]
    # One batched download rather than N round trips — the same downloader the
    # sector pages and the breadth strip use.
    hist = ts._batch_history(syms, period="3y")

    pairs: list[tuple[str, str]] = []
    excluded = 0
    for sym in syms:
        df = hist.get(sym)
        if df is None or len(df) < 60:
            excluded += 1
            continue
        df = df.rename(columns={c: c.lower() for c in df.columns})
        p = read_pair(df.tail(a.days))
        if p is None:
            excluded += 1
            continue
        pairs.append(p)

    s = summarise(pairs)
    if not s.get("n"):
        print("No name produced both reads — nothing to report.")
        return 1

    print(f"\nB-97 · pivot_d vs pivot_w — {s['n']} names read on both "
          f"timeframes ({excluded} excluded, could not produce both)\n")
    print(f"  zone agreement (7 labels)   {s['zone_pct']:>6.1f}%   "
          f"chance {s['base_zone']:.1f}%   lift {s['lift_zone']:+.1f}")
    print(f"  SIDE agreement (of pivot)   {s['side_pct']:>6.1f}%   "
          f"chance {s['base_side']:.1f}%   lift {s['lift_side']:+.1f}")
    print(f"  opposite sides              {s['opposite_pct']:>6.1f}%")

    print("\n  Label distribution (daily / weekly):")
    labels = sorted(set(s["daily_dist"]) | set(s["weekly_dist"]))
    for lab in labels:
        print(f"    {lab:<12} {s['daily_dist'].get(lab, 0):>4} / "
              f"{s['weekly_dist'].get(lab, 0):>4}")

    print("\n  Most common disagreements (daily -> weekly):")
    for (pd_, pw), k in s["pairs"].most_common(20):
        if pd_ == pw:
            continue
        print(f"    {pd_:<12} -> {pw:<12} {k:>4}  ({100.0 * k / s['n']:.1f}%)")

    band, contra, why = verdict(s)
    print(f"\nVERDICT: {band}   ·   opposite-side flag: {contra}\n  {why}")

    if a.across_dates:
        import pandas as pd
        print(f"\n── ROBUSTNESS (post-hoc): the same statistic on "
              f"{a.across_dates} past month-ends ──")
        print(f"{'as-of':<12} {'n':>4} {'zone%':>7} {'side%':>7} "
              f"{'opp%':>7} {'lift(side)':>11}")
        anchor = max(df.index.max() for df in hist.values() if df is not None)
        dates = pd.date_range(end=anchor, periods=a.across_dates + 1,
                              freq="ME")[:-1]
        rows = []
        for d in dates:
            ps = as_of_pairs(hist, syms, d, a.days)
            if len(ps) < 30:
                continue
            si = summarise(ps)
            rows.append(si)
            print(f"{d.date()!s:<12} {si['n']:>4} {si['zone_pct']:>6.1f}% "
                  f"{si['side_pct']:>6.1f}% {si['opposite_pct']:>6.1f}% "
                  f"{si['lift_side']:>+10.1f}")
        if rows:
            sides = sorted(r["side_pct"] for r in rows)
            opps = sorted(r["opposite_pct"] for r in rows)
            mid = len(sides) // 2
            print(f"\n  median side agreement {sides[mid]:.1f}%  "
                  f"(range {sides[0]:.1f}–{sides[-1]:.1f})")
            print(f"  median opposite       {opps[mid]:.1f}%  "
                  f"(range {opps[0]:.1f}–{opps[-1]:.1f})")
            print(f"  the primary run reads {s['side_pct']:.1f}% side / "
                  f"{s['opposite_pct']:.1f}% opposite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
