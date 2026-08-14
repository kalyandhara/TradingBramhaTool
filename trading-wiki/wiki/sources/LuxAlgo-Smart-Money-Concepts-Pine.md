---
title: "Pine Script — Smart Money Concepts [LuxAlgo]"
category: source
tags: [pine-script, smc, smart-money, luxalgo, order-blocks, fvg, bos, choch, equal-highs-lows, premium-discount, market-structure, mtf, tradingview]
created: 2026-07-16
updated: 2026-07-16
sources: 1
related: [entities/LuxAlgo, concepts/Market-Structure-CHOCH-BOS, concepts/Order-Blocks, concepts/Equal-Highs-Lows, concepts/Premium-Discount-Zones, concepts/Fair-Value-Gap, concepts/Multi-Timeframe-Analysis, sources/SR-SMC-Supply-Demand-Dhruv-Emily-2022, sources/BOS-FVG-Pullback-Signals-Pine]
---

# Pine Script — Smart Money Concepts [LuxAlgo]

## Metadata
- Author: © [[entities/LuxAlgo]]
- License: CC BY-NC-SA 4.0 (Attribution-NonCommercial-ShareAlike) — **non-commercial**; a port must credit LuxAlgo and stay non-commercial + share-alike
- Format: Pine Script **v5** indicator, `overlay = true`, `max_labels_count = 500`, `max_lines_count = 500`, `max_boxes_count = 500`
- Ingested: 2026-07-16 (pasted source code)

## Why this matters
This is the **canonical, most-forked SMC indicator on TradingView** — effectively the reference implementation the whole "Smart Money Concepts" retail ecosystem copies. It is a *superset*: nearly every SMC primitive the wiki tracks in isolation lives here in one script, with the exact mechanical definitions the community treats as standard. It is the single best source for pinning down "how do SMC traders actually compute X" for X ∈ {internal vs swing structure, BOS, CHoCH, order blocks, equal highs/lows, FVG, premium/discount, strong/weak highs}.

