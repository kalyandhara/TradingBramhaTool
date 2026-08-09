---
title: "Fair Value Gap (FVG)"
category: concept
tags: [fvg, fair-value-gap, imbalance, smc, ict, pullback-entry, rejection-wick, demand-zone, mtf, auto-threshold, luxalgo]
created: 2026-07-03
updated: 2026-08-09
sources: 7
related: [concepts/Market-Structure-CHOCH-BOS, strategies/Supply-Demand-Zone-Trading, concepts/Support-Resistance, concepts/Trend-Lines, concepts/Order-Blocks, concepts/Multi-Timeframe-Analysis, concepts/Fair-Value-Breaker-FBG, concepts/Fibonacci-Retracement, concepts/FPV-Flow-Price-Volume-Ownership, analyses/FVG-FBG-Fibonacci-Chart-Roadmap, sources/FVG-LuxAlgo-Pine, sources/FVG-DGT-Pine, sources/FVG-Zeiierman-MTF-Pine]
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

### LuxAlgo standalone FVG indicator — mitigation statistics dashboard (2026-07-22)
LuxAlgo also ships a **dedicated FVG-only** indicator ([[sources/FVG-LuxAlgo-Pine]], separate from the SMC superset) that adds features the superset lacks:
- **Detection uses a `close[1] > high[2]` directional gate** alongside `low > high[2]` and the size threshold — the middle candle must have *closed* above the prior two-bar high. Same intent as the directional-middle-candle filter above, expressed as a close-vs-prior-high test.
- **Dashboard of fill % + average bars-to-mitigation** — turns FVG mitigation from binary (filled/unfilled) into a measurable expectancy ("how many bars until an FVG of this type typically fills"). Genuinely new quantitative angle; a port target for `tools/fvg.js`.
- **"Dynamic" mitigation mode** — instead of deleting a gap the instant it's touched, keeps tracking how a partially-mitigated gap evolves. Softens LuxAlgo's usual wick-through-deletes-the-gap stance (see the contradiction callout above) toward the Quant script's "partial fill = entry, not death" lifecycle.
- **Mitigation-level display** — optional draw of the level price must reclaim to mitigate (lower extremity for bullish, upper for bearish). Alerts fire on fill. Auto threshold (cumulative-mean) and custom-timeframe (MTF) options as in the superset.

### DGT variant — fill logic as a user setting + LTF/intrabar detection (2026-07-22)
"Fair Value Gaps by DGT" ([[sources/FVG-DGT-Pine]], by [[DGT]]) contributes two things the LuxAlgo scripts don't:
- **Four selectable fill definitions** — the user picks what counts as "filled": **Any Touch** (price reaches the near edge) · **Midpoint Reached** (50% / consequent-encroachment level) · **Wick Sweep** (a wick fully crosses) · **Body Beyond** (a body/close pushes fully through). This *parameterizes* the mitigation-rule contradiction below: **Any Touch = LuxAlgo's aggressive wick-through** and **Body Beyond ≈ the Quant script's close-through invalidation** are just the two ends of one dial. The right way to port this is a `fill_mode` parameter, not a hard-coded rule.
- **Three-source detection: current TF + HTF + LTF/intrabar** — LuxAlgo only projects gaps *down* from a higher timeframe; DGT also reads gaps on a *lower* timeframe (intrabar), auto-selecting the LTF from chart resolution, surfacing imbalances hidden inside the current bar.
- Also: continuous **unfilled → partially repaired → fully resolved** lifecycle with live fill %, and hover-tooltips anchored on the gap midpoint.

