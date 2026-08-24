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


def _cache_path(kind: str) -> Path:
    return CACHE_DIR / f"smallcap_universe_{kind}.json"


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
            if not sym:
                continue
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


def fetch_universe(kind: str = "both", *, refresh: bool = False) -> list[dict]:
    """Free small/micro-cap universe. kind ∈ {smallcap250, microcap250, both}.
    Returns [{symbol, name, industry, index}], de-duplicated by symbol."""
    kinds = (["smallcap250", "microcap250"] if kind == "both" else [kind])
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
