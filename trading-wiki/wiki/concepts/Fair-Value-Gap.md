---
title: "Fair Value Gap (FVG)"
category: concept
tags: [fvg, fair-value-gap, imbalance, smc, ict, pullback-entry, rejection-wick, demand-zone, mtf, auto-threshold, luxalgo]
created: 2026-07-03
updated: 2026-07-16
sources: 3
related: [concepts/Market-Structure-CHOCH-BOS, strategies/Supply-Demand-Zone-Trading, concepts/Support-Resistance, concepts/Trend-Lines, concepts/Order-Blocks, concepts/Multi-Timeframe-Analysis]
---

# Fair Value Gap (FVG)

## Definition
A 3-candle price imbalance: when candle 1 and candle 3 don't overlap, the middle candle "raced through" a price range without trading both sides of it, leaving a gap. Bullish FVG: candle 3's low sits above candle 1's high (zone = candle 1 high → candle 3 low). Bearish FVG: candle 3's high sits below candle 1's low. In SMC/ICT reading, the gap marks one-sided institutional execution — an unfair price the market often revisits ("fills") before continuing, which makes an unfilled FVG a tradeable demand (bullish) or supply (bearish) zone.

## How to Use

### Quality filters (from the Quant reference script — raw 3-candle gaps are too common to trade)
1. **Directional middle candle** — the gap must come from a genuine momentum candle (`close > open` for bullish). A gap left by a doji-ish bar is noise.
2. **ATR-scaled minimum size** — gap height > 0.5 × ATR(14). Auto-adapts per symbol; a fixed % threshold under-filters quiet stocks and over-filters volatile ones.
3. **Track only the newest unmitigated zone per side** — old gaps far from price are stale context, not entries.

### Zone lifecycle
- **Active**: from formation until fully mitigated. Partial fills (price dips into the zone and leaves) do *not* invalidate — they're the entry opportunity.
- **Invalidated**: a *close* fully through the zone (below a bull FVG's bottom / above a bear FVG's top). Wick penetration doesn't kill the zone.
- **Consumed**: after producing one signal — no re-entry off the same zone.

### The pullback-rejection entry (bullish; bearish is the mirror)
All three on the same candle: (1) low touches inside the FVG zone; (2) close back **above** the zone top with a dominant lower wick (`close − low > high − close` — buyers rejected the dip); (3) the bar **opened** above the zone top — price fell into the zone and got bought back, rather than gapping down through it. This is [[strategies/Supply-Demand-Zone-Trading]]'s zone-touch entry with a candle-quality gate, applied to the FVG zone type.

### LuxAlgo variant — MTF detection + auto-threshold (from the LuxAlgo SMC reference)
The canonical [[sources/LuxAlgo-Smart-Money-Concepts-Pine|LuxAlgo SMC]] indicator implements FVGs with two differences worth knowing:
- **Multi-timeframe**: gaps are pulled through `request.security` so an FVG can be detected on a *higher* timeframe than the chart and drawn on it — HTF imbalances projected onto a lower-timeframe chart ([[concepts/Multi-Timeframe-Analysis]]).
- **Auto threshold** (instead of ATR×0.5): the significance filter is the cumulative mean of absolute bar-delta-% × 2 — an adaptive baseline that self-scales as the series evolves, rather than a fixed ATR multiple. Optional; can be turned off for raw gaps.
- Cosmetically each gap is drawn as **two half-boxes** split at the midpoint (a visual gradient), and boxes extend forward N bars.

> [!contradiction] Mitigation rule differs from the Quant-script lifecycle above
> This page's lifecycle (from the Quant script) invalidates an FVG only on a **close fully through** the far side — wick penetration is the entry, not the death of the zone. The **LuxAlgo** implementation deletes the gap on any **wick through** the far side (`low < bottom` bull / `high > top` bear). Same primitive, different lifecycle: LuxAlgo is a pure *visualizer* that wants clean charts, so it retires touched gaps aggressively; the Quant script is an *entry-signal engine* that needs the zone to survive the touch it trades. Pick the close-through rule when the FVG must survive to produce a pullback entry; the wick-through rule when you only want currently-untouched gaps on screen.

## Variants / Parameters
- ATR multiplier (default 0.5) and ATR length (14) for minimum gap size; raise the multiplier for fewer, more significant zones.
- **LuxAlgo variant**: auto-threshold (cumulative-mean-delta×2) + optional higher-timeframe detection + two-half-box rendering (see above).
- `tools/fvg.js` — chart-side module that finds and draws *all* FVG zones (optional min-%-size filter, fill tracking) for the chart dashboard.
- `detect_fvg_pullback()` in `tools/scanner_templates.py` — Python port of the full signal state machine; the "FVG" check (8th) in the Early Reversal validation layer: recent bullish rejection = pass, recent bearish rejection = ⚠ warning.

## Common Mistakes
- Trading every raw 3-candle gap — without the directional-middle-candle and ATR-size filters, FVGs appear constantly and mean little.
- Treating a wick through the zone as invalidation (it's often the rejection that *is* the entry) — or conversely, treating a full close-through as still-active.
- Entering on a bar that gapped down into the zone — the open-above-zone condition exists precisely to filter this trap.
- Taking FVG entries against the higher-timeframe regime — an FVG pullback is an entry *timing* tool; direction should already be justified by structure ([[concepts/Market-Structure-CHOCH-BOS]]) and the weekly tape.

## Related Concepts
- [[concepts/Market-Structure-CHOCH-BOS]] — FVGs appear at trend pauses, often near a CHOCH; that page first sketched the FVG definition this page expands.
- [[strategies/Supply-Demand-Zone-Trading]] — FVG is one zone type in the same institutional-footprint family (RBR/DBD formations leave FVGs inside them); zone freshness/strength factors apply.
- [[concepts/Support-Resistance]] — zones-not-lines logic; an FVG is a zone whose boundaries are mechanically defined instead of drawn.
- [[concepts/Trend-Lines]] — same ingest-and-adopt lineage; both scripts contribute an anti-fakeout condition (body-close break there, open-above-zone here).

## Examples in This Wiki
- **Python port (2026-07-03)**: `detect_fvg_pullback()` in `tools/scanner_templates.py`, wired into the Early Reversal Detector validation layer and the High-Growth Screener Validations column.
- Chart rendering: `tools/fvg.js` + `drawFVG()` in `tools/chart_dashboard.html`.
- No live-ticker example yet — annotate an entity page when an FVG rejection fires on a tracked stock.

## Sources
1. [BOS-FVG-Pullback-Signals-Pine](../sources/BOS-FVG-Pullback-Signals-Pine.md) — Pine v6 indicator by Quant (MPL-2.0), ingested 2026-07-03; quality filters, lifecycle rules, and the 3-condition rejection signal are from this script.
2. `tools/fvg.js` (this repo, 2026-06) — prior chart-side FVG zone detection; basic 3-candle definition and fill tracking.
3. [LuxAlgo-Smart-Money-Concepts-Pine](../sources/LuxAlgo-Smart-Money-Concepts-Pine.md) — Pine v5 indicator by [[LuxAlgo]] (CC BY-NC-SA 4.0), ingested 2026-07-16; source for the MTF (`request.security`) detection, auto-threshold significance filter, two-half-box rendering, and the wick-through mitigation variant (contradiction callout above).
