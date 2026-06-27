---
title: "Master Screener Query Library"
category: strategy
tags: [screener, fundamental, indian-markets, chartink, screener-in]
timeframe: position
created: 2026-06-14
updated: 2026-06-15
sources: 2
related: [concepts/CANSLIM.md, strategies/TechnoFunda-Swing.md, concepts/Darvas-Box.md, concepts/CCI.md, concepts/VCP.md, sources/Chartink-Atlas-Nimblr-Dashboard.md]
---

# Master Screener Query Library

> All queries for Screener.in unless otherwise noted.

## Fundamental Quality Screens

### 1. Blockbuster Quarterly Results
Goal: Exceptional quarterly performance likely to catch market attention.
```
Market Cap 200–100000 AND YOY Q sales growth > 20 AND
YOY Q profit growth > YOY Q sales growth AND
OPM latest Q > OPM 5Y AND
Other income latest Q < Other income preceding year Q * 2 AND
PE < YoY Q Profit Growth
```

### 2. Quarterly Profit Growers
```
Net Profit latest Q > Net Profit preceding Q AND
Net Profit preceding Q > Net profit 2Q back AND
Net profit 2Q back > Net profit 3Q back AND
Net Profit latest Q > Net Profit preceding year Q AND
Market Cap > 500
```

### 3. Turnaround Framework
```
(Net Profit latest Q > 0 OR Net Profit latest Q > Net Profit preceding Q) AND
(Net Profit preceding Q < 0 OR Net Profit preceding year Q < 0 OR
Net Profit preceding year < 0 OR Profit growth 3Y < -5) AND
Market Cap > 500 AND Public holding < 50 AND Pledged % < 10 AND
D/E < 1 AND OPM latest Q > OPM last year AND ROE > 0
```

### 4. GARP (Growth at Reasonable Price)
```
Market Cap > 500 AND Sales > 500 AND
Sales growth > 15 AND Sales growth 3Y > 15 AND Sales growth 5Y > 15 AND
EPS / EPS last year > 1.15 AND EPS growth 3Y > 15 AND EPS growth 5Y > 15 AND
Expected Q net profit > Net profit 3Q back
```

### 5. Volume Accumulation (Smart Money)
```
(Volume > Volume 1Y avg * 10 OR Volume 1W avg > Volume 1Y avg OR
Volume 1M avg > Volume 1Y avg) AND
Market Cap > 500 AND Return 1D > 2 AND Return 1W > 5 AND Return 1M > 10
```

### 6. Trading Below Historical Valuations
```
Market Cap > 500 AND
(PE < Historical PE 3Y OR PE < Historical PE 5Y OR PE < Historical PE 7Y OR
PE < Historical PE 10Y) AND
YOY Q sales growth > 10 AND YOY Q profit growth > 10 AND
Public holding < 50 AND ROE > 12 AND D/E < 1
```

### 7. Re-Rating Candidates
```
((Change in promoter + DII + FII holding) > 1 OR ... OR
YOY Q profit growth > 20 AND YOY Q sales growth > 10) AND
Market Cap > 500 AND Sales > 100 AND D/E < 1 AND
Public holding < 30 AND Pledged % < 10
```

### 8. Capacity Expansion (Capex Plays)
```
(Gross block + CWIP) > 1.5 * (Gross block preceding year + CWIP preceding year) AND
D/E < 1 AND Market Cap > 500 AND Debt < Debt preceding year
```

### 9. TechnoFunda Momentum
```
Market Cap > 500 AND ROE > 10 AND Public holding < 49 AND
YOY Q profit growth > 20 AND YOY Q sales growth > 15 AND
Price > DMA50 AND DMA50 > DMA200 AND
RSI 60–85 AND Volume 1W avg > 1Y avg AND
Return 1D > 2 AND Return 1W > 5 AND PE < YOY Q profit growth
```

### 10. Fraud Detection — AVOID
```
Days Payable Outstanding > 365 AND
Days Receivable Outstanding > 365 AND
Trade receivables > Sales * 0.25
```

### 11. Cash Rich Companies
```
Cash Equivalents > Market Cap * 0.2 AND Market Cap > 200 AND D/E < 1
```

### 12. Deep Value (Net Cash > Market Cap)
```
(Market Cap - Cash Equivalents - Investments + Debt) < 0 AND Market Cap > 100
```

