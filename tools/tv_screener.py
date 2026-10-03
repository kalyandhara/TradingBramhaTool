"""
tv_screener.py — TradingView screener via the public scan endpoint.

Uses the `tradingview-screener` package (pip install tradingview-screener),
which wraps https://scanner.tradingview.com/india/scan — no login needed for
public columns. Filters below replicate the saved screener
"BrkoutGeek: Horz Break copy" (uPUJdiD5).

If the package isn't installed the module falls back to a direct requests call
against the same endpoint so the dashboard still functions.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import requests

log = logging.getLogger(__name__)

TV_SCAN_URL = "https://scanner.tradingview.com/india/scan"


def _direct_scan_payload(min_chg: float, min_rel_vol: float,
                         min_price_vol_inr: float) -> dict[str, Any]:
    """Raw JSON payload for the /scan endpoint. Column names come from TV's
    public schema — Volume*close is TV's proxy for turnover."""
    return {
        "filter": [
            {"left": "exchange", "operation": "equal", "right": "NSE"},
            {"left": "change", "operation": "egreater", "right": min_chg},
            {"left": "relative_volume_10d_calc", "operation": "egreater",
             "right": min_rel_vol},
            {"left": "High.1M", "operation": "eless", "right": "high"},
            # Turnover proxy: today's volume × close
            {"left": "Value.Traded", "operation": "egreater",
             "right": min_price_vol_inr},
        ],
        "options": {"lang": "en"},
        "markets": ["india"],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": [
            "name", "description", "close", "change", "change_from_open",
            "volume", "relative_volume_10d_calc", "Value.Traded",
            "market_cap_basic", "sector", "industry", "High.1M", "Low.1M",
        ],
        "sort": {"sortBy": "change", "sortOrder": "asc"},
        "range": [0, 150],
    }


def fetch_brkoutgeek(min_chg: float = 2.0,
                     min_rel_vol: float = 1.5,
                     min_price_vol_inr: float = 10_000_000.0,
                     raise_on_error: bool = False) -> pd.DataFrame:
    """Replicates the BrkoutGeek: Horz Break copy screener.

    An empty frame means "no matches" OR "TradingView unreachable"; callers that
    must tell them apart (the snapshot job) pass raise_on_error=True.
    """
    try:
        r = requests.post(
            TV_SCAN_URL,
            json=_direct_scan_payload(min_chg, min_rel_vol, min_price_vol_inr),
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("TV scan failed: %s", e)
        if raise_on_error:
            raise RuntimeError(f"TradingView scan unreachable: {e}") from e
        return pd.DataFrame()

    rows = data.get("data", []) or []
    if not rows:
        return pd.DataFrame()

    cols = _direct_scan_payload(min_chg, min_rel_vol, min_price_vol_inr)["columns"]
    records = []
    for row in rows:
        vals = row.get("d") or []
        rec = dict(zip(cols, vals))
        rec["symbol"] = (row.get("s") or "").split(":")[-1]
        records.append(rec)

    df = pd.DataFrame(records)
    # Human-friendly renames
    df = df.rename(columns={
        "name": "Symbol",
        "description": "Company",
        "close": "Price",
        "change": "Chg %",
        "change_from_open": "Chg from Open %",
        "volume": "Volume",
        "relative_volume_10d_calc": "Rel Vol",
        "Value.Traded": "Turnover ₹",
        "market_cap_basic": "Mkt Cap ₹",
        "sector": "Sector",
        "industry": "Industry",
        "High.1M": "1M High",
        "Low.1M": "1M Low",
    })
    # Round for display
    for c in ["Price", "Chg %", "Chg from Open %", "Rel Vol"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").round(2)
    for c in ["Turnover ₹", "Mkt Cap ₹", "Volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").round(0)
    # Chart link (reuses local chart_server on :5001)
    if "Symbol" in df.columns:
        df["Chart"] = df["Symbol"].apply(
            lambda s: f"http://localhost:5001/?symbol={s}&exchange=NSE&tf=1d"
        )
    return df.sort_values("Chg %", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = fetch_brkoutgeek()
    if df.empty:
        print("No hits (market closed or filter too tight).")
    else:
        print(df[["Symbol", "Chg %", "Rel Vol", "Turnover ₹",
                  "Industry"]].to_string(index=False))
        print(f"\n{len(df)} hits")
