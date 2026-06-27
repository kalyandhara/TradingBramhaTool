---
title: "ConnorsRSI"
category: concept
tags: [momentum, oscillator, mean-reversion, connors]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [concepts/RSI.md, strategies/Quantified-MA-Mean-Reversion.md, concepts/McDowell-Probability-Matrix.md]
---

# ConnorsRSI

## Definition
A composite momentum oscillator (0-100) developed by Connors Research that blends three sub-indicators into a single average:

```
ConnorsRSI(3,2,100) = [ RSI(Close, 3) + RSI(Streak, 2) + PercentRank(ROC(1), 100) ] / 3
```

Default parameters are 3, 2, 100 (hence the notation). Each component captures a different facet of short-term momentum/mean-reversion pressure.

## Components

### 1. RSI(Close, 3)
A standard [[concepts/RSI]] calculation, but with a very short 3-period lookback. Reacts quickly to recent price moves — high readings = several recent up days, low readings = several recent down days.

### 2. RSI(Streak, 2)
Same RSI formula, but applied to the **consecutive-day streak count** instead of price.
- Each day, track how many consecutive days the close has moved in the same direction (up streak = positive count, down streak = negative count, e.g. +1, +2, +3... or -1, -2, -3...).
- Apply a 2-period RSI to this streak series.
- The longer/more extreme the current streak, the more extreme (toward 0 or 100) this component becomes — capturing "how stretched is the current run of consecutive up/down closes."

### 3. PercentRank(ROC(1), 100)
- Compute the 1-day Rate of Change (ROC(1) = today's % price change).
- PercentRank ranks today's ROC(1) value against the prior 100 days of ROC(1) values, returning the percentile (0-100) of today's move relative to the last 100 days.
- A value near 100 means today's move was larger (more positive) than nearly all moves in the past 100 days; near 0 means it was one of the smallest/most negative.

## How to Use
- ConnorsRSI is a **mean-reversion** tool, not a trend tool — low readings (e.g. <10-30) flag oversold/stretched-down conditions, high readings (e.g. >50-90) flag a resumption of strength after a pullback.
- Used in [[strategies/Quantified-MA-Mean-Reversion]] as an **exit trigger**: after a long entry, exit when ConnorsRSI crosses above 50 (looser, faster exit) or above 70 (stricter, holds for a stronger bounce).
- Because it averages three differently-scaled signals (price RSI, streak RSI, percentile rank), it tends to be smoother and less noisy than a single RSI(3) reading alone.

## Variants / Parameters
- Default (3,2,100) is the standard; shorter streak/RSI periods or shorter PercentRank lookbacks (e.g. 50) make it more reactive.

## Common Mistakes
- Treating ConnorsRSI like classic RSI(14) — its short lookbacks make it far noisier and only meaningful for short-term mean-reversion timing, not trend assessment.
- Forgetting the streak component resets to 0/flips sign on any reversal day, which can cause sharp jumps in the composite value.

## Related Concepts
- [[concepts/RSI]] — ConnorsRSI's component #1 is a short-period RSI; existing RSI page documents the classic 14-period trend-following use (40-80/20-60 bands), which is a different regime than ConnorsRSI's short-term mean-reversion use.
- [[strategies/Quantified-MA-Mean-Reversion]] — primary application of ConnorsRSI in this wiki, used as an exit-timing filter.

## Examples in This Wiki
- Worked streak-duration and PercentRank examples from the source book are summarized in [[sources/Connors-MA-Quantified-Approach-2013]].

## Sources
- [[sources/Connors-MA-Quantified-Approach-2013]] — Appendix: full ConnorsRSI(3,2,100) derivation with worked examples
