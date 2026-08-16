---
source_url: https://web.stockedge.com/company-filings
fetched: 2026-08-11
---

# StockEdge Company Filings — Raw Snapshot (11 Aug 2026)

## Page Title
"List of Shares Annual Report | Bonus | Stock Split | Buyback"

## FAQ Content

**Importance of Company Filings:**
"Company filings are decisions taken by the companies which has to be reported to the exchange. It helps you to be updated with the latest happenings in the corporate world and enables you to take investment or trading decisions wisely. They affect the stock prices and hence one should be aware of these filings."

**Frequency of updation:**
"Company filings are updated & classified at regular intervals throughout the day."

**Disclosure:**
"Categorisation done by using in house algorithm."

## Filing Categories — Partial Capture (A–E, 30 of ~50+ categories)

Note: The list uses virtual scrolling with per-page API loading (pageSize=10, paginated). Full list capture failed due to virtual DOM rendering — ArrowDown navigation caused page redirect. 30 categories captured via DOM snapshots; remainder estimated from alphabetical ordering and page title.

### Confirmed Categories (captured from DOM, alphabetical order)
1. Acquisition
2. Annual General Meeting
3. Annual Report
4. Annual Secretarial Compliance Report
5. Appointment/Change in Auditor
6. Appointment/Change in Key Personnel
7. Appointment/Change in Registrar & Transfer Agent
8. Assets & Liabilities Statement
9. Board Meeting
10. Bonus
11. Business/Operational Update
12. Buyback
13. Call Money/Forfeiture
14. Capital Reduction
15. Certificate/Document - Debenture Trustee
16. Change in Company Detail
17. Clarification Sought
18. Committee/Creditors Meeting
19. Compliance Certificate/Report
20. Conference Call/Investor Meet
21. Consolidation of Shares
22. Coronavirus
23. Credit Rating
24. Default/Delay on Payment
25. Delisting
26. Demerger/Merger
27. Disclosure/Information
28. Disinvestment/Diversification
29. Dividend/Interest/Redemption
30. Earnings/Investor Presentation

### Categories Confirmed from Page Title (not yet captured alphabetically)
- Stock Split (mentioned in page title)
- Buyback (confirmed in list above, #12)
- Annual Report (confirmed in list above, #3)
- Bonus (confirmed in list above, #10)

## API Architecture
- Endpoint: https://api.stockedge.com/Api/CorporateAnnouncementCategoriesDashboardApi/GetCategories
- Parameters: page={n}&pageSize=10&lang=en
- Pages loaded on initial render: page=1, 2, 3 (confirmed via network requests)
- Categories are assigned icon IDs; SVG icons at /assets/img/light/corporate-announcements/{id}.svg
- Icon IDs observed in network: 1, 2, 3, 10, 11, 17, 21, 23, 24, 26, 27, 28, 29, 30, 31, 32, 34, 43, 72, 75, 79, 81 (suggesting ~80+ total icon slots, not all in use)
