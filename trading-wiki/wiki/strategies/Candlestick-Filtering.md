---
title: "Candlestick Filtering Strategy"
category: strategy
tags: [candlestick, filtering, RSI, MACD, stochastic, entry-timing, multi-indicator]
created: 2026-06-19
updated: 2026-06-19
sources: 1
timeframe: swing
related:
  - concepts/Candlestick-Patterns.md
  - concepts/Support-Resistance.md
  - strategies/Supply-Demand-Zone-Trading.md
  - concepts/RSI.md
  - concepts/MACD-Divergence.md
  - sources/Litchfield-Morris-Candlestick-Charting-Explained-2006.md
---

# Candlestick Filtering Strategy

## Core Idea
Candlestick patterns alone produce 41–64% win rates — insufficient for systematic trading. The filtering concept adds a **presignal condition** from a separate technical indicator. The indicator must reach a defined presignal zone FIRST; only then does the next candle pattern trigger an entry. Filtered candles consistently rank #1 vs 14 standalone indicators across 7,275 stocks and 14.6M days of data.

**Analogy:** The filter primes the gun. The candle pattern pulls the trigger. Without the gun being primed, the trigger does nothing.

---

## Setup Criteria

1. **Trend established:** Price above/below an exponential moving average (10–21 day) confirms the operative trend direction
2. **Filter primed (presignal zone):** A secondary indicator has reached — but not yet signaled — its extreme zone:
   - RSI approaching oversold (30–40 zone for bullish; 60–70 for bearish)
   - MACD showing early divergence (histogram shrinking while price continues)
   - Stochastic %K and %D in extreme territory (< 20 or > 80)
   - Price at a defined S/R zone, supply/demand zone, or prior structure level
3. **Candle pattern fires:** A valid reversal pattern (Hammer, Engulfing, Morning Star, Harami Cross, etc.) appears WITHIN the presignal zone

---

## Entry Rules
- Enter at the close of the confirming candle (or open of the following day)
- Preferred setup: candle pattern that closes at or near its session high (bullish) or low (bearish) — shows commitment
- Volume expansion on the signal bar strengthens the setup

---

## Exit Rules
- **Profit target:** Measured move or prior S/R level; typically sized for a 2-day forward window (the statistically strongest horizon)
- **Stop loss:** Below the candle pattern's extreme (e.g., below Hammer's tail; below the Morning Star's middle bar low)
- **Trailing:** 5-bar trailing stop or flip of the confirming indicator signal

---

## Timeframe
- **Primary:** Daily swing (1–10 day holds)
- **Note:** Authors explicitly warn against sub-daily application — overnight psychology (gap between close and open) is central to candle pattern mechanics; intraday bars don't carry this

---

## Best Market Conditions
- Trending market with occasional pullbacks (Rising/Falling Three Methods, Hammer-at-EMA setups)
- High-volume trend days as context → look for candle confirmation on pullback

## Worst Market Conditions
- Choppy, range-bound markets with no clear EMA direction — trend filter fails; patterns generate noise
- Very low-liquidity stocks (patterns manipulable with thin volume)

---

## Kalyan Application: S&D Zone as Filter
The most actionable version for this wiki:
1. Mark Supply/Demand zones per [[strategies/Supply-Demand-Zone-Trading]]
2. When price approaches a zone AND RSI is in presignal territory:
   - Bullish: price at demand zone + RSI 35–45 + Hammer / Engulfing / Morning Star → long entry
   - Bearish: price at supply zone + RSI 55–65 + Shooting Star / Dark Cloud / Evening Star → short entry
3. Stop below zone base; target next S/R level

This is the Ryan Litchfield framework (Ch. 10): *Candlesticks are not the setup; they are the timing trigger within a pre-identified structural setup.*

---

## Backtest / Track Record
- Gregory Morris: 7,275 stocks, all NYSE/Nasdaq/Amex, 13+ years, 14.6M days, 1.7M patterns
- Filtered candles: ranked **#1** vs all 14 common technical indicators at 2-day prediction horizon
- Unfiltered candles ranked 5th at 1-day, #1 at 2-day
- Pattern Detail boxes in the book show individual pattern win rates (range: 41–64%; only 5 patterns > 59%)

---

## Examples
- Hammer at 21 EMA with RSI at 38 → long entry → 2-day target = first resistance
- Bearish Engulfing at supply zone with RSI at 66 → short entry → stop above supply zone high
- Rising Three Methods after EMA reclaim → continuation buy on 5th bar break above bar 1 high

---

## Related Concepts
- [[concepts/Candlestick-Patterns]] — complete pattern reference with statistics
- [[concepts/Sakata-Method]] — foundational philosophy
- [[concepts/Support-Resistance]] — the most natural filter for candle signals
- [[concepts/RSI]] — most commonly used presignal indicator
- [[concepts/MACD-Divergence]] — alternative presignal filter
- [[strategies/Supply-Demand-Zone-Trading]] — S&D zones as structural filter layer

## Sources
- [Litchfield-Morris-Candlestick-Charting-Explained-2006](../sources/Litchfield-Morris-Candlestick-Charting-Explained-2006.md)
