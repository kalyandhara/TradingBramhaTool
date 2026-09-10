#!/usr/bin/env python3
"""rs_walk.py — relative-strength rank as a WALK: T-30 → T-15 → T-5 → T0.

B-63b's last column, and the only one the teardown asked for that could not be
built as a column. Two things blocked it, and only one of them was real.

── Blocker 1, real: the existing rank has a moving denominator ────────────────
`scanner_templates._finalize_relative_strength` ranks `rs_raw` **across that
scan's matched set** — deliberately ("RS rank is by definition relative to the
rest of the scan"). A rank of 90 among 12 hits and 90 among 400 are different
statements, so four of them in a row plot a **changing population**, not a
moving stock. This module therefore computes a **universe-wide** rank: one fixed
denominator (every constituent with usable history), computed for every symbol
whether or not any scanner fired on it. It sits BESIDE the scan-relative rank
rather than replacing it; the two answer different questions and both are valid.

── Blocker 2, not real: "we would have to collect snapshots for a month" ──────
The backlog assumed the walk needed a daily snapshot table filled in over 30
sessions. It does not. **`rs_raw` as of a past date is a pure function of the
price series up to that date**, so the whole walk is computable TODAY from the
same history the desk already downloads. Persistence is a cache, not a
prerequisite — which is why this shipped as a column instead of a data-collection
project.

── What it still cannot escape: survivorship ──────────────────────────────────
The T-30 column ranks **today's universe** as it stood 30 sessions ago. A name
that has since been removed from the index is not in the denominator, and one
added since is — with 30 sessions of hindsight about its inclusion. The rank is
therefore *point-in-time in its prices* and *present-day in its membership*.
That is a real bias, it flatters the walk slightly, and it is the reason this is
a **reading of where attention has travelled, not a backtestable signal**.
`SURVIVORSHIP_NOTE` carries the text so the page cannot drift from the module.

── The arithmetic is borrowed, not reinvented ─────────────────────────────────
`_weighted_trailing_return` (IBD-style 63/126/189/252 at .4/.2/.2/.2) comes from
`scanner_templates` by import. A second copy would be the same idea drifting in
two places — the failure `test_renko_parity.py` exists to catch elsewhere.

CLI:
    py -3 tools/rs_walk.py --top 15
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

#: The walk's stops, in TRADING days back from the last bar. Matches the
#: reference layout (T-30 / T-15 / T-5 / T0), oldest first.
OFFSETS: list[tuple[str, int]] = [("t30", 30), ("t15", 15), ("t5", 5), ("t0", 0)]

#: Below this many ranked names a percentile is theatre, not a statistic.
MIN_UNIVERSE = 20

#: Bars needed before a weighted trailing return means anything. The weighting
#: reaches back 252 sessions; it degrades gracefully below that, but a name with
#: a few months of history is being ranked on a different measure from its peers.
MIN_BARS = 252

SURVIVORSHIP_NOTE = (
    "The T-30 column ranks TODAY'S universe as it stood 30 sessions ago: a name "
    "since removed from the index is not in the denominator, and one added since "
    "is. The prices are point-in-time; the membership is not. Read the walk as "
    "where attention has travelled, not as a signal — it has not been measured."
)


def _close(df: pd.DataFrame) -> Optional[pd.Series]:
    """The close series, case-insensitively, as float. None if absent."""
    if df is None or not hasattr(df, "columns"):
        return None
    col = "close" if "close" in df.columns else None
    if col is None:
        lower = {str(c).lower(): c for c in df.columns}
        col = lower.get("close")
    if col is None:
        return None
    return pd.to_numeric(df[col], errors="coerce").astype(float)


def weighted_return_asof(df: pd.DataFrame, offset: int = 0) -> Optional[float]:
    """The IBD-style weighted trailing return as of `offset` bars before the end.

    Slicing the series and handing it to the SAME function the scanners use is
    the whole trick: no as-of logic is reimplemented, so a change to the
    weighting reaches this module for free.
    """
    c = _close(df)
    if c is None:
        return None
    end = len(c) - offset
    if end < MIN_BARS:
        return None
    try:
        from scanner_templates import _weighted_trailing_return
    except Exception as e:                                   # pragma: no cover
        log.warning("scanner_templates unavailable: %s", e)
        return None
    v = _weighted_trailing_return(c.iloc[:end])
    return float(v) if np.isfinite(v) else None


def percentile_ranks(values: dict[str, float]) -> dict[str, int]:
    """Cross-sectional 0-100 percentile, worst = 0, best = 100.

    Same convention as `_finalize_relative_strength` so a reader moving between
    the two is not silently reading an inverted scale. Ties take the same rank
    (the average of the positions they span) rather than an arbitrary order,
    because a coin-flip between two identical returns is not information.
    """
    if len(values) < 2:
        return {k: 50 for k in values}
    s = pd.Series(values, dtype=float)
    pct = s.rank(method="average", pct=True) * 100.0
    return {k: int(round(v)) for k, v in pct.items()}


def rank_against(distribution: list[float], value: float) -> int:
    """Where `value` sits inside a distribution it is NOT a member of, 0-100.

    This is what lets a name be ranked without being in the index. Membership of
    the nifty500 is not a prerequisite for asking "how does this return compare
    with the market's" — the universe is the **yardstick**, and a micro-cap
    measured against it is a meaningful reading, while a micro-cap measured
    against nothing is not.

    The distribution is unchanged by the guest: adding outsiders to the
    denominator would make the yardstick depend on who happened to be on a
    watchlist, and two users would then get different ranks for the same stock.
    """
    if not distribution:
        return 50
    below = sum(1 for v in distribution if v < value)
    ties = sum(1 for v in distribution if v == value)
    # Midpoint of the tied band, matching the "average" convention used by
    # percentile_ranks so a member and a guest are scored the same way.
    return int(round((below + ties / 2.0) / len(distribution) * 100.0))


def walk_grid(universe: str = "nifty500",
              hist: dict[str, pd.DataFrame] | None = None,
              benchmark: pd.DataFrame | None = None,
              offsets: list[tuple[str, int]] | None = None,
              min_universe: int = MIN_UNIVERSE,
              extra_hist: dict[str, pd.DataFrame] | None = None) -> dict[str, Any]:
    """`{symbol: {"t30": int|None, ..., "t0": int|None}}` plus run metadata.

    Excess return over the benchmark is used when one is supplied, matching
    `_rs_raw`; absolute weighted return otherwise. The benchmark is measured at
    the SAME offset as the stock — comparing today's stock against a
    month-old index would manufacture a trend out of the index's own drift.

    `extra_hist` ranks symbols that are NOT constituents — a watchlist of
    micro-caps, say — against the universe's distribution **without adding them
    to it**. Without this the column is empty for exactly the names a personal
    watchlist is made of, which is how it first shipped and why this exists.
    Those rows are flagged `in_universe: False`.
    """
    offsets = offsets or OFFSETS
    if hist is None:
        try:
            import sectors as sc
            import trending_stocks as ts
        except Exception as e:                               # pragma: no cover
            return {"error": f"universe unavailable: {e}", "ranks": {}}
        symbols = sorted(sc.symbol_map(universe))
        if not symbols:
            return {"error": "no constituents", "ranks": {}}
        hist = ts._batch_history(symbols, period="2y")

    extra_hist = extra_hist or {}
    guests = {s: d for s, d in extra_hist.items() if s not in hist}
    ranks: dict[str, dict[str, Optional[int]]] = {s: {} for s in list(hist) + list(guests)}
    for sym in ranks:
        ranks[sym]["in_universe"] = sym in hist
    covered: dict[str, int] = {}
    for label, off in offsets:
        bench = weighted_return_asof(benchmark, off) if benchmark is not None else None
        raw: dict[str, float] = {}
        for sym, df in hist.items():
            v = weighted_return_asof(df, off)
            if v is not None:
                raw[sym] = v - (bench or 0.0)
        covered[label] = len(raw)
        if len(raw) < min_universe:
            # Too few names to call anything a percentile. Say so with None
            # rather than ranking six stocks 0-100 and letting it look precise.
            for sym in ranks:
                ranks[sym][label] = None
            continue
        pct = percentile_ranks(raw)
        for sym in hist:
            ranks[sym][label] = pct.get(sym)
        dist = list(raw.values())
        for sym, df in guests.items():
            v = weighted_return_asof(df, off)
            ranks[sym][label] = (None if v is None
                                 else rank_against(dist, v - (bench or 0.0)))

    return {
        "ranks": ranks,
        "columns": [lbl for lbl, _ in offsets],
        "universe": universe,
        "n_symbols": len(hist),
        "n_ranked": covered,
        "n_guests": len(guests),
        "benchmark": benchmark is not None,
        "survivorship_note": SURVIVORSHIP_NOTE,
    }


def format_walk(row: dict[str, Optional[int]],
                columns: list[str] | None = None) -> str:
    """`"18 → 86 → 95 → 99"`, oldest first, `?` where the name lacked history.

    `?` is not decoration: an IPO has no rank 30 sessions before it listed, and
    printing 0 or a blank there would read as "weakest" or "missing data"
    instead of "did not exist yet".
    """
    cols = columns or [lbl for lbl, _ in OFFSETS]
    parts = []
    for c in cols:
        v = row.get(c) if row else None
        parts.append("?" if v is None else str(v))
    return " → ".join(parts)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    logging.basicConfig(level=logging.WARNING)
    ap = argparse.ArgumentParser(description="Universe-wide RS rank walk (B-63b)")
    ap.add_argument("--universe", default="nifty500")
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    try:
        import screener_pipeline as sp
        bench = sp.fetch_nifty50(days=760)
    except Exception:
        bench = None

    g = walk_grid(args.universe, benchmark=bench)
    if g.get("error"):
        print(g["error"])
        return 1
    cols = g["columns"]
    rows = [(s, r) for s, r in g["ranks"].items() if r.get("t0") is not None]
    rows.sort(key=lambda kv: kv[1]["t0"], reverse=True)
    print(f"RS rank walk — {g['universe']}, {g['n_symbols']} symbols, "
          f"ranked per column: {g['n_ranked']}, "
          f"benchmark {'ON' if g['benchmark'] else 'OFF'}\n")
    print(f"{'symbol':16} {'T-30 → T-15 → T-5 → T0'}")
    for sym, r in rows[:args.top]:
        print(f"{sym:16} {format_walk(r, cols)}")
    print(f"\n{g['survivorship_note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
