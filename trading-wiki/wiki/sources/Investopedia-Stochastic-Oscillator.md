---
title: "Investopedia — Stochastic Oscillator (article 073001)"
category: source
tags: [oscillator, momentum, stochastic, lane]
created: 2026-07-14
updated: 2026-07-14
sources: 1
related:
  - concepts/Stochastic-Oscillator.md
  - concepts/RSI.md
  - concepts/True-Strength-Index-TSI.md
---

# Investopedia — Stochastic Oscillator

## Metadata
- **URL**: https://www.investopedia.com/articles/technical/073001.asp
- **Fetched**: 2026-07-14
- **Fetch status**: **Blocked** — WebFetch could not retrieve investopedia.com from this session.
- **Filed from**: canonical George C. Lane (1950s) reference material. Re-ingest and enrich when the URL is accessible from a subsequent session.
- **Raw**: `.raw/articles/investopedia-stochastic-oscillator-2026-07-14.md`

## Key Takeaways
1. **Author**: George C. Lane, late 1950s at Investment Educators, Chicago.
2. **Premise**: In an uptrend closes cluster near the range high; in a downtrend, near the low. Stochastic quantifies the close's position within the recent range.
3. **Formulas**: raw %K = `100 × (Close − LowestLow(n)) / (HighestHigh(n) − LowestLow(n))`; %K = SMA(raw %K, kSmooth); %D = SMA(%K, dSmooth).
4. **Defaults**: (14, 3, 3) is the widely-taught "slow stochastic". (14, 1, 3) is the "fast" variant. Full stochastic exposes both smoothing parameters.
5. **Thresholds**: 80 overbought / 20 oversold / 50 centreline.
6. **Signals**: %K/%D crossover in extreme zones; exit-from-extreme; bullish/bearish divergence; Lane's higher-quality "bull/bear setup" (divergence + failed retest).

## Detailed Notes
See [[concepts/Stochastic-Oscillator]] for the concept page. See raw file for the full canonical reference.

## Actionable Insights
- Wired as a sub-pane indicator in the chart tool as **Stochastic (14,3,3)** — cyan %K + dashed orange %D with 80/50/20 guide lines. See [tools/chart_dashboard.html](../../tools/chart_dashboard.html) `stochSeries()` and its render block.
- Pairs naturally with [[concepts/PMax]] (trend filter) — take Lane crossovers only when PMax direction agrees.

## Contradictions with Existing Wiki
None. Complements existing oscillators: [[concepts/RSI]], [[concepts/True-Strength-Index-TSI]], [[concepts/Percent-R-Trend-Exhaustion]], [[concepts/ConnorsRSI]].

## Pages Updated
- Created [[concepts/Stochastic-Oscillator]]
- Updated [[index]]
- Updated [[log]]
- Wired into chart tool (`tools/chart_dashboard.html`)
