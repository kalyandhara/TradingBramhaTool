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
from scipy import stats

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
                     stride: int = 1,
                     benchmark_df: "pd.DataFrame | None" = None) -> dict:
    """Replay ``scanner_name`` over ``symbols`` and return aggregate metrics.

    ``fetch_fn(symbol) -> OHLCV DataFrame`` (lowercase o/h/l/c/v columns). Use a
    long window (e.g. ``lambda s: fetch_ohlcv(s, days=1500)``) so there is enough
    history for a meaningful sample. ``stride`` evaluates every k-th bar to trade
    resolution for speed (default 1 = every bar); signals are still de-duplicated
    by ``min_gap``.

    ``benchmark_df`` (optional) — a Nifty50 / index OHLCV frame with a DatetimeIndex
    and a ``close`` column. When supplied, each signal's forward return is also
    computed against the benchmark over the same window, enabling:
      * market-model alpha  = signal_ret - β_symbol × benchmark_ret  (B-20b)
      * OLS β estimated from the 60-bar pre-signal window               (B-20b)
    The t-stat / p-value / 95% CI for the raw edge and for the alpha are both
    reported so the numbers can no longer be quoted without a noise-probability
    caveat (B-20a).
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
    # Market-model: parallel lists for the benchmark return and estimated alpha
    # at each signal, per horizon.  Only populated when benchmark_df is supplied.
    mkt_ret: dict[int, list[float]] = {h: [] for h in horizons}
    alpha_ret: dict[int, list[float]] = {h: [] for h in horizons}
    mae_list: list[float] = []           # max adverse excursion per signal (%)
    r_results: list[dict] = []
    n_signals = 0
    n_symbols_used = 0
    total_bars = 0
    n_plans = 0                 # signals that carried a full entry/stop/target
    n_plans_unsimulated = 0     # …of which the long-only sim could not run

    # Pre-process benchmark into a date→close map for fast lookups.
    bench_close: pd.Series | None = None
    if benchmark_df is not None and "close" in benchmark_df.columns:
        bench_close = benchmark_df["close"].dropna()

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
                # ── market-model beta from the 60-bar pre-signal window ──────
                _beta: float | None = None
                if bench_close is not None and hasattr(df.index, "date"):
                    try:
                        _sym_px = df["close"].iloc[max(0, t - 60): t + 1]
                        _sym_r = _sym_px.pct_change().dropna()
                        # Align benchmark returns to the same dates
                        _b_px = bench_close.reindex(_sym_r.index, method="nearest",
                                                     tolerance=pd.Timedelta("2d"))
                        _b_r = _b_px.pct_change().dropna()
                        _both = pd.concat([_sym_r, _b_r], axis=1).dropna()
                        if len(_both) >= 20:
                            _beta = float(
                                np.cov(_both.iloc[:, 0], _both.iloc[:, 1])[0, 1]
                                / max(np.var(_both.iloc[:, 1]), 1e-12)
                            )
                    except Exception:
                        _beta = None

                for h in horizons:
                    fwd = close[entry_idx + h]
                    sr = (fwd / entry_b - 1.0) * 100.0
                    sig_ret[h].append(sr)

                    # Market return for the same forward window (by date index)
                    if bench_close is not None and hasattr(df.index, "date"):
                        try:
                            _entry_date = df.index[entry_idx]
                            _exit_date = df.index[min(entry_idx + h, len(df) - 1)]
                            _b_entry = float(bench_close.asof(_entry_date))
                            _b_exit = float(bench_close.asof(_exit_date))
                            _mr = (_b_exit / _b_entry - 1.0) * 100.0
                            mkt_ret[h].append(_mr)
                            # alpha = raw_ret - β × mkt_ret; fall back to β=1 if unknown
                            _b = _beta if _beta is not None else 1.0
                            alpha_ret[h].append(sr - _b * _mr)
                        except Exception:
                            pass

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
                      n_plans, n_plans_unsimulated,
                      mkt_ret=mkt_ret, alpha_ret=alpha_ret)


def _ttest_edge(arr: np.ndarray, null: float = 0.0) -> dict:
    """One-sample t-test: H0 = mean equals null.  Returns t, p, 95% CI."""
    n = len(arr)
    if n < 4:
        return {"t": None, "p": None, "ci95": None, "reliable": False}
    t, p = stats.ttest_1samp(arr, null)
    ci = stats.t.interval(0.95, df=n - 1, loc=float(np.mean(arr)),
                          scale=stats.sem(arr))
    return {
        "t": round(float(t), 3),
        "p": round(float(p), 4),
        "ci95": [round(float(ci[0]), 3), round(float(ci[1]), 3)],
        "reliable": bool(p < 0.05),   # two-tailed α=0.05
    }


def _aggregate(scanner_name, horizons, sig_ret, base_ret, mae_list, r_results,
               n_signals, n_symbols_used, total_bars,
               n_plans=0, n_plans_unsimulated=0,
               mkt_ret=None, alpha_ret=None) -> dict:
    per_h = {}
    for h in horizons:
        s = np.array(sig_ret[h], dtype=float)
        b = np.array(base_ret[h], dtype=float)
        if len(s) == 0:
            per_h[h] = {"n": 0}
            continue
        sig_avg = float(np.mean(s))
        base_avg = float(np.mean(b)) if len(b) else 0.0
        edge_arr = s - base_avg          # each signal's excess over the random-entry mean

        m: dict = {
            "n": int(len(s)),
            "hit_rate": round(float(np.mean(s > 0) * 100), 1),
            "avg_ret": round(sig_avg, 2),
            "median_ret": round(float(np.median(s)), 2),
            "baseline_avg": round(base_avg, 2),
            "edge": round(sig_avg - base_avg, 2),      # signal minus random-entry
            "baseline_hit_rate": round(float(np.mean(b > 0) * 100), 1) if len(b) else None,
            # B-20a — significance: is the edge distinguishable from noise?
            "edge_ttest": _ttest_edge(edge_arr),
        }

        # B-20b — market-model alpha when benchmark data was supplied.
        a_arr = np.array((alpha_ret or {}).get(h, []), dtype=float)
        if len(a_arr) >= 4:
            m["alpha_avg"] = round(float(np.mean(a_arr)), 2)
            m["alpha_ttest"] = _ttest_edge(a_arr)
        else:
            m["alpha_avg"] = None
            m["alpha_ttest"] = None

        per_h[h] = m

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
    has_alpha = any(m.get("alpha_avg") is not None
                    for m in result["horizons"].values() if m.get("n", 0) > 0)
    hdr = (f"{'horizon':>8} {'n':>5} {'hit%':>6} {'avg%':>7} "
           f"{'base%':>7} {'edge%':>7} {'p(edge)':>9} {'med%':>7}")
    if has_alpha:
        hdr += f"  {'alpha%':>7} {'p(α)':>7}"
    lines.append(hdr)
    for h, m in result["horizons"].items():
        if m.get("n", 0) == 0:
            lines.append(f"{h:>7}d {'0':>5}  (no signals)")
            continue
        tt = m.get("edge_ttest") or {}
        p_str = f"{tt['p']:.4f}" if tt.get("p") is not None else "   n/a"
        sig_mark = "*" if tt.get("reliable") else " "
        row = (f"{h:>7}d {m['n']:>5} {m['hit_rate']:>6} {m['avg_ret']:>7} "
               f"{m['baseline_avg']:>7} {m['edge']:>+7} {p_str:>9}{sig_mark}"
               f" {m['median_ret']:>7}")
        if has_alpha:
            at = m.get("alpha_ttest") or {}
            ap_str = f"{at['p']:.4f}" if at.get("p") is not None else "    n/a"
            a_sig = "*" if at.get("reliable") else " "
            a_avg = m.get("alpha_avg")
            row += f"  {(f'{a_avg:+.2f}' if a_avg is not None else '    n/a'):>7} {ap_str:>7}{a_sig}"
        lines.append(row)
    if has_alpha:
        lines.append("  (* = p<0.05 two-tailed; alpha = market-model excess return)")
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


def backtest_confluence(scanner_names: list[str],
                        symbols: list[str],
                        fetch_fn,
                        horizons: tuple[int, ...] = DEFAULT_HORIZONS,
                        min_gap: int = DEFAULT_MIN_GAP,
                        warmup: int = WARMUP_BARS,
                        min_cofiring: int = 2) -> dict:
    """Measure whether co-firing (≥ min_cofiring scanners agreeing on the same
    bar) beats any single-scanner fire over the same symbols and tape.

    This tests the Opportunity Hub's core premise: that confluence is additive.
    If it is, co-firing bars should show materially higher forward returns than
    single-fire bars, and the difference should be statistically significant.

    Returns a dict with keys:
      ``single``  — aggregate metrics for bars where exactly 1 scanner fired
      ``cofired`` — aggregate metrics for bars where ≥ min_cofiring fired
      ``lift``    — cofired.avg_ret - single.avg_ret per horizon
      ``lift_ttest`` — t-test on whether lift differs from zero (B-20a applied
                       to the confluence question)
    """
    # Build a function map: scanner_name → scan_fn
    fns: dict[str, object] = {}
    for name in scanner_names:
        spec = sc.SCANNERS.get(name)
        if spec:
            fns[name] = spec["fn"]
    if len(fns) < 2:
        return {"error": "need at least 2 valid scanner names"}

    max_h = max(horizons)
    single_ret: dict[int, list[float]] = {h: [] for h in horizons}
    co_ret:     dict[int, list[float]] = {h: [] for h in horizons}

    for sym in symbols:
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        df = df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
        n = len(df)
        if n < warmup + max_h + 2:
            continue

        has_open = "open" in df.columns
        close = df["close"].to_numpy(dtype=float)
        openp = df["open"].to_numpy(dtype=float) if has_open else close

        last_signal_bar: dict[str, int] = {}   # de-dup per scanner
        last_co_bar = -min_gap                  # de-dup for co-fire events

        t = warmup
        last_eval = n - max_h - 2
        while t <= last_eval:
            fired = []
            for name, fn in fns.items():
                # enforce min_gap per-scanner
                if t - last_signal_bar.get(name, -min_gap) < min_gap:
                    continue
                try:
                    hit = fn(df.iloc[:t + 1])
                except Exception:
                    hit = None
                if hit:
                    fired.append(name)

            entry_idx = t + 1
            entry_b = openp[entry_idx]
            if entry_b > 0 and fired:
                is_co = len(fired) >= min_cofiring
                # co-fire: de-dup so we don't count the same burst multiple times
                if is_co and (t - last_co_bar) < min_gap:
                    is_co = False
                for name in fired:
                    last_signal_bar[name] = t
                if is_co:
                    last_co_bar = t
                bucket = co_ret if is_co else single_ret
                for h in horizons:
                    fwd = close[entry_idx + h]
                    bucket[h].append((fwd / entry_b - 1.0) * 100.0)

            t += 1

    # Aggregate and compare
    result_single = {}
    result_co = {}
    lift = {}
    lift_ttest = {}
    for h in horizons:
        s = np.array(single_ret[h], dtype=float)
        c = np.array(co_ret[h], dtype=float)
        result_single[h] = {
            "n": len(s),
            "avg_ret": round(float(np.mean(s)), 2) if len(s) else None,
            "hit_rate": round(float(np.mean(s > 0) * 100), 1) if len(s) else None,
        }
        result_co[h] = {
            "n": len(c),
            "avg_ret": round(float(np.mean(c)), 2) if len(c) else None,
            "hit_rate": round(float(np.mean(c > 0) * 100), 1) if len(c) else None,
        }
        if len(s) >= 4 and len(c) >= 4:
            _lift = float(np.mean(c)) - float(np.mean(s))
            lift[h] = round(_lift, 2)
            # Two-sample t-test: is the co-fired mean significantly higher?
            t2, p2 = stats.ttest_ind(c, s, equal_var=False, alternative="greater")
            lift_ttest[h] = {
                "lift": round(_lift, 2),
                "t": round(float(t2), 3),
                "p_one_tail": round(float(p2), 4),
                "reliable": bool(p2 < 0.05),
            }
        else:
            lift[h] = None
            lift_ttest[h] = {"lift": None, "reliable": False,
                             "note": "thin sample — need ≥4 events in each bucket"}

    return {
        "scanners": list(fns.keys()),
        "min_cofiring": min_cofiring,
        "single": result_single,
        "cofired": result_co,
        "lift_per_horizon": lift,
        "lift_ttest": lift_ttest,
        "premise_supported": any(v.get("reliable") for v in lift_ttest.values()),
    }


def format_confluence_report(result: dict) -> str:
    """Human-readable report for backtest_confluence."""
    if "error" in result:
        return f"ERROR: {result['error']}"
    lines = [
        "=== Confluence Backtest ===",
        f"scanners: {', '.join(result['scanners'])}",
        f"co-fire threshold: ≥{result['min_cofiring']}",
        "",
        f"{'horizon':>8}  {'single n':>9} {'single%':>8}  {'cofired n':>9} "
        f"{'cofired%':>8}  {'lift%':>7} {'p(lift)':>8}",
    ]
    for h in result["single"]:
        s = result["single"][h]
        c = result["cofired"][h]
        lt = result["lift_ttest"].get(h, {})
        s_avg = f"{s['avg_ret']:+.2f}" if s.get("avg_ret") is not None else "  n/a"
        c_avg = f"{c['avg_ret']:+.2f}" if c.get("avg_ret") is not None else "  n/a"
        lift_s = f"{lt['lift']:+.2f}" if lt.get("lift") is not None else "   n/a"
        p_s = f"{lt['p_one_tail']:.4f}" if lt.get("p_one_tail") is not None else "    n/a"
        sig = "*" if lt.get("reliable") else " "
        lines.append(
            f"{h:>7}d  {s['n']:>9} {s_avg:>8}  {c['n']:>9} {c_avg:>8}"
            f"  {lift_s:>7} {p_s:>8}{sig}"
        )
    verdict = ("SUPPORTED — co-firing beats single-firing (p<0.05, one-tail)"
               if result.get("premise_supported")
               else "NOT SUPPORTED — co-firing lift not statistically significant")
    lines += ["", f"Confluence premise: {verdict}",
              "  (* = one-tailed p<0.05: co-fired mean > single mean)"]
    return "\n".join(lines)


def sweep_volume_threshold(scanner_name: str,
                           symbols: list[str],
                           fetch_fn,
                           thresholds: tuple[float, ...] = (1.0, 1.2, 1.5, 2.0),
                           horizons: tuple[int, ...] = (10, 20),
                           **backtest_kwargs) -> dict:
    """Sweep volume confirmation multipliers to find the best edge cutoff (B-7).

    For each ``threshold`` in ``thresholds``, wraps the target scanner so that
    its ``vol_x50d`` field must meet the threshold before the signal is counted.
    This is a post-hoc filter on the scanner output — it is NOT the same as
    re-parameterising the scanner's internal logic (some scanners gate on volume
    internally, some score it as a bonus). The sweep tells you: "given this
    scanner's universe of hits, what vol_x multiplier floor maximises edge?"

    Returns a dict keyed by threshold, each containing the backtest result for
    that vol floor, plus a ``best_threshold`` key pointing to whichever threshold
    produced the highest mean edge across all horizons.
    """
    spec = sc.SCANNERS.get(scanner_name)
    if spec is None:
        return {"error": f"unknown scanner '{scanner_name}'"}
    base_fn = spec["fn"]
    results = {}

    for thresh in thresholds:
        # Wrap: only pass through hits that meet the vol threshold
        def _gated(df, _t=thresh, _fn=base_fn):
            hit = _fn(df)
            if hit is None:
                return None
            vx = hit.get("vol_x50d", hit.get("vol_x", None))
            if vx is not None and vx < _t:
                return None
            return hit

        # Temporarily register the gated scanner so backtest_scanner can find it
        _tmp_name = f"__sweep_{scanner_name}_{thresh}"
        sc.SCANNERS[_tmp_name] = {"fn": _gated, "category": "sweep", "description": ""}
        r = backtest_scanner(_tmp_name, symbols, fetch_fn,
                             horizons=horizons, **backtest_kwargs)
        del sc.SCANNERS[_tmp_name]
        r["vol_threshold"] = thresh
        results[thresh] = r

    # Find the threshold with the best average edge across all horizons
    def _avg_edge(r):
        edges = [m.get("edge", 0) or 0 for m in r.get("horizons", {}).values()
                 if m.get("n", 0) > 0]
        return float(np.mean(edges)) if edges else float("-inf")

    best = max(thresholds, key=lambda t: _avg_edge(results[t]))
    return {"results": results, "best_threshold": best,
            "scanner": scanner_name, "thresholds_tested": list(thresholds)}


def format_volume_sweep(sweep: dict) -> str:
    """Human-readable report for sweep_volume_threshold."""
    if "error" in sweep:
        return f"ERROR: {sweep['error']}"
    lines = [
        f"=== Volume Threshold Sweep — {sweep['scanner']} ===",
        f"best threshold: {sweep['best_threshold']}×",
        "",
        f"{'vol≥':>6}  {'signals':>8}  " +
        "  ".join(f"{'edge@' + str(h) + 'd':>10}" for h in
                  (list(next(iter(sweep['results'].values()))
                        .get('horizons', {}).keys()))),
    ]
    for thresh, r in sweep["results"].items():
        n = r.get("n_signals", 0)
        edges = [f"{m.get('edge', 0):>+9.2f}"
                 for m in r.get("horizons", {}).values()]
        lines.append(f"{thresh:>5}×  {n:>8}  " + "  ".join(edges))
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
