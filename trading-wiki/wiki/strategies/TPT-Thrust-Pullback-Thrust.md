---
title: "TPT — Thrust-Pullback-Thrust Resumption"
category: strategy
tags: [tpt, resumption, trend-following, rob-hoffman, scalping, day-trading, futures, pullback]
created: 2026-06-17
updated: 2026-06-17
timeframe: intraday
sources: 1
related:
  - concepts/EMA.md
  - concepts/Order-Flow.md
  - concepts/Initial-Balance.md
  - concepts/Elliott-Wave.md
  - sources/Prop-Trading-Secrets-Lien-Crete-2025.md
---

# TPT — Thrust-Pullback-Thrust Resumption

## Core Idea

Wait for the market to make a strong directional move (Thrust 1), let price pull back in an orderly fashion, then enter as the original direction resumes (Thrust 2). The entry captures the second leg of the move at a lower-risk, higher-conviction point than entering on the initial thrust.

Developed/popularized by **Rob Hoffman** (30+ year futures trader, member of multiple prop trading firms). The pattern is universal — applicable to any instrument and timeframe.

## Setup Criteria

1. **Thrust 1 (impulse move)**: Strong directional candle(s); large bar range; above-average volume; closes at or near the extreme with minimal rejection wick
2. **Pullback**: Price retraces partially (does not fully reverse Thrust 1); lower volume than the thrust; range contracts; does NOT breach the structural high/low that triggered the thrust move
3. **Resumption setup forming**: Price shows signs of resuming original direction — higher low forming (for longs) or lower high forming (for shorts)
4. **HTF context**: Thrust 1 must align with the larger trend; do not take TPT against the HTF trend

## Entry Rules

- **Long entry**: Pullback forms a higher low → price breaks above pullback high → enter on the breakout candle or the next candle close above
- **Short entry**: Pullback forms a lower high → price breaks below pullback low → enter on the breakout candle or the next candle close below
- **Timing requirement**: Entry must occur before price reaches the prior Thrust 1 extreme; if price is already near the extreme, the setup has passed

## Exit Rules

**Profit target:**
- Measure the height (range) of Thrust 1
- Project the same distance from the entry point = minimum Thrust 2 target
- Alternatively: next major S/R level on HTF chart if closer
- Advanced: use Elliott Wave — if Thrust 1 = Wave 1, Pullback = Wave 2, Thrust 2 = Wave 3 (target: 1.618× Thrust 1)

**Stop loss:**
- Long: below the pullback low (last swing low before entry)
- Short: above the pullback high
- If stop distance > 2× ATR, setup quality is marginal — skip or size down

**Trailing stop (optional for runners):**
- Once in profit by 1R, move stop to breakeven
- Trail stop to each subsequent higher low (longs) as Thrust 2 develops
- Take partial off at 1R; let remainder run with trailing stop

## Timeframe

- **Primary**: 5-minute (intraday scalping on NQ, ES, YM, CL, GC, EUR/USD)
- **Secondary confirmation**: 15-minute or 30-minute for HTF trend direction
- **Works on**: Any timeframe from 1-minute (scalping) to daily (position swing)
- **Best session**: 9:45 a.m.–12:00 p.m. EST for futures; first half of London session for forex

## Best Market Conditions

- Trending day with clear directional bias established at or after the open
- Moderate volatility (ATR not at multi-year extremes)
- Thrust 1 occurs after a significant catalyst (news, level break, IB breakout)
- Low to moderate spread (avoid pre-news periods)

## Worst Market Conditions

- Choppy, range-bound sessions (no clear Thrust 1 to identify)
- High-impact news immediately before planned entry (slippage risk)
- End-of-day low-volume drift (manufactured "thrusts" that don't follow through)
- Overextended trend (5th+ impulse wave; Thrust 2 setup after very extended move has lower probability)

## Relationship to IB Breakout-Retest

The Initial Balance breakout-retest is a named version of TPT in the futures morning session:
- IB breakout = **Thrust 1**
- Pullback to IB level = **Pullback** (retest)
- Bounce from IB level = **Thrust 2 entry**

This is why TPT and IB strategies are cross-listed.

## Elliott Wave Connection

| EW Label | TPT Label | Interpretation |
|---------|-----------|---------------|
| Wave 1 or 3 impulse | Thrust 1 | Strong directional move |
| Wave 2 or 4 correction | Pullback | Orderly retracement |
| Wave 3 or 5 continuation | Thrust 2 | Entry point; target = W3 extension or W5 target |

McDowell's OWL histogram (EMA5–EMA35 on lows) identifies whether a thrust has occurred on the right wave count.

## Backtest / Track Record

- Rob Hoffman: 30+ years as a futures trader using this framework as a core strategy
- No formal published backtest statistics in the source book
- Conceptual support: multiple traders in the book independently describe TPT-equivalent entries (Vince Koehn's pullback to Fibonacci confluence; Nick Syiek's pullback to market structure in direction of fundamental bias)

## Related Concepts

- [EMA](../concepts/EMA.md) — 21 EMA as dynamic Thrust 2 entry support
- [Order Flow](../concepts/Order-Flow.md) — delta confirmation at pullback lows
- [Initial Balance](../concepts/Initial-Balance.md) — IB breakout-retest is a TPT pattern applied to the morning session
- [Elliott Wave](../concepts/Elliott-Wave.md) — EW framework provides Thrust 2 targets; Wave 3 and Wave 5 = Thrust candidates

## Sources

1. [Prop-Trading-Secrets-Lien-Crete-2025](../sources/Prop-Trading-Secrets-Lien-Crete-2025.md) — Ch3 (Rob Hoffman)
