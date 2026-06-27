---
title: "CCI — Commodity Channel Index"
category: concept
tags: [momentum, oscillator, breakout-trigger, chartink]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [concepts/RSI.md, concepts/ADX.md, strategies/Screener-Queries.md, concepts/VCP.md]
---

# CCI — Commodity Channel Index

## Definition
CCI = (Typical Price − SMA(Typical Price, N)) / (0.015 × Mean Deviation), where Typical Price = (High + Low + Close) / 3. The screeners ingested here all use period N = 34 (longer than the classic default of 20).

## How to Use
- **CCI(34) > +100**: strong upward momentum — used as the primary "momentum confirmation" gate across 6 of 7 Nimblr chartink scanners (see [[strategies/Screener-Queries]]).
- Stricter variants raise the threshold to **110** (Volume Shocker, weekly Multibagger screen) or **133** (FII-DII Volume Interest proxy) to filter for stronger momentum.
- Values beyond ±200 are considered extreme/overbought-oversold for CCI.

## Variants / Parameters
- Period 34 throughout (vs classic 20) → smoother, fewer false triggers, more suited to swing/position screens.
- Almost always paired with a second confirming condition: a tight price range / contraction (VCP-like), volume expansion (SMA20 vol > SMA50 vol), and/or a trend filter (close > SMA200).

## Common Mistakes
- Using CCI(34) > 100 alone, with no trend or volume filter — every scanner in [[strategies/Screener-Queries]] pairs it with at least one of those.

## Related Concepts
- [[concepts/RSI]] — alternative momentum oscillator; plays a similar "trigger" role to CCI(34)>100 here, but on a different scale/calculation
- [[concepts/VCP]] — the "Accumulation Breakout" chartink scanner is essentially a CCI-gated VCP_1C variant
- [[strategies/Screener-Queries]] — full set of CCI-based chartink scanners

## Examples in This Wiki
- [[strategies/Screener-Queries]] — Chartink scanners 1 and 3–7 all use CCI(34) as a momentum gate

## Sources
- [[sources/Chartink-Atlas-Nimblr-Dashboard]] (2026-06-15)
