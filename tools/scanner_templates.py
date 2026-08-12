#!/usr/bin/env python3
"""
scanner_templates.py
Pre-built pattern scanners inspired by SwingEdge's scanner hub.
Each scanner function takes a fetched OHLCV DataFrame and returns a result
dict (symbol, pattern_type, tags, reasons, score) or None if no match.
"""

import logging

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


def detect_support_breakdown(df: pd.DataFrame, pivot_len: int = 5,
                             lookback: int = 120) -> dict | None:
    """Bearish market-structure event (B-19b): a close BELOW the most recent
    confirmed swing LOW while structure is bullish = bearish CHOCH (first
    counter-trend break); while already bearish = bearish BOS (continuation).
    The mirror-image of ``detect_bos_choch`` — same walk, opposite direction.

    Returns the surviving bearish event or None (no bearish break in the window,
    or a later bullish break invalidated it).
    """
    if len(df) < pivot_len * 4 + 20:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    n = len(df)

    swing_high: float | None = None
    swing_low: float | None = None
    trend = 0           # 1 up / -1 down / 0 unknown
    last_event: tuple[str, int, float] | None = None

    for i in range(max(pivot_len * 2, n - lookback), n):
        j = i - pivot_len
        if j >= pivot_len:
            if high.iloc[j] == high.iloc[j - pivot_len: j + pivot_len + 1].max():
                swing_high = float(high.iloc[j])
            if low.iloc[j] == low.iloc[j - pivot_len: j + pivot_len + 1].min():
                swing_low = float(low.iloc[j])
        c = float(close.iloc[i])
        if swing_low is not None and c < swing_low:
            last_event = ("bearish BOS" if trend == -1 else "bearish CHOCH", i, swing_low)
            trend = -1
            swing_low = None   # consumed
        elif swing_high is not None and c > swing_high:
            trend = 1
            swing_high = None
            last_event = None  # bullish break invalidates the bearish event

    if last_event is None:
        return None
    label, idx, level = last_event
    return {"signal": label, "level": round(level, 2), "bars_ago": n - 1 - idx}


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

    Unmeasured: this scanner has never been through ``analyses/Backtest-Harness``.
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
        "⚠ Unmeasured — this scanner has not been through the backtest harness",
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
        "rs_raw": _rs_raw(df),
        "vol_x50d": round(vol_x, 2),
    }
    if entry and stop and target:
        out.update({"entry": entry, "stop": stop, "target": target,
                    # B-5: time stop — RSI 60-40 is a momentum continuation trade;
                    # 15 bars (3 weeks) without follow-through signals the thesis failed.
                    "time_stop": 15})
    return out


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
        "rs_raw": _rs_raw(df),
        "entry": round(entry, 2),
        "stop": stop,
        "target": target,
        "vol_x50d": round(vol_x, 2),
        # B-5: SMC order-block trades should resolve promptly; 10 bars without
        # follow-through means the zone is not acting as support.
        "time_stop": 10,
    }


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
            "layer and so was never screenable. Unmeasured."
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
            "AGAINST a long, not a buy signal. Unmeasured."
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
            "Unmeasured — not yet through the backtest harness."
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

    out = {
        "market_cap_cr": round(mc / 1e7) if mc else None,
        "de_ratio": round(de / 100.0, 3) if de is not None else None,
        "roe_pct": round(roe * 100.0, 1) if roe is not None else None,
        "opm_pct": round(opm * 100.0, 1) if opm is not None else None,
        "roa_pct": round(roa * 100.0, 1) if roa is not None else None,
        "pe": round(pe, 1) if pe else None,
        "peg": round(peg, 2) if peg is not None else None,
        "peg_src": peg_src,
        # Sector / industry classification (login-free) — used by the Opportunity
        # Hub funnel to rank sector & industry leadership bottom-up.
        "sector": info.get("sector"),
        "industry": info.get("industry"),
    }
    if use_cache:
        _FUND_CACHE[symbol] = out
    return out


