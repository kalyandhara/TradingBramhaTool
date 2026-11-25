"""target_anchors.py — target-anchor tag enrichment for plan cards (LuxAlgo step 6).

B-169 asks: for a plan whose target is at some price, WHAT structural level does
that price coincide with?  The desk already prints targets; nobody has ever
measured whether the ones that land on a prior extreme or an ICT SD projection
reach more often than arbitrary ones.

This module adds `target_anchor` metadata to a card dict without changing any
plan logic.  It is enrichment only — a tag for the scoreboard to group by, not
a signal and not a new entry filter.

== Tag taxonomy ==

    SD_1R   Target within tolerance of entry + 1×R  (ICT "1 std deviation")
    SD_2R   Target within tolerance of entry + 2×R  (ICT "2 std deviations")
    SD_3R   Target within tolerance of entry + 3×R  (ICT "3 std deviations")
    DAY_HIGH  Within tolerance of the prior trading day's high
    DAY_LOW   Within tolerance of the prior trading day's low
    WEEK_HIGH Within tolerance of the prior calendar week's high
    WEEK_LOW  Within tolerance of the prior calendar week's low
    MONTH_HIGH Within tolerance of the prior calendar month's high
    MONTH_LOW  Within tolerance of the prior calendar month's low
    NONE    No candidate within tolerance

Tags are ordered by specificity: SD projections first, then monthly, weekly,
daily.  The first match wins.  When two levels coincide (e.g. prior month high
sits very close to 2R), the SD tag takes precedence because it is the
structural reason the SCANNER placed the target there.

== Usage ==

    from target_anchors import tag_target, AnchorTag

    card   = scanner_card_dict          # must have entry, stop, target
    df_sym = daily_ohlcv_up_to_signal   # DatetimeIndex or integer index

    anchor = tag_target(card, df_sym)   # returns AnchorTag string
    card["target_anchor"] = anchor

The enriched card can be passed into any scoreboard that groups by
`target_anchor`.

== Note on SD projections ==

ICT's "standard deviation" is not the statistical σ — it is a measured-move
term: the initial stop distance (1R) is the "one-standard-deviation" expansion.
SD_1R is therefore the card's own 1:1 target, SD_2R is 2:1, etc.  This is
already how most scanners set their target (1.5R, 2R) so SD tags will be the
most common result — the minority are the ones that coincide with structure.
"""
from __future__ import annotations

from typing import Literal

import pandas as pd

AnchorTag = Literal[
    "SD_1R", "SD_2R", "SD_3R",
    "DAY_HIGH", "DAY_LOW",
    "WEEK_HIGH", "WEEK_LOW",
    "MONTH_HIGH", "MONTH_LOW",
    "NONE",
]

_SD_TAGS: list[tuple[float, AnchorTag]] = [
    (1.0, "SD_1R"),
    (2.0, "SD_2R"),
    (3.0, "SD_3R"),
]

_STRUCTURE_TAGS: list[AnchorTag] = [
    "MONTH_HIGH", "MONTH_LOW",
    "WEEK_HIGH", "WEEK_LOW",
    "DAY_HIGH", "DAY_LOW",
]

DEFAULT_TOLERANCE = 0.010   # 1.0% — a target within 1% of a level counts


def _prior_extremes(df: pd.DataFrame) -> dict[AnchorTag, float | None]:
    """Compute prior D/W/M highs and lows from df (all bars UP TO the signal).

    Uses the last complete prior period — not the current in-progress one.
    Returns None for a level when there is insufficient history.
    """
    out: dict[AnchorTag, float | None] = {k: None for k in _STRUCTURE_TAGS}
    if df.empty or "high" not in df.columns or "low" not in df.columns:
        return out

    hi = df["high"]
    lo = df["low"]

    # --- daily: exclude the signal bar itself (last row) ---
    if len(df) >= 2:
        prev = df.iloc[-2]
        out["DAY_HIGH"] = float(prev["high"])
        out["DAY_LOW"] = float(prev["low"])

    # --- weekly / monthly: requires a DatetimeIndex ---
    if not isinstance(df.index, pd.DatetimeIndex):
        return out

    # signal bar's date
    sig_date = df.index[-1]

    # prior complete week (Mon–Fri week of sig_date minus one week)
    sig_week_start = sig_date - pd.tseries.offsets.Week(weekday=0)
    prev_week_end = sig_week_start - pd.Timedelta(days=1)
    prev_week_start = prev_week_end - pd.Timedelta(days=6)
    week_mask = (df.index >= prev_week_start) & (df.index <= prev_week_end)
    if week_mask.any():
        out["WEEK_HIGH"] = float(hi[week_mask].max())
        out["WEEK_LOW"] = float(lo[week_mask].min())

    # prior complete calendar month
    this_month_start = sig_date.replace(day=1)
    prev_month_end = this_month_start - pd.Timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    month_mask = (df.index >= prev_month_start) & (df.index <= prev_month_end)
    if month_mask.any():
        out["MONTH_HIGH"] = float(hi[month_mask].max())
        out["MONTH_LOW"] = float(lo[month_mask].min())

    return out


def tag_target(
    card: dict,
    df: pd.DataFrame,
    tolerance: float = DEFAULT_TOLERANCE,
) -> AnchorTag:
    """Return the structural anchor tag for the plan card's target price.

    Parameters
    ----------
    card:      scanner card dict with float-castable 'entry', 'stop', 'target'
    df:        daily OHLCV bars up to and INCLUDING the signal bar (the last row
               is the signal bar; prior bars supply structure)
    tolerance: fractional distance within which target ≈ level (default 1%)

    Returns
    -------
    AnchorTag string — "NONE" when no level matches within tolerance
    """
    try:
        entry = float(card["entry"])
        stop = float(card["stop"])
        target = float(card["target"])
    except (KeyError, TypeError, ValueError):
        return "NONE"

    risk = abs(entry - stop)
    if risk <= 0:
        return "NONE"

    # Determine long/short by stop position
    is_long = stop < entry

    def _near(level: float | None) -> bool:
        if level is None:
            return False
        return abs(target - level) / max(abs(target), 1e-9) <= tolerance

    # 1. SD projections (most specific — scanner's own measured-move target)
    for k, tag in _SD_TAGS:
        sd_level = (entry + k * risk) if is_long else (entry - k * risk)
        if _near(sd_level):
            return tag

    # 2. Prior structure (monthly before weekly before daily — largest frame wins)
    extremes = _prior_extremes(df)
    for tag in _STRUCTURE_TAGS:
        if _near(extremes.get(tag)):
            return tag

    return "NONE"


def enrich_card(card: dict, df: pd.DataFrame,
                tolerance: float = DEFAULT_TOLERANCE) -> dict:
    """Return card with 'target_anchor' key added (mutates and returns)."""
    card["target_anchor"] = tag_target(card, df, tolerance=tolerance)
    return card
