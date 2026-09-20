#!/usr/bin/env python3
"""
scanner_templates.py
Pre-built pattern scanners inspired by SwingEdge's scanner hub.
Each scanner function takes a fetched OHLCV DataFrame and returns a result
dict (symbol, pattern_type, tags, reasons, score) or None if no match.
"""

import logging
import threading

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _sma(series: pd.Series, n: int) -> float:
    v = series.rolling(n).mean().iloc[-1]
    return float(v) if not pd.isna(v) else float("nan")


def _ema_series(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def _rsi_series(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI (0-100), aligned to ``close`` with NaN through the warm-up.
    A flat/all-gains window (no average loss) reads 100 rather than dividing by
    zero."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return rsi.where(avg_loss != 0.0, 100.0)


# Benchmark weighted trailing return for the active scan (set by run_scanner
# when a benchmark DataFrame is supplied). When set, _rs_raw returns the
# stock's EXCESS return over the benchmark — a true relative-strength line —
# instead of an absolute trailing return.
# threading.local() prevents concurrent scanner runs in different threads from
# leaking benchmark state into each other.
_tls = threading.local()


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
    return stock - (getattr(_tls, "benchmark_wret", None) or 0.0)


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
    score_base = round(50.0 + (5.0 - pct) * 10.0, 1)
    return {
        "pattern_type": "52-Week High Leader",
        "tags": [f"{pct:.1f}% from 52w high", "Near highs"],
        "reasons": reasons,
        "score": score_base,
        "score_base": score_base,
        "rs_raw": round(_rs_raw(df), 3),
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
    if not np.isnan(sma200_1m) and sma200 < sma200_1m:
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


def _suv_series(vol: pd.Series, lookback: int = 30, use_log: bool = False) -> pd.Series:
    """Standardized Unexpected Volume (SUV) — a per-bar volume z-score with an
    anti-leak baseline. Ported from the TradingView 8-criteria PEAD screener
    ([[sources/TV-PEAD-Screener-PineScript]]).

    Baseline = the `lookback` bars STRICTLY BEFORE each bar (`volume.shift(1)`
    rolling), so an event bar never inflates the mean/std it is measured against
    — the "pre-D0 baseline" fix (a trailing average that includes the elevated
    post-earnings bars deflates the reading for weeks). `use_log` runs the z on
    log(volume): volume is right-skewed, so one prior spike otherwise inflates
    std and suppresses SUV across the whole PEAD window. Sigma floor prevents
    div-by-≈0 on thin names; output clamped to [-10, 20] so a lone historical
    spike + a quiet tape can't yield a ±40 reading.
    """
    v = vol.astype(float)
    if use_log:
        cur = np.log(v.where(v > 0))
        floor = 0.2
    else:
        cur = v
        floor = 1.0
    prior = cur.shift(1)
    mean = prior.rolling(lookback).mean()
    std = prior.rolling(lookback).std().clip(lower=floor)
    z = (cur - mean) / std
    return z.clip(lower=-10.0, upper=20.0)


def scan_pead(df: pd.DataFrame,
              lookback: int = 20,
              min_react_atr: float = 1.5,
              min_react_pct: float = 4.0,
              min_suv: float = 1.5,
              suv_lookback: int = 30,
              suv_log: bool = False,
              drift_tol: float = 0.98) -> dict | None:
    """Proxy-PEAD (Post-Earnings Announcement Drift) — the price-only event engine.

    This function stays deliberately price-only and symbol-blind: `run_scanner`
    attaches the symbol only AFTER it returns, so it cannot look up fundamentals
    or a result calendar for itself. It infers the earnings event from price — a
    large reaction on Standardized-Unexpected-Volume is the market pricing the
    surprise — and requires the move to be *holding / extending*: the drift.

    Phases 2 and 3 no longer live here, they live in the symbol-level join:
    `earnings_calendar.enrich_pead_hit` reconciles the `event_date` returned
    below against the real NSE result calendar and computes a TRUE SUE
    (reported EPS vs analyst consensus). Both arrive free from yfinance — the
    "no consensus estimate for NSE" constraint this scanner was built under was
    retired on 2026-08-04; see that module's header for the coverage probe.
    Un-enriched, the output is still honestly labelled Proxy-PEAD.

    Event gate (bullish side only in Phase 1):
      • one bar in the last `lookback` sessions (and ≥1 bar ago, so drift is
        observable) whose up-reaction ≥ `min_react_atr`×ATR(14) AND
        ≥ `min_react_pct`% close-to-close,
      • with SUV ≥ `min_suv` σ — a proper volume z-score vs a `suv_lookback`-bar
        PRE-EVENT baseline (anti-leak), not a raw ratio vs a contaminated mean.
    Drift gate: current close still ≥ `drift_tol`× the event-bar close — the
    reaction has not been given back.

    HONESTY: on its own this is "Proxy-PEAD", not SUE — the event is inferred
    from the price reaction. Only the enrichment pass may relabel a hit as
    confirmed, and only when a real result date backs it.
    """
    if len(df) < 60:
        return None
    # Drop NaN OHLCV bars up front — yfinance occasionally returns gap/holiday
    # rows with NaN prices, and because every NaN comparison is False they slip
    # through all the gates below (observed: ULTRACEMCO firing with "nan% gap",
    # score 100). Reset the index so the positional iloc logic stays consistent.
    df = df.dropna(
        subset=[c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    )
    # Keep the bar dates before flattening to positions. Phase 2 reconciles the
    # inferred event bar against the real result calendar, and reset_index(drop=True)
    # discards precisely the date it needs. The positional iloc logic below is
    # untouched — bar_dates is only read once, for the winning event bar.
    bar_dates = df.index
    df = df.reset_index(drop=True)
    if len(df) < 60:
        return None
    close = df["close"]
    high = df["high"]
    vol = df["volume"]
    last = float(close.iloc[-1])
    if np.isnan(last):
        return None

    med_vol50 = float(vol.tail(50).median())
    if not (med_vol50 > 0):
        return None
    atr = _atr_series(df, 14)
    suv = _suv_series(vol, suv_lookback, suv_log)   # standardized unexpected volume

    n = len(df)
    # Candidate event bars: at least 1 session ago (need drift), within lookback.
    start = max(1, n - 1 - lookback)
    best = None  # (react_atr, idx)
    for i in range(start, n - 1):
        prev_c = float(close.iloc[i - 1])
        if prev_c <= 0:
            continue
        react = float(close.iloc[i]) - prev_c          # full-day reaction
        if np.isnan(react) or react <= 0:
            continue                                    # bullish side only (Phase 1)
        react_pct = react / prev_c * 100.0
        atr_i = float(atr.iloc[i])
        if np.isnan(atr_i) or atr_i <= 0:
            continue
        react_atr = react / atr_i
        suv_i = float(suv.iloc[i])
        if (react_atr < min_react_atr or react_pct < min_react_pct
                or np.isnan(suv_i) or suv_i < min_suv):
            continue
        if best is None or react_atr > best[0]:
            best = (react_atr, i)

    if best is None:
        return None

    react_atr, e = best
    prev_c = float(close.iloc[e - 1])
    event_close = float(close.iloc[e])
    react_pct = (event_close - prev_c) / prev_c * 100.0
    suv_e = float(suv.iloc[e])                       # SUV z-score at the event
    vol_x = float(vol.iloc[e]) / med_vol50           # kept for display + 'Vol Confirmed' pill
    bars_since = (n - 1) - e

    # Drift gate — the reaction must still be intact.
    if last < event_close * drift_tol:
        return None
    drift_pct = (last / event_close - 1.0) * 100.0

    # 0-100 score: surprise magnitude + drift continuation + volume conviction
    # (SUV z-score, capped), tuned so the Hub's strength pills (Strongest ≥65 /
    # Moderate 45-65) bite.
    score = 40.0 + react_atr * 8.0 + drift_pct * 1.5 + min(max(suv_e, 0.0), 6.0) * 2.5
    score = float(max(0.0, min(100.0, score)))

    # Optional "gap at open" colour if the frame carries an open column.
    gap_at_open = None
    if "open" in df.columns:
        o = float(df["open"].iloc[e])
        if o > prev_c:
            gap_at_open = (o - prev_c) / prev_c * 100.0

    reasons = [
        f"Earnings-like reaction +{react_pct:.1f}% ({react_atr:.1f}×ATR), "
        f"{bars_since} session(s) ago",
        f"Standardized Unexpected Volume {suv_e:.1f}σ vs a {suv_lookback}-day "
        f"pre-event baseline ({vol_x:.1f}× median) — institutional footprint",
        f"Drift intact: price {drift_pct:+.1f}% since the event — reaction held, not faded",
        "Proxy-PEAD: event inferred from the price reaction, not a confirmed "
        "earnings date (the enrichment pass replaces this line once reconciled)",
    ]
    if gap_at_open is not None:
        reasons.insert(1, f"Gapped +{gap_at_open:.1f}% at the open — classic post-result gap")
    if last >= float(high.iloc[e]):
        reasons.append("Closed above the event-bar high — drift extending, not just holding")

    tags = [
        "Proxy-PEAD",
        f"{react_pct:.0f}% gap",
        f"SUV {suv_e:.1f}σ",
        f"{bars_since}d drift",
        f"{drift_pct:+.0f}% since",
    ]
    # The event bar's calendar date, for the Phase 2 join. None when the caller
    # passed a positionally-indexed frame — the enrichment reports NOT_CHECKED
    # rather than reconciling against a date it does not have.
    event_date = None
    try:
        ts = bar_dates[e]
        if hasattr(ts, "date"):
            event_date = ts.date().isoformat()
    except Exception:
        pass

    return {
        "pattern_type": "Proxy-PEAD Drift",
        "tags": tags,
        "reasons": reasons,
        "score": round(score, 2),
        "vol_x50d": round(vol_x, 2),   # lights up the Hub 'Vol Confirmed' pill
        "event_date": event_date,      # Phase 2 reconciliation key
    }


def _enrich_pead(results: list[dict]) -> list[dict]:
    """SCANNERS ``enrich`` hook for the PEAD entries — Phases 2 + 3.

    Reconciles each inferred event against the real NSE result calendar and
    attaches a true SUE. Imported lazily and failure-tolerant on purpose: if
    earnings_calendar (or the network behind it) is unavailable the scan still
    returns, holding its honest Phase-1 'Proxy-PEAD' labelling instead of
    dropping hits or, worse, presenting unenriched ones as confirmed.
    """
    try:
        import earnings_calendar as ec
    except Exception as e:
        log.debug("PEAD earnings enrichment unavailable: %s", e)
        return results
    return ec.enrich_pead_results(results)


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
    out = {
        "pattern_type": "VCP Coiling",
        "tags": [f"{contraction:.0f}% contraction", "VCP"],
        "reasons": reasons,
        "score": round(contraction, 2),
    }
    # A plan, where the measurement harness can see it — but WITHOUT touching
    # which hits fire. This scanner is tier `weak`, meaning it has been measured;
    # swapping its coarse 3-window test for `detect_vcp_geometry`'s stricter
    # pivot walk would change the hit set and silently invalidate that recorded
    # number, which is the same reason `detect_bullish_reversal_structure` was
    # left alone when the full-spec Double Bottom landed.
    #
    # So the geometry detector is consulted as an ADD-ON: every hit above still
    # fires, and the ones the stricter detector also recognises gain an
    # entry/stop/target that `backtest.py` can R-simulate. Measured 2026-09-19
    # on 110 NSE names: the two agree on 16 of 29 hits (55%), so this scanner is
    # expected to read PARTIAL in the plan census rather than FULL — an honest
    # reading, and better than the 0/N it reported while carrying no plan at all.
    #
    # Only computed on a HIT, so the pivot walk costs nothing on the scans that
    # do not fire.
    try:
        _g = detect_vcp_geometry(df)
    except Exception:                                      # pragma: no cover
        _g = None
    if _g and all(_g.get(k) is not None for k in ("entry", "stop", "target")):
        out["entry"]  = _g["entry"]
        out["stop"]   = _g["stop"]
        out["target"] = _g["target"]
        out["geometry"] = _g
    return out


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
    # NOTE: the first/final depth ranges are applied BELOW, to the tightening run —
    # not here to the raw detector output. Checking them twice would silently reject a
    # base whose raw outermost leg is out of range even though the run that actually
    # forms the VCP is inside it, which is the same class of bug being fixed.
    tight_ratio_cap = 0.5 if strict else 0.9
    # ── Fixed 2026-08-29: this gate rejected 59 of 59 candidates, i.e. everything ──
    # The old test demanded that EVERY consecutive pair in `detect_vcp_geometry`'s
    # output tighten. But that helper returns the raw pivot-to-pivot contractions in
    # the window, and real bases oscillate — measured depth runs look like
    # [14.2, 10.2, 8.0, 5.3, 10.5, 5.7]: clearly contracting overall, yet one widening
    # leg is enough to fail a strict all-pairs test. valchak's script does not test a
    # raw list; it only COUNTS a contraction when it is tighter than the previous one,
    # so the ratio test belongs to the tightening RUN, not to everything detected.
    #
    # So: take the longest run ending at the most recent contraction in which each step
    # tightens by <= cap, and apply valchak's depth ranges to THAT run. A widening leg
    # earlier in the window now ends the run instead of invalidating the whole base.
    run = [depths[-1]]
    for i in range(len(depths) - 2, -1, -1):
        if run[0] <= depths[i] * tight_ratio_cap:
            run.insert(0, depths[i])
        else:
            break
    if len(run) < 2:
        return None
    depths = run
    first_d, final_d = depths[0], depths[-1]
    if not (10.0 <= first_d <= 35.0):
        return None
    if not (3.0 <= final_d <= 10.0):
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

    # Footprint must describe the RUN, not the detector's full window. Reporting
    # "2 contractions" next to a six-leg footprint (geom["footprint"]) invited the
    # reader to check a number the gates never used.
    footprint = "/".join(f"{d:.0f}" for d in depths) + "%"
    window_footprint = geom["footprint"]
    tags = [
        "Trend Template ✓",
        f"VCP {footprint}",
        f"Vol {vol_mult:.1f}×",
        "Strict" if strict else "Practical",
    ]
    reasons = [
        "All 8 Trend Template criteria passed (above/below levels, MA stack, 52w low/high bands, SMA200 rising)",
        f"VCP: {len(depths)} tightening contractions {footprint}, base {base_bars} bars "
        f"(detector saw {window_footprint}% across the whole window)",
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

    tags = ["Below SMA50", "Distribution"]
    score = round((sma50 - last) / sma50 * 100, 2)

    # ADX/DI directional confirmation — −DI in control with trend strength turns a
    # passive "below SMA50" into an active downtrend. (Measured: ADX/DI is a
    # regime read, not a trigger — see concepts/ADX; here it CONFIRMS the break.)
    if len(df) >= 40:
        try:
            plus_di, minus_di, adx = _adx_di_series(df)
            adx_now = float(adx.iloc[-1]); pdi = float(plus_di.iloc[-1]); mdi = float(minus_di.iloc[-1])
            if not (np.isnan(adx_now) or np.isnan(pdi)):
                if mdi > pdi and adx_now >= 25:
                    reasons.append(f"−DI {mdi:.0f} > +DI {pdi:.0f} with ADX {adx_now:.0f} — "
                                   f"directional downtrend has strength, not just a wobble")
                    tags.append("−DI>+DI, ADX≥25")
                    score = min(100.0, score + 15.0)
                elif mdi > pdi:
                    reasons.append(f"−DI {mdi:.0f} > +DI {pdi:.0f} (ADX {adx_now:.0f}) — "
                                   f"sellers ahead but trend strength still weak")
                    tags.append("−DI>+DI")
        except Exception:
            pass

    return {
        "pattern_type": "Downside Risk",
        "tags": tags,
        "reasons": reasons,
        "score": score,
    }


def scan_adx_trend_confirmation(df: pd.DataFrame) -> dict | None:
    """ADX+DI trend-UP confirmation — NOT a standalone buy trigger.

    Fires when the directional-movement system confirms an up-trend with
    strength: price > SMA50, **+DI > −DI**, **ADX ≥ 25 AND rising**. This is a
    *context/confirmation* read, not an entry: the measured evidence
    (concepts/ADX.md — DI crosses are negative-edge, the confirmed state ~neutral)
    says ADX/DI does not itself generate alpha. Its job here is to say "the trend
    is on and pointed up" so a separate price+volume trigger can be taken with the
    tape rather than against it. Deliberately carries **no entry/stop/target** —
    it is not a trade plan. Kept out of MEASURED_EDGE_SCANNERS for the same reason.
    """
    if len(df) < 60:
        return None
    close = df["close"]
    last = float(close.iloc[-1])
    sma50 = _sma(close, 50)
    if np.isnan(sma50) or last <= sma50:
        return None
    try:
        plus_di, minus_di, adx = _adx_di_series(df)
        adx_now = float(adx.iloc[-1]); adx_prev = float(adx.iloc[-2])
        pdi = float(plus_di.iloc[-1]); mdi = float(minus_di.iloc[-1])
    except Exception:
        return None
    if any(np.isnan(x) for x in (adx_now, adx_prev, pdi, mdi)):
        return None
    # +DI must lead, ADX must be actionable (≥25) AND rising (slope > level).
    if not (pdi > mdi and adx_now >= 25 and adx_now > adx_prev):
        return None

    spread = pdi - mdi
    reasons = [
        f"ADX {adx_now:.0f} (rising from {adx_prev:.0f}) — trend strength is real and building",
        f"+DI {pdi:.0f} > −DI {mdi:.0f} (spread {spread:.0f}) — buyers in directional control",
        f"Price ({last:.0f}) > SMA50 ({sma50:.0f}) — structure agrees with the DI read",
        "CONFIRMATION, not a trigger — pair with a price+volume entry; ADX/DI alone "
        "has no measured edge (concepts/ADX.md).",
    ]
    # Score from trend strength + directional conviction; capped. No trade plan.
    score = min(100.0, 35.0 + min(35.0, (adx_now - 25.0)) + min(30.0, spread))
    return {
        "pattern_type": "ADX Trend-Up (confirmation)",
        "tags": [f"ADX {adx_now:.0f}↑", f"+DI>−DI ({spread:.0f})", "Confirm, not trigger"],
        "reasons": reasons,
        "score": round(score, 1),
        "rs_raw": _rs_raw(df),
    }


#: Last-session TURNOVER floor (rupees) for the consolidation-breakout family
#: (6M/1Y/5Y/10Y). Switched from a 100k share count on 2026-09-05 for the same
#: reason as screener_pipeline.MIN_TURNOVER: a share count rejects expensive
#: stocks that trade tens of crores a day. A breakout on MRF would have been
#: dropped for printing 4,656 shares.
#:
#: Still a DIFFERENT measure from the scan floor: it reads the single most recent
#: session, not a 10-day average, because a breakout is a claim about the day it
#: happened — a name that averages well but broke out on nothing is what this
#: rejects. Set at 2x the scan floor, as the share-count version was.
#:
#: It lived as a literal in two places (this family's 6M scan and the shared
#: engine's default), which is how a floor drifts. One name now.
CONSOLIDATION_MIN_TURNOVER = 20_000_000


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

    # Condition 4 — liquidity, as traded value
    if last_close * last_volume < CONSOLIDATION_MIN_TURNOVER:
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
        # Structured copies of the tag numbers — the combined-breakout table
        # renders these as columns instead of parsing tag strings back apart.
        "broke_level": round(prior_126_high, 2),
        "breakout_pct": round((last_close - prior_126_high) / prior_126_high * 100, 1),
        "range_pct": round(consolidation_pct, 1),
        "vol_ratio": round(vol_ratio, 2),
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
    min_turnover: float = CONSOLIDATION_MIN_TURNOVER,
) -> dict | None:
    """Generic multi-timeframe consolidation-breakout engine.

    Args:
        lookback:      Number of trading sessions to look back (252=1Y, 1260=5Y, 2520=10Y).
        label:         Human-readable period label shown in card text.
        max_range_pct: Reject if prior range was wider than this % (prevents trending stocks
                       being flagged as 'consolidating').
        min_turnover:  Minimum last-session traded value (rupees) for the
                       liquidity gate. Value, not share count — see
                       CONSOLIDATION_MIN_TURNOVER.
    """
    if len(df) < lookback + 5:
        return None

    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]

    last_close  = float(close.iloc[-1])
    last_volume = float(volume.iloc[-1])

    if last_close * last_volume < min_turnover:
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
        # Structured copies of the tag numbers — see the 6M scanner's note.
        "broke_level": round(prior_high, 2),
        "breakout_pct": round(breakout_pct, 1),
        "range_pct": round(range_pct, 1),
        "vol_ratio": round(vol_ratio, 2),
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


def scan_all_duration_breakout(df: pd.DataFrame) -> dict | None:
    """Every consolidation-breakout duration in a single pass.

    Tries the longest window first (10Y → 5Y → 1Y → 6M) and reports a stock
    once, at the LONGEST duration whose gates it clears — a 10-year breakout
    by construction also clears the 1-year and 6-month highs, so the longest
    label is the only non-redundant one. ``duration_days`` drives the hub's
    longest-first table sort.
    """
    tiers = [
        (2520, "10-Year", scan_10y_breakout),
        (1260, "5-Year",  scan_5y_breakout),
        (252,  "1-Year",  scan_1y_breakout),
        (126,  "6-Month", scan_6m_consolidation_breakout),
    ]
    for days, label, fn in tiers:
        hit = fn(df)
        if hit:
            hit["duration_days"] = days
            hit["duration_label"] = label
            hit["tags"] = [label, *hit.get("tags", [])]
            return hit
    return None


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
    # The plan is emitted at the TOP LEVEL as well as inside `geometry`, because
    # that is where the measurement harness looks: `backtest.py` reads
    # `hit.get("entry"/"stop"/"target")` and `scanner_plans.has_plan` checks the
    # same three keys. Until this line existed, every Rounding Bottom hit carried
    # a complete entry/stop/target that the R-simulator could not see, and the
    # plan census scored the scanner as planless on 39/39 hits — accurately, in
    # that nothing could be scored from it.
    #
    # Additive, never a move: the chart overlay and /api/rounding_bottom both
    # read the geometry payload, and every existing reader keeps working.
    return {"pattern_type": "Rounding Bottom", "tags": tags,
            "reasons": reasons, "score": score,
            "entry": geometry["entry"],
            "stop": geometry["stop"],
            "target": geometry["target"],
            "geometry": geometry}


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


def _percentr_exhaustion(df: pd.DataFrame, lookback: int = 3) -> dict | None:
    """Port of the %R Trend Exhaustion indicator (see
    percent_r_trend_exhaustion.js — same fast/slow Williams %R + EMA smoothing +
    overbought/oversold zone logic) for bulk Python screening.

    Williams %R runs 0 (top of range) to -100 (bottom). When BOTH the fast and
    slow %R are in the overbought band (>= -threshold) and then LEAVE it, that is
    a top exhaustion → "bearish" (sell); the oversold-zone exit is the mirror →
    "bullish" (bottoming). Returns detail so callers can report the reading:
      {"signal": "bullish"/"bearish"/None, "fast", "slow", "bars_ago"}.
    None only when there is not enough history.
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
    ob_reversal = (~overbought) & overbought.shift(1).fillna(False)   # bearish (top)
    os_reversal = (~oversold) & oversold.shift(1).fillna(False)       # bullish (bottom)

    recent_bear = ob_reversal.tail(lookback)
    recent_bull = os_reversal.tail(lookback)
    has_bear, has_bull = bool(recent_bear.any()), bool(recent_bull.any())
    signal = ("bullish" if (has_bull and not has_bear)
              else "bearish" if (has_bear and not has_bull) else None)

    def _bars_ago(win: pd.Series) -> int | None:
        hits = [i for i, v in enumerate(win.tolist()) if v]
        return (len(win) - 1 - hits[-1]) if hits else None

    return {
        "signal": signal,
        "fast": round(float(fast.iloc[-1]), 1),
        "slow": round(float(slow.iloc[-1]), 1),
        "bars_ago": _bars_ago(recent_bull if signal == "bullish" else recent_bear)
        if signal else None,
    }


def compute_recent_exhaustion_signal(df: pd.DataFrame, lookback: int = 3) -> str | None:
    """Back-compat wrapper: just the "bullish"/"bearish"/None signal."""
    d = _percentr_exhaustion(df, lookback)
    return d["signal"] if d else None


def scan_percentr_exhaustion_sell(df: pd.DataFrame) -> dict | None:
    """Risk scanner — %R Trend Exhaustion SELL. Fires when fast AND slow Williams
    %R both left the OVERBOUGHT band within the last 3 bars: a topping/momentum-
    exhaustion read (exit longs / short-bias), not a with-trend signal. Unmeasured."""
    d = _percentr_exhaustion(df, lookback=3)
    if not d or d.get("signal") != "bearish":
        return None
    close, high = df["close"], df["high"]
    last = float(close.iloc[-1])
    ba = d["bars_ago"]
    when = f"{ba} bar(s) ago" if ba is not None else "within 3 bars"
    reasons = [
        f"%R Trend Exhaustion at the top — fast %R {d['fast']:.0f} & slow %R "
        f"{d['slow']:.0f} left the overbought zone {when} → momentum exhaustion / "
        f"distribution risk."
    ]
    tags = ["%R exhaustion", "Sell signal"]
    sma50 = _sma(close, 50)
    if not np.isnan(sma50):
        reasons.append(
            f"Price {last:.0f} vs SMA50 {sma50:.0f}"
            + (" — still extended above trend (exit / at-risk)" if last > sma50
               else " — already below trend (breakdown risk)"))
    swing_high = round(float(high.tail(10).max()), 2)
    reasons.append(f"Invalidation: a close back above the 10-bar swing high "
                   f"{swing_high:.0f} negates the exhaustion.")
    recent_bonus = {0: 15, 1: 10, 2: 5}.get(ba, 5) if ba is not None else 5
    depth_bonus = max(0.0, (100 + d["fast"]) / 100 * 15)   # closer to 0 = more overbought
    return {
        "pattern_type": "%R Exhaustion Sell",
        "tags": tags,
        "reasons": reasons,
        "score": round(min(100.0, 55 + recent_bonus + depth_bonus), 1),
        "signal": "SELL / reduce",
        "invalidation": swing_high,
    }


def scan_percentr_bottoming(df: pd.DataFrame) -> dict | None:
    """Trend scanner — %R bottomed-out candidate. Mirror of the sell scanner:
    fires when fast AND slow Williams %R both left the OVERSOLD band within the
    last 3 bars, i.e. seller exhaustion / a potential bottom turning up. Carries
    a swing-low-stop / 2R read. Unmeasured — a turn attempt, not a confirmed one."""
    d = _percentr_exhaustion(df, lookback=3)
    if not d or d.get("signal") != "bullish":
        return None
    close, low = df["close"], df["low"]
    last = float(close.iloc[-1])
    ba = d["bars_ago"]
    when = f"{ba} bar(s) ago" if ba is not None else "within 3 bars"
    reasons = [
        f"%R Trend Exhaustion at the bottom — fast %R {d['fast']:.0f} & slow %R "
        f"{d['slow']:.0f} left the oversold zone {when} → seller exhaustion / "
        f"bottoming attempt."
    ]
    tags = ["%R exhaustion", "Bottoming"]
    sma50 = _sma(close, 50)
    reclaim = (not np.isnan(sma50)) and last > sma50
    if not np.isnan(sma50):
        reasons.append(
            f"Price {last:.0f} vs SMA50 {sma50:.0f}"
            + (" — reclaiming trend" if reclaim else " — still below SMA50, early turn"))
    swing_low = round(float(low.tail(10).min()), 2)
    risk = last - swing_low
    target = round(last + 2 * risk, 2) if risk > 0 else None
    reasons.append(f"Trade read: stop below the 10-bar swing low {swing_low:.0f}"
                   + (f", 2R target {target:.0f}." if target else "."))
    recent_bonus = {0: 15, 1: 10, 2: 5}.get(ba, 5) if ba is not None else 5
    return {
        "pattern_type": "%R Bottoming",
        "tags": tags,
        "reasons": reasons,
        "score": round(min(100.0, 55 + recent_bonus + (10 if reclaim else 0)), 1),
        "signal": "BUY / accumulate",
        "entry": round(last, 2),
        "stop": swing_low,
        "target": target,
    }


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


def detect_bullish_rsi_divergence(df: pd.DataFrame, pivot_len: int = 3,
                                  lookback: int = 80) -> bool:
    """Pivot-based bullish RSI divergence — same definition as scan_rsi_divergence_bull.

    Uses Wilder's RSI (via _rsi_series) and swing-pivot lows, not a rolling-mean
    RSI against a raw min.  Returns True when the two most recent pivot lows show
    price lower-low + RSI higher-low with a ≥3-point gap (B-24 fix).
    """
    if len(df) < pivot_len * 2 + 40:
        return False
    close = df["close"]
    low = df["low"]
    n = len(df)
    rsi = _rsi_series(close, 14)

    search_start = max(pivot_len, n - lookback)
    pivot_lows: list[tuple[int, float, float]] = []
    for i in range(search_start, n - pivot_len):
        window = low.iloc[i - pivot_len: i + pivot_len + 1]
        if float(low.iloc[i]) == float(window.min()):
            rsi_val = float(rsi.iloc[i])
            if not np.isnan(rsi_val):
                pivot_lows.append((i, float(low.iloc[i]), rsi_val))

    if len(pivot_lows) < 2:
        return False

    _, price1, rsi1 = pivot_lows[-2]
    _, price2, rsi2 = pivot_lows[-1]

    return bool(price2 < price1 and rsi2 > rsi1 and (rsi2 - rsi1) >= 3.0)


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


def _mfi_series(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Money Flow Index — volume-weighted RSI on typical price (H+L+C)/3.

    Returns a 0-100 Series aligned to df's index.  Needs 'high', 'low',
    'close', 'volume' columns.
    """
    tp = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
    vol = df["volume"].astype(float)
    rmf = tp * vol                                  # raw money flow
    direction = tp.diff()                           # positive when TP rose
    pos_mf = rmf.where(direction > 0, 0.0)
    neg_mf = rmf.where(direction < 0, 0.0)
    pos_sum = pos_mf.rolling(n).sum()
    neg_sum = neg_mf.rolling(n).sum()
    mfr = pos_sum / neg_sum.replace(0.0, np.nan)   # money flow ratio
    return 100.0 - 100.0 / (1.0 + mfr)


def _adx_di_series(df: pd.DataFrame, n: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Wilder's ADX with +DI / -DI directional lines.

    Returns (+DI, -DI, ADX) as three Series aligned to df's index, with NaN
    through the warm-up period (first 2n bars).  All three are 0-100 scaled.
    """
    h, l, c = df["high"].astype(float), df["low"].astype(float), df["close"].astype(float)
    ph, pl = h.shift(1), l.shift(1)
    up_move   = h - ph
    down_move = pl - l
    plus_dm  = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm_s  = pd.Series(plus_dm,  index=df.index, dtype=float)
    minus_dm_s = pd.Series(minus_dm, index=df.index, dtype=float)
    alpha = 1.0 / n
    atr14      = _atr_series(df, n)
    sdm_plus   = plus_dm_s.ewm(alpha=alpha, adjust=False).mean()
    sdm_minus  = minus_dm_s.ewm(alpha=alpha, adjust=False).mean()
    denom = atr14.replace(0.0, np.nan)
    plus_di  = 100.0 * sdm_plus  / denom
    minus_di = 100.0 * sdm_minus / denom
    di_sum  = (plus_di + minus_di).replace(0.0, np.nan)
    dx      = 100.0 * (plus_di - minus_di).abs() / di_sum
    adx     = dx.ewm(alpha=alpha, adjust=False).mean()
    return plus_di, minus_di, adx


def detect_structure_chain(df: pd.DataFrame, pivot_len: int = 15,
                           confirm: str = "close", fail_win: int = 3,
                           max_swings: int = 15) -> dict | None:
    """Full market-structure break chain — port of the Structure Break Chain [SBC]
    Pine indicator (© SharpStrat, MPL 2.0; see sources/Structure-Break-Chain-SBC-Pine.md
    and concepts/Market-Structure-CHOCH-BOS.md).

    Where `detect_bos_choch` returns only the latest surviving *bullish* event, this
    walks the whole series and returns **every** structural break in both directions
    with the three gradings SBC contributes:

      * quality  — 0.6 x (distance beyond the level / ATR14)
                 + 0.4 x (|close - open| / ATR14)  ->  STRONG >= 0.75,
                   NORMAL >= 0.35, else WEAK. ATR-normalised, so the thresholds
                   travel across symbols and timeframes.
      * chain    — consecutive same-direction breaks since the last CHOCH. A CHOCH
                   resets it to 1; each following BOS increments. The reset *is* the
                   character change.
      * failed   — price closed back inside the broken level within `fail_win` bars.
                   Always close-tested (as in the source) even when `confirm="wick"`,
                   and never on the break bar itself. fail_win=0 disables the check.

    Faithful to the source: one structural event per bar with bullish priority, the
    broken level is consumed until a fresh pivot forms, and completed-chain averages
    accumulate only at CHOCH events (so the in-progress chain is excluded).

    Deliberate difference: pivots reuse this module's window-max rule (as in
    `detect_bos_choch`) rather than Pine's strict comparison, so a flat plateau can
    register as a pivot. Immaterial on real data, but it is not a byte-for-byte port.

    Returns None when there is not enough history, else:
      {"events": [...], "swings": [...], "stats": {...}}
    with bar *indices* (the caller maps them to timestamps).
    """
    if confirm not in ("close", "wick"):
        confirm = "close"
    need = pivot_len * 2 + 20
    if df is None or len(df) < need:
        return None

    high, low, close, open_ = df["high"], df["low"], df["close"], df["open"]
    atr = _atr_series(df).fillna(0.0)
    n = len(df)

    def _qual(dist: float, i: int) -> tuple[str, float]:
        a = max(float(atr.iloc[i]), 1e-6)
        s = (dist / a) * 0.6 + (abs(float(close.iloc[i]) - float(open_.iloc[i])) / a) * 0.4
        return ("STRONG" if s >= 0.75 else "NORMAL" if s >= 0.35 else "WEAK"), round(s, 2)

    sh: float | None = None            # live (unbroken) swing high
    sh_bar: int | None = None
    sl: float | None = None
    sl_bar: int | None = None
    swings: list[dict] = []

    trend = 0                          # 1 up / -1 down / 0 unknown
    chain = 0
    events: list[dict] = []
    tot_bos = tot_choch = max_chain = n_chains = 0
    sum_chains = 0.0

    watch: dict | None = None          # armed failure watch for the last break

    for i in range(pivot_len, n):
        # ── pivot confirmation (a pivot at j is only knowable pivot_len bars later)
        j = i - pivot_len
        if j >= pivot_len:
            win_hi = high.iloc[j - pivot_len: j + pivot_len + 1]
            win_lo = low.iloc[j - pivot_len: j + pivot_len + 1]
            if float(high.iloc[j]) == float(win_hi.max()):
                sh, sh_bar = float(high.iloc[j]), j
                swings.append({"bar": j, "level": round(sh, 2), "kind": "high"})
            if float(low.iloc[j]) == float(win_lo.min()):
                sl, sl_bar = float(low.iloc[j]), j
                swings.append({"bar": j, "level": round(sl, 2), "kind": "low"})

        ref_hi = float(close.iloc[i]) if confirm == "close" else float(high.iloc[i])
        ref_lo = float(close.iloc[i]) if confirm == "close" else float(low.iloc[i])
        chain_before = chain
        event = None

        # ── bullish break (takes precedence on ties, as in the source) ──
        if sh is not None and ref_hi > sh:
            kind, score = _qual(ref_hi - sh, i)
            if trend == -1:
                label, chain = "CHOCH", 1
                tot_choch += 1
                if chain_before > 0:
                    n_chains += 1
                    sum_chains += chain_before
            else:
                label = "BOS"
                chain = 1 if trend == 0 else chain + 1
                tot_bos += 1
            event = {"bar": i, "type": label, "direction": "up", "level": round(sh, 2),
                     "pivot_bar": sh_bar, "quality": kind, "score": score, "chain": chain}
            trend = 1
            sh, sh_bar = None, None      # level consumed

        # ── bearish break (only if no bullish event fired on this bar) ──
        elif sl is not None and ref_lo < sl:
            kind, score = _qual(sl - ref_lo, i)
            if trend == 1:
                label, chain = "CHOCH", 1
                tot_choch += 1
                if chain_before > 0:
                    n_chains += 1
                    sum_chains += chain_before
            else:
                label = "BOS"
                chain = 1 if trend == 0 else chain + 1
                tot_bos += 1
            event = {"bar": i, "type": label, "direction": "down", "level": round(sl, 2),
                     "pivot_bar": sl_bar, "quality": kind, "score": score, "chain": chain}
            trend = -1
            sl, sl_bar = None, None

        if event is not None:
            event["failed"] = False
            event["failed_bar"] = None
            events.append(event)
            max_chain = max(max_chain, chain)
            watch = ({"level": event["level"], "dir": 1 if event["direction"] == "up" else -1,
                      "bar": i, "idx": len(events) - 1} if fail_win > 0 else None)
            continue                     # failure is never tested on the break bar

        # ── failed-break watch (only on bars that produced no new event) ──
        if watch is not None:
            elapsed = i - watch["bar"]
            c = float(close.iloc[i])
            if 0 < elapsed <= fail_win:
                broke_back = (c < watch["level"]) if watch["dir"] == 1 else (c > watch["level"])
                if broke_back:
                    events[watch["idx"]]["failed"] = True
                    events[watch["idx"]]["failed_bar"] = i
                    watch = None
            elif elapsed > fail_win:
                watch = None

    if not events:
        return None

    last = events[-1]
    return {
        "events": events,
        # Only the most recent pivots are returned — the chart draws one line each.
        "swings": swings[-max_swings:] if max_swings > 0 else [],
        "live_swing_high": round(sh, 2) if sh is not None else None,
        "live_swing_low": round(sl, 2) if sl is not None else None,
        "stats": {
            "trend": trend,
            "chain": chain,
            "max_chain": max_chain,
            "avg_chain": round(sum_chains / n_chains, 1) if n_chains else None,
            "completed_chains": n_chains,
            "total_bos": tot_bos,
            "total_choch": tot_choch,
            "failed_count": sum(1 for e in events if e["failed"]),
            "last_quality": last["quality"],
            "last_type": last["type"],
            "last_bars_ago": n - 1 - last["bar"],
            "pivot_len": pivot_len,
            "confirm": confirm,
            "fail_win": fail_win,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# B-42 · Shared market-structure read
#
# `detect_structure_chain` (above) walks the breaks; `detect_bos_choch` returns
# the latest bullish one. Neither labels the *sequence* — HH/HL/LH/LL — which is
# what a swing trader reads first and every entry hangs off. These two functions
# add that layer on top of the existing walk, additively: no existing detector
# changes behaviour, and `read_market_structure` is the one primitive a consumer
# should call when it wants "what is structure doing right now".
#
# B-42r, MEASURED 2026-09-17 (`pivot_len_agreement.py`, 199 nifty500 names):
# `detect_bos_choch`/`detect_support_breakdown` default to pivot_len=5 while
# `detect_structure_chain`, `read_market_structure` and the chart overlay use 15,
# and the two readings AGREE ON `state` ONLY 29.6% OF THE TIME.
#
#     agree on state               29.6%
#     agree on agreement           35.2%
#     agree on zone                57.3%
#     agree on trend_from_breaks   68.3%
#     median |zone_pct| gap        42.5 pp
#
# The largest single disagreement is DOWNTREND (scanners) against UPTREND
# (chart) on 17.6% of names — not coarser, OPPOSITE. So this was never a tidying
# question: the chart and the scanners describe different structures, and a
# reader comparing them is comparing two definitions under one word.
#
# Still deliberately NOT unified. Changing either default silently re-grades live
# output (the B-26 lesson), and at 29.6% agreement the change would move most
# names — which makes it an OWNER decision about what "structure" means at each
# timeframe, not a default to tidy. Every read carries its own `params.pivot_len`,
# so a consumer can always say which definition produced the word.
# ─────────────────────────────────────────────────────────────────────────────

def label_swing_sequence(swings: list[dict], tol_pct: float = 0.0) -> list[dict]:
    """Label each swing against the prior swing of the SAME kind.

    highs -> "HH" (higher high) / "LH" (lower high) / "EQH" (equal, within tol)
    lows  -> "HL" (higher low)  / "LL" (lower low)  / "EQL"

    The first swing of each kind has no predecessor and is labelled None. Input
    is the `swings` list from `detect_structure_chain` ({"bar", "level", "kind"});
    returns new dicts (input is not mutated) with "label" and "prev_level" added.

    `tol_pct` treats near-equal levels as equal — an equal-highs/lows cluster is
    a liquidity pool rather than a trend step (B-41's raw material). Default 0.0
    keeps the classification strict.
    """
    out: list[dict] = []
    prev: dict[str, float] = {}
    for idx, s in enumerate(swings):
        kind = s.get("kind")
        lvl = s.get("level")
        d = dict(s)
        # A flat plateau registers once per bar in `detect_structure_chain`, so a
        # single real swing can arrive as several identical entries. Collapsing
        # them keeps the sequence describing the market rather than the sampling:
        # left in, every trend read degrades to EQH/EQL on plateau-y tapes.
        if (out and out[-1].get("kind") == kind
                and isinstance(lvl, (int, float))
                and out[-1].get("level") == lvl):
            d["label"] = None
            d["prev_level"] = None
            d["duplicate_of"] = out[-1].get("bar")
            out.append(d)
            continue
        d["label"] = None
        d["prev_level"] = None
        if kind in ("high", "low") and isinstance(lvl, (int, float)):
            p = prev.get(kind)
            if p is not None:
                d["prev_level"] = p
                tol = abs(p) * (tol_pct / 100.0)
                if abs(lvl - p) <= tol:
                    d["label"] = "EQH" if kind == "high" else "EQL"
                elif lvl > p:
                    d["label"] = "HH" if kind == "high" else "HL"
                else:
                    d["label"] = "LH" if kind == "high" else "LL"
            prev[kind] = float(lvl)
        out.append(d)
    return out


def _verify_swing_sequence(labelled: list[dict], tol_pct: float = 0.0) -> dict:
    """The B-42 invariant: every label must reconcile to the pivots it came from.

    Re-derives each label from its own `prev_level` and reports any mismatch.
    A structure read that cannot pass this is not trustworthy as shared context.
    """
    violations: list[str] = []
    for s in labelled:
        lab, lvl, p, kind = s.get("label"), s.get("level"), s.get("prev_level"), s.get("kind")
        if lab is None or p is None:
            continue
        tol = abs(p) * (tol_pct / 100.0)
        if abs(lvl - p) <= tol:
            expect = "EQH" if kind == "high" else "EQL"
        elif lvl > p:
            expect = "HH" if kind == "high" else "HL"
        else:
            expect = "LH" if kind == "high" else "LL"
        if expect != lab:
            violations.append(f"bar {s.get('bar')}: labelled {lab}, pivots imply {expect}")
    return {"ok": not violations, "violations": violations}


def read_market_structure(df: pd.DataFrame, pivot_len: int = 15,
                          confirm: str = "close", fail_win: int = 3,
                          max_swings: int = 15,
                          eq_tol_pct: float = 0.0,
                          chain: dict | None = None) -> dict | None:
    """First-class market-structure state — the shared read B-42 asks for.

    Composes the existing `detect_structure_chain` walk with HH/HL/LH/LL sequence
    labelling and a premium/discount location, so every consumer means the same
    thing by "structure". Purely additive: it calls the existing engine and does
    not alter it.

    state is derived from the last high-label and last low-label together:
      UPTREND     HH + HL   — both ends rising
      DOWNTREND   LH + LL   — both ends falling
      RANGE       LH + HL   — contracting, lower highs into higher lows
      BROADENING  HH + LL   — expanding, both ends widening
      TRANSITION  anything involving an equal high/low, or only one side known
      UNKNOWN     not enough labelled swings to say

    `agreement` compares that sequence read against the break-derived trend:
    CONFIRMED (both agree), DIVERGING (they disagree — the sequence lags pivot
    confirmation, so a fresh CHOCH against a still-intact sequence is the
    earliest warning structure is turning), or UNDECIDED (either side neutral).

    `zone` locates the last close inside the most recent swing-high/swing-low
    band (the SMC premium/discount read): PREMIUM >70%, DISCOUNT <30%, else
    EQUILIBRIUM. None when the band cannot be established.

    Pass `chain` to reuse a `detect_structure_chain` result you already have
    (the chart endpoint does) instead of walking the series a second time; the
    pivot_len/confirm/fail_win args are then only echoed back in `params`, so
    they must match how that chain was built.

    Returns None when there is not enough history for the underlying walk.
    """
    if chain is None:
        chain = detect_structure_chain(df, pivot_len=pivot_len, confirm=confirm,
                                       fail_win=fail_win, max_swings=max_swings)
    if chain is None:
        return None

    labelled = label_swing_sequence(chain.get("swings") or [], tol_pct=eq_tol_pct)
    invariant = _verify_swing_sequence(labelled, tol_pct=eq_tol_pct)

    last_high = next((s for s in reversed(labelled)
                      if s["kind"] == "high" and s["label"]), None)
    last_low = next((s for s in reversed(labelled)
                     if s["kind"] == "low" and s["label"]), None)
    hl = last_high["label"] if last_high else None
    ll = last_low["label"] if last_low else None

    if hl == "HH" and ll == "HL":
        state = "UPTREND"
    elif hl == "LH" and ll == "LL":
        state = "DOWNTREND"
    elif hl == "LH" and ll == "HL":
        state = "RANGE"
    elif hl == "HH" and ll == "LL":
        state = "BROADENING"
    elif hl is None and ll is None:
        state = "UNKNOWN"
    else:
        state = "TRANSITION"

    # Premium/discount inside the live swing band. Fall back to the most recent
    # pivot of each kind when a side has already been consumed by a break — the
    # FIRST pivot of a kind carries no label, so this must not filter on one.
    hi = chain.get("live_swing_high")
    lo = chain.get("live_swing_low")
    last_hi_pivot = next((s for s in reversed(labelled)
                          if s["kind"] == "high" and "duplicate_of" not in s), None)
    last_lo_pivot = next((s for s in reversed(labelled)
                          if s["kind"] == "low" and "duplicate_of" not in s), None)
    if hi is None and last_hi_pivot:
        hi = last_hi_pivot["level"]
    if lo is None and last_lo_pivot:
        lo = last_lo_pivot["level"]
    zone = None
    zone_pct = None
    if hi is not None and lo is not None and hi > lo:
        c = float(df["close"].iloc[-1])
        pos = (c - lo) / (hi - lo)
        # Not clamped on purpose: >100 or <0 means price has left the band its
        # last pivots defined, which is breakout/breakdown information, not an
        # error. Callers wanting a bounded gauge should clamp at the edge.
        zone_pct = round(pos * 100, 1)
        zone = "PREMIUM" if pos > 0.7 else "DISCOUNT" if pos < 0.3 else "EQUILIBRIUM"

    stats = chain.get("stats", {})
    events = chain.get("events") or []
    last_ev = events[-1] if events else None

    # The swing sequence lags (a pivot needs pivot_len bars to confirm) while a
    # break prints immediately, so the two reads can disagree — an UPTREND
    # sequence under a fresh CHOCH down is a character change the sequence has
    # not caught up to yet. Surfacing the disagreement is the point: it is the
    # earliest honest warning the structure is turning.
    brk = stats.get("trend")
    seq_dir = 1 if state == "UPTREND" else -1 if state == "DOWNTREND" else 0
    if seq_dir == 0 or brk in (0, None):
        agreement = "UNDECIDED"
    elif seq_dir == brk:
        agreement = "CONFIRMED"
    else:
        agreement = "DIVERGING"

    return {
        "state": state,
        "agreement": agreement,
        "last_high_label": hl,
        "last_low_label": ll,
        "sequence": [s["label"] for s in labelled if s["label"]],
        "swings": labelled,
        "zone": zone,
        "zone_pct": zone_pct,
        "swing_high": hi,
        "swing_low": lo,
        "last_event": ({"type": last_ev["type"], "direction": last_ev["direction"],
                        "level": last_ev["level"], "quality": last_ev["quality"],
                        "chain": last_ev["chain"], "failed": last_ev["failed"],
                        "bars_ago": stats.get("last_bars_ago")}
                       if last_ev else None),
        "trend_from_breaks": stats.get("trend"),
        "invariant_ok": invariant["ok"],
        "invariant_violations": invariant["violations"],
        "params": {"pivot_len": pivot_len, "confirm": confirm,
                   "fail_win": fail_win, "eq_tol_pct": eq_tol_pct},
    }


# ─────────────────────────────────────────────────────────────────────────────
# B-41 · Liquidity sweeps (stop hunts) — the missing third of the SMC stack
#
# We ship FVG Pullback, Order Block Retest and ICT Setup, but not the event that
# VALIDATES them: an equal-highs/lows pool where stops rest, run by a wick, then
# reclaimed. Built on B-42's labelled swings — the equal-level clustering is what
# `eq_tol_pct` was added for.
#
# Distinct from B-19b `detect_support_breakdown`, and the distinction is the
# whole point: a breakdown CLOSES beyond the level (a real break); a sweep pokes
# through on the wick and closes back INSIDE (a false break that reverses).
#
# That exclusivity is PER LEVEL, not global — a single bar can legitimately sweep
# a pool below it while still closing under a higher swing low, so both detectors
# firing on the same bar is coherent rather than contradictory (measured: 1 of 49
# NSE large-caps, ULTRACEMCO, closing above its 11254 pool and below its 11396
# swing low). Only "swept and reclaimed level X" and "closed below level X" are
# mutually exclusive.
#
# Also distinct from the JS `session_volume_profile.js` sweep (line ~345), which
# compares the CURRENT session's extreme against the PRIOR session's — an
# intraday, two-bar-of-sessions read. This one is a multi-touch pool on daily
# swing pivots. Two different claims that share a name; recorded so nobody
# assumes they agree (the B-24 lesson).
# ─────────────────────────────────────────────────────────────────────────────

MIN_SWEEP_RR = 1.0   # a pool nearer than this many R is not worth targeting


def detect_liquidity_pools(df: pd.DataFrame, pivot_len: int = 5,
                           eq_tol_pct: float = 0.75, min_touches: int = 2,
                           max_pools: int = 6,
                           min_separation: int | None = None) -> list[dict]:
    """Equal-highs / equal-lows clusters — where resting stops pool up.

    Clusters same-kind swing pivots **by level, across the whole window** — not
    only consecutive ones. A pool is price revisiting a level, and the revisits
    are normally interrupted: a low at 90, a rally, a low at 95, a rally, then 90
    again is a textbook double bottom, and grouping only adjacent pivots would
    miss it because the 95 breaks the run.

    Membership is tested against the cluster ANCHOR rather than pairwise, since
    chaining pairwise equality lets a "pool" drift arbitrarily far from where it
    started while every adjacent pair still looks equal.

    Touches must be at least `min_separation` bars apart (default `pivot_len * 2`,
    the narrowest spacing at which two pivots can independently confirm). Without
    it a single flat shelf reads as many touches, which would overstate how much
    stop liquidity has actually accumulated.

    The pool's `level` is the extreme of its members — the low of an equal-lows
    cluster, the high of an equal-highs cluster — because that is the edge stops
    sit beyond and therefore the price that must be pierced.

    Returns pools newest-first, each:
      {"kind": "high"|"low", "level", "touches", "bars", "first_bar", "last_bar",
       "width_pct"}
    """
    if df is None or len(df) < pivot_len * 2 + 20:
        return []
    if min_separation is None:
        min_separation = pivot_len * 2
    # A generous max_swings on purpose: the chart only needs the drawable tail,
    # but a pool search must see enough history for a cluster to form.
    chain = detect_structure_chain(df, pivot_len=pivot_len, max_swings=200)
    if chain is None:
        return []
    labelled = label_swing_sequence(chain.get("swings") or [], tol_pct=eq_tol_pct)

    pools: list[dict] = []
    for kind in ("high", "low"):
        members = [s for s in labelled
                   if s.get("kind") == kind and "duplicate_of" not in s
                   and isinstance(s.get("level"), (int, float))]
        if len(members) < min_touches:
            continue

        def _cluster(anchor_level: float, pool: list[dict]) -> list[dict]:
            """Members within tolerance of the anchor, thinned to one per
            `min_separation` window so a shelf counts once.

            The whole cluster must also SPAN no more than one tolerance band.
            Distance-from-anchor alone still admits a group twice that wide (one
            member a full tol below the anchor, another a full tol above), and a
            pool that wide is not "equal" lows in any useful sense.
            """
            tol = abs(anchor_level) * (eq_tol_pct / 100.0)
            near = [m for m in pool if abs(float(m["level"]) - anchor_level) <= tol]
            near.sort(key=lambda m: m["bar"])
            kept: list[dict] = []
            for m in near:
                if kept and (m["bar"] - kept[-1]["bar"]) < min_separation:
                    continue
                lv = [float(g["level"]) for g in kept] + [float(m["level"])]
                if max(lv) - min(lv) > tol:
                    continue
                kept.append(m)
            return kept

        # Greedy: take the richest cluster available, consume it, repeat. Sorting
        # candidates by touch count first means a strong pool is not fragmented
        # by an arbitrary starting anchor.
        remaining = list(members)
        while len(remaining) >= min_touches:
            best: list[dict] | None = None
            for m in remaining:
                cand = _cluster(float(m["level"]), remaining)
                if best is None or len(cand) > len(best) or (
                        len(cand) == len(best) and cand[-1]["bar"] > best[-1]["bar"]):
                    best = cand
            if best is None or len(best) < min_touches:
                break
            lv = [float(g["level"]) for g in best]
            anchor = lv[0]
            level = min(lv) if kind == "low" else max(lv)
            pools.append({
                "kind": kind,
                "level": round(level, 2),
                "touches": len(best),
                "bars": [g["bar"] for g in best],
                "first_bar": best[0]["bar"],
                "last_bar": best[-1]["bar"],
                "width_pct": round((max(lv) - min(lv)) / max(abs(anchor), 1e-9) * 100, 3),
            })
            used = {id(g) for g in best}
            remaining = [m for m in remaining if id(m) not in used]

    pools.sort(key=lambda p: p["last_bar"], reverse=True)
    return pools[:max_pools] if max_pools > 0 else pools


def detect_liquidity_sweep(df: pd.DataFrame, pivot_len: int = 5,
                           eq_tol_pct: float = 0.75, min_touches: int = 2,
                           lookback: int = 40, min_wick_ratio: float = 0.5,
                           min_pierce_atr: float = 0.05,
                           max_pierce_atr: float = 2.0) -> dict | None:
    """Most recent sweep-and-reclaim of a liquidity pool, either direction.

    A qualifying bar must, against a pool formed BEFORE it:
      1. pierce the pool level on the wick — `low < level` (sell-side pool) or
         `high > level` (buy-side), by between `min_pierce_atr` and
         `max_pierce_atr` ATR. The floor rejects a meaningless graze; the
         ceiling rejects a genuine break that simply kept going.
      2. close back INSIDE — above the level for a low pool, below it for a
         high pool. This is what separates a sweep from a breakdown/breakout.
      3. show a dominant rejection wick — the wick beyond the level is at least
         `min_wick_ratio` of the bar's full range.

    Returns the most recent qualifying event, or None:
      {"direction": "bullish"|"bearish", "level", "touches", "bars_ago",
       "pierce_atr", "wick_ratio", "close", "reclaimed", "pool_width_pct"}

    "bullish" = a SELL-side pool (equal lows) was swept and reclaimed, i.e. the
    stop hunt was downward and the reversal is up.
    """
    if df is None or len(df) < pivot_len * 2 + 25:
        return None
    d = _clean_ohlc(df)
    if len(d) < pivot_len * 2 + 25:
        return None
    pools = detect_liquidity_pools(d, pivot_len=pivot_len, eq_tol_pct=eq_tol_pct,
                                   min_touches=min_touches, max_pools=0)
    if not pools:
        return None

    atr = _atr_series(d, 14)
    n = len(d)
    high, low, close = d["high"], d["low"], d["close"]
    start = max(pivot_len, n - lookback)

    best: dict | None = None
    for i in range(start, n):
        a = float(atr.iloc[i]) if not pd.isna(atr.iloc[i]) else 0.0
        if a <= 0:
            continue
        hi, lo, c = float(high.iloc[i]), float(low.iloc[i]), float(close.iloc[i])
        o = float(d["open"].iloc[i])
        rng = hi - lo
        if rng <= 0:
            continue
        # The rejection wick is the bar's SHADOW beyond its body — the standard
        # reading. Measuring only the part below the pool level instead would
        # report a fraction of the true rejection and reject real sweeps.
        lower_wick = (min(o, c) - lo) / rng
        upper_wick = (hi - max(o, c)) / rng
        for p in pools:
            # The pool must be fully formed before the bar that sweeps it.
            if p["last_bar"] >= i:
                continue
            lvl = p["level"]
            if p["kind"] == "low":
                pierce = lvl - lo
                if pierce <= 0 or c <= lvl:
                    continue
                wick = lower_wick
                direction = "bullish"
            else:
                pierce = hi - lvl
                if pierce <= 0 or c >= lvl:
                    continue
                wick = upper_wick
                direction = "bearish"
            pierce_atr = pierce / a
            if not (min_pierce_atr <= pierce_atr <= max_pierce_atr):
                continue
            if wick < min_wick_ratio:
                continue
            best = {
                "direction": direction,
                "level": lvl,
                "touches": p["touches"],
                "bars_ago": n - 1 - i,
                "pierce_atr": round(pierce_atr, 2),
                "wick_ratio": round(wick, 2),
                "close": round(c, 2),
                "reclaimed": True,
                "pool_width_pct": p["width_pct"],
                "pool_bars": p["bars"],
            }
    return best


def _displacement_body_ratio(o: float, h: float, l: float, c: float) -> float:
    """Body as a fraction of total range. Used by the ICT displacement gate."""
    rng = h - l
    return abs(c - o) / rng if rng > 0 else 0.0


def _ote_zone(leg_start: float, leg_end: float, direction: str) -> tuple[float, float]:
    """ICT Optimal Trade Entry zone: 61.8%–79% retracement of a displacement leg.

    direction='bullish': leg went UP (leg_start < leg_end); OTE is below leg_end.
    direction='bearish': leg went DOWN (leg_start > leg_end); OTE is above leg_end.

    Returns (ote_lo, ote_hi) where ote_lo < ote_hi always, ready to compare
    against current price.
    """
    span = abs(leg_end - leg_start)
    if direction == "bullish":
        return (round(leg_end - 0.786 * span, 2), round(leg_end - 0.618 * span, 2))
    else:
        return (round(leg_end + 0.618 * span, 2), round(leg_end + 0.786 * span, 2))


def detect_bos_choch(df: pd.DataFrame, pivot_len: int = 5,
                     lookback: int = 120,
                     require_displacement: bool = False,
                     min_body_ratio: float = 0.5) -> dict | None:
    """Bullish market-structure event (SMC swing-labeling walk): a close above
    the most recent confirmed swing high while structure is bearish = CHOCH
    (first counter-trend break); while already bullish = BOS (continuation).
    A later close below a confirmed swing low re-flips structure bearish and
    invalidates the bullish event. Returns the surviving bullish event or None.

    When require_displacement=True (ICT mode), the break candle must have a
    body that is at least min_body_ratio of its full high-low range, filtering
    out soft, low-conviction closes that just edge past the pivot.

    Extra keys when displacement was measured:
      displacement (bool) — whether the break candle met the body-ratio gate
      body_ratio  (float) — actual body/range of the break candle
      leg_start   (float) — swing low before the break (OTE calculation anchor)
      leg_end     (float) — the swing-high level that was broken (OTE top anchor)
      ote_zone    (float, float) — (ote_lo, ote_hi) = 61.8–79% retracement band
    """
    if len(df) < pivot_len * 4 + 20:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    opens = df["open"]
    n = len(df)

    swing_high: float | None = None
    swing_low: float | None = None
    trend = 0            # 1 up / -1 down / 0 unknown
    last_event: tuple[str, int, float, float | None, float | None] | None = None
    # last_event = (label, bar_idx, level, leg_start_swing_low, body_ratio)

    for i in range(max(pivot_len * 2, n - lookback), n):
        j = i - pivot_len          # pivot confirmed pivot_len bars later
        if j >= pivot_len:
            if high.iloc[j] == high.iloc[j - pivot_len: j + pivot_len + 1].max():
                swing_high = float(high.iloc[j])
            if low.iloc[j] == low.iloc[j - pivot_len: j + pivot_len + 1].min():
                swing_low = float(low.iloc[j])
        c = float(close.iloc[i])
        if swing_high is not None and c > swing_high:
            br = _displacement_body_ratio(
                float(opens.iloc[i]), float(high.iloc[i]),
                float(low.iloc[i]), c,
            )
            if require_displacement and br < min_body_ratio:
                # Soft close — skip but do NOT consume the swing_high; a later
                # stronger bar on the same level can still qualify.
                pass
            else:
                last_event = ("BOS" if trend == 1 else "CHOCH", i, swing_high, swing_low, br)
                trend = 1
                swing_high = None      # consumed — wait for a fresh pivot
        elif swing_low is not None and c < swing_low:
            trend = -1
            swing_low = None
            last_event = None      # bearish break invalidates the bullish event

    if last_event is None:
        return None
    label, idx, level, leg_start, body_ratio = last_event
    ote = _ote_zone(leg_start, level, "bullish") if leg_start is not None else None
    return {
        "signal": label,
        "level": round(level, 2),
        "bars_ago": n - 1 - idx,
        "displacement": (body_ratio or 0.0) >= min_body_ratio,
        "body_ratio": round(body_ratio, 3) if body_ratio is not None else None,
        "leg_start": round(leg_start, 2) if leg_start is not None else None,
        "leg_end": round(level, 2),
        "ote_zone": ote,
    }


def detect_support_breakdown(df: pd.DataFrame, pivot_len: int = 5,
                             lookback: int = 120,
                             require_displacement: bool = False,
                             min_body_ratio: float = 0.5) -> dict | None:
    """Bearish market-structure event (B-19b): a close BELOW the most recent
    confirmed swing LOW while structure is bullish = bearish CHOCH (first
    counter-trend break); while already bearish = bearish BOS (continuation).
    The mirror-image of ``detect_bos_choch`` — same walk, opposite direction.

    Returns the surviving bearish event or None (no bearish break in the window,
    or a later bullish break invalidated it).

    When require_displacement=True (ICT mode), the break candle must have a
    body of at least min_body_ratio of its range (same gate as detect_bos_choch).

    Extra keys: displacement, body_ratio, leg_start (swing high before break),
    leg_end (swing low broken), ote_zone (61.8–79% retracement back up).
    """
    if len(df) < pivot_len * 4 + 20:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    opens = df["open"]
    n = len(df)

    swing_high: float | None = None
    swing_low: float | None = None
    trend = 0           # 1 up / -1 down / 0 unknown
    last_event: tuple[str, int, float, float | None, float | None] | None = None

    for i in range(max(pivot_len * 2, n - lookback), n):
        j = i - pivot_len
        if j >= pivot_len:
            if high.iloc[j] == high.iloc[j - pivot_len: j + pivot_len + 1].max():
                swing_high = float(high.iloc[j])
            if low.iloc[j] == low.iloc[j - pivot_len: j + pivot_len + 1].min():
                swing_low = float(low.iloc[j])
        c = float(close.iloc[i])
        if swing_low is not None and c < swing_low:
            br = _displacement_body_ratio(
                float(opens.iloc[i]), float(high.iloc[i]),
                float(low.iloc[i]), c,
            )
            if require_displacement and br < min_body_ratio:
                pass  # soft close — wait for a stronger candle on this level
            else:
                last_event = ("bearish BOS" if trend == -1 else "bearish CHOCH", i, swing_low, swing_high, br)
                trend = -1
                swing_low = None   # consumed
        elif swing_high is not None and c > swing_high:
            trend = 1
            swing_high = None
            last_event = None  # bullish break invalidates the bearish event

    if last_event is None:
        return None
    label, idx, level, leg_start, body_ratio = last_event
    ote = _ote_zone(leg_start, level, "bearish") if leg_start is not None else None
    return {
        "signal": label,
        "level": round(level, 2),
        "bars_ago": n - 1 - idx,
        "displacement": (body_ratio or 0.0) >= min_body_ratio,
        "body_ratio": round(body_ratio, 3) if body_ratio is not None else None,
        "leg_start": round(leg_start, 2) if leg_start is not None else None,
        "leg_end": round(level, 2),
        "ote_zone": ote,
    }


def scan_support_breakdown(df: pd.DataFrame) -> dict | None:
    """Bearish support breakdown — the structural bearish mirror of Order Block
    Retest (B-19b).

    Fires when:
      1. ``detect_support_breakdown`` confirms a bearish BOS or CHOCH in the
         last ~10 bars (structure is cracking, not just a random down-day).
      2. Price has since pulled back into the broken support (now resistance) —
         the "retest of the breakdown level from below" entry confirmation.
      3. Price closed back below that level on the current bar (failed retest),
         adding the bearish volume/OI confirmation the completeness audit wanted.
      4. Volume expansion is present (down-day on > 1× 20-day average volume).

    This scanner is a **Risk** entry — it is evidence AGAINST a long and a
    potential short-side setup, not a buy signal. Carries entry/stop/target
    for the short side (stop above the breakdown level, target = measured move
    down from the structure break).
    """
    if df is None or len(df) < 60:
        return None
    df = _clean_ohlc(df)
    if len(df) < 60:
        return None

    ev = detect_support_breakdown(df)
    if ev is None:
        return None

    n = len(df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    atr = float(_atr_series(df, 14).iloc[-1])
    if np.isnan(atr) or atr <= 0:
        return None

    bk_level = ev["level"]      # the broken swing low (now resistance)
    last = float(c.iloc[-1])
    last_high = float(h.iloc[-1])

    # Require price to be AT or below the broken level (not already far extended)
    if last > bk_level * 1.02:  # allow 2% tolerance for wicks
        return None

    # "Retest from below" — the bar touched the level and closed back under it
    retest = bool(last_high >= bk_level * 0.98 and last < bk_level)
    if not retest:
        return None

    vol20 = float(df["volume"].tail(20).mean())
    vol_last = float(df["volume"].iloc[-1])
    vol_x = vol_last / vol20 if vol20 > 0 else 0.0
    vol_ok = vol_x >= 1.0

    entry = last
    stop = round(bk_level * 1.005, 2)   # just above the breakdown level
    risk = stop - entry
    if risk <= 0:
        return None

    # Measured-move target: distance of the most recent swing-high above the
    # breakdown level projected down.
    swing_high_val = float(h.iloc[max(0, n - 60): n].max())
    measured_dist = max(swing_high_val - bk_level, atr * 2)
    target = round(entry - measured_dist, 2)

    reasons = [
        f"Bearish {ev['signal']} — structure cracked below ₹{bk_level:.0f}, "
        f"{ev['bars_ago']} bars ago",
        f"Retest of the breakdown level (now resistance) from below — failed to reclaim ₹{bk_level:.0f}",
        (f"Volume {vol_x:.1f}× 20-day average — distribution on the retest"
         if vol_ok else
         "⚠ Volume weak on the retest — conviction limited"),
        f"Short plan — entry {entry:.0f} · stop {stop:.0f} · target {target:.0f} "
        f"(R:R {(entry - target) / risk:.1f})",
    ]
    score = 30.0 + (25.0 if vol_ok else 0.0) + (20.0 if retest else 0.0)
    score += min(15.0, vol_x * 5.0)

    return {
        "pattern_type": f"Support Breakdown · {ev['signal']}",
        "tags": ["Breakdown", ev["signal"], f"Level {bk_level:.0f}",
                 "Vol ✓" if vol_ok else "Vol ✗"],
        "reasons": reasons,
        "score_base": round(min(100.0, score), 1),
        "rs_raw": _rs_raw(df),
        "entry": round(entry, 2),
        "stop": stop,
        "target": target,
        "vol_x50d": round(vol_x, 2),
        # B-5: breakdown retests resolve quickly — 8 bars is the expected window
        "time_stop": 8,
    }


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
    # The zone a signal fired FROM. The state machine consumes the zone on the
    # signal, so without capturing it here a caller can know a rejection
    # happened but not where its stop belongs — which is why `scan_fvg_pullback`
    # could not emit a trade plan. Additive: existing callers read only the
    # *_bars_ago / recent keys.
    last_buy_zone = last_sell_zone = None

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
                last_buy_zone = (bull_bot, bull_top)
                bull_top = bull_bot = None
        if bear_top is not None:
            touch = bear_bot <= h0 <= bear_top
            reject = c0 < bear_bot and (h0 - c0) > (c0 - l0)
            if touch and reject and o0 < bear_bot:
                last_sell = i
                last_sell_zone = (bear_bot, bear_top)
                bear_top = bear_bot = None

    if last_buy is None and last_sell is None and bull_top is None and bear_top is None:
        return None
    return {
        "buy_bars_ago": (n - 1 - last_buy) if last_buy is not None else None,
        "sell_bars_ago": (n - 1 - last_sell) if last_sell is not None else None,
        "active_bull_zone": (round(bull_bot, 2), round(bull_top, 2)) if bull_top is not None else None,
        "active_bear_zone": (round(bear_bot, 2), round(bear_top, 2)) if bear_top is not None else None,
        "buy_signal_zone": last_buy_zone,     # zone the buy fired from (stop reference)
        "sell_signal_zone": last_sell_zone,
        "recent": recent,
    }


def scan_fvg_pullback(df: pd.DataFrame, max_bars_ago: int = 3) -> dict | None:
    """Bullish Fair-Value-Gap pullback rejection — registered entry scanner.

    Wraps `detect_fvg_pullback` (a faithful port of the "BOS & FVG Pullback
    Signals" Pine) so an FVG setup is **screenable across a universe**. Until
    now the detector existed only as one boolean inside the Early Reversal
    validation layer (`checks["FVG"]`), so a gap setup could be confirmed on a
    name you were already looking at but never *found* — the recurring orphaned
    detector pattern in this repo.

    Fires when a bullish FVG rejection printed within `max_bars_ago` bars: price
    dipped into the demand gap and closed back **above** its top with a dominant
    lower wick. Emits entry/stop/target, with the stop referenced to the gap the
    signal actually fired from.

    Why the rejection requirement matters (see ``concepts/Fair-Value-Gap``): the
    popular instruction is to rest a limit order *inside* the zone. That fills
    you on the way through in exactly the cases where the gap fails — the fill is
    guaranteed precisely when it is unwanted. Requiring the close back above the
    zone trades only gaps that held, at the cost of a worse average price.

    MEASURED in B-19's batch walk-forward (2026-09-02, LIQUID_50, 3 windows,
    Indian delivery ~29bps): **+0.11% @20d, -0.37% @60d on 1731 signals --
    "POSITIVE EDGE [UNSTABLE]"**.  Positive at 20d, negative at 60d, and unstable
    across windows, so it is not a graded entry: the honest read is that the setup
    is not distinguishable from the baseline once costs and window variation are
    paid.  (This docstring said "never been through the harness" for four days
    after B-19 ran -- the drift `claims_lint` exists to catch.)

    The separate question of whether gaps fill at all — the "market magnet"
    claim — is measured by ``fvg_fill_study.py``, which is a different question
    from whether this entry makes money.
    """
    if df is None or len(df) < 40:
        return None
    df = _clean_ohlc(df)
    if len(df) < 40:
        return None

    fvg = detect_fvg_pullback(df)
    if not fvg:
        return None
    ago = fvg["buy_bars_ago"]
    zone = fvg["buy_signal_zone"]
    if ago is None or ago > max_bars_ago or zone is None:
        return None

    bot, top = float(zone[0]), float(zone[1])
    if not top > bot:
        return None

    c = df["close"]
    last = float(c.iloc[-1])
    atr = float(_atr_series(df, 14).iloc[-1])
    if np.isnan(atr) or atr <= 0:
        return None

    stop = round(bot * 0.995, 2)
    risk = last - stop
    if risk <= 0:
        return None
    swing_high = float(df["high"].tail(40).max())
    target = round(max(swing_high, last + 2.0 * risk), 2)

    vol20 = float(df["volume"].tail(20).mean())
    vol_x = float(df["volume"].iloc[-1]) / vol20 if vol20 > 0 else 0.0
    vc = detect_volume_confirmation(df)
    vol_ok = bool(vc and vc["pass"])

    # Score: gap width in ATR (displacement strength) · volume · freshness.
    width_atr = min((top - bot) / atr, 3.0) / 3.0
    fresh = 1.0 if ago <= 1 else (0.7 if ago == 2 else 0.5)
    base = 12.0 + 38.0 * width_atr + (20.0 if vol_ok else 0.0) + 20.0 * fresh

    reasons = [
        f"Bullish FVG rejection {ago} bar(s) ago — dipped into the demand gap "
        f"₹{bot:.0f}–₹{top:.0f} and closed back above it",
        f"Gap width {(top - bot) / atr:.1f}× ATR "
        f"(size-gated: the port requires > 0.5× ATR, so trivial gaps are skipped)",
        (f"Displacement backed by volume ({vc['best_up_rvol']:.1f}× avg)" if vol_ok
         else "⚠ Displacement volume unconfirmed — weaker gap"),
        f"Trade plan — entry {last:.0f} · stop {stop:.0f} · target {target:.0f} "
        f"(R:R {(target - last) / risk:.1f})",
        "⚠ B-19 walk-forward: +0.11% @20d, −0.37% @60d — positive but UNSTABLE",
    ]
    return {
        "pattern_type": "Bullish FVG Pullback",
        "tags": ["FVG", f"Zone {bot:.0f}-{top:.0f}", f"{ago}d ago"],
        "reasons": reasons,
        "score_base": round(min(100.0, base), 1),
        "rs_raw": _rs_raw(df),
        "entry": round(last, 2),
        "stop": stop,
        "target": target,
        "vol_x50d": round(vol_x, 2),
    }


def _sweep_common(df: pd.DataFrame, direction: str, max_bars_ago: int,
                  pivot_len: int, eq_tol_pct: float,
                  min_touches: int) -> tuple[dict, pd.DataFrame] | None:
    """Shared gate for the two sweep scanners — find a recent sweep of the asked
    direction and hand back the event plus the cleaned frame."""
    if df is None or len(df) < pivot_len * 2 + 40:
        return None
    d = _clean_ohlc(df)
    if len(d) < pivot_len * 2 + 40:
        return None
    ev = detect_liquidity_sweep(d, pivot_len=pivot_len, eq_tol_pct=eq_tol_pct,
                                min_touches=min_touches,
                                lookback=max(20, max_bars_ago * 4))
    if not ev or ev["direction"] != direction:
        return None
    if ev["bars_ago"] > max_bars_ago:
        return None
    return ev, d


def scan_liquidity_sweep(df: pd.DataFrame, max_bars_ago: int = 3,
                         pivot_len: int = 5, eq_tol_pct: float = 0.75,
                         min_touches: int = 2) -> dict | None:
    """Bullish liquidity sweep — sell-side stop hunt reclaimed (B-41).

    Price ran a pool of **equal lows** (where stops rest), pierced it on the
    wick, and **closed back above** it. That is a false break, not a breakdown:
    the sellers who got filled below the pool are trapped, and the reversal is
    fuelled by their covering.

    This is the SMC event that *validates* the entries we already scan — an
    Order Block or FVG that forms right after a sweep is the textbook sequence.
    It is deliberately NOT `detect_support_breakdown`: that one requires a
    CLOSE beyond the level (a real break), this one requires the close back
    inside. One bar cannot satisfy both.

    Stop sits below the sweep wick — the point that invalidates the "trapped
    sellers" read. Target is the nearest buy-side pool above, falling back to
    2R when no equal-highs cluster is overhead.

    MEASURED 2026-09-06 (B-41m) -- the best result on this desk, and its own plan
    does not harvest it.  1400 signals on LIQUID_50: **+0.51% @20d (p=0.005) and
    +0.91% @60d (p=0.002), NET of Indian delivery costs**.  Walk-forward over 3
    windows is sign-stable at 10d, 20d and 60d (3/3 positive at each), against
    B-19's 0/41 stable -- though B-19 never covered this scanner, so it is a gap
    filled rather than a contradiction.

    Two caveats carry equal weight with that headline:

    * **The magnitude lives in two windows of three.**  Window 2 reads +0.03 /
      +0.06 / +0.12 -- indistinguishable from zero.  The SIGN is stable, the SIZE
      is not, and degradation confirms it (pooled +1.16 @60d vs a best window of
      +1.70).
    * **The shipped stop/target converts the edge to nothing: +0.23R gross,
      +0.06R after costs**, win 39.2%, target hit 549 times against stop 842.
      The signal carries forward information; this plan throws it away.

    That pre-registered test was then run (B-41p, `sweep_plan_study.py`, design
    committed before the first result).  **It is not WHERE the stop is, it is that
    there IS one**: swapping the wick stop for a 1.5x ATR stop moved the result
    +0.012R with a CI straddling zero, while REMOVING the stop turned -0.059R into
    **+0.504R** (CI [+0.337, +0.798], 4,854 trades).  A 20-day hold on this signal
    cannot survive a stop of that magnitude -- the drawdown path is part of the
    edge, which the -7.3% average MAE already implied.

    That is NOT a licence to trade it unstopped: arm C's downside is uncapped
    where a stopped arm loses at most 1R, and a better mean with an unbounded tail
    is a different risk profile, not a better one.  A lead, not a graded entry -- left at
    unmeasured weight in ``opportunity_hub`` rather than promoted, because +0.06R
    is what trading it as shipped actually returns.

    The claim still untested is the one this docstring always named: a
    sweep-reversal against a matched *clean* break, rather than against every bar.
    """
    got = _sweep_common(df, "bullish", max_bars_ago, pivot_len, eq_tol_pct, min_touches)
    if got is None:
        return None
    ev, d = got

    c = d["close"]
    last = float(c.iloc[-1])
    n = len(d)
    swept_bar = n - 1 - ev["bars_ago"]
    wick_low = float(d["low"].iloc[swept_bar])
    atr = float(_atr_series(d, 14).iloc[-1])
    if np.isnan(atr) or atr <= 0:
        return None

    # Price must still be holding the reclaim; a later close back under the pool
    # means the sweep read failed and this is a breakdown after all.
    if last <= ev["level"] * 0.995:
        return None

    stop = round(wick_low * 0.995, 2)
    risk = last - stop
    if risk <= 0:
        return None

    # Target the nearest buy-side pool overhead — but only if it is far enough to
    # be worth taking. A pool sitting just above entry yields an R:R near zero,
    # which is not a trade plan; fall back to 2R rather than emit one.
    pools = detect_liquidity_pools(d, pivot_len=pivot_len, eq_tol_pct=eq_tol_pct,
                                   min_touches=min_touches, max_pools=0)
    above = [p["level"] for p in pools
             if p["kind"] == "high" and p["level"] >= last + MIN_SWEEP_RR * risk]
    target = round(min(above) if above else last + 2.0 * risk, 2)

    vol20 = float(d["volume"].tail(20).mean())
    vol_x = float(d["volume"].iloc[-1]) / vol20 if vol20 > 0 else 0.0
    sweep_vol = (float(d["volume"].iloc[swept_bar]) / vol20) if vol20 > 0 else 0.0

    ms = read_market_structure(d, pivot_len=pivot_len)
    struct_state = ms["state"] if ms else "UNKNOWN"
    with_trend = struct_state in ("UPTREND", "BROADENING")

    # Score: pool depth (more touches = more stops) · rejection wick · freshness
    # · volume on the sweep bar · structural agreement.
    touch = min(ev["touches"], 4) / 4.0
    fresh = 1.0 if ev["bars_ago"] <= 1 else (0.7 if ev["bars_ago"] == 2 else 0.5)
    base = (10.0 + 25.0 * touch + 20.0 * min(ev["wick_ratio"], 1.0)
            + 20.0 * fresh + (15.0 if sweep_vol >= 1.2 else 0.0)
            + (10.0 if with_trend else 0.0))

    reasons = [
        f"Swept a {ev['touches']}-touch equal-lows pool at ₹{ev['level']:.0f} "
        f"{ev['bars_ago']} bar(s) ago and closed back above it",
        f"Pierce {ev['pierce_atr']:.2f}× ATR with a {ev['wick_ratio']:.0%} rejection wick "
        f"— a false break, not a breakdown (a breakdown closes below)",
        (f"Sweep bar volume {sweep_vol:.1f}× the 20d average" if sweep_vol >= 1.2
         else f"⚠ Sweep bar volume only {sweep_vol:.1f}× average — weaker stop-hunt read"),
        (f"Market structure {struct_state} — sweep runs with structure" if with_trend
         else f"⚠ Market structure {struct_state} — sweep is counter-structure"),
        f"Trade plan — entry {last:.0f} · stop {stop:.0f} · target {target:.0f} "
        f"(R:R {(target - last) / risk:.1f})",
        "⚠ B-41m: +0.51% @20d (p=0.005) net of costs, walk-forward stable — but the plan returns +0.06R",
    ]
    return {
        "pattern_type": "Bullish Liquidity Sweep",
        "tags": ["Sweep", f"{ev['touches']}-touch EQL", f"₹{ev['level']:.0f}",
                 f"{ev['bars_ago']}d ago"],
        "reasons": reasons,
        "score_base": round(min(100.0, base), 1),
        "rs_raw": _rs_raw(d),
        "entry": round(last, 2),
        "stop": stop,
        "target": target,
        "vol_x50d": round(vol_x, 2),
    }


def scan_liquidity_sweep_bear(df: pd.DataFrame, max_bars_ago: int = 3,
                              pivot_len: int = 5, eq_tol_pct: float = 0.75,
                              min_touches: int = 2) -> dict | None:
    """Bearish liquidity sweep — buy-side stop hunt rejected (B-41, Risk lane).

    The mirror of ``scan_liquidity_sweep``: price ran a pool of **equal highs**,
    pierced it on the wick, and **closed back below**. Breakout buyers filled
    above the pool are trapped and their stops feed the move down.

    Registered under Risk, so a NEGATIVE forward edge is the desired direction —
    it flags a name to avoid or exit, not a short to put on.

    Unmeasured, same event-study caveat as the bullish half.
    """
    got = _sweep_common(df, "bearish", max_bars_ago, pivot_len, eq_tol_pct, min_touches)
    if got is None:
        return None
    ev, d = got

    last = float(d["close"].iloc[-1])
    n = len(d)
    swept_bar = n - 1 - ev["bars_ago"]
    wick_high = float(d["high"].iloc[swept_bar])

    # Still rejected? A close back above the pool invalidates the trap read.
    if last >= ev["level"] * 1.005:
        return None

    invalidation = round(wick_high * 1.005, 2)
    vol20 = float(d["volume"].tail(20).mean())
    vol_x = float(d["volume"].iloc[-1]) / vol20 if vol20 > 0 else 0.0
    sweep_vol = (float(d["volume"].iloc[swept_bar]) / vol20) if vol20 > 0 else 0.0

    ms = read_market_structure(d, pivot_len=pivot_len)
    struct_state = ms["state"] if ms else "UNKNOWN"
    with_trend = struct_state in ("DOWNTREND", "BROADENING")

    touch = min(ev["touches"], 4) / 4.0
    fresh = 1.0 if ev["bars_ago"] <= 1 else (0.7 if ev["bars_ago"] == 2 else 0.5)
    base = (10.0 + 25.0 * touch + 20.0 * min(ev["wick_ratio"], 1.0)
            + 20.0 * fresh + (15.0 if sweep_vol >= 1.2 else 0.0)
            + (10.0 if with_trend else 0.0))

    reasons = [
        f"Swept a {ev['touches']}-touch equal-highs pool at ₹{ev['level']:.0f} "
        f"{ev['bars_ago']} bar(s) ago and closed back below it",
        f"Pierce {ev['pierce_atr']:.2f}× ATR with a {ev['wick_ratio']:.0%} rejection wick "
        f"— breakout buyers above ₹{ev['level']:.0f} are trapped",
        (f"Sweep bar volume {sweep_vol:.1f}× the 20d average" if sweep_vol >= 1.2
         else f"⚠ Sweep bar volume only {sweep_vol:.1f}× average — weaker trap read"),
        (f"Market structure {struct_state} — sweep runs with structure" if with_trend
         else f"⚠ Market structure {struct_state} — sweep is counter-structure"),
        f"Invalidated on a reclaim above {invalidation:.0f}",
        "⚠ Risk flag, not a short signal — avoid/exit, and unmeasured",
    ]
    return {
        "pattern_type": "Bearish Liquidity Sweep",
        "tags": ["Sweep", f"{ev['touches']}-touch EQH", f"₹{ev['level']:.0f}",
                 f"{ev['bars_ago']}d ago"],
        "reasons": reasons,
        "score_base": round(min(100.0, base), 1),
        "rs_raw": _rs_raw(d),
        "entry": round(last, 2),
        "stop": invalidation,
        "target": None,
        "vol_x50d": round(vol_x, 2),
    }


def scan_ict_setup(df: pd.DataFrame, pivot_len: int = 5,
                   lookback: int = 120,
                   min_body_ratio: float = 0.5) -> dict | None:
    """ICT Execution Blueprint composite scanner — chains the four ICT primitives:

    1. MSS with displacement: detect_bos_choch(require_displacement=True) must
       fire, confirming institutional participation on the structure break.
    2. OTE zone: 61.8–79% Fibonacci retracement of the displacement leg is
       computed from the returned leg_start / leg_end pair.
    3. Price location: current close must be inside or below the OTE zone
       (pullback is in progress or has dipped through). Only fires when
       price is in the zone — not a post-OTE entry.
    4. FVG overlap: an active bull FVG or a recent FVG rejection must overlap
       the OTE zone, confirming the zone from two independent methods.

    Stop: below the OTE zone low (same side as the FVG stop).
    Target: the next BSL pool, proxied by the rolling 40-bar swing high.

    MEASURED in B-19's batch walk-forward (2026-09-02): **-0.36% @20d,
    -1.24% @60d on 158 signals -- "NO EDGE [UNSTABLE]"**.  Negative at both
    horizons on a thin signal count.  Kept as a structured way to express the ICT
    read, not as a graded entry.
    """
    if df is None or len(df) < pivot_len * 4 + 40:
        return None
    df = _clean_ohlc(df)
    if len(df) < pivot_len * 4 + 40:
        return None

    ev = detect_bos_choch(df, pivot_len=pivot_len, lookback=lookback,
                          require_displacement=True,
                          min_body_ratio=min_body_ratio)
    if ev is None or not ev.get("displacement"):
        return None
    ote = ev.get("ote_zone")
    if ote is None:
        return None
    ote_lo, ote_hi = ote

    last = float(df["close"].iloc[-1])
    if not (ote_lo <= last <= ote_hi * 1.005):  # 0.5% above ote_hi = still eligible
        return None

    fvg = detect_fvg_pullback(df)
    fvg_overlap = False
    fvg_zone_label = ""
    if fvg:
        az = fvg.get("active_bull_zone")
        rz = fvg.get("buy_signal_zone")
        for zone in (az, rz):
            if zone:
                zbot, ztop = zone
                if zbot <= ote_hi and ztop >= ote_lo:
                    fvg_overlap = True
                    fvg_zone_label = f"₹{zbot:.0f}–₹{ztop:.0f}"
                    break
    if not fvg_overlap:
        return None

    atr = float(_atr_series(df, 14).iloc[-1])
    stop = round(ote_lo - 0.5 * atr, 2)
    risk = last - stop
    if risk <= 0:
        return None
    bsl_target = round(float(df["high"].tail(40).max()), 2)
    target = round(max(bsl_target, last + 2.0 * risk), 2)
    rr = round((target - last) / risk, 1)

    bos_label = ev["signal"]
    br = ev.get("body_ratio", 0.0) or 0.0
    bars_ago = ev.get("bars_ago", "?")

    reasons = [
        f"ICT MSS: {bos_label} with displacement (body {br:.0%} of range) "
        f"{bars_ago} bar(s) ago at ₹{ev['level']:.0f}",
        f"OTE zone: ₹{ote_lo:.0f}–₹{ote_hi:.0f} "
        f"(61.8–79% retracement of leg ₹{ev['leg_start']:.0f}→₹{ev['leg_end']:.0f})",
        f"FVG overlap confirmed inside OTE: {fvg_zone_label}",
        f"Trade plan — entry ₹{last:.0f} · stop ₹{stop:.0f} · target ₹{target:.0f} "
        f"(R:R {rr}×) · BSL proxy = 40-bar high",
        "⚠ B-19 walk-forward: −0.36% @20d, −1.24% @60d — NO EDGE, unstable",
    ]
    score = 55.0 + 20.0 * min(br / 0.8, 1.0) + (15.0 if fvg_overlap else 0.0)

    return {
        "pattern_type": "ICT Setup",
        "tags": ["ICT", bos_label, f"OTE ₹{ote_lo:.0f}-{ote_hi:.0f}", "FVG+OTE"],
        "reasons": reasons,
        "score_base": round(min(100.0, score), 1),
        "rs_raw": _rs_raw(df),
        "entry": round(last, 2),
        "stop": stop,
        "target": target,
        "ote_zone": ote,
        "displacement_body_ratio": round(br, 3),
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
        "score": round(50.0 + min(max(t["rr_to_t2"] - 1.5, 0.0) / 3.5, 1.0) * 45.0, 1),
        # Structured trade plan (Phase 3). `detect_last_pattern` already computed
        # all of this; it was only ever rendered into reason-text, which is why
        # the harness's R path stayed dormant on the scanner that measured the
        # second-best edge of the six tested.
        #
        # `target` is deliberately the SCALAR T2, not the targets list: the
        # backtest reads `target[0]` when handed a sequence, which would measure
        # to T1 (0.382) while this scanner gates on and advertises `rr_to_t2`
        # (0.618). Measuring a different target than the one the card promises is
        # the sort of quiet mismatch that makes a backtest worse than none.
        "entry":     t["entry"],
        "stop":      t["stop"],
        "target":    t["targets"][1],
        "targets":   t["targets"],          # full T1/T2/T3 ladder for the card
        "rr":        t["rr_to_t2"],
        "direction": h["direction"],
        # B-5: time stop — harmonic D-point PRZ typically resolves in ≤10 bars;
        # beyond that the pattern has failed (the PRZ wasn't respected).
        "time_stop": 10,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Opportunity Hub Phase 3 — the three greenfield detectors
# (candlestick patterns · IPO-base breakout · all-time-high breakout).
# ATH & IPO carry a ``needs_full_history`` marker in the registry so the hubs feed
# them the full listing history instead of the default ~300-bar window.
# ──────────────────────────────────────────────────────────────────────────────

def _clean_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Drop NaN OHLCV bars + reset index (the recurring yfinance-gap-bar guard)."""
    cols = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    return df.dropna(subset=cols).reset_index(drop=True)


def scan_candlestick(df: pd.DataFrame, min_vol_x: float = 1.0) -> dict | None:
    """Bullish candlestick reversal/continuation on the LATEST bar, with context.

    Fires only on a *fresh* (last-bar) bullish pattern — Bullish Engulfing,
    Hammer, Piercing Line, or Morning Star — and prefers ones forming after a
    pullback (at/below EMA20) rather than when already extended, with volume
    confirmation. A candlestick is a trigger, not a system: score stays modest.
    """
    if len(df) < 30:
        return None
    df = _clean_ohlc(df)
    if len(df) < 30:
        return None
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    n = len(df)
    i = n - 1
    avg_vol = float(v.tail(20).mean())
    if not (avg_vol > 0):
        return None
    vol_x = float(v.iloc[i]) / avg_vol
    ema20 = _ema_series(c, 20)
    rng = float(h.iloc[i] - l.iloc[i])
    if rng <= 0:
        return None
    body = abs(float(c.iloc[i] - o.iloc[i]))

    def is_bull_engulf() -> bool:
        return (c.iloc[i - 1] < o.iloc[i - 1] and c.iloc[i] > o.iloc[i]
                and o.iloc[i] <= c.iloc[i - 1] and c.iloc[i] >= o.iloc[i - 1])

    def is_hammer() -> bool:
        lower = min(o.iloc[i], c.iloc[i]) - l.iloc[i]
        upper = h.iloc[i] - max(o.iloc[i], c.iloc[i])
        return body > 0 and lower >= 2 * body and upper <= body and body <= 0.4 * rng

    def is_piercing() -> bool:
        mid = (o.iloc[i - 1] + c.iloc[i - 1]) / 2
        return (c.iloc[i - 1] < o.iloc[i - 1] and o.iloc[i] < l.iloc[i - 1]
                and mid < c.iloc[i] < o.iloc[i - 1])

    def is_morning_star() -> bool:
        if n < 3:
            return False
        first_body = o.iloc[i - 2] - c.iloc[i - 2]                 # >0 if red
        big_red = first_body > 0 and first_body > 0.5 * (h.iloc[i - 2] - l.iloc[i - 2])
        small = abs(c.iloc[i - 1] - o.iloc[i - 1]) < 0.4 * max(first_body, 1e-9)
        big_green = c.iloc[i] > o.iloc[i] and c.iloc[i] > (o.iloc[i - 2] + c.iloc[i - 2]) / 2
        return bool(big_red and small and big_green)

    found: list[tuple[str, float]] = []            # (name, base strength 0-100)
    if is_morning_star():
        found.append(("Morning Star", 70))
    if is_bull_engulf():
        found.append(("Bullish Engulfing", 62))
    if is_piercing():
        found.append(("Piercing Line", 55))
    if is_hammer():
        found.append(("Hammer", 52))
    if not found:
        return None

    name, base = max(found, key=lambda x: x[1])

    # Context: reversal candles earn their keep after a pullback, not when extended.
    dist_ema20 = (float(c.iloc[i]) / float(ema20.iloc[i]) - 1.0) * 100.0 if ema20.iloc[i] > 0 else 0.0
    pullback = float(l.iloc[i]) <= float(ema20.iloc[i]) * 1.02      # dipped to/through EMA20
    # Volume gate (engulfing/star want conviction; hammers can be quieter).
    if name in ("Bullish Engulfing", "Morning Star") and vol_x < min_vol_x:
        return None

    score = base + min(max(vol_x - 1.0, 0.0), 2.0) * 6.0
    if pullback:
        score += 6.0
    if dist_ema20 > 12:            # already extended — discount the reversal read
        score -= 12.0
    score = float(max(0.0, min(100.0, score)))

    reasons = [
        f"{name} on the latest bar — bullish {'reversal' if name != 'Bullish Engulfing' else 'reversal/continuation'} candle",
        f"Volume {vol_x:.1f}× the 20-day average" + (" — conviction" if vol_x >= 1.5 else ""),
        ("Formed after a pullback to EMA20 — higher-quality location"
         if pullback else f"{dist_ema20:+.1f}% vs EMA20"),
    ]
    tags = [name, f"Vol {vol_x:.1f}×"]
    if pullback:
        tags.append("At EMA20")
    return {
        "pattern_type": f"Candlestick: {name}",
        "tags": tags,
        "reasons": reasons,
        "score": round(score, 2),
        "vol_x50d": round(vol_x, 2),          # lights the Hub 'Vol Confirmed' pill
    }


def scan_bearish_reversal_candle(df: pd.DataFrame,
                                 require_gap: bool = True,
                                 resistance_pct: float = 3.0,
                                 min_vol_x: float = 1.0) -> dict | None:
    """Bearish reversal candle at resistance — a RISK FLAG, not a short signal.

    The bearish mirror of `scan_candlestick`, which had covered only the four
    bullish patterns. Detects **Evening Doji Star · Evening Star · Three Black
    Crows · Dark Cloud Cover · Bearish Engulfing · Shooting Star** on the latest
    bar and reports the strictest one that fires.

    Registered under category ``Risk``, so per `opportunity_hub.RISK_SCANNERS` a
    hit is evidence *against* a shortlisted long and can never add to a
    confluence count. An Evening Doji Star at resistance on a name about to be
    bought is exactly that read. See ``concepts/Candlestick-Patterns`` (Evening
    Doji Star deep-dive).

    Three design choices, each tracing to a decision recorded on that page:

    1. **Trend context is evaluated as of the bar the pattern STARTED forming**,
       not the current bar (`downCtx[N]` idiom from
       ``sources/Forthius-Reversal-Scanner-Pine``). Checking "was this an
       uptrend?" *after* the reversal has printed is lookback bias, and it is
       what makes reversal detectors look better than they are.
    2. **`require_gap` is a parameter, not a hard-coded rule.** Our book source
       (Morris) requires the star to gap above candle 1's body; the widely
       circulated retail version drops the gap and fires far more often. Both
       are documented endpoints of one dial, exactly as the FVG page treats its
       fill-mode spectrum. Default is the sourced (strict) reading. The gap test
       is **body-vs-body** (`min(o2,c2) > max(o1,c1)`) — the textbook "small body
       gaps higher" — not `pmax.pine`'s stricter wick-clear `low[1] > high[2]`.
    3. **The location gate is mandatory.** A reversal candle mid-range is noise;
       it earns attention only at resistance (near a swing-high pivot or the
       60-bar high). This is the page's Litchfield rule — the candle is the
       timing trigger inside a pre-identified structural setup, never the setup.

    Base scores are ordered by **geometric strictness** (how many independent
    conditions the pattern must satisfy), NOT by claimed accuracy.

    **Provenance update (2026-08-09):** Bulkowski's own pattern pages were
    checked and they confirm the gap requirement *body-to-body, shadows ignored*
    — i.e. `require_gap=True` with the body-gap test is his definition, not a
    guess. They also show **Evening Star and Evening Doji Star are separate
    patterns**: 72% / perf rank 4th vs **71% / perf rank 30th**. So the doji
    variant is the *weaker* one, and an accuracy-based ordering would invert the
    two scores below. Left on the strictness basis deliberately: the figures that
    would justify re-basing rest on 28-199-sample cells. See
    ``concepts/Candlestick-Patterns``.

    **Measured base rate** (2026-08-09, 17 NSE large-caps, 3y daily, 11,628
    bar-observations): fires on **2.61%** of bars strict / 2.75% loose. The gap
    switch barely moves the total but **quadruples the stars** — Evening Star
    5→23, Evening Doji Star 2→8 — because Shooting Star (158) and Bearish
    Engulfing (99) dominate the count either way. **Evening Doji Star is rare
    enough to be operationally irrelevant on its own** (~1 per 8.5 stock-years
    strict); the flag earns its keep through the commoner shapes.

    That is a *frequency* measurement, not an edge measurement. Whether a hit
    predicts anything is unmeasured until this goes through
    ``analyses/Backtest-Harness``.
    """
    if df is None or len(df) < 60:
        return None
    df = _clean_ohlc(df)
    if len(df) < 60:
        return None
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    n = len(df)
    i = n - 1
    avg_vol = float(v.tail(20).mean())
    if not (avg_vol > 0):
        return None
    vol_x = float(v.iloc[i]) / avg_vol
    ema20 = _ema_series(c, 20)
    ema50 = _ema_series(c, 50)
    rng = float(h.iloc[i] - l.iloc[i])
    if rng <= 0:
        return None
    body = abs(float(c.iloc[i] - o.iloc[i]))

    def _body(k: int) -> float:
        return abs(float(c.iloc[k] - o.iloc[k]))

    def _range(k: int) -> float:
        return float(h.iloc[k] - l.iloc[k])

    def _is_doji(k: int) -> bool:
        r = _range(k)
        return r > 0 and _body(k) <= 0.10 * r

    def uptrend_at(k: int) -> bool:
        """Was bar k in an uptrend? Evaluated at k, never at the current bar."""
        if k < 50 or np.isnan(ema50.iloc[k]) or ema50.iloc[k] <= 0:
            return False
        return bool(c.iloc[k] > ema20.iloc[k] and ema20.iloc[k] > ema50.iloc[k])

    def is_evening_star() -> tuple[bool, bool]:
        """(fired, is_doji_variant) — candle 1 white, small star, candle 3 < 50%."""
        if i < 2:
            return (False, False)
        b1 = float(c.iloc[i - 2] - o.iloc[i - 2])           # >0 if white
        big_white = b1 > 0 and b1 > 0.5 * max(_range(i - 2), 1e-9)
        small_star = _body(i - 1) < 0.4 * max(b1, 1e-9)
        gap_ok = True
        if require_gap:
            star_body_low = min(float(o.iloc[i - 1]), float(c.iloc[i - 1]))
            c1_body_high = max(float(o.iloc[i - 2]), float(c.iloc[i - 2]))
            gap_ok = star_body_low > c1_body_high
        mid1 = (float(o.iloc[i - 2]) + float(c.iloc[i - 2])) / 2.0
        big_black = bool(c.iloc[i] < o.iloc[i] and c.iloc[i] < mid1)
        fired = bool(big_white and small_star and gap_ok and big_black)
        return (fired, fired and _is_doji(i - 1))

    def is_shooting_star() -> bool:
        upper = float(h.iloc[i]) - max(float(o.iloc[i]), float(c.iloc[i]))
        lower = min(float(o.iloc[i]), float(c.iloc[i])) - float(l.iloc[i])
        return bool(body > 0 and upper >= 2 * body and lower <= body
                    and body <= 0.4 * rng)

    def is_bear_engulf() -> bool:
        return bool(c.iloc[i - 1] > o.iloc[i - 1] and c.iloc[i] < o.iloc[i]
                    and o.iloc[i] >= c.iloc[i - 1] and c.iloc[i] <= o.iloc[i - 1])

    def is_dark_cloud() -> bool:
        mid = (float(o.iloc[i - 1]) + float(c.iloc[i - 1])) / 2.0
        return bool(c.iloc[i - 1] > o.iloc[i - 1] and o.iloc[i] > h.iloc[i - 1]
                    and o.iloc[i - 1] < c.iloc[i] < mid)

    def is_three_black_crows() -> bool:
        if i < 2:
            return False
        for k in (i - 2, i - 1, i):
            if not (c.iloc[k] < o.iloc[k] and _body(k) > 0.5 * max(_range(k), 1e-9)):
                return False
        for k in (i - 1, i):
            # each opens inside the prior body and closes lower
            if not (o.iloc[k] < o.iloc[k - 1] and o.iloc[k] > c.iloc[k - 1]
                    and c.iloc[k] < c.iloc[k - 1]):
                return False
        return True

    # ── Detect. (name, base strictness score, bars the pattern spans) ──────────
    found: list[tuple[str, float, int]] = []
    star_fired, star_doji = is_evening_star()
    if star_fired:
        found.append(("Evening Doji Star" if star_doji else "Evening Star",
                      68.0 if star_doji else 62.0, 3))
    if is_three_black_crows():
        found.append(("Three Black Crows", 60.0, 3))
    if is_dark_cloud():
        found.append(("Dark Cloud Cover", 55.0, 2))
    if is_bear_engulf():
        found.append(("Bearish Engulfing", 52.0, 2))
    if is_shooting_star():
        found.append(("Shooting Star", 48.0, 1))
    if not found:
        return None

    name, base, span = max(found, key=lambda x: x[1])

    # ── Context gate 1: uptrend as of when the pattern started forming ─────────
    start = i - (span - 1)
    if not uptrend_at(start):
        return None

    # ── Context gate 2: at resistance (swing-high pivot, or the 60-bar high) ───
    win = df.tail(60)
    hi60 = float(win["high"].max())
    # Pivot search must EXCLUDE the pattern's own bars. A star is itself a local
    # high (candle 3 is lower, candle 1 is lower), so scanning the full window
    # lets every pattern be "near a pivot" — the gate would never reject anything.
    highs = win["high"].values[:max(0, len(win) - span)]
    pivot = None
    for k in range(len(highs) - 2, 1, -1):
        if highs[k] > highs[k - 1] and highs[k] > highs[k + 1]:
            pivot = float(highs[k])
            break
    patt_high = float(h.iloc[start:].max())
    near_pivot = pivot is not None and abs(patt_high - pivot) / pivot * 100 <= resistance_pct
    near_hi60 = (hi60 - patt_high) / hi60 * 100 <= resistance_pct if hi60 > 0 else False
    if not (near_pivot or near_hi60):
        return None
    where = (f"swing-high pivot {pivot:.0f}" if near_pivot else f"60-bar high {hi60:.0f}")

    # ── Score: strictness prior + volume conviction + how extended the run was ─
    if name in ("Evening Star", "Evening Doji Star", "Bearish Engulfing") and vol_x < min_vol_x:
        return None
    score = base + min(max(vol_x - 1.0, 0.0), 2.0) * 6.0
    ext = ((float(c.iloc[start]) / float(ema20.iloc[start]) - 1.0) * 100.0
           if ema20.iloc[start] > 0 else 0.0)
    if ext > 8:                     # reversing out of an extended run — more meaningful
        score += 6.0
    score = float(max(0.0, min(100.0, score)))

    reasons = [
        f"{name} on the latest bar — bearish reversal candle"
        + (" (star gapped above candle 1's body)" if name.startswith("Evening") and require_gap else ""),
        f"Uptrend confirmed as of the bar the pattern started ({span}-bar pattern) — "
        "context checked at formation, not after the reversal printed",
        f"Formed at resistance — {where} (within {resistance_pct:.0f}%)",
        f"Volume {vol_x:.1f}× the 20-day average" + (" — conviction" if vol_x >= 1.5 else ""),
        (f"Reversing {ext:+.1f}% above EMA20 — extended run" if ext > 8
         else f"{ext:+.1f}% vs EMA20 at pattern start"),
        "⚠ RISK FLAG on a long thesis, not a short signal — and unmeasured: "
        "not yet run through the backtest harness",
    ]
    tags = [name, f"Vol {vol_x:.1f}×", "At Resistance"]
    if name == "Evening Doji Star":
        tags.append("Doji Star")
    return {
        "pattern_type": f"Bearish Reversal: {name}",
        "tags": tags,
        "reasons": reasons,
        "score": round(score, 2),
        "vol_x50d": round(vol_x, 2),
    }


def scan_mean_reversion(df: pd.DataFrame,
                        rsi2_oversold: float = 10.0,
                        stretch_pct: float = 5.0,
                        lookback: int = 3) -> dict | None:
    """Connors-style mean-reversion setup (B-3 — fills the SIDEWAYS regime gap).

    Fires when:
      1. **Stretch**: close is ≥ stretch_pct % below the 20-bar SMA (rubber-band
         pulled down far enough to snap back).
      2. **RSI(2) oversold**: the ultra-short RSI is below rsi2_oversold (default 10),
         confirming short-term exhaustion.
      3. **First up day**: today's close is higher than yesterday's — the pullback
         is beginning to curl up, not still in free-fall.
      4. **Regime gate**: the 200-bar SMA is flat or rising (slope over 20 bars
         ≥ -0.1%), so we are buying the dip in an intact long-term uptrend, not
         catching a falling knife in a bear market.

    This is a *mean-reversion entry*, not a breakout: the stop is tight (below the
    session low) and the target is a partial reversion to the 20-day SMA (T1) or
    full reversion plus a buffer (T2 = 20-SMA × 1.01).

    ── THE STOP IS MEASURED, AND IT COSTS RETURN (B-8, 2026-09-17) ────────────
    `mean_reversion_stop_study.py` ran this setup's own signals under four stop
    policies over ~20 years, Indian delivery costs on every arm. Headline figures
    are the WIDE run (300 nifty500 names, **742 non-overlapping signals**, above
    the desk's 200 floor):

        NO STOP              +0.47%   stopped  0.0%   win 55.5%
        session low x0.995   -0.15%   stopped 68.1%   win 30.1%   <- this one
        1-ATR                +0.07%   stopped 52.7%   win 40.8%
        2-ATR                +0.33%   stopped 24.7%   win 53.1%

    Paired on the same signals, **this stop costs -0.64pp versus no stop at all
    (p=0.0086)**. 1-ATR costs -0.40pp (p=0.082) and 2-ATR -0.14pp (p=0.370) —
    neither significant, and 2-ATR is nearly free because it is only touched 24.7%
    of the time. The tight stop fires on more than two trades in three and cuts
    the win rate from 55.5% to 30.1%: it closes mean-reversion trades exactly
    where the reversion was about to happen, which is what Connors' sources
    claimed and what this desk had adopted the opposite of by inheritance.

    **The narrow basket overstated it, and that is worth knowing.** On LIQUID_50
    alone (145 signals) the same test read -1.44pp at p=0.0009 — more than double
    the effect. The DIRECTION replicated on 5x the sample and the policy ordering
    is identical; the SIZE did not. Cite -0.64pp.

    **It is deliberately UNCHANGED.** `time_stop` already bounds the trade in
    time, and removing a price stop trades a bounded loss for a gap-exposed one —
    which this study did not measure. The number is recorded here so the next
    reader chooses on purpose. 2-ATR is the candidate a follow-up should test as
    the default: it keeps a bound and costs nothing measurable.

    Unlike the trend-following scanners, ``vol_x50d`` is intentionally ignored:
    mean-reversion entries often happen on low volume (exhaustion, not expansion).
    """
    if df is None or len(df) < 210:
        return None
    df = _clean_ohlc(df)
    if len(df) < 210:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma200 = close.rolling(200).mean()
    if np.isnan(sma20) or np.isnan(sma200.iloc[-1]):
        return None

    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])

    # --- Gate 4: regime (200-SMA slope must not be sharply down) ---
    sma200_now = float(sma200.iloc[-1])
    sma200_20ago = float(sma200.iloc[-21])
    slope_pct = (sma200_now - sma200_20ago) / max(sma200_20ago, 1.0) * 100.0
    if slope_pct < -0.1:
        return None   # 200-SMA falling — not a dip, might be a new downtrend

    # --- Gate 1: stretched below 20-SMA ---
    dist_pct = (sma20 - last) / sma20 * 100.0
    if dist_pct < stretch_pct:
        return None

    # --- Gate 2: RSI(2) oversold ---
    rsi2 = _rsi_series(close, 2)
    rsi2_now = float(rsi2.iloc[-1])
    if np.isnan(rsi2_now) or rsi2_now >= rsi2_oversold:
        return None

    # --- Gate 3: first up day (close > prior close) ---
    if last <= prev:
        return None

    # --- Consecutive down days before today (depth of the pull) ---
    down_days = 0
    for i in range(2, min(lookback + 2, len(close))):
        if float(close.iloc[-i]) >= float(close.iloc[-i - 1]):
            break
        down_days += 1

    # Score: deeper stretch and more extreme RSI(2) = higher confidence
    stretch_score = min(dist_pct / 15.0, 1.0) * 35.0   # full at 15% below SMA
    rsi_score = max(0.0, (rsi2_oversold - rsi2_now) / rsi2_oversold) * 35.0
    down_score = min(down_days / 3.0, 1.0) * 20.0
    slope_bonus = 10.0 if slope_pct > 0.2 else 0.0     # actively rising 200-SMA
    score = stretch_score + rsi_score + down_score + slope_bonus

    entry = last
    stop = round(float(low.iloc[-1]) * 0.995, 2)     # below session low
    risk = entry - stop
    if risk <= 0:
        return None

    target1 = round(sma20, 2)                              # T1 = revert to SMA20
    target2 = round(sma20 * 1.01, 2)                       # T2 = SMA20 + 1% buffer
    rr1 = round((target1 - entry) / risk, 1) if risk > 0 else 0

    vol20 = float(df["volume"].tail(20).mean())
    vol_x = float(df["volume"].iloc[-1]) / vol20 if vol20 > 0 else 0.0

    reasons = [
        f"Stretched {dist_pct:.1f}% below 20-SMA (₹{sma20:.0f}) — rubber-band tension",
        f"RSI(2) = {rsi2_now:.1f} — ultra-short-term exhaustion (gate < {rsi2_oversold})",
        f"First up close after {down_days} down days — early curl from the low",
        f"200-SMA slope {slope_pct:+.2f}% over 20 bars — long-term trend intact"
        if slope_pct >= 0 else
        f"⚠ 200-SMA slope {slope_pct:+.2f}% — marginal regime; watch for trend change",
        f"Trade plan — entry {entry:.0f} · stop {stop:.0f} · T1 {target1:.0f} (SMA20) "
        f"· T2 {target2:.0f} · R:R to T1 = {rr1}",
        "⚠ The stop is MEASURED and it costs return (B-8): this session-low stop "
        "fires on 68% of trades and gave -0.64pp vs no stop at all (p=0.009, 742 "
        "signals, 300 names, 20y). A 2-ATR stop cost nothing measurable. Kept "
        "unchanged — it bounds the loss, which the study did not score.",
    ]

    return {
        "pattern_type": "Mean Reversion (Connors RSI2)",
        "tags": [f"RSI2 {rsi2_now:.0f}", f"Stretch {dist_pct:.1f}%",
                 f"{down_days}d down", "SIDEWAYS regime"],
        "reasons": reasons,
        "score_base": round(min(100.0, score), 1),
        "rs_raw": _rs_raw(df),
        "vol_x50d": round(vol_x, 2),
        "entry": round(entry, 2),
        "stop": stop,
        "target": target1,
        "target2": target2,
        # B-5: Connors RSI(2) mean-reversion typically resolves in 3-5 days;
        # 10 bars is a generous outer limit — still in the position after that
        # means the rubber band is not snapping back (thesis failed).
        "time_stop": 10,
    }


def scan_ipo_breakout(df: pd.DataFrame,
                      max_history_bars: int = 500,
                      min_history_bars: int = 40,
                      base_window: int = 20,
                      min_vol_x: float = 1.5,
                      max_extended_pct: float = 8.0) -> dict | None:
    """First-base breakout for a RECENTLY LISTED stock (IPO base).

    Recency is read from the *total* listing history (needs the hub's full-history
    fetch): a stock with only `min_history_bars`–`max_history_bars` bars is young.
    Fires when price makes a new post-listing closing high out of a recent base
    (`base_window` bars) on ≥`min_vol_x`× volume, and isn't already extended.
    """
    if df is None or len(df) < min_history_bars:
        return None
    df = _clean_ohlc(df)
    n = len(df)
    if not (min_history_bars <= n <= max_history_bars):
        return None                                  # not a recent listing (or too raw)
    c, h, v = df["close"], df["high"], df["volume"]
    last = float(c.iloc[-1])
    # New post-listing closing high (allow ties within a hair).
    prior_high = float(c.iloc[:-1].max())
    if last < prior_high * 0.999:
        return None
    # A base must precede the breakout: the `base_window` bars before today were a
    # tight-ish range (not a vertical ramp).
    base = c.iloc[-(base_window + 1):-1]
    if len(base) < base_window // 2:
        return None
    base_hi, base_lo = float(base.max()), float(base.min())
    if base_lo <= 0:
        return None
    base_range_pct = (base_hi - base_lo) / base_lo * 100.0
    if base_range_pct > 35:
        return None                                  # too loose to be a base
    # Volume expansion on the breakout.
    avg_vol = float(v.tail(min(50, n)).median())
    if not (avg_vol > 0):
        return None
    vol_x = float(v.iloc[-1]) / avg_vol
    if vol_x < min_vol_x:
        return None
    # Not already extended above the base.
    extended = (last - base_hi) / base_hi * 100.0
    if extended > max_extended_pct:
        return None

    age_days = n
    score = 50.0 + min(max(vol_x - 1.0, 0.0), 3.0) * 8.0 + max(0.0, (35 - base_range_pct)) * 0.4
    score = float(max(0.0, min(100.0, score)))
    reasons = [
        f"Recently listed (~{age_days} sessions of history) — IPO / early-stage name",
        f"New post-listing high: {last:.2f} clears the prior high {prior_high:.2f}",
        f"Broke a {len(base)}-bar base ({base_lo:.2f}–{base_hi:.2f}, {base_range_pct:.0f}% wide)",
        f"Volume {vol_x:.1f}× median — breakout conviction",
    ]
    return {
        "pattern_type": "IPO-Base Breakout",
        "tags": ["IPO Breakout", f"~{age_days}d listed", f"base {base_range_pct:.0f}%",
                 f"Vol {vol_x:.1f}×"],
        "reasons": reasons,
        "score": round(score, 2),
        "vol_x50d": round(vol_x, 2),
    }


def scan_ath_breakout(df: pd.DataFrame,
                      min_history_bars: int = 250,
                      buffer_pct: float = 0.5,
                      confirm_bars: int = 3,
                      min_vol_x: float = 1.3,
                      max_extended_pct: float = 10.0) -> dict | None:
    """All-time-high breakout — a new closing high over the ENTIRE listing history.

    Needs the hub's full-history fetch (the default ~300-bar window would make this
    a mere ~1-year high, duplicating 52-Week High Leaders). Requires enough history
    to be a real ATH (`min_history_bars`), the prior ATH taken over all bars except
    the last `confirm_bars`, volume confirmation, and not already extended.
    """
    if df is None or len(df) < min_history_bars:
        return None
    df = _clean_ohlc(df)
    n = len(df)
    if n < min_history_bars:
        return None
    c, h, v = df["close"], df["high"], df["volume"]
    last = float(c.iloc[-1])
    # Prior ATH = highest high before the breakout window.
    prior_ath = float(h.iloc[:-confirm_bars].max())
    if prior_ath <= 0:
        return None
    # New high: today clears the prior ATH (within a small buffer for close vs high).
    if not (float(h.iloc[-1]) >= prior_ath and last >= prior_ath * (1 - buffer_pct / 100.0)):
        return None
    # Not a vertical blow-off already far above the prior ATH.
    extended = (last - prior_ath) / prior_ath * 100.0
    if extended > max_extended_pct:
        return None
    # Volume confirmation.
    avg_vol = float(v.tail(50).median())
    if not (avg_vol > 0):
        return None
    vol_x = float(v.iloc[-1]) / avg_vol
    if vol_x < min_vol_x:
        return None
    # Base quality bonus: was price coiling near the highs (last ~30 bars tight)
    # rather than spiking straight up?
    recent = c.tail(30)
    coil_pct = (float(recent.max()) - float(recent.min())) / float(recent.min()) * 100.0 \
        if float(recent.min()) > 0 else 999.0
    coiled = coil_pct <= 25.0

    years = round(n / 250.0, 1)
    score = 55.0 + min(max(vol_x - 1.0, 0.0), 3.0) * 8.0 + (8.0 if coiled else 0.0)
    score = float(max(0.0, min(100.0, score)))
    reasons = [
        f"New all-time high — clears the prior ATH {prior_ath:.2f} over ~{years}y of history",
        f"Close {last:.2f} ({extended:+.1f}% vs prior ATH — not yet extended)",
        f"Volume {vol_x:.1f}× median — breakout conviction",
        ("Broke out of a tight base near the highs (constructive)" if coiled
         else "Faster run into the high — watch for a retest"),
    ]
    tags = ["ATH Breakout", f"{years}y history", f"Vol {vol_x:.1f}×"]
    if coiled:
        tags.append("Coiled base")
    return {
        "pattern_type": "All-Time-High Breakout",
        "tags": tags,
        "reasons": reasons,
        "score": round(score, 2),
        "vol_x50d": round(vol_x, 2),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Scanner registry
# ──────────────────────────────────────────────────────────────────────────────

def scan_rsi_60_40(df: pd.DataFrame) -> dict | None:
    """RSI 60-40 with-trend continuation setup (21 & 50 EMA).

    In a healthy uptrend RSI(14) does not obey the textbook 70/30 rules — it
    oscillates in a ~40-60 band, making buyable higher-lows near 40 and getting
    rejected (a breakout trigger, not a sell) near 60. This scanner requires that
    regime, then fires one of two with-trend entries:

      A. RSI-40 pullback — RSI dipped near 40 and is turning up at EMA21/EMA50
         support, ideally with a bullish confirmation bar. Stop below EMA50.
      B. RSI-60 breakout — RSI is breaking up through ~60 as price clears a
         recent high on expanding volume. Stop below EMA21.

    Trend gate (all required): price above both EMAs and EMA21 stacked above
    EMA50. Emits ``score_base`` + ``rs_raw`` so the hub blends the RS percentile
    like the other graded scanners. See ``strategies/RSI-60-40-Setup``.
    """
    if df is None or len(df) < 70:
        return None
    df = _clean_ohlc(df)
    if len(df) < 70:
        return None

    close = df["close"]
    ema21 = _ema_series(close, 21)
    ema50 = _ema_series(close, 50)
    rsi = _rsi_series(close, 14)
    if np.isnan(rsi.iloc[-1]) or np.isnan(rsi.iloc[-2]) or np.isnan(ema50.iloc[-1]):
        return None

    last = float(close.iloc[-1])
    prev_close = float(close.iloc[-2])
    open_last = float(df["open"].iloc[-1]) if "open" in df.columns else prev_close
    e21 = float(ema21.iloc[-1])
    e50 = float(ema50.iloc[-1])
    rsi_now = float(rsi.iloc[-1])
    rsi_prev = float(rsi.iloc[-2])

    # --- Trend gate (all required) ---
    if not (last > e21 and last > e50 and e21 > e50):
        return None

    # --- RSI regime gate: recent RSI must behave as a 40-60 band, not a blow-off ---
    recent = rsi.tail(20).dropna()
    if len(recent) < 15:
        return None
    if float(recent.min()) < 30.0 or float(recent.max()) > 80.0 or float(recent.median()) < 40.0:
        return None  # left the 40-60 regime (oversold, blow-off, or downtrend)

    vol20 = float(df["volume"].tail(20).mean())
    vol_last = float(df["volume"].iloc[-1])
    vol_x = vol_last / vol20 if vol20 > 0 else 0.0
    bull_bar = last > open_last and last > prev_close

    setup = None
    reasons: list[str] = []
    tags: list[str] = []
    entry = stop = None
    base = 0.0

    # --- A. RSI-40 pullback entry ---
    near_support = (last <= e21 * 1.03) or (abs(last - e50) / e50 <= 0.03)
    if 36.0 <= rsi_now <= 50.0 and rsi_now > rsi_prev and near_support:
        setup = "RSI-40 Pullback"
        prox_rsi = max(0.0, 1.0 - abs(rsi_now - 42.0) / 10.0)
        dist_sup = min(abs(last - e21), abs(last - e50)) / last
        prox_sup = max(0.0, 1.0 - dist_sup / 0.03)
        base = 40.0 + 30.0 * prox_rsi + 20.0 * prox_sup + (10.0 if bull_bar else 0.0)
        entry = last
        stop = round(e50 * 0.995, 2)   # below the 50 EMA per the rules
        reasons = [
            f"RSI(14) {rsi_now:.0f} turning up from the ~40 floor — buyable dip in an uptrend",
            f"Price {last:.0f} at EMA support (EMA21 {e21:.0f} · EMA50 {e50:.0f})",
        ]
        reasons.append("Bullish bar at support — entry confirmation present" if bull_bar
                       else "⚠ No bullish confirmation bar yet — wait for a green candle")
        tags = [f"RSI {rsi_now:.0f}", "Pullback to EMA", "Stop < EMA50"]

    # --- B. RSI-60 breakout entry ---
    else:
        recent_high = float(df["high"].iloc[-21:-1].max())
        breaking_60 = (rsi_prev < 60.0 <= rsi_now) or (rsi_now >= 58.0 and rsi_now > rsi_prev)
        if breaking_60 and last >= recent_high:
            setup = "RSI-60 Breakout"
            prox_rsi = max(0.0, min(1.0, (rsi_now - 58.0) / 7.0))
            vol_score = max(0.0, min(1.0, (vol_x - 1.0) / 0.5))
            base = 45.0 + 25.0 * prox_rsi + 20.0 * vol_score + (10.0 if bull_bar else 0.0)
            entry = last
            stop = round(e21 * 0.995, 2)   # below the 21 EMA per the rules
            reasons = [
                f"RSI(14) {rsi_now:.0f} breaking above 60 — momentum trigger, not a sell",
                f"Price {last:.0f} clearing the 20-day high {recent_high:.0f}",
            ]
            reasons.append(
                f"Volume {vol_x:.1f}× 20-day average — breakout backed by participation"
                if vol_x >= 1.5 else
                "⚠ Volume below 1.5× average — breakout lacks strong participation")
            tags = [f"RSI {rsi_now:.0f}", "60 breakout", "Stop < EMA21"]

    if setup is None:
        return None

    # 2R target (conservative end of the strategy's 2R-3R band).
    target = None
    if entry and stop and entry > stop:
        target = round(entry + 2.0 * (entry - stop), 2)
        reasons.append(f"Trade plan — entry {entry:.0f} · stop {stop:.0f} · target {target:.0f} (2R)")

    out: dict = {
        "pattern_type": f"RSI 60-40 · {setup}",
        "tags": tags,
        "reasons": reasons,
        "score_base": round(min(100.0, base), 1),
        "score": round(min(100.0, base), 1),    # provisional — run_scanner blends in RS
        "rs_raw": _rs_raw(df),
        "vol_x50d": round(vol_x, 2),
    }
    if entry and stop and target:
        out.update({"entry": entry, "stop": stop, "target": target,
                    # B-5: time stop — RSI 60-40 is a momentum continuation trade;
                    # 15 bars (3 weeks) without follow-through signals the thesis failed.
                    "time_stop": 15})
    return out


def scan_rsi_divergence_bull(df: pd.DataFrame, pivot_len: int = 3,
                             lookback: int = 80) -> dict | None:
    """Bullish RSI divergence on the last closed daily bar.

    Fires when the most recent swing low made a LOWER price low but a HIGHER
    RSI(14) low than the preceding swing low — classic hidden institutional
    accumulation. The second swing low must be within the last 3 bars so the
    signal is actionable on the last closed daily bar (pivot_len=3 keeps the
    symmetry requirement tight so only near-term pivots qualify).

    Conditions (all must hold):
      1. Two pivot lows within ``lookback`` bars, detected by pivot_len symmetry.
      2. Price: low2 < low1  (lower low).
      3. RSI: rsi_at_low2 > rsi_at_low1  (higher RSI low — the divergence).
      4. Divergence gap ≥ 3 RSI points (avoids noise from near-equal readings).
      5. The second low is within the last 3 bars (tight recency window).
      6. RSI(14) at the second low ≤ 60 (divergence in overbought territory is noise).
      7. RSI on bar[-1] > RSI at bar of the second low (bounce already starting).

    Score  (0-100):
      Base 55 + oversold bonus (≤35 → +15, ≤45 → +8) + magnitude bonus
      (RSI gap > 10 pts → +10) + recency bonus (≤3 bars ago → +5, automatic
      given the 3-bar gate).
    """
    if df is None or len(df) < pivot_len * 2 + 40:
        return None
    df = _clean_ohlc(df)
    if len(df) < pivot_len * 2 + 40:
        return None

    close = df["close"]
    low = df["low"]
    high = df["high"]
    n = len(df)
    rsi = _rsi_series(close, 14)
    atr = float(_atr_series(df, 14).iloc[-1])
    if np.isnan(atr) or atr <= 0:
        return None

    # ── Collect all swing lows in the lookback window ────────────────────────
    search_start = max(pivot_len, n - lookback)
    pivot_lows: list[tuple[int, float, float]] = []   # (bar_idx, price_low, rsi_at_low)
    for i in range(search_start, n - pivot_len):
        window = low.iloc[i - pivot_len: i + pivot_len + 1]
        if float(low.iloc[i]) == float(window.min()):
            rsi_val = float(rsi.iloc[i])
            if not np.isnan(rsi_val):
                pivot_lows.append((i, float(low.iloc[i]), rsi_val))

    if len(pivot_lows) < 2:
        return None

    # ── Check most recent pivot pair for divergence ───────────────────────────
    idx1, price1, rsi1 = pivot_lows[-2]
    idx2, price2, rsi2 = pivot_lows[-1]

    bars_ago = n - 1 - idx2          # how many bars since the second pivot low

    if bars_ago > 3:                 # outside the 3-bar detection window
        return None
    if price2 >= price1:             # no lower low in price
        return None
    if rsi2 <= rsi1:                 # no higher low in RSI
        return None
    rsi_gap = rsi2 - rsi1
    if rsi_gap < 3.0:                # gap too small to trust
        return None
    if rsi2 > 60.0:                  # divergence in overbought is meaningless
        return None

    # Bounce confirmation: RSI on the last bar must be rising above the second low
    rsi_now = float(rsi.iloc[-1])
    if np.isnan(rsi_now) or rsi_now <= rsi2:
        return None

    # ── Fibonacci retracement (swing high between the two lows → low2) ───────
    swing_high_between = float(high.iloc[idx1:idx2 + 1].max())
    swing_range = swing_high_between - price2
    has_fib = swing_range > 0 and swing_high_between > price1

    fib_0 = fib_236 = fib_382 = fib_500 = fib_618 = None
    fib_near_tag = ""
    fib_score_bonus = 0.0
    if has_fib:
        fib_0   = swing_high_between
        fib_236 = swing_high_between - 0.236 * swing_range
        fib_382 = swing_high_between - 0.382 * swing_range
        fib_500 = swing_high_between - 0.500 * swing_range
        fib_618 = swing_high_between - 0.618 * swing_range

        cmp_now = float(close.iloc[-1])
        for label, level, bonus in [
            ("38.2%", fib_382, 8.0), ("50%", fib_500, 10.0), ("61.8%", fib_618, 6.0),
        ]:
            if swing_range > 0 and abs(cmp_now - level) / swing_range < 0.02:
                fib_near_tag = f"@ Fib {label}"
                fib_score_bonus = bonus
                break

    # ── Score ─────────────────────────────────────────────────────────────────
    score = 55.0
    if rsi2 <= 35.0:
        score += 15.0
    elif rsi2 <= 45.0:
        score += 8.0
    if rsi_gap >= 10.0:
        score += 10.0
    if bars_ago <= 3:
        score += 5.0
    score += fib_score_bonus
    score = min(round(score, 1), 95.0)

    # ── Trade plan: CMP / SL / TGT ───────────────────────────────────────────
    cmp = round(float(close.iloc[-1]), 2)
    if has_fib:
        stop = round(fib_618 - 0.3 * atr, 2)
        target = round(fib_0, 2)
    else:
        stop = round(price2 - 0.5 * atr, 2)
        risk = cmp - stop
        target = round(cmp + 2.0 * risk, 2) if risk > 0 else None

    risk = cmp - stop
    if risk > 0 and target is not None:
        rr = round((target - cmp) / risk, 1)
    else:
        rr = 0.0

    tags = [
        f"RSI div +{rsi_gap:.1f}pt",
        f"RSI {rsi2:.0f}",
        f"{bars_ago}d ago",
    ]
    if fib_near_tag:
        tags.append(fib_near_tag)
    if rr > 0:
        tags.append(f"R:R {rr}×")

    reasons = [
        f"Price lower low: ₹{price1:.2f} → ₹{price2:.2f}",
        f"RSI(14) higher low: {rsi1:.1f} → {rsi2:.1f} (+{rsi_gap:.1f} pts divergence)",
        f"RSI now {rsi_now:.1f} — bouncing off the divergence low",
        f"Second swing low {bars_ago} bar(s) ago — signal still fresh",
    ]
    if rsi2 <= 45.0:
        reasons.append(f"RSI oversold at the low ({rsi2:.0f}) — strengthens the read")
    if has_fib:
        reasons.append(
            f"Fib levels: 0%=₹{fib_0:.0f} · 23.6%=₹{fib_236:.0f} · "
            f"38.2%=₹{fib_382:.0f} · 50%=₹{fib_500:.0f} · 61.8%=₹{fib_618:.0f}"
        )
    reasons.append(
        f"CMP ₹{cmp} · SL ₹{stop} · TGT ₹{target} · R:R {rr}×"
    )

    result = {
        "symbol": df.index[-1] if hasattr(df.index[-1], "__str__") else "?",
        "pattern_type": "RSI Divergence Bull",
        "score": score,
        "tags": tags,
        "reasons": reasons,
        "entry": cmp,
        "stop": stop,
        "target": target,
        "time_stop": 10,
        "key_level": round(swing_high_between, 2),
        "rsi_now": round(rsi_now, 1),
        "rsi_at_low": round(rsi2, 1),
        "rsi_gap": round(rsi_gap, 1),
        "bars_since_low": bars_ago,
        "rr_ratio": rr,
    }
    if has_fib:
        result["fib_382_level"] = round(fib_382, 2)
        result["fib_500_level"] = round(fib_500, 2)
        result["fib_618_level"] = round(fib_618, 2)
        result["swing_high"] = round(fib_0, 2)
    return result


def scan_rsi_divergence_bear(df: pd.DataFrame, pivot_len: int = 3,
                             lookback: int = 80) -> dict | None:
    """Bearish RSI divergence on the last closed daily bar.

    Fires when the most recent swing high made a HIGHER price high but a LOWER
    RSI(14) high than the preceding swing high — classic institutional distribution.
    The second swing high must be within the last 3 bars.

    Conditions (all must hold):
      1. Two pivot highs within ``lookback`` bars, detected by pivot_len symmetry.
      2. Price: high2 > high1  (higher high).
      3. RSI: rsi_at_high2 < rsi_at_high1  (lower RSI high — the divergence).
      4. Divergence gap ≥ 3 RSI points.
      5. The second high is within the last 3 bars.
      6. RSI(14) at the second high ≥ 40 (divergence in oversold territory is noise).
      7. RSI on bar[-1] < RSI at bar of the second high (rollover already starting).
    """
    if df is None or len(df) < pivot_len * 2 + 40:
        return None
    df = _clean_ohlc(df)
    if len(df) < pivot_len * 2 + 40:
        return None

    close = df["close"]
    low   = df["low"]
    high  = df["high"]
    n = len(df)
    rsi = _rsi_series(close, 14)
    atr = float(_atr_series(df, 14).iloc[-1])
    if np.isnan(atr) or atr <= 0:
        return None

    search_start = max(pivot_len, n - lookback)
    pivot_highs: list[tuple[int, float, float]] = []
    for i in range(search_start, n - pivot_len):
        window = high.iloc[i - pivot_len: i + pivot_len + 1]
        if float(high.iloc[i]) == float(window.max()):
            rsi_val = float(rsi.iloc[i])
            if not np.isnan(rsi_val):
                pivot_highs.append((i, float(high.iloc[i]), rsi_val))

    if len(pivot_highs) < 2:
        return None

    idx1, price1, rsi1 = pivot_highs[-2]
    idx2, price2, rsi2 = pivot_highs[-1]

    bars_ago = n - 1 - idx2

    if bars_ago > 3:
        return None
    if price2 <= price1:             # no higher high in price
        return None
    if rsi2 >= rsi1:                 # no lower high in RSI
        return None
    rsi_gap = rsi1 - rsi2            # positive gap = magnitude of divergence
    if rsi_gap < 3.0:
        return None
    if rsi2 < 40.0:                  # divergence in oversold is meaningless
        return None

    rsi_now = float(rsi.iloc[-1])
    if np.isnan(rsi_now) or rsi_now >= rsi2:
        return None

    score = 55.0
    if rsi2 >= 65.0:
        score += 15.0
    elif rsi2 >= 55.0:
        score += 8.0
    if rsi_gap >= 10.0:
        score += 10.0
    score += 5.0                     # recency always satisfied (≤3 bar gate)
    score = min(round(score, 1), 95.0)

    entry = round(float(close.iloc[-1]), 2)
    stop  = round(price2 + 0.5 * atr, 2)
    risk  = stop - entry
    target = round(entry - 2.0 * risk, 2) if risk > 0 else None

    swing_low_between = float(low.iloc[idx1:idx2 + 1].min())

    tags = [
        f"RSI div gap -{rsi_gap:.1f}pt",
        f"RSI at high {rsi2:.0f}",
        f"{bars_ago}d ago",
        f"2nd high ₹{price2:.2f}",
    ]
    reasons = [
        f"Price higher high: ₹{price1:.2f} → ₹{price2:.2f}",
        f"RSI(14) lower high: {rsi1:.1f} → {rsi2:.1f} (-{rsi_gap:.1f} pts divergence)",
        f"RSI now {rsi_now:.1f} — rolling over from the divergence high",
        f"Second swing high {bars_ago} bar(s) ago — signal still fresh",
    ]
    if rsi2 >= 65.0:
        reasons.append(f"RSI overbought at the high ({rsi2:.0f}) — strengthens the read")

    return {
        "symbol": df.index[-1] if hasattr(df.index[-1], "__str__") else "?",
        "pattern_type": "RSI Divergence Bear",
        "score": score,
        "tags": tags,
        "reasons": reasons,
        "entry": entry,
        "stop": stop,
        "target": target,
        "time_stop": 10,
        "key_level": round(swing_low_between, 2),
        "rsi_now": round(rsi_now, 1),
        "rsi_at_high": round(rsi2, 1),
        "rsi_gap": round(rsi_gap, 1),
        "bars_since_high": bars_ago,
    }


def scan_rsi_fibo_hidden_div(df: pd.DataFrame, pivot_len: int = 5,
                             lookback: int = 120,
                             fib_tolerance: float = 0.015) -> dict | None:
    """Hidden bullish RSI divergence + 50% Fibonacci retracement confluence.

    Fires when price is in an uptrend, pulls back to the ~50% fib level of the
    last completed swing, AND forms a hidden bullish divergence at that pullback
    — a continuation entry, not a reversal.

    Hidden bullish divergence: price makes a HIGHER low while RSI(14) makes a
    LOWER low. This is the opposite of regular divergence and signals that
    underlying momentum is coiling for continuation despite the RSI dip.

    Confluence with the 50% fib retracement adds a second geometric
    confirmation that institutional demand sits at the equilibrium zone.

    Entry: 38.2% retracement level (after bounce confirmed).
    Stop: below the 61.8% retracement level.
    Target: prior swing high (0% fib level).
    """
    if df is None or len(df) < pivot_len * 2 + 50:
        return None
    df = _clean_ohlc(df)
    if len(df) < pivot_len * 2 + 50:
        return None

    close = df["close"]
    low = df["low"]
    high = df["high"]
    n = len(df)
    rsi = _rsi_series(close, 14)
    atr = float(_atr_series(df, 14).iloc[-1])
    if np.isnan(atr) or atr <= 0:
        return None

    # ── Trend filter: price above 200-EMA ────────────────────────────────────
    if n < 200:
        return None
    ema200 = close.ewm(span=200, adjust=False).mean()
    if float(close.iloc[-1]) < float(ema200.iloc[-1]):
        return None

    # ── Collect swing highs and swing lows ───────────────────────────────────
    search_start = max(pivot_len, n - lookback)

    pivot_highs: list[tuple[int, float]] = []
    for i in range(search_start, n - pivot_len):
        window = high.iloc[i - pivot_len: i + pivot_len + 1]
        if float(high.iloc[i]) == float(window.max()):
            pivot_highs.append((i, float(high.iloc[i])))

    pivot_lows: list[tuple[int, float, float]] = []
    for i in range(search_start, n - pivot_len):
        window = low.iloc[i - pivot_len: i + pivot_len + 1]
        if float(low.iloc[i]) == float(window.min()):
            rsi_val = float(rsi.iloc[i])
            if not np.isnan(rsi_val):
                pivot_lows.append((i, float(low.iloc[i]), rsi_val))

    if len(pivot_lows) < 2 or len(pivot_highs) < 1:
        return None

    # ── Hidden bullish divergence: higher price low + lower RSI low ──────────
    idx1, price_low1, rsi1 = pivot_lows[-2]
    idx2, price_low2, rsi2 = pivot_lows[-1]

    bars_ago = n - 1 - idx2
    if bars_ago > 5:
        return None
    if price_low2 <= price_low1:        # need HIGHER low in price
        return None
    if rsi2 >= rsi1:                    # need LOWER low in RSI
        return None
    rsi_gap = rsi1 - rsi2               # positive = magnitude of hidden divergence
    if rsi_gap < 2.0:
        return None

    # ── Find the swing high between (or just before) the two lows ────────────
    # This defines the fib measurement leg: swing_low1 → swing_high → pullback
    swing_high_idx = None
    swing_high_val = 0.0
    for ph_idx, ph_val in pivot_highs:
        if idx1 <= ph_idx <= idx2 and ph_val > swing_high_val:
            swing_high_idx = ph_idx
            swing_high_val = ph_val
    # If no swing high between the two lows, take the most recent one before low2
    if swing_high_idx is None:
        for ph_idx, ph_val in reversed(pivot_highs):
            if ph_idx < idx2 and ph_val > swing_high_val:
                swing_high_idx = ph_idx
                swing_high_val = ph_val
                break
    if swing_high_idx is None or swing_high_val <= price_low1:
        return None

    # ── Fibonacci retracement levels (measured from swing_low1 → swing_high) ─
    swing_range = swing_high_val - price_low1
    if swing_range <= 0:
        return None

    fib_0   = swing_high_val                              # 0% = swing high
    fib_236 = swing_high_val - 0.236 * swing_range
    fib_382 = swing_high_val - 0.382 * swing_range
    fib_500 = swing_high_val - 0.500 * swing_range
    fib_618 = swing_high_val - 0.618 * swing_range

    # ── Check: did the second low land near the 50% fib? ─────────────────────
    dist_to_50 = abs(price_low2 - fib_500) / swing_range
    if dist_to_50 > fib_tolerance:
        return None

    # ── Bounce confirmation: RSI rising off the hidden-divergence low ────────
    rsi_now = float(rsi.iloc[-1])
    if np.isnan(rsi_now) or rsi_now <= rsi2:
        return None

    cmp = round(float(close.iloc[-1]), 2)

    # ── Trade plan: entry at CMP, stop below 61.8%, target at swing high ─────
    stop = round(fib_618 - 0.3 * atr, 2)
    target = round(fib_0, 2)
    risk = cmp - stop
    if risk <= 0:
        return None
    reward = target - cmp
    rr = round(reward / risk, 1) if risk > 0 else 0.0

    # ── Score ─────────────────────────────────────────────────────────────────
    score = 55.0
    if rsi2 <= 35.0:
        score += 12.0
    elif rsi2 <= 45.0:
        score += 6.0
    if rsi_gap >= 8.0:
        score += 10.0
    elif rsi_gap >= 5.0:
        score += 5.0
    if dist_to_50 < 0.005:             # very tight fib hit
        score += 8.0
    elif dist_to_50 < 0.010:
        score += 4.0
    if rr >= 2.0:
        score += 5.0
    score = min(round(score, 1), 95.0)

    tags = [
        "Hidden Div",
        f"Fib 50% ±{dist_to_50:.1%}",
        f"R:R {rr}×",
        f"RSI {rsi_now:.0f}",
    ]
    reasons = [
        f"Hidden bullish divergence: price higher low ₹{price_low1:.2f} → ₹{price_low2:.2f}, "
        f"RSI lower low {rsi1:.1f} → {rsi2:.1f} (gap {rsi_gap:.1f} pts)",
        f"Pullback held 50% Fibonacci (₹{fib_500:.2f}) — "
        f"2nd swing low at ₹{price_low2:.2f} ({dist_to_50:.1%} from 50%)",
        f"Fib levels: 0%=₹{fib_0:.0f} · 23.6%=₹{fib_236:.0f} · "
        f"38.2%=₹{fib_382:.0f} · 50%=₹{fib_500:.0f} · 61.8%=₹{fib_618:.0f}",
        f"CMP ₹{cmp} · SL ₹{stop} (below 61.8%) · TGT ₹{target} (swing high) · R:R {rr}×",
        f"RSI(14) bouncing: {rsi2:.1f} → {rsi_now:.1f} — momentum resuming",
        f"Trend: above 200-EMA (₹{float(ema200.iloc[-1]):.0f})",
        "⚠ Unmeasured — not yet through the backtest harness",
    ]

    return {
        "pattern_type": "RSI-Fibo Hidden Div",
        "score": score,
        "tags": tags,
        "reasons": reasons,
        "entry": cmp,
        "stop": stop,
        "target": target,
        "time_stop": 15,
        "key_level": round(swing_high_val, 2),
        "rsi_now": round(rsi_now, 1),
        "rsi_at_low": round(rsi2, 1),
        "rsi_gap": round(rsi_gap, 1),
        "bars_since_low": bars_ago,
        "fib_50_level": round(fib_500, 2),
        "fib_382_level": round(fib_382, 2),
        "fib_618_level": round(fib_618, 2),
        "swing_high": round(swing_high_val, 2),
        "rr_ratio": rr,
        "rs_raw": _rs_raw(df),
    }


def scan_order_block(df: pd.DataFrame) -> dict | None:
    """Bullish order block (SMC demand zone) retest entry.

    The last down-close candle *before* a bullish displacement that BREAKS
    STRUCTURE (BOS / CHOCH up) marks where institutions absorbed supply — a
    demand zone price tends to return to and bounce from. This scanner fires when
    a **fresh (unmitigated, not violated) bullish order block is being retested
    right now**: recent price has dipped back into the zone and is holding above
    its low. Reuses the repo's `detect_bos_choch` structure walk and
    `detect_volume_confirmation`. Emits a structured entry/stop/target (stop
    below the zone, target at the displacement extension or 2R). See
    ``concepts/Order-Blocks``.
    """
    if df is None or len(df) < 60:
        return None
    df = _clean_ohlc(df)
    if len(df) < 60:
        return None
    ev = detect_bos_choch(df)
    if ev is None or ev["signal"] not in ("BOS", "CHOCH"):
        return None

    n = len(df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    atr = float(_atr_series(df, 14).iloc[-1])
    if np.isnan(atr) or atr <= 0:
        return None

    bk = n - 1 - ev["bars_ago"]          # the structure-break bar index
    if bk < 3 or bk > n - 2:
        return None

    # Order block = last DOWN-close candle before the break bar (search back ~8).
    ob_idx = None
    for j in range(bk - 1, max(0, bk - 8) - 1, -1):
        if c.iloc[j] < o.iloc[j]:
            ob_idx = j
            break
    if ob_idx is None:
        return None
    ob_low = float(l.iloc[ob_idx])
    ob_high = float(h.iloc[ob_idx])
    if ob_high <= ob_low:
        return None

    # Displacement out of the zone into the break must be a real move (≥ 1 ATR).
    disp_high = float(h.iloc[ob_idx:].max())
    if (disp_high - ob_high) < atr:
        return None

    # Freshness: not yet violated — no close below the zone low after the break.
    after = c.iloc[bk + 1:]
    if len(after) and bool((after < ob_low).any()):
        return None

    # Mitigation NOW: recent low dipped back into the zone and price holds above it.
    last = float(c.iloc[-1])
    recent_low = float(l.tail(3).min())
    if not (recent_low <= ob_high and last >= ob_low):
        return None

    entry = last
    stop = round(ob_low * 0.995, 2)
    risk = entry - stop
    if risk <= 0:
        return None
    target = round(max(disp_high, entry + 2.0 * risk), 2)

    vc = detect_volume_confirmation(df)
    vol_ok = bool(vc and vc["pass"])
    vol20 = float(df["volume"].tail(20).mean())
    vol_x = float(df["volume"].iloc[-1]) / vol20 if vol20 > 0 else 0.0

    # ── Score (0-100) — displacement strength · volume · freshness · location ──
    disp_strength = min((disp_high - ob_high) / atr, 3.0) / 3.0
    bars_since = n - 1 - ob_idx
    fresh = 1.0 if 3 <= bars_since <= 20 else (0.5 if bars_since <= 30 else 0.2)
    zone_pos = (last - ob_low) / (ob_high - ob_low) if ob_high > ob_low else 0.5
    prox = max(0.0, 1.0 - abs(min(zone_pos, 1.5) - 0.5))   # best entering mid-zone
    base = 10.0 + 35.0 * disp_strength + (20.0 if vol_ok else 0.0) + 20.0 * fresh + 15.0 * prox

    reasons = [
        f"Bullish {ev['signal']} — displacement broke structure at ₹{ev['level']:.0f}",
        f"Demand zone ₹{ob_low:.0f}–₹{ob_high:.0f} (last down candle before the move), "
        f"unmitigated {bars_since} bars",
        "Price retesting the order block and holding above the zone low",
        (f"Displacement backed by volume ({vc['best_up_rvol']:.1f}× avg)" if vol_ok
         else "⚠ Displacement volume unconfirmed — weaker order block"),
        f"Trade plan — entry {entry:.0f} · stop {stop:.0f} · target {target:.0f} "
        f"(R:R {(target - entry) / risk:.1f})",
    ]
    return {
        "pattern_type": f"Bullish Order Block · {ev['signal']}",
        "tags": ["Order Block", ev["signal"], f"Zone {ob_low:.0f}-{ob_high:.0f}"],
        "reasons": reasons,
        "score_base": round(min(100.0, base), 1),
        "score": round(min(100.0, base), 1),   # provisional — run_scanner blends in RS
        "rs_raw": _rs_raw(df),
        "entry": round(entry, 2),
        "stop": stop,
        "target": target,
        "vol_x50d": round(vol_x, 2),
        # B-5: SMC order-block trades should resolve promptly; 10 bars without
        # follow-through means the zone is not acting as support.
        "time_stop": 10,
    }


def detect_order_blocks(df: pd.DataFrame, pivot_len: int = 5,
                        min_disp_atr: float = 1.0, max_ob_search: int = 8,
                        max_blocks: int = 14) -> list[dict]:
    """All order blocks (bullish demand + bearish supply) in the window, for the
    chart overlay — the multi-zone sibling of ``scan_order_block`` (which returns
    only the single 'retest now' bullish signal).

    Walks the same SMC swing structure as ``detect_bos_choch``: whenever a close
    breaks the most recent confirmed swing (up = bullish break, down = bearish),
    the **last opposing-close candle before the break** is the order block — the
    candle where institutions absorbed the other side before the displacement.
    Each block keeps its full high-low zone, the BOS/CHOCH label, an ATR-measured
    displacement gate (≥ ``min_disp_atr`` ATR out of the zone), and its mitigation
    state: ``mitigated`` once price trades back INTO the zone after the break
    (``mit_idx`` = first such bar). Blocks fully violated (a close beyond the far
    side of the zone) are dropped — they are no longer valid order blocks.

    Every non-violated zone also carries a trade plan — ``entry`` (the zone edge
    price retests), ``stop`` just beyond the far side, and ``target`` at a flat 2R.
    MEASURED 2026-09-13 at **-0.095R net of costs** (+0.026R gross, n=271): the
    plan does not survive its own costs, and the opposing-zone / displacement
    target rules it replaced measured no better — the displacement target was the
    only one significantly negative (-0.164R, p=0.037). Drawn as the detector's
    geometry, not as a recommendation. See ``analyses/Order-Block-Rules-Measured``.

    Returns a list of dicts (bar indices, mapped to timestamps by the caller),
    most-recent last, capped at ``max_blocks``. Bearish is the exact mirror of
    bullish. See ``concepts/Order-Blocks``.
    """
    if df is None or len(df) < pivot_len * 4 + 20:
        return []
    df = _clean_ohlc(df)
    n = len(df)
    if n < pivot_len * 4 + 20:
        return []
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    vol = df["volume"] if "volume" in df.columns else pd.Series([0.0] * n, index=df.index)
    atr = _atr_series(df, 14)

    swing_high: float | None = None
    swing_low: float | None = None
    trend = 0
    raw: list[dict] = []

    for i in range(pivot_len * 2, n):
        j = i - pivot_len          # a pivot is confirmed pivot_len bars later
        if j >= pivot_len:
            if h.iloc[j] == h.iloc[j - pivot_len: j + pivot_len + 1].max():
                swing_high = float(h.iloc[j])
            if l.iloc[j] == l.iloc[j - pivot_len: j + pivot_len + 1].min():
                swing_low = float(l.iloc[j])
        a = float(atr.iloc[i]) if not np.isnan(atr.iloc[i]) else 0.0
        close_i = float(c.iloc[i])

        # ── Bullish break → look back for the last DOWN candle = demand block ──
        if swing_high is not None and close_i > swing_high and a > 0:
            ob_idx = None
            for k in range(i - 1, max(0, i - max_ob_search) - 1, -1):
                if c.iloc[k] < o.iloc[k]:
                    ob_idx = k
                    break
            if ob_idx is not None:
                ob_lo, ob_hi = float(l.iloc[ob_idx]), float(h.iloc[ob_idx])
                disp = float(h.iloc[ob_idx:i + 1].max()) - ob_hi
                if ob_hi > ob_lo and disp >= min_disp_atr * a:
                    buy_ratio = _buy_sell_ratio(o, c, vol, ob_idx, pivot_len)
                    raw.append({"dir": "bull", "ob_idx": ob_idx, "break_idx": i,
                                "low": ob_lo, "high": ob_hi,
                                "signal": "BOS" if trend == 1 else "CHOCH",
                                "disp_atr": round(disp / a, 2),
                                "ext": ob_hi + disp,
                                "vol_x": _vol_x(vol, i),
                                "buy_pct": round(buy_ratio * 100, 1),
                                "sell_pct": round((1 - buy_ratio) * 100, 1)})
            trend = 1
            swing_high = None
        # ── Bearish break → look back for the last UP candle = supply block ──
        elif swing_low is not None and close_i < swing_low and a > 0:
            ob_idx = None
            for k in range(i - 1, max(0, i - max_ob_search) - 1, -1):
                if c.iloc[k] > o.iloc[k]:
                    ob_idx = k
                    break
            if ob_idx is not None:
                ob_lo, ob_hi = float(l.iloc[ob_idx]), float(h.iloc[ob_idx])
                disp = ob_lo - float(l.iloc[ob_idx:i + 1].min())
                if ob_hi > ob_lo and disp >= min_disp_atr * a:
                    buy_ratio = _buy_sell_ratio(o, c, vol, ob_idx, pivot_len)
                    raw.append({"dir": "bear", "ob_idx": ob_idx, "break_idx": i,
                                "low": ob_lo, "high": ob_hi,
                                "signal": "BOS" if trend == -1 else "CHOCH",
                                "disp_atr": round(disp / a, 2),
                                "ext": ob_lo - disp,
                                "vol_x": _vol_x(vol, i),
                                "buy_pct": round(buy_ratio * 100, 1),
                                "sell_pct": round((1 - buy_ratio) * 100, 1)})
            trend = -1
            swing_low = None

    # ── Mitigation + violation pass ──────────────────────────────────────────
    # State (not a drop): fresh = never returned to; mitigated = price tapped the
    # zone but hasn't closed through; violated = price closed beyond the far side
    # (the zone failed). All three are kept so the overlay shows the full history;
    # the caller fades mitigated and greys violated.
    out: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for ob in raw:
        dedup = (ob["dir"], ob["ob_idx"])
        if dedup in seen:
            continue
        seen.add(dedup)
        mit_idx = None
        vio_idx = None
        for m in range(ob["break_idx"] + 1, n):
            if ob["dir"] == "bull":
                if mit_idx is None and float(l.iloc[m]) <= ob["high"]:
                    mit_idx = m                       # tapped the zone
                if float(c.iloc[m]) < ob["low"]:
                    vio_idx = m                       # closed through → failed
                    break
            else:
                if mit_idx is None and float(h.iloc[m]) >= ob["low"]:
                    mit_idx = m
                if float(c.iloc[m]) > ob["high"]:
                    vio_idx = m
                    break
        ob["state"] = ("violated" if vio_idx is not None
                       else "mitigated" if mit_idx is not None else "fresh")
        ob["mit_idx"] = mit_idx
        ob["vio_idx"] = vio_idx
        out.append(ob)

    out = out[-max_blocks:]

    # ── Retest signals ──────────────────────────────────────────────────────
    # Two entries per zone, and they are NOT the same trade:
    #   * ``early``     — the rejection itself: a bar whose wick pierced the zone
    #                     but which CLOSED back outside it, without breaching the
    #                     far side. Fires at the tap, so it is earlier and looser.
    #   * ``confirmed`` — Pine's cross: bullish = low crosses above the OB top
    #                     (price reclaims demand), bearish = high crosses below
    #                     the OB bottom. Fires after price has left the zone.
    # Both gated by the buy%/sell% threshold (default 50%), first of each kind
    # only, on non-violated zones. See ``concepts/Order-Blocks``.
    retests: list[dict] = []
    for ob in out:
        if ob["state"] == "violated":
            continue
        buy_ratio = ob.get("buy_pct", 50.0) / 100.0
        side_ratio = buy_ratio if ob["dir"] == "bull" else 1.0 - buy_ratio
        if side_ratio < 0.5:
            continue
        end = ob["vio_idx"] if ob["vio_idx"] is not None else n
        got_early = got_confirmed = False
        for m in range(ob["break_idx"] + 1, end):
            lo_m, hi_m, cl_m = float(l.iloc[m]), float(h.iloc[m]), float(c.iloc[m])
            if ob["dir"] == "bull":
                if (not got_early and ob["low"] <= lo_m <= ob["high"]
                        and cl_m > ob["high"]):
                    retests.append({"dir": "bull", "idx": m, "kind": "early",
                                    "ob_idx": ob["ob_idx"],
                                    "price": lo_m,
                                    "buy_pct": ob.get("buy_pct", 50.0)})
                    got_early = True
                if not got_confirmed:
                    prev_low = float(l.iloc[m - 1]) if m > 0 else lo_m
                    if prev_low <= ob["high"] and lo_m > ob["high"]:
                        retests.append({"dir": "bull", "idx": m, "kind": "confirmed",
                                    "ob_idx": ob["ob_idx"],
                                        "price": ob["high"],
                                        "buy_pct": ob.get("buy_pct", 50.0)})
                        got_confirmed = True
            else:
                if (not got_early and ob["low"] <= hi_m <= ob["high"]
                        and cl_m < ob["low"]):
                    retests.append({"dir": "bear", "idx": m, "kind": "early",
                                    "ob_idx": ob["ob_idx"],
                                    "price": hi_m,
                                    "sell_pct": ob.get("sell_pct", 50.0)})
                    got_early = True
                if not got_confirmed:
                    prev_high = float(h.iloc[m - 1]) if m > 0 else hi_m
                    if prev_high >= ob["low"] and hi_m < ob["low"]:
                        retests.append({"dir": "bear", "idx": m, "kind": "confirmed",
                                    "ob_idx": ob["ob_idx"],
                                        "price": ob["low"],
                                        "sell_pct": ob.get("sell_pct", 50.0)})
                        got_confirmed = True
            if got_early and got_confirmed:
                break

    # ── Trade plan per live zone ─────────────────────────────────────────────
    # Entry at the edge price returns to (demand top / supply bottom), stop just
    # beyond the far side of the zone, target a flat 2R.
    #
    # MEASURED 2026-09-13 — see ``analyses/Order-Block-Rules-Measured``. This was
    # a three-step ladder: nearest still-live opposing zone, else the displacement
    # extension, else 2R. All three were measured PAIRED — same zone, same entry,
    # same stop, only the target varying — over 270 filled plans on LIQUID_50 /
    # 1500d. Against flat 2R the opposing-zone target came in at **-0.019R
    # (p=0.76)** and the displacement target at **-0.058R (p=0.26)**. The three
    # targets are genuinely different distances (target-hit 26.3% / 38.1% / 33.7%)
    # and expectancy is flat across all of them, so the ladder bought nothing but
    # the appearance of structure. Collapsed to the simplest rule that measured
    # the same thing. Net of NSE delivery costs the ordering is unchanged and the
    # paired deltas stay null (-0.030R p=0.64, -0.069R p=0.19).
    #
    # The expectancy itself is **-0.095R net** of costs (+0.026R gross, p=0.27 /
    # p=0.76) — a plan that does not survive its own costs, let alone carry an
    # edge. Nothing here licenses trading it. ``ext`` stays on the block so the
    # measurement is reproducible.
    for ob in out:
        if ob["state"] == "violated":
            continue
        if ob["dir"] == "bull":
            entry = ob["high"]
            stop = round(ob["low"] * 0.995, 2)
            risk = entry - stop
            if risk <= 0:
                continue
            target = entry + 2.0 * risk
        else:
            entry = ob["low"]
            stop = round(ob["high"] * 1.005, 2)
            risk = stop - entry
            if risk <= 0:
                continue
            target = entry - 2.0 * risk
        ob["entry"]  = round(entry, 2)
        ob["stop"]   = stop
        ob["target"] = round(target, 2)

    return out, retests


def _vol_x(vol: pd.Series, i: int, avg_len: int = 20) -> float:
    """Break-bar volume as a multiple of the trailing average (0 if unavailable)."""
    lo = max(0, i - avg_len)
    avg = float(vol.iloc[lo:i].mean()) if i > lo else 0.0
    return round(float(vol.iloc[i]) / avg, 2) if avg > 0 else 0.0


def _buy_sell_ratio(o: pd.Series, c: pd.Series, vol: pd.Series,
                    center: int, half_win: int) -> float:
    """Buy-volume ratio in a window around *center* (Pine: get_window_volume_ratio).
    Returns 0.0–1.0; buy = close >= open bars' volume / total volume."""
    lo = max(0, center - half_win)
    hi = min(len(o), center + half_win + 1)
    buy = sell = 0.0
    for k in range(lo, hi):
        v = float(vol.iloc[k])
        if float(c.iloc[k]) >= float(o.iloc[k]):
            buy += v
        else:
            sell += v
    total = buy + sell
    return round(buy / total, 3) if total > 0 else 0.5


def detect_falling_wedge_geometry(df: pd.DataFrame, window: int = 60,
                                  touch_tol: float = 0.015) -> dict | None:
    """Falling-wedge detection core → geometry dict, or None.

    Shared by ``scan_falling_wedge`` (the hub card) and the ``/api/falling_wedge``
    chart overlay (FW-3). **Assumes a clean OHLCV frame** (the caller drops NaN rows).
    Returns the upper/lower trendline endpoints as **bar indices into the passed df**
    (+ prices) so the chart can map them to timestamps, plus the breakout state, a
    0-100 confidence, the metric surface, and the trade plan. See
    ``concepts/Falling-Wedge`` for the algorithm.
    """
    if df is None or len(df) < window:
        return None
    n = window
    off = len(df) - n                            # abs bar index of the window's first bar
    w = df.tail(window).reset_index(drop=True)
    high = w["high"].to_numpy(float)
    low = w["low"].to_numpy(float)
    close = w["close"].to_numpy(float)
    n = len(w)
    last = float(close[-1])
    if last <= 0:
        return None

    # 1) Swing pivots (look-back 1). The last bar can't be a confirmed pivot.
    sh = [(i, high[i]) for i in range(1, n - 1) if high[i] > high[i - 1] and high[i] > high[i + 1]]
    sl = [(i, low[i]) for i in range(1, n - 1) if low[i] < low[i - 1] and low[i] < low[i + 1]]
    if len(sh) < 2 or len(sl) < 2:
        return None

    # 2) Fit upper through the last ≤3 swing highs, lower through the last ≤3 swing lows.
    hx = np.array([p[0] for p in sh[-3:]], float); hy = np.array([p[1] for p in sh[-3:]], float)
    lx = np.array([p[0] for p in sl[-3:]], float); ly = np.array([p[1] for p in sl[-3:]], float)
    su, iu = np.polyfit(hx, hy, 1)
    slo, il = np.polyfit(lx, ly, 1)

    def u(x): return iu + su * x
    def lo(x): return il + slo * x

    # 3) Geometric validation.
    if not (su < 0 and slo < 0):                 # both trendlines must fall
        return None
    if su >= slo:                                # upper must be steeper (more negative)
        return None
    x0 = int(min(hx.min(), lx.min()))            # oldest fitted swing (bar index)
    x1 = n - 1                                   # current bar (last)
    if (x1 - x0) < 15:                           # a wedge must span real time, not 5 bars
        return None
    gap_old = u(x0) - lo(x0)
    gap_now = u(x1) - lo(x1)
    if gap_old <= 0 or gap_now <= 0 or gap_now >= gap_old:   # must be open + converging
        return None
    conv_ratio = (gap_old - gap_now) / gap_old
    if conv_ratio < 0.10:                        # too parallel — a channel, not a wedge
        return None

    # Touches: pivots sitting within tolerance of their line (≥2 each required).
    tu = sum(1 for i, p in sh if abs(p - u(i)) <= touch_tol * p)
    tl = sum(1 for i, p in sl if abs(p - lo(i)) <= touch_tol * p)
    if tu < 2 or tl < 2:
        return None

    # 4) Confidence factors (0-1 each), weighted blend documented below.
    steep_ratio = su / slo                                   # >1 when upper steeper
    inside = 0
    for i in range(n):
        if high[i] <= u(i) * (1 + touch_tol) and low[i] >= lo(i) * (1 - touch_tol):
            inside += 1
    containment = inside / n
    if containment < 0.55:                       # lines don't actually bound price → not a wedge
        return None

    # Volume behaviour (FW-2) — a real wedge CONTRACTS into the apex (dry-up) then
    # expands on breakout, the VCP-style tell. Compare early- vs late-window volume,
    # excluding the last (breakout) bar so its spike can't mask the into-apex dry-up.
    vol_arr = w["volume"].to_numpy(float) if "volume" in w.columns else np.zeros(n)
    third = max(5, n // 3)
    vol_early = float(np.mean(vol_arr[:third])) if third else 0.0
    vol_late = (float(np.mean(vol_arr[-third - 1:-1])) if n > third + 1
                else float(np.mean(vol_arr[-third:])))
    vol_trend = (vol_late / vol_early) if vol_early > 0 else 1.0
    if vol_trend > 1.30:                         # volume RISING into the apex → not a valid coil
        return None
    vol_dry = vol_trend <= 0.90

    last_piv = max(sh[-1][0], sl[-1][0])
    recency = max(0.0, 1.0 - (n - 1 - last_piv) / window)
    touch_score = min(1.0, (tu + tl) / 6.0)                  # 2+2 → .67, 3+3 → 1.0
    conv_score = min(1.0, conv_ratio / 0.5)                  # 50% narrowing → full
    steep_score = min(1.0, max(0.0, (steep_ratio - 1.0) / 1.5))
    vol_score = min(1.0, max(0.0, (1.0 - vol_trend) / 0.30))  # 0.70×→1.0, ≥1.0×→0
    # Weights: containment .28 · convergence .22 · touches .18 · steepness .12
    #          · volume-dry-up .12 · recency .08  (sum 1.0).
    conf = 100.0 * (0.28 * containment + 0.22 * conv_score + 0.18 * touch_score +
                    0.12 * steep_score + 0.12 * vol_score + 0.08 * recency)

    # 5) Breakout state + actionability gate.
    u_now, l_now = u(x1), lo(x1)
    pos = (last - l_now) / (u_now - l_now)                   # 0 lower … 1 upper line
    if last > u_now:
        state, state_lbl, bonus = "confirmed", "Breakout", 8.0
    elif (u_now - last) / u_now <= 0.005:
        state, state_lbl, bonus = "pre-breakout", "Pre-Breakout", 4.0
    elif pos >= 0.5:
        state, state_lbl, bonus = "forming", "Forming", 0.0
    else:
        return None                                          # deep in the wedge — not actionable
    conf = min(100.0, conf + bonus)

    # Trade plan — enter on/above the upper line, stop below the lower line,
    # target = measured move (wedge height at its widest).
    entry = round(max(last, u_now), 2)
    recent_low = float(low[-10:].min())
    stop = round(min(l_now, recent_low) * 0.995, 2)
    if entry <= stop:
        return None
    target = round(entry + gap_old, 2)
    rr = (target - entry) / (entry - stop)

    vol20 = float(w["volume"].tail(20).mean()) if "volume" in w.columns else 0.0
    vol_last = float(w["volume"].iloc[-1]) if "volume" in w.columns else 0.0
    vol_x = vol_last / vol20 if vol20 > 0 else 0.0

    return {
        # Trendline endpoints as bar indices into the passed df (+ prices) — FW-3 overlay.
        "upper_x0": off + x0, "upper_y0": round(u(x0), 2),
        "upper_x1": off + x1, "upper_y1": round(u_now, 2),
        "lower_x0": off + x0, "lower_y0": round(lo(x0), 2),
        "lower_x1": off + x1, "lower_y1": round(l_now, 2),
        "breakout_bar": off + x1, "last_close": round(last, 2),
        # Scalars for the card text + metric surface.
        "upper_slope": su, "lower_slope": slo,
        "gap_old": gap_old, "gap_now": gap_now, "conv_ratio": conv_ratio,
        "containment": containment, "touches_h": tu, "touches_l": tl,
        "vol_trend": vol_trend, "vol_dry": vol_dry, "vol_x": vol_x,
        "state": state, "state_label": state_lbl, "confidence": conf,
        "entry": entry, "stop": stop, "target": target, "rr": rr,
        "u_now": u_now, "l_now": l_now,
    }


def scan_falling_wedge(df: pd.DataFrame, window: int = 60,
                       touch_tol: float = 0.015) -> dict | None:
    """Falling wedge — two converging DOWNWARD trendlines → bullish breakout.

    Thin hub-card wrapper over ``detect_falling_wedge_geometry`` (which the
    ``/api/falling_wedge`` chart overlay shares). Cleans the frame, runs the
    detection core, and formats the card (pattern + tags + reasons + trade plan +
    the FW-2 metric surface). See ``concepts/Falling-Wedge`` /
    ``analyses/Falling-Wedge-Scanner-Fit``.
    """
    if df is None:
        return None
    df = _clean_ohlc(df)
    g = detect_falling_wedge_geometry(df, window, touch_tol)
    if g is None:
        return None
    su, slo = g["upper_slope"], g["lower_slope"]
    gap_old, gap_now, conv_ratio = g["gap_old"], g["gap_now"], g["conv_ratio"]
    containment = g["containment"]
    tu, tl = g["touches_h"], g["touches_l"]
    vol_trend, vol_dry, vol_x = g["vol_trend"], g["vol_dry"], g["vol_x"]
    state, state_lbl = g["state"], g["state_label"]
    last, u_now = g["last_close"], g["u_now"]
    entry, stop, target, rr = g["entry"], g["stop"], g["target"], g["rr"]

    reasons = [
        f"Falling wedge — converging down-lines (upper slope {su:.2f} steeper than lower {slo:.2f})",
        f"Gap narrowed {conv_ratio * 100:.0f}% (widest {gap_old:.0f} → now {gap_now:.0f})",
        f"{tu} upper / {tl} lower touches · containment {containment * 100:.0f}%",
        {"confirmed":    f"Breakout — close {last:.0f} cleared the upper line {u_now:.0f}",
         "pre-breakout": f"Pre-breakout — {last:.0f} within 0.5% of the upper line {u_now:.0f}",
         "forming":      f"Forming — price in the upper half; upper line at {u_now:.0f}"}[state],
        f"Trade plan — entry {entry:.0f} · stop {stop:.0f} · target {target:.0f} "
        f"(measured move, R:R {rr:.1f})",
    ]
    reasons.append(
        f"Volume drying into the apex ({vol_trend:.2f}× early-window) — healthy contraction"
        if vol_dry else
        f"⚠ Volume flat/rising into the apex ({vol_trend:.2f}× early-window) — weaker wedge")
    if vol_x >= 1.5 and state == "confirmed":
        reasons.append(f"Breakout volume {vol_x:.1f}× 20-day average — expansion on the break")

    return {
        "pattern_type": f"Falling Wedge · {state_lbl}",
        "tags": ["Falling Wedge", state_lbl,
                 f"Contain {containment * 100:.0f}%", f"Conv {conv_ratio * 100:.0f}%",
                 f"{tu}H/{tl}L touches", ("Vol dry↓" if vol_dry else "Vol flat")],
        "reasons": reasons,
        "score_base": round(g["confidence"], 1),
        "rs_raw": _rs_raw(df),
        "entry": entry,
        "stop": stop,
        "target": target,
        "vol_x50d": round(vol_x, 2),
        # FW-2 metric surface.
        "containment_pct": round(containment * 100, 1),
        "convergence_pct": round(conv_ratio * 100, 1),
        "touches_h": tu,
        "touches_l": tl,
        "vol_trend": round(vol_trend, 2),
        "vol_dry": vol_dry,
        # B-5: wedge breakouts extend fast or fail; 20 bars (4 weeks) captures
        # the initial impulse — beyond that the measured-move premise is stale.
        "time_stop": 20,
    }


def scan_ema50_coil(df: pd.DataFrame) -> dict | None:
    """EMA-50 coiled-spring breakout — Ashok Daniel StockEdge scanner.

    Captures quality stocks resting near their 50-EMA floor that break out on
    institutional volume before the trend becomes obvious.  The key gate is
    ``Close within 2% of EMA-50`` — it is NOT a chase scanner; it fires on the
    rest-before-thrust zone, not after extension.

    Gates:
      1. Close > EMA200 — broad uptrend context
      2. ADX(14) > 25 — the trend is actionable
      3. Close within 2% above OR below EMA-50 (the coil zone)
      4. Close > 1.03× prior close AND volume > 20-day avg — breakout thrust
         confirmed by price AND participation simultaneously

    ── Fixed 2026-08-29: it fired ZERO times in 2,496 cells ─────────────────
    The port carried two gates the source does not have — **ADX rising vs the prior
    bar** and **+DI > −DI** — and they contradict this scanner's own premise. A stock
    whose ADX is high *and still accelerating* is, by construction, extended away from
    its 50-EMA; this scanner exists to catch the opposite state, price resting ON that
    mean before the thrust. Measured: 375 cells cleared ADX-rising + DI, and exactly
    **1** of those was also within 2% of the EMA-50. Removing the two undocumented
    gates restores the source (Ashok Daniel's StockEdge screen: ADX > 25, close within
    2% of EMA-50, close > 1.03× prior on above-average volume).

    It remains a genuinely RARE setup — ~0.2% of cells, ~5 hits per 2,496 — because
    "resting at the mean" and "thrusting 3% today" only coincide when a stock gaps up
    into its 50-EMA from below. That is the setup, not a defect. `close > EMA200` is
    kept as context (it costs 8 hits → 5) and is deliberately not dropped to chase a
    higher fire rate.
    """
    if len(df) < 60 or "volume" not in df.columns:
        return None
    close = df["close"].astype(float)
    last  = float(close.iloc[-1])

    ema50  = float(_ema_series(close, 50).iloc[-1])
    ema200 = float(_ema_series(close, 200).iloc[-1])
    if np.isnan(ema50) or np.isnan(ema200):
        return None

    # Gate 1 — broad uptrend
    if last < ema200:
        return None

    # Gate 2 — ADX > 25. Deliberately NOT "and rising", and no +DI/−DI gate: both
    # were undocumented additions and both select for an extended stock, which is the
    # opposite of the coil this scanner looks for (see the docstring).
    if len(df) < 50:
        return None
    plus_di, minus_di, adx = _adx_di_series(df)
    adx_now  = float(adx.iloc[-1])
    adx_prev = float(adx.iloc[-2])
    pdi_now  = float(plus_di.iloc[-1])
    mdi_now  = float(minus_di.iloc[-1])
    if np.isnan(adx_now) or np.isnan(pdi_now):
        return None
    if adx_now < 25:
        return None

    # Gate 4 — close within 2% of EMA-50 (above OR below — the coil can form
    # just under or just at the EMA; the volume thrust is the confirmation)
    dist_pct = (last - ema50) / ema50 * 100      # + above, - below
    if abs(dist_pct) > 2.0:
        return None

    # Gate 5 — breakout thrust: >3% from prior close on above-average volume
    prior_close = float(close.iloc[-2])
    if prior_close <= 0:
        return None
    move_pct = (last - prior_close) / prior_close * 100
    if move_pct < 3.0:
        return None
    vol_avg_20 = float(df["volume"].tail(20).mean())
    vol_last   = float(df["volume"].iloc[-1])
    if vol_avg_20 <= 0 or vol_last < vol_avg_20:
        return None
    vol_x = vol_last / vol_avg_20

    zone = "at" if abs(dist_pct) <= 0.5 else ("above" if dist_pct > 0 else "below")
    reasons = [
        f"Price ({last:.1f}) {zone} EMA50 ({ema50:.1f}) — resting in the coil zone "
        f"({dist_pct:+.1f}%)",
        f"ADX {adx_now:.0f} (prior {adx_prev:.0f}), +DI {pdi_now:.0f} vs −DI {mdi_now:.0f} "
        f"— trend is actionable; direction comes from the thrust, not the DI spread",
        f"Thrust: +{move_pct:.1f}% vs prior close on {vol_x:.1f}× 20-day volume — "
        "institutional breakout signal",
        f"Above EMA200 ({ema200:.1f}) — long-term uptrend intact",
    ]
    # Base score: combine ADX strength, DI spread and volume quality
    di_spread = pdi_now - mdi_now
    score_base = round(
        min(adx_now - 25, 30) * 0.8       # ADX premium above 25, capped at 30 pts
        + min(di_spread, 20) * 0.5         # DI spread quality
        + min(move_pct, 10) * 1.0          # thrust magnitude, cap 10 pts
        + min(vol_x, 3.0) * 5.0,           # volume conviction, cap 3× → 15 pts
        1,
    )
    score_base = float(max(0.0, min(score_base, 100.0)))
    return {
        "pattern_type": "EMA-50 Coil",
        "tags": [f"ADX {adx_now:.0f}", f"+DI>{mdi_now:.0f}", f"{dist_pct:+.1f}% of EMA50",
                 f"{move_pct:.1f}% thrust", f"{vol_x:.1f}× vol"],
        "reasons": reasons,
        "score_base": score_base,
        "score": score_base,
        "rs_raw": round(_rs_raw(df), 3),
        "adx": round(adx_now, 1),
        "plus_di": round(pdi_now, 1),
        "minus_di": round(mdi_now, 1),
        "dist_to_ema50_pct": round(dist_pct, 2),
        "thrust_pct": round(move_pct, 2),
        "vol_x20d": round(vol_x, 2),
    }


def scan_mfi_oversold(df: pd.DataFrame,
                      n: int = 14,
                      oversold: float = 20.0) -> dict | None:
    """Money Flow Index (MFI) oversold-recovery scanner.

    Fires when MFI crosses UP from below `oversold` (default 20) with a
    positive close vs prior day.  MFI = volume-weighted RSI on typical
    price — it catches exhaustion exits where price dips coincide with
    heavy selling volume that then dries up (reversal signal).

    Gates:
      1. MFI(n) crossed above `oversold` (was below, now above)
      2. Close > prior close (up day confirmation)
      3. Volume at least average (no low-conviction recovery)

    Returns None when gates don't fire.
    """
    if len(df) < n + 5:
        return None

    mfi = _mfi_series(df, n)
    if mfi.isna().all():
        return None

    mfi_now  = float(mfi.iloc[-1])
    mfi_prev = float(mfi.iloc[-2]) if len(mfi) >= 2 else mfi_now
    close    = df["close"].astype(float)
    vol      = df["volume"].astype(float)

    c_now   = float(close.iloc[-1])
    c_prev  = float(close.iloc[-2])
    vol_now = float(vol.iloc[-1])
    vol_avg = float(vol.rolling(20).mean().iloc[-1]) if len(vol) >= 20 else float(vol.mean())

    # Gate 1 — MFI crossover above oversold
    if not (mfi_prev < oversold <= mfi_now):
        return None
    # Gate 2 — up-day confirmation
    if c_now <= c_prev:
        return None
    # Gate 3 — at least average volume
    vol_x = vol_now / vol_avg if vol_avg > 0 else 0.0
    if vol_x < 1.0:
        return None

    headroom = 80.0 - mfi_now        # distance to overbought
    score = min(100, int(50 + (oversold - mfi_prev) * 2 + headroom * 0.5))

    return {
        "pattern_type": "MFI Oversold Recovery",
        "tags": ["MFI-cross", f"MFI {mfi_now:.0f}"],
        "reasons": [
            f"MFI crossed {oversold:.0f} from below ({mfi_prev:.1f} → {mfi_now:.1f}); "
            f"up-day +{(c_now/c_prev - 1)*100:.1f}%; vol {vol_x:.1f}×20d-avg"
        ],
        "score_base": score,
        "score": score,
        "mfi_now": round(mfi_now, 1),
        "mfi_prev": round(mfi_prev, 1),
        "vol_x20d": round(vol_x, 2),
    }


def _anchored_vwap(df: pd.DataFrame, anchor_idx: int) -> pd.Series:
    """Anchored VWAP — cumulative volume-weighted typical price from ``anchor_idx``
    to the end.  This is the *daily* VWAP concept (Brian Shannon): a session VWAP
    is meaningless on daily bars (one bar = one session), so the mean price a swing
    leg is measured against is the volume-weighted average since the leg's origin.

    Returns a Series aligned to ``df.index`` — NaN before ``anchor_idx``, the
    cumulative AVWAP from the anchor onward.  Needs high/low/close/volume.
    """
    tp  = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
    vol = df["volume"].astype(float)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    seg_tp  = tp.iloc[anchor_idx:]
    seg_vol = vol.iloc[anchor_idx:]
    num = (seg_tp * seg_vol).cumsum()
    den = seg_vol.cumsum().replace(0.0, np.nan)
    out.iloc[anchor_idx:] = (num / den).to_numpy()
    return out


def _rolling_vwap(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """Rolling n-day VWAP — volume-weighted typical price over a trailing window.

    Unlike an anchored VWAP (which sits far below price once a trend has run), the
    rolling VWAP tracks recent price, so price genuinely oscillates around it — the
    mean a daily pullback/reclaim entry is measured against.  Returns a Series
    aligned to ``df.index`` (NaN through the first n-1 bars).
    """
    tp  = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
    vol = df["volume"].astype(float)
    num = (tp * vol).rolling(n).sum()
    den = vol.rolling(n).sum().replace(0.0, np.nan)
    return num / den


def scan_vwap_reclaim(df: pd.DataFrame,
                      vwap_n: int = 20,
                      touch_tol: float = 0.01,
                      extend_cap: float = 0.06) -> dict | None:
    """Rolling-VWAP reclaim / pullback-support — the VWAP-as-signal entry (B-40).

    On daily bars a session VWAP is meaningless (one bar = one session), so the
    tradeable mean is a rolling n-day VWAP: in a healthy trend price rides above it
    and pulls back TO it, not through it.  That mean is what the classic
    trend+pullback entry actually leans on — not just an EMA.  Fires on either of
    two long events at the rising VWAP:

      * **reclaim**   — close was below VWAP and has crossed back above it, or
      * **pullback-hold** — a recent bar's low tagged VWAP (within ``touch_tol``)
        and price is bouncing (close back above VWAP and up on the day).

    Gates (all required):
      1. Trend context — close > EMA-50 (with-trend only; not a bottom-fisher).
      2. VWAP rising over the last 10 bars (the leg is intact).
      3. Not extended — close ≤ (1 + ``extend_cap``) × VWAP, so it's an entry near
         the mean, not a chase.
      4. One of the two events above fired, with volume ≥ 20-day average on a reclaim.

    MEASURED 2026-09-06 (B-40) -- NEGATIVE, NOT MERELY NULL.  50 symbols, **2745
    signals**: forward edge is negative at every horizon and significantly so at
    three of four -- -0.02% @5d (p=0.77), **-0.20% @10d (p=0.042)**, **-0.45%
    @20d (p=0.0006)**, **-0.50% @60d (p=0.033)**.  Net of Indian delivery costs
    the median is negative at 5/10/20d and the hit rate is under 50%.

    Read it plainly: a VWAP reclaim does not merely fail to predict, it selects
    bars that do WORSE than a random bar from the same pool.  The -0.45% @20d at
    p=0.0006 is the most statistically solid number this desk has on a VWAP rule
    in either direction.

    Two things explain the shape.  It fires 2745 times against VWAP Mean
    Reversion's 275, so the gates are loose -- closer to "a stock in an uptrend
    near its mean" than to an event -- which is also why the small negative is
    detectable at all.  And the design note below records that the first cut
    never fired and the gates were loosened until it did; this is what that
    bought.

    NOT a licence to fade reclaims.  That is a different claim needing its own
    pre-registered test, and -0.45% would not survive costs on the short side.

    Kept for coverage and context, but listed in ``opportunity_hub.PIPELINE_EXCLUDED``
    so it can never become a confluence vote -- the same enforcement Renko Flip gets
    for the same reason, one step further along (Renko measured NO edge; this measured
    a negative one).  A quarter-weight demotion was tried first and was not enough: a
    weak weight still counts toward FULL_CONFLUENCE, so a negative detector could still
    help push a name onto the shortlist.  It stays registered, visible and runnable in
    the Scanner Hub, and backtestable -- the measurement rules out a vote, not the view.

    (The complementary *anchored*-VWAP-from-catalyst read — earnings/breakout/IPO
    anchors — is served by ``_anchored_vwap`` and belongs with the chart's
    click-to-anchor, the B-4/B-12 item.)  Emits ``time_stop`` — a pullback-to-mean
    entry that hasn't worked in ~15 bars is a failed thesis, not an open trade.
    """
    n = len(df)
    if n < vwap_n + 15:
        return None

    close = df["close"].astype(float)
    low   = df["low"].astype(float)
    vol   = df["volume"].astype(float)

    vwap = _rolling_vwap(df, vwap_n)
    v_now  = float(vwap.iloc[-1])
    v_prev = float(vwap.iloc[-2])
    if not np.isfinite(v_now) or v_now <= 0 or not np.isfinite(v_prev):
        return None

    c_now, c_prev = float(close.iloc[-1]), float(close.iloc[-2])
    ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])

    # Gate 1 — with-trend
    if c_now <= ema50:
        return None
    # Gate 2 — VWAP rising over the last 10 bars
    ref = float(vwap.iloc[-11]) if np.isfinite(vwap.iloc[-11]) else v_prev
    if not (v_now > ref):
        return None
    # Gate 3 — not extended above the mean
    dist = c_now / v_now - 1.0
    if dist > extend_cap:
        return None

    # Event (a) — reclaim cross from below
    reclaim = (c_prev < v_prev) and (c_now > v_now)

    # Event (b) — recent pullback tagged VWAP and price is holding above / bouncing
    tagged = False
    for k in range(1, 4):
        lv = float(vwap.iloc[-k])
        if np.isfinite(lv) and lv > 0 and (float(low.iloc[-k]) <= lv * (1.0 + touch_tol)):
            tagged = True
            break
    pullback_hold = tagged and (c_now > v_now) and (c_now > c_prev)

    if not (reclaim or pullback_hold):
        return None

    vol_now = float(vol.iloc[-1])
    vol_avg = float(vol.rolling(20).mean().iloc[-1]) if n >= 20 else float(vol.mean())
    vol_x = vol_now / vol_avg if vol_avg > 0 else 0.0
    # Reclaim needs conviction volume; a quiet pullback-hold does not.
    if reclaim and vol_x < 1.0:
        return None

    event = "reclaim" if reclaim else "pullback-hold"
    slope = (v_now / ref - 1.0) * 100.0
    proximity = max(0.0, (extend_cap - abs(dist))) / extend_cap    # 0..1
    score = int(min(100, 55 + proximity * 20 + min(vol_x, 2.0) * 7 + min(slope, 5.0)))

    return {
        "pattern_type": "VWAP Reclaim/Support",
        "tags": ["VWAP", event, f"VWAP{vwap_n}"],
        "reasons": [
            f"{event} at the rising {vwap_n}-day VWAP (VWAP {v_now:.2f}, close "
            f"{c_now:.2f}, {dist*100:+.1f}% vs mean); vol {vol_x:.1f}×20d; "
            f"VWAP slope +{slope:.1f}%/10d"
        ],
        "score_base": score,
        "score": score,
        "vwap": round(v_now, 2),
        "dist_pct": round(dist * 100, 2),
        "vol_x20d": round(vol_x, 2),
        "time_stop": 15,
    }


def scan_vwap_mean_reversion(df: pd.DataFrame,
                             vwap_n: int = 20,
                             band_k: float = 2.0,
                             dev_vol_mult: float = 1.5,
                             conf_vol_mult: float = 1.2,
                             max_excursion: int = 15,
                             min_target_pct: float = 0.5) -> dict | None:
    """Two-sided VWAP mean reversion with volume in BOTH roles (B-40m).

    The "VWAP Mean Reversion + Volume" rule: price deviates far from VWAP on
    EXTREME volume, rejects, and reverts to VWAP on RISING volume.  The mirror of
    ``scan_vwap_reclaim``'s question -- that one asks whether a trend is resuming
    at its mean, this one asks whether a stretch away from the mean is snapping
    back.

    -- What makes it a different scanner, not a re-skin ------------------------
    ``scan_vwap_reclaim`` (B-40) is long-only, with-trend, and uses volume as a
    participation FLOOR.  Here volume is the signal twice over:

      * ``dev_vol_mult``  -- the deviation extreme must come on heavy volume, or
        the stretch is drift rather than capitulation and there is nothing to
        snap back;
      * ``conf_vol_mult`` -- the reversal bar must ALSO be heavy, because a
        reversion on falling volume is the failure case the rule exists to skip.

    Neither existing VWAP tool can express that pair, which is the whole reason
    this one was written.

    -- Daily bars measure a DIFFERENT claim, and that is deliberate ------------
    Natively this is intraday: session VWAP needs many bars inside one session.
    On daily bars a session VWAP collapses to the bar's own (H+L+C)/3 (measured
    24 of 24 on daily RELIANCE), so this uses the ROLLING ``vwap_n``-day VWAP --
    the same mean ``scan_vwap_reclaim`` settled on after an anchored VWAP proved
    to sit too far below price to ever be touched.  ``tools/vwap_mean_reversion.js``
    runs the identical rule on the chart and reports ``source: 'session'`` intraday
    vs ``'rolling'`` on daily+, so the two never get conflated.

    -- Gates ------------------------------------------------------------------
      1. An excursion is open: some bar within the last ``max_excursion`` closed
         at least ``band_k`` dispersions beyond VWAP.
      2. The LAST bar closes back inside the band -- the reversal candle.
      3. That candle agrees with the direction (up-close and above yesterday for
         a long; the mirror for the bearish read).
      4. Volume at the excursion extreme >= ``dev_vol_mult`` x its trailing 20d.
      5. Volume on the reversal bar >= ``conf_vol_mult`` x its trailing 20d.
      6. The trip back to VWAP is worth >= ``min_target_pct``.

    Dispersion, not stdev of close: the band has to answer "how far from VWAP is
    far for this symbol lately".  Stdev of close would measure the TREND, and the
    bands would go untouched in exactly the trending conditions where a reversion
    trade is most dangerous.

    -- Direction --------------------------------------------------------------
    The bearish side fires as a *stretched-above-VWAP* read.  It is tagged and
    scored, but described as a name to trim or avoid rather than a short to put
    on -- the same stance ``scan_distribution`` takes, and the same one this desk
    takes generally on cash equity.

    MEASURED 2026-09-06 (B-40m) -- NULL, AND NEGATIVE AFTER COSTS.  50 symbols,
    275 signals: forward edge +0.19% at both 5d and 10d (p 0.51 / 0.57), which is
    where a 10-bar reversion trade actually lives.  The R-multiple sim traded as
    written -- enter on confirmation, target VWAP, stop beyond the rejected
    extreme -- returns **+0.04R gross and -0.19R at Indian delivery costs**, on
    116 long-side plans hitting target 50 times against stop 53.  A coin flip at
    1:1.

    The +1.54% at 60d (p=0.053) is recorded as a TRAP, not a result: it sits far
    outside the holding period, so it measures drift rather than this rule.

    Kept as a chart/coverage read, not a trigger.  This is the third VWAP-derived
    rule to measure null here (EVWMA/VWAP MACD crossovers outright; only
    ``scan_vwap_reclaim`` is still open), which is consistent enough to state:
    on NSE daily bars VWAP is context, not a trigger.  Testing the playbook's
    ACTUAL intraday claim needs a session-VWAP store this repo does not have --
    a data gap, not a parameter to tune.
    """  # claims-lint: checked B-40m
    need = vwap_n + 20 + 2
    if len(df) < need:
        return None

    close = df["close"].astype(float)
    high  = df["high"].astype(float)
    low   = df["low"].astype(float)
    vol   = df["volume"].astype(float)

    vwap = _rolling_vwap(df, vwap_n)
    if not np.isfinite(float(vwap.iloc[-1])):
        return None

    # Dispersion of close around VWAP over the same window.
    dev = close - vwap
    sigma = dev.rolling(vwap_n).apply(lambda w: float(np.sqrt(np.mean(w ** 2))), raw=True)
    s_now = float(sigma.iloc[-1])
    if not np.isfinite(s_now) or s_now <= 0:
        return None

    # Trailing 20-bar volume average EXCLUDING the bar being judged -- comparing a
    # bar's volume to an average containing it dilutes the very spike being tested.
    vol_avg = vol.shift(1).rolling(20).mean()

    z = dev / sigma
    z_now = float(z.iloc[-1])
    if not np.isfinite(z_now) or abs(z_now) >= band_k:
        return None                      # still outside the band: not back yet

    # Walk back for the excursion this bar just closed.
    ext_i = None
    ext_z = 0.0
    ext_price = None
    side = 0
    for k in range(2, min(max_excursion, len(df) - 1) + 2):
        zk = float(z.iloc[-k])
        if not np.isfinite(zk):
            break
        if abs(zk) < band_k:
            break                        # excursion started after this bar
        d = 1 if zk < 0 else -1
        if side == 0:
            side = d
        elif d != side:
            break                        # flipped sides mid-excursion
        if abs(zk) > abs(ext_z):
            ext_z, ext_i = zk, -k
            ext_price = float(low.iloc[-k]) if d == 1 else float(high.iloc[-k])

    if ext_i is None or side == 0:
        return None

    c_now, c_prev = float(close.iloc[-1]), float(close.iloc[-2])
    o_now = float(df["open"].astype(float).iloc[-1])
    agrees = ((c_now > o_now and c_now > c_prev) if side == 1
              else (c_now < o_now and c_now < c_prev))
    if not agrees:
        return None

    va_ext = float(vol_avg.iloc[ext_i])
    va_now = float(vol_avg.iloc[-1])
    if not (np.isfinite(va_ext) and va_ext > 0 and np.isfinite(va_now) and va_now > 0):
        return None
    dev_x  = float(vol.iloc[ext_i]) / va_ext
    conf_x = float(vol.iloc[-1]) / va_now
    if dev_x < dev_vol_mult or conf_x < conf_vol_mult:
        return None

    v_now = float(vwap.iloc[-1])
    target_pct = (v_now - c_now) / c_now * 100.0 if c_now > 0 else 0.0
    if abs(target_pct) < min_target_pct:
        return None

    bars_out = -ext_i - 1
    bull = side == 1
    label = "below VWAP (long)" if bull else "above VWAP (trim)"
    score = int(min(100, 55
                    + min(abs(ext_z) - band_k, 2.0) * 8      # how stretched it got
                    + min(dev_x, 3.0) * 5                    # capitulation volume
                    + min(conf_x, 2.5) * 4))                 # confirmation volume

    return {
        "pattern_type": "VWAP Mean Reversion",
        "tags": ["VWAP", "mean-reversion", f"VWAP{vwap_n}",
                 "long" if bull else "bearish", f"{abs(ext_z):.1f}sigma"],
        "reasons": [
            f"Stretched {abs(ext_z):.1f}σ {label} then closed back inside the "
            f"±{band_k:.1f}σ band; extreme bar {bars_out}d ago on {dev_x:.1f}×20d "
            f"volume, reversal bar on {conf_x:.1f}×20d. VWAP{vwap_n} {v_now:.2f} "
            f"vs close {c_now:.2f} — {target_pct:+.1f}% back to the mean.",
            ("⚠ Measured NULL (B-40m) — +0.04R gross, −0.19R after costs"
             if bull else
             "Bearish side is a trim/avoid read, not a short to put on."),
        ],
        "score_base": score,
        "score": score,
        "direction": "long" if bull else "bearish",
        # entry/stop/target as a complete plan, so backtest_scanner runs its
        # R-multiple simulation instead of forward returns alone. For a rule
        # whose whole thesis is "the trip back to the mean", R is the honest
        # measure and a raw 60d forward return is not.
        "entry": round(c_now, 2),
        "vwap": round(v_now, 2),
        "z": round(z_now, 2),
        "dev_z": round(ext_z, 2),
        "dev_vol_x": round(dev_x, 2),
        "conf_vol_x": round(conf_x, 2),
        "target": round(v_now, 2),
        "target_pct": round(target_pct, 2),
        "stop": round(ext_price, 2) if ext_price is not None else None,
        "time_stop": 10,
    }


def scan_rsi_band_momentum(df: pd.DataFrame,
                            rsi_lo: float = 50.0,
                            rsi_hi: float = 68.0) -> dict | None:
    """RSI mid-band momentum — Patel Yash Ashokbhai StockEdge scanner.

    Targets momentum stocks with strong price structure that are NOT yet
    overbought — within 10% of their 52-week high but RSI still in the
    [50, 68] band.  The upper cap is the key new mechanic: stocks above RSI 68
    are deliberately excluded (they are already extended).  This creates an
    "approaching new high" setup zone rather than a "chasing new high" one.

    Gates:
      1. Close within 10% of 52-week high — price strength already there
      2. RSI(14) in [rsi_lo, rsi_hi] (default 50–68) — momentum, not overextended
      3. SMA20 > SMA50 — short-term trend aligned above medium-term (golden-cross zone)
      4. Close > SMA50 — confirming trend direction
      5. RSI rising vs prior day — momentum confirming, not stalling
    """
    if len(df) < 60:
        return None
    close = df["close"].astype(float)
    last  = float(close.iloc[-1])

    # Gate 1 — within 10% of 52-week high
    hi_52 = float(df["high"].tail(252).max())
    if hi_52 <= 0:
        return None
    below_high_pct = (hi_52 - last) / hi_52 * 100
    if below_high_pct > 10.0:
        return None

    # Gate 2 — RSI in mid-band
    rsi = _rsi_series(close, 14)
    rsi_now  = float(rsi.iloc[-1])
    rsi_prev = float(rsi.iloc[-2])
    if np.isnan(rsi_now):
        return None
    if not (rsi_lo <= rsi_now <= rsi_hi):
        return None

    # Gate 3 & 4 — MA alignment
    sma20 = _sma(close, 20)
    sma50 = _sma(close, 50)
    if np.isnan(sma20) or np.isnan(sma50):
        return None
    if not (last > sma50 > 0 and sma20 > sma50):
        return None

    # Gate 5 — RSI rising
    if not np.isnan(rsi_prev) and rsi_now <= rsi_prev:
        return None

    rsi_headroom = rsi_hi - rsi_now    # room left before the overbought ceiling
    reasons = [
        f"RSI {rsi_now:.0f} in the mid-band [{rsi_lo:.0f}–{rsi_hi:.0f}] — "
        f"momentum active, {rsi_headroom:.0f} pts of headroom before the "
        f"overbought ceiling",
        f"Within {below_high_pct:.1f}% of 52-week high ({hi_52:.0f}) — "
        "approaching highs, not chasing an extended move",
        f"SMA20 ({sma20:.0f}) > SMA50 ({sma50:.0f}) — golden-cross zone; "
        f"price ({last:.0f}) above SMA50",
        "RSI rising vs prior session — momentum confirming",
    ]
    # Score: combination of RSI headroom (more room = better entry) and proximity
    # to 52W high (closer = stronger but still within gate)
    score = round(
        (rsi_headroom / (rsi_hi - rsi_lo)) * 40    # RSI headroom (0-40)
        + (10.0 - below_high_pct) / 10.0 * 30      # near-high quality (0-30)
        + (rsi_now - rsi_lo) / (rsi_hi - rsi_lo) * 30,  # RSI above midpoint (0-30)
        1,
    )
    score = float(max(0.0, min(score, 100.0)))
    return {
        "pattern_type": "RSI Mid-Band Momentum",
        "tags": [f"RSI {rsi_now:.0f}", f"{below_high_pct:.1f}% from 52W high",
                 f"SMA20>{sma50:.0f}"],
        "reasons": reasons,
        "score": score,
        "rsi_now": round(rsi_now, 1),
        "rsi_headroom": round(rsi_headroom, 1),
        "below_52w_high_pct": round(below_high_pct, 1),
    }


def scan_triple_rs_52w(df: pd.DataFrame) -> dict | None:
    """Triple-RS + 52-week high crossover — Ashok Taneja StockEdge scanner.

    Requires ALL three relative-strength measures to be positive at once, then
    fires only when price simultaneously crosses/hugs the 52-week high with
    dual-timeframe RSI momentum confirming.  The triple-RS gate is the key new
    mechanic: a stock must outperform in absolute terms, over 55 days, AND have
    a rising weekly RSI — one dimension of RS alone is insufficient.

    Price-only equivalents of StockEdge's RSMkt55Days / ARS / weekly-RSI gate:
      1. 55-day absolute return > 0 (ARS proxy — stock is up over 55 trading days)
      2. 55-day excess return > 0 vs benchmark if supplied (RSMkt55Days proxy)
      3. Daily RSI(14) > prior-day RSI (RSI rising intraday-to-day)
      4. Weekly RSI (sampled every 5 bars) rising vs prior week
      5. Close crossed above 52-week high in last 5 sessions (52W cross trigger)
      6. RSI < 80 — anti-chase gate (Taneja uses MCap > 10000 Cr as a universe
         filter; this gate keeps us out of exhausted, already-extended breakouts)
    """
    if len(df) < 260:
        return None
    close = df["close"].astype(float)
    last  = float(close.iloc[-1])

    # Gate 1 — 55-day absolute return positive (ARS proxy)
    if len(df) < 56:
        return None
    ret_55d = last / float(close.iloc[-56]) - 1.0 if float(close.iloc[-56]) > 0 else -1.0
    if ret_55d <= 0:
        return None

    # Gate 2 — 55-day excess return positive (RSMkt55Days proxy, benchmark-optional)
    bmk_wret = getattr(_tls, "benchmark_wret", None)
    if bmk_wret is not None:
        # Convert benchmark's IBD-weighted return to an approximate 55d return
        # (the weighted return is already excess when _rs_raw uses it, but for a
        # pure 55-day comparison we use the raw stock 55d minus what the benchmark
        # would have done in the same window — a simple approximation)
        bench_55d_approx = bmk_wret / 100.0  # wret is in %, normalise
        if ret_55d <= bench_55d_approx:
            return None

    # Gate 3 — daily RSI rising
    rsi = _rsi_series(close, 14)
    rsi_now  = float(rsi.iloc[-1])
    rsi_prev = float(rsi.iloc[-2])
    if np.isnan(rsi_now) or np.isnan(rsi_prev):
        return None
    if rsi_now <= rsi_prev:
        return None
    if rsi_now >= 80.0:   # anti-chase
        return None

    # Gate 4 — weekly RSI rising (sample close every 5 bars as a weekly proxy)
    weekly_close = close.iloc[::5]
    if len(weekly_close) < 16:
        return None
    wrsi = _rsi_series(weekly_close, 14)
    wrsi_now  = float(wrsi.iloc[-1])
    wrsi_prev = float(wrsi.iloc[-2])
    if np.isnan(wrsi_now) or np.isnan(wrsi_prev):
        return None
    if wrsi_now <= wrsi_prev:
        return None

    # Gate 5 — 52-week high crossover within the last 5 sessions
    hi_52 = float(df["high"].iloc[-252:-1].max()) if len(df) >= 253 else float(
        df["high"].iloc[:-1].max())
    if hi_52 <= 0:
        return None
    # Did any session in the last 5 close above the prior 52W high?
    recent_closes = close.iloc[-5:]
    cross_occurred = bool((recent_closes > hi_52).any())
    pct_from_52w = (last - hi_52) / hi_52 * 100
    if not cross_occurred and pct_from_52w < -1.0:
        return None   # neither crossed nor hugging the high

    reasons = [
        f"55-day return {ret_55d * 100:.1f}% — absolute RS positive (ARS proxy: stock "
        "is stronger than it was 55 days ago)",
        f"Daily RSI {rsi_now:.0f} rising from {rsi_prev:.0f}; "
        f"Weekly RSI {wrsi_now:.0f} rising from {wrsi_prev:.0f} — "
        "dual-timeframe momentum aligned",
        ("52-week high crossover in the last 5 sessions"
         if cross_occurred else
         f"Hugging 52-week high ({hi_52:.0f}), {pct_from_52w:+.1f}%)"),
        f"RSI {rsi_now:.0f} < 80 — momentum active, not exhausted",
    ]
    if bmk_wret is not None:
        reasons.insert(1, "Benchmark-relative 55-day return positive (RSMkt55Days proxy)")

    # Score: weight the triple-RS quality + proximity to the 52W high
    rs_strength = min(ret_55d * 100, 30.0) / 30.0 * 40   # 55d return up to 30% → 40 pts
    di_score    = min(max(rsi_now - 50.0, 0.0), 18.0) / 18.0 * 30  # RSI 50-68 → up to 30 pts
    hi_score    = max(0.0, 5.0 - abs(pct_from_52w)) / 5.0 * 30     # within 5% of high → 30 pts
    score = round(float(max(0.0, min(rs_strength + di_score + hi_score, 100.0))), 1)

    return {
        "pattern_type": "Triple-RS 52W Cross",
        "tags": [f"ARS {ret_55d * 100:.0f}%", f"RSI {rsi_now:.0f}↑",
                 f"wRSI {wrsi_now:.0f}↑",
                 "52W cross" if cross_occurred else f"{pct_from_52w:+.1f}% from 52W"],
        "reasons": reasons,
        "score": score,
        "rs_raw": round(_rs_raw(df), 3),
        "ret_55d_pct": round(ret_55d * 100, 1),
        "rsi_now": round(rsi_now, 1),
        "wrsi_now": round(wrsi_now, 1),
        "pct_from_52w_high": round(pct_from_52w, 2),
        "cross_occurred": cross_occurred,
    }


def scan_hm_buy(df: pd.DataFrame) -> dict | None:
    """HM (Hilega Milega) fresh BUY on the last closed daily bar.

    Python port of the chart dashboard's HM indicator (tools/hm_indicator.js,
    window.HM). Reads three views of a short RSI:
      - RSI(9)                — "strength" (OB/OS collapse to the 50 midline)
      - EMA(3) of RSI         — momentum (rising = strength turning up)
      - VWMA(21) of RSI       — volume-adjusted strength (a true volume weighting,
                                the fix over the source's plain-WMA "volume" line)

    The actionable BUY is the *early setup* — RSI(9) crosses above 50 with
    EMA(3)-of-RSI rising while the slower VWMA(21)-of-RSI is still below 50
    (momentum turning up, not yet exhausted) — which is exactly where the method
    says to enter. If the VWMA(RSI) later crosses above 50 within a 10-bar prime
    window, the signal is marked *confirmed* (a strength upgrade). Closed-bar
    only; fires when the setup (or its confirm) landed within the last 5 bars
    (~a trading week), so the pick is still fresh but the window is wide enough to
    catch a signal from earlier in the week. Emits a swing-low-stop / 2R plan. See
    concepts/HM-(Hilega-Milega)-Indicator. Accuracy is UNMEASURED.
    """
    if df is None or len(df) < 40:
        return None
    df = _clean_ohlc(df)
    if len(df) < 40:
        return None
    close = df["close"]
    vol = df["volume"] if "volume" in df.columns else pd.Series(0.0, index=df.index)
    mid = 50.0
    prime_window = 10
    recency = 5                      # signal within the last 5 closed bars (~a trading week)

    rsi = _rsi_series(close, 9)
    ema = _ema_series(rsi, 3)
    # VWMA of RSI over 21 bars (volume-weighted; plain-mean fallback on no volume).
    wv = (rsi * vol).rolling(21).sum()
    wsum = vol.rolling(21).sum()
    vwma = (wv / wsum.replace(0.0, np.nan)).fillna(rsi.rolling(21).mean())

    r = rsi.to_numpy(); e = ema.to_numpy(); v = vwma.to_numpy()
    n = len(df)
    prime = 0
    last_early = None
    last_confirm = None
    for i in range(1, n):
        vals = (r[i - 1], r[i], e[i - 1], e[i], v[i - 1], v[i])
        if any(np.isnan(x) for x in vals):
            continue
        rsi_cross_up = r[i - 1] <= mid and r[i] > mid
        ema_rising = e[i] > e[i - 1]
        vwma_cross_up = v[i - 1] < mid and v[i] >= mid
        if prime > 0:
            prime -= 1
        if rsi_cross_up and ema_rising and v[i] < mid:     # early setup = the entry
            last_early = i
            prime = prime_window
        if prime > 0 and vwma_cross_up:                    # VWMA leaves band = confirmed
            last_confirm = i
            prime = 0

    # Fire on whichever is fresh, preferring the stronger confirmed reading.
    signal = None
    if last_confirm is not None and (n - 1 - last_confirm) <= recency:
        signal, sig_idx = "confirmed", last_confirm
    elif last_early is not None and (n - 1 - last_early) <= recency:
        signal, sig_idx = "setup", last_early
    if signal is None:
        return None
    bars_since = n - 1 - sig_idx

    entry = float(close.iloc[-1])
    swing_low = float(df["low"].iloc[-5:].min())           # stop below recent swing low
    stop = round(swing_low * 0.995, 2)
    risk = entry - stop
    if risk <= 0:
        return None
    target = round(entry + 2.0 * risk, 2)

    rsi_now = float(rsi.iloc[-1])
    vwma_now = float(vwma.iloc[-1])
    vol20 = float(vol.tail(20).mean())
    vol_x = float(vol.iloc[-1]) / vol20 if vol20 > 0 else 0.0

    # Score (0-100): a confirmed reading + freshness + RSI strength + VWMA lift + volume.
    confirmed = signal == "confirmed"
    fresh = max(0.15, 1.0 - bars_since / (recency + 1.0))   # decays across the 5-bar window
    strength = min(max((rsi_now - mid) / 20.0, 0.0), 1.0)   # 50→0, 70→1
    vwma_lift = min(max((vwma_now - mid) / 15.0, 0.0), 1.0)
    vol_ok = vol_x >= 1.5
    base = (10.0 + (20.0 if confirmed else 0.0) + 25.0 * fresh
            + 20.0 * strength + 10.0 * vwma_lift + (15.0 if vol_ok else 0.0))

    kind = "confirmed" if confirmed else "setup"
    reasons = [
        (f"HM BUY {kind} {bars_since}b ago — "
         + ("VWMA(RSI) crossed above 50 (strength confirmed) after "
            "RSI reclaimed 50 with EMA(RSI) rising" if confirmed
            else "RSI(9) crossed above the 50 pivot with EMA(RSI) rising while "
                 "VWMA(RSI) is still below 50 (early, not yet exhausted)")),
        f"RSI(9) {rsi_now:.0f}; VWMA(RSI) {vwma_now:.0f} "
        + ("(above the 50 band)" if vwma_now >= mid else "(still inside the sub-50 band)"),
        (f"Volume {vol_x:.1f}× the 20-day average"
         if vol_ok else f"⚠ Volume only {vol_x:.1f}× avg — weaker signal"),
        f"Trade plan — entry {entry:.0f} · stop {stop:.0f} (swing low) · "
        f"target {target:.0f} (2R, R:R {(target - entry) / risk:.1f})",
        "HM is a momentum-reversal read; accuracy is unmeasured — size per Risk Per Trade.",
    ]
    return {
        "pattern_type": f"HM BUY · {kind} (Hilega Milega)",
        "tags": ["HM Buy", kind, "RSI-9", f"{bars_since}b fresh"]
                + (["Vol 1.5x+"] if vol_ok else []),
        "reasons": reasons,
        "score_base": round(min(100.0, base), 1),
        "score": round(min(100.0, base), 1),   # provisional — run_scanner blends in RS
        "rs_raw": _rs_raw(df),
        "entry": round(entry, 2),
        "stop": stop,
        "target": target,
        "vol_x50d": round(vol_x, 2),
        "rsi_now": round(rsi_now, 1),
        # HM reversal trades should resolve promptly; give it a fortnight.
        "time_stop": 15,
    }


# ── Renko structure (Python port of tools/renko.js) ───────────────────────────
#
# Ported, not re-invented: `renko.js` is the shipped chart engine and was measured
# in B-43, so the scanner must fire on exactly the bars the chart draws a flip on.
# `test_renko_parity.py` asserts bar-for-bar agreement between the two.
#
# NOTE — this deliberately does NOT reuse `_atr_series`. That helper is
# `ewm(alpha=1/n, adjust=False)`, which seeds from the first TR; `renko.js` (and
# `chart_dashboard.atrSeries`) seed from the SMA of the first `n` TRs and then
# recurse. The gap decays but never reaches zero, and brick size feeds a RECURSIVE
# grid — a hair's difference at an epoch boundary flips a brick and the two series
# diverge permanently afterwards. Parity has to be exact at the source.

RENKO_ATR_PERIOD = 5      # the source rule's lookback ("ATR of the last five sessions")
RENKO_EPOCH_BARS = 20     # re-derive the brick ~monthly, from PRIOR bars only
RENKO_WARMUP = 30
RENKO_REVERSAL = 2        # bricks needed to turn — the classic Renko definition


def _renko_atr(df: pd.DataFrame, period: int = RENKO_ATR_PERIOD) -> list[float]:
    """Wilder ATR seeded with the SMA of the first `period` true ranges (matches renko.js)."""
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    close = df["close"].to_numpy(float)
    out = [float("nan")] * len(close)
    trs: list[float] = []
    atr = None
    prev_close = None
    for i in range(len(close)):
        tr = (high[i] - low[i]) if prev_close is None else max(
            high[i] - low[i], abs(high[i] - prev_close), abs(low[i] - prev_close))
        trs.append(tr)
        prev_close = close[i]
        if i == period - 1:
            atr = sum(trs[:period]) / period
            out[i] = atr
        elif i > period - 1:
            atr = (atr * (period - 1) + tr) / period
            out[i] = atr
    return out


def _renko_flips(df: pd.DataFrame,
                 atr_period: int = RENKO_ATR_PERIOD,
                 epoch_bars: int = RENKO_EPOCH_BARS,
                 warmup: int = RENKO_WARMUP,
                 reversal: int = RENKO_REVERSAL) -> dict:
    """Close-based Renko with causal ATR-epoch brick sizing.

    Returns ``{"flips": [...], "state": {...} | None}`` where each flip is
    ``{"index", "dir", "price", "bricks_in_prior"}`` and ``index`` is the bar whose
    CLOSE completed the turn — i.e. a bar you could have acted on the next open.
    """
    empty = {"flips": [], "state": None}
    if df is None or len(df) < warmup + atr_period + 5:
        return empty
    close = df["close"].to_numpy(float)
    atr = _renko_atr(df, atr_period)

    flips: list[dict] = []
    brick = None
    last_close = None
    direction = 0
    bricks_in_dir = 0

    for i in range(len(close)):
        # Epoch boundary: re-derive the brick from ATR at the PREVIOUS bar, so the
        # bar about to complete a brick never contributes to that brick's size.
        if i >= warmup and (last_close is None or (i - warmup) % epoch_bars == 0):
            a = atr[i - 1] if i > 0 else float("nan")
            if a == a and a > 0:                      # a == a filters NaN
                brick = a
                if last_close is None:
                    last_close = close[i]
                    direction = 0
        if last_close is None or not brick or brick <= 0:
            continue

        c = close[i]
        for _ in range(1000):                          # a gap can complete many bricks
            moved = False
            if direction >= 0 and c >= last_close + brick:
                last_close += brick
                if direction != 1:
                    direction, bricks_in_dir = 1, 0
                bricks_in_dir += 1
                moved = True
            elif direction <= 0 and c <= last_close - brick:
                last_close -= brick
                if direction != -1:
                    direction, bricks_in_dir = -1, 0
                bricks_in_dir += 1
                moved = True
            elif direction == 1 and c <= last_close - reversal * brick:
                last_close -= reversal * brick
                flips.append({"index": i, "dir": -1, "price": float(c),
                              "bricks_in_prior": bricks_in_dir})
                direction, bricks_in_dir = -1, 1
                moved = True
            elif direction == -1 and c >= last_close + reversal * brick:
                last_close += reversal * brick
                flips.append({"index": i, "dir": 1, "price": float(c),
                              "bricks_in_prior": bricks_in_dir})
                direction, bricks_in_dir = 1, 1
                moved = True
            if not moved:
                break

    state = None if last_close is None else {
        "dir": direction, "bricks": bricks_in_dir,
        "brick": float(brick) if brick else None, "last_close": float(last_close),
    }
    return {"flips": flips, "state": state}


def scan_renko_flip(df: pd.DataFrame, max_bars_ago: int = 2) -> dict | None:
    """Renko brick FLIP — a structure-change SCREEN, explicitly not a trade trigger.

    Fires when the Renko grid changed direction within the last `max_bars_ago` bars,
    in EITHER direction. Renko samples by price rather than by time, so a flip says
    "price has now travelled far enough, against the prior run, to reverse the grid"
    — a statement about structure, not about what happens next.

    **It carries no direction implication and no trade plan, by measurement.** B-43
    scored this exact engine's flips over 23 names and ~19 years: the up-flip's edge
    was NEGATIVE at every horizon (−0.06 / −0.08 / −0.04 / −0.77% at 5/10/20/60d) and
    stop-and-reverse beat buy-and-hold 0 times in 23. What Renko *did* deliver is
    noise reduction — it fires ~40% less often than the EVWMA cross on the same names.
    Fewer decisions of the same quality is an ergonomic benefit, not an edge, and this
    scanner is registered to exploit the former only.

    Consequences of that, enforced structurally rather than by wording:
      * no ``entry`` / ``stop`` / ``target`` keys — the thing that would make it a plan;
      * listed in ``opportunity_hub.PIPELINE_EXCLUDED`` so it can never become a
        confluence vote;
      * a DOWN flip is reported as plainly as an UP flip and is not a risk flag —
        it is neutral information, not a bearish call.

    ``max_bars_ago`` is the freshness window, and it is what makes this selective.
    Measured over 2,496 (symbol, as-of) cells on a 110-name NIFTY-500 sample
    (`scanner_overlap.py`):

        max_bars_ago=0   4.3% of cells    flipped today
        max_bars_ago=1   8.9%
        max_bars_ago=2  13.7%             <- default
        max_bars_ago=3  17.5%
        max_bars_ago=5  24.3%             a firehose, not a screen

    Default 2 catches a Friday flip when you scan on Monday without flooding the list.
    Widen it only if you are deliberately trading a slower book.

    In the same measurement it flagged **146 cells no other scanner flagged** — the
    largest unique contribution of any bullish scanner in the registry. That is what a
    price-sampled detector buys you when everything else is time-sampled: a genuinely
    different view. It is NOT a claim that the view is profitable — see above.

    Use it to answer "which names just changed structure?", then bring your own
    tested trigger.
    """
    if df is None or len(df) < RENKO_WARMUP + RENKO_ATR_PERIOD + 10:
        return None
    r = _renko_flips(df)
    flips, state = r["flips"], r["state"]
    if not flips or not state:
        return None

    last = flips[-1]
    n = len(df)
    bars_ago = (n - 1) - last["index"]
    if bars_ago > max_bars_ago:
        return None

    close = float(df["close"].iloc[-1])
    brick = state["brick"] or 0.0
    brick_pct = (brick / close * 100.0) if close > 0 else 0.0
    up = last["dir"] == 1
    word = "UP" if up else "DOWN"
    when = "today" if bars_ago == 0 else f"{bars_ago} bar{'s' if bars_ago > 1 else ''} ago"

    reasons = [
        f"Renko grid flipped {word} {when} at {last['price']:.2f} — the {RENKO_REVERSAL}-brick "
        f"reversal completed on that close",
        f"Ended a run of {last['bricks_in_prior']} brick(s) in the other direction",
        f"Brick size {brick:.2f} ({brick_pct:.2f}% of price), derived from ATR("
        f"{RENKO_ATR_PERIOD}) and re-set every {RENKO_EPOCH_BARS} bars — not tuned",
        "SCREEN, not a trigger: the flip was measured at NO forward edge (B-43), so this "
        "is a 'what changed' filter. No entry/stop/target, and a DOWN flip is not a sell.",
    ]
    return {
        "pattern_type": f"Renko flip {word} (structure change)",
        "tags": [f"Renko {word}", f"{when}", f"brick {brick_pct:.2f}%",
                 "Screen, not trigger"],
        "reasons": reasons,
        # Freshness only — deliberately NOT a conviction score. A flip 0 bars ago is
        # more current than one 5 bars ago; neither is more likely to be profitable.
        "score": round(max(10.0, 60.0 - 8.0 * bars_ago), 1),
        "renko_dir": word,
        "renko_bars_ago": bars_ago,
        "renko_brick": round(brick, 4),
        "rs_raw": _rs_raw(df),
    }



#: The correction cap that defines "shallow", in percent. Chosen in B-57 on
#: CARDINALITY and prior coverage -- it is the tightest rung with workable n and
#: the only one B-43r's brick-run secondary does not already cover -- with no
#: forward-return information in the choice. It is NOT a tuned threshold, and the
#: study that used it measured no edge, so nothing here is calibrated to pay.
SHALLOW_CORRECTION_PCT = 10.0


def _correction_before_flip(df: pd.DataFrame, flips: list[dict],
                            k: int) -> dict | None:
    """How far price fell into the down-leg that `flips[k]` (an UP flip) ended.

    Same definition `renko_quality_cardinality.flip_events_raw` counted with and
    `renko_shallow_quality_study` scored with -- peak is the highest high between
    the PRIOR up-flip and the down-flip, trough the lowest low from that down-flip
    to this one. Re-deriving it here with a different reading would mean the
    screen and the measurement that judged it were about different things.
    """
    if k <= 0 or flips[k]["dir"] != 1:
        return None
    prev_dn = next((flips[j] for j in range(k - 1, -1, -1)
                    if flips[j]["dir"] == -1), None)
    if prev_dn is None:
        return None
    prev_up = next((flips[j] for j in range(k - 1, -1, -1)
                    if flips[j]["dir"] == 1
                    and flips[j]["index"] < prev_dn["index"]), None)
    i_dn, i_up = prev_dn["index"], flips[k]["index"]
    if i_up <= i_dn:
        return None
    high = df["high"].astype(float).to_numpy()
    low = df["low"].astype(float).to_numpy()
    peak_from = prev_up["index"] if prev_up is not None else max(0, i_dn - 120)
    peak = float(high[peak_from:i_dn + 1].max())
    trough = float(low[i_dn:i_up + 1].min())
    if peak <= 0 or trough <= 0:
        return None
    return {
        "depth_pct": round((peak - trough) / peak * 100.0, 2),
        "peak": peak, "trough": trough,
        "days_down": int(i_up - i_dn),
        "bricks_in_prior": int(flips[k].get("bricks_in_prior", 0)),
    }


def scan_shallow_flip(df: pd.DataFrame, max_bars_ago: int = 2,
                      max_correction: float = SHALLOW_CORRECTION_PCT) -> dict | None:
    """Renko UP-flip out of a SHALLOW correction — an attention list, measured at zero.

    Fires when the grid flipped UP within `max_bars_ago` bars AND the down-leg it
    ended took price no more than `max_correction`% below its prior peak. The idea
    is the owner's: a buy flip whose preceding sell flip led into a bounded, not
    catastrophic, fall.

    **This carries no edge, and the number is on the record.** B-57 scored exactly
    this condition on 460 names against a STATE-MATCHED baseline -- the same names,
    also within 10% of their trailing high, minus the flip -- and measured
    **-0.25% at 20d, p_rot = 0.714, n = 207**. It fails its pre-registered bar
    (`edge > 0 AND p_rot < 0.05`).

    What makes it worth registering anyway is the SHAPE of that null, and it is a
    genuine finding rather than a consolation. B-43r measured the bare flip at
    **-1.01%, p_rot = 0.000** and explained the sign: an up-flip is punished
    because it re-enters after price has already given back part of a run.
    Restricting to shallow corrections dissolves that penalty to -0.25% -- which
    is what the mechanism predicts, since a <=10% pullback gives back little. So
    this screen is the version of the Renko flip that has had its known PENALTY
    removed. It still has no edge. Those are different statements and the card
    must not blur them.

    Enforced structurally, the same way ``scan_renko_flip`` is:
      * no ``entry`` / ``stop`` / ``target`` keys -- nothing that reads as a plan;
      * listed in ``opportunity_hub.PIPELINE_EXCLUDED``, so it can never become a
        confluence vote;
      * ``score`` ranks freshness and shallowness ONLY, never conviction.

    The fundamental half of the owner's idea -- revenue and cash-flow growth -- is
    deliberately NOT filtered here. Scanners in this registry are pure price
    functions of ``df``; the Hub card already renders a fundamentals strip beside
    every hit, so the reader sees cash-flow and EPS next to the flip and decides.
    Filtering on it inside a price scanner would hide the disagreements, which on
    an attention list is the information.

    B-57 also settled the owner's original ``<=40%`` version without running it:
    `renko_quality_cardinality.py` counted 4,407 of 4,598 flips (96%) clearing a
    40% cap -- not a filter at all -- with a median ``bricks_in_prior`` of 3,
    which is precisely B-43r's WORST measured bucket (-1.30%). Hence 10, not 40.
    """
    if df is None or len(df) < RENKO_WARMUP + RENKO_ATR_PERIOD + 10:
        return None
    r = _renko_flips(df)
    flips, state = r["flips"], r["state"]
    if not flips or not state:
        return None

    k = len(flips) - 1
    last = flips[k]
    if last["dir"] != 1:                       # UP flips only -- this is the buy read
        return None

    n = len(df)
    bars_ago = (n - 1) - last["index"]
    if bars_ago > max_bars_ago:
        return None

    corr = _correction_before_flip(df, flips, k)
    if corr is None or corr["depth_pct"] > max_correction:
        return None

    close = float(df["close"].iloc[-1])
    brick = state["brick"] or 0.0
    brick_pct = (brick / close * 100.0) if close > 0 else 0.0
    when = "today" if bars_ago == 0 else f"{bars_ago} bar{'s' if bars_ago > 1 else ''} ago"

    reasons = [
        f"Renko grid flipped UP {when} at {last['price']:.2f}, ending a run of "
        f"{corr['bricks_in_prior']} brick(s) down",
        f"The correction it ended was SHALLOW: {corr['depth_pct']:.1f}% from "
        f"{corr['peak']:.2f} to {corr['trough']:.2f} over {corr['days_down']} bars "
        f"(cap {max_correction:.0f}%)",
        f"Brick size {brick:.2f} ({brick_pct:.2f}% of price), from ATR("
        f"{RENKO_ATR_PERIOD}) re-set every {RENKO_EPOCH_BARS} bars — not tuned",
        "MEASURED AT NO EDGE (B-57): −0.25% at 20d vs a state-matched baseline, "
        "p_rot=0.714, n=207. This is an attention list, not a trigger.",
        "What it IS: the flip with its known penalty removed. B-43r measured the "
        "bare flip at −1.01% (p=0.000) because an up-flip re-enters after giving "
        "back part of a run; a shallow pullback gives back little. Penalty gone, "
        "edge still absent — check the fundamentals strip and bring your own trigger.",
    ]
    return {
        "pattern_type": "Renko UP flip out of a shallow correction",
        "tags": ["Shallow flip", f"correction {corr['depth_pct']:.1f}%", when,
                 "Screen, not trigger", "Measured: no edge"],
        "reasons": reasons,
        # Freshness + shallowness. Explicitly NOT conviction: B-57 measured this
        # condition at no edge, so a higher number means "more current and shallower",
        # never "more likely to work".
        "score": round(max(10.0, 60.0 - 8.0 * bars_ago
                           - 2.0 * corr["depth_pct"]), 1),
        "renko_dir": "UP",
        "renko_bars_ago": bars_ago,
        "renko_brick": round(brick, 4),
        "correction_pct": corr["depth_pct"],
        "correction_days": corr["days_down"],
        "rs_raw": _rs_raw(df),
    }



# ── Quasimodo (QM / "over and under") — B-58 ─────────────────────────────────
#
# The BUY-side sequence, and the one thing that makes it a QM rather than an
# inverse head-and-shoulders. Both shapes put the head below the shoulders, so
# that condition distinguishes nothing. What does:
#
#   * CHOCH — the post-head rally must break the PRE-head swing high (RH > LH).
#     That is the change of character the pattern is named for.
#   * The entry sits at the LEFT SHOULDER's low retested from above, not at a
#     neckline break.
#
# Swings come from `detect_structure_chain`, the same source `detect_liquidity_pools`
# reads, so the QM geometry and the pools can never disagree about where a swing is.
#
# ── Why the right shoulder is OPTIONAL, which B-58's first draft got wrong ────
# A swing pivot needs `pivot_len` bars on BOTH sides to confirm. The right
# shoulder is the retracement into the entry zone -- so requiring it to be a
# confirmed pivot means the pattern only becomes visible `pivot_len` bars AFTER
# price has already been in the zone and left it. A detector that can only see
# the setup once it is untradeable is a chart annotator, not a screen.
#
# So the pattern COMPLETES at the CHOCH (LS, LH, HEAD, RH) and the right shoulder
# is reported when a confirmed low exists and left None when it does not. Whether
# price is in the zone right now is a separate, live field (`in_zone`) rather than
# something smuggled into the pattern's definition.

#: How near the left-shoulder level counts as "at" the entry zone, in percent.
QM_TOL_PCT = 2.0

#: Swing-sequence window. Deep enough for the four-pivot shape, bounded so an
#: ancient pattern is not resurrected long after it stopped describing the tape.
QM_LOOKBACK = 120

#: Minimum size for the two conditions that DEFINE the pattern, in percent.
#:
#: Without these the detector fires on 73% of names (measured, 460 liquid NSE
#: names) -- which is not a pattern, it is "this stock has had a pullback and a
#: rally". The reason is that both conditions were tested as strict inequalities:
#: a head 0.2% below the left shoulder counted as a liquidity grab (BANKBEES did
#: exactly that), and a 1.1% clearance of the pre-head high counted as a change
#: of character. Neither is the event the pattern is named for.
#:
#: The floor is `detect_liquidity_pools`'s own equal-level tolerance rather than a
#: number invented here: that function already treats levels within 0.75% as EQUAL
#: -- as a liquidity pool rather than a break. A "grab" shallower than the desk's
#: own definition of equal is not a grab, and a "break" that small is not a break.
#: Reusing the constant keeps one definition of when two levels are the same.
QM_MIN_GRAB_PCT = 0.75
QM_MIN_CHOCH_PCT = 0.75


def detect_quasimodo(df: pd.DataFrame, pivot_len: int = 5,
                     lookback: int = QM_LOOKBACK,
                     tol_pct: float = QM_TOL_PCT,
                     min_grab_pct: float = QM_MIN_GRAB_PCT,
                     min_choch_pct: float = QM_MIN_CHOCH_PCT) -> dict | None:
    """The most recent BUY-side Quasimodo, or None.

    Sequence, chronological, over alternating swing pivots:

        LS    swing LOW                      the left shoulder
        LH    swing HIGH after LS
        HEAD  swing LOW  **below LS**        the liquidity grab (sell-side stops)
        RH    swing HIGH **above LH**        the CHOCH -- completes the pattern
        RS    swing LOW  **above HEAD**      the right shoulder, OPTIONAL (see above)

    Entry zone is `LS` +- `tol_pct`; invalidation is below `HEAD`.

    Returns the pivots with their bars and levels, the zone, the invalidation,
    `bars_ago` (since the CHOCH), and `choch_break_pct` / `grab_depth_pct` -- a
    token CHOCH break and a decisive one are not the same event, and a caller
    thresholding on either should not have to recompute it and risk drifting from
    this definition.

    **NOT a trade plan.** No entry/stop/target keys, and any wrapping scanner is
    registered PIPELINE_EXCLUDED until B-58's pre-registered test runs. The family
    this belongs to -- retrace into a level after a structure break -- has measured
    negative on this desk three times (`scan_ict_setup` -0.36%/-1.24%, `Order Block
    Retest` -0.47%/-0.70%, `Pullback Entry` -0.43%/-1.12%, ~9,000 signals), so the
    prior is low and the geometry is the only thing being added.
    """
    if df is None or len(df) < pivot_len * 4 + 40:
        return None
    df = _clean_ohlc(df)
    if len(df) < pivot_len * 4 + 40:
        return None

    # max_swings must cover `lookback`, or this function's window is not the window
    # it documents. The default is 15; measured on 200 liquid names, **29% carry
    # more than 15 swings inside the 120-bar lookback** (median exactly 15, max 20),
    # and in 2% the cap silently dropped the oldest in-window swings and with them a
    # valid pattern. The filter below then trimmed to `lookback` anyway, so the cap
    # was doing nothing except removing history the filter was about to keep.
    #
    # Found auditing every `detect_structure_chain` caller after the same default
    # invalidated B-58's first measurement. Every OTHER caller is safe: the chart
    # endpoint and `read_market_structure` pass their own, `detect_liquidity_pools`
    # sets 200 deliberately, and the scanner harness replays `scan_*(df.iloc[:t+1])`
    # per bar, where a trailing window is exactly right.
    chain = detect_structure_chain(df, pivot_len=pivot_len,
                                   max_swings=max(15, lookback))
    if not chain:
        return None
    swings = chain.get("swings") or []
    if len(swings) < 4:
        return None

    n = len(df)
    swings = [s for s in swings if s.get("bar", 0) >= n - 1 - lookback]
    if len(swings) < 4:
        return None
    swings = sorted(swings, key=lambda s: s["bar"])

    # `detect_structure_chain` can emit the same extreme on consecutive bars
    # (a flat two-bar top registers twice). Collapse runs of the same kind to
    # their extreme, or the four-pivot walk below burns its slots on duplicates.
    dedup: list[dict] = []
    for sw in swings:
        if dedup and dedup[-1]["kind"] == sw["kind"]:
            better = (float(sw["level"]) > float(dedup[-1]["level"])
                      if sw["kind"] == "high"
                      else float(sw["level"]) < float(dedup[-1]["level"]))
            if better:
                dedup[-1] = sw
            continue
        dedup.append(sw)
    swings = dedup
    if len(swings) < 4:
        return None

    # ── The pivots must be CONSECUTIVE, and that is not a detail ─────────────
    # Searching all four positions independently over a 120-bar window finds a
    # qualifying combination in almost any series: measured, it fired on 73% of
    # 460 liquid names, and tightening the grab/CHOCH floors only moved that to
    # 67% because the search simply selected a different, deeper quadruple.
    #
    # A Quasimodo is a LOCAL shape -- LS, LH, HEAD, RH adjacent in the zigzag,
    # exactly as it is drawn. Requiring adjacency is what makes the detector
    # describe a pattern rather than assert that a stock has had a pullback and a
    # rally at some point.
    best: dict | None = None
    for i in range(len(swings) - 4, -1, -1):      # newest qualifying shape wins
        ls, lh, head, rh = swings[i:i + 4]
        if [ls["kind"], lh["kind"], head["kind"], rh["kind"]] !=                 ["low", "high", "low", "high"]:
            continue
        ls_lvl_, lh_lvl_ = float(ls["level"]), float(lh["level"])
        if ls_lvl_ <= 0 or lh_lvl_ <= 0:
            continue
        # The grab: the head must clear the left shoulder's low by more than the
        # desk's own "these levels are equal" tolerance.
        if ((ls_lvl_ - float(head["level"])) / ls_lvl_ * 100.0) < min_grab_pct:
            continue
        # The CHOCH, same reasoning: a clearance inside that tolerance is an
        # equal high, not a change of character.
        if ((float(rh["level"]) - lh_lvl_) / lh_lvl_ * 100.0) < min_choch_pct:
            continue
        best = {"ls": ls, "lh": lh, "head": head, "rh": rh}
        break

    if best is None:
        return None

    ls_lvl = float(best["ls"]["level"])
    head_lvl = float(best["head"]["level"])
    lh_lvl = float(best["lh"]["level"])
    rh_lvl = float(best["rh"]["level"])
    if ls_lvl <= 0 or head_lvl <= 0 or lh_lvl <= 0:
        return None

    # The right shoulder if one has confirmed since the CHOCH. Absent is normal
    # and not a defect -- see the note above.
    rs = None
    for sw in swings:
        if (sw["bar"] > best["rh"]["bar"] and sw.get("kind") == "low"
                and float(sw["level"]) > head_lvl):
            rs = {"bar": int(sw["bar"]), "level": float(sw["level"])}

    tol = ls_lvl * (tol_pct / 100.0)
    last = float(df["close"].iloc[-1])

    return {
        "pattern": "quasimodo_buy",
        "ls": {"bar": int(best["ls"]["bar"]), "level": ls_lvl},
        "lh": {"bar": int(best["lh"]["bar"]), "level": lh_lvl},
        "head": {"bar": int(best["head"]["bar"]), "level": head_lvl},
        "rh": {"bar": int(best["rh"]["bar"]), "level": rh_lvl},
        "rs": rs,
        "entry_zone": (round(ls_lvl - tol, 2), round(ls_lvl + tol, 2)),
        "invalidation": round(head_lvl, 2),
        # How decisively the CHOCH cleared the pre-head high, as a percent of it.
        "choch_break_pct": round((rh_lvl - lh_lvl) / lh_lvl * 100.0, 2),
        # How deep the grab went below the left shoulder.
        "grab_depth_pct": round((ls_lvl - head_lvl) / ls_lvl * 100.0, 2),
        # Bars since the CHOCH -- the event that completes the pattern.
        "bars_ago": int((n - 1) - int(best["rh"]["bar"])),
        "in_zone": bool(ls_lvl - tol <= last <= ls_lvl + tol),
        "below_invalidation": bool(last < head_lvl),
        "last_close": round(last, 2),
    }


# B-92 / PR-3. The flag & pole detector lives in its own module because it is
# self-contained geometry with its own CLI and its own `--count`, and this file
# is already 8.5k lines. The two cards below are thin wrappers over it, the same
# split `scan_falling_wedge` uses over `detect_falling_wedge_geometry`.
import flag_pole as _fp


# ──────────────────────────────────────────────────────────────────────────────
# Double Bottom — the AGPro Reversal Pattern Quality Scanner, ported
# ------------------------------------------------------------------------------
# sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine.md called this port "a
# stronger building block for the 'early buy sign at scale' goal than anything
# discussed so far this session" and it was never built — the recommendation sat
# in the source page and reached neither the backlog nor the code.
#
# ── Why this exists next to `detect_bullish_reversal_structure` ───────────────
# That function is ALSO a double-bottom detector against the same spec, and it
# stays. It is a deliberately loose SUB-SIGNAL of `scan_early_reversal` (one tag
# among several), and Early Reversal has been measured. Tightening it in place
# would silently change a scanner whose numbers are already on record, which is
# the one thing a registry of measured scanners must not do. So the loose one
# keeps its job and this is the full-spec standalone. What the spec adds:
#
#   equality 1.4% (not 3%)       pattern-width gate 10-90 bars
#   ATR break buffer             time symmetry
#   5-factor weighted quality    volume contraction + breakout expansion
#   letter grade                 breakout strength in ATRs
#   retest / confirmed states    follow-through proof
#
# ── The neckline-flatness term is ABSENT, not forgotten ───────────────────────
# AGPro's structure score is "symmetry + time symmetry + neckline flatness". For
# Head & Shoulders the neckline is the average of two troughs, so flatness is the
# gap between them and means something. For a Double Bottom the neckline is a
# SINGLE pivot high — there is no second point to be flat against. The term has
# nothing to measure here, so structure is bottom-equality + time-symmetry
# renormalised, rather than a third component invented to fill the slot.
#
# ── The cooldown is moot here, and that is an adaptation not an omission ──────
# The Pine script re-scans every bar to paint a live overlay, so it needs a
# same-region cooldown and a per-type gap to stop drawing the same reversal
# pocket twice. This runs once per symbol per scan and returns ONE dict, so
# "do not emit the same pocket twice" is structural rather than a rule to enforce.
#
# ── Follow-through proof is reported and NEVER scored ─────────────────────────
# The wiki calls it the standout idea and also names the trap: "a pattern can be
# a textbook 'A' grade shape with a 30% real follow-through rate on that name".
# Quality describes the SHAPE; follow-through describes whether this symbol has
# been honouring these breaks. Folding the second into the first would destroy
# exactly the disagreement that makes it worth reading, so they are two numbers.
# It is always reported WITH its sample size, because on a year of daily bars a
# name typically yields 1-3 past patterns and a bare "67%" off n=3 reads as a
# measurement when it is an anecdote.
#
# NOT MEASURED. No forward edge is claimed for this scanner; it registers as
# `unmeasured` (0.5 edge points) like every new arrival, and the follow-through
# number is descriptive history for one name, not a backtest of the scanner.
# ──────────────────────────────────────────────────────────────────────────────

#: AGPro v2.2 defaults, kept at the source's values so a disagreement with the
#: script is a real disagreement and not a silently retuned parameter.
DB_PIVOT_LEN = 8            # symmetric lookback/lookforward for a swing pivot
DB_EQ_TOL_PCT = 1.4         # how "double" the two bottoms must be
DB_MIN_PULLBACK_PCT = 2.0   # neckline must sit this far above the bottoms
DB_MIN_BARS = 10            # pattern width floor — rejects noise-sized shapes
DB_MAX_BARS = 90            # and ceiling — rejects multi-year structures
DB_ATR_BUFFER = 0.15        # a close must clear the neckline by this many ATRs
DB_FOLLOW_HORIZON = 12      # bars after confirmation at which a break is graded
DB_FOLLOW_ATR = 0.75        # move, in ATRs, that counts as follow-through
#: 5-factor quality weights (AGPro v2.2, unchanged).
DB_WEIGHTS = {"structure": 0.28, "depth": 0.22, "volume": 0.18,
              "breakout": 0.17, "context": 0.15}


def _db_pivot_lows(low: np.ndarray, pivot_len: int) -> list[int]:
    """Bars that are the minimum of a symmetric `pivot_len` window.

    The last `pivot_len` bars can never appear: confirming a pivot needs that
    many bars of hindsight. That lag is inherent to any pivot method — the wiki
    page names it as a tradeoff rather than a flaw — and `scan_darvas_box` and
    `scan_vcp` already carry the same one.
    """
    out = []
    n = len(low)
    for i in range(pivot_len, n - pivot_len):
        if low[i] == low[i - pivot_len:i + pivot_len + 1].min():
            out.append(i)
    return out


def _db_pivot_highs(high: np.ndarray, pivot_len: int) -> list[int]:
    """Mirror of `_db_pivot_lows` — the neckline candidates."""
    out = []
    n = len(high)
    for i in range(pivot_len, n - pivot_len):
        if high[i] == high[i - pivot_len:i + pivot_len + 1].max():
            out.append(i)
    return out


def _db_bucket(value: float, table: tuple) -> float:
    """First `score` whose `threshold` the value clears; 0.0 if it clears none.

    AGPro scores its components in buckets rather than on a line, and the buckets
    are kept because a linear rescale would be a different scoring function
    wearing the source's weights.
    """
    for threshold, score in table:
        if value >= threshold:
            return score
    return 0.0


def _db_candidates(df: pd.DataFrame, pivot_len: int, eq_tol_pct: float,
                   min_pullback_pct: float, min_bars: int, max_bars: int,
                   atr_buffer: float) -> list:
    """Every confirmed double bottom in the frame, oldest first.

    Returns geometry only — no scoring — because two callers want different
    things from it: the live read wants the most recent one scored in full, and
    the follow-through proof wants all the OLD ones graded and nothing else.
    """
    n = len(df)
    low = df["low"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    atr = _atr_series(df).to_numpy(dtype=float)

    lows = _db_pivot_lows(low, pivot_len)
    highs = _db_pivot_highs(high, pivot_len)
    if len(lows) < 2 or not highs:
        return []

    out = []
    for a in range(len(lows) - 1):
        for b in range(a + 1, len(lows)):
            i1, i2 = lows[a], lows[b]
            width = i2 - i1
            if width < min_bars:
                continue
            if width > max_bars:
                break                      # lows[b] only moves further away

            b1, b2 = low[i1], low[i2]
            mean_b = (b1 + b2) / 2.0
            if mean_b <= 0:
                continue
            eq_pct = abs(b1 - b2) / mean_b * 100.0
            if eq_pct > eq_tol_pct:
                continue

            between = [h for h in highs if i1 < h < i2]
            if not between:
                continue
            neck_idx = max(between, key=lambda h: high[h])   # highest pivot = neckline
            neck = high[neck_idx]
            if neck <= 0:
                continue
            pullback_pct = (neck - min(b1, b2)) / neck * 100.0
            if pullback_pct < min_pullback_pct:
                continue

            # Confirmation: the FIRST close after the second bottom that clears
            # the neckline by the ATR buffer. Touching it is not a break — that
            # buffer is the whole reason the spec quotes an ATR multiple.
            brk = None
            for j in range(i2 + 1, n):
                a_j = atr[j]
                if not np.isfinite(a_j) or a_j <= 0:
                    continue
                if close[j] > neck + atr_buffer * a_j:
                    brk = j
                    break
            if brk is None:
                continue

            leg1, leg2 = neck_idx - i1, i2 - neck_idx
            out.append({
                "left_idx": int(i1), "right_idx": int(i2),
                "neck_idx": int(neck_idx), "break_idx": int(brk),
                "left_low": float(b1), "right_low": float(b2),
                "neckline": float(neck),
                "eq_pct": float(eq_pct),
                "pullback_pct": float(pullback_pct),
                "width": int(width),
                "time_sym": (float(min(leg1, leg2)) / max(leg1, leg2)
                             if max(leg1, leg2) else 0.0),
                "break_close": float(close[brk]),
                "break_atr": float(atr[brk]),
            })

    # Dedup on the LEFT bottom: one left low can pair with several later lows
    # inside the tolerance, and those are the same reversal pocket described
    # three ways. Keep the widest (most developed) shape per left bottom.
    best = {}
    for c in out:
        prev = best.get(c["left_idx"])
        if prev is None or c["width"] > prev["width"]:
            best[c["left_idx"]] = c
    return sorted(best.values(), key=lambda c: c["break_idx"])


def _db_follow_through(df: pd.DataFrame, cands: list,
                       horizon: int = DB_FOLLOW_HORIZON,
                       atr_mult: float = DB_FOLLOW_ATR):
    """This symbol's own recent record on its own double bottoms.

    Each past confirmation is graded EXACTLY ONCE, at a fixed horizon: did close
    rise at least `atr_mult` ATRs — measured at confirmation time, not today —
    above the confirmation close? A break too recent to have reached its horizon
    is unresolved and is counted neither way; grading it early would score the
    newest and most interesting signals as failures by construction.

    Returns None when nothing has resolved. `n` rides along with `rate` on
    purpose: see the section header.
    """
    close = df["close"].to_numpy(dtype=float)
    n = len(df)
    resolved = follows = 0
    for c in cands:
        j = c["break_idx"]
        if j + horizon >= n:
            continue                      # not yet gradeable
        a = c["break_atr"]
        if not np.isfinite(a) or a <= 0:
            continue
        resolved += 1
        if close[j + horizon] - c["break_close"] >= atr_mult * a:
            follows += 1
    if resolved == 0:
        return None
    return {"rate": round(100.0 * follows / resolved, 1),
            "n": resolved, "follows": follows,
            "horizon": horizon, "atr_mult": atr_mult}


def _db_quality(df: pd.DataFrame, c: dict) -> dict:
    """AGPro's 5-factor weighted quality, 1-10, with its letter grade.

    Every component is 0-10 and the weights are the source's. Returned with the
    parts exposed rather than as one number, because "A+ shape, weak volume" is
    the read that makes the score worth having.
    """
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float) if "volume" in df.columns else None

    # 1. STRUCTURE — bottom equality + time symmetry. Neckline flatness is
    #    absent by construction; see the section header.
    eq_score = max(0.0, 10.0 * (1.0 - c["eq_pct"] / max(DB_EQ_TOL_PCT, 1e-9)))
    sym_score = 10.0 * max(0.0, min(1.0, c["time_sym"]))
    structure = (eq_score + sym_score) / 2.0

    # 2. DEPTH — a deeper pullback to the neckline is a higher-conviction shape.
    depth = _db_bucket(c["pullback_pct"],
                       ((5.0, 10.0), (4.0, 8.5), (3.0, 7.0), (2.0, 5.5)))

    # 3. VOLUME — contraction through the pattern's OWN formation window, then
    #    expansion on the break. The two-sided signature VCP documents.
    volume = 5.0
    vol_ratio = None
    brk_vol_x = None
    if vol is not None:
        seg = vol[c["left_idx"]:c["right_idx"] + 1]
        if len(seg) >= 4:
            half = len(seg) // 2
            first, second = seg[:half].mean(), seg[half:].mean()
            if first > 0:
                vol_ratio = float(second / first)
                # Negated so the shared bucket helper's ">=" reads the right way
                # round: a LOWER second-half ratio is the better score.
                volume = _db_bucket(-vol_ratio,
                                    ((-0.70, 10.0), (-0.85, 8.0),
                                     (-1.00, 6.0), (-1.20, 4.0)))
                if volume == 0.0:
                    volume = 2.0
        j = c["break_idx"]
        base = vol[max(0, j - 20):j]
        if len(base) > 0 and base.mean() > 0:
            brk_vol_x = float(vol[j] / base.mean())
            if brk_vol_x >= 1.5:
                volume += 1.5
            elif brk_vol_x >= 1.2:
                volume += 0.8
        volume = min(10.0, volume)

    # 4. BREAKOUT STRENGTH — how many ATRs past the neckline the break closed.
    atrs_past = ((c["break_close"] - c["neckline"]) / c["break_atr"]
                 if c["break_atr"] > 0 else 0.0)
    breakout = _db_bucket(atrs_past,
                          ((1.00, 10.0), (0.75, 8.5), (0.50, 7.0),
                           (0.30, 5.0), (0.15, 3.5)))

    # 5. EXHAUSTION CONTEXT — how stretched the pattern's low was below EMA(34),
    #    plus how decisively the confirmation bar closed within its own range.
    ema34 = _ema_series(df["close"], 34).to_numpy(dtype=float)
    deep = min(c["left_low"], c["right_low"])
    ref = ema34[c["right_idx"]] if np.isfinite(ema34[c["right_idx"]]) else None
    stretch_score = 5.0
    if ref and ref > 0:
        stretch_pct = (ref - deep) / ref * 100.0
        stretch_score = _db_bucket(stretch_pct,
                                   ((12.0, 10.0), (8.0, 8.0), (5.0, 6.5),
                                    (2.0, 5.0), (0.0, 3.5)))
    j = c["break_idx"]
    rng = high[j] - low[j]
    close_pos = ((close[j] - low[j]) / rng) if rng > 0 else 0.5
    # float() rather than leaving a numpy scalar: this payload is persisted as
    # JSON on the opportunity cards, and while float64 happens to subclass float
    # its integer cousin does not — casting at the boundary keeps the next
    # component that returns an np.int64 from discovering that the hard way.
    context = float((stretch_score + 10.0 * close_pos) / 2.0)

    parts = {"structure": structure, "depth": depth, "volume": volume,
             "breakout": breakout, "context": context}
    q = float(sum(parts[k] * w for k, w in DB_WEIGHTS.items()))
    q = max(1.0, min(10.0, q))
    grade = ("S" if q >= 9 else "A+" if q >= 8 else "A" if q >= 7
             else "B" if q >= 6 else "C" if q >= 4.5 else "D")
    return {"quality": round(q, 1), "grade": grade,
            "parts": {k: round(v, 1) for k, v in parts.items()},
            "atrs_past": round(atrs_past, 2),
            "vol_contraction": round(vol_ratio, 2) if vol_ratio else None,
            "breakout_vol_x": round(brk_vol_x, 2) if brk_vol_x else None}


def detect_double_bottom(df: pd.DataFrame, window: int = 260,
                         pivot_len: int = DB_PIVOT_LEN,
                         eq_tol_pct: float = DB_EQ_TOL_PCT,
                         min_pullback_pct: float = DB_MIN_PULLBACK_PCT,
                         min_bars: int = DB_MIN_BARS,
                         max_bars: int = DB_MAX_BARS,
                         atr_buffer: float = DB_ATR_BUFFER,
                         max_bars_since_break: int = 20):
    """Full-spec Double Bottom geometry, quality score and follow-through record.

    `window` must hold the pattern plus both pivot confirmations plus the break;
    the source page flags that pivot methods need meaningfully more history than
    the oscillator signals already built, so the default is a year of daily bars.

    Returns None when no confirmed pattern is recent enough to be actionable. A
    break older than `max_bars_since_break` is history rather than a setup — it
    still counts toward the follow-through record, it just does not fire.
    """
    need = max(window // 3, pivot_len * 4 + min_bars + 10)
    if df is None or len(df) < need or "volume" not in df.columns:
        return None
    w = df.tail(window).reset_index(drop=True)
    off = len(df) - len(w)
    n = len(w)

    cands = _db_candidates(w, pivot_len, eq_tol_pct, min_pullback_pct,
                           min_bars, max_bars, atr_buffer)
    if not cands:
        return None
    follow = _db_follow_through(w, cands)

    c = cands[-1]                                   # most recent confirmed break
    bars_since = n - 1 - c["break_idx"]
    if bars_since > max_bars_since_break:
        return None

    close = w["close"].to_numpy(dtype=float)
    low = w["low"].to_numpy(dtype=float)
    last = float(close[-1])
    neck = c["neckline"]
    if last <= neck:
        return None                                 # gave the neckline back

    # STATE. The lesson's own sequence is break, then retest, then hold, and the
    # retest is the entry the trading plan actually names — so it is a state
    # rather than a footnote.
    #
    # A retest requires price to have LEFT the neckline first. Checking only
    # "did a low come back within 1%" marks a slow grind straight up off the
    # break as a retest, because the early bars of that grind are still inside
    # the band — caught on a synthetic where price ran 70 -> 84 and never once
    # pulled back. That mislabel is not cosmetic: it swaps the pattern-low stop
    # for the much tighter neckline stop on a trade that never earned it.
    band = neck * 1.01
    away = neck + 0.5 * float(_atr_series(w).to_numpy(dtype=float)[c["break_idx"]])
    retested = False
    left_it = False
    for j in range(c["break_idx"], n):
        # Tested BEFORE `left_it` is updated for this bar, so "left, then came
        # back" is always two different bars. Folding both into one if/elif made
        # the answer depend on which branch ran first, and a wide bar that dips
        # to the neckline and closes strongly above — a textbook retest-and-
        # reclaim — took the "left" branch and never counted as a retest.
        if left_it and low[j] <= band:
            retested = True
            break
        if close[j] >= away:
            left_it = True
    state = "Retest hold" if (retested and bars_since >= 2) else "Confirmed"

    q = _db_quality(w, c)

    # TRADE PLAN. Target is the classic measured move — pattern height projected
    # off the neckline, the same projection `scan_rounding_bottom` uses. The stop
    # sits under the pattern low, which is the level that makes the shape wrong.
    height = neck - min(c["left_low"], c["right_low"])
    atr_now = float(_atr_series(w).to_numpy(dtype=float)[-1])
    entry = last
    stop = min(c["left_low"], c["right_low"]) - 0.5 * atr_now
    # A retest that already held gives a tighter and more honest invalidation:
    # back below the neckline means the break failed, and waiting for the
    # pattern low would sit through the whole failure to find that out.
    if state == "Retest hold":
        stop = max(stop, neck * 0.98)
    target = neck + height
    risk, reward = entry - stop, target - entry
    rr = round(reward / risk, 2) if risk > 0 else None
    # How far past the neckline price already sits. A measured-move target is
    # FIXED by the pattern's own height, so every bar of extension spends the
    # trade's reward without touching its risk — the same "a plan with no room
    # is not a plan" problem MIN_SWEEP_RR was added for. The hit is still
    # reported (the pattern is real and worth seeing) but it stops calling
    # itself a buy.
    extended_pct = (entry - neck) / neck * 100.0 if neck > 0 else 0.0
    if rr is not None and rr < MIN_SWEEP_RR:
        verdict = "EXTENDED (no room)"
    elif state == "Retest hold":
        verdict = "BUY (retest hold)"
    elif (q["breakout_vol_x"] or 0) >= 1.2:
        verdict = "BUY"
    else:
        verdict = "WEAK BUY"

    return {
        "state": state,
        "neckline": round(neck, 2),
        "left_low": round(c["left_low"], 2),
        "right_low": round(c["right_low"], 2),
        "eq_pct": round(c["eq_pct"], 2),
        "pullback_pct": round(c["pullback_pct"], 1),
        "width_bars": c["width"],
        "time_sym": round(c["time_sym"], 2),
        "bars_since_break": bars_since,
        "extended_pct": round(extended_pct, 1),
        # Absolute bar indices into the CALLER's frame, matching the convention
        # `scan_rounding_bottom`'s geometry payload set for the chart endpoint.
        "left_bar_idx": off + c["left_idx"],
        "right_bar_idx": off + c["right_idx"],
        "neck_bar_idx": off + c["neck_idx"],
        "breakout_bar_idx": off + c["break_idx"],
        "follow_through": follow,
        "verdict": verdict,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk_reward": rr,
        **q,
    }


def scan_double_bottom(df: pd.DataFrame):
    """Scanner Hub wrapper — confirmed Double Bottom, AGPro quality graded."""
    d = detect_double_bottom(df)
    if d is None:
        return None
    score = int(round(d["quality"] * 10))
    if score < 55:
        return None                                  # D and low-C shapes are noise

    tags = [f"Grade {d['grade']} ({d['quality']}/10)", d["state"],
            f"neckline {d['neckline']}", f"bottoms ±{d['eq_pct']}%"]
    if d["breakout_vol_x"]:
        tags.append(f"{d['breakout_vol_x']}x break vol")
    ft = d["follow_through"]
    if ft:
        # ALWAYS with n — a bare rate off n=2 reads as a measurement.
        tags.append(f"follow-through {ft['rate']:.0f}% (n={ft['n']})")
    if d["risk_reward"]:
        tags.append(f"R:R {d['risk_reward']}")

    reasons = [
        f"Two lows within {d['eq_pct']}% of each other, {d['width_bars']} bars apart",
        f"Neckline {d['neckline']} sits {d['pullback_pct']}% above the bottoms",
        f"Break closed {d['atrs_past']} ATR past the neckline",
        "Quality {}/10 (grade {}): ".format(d["quality"], d["grade"]) +
        ", ".join(f"{k} {v}" for k, v in d["parts"].items()),
    ]
    if ft:
        reasons.append(
            f"This name's own record on its last {ft['n']} double bottoms: "
            f"{ft['follows']}/{ft['n']} moved {ft['atr_mult']}+ ATR within "
            f"{ft['horizon']} bars. Descriptive history on a small sample, "
            f"never a forward claim.")
    else:
        reasons.append("No prior double bottom in range has resolved yet, so "
                       "this name has no follow-through record.")

    return {
        "pattern_type": "Double Bottom", "tags": tags,
        "reasons": reasons, "score": score,
        # The plan is emitted at the TOP LEVEL as well as inside `geometry`,
        # because that is where the measurement harness looks: `backtest.py`
        # reads `hit.get("entry"/"stop"/"target")` and `scanner_plans.has_plan`
        # checks the same three keys. A plan nested only in `geometry` is
        # readable by a human on the chart card and invisible to the R-simulator
        # — which is why the plan census scores `Rounding Bottom` and
        # `VCP Coiling` as having NO plan despite both emitting one on every hit.
        # Duplicated rather than moved: the chart overlay and /api/double_bottom
        # both read the geometry payload, and this scanner is not the place to
        # change that convention for the others.
        "entry": d["entry"],
        "stop": d["stop"],
        "target": d["target"],
        "geometry": d,
    }


SCANNERS: dict[str, dict] = {
    "Shallow Flip (Renko, bounded correction)": {
        "fn": scan_shallow_flip,
        "description": (
            "Renko UP-flip within the last 2 bars whose preceding down-leg fell no "
            "more than 10% from its prior peak — the owner's 'buy flip after a "
            "bounded correction' idea, built and MEASURED. B-57 scored exactly this "
            "on 460 names against a state-matched baseline (same names, also within "
            "10% of their trailing high, minus the flip) and found NO EDGE: −0.25% "
            "at 20d, p_rot=0.714, n=207, failing its pre-registered bar. It is "
            "registered as an attention list, never a trigger: no entry/stop/target, "
            "never votes in confluence, and the score ranks freshness and shallowness "
            "rather than conviction. The reason it earns a place despite the null is "
            "the shape of it — B-43r measured the BARE flip at −1.01% (p=0.000) "
            "because an up-flip re-enters after price has given back part of a run, "
            "and capping the correction dissolves that penalty to −0.25%. This is "
            "the Renko flip with its known penalty removed and still no edge added. "
            "The owner's original 40% cap was rejected on counting alone: 96% of all "
            "flips clear it, so it filters nothing. Quality is NOT filtered here — "
            "the card's fundamentals strip shows cash-flow and EPS beside each hit "
            "so the disagreements stay visible."
        ),
        "category": "Trend",
    },
    "Renko Flip (structure change)": {
        "fn": scan_renko_flip,
        "description": (
            "Renko brick FLIP in either direction within the last 2 bars — a "
            "structure-change SCREEN, not a trade trigger. Renko samples by price "
            "instead of time, so a flip means price has travelled far enough against "
            "the prior run to reverse the grid. B-43 measured this exact engine's "
            "flips over 23 names / ~19 years and found NO forward edge (up-flip edge "
            "negative at every horizon; stop-and-reverse beat buy-and-hold 0/23), so "
            "it carries no direction implication, no entry/stop/target, and never "
            "votes in confluence. What it does give is fewer, cleaner events (~40% "
            "fewer than the EVWMA cross on the same names), and in a 2,496-cell overlap "
            "audit it flagged 146 cells no other scanner flagged — the largest unique "
            "contribution in the registry. Use it to ask 'which "
            "names just changed structure?' and bring your own tested trigger."
        ),
        "category": "Trend",
    },
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
    "ADX Trend Confirmation": {
        "fn": scan_adx_trend_confirmation,
        "description": ("ADX+DI confirms an up-trend with strength: price > SMA50, "
                        "+DI > −DI, ADX ≥ 25 and rising. A CONFIRMATION/context read, "
                        "not a standalone buy — ADX/DI alone has no measured edge "
                        "(see concepts/ADX.md). Pair with a price+volume trigger."),
        "category": "Trend",
    },
    "Pullback Entry": {
        "fn": scan_pullback_to_ema,
        "description": "Quality stocks that touched EMA21 and are recovering above it",
        "category": "Entry",
    },
    "Order Block Retest": {
        "fn": scan_order_block,
        "description": (
            "Bullish order block (SMC demand zone) retest. Finds the last "
            "down-close candle before a displacement that BROKE STRUCTURE (BOS/"
            "CHOCH up ≥1 ATR), confirms the zone is still unmitigated (never "
            "closed below since), and fires when price is retesting it now and "
            "holding above the zone low. Carries a structured entry/stop/target "
            "(stop below the zone, target at the displacement extension or 2R)."
        ),
        "category": "Entry",
    },
    "HM Buy (Hilega Milega)": {
        "fn": scan_hm_buy,
        "description": (
            "Fresh HM (Hilega Milega) BUY on the last closed daily bar — the "
            "Python port of the chart dashboard's HM sub-plot. RSI(9) crosses "
            "above the 50 pivot with EMA(3)-of-RSI rising while VWMA(21)-of-RSI is "
            "still below 50, then the VWMA(RSI) itself crosses above 50 within 10 "
            "bars = confirmed BUY. Fires when the setup (or confirm) is within the "
            "last 5 bars (~a trading week), so it catches signals from earlier in "
            "the week. Carries a swing-low-stop / 2R trade plan "
            "and a volume-confirmation check. Momentum-reversal read. MEASURED (B-19, "
            "2026-09-02): 3,442 signals, +0.63% @20d / +0.56% @60d — POSITIVE "
            "EDGE but UNSTABLE across walk-forward windows, on the largest "
            "signal count in the batch."
        ),
        "category": "Entry",
    },
    "RSI 60-40 Setup": {
        "fn": scan_rsi_60_40,
        "description": (
            "With-trend RSI 60-40 continuation (21 & 50 EMA). Requires an uptrend "
            "regime — price above both EMAs, EMA21 stacked over EMA50, and RSI(14) "
            "oscillating in the ~40-60 band — then fires one of two entries: an "
            "RSI-40 PULLBACK turning up at EMA support (stop < EMA50), or an RSI-60 "
            "BREAKOUT clearing the 20-day high on ≥1.5× volume (stop < EMA21). Each "
            "hit carries a 2R trade plan. A continuation system, not a reversal one."
        ),
        "category": "Entry",
    },
    "RSI Divergence Bull": {
        "fn": scan_rsi_divergence_bull,
        "description": (
            "Bullish RSI divergence + Fibonacci retracement on the last closed daily "
            "bar — price made a lower pivot low within the last 3 bars while RSI(14) "
            "made a higher low (divergence ≥3 pts), with RSI now rising. Computes "
            "Fibonacci levels (23.6 / 38.2 / 50 / 61.8%) from the swing high between "
            "the two lows; CMP near a fib level boosts score. Card shows CMP / SL "
            "(below 61.8% fib) / TGT (swing high) with R:R. MEASURED (B-19, 2026-09-02): 211 signals, +0.36% @20d / +0.93% @60d, POSITIVE EDGE but flagged UNSTABLE — the sign did not hold across all three walk-forward windows."
        ),
        "category": "Entry",
    },
    "RSI-Fibo Hidden Divergence": {
        "fn": scan_rsi_fibo_hidden_div,
        "description": (
            "Hidden bullish RSI divergence + 50% Fibonacci retracement confluence. "
            "Fires in uptrends (above 200-EMA) when price pulls back to the 50% fib "
            "of the last swing AND forms a hidden divergence (higher price low, lower "
            "RSI low) — a continuation entry, not a reversal. Card shows CMP / SL "
            "(below 61.8% fib) / TGT (swing high) with R:R. MEASURED (B-19) and inconclusive: only 11 signals (−0.10% @20d / −0.08% @60d) — TOO FEW SIGNALS to read either way."
        ),
        "category": "Entry",
    },
    "RSI Divergence Bear": {
        "fn": scan_rsi_divergence_bear,
        "description": (
            "Bearish RSI divergence on the last closed daily bar — price made a "
            "higher pivot high within the last 3 bars (pivot_len=3 symmetry) while "
            "RSI(14) made a lower high (divergence ≥3 RSI points), with RSI now "
            "already rolling over below the divergence high. RSI at the high must "
            "be ≥40. Score rises with overbought depth (≥65 → +15, ≥55 → +8) and "
            "divergence magnitude (gap ≥10 pts → +10). Emits short/exit entry. MEASURED (B-19): 403 signals, −0.84% @20d / −1.18% @60d — BEARISH EDGE, the direction a risk flag should point, but UNSTABLE across windows."
        ),
        "category": "Risk",
    },
    "%R Exhaustion Sell": {
        "fn": scan_percentr_exhaustion_sell,
        "description": (
            "%R Trend Exhaustion SELL — the Python port of the chart's %R Trend "
            "Exhaustion sub-plot (fast Williams %R 21/7, slow 112/3). Fires when "
            "BOTH the fast and slow %R were in the overbought band (≥ -20) and left "
            "it within the last 3 bars = a top/momentum-exhaustion read for exiting "
            "longs or a short bias — NOT a with-trend signal. Adds the SMA50 context "
            "and a swing-high invalidation. MEASURED (B-19): 966 signals, −0.65% @20d / −1.21% @60d — BEARISH EDGE, correct direction for an exhaustion/exit read, UNSTABLE across windows."
        ),
        "category": "Risk",
    },
    "%R Bottoming": {
        "fn": scan_percentr_bottoming,
        "description": (
            "%R bottomed-out candidate — mirror of %R Exhaustion Sell. Fires when "
            "BOTH the fast (21/7) and slow (112/3) Williams %R left the OVERSOLD "
            "band (≤ -80) within the last 3 bars = seller exhaustion / a bottoming "
            "attempt turning up. Carries a swing-low stop and 2R target and flags "
            "whether price has reclaimed SMA50. A turn attempt, not a confirmed "
            "reversal. MEASURED (B-19): 462 signals, +0.55% @20d / +2.68% @60d — POSITIVE EDGE, the largest 60d figure in the batch, but UNSTABLE across windows and NOT cost-survival-tested the way B-41m's sweep was."
        ),
        "category": "Trend",
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
    "PEAD Drift": {
        "fn": scan_pead,
        "enrich": _enrich_pead,
        "description": (
            "Post-Earnings Announcement Drift. Infers the earnings event from a "
            "large up-reaction (≥1.5×ATR, ≥4%) on ≥1.5σ Standardized Unexpected "
            "Volume (a volume z-score vs a 30-day PRE-event baseline, not a raw "
            "ratio) in the last 20 sessions, and fires only while the move is "
            "still holding/extending — the drift. Every hit is then reconciled "
            "against the real NSE result calendar and tagged **Confirmed "
            "earnings** or **Gap-only (unconfirmed)**, and a confirmed hit "
            "carries a TRUE SUE — reported EPS vs analyst consensus, "
            "standardized over its own prior surprises. SUV upgrade absorbed "
            "from the TradingView PEAD screener ingest."
        ),
        "category": "Momentum",
    },
    "Zero-Debt Quality PEAD": {
        # Composite: the "fn" is scan_pead (so any generic caller still gets the
        # drift scan), but the Scanner Hub routes this entry through
        # run_quality_pead() — the quality_pead marker — to apply the yfinance
        # zero-debt / high-ROE / high-OPM quality gate at the symbol level first.
        "fn": scan_pead,
        "quality_pead": True,
        "description": (
            "Zero-Debt + high ROE/OPM names (ANY market cap by default) carrying "
            "the Proxy-PEAD drift edge. A yfinance fundamentals gate (Debt/Equity "
            "≈ 0, ROE & OPM floors, optional market-cap ceiling and optional Max "
            "PE / Max PEG valuation caps — NO login needed) pre-filters the "
            "universe, then PEAD Drift runs over the survivors and each hit is "
            "reconciled against the real result calendar (confirmed vs gap-only, "
            "with a true SUE). Each card "
            "shows ROE · OPM · PE · PEG · market cap. Tick the ceiling toggle "
            "below to restrict to small/mid-caps, where the post-earnings "
            "under-reaction edge is theoretically largest. ROCE proper needs "
            "screener.in (Phase 5.2); ROA & ~PEG shown as labelled proxies. Tune "
            "the gate in the sliders below."
        ),
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
    "Liquidity Sweep": {
        "fn": scan_liquidity_sweep,
        "description": (
            "Bullish liquidity sweep (stop hunt) — price ran a multi-touch "
            "equal-lows pool, pierced it on the wick, and closed back ABOVE it. "
            "A false break, not a breakdown: the distinction is the close, and "
            "one bar cannot be both. Sellers filled below the pool are trapped "
            "and their covering fuels the reversal. Stop below the sweep wick; "
            "target the nearest equal-highs pool overhead. Completes the SMC "
            "stack alongside FVG Pullback and Order Block Retest — this is the "
            "event that validates those entries. Built on B-42's equal-level "
            "labelling. "
            "MEASURED (B-41m, 2026-09-06) — the desk's best signal result: "
            "1,400 signals on LIQUID_50, +0.51% @20d (p=0.0053) and +0.91% @60d "
            "(p=0.0022) NET of ~29bps, hit 57.5%/64.1%, walk-forward sign-stable "
            "at 10/20/60d. It is the only scanner here whose edge survives costs. "
            "BUT THE PLAN BELOW DOES NOT HARVEST IT: B-41p measured the shipped "
            "entry/stop/target at −0.06R against +0.50R for the same signal held "
            "20 days with NO stop (CI excludes 0), and an ATR stop scored no "
            "better than the wick stop. It is not where the stop is, it is that "
            "there is one — the drawdown path is part of the edge. Read the "
            "SIGNAL as measured and the STOP as a known defect."
        ),
        "category": "Entry",
    },
    "Liquidity Sweep Bear": {
        "fn": scan_liquidity_sweep_bear,
        "description": (
            "Bearish liquidity sweep — price ran a multi-touch equal-HIGHS pool, "
            "pierced it on the wick, and closed back BELOW it, trapping breakout "
            "buyers. Risk flag rather than a short signal: it marks a name to "
            "avoid or exit, so a negative forward edge is the desired direction. "
            "Mirror of Liquidity Sweep. "
            "MEASURED (B-41m) and NOT established: 1,471 signals, negative at "
            "every horizon as a risk flag should be (−0.16/−0.18/−0.32/−0.56% "
            "gross at 5/10/20/60d) but nothing reaches significance "
            "(p 0.11/0.19/0.084/0.063). Suggestive, not a result. Known gap: it "
            "emits entry and stop but target=None, so no R line can be computed "
            "for it at all."
        ),
        "category": "Risk",
    },
    "FVG Pullback": {
        "fn": scan_fvg_pullback,
        "description": (
            "Bullish Fair-Value-Gap pullback rejection — price dipped into a "
            "size-gated 3-candle demand gap (> 0.5x ATR, directional middle "
            "candle) and closed back ABOVE its top with a dominant lower wick. "
            "Emits entry/stop/target referenced to the gap. Deliberately not a "
            "resting limit order inside the zone: that fills on the way through "
            "exactly when the gap fails. Wraps detect_fvg_pullback, which "
            "previously existed only as one boolean inside the Early Reversal "
            "layer and so was never screenable. MEASURED (B-19): 1,731 signals, +0.11% @20d / −0.37% @60d — nominally POSITIVE EDGE at 20d, UNSTABLE, and it turns negative by 60d. Effectively flat."
        ),
        "category": "Entry",
    },
    "ICT Setup": {
        "fn": scan_ict_setup,
        "description": (
            "ICT Execution Blueprint composite scanner — chains four ICT primitives: "
            "(1) MSS with displacement: BOS/CHoCH where the break candle body is "
            ">50% of its range, proving institutional participation; "
            "(2) OTE zone: 61.8–79% Fibonacci retracement of the displacement leg — "
            "where institutional orders were left unfilled; "
            "(3) price currently inside the OTE zone (pullback in progress); "
            "(4) FVG (active zone or recent rejection) overlapping the OTE zone — "
            "two independent methods pointing to the same price area. "
            "Stop below OTE zone low; target = 40-bar swing high (BSL proxy). "
            "Requires all four conditions simultaneously. MEASURED (B-19): 158 signals, −0.36% @20d / −1.24% @60d — NO EDGE. One of the three independent 'retrace into a level after a structure break' implementations measured negative here (~9,000 signals across all three)."
        ),
        "category": "Entry",
    },
    "Downside Risk": {
        "fn": scan_downside_risk,
        "description": "Below key MAs with distribution volume — stocks to avoid or short",
        "category": "Risk",
    },
    "Mean Reversion (Connors RSI2)": {
        "fn": scan_mean_reversion,
        "description": (
            "Connors-style mean-reversion — the SIDEWAYS-regime scanner the playbook "
            "prescribes but nothing previously implemented (B-3). Fires when: price is "
            "≥5% below the 20-SMA (stretched), RSI(2) < 10 (ultra-short exhaustion), "
            "today's close > yesterday (first curl up), and the 200-SMA slope is ≥-0.1% "
            "(not a new downtrend). Stop below the session low; T1 = 20-SMA reversion; "
            "T2 = 20-SMA + 1% buffer. Time stop 10 bars. Low-volume entries are expected "
            "— do NOT require vol expansion for this setup."
        ),
        "category": "Entry",
    },
    "Support Breakdown": {
        "fn": scan_support_breakdown,
        "description": (
            "Bearish structural support breakdown — the mirror of Order Block Retest "
            "(B-19b). Fires when: (1) a bearish BOS or CHOCH confirms structure cracked "
            "below a swing low in the last ~10 bars; (2) price has since retested the "
            "broken level (now resistance) from below; (3) the retest failed (close back "
            "under); (4) down-day on ≥1× 20-day average volume. Emits a short-side trade "
            "plan (stop above the breakdown level, target = measured move). Evidence "
            "AGAINST a long, not a buy signal. "
            "RETIRED 2026-09-11 — MEASURED (B-19): 2,880 signals, +0.47% @20d / "
            "+1.22% @60d, NO BEARISH EDGE: names it flagged went UP on average. "
            "Now in opportunity_hub.PIPELINE_EXCLUDED, so it no longer runs in the "
            "pipeline and no longer displays a bearish flag on shortlisted names. "
            "It never voted (risk scanners cannot), but a WARNING with no support "
            "steers a reader away from names that outperformed, which is its own "
            "harm. The verdict is [UNSTABLE] — not sign-stable across windows — so "
            "read this as 'the bearish claim has no support', not as a significant "
            "inversion. Still registered, runnable and backtestable (the B-44r GEX "
            "precedent: retired as a decision input, kept as a view); restoring it "
            "needs a NEW measurement finding a bearish edge."
        ),
        "category": "Risk",
    },
    "Bearish Reversal Candle": {
        "fn": scan_bearish_reversal_candle,
        "description": (
            "Bearish reversal candle AT RESISTANCE — Evening Doji Star, Evening "
            "Star, Three Black Crows, Dark Cloud Cover, Bearish Engulfing, "
            "Shooting Star. The bearish mirror of 'Candlestick Patterns', which "
            "covered only bullish shapes. Trend context is checked as of the bar "
            "the pattern started forming (not after the reversal printed), the "
            "resistance location gate is mandatory, and the star's gap "
            "requirement is a parameter (default: the sourced strict reading). "
            "A hit is evidence AGAINST a long, never a confluence vote. "
            "MEASURED (B-19): 1,476 signals, −0.46% @20d / −0.82% @60d — BEARISH "
            "EDGE, the direction a risk flag should point, UNSTABLE across windows."
        ),
        "category": "Risk",
    },
    # One combined entry replaced the four separate 6M/1Y/5Y/10Y buttons
    # (2026-07-22): each stock reports once at the LONGEST duration it broke,
    # and the hub renders a single longest-first table instead of cards.
    "Consolidation Breakout (6M–10Y)": {
        "fn": scan_all_duration_breakout,
        "description": (
            "All durations in one pass — 10-year, 5-year, 1-year and 6-month "
            "consolidation breakouts (Close > period high, above EMA50, Volume "
            "> 2L, range gate per duration). Each stock is reported at the "
            "longest duration it cleared; results table sorts longest first."
        ),
        "category": "Pattern",
    },
    "Flag & Pole": {
        "fn": _fp.scan_flag_pole,
        "description": (
            "Proportionate bull continuation: a pole of ≥4× ATR in ≤15 bars, then a "
            "flag retracing ≤50% of it in 3–25 bars, then a close above the flag "
            "high. The general case of High Tight Flag, which demands a ≥90% pole "
            "and was one of three scanners B-19 could not score for too few "
            "signals. Emits the card's three levels — entry at the flag break, stop "
            "at the far flag boundary, target = the POLE HEIGHT PROJECTED. That "
            "target is a measured move, NOT a forecast. Present on 5.1% of bars, "
            "BROKEN OUT on 0.45%. **MEASURED 2026-09-17 (B-92), 1,189 breakouts "
            "on 248 names: edge +0.71% at 20 sessions, p=0.0499 — a PASS by the "
            "pre-registered rule, and a MARGINAL one sitting on the threshold.** "
            "Nothing at 5 or 10 days (p≈0.86). The PLAN did better than the "
            "entry: target hit 36.8% against a 51.6% stop rate, avg +0.36R — it "
            "loses more often than it wins and still pays, which is what a "
            "measured move is supposed to do. **No confluence vote**: one test "
            "buys visibility, not authority, and a momentum confound is "
            "unresolved (it fires only after a 4×ATR thrust). See "
            "analyses/Flag-Pole-Pre-Registration."
        ),
        "category": "Pattern",
    },
    "Inverted Flag & Pole": {
        "fn": _fp.scan_inverted_flag_pole,
        "description": (
            "The bear mirror, and the first bear continuation detector on this desk. "
            "Down pole ≥4× ATR, shallow bounce retracing ≤50%, close below the flag "
            "low. **Read it as EXIT / AVOID, not as an entry** — shorting NSE cash "
            "for a swing hold is not available to most users here, so the useful "
            "meaning is 'do not be long', the same scoping B-90 carries. Present on "
            "3.3% of bars, broken out on 0.32%. **MEASURED 2026-09-17 (B-92) and "
            "INVERTED — do not trade it in either direction.** 979 breakdowns "
            "on 248 names: the stock went UP +1.33% MORE than baseline at 20 "
            "sessions (p=0.0005), and the plan hit its target only 8.6% of the "
            "time against a 77.8% stop rate, avg −0.44R. A bear flag breaking "
            "down was followed by strength. **The mirror was NOT shipped** — a "
            "significant inversion is a reason to re-read the construction, not "
            "to flip the label, and the window is a market that rose. Kept as "
            "STRUCTURE only: it marks a down thrust that paused, which is worth "
            "seeing, but on this evidence it is neither a short nor an exit "
            "signal. See analyses/Flag-Pole-Pre-Registration."
        ),
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
    "Double Bottom": {
        "fn": scan_double_bottom,
        "description": (
            "Confirmed Double Bottom, ported from the AGPro Reversal Pattern "
            "Quality Scanner (sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine.md, "
            "concepts/Reversal-Chart-Patterns.md) at the source's own parameters: "
            "two swing lows within 1.4% of each other, 10-90 bars apart, a "
            "neckline pivot at least 2% above them, and a close clearing that "
            "neckline by 0.15x ATR — touching it is not a break. Graded S/A+/A/B/C "
            "on AGPro's 5-factor weighted quality (structure .28, depth .22, volume "
            ".18, breakout strength .17, exhaustion context .15), which scores the "
            "SHAPE and nothing else. Separately it reports FOLLOW-THROUGH: this "
            "symbol's own past double bottoms, each graded once at 12 bars against "
            "a 0.75x ATR move, always printed with its sample size because the "
            "typical n is 1-3. The two numbers are kept apart on purpose — the "
            "source page's own warning is that a textbook A-grade shape can sit on "
            "a 30% real follow-through rate for that name. States: Confirmed, or "
            "Retest hold once price has come back to the neckline and held, which "
            "is the entry the pattern's trading plan actually names. NOT MEASURED "
            "— no forward edge is claimed, it scores as `unmeasured`, and the "
            "follow-through figure is descriptive history for one symbol rather "
            "than a backtest of the scanner."
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
    "Candlestick Patterns": {
        "fn": scan_candlestick,
        "description": (
            "Fresh bullish candlestick on the LATEST bar — Bullish Engulfing, "
            "Hammer, Piercing Line or Morning Star — with volume confirmation and "
            "a preference for pullback locations (at/below EMA20) over extended "
            "ones. A trigger, not a system, so scores stay modest. (Opportunity "
            "Hub Phase 3.)"
        ),
        "category": "Entry",
    },
    "IPO-Base Breakout": {
        "fn": scan_ipo_breakout,
        "needs_full_history": True,
        "description": (
            "First-base breakout for RECENTLY LISTED names — young stocks (read "
            "from total listing history) making a new post-listing high out of a "
            "tight base on ≥1.5× volume, not yet extended. Needs full listing "
            "history (the hubs feed it automatically). (Opportunity Hub Phase 3.)"
        ),
        "category": "Pattern",
    },
    "ATH Breakout (all-time high)": {
        "fn": scan_ath_breakout,
        "needs_full_history": True,
        "description": (
            "TRUE all-time-high breakout — a new closing high over the entire "
            "listing history (not the ~1-year high of 52-Week Leaders), volume-"
            "confirmed, not extended, with a bonus when it breaks from a tight "
            "base near the highs. Needs full history (the hubs feed it "
            "automatically). (Opportunity Hub Phase 3.)"
        ),
        "category": "Pattern",
    },
    "Falling Wedge": {
        "fn": scan_falling_wedge,
        "description": (
            "Falling wedge → bullish breakout. Two CONVERGING downward trendlines "
            "(upper steeper than lower) over the last 60 bars, fitted by regression "
            "through the swing highs/lows, ≥2 touches per side. 0-100 confidence "
            "from containment · convergence · touches · steepness · recency; fires "
            "on an actionable wedge (Breakout close>upper / Pre-Breakout within 0.5% "
            "/ Forming in the upper half) with a measured-move entry/stop/target."
        ),
        "category": "Pattern",
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
    "MFI Oversold Recovery": {
        "fn": scan_mfi_oversold,
        "description": (
            "Money Flow Index (MFI) oversold-recovery scanner. Fires when MFI(14) "
            "crosses UP from below 20 with an up-day and at least average volume. "
            "MFI is volume-weighted RSI on typical price (H+L+C)/3 — it catches "
            "exhaustion exits where heavy selling volume reverses before price "
            "fully recovers. Three gates: MFI crosses 20 from below + up-day "
            "confirmation + volume ≥ 20-day average."
        ),
        "category": "Entry",
    },
    "VWAP Mean Reversion": {
        "fn": scan_vwap_mean_reversion,
        "description": (
            "Two-sided VWAP mean reversion with volume in BOTH roles (B-40m). Price "
            "stretches ≥2σ from the rolling 20-day VWAP on EXTREME volume (≥1.5×20d at "
            "the extreme), then closes back inside the band on a reversal candle with "
            "RISING volume (≥1.2×20d). Target is the VWAP itself; stop sits beyond the "
            "excursion extreme the market already rejected. Distinct from VWAP "
            "Reclaim/Support, which is long-only, with-trend, and treats volume as a "
            "floor — a reversion on FALLING volume is the failure case this rule exists "
            "to skip, and no other scanner here can express that. The bearish side is a "
            "trim/avoid read, not a short. Natively an intraday rule; on daily bars the "
            "rolling VWAP measures a different claim, which `vwap_mean_reversion.js` "
            "reports as source='rolling' so the two are never conflated. MEASURED "
            "(B-40m): +0.19% edge at 5d and 10d (p 0.51/0.57) and the traded rule returns "
            "+0.04R gross, −0.19R after Indian delivery costs. A chart and coverage read, "
            "NOT a trigger — third VWAP rule to measure null here."  # claims-lint: checked B-40m
        ),
        "category": "Entry",
    },
    "VWAP Reclaim/Support": {
        "fn": scan_vwap_reclaim,
        "description": (
            "Rolling-VWAP reclaim / pullback-support (B-40 — VWAP as a signal, not "
            "just a chart line). On daily bars a session VWAP is meaningless, so the "
            "tradeable mean is a rolling 20-day VWAP: in a healthy trend price rides "
            "above it and pulls back TO it, so the VWAP is the mean the classic "
            "trend+pullback entry needs — not just an EMA. Fires on a reclaim cross "
            "(close back above VWAP on ≥20-day-avg volume) OR a pullback-hold (a bar "
            "tags VWAP within 1% and price bounces). With-trend only (close > EMA-50), "
            "VWAP rising, and not extended (≤6% above the mean). The anchored-VWAP-"
            "from-catalyst read is the complementary chart feature (B-4/B-12). "
            "MEASURED (B-40) — edge is NEGATIVE at every horizon and significantly so: "
            "−0.20% @10d (p=0.042), −0.45% @20d (p=0.0006), −0.50% @60d (p=0.033) over "
            "2745 signals. It selects bars that do WORSE than a random bar from the same "
            "pool. Coverage and context only — NOT an entry."  # claims-lint: checked B-40
        ),
        "category": "Entry",
    },
    "EMA-50 Coil": {
        "fn": scan_ema50_coil,
        "description": (
            "EMA-50 coiled-spring breakout (Ashok Daniel StockEdge scanner). "
            "Captures quality stocks resting within 2% of their 50-EMA floor that "
            "break out on institutional volume before the trend becomes obvious. "
            "Five gates: Close > EMA200 (uptrend) + ADX(14) > 25 & rising + "
            "+DI > -DI + Close within ±2% of EMA-50 + Close > 1.03× prior close "
            "on volume > 20-day avg. The ±2% proximity gate is the key new mechanic "
            "from the StockEdge Epic Scanner compilation — rest-before-thrust, not chase."
        ),
        "category": "Entry",
    },
    "RSI Mid-Band Momentum": {
        "fn": scan_rsi_band_momentum,
        "description": (
            "RSI 50–68 mid-band momentum (Patel Yash Ashokbhai StockEdge scanner). "
            "Targets momentum stocks approaching new highs without being overbought. "
            "The RSI UPPER cap (68) is the key new mechanic — it explicitly excludes "
            "extended stocks, creating a setup-zone scan rather than a chase scan. "
            "Gates: within 10% of 52-week high + RSI(14) in [50, 68] + SMA20 > SMA50 "
            "+ Close > SMA50 + RSI rising vs prior day."
        ),
        "category": "Momentum",
    },
    "Triple-RS 52W Cross": {
        "fn": scan_triple_rs_52w,
        "description": (
            "Triple relative-strength + 52-week high crossover (Ashok Taneja StockEdge "
            "scanner). Requires ALL three RS measures positive simultaneously before "
            "firing — the triple-gate is the key new mechanic. Price-only equivalents: "
            "(1) 55-day absolute return > 0 (ARS proxy); (2) 55-day excess return > 0 "
            "vs benchmark if supplied (RSMkt55Days proxy); (3) daily RSI rising; "
            "(4) weekly RSI (5-bar sample) rising; (5) 52-week high crossover in last "
            "5 sessions; (6) RSI < 80 anti-chase gate. One RS failure disqualifies."
        ),
        "category": "Momentum",
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

    _tls.benchmark_wret = None
    if benchmark_df is not None and not benchmark_df.empty:
        try:
            col = "close" if "close" in benchmark_df.columns else "Close"
            _tls.benchmark_wret = _weighted_trailing_return(benchmark_df[col])
        except Exception:
            _tls.benchmark_wret = None

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
        _tls.benchmark_wret = None  # never leak benchmark state across scans

    _finalize_relative_strength(results)
    # Symbol-level enrichment. A scan fn only ever sees OHLCV, so anything keyed
    # on the symbol (the PEAD result calendar, its SUE) has to be joined here,
    # after the symbol is attached. Declared per-scanner so this stays opt-in.
    enrich = spec.get("enrich")
    if enrich is not None:
        try:
            results = enrich(results)
        except Exception as e:
            log.debug("enrichment failed for %s: %s", scanner_name, e)
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)


# ──────────────────────────────────────────────────────────────────────────────
# Phase 5.1 — Quality-gated Small-Cap Proxy-PEAD
# ------------------------------------------------------------------------------
# The zero-debt / high-ROE / high-OPM small-cap gate the user asked for, combined
# with the Proxy-PEAD drift engine. Fundamentals come from yfinance `.info` —
# NO screener.in login required (the session-capture path was abandoned as too
# fragile on this machine; see wiki log 2026-07-24).
#
# yfinance field units (verified 2026-07-24):
#   • marketCap       — currency (INR); /1e7 = ₹ Crore
#   • debtToEquity    — PERCENT form (95.4 ⇒ D/E ratio 0.95); ratio = field/100
#   • returnOnEquity  — ratio (0.156 ⇒ 15.6%)
#   • operatingMargins— ratio (0.393 ⇒ 39.3%)
#   • returnOnAssets  — ratio; carried as an HONEST ROA PROXY for ROCE (true ROCE
#                       = EBIT / capital employed is not in yfinance; the real
#                       ROCE upgrade needs screener.in — deferred to Phase 5.2).
#
# NSE fundamentals coverage in yfinance is PATCHY — many names return None for
# some/all of these. Missing fields are surfaced, never faked; `require_complete`
# controls whether a name with an unverifiable gate is dropped (default) or kept.
#
# Architectural note: scan_pead is symbol-blind (run_scanner attaches the symbol
# only AFTER the fn runs), so the quality gate CANNOT live inside it. It is
# applied here at the SYMBOL level — filter on fundamentals first, then run
# scan_pead on the survivors' OHLCV — exactly the universe-join the roadmap scoped.
# ──────────────────────────────────────────────────────────────────────────────

_FUND_CACHE: dict[str, dict | None] = {}


def _yf_symbol(symbol: str) -> str:
    """Scanner-hub universes carry bare NSE tickers; yfinance needs the .NS suffix."""
    return symbol if ("." in symbol or symbol.startswith("^")) else f"{symbol}.NS"


def fetch_fundamentals_yf(symbol: str, use_cache: bool = True) -> dict | None:
    """Login-free fundamentals for the quality gate, via yfinance `.info`.

    Returns a dict with market_cap_cr / de_ratio / roe_pct / opm_pct / roa_pct
    (any of which may be None when yfinance has no value), or None if the whole
    lookup failed. Cached per process so re-runs over the same universe are fast.
    """
    if use_cache and symbol in _FUND_CACHE:
        return _FUND_CACHE[symbol]
    try:
        import yfinance as yf
        info = yf.Ticker(_yf_symbol(symbol)).info or {}
    except Exception:
        if use_cache:
            _FUND_CACHE[symbol] = None
        return None

    mc = info.get("marketCap")
    de = info.get("debtToEquity")        # percent form → ratio = /100
    roe = info.get("returnOnEquity")
    opm = info.get("operatingMargins")
    roa = info.get("returnOnAssets")
    pe = info.get("trailingPE") or info.get("forwardPE")

    # PEG: prefer yfinance's own ratio; it's sparse for NSE (often None), so fall
    # back to PE / (earnings growth %) — labelled 'calc' so the card can mark it
    # approximate rather than passing it off as the vendor's figure.
    peg = info.get("trailingPegRatio") or info.get("pegRatio")
    peg_src = "yf" if peg is not None else None
    if peg is None:
        eg = info.get("earningsGrowth")
        if pe and eg and eg > 0:
            peg = pe / (eg * 100.0)
            peg_src = "calc"

    # Cash flow — try the .cashflow statement (annual, column 0 = most recent FY).
    # freeCashflow in .info is rarely populated for NSE; the statement is more
    # reliable.  We accept None gracefully so a missing statement never crashes.
    fcf_cr = ocf_cr = None
    try:
        tk = yf.Ticker(_yf_symbol(symbol))
        cf = tk.cashflow          # columns = period dates, rows = line items
        if cf is not None and not cf.empty:
            # yfinance row labels vary by version — try both casing forms.
            _ocf_row = next(
                (r for r in cf.index
                 if "Operating" in r and "Cash" in r and "Activities" in r), None)
            _capex_row = next(
                (r for r in cf.index
                 if "Capital" in r and ("Expenditure" in r or "Expenditures" in r)), None)
            if _ocf_row is not None:
                _ocf_val = cf.loc[_ocf_row].iloc[0]
                if _ocf_val is not None and not (hasattr(_ocf_val, "__float__") and
                                                  __import__("math").isnan(float(_ocf_val))):
                    ocf_cr = round(float(_ocf_val) / 1e7, 1)
                    if _capex_row is not None:
                        _capex_val = cf.loc[_capex_row].iloc[0]
                        if _capex_val is not None:
                            fcf_cr = round((float(_ocf_val) + float(_capex_val)) / 1e7, 1)
                        else:
                            fcf_cr = ocf_cr
    except Exception:
        pass

    rev_g  = info.get("revenueGrowth")     # annual revenue growth (0-based fraction)
    earn_g = info.get("earningsGrowth")    # annual earnings growth (0-based fraction)

    # EPS / EBITDA / revenue (login-free, from .info). EBITDA + revenue come in
    # absolute rupees → crore; EPS is already per-share. Cash-flow margin = OCF as
    # a % of revenue (both to ₹cr first so the ratio is unit-consistent).
    eps      = info.get("trailingEps")
    ebitda   = info.get("ebitda")
    revenue  = info.get("totalRevenue")
    ebitda_cr  = round(ebitda / 1e7) if ebitda else None
    revenue_cr = round(revenue / 1e7) if revenue else None
    cf_margin_pct = (
        round(ocf_cr / revenue_cr * 100.0, 1)
        if (ocf_cr is not None and revenue_cr) else None
    )

    out = {
        "market_cap_cr": round(mc / 1e7) if mc else None,
        "de_ratio": round(de / 100.0, 3) if de is not None else None,
        "roe_pct": round(roe * 100.0, 1) if roe is not None else None,
        "opm_pct": round(opm * 100.0, 1) if opm is not None else None,
        "roa_pct": round(roa * 100.0, 1) if roa is not None else None,
        "pe": round(pe, 1) if pe else None,
        "peg": round(peg, 2) if peg is not None else None,
        "peg_src": peg_src,
        "fcf_cr": fcf_cr,    # free cash flow (OCF − CapEx) in ₹ crore, most recent FY
        "ocf_cr": ocf_cr,    # operating cash flow in ₹ crore
        "eps": round(eps, 2) if eps is not None else None,          # trailing EPS (₹/share)
        "ebitda_cr": ebitda_cr,          # EBITDA in ₹ crore
        "revenue_cr": revenue_cr,        # total revenue in ₹ crore
        "cf_margin_pct": cf_margin_pct,  # operating cash-flow margin = OCF ÷ revenue %
        "pledge_pct": None,  # promoter pledge % — not in yfinance; set by a Screener source if wired
        # Growth metrics for PEAD pre-filter (annual; yfinance earningsGrowth /
        # revenueGrowth are annual fractions — *100 to match screener.in % convention).
        "revenue_growth_pct":  round(rev_g  * 100.0, 1) if rev_g  is not None else None,
        "earnings_growth_pct": round(earn_g * 100.0, 1) if earn_g is not None else None,
        # Sector / industry classification (login-free) — used by the Opportunity
        # Hub funnel to rank sector & industry leadership bottom-up.
        "sector": info.get("sector"),
        "industry": info.get("industry"),
    }
    if use_cache:
        _FUND_CACHE[symbol] = out
    return out


def passes_quality_gate(f: dict | None, *,
                        min_market_cap_cr: float | None = None,
                        max_market_cap_cr: float | None = None,
                        max_de_ratio: float | None = 0.10,
                        min_roe_pct: float | None = 15.0,
                        min_opm_pct: float | None = 10.0,
                        max_pe: float | None = None,
                        max_peg: float | None = None,
                        min_revenue_growth_pct: float | None = None,
                        min_earnings_growth_pct: float | None = None,
                        require_complete: bool = True) -> bool:
    """True iff the fundamentals clear the zero-debt + quality (+ valuation) gate.

    Cap-agnostic by default (both market-cap bounds None → all caps). Valuation
    caps (`max_pe`, `max_peg`) are off by default. Growth floors (`min_revenue_growth_pct`,
    `min_earnings_growth_pct`) map to screener.in's Sales > X% / PAT > X% filters
    and use yfinance annual growth (quarterly data requires heavier fetches). A gate
    whose data is missing fails when `require_complete` (the honest default); with
    `require_complete=False` a missing field is skipped rather than failing.
    """
    if f is None:
        return False

    checks = (
        (min_market_cap_cr,      f.get("market_cap_cr"),      lambda v: v >= min_market_cap_cr),
        (max_market_cap_cr,      f.get("market_cap_cr"),      lambda v: v <= max_market_cap_cr),
        (max_de_ratio,           f.get("de_ratio"),           lambda v: v <= max_de_ratio),
        (min_roe_pct,            f.get("roe_pct"),            lambda v: v >= min_roe_pct),
        (min_opm_pct,            f.get("opm_pct"),            lambda v: v >= min_opm_pct),
        (max_pe,                 f.get("pe"),                 lambda v: v <= max_pe),
        (max_peg,                f.get("peg"),                lambda v: v <= max_peg),
        (min_revenue_growth_pct, f.get("revenue_growth_pct"), lambda v: v >= min_revenue_growth_pct),
        (min_earnings_growth_pct,f.get("earnings_growth_pct"),lambda v: v >= min_earnings_growth_pct),
    )
    for threshold, value, ok in checks:
        if threshold is None:
            continue                    # this gate disabled
        if value is None:
            if require_complete:
                return False            # unverifiable → drop
            continue                    # lenient → skip this check
        if not ok(value):
            return False
    return True


def _attach_quality(hit: dict, f: dict, max_de_ratio: float) -> None:
    """Fold the quality + valuation metrics onto a Proxy-PEAD hit as pills + a
    reason line, and relabel it as the composite scanner."""
    de, roe, opm = f.get("de_ratio"), f.get("roe_pct"), f.get("opm_pct")
    mc, roa = f.get("market_cap_cr"), f.get("roa_pct")
    pe, peg, peg_src = f.get("pe"), f.get("peg"), f.get("peg_src")
    rev_g  = f.get("revenue_growth_pct")
    earn_g = f.get("earnings_growth_pct")
    peg_pfx = "~" if peg_src == "calc" else ""     # ~ marks a computed (not vendor) PEG

    qtags: list[str] = []
    if de is not None:
        qtags.append("Zero-Debt ✓" if de <= max_de_ratio else f"D/E {de:.2f}")
    if roe is not None:
        qtags.append(f"ROE {roe:.0f}%")
    if opm is not None:
        qtags.append(f"OPM {opm:.0f}%")
    if earn_g is not None:
        qtags.append(f"PAT {earn_g:+.0f}%")
    if rev_g is not None:
        qtags.append(f"Sales {rev_g:+.0f}%")
    if pe is not None:
        qtags.append(f"PE {pe:.0f}")
    if peg is not None:
        qtags.append(f"PEG {peg_pfx}{peg:.2f}")
    if mc is not None:
        qtags.append(f"₹{mc:,}Cr")

    hit["pattern_type"] = "Zero-Debt Quality PEAD"
    hit["quality_tags"] = qtags
    hit["fundamentals"] = f
    # Quality/valuation pills lead the metric row, drift tags follow.
    hit["tags"] = qtags + hit.get("tags", [])

    def _fmt(label, val, suffix=""):
        return f"{label} {val}{suffix}" if val is not None else f"{label} n/a"
    quality_line = "Quality: " + ", ".join([
        _fmt("D/E", f"{de:.2f}" if de is not None else None),
        _fmt("ROE", f"{roe:.0f}" if roe is not None else None, "%"),
        _fmt("OPM", f"{opm:.0f}" if opm is not None else None, "%"),
        _fmt("PAT YoY", f"{earn_g:+.0f}" if earn_g is not None else None, "%"),
        _fmt("Sales YoY", f"{rev_g:+.0f}" if rev_g is not None else None, "%"),
        _fmt("PE", f"{pe:.1f}" if pe is not None else None),
        _fmt("PEG", f"{peg_pfx}{peg:.2f}" if peg is not None else None),
        _fmt("mcap", f"₹{mc:,}Cr" if mc is not None else None),
    ])
    if roa is not None:
        quality_line += f" · ROA {roa:.0f}%"
    quality_line += (
        " (yfinance annual growth; ~PEG = PE÷growth when vendor PEG absent)")
    hit.setdefault("reasons", []).insert(0, quality_line)


def run_quality_pead(symbols: list[str], fetch_fn,
                     benchmark_df: pd.DataFrame | None = None, *,
                     min_market_cap_cr: float | None = 500.0,
                     max_market_cap_cr: float | None = 15_000.0,
                     max_de_ratio: float | None = 0.10,
                     min_roe_pct: float | None = 15.0,
                     min_opm_pct: float | None = 10.0,
                     max_pe: float | None = None,
                     max_peg: float | None = None,
                     min_revenue_growth_pct: float | None = 20.0,
                     min_earnings_growth_pct: float | None = 20.0,
                     require_complete: bool = True,
                     pead_kwargs: dict | None = None,
                     progress_cb=None) -> list[dict]:
    """Phase 5.1 composite: quality small-cap gate ∩ Proxy-PEAD drift.

    Defaults match the vault's PEAD pre-filter (2026-08-05):
      MCap 500–15,000 Cr · Sales YoY > 20% · PAT YoY > 20% · ROE > 15%

    For each symbol: confirm the fundamentals gate (cheap, login-free) FIRST, and
    only then fetch OHLCV + run scan_pead — so the expensive price fetch runs only
    on quality survivors. Quality metrics are attached to every hit as pills.

    `progress_cb(i, total)` is called as symbols are processed (for a UI bar).
    """
    pead_kwargs = pead_kwargs or {}

    _tls.benchmark_wret = None
    if benchmark_df is not None and not benchmark_df.empty:
        try:
            col = "close" if "close" in benchmark_df.columns else "Close"
            _tls.benchmark_wret = _weighted_trailing_return(benchmark_df[col])
        except Exception:
            _tls.benchmark_wret = None

    results: list[dict] = []
    total = len(symbols)
    try:
        for i, sym in enumerate(symbols, 1):
            if progress_cb is not None:
                try:
                    progress_cb(i, total)
                except Exception:
                    pass
            f = fetch_fundamentals_yf(sym)
            if not passes_quality_gate(
                    f,
                    min_market_cap_cr=min_market_cap_cr,
                    max_market_cap_cr=max_market_cap_cr,
                    max_de_ratio=max_de_ratio,
                    min_roe_pct=min_roe_pct, min_opm_pct=min_opm_pct,
                    max_pe=max_pe, max_peg=max_peg,
                    min_revenue_growth_pct=min_revenue_growth_pct,
                    min_earnings_growth_pct=min_earnings_growth_pct,
                    require_complete=require_complete):
                continue
            try:
                df = fetch_fn(sym)
            except Exception:
                continue
            if df is None or df.empty:
                continue
            hit = scan_pead(df, **pead_kwargs)
            if not hit:
                continue
            hit["symbol"] = sym
            _attach_quality(hit, f, max_de_ratio if max_de_ratio is not None else 0.10)
            results.append(hit)
    finally:
        _tls.benchmark_wret = None  # never leak benchmark state across scans

    _finalize_relative_strength(results)
    # Same Phase 2+3 join the plain scanner gets via the SCANNERS `enrich` hook —
    # this path bypasses run_scanner, so it has to ask for it explicitly.
    results = _enrich_pead(results)
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
