---
title: "Order Block (SMC demand/supply zone)"
category: concept
tags: [smc, order-block, demand-zone, supply-zone, bos, choch, displacement, price-action]
created: 2026-07-25
updated: 2026-07-25
sources: 0
related:
  - concepts/Fair-Value-Gap.md
  - concepts/Fair-Value-Breaker-FBG.md
  - strategies/RSI-60-40-Setup.md
  - analyses/Dashboard-UI-Roadmap.md
---

# Order Block (SMC demand/supply zone)

## Definition
An **order block** is the last opposite-direction candle before a strong move
that **breaks market structure**. A *bullish* order block is the last **down**
candle before a bullish **displacement** that takes out a prior swing high
(Break of Structure / Change of Character). The premise from Smart-Money-Concepts
price action: institutions accumulated within that candle's range before driving
price up, so the zone becomes **latent demand** — when price returns to it, unfilled
interest tends to defend it and produce a bounce.

The zone is the order-block candle's range `[low, high]` (some traders use the
body). It stays valid ("unmitigated") until price **closes back below** it, which
"consumes"/violates the block.

## How to Use
1. **Find the displacement + structure break** — a decisive up-move (≥ ~1 ATR)
   whose close clears the most recent swing high (BOS if already uptrending, CHOCH
   if it's the first counter-trend break).
2. **Mark the order block** — the last down-close candle immediately before that
   move. Its `[low, high]` is the demand zone.
3. **Wait for the retest** — price pulls back **into** the zone and **holds above
   its low**. That mitigation is the entry trigger, not the initial displacement.
4. **Trade plan** — enter in the zone, **stop just below the zone low**, target the
   displacement extension (or a 2R minimum). Favourable because the stop is tight
   (zone low) while the target is the prior impulse.

## Variants / Parameters
- **Bullish vs bearish** — mirror logic; the bearish block is the last *up* candle
  before a down displacement that breaks a swing low.
- **Body vs wick zone** — body-only is stricter (fewer, cleaner retests); full
  range catches more.
- **BOS vs CHOCH** — a block formed on a BOS is a *continuation* demand zone
  (with-trend, generally higher-probability); a CHOCH block is a *reversal* zone
  (counter-trend, treat with more care).
- **Freshness** — the first retest of an unmitigated block is the highest-quality;
  each subsequent tap weakens it.

## Common Mistakes
- **Trading the displacement, not the retest** — chasing the impulse bar instead
  of waiting for price to return to the zone.
- **Ignoring mitigation/violation** — a block that price already closed through is
  spent; don't treat it as fresh demand.
- **No structure break** — a down candle before a weak drift up is *not* an order
  block; the displacement must actually break structure.
- **Volume blind** — a displacement on below-average volume is a weaker block
  (our detector flags this explicitly).

## Related Concepts
- [[concepts/Fair-Value-Gap]] — the imbalance/gap left *by* a displacement; often
  sits just above a bullish order block (confluence).
- [[concepts/Fair-Value-Breaker-FBG]] — a failed FVG flipped into a breaker; a
  cousin structure on the reversal side.
- [[strategies/RSI-60-40-Setup]] — another with-trend continuation entry; an order
  block that lands at EMA support is confluent with the RSI-40 pullback.

## Examples in This Wiki
- **`scan_order_block`** ([scanner_templates.py](tools/scanner_templates.py),
  registered "Order Block Retest", category Entry) implements exactly this:
  `detect_bos_choch` finds the structure break, the last down candle before it is
  the zone, freshness/mitigation are checked, and it fires on the retest with a
  structured entry/stop/target. Being the first scanner to emit a structured plan,
  it is also the first to exercise the [[analyses/Backtest-Harness]] R-simulation
  (v1 read: low win-rate, favourable payoff, ~+0.11R expectancy — measured, gross).

## Sources
- Greenfield build (2026-07-25) from standard SMC price-action definitions; no
  single ingested source. [[analyses/Dashboard-UI-Roadmap]] Phase 2.
