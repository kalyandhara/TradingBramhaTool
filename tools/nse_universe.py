"""nse_universe.py — index constituents and NSE's own sector taxonomy.

SR-0. Why this exists
---------------------
`nse_shareholding_fetch.fetch_industry_and_cap` read `Industry` and market cap
from `nseindia.com/api/quote-equity`. That endpoint now returns **403 for every
symbol** (verified 2026-08-01 across RELIANCE / TCS / TITAN / HDFCBANK /
SUNPHARMA / TATASTEEL — 6 of 6). Because `build_dataset` *skips* any symbol whose
industry or cap is None, the whole Other Screeners -> Pipeline -> Sector Rotation
path had been producing an **empty frame** — no error, just no rows. That is the
same failure shape the wiki log records for DS-2, one layer down.

NSE's index-constituent archive CSVs are not behind the API gateway and carry the
label we need:

    https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv
    -> HTTP 200, 500 rows, columns: Company Name, Industry, Symbol, Series, ISIN Code

Two things this module deliberately does NOT do:

  * It does not read the filing-master's own `industry` field. That key exists on
    the shareholding-master response and looks like a free route around the 403 —
    it is the string `'-'` for every symbol tested. A decoy, recorded here so
    nobody spends the afternoon on it twice.
  * It does not guess a sector index for every label. Four of NSE's twenty macro
    sectors have no counterpart among the eleven indices we track, and they stay
    unmapped, exactly as `sector_rotation.SECTOR_INDEX_MAP` documents for its own
    vocabulary: "unmapped sectors are intentionally left as unscored rather than
    guessed, to avoid silently misclassifying bias".
"""

from __future__ import annotations

import io
import json
import logging
import time
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

HERE      = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache"
#: Constituent lists are reconstituted about twice a year; a week is generous
#: and still means a rename cannot go stale for a whole quarter.
CACHE_TTL = 7 * 24 * 3600

INDEX_CSVS = {
    "nifty500": "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "nifty200": "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv",
    "nifty100": "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
    "nifty50":  "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/csv,*/*",
    "Referer": "https://www.nseindia.com/",
}

# ──────────────────────────────────────────────────────────────────────────────
# NSE macro-sector -> the sector index that actually tracks it
# ──────────────────────────────────────────────────────────────────────────────
# NSE's constituent CSV uses a 20-value macro taxonomy. `sector_rotation`'s
# existing SECTOR_INDEX_MAP is keyed on screener.in's ~130-value Industry
# vocabulary instead, and the two share **nothing**: measured 2026-08-01, 0 of
# NSE's 20 labels appear among its 97 keys. So this is a second map, not an
# extension of that one — and being coarse, it maps onto eleven indices far more
# honestly than a 130-way vocabulary could.
#
# The four omissions are deliberate, not gaps to fill later:
#   Services / Diversified — grab-bag labels with no coherent index
#   Textiles / Media Entertainment & Publication — real sectors, but no index
#     among the eleven this repo tracks
# Together they are 27 of the 500 constituents (5.4%), and they come back
# "unscored" rather than being folded into whichever index looks nearest.
NSE_SECTOR_INDEX_MAP = {
    "Financial Services":              "NIFTY_FIN_SERVICE.NS",
    "Information Technology":          "^CNXIT",
    "Telecommunication":               "^CNXIT",       # display label is "IT / Telecom"
    "Healthcare":                      "^CNXPHARMA",
    "Automobile and Auto Components":  "^CNXAUTO",
    "Fast Moving Consumer Goods":      "^CNXFMCG",
    "Chemicals":                       "^CNXFMCG",     # display label is "FMCG / Chem"
    "Metals & Mining":                 "^CNXMETAL",
    "Realty":                          "^CNXREALTY",
    "Capital Goods":                   "^CNXINFRA",
    "Construction":                    "^CNXINFRA",
    "Construction Materials":          "^CNXINFRA",
    "Power":                           "^CNXENERGY",
    "Oil Gas & Consumable Fuels":      "^CNXENERGY",
    "Consumer Durables":               "^CNXCONSUM",
    "Consumer Services":               "^CNXCONSUM",
}

#: Labels seen in the CSV that intentionally have no index (see above).
UNMAPPED_SECTORS = {"Services", "Diversified", "Textiles",
                    "Media Entertainment & Publication"}


def _cache_path(index: str) -> Path:
    return CACHE_DIR / f"nse_{index}_constituents.json"


def _read_cache(index: str) -> list[dict] | None:
    p = _cache_path(index)
    try:
        if not p.exists() or (time.time() - p.stat().st_mtime) > CACHE_TTL:
            return None
        return json.loads(p.read_text(encoding="utf-8")) or None
    except Exception as e:
        log.debug("constituent cache read failed (%s): %s", index, e)
        return None


