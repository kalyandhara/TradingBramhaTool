#!/usr/bin/env python3
"""row_metrics.py — the per-row columns a screener table owes its reader.

B-63b, from the ScreeningMantis column teardown
(sources/ScreeningMantis-Price-Volume-Sector-Rotation-2026-09-09.md).

The pattern worth stealing was not any one indicator. It was that their table
answers **"how long has this been true?"** while every table on this desk
answered only **"is it true now?"** A 10x20 EMA cross that happened 28 sessions
ago reads nothing like one that happened this morning, and until now nowhere in
this repo could say which it was.

Everything here is computed from daily bars the desk already pulls. No new data
source, no vendor, no auth.

── What these are NOT ─────────────────────────────────────────────────────────
Descriptions of state, not signals. Nothing here is registered in
`scanner_templates.SCANNERS`, nothing casts a confluence vote, and nothing has
been measured — because there is nothing to measure: these report conditions
that are already computed elsewhere, they do not claim any of them predicts a
return.

── Two things deliberately NOT built here ─────────────────────────────────────
**Stage 2 as a count already exists.** `screener_pipeline.score_minervini`
returns `(0-8, conditions)` and the Watchlist has been rendering it as "x/8" all
along. The gap the teardown found is real but narrower than it looked: the
SCANNER (`scanner_templates.scan_stage2_uptrend`) is a hard gate that returns
None on any failed leg. Surfacing the existing score is the fix; a second
Stage-2 scorer would be two implementations of one idea, drifting.

**The RS-rank walk (T-30/T-15/T-5/T0) is not here.** `rs_rank` is a percentile
across a SCAN's matched set, so four of them in a row plot a changing population
rather than a moving stock, and only shortlist survivors are stored. That column
needs a universe-wide rank plus a daily snapshot table — a data-collection job,
tracked separately in the backlog.

CLI:
    py -3 tools/row_metrics.py RELIANCE.NS
"""
from __future__ import annotations

import sys
from typing import Any, Optional

import numpy as np
import pandas as pd

#: Bars either side of a swing used by the breakout lookback.
BREAKOUT_LOOKBACK = 20

#: How close to a pivot counts as "at" it, as a fraction of the pivot value.
#: 0.15% either side — tight enough that "Near Pivot" means something, wide
#: enough that a rupee of noise on a 3-digit price does not flip the label.
PIVOT_NEAR = 0.0015


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Case-insensitive column fetch — the desk hands these functions both
    yfinance's capitalised frames and lowercase bhavcopy ones."""
    if name in df.columns:
        return df[name]
    lower = {str(c).lower(): c for c in df.columns}
    key = lower.get(name.lower())
    if key is None:
        raise KeyError(f"{name!r} not in {list(df.columns)[:8]}")
    return df[key]


