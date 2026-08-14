---
title: "Equal Highs / Equal Lows (EQH/EQL)"
category: concept
tags: [equal-highs, equal-lows, eqh, eql, liquidity, smc, smart-money, stop-hunt, luxalgo, double-top-bottom]
created: 2026-07-16
updated: 2026-07-16
sources: 1
related: [concepts/Market-Structure-CHOCH-BOS, concepts/Order-Flow, concepts/Reversal-Chart-Patterns, concepts/Support-Resistance, concepts/Premium-Discount-Zones]
---

# Equal Highs / Equal Lows (EQH/EQL)

## Definition
**Equal Highs (EQH)** are two or more swing highs at effectively the same price; **Equal Lows (EQL)** are two or more swing lows at the same price. In SMC reading they mark **resting liquidity** — a shelf of stop-loss and breakout orders sitting just beyond the equal level. Because that liquidity is obvious, price often **sweeps** it (runs slightly past the equal level to trigger the stops) and then reverses — the "liquidity grab / stop hunt" that frequently precedes a [[concepts/Market-Structure-CHOCH-BOS|CHoCH]]. Structurally identical to a **double top / double bottom** ([[concepts/Reversal-Chart-Patterns]]), but framed as *liquidity to be taken* rather than as a reversal pattern in itself.

## How to Use

### Mechanical detection (from the [[sources/LuxAlgo-Smart-Money-Concepts-Pine|LuxAlgo SMC]] reference)
- Detected on a short pivot lookback (default confirmation = 3 bars each side).
- A new pivot high is tagged **EQH** if `|new high − previous pivot high| < threshold × ATR(200)`; new pivot low tagged **EQL** by the mirror test. The two equal points are joined with a dotted line and labeled.
- **Threshold** default 0.1 (range 0–0.5). Lower = fewer but more exact equals; it's an ATR-scaled tolerance so "equal" auto-adapts to each symbol's volatility rather than requiring a tick-perfect match.

### Reading it
- EQH overhead = a **liquidity target above**; in a range, price is often drawn up to sweep it. EQL below = liquidity target below.
- The high-probability play is *not* the breakout of the equal level — it's the **failure** of that breakout: price sweeps just past EQH, fails to hold, and prints a CHoCH back down (the trapped-breakout-buyers fade, same mechanic as [[strategies/False-Break-Buildup-Trading]]).
- EQH/EQL are most meaningful *inside* a range or at the boundary of a swing; a single equal touch in a strong trend is weak signal.

## Variants / Parameters
- **Bars confirmation** (pivot strength, default 3) — larger = stronger but later-confirmed equals.
- **Threshold** (0.1 default) — ATR-fraction tolerance for "equal."
- Community variants sometimes require the sweep + reversal to have *already happened* before marking the level as valid liquidity; the LuxAlgo reference marks the equality as soon as the second pivot confirms, independent of whether it later gets swept.

## Common Mistakes
- **Buying the breakout of equal highs.** Equal highs are where breakout buyers get trapped — the SMC read is that the level exists to be swept, not broken cleanly. Treat a break as suspect until it holds on a retest.
- Requiring pixel-perfect equality — real equals cluster within a small band; the ATR threshold captures this. Demanding exact ticks misses most valid pools.
- Confusing EQH/EQL (a *liquidity* read, actionable on the sweep-and-fail) with plain horizontal [[concepts/Support-Resistance]] (a *level* read). Same geometry, different intent.
- Trading every equal pair — only those near a swing extreme or range boundary carry real liquidity weight.

## Related Concepts
- [[concepts/Market-Structure-CHOCH-BOS]] — a liquidity sweep of EQH/EQL is the classic precursor to a CHoCH; the sharp wick beyond the prior swing that page describes is often exactly an equal-highs sweep.
- [[concepts/Order-Flow]] — EQH/EQL are visible resting-stop clusters; the sweep is the same stop-hunt / iceberg absorption mechanic documented there.
- [[concepts/Reversal-Chart-Patterns]] — EQH ≈ double top, EQL ≈ double bottom; that page's swing-equality detection is the same test framed as a chart pattern. A port could share the pivot code and add the ATR-threshold equality check.
- [[concepts/Premium-Discount-Zones]] — EQH forming in premium (sell zone) or EQL in discount (buy zone) is a higher-conviction liquidity target.
- [[strategies/False-Break-Buildup-Trading]] — the sweep-and-fail of an equal level is the trapped-trader fade in SMC clothing.

## Examples in This Wiki
- **No dedicated port yet** — the existing [[concepts/Reversal-Chart-Patterns]] double-top/bottom detector in `tools/` is the closest primitive; adding an ATR-threshold equal-pivot tag would give the liquidity-pool framing directly.
- No live-ticker example yet.

## Sources
1. [LuxAlgo-Smart-Money-Concepts-Pine](../sources/LuxAlgo-Smart-Money-Concepts-Pine.md) — Pine v5 indicator by [[entities/LuxAlgo]] (CC BY-NC-SA 4.0), ingested 2026-07-16; the ATR-threshold equality test, dotted-line join, and bars-confirmation parameter are from this script.
