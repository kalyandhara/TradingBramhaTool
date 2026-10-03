---
title: "Chartink Dashboard — Atlas / Nimblr's Dashboard"
category: source
tags: [chartink, screener, cci, breakout, volume, fundamentals, momentum]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [strategies/Screener-Queries.md, concepts/CCI.md, concepts/VCP.md, strategies/EW-Flat-Bottom-Breakout.md, concepts/CANSLIM.md]
---

# Chartink Dashboard — Atlas / Nimblr's Dashboard

## Metadata
- Author: "Nimblr" (chartink screener author; screen slugs prefixed "nimblr...")
- Date accessed: 2026-06-15
- URL: https://chartink.com/dashboard/261357 (widget opened: 4788842)
- Type: Chartink dashboard bundling 7 saved scanners

## Key Takeaways
- All 7 scanners are CCI(34)-gated momentum/breakout screens for the Indian cash market, each pairing a CCI momentum trigger with a price-range/volume condition (technical) or a fundamentals growth filter.
- CCI(34) > 100 (or 110/133 for stricter variants) is the common "momentum confirmation" thread across 6 of 7 scanners — new concept page [[concepts/CCI]] created for this.
- 4 scanners were already linked (by URL only, no formula) in [[strategies/Screener-Queries]]: Blockbuster, Accumulation, FII-DII Volume, Volume Shocker. Their full formulas are now documented there.
- 3 scanners are new additions to the wiki: Fundamental Multibagger + Breakout, 1Y All-Time Breakout, 3Y Breakout Scanner.
- The "1Y/3Y Breakout" scanners are chartink-native equivalents of [[strategies/EW-Flat-Bottom-Breakout]] — price near/above a long-term high with rising volume + SMA200 trend filter, using a simple % threshold instead of an explicit flat channel.
- "Blockbuster Screener 2.0" embeds a PEG-style custom indicator: (Close/EPS) / (EPS QoQ growth %) < 1.5 — classic Peter Lynch PEG < 1.5 — layered on a golden-cross (SMA50>SMA200) + CCI trend filter.
- "Volume Shocker" contains a redundant/no-op condition (`daily volume / daily SMA(volume,1) = 1`, always true since SMA(1)=itself) — an authoring quirk, not a wiki contradiction.

## Detailed Notes

### 1. Accumulation Breakout Stock (id 4789128)
> "stocks trading within a tight price range (accumulation) now breaking out with strong momentum"

```
(greatest(10, daily close) - least(10, daily close)) / least(10, daily close) * 100 < 7
  AND daily cci(34) >= 100
  AND daily close > daily max(10, 1 day ago close)
```
10-day high-low range <7% of the 10-day low (tight base), CCI(34)>=100 momentum trigger, and today's close exceeds the prior 10-day high (breakout). A CCI-gated **VCP_1C** variant — compare to [[concepts/VCP]]'s "final contraction <=8%, breakout on momentum" logic.

### 2. Fundamental Multibagger + Breakout (id 4789180) — NEW
> "For educational purposes only based on Fundamentals."

```
market cap >= 200 and market cap <= 20000
  AND yearly operating profit margin percentage >= 15
  AND yearly return on capital employed percentage >= 18
  AND yearly net profit/reported profit after tax >= 1 year ago net profit/reported profit after tax * 1.15
  AND weekly cci(34) > 110
  AND weekly close > 1 week ago max(52, weekly high) * 0.95
```
Mid-cap (200-20000cr), high margin/ROCE, >15% YoY profit growth, weekly CCI(34)>110 momentum trigger, and within 5% of the 52-week high. Overlaps with [[concepts/CANSLIM]]'s growth criteria but with looser thresholds.

### 3. Blockbuster Screener 2.0 (id 4789099)
> "This is an educational tool, please use your process for any further decisions."

```
quarterly eps after extraordinary items basic > 4 quarters ago eps after extraordinary items basic
  AND quarterly net sales > 4 quarters ago net sales
  AND quarterly net profit/reported profit after tax > 4 quarters ago net profit/reported profit after tax
  AND daily close > daily sma(daily close, 200)
  AND daily sma(daily close, 50) > daily sma(daily close, 200)
  AND quarterly (close/eps after extraordinary items basic)/((abs(eps after extraordinary items basic - 1 candle ago eps after extraordinary items basic) - 1)*100) < 1.5
  AND market cap > 300
  AND daily volume > daily sma(daily volume, 20)
  AND yearly return on net worth percentage > 15
  AND yearly return on capital employed percentage > 15
  AND yearly debt equity ratio < 1.5
  AND daily cci(34) > 100
  AND daily volume > daily sma(daily volume, 20) * 1.5
```
The most comprehensive of the 7: YoY fundamental growth (EPS/sales/profit) + Stage 2 trend (golden cross) + PEG-style valuation <1.5 + quality filters (RONW/ROCE/D-E) + CCI/volume momentum trigger.

