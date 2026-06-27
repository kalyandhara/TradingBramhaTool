---
title: "Book — Elliott Wave Techniques Simplified"
category: source
tags: [elliott-wave, fibonacci, mcdowell-probability-matrix, owl, ptf, trading-psychology]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [concepts/Elliott-Wave.md, concepts/McDowell-Probability-Matrix.md, strategies/EW-Flat-Bottom-Breakout.md, strategies/EW-Wave5-Catch.md]
---

# Book — Elliott Wave Techniques Simplified

## Metadata
- Author: Bennett McDowell (founder, TradersCoach.com), with Foreword by Stanley Dash and a student chapter by Dean Jenkins
- Publisher: McGraw-Hill Education, 2016 (ISBN 978-0-07-181931-2)
- File: `Bennett McDowell - Elliot Wave Techniques Simplified (2015, McGraw Hill LLC) - libgen.li.epub`

## Key Takeaways
- Elliott Wave analysis should combine **Classic** (price structure, volume, Fibonacci) with **Modern** (price oscillator histogram + RSI w/ nonstandard settings, multi-timeframe alignment) approaches — agreement between the two raises confidence in a wave count.
- The **McDowell Probability Matrix (MPM)** scores 6 factors (0–5 each, max 30) to turn "is this wave count right?" into a numeric probability — a directly portable confluence-scoring idea, conceptually similar to the existing [[strategies/PMax-Confluence-Strategy]] 16-factor score.
- McDowell's "secret settings": Price Oscillator (5/35, source=low, histogram) to find Wave 3 and spot divergence; RSI(9, bands 80/20) — band penetration (not classic overbought/oversold) predicts continuation ~75% of the time.
- Only Waves 1, 3, 5, and (carefully) Wave C of a Wave 4 are tradeable. Waves 2/4 are "do not trade" by default — this matches the existing wiki's EW guidance but adds the **Wave-C-of-4 exception** with a concrete setup (enter right after Wave B fully retraces to the Wave 3 price level).
- Concrete numeric statistics for Wave 2/3/4/5 retracement/extension distributions (percentile breakdowns, not just single Fibonacci levels) — useful for setting probability-weighted target zones rather than single numbers.
- Two named, rules-based setups: **Flat Bottom Channel Breakout** (catch Wave 3 off a basing channel) and **Catching Wave 5** (enter on Wave 4 Fibonacci retracement completion, ride to Wave 5 extension zone with a 3-bar trailing stop).
- Heavy psychology section (Ch. 2 & 9): markets move because of crowd fear/greed cycles mapped onto the 5-wave structure; "grounded" (price-based entries/exits/risk) vs "ungrounded" (forecast-based) assessments — forecasts (EW counts) should only filter direction, never replace a price-based entry/exit/stop system.

## Detailed Notes

### Classic Elliott Wave — refined statistics (vs. existing wiki page)
The existing [[concepts/Elliott-Wave]] page already has the core 5-3 wave structure and basic rules from the prior `trading-learning-raw` source. This book adds **percentile distributions**:
- Wave 2 retrace of Wave 1: 15% land 23.6–38.2%, 70% land 38.2–61.8%, 15% land 61.8–100% (never >100%, hard rule).
- Wave 3 extension of Wave 1: 45% land 161.8–175%, 30% land 175–261.8%, 15% land 100–161.8%, 10% exceed 261.8%.
- Wave 4 retrace of Wave 3: 70% land 38.2–61.8%, 15% land 23.6–38.2%, 15% land 61.8–76.4%. A retrace beyond 76.4% usually means it's actually a Wave 2 of a new impulse, not a Wave 4 — re-evaluate the count.
- Wave 5 extension (3-anchor Fib from end of W2→W3→W4): 70% land 61.8–100%, 15% land 38.2–61.8%, 15% land 100–161.8%. Most Wave 5s end between 0.618 and 1.0 of this projection.
- Alternation rule: if Wave 2 is simple (ABC zigzag), expect Wave 4 to be complex (flat/irregular/triangle), and vice versa.
- Simple ABC correction stats: Wave B = ~50% of Wave A (max 76.4%); Wave C = 1.0x, 1.618x, or 2.618x Wave A.
- Irregular complex correction: Wave B = 1.15–1.272x Wave A (makes a new extreme beyond the impulse high/low); Wave C = 1.618–2.618x Wave A.
- Triangles (ABCDE) are most common in Wave 4 and produce a sharp "thrust" breakout in the direction of Wave 1 when they resolve.

### Modern indicators — McDowell's nonstandard settings
- **Price Oscillator Histogram ("OWL")**: short MA = 5, long MA = 35, source = low price, displayed as histogram. Highest/deepest histogram reading within the last 144 bars = Wave 3. Bearish divergence (price higher, histogram lower) between Wave 3 and Wave 5 confirms Wave 5. 144 bars ≈ 4.8 months on daily, 2.7 years on weekly — used as the "current dominant trend" lookback window.
- **RSI ("PTF")**: length 9 (close), bands at 80/20 (not 70/30). Penetration above 80 → ~75% chance of an eventual higher high (common in Wave 3, rare in Wave 5 — its absence in Wave 5 is itself a signal of trend exhaustion). Penetration below 20 → ~75% chance of an eventual lower low. RSI failing to penetrate the band on what should be Wave 5 = trend likely ending.
- **Multiple timeframe alignment**: pick a higher timeframe roughly 3-5x the base interval (e.g., daily→weekly→monthly) and require the OWL histogram sign/trend to agree across all three before trusting a wave count — directly reinforces the fractal-symmetry section already in [[concepts/Elliott-Wave]].

