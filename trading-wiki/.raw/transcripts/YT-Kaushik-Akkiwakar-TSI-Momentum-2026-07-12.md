---
source_type: youtube-transcript
author: Kaushik Akkiwakar
fetched: 2026-07-12
---

# Transcript: True Strength Index (TSI) — Kaushik Akkiwakar

In trading, the most popular trading style is momentum trading — yet 95% of traders haven't even heard the name of this powerful indicator: the **True Strength Index (TSI)**.

Kaushik Akkiwakar, SEBI-registered research analyst, walks through TSI from first principles.

## What is TSI?

The True Strength Index is a momentum indicator — "the average of moving averages," double-smoothed. Underused because the formula looks intimidating; the logic is simple.

## Calculation

1. **Price Change** = Current Close − Previous Close (can be +/−).
2. **Absolute Price Change** = |Current Close − Previous Close|.
3. **First smoothing**: 25-period average of both raw and absolute price change.
4. **Second smoothing**: 13-period average of the smoothed series.
5. **TSI = 100 × (Double-smoothed price change) / (Double-smoothed absolute price change)**.

×100 because denominator (all positives) is always ≥ numerator (signed), so raw ratio is small.

Contrast RSI: RS = avg gains / avg losses, RSI = 100 − 100/(1+RS). TSI uses raw signed changes with double smoothing — less noisy, better at trend transitions.

## Signal Line

Add a 13- or 7-period EMA of TSI itself.
- Bullish signal: TSI crosses above signal line.
- Bearish signal: TSI crosses below signal line.

Momentum alone is insufficient — combine with trend.

## 4-Quadrant Trend + Momentum Matrix

| Trend | TSI signal | Interpretation | Action |
|---|---|---|---|
| Bullish (Price > SuperTrend) | Positive crossover | Strong upward momentum | Ideal entry |
| Bullish | Negative crossover | Momentum fading, consolidation likely | Partial exit / wait |
| Bearish | Negative crossover | Strong downward momentum | Ideal short entry |
| Bearish | Positive crossover | Downtrend weakening, possible reversal | Consolidation ahead |

Key: a bullish trend + negative TSI crossover doesn't mean reversal — it signals pause, range, or profit booking.

## Why TSI Works

- Double smoothing reduces false signals while retaining sensitivity.
- Uses raw price movement (not gains vs losses like RSI).
- Excellent with point-and-figure charts (time-noise removed).
- Distinguishes trend continuation from momentum exhaustion.

## Practical Examples

Uses SuperTrend (or MAST: Moving Average + SuperTrend) for trend direction.

1. **Bullish breakout**: Price > SuperTrend, TSI crosses above signal, P&F shows Turtle Pattern → high-probability long.
2. **Profit booking**: Bullish trend + TSI negative crossover → book partial, tighten stops.
3. **Reversal warning**: Bearish trend, long consolidation, TSI positive crossover appears before SuperTrend flips → early re-entry.
4. **Strong uptrend + momentum fade**: Price ₹500→₹1200, TSI negative crossover at top → momentum exhaustion; later bear trap + double-bottom sell → reversal.
5. **Consolidation breakout**: ₹94–₹110 consolidation, TSI bullish crossover, breakout above ₹110 → ₹212 (+126%).
6. **Broadening top with TSI confirmation**: Broadening pattern (churning), TSI positive crossover in bullish trend → successful breakout.

## Takeaways

- TSI is a trend-momentum confluence tool, not a pure oscillator.
- Use with a trend filter (SuperTrend, MA crossover).
- Positive crossover in uptrend = entry; negative crossover = warning.
- Zero-line crossovers also matter: TSI > 0 = net bullish momentum; TSI < 0 = net bearish.

## Author's Real-Time Use

- Scans daily and 5m timeframes continuously.
- Alerts on negative TSI crossovers as leading exit signals.
- Combined with 4-step stock selection (market cap, volume, volatility, trend alignment).
- Deployed at the MarkUp platform for live client alerts.
