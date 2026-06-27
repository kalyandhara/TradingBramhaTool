---
title: "McDowell Probability Matrix (MPM)"
category: concept
tags: [elliott-wave, confluence-score, wave-count-confidence, risk-control]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [concepts/Elliott-Wave.md, concepts/RSI.md, concepts/PMax.md, strategies/PMax-Confluence-Strategy.md]
---

# McDowell Probability Matrix (MPM)

## Definition
A 6-factor scoring worksheet (from Bennett McDowell, *Elliott Wave Techniques Simplified*) that converts a subjective Elliott Wave count into a numeric confidence score, used to decide whether a wave-based forecast is worth acting on.

## How to Use
Score each of the 6 factors 0–5 (0 = lowest probability, 5 = highest), sum for a total out of 30:

1. **Clear price structure (classic)** — can the 5-wave pattern be read cleanly on the chart, with an identifiable Wave 3?
2. **Clear OWL/price-oscillator reading (modern)** — does the price oscillator histogram (5/35 on low, histogram) show the steepest peak/trough at the candidate Wave 3, with bearish/bullish divergence into Wave 5?
3. **Volume confirms Wave 3 (classic)** — is volume highest at the candidate Wave 3 and declining into Wave 5, as expected?
4. **Fibonacci levels hit (classic)** — do Wave 2/4 retracements and the Wave 5 extension land in their expected zones (see [[concepts/Elliott-Wave]] statistics tables)?
5. **RSI/PTF behavior (modern)** — RSI(9, bands 80/20): does band penetration (or its absence at Wave 5) align with the forecast?
6. **Multi-timeframe alignment (modern)** — does a higher timeframe (~3-5x the base interval) show the same OWL histogram trend direction (fractal symmetry)?

Total score interpretation (lower → higher confidence): roughly 0-9 = minimal probability, up to 28-30 = outstanding probability that the wave count is correct. Be conservative while learning — the score is only as good as the accuracy of each component read.

## Grounded vs. Ungrounded Assessments
- **Ungrounded** = the MPM score and the Elliott Wave forecast itself. It tells you *direction* only — it is a filter, not a trigger.
- **Grounded** = your price-based entry, stop-loss, and exit rules. These always take priority. Never size or hold a position based on the forecast alone; the forecast only decides which direction you're willing to take a grounded signal.

## Variants / Parameters
- OWL settings: price oscillator, short MA = 5, long MA = 35, source = low, histogram display.
- PTF settings: RSI length = 9 on close, bands at 80/20.
- "144 price bars" (a Fibonacci number) is the default lookback window for "the current dominant trend" across timeframes.

## Common Mistakes
- Treating a high MPM score as permission to skip a stop-loss — it isn't; risk control is independent of forecast confidence.
- Forcing a score on a messy/complex-correction chart instead of moving to a clearer chart or timeframe.
- Using standard RSI 70/30 overbought/oversold logic instead of the 80/20 band-*penetration* logic this matrix relies on (factor 5).

## Related Concepts
- [[concepts/Elliott-Wave]] — the wave count and statistics this matrix is scoring
- [[concepts/PMax]] / [[strategies/PMax-Confluence-Strategy]] — a similar idea (multi-factor confluence → graded score → position sizing), applied to entry/exit grading rather than wave-count confidence. The two scoring systems are complementary and could be combined.
- [[concepts/RSI]] — note the differing band convention (80/20 penetration vs. 40-80/20-60 regime ranges) when combining indicator panes

## Examples in This Wiki
- None scored yet — first candidate would be applying the MPM to a current watchlist name (e.g. from [[overview]]) alongside its existing PMax confluence score.

## Sources
- [[sources/EW-Techniques-Simplified-McDowell]] (2026-06-15)
