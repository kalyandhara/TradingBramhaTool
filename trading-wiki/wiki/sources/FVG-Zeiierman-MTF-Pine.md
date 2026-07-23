---
title: "TradingView — Multitimeframe Fair Value Gap (FVG) [Zeiierman]"
category: source
tags: [pine-script, fvg, fair-value-gap, zeiierman, mtf, htf, ltf, bull-bear-power, volume, butterworth, trend-filter, mitigation, tradingview]
created: 2026-07-22
updated: 2026-07-22
sources: 1
related: [entities/Zeiierman, concepts/Fair-Value-Gap, concepts/Multi-Timeframe-Analysis, concepts/FPV-Flow-Price-Volume-Ownership, sources/FVG-DGT-Pine, sources/FVG-LuxAlgo-Pine, concepts/Trend-Lines]
---

# TradingView — Multitimeframe Fair Value Gap (FVG) [Zeiierman]

## Metadata
- Author: © **Zeiierman** ([[Zeiierman]]), TradingView Wizard
- Source: https://www.tradingview.com/script/5jS51RsP-Multitimeframe-Fair-Value-Gap-FVG-Zeiierman/
- License: open-source (public TradingView script; verify exact terms on the script page before any port)
- Format: TradingView Pine Script overlay indicator
- Ingested: 2026-07-22 (URL fetch)

## Why this matters
The **fourth** FVG indicator ingested this session ([[sources/FVG-LuxAlgo-Pine]], [[sources/LuxAlgo-Smart-Money-Concepts-Pine]], [[sources/FVG-DGT-Pine]] are the others). By now the raw 3-candle definition and MTF projection are well-covered — Zeiierman's value is two ideas none of the others have:
1. **Bull/Bear Power drawn *inside* the gap** — volume-weighted sub-bars showing estimated buy vs sell effort within each FVG box. This is the first source to put a *volume/effort* read directly on the imbalance zone, operationalizing the price+volume half of [[concepts/FPV-Flow-Price-Volume-Ownership]] at the individual-gap level.
2. **Butterworth-filtered trend classification** — a two-pole low-pass filter categorizes each FVG as trend-aligned or countertrend, mechanizing the wiki's "only trade FVGs with structure" rule with a DSP smoother instead of an EMA/pivot.

## Key Takeaways
1. **Bull/Bear Power (the standout).** Each FVG box is subdivided into volume-weighted sub-bars: **Buy Volume ≈ effort from low→close**, **Sell Volume ≈ effort from high→close**, colored proportionally by dominance. Lets you see whether the imbalance was built by dominant buyers or sellers — a per-gap conviction read. Note: these are *estimates* from OHLCV geometry (no real bid/ask), the same close-position-within-range proxy used elsewhere in retail volume tooling.
2. **Butterworth two-pole low-pass trend filter.** A smoothed trendline (controls: **Passband Ripple in dB**, **Cutoff Frequency 0–0.5**) classifies FVGs as trend-aligned vs countertrend. Trend-aligned gaps are the continuation setups; countertrend gaps are the ones the retail framework says to skip (no structure support). A more sophisticated smoother than the EMA-21/pivot trend gates the wiki uses elsewhere ([[concepts/Trend-Lines]], [[concepts/EMA]]).
3. **Wick-sensitivity impulse filter.** Measures candidate-candle wick sizes against a **running average** and drops gaps below a sensitivity threshold — an adaptive significance filter, cousin to LuxAlgo's cumulative-mean auto-threshold and the Quant script's ATR×0.5. Uses *wick* size (not body/ATR) as the impulse proxy.
4. **Midpoint-or-full mitigation toggle ("Mitigated on Mid").** User chooses whether a midpoint touch or full closure retires the gap — another point on the DGT fill-mode spectrum ([[sources/FVG-DGT-Pine]]): this is the Midpoint-vs-Body-Beyond choice exposed as a boolean.
5. **True HTF *or* LTF selection.** `request.security()` pulls OHLCV from any chosen timeframe, higher or lower than the chart — matches DGT's HTF+LTF capability (vs LuxAlgo's HTF-only projection).
6. **FVG table.** Optional side-panel listing active (unmitigated) gaps with timestamps and color-coding — same watchlist-overlay idea as the LuxAlgo dashboard / DGT.

## Detailed Notes
- Detection is wick-based 3-candle non-overlap (gap between candle-1 and candle-3 wicks), consistent with every other FVG source here.
- The differentiation is entirely in **context layers** bolted onto the standard gap: volume-effort (bull/bear power), trend classification (Butterworth), and impulse filtering (wick-vs-running-average) — not in the gap primitive.
- Butterworth cutoff 0–0.5 is normalized frequency (Nyquist = 0.5); lower cutoff = smoother/slower trendline. Passband ripple in dB trades flatness for roll-off sharpness. This is genuine DSP, unusual in retail FVG scripts.

## Actionable Insights
- **Bull/Bear Power is the highest-value port idea** for this repo's chart: `tools/fvg.js` already draws zones and this project already computes volume; adding a per-gap buy/sell-effort estimate (close-position-in-range × volume) would give each FVG a conviction tint and feed the FPV read directly. Fits FF-5 (price+volume gate) in [[analyses/FVG-FBG-Fibonacci-Chart-Roadmap]].
- **Trend-alignment classification** is worth adopting conceptually (tag each FVG trend-aligned/countertrend) but we'd likely reuse an existing trend gate (EMA/structure) rather than port a Butterworth filter — flag the filter as *notable but not necessary*.

## Contradictions with Existing Wiki
No new contradiction. The midpoint-vs-full mitigation toggle is consistent with the DGT-based resolution already recorded on [[concepts/Fair-Value-Gap]] (fill logic is a configurable spectrum, not a fixed rule).

## Pages Updated
- [[concepts/Fair-Value-Gap]] — added Zeiierman variant (bull/bear power, Butterworth trend filter, wick-sensitivity impulse filter, midpoint mitigation toggle).
- [[Zeiierman]] — new author entity.
