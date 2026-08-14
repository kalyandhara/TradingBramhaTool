---
title: "Premium / Discount Zones"
category: concept
tags: [premium, discount, equilibrium, fibonacci, smc, smart-money, ict, mean-reversion, luxalgo, regime-filter]
created: 2026-07-16
updated: 2026-07-16
sources: 1
related: [concepts/Market-Structure-CHOCH-BOS, concepts/Order-Blocks, concepts/Fair-Value-Gap, strategies/Supply-Demand-Zone-Trading, concepts/Support-Resistance]
---

# Premium / Discount Zones

## Definition
A Fibonacci-based partition of the **current swing range** (last swing high → last swing low) into three regions relative to the 50% midpoint (the **equilibrium**):
- **Premium** = upper portion of the range — price is "expensive." Favor **selling** / avoid chasing longs.
- **Discount** = lower portion — price is "cheap." Favor **buying** / accumulation.
- **Equilibrium** = the ~50% zone — fair value; no directional edge from price *location* alone.

The idea (from ICT/SMC): institutions accumulate in discount and distribute in premium, so entries are higher-probability when taken from the "right" side of equilibrium in the direction of structure. It is a **location filter**, not a signal — it tells you *where* an entry is favorable, not *when*.

## How to Use

### Mechanical construction (from the [[sources/LuxAlgo-Smart-Money-Concepts-Pine|LuxAlgo SMC]] reference)
Built on the trailing swing extremes (`trailing.top`, `trailing.bottom`):
- **Premium zone** = top 5% band of the range: from `top` down to `0.95·top + 0.05·bottom`.
- **Equilibrium zone** = middle ~5% around the midpoint: `0.525·top + 0.475·bottom` down to `0.525·bottom + 0.475·top`.
- **Discount zone** = bottom 5% band: from `0.95·bottom + 0.05·top` down to `bottom`.

(LuxAlgo draws only these three thin bands, not the whole upper/lower halves — the bands mark the *extremes* of premium/discount where the edge is strongest. Many traders instead shade the entire above-50% region premium and below-50% discount; both readings share the same equilibrium anchor.)

### Combining with other tools
Premium/discount is a **grader**, most useful stacked on a concrete signal:
- Take a **bullish [[concepts/Order-Blocks|order block]]** only when it sits in **discount**; a bearish OB only in **premium**. A demand zone in premium is fighting the location.
- A **[[concepts/Fair-Value-Gap|FVG]]** rejection in discount (bull) or premium (bear) is higher-conviction than one at equilibrium.
- As a **regime tag** for the dashboard: "price in premium → don't chase longs / trail tighter"; "price in discount → pullback entries favored." Cheap to compute once trailing swing extremes exist.

## Variants / Parameters
- **Range anchor**: LuxAlgo uses the current *trailing swing* high/low. Others anchor to a specific dealing range (last major impulse leg) or an HTF swing — the zone moves with whatever range you choose, so state the anchor.
- **Band width**: LuxAlgo's 5% extreme bands vs the simpler full-half shading. Narrow bands = fewer but stronger location calls.
- Equilibrium = strict 50%; some frameworks add the 0.618/0.705 "OTE" (optimal trade entry) sub-zone inside discount/premium for tighter entries.

## Common Mistakes
- **Using location as a signal.** "Price is in discount" is not a buy — it's permission to look for a buy *setup*. Without structure/OB/FVG confirmation it's just a Fibonacci level.
- Anchoring to the wrong range — a premium/discount read is only as good as the swing high/low it's measured between; a stale or mis-picked range gives a meaningless zone. Re-anchor when structure shifts ([[concepts/Market-Structure-CHOCH-BOS]]).
- Fighting the trend from the "cheap" side — buying discount in a confirmed downtrend is catching a falling knife; location favors entries *in the direction of structure*, not against it.
- Treating equilibrium as tradeable — the midpoint offers no location edge; it's the neutral zone.

## Related Concepts
- [[concepts/Market-Structure-CHOCH-BOS]] — the swing high/low that defines the range comes from the same trailing-extremes / swing-structure engine; re-anchor premium/discount when a CHoCH/BOS redraws structure.
- [[concepts/Order-Blocks]] — the primary use: grade OBs by zone (bullish OB in discount = A-setup).
- [[concepts/Fair-Value-Gap]] — same grading logic for FVG rejections.
- [[strategies/Supply-Demand-Zone-Trading]] — premium/discount is the multi-timeframe "where in the range" overlay on top of supply/demand zones; a fresh demand zone in discount is the confluence sweet spot.
- [[concepts/Support-Resistance]] — equilibrium/premium/discount are mechanically-derived levels rather than drawn S/R, but function as the same reference geometry.

## Examples in This Wiki
- **No Python port yet** — trivial to add once trailing swing extremes exist (the same engine a `detect_bos_choch()` swing tier would produce). A "premium / equilibrium / discount" regime tag is a cheap, high-readability addition to the dashboard and to entry-validation gating.
- No live-ticker example yet.

## Sources
1. [LuxAlgo-Smart-Money-Concepts-Pine](../sources/LuxAlgo-Smart-Money-Concepts-Pine.md) — Pine v5 indicator by [[entities/LuxAlgo]] (CC BY-NC-SA 4.0), ingested 2026-07-16; the 5%-band premium/equilibrium/discount construction on trailing swing extremes is from this script.
