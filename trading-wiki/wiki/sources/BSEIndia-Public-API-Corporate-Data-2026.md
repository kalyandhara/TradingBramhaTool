---
title: "bseindia.com — undocumented public API for announcements, corporate actions, and shareholding pattern (incl. pledge %)"
category: source
tags: [bse, api, corporate-announcements, corporate-actions, shareholding-pattern, pledge, data-source]
created: 2026-07-02
updated: 2026-07-02
sources: 1
related:
  - strategies/Drop-Recovery-Reversal-Screen.md
---

# bseindia.com — Public API for Corporate Announcements, Actions & Shareholding Pattern

## Metadata
- Site: https://www.bseindia.com/ (BSE's Angular SPA frontend calls a separate API host, `api.bseindia.com`)
- Ingest trigger: Kalyan asked to ingest bseindia.com; scope narrowed via clarifying question to corporate announcements/actions data specifically
- Method: reverse-engineered from BSE's own minified frontend JS bundle (`main-*.js`), same technique used earlier this session for screener.in's `/api/ratio/search/` and `/screen/raw/` endpoints — found the internal API path names in the bundle, then tested them directly with `curl`

## Key Takeaways

- **Confirmed three genuine, public, unauthenticated JSON API endpoints on `api.bseindia.com/BseIndiaAPI/api/`** (all tested live, all returned real data for Reliance Industries, scripcode 500325):
  1. **`AnnSubCategoryGetData/w`** — corporate announcements list, filterable by scrip code and date range. Returns headline, category/subcategory, full text, PDF attachment link, and a direct BSE stock-page URL per announcement.
  2. **`CorporateAction/w`** — dividend history, bonus issue history, and a combined corporate-actions table (record date, ex-date, purpose, payment date) — verified against Reliance's actual known dividend/bonus history.
  3. **`CorporatesSHPSecuritybeta/w`** — full shareholding pattern breakdown (Promoter/Public/etc. categories, number of shares, % of total, voting rights) **including a literal `Fld_PledgeEncumberedPercentage` field** — a real numeric promoter-pledge percentage, plus `Fld_IsPledge` (boolean) and `Fld_PledgeEncumberedNoOfShares`.
- **This directly closes a data gap hit earlier this session.** When building the Pre-Breakout Screener's pledge/cash-flow safety filter, screener.in was confirmed to have no pledge-percentage field at all (its `/api/ratio/search/` returned zero results for "surprise" and pledge required its own confirmation via `Pledged percentage` — that one *did* exist, but needed a paid/logged-in query). BSE's `CorporatesSHPSecuritybeta` endpoint gives the same data — for free, with no login — directly from the shareholding-pattern regulatory filing itself, not a third-party aggregator.
- **Not yet solved**: mapping an NSE trading symbol (e.g. `RELIANCE`) to BSE's internal `scripcode` (e.g. `500325`) programmatically. A `ListScripSmartSearch_ng/w` endpoint exists in the bundle but the first parameter guess (`Type=EQ&text=...`) didn't return data — needs another round of reverse-engineering, or a static NSE-symbol↔BSE-scripcode mapping table (BSE publishes an "Equity" scrip master list as a downloadable file, not yet checked here).

## Detailed Notes

All three endpoints require an `Origin: https://www.bseindia.com` and/or `Referer` header to avoid a 302 redirect to an error page — no cookie or session token needed, unlike the screener.in flow which needs an authenticated `sessionid`. This makes BSE's data meaningfully easier to automate than screener.in for the fields it covers.

Example working calls (verified live 2026-07-02):
```
GET https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w
    ?pageno=1&strCat=-1&strPrevDate=YYYYMMDD&strScrip={bse_scripcode}
    &strSearch=P&strToDate=YYYYMMDD&strType=C&subcategory=-1

GET https://api.bseindia.com/BseIndiaAPI/api/CorporateAction/w
    ?scripcode={bse_scripcode}&Fdate=&TDate=&ddlcategry=

GET https://api.bseindia.com/BseIndiaAPI/api/CorporatesSHPSecuritybeta/w
    ?scripcode={bse_scripcode}&halfyear=&YrDate=
```
All three require the two headers above; response is straight JSON (the announcements/actions calls), or JSON with an embedded pre-rendered HTML table string for at least one sibling endpoint (`shpSecSummery_New`) — the `CorporatesSHPSecuritybeta` endpoint used for the pledge figure returns clean structured JSON, not HTML.

This is the same class of finding as the screener.in `/api/ratio/search/` and `/screen/raw/` discoveries from earlier this session — an internal API meant for a site's own frontend, not published as a developer API, found by reading the frontend's own JS bundle rather than guessing. Same caveat applies: undocumented APIs can change without notice; this isn't a stable, versioned public contract the way NSE's officially-published bhavcopy file is.

## Actionable Insights

- **Upgrade the Pre-Breakout Screener's pledge filter** (`tools/screener_scraper.py`, `fetch_fundamental_safe_symbols`) to use BSE's `CorporatesSHPSecuritybeta` endpoint instead of (or alongside) screener.in's `Pledged percentage` field — no login/cookie needed, and it's the primary regulatory-filing source rather than a third-party recomputation.
- **Solve the NSE-symbol → BSE-scripcode mapping** as a prerequisite — either find BSE's scrip-master download (a bhavcopy-equivalent full list, likely on bseindia.com's markets-data section) or properly reverse-engineer `ListScripSmartSearch_ng/w`'s actual parameter contract.
- **`CorporateAction/w`** is a genuine alternative/cross-check for dividend and bonus/split history — this project doesn't currently have a dedicated corporate-actions data source; could feed into position-sizing adjustments (e.g. auto-detecting a stock's price drop is a dividend ex-date artifact, not a real decline) — directly relevant to the Drop-Recovery-Reversal-Screen and Early Reversal Detector built earlier today, which currently have no such adjustment and could misread an ex-dividend gap as a "drop."
- **`AnnSubCategoryGetData/w`** could feed a "recent material announcement" flag into any of this project's scanners (e.g. don't trust a technical reversal signal that coincides with an unexplained corporate announcement) — not built, just noted as a candidate.

## Contradictions with Existing Wiki

None directly, but it materially changes the pledge-data story from earlier today's Pre-Breakout Screener build, which treated screener.in as the only viable pledge-percentage source (Chartink confirmed to have none). BSE's API is a better option for that specific field.

## Pages Updated

None yet — findings recorded for a future follow-up to `tools/screener_scraper.py`, not yet implemented.

## Follow-Up

[[sources/BSE-NSE-BlockDeal-InsiderTrading-APIs-2026]] (2026-07-02) extends this same reverse-engineering approach to block deals, bulk deals, and insider trading on both BSE and NSE.
