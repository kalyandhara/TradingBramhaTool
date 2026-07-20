---
title: "Stochastic Oscillator"
category: concept
tags: [oscillator, momentum, stochastic, lane]
created: 2026-07-14
updated: 2026-07-14
sources: 1
related:
  - sources/Investopedia-Stochastic-Oscillator.md
  - concepts/RSI.md
  - concepts/True-Strength-Index-TSI.md
  - concepts/Percent-R-Trend-Exhaustion.md
  - concepts/PMax.md
---

# Stochastic Oscillator

## Definition
Momentum oscillator (George C. Lane, late 1950s) that expresses the close as a percentage of the high-low range over the last `n` bars. Bounded 0-100.

Reads high (>80) when closes cluster near recent highs (up-move exhaustion risk); reads low (<20) when closes cluster near recent lows (down-move exhaustion risk).

## Formulas
- **raw %K** = `100 × (Close − LowestLow(n)) / (HighestHigh(n) − LowestLow(n))`
- **%K**      = `SMA(raw %K, kSmooth)`
- **%D**      = `SMA(%K, dSmooth)` — signal line

## Variants / Parameters
| Variant | Spec | Note |
|---------|------|------|
| Fast Stochastic | (14, 1, 3) | Raw %K, no smoothing → whippy |
| Slow Stochastic | (14, 3, 3) | The default; smoothing damps noise |
| Full Stochastic | (n, k, d) | Both smoothing params user-tunable |

Trading Bramha ships **(14, 3, 3)** in the chart tool. Change constants in `stochSeries()` (`tools/chart_dashboard.html`) to expose other presets.

## How to Use
1. **Crossover in extreme zone**: %K crossing %D upward while both are <20 → buy prep; downward while both >80 → sell prep.
2. **Exit-from-extreme**: safer variant — wait for %K to cross back below 80 (sell) or above 20 (buy).
3. **Divergence**: price higher high + stochastic lower high → bearish (and vice versa).
4. **Lane's bull/bear setup**: divergence + failed retest of the extreme = highest-quality signal.
5. **Trend filter**: pair with [[concepts/PMax]] direction or SMA200 regime. Don't take shorts in a confirmed uptrend just because stochastic is >80.

## Common Mistakes
- **Trading extremes in trends**: Stochastic can pin >80 for weeks in a strong uptrend. Overbought ≠ sell.
- **Every crossover matters**: on (14,3,3), whipsaws are frequent in chop. Filter by higher-TF alignment or trend gate.
- **Reading intra-bar**: value only updates on candle close; a mid-bar cross can reverse before it prints.

## Related Concepts
- [[concepts/RSI]] — same family (0-100 momentum), different formulation (avg gain / avg loss).
- [[concepts/True-Strength-Index-TSI]] — double-smoothed momentum; less prone to sticky extremes.
- [[concepts/Percent-R-Trend-Exhaustion]] — Williams %R is arithmetically equivalent to (100 − stochastic raw %K) but scaled −100 to 0.
- [[concepts/PMax]] — recommended trend gate for filtering stochastic crossovers.

## Examples in This Wiki
- Wired into the chart tool as a sub-pane oscillator (**Oscillators → Stochastic (14,3,3)**). Cyan %K, dashed orange %D, 80/50/20 guide lines.

## Sources
- [[sources/Investopedia-Stochastic-Oscillator]]
