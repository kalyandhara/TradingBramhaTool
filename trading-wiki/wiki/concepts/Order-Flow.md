---
title: "Order Flow"
category: concept
tags: [order-flow, DOM, depth-of-market, delta, bookmap, market-microstructure, footprint, scalping]
created: 2026-06-17
updated: 2026-06-17
sources: 1
related:
  - concepts/Initial-Balance.md
  - strategies/TPT-Thrust-Pullback-Thrust.md
  - strategies/Prop-Scalp-NQ-Initial-Balance.md
  - strategies/Opening-Range-Breakout.md
  - sources/Prop-Trading-Secrets-Lien-Crete-2025.md
  - sources/YT-Samir-Varmer-Physicist-Trader.md
---

# Order Flow

## Definition

Order flow analysis is the study of how buy and sell orders are being executed in real time through the Depth of Market (DOM), Level 2 data, and trade-by-trade prints. Rather than asking "where is price?", it asks: **"Who is buying/selling, with how much conviction, at which specific level?"**

Order flow is used to confirm or reject trade entries based on actual market participation, rather than lagging price indicators.

## Core Components

### 1. Depth of Market (DOM / Level 2)

The live order book showing:
- **Bid side**: limit buy orders queued at each price level (waiting to buy)
- **Ask side**: limit sell orders queued at each price level (waiting to sell)

Large bid/ask "walls" (clusters of limit orders) act as temporary support/resistance because market orders must sweep through them before price can move past. Note: walls can be pulled/spoofed; they are not equivalent to historical price S/R.

### 2. Delta (Net Aggressor Volume)

**Delta = Market Buy Volume − Market Sell Volume**

| Delta Reading | Interpretation |
|--------------|----------------|
| Positive, rising | Aggressive buyers dominating → bullish near-term |
| Negative, falling | Aggressive sellers dominating → bearish near-term |
| Positive delta + falling price | Sellers absorbing buyers → bearish divergence (likely reversal down) |
| Negative delta + rising price | Buyers absorbing sellers → bullish divergence (likely reversal up) |

Used by Matt Miller: positive delta at Initial Balance retest = long entry confirmation.

### 3. Bid Absorption vs. Ask Absorption

- **Bid absorption**: large limit bids absorb incoming market sells → price holds despite sell pressure → potential long setup (floor identified)
- **Ask absorption**: large limit asks absorb market buys → price holds despite buy pressure → potential short setup (ceiling identified)

This is the mechanism behind Davide Biocchi's "blue shark" detection.

### 4. Bookmap

Standalone platform providing:
- Heat-map visualization of the order book across time (shows liquidity building and vanishing)
- Iceberg order detection (hidden orders partially revealed)
- Liquidity cluster identification near Fibonacci/S/R levels
- Alert capability when large orders appear or disappear

Vince Koehn adjusts his Fibonacci entry/exit levels by ±8–10 NQ points based on where Bookmap shows actual liquidity vs. his theoretical level.

Andres Granger uses Bookmap + QuantTower for arbitrage execution quality and size estimation.

## Davide Biocchi's Participant Classification (TWbook Indicator)

Biocchi (Chapter 4, Prop Trading Secrets) proprietary indicator `TWbook` classifies participants by order size and execution pattern:

| Label | Behaviour | Signal Use |
|-------|-----------|-----------|
| **Piranhas** (retail) | Small lots, fast in/out | Contrarian (retail is often on wrong side) |
| **White Sharks** (mid-tier institutions) | Medium size, systematic | Context-dependent |
| **Blue Sharks** (large institutions / HFT) | Large hidden/iceberg orders; absorb moves | Follow their direction |

Three DOM order types Biocchi tracks:
1. **Spot orders**: execute immediately at market price (aggressor orders; remove liquidity)
2. **Market orders**: aggressive sweeps that take out full order book levels at once
3. **Hidden/iceberg orders**: only partially displayed; remainder revealed as each tranche fills; indicates large institutional intent

**Key signal**: when Blue Sharks show **bid absorption** (absorbing heavy selling at a level, price not falling), the downward move is unlikely to sustain → potential long setup.

## Austin Silver's VWAP + Order Flow Proxy

Simplified order flow via VWAP:
- **Above VWAP** = institutions have bought above this level; long bias
- **Below VWAP** = institutions have sold below this level; short bias
- Entry: 21 EMA break in direction of VWAP bias serves as entry trigger
- (No raw DOM required; VWAP position is a proxy for aggregate institutional positioning)

## Tools Overview

