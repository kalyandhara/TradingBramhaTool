---
title: "StockEdge Company Filings — Category Catalog, 11 Aug 2026"
category: source
tags: [company-filings, corporate-announcements, india-markets, stockedge, nse, bse, exchange-filings]
created: 2026-08-11
updated: 2026-08-11
sources: 1
related:
  - sources/StockEdge-Markets-Dashboard-2026-08-11.md
  - sources/StockEdge-Investment-Themes-2026-08-11.md
---

# Web Snapshot — StockEdge Company Filings (11 Aug 2026)

## Metadata
- **Source:** https://web.stockedge.com/company-filings
- **Date:** 11 Aug 2026
- **Page title:** "List of Shares Annual Report | Bonus | Stock Split | Buyback"
- **Platform description:** Classified corporate announcements filed with NSE/BSE exchanges
- **Update frequency:** "Updated & classified at regular intervals throughout the day" (intraday, not EOD)
- **Categorisation method:** "In house algorithm" (automated classification)

---

## Key Takeaways

1. **Exchange-filing aggregator, not a screener.** Company Filings shows what companies have formally reported to BSE/NSE. These are regulatory disclosures — board meetings, results, bonuses, buybacks, mergers — not signals or recommendations. The value is speed (intraday updates) and classification (automated sorting into ~50 categories).

2. **Intraday update cadence** distinguishes it from every other StockEdge feature captured so far. Markets snapshot is EOD; Chart Patterns EOD; Trading Strategies EOD; Investment Themes static. Company Filings updates throughout the trading day. This makes it the platform's real-time event feed.

3. **~50+ filing categories** covering the full regulatory disclosure universe: corporate actions (Bonus, Buyback, Stock Split, Rights Issue), governance (Board Meeting, AGM, Auditor changes), financials (Annual Report, Assets & Liabilities), credit events (Default/Delay on Payment, Credit Rating), and M&A (Demerger/Merger, Acquisition, Delisting).

4. **"Coronavirus" as a standing category** — a pandemic-era category that was apparently never deprecated. Its presence in the list (alongside Credit Rating, Delisting, etc.) is an artifact of the 2020-era exchange filing surge. Signals that the category taxonomy was built organically during high-disclosure periods.

5. **Categorisation is algorithmic** ("in house algorithm") — same as Chart Patterns. StockEdge classifies filings automatically rather than manually tagging. This means the category a filing lands in is a best-guess, not a human editorial decision.

---

## Filing Category Catalog (Partial — A through E captured)

> [!gap] Partial capture
> Virtual scrolling + session fragility prevented full list extraction. 30 of an estimated 50+ categories captured (A–E alphabetically). Page title confirms: Annual Report, Bonus, Stock Split, Buyback are all present. The API paginates at pageSize=10; at least 3 pages confirmed loaded on initial render.

| # | Category | Notes |
|---|----------|-------|
| 1 | Acquisition | Corporate M&A — company buys another |
| 2 | Annual General Meeting | AGM notices and outcomes |
| 3 | Annual Report | Full-year financial report |
| 4 | Annual Secretarial Compliance Report | Regulatory compliance (SEBI listing obligations) |
| 5 | Appointment/Change in Auditor | Statutory auditor changes — high signal for governance concern |
| 6 | Appointment/Change in Key Personnel | CEO/CFO/Director changes |
| 7 | Appointment/Change in Registrar & Transfer Agent | RTA changes — operational, low price impact |
| 8 | Assets & Liabilities Statement | Interim financial position disclosure |
| 9 | Board Meeting | Board meeting notices and outcomes |
| 10 | Bonus | Bonus share issuance (stock dividend) — typically bullish catalyst |
| 11 | Business/Operational Update | Informal operational updates, order wins, partnerships |
| 12 | Buyback | Share repurchase — typically bullish; reduces float |
| 13 | Call Money/Forfeiture | Partly-paid share calls; rare in large caps |
| 14 | Capital Reduction | Share count reduction; can signal restructuring |
| 15 | Certificate/Document - Debenture Trustee | Debt compliance; relevant for bond issuers |
| 16 | Change in Company Detail | Name, address, or registered office changes |
| 17 | Clarification Sought | Exchange queries to the company — watch for price-sensitive context |
| 18 | Committee/Creditors Meeting | Insolvency / restructuring proceedings |
| 19 | Compliance Certificate/Report | Periodic regulatory compliance certificates |
| 20 | Conference Call/Investor Meet | Investor relations — often post-result calls |
| 21 | Consolidation of Shares | Reverse stock split |
| 22 | Coronavirus | COVID-era disclosures — legacy category, still in system |
| 23 | Credit Rating | Rating agency actions — significant for debt-heavy companies |
| 24 | Default/Delay on Payment | Payment defaults — high-severity event, distress signal |
| 25 | Delisting | Company being removed from exchange |
| 26 | Demerger/Merger | Structural M&A events |
| 27 | Disclosure/Information | General disclosures; catch-all |
| 28 | Disinvestment/Diversification | Government disinvestment or business exits |
| 29 | Dividend/Interest/Redemption | Dividend declarations, bond interest, debenture redemptions |
| 30 | Earnings/Investor Presentation | Quarterly result presentations |
| … | *(Additional categories F–Z not captured — see note above)* | Likely includes: ESOP, Financial Results, Fund Raising, Insider Trading, IPO, Litigation/Legal, Postal Ballot, Preferential Allotment, Related Party Transactions, Rights Issue, Scheme of Arrangement, Shareholding Pattern, Stock Split, Suspension, Takeover, and others |

---

## Platform Architecture Notes

- **API:** `https://api.stockedge.com/Api/CorporateAnnouncementCategoriesDashboardApi/GetCategories?page={n}&pageSize=10&lang=en`
- **Render:** Virtual scrolling list — items load as the user scrolls, not all at once in the DOM. Standard Playwright DOM queries return empty until the Angular component mounts (~2–3 seconds after navigation).
- **Icons:** Each category has a numeric icon ID (`/assets/img/light/corporate-announcements/{id}.svg`). Icon IDs confirmed from network: 1, 2, 3, 10, 11, 17, 21, 23–34, 43, 72, 75, 79, 81. Non-contiguous IDs suggest some categories were removed or reorganised.
- **Session behaviour:** The page shows full content when arriving from `/app/markets` but drops auth on direct URL navigation from unauthenticated pages. Same fragility as `/trading-strategies` sub-pages.
- **Update model:** Intraday, unlike all other StockEdge features captured (which are EOD). This is the platform's event feed, not an analytics engine.

---

## Actionable Insights

- **High-signal categories for traders**: Bonus (bullish, float-neutral at first glance but typically followed by price pop), Buyback (bullish, direct floor bid), Default/Delay on Payment (severe distress), Delisting (event risk), Clarification Sought (exchange query = news ahead), Credit Rating (watch for downgrades).
- **Use in conjunction with Markets Dashboard**: The [[sources/StockEdge-Markets-Dashboard-2026-08-11]] captures today's top movers. If CPCL (+15%) had filed a Business/Operational Update today (e.g., confirming crude offtake from alternative routes), that would appear in this feed. The Markets Dashboard shows price outcome; Company Filings shows the underlying filing trigger.
- **"Clarification Sought" = early warning**: When NSE/BSE queries a company, the filing appears here before any news story. This category is disproportionately worth watching for outsized moves.

---

## Pages Updated
- [[log]] — appended
- [[index]] — updated