### 4. FII-DII Volume Interest Scanner — Proxy Updated (id 4789100)
> "Identify stocks with unusually high delivery volume and signs of smart money activity (typically institutional interest). Chartink does not support FII/DII buying, so we create a proxy scanner..."

```
daily close >= 1 day ago close * 1.02
  AND daily volume >= daily sma(daily volume, 10) * 2
  AND daily volume / daily volume * 100 >= 60   (redundant/no-op — always true)
  AND daily close > 100
  AND daily cci(34) > 100 and daily cci(34) > 133   (effectively CCI(34) > 133)
  AND yearly net sales > 1 year ago net sales * 1.20
```
Proxy for institutional buying: >2% one-day move + 2x average volume + CCI(34)>133 + >20% YoY sales growth.

### 5. 1Y All-Time Breakout — By Nimblr (id 4788842, opened widget)
> "This scanner highlights stocks approaching or breaking a year (~1-year) price resistance based on price-volume behaviour. Technical research tool for study and analysis only, not an investment recommendation."

```
daily sma(daily volume, 20) > daily sma(daily volume, 50) * 1.05
  AND daily close > daily sma(daily close, 200)
  AND daily close >= daily high * 0.99
```
Trend filter (close > SMA200) + rising volume trend (SMA20 vol > 1.05x SMA50 vol) + strong daily close (within 1% of the day's high). No explicit lookback-high comparison — relies on trend + strong close as the breakout proxy.

### 6. 3Y Breakout Scanner — By Nimblr (id 4788843) — NEW
> "Highlights stocks approaching or breaking a multi-year (~3-year) price resistance based on price-volume behaviour."

```
daily close >= daily max(756, daily high) * 0.98
  AND daily close > daily sma(daily close, 200)
  AND daily sma(daily volume, 20) > daily sma(daily volume, 50) * 1.3
```
Same idea as #5 but with an explicit ~3-year (756 trading days) lookback high and stricter volume expansion (1.3x vs 1.05x).

### 7. Volume Shocker — By Nimblr (id 4789114)
> "This is for educational purposes only."

```
daily volume / daily sma(daily volume, 1) = 1   (redundant/no-op — always true)
  AND daily volume > daily sma(daily volume, 10) * 2
  AND daily volume < daily sma(daily volume, 10) * 5
  AND daily cci(34) > 110
  AND daily close > 100
```
Pure volume-anomaly (2x-5x average volume = "shock") + CCI(34)>110 momentum, no price-trend filter — highest false-positive rate of the 7, intended for manual review only.

## Actionable Insights
- The CCI(34)>100/110/133 momentum trigger is reusable: could be added as an additional flag in `trading-wiki/tools/nse_wave_scanner.py` alongside the existing OWL/RSI/ATR/EMA flags.
- The "1Y/3Y Breakout" formulas (#5, #6) are simpler/looser versions of [[strategies/EW-Flat-Bottom-Breakout]] — useful as a first-pass filter before applying the stricter flat-channel + OWL check.
- The Blockbuster Screener's PEG<1.5 + golden cross + YoY growth combo (#3) is a strong candidate to cross-check against [[concepts/CANSLIM]] picks.
- "Fundamental Multibagger" (#2) weekly-CCI + 52w-high-proximity could feed sector/position-sizing watchlists.

## Contradictions with Existing Wiki
None directly contradictory. Note: this dashboard's CCI(34)>100 momentum trigger and the wiki's existing RSI-based momentum reads ([[concepts/RSI]] 40-80/20-60 zones, McDowell PTF RSI(9) 80/20 bands) are different oscillators measuring related but distinct things — both usable in confluence, not interchangeable.

## Pages Updated
- Created: wiki/sources/Chartink-Atlas-Nimblr-Dashboard.md (this page)
- Created: wiki/concepts/CCI.md
- Updated: wiki/strategies/Screener-Queries.md (added full chartink scan-clause formulas for all 7 scanners; added 3 new scanners; added cross-links)
- Updated: wiki/index.md, wiki/log.md