| Tool | Use | Typical Cost |
|------|-----|-------------|
| **Bookmap** | Heat-map order book; liquidity visualization | ~$100/mo subscription |
| **QuantTower** | Scalping platform with footprint charts; order flow | Subscription |
| **NinjaTrader** | Execution + DOM + footprint charts | Free platform; data fees apply |
| **Sierra Chart** | Highly customizable DOM + footprint | Subscription |
| **TradingView** | No real order flow; price analysis only | Free/paid |
| **Coinglass** | Crypto-specific: funding rates, open interest, liquidations | Free |

## How to Use

### For NQ Scalping (Entry Confirmation)
1. Mark key level (Initial Balance high/low, prior day high/low, Fibonacci confluence)
2. Wait for price to approach the level
3. Check delta: if entering long, confirm net delta is positive (buyers dominating) at the test
4. Check DOM: confirm large bids visible at or near the level (bid absorption)
5. Enter on confirmation; stop below the level

### For Directional Bias (Session Setup)
1. Check overnight delta: if positive overnight → buyers were active → bullish lean for morning
2. Check VWAP position at open: above VWAP → long bias for the session
3. Watch for first 30-min delta direction to confirm session tone

## Common Mistakes

1. **Watching delta in isolation** — price can rise on negative delta (sellers absorbed) and fall on positive delta (buyers absorbed). Always check price reaction at the level.
2. **Confusing DOM walls with permanent S/R** — large limit orders can be pulled in milliseconds; not the same as historical price structure
3. **Over-relying on order flow without price context** — order flow is an entry timing tool, not a direction-finding tool; establish HTF direction first
4. **Not accounting for spoofing** — HFT algorithms place and cancel large orders to move price; use time-persistent Bookmap view to filter spoofing from genuine orders

## Related Concepts

- [Initial Balance](Initial-Balance.md) — core level for NQ scalping; delta used for IB retest confirmation
- [VCP](VCP.md) — VCP breakout combined with volume spike signals institutional entry
- [EMA](EMA.md) — VWAP + EMA(21) as simplified order flow proxy (Austin Silver approach)
- [Performance-Metrics](Performance-Metrics.md) — profit factor helps evaluate whether order flow confirmation adds edge

## Iceberg Orders and VWAP Algo Mechanics (Varmer)

The "stop hunt" pattern — price sweeps a predictable level, triggers stops, then reverses in the predicted direction — is **not a conspiracy**. It is the natural output of institutional VWAP execution algorithms:

1. Institution has a large order (e.g., 1 million shares) to execute over hours
2. VWAP/smart algo has "trader logic": knows stops cluster at round numbers, swing lows, support lines
3. When approaching such a level, the algo **slows its own buying** → price drifts down without buy support → retail stops trigger below the level
4. Algo then **accelerates buying** at the cheaper price → price rebounds
5. From outside, this looks like an intentional stop hunt; mechanically it is cost-basis improvement

**Double-tap explanation**: more sophisticated algo versions test the level twice before committing. This is why double-tap sweeps are increasing in frequency.

**Key insight — "leech on whale" strategy**:
- Retail trader identifies the predictable sweep zone
- Enters long after sweep + confirmation (structure break back above)
- Is riding alongside the institutional VWAP algo, not against it
- "You are the leech on the shark" — Varmer

**Why small retail stops can move price**: "Liquidity exists over periods of time; at any instant in time it doesn't really exist." (Olsen & Associates: "camel through the eye of a needle.") The order book is thin precisely at the level being tested, so even small stop orders temporarily move price.

**Practical order placement** (Varmer):
- Never place orders at round numbers (100.00, 50.00, 200.00) — these are targeted by algos
- Never use numbers ending in 0 or 5
- Use prime numbers or strange lots (96 shares, 221, 131) to look like retail, not institutional
- Protected low after a sweep is a statistically better stop location than an obvious support line

Valid losses in a leech-on-whale setup occur when "something else looked like the iceberg but wasn't" — the confirming sweep was not an institutional level, just noise.

## Sources

1. [Prop-Trading-Secrets-Lien-Crete-2025](../sources/Prop-Trading-Secrets-Lien-Crete-2025.md) — Ch4 (Biocchi), Ch10 (Granger), Ch12 (Silver), Ch14 (Miller), Ch16 (Koehn)
2. [YT-Samir-Varmer-Physicist-Trader](../sources/YT-Samir-Varmer-Physicist-Trader.md) — Iceberg order mechanics; VWAP algo trader logic; leech on whale strategy; double-tap frequency increase; order placement tactics
