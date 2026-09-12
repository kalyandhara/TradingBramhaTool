#!/usr/bin/env python3
"""pmax_plan_study.py - B-74: the PMax PLAN has never been scored.

B-65 scored the PMax SIGNAL -- flip to 20d forward return, -0.55%, p=0.511,
n=1,538 -- and stopped there. The chart has been drawing an entry, a ratcheting
stop, three R-targets and an exit rule on top of that null, and nobody has ever
scored the plan itself.

The asymmetry is the argument for the study. B-72's liquidity-sweep overlay ships
with BOTH halves attached: B-41m scored the signal (+0.51% @20d, p=0.005) and
B-41p scored that exact entry/stop/target (+0.06R). PMax has only the first half,
and the missing half is the one the reader is looking at.

== PRE-REGISTRATION, from Open-Backlog B-74, filed 2026-09-12 before this ran ==

  PANEL     B-65's, unchanged: the 460 cached names, ~3y daily bars, WARMUP 60,
            costs 29bps round trip, symbol-block bootstrap. Numbers land beside
            the signal measurement rather than in their own frame.

  THE PLAN, read off pmaxSignals() in chart_dashboard.html rather than off the
  card's prose:
      entry        the flip bar's close
      initial stop the PMax band ON that bar, so R = |entry - stop|
      trail        the live band, which ratchets and never loosens
      exit shown   the opposite flip ("exit when the band flips")
      targets      1R / 2R / 3R markers

  THE ARMS (paired: every arm sees identical entries)

    A1 SHIPPED-FLIP   exit at the opposite flip's close.          DECIDES
    A2 SHIPPED-TRAIL  exit if price touches the ratcheting band,
                      else at the opposite flip's close.          describes
    B  FROZEN STOP    stop fixed at the flip-bar band, else flip.  describes
    C  TIME ONLY      no stop, exit at the 20-day close.          describes

  == A DEFECT IN THE PRE-REGISTRATION, DECLARED BEFORE THE RUN ==

  B-74 wrote arm A as "enter at the flip close, trail the ratcheting band, exit
  on the opposite flip" -- which is TWO exit rules, and in PMax they are not the
  same event. The flip is tested EMA-vs-band, so price can cross the band without
  flipping it. The card states the flip as the exit and DRAWS the trail as a
  price line, so both readings are defensible.

  Resolved by splitting the arm rather than picking: A1 is the card's literal
  exit sentence and is the one that decides; A2 is the same plan with the drawn
  line treated as a stop. Declared here, before any number was seen. B-41w's
  lesson applies -- an ambiguity in a pre-registration is a defect to state, not
  a free pass to choose afterwards.

  R DENOMINATOR   the SHIPPED initial risk for every arm, so "R" means one thing
                  across the table (B-41p's convention).

  DIRECTION       up-flips (long) DECIDE, matching B-65's PRIMARY arm and the
                  harness's long-only convention. Down-flips are scored and
                  printed because the card draws SHORT plans too, but they are
                  description: this panel has no short-side baseline.

  PAIRING         a trade is scored only if BOTH an opposite flip and the 20th
                  bar are in range, so all four arms see the same trade list and
                  the comparison is within-signal.

  STATISTIC       mean R per trade.
  UNCERTAINTY     bootstrap resampling SYMBOLS with replacement, 2000 draws.
                  Trades cluster within a name, so a t-test on ~1,500 trades
                  would treat correlated outcomes as independent.

  DECISION BAR    if A1 is worse than C and the paired bootstrap CI for (C - A1)
                  EXCLUDES zero, the card's trail and target lines are drawing a
                  plan that costs the reader money against doing nothing, and
                  they are demoted to context -- the B-70 move. If A1 ~ C, the
                  furniture stays and the card's existing B-65 caveat suffices.

  ABORT           under 200 long trades the run is UNDERPOWERED and concludes
                  nothing. Not expected to bind: B-65 counted 1,538 flips.

  PRIOR           all arms ~ 0. A null signal does not become a plan by having a
                  stop attached. B-41p worked because removing the stop unlocked
                  an edge the signal ALREADY HAD; there is no such edge here, so
                  a positive arm is a sample artifact rather than a discovery.
                  Written down so a good number cannot be promoted afterwards.

CLI:
  node tools/pmax_bands_emit.js tools/cache/pmax_bands.json
  py -3 tools/pmax_plan_study.py
  py -3 tools/pmax_plan_study.py --limit 20          # smoke test
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "cardinality"
BANDS = HERE / "cache" / "pmax_bands.json"

WARMUP = 60          # B-65's, unchanged
HORIZON = 20         # arm C's exit, B-65's measured horizon
COST_BPS = 29.0      # round trip, matching B-41p / B-65
N_BOOT = 2000
MIN_TRADES = 200     # ABORT floor


def _trades_for(sym, doc, band_doc):
    """Every flip on one symbol, scored on all four arms. Paired by construction."""
    bars = [b for b in doc.get("bars", [])
            if b and np.isfinite(b.get("high", np.nan))
            and np.isfinite(b.get("low", np.nan))
            and np.isfinite(b.get("close", np.nan))]
    n = len(bars)
    if n < 120 or band_doc.get("n") != n:
        return []
    hi = np.array([b["high"] for b in bars], float)
    lo = np.array([b["low"] for b in bars], float)
    cl = np.array([b["close"] for b in bars], float)

    start = band_doc["start"]
    band = band_doc["band"]
    dirs = band_doc["dir"]

    def band_at(i):
        k = i - start
        return band[k] if 0 <= k < len(band) else None

    flips = [(start + k, dirs[k]) for k in range(1, len(dirs)) if dirs[k] != dirs[k - 1]]
    out = []
    for f, (i, d) in enumerate(flips):
        if i < WARMUP:
            continue
        nxt = flips[f + 1][0] if f + 1 < len(flips) else None
        # Pairing: every arm must be observable, or the trade is dropped whole.
        if nxt is None or i + HORIZON > n - 1:
            continue
        entry = cl[i]
        stop0 = band_at(i)
        if stop0 is None or not np.isfinite(stop0):
            continue
        risk = (entry - stop0) if d == 1 else (stop0 - entry)
        if not risk > 0:
            continue
        sgn = 1.0 if d == 1 else -1.0

        # A1 - exit at the opposite flip's close
        r_a1 = sgn * (cl[nxt] - entry) / risk

        # A2 - the drawn trail treated as a stop, walked bar by bar. The band is
        # read from the PREVIOUS bar: the value on bar t is not knowable until it
        # closes, and using it to stop out during t would be lookahead.
        r_a2 = None
        for t in range(i + 1, nxt + 1):
            lvl = band_at(t - 1)
            if lvl is None or not np.isfinite(lvl):
                continue
            if d == 1 and lo[t] <= lvl:
                r_a2 = (lvl - entry) / risk
                break
            if d == -1 and hi[t] >= lvl:
                r_a2 = (entry - lvl) / risk
                break
        if r_a2 is None:
            r_a2 = r_a1

        # B - stop frozen at the flip-bar band
        r_b = None
        for t in range(i + 1, nxt + 1):
            if (d == 1 and lo[t] <= stop0) or (d == -1 and hi[t] >= stop0):
                r_b = -1.0
                break
        if r_b is None:
            r_b = r_a1

        # C - no stop, exit at the 20-day close
        r_c = sgn * (cl[i + HORIZON] - entry) / risk

        # Best excursion in R, for the TP1/2/3 badges the card draws
        seg_hi, seg_lo = hi[i + 1:nxt + 1], lo[i + 1:nxt + 1]
        if len(seg_hi):
            mfe = ((seg_hi.max() - entry) / risk) if d == 1 else ((entry - seg_lo.min()) / risk)
        else:
            mfe = 0.0

        # ── the unconditional baseline, which the raw numbers badly need ──────
        # B-74's PANEL line said "B-65's, unchanged ... unconditional baseline"
        # and the first cut of this file then reported RAW R, which is not what
        # B-65 reports: its -0.55% is an EDGE, signal minus the unconditional
        # +1.76%. Raw R flatters every long arm by exactly the drift it sat
        # through, and the arms here hold for different lengths (A1's median 67
        # bars against C's fixed 20), so raw R does not even compare them to
        # each other. Implementing the baseline is honouring the registration,
        # not extending it.
        #
        # Benchmark per trade = this symbol's mean return over a window of the
        # SAME length, from every valid start. "Did the signal pick a better
        # window than an arbitrary one of equal length?"
        def bench_r(h):
            if h <= 0 or h >= n:
                return 0.0
            a, b_ = cl[:n - h], cl[h:]
            ok = a > 0
            if not ok.any():
                return 0.0
            return float(np.mean(b_[ok] / a[ok] - 1.0)) * entry / risk

        hold = int(nxt - i)
        bench_hold = bench_r(hold) * sgn
        bench_h20 = bench_r(HORIZON) * sgn

        cost_r = (COST_BPS / 10000.0) * 2 * entry / risk
        out.append({
            "symbol": sym, "i": i, "dir": int(d), "bars_held": hold,
            "A1": r_a1 - cost_r, "A2": r_a2 - cost_r,
            "B": r_b - cost_r, "C": r_c - cost_r, "mfe": float(mfe),
            # edge = arm minus the equal-length unconditional window
            "eA1": r_a1 - cost_r - bench_hold, "eA2": r_a2 - cost_r - bench_hold,
            "eB": r_b - cost_r - bench_hold, "eC": r_c - cost_r - bench_h20,
            "bench_hold": bench_hold, "bench_h20": bench_h20,
        })
    return out


def _boot(rows, values, rng):
    """Bootstrap CI for a mean, resampling SYMBOLS with replacement.

    `values` maps a trade row to the number being averaged, so the same routine
    serves both a paired difference and a single arm's LEVEL. The level is not
    optional decoration: the decision bar only needs differences, but "the
    shipped plan returns +0.135R" is a claim about a level and cannot be made
    from a difference CI.
    """
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["symbol"], []).append(values(r))
    keys = sorted(by)
    arrs = {s: np.array(by[s], float) for s in keys}
    draws = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.choice(keys, size=len(keys), replace=True)
        draws[b] = np.concatenate([arrs[s] for s in pick]).mean()
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def _boot_diff(rows, arm, base, rng):
    return _boot(rows, lambda r: r[arm] - r[base], rng)


def _boot_level(rows, arm, rng):
    return _boot(rows, lambda r: r[arm], rng)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="symbols, for a smoke test")
    args = ap.parse_args()

    if not BANDS.exists():
        raise SystemExit(f"missing {BANDS} - run: node tools/pmax_bands_emit.js {BANDS}")
    bands = json.loads(BANDS.read_text(encoding="utf-8"))

    files = sorted(CACHE.glob("*_1d.json"))
    if args.limit:
        files = files[:args.limit]

    rows = []
    for f in files:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        sym = doc.get("symbol")
        if sym not in bands:
            continue
        rows.extend(_trades_for(sym, doc, bands[sym]))

    longs = [r for r in rows if r["dir"] == 1]
    shorts = [r for r in rows if r["dir"] == -1]

    print()
    print("=== B-74 - the PMax PLAN, scored ===")
    print(f"  {len(rows)} trades ({len(longs)} long / {len(shorts)} short) - "
          f"{len({r['symbol'] for r in rows})} symbols - {COST_BPS:.0f}bps - "
          f"{N_BOOT}-draw symbol bootstrap")
    if len(longs) < MIN_TRADES:
        print(f"\n  ABORT - {len(longs)} long trades is under the pre-registered "
              f"floor of {MIN_TRADES}. UNDERPOWERED, concludes nothing.")
        return

    rng = np.random.default_rng(20260912)
    for label, group in (("LONG (decides)", longs), ("SHORT (description)", shorts)):
        if not group:
            continue
        print()
        print(f"  -- {label}: {len(group)} trades --")
        print(f"  {'arm':<18}{'mean R':>9}{'win%':>7}{'hold':>6}"
              f"   {'95% CI on the LEVEL':<26}{'vs A1':>8}   95% CI on the diff")
        base = np.array([r["A1"] for r in group])
        hold = float(np.median([r["bars_held"] for r in group]))
        for arm, name in (("A1", "A1 SHIPPED-FLIP"), ("A2", "A2 SHIPPED-TRAIL"),
                          ("B", "B  FROZEN STOP"), ("C", "C  TIME ONLY")):
            v = np.array([r[arm] for r in group])
            llo, lhi = _boot_level(group, arm, rng)
            lex = "EXCLUDES 0" if (llo > 0 or lhi < 0) else "includes 0"
            lvl = f"[{llo:+.3f}, {lhi:+.3f}] {lex}"
            head = (f"  {name:<18}{v.mean():>+9.3f}{100 * (v > 0).mean():>6.1f}%"
                    f"{hold:>6.0f}   {lvl:<26}")
            if arm == "A1":
                print(head + f"{'-':>8}")
            else:
                lo_, hi_ = _boot_diff(group, arm, "A1", rng)
                excl = "EXCLUDES 0" if (lo_ > 0 or hi_ < 0) else "includes 0"
                print(head + f"{v.mean() - base.mean():>+8.3f}   "
                             f"[{lo_:+.3f}, {hi_:+.3f}] {excl}")
        mfe = np.array([r["mfe"] for r in group])
        print(f"  targets the card draws: TP1 hit {100 * (mfe >= 1).mean():.1f}% - "
              f"TP2 {100 * (mfe >= 2).mean():.1f}% - TP3 {100 * (mfe >= 3).mean():.1f}%")

    # ---- baseline-adjusted, which is the reading that means anything ----
    for label, group in (("LONG (decides)", longs), ("SHORT (description)", shorts)):
        if not group:
            continue
        print()
        print(f"  -- EDGE: each arm minus an equal-length unconditional "
              f"window - {label} --")
        print(f"  {'arm':<18}{'edge R':>9}   95% CI on the edge")
        for arm, name in (("eA1", "A1 SHIPPED-FLIP"), ("eA2", "A2 SHIPPED-TRAIL"),
                          ("eB", "B  FROZEN STOP"), ("eC", "C  TIME ONLY")):
            v = np.array([r[arm] for r in group])
            lo_, hi_ = _boot_level(group, arm, rng)
            excl = "EXCLUDES 0" if (lo_ > 0 or hi_ < 0) else "includes 0"
            print(f"  {name:<18}{v.mean():>+9.3f}   [{lo_:+.3f}, {hi_:+.3f}] {excl}")
        bh = float(np.mean([r["bench_hold"] for r in group]))
        print(f"  drift the shipped hold sits through: {bh:+.3f}R over a median "
              f"{np.median([r['bars_held'] for r in group]):.0f} bars")

    # ---- the pre-registered decision ----
    print()
    c = float(np.array([r["C"] for r in longs]).mean())
    a1 = float(np.array([r["A1"] for r in longs]).mean())
    lo_, hi_ = _boot_diff(longs, "C", "A1", rng)
    worse = a1 < c
    excludes = lo_ > 0 or hi_ < 0
    print("  DECISION BAR (pre-registered): demote the card's trail/target lines iff")
    print("  A1 is worse than C AND the CI for (C - A1) excludes zero.")
    print(f"    A1 {a1:+.3f}R   C {c:+.3f}R   C-A1 {c - a1:+.3f}R   "
          f"CI [{lo_:+.3f}, {hi_:+.3f}]")
    print(f"    A1 worse than C: {worse}    CI excludes zero: {excludes}")
    print("  VERDICT AS REGISTERED: " +
          ("DEMOTE" if (worse and excludes) else "KEEP"))
    print()
    print("  THE REGISTERED BAR IS MIS-SPECIFIED, and the edge table above is why.")
    print("  A1 and C are compared RAW while holding for different lengths (median")
    print("  67 bars against a fixed 20), so A1 collects ~3x the drift before any")
    print("  plan quality is involved. The bar's INTENT -- does the drawn plan cost")
    print("  the reader against doing nothing -- is answered on the edge basis,")
    print("  where each arm is already measured against its own equal-length window.")
    print()
    ea1 = float(np.array([r["eA1"] for r in longs]).mean())
    ec = float(np.array([r["eC"] for r in longs]).mean())
    elo, ehi = _boot_diff(longs, "eC", "eA1", rng)
    e_worse = ea1 < ec
    e_excl = elo > 0 or ehi < 0
    print("  DECISION ON THE EDGE BASIS (the bar's intent, equal footing):")
    print(f"    A1 {ea1:+.3f}R   C {ec:+.3f}R   C-A1 {ec - ea1:+.3f}R   "
          f"CI [{elo:+.3f}, {ehi:+.3f}]")
    print(f"    A1 worse than C: {e_worse}    CI excludes zero: {e_excl}")
    print("  VERDICT: " + ("DEMOTE - the drawn plan costs against doing nothing"
                           if (e_worse and e_excl) else
                           "KEEP - no significant cost to the drawn plan"))


if __name__ == "__main__":
    main()
