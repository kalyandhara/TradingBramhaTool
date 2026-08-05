#!/usr/bin/env python3
"""
backtest.py — point-in-time replay harness for the Scanner Hub scanners.

The dashboard's scanners (``scanner_templates.SCANNERS``) and the council's
thresholds are all *hand-set* — flagged across the wiki as the single biggest
credibility gap (see analyses/Dashboard-UI-Roadmap Phase 3). This module is the
measurement layer: it replays any ``scan_*(df) -> dict | None`` scanner over
historical data, bar by bar, and reports whether firing actually preceded
above-baseline forward returns.

Design (the honesty-critical parts):

  * **No look-ahead.** At bar ``t`` the scanner is handed ONLY ``df.iloc[:t+1]``
    — it physically cannot see the future. Entry is taken at the NEXT bar's open
    (``t+1``), never the signal bar's own close, so a signal that depends on the
    close can't be "traded" on that same close.
  * **Baseline = random entry in the same tape.** Every scanner looks good in a
    bull market. "Edge" here means the signal's average forward return MINUS the
    average forward return of *all bars* over the same symbols and window — i.e.
    did firing beat a coin-flip entry on the same names over the same period.
  * **R-expectancy only where a plan exists.** Scanners that emit
    ``entry``/``stop``/``target`` get a stop-or-target-first simulation and an
    expectancy in R; scanners without a plan get forward-return metrics only.
  * **Thin samples are flagged, not hidden.** A hit-rate off < ``MIN_SAMPLE``
    signals is marked unreliable rather than quoted as a headline number.

Known v1 limitations (labelled, not silently ignored):
  * **Survivorship bias** — only names that exist today are in the universe.
  * **No costs/slippage** — gross returns; a real edge must survive costs.
  * **History depth varies** — young listings contribute fewer bars/signals.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import scanner_templates as sc

# A scanner needs enough warm-up history before its first honest evaluation
# (Stage-2 wants ~210 bars). Start every replay after this many bars.
WARMUP_BARS = 210

# Below this many recorded signals, aggregate stats are statistically noise.
MIN_SAMPLE = 30

# Default forward-return horizons (in trading bars).
DEFAULT_HORIZONS = (5, 10, 20, 60)

# A trending scanner fires on many consecutive bars; counting each as an
# independent trade inflates and correlates the sample. Enforce a gap (bars)
# between recorded signals per symbol.
DEFAULT_MIN_GAP = 5


def _to_float(x) -> float | None:
    try:
        v = float(x)
        return None if np.isnan(v) else v
    except (TypeError, ValueError):
        return None


def _simulate_plan(df: pd.DataFrame, entry_idx: int, entry: float,
                   stop: float, target: float, max_bars: int,
                   time_stop: float | None = None) -> dict | None:
    """Stop-or-target-first walk forward from ``entry_idx`` (the entry bar).

    Conservative tie-break: if a single bar's range spans BOTH the stop and the
    target, assume the stop filled first (the pessimistic assumption — never
    credit the win we can't prove came first from daily bars).

    ``time_stop`` is the number of bars the SCANNER ITSELF declares a trade may
    run before being closed regardless of price — the missing time dimension in
    every structured plan (backlog B-5; [[concepts/Mean-Reversion]] names ~10
    bars as standard). When absent the trade simply runs to ``max_bars``, which
    is the measurement horizon rather than a decision, and the two are reported
    as different outcomes so a deliberate exit is never read as a stalled one.

    Returns None when the plan cannot be simulated long-only — a short-side plan
    (stop above entry) or a degenerate one. The caller counts these rather than
    letting them vanish: a scanner whose plans are all unsimulatable must not
    look like a scanner with no plans.
    """
    risk = entry - stop
    if risk <= 0:
        return None
    n = len(df)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)

    horizon = max_bars if time_stop is None else min(max_bars, int(time_stop))
    end = min(n - 1, entry_idx + horizon)
    for i in range(entry_idx, end + 1):
        hit_stop = low[i] <= stop
        hit_tgt = high[i] >= target
        if hit_stop:                       # pessimistic: stop wins a same-bar tie
            return {"outcome": "stop", "r": (stop - entry) / risk, "bars": i - entry_idx}
        if hit_tgt:
            return {"outcome": "target", "r": (target - entry) / risk, "bars": i - entry_idx}
    # Neither level hit. If the scanner declared a time stop and we reached it,
    # that is a planned exit ("time"); otherwise the trade merely ran out of
    # measurement window ("open") and is still live in reality.
    exit_px = close[end]
    timed_out = time_stop is not None and (end - entry_idx) >= horizon
    return {"outcome": "time" if timed_out else "open",
            "r": (exit_px - entry) / risk, "bars": end - entry_idx}


def backtest_scanner(scanner_name: str,
                     symbols: list[str],
                     fetch_fn,
                     horizons: tuple[int, ...] = DEFAULT_HORIZONS,
                     min_gap: int = DEFAULT_MIN_GAP,
                     warmup: int = WARMUP_BARS,
                     stride: int = 1) -> dict:
    """Replay ``scanner_name`` over ``symbols`` and return aggregate metrics.

    ``fetch_fn(symbol) -> OHLCV DataFrame`` (lowercase o/h/l/c/v columns). Use a
    long window (e.g. ``lambda s: fetch_ohlcv(s, days=1500)``) so there is enough
    history for a meaningful sample. ``stride`` evaluates every k-th bar to trade
    resolution for speed (default 1 = every bar); signals are still de-duplicated
    by ``min_gap``.
    """
    spec = sc.SCANNERS.get(scanner_name)
    if spec is None:
        return {"error": f"unknown scanner '{scanner_name}'"}
    fn = spec["fn"]
    max_h = max(horizons)

    # Per-signal forward returns (%), keyed by horizon; plus every-bar baseline
    # returns over the same replay window; plus R results where a plan existed.
    sig_ret: dict[int, list[float]] = {h: [] for h in horizons}
    base_ret: dict[int, list[float]] = {h: [] for h in horizons}
    mae_list: list[float] = []           # max adverse excursion per signal (%)
    r_results: list[dict] = []
    n_signals = 0
    n_symbols_used = 0
    total_bars = 0
    n_plans = 0                 # signals that carried a full entry/stop/target
    n_plans_unsimulated = 0     # …of which the long-only sim could not run

    for sym in symbols:
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        df = df.dropna(subset=["high", "low", "close", "volume"]).reset_index(drop=True)
        n = len(df)
        if n < warmup + max_h + 2:
            continue
        n_symbols_used += 1
        has_open = "open" in df.columns
        close = df["close"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        openp = df["open"].to_numpy(dtype=float) if has_open else close

        # Baseline: every eligible bar's forward returns (random entry in-tape).
        # Entry at t+1 open, exit at t+1+h close — identical timing to signals.
        last_eval = n - max_h - 2
        for t in range(warmup, last_eval + 1):
            total_bars += 1
            entry_b = openp[t + 1]
            if entry_b <= 0:
                continue
            for h in horizons:
                fwd = close[t + 1 + h]
                base_ret[h].append((fwd / entry_b - 1.0) * 100.0)

        # Signals: walk the same window, feed point-in-time slices.
        t = warmup
        while t <= last_eval:
            if stride > 1 and (t - warmup) % stride != 0:
                t += 1
                continue
            try:
                hit = fn(df.iloc[:t + 1])
            except Exception:
                hit = None
            if not hit:
                t += 1
                continue

            n_signals += 1
            entry_idx = t + 1
            entry_b = openp[entry_idx]
            if entry_b > 0:
                for h in horizons:
                    fwd = close[entry_idx + h]
                    sig_ret[h].append((fwd / entry_b - 1.0) * 100.0)
                # Max adverse excursion over the longest horizon.
                window_low = float(np.min(low[entry_idx:entry_idx + max_h + 1]))
                mae_list.append((window_low / entry_b - 1.0) * 100.0)

                # R-simulation when the scanner emitted a trade plan.
                entry_p = _to_float(hit.get("entry"))
                stop_p = _to_float(hit.get("stop"))
                tgt = hit.get("target")
                tgt_p = _to_float(tgt[0] if isinstance(tgt, (list, tuple)) and tgt else tgt)
                if entry_p and stop_p and tgt_p:
                    n_plans += 1
                    r = _simulate_plan(df, entry_idx, entry_p, stop_p, tgt_p,
                                       max_h, _to_float(hit.get("time_stop")))
                    if r:
                        r_results.append(r)
                    else:
                        # Long-only simulator: short-side and degenerate plans are
                        # counted, not dropped, so the report can say how much of
                        # the plan coverage it could actually measure.
                        n_plans_unsimulated += 1

            t += min_gap        # de-dup: skip ahead after a recorded signal

    return _aggregate(scanner_name, horizons, sig_ret, base_ret, mae_list,
                      r_results, n_signals, n_symbols_used, total_bars,
                      n_plans, n_plans_unsimulated)


def _aggregate(scanner_name, horizons, sig_ret, base_ret, mae_list, r_results,
               n_signals, n_symbols_used, total_bars,
               n_plans=0, n_plans_unsimulated=0) -> dict:
    per_h = {}
    for h in horizons:
        s = np.array(sig_ret[h], dtype=float)
        b = np.array(base_ret[h], dtype=float)
        if len(s) == 0:
            per_h[h] = {"n": 0}
            continue
        sig_avg = float(np.mean(s))
        base_avg = float(np.mean(b)) if len(b) else 0.0
        per_h[h] = {
            "n": int(len(s)),
            "hit_rate": round(float(np.mean(s > 0) * 100), 1),
            "avg_ret": round(sig_avg, 2),
            "median_ret": round(float(np.median(s)), 2),
            "baseline_avg": round(base_avg, 2),
            "edge": round(sig_avg - base_avg, 2),      # signal minus random-entry
            "baseline_hit_rate": round(float(np.mean(b > 0) * 100), 1) if len(b) else None,
        }

    r_block = None
    if not r_results and n_plans:
        # Every plan was unsimulatable. Report that explicitly — an empty R block
        # would otherwise be indistinguishable from a scanner emitting no plans.
        r_block = {"n_with_plan": 0, "plans_seen": int(n_plans),
                   "plans_unsimulated": int(n_plans_unsimulated),
                   "note": "no plan could be simulated long-only (short-side or degenerate)"}
    elif r_results:
        rs = np.array([x["r"] for x in r_results], dtype=float)
        wins = np.array([x["outcome"] == "target" for x in r_results])
        r_block = {
            "n_with_plan": int(len(rs)),
            "win_rate": round(float(np.mean(wins) * 100), 1),
            "avg_R": round(float(np.mean(rs)), 2),
            "expectancy_R": round(float(np.mean(rs)), 2),   # avg R per trade
            "target_hits": int(np.sum([x["outcome"] == "target" for x in r_results])),
            "stop_hits": int(np.sum([x["outcome"] == "stop" for x in r_results])),
            "open_exits": int(np.sum([x["outcome"] == "open" for x in r_results])),
            "time_exits": int(np.sum([x["outcome"] == "time" for x in r_results])),
            # Plan coverage. Without these two a scanner whose plans are all
            # short-side would report an empty R block indistinguishable from one
            # that emits no plans at all.
            "plans_seen": int(n_plans),
            "plans_unsimulated": int(n_plans_unsimulated),
        }

    return {
        "scanner": scanner_name,
        "n_signals": n_signals,
        "n_symbols_used": n_symbols_used,
        "baseline_bars": total_bars,
        "thin_sample": n_signals < MIN_SAMPLE,
        "horizons": per_h,
        "r_metrics": r_block,
        "mae_avg": round(float(np.mean(mae_list)), 2) if mae_list else None,
        "limitations": ["survivorship-bias", "no-costs-slippage", "history-depth-varies"],
    }


def format_report(result: dict) -> str:
    """Human-readable text report for one backtest result."""
    if "error" in result:
        return f"ERROR: {result['error']}"
    lines = []
    warn = "  ⚠ THIN SAMPLE — treat as directional only" if result["thin_sample"] else ""
    lines.append(f"=== {result['scanner']} ===")
    lines.append(f"signals={result['n_signals']}  symbols={result['n_symbols_used']}  "
                 f"baseline-bars={result['baseline_bars']}{warn}")
    lines.append(f"{'horizon':>8} {'n':>5} {'hit%':>6} {'avg%':>7} "
                 f"{'base%':>7} {'edge%':>7} {'med%':>7}")
    for h, m in result["horizons"].items():
        if m.get("n", 0) == 0:
            lines.append(f"{h:>7}d {'0':>5}  (no signals)")
            continue
        lines.append(f"{h:>7}d {m['n']:>5} {m['hit_rate']:>6} {m['avg_ret']:>7} "
                     f"{m['baseline_avg']:>7} {m['edge']:>+7} {m['median_ret']:>7}")
    if result["mae_avg"] is not None:
        lines.append(f"avg MAE over longest horizon: {result['mae_avg']}%")
    r = result["r_metrics"]
    if r and r.get("n_with_plan"):
        lines.append(f"trade-plan R: n={r['n_with_plan']} win%={r['win_rate']} "
                     f"expectancy={r['expectancy_R']}R "
                     f"(target={r['target_hits']}/stop={r['stop_hits']}"
                     f"/time={r.get('time_exits', 0)}/open={r['open_exits']})")
        # Plan coverage. A scanner can emit plans on every signal and still have
        # half of them unsimulatable (short-side); quoting the expectancy without
        # saying what fraction it was measured on is the partial-result habit.
        seen, unsim = r.get("plans_seen", 0), r.get("plans_unsimulated", 0)
        if unsim:
            lines.append(f"   plan coverage: {r['n_with_plan']}/{seen} simulated "
                         f"({unsim} skipped — short-side or degenerate, sim is long-only)")
    elif r:
        lines.append(f"trade-plan R: none simulatable — {r.get('note', '')} "
                     f"({r.get('plans_seen', 0)} plans seen)")
    else:
        lines.append("trade-plan R: (scanner emits no entry/stop/target — forward-return only)")
    lines.append(f"limitations: {', '.join(result['limitations'])}")
    return "\n".join(lines)


# Default liquid ~50-name universe for a v1 run (widen once the engine is trusted).
LIQUID_50 = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL",
    "ITC", "LT", "KOTAKBANK", "AXISBANK", "HINDUNILVR", "BAJFINANCE", "MARUTI",
    "ASIANPAINT", "TITAN", "SUNPHARMA", "WIPRO", "HCLTECH", "ULTRACEMCO",
    "NESTLEIND", "TATASTEEL", "JSWSTEEL", "POWERGRID", "NTPC", "ONGC",
    "COALINDIA", "M&M", "ADANIPORTS", "GRASIM", "TECHM", "BAJAJFINSV",
    "HDFCLIFE", "DRREDDY", "CIPLA", "DIVISLAB", "EICHERMOT", "HEROMOTOCO",
    "BRITANNIA", "BPCL", "IOC", "SHREECEM", "APOLLOHOSP", "TATACONSUM",
    "PIDILITIND", "DABUR", "SIEMENS", "HAVELLS", "DMART", "BAJAJ-AUTO",
]


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    import screener_pipeline as sp
    name = sys.argv[1] if len(sys.argv) > 1 else "RSI 60-40 Setup"
    syms = LIQUID_50
    res = backtest_scanner(name, syms, lambda s: sp.fetch_ohlcv(s, days=1500))
    print(format_report(res))
