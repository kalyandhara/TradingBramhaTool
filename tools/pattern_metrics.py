#!/usr/bin/env python3
"""pattern_metrics.py — the "Historical pattern metrics" blocks for one symbol.

Five derived reads over the daily OHLCV the Predictive Analysis page already
holds, so the panel adds no fetch:

  overhead_supply     share of recent bars whose high sits above the current
                      close — a resistance ceiling, or a clear path
  extension           a 0-100 composite of how stretched price is (above the
                      50-day and 20-day means, RSI percentile over two years,
                      5-day run) and an RSI-exhaustion flag
  vcp_coil            base length, depth, contraction count, the contraction
                      ladder and a tightness ratio, from the same pivot-based
                      detector the Chart Tool draws (scanner_templates.detect_vcp_geometry)
  radar               six 0-100 axes — VCP, RS, Stage, Volume, Low risk, Clear
                      path — and their mean, each axis defined in `radar()`
  exceptional_volume  sessions at or above 4× the two-year average volume

Every number is a description of the history; none is a signal, and none has
been measured for forward return here. The wording on the page says so.
Expected frame: lowercase `open`, `high`, `low`, `close`, `volume`.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

OVERHEAD_LOOKBACK = 250       # ~1y of sessions the ceiling is read over
OVERHEAD_CLEAR = 10.0         # % of bars above price: below = clear path
OVERHEAD_HEAVY = 35.0         # above = heavy ceiling
EXT_SMA50_FULL = 25.0         # % above SMA50 that scores 100 on that leg
EXT_EMA20_FULL = 12.0
EXT_RUN5_FULL = 12.0          # 5-day gain that scores 100
RSI_EXHAUST_PCT = 95.0        # RSI percentile (2y) at or above = exhaustion flag
EXC_VOL_MULT = 4.0
EXC_VOL_YEARS = 2


def _ok(df: pd.DataFrame, n: int = 60) -> bool:
    return (df is not None and len(df) >= n
            and {"high", "low", "close", "volume"}.issubset(df.columns))


# ── 1. overhead supply ────────────────────────────────────────────────────────
def overhead_supply(df: pd.DataFrame, lookback: int = OVERHEAD_LOOKBACK) -> dict | None:
    if not _ok(df, 20):
        return None
    w = df.tail(lookback)
    price = float(w["close"].iloc[-1])
    highs = w["high"].to_numpy(dtype=float)[:-1]
    if len(highs) == 0 or not np.isfinite(price):
        return None
    above = int((highs > price).sum())
    pct = above / len(highs) * 100.0
    label = ("Clear path" if pct < OVERHEAD_CLEAR else
             "Light ceiling" if pct < OVERHEAD_HEAVY else "Heavy ceiling")
    note = ("Few recent highs above price — room to run" if pct < OVERHEAD_CLEAR else
            "Some prior highs overhead — supply to absorb" if pct < OVERHEAD_HEAVY else
            "Most of the last year traded above here — heavy supply")
    return {"pct": pct, "bars_above": above, "bars": int(len(highs)),
            "label": label, "note": note}


# ── 2. extension ──────────────────────────────────────────────────────────────
def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def extension(df: pd.DataFrame) -> dict | None:
    if not _ok(df, 60):
        return None
    c = df["close"].astype(float)
    price = float(c.iloc[-1])
    sma50 = float(c.rolling(50).mean().iloc[-1])
    ema20 = float(c.ewm(span=20, adjust=False).mean().iloc[-1])
    run5 = (price / float(c.iloc[-6]) - 1) * 100.0 if len(c) > 6 else 0.0
    rsi = _rsi(c)
    rsi_now = float(rsi.iloc[-1]) if np.isfinite(rsi.iloc[-1]) else None
    hist = rsi.tail(EXC_VOL_YEARS * 250).dropna()
    rsi_pct = float((hist < rsi_now).mean() * 100.0) if rsi_now is not None and len(hist) > 30 else None

    legs = {}
    if np.isfinite(sma50) and sma50 > 0:
        legs["above_sma50_pct"] = (price / sma50 - 1) * 100.0
    if np.isfinite(ema20) and ema20 > 0:
        legs["above_ema20_pct"] = (price / ema20 - 1) * 100.0
    legs["run5_pct"] = run5

    def _n(v, full):                      # 0 at or below zero, 100 at `full`
        return float(np.clip(v / full * 100.0, 0, 100))
    parts = []
    if "above_sma50_pct" in legs:
        parts.append(_n(legs["above_sma50_pct"], EXT_SMA50_FULL))
    if "above_ema20_pct" in legs:
        parts.append(_n(legs["above_ema20_pct"], EXT_EMA20_FULL))
    parts.append(_n(run5, EXT_RUN5_FULL))
    if rsi_pct is not None:
        parts.append(rsi_pct)
    score = float(np.mean(parts)) if parts else None
    band = (None if score is None else
            "Lower band" if score < 33 else "Middle band" if score < 66 else "Upper band")
    exhausted = rsi_pct is not None and rsi_pct >= RSI_EXHAUST_PCT
    return {"score": score, "band": band, "rsi": rsi_now, "rsi_pct": rsi_pct,
            "rsi_exhaustion": bool(exhausted), **legs}


# ── 3. base / VCP coil ────────────────────────────────────────────────────────
def vcp_coil(df: pd.DataFrame) -> dict | None:
    """From detect_vcp_geometry: base length in weeks, depth, contraction count,
    the ladder of depths and tightness = final depth as % of the first (lower is
    tighter). None when the detector abstains."""
    if not _ok(df, 60):
        return None
    try:
        import scanner_templates as sc
        g = sc.detect_vcp_geometry(df)
    except Exception:                                  # noqa: BLE001
        g = None
    if not g or not g.get("contractions"):
        return None
    ladder = [float(x["depth_pct"]) for x in g["contractions"]]
    bars = int(g["base_end_bar_idx"]) - int(g["base_start_bar_idx"]) + 1
    pivot, base_low = float(g["pivot"]), float(g["base_low"])
    depth = (pivot - base_low) / pivot * 100.0 if pivot > 0 else max(ladder)
    tight = ladder[-1] / ladder[0] * 100.0 if ladder[0] > 0 else None
    return {"base_weeks": bars / 5.0, "base_bars": bars, "depth_pct": depth,
            "contractions": len(ladder), "ladder": ladder, "tightness_pct": tight,
            "pivot": pivot, "base_low": base_low,
            "in_progress": bool(g["contractions"][-1].get("in_progress", False))}


# ── 4. radar ──────────────────────────────────────────────────────────────────
def _stage_score(df: pd.DataFrame) -> float:
    c = df["close"].astype(float)
    price = float(c.iloc[-1])
    s50 = float(c.rolling(50).mean().iloc[-1])
    s200 = c.rolling(200).mean()
    if len(c) < 200 or not np.isfinite(s200.iloc[-1]):
        return 50.0
    rising = float(s200.iloc[-1]) > float(s200.iloc[-20])
    if price > s50 > float(s200.iloc[-1]) and rising:
        return 100.0                                    # stage 2, full stack
    if price > float(s200.iloc[-1]):
        return 70.0 if rising else 40.0                 # stage 2 forming / 3
    return 15.0 if rising else 0.0                      # stage 1 / 4


def _rs_score(df: pd.DataFrame, nifty_df: pd.DataFrame | None) -> float | None:
    if nifty_df is None or "close" not in nifty_df.columns or len(df) < 130:
        return None
    n = min(250, len(df) - 1, len(nifty_df) - 1)
    if n < 60:
        return None
    s = float(df["close"].iloc[-1]) / float(df["close"].iloc[-n - 1]) - 1
    b = float(nifty_df["close"].iloc[-1]) / float(nifty_df["close"].iloc[-n - 1]) - 1
    out = (s - b) * 100.0                               # outperformance in pp
    return float(np.clip(50 + out * 1.25, 0, 100))      # +40pp → 100, −40pp → 0


def _volume_score(df: pd.DataFrame, n: int = 60) -> float:
    w = df.tail(n)
    up = w["close"].to_numpy() >= w["open"].to_numpy() if "open" in w.columns else \
        w["close"].to_numpy() >= w["close"].shift(1).bfill().to_numpy()
    v = w["volume"].to_numpy(dtype=float)
    tot = v.sum()
    return float(v[up].sum() / tot * 100.0) if tot > 0 else 50.0


def _risk_score(df: pd.DataFrame) -> float:
    price = float(df["close"].iloc[-1])
    swing_low = float(df["low"].tail(10).min())
    risk_pct = (price - swing_low) / price * 100.0 if price > 0 else 12.0
    return float(np.clip(100 - (risk_pct - 3.0) / 9.0 * 100.0, 0, 100))   # ≤3% → 100, ≥12% → 0


def radar(df: pd.DataFrame, nifty_df: pd.DataFrame | None = None, *,
          vcp: dict | None = None, overhead: dict | None = None) -> dict | None:
    """Six axes, each 0-100:
      VCP        contractions shrinking and tight → 100; no coil → 0
      RS         1y outperformance vs the benchmark, ±40pp → 0/100 (None without benchmark)
      Stage      Weinstein: stage-2 stack rising → 100 … stage 4 → 0
      Volume     share of the last 60 sessions' volume on up bars
      Low risk   distance to the 10-bar swing low: ≤3% → 100, ≥12% → 0
      Clear path 100 − overhead-supply %
    `score` is the mean of the axes that could be computed."""
    if not _ok(df, 60):
        return None
    vcp = vcp if vcp is not None else vcp_coil(df)
    overhead = overhead if overhead is not None else overhead_supply(df)
    if vcp:
        shrink = all(b <= a for a, b in zip(vcp["ladder"], vcp["ladder"][1:]))
        vcp_s = float(np.clip(40 + 20 * vcp["contractions"] + (20 if shrink else 0)
                              - (vcp["tightness_pct"] or 100) * 0.4, 0, 100))
    else:
        vcp_s = 0.0
    axes = {
        "VCP": vcp_s,
        "RS": _rs_score(df, nifty_df),
        "Stage": _stage_score(df),
        "Volume": _volume_score(df),
        "Low risk": _risk_score(df),
        "Clear path": float(100 - overhead["pct"]) if overhead else None,
    }
    vals = [v for v in axes.values() if v is not None]
    return {"axes": axes, "score": float(np.mean(vals)) if vals else None}


# ── 5. exceptional volume ─────────────────────────────────────────────────────
def exceptional_volume(df: pd.DataFrame, mult: float = EXC_VOL_MULT,
                       years: int = EXC_VOL_YEARS) -> dict | None:
    if not _ok(df, 60):
        return None
    w = df.tail(years * 250)
    v = w["volume"].astype(float)
    avg = float(v.mean())
    if not np.isfinite(avg) or avg <= 0:
        return None
    thr = avg * mult
    hits = w[v >= thr]
    sessions = [{"date": pd.Timestamp(i).date().isoformat(), "volume": float(r["volume"]),
                 "ratio": float(r["volume"]) / avg,
                 "chg_pct": (float(r["close"]) / float(r["open"]) - 1) * 100.0 if "open" in w.columns and float(r["open"]) > 0 else None}
                for i, r in hits.iterrows()]
    sessions.sort(key=lambda s: s["ratio"], reverse=True)
    return {"avg_volume": avg, "threshold": thr, "mult": mult, "count": len(sessions),
            "sessions": sessions, "n_sessions": int(len(w)),
            "from": pd.Timestamp(w.index[0]).date().isoformat(),
            "to": pd.Timestamp(w.index[-1]).date().isoformat()}


def compute_all(df: pd.DataFrame, nifty_df: pd.DataFrame | None = None) -> dict[str, Any]:
    d = df.dropna(subset=[c for c in ("open", "high", "low", "close", "volume") if c in df.columns]) \
        if df is not None else df
    oh = overhead_supply(d)
    vc = vcp_coil(d)
    return {"overhead": oh, "extension": extension(d), "vcp": vc,
            "radar": radar(d, nifty_df, vcp=vc, overhead=oh),
            "exceptional_volume": exceptional_volume(d)}
