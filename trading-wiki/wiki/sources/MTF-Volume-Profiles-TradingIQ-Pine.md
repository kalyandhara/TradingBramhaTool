---
title: "Pine Script — Multi Timeframe Volume Profiles [TradingIQ] (KioseffTrading)"
category: source
tags: [pine-script, volume-profile, delta-profile, poc, value-area, multi-timeframe, order-flow, tradingview]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [concepts/Volume-Profile, concepts/Multi-Timeframe-Analysis, concepts/Order-Flow, sources/YT-MultiChart-TradingView-Alternative]
---

# Pine Script — Multi Timeframe Volume Profiles [TradingIQ]

## Metadata
- Author: © KioseffTrading (TradingIQ, TradingView)
- License: Mozilla Public License 2.0
- Format: Pine Script v6 indicator, `overlay=true`, up to 500 boxes/labels/lines + 100 polylines
- Ingested: 2026-07-03 (pasted source code)

## Key Takeaways
1. **Up to five simultaneous HTF volume profiles** (defaults 30m / 1h / 4h, optional 1D / 1W), each drawn as a synthetic HTF candle + its profile at a configurable offset right of the live chart — the on-chart embodiment of [[concepts/Multi-Timeframe-Analysis]]: where value sits on each timeframe at a glance, POC/VA confluence across timeframes visible directly.
2. **Lower-timeframe volume sourcing** — each profile is built not from chart-TF bars but from `request.security_lower_tf` 1-minute H/L/V data within the current HTF period. Much finer allocation granularity than binning chart-TF bars; the profile's shape converges toward the true intraperiod distribution.
3. **Two models: Traditional and Delta.** Traditional stacks buy and sell volume per price row; Delta signs each LTF bar's volume by direction and shows net per row. Direction = `sign(close − close[1])` on the LTF — except on true tick charts (`"1T"`), where it upgrades to real bid/ask matching (`close == ask` → buy, `close == bid` → sell). A graceful degradation hierarchy: use real order-flow data when the feed has it, tick-rule approximation otherwise (the same tick-rule delta idea documented in [[concepts/Order-Flow]]).
4. **POC + 70% value area per profile** — POC = highest-volume row; VA expands outward from the POC, alternately stepping one row up and one row down per iteration until 70% of total volume is enclosed, labeling VAH/VAL.
5. **Current-price dot** — marks which profile row the live close sits in for each timeframe, making "above/below value per timeframe" readable instantly.

## Detailed Notes
- **Even-split allocation (weaker than our existing module)**: each LTF bar's volume is divided *equally* across all rows its H–L range touches (`div = V / (rows spanned)`). `tools/volume_profile.js` allocates by *proportional range overlap* per bin, which is strictly more accurate — the Pine's shortcut over-weights rows the bar barely clipped. Kept in mind for the port (see below).
- **VA expansion is order-based, not volume-greedy**: alternating up/down one row per iteration regardless of which neighbor holds more volume. The standard market-profile rule (and `volume_profile.js`) expands toward the *higher-volume* neighbor; the alternating shortcut can misplace VAH/VAL on asymmetric profiles. Flagged as a mild methodological contradiction.
- Bar width normalization: per-row bars normalized to a 1–16 bar-width scale against the profile's min/max row volume.
- All drawing is done once on `barstate.islast` (delete-and-redraw each update) — display-layer only.
- `formTF()` pretty-prints minute counts as hours; optional HTF-close countdown timer per profile.

## Actionable Insights
- **Ported to Python (2026-07-03)**: `compute_volume_profile_levels()` in `tools/scanner_templates.py` — POC/VAH/VAL over the trailing window plus the script's *delta* model (per-bin signed volume). Two deliberate deviations, both upgrades and both documented in the docstring: proportional-overlap allocation (from `volume_profile.js`) instead of even split, and volume-greedy VA expansion instead of alternating. Wired as the 9th validation check ("Profile"): close accepted above the POC passes (with above-entire-VA and buy-side-delta-at-POC noted when true); close below VAL raises a ⚠ "no volume acceptance yet" warning.
- The delta-at-POC reading is the actionable order-flow nugget for daily screening: a reversal candidate whose highest-volume node was built on net *buying* is a different animal from one whose node is where sellers unloaded.
- MTF profile stacking (several lookback windows' POC/VA side by side) is a natural future upgrade for the chart dashboard's existing `drawVolumeProfile()` — noted, not built.

## Contradictions with Existing Wiki
- **Allocation + VA-expansion shortcuts vs `volume_profile.js`/VOLUME_PROFILE_MODULE.md** (see Detailed Notes) — the wiki's documented methods are more accurate on both counts; the Pine's value is the MTF stacking, delta model, and LTF sourcing, not its binning math. Port uses the better math.
- None otherwise — POC/VA definitions match [[concepts/Initial-Balance]]'s value-area usage and the Order-Flow page's framing.

## Pages Updated
- [[concepts/Volume-Profile]] — created (first dedicated volume-profile concept page; this script + `tools/volume_profile.js` are its sources)
- [[concepts/Multi-Timeframe-Analysis]] — cross-link added (MTF value confluence as the volume-profile application of the framework)
- `tools/scanner_templates.py` — Python port + validation-layer wiring (code, not wiki)
