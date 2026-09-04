#!/usr/bin/env python3
"""Measure what "good growth" actually looks like on NSE, so the Growth bands
in fundamental_score.py are set from the distribution rather than from intuition.

Why this exists
---------------
FP-1's peer table made a calibration fault visible that a single stock's donut
could not: in both measured peer groups nearly every company scored Growth
90-100. The band topped out at 25% CAGR, and a large share of the market clears
25% on a 3-year window whose base year is FY21/FY22 — a COVID trough. An axis
where almost everyone scores full marks discriminates nothing.

This script samples the NIFTY-500 by stride (so it spans industries rather than
the alphabet), pulls the same three inputs `_score_growth` uses, and prints the
percentile distribution of each. Bands are then anchored on percentiles, which is
the only way "100" can mean "top of this market" instead of "above a number
someone typed".

    py -3 tools/calibrate_growth_bands.py [n_symbols]

Results are cached to cache/growth_calibration.json so the bands can be re-derived
or re-argued without paying for the network sample again.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fundamentals_deep as fdeep          # noqa: E402
import stock_council as council            # noqa: E402

OUT = HERE / "cache" / "growth_calibration.json"
UNIVERSE = HERE / "cache" / "nse_nifty500_constituents.json"
METRICS = ("revenue_cagr_3y", "profit_cagr_3y", "revenue_yoy")
PCTS = (5, 10, 25, 40, 50, 60, 75, 90, 95)


def sample(n: int) -> list[str]:
    names = [r["symbol"] for r in json.loads(UNIVERSE.read_text(encoding="utf-8"))]
    step = max(1, len(names) // n)
    return names[::step][:n]


def _one(sym: str) -> dict | None:
    try:
        d = fdeep.derive_fundamentals(sym) or {}
    except Exception:
        return None
    quarters = d.get("quarters") or []
    yoy = next((q.get("revenue_yoy") for q in quarters
                if q.get("revenue_yoy") is not None), None)
    if yoy is None:
        try:
            yoy = (council.fetch_fundamentals(sym) or {}).get("revenue_growth")
        except Exception:
            yoy = None
    return {"symbol": sym,
            "revenue_cagr_3y": d.get("revenue_cagr_3y"),
            "profit_cagr_3y": d.get("profit_cagr_3y"),
            "revenue_yoy": yoy}


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile — no interpolation, so every printed figure is a
    value some real company actually posted."""
    if not values:
        return float("nan")
    s = sorted(values)
    k = max(0, min(len(s) - 1, round(p / 100 * len(s) + 0.5) - 1))
    return s[k]


def run(n: int = 120, max_workers: int = 6) -> dict:
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
    for m in METRICS:
        vals = [float(r[m]) for r in rows
                if r.get(m) is not None and float(r[m]) == float(r[m])]
        out["metrics"][m] = {
            "n": len(vals),
            "coverage_pct": round(100 * len(vals) / max(len(rows), 1), 1),
            "median": round(median(vals), 1) if vals else None,
            "pct_over_25": round(100 * sum(v >= 25 for v in vals) / len(vals), 1) if vals else None,
            "pct_negative": round(100 * sum(v < 0 for v in vals) / len(vals), 1) if vals else None,
            "percentiles": {str(p): round(percentile(vals, p), 1) for p in PCTS},
        }
    out["rows"] = rows
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    res = run(int(sys.argv[1]) if len(sys.argv) > 1 else 120)
    print(f"\nsampled {res['n_sampled']}, returned {res['n_returned']}\n")
    for m, s in res["metrics"].items():
        print(f"{m}  (n={s['n']}, coverage {s['coverage_pct']}%, "
              f"median {s['median']}%, >=25%: {s['pct_over_25']}%, "
              f"negative: {s['pct_negative']}%)")
        print("   " + "  ".join(f"p{p}={s['percentiles'][p]}" for p in s["percentiles"]))
    print(f"\nwritten to {OUT}")
