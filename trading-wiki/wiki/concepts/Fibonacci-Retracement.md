---
title: "Fibonacci Retracement & Extension"
category: concept
tags: [fibonacci, retracement, extension, golden-zone, support-resistance, targets]
created: 2026-07-19
updated: 2026-07-19
sources: 1
related: [concepts/Support-Resistance.md, concepts/Elliott-Wave.md, concepts/RSI.md, concepts/Premium-Discount-Zones.md]
---

# Fibonacci Retracement & Extension

## Definition
A grid of horizontal levels drawn between a **swing high** and **swing low** at ratios derived from the Fibonacci sequence. **Retracement** levels measure how far a pullback *inside* a prior move is likely to go before the trend resumes; **extension** levels project *beyond* the move to set profit targets. The tool measures nothing on its own — it marks where price *tends* to react. It is a confluence input, not a standalone signal.

## Levels
| Ratio | Role | Notes |
|-------|------|-------|
| 0.236 | Shallow retracement | Very strong trends only pull back this far |
| 0.382 | Moderate retracement | Common in fast trends |
| 0.500 | Half give-back | Not a true Fib ratio, but widely watched |
| **0.618** | **Golden ratio** | The most-watched retracement; deepest "healthy" pullback |
| **0.786** | Deep retracement | Last defense before the move is negated |
| 1.000 | Full retrace | Move is invalidated |
| **1.272 / 1.618 / 2.618** | **Extension targets** | Projected beyond the swing for profit-taking |

**Golden zone: 0.5 → 0.786.** Pullback entries in the direction of the trend are preferred inside this band — deep enough to get a good price, shallow enough that the trend is likely intact.

## How to Plot (4-step)
1. **Identify the trend** (up or down) on the working timeframe.
2. **Find the recent swing high and swing low** that bound the move.
3. **Drag the tool along the impulse:** in an **uptrend** anchor swing low (1.0) → swing high (0.0), so retracement levels sit *below* current price as support; in a **downtrend** anchor swing high → swing low, so levels sit *above* as resistance. (Convention varies by platform — what matters is that 0 is at the *end* of the impulse and 1.0 at its origin.)
4. **Trade the reaction, not the line:** wait for a candle/pattern to confirm rejection or support at a level before entering. Price *between 0.236–0.50 is a moderate retracement*; the *0.5–0.786 golden zone* is the higher-conviction pullback-entry band.

## How to Use

### Retracement — pullback entries
- **Uptrend:** buy the pullback into the golden zone; stop below 0.786 (or below the swing low). A hold at 0.382–0.618 with a bullish candle is a classic continuation entry.
- **Downtrend:** short the bounce into the golden zone; stop above 0.786 (or the swing high).

### Extension — profit targets
The **fib-extension tool** projects targets from a 3-point A-B-C selection (A = start, B = end of impulse, C = the retracement pullback). Levels at 0.618/1.0/1.618 beyond the move become take-profit / trend-exhaustion zones. Exit (or trail tighter) when price shows reversal signs at an extension level rather than holding for the next one.

### Fibonacci + RSI confluence (bullish momentum)
A higher-conviction long combines a **61.8% retracement** with an **RSI confirmation**:
- **Entry:** price retraces ~61.8% of the prior up-leg **and** [[concepts/RSI]] is turning up out of its oversold zone.
- **Stop:** below the entry candle's low or the retracement level.
This pairs a *location* edge (Fib) with a *momentum* edge (RSI) — neither alone would justify the entry.

## Variants / Parameters
- **Anchoring choice dominates everything.** Different swing selections produce different grids; use the most obvious, structurally significant high/low, and prefer levels that align across timeframes (fib confluence).
- **Fib clusters:** when retracement levels from two different swings overlap, that price is a stronger reaction zone.
- **In Elliott Wave**, wave retracements/extensions cluster at Fib ratios (wave 2 often 0.5–0.618 of wave 1; wave 3 commonly 1.618× wave 1) — see [[concepts/Elliott-Wave]] and the classic-EW Fibonacci statistics in [[concepts/McDowell-Probability-Matrix]].

## Common Mistakes
- **Trading the line, not the reaction** — a level is a *zone of interest*, not an automatic entry. Wait for price confirmation.
- **Arbitrary anchoring** — snapping the tool to insignificant wicks produces meaningless levels; garbage in, garbage out.
- **Using Fib in isolation** — its edge appears only in confluence with structure ([[concepts/Support-Resistance]]), trend, and momentum.
- **Fighting the trend at a level** — retracements are *with-trend* entries; buying a 0.618 in a confirmed downtrend is catching a knife.
- **Forgetting invalidation** — a decisive close beyond 0.786 (toward 1.0) means the pullback is now a reversal; the setup is dead.

## Related Concepts
- [[concepts/Support-Resistance]] — Fib levels are strongest when they coincide with prior structural S/R.
- [[concepts/Premium-Discount-Zones]] — the SMC 0.5-anchored premium/discount model is the same swing-range logic expressed as equilibrium bands.
- [[concepts/RSI]] — momentum confirmation for the Fib-retracement entry.
- [[concepts/Elliott-Wave]] — wave targets and retracements are defined in Fibonacci ratios.

## Examples in This Wiki
- [[sources/FinanceWithSunil-telegram]] and [[sources/EW-Techniques-Simplified-McDowell]] both lean on Fib retracement/extension for level-setting.

## Sources
- [[sources/Fingrad-Trading-Infographics-Collection]] (2026-07-19) — plotting steps, golden zone (0.5–0.786), fib-extension target tool, Fib + RSI confluence entry.
