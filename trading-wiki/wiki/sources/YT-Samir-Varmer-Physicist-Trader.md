---
title: "YouTube — Samir Varmer: PhD Physicist to 8-Figure Futures Trader (Titans of Tomorrow)"
category: source
tags: [systematic-trading, risk-management, market-microstructure, intraday, futures, opening-range-breakout, kelly, iceberg-orders, leech-on-whale, stop-hunt]
created: 2026-06-18
updated: 2026-06-18
sources: 1
related:
  - concepts/Order-Flow.md
  - concepts/Kelly-Criterion.md
  - strategies/Opening-Range-Breakout.md
  - analyses/Kalyan-Trading-Philosophy.md
  - concepts/Trading-Psychology-Champion.md
---

# YouTube — Samir Varmer: PhD Physicist to 8-Figure Futures Trader

## Metadata
- **Source**: YouTube — Titans of Tomorrow podcast
- **URL**: https://www.youtube.com/watch?v=itRL9v67v9I
- **Guest**: Samir Varmer — PhD particle physicist (U. Texas), ranked #5 US futures trader, systematic fund manager for 30+ years; started October 1993
- **Host**: Titans of Tomorrow (code: toot)
- **Date ingested**: 2026-06-18

## Key Takeaways

1. **Edge + personality congruency** — finding an edge is not enough; it must match your psychological makeup (trend-following vs counter-trend; overnight vs intraday)
2. **Reactive, not predictive** — mature system does not predict markets; it reacts to current conditions and expects them to persist
3. **200-day MA regime filter** — 2/3 of all market returns occur above the long-term trend line; 2/3 of all risk occurs below it; exploit this asymmetry by scaling exposure
4. **Classify risk, don't predict it** — "Is risk high or low?" is all you need; exact 23% vs 28% annualized vol is a false precision; be aggressive when risk is low, out or small when high
5. **Leech on whale / iceberg order mechanics** — stop hunts are not conspiracies; they are VWAP algos slowing buying to improve execution near predictable stop clusters
6. **System stress testing** — add random noise to all inputs; returns should degrade smoothly as noise increases; any humps/spikes in the noise curve = overfitting, not a real edge
7. **Kelly sizing via max acceptable drawdown** — set your position size so that the worst realistic sequence of losses produces a drawdown you can live with (not a formula-derived fraction)
8. **Leptokurtic returns** — stock returns have fat tails; standard deviation may be infinite for individual stocks; do not use SD as the primary risk measure
9. **Good process, bad result > bad process, good result** — always; bad process with lucky outcome corrupts learning and incentivizes repetition of the error
10. **Opening range breakout** — 10–15–20 minute range after open; wait for breakout; trade that direction the rest of the day; statistically sound for equities
11. **Overnight SPY returns > 100%** — more than 100% of S&P 500 long-run return accrues overnight (close-to-open); intraday (open-to-close) is on average negative; hard to exploit at scale but a real, persistent edge
12. **Yield curve inversion anomaly** — Campbell Harvey's recession predictor has not fired cleanly in recent 2-year inversion; Varmer notes this is a current unresolved anomaly in his risk model

## Detailed Notes

### Career Path
- BS Electrical Engineering → PhD Particle Physics (U. Texas) → lost job when Superconducting Super Collider canceled → trader from Oct 1993
- First trade: S&P 500 futures via chaos theory — believed to be first algorithmic S&P futures trader using advanced math
- 2003: shifted from short-term to long-term (>1 year) position size after recognizing short-term alpha decays faster than long-term risk premia
- Non-conformist philosophy: avoids consensus positions; deliberately chose time frames and approaches no one else was pursuing
- Current approach: systematic, risk-focused (not alpha-focused), lean team (2 people), OPM avoided or treated as if own capital

### Edge and Personality Framework
Two questions to diagnose trading style:
1. "If holding overnight, can you sleep?" — No → day trade / scalp
2. "If you've had several losses in a row, do you panic?" — No → can do trend-following (winning 30% of trades with large winners is acceptable)

Counter-trend traders: win 65–70% of trades, but occasional large loss. Trend-followers: win 25–30% but 19:1 win/loss ratio. Neither works for the wrong personality.

