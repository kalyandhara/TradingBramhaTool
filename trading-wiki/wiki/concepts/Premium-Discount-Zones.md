---
title: "Premium / Discount Zones"
category: concept
tags: [premium, discount, equilibrium, fibonacci, smc, smart-money, ict, mean-reversion, luxalgo, regime-filter]
created: 2026-07-16
updated: 2026-08-29
sources: 2
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

## Variants / Parameters — the deep-fib + value-area agreement rule (Kmer, 2026-08-29)

A stricter construction from [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]], notable
because it requires **two independent definitions of "discount" to agree** before the
location counts:

1. **Fibonacci band** drawn swing-low → swing-high at **0.705 / 0.786 / 0.886** — deeper
   than the ICT OTE zone (61.8–79%) documented in [[concepts/ICT-Methodology]], and
   deeper than the LuxAlgo 5% extreme bands above.
2. **Value area** ([[concepts/Volume-Profile]]) — the band must sit **below the value
   area low**. If the fib zone lands *inside* value area, the setup is discarded outright.

The second condition is the load-bearing one and the reason this variant is worth
recording: a Fibonacci level is a drawing, while value area is where business was
actually transacted. Requiring both removes the failure mode where a retracement level
happens to fall in the middle of accepted value and therefore marks nothing.

**The 0.886 as a hard invalidation.** Not a target zone but a line: if price closes beyond
the 0.886 without the dominance shift appearing, the trade is not taken. The reasoning is
structural — a pullback that was going to hold should have held before the range is nearly
fully retraced.

Also required: some **internal structure** (a swing point, ideally a sweep) before price
enters the zone, and a preference for the pullback to be into an **inefficient /
low-volume node** — an area price crossed quickly, where little was transacted.

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
2. [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]] — the 0.705/0.786/0.886 band, the must-be-outside-value-area agreement rule, and the 0.886 hard invalidation.

1. [LuxAlgo-Smart-Money-Concepts-Pine](../sources/LuxAlgo-Smart-Money-Concepts-Pine.md) — Pine v5 indicator by [[entities/LuxAlgo]] (CC BY-NC-SA 4.0), ingested 2026-07-16; the 5%-band premium/equilibrium/discount construction on trailing swing extremes is from this script.
