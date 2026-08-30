"""scanner_overlap.py — which Scanner Hub scanners are measuring the same thing?

B-35 asks to collapse the 40-scanner list into family lenses, with a stated invariant:
**no unique hit may be lost**. That invariant cannot be checked from names or categories,
so this measures it.

Method: replay every registered scanner point-in-time over a universe (the same
`fn(df.iloc[:t+1])` idiom `backtest.backtest_scanner` uses), record the set of
(symbol, as-of date) cells each one fires on, and compare the SETS.

Three numbers, because they answer different questions:

  * **Jaccard** |A∩B| / |A∪B| — symmetric similarity. High = the two are near-clones.
  * **Containment** P(B fires | A fires) = |A∩B| / |A| — ASYMMETRIC, and the one that
    actually drives a merge decision. If 95% of B's hits are also A's hits but only 20%
    of A's are B's, then B is a strict-ish subset: dropping B loses almost nothing,
    dropping A loses a lot. Jaccard alone would call that pair "not very similar".
  * **Unique hits** |A minus every other scanner| — the B-35 invariant, per scanner. A
    scanner with zero unique cells is fully covered by the rest of the list.

Bearish/risk scanners are reported separately: a bullish and a bearish detector firing on
the same cell is a contradiction, not redundancy, and pooling them would invent overlap.

Deliberately NOT measured here: whether any scanner has *edge*. Two scanners can be
perfect clones and both be worthless. Overlap answers "is this list redundant?", which is
the question asked; `backtest.backtest_scanner` answers the other one.

CLI:
  py -3 tools/scanner_overlap.py                     # fetch (cached) + measure + report
  py -3 tools/scanner_overlap.py --limit 60 --asof 16
  py -3 tools/scanner_overlap.py --min-jaccard 0.5
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import pandas as pd

import scanner_templates as sc
import opportunity_hub as oh

HERE = Path(__file__).resolve().parent
FRAME_CACHE = HERE / "cache" / "overlap"
UNIVERSE_FILE = HERE / "cache" / "nse_nifty500_constituents.json"

WARMUP = 260          # every scanner needs a year-ish; ATH/IPO want far more (see report)
DEFAULT_DAYS = 1500
DEFAULT_LIMIT = 100
DEFAULT_ASOF = 24     # as-of dates per symbol, spread over the tail of the history


def universe(limit: int) -> list[str]:
    """A breadth sample of NIFTY-500, taken by fixed stride so it spans industries."""
    if not UNIVERSE_FILE.exists():
        sys.exit(f"missing {UNIVERSE_FILE}")
    names = [r["symbol"] for r in json.loads(UNIVERSE_FILE.read_text(encoding="utf-8"))]
    if limit >= len(names):
        return names
    step = max(1, len(names) // limit)
    return names[::step][:limit]


def load_frame(symbol: str, days: int = DEFAULT_DAYS) -> pd.DataFrame | None:
    """Cached OHLCV. Frames are settled history, so one fetch per symbol, ever.

    CSV rather than pickle deliberately: this is plain OHLCV, and a cache directory
    full of pickles is an arbitrary-code-execution surface for no benefit.

    ``days=0`` fetches the FULL listing history, which the `needs_full_history`
    scanners require to be measured honestly — see the note on `collect_hits`.
    Full-history frames cache separately so the two runs never mix.
    """
    cache_dir = FRAME_CACHE if days else FRAME_CACHE / "full"
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / f"{symbol}.csv"
    if p.exists():
        try:
            df = pd.read_csv(p, index_col=0, parse_dates=True)
            if not df.empty:
                return df
        except Exception:
            pass
    try:
        import screener_pipeline as sp
        df = sp.fetch_ohlcv(symbol, days=days)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    try:
        df.to_csv(p)
    except Exception:
        pass
    return df


def collect_hits(symbols: list[str], n_asof: int, days: int,
                 verbose: bool = True) -> tuple[dict[str, set], int]:
    """{scanner: {(symbol, date), ...}}, plus the number of cells evaluated.

    A "cell" is one (symbol, as-of date) pair — the unit of opportunity. Every scanner
    sees exactly the same cells, which is what makes the sets comparable.

    ── Why `days=0` (full history) is the honest setting ────────────────────────
    The replay hands each scanner ``df.iloc[:t+1]``, i.e. "everything known at t". That
    is only true if the frame STARTS at the listing. With a truncated window the slice
    silently lies to any scanner that reasons about the whole history:

      * `ATH Breakout` reads the slice max as an all-time high — on a 261-bar slice
        that is a one-year high, so it over-fires on fake ATHs;
      * `IPO-Base Breakout` gates on listing age as ``len(df)``, so at early as-of
        dates every stock looks freshly listed and it fires on 20-year-old companies.

    Neither error has a predictable direction, so counts from a truncated run are not
    "floors" — they are invalid for those two. Run with ``--days 0`` before drawing any
    conclusion about a `needs_full_history` scanner.
    """
    # Every REGISTERED scanner, including the pipeline-excluded ones: the Hub lists
    # them, so the audit has to say whether they overlap. The one true function-level
    # duplicate ("Zero-Debt Quality PEAD" shares scan_pead with "PEAD Drift") is dropped
    # because measuring a function against itself would report a spurious J=1.00.
    names = [n for n in sc.SCANNERS if n != "Zero-Debt Quality PEAD"]
    hits: dict[str, set] = {n: set() for n in names}
    cells = 0
    for i, sym in enumerate(symbols, 1):
        df = load_frame(sym, days)
        if df is None or len(df) < WARMUP + 30:
            continue
        n = len(df)
        # As-of bars spread across the tail, oldest-first, never the final bar.
        step = max(1, (n - WARMUP - 2) // n_asof)
        bars = list(range(WARMUP, n - 1, step))[:n_asof]
        for t in bars:
            window = df.iloc[:t + 1]
            asof = df.index[t]
            cells += 1
            for name in names:
                try:
                    if sc.SCANNERS[name]["fn"](window):
                        hits[name].add((sym, asof))
                except Exception:
                    continue
        if verbose and i % 10 == 0:
            print(f"  ...{i}/{len(symbols)} symbols, {cells} cells", flush=True)
    return hits, cells


def analyse(hits: dict[str, set], min_jaccard: float, min_contain: float) -> dict:
    risk = set(oh.RISK_SCANNERS)
    bull = {k: v for k, v in hits.items() if k not in risk}
    bear = {k: v for k, v in hits.items() if k in risk}

    def pairs_for(group: dict[str, set]) -> list[dict]:
        out = []
        for a, b in combinations(sorted(group), 2):
            A, B = group[a], group[b]
            if not A or not B:
                continue
            inter = len(A & B)
            if not inter:
                continue
            out.append({
                "a": a, "b": b, "na": len(A), "nb": len(B), "inter": inter,
                "jaccard": inter / len(A | B),
                "a_given_b": inter / len(B),      # share of B covered by A
                "b_given_a": inter / len(A),      # share of A covered by B
            })
        return sorted(out, key=lambda r: -r["jaccard"])

    def unique_for(group: dict[str, set]) -> list[dict]:
        out = []
        for name, S in group.items():
            others = set()
            for k, v in group.items():
                if k != name:
                    others |= v
            out.append({"name": name, "n": len(S), "unique": len(S - others)})
        return sorted(out, key=lambda r: (r["unique"], r["n"]))

    return {
        "bull_pairs": pairs_for(bull), "bear_pairs": pairs_for(bear),
        "bull_unique": unique_for(bull), "bear_unique": unique_for(bear),
        "counts": {k: len(v) for k, v in sorted(hits.items(), key=lambda kv: -len(kv[1]))},
        "min_jaccard": min_jaccard, "min_contain": min_contain,
    }


def format_report(res: dict, cells: int, n_sym: int) -> str:
    fam_of = {}
    for fam, members in oh.SCANNER_FAMILIES.items():
        for m in members:
            fam_of[m] = fam

    L = [f"Scanner overlap — {n_sym} symbols, {cells} (symbol, as-of) cells, "
         f"{len(res['counts'])} scanners replayed point-in-time",
         ""]

    L += ["FIRE RATE (how often each scanner fires at all)",
          f"  {'scanner':<34}{'hits':>7}{'rate':>8}   family"]
    L.append("  " + "-" * 72)
    for name, n in res["counts"].items():
        rate = n / cells * 100 if cells else 0
        tag = "RISK" if name in oh.RISK_SCANNERS else fam_of.get(name, "—")
        L.append(f"  {name:<34}{n:>7}{rate:>7.1f}%   {tag}")

    L += ["", "NEAR-CLONES (high Jaccard = the two fire on the same cells)",
          f"  showing pairs with Jaccard >= {res['min_jaccard']:.2f}"]
    shown = [p for p in res["bull_pairs"] if p["jaccard"] >= res["min_jaccard"]]
    if shown:
        L.append(f"  {'A':<30}{'B':<30}{'J':>6}{'A|B':>7}{'B|A':>7}")
        L.append("  " + "-" * 80)
        for p in shown:
            L.append(f"  {p['a']:<30}{p['b']:<30}{p['jaccard']:>6.2f}"
                     f"{p['a_given_b']:>7.0%}{p['b_given_a']:>7.0%}")
    else:
        L.append("  none — no two bullish scanners are near-clones at this threshold")

    L += ["", "SUBSUMED (one scanner's hits are mostly inside another's)",
          f"  'A covers B {res['min_contain']:.0%}+' means dropping B loses little that A "
          f"does not already flag"]
    subs = [p for p in res["bull_pairs"]
            if max(p["a_given_b"], p["b_given_a"]) >= res["min_contain"]]
    subs.sort(key=lambda p: -max(p["a_given_b"], p["b_given_a"]))
    if subs:
        L.append(f"  {'covered (drop candidate)':<32}{'covered by':<32}{'share':>7}{'n':>6}")
        L.append("  " + "-" * 80)
        for p in subs[:25]:
            if p["a_given_b"] >= p["b_given_a"]:
                inner, outer, share, n = p["b"], p["a"], p["a_given_b"], p["nb"]
            else:
                inner, outer, share, n = p["a"], p["b"], p["b_given_a"], p["na"]
            L.append(f"  {inner:<32}{outer:<32}{share:>7.0%}{n:>6}")
    else:
        L.append("  none at this threshold")

    L += ["", "UNIQUE CONTRIBUTION (the B-35 invariant, per scanner)",
          "  'unique' = cells this scanner alone flags. 0 = fully covered by the rest.",
          f"  {'scanner':<34}{'hits':>7}{'unique':>8}{'unique %':>10}"]
    L.append("  " + "-" * 62)
    for r in res["bull_unique"]:
        pct = (r["unique"] / r["n"] * 100) if r["n"] else 0
        L.append(f"  {r['name']:<34}{r['n']:>7}{r['unique']:>8}{pct:>9.0f}%")

    L += ["", "RISK / BEARISH scanners (kept separate — a bearish hit on a bullish cell",
          "is a contradiction, not redundancy)",
          f"  {'scanner':<34}{'hits':>7}{'unique':>8}"]
    L.append("  " + "-" * 52)
    for r in res["bear_unique"]:
        L.append(f"  {r['name']:<34}{r['n']:>7}{r['unique']:>8}")
    if res["bear_pairs"]:
        L.append("  near-clones among risk scanners:")
        for p in res["bear_pairs"][:8]:
            if p["jaccard"] >= 0.3:
                L.append(f"    {p['a']} ~ {p['b']}  J={p['jaccard']:.2f} "
                         f"(A|B {p['a_given_b']:.0%}, B|A {p['b_given_a']:.0%})")

    L += ["",
          "CAVEATS",
          "  * Overlap is not edge. Clones can both be worthless; see backtest.backtest_scanner.",
          "  * ATH / IPO-base breakout carry `needs_full_history` and are under-fed by the",
          "    fetch window here, so their hit counts are floors, not true rates.",
          "  * A rare scanner (few hits) has a noisy Jaccard; read its containment and",
          "    unique count instead.",
          ]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure Scanner Hub overlap (B-35)")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="symbols to sample")
    ap.add_argument("--asof", type=int, default=DEFAULT_ASOF, help="as-of dates per symbol")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--min-jaccard", type=float, default=0.40)
    ap.add_argument("--min-contain", type=float, default=0.80)
    ap.add_argument("--json", help="also write the raw sets/metrics here")
    args = ap.parse_args()

    syms = universe(args.limit)
    print(f"Universe: {len(syms)} symbols (NIFTY-500 stride sample). "
          f"Fetching/loading frames — first run downloads, later runs are cached.")
    hits, cells = collect_hits(syms, args.asof, args.days)
    if not cells:
        sys.exit("no cells evaluated — no frames loaded")
    res = analyse(hits, args.min_jaccard, args.min_contain)
    print()
    print(format_report(res, cells, len(syms)))
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"cells": cells, "counts": res["counts"],
             "pairs": res["bull_pairs"], "unique": res["bull_unique"]},
            indent=1), encoding="utf-8")
        print(f"\nraw metrics -> {args.json}")


if __name__ == "__main__":
    main()
