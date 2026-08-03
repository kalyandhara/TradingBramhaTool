---
title: "Quantified MA Mean-Reversion Strategy"
category: strategy
tags: [mean-reversion, moving-average, connors-rsi, options, swing]
created: 2026-06-15
updated: 2026-08-02
sources: 1
related: [concepts/ConnorsRSI.md, concepts/EMA.md, concepts/Performance-Metrics.md, concepts/RSI.md, concepts/Mean-Reversion, sources/ForexTester-Mean-Reversion-Guide]
timeframe: swing
---

# Quantified MA Mean-Reversion Strategy

## Core Idea
A **dual-moving-average mean-reversion** system — the opposite philosophy from trend-following MA crossovers. The thesis: when a faster MA pulls significantly *below* a slower MA on a stock that is still in a long-term uptrend (price > MA(200)), the short-term divergence is statistically likely to revert. Entry is via a **limit order below the current close** (buying further weakness), not a breakout. This directly contrasts with trend-following MA usage in [[concepts/EMA]] (buying pullbacks *to* a rising MA, in the direction of the trend).

## Setup Criteria
All of the following must be true before placing an entry order:
1. **Price filter**: Stock price > $5
2. **Liquidity filter**: Average daily volume ≥ 250,000 shares
3. **Volatility filter**: Historical Volatility, HV(100) > 30 (the stock must be volatile enough for mean-reversion edges to exist)
4. **Long-term trend filter**: Close > MA(200) — only take mean-reversion longs in stocks that are still in a primary uptrend
5. **MA divergence trigger**: The Fast MA must be at least **Y% below** the Slow MA, where Y is the "MA Stretch" parameter (tested at 2.5%, 5%, 7.5%, 10%)

### MA Scenarios Tested
| Fast MA | Slow MA |
|---------|---------|
| 5 | 10 |
| 5 | 20 |
| 5 | 50 |
| 10 | 20 |
| 10 | 50 |

### Percent Below Formula
```
Percent Below = (Slow MA - Fast MA) / Slow MA × 100
```
Setup triggers when `Percent Below >= Y%`.

## Entry Rules
- Place a **limit order to buy X% below the prior day's close**, where X is the "Limit %" parameter (tested at 2%, 4%, 6%, 8%, 10%).
```
Limit Price = Prior Close × (1 - X/100)
```
- The order only fills if the stock gaps/trades down further — this means many setup days produce no fill (the strategy waits for the dip rather than chasing).
- Higher X = fewer fills but (per the backtest data) typically a higher average gain per trade, since you're buying a deeper, more stretched dip.

## Exit Rules
Five exit methods were backtested (7a-7e), all assuming a long position:
- **(a) First Up Close** — exit on the first day the stock closes higher than the prior close (fastest, most trades, smallest average gain)
- **(b) ConnorsRSI > 50** — exit when [[concepts/ConnorsRSI]] crosses above 50
- **(c) ConnorsRSI > 70** — exit when ConnorsRSI crosses above 70 (stricter, holds longer for a stronger bounce)
- **(d) Close > MA(3)** — exit when the close moves back above its 3-period moving average
- **(e) Close > MA(5)** — exit when the close moves back above its 5-period moving average (loosest of the MA exits, longest average hold)

**No stop loss is used in this system.** See Contradictions section in [[sources/Connors-MA-Quantified-Approach-2013]] — the book's own backtests found that adding a stop-loss reduced or eliminated the strategy's edge in most configurations.

> [!contradiction] Directly contradicted by [[sources/ForexTester-Mean-Reversion-Guide]] (2026-08-02)
> That source treats stops as mandatory for mean reversion: *"Put the stop beyond the extreme, not at the mean… 1–2 ATR outside the band. If price keeps stretching, you are wrong – exit."* Both describe mean reversion and they disagree on its most consequential rule.
>
> The reconciliation neither source states: **a stopless fade is only survivable when something else bounds the loss.** This system carries three such bounds — a hard `Close > MA(200)` regime filter (it only reverts *inside* a primary uptrend), a limit-order ladder that buys progressively deeper rather than all at once, and holds measured in days. An FX intraday fade has none of them, so an unstopped loss there is unbounded.
>
> Left open rather than resolved, and testable: run one reversion entry rule through [[analyses/Backtest-Harness]] with and without a 2-ATR stop. See [[concepts/Mean-Reversion]] for the general discipline this strategy instantiates.

