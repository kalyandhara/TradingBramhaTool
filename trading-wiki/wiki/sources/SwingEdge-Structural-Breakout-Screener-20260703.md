---
title: "SwingEdge — Structural Breakout Scanner (Flat Bases & Neckline Reversals, scan 2026-07-02)"
category: source
tags: [swingedge, structural-breakout, flat-base, neckline-reversal, resistance-cluster, atr-buffer, retest, screener]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [concepts/Support-Resistance, concepts/Reversal-Chart-Patterns, concepts/Darvas-Box, concepts/Multi-Timeframe-Analysis, entities/AUBANK, entities/AADHARHFC, sources/SwingEdge-Momentum-Buildup-Screener-20260703]
---

# SwingEdge — Structural Breakout Scanner

## Metadata
- URL: https://www.swingedge.info/structural-breakout
- Scan data dated: 2026-07-02 20:48 IST (one day older than the Momentum Buildup scan fetched the same evening — boards don't all refresh together)
- Fetched: 2026-07-03 via Playwright
- Scope: methodology page + live scan (53 qualifiers, 3 visible without login)

## Key Takeaways
1. **Different animal from VCP pivots**: targets multi-week (~20–120 bar) *horizontal* resistance structures. Two families: **Flat base** (continuation — prior run-up ≥ ~15%, contained range, volume contracting) and **Neckline reversal** (W-shaped double bottom after a downtrend; neckline connects the swing highs between troughs).
2. **Resistance cluster definition is concrete and portable**: multiple daily highs within **~1.5%** of each other define the ceiling; more touches with contained price action = stronger structure (live cards show 9–19 touches).
3. **ATR-aware break buffer** — confirmation requires a close beyond resistance by a buffer scaled to ATR(14), "so a ₹50 stock and a ₹500 stock use comparable volatility units," plus strong close location and volume vs the 50-DMA. Same normalize-by-ATR philosophy as the FVG script's minimum-gap rule.
4. **Three-state lifecycle**: **approaching** (inside an ATR-scaled band under resistance) → **confirmed** (cleared the buffer on volume) → **retest** (broke recently, holding above on pullback). Extended moves beyond the neckline are *scored down* — an explicit anti-chase cap.
5. **Weekly confirm bonus** — when the weekly chart clears the same zone, the score gets a bonus; all three visible cards carry "Weekly ✓". MTF alignment as a score component, not a filter.
6. **Score floors differ by state**: 0–100 on structure/volume/RS/extension caps; list minimum **72 for confirmed/retest**, **65 for approaching** — a stricter bar for claiming a done deal than for a setup still forming.
7. **Supporting metrics**: base compression ratio (late-base range vs early-base range — tighter late = absorbed supply) and overhead supply (share of recent closes trapped relative to the break level — fewer trapped sellers = cleaner air above).

## Detailed Notes
- Live cards (all Neckline Reversal · Confirmed break · Weekly ✓): **ABCAPITAL** (10w base, 15 touches), **AUBANK** (7w base, 19 touches), **AADHARHFC** (9w base, 9 touches). 50 more behind login.
- Lifecycle cross-references: confirmed structural clears may simultaneously appear on Momentum Buildup or Base Formation depending on stage — the boards partition one underlying scan by structure age.
- Related-scanner framing: Darvas Box = "another horizontal-range breakout board" (boxes after new highs); Rounding Bottom = "saucer reversals and constructive Stage-1 bases — complementary reversal geometry" (still no wiki coverage — last un-ingested scanner family).

## Contradictions with Existing Wiki
- None substantive. The neckline reversal is the [[concepts/Reversal-Chart-Patterns]] Double Bottom with an explicit lifecycle state machine bolted on; the resistance-cluster/touch-count logic is [[concepts/Support-Resistance]]'s zone-strength factors made mechanical; the retest state is the confirmed-retest side of our fakeout check. Convergent, not conflicting.
- Worth noting: this board's stale-ish timestamp (2026-07-02) vs Momentum Buildup's same-evening refresh (2026-07-03) — when cross-referencing SwingEdge boards, check each board's Last Updated rather than assuming one scan date.

## Actionable Insights
- **Adopted (2026-07-03)**: `scan_structural_breakout()` added to the Scanner Hub in `tools/scanner_templates.py` — resistance cluster (highs within 1.5%, ≥4 touches), 20–120 bar base, flat-base vs neckline-reversal classification from the pre-base trend, ATR(14)-scaled break buffer, approaching/confirmed/retest states, base-compression and breakout-volume scoring, weekly-confirm bonus, and the page's own score floors (72 confirmed/retest, 65 approaching).
- **Two watch-note loops closed**: [[entities/AUBANK]] (flagged breakout candidate 2026-06-14 → confirmed neckline break, 19 touches, Weekly ✓) and [[entities/AADHARHFC]] (2026-06-21 grade-C skip-flag snapshot → confirmed neckline break, 9w base, Weekly ✓). Entity pages updated with the state change.
- The **per-state score floor** idea (stricter minimum for "confirmed" claims than "approaching" watches) is worth carrying into the Confirm-Before-Entry doctrine: a card claiming a done breakout should clear a higher bar than one flagged as forming.

## Pages Updated
- [[entities/AUBANK]], [[entities/AADHARHFC]] — 2026-07-02 scan state recorded
- `tools/scanner_templates.py` — `scan_structural_breakout()` (code, not wiki)
- index.md, log.md
