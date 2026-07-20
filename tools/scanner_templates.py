#!/usr/bin/env python3
"""
scanner_templates.py
Pre-built pattern scanners inspired by SwingEdge's scanner hub.
Each scanner function takes a fetched OHLCV DataFrame and returns a result
dict (symbol, pattern_type, tags, reasons, score) or None if no match.
"""

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _sma(series: pd.Series, n: int) -> float:
    v = series.rolling(n).mean().iloc[-1]
    return float(v) if not pd.isna(v) else float("nan")


def _ema_series(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


# Benchmark weighted trailing return for the active scan (set by run_scanner
# when a benchmark DataFrame is supplied). When set, _rs_raw returns the
# stock's EXCESS return over the benchmark — a true relative-strength line —
# instead of an absolute trailing return.
_BENCHMARK_WRET: float | None = None


def _weighted_trailing_return(close: pd.Series) -> float:
    """IBD-style weighted trailing return (percent), tilted to the most recent
    quarter. Degrades gracefully on short history."""
    n = len(close)
    last = float(close.iloc[-1])

    def _ret(days: int) -> float | None:
        if n <= days:
            return None
        past = float(close.iloc[-1 - days])
        return (last / past - 1.0) if past > 0 else None

    num = 0.0
    wsum = 0.0
    for days, w in [(63, 0.4), (126, 0.2), (189, 0.2), (252, 0.2)]:
        r = _ret(days)
        if r is not None:
            num += w * r
            wsum += w
    return (num / wsum * 100.0) if wsum else 0.0


def _rs_raw(df: pd.DataFrame) -> float:
    """Relative-strength metric ranked into a 0-100 percentile by
    _finalize_relative_strength(). When run_scanner set a benchmark this is the
    stock's excess return over that benchmark (e.g. vs Nifty); otherwise it
    falls back to the absolute weighted trailing return."""
    stock = _weighted_trailing_return(df["close"])
    return stock - (_BENCHMARK_WRET or 0.0)


_SIGNAL_BANDS = [(85, "Very Strong"), (70, "Strong"),
                 (55, "Moderate"), (40, "Watch"), (0, "Weak")]


def _signal_band(score: float) -> str:
    for thr, label in _SIGNAL_BANDS:
        if score >= thr:
            return label
    return "Weak"


def _finalize_relative_strength(results: list[dict]) -> None:
    """Rank rs_raw across the matched set into a 0-100 RS percentile, then blend
    it into the total score for scanners that expose a ``score_base``. Scanners
    that don't emit ``rs_raw``/``score_base`` are left untouched. Mutates in
    place (RS rank is by definition relative to the rest of the scan)."""
    rated = [r for r in results if "rs_raw" in r]
    if not rated:
        return
    ordered = sorted(rated, key=lambda r: r["rs_raw"])
    m = len(ordered)
    for rank, r in enumerate(ordered):
        r["rs_rank"] = 50 if m == 1 else round(rank / (m - 1) * 100)
    for r in rated:
        if "score_base" in r:
            r["score"] = round(0.75 * r["score_base"] + 0.25 * r["rs_rank"], 1)
            r["signal"] = _signal_band(r["score"])


# ──────────────────────────────────────────────────────────────────────────────
# Scanner functions
# ──────────────────────────────────────────────────────────────────────────────

def scan_52w_high_leaders(df: pd.DataFrame) -> dict | None:
    """Within 5% of 52-week high with MA stack intact."""
    if len(df) < 60:
        return None
    last = float(df["close"].iloc[-1])
    high_52 = float(df["high"].tail(252).max())
    pct = (high_52 - last) / high_52 * 100
    if pct > 5:
        return None
    sma50 = _sma(df["close"], 50)
    sma200 = _sma(df["close"], 200)
    if np.isnan(sma50) or last < sma50:
        return None
    reasons = [
        f"Within {pct:.1f}% of 52-week high — minimal overhead resistance",
        f"Holding above SMA50 ({sma50:.0f})" + (
            f" and SMA200 ({sma200:.0f})" if not np.isnan(sma200) else ""
        ),
    ]
    vol_avg = float(df["volume"].tail(20).mean())
    vol_last = float(df["volume"].iloc[-1])
    if vol_last > vol_avg * 1.5:
        reasons.append(f"Volume {vol_last / vol_avg:.1f}× average — institutional activity")
    return {
        "pattern_type": "52-Week High Leader",
        "tags": [f"{pct:.1f}% from 52w high", "Near highs"],
        "reasons": reasons,
        "score": round(10 - pct, 2),
    }


def scan_stage2_uptrend(df: pd.DataFrame) -> dict | None:
    """Minervini Stage 2: SMA50 > SMA150 > SMA200, all rising, price above SMA50."""
    if len(df) < 210:
        return None
    close = df["close"]
    last = float(close.iloc[-1])
    sma50 = _sma(close, 50)
    sma150 = _sma(close, 150)
    sma200 = _sma(close, 200)
    sma200_1m = _sma(close.iloc[:-21], 200) if len(df) >= 221 else sma200
    if any(np.isnan(v) for v in [sma50, sma150, sma200]):
        return None
    if not (last > sma50 > sma150 > sma200):
        return None
    if not np.isnan(sma200_1m) and sma200 <= sma200_1m:
        return None
    pct_ext = (last - sma50) / sma50 * 100
    reasons = [
        f"Price ({last:.0f}) > SMA50 ({sma50:.0f}) > SMA150 ({sma150:.0f}) > SMA200 ({sma200:.0f})",
        "SMA200 rising month-over-month — Stage 2 confirmed",
    ]
    if pct_ext < 15:
        reasons.append(f"Only {pct_ext:.1f}% above SMA50 — room to run, not extended")
    return {
        "pattern_type": "Stage 2 Uptrend",
        "tags": ["Stage 2", "MA stack"],
        "reasons": reasons,
        "score": round(sma50 / sma200 * 10, 2),
    }


def scan_pullback_to_ema(df: pd.DataFrame) -> dict | None:
    """Pulled back to 21-EMA in last 5 days and is recovering above it."""
    if len(df) < 60:
        return None
    close = df["close"]
    ema21 = _ema_series(close, 21)
    last = float(close.iloc[-1])
    ema_now = float(ema21.iloc[-1])
    if last < ema_now:
        return None
    low_5d = float(df["low"].tail(5).min())
    if low_5d > ema_now * 1.02:
        return None
    sma200 = _sma(close, 200)
    if not np.isnan(sma200) and last < sma200:
        return None
    vol_5d = float(df["volume"].tail(5).mean())
    vol_20d = float(df["volume"].tail(20).mean())
    reasons = [
        f"Touched EMA21 ({ema_now:.0f}) in last 5 sessions — controlled pullback",
        f"Now recovering at {last:.0f} — buyers stepping in",
    ]
    if vol_5d < vol_20d:
        reasons.append("Volume dried up on pullback — healthy retracement (no distribution)")
    return {
        "pattern_type": "Pullback Entry",
        "tags": ["EMA21 touch", "Recovering"],
        "reasons": reasons,
        "score": round((last - ema_now) / ema_now * 100, 2),
    }


# Darvas box tuning constants
_DARVAS_LOOKBACK = 40        # bars to search for the box swing pivots
_DARVAS_PIVOT = 3            # fractal half-width for a confirmed swing pivot
_DARVAS_MAX_BOX_HEIGHT = 15  # % — looser than this isn't a tight box
_DARVAS_MIN_POSITION = 40    # % of range — below this is too deep to be actionable
_DARVAS_PRESSING = 85        # % of range — hugging the top = "Near breakout"


def _darvas_box(df: pd.DataFrame, lookback: int = _DARVAS_LOOKBACK,
                prd: int = _DARVAS_PIVOT) -> dict | None:
    """Box boundaries from recent confirmed swing pivots (not a raw rolling
    max/min — the last ``prd`` unconfirmed bars are excluded and each extreme
    must be a genuine local pivot, so single-bar spikes don't set the box).
    Returns box_top/box_bottom and each level's age in bars, or None."""
    n = len(df)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    lo = max(prd, n - lookback)
    hi = n - prd
    piv_h = [i for i in range(lo, hi) if highs[i] == highs[i - prd:i + prd + 1].max()]
    piv_l = [i for i in range(lo, hi) if lows[i] == lows[i - prd:i + prd + 1].min()]
    if not piv_h or not piv_l:
        return None
    top_idx = max(piv_h, key=lambda i: highs[i])
    bot_idx = min(piv_l, key=lambda i: lows[i])
    box_top = float(highs[top_idx])
    box_bottom = float(lows[bot_idx])
    if box_bottom <= 0 or box_top <= box_bottom:
        return None
    return {
        "box_top": box_top,
        "box_bottom": box_bottom,
        "top_age": n - 1 - top_idx,
        "bottom_age": n - 1 - bot_idx,
    }


def scan_darvas_box(df: pd.DataFrame) -> dict | None:
    """Darvas box: a consolidation bounded by recent swing pivots.

    States — Active (inside the box), Near breakout (pressing the top),
    Breakout (closed above the top). Emits a 0-100 base score (blended with an
    RS percentile in run_scanner), a volume-quality tag, from-pivot distance,
    vol ×50d and fail-risk flags for the Scanner Hub card."""
    if len(df) < 60:
        return None
    box = _darvas_box(df)
    if box is None:
        return None
    box_top = box["box_top"]
    box_bottom = box["box_bottom"]
    box_height = (box_top - box_bottom) / box_bottom * 100
    if box_height > _DARVAS_MAX_BOX_HEIGHT:
        return None

    last = float(df["close"].iloc[-1])
    if last < box_bottom:
        return None                        # broke down out of the box — not our setup

    rng = box_top - box_bottom
    position = (last - box_bottom) / rng * 100      # % of box range
    from_pivot = (last - box_top) / box_top * 100   # % vs the breakout level

    # trend guard — box must be forming in (or just under) an uptrend
    sma150 = _sma(df["close"], 150)
    if not np.isnan(sma150) and last < sma150 * 0.95:
        return None

    # ── state ──
    if last >= box_top:
        state = "Breakout"
    elif position >= _DARVAS_PRESSING:
        state = "Near breakout"
    else:
        if position < _DARVAS_MIN_POSITION:
            return None                    # too deep in the box to be actionable
        state = "Active"

    # ── volume participation ──
    vol_last = float(df["volume"].iloc[-1])
    vol_50 = float(df["volume"].tail(50).mean())
    vol_x50 = (vol_last / vol_50) if vol_50 > 0 else 0.0
    base_vol_ratio = (float(df["volume"].tail(5).mean()) / vol_50) if vol_50 > 0 else 1.0

    if state == "Breakout":
        vol_q = ("Surge on break" if vol_x50 >= 1.5
                 else "Confirmed" if vol_x50 >= 1.0
                 else "Low participation")
    else:
        vol_q = ("Dry-up in base" if base_vol_ratio <= 0.7
                 else "Early surge" if vol_x50 >= 1.5
                 else "Normal")

    # ── fail-risk flags ──
    fail_risk = []
    if state == "Breakout" and from_pivot > 5:
        fail_risk.append(f"Extended {from_pivot:.0f}% above pivot")
    if state == "Breakout" and vol_x50 < 1.0:
        fail_risk.append("Breakout on below-average volume — false-break prone")
    if box_height > 12:
        fail_risk.append(f"Wide {box_height:.0f}% box — looser structure")
    if box["top_age"] > 60:
        fail_risk.append("Stale box — ceiling set >60 bars ago")

    # ── base score (0-100; RS percentile blended in by run_scanner) ──
    quality = max(0.0, (15 - box_height) / 15) * 22 + min(position, 100) / 100 * 18
    if state == "Breakout":
        vol_pts = max(0.0, min(vol_x50 / 2.0, 1.0)) * 30      # full marks at ≥2× 50d
    elif vol_q == "Dry-up in base":
        vol_pts = 22
    else:
        vol_pts = 12
    state_bonus = {"Breakout": 15, "Near breakout": 10, "Active": 5}[state]
    score_base = quality + vol_pts + state_bonus - 6 * len(fail_risk)
    score_base = float(max(0.0, min(score_base, 100.0)))

    # ── reasons (vol-quality and fail-risk surface as dedicated card fields) ──
    reasons = [
        f"{state} — {box_height:.1f}% box ({box_bottom:.1f}–{box_top:.1f}); "
        f"price at {position:.0f}% of range",
    ]
    if state == "Breakout":
        reasons.append(f"Cleared box top by {from_pivot:.1f}% on {vol_x50:.1f}× 50-day volume")
    else:
        reasons.append(f"{from_pivot:+.1f}% from pivot ({box_top:.1f}) · Vol {vol_x50:.1f}× 50-day")

    return {
        "pattern_type": state,
        "tags": [f"{box_height:.1f}% box", "Darvas", state],
        "filter_tags": [state],
        "reasons": reasons,
        "score_base": round(score_base, 2),
        "score": round(score_base, 2),     # provisional — run_scanner blends in RS
        "rs_raw": round(_rs_raw(df), 3),
        "state": state,
        "vol_q": vol_q,
        "vol_x50d": round(vol_x50, 2),
        "from_pivot": round(from_pivot, 2),
        "fail_risk": fail_risk,
        "box_top": round(box_top, 2),
        "box_bottom": round(box_bottom, 2),
    }


def scan_momentum_continuation(df: pd.DataFrame) -> dict | None:
    """Stocks near 20-day high with intact MA stack — momentum still running."""
    if len(df) < 60:
        return None
    close = df["close"]
    last = float(close.iloc[-1])
    sma50 = _sma(close, 50)
    sma150 = _sma(close, 150)
    if np.isnan(sma50) or np.isnan(sma150):
        return None
    if not (last > sma50 > sma150):
        return None
    high_20 = float(df["high"].tail(20).max())
    pct_from_high = (high_20 - last) / high_20 * 100
    if pct_from_high > 8:
        return None
    mom_3m = (last / float(close.iloc[-63]) - 1) * 100 if len(df) >= 63 else 0.0
    reasons = [
        f"MA stack intact: price > SMA50 ({sma50:.0f}) > SMA150 ({sma150:.0f})",
        f"Within {pct_from_high:.1f}% of 20-day high",
    ]
    if mom_3m > 10:
        reasons.append(f"3-month return {mom_3m:.1f}% — strong sustained momentum")
    return {
        "pattern_type": "Momentum Continuation",
        "tags": ["MA stack", f"{mom_3m:.0f}% 3m return"],
        "reasons": reasons,
        "score": round(mom_3m, 2),
    }


def scan_vcp(df: pd.DataFrame) -> dict | None:
    """Volatility contraction: three successive 10-day ranges each tighter than the last."""
    if len(df) < 35:
        return None
    close = df["close"]
    last = float(close.iloc[-1])
    sma50 = _sma(close, 50)
    if np.isnan(sma50) or last < sma50:
        return None

    def _range_pct(window: pd.DataFrame) -> float:
        lo = float(window["low"].min())
        hi = float(window["high"].max())
        return (hi - lo) / lo * 100 if lo > 0 else float("inf")

    r0 = _range_pct(df.tail(10))
    r1 = _range_pct(df.iloc[-20:-10])
    r2 = _range_pct(df.iloc[-30:-20])
    if not (r2 > r1 > r0):
        return None
    contraction = (r2 - r0) / r2 * 100
    if contraction < 20:
        return None
    vol_recent = float(df["volume"].tail(10).mean())
    vol_prior = float(df["volume"].iloc[-30:-10].mean())
    reasons = [
        f"Ranges contracting: {r2:.1f}% → {r1:.1f}% → {r0:.1f}% (last 30 days)",
        f"{contraction:.0f}% total volatility contraction — classic VCP signature",
    ]
    if vol_recent < vol_prior:
        reasons.append("Volume drying on contraction — institutional absorption, not selling")
    return {
        "pattern_type": "VCP Coiling",
        "tags": [f"{contraction:.0f}% contraction", "VCP"],
        "reasons": reasons,
        "score": round(contraction, 2),
    }


def detect_vcp_geometry(df: pd.DataFrame, window: int = 90,
                        pivot_len: int = 3, min_contractions: int = 2,
                        max_contractions: int = 4,
                        tightest_tolerance: float = 1.15,
                        atr_len: int = 14) -> dict | None:
    """Proper pivot-based VCP detector for chart overlay use (see
    concepts/VCP.md). The Scanner Hub's `scan_vcp` uses a coarser 3-window
    range check that's fine for card triage but doesn't yield the per-
    contraction geometry needed to draw the coil. This one walks confirmed
    swing highs, extracts each pullback leg, verifies the depths shrink
    and volume dries, and returns bar-indexed geometry + a Minervini-style
    trade plan.

    Contraction footprint returned as e.g. `28/12/6` (percent depths) —
    matches the Minervini `WW depth/final Tcount` notation.
    """
    # Enough history for the window itself plus one 50-DMA lookback for the
    # volume dry-up reference. If either isn't there, no valid VCP call
    # can be made — abstain rather than guess.
    if len(df) < max(window, 55) or "volume" not in df.columns:
        return None
    w = df.tail(window)
    m = len(w)
    h = w["high"].to_numpy(dtype=float)
    l = w["low"].to_numpy(dtype=float)
    c = w["close"].to_numpy(dtype=float)
    v = w["volume"].to_numpy(dtype=float)

    # Confirmed pivot highs — a bar higher than pivot_len neighbors on each
    # side. The last (pivot_len) bars of the window can't confirm as pivots
    # (no future neighbors yet) so we handle the in-progress right-side
    # separately below.
    raw_pivots = []
    for i in range(pivot_len, m - pivot_len):
        seg = h[i - pivot_len:i + pivot_len + 1]
        if h[i] == seg.max():
            raw_pivots.append(i)
    # Dedupe plateau pivots — a flat-top swing (multiple adjacent bars at the
    # same high) produces one pivot per bar in the plateau. Left uncorrected,
    # each adjacent pair generated a spurious ~0% "contraction" that then
    # failed the "final tightest" gate and made valid VCPs invisible.
    # Rule: pivots within `pivot_len` bars of each other AND within 0.3% of
    # each other's price get merged; keep the leftmost, drop the rest.
    pivot_highs = []
    for i in raw_pivots:
        if pivot_highs:
            prev = pivot_highs[-1]
            if (i - prev) <= pivot_len and abs(h[i] - h[prev]) / max(h[prev], 1e-9) < 0.003:
                continue
        pivot_highs.append(i)
    if len(pivot_highs) < 2:
        return None

    # Build contractions from consecutive pivot-high pairs. A contraction =
    # (swing high → lowest low before the next swing high). Depth is the
    # % drop from that swing high to the leg low.
    contractions = []
    for k in range(len(pivot_highs) - 1):
        p_hi, p_next = pivot_highs[k], pivot_highs[k + 1]
        seg_l = l[p_hi:p_next]
        if not len(seg_l):
            continue
        lo_off = int(seg_l.argmin())
        lo_idx = p_hi + lo_off
        hi_price = float(h[p_hi])
        lo_price = float(l[lo_idx])
        depth = (hi_price - lo_price) / hi_price * 100 if hi_price > 0 else 0.0
        seg_vol = float(v[p_hi:p_next].mean())
        contractions.append({
            "high_idx": p_hi, "high_price": hi_price,
            "low_idx": lo_idx, "low_price": lo_price,
            "depth_pct": depth, "avg_volume": seg_vol,
        })

    # In-progress right-side contraction (from the last confirmed pivot to
    # the current bar) — the tightening usually happens HERE, so the pattern
    # would look broken without it.
    last_hi = pivot_highs[-1]
    tail_len = m - 1 - last_hi
    if tail_len >= 3:
        lo_off = int(l[last_hi:].argmin())
        lo_idx = last_hi + lo_off
        hi_price = float(h[last_hi])
        lo_price = float(l[lo_idx])
        depth = (hi_price - lo_price) / hi_price * 100 if hi_price > 0 else 0.0
        seg_vol = float(v[last_hi:].mean())
        contractions.append({
            "high_idx": last_hi, "high_price": hi_price,
            "low_idx": lo_idx, "low_price": lo_price,
            "depth_pct": depth, "avg_volume": seg_vol,
            "in_progress": True,
        })

    contractions = contractions[-max_contractions:]
    if len(contractions) < min_contractions:
        return None

    depths = [c["depth_pct"] for c in contractions]

    # Core VCP rule: final contraction must be the tightest of the series
    # (Minervini's "final tightest" rule — the whole edge of the pattern is
    # this bit). Not just "smaller than the previous"; the smallest so far.
    # Autopsy 2026-07-14: with the old strict `≤ min` gate and max_contractions=5,
    # a single tight mid-series contraction (e.g. RELIANCE 10.9 → 1.6 → 8 → 4 → 4.2)
    # killed every otherwise-valid coil. Two fixes: (a) max_contractions dropped
    # to 4 above so we only compare within the active coil, (b) allow the final
    # to exceed the previous minimum by up to `tightest_tolerance` (1.15 → +15%).
    if len(depths) > 1 and depths[-1] > min(depths[:-1]) * tightest_tolerance:
        return None

    # Progressive shrinkage — allow one non-monotonic step (real charts
    # rarely produce perfectly monotone contractions) but require the trend
    # overall to point down. Rough proxy: at least 60% of consecutive pairs
    # decrease, and the linear slope of depths is negative.
    consecutive_shrinks = sum(depths[i + 1] < depths[i]
                              for i in range(len(depths) - 1))
    shrink_ratio = consecutive_shrinks / max(1, len(depths) - 1)
    x = np.arange(len(depths), dtype=float)
    slope = float(np.polyfit(x, depths, 1)[0]) if len(depths) >= 2 else 0.0
    if shrink_ratio < 0.6 or slope >= 0:
        return None

    # Depth sanity: reject "contractions" that are actually a downtrend.
    # First contraction shouldn't exceed 40% (that's a bear market base,
    # not a VCP) and the final shouldn't be zero (needs some pullback).
    if depths[0] > 40 or depths[-1] < 1.0:
        return None

    # Volume dry-up: mean of last contraction relative to mean of first,
    # scaled against the 50-DMA of volume. Full 50-DMA comparison instead of
    # just contraction-vs-contraction so we catch the case where the whole
    # base was low-volume from the start.
    off = len(df) - m
    vol50 = float(pd.Series(df["volume"].to_numpy(dtype=float))
                   .rolling(50).mean().iloc[-1])
    final_vol = contractions[-1]["avg_volume"]
    first_vol = contractions[0]["avg_volume"]
    vol_drying = bool(final_vol < first_vol) if len(contractions) >= 2 else False
    # Strict threshold from VCP.md: final contraction avg volume ≤ 80% of
    # 50-day (or ≤70% if the final contraction is >8% deep). This is what
    # separates "coiling" from "just quiet."
    strict_thresh = 0.70 if depths[-1] > 8 else 0.80
    vol_confirmed = bool(vol50 > 0 and final_vol <= vol50 * strict_thresh)

    # Pivot = the highest high across all tracked contractions. That's the
    # buy-point line — closing above it on volume expansion is the trigger.
    pivot = max(c["high_price"] for c in contractions)
    # Base low = the lowest of the leg lows (used for measured-move target).
    base_low = min(c["low_price"] for c in contractions)
    base_depth = pivot - base_low
    base_start_off = min(c["high_idx"] for c in contractions)

    # Stop = low of the FINAL contraction, per Minervini + VCPBot rules
    # (micro-pivot stop from the post-contraction window — not the prior
    # deep base low). Small ATR buffer to avoid wick-out stops.
    atr = _atr_series(df, atr_len)
    a = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0
    final_low = contractions[-1]["low_price"]
    stop = final_low - 0.5 * a

    # Verdict logic:
    #   • BUY          — last close > pivot AND today's volume ≥1.5× 50-DMA
    #   • WEAK BUY     — broke pivot but volume didn't expand
    #   • READY        — within 3% of pivot, final contraction tight (≤8%),
    #                    volume dried (≤ strict_thresh × 50-DMA)
    #   • WATCH        — pattern valid but not near pivot yet
    # Anything else has already been filtered out above.
    last_close = float(c[-1])
    last_vol = float(v[-1])
    dist_to_pivot_pct = (pivot - last_close) / pivot * 100 if pivot > 0 else 100
    vol_expansion = bool(vol50 > 0 and last_vol >= 1.5 * vol50)

    if last_close > pivot:
        verdict = "BUY" if vol_expansion else "WEAK BUY"
        entry = last_close
    elif dist_to_pivot_pct <= 3 and depths[-1] <= 8 and vol_confirmed:
        verdict = "READY"
        entry = pivot                            # trigger price
    else:
        verdict = "WATCH"
        entry = pivot

    target = pivot + base_depth
    risk = entry - stop
    reward = target - entry
    risk_reward = round(reward / risk, 2) if risk > 0 else None

    # Footprint string à la Minervini's WW notation: `depths joined by /`,
    # e.g. "28/12/6" for a 3-contraction VCP with 28% → 12% → 6% depths.
    footprint = "/".join(f"{d:.0f}" for d in depths)
    base_weeks = int(round((m - base_start_off) / 5))

    return {
        "pivot": round(pivot, 2),
        "base_low": round(base_low, 2),
        "base_start_bar_idx": int(off + base_start_off),
        "base_end_bar_idx": int(len(df) - 1),
        "contractions": [
            {"high_bar_idx":  int(off + cc["high_idx"]),
             "high_price":    round(cc["high_price"], 2),
             "low_bar_idx":   int(off + cc["low_idx"]),
             "low_price":     round(cc["low_price"], 2),
             "depth_pct":     round(cc["depth_pct"], 1),
             "in_progress":   bool(cc.get("in_progress", False))}
            for cc in contractions
        ],
        "footprint":         footprint,
        "base_weeks":        base_weeks,
        "n_contractions":    len(contractions),
        "vol_drying":        vol_drying,
        "vol_confirmed":     vol_confirmed,
        "vol_expansion":     vol_expansion,
        "dist_to_pivot_pct": round(dist_to_pivot_pct, 1),
        "verdict":           verdict,
        "entry":             round(entry, 2),
        "stop":              round(stop, 2),
        "target":            round(target, 2),
        "risk_reward":       risk_reward,
    }


def _base_quality(pivot: float, base_low: float, final_depth: float,
                  n_contractions: int, vol_confirmed: bool,
                  vol_drying: bool) -> tuple[float, float]:
    """Base-quality score (0-100) — how tight/shallow/quiet the base looks.
    Returns (base_q, base_depth_pct). Higher = cleaner, more compressed base."""
    base_depth_pct = (pivot - base_low) / pivot * 100 if pivot > 0 else 100.0
    shallow = max(0.0, min((30 - base_depth_pct) / 30, 1.0)) * 30    # shallower is better
    tight = max(0.0, min((10 - final_depth) / 10, 1.0)) * 30         # tighter final leg
    dry = 20 if vol_confirmed else (12 if vol_drying else 0)          # right-side dry-up
    struct = min(n_contractions, 4) / 4 * 20                          # well-formed coil
    return float(max(0.0, min(shallow + tight + dry + struct, 100.0))), base_depth_pct


def scan_base_formation(df: pd.DataFrame) -> dict | None:
    """Pre-breakout base screen: names building a tight base under resistance
    that pass Stage + pivot + RS + volume gates but haven't cleared the pivot
    yet. Once price clears the pivot on volume the name graduates to a breakout
    scanner (Momentum Continuation), so already-broken-out names are excluded
    here — a row means base structure was seen, not that a breakout is coming.

    Emits Base Q (0-100), VCP / Vol Dry / HTF tags, from-pivot distance and an
    RS percentile (blended into the score by run_scanner)."""
    if len(df) < 200 or "volume" not in df.columns:
        return None
    close = df["close"]
    last = float(close.iloc[-1])

    # ── Gate 1: Stage — practical Minervini trend template ──
    sma50 = _sma(close, 50)
    sma150 = _sma(close, 150)
    sma200 = _sma(close, 200)
    if any(np.isnan(v) for v in (sma50, sma150, sma200)):
        return None
    hi_52 = float(df["high"].tail(252).max())
    lo_52 = float(df["low"].tail(252).min())
    if lo_52 <= 0:
        return None
    below_high_pct = (hi_52 - last) / hi_52 * 100
    above_low_pct = (last - lo_52) / lo_52 * 100
    if not (last > sma50 and last > sma150 and sma50 > sma150 > sma200
            and below_high_pct <= 25 and above_low_pct >= 25):
        return None

    # ── Gate 2: Base structure — reuse the pivot-based VCP geometry ──
    geom = detect_vcp_geometry(df, window=120, pivot_len=3,
                               min_contractions=2, max_contractions=4)
    if not geom:
        return None
    pivot = float(geom["pivot"])
    base_low = float(geom["base_low"])
    depths = [c["depth_pct"] for c in geom["contractions"]]
    final_d = depths[-1]
    dist_to_pivot = float(geom["dist_to_pivot_pct"])     # % below pivot (≥0 while under it)

    # ── Gate 3: Pivot / near resistance — still in the base, not broken out ──
    if last > pivot:                       # cleared pivot → hands off to a breakout scan
        return None
    if not (0 <= dist_to_pivot <= 15):
        return None

    # ── Gate 4: RS — absolute floor; percentile added later by run_scanner ──
    rs_raw = _rs_raw(df)
    if rs_raw <= 0:
        return None

    # ── Gate 5: Volume — constructive dry-up on the right side of the base ──
    if not (geom["vol_drying"] or geom["vol_confirmed"]):
        return None

    base_q, base_depth_pct = _base_quality(
        pivot, base_low, final_d, geom["n_contractions"],
        geom["vol_confirmed"], geom["vol_drying"])

    vol50 = float(df["volume"].tail(50).mean())
    vol_x50 = (float(df["volume"].iloc[-1]) / vol50) if vol50 > 0 else 0.0

    # ── tags (VCP always; Vol Dry / HTF when present) ──
    filter_tags = ["VCP"]
    tags = [f"VCP {geom['footprint']}", f"{base_q:.0f} Base Q"]
    if geom["vol_confirmed"] or geom["vol_drying"]:
        filter_tags.append("Vol Dry")
        tags.append("Vol Dry")
    if len(df) >= 60:
        pole_ref = float(close.iloc[-60])
        pole_gain = (pivot / pole_ref - 1) * 100 if pole_ref > 0 else 0.0
        if pole_gain >= 80 and base_depth_pct <= 25:
            filter_tags.append("HTF")
            tags.append("HTF")

    # ── fail-risk flags (structural cautions; also lightly penalise the score) ──
    fail_risk = []
    if base_depth_pct > 25:
        fail_risk.append(f"Deep {base_depth_pct:.0f}% base — wide structure")
    if dist_to_pivot > 10:
        fail_risk.append(f"{dist_to_pivot:.0f}% below pivot — not yet actionable")
    if final_d > 8:
        fail_risk.append(f"Final contraction {final_d:.0f}% — not fully tightened")

    score_base = float(max(0.0, min(base_q - 4 * len(fail_risk), 100.0)))

    reasons = [
        f"Base under resistance — pivot {pivot:.1f}, low {base_low:.1f} "
        f"({base_depth_pct:.0f}% deep, {geom['base_weeks']}w)",
        f"VCP {geom['footprint']}% ({geom['n_contractions']} contractions), "
        f"final {final_d:.1f}% tight · {dist_to_pivot:.1f}% below pivot",
        f"Relative strength {rs_raw:+.0f}% · "
        + ("volume-confirmed dry-up" if geom["vol_confirmed"]
           else "volume drying on the right side"),
    ]

    return {
        "pattern_type": "Base Formation",
        "tags": tags,
        "filter_tags": filter_tags,
        "reasons": reasons,
        "score_base": round(score_base, 2),
        "score": round(score_base, 2),        # provisional — run_scanner blends in RS
        "rs_raw": round(rs_raw, 3),
        "base_q": round(base_q, 1),
        "vol_q": "Dry-up in base" if geom["vol_confirmed"] else "Drying",
        "vol_x50d": round(vol_x50, 2),
        "from_pivot": round(-dist_to_pivot, 2),   # negative = below pivot
        "fail_risk": fail_risk,
        "pivot": pivot,
        "base_low": base_low,
        "footprint": geom["footprint"],
    }


def scan_vcp_minervini_valchak(df: pd.DataFrame, strict: bool = False) -> dict | None:
    """Minervini VCP scanner — port of valchak's TradingView Pine v5 script
    (https://www.tradingview.com/script/XKX8RJNc-VCP-Scanner-Minervini-Method/).

    Six independent gates must all pass on the current bar:
      1. Trend Template — all 8 Minervini structural criteria
      2. VCP Valid — 2–6 tightening contractions, first 10–35%, final 3–10%,
         tightening ratio ≤ 0.9× (0.5× strict) each vs prior
      3. VDU (Volume Dry-Up) — final contraction avg vol vs 50-DMA below
         threshold (1.0 practical = off, 0.7 strict)
      4. BreakingOut — close > pivot (final contraction high)
      5. VolumeSurge — today's vol ≥ 1.4× 50-DMA
      6. NotExtended — close ≤ pivot × 1.12 (0.05 strict) — anti-chase cap

    RS Rating (7th book criterion) is NOT checked here — it requires a
    benchmark series the scanner pipeline doesn't hand us. Assume the
    universe pre-filter (`scan_stage2_uptrend` or Chartink RS filter)
    handles it upstream.

    See wiki/sources/TV-VCP-Scanner-Minervini-valchak.md for the full
    methodology and wiki/concepts/VCP.md for divergences from the book.
    """
    if len(df) < 260 or "volume" not in df.columns:
        return None
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    last = float(close.iloc[-1])

    # ── Gate 1: Trend Template (all 8) ─────────────────────────────────────
    sma50 = _sma(close, 50)
    sma150 = _sma(close, 150)
    sma200 = _sma(close, 200)
    sma200_prev = _sma(close.iloc[:-22], 200) if len(df) >= 222 else float("nan")
    if any(np.isnan(v) for v in [sma50, sma150, sma200, sma200_prev]):
        return None
    hi_52w = float(high.tail(252).max())
    lo_52w = float(low.tail(252).min())
    if lo_52w <= 0:
        return None
    above_low_pct = (last - lo_52w) / lo_52w * 100
    below_high_pct = (hi_52w - last) / hi_52w * 100
    min_above_low = 30.0 if strict else 25.0

    tt_checks = {
        "Price > SMA150 & SMA200": last > sma150 and last > sma200,
        "SMA150 > SMA200": sma150 > sma200,
        "SMA200 rising ≥22 bars": sma200 > sma200_prev,
        "SMA50 > SMA150 > SMA200": sma50 > sma150 > sma200,
        "Price > SMA50": last > sma50,
        f"≥{min_above_low:.0f}% above 52w low": above_low_pct >= min_above_low,
        "Within 25% of 52w high": below_high_pct <= 25.0,
    }
    if not all(tt_checks.values()):
        return None

    # ── Gate 2: VCP Valid — reuse detect_vcp_geometry, layer valchak's ranges
    pivot_len = 5 if strict else 3
    geom = detect_vcp_geometry(
        df, window=180, pivot_len=pivot_len,
        min_contractions=2, max_contractions=6,
    )
    if not geom:
        return None
    depths = [c["depth_pct"] for c in geom["contractions"]]
    first_d = depths[0]
    final_d = depths[-1]
    if not (10.0 <= first_d <= 35.0):
        return None
    if not (3.0 <= final_d <= 10.0):
        return None
    tight_ratio_cap = 0.5 if strict else 0.9
    tighten_ok = all(depths[i + 1] <= depths[i] * tight_ratio_cap
                     for i in range(len(depths) - 1))
    if not tighten_ok:
        return None
    base_bars = geom["base_end_bar_idx"] - geom["base_start_bar_idx"]
    if not (15 <= base_bars <= 325):
        return None

    pivot = float(geom["pivot"])

    # ── Gate 3: VDU (only enforced in strict mode; off by default like valchak)
    vol50 = float(volume.tail(50).mean())
    if strict and vol50 > 0:
        vdu_ratio = geom.get("dist_to_pivot_pct")  # unused; use vol_confirmed
        if not geom.get("vol_confirmed"):
            return None

    # ── Gate 4: BreakingOut — close > pivot
    if last <= pivot:
        return None

    # ── Gate 5: VolumeSurge — today's vol ≥ 1.4× 50-DMA
    vol_today = float(volume.iloc[-1])
    vol_mult = vol_today / vol50 if vol50 > 0 else 0.0
    if vol_mult < 1.4:
        return None

    # ── Gate 6: NotExtended — close ≤ pivot × (1 + max_ext)
    max_ext_pct = 5.0 if strict else 12.0
    ext_above_pivot_pct = (last - pivot) / pivot * 100 if pivot > 0 else 0.0
    if ext_above_pivot_pct > max_ext_pct:
        return None

    footprint = geom["footprint"]
    tags = [
        "Trend Template ✓",
        f"VCP {footprint}",
        f"Vol {vol_mult:.1f}×",
        "Strict" if strict else "Practical",
    ]
    reasons = [
        f"All 8 Trend Template criteria passed (above/below levels, MA stack, 52w low/high bands, SMA200 rising)",
        f"VCP: {len(depths)} contractions, footprint {footprint}%, base {base_bars} bars",
        f"First {first_d:.1f}% → Final {final_d:.1f}% (tightening ≤{tight_ratio_cap:.1f}× each step)",
        f"Breakout: close {last:.2f} > pivot {pivot:.2f} on {vol_mult:.1f}× 50-DMA volume",
        f"Not extended: only {ext_above_pivot_pct:.1f}% above pivot (cap {max_ext_pct:.0f}%)",
    ]
    # Score: composite of tightness (final depth), volume surge, and how
    # close to pivot (lower extension = better entry).
    score = round(
        (10 - final_d) * 3         # tightness (max ~21 for a 3% final)
        + min(vol_mult, 3.0) * 5   # volume surge, cap at 3× (max 15)
        + (max_ext_pct - ext_above_pivot_pct) * 1.5,  # freshness (max ~18)
        2,
    )
    return {
        "pattern_type": "Minervini VCP (valchak)",
        "tags": tags,
        "reasons": reasons,
        "score": score,
        "pivot": pivot,
        "stop": geom["stop"],
        "target": geom["target"],
        "footprint": footprint,
        "contractions": depths,
    }


def scan_near_pivot(df: pd.DataFrame) -> dict | None:
    """Within 3% of the most recent swing-high pivot (higher than both neighbors)."""
    if len(df) < 40:
        return None
    last = float(df["close"].iloc[-1])
    sma50 = _sma(df["close"], 50)
    if not np.isnan(sma50) and last < sma50 * 0.97:
        return None
    highs = df["high"].tail(60).values
    pivot = None
    for i in range(len(highs) - 2, 1, -1):
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            pivot = highs[i]
            break
    if pivot is None:
        return None
    pct = abs(last - pivot) / pivot * 100
    if pct > 3:
        return None
    direction = "approaching from below" if last < pivot else "just broke above"
    reasons = [
        f"Price {direction} pivot at {pivot:.0f} ({pct:.1f}% away)",
        "Tight stop available at pivot — favorable risk/reward",
    ]
    return {
        "pattern_type": "Near Pivot",
        "tags": [f"{pct:.1f}% from pivot", "Pivot zone"],
        "reasons": reasons,
        "score": round(3 - pct, 2),
    }


def scan_downside_risk(df: pd.DataFrame) -> dict | None:
    """Below SMA50 with above-average volume on down days — distribution pattern."""
    if len(df) < 60:
        return None
    close = df["close"]
    last = float(close.iloc[-1])
    sma50 = _sma(close, 50)
    sma200 = _sma(close, 200)
    if np.isnan(sma50) or last > sma50:
        return None
    reasons = [f"Price ({last:.0f}) below SMA50 ({sma50:.0f}) — bearish MA break"]
    if not np.isnan(sma200) and last < sma200:
        reasons.append(f"Also below SMA200 ({sma200:.0f}) — potential Stage 4 decline")
    vol_avg = float(df["volume"].tail(20).mean())
    dist_days = sum(
        1 for _, row in df.tail(10).iterrows()
        if float(row["close"]) < float(row["open"]) and float(row["volume"]) > vol_avg
    )
    if dist_days >= 2:
        reasons.append(f"{dist_days} distribution days in last 10 sessions — selling pressure")
    return {
        "pattern_type": "Downside Risk",
        "tags": ["Below SMA50", "Distribution"],
        "reasons": reasons,
        "score": round((sma50 - last) / sma50 * 100, 2),
    }


def scan_6m_consolidation_breakout(df: pd.DataFrame) -> dict | None:
    """Chartink-style: price breaks above 6-month high after consolidation.

    Conditions (mirrors the Chartink screener exactly):
      1. Daily Close > EMA(Close, 50)           — trend filter
      2. Daily Close > 126-day Max(Daily High)  — fresh 6-month breakout
      3. 126-day Min(Low) < 1-day-ago Max(126, High)  — prior range had ceiling
         i.e. the stock was range-bound for 6 months before today's breakout
      4. Daily Volume > 200,000                 — liquidity gate
    """
    if len(df) < 130:
        return None

    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]

    last_close  = float(close.iloc[-1])
    last_volume = float(volume.iloc[-1])

    # Condition 4 — liquidity
    if last_volume < 200_000:
        return None

    # Condition 1 — price above 50 EMA
    ema50 = float(_ema_series(close, 50).iloc[-1])
    if last_close <= ema50:
        return None

    # Condition 2 — today's close > 126-day high (breakout)
    # Use iloc[-127:-1] as "previous 126 sessions" so today isn't self-referencing
    prior_126_high = float(high.iloc[-127:-1].max())
    if last_close <= prior_126_high:
        return None

    # Condition 3 — consolidation proof: 6-month range was tight enough.
    # The stock was trapped below that ceiling (min-low < prior ceiling means
    # it has been ranging, not trending up the whole time).
    prior_126_low = float(low.iloc[-127:-1].min())
    consolidation_pct = (prior_126_high - prior_126_low) / prior_126_low * 100
    # Reject if it was already in a strong uptrend (range > 40% = not consolidating)
    if consolidation_pct > 40:
        return None

    # Volume confirmation — today should be above 20-day avg
    vol_avg_20 = float(volume.tail(20).mean())
    vol_ratio  = last_volume / vol_avg_20 if vol_avg_20 > 0 else 1.0

    reasons = [
        f"Price ({last_close:.2f}) broke above 6-month high ({prior_126_high:.2f}) — fresh breakout",
        f"Prior 6-month range: {prior_126_low:.2f}–{prior_126_high:.2f} "
        f"({consolidation_pct:.1f}% wide) — genuine consolidation",
        f"Holding above EMA50 ({ema50:.2f}) — trend is supportive",
        f"Volume {last_volume:,.0f} (>{200_000:,} filter)" +
        (f", {vol_ratio:.1f}× 20-day avg — breakout confirmed" if vol_ratio >= 1.5
         else f", {vol_ratio:.1f}× 20-day avg"),
    ]

    # Score: higher breakout volume + tighter prior range = better quality
    score = round(vol_ratio * 3 + (40 - consolidation_pct) / 4, 2)

    return {
        "pattern_type": "6-Month Consolidation Breakout",
        "tags": [
            f"Broke {prior_126_high:.0f}",
            f"{consolidation_pct:.0f}% range",
            f"{vol_ratio:.1f}× vol",
        ],
        "reasons": reasons,
        "score": score,
    }


