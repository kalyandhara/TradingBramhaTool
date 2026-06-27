---
title: "Initial Balance"
category: concept
tags: [initial-balance, NQ, market-profile, value-area, scalping, first-hour, futures, morning-session]
created: 2026-06-17
updated: 2026-06-17
sources: 1
related:
  - strategies/Prop-Scalp-NQ-Initial-Balance.md
  - concepts/Order-Flow.md
  - concepts/Prop-Trading-Funded-Model.md
  - sources/Prop-Trading-Secrets-Lien-Crete-2025.md
---

# Initial Balance

## Definition

The **Initial Balance (IB)** is the high and low price established during the **first hour of regular trading hours** (9:30–10:30 a.m. EST for US futures). It represents the range where price discovery begins each session and defines the zone of early price acceptance.

IB is a core concept in **Market Profile** analysis (developed by Peter Steidlmayer at CBOT, 1980s). It anchors intraday structure and provides high-probability reference levels for the rest of the trading day.

## How to Use

### IB Breakout-Retest Entry (Matt Miller's Method)

1. **Wait for IB to form**: do NOT trade during 9:30–10:30 a.m. EST; observe only; mark IB high and IB low
2. **Watch for breakout**: price breaks above IB high (long setup) or below IB low (short setup) with a strong candle close
3. **Wait for retest**: price returns to the broken IB level (IB high becomes new support for longs; IB low becomes new resistance for shorts)
4. **Delta confirmation**: at the retest, delta (net aggressor volume) shows net buying for longs / net selling for shorts
5. **Entry**: enter as price bounces off the retested IB level with confirming candle (hammer, engulfing, or inside bar breakout)
6. **Stop**: below the retest low (longs) or above the retest high (shorts) — typically 4–6 NQ points
7. **Target**: 10 NQ points ($200 per contract), or next structure level if further away

### Value Area Fill Play (Vince Koehn / Market Profile)

- **Value Area** = price range containing 70% of prior session's volume (VAH = value area high, VAL = value area low, POC = point of control)
- If price opens **outside** the prior day's value area (driven by Asia/London session) and then **re-enters** it → **80% probability of filling the full value area**
- Entry: buy at VAL when price accepts back inside value area (next candle opens above VAL); target VAH (or vice versa for shorts)
- Stop: outside VAL by a few ticks

### Time-Based Edge

- Best trading window: **10:00 a.m.–12:00 p.m. EST** (IB has formed; early volatility settled; morning trend established)
- Avoid: 9:30–10:00 a.m. open (rapid moves, false signals) and 3:30–4:00 p.m. close (low volume, whipsaw)
- Vince Koehn's optimal: 10:00–11:00 a.m. EST specifically

## Statistical Properties

- ~70% of trading days, price remains within the IB range (IB breakouts only occur 30% of days)
- When IB breakout occurs with high delta AND clean structure, follow-through rate is meaningfully higher
- Value area fill: 80% probability when price re-enters from outside (cited by Vince Koehn; consistent with published Market Profile research)

## Relationship to Adjacent Levels

| Level | How It Interacts with IB |
|-------|-------------------------|
| Prior day high/low | Strong extension target or barrier for IB breakouts |
| Prior day VAH/VAL | 80% fill probability when re-entering value area |
| Prior day POC | Strong intraday magnet; price tends to revisit |
| Fibonacci daily/weekly | IB confluence with Fib level = higher-conviction setup (Koehn model) |
| Weekly open | Directional bias anchor; IB relative to weekly open frames session tone |

## Variants / Parameters

| Variant | Definition | Use Case |
|---------|-----------|----------|
| 30-minute IB | First 30 minutes only | Scalpers wanting faster structure |
| 1-hour IB | Standard (9:30–10:30 EST) | Most Market Profile practitioners |
| 2-hour IB | First 2 hours | Slower, more volatile instruments |
| True IB | Regular session only (excludes overnight globex) | Pure day-session analysis |

## Common Mistakes

1. **Trading during IB formation** — the first hour is price discovery; context, not signals
2. **Entering IB breakouts without confirmation** — many IB breaks are false; wait for the retest
3. **Ignoring delta** — an IB breakout with weak or negative delta on a long is a low-quality setup
4. **Waiting for a retest that isn't coming** — on strong trending days, price breaks IB and doesn't look back; must recognize trending-day context vs. range-day context
5. **Using IB in isolation** — always check prior day levels, value area, and overall session direction first

## Tools

- **NinjaTrader**: built-in Market Profile and IB plotting
- **Sierra Chart**: highly customizable Market Profile with IB and value area auto-plotting
- **TradingView**: custom scripts for IB and value area visualization
- **thinkorswim** (Charles Schwab): Market Profile charting with separate regular/overnight session view

## Related Concepts

- [Order Flow](Order-Flow.md) — delta confirmation for IB entries
- [EMA](EMA.md) — 21 EMA as dynamic support within the IB breakout move
- [McDowell-Probability-Matrix](McDowell-Probability-Matrix.md) — confluence scoring applicable to IB setups
- [Prop-Trading-Funded-Model](Prop-Trading-Funded-Model.md) — IB strategy context for prop account management

## Examples in This Wiki

- Matt Miller: $309,400 from 85 trading days using IB breakout-retest on NQ
- Vince Koehn: value area fill play with 80% stated probability; made $1M across 20 Apex accounts using IB + Fibonacci confluence

## Sources

1. [Prop-Trading-Secrets-Lien-Crete-2025](../sources/Prop-Trading-Secrets-Lien-Crete-2025.md) — Ch14 (Matt Miller), Ch16 (Vince Koehn)