## Worked Examples (from source)
- **SWHC**: Fast MA (5) dropped >Y% below Slow MA (20) → limit buy X% below prior close filled on a gap-down day → held through a multi-day reversion → exited on ConnorsRSI>50 cross, producing a profitable short hold.
- **SPRD**: Same setup logic on the 10/50 MA scenario with a deeper Limit% (8-10%), illustrating a longer drawdown-before-reversion case before the MA(5) exit triggered.

(Full numeric walk-throughs are in the source PDF; not reproduced here verbatim.)

## Timeframe
Swing — typical holds range from 1-2 days (First Up Close exit) to 5-10+ days (MA(5)/ConnorsRSI>70 exits), per the backtest's "Avg Days Held" statistic.

## Best Market Conditions
- Range-bound or choppy markets within a broader uptrend (Close > MA(200) still satisfied) — gives the fast MA room to oscillate below the slow MA repeatedly.
- High-volatility names (HV(100) > 30) — the strategy's edge is built on volatility-driven overreactions.

## Worst Market Conditions
- Sustained strong downtrends — Close > MA(200) filter should exclude most of these, but a fast bear-market transition can still produce false setups right as the MA(200) filter flips.
- Very low-volatility / low-volume names — filtered out by the HV(100) and average-volume criteria, but if those filters are loosened, edges disappear.

## Backtest / Track Record
- **Data window**: January 2001 - September 2013, US equities.
- **Stats tracked**: Average % P/L per trade ("the edge"), Win Rate, Average Days Held.
- **Top 20 by Average % Gain** and **Top 20 by Win Rate** tables (from source) consistently favored:
  - Larger MA Stretch (Y) values (7.5-10%) — fewer but higher-quality setups
  - Larger Limit % (X) values (6-10%) — deeper dips bought = bigger average reversion
  - ConnorsRSI>70 or Close>MA(5) exits — longer holds, larger average gain per trade, at the cost of fewer trades/year and lower win rate than the First Up Close exit
- **General parameter tradeoffs** (per source Section 4):
  - Stricter **entry** criteria (higher Y, higher X) → fewer trades, higher average gain per trade
  - Stricter **exit** criteria (ConnorsRSI>70, MA(5) vs. First Up Close) → longer average hold, higher average gain per trade, lower win rate
- Up to **125 parameter combinations** (5 MA scenarios x 4 Y values x 5 X values, before multiplying by 5 exit methods) were systematically tested — directly analogous to the coarse-to-fine parameter sweep approach in [[strategies/Systematic-Strategy-Search]].

## Using Options Instead of Stock
The source dedicates a section to substituting a **front-month, in-the-money (ITM) long call** for the underlying stock position:
1. **Instrument**: Buy a call option 1-2 strikes ITM, in the front (nearest) expiration month, instead of buying shares.
2. **Sizing**: 1 option contract per 100 shares the strategy would otherwise buy.
3. **Exit trigger**: Exit the option position on the *same signal* that would exit the stock position (e.g. ConnorsRSI>50) — the option is a stock-substitute, not a separately-managed options trade.
4. **Rationale for ITM (not OTM/ATM)**: ITM calls have a delta close to 1, so they track the stock's price movement almost 1:1 (minimal time-decay drag over a short 1-10 day hold), while requiring less capital than buying 100 shares outright.
5. **Liquidity/spread guidance**: Only substitute options on names with tight bid-ask spreads and adequate open interest — wide spreads can erode the edge on short holds.
6. **Rolling**: If the position is held into the option's final week and not yet exited, roll to the next front-month ITM call rather than holding through expiration risk.

## Related Concepts
- [[concepts/ConnorsRSI]] — primary exit-timing oscillator (exits c and b above)
- [[concepts/EMA]] — contrasting trend-following MA philosophy (buy pullback to rising MA vs. buy stretch below MA)
- [[concepts/Performance-Metrics]] — Average % P/L, Win Rate, Avg Days Held map to this wiki's existing performance-metric definitions
- [[strategies/Systematic-Strategy-Search]] — the 125+ combination parameter sweep mirrors this wiki's general coarse-to-fine optimization framework

## Sources
- [[sources/Connors-MA-Quantified-Approach-2013]]
