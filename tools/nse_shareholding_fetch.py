#!/usr/bin/env python3
"""
nse_shareholding_fetch.py
EXPERIMENTAL — free, no-login fallback for sector_rotation.py's input data.

Builds the same input that sector_rotation.py expects from a screener.in
export (Name, Mar Cap, Change in FII holding %, Industry) but sourced
directly from NSE's public corporate-filings APIs instead of screener.in.

Two data points NSE does not expose as clean JSON, scraped here:
  1. FII/FPI holding % per company per quarter -> from shareholding-pattern
     XBRL filings (corporate-share-holdings-master endpoint + XBRL parse).
  2. Industry classification -> from quote-equity API.

CAVEATS (untested against live NSE — this sandbox's IP is blocked by NSE's
Akamai CDN with "Access Denied" regardless of headers/session warmup, so
this can only be validated by running it from a real home/office IP):
  - XBRL tag names for FII/FPI holding vary slightly by filing software
    version. parse_fii_pct() tries several known tag patterns; if NSE
    changes filing format or a filer uses an unrecognized tag, that
    symbol will silently return None and get skipped — check the log.
  - NSE rate-limits aggressively; this sleeps between requests but may
    still need retries/backoff tuning on first real run.
  - Only the latest two quarterly filings are compared (most recent vs
    immediately preceding) to compute the FII % change.

Run manually:
  py -3 tools/nse_shareholding_fetch.py SYMBOL1 SYMBOL2 ...
  py -3 tools/nse_shareholding_fetch.py --top200    # use Bhavcopy top-200 list

Output: nse_fii_change_<date>.csv in the same shape sector_rotation.py
expects (Name, Mar Cap, Change in FII holding %, Industry), so you can run:
  py -3 tools/sector_rotation.py nse_fii_change_<date>.csv
"""

import re
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE_DIR = Path(__file__).resolve().parent.parent

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
    "X-Requested-With": "XMLHttpRequest",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
log = logging.getLogger(__name__)


def _new_session() -> requests.Session:
    s = requests.Session()
    try:
        s.get("https://www.nseindia.com/", headers=HEADERS, timeout=15)
        s.get("https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
              headers=HEADERS, timeout=15)
    except Exception as e:
        log.warning("Session warmup failed: %s", e)
    return s


def get_shareholding_filings(session: requests.Session, symbol: str) -> list[dict]:
    """Returns recent shareholding-pattern filings for a symbol, newest first."""
    url = "https://www.nseindia.com/api/corporate-share-holdings-master"
    try:
        r = session.get(url, headers=HEADERS, params={"index": "equities", "symbol": symbol}, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("[%s] filing-master fetch failed: %s", symbol, e)
        return []

    filings = data if isinstance(data, list) else data.get("data", [])
    filings = [f for f in filings if f.get("symbol", "").upper() == symbol.upper()]
    filings.sort(key=lambda f: f.get("toDate", ""), reverse=True)
    return filings


# XBRL tag patterns observed across common filing-software vendors for
# "Total shareholding of FII/FPI as a % of total share capital".
_FII_TAG_PATTERNS = [
    r"TotalShareholdingAsAPercentageOfTotalNumberOfShares[^>]*FII[^>]*>([\d.]+)<",
    r"ForeignPortfolioInvestor[^>]*TotalShareholdingPercentage[^>]*>([\d.]+)<",
    r"in-bse-fin:PercentageOfShareholdingForeignPortfolioInvestor[^>]*>([\d.]+)<",
    r"<.*?FIIHolding.*?>([\d.]+)<",
]


def parse_fii_pct(xbrl_text: str) -> float | None:
    for pattern in _FII_TAG_PATTERNS:
        m = re.search(pattern, xbrl_text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def fetch_fii_change(session: requests.Session, symbol: str) -> float | None:
    filings = get_shareholding_filings(session, symbol)
    if len(filings) < 2:
        log.warning("[%s] fewer than 2 filings found — cannot compute change", symbol)
        return None

    pcts = []
    for f in filings[:2]:
        xbrl_url = f.get("xbrl") or f.get("xbrlFile")
        if not xbrl_url:
            return None
        try:
            r = session.get(xbrl_url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            pct = parse_fii_pct(r.text)
        except Exception as e:
            log.warning("[%s] XBRL fetch/parse failed: %s", symbol, e)
            return None
        if pct is None:
            log.warning("[%s] could not find FII tag in XBRL — filing format not recognized", symbol)
            return None
        pcts.append(pct)
        time.sleep(1)

    return round(pcts[0] - pcts[1], 3)


def fetch_industry_and_cap(session: requests.Session, symbol: str) -> tuple[str | None, float | None]:
    try:
        r = session.get("https://www.nseindia.com/api/quote-equity",
                         headers=HEADERS, params={"symbol": symbol}, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("[%s] quote-equity fetch failed: %s", symbol, e)
        return None, None

    industry = data.get("industryInfo", {}).get("industry") or data.get("info", {}).get("industry")
    mar_cap = None
    try:
        price = float(data.get("priceInfo", {}).get("lastPrice"))
        issued = float(data.get("securityInfo", {}).get("issuedSize"))
        mar_cap = round(price * issued / 1e7, 2)  # rupees crore
    except (TypeError, ValueError):
        pass

    return industry, mar_cap


def build_dataset(symbols: list[str]) -> pd.DataFrame:
    session = _new_session()
    rows = []
    for i, sym in enumerate(symbols, 1):
        log.info("[%d/%d] %s", i, len(symbols), sym)
        fii_chg = fetch_fii_change(session, sym)
        if fii_chg is None:
            continue
        industry, mar_cap = fetch_industry_and_cap(session, sym)
        if industry is None or mar_cap is None:
            log.warning("[%s] missing industry/mar_cap — skipping", sym)
            continue
        rows.append({
            "Name": sym,
            "Mar Cap": mar_cap,
            "Change in FII holding %": fii_chg,
            "Industry": industry,
        })
        time.sleep(1.5)

    return pd.DataFrame(rows)


def _bhav_top200_symbols() -> list[str]:
    from screener_pipeline import fetch_bhavcopy_top_volume
    return fetch_bhavcopy_top_volume(200)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: py -3 tools/nse_shareholding_fetch.py SYMBOL1 SYMBOL2 ...\n"
                  "       py -3 tools/nse_shareholding_fetch.py --top200")

    if sys.argv[1] == "--top200":
        symbols = _bhav_top200_symbols()
    else:
        symbols = [s.upper() for s in sys.argv[1:]]

    if not symbols:
        sys.exit("No symbols to process.")

    df = build_dataset(symbols)
    if df.empty:
        sys.exit("No data fetched — check pipeline.log-style output above for per-symbol failures.")

    out_path = BASE_DIR / f"nse_fii_change_{datetime.today().strftime('%Y%m%d')}.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved -> {out_path}")
    print(f"\nFetched {len(df)}/{len(symbols)} symbols successfully.")
    print("Next: py -3 tools/sector_rotation.py", out_path)
