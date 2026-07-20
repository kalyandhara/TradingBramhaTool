#!/usr/bin/env python3
"""
sentiment_index.py — Market Sentiment Index (Phase 1, 4 home-data inputs).

Composite 0-100 gauge for NIFTY-wide sentiment, mapped to 5 bands. See
`trading-wiki/wiki/concepts/Market-Sentiment-Index.md` and the roadmap analysis
at `wiki/analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14.md`.

Phase 1 inputs (Raut-style but with disclosed technical replacements):
  1. Advance / Decline ratio          (weight 30, bhavcopy)
  2. Sector performance count         (weight 25, distinct NIFTY sector indices)
  3. NIFTY vs SMA200 regime           (weight 25, yfinance ^NSEI daily)
  4. PMax direction on NIFTY 1H       (weight 20, ATR-trailing band on ^NSEI 60m)
  ──────────────────────────────────────────────────
                                       total   100

Phase 2 (deferred, tracked in the roadmap page):
  5. PCR + PCR-slope on NIFTY options (weight ~20; requires NSE option-chain
     scraper). When added, other weights re-normalise.

Bands (matches the reference infographic):
    0-20   Strong Sell
   20-40   Sell
   40-55   Neutral
   55-80   Buy
   80-100  Strong Buy

Public API:
  compute_sentiment(persist=True) -> dict
  history(days=90)               -> pd.DataFrame

CLI:
  python sentiment_index.py           # compute + print + persist
  python sentiment_index.py --peek    # compute + print (no persist)
"""
from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio_db as db
import screener_pipeline as sp
import sector_rotation as secrot

try:
    import yfinance as yf
except ImportError:
    sys.exit("Run:  py -3 -m pip install yfinance")

log = logging.getLogger("sentiment_index")

# ── Weights (Phase 1) ─────────────────────────────────────────────────────────
W_ADV_DECL = 30
W_SECTOR   = 25
W_REGIME   = 25
W_PMAX_1H  = 20
W_TOTAL    = W_ADV_DECL + W_SECTOR + W_REGIME + W_PMAX_1H  # 100

# ── Band mapping (score → label) ──────────────────────────────────────────────
BANDS = [
    (0,   20,  "Strong Sell"),
    (20,  40,  "Sell"),
    (40,  55,  "Neutral"),
    (55,  80,  "Buy"),
    (80, 101,  "Strong Buy"),
]


def _band_for(score: float) -> str:
    for lo, hi, label in BANDS:
        if lo <= score < hi:
            return label
    return "Neutral"


