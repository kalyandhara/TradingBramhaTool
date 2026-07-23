---
title: "FVG + FBG + Fibonacci Chart Roadmap"
category: analysis
tags: [roadmap, fvg, fbg, breaker-block, fibonacci, chart, confluence, fpv, smc, dashboard]
timeframe: milestone-plan
created: 2026-07-22
updated: 2026-07-22
sources: 1
related:
  - sources/FVG-FBG-Fibonacci-Retail-Framework.md
  - concepts/Fair-Value-Gap.md
  - concepts/Fair-Value-Breaker-FBG.md
  - concepts/Fibonacci-Retracement.md
  - analyses/Dashboard-UI-Roadmap.md
---

# Analysis: FVG + FBG + Fibonacci Chart Roadmap

## Thesis
The framework ([[sources/FVG-FBG-Fibonacci-Retail-Framework]]) wants three chart capabilities working together: quality-gated **FVG** zones, a **FBG** (breaker) detector, and **Fibonacci confluence** that resolves entries/stops/targets mechanically (0.50 midpoint · 0.618–0.705 breaker retest · 1.272/1.618 targets). The chart already has two of the three primitives — `fvg.js` and the newly-shipped `fibonacci.js` — so most of this is **wiring existing pieces into confluence**, plus one genuinely new detector (FBG). Feeds [[analyses/Dashboard-UI-Roadmap]] Phase 2.

## Current State (grounded, 2026-07-22)

| Framework piece | Nearest existing surface | Gap |
|---|---|---|
| **FVG zones** | [fvg.js](tools/fvg.js) `FVG.compute()` — 3-candle detection + fill tracking + size filter, drawn via `drawFVG()` | Detects **raw gaps only**. No displacement/ATR gate, no liquidity-sweep, no rejection-entry — the richer logic exists in `detect_fvg_pullback()` (Python scanner) but was never ported to the chart |
| **Fibonacci levels** | [fibonacci.js](tools/fibonacci.js) `FIB.*` (shipped this session) — 0.236–0.786 grid + 1.272/1.618 extensions, `scoreLevels()` confluence vs Volume Profile + projection, entry/stop/target plan | **Does not know about FVG zones.** `scoreLevels()` currently scores against VP nodes only |
| **FBG (breaker)** | — | **Nothing.** No detector, no concept until [[concepts/Fair-Value-Breaker-FBG]] (this ingest) |
| **FPV (price+volume) confirmation** | Volume is on every chart; OI Momentum is a positioning cousin | The price+volume "strong/weak FVG" and "strong/fake breaker" readout is not wired to the FVG/FBG overlays |
| **Retail checklist** ("2+ NO → skip") | — | Not surfaced; same veto-stack shape as the [[strategies/Crash-Proof-3-Filter-System]] gate |

> [!key-insight] Two of three primitives already exist
> `fibonacci.js` already computes exactly the levels the framework names (0.5 / 0.618 / 1.272 / 1.618) and already has a zone-confluence scorer. FVG-zone scoring is an *extension of `scoreLevels()`*, not new math. The only greenfield piece is FBG detection.

## Conclusion — five items

Sequenced cheapest-and-most-grounded first. Effort in the house style of [[analyses/Dashboard-UI-Roadmap]].

### FF-1 — FVG midpoint ↔ Fib 0.50 confluence (highest ROI, lowest risk)
**Goal:** `fibonacci.js` scores its levels against **FVG zones** the same way it scores against Volume-Profile nodes, so a Fib 0.50 that lands on an FVG midpoint (or 0.618 on an FVG boundary) is flagged as stacked confluence and can drive the entry.
- **Data:** both modules already loaded on the chart (`FVG.compute()`, `FIB.scoreLevels()`). Add an FVG-zone match arm to `scoreLevels()` alongside the existing VP arm.
- **UI:** existing Fibonacci overlay — a level that coincides with an FVG zone draws solid/labelled (as VP hits already do), and the trade-plan panel names the FVG.
- **Effort:** 2–3h; `fibonacci.js` + a small wiring change in `chart_dashboard.html`. No new endpoint.
- **Ships value:** the framework's #1 mapping (FVG midpoint = Fib 0.50) becomes mechanical, reusing the confluence engine built this session.

### FF-2 — Upgrade chart FVG detection to the quality-gated definition
**Goal:** bring `fvg.js` up to the wiki's own [[concepts/Fair-Value-Gap]] standard — directional/displacement middle candle + ATR-scaled minimum size + newest-unmitigated-per-side, matching the `detect_fvg_pullback()` port.
- **Data:** logic already specified and Python-ported; translate the gates into `fvg.js`.
- **UI:** fewer, higher-quality zones; optional "raw gaps" toggle to keep current behaviour.
- **Effort:** 3–4h. Risk: changing detection alters what every downstream FVG feature sees — keep the raw mode behind a flag.
- **Ships value:** removes the raw-gap noise the framework explicitly warns against ("no displacement → don't trade").

### FF-3 — FBG (breaker) detector + overlay *(the one greenfield piece)*
**Goal:** detect when an FVG fails (price closes through the opposite boundary) and flip it into a breaker zone, drawn distinctly from live FVGs, per [[concepts/Fair-Value-Breaker-FBG]].
- **Data:** extend `fvg.js` — track each zone's lifecycle; on a **close** beyond the opposite boundary, reclassify the zone as an FBG and record the break bar + break volume.
- **UI:** new overlay (breaker zones in a distinct colour) + the FBG's own info line; wire into the indicator registry as a toggle like `fvg`.
- **Effort:** 4–6h. The lifecycle tracking is the substance; rendering reuses the FVG box path.
- **Ships value:** unlocks the entire reversal half of the framework, which has no representation on the chart today.

