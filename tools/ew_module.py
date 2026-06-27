"""
ew_module.py — Elliott Wave probabilistic analysis for daily timeframe
Implements McDowell (2016) Fibonacci statistics and OWL/PTF indicator suite.
Source: wiki/concepts/Elliott-Wave.md

Wave 3 target distribution (extension of W1 from W2 low):
  45% -> 1.618x W1   (primary)
  30% -> 2.618x W1   (extended run)
  15% -> 1.000x W1   (minimum / truncated)
  10% -> 3.618x W1   (rare)

Wave 5 target distribution (measured from estimated W4 low, in W1 magnitudes):
  35% -> 0.618x W1
  35% -> 1.000x W1   (equality — most common anchor)
  15% -> 1.618x W1
  15% -> 0.382x W1   (weak / failed W5)

OWL histogram (McDowell): EMA(low,5) - EMA(low,35).
  Most negative reading in last 144 bars marks Wave 3 peak.

PTF (McDowell): RSI(9) on close, 80/20 bands.
  Penetration of 80 band -> 75% odds of further high in that direction.
  Failure to penetrate 80 during W5 -> exhaustion warning.
"""

import numpy as np
import pandas as pd

# ── Constants ─────────────────────────────────────────────────────────────────

# Pivot detection: 5 bars each side on daily (matches PMax v2 engine)
PIVOT_DEPTH = 5
# Minimum swing size to qualify a pivot (filters noise)
MIN_SWING_PCT = 0.04

# OWL oscillator
OWL_FAST = 5
OWL_SLOW = 35
OWL_LOOKBACK = 144      # bars (~4.8 months on daily)

# PTF
PTF_LEN = 9
PTF_BULL = 80.0
PTF_BEAR = 20.0

# Fibonacci levels
F382, F500, F618, F786 = 0.382, 0.500, 0.618, 0.786
F100, F1272, F1618, F2618, F3618 = 1.000, 1.272, 1.618, 2.618, 3.618

# McDowell W3 probability table:  (fib_ratio, probability_pct, short_label)
W3_TABLE = [
    (F1618, 45, "1.618x"),
    (F2618, 30, "2.618x"),
    (F100,  15, "1.000x"),
    (F3618, 10, "3.618x"),
]

