---
title: "Infographic — Supertrend & EMA Crossover"
category: source
tags: [supertrend, ema, crossover, infographic, trend-following]
created: 2026-09-26
updated: 2026-09-26
sources: 0
related:
  - concepts/Supertrend-EMA-Crossover.md
---

# Infographic — Supertrend & EMA Crossover

## Metadata
- **Type:** Infographic
- **Date ingested:** 2026-09-26
- **Author:** Unknown (social media infographic)
- **File:** `raw/` (image)

## Key Takeaways

1. Supertrend (10, 3) provides trend direction; EMA 20/50 crossover provides
   entry timing — dual confirmation reduces false signals
2. Buy when Supertrend is green AND EMA 20 > EMA 50 AND price above both;
   sell the mirror
3. Wait for pullback to EMA or consolidation breakout — do not chase
4. Stop loss below Supertrend line (buy) or above it (sell); target R:R 1:2
   or 1:3
5. Best in trending markets (15m–4H); avoid sideways / low-vol / news chop
6. Risk management: 1–2% per trade, let winners run

## Detailed Notes

The infographic presents an 8-section layout:

1. **What is it** — Supertrend confirms trend strength; EMA crossover
   filters false signals and improves entry accuracy
2. **Indicators** — Supertrend (10, 3): green = up, red = down. EMA: fast
   20, slow 50
3. **Buy setup** — 7-step: ST green, EMA cross up, price above both, wait
   for pullback, enter, stop below ST, target next resistance
4. **Sell setup** — mirror of buy
5. **Example setups** — visual buy/sell chart examples
6. **Best timeframes** — 15m, 30m, 1H, 4H; higher TF = stronger signal
7. **Market conditions** — trending/breakouts good; sideways/low-vol/news
   bad
8. **Key rules** — follow trend, never fight ST, use stops, 1–2% risk, let
   winners run

**Pro tip:** Supertrend for direction, EMA crossover for timing.

## Actionable Insights

- Both indicators already ship on the desk chart (`supertrend_ai.js`, EMA
  overlays). No build needed.
- SuperTrend AI flip was measured negative (B-44: -1.00% @20d). Adding EMA
  crossover as a gate is unlikely to flip the edge.
- The pullback-entry discipline (step 4) is the valuable part — it applies
  to any trend-following system, not just this pair.

## Contradictions with Existing Wiki

- None. The infographic describes a standard trend-following combination.
  Our desk has the more sophisticated adaptive SuperTrend variant and has
  already measured it.

## Pages Updated

- Created [Supertrend-EMA-Crossover](../concepts/Supertrend-EMA-Crossover.md)
  concept page
