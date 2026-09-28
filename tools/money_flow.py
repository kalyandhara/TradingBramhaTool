#!/usr/bin/env python3
"""money_flow.py — Chaikin Money Flow, per symbol and aggregated per SECTOR.

B-60. The desk has volume at PRICE (Volume Profile), volume SPIKES
(`volume_anomaly`) and no view of **where money is going by sector over time**.
This closes that, as a VIEW — see the bottom of this docstring.

Indicator reference: concepts/Chaikin-Money-Flow.md.

    MFM = ((C - L) - (H - C)) / (H - L)        close's place in its own bar, [-1, +1]
    MFV = MFM x Volume                          "money flow volume"
    CMF = sum(MFV, N) / sum(Volume, N)

── The aggregation choice IS the design, and the obvious one is wrong ──────────
Averaging constituent CMFs treats a Rs 200cr smallcap as equal to a Rs 5trn
heavyweight, so the sector reading gets driven by its tail — the most illiquid
names move the number most, which is the opposite of "where money went".

`sector_cmf` instead sums money-flow volume across the sector and divides by the
sector's summed volume:

    sector_CMF = sum(MFV over all constituents, N) / sum(Volume over all constituents, N)

That is CMF's own construction applied to the sector as ONE synthetic instrument.
It keeps the [-1, +1] bound and weights each name by the volume it actually
traded. `_MEAN_OF_MEMBERS` is kept as a comparison mode precisely so the two can
be shown to disagree rather than the choice being asserted.

── The columns are a LOOKBACK, not a history ──────────────────────────────────
`today / 1W / 2W / 1M` are each a 21-bar CMF ending at that date, so consecutive
columns share ~16 of their 21 bars. **They are not independent observations** and
a row agreeing across all four is one measurement smeared, not four
confirmations. `trend_label` exists to name the shape without implying otherwise,
and the UI caption must say so.

── What this is NOT ───────────────────────────────────────────────────────────
A VIEW, not a signal: no entry/stop/target, NOT registered in
`scanner_templates.SCANNERS`, and never a confluence vote. B-19 measured most
single-condition scanners negative after costs and this desk's volume tools ship
as attention lists; nothing here has been measured at all.

CMF also **ignores the previous close**, so gaps are invisible to it: a sector can
gap down, close sharply lower on heavy volume, and still print rising CMF.
Idiosyncratic gaps wash out in an aggregate; an INDEX-level gap does not.
`CAVEAT` carries that text so the page and the module cannot drift apart.

CLI:
    py -3 tools/money_flow.py                 # the sector grid
    py -3 tools/money_flow.py --universe nifty500 --n 21
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

#: Chaikin's standard window, roughly a trading month.
CMF_N = 21

#: Column offsets in TRADING days, matching the reference layout.
LOOKBACKS = [("today", 0), ("1W ago", 5), ("2W ago", 10), ("1M ago", 21)]

#: CMF is bounded [-1, +1] but lives inside roughly +-0.25 in practice, so the
#: heatmap clips here. Scaling to the theoretical bound would render every real
#: reading as near-white and throw away the whole point of a heatmap.
HEAT_CLIP = 0.25

#: A sector computed from a handful of its members is not a sector reading.
#: Cells below this coverage are returned with `low_coverage=True` rather than
#: dropped -- the reader should see the gap, not a hole where a sector was.
MIN_COVERAGE = 0.5

CAVEAT = ("CMF ignores the previous close, so gaps are invisible to it: a sector can "
          "gap down, close sharply lower on heavy volume, and still print rising CMF. "
          "Idiosyncratic gaps wash out across a sector; an index-level gap (budget "
          "day, a global risk event) does not.")


# ── per symbol ────────────────────────────────────────────────────────────────

def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Fetch a column case-insensitively.

    The two frames this module is handed use different conventions and both are
    legitimate: `trending_stocks._batch_history` passes yfinance's capitalised
    `High/Low/Close/Volume`, while the bhavcopy path and the tests use lowercase.
    Resolving here beats making every caller normalise -- and beats the
    alternative discovered on the first live run, which was a KeyError 300
    symbols into a download.
    """
    if name in df.columns:
        return df[name]
    lower = {str(c).lower(): c for c in df.columns}
    key = lower.get(name.lower())
    if key is None:
        raise KeyError(f"{name!r} not in {list(df.columns)[:8]}")
    return df[key]