### Reactive System Philosophy
- Moved away from all prediction (chaos theory, alpha-generation, breakouts) to reaction
- System reacts to today's data and assumes conditions persist for ~1 year
- Long-term trend line (200-day MA or similar): if price above → 2/3 of returns occur here, 1/3 of risk → be fully invested or levered; if price below → 1/3 of returns, 2/3 of risk → reduce to half position or exit
- This is not prediction; it is regime classification via observable market state

### Risk Classification (Not Prediction)
- Criticizes GARCH, ARIMA, ECHOT and all risk-forecast models: "prefer to be exactly wrong than approximately right"
- Keynes paraphrase: models optimize root-mean-square error, get 95% of scenarios right, but get the 5% that matters (crashes) wrong
- Tiger Woods analogy: don't need to know if he was 2×, 4×, or 8× better than Mickelson — "he was just a hell of a lot better; be scared when risk is high, aggressive when it's low"
- Yield curve as risk indicator: Campbell Harvey's inversion → recession → S&P decline is well-documented but ambiguous in recent cycles (COVID + tariff collapses may have masked or consumed the signal)
- SAC (serial autocorrelation) identifies trend vs. mean-reversion regimes — consistent with wiki [[concepts/Performance-Metrics]]

### Pod Shop Drawdown Limits (Paper in Journal of Portfolio Management)
- Standard pod-shop rule: if PM hits 7–10% drawdown → terminate
- Varmer shows this is **statistically stupid**: took ETF pairs with known profitable windows (perfect hindsight), imposed drawdown cutoffs, and turned certain profits into losses more often than not
- Why: drawdowns must be explained (bad luck? bad process? external shock?); tariff crash PM → was that bad management? Obviously not
- The correct response to a drawdown is to **understand its cause**, not trigger a fixed threshold
- Implication: retail traders applying hard daily loss limits mechanically may be doing the same statistical error

### Kelly Sizing (Varmer's Approach)
Varmer does not use the Kelly formula directly. His method:
1. Identify worst realistic sequence of losing trades
2. Estimate the drawdown that sequence produces at current position size
3. Ask: "Can I live with this drawdown?" (Long-only market: 55% historically)
4. Scale position size so that worst-case drawdown matches your tolerance
5. Below the long-term line: cut position to ~half (because 2/3 of risk is below the line)

Full Kelly produces 95% drawdowns → unusable; but Kelly-based reasoning for sizing is sound.

### Leptokurtic Distributions
- Stock returns are leptokurtic (fat tails, thin peak) relative to Gaussian
- Extreme events happen more often than normal distribution predicts; small events happen less
- Practical consequence: standard deviation understates tail risk; may be formally **infinite** for individual stocks (Tesla short example)
- Do not optimize for standard deviation; use drawdown tolerance instead

### System Stress Testing
Three stress tests Varmer applies before trusting a system:
1. **Noise injection**: add random noise (scaled up gradually) to all inputs; plot returns vs noise level; expect smooth monotonic decay — any non-monotone region = overfitting
2. **Break the worst way you can think of**: pick the nastiest historical period and run through it
3. **Examine moving average cross optimization**: if you optimize MA crossover lengths and find one "optimal" pair, it's almost certainly curve-fit; the noise test will expose this
- Moving average crossover example: picking "optimal" pair is almost always overfitting; noise test would show degradation is not smooth

### Iceberg Orders and Stop Hunt Mechanics (Core Insight)
The signature: price sweeps a predictable level (demand zone, round number, prior low), triggers stops, then moves in the pre-predicted direction.

**This is NOT a conspiracy.** Mechanism:
1. Institution has a large multi-day buy order (e.g., 1 million IBM shares)
2. Uses a VWAP or smart algo to execute over hours
3. The algo has "trader logic" — it knows stops are concentrated near predictable levels (round numbers, swing lows, support lines)
4. When price approaches such a level, the algo **slows its buying** → without buying support, price naturally drifts down → triggers stops below the level → price briefly falls further → algo then **accelerates buying** at the cheaper price → price rebounds

The retail trader isn't being hunted; they are predicting the same location the VWAP algo is also targeting for better fill.