## Key Takeaways
1. **Two-tier market structure — internal vs swing.** The script runs the *same* swing-detection algorithm at two lengths simultaneously: **swing** structure on a 50-bar pivot lookback (`swingsLengthInput`, major structure) and **internal** structure on a hard-coded **5-bar** pivot (minor structure inside the swings). Every BOS/CHoCH is labeled as either internal (dashed lines, tiny labels) or swing (solid lines). This is the key insight the wiki's existing [[concepts/Market-Structure-CHOCH-BOS]] page was missing — SMC is inherently *nested* multi-timeframe structure on a single chart.
2. **BOS vs CHoCH is decided purely by trend state at break time.** `displayStructure()` keeps a `trend.bias` per tier. On a `ta.crossover(close, pivotHigh)`: if bias was BEARISH → label **CHoCH** (and flip bias bullish); if already BULLISH → label **BOS**. Mirror for crossunder. Confirms the existing page's rule mechanically: CHoCH = first counter-trend break, BOS = continuation break. Uses **close** crossing the pivot level, not wick.
3. **Order blocks are derived from the structure break, not drawn separately.** When a bullish structure breaks, `storeOrdeBlock()` scans the bars between the broken pivot and the current bar and picks the candle with the **lowest low** (bullish OB) or **highest high** (bearish OB) — the last opposing candle before the impulse — using an ATR-parsed high/low to avoid volatile bars. That candle's range becomes the order block box. Mitigation = price closing/trading back through it. → new page [[concepts/Order-Blocks]].
4. **"Strong/Weak High/Low" = trailing extremes tagged by trend.** The script tracks the running swing top/bottom (`trailingExtremes`) and labels the most recent one **Strong** vs **Weak** by whether the swing trend agrees with it: in a bullish swing trend the low is a "Strong Low" (defended) and the high is a "Weak High" (likely to break). This is the protected-vs-vulnerable-extreme idea, formalized. → folded into [[concepts/Market-Structure-CHOCH-BOS]].
5. **Equal Highs/Lows (EQH/EQL) = liquidity pools, detected within an ATR threshold.** A new pivot whose level is within `threshold × ATR(200)` of the prior same-side pivot is tagged EQH/EQL and joined with a dotted line. Default threshold 0.1. These mark resting-liquidity zones (double-top/bottom equivalents in SMC vocabulary). → new page [[concepts/Equal-Highs-Lows]].
6. **Premium/Discount zones = Fibonacci equilibrium on the current swing range.** Between the trailing swing top and bottom: top 5% band = **Premium** (sell zone), bottom 5% = **Discount** (buy zone), middle 5% around the 50% level = **Equilibrium**. Pure geometry on `trailing.top`/`trailing.bottom`. → new page [[concepts/Premium-Discount-Zones]].
7. **FVG detection is MTF-capable and auto-thresholded.** Classic 3-candle gap, but pulled through `request.security` so gaps can be detected on a *higher* timeframe than the chart, and the significance filter is an **auto threshold** = cumulative mean of absolute bar-delta-% × 2 (adaptive, not a fixed %). Complements the existing [[concepts/Fair-Value-Gap]] page (which documented the Quant script's ATR-scaled filter and pullback-entry — LuxAlgo adds the MTF + auto-threshold flavor and draws *two* half-boxes per gap).

## Detailed Notes

### Swing detection (`leg()` / `getCurrentStructure()`)
- A "leg" flips **bearish** when `high[size] > ta.highest(size)` (new leg high confirmed `size` bars back) and **bullish** when `low[size] < ta.lowest(size)`. A change in leg = a confirmed pivot `size` bars ago.
- Pivots are stored in `pivot` UDTs (currentLevel, lastLevel, crossed flag, barTime, barIndex). The `crossed` flag prevents re-firing a BOS/CHoCH off an already-broken level.
- Swing labels: HH/HL/LH/LL are assigned by comparing `currentLevel` vs `lastLevel` at each new pivot (optional `showSwingsInput`).

### Order block internals (`storeOrdeBlock` / `deleteOrderBlocks` / `drawOrderBlocks`)
- **Volatility parsing**: each bar, if `(high−low) ≥ 2 × volatilityMeasure` it's a "high volatility bar" and its parsed high/low are *swapped* (`parsedHigh = low`), so a violent bar doesn't dominate OB selection. `volatilityMeasure` = `ta.atr(200)` (default) or cumulative-mean-range.
- OBs stored newest-first, capped at 100 internally, only the top N (default 5 internal / 5 swing) drawn.
- **Mitigation source** is user-selectable: `Close` (close through the OB) or `High/Low` (wick through). Bearish OB mitigated when `source > OB.barHigh`; bullish when `source < OB.barLow`.

### FVG internals (`drawFairValueGaps`)
- Bullish: `currentLow > last2High and lastClose > last2High and barDeltaPercent > threshold and newTimeframe`. Each FVG becomes **two boxes** split at the gap midpoint (visual gradient).
- Mitigation: `low < FVG.bottom` (bull) or `high > FVG.top` (bear) deletes the gap. Note this is a *wick*-through delete, looser than the existing Quant-script's close-through rule — a **contradiction worth noting** (see below).
- `fairValueGapsExtendInput` extends boxes forward N bars.

### MTF levels & misc
- `drawLevels()` renders previous Day/Week/Month H/L lines via `request.security` with `lookahead_on`, labeled `PDH/PDL`, `PWH/PWL`, `PMH/PML`.
- `Mode` (Historical vs Present) toggles whether old structure is kept or only the latest shown (deletes prior labels/lines each bar in Present mode).
- Alerts: 16 `alertcondition`s covering every internal/swing BOS+CHoCH, OB breakout, EQH/EQL, and FVG event.

## Actionable Insights
- **Highest-value ports (not yet in `tools/`)**: (1) **Order blocks** — nothing in the repo computes them; `storeOrdeBlock`'s "last opposing candle before the impulse, volatility-parsed" rule is clean and portable. Would slot into the Early Reversal / structure layer in `tools/scanner_templates.py` next to the existing `detect_bos_choch()`. (2) **Internal-vs-swing two-tier structure** — the existing `detect_bos_choch()` uses a single 5-bar pivot; adding a second 50-bar swing tier would give the nested MTF structure LuxAlgo relies on. (3) **Premium/Discount** — trivial geometry once trailing swing extremes exist; a cheap "is price in premium (don't chase longs) / discount (accumulation OK)" regime tag.
- **Equal Highs/Lows** overlaps conceptually with the wiki's [[concepts/Reversal-Chart-Patterns]] double-top/bottom detector — EQH/EQL is the same swing-equality test but framed as *liquidity to be swept* rather than a reversal pattern. A port could reuse the existing pivot detection and just add the ATR-threshold equality check.
- **Strong/Weak High/Low** gives the structure layer a "which extreme is protected" read that pairs naturally with [[concepts/Premium-Discount-Zones]] and [[strategies/Supply-Demand-Zone-Trading]] zone freshness.

## Contradictions with Existing Wiki
> [!contradiction] FVG mitigation rule differs from [[concepts/Fair-Value-Gap]]
> The existing FVG page (from the Quant script) invalidates a gap only on a **close fully through** the zone — partial wick fills stay active and *are the entry*. LuxAlgo here deletes the FVG on any **wick through** the far side (`low < bottom` / `high > top`). Same primitive, stricter/looser lifecycle. Neither is "correct" — they're different design choices (LuxAlgo is a pure visualizer that wants clean charts; Quant's is an entry-signal engine that needs the zone to survive the touch). Documented on both pages.

- No conflict on BOS/CHoCH definition — LuxAlgo's close-cross + trend-state rule **matches** [[concepts/Market-Structure-CHOCH-BOS]] exactly, and its two-tier internal/swing model *extends* rather than contradicts it.
- Order block selection ("last opposing candle before impulse") agrees with the RBR/DBD base logic in [[sources/SR-SMC-Supply-Demand-Dhruv-Emily-2022]] — an order block is essentially the origin candle of a supply/demand zone.

## Pages Updated
- [[concepts/Order-Blocks]] — **created** (first dedicated OB page; this script is the primary source)
- [[concepts/Equal-Highs-Lows]] — **created** (EQH/EQL liquidity pools)
- [[concepts/Premium-Discount-Zones]] — **created** (Fibonacci equilibrium sell/buy zones)
- [[concepts/Market-Structure-CHOCH-BOS]] — added internal-vs-swing two-tier model + Strong/Weak High/Low + order-block linkage; LuxAlgo added as source
- [[concepts/Fair-Value-Gap]] — added LuxAlgo MTF + auto-threshold variant and the mitigation-rule contradiction callout
- [[entities/LuxAlgo]] — **created** (author entity)
