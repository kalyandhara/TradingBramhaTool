---
title: "NQ Scalping — Initial Balance Breakout-Retest"
category: strategy
tags: [NQ, scalping, initial-balance, prop-trading, futures, delta, morning-session, matt-miller, vince-koehn]
created: 2026-06-17
updated: 2026-06-17
timeframe: intraday | scalp
sources: 1
related:
  - concepts/Initial-Balance.md
  - concepts/Order-Flow.md
  - concepts/Prop-Trading-Funded-Model.md
  - strategies/TPT-Thrust-Pullback-Thrust.md
  - sources/Prop-Trading-Secrets-Lien-Crete-2025.md
---

# NQ Scalping — Initial Balance Breakout-Retest

## Core Idea

Wait for the Initial Balance (first-hour high/low on NQ) to form; then trade the breakout of the IB level once price returns to retest it as new support/resistance. Entry is confirmed by positive delta (net aggressor buying) at the retest. Target: 10 NQ points.

Primarily from **Matt "Trades by Matt" Miller**, who made $309,400 from 85 trading days using this approach on NQ futures via Apex Trader Funding. **Vince Koehn** applies a complementary Fibonacci + S/R approach to the same time window.

## Setup Criteria

1. **Pre-session prep**: mark prior day's high, low, VAH, VAL, POC on the 5-minute chart; note key Fibonacci daily/weekly levels
2. **IB formation (9:30–10:30 a.m. EST)**: do NOT trade; observe and mark IB high and IB low
3. **Directional bias**: confirm session direction from prior day context, overnight range, and opening VWAP position
4. **IB breakout**: price breaks above IB high (long) or below IB low (short) with a strong large-range candle close
5. **Retest**: price pulls back to the broken IB level (IB high becomes new support; IB low becomes new resistance)
6. **Delta confirmation at retest**: net aggressor buying (positive delta) at the retest for longs; net selling (negative delta) for shorts
7. **Entry candle**: confirming candle at the level — hammer, engulfing, or 1-min breakout above retest high

## Entry Rules

- **Long**: Price breaks above IB high → returns to IB high level → delta shows net buying → enter long at or just above IB high
- **Short**: Price breaks below IB low → returns to IB low level → delta shows net selling → enter short at or just below IB low
- **Do not enter on the first break**: wait for the retest; false IB breaks happen; the retest separates quality setups from noise

## Exit Rules

**Profit target:**
- Primary: 10 NQ points ($200/contract standard NQ; $20/contract micro MNQ)
- Secondary: next major structure (prior day high, weekly level, major Fibonacci) if > 10 points away

**Stop loss:**
- Long: below the retest low (typically 4–6 NQ points below entry)
- Short: above the retest high
- Hard stop; no exceptions; "mental stops" are not stops

**Three-strikes rule:**
- After 3 losing trades in one session → stop trading completely
- Do not attempt to recover losses; protecting daily drawdown is more important than recovering trades
- Restart the next day fresh

**Daily target protection:**
- Prop accounts: set a daily sub-goal (e.g., $1,500/day on $150K 5-day evaluation)
- Once daily sub-goal hit → trail stop on any remaining positions → if stopped out, call it a day; do not re-enter
- "Your profits only become real when they hit your bank account" — take payouts, don't leave everything at risk

## Timeframe

- **Primary chart**: 5-minute NQ futures (regular session)
- **Entry refinement**: 1-minute chart for entry candle precision
- **Context chart**: 30-minute or 1-hour for prior day levels and trend structure
- **Best trading window**: 10:00 a.m.–12:00 p.m. EST (IB formed; early noise settled; morning trend established)
- **Avoid**: 9:30–10:00 a.m. open (excessive noise); 3:30–4:00 p.m. close (low-volume whipsaw)

## Value Area Extension (Vince Koehn Variant)

On days when the value area play is active:
- If price opens outside prior day's value area → re-enters → next candle opens inside value area → enter in direction of fill
- Target: top or bottom of prior day's value area (80% fill probability)
- Combine with IB level for confluence: IB breakout toward value area + value area fill = double-confluence setup

## Fibonacci + S/R Confluence (Koehn Method)

Within the same 10:00–11:00 a.m. window, apply:
1. Mark daily/weekly Fibonacci retracements manually (thinkorswim or NinjaTrader)
2. Color-code by timeframe (e.g., red = monthly, blue = weekly, yellow = daily)
3. Let Trade Devils S/R indicator auto-plot daily S/R on 5-min chart
4. Use Bookmap to adjust entry/exit by ±8–10 points to where actual liquidity clusters
5. Enter only when ≥3 confluence factors align: Fib + S/R level + IB level + delta

## Position Sizing for Prop Accounts

**Overfunded + underleveraged** (Matt Miller principle):
- Trade on the largest account size possible relative to contract size
- This increases the drawdown buffer and reduces psychological pressure per trade

**Micro NQ (MNQ) vs. Full NQ (NQ):**
- MNQ: $2/point (vs. $20 for NQ); 10-point target = $20/contract; suitable for early prop accounts or tight daily drawdown
- Switch to full NQ once account has sufficient cushion above trailing drawdown

**Scale with accounts principle (Vince Koehn):**
- 1–3 contracts per account × 20 accounts > 20 contracts × 1 account
- Per-account target: $250–$500/day; across 20 accounts = $5,000–$10,000/day
- Work in groups of 3–5 accounts; hit mini-target per group; protect and move to next group

## Best Market Conditions

- Clear directional day with momentum established at open
- IB forms with clean high and low (not chaotic whipsaw during first hour)
- IB breakout is decisive (large candle, clear expansion from IB range)
- Orderly, low-volume retest (price drifts back to IB level rather than spiking through)
- Delta confirms direction at the retest level

## Worst Market Conditions

- Inside day (price never breaks out of IB, or breaks and immediately reverses)
- Major high-impact news during IB formation (9:30–10:00 a.m. EST: NFP, CPI days)
- Very narrow IB range (less than 30 NQ points) → false breakout risk high
- Choppy afternoon session — apply only to morning window; stop by noon

## Backtest / Track Record

- **Matt Miller**: $309,400 from 85 trading days on NQ (publicly documented via Apex Trader Funding; multiple funded accounts)
- **Vince Koehn**: $1M profit across 20 Apex accounts using complementary Fibonacci + S/R approach in same 10–11 a.m. window; had previously lost $350K before refining discipline

## Related Concepts

- [Initial Balance](../concepts/Initial-Balance.md) — the core level concept and statistical properties
- [Order Flow](../concepts/Order-Flow.md) — delta as entry confirmation tool
- [TPT-Thrust-Pullback-Thrust](TPT-Thrust-Pullback-Thrust.md) — IB breakout-retest is a TPT pattern; same framework
- [Prop-Trading-Funded-Model](../concepts/Prop-Trading-Funded-Model.md) — context for running on funded accounts; trailing drawdown mechanics
- [Trading-Psychology-Champion](../concepts/Trading-Psychology-Champion.md) — three-strikes rule; daily discipline; first-trade tone

## Sources

1. [Prop-Trading-Secrets-Lien-Crete-2025](../sources/Prop-Trading-Secrets-Lien-Crete-2025.md) — Ch14 (Matt Miller), Ch16 (Vince Koehn)
