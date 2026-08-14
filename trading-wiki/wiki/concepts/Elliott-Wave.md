---
title: "Elliott Wave Theory"
category: concept
tags: [elliott-wave, wave-count, impulse, corrective, price-action, extension, valuation, stage-analysis, fibonacci, mcdowell-probability-matrix]
created: 2026-06-14
updated: 2026-08-09
sources: 4
related: [concepts/RSI.md, concepts/MACD-Divergence.md, concepts/PMax, strategies/PMax-Confluence-Strategy, concepts/McDowell-Probability-Matrix, strategies/EW-Flat-Bottom-Breakout, strategies/EW-Wave5-Catch]
---

# Elliott Wave Theory

## Core Principle
Markets move in repeating cycles of 5 waves in the trend direction, followed by 3 corrective waves.

## Impulse Phase (5 waves, trend direction)
| Wave | Character |
|------|-----------|
| Wave 1 | Smart money enters — small, often unnoticed |
| Wave 2 | Pullback — never goes below start of Wave 1 |
| Wave 3 | **Strongest and longest** — big trend, most retail participation |
| Wave 4 | Sideways correction — shallow, overlaps Wave 1 range |
| Wave 5 | Final push — often weaker, divergence may appear |

## Corrective Phase (3 waves, against trend)
| Wave | Character |
|------|-----------|
| A | First drop after Wave 5 peak |
| B | Bounce — traps bulls |
| C | Final correction — often sharp |

## Key Rules
- Wave 2 never goes below start of Wave 1
- Wave 3 is never the shortest impulse wave
- Wave 4 never overlaps Wave 1 price territory (in stocks)
- Three impulse waves (1, 3, 5) + two corrective waves (2, 4) in trend

## Trading Application
- **Buy at Wave 2 or Wave 4** (corrections within uptrend)
- **Exit/sell at Wave 5** (watch for RSI divergence as W5 warning)
- **A-B-C correction** = do not buy the B bounce, wait for C to complete

## Classic Fibonacci Statistics (McDowell)
Percentile distributions for retracement/extension targets — use these to size probability-weighted zones rather than a single Fib level:

| Wave | Relationship | Distribution |
|------|--------------|--------------|
| Wave 2 | retrace of Wave 1 | 15% land 23.6-38.2% · 70% land 38.2-61.8% · 15% land 61.8-100% (never >100%, hard rule) |
| Wave 3 | extension of Wave 1 | 45% land 161.8-175% · 30% land 175-261.8% · 15% land 100-161.8% · 10% exceed 261.8% |
| Wave 4 | retrace of Wave 3 | 70% land 38.2-61.8% · 15% land 23.6-38.2% · 15% land 61.8-76.4% |
| Wave 5 | extension (anchors: end of W2 → end of W3 → end of W4) | 70% land 61.8-100% · 15% land 38.2-61.8% · 15% land 100-161.8% (most end 0.618-1.00) |

**Re-labeling trigger**: if a "Wave 4" retraces beyond 76.4% of Wave 3, treat it as a Wave 2 of a new impulse instead — re-count rather than forcing a deep Wave 4.

Simple ABC correction stats: Wave B ≈ 50% of Wave A (max 76.4%); Wave C = 1.0x, 1.618x, or 2.618x Wave A.
Irregular complex correction: Wave B = 1.15-1.272x Wave A (makes a new extreme beyond the impulse high/low); Wave C = 1.618-2.618x Wave A.
Triangles (ABCDE) are most common in Wave 4 and resolve with a sharp thrust in the direction of Wave 1.

