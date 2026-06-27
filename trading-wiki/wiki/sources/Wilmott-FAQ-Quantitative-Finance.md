---
title: "Book — Frequently Asked Questions in Quantitative Finance (2nd ed.)"
category: source
tags: [quant-finance, options, derivatives, kelly-criterion, performance-metrics, dispersion-trading, risk-management, hedging, portfolio-theory]
created: 2026-06-16
updated: 2026-06-16
sources: 1
related:
  - concepts/Kelly-Criterion.md
  - concepts/Performance-Metrics.md
  - strategies/Dispersion-Trading.md
  - concepts/Capital-Management-Methods.md
  - analyses/Kalyan-Trading-Philosophy.md
---

# [Book] — Frequently Asked Questions in Quantitative Finance (2nd ed.)

## Metadata
- **Author**: Paul Wilmott (with Emanuel Derman for Chapter 3)
- **Publisher**: Wiley, 2009
- **Pages**: 625 (includes timeline, 58 FAQs, manifesto, essays, 12 mistakes, formulas, contracts, brain teasers)
- **File**: `C:\Users\dhara\Downloads\Paul Wilmott - Frequently asked questions in quantitative finance...pdf`
- **Scope**: Derivatives, options pricing, risk management, performance measurement, quant philosophy — written for practitioners, not just theorists

## Key Takeaways

1. **Kelly Criterion** — optimal fraction to bet/invest = μ/σ² (continuous) or 2p−1 (binary coin). Use **half-Kelly** in practice because mean and σ are never known precisely. No single trade should be allowed to make or break you.

2. **Performance Hierarchy**: Sharpe ratio (excess return / total volatility) is the foundation. Sortino (uses downside semi-variance, better for skewed returns) is more honest. Treynor (excess return / β) matters for non-diversified positions. Information ratio tracks value vs benchmark.

3. **Dynamic Hedging P&L**: Hedge using actual volatility → guaranteed locked-in profit but random daily P&L. Hedge using implied volatility → smooth monotonically increasing P&L, but final profit is path-dependent. Long gamma loses money ~68% of the time (chi-square distribution); short gamma loses only 32% of the time but those losses are huge.

4. **Dispersion Trading** — short index options + long basket of individual stock options = bet that implied index correlation is too high vs actual correlation. Works when stocks move in different directions; hurts badly when market crashes (correlation → 1).

5. **Serial Autocorrelation (SAC)** — positive SAC = trend-following regime; negative SAC = mean-reversion regime. DJIA shifted to deeply negative SAC by 2009 (previously strongly positive in 1970s). SAC matters in discrete hedging but vanishes under continuous hedging.

6. **Supply and Demand Dominates** — option prices reflect supply/demand, fear/greed, and all market imperfections, not just the mathematical replication cost. Calibration extracts a "scalar" from a vector of effects; implied volatility is not the actual expected volatility.

7. **12 Commonest Mistakes** (Chapter 5): See Detailed Notes below. The meta-lesson: models should be simple, clear, and robust — not complex, calibrated, and fragile.

8. **Modellers' Manifesto** (Wilmott & Derman, 2009): "There are no fundamental laws in finance." Models are tools, not the world. Idolatry of mathematical elegance is the greatest danger. The Hippocratic Oath for quants: never sacrifice reality for elegance without saying why.

## Detailed Notes

### Kelly Criterion (FAQ #15)
- Binary case: Kelly fraction `f = 2p − 1` where p = probability of winning
- Continuous case: `f = μ / σ²` (Sharpe ratio numerator / denominator)
- Betting more than Kelly reduces expected growth (moves to right of maximum in the growth-rate-vs-fraction curve; growth eventually goes negative)
- **Half-Kelly**: most practitioners use f/2 because μ and σ are estimated with error; reduces variance dramatically at the cost of ~25% expected growth
- Reference: Kelly (1956), Poundstone (2005) *Fortune's Formula*

