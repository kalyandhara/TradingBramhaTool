---
title: "YT — Kaushik Akkiwakar: True Strength Index (TSI) for Momentum"
category: source
type: source
source_type: youtube-transcript
author: "[[entities/Kaushik-Akkiwakar]]"
fetched: 2026-07-12
created: 2026-07-12
raw: .raw/transcripts/YT-Kaushik-Akkiwakar-TSI-Momentum-2026-07-12.md
tags: [momentum, indicator, tsi, supertrend, point-and-figure]
---

# YT — Kaushik Akkiwakar: True Strength Index (TSI) for Momentum

SEBI-registered research analyst [[entities/Kaushik-Akkiwakar]] argues TSI is the most underused momentum indicator (~95% of retail traders haven't heard of it) despite double-smoothed responsiveness that beats RSI on trend transitions. Video walks TSI from formula → 4-quadrant trend+momentum matrix → six point-and-figure worked examples, all combined with SuperTrend / MAST for trend context.

> [!key-insight]
> TSI in isolation is noise. Its edge is as a **trend-momentum confluence tool** — TSI crossovers are read *conditional on trend direction* (given by SuperTrend or a moving average). A bullish trend + negative TSI crossover is a *pause / profit-book* signal, not a reversal.

## Core Claims

- **Formula** — double-smoothed price change: first a 25-period smoothing of both raw ΔClose and |ΔClose|, then a 13-period smoothing of both series; TSI = 100 × (double-smoothed ΔClose) / (double-smoothed |ΔClose|). See [[concepts/True-Strength-Index-TSI]] for the derivation.
- **Signal line** — 13- or 7-period EMA of TSI itself. Crossovers of TSI vs signal line are the primary entry/exit triggers.
- **vs RSI** — RSI compares average gains to average losses (RSI = 100 − 100/(1+RS)). TSI uses *signed* raw price changes with double smoothing → less whipsaw, more sensitive to actual trend inflections.
- **Zero-line** — TSI > 0 = net bullish momentum; TSI < 0 = net bearish. Secondary confirmation on top of crossovers.
- **Best pairing** — [[concepts/SuperTrend]] or MAST (Moving Average + SuperTrend) for trend; [[concepts/Point-and-Figure-Charts]] for price rendering (eliminates time-based noise).

## The 4-Quadrant Matrix

| Trend | TSI signal | Meaning | Action |
|---|---|---|---|
| Bullish (Price > SuperTrend) | Positive crossover | Strong up-momentum | Ideal long entry |
| Bullish | Negative crossover | Momentum fading → range/consolidation | Partial exit / tighten stop |
| Bearish (Price < SuperTrend) | Negative crossover | Strong down-momentum | Ideal short entry |
| Bearish | Positive crossover | Downtrend weakening | Watch for reversal / consolidation |

## Six Worked Examples (paraphrased)

1. **Bullish breakout** — Price > SuperTrend, TSI+, P&F Turtle Pattern → long.
2. **Profit booking** — Bullish trend, TSI− → book partial, tighten stop.
3. **Early reversal warning** — Bearish trend consolidating, TSI+ appears *before* SuperTrend flip → early long.
4. **Strong uptrend + fade** — ₹500 → ₹1200 rally, TSI− at top signals exhaustion; later bear trap + double-bottom sell → reversal.
5. **Consolidation breakout** — ₹94–₹110 base, TSI+ crossover, break above ₹110 → ₹212 (+126%).
6. **Broadening top** — Broadening pattern (high churn), TSI+ in bullish trend → successful upside breakout.

## How the Author Trades It

- Scans daily and 5-min TF continuously.
- Runs alerts on **negative TSI crossovers** as leading exit signals.
- Feeds into a 4-step selection filter: market cap → volume → volatility → trend alignment.
- Deployed live at the [[entities/MarkUp-Platform]].

## Local Fit / Actionability

- **Chart integration** — TSI is not currently in `INDICATOR_DEFS`. Fits naturally as a 5th chart pane alongside [[concepts/MACD-Divergence]] and [[concepts/RSI]]; both share the "oscillator below price" slot pattern already established after `87a49c6` (RS Line) and `fcb3faa` (MACD).
- **Scanner integration** — Negative TSI crossover in bullish trend is a clean scanner rule; complements the SwingEdge Momentum Buildup family.
- **Cross-check** — Compare TSI(25,13) vs [[concepts/KST]] (Know Sure Thing — another double-smoothed ROC composite); the two solve overlapping problems, so pick one to avoid redundancy.

## Contradictions / Open Questions

- Author claims 95% of traders haven't heard of TSI. Directional plausibility, but no citation. Treat as rhetorical.
- Video does not disclose backtest stats for the 4-quadrant matrix. Rules-of-thumb, not measured edge.

## Cross-References

- Concept: [[concepts/True-Strength-Index-TSI]] · [[concepts/SuperTrend]] · [[concepts/Point-and-Figure-Charts]]
- Related indicators: [[concepts/RSI]] · [[concepts/KST]] · [[concepts/MACD-Divergence]] · [[concepts/Percent-R-Trend-Exhaustion]]
- Companion trend tools: [[concepts/EMA]] · [[concepts/PMax]]
- Entity: [[entities/Kaushik-Akkiwakar]] · [[entities/MarkUp-Platform]]
