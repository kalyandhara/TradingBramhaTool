---
title: "Support and Resistance"
category: concept
tags: [support-resistance, price-action, zones, flip-zones, multi-timeframe, swing-high-low, congestion, fibonacci, S&D]
created: 2026-06-18
updated: 2026-06-19
sources: 2
related:
  - strategies/Supply-Demand-Zone-Trading.md
  - concepts/Order-Flow.md
  - concepts/Elliott-Wave.md
  - concepts/Darvas-Box.md
  - strategies/Opening-Range-Breakout.md
  - sources/SR-SMC-Supply-Demand-Dhruv-Emily-2022.md
  - strategies/False-Break-Buildup-Trading.md
  - sources/Price-Action-Trading-MTF-Brandon-Kenny-2023.md
---

# Support and Resistance

## Definition

Support and resistance (S&R) are price zones where supply and demand are temporarily imbalanced:
- **Support**: buyers outnumber sellers → price stops falling and reverses upward
- **Resistance**: sellers outnumber buyers → price stops rising and reverses downward

These are **zones, not lines**. A precise line causes missed trades (undershoot) and false breakout exits (overshoot). Always draw a zone between the candle body and wick at the key level.

## How to Use

### Step 1 — Mark levels top-down (timeframe hierarchy)
1. **Weekly chart**: mark the major swing highs and lows, congestion areas, prior rejection zones
2. **Daily chart**: plot weekly levels; add daily swing points and consolidation zones
3. **Intraday (1H, 15m)**: look for entries only at levels visible from above

Only mark **valid major levels** — swing points with clear rejection, multi-touch congestion zones, prior S&R flip zones. Ignore minor retracements. Cluttered charts prevent good trading.

### Step 2 — Draw the zone correctly
1. Switch to **line chart** (closes only); identify the exact rejection point
2. Switch back to **candlestick chart**; draw a zone from the **body** to the **wick** of the candle that formed the rejection

### Step 3 — Wait for price to approach and show entry signal
Entry signal candles at the zone: **pin bar**, **engulfing**, **outside candle**

Validate with S&D entry checklist (see [[strategies/Supply-Demand-Zone-Trading]]):
1. Momentum loss (decreasing candle range)
2. Lower wick (demand candle) or upper wick (supply candle)
3. Mixed red/green candles (indecision → reversal)

### Step 4 — Enter in direction of dominant trend
- Only long from demand zones in uptrends; only short from supply zones in downtrends
- Exception: reversal setups at major HTF levels (RBD / DBR formations)

## Variants / Parameters

### Types of S&R
| Type | Description | Strength |
|------|------------|---------|
| Horizontal (swing H/L) | Prior swing highs and lows | High — clear market memory |
| Congestion area | Multi-bar sideways consolidation | High — Smart Money activity zone |
| Flip zone | Broken support → resistance; broken resistance → support | High — participant psychology inverts |
| Fibonacci retracement | 23.6%, 38.2%, 50%, 61.8% of major swings | Medium — widely watched, self-fulfilling |
| Moving Average (dynamic S&R) | 20/50/200-day MA | Medium — effective in strong trends only |
| Trend line | Diagonal connection of swing points | Medium — subjective; break often signals trend change |

### Strength Factors (rank order)
1. **Freshness** — first retest is strongest; each subsequent test consumes orders → weakens the level
2. **Exit move** — bigger and faster the move away from the zone, the larger the order imbalance
3. **Time at zone** — less time at the level = more aggressive Smart Money = stronger zone
4. **Distance of excursion** — further price traveled before returning → higher R:R; buyers far below confirm absence of sellers
5. **Volume at creation** — high volume at zone = strong market interest

### The Psychology of S&R (Three-Group Model)
At any S&R zone, three participant types have interest in the level:

| Group | At support | Motivation |
|-------|-----------|-----------|
| **Longs** | Profitable; would buy more if price returns | Add to winner |
| **Shorts** | In pain; hoping for break-even exit (which = buying) | Close short = buy |
| **Uncommitted** | Missed the move; waiting to enter long | Buy the dip |

All three groups create buying at the same support level → zone self-fulfills on retest.

When support **breaks**: all groups were wrong → longs now need to exit (sell) → shorts vindicated → uncommitted now waiting to short. The support zone becomes resistance.

## S&R Flip Zones
- **Broken resistance → support**: buyers proved stronger; sellers at the old resistance are now underwater; pullback to the level gives long entry
- **Broken support → resistance**: sellers proved stronger; buyers at the old support are now underwater; bounce to the level gives short entry