### 13. Accumulation (Big Hand Buying)
```
Number of Shareholders < Number of Shareholders 1Y back * 0.80 AND
Market Cap > 1000 AND D/E < 1
```

### 14. Distribution (Big Hand Selling — CAUTION)
```
Number of Shareholders > Number of Shareholders 1Y back * 2 AND
Market Cap > 1000 AND Number of Shareholders > 10000
```

### 15. MOAT Companies
```
Market Cap > 200 AND ROCE > 15 AND ROE > 15 AND OPM > 15 AND
NPM last year > 10 AND Cash from ops > Net Profit AND NCF > 0 AND
FCF > 0 AND D/E < 0.5 AND Interest Coverage > 5 AND
Inventory days < 90 AND Debtor days < 60 AND
Days Payable > 60 AND Cash Conversion Cycle < 90 AND
Sales growth 3Y > 10 AND Profit growth 3Y > 10 AND Public holding < 50
```

### 16. SME Gems
```
Is SME AND Sales > 50 AND Sales growth 3Y > 20% AND Profit growth 3Y > 20% AND
ROCE > 20 AND ROE > 20 AND D/E < 1 AND Market Cap 50–500 AND
Promoter holding > 50 AND YOY Q sales growth > 20 AND YOY Q profit growth > 20
```

### 17. Underperformer (Return < FD but Growing)
```
Market Cap > 500 AND
(Return 10Y < 8 OR Return 7Y < 8 OR Return 5Y < 8 OR Return 3Y < 8) AND
Sales growth 10Y > 8 AND Profit growth 10Y > 8 AND
PE < Historical PE 10Y AND Promoter holding > 50 AND
ROE > 8 AND ROCE > 8
```

### 18. Beaten Down Quality
```
(Return 3Y < -15 OR Down from 52w high > 30) AND
Market Cap > 500 AND D/E < 1 AND ROE > 15 AND
YOY Q sales growth > 10 AND YOY Q profit growth > 20
```

### 19. Consistent Sales Growers
```
Sales growth > Sales growth 3Y AND Sales growth 3Y > Sales growth 5Y AND
Sales growth 5Y > Sales growth 7Y AND Sales growth 7Y > Sales growth 10Y AND
Sales latest Q > Sales preceding Q AND ... AND
YOY Q sales growth > Sales growth AND Market Cap > 500
```

### 20. Coffee Can Portfolio
```
Sales growth > 10 AND Sales growth 10Y > 10 AND Profit growth > 10 AND
EPS growth 10Y > 10 AND Avg ROCE 10Y > 15 AND D/E < 0.5 AND
Promoter holding > 50 AND OPM > 15 AND Market Cap > 1000 AND
Dividend yield > 0.5
```

### 21. CANSLIM Model
```
EPS latest Q > 1.15 * EPS preceding year Q AND
EPS > 1.20 * EPS last year AND EPS last year > EPS preceding year AND
YOY Q sales growth > 15 AND Profit growth > 15 AND Sales growth > 15 AND
YOY Q profit growth > 16 AND ROE > 15 AND D/E < 2 AND
Market Cap > 10 AND Down from 52w high <= 10
```

## Chartink Scanners

