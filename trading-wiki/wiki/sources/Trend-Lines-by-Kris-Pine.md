---
title: "Pine Script — Trend Lines by Kris (KRISTRADER1)"
category: source
tags: [pine-script, trendlines, supply-demand-lines, pivot-points, breakout, angle-filter, tradingview]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [concepts/Trend-Lines, concepts/Support-Resistance, concepts/Market-Structure-CHOCH-BOS, strategies/False-Break-Buildup-Trading]
---

# Pine Script — Trend Lines by Kris

## Metadata
- Author: © KRISTRADER1 (TradingView)
- License: Mozilla Public License 2.0
- Format: Pine Script v6 indicator, `overlay=true`, max 500 lines/labels, `max_bars_back=5000`
- Ingested: 2026-07-03 (pasted source code)

## Key Takeaways
1. **Fully mechanical trendline drawing** — no discretion anywhere: confirmed pivot highs/lows (`ta.pivothigh/low(prd, prd)`, default sensitivity 20) are binned (newest-first, max 10 kept), and a line forms from the two most recent pivots when they slope the right way (falling pivot highs → supply line; rising pivot lows → demand line).
2. **Clean-line validation** — a candidate line is rejected if *any* close between the two pivots, or between the second pivot and the current bar, has already crossed it (close above a supply line / below a demand line). Lines are only drawn when price has fully respected them so far.
3. **Normalized angle filter ≤ 30°** — slope is normalized to a fixed 500-bar × (500/3) chart-aspect box using the 500-bar high-low range (`Yaxis`), making the angle scale-independent, then lines steeper than 30° are discarded. Steep trendlines are unsustainable and break trivially; only shallow, durable lines survive. The angle is printed as the line's label.
4. **Body-close break rule** — a break requires the candle *body* (`max(open, close)` for supply, `min(open, close)` for demand) to cross the projected line. Wick pierces don't count. This is a built-in fakeout guard — the same wick-vs-body distinction the [[strategies/False-Break-Buildup-Trading]] page documents as the trapped-trader false-break tell.
5. **One active line per side, with a refresh rule** — a new line only forms if the previous one has already broken, *or* if the pivots are stepping directionally (three successively lower pivot highs / higher pivot lows), letting a steepening trend replace a stale unbroken line. Last 3 lines + labels per side are kept for context.
6. **Break semantics for signals** — supply-line break (body close above a falling resistance line) = bullish; demand-line break (body close below a rising support line) = bearish. Both are exposed as `alertcondition`s.

## Detailed Notes
- **Pivot gap cap**: the two pivots must be within `prd × 7` bars (140 bars at defaults) — no lines drawn across unrelated price regimes.
- **Angle normalization math**: `normalisedSlope = (height / (Yaxis / diffY)) / diffX` with `height = 500/3` and `Yaxis` = highest-lowest of the last ≤500 bars; `angle = |atan(normalisedSlope)|` in degrees. Equivalent to mapping the last 500 bars onto a 3:1 aspect box so "30°" means the same thing on any symbol or timeframe.
- **Line maintenance**: while a line is unbroken, its right endpoint is re-projected to the current bar each bar (`line.set_x2/y2`), so the drawn line always extends to "now"; at the break bar the endpoint freezes at the break price.
- **The `valid` gate in full**: `valid = previousLineBroken OR (array.size(bin) > 2 AND before.price < prev2.price)` (mirror for demand). So an unbroken line blocks new lines *unless* structure keeps stepping down/up — the bin's third pivot is only consulted for this refresh test.
- Cosmetics ignored for our purposes: colors, width input, label styling, history trimming to 3.

## Actionable Insights
- **Ported to Python (2026-07-03)**: `detect_trendline_break()` in `tools/scanner_templates.py` — same pivot pairing, gap cap, clean-line validation, normalized ≤30° angle filter, and body-close break rule. Wired as the 7th check ("Trendline") in the Early Reversal Detector's validation layer: a recent supply-line break passes the check; a recent demand-line break raises a ⚠ warning on the card.
- The falling-supply-line break is a natural *reversal confirmation*: a stock exiting a decline that body-closes above the trendline connecting its lower pivot highs has objectively ended the downtrend's supply structure — complementary to (and more gradual than) the horizontal-level CHOCH test from [[concepts/Market-Structure-CHOCH-BOS]].

## Contradictions with Existing Wiki
- None. The body-close break rule *agrees* with [[strategies/False-Break-Buildup-Trading]]'s false-break framework (wick pierce = trap, body close = real move) — independent convergence on the same rule from a different author.
- Mild tension worth remembering: [[concepts/Support-Resistance]] argues levels are *zones, not lines*; this script draws literal 1-price-wide lines. The body-close requirement effectively re-adds tolerance, but combining the two (line break + zone-width buffer) is stricter than either alone.

## Pages Updated
- [[concepts/Trend-Lines]] — created (first dedicated trendline concept page; this script is its primary source)
- [[concepts/Market-Structure-CHOCH-BOS]] — cross-referenced (diagonal supply-line break vs horizontal swing-high break as complementary reversal confirmations)
- `tools/scanner_templates.py` — Python port + validation-layer wiring (code, not wiki)
