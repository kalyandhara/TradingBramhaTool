---
title: "Dispersion Trading"
category: strategy
tags: [options, derivatives, correlation, index, volatility, quant]
timeframe: position
created: 2026-06-16
updated: 2026-06-16
sources: 1
related:
  - concepts/Performance-Metrics.md
  - concepts/Capital-Management-Methods.md
  - sources/Wilmott-FAQ-Quantitative-Finance.md
---

# Dispersion Trading

## Core Idea

Dispersion trading is an **options strategy** that sells index options and buys a basket of individual stock options. The bet is that the market's implied correlation across index constituents is **too high** relative to what will actually materialize. When stocks move in different directions (dispersing), individual stock options pay off while the index option expires cheaply. When stocks move together (crash mode), the short index options hurt.

> Short index volatility + Long individual stock volatility = short implied correlation.

## Setup Criteria

1. **Index implied volatility** is elevated relative to historical realized correlation of constituents
2. **Individual stock implied volatilities** are relatively cheap (≤ index vol when weighted)
3. Implied correlation (backed out from index IV vs constituent IV) is high compared to your forecast
4. Market is in a **normal / low-correlation regime** (not crisis, not strong trending)

### Implied Correlation Formula
```
σ_I² ≈ ΣΣ w_i × w_j × ρ_ij × σ_i × σ_j

Implied correlation ≈ (σ_I² − Σ w_i² σ_i²) / (Σ_cross w_i w_j σ_i σ_j)
```
If market-implied correlation >> your forecast → sell index options, buy stock options.

## Entry Rules

- Sell **straddles or strangles** on the index (Nifty 50, Bank Nifty, or S&P 500)
- Buy **straddles or strangles** on a basket of individual index constituents
- Weight individual positions by value weight in the index OR by cheapness of individual options
- Choose constituents with high dispersion likelihood: **competing companies, different sectors, merger candidates, stocks that diverge in stress**
- Delta hedge each leg to isolate the volatility/correlation bet

## Exit Rules

- Close when the correlation trade has played out (individual stocks have moved, index has not)
- Close before earnings on any individual constituent (earnings creates binary jump risk not captured by the model)
- Stop: if implied correlation falls (index vol drops, individual vol stays) the trade is working; if index vol spikes (crash), the short index leg is losing — exit promptly

## Timeframe
- Position / multi-week. Options are typically monthly expirations.

## Why It Can Work

- **Index options command a premium** because fund managers buy puts on the index for downside protection (supply/demand drives index IV above fair value)
- **Stock options are cheaper** per unit of move because dispersion is harder to hedge
- During normal markets, correlation is meaningfully below 1; during crises it approaches 1

## Why It Can Fail

- **Crash / black swan**: all stocks fall together → correlation → 1 → index vol explodes → short index options produce catastrophic losses while long stock options only partially offset
- **Bid-offer spreads**: requires many contracts; transaction costs can swamp the theoretical edge
- **Delta hedging costs**: each individual leg must be delta-hedged continuously — expensive
- **Timing**: selling index options in low-vol environments = selling cheap premium; the setup only works when index IV is genuinely elevated

## Best Market Conditions
- Normal range-bound or mildly trending market with sector rotation
- Individual stocks with high idiosyncratic risk (company-specific news flows)
- Low macro correlation (economic data doesn't dominate every stock)

## Worst Market Conditions
- Risk-off, panic selling, or macro regime shifts where all stocks correlate
- VIX spike > 30% (index vol rises faster than individual vols → you lose on net)

## Indian Market Applicability

India: Dispersion trading on Nifty 50 / Bank Nifty options is feasible via NSE F&O. Considerations:
- Bank Nifty has 12 constituents with very high pairwise correlation (most are just "banking") → dispersion payoff is limited; prefer Nifty 50
- Sector rotation in India tends to be fast and policy-driven (RBI, budget) — watch for macro-driven correlation spikes
- Weekly Nifty options allow shorter-duration dispersion plays

## Backtest / Track Record
- Wilmott (2009): "Dispersion trading can be interpreted as a view on implied correlation versus one's own forecast." No specific backtest cited.
- Academic reference: Grace, D & Van der Klink, R (2005), *Dispersion Trading Project*, EPFL

## Related Concepts
- [[concepts/Performance-Metrics]] — Sharpe/Sortino to evaluate if the edge survives transaction costs
- [[concepts/Capital-Management-Methods]] — Kelly sizing of the correlation bet

## Sources
1. [Wilmott-FAQ-Quantitative-Finance](../sources/Wilmott-FAQ-Quantitative-Finance.md) — FAQ #43, pp. 188–190; full derivation of implied correlation formula and trade mechanics
