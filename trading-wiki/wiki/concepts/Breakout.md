---
title: "Breakout — Confirmation, Retest, and Why Most Fail"
category: concept
tags: [breakout, false-breakout, fakeout, retest, volume-confirmation, atr-stop, squeeze, measured-move, regime]
created: 2026-08-02
updated: 2026-08-02
sources: 1
related: [concepts/Mean-Reversion, concepts/Volume-Analysis, concepts/Support-Resistance, concepts/Market-Structure-CHOCH-BOS, concepts/VCP, concepts/Bollinger-Bands-Squeeze, strategies/Opening-Range-Breakout]
---

# Breakout — Confirmation, Retest, and Why Most Fail

## Definition
Buying when price closes above resistance, or selling when it closes below support, on the thesis that a range ending starts a new move.

Mechanically it is a trapped-participant story: *above resistance, trapped shorts buy back and new buyers join; below support, trapped longs exit and new sellers push*. Two order-flow sources arriving together is what produces the fast follow-through.

This is the complement of [[concepts/Mean-Reversion]] — same market, opposite regime. Breakouts want **expansion**; reversion wants **range**. Neither is a style you hold all the time, which is why regime classification precedes both.

## How to Use

### The confirmation stack
In order. Each item removes a class of failure, and skipping any of them is where the losses come from:

1. **A level worth breaking** — a real range, triangle, flag or rectangle boundary. *"Levels that were not real supply/demand"* is a named failure cause; a break of a line you drew arbitrarily confirms nothing.
2. **A candle CLOSE beyond it, never a wick.** The single most repeated rule in every source on this.
3. **Volume confirmation** — expansion versus the recent average. See the caveat below on the threshold.
4. **Trend filter agrees** — 20-EMA above 50-EMA for longs (or price above [[concepts/VWAP]] intraday). *"If the filter disagrees, skip."*
5. **ATR stop set before entry** — `1–1.5 × ATR` beyond the level or retest.

### Entry: break versus retest
| | Breakout close | Retest |
|---|---|---|
| Trigger | bar closes through the level | break, pull back, level holds, small confirming candle |
| Trade-off | fast, **more slippage** | **tighter risk, fewer false signals** — but the move can leave without you |
| Stop | `1.5 × ATR` below the level | a few ticks beyond the retest extreme, or `1 × ATR` |

The retest is the higher-quality entry and the lower-participation one. Which you take is a throughput-versus-precision choice, not a correctness one.

### Stops — one rule above the rest
> **Do not set the stop inside the range you just broke. That gets hit by noise.**

The range is where price has already proven it likes to oscillate. A stop placed inside it is a stop placed in the noisiest available location. Put it where the setup is *proven wrong* — beyond the level after a retest, or `1–1.5 ATR` out.

### Targets
- **Measured move** — project the pattern/range height from the break point.
- **R-multiple** — at least `1.5R–2R` on first take-profit.
- **Trail** the remainder by `1 × ATR` or under successive higher lows.
- If **volume fades and price stalls near the level, take some off**.

### Volatility contraction precedes expansion
*"Before big moves, volatility often contracts — small candles, narrow ranges — and the surge after a squeeze signals momentum."* This is the [[concepts/VCP]] thesis reached from the volatility side rather than the pattern side, and it is why [[concepts/Bollinger-Bands-Squeeze]] and breakout scanning are the same family.

Note the symmetry with [[concepts/Mean-Reversion]]: **expanding Bandwidth means stand aside for a reversion trader and stand ready for a breakout trader.** Same measurement, opposite instruction, resolved by which regime you have classified.

### False breakouts
The defining failure. Filters, in order of power: wait for the close · require rising volume · prefer a held retest · skip tiny moves in dead volatility and don't chase spikes · avoid high-impact news · keep risk fixed and small.

**Exit rule:** a fast close back inside the range *is* the invalidation — exit and reassess rather than hoping. Our `detect_structure_chain` mechanises exactly this as a **time-boxed failed break** (close back inside within 3 bars), which makes it countable instead of impressionistic.

## Variants / Parameters
Nine standard setups: **ORB** ([[strategies/Opening-Range-Breakout]]; 5–30 min session range, target 1R–2R) · momentum/news · S/R · trendline · **volatility squeeze** (stops one ATR *inside* the base) · volume-confirmed · gap · consolidation (rectangle/triangle/flag, target = pattern height) · **Fibonacci** (close beyond 61.8%, targets at 100% and 127.2%).

> [!caution] There is no standard volume-confirmation threshold
> Four numbers for one idea, all presented as rules:
> | Threshold | Lookback | Source |
> |---|---|---|
> | `≥1.2×` | 20-bar | [[sources/ForexTester-Breakout-Guide]] |
> | `≥1.5×` | 20-period | [[sources/ForexTester-Volume-Analysis-Guide]] — **same publisher** |
> | `≥1.5×` | 20-day | our breakout scanners |
> | `≥1.5×` | 50-period | our VCP |
> | `≥1.4×` | 50-DMA | our structural breakout |
>
> The same vendor published 1.2× and 1.5× within weeks, neither citing data. Treat the threshold as a **tunable to be swept**, not a constant to be adopted — and note that a lower bar admits more trades of lower quality, so it is not a free choice. Settle it for our universe with [[analyses/Backtest-Harness]], not with another article.

## Common Mistakes
- **Entering on a wick** instead of a close.
- **Stop inside the broken range** — see above.
- **Breaking against the higher-timeframe trend** — a named failure cause.
- **Trading breaks of lines nobody else is watching.**
- **Taking breaks on thin volume** or in illiquid hours.
- **Chasing after the move has already extended** — the retest exists for this.
- **Assuming a breakout regime because the last one worked** — the volatility state has to be checked each time.

## In this repo
Our scanner coverage is **strongly weighted to this concept**: Stage 2 Uptrend · Consolidation Breakout (6M–10Y) · Structural Breakout · ATH Breakout · IPO-Base Breakout · High Tight Flag · Near Pivot · VCP Coiling · Minervini VCP · Darvas Box · Falling Wedge · Momentum Continuation.

Two asymmetries worth naming:
- **We detect breaks well and retests poorly.** The article's preferred entry is the retest, and `scan_order_block` is the only scanner treating a retest as the trigger rather than the break itself.
- **This is the mirror of the [[concepts/Mean-Reversion]] gap.** We are well-tooled for the breakout regime and untooled for the reversion one, while `market_verdict.classify_regime` reports both — so on a SIDEWAYS day the tooling and the playbook disagree.

## Related Concepts
- [[concepts/Mean-Reversion]] — the opposite regime; read the two together.
- [[concepts/Volume-Analysis]] — confirmation, and the threshold problem above.
- [[concepts/Support-Resistance]] — what makes a level worth breaking.
- [[concepts/Market-Structure-CHOCH-BOS]] — a break of structure is this concept expressed in swing terms; the failed-break flag is the shared invalidation.
- [[concepts/VCP]] · [[concepts/Bollinger-Bands-Squeeze]] — contraction preceding expansion.
- [[strategies/Opening-Range-Breakout]] · [[strategies/False-Break-Buildup-Trading]] — the session variant, and trading the failure instead.

## Sources
- [[sources/ForexTester-Breakout-Guide]] (2026-08-02) — the confirmation stack, break-vs-retest trade-off, the three trade plans with ATR stops and R-targets, nine setups, and the false-breakout filter list.
