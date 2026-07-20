---
title: "Koroush AK — Breakout Momentum (1-Minute)"
category: strategy
tags: [breakout, momentum, intraday, crypto, 1-minute, smma-30, 1R]
timeframe: intraday
created: 2026-07-06
updated: 2026-07-06
sources: 1
related: [sources/X-KoroushAK-Breakout-Strategy-20260128, concepts/VWAP, concepts/EMA]
---

# Koroush AK — Breakout Momentum (1-Minute)

## Core Idea
Long resistance / short support **only when the environment favours continuation**. A breakout is worth taking when three environmental filters agree: the *approach* is a slow grinding staircase (not a spike), *volume* is gradually rising (not flat and not spiking), and the price↔SMMA-30 crossover count is low (clean trend, not chop). All three aligned = full-size A-grade entry; partial fail = reduced size; two-plus fails = pass.

Author (@KoroushAK) is a crypto trader — the strategy is designed and demonstrated on crypto 1-minute charts. Do **not** transplant verbatim to Indian-equity swing without re-testing timeframe assumptions.

## Setup Criteria
Pre-conditions for a long-side momentum breakout at resistance:

- **Level quality:** consistent S/R drawn on the primary timeframe (Koroush uses his own S/R masterclass process; this wiki treats S/R construction as an external prerequisite for now).
- **Filter 1 — Approach shape:** price grinds into the resistance level with a staircase of higher lows over multiple candles. Rejects fast-spike approaches.
- **Filter 2 — Volume:** gradually increasing (or at minimum steady) as price approaches the level. Flat volume ⇒ no participation; sudden spike near the level ⇒ climax, not fuel.
- **Filter 3 — SMMA-30 crossover count:** load the Smoothed Moving Average indicator with length = 30 on the trading timeframe. Count how often price crosses it in the run-up. Few crossovers ⇒ directional regime, tradeable; many ⇒ chop, skip.

Sizing rule: all three green ⇒ full risk. Any single filter degraded ⇒ reduce size. Two or more fail ⇒ don't take the trade.

## Entry Rules
1. Identify resistance level on the primary timeframe.
2. Switch to the **1-minute chart** for entry timing.
3. Wait for **two consecutive 1-minute candles to close fully above resistance**. Both closes above the level — not just wicks.
4. Preset a **limit order AT the prior resistance level** (which is now support). Do NOT market-buy above resistance after confirmation.
5. Let price come back to the limit on the post-breakout pullback. If price never returns, no trade — pass rather than chase.

Rationale for the limit-at-level rule (not stop-order-above-level): the 2-candle-close already confirms the break. Chasing the confirmation with a market order pays a wider spread and worsens the stop distance, killing R/R.

## Exit Rules

### Stop loss
- Place at the **most recent valid swing low before the breakout** (swing low = lowest wick of the most recent pullback).
- **1% floor rule:** measure the distance from entry to that swing low using the ruler tool. If the distance is < 1% (of price), drop to the *next* swing low down. Sub-1% stops get eaten by normal volatility and stop-hunt wicks.

### Take profit
- **Initial target = 1R**, i.e., same distance as the stop but in the profit direction (1:1 R/R).
- Rationale: momentum breakouts hit 1R fast due to continuation follow-through; the goal at this stage is a *repeatable* high-probability slice, not the whole move.
- Extension protocol: after 30+ journalled trades, review how far winners run beyond 1R and extend the target only when the data supports it. Do not extend targets discretionarily.

## Timeframe
- **Execution:** 1-minute.
- **Level identification:** primary timeframe (author does not lock this — implicitly whatever timeframe the trader normally reads S/R on; 5m–1h typical for crypto).
- **Asset class:** demonstrated on crypto. Applicability to equities is untested here — see "Contradictions" below.

## Best Market Conditions
- Directional / trending regime on the primary timeframe.
- Low chop, few price↔SMMA-30 crossovers.
- Rising volume in the accumulation into the level.
- Session-anchored VWAP slope aligned (see [[concepts/VWAP]] for a compatible independent read — steep slope + widening bands is the VWAP-side confirmation of the same regime).

## Worst Market Conditions
- Choppy sideways price action with many SMMA-30 crossovers.
- Flat or spike-y volume — either no participation or exhaustion at the level.
- News-driven vertical spikes into resistance (climax pattern; strategy explicitly wants to *skip* these, not fade them — this is a momentum strategy, not a reversal strategy).
- News-halted or extremely thin books (crypto low-cap after listing pumps).

## Backtest / Track Record
- No formal backtest published with the article. Coach-trade examples are shown but not aggregated into a hit-rate.
- **Recommended paper protocol before real capital:** journal 30 trades using the exact filter checklist (approach shape / volume / SMMA-30 crossovers). Track (a) how often all three align, (b) hit rate given all-three-align, (c) average multi-of-R on winners.

## Examples
The article cites three coach-trade examples (Brandon, Josh, Kim) but only in image form; screenshots not extractable from the X article API. Placeholder for future journal entries here once the strategy is being paper-traded.

## Related Concepts
- [[concepts/VWAP]] — session-anchored VWAP gives an independent slope/bandwidth read that agrees with the SMMA-30 crossover filter (both are trying to detect trend-vs-chop). Using them together provides confluence.
- [[concepts/EMA]] — SMMA-30 is a smoothed moving average variant; conceptually adjacent to EMA-30 but slower to react.
- [[strategies/Minervini-SEPA]] and [[strategies/Parabolic-Short-First-Red-Day]] — both use R-multiple thinking; Koroush's 1R baseline is a systematic-first version of the same idea.

## Contradictions with Existing Wiki
- Uses **1-minute execution** and applies to **crypto**; the swing-oriented Indian-equity strategies on this wiki (Minervini-SEPA, TechnoFunda-Swing, VCP scanners) operate at daily/weekly on a completely different microstructure. Do not port the 1m/1R execution rules to those without independent testing.
- **"Limit AT the level, not above"** is a distinct entry philosophy from the standard "buy-stop above pivot" convention in Minervini-style equity swings. Both are internally consistent; the difference is that Koroush's 2-candle-close *is* the confirmation, so the pullback fill is the honest cost basis.

## Sources
- [[sources/X-KoroushAK-Breakout-Strategy-20260128]]
