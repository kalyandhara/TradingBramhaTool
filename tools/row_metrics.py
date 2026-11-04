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
    """Daily bars resampled to weekly OHLC — the input for weekly pivots."""
    return period_frame(df, "W")


def period_frame(df: pd.DataFrame, rule: str) -> Optional[pd.DataFrame]:
    """Daily bars resampled to `rule` OHLC (`W`, `ME`, `QE`, `YE`).

    The last row is the period in progress, so `pivot_levels` — which reads the
    PRIOR bar — gets the last COMPLETED week / month / quarter / year, the way a
    floor pivot is defined. Returns None when the index is not datetime-like,
    rather than resampling a positional index into nonsense.
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
    agg = w.resample(rule).agg({"open": "first", "high": "max",
                               "low": "min", "close": "last"}).dropna()
    return agg if len(agg) >= 2 else None


#: B-96. Five timeframes, ONE reading. B-97 measured daily and weekly zones on
#: OPPOSITE sides of their pivot for 37.9% of 499 names, so five peer columns
#: would routinely contradict each other with nothing saying which governs. The
#: honest single reading is the agreement itself: how many of the timeframes that
#: could be read have the close above their own pivot.
PIVOT_TIMEFRAMES: tuple[tuple[str, Optional[str]], ...] = (
    ("D", None), ("W", "W"), ("M", "ME"), ("Q", "QE"), ("Y", "YE"))


def pivot_sides(df: pd.DataFrame) -> dict[str, Optional[int]]:
    """+1 / -1 per timeframe: last close above / below that timeframe's PP.
    None where the timeframe cannot be read (too little history for a prior
    COMPLETED period) or the close sits exactly on the pivot."""
    out: dict[str, Optional[int]] = {}
    if df is None or len(df) < 2:
        return {k: None for k, _ in PIVOT_TIMEFRAMES}
    try:
        last = float(_f(df, "close").iloc[-1])
    except KeyError:
        return {k: None for k, _ in PIVOT_TIMEFRAMES}
    for key, rule in PIVOT_TIMEFRAMES:
        fr = df if rule is None else period_frame(df, rule)
        lv = pivot_levels(fr) if fr is not None else None
        if not lv or not np.isfinite(last) or last == lv["pp"]:
            out[key] = None
        else:
            out[key] = 1 if last > lv["pp"] else -1
    return out


def pivot_agreement(df: pd.DataFrame) -> Optional[str]:
    """`"4/5 above"` — of the timeframes that could be read, how many have the
    close above their pivot. The denominator is printed because a young listing
    has no prior year: `3/4` and `3/5` are different statements. None below two
    readable timeframes, where "agreement" means nothing."""
    sides = [v for v in pivot_sides(df).values() if v is not None]
    if len(sides) < 2:
        return None
    return f"{sum(1 for v in sides if v > 0)}/{len(sides)} above"


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


#: EMA spans shown in the alignment stack, fast to slow. Deliberately the four
#: ScreeningMantis shows: they are the spans this desk already computes, and a
#: fifth would make the cell wider than the fact it carries.
EMA_STACK_SPANS = (10, 20, 50, 200)

#: The span the "% from EMA" column measures against. 20, NOT 21 — and the
#: difference is not cosmetic: `scan_pullback_to_ema` uses 21, so a column
#: labelled "% from 20EMA" that quietly used 21 would disagree with that
#: scanner by construction while appearing to confirm it. The audit in B-63b
#: flagged exactly this collision.
PCT_FROM_EMA_SPAN = 20


def rsi(df: pd.DataFrame, n: int = 14) -> Optional[float]:
    """Wilder RSI(14) at the last bar.

    Imported from `scanner_templates`, not re-derived: that module's `_rsi_series`
    is the desk's ONE RSI, and B-24 was a full entry about two RSI
    implementations that disagreed. A second one here would re-open it.
    """
    if df is None or len(df) < n + 2:
        return None
    try:
        import scanner_templates as st
        v = float(st._rsi_series(_f(df, "close"), n).iloc[-1])
    except (KeyError, ImportError, ValueError, IndexError):
        return None
    return None if not np.isfinite(v) else round(v, 1)


def pct_from_ema(df: pd.DataFrame, span: int = PCT_FROM_EMA_SPAN) -> Optional[float]:
    """Signed distance of the close from its `span`-EMA, per cent.

    Computed inline at `scanner_templates.py:4340` and never exposed as a column
    until now — one of the three things the B-63b audit found we already had and
    were not showing.
    """
    if df is None or len(df) < span + 2:
        return None
    try:
        import scanner_templates as st
        e = float(st._ema_series(_f(df, "close"), span).iloc[-1])
        last = float(_f(df, "close").iloc[-1])
    except (KeyError, ImportError, ValueError, IndexError):
        return None
    if not np.isfinite(e) or e <= 0 or not np.isfinite(last):
        return None
    return round((last / e - 1.0) * 100.0, 2)


#: Red / green / grey, matching the dot vocabulary the rest of the dashboard
#: already speaks (`_TONE_DOT`, and `⚪` as its "unknown" fallback). These are
#: the only characters that carry their own colour inside an `st.dataframe`
#: cell: a TextColumn cannot style part of its text, so a coloured glyph is the
#: whole mechanism, not a decoration on top of one.
EMA_DOT_ABOVE = "🟢"
EMA_DOT_BELOW = "🔴"
EMA_DOT_UNKNOWN = "⚪"


def ema_stack(df: pd.DataFrame, spans=EMA_STACK_SPANS) -> Optional[str]:
    """Price vs each EMA as one glance-width cell, e.g. `10🟢 20🟢 50🟢 200🔴`.

    The best idea on the source table: four facts in the width of one column.
    Green where the close is above that EMA, red where below, **grey where the
    name has too little history for that span to exist**.

    ── Why grey rather than omission ──────────────────────────────────────────
    This previously DROPPED a span it could not compute, on the reasoning that
    printing `200▼` for a name with 120 bars states something we cannot see.
    That reasoning still holds — but dropping it also collapsed the cell, so a
    young listing and a name below its 200 EMA produced different-length cells
    that no longer lined up down the column, and the reader had to count.

    Grey keeps the SLOT and empties it: four positions always, in the same
    order, so the column scans vertically and "unknown" is visibly distinct from
    both "above" and "below" rather than being inferred from a gap. The claim we
    refuse to make is unchanged — grey asserts nothing about price.
    """
    if df is None or len(df) < 12:
        return None
    try:
        import scanner_templates as st
        close = _f(df, "close")
        last = float(close.iloc[-1])
    except (KeyError, ImportError, ValueError, IndexError):
        return None
    if not np.isfinite(last):
        return None
    parts, known = [], 0
    for sp in spans:
        dot = EMA_DOT_UNKNOWN
        if len(close) >= sp + 2:
            try:
                e = float(st._ema_series(close, sp).iloc[-1])
                if np.isfinite(e) and e > 0:
                    dot = EMA_DOT_ABOVE if last >= e else EMA_DOT_BELOW
                    known += 1
            except (ValueError, IndexError):
                pass
        parts.append(f"{sp}{dot}")
    # All four grey is not a reading, it is an absence — return None so the cell
    # is blank rather than a row of empty circles pretending to be a measurement.
    return " ".join(parts) if known else None


# ── the quarterly profit shape ────────────────────────────────────────────────
# B-75. A SEQUENTIAL walk, and the word matters: `fundamentals_deep` computes
# profit growth year-over-year on purpose, because "sequential comparison would
# read seasonality as growth". That reasoning is not withdrawn here. The count
# is what forces the choice — yfinance serves 5-7 quarterly columns, of which
# only 1-2 have a year-ago match, so a YoY walk is one or two points and is not
# a sequence at all. The sequential walk is the only walk this data supports.
#
# So it is published as a SHAPE, never as a growth rate: decaying reads
# differently from turning up, and that comparison survives seasonality even
# where the individual step does not. Nothing here votes, scores, or enters a
# confluence weight, and it owes no backtest because it makes no claim.

#: A sequential step must span roughly one quarter. Anything outside this is a
#: gap in the frame, not a quarter of growth -- see `_QOQ_GAP`.
QOQ_MIN_DAYS, QOQ_MAX_DAYS = 60, 130

#: The frame skipped a quarter, so the step spans more than one. Printed rather
#: than bridged: silently spanning a gap manufactures a number nobody can see is
#: wrong. Same reasoning as `rs_walk.format_walk`'s '?'.
_QOQ_GAP = "?"

#: The BASE quarter was a loss (or zero), so a percentage is not defined -- a
#: loss shrinking from -100 to -10 computes as +90%, which reads as growth. The
#: letter says "the denominator was a loss", which is the fact worth carrying.
_QOQ_LOSS_BASE = "L"

#: Steps shown. 5-7 quarterly columns give 4-6 steps; the cap keeps the cell
#: from growing without bound if a frame ever carries more.
QOQ_MAX_STEPS = 6


def _qoq_days(newer: Any, older: Any) -> Optional[int]:
    try:
        return int((pd.Timestamp(newer) - pd.Timestamp(older)).days)
    except (TypeError, ValueError):
        return None


def profit_qoq_steps(quarters: list[dict[str, Any]],
                     max_steps: int = QOQ_MAX_STEPS) -> list[dict[str, Any]]:
    """Sequential profit change per quarter, OLDEST FIRST.

    Takes `fundamentals_deep.derive_fundamentals(...)["quarters"]`, which is
    newest-first and carries `period` (ISO date) and `net_income`.

    Each step is `{"period", "pct", "flag"}` where `flag` is None for a computed
    step, `"gap"` where the frame skipped a quarter, and `"loss_base"` where the
    earlier quarter was not positive. A step whose either end is missing is
    dropped entirely rather than flagged: an absent row is not a gapped quarter,
    and the two should not read alike.
    """
    if not quarters:
        return []
    rows = list(reversed(quarters))            # oldest first, the reading order
    steps: list[dict[str, Any]] = []
    for prev, cur in zip(rows, rows[1:]):
        p, c = prev.get("net_income"), cur.get("net_income")
        if p is None or c is None:
            continue
        days = _qoq_days(cur.get("period"), prev.get("period"))
        if days is None or not (QOQ_MIN_DAYS <= days <= QOQ_MAX_DAYS):
            steps.append({"period": cur.get("period"), "pct": None, "flag": "gap"})
            continue
        if p <= 0:
            steps.append({"period": cur.get("period"), "pct": None,
                          "flag": "loss_base"})
            continue
        steps.append({"period": cur.get("period"),
                      "pct": round((c / p - 1) * 100, 1), "flag": None})
    return steps[-max_steps:] if max_steps else steps


def format_profit_walk(steps: list[dict[str, Any]]) -> Optional[str]:
    """`"+12 → -5 → ? → +8"`, oldest first, per cent, sequential.

    None when there is nothing to show, so the cell renders absent rather than
    as an empty walk — absent and flat are different readings.
    """
    if not steps:
        return None
    parts = []
    for s in steps:
        if s.get("flag") == "gap":
            parts.append(_QOQ_GAP)
        elif s.get("flag") == "loss_base":
            parts.append(_QOQ_LOSS_BASE)
        else:
            parts.append(f"{s['pct']:+.0f}")
    return " → ".join(parts)


def profit_qoq_walk(quarters: list[dict[str, Any]],
                    max_steps: int = QOQ_MAX_STEPS) -> Optional[str]:
    """The `profit_qoq_walk` cell for one symbol, from its quarterly history."""
    return format_profit_walk(profit_qoq_steps(quarters, max_steps))


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
        "pivot_agree": pivot_agreement(df),
        "bo_gain_pct": bo["gain_pct"],
        "bo_date": bo["date"],
        "from_52w_high_pct": from_52w_high_pct(df),
        "hist_price": sc.get("price"),
        "gain_since_pct": sc.get("gain_pct"),
        "rsi": rsi(df),
        "pct_from_20ema": pct_from_ema(df),
        "ema_stack": ema_stack(df),
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
