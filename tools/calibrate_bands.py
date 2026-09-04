#!/usr/bin/env python3
"""Measure the NSE distribution of every curve-scored input in
fundamental_score.py, so the score bands are set from data rather than intuition.

Why this exists
---------------
FP-1's peer table made a calibration fault visible that a single stock's donut
could not: in both measured peer groups nearly every company scored Growth
90-100. The band topped out at 25% CAGR — the 81st percentile of NSE revenue
CAGR and only the 65th of quarterly YoY. An axis where most of the market scores
full marks discriminates nothing.

Growth was fixed first (2026-09-04); this script then generalised to the other
five axes, which had never been checked at all.

What it does
------------
Samples the NIFTY-500 by stride (so it spans industries rather than the
alphabet), pulls every metric through `fundamental_score.raw_metrics` — the same
extractor the scorers use, so the measurement can never drift from what is
actually scored — and prints each metric's percentile distribution.

    py -3 tools/calibrate_bands.py [n_symbols]

Reading the output: the anchors printed under each metric are the curve to paste
into `_CURVES`. `DIR=lo` metrics (P/E, D/E, debtor days, margin CV) are
lower-is-better, so their anchors descend in score as the value rises.

Raw values are cached to cache/band_calibration.json so the bands can be
re-derived, argued with, or re-anchored without paying for the network sample.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fundamental_score as fs             # noqa: E402
import fundamentals_deep as fdeep          # noqa: E402
import stock_council as council            # noqa: E402

OUT = HERE / "cache" / "band_calibration.json"
UNIVERSE = HERE / "cache" / "nse_nifty500_constituents.json"
PCTS = (5, 10, 25, 40, 50, 60, 75, 90, 95)

#: Metric -> is a LOWER value better? Determines which way the curve runs.
DIRECTION = {
    "pe": True, "pb": True, "peg": True,
    "revenue_cagr_3y": False, "profit_cagr_3y": False, "revenue_yoy": False,
    "debt_to_equity": True, "debtor_days": True,
    "roe": False, "roce": False, "npm": False,
    "fcf_margin": False, "roce_trend": False,
    "margin_cv": True,
}

#: The percentile -> score mapping every curve is anchored on. Deliberately one
#: shared shape: an axis is "top decile = ~95, median = 55" or the six axes stop
#: meaning the same thing as each other, which is the entire point of one scorer.
ANCHORS = ((10, 20), (25, 35), (50, 55), (75, 80), (90, 95))


def sample(n: int) -> list[str]:
    names = [r["symbol"] for r in json.loads(UNIVERSE.read_text(encoding="utf-8"))]
    step = max(1, len(names) // n)
    return names[::step][:n]


def _one(sym: str) -> dict | None:
    try:
        m = fs.raw_metrics(council.fetch_fundamentals(sym), fdeep.derive_fundamentals(sym))
    except Exception:
        return None
    m["symbol"] = sym
    return m


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile — no interpolation, so every printed figure is a
    value some real company actually posted."""
    if not values:
        return float("nan")
    s = sorted(values)
    k = max(0, min(len(s) - 1, round(p / 100 * len(s) + 0.5) - 1))
    return s[k]


def curve_for(vals: list[float], lower_is_better: bool) -> list[tuple[float, int]]:
    """Percentile anchors as a (value, score) curve, ascending in value.

    For a lower-is-better metric the scores run downhill: the 10th percentile
    P/E is the cheapest decile and earns 95, not 20.
    """
    pts = []
    for pct, score in ANCHORS:
        v = round(percentile(vals, 100 - pct if lower_is_better else pct), 2)
        pts.append((v, score))
    if lower_is_better:
        pts.reverse()                      # ascending by value, descending by score
    # A flat segment (two anchors on the same value) makes interpolation
    # meaningless, so collapse duplicates keeping the better score.
    out: list[tuple[float, int]] = []
    for v, s in pts:
        if out and out[-1][0] == v:
            continue
        out.append((v, s))
    return out


def run(n: int = 200, max_workers: int = 6) -> dict:
    syms = sample(n)
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_one, s): s for s in syms}
        for i, fut in enumerate(as_completed(futures), 1):
            print(f"\r  {i}/{len(syms)}", end="", flush=True)
            try:
                r = fut.result()
            except Exception:
                r = None
            if r:
                rows.append(r)
    print()

    out: dict = {"n_sampled": len(syms), "n_returned": len(rows), "metrics": {}}
    for m, lower in DIRECTION.items():
        vals = [float(r[m]) for r in rows
                if r.get(m) is not None and float(r[m]) == float(r[m])]
        out["metrics"][m] = {
            "n": len(vals),
            "lower_is_better": lower,
            "coverage_pct": round(100 * len(vals) / max(len(rows), 1), 1),
            "median": round(median(vals), 2) if vals else None,
            "percentiles": {str(p): round(percentile(vals, p), 2) for p in PCTS},
            "curve": curve_for(vals, lower) if len(vals) >= 30 else None,
        }
    out["rows"] = rows
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    res = run(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
    print(f"\nsampled {res['n_sampled']}, returned {res['n_returned']}\n")
    for m, s in res["metrics"].items():
        d = "lo" if s["lower_is_better"] else "hi"
        print(f"{m}  [DIR={d}]  n={s['n']} ({s['coverage_pct']}%)  median={s['median']}")
        print("   " + "  ".join(f"p{p}={s['percentiles'][p]}" for p in s["percentiles"]))
        if s["curve"]:
            print(f'   curve: {tuple(tuple(x) for x in s["curve"])}')
        else:
            print("   curve: SKIPPED — under 30 observations, too thin to anchor")
    print(f"\nwritten to {OUT}")