def _consolidation_breakout(
    df: pd.DataFrame,
    lookback: int,
    label: str,
    max_range_pct: float,
    min_volume: int = 200_000,
) -> dict | None:
    """Generic multi-timeframe consolidation-breakout engine.

    Args:
        lookback:      Number of trading sessions to look back (252=1Y, 1260=5Y, 2520=10Y).
        label:         Human-readable period label shown in card text.
        max_range_pct: Reject if prior range was wider than this % (prevents trending stocks
                       being flagged as 'consolidating').
        min_volume:    Minimum last-session volume for liquidity gate.
    """
    if len(df) < lookback + 5:
        return None

    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]

    last_close  = float(close.iloc[-1])
    last_volume = float(volume.iloc[-1])

    if last_volume < min_volume:
        return None

    ema50 = float(_ema_series(close, 50).iloc[-1])
    if last_close <= ema50:
        return None

    # Prior period excludes today so breakout is truly "new"
    prior_high = float(high.iloc[-(lookback + 1):-1].max())
    prior_low  = float(low.iloc[-(lookback + 1):-1].min())

    if last_close <= prior_high:
        return None

    if prior_low <= 0 or prior_high == prior_low:
        return None

    range_pct = (prior_high - prior_low) / prior_low * 100
    if range_pct > max_range_pct:
        return None

    vol_avg_20 = float(volume.tail(20).mean())
    vol_ratio  = last_volume / vol_avg_20 if vol_avg_20 > 0 else 1.0

    breakout_pct = (last_close - prior_high) / prior_high * 100

    reasons = [
        f"Price ({last_close:.2f}) broke above {label} high ({prior_high:.2f})"
        f" — +{breakout_pct:.1f}% above breakout level",
        f"{label} range: {prior_low:.2f}–{prior_high:.2f} ({range_pct:.1f}% wide)"
        f" — stock was consolidating",
        f"Holding above EMA50 ({ema50:.2f}) — trend filter passed",
        f"Volume {last_volume:,.0f} ({vol_ratio:.1f}× 20-day avg)"
        + (" — breakout confirmed" if vol_ratio >= 1.5 else ""),
    ]

    score = round(vol_ratio * 3 + (max_range_pct - range_pct) / 5, 2)

    return {
        "pattern_type": f"{label} Consolidation Breakout",
        "tags": [
            f"Broke {prior_high:.0f}",
            f"{range_pct:.0f}% range",
            f"{vol_ratio:.1f}× vol",
        ],
        "reasons": reasons,
        "score": score,
    }