def money_flow_volume(df: pd.DataFrame) -> pd.Series:
    """Signed volume by where each close sat inside its own bar.

    A zero-range bar (limit-locked, or a synthetic flat series) makes the
    multiplier 0/0. It is set to 0 -- undefined, contributing nothing -- rather
    than dropped, so the denominator in `cmf` still counts the volume that
    genuinely traded that day.
    """
    h = pd.to_numeric(_col(df, "high"), errors="coerce").astype(float)
    l = pd.to_numeric(_col(df, "low"), errors="coerce").astype(float)
    c = pd.to_numeric(_col(df, "close"), errors="coerce").astype(float)
    v = pd.to_numeric(_col(df, "volume"), errors="coerce").astype(float)
    rng = h - l
    with np.errstate(invalid="ignore", divide="ignore"):
        mfm = ((c - l) - (h - c)) / rng
    mfm = mfm.where(rng > 0, 0.0).fillna(0.0)
    return mfm * v.fillna(0.0)


def cmf(df: pd.DataFrame, n: int = CMF_N, offset: int = 0) -> Optional[float]:
    """CMF over the `n` bars ending `offset` trading days before the last bar."""
    if df is None or len(df) < n + offset:
        return None
    mfv = money_flow_volume(df)
    vol = pd.to_numeric(_col(df, "volume"), errors="coerce").astype(float).fillna(0.0)
    end = len(df) - offset
    mfv_w, vol_w = mfv.iloc[end - n:end], vol.iloc[end - n:end]
    tot = float(vol_w.sum())
    if tot <= 0:
        return None
    return round(float(mfv_w.sum()) / tot, 4)