# McDowell W5 probability table (from W4 low, W1 magnitude as ruler)
W5_TABLE = [
    (F618,  35, "0.618x W1"),
    (F100,  35, "1.000x W1 eq"),
    (F1618, 15, "1.618x W1"),
    (F382,  15, "0.382x W1"),
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _owl_histogram(df: pd.DataFrame) -> pd.Series:
    """EMA(low, 5) - EMA(low, 35). Most negative value in 144 bars = W3 anchor."""
    low = df["low"]
    fast = low.ewm(span=OWL_FAST, adjust=False).mean()
    slow = low.ewm(span=OWL_SLOW, adjust=False).mean()
    return fast - slow


def _ptf_rsi(close: pd.Series) -> pd.Series:
    """RSI(9) — PTF indicator. Penetration of 80 band = 75% odds of further high."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=PTF_LEN - 1, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=PTF_LEN - 1, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _find_pivots(df: pd.DataFrame, depth: int = PIVOT_DEPTH, min_pct: float = MIN_SWING_PCT):
    """
    Zigzag pivot detection (depth bars each side).
    Returns list of (bar_idx, price, 'H'|'L'), alternating, significance-filtered.
    """
    highs = df["high"].values
    lows  = df["low"].values
    n = len(df)

    raw = []
    for i in range(depth, n - depth):
        h_win = highs[i - depth: i + depth + 1]
        l_win = lows[i - depth:  i + depth + 1]
        if highs[i] == h_win.max():
            raw.append((i, float(highs[i]), "H"))
        elif lows[i] == l_win.min():
            raw.append((i, float(lows[i]),  "L"))

    # Enforce alternation — merge consecutive same-type, keeping extremes
    alt: list = []
    for p in raw:
        if not alt:
            alt.append(p)
        elif p[2] == alt[-1][2]:
            if (p[2] == "H" and p[1] > alt[-1][1]) or (p[2] == "L" and p[1] < alt[-1][1]):
                alt[-1] = p
        else:
            move = abs(p[1] - alt[-1][1]) / max(alt[-1][1], 1e-9)
            if move >= min_pct:
                alt.append(p)
            elif (p[2] == "H" and p[1] > alt[-1][1]) or (p[2] == "L" and p[1] < alt[-1][1]):
                alt[-1] = p

    return alt


def _find_w1_structure(pivots):
    """
    From pivot list, find (w1_start, w1_high, w2_low) — the most recent clear
    L -> H -> L sequence. Returns None if insufficient pivots.
    """
    lows  = [p for p in pivots if p[2] == "L"]
    highs = [p for p in pivots if p[2] == "H"]

    if len(lows) < 2 or not highs:
        return None

    # Most recent low = W2 candidate
    w2 = lows[-1]

    # W1 high = highest high between W1_start and W2_low
    w1_high_cands = [h for h in highs if h[0] < w2[0]]
    if not w1_high_cands:
        return None
    w1_high = max(w1_high_cands, key=lambda p: p[1])

    # W1 start = lowest low before W1 high
    w1_start_cands = [l for l in lows if l[0] < w1_high[0]]
    if not w1_start_cands:
        return None
    w1_start = min(w1_start_cands, key=lambda p: p[1])

    return w1_start, w1_high, w2


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_ew(df: pd.DataFrame) -> dict:
    """
    Full Elliott Wave probabilistic analysis on a daily OHLCV DataFrame.

    Required columns: open, high, low, close, volume (lowercase).
    Minimum rows: ~180 (for OWL 144-bar lookback + pivot warmup).

    Returns a dict (all keys always present):
      wave_pos       str    'W3', 'W5', 'W2', 'W2-deep', 'ABC', 'unclear'
      confidence     int    0-100 wave-count reliability score
      ew_valid       bool   passes EW hard rules (W2<100% W1, etc.)

      w1_start       float  W1 origin price
      w1_high        float  W1 peak price
      w1_mag         float  W1 magnitude in price units
      w2_low         float  W2 corrective low (stop-invalidation level)
      w2_retrace_pct float  W2 retrace as % of W1 (ideal 38.2-61.8%)

      w3_targets     list   [(price, prob_pct, label), ...] from W2 low
      w4_est         float  estimated W4 low (38.2% retrace of W3 from W3@1.618)
      w5_targets     list   [(price, prob_pct, label), ...] from W4 est

      owl_now        float  current OWL histogram value
      owl_w3_peak    float  most negative OWL in last 144 bars (W3 anchor)
      owl_signal     str    'W3-active', 'W3-past', 'corrective', 'unclear'
      ptf_rsi9       float  current RSI(9)
      ptf_signal     str    'bullish-penetration', 'divergence-warn', 'neutral'

      stop_zone      float  W1 start (full invalidation price)
      ext_risk       str    'NORMAL', 'EXTENDED', 'EXHAUSTION'
      note           str    human-readable diagnosis
    """
    empty = dict(
        wave_pos="unclear", confidence=0, ew_valid=False,
        w1_start=None, w1_high=None, w1_mag=None,
        w2_low=None, w2_retrace_pct=None,
        w3_targets=[], w4_est=None, w5_targets=[],
        owl_now=None, owl_w3_peak=None, owl_signal="unclear",
        ptf_rsi9=None, ptf_signal="neutral",
        stop_zone=None, ext_risk="NORMAL", note="",
    )

    if len(df) < 180:
        empty["note"] = "insufficient data (<180 bars)"
        return empty

    close = df["close"]
    current = float(close.iloc[-1])

    # ── OWL ──────────────────────────────────────────────────────────────
    owl = _owl_histogram(df)
    owl_now = float(owl.iloc[-1])
    owl_min = float(owl.tail(OWL_LOOKBACK).min())   # most negative = W3 anchor

    if owl_now < 0 and abs(owl_now) >= abs(owl_min) * 0.80:
        owl_signal = "W3-active"      # near or at OWL W3 trough
    elif owl_now > 0 and owl_min < -0.5:
        owl_signal = "W3-past"        # was deep negative, now recovered
    elif owl_now > 0:
        owl_signal = "corrective"     # above-zero = uptrend oscillator above baseline
    else:
        owl_signal = "unclear"

    # ── PTF ──────────────────────────────────────────────────────────────
    ptf = _ptf_rsi(close)
    ptf_now   = float(ptf.iloc[-1])
    ptf_tail  = ptf.tail(15)
    ptf_peak  = float(ptf_tail.max())

    if ptf_now > PTF_BULL:
        ptf_signal = "bullish-penetration"
    elif ptf_peak > PTF_BULL and ptf_now < PTF_BULL and current > float(close.tail(15).iloc[0]):
        ptf_signal = "divergence-warn"    # RSI fell from 80+ but price still rising = W5 exhaustion
    else:
        ptf_signal = "neutral"

    # ── Pivots ───────────────────────────────────────────────────────────
    pivots = _find_pivots(df)
    if len(pivots) < 4:
        result = dict(empty)
        result.update(
            owl_now=round(owl_now, 4), owl_w3_peak=round(owl_min, 4),
            owl_signal=owl_signal, ptf_rsi9=round(ptf_now, 1),
            ptf_signal=ptf_signal, note="too few pivots (<4)",
        )
        return result

    # ── W1/W2 structure ──────────────────────────────────────────────────
    struct = _find_w1_structure(pivots)
    if struct is None:
        result = dict(empty)
        result.update(
            owl_now=round(owl_now, 4), owl_w3_peak=round(owl_min, 4),
            owl_signal=owl_signal, ptf_rsi9=round(ptf_now, 1),
            ptf_signal=ptf_signal, note="could not identify W1 structure",
        )
        return result

    w1_start_p, w1_high_p, w2_p = struct
    w1_start = w1_start_p[1]
    w1_high  = w1_high_p[1]
    w2_low   = w2_p[1]
    w1_mag   = w1_high - w1_start

    if w1_mag <= 0:
        empty["note"] = "degenerate W1 (mag <= 0)"
        return empty

    w2_retrace = (w1_high - w2_low) / w1_mag
    w2_retrace_pct = round(w2_retrace * 100, 1)

    # ── EW Validity ───────────────────────────────────────────────────────
    # Hard rule: W2 never retraces 100%+ of W1
    ew_valid = (w2_retrace < 1.0) and (w2_low > w1_start)

    # ── Confidence ────────────────────────────────────────────────────────
    conf = 0
    # W2 in 38.2-61.8% zone: gold standard
    if F382 <= w2_retrace <= F618:
        conf += 25
    elif w2_retrace < F382:
        conf += 10
    elif w2_retrace <= F786:
        conf += 15
    # Price above W1 high (actually in W3+ territory)
    if current > w1_high:
        conf += 20
    # OWL confirmation
    if owl_signal in ("W3-active", "W3-past"):
        conf += 15
    # PTF bullish
    if ptf_signal == "bullish-penetration":
        conf += 15
    elif ptf_now > 50:
        conf += 5
    # Pivot count richness
    if len(pivots) >= 7:
        conf += 15
    elif len(pivots) >= 5:
        conf += 10
    elif len(pivots) >= 4:
        conf += 5
    # EW validity
    if ew_valid:
        conf += 10

    conf = min(conf, 100)

    # ── Wave position ─────────────────────────────────────────────────────
    above_w1 = current > w1_high
    post_w2_highs = [p for p in pivots if p[0] > w2_p[0] and p[2] == "H"]

    if not above_w1:
        if w2_retrace > F786:
            wave_pos = "W2-deep"
        elif w2_retrace > F100:
            wave_pos = "unclear"     # W2 > W1 = not an EW structure here
        else:
            wave_pos = "W2"
    else:
        # Above W1 high — in W3 or W5
        in_w5 = (owl_signal == "W3-past") and (len(post_w2_highs) >= 2)
        # Additional W5 signal: PTF divergence
        if ptf_signal == "divergence-warn":
            in_w5 = True
        wave_pos = "W5" if in_w5 else "W3"

    # ── Fibonacci targets ─────────────────────────────────────────────────
    # W3 targets from W2 low
    w3_targets = [
        (round(w2_low + ratio * w1_mag, 2), prob, label)
        for ratio, prob, label in W3_TABLE
    ]

    # Estimated W4 low = W3 top (1.618x) minus 38.2% of that W3 leg
    w3_top_est = w2_low + F1618 * w1_mag
    w4_est     = round(w3_top_est - F382 * (w3_top_est - w2_low), 2)

    # W5 targets from W4 estimate
    w5_targets = [
        (round(w4_est + ratio * w1_mag, 2), prob, label)
        for ratio, prob, label in W5_TABLE
    ]

    # ── Extension risk ─────────────────────────────────────────────────────
    w3_primary = w2_low + F1618 * w1_mag
    w3_extended = w2_low + F2618 * w1_mag

    if current > w3_extended:
        ext_risk = "EXHAUSTION"
    elif current > w3_primary:
        ext_risk = "EXTENDED"
    else:
        ext_risk = "NORMAL"

    # ── Human-readable note ────────────────────────────────────────────────
    if not ew_valid:
        note = f"INVALID: W2 retrace={w2_retrace_pct}% exceeds W1 — not an EW impulse"
    elif wave_pos == "W3":
        pct_to_target = (current - w2_low) / (w1_mag * F1618) * 100
        note = f"{pct_to_target:.0f}% toward W3@1.618x target={w3_primary:.1f}"
    elif wave_pos == "W5":
        w5_eq = w4_est + w1_mag
        note = f"W5 in progress; equality target={w5_eq:.1f}; divergence={ptf_signal}"
    elif wave_pos in ("W2", "W2-deep"):
        note = f"W2 pullback {w2_retrace_pct}%; watch for W3 launch above {w1_high:.1f}"
    else:
        note = f"wave={wave_pos}; W2_retrace={w2_retrace_pct}%"

    if ext_risk != "NORMAL":
        note = ext_risk + " — " + note

    return dict(
        wave_pos=wave_pos,
        confidence=conf,
        ew_valid=ew_valid,
        w1_start=round(w1_start, 2),
        w1_high=round(w1_high, 2),
        w1_mag=round(w1_mag, 2),
        w2_low=round(w2_low, 2),
        w2_retrace_pct=w2_retrace_pct,
        w3_targets=w3_targets,
        w4_est=w4_est,
        w5_targets=w5_targets,
        owl_now=round(owl_now, 4),
        owl_w3_peak=round(owl_min, 4),
        owl_signal=owl_signal,
        ptf_rsi9=round(ptf_now, 1),
        ptf_signal=ptf_signal,
        stop_zone=round(w1_start, 2),
        ext_risk=ext_risk,
        note=note,
    )


def ew_summary_row(ew: dict) -> dict:
    """
    Flatten analyze_ew() output into a flat dict of Excel-friendly columns.
    Picks the primary W3 target (1.618x, 45%) and top 2 W5 targets.
    """
    if not ew["w3_targets"]:
        return {
            "EW Wave":          ew["wave_pos"],
            "EW Confidence":    ew["confidence"],
            "EW Valid":         ew["ew_valid"],
            "W1 Magnitude":     None,
            "W2 Low (stop)":    None,
            "W2 Retrace %":     None,
            "W3 T1 1.618 (45%)": None,
            "W3 T2 2.618 (30%)": None,
            "W3 T3 1.000 (15%)": None,
            "W4 Est Low":       None,
            "W5 T1 eq (35%)":   None,
            "W5 T2 ext (15%)":  None,
            "OWL Signal":       ew["owl_signal"],
            "PTF RSI(9)":       ew["ptf_rsi9"],
            "PTF Signal":       ew["ptf_signal"],
            "Ext Risk":         ew["ext_risk"],
            "EW Note":          ew["note"],
        }

    w3 = {lbl: (px, pr) for px, pr, lbl in ew["w3_targets"]}
    w5 = {lbl: (px, pr) for px, pr, lbl in ew["w5_targets"]}

    return {
        "EW Wave":           ew["wave_pos"],
        "EW Confidence":     ew["confidence"],
        "EW Valid":          ew["ew_valid"],
        "W1 Magnitude":      ew["w1_mag"],
        "W2 Low (stop)":     ew["w2_low"],
        "W2 Retrace %":      ew["w2_retrace_pct"],
        "W3 T1 1.618 (45%)": w3.get("1.618x", (None, None))[0],
        "W3 T2 2.618 (30%)": w3.get("2.618x", (None, None))[0],
        "W3 T3 1.000 (15%)": w3.get("1.000x", (None, None))[0],
        "W4 Est Low":        ew["w4_est"],
        "W5 T1 eq (35%)":    w5.get("1.000x W1 eq", (None, None))[0],
        "W5 T2 ext (15%)":   w5.get("1.618x W1", (None, None))[0],
        "OWL Signal":        ew["owl_signal"],
        "PTF RSI(9)":        ew["ptf_rsi9"],
        "PTF Signal":        ew["ptf_signal"],
        "Ext Risk":          ew["ext_risk"],
        "EW Note":           ew["note"],
    }
