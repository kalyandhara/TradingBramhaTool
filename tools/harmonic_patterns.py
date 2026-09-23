#!/usr/bin/env python3
"""
harmonic_patterns.py
Fibonacci-ratio harmonic pattern detection (Gartley, Bat, Butterfly, Crab).

Pipeline:
  1. ATR-scaled ZigZag → alternating swing pivots (H/L).
  2. Slide a 5-pivot window (X-A-B-C-D) across the tail of the pivot list.
  3. Match Fib retracement / extension ratios with per-pattern tolerance.
  4. Emit trade plan: entry at D, stop beyond X, targets at 0.382/0.618 of AD.

Bullish  = X(L) A(H) B(L) C(H) D(L)  → long from D
Bearish  = X(H) A(L) B(H) C(L) D(H)  → short from D
"""

from __future__ import annotations
import numpy as np
import pandas as pd


# ── Ratio spec ────────────────────────────────────────────────────────────────
# Each entry: (ab_xa, bc_ab, cd_bc, ad_xa) — either a single value or (lo, hi).
PATTERNS: dict[str, dict] = {
    "Gartley": {
        "ab_xa": 0.618, "bc_ab": (0.382, 0.886),
        "cd_bc": (1.13, 1.618), "ad_xa": 0.786,
    },
    "Bat": {
        "ab_xa": (0.382, 0.50), "bc_ab": (0.382, 0.886),
        "cd_bc": (1.618, 2.618), "ad_xa": 0.886,
    },
    "Butterfly": {
        "ab_xa": 0.786, "bc_ab": (0.382, 0.886),
        "cd_bc": (1.618, 2.24), "ad_xa": 1.27,
    },
    "Crab": {
        "ab_xa": (0.382, 0.618), "bc_ab": (0.382, 0.886),
        "cd_bc": (2.24, 3.618), "ad_xa": 1.618,
    },
}
TOL = 0.06  # ±6% tolerance on single-value ratio targets


# ── ZigZag pivot detection (ATR-scaled) ──────────────────────────────────────
def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(span=n, adjust=False).mean()


def find_pivots(df: pd.DataFrame, atr_mult: float = 2.0) -> list[tuple[int, float, str]]:
    """Alternating (bar_idx, price, 'H'|'L') pivots via ATR-band reversal.
    A pivot is confirmed when price retraces from the running extreme by ≥ atr_mult*ATR."""
    n = len(df)
    if n < 20:
        return []
    atr = _atr(df).bfill().values
    highs = df["high"].values.astype(float)
    lows  = df["low"].values.astype(float)

    pivots: list[tuple[int, float, str]] = []
    # direction: +1 tracking an up-swing (looking for a high pivot), -1 tracking down
    ext_i, ext_v = 0, highs[0]
    direction = 1

    for i in range(1, n):
        thr = atr_mult * atr[i]
        if direction == 1:
            if highs[i] >= ext_v:
                ext_i, ext_v = i, highs[i]
            elif ext_v - lows[i] >= thr:
                pivots.append((ext_i, ext_v, "H"))
                direction = -1
                ext_i, ext_v = i, lows[i]
        else:
            if lows[i] <= ext_v:
                ext_i, ext_v = i, lows[i]
            elif highs[i] - ext_v >= thr:
                pivots.append((ext_i, ext_v, "L"))
                direction = 1
                ext_i, ext_v = i, highs[i]

    # Append the tail as a provisional pivot (opposite kind to the last confirmed)
    if pivots:
        pivots.append((ext_i, ext_v, "H" if direction == 1 else "L"))
        # Prepend a starting pivot opposite in kind to the first confirmed one
        first_i, _, first_k = pivots[0]
        if first_k == "H":
            j = int(np.argmin(lows[:first_i + 1]))
            pivots.insert(0, (j, float(lows[j]), "L"))
        else:
            j = int(np.argmax(highs[:first_i + 1]))
            pivots.insert(0, (j, float(highs[j]), "H"))
    return pivots


# ── Ratio matching ───────────────────────────────────────────────────────────
def _in(val: float, spec) -> bool:
    if isinstance(spec, tuple):
        lo, hi = spec
        return lo - TOL <= val <= hi + TOL
    return abs(val - spec) <= TOL