def scan_1y_breakout(df: pd.DataFrame) -> dict | None:
    """1-year high breakout after ≤50% consolidation range, EMA50 filter, Vol>2L."""
    return _consolidation_breakout(df, lookback=252, label="1-Year", max_range_pct=50)


def scan_5y_breakout(df: pd.DataFrame) -> dict | None:
    """5-year high breakout after ≤80% consolidation range, EMA50 filter, Vol>2L."""
    return _consolidation_breakout(df, lookback=1260, label="5-Year", max_range_pct=80)


def scan_10y_breakout(df: pd.DataFrame) -> dict | None:
    """10-year / all-time high breakout, EMA50 filter, Vol>2L — generational move."""
    return _consolidation_breakout(df, lookback=2520, label="10-Year", max_range_pct=200)


def scan_high_tight_flag(df: pd.DataFrame, min_pole_pct: float = 90.0,
                         max_pole_bars: int = 40, min_flag_bars: int = 5,
                         max_flag_bars: int = 25,
                         max_flag_depth_pct: float = 25.0) -> dict | None:
    """High Tight Flag (SwingEdge Momentum Buildup ingest — see
    concepts/High-Tight-Flag.md): a ~doubling pole (>=90%) within ~8 weeks,
    then a tight flag correcting <=25% on contracting volume. A flag on
    rising volume is distribution into strength, so it's rejected outright.
    Scores higher for a stronger pole, tighter flag, harder volume dry-up,
    and proximity to (or a fresh clear of) the flag high.
    """
    if len(df) < max_pole_bars + max_flag_bars + 10:
        return None
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    n = len(df)

    flag_zone = h[-(max_flag_bars + 1):]
    p = n - len(flag_zone) + int(flag_zone.argmax())      # pole-high bar
    flag_len = n - 1 - p
    if flag_len < min_flag_bars:
        return None

    pole_high = float(h[p])
    pole_start = max(0, p - max_pole_bars)
    pole_low_idx = pole_start + int(l[pole_start:p + 1].argmin())
    pole_low = float(l[pole_low_idx])
    if pole_low <= 0:
        return None
    pole_bars = p - pole_low_idx
    pole_pct = (pole_high - pole_low) / pole_low * 100
    if pole_pct < min_pole_pct:
        return None

    flag_low = float(l[p + 1:].min())
    depth = (pole_high - flag_low) / pole_high * 100
    if depth > max_flag_depth_pct:
        return None

    if "volume" not in df.columns:
        return None
    pole_vol = float(df["volume"].iloc[pole_start:p + 1].mean())
    flag_vol = float(df["volume"].iloc[p + 1:].mean())
    if not pole_vol > 0 or flag_vol >= pole_vol:
        return None

    last_close = float(c[-1])
    breakout = last_close > pole_high
    near_pivot = last_close >= pole_high * 0.95
    dry_up = 1 - flag_vol / pole_vol

    score = 50.0
    score += min(15.0, (pole_pct - min_pole_pct) / 30 * 15)          # 90→120%+
    score += (max_flag_depth_pct - depth) / max_flag_depth_pct * 20  # tightness
    score += dry_up * 10
    score += 10 if breakout else (5 if near_pivot else 0)
    score = round(min(100.0, score), 1)

    status = ("Breaking out of flag" if breakout
              else "Within 5% of flag high" if near_pivot
              else "Flag forming")
    tags = [f"{pole_pct:.0f}% pole", f"{depth:.0f}% flag", f"{flag_len}d flag"]
    if breakout:
        tags.append("Breakout")
    reasons = [
        f"Pole: +{pole_pct:.0f}% into {pole_high:.2f} within {pole_bars} bars",
        f"Flag: {depth:.1f}% deep over {flag_len} bars — inside the 10–25% HTF band",
        f"Flag volume {flag_vol / pole_vol:.0%} of pole volume — supply drying up",
        status,
    ]
    return {"pattern_type": "High Tight Flag", "tags": tags,
            "reasons": reasons, "score": score}


