#!/usr/bin/env python3
"""pmax_edge.py — B-65: PMax has never been scored, and it carries a fifth of the sentiment index.

Runs the design pre-registered in `analyses/Open-Backlog.md` §B-65, committed at
`9e8430f` BEFORE this scorer existed. Nothing here may change the design; if
something has to change, the entry changes first and says why.

══ WHY THIS EXISTS ══════════════════════════════════════════════════════════════

B-59r scored both of the trailing-stop twins. PMax was deliberately left out of
that test (B-59 had already shown it is not interchangeable with either), and
that leaves it as the one member of the family with real authority in the desk
and no measurement behind it:

  * `W_PMAX_1H = 15` in `sentiment_index.py` -- 15% of the sentiment score
    (it was 20 of 100 when this was written; B-22 wired the PCR factor on
    2026-09-11 and the weights went to the roadmap's 25/20/20/15/20)
  * a named factor row in `market_verdict.py` (`pmax_nifty_1h`)
  * a live trade-state panel in `dashboard_app.py`, with stop and T1/T2/T3

Three surfaces, zero measurements.

══ SCOPE -- WHAT THIS DOES NOT SETTLE ═══════════════════════════════════════════

This scores PMax on DAILY EQUITY bars, because that is what the cached universe
holds and what makes the result comparable to B-43/B-59r. **The sentiment factor
is a different claim**: a direction STATE, on NIFTY, at 1H.

A null here does NOT retire `W_PMAX_1H`. What it does is remove the presumption
that the factor is safe because "PMax works", and make the 1H index version its
own owed measurement.

══ PRE-REGISTERED DESIGN (mirrored from the entry; do not edit here) ════════════

  Same panel, harness, universe and baseline as B-59r: 460 names, ~3y daily, 20d
  horizon, entry next open, unconditional baseline, costs cancel.

  PRIMARY   · flip         PMax up-flips, all of them.  PASS: edge > 0 AND p < 0.05
  SECONDARY · state        every bar where PMax dir == 1.  NOT DECISIVE -- see below
  CONTEXT   · lonely flip  PMax up-flips with NO PSAR up-flip within +-3 bars
  CONTEXT   · joint flip   PMax up-flips WITH a PSAR up-flip within +-3 bars

  The STATE arm is explicitly not decisive, and the reason is a confound this
  baseline cannot remove: in a window whose unconditional mean 20-day return is
  around +1.76%, ANY up-trend filter looks good simply by sitting out the falls.
  A positive state arm therefore measures "trend filter in a bull sample". That
  was written down before the run so a positive number could not be quietly
  promoted afterwards.

  The two CONTEXT arms exist because of B-59's oddest finding -- PMax and PSAR
  agree BELOW chance. Description only; no decision hangs on them.

  ABORT   any arm under 200 events is UNDERPOWERED and concludes nothing.

  PRIOR: skeptical on the flip, genuinely uncertain on the state. The flip is the
  fourth member of a family measuring -1.01% (Renko, B-43r), -0.77% (PSAR-only)
  and -1.00% (STAI-only). The one structural reason it might not share their fate
  is that PMax flips are rarer and slower -- it does not re-enter after every
  wobble.

══ WHERE THE NUMBERS COME FROM ══════════════════════════════════════════════════

Flips are NOT recomputed here. `psar_overlap.js --emit` produces them from the
`pmaxSeries` lifted out of `chart_dashboard.html` -- the same function the chart
draws -- and this file only scores them, through the same `renko_regime_study`
harness as B-43/B-57/B-58/B-59r.

CLI:
    node tools/psar_overlap.js --emit tools/cache/flip_vectors.json
    py -3 tools/pmax_edge.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

import renko_quality_cardinality as card
import renko_regime_study as reg

HERE = Path(__file__).resolve().parent
CACHE = card.CACHE
WARMUP = card.WARMUP
VECTORS = HERE / "cache" / "flip_vectors.json"

# ── pre-registered constants. Changing one changes the study. ────────────────
HORIZON = 20        #: trading days, entry next open
TOL = 3             #: bars, B-59's middle rung
MIN_EVENTS = 200    #: below this an arm is UNDERPOWERED and concludes nothing


def _has_near(bar: int, others: list[int], tol: int = TOL) -> bool:
    return any(abs(o - bar) <= tol for o in others)


def build_panel(vectors: dict, horizon: int = HORIZON) -> list[dict[str, Any]]:
    panel: list[dict[str, Any]] = []
    for sym, v in vectors.items():
        path = CACHE / f"{sym}_1d.json"
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        bars = doc["bars"]
        m = len(bars)
        if m < WARMUP + horizon + 3:
            continue
        o = np.array([b["open"] for b in bars], float)
        c = np.array([b["close"] for b in bars], float)

        fwd = np.full(m, np.nan)
        last = m - horizon - 2
        for t in range(WARMUP, last + 1):
            if o[t + 1] > 0:
                fwd[t] = (c[t + 1 + horizon] / o[t + 1] - 1.0) * 100.0

        pmax_all = sorted([(i, d) for i, d in v["pmax"]])
        m_up = [i for i, d in pmax_all if d == 1]
        p_up = [i for i, d in v["psar"] if d == 1]

        flip = np.zeros(m, bool)
        lonely = np.zeros(m, bool)
        joint = np.zeros(m, bool)
        for t in m_up:
            if not (WARMUP <= t <= last):
                continue
            flip[t] = True
            if _has_near(t, p_up):
                joint[t] = True
            else:
                lonely[t] = True

        # STATE: dir is constant between flips, so it reconstructs exactly from
        # the flip vector — no second implementation of pmaxSeries. Bars before
        # the FIRST flip are left out rather than guessed: the direction there is
        # whatever the series was seeded with, and seeding is not a reading.
        state = np.zeros(m, bool)
        if pmax_all:
            for k, (t, d) in enumerate(pmax_all):
                end = pmax_all[k + 1][0] if k + 1 < len(pmax_all) else m
                if d == 1:
                    state[t:end] = True

        allb = np.zeros(m, bool)
        allb[WARMUP:last + 1] = True
        state = state & allb

        panel.append({"sym": sym, "fwd": fwd, "flip": flip, "state": state,
                      "lonely": lonely, "joint": joint, "all": allb})
    return panel


def _all_mask(d):
    return d["all"]


def _arm(panel, key):
    r = reg._edge(panel, key, _all_mask)
    if r is None:
        return None, None, 0
    p, nrot = reg._rotation_p(panel, key, _all_mask, r["edge"])
    return r, p, nrot


def main() -> int:
    ap = argparse.ArgumentParser(description="B-65 - PMax scored for the first time")
    ap.add_argument("--vectors", default=str(VECTORS))
    ap.add_argument("--horizon", type=int, default=HORIZON)
    args = ap.parse_args()

    vpath = Path(args.vectors)
    if not vpath.exists():
        sys.exit(f"no flip vectors at {vpath}\n"
                 f"run: node tools/psar_overlap.js --emit {vpath}")
    vectors = json.loads(vpath.read_text(encoding="utf-8"))

    print("B-65 - PMax scored for the first time (daily equity bars, NOT the 1H sentiment factor)")
    print(f"{len(vectors)} names | horizon {args.horizon}d | long side only | "
          f"no costs (they cancel)")
    panel = build_panel(vectors, args.horizon)
    if not panel:
        sys.exit("empty panel")

    for label, key in [("PRIMARY   PMax up-flip", "flip"),
                       ("SECONDARY PMax state (dir=1)", "state"),
                       ("CONTEXT   lonely flip (no PSAR)", "lonely"),
                       ("CONTEXT   joint flip (with PSAR)", "joint")]:
        r, p, nrot = _arm(panel, key)
        print(reg._row(label, r, p, nrot))
        if key == "flip":
            primary = (r, p)
        if key == "state":
            secondary = (r, p)

    print()
    r, p = primary
    if r is None:
        print("VERDICT: INCONCLUSIVE - the primary arm produced no scorable events.")
        return 0
    if r["n_sig"] < MIN_EVENTS:
        print(f"VERDICT: INCONCLUSIVE - UNDERPOWERED. {r['n_sig']} flips, floor is "
              f"{MIN_EVENTS}. NOT a null.")
        return 0
    passed = r["edge"] > 0 and p is not None and p < 0.05
    print(f"VERDICT (flip): {'PASS' if passed else 'FAIL'} against the pre-registered bar "
          f"(edge > 0 AND p_rot < 0.05): edge={r['edge']:+.2f}%, "
          f"p_rot={'n/a' if p is None else f'{p:.3f}'}")

    sr, sp = secondary
    if sr is not None:
        print(f"\nSTATE arm, NOT decisive: {sr['edge']:+.2f}% "
              f"(p={'n/a' if sp is None else f'{sp:.3f}'}) on {sr['n_sig']} bars, "
              f"hit {sr['hit']:.1f}% vs {sr['hit_base']:.1f}%.")
        print("  Read it with the confound that was written down before the run: in a")
        print(f"  window whose unconditional mean 20d return is {sr['base']:+.2f}%, an")
        print("  up-trend filter looks good by sitting out the falls. This measures a")
        print("  trend filter in a bull sample, and cannot be promoted to an edge claim.")

    print("\nSCOPE: daily EQUITY bars. The sentiment factor is a direction STATE on")
    print("       NIFTY at 1H -- a different claim on a different instrument and")
    print("       timeframe. Nothing here retires W_PMAX_1H; it only removes the")
    print("       presumption that the factor is safe because PMax 'works', and makes")
    print("       the 1H index version its own owed measurement.")
    print("\nLIMITS: today's listed liquid names (survivorship) => UPPER BOUND; long")
    print("        side only; rotation grid is coarse, so p is indicative, not exact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