### FF-4 — FBG retest ↔ Fib 0.618–0.705 confluence + strong/weak grading
**Goal:** once FBG zones exist (FF-3), score the Fib retracement of the breaking swing; a retest into **0.618–0.705 with a volume spike** grades a **strong** breaker, a stall at **0.382** grades **weak** (expect continuation).
- **Data:** FBG zones from FF-3, Fib levels from FF-1's extended scorer, volume already on the chart.
- **UI:** the FBG info line shows Strong/Weak with the retest level and volume read; entry/stop/target only when Strong.
- **Effort:** 2–3h once FF-1 and FF-3 land.
- **Ships value:** the framework's highest-probability reversal entry, mechanised.

### FF-5 — FPV (price+volume) confirmation + retail checklist gate
> [!key-insight] Core shipped 2026-07-22 (price+volume leg + actionable entry)
> The actionable **buy/sell signal with the FPV price+volume read** is now live on the chart — see Outcome below. What shipped: the pullback-rejection entry engine (`FVG.signals()`) + STRONG/WEAK grading by displacement volume + Zeiierman bull/bear power, surfaced as a marker + panel. What's still open under FF-5: the full **7-point retail checklist** ("2+ NO → skip") and the **news-in-10-min** calendar leg.
**Goal:** a small panel emitting the framework's price+volume reads (strong/weak FVG; strong/fake breaker) and the 7-point retail checklist with the **"2+ NO → skip"** verdict.
- **Data:** price+volume (chart), displacement/sweep/structure derivable from FF-2/FF-3; "no news in 10 min" needs a calendar feed (may be out of scope — mark it manual).
- **UI:** a checklist chip like the crash-proof gate; shown after the confluence, never before.
- **Effort:** 3–4h; the news-calendar leg is the only uncertain dependency.
- **Ships value:** the veto gate that the framework claims removes 70% of bad trades — the honest "should I take this at all" layer on top of the mechanical entries.

## Evidence For
- **Two of three primitives already shipped** — FF-1 and FF-4 are confluence wiring on top of `fibonacci.js` + `fvg.js`, not new engines.
- **The Fib levels the framework names are already computed** — 0.5/0.618/1.272/1.618 all exist in `fibonacci.js`.
- **The user asked for exactly this** — FVG/FBG in the chart with Fibonacci's role spelled out.

## Evidence Against
- **FF-2 changes detection under existing features.** Anything reading FVG zones today (including FF-1) shifts when the quality gates land — hence the raw-mode flag and the sequencing (FF-1 before FF-2 is deliberate: prove confluence on current zones, then tighten).
- **Overlay crowding.** FVG + FBG + Fibonacci + Volume Profile + projection on one chart is a lot of ink; z-index and toggle discipline (already established for the existing overlays) must hold, and defaults should not turn everything on at once.
- **"Removes 70% of bad trades" is unmeasured** — the checklist gate (FF-5) is a discipline aid, not a validated filter; do not present it as backtested. Same Phase 3 backtest caveat as the other roadmaps.
- **News-calendar dependency (FF-5)** may not have a clean data source; ship the checklist with that leg manual rather than block the feature.

## Action Taken / Plan
- **Sequencing rule (inherited):** don't start FF-N until FF-(N−1) ships and gets one session of live use. FF-1 first (extends this session's `fibonacci.js`); FF-3 (FBG) is the one greenfield build and gates FF-4.
- **Owner:** user-driven; not started. **FF-1 recommended first.**
- **Relationship to the main roadmap:** concrete expansion of [[analyses/Dashboard-UI-Roadmap]] Phase 2 for the FVG/FBG/Fibonacci theme; sibling to [[analyses/Decision-Support-Gating-Roadmap]].

## Outcome (fill in later)
- _2026-07-22: filed from the FVG/FBG/Fibonacci framework ingest. Nothing built yet._
- **2026-07-22 (build): FF-5 core + FF-2 rejection-entry shipped.** `tools/fvg.js` gained `FVG.signals()` (v1.1.0) — a faithful JS port of the Python `detect_fvg_pullback()` state machine (ATR×0.5 displacement gate + directional middle candle + close-through invalidation + open-beyond/touch/dominant-wick rejection entry), plus a **price+volume FPV read** (2-component chart variant of [[concepts/FPV-Flow-Price-Volume-Ownership]]): displacement volume vs 20-bar average → STRONG/WEAK, and Zeiierman-style bull/bear power (close-position-in-range). `tools/chart_dashboard.html` renders it as a BUY/SELL arrow marker (bright=live, muted=historical) + a bottom-right actionable panel (recommendation badge, zone, recency, vol ratio, bull/bear power bar, thin-volume distrust warning). Verified on live RELIANCE.NS daily: fired WEAK BUY @1313.60 (vol 0.62× avg) + WEAK SELL @1263 — grading correctly downgrades thin-volume rejections. `FVG.compute()` (raw-gap visualizer for FF-1) left untouched, so nothing downstream shifted.
- **Still open:** FF-1 (Fib↔FVG confluence), FF-2 (upgrade the *raw-gap rendering* to quality-gated — only the signal engine is gated so far, the drawn boxes are still all raw), FF-3 (FBG detector), FF-4, and FF-5's retail checklist + news-calendar leg.

## Related Pages
- [[concepts/Fair-Value-Gap]] · [[concepts/Fair-Value-Breaker-FBG]] · [[concepts/Fibonacci-Retracement]] — the three primitives.
- [[analyses/Dashboard-UI-Roadmap]] — parent roadmap (Phase 2).
- [[analyses/Decision-Support-Gating-Roadmap]] — sibling decision-support roadmap from the prior ingest.
- [[sources/FVG-FBG-Fibonacci-Retail-Framework]] — the source.
