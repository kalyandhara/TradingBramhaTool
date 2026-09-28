#!/usr/bin/env python3
"""calendar_anchor.py — the yearly opening range (B-98).

The January high/low as a reference level, and the first close outside it as an
event. From [[sources/Bramesh-TradingView-Gann-Scanners-Product-Line]], where it
was the **only** construct fully specified, reproducible and measurable on cached
daily history — an anchor rule, a state, and an event, with no judgement anywhere
in it. Nothing in `tools/` held a calendar anchor before this (no `opening_range`,
no year-open).

── Why a CALENDAR anchor, specifically ───────────────────────────────────────
Anchored VWAP has the same shape and has been parked since B-4/B-12 for one
reason: **the anchor choice is subjective**, and nobody has built the UI to make
it. A calendar anchor has no such half. January is January. Two readers get the
same level from the same data, which is what makes this measurable at all and
Anchored VWAP not (yet).

── The dates are the point, and the desk's scanner path destroys them ────────
`scanner_templates._clean_ohlc` and `backtest.backtest_scanner` both call
`reset_index(drop=True)`, because every other detector here works in bar offsets.
A calendar rule cannot: it needs to know which bars are January. So this module
takes a **DatetimeIndex-ed frame** and says so loudly rather than silently
reading the first 20 bars of whatever it was handed and calling that January —
which is the bug this docstring exists to stop someone writing later.

`detect_yearly_opening_range` is therefore NOT registered as a scanner. It cannot
be, honestly, until the shared harness carries dates (B-104 fixed the same class
of problem for the market model; the scanner path is still offset-only). The
measurement runs through a study of its own, pre-registered first.

── Definitions, fixed here so the study cannot drift ─────────────────────────
  RANGE   high = max(high) and low = min(low) over every session in JANUARY of
          year Y. A partial January (a listing mid-month) still counts, and the
          session count is reported so a thin range can be judged rather than
          silently used.
  STATE   from the first session of February onward: ABOVE (close > range high),
          BELOW (close < range low), INSIDE otherwise.
  EVENT   the FIRST close outside the range in year Y — the transition, not the
          state. A state persists for months and would be counted once per bar;
          the event happens once (B-92's shape).

CLI:
    py -3 -X utf8 tools/calendar_anchor.py --symbol RELIANCE [--days 2500]
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import pandas as pd

#: The anchor month. A constant rather than a literal 1, because the same
#: machinery answers "the April range" for a fiscal-year reader, and a magic 1
#: buried in three comparisons is how that becomes a rewrite instead of an
#: argument.
ANCHOR_MONTH = 1


class UndatedFrame(ValueError):
    """Raised when the frame has no DatetimeIndex.

    Loud on purpose. The alternative — assuming bar 0 is the year's first
    session — produces a plausible number from the wrong bars, and a plausible
    wrong number is the thing this desk spends most of its time removing.
    """


def _require_dates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) == 0:
        raise UndatedFrame("empty frame")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise UndatedFrame(
            "calendar_anchor needs a DatetimeIndex — the scanner path's "
            "reset_index(drop=True) destroys it, so pass the dated frame")
    return df.dropna(subset=[c for c in ("high", "low", "close") if c in df.columns])


def yearly_opening_range(df: pd.DataFrame, year: int) -> dict[str, Any] | None:
    """The anchor month's high/low for ``year``, or None if that month is absent.

    None is not "no range": it means this frame does not cover that January, and
    the caller must not fall back to the first N bars it does have.
    """
    d = _require_dates(df)
    jan = d[(d.index.year == year) & (d.index.month == ANCHOR_MONTH)]
    if jan.empty:
        return None
    hi = float(jan["high"].max())
    lo = float(jan["low"].min())
    if not (hi > lo > 0):
        return None
    return {
        "year": year,
        "high": round(hi, 2),
        "low": round(lo, 2),
        "width_pct": round((hi - lo) / lo * 100.0, 2),
        "sessions": int(len(jan)),
        "first_session": jan.index[0].date().isoformat(),
        "last_session": jan.index[-1].date().isoformat(),
    }


def state_at(df: pd.DataFrame, year: int, asof=None) -> dict[str, Any] | None:
    """ABOVE / BELOW / INSIDE the year's opening range at ``asof`` (default: last bar)."""
    rng = yearly_opening_range(df, year)
    if rng is None:
        return None
    d = _require_dates(df)
    after = d[(d.index.year == year) & (d.index.month > ANCHOR_MONTH)]
    if asof is not None:
        after = after[after.index <= pd.Timestamp(asof)]
    if after.empty:
        return None
    px = float(after["close"].iloc[-1])
    state = "ABOVE" if px > rng["high"] else "BELOW" if px < rng["low"] else "INSIDE"
    # Distance to the nearer boundary, signed by the side price is on: the number
    # a reader wants is "how far from the level", not "how far from the middle".
    dist = ((px - rng["high"]) if state == "ABOVE"
            else (px - rng["low"]) if state == "BELOW"
            else min(rng["high"] - px, px - rng["low"]))
    return {
        **rng,
        "asof": after.index[-1].date().isoformat(),
        "close": round(px, 2),
        "state": state,
        "distance_pct": round(dist / px * 100.0, 2),
    }