### Performance Measures (FAQ #19)
| Measure | Formula | Best Use |
|---------|---------|---------|
| Sharpe | (μ − r) / σ | Universal baseline; penalizes all volatility equally |
| M² (Modigliani) | r + v × Sharpe | Sharpe in return terms, benchmark volatility as scale |
| Sortino | (μ − r) / σ_downside | Skewed returns; ignores upside "risk" |
| Treynor | (μ − r) / β | Individual stocks / non-diversified portfolios |
| Information | (μ − r_benchmark) / tracking_error | Manager skill vs benchmark |

### Dynamic Hedging (FAQ #41)
- **Hedge at actual σ**: P&L is random each day but total profit at expiry is guaranteed = BS(actual σ) − BS(implied σ). Requires accurate σ forecast.
- **Hedge at implied σ**: daily P&L = ½(σ²−σ̃²)S²Γ·dt > 0 each step as long as actual > implied. Total is path-dependent (concentrated near strike = big profit; far ITM/OTM = small).
- **Hedging error** from discrete rebalancing = ½σ²S²Γ·δt·(φ²−1): proportional to δt (large!), averages to zero but is chi-square distributed.
- **Transaction costs** ∝ 1/√δt: halving rehedging error requires 4× more hedges, doubling costs. An optimal rehedging schedule exists (see Whalley & Wilmott papers).

### Dispersion Trading (FAQ #43)
See [Dispersion-Trading strategy page](../strategies/Dispersion-Trading.md).

### Serial Autocorrelation (FAQ #42)
- Positive SAC: stock up today → likely up tomorrow. Like trend-following in the noise term.
- Negative SAC: stock up today → likely down tomorrow. Like mean-reversion in the noise term.
- SAC with lag=1 for DJIA: strongly positive ~1970s, shifted progressively to strongly negative by 2009.
- With negative SAC: if long gamma → trade to capture extremes (buy after down days, sell after up days). If short gamma → you can wait (stock returns to current level), but nerves of steel required.
- SAC does NOT affect continuous-hedging results (only matters for discrete hedging).

### 12 Commonest Mistakes in Quant Finance (Chapter 5)
1. **Lack of Diversification** — compensation systems incentivize herding (copy what makes bonus, not what is correct). "No single trade should make or break you." Game theory: if everyone else copies, copying is individually rational even if bad systemically.
2. **Supply and Demand ignored** — market prices are vectors of influences compressed to a scalar; you cannot back out true volatility from an option price any more than cost-of-production from a retail price. Supply/demand, fear/greed dominate in practice.
3. **Jensen's Inequality Arbitrage** — for convex payoffs E[f(x)] ≥ f(E[x]); the excess ≈ ½f''(E[S])·Var(S). Any non-linearity in a random variable must be correctly priced; ignoring convexity means leaving money on the table.
4. **Sensitivity to Parameters** — stress-testing by varying a constant volatility is wrong if volatility actually varies. True worst/best case: price with σ_low when Γ>0, σ_high when Γ<0 (Uncertain Volatility Model). "Bastard greeks" (vega) are misleading when gamma changes sign.
5. **Correlation** — correlation measures infinitesimal-timescale co-movement, not directional similarity over investment horizons. Two perfectly correlated assets can move in opposite directions. Correlation breaks down in crises exactly when you need it.
6. **Reliance on Continuous Hedging** — hedging error is O(δt), same order as all other Black-Scholes terms. In practice discrete hedging error is large and chi-square distributed. Long gamma loses 68% of days; short gamma loses only 32% but the losses are large.
7. **Feedback** — large traders' actions change the market they are modelling. Delta hedging a large position creates feedback: buying when price rises, selling when it falls → amplifies volatility. Portfolio insurance (1987 crash) is the canonical example.
8. **Reliance on Closed-Form Solutions** — closed forms exist only for simple models; practitioners often torture models to get closed forms rather than use better models with numerical solutions. Finite-difference methods are usually superior to Monte Carlo for path-dependent structures.
9. **Valuation is Not Linear** — you cannot add up option values if γ changes sign across the portfolio. Long and short positions interact non-linearly.
10. **Calibration** — fitting a model to market prices and then using that model to price other contracts is circular and dangerous. "The model fits historical options well" does not mean it will price new options correctly; it may simply be over-parameterized.
11. **Too Much Precision** — quoting a model price to 5 decimal places when the underlying assumptions have 10–20% uncertainty is false precision. Models should be used for direction and order-of-magnitude, not as authoritative prices.
12. **Too Much Complexity** — complexity hides risk rather than reducing it. Simple robust models whose assumptions are transparent are better than complex ones that are calibrated to fit. Complexity is often used to justify large bonuses without improving actual risk management.

