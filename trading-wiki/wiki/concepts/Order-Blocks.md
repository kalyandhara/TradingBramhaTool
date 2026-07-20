---
title: "Order Blocks (OB)"
category: concept
tags: [order-block, smc, smart-money, ict, supply-demand, mitigation, luxalgo, institutional-footprint]
created: 2026-07-16
updated: 2026-07-16
sources: 1
related: [concepts/Market-Structure-CHOCH-BOS, concepts/Fair-Value-Gap, strategies/Supply-Demand-Zone-Trading, concepts/Support-Resistance, concepts/Premium-Discount-Zones]
---

# Order Blocks (OB)

## Definition
An **order block** is the last opposing candle *before* an impulsive move that breaks structure — the candle where institutions are presumed to have loaded a position before driving price away. A **bullish OB** is the last down-candle before a strong up-move that breaks a swing high (a demand footprint); a **bearish OB** is the last up-candle before a strong down-move that breaks a swing low (a supply footprint). Price returning to that candle's range is expected to react (bounce/reject) because unfilled institutional orders are assumed to rest there. It is the SMC sibling of a supply/demand *base* ([[strategies/Supply-Demand-Zone-Trading]]) and of the origin candle of a [[concepts/Fair-Value-Gap]].

## How to Use

### Mechanical detection (from the [[sources/LuxAlgo-Smart-Money-Concepts-Pine|LuxAlgo SMC]] reference)
An OB is not drawn freehand — it is *derived from a structure break*:
1. A BOS or CHoCH fires ([[concepts/Market-Structure-CHOCH-BOS]]) — say a bullish break of a swing high.
2. Scan every bar between the broken pivot and the break bar.
3. **Bullish OB** = the bar with the **lowest low** in that window (the deepest pullback candle before the impulse). **Bearish OB** = the bar with the **highest high**. That bar's high–low range becomes the order-block zone.
4. **Volatility parsing** (key refinement): before selecting, each bar's high/low is "parsed" — if a bar's range ≥ 2 × ATR(200) it's flagged high-volatility and its high/low are *swapped* for selection purposes, so a single violent spike bar doesn't get mis-picked as the OB.

### Two tiers, mirroring structure
LuxAlgo derives OBs at both structure tiers: **internal order blocks** (from 5-bar internal structure breaks — minor, more frequent) and **swing order blocks** (from 50-bar swing breaks — major). Only the newest N are kept (default 5 each).

### Mitigation (when an OB is "used up")
- **Bearish OB** is mitigated when price trades/closes back **above** its high; **bullish OB** when price trades/closes back **below** its low.
- The mitigation source is a choice: **Close** (body close through the block — stricter, fewer invalidations) vs **High/Low** (any wick through — looser). Same close-vs-wick design tension as the [[concepts/Fair-Value-Gap]] lifecycle.
- Once mitigated, the block is removed — it has done its job (or failed).

### Trading the zone
An unmitigated OB in the trade direction is a **pullback entry zone**: wait for price to return into the block, look for a rejection/confirmation candle, enter with a stop just beyond the block. Strongest when it aligns with a [[concepts/Premium-Discount-Zones]] read (buy bullish OBs in discount, sell bearish OBs in premium) and the higher-timeframe structure.

## Variants / Parameters
- **Filter method**: ATR(200) (default) vs cumulative-mean-range for the volatility parse. LuxAlgo recommends cumulative-mean-range when little data is available.
- **Mitigation basis**: Close vs High/Low (see above).
- **Count**: how many recent OBs to display (default 5 internal, 5 swing).
- Related unstructured OB definitions in the wild also require an FVG immediately after the OB candle ("OB + imbalance"); the LuxAlgo reference does **not** require an FVG — it takes the extreme candle before the break unconditionally.

## Common Mistakes
- **Drawing OBs without a structure break.** A down candle is only a bullish OB if the move *after* it broke structure. No break → not an OB, just a candle.
- Treating every touch as a bounce — an OB is a *zone of interest*, not a guaranteed reversal; it needs confirmation on return, same warning as CHoCH being a warning not a trigger ([[concepts/Market-Structure-CHOCH-BOS]]).
- Ignoring mitigation — a block price has already closed through is spent; re-using it is trading a level the market already cleared.
- Picking the spike bar as the OB — the volatility-parse step exists precisely to avoid this; a naive min-low/max-high selection will grab violent bars.
- Trading counter-trend OBs against the HTF regime — OB entries are timing tools; direction must already be justified by structure and the weekly tape.

## Related Concepts
- [[concepts/Market-Structure-CHOCH-BOS]] — OBs are *derived from* BOS/CHoCH breaks; no structure event, no order block. The two-tier (internal/swing) split applies identically.
- [[strategies/Supply-Demand-Zone-Trading]] — an order block is essentially the origin/base candle of a supply or demand zone; RBR/DBD zone-strength factors (freshness, exit-move strength, distance) map directly onto OB quality.
- [[concepts/Fair-Value-Gap]] — OBs and FVGs are the two dominant SMC "return-to" zones; the impulse that validates an OB usually leaves an FVG, and "OB + FVG confluence" is a common higher-quality entry filter.
- [[concepts/Premium-Discount-Zones]] — grade an OB by where it sits: a bullish OB in discount is higher-probability than one in premium.
- [[concepts/Support-Resistance]] — an OB is a mechanically-defined zone-not-line; the same zone psychology applies.

## Examples in This Wiki
- **No Python port yet** — as of 2026-07-16 nothing in `tools/` computes order blocks. This is the highest-value port from the LuxAlgo source: the "last opposing candle before an impulse that breaks structure, volatility-parsed" rule would slot into `tools/scanner_templates.py` alongside `detect_bos_choch()` in the Early Reversal / structure layer. Mitigation state and Close-vs-High/Low basis carry over directly.
- No live-ticker example yet — annotate an entity page when an OB rejection fires on a tracked stock.

## Sources
1. [LuxAlgo-Smart-Money-Concepts-Pine](../sources/LuxAlgo-Smart-Money-Concepts-Pine.md) — Pine v5 indicator by [[LuxAlgo]] (CC BY-NC-SA 4.0), ingested 2026-07-16; the derive-from-structure-break selection rule, volatility parsing, two-tier internal/swing split, and Close-vs-High/Low mitigation are all from this script.
