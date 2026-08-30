---
title: "Forced-Participation Reversal (Chris Kmer)"
category: strategy
timeframe: intraday
tags: [order-flow, auction-market-theory, absorption, volume-profile, gex, futures, mnq, prop-trading, discretionary]
created: 2026-08-29
updated: 2026-08-29
sources: 1
related: [concepts/Order-Flow, concepts/Volume-Profile, concepts/Gamma-Exposure-GEX, concepts/Premium-Discount-Zones, concepts/Market-Structure-CHOCH-BOS, concepts/Prop-Trading-Funded-Model, entities/Chris-Kmer, sources/YT-Chris-Kmer-World-Cup-Order-Flow]
---

# Forced-Participation Reversal (Chris Kmer)

## Core Idea

Trade the moment one side of the auction has **committed size and is not being rewarded
for it**. A buyer who is offside has only two exits: defend/add, or sell to get out — and
that forced selling is itself the next move. So the setup is not a pattern; it is a
**condition**: aggressive effort at a location, no result, then a dominance shift.

Deliberately *not* traded in balance. Balance means both sides are comfortable and nobody
is forced to do anything.

## Setup Criteria

Four gates, checked in order. All four must hold.

1. **Environment** (pre-open only, never while price is moving)
   - Higher-timeframe (1h/4h) structure: value building **up**, **down**, or sideways.
   - Trade *with* that structure — no top-calling, no bottom-calling.
   - **Gamma regime** ([[concepts/Gamma-Exposure-GEX]]): negative gamma = expect
     amplified, faster moves; positive gamma = expect damped moves and failed breakouts.
     Note call wall / put wall / gamma flip as context, not as entry levels.
2. **Location** — two definitions of "discount" that must agree
   - Below the **value area low** of the profile ([[concepts/Volume-Profile]]); and
   - Inside the **0.705 / 0.786 / 0.886** Fibonacci band drawn swing-low → swing-high.
   - **Reject** if the fib band falls *inside* value area.
   - Preferred: the pullback is into an **inefficient / low-volume node** — price crossed
     it fast, little business was transacted there.
   - Some internal structure (a swing point, ideally a sweep) before entering the zone.
3. **Confirmation** — footprint order flow on **5-minute** candles
   - Aggressive sellers concentrated at the candle's **lower extreme** (negative delta
     ladder, intra-candle POC at the wick) = effort.
   - No downward result from that effort = **absorption**.
   - Dominance shift: bullish close → next candle pulls back → sellers try again and
     **fail higher** → buy-side imbalances (≥ **400%**) light up.
   - **Two failed attempts required.** One is whipsaw.
4. **Participation floor** — ≥ **20,000 contracts per 5-min MNQ candle**. Below it, stand
   down entirely. This, plus the session window, is what holds the strategy to **0–2
   trades a day**.

## Entry Rules

Enter on the **second** seller failure flipping bullish, with buy-side imbalance
confirmation. (Mirror-image for shorts in a value-down structure.)

## Exit Rules

- **Stop** — just beyond the extreme of the failed sellers. That level breaking *is* the
  idea being wrong; nothing else is.
- **Invalidation before entry** — price closing beyond the **0.886**. The pullback should
  have completed before that; past it, the trade is not taken at all.
- **First checkpoint** — do buyers **reclaim the value area**? Spending aggression and
  stalling below it → move to break-even or cut.
- **Targets** — POC, or a **swing high/low** (resting orders cluster at swing points and
  psychological levels). Trail behind continued effort-with-result; trail early into a
  call wall.

## Timeframe

Intraday. Structure on 1h/4h, location on 15m, execution on 5m (occasionally 1m). Traded
in the **first 90 minutes** after the New York open, occasionally the Asia session.

## Best Market Conditions

High participation, a clear higher-timeframe value structure, and a fast/inefficient move
into discount. Negative gamma helps — the squeeze out of trapped positioning is amplified
by dealer hedging pushing the same way.

## Worst Market Conditions

Thin volume (the explicit stand-down), balanced/rotational markets with no forced side,
and slow grinds into the lunch hour. Positive gamma argues against continuation targets.

## Backtest / Track Record

**None, in the sense this vault means it.** What exists:

- Claimed **100% return** in one month of the Robbins World Cup micro day-trading
  division — a single month of a percentage-ranked contest, a format that surfaces the
  right tail of a high-variance field.
- Self-reported **60–65% win rate, 1.5–2R, profit factor ~1.8**. These three are
  mutually inconsistent (1.5R at 62.5% implies PF ≈ 2.5, not 1.8); the reconciliation is
  that 1.5R is the *target* and frequent break-even/trailing exits pull the realised
  average win to ~1.1R. Treat **PF 1.8** as the number with weight behind it.
- Implied sizing: a 100% month at that expectancy over ~30 trades needs **4–8% of account
  risked per trade**. See the working in [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]].

**Not testable with this repo's data.** The confirmation gate needs tick-level footprint
and delta, which nothing here carries; the environment gate needs an intraday gamma feed.
Filed as documented process, not as a candidate for the harness.

## Related Concepts

[[concepts/Order-Flow]] · [[concepts/Volume-Profile]] · [[concepts/Gamma-Exposure-GEX]] ·
[[concepts/Premium-Discount-Zones]] · [[concepts/Market-Structure-CHOCH-BOS]] ·
[[concepts/Prop-Trading-Funded-Model]] · [[strategies/Prop-Scalp-NQ-Initial-Balance]]
(the vault's other intraday NQ process — same instrument, different trigger logic)

## Sources

- [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]] — whiteboard walkthrough by
  [[entities/Chris-Kmer]], 2026-08-29.
