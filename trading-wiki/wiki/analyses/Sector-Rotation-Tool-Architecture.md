---
title: "Sector Rotation Tool Architecture — sector_rotation.py"
category: analysis
tags: [python, tooling, sectors, FII, DII, institutional-flow, architecture]
created: 2026-06-20
updated: 2026-06-20
related: [strategies/Sector-Liquidity-Rotation.md, strategies/Screener-Queries.md, analyses/Sector-Watchlist.md]
timeframe: n/a
sources: 0
---

# Sector Rotation Tool Architecture — sector_rotation.py

> Source: tools/sector_rotation.py (built 2026-06-20). See [[strategies/Sector-Liquidity-Rotation]] for the trading strategy this tool implements.

## Overview
Standalone script that converts a stock-level FII/DII holding-change export into a ranked, sector-level institutional rotation signal, cross-checked against each sector's trailing-1Y price trend. Not yet wired into the scheduled [tools/screener_pipeline.py](../../tools/screener_pipeline.py) run — input currently requires a manual screener.in export (see [[strategies/Sector-Liquidity-Rotation]] for why: screener.in blocks unauthenticated/automated fetches).

## Tech Stack
- **pandas** — aggregation
- **yfinance** — sector index trailing-1Y price data (free, no API key)
- **openpyxl** — colour-coded Excel export

## Pipeline Steps

### Step 1 — `load_export()`
Reads a screener.in CSV/XLSX export. Column-name matching is fuzzy (substring match on "FII"+"Hold", "Mar Cap"/"Market Cap", "Industry"/"Sector") so it tolerates minor header variations across screener.in export versions. Hard-fails with a clear message if Industry, Market Cap, or FII-holding-change columns are missing — Industry is not in the default export and must be added via Edit Columns first.

### Step 2 — `aggregate_by_sector()`
Computes `weighted_fii = fii_chg × mar_cap` per stock, sums both within each Industry group, then:
```
fii_rotation_score = Σ(weighted_fii) / Σ(mar_cap)
```
This is the market-cap-weighted average FII holding change for the sector — deliberately not a simple average or raw stock count, since a sector could otherwise top the rankings purely because more small-caps happened to clear the screener threshold (the count-only flaw originally noted when reviewing the screener UI's Industry filter dropdown).

### Step 3 — `fetch_sector_index_1y_return()`
For each sector with a mapped index ticker (`SECTOR_INDEX_MAP`), pulls 1Y daily closes via yfinance and computes simple first-to-last return. Sectors without a mapped ticker get `None` and are marked "unscored" downstream — `SECTOR_INDEX_MAP` is intentionally partial and expected to grow as new Industry labels appear in real exports.

### Step 4 — `classify_bias()`
4-way classification crossing FII flow direction with index trend direction:
| FII flow | Index trend | Bias |
|---|---|---|
| Inflow (+) | Rising | confirmed bullish rotation |
| Inflow (+) | Falling | early accumulation / contrarian watch |
| Outflow (-) | Rising | distribution into strength (caution) |
| Outflow (-) | Falling | confirmed bearish rotation |

### Step 5 — Excel export
`sector_rotation_<date>.xlsx`, one sheet, sorted by `fii_rotation_score` descending. Bias column colour-coded (green/amber/amber/red matching the 4 classes), column widths auto-sized — same visual style as `screener_pipeline.py`'s `_style_sheet()` for consistency across the vault's tools.

## Known Limitations
- `SECTOR_INDEX_MAP` is a small seed list (14 entries) hand-mapped from the screener screenshot's Industry filter dropdown on 2026-06-20 — will need extending as new sectors surface in real exports.
- Sector index proxies are NSE sectoral indices (`^CNXxxx` / `^NSEBANK`); some screener.in Industry labels map crudely to the nearest available index (e.g. both "Electrical Equipment" and "Cement & Cement Products" fall back to `^CNXINFRA`/`^CNXFMCG` respectively) since NSE doesn't publish an index for every granular Industry category.
- No backtest yet — first real run pending a screener.in export with Industry column added (manual step, not yet automated).
- A parallel free/no-login data path was attempted in [tools/nse_shareholding_fetch.py](../../tools/nse_shareholding_fetch.py) (NSE XBRL shareholding-pattern scrape) but is unvalidated — this sandbox's IP is blocked by NSE's Akamai CDN, so it can only be tested from the user's real machine.

## Related
- [[strategies/Sector-Liquidity-Rotation]] — the trading strategy and methodology this tool implements
- [[strategies/Screener-Queries]] — source query library (query #7 Re-Rating Candidates uses related FII/DII holding-change logic)
- [[analyses/Sector-Watchlist]] — static sector/stock lists this tool's live output can validate or contradict
- [[analyses/VCPBot-Architecture]] — comparable tool-architecture documentation pattern followed here
