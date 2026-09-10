#!/usr/bin/env python3
"""turnover_share.py — sector rotation stated in MONEY, not price.

B-62. Concept page: concepts/Turnover-Share-Rotation.md.

    share_s(t)    = turnover_s(t) / sum over sectors of turnover(t)
    d_share_D     = 100 * (share_s(t) - share_s(t-1))        percentage POINTS
    d_share_W     = 100 * (share_s(t) - share_s(t-5))

Two properties follow from the definition and both are the reason to prefer
share over raw turnover:

  * **Zero-sum by construction.** The shares sum to 1, so the delta column sums
    to zero and every sector that gains attention takes it from named others. A
    sector-RETURN column has no such constraint — on a broad rally everything is
    green and the ranking says very little.
  * **Scale-free.** A sector holding 6.8% of turnover on a heavy session and on a
    quiet one is doing the same thing. Raw rupees would call the heavy day inflow.

Hence percentage POINTS, not percent: 3.70% -> 6.65% is +2.95 pt, not +80%.

── What it cannot tell you, stated first ──────────────────────────────────────
**Turnover is UNSIGNED.** A sector taking share while its price falls is either
accumulation into weakness or distribution, and nothing here distinguishes them.
That is the whole limitation, and it is why this pairs with `money_flow.py`
(B-60): CMF places each close inside its own bar, so it supplies the direction
this cannot. Delta-share says WHERE the attention went; CMF says which side of
the range it closed on. **Neither is a signal alone.**

Observed on 2026-09-09, kept as the worked example: Information Technology took
**+2.70 pt of turnover share on a day NIFTY IT fell -3.24%.** Money in, price out.

── Turnover here is a PROXY ───────────────────────────────────────────────────
Real traded value comes from the exchange bhavcopy. This module computes
`close x volume` from the same daily bars the rest of the desk already pulls, so
it is a **proxy**, and it differs from true turnover by the gap between the close
and the day's volume-weighted average price. That error is small for a liquid
name and washes out further across a sector, but it is real and named rather than
implied. `TURNOVER_NOTE` carries the text so the page and the module cannot drift.

── Sector vocabulary ──────────────────────────────────────────────────────────
Buckets come from `sectors.symbol_map()` (B-64), NOT from a second local
taxonomy. A share is a ratio over a denominator; the denominator only means
something if every symbol is bucketed once, under one vocabulary, over a stable
universe.

── What this is NOT ───────────────────────────────────────────────────────────
A VIEW. No entry, stop or target; NOT registered in `scanner_templates.SCANNERS`;
never a confluence vote. Nothing here has been measured. The prior is explicitly
LOW — turnover concentration spikes on news, index rebalances, block deals and
expiry, none of which is rotation in the sense a trader means. The pre-registered
test lives in analyses/Open-Backlog.md (B-62) and expects no lift.

CLI:
    py -3 tools/turnover_share.py
    py -3 tools/turnover_share.py --universe niftytotalmarket --top 10
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

#: Trading-day offsets for the two delta columns.
DAY_OFFSET = 1
WEEK_OFFSET = 5

#: A sector computed from a handful of its members is not a sector reading.
#: Same threshold and same reasoning as money_flow.MIN_COVERAGE — the reader
#: should see the gap rather than a hole where a sector was.
MIN_COVERAGE = 0.5

TURNOVER_NOTE = ("Turnover is a proxy: close x volume from daily bars, not exchange "
                 "traded value. It differs from true turnover by the gap between the "
                 "close and the day's VWAP — small for liquid names, smaller again "
                 "across a sector, but real.")

UNSIGNED_NOTE = ("Turnover is unsigned: a sector taking share while its price falls is "
                 "either accumulation into weakness or distribution, and this cannot "
                 "tell you which. Read it beside the money-flow (CMF) grid, which is "
                 "signed. Neither is a signal alone.")


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Case-insensitive column fetch — same reason as `money_flow._col`:
    `trending_stocks._batch_history` returns yfinance's capitalised columns while
    the bhavcopy path and the tests use lowercase."""
    if name in df.columns:
        return df[name]
    lower = {str(c).lower(): c for c in df.columns}
    key = lower.get(name.lower())
    if key is None:
        raise KeyError(f"{name!r} not in {list(df.columns)[:8]}")
    return df[key]


def turnover_series(df: pd.DataFrame) -> pd.Series:
    """`close x volume` per bar — the proxy described in the module docstring."""
    c = pd.to_numeric(_col(df, "close"), errors="coerce").astype(float)
    v = pd.to_numeric(_col(df, "volume"), errors="coerce").astype(float)
    return (c * v).fillna(0.0)


def turnover_at(df: pd.DataFrame, offset: int = 0) -> Optional[float]:
    """One bar's turnover, `offset` trading days before the last bar."""
    if df is None or len(df) <= offset:
        return None
    try:
        s = turnover_series(df)
    except KeyError:
        return None
    v = float(s.iloc[len(s) - 1 - offset])
    return v if np.isfinite(v) else None


