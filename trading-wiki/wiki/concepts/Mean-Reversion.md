---
title: "Mean Reversion — Defining the Mean, Measuring Stretch, and When Not To"
category: concept
tags: [mean-reversion, z-score, bollinger-bands, rsi, atr, range-bound, regime, pairs-trading, time-stop]
created: 2026-08-02
updated: 2026-08-02
sources: 1
related: [strategies/Quantified-MA-Mean-Reversion, concepts/Bollinger-Bands-Squeeze, concepts/RSI, concepts/VWAP, concepts/Volume-Analysis, concepts/ConnorsRSI, strategies/Crash-Proof-3-Filter-System]
---

# Mean Reversion — Defining the Mean, Measuring Stretch, and When Not To

## Definition
The bet that price stretched far from a reference average tends to return to it. Markets overreact, orders cluster, liquidity thins and then returns; when the push fades, price normalises.

The concept is trivially stated and almost entirely dependent on one thing: **which regime you are in**. This page is the general discipline; [[strategies/Quantified-MA-Mean-Reversion]] is one fully-specified instance of it.

> [!caution] Mean reversion is a regime bet before it is a setup
> *"It works best in range-bound markets… In strong trends, reversion trades fail more."* The honest cost/benefit: **high win rate in ranges, large losses when trends run**, plus frequent trading that raises costs and slippage. The win rate is the seduction and the tail is the bill — a run of small wins funds one loss that is larger than all of them, which is exactly the payoff shape that flatters a short track record.
>
> This is why regime classification is a **prerequisite**, not a refinement. `market_verdict.classify_regime` already labels SIDEWAYS vs TRENDING for exactly this purpose.

## How to Use

### The five-step skeleton
1. **Define the mean** — 20–50 SMA/EMA, [[concepts/VWAP]] (intraday), or a rolling median. Bollinger Bands frame what "typical distance" means for this instrument.
2. **Measure deviation** — three interchangeable measures of *stretch*:
   - `RSI` / Stochastic beyond 30 / 70 ([[concepts/RSI]])
   - a **z-score of ±2** against the mean
   - price **1.5–2 ATR** from the mean
3. **Add context** — map support/resistance; favour longs near support and shorts near resistance; want **volume confirmation** on the turn and **cooling** volatility before entry ([[concepts/Volume-Analysis]]).
4. **Confirm** — engulfing, pin bar, or momentum fade (RSI hooking back up through 30; MACD histogram shrinking then crossing). **The extreme alone is never the trigger** — an oversold market can stay oversold.
5. **Enter and exit** — enter after the signal candle **closes back inside** the band, not while price is still extending. First exit at the mean; optional runner to the opposite band.

### Stops, sizing, and the exit nobody implements
- **Stop beyond the extreme, never at the mean** — `1–2 ATR` outside the band or past the swing. Placing it at the mean guarantees being stopped by the very move you are trading toward.
- **Risk `0.5–1%`** per idea. Size = account risk ÷ stop distance.
- **Scale out at the mean.** Runner to the opposite band only if volume and momentum cool as price returns.
- **Time-based exit (~10 bars).** A reversion trade that neither works nor fails is a losing trade with the loss deferred — capital parked, opportunity cost accruing, thesis silently decayed. This is the exit most systems omit, including ours.

### Failure modes, and the tell for each
| Failure | Tell |
|---|---|
| Fresh trend after a breakout | structure shifts to higher highs / lower lows — **stand down** |
| News shock | scheduled event calendar; skip or size down |
| Thin liquidity | wide spreads, erratic fills |
| **Volatility-regime shift** | ATR / Bandwidth expanding — your stretch thresholds were calibrated to the old regime and are now wrong |

That last one is the subtle one: nothing about the *signal* looks different, but the distribution it was measured against has moved.

### Timeframes and markets
**4H and daily give the cleanest signals**; lower timeframes work but noise dominates. Major FX pairs and large-cap indices revert inside ranges; **thin crypto alts and news-driven small caps trend and ignore reversion entirely**.

