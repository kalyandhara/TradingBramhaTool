"""
finviz_sentiment.py — Scrape US market context from finviz.com.

Finviz has no public API but its homepage renders classic HTML tables that are
free to scrape at low frequency. We pull:

  * Index snapshot (DOW / NASDAQ / S&P 500 / RUSSELL 2000)  — day change
  * Market breadth: Advancing/Declining, New High/Low, Above/Below SMA50/SMA200
  * Bull/Bear signal ratio (from the sentiment strip)
  * Signal tables: Top Gainers, Top Losers, New High, Unusual Volume, Insider Buying

The dashboard's Market Sentiment page uses NIFTY inputs; this adds US-market
context so you can see if global risk-on/risk-off is confirming or diverging
from the domestic reading.
"""

from __future__ import annotations

import logging
import re
from io import StringIO
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

FINVIZ_HOME = "https://finviz.com/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _get(url: str, timeout: int = 15) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        log.warning("finviz fetch failed (%s): %s", url, e)
        return None


# ── Index snapshot (day change for DOW/NASDAQ/S&P/RUSSELL) ────────────────────

def fetch_index_snapshot() -> pd.DataFrame:
    """DOW / NASDAQ / S&P 500 / RUSSELL 2000 day change via yfinance.
    Finviz renders these inside JS mini-charts, so we source from yfinance
    (already a project dependency) instead of scraping."""
    tickers = [("DOW", "^DJI"), ("NASDAQ", "^IXIC"),
               ("S&P 500", "^GSPC"), ("RUSSELL 2000", "^RUT")]
    rows = []
    try:
        import yfinance as yf
        for name, sym in tickers:
            try:
                fi = yf.Ticker(sym).fast_info
                last = float(fi.get("lastPrice") or 0)
                prev = float(fi.get("previousClose") or 0)
                pct = ((last - prev) / prev * 100.0) if prev else None
                rows.append({"index": name, "last": round(last, 2),
                             "chg_pct": round(pct, 2) if pct is not None else None})
            except Exception as e:
                log.debug("index fetch failed %s: %s", sym, e)
                rows.append({"index": name, "last": None, "chg_pct": None})
    except ImportError:
        log.warning("yfinance not installed")
    return pd.DataFrame(rows)


# ── Breadth strip (Advancing/Declining, New H/L, Above/Below SMAs, Bull/Bear) ─

_BREADTH_LABELS = {
    "Advancing": "advancing", "Declining": "declining",
    "New High": "new_high",   "New Low":   "new_low",
    "Above":    "above_sma",  "Below":     "below_sma",
    "BULL":     "bull_pct",   "BEAR":      "bear_pct",
}


def fetch_breadth() -> dict[str, Any]:
    """Return a flat dict of the numeric breadth stats visible on the strip.

    Notes on the SMA50 / SMA200 split — the strip labels both as 'Above/Below',
    disambiguated by a nearby 'SMA50' / 'SMA200' tag. We capture both cells and
    map them by nearby text.
    """
    soup = _get(FINVIZ_HOME)
    if soup is None:
        return {}

    stats: dict[str, Any] = {}
    text = soup.get_text(" ", strip=True)

    # Finviz's breadth strip is a horizontal bar — left side shows the "good"
    # metric label + pct + count in normal order, right side shows the "bad"
    # metric with count-first (mirrored). So the flattened text looks like:
    #   "Advancing 54.0% (3032) Declining (2355) 42.0%"
    # Handle both orderings for every label.
    NUM  = r"([\d.]+)"
    CNT  = r"\(?([\d,]+)\)?"
    for label in ["Advancing", "Declining", "New High", "New Low"]:
        # Try each of the four orderings; first match wins.
        patterns = [
            rf"{label}\s+{NUM}%\s+{CNT}",     # label pct count
            rf"{label}\s+{CNT}\s+{NUM}%",     # label count pct  (mirrored)
            rf"{CNT}\s+{NUM}%\s+{label}",     # count pct label
            rf"{NUM}%\s+{CNT}\s+{label}",     # pct count label
        ]
        pct = count = None
        for pat in patterns:
            m = re.search(pat, text)
            if not m:
                continue
            g1, g2 = m.group(1), m.group(2)
            # A group with '.' is the pct; a group of only digits/commas is the count.
            if "." in g1:
                pct, count = float(g1), g2.replace(",", "")
            else:
                count, pct = g1.replace(",", ""), float(g2)
            break
        if pct is not None:
            stats[_BREADTH_LABELS[label]] = {
                "pct": pct,
                "count": int(count) if count else None,
            }

    # SMA50 / SMA200 above-below: capture "Above 52.4% (2937) SMA50 Below 47.6% (2664)"
    for sma in ["SMA50", "SMA200"]:
        m = re.search(
            rf"Above\s+([\d.]+)%\s*\(?([\d,]+)?\)?.*?{sma}.*?Below\s+([\d.]+)%\s*\(?([\d,]+)?\)?",
            text, flags=re.DOTALL,
        )
        if m:
            stats[f"above_{sma.lower()}"] = float(m.group(1))
            stats[f"below_{sma.lower()}"] = float(m.group(3))

    # Bull / Bear strip: "76% BULL 24% BEAR"
    m = re.search(r"(\d+)%\s*BULL.*?(\d+)%\s*BEAR", text, flags=re.DOTALL)
    if m:
        stats["bull_pct"] = int(m.group(1))
        stats["bear_pct"] = int(m.group(2))

    return stats


