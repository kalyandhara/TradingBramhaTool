#!/usr/bin/env python3
"""
india_market_intel.py
Bulk deals, block deals, and insider trading (SEBI PIT) for NSE + BSE —
India-only market intelligence, no US SEC EDGAR content (that was scoped
out; see trading-wiki for the reasoning).

Data sources (both confirmed working, no login, whole-market — see
trading-wiki/wiki/sources/BSEIndia-Public-API-Corporate-Data-2026.md and
BSE-NSE-BlockDeal-InsiderTrading-APIs-2026.md for how these were found):
  - BSE: reverse-engineered internal API at api.bseindia.com/BseIndiaAPI/api/
    (undocumented — found by reading BSE's own frontend JS bundle). Needs
    an Origin/Referer header, no cookie/session.
  - NSE: interactive site (www.nseindia.com) is blocked from some
    environments by Akamai; the *static archive* subdomain
    (archives.nseindia.com — same one screener_pipeline.py's bhavcopy
    fetcher uses) is not, and publishes plain CSV files for these reports.

"NEW" flagging: these feeds only return "today's" data with no built-in
history, so "new since last check" is tracked by caching the last-seen row
set to a local JSON file and diffing on each fetch — not a true day-over-day
comparison, just "appeared since the last time this was run".
"""

import json
import logging
from pathlib import Path

import requests
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "tools" / ".india_intel_cache"

BSE_API = "https://api.bseindia.com/BseIndiaAPI/api"
BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.bseindia.com",
    "Referer": "https://www.bseindia.com/",
}

NSE_ARCHIVE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
log = logging.getLogger(__name__)


# ── BSE ─────────────────────────────────────────────────────────────────────

def fetch_bse_bulk_deals() -> pd.DataFrame:
    """Today's bulk deals, whole market. No parameters needed."""
    r = requests.get(f"{BSE_API}/BulkDeal_Beta/w", headers=BSE_HEADERS, timeout=20)
    r.raise_for_status()
    rows = r.json().get("Table", [])
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Exchange"] = "BSE"
    return df


def fetch_bse_block_deals() -> pd.DataFrame:
    """Today's block deals, whole market. No parameters needed."""
    r = requests.get(f"{BSE_API}/BlockDeal_Beta/w", headers=BSE_HEADERS, timeout=20)
    r.raise_for_status()
    rows = r.json().get("Table", [])
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Exchange"] = "BSE"
    return df


def fetch_bse_insider_trading(from_date: str, to_date: str) -> pd.DataFrame:
    """SEBI PIT Regulation 7(2) insider-trading disclosures, whole market.

    Dates in DD/MM/YYYY (BSE's own format). Leaving scripcode blank returns
    every company, not just one.
    """
    params = {"fromdt": from_date, "todt": to_date, "pageno": 1, "scripcode": ""}
    r = requests.get(f"{BSE_API}/InsiderTrade15/w", headers=BSE_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    rows = r.json().get("Table", [])
    return pd.DataFrame(rows)


# ── NSE ─────────────────────────────────────────────────────────────────────

def fetch_nse_bulk_deals() -> pd.DataFrame:
    """Today's bulk deals from NSE's static archive (unauthenticated CSV)."""
    r = requests.get("https://archives.nseindia.com/content/equities/bulk.csv",
                      headers=NSE_ARCHIVE_HEADERS, timeout=20)
    r.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(r.text))
    df.columns = [c.strip() for c in df.columns]
    if not df.empty:
        df["Exchange"] = "NSE"
    return df


def fetch_nse_block_deals() -> pd.DataFrame:
    """Today's block deals from NSE's static archive (unauthenticated CSV)."""
    r = requests.get("https://archives.nseindia.com/content/equities/block.csv",
                      headers=NSE_ARCHIVE_HEADERS, timeout=20)
    r.raise_for_status()
    from io import StringIO
    text = r.text.strip()
    if not text or "NO RECORDS" in text.upper():
        return pd.DataFrame()
    df = pd.read_csv(StringIO(text))
    df.columns = [c.strip() for c in df.columns]
    if not df.empty:
        df["Exchange"] = "NSE"
    return df


# ── "NEW since last check" tracking ──────────────────────────────────────────

def mark_new_rows(df: pd.DataFrame, cache_key: str, key_cols: list[str]) -> pd.DataFrame:
    """Adds a boolean 'New' column: True for rows not seen on the previous
    call with this cache_key, then updates the cache. Not a day-over-day
    diff — these feeds have no history endpoint, so this only catches rows
    that appeared since the last time this function ran for this key.
    """
    if df.empty:
        return df
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{cache_key}.json"

    row_keys = df[key_cols].astype(str).agg("|".join, axis=1)
    try:
        seen = set(json.loads(cache_path.read_text())) if cache_path.exists() else set()
    except Exception:
        seen = set()

    df = df.copy()
    df["New"] = ~row_keys.isin(seen)

    try:
        cache_path.write_text(json.dumps(sorted(set(row_keys))))
    except Exception as e:
        log.warning("Could not write NEW-tracking cache %s: %s", cache_key, e)

    return df