## Modern Confirmation Indicators (McDowell OWL / PTF)
- **OWL (price oscillator histogram)**: short MA = 5, long MA = 35, source = low price, histogram display. The highest/deepest histogram reading within the last 144 bars marks Wave 3. Bearish/bullish divergence between Wave 3 and Wave 5 (price extends further, histogram doesn't) confirms Wave 5. "144 bars" ≈ 4.8 months on daily, 2.7 years on weekly — the default lookback for "the current dominant trend."
- **PTF (RSI tuned for trend continuation)**: RSI length 9 on close, bands at 80/20. Band *penetration* (not classic overbought/oversold) implies ~75% odds of a further high/low in that direction. RSI failing to penetrate the band during what should be Wave 5 signals trend exhaustion. Note: this is a different convention from [[concepts/RSI]]'s 40-80/20-60 regime ranges — both can coexist in separate panes.
- **Multi-timeframe alignment**: pick a higher timeframe ~3-5x the base interval (e.g. daily→weekly→monthly) and require the OWL histogram trend direction to agree across all of them.

## McDowell Probability Matrix (MPM)
See [[concepts/McDowell-Probability-Matrix]] for the full 6-factor (0-5 each, max 30) scoring framework that combines the classic statistics above with the OWL/PTF/multi-timeframe modern reads into a single wave-count confidence score. Key principle: the MPM/EW forecast is an "ungrounded" filter on *direction* only — entries, stops, and exits must come from a price-based "grounded" system (see [[strategies/EW-Flat-Bottom-Breakout]] and [[strategies/EW-Wave5-Catch]] for two such grounded setups).

## Algorithmic Implementation (v2 engine, from PMax Confluence Strategy)
[[strategies/PMax-Confluence-Strategy]] implements an automatable EW engine on top of the theory above:

### Pivot Detection & 9-Position Cycle
- Zigzag pivots via `ta.pivothigh`/`ta.pivotlow` at a configurable depth (5=Daily, 3=Weekly, 2=Monthly).
- Each full cycle is mapped to 9 positions: impulse cycles = `W1, 2a, 2b, W2, W3, 4a, 4b, W4, W5`; corrective cycles = `W, w1, x1, X, Y, y1, z1, XX, Z`. Repeated cycles get prime marks (`'`, `''`, `'''`).
- Current wave position auto-detected by finding the longest of the last ~18 pivot legs and assuming it is Wave 3 (`autoOff9`).

### Forward Projections
- Up to 36 future segments projected using Fibonacci ratios: W1=1.0×, W2=0.618 retrace, W3=1.618 extension, W4=0.382 retrace of W3, W5=1.0×.
- Bar spacing is timeframe-aware (21 bars/segment daily, 4 weekly, 2 monthly, 3–390 intraday).

### EW Validity Rules (gates strong buy/sell signals)
A wave count is **invalid** (`ewValid = false`) if any of:
- Wave 2 retraces beyond 100% of Wave 1's start
- Wave 3 is the shortest of Waves 1/3/5
- Wave 4 overlaps Wave 1's price territory

Additional "modern constraint" checks (informational): **alternation** (|W2/W1 − W4/W3| > 0.2 → sharp vs sideways correction alternation present) and **Fibonacci alignment** (W3 ≥ 1.618×W1 and W2 between 50–78.6% of W1 → "High Prob (Aligned)" vs "Low Prob (Guideline Gap)").

### Extension Analysis
- **Short-Term Extension**: price has already exceeded the *next* Fibonacci wave target while still nominally "in" the prior wave (e.g. exceeding the W3 1.618 target while in W1) — signals a possible early/aggressive move.
- **Long-Term Extension**: the most recent 9-pivot net move is >3× the average of the last 8 swing legs — signals a multi-cycle stretched structure.
- Combined into one "Extension Risk" read: NORMAL → IMPULSE EXT (short-term only) → OVER-EXTENDED (long-term only) → EXHAUSTION (both, "Critical Cycle Risk").

### Valuation (Over/Undervalued)
- **Overvalued**: at Wave 3 or Wave 5 peaks (bull) with RSI overbought, or at the bearish equivalents with RSI oversold — classic exhaustion zones.
- **Undervalued**: at Wave 2/Wave 4 troughs with RSI extremes, or early Wave 1 with RSI<40 — classic accumulation zones.
- Otherwise "Fair".

### Earnings Power (proxy, not real fundamentals)
- **Strong**: impulse phase (W1/W3/W5) + volume above its MA + ADX > threshold (trend confirmed by participation).
- **Weak**: corrective phase + volume below its MA.
- **Moderate**: impulse-without-volume or corrective-with-volume (mixed signals).

### Stage Analysis (Weinstein-style, 1–4)
- **Stage 1 (Accumulation)**: early impulse (W1/2a/2b) in a bull context, or W5 completion in a bear context (basing after downtrend).
- **Stage 2 (Advancing)**: W2 through W4 progression in a bull context.
- **Stage 3 (Distribution)**: W5 completion in a bull context (topping).
- **Stage 4 (Declining)**: early-to-mid impulse in a bear context.
- Odd-numbered cycles (corrective overlays) override to "Correction within Up/Downtrend".

## Related
- [[concepts/RSI]] — RSI divergence often appears at Wave 5 top; also drives Valuation analysis above
- [[concepts/MACD-Divergence]] — MACD divergence at wave tops
- [[concepts/PMax]] — EW trend alignment is one of the confluence factors gating PMax signals
- [[strategies/PMax-Confluence-Strategy]] — full implementation of the v2 engine and advanced analysis layer
- [[concepts/McDowell-Probability-Matrix]] — 6-factor wave-count confidence score
- [[strategies/EW-Flat-Bottom-Breakout]] — grounded Wave 3 entry setup
- [[strategies/EW-Wave5-Catch]] — grounded Wave 5 entry setup

## Examples in This Wiki — and a capability gap measured 2026-08-09

Two engines implement this page, and **they disagree with each other on live NIFTY**:

| Engine | Where | Method | NIFTY read (2026-08-07) |
|---|---|---|---|
| `ew_module.py` | Stock Analyzer "EW" chip | McDowell probabilistic — pivots → W1 structure → W3/W5 target *distributions*, plus OWL histogram + PTF RSI(9) | **W2**, W1 21,744→26,373, W3 primary **31,097** (45%) |
| [elliott_wave.js](tools/elliott_wave.js) | chart tool overlay | ATR-adaptive ZigZag → greedy 6-point impulse windows → A-B-C off each impulse | **C of an expanded-flat, complete**, invalidation 23,606 |

> [!contradiction] Same doctrine, two engines, incompatible answers — and one engine contradicts itself
> The dashboard can show the Python "W2" chip beside the JS overlay's completed correction. Separately, `ew_module.py` returns `wave_pos: W2` alongside `owl_signal: "W3-past"` — the pivot structure says Wave 3 has not begun while the OWL histogram says its peak has passed, and `ew_summary_row` prints both unreconciled. Full workings: [[analyses/EW-Engine-vs-SweeGlu-NIFTY]].
>
> Also worth heeding: on 3D NIFTY the JS engine found 18 impulses with **median score 40, max 59** and **14 of 18 flagged diagonal**. Our own tool is reporting that it has no strong count on this instrument.

**Capability gap — corrective COMBINATIONS (WXY), not corrective labels as such.** `ew_module.py` and `elliott_wave.js` are impulse-first and single-degree: `detectCorrectives` only labels A-B-C hanging off an already-detected impulse. The third engine, [pmax.pine](tools/pmax.pine), does alternate impulse and corrective cycles with prime marks for repeats — but its corrective branch emits **`(a)(ax)(ay)(b)(c)(az)(ax)(d)(e)`, an ABCDE triangle**, not a WXY combination (`f_waveLabel`, line 196). A triangle is one pattern; WXY is two or three joined by X waves. So a discretionary label like *(y) of (b) of (x) of (B or X) of (iv) of Major (3)* ([[sources/SweeGlu-EW-NIFTY-Chart3-2026-08-05]]) is **not something this repo can express** — complex corrections, the WXY combinations that dominate sideways markets, are outside all three models.

> [!contradiction] This page has documented WXY support for pmax that the code does not have
> Line 72 above (and [[sources/PMax-Optimization-Pine]]) state pmax's corrective cycles are `W, w1, x1, X, Y, y1, z1, XX, Z`. **`tools/pmax.pine` emits `(a)(ax)(ay)(b)(c)(az)(ax)(d)(e)` instead**, and the WXY string exists nowhere in any source file — only in those two markdown pages. Presumably the upstream TradingView script had it and our port simplified to a triangle. **Fourth documented-but-not-coded gap found this week**, after the order-block selection rule, volume-profile HVN/LVN, and the evening-star gap.

That gap is real but **should not be filled first**: no EW output here has ever been scored against outcomes ([[analyses/Backtest-Harness]] has never run on it). Building deeper labelling on unmeasured labelling repeats the FA-3-before-FA-2 mistake.

**Known bug:** `ew_module.analyze_ew` raises `TypeError` on **weekly** bars — the timeframe a position-degree count would most naturally use.

## Sources
- [[sources/trading-learning-raw]] (2026-06-14) — core theory
- [[sources/PMax-Optimization-Pine]] (2026-06-14) — v2 algorithmic engine + advanced analysis
- [[sources/EW-Techniques-Simplified-McDowell]] (2026-06-15) — classic Fibonacci statistics, OWL/PTF modern indicators, McDowell Probability Matrix, grounded trade setups
