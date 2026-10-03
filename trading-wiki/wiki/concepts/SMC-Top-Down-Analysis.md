---
title: "SMC Top-Down Analysis"
category: concept
tags: [SMC, smart-money, top-down, multi-timeframe, order-block, liquidity, CHoCH, FVG]
created: 2026-09-26
updated: 2026-09-26
sources: 1
related:
  - concepts/ICT-Methodology.md
  - concepts/Market-Structure-CHOCH-BOS.md
  - concepts/Fair-Value-Gap.md
  - concepts/Fair-Value-Breaker-FBG.md
---

# SMC Top-Down Analysis

## Definition

A **three-timeframe execution workflow** from the Smart Money Concepts (SMC)
framework. Each timeframe has one job:

| Step | Timeframe | Job | Output |
|------|-----------|-----|--------|
| 1 | **4H** (HTF) | Define trend direction via market structure | Bullish or bearish bias |
| 2 | **1H** (ITF) | Locate liquidity pools and the Point of Interest (POI) | Order block / demand-supply zone to watch |
| 3 | **5M** (LTF) | Execute with precision confirmation | Entry, stop, target |

The framework is a **filtering funnel**: each lower timeframe narrows the
decision space rather than generating independent signals. A 5M entry is
only valid if the 4H bias and 1H POI agree.

## How to Use

### Step 1 — 4H: Define HTF Direction

Read market structure on the 4H chart:

- **Bullish:** higher highs (HH) + higher lows (HL), order flow bullish,
  clean price action
- **Bearish:** lower highs (LH) + lower lows (LL)

Identify:
- PDH / PDL (Previous Day's High / Low) as reference levels
- Valid demand / supply zones (4H order blocks)
- The current trend direction — this is the **only direction** you trade

### Step 2 — 1H: Locate Liquidity & POI

On the 1H chart within the 4H trend:

- Identify **Sell-Side Liquidity (SSL)** pools below swing lows and
  **Buy-Side Liquidity (BSL)** pools above swing highs
- Locate the **1H Order Block** that is the Point of Interest (POI) —
  the zone where price is likely to react
- Watch for SSL/BSL sweeps or mitigation of the POI
- Note the **full range** — the distance from the POI to the liquidity pool
  defines the trade's potential

### Step 3 — 5M: Execute with Precision

Five-step confirmation sequence on the 5M chart:

1. **Internal liquidity sweep** — price takes out a minor swing low/high
   within the POI zone
2. **CHoCH (Change of Character)** — first counter-trend break confirming
   reversal at the POI
3. **Pullback to new 5M Order Block / FVG** — price returns to the origin
   of the CHoCH move
4. **Precision entry** — enter at the 5M OB/FVG with stop below/above the
   sweep low/high
5. **Confirmation & breakout** — CHoCH + OB + breakout alignment confirms
   the trade

### Trade Management

- **Stop loss:** below the internal liquidity sweep (buy) or above it (sell)
- **Take profit:** the opposing liquidity pool identified on 1H
- **R:R:** typically 1:3 or better due to the tight 5M stop vs 1H target

## Variants / Parameters

| Variant | HTF | ITF | LTF | Use case |
|---------|-----|-----|-----|----------|
| Standard (this infographic) | 4H | 1H | 5M | Intraday / short swing |
| Swing | Daily | 4H | 1H | Multi-day holds |
| Scalp | 1H | 15M | 1M | Ultra-short intraday |

The timeframe trio scales but the **ratio** (~4:1 between tiers) stays
roughly constant.

## Desk Coverage

| Component | Status | Where |
|-----------|--------|-------|
| BOS / CHoCH detection | Shipped | `structure_chain` overlay on chart |
| Order Blocks (demand/supply) | Shipped | `orderblock` overlay on chart |
| Fair Value Gaps | Shipped | `fvg.js` + signal panel on chart |
| Market structure (HH/HL/LH/LL) | Shipped | Part of Structure Break Chain |
| BSL / SSL liquidity pools | **Not built** | Flagged in [[concepts/ICT-Methodology]] |
| OTE zone (61.8–79% Fib) | **Not built** | Flagged in [[concepts/ICT-Methodology]] |
| Displacement gate on CHoCH | **Not built** | `detect_bos_choch` lacks displacement filter |
| Multi-TF linked drill-down | **Not built** | Conceptually documented, not automated |

Three of five key components ship. The two missing primitives (liquidity
pools, OTE zone) are logged as pending builds in the ICT concept page.

## Common Mistakes

- Trading the 5M setup **against** the 4H bias — the HTF filter is not
  optional
- Entering at the POI without waiting for 5M CHoCH confirmation — the POI
  is a zone to **watch**, not an automatic entry
- Confusing BOS (trend continuation) with CHoCH (trend reversal) — the
  infographic's 5M entry requires a CHoCH specifically
- Ignoring unmitigated SSL/BSL pools — they remain magnets until swept
- Using this in **sideways / choppy** 4H structure where HH/HL or LH/LL
  is ambiguous

## Relationship to ICT Methodology

This is a **workflow instantiation** of [[concepts/ICT-Methodology]]. ICT
defines the primitives (liquidity pools, MSS, FVG, OTE); SMC Top-Down
Analysis arranges them into a timeframe hierarchy with an execution
sequence. The infographic's 5-step LTF entry maps directly to ICT's
MSS → FVG → OTE sequence.

## Sources

- SMC Top-Down Analysis infographic (2026-09-26) — see
  [source page](../sources/Infographic-SMC-Top-Down-Analysis.md)
