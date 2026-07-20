---
title: "Market Sentiment Index"
category: concept
tags: [sentiment, breadth, composite, pcr, advance-decline, sector-rotation, regime]
created: 2026-07-14
updated: 2026-07-14
sources: 1
related:
  - sources/Madhur-Raut-Market-Sentiment-Index-Infographic.md
  - sources/OptionTools-in.md
  - concepts/Stage-Analysis.md
  - strategies/Sector-Momentum-Map.md
  - analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14.md
---

# Market Sentiment Index

## Definition
A **weighted composite score (0-100)** of index-level breadth and technical inputs, mapped to a five-band gauge (Strong Sell / Sell / Neutral / Buy / Strong Buy). Purpose: a **single-number regime gauge** the trader reads before deciding whether to take fresh long / short exposure or sit out.

Analogous to CNN's *Fear & Greed Index*, but tuned for the Indian cash + options market. Canonical construction from [[sources/Madhur-Raut-Market-Sentiment-Index-Infographic]].

## How to Use
- **Regime gate**: below 40 = defensive (skip fresh longs, tighten stops); 40-55 = normal; above 55 = risk-on. Similar posture to Minervini's SMA200 regime rule and Varmer's 200-MA gate ([[sources/YT-Samir-Varmer-Physicist-Trader]]).
- **Position-size dial**: half-size below 30, full-size above 70. Complements [[concepts/Kelly-Criterion]] as a top-down volatility multiplier.
- **Confirmation only, not a trigger**: the gauge is slow relative to per-symbol setups — it should filter, never generate, entries.

## Composition (Raut variant)
| Indicator | Weight | Signal source | Notes |
|-----------|--------|---------------|-------|
| PCR Trend | 30 | NSE NIFTY options | Direction of PCR matters more than absolute value; declining PCR = puts unwinding = bearish undertone |
| Advance / Decline Ratio | 20 | NSE bhavcopy daily | Count of stocks up vs down (whole market or NIFTY-500) |
| Sector Performance | 20 | 22 NSE sectors | Green-vs-red sector count |
| Hourly Technical Trend | 15 | NIFTY 1H | Composite of EMA/RSI/MACD (indicator stack not disclosed) |
| 3-Minute Technical Trend | 15 | NIFTY 3M | Same stack, faster TF |

Score in each row = `weight × factor`, `factor ∈ [0, 1]`. Rule-based discretisation (e.g. "Declining" PCR = fixed fraction, "Neutral" TT = 0.53).

Total = sum → gauge band.

## Variants / Parameters
- **Weights are arbitrary** — the 30/20/20/15/15 split is Raut's, not derived. Any composite of the same inputs would work; a more principled split would weight by predictive lift on next-day NIFTY return.
- **Options input** could be swapped for **India VIX** (regime volatility) or **Max Pain deviation** — see [[sources/OptionTools-in]].
- **Technical trend** could be replaced by [[concepts/PMax]] direction on NIFTY, [[concepts/Stage-Analysis]] stage of NIFTY, or SMA200 slope — all cleaner than an undisclosed indicator stack.
- **Breadth** could add **% of NIFTY-500 above 50-DMA** and **new-highs-minus-new-lows** — both are single-number lifts.

## Common Mistakes
- Using the index as a **trigger** rather than a **filter**. Composite indices lag by construction.
- Reading the absolute score as more precise than it is; the value of the gauge is the **band**, not the digit.
- Treating "Neutral" cells as informative — Raut's card scores neutral TT at 53%, which is a fixed placeholder, not a real read.
- Not versioning the weighting scheme. Once weights change, historical scores are no longer comparable.

## Related Concepts
- [[concepts/Stage-Analysis]] — regime bucket at the individual-stock level; sentiment index is the market-wide analogue.
- [[concepts/Kelly-Criterion]] — position sizing that a regime gauge multiplicatively down-weights.
- [[concepts/Distribution-Days]] — bearish breadth signal that would fit naturally as a sixth input.

## Examples in This Wiki
- 14 Jul 2026 reading: **34/100 SELL** (PCR 1.01 declining, A/D 834:2151, Sectors 5G/17R). Snapshot in [[sources/Madhur-Raut-Market-Sentiment-Index-Infographic]].

## Sources
- [[sources/Madhur-Raut-Market-Sentiment-Index-Infographic]]
