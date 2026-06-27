---
title: "Distribution Days"
category: concept
tags: [distribution, volume, bearish, downside-risk, institutional-selling]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [sources/SwingEdge-Downside-Risk-Screener, entities/AADHARHFC, concepts/Stage-Analysis, concepts/Support-Resistance, concepts/ADX]
---

# Distribution Days

## Definition
A **distribution day** is a single trading session showing statistical evidence of institutional selling pressure: price closes down, on volume meaningfully above average, with a wide range and a close near the session low. It's the bearish mirror of an "accumulation day" (institutions quietly buying). Clusters of distribution days are a classic precursor signal studied in CANSLIM-adjacent and Wyckoff-adjacent literature — already referenced once in this wiki on [[entities/AADHARHFC]] ("6 distribution days recently — institutional selling").

## How to Use
**SwingEdge's operational definition** (the most precise formulation in this wiki so far, from [[sources/SwingEdge-Downside-Risk-Screener]]):
> "A bearish distribution day requires price closing down, volume at least 0.5 standard deviations above the 50-day average, a wide spread and a close near the low of the day — all weighted together for accuracy. **Three or more clusters often precede major NSE breakdowns.**"

Practical reading checklist for a single session to qualify:
1. Close < prior close (down day)
2. Volume ≥ 50-day average + 0.5σ (a volume z-score threshold, not just "above average")
3. Wide range (high − low meaningfully larger than typical recent ranges)
4. Close near the low of the day's range (selling held through the close, not bought back)

Count clustered occurrences (3+ within a recent lookback window, e.g. 4–6 weeks) rather than treating any single day as meaningful in isolation — one distribution day is noise; a cluster is a structural warning.

## Variants / Parameters
- **Volume z-score threshold**: 0.5σ above the 50-day average volume is SwingEdge's specific cutoff — a relatively low bar (many "above average volume" days will already clear it), so the *combination* with wide-range + weak-close is what filters noise, not the volume rule alone.
- **Lookback window for "recent"**: not specified exactly by the source; AADHARHFC's "6 distribution days recently" wasn't given an explicit window length either — treat counts from this source as relative/comparative, not an absolute calendar-defined count, until confirmed otherwise.
- **Severity tiering**: SwingEdge folds distribution-day counts into a broader 0–100 bearish composite score (alongside DMA stack inversion, pivot retest failures, RSI/MACD softness, RS percentile) and labels the result Severe (80+), High (65–80), Moderate (50–65) — see [[sources/SwingEdge-Downside-Risk-Screener]] for the full composite.

## Common Mistakes
- Treating a single distribution day as actionable — the signal is in the *cluster count*, not any one session.
- Conflating "down day on high volume" with "distribution day" — the close-near-the-low requirement matters; a down day that closes well off its lows is a weaker signal (some buying interest absorbed the selling).
- Assuming distribution-day counts and a stock's broader trend agree — AADHARHFC showed a constructive volume/accumulation narrative in some panels of the same SwingEdge page while separately carrying a distribution-day skip flag; the two metrics can disagree on the same name, and the disagreement itself can be informative (mixed institutional activity, not a clean signal).

## Related Concepts
- [[concepts/Stage-Analysis]] — a "bearish DMA stack" (faster MAs below slower MAs, negative slopes) is explicitly described by SwingEdge as "the inverse of popular Stage 2 illustrations" — i.e. Stage 4 (decline) territory in Weinstein's framework, identified by the mirror-image rule set to the bullish Stage 2 trend template already documented in this wiki.
- [[concepts/Support-Resistance]] — SwingEdge's "support loss" detection (a structural-break trigger) uses a specific, falsifiable rule: pivot lows = local minima with ≥2 confirming candles on each side, and a close >0.5% below that pivot triggers the break flag — more rigorous than a simple rolling-minimum check, and a concrete operational definition worth comparing against this wiki's existing zone-based S/R framework.
- [[concepts/ADX]] — trend-strength components are folded into SwingEdge's bearish composite score alongside the distribution/support/RS inputs.

## Examples in This Wiki
- [[entities/AADHARHFC]] — first ticker in this wiki flagged with a distribution-day skip reason ("6 distribution days recently — institutional selling"), ingested before this concept page existed to formally define the term.

## Sources
- [[sources/SwingEdge-Downside-Risk-Screener]] (2026-06-22) — full methodology: support-loss detection, distribution volume z-score model, Severe/High/Moderate confidence tiers
