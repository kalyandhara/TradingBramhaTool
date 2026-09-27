#!/usr/bin/env python3
"""
smallcap_universe.py — FREE small/micro-cap universe from NSE index constituents.

The "hidden treasures" lane (backlog B-34) needs a universe the Opportunity Hub
funnel structurally cannot see: the funnel loads top-N by TRADED VALUE, which is
large-cap by construction. NSE publishes its Smallcap-250 and Microcap-250
constituent lists as public CSVs on the archives host — no screener.in cookie —
so this gives ~500 genuinely small/micro-cap names for free.

  from smallcap_universe import fetch_universe
  names = fetch_universe("both")   # [{symbol, name, industry, index}]

CLI:
  py -3 tools/smallcap_universe.py            # counts + a sample
  py -3 tools/smallcap_universe.py --refresh  # force re-fetch
"""
from __future__ import annotations

import csv
import io
import json
import logging
import time
from pathlib import Path

import nse_shareholding_fetch as _nsf   # reuse the warmed NSE session + HEADERS

log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache"
CACHE_TTL = 24 * 3600

INDEX_CSV = {
    "smallcap250": "https://nsearchives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
    "microcap250": "https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
    # UI-2 (2026-09-10): the two upper buckets, added for the CAP column. Same
    # free, cookie-less CSV path as the two above — no new dependency, no auth,
    # and NSE's own index membership rather than a market-cap threshold this
    # desk would have to pick and defend.
    "largecap100": "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
    "midcap150": "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
}

#: Bucket labels, smallest first. Order matters: `cap_bucket` resolves a symbol
#: to the FIRST list it appears in, so overlaps (a name in both microcap250 and
#: smallcap250) resolve to the tighter one, which is what the label should say.
_BUCKET_ORDER = (("microcap250", "Mic"), ("smallcap250", "SC"),
                 ("midcap150", "MC"), ("largecap100", "LC"))

# BSE SmallCap / MicroCap — the API endpoint returns JSON with constituent lists.
# These widen the universe beyond NSE indices (partial overlap expected; de-duped
# by symbol in fetch_universe).
BSE_INDEX_API = {
    "bse_smallcap": "https://api.bseindia.com/BseIndiaAPI/api/GetSensexData/w?Ession_id=&index_Code=22&FL=S",
    "bse_microcap": "https://api.bseindia.com/BseIndiaAPI/api/GetSensexData/w?Ession_id=&index_Code=90&FL=S",
}

# Small curated fallback (a handful per bucket) so a fetch failure still returns
# a usable, clearly small/micro-cap set rather than nothing.
_FALLBACK = {
    "smallcap250": [
        ("KIRLOSBROS", "Kirloskar Brothers Ltd.", "Capital Goods"),
        ("JBCHEPHARM", "JB Chemicals & Pharmaceuticals Ltd.", "Healthcare"),
        ("REDINGTON", "Redington Ltd.", "Services"),
        ("CROMPTON", "Crompton Greaves Consumer Electricals Ltd.", "Consumer Durables"),
    ],
    "microcap250": [
        ("ASKAUTOLTD", "ASK Automotive Ltd.", "Automobile and Auto Components"),
        ("GABRIEL", "Gabriel India Ltd.", "Automobile and Auto Components"),
        ("PGEL", "PG Electroplast Ltd.", "Consumer Durables"),
    ],
}


BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.bseindia.com/",
}


def _cache_path(kind: str) -> Path:
    return CACHE_DIR / f"smallcap_universe_{kind}.json"


