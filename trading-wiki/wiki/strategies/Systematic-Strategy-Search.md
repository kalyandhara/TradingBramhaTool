---
title: "Systematic Strategy Search (Theory → SubTheory → Strategy)"
category: strategy
tags: [methodology, optimization, strategy-search, system-design, portfolio]
timeframe: all
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [concepts/Genetic-Algorithm-Optimization.md, concepts/Capital-Management-Methods.md, concepts/Performance-Metrics.md, analyses/Kalyan-Trading-Philosophy.md, concepts/PMax.md]
---

# Systematic Strategy Search (Theory → SubTheory → Strategy)

## Core Idea
Instead of hunting for a single super-profitable strategy, build a pipeline that automatically generates, filters, optimizes, and runs **hundreds of modestly-profitable strategies (0.5-1%/month each)** in parallel across different financial instruments. Profitability comes from breadth and diversification of small edges, not from one big edge. This is a portfolio-of-strategies philosophy — complements [[analyses/Kalyan-Trading-Philosophy.md]]'s "the market always has opportunity, don't chase one trade" rule at the strategy-construction level.

## Setup Criteria — The Entity Model
A strict hierarchy of entities defines a strategy without ambiguity:
- **Indicator** — a single technical calculation (e.g. ADX(14), CCI(34)).
- **Signal** — a group of conditions combined with AND/OR. Each condition compares a left side (indicator or value) to a right side (indicator or value) using a comparison operator, optionally with a candle-depth lookback (e.g. "ADX(14) [2 candles ago] > 25").
- **Theory** — a *template* of signals with no concrete parameter values yet (e.g. "price crosses above an MA, confirmed by ADX above some threshold" — MA length and ADX threshold left as variables).
- **SubTheory** — a Theory plus a concrete optimization-algorithm configuration: parameter ranges and step sizes (e.g. `LookbackPeriod ∈ [1,300]` step 15).
- **Strategy** — a Theory + concrete parameter values (the winning combination from optimization) + a chosen [[concepts/Capital-Management-Methods]] method + a chosen risk-control method (stop loss / take profit / trailing config).

## Entry Rules — The Three-Step Search Process

### Step 1: Coarse "Quality Condition" Filter
Run a SubTheory with **wide parameter ranges and large step sizes** through a breadth-tuned optimization algorithm (see [[concepts/Genetic-Algorithm-Optimization]]) — the goal is *cheap rejection* of theories that are obviously bad, not finding the final answer. A separate **quality condition** (a yes/no suitability filter — e.g. minimum trade count, maximum drawdown ceiling from [[concepts/Performance-Metrics]]) is applied to weed out statistically meaningless results. The quality condition is deliberately kept *separate* from the optimization objective function so that "technically optimal but practically useless" results (e.g. 3 trades with huge profit factor) don't pass.

### Step 2: Iterative Narrowing
Take the top-N results (e.g. top 5) from Step 1 and use their parameter values to define a new SubTheory with a **narrower range and smaller step size** around those values. Worked numeric example from the source: `LookbackPeriod` narrowed from `[1,300]` step 15 → `[1,211]` step ≈11, based on where the top-5 results clustered. Repeat across successive SubTheories until the parameter ranges converge.

### Step 3: Forward Test + Final Quality Gate
Take surviving strategies (now with narrow, near-optimal parameters) and **forward-test them on out-of-sample instruments/periods** they weren't optimized on. Apply the final quality condition. Strategies that pass are handed off to real trading.

## Exit Rules (Strategy Lifecycle, Not Per-Trade)
- A strategy that stops meeting quality conditions live (e.g. drawdown breach, instrument type changes — see Instrument Grouping below) gets disabled by an external **audit** process that continuously monitors live strategy balances for anomalies.
- Per-trade exits (stop loss, take profit, trailing stop) are a property of the Strategy entity itself — see [[concepts/PMax]] for the "Trailing System Order" algorithm variant documented alongside it.

## Timeframe
All — the framework is timeframe-agnostic; the book targets average position lifetimes of minutes-to-hours (explicitly *not* scalping, to avoid needing colocated low-latency infrastructure).

## Best Market Conditions
- Works best when many financial instruments are classified by **type** (price range, volume profile, volatility, trend/flat/sideways) and strategies are only deployed on instruments matching the type they were optimized for. This balances generalization (a strategy shouldn't be so specific it only works on one stock's exact history) against overfitting (a strategy tested on "everything" tends to find spurious edges).
- Instrument types are re-evaluated continuously with **hysteresis** (don't flip a strategy on/off on every borderline reading) before strategies are enabled/disabled for that instrument.

## Worst Market Conditions
- A regime shift that changes many instruments' "type" simultaneously (e.g. broad volatility spike) could disable many strategies at once — the framework doesn't have a documented portfolio-level circuit breaker beyond per-strategy quality conditions and the external audit process.

## Backtest / Track Record
- No live track record given — this is the *author's own system design*, presented as a blueprint rather than a published result. Recommended backtest length: 5 years for daily charts, ≥1 year for intraday.

## Examples
- Worked numeric example for Step 2 narrowing (`LookbackPeriod [1,300] step 15` → `[1,211] step ~11`) is the only concrete numeric walkthrough in the source.

## Related Concepts
- [[concepts/Genetic-Algorithm-Optimization]] — the optimization-algorithm layer used inside each SubTheory's search
- [[concepts/Capital-Management-Methods]] — the position-sizing component of a finished Strategy
- [[concepts/Performance-Metrics]] — objective function + quality-condition metrics used at every step
- [[concepts/PMax]] — Trailing System Order algorithm (TrailingPrice/ProfitBorderCoeff/StopBorderCoeff/BorderChangeCoeff) documented as part of risk control for a Strategy
- [[analyses/Kalyan-Trading-Philosophy.md]] — "many small opportunities, not one big bet" philosophy at the portfolio level mirrors this framework's "hundreds of modest strategies" approach

## Sources
- [[sources/Dolzhenko-Algorithmic-Trading-Systems-2024]] (2026-06-15)
