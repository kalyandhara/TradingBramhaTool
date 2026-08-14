---
title: "Book — Algorithmic Trading Systems and Strategies: A New Approach"
category: source
tags: [book, system-design, optimization, capital-management, risk-control, genetic-algorithm]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [strategies/Systematic-Strategy-Search.md, concepts/Capital-Management-Methods.md, concepts/Performance-Metrics.md, concepts/Genetic-Algorithm-Optimization.md, concepts/PMax.md]
---

# Book — Algorithmic Trading Systems and Strategies: A New Approach

## Metadata
- Author: Viktoria Dolzhenko
- Publisher: Apress, 2024
- Format: epub, copied to `raw/Dolzhenko-Algorithmic-Trading-Systems-2024.epub`, converted to plain text via Calibre for full read (16,845 lines)
- Date ingested: 2026-06-15

## Key Takeaways
- Core thesis: build a system that automatically generates, tests, and runs **hundreds of modestly-profitable strategies (0.5-1%/month)** in parallel, rather than searching for one highly-profitable strategy. New methodology page: [[strategies/Systematic-Strategy-Search]].
- Formal entity model for unambiguous strategy definition: Indicator → Signal (AND/OR condition groups) → Theory (template, no params) → SubTheory (Theory + optimization-algorithm config + param ranges/steps) → Strategy (Theory + concrete params + capital management + risk control).
- Comprehensive catalogue of **position-sizing methods** (Kelly Criterion, Optimal f, Martingale/Anti-Martingale, Fixed Proportional/Ryan Jones delta) — new concept page [[concepts/Capital-Management-Methods]].
- Standard **performance metrics** (profit factor, 5 drawdown types, Sharpe ratio, expected value) — new concept page [[concepts/Performance-Metrics]].
- A **"Trailing System Order"** algorithm (TrailingPrice/ProfitBorderCoeff/StopBorderCoeff/BorderChangeCoeff) that progressively tightens stop/profit bands as a position runs — added as an alternative to [[concepts/PMax]]'s ATR-based trailing stop.
- Detailed **genetic algorithm / population algorithm** theory (mutation, crossover, filtering, selection operators; constraint-handling methods) for strategy parameter optimization — new concept page [[concepts/Genetic-Algorithm-Optimization]].
- Three-step strategy search: coarse wide-range filter with a separate "quality condition" → iterative range-narrowing across successive SubTheories → forward-test on out-of-sample instruments before going live.
- Instrument classification (by price range, volume, volatility, trend/flat/sideways type) gates which strategies are allowed to run on which instruments — re-evaluated continuously with hysteresis.

## Detailed Notes

### Trading system fundamentals (Ch. 1-2)
The book opens with the standard trading-system composition: Theory formation → Testing → Capital management → Risk control → Performance evaluation → Optimization. It covers backtest vs. forward test vs. multicurrency/multiperiod testing (recommended 5yr backtest for daily charts, ≥1yr for intraday), and the 8-step optimization workflow (describe strategy → preliminary test → choose data period → test → identify params → set param boundaries → choose optimization algorithm + criteria → select best params and iteratively narrow).

### Risk control (Ch. 2)
Maximum Loss Amount sizing (per-position % risk × max open positions ≤ max account drawdown tolerance, with worked "survival days" examples for a $10k account at various daily drawdown limits). Stop types: initial, trailing, take profit, breakeven, timed. Portfolio diversification guidelines: ≤10% capital per asset, ≤20% per sector — directly comparable to [[analyses/Kalyan-Trading-Philosophy]]'s existing single-stock <10% / SME <20% rules (same numbers, independently arrived at).

### Indicator normalization (Ch. 3)
Min-max scaling of any indicator to a common 0-100 range via `(current - min) / (max - min) * 100` using rolling historical min/max — allows combining indicators of very different native scales (e.g. ADX vs. raw price) in a single signal condition. Minor technique, not given its own page; relevant if building multi-indicator confluence scores like [[strategies/PMax-Confluence-Strategy]].

### Architecture chapters (Ch. 3-5, 8-9)
Large portions of the book (microservices vs. monolith, Kubernetes pod-per-strategy design, Postgres task queues, Kafka message brokers, .NET/Dapper/Clean Architecture implementation, state-machine "Process Bot" pattern, exchange adapter design) are software-engineering/DevOps content for building the author's own trading platform. **Not extracted into the wiki** — low relevance to a strategy/concept-focused trading wiki, though the underlying *Theory→SubTheory→Strategy* and *instrument classification* ideas (which motivate that architecture) were extracted into [[strategies/Systematic-Strategy-Search]].

## Actionable Insights
- [[concepts/Capital-Management-Methods]]'s Fixed Proportional (Ryan Jones delta) method is a concrete formula that could replace ad-hoc position sizing as Kalyan's portfolio scales.
- [[concepts/Performance-Metrics]]'s "quality condition separate from objective function" principle (e.g. always pair "maximize profit factor" with "AND max drawdown < X AND trade count > N") is directly applicable to evaluating any of the existing screener/scanner outputs in [[strategies/Screener-Queries]].
- [[concepts/Genetic-Algorithm-Optimization]]'s operator catalogue is a ready reference if a parameter-sweep tool is ever built for [[strategies/PMax-Confluence-Strategy]] (e.g. tuning ATR multiplier, CCI threshold).
- The min-max indicator normalization technique (Ch.3) could simplify combining oscillators of different scales in confluence scores.

## Contradictions with Existing Wiki
- None directly contradictory. [[analyses/Kalyan-Trading-Philosophy]]'s portfolio % limits (single stock <10%, SME <20%) independently match this book's diversification guidelines (≤10% per asset, ≤20% per sector) — mutually reinforcing, not contradictory.

## Pages Updated
- Created: wiki/sources/Dolzhenko-Algorithmic-Trading-Systems-2024.md (this page)
- Created: wiki/concepts/Capital-Management-Methods.md
- Created: wiki/concepts/Performance-Metrics.md
- Created: wiki/concepts/Genetic-Algorithm-Optimization.md
- Created: wiki/strategies/Systematic-Strategy-Search.md
- Updated: wiki/concepts/PMax.md (added Trailing System Order algorithm section)
- Updated: wiki/index.md, wiki/log.md
