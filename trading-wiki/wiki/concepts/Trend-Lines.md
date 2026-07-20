---
title: "Trend Lines (Supply & Demand Lines)"
category: concept
tags: [trendlines, supply-line, demand-line, pivot-points, angle-filter, breakout, diagonal-support-resistance]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [concepts/Support-Resistance, concepts/Market-Structure-CHOCH-BOS, strategies/False-Break-Buildup-Trading, concepts/Stage-Analysis]
---

# Trend Lines (Supply & Demand Lines)

## Definition
Diagonal support/resistance drawn through swing pivots: a **supply line** connects falling pivot highs (the downtrend's selling boundary), a **demand line** connects rising pivot lows (the uptrend's buying boundary). Where [[concepts/Support-Resistance]] levels are horizontal zones, trendlines encode the *rate* at which the controlling side is advancing — and their break marks the moment that side loses control.

## How to Use

### Mechanical drawing rules (from the KRISTRADER1 reference implementation)
1. **Pivots only** — anchor lines to *confirmed* swing pivots (a high/low with `prd` bars on each side, default 20), never to arbitrary candles. A pivot confirms only `prd` bars after it prints.
2. **Two most recent pivots, right slope** — supply: newer pivot high below the older one; demand: newer pivot low above the older one. Pivots more than `7 × prd` bars apart don't form a line (different regime).
3. **Clean-line validation** — reject the line if any close has already crossed it (above supply / below demand) between the pivots or since the second pivot. A trendline price has already violated was never a real boundary.
4. **Angle filter ≤ 30° (normalized)** — normalize slope to a fixed 500-bar, 3:1-aspect box using the 500-bar high-low range, then discard lines steeper than 30°. Steep lines describe unsustainable moves and break on the first pause; shallow lines are the durable ones.
5. **Break = body close beyond the line** — `max(open, close)` above a supply line, `min(open, close)` below a demand line. Wick pierces are not breaks — they're the false-break trap documented in [[strategies/False-Break-Buildup-Trading]].

### Signal interpretation
- **Supply-line break → bullish**: a body close above the falling line joining lower pivot highs is an objective "downtrend supply structure ended" event — the diagonal cousin of a bullish CHOCH ([[concepts/Market-Structure-CHOCH-BOS]] breaks a horizontal swing high; this breaks the descent rate itself, so it usually fires earlier).
- **Demand-line break → bearish**: body close below the rising line joining higher pivot lows — first mechanical warning an uptrend's buying pressure has failed.

## Variants / Parameters
- `prd` (sensitivity, 5–50, default 20): pivot half-width. Higher = fewer, more significant lines.
- Max pivot gap `7 × prd`; angle cap 30° (normalized); one active line per side, refreshed when broken or when pivots keep stepping in the trend direction (3 successively lower highs / higher lows).
- **Python port**: `detect_trendline_break()` in `tools/scanner_templates.py` — used as the "Trendline" check (7th) in the Early Reversal Detector validation layer: recent supply-line break = pass, recent demand-line break = ⚠ warning.

## Common Mistakes
- Drawing lines through wicks/arbitrary touches instead of confirmed pivots — un-falsifiable, redraws forever.
- Trusting steep trendlines — they break on any pause; the 30° cap exists precisely to filter them.
- Calling a wick pierce a break (or a fakeout a breakout) — require the body close, and remember [[concepts/Support-Resistance]]'s point that levels are zones: a break by a fraction of a % inside the zone's width proves little.
- Keeping a line alive after price has closed through it — a broken line's next role, if any, is the flip-zone retest, not continued projection.

## Related Concepts
- [[concepts/Support-Resistance]] — horizontal counterpart; zone-width tolerance and flip-zone retest logic apply to broken trendlines too
- [[concepts/Market-Structure-CHOCH-BOS]] — horizontal swing-break reversal labels; supply-line break ≈ early CHOCH, and both need the same follow-through confirmation
- [[strategies/False-Break-Buildup-Trading]] — wick-pierce-vs-body-close is the same trapped-trader mechanic; fade wick pierces of a still-valid line, trade body closes
- [[concepts/Stage-Analysis]] — a supply-line break off a Stage 4 decline is one of the earliest mechanical Stage 4→1 transition tells

## Examples in This Wiki
- **Python port (2026-07-03)**: `detect_trendline_break()` in `tools/scanner_templates.py`, wired into the Early Reversal Detector's validation layer and the High-Growth Screener's Validations column.
- No live-ticker example yet — annotate an entity page the next time a supply-line break fires on a tracked stock.

## Sources
1. [Trend-Lines-by-Kris-Pine](../sources/Trend-Lines-by-Kris-Pine.md) — Pine Script v6 indicator by KRISTRADER1 (MPL-2.0), ingested 2026-07-03; all mechanical rules above are from this script.
