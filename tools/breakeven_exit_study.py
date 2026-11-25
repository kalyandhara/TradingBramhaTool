#!/usr/bin/env python3
"""breakeven_exit_study.py - B-205: does moving the stop to breakeven improve results?

The LuxAlgo roadmap (step 3) says: once price gains k×R from entry, ratchet the
stop to entry. The target stays active, unlike the trail arms in B-124 that drop
it. This study asks whether that one-time ratchet helps or hurts.

== PRE-REGISTRATION -- committed BEFORE this file was first run ==

  SETUPS    Same two scanners measured to beat a random-entry baseline:
            Falling Wedge and Harmonic Reversal (XABCD). Same policy as
            B-124: never test on scanners with no measured edge.

  PANEL     nse_universe "nifty500", first 300 names, 1500 days daily,
            COST_INDIAN (~29bps round trip), signal_mode="fresh" (B-120),
            fill_model="market" -- entry at the next open.

  ARMS      control  fixed         the card's own stop / target / time stop
            treat    breakeven:1.0  stop ratchets to entry once price +1×R
                     breakeven:1.5  stop ratchets to entry once price +1.5×R
                     breakeven:2.0  stop ratchets to entry once price +2×R
            All breakeven arms run with honor_time_stop=False (same as B-124
            trail arms): the card's time stop would cap the tail the ratchet
            exists for. Time-stop-kept is reported as SENSITIVITY.

  UNIT      Trades paired on (symbol, signal bar); dR = R_be - R_fixed is
            averaged PER SYMBOL first. Test: one-sample t on per-symbol means.

  DECISION  6 comparisons (2 setups x 3 k values) -> alpha = 0.05 / 6 ≈ 0.0083.
            INCONCLUSIVE if < 30 symbols or < 150 paired trades.
            BE BETTER    mean dR > 0 and p < alpha
            BE WORSE     mean dR < 0 and p < alpha
            NO DIFFERENCE otherwise
            Descriptive only: r_p90, R>0 rate, bars held, % that triggered.

  EXPECTED  "No difference or worse" -- the ratchet eliminates small-loss
            exits (stop → entry) but also converts some winners that would
            have held to target into breakeven exits. On daily bars with
            directional drift the exchange rate is unclear. Prior is
            tie-or-worse; a positive result needs to clear the Bonferroni bar.

  py -3 -X utf8 tools/breakeven_exit_study.py            # the registered run
  py -3 -X utf8 tools/breakeven_exit_study.py --keep-time-stop   # sensitivity
  py -3 -X utf8 tools/breakeven_exit_study.py --out cache/be_study_custom.json
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import backtest as bt
import screener_pipeline as sp
from opportunity_hub import MEASURED_EDGE_SCANNERS, nse_universe

# ---------------------------------------------------------------------------
# Registration constants (never modify after first run)
# ---------------------------------------------------------------------------
SETUPS: tuple[str, ...] = ("Falling Wedge", "Harmonic Reversal (XABCD)")
K_ARMS: tuple[float, ...] = (1.0, 1.5, 2.0)
N_SYMBOLS = 300
DAYS = 1500
ALPHA = 0.05 / (len(SETUPS) * len(K_ARMS))   # Bonferroni: 0.0083
MIN_SYMBOLS = 30
MIN_TRADES = 150
OUT = Path("cache/be_study.json")


# ---------------------------------------------------------------------------
# Stats helpers (same as exit_model_bakeoff)
# ---------------------------------------------------------------------------

def _t_one_sample(arr: list[float]) -> tuple[float, float]:
    """Return (t, p) for a one-sample t-test against mu=0."""
    n = len(arr)
    if n < 2:
        return float("nan"), float("nan")
    a = np.asarray(arr, dtype=float)
    se = a.std(ddof=1) / math.sqrt(n)
    if se == 0:
        return float("nan"), float("nan")
    t = float(a.mean() / se)
    from scipy.stats import t as t_dist
    p = float(2 * t_dist.sf(abs(t), df=n - 1))
    return t, p


def _percentile(arr: list[float], q: float) -> float:
    return float(np.percentile(arr, q)) if arr else float("nan")


def _verdict(mean_dr: float, p: float, n_sym: int, n_trades: int) -> str:
    if n_sym < MIN_SYMBOLS or n_trades < MIN_TRADES:
        return "INCONCLUSIVE (insufficient data)"
    if math.isnan(p):
        return "INCONCLUSIVE (nan)"
    if p < ALPHA and mean_dr > 0:
        return "BE BETTER"
    if p < ALPHA and mean_dr < 0:
        return "BE WORSE"
    return "NO DIFFERENCE"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(keep_time_stop: bool = False, out: Path = OUT) -> dict[str, Any]:
    symbols = nse_universe("nifty500")[:N_SYMBOLS]

    _cache: dict = {}

    def fetch_fn(s):
        if s not in _cache:
            try:
                _cache[s] = sp.fetch_ohlcv(s, days=DAYS)
            except Exception:
                _cache[s] = None
        return _cache[s]

    results: dict[str, Any] = {
        "meta": {
            "study": "B-205",
            "setups": SETUPS,
            "k_arms": K_ARMS,
            "n_symbols": N_SYMBOLS,
            "days": DAYS,
            "alpha": ALPHA,
            "keep_time_stop": keep_time_stop,
        },
        "comparisons": {},
    }

    for setup in SETUPS:
        for k in K_ARMS:
            arm_key = f"breakeven:{k:g}"
            label = f"{setup} | {arm_key}"

            _common = dict(cost_model=bt.COST_INDIAN, signal_mode="fresh",
                           fill_model="market", keep_trades=True)
            ctrl_runs = bt.backtest_scanner(
                setup, symbols, fetch_fn,
                exit_model="fixed",
                honor_time_stop=keep_time_stop,
                **_common,
            ).get("trades", [])
            be_runs = bt.backtest_scanner(
                setup, symbols, fetch_fn,
                exit_model=f"breakeven:{k}",
                honor_time_stop=keep_time_stop,
                **_common,
            ).get("trades", [])

            ctrl_index: dict[tuple, float] = {}
            for rec in ctrl_runs:
                ctrl_index[(rec["symbol"], rec["t"])] = rec["r"]

            sym_dr: dict[str, list[float]] = defaultdict(list)
            paired = 0
            be_triggered = 0
            for rec in be_runs:
                key = (rec["symbol"], rec["t"])
                if key not in ctrl_index:
                    continue
                dr = rec["r"] - ctrl_index[key]
                sym_dr[rec["symbol"]].append(dr)
                paired += 1
                if rec.get("exit_model", "").startswith("breakeven") and rec.get("outcome") == "trail":
                    be_triggered += 1

            per_sym_means = [float(np.mean(v)) for v in sym_dr.values() if v]
            n_sym = len(per_sym_means)
            mean_dr = float(np.mean(per_sym_means)) if per_sym_means else float("nan")
            t, p = _t_one_sample(per_sym_means)

            results["comparisons"][label] = {
                "setup": setup,
                "arm": arm_key,
                "n_symbols": n_sym,
                "n_paired_trades": paired,
                "mean_dR": round(mean_dr, 4),
                "p90_dR": round(_percentile(per_sym_means, 90), 4),
                "t": round(t, 3) if not math.isnan(t) else None,
                "p": round(p, 4) if not math.isnan(p) else None,
                "alpha": round(ALPHA, 5),
                "verdict": _verdict(mean_dr, p, n_sym, paired),
                "be_triggered_pct": round(100 * be_triggered / paired, 1) if paired else None,
            }
            print(f"  {label}: dR={mean_dr:+.4f} t={t:.3f} p={p:.4f} -> "
                  f"{results['comparisons'][label]['verdict']}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults written to {out}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-time-stop", action="store_true")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    run(keep_time_stop=args.keep_time_stop, out=args.out)
