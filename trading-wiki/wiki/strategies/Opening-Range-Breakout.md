---
title: "Opening Range Breakout (ORB)"
category: strategy
tags: [intraday, scalp, opening-range, breakout, futures, equities, trend-following]
created: 2026-06-18
updated: 2026-06-18
sources: 1
related:
  - concepts/Initial-Balance.md
  - concepts/Order-Flow.md
  - strategies/Prop-Scalp-NQ-Initial-Balance.md
  - analyses/Kalyan-Trading-Philosophy.md
  - sources/YT-Samir-Varmer-Physicist-Trader.md
---

# Opening Range Breakout (ORB)

## Core Idea

The first 10–20 minutes of trading establish a range of price discovery (the opening range). Once price breaks out of this range in either direction, institutional order flow tends to carry it further in that direction for the rest of the session.

Varmer and Joe Richie traded this systematically for equities for years. It is one of the few statistically documented intraday edges in equity markets.

## Setup Criteria

1. Identify the high and low of the opening range — typically the first **10, 15, or 20 minutes** of the regular session
2. Wait for a clear breakout: price closes a bar **above the opening range high** (long signal) or **below the opening range low** (short signal)
3. Optionally: confirm with a retest of the broken range level (aligns with Initial Balance breakout-retest from [[concepts/Initial-Balance]])

## Entry Rules

- **Long**: enter on breakout above opening range high, or on first retest of opening range high from above
- **Short**: enter on breakout below opening range low, or on retest of opening range low from below
- Entry can be limit (at the retest) or market/stop (on the break)

## Exit Rules

- **Profit target**: session high or low (opposite end of expected range expansion), or a fixed multiple of the opening range (e.g., 1× or 2× range extension above/below)
- **Stop loss**: below the opening range for longs (below the swept low is preferred per Varmer); above the opening range for shorts
- Do NOT use round numbers for stop placement; use non-round levels (e.g., not 100.00 → use 99.83 or 100.17)

## Timeframe

- **Opening range**: 10–20 minutes after regular session open
- **Trade duration**: intraday (hold for the rest of the session, or until target/stop hit)
- **Best window**: first 1–2 hours after open

## Best Market Conditions

- Trending day: large opening gap + breakout from opening range in the gap direction
- News-driven sessions where institutional order flow commits early
- Price above 200-day MA (regime filter: 2/3 of equity returns occur above long-term trend line per Varmer)

## Worst Market Conditions

- Chop / range-bound day (opening range breaks and immediately reverses)
- End-of-month or low-liquidity sessions
- Price below 200-day MA: statistically higher risk, lower return — reduce position size to ~half

## Relationship to Initial Balance

The **Initial Balance** (first hour) is the same concept at a longer timeframe. Opening Range Breakout uses a tighter 10–20 minute window.
- IB: broader context, filters noise, used for NQ scalping by Matt Miller and Vince Koehn
- ORB (10 min): faster signal, higher frequency, used for equities by Varmer/Richie

When the 10-minute ORB and the IB breakout align, signal conviction is higher.

## Why It Works (Mechanism)

Institutional order flow often commits direction early in the session:
1. VWAP algos handling large orders use the opening range to calibrate execution direction
2. The breakout from the opening range signals which side has institutional backing
3. Retail stops concentrated just outside the opening range provide fuel for the move (see [[concepts/Order-Flow]] — iceberg mechanics)
4. Once the opening range breaks, the institutional algo accelerates execution in that direction → momentum follows

This is the "leech on whale" mechanic: identifying which direction the whale is executing and trading alongside.

## Backtest / Track Record

- Traded systematically by Samir Varmer and Joe Richie in Chicago for "quite some time" — profitable on average across a broad universe of equities
- Empirically documented in academic literature on intraday momentum (first 30 minutes predicts rest of day direction)
- Aligns with Matt Miller's NQ IB breakout-retest results ($309K in 85 days per Prop Trading Secrets)

## Examples

- Kalyan's sweep-reverse scalp (described in [[analyses/Kalyan-Trading-Philosophy]]) is a variant: instead of trading the clean ORB break, waits for the stop-hunt sweep of the ORB low/high and then reverses in the direction of the institutional order. Varmer confirms this is valid and explains the mechanism.

## Related Concepts

- [[concepts/Initial-Balance]] — hourly version; same directional principle at broader scope
- [[concepts/Order-Flow]] — iceberg order and VWAP algo mechanics that drive ORB momentum
- [[strategies/Prop-Scalp-NQ-Initial-Balance]] — NQ IB version with delta confirmation
- [[analyses/Kalyan-Trading-Philosophy]] — Kalyan's sweep-reverse variant

## Sources

1. [YT-Samir-Varmer-Physicist-Trader](../sources/YT-Samir-Varmer-Physicist-Trader.md) — Varmer confirming ORB as statistically sound; mechanism of institutional order flow; recommendation for intraday trend-following personality type
