---
title: "Indicator Selection by Regime"
category: concept
family: methodology
tags: [indicators, regime, confluence, methodology, unvalidated]
created: 2026-08-30
updated: 2026-08-30
sources: 1
related: [analyses/Indicator-Coverage-Gap, concepts/Multi-Timeframe-Analysis, concepts/ADX, concepts/SuperTrend, concepts/Bollinger-Bands-Squeeze, concepts/Performance-Metrics, concepts/Volume-Analysis, sources/AI-Summary-Indicator-Taxonomy]
---

# Indicator Selection by Regime

The claim: an indicator is not good or bad, it is **matched or mismatched to the current
market state**. Trend tools bleed in ranges; oscillators bleed in trends. So the first
decision is not *which indicator* but *which regime*, and the indicator follows.

This is the one non-obvious idea in [[sources/AI-Summary-Indicator-Taxonomy]]. Everything
else in that source is standard taxonomy the wiki already carries page-by-page.

## The routing table

| Regime | Family to use | Family to avoid | Why |
|---|---|---|---|
| Strong trend | trailing-stop trend tools (SuperTrend/PMax, SAR, MA band) | overbought/oversold oscillators | RSI pins at 70+ for weeks; every "overbought" read is a losing short |
| Breakout / expansion | band expansion, trend flips, volume confirmation | mean-reversion | the premise of the trade is that the range broke |
| Range / sideways | Stochastic, RSI, MFI at the edges; ATR for stops | trend-following | MAs whipsaw across a flat price |
| Low-volatility coil | none — price structure only | all of them | there is no move to measure yet |
| High volatility / news | ADX for whether the move is a trend, ATR for stop width | tight fixed stops | the question is trend-vs-spike, not direction |

## What this actually requires

The table is unusable without a **regime classifier**, and naming one is where most
presentations of this idea stop. Candidates already present in this repo:

- **ADX** ([[concepts/ADX]], `adxdi`) — the conventional answer; >25 trend, <20 range.
- **Bollinger bandwidth** ([[concepts/Bollinger-Bands-Squeeze]]) — separates the coil case,
  which ADX alone does not.
- **`stai`'s adaptive factor** — the K-means cluster assignment *is* a volatility-regime
  label, produced as a side effect and currently discarded.

## Status: UNVALIDATED

No part of this has been tested here. The specific claims that would need measuring, in
order of how load-bearing they are:

1. **Does regime-gating an oscillator beat running it ungated?** This is the whole thesis
   and it is a clean two-arm test against the existing scorer
   (`evwma_vwap_macd_backtest.event_edge`, which now takes an injected signal source).
2. **Is ADX>25 the right cut?** Threshold almost certainly needs fitting, and fitting it
   invites the overlap problem — see [[analyses/Scanner-Overlap-Audit]].
3. **Do the "under-rated" nominations survive?** The source names MFI, Vortex and MAMA.
   The repo's four most recent indicator measurements returned three nulls, so the prior
   on any nomination sourced from a video is low.

> [!warning] Source quality
> The parent source is an **AI summary of an unattributed video** — no speaker, no channel,
> no URL. It cites no backtest, no sample size, and no losing example. The routing table is
> recorded here because it is *testable*, not because it is supported.

> [!key-insight]
> The testable core reduces to one sentence: **regime should gate which indicator is allowed
> to speak.** If that is true, it is worth more than any individual indicator on the list,
> because it applies to all 44 already implemented. If it is false, it is the reason
> indicator counts keep rising without results improving.
