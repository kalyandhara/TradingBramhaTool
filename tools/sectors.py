#!/usr/bin/env python3
"""sectors.py — ONE canonical sector vocabulary for the desk.

B-64. Before this module, "sector" meant three different things depending on
which page you were on, and the three did not join:

  1. NSE macro       — 20 labels on nifty500, 22 on niftytotalmarket, from the
                       constituent CSV. `nse_universe`, mapped to 11 indices.
  2. screener.in     — ~130 Industry values, 97 mapped in
                       `sector_rotation.SECTOR_INDEX_MAP`. Needs a manual
                       authenticated export.
  3. Yahoo/yfinance  — 11 sectors + ~150 industries. The ONLY one persisted
                       (`daily_opportunities.sector` / `.industry`).

`nse_universe`'s own comment records the collision, measured 2026-08-01: **0 of
NSE's 20 labels appear among screener.in's 97 keys** — the two "share nothing".

── The decision ───────────────────────────────────────────────────────────────
**NSE macro is canonical.** It is free, fetched from NSE itself with a 7-day
cache, covers the whole index universe, and is the only one of the three with an
honest index mapping (11 indices; 4 labels deliberately left UNMAPPED rather than
guessed). Yahoo's taxonomy is richer but is a US-shaped vocabulary applied to
Indian names; screener.in's is the most granular and the least reachable.

Yahoo sector/industry KEEPS being stored on opportunity rows — it is useful
description. It stops being a **join key**. One canonical column; other
vocabularies become attributes that map INTO it.

── Why `from_yahoo` takes the industry too ────────────────────────────────────
Four Yahoo sectors are irreducibly ambiguous against NSE's vocabulary:

    Industrials       -> Capital Goods | Construction | Services | Automobile...
    Basic Materials   -> Metals & Mining | Chemicals | Construction Materials...
    Consumer Cyclical -> Automobile | Consumer Durables | Consumer Services...
    Utilities         -> Power | Oil Gas & Consumable Fuels (gas distribution)

For those the SECTOR alone cannot decide, so `_BY_INDUSTRY` is consulted first
and the sector-level fallback is deliberately absent. An unresolvable pair
returns **None**, and None means UNMAPPED — never a nearest guess. That is the
same rule `nse_universe` already holds for its four unmapped labels ("unmapped
sectors are intentionally left as unscored rather than guessed, to avoid silently
misclassifying bias") and the reason a coverage number is worth trusting.

── The naming trap this module exists partly to contain ───────────────────────
`nse_universe.fetch_constituents` emits a key called **`industry`** whose values
are NSE's macro **SECTOR** labels (the CSV's column is named `Industry`).
`money_flow.sector_grid` groups on that key and correctly calls the result
`sector`. The name lies at the boundary. `symbol_map()` below returns
`{symbol: sector}` with the honest name, and every new caller should use it
rather than reaching for `r["industry"]`.

CLI:
    py -3 tools/sectors.py                    # canonical labels + coverage
    py -3 tools/sectors.py --universe niftytotalmarket
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Optional

log = logging.getLogger(__name__)

#: The canonical vocabulary. Sourced from NSE's constituent CSV rather than
#: invented here — this tuple is the union observed across the indices we track
#: (20 on nifty500; niftytotalmarket adds Forest Materials and Utilities), kept
#: explicit so a typo in a mapping table fails a test instead of inventing a
#: 23rd sector at runtime.
CANONICAL: tuple[str, ...] = (
    "Automobile and Auto Components",
    "Capital Goods",
    "Chemicals",
    "Construction",
    "Construction Materials",
    "Consumer Durables",
    "Consumer Services",
    "Diversified",
    "Fast Moving Consumer Goods",
    "Financial Services",
    "Forest Materials",
    "Healthcare",
    "Information Technology",
    "Media Entertainment & Publication",
    "Metals & Mining",
    "Oil Gas & Consumable Fuels",
    "Power",
    "Realty",
    "Services",
    "Telecommunication",
    "Textiles",
    "Utilities",
)

#: Yahoo SECTOR -> canonical, for the sectors where the mapping is unambiguous.
#: The four ambiguous ones are ABSENT on purpose (see the module docstring); do
#: not add them "for coverage" without an industry-level reason.
_BY_SECTOR: dict[str, str] = {
    "Healthcare": "Healthcare",
    "Technology": "Information Technology",
    "Financial Services": "Financial Services",
    "Real Estate": "Realty",
    "Energy": "Oil Gas & Consumable Fuels",
    "Consumer Defensive": "Fast Moving Consumer Goods",
    "Communication Services": "Telecommunication",
}

#: Yahoo INDUSTRY -> canonical. Consulted FIRST, so it both resolves the
#: ambiguous sectors and overrides a sector-level default where Yahoo's
#: hierarchy disagrees with NSE's (gas distribution is Utilities at Yahoo and
#: Oil Gas & Consumable Fuels at NSE; Solar is Technology at Yahoo and Capital
#: Goods at NSE).
_BY_INDUSTRY: dict[str, str] = {
    # Industrials
    "Aerospace & Defense": "Capital Goods",
    "Specialty Industrial Machinery": "Capital Goods",
    "Electrical Equipment & Parts": "Capital Goods",
    "Farm & Heavy Construction Machinery": "Capital Goods",
    "Metal Fabrication": "Capital Goods",
    "Tools & Accessories": "Capital Goods",
    "Building Products & Equipment": "Capital Goods",
    "Engineering & Construction": "Construction",
    "Conglomerates": "Diversified",
    "Specialty Business Services": "Services",
    "Staffing & Employment Services": "Services",
    "Consulting Services": "Services",
    "Railroads": "Services",
    "Marine Shipping": "Services",
    "Integrated Freight & Logistics": "Services",
    "Airlines": "Services",
    "Waste Management": "Services",
    "Security & Protection Services": "Services",
    # Basic Materials
    "Steel": "Metals & Mining",
    "Aluminum": "Metals & Mining",
    "Copper": "Metals & Mining",
    "Other Industrial Metals & Mining": "Metals & Mining",
    "Other Precious Metals & Mining": "Metals & Mining",
    "Gold": "Metals & Mining",
    "Coking Coal": "Metals & Mining",
    "Specialty Chemicals": "Chemicals",
    "Chemicals": "Chemicals",
    "Agricultural Inputs": "Chemicals",
    "Building Materials": "Construction Materials",
    "Paper & Paper Products": "Forest Materials",
    "Lumber & Wood Production": "Forest Materials",
    # Consumer Cyclical
    "Auto Manufacturers": "Automobile and Auto Components",
    "Auto Parts": "Automobile and Auto Components",
    "Auto & Truck Dealerships": "Automobile and Auto Components",
    "Recreational Vehicles": "Automobile and Auto Components",
    "Textile Manufacturing": "Textiles",
    "Apparel Manufacturing": "Textiles",
    "Footwear & Accessories": "Consumer Durables",
    "Furnishings, Fixtures & Appliances": "Consumer Durables",
    "Luxury Goods": "Consumer Durables",
    "Packaging & Containers": "Capital Goods",
    "Home Improvement Retail": "Consumer Services",
    "Specialty Retail": "Consumer Services",
    "Internet Retail": "Consumer Services",
    "Apparel Retail": "Consumer Services",
    "Restaurants": "Consumer Services",
    "Leisure": "Consumer Services",
    "Lodging": "Consumer Services",
    "Resorts & Casinos": "Consumer Services",
    "Travel Services": "Consumer Services",
    "Gambling": "Consumer Services",
    "Education & Training Services": "Consumer Services",
    # Consumer Defensive — sector default is FMCG; these are the exceptions
    "Discount Stores": "Consumer Services",
    "Food Distribution": "Consumer Services",
    "Grocery Stores": "Consumer Services",
    # Utilities — NSE splits gas distribution away from Power
    "Utilities - Regulated Electric": "Power",
    "Utilities - Independent Power Producers": "Power",
    "Utilities - Renewable": "Power",
    "Utilities - Diversified": "Power",
    "Utilities - Regulated Gas": "Oil Gas & Consumable Fuels",
    "Utilities - Regulated Water": "Utilities",
    # Energy
    "Thermal Coal": "Oil Gas & Consumable Fuels",
    # Technology / Communication overrides
    "Solar": "Capital Goods",
    "Consumer Electronics": "Consumer Durables",
    "Electronic Components": "Capital Goods",
    "Electronics & Computer Distribution": "Capital Goods",
    "Communication Equipment": "Telecommunication",
    "Telecom Services": "Telecommunication",
    "Entertainment": "Media Entertainment & Publication",
    "Broadcasting": "Media Entertainment & Publication",
    "Publishing": "Media Entertainment & Publication",
    "Advertising Agencies": "Media Entertainment & Publication",
    "Electronic Gaming & Multimedia": "Media Entertainment & Publication",
    # Real Estate
    "Real Estate - Development": "Realty",
    "Real Estate - Diversified": "Realty",
    "Real Estate Services": "Realty",
}


def is_canonical(label: str | None) -> bool:
    """True only for a label in the canonical vocabulary."""
    return bool(label) and label in CANONICAL


def from_yahoo(sector: str | None, industry: str | None = None) -> Optional[str]:
    """Map a Yahoo (sector, industry) pair onto the canonical vocabulary.

    Industry wins where both are known, because Yahoo's sector is too coarse for
    four of its own buckets and disagrees with NSE's hierarchy in a handful of
    named places. Returns **None** when the pair cannot be resolved — an honest
    hole, never a nearest guess.
    """
    ind = (industry or "").strip()
    if ind in _BY_INDUSTRY:
        return _BY_INDUSTRY[ind]
    sec = (sector or "").strip()
    return _BY_SECTOR.get(sec)


def symbol_map(universe: str = "nifty500") -> dict[str, str]:
    """`{symbol: canonical_sector}` straight from NSE's own constituent list.

    This is the honest-name replacement for reaching into
    `nse_universe.fetch_constituents()` and reading `r["industry"]`, which holds
    a SECTOR despite its name.
    """
    try:
        import nse_universe as nu
    except Exception as e:                                   # pragma: no cover
        log.warning("nse_universe unavailable: %s", e)
        return {}
    out: dict[str, str] = {}
    for r in nu.fetch_constituents(universe):
        label = (r.get("industry") or "").strip()   # NSE's CSV column, holds a sector
        sym = str(r.get("symbol") or "").strip()
        if sym and label:
            out[sym] = label
    return out


#: The universe the monthly cache is BUILT from. `niftytotalmarket` is the
#: broadest list NSE publishes as a CSV (~750 names), so it is the one that
#: makes a screener hit most likely to come back with a label. Narrower lists
#: are subsets of it and add nothing to the map.
CACHE_UNIVERSE = "niftytotalmarket"


def _db():
    """portfolio_db, imported lazily — this module must stay importable on a
    machine with no database (the CLI below is a pure vocabulary report)."""
    import portfolio_db as _pdb
    return _pdb


def refresh_cache(universe: str = CACHE_UNIVERSE,
                  period: str | None = None) -> int:
    """Fetch NSE's constituent list and write this month's map. Rows written.

    The one place that pays a network cost. Everything on the render path goes
    through `lookup`, which reads what this wrote.
    """
    pdb = _db()
    pdb.init_db()
    m = symbol_map(universe)
    if not m:
        log.warning("refresh_cache: NSE returned no constituents for %s", universe)
        return 0
    # A label NSE emits that this module does not recognise is stored AS ITSELF,
    # not dropped and not coerced. `coverage()` is what surfaces it as a number;
    # silently discarding it here would make the hole invisible on the one page
    # that exists to show holes.
    return pdb.save_sector_map(m, universe=universe, source="nse", period=period)


def lookup(symbols=None, period: str | None = None,
           universe: str = CACHE_UNIVERSE, refresh: bool = False) -> dict:
    """`{SYMBOL: canonical_sector_or_None}` — the desk's one sector accessor.

    Reads the monthly cache and refills it on a MISS, so the first render of a
    new month pays one NSE fetch and every render after it pays none. Pass
    `symbols` to narrow the result; omit it for the whole stored map.

    A symbol the cache has never seen (a listing outside NSE's broadest index,
    or a scanner hit from another source) is absent from the returned dict
    rather than present with a guessed label. Callers render that as BLANK —
    "no NSE macro sector for this name", which is the honest reading and the
    same one `cap_bucket` gives a name in none of its four index buckets.
    """
    try:
        # The import itself is inside the try: portfolio_db pulls in pandas, and
        # "the database module would not import" must degrade the same way "the
        # database was unreadable" does.
        pdb = _db()
        pdb.init_db()
        have = pdb.get_sector_map(period=period)
        if refresh or not have:
            refresh_cache(universe=universe, period=period)
            have = pdb.get_sector_map(period=period)
    except Exception as e:                                    # pragma: no cover
        # A screener table must still render when the cache is unreachable. A
        # missing sector column is a smaller failure than a blank page.
        log.warning("sector lookup unavailable: %s", e)
        return {}
    if symbols is None:
        return have
    out = {}
    for sym in symbols:
        s_ = str(sym).strip().upper()
        if s_ in have:
            out[s_] = have[s_]
    return out


def coverage(universe: str = "nifty500") -> dict[str, Any]:
    """How much of the universe carries a canonical sector, and what is unknown.

    `unknown` names labels NSE emitted that this module does not recognise —
    a new NSE label should surface here as a number, not as a silent bucket.
    """
    m = symbol_map(universe)
    unknown = sorted({v for v in m.values() if v not in CANONICAL})
    return {
        "universe": universe,
        "symbols": len(m),
        "labels": sorted(set(m.values())),
        "n_labels": len(set(m.values())),
        "unknown_labels": unknown,
        "canonical_pct": (round(100.0 * sum(1 for v in m.values() if v in CANONICAL)
                                / len(m), 1) if m else 0.0),
    }


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    ap = argparse.ArgumentParser(description="Canonical sector vocabulary (B-64)")
    ap.add_argument("--universe", default="nifty500")
    ap.add_argument("--refresh-cache", action="store_true",
                    help=f"fetch and store this month's map for {CACHE_UNIVERSE}")
    args = ap.parse_args()

    if args.refresh_cache:
        n = refresh_cache()
        import portfolio_db as _pdb
        print(f"sector_map: wrote {n} rows for {_pdb.current_period()} "
              f"({CACHE_UNIVERSE}); periods stored: "
              f"{', '.join(_pdb.sector_map_periods()) or 'none'}")
        return 0

    c = coverage(args.universe)
    print(f"Canonical sectors — {c['universe']}: {c['symbols']} symbols, "
          f"{c['n_labels']} labels, {c['canonical_pct']}% canonical")
    for label in c["labels"]:
        mark = " " if label in CANONICAL else " <- NOT IN CANONICAL"
        print(f"  {label}{mark}")
    if c["unknown_labels"]:
        print("\nUnrecognised NSE labels (add to CANONICAL after checking):")
        for u in c["unknown_labels"]:
            print(f"  {u}")
    print(f"\nYahoo mapping: {len(_BY_INDUSTRY)} industries, "
          f"{len(_BY_SECTOR)} sectors; ambiguous Yahoo sectors resolve by "
          f"industry or return None.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
