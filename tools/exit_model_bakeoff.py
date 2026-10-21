#!/usr/bin/env python3
"""exit_model_bakeoff.py - B-124: does a trailing exit beat the fixed plan?

The LuxAlgo exit list that raised B-123..127 assumes a better exit is a better
trade. Nobody on this desk has checked, because until B-123 the harness could
not express a stop that moves.

== PRE-REGISTRATION -- committed 2026-09-23 BEFORE this file was first run ==

  SETUPS    The two scanners MEASURED to beat a random-entry baseline
            (opportunity_hub.MEASURED_EDGE_SCANNERS): Falling Wedge and
            Harmonic Reversal (XABCD). Never the failures: a better exit on a
            null entry is a better-managed null. B-115's held structure breaks
            are named in B-124 but are not a harness scanner with a plan, so
            they are OUT of this run -- stated, not quietly dropped.

  PANEL     nse_universe "nifty500", first 300 names, 1500 days daily,
            COST_INDIAN (~29bps round trip), signal_mode="fresh" (B-120),
            fill_model="market" -- entry at the next open, what acting on the
            card the next morning gets, and B-92's convention (B-121).

  ARMS      control  fixed      the card's own stop / target / time stop
            treat    atr_trail:3   Chandelier, extreme - 3 x ATR22
                     structure:5   close through last confirmed swing
                     ema_close:20  close through EMA20
            Trail arms run with honor_time_stop=False: the B-123 smoke showed
            the card's time stop ending ~a quarter of trades under every trail,
            capping the tail a trail exists for. The time-stop-kept variant is
            reported as SENSITIVITY, never as the verdict.

  UNIT      Trades are PAIRED on (symbol, signal bar) -- identical entries in
            both arms -- and the paired difference dR = R_trail - R_fixed is
            averaged PER SYMBOL first. The test is a one-sample t on the
            per-symbol means (ob_bias_clustered precedent): a name that fires
            thirty times is one opinion, not thirty.

  DECISION  6 comparisons (2 setups x 3 trail arms) -> alpha = 0.05 / 6.
            INCONCLUSIVE if < 30 symbols or < 150 paired trades.
            TRAIL BETTER   mean dR > 0 and p < alpha
            TRAIL WORSE    mean dR < 0 and p < alpha
            NO DIFFERENCE  otherwise
            Descriptive only (NOT decisions): r_p90, R>0 rate, bars held.

  EXPECTED  "Trails cut winners on daily bars" -- B-8 found tight stops cost
            -0.64pp on mean reversion. Written down so a null is not a surprise
            and a positive has to beat a stated prior.

  py -3 -X utf8 tools/exit_model_bakeoff.py            # the registered run
  py -3 -X utf8 tools/exit_model_bakeoff.py --keep-time-stop   # sensitivity

== B-181 RE-RUN -- pre-registered 2026-10-21 BEFORE this variant was run ==

  REASON    B-116's control diagnosis (2026-10-21) found that `signal_mode="fresh"`
            drops a breakout bar that follows a scanner's WATCH-only card: the
            WATCH bar is the 'first hit', so the actionable break is never fresh.
            Falling Wedge emits WATCH cards; Harmonic Reversal (XABCD) does not.
            The original B-124 run used `signal_mode="fresh"`, so its Falling Wedge
            arm undercounted breakouts. The Harmonic arm is unaffected.

  CHANGE    `signal_mode="fresh_plan"` in place of `"fresh"`. Everything else
            unchanged: same panel (nifty500 first 300, 1500 days), same arms
            (atr_trail:3, structure:5, ema_close:20), same pairing rule, same
            decision alpha (0.05/6 = 0.0083), same INCONCLUSIVE / TRAIL BETTER /
            TRAIL WORSE thresholds, honor_time_stop=False for trail arms.

  CONTROL   Harmonic Reversal arm must reproduce B-124 run 2: pairs 793, symbols 257,
            mean_dR within +/-0.05R and p within +/-0.05 for each of the three arms.
            If it fails, the run stops -- the scanner or the harness moved.

  EXPECTED  Falling Wedge will have more trades and pairs. The ATR arm (+0.13R,
            p=0.058) may cross significance or stay a tie. Prior: tie or worse.
            One decisive result in the whole bake-off, and it was a trail LOSING --
            the structural prior is "trails cut winners on daily bars."

  py -3 -X utf8 tools/exit_model_bakeoff.py --fresh-plan           # B-181 run
  py -3 -X utf8 tools/exit_model_bakeoff.py --fresh-plan --keep-time-stop  # sensitivity
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

SETUPS = ("Falling Wedge", "Harmonic Reversal (XABCD)")
TRAIL_ARMS = ("atr_trail:3", "structure:5", "ema_close:20")
N_SYMBOLS = 300
DAYS = 1500
MIN_SYMBOLS = 30
MIN_TRADES = 150
ALPHA = 0.05 / (len(SETUPS) * len(TRAIL_ARMS))
OUT = Path(__file__).resolve().parent / "cache" / "exit_model_bakeoff.json"


def _t_test(xs: list[float]) -> tuple[float, float]:
    """Two-sided one-sample t-test against 0. Returns (t, p)."""
    a = np.asarray(xs, dtype=float)
    n = len(a)
    if n < 2:
        return float("nan"), float("nan")
    sd = float(a.std(ddof=1))
    if sd == 0:
        return float("inf") if a.mean() else 0.0, 0.0 if a.mean() else 1.0
    t = float(a.mean()) / (sd / math.sqrt(n))
    try:
        from scipy import stats
        p = float(2 * stats.t.sf(abs(t), df=n - 1))
    except Exception:                          # normal approximation
        p = float(math.erfc(abs(t) / math.sqrt(2)))
    return t, p


def paired(control: list[dict], treat: list[dict]) -> dict[str, Any]:
    """Pair on (symbol, t), average dR per symbol, test across symbols."""
    c = {(x["symbol"], x["t"]): x for x in control}
    per_sym: dict[str, list[float]] = defaultdict(list)
    pairs = 0
    for x in treat:
        k = (x["symbol"], x["t"])
        if k in c:
            per_sym[x["symbol"]].append(float(x["r"]) - float(c[k]["r"]))
            pairs += 1
    means = [float(np.mean(v)) for v in per_sym.values()]
    t, p = _t_test(means)
    return {"pairs": pairs, "symbols": len(means),
            "mean_dR": round(float(np.mean(means)), 3) if means else None,
            "median_dR": round(float(np.median(means)), 3) if means else None,
            "symbols_better": int(sum(m > 0 for m in means)),
            "t": round(t, 2) if not math.isnan(t) else None,
            "p": round(p, 4) if not math.isnan(p) else None}


def verdict(pr: dict[str, Any]) -> str:
    if pr["symbols"] < MIN_SYMBOLS or pr["pairs"] < MIN_TRADES:
        return "INCONCLUSIVE"
    if pr["p"] is not None and pr["p"] < ALPHA:
        return "TRAIL BETTER" if pr["mean_dR"] > 0 else "TRAIL WORSE"
    return "NO DIFFERENCE"


def describe(trades: list[dict]) -> dict[str, Any]:
    rs = np.asarray([x["r"] for x in trades], dtype=float)
    if not len(rs):
        return {"n": 0}
    return {"n": int(len(rs)), "avg_R": round(float(rs.mean()), 3),
            "r_p90": round(float(np.percentile(rs, 90)), 2),
            "positive_rate": round(float((rs > 0).mean()), 3),
            "avg_bars": round(float(np.mean([x["bars"] for x in trades])), 1)}


def run(symbols, fetch_fn, keep_time_stop: bool = False,
        fresh_plan: bool = False) -> dict[str, Any]:
    signal_mode = "fresh_plan" if fresh_plan else "fresh"
    out: dict[str, Any] = {"alpha": ALPHA, "keep_time_stop": keep_time_stop,
                           "fill_model": "market", "signal_mode": signal_mode,
                           "setups": {}}
    common = dict(cost_model=bt.COST_INDIAN, signal_mode=signal_mode,
                  fill_model="market", keep_trades=True)
    for setup in SETUPS:
        ctl = bt.backtest_scanner(setup, symbols, fetch_fn, **common)
        block: dict[str, Any] = {"control": describe(ctl.get("trades", [])),
                                 "unfilled": (ctl.get("r_metrics") or {}).get("plans_unfilled"),
                                 "arms": {}}
        for arm in TRAIL_ARMS:
            tr = bt.backtest_scanner(setup, symbols, fetch_fn, exit_model=arm,
                                     honor_time_stop=keep_time_stop, **common)
            pr = paired(ctl.get("trades", []), tr.get("trades", []))
            block["arms"][arm] = {"paired": pr, "verdict": verdict(pr),
                                  "describe": describe(tr.get("trades", []))}
            print(f"  {setup:28s} {arm:13s} {verdict(pr):14s} {pr}", flush=True)
        out["setups"][setup] = block
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--keep-time-stop", action="store_true",
                    help="SENSITIVITY: trail arms honour the card's time stop")
    ap.add_argument("--fresh-plan", action="store_true",
                    help="B-181 re-run: use fresh_plan signal mode instead of fresh")
    ap.add_argument("--symbols", type=int, default=N_SYMBOLS)
    a = ap.parse_args()
    import nse_universe as nu
    import screener_pipeline as sp
    syms = list(nu.symbols("nifty500"))[:a.symbols]
    cache: dict = {}

    def fetch(s):
        if s not in cache:
            try:
                cache[s] = sp.fetch_ohlcv(s, days=DAYS)
            except Exception:
                cache[s] = None
        return cache[s]

    res = run(syms, fetch, keep_time_stop=a.keep_time_stop, fresh_plan=a.fresh_plan)
    res["symbols_requested"] = len(syms)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    suffix = ("_fp" if a.fresh_plan else "") + ("_keep_ts" if a.keep_time_stop else "")
    out = OUT.with_name(OUT.stem + suffix + ".json")
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwritten {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
