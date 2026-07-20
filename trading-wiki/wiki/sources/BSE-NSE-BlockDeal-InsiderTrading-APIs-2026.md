---
title: "BSE + NSE — block deal, bulk deal, and insider trading data sources (confirmed working)"
category: source
tags: [bse, nse, api, block-deal, bulk-deal, insider-trading, sast, data-source]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related:
  - sources/BSEIndia-Public-API-Corporate-Data-2026.md
  - concepts/Order-Flow.md
  - strategies/Drop-Recovery-Reversal-Screen.md
---

# BSE + NSE — Block Deal, Bulk Deal & Insider Trading Data Sources

## Metadata
- Ingest trigger: Kalyan asked how to get block deal / insider trading data from bseindia.com and nseindia.com, directly following the earlier bseindia.com API ingest
- Method: same JS-bundle reverse-engineering technique as the prior BSE ingest for BSE; for NSE, tested both the interactive API (already known from `tools/nse_shareholding_fetch.py` to be blocked from this sandbox) and NSE's separate static-archive subdomain

## Key Takeaways

- **BSE: all 3 confirmed live and working, whole-market, no auth**:
  - `https://api.bseindia.com/BseIndiaAPI/api/BulkDeal_Beta/w` — today's bulk deals across the entire exchange, no parameters needed. Verified live (2026-07-02): real deals, e.g. ICICI Prudential Mutual Fund buying 1.3 crore shares of AWL at ₹180.10.
  - `https://api.bseindia.com/BseIndiaAPI/api/BlockDeal_Beta/w` — same shape, block deals.
  - `https://api.bseindia.com/BseIndiaAPI/api/InsiderTrade15/w?fromdt=DD/MM/YYYY&todt=DD/MM/YYYY&pageno=1&scripcode=` — SEBI PIT Regulation 7(2) insider-trading disclosures, whole market when `scripcode` is left blank. Verified live: promoter name, PAN, % shareholding before/after, transaction type, exchange, company name — genuinely comprehensive.
- **NSE: bulk/block deals confirmed working via a different route than the (blocked) interactive API** — `tools/nse_shareholding_fetch.py` already documented that this sandbox gets a flat IP-level block from NSE's Akamai CDN on `www.nseindia.com` (confirmed again here: even the homepage returned an Access-Denied-style page). But NSE's **static archive subdomain** (`archives.nseindia.com`, the same one `screener_pipeline.py`'s bhavcopy fetcher already uses successfully) is **not** behind that protection:
  - `https://archives.nseindia.com/content/equities/bulk.csv` — today's bulk deals, plain CSV (Date/Symbol/Security Name/Client Name/Buy-Sell/Quantity/Price). Confirmed working live from this same blocked-for-everything-else sandbox.
  - `https://archives.nseindia.com/content/equities/block.csv` — same shape for block deals (returned "NO RECORDS" on the test date — a normal empty-day response, not an error).
- **NSE insider trading: not found via static archive** — guessed paths (`sast.csv`, `insider_trading.csv`, `pit.csv`) all 404'd. NSE's insider-trading/SAST disclosures likely only exist behind the blocked interactive API (the same `www.nseindia.com/api/...` family `nse_shareholding_fetch.py` already flags as "untested against live NSE — this sandbox's IP is blocked... can only be validated from a real home/office IP"). Not resolved here; would need testing from the user's actual machine, not this sandbox.

## Detailed Notes

The BSE/NSE contrast here is the same "interactive API vs. static archive" split already implicit in this project's existing NSE tooling: `screener_pipeline.fetch_bhavcopy_top_volume()` works today because it targets `nsearchives.nseindia.com`, not `www.nseindia.com`. This ingest confirms the same split applies to bulk/block deals specifically (`archives.nseindia.com`, a sibling static subdomain, also unprotected) — meaning **NSE quietly publishes several market-wide reports as plain files with no bot protection**, while anything requiring the interactive site's JS-driven API is walled off. Worth checking whether other `archives.nseindia.com/content/equities/*.csv` paths exist for further reports (short-selling, F&O ban list — `fo_secban.csv` confirmed to exist and work too, found opportunistically while testing).

BSE's insider-trading endpoint takes a date range and an optional scrip code — leaving `scripcode` blank returns everything, which is what makes it a genuine whole-market feed rather than a per-stock lookup requiring 2,000+ individual calls.

## Actionable Insights

- **A "Smart Money Confirmation" signal is now buildable**: cross-reference a stock showing up in NSE/BSE's bulk-deal or insider-trading feed (especially a *buy* by an institution or promoter) with any of this project's existing technical scanners — e.g. a stock the Early Reversal Detector already flagged, corroborated by a same-week institutional bulk-deal buy or an insider acquisition, is a materially stronger signal than either alone. Not built — a natural next scanner-composite candidate, same shape as combining %R Trend Exhaustion + candlestick + structure earlier today.
- **BSE is the more complete, easier source for insider trading specifically** — confirmed working with zero auth from this environment; NSE's equivalent needs testing from a real (non-sandboxed) IP before it can be relied on.
- **Both bulk-deal feeds (BSE + NSE) are whole-market and free** — worth pulling both and reconciling by symbol, since a stock can be dual-listed and a bulk deal might route through either exchange.
- **`archives.nseindia.com` deserves a broader inventory pass** — this ingest found 3 useful paths (`bulk.csv`, `block.csv`, `fo_secban.csv`) just by pattern-guessing from the bhavcopy URL convention; a more systematic search (checking NSE's own "Reports" download page for the full file-name list) would likely surface more free, unauthenticated market-wide data.

## Contradictions with Existing Wiki

None — extends and confirms the existing `nse_shareholding_fetch.py` finding (interactive NSE API blocked from this sandbox) rather than contradicting it, while adding the new finding that NSE's static archive subdomain is a working alternative for at least these two report types.

## Pages Updated

None yet — findings recorded for a future addition to `tools/screener_pipeline.py` or a new dedicated module, not yet implemented.