Flip zones are high-probability entries because the psychological role inversion is confirmed by the break itself.

## Breakout Conditions
S&R breaks predictably in these situations:
- **With the trend**: support breaks into downtrends; resistance breaks into uptrends
- **Tight range at the level**: neither side applying pressure → imminent break (direction of trend)
- **Repeated testing**: each test consumes orders at the level; more touches = weaker; eventually breaks
- **Ascending triangle**: higher lows into resistance → buyers more aggressive → resistance breaks upward
- **Descending triangle**: lower highs into support → sellers more aggressive → support breaks downward

**Confirming a breakout** (avoid false breaks):
- Wait for a pin bar or engulfing candle closing on the other side of the level
- Re-test of the broken level from the new side (flip zone) provides a second confirmation entry

## Common Mistakes

1. **Drawing lines, not zones** — exact lines cause undershoot misses and overshoot exits; always use a zone of width
2. **Too many levels** — marking every minor retracement clutters the chart; only mark major, obvious levels
3. **Third or later retests** — by the 3rd+ touch, the level is weakened; skip these entries
4. **Counter-trend entries at S&R** — longing at support in a strong downtrend has low probability; trend + S&R must align
5. **Ignoring HTF context** — a support on the 15-minute chart inside a 1-hour resistance zone will fail; always check the higher TF first
6. **Not waiting for an entry signal** — price touching a zone is not a trade signal; wait for a pin bar, engulfing, or two-bar reversal at the zone

## Area of Value & the Rubber Band Snap

[Price-Action-Trading-MTF-Brandon-Kenny-2023](../sources/Price-Action-Trading-MTF-Brandon-Kenny-2023.md) frames any S/R zone, respected MA, or trendline as an "area of value" and adds an explicit entry veto: **don't take a trend-direction entry when price is far from its area of value.** The only technically valid stop in that case sits beyond the area of value, making it too wide for acceptable R:R — and price tends to snap back toward the area of value before continuing, stopping out the late entry first. Wait for the pullback instead. See [[strategies/False-Break-Buildup-Trading]] for the full entry rule.

## Related Concepts
- [[strategies/Supply-Demand-Zone-Trading]] — S&D zones are S&R areas with Smart Money context; RBR/DBD/RBD/DBR formations
- [[concepts/Order-Flow]] — S&R zones correspond to iceberg order placement areas; Varmer's VWAP algo mechanic operates at predictable S&R stops
- [[concepts/Darvas-Box]] — Darvas high = resistance; Darvas box = consolidation = S&D zone
- [[concepts/Elliott-Wave]] — Wave 2 and Wave 4 retrace to Fibonacci S&R; Wave 3 breaks resistance
- [[strategies/Opening-Range-Breakout]] — Opening range H/L are the session's first S&R levels
- [[strategies/False-Break-Buildup-Trading]] — false-break fade and buildup-tight-stop tactics at S/R zones; rubber band snap entry filter
- [[concepts/Distribution-Days]] — SwingEdge's falsifiable support-loss rule: pivot low = local minimum with ≥2 confirming candles each side; close >0.5% below it triggers a structural break flag. Also documents the "failed retest" pattern (price revisits a broken pivot, fails to reclaim, settles back under) as the bearish mirror of a flip-zone retest.

## Examples in This Wiki

- Kalyan's sweep-reverse scalp ([[analyses/Kalyan-Trading-Philosophy]]): enters long at a swept demand zone; stop below the sweep low (base of the zone); target session high (next resistance). Directly implements demand zone entry + flip zone stop logic.
- VCPBot pivot breakout ([[strategies/VCPBot-Trend-Template]]): entry above the pivot (prior swing high resistance → becomes support on pullback = flip zone).
- Initial Balance H/L ([[concepts/Initial-Balance]]): IB high and low are the session's S&R levels; breakout-retest follows flip zone logic.

## Sources

1. [SR-SMC-Supply-Demand-Dhruv-Emily-2022](../sources/SR-SMC-Supply-Demand-Dhruv-Emily-2022.md) — core framework; zone drawing; psychology; flip zones; breakout conditions; strength factors; multi-TF approach
2. [Price-Action-Trading-MTF-Brandon-Kenny-2023](../sources/Price-Action-Trading-MTF-Brandon-Kenny-2023.md) — Chapter 3; area of value / rubber band snap entry filter