def passes_quality_gate(f: dict | None, *,
                        max_market_cap_cr: float | None = None,
                        max_de_ratio: float | None = 0.10,
                        min_roe_pct: float | None = 15.0,
                        min_opm_pct: float | None = 10.0,
                        max_pe: float | None = None,
                        max_peg: float | None = None,
                        require_complete: bool = True) -> bool:
    """True iff the fundamentals clear the zero-debt + quality (+ valuation) gate.

    Cap-agnostic by default (`max_market_cap_cr=None` → all caps); pass a ceiling
    to restrict to small/mid-caps. Valuation caps (`max_pe`, `max_peg`) are off by
    default; when set they screen out expensive names (PEG may be the computed
    `~` proxy — see fetch_fundamentals_yf). A gate whose data is missing fails
    when `require_complete` (the honest default — we can't call a name 'zero-debt'
    if we can't see its debt); with `require_complete=False` a missing field is
    skipped rather than failing.
    """
    if f is None:
        return False

    checks = (
        (max_market_cap_cr, f.get("market_cap_cr"), lambda v: v <= max_market_cap_cr),
        (max_de_ratio,      f.get("de_ratio"),      lambda v: v <= max_de_ratio),
        (min_roe_pct,       f.get("roe_pct"),       lambda v: v >= min_roe_pct),
        (min_opm_pct,       f.get("opm_pct"),       lambda v: v >= min_opm_pct),
        (max_pe,            f.get("pe"),            lambda v: v <= max_pe),
        (max_peg,           f.get("peg"),           lambda v: v <= max_peg),
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
    peg_pfx = "~" if peg_src == "calc" else ""     # ~ marks a computed (not vendor) PEG

    qtags: list[str] = []
    if de is not None:
        qtags.append("Zero-Debt ✓" if de <= max_de_ratio else f"D/E {de:.2f}")
    if roe is not None:
        qtags.append(f"ROE {roe:.0f}%")
    if opm is not None:
        qtags.append(f"OPM {opm:.0f}%")
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
        _fmt("PE", f"{pe:.1f}" if pe is not None else None),
        _fmt("PEG", f"{peg_pfx}{peg:.2f}" if peg is not None else None),
        _fmt("mcap", f"₹{mc:,}Cr" if mc is not None else None),
    ])
    if roa is not None:
        quality_line += f" · ROA {roa:.0f}%"
    quality_line += (
        " (yfinance; ~PEG = PE÷growth when vendor PEG absent; true ROCE via "
        "screener.in is Phase 5.2)")
    hit.setdefault("reasons", []).insert(0, quality_line)


def run_quality_pead(symbols: list[str], fetch_fn,
                     benchmark_df: pd.DataFrame | None = None, *,
                     max_market_cap_cr: float | None = None,
                     max_de_ratio: float | None = 0.10,
                     min_roe_pct: float | None = 15.0,
                     min_opm_pct: float | None = 10.0,
                     max_pe: float | None = None,
                     max_peg: float | None = None,
                     require_complete: bool = True,
                     pead_kwargs: dict | None = None,
                     progress_cb=None) -> list[dict]:
    """Phase 5.1 composite: quality small-cap gate ∩ Proxy-PEAD drift.

    For each symbol: confirm the fundamentals gate (cheap, login-free) FIRST, and
    only then fetch OHLCV + run scan_pead — so the expensive price fetch runs only
    on quality survivors. Quality metrics are attached to every hit as pills.

    `progress_cb(i, total)` is called as symbols are processed (for a UI bar).
    """
    pead_kwargs = pead_kwargs or {}

    global _BENCHMARK_WRET
    _BENCHMARK_WRET = None
    if benchmark_df is not None and not benchmark_df.empty:
        try:
            col = "close" if "close" in benchmark_df.columns else "Close"
            _BENCHMARK_WRET = _weighted_trailing_return(benchmark_df[col])
        except Exception:
            _BENCHMARK_WRET = None

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
                    f, max_market_cap_cr=max_market_cap_cr, max_de_ratio=max_de_ratio,
                    min_roe_pct=min_roe_pct, min_opm_pct=min_opm_pct,
                    max_pe=max_pe, max_peg=max_peg,
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
        _BENCHMARK_WRET = None

    _finalize_relative_strength(results)
    # Same Phase 2+3 join the plain scanner gets via the SCANNERS `enrich` hook —
    # this path bypasses run_scanner, so it has to ask for it explicitly.
    results = _enrich_pead(results)
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