# ── Signal tables (Top Gainers / Losers / Unusual Volume / New High / Insider) ─

_SIGNAL_URLS = {
    "Top Gainers":     "https://finviz.com/screener.ashx?v=111&s=ta_topgainers",
    "Top Losers":      "https://finviz.com/screener.ashx?v=111&s=ta_toplosers",
    "New 52W High":    "https://finviz.com/screener.ashx?v=111&s=ta_newhigh",
    "Unusual Volume":  "https://finviz.com/screener.ashx?v=111&s=ta_unusualvolume",
    "Insider Buying":  "https://finviz.com/insidertrading.ashx?tc=1",
}


def fetch_signal_table(signal: str, limit: int = 20) -> pd.DataFrame:
    """Pull a finviz signal table by name. Returns first N rows."""
    url = _SIGNAL_URLS.get(signal)
    if not url:
        return pd.DataFrame()
    soup = _get(url)
    if soup is None:
        return pd.DataFrame()
    # Parse tables directly with BeautifulSoup — pandas.read_html secretly
    # requires lxml/html5lib, neither of which is a project dep.
    # Finviz's actual results grid carries class="screener_table" (or similar
    # "screener" substring). Fall back to any table whose rows look like
    # ticker rows if the class-based lookup fails.
    # Finviz's actual results grid carries class "styled-table-new" (also on
    # the Recent Insider Trading page). The legacy "screener_table" class no
    # longer maps to the grid — it's on unrelated modal panels now.
    grid = soup.find("table", class_=re.compile(r"styled-table-new"))
    tables_iter = [grid] if grid else soup.find_all("table")
    tables_data: list[list[list[str]]] = []
    for tbl in tables_iter:
        if tbl is None:
            continue
        rows = []
        for tr in tbl.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if rows and len(rows) > 1:
            tables_data.append(rows)
    if not tables_data:
        return pd.DataFrame()
    # A well-formed screener grid has header + N rows all the same width.
    # Prefer tables whose rows are uniformly wide (rules out the settings panel
    # whose rows have wildly varying cell counts).
    def _uniform_score(t):
        widths = [len(r) for r in t]
        return (len(t), -max(widths) + min(widths), widths[0])
    best = max(tables_data, key=_uniform_score)
    header, *body = best
    body = [r[:len(header)] + [""] * (len(header) - len(r)) for r in body]
    return pd.DataFrame(body, columns=header).head(limit)


# ── Convenience wrapper for the dashboard ─────────────────────────────────────

def fetch_all() -> dict[str, Any]:
    return {
        "indices": fetch_index_snapshot(),
        "breadth": fetch_breadth(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    snap = fetch_all()
    print("INDICES:\n", snap["indices"])
    print("\nBREADTH:\n", snap["breadth"])
    print("\nTOP GAINERS:\n", fetch_signal_table("Top Gainers", limit=5))
