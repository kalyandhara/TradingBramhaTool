---
title: "Strategy Performance Metrics"
category: concept
tags: [performance, drawdown, sharpe-ratio, sortino, treynor, profit-factor, backtesting]
created: 2026-06-15
updated: 2026-06-16
sources: 2
related:
  - concepts/Capital-Management-Methods.md
  - concepts/Kelly-Criterion.md
  - strategies/Systematic-Strategy-Search.md
  - sources/Wilmott-FAQ-Quantitative-Finance.md
---

# Strategy Performance Metrics

## Definition
A standard set of indicators for evaluating a backtested or live trading strategy, used both to compare strategies during optimization and to monitor live performance for anomalies.

## How to Use

### Profitability / Profit Factor
- **Profit factor** = gross profit / gross loss. Minimum acceptable is >1 (breakeven); a profit factor >6 is described as "more meaningful" — i.e. a strong edge, not just statistical noise.

### Drawdown Types
- **Current drawdown**: drop from the most recent equity peak to the current equity, live/ongoing.
- **Recorded drawdown**: a drawdown episode that has completed (equity recovered to a new high after it).
- **Maximum drawdown**: the largest recorded drawdown over the test period.
- **Absolute drawdown**: measured from the *initial* deposit (can show deficit even before any new equity peak is made).
- **Relative drawdown**: measured as a % of the equity peak at the time (vs. absolute dollar/currency terms).

### Sharpe Ratio
`Sharpe = (μ − r) / σ`
- `μ` = strategy return, `r` = risk-free rate, `σ` = standard deviation of returns (annualized).
- Standard risk-adjusted return measure; higher = better return per unit of volatility.
- In MPT, the Sharpe ratio is the slope of the line joining each portfolio to the risk-free investment. Maximizing Sharpe gives the Market Portfolio.
- **Criticism** (Wilmott): penalizes upside volatility equally with downside — misleading for positively-skewed strategies.

### Sortino Ratio
`Sortino = (μ − r) / σ_downside`
- Denominator is the **square root of semi-variance** — only returns below zero (or a target threshold) contribute.
- Better than Sharpe for **breakout/growth strategies** where upside runs are expected. Sharpe would penalize a stock that surges 30% in a month; Sortino would not.
- Trade-off: semi-variance is noisier (fewer data points used) — requires more history to be statistically reliable.

### Treynor Ratio
`Treynor = (μ − r) / β`
- Uses systematic risk (beta vs market) instead of total volatility.
- More appropriate for **individual stocks or concentrated positions** that are not fully diversified.
- Converges to Sharpe for well-diversified portfolios.

### Information Ratio
`IR = (μ − r_benchmark) / Tracking Error`
- Tracking error = std dev of (portfolio return − benchmark return).
- Measures **value added above a benchmark per unit of active risk**.
- Relevant for fund managers; less directly applicable for a private swing-trading account.

### Modigliani–Modigliani (M²)
`M² = r + σ_benchmark × Sharpe`
- Sharpe ratio expressed in **return units** by scaling to benchmark volatility. Easy to compare to benchmark return directly.

### Average Win / Loss Size
- Track average winning trade size and average losing trade size separately — both feed into [[concepts/Capital-Management-Methods]] (Kelly's `z` ratio, Optimal f's trade-result distribution).

### Expected Value (EV)
`EV = P(win) × AvgWin − P(loss) × AvgLoss`
- The expected $ (or %) result per trade. A strategy with positive EV is profitable in expectation even if its win rate is below 50%, provided AvgWin/AvgLoss compensates.

## Variants / Parameters
- **Recovery factor** (mentioned as a candidate metric, not detailed in source): net profit / max drawdown — measures how efficiently profit is generated relative to the worst pain endured.
- Performance metrics should be computed identically in the backtest/search subsystem and the live-trading subsystem (same Core library) — otherwise live results will silently diverge from backtest expectations.

## Common Mistakes
- Optimizing purely for net profit or profit factor without a drawdown ceiling — a strategy can have an excellent profit factor and an unacceptable max drawdown. The book's "[[strategies/Systematic-Strategy-Search]]" framework explicitly separates the **optimization objective function** from a **quality condition** (a yes/no suitability filter on max drawdown, min trade count, etc.) applied afterward.
- Trusting a small number of trades — profit factor and Sharpe ratio are unreliable with few samples; a minimum trade-count quality condition should always accompany them.

## Related Concepts
- [[concepts/Capital-Management-Methods]] — sizing methods consume these metrics (win rate, avg win/loss) as inputs
- [[strategies/Systematic-Strategy-Search]] — performance metrics are the objective function / quality condition in the strategy search pipeline

## Examples in This Wiki
- None yet implemented in code — candidate metrics to compute when backtesting strategies from [[strategies/Screener-Queries]] or [[strategies/TechnoFunda-Swing]].

## Wilmott's Meta-Critique of Performance Metrics
> "A high Sharpe ratio is intended to be a sign of a good strategy." — but only if returns are approximately normally distributed.

Key Wilmott warnings (from 12 Commonest Mistakes):
- **Too much precision**: quoting performance metrics to 5 decimal places when underlying model assumptions have 10–20% uncertainty gives false comfort.
- **Small sample fallacy**: profit factor and Sharpe are unreliable with few trades. Always enforce a minimum trade-count condition before trusting any metric.
- **Calibration trap**: tuning parameters to maximize Sharpe on a backtest period is over-fitting. A strategy with Sharpe 3.0 in-sample and 0.1 out-of-sample has no edge, just a curve-fit.
- **For Indian swing trading** → use Sortino as primary metric (breakout trades have positive skew), profit factor as secondary, max drawdown as hard filter.

## Sources
- [[sources/Dolzhenko-Algorithmic-Trading-Systems-2024]] (2026-06-15) — profit factor, drawdown types, EV
- [[sources/Wilmott-FAQ-Quantitative-Finance]] (2026-06-16) — Sharpe, Sortino, Treynor, M², Information Ratio; meta-critique of precision and calibration
