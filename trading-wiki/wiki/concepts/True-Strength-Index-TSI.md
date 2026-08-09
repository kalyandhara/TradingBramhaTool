---
title: "True Strength Index (TSI)"
type: concept
category: indicator
family: momentum-oscillator
created: 2026-07-12
tags: [momentum, oscillator, double-smoothed, tsi]
---

# True Strength Index (TSI)

Double-smoothed momentum oscillator (William Blau, 1991). Ratio of double-smoothed *signed* price change to double-smoothed *absolute* price change, scaled ×100. Range −100 … +100.

## Formula

Let `Δ = Close − Close[1]`.

```
PCS   = EMA(EMA(Δ, 25), 13)          # double-smoothed signed change
APCS  = EMA(EMA(|Δ|, 25), 13)        # double-smoothed absolute change
TSI   = 100 × PCS / APCS
Signal = EMA(TSI, 13)                 # or 7 for faster signals
```

Standard parameters: **(r=25, s=13, signal=13)**. Author uses these; also cites `(7)` for a faster signal line.

Why ×100: `APCS ≥ |PCS|` always (positive/negative in numerator partially cancel; denominator sums magnitudes), so the raw ratio is small. Scaling normalizes to −100…+100 for readability.

## vs RSI

| | RSI | TSI |
|---|---|---|
| Numerator | Avg gains | Signed price change (double-smoothed) |
| Denominator | Avg losses | Absolute price change (double-smoothed) |
| Range | 0–100 | −100 to +100 |
| Smoothing | Single (Wilder) | Double (25 then 13) |
| Strength | Overbought/oversold | Trend inflection, divergence |
| Weakness | Whipsaw in trends | Slower entry in choppy markets |

Both are momentum tools. TSI is quieter and better at *when* momentum flips; RSI is louder on *how stretched* the move is.

## Signals

- **Signal-line crossover** — TSI crosses above/below its 13-EMA signal line → primary entry/exit trigger.
- **Zero-line crossover** — TSI > 0 = net bullish momentum bias; TSI < 0 = net bearish. Confirmation only.
- **Divergence** — Price higher-high but TSI lower-high → bearish divergence (classic momentum-exhaustion tell). Reverse for bullish.
- **Overbought / oversold** — Loose bands at ±25 to ±30. Not a fade signal on its own.

## The Trend × TSI Matrix

TSI in isolation whips. Read it *conditional on trend* (from [[concepts/SuperTrend]], [[concepts/EMA]] slope, or price-vs-SuperTrend):

| Trend | TSI crossover | Read | Action |
|---|---|---|---|
| Up | Positive (TSI > signal) | Confirmed up-momentum | Enter long |
| Up | Negative (TSI < signal) | Momentum fading, likely pause | Book partial / trail stop |
| Down | Negative | Confirmed down-momentum | Enter short |
| Down | Positive | Down-momentum weakening | Watch for reversal / range |

Key nuance: **a negative TSI crossover in an uptrend is not a reversal signal** — it's a pause. Reversal requires the trend filter itself to flip.

## Best Pairings

- **Trend filter**: [[concepts/SuperTrend]] or MAST (MA + SuperTrend).
- **Chart type**: [[concepts/Point-and-Figure-Charts]] — removes time noise; TSI crossovers on P&F filter more decisively than on time-based bars.
- **Divergence context**: pair with [[concepts/MACD-Divergence]] for confirmation.

## Common Mistakes

- Trading TSI crossovers with no trend filter → whipsaw graveyard.
- Reading a negative crossover in an uptrend as "sell" instead of "pause."
- Ignoring the zero line — a crossover with TSI still deep negative is much weaker than one near/above zero.

## Sources

- [[sources/YT-Kaushik-Akkiwakar-TSI-Momentum]] — primary source; 4-quadrant matrix, 6 examples, real-time deployment recipe.

## Related

- [[concepts/RSI]] · [[concepts/KST]] · [[concepts/MACD-Divergence]] · [[concepts/Percent-R-Trend-Exhaustion]] · [[concepts/ConnorsRSI]]
- Trend filters: [[concepts/SuperTrend]] · [[concepts/EMA]] · [[concepts/PMax]]
- Chart type: [[concepts/Point-and-Figure-Charts]]
