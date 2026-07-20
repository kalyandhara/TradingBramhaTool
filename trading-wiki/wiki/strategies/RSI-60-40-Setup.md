---
title: "RSI 60-40 Setup (21 & 50 EMA)"
category: strategy
timeframe: swing
tags: [rsi, ema, pullback, breakout, trend-following, uptrend]
created: 2026-07-19
updated: 2026-07-19
sources: 1
related: [concepts/RSI.md, concepts/EMA.md, strategies/EMA-Pullback.md, concepts/Fibonacci-Retracement.md]
---

# RSI 60-40 Setup (21 & 50 EMA)

## Core Idea
In a healthy uptrend, [[concepts/RSI]] does **not** behave by the textbook 70/30 rules — it oscillates in a **40–60 band**: it makes *higher lows near 40* (buyable dips) and *faces rejection near 60* (breakout trigger, not a sell). Overlaying **21 EMA** (dynamic support) and **50 EMA** (major support) turns that RSI behavior into two repeatable, with-trend entries. This is a trend-*continuation* system, not a reversal system.

## Setup Criteria (trend filter — all required)
- Price above **both** the 21 EMA and 50 EMA.
- **21 EMA above 50 EMA** (bullish stack / alignment).
- RSI(14) swinging between ~40 and ~60, making higher lows near 40 and getting rejected near 60.

If price is below the EMAs or the EMAs are not stacked bullishly, there is no setup — do not force it.

## Entry Rules

### A. RSI 40 setup — pullback entry
- RSI pulls back **near 40 and is bouncing up**.
- Price is **near the 21 EMA or 50 EMA** (dynamic/major support).
- **Confirmation:** a bullish candle / pattern at the support before entering.

### B. RSI 60 setup — breakout entry
- RSI is **near 60 and breaks above it**.
- Price **breaks recent high / resistance**.
- **Confirmation:** a strong candle with volume.

## Exit Rules (stop + targets)
- **Stop-loss:**
  - RSI-40 (pullback) entry → below the **50 EMA**.
  - RSI-60 (breakout) entry → below the **21 EMA**.
- **Risk per trade:** 1–2% of capital.
- **Target 1:** recent swing high / resistance.
- **Target 2:** 2R to 3R.
- **Trail:** move the stop below the **21 EMA** as price advances, and let winners run in the direction of the trend.

## Timeframe
Swing (works on the trend timeframe; the source frames it on a daily-style uptrend). Best in clean, sustained trends.

## Best Market Conditions
Strong, orderly uptrends where price rides the 21 EMA and RSI holds its 40–60 range — "trend is your friend."

## Worst Market Conditions
Range-bound / choppy tape: RSI whipsaws through 40–60 with no follow-through and the EMAs flatten and tangle. The 40-bounce and 60-breakout both fail repeatedly in chop.

## Backtest / Track Record
None in-wiki — sourced from an educational infographic, not a validated system. Rules are specific enough to backtest against the repo's screener toolchain (EMA stack + RSI-band state are already computable). Treat as a hypothesis until measured.

## Examples
_None filed yet — add worked charts on first live application._

## Related Concepts
- [[concepts/RSI]] — the regime-aware 40–60 range this setup exploits is documented on the RSI page.
- [[concepts/EMA]] — 21 EMA (dynamic support) / 50 EMA (major support), bullish-stack requirement.
- [[strategies/EMA-Pullback]] — sibling with-trend pullback entry; RSI-40 is the momentum-gated version of the same idea.
- [[concepts/Fibonacci-Retracement]] — the Fib golden-zone pullback + RSI-oversold entry is a location-based cousin of the RSI-40 entry.

## Sources
- [[sources/Fingrad-Trading-Infographics-Collection]] (2026-07-19) — full "RSI 60-40 Setup using 21 EMA & 50 EMA" handwritten infographic (concept, entries A/B, risk, targets, trailing).