Varmer and Joe Richie built this explicitly: "trader logic" subroutines in the VWAP algo that slow/speed execution based on recognized support/resistance patterns.

Why double-taps are increasing: more sophisticated algo versions will test a level twice before committing capital.

### Liquidity at an Instant
"Liquidity exists over periods of time. At any instant in time it doesn't really exist." — Olsen Associates: "camel going through the eye of a needle"
- Even small retail stop orders can move price at the exact instant of triggering because the order book is thin at that moment
- This is why stop clusters matter even if retail is small

### Order Placement Tactics
- **Never use round numbers** for orders — algos target round numbers; stops at 100.00 are obvious
- **Never use numbers ending in 0 or 5** — same reason
- **Use prime numbers or strange non-round numbers** — 96 shares, 221, 131 etc. — this disguises you as non-institutional
- Institutional orders come in round lots, at regular intervals, over hours → if your order looks institutional, other algos will "get in front of you" (front-run)
- Protected low after sweep: statistically a good stop location (not obvious to algos, below where they've already cleared stops)

### Leech on Whale Strategy
What Kalyan is doing with his sweep-and-reverse scalp:
- Correctly identifying an iceberg whale order being executed
- The sweep + confirmation = the algo just cleared its cheap entry zone
- Kalyan is the "leech on the shark" — riding in the direction of the whale for the session
- Valid losses = "the iceberg wasn't there; something else looked like the iceberg but wasn't"
- Varmer explicitly confirms this is valid and why it works

### Gross Misconceptions About Hedge Funds
- Institutional funds hire same people from same schools with same strategies → systemic group-think
- Soros/Steinhart era: risk own money, concentrated bets, genuine edge → modern era: mostly fee collection vehicles
- Warren Buffett bet: S&P 500 vs any group of hedge funds over 10 years → S&P won by large margin
- "You as a retail investor are way better off just buying the SPY and sitting at home" than investing in hedge funds

### Grossman-Stiglitz Paradox
If markets were perfectly efficient, no one would trade → no price discovery → inefficiency would emerge → people would trade again → equilibrium at "just enough inefficiency to reward the research to find it." Markets are neither fully random nor fully predictable; they settle at a level where the edge exactly compensates the effort of finding it.

### AI in Trading
- Need direction before AI is useful; AI cannot generate hypotheses from scratch about trading
- Need market experience to judge whether AI's answers make sense
- Only two paths to trading knowledge: (1) read many books with skeptical eye; (2) lose real money in the market

## Actionable Insights

1. **Opening range breakout** → create strategy page [[strategies/Opening-Range-Breakout]]; this is what Kalyan's intraday approach most resembles
2. **Protected low as stop location** → confirmed statistically better than obvious round-number stop
3. **Never place orders at round numbers** → apply immediately to stop placement and entry orders
4. **Regime filter via 200-day MA** → scale full position above line, half position below line; this is a simple improvement to any existing long-biased system
5. **Noise injection stress test** → apply to any systematic screener or strategy being developed (VCPBot, PMax-Confluence)
6. **Drawdown-tolerance-based sizing** → more intuitive than Kelly formula: "size so worst-case feels painful but survivable"
7. **Double-tap sweeps increasing** → accept these as normal algo behavior; widen stop slightly below the double-tap low, not just the first tap low

## Contradictions with Existing Wiki

- **No direct contradictions.** The leech-on-whale framework validates Kalyan's existing scalp approach with a clear mechanism.
- Varmer agrees with Minervini/prop-trading: process over outcome, hard rules, no discretion at trade time
- **Mild tension**: Varmer says large fund drawdown limits are statistically stupid → wiki's 3-strikes rule (from Prop Trading Secrets) is a daily behavioral limit, not a drawdown cutoff; they serve different functions. The 3-strikes rule is about protecting psychology, not a risk model. Both can coexist.

## Pages Updated
- [[concepts/Order-Flow]] — added iceberg mechanics, VWAP algo trader logic, double-tap explanation
- [[concepts/Kelly-Criterion]] — added Varmer's drawdown-tolerance sizing approach
- [[strategies/Opening-Range-Breakout]] — new page created
- [[analyses/Kalyan-Trading-Philosophy]] — added Varmer validation of sweep-reverse scalp + tactical improvements