def scan_structural_breakout(df: pd.DataFrame, lookback: int = 120,
                             cluster_tol_pct: float = 1.5, min_touches: int = 4,
                             min_base_bars: int = 20,
                             atr_len: int = 14) -> dict | None:
    """Structural Breakout (SwingEdge ingest — see sources/SwingEdge-
    Structural-Breakout-Screener-20260703.md): multi-week horizontal
    resistance cluster (daily highs within ~1.5% of the ceiling, >=4
    touches), ATR(14)-scaled break buffer, three lifecycle states
    (Approaching / Confirmed break / Retest hold) with an anti-chase
    extension cap, base-compression + breakout-volume + weekly-confirm
    scoring, and the page's own score floors (72 confirmed/retest, 65
    approaching). Flat Base vs Neckline Reversal classified from the
    pre-base trend (>=15% run-up in vs >=15% decline in).
    """
    if len(df) < min_base_bars + 30 or "volume" not in df.columns:
        return None
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    v = df["volume"].to_numpy(dtype=float)
    n = len(df)
    w0 = max(0, n - lookback)

    ceil_end = n - 3                      # ceiling must pre-exist the break
    if ceil_end - w0 < min_base_bars:
        return None
    level = float(h[w0:ceil_end].max())
    tol = cluster_tol_pct / 100
    touch_idx = [i for i in range(w0, ceil_end) if h[i] >= level * (1 - tol)]
    touches = len(touch_idx)
    if touches < min_touches:
        return None

    base_start = touch_idx[0]
    base_bars = n - base_start
    if base_bars < min_base_bars:
        return None

    atr = _atr_series(df, atr_len)
    a = float(atr.iloc[-1])
    if pd.isna(a) or a <= 0:
        return None
    buffer = 0.25 * a
    last_close = float(c[-1])

    cross = None                          # last close-cross above level+buffer
    for i in range(max(base_start, n - 15), n):
        if c[i] > level + buffer and (i == 0 or c[i - 1] <= level + buffer):
            cross = i

    vol50 = pd.Series(v).rolling(50).mean()
    if last_close > level + buffer:
        if cross is None or last_close > level + 4 * a:
            return None                   # extended past the anti-chase cap
        since = n - 1 - cross
        retested = float(l[cross:].min()) <= level * (1 + tol)
        state = ("Confirmed break" if since <= 3
                 else "Retest hold" if retested else "Confirmed break")
        v50 = float(vol50.iloc[cross]) if not pd.isna(vol50.iloc[cross]) else 0.0
        vol_confirmed = v50 > 0 and float(v[cross]) >= 1.3 * v50
    elif level - 1.5 * a <= last_close <= level:
        state, vol_confirmed = "Approaching", False
    else:
        return None

    third = max(5, base_bars // 3)
    early_rng = (float(h[base_start:base_start + third].max())
                 - float(l[base_start:base_start + third].min())) / level
    late_rng = (float(h[n - third:].max()) - float(l[n - third:].min())) / level
    compression = late_rng / early_rng if early_rng > 0 else 1.0
    base_vol_drying = float(v[n - third:].mean()) < float(v[base_start:base_start + third].mean())

    ref = max(0, base_start - 60)
    pre_ret = (c[base_start] - c[ref]) / c[ref] if c[ref] > 0 else 0.0
    family = ("Neckline Reversal" if pre_ret <= -0.15
              else "Flat Base" if pre_ret >= 0.15 else "Structural Base")

    weekly_ok = False
    if isinstance(df.index, pd.DatetimeIndex):
        wk_close = df["close"].resample("W-FRI").last().dropna()
        weekly_ok = len(wk_close) > 0 and float(wk_close.iloc[-1]) > level

    score = 55.0
    score += min(15, touches)
    score += 8 if compression <= 0.7 else 4 if compression <= 0.9 else 0
    score += 8 if vol_confirmed else 0
    score += 6 if base_vol_drying else 0
    score += 5 if weekly_ok else 0
    score += 3 if state != "Approaching" else 0
    score = round(min(100.0, score), 1)

    floor = 65 if state == "Approaching" else 72
    if score < floor:
        return None

    base_weeks = base_bars // 5
    tags = [family, state, f"{base_weeks}w base", f"{touches} touches"]
    if weekly_ok:
        tags.append("Weekly ✓")
    reasons = [
        f"Resistance cluster {level:.2f} — {touches} touches within {cluster_tol_pct}%",
        f"{base_weeks}-week base ({family.lower()}, pre-base move {pre_ret * 100:+.0f}%)",
        f"Late-base range {compression:.0%} of early-base range"
        + (", volume drying up" if base_vol_drying else ""),
        state + (f" — cleared level + 0.25×ATR buffer on {v[cross] / max(float(vol50.iloc[cross]), 1.0):.1f}× 50d volume"
                 if state != "Approaching" and vol_confirmed else ""),
    ]
    if weekly_ok:
        reasons.append("Weekly close also above the resistance zone (weekly confirm)")
    return {"pattern_type": "Structural Breakout", "tags": tags,
            "reasons": reasons, "score": score}


def scan_rounding_bottom(df: pd.DataFrame, window: int = 90,
                         min_decline_pct: float = 12.0,
                         max_decline_pct: float = 40.0,
                         atr_len: int = 14) -> dict | None:
    """Rounding Bottom / saucer (SwingEdge ingest — see sources/SwingEdge-
    Rounding-Bottom-Screener-20260703.md): smooth U mapped with swing
    structure and *linear slope stats*, not curve fitting. Gates: 12-40%
    left-side decline off the rim, orderly legs (decent linear fit on both
    sides), EMA-21 slope flat/down at the trough and turning up on the
    right. States mirror the board: Approaching rim (within 3%), Confirmed
    (close above rim on 1.3x+ 50d volume, recent), Retest hold. Families:
    Classic Reversal (trough under a falling 200-DMA) vs Constructive Base
    (repairing near/above a rising one). Score floors 70 confirmed/retest,
    65 approaching, per the page.
    """
    if len(df) < window // 2 or "volume" not in df.columns:
        return None
    w = df.tail(window)
    m = len(w)
    h = w["high"].to_numpy(dtype=float)
    l = w["low"].to_numpy(dtype=float)
    c = w["close"].to_numpy(dtype=float)
    v = w["volume"].to_numpy(dtype=float)

    t = int(l.argmin())                       # trough bar
    if t < 10 or m - 1 - t < 6:
        return None                           # need both saucer legs

    rim = float(h[:t].max())                  # left lip = pre-decline high
    trough_low = float(l[t])
    if rim <= 0:
        return None
    decline = (rim - trough_low) / rim * 100
    if not min_decline_pct <= decline <= max_decline_pct:
        return None

    def _linfit_r2(y: np.ndarray) -> tuple[float, float]:
        x = np.arange(len(y), dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        pred = slope * x + intercept
        ss_res = float(((y - pred) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return float(slope), r2

    slope_l, r2_l = _linfit_r2(c[:t + 1])
    slope_r, r2_r = _linfit_r2(c[t:])
    if slope_l >= 0 or slope_r <= 0:
        return None                           # legs must actually decline/recover
    orderly = r2_l >= 0.45 and r2_r >= 0.45   # whipsaw saucers score down/fail
    if r2_l < 0.25 or r2_r < 0.25:
        return None

    symmetry = min(t, m - 1 - t) / max(t, m - 1 - t)
    if symmetry < 0.25:
        return None       # extreme asymmetry = V-bottom, not a saucer
    trough_days = int((l <= trough_low * 1.03).sum())   # flat-bottom width

    ema21 = _ema_series(df["close"], 21).to_numpy(dtype=float)
    off = len(df) - m
    e_now = ema21[-1] - ema21[-4]
    e_trough = ema21[off + t] - ema21[max(0, off + t - 3)]
    ema_turn = bool(e_now > 0 and e_trough <= 0)

    family = "Saucer"
    if len(df) >= 220:
        sma200 = df["close"].rolling(200).mean().to_numpy(dtype=float)
        rising = sma200[-1] > sma200[-21]
        family = ("Constructive Base"
                  if rising and float(df["close"].iloc[-1]) >= sma200[-1] * 0.98
                  else "Classic Reversal")

    atr = _atr_series(df, atr_len)
    a = float(atr.iloc[-1])
    if pd.isna(a) or a <= 0:
        return None
    last_close = float(df["close"].iloc[-1])
    vol50 = pd.Series(df["volume"].to_numpy(dtype=float)).rolling(50).mean()

    cross = None
    for i in range(max(1, m - 10), m):
        if c[i] > rim and c[i - 1] <= rim:
            cross = i
    if last_close > rim:
        if cross is None or last_close > rim + 4 * a:
            return None                       # extended past the rim — chase
        since = m - 1 - cross
        state = "Confirmed" if since <= 3 else "Retest hold"
        gi = off + cross
        v50 = float(vol50.iloc[gi]) if not pd.isna(vol50.iloc[gi]) else 0.0
        vol_confirmed = v50 > 0 and float(v[cross]) >= 1.3 * v50
        rim_dist = 0.0
    elif last_close >= rim * 0.97:
        state, vol_confirmed = "Approaching rim", False
        rim_dist = (rim - last_close) / rim * 100
    else:
        return None

    score = 55.0
    score += 10 if orderly else 4
    score += 8 * symmetry
    score += 6 if ema_turn else 0
    score += 8 if vol_confirmed else 0
    score += 4 if family == "Constructive Base" else 2
    score = round(min(100.0, score), 1)
    if score < (65 if state == "Approaching rim" else 70):
        return None

    tags = [family, state, f"{trough_days}d trough"]
    if ema_turn:
        tags.append("EMA turn")
    reasons = [
        f"Saucer: {decline:.1f}% decline off rim {rim:.2f}, "
        f"legs {t}/{m - 1 - t} bars (symmetry {symmetry:.0%})",
        f"Orderly legs — linear fit R² {r2_l:.2f} left / {r2_r:.2f} right"
        if orderly else f"Legs loosely fit (R² {r2_l:.2f}/{r2_r:.2f}) — scored down",
    ]
    if ema_turn:
        reasons.append("EMA-21 slope flat/down at trough, turning upward on the right side")
    if state == "Approaching rim":
        reasons.append(f"Within {rim_dist:.1f}% of rim — no confirmed clear yet")
    else:
        reasons.append(state + (" — rim cleared on ≥1.3× 50d volume" if vol_confirmed
                                else " — rim cleared on light volume (scored down)"))
    # Actionable trade plan derived directly from the saucer geometry. The
    # verdict/entry/stop/target logic lives HERE (not in the chart_server or
    # in the JS) so the Scanner Hub card, the chart overlay, and any future
    # dashboard consumer all see identical numbers.
    #   • Retest hold     — strongest: rim already cleared AND holding above
    #                        on pullback. Entry at last close, tight stop just
    #                        under the reclaimed rim.
    #   • Confirmed break — buy the fresh clear. If cleared on ≥1.3× 50-day
    #                        volume, verdict = BUY; otherwise WEAK BUY (real
    #                        break but no institutional participation yet).
    #   • Approaching rim — WATCH only: no entry until the buffer-close above
    #                        rim happens. Levels shown are what the trade
    #                        WOULD be if the break confirms.
    # Stop candidates:
    #   • stop_flip   = rim × 0.97 (broken level flip zone — tight)
    #   • stop_leg    = min of the last 15 bars − 0.5×ATR (right-leg low
    #                    invalidation — tighter than the pattern trough
    #                    once the right leg is well underway, and the
    #                    honest "if we're wrong we shouldn't come back
    #                    here" level for an Approaching rim setup)
    #   • stop_trough = trough_low − 0.5×ATR (pattern-low invalidation —
    #                    widest, only relevant as a backstop)
    # Target = rim + (rim − trough_low): classic measured-move projection.
    pattern_height = rim - trough_low
    right_leg_len = min(15, m - 1 - t)
    stop_leg  = float(l[-right_leg_len:].min()) - 0.5 * a if right_leg_len > 0 else trough_low
    stop_flip = rim * 0.97
    stop_trough = trough_low - 0.5 * a
    if state == "Retest hold":
        verdict = "BUY (retest hold)"
        entry = last_close
        stop  = max(stop_flip, stop_leg)         # tightest reasonable
        target = rim + pattern_height
    elif state == "Confirmed":
        verdict = "BUY" if vol_confirmed else "WEAK BUY"
        entry = last_close
        stop  = max(stop_flip, stop_leg)
        target = rim + pattern_height
    else:                                        # Approaching rim
        verdict = "WATCH"
        entry = rim                              # buy the break, not the run-up
        # Use the tighter of the right-leg low and the pattern trough as the
        # WATCH stop — trough is the theoretical worst case but the recent
        # leg-low is the actual "if we're wrong" level when the right leg
        # has been holding above it for a while.
        stop  = max(stop_leg, stop_trough)
        target = rim + pattern_height
    reward = target - entry
    risk = entry - stop
    risk_reward = round(reward / risk, 2) if risk > 0 else None

    # Geometry payload: bar indices into df (0-based, absolute), NOT into the
    # trailing window w. The chart_server endpoint converts these to unix
    # timestamps via the OHLCV list it already has. Scanner Hub ignores the
    # `geometry` key so this stays backward-compatible with existing callers.
    geometry = {
        "rim": round(rim, 2),
        "trough_bar_idx": int(off + t),
        "trough_price": round(trough_low, 2),
        "base_start_bar_idx": int(off),
        "breakout_bar_idx": int(off + cross) if cross is not None else None,
        "state": state,
        "family": family,
        "decline_pct": round(decline, 1),
        "symmetry_pct": int(round(symmetry * 100)),
        "trough_days": trough_days,
        "ema_turn": ema_turn,
        "vol_confirmed": vol_confirmed if state != "Approaching rim" else None,
        "score": score,
        # Actionable trade plan
        "verdict": verdict,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk_reward": risk_reward,
    }
    return {"pattern_type": "Rounding Bottom", "tags": tags,
            "reasons": reasons, "score": score, "geometry": geometry}


def compute_pre_breakout_conviction(df: pd.DataFrame) -> dict | None:
    """Score (0-100) how convincing a 1-2 day pre-breakout setup is.

    Chartink's "Pre-Breakout Setup" scan only filters the boolean gates
    (below-but-near a 20-day high, RSI band, EMA50, volume-dry-up); this
    turns that into a graded score across four equally-weighted signals so
    the caller can keep only score >= 60:
      1. Proximity to the breakout trigger (20-day high)   — up to 25 pts
      2. Volatility contraction (10d range vs prior 10d)    — up to 25 pts
      3. RSI sitting in the constructive pre-breakout band   — up to 25 pts
      4. Trend support (above EMA50) + volume drying up      — up to 25 pts
    """
    if len(df) < 40:
        return None

    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]
    last = float(close.iloc[-1])

    # 1 — proximity to the trigger level
    trigger = float(high.iloc[-21:-1].max())
    if trigger <= 0:
        return None
    dist_pct = (trigger - last) / trigger * 100
    if dist_pct < 0 or dist_pct > 10:
        return None  # already broke out, or too far away to call this "imminent"
    prox_score = max(0.0, 25 - dist_pct * 25 / 10)

    # 2 — volatility contraction vs the prior 10-day window
    def _range_pct(window: pd.DataFrame) -> float:
        lo, hi = float(window["low"].min()), float(window["high"].max())
        return (hi - lo) / lo * 100 if lo > 0 else 0.0

    r_recent = _range_pct(df.tail(10))
    r_prior = _range_pct(df.iloc[-20:-10])
    contraction = (r_prior - r_recent) / r_prior * 100 if r_prior > 0 else 0.0
    contract_score = max(0.0, min(25.0, contraction * 25 / 40))

    # 3 — RSI(14) in the constructive band
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_val = (100 - 100 / (1 + rs)).iloc[-1]
    rsi = float(rsi_val) if not pd.isna(rsi_val) else None
    if rsi is None:
        rsi_score = 0.0
    elif 50 <= rsi <= 65:
        rsi_score = 25.0
    elif 40 <= rsi < 50 or 65 < rsi <= 72:
        rsi_score = 15.0
    else:
        rsi_score = 0.0

    # 4 — trend support + volume dry-up in the base
    ema50 = float(_ema_series(close, 50).iloc[-1])
    trend_ok = last > ema50
    vol_avg20 = float(volume.tail(20).mean())
    vol_last = float(volume.iloc[-1])
    dryup = vol_avg20 > 0 and vol_last < vol_avg20
    vol_score = (15.0 if trend_ok else 0.0) + (10.0 if dryup else 0.0)

    conviction = round(prox_score + contract_score + rsi_score + vol_score, 1)

    reasons = [
        f"{dist_pct:.1f}% below the 20-day high ({trigger:.2f}) — trigger within reach",
        f"Range contracted {contraction:.0f}% vs the prior 10 sessions"
        if contraction > 0 else "Range not yet contracting",
        f"RSI {rsi:.0f}" if rsi is not None else "RSI unavailable",
        ("Above" if trend_ok else "Below") + f" rising EMA50 ({ema50:.2f})"
        + (", volume drying up in the base" if dryup else ""),
    ]

    return {
        "conviction": conviction,
        "trigger_level": round(trigger, 2),
        "distance_pct": round(dist_pct, 2),
        "rsi": round(rsi, 1) if rsi is not None else None,
        "reasons": reasons,
    }


def compute_ibd_rs_blend(df: pd.DataFrame) -> float | None:
    """IBD-style blended return: 40% 3mo + 20% 6mo + 20% 9mo + 20% 12mo.

    This is the raw blended-return number, not the final 1-99 RS Rating —
    IBD's rating is this same blend percentile-ranked across the *entire*
    market. Percentile-ranking against thousands of stocks isn't practical
    here, so the caller percentile-ranks this value within whatever batch of
    stocks it just screened (a relative comparison within that batch, not a
    market-wide rating).
    """
    close = df["close"]

    def _ret(days: int) -> float | None:
        if len(close) <= days:
            return None
        prev = float(close.iloc[-1 - days])
        return (float(close.iloc[-1]) / prev - 1) if prev > 0 else None

    r3, r6, r9, r12 = _ret(63), _ret(126), _ret(189), _ret(252)
    if any(r is None for r in (r3, r6, r9, r12)):
        return None
    return 0.4 * r3 + 0.2 * r6 + 0.2 * r9 + 0.2 * r12


def compute_recent_exhaustion_signal(df: pd.DataFrame, lookback: int = 3) -> str | None:
    """Port of the %R Trend Exhaustion indicator (see
    percent_r_trend_exhaustion.js — same fast/slow Williams %R + EMA
    smoothing + overbought/oversold zone logic) for bulk Python screening.

    Returns "bullish" if a bullish exhaustion (price just left the oversold
    zone) fired within the last `lookback` bars, "bearish" for the oversold
    equivalent, or None if neither fired recently.
    """
    fast_len, fast_smooth = 21, 7
    slow_len, slow_smooth = 112, 3
    threshold = 20
    if len(df) < slow_len + slow_smooth + lookback + 5:
        return None

    high, low, close = df["high"], df["low"], df["close"]

    def _percent_r(length: int) -> pd.Series:
        hh = high.rolling(length).max()
        ll = low.rolling(length).min()
        rng = hh - ll
        return ((close - hh) / rng.replace(0, np.nan) * 100).fillna(0.0)

    fast = _ema_series(_percent_r(fast_len), fast_smooth)
    slow = _ema_series(_percent_r(slow_len), slow_smooth)

    overbought = (fast >= -threshold) & (slow >= -threshold)
    oversold = (fast <= -(100 - threshold)) & (slow <= -(100 - threshold))
    ob_reversal = (~overbought) & overbought.shift(1).fillna(False)   # bearish
    os_reversal = (~oversold) & oversold.shift(1).fillna(False)       # bullish

    recent_bull = bool(os_reversal.tail(lookback).any())
    recent_bear = bool(ob_reversal.tail(lookback).any())
    if recent_bull and not recent_bear:
        return "bullish"
    if recent_bear and not recent_bull:
        return "bearish"
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Early Reversal Detector — combines 4 independently-sourced reversal signals
# ingested into trading-wiki this session (see wiki/strategies/Drop-Recovery-
# Reversal-Screen.md, wiki/concepts/Percent-R-Trend-Exhaustion.md,
# wiki/strategies/Candlestick-Filtering.md, wiki/concepts/Reversal-Chart-Patterns.md).
#
# Design note: deliberately does NOT require a strict prior downtrend. Watching
# the Forthius Reversal Scanner run live on a real chart showed its own default
# config goes quiet exactly at the Stage 4->1->2 transition it's meant to catch,
# because its bullish patterns require an active downtrend rather than treating
# "ranging after a decline" as valid context. The drop-recovery gate below
# already proves a real decline happened — nothing here re-requires the stock
# still be trending down.
# ──────────────────────────────────────────────────────────────────────────────

def compute_drop_recovery_signal(
    df: pd.DataFrame,
    high_lookback: int = 20,
    min_drop_pct: float = 5.0,
    min_recovery_pct: float = 40.0,
) -> dict | None:
    """Drop-then-recover magnitude gate (see Drop-Recovery-Reversal-Screen).

    Fixes the source script's likely highBeforeLow bug (its period-boundary
    loop appeared to collapse to just the prior bar's close/open on both
    timeframes it supports) by using an actual N-day rolling high instead.
    """
    if len(df) < high_lookback + 5:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    recent_high = float(high.iloc[-high_lookback:-1].max())
    recent_low = float(low.iloc[-high_lookback:].min())
    if recent_high <= 0 or recent_low >= recent_high:
        return None

    drop_pct = (recent_high - recent_low) / recent_high * 100
    if drop_pct < min_drop_pct:
        return None

    drop_amt = recent_high - recent_low
    last_close = float(close.iloc[-1])
    recovery_pct = (last_close - recent_low) / drop_amt * 100 if drop_amt > 0 else 0.0
    if recovery_pct < min_recovery_pct:
        return None

    return {
        "drop_pct": round(drop_pct, 1),
        "recovery_pct": round(recovery_pct, 1),
        "recent_high": round(recent_high, 2),
        "recent_low": round(recent_low, 2),
    }


def detect_bullish_candlestick(df: pd.DataFrame) -> dict | None:
    """Textbook bullish reversal candles on the most recent bar: Bullish
    Engulfing, Hammer, Bullish Harami, Piercing Line, Morning Star. Quality
    (0-10) mirrors the geometry checks from the Forthius Reversal Scanner
    ingest (engulfing ratio + close position, wick-in-ATR for Hammer,
    penetration ratio for Piercing Line) without replicating its full
    trend-context gating — this function only reads candle shape.
    """
    if len(df) < 20:
        return None
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    atr = (h - l).rolling(14).mean()
    a = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0
    if a <= 0:
        return None

    o0, h0, l0, c0 = float(o.iloc[-1]), float(h.iloc[-1]), float(l.iloc[-1]), float(c.iloc[-1])
    o1, h1, l1, c1 = float(o.iloc[-2]), float(h.iloc[-2]), float(l.iloc[-2]), float(c.iloc[-2])
    o2, h2, l2, c2 = float(o.iloc[-3]), float(h.iloc[-3]), float(l.iloc[-3]), float(c.iloc[-3])
    body0, body1, body2 = abs(c0 - o0), abs(c1 - o1), abs(c2 - o2)
    range0 = h0 - l0
    bull0, bear1, bear2 = c0 > o0, c1 < o1, c2 < o2

    if bear1 and bull0 and c0 >= o1 and o0 <= c1 and body0 > body1 * 1.1:
        ratio = body0 / max(body1, 1e-9)
        close_pos = (c0 - l0) / range0 if range0 > 0 else 0.0
        q = min(10, (4 if ratio >= 2 else 2 if ratio >= 1.5 else 0)
                + (4 if close_pos >= 0.9 else 2 if close_pos >= 0.75 else 0) + 2)
        return {"pattern": "Bullish Engulfing", "quality": q}

    lw0 = min(o0, c0) - l0
    uw0 = h0 - max(o0, c0)
    if range0 > 0 and body0 / range0 <= 0.35 and lw0 >= 2 * a and uw0 <= max(body0 * 0.4, a * 0.15):
        body_top_pos = (min(o0, c0) - l0) / range0
        q = min(10, (4 if lw0 / a >= 4 else 2 if lw0 / a >= 3 else 0)
                + (3 if body_top_pos >= 0.65 else 0) + 3)
        return {"pattern": "Hammer", "quality": q}

    if bear1 and body1 > a * 1.5 and bull0 and max(o0, c0) <= max(o1, c1) \
            and min(o0, c0) >= min(o1, c1) and body0 < body1 * 0.6:
        ratio = body0 / max(body1, 1e-9)
        q = min(10, (4 if ratio <= 0.3 else 2 if ratio <= 0.5 else 0)
                + (3 if body1 / a >= 1.5 else 0) + 3)
        return {"pattern": "Bullish Harami", "quality": q}

    mid1 = (o1 + c1) / 2
    if bear1 and body1 > a and bull0 and o0 < c1 and mid1 < c0 < o1 and body0 > a:
        penetration = (c0 - c1) / max(o1 - c1, 1e-9)
        q = min(10, (4 if penetration >= 1.0 else 2 if penetration >= 0.75 else 0) + 6)
        return {"pattern": "Piercing Line", "quality": q}

    doji_like = body1 / max(h1 - l1, 1e-9) < 0.3
    if bear2 and body2 > a * 2 and doji_like and bull0 and body0 > a * 2 \
            and c0 > (o2 + c2) / 2 and o1 < c2:
        penetration = (c0 - c2) / max(o2 - c2, 1e-9)
        q = min(10, (4 if body1 / max(h1 - l1, 1e-9) <= 0.1 else 2)
                + (4 if penetration >= 1.0 else 2 if penetration >= 0.75 else 0) + 2)
        return {"pattern": "Morning Star", "quality": q}

    return None


def detect_bullish_rsi_divergence(df: pd.DataFrame, lookback: int = 10) -> bool:
    """Price makes a new low while RSI doesn't — classic momentum-divergence
    reversal tell (from the Forthius Reversal Scanner ingest)."""
    if len(df) < lookback + 20:
        return False
    close = df["close"]
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    low = df["low"]
    prior_low = float(low.iloc[-lookback - 1:-1].min())
    prior_rsi_low = float(rsi.iloc[-lookback - 1:-1].min())
    return bool(low.iloc[-1] < prior_low and rsi.iloc[-1] > prior_rsi_low)


def detect_bullish_reversal_structure(
    df: pd.DataFrame, pivot_len: int = 5, eq_tol_pct: float = 3.0, min_pullback_pct: float = 3.0,
) -> dict | None:
    """Simplified Double Bottom / Inverse Head & Shoulders detector, pivot-based
    (see the AGPro Reversal Pattern Quality Scanner ingest). Looser tolerances
    than the source script since this checks once per symbol per scan rather
    than continuously re-scanning every bar for a live chart overlay.
    """
    if len(df) < pivot_len * 6 + 10:
        return None
    low, high, close = df["low"], df["high"], df["close"]
    n = len(df)

    def _is_pivot_low(i: int) -> bool:
        window = low.iloc[max(0, i - pivot_len):i + pivot_len + 1]
        return bool(low.iloc[i] == window.min())

    def _is_pivot_high(i: int) -> bool:
        window = high.iloc[max(0, i - pivot_len):i + pivot_len + 1]
        return bool(high.iloc[i] == window.max())

    search_start = max(0, n - 120)
    search_end = n - pivot_len
    piv_lows = [i for i in range(search_start, search_end) if _is_pivot_low(i)]
    piv_highs = [i for i in range(search_start, search_end) if _is_pivot_high(i)]
    last_close = float(close.iloc[-1])

    if len(piv_lows) >= 2:
        i1, i2 = piv_lows[-2], piv_lows[-1]
        tr1, tr2 = float(low.iloc[i1]), float(low.iloc[i2])
        pct_eq = abs(tr1 - tr2) / max((tr1 + tr2) / 2, 1e-9) * 100
        necks = [hh for hh in piv_highs if i1 < hh < i2]
        if pct_eq <= eq_tol_pct and necks:
            neck = float(high.iloc[necks[-1]])
            pullback_pct = (neck - min(tr1, tr2)) / neck * 100 if neck > 0 else 0.0
            if pullback_pct >= min_pullback_pct and last_close > neck:
                depth_score = min(10.0, pullback_pct / 5 * 10)
                sym_score = max(0.0, 10 - pct_eq / eq_tol_pct * 10)
                return {"pattern": "Double Bottom", "quality": round((depth_score + sym_score) / 2, 1)}

    if len(piv_lows) >= 3:
        i1, i2, i3 = piv_lows[-3], piv_lows[-2], piv_lows[-1]
        ls, head, rs = float(low.iloc[i1]), float(low.iloc[i2]), float(low.iloc[i3])
        if head < ls and head < rs:
            pct_eq = abs(ls - rs) / max((ls + rs) / 2, 1e-9) * 100
            necks = [hh for hh in piv_highs if i1 < hh < i3]
            if pct_eq <= eq_tol_pct * 2 and len(necks) >= 2:
                neck = float(np.mean([float(high.iloc[necks[0]]), float(high.iloc[necks[-1]])]))
                pullback_pct = (neck - head) / neck * 100 if neck > 0 else 0.0
                if pullback_pct >= min_pullback_pct and last_close > neck:
                    depth_score = min(10.0, pullback_pct / 5 * 10)
                    sym_score = max(0.0, 10 - pct_eq / (eq_tol_pct * 2) * 10)
                    return {"pattern": "Inverse Head & Shoulders",
                            "quality": round((depth_score + sym_score) / 2, 1)}

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Validation layer — nine independent confirmation checks run on every Early
# Reversal candidate (and reusable from any screener). Seven are direct
# Python ports of vault pages: Market-Structure-CHOCH-BOS (structure),
# Multi-Timeframe-Analysis (weekly regime), False-Break-Buildup-Trading
# (fakeout/retest), TPT-Thrust-Pullback-Thrust (pullback after breakout),
# Trend-Lines (supply/demand trendline break), Fair-Value-Gap (FVG pullback
# rejection), and Volume-Profile (POC/value-area acceptance). Volume and ATR
# checks follow the standard O'Neil/Minervini breakout-volume and
# volatility-band rules already cited in Stage-Analysis / VCP.
# ──────────────────────────────────────────────────────────────────────────────

def _atr_series(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()   # Wilder smoothing


def detect_bos_choch(df: pd.DataFrame, pivot_len: int = 5,
                     lookback: int = 120) -> dict | None:
    """Bullish market-structure event (SMC swing-labeling walk): a close above
    the most recent confirmed swing high while structure is bearish = CHOCH
    (first counter-trend break); while already bullish = BOS (continuation).
    A later close below a confirmed swing low re-flips structure bearish and
    invalidates the bullish event. Returns the surviving bullish event or None.
    """
    if len(df) < pivot_len * 4 + 20:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    n = len(df)

    swing_high: float | None = None
    swing_low: float | None = None
    trend = 0            # 1 up / -1 down / 0 unknown
    last_event: tuple[str, int, float] | None = None

    for i in range(max(pivot_len * 2, n - lookback), n):
        j = i - pivot_len          # pivot confirmed pivot_len bars later
        if j >= pivot_len:
            if high.iloc[j] == high.iloc[j - pivot_len: j + pivot_len + 1].max():
                swing_high = float(high.iloc[j])
            if low.iloc[j] == low.iloc[j - pivot_len: j + pivot_len + 1].min():
                swing_low = float(low.iloc[j])
        c = float(close.iloc[i])
        if swing_high is not None and c > swing_high:
            last_event = ("BOS" if trend == 1 else "CHOCH", i, swing_high)
            trend = 1
            swing_high = None      # consumed — wait for a fresh pivot
        elif swing_low is not None and c < swing_low:
            trend = -1
            swing_low = None
            last_event = None      # bearish break invalidates the bullish event

    if last_event is None:
        return None
    label, idx, level = last_event
    return {"signal": label, "level": round(level, 2), "bars_ago": n - 1 - idx}


def detect_volume_confirmation(df: pd.DataFrame, avg_len: int = 20,
                               surge_mult: float = 1.5,
                               window: int = 5) -> dict | None:
    """Volume must back the move: a recent up-day at >= surge_mult x the
    20-day average volume (breakout-volume rule), or a 10-day up/down volume
    ratio >= 1.2 showing net accumulation."""
    if "volume" not in df.columns or len(df) < avg_len + window + 2:
        return None
    vol = df["volume"].astype(float)
    close = df["close"]
    avg = vol.rolling(avg_len).mean()
    up_day = close > close.shift(1)

    rvol = vol / avg.replace(0, np.nan)
    recent_up_rvol = rvol.tail(window)[up_day.tail(window)]
    best_rvol = float(recent_up_rvol.max()) if not recent_up_rvol.empty else 0.0
    if pd.isna(best_rvol):
        best_rvol = 0.0

    up_vol = float(vol.tail(10)[up_day.tail(10)].sum())
    down_vol = float(vol.tail(10)[~up_day.tail(10)].sum())
    ud_ratio = min(up_vol / max(down_vol, 1.0), 99.0)   # cap: zero-down-volume runs

    return {"best_up_rvol": round(best_rvol, 2), "ud_ratio": round(ud_ratio, 2),
            "surge_mult": surge_mult,
            "pass": bool(best_rvol >= surge_mult or ud_ratio >= 1.2)}


def compute_atr_filter(df: pd.DataFrame, n: int = 14, min_pct: float = 1.0,
                       max_pct: float = 8.0) -> dict | None:
    """ATR(14) as % of price must sit in a tradeable band — below min_pct the
    stock is too dead to pay for the trade, above max_pct the stop distance is
    uninvestable. Also reports whether ATR is contracting vs 20 bars ago
    (constructive post-decline compression, per the VCP/buildup notes)."""
    if len(df) < n + 25:
        return None
    atr = _atr_series(df, n)
    last_close = float(df["close"].iloc[-1])
    a_now, a_prev = float(atr.iloc[-1]), float(atr.iloc[-21])
    if last_close <= 0 or pd.isna(a_now):
        return None
    atr_pct = a_now / last_close * 100
    return {"atr_pct": round(atr_pct, 2),
            "contracting": bool(not pd.isna(a_prev) and a_now < a_prev),
            "pass": bool(min_pct <= atr_pct <= max_pct)}


def detect_mtf_alignment(df: pd.DataFrame, min_weeks: int = 30) -> dict | None:
    """Weekly-regime read from the Multi-Timeframe-Analysis vault page (daily
    setups inside a deteriorating weekly tape fail repeatedly). Three checks
    on daily bars resampled to weekly: close above the 10-week EMA, weekly
    RSI(14) >= 45 (stabilizing — a stock exiting a decline rarely has weekly
    RSI above 50 yet), and a weekly higher low. Pass = at least 2 of 3."""
    if not isinstance(df.index, pd.DatetimeIndex):
        return None
    wk = (df.resample("W-FRI")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna())
    if len(wk) < min_weeks:
        return None
    wclose = wk["close"]
    above_ema = bool(float(wclose.iloc[-1]) > float(_ema_series(wclose, 10).iloc[-1]))

    delta = wclose.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    rsi_ok = bool(not pd.isna(rsi.iloc[-1]) and float(rsi.iloc[-1]) >= 45)

    higher_low = bool(float(wk["low"].iloc[-4:].min()) > float(wk["low"].iloc[-12:-4].min()))

    return {"above_10w_ema": above_ema, "weekly_rsi_ok": rsi_ok,
            "weekly_higher_low": higher_low,
            "pass": bool(above_ema + rsi_ok + higher_low >= 2)}


def detect_pullback_entry(df: pd.DataFrame, breakout_lookback: int = 15,
                          level_lookback: int = 20,
                          tol_pct: float = 2.0) -> dict | None:
    """Breakout → orderly pullback → hold sequence (TPT strategy applied to a
    breakout level rather than a bare EMA touch). Finds the most recent close
    that crossed above the prior `level_lookback`-day high, then requires the
    subsequent pullback to have come near that level without losing it, with
    the latest close back above the level and turning up."""
    if len(df) < level_lookback + breakout_lookback + 5:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    n = len(df)
    for k in range(2, breakout_lookback + 1):
        i = n - 1 - k                       # candidate breakout bar
        level = float(high.iloc[i - level_lookback:i].max())
        if float(close.iloc[i]) > level >= float(close.iloc[i - 1]):
            post_low = float(low.iloc[i + 1:].min())
            pulled_back = post_low <= level * (1 + tol_pct / 100)
            held = post_low >= level * (1 - tol_pct / 100)
            reclaimed = float(close.iloc[-1]) > level
            turning_up = float(close.iloc[-1]) > float(close.iloc[-2])
            return {"level": round(level, 2), "bars_since_breakout": k,
                    "pass": bool(pulled_back and held and reclaimed and turning_up)}
    return None


def detect_fakeout(df: pd.DataFrame, level_lookback: int = 20,
                   window: int = 10, tol_pct: float = 1.0) -> dict | None:
    """False-break / retest check from the False-Break-Buildup-Trading vault
    page. Walks back from the latest bar to the most recent interaction with
    the rolling `level_lookback`-day high:
      - pierced intraday but closed back below          → "fakeout" (trap)
      - broke out, later retested the level and held    → "confirmed_retest"
      - broke out, no retest yet but still above        → "breakout_no_retest"
      - broke out, then closed back below the level     → "fakeout"
    """
    if len(df) < level_lookback + window + 2:
        return None
    high, close = df["high"], df["close"]
    n = len(df)
    status, level_out = "no_break", None
    for k in range(1, window + 1):
        i = n - k
        level = float(high.iloc[i - level_lookback:i].max())
        pierced = float(high.iloc[i]) > level
        closed_above = float(close.iloc[i]) > level
        if pierced and not closed_above:
            status, level_out = "fakeout", level
            break
        if closed_above and float(close.iloc[i - 1]) <= level:
            post = df.iloc[i + 1:]
            if post.empty:
                status = "breakout_no_retest"
            elif float(close.iloc[-1]) <= level:
                status = "fakeout"
            elif float(post["low"].min()) <= level * (1 + tol_pct / 100):
                status = "confirmed_retest"
            else:
                status = "breakout_no_retest"
            level_out = level
            break
    return {"status": status,
            "level": round(level_out, 2) if level_out is not None else None,
            "pass": status == "confirmed_retest",
            "warn": status == "fakeout"}


def detect_trendline_break(df: pd.DataFrame, prd: int = 20, recent: int = 10,
                           max_angle: float = 30.0) -> dict | None:
    """Port of the "Trend Lines by Kris" Pine indicator (see
    sources/Trend-Lines-by-Kris-Pine.md and concepts/Trend-Lines.md):
    supply line = the two most recent confirmed pivot highs sloping down,
    demand line = the two most recent confirmed pivot lows sloping up.
    Same rules as the script — pivots ≤ 7×prd bars apart, no close may have
    crossed the line before it completed, normalized angle ≤ 30° (slope
    mapped onto a 500-bar 3:1-aspect box), and a break needs the candle
    BODY to close beyond the projected line (wick pierces don't count).
    Supply-line break = bullish, demand-line break = bearish.
    """
    if len(df) < prd * 4 + 5:
        return None
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(df)
    win = min(n, 500)
    yaxis = float(h.tail(win).max() - l.tail(win).min())
    height = 500 / 3.0
    max_dist = prd * 7

    def _angle(x1: int, y1: float, x2: int, y2: float) -> float:
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 or dy == 0 or yaxis == 0:
            return 0.0
        return float(abs(np.degrees(np.arctan((dy / yaxis * height) / dx))))

    def _line_y(x1: int, y1: float, x2: int, y2: float, x: int) -> float:
        return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

    def _pivots(series: pd.Series, is_high: bool) -> list[tuple[int, float]]:
        out = []
        for i in range(prd, n - prd):
            w = series.iloc[i - prd:i + prd + 1]
            v = float(series.iloc[i])
            if v == float(w.max() if is_high else w.min()):
                out.append((i, v))
        return out

    def _scan(pivots: list[tuple[int, float]], is_supply: bool) -> dict | None:
        # newest adjacent pair first, mirroring the Pine bin order
        for a in range(len(pivots) - 1, 0, -1):
            (x1, y1), (x2, y2) = pivots[a - 1], pivots[a]
            sloped = y2 < y1 if is_supply else y2 > y1
            if not sloped or (x2 - x1) > max_dist:
                continue
            ang = _angle(x1, y1, x2, y2)
            if ang > max_angle:
                continue
            confirm = min(n - 1, x2 + prd)     # pivot confirms prd bars later
            clean = True
            for b in range(x1 + 1, confirm + 1):
                ly = _line_y(x1, y1, x2, y2, b)
                cb = float(c.iloc[b])
                if (is_supply and cb > ly) or (not is_supply and cb < ly):
                    clean = False
                    break
            if not clean:
                continue
            def _anchors(broken: bool, bars_ago: int | None,
                         level_at_end: float) -> dict:
                # x1/x2 = anchor bar indices; y1/y2 = anchor prices.
                # x3/y3 = the line's projection at the last bar so the client
                # can draw an "extended forward" line without having to
                # recompute the slope.
                return {
                    "x1": int(x1), "y1": round(float(y1), 4),
                    "x2": int(x2), "y2": round(float(y2), 4),
                    "x3": int(n - 1), "y3": round(float(level_at_end), 4),
                    "broken": broken,
                    "bars_ago": bars_ago,
                    "level": round(float(level_at_end), 2),
                    "angle": round(ang, 1),
                }
            for b in range(confirm + 1, n):    # first BODY close beyond line
                ly = _line_y(x1, y1, x2, y2, b)
                body = (max(float(o.iloc[b]), float(c.iloc[b])) if is_supply
                        else min(float(o.iloc[b]), float(c.iloc[b])))
                if (is_supply and body > ly) or (not is_supply and body < ly):
                    return _anchors(True, n - 1 - b, ly)
            return _anchors(False, None, _line_y(x1, y1, x2, y2, n - 1))
        return None

    supply = _scan(_pivots(h, True), True)
    demand = _scan(_pivots(l, False), False)
    if supply is None and demand is None:
        return None
    return {"supply": supply, "demand": demand, "recent": recent}


def detect_fvg_pullback(df: pd.DataFrame, atr_mult: float = 0.5,
                        atr_len: int = 14, recent: int = 10) -> dict | None:
    """Port of the "BOS & FVG Pullback Signals" Pine indicator (see
    sources/BOS-FVG-Pullback-Signals-Pine.md and concepts/Fair-Value-Gap.md;
    note: despite its title the script has no BOS logic — it's pure FVG).

    State machine per bar, same order as the Pine: (1) a qualifying 3-candle
    gap (directional middle candle, gap height > atr_mult × ATR) replaces the
    active FVG on its side; (2) a close fully through the zone invalidates
    it; (3) buy signal when a bar opens above the bull zone, dips into it,
    and closes back above the top with a dominant lower wick — one signal
    per zone. Bearish is the mirror. Returns the most recent buy/sell
    signal ages plus any still-active zones.
    """
    if len(df) < atr_len + 10:
        return None
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    atr = _atr_series(df, atr_len)
    n = len(df)

    bull_top = bull_bot = bear_top = bear_bot = None
    last_buy = last_sell = None

    for i in range(2, n):
        a = float(atr.iloc[i])
        if pd.isna(a) or a <= 0:
            continue
        o0, h0, l0, c0 = float(o.iloc[i]), float(h.iloc[i]), float(l.iloc[i]), float(c.iloc[i])
        h2, l2 = float(h.iloc[i - 2]), float(l.iloc[i - 2])
        c1, o1 = float(c.iloc[i - 1]), float(o.iloc[i - 1])

        if l0 > h2 and c1 > o1 and (l0 - h2) > a * atr_mult:
            bull_top, bull_bot = l0, h2
        if h0 < l2 and c1 < o1 and (l2 - h0) > a * atr_mult:
            bear_top, bear_bot = l2, h0

        if bull_top is not None and c0 < bull_bot:
            bull_top = bull_bot = None
        if bear_top is not None and c0 > bear_top:
            bear_top = bear_bot = None

        if bull_top is not None:
            touch = bull_bot <= l0 <= bull_top
            reject = c0 > bull_top and (c0 - l0) > (h0 - c0)
            if touch and reject and o0 > bull_top:
                last_buy = i
                bull_top = bull_bot = None
        if bear_top is not None:
            touch = bear_bot <= h0 <= bear_top
            reject = c0 < bear_bot and (h0 - c0) > (c0 - l0)
            if touch and reject and o0 < bear_bot:
                last_sell = i
                bear_top = bear_bot = None

    if last_buy is None and last_sell is None and bull_top is None and bear_top is None:
        return None
    return {
        "buy_bars_ago": (n - 1 - last_buy) if last_buy is not None else None,
        "sell_bars_ago": (n - 1 - last_sell) if last_sell is not None else None,
        "active_bull_zone": (round(bull_bot, 2), round(bull_top, 2)) if bull_top is not None else None,
        "active_bear_zone": (round(bear_bot, 2), round(bear_top, 2)) if bear_top is not None else None,
        "recent": recent,
    }


def compute_volume_profile_levels(df: pd.DataFrame, lookback: int = 60,
                                  bins: int = 20,
                                  va_pct: float = 0.70) -> dict | None:
    """Volume profile POC / VAH / VAL over the last `lookback` bars, ingested
    from the MTF Volume Profiles [TradingIQ] Pine (sources/MTF-Volume-
    Profiles-TradingIQ-Pine.md, concepts/Volume-Profile.md) with two
    deliberate upgrades documented there: volume is split across price bins
    by proportional range overlap (tools/volume_profile.js's method — more
    accurate than the script's even split per row), and the value area is
    expanded greedily toward the higher-volume neighbor (standard market-
    profile rule) instead of strictly alternating rows. The script's delta
    model is kept: each bar's volume is signed by close-vs-prior-close and
    accumulated per bin, so the POC's delta says who was in control there.
    """
    if "volume" not in df.columns or len(df) < 10:
        return None
    w = df.tail(lookback)
    lo, hi = float(w["low"].min()), float(w["high"].max())
    if not hi > lo:
        return None
    edges = np.linspace(lo, hi, bins + 1)
    bin_size = (hi - lo) / bins
    vol_bins = np.zeros(bins)
    delta_bins = np.zeros(bins)

    closes = w["close"].to_numpy(dtype=float)
    prev = np.concatenate([[closes[0]], closes[:-1]])
    signs = np.sign(closes - prev)

    for k in range(len(w)):
        v = float(w["volume"].iloc[k])
        if not v > 0:
            continue
        bl, bh = float(w["low"].iloc[k]), float(w["high"].iloc[k])
        rng = bh - bl
        if rng <= 0:                     # flat bar: whole volume in one bin
            i = min(bins - 1, max(0, int((closes[k] - lo) / bin_size)))
            vol_bins[i] += v
            delta_bins[i] += v * signs[k]
            continue
        i0 = min(bins - 1, max(0, int((bl - lo) / bin_size)))
        i1 = min(bins - 1, max(0, int((bh - lo) / bin_size)))
        for i in range(i0, i1 + 1):
            overlap = max(0.0, min(bh, edges[i + 1]) - max(bl, edges[i]))
            if overlap > 0:
                share = v * overlap / rng
                vol_bins[i] += share
                delta_bins[i] += share * signs[k]

    total = float(vol_bins.sum())
    if total <= 0:
        return None

    poc = int(vol_bins.argmax())
    target = total * va_pct
    covered = float(vol_bins[poc])
    up, dn = poc + 1, poc - 1
    while covered < target and (up < bins or dn >= 0):
        vu = vol_bins[up] if up < bins else -1.0
        vd = vol_bins[dn] if dn >= 0 else -1.0
        if vu >= vd:
            covered += vu
            up += 1
        else:
            covered += vd
            dn -= 1

    poc_price = float((edges[poc] + edges[poc + 1]) / 2)
    vah = float(edges[min(up, bins)])
    val = float(edges[max(dn + 1, 0)])
    last_close = float(df["close"].iloc[-1])

    return {"poc": round(poc_price, 2), "vah": round(vah, 2), "val": round(val, 2),
            "above_poc": bool(last_close > poc_price),
            "above_vah": bool(last_close > vah),
            "below_val": bool(last_close < val),
            "poc_delta_positive": bool(delta_bins[poc] > 0)}


def compute_validation_summary(df: pd.DataFrame) -> dict:
    """Runs all nine validation checks and returns a card/screener-ready
    summary: per-check booleans (keyed Structure/Volume/ATR/MTF/Pullback/
    Retest/Trendline/FVG/Profile), passed count, reason strings for passing
    checks, and warning strings (fakeout risk, demand-trendline break,
    bearish FVG rejection, below-value-area)."""
    checks: dict[str, bool] = {}
    reasons: list[str] = []
    warnings: list[str] = []

    bos = detect_bos_choch(df)
    checks["Structure"] = bool(bos and bos["bars_ago"] <= 30)
    if checks["Structure"]:
        reasons.append(f"Bullish {bos['signal']} — closed above swing high "
                       f"{bos['level']:.2f} {bos['bars_ago']} bars ago")

    volc = detect_volume_confirmation(df)
    checks["Volume"] = bool(volc and volc["pass"])
    if checks["Volume"]:
        detail = (f"{volc['best_up_rvol']:.1f}× avg volume on a recent up-day"
                  if volc["best_up_rvol"] >= volc["surge_mult"]
                  else f"10-day up/down volume ratio {volc['ud_ratio']:.2f} (accumulation)")
        reasons.append(f"Volume confirms — {detail}")

    atrf = compute_atr_filter(df)
    checks["ATR"] = bool(atrf and atrf["pass"])
    if checks["ATR"]:
        extra = ", volatility contracting" if atrf["contracting"] else ""
        reasons.append(f"ATR {atrf['atr_pct']:.1f}% of price — tradeable band{extra}")

    mtf = detect_mtf_alignment(df)
    checks["MTF"] = bool(mtf and mtf["pass"])
    if checks["MTF"]:
        parts = [label for label, ok in
                 [("above 10-wk EMA", mtf["above_10w_ema"]),
                  ("weekly RSI ≥ 45", mtf["weekly_rsi_ok"]),
                  ("weekly higher low", mtf["weekly_higher_low"])] if ok]
        reasons.append("Weekly timeframe aligned — " + ", ".join(parts))

    pb = detect_pullback_entry(df)
    checks["Pullback"] = bool(pb and pb["pass"])
    if checks["Pullback"]:
        reasons.append(f"Pullback entry — broke out over {pb['level']:.2f} "
                       f"{pb['bars_since_breakout']} bars ago, pulled back and held")

    fk = detect_fakeout(df)
    checks["Retest"] = bool(fk and fk["pass"])
    if checks["Retest"]:
        reasons.append(f"Breakout over {fk['level']:.2f} retested and held — not a fakeout")
    elif fk and fk["warn"]:
        warnings.append(f"⚠ Fakeout risk — pierced {fk['level']:.2f} "
                        f"but closed back below (false break)")

    tl = detect_trendline_break(df)
    sup = tl["supply"] if tl else None
    dem = tl["demand"] if tl else None
    recent_tl = tl["recent"] if tl else 10
    checks["Trendline"] = bool(sup and sup["broken"] and sup["bars_ago"] <= recent_tl)
    if checks["Trendline"]:
        reasons.append(f"Falling supply trendline broken — body closed above "
                       f"{sup['level']:.2f} {sup['bars_ago']} bars ago "
                       f"({sup['angle']:.0f}° line)")
    if dem and dem["broken"] and dem["bars_ago"] <= recent_tl:
        warnings.append(f"⚠ Rising demand trendline broken {dem['bars_ago']} bars ago "
                        f"— body closed below {dem['level']:.2f} (bearish break)")

    fvg = detect_fvg_pullback(df)
    buy_ago = fvg["buy_bars_ago"] if fvg else None
    sell_ago = fvg["sell_bars_ago"] if fvg else None
    recent_fvg = fvg["recent"] if fvg else 10
    checks["FVG"] = bool(buy_ago is not None and buy_ago <= recent_fvg)
    if checks["FVG"]:
        reasons.append(f"Bullish FVG pullback rejection {buy_ago} bars ago — "
                       f"dipped into the demand gap and closed back above it")
    if sell_ago is not None and sell_ago <= recent_fvg:
        warnings.append(f"⚠ Bearish FVG rejection {sell_ago} bars ago — "
                        f"pullback into the overhead gap was sold")

    vp = compute_volume_profile_levels(df)
    checks["Profile"] = bool(vp and vp["above_poc"])
    if checks["Profile"]:
        extra = " — above the entire value area" if vp["above_vah"] else ""
        delta_note = ", buy-side delta at the node" if vp["poc_delta_positive"] else ""
        reasons.append(f"Volume profile — close accepted above POC {vp['poc']:.2f} "
                       f"(VAH {vp['vah']:.2f} / VAL {vp['val']:.2f}){extra}{delta_note}")
    elif vp and vp["below_val"]:
        warnings.append(f"⚠ Trading below the value area (VAL {vp['val']:.2f}) — "
                        f"no volume acceptance of the recovery yet")

    return {"checks": checks, "passed": sum(checks.values()), "total": len(checks),
            "reasons": reasons, "warnings": warnings}


def compute_early_reversal_signal(df: pd.DataFrame) -> dict | None:
    """Early Reversal Detector — composite of the 4 signals above. Returns
    None if the drop-recovery gate isn't met at all (no real decline+reclaim
    means this isn't a reversal candidate regardless of anything else).
    """
    drop_recovery = compute_drop_recovery_signal(df)
    if drop_recovery is None:
        return None

    score = 25.0
    reasons = [
        f"Dropped {drop_recovery['drop_pct']:.1f}% from {drop_recovery['recent_high']:.2f}, "
        f"recovered {drop_recovery['recovery_pct']:.1f}% of that drop"
    ]

    exhaustion = compute_recent_exhaustion_signal(df)
    if exhaustion == "bullish":
        score += 25.0
        reasons.append("Bullish %R Trend Exhaustion fired recently (left oversold)")

    candle = detect_bullish_candlestick(df)
    if candle:
        score += candle["quality"] * 1.5
        reasons.append(f"{candle['pattern']} on the latest bar (quality {candle['quality']}/10)")

    rsi_div = detect_bullish_rsi_divergence(df)
    if rsi_div:
        score += 10.0
        reasons.append("Bullish RSI divergence — price made a new low, RSI didn't")

    structure = detect_bullish_reversal_structure(df)
    if structure:
        score += structure["quality"] * 1.5
        reasons.append(f"{structure['pattern']} structure completing (quality {structure['quality']}/10)")

    # Validation layer: modest score influence only (+2 per passed check,
    # -8 on fakeout warning) — validations confirm a reversal thesis, they
    # shouldn't be able to manufacture a candidate on their own.
    validation = compute_validation_summary(df)
    score += validation["passed"] * 2.0
    if validation["warnings"]:
        score -= 8.0
    reasons.extend(validation["reasons"])
    reasons.extend(validation["warnings"])

    return {
        "score": round(max(0.0, min(100.0, score)), 1),
        "drop_pct": drop_recovery["drop_pct"],
        "recovery_pct": drop_recovery["recovery_pct"],
        "exhaustion": exhaustion,
        "candlestick": candle["pattern"] if candle else None,
        "rsi_divergence": rsi_div,
        "structure": structure["pattern"] if structure else None,
        "validation": validation,
        "reasons": reasons,
    }


def scan_early_reversal(df: pd.DataFrame) -> dict | None:
    """Scanner Hub wrapper for compute_early_reversal_signal."""
    sig = compute_early_reversal_signal(df)
    if sig is None or sig["score"] < 35:
        return None
    tags = [f"{sig['drop_pct']:.0f}% drop", f"{sig['recovery_pct']:.0f}% recovered"]
    if sig["exhaustion"] == "bullish":
        tags.append("%R exhaustion")
    if sig["candlestick"]:
        tags.append(sig["candlestick"])
    if sig["structure"]:
        tags.append(sig["structure"])
    val = sig.get("validation")
    if val:
        tags.append(f"✔ {val['passed']}/{val['total']} validations")
        if val["checks"].get("Structure"):
            tags.append("BOS/CHOCH")
    return {
        "pattern_type": "Early Reversal",
        "tags": tags,
        "reasons": sig["reasons"],
        "score": sig["score"],
    }


def scan_harmonic_reversal(df: pd.DataFrame) -> dict | None:
    """Fibonacci-ratio harmonic pattern (Gartley/Bat/Butterfly/Crab) completing
    at D within the last 10 bars — low-risk / high-reward reversal setup."""
    if len(df) < 60:
        return None
    try:
        import harmonic_patterns as hp
    except ImportError:
        return None
    h = hp.detect_last_pattern(df)
    if h is None:
        return None
    t = h["trade"]
    if t["rr_to_t2"] < 1.5:
        return None
    reasons = [
        f"{h['pattern']} ({h['direction']}) completed at D, {h['age_bars']} bars ago",
        f"Ratios AB/XA={h['ratios']['AB/XA']}, BC/AB={h['ratios']['BC/AB']}, "
        f"CD/BC={h['ratios']['CD/BC']}, AD/XA={h['ratios']['AD/XA']}",
        f"Entry {t['entry']} · Stop {t['stop']} · T2 {t['targets'][1]} — R:R {t['rr_to_t2']}",
    ]
    return {
        "pattern_type": f"Harmonic {h['pattern']}",
        "tags": [h["pattern"], h["direction"], f"R:R {t['rr_to_t2']}"],
        "reasons": reasons,
        "score": round(t["rr_to_t2"] * 2, 2),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Scanner registry
# ──────────────────────────────────────────────────────────────────────────────

SCANNERS: dict[str, dict] = {
    "52-Week High Leaders": {
        "fn": scan_52w_high_leaders,
        "description": "Strong momentum leaders within 5% of their 52-week high",
        "category": "Momentum",
    },
    "Stage 2 Uptrend": {
        "fn": scan_stage2_uptrend,
        "description": "Textbook Minervini Stage 2: SMA50 > SMA150 > SMA200, all rising",
        "category": "Trend",
    },
    "Pullback Entry": {
        "fn": scan_pullback_to_ema,
        "description": "Quality stocks that touched EMA21 and are recovering above it",
        "category": "Entry",
    },
    "Darvas Box": {
        "fn": scan_darvas_box,
        "description": (
            "Swing-pivot Darvas box — Active / Near breakout / Breakout states with a "
            "0-100 score (base quality + RS percentile + vol participation − fail-risk), "
            "volume-quality tag, from-pivot distance and vol ×50d"
        ),
        "category": "Pattern",
    },
    "Momentum Continuation": {
        "fn": scan_momentum_continuation,
        "description": "Strong uptrends near 20-day highs with intact MA stack",
        "category": "Momentum",
    },
    "Base Formation": {
        "fn": scan_base_formation,
        "description": (
            "Pre-breakout base screen — Stage + pivot + RS + volume gates over a tight "
            "base under resistance (not yet broken out). Base Q (0-100), VCP / Vol Dry / "
            "HTF tags, from-pivot distance and an RS percentile; graduates to a breakout "
            "scanner once the pivot clears"
        ),
        "category": "Pattern",
    },
    "VCP Coiling": {
        "fn": scan_vcp,
        "description": "Volatility contraction pattern with drying volume — coiling before move",
        "category": "Pattern",
    },
    "Minervini VCP (valchak)": {
        "fn": scan_vcp_minervini_valchak,
        "description": (
            "Six-gate Minervini VCP breakout — port of valchak's TradingView Pine "
            "script: Trend Template (8 criteria) + VCP (2–6 contractions, first "
            "10–35%, final 3–10%, tightening ≤0.9×) + BreakingOut + VolumeSurge "
            "(≥1.4× 50-DMA) + NotExtended (≤12% above pivot). Only fires on "
            "live breakouts, not watchlists."
        ),
        "category": "Pattern",
    },
    "Near Pivot": {
        "fn": scan_near_pivot,
        "description": "Within 3% of a recent swing-high pivot — tight stop opportunity",
        "category": "Entry",
    },
    "Downside Risk": {
        "fn": scan_downside_risk,
        "description": "Below key MAs with distribution volume — stocks to avoid or short",
        "category": "Risk",
    },
    "6M Consolidation Breakout": {
        "fn": scan_6m_consolidation_breakout,
        "description": (
            "Chartink-style: Close > EMA50, Close > 126-day high (fresh breakout), "
            "prior 6-month range ≤40% (was consolidating), Volume > 2L"
        ),
        "category": "Pattern",
    },
    "1Y Breakout": {
        "fn": scan_1y_breakout,
        "description": "Close > 252-day high (1-year breakout) after consolidation ≤50%, above EMA50, Volume > 2L",
        "category": "Pattern",
    },
    "5Y Breakout": {
        "fn": scan_5y_breakout,
        "description": "Close > 1260-day high (5-year breakout) after consolidation ≤80%, above EMA50, Volume > 2L",
        "category": "Pattern",
    },
    "10Y Breakout": {
        "fn": scan_10y_breakout,
        "description": "Close > 2520-day high (10-year / all-time breakout), above EMA50, Volume > 2L — generational breakout",
        "category": "Pattern",
    },
    "High Tight Flag": {
        "fn": scan_high_tight_flag,
        "description": (
            "Rare leadership pattern: ≥90% pole within ~8 weeks, tight ≤25% flag on "
            "drying volume; scores highest at the flag-high breakout (SwingEdge "
            "Momentum Buildup ingest)"
        ),
        "category": "Pattern",
    },
    "Structural Breakout": {
        "fn": scan_structural_breakout,
        "description": (
            "Multi-week horizontal resistance cluster (≥4 touches within 1.5%) — flat "
            "bases and neckline reversals pressing or clearing the ceiling with an "
            "ATR-scaled buffer; Approaching / Confirmed / Retest states, weekly-confirm "
            "bonus (SwingEdge Structural Breakout ingest)"
        ),
        "category": "Pattern",
    },
    "Rounding Bottom": {
        "fn": scan_rounding_bottom,
        "description": (
            "Saucer base: 12–40% decline, orderly U mapped by linear-fit legs + time "
            "symmetry, EMA-21 slope turn at the trough; Approaching rim / Confirmed / "
            "Retest states, Classic Reversal vs Constructive Base by 200-DMA context "
            "(SwingEdge Rounding Bottom ingest)"
        ),
        "category": "Pattern",
    },
    "Early Reversal Detector": {
        "fn": scan_early_reversal,
        "description": (
            "Drop-then-recovery gate + bullish %R Trend Exhaustion + candlestick trigger "
            "(w/ RSI divergence) + Double Bottom/Inverse H&S structure — 4 independently-"
            "sourced reversal signals combined into one composite score, no strict-downtrend "
            "requirement. Each hit is then validated by 9 confirmation checks: BOS/CHOCH "
            "structure, volume confirmation, ATR volatility band, weekly MTF alignment, "
            "pullback-after-breakout entry, fakeout/retest detection, supply/demand "
            "trendline break, FVG pullback rejection, and volume-profile POC/value-area "
            "acceptance"
        ),
        "category": "Entry",
    },
    "Harmonic Reversal (XABCD)": {
        "fn": scan_harmonic_reversal,
        "description": (
            "Fibonacci XABCD harmonic patterns (Gartley, Bat, Butterfly, Crab) "
            "completing at D within the last 10 bars, filtered to R:R ≥ 1.5 to T2. "
            "Trade plan: entry at D, stop beyond X, targets at 0.382 / 0.618 / 1.0 of AD."
        ),
        "category": "Pattern",
    },
}


def run_scanner(scanner_name: str, symbols: list[str], fetch_fn,
                benchmark_df: pd.DataFrame | None = None) -> list[dict]:
    """Run scanner_name over symbols. Returns result cards sorted by score.

    If ``benchmark_df`` (an OHLCV frame, e.g. Nifty50) is supplied, RS is
    computed as excess return over that benchmark for the duration of the scan
    — a true relative-strength line rather than an absolute trailing return."""
    spec = SCANNERS.get(scanner_name)
    if spec is None:
        return []

    global _BENCHMARK_WRET
    _BENCHMARK_WRET = None
    if benchmark_df is not None and not benchmark_df.empty:
        try:
            col = "close" if "close" in benchmark_df.columns else "Close"
            _BENCHMARK_WRET = _weighted_trailing_return(benchmark_df[col])
        except Exception:
            _BENCHMARK_WRET = None

    try:
        results = []
        for sym in symbols:
            try:
                df = fetch_fn(sym)
                if df is None or df.empty:
                    continue
                hit = spec["fn"](df)
                if hit:
                    hit["symbol"] = sym
                    results.append(hit)
            except Exception:
                continue
    finally:
        _BENCHMARK_WRET = None      # never leak benchmark state across scans

    _finalize_relative_strength(results)
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