def _match_ratios(x, a, b, c, d, bullish: bool) -> dict | None:
    xa = abs(a - x)
    ab = abs(b - a)
    bc = abs(c - b)
    cd = abs(d - c)
    ad = abs(d - a)
    if xa == 0 or ab == 0 or bc == 0:
        return None
    r_ab_xa = ab / xa
    r_bc_ab = bc / ab
    r_cd_bc = cd / bc
    r_ad_xa = ad / xa

    for name, spec in PATTERNS.items():
        if (_in(r_ab_xa, spec["ab_xa"]) and _in(r_bc_ab, spec["bc_ab"])
                and _in(r_cd_bc, spec["cd_bc"]) and _in(r_ad_xa, spec["ad_xa"])):
            return {
                "pattern": name,
                "direction": "bullish" if bullish else "bearish",
                "ratios": {
                    "AB/XA": round(r_ab_xa, 3), "BC/AB": round(r_bc_ab, 3),
                    "CD/BC": round(r_cd_bc, 3), "AD/XA": round(r_ad_xa, 3),
                },
            }
    return None


# ── Public API ───────────────────────────────────────────────────────────────
def detect_last_pattern(df: pd.DataFrame, max_age_bars: int = 10,
                         atr_mult: float = 2.0) -> dict | None:
    """Return the most recent harmonic pattern whose D pivot is within max_age_bars.
    None if no valid pattern completes near the current bar."""
    pivots = find_pivots(df, atr_mult=atr_mult)
    if len(pivots) < 5:
        return None

    last_bar = len(df) - 1
    # Iterate 5-pivot windows from newest backward
    for end in range(len(pivots) - 1, 3, -1):
        window = pivots[end - 4:end + 1]
        kinds = "".join(p[2] for p in window)
        d_idx = window[-1][0]
        if last_bar - d_idx > max_age_bars:
            break  # older windows will only be worse
        if kinds == "LHLHL":
            bullish = True
        elif kinds == "HLHLH":
            bullish = False
        else:
            continue
        x, a, b, c, d = [p[1] for p in window]
        m = _match_ratios(x, a, b, c, d, bullish)
        if m is None:
            continue

        # Trade plan
        ad = abs(d - a)
        buffer = 0.005 * abs(x)  # 0.5% beyond the invalidation point
        # The invalidation point is the MORE EXTREME of X and D. For Gartley and
        # Bat, D completes inside XA and X is beyond it. For Butterfly and Crab,
        # D completes BEYOND X (AD/XA 1.27-1.618), so a stop "beyond X" sat on the
        # PROFIT side of the entry -- above a bullish entry, below a bearish one.
        # Found 2026-09-23 (B-124): ~a quarter of Harmonic cards carried that
        # inverted plan, the harness inferred the side from it and scored them as
        # trades in the wrong direction. Anchoring past D for extensions is the
        # standard practice for those two patterns.
        if bullish:
            stop = min(x, d) - buffer
            t1 = d + 0.382 * ad
            t2 = d + 0.618 * ad
            t3 = d + 1.0 * ad
        else:
            stop = max(x, d) + buffer
            t1 = d - 0.382 * ad
            t2 = d - 0.618 * ad
            t3 = d - 1.0 * ad
        entry = d
        risk = abs(entry - stop)
        reward = abs(t2 - entry)
        rr = round(reward / risk, 2) if risk > 0 else 0.0

        m.update({
            "points": {
                "X": {"idx": window[0][0], "price": x},
                "A": {"idx": window[1][0], "price": a},
                "B": {"idx": window[2][0], "price": b},
                "C": {"idx": window[3][0], "price": c},
                "D": {"idx": window[4][0], "price": d},
            },
            "trade": {
                "entry": round(entry, 2),
                "stop": round(stop, 2),
                "targets": [round(t1, 2), round(t2, 2), round(t3, 2)],
                "risk": round(risk, 2),
                "rr_to_t2": rr,
            },
            "age_bars": int(last_bar - d_idx),
        })
        return m
    return None
