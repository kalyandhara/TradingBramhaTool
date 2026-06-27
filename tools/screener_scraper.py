#!/usr/bin/env python3
"""
screener_scraper.py
Authenticated screener.in scraper for sector_rotation.py's input data.

Hits the raw query results page directly (paginated HTML table) using your
screener.in session cookie, then visits each company's page once to read
its Sector/Industry from the "Peer comparison" breadcrumb. Replaces the
manual Edit Columns + Export workflow.

Requires a valid screener.in `sessionid` cookie value (from your browser's
dev tools: Application/Storage > Cookies > https://www.screener.in >
sessionid). The cookie expires eventually — re-grab it if requests start
getting redirected to /register/.

Run manually:
  py -3 tools/screener_scraper.py SESSIONID
  py -3 tools/screener_scraper.py SESSIONID --query "Market Capitalization > 1000 AND ..."

Output: screener_export_<date>.csv in the shape sector_rotation.py expects
(Name, Mar Cap, Change in FII holding %, Industry).
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENER_BASE = "https://www.screener.in"

DEFAULT_QUERY = (
    "Market Capitalization > 1000 AND\n"
    "Current price > 30 AND\n"
    "(Change in FII holding > 0.5 OR Change in FII holding < -0.5)"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
log = logging.getLogger(__name__)


def _session(sessionid: str) -> requests.Session:
    s = requests.Session()
    s.cookies.set("sessionid", sessionid, domain="www.screener.in")
    return s


def _check_authenticated(session: requests.Session, resp: requests.Response) -> None:
    if "/register/" in resp.url or resp.history and any("/register/" in h.headers.get("Location", "") for h in resp.history):
        sys.exit(
            "Got redirected to the login/register page — the sessionid cookie is "
            "invalid or expired. Re-grab it from your browser and try again."
        )


def fetch_results_page(session: requests.Session, query: str, page: int) -> BeautifulSoup:
    url = f"{SCREENER_BASE}/screen/raw/"
    params = {"sort": "", "order": "", "query": query, "page": page}
    resp = session.get(url, headers=HEADERS, params=params, timeout=30, allow_redirects=True)
    _check_authenticated(session, resp)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_results_table(soup: BeautifulSoup) -> tuple[list[dict], int]:
    table = soup.find("table", class_="data-table")
    if table is None:
        return [], 0

    # screener.in repeats the header row every ~10 data rows for readability;
    # only the first occurrence is the real header set.
    first_header_row = table.find("tr")
    headers = [th.get("data-tooltip") or th.get_text(strip=True)
               for th in first_header_row.find_all("th")]

    rows = []
    for tr in table.find("tbody").find_all("tr", attrs={"data-row-company-id": True}):
        cells = tr.find_all("td")
        if len(cells) != len(headers):
            continue
        link = cells[1].find("a")
        name = link.get_text(strip=True) if link else cells[1].get_text(strip=True)
        slug = None
        if link:
            # href is like /company/RELIANCE/ or /company/RELIANCE/consolidated/ —
            # the slug is always the segment right after "company", not the last segment.
            parts = link["href"].strip("/").split("/")
            if "company" in parts:
                slug = parts[parts.index("company") + 1]
        row = {"Name": name, "_slug": slug}
        for h, c in zip(headers[2:], cells[2:]):
            row[h] = c.get_text(strip=True)
        rows.append(row)

    count_text = soup.find(string=lambda t: t and "results found" in t)
    total = 0
    if count_text:
        try:
            total = int(count_text.strip().split()[0])
        except (ValueError, IndexError):
            pass

    return rows, total


def fetch_all_results(session: requests.Session, query: str) -> list[dict]:
    all_rows, page = [], 1
    while True:
        soup = fetch_results_page(session, query, page)
        rows, total = parse_results_table(soup)
        if not rows:
            break
        all_rows.extend(rows)
        log.info("Page %d: %d rows (running total %d/%d)", page, len(rows), len(all_rows), total)
        if len(all_rows) >= total or not total:
            break
        page += 1
        time.sleep(1)
    return all_rows


def _parse_quarterly_holding(soup: BeautifulSoup, label: str) -> dict[str, float]:
    """label is a substring to match in the row's text, e.g. 'FII' or 'DII'."""
    qshp = soup.find("div", id="quarterly-shp")
    if qshp is None:
        return {}
    table = qshp.find("table")
    if table is None:
        return {}

    quarters = [th.get_text(strip=True) for th in table.find("thead").find_all("th")][1:]
    for tr in table.find("tbody").find_all("tr"):
        label_cell = tr.find("td", class_="text")
        if label_cell is None or label not in label_cell.get_text():
            continue
        values = [td.get_text(strip=True) for td in tr.find_all("td")[1:]]
        result = {}
        for q, v in zip(quarters, values):
            try:
                result[q] = float(v.replace("%", ""))
            except ValueError:
                continue
        return result
    return {}