def _f(df: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(_col(df, name), errors="coerce").astype(float)


# ── the overnight move ────────────────────────────────────────────────────────

def gap_pct(df: pd.DataFrame) -> Optional[float]:
    """Today's OPEN against the previous CLOSE, per cent.

    Distinct from the day change, which measures close-to-close: the gap is the
    part of the move that happened while the market was shut, and a name can gap
    +4% and still close red.
    """
    if df is None or len(df) < 2:
        return None
    try:
        o, c = _f(df, "open"), _f(df, "close")
    except KeyError:
        return None
    prev_close, today_open = float(c.iloc[-2]), float(o.iloc[-1])
    if not np.isfinite(prev_close) or prev_close == 0 or not np.isfinite(today_open):
        return None
    return round((today_open - prev_close) / prev_close * 100.0, 2)


# ── how long has this been true ───────────────────────────────────────────────

def ema_cross_age(df: pd.DataFrame, fast: int = 10, slow: int = 20,
                  max_lookback: int = 250) -> dict[str, Any]:
    """Bars since the fast EMA last crossed the slow one, and in which direction.

    Returns `{"age": int|None, "direction": "up"|"down"|None,
              "searched": int}`.

    **`age=None` means "no cross within `searched` bars", not "never crossed".**
    That distinction is the whole reason `searched` is returned: a blank cell
    that silently meant "we only looked back three bars" would be a lie, and the
    existing `_percentr_exhaustion` helper this borrows from windows its search
    to a `lookback` and returns None outside it. Here the caller is told how far
    the search went so the tooltip can say it.
    """
    out: dict[str, Any] = {"age": None, "direction": None, "searched": 0}
    if df is None or len(df) < slow + 2:
        return out
    c = _f(df, "close")
    fast_s = c.ewm(span=fast, adjust=False).mean()
    slow_s = c.ewm(span=slow, adjust=False).mean()
    above = (fast_s > slow_s).to_numpy()

    # Only bars where both EMAs are meaningfully warmed up are searched. The
    # first bar of an EWM is just the price, so the very start of a short frame
    # would otherwise manufacture a "cross" out of the warm-up.
    start = min(slow, len(above) - 1)
    end = len(above) - 1
    lo = max(start, end - max_lookback)
    out["searched"] = max(0, end - lo)
    for i in range(end, lo, -1):
        if above[i] != above[i - 1]:
            out["age"] = end - i
            out["direction"] = "up" if above[i] else "down"
            return out
    return out


def breakout(df: pd.DataFrame, lookback: int = BREAKOUT_LOOKBACK,
             max_search: int = 120) -> dict[str, Any]:
    """The most recent close above its prior `lookback`-bar high, with the gain
    since — the ScreeningMantis "BO gain% + date" pair.

    Returns `{"date", "gain_pct", "bars_ago", "level"}`, all None when no such
    close is found inside `max_search` bars.

    The definition is deliberately the plainest one available (close above the
    prior N-bar high) rather than a pattern detector: this is a **descriptive
    column**, and borrowing a scanner's breakout definition would make the
    column mean whichever scanner it borrowed from.
    """
    out: dict[str, Any] = {"date": None, "gain_pct": None,
                           "bars_ago": None, "level": None}
    if df is None or len(df) < lookback + 2:
        return out
    c, h = _f(df, "close"), _f(df, "high")
    prior_high = h.shift(1).rolling(lookback).max()
    broke = (c > prior_high).to_numpy()
    last = float(c.iloc[-1])
    end = len(c) - 1
    lo = max(lookback, end - max_search)
    for i in range(end, lo - 1, -1):
        if bool(broke[i]):
            lvl = float(prior_high.iloc[i])
            px = float(c.iloc[i])
            out["bars_ago"] = end - i
            out["level"] = round(lvl, 2)
            out["gain_pct"] = (round((last / px - 1.0) * 100.0, 2)
                               if px > 0 else None)
            idx = df.index[i]
            out["date"] = (idx.date().isoformat()
                           if hasattr(idx, "date") else str(idx))
            return out
    return out


# ── where price sits against the pivots ───────────────────────────────────────

def pivot_levels(df: pd.DataFrame) -> Optional[dict[str, float]]:
    """Classic floor pivots from the PRIOR bar: PP, R1, S1, plus the CPR band.

    The desk already computed exactly this arithmetic — inside `build_chart()`
    in `dashboard_app.py`, as plot traces, daily only, with no way for anything
    else to ask. This is that same calculation extracted so a table can use it.
    Feed it a weekly-resampled frame to get weekly pivots.
    """
    if df is None or len(df) < 2:
        return None
    try:
        h, l, c = _f(df, "high"), _f(df, "low"), _f(df, "close")
    except KeyError:
        return None
    ph, pl, pc = float(h.iloc[-2]), float(l.iloc[-2]), float(c.iloc[-2])
    if not all(np.isfinite(v) for v in (ph, pl, pc)):
        return None
    pp = (ph + pl + pc) / 3.0
    bc = (ph + pl) / 2.0
    return {"pp": pp, "bc": bc, "tc": 2.0 * pp - bc,
            "r1": 2.0 * pp - pl, "s1": 2.0 * pp - ph}


def pivot_zone(df: pd.DataFrame) -> Optional[str]:
    """Which band the last close sits in: `R1`, `R1-PP`, `PP-S1`, `S1`,
    `Near R1`, `Near Pivot`, `Near S1`.

    A label, not a level — the point of the column is that a glance down it
    sorts a list into "pressing resistance" and "sitting on support" without
    the reader doing arithmetic per row.
    """
    lv = pivot_levels(df)
    if not lv:
        return None
    last = float(_f(df, "close").iloc[-1])
    if not np.isfinite(last):
        return None
    for level, name in ((lv["r1"], "Near R1"), (lv["pp"], "Near Pivot"),
                        (lv["s1"], "Near S1")):
        if level and abs(last - level) <= abs(level) * PIVOT_NEAR:
            return name
    if last > lv["r1"]:
        return "R1"
    if last > lv["pp"]:
        return "R1-PP"
    if last > lv["s1"]:
        return "PP-S1"
    return "S1"


def weekly_frame(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Daily bars resampled to weekly OHLC — the input for weekly pivots.

    Returns None when the index is not datetime-like, rather than resampling a
    positional index into nonsense.
    """
    if df is None or len(df) < 2:
        return None
    idx = pd.to_datetime(pd.Series(df.index), errors="coerce")
    if idx.isna().any():
        return None
    w = pd.DataFrame({
        "open": _f(df, "open").to_numpy(),
        "high": _f(df, "high").to_numpy(),
        "low": _f(df, "low").to_numpy(),
        "close": _f(df, "close").to_numpy(),
    }, index=pd.DatetimeIndex(idx))
    agg = w.resample("W").agg({"open": "first", "high": "max",
                               "low": "min", "close": "last"}).dropna()
    return agg if len(agg) >= 2 else None


# ── re-base the table on a date the reader picks ──────────────────────────────

def since(df: pd.DataFrame, ref_date) -> dict[str, Any]:
    """Close on (or the last close before) `ref_date`, and the gain since.

    Their `HIST. PRICE` + `GAIN% SINCE` pair. The reader picks the date and the
    whole table re-bases — "how has my list done since the day I looked", which
    is a different question from any fixed lookback answers.

    A date before the frame starts returns None rather than silently anchoring
    on the earliest bar available, which would quietly turn "since 1 Jan" into
    "since whenever this history happens to begin".
    """
    out: dict[str, Any] = {"price": None, "gain_pct": None, "date": None}
    if df is None or len(df) < 1 or ref_date is None:
        return out
    idx = pd.to_datetime(pd.Series(df.index), errors="coerce")
    if idx.isna().any():
        return out
    ref = pd.Timestamp(ref_date)
    mask = (idx <= ref).to_numpy()
    if not mask.any():
        return out
    pos = int(np.flatnonzero(mask)[-1])
    c = _f(df, "close")
    px, last = float(c.iloc[pos]), float(c.iloc[-1])
    if not np.isfinite(px) or px <= 0:
        return out
    out["price"] = round(px, 2)
    out["gain_pct"] = round((last / px - 1.0) * 100.0, 2)
    d = idx.iloc[pos]
    out["date"] = d.date().isoformat()
    return out


def from_52w_high_pct(df: pd.DataFrame, window: int = 252) -> Optional[float]:
    """Signed distance below the 52-week high, per cent (0 = at the high)."""
    if df is None or len(df) < 2:
        return None
    try:
        h, c = _f(df, "high"), _f(df, "close")
    except KeyError:
        return None
    hi = float(h.tail(window).max())
    last = float(c.iloc[-1])
    if not np.isfinite(hi) or hi <= 0 or not np.isfinite(last):
        return None
    return round((last / hi - 1.0) * 100.0, 2)


def row(df: pd.DataFrame, ref_date=None) -> dict[str, Any]:
    """Every column above for one symbol, ready to drop into a table row."""
    x = ema_cross_age(df)
    bo = breakout(df)
    sc = since(df, ref_date) if ref_date is not None else {}
    wk = weekly_frame(df)
    return {
        "gap_pct": gap_pct(df),
        "ema_cross_age": x["age"],
        "ema_cross_dir": x["direction"],
        "ema_cross_searched": x["searched"],
        "pivot_d": pivot_zone(df),
        "pivot_w": pivot_zone(wk) if wk is not None else None,
        "bo_gain_pct": bo["gain_pct"],
        "bo_date": bo["date"],
        "from_52w_high_pct": from_52w_high_pct(df),
        "hist_price": sc.get("price"),
        "gain_since_pct": sc.get("gain_pct"),
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    sym = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
    import yfinance as yf
    df = yf.Ticker(sym).history(period="2y")
    if df is None or df.empty:
        print(f"no data for {sym}")
        return 1
    df.columns = [str(c).lower() for c in df.columns]
    r = row(df, ref_date=df.index[-60])
    print(f"{sym} — {len(df)} bars\n")
    for k, v in r.items():
        print(f"  {k:24} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
