---
title: "Radar-Chart Stock Scoring (Growth · Valuation · Finance · Sentiment)"
category: concept
tags: [radar-chart, scorecard, fundamentals, growth, valuation, finance, sentiment, visualization]
created: 2026-07-25
updated: 2026-07-25
sources: 1
related:
  - sources/YT-Stock-Radar-Chart-Skill.md
  - analyses/Radar-Chart-Analyzer-Fit.md
  - concepts/CANSLIM.md
  - analyses/Dashboard-UI-Roadmap.md
---

# Radar-Chart Stock Scoring

## Definition
A compact **fundamental scorecard** that reduces a stock to **four 0–10 axes** —
**Growth, Valuation, Finance, Sentiment** — and draws them as a **radar (spider)
chart** so shape tells the story at a glance. A "balanced" stock is a big even
diamond; a lopsided one (e.g. great Finance, poor Valuation) shows as a spike.
Sourced from [[sources/YT-Stock-Radar-Chart-Skill]].

## The four axes and their component metrics
| Axis | Component metrics (each scored /10) | Direction |
|---|---|---|
| **Growth** | Sales growth (3Y CAGR), Profit growth (3Y CAGR), EPS growth (YoY) | higher better |
| **Valuation** | P/E, Price/Book, PEG | **cheaper better** (inverted) |
| **Finance** | ROE, ROCE, Debt/Equity (balance-sheet quality) | higher ROE/ROCE, lower debt |
| **Sentiment** | price/momentum context (e.g. distance from 52-week high, trend) | higher better |

## Scoring
1. **Metric → /10 via bands.** Each raw metric maps onto 0–10 (e.g. EPS growth +57.8%
   → 10/10; P/E 25.3x → 4/10; P/B 4.36x → 4/10). Valuation metrics invert
   (cheap = high score).
2. **Axis = mean of its component /10 scores.**
3. **Overall = mean of the four axes** (a plain average, not a weighted blend —
   verified against the source's own table).
4. **Auto strength/concern:** surface the single best axis/metric as a ✅ strength and
   the single worst as a ⚠ concern in plain language.

## How to Use
- **Triage a watchlist/portfolio** — rank by Overall, then read *shape*: two stocks with
  the same Overall can be opposite bets (cheap-but-slow vs dear-but-fast).
- **Spot the trade-off you're taking** — the radar makes "I'm paying up for growth"
  (Valuation spike inward, Growth outward) visually obvious.
- **Compare overlay** — superimpose several stocks' radars to see who dominates which
  axis.

## Variants / Parameters
- **Axis choice** is a design decision — Growth/Valuation/Finance/Sentiment is one
  sensible 4-tuple; others use Quality/Momentum/Value/Size, etc.
- **Weighting** — the source uses an equal-weight mean; a weighted Overall (e.g. tilt to
  Finance for quality investing) is a natural variant.
- **Metric bands** must be **calibrated to the universe** (Indian large/mid/small-caps
  have different "normal" P/E and ROCE) or the scores mislead.

## Common Mistakes
- **Reading radar *area* as meaning.** Polygon area depends on axis order and is not a
  real quantity — use it for *shape/balance*, not precision. The Overall number, not the
  area, is the comparable.
- **Uncalibrated bands** — a fixed "P/E 25 → 4/10" band is wrong across sectors; a bank,
  an FMCG name, and a cyclical don't share a valuation scale.
- **Treating it as timing.** This is a **fundamental snapshot**, not an entry signal —
  pair it with the technical/setup read, don't trade off the radar alone.
- **Stale fundamentals** — screener.in figures are last-reported-quarter; timestamp them
  (wiki rule: "price levels decay" — so do fundamentals).

## Related Concepts
- [[concepts/CANSLIM]] — another multi-factor stock scorecard (growth + RS + institutional).
- [[concepts/FPV-Flow-Price-Volume-Ownership]] — the "Sentiment/flow" leg has a cousin here.
- [[analyses/Radar-Chart-Analyzer-Fit]] — how this maps onto our Stock Analyzer.

## Sources
- [[sources/YT-Stock-Radar-Chart-Skill]] (2026-07-25) — the video/skill this is drawn from.
