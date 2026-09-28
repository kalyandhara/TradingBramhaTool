---
title: "Infographic — SMC Top-Down Analysis"
category: source
tags: [SMC, smart-money, top-down, multi-timeframe, order-block, liquidity, CHoCH]
created: 2026-09-26
updated: 2026-09-26
sources: 0
related:
  - concepts/SMC-Top-Down-Analysis.md
  - concepts/ICT-Methodology.md
---

# Infographic — SMC Top-Down Analysis

## Metadata
- **Type:** Infographic
- **Date ingested:** 2026-09-26
- **Author:** Unknown (social media infographic)
- **File:** `raw/` (image)

## Key Takeaways

1. Three-timeframe funnel: 4H defines bias → 1H locates POI → 5M executes
2. 4H reads market structure (HH/HL = bullish, LH/LL = bearish) — this is
   the only direction you trade
3. 1H identifies order blocks as POI and maps SSL/BSL liquidity pools that
   price has not yet mitigated
4. 5M entry is a 5-step sequence: internal liquidity sweep → CHoCH →
   pullback to new OB/FVG → precision entry → confirmation breakout
5. Stop below the 5M sweep; target the opposing 1H liquidity pool
6. The workflow is a filtering funnel — each TF narrows, none generates
   independent signals

## Detailed Notes

Three-panel layout, one per timeframe:

**Panel 1 — 4H:** Shows a clean uptrend with HH/HL labels, a PDH reference
level, and a 4H valid demand / order block zone. Checklist: strong market
structure, bullish order flow, clean price action.

**Panel 2 — 1H:** Zooms into the trend. Identifies a 1H bullish order block
as the POI. Marks SSL pools that price did not mitigate (still magnetic).
Notes the full range from POI to liquidity.

**Panel 3 — 5M:** The execution chart. Five numbered steps:
1. Internal liquidity sweep at the POI zone
2. CHoCH — first counter-trend structure break
3. Pullback to the new 5M OB / FVG created by the CHoCH move
4. Precision entry at the OB/FVG
5. Confirmation via CHoCH + OB + breakout alignment

Stop loss below the sweep low; take profit at the 1H liquidity target.

## Actionable Insights

- Three of five chart components already ship (structure breaks, order
  blocks, FVGs). The workflow is usable today with manual multi-TF
  navigation.
- BSL/SSL pool detection and the OTE Fibonacci zone are the two gaps —
  both logged as pending in [[concepts/ICT-Methodology]].
- The displacement gate on CHoCH is the highest-value small build: it
  filters noise from the existing `detect_bos_choch` and is called out as
  low effort in the ICT page.

## Contradictions with Existing Wiki

- None. This is a workflow instantiation of ICT methodology, which is
  already documented. The infographic adds the explicit 4H→1H→5M
  timeframe hierarchy and the 5-step LTF execution sequence, neither of
  which were spelled out on the ICT page.

## Pages Updated

- Created [SMC-Top-Down-Analysis](../concepts/SMC-Top-Down-Analysis.md)
  concept page
- Cross-linked to existing [[concepts/ICT-Methodology]]
