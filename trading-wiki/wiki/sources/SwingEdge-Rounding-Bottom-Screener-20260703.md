---
title: "SwingEdge — Rounding Bottom Scanner (Saucer Bases & Reversals, scan 2026-07-02)"
category: source
tags: [swingedge, rounding-bottom, saucer, ema-slope, rim-breakout, time-symmetry, screener]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [concepts/Rounding-Bottom, concepts/Reversal-Chart-Patterns, concepts/Stage-Analysis, concepts/EMA, sources/SwingEdge-Structural-Breakout-Screener-20260703]
---

# SwingEdge — Rounding Bottom Scanner

## Metadata
- URL: https://www.swingedge.info/rounding-bottom
- Scan data dated: 2026-07-02 20:48 IST (same batch as Structural Breakout; Momentum Buildup refreshed a day later — check each board's Last Updated)
- Fetched: 2026-07-03 via Playwright
- Scope: methodology page + live scan (16 qualifiers, 3 visible without login). **Completes the SwingEdge pre-built scanner family coverage** — every family board is now ingested.

## Key Takeaways
1. **Saucer mapped mechanically, not aesthetically**: "swing lows and linear slope stats, not curve fitting." Trough zone from confirmed swing lows with minimum width; left decline and right recovery each need an adequate *linear fit* — chaotic whipsaw legs score down or fail. A falsifiable definition of "smooth U."
2. **Constructive bands on depth**: left-side decline roughly **12–40%** — too shallow isn't a base, too deep isn't a saucer (it's a crash-and-recover, different distribution of trapped supply).
3. **EMA slope transition as the knife-filter**: short EMAs (EMA-21 on the cards) must flatten at the trough and turn up on the right side while longer averages lag — "separates repair bases from still-falling knives."
4. **Time symmetry scored**: left and right legs should be reasonably balanced; extreme asymmetry (a V) reduces the score / fails the saucer definition.
5. **Two families scored separately by 200-DMA context**: **Classic Reversal** (trough below a falling 200-DMA — deeper turnaround) vs **Constructive Base** (repair near/above a rising 200-DMA — earlier-stage bases in trending markets). All three visible cards were Constructive Base.
6. **Same lifecycle machinery as Structural Breakout**: rim = recovery high of the pattern window; **Approaching rim** → **Confirmed** (close above rim on volume vs 50-DMA) → **Retest** (holding above after clear); overhead-supply metric; score floors **70 confirmed/retest, 65 approaching**.
7. **Lifecycle hand-off is explicit**: saucer repair → Base Formation (VCP compression near pivot) → Momentum Buildup (when clears accelerate) — the boards are one scan partitioned by structure age, and a saucer that tightens should be re-evaluated as a VCP.

## Detailed Notes
- Live cards (all Constructive Base · Approaching rim · EMA turn): **GROWW** (13d trough, 0.9% from rim), **TITAN** (11d trough, 1.0%), **MMFL** (6d trough, 1.9%). 13 more behind login.
- **Terminology quirk**: the concepts panel says wider troughs "within 30–90 bar windows" reflect classic geometry, yet live cards show 6–13d troughs — "trough duration" evidently counts only the flat bottom, while 30–90 bars is the full pattern window. Two different widths, one word.
- Card reason lines again check-style ("✔ Within 0.9% of rim", "✔ EMA-21 slope turning upward").

## Contradictions with Existing Wiki
- None substantive — the saucer is complementary geometry to [[concepts/Reversal-Chart-Patterns]]'s sharp-pivot Double Bottom/Inverse H&S (gradual vs event-driven reversal), and the EMA-slope-transition gate matches [[concepts/EMA]]'s slope-over-position rule.
- The 6–13d troughs on live cards vs the "30–90 bar window" prose is an internal ambiguity (see Detailed Notes), not an error — but it's another instance of the running SwingEdge lesson: field semantics over prose.

## Actionable Insights
- **Adopted (2026-07-03)**: `scan_rounding_bottom()` added to the Scanner Hub in `tools/scanner_templates.py` — 12–40% decline band, linear-fit R² gates on both legs, time-symmetry gate (V-bottoms with symmetry <0.25 rejected outright), EMA-21 slope transition, Approaching/Confirmed/Retest states with anti-chase cap, Classic Reversal vs Constructive Base by 200-DMA context, and the page's score floors.
- The saucer's *right side approaching the rim* is a natural feeder for the Early Reversal Detector — a name that passes both (saucer geometry + drop-recovery composite) is a stronger candidate than either alone. Cross-scanner confluence candidate, noted not built.

## Pages Updated
- [[concepts/Rounding-Bottom]] — created (first dedicated saucer page)
- `tools/scanner_templates.py` — `scan_rounding_bottom()` (code, not wiki)
- index.md, log.md
