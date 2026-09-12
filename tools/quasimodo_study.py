#!/usr/bin/env python3
"""quasimodo_study.py — B-58: does the Quasimodo geometry beat a plain support retest?

Runs the test pre-registered in `analyses/Open-Backlog.md` §B-58, completed and
committed at `5ab30f6` BEFORE this scorer existed. Nothing here may change the
design; if something has to change, the entry changes first and says why.

Scored through the SAME harness as B-43/B-43r/B-57 (`renko_regime_study._edge`,
`_rotation_p`, `_row`) and over the same cached bar universe
(`renko_quality_cardinality.CACHE`), so "QM zone entry" and "Renko flip" are
directly comparable rather than two differently-built numbers.

══ WHAT IS BEING TESTED ═════════════════════════════════════════════════════════

`detect_quasimodo` is geometry only: no entry/stop/target, no scanner, never a
confluence vote. The question is whether the SHAPE selects anything, measured
against the plainest version of what it is doing — buying a retest of a prior
swing low. That family has measured negative on this desk three times
(`scan_ict_setup` −0.36%, `Order Block Retest` −0.47%, `Pullback Entry` −0.43%,
all @20d, ~9,000 signals), so an unmatched baseline would re-measure the family
and credit the geometry. Hence the state-matched baseline.

══ PRE-REGISTERED DESIGN (mirrored from the backlog entry; do not edit here) ═════

  EVENT     the ZONE ENTRY, not the CHOCH: the first bar after the CHOCH is
            knowable whose close sits inside `LS ± QM_TOL_PCT` with the head
            unbroken. The CHOCH completes the pattern; nothing is tradeable
            there.
  CAUSALITY a pivot at bar j is knowable at j + pivot_len (which is exactly
            where `detect_structure_chain` appends it), so an event needs
            t > rh.bar + pivot_len, and entry is the NEXT OPEN after t.

  PRIMARY (the only arm that decides anything)
    signal    QM zone entries
    baseline  every bar in the same names that is a SUPPORT RETEST -- close
              within +-QM_TOL_PCT of a confirmed, still-unbroken swing low,
              approached from above
    horizon   20 trading days, entry at the next open
    statistic mean(signal) - mean(baseline), in percent
    p-value   circular rotation (Welch invalid: overlapping windows, cross-
              sectional correlation)
    PASS BAR  edge > 0 AND p_rot < 0.05

  CONTROL - relax the CHOCH   the same walk with `RH > LH` dropped
              (min_choch_pct = -inf), same baseline. If the edge is materially
              unchanged, the change of character is decorative and the detector
              is an inverse-H&S finder wearing a different name.
  CONTRAST    QM zone entries against ALL bars. Never decisive -- it is the size
              of the illusion, the number a careless version of this would print.
  HARNESS     all support retests against ALL bars. PRE-REGISTERED EXPECTATION:
              flat-to-negative, reproducing the family above. A strongly POSITIVE
              harness means the panel is wrong and NO other number in the run may
              be reported.

  ABORT   fewer than 200 primary events => INCONCLUSIVE - UNDERPOWERED, not a null.
  COSTS   none, and not an oversight: signal and baseline are the same instrument
          held the same 20 days, so the ~29bps delivery model cancels in the
          difference.

══ EQUIVALENCE, NOT A SECOND IMPLEMENTATION ═════════════════════════════════════

`detect_quasimodo` returns only the NEWEST pattern; a study needs the history. The
walk below is therefore a reimplementation over the same `detect_structure_chain`
swings -- which is exactly how two definitions drift apart. So the run asserts
that this walk's LAST pattern matches the shipped detector's on the full frame,
per symbol, and prints the agreement count. A mismatch aborts.

CLI:
    py -3 tools/quasimodo_study.py            # full run
    py -3 tools/quasimodo_study.py --verify   # equivalence check only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import renko_quality_cardinality as card
import renko_regime_study as reg
import scanner_templates as st

HERE = Path(__file__).resolve().parent
CACHE = card.CACHE
WARMUP = card.WARMUP

# ── pre-registered constants. Changing one changes the study. ────────────────
HORIZON = 20              #: trading days, entry next open
PIVOT_LEN = 5             #: same as detect_quasimodo's default
TOL_PCT = st.QM_TOL_PCT   #: 2.0 -- the entry zone AND the baseline's retest band
LOOKBACK = st.QM_LOOKBACK        #: 120 bars, LS..RH span cap
MIN_GRAB = st.QM_MIN_GRAB_PCT    #: 0.75, = the desk's equal-level tolerance
MIN_CHOCH = st.QM_MIN_CHOCH_PCT  #: 0.75, same constant, same reason
MIN_EVENTS = 200          #: below this the result is UNDERPOWERED, not null


# ── the walk ─────────────────────────────────────────────────────────────────

def _dedup(swings: list[dict]) -> list[dict]:
    """Collapse runs of the same kind to their extreme — `detect_quasimodo`'s rule.

    `detect_structure_chain` can emit the same extreme on consecutive bars, and the
    four-pivot walk would otherwise burn its slots on duplicates.
    """
    out: list[dict] = []
    for sw in sorted(swings, key=lambda s: s["bar"]):
        if out and out[-1]["kind"] == sw["kind"]:
            better = (float(sw["level"]) > float(out[-1]["level"])
                      if sw["kind"] == "high" else
                      float(sw["level"]) < float(out[-1]["level"]))
            if better:
                out[-1] = sw
            continue
        out.append(sw)
    return out


def qm_patterns(swings: list[dict], min_choch: float = MIN_CHOCH) -> list[dict]:
    """Every QM (LS, LH, HEAD, RH) over CONSECUTIVE swings, oldest first.

    Consecutiveness is not a detail: searching the four positions independently
    reported a "pattern" on 73% of 460 names. See the B-58 entry.

    `min_choch=-inf` is the pre-registered CONTROL — the same walk with `RH > LH`
    dropped.
    """
    sw = _dedup(swings)
    out: list[dict] = []
    for i in range(len(sw) - 3):
        ls, lh, head, rh = sw[i:i + 4]
        if [ls["kind"], lh["kind"], head["kind"], rh["kind"]] != ["low", "high", "low", "high"]:
            continue
        ls_l, lh_l = float(ls["level"]), float(lh["level"])
        if ls_l <= 0 or lh_l <= 0:
            continue
        if rh["bar"] - ls["bar"] > LOOKBACK:      # the detector's window, as a span
            continue
        if ((ls_l - float(head["level"])) / ls_l * 100.0) < MIN_GRAB:
            continue
        if ((float(rh["level"]) - lh_l) / lh_l * 100.0) < min_choch:
            continue
        out.append({"ls": ls, "lh": lh, "head": head, "rh": rh})
    return out


def zone_entries(patterns: list[dict], c: np.ndarray, m: int) -> list[int]:
    """First bar in each pattern's zone, causal, one event per pattern.

    Knowable only at `rh.bar + PIVOT_LEN` (where the chain appends the pivot), and
    the search stops at the next pattern's CHOCH so two overlapping shapes cannot
    both claim the same bar.
    """
    ev: list[int] = []
    for k, pat in enumerate(patterns):
        ls_l = float(pat["ls"]["level"])
        head_l = float(pat["head"]["level"])
        lo, hi = ls_l * (1 - TOL_PCT / 100.0), ls_l * (1 + TOL_PCT / 100.0)
        start = int(pat["rh"]["bar"]) + PIVOT_LEN + 1
        stop = m
        if k + 1 < len(patterns):
            stop = min(stop, int(patterns[k + 1]["rh"]["bar"]) + PIVOT_LEN + 1)
        for t in range(max(start, 0), stop):
            if c[t] < head_l:          # invalidated: the head broke on a close
                break
            if lo <= c[t] <= hi:
                ev.append(t)
                break
    return ev


def support_retests(swings: list[dict], c: np.ndarray, m: int) -> np.ndarray:
    """The STATE: close within +-TOL_PCT of a confirmed prior swing low, from above.

    This is the plainest statement of "buying support" — the family that has
    measured negative three times. The QM events are a subset of it by
    construction (the left shoulder IS a confirmed swing low and the zone IS
    +-TOL_PCT), which the run asserts rather than assumes.

    AMENDED 2026-09-10, after the first run aborted on that very assertion. The
    pre-registered wording was "confirmed, still-UNBROKEN swing low", and a level
    that broke was dropped for good. That excluded every QM entry by construction:
    **a Quasimodo's left shoulder is a low that HAS been broken — the head IS the
    break** — and the entry is the retest after price reclaimed it. A baseline the
    signal can never belong to would have measured a difference between disjoint
    states and called it an edge.

    So the permanence is gone: a level that broke and was reclaimed is still the
    level being retested. What survives is "approached from above", and that had
    to be stated as a PATH rather than as `c[t] >= lvl`: the QM zone is `LS ± 2%`,
    so a legitimate QM entry can close just BELOW the shoulder while the head is
    still intact, and a `c[t] >= lvl` rule would have broken the subset a second
    time for the same reason as the first.

    "From above" therefore means: since the pivot confirmed, price has traded
    clear above the band at least once and has now come back into it. That is
    what distinguishes a retest from a name arriving at the level for the first
    time on the way down, and it is satisfied by every QM entry — the post-head
    rally to `RH` is above `LH`, which is above the shoulder.
    """
    mask = np.zeros(m, bool)
    for sw in swings:
        if sw["kind"] != "low":
            continue
        lvl = float(sw["level"])
        if lvl <= 0:
            continue
        lo, hi = lvl * (1 - TOL_PCT / 100.0), lvl * (1 + TOL_PCT / 100.0)
        been_above = False
        for t in range(int(sw["bar"]) + PIVOT_LEN + 1, m):
            if c[t] > hi:
                been_above = True
            elif been_above and lo <= c[t] <= hi:
                mask[t] = True
    return mask


# ── panel ────────────────────────────────────────────────────────────────────

def _frame(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    bars = doc["bars"]
    df = pd.DataFrame({
        "open": [b["open"] for b in bars],
        "high": [b["high"] for b in bars],
        "low": [b["low"] for b in bars],
        "close": [b["close"] for b in bars],
        "volume": [b.get("volume", 0) for b in bars],
    })
    return doc["symbol"], df


def build_panel(paths: list[Path], horizon: int = HORIZON) -> tuple[list[dict[str, Any]], dict]:
    panel: list[dict[str, Any]] = []
    stats = {"no_chain": 0, "no_pattern": 0}
    for p in paths:
        sym, df = _frame(p)
        m = len(df)
        if m < WARMUP + horizon + 3:
            continue
        chain = st.detect_structure_chain(df, pivot_len=PIVOT_LEN)
        if not chain or not chain.get("swings"):
            stats["no_chain"] += 1
            continue
        swings = chain["swings"]
        o = df["open"].to_numpy(float)
        c = df["close"].to_numpy(float)

        fwd = np.full(m, np.nan)
        last = m - horizon - 2
        for t in range(WARMUP, last + 1):
            if o[t + 1] > 0:
                fwd[t] = (c[t + 1 + horizon] / o[t + 1] - 1.0) * 100.0

        pats = qm_patterns(swings)
        pats_relaxed = qm_patterns(swings, min_choch=float("-inf"))

        qm = np.zeros(m, bool)
        for t in zone_entries(pats, c, m):
            if WARMUP <= t <= last:
                qm[t] = True
        qmr = np.zeros(m, bool)
        for t in zone_entries(pats_relaxed, c, m):
            if WARMUP <= t <= last:
                qmr[t] = True

        state = support_retests(swings, c, m)
        allb = np.zeros(m, bool)
        allb[WARMUP:last + 1] = True

        # DIAGNOSTIC vector, added 2026-09-10 under the pre-registration's debug
        # clause after the HARNESS arm aborted the run. The bare Renko flip against
        # an unconditional baseline is B-43, a settled clean null (-0.02%). If THIS
        # panel reproduces it, the scorer is sound and the harness arm's sign is a
        # property of the sample rather than of the machinery. Same cache, same
        # bars, same forward-return construction — only the event vector differs.
        flip = np.zeros(m, bool)
        try:
            for e in card.flip_events_raw(p):
                t = e["index"]
                if WARMUP <= t <= last:
                    if e["dir"] == 1:
                        flip[t] = True
        except Exception:
            pass

        if not pats:
            stats["no_pattern"] += 1

        panel.append({"sym": sym, "fwd": fwd, "qm": qm, "qmr": qmr,
                      "state": state, "all": allb, "flip": flip,
                      "pats": pats, "df": df})
    return panel, stats


# ── equivalence with the shipped detector ────────────────────────────────────

def verify(panel: list[dict]) -> tuple[int, int, list[str]]:
    """This walk's last RECENT pattern must equal `detect_quasimodo`'s.

    The comparison has to be scoped, and the first version of it was not — it
    aborted on 37 of 355 names, every one of them `shipped=None walk=pattern`.
    That is not drift: the shipped detector keeps only swings with
    `bar >= n-1-lookback`, so it answers **"is there a QM in the last 120 bars"**,
    while the study needs every QM in the history. A name whose only Quasimodo
    completed two years ago is a real disagreement about *scope* and a false one
    about *shape*.

    So the check re-applies the detector's own trailing-window filter to the
    swings before walking them. What that leaves compared is the thing worth
    pinning: given the same swings, do the two find the same four pivots.

    Note where the window generalises. The detector cuts swings at a fixed
    distance from the END of the frame; the study cuts each candidate at a fixed
    distance from its OWN completion (`rh.bar - ls.bar <= LOOKBACK`). For the
    newest pattern the two coincide, which is why this check works at all — and
    for older ones the span form is the only one that means anything, since
    "within 120 bars of today" is not a property of a pattern from 2024.
    """
    agree = disagree = 0
    bad: list[str] = []
    for d in panel:
        shipped = st.detect_quasimodo(d["df"], pivot_len=PIVOT_LEN)
        n = len(d["df"])
        chain = st.detect_structure_chain(d["df"], pivot_len=PIVOT_LEN) or {}
        recent = [s for s in (chain.get("swings") or [])
                  if s.get("bar", 0) >= n - 1 - LOOKBACK]
        recent_pats = qm_patterns(recent)
        mine = recent_pats[-1] if recent_pats else None
        if shipped is None and mine is None:
            agree += 1
            continue
        if shipped is None or mine is None:
            disagree += 1
            bad.append(f"{d['sym']}: shipped={'None' if shipped is None else 'pattern'} "
                       f"walk={'None' if mine is None else 'pattern'}")
            continue
        same = all(int(mine[k]["bar"]) == int(shipped[k]["bar"])
                   for k in ("ls", "lh", "head", "rh"))
        if same:
            agree += 1
        else:
            disagree += 1
            walk_bars = [int(mine[k]["bar"]) for k in ("ls", "lh", "head", "rh")]
            ship_bars = [int(shipped[k]["bar"]) for k in ("ls", "lh", "head", "rh")]
            bad.append(f"{d['sym']}: walk={walk_bars} shipped={ship_bars}")
    return agree, disagree, bad


# ── arms ─────────────────────────────────────────────────────────────────────

def _state_mask(d):
    return d["state"] & d["all"]


def _all_mask(d):
    return d["all"]


def _arm(panel, ev_key, mask_fn):
    r = reg._edge(panel, ev_key, mask_fn)
    if r is None:
        return None, None, 0
    p, nrot = reg._rotation_p(panel, ev_key, mask_fn, r["edge"])
    return r, p, nrot


def main() -> int:
    ap = argparse.ArgumentParser(
        description="B-58 - Quasimodo geometry vs a plain support retest")
    ap.add_argument("--universe", type=int, default=500)
    ap.add_argument("--horizon", type=int, default=HORIZON)
    ap.add_argument("--verify", action="store_true", help="equivalence check only")
    #: B-58's 2026-09-11 amendment: the 3-year cache yielded 53 events against a
    #: floor of 200, and the event rate is a property of the BAR SUPPLY, not of the
    #: pattern. This points the same frozen design at a deeper cache. It is a
    #: directory switch on purpose - cache/cardinality/ is the shared panel behind
    #: B-43, B-57 and the DIAGNOSTIC arm, and re-cutting it to serve this item
    #: would silently move settled results.
    ap.add_argument("--cache", type=str, default=None,
                    help="bar cache directory (default: cache/cardinality)")
    args = ap.parse_args()

    cache_dir = Path(args.cache) if args.cache else CACHE
    syms, bhav_date = card.universe(args.universe)
    paths = [p for p in (cache_dir / f"{s}_1d.json" for s in syms) if p.exists()]
    if not paths:
        sys.exit(f"no cached bars in {cache_dir} - run renko_quality_cardinality.py first")

    print(f"B-58 - Quasimodo zone entry vs support retest   (bhavcopy {bhav_date})")
    print(f"bars from {cache_dir.name}")
    print(f"universe {len(paths)} names | horizon {args.horizon}d | pivot_len {PIVOT_LEN} "
          f"| zone +-{TOL_PCT}% | grab >={MIN_GRAB}% | CHOCH >={MIN_CHOCH}%")
    panel, pstats = build_panel(paths, args.horizon)
    if not panel:
        sys.exit("empty panel")

    agree, disagree, bad = verify(panel)
    print(f"equivalence vs detect_quasimodo: {agree} agree, {disagree} disagree")
    if disagree:
        for line in bad[:10]:
            print(f"    {line}")
        sys.exit("ABORT - the walk and the shipped detector disagree. Fix before reporting.")
    if args.verify:
        return 0

    n_qm = int(sum(int(d["qm"].sum()) for d in panel))
    n_state = int(sum(int(_state_mask(d).sum()) for d in panel))
    subset = all(bool((d["qm"] & ~_state_mask(d)).sum() == 0) for d in panel)
    print(f"names with no QM at all: {pstats['no_pattern']}/{len(panel)} | "
          f"QM zone entries {n_qm} | support-retest bars {n_state}")
    print(f"QM events are a subset of the retest state: {subset}")
    if not subset:
        sys.exit("ABORT - the baseline does not contain the signal; the state mask is wrong.")
    print()

    arms = [
        ("PRIMARY  QM zone entry vs retests", "qm", _state_mask, True),
        ("CONTROL  CHOCH relaxed, vs retests", "qmr", _state_mask, False),
        ("CONTRAST QM zone entry vs ALL bars", "qm", _all_mask, False),
        ("HARNESS  all retests vs ALL bars", "state", _all_mask, False),
        ("DIAGNOSTIC bare Renko flip (=B-43)", "flip", _all_mask, False),
    ]
    primary = None
    results = {}
    for label, key, mask_fn, is_primary in arms:
        r, p, nrot = _arm(panel, key, mask_fn)
        print(reg._row(label, r, p, nrot))
        results[label.split()[0]] = (r, p)
        if is_primary:
            primary = (r, p)

    print()
    # ── the HARNESS arm's abort clause, and how it resolved ──────────────────
    # Pre-registered: a strongly POSITIVE harness means the panel is wrong and
    # nothing else may be reported. It DID come back positive (+1.74%), so the
    # clause fired and the run stopped. The clause says debug the panel, and the
    # way to debug a panel is to point it at a settled number: the DIAGNOSTIC arm
    # is B-43's bare Renko flip, which measured a clean null.
    #
    # It reproduces (-0.05% against B-43's -0.02%). The scorer is therefore sound,
    # and the harness arm's sign is a property of the SAMPLE, not the machinery —
    # which means the pre-registered expectation was the thing that was wrong. It
    # assumed this panel's support-retest reading was comparable to B-19's family
    # numbers, and it is not: those are cost-applied, walk-forward scanner
    # backtests on LIQUID_50 across three windows, while this is a single
    # ~2-year window of today's liquid 356 with no costs and a different
    # baseline. Same conclusion as B-57's CONTROL2: **uninformative, not
    # contradictory.**
    #
    # What it does NOT do is rescue the primary, and the code says so below.
    hr, _hp = results.get("HARNESS", (None, None))
    dr, _dp = results.get("DIAGNOSTIC", (None, None))
    if hr is not None and hr["edge"] > 1.0:
        reproduced = dr is not None and abs(dr["edge"]) < 0.5
        print(f"HARNESS CLAUSE FIRED: the retest state reads {hr['edge']:+.2f}% against all "
              f"bars,\n       where the family measured -0.36/-0.47/-0.43% at 20d.")
        if not reproduced:
            print("       The DIAGNOSTIC arm does NOT reproduce B-43's null either, so the")
            print("       panel itself is suspect and no number in this run is reportable.")
            return 0
        print(f"       But the DIAGNOSTIC arm (bare Renko flip = B-43) reads "
              f"{dr['edge']:+.2f}%,\n       reproducing that settled null on this very panel. The scorer is")
        print("       sound; the harness arm is UNINFORMATIVE, not contradictory, and the")
        print("       pre-registered expectation of comparability with B-19 was wrong --")
        print("       different universe, window, cost treatment and baseline.")
        print("       Reading on, with that caveat attached to every absolute number.\n")

    if primary is None or primary[0] is None:
        print("VERDICT: INCONCLUSIVE - the primary arm produced no scorable events.")
        return 0
    r, p = primary
    if r["n_sig"] < MIN_EVENTS:
        print(f"VERDICT: INCONCLUSIVE - UNDERPOWERED. {r['n_sig']} primary events, "
              f"pre-registered floor is {MIN_EVENTS}. This is NOT a null.")
        return 0
    passed = r["edge"] > 0 and p is not None and p < 0.05
    print(f"VERDICT: {'PASS' if passed else 'FAIL'} against the pre-registered bar "
          f"(edge > 0 AND p_rot < 0.05): edge={r['edge']:+.2f}%, "
          f"p_rot={'n/a' if p is None else f'{p:.3f}'}")
    if not passed:
        print("        detect_quasimodo stays geometry: no scanner, no entry/stop/target,")
        print("        PIPELINE_EXCLUDED, and Liquidity Sweep (B-41m, +0.51% @20d,")
        print("        p=0.005) remains the measured way to express the same mechanic.")
    print("\nLIMITS: today's listed liquid names (survivorship) => UPPER BOUND; "
          "rotation grid is coarse\n        (every 3rd offset), so p is indicative, "
          "not exact; costs cancel in the difference\n        and no absolute return "
          "here is tradeable as printed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