All "Nimblr"-authored scanners below are CCI(34)-gated momentum/breakout screens — see [[concepts/CCI]] for the indicator. Full scan-clause formulas were extracted 2026-06-15 from "Atlas / Nimblr's Dashboard" (https://chartink.com/dashboard/261357); see [[sources/Chartink-Atlas-Nimblr-Dashboard]] for full detail.

### 1. Blockbuster Screener 2.0
https://chartink.com/screener/nimblr-blockbuster-screener
```
quarterly EPS > 4-quarters-ago EPS AND
quarterly net sales > 4-quarters-ago net sales AND
quarterly net profit > 4-quarters-ago net profit AND
close > SMA(close, 200) AND SMA(close, 50) > SMA(close, 200) AND
(close / EPS) / (|EPS - 1-candle-ago EPS| - 1) * 100 < 1.5  (PEG-style < 1.5) AND
market cap > 300 AND
daily volume > SMA(volume, 20) * 1.5 AND
yearly RONW% > 15 AND yearly ROCE% > 15 AND yearly D/E < 1.5 AND
daily CCI(34) > 100
```
YoY fundamental growth + golden-cross Stage 2 trend + PEG<1.5 valuation + quality filters + CCI/volume momentum trigger.

### 2. Early Breakout
https://chartink.com/screener/nimblr-s-early-breakout-scanner
(formula not yet extracted — link only)

### 3. Accumulation Breakout Stock
https://chartink.com/screener/nimblr-s-accumulation-breakout-stock
```
(10-day high - 10-day low) / 10-day low * 100 < 7  (tight base) AND
daily CCI(34) >= 100 AND
close > 10-day-prior high  (breakout)
```
A CCI-gated VCP_1C variant — compare to [[concepts/VCP]].

### 4. FII-DII Volume Interest Scanner — Proxy
https://chartink.com/screener/nimblr-s-fii-dii-volume-interest-scanner-proxy
```
close >= 1-day-ago close * 1.02 AND
volume >= SMA(volume, 10) * 2 AND
close > 100 AND
daily CCI(34) > 133 AND
yearly net sales > 1-year-ago net sales * 1.20
```
Proxy for institutional buying (Chartink has no native FII/DII data): big daily move + 2x volume + strong CCI + revenue growth.

### 5. Volume Shocker
https://chartink.com/screener/nimblr-s-volume-shocker
```
daily volume > SMA(volume, 10) * 2 AND
daily volume < SMA(volume, 10) * 5  (2x-5x = "shock", not a one-off blowout) AND
daily CCI(34) > 110 AND
close > 100
```
Pure volume-anomaly + momentum screen, no trend filter — highest false-positive rate, for manual review only.

### 6. Fundamental Multibagger + Breakout (new)
```
market cap 200-20000 AND
yearly OPM% >= 15 AND yearly ROCE% >= 18 AND
yearly net profit > 1-year-ago net profit * 1.15 AND
weekly CCI(34) > 110 AND
weekly close > 0.95 * 52-week high
```
Mid-cap, high-margin/ROCE growth screen, gated by weekly CCI momentum + proximity to 52w high. Overlaps with [[concepts/CANSLIM]] growth criteria.

### 7. 1Y All-Time Breakout (new)
```
SMA(volume, 20) > SMA(volume, 50) * 1.05 AND
close > SMA(close, 200) AND
close >= daily high * 0.99  (strong close near the day's high)
```
Simple "approaching/breaking ~1yr resistance" screen — trend filter + volume expansion + strong close. Looser sibling of [[strategies/EW-Flat-Bottom-Breakout]].

### 8. 3Y Breakout Scanner (new)
```
close >= (756-trading-day high) * 0.98  (within 2% of ~3yr high) AND
close > SMA(close, 200) AND
SMA(volume, 20) > SMA(volume, 50) * 1.3
```
Same idea as #7 but with an explicit ~3-year lookback high and a stricter volume-expansion threshold.

### 9. Darvas Volume Shockers (Amitabh Jha3)
https://chartink.com/screener/copy-amitabh-jha3-volume-shockers-stocks-with-rising-volumes-darvas-100
```
latest volume > sma(volume, 10) * 2 AND
(latest close > 1 day ago close * 1.05 OR latest close < 1 day ago close * 0.95)
```
Raw volume-anomaly + ±5% price-swing screen. No CCI gate, no price floor, no trend filter — bidirectional (catches breakouts AND breakdowns). Contrast with #5 (Nimblr Volume Shocker): same 2× volume floor but #5 adds CCI(34)>110 momentum gate and upper volume cap, making it directionally bullish only. This Darvas variant is a broader activity radar; output requires manual filtering for trend context (e.g. close > MA(200), [[concepts/Darvas-Box]] box structure). See [[sources/Chartink-Darvas-Volume-Shockers-Screener]] for detailed comparison.

## Related
- [[concepts/CANSLIM]] — CANSLIM method detail
- [[concepts/Darvas-Box]] — Darvas scan
- [[concepts/CCI]] — CCI(34) indicator used across the Chartink scanners above
- [[concepts/VCP]] — Accumulation Breakout scanner is a CCI-gated VCP_1C variant
- [[strategies/TechnoFunda-Swing]] — TA overlay on these screens
- [[strategies/EW-Flat-Bottom-Breakout]] — related breakout logic
- [[sources/Chartink-Atlas-Nimblr-Dashboard]] — source for scanners #1, #3-8 formulas
