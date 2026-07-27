#!/usr/bin/env python3
"""
opportunity_hub.py — top-down Sector → Industry → Stock funnel (Phase 1).

The "Opportunity Hub" answers "Right Sector → Right Industry → Right Stock →
Right Pattern → Right Entry" as one connected flow, instead of a bottom-up
pattern scan over a flat universe. Phase 1 is pure composition — no new detectors:

  1. Score each stock's momentum (IBD-style weighted trailing return, reused from
     scanner_templates) and tag its sector / industry (yfinance .info, login-free,
     sharing the quality-gate's cached fetch).
  2. Rank SECTORS and INDUSTRIES bottom-up by their constituents' aggregate
     strength — leadership is derived from the very names we'll trade, in one
     consistent taxonomy (no index→constituents reconciliation needed).
  3. The dashboard then drills into the leading sectors/industries and runs the
     EXISTING Scanner Hub scanners on just those stocks (pattern + entry).

See wiki/analyses/Opportunity-Hub-Roadmap.md.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

import scanner_templates as sc


def _close(df) -> pd.Series | None:
    """Closing-price series with NaN bars dropped. yfinance occasionally returns a
    trailing NaN bar (holiday / incomplete session); _weighted_trailing_return
    anchors on the LAST close, so a NaN there yields a NaN momentum that then
    poisons the group ranking — drop them up front, same discipline as scan_pead."""
    if df is None or getattr(df, "empty", True):
        return None
    col = "close" if "close" in df.columns else ("Close" if "Close" in df.columns else None)
    if not col:
        return None
    c = df[col].dropna()
    return c if len(c) else None


def stock_strength(df) -> float | None:
    """Per-stock momentum = IBD-style weighted trailing return (reuses the scanner
    engine's own RS primitive so the funnel and the scanners agree on 'strength')."""
    c = _close(df)
    if c is None or len(c) < 30:
        return None
    try:
        v = sc._weighted_trailing_return(c)
    except Exception:
        return None
    if v is None or pd.isna(v):
        return None
    return round(float(v), 2)


def _one_constituent(sym: str, fetch_ohlcv) -> dict | None:
    """Tag + strength for a single symbol (the unit of work parallelised below)."""
    try:
        f = sc.fetch_fundamentals_yf(sym) or {}
    except Exception:
        f = {}
    sector = f.get("sector")
    try:
        df = fetch_ohlcv(sym)
    except Exception:
        df = None
    mom = stock_strength(df)
    if sector is None or mom is None:
        return None                        # need a sector AND a strength to place it
    c = _close(df)
    return {
        "symbol": sym,
        "sector": sector,
        "industry": f.get("industry") or "—",
        "momentum": mom,
        "last": round(float(c.iloc[-1]), 2) if c is not None else None,
        "roe_pct": f.get("roe_pct"),
        "opm_pct": f.get("opm_pct"),
        "pe": f.get("pe"),
        "market_cap_cr": f.get("market_cap_cr"),
    }


def build_constituent_table(symbols: list[str], fetch_ohlcv,
                            *, progress_cb=None, max_workers: int = 8) -> pd.DataFrame:
    """One row per stock that has BOTH a sector tag and a computable momentum:
    symbol · sector · industry · momentum · last · (roe/opm/pe/mcap for display).

    The per-symbol yfinance `.info` (sector tag) + OHLCV fetches are network-bound,
    so they run across a THREAD POOL (`max_workers`) — the funnel's build over a
    few-hundred-name universe drops from minutes (sequential) to tens of seconds.
    Both fetches are cached (scanner_templates' `.info` cache + the caller's OHLCV
    cache), so a re-run and the subsequent scanner pass reuse the work."""
    rows: list[dict] = []
    total = len(symbols)
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_one_constituent, s, fetch_ohlcv) for s in symbols]
        for fut in as_completed(futures):
            done += 1
            if progress_cb is not None:
                try:
                    progress_cb(done, total)
                except Exception:
                    pass
            try:
                r = fut.result()
            except Exception:
                r = None
            if r:
                rows.append(r)
    return pd.DataFrame(rows)


def rank_groups(stock_df: pd.DataFrame, group_col: str,
                *, min_constituents: int = 3) -> pd.DataFrame:
    """Rank sectors or industries by aggregate constituent strength.

    strength = mean constituent momentum; also reports median, breadth (% of
    constituents with positive momentum), constituent count, and the strongest
    name. Groups with fewer than `min_constituents` members are dropped — a
    one-stock 'sector' is not a leadership signal.
    """
    if stock_df is None or stock_df.empty or group_col not in stock_df.columns:
        return pd.DataFrame()
    out = []
    for name, g in stock_df.groupby(group_col):
        g = g[g["momentum"].notna()]
        if len(g) < min_constituents:
            continue
        breadth = float((g["momentum"] > 0).mean() * 100.0)
        leader = g.loc[g["momentum"].idxmax()]
        out.append({
            group_col: name,
            "avg_momentum": round(float(g["momentum"].mean()), 2),
            "median_momentum": round(float(g["momentum"].median()), 2),
            "breadth_pct": round(breadth, 0),
            "count": int(len(g)),
            "leader": f'{leader["symbol"]} ({leader["momentum"]:+.0f}%)',
        })
    df = pd.DataFrame(out)
    if df.empty:
        return df
    return df.sort_values("avg_momentum", ascending=False).reset_index(drop=True)


def stocks_in_groups(stock_df: pd.DataFrame, group_col: str,
                     names: list[str]) -> list[str]:
    """Constituent symbols belonging to the chosen sectors/industries, strongest
    first — this is the narrowed list the pattern scanner then runs on."""
    if stock_df is None or stock_df.empty or not names:
        return []
    sel = stock_df[stock_df[group_col].isin(names)].sort_values(
        "momentum", ascending=False)
    return sel["symbol"].tolist()
