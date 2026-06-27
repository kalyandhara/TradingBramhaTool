---
title: "Elliott Wave Flat Bottom Channel Breakout"
category: strategy
tags: [elliott-wave, breakout, wave-3, channel]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [concepts/Elliott-Wave.md, concepts/McDowell-Probability-Matrix.md, strategies/EW-Wave5-Catch.md]
timeframe: swing
---

# Elliott Wave Flat Bottom Channel Breakout

## Core Idea
Catch Wave 3 — the strongest, highest-volume wave — as early as possible by trading the breakout from a narrow basing channel that forms after the prior trend's Wave 5 completes.

## Setup Criteria
- A completed Wave 5 of the prior trend (use [[concepts/Elliott-Wave]] / OWL histogram to confirm exhaustion: histogram fails to make a new extreme, RSI(9, 80/20) fails to penetrate the band).
- Price then bases in a narrow horizontal channel for at least 20 bars — the longer and narrower, the better.
- Mark channel resistance (top) and support (bottom) with horizontal lines.

## Entry Rules
**Bullish:**
1. Alert on a close above channel resistance (breakout).
2. Wait for a higher low, then a higher high after the breakout.
3. Enter when price exceeds that second higher high.
4. OWL price oscillator histogram (5/35 on low) must be positive (bullish) at entry.

**Bearish:** mirror — breakout below channel support, wait for lower high then lower low, enter below the second lower low, OWL histogram must be negative.

## Exit Rules (profit target + stop loss)
- Initial stop: below the higher low (bullish) / above the lower high (bearish), or at the channel boundary if tighter.
- Trail stop under each subsequent higher low (bullish) / above each subsequent lower high (bearish) as Wave 3 develops.
- Target: Fibonacci extension of Wave 1→2→3 — Wave 3 commonly extends 161.8-261.8% of Wave 1 (see [[concepts/Elliott-Wave]] statistics). Consider scaling out near 1.618x.

## Timeframe
Swing (designed around daily charts in the source material, but the channel-breakout logic is timeframe-agnostic — apply the [[concepts/Elliott-Wave]] multi-timeframe pairing when selecting confirmation timeframe).

## Best Market Conditions
- Clean basing after a clearly exhausted prior trend (low volatility, tight range).
- OWL histogram near zero / flat during the base, then a clean directional flip on breakout.

## Worst Market Conditions
- Choppy, wide-ranging "channels" that aren't really flat — these tend to be complex corrections (Wave 4 of a larger degree), not pre-Wave-1/3 bases. If the channel is wide or messy, skip it.

## Backtest / Track Record
None recorded yet — source book provides illustrative chart examples only (AMMRQ, SPWR, LEE, TSLA).

## Examples
- None logged in this wiki yet.

## Related Concepts
- [[concepts/Elliott-Wave]] — wave statistics and OWL/RSI settings used for confirmation
- [[concepts/McDowell-Probability-Matrix]] — score the resulting wave count before sizing the trade
- [[strategies/EW-Wave5-Catch]] — companion setup for entries later in the trend

## Sources
- [[sources/EW-Techniques-Simplified-McDowell]] (2026-06-15)