def _write_cache(index: str, rows: list[dict]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(index).write_text(json.dumps(rows), encoding="utf-8")
    except Exception as e:
        log.debug("constituent cache write failed (%s): %s", index, e)


#: In-process memo on top of the disk cache. `build_dataset` asks for the
#: industry of every symbol in turn; without this, each lookup would re-read and
#: re-parse the same JSON file 500 times.
_MEMO: dict[str, list[dict]] = {}


def fetch_constituents(index: str = "nifty500",
                       use_cache: bool = True) -> list[dict]:
    """[{symbol, name, industry, isin}] for an NSE index. [] if unreachable.

    Returns the cached copy on a failed fetch even when the cache is stale — a
    week-old constituent list is a far better answer than no universe at all,
    and the caller is told which it got via the log line.
    """
    if use_cache:
        if index in _MEMO:
            return _MEMO[index]
        cached = _read_cache(index)
        if cached:
            _MEMO[index] = cached
            return cached

    url = INDEX_CSVS.get(index)
    if url is None:
        raise ValueError(f"unknown index {index!r}; known: {sorted(INDEX_CSVS)}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
    except Exception as e:
        log.warning("constituent fetch failed for %s: %s", index, e)
        stale = _read_cache(index) or (json.loads(_cache_path(index).read_text("utf-8"))
                                       if _cache_path(index).exists() else None)
        if stale:
            log.warning("falling back to STALE cached %s constituents", index)
            return stale
        return []

    rows = [
        {
            "symbol":   str(row.get("Symbol", "")).strip().upper(),
            "name":     str(row.get("Company Name", "")).strip(),
            "industry": str(row.get("Industry", "")).strip(),
            "isin":     str(row.get("ISIN Code", "")).strip(),
        }
        for _, row in df.iterrows()
    ]
    rows = [r for r in rows if r["symbol"]]
    if rows:
        _write_cache(index, rows)
        _MEMO[index] = rows
        log.info("NSE %s constituents fetched — %d rows", index, len(rows))
    return rows


def industry_map(index: str = "nifty500") -> dict[str, str]:
    """symbol -> NSE macro-sector label."""
    return {r["symbol"]: r["industry"] for r in fetch_constituents(index) if r["industry"]}


def symbols(index: str = "nifty500") -> list[str]:
    return [r["symbol"] for r in fetch_constituents(index)]


def index_for_sector(label: str | None) -> str | None:
    """Sector-index ticker for an NSE macro-sector label, or None if unmapped."""
    return NSE_SECTOR_INDEX_MAP.get(label) if label else None


def market_cap(symbol: str) -> float | None:
    """Market cap in rupees via yfinance, or None.

    yfinance rather than NSE because the endpoint that used to serve this is the
    403 that motivated this module. `fast_info` is the cheap accessor; `.info` is
    a much heavier call and is only tried as a fallback.
    """
    try:
        import yfinance as yf
    except ImportError:
        return None
    tkr = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
    try:
        mc = yf.Ticker(tkr).fast_info["market_cap"]
        if mc:
            return float(mc)
    except Exception:
        pass
    try:
        mc = yf.Ticker(tkr).info.get("marketCap")
        return float(mc) if mc else None
    except Exception:
        return None


def coverage_report(index: str = "nifty500") -> dict:
    """How much of the universe this taxonomy actually scores. Used by callers to
    fail loudly instead of shipping an empty or mostly-unmapped frame."""
    rows = fetch_constituents(index)
    total = len(rows)
    mapped = sum(1 for r in rows if index_for_sector(r["industry"]))
    unknown = sorted({r["industry"] for r in rows
                      if r["industry"]
                      and r["industry"] not in NSE_SECTOR_INDEX_MAP
                      and r["industry"] not in UNMAPPED_SECTORS})
    return {
        "index": index, "total": total, "mapped": mapped,
        "mapped_pct": round(mapped / total * 100, 1) if total else 0.0,
        "unrecognised_labels": unknown,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    rep = coverage_report()
    print(f"{rep['index']}: {rep['mapped']}/{rep['total']} constituents "
          f"map to a sector index ({rep['mapped_pct']}%)")
    if rep["unrecognised_labels"]:
        print("Labels NSE added that this map has never seen — extend "
              "NSE_SECTOR_INDEX_MAP or add to UNMAPPED_SECTORS:")
        for lbl in rep["unrecognised_labels"]:
            print(f"  - {lbl}")
    else:
        print("Every label is either mapped or deliberately unmapped.")
