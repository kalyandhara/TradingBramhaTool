---
title: "CANSLIM Method"
category: concept
tags: [fundamental, growth-stocks, William-ONeil, screener]
created: 2026-06-14
updated: 2026-06-14
sources: 1
related: [strategies/Screener-Queries.md, concepts/Darvas-Box.md]
---

# CANSLIM Method

## Definition
Stock selection method by William O'Neil combining fundamental growth criteria with technical momentum. Each letter = one criterion.

## The 7 Criteria
- **C** — Current Earnings (EPS growth latest quarter vs prior year quarter > 25%)
- **A** — Annual Earnings (3-year EPS growth > 20%)
- **N** — New (new products, services, management, or price highs)
- **S** — Supply & Demand (low float, high volume on up days)
- **L** — Leaders (buy leaders in the sector, not laggards)
- **I** — Institutional Investors (increasing FII/DII holding)
- **M** — Market trend (only buy in confirmed uptrend)

## Core Screener Query (Screener.in)
```
EPS latest quarter > 1.25 * EPS preceding year quarter AND
EPS growth 3Years > 20 AND
Promoter holding > 65 AND
Return over 1year > 30 AND
FII holding + DII holding > 5 AND
FII holding + DII holding < 15 AND
Market Capitalization > 5000
```

## CANSLIM Model (Advanced — 21 Scanners Version)
```
EPS latest quarter > 1.15 * EPS preceding year quarter AND
EPS > 1.20 * EPS last year AND
EPS last year > EPS preceding year AND
YOY Quarterly sales growth > 15 AND
Profit growth > 15 AND Sales growth > 15 AND
YOY Quarterly profit growth > 16 AND
Return on equity > 15 AND
Debt to equity < 2 AND
Market Capitalization > 10 AND
Down from 52w high <= 10
```

## Key Insight
Down from 52-week high <= 10% means the stock is near ATH — CANSLIM only buys strength, not value traps.

## Related
- [[strategies/Screener-Queries]] — Full list of all 21 scanner variants
- [[concepts/Darvas-Box]] — DarvaX often finds the same stocks CANSLIM identifies
