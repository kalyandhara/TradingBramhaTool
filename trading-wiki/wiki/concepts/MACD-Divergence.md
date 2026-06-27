---
title: "MACD Divergence"
category: concept
tags: [MACD, divergence, reversal, momentum, histogram, zero-line]
created: 2026-06-14
updated: 2026-06-22
sources: 2
related: [concepts/RSI.md, concepts/Elliott-Wave.md, concepts/KST.md, sources/SwingEdge-Learn-Indicators-Deep-Dive]
---

# MACD Divergence

## Definition
When price and MACD move in opposite directions — signals weakening momentum and potential reversal. MACD itself = 12 EMA − 26 EMA ("MACD line"), with a 9 EMA of that line as the "signal line," and the histogram = MACD line − signal line.

## Types
**Bullish Divergence:**
- Price forms **lower lows**
- MACD forms **higher lows**
- Meaning: downward momentum weakening → potential upside reversal

**Bearish Divergence:**
- Price forms **higher highs**
- MACD forms **lower highs**
- Meaning: upward momentum weakening → potential downside reversal

Because MACD smooths more than RSI, its divergences are less frequent but typically more reliable — when MACD divergence and price structure agree, signal quality is high (cf. [[concepts/RSI]]'s four divergence variants, including hidden/continuation divergence, which apply analogously to MACD though the reference source below focuses on the classic two).

## The Zero Line — the most useful single signal (2026-06-22 addition)
MACD above zero means the 12 EMA is above the 26 EMA — short-term momentum sits on top of intermediate. Below zero is the reverse. **Long setups have higher follow-through when MACD is positive; short setups when MACD is negative.** Trading a bullish setup with MACD below zero is fighting the indicator's most basic signal.

## Histogram Acceleration/Deceleration — the leading edge (2026-06-22 addition)
- Rising histogram (bars getting taller above zero) = MACD pulling away from signal = momentum accelerating.
- Falling histogram (bars getting shorter) = MACD converging toward signal = momentum decaying, **even if price is still rising**. Histogram deceleration almost always precedes price reversal — histogram peaks before price peaks, histogram troughs before price troughs. Three consecutively shorter bars after a run is a tightening-of-stops cue.
- A color flip (green↔red) is the crossover itself — it only *confirms* what the histogram pattern already showed.
- Histogram is noisy on short timeframes — use primarily on daily/weekly for swing decisions.

## Crossovers — location relative to zero changes the signal completely
| Crossover | Location | Read |
|---|---|---|
| Bullish (MACD crosses above signal) | Above zero | High-quality continuation cue — pair with price structure |
| Bullish | Below zero | Counter-trend bounce — lower win rate, use only with multiple confluence |
| Bearish (MACD crosses below signal) | Above zero | Pullback in an uptrend — often a buying opportunity, not a short |
| Bearish | Below zero | Continuation down — pair with breakdown of structural support |

## Multi-Timeframe MACD Template
Weekly MACD sets the regime (above/below zero → long vs. short bias) → Daily MACD sets the setup (histogram behavior, divergence) → Intraday MACD sets the trigger (crossover/histogram flip on entry timeframe). When all three align, confidence is high; when weekly and daily disagree, sit out. Mirrors the same top-down logic as [[concepts/Multi-Timeframe-Analysis]].

## Trading Use
- Most reliable on daily and weekly timeframes
- Especially powerful at Elliott Wave 5 tops (price makes new high, MACD doesn't)
- Combine with RSI divergence for higher confidence
- MACD is lagging by construction (averages of averages) — treat as confirmation, never a leading signal
- Meaningless in low-volume, range-bound stocks (math assumes trend; without trend you get whipsaw)
- Default 12/26/9 settings are fine for most stocks — don't curve-fit by tuning parameters to history

## Related
- [[concepts/RSI]] — RSI divergence works the same way, often at same turning points; RSI also documents hidden/continuation divergence and swing-failure patterns that apply analogously here
- [[concepts/Elliott-Wave]] — Wave 5 top often shows MACD bearish divergence
- [[concepts/KST]] — KST divergence works similarly
- [[concepts/Multi-Timeframe-Analysis]] — the weekly/daily/intraday MACD template is a specific application of this general framework

## Sources
- [[sources/SwingEdge-Learn-Indicators-Deep-Dive]] (2026-06-22) — zero-line filter, histogram acceleration/deceleration, crossover-location table, MTF template