### Zeiierman variant — volume-effort + DSP trend filter inside the gap (2026-07-22)
"Multitimeframe FVG" ([[sources/FVG-Zeiierman-MTF-Pine]], by [[Zeiierman]]) layers *context* onto the standard gap rather than changing the gap primitive:
- **Bull/Bear Power inside the box** — volume-weighted sub-bars estimate buy vs sell effort per gap (Buy ≈ low→close, Sell ≈ high→close), colored by dominance. First source to put a *volume/effort* read directly on the imbalance zone — operationalizes the price+volume half of [[concepts/FPV-Flow-Price-Volume-Ownership]] at the single-gap level. (Estimates from OHLCV geometry, not real bid/ask.)
- **Butterworth two-pole low-pass trend filter** (Passband Ripple dB, Cutoff 0–0.5) classifies each FVG **trend-aligned vs countertrend** — mechanizes "only trade FVGs with structure" with a DSP smoother instead of an EMA/pivot. Notable but not necessary to port (reuse an existing trend gate).
- **Wick-sensitivity impulse filter** — candidate wick sizes vs a running average; another adaptive significance filter (cousin of LuxAlgo's cumulative-mean and the Quant ATR×0.5), but keyed on *wick* size.
- **"Mitigated on Mid" toggle** — midpoint touch vs full closure; the Midpoint↔Body-Beyond choice from the DGT fill-mode spectrum exposed as a boolean. HTF *or* LTF selection + optional active-gap table as in the others.

> [!contradiction] Mitigation rule differs from the Quant-script lifecycle above
> This page's lifecycle (from the Quant script) invalidates an FVG only on a **close fully through** the far side — wick penetration is the entry, not the death of the zone. The **LuxAlgo** implementation deletes the gap on any **wick through** the far side (`low < bottom` bull / `high > top` bear). Same primitive, different lifecycle: LuxAlgo is a pure *visualizer* that wants clean charts, so it retires touched gaps aggressively; the Quant script is an *entry-signal engine* that needs the zone to survive the touch it trades. Pick the close-through rule when the FVG must survive to produce a pullback entry; the wick-through rule when you only want currently-untouched gaps on screen.
>
> **Resolution (2026-07-22):** the [[sources/FVG-DGT-Pine|DGT indicator]] treats fill logic as a *setting* with four definitions — **Any Touch** (= LuxAlgo wick-through) at one end, **Body Beyond** (= Quant close-through) at the other, with Midpoint and Wick Sweep in between. Both rules are valid endpoints of one configurable spectrum; model it as a `fill_mode` parameter rather than choosing a side.

### MEASURED (2026-08-09): the "price magnet" is almost entirely width and distance

The claim every FVG explainer makes — *"the market seeks balance and will eventually pull back to fill the gap"* — is now tested. [fvg_fill_study.py](tools/fvg_fill_study.py), 20 NSE large-caps, 5y daily, **2,014 size-gated gaps**, each paired with a **matched placebo**: a zone of identical width at an identical distance from price, anchored at a random unrelated bar.

The control is the whole point. A bare "89% of gaps get filled" is not evidence, because whether price returns to a band is driven mostly by **how wide the band is and how far it sits from price** — facts that have nothing to do with imbalance.

| Fill definition | Real | Placebo | Δ | p | Median bars (real vs placebo) |
|---|---|---|---|---|---|
| Any Touch | 89.2% | 87.0% | **+2.1pp** | 0.036 | 2 vs 2 |
| Midpoint | 79.8% | 78.0% | +1.9pp | 0.142 | 4 vs 4 |
| Wick Sweep | 71.7% | 69.6% | +2.2pp | 0.128 | 7 vs **6** |
| Body Beyond | 65.8% | 63.3% | +2.6pp | 0.087 | 9 vs 9 |

> [!key-insight] The fill statistic is real; the *gap's* contribution to it is ~2 percentage points and does not survive scrutiny
> Three findings, and each one weakens the claim further:
>
> **1. Extending the horizon — which is what "eventually" asks for — kills the effect.** At 120 bars the deltas collapse to **+0.3 to +1.4pp, every p ≥ 0.32**. Wait long enough and almost everything gets touched, so the gap's marginal contribution tends to zero. The claim is *weakest* on exactly the timescale it invokes.
>
> **2. There is no speed effect at all.** Median bars-to-fill is identical in every cell, and for Wick Sweep the **placebo is faster** (6 vs 7). "Magnet" implies pull. Nothing here pulls.
>
> **3. Wider gaps are not more magnetic.** Stratified by width (n≈665 each), no class is significant (p 0.20–0.50). Wide gaps fill *less* often in absolute terms (56.9% vs 72.6% for narrow) — pure geometry, the far edge is further away — and the delta over placebo does not grow with width. "Bigger imbalance, stronger magnet" gets no support.
>
> The lone p=0.036 (Any Touch, 40 bars) is the loosest definition, fails a multiple-comparison correction (4 tests → Bonferroni 0.0125), and does not replicate at 120 bars (p=0.65). Read it as noise.

**What this does and does not invalidate.** It tests the *mechanism* claim — gaps as magnets — and finds essentially nothing beyond location. It does **not** test whether a *pullback-rejection entry* at a gap makes money: a zone can be a useful place to look for a rejection even if its fill rate is unremarkable. That is a forward-return question for [[analyses/Backtest-Harness]] and has not been run. Keep the two apart; conflating them is how a null result gets over-read in either direction.

### Retail-friendly actionable rules (2026-07-22 framework)
A condensed rule set from [[sources/FVG-FBG-Fibonacci-Retail-Framework]], consistent with the lifecycle above:
- **Trade only when:** market structure supports the direction · a **liquidity sweep** happened before the FVG · price returns to the zone · **volume confirms** the displacement.
- **Entry:** 50% of the FVG (optimal) or the full zone (aggressive); SL below/above the sweep or displacement candle.
- **Exit:** TP1 return to origin · TP2 next liquidity pool · TP3 opposite-side FVG.
- **Do NOT trade:** no displacement · no sweep · inside an HTF FVG (chop) · during news · low-volume sessions.
- **FPV (price+volume) strength read:** Price↑+Vol↑ = strong long FVG; Price↓+Vol↑ = strong short; either on falling volume = weak. See the two-component FPV note in [[concepts/FPV-Flow-Price-Volume-Ownership]].

### Fibonacci confluence
Draw the Fib across the displacement candle (low→high for a bullish FVG):
- **0.50 ≈ the FVG midpoint** — the cleanest continuation entry (SL below the displacement candle; TP at Fib 1.0 / next liquidity).
- **0.618 = the "reaction test"** — a clean rejection there confirms a strong FVG; slicing through 0.618 on weak volume signals the imbalance is failing (and may become an FBG).
- **1.272 / 1.618 / 2.0 extensions** = mechanical take-profit zones (they tend to align with liquidity pools / opposite-side FVGs).
The chart's [fibonacci.js](tools/fibonacci.js) already computes these levels; scoring them against FVG zones is planned as FF-1 in [[analyses/FVG-FBG-Fibonacci-Chart-Roadmap]].

### When an FVG fails → FBG
A returning price that **closes through the opposite boundary** invalidates the FVG *and* flips it into a **breaker** — a reversal zone. That failure mode is its own concept: [[concepts/Fair-Value-Breaker-FBG]].

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
- **Screenable since 2026-08-09**: [`scan_fvg_pullback`](tools/scanner_templates.py:2660) — registered **"FVG Pullback"** (category Entry, Entry Trigger family). Until then `detect_fvg_pullback` existed only as one boolean inside the Early Reversal layer (`checks["FVG"]`), so a gap setup could be *confirmed* on a name you were already looking at but never *found* — the recurring orphaned-detector pattern. The wrapper emits entry/stop/target with the stop referenced to the gap the signal fired from, which required `detect_fvg_pullback` to stop discarding that zone on the signal (additive keys `buy_signal_zone` / `sell_signal_zone`; the existing consumer reads only `*_bars_ago`). Fired on 8/12 large-caps over 2y. **Unmeasured** — no harness run.
- **The entry is deliberately not the popular one.** Retail instruction is to rest a limit order *inside* the zone; that fills you on the way through in exactly the cases where the gap fails, so the fill is guaranteed precisely when it is unwanted. This requires price to close back **above** the zone with a dominant lower wick — fewer trades, worse average price, only gaps that held.
- **Fill-rate study**: [`fvg_fill_study.py`](tools/fvg_fill_study.py) — the measurement behind the callout above. `python tools/fvg_fill_study.py`.
- **Used as a composition leg**: [[strategies/4H-Wick-Zone-FVG-Setup]] (parked, intraday reference) places the gap as an *entry location after a confirmed BOS* rather than as a magnet prediction — which is the use the fill study above does not speak against. Its Weekly→Daily translation would reuse `scan_fvg_pullback` directly.
- No live-ticker example yet — annotate an entity page when an FVG rejection fires on a tracked stock.

## Sources
1. [BOS-FVG-Pullback-Signals-Pine](../sources/BOS-FVG-Pullback-Signals-Pine.md) — Pine v6 indicator by Quant (MPL-2.0), ingested 2026-07-03; quality filters, lifecycle rules, and the 3-condition rejection signal are from this script.
2. `tools/fvg.js` (this repo, 2026-06) — prior chart-side FVG zone detection; basic 3-candle definition and fill tracking.
3. [LuxAlgo-Smart-Money-Concepts-Pine](../sources/LuxAlgo-Smart-Money-Concepts-Pine.md) — Pine v5 indicator by [[LuxAlgo]] (CC BY-NC-SA 4.0), ingested 2026-07-16; source for the MTF (`request.security`) detection, auto-threshold significance filter, two-half-box rendering, and the wick-through mitigation variant (contradiction callout above).
4. [FVG-LuxAlgo-Pine](../sources/FVG-LuxAlgo-Pine.md) — LuxAlgo's standalone FVG-only TradingView indicator, ingested 2026-07-22; source for the mitigation-statistics dashboard (fill % + average bars-to-mitigation), the `close[1] > high[2]` directional gate, and the "Dynamic" mitigation mode.
5. [FVG-DGT-Pine](../sources/FVG-DGT-Pine.md) — "Fair Value Gaps by DGT" TradingView indicator by [[DGT]], ingested 2026-07-22; source for the four fill-classification definitions (Any Touch / Midpoint / Wick Sweep / Body Beyond — the mitigation-rule spectrum that resolves the contradiction above) and current-TF + HTF + LTF/intrabar three-source detection.
6. [FVG-Zeiierman-MTF-Pine](../sources/FVG-Zeiierman-MTF-Pine.md) — "Multitimeframe FVG" TradingView indicator by [[Zeiierman]], ingested 2026-07-22; source for the in-gap Bull/Bear Power volume-effort visualization, the Butterworth two-pole trend-alignment filter, the wick-sensitivity impulse filter, and the midpoint-vs-full mitigation toggle.