def sector_turnover(members: dict[str, pd.DataFrame], offset: int = 0) -> float:
    """Summed turnover across a sector's members for one bar.

    Summed, not averaged: this is a sector treated as one synthetic instrument,
    the same aggregation choice `money_flow.sector_cmf` makes and for the same
    reason — an average lets a small illiquid name weigh as much as a heavyweight,
    which is the opposite of "where the money went".
    """
    total = 0.0
    for d in members.values():
        t = turnover_at(d, offset)
        if t is not None:
            total += t
    return total


def shares(by_sector: dict[str, dict[str, pd.DataFrame]],
           offset: int = 0) -> dict[str, float]:
    """`{sector: share of total turnover}` for one bar. Shares sum to 1.0.

    An all-zero session (a holiday slipping into the frame, or a universe with no
    volume) returns an empty dict rather than dividing by zero and printing NaN
    shares that would still look like data.
    """
    raw = {s: sector_turnover(m, offset) for s, m in by_sector.items()}
    total = sum(raw.values())
    if total <= 0:
        return {}
    return {s: v / total for s, v in raw.items()}


def rotation_grid(universe: str = "nifty500",
                  hist: dict[str, pd.DataFrame] | None = None,
                  min_members: int = 3) -> dict[str, Any]:
    """One row per sector: turnover, share %, and delta share in POINTS (D and W).

    Rows carry `members`/`coverage` so a thin sector can say so rather than
    presenting three stocks as a sector view.
    """
    try:
        import sectors as sc
    except Exception as e:                                   # pragma: no cover
        return {"error": f"sectors unavailable: {e}", "rows": pd.DataFrame()}

    smap = sc.symbol_map(universe)
    if not smap:
        return {"error": "no constituents", "rows": pd.DataFrame()}

    by_sector_syms: dict[str, list[str]] = {}
    for sym, sector in smap.items():
        by_sector_syms.setdefault(sector, []).append(sym)

    symbols = sorted(smap)
    if hist is None:
        import trending_stocks as ts
        # Reuse the batched downloader rather than adding a second one.
        hist = ts._batch_history(symbols, period="3mo")

    by_sector: dict[str, dict[str, pd.DataFrame]] = {}
    cover: dict[str, tuple[int, int]] = {}
    for sector, syms in by_sector_syms.items():
        members = {s: hist[s] for s in syms if s in hist and hist[s] is not None}
        if len(members) < min_members:
            continue
        by_sector[sector] = members
        cover[sector] = (len(members), len(syms))

    if not by_sector:
        return {"error": "no sector had enough members with history",
                "rows": pd.DataFrame()}

    now = shares(by_sector, 0)
    prev_d = shares(by_sector, DAY_OFFSET)
    prev_w = shares(by_sector, WEEK_OFFSET)

    rows: list[dict[str, Any]] = []
    for sector, members in by_sector.items():
        n_have, n_all = cover[sector]
        s_now = now.get(sector)
        row: dict[str, Any] = {
            "sector": sector,
            "members": n_have,
            "of": n_all,
            "coverage": round(n_have / n_all, 2),
            "low_coverage": bool(n_have / n_all < MIN_COVERAGE),
            "turnover_cr": round(sector_turnover(members, 0) / 1e7, 1),
            "share_pct": None if s_now is None else round(100.0 * s_now, 2),
            "d_share_d": (None if (s_now is None or sector not in prev_d)
                          else round(100.0 * (s_now - prev_d[sector]), 2)),
            "d_share_w": (None if (s_now is None or sector not in prev_w)
                          else round(100.0 * (s_now - prev_w[sector]), 2)),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("d_share_d", ascending=False, na_position="last")
        df = df.reset_index(drop=True)
    return {
        "rows": df,
        "universe": universe,
        "n_symbols": len(symbols),
        "n_covered": sum(len(m) for m in by_sector.values()),
        "n_sectors": len(by_sector),
        "turnover_note": TURNOVER_NOTE,
        "unsigned_note": UNSIGNED_NOTE,
    }


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    ap = argparse.ArgumentParser(description="Sector turnover-share rotation (B-62)")
    ap.add_argument("--universe", default="nifty500")
    ap.add_argument("--top", type=int, default=0, help="show only the top N rows")
    args = ap.parse_args()

    g = rotation_grid(args.universe)
    if g.get("error"):
        print(g["error"])
        return 1
    df = g["rows"]
    if args.top:
        df = df.head(args.top)
    print(f"Turnover-share rotation — {g['universe']}, "
          f"{g['n_covered']}/{g['n_symbols']} symbols, {g['n_sectors']} sectors\n")
    cols = ["sector", "members", "turnover_cr", "share_pct", "d_share_d", "d_share_w"]
    print(df[cols].to_string(index=False))
    total = df["d_share_d"].dropna().sum() if "d_share_d" in df else 0.0
    print(f"\nSum of d_share_d over ALL sectors: {total:+.2f} pt "
          f"(zero-sum by construction; a few hundredths is the per-row "
          f"rounding to 2dp, more than that means --top clipped rows)")
    print(f"\n{g['unsigned_note']}")
    print(f"{g['turnover_note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
