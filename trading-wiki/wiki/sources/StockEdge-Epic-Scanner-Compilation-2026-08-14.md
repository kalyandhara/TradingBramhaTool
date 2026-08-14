---
title: "StockEdge Epic Scanner Compilation — Community Scans"
category: source
tags: [stockedge, scanner, fundamentals, momentum, community, fipa, ema-stack, atm-high]
created: 2026-08-14
updated: 2026-08-14
sources: 1
related: [concepts/Momentum-Score-MS, strategies/FIPA-Quality-Momentum, entities/Lupin]
---

# StockEdge Epic Scanner Compilation — Community Scans

## Metadata
- **Source type:** Obsidian note — screenshot compilation (`epic stock scanner.md`, Trading_Bramha vault)
- **Captured:** 2026-08-14
- **Platform:** StockEdge (EOD, NSE/BSE, community scanner builder)
- **Scanners documented:** 6 (2 with conditions detail + 4 from StockEdge's own showcase/competition)

---

## Key Takeaways

1. **FIPA + trend structure is the dominant recipe** — every scanner here combines at least one fundamental filter (ROE, ROCE, FCF, PEG, Sales Growth, FundamentalScore) with a trend/momentum gate (EMA stack, RS, ATH zone).
2. **Momentum Score (MS1M/MS3M/MS6M)** is the StockEdge-native RS proxy — used by two of six scanners with thresholds of 60–70+.
3. **Relative Strength variants** appear in nearly every scanner: RSMkt55Days, RSSec55Days, RSMkt21Weeks, ARS (Absolute RS), SRS (Sector RS) — StockEdge exposes both market-relative and sector-relative RS across multiple timeframes.
4. **ATH zone** (`Close Within All Time High Zone`) is a recurring final gate — it keeps only stocks where price strength already confirms the fundamentals.
5. **ADX > 25 + DI crossover** is the trend-confirmation entry trigger in the Ashok Daniel coiled-spring scanner — overlaps with our existing ADX logic in `scanner_templates.py`.
6. **Perfect Match (12 Aug 2026, Major Stocks):** Lupin Ltd. is the sole stock hitting all 10 conditions of the Cheap Fundamental scanner simultaneously.

---

## Scanner 1 — Cheap Fundamental Stock

**Conditions count:** 10 (all Readymade StockEdge scans)

| # | Condition |
|---|-----------|
| 1 | Improved Return on Equity |
| 2 | Improved Return on Capital Employed |
| 3 | Consistently Increasing Annual EPS |
| 4 | High PAT Margin |
| 5 | High Sales Growth Ratio (Annual Report) |
| 6 | Consistent Sales Growth Ratio (Annual Report) |
| 7 | High Interest Coverage Ratio |
| 8 | Consistent Cash From Operations |
| 9 | Consistently Positive Free Cash Flow/Share |
| 10 | Low PEG Ratio |

**Results — 12 Aug 2026 (Major Stocks filter):**
- **Perfect Match:** Lupin Ltd. (NSE) — all 10 conditions met
- **Almost There (9/10, missing Low PEG):** Anand Rathi Wealth Ltd. · Castrol India Ltd. · Cummins India Ltd.

**Read:** This is a pure quality filter — no price/technical gate. Low PEG is the hardest condition to meet in a good uptrend (rising price inflates PEG). The "Almost There" cluster at 9/10 suggests stocks that are fundamentally excellent but trading at a growth premium.

---

## Scanner 2 — Trend Momentum+ (Abhishek Pramod Keskar)

**Conditions count:** 14 | **Type:** Mixed Custom Query + Readymade

**Custom Query 1 — Trend & Momentum Base:**
```
EMA200 > EMA200PrecedingDay
AND Close > EMA50
AND EMA20 > EMA20PrecedingDay
AND Close > EMA20
AND Close > EMA200
AND RSI > 40
AND MCap > 1000
```

**Custom Query 2 — StockEdge Momentum Scores:**
```
MS1M > 60 AND MS3M > 60 AND MS6M > 60
```

**Readymade Scans (8 more):**
- Strongly Outperforming Benchmark Index (21 Days)
- Increasing Relative Strength — Benchmark Index (21 Days)
- Stock Outperforming Benchmark Index in both 1 Week and 3 Month
- Stock Outperforming Sectoral Index in both 1 Week and 3 Month
- Strongly Outperforming — Sectoral Index (55 Days)
- Increasing Relative Strength — Sectoral Index (55 Days)
- Strongly Outperforming Benchmark Index (21 Weeks)
- Increasing Relative Strength — Benchmark Index (21 Weeks)
- Close Within All Time High Zone

**Thesis (as stated):** "Finds fundamentally strong stocks in a healthy uptrend, suitable for medium-to-long-term swing investing. Combines FIPA and positive results with EMA 50 > 100 > 200 trend structure and a bullish momentum zone."

**Read:** The most comprehensive RS gate of the six — it requires outperformance vs both benchmark AND sector across three time windows (21D, 55D, 21W). RSI > 40 is unusually loose (not > 50 or > 60) — likely to allow pullbacks within an uptrend. MCap > 1000 Cr = very wide market-cap universe. The combination of benchmark + sectoral RS across 1W/3M/55D/21W creates a multi-timeframe RS filter that no single RS signal replicates.

---

## Scanner 3 — Ashok Daniel (StockEdge Showcase, Slide 06)

**Thesis:** "Transitions from a late-stage trend-following scanner into a coiled-spring breakout engine — capturing quality mid-caps resting near their 50-EMA floor and exploding upward on institutional volume before the trend becomes obvious."

**Criteria (as submitted):**
```
Nifty Midcap 150
Market Cap: 5,000–50,000 Cr
Beta: 0.90–1.25
+DI > -DI
ADX(14) > 25 AND rising
Close within 2% of EMA-50
Close > 1.03× prior close WITH volume > 20-day avg
```

**Read:** The `Close within 2% of EMA-50` gate is the key differentiator — it's not chasing extended moves but waiting for price to rest at the EMA before the next thrust. The `Close > 1.03× prior close with volume > 20-day avg` is a same-day breakout confirmation requiring both price thrust AND volume surge in the same session. Beta 0.90–1.25 keeps volatility moderate. Nifty Midcap 150 universe = ~150 stocks, keeps the list manageable.

**Overlap with our tools:** ADX > 25 + DI crossover pattern exists in `scanner_templates.py`. The EMA-50 proximity gate (`within 2%`) is net-new.

---

## Scanner 4 — ASHOK TANEJA (StockEdge)

**Conditions count:** 9 | **Type:** Mixed Custom Query + Readymade

**Custom Queries:**
```
ROE > 15 AND ROCE > 15
RSMkt55Days > 0 AND SRS > 0 AND ARS > 0
MCap > 10000
DebtToEquity < 1
AND WeeklyRSI > WeeklyRSIPrecedingWeek
AND RSI > RSIPrecedingDay
```

**Readymade Scans:**
- Close Crossing 52 Week High
- Stock Outperforming Benchmark Index in both 1 Week and 3 Month

**Read:** `RSMkt55Days > 0 AND SRS > 0 AND ARS > 0` requires ALL three RS measures to be positive — the stock must outperform the market over 55 days, outperform its sector, and have positive absolute RS. `Close Crossing 52 Week High` is the price-trigger gate. Weekly RSI rising + Daily RSI rising = dual-timeframe momentum confirmation. MCap > 10,000 Cr = large-cap only.

---

## Scanner 5 — Patel Yash Ashokbhai (StockEdge Showcase, Slide 09)

**Thesis:** "Momentum stocks with strong fundamentals — within 10% of 52-week high, RSI 50-68 across daily/weekly/monthly, SMA20 above SMA50, ROE above 15%, debt-to-equity under 1, and sales growth above 12%."

**Key gates (inferred from thesis):**
- Price within 10% of 52-week high
- RSI 50–68 (daily + weekly + monthly) — RSI ceiling is deliberate, avoids overbought
- SMA20 > SMA50 (golden cross zone)
- ROE > 15%
- Debt-to-Equity < 1
- Sales growth > 12%

**Read:** The RSI 50–68 band is the most unusual gate here — it explicitly excludes overbought stocks (>68), looking for stocks in the middle of a move, not extended. Combined with "within 10% of 52-week high," it targets the setup zone before a breakout to new highs rather than after.

---

## Scanner 6 — All Time High Momentum Scan (Nikhil Pandurang Mahindre)

**Conditions count:** 3 (grouped) | **Type:** Mixed Custom Query + Readymade

**Custom Query:**
```
EMA10 > EMA20 AND EMA20 > EMA50 AND EMA50 > EMA200
AND MS1M >= 70 AND MS3M >= 70 AND MS6M >= 70
AND RSI >= 50
AND ADX >= 25
AND RSMkt55Days > 0.1
AND FundamentalScore >= 70
AND RSSec55Days > 0.1
AND RSMkt21Weeks > 0.1
```

**Readymade Scans:**
- Close Within All Time High Zone
- Strong Fundamentals

**Read:** Full EMA stack (10>20>50>200) is the strictest trend gate of the six. `FundamentalScore >= 70` is StockEdge's proprietary composite (not disclosed) — this is a black-box filter. Momentum Score thresholds at 70+ vs 60+ in Scanner 2 = stricter. `RSMkt21Weeks > 0.1` requires meaningful 21-week market outperformance, not just positive RS. This scanner produces the fewest results but the cleanest, strongest stocks.

---

## Actionable Insights

1. **Combine Cheap Fundamental + Trend Momentum+** — run the 10-condition quality filter first as a watchlist, then apply the EMA/RS gate for timing. Lupin, Cummins, Castrol, Anand Rathi = quality candidates waiting for a momentum trigger.

2. **EMA-50 proximity gate** (Ashok Daniel `within 2%`) is a net-new setup rule worth adding to our scanner toolbox — it captures the rest before the thrust, not the thrust itself.

3. **RSI 50–68 band** (Patel Yash) is a deliberate overbought-exclusion — worth testing as an alternative to our typical `RSI > 60` gate on breakout scanners.

4. **MS1M/MS3M/MS6M** (StockEdge Momentum Scores) are StockEdge-native and not directly replicated in our Python tools. Our closest proxies are percentile RS calculations in `scanner_templates.py`.

5. **FundamentalScore ≥ 70** in Scanner 6 is a StockEdge proprietary — treat it as a black box that bundles the 10 quality metrics from Scanner 1 into one number.

---

## Contradictions with Existing Wiki

None found. These scanners are additive to existing [[strategies/FIPA-Quality-Momentum]] and [[concepts/Relative-Strength-RS]] frameworks.

> [!note] EMA stack note
> Scanner 6 uses EMA10>20>50>200 (four levels). Our `scanner_templates.py` typically uses EMA20>50>200 (three levels). EMA10 adds a short-term trend qualifier — worth testing whether it improves signal quality.

---

## Pages Updated
- [[wiki/log.md]]
- [[wiki/index.md]]
