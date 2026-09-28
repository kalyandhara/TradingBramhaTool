#!/usr/bin/env python3
"""pivot_len_agreement.py — how far apart are the two structure definitions? (B-42r)

`detect_bos_choch` / `detect_support_breakdown` default to **pivot_len=5**;
`detect_structure_chain`, `read_market_structure` and the chart overlay use
**15**. So "structure" is coarser on the chart than in the scanners, and the
module has carried that as a known open question since 2026-09-02.

══ WHY THIS IS AN AGREEMENT TEST AND NOT AN EDGE TEST ══════════════════════════

The backlog's note says "settle it on data — the same `--wf` harness B-19 used".
Running an edge sweep over pivot_len would be the wrong first move, for two
reasons:

  1. **B-19 already measured these scanners: 0 of 41 stable after costs.**
     Sweeping a parameter to find the setting with the best forward return, on
     detectors with no established edge, is parameter-fitting dressed as
     settlement. Whichever number won would be noise with a decimal point.
  2. **`pivot_len` is a DEFINITION, not a signal.** It decides what counts as a
     swing. The question it raises is not "which is more profitable" but "are
     these two the same reading or two different ones", and that is answerable
     without any forward return at all.

This is the **B-59 precedent, applied**: when PSAR was proposed as a signal, the
desk's own rule was that *"the first measurement owed is an overlap check, not an
edge test"*. Same here.

══ WHAT IS MEASURED ════════════════════════════════════════════════════════════

For each symbol, `read_market_structure` is called at BOTH settings on the same
frame, and the two reads are compared field by field:

  * `state`      — the headline (UPTREND / DOWNTREND / BROADENING / ...)
  * `agreement`  — CONFIRMED / UNDECIDED, the "is structure turning" field the
                   B-42 write-up called the most useful on the object
  * `zone`       — PREMIUM / DISCOUNT / EQUILIBRIUM
  * `trend_from_breaks` — the break-derived direction

**Disagreement on `state` is the one that matters**, because that is the word a
reader sees. A high disagreement rate means the chart and the scanners are
telling the reader two different things about the same name on the same day.

CLI:
  py -3 -X utf8 tools/pivot_len_agreement.py
  py -3 -X utf8 tools/pivot_len_agreement.py --symbols 200 --days 800
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

import scanner_templates as sc

#: The two shipped defaults. Not a sweep — these are the two values actually in
#: the code, and the question is about them specifically.
SCANNER_PL = 5
CHART_PL = 15

#: Fields compared. `state` is primary; the rest are reported because a split
#: that shows up in only one field means something different from one that shows
#: up in all of them.
FIELDS = ("state", "agreement", "zone", "trend_from_breaks")


def compare(df, a: int = SCANNER_PL, b: int = CHART_PL) -> dict | None:
    """Both reads on one frame. None when either cannot be computed."""
    try:
        ra = sc.read_market_structure(df, pivot_len=a)
        rb = sc.read_market_structure(df, pivot_len=b)
    except Exception:
        return None
    if not ra or not rb:
        return None
    out = {"a": ra, "b": rb}
    for f in FIELDS:
        out[f"same_{f}"] = ra.get(f) == rb.get(f)
    # The zone percentage is continuous, so it is reported as a gap rather than
    # as an equality — two reads can agree on DISCOUNT while disagreeing about
    # how deep, which is a different kind of split.
    za, zb = ra.get("zone_pct"), rb.get("zone_pct")
    out["zone_pct_gap"] = (abs(za - zb) if isinstance(za, (int, float))
                           and isinstance(zb, (int, float)) else None)
    return out


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    res = {"n": n, "same": {}, "pairs": Counter(), "zone_gap": []}
    for f in FIELDS:
        k = sum(1 for r in rows if r[f"same_{f}"])
        res["same"][f] = 100.0 * k / n if n else float("nan")
    for r in rows:
        res["pairs"][(r["a"].get("state"), r["b"].get("state"))] += 1
    gaps = [r["zone_pct_gap"] for r in rows if r["zone_pct_gap"] is not None]
    res["zone_gap"] = gaps
    res["zone_gap_median"] = (sorted(gaps)[len(gaps) // 2] if gaps else float("nan"))
    return res


def verdict(s: dict) -> tuple[str, str]:
    """No p-value here: this is a coverage count, not a hypothesis test.

    The thresholds are stated in advance so the reading is not invented from the
    number that comes back.
    """
    if s["n"] < 30:
        return "INCONCLUSIVE", f"{s['n']} symbols is too few to count"
    agree = s["same"]["state"]
    if agree >= 90:
        return ("COSMETIC",
                f"the two settings agree on state {agree:.1f}% of the time — "
                f"unify on one and pick by cost, not by meaning")
    if agree >= 70:
        return ("REAL BUT NARROW",
                f"state agrees {agree:.1f}% of the time — the split is visible "
                f"but most readers see the same word")
    return ("TWO DIFFERENT READINGS",
            f"state agrees only {agree:.1f}% of the time — the chart and the "
            f"scanners are describing different structures, and unifying them "
            f"is a decision about what structure MEANS, not a default to tidy")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(description="B-42r · pivot_len 5 vs 15 agreement")
    ap.add_argument("--symbols", type=int, default=200)
    ap.add_argument("--days", type=int, default=800)
    a = ap.parse_args()

    import nse_universe as nu
    import screener_pipeline as sp

    syms = list(nu.symbols("nifty500"))[:a.symbols]
    rows = []
    for sym in syms:
        try:
            df = sp.fetch_ohlcv(sym, days=a.days)
        except Exception:
            continue
        if df is None or len(df) < 200:
            continue
        r = compare(df)
        if r:
            rows.append(r)

    s = summarise(rows)
    print(f"\n{s['n']} symbols read at pivot_len {SCANNER_PL} (scanners) "
          f"and {CHART_PL} (chart / shared read)\n")
    for f in FIELDS:
        print(f"  agree on {f:<18} {s['same'][f]:>6.1f}%")
    print(f"\n  median |zone_pct| gap     {s['zone_gap_median']:>6.1f} pp")

    print("\n  Most common disagreements (scanners -> chart):")
    for (pa, pb), k in s["pairs"].most_common(8):
        if pa == pb:
            continue
        print(f"    {str(pa):<14} -> {str(pb):<14} {k:>4}  "
              f"({100.0 * k / s['n']:.1f}%)")

    v, why = verdict(s)
    print(f"\nVERDICT: {v}\n  {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
