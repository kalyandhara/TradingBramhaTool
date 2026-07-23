---
title: "Fair Value Breaker (FBG)"
category: concept
tags: [fbg, breaker-block, fair-value-gap, reversal, smc, ict, liquidity, fibonacci, displacement]
created: 2026-07-22
updated: 2026-07-22
sources: 1
related:
  - concepts/Fair-Value-Gap.md
  - concepts/Order-Blocks.md
  - concepts/Market-Structure-CHOCH-BOS.md
  - concepts/Fibonacci-Retracement.md
  - analyses/FVG-FBG-Fibonacci-Chart-Roadmap.md
---

# Fair Value Breaker (FBG)

## Definition
An FBG is a **failed FVG that flips into a reversal zone**. A fair-value gap ([[concepts/Fair-Value-Gap]]) implies price should continue in the displacement direction and treat the gap as support/resistance on the retrace. When price instead returns to the gap and **closes through the opposite boundary**, the original imbalance's thesis is broken — the failed gap becomes a *breaker*, and the boundary it broke now acts in the opposite direction. This is the FVG-specific member of the broader breaker-block family ([[concepts/Order-Blocks]]).

An FVG becomes an FBG when **all four** hold:
1. Price returns to the FVG.
2. Price breaks through the **opposite** side.
3. Price **closes beyond** the FVG boundary (a close, not a wick).
4. The original FVG direction fails.

## How to Use

### Why it works
A broken imbalance means the participants who executed the original displacement are now **trapped** on the wrong side — a failed displacement forces them to cover, which adds counter-trend momentum. That trapped-liquidity mechanic is what gives a breaker its reversal thrust, and why it is a *reversal* tool where the FVG is a *continuation* tool.

### Entry (retail-friendly)
- **Wait for the retest** of the breaker block — do not enter on the break itself (the recurring retail error is entering too early on breakers).
- Enter at the **breaker-block midpoint**.
- **Volume confirmation required** — a break on high volume is a *strong* breaker; a break on low volume is a *fake* breaker and usually leads to continuation, not reversal.
- **Stop** beyond the breaker block (above for a bearish breaker, below for a bullish one).

### Fibonacci confluence (the high-probability version)
Draw the Fib across the swing that produced the break (swing high → swing low for a bearish breaker):
- **Strong breaker:** price retraces to **Fib 0.618–0.705**, rejects strongly, volume spikes → the ideal FBG entry zone.
- **Weak breaker:** price retraces only to **0.382**, no strong rejection, weak volume → expect continuation, not reversal.
- **Entry:** 0.618–0.705 retracement; **SL** above the breaker block; **TP** at Fib 0.0 / the liquidity pool beyond. See [[concepts/Fibonacci-Retracement]].

### Exit
- **TP1:** previous swing.
- **TP2:** opposite liquidity.
- **TP3:** higher-timeframe imbalance.

## Variants / Parameters
- **Close-through vs wick-through** for the "break" that creates the FBG: the wiki's FVG lifecycle already carries this exact tension (see the contradiction callout in [[concepts/Fair-Value-Gap]]). An FBG should be defined on a **close** through the opposite boundary — a wick-through is a failed-fill, not a confirmed breaker.
- **Breaker vs order block:** a breaker is a *failed* zone that flips polarity; an order block is the last opposing candle before a move. Related but distinct — see [[concepts/Order-Blocks]].

## Common Mistakes
- **Entering on the break, not the retest** — the break is the trigger to *watch*; the retest is the entry.
- **Ignoring volume** — a low-volume break is a fake breaker; without the volume spike the "reversal" is often just a liquidity grab before continuation.
- **Retrace too shallow** — a breaker that only pulls back to 0.382 has not proven rejection; treat 0.618–0.705 as the qualifying zone.
- **Trading against HTF structure** — like the FVG, the FBG is an entry-timing tool; the reversal thesis needs a market-structure shift ([[concepts/Market-Structure-CHOCH-BOS]]) behind it.

## Related Concepts
- [[concepts/Fair-Value-Gap]] — the FBG is a failed FVG; same primitive, opposite intent (continuation → reversal).
- [[concepts/Order-Blocks]] — the general breaker-block family.
- [[concepts/Fibonacci-Retracement]] — the 0.618–0.705 retest zone that qualifies a strong breaker.
- [[concepts/Market-Structure-CHOCH-BOS]] — the structure shift that should accompany a valid breaker.

## Examples in This Wiki
- Not yet implemented on the chart. Planned as a detector extending `tools/fvg.js` — see [[analyses/FVG-FBG-Fibonacci-Chart-Roadmap]].

## Sources
- [[sources/FVG-FBG-Fibonacci-Retail-Framework]]
