"""price_levels.py — where a close sits in its recent range, and whether it just
cleared it.

Built for the OI-momentum linkage: the question an OI reading cannot answer on
its own is *where* the positions were built. Fresh longs at a three-month high
are a breakout being bought; the identical OI print in the middle of a range is
the same money with nothing to push against.

Why this is a LOCATION measure and not another scanner
------------------------------------------------------
The obvious move was to compose `scan_structural_breakout`, which already
detects a resistance cluster and its Approaching/Confirmed/Retest lifecycle.
Measured against a live OI scan, that composition annotates **4 of 57 readings
(7%)**, for two reasons that only show up on contact with data:

  1. It is bullish-only — a resistance cluster, with no support-breakdown
     counterpart anywhere in this repo (verified: zero occurrences). On a
     session that ran 35 down-moves against 22 up-moves it can therefore reach
     at most 39% of rows before any quality gate applies.
  2. It is a SCANNER, gated on score floors (65 approaching / 72 confirmed). It
     answers "is this a good breakout" and returns None otherwise — which is
     correct for a scanner and useless as a column, because "no qualifying
     breakout" and "nowhere near a level" collapse to the same blank.

The per-symbol OHLCV fetch costs the same either way, so it should buy a reading
for every row rather than 7% of them. This module reports position for all of
them, symmetrically, and `scan_structural_breakout` is layered on top where it
fires — the measured scanner still gets the last word on breakout QUALITY, it
just no longer decides whether a row gets any level context at all.

Nothing here is scored. It reports where price is; what that means next to an OI
build is the caller's call.

Public API:
    locate(df, window=60, band_pct=2.0) -> dict | None
    tag_against_oi(location, reading) -> dict | None

NOT ADVICE.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

#: Lookback for the range, in bars. 60 sessions is about three months — a swing
#: horizon, and long enough that the extremes are structure rather than last
#: week's noise. `scan_structural_breakout` uses 120 for its cluster; this is
#: deliberately shorter because it answers "where is price now" rather than
#: "is there a multi-week ceiling here".
DEFAULT_WINDOW = 60

#: How close to an extreme still counts as AT it. Measured across a live 57-name
#: OI scan: a 2% band put 15 names at the high, 4 at the low and 36 mid-range —
#: roughly a third at a level. That split is the point. A band that flagged
#: almost everything or almost nothing would be arithmetic; this one separates
#: the universe into groups that differ.
DEFAULT_BAND_PCT = 2.0

#: Ordered high → low. Names describe POSITION, never direction: "at support" is
#: not a buy and "new low" is not a sell, and the OI reading beside it is what
#: gives either one meaning.
NEW_HIGH = "NEW HIGH"
AT_RESISTANCE = "AT RESISTANCE"
MID_RANGE = "MID-RANGE"
AT_SUPPORT = "AT SUPPORT"
NEW_LOW = "NEW LOW"


def locate(df: pd.DataFrame, window: int = DEFAULT_WINDOW,
           band_pct: float = DEFAULT_BAND_PCT) -> dict[str, Any] | None:
    """Where the last close sits in the trailing `window` bars.

    Returns None when there is not enough history to define a range — absent
    rather than defaulted, because a fabricated mid-range reading would be
    indistinguishable from a real one.

    `range_pos` is 0 at the window low and 100 at the window high. The extremes
    are taken over the window EXCLUDING the last bar, so "new high" means today
    cleared the prior range rather than tautologically equalling its own high.
    """
    if df is None or "close" not in getattr(df, "columns", []):
        return None
    d = df[df["close"].notna()]
    if len(d) < window + 2:
        return None

    prior = d.tail(window + 1).iloc[:-1]          # window bars BEFORE today
    hi = float(prior["high"].max())
    lo = float(prior["low"].min())
    close = float(d["close"].iloc[-1])
    if not (hi > lo > 0):
        return None

    to_high = (close - hi) / hi * 100.0
    to_low = (close - lo) / lo * 100.0
    span = hi - lo
    pos = (close - lo) / span * 100.0

    if close > hi:
        state = NEW_HIGH
    elif close < lo:
        state = NEW_LOW
    elif to_high >= -band_pct:
        state = AT_RESISTANCE
    elif to_low <= band_pct:
        state = AT_SUPPORT
    else:
        state = MID_RANGE

    return {
        "state": state,
        "range_pos": round(pos, 1),
        "range_high": round(hi, 2),
        "range_low": round(lo, 2),
        "to_high_pct": round(to_high, 2),
        "to_low_pct": round(to_low, 2),
        "window": window,
        "at_level": state != MID_RANGE,
    }


#: Which OI readings the location either supports or argues with. Keyed by the
#: reading strings in nse_oi_momentum; kept as data so the mapping is readable
#: in one place rather than buried in branches.
_UPPER = (NEW_HIGH, AT_RESISTANCE)
_LOWER = (NEW_LOW, AT_SUPPORT)


def tag_against_oi(location: dict[str, Any] | None,
                   reading: str) -> dict[str, str] | None:
    """Confirm/diverge between WHERE price is and WHAT the OI did.

    This is the infographic's rule made checkable — bullish confirmation is
    price up plus fresh OI plus a resistance break; bearish is the mirror. It is
    a tag to sit BESIDE the OI verdict, never inside it: location is not
    evidence about positioning, it is context for it.

    Returns None for mid-range names, which is most of them and should stay
    quiet. "The build happened nowhere near a level" is worth knowing, but it is
    not a confirmation or a contradiction of anything.
    """
    if not location or not reading:
        return None
    state = location["state"]
    if state == MID_RANGE:
        return None

    up_build = reading == "LONG BUILD-UP"
    down_build = reading == "SHORT BUILD-UP"

    if up_build and state in _UPPER:
        return {"tag": "CONFIRMS",
                "note": f"Fresh longs built with price {state.lower()} — the "
                        f"positions went on where a break has to be defended."}
    if down_build and state in _LOWER:
        return {"tag": "CONFIRMS",
                "note": f"Fresh shorts built with price {state.lower()} — "
                        f"pressure applied where the range gives way."}
    if up_build and state in _LOWER:
        return {"tag": "DIVERGES",
                "note": f"Fresh longs built with price {state.lower()}, at the "
                        f"wrong end of the range for a breakout read."}
    if down_build and state in _UPPER:
        return {"tag": "DIVERGES",
                "note": f"Fresh shorts built with price {state.lower()} — "
                        f"sellers positioning into strength, not breakdown."}
    # Covering and unwinding describe positions LEAVING, so a level says less
    # about them; reported as context only.
    return {"tag": "CONTEXT",
            "note": f"Positions closed out with price {state.lower()}."}
