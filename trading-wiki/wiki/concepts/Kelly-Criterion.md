---
title: "Kelly Criterion"
category: concept
tags: [position-sizing, money-management, risk-management, kelly, portfolio]
created: 2026-06-16
updated: 2026-06-16
sources: 1
related:
  - concepts/Capital-Management-Methods.md
  - concepts/Performance-Metrics.md
  - strategies/Minervini-SEPA.md
  - analyses/Kalyan-Trading-Philosophy.md
  - sources/Wilmott-FAQ-Quantitative-Finance.md
---

# Kelly Criterion

## Definition

The Kelly Criterion is a money-management rule that specifies the optimal fraction of wealth to invest in a bet or position to **maximize the long-run expected growth of wealth**. It was derived by J.L. Kelly Jr. in 1956 from information theory. Too little → you leave growth on the table. Too much → volatility of returns rises and eventually expected growth goes negative — you blow up.

> "No single trade should be allowed to make or break you." — Wilmott

## How to Use

### Binary Bet (coin-flip analogy)
If the probability of winning is `p` and the bet pays even money:

```
f* = 2p − 1
```

Example: p = 0.55 → f* = 0.10 → bet 10% of wealth per flip.

### Continuous Investment (stocks / strategies)
If the investment has expected return `μ` and standard deviation `σ`:

```
f* = μ / σ²
```

This is the **Sharpe ratio's numerator over its denominator** — the higher the edge (μ) and the lower the risk (σ²), the more you should size.

### Half-Kelly (Practical Default)
In practice, `μ` and `σ` are estimated with error. Wilmott recommends **half-Kelly**:

```
f_practical = f* / 2
```

Half-Kelly captures ~75% of the long-run expected growth of full Kelly at dramatically reduced variance. Most professional traders use Kelly fractions between 0.25× and 0.5× full Kelly.

### Growth-Rate Curve
The expected growth rate is a concave function of betting fraction. It rises to a maximum at `f*` and then falls, eventually going negative. Key observations:
- **Betting fraction < f***: "conservative" — leaves growth behind but is safe
- **Betting fraction = f***: maximum long-run growth
- **Betting fraction > f***: more volatility AND lower expected growth — strictly worse in the long run
- **Betting fraction = 2×f***: expected growth = 0 (ruin in long run)

## Variants / Parameters

| Variant | Formula | When to Use |
|---------|---------|-------------|
| Full Kelly | f* = μ/σ² | Theoretical optimum; requires precise μ and σ |
| Half Kelly | f*/2 | Practical default; tolerates estimation error |
| Quarter Kelly | f*/4 | Very conservative; multiple positions simultaneously |
| Fractional Kelly | f* × fraction | Adjust based on confidence in μ/σ estimates |

### Multi-Position Kelly
With N simultaneous uncorrelated bets, total Kelly allocation across all positions remains f*. Each individual position gets f*/N. With correlated positions, the math is more complex but the principle is the same — total portfolio exposure should not exceed the Kelly fraction of your edge.

## Relationship to Minervini's Position Sizing

Minervini's 1.25–2.5% equity risk per trade maps to Kelly as follows:
- With typical swing-trade win rate ~45–55% and avg win / avg loss ~2.5:
  - EV per dollar risked ≈ 0.5×2.5 − 0.5×1 = 0.75 (75% edge per dollar)
  - Kelly would suggest a higher fraction, but Minervini uses extreme conservatism (10% max stop, 1.25–2.5% of equity risk) → approximately **0.1–0.2× Kelly**
- This conservatism is correct: (1) win rates and avg win/loss are estimated, not known; (2) multiple simultaneous open positions add correlation; (3) tail risk in individual stocks is fat

## Common Mistakes

1. **Using full Kelly** — almost always wrong in practice. Estimation error in μ alone can flip optimal Kelly from meaningful to destructive. Half-Kelly is the minimum conservatism.
2. **Ignoring correlation** — if all positions move together, they are effectively one bet. The correct Kelly total is f* for the *portfolio*, not f* per stock.
3. **Using Kelly as a strategy selector** — Kelly tells you *how much* to bet given an edge; it does not tell you *whether* you have an edge. You must independently verify the edge exists before sizing.
4. **Applying Kelly to very few samples** — Kelly requires a large number of bets to dominate. For small samples, Kelly can lead to ruin before the long-run average kicks in.
5. **Confusing Kelly with optimal single-trade sizing** — Kelly maximizes multi-period geometric growth; for a single trade, expected value maximization would have you go all-in if EV is positive. Kelly is not for single trades.

## Related Concepts

- [[concepts/Capital-Management-Methods]] — Kelly alongside Optimal f, Fixed Proportional, Martingale/Anti-Martingale
- [[concepts/Performance-Metrics]] — μ and σ² inputs to Kelly come from performance measurement
- [[strategies/Minervini-SEPA]] — Minervini's 1.25–2.5% risk rule ≈ 0.1–0.2× Kelly in practice
- [[analyses/Kalyan-Trading-Philosophy]] — personal single-stock limit of 10% is consistent with sub-Kelly sizing

## Examples in This Wiki

- Minervini's position sizing (1.25–2.5% equity at risk, max position 20–25%) is a Kelly-conservative approach tuned for concentrated growth stock portfolios with uncertain edge
- The 50/80 Rule (never average down into a losing leader) is the Kelly equivalent of recognizing that f*=0 when you have no positive edge in a declining stock

## Varmer's Drawdown-Tolerance Sizing (Practical Alternative)

Samir Varmer (systematic futures trader, 30+ years) does not use the Kelly formula directly. His sizing method:

1. Model the **worst realistic sequence** of losses for your system
2. Calculate what drawdown that sequence produces at current position size
3. Ask: "Can I live with this drawdown?" For long-only equity exposure: 55% historically. For a trading system: pick your personal pain threshold.
4. **Scale position size** so the worst-case produces a drawdown you can endure, not one that forces you to quit
5. **Below the 200-day MA**: the market delivers 2/3 of its risk and only 1/3 of its return below the trend line → cut position to ~half to keep expected drawdown constant

This is Kelly intuition without the formula: you're implicitly setting f to match your utility function (drawdown tolerance), not the mathematical optimum.

**Regime scaling** (Varmer):
- Above 200-day MA: full position (or levered)
- Below 200-day MA: ~half position
- This keeps portfolio expected drawdown roughly constant despite the different risk/return asymmetry

**On leptokurtic returns** (Varmer):
- Stock returns have fat tails; individual stocks may have theoretically **infinite** standard deviation
- Do not use SD as the primary size input → use drawdown tolerance as the constraint instead
- Kelly's σ² term becomes unreliable when the distribution is not Gaussian

## Sources

1. [Wilmott-FAQ-Quantitative-Finance](../sources/Wilmott-FAQ-Quantitative-Finance.md) — FAQ #15, pp. 74–76; Kelly derivation, continuous approximation, half-Kelly recommendation
2. [YT-Samir-Varmer-Physicist-Trader](../sources/YT-Samir-Varmer-Physicist-Trader.md) — Drawdown-tolerance sizing; 200-day MA regime scaling; leptokurtic returns and infinite SD problem
   - Reference: Kelly, JL 1956. *A new interpretation of information rate.* Bell Systems Technical Journal 35, 917–926
   - Reference: Poundstone, W 2005. *Fortune's Formula.* Hill & Wang
