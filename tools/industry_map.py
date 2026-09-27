#!/usr/bin/env python3
"""industry_map.py — NSE's four-level industry classification per symbol.

NSE classifies every listed company as macro → sector → industry → basic
industry (e.g. FMCG → FMCG → Agricultural Food & other Products → **Sugar**).
The index-constituent CSVs carry only the broad sector (~20 labels), and the
NSE API that serves the rest (`quote-equity`) returns 403 (see `nse_universe`).

screener.in's public company page prints the same four levels as `/market/…`
links, no login needed. This module reads them once per symbol and caches them
in `cache/industry_map.json`; a classification changes rarely, so the cache is
refreshed only for symbols it lacks (or on `refresh=True`).

Used by `sector_ranking` to group at basic-industry level, the granularity
ScreeningMantis's sector table uses (Sugar, Cables & Wires, Paints…).
"""
from __future__ import annotations

import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

import requests

CACHE = Path(__file__).resolve().parent / "cache" / "industry_map.json"
URL = "https://www.screener.in/company/{sym}/"
LEVELS = ("macro", "sector", "industry", "basic")
_LINK = re.compile(r'href="/market/[^"]+"[^>]*>\s*([^<]+?)\s*</a>')
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/126 Safari/537.36"}


def parse(page: str) -> Optional[dict[str, str]]:
    """The four `/market/` breadcrumb labels, or None if the page lacks them."""
    labels = [html.unescape(x).strip() for x in _LINK.findall(page)]
    if len(labels) < 4:
        return None
    return dict(zip(LEVELS, labels[:4]))


def fetch_one(sym: str, session: requests.Session | None = None,
              pause: float = 0.25) -> Optional[dict[str, str]]:
    s = session or requests.Session()
    s.headers.update(_HEADERS)
    try:
        r = s.get(URL.format(sym=sym), timeout=20)
    except requests.RequestException:
        return None
    time.sleep(pause)
    return parse(r.text) if r.status_code == 200 else None


def _read() -> dict[str, dict[str, str]]:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(data: dict[str, dict[str, str]]) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data, indent=0, sort_keys=True), encoding="utf-8")


def load(symbols: list[str], *, refresh: bool = False, workers: int = 2,
         fetch: Callable[[str], Optional[dict]] = fetch_one) -> dict[str, dict[str, str]]:
    """`{symbol: {macro, sector, industry, basic}}`, fetching only what is missing."""
    data = {} if refresh else _read()
    missing = [s for s in symbols if s not in data]
    if missing:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for sym, cls in zip(missing, ex.map(fetch, missing)):
                if cls:
                    data[sym] = cls
        _write(data)
    return {s: data[s] for s in symbols if s in data}


def symbol_map(universe: str = "niftytotalmarket", level: str = "basic") -> dict[str, str]:
    """`{symbol: label}` at the chosen level for an NSE index universe."""
    import nse_universe as nu
    syms = nu.symbols(universe)
    return {s: c[level] for s, c in load(syms).items() if c.get(level)}


if __name__ == "__main__":
    import sys
    u = sys.argv[1] if len(sys.argv) > 1 else "niftytotalmarket"
    m = symbol_map(u)
    from collections import Counter
    print(f"{len(m)} symbols classified")
    for label, n in Counter(m.values()).most_common(25):
        print(f"{n:4d}  {label}")
