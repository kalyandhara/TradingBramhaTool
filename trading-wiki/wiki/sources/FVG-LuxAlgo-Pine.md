---
title: "TradingView — Fair Value Gap [LuxAlgo]"
category: source
tags: [pine-script, fvg, fair-value-gap, luxalgo, imbalance, mitigation, auto-threshold, mtf, dashboard, tradingview]
created: 2026-07-22
updated: 2026-07-22
sources: 1
related: [entities/LuxAlgo, concepts/Fair-Value-Gap, sources/LuxAlgo-Smart-Money-Concepts-Pine, sources/BOS-FVG-Pullback-Signals-Pine, concepts/Multi-Timeframe-Analysis]
---

# TradingView — Fair Value Gap [LuxAlgo]

## Metadata
- Author: © [[entities/LuxAlgo]]
- Source: https://www.tradingview.com/script/jWY4Uiez-Fair-Value-Gap-LuxAlgo/
- License: open-source (LuxAlgo's standard release terms are CC BY-NC-SA 4.0 — attribution / non-commercial / share-alike; any port must credit LuxAlgo and stay non-commercial)
- Format: TradingView Pine Script overlay indicator
- Ingested: 2026-07-22 (URL fetch)

## Why this matters
LuxAlgo's **dedicated, FVG-only** indicator — narrower than the [[sources/LuxAlgo-Smart-Money-Concepts-Pine|SMC superset]] already in the wiki, but it ships one thing the superset does not: a **statistics dashboard** reporting each gap's **fill %** and the **average number of bars before mitigation**. That "how long until an FVG typically fills" statistic is a genuinely new idea for this vault — it turns FVG mitigation from a binary (filled / unfilled) into a measurable expectancy. It also formalizes a **"Dynamic" mitigation** mode (track gaps as they evolve after being partially mitigated) that neither the Quant script nor the SMC superset expose as a setting.

## Key Takeaways
1. **Three-condition detection (adds a directional gate).** A bullish FVG needs `low > high[2]` **and** `close[1] > high[2]` (the middle bar closed above the prior two-bar high — a directional-displacement confirmation) **and** gap-height ratio above threshold. Bearish is the mirror. The `close[1]` condition is the same idea as the Quant script's "directional middle candle" filter on [[concepts/Fair-Value-Gap]], expressed as a close-vs-prior-high test rather than a body-color test.
2. **Auto threshold = cumulative-mean significance filter.** The height filter can be a fixed percentage OR an **"Auto"** mode that uses cumulative-mean analysis to keep only the more volatile (significant) gaps — the same adaptive-baseline concept documented as "cumulative mean of abs bar-delta% × 2" from the SMC source. Optional; can be a plain fixed % instead.
3. **Mitigation-aware display.** By default draws only **unmitigated** gaps (clean chart). Optionally shows mitigation levels — the *lower* extremity for bullish gaps, *upper* for bearish (the level price must reclaim to mitigate). Consistent with LuxAlgo's aggressive "retire touched gaps" philosophy already noted as a contradiction on the FVG concept page.
4. **"Dynamic" mode tracks evolved/mitigated gaps.** Rather than deleting a gap the moment it's touched, Dynamic mode keeps monitoring how a partially-mitigated gap develops — closer to the Quant script's "partial fill = entry, not death" lifecycle.
5. **Dashboard: fill % + average mitigation duration (bars).** The standout feature — on-chart table showing what fraction of gaps have filled and the average bars-to-mitigation. New quantitative angle for FVG work here.
6. **Alerts fire on fill.** Built-in notification when a gap becomes filled.
7. **MTF.** Custom timeframe selection — detect gaps on a chosen timeframe (incl. higher than the chart), same [[concepts/Multi-Timeframe-Analysis]] projection idea as the SMC implementation.

## Detailed Notes

### Detection (bullish; bearish mirrors)
- `low > high[2]` — current low above the high of two bars ago (the 3-candle non-overlap that defines the gap).
- `close[1] > high[2]` — the middle candle closed above the prior two-bar high (directional displacement gate).
- gap-height ratio `> threshold%` — size filter, fixed % or Auto (cumulative-mean).

### Settings exposed
- **Threshold %** — minimum gap-height ratio.
- **Auto threshold** toggle — swaps the fixed % for the cumulative-mean significance filter.
- **Unmitigated levels count** — how many recent unmitigated gaps to keep drawn.
- **Mitigated levels** display option — show/hide the mitigation extremity level.
- **Custom timeframe** — MTF detection source.

### Two ways to trade it (per the description)
- **Contrarian:** enter on fill confirmation (fade into the imbalance as it fills).
- **Trend-following:** treat gap identification itself as a direct continuation signal.

## Actionable Insights
- **Port target for the chart tool:** add a fill-% and average-bars-to-mitigation readout to `tools/fvg.js`'s FVG rendering — the dashboard statistic is cheap to compute from zones we already track and would make FVG context quantitative rather than binary. Fits [[analyses/FVG-FBG-Fibonacci-Chart-Roadmap]] (FF-2 quality-gated FVG detection).
- The `close[1] > high[2]` directional gate is a lighter-weight alternative to the ATR-size + body-color filter already ported in `detect_fvg_pullback()` — worth noting as an option, not a replacement.

## Contradictions with Existing Wiki
No new contradiction. The existing FVG-page contradiction (LuxAlgo's **wick-through** mitigation vs the Quant script's **close-through** lifecycle) still stands; this indicator's optional **"Dynamic"** mode partially bridges the gap by continuing to track a touched gap instead of deleting it outright — worth flagging as a *softening* of the pure-visualizer stance rather than a conflict.

## Pages Updated
- [[concepts/Fair-Value-Gap]] — added the standalone indicator's variant (dashboard fill%/avg-duration, Dynamic mitigation, `close[1]` directional gate).
- [[entities/LuxAlgo]] — added this as a second ingested contribution.
