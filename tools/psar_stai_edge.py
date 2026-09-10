#!/usr/bin/env python3
"""psar_stai_edge.py — B-59r: PSAR and STAI agree. Which one carries the information?

Runs the design pre-registered in `analyses/Open-Backlog.md` §B-59r, committed at
`1035729` BEFORE this scorer existed. Nothing here may change the design; if
something has to change, the entry changes first and says why.

══ WHY THIS EXISTS ══════════════════════════════════════════════════════════════

B-59's chance-corrected run found the trailing-stop role is NOT held by three
detectors. It is held by **PMax, plus one detector implemented twice**: PSAR and
STAI agree at +34.2 lift over rotation, while PSAR and PMax agree BELOW chance.
So "can we drop one" has exactly one answerable form — which of the twins carries
information the other misses — and that is what this scores.

**It is also the first time any of PSAR, STAI or PMax is scored on this desk at
all.** B-59 measured agreement. Agreement is not accuracy.

══ PRE-REGISTERED DESIGN (mirrored from the entry; do not edit here) ════════════

  EVENTS   long side only (up-flips), three mutually exclusive arms:
             AGREE      a PSAR up-flip with an STAI up-flip within +-3 bars
             PSAR-ONLY  a PSAR up-flip with NO STAI up-flip within +-3 bars
             STAI-ONLY  an STAI up-flip with NO PSAR up-flip within +-3 bars
           +-3 is B-59's middle rung, fixed before any of these numbers existed.

  CAUSALITY  an AGREE event is dated at max(psar_bar, stai_bar) -- the bar both
             are known on. Dating it at the earlier flip would trade on a
             confirmation that had not arrived. Entry is the NEXT OPEN.
  BASELINE   every bar in the same names, unconditional -- the same construction
             as B-43 and B-58's CONTRAST arm.
  HORIZON    20 trading days.
  STATISTIC  mean(arm) - mean(baseline), percent, circular-rotation p.
  COSTS      none: every arm is differenced against the same baseline held the
             same 20 days, so the ~29bps model cancels.

  DECISION RULE (a SELECTION, not a pass/fail):
    PSAR-ONLY sig, STAI-ONLY not  -> PSAR sees something STAI misses
    STAI-ONLY sig, PSAR-ONLY not  -> the reverse; PSAR stays an overlay for good
    BOTH NULL                     -> neither twin's unique cells carry measurable
                                     information. The trim cannot be decided on
                                     edge and falls back to cost: KEEP STAI (it is
                                     already wired), PSAR stays a drawn overlay.
                                     **No indicator is deleted on a null.**
    both positive                 -> the disagreement is noise both ways; AGREE
                                     becomes the interesting arm
  AGREE is context, never decisive.
  ABORT   any arm under 200 events is UNDERPOWERED and supports no conclusion.

  PRIOR: skeptical. A trailing-stop up-flip is a trend-following entry AFTER a
  move -- the same shape B-43 measured at a clean null and B-43r at -1.01% once
  state-matched. Expectation is both twins null.

══ WHERE THE NUMBERS COME FROM ══════════════════════════════════════════════════

The flips are NOT recomputed here. `psar_overlap.js --emit` produces them from
the shipped `psar.js` / `supertrend_ai.js` and the `pmaxSeries` lifted out of
`chart_dashboard.html`; this file only scores them, through the same
`renko_regime_study` harness as B-43/B-57/B-58. Neither side reimplements the
other's half -- which is the only reason B-59, B-59r and the Renko studies are
comparable rather than three differently-built numbers.

CLI:
    node tools/psar_overlap.js --emit tools/cache/flip_vectors.json
    py -3 tools/psar_stai_edge.py
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
TOL = 3             #: bars, B-59's middle rung -- fixed before these numbers existed
MIN_EVENTS = 200    #: below this an arm is UNDERPOWERED and concludes nothing


def _near(bar: int, others: list[int], tol: int = TOL) -> int | None:
    """The nearest same-direction flip within `tol`, or None.

    Returns the BAR rather than a boolean because AGREE needs it: the event is
    dated at the later of the two flips, and that requires knowing which bar the
    partner landed on.
    """
    best, bestd = None, tol + 1
    for o in others:
        d = abs(o - bar)
        if d <= tol and d < bestd:
            best, bestd = o, d
    return best


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

        p_up = [i for i, d in v["psar"] if d == 1]
        s_up = [i for i, d in v["stai"] if d == 1]

        agree = np.zeros(m, bool)
        psar_only = np.zeros(m, bool)
        stai_only = np.zeros(m, bool)

        for t in p_up:
            partner = _near(t, s_up)
            if partner is None:
                if WARMUP <= t <= last:
                    psar_only[t] = True
            else:
                # Dated at the LATER of the two: the bar on which both are known.
                # Anything earlier trades a confirmation that has not arrived.
                e = max(t, partner)
                if WARMUP <= e <= last:
                    agree[e] = True

        for t in s_up:
            if _near(t, p_up) is None and WARMUP <= t <= last:
                stai_only[t] = True

        allb = np.zeros(m, bool)
        allb[WARMUP:last + 1] = True

        panel.append({"sym": sym, "fwd": fwd, "agree": agree,
                      "psar_only": psar_only, "stai_only": stai_only,
                      "all": allb})
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
    ap = argparse.ArgumentParser(description="B-59r - PSAR vs STAI, which twin carries the information")
    ap.add_argument("--vectors", default=str(VECTORS))
    ap.add_argument("--horizon", type=int, default=HORIZON)
    args = ap.parse_args()

    vpath = Path(args.vectors)
    if not vpath.exists():
        sys.exit(f"no flip vectors at {vpath}\n"
                 f"run: node tools/psar_overlap.js --emit {vpath}")
    vectors = json.loads(vpath.read_text(encoding="utf-8"))

    print("B-59r - PSAR vs STAI: which of the two agreeing detectors carries the information?")
    print(f"{len(vectors)} names | horizon {args.horizon}d | agreement window +-{TOL} bars "
          f"| long side only | no costs (they cancel)")
    panel = build_panel(vectors, args.horizon)
    if not panel:
        sys.exit("empty panel")

    n_ag = int(sum(int(d["agree"].sum()) for d in panel))
    n_po = int(sum(int(d["psar_only"].sum()) for d in panel))
    n_so = int(sum(int(d["stai_only"].sum()) for d in panel))
    print(f"events: AGREE {n_ag} | PSAR-ONLY {n_po} | STAI-ONLY {n_so}\n")

    out = {}
    for label, key in [("AGREE     both flip up within +-3", "agree"),
                       ("PSAR-ONLY no STAI flip near it", "psar_only"),
                       ("STAI-ONLY no PSAR flip near it", "stai_only")]:
        r, p, nrot = _arm(panel, key)
        print(reg._row(label, r, p, nrot))
        out[key] = (r, p)

    print()
    verdicts = {}
    for key, name in [("psar_only", "PSAR-ONLY"), ("stai_only", "STAI-ONLY")]:
        r, p = out[key]
        if r is None:
            verdicts[key] = "no events"
        elif r["n_sig"] < MIN_EVENTS:
            verdicts[key] = f"UNDERPOWERED ({r['n_sig']} < {MIN_EVENTS})"
        elif p is not None and p < 0.05 and r["edge"] > 0:
            verdicts[key] = f"POSITIVE ({r['edge']:+.2f}%, p={p:.3f})"
        elif p is not None and p < 0.05 and r["edge"] < 0:
            verdicts[key] = f"NEGATIVE ({r['edge']:+.2f}%, p={p:.3f})"
        else:
            verdicts[key] = (f"null ({r['edge']:+.2f}%, "
                             f"p={'n/a' if p is None else f'{p:.3f}'})")
        print(f"  {name:<10} {verdicts[key]}")

    po_sig = verdicts["psar_only"].startswith("POSITIVE")
    so_sig = verdicts["stai_only"].startswith("POSITIVE")
    under = any(v.startswith("UNDERPOWERED") or v == "no events" for v in verdicts.values())

    print()
    if under:
        print("VERDICT: INCONCLUSIVE for the underpowered arm(s) — that arm supports no")
        print("         conclusion in either direction, and is NOT a null.")
    if po_sig and not so_sig:
        print("VERDICT: PSAR sees something STAI misses. Keeping PSAR is justified, and a")
        print("         PSAR signal becomes a legitimate proposal for the first time.")
    elif so_sig and not po_sig:
        print("VERDICT: STAI carries it; PSAR's unique flips do not. PSAR stays a drawn")
        print("         overlay for good, and B-46's exclusion is now measured rather than")
        print("         argued.")
    elif po_sig and so_sig:
        print("VERDICT: both twins' unique cells are positive — the disagreement is noise in")
        print("         both directions, and the AGREE arm is the interesting one. That is a")
        print("         confluence question for its own entry, not a trim.")
    elif not under:
        print("VERDICT: BOTH NULL, which is the pre-registered outcome with a named")
        print("         consequence: the trim cannot be decided on edge. It falls back to")
        print("         cost -- KEEP STAI, which is already wired, and PSAR stays a drawn")
        print("         overlay. NO INDICATOR IS DELETED ON A NULL: a null is not evidence")
        print("         of harm, and neither twin has been shown to mislead anyone.")

    ar, ap_ = out["agree"]
    if ar is not None:
        print(f"\n  AGREE, as context only: {ar['edge']:+.2f}% "
              f"(p={'n/a' if ap_ is None else f'{ap_:.3f}'}) on {ar['n_sig']} events. "
              f"Never decisive here —\n  if it beats both singles that is a confluence "
              "finding for its own entry.")

    print("\nLIMITS: today's listed liquid names (survivorship) => UPPER BOUND; a 20d")
    print("        horizon is one choice and a trailing stop is not obviously a 20d")
    print("        instrument; long side only; rotation grid is coarse, so p is")
    print("        indicative, not exact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
