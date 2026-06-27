---
title: "Elliott Wave 5 Catch (Wave 4 Retracement Entry)"
category: strategy
tags: [elliott-wave, wave-5, fibonacci, trailing-stop]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [concepts/Elliott-Wave.md, concepts/McDowell-Probability-Matrix.md, strategies/EW-Flat-Bottom-Breakout.md, strategies/EMA-Pullback.md]
timeframe: swing
---

# Elliott Wave 5 Catch (Wave 4 Retracement Entry)

## Core Idea
Enter right after Wave 4 completes its retracement of Wave 3, riding Wave 5 to its Fibonacci extension target with an aggressive trailing stop.

## Setup Criteria
- A clearly identified Wave 3 (steepest move, highest volume, OWL histogram extreme — see [[concepts/Elliott-Wave]]).
- Fibonacci retracement drawn from end of Wave 2 to end of Wave 3 defines the Wave 4 target zone (38.2-61.8%).
- Price retraces into that zone. **If the retracement overshoots past 75%, abandon this setup** — it's likely a Wave 2 of a new impulse, not a Wave 4 (see [[concepts/Elliott-Wave]] re-labeling note).

## Entry Rules
**Bullish:**
1. Wait for price to enter the 38.2-61.8% Wave 4 retracement zone and bullishness to return (OWL histogram flips positive).
2. Draw Fibonacci extension using end of Wave 2 → end of Wave 3 → end of Wave 4 as anchors; this projects the Wave 5 target zone (61.8-100%).
3. Wait for a higher low then higher high after the Wave 4 low.
4. Enter when price exceeds that higher high.

**Bearish:** mirror — retracement into 38.2-61.8% zone with bearish OWL flip, lower high then lower low, enter below the lower low.

## Exit Rules (profit target + stop loss)
- Initial stop: below the Wave 4 low (bullish) / above the Wave 4 high (bearish), or the most recent support/resistance formed after Wave 4.
- Trail stop under key support levels, especially once Wave B (within Wave 4) is breached by Wave 5 progress.
- **Inside the Wave 5 Fibonacci target zone (61.8-100% extension)**: switch to a 3-bar-back trailing stop — stop placed at the low (bullish) / high (bearish) of the 3rd price bar back from current. Exit in full when that stop is hit.
- Require minimum 2:1 reward:risk from entry to the Wave 5 target zone; skip the trade if not met.

## Timeframe
Swing (source examples are daily charts; apply [[concepts/Elliott-Wave]] multi-timeframe alignment for confirmation).

## Best Market Conditions
- Clean impulsive Wave 3 with a simple ABC zigzag Wave 4 (per the alternation rule, if Wave 2 was complex, Wave 4 is more likely simple and tradeable this way).
- RSI(9, 80/20) confirms: no band penetration during Wave 4, then renewed momentum into Wave 5.

## Worst Market Conditions
- Complex (flat/irregular/triangle) Wave 4 corrections — these are "messy" and McDowell's advice is to pass and find another chart.
- Wave 4 retracement exceeding 76.4% (likely mislabeled — see Core Idea note).

## Backtest / Track Record
None recorded yet — source book provides illustrative chart examples only (DZZ, TSLA).

## Examples
- None logged in this wiki yet.

## Related Concepts
- [[concepts/Elliott-Wave]] — wave statistics and OWL/RSI settings
- [[concepts/McDowell-Probability-Matrix]] — score the wave count before entry
- [[strategies/EMA-Pullback]] — similar "buy the pullback" structure using EMA instead of Fibonacci/EW
- [[strategies/EW-Flat-Bottom-Breakout]] — companion setup earlier in the trend (Wave 3 entry)

## Sources
- [[sources/EW-Techniques-Simplified-McDowell]] (2026-06-15)
