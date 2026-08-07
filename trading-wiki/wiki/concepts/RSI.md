---
title: "RSI — Relative Strength Index"
category: concept
tags: [momentum, oscillator, divergence]
created: 2026-06-14
updated: 2026-06-22
sources: 2
related: [concepts/EMA.md, concepts/ConnorsRSI.md, concepts/MACD-Divergence, sources/SwingEdge-Learn-Indicators-Deep-Dive]
---

# RSI — Relative Strength Index

## Definition
Momentum oscillator, scaled 0–100. Default period: 14.

## Key Levels
- **>70**: Overbought (potential exhaustion)
- **<30**: Oversold (potential bounce)
- **50**: Trend divider — above = bullish momentum

## How to Use
- **Divergence**: Price new high, RSI does not → bearish signal
- **Trend context**: In strong uptrends RSI ranges 40–80 (use 40–50 as buy zone, not 30); in downtrends RSI ranges roughly 20–60 (bounces to 50–60 are selling opportunities for trend-followers, dips to 20–30 are continuation, not reversal). The same RSI number means different things in different regimes — read it relative to the trend, not against the textbook 70/30 thresholds.
- **Failure swings**: RSI breaks prior RSI swing → strong signal

### Divergence — four variants, not just one (2026-06-22 addition)
| Type | Price | RSI | Meaning |
|---|---|---|---|
| Bullish (reversal) | Lower low | Higher low | Sellers losing intensity — setup-quality clue, not an entry by itself; wait for price to confirm (break a swing high / reclaim a level) |
| Bearish (reversal) | Higher high | Lower high | New high made with less momentum — tightening-of-risk signal near known resistance; in a strong young trend this resolves up often, don't short it inside a Stage-2 leader without other evidence |
| **Hidden bullish (continuation)** | Higher low | **Lower low** | Pullback was shallow in price but momentum reset deeply — a continuation setup, the opposite signature of classic bullish divergence |
| **Hidden bearish (continuation)** | Lower high | **Higher high** | Mirror of hidden bullish; flags weakness inside a downtrend bounce, useful for short-side continuation |

### Swing failure (failure swing) — a higher-confidence variant
RSI pushes into overbought/oversold, pulls back, then fails to reach the prior extreme on the next push — e.g. RSI hits 78, pulls back to 55, rallies only to 71 (a lower high inside overbought), then breaks below 55. That structural break *inside RSI itself* is read as a higher-confidence signal than any single absolute level (70/30) crossing alone.

### Period selection
Shorter RSI (7 or 9) for active swings; longer (21+) for position/weekly context. Don't run a short-period RSI on a weekly chart — it's just noise at that timeframe.

## Common Mistakes
- Selling just because RSI is overbought in a strong trend — strong leaders spend extended time above 70; exiting on "overbought" alone misses the bulk of the move.
- Ignoring higher timeframe divergence
- Trading divergence alone with no price confirmation — divergence is "a tell, not a clock": it can resolve in the trend's favor repeatedly before an actual reversal arrives.
- Running RSI on choppy, range-bound names — it generates constant noise there regardless of period; only meaningful on names with clear structure.

## Confluence Uses (2026-07-19)
- **RSI 40–60 trend band → a full setup:** the regime-aware ranges above are formalized into two with-trend entries (RSI-40 pullback / RSI-60 breakout) on the 21 & 50 EMA in [[strategies/RSI-60-40-Setup]].
- **Fibonacci + RSI:** buy a ~61.8% [[concepts/Fibonacci-Retracement]] pullback *only* when RSI is turning up out of oversold — pairing a location edge with a momentum edge.

### Shipped as a chart indicator (2026-08-07)
The four-variant table above is now executable: `rsi_divergence.js` in the
charting tool detects all four and draws each one twice — across the price
swings and across the matching RSI swings, because the whole point is that the
two disagree and one line alone cannot show a disagreement. Colour carries
direction (green bullish / red bearish), dash carries kind (solid regular /
dashed hidden).

Two things worth knowing when reading it:
- **A faded line with a `?` is provisional.** Its swing has not been confirmed
  by a reversal yet, so it can move or vanish on the next bar. That is inherent
  to divergence on a live chart; the indicator shows it rather than letting the
  line quietly disappear.
- **It uses a coarser swing filter than the Elliott overlay** (ATR ×2.0 vs ×1.2).
  Measured: at Elliott's setting a 300-bar daily chart gives ~132 pivots and the
  resulting "divergences" have a median span of 8 bars and ±0.4% legs — noise
  with a label on it. At ×2.0 it is ~43 pivots and a 27-bar median span.

Still true, and the reason this is a chart overlay and not a scanner: divergence
is **a tell, not a clock**, and [[analyses/Backtest-Harness]] has never measured
it. `detect_bullish_rsi_divergence` in `scanner_templates.py` (which feeds Early
Reversal's score) is a cruder, older test — rolling-mean RSI rather than Wilder,
last-bar-vs-prior-10 rather than swing pivots, and only the regular-bullish
variant — so the chart and that scanner will not always agree. Reconciling it to
this four-type definition is open.

## Related
- [[concepts/EMA]] — Combine RSI timing with EMA trend direction
- [[concepts/ConnorsRSI]] — composite short-period (3,2,100) variant used for mean-reversion exit timing; uses a much shorter RSI(3) lookback than the classic 14-period RSI documented here
- [[concepts/MACD-Divergence]] — same bullish/bearish divergence logic, but on smoother (more-lagged, less frequent, typically more reliable) data
- [[strategies/RSI-60-40-Setup]] · [[concepts/Fibonacci-Retracement]]

## Sources
- [[sources/Connors-MA-Quantified-Approach-2013]] — cross-reference only (introduces the related ConnorsRSI composite)
- [[sources/SwingEdge-Learn-Indicators-Deep-Dive]] (2026-06-22) — regime-aware ranges, hidden divergence, swing failure swings, period selection
- [[sources/Fingrad-Trading-Infographics-Collection]] (2026-07-19) — RSI 40–60 trend-band setup and Fibonacci+RSI confluence entry
