"""volume_profile.py — Volume Profile (POC / Value Area / HVN / LVN).

Python port of `tools/volume_profile.js`, which remains the reference
implementation the boundary math is defined by (see VOLUME_PROFILE_MODULE.md).
This module exists so the *Python* toolchain — the council, the scanners, the
screener pipeline — can reach the same POC / Value Area / node structures the
chart dashboard already draws in JS, instead of the profile being chart-only.

Algorithms are a faithful 1:1 port and are parity-tested against the JS
reference; do not "improve" the math here without changing the JS too, or the
chart and the scanners will silently disagree about where the POC is.

Public API:
    compute_profile(df, **opts) -> dict | None
    find_confluence(points, profile, tol_pct=0.004) -> list[dict]
    describe_position(df, profile) -> dict | None

`describe_position` reports value-area location *and* (since 2026-08-09) where
price sits relative to the HVN/LVN pockets — `at_hvn` / `at_lvn` plus distances
to the nearest pocket above and below. Those pockets were computed and drawn on
the chart from the start but never read back into the screening path, so the
magnet/air-pocket read — the actionable half of the profile — was unavailable to
Setup Intelligence. See ``concepts/Volume-Profile``.

Expected frame: pandas DataFrame with lowercase `high`, `low`, `close`,
`volume` columns (the shape used across this repo's Python tools).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

VERSION = "1.0.0"

DEFAULT_OPTS: dict[str, Any] = {
    "bins":           30,     # price rows spanning [lookback_low, lookback_high]
    "lookback":       None,   # None = every bar passed in; else last N bars
    "value_area_pct": 0.70,   # fraction of total volume the Value Area encloses
    "hvn_mult":       1.5,    # HVN seed if vol >= mean_vol * hvn_mult
    "lvn_mult":       0.5,    # LVN seed if vol <= mean_vol * lvn_mult
    "hvn_expand_tol": 0.85,   # absorb neighbors while vol >= seed_vol * this
    "lvn_expand_tol": 1.30,   # absorb neighbors while vol <= threshold * this
}


# ── Step 1: binned histogram with proportional intrabar volume distribution ──
# Each bar's volume is split across every bin its [low, high] range overlaps,
# weighted by the fraction of the bar's range inside that bin — the standard
# approximation when only OHLCV (not tick) data is available.
def _build_histogram(high, low, close, volume, n_bins: int) -> dict | None:
    lo = float(np.min(low))
    hi = float(np.max(high))
    if not (hi > lo):
        return None

    bin_size = (hi - lo) / n_bins
    bin_edges = [lo + i * bin_size for i in range(n_bins + 1)]
    bins = [0.0] * n_bins

    def clamp_bin(i: int) -> int:
        return max(0, min(n_bins - 1, i))

    for b_high, b_low, b_close, vol in zip(high, low, close, volume):
        b_high, b_low, b_close = float(b_high), float(b_low), float(b_close)
        vol = float(vol) if vol == vol and vol is not None else 0.0  # NaN-safe
        if vol == 0:
            continue

        rng = b_high - b_low
        if rng <= 0:
            # Flat/doji bar: all volume lands in the bin containing the price.
            bins[clamp_bin(math.floor((b_close - lo) / bin_size))] += vol
            continue

        i0 = clamp_bin(math.floor((b_low - lo) / bin_size))
        i1 = clamp_bin(math.floor((b_high - lo) / bin_size))
        for i in range(i0, i1 + 1):
            bin_low, bin_high = bin_edges[i], bin_edges[i + 1]
            overlap = max(0.0, min(b_high, bin_high) - max(b_low, bin_low))
            if overlap > 0:
                bins[i] += vol * (overlap / rng)

    return {"bin_edges": bin_edges, "bins": bins, "lo": lo, "hi": hi,
            "bin_size": bin_size}


# ── Step 2: Point of Control ────────────────────────────────────────────────
# POC = the single bin holding the most volume. Quoted price is the midpoint.
def _find_poc(hist: dict) -> dict:
    bins, bin_edges = hist["bins"], hist["bin_edges"]
    poc_idx = 0
    for i in range(1, len(bins)):
        if bins[i] > bins[poc_idx]:
            poc_idx = i
    return {
        "idx": poc_idx,
        "price": (bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2,
        "low": bin_edges[poc_idx],
        "high": bin_edges[poc_idx + 1],
        "volume": bins[poc_idx],
    }


# ── Step 3: Value Area (single-bin, greater-of-two-neighbors expansion) ─────
# From the POC bin, repeatedly add whichever adjacent bin holds more volume
# until cumulative volume reaches value_area_pct of the total.
def _find_value_area(hist: dict, poc: dict, value_area_pct: float) -> dict:
    bins, bin_edges = hist["bins"], hist["bin_edges"]
    total = sum(bins)
    target = total * value_area_pct

    low = high = poc["idx"]
    cum = bins[poc["idx"]]

    while cum < target and (low > 0 or high < len(bins) - 1):
        vol_below = bins[low - 1] if low > 0 else -math.inf
        vol_above = bins[high + 1] if high < len(bins) - 1 else -math.inf
        if vol_below >= vol_above:
            low -= 1
            cum += bins[low]
        else:
            high += 1
            cum += bins[high]

    return {
        "low": bin_edges[low], "high": bin_edges[high + 1],
        "low_idx": low, "high_idx": high,
        "volume": cum, "pct": (cum / total) if total > 0 else 0.0,
    }


# ── Step 4/5: HVN / LVN pocket detection ────────────────────────────────────
# A node starts at a local-extremum bin clearing a significance threshold, then
# expands outward while neighbors stay within tolerance of the seed, turning a
# single row into the contiguous price *pocket* it spans. Overlapping pockets
# from adjacent seeds are merged.
def _find_nodes(hist: dict, mult: float, expand_tol: float, mode: str) -> list[dict]:
    bins, bin_edges = hist["bins"], hist["bin_edges"]
    n = len(bins)
    total = sum(bins)
    mean_vol = total / n if n else 0.0
    threshold = mean_vol * mult

    def is_seed(i: int) -> bool:
        v = bins[i]
        if mode == "hvn":
            left = bins[i - 1] if i > 0 else -math.inf
            right = bins[i + 1] if i < n - 1 else -math.inf
            return v >= threshold and v >= left and v >= right
        left = bins[i - 1] if i > 0 else math.inf
        right = bins[i + 1] if i < n - 1 else math.inf
        return v <= threshold and v <= left and v <= right

    pockets: list[dict] = []
    for i in range(n):
        if not is_seed(i):
            continue
        lo_i = hi_i = i
        seed_vol = bins[i]
        if mode == "hvn":
            while lo_i > 0 and bins[lo_i - 1] >= seed_vol * expand_tol:
                lo_i -= 1
            while hi_i < n - 1 and bins[hi_i + 1] >= seed_vol * expand_tol:
                hi_i += 1
        else:
            while lo_i > 0 and bins[lo_i - 1] <= threshold * expand_tol:
                lo_i -= 1
            while hi_i < n - 1 and bins[hi_i + 1] <= threshold * expand_tol:
                hi_i += 1
        pockets.append({"low_idx": lo_i, "high_idx": hi_i,
                        "seed_idx": i, "seed_volume": seed_vol})

    # Merge overlapping/adjacent pockets.
    pockets.sort(key=lambda p: p["low_idx"])
    merged: list[dict] = []
    for p in pockets:
        prev = merged[-1] if merged else None
        if prev and p["low_idx"] <= prev["high_idx"] + 1:
            prev["high_idx"] = max(prev["high_idx"], p["high_idx"])
            prev["seed_volume"] = max(prev["seed_volume"], p["seed_volume"])
        else:
            merged.append(dict(p))

    return [{
        "low": bin_edges[p["low_idx"]],
        "high": bin_edges[p["high_idx"] + 1],
        "volume": sum(bins[p["low_idx"]:p["high_idx"] + 1]),
        "peak_volume": p["seed_volume"],
    } for p in merged]


# ── Node position relative to a price ───────────────────────────────────────
# HVN/LVN pockets were computed and drawn on the chart but never read back into
# the screening path, so "price is above value" was sayable while "price is
# sitting on an HVN" / "there is an LVN air pocket overhead" was not — which is
# the actionable half (HVN = magnet/S-R, LVN = fast traverse).
def _nearest_nodes(price: float, zones: list[dict]) -> dict:
    """Where `price` sits relative to a set of pockets.

    Returns `inside` plus signed distances (in %) to the nearest pocket edge
    above and below. "Above" measures to the nearest pocket whose *low* is above
    price; "below" to the nearest pocket whose *high* is below it. Both are None
    when there is no pocket on that side.
    """
    inside = any(z["low"] <= price <= z["high"] for z in zones)
    above = [z["low"] for z in zones if z["low"] > price]
    below = [z["high"] for z in zones if z["high"] < price]
    return {
        "inside": inside,
        "above_pct": ((min(above) - price) / price * 100) if above and price else None,
        "below_pct": ((price - max(below)) / price * 100) if below and price else None,
    }


# ── Convenience full pipeline ───────────────────────────────────────────────
def compute_profile(df: pd.DataFrame, **opts: Any) -> dict | None:
    """Build the full volume profile for `df`. Returns None if unusable."""
    o = {**DEFAULT_OPTS, **opts}
    if df is None or len(df) < 2:
        return None
    if not {"high", "low", "close", "volume"}.issubset(df.columns):
        return None

    window = df.tail(o["lookback"]) if o["lookback"] else df
    if len(window) < 2:
        return None

    hist = _build_histogram(
        window["high"].to_numpy(), window["low"].to_numpy(),
        window["close"].to_numpy(), window["volume"].to_numpy(),
        o["bins"],
    )
    if hist is None:
        return None

    poc = _find_poc(hist)
    value_area = _find_value_area(hist, poc, o["value_area_pct"])
    hvn_zones = _find_nodes(hist, o["hvn_mult"], o["hvn_expand_tol"], "hvn")
    lvn_zones = _find_nodes(hist, o["lvn_mult"], o["lvn_expand_tol"], "lvn")

    return {
        "bin_edges": hist["bin_edges"], "bins": hist["bins"],
        "lo": hist["lo"], "hi": hist["hi"], "bin_size": hist["bin_size"],
        "total_volume": sum(hist["bins"]),
        "poc": poc, "value_area": value_area,
        "hvn_zones": hvn_zones, "lvn_zones": lvn_zones,
        "opts": o,
    }


def find_confluence(points: list[dict], profile: dict | None,
                    tol_pct: float = 0.004) -> list[dict]:
    """Points (e.g. Elliott Wave pivots) that line up with profile zones."""
    if not profile or not points:
        return []

    out: list[dict] = []
    for p in points:
        tol = p["price"] * tol_pct
        matches: list[dict] = []

        if abs(p["price"] - profile["poc"]["price"]) <= tol:
            matches.append({"type": "POC", "detail": profile["poc"]["price"]})
        if abs(p["price"] - profile["value_area"]["high"]) <= tol:
            matches.append({"type": "VAH", "detail": profile["value_area"]["high"]})
        if abs(p["price"] - profile["value_area"]["low"]) <= tol:
            matches.append({"type": "VAL", "detail": profile["value_area"]["low"]})
        for z in profile["hvn_zones"]:
            if z["low"] - tol <= p["price"] <= z["high"] + tol:
                matches.append({"type": "HVN", "detail": [z["low"], z["high"]]})
        for z in profile["lvn_zones"]:
            if z["low"] - tol <= p["price"] <= z["high"] + tol:
                matches.append({"type": "LVN", "detail": [z["low"], z["high"]]})

        if matches:
            out.append({**p, "matches": matches})
    return out


# ── Derived read: where is price sitting relative to the profile? ────────────
def describe_position(df: pd.DataFrame, profile: dict | None) -> dict | None:
    """Summarize price-vs-profile into the handful of facts a setup card wants.

    Returns None when there's no usable profile, so callers can degrade to
    profile-free behavior rather than guessing.
    """
    if not profile or df is None or len(df) == 0:
        return None

    price = float(df["close"].iloc[-1])
    poc_price = profile["poc"]["price"]
    va = profile["value_area"]
    total = profile["total_volume"]

    # Share of profile volume resting above the POC — a lopsided profile means
    # most business was done on one side of the control price.
    bins, edges = profile["bins"], profile["bin_edges"]
    poc_idx = profile["poc"]["idx"]
    vol_above_poc = sum(bins[poc_idx + 1:])
    pct_above_poc = (vol_above_poc / total * 100) if total > 0 else None

    hvn = _nearest_nodes(price, profile["hvn_zones"])
    lvn = _nearest_nodes(price, profile["lvn_zones"])

    if price > va["high"]:
        zone = "above_value"
    elif price < va["low"]:
        zone = "below_value"
    else:
        zone = "inside_value"

    return {
        "price": price,
        "poc": poc_price,
        "vah": va["high"],
        "val": va["low"],
        "zone": zone,
        "above_poc": price > poc_price,
        "pct_volume_above_poc": pct_above_poc,
        "poc_distance_pct": ((price - poc_price) / poc_price * 100) if poc_price else None,
        "value_area_pct": va["pct"] * 100,
        "hvn_count": len(profile["hvn_zones"]),
        "lvn_count": len(profile["lvn_zones"]),
        # Node position — the HVN-magnet / LVN-air-pocket read (see _nearest_nodes).
        "at_hvn": hvn["inside"],
        "hvn_above_pct": hvn["above_pct"],
        "hvn_below_pct": hvn["below_pct"],
        "at_lvn": lvn["inside"],
        "lvn_above_pct": lvn["above_pct"],
        "lvn_below_pct": lvn["below_pct"],
    }