def _parse_quarterly_fii(soup: BeautifulSoup) -> dict[str, float]:
    return _parse_quarterly_holding(soup, "FII")


def fetch_company_page(session: requests.Session, slug: str, retries: int = 3) -> BeautifulSoup | None:
    url = f"{SCREENER_BASE}/company/{slug}/"
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                log.warning("[%s] rate-limited (429), backing off %ds", slug, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            log.warning("[%s] company page fetch failed: %s", slug, e)
            return None
    log.warning("[%s] gave up after %d retries (rate-limited)", slug, retries)
    return None


def fetch_sector_and_history(session: requests.Session, slug: str) -> tuple[str | None, dict[str, float]]:
    soup = fetch_company_page(session, slug)
    if soup is None:
        return None, {}

    industry_link = soup.find("a", title="Industry")
    broad_industry_link = soup.find("a", title="Broad Industry")
    link = industry_link or broad_industry_link
    industry = link.get_text(strip=True) if link else None

    quarterly_fii = _parse_quarterly_fii(soup)
    return industry, quarterly_fii


def build_dataset(sessionid: str, query: str) -> pd.DataFrame:
    session = _session(sessionid)

    log.info("Fetching screener results...")
    rows = fetch_all_results(session, query)
    if not rows:
        sys.exit("No results parsed — check the query or whether the cookie is still valid.")

    fii_col = next((c for c in rows[0] if "FII" in c), None)
    cap_col = next((c for c in rows[0] if "Market Capitalization" in c or "Mar Cap" in c), None)
    if fii_col is None or cap_col is None:
        sys.exit(f"Could not find FII/Market-Cap columns in parsed headers: {list(rows[0].keys())}")

    log.info("Fetching sector for %d unique companies...", len(rows))
    cache: dict[str, tuple[str | None, dict[str, float]]] = {}
    all_quarters: set[str] = set()
    for i, row in enumerate(rows, 1):
        slug = row["_slug"]
        if slug not in cache:
            cache[slug] = fetch_sector_and_history(session, slug)
            time.sleep(2.0)
        industry, quarterly_fii = cache[slug]
        row["Industry"] = industry
        row["_quarterly_fii"] = quarterly_fii
        all_quarters.update(quarterly_fii.keys())
        if i % 25 == 0:
            log.info("  company lookup %d/%d", i, len(rows))

    quarter_cols = sorted(all_quarters, key=lambda q: pd.Period(q, freq="Q") if q else q)

    df = pd.DataFrame(rows)
    df = df.rename(columns={fii_col: "Change in FII holding %", cap_col: "Mar Cap"})
    df["Change in FII holding %"] = pd.to_numeric(df["Change in FII holding %"], errors="coerce")
    df["Mar Cap"] = pd.to_numeric(df["Mar Cap"].astype(str).str.replace(",", ""), errors="coerce")

    for q in quarter_cols:
        df[f"FII_{q}"] = df["_quarterly_fii"].apply(lambda d, q=q: d.get(q))

    keep = ["Name", "Mar Cap", "Change in FII holding %", "Industry"] + [f"FII_{q}" for q in quarter_cols]
    out = df[keep].dropna(subset=["Name", "Mar Cap", "Change in FII holding %", "Industry"])
    skipped = len(df) - len(out)
    if skipped:
        log.warning("Dropped %d rows with missing sector/numeric data", skipped)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: py -3 tools/screener_scraper.py SESSIONID [--query \"...\"]")

    sessionid = sys.argv[1]
    query = DEFAULT_QUERY
    if "--query" in sys.argv:
        query = sys.argv[sys.argv.index("--query") + 1]

    df = build_dataset(sessionid, query)
    out_path = BASE_DIR / f"screener_export_{datetime.today().strftime('%Y%m%d')}.csv"
    df.to_csv(out_path, index=False)
    quarter_count = sum(c.startswith("FII_") for c in df.columns)
    print(f"Saved -> {out_path}  ({len(df)} rows, {quarter_count} quarterly FII columns)")
    print("Next: py -3 tools/sector_rotation.py", out_path)
