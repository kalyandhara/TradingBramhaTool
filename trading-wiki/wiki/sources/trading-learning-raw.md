---
title: "Personal Trading Notes — trading_learning_raw.pdf"
category: source
tags: [screener-queries, technical-analysis, fundamental-analysis, indian-markets, darvas, canslim, swing-trading]
created: 2026-06-14
updated: 2026-06-14
author: Kalyan Dhara
related: [wiki/concepts/Darvas-Box.md, wiki/concepts/CANSLIM.md, wiki/concepts/RSI.md, wiki/strategies/TechnoFunda-Swing.md, wiki/concepts/Elliott-Wave.md]
sources: 0
---

# Personal Trading Notes — trading_learning_raw.pdf

## Metadata
- **Author:** Kalyan Dhara
- **Created:** 2026-06-14
- **Pages:** 104
- **Type:** Personal research compilation — screener queries, stock watchlists, TA notes, market logic, indicator explanations

## Key Takeaways

1. **Darvas Box / DarvaX** is the core strategy framework — combined with RSI and EMA for entry timing and a lollipop low as the stop loss on daily/weekly closing basis
2. **21 CANSLIM screener variants** documented with exact Screener.in query syntax, covering everything from GARP to turnaround plays to fraud detection
3. **RSI regime rules**: in uptrend, RSI bounces 40–80 (not 30); in downtrend, RSI finds resistance at 60 and support at 20
4. **VCP (Volatility Contraction Pattern)** is a key setup — price tightens into lower-volume squeeze before breakout
5. **TechnoFunda** approach: use fundamentals (YoY profit growth, ROE, debt) to filter quality, then TA (EMA, RSI, ADX, VWAP) for timing
6. **Sector watchlists** built across Electronics, Solar, Infrastructure, FMCG, IT, Pharma, Auto, Banking
7. **Swing system** described: VWAP + RSI + EMA20/SMA50 + VCP + ATR + ADX — all must align for entry
8. **Elliott Wave** logic documented: 5-wave impulse (smart money → pullback → strongest → sideways → final push) + 3-wave corrective

## Detailed Notes

### Screener Queries (Screener.in)

**Big Change in Institutional Holding:**
Change in FII + DII + Promoter holding > 10 AND YOY Quarterly profit growth > 10 AND YOY Quarterly sales growth > 10 AND Market Cap > 5000

**Tiny Fish (Small Cap Momentum):**
Market Cap < 100 AND Price < 200 AND PE < 15 AND Sales growth 3Y > 10 AND Profit growth 3Y > 10 AND Promoter holding > 20%

**Darvas Scan:** 100*((High - Price)/High) < 10 AND > 0 AND 100*(Price/Low - 1) > 100 AND Price > 10 AND Volume > 100000
→ https://screener.in/screens/4928/darvas-scan/

**Undervalued Large Cap:** PE < Industry PE AND PE < 20 AND Market Cap > 5000

**CANSLIM (Core):** EPS latest quarter > 1.25 * EPS preceding year quarter AND EPS growth 3Y > 20 AND Promoter holding > 65 AND Return 1Y > 30 AND FII+DII holding 5–15 AND Market Cap > 5000

**Blockbuster Quarterly Results:** Market Cap 200–100000 AND YOY quarterly sales growth > 20 AND YOY quarterly profit growth > sales growth AND OPM latest Q > OPM 5Y AND Other income latest Q < Other income preceding year Q * 2 AND PE < YoY Quarterly Profit Growth

**TechnoFunda Momentum:** Market Cap > 500 AND ROE > 10 AND Public holding < 49 AND YOY Q profit growth > 20 AND YOY Q sales growth > 15 AND Price > DMA50 AND DMA50 > DMA200 AND RSI 60–85 AND Volume 1W avg > 1Y avg AND Return 1D > 2 AND Return 1W > 5 AND PE < YOY Q profit growth

**Fraud Detection (AVOID):** Days Payable > 365 AND Days Receivable > 365 AND Trade receivables > Sales * 0.25

**MOAT Companies:** ROCE > 15 AND ROE > 15 AND OPM > 15 AND NPM > 10 AND Cash from ops > Net Profit AND FCF > 0 AND D/E < 0.5 AND Interest Coverage > 5 AND Cash Conversion Cycle < 90 AND Sales growth 3Y > 10 AND Profit growth 3Y > 10

**Coffee Can Portfolio:** Sales growth > 10 AND Sales growth 10Y > 10 AND Profit growth > 10 AND EPS growth 10Y > 10 AND Avg ROCE 10Y > 15 AND D/E < 0.5 AND Promoter holding > 50 AND OPM > 15 AND Market Cap > 1000 AND Dividend yield > 0.5