### Financial Modellers' Manifesto (Chapter 3 — Derman & Wilmott)
> "There are no fundamental laws in finance. And even if there were, there is no way to run repeatable experiments to verify them."

**Hippocratic Oath for Quants:**
- I will remember that I didn't make the world, and it doesn't satisfy my equations
- I will use models boldly to estimate value, but not be overly impressed by mathematics
- I will never sacrifice reality for elegance without explaining why
- I will make explicit my assumptions and oversights (not give false comfort about accuracy)
- I understand that my work may have enormous effects on society beyond my comprehension

## Actionable Insights for Kalyan's Trading

1. **Position Sizing → Apply Kelly**: f = μ/σ² or use half-Kelly. This is the quantitative foundation for Minervini's 1.25–2.5% risk rule — a rule derived from Kelly with extreme conservatism built in.
2. **Use Sortino not Sharpe** when evaluating strategies with asymmetric returns (growth-stock breakouts have positive skew; downside semi-variance is the better denominator).
3. **Discrete hedging analogy**: Minervini's trailing stop management is analogous to discrete rehedging — the right rebalance frequency depends on ATR (vol) and transaction cost tolerance. Don't over-manage stops.
4. **SAC indicator**: Monitor NIFTY 1-day lagged autocorrelation over 252-day window. Positive SAC = trend-follow harder; negative SAC = tighten mean-reversion exits.
5. **Don't calibrate to fit** — the Chartink screener + Minervini TT is a qualitative filter, not a precisely calibrated model. Do not try to "fit" screener parameters to historical results; that's overfitting.

## Contradictions with Existing Wiki
| Topic | Wilmott | Existing Wiki | Resolution |
|-------|---------|--------------|------------|
| Stop-losses | No direct contradiction; long gamma = lose 68% of days but profit long-run — patience required | Minervini: hard stops mandatory; Connors: stops remove edge | Wilmott is in options theory; doesn't directly apply to stock stop-loss debate. But chi-square insight (68% losing days with long gamma) intellectually supports why Connors' mean-reversion no-stop works short-term |
| Diversification | OPM structures actively disincentivize diversification; don't try to be different if it could cost you the job | Kalyan: max 10% single stock | Consistent — Kalyan's hard limit IS the diversification rule; Wilmott explains *why* the system fights it |
| Model complexity | Simpler is better; complexity hides risk | Dolzhenko: genetic algorithms, multi-factor optimization | Tension: Dolzhenko advocates systematic optimization; Wilmott warns against over-fitting / too much precision. Resolution: use Dolzhenko's framework but set a small number of parameters, test robustness over wide parameter ranges, not just the best-fit point |

## Pages Updated
- Created: `concepts/Kelly-Criterion.md`
- Created: `strategies/Dispersion-Trading.md`
- Updated: `concepts/Performance-Metrics.md` (Sortino, Treynor, Information Ratio detail; Wilmott critiques)
- Updated: `wiki/index.md` (pages +3, sources +1)
- Updated: `wiki/log.md`