## Variants / Parameters
- **Mean:** 20-SMA (fast snaps) · 50-EMA (slower swings) · VWAP (intraday) · rolling median.
- **Stretch trigger:** RSI/Stoch 30/70 · z-score ±2 · 1.5–2 ATR.
- **Six standard setups:** MA reclaim · RSI/Stochastic hook · Bollinger close-back-inside · **pairs / stat-arb** (z `>|2|` entry, exit z `0–0.5`, stop z `>|3|` or 10-bar time stop) · volatility reversion (fade an ATR spike) · Fibonacci reversion (38.2%/50% retrace, stop below 61.8%).
- **Bands widening fast → stand aside.** Expanding Bandwidth is trend risk, and the same reading appears in [[concepts/VWAP]]'s decision matrix (flat slope + tight bands favours reversal; widening favours continuation) and [[concepts/Bollinger-Bands-Squeeze]].

## Common Mistakes
- **Trading it in a trend.** The single dominant failure; "oversold" in a downtrend is a description, not a signal.
- **Entering at the extreme instead of on the close back inside.** No confirmation means no defined invalidation.
- **Putting the stop at the mean** — stopped out by the target.
- **Omitting a time stop** — the trade that never resolves.
- **Assuming a high win rate means a positive expectancy.** In this style they routinely diverge; see [[concepts/Performance-Metrics]].
- **Reusing stretch thresholds across a volatility regime change** without recalibrating.

## In this repo
- **Regime classification exists**: `market_verdict.REGIME_PLAYBOOKS["SIDEWAYS"]` → *"Range-bound. Mean-reversion works, breakouts fake out."* The prerequisite is already computed and displayed.
- **The primitives exist**: `_rsi_series` (Wilder), ATR, and rolling z-scores (`rrg.py`) — so stretch could be measured three ways without new maths.

> [!gap] The playbook has no tooling behind it
> The `SCANNERS` registry is ~24 scanners and **almost entirely breakout / trend / continuation**. The reversion-adjacent few (Early Reversal Detector, Rounding Bottom, Harmonic Reversal) are **reversal-pattern** detectors rather than fade-the-stretch screens, and "RSI 60-40 Setup" is a trend-pullback entry.
> **On a SIDEWAYS day the dashboard tells you to mean-revert and then offers two dozen breakout scanners.** A `scan_mean_reversion` — stretch measured in z or ATR, close-back-inside trigger, 2-ATR stop, target at the mean, 10-bar time stop — is the missing piece, and every input it needs is already computed.

> [!contradiction] Unresolved: do stops help or hurt here?
> This page's source mandates `1–2 ATR` stops. [[strategies/Quantified-MA-Mean-Reversion]] uses **no stop at all**, because Connors' 2001–2013 equity backtests found stops *reduced or eliminated* the edge.
> The likely reconciliation, stated by neither source: a stopless fade is only survivable when something else bounds the loss — Connors carries a hard `Close > MA200` regime filter and a limit ladder; an FX intraday fade has neither. Directly testable via [[analyses/Backtest-Harness]] by running one entry rule with and without a 2-ATR stop.

## Related Concepts
- [[strategies/Quantified-MA-Mean-Reversion]] — a fully specified instance, and the source of the stop-loss contradiction above.
- [[concepts/Bollinger-Bands-Squeeze]] · [[concepts/RSI]] · [[concepts/ConnorsRSI]] — the stretch measures.
- [[concepts/VWAP]] — the intraday mean, and a decision matrix that agrees on when to prefer reversion over momentum.
- [[concepts/Volume-Analysis]] — volume confirmation on the turn; cooling volatility before entry.
- [[strategies/Crash-Proof-3-Filter-System]] — the STAND DOWN discipline, which is the same instinct as "in strong trends, wait".

## Sources
- [[sources/ForexTester-Mean-Reversion-Guide]] (2026-08-02) — the five-step skeleton, three stretch measures, six setups with entry/stop/exit, risk rules and the failure-mode list.
