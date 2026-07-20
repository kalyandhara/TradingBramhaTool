#!/usr/bin/env python3
"""
chartink_scraper.py
Fetch screener results from chartink.com using its internal JSON API.

Chartink uses a Rails CSRF token + session cookie pair.  The flow is:
  1. GET https://chartink.com/screener/  →  parse <meta name="csrf-token">
  2. POST https://chartink.com/screener/process
        with form-data  scan_clause=<condition string>
        and headers     X-CSRF-Token: <token>
                        Cookie: _chartink_session=<user-supplied value>
  3. Response JSON: { "data": [ {"nsecode":"RELIANCE", "per_chg":"1.5", ...}, ... ] }

The user must supply the `_chartink_session` cookie value once from their
browser (DevTools → Application → Cookies → _chartink_session).  It is
long-lived (months) but expires eventually.
"""

import time
import requests
from bs4 import BeautifulSoup

BASE_URL   = "https://chartink.com"
SCREENER   = f"{BASE_URL}/screener/"
PROCESS    = f"{BASE_URL}/screener/process"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": SCREENER,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

# ── Pre-built Chartink scan clauses ──────────────────────────────────────────
# These match the Chartink conditions exactly as you would type them in the
# screener builder.  Volumes are in actual share count (Chartink uses raw numbers).

SCAN_CLAUSES = {
    "6M Consolidation Breakout": (
        "( {cash} ( "
        "daily close > daily ema ( daily close , 50 ) and "
        "daily close > 1 day ago max ( 126 , daily high ) and "
        "1 day ago min ( 126 , daily low ) < 1 day ago max ( 126 , daily high ) and "
        "daily volume > number 200000"
        " ) )"
    ),
    "1Y All-Time Breakout": (
        "( {cash} ( "
        "daily close > daily ema ( daily close , 50 ) and "
        "daily close > 1 day ago max ( 252 , daily high ) and "
        "1 day ago min ( 252 , daily low ) < 1 day ago max ( 252 , daily high ) and "
        "daily volume > number 200000"
        " ) )"
    ),
    "3Y Breakout": (
        "( {cash} ( "
        "daily close > daily ema ( daily close , 50 ) and "
        "daily close > 1 day ago max ( 756 , daily high ) and "
        "1 day ago min ( 756 , daily low ) < 1 day ago max ( 756 , daily high ) and "
        "daily volume > number 200000"
        " ) )"
    ),
    "5Y Breakout": (
        "( {cash} ( "
        "daily close > daily ema ( daily close , 50 ) and "
        "daily close > 1 day ago max ( 1260 , daily high ) and "
        "1 day ago min ( 1260 , daily low ) < 1 day ago max ( 1260 , daily high ) and "
        "daily volume > number 200000"
        " ) )"
    ),
    "10Y Breakout": (
        "( {cash} ( "
        "daily close > daily ema ( daily close , 50 ) and "
        "daily close > 1 day ago max ( 2520 , daily high ) and "
        "1 day ago min ( 2520 , daily low ) < 1 day ago max ( 2520 , daily high ) and "
        "daily volume > number 200000"
        " ) )"
    ),
    # Coiled just under a 20-day resistance level — not broken out yet, RSI in a
    # constructive-but-not-overbought band, volume drying up in the base, and
    # trend intact above a rising EMA50.  This is the "1-2 sessions before the
    # move" setup: the confirmed-breakout clauses above only fire *after* price
    # has already cleared the level.  Volatility-contraction and the final
    # conviction score are computed client-side (see
    # scanner_templates.compute_pre_breakout_conviction) since Chartink has no
    # ATR-comparison operator to pre-filter on.
    "Pre-Breakout Setup (1-2 Day)": (
        "( {cash} ( "
        "daily close > daily ema ( daily close , 50 ) and "
        "daily close <= 1 day ago max ( 20 , daily high ) and "
        "daily close > 0.90 * 1 day ago max ( 20 , daily high ) and "
        "daily rsi ( 14 ) > 40 and daily rsi ( 14 ) < 72 and "
        "daily volume < 1.3 * daily sma ( daily volume , 20 ) and "
        "daily volume > number 50000"
        " ) )"
    ),
}


def _make_session(chartink_session_cookie: str) -> requests.Session:
    s = requests.Session()
    s.cookies.set("_chartink_session", chartink_session_cookie, domain="chartink.com")
    return s


def _get_csrf_token(session: requests.Session, timeout: int = 20) -> str:
    """Load the screener page and extract the CSRF meta tag."""
    resp = session.get(SCREENER, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    meta = soup.find("meta", {"name": "csrf-token"})
    if not meta or not meta.get("content"):
        raise ValueError(
            "Could not find CSRF token on chartink.com — "
            "the session cookie may be expired or invalid."
        )
    return meta["content"]


def run_chartink_scan(
    scan_clause: str,
    chartink_session_cookie: str,
    retries: int = 2,
    timeout: int = 30,
) -> list[dict]:
    """
    Run a raw scan_clause string against chartink.com/screener/process.

    Returns a list of dicts with keys:
        nsecode, bsecode, per_chg, close, volume, series, market_cap_full
    Raises on auth failure or HTTP error.
    """
    session = _make_session(chartink_session_cookie)
    csrf    = _get_csrf_token(session, timeout=timeout)

    headers = {**HEADERS, "X-CSRF-Token": csrf}
    payload = {"scan_clause": scan_clause}

    for attempt in range(retries + 1):
        try:
            resp = session.post(PROCESS, data=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            break
        except (requests.Timeout, requests.ConnectionError):
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)

    if "data" not in data:
        raise ValueError(f"Unexpected response from Chartink: {data}")

    return data["data"]   # list of stock-dicts


def run_named_scan(
    scan_name: str,
    chartink_session_cookie: str,
    **kwargs,
) -> list[dict]:
    """Run one of the pre-built SCAN_CLAUSES by name."""
    clause = SCAN_CLAUSES.get(scan_name)
    if clause is None:
        raise KeyError(f"Unknown scan: {scan_name!r}. Available: {list(SCAN_CLAUSES)}")
    return run_chartink_scan(clause, chartink_session_cookie, **kwargs)


# ── CLI smoke-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: py chartink_scraper.py <_chartink_session cookie> [scan_name]")
        print("Available scans:", list(SCAN_CLAUSES))
        sys.exit(1)
    cookie = sys.argv[1]
    name   = sys.argv[2] if len(sys.argv) > 2 else "1Y All-Time Breakout"
    rows   = run_named_scan(name, cookie)
    print(f"{len(rows)} stocks matched '{name}'")
    print(json.dumps(rows[:5], indent=2))