def detect_yearly_opening_range(df: pd.DataFrame, year: int) -> dict[str, Any] | None:
    """The EVENT: the first close outside year ``year``'s opening range.

    Returns the break with its date, direction, bar offset and the state at the
    end of the frame — or None when the range was never left, which is itself a
    fact worth counting rather than a missing row.
    """
    rng = yearly_opening_range(df, year)
    if rng is None:
        return None
    d = _require_dates(df)
    after = d[(d.index.year == year) & (d.index.month > ANCHOR_MONTH)]
    if after.empty:
        return None
    closes = after["close"].to_numpy(float)
    hi, lo = rng["high"], rng["low"]
    for i, px in enumerate(closes):
        if px > hi or px < lo:
            up = px > hi
            return {
                **rng,
                "broke": True,
                "direction": "up" if up else "down",
                "break_date": after.index[i].date().isoformat(),
                "break_close": round(float(px), 2),
                "sessions_into_year": int(i + 1),
                # Where the whole frame sits, so a reader can tell a break that
                # held from one that came straight back inside.
                "still_outside": bool(
                    (closes[-1] > hi) if up else (closes[-1] < lo)),
            }
    return {**rng, "broke": False, "direction": None,
            "sessions_into_year": int(len(closes)),
            "last_close": round(float(closes[-1]), 2)}


def years_covered(df: pd.DataFrame) -> list[int]:
    """Years whose anchor month is present in this frame, oldest first."""
    d = _require_dates(df)
    jan = d[d.index.month == ANCHOR_MONTH]
    return sorted({int(y) for y in jan.index.year})


def main() -> int:
    ap = argparse.ArgumentParser(description="B-98 — yearly opening range")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--days", type=int, default=2500)
    a = ap.parse_args()

    import screener_pipeline as sp
    df = sp.fetch_ohlcv(a.symbol, days=a.days)
    if df is None or df.empty:
        print(f"no data for {a.symbol}")
        return 1
    print(f"{a.symbol} — yearly opening range (January anchor)\n")
    for y in years_covered(df):
        ev = detect_yearly_opening_range(df, y)
        if ev is None:
            continue
        head = (f"{y}: {ev['low']:.2f}-{ev['high']:.2f} "
                f"({ev['width_pct']:.1f}% wide, {ev['sessions']} sessions)")
        if ev["broke"]:
            print(f"{head} → first close {ev['direction'].upper()} on "
                  f"{ev['break_date']} at {ev['break_close']:.2f} "
                  f"(session {ev['sessions_into_year']} after January)"
                  f"{'' if ev['still_outside'] else ' — back inside since'}")
        else:
            print(f"{head} → never left the range "
                  f"({ev['sessions_into_year']} sessions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