**GARP Scanner:** Market Cap > 500 AND Sales > 500 AND Sales growth > 15 (3Y and 5Y) AND EPS growth > 15 (3Y and 5Y) AND Expected Q net profit > Net profit 3Q back

**Accumulation (Big Hand Buying):** Number of shareholders < 1Y back * 0.80 AND Market Cap > 1000 AND D/E < 1

**Distribution (Big Hand Selling — CAUTION):** Number of shareholders > 1Y back * 2 AND Market Cap > 1000

### DarvaX Framework
- **High Dry Fry Pattern:** Stock moves 20–50% on huge volume → corrects 10–20% from peak → small baby candles cluster (DarvaX box)
- **Lollipop Low = Stop Loss** on daily or weekly closing basis
- Stage transition signals new uptrend (e.g. KAKA INDUSTRIES example above ₹250, new uptrend above ₹300 CBS)
- Combined with: RSI, EMA, Fibonacci, Price Action, Crowd Mindset
- Without discipline and patience, all tools are garbage (direct quote from notes)

### RSI Rules (Kalyan's Rules)
- Uptrend: RSI finds resistance at 80, support at 40
- Downtrend: RSI finds resistance at 60, support at 20
- When price below 21 EMA and RSI consistently below 40 → every pullback is a selling opportunity

### Swing Trading System (Full)
Entry only when ALL align:
- Price > VWAP (institutions net buyers)
- Price > EMA20 (short-term trend)
- Price > SMA50 (medium-term trend)
- RSI > 50
- ADX > 20 (trend strength, not chop)
- VCP: volume contracting (tight base before breakout)
- ATR: breakout candle moves > 0.5 × ATR (real move, not fakeout)

### Indicators Documented
- **KST (Know Sure Thing):** Multi-timeframe ROC oscillator by Martin Pring. KST cross above signal = early bullish. KST above zero = trend confirmed. KST below zero despite cross = only short-term pullback within downtrend
- **ADX:** Non-directional trend strength. < 20 = chop; 20–40 = moderate; > 40 = strong. +DI vs -DI determines direction
- **ROC:** Rising ROC = uptrend confirmation. Divergence with price = weakening momentum
- **MACD Divergence:** Bullish = price lower lows, MACD higher lows. Bearish = price higher highs, MACD lower highs

### Elliott Wave Summary
Impulse: Wave 1 (smart money enters) → Wave 2 (pullback, not below W1 start) → Wave 3 (strongest, longest) → Wave 4 (sideways correction) → Wave 5 (final push, often weaker)
Corrective: A (first drop) → B (bounce) → C (final correction)

### Personal Trading Philosophy (Kalyan's Notes)
- "Don't react, respond" — market creates urgency traps at entry and exit
- Keep cash during blood bath for correct-time entry
- In uptrend: follow DarvaX/TechnoFunda
- In downtrend: look for quality large caps with convincing future
- When downtrend sensed per RSI/EMA: book max profit (don't worry about brokerage on blue chips, can re-enter)
- Personal allocation: < 20% in SME; < 10% in any single stock
- Portfolio lesson: Jan 2 2025 was +₹2L up, Jan 13 2025 turned -₹4L down (−15% swing)

### Key Resource Links
- BSE Insider Trading: https://bseindia.com/corporates/Insider_Trading_new.aspx
- NSE Bulk/Block Deals: https://nseindia.com/report-detail/display-bulk-and-block-deals
- Screener Results: https://screener.in/results/latest/
- BSE Latest Announcements: https://bseindia.com/corporates/ann.html

## Chartink Scanners (Ready to Use)
1. Blockbuster Screener: https://chartink.com/screener/nimblr-blockbuster-screener
2. Early Breakout: https://chartink.com/screener/nimblr-s-early-breakout-scanner
3. Accumulation: https://chartink.com/screener/nimblr-s-accumulation-breakout-stock
4. FII-DII Volume: https://chartink.com/screener/nimblr-s-fii-dii-volume-interest-scanner-proxy
5. Volume Shocker: https://chartink.com/screener/nimblr-s-volume-shocker
6. TechnoFunda Momentum: https://chartink.com/screener/darvas-bullish-tasuki-line-reversal-pattern

## Pages Updated by This Ingest
- [[concepts/Darvas-Box]]
- [[concepts/CANSLIM]]
- [[concepts/RSI]]
- [[concepts/VCP]]
- [[concepts/Elliott-Wave]]
- [[concepts/KST]]
- [[concepts/ADX]]
- [[strategies/TechnoFunda-Swing]]
- [[strategies/Screener-Queries]]
- [[analyses/Kalyan-Trading-Philosophy]]
