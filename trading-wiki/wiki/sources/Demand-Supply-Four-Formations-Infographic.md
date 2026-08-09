---
title: "Infographic — Demand & Supply, the four base formations (RBR / RBD / DBR / DBD)"
category: source
tags: [infographic, supply-demand, RBR, RBD, DBR, DBD, base, demand-zone, supply-zone, corroboration]
created: 2026-08-09
updated: 2026-08-09
sources: 1
related:
  - strategies/Supply-Demand-Zone-Trading.md
  - concepts/Order-Blocks.md
  - concepts/Support-Resistance.md
  - sources/SR-SMC-Supply-Demand-Dhruv-Emily-2022.md
---

# Infographic — Demand & Supply, the four base formations

## Metadata
- **Author:** unattributed retail educational graphic ("Demand & Supply")
- **Date:** supplied 2026-08-09
- **Format:** single image, 2×2 quadrant — one schematic per formation
- **Ingest trigger:** user supplied it "for demand supply understanding"

## Key Takeaways

1. **All four formations, exactly as this wiki already has them.** Rally-Base-Rally and Drop-Base-Drop draw the zone at the base for **continuation**; Rally-Base-Drop and Drop-Base-Rally draw it for **reversal**. Demand zones under price, supply zones above.
2. **The zone is the base**, drawn as a rectangle across the base candles and extended rightward — the level to trade on retest.
3. **Nothing else.** No zone-strength criteria, no entry trigger, no stop, no target, no timeframe guidance, no invalidation rule.

> [!note] Pure corroboration — this source adds no mechanics the wiki lacked
> [[strategies/Supply-Demand-Zone-Trading]] (ingested 2026-06-18 from a book source) already carries all four formations with the same continuation/reversal split and the same zone-at-the-base construction. It is filed here anyway because independent corroboration of a framework is worth recording — the same reason [[sources/Fingrad-OI-Analysis-Infographic]] was kept when its quadrants matched `nse_oi_momentum.py` exactly.
>
> **Everything our page has that this graphic does not:** the zone-strength ranking (freshness → exit-move speed → time at base → excursion distance), **flip zones**, the HTF-mark → TTF-entry split, entry triggers (pin bar / engulfing / two-bar reversal inside the zone), stop placement with a 1–2 ATR buffer and the never-use-round-numbers rule, partials at 1:1, the Smart-Money accumulation→distribution phase table, and the mapping onto the sweep-reverse scalp as a DBR flip zone.

## Detailed Notes

| Formation | Legs | Zone | Read | Wiki match |
|---|---|---|---|---|
| **RBR** | Rally → Base → Rally | Demand (below) | Trend continuation, long the retest | ✅ identical |
| **DBD** | Drop → Base → Drop | Supply (above) | Trend continuation, short the retest | ✅ identical |
| **RBD** | Rally → Base → Drop | Supply (at the top) | Trend reversal, short the retest | ✅ identical |
| **DBR** | Drop → Base → Rally | Demand (at the bottom) | Trend reversal, long the retest | ✅ identical |

The mnemonic is worth keeping as a mnemonic: **the middle leg names the zone, the two outer legs name the trade.** Same-direction outer legs → continuation; opposite → reversal.

## Actionable Insights

The value of this ingest is not the content — it is that re-reading the four formations against `tools/` exposed a **coverage map nobody had drawn**. See the table now on [[strategies/Supply-Demand-Zone-Trading]]; the short version:

- **Only RBR is detected**, and only in a heavily gated form. `scan_base_formation` requires the full Minervini Stage-2 trend template (price > SMA50 > SMA150 > SMA200, within 25% of the 52-week high, ≥25% above the 52-week low) and reuses `detect_vcp_geometry` for a contracting base. That is a *subtype* of RBR, not RBR.
- **DBD, RBD and DBR are not detected at all.** Two of the four are supply-side/bearish, which is the **fourth instance of the same long-only bias** found this week in candlesticks (no bearish patterns until 2026-08-09), order blocks (`scan_order_block` long-only) and now here.
- **DBR is the notable absence.** The repo has several reversal-from-decline detectors — Early Reversal Detector, Rounding Bottom, Falling Wedge, the Drop-Recovery screen — which are the DBR *shape*, but **none is framed as a base with a tradeable zone**, so none emits the zone the retest is taken against.

## Contradictions with Existing Wiki

> [!contradiction] `scan_base_formation` finds the RBR shape but trades the opposite event
> S&D says the base **is the zone**: you wait for price to leave, come back, and you long the **retest of the base**. `scan_base_formation` is Minervini-framed and buys the **breakout above the pivot** — it explicitly excludes already-broken-out names and treats the base as a launchpad, not a zone to return to.
>
> **Same shape, opposite trade, different bar.** Neither is wrong, but they must not be conflated: a name appearing in Base Formation is *not* an RBR demand-zone setup, and building one on the other's output would buy the wrong event. The distinction is the same class as order-block-vs-wick-zone and the Evening Star's gap — a shape match is not a method match.

- **No conflict on the formations themselves** — the graphic and [[sources/SR-SMC-Supply-Demand-Dhruv-Emily-2022]] agree completely.
- **Consistent with [[concepts/Order-Blocks]]**, which already records that an order block is essentially the origin/base candle of a supply or demand zone, and that RBR/DBD zone-strength factors map onto OB quality.

## Pages Updated
- [[strategies/Supply-Demand-Zone-Trading]] — added the implementation-coverage table, the `scan_base_formation` contradiction, and this source
- `wiki/index.md`, `wiki/log.md`
- **`wiki/overview.md` untouched** — corroboration shifts no thesis.