def _fetch_bse_index(kind: str) -> list[dict] | None:
    """Fetch BSE index constituents via the public JSON API."""
    url = BSE_INDEX_API.get(kind)
    if not url:
        return None
    try:
        import requests
        r = requests.get(url, headers=BSE_HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        out = []
        for item in data:
            # BSE API returns scrip_cd (code) and scripname / long_name / industry
            sym = (item.get("scrip_id") or item.get("scripname") or "").strip()
            name = (item.get("long_name") or item.get("scripname") or "").strip()
            ind = (item.get("industry") or "").strip()
            if not sym:
                continue
            sym_clean = sym.upper().replace(" ", "")
            out.append({
                "symbol": sym_clean,
                "name": name,
                "industry": ind,
                "index": kind,
            })
        log.info("BSE %s constituents: %d", kind, len(out))
        return out or None
    except Exception as e:
        log.warning("BSE %s constituent fetch failed: %s", kind, e)
        return None


def _fetch_index_csv(kind: str) -> list[dict] | None:
    url = INDEX_CSV.get(kind)
    if not url:
        return None
    try:
        session = _nsf._new_session()
        r = session.get(url, headers=_nsf.HEADERS, timeout=20)
        r.raise_for_status()
        out = []
        for row in csv.DictReader(io.StringIO(r.text)):
            sym = (row.get("Symbol") or "").strip()
            if not sym or sym.upper().startswith("DUMMY"):
                continue    # NSE placeholder row during a corporate action
            out.append({
                "symbol": sym,
                "name": (row.get("Company Name") or "").strip(),
                "industry": (row.get("Industry") or "").strip(),
                "index": kind,
            })
        log.info("NSE %s constituents: %d", kind, len(out))
        return out or None
    except Exception as e:
        log.warning("NSE %s constituent fetch failed: %s", kind, e)
        return None


def _load_kind(kind: str, refresh: bool = False) -> list[dict]:
    CACHE_DIR.mkdir(exist_ok=True)
    p = _cache_path(kind)
    if not refresh and p.exists() and (time.time() - p.stat().st_mtime) < CACHE_TTL:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    if kind in BSE_INDEX_API:
        entries = _fetch_bse_index(kind)
    else:
        entries = _fetch_index_csv(kind)
    if entries:
        try:
            p.write_text(json.dumps(entries), encoding="utf-8")
        except Exception as e:
            log.warning("could not cache %s: %s", kind, e)
        return entries
    if p.exists():                                   # stale cache beats fallback
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    log.warning("using bundled %s fallback (%d names)", kind, len(_FALLBACK.get(kind, [])))
    return [{"symbol": s, "name": n, "industry": i, "index": kind}
            for s, n, i in _FALLBACK.get(kind, [])]


_KIND_ALIASES = {
    "both": ["smallcap250", "microcap250"],
    "nse": ["smallcap250", "microcap250"],
    "bse": ["bse_smallcap", "bse_microcap"],
    "all": ["smallcap250", "microcap250", "bse_smallcap", "bse_microcap"],
}


def cap_bucket(symbols=None, *, refresh: bool = False) -> dict[str, str]:
    """{SYMBOL: "Mic"|"SC"|"MC"|"LC"} from NSE index membership.

    Membership, not a market-cap threshold. A threshold would be a number this
    desk had to choose, defend and re-cut as the market moves; index membership
    is NSE's own answer, already cached here, and it is what the label on a
    screener chip actually means to a reader.

    A symbol in none of the four lists is ABSENT from the result rather than
    labelled — outside the top ~1,000 by cap there is no bucket to give it, and
    a blank cell is the honest rendering of that. Never guess a bucket.
    """
    out: dict[str, str] = {}
    want = None if symbols is None else {str(s).strip().upper() for s in symbols}
    # Reverse order so the TIGHTEST bucket wins on overlap: writing LC first and
    # letting Mic overwrite it is simpler than checking membership four times.
    for kind, label in reversed(_BUCKET_ORDER):
        try:
            entries = _load_kind(kind, refresh=refresh)
        except Exception as e:                                # pragma: no cover
            log.warning("cap_bucket: %s unavailable (%s)", kind, e)
            continue
        for e in entries or []:
            sym = str(e.get("symbol", "")).strip().upper()
            if not sym or (want is not None and sym not in want):
                continue
            out[sym] = label
    return out


def fetch_universe(kind: str = "both", *, refresh: bool = False) -> list[dict]:
    """Free small/micro-cap universe.
    kind ∈ {smallcap250, microcap250, bse_smallcap, bse_microcap,
            both (NSE only), nse, bse, all (NSE+BSE)}.
    Returns [{symbol, name, industry, index}], de-duplicated by symbol."""
    kinds = _KIND_ALIASES.get(kind, [kind])
    seen: set[str] = set()
    out: list[dict] = []
    for k in kinds:
        for e in _load_kind(k, refresh=refresh):
            if e["symbol"] not in seen:
                seen.add(e["symbol"])
                out.append(e)
    return out


def symbols(kind: str = "both", *, suffix: str = "") -> list[str]:
    """Just the tickers, optionally suffixed (e.g. '.NS' for yfinance)."""
    return [e["symbol"] + suffix for e in fetch_universe(kind)]


def refresh_all() -> dict[str, int]:
    return {k: len(_load_kind(k, refresh=True)) for k in INDEX_CSV}


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(description="NSE small/micro-cap universe")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--kind", default="both")
    a = ap.parse_args()
    uni = fetch_universe(a.kind, refresh=a.refresh)
    print(f"{a.kind}: {len(uni)} names")
    for e in uni[:8]:
        print(f"  {e['symbol']:14} {e['industry']:32} {e['name']}")
