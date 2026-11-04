#!/usr/bin/env python3
"""smc_state.py — SMC state columns for a symbol table (B-42r Option C).

The desk computes market structure, premium/discount and liquidity pools, and the
Watchlist showed none of it. These are DESCRIPTIONS OF STATE, not signals:
structure state was measured at no edge (CHoCH), and nothing here votes, scores or
filters. They exist so a reader can see what the SMC scanners and the chart see.

── Two structure definitions, ONE reading (owner decision B-42r, 2026-10-15) ──
pivot_len 5 is **short-term structure** (every SMC scanner); 15 is **swing
structure** (the chart's Structure Break Chain, `read_market_structure`'s
default). They agree on state only 29.6% of the time and read opposite on 17.6%
of names, so they are NOT printed as two peer columns. Following B-96/B-97, the
split itself is the reading: one cell, e.g. ``ST ▲ · SW ▼ — opposite``.

Which definition each other column uses, and why:
  * premium/discount — **swing (15)**: P/D is a location inside the swing band.
  * liquidity pools and the recent sweep — **short-term (5)**: the definition
    B-41m measured the Liquidity Sweep edge on, so the column describes the same
    pools the scanner fires on.

Pure: daily bars in, a dict out. The scanner_templates detectors are called, not
re-implemented.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

SHORT_TERM = 5      # B-42r: "short-term structure" — the SMC scanners
SWING = 15          # B-42r: "swing structure" — chart + read_market_structure
SWEPT_WITHIN = 5    # sessions for the "swept recently" flag

ARROW = {"UPTREND": "▲", "DOWNTREND": "▼", "RANGE": "↔", "BROADENING": "⇕",
         "TRANSITION": "~", "UNKNOWN": "?"}


def agreement(st: str | None, sw: str | None) -> str:
    """``agree`` (same state), ``opposite`` (one up, one down) or ``split``."""
    st, sw = st or "UNKNOWN", sw or "UNKNOWN"
    if "UNKNOWN" in (st, sw):
        return "unknown"
    if st == sw:
        return "agree"
    if {st, sw} == {"UPTREND", "DOWNTREND"}:
        return "opposite"
    return "split"


def structure_cell(st: str | None, sw: str | None) -> str:
    st, sw = st or "UNKNOWN", sw or "UNKNOWN"
    return f"ST {ARROW.get(st, '?')} · SW {ARROW.get(sw, '?')} — {agreement(st, sw)}"


def pd_cell(ms_swing: dict | None) -> str:
    if not ms_swing or ms_swing.get("zone") is None or ms_swing.get("zone_pct") is None:
        return ""
    pct = float(ms_swing["zone_pct"])
    # Outside the band is not "very premium": price has left the last swing range,
    # and a percentage like 579% would read as a measurement rather than an exit.
    if pct > 100:
        return "ABOVE swing high"
    if pct < 0:
        return "BELOW swing low"
    short = {"PREMIUM": "PREM", "DISCOUNT": "DISC", "EQUILIBRIUM": "EQ"}
    return f"{short.get(ms_swing['zone'], ms_swing['zone'])} {pct:.0f}%"


def nearest_untouched_pools(df: pd.DataFrame, pools: list[dict]
                            ) -> tuple[float | None, float | None]:
    """Nearest equal-lows pool below the close and equal-highs pool above it that
    price has NOT traded through since the pool's last touch. A pool already
    pierced is spent liquidity; reporting it as resting would point at stops
    that have been taken."""
    low, high = df["low"].to_numpy(float), df["high"].to_numpy(float)
    last = float(df["close"].iloc[-1])
    ssl = bsl = None
    for p in pools:
        after = slice(int(p["last_bar"]) + 1, len(df))
        lvl = float(p["level"])
        if p["kind"] == "low" and lvl < last:
            if low[after].size and low[after].min() < lvl:
                continue
            ssl = lvl if ssl is None else max(ssl, lvl)
        elif p["kind"] == "high" and lvl > last:
            if high[after].size and high[after].max() > lvl:
                continue
            bsl = lvl if bsl is None else min(bsl, lvl)
    return ssl, bsl


def row(df: pd.DataFrame) -> dict[str, Any]:
    """The SMC columns for one symbol. Missing history -> blanks, never a guess."""
    import scanner_templates as sc

    out: dict[str, Any] = {"smc_structure": "", "pd_swing": "",
                           "ssl_atr": None, "bsl_atr": None, "swept_recent": ""}
    if df is None or len(df) < SWING * 2 + 25:
        return out
    d = sc._clean_ohlc(df)
    ms_st = sc.read_market_structure(d, pivot_len=SHORT_TERM)
    ms_sw = sc.read_market_structure(d, pivot_len=SWING)
    out["smc_structure"] = structure_cell(ms_st and ms_st.get("state"),
                                          ms_sw and ms_sw.get("state"))
    out["pd_swing"] = pd_cell(ms_sw)

    atr = float(sc._atr_series(d, 14).iloc[-1])
    last = float(d["close"].iloc[-1])
    pools = sc.detect_liquidity_pools(d, pivot_len=SHORT_TERM)
    ssl, bsl = nearest_untouched_pools(d, pools)
    if atr > 0:
        out["ssl_atr"] = round((last - ssl) / atr, 2) if ssl is not None else None
        out["bsl_atr"] = round((bsl - last) / atr, 2) if bsl is not None else None

    ev = sc.detect_liquidity_sweep(d, pivot_len=SHORT_TERM)
    if ev and ev.get("bars_ago") is not None and ev["bars_ago"] < SWEPT_WITHIN:
        side = "SSL" if ev["direction"] == "bullish" else "BSL"
        out["swept_recent"] = f"{side} {ev['bars_ago']}d ago" if ev["bars_ago"] else f"{side} today"
    return out
