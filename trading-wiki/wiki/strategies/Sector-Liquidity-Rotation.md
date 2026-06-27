---
title: "Sector Liquidity Rotation (FII/DII Flow Tracking)"
category: strategy
tags: [sectors, FII, DII, institutional-flow, screener, rotation]
timeframe: position
created: 2026-06-20
updated: 2026-06-20
sources: 0
related: [strategies/Screener-Queries.md, analyses/Sector-Watchlist.md, analyses/Sector-Rotation-Tool-Architecture.md]
---

# Sector Liquidity Rotation (FII/DII Flow Tracking)

## Core Idea
Detect which stocks recently had a meaningful change in FII (or DII) holding %, trace those stocks back to their sector, and aggregate the flow **weighted by market cap** (not raw stock count) to rank which sectors institutions are rotating into or out of. Combine that flow signal with the sector index's trailing-1Y price trend to form a directional bias, rather than treating institutional buying as bullish in isolation.

## Setup Criteria
Screener.in query (base):
```
Market Capitalization > 1000 AND
Current price > 30 AND
(Change in FII holding > 0.5 OR Change in FII holding < -0.5)
```
- Threshold widened from the original draft's `> 0.1%` — 0.1% is noise-level; 0.5% filters for moves likely to reflect deliberate institutional repositioning.
- Bidirectional clause (`> 0.5 OR < -0.5`) on purpose: rotation means money leaving one sector and entering another, so both inflow and outflow sectors must be visible in the same pass.
- Must add **Industry** as a visible column (Edit Columns) before exporting — the per-sector counts shown in the Industry filter dropdown are UI-only and aren't in the raw CSV/XLSX export.

## Entry Rules
Not a single-stock entry trigger — this is a sector-level radar. Use the top-ranked sector(s) as a candidate pool, then apply a stock-level system ([[strategies/TechnoFunda-Swing]] or [[strategies/VCPBot-Trend-Template]]) for actual entries within that sector.

## Exit Rules (profit target + stop loss)
N/A at sector level — inherited from whichever stock-level strategy is applied within the selected sector.

## Timeframe
Position / swing — FII/DII holding disclosures are quarterly, so this is a slow, regime-level signal, not a day-to-day trigger.

## Best Market Conditions
Works best when sector rotation is actually occurring (e.g. broad market consolidation while leadership rotates between sectors) rather than a single-direction trending market where everything moves together.

## Worst Market Conditions
Low signal value during broad risk-off/risk-on moves where FII flow is uniformly negative/positive across all sectors — the cross-sector ranking degenerates to noise.

## Methodology — Rotation Bias Classification
| FII flow (cap-weighted) | Sector index 1Y trend | Bias |
|---|---|---|
| Inflow | Rising | Confirmed bullish rotation |
| Inflow | Falling | Early accumulation / contrarian watch |
| Outflow | Rising | Distribution into strength (caution) |
| Outflow | Falling | Confirmed bearish rotation |

## Tooling
[tools/sector_rotation.py](../../tools/sector_rotation.py):
1. Reads a screener.in export (CSV/XLSX) with Industry, Market Cap, and Change in FII holding % columns.
2. Aggregates `Change in FII holding % × Market Cap` per sector, normalized by total sector market cap → `fii_rotation_score`.
3. Pulls trailing-1Y return for each sector's NSE index proxy via yfinance (`SECTOR_INDEX_MAP` — extend as new Industry labels appear in exports).
4. Classifies bias per the table above, exports a colour-coded `sector_rotation_YYYYMMDD.xlsx` ranked by rotation score.

Run manually until a fresh FII/DII export is available:
```
py -3 tools/sector_rotation.py path/to/export.csv
```
Not yet wired into the scheduled [tools/screener_pipeline.py](../../tools/screener_pipeline.py) run — screener.in requires an authenticated session and blocks unauthenticated/automated fetches (confirmed 2026-06-20), so the export step stays manual for now.

## Backtest / Track Record
None yet — new strategy, no live track record.

## Examples
None yet — pending first real export run (2026-06-20 screener URL returned 435 results across categories incl. Industrial Products-38, Pharmaceuticals & Biotechnology-32, Finance-30, Auto Components-25, Electrical Equipment-23).

## Related Concepts
- [[strategies/Screener-Queries]] — source query library, including the "Re-Rating Candidates" query that also uses promoter+DII+FII holding change
- [[analyses/Sector-Watchlist]] — static sector/stock lists this can validate or contradict with live flow data
- [[analyses/Sector-Rotation-Tool-Architecture]] — detailed tool internals (aggregation formula, bias classification, known limitations)
- [[sources/SwingEdge-Sector-Momentum-Map-20260622]] — an independent, third-party sector-rotation read using the same Leading/Improving/Weakening/Lagging quadrant naming, but computed purely from price relative-strength (3mo RS vs Nifty 500 × recent pace) rather than FII/DII flow. Worth running side-by-side against this tool's output on a shared sector list — agreement reinforces a call, divergence (e.g. FII inflow into a sector still "Weakening" on pure price RS) is itself a signal, since institutional accumulation often precedes price strength.

## Sources
- User-drafted screener query, refined 2026-06-20
- [[sources/SwingEdge-Sector-Momentum-Map-20260622]] (2026-06-22) — cross-reference source, not an input to this strategy's own data pipeline
