---
title: "Pine Script — BOS & FVG Pullback Signals (Quant)"
category: source
tags: [pine-script, fvg, fair-value-gap, smc, pullback-entry, rejection-wick, atr-filter, tradingview]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [concepts/Fair-Value-Gap, concepts/Market-Structure-CHOCH-BOS, strategies/Supply-Demand-Zone-Trading, sources/Trend-Lines-by-Kris-Pine]
---

# Pine Script — BOS & FVG Pullback Signals

## Metadata
- Author: © Quant (TradingView)
- License: Mozilla Public License 2.0
- Format: Pine Script v6 indicator, `overlay=true`, max 100 boxes
- Ingested: 2026-07-03 (pasted source code)

## Key Takeaways
1. **Title is misleading — there is no BOS logic in the code.** Despite being named "BOS & FVG Pullback Signals", the script contains zero market-structure/swing-break detection; it is purely an FVG detector plus a pullback-rejection entry signal. (Contradictions are gold: don't assume a script does what its title claims.)
2. **Quality-filtered FVG definition** — beyond the classic 3-candle gap (`low > high[2]` bullish / `high < low[2]` bearish), it requires (a) the middle candle to be *directional* (`close[1] > open[1]` for bullish — the gap must come from real momentum, not noise) and (b) gap size > 0.5 × ATR(14) — an ATR-scaled minimum that auto-adapts to each symbol's volatility instead of a fixed %.
3. **One active FVG per side, newest wins** — a fresh bullish FVG replaces the previous one; the script deliberately tracks only the most recent unmitigated gap per direction, keeping the signal focused on current structure.
4. **Mitigation rule** — a bullish FVG is invalidated only when a close falls below the gap's *bottom* (fully closed through); partial fills leave it active. Bearish mirror: close above the gap's top.
5. **The signal is a 3-condition pullback rejection**, not a gap fill: price's low must touch inside the bull FVG zone, the candle must close back *above* the zone top with a dominant lower wick (`close − low > high − close`), and the bar must have *opened* above the zone top (`open > bullFvgTop` — excludes bars that gapped down into the zone; a genuine pullback-and-reject, not a breakdown). One signal per FVG — the zone is consumed after firing.

## Detailed Notes
- ATR: Pine's `ta.atr(14)` = Wilder/RMA smoothing (matches this project's `_atr_series`).
- Signal ordering per bar: new-FVG assignment → mitigation check → signal check → zone consumed if signal fired.
- **Same-bar-signal quirk (found while testing the port)**: the zone top is defined as candle 3's *own low*, so the touch condition (`low <= top`) is trivially true on the formation bar. If candle 3 happens to be hammer-shaped (close near high, dominant lower wick), the script fires BUY on the very bar that created the FVG and consumes the zone — no pullback ever happened. Harmless-to-useful in practice (a momentum gap + hammer close is itself bullish) but it means not every "BUY" label marks a genuine pullback rejection. The Python port reproduces this faithfully.
- Box drawing/extension is cosmetic; boxes are orphaned (never deleted) when zones invalidate — display quirk only, no logic impact.
- Sell side is the exact mirror: touch inside bear FVG from below, close back under the zone bottom, dominant upper wick, open below the zone bottom.

## Actionable Insights
- **Ported to Python (2026-07-03)**: `detect_fvg_pullback()` in `tools/scanner_templates.py` — same state machine (directional middle candle, ATR-scaled size, newest-per-side, full-mitigation invalidation, 3-condition rejection signal, one signal per zone). Wired as the 8th check ("FVG") in the Early Reversal validation layer: a recent bullish FVG rejection passes; a recent bearish FVG rejection raises a ⚠ warning.
- Complements the existing `tools/fvg.js` chart module (which draws *all* zones, unfiltered): this script's contribution is the entry *signal* layered on top — demand-zone pullback logic from [[strategies/Supply-Demand-Zone-Trading]] applied to the FVG flavor of zone.
- The `open > zone top` condition is a small but smart fakeout guard — the same trapped-trader logic as the body-close rule in [[sources/Trend-Lines-by-Kris-Pine]]: both refuse to treat "price already broke through" as "price is rejecting."

## Contradictions with Existing Wiki
- **Name vs content** (see takeaway 1) — filed under FVG, not market structure; anyone searching the wiki for BOS logic should use [[concepts/Market-Structure-CHOCH-BOS]] and its Python port instead.
- None substantive: the FVG definition matches the one sketched on [[concepts/Market-Structure-CHOCH-BOS]] (imbalance price returns to fill), and the rejection-entry logic agrees with [[strategies/Supply-Demand-Zone-Trading]]'s zone-touch entry rules.

## Pages Updated
- [[concepts/Fair-Value-Gap]] — created (first dedicated FVG concept page; this script + the existing `tools/fvg.js` module are its sources)
- [[concepts/Market-Structure-CHOCH-BOS]] — FVG mention now links to the new concept page
- `tools/scanner_templates.py` — Python port + validation-layer wiring (code, not wiki)
