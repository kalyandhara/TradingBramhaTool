---
title: "Mansfield Relative Strength"
category: concept
tags: [relative-strength, mansfield, weinstein, benchmark, outperformance]
created: 2026-06-14
updated: 2026-06-25
sources: 2
related: [strategies/PMax-Confluence-Strategy, concepts/VCP, strategies/VCPBot-Trend-Template, sources/Minervini-Market360-Dashboard-Video]
---

# Mansfield Relative Strength

## Definition
A normalized relative-strength oscillator (Stan Weinstein method) that measures whether a stock is outperforming or underperforming a benchmark (index/ETF), oscillating around a zero line.

## How to Use
1. `rsRatio = close / benchmarkClose`
2. `rsRatioMA = SMA(rsRatio, 52)` (52-period = roughly 1 year on weekly, or one "Weinstein" cycle on the chosen timeframe)
3. `rsMansfield = (rsRatio / rsRatioMA − 1) × 100`
4. **rsMansfield > 0** → stock is outperforming the benchmark (relative strength bullish)
5. **rsMansfield < 0** → underperforming (relative strength bearish)
6. Trend of RS line matters as much as sign: compare current value to N bars ago (`rsTrendLen`, default 5) to determine if RS is rising or falling.

## Variants / Parameters
- Benchmark symbol: default SPY (US) — **for Indian markets, swap to NIFTY 50 / relevant sector index**.
- Smoothing length: 52 (Weinstein default)
- Trend lookback: 5 bars

## Common Mistakes
- Using a benchmark that isn't representative of the stock's actual peer group/sector (e.g. comparing a small-cap to a broad index dilutes the signal).
- Treating RS in isolation — it's a confirmation/filter factor, not a standalone entry signal.
- **Non-benchmark "RS Rating" formulas circulating in AI-generated guides**: one ingested source ([[sources/Minervini-Market360-Dashboard-Video]]) defines `RS Rating = (52w_high − price) / (52w_high − 52w_low) × 100` — this has no benchmark term at all, just the stock's own position in its 52-week range (closer to an inverted Stochastic %K). It would score a stock as "strongest" the further below its own high it sits — the opposite of relative *strength*. Don't use it; use the benchmark-relative formula above, or the percentile-ranked RS Rank in [[strategies/VCPBot-Trend-Template]] (`0.4×ROC63 + 0.2×ROC126 + 0.2×ROC189 + 0.2×ROC252`, percentile vs universe).

## Related Concepts
- [[strategies/PMax-Confluence-Strategy]] — RS is one of 16 confluence factors (outperform/underperform/inline)
- [[concepts/VCP]] — RS Rank is also used as a dual-gate filter in [[strategies/VCPBot-Trend-Template]]

## Examples in This Wiki
- [[strategies/PMax-Confluence-Strategy]] — "Rel Strength" dashboard row (OUTPERFORM/UNDERPERFORM/INLINE vs benchmark)

## Sources
- [[sources/PMax-Optimization-Pine]] (2026-06-14)
- [[sources/Minervini-Market360-Dashboard-Video]] (2026-06-25) — flagged a non-standard, benchmark-less "RS Rating" formula to avoid
