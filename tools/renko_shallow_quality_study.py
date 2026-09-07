#!/usr/bin/env python3
"""renko_shallow_quality_study.py — B-57: the shallow-correction flip on quality names.

Runs the test pre-registered in `analyses/Open-Backlog.md` §B-57, committed at
`04f35f0` and amended at `36c09a0` BEFORE this scorer existed. Nothing here may
change the design; if something has to change, the entry changes first and says
why.

Scored through the SAME harness as B-43/B-43r (`renko_regime_study._panel`-shaped
panel, `_edge`, `_rotation_p`), so "shallow flip on quality names" and "flip in a
trend" are directly comparable rather than two differently-built numbers.

══ WHAT IS BEING TESTED, AND WHY IT IS NOT JUST B-43r AGAIN ═════════════════════

B-43 measured the bare Renko flip at a clean null; B-43r measured it at −1.01%
(p_rot=0.000) against an ADX-matched baseline, and explained the sign: an up-flip
requires price to have first fallen enough to print down bricks, so it selects the
moment after a counter-move, and holding beat re-entering.

`renko_quality_cardinality.py` then showed the owner's proposed 40% correction cap
is not a filter — 96% of flips clear it — and that its median `bricks_in_prior`=3
lands on B-43r's WORST bucket. What is uncovered is the tight end: at ≤10% the
median event carries `bricks_in_prior`=1. If B-43r's mechanism is right, a shallow
pullback gives back little of the run, so the penalty should shrink. Whether it
shrinks past zero is the question.

══ PRE-REGISTERED DESIGN (mirrored from the backlog entry; do not edit here) ═════

  PRIMARY (the only arm that decides anything)
    signal    flip_up with depth_from_peak <= 10%, on a name whose point-in-time
              quality gate passes AT THE FLIP DATE
    baseline  bars in the SAME quality-passing names that are ALSO within 10% of
              their trailing 120d high -- the same state, minus the flip
    horizon   20 trading days, entry at the next open
    statistic mean(signal) - mean(baseline), in percent
    p-value   circular rotation (Welch invalid: overlapping windows, cross-
              sectional correlation)
    PASS BAR  edge > 0 AND p_rot < 0.05

  CONTROL 1 · directional   flip_dn in the SAME state (quality, drawdown <= 10%),
              scored as a long. Note "identical filters" means the identical
              STATE MASK, not an identical depth condition: `depth_from_peak`
              means "how far did it fall before turning back up", which has no
              coherent reading for a flip in the other direction, so inventing
              one to make the arms look symmetric would be worse than the gap.
              B-43r's down leg was a clean null (p=0.331). If this lights up, the
              filters are selecting the dip state rather than the flip.
  CONTROL 2 · depth inversion   flip_up with depth_from_peak >= 25%, baselined on
              bars >= 25% below their trailing high. PRE-REGISTERED EXPECTATION:
              NEGATIVE, reproducing B-43r. A positive here means the harness
              disagrees with a settled result and must be debugged, not reported.

  STATE CONTRAST (reported, never decisive)
    The same signal against an UNFILTERED baseline of every bar in the quality
    universe. The gap between it and the primary is the size of the illusion --
    the number a careless version of this test would have published.

  ABORT   fewer than 200 signal events => INCONCLUSIVE - UNDERPOWERED, not a null.

══ THE TWO THINGS MOST LIKELY TO FOOL THIS STUDY ════════════════════════════════

1. **An unmatched baseline.** Compare shallow-dip flips against every bar and a
   positive edge is nearly free: shallow dips in growing companies resolve upward
   often enough on their own, and quality names drifted up over this window. That
   measures the state and the quality screen, then credits the flip. Hence the
   state-matched baseline. This is the rule B-43r and B-44r were both written to
   enforce: FILTER THE BASELINE WITH WHATEVER YOU FILTER THE SIGNAL.

2. **Lookahead through the fundamentals.** Handled by `point_in_time_quality`,
   which will not report a fiscal year before `period_end + 60d`. The residual --
   restatements, and a universe of today's listed names -- is unfixable on free
   data and makes every number here an UPPER BOUND.

Baseline bars INCLUDE the event bars, matching B-43r's `_edge`. With a few hundred
events among tens of thousands of state bars the contamination is negligible, and
diverging from B-43r's construction would break the comparison this study exists
to make.

CLI:
    py -3 tools/renko_shallow_quality_study.py                 # full run
    py -3 tools/renko_shallow_quality_study.py --quality-only  # fetch statements
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np

import fundamentals_deep as fd
import point_in_time_quality as pit
import renko_quality_cardinality as card
import renko_regime_study as reg

HERE = Path(__file__).resolve().parent
CACHE = card.CACHE

WARMUP = card.WARMUP

# ── pre-registered constants. Changing one changes the study. ────────────────
HORIZON = 20            #: trading days, entry next open
SHALLOW_CAP = 10.0      #: %, the primary's correction cap
DEEP_FLOOR = 25.0       #: %, control 2's inversion band
PEAK_LOOKBACK = 120     #: bars, the trailing high the baseline state is measured from
MIN_EVENTS = 200        #: below this the result is UNDERPOWERED, not null

#: The gate's growth span, FIXED at 2 years. yfinance serves only four annual
#: columns, so leaving this at 3 would measure a 2y span early in the window and a
#: 3y span late -- a gate whose definition changes mid-sample. See B-57's amendment.
QUALITY_WINDOW_YEARS = 2

#: Earliest date at which three fiscal years have been published for a March-FY
#: company, given the 60-day filing lag. Events before this are unevaluable, not
#: failures, and the window truncates here rather than silently thinning.
WINDOW_START = dt.date(2025, 5, 30)


# ── quality, evaluated per publication regime rather than per bar ────────────

def quality_timeline(symbol: str, dates: list[dt.date]) -> np.ndarray:
    """Boolean per bar: did the point-in-time gate PASS on that date?

    Evaluated once per publication regime, not once per bar. The gate's answer can
    only change when a new fiscal year becomes public, so 500 bars need at most a
    handful of evaluations -- and doing it per bar would make the study's runtime
    a function of its bar count for no additional truth.

    UNKNOWN (too few published years) maps to False HERE, because a bar the gate
    cannot evaluate must not enter the signal or the baseline. That is exclusion,
    not failure; `quality_as_of` keeps the three-state distinction intact and the
    run report counts the exclusions separately.
    """
    stmts = pit.cached_statements(symbol)
    out = np.zeros(len(dates), bool)
    if not stmts:
        return out
    cache: dict[str, bool] = {}
    for i, d in enumerate(dates):
        # The regime key is the newest fiscal year public on this date.
        key = None
        for end, _ in pit.series_with_dates(stmts.get("income"), fd._REVENUE):
            if end + dt.timedelta(days=pit.LAG_DAYS) <= d:
                key = end.isoformat()
                break
        if key is None:
            continue
        if key not in cache:
            r = pit.quality_as_of(stmts, d, min_years=3,
                                  window=QUALITY_WINDOW_YEARS)
            cache[key] = bool(r["verdict"] is True)
        out[i] = cache[key]
    return out


# ── panel ────────────────────────────────────────────────────────────────────

def build_panel(paths: list[Path], horizon: int = HORIZON) -> list[dict[str, Any]]:
    """Per symbol: forward returns, the flip vectors WITH their correction depth,
    the trailing-high drawdown state, and the point-in-time quality mask."""
    panel: list[dict[str, Any]] = []
    for p in paths:
        doc = json.loads(p.read_text(encoding="utf-8"))
        bars = doc["bars"]
        m = len(bars)
        if m < WARMUP + horizon + 3:
            continue
        sym = doc["symbol"]
        o = np.array([b["open"] for b in bars], float)
        h = np.array([b["high"] for b in bars], float)
        c = np.array([b["close"] for b in bars], float)
        dates = [dt.date.fromtimestamp(b["time"]) for b in bars]

        fwd = np.full(m, np.nan)
        last = m - horizon - 2
        for t in range(WARMUP, last + 1):
            if o[t + 1] > 0:
                fwd[t] = (c[t + 1 + horizon] / o[t + 1] - 1.0) * 100.0

        # Drawdown from the trailing high — the STATE the baseline is drawn from.
        dd = np.full(m, np.nan)
        for t in range(PEAK_LOOKBACK, m):
            pk = h[t - PEAK_LOOKBACK:t + 1].max()
            if pk > 0:
                dd[t] = (pk - c[t]) / pk * 100.0

        up = np.zeros(m, bool)
        dn = np.zeros(m, bool)
        depth = np.full(m, np.nan)
        for e in card.flip_events_raw(p):
            t = e["index"]
            if WARMUP <= t <= last:
                (up if e["dir"] == 1 else dn)[t] = True
                depth[t] = e["depth_from_peak"]

        in_window = np.array([d >= WINDOW_START for d in dates], bool)
        qual = quality_timeline(sym, dates)

        panel.append({"sym": sym, "fwd": fwd, "dd": dd, "up": up, "dn": dn,
                      "depth": depth, "qual": qual, "win": in_window,
                      "lo": WARMUP, "hi": last})
    return panel


# ── arms ─────────────────────────────────────────────────────────────────────

def _shallow_mask(d):
    """Quality names, in a shallow drawdown, inside the evaluable window."""
    return d["qual"] & d["win"] & np.isfinite(d["dd"]) & (d["dd"] <= SHALLOW_CAP)


def _deep_mask(d):
    return d["qual"] & d["win"] & np.isfinite(d["dd"]) & (d["dd"] >= DEEP_FLOOR)


def _unfiltered_mask(d):
    """STATE CONTRAST: quality universe, any state. Never decisive."""
    return d["qual"] & d["win"]


def _all_bars_mask(d):
    """HARNESS CHECK: every bar in the window, no quality and no state filter.

    Added 2026-09-07 under the pre-registration's own debug clause, after CONTROL2
    came back POSITIVE where a negative was pre-registered. The clause says a
    misbehaving control means the harness must be debugged rather than the result
    reported, and the way to test a harness is to point it at a settled number:
    the bare flip against an unconditional baseline is B-43, which measured a
    clean null (-0.02%). If this panel reproduces that, the machinery agrees with
    the study it extends and CONTROL2's sign is a property of the deep-drawdown
    SAMPLE, not of the scorer.
    """
    return d["win"] & np.isfinite(d["dd"])


def _event(d, key, lo=None, hi=None):
    ev = d[key] & np.isfinite(d["depth"])
    if lo is not None:
        ev = ev & (d["depth"] >= lo)
    if hi is not None:
        ev = ev & (d["depth"] <= hi)
    return ev


def _arm(panel, ev_fn, mask_fn):
    """Edge + rotation p for one arm, with the event vector materialised.

    `renko_regime_study._edge` takes an event KEY; these arms are computed
    (depth-banded) rather than stored, so each is written into the panel under a
    scratch key and the shared scorer is called on that. Reusing the scorer beats
    re-deriving pooled means that must match B-43r's to the decimal.
    """
    for d in panel:
        d["_ev"] = ev_fn(d)
    r = reg._edge(panel, "_ev", mask_fn)
    if r is None:
        return None, None, 0
    p, nrot = reg._rotation_p(panel, "_ev", mask_fn, r["edge"])
    return r, p, nrot


def main() -> int:
    ap = argparse.ArgumentParser(description="B-57 · shallow flip on quality names")
    ap.add_argument("--universe", type=int, default=500)
    ap.add_argument("--horizon", type=int, default=HORIZON)
    ap.add_argument("--quality-only", action="store_true",
                    help="fetch and cache statements, then stop")
    args = ap.parse_args()

    syms, bhav_date = card.universe(args.universe)
    paths = [p for p in (CACHE / f"{s}_1d.json" for s in syms) if p.exists()]
    if not paths:
        sys.exit(f"no cached bars in {CACHE} — run renko_quality_cardinality.py first")

    if args.quality_only:
        for i, p in enumerate(paths, 1):
            sym = json.loads(p.read_text(encoding="utf-8"))["symbol"]
            pit.cached_statements(sym)
            if i % 25 == 0:
                print(f"  statements cached: {i}/{len(paths)}", file=sys.stderr)
        print("statements cached")
        return 0

    print(f"B-57 · shallow Renko flip on quality names   (bhavcopy {bhav_date})")
    print(f"universe {len(paths)} names · horizon {args.horizon}d · "
          f"window from {WINDOW_START} · quality span {QUALITY_WINDOW_YEARS}y "
          f"· lag {pit.LAG_DAYS}d")
    panel = build_panel(paths, args.horizon)
    if not panel:
        sys.exit("empty panel")

    n_qual_bars = int(sum(int((d["qual"] & d["win"]).sum()) for d in panel))
    n_qual_names = sum(1 for d in panel if (d["qual"] & d["win"]).any())
    print(f"quality-passing: {n_qual_names} names, {n_qual_bars} evaluable bars\n")

    arms = [
        ("PRIMARY  flip_up, depth<=10%, quality",
         lambda d: _event(d, "up", hi=SHALLOW_CAP), _shallow_mask, True),
        ("CONTROL1 flip_dn as long, same state",
         lambda d: d["dn"], _shallow_mask, False),
        ("CONTROL2 flip_up, depth>=25%, quality",
         lambda d: _event(d, "up", lo=DEEP_FLOOR), _deep_mask, False),
        ("CONTRAST flip_up<=10% vs ALL quality bars",
         lambda d: _event(d, "up", hi=SHALLOW_CAP), _unfiltered_mask, False),
        ("HARNESS   bare flip_up vs ALL bars (=B-43)",
         lambda d: d["up"], _all_bars_mask, False),
    ]

    primary = None
    for label, ev_fn, mask_fn, is_primary in arms:
        r, p, nrot = _arm(panel, ev_fn, mask_fn)
        print(reg._row(label, r, p, nrot))
        if is_primary:
            primary = (r, p)

    print()
    if primary is None or primary[0] is None:
        print("VERDICT: INCONCLUSIVE — the primary arm produced no scorable events.")
        return 0
    r, p = primary
    if r["n_sig"] < MIN_EVENTS:
        print(f"VERDICT: INCONCLUSIVE — UNDERPOWERED. {r['n_sig']} signal events, "
              f"pre-registered floor is {MIN_EVENTS}. This is NOT a null.")
        return 0
    passed = r["edge"] > 0 and p is not None and p < 0.05
    print(f"VERDICT: {'PASS' if passed else 'FAIL'} against the pre-registered bar "
          f"(edge > 0 AND p_rot < 0.05): edge={r['edge']:+.2f}%, "
          f"p_rot={'n/a' if p is None else f'{p:.3f}'}")
    if not passed:
        print("        B-43/B-43r stand. Renko stays a chart overlay labelled FLIP,")
        print("        and stays in PIPELINE_EXCLUDED.")
    print("\nLIMITS: today's listed liquid names (survivorship) => UPPER BOUND; "
          "restatements unfixable on free data;\n        rotation grid is coarse "
          "(every 3rd offset), so p is indicative, not exact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
