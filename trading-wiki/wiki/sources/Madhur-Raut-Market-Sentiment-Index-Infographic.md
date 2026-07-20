---
title: "Madhur Raut — Market Sentiment Index Infographic"
category: source
tags: [sentiment, breadth, pcr, advance-decline, sector-rotation, india]
created: 2026-07-14
updated: 2026-07-14
sources: 1
related:
  - concepts/Market-Sentiment-Index.md
  - entities/Madhur-Raut.md
  - analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14.md
---

# Infographic — Market Sentiment Index (Madhur Raut, 14 Jul 2026)

## Metadata
- **Author**: Madhur Raut (retail trader / educator, India)
- **Format**: Dark-themed sentiment-gauge infographic (social media share)
- **Date on card**: Tuesday, 14 July 2026
- **Raw**: `.raw/images/market-sentiment-index-madhur-raut-2026-07-14.md`
- **Disclaimer on card**: "Not SEBI registered" — treat as educational, not advisory.

## Key Takeaways
1. **Composite sentiment score 0–100** driven by five weighted indicators totalling 100 weight.
2. **Breadth-heavy weighting** (70/100): PCR Trend (30) + Advance/Decline (20) + Sector Performance (20).
3. **Technical weighting is light** (30/100): Hourly TT (15) + 3-Minute TT (15) — both "Neutral" cells scored 8/15 flat, suggesting a static midpoint when not directional.
4. Gauge bands: **0-20 Strong Sell · 20-40 Sell · 40-55 Neutral · 55-80 Buy · 80-100 Strong Buy**.
5. Snapshot reading: **34/100 → SELL** — PCR 1.01 declining (10/30), A/D 834:2151 (3/20), Sectors 5G/17R (5/20).
6. Impact-bar colour codes score-vs-weight fraction (red <40%, yellow 40-70%, green >70%).

## Detailed Notes

### The five indicators
- **PCR Trend** — Put/Call Ratio direction on NIFTY options. 1.01 is roughly neutral in absolute terms but the *direction* (declining) is what scores; declining PCR = puts unwinding faster than calls = bearish undertone. Weight 30 makes this the dominant single input.
- **Advance / Decline Ratio** — Number of NSE stocks up vs down on the day. 834:2151 is deeply negative; score 3/20 = 15%.
- **Sector Performance** — Green vs red sectors out of 22 (matches NSE's 22-sector cut). 5/17 = 23% green.
- **Hourly Technical Trend** — Multi-indicator 1H read on NIFTY (unspecified indicators, likely EMA/RSI/MACD stack). Neutral = 8/15 (53%).
- **3-Minute Technical Trend** — Same idea at 3M. Neutral = 8/15.

### Scoring model (inferred)
Each row: `score = weight × factor`, where `factor ∈ [0, 1]`. Sum of scores gives the 0-100 headline. Rows appear to be **rule-based-discretized** rather than continuous — PCR "Declining" maps to some fixed fraction, "Neutral" TT rows land on 53%.

### Where it lands vs our existing stack
- We already ingest **PCR** and options flow via [[sources/OptionTools-in]] (max pain, PCR, ATM CE/PE buildup), but consume it descriptively — not folded into a composite.
- **Sector performance** is available in [[strategies/Sector-Momentum-Map]] and [[sources/SwingEdge-Sector-Momentum-Map-20260622]] — same "green vs red count" is a natural sub-output.
- **Advance/Decline** is NOT currently computed anywhere — would need a bhavcopy pass (we already fetch bhavcopy for [[sources/HB-Stocks-6-Filters]] and screener pipeline).
- **Hourly + 3-Min Technical Trend** — no direct equivalent; we compute per-symbol technicals but not an index-level composite.

## Actionable Insights
See [[analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14]] for the full roadmap assessment. TL;DR: **medium-value, low-effort addition** — three of the five inputs are already computable from data we ingest, and it slots into `india_market_intel.py` as a top-of-dashboard gauge card.

## Contradictions with Existing Wiki
None — this is a new surface (index-level breadth composite) with no direct conflict against our per-symbol setups. The **only tension** is that our existing philosophy leans heavily on individual setup quality (VCP, Rounding Bottom, PMax) rather than top-down regime gating; adding a breadth gauge would nudge the workflow toward a regime-first prelude, which several sources ([[sources/Minervini-Think-Trade-Champion]] regime rule, [[sources/YT-Samir-Varmer-Physicist-Trader]] 200-MA regime, [[concepts/Stage-Analysis]]) already endorse.

## Pages Updated
- Created [[concepts/Market-Sentiment-Index]] — composite construction and interpretation
- Created [[entities/Madhur-Raut]] — author profile
- Created [[analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14]] — feasibility + effort estimate
- Updated [[index]]
- Updated [[log]]
