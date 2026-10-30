#!/usr/bin/env python3
"""crt_weekly.py — weekly Candle Range Theory (CRT) events from daily bars (B-165).

Candle Range Theory reads a candle's range as liquidity: candle 2 trades beyond
candle 1's extreme, closes back INSIDE candle 1's range, and the stops it took
are expected to fuel a move the other way. On the weekly candle the bullish case
is: this week trades below last week's low and closes back inside last week's
range. That is a liquidity sweep with the prior candle's low as the pool, which is
why B-165 asks first whether it is anything the `Liquidity Sweep` scanner does not
already see (see analyses/Weekly-CRT-Sweep-Overlap).

Definition (fixed in the B-165 pre-registration):
  * calendar weeks ending Friday, completed weeks only;
  * low[t] < low[t-1]  and  low[t-1] < close[t] < high[t-1];
  * outside weeks (high[t] > high[t-1]) excluded: both sides swept is not a
    directional sweep;
  * no pierce-size floor; the pierce in ATR is reported, never filtered on.

Detector only. Nothing here is registered as a scanner, votes, or scores:
it has not been measured.
"""
from __future__ import annotations

import pandas as pd


def weekly_bars(df: pd.DataFrame, drop_last_partial: bool = True) -> pd.DataFrame:
    """Calendar weeks ending Friday from daily bars that carry a ``date`` column
    or a DatetimeIndex. Adds ``start`` / ``end`` (first / last trading day) and
    ``n_days``. The final week is dropped when it ends before its Friday."""
    d = df.copy()
    idx = pd.to_datetime(d["date"]) if "date" in d.columns else pd.to_datetime(d.index)
    d.index = pd.DatetimeIndex(idx).tz_localize(None).normalize()
    d["_day"] = d.index
    g = d.groupby(pd.Grouper(freq="W-FRI"))
    w = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
        "close": g["close"].last(), "start": g["_day"].min(), "end": g["_day"].max(),
        "n_days": g["close"].count(),
    }).dropna(subset=["close"])
    if drop_last_partial and len(w):
        week_end = w.index[-1]                      # the Friday label of the last week
        if w["end"].iloc[-1] < week_end:
            w = w.iloc[:-1]
    return w


def bullish_events(df: pd.DataFrame, atr_daily: pd.Series | None = None) -> list[dict]:
    """Bullish weekly CRT events, oldest first. Each: ``week`` (Friday label),
    ``start``/``end`` (trading days of candle 2), ``c1_low``/``c1_high``,
    ``low``/``close`` of candle 2, and ``pierce_atr`` when a daily ATR is given."""
    w = weekly_bars(df)
    out = []
    for i in range(1, len(w)):
        c1, c2 = w.iloc[i - 1], w.iloc[i]
        if not (c2["low"] < c1["low"] and c1["low"] < c2["close"] < c1["high"]
                and c2["high"] <= c1["high"]):
            continue
        ev = {"week": w.index[i], "start": c2["start"], "end": c2["end"],
              "c1_low": float(c1["low"]), "c1_high": float(c1["high"]),
              "low": float(c2["low"]), "close": float(c2["close"]), "pierce_atr": None}
        if atr_daily is not None:
            a = atr_daily.loc[:c1["end"]]
            if len(a) and a.iloc[-1] > 0:
                ev["pierce_atr"] = round((c1["low"] - c2["low"]) / float(a.iloc[-1]), 3)
        out.append(ev)
    return out
