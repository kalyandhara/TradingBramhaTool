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


def scan_darvas_box(df: pd.DataFrame) -> dict | None:
    """20-day Darvas box: tight consolidation with price in upper half or breaking out."""
    if len(df) < 60:
        return None
    recent = df.tail(20)
    box_high = float(recent["high"].max())
    box_low = float(recent["low"].min())
    if box_low <= 0 or box_high == box_low:
        return None
    box_height = (box_high - box_low) / box_low * 100
    last = float(df["close"].iloc[-1])
    if box_height > 15 or last < box_low:
        return None
    pct_in_box = (last - box_low) / (box_high - box_low) * 100
    if pct_in_box < 60:
        return None
    sma150 = _sma(df["close"], 150)
    if not np.isnan(sma150) and last < sma150 * 0.95:
        return None
    status = "Fresh breakout" if last >= box_high * 0.99 else "Inside box (upper)"
    reasons = [
        f"{status} — {box_height:.1f}% box height (tight consolidation)",
        f"Price at {pct_in_box:.0f}% of box range",
    ]
    if status == "Fresh breakout":
        vol_last = float(df["volume"].iloc[-1])
        vol_avg = float(df["volume"].tail(20).mean())
        if vol_last > vol_avg:
            reasons.append(f"Breakout volume {vol_last / vol_avg:.1f}× average — confirmed")
    return {
        "pattern_type": status,
        "tags": [f"{box_height:.1f}% box", "Darvas"],
        "reasons": reasons,
        "score": round(pct_in_box / 10 + (15 - box_height), 2),
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
        "description": "Tight 20-day consolidation — fresh breakouts and near-breakouts",
        "category": "Pattern",
    },
    "Momentum Continuation": {
        "fn": scan_momentum_continuation,
        "description": "Strong uptrends near 20-day highs with intact MA stack",
        "category": "Momentum",
    },
    "VCP Coiling": {
        "fn": scan_vcp,
        "description": "Volatility contraction pattern with drying volume — coiling before move",
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
}


def run_scanner(scanner_name: str, symbols: list[str], fetch_fn) -> list[dict]:
    """Run scanner_name over symbols. Returns result cards sorted by score."""
    spec = SCANNERS.get(scanner_name)
    if spec is None:
        return []
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
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
