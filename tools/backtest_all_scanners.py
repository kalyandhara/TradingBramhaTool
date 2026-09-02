"""B-19 batch runner — walk-forward + Indian costs for every registered scanner.

Fetches OHLCV once per symbol, caches in memory, then runs walk_forward_scanner
on each scanner name.  Outputs a structured verdict report.

Usage:
    py -3 tools/backtest_all_scanners.py
    py -3 tools/backtest_all_scanners.py --dry-run        # list scanners, don't run
    py -3 tools/backtest_all_scanners.py --only "RSI 60-40 Setup,Stage 2 Uptrend"
"""
from __future__ import annotations

import io, json, os, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import screener_pipeline as sp
import scanner_templates as sc
from backtest import (
    LIQUID_50, COST_INDIAN,
    walk_forward_scanner, format_walk_forward,
    backtest_scanner, format_report,
)


SKIP = {
    "Zero-Debt Quality PEAD",       # needs yfinance fundamentals gate, not pure OHLCV
}

N_WINDOWS = 3
OUT_DIR = os.path.join(os.path.dirname(__file__), "cache", "b19_verdicts")


def _fetch_and_cache(symbols: list[str], days: int = 1500) -> dict:
    """Download OHLCV once per symbol and return {symbol: DataFrame}."""
    cache = {}
    for i, sym in enumerate(symbols, 1):
        print(f"  fetching {sym} ({i}/{len(symbols)}) …", end="", flush=True)
        try:
            df = sp.fetch_ohlcv(sym, days=days)
            if df is not None and not df.empty:
                cache[sym] = df
                print(f" {len(df)} bars")
            else:
                print(" (empty)")
        except Exception as e:
            print(f" ERROR: {e}")
    return cache


def main():
    dry_run = "--dry-run" in sys.argv
    resume = "--resume" in sys.argv
    only = None
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        only = [s.strip() for s in sys.argv[idx + 1].split(",")]

    all_names = sorted(sc.SCANNERS.keys())
    run_names = [n for n in all_names if n not in SKIP]
    if only:
        run_names = [n for n in run_names if n in only]

    if resume:
        done = set()
        summary_path = os.path.join(OUT_DIR, "_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                for r in json.load(f):
                    if "ERROR" not in str(r.get("verdict", "")):
                        done.add(r["scanner"])
        run_names = [n for n in run_names if n not in done]
        print(f"Resume mode: {len(done)} already done, {len(run_names)} remaining\n")

    risk_scanners = {n for n, spec in sc.SCANNERS.items()
                     if spec.get("category") == "Risk"}

    print(f"B-19 batch: {len(run_names)} scanners, {len(LIQUID_50)} symbols, "
          f"WF={N_WINDOWS}, cost=Indian delivery\n")

    if dry_run:
        for n in run_names:
            tag = " [RISK/bearish]" if n in risk_scanners else ""
            print(f"  {n}{tag}")
        print(f"\nSkipped: {SKIP}")
        return

    # Step 1: fetch all OHLCV once
    print("═══ Fetching OHLCV (one-time) ═══")
    ohlcv = _fetch_and_cache(LIQUID_50)
    syms = list(ohlcv.keys())
    fetch = lambda s: ohlcv[s]
    print(f"\n{len(syms)} symbols cached.\n")

    os.makedirs(OUT_DIR, exist_ok=True)

    # Step 2: run each scanner
    results = []
    for i, name in enumerate(run_names, 1):
        print(f"═══ [{i}/{len(run_names)}] {name} ═══")
        t0 = time.time()
        try:
            res = walk_forward_scanner(name, syms, fetch,
                                       n_windows=N_WINDOWS,
                                       cost_model=COST_INDIAN)
            elapsed = time.time() - t0
            report = format_walk_forward(res)
            print(report)
            print(f"  ({elapsed:.1f}s)\n")

            # Extract verdict from pooled OOS
            pooled = res.get("pooled", {})
            pooled_h = pooled.get("horizons", {})
            n_sig = pooled.get("n_signals", 0)
            is_risk = name in risk_scanners
            degradation = res.get("degradation", {})
            stability = res.get("stability", {})

            # Build edge dict keyed by horizon
            edges = {h: m.get("edge") for h, m in pooled_h.items() if m.get("edge") is not None}

            verdict = _derive_verdict(edges, n_sig, is_risk, degradation, stability)

            results.append({
                "scanner": name,
                "category": sc.SCANNERS[name].get("category", "?"),
                "n_signals": n_sig,
                "edges": edges,
                "stability": stability.get("verdict", "?"),
                "degradation": degradation,
                "verdict": verdict,
                "elapsed_s": round(elapsed, 1),
            })

            # Save individual report
            safe = name.replace("/", "-").replace(" ", "_")
            with open(os.path.join(OUT_DIR, f"{safe}.txt"), "w", encoding="utf-8") as f:
                f.write(report)

        except Exception as e:
            print(f"  ERROR: {e}\n")
            results.append({
                "scanner": name,
                "category": sc.SCANNERS[name].get("category", "?"),
                "verdict": f"ERROR: {e}",
            })

    # Step 3: summary
    print("\n" + "═" * 70)
    print("B-19 VERDICT SUMMARY")
    print("═" * 70)
    print(f"{'Scanner':<40} {'Cat':<10} {'Sig':>5} {'20d edge':>10} {'60d edge':>10} {'Verdict'}")
    print("─" * 100)
    for r in results:
        edges = r.get("edges", {})
        e20 = edges.get(20, edges.get("20"))
        e60 = edges.get(60, edges.get("60"))
        n = r.get("n_signals", "?")
        e20s = f"{e20:+.2f}%" if isinstance(e20, (int, float)) else "n/a"
        e60s = f"{e60:+.2f}%" if isinstance(e60, (int, float)) else "n/a"
        print(f"{r['scanner']:<40} {r.get('category','?'):<10} {n:>5} {e20s:>10} {e60s:>10} {r['verdict']}")

    # Save JSON + summary
    with open(os.path.join(OUT_DIR, "_summary.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull reports in {OUT_DIR}/")
    print(f"Summary JSON: {OUT_DIR}/_summary.json")


def _derive_verdict(edges, n_sig, is_risk, degradation, stability) -> str:
    if n_sig < 20:
        return "TOO FEW SIGNALS"

    e20 = edges.get(20)
    e60 = edges.get(60)

    if e20 is None and e60 is None:
        return "INCOMPLETE"

    # Use 20d as primary, fall back to 60d
    ep = e20 if e20 is not None else e60

    stab = stability.get("all_stable", False)
    stab_tag = "" if stab else " [UNSTABLE]"

    # For risk scanners, NEGATIVE edge is the desired direction
    if is_risk:
        if ep < 0:
            return f"BEARISH EDGE{stab_tag}"
        return f"NO BEARISH EDGE{stab_tag}"

    # Bullish scanners
    if ep > 0:
        v = "POSITIVE EDGE"
    elif ep == 0:
        v = "FLAT"
    else:
        v = "NO EDGE"

    return f"{v}{stab_tag}"


if __name__ == "__main__":
    main()