### McDowell Probability Matrix (MPM) — new concept, see [[concepts/McDowell-Probability-Matrix]]
6 factors scored 0–5 each (max 30 total):
1. Clear price structure (classic)
2. Clear OWL/price-oscillator Wave 3 reading (modern)
3. Volume confirms Wave 3 = highest volume (classic)
4. Fibonacci levels hit as expected (classic)
5. RSI/PTF band behavior aligns with forecast (modern)
6. Multi-timeframe alignment (modern)

Score bands run from "minimal probability" (0-9) to "outstanding probability" (28-30) — exact table wasn't fully extractable from the converted text but the scoring mechanism and 6 inputs are clear. **Grounded vs ungrounded**: the MPM score only filters *which direction* to trade; actual entries/exits/stops must come from a price-based ("grounded") system, never from the forecast itself.

### Trading setups
**Flat Bottom Channel Breakout** (catch Wave 3 early):
1. Find a narrow horizontal channel (≥20 bars) after a completed Wave 5 of the prior trend.
2. Mark channel support/resistance, alert on breakout.
3. After breakout, wait for a higher-low + higher-high (bullish) or lower-high + lower-low (bearish) before entry.
4. OWL histogram must confirm direction (positive for longs, negative for shorts) at entry.
5. Initial stop below the higher low / channel support (or above for shorts); trail under subsequent higher lows / above lower highs.

**Catching Wave 5**:
1. Identify completed Wave 3, draw Fib retracement (W2→W3 anchors) for the Wave 4 target zone (38.2–61.8%).
2. Wait for the correction to land in that zone (skip the trade if it overshoots past 75% — likely a Wave 2 re-label).
3. OWL histogram must flip back to trend direction; draw Fib extension (W2→W3→W4 anchors) for the Wave 5 target zone (61.8–100%).
4. Enter on higher-low/higher-high (or lower-high/lower-low) confirmation after Wave 4 ends. Stop below Wave 4 low (or above Wave 4 high for shorts).
5. Inside the Wave 5 target zone, trail aggressively with a 3-bar-back stop (stop at the extreme of the 3rd bar back); exit in full when hit.
6. Require minimum 2:1 reward:risk or skip the trade.

### Trading psychology (Ch. 2, 9)
- Crowd psychology drives the 5-3 wave structure: optimism overextends into Waves 3/5 tops, pessimism overextends into corrective lows — news is a *trigger*, not the *cause*, of mood shifts.
- "Grounded" assessments (price-based entries/exits/stops) must always override "ungrounded" assessments (EW forecasts/targets).
- Student case study (Dean Jenkins): 77% win rate, 2.6 payout ratio, never risked more than 2% of account per trade — illustrates that a mediocre win rate is fine with strict R:R and risk sizing (echoes [[analyses/Kalyan-Trading-Philosophy]] cash-management principles).
- "If you don't see a clear wave count, move on" — avoid forcing analysis on messy/complex-correction charts; there's always another chart with clarity.

## Actionable Insights
1. Add the OWL (5/35 on low, histogram) and PTF (RSI 9, 80/20 bands) indicator settings to chart templates — they're a cheap, concrete addition to existing RSI/EMA-based screens and directly help locate Wave 3 vs Wave 5.
2. The MPM 6-factor / 0-5 scoring framework could be merged with or run alongside the existing [[strategies/PMax-Confluence-Strategy]] 16-factor confluence score — both produce a 0-100%-style probability/grade from multiple confirming signals, but MPM is specifically about *wave-count confidence* rather than entry timing.
3. Wave 4 retracement >76.4% of Wave 3 = treat as a relabeled Wave 2 (new impulse starting), not a deep Wave 4 — a concrete re-labeling trigger not previously captured in the wiki.
4. The "Catching Wave 5" setup with a 2:1 minimum R:R and 3-bar trailing stop is a ready-made, mechanical addition to [[strategies/EMA-Pullback]]-style swing entries.

## Contradictions with Existing Wiki
- None directly contradictory. This source uses RSI bands of 80/20 (vs. the existing [[concepts/RSI]] page's 40-80/20-60 regime ranges) — different purpose (band *penetration* as a continuation signal, not overbought/oversold), so both can coexist; flagged here for clarity if the two RSI conventions are ever combined in one indicator pane.

## Pages Updated
- Created: `wiki/sources/EW-Techniques-Simplified-McDowell.md` (this page)
- Created: `wiki/concepts/McDowell-Probability-Matrix.md`
- Created: `wiki/strategies/EW-Flat-Bottom-Breakout.md`
- Created: `wiki/strategies/EW-Wave5-Catch.md`
- Updated: `wiki/concepts/Elliott-Wave.md` (added classic statistics tables, OWL/PTF modern indicator settings, MPM cross-link)
- Updated: `wiki/index.md`, `wiki/log.md`
