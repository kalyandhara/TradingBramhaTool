#!/usr/bin/env python3
"""target_anchor_study.py - B-207: do target-anchor types predict reach rate?

LuxAlgo step 6 adds target-anchor tags (target_anchors.py) to every plan card.
This study asks whether the tag type predicts whether the target is actually
reached.  It is the measurement that justifies (or refutes) using anchor type
as a filter or weight in the plan scoreboard.

== PRE-REGISTRATION — committed BEFORE this file was first run ==

  PANEL     Two measured-edge scanners (B-19 / B-92 baseline): Falling Wedge and
            Harmonic Reversal (XABCD).  Same walk-forward harness as B-19: 3
            windows × 500 days, nse_universe "nifty500" first 300 names, 29bps
            round-trip cost, signal_mode="fresh", fill_model="market".

  ENRICHMENT Each plan card is tagged with target_anchors.tag_target() against
            the daily OHLCV up to the signal bar.  Tolerance = 1.0% (DEFAULT).

  ARMS      One "arm" per anchor tag that appears in ≥ 30 plans.  The baseline
            is the pooled reach rate across ALL plans regardless of tag.  Each
            arm is compared to the baseline with a two-proportion z-test.

  STATISTIC Reach rate = target_hits / (target_hits + stop_hits).  Open / time
            exits are excluded from the denominator (consistent with B-116
            pooling).  Pooled across windows (counts summed, rate recomputed)
            before the z-test so the three windows are not three equal votes.

  DECISION  ALPHA = 0.05 / n_arms (Bonferroni, n_arms determined from the data).
            TAG PREDICTIVE   reach rate significantly higher than baseline
            TAG DESTRUCTIVE  reach rate significantly lower than baseline
            NO DIFFERENCE    otherwise
            INCONCLUSIVE     < 30 plans with that tag

  EXPECTED  SD_1R, SD_2R (most common tags — scanner's own measured moves) will
            NOT differ from baseline because the baseline IS mostly them.
            MONTH_HIGH / WEEK_HIGH may show a small positive: prior structure
            as a target destination is a reason the scanner placed it there.
            Prior = "no meaningful difference across tag types."  Any positive
            tag effect clears the Bonferroni bar before being reported.

  SCOPE     A predictive tag licenses noting it in the plan scoreboard display.
            It does NOT change any scanner output, entry rule, or plan.

  py -3 -X utf8 tools/target_anchor_study.py
  py -3 -X utf8 tools/target_anchor_study.py --out cache/anchor_study_custom.json
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

import backtest as bt
import screener_pipeline as sp
from opportunity_hub import nse_universe
from target_anchors import tag_target, AnchorTag

SETUPS: tuple[str, ...] = ("Falling Wedge", "Harmonic Reversal (XABCD)")
N_SYMBOLS = 300
DAYS = 1500
TOLERANCE = 0.010
MIN_PLANS_PER_TAG = 30
OUT = Path("cache/anchor_study.json")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def _two_prop_z(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    """Two-proportion z-test: arm (k1/n1) vs baseline (k2/n2)."""
    if n1 == 0 or n2 == 0:
        return float("nan"), float("nan")
    p1 = k1 / n1
    p2 = k2 / n2
    p_pool = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return float("nan"), float("nan")
    z = (p1 - p2) / se
    # two-tailed p via normal CDF approximation
    from scipy.stats import norm
    p = float(2 * norm.sf(abs(z)))
    return float(z), p


def _verdict(p: float, z: float, n: int, alpha: float) -> str:
    if n < MIN_PLANS_PER_TAG:
        return "INCONCLUSIVE (< 30 plans)"
    if math.isnan(p):
        return "INCONCLUSIVE (nan)"
    if p < alpha and z > 0:
        return "TAG PREDICTIVE"
    if p < alpha and z < 0:
        return "TAG DESTRUCTIVE"
    return "NO DIFFERENCE"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(out: Path = OUT) -> dict[str, Any]:
    symbols = nse_universe("nifty500")[:N_SYMBOLS]

    # Shared OHLCV cache: backtest_scanner fills it, tagging step reuses it.
    _cache: dict = {}

    def fetch_fn(s):
        if s not in _cache:
            try:
                raw = sp.fetch_ohlcv(s, days=DAYS)
                if raw is not None and not raw.empty:
                    import pandas as pd
                    raw = raw.dropna(subset=["high", "low", "close", "volume"])
                    _cache[s] = raw.reset_index(drop=True)
                else:
                    _cache[s] = None
            except Exception:
                _cache[s] = None
        return _cache[s]

    # Collect all plan records with their anchor tags
    # tag_counts[setup][tag] -> {"target": int, "stop": int}
    tag_counts: dict[str, dict[AnchorTag, dict[str, int]]] = {}

    for setup in SETUPS:
        tag_counts[setup] = defaultdict(lambda: {"target": 0, "stop": 0})

        result = bt.backtest_scanner(
            setup, symbols, fetch_fn,
            cost_model=bt.COST_INDIAN,
            signal_mode="fresh",
            fill_model="market",
            exit_model="fixed",
            honor_time_stop=True,
            keep_trades=True,
        )
        records = result.get("trades", [])

        for rec in records:
            outcome = rec.get("outcome")
            if outcome not in ("target", "stop"):
                continue
            # Tag the target using the signal-bar slice from the cached df
            sym = rec["symbol"]
            t = rec["t"]
            df_sym = _cache.get(sym)
            if df_sym is not None and t < len(df_sym):
                card = {
                    "entry": rec["entry_px"],
                    "stop": rec["stop"],
                    "target": rec["target"],
                }
                tag = tag_target(card, df_sym.iloc[: t + 1], tolerance=TOLERANCE)
            else:
                tag = "NONE"
            if outcome == "target":
                tag_counts[setup][tag]["target"] += 1
            else:
                tag_counts[setup][tag]["stop"] += 1

    results: dict[str, Any] = {
        "meta": {
            "study": "B-207",
            "setups": SETUPS,
            "n_symbols": N_SYMBOLS,
            "days": DAYS,
            "tolerance": TOLERANCE,
            "min_plans_per_tag": MIN_PLANS_PER_TAG,
        },
        "by_setup": {},
    }

    for setup in SETUPS:
        counts = dict(tag_counts[setup])
        # Baseline: all plans pooled
        total_t = sum(v["target"] for v in counts.values())
        total_s = sum(v["stop"] for v in counts.values())
        total_n = total_t + total_s
        base_rate = total_t / total_n if total_n else float("nan")

        all_tags = [t for t in counts if (counts[t]["target"] + counts[t]["stop"]) >= MIN_PLANS_PER_TAG]
        alpha = 0.05 / max(len(all_tags), 1)

        tag_results: dict[str, Any] = {}
        for tag in sorted(counts.keys()):
            t = counts[tag]["target"]
            s = counts[tag]["stop"]
            n = t + s
            rate = t / n if n else float("nan")
            z, p = _two_prop_z(t, n, total_t, total_n)
            tag_results[tag] = {
                "n": n, "target": t, "stop": s,
                "reach_rate": round(rate, 4) if not math.isnan(rate) else None,
                "vs_baseline": round(rate - base_rate, 4) if not math.isnan(rate) else None,
                "z": round(z, 3) if not math.isnan(z) else None,
                "p": round(p, 4) if not math.isnan(p) else None,
                "verdict": _verdict(p, z, n, alpha),
            }
            print(f"  {setup} | {tag:15s}: n={n:4d} rate={rate:.1%} "
                  f"vs base={base_rate:.1%}  -> {tag_results[tag]['verdict']}")

        results["by_setup"][setup] = {
            "baseline": {
                "n": total_n, "target": total_t, "stop": total_s,
                "reach_rate": round(base_rate, 4) if not math.isnan(base_rate) else None,
            },
            "alpha": round(alpha, 5),
            "tags": tag_results,
        }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults written to {out}")
    return results


if __name__ == "__main__":
    import sys
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    run(out=args.out)