# ── DB persistence ────────────────────────────────────────────────────────────
def _ensure_table() -> None:
    with db.get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sentiment_history (
                reading_date TEXT PRIMARY KEY,
                score        REAL NOT NULL,
                band         TEXT NOT NULL,
                inputs_json  TEXT NOT NULL,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _persist(reading: dict[str, Any]) -> None:
    _ensure_table()
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sentiment_history (reading_date, score, band, inputs_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(reading_date) DO UPDATE SET
                score = excluded.score,
                band  = excluded.band,
                inputs_json = excluded.inputs_json
            """,
            (reading["reading_date"], reading["score"], reading["band"],
             json.dumps(reading["inputs"], default=float)),
        )


def history(days: int = 90) -> pd.DataFrame:
    """Return the last `days` calendar days of persisted sentiment readings."""
    _ensure_table()
    with db.get_connection() as conn:
        df = pd.read_sql(
            "SELECT reading_date, score, band, inputs_json "
            "FROM sentiment_history ORDER BY reading_date DESC LIMIT ?",
            conn, params=(days,),
        )
    if not df.empty:
        df["reading_date"] = pd.to_datetime(df["reading_date"])
        df = df.sort_values("reading_date").reset_index(drop=True)
    return df


# ── Input #1: Advance / Decline from bhavcopy ────────────────────────────────
def _advance_decline() -> dict[str, Any]:
    """Compute advance/decline ratio from most recent NSE bhavcopy. Returns a
    dict with raw counts, factor ∈ [0, 1], and a score contribution."""
    import requests
    from datetime import timedelta

    session = requests.Session()
    try:
        session.get("https://www.nseindia.com/", headers=sp.NSE_HEADERS, timeout=15)
    except Exception:
        pass

    df = None
    for days_back in range(1, 6):
        cand = datetime.today() - timedelta(days=days_back)
        if cand.weekday() >= 5:
            continue
        df = sp._fetch_bhav_df(session, cand)
        if df is not None:
            break
    if df is None:
        log.warning("A/D: no bhavcopy available")
        return {"reading": "n/a", "factor": 0.5, "score": 0.5 * W_ADV_DECL,
                "advances": 0, "declines": 0, "unchanged": 0}

    df.columns = [c.strip().upper() for c in df.columns]
    ser_col   = next((c for c in df.columns if c in ("SERIES", "SCTYSRS")), None)
    close_col = next((c for c in df.columns if c in ("CLOSE", "CLSPRIC")), None)
    prev_col  = next((c for c in df.columns
                      if c in ("PREVCLOSE", "PREV_CLOSE", "PRVSCLSGPRIC")), None)
    if not (close_col and prev_col):
        log.warning("A/D: bhavcopy missing close/prev columns (%s)", list(df.columns)[:20])
        return {"reading": "n/a", "factor": 0.5, "score": 0.5 * W_ADV_DECL,
                "advances": 0, "declines": 0, "unchanged": 0}

    if ser_col:
        df = df[df[ser_col].astype(str).str.strip() == "EQ"]
    df = df[[close_col, prev_col]].apply(pd.to_numeric, errors="coerce").dropna()
    df = df[df[prev_col] > 0]

    advances  = int((df[close_col] > df[prev_col]).sum())
    declines  = int((df[close_col] < df[prev_col]).sum())
    unchanged = int((df[close_col] == df[prev_col]).sum())
    total = advances + declines
    # Ratio in [0, 1]: 1.0 = every stock up, 0.5 = balanced, 0.0 = every stock down.
    factor = 0.5 if total == 0 else advances / total
    return {
        "reading": f"{advances} Adv vs {declines} Decl",
        "factor": round(factor, 4),
        "score":  round(factor * W_ADV_DECL, 2),
        "advances": advances, "declines": declines, "unchanged": unchanged,
    }


# ── Input #2: Sector performance (green vs red count) ────────────────────────
def _sector_perf() -> dict[str, Any]:
    """Fetch 1-day change for every distinct NIFTY sector index in
    sector_rotation's SECTOR_INDEX_MAP. Factor = (green + 0.5*flat) / total."""
    tickers = sorted(set(secrot.SECTOR_INDEX_MAP.values()))
    greens, reds, flats = 0, 0, 0
    details: list[dict[str, Any]] = []
    for tkr in tickers:
        try:
            hist = yf.Ticker(tkr).history(period="10d", interval="1d", auto_adjust=False)
            if hist is None:
                continue
            # Drop rows with NaN close — yfinance sometimes returns a stub row for
            # today with all-NaN values before session data is finalised.
            hist = hist.dropna(subset=["Close"])
            if len(hist) < 2:
                continue
            prev, last = float(hist["Close"].iloc[-2]), float(hist["Close"].iloc[-1])
            chg_pct = (last / prev - 1) * 100 if prev > 0 else 0.0
            if chg_pct > 0.05:  flat = False; greens += 1; color = "green"
            elif chg_pct < -0.05: flat = False; reds += 1;  color = "red"
            else:                 flat = True;  flats += 1;  color = "flat"
            details.append({"ticker": tkr, "chg_pct": round(chg_pct, 2), "color": color})
        except Exception as e:
            log.debug("Sector %s fetch failed: %s", tkr, e)
    total = greens + reds + flats
    factor = 0.5 if total == 0 else (greens + 0.5 * flats) / total
    return {
        "reading": f"{greens} Green / {reds} Red / {flats} Flat  ({total} sector indices)",
        "factor": round(factor, 4),
        "score":  round(factor * W_SECTOR, 2),
        "greens": greens, "reds": reds, "flats": flats,
        "details": details,
    }


# ── Input #3: NIFTY vs SMA200 (regime gauge) ─────────────────────────────────
def _regime_sma200() -> dict[str, Any]:
    """NIFTY close vs its 200-DMA. Factor centred on 1.0: at SMA=0.5, 5% above=1.0,
    5% below=0.0, linearly interpolated in between and clipped."""
    try:
        hist = yf.Ticker("^NSEI").history(period="14mo", interval="1d", auto_adjust=False)
        if hist is None:
            raise RuntimeError("no NIFTY history")
        # yfinance occasionally returns an all-NaN stub for today's incomplete
        # session — drop it so SMA200 doesn't inherit the NaN.
        hist = hist.dropna(subset=["Close"])
        if len(hist) < 210:
            raise RuntimeError("insufficient NIFTY history")
        close = hist["Close"].astype(float)
        sma200 = close.rolling(200).mean()
        last_close = float(close.iloc[-1])
        last_sma   = float(sma200.iloc[-1])
        if not np.isfinite(last_sma) or last_sma <= 0:
            raise RuntimeError("SMA200 unavailable")
        dist_pct = (last_close / last_sma - 1) * 100
        # Map ±5% distance → factor in [0, 1] centred at 0.5.
        factor = np.clip(0.5 + dist_pct / 10.0, 0.0, 1.0)
        return {
            "reading": (f"NIFTY {last_close:,.0f} vs SMA200 {last_sma:,.0f} "
                        f"({dist_pct:+.2f}%)"),
            "factor": round(float(factor), 4),
            "score":  round(float(factor) * W_REGIME, 2),
            "close": round(last_close, 2), "sma200": round(last_sma, 2),
            "dist_pct": round(dist_pct, 2),
        }
    except Exception as e:
        log.warning("Regime: %s", e)
        return {"reading": "n/a", "factor": 0.5, "score": 0.5 * W_REGIME,
                "close": None, "sma200": None, "dist_pct": None}


# ── Input #4: PMax direction on NIFTY 1H ─────────────────────────────────────
def _pmax_direction_nifty_1h(atr_len: int = 10, atr_mult: float = 3.0,
                              ma_len: int = 10) -> dict[str, Any]:
    """Port of the PMax logic used by the chart tool (tools/pmax.pine +
    the JS `pmaxSeries` in chart_dashboard.html) applied to NIFTY 1H.
    Factor = 1.0 if PMax dir is up (bullish trend), 0.0 if down. When we have
    a fresh flip we can weight it more, but for Phase 1 the binary is fine."""
    try:
        hist = yf.Ticker("^NSEI").history(period="60d", interval="1h", auto_adjust=False)
        if hist is None:
            raise RuntimeError("no NIFTY 1h history")
        hist = hist.dropna(subset=["Close"])
        if len(hist) < 40:
            raise RuntimeError("insufficient NIFTY 1h history")
        high = hist["High"].astype(float).values
        low  = hist["Low"].astype(float).values
        close = hist["Close"].astype(float).values
        n = len(close)

        # Wilder ATR
        tr = np.zeros(n)
        tr[0] = high[0] - low[0]
        for i in range(1, n):
            tr[i] = max(high[i] - low[i],
                        abs(high[i] - close[i - 1]),
                        abs(low[i]  - close[i - 1]))
        atr = np.zeros(n)
        atr[atr_len - 1] = tr[:atr_len].mean()
        for i in range(atr_len, n):
            atr[i] = (atr[i - 1] * (atr_len - 1) + tr[i]) / atr_len

        # EMA of hl2
        src = (high + low) / 2
        alpha = 2 / (ma_len + 1)
        ema = np.zeros(n)
        ema[0] = src[0]
        for i in range(1, n):
            ema[i] = alpha * src[i] + (1 - alpha) * ema[i - 1]

        long_prev = short_prev = None
        direction = 1
        # Warm-up to the max of atr_len / ma_len
        warm = max(atr_len, ma_len)
        for i in range(warm, n):
            a = atr[i]
            long_stop  = ema[i] - atr_mult * a
            short_stop = ema[i] + atr_mult * a
            if long_prev is not None and ema[i] > long_prev:
                long_stop = max(long_stop, long_prev)
            if short_prev is not None and ema[i] < short_prev:
                short_stop = min(short_stop, short_prev)
            if direction == -1 and ema[i] > (short_prev if short_prev is not None else short_stop):
                direction = 1
            elif direction == 1 and ema[i] < (long_prev if long_prev is not None else long_stop):
                direction = -1
            long_prev, short_prev = long_stop, short_stop

        factor = 1.0 if direction == 1 else 0.0
        pmax_val = long_prev if direction == 1 else short_prev
        return {
            "reading": ("Bullish (PMax up)" if direction == 1
                        else "Bearish (PMax down)"),
            "factor": factor,
            "score":  factor * W_PMAX_1H,
            "direction": int(direction),
            "last_close": round(float(close[-1]), 2),
            "pmax": round(float(pmax_val), 2) if pmax_val is not None else None,
        }
    except Exception as e:
        log.warning("PMax 1H: %s", e)
        return {"reading": "n/a", "factor": 0.5, "score": 0.5 * W_PMAX_1H,
                "direction": 0, "last_close": None, "pmax": None}


# ── Composite ─────────────────────────────────────────────────────────────────
def compute_sentiment(persist: bool = True) -> dict[str, Any]:
    """Compute the composite sentiment reading and (by default) persist it to
    trading_bramha.db under `sentiment_history`. Idempotent per calendar day —
    same-day recomputes overwrite the previous row."""
    ad      = _advance_decline()
    sector  = _sector_perf()
    regime  = _regime_sma200()
    pmax_1h = _pmax_direction_nifty_1h()

    score = round(ad["score"] + sector["score"] + regime["score"] + pmax_1h["score"], 2)
    band  = _band_for(score)

    reading = {
        "reading_date": date.today().isoformat(),
        "score": score,
        "band":  band,
        "inputs": {
            "advance_decline":  {"weight": W_ADV_DECL, **ad},
            "sector_performance": {"weight": W_SECTOR, **sector},
            "regime_sma200":    {"weight": W_REGIME, **regime},
            "pmax_nifty_1h":    {"weight": W_PMAX_1H, **pmax_1h},
        },
    }
    if persist:
        try:
            _persist(reading)
        except Exception as e:
            log.warning("persist failed: %s", e)
    return reading


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
                        datefmt="%H:%M:%S")
    persist = "--peek" not in sys.argv
    r = compute_sentiment(persist=persist)
    print(json.dumps(r, indent=2, default=float))
