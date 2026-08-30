---
title: "SuperTrend"
category: concept
family: trend-following
tags: [trend, atr, trailing-stop, supertrend, indicator]
created: 2026-07-12
updated: 2026-08-29
sources: 3
related: [concepts/True-Strength-Index-TSI, concepts/ADX, concepts/EMA, concepts/PMax, concepts/Point-and-Figure-Charts, concepts/Renko-Charts, entities/Kaushik-Akkiwakar, sources/YT-Kaushik-Akkiwakar-TSI-Momentum]
---

# SuperTrend

Trend-following indicator plotted as a trailing line above or below price. Based on HL2 (median price) offset by a multiple of ATR. Flips side when price closes through the band.

## Formula

```
HL2       = (High + Low) / 2
UpperBand = HL2 + Factor × ATR(period)
LowerBand = HL2 − Factor × ATR(period)

if Close > previous UpperBand: SuperTrend = LowerBand (green, uptrend)
if Close < previous LowerBand: SuperTrend = UpperBand (red, downtrend)
otherwise: carry previous value, tightening only in trend direction
```

Standard parameters: `(Factor=3, ATR period=10)`. Common variants: `(2, 10)` faster, `(3, 14)` slower.

## Signals

- **Trend direction**: Price above SuperTrend line = uptrend; below = downtrend.
- **Flip**: line crosses to the other side of price → trend change signal.
- **Trailing stop**: SuperTrend value acts as a dynamic stop for the current position.

## Use With TSI

Price-vs-SuperTrend gives the trend context for reading [[concepts/True-Strength-Index-TSI]] crossovers per the 4-quadrant matrix. See [[sources/YT-Kaushik-Akkiwakar-TSI-Momentum]].

## MAST (MA + SuperTrend)

Author's variant: overlay a moving average with SuperTrend; require both to agree on trend direction before taking a TSI signal. Reduces false trend classifications during transitions.

## Confluence Setups (2026-07-19)

Two popular multi-indicator entries that use SuperTrend as the trend gate:

- **SuperTrend + 5/20 EMA crossover** ("winning combination"): go **long** when 5 EMA crosses *above* 20 EMA **and** SuperTrend turns green; go **short** when 5 EMA crosses *below* 20 EMA **and** SuperTrend turns red. The EMA cross times the entry; SuperTrend confirms the regime and doubles as the trailing stop. Same MAST logic (MA agreement + SuperTrend) at a fast dual-EMA setting. See [[concepts/EMA]].
- **SuperTrend + RSI + ADX**: **enter long** when SuperTrend turns green, [[concepts/RSI]] is below ~30 (oversold) and turning up, **and** [[concepts/ADX]] crosses above 25 (trend strong enough to act on). **Exit** when SuperTrend turns red, RSI is above ~70 and rolling down, and ADX falls back below 25. ADX is the "is there a trend at all" filter that keeps the SuperTrend flip from firing in chop.

## Sources

- [[sources/YT-Kaushik-Akkiwakar-TSI-Momentum]] — SuperTrend / MAST as trend filter for TSI.
- [[sources/CPR-GuruprasadMeduri-Pine]] — Supertrend(3,10) in Pine v4.
- [[sources/Fingrad-Trading-Infographics-Collection]] (2026-07-19) — SuperTrend+5/20-EMA and SuperTrend+RSI+ADX confluence setups.

## Related

- [[concepts/True-Strength-Index-TSI]] · [[concepts/PMax]] · [[concepts/EMA]] · [[concepts/ADX]]
