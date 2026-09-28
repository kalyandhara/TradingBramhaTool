---
title: "Supertrend & EMA Crossover"
category: concept
tags: [supertrend, ema, crossover, trend-following, momentum]
created: 2026-09-26
updated: 2026-09-26
sources: 1
related:
  - concepts/Indicator-Selection-By-Regime.md
  - concepts/VWAP.md
  - analyses/Indicator-Coverage-Gap.md
---

# Supertrend & EMA Crossover

## Definition

A **dual-confirmation trend-following strategy** that combines:

1. **Supertrend (10, 3)** — an ATR-based trailing stop that flips between
   green (uptrend: price above the line) and red (downtrend: price below).
   Formula: `median price +/- multiplier * ATR(period)`.
2. **EMA Crossover (20/50)** — a momentum filter where the fast EMA (20)
   crossing above/below the slow EMA (50) signals trend acceleration.

The idea is that Supertrend provides **trend direction** while the EMA
crossover provides **entry timing**, filtering out false signals from either
indicator alone.

## How to Use

### Buy Setup
1. Supertrend is green (price above Supertrend line)
2. EMA 20 crosses above EMA 50
3. Price is above both EMAs
4. Wait for pullback to EMA or breakout of consolidation
5. Stop loss: below Supertrend line or recent swing low
6. Target: next resistance or R:R of 1:2 / 1:3

### Sell Setup
1. Supertrend is red (price below Supertrend line)
2. EMA 20 crosses below EMA 50
3. Price is below both EMAs
4. Wait for pullback to EMA or breakdown of consolidation
5. Stop loss: above Supertrend line or recent swing high
6. Target: next support or R:R of 1:2 / 1:3

### Entry Refinement
- Buy above the high of the confirmation candle
- Sell below the low of the confirmation candle

## Variants / Parameters

| Parameter | Standard | Notes |
|-----------|----------|-------|
| Supertrend period | 10 | ATR lookback |
| Supertrend multiplier | 3 | Band width |
| Fast EMA | 20 | Momentum |
| Slow EMA | 50 | Trend |

**Adaptive variant (our desk):** `supertrend_ai.js` uses K-means clustering
to adapt the ATR multiplier dynamically rather than fixing it at 3. This is
the LuxAlgo "SuperTrend AI (Clustering)" technique. See
[[analyses/Open-Backlog#B-44]] for the measurement.

## Best / Worst Market Conditions

**Best:** trending markets, strong directional moves, breakouts.

**Worst:** sideways/choppy markets, low volatility, news-driven noise.

**Timeframes:** works on all; 15m/30m/1H/4H cited as best. Higher TFs give
stronger, more reliable signals.

## Desk Coverage & Measurement

| Component | Status | Where |
|-----------|--------|-------|
| Supertrend overlay | Shipped | `supertrend_ai.js` (adaptive) on chart |
| EMA 20/50 overlays | Shipped | `chart_dashboard.html` indicator menu |
| EMA crossover scanner | Shipped | `scanner_templates.py`, `row_metrics.py` |
| SuperTrend AI flip signal | **Measured negative** | B-44: -1.00% @20d, p=0.150, n=1,909 |
| Combined ST + EMA as fused scanner | Not built | Flip alone is negative; adding EMA gate unlikely to flip edge positive |

The SuperTrend AI flip was measured as a clean negative in the B-44 backtest.
The two indicators are available as separate chart overlays for visual
confirmation but are **not fused into a single automated signal**, and the
measurement suggests they should not be.

## Common Mistakes

- Trading against the Supertrend direction
- Entering without waiting for pullback (chasing)
- Using in sideways markets where both indicators whipsaw
- Treating overlapping lookback windows as independent confirmations

## Key Rules (from the infographic)

1. Always follow the trend
2. Never trade against Supertrend
3. Use proper stop loss
4. Manage risk: 1-2% per trade
5. Let your winners run

## Related Concepts

- [[concepts/Indicator-Selection-By-Regime]] — when to use trend-following vs mean-reversion
- [[concepts/VWAP]] — complementary intraday anchor
- [[analyses/Indicator-Coverage-Gap]] — desk indicator audit

## Sources

- Supertrend & EMA Crossover infographic (2026-09-26) — see
  [source page](../sources/Infographic-Supertrend-EMA-Crossover.md)