def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume — cumulative sum of signed volume."""
    close = pd.to_numeric(_col(df, "close"), errors="coerce")
    vol = pd.to_numeric(_col(df, "volume"), errors="coerce").fillna(0.0)
    sign = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (sign * vol).cumsum()


# ── per sector ────────────────────────────────────────────────────────────────

def sector_cmf(members: dict[str, pd.DataFrame], n: int = CMF_N,
               offset: int = 0, mode: str = "volume_weighted") -> Optional[float]:
    """CMF for a whole sector. See the module docstring for why the default wins.

    `mode="mean_of_members"` is the naive average, kept so the two can be shown
    to disagree rather than the choice being asserted in a comment.
    """
    if not members:
        return None
    if mode == "mean_of_members":
        vals = [c for c in (cmf(d, n, offset) for d in members.values()) if c is not None]
        return round(float(np.mean(vals)), 4) if vals else None

    num = den = 0.0
    for d in members.values():
        if d is None or len(d) < n + offset:
            continue
        end = len(d) - offset
        try:
            mfv = money_flow_volume(d).iloc[end - n:end]
        except KeyError:            # a frame without OHLC is not a member
            continue
        vol = (pd.to_numeric(_col(d, "volume"), errors="coerce")
               .astype(float).fillna(0.0).iloc[end - n:end])
        num += float(mfv.sum())
        den += float(vol.sum())
    if den <= 0:
        return None
    return round(num / den, 4)


def trend_label(series: list[Optional[float]]) -> str:
    """Name the shape across the lookback columns, oldest-last as displayed.

    Pre-registered before it was written, so it stays a rule rather than a vibe:

        Accumulation   positive in every column
        Distribution   negative in every column
        Increasing     monotonically rising from oldest to newest, sign changes
        Decreasing     monotonically falling from oldest to newest, sign changes
        -              anything else

    The columns overlap by ~16 of 21 bars, so this describes a shape; it is NOT
    four independent confirmations and must not be presented as agreement.
    """
    vals = [v for v in series if v is not None]
    if len(vals) < 2:
        return "-"
    newest_first = vals
    oldest_first = list(reversed(vals))
    if all(v > 0 for v in vals):
        return "Accumulation"
    if all(v < 0 for v in vals):
        return "Distribution"
    rising = all(b >= a for a, b in zip(oldest_first, oldest_first[1:]))
    falling = all(b <= a for a, b in zip(oldest_first, oldest_first[1:]))
    if rising and newest_first[0] > 0:
        return "Increasing"
    if falling and newest_first[0] < 0:
        return "Decreasing"
    return "-"


def sector_grid(universe: str = "nifty500", n: int = CMF_N,
                lookbacks: list[tuple[str, int]] | None = None,
                hist: dict[str, pd.DataFrame] | None = None,
                min_members: int = 3) -> dict[str, Any]:
    """The heatmap frame: one row per sector, one column per lookback.

    Returns `{"rows": DataFrame, "n_symbols", "n_covered", "caveat", ...}`.
    Each row carries `members` and `coverage` so a thin sector can say so rather
    than presenting a two-stock average as a sector view.
    """
    lookbacks = lookbacks or LOOKBACKS
    try:
        import nse_universe as nu
    except Exception as e:
        return {"error": f"nse_universe unavailable: {e}", "rows": pd.DataFrame()}

    cons = nu.fetch_constituents(universe)
    if not cons:
        return {"error": "no constituents", "rows": pd.DataFrame()}

    by_sector: dict[str, list[str]] = {}
    for r in cons:
        ind = (r.get("industry") or "").strip()
        if ind:
            by_sector.setdefault(ind, []).append(str(r["symbol"]).strip())

    symbols = sorted({s for v in by_sector.values() for s in v})
    if hist is None:
        import trending_stocks as ts
        # Reuse the batched downloader rather than adding a second one. Needs
        # enough history for the deepest lookback plus the window.
        hist = ts._batch_history(symbols, period="6mo")

    rows: list[dict[str, Any]] = []
    for sector, syms in sorted(by_sector.items()):
        members = {s: hist[s] for s in syms if s in hist and hist[s] is not None}
        if len(members) < min_members:
            continue
        cov = len(members) / len(syms)
        row: dict[str, Any] = {
            "sector": sector,
            "members": len(members),
            "of": len(syms),
            "coverage": round(cov, 2),
            "low_coverage": bool(cov < MIN_COVERAGE),
        }
        vals: list[Optional[float]] = []
        for label, off in lookbacks:
            v = sector_cmf(members, n=n, offset=off)
            row[label] = v
            vals.append(v)
        row["trend"] = trend_label(vals)
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        first = lookbacks[0][0]
        df = df.sort_values(first, ascending=False, na_position="last")
        df = df.reset_index(drop=True)
    return {
        "rows": df,
        "columns": [c for c, _ in lookbacks],
        "n": n,
        "n_symbols": len(symbols),
        "n_covered": len(hist or {}),
        "universe": universe,
        "clip": HEAT_CLIP,
        "caveat": CAVEAT,
    }


def positive_sectors(grid: dict[str, Any], top_n: int = 5) -> pd.DataFrame:
    """Sectors with positive money flow TODAY, best first — the Home strip.

    A reading order, not a buy list. Nothing here has been measured.
    """
    df = grid.get("rows")
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    col = grid["columns"][0]
    out = df[df[col].notna() & (df[col] > 0)]
    return out.nlargest(min(top_n, len(out)), col).reset_index(drop=True)


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    ap = argparse.ArgumentParser(description="Sector money-flow grid (CMF)")
    ap.add_argument("--universe", default="nifty500")
    ap.add_argument("--n", type=int, default=CMF_N)
    args = ap.parse_args()

    g = sector_grid(args.universe, n=args.n)
    if g.get("error"):
        print(g["error"])
        return 1
    df = g["rows"]
    print(f"Sector money flow — CMF({g['n']}) over {g['universe']}, "
          f"{g['n_covered']}/{g['n_symbols']} symbols with history\n")
    cols = ["sector", "members"] + g["columns"] + ["trend"]
    print(df[cols].to_string(index=False))
    print(f"\nCAVEAT: {g['caveat']}")
    print("Columns are overlapping 21-bar windows, NOT independent observations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
