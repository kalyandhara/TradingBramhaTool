---
title: "Rounding Bottom (Saucer Base)"
category: concept
tags: [rounding-bottom, saucer, reversal, ema-slope, rim, time-symmetry, stage-1]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [concepts/Reversal-Chart-Patterns, concepts/Stage-Analysis, concepts/EMA, concepts/VCP, concepts/Support-Resistance]
---

# Rounding Bottom (Saucer Base)

## Definition
A gradual U-shaped reversal: price declines on the left, rounds through a multi-week trough as selling exhausts, then rises on the right as momentum quietly shifts. Unlike the sharp, event-driven turns of a Double Bottom or Inverse H&S ([[concepts/Reversal-Chart-Patterns]]), the saucer's information is in its *smoothness* — supply being absorbed gradually rather than in capitulation. The **rim** (pre-decline high / pattern recovery high) is the breakout level.

## How to Use (mechanical definition, from the SwingEdge reference)
1. **Trough from swing structure, legs by linear fit** — map the U with confirmed swing lows and require each leg to fit a straight line reasonably well (orderly decline, orderly recovery). No curve fitting, no eyeballing; whipsaw legs disqualify.
2. **Depth band 12–40%** off the rim — shallower isn't a base, deeper is a crash-recovery with different trapped-supply dynamics.
3. **Time symmetry** — left and right legs reasonably balanced; extreme asymmetry is a V-bottom, a different (and less reliable) animal.
4. **EMA slope transition** — EMA-21 flat/falling at the trough, turning up on the right side while the 200-DMA lags. This is the falling-knife filter: a right side without the short-EMA turn is still a downtrend, per [[concepts/EMA]]'s slope-over-position rule.
5. **Rim breakout lifecycle** — Approaching rim (near the top, no clear) → Confirmed (close above rim on ≥ ~1.3× 50-day volume) → Retest (holding above on pullback). Extended moves past the rim are a chase, not a signal.
6. **Context families** — *Classic Reversal*: trough under a falling 200-DMA (Stage 4→1→2 turnaround, per [[concepts/Stage-Analysis]]). *Constructive Base*: repair near/above a rising 200-DMA (a resting base inside an uptrend). Same geometry, different base rates — score them separately.

## Variants / Parameters
- Pattern window ~30–90 bars; note the "trough duration" shown on cards counts only the flat bottom (6–13 days typical), not the full window.
- Python implementation: `scan_rounding_bottom()` in `tools/scanner_templates.py` (Scanner Hub "Rounding Bottom") — 12–40% band, R² gates on both legs, symmetry <0.25 rejected, EMA-21 turn, three states, 200-DMA family split, score floors 70 (confirmed/retest) / 65 (approaching).
- Cup-with-handle is the saucer's famous descendant: a saucer whose right rim adds a small handle pullback before breaking out.

## Common Mistakes
- Buying the right side before the short-EMA turn — a smooth-looking left leg with no momentum shift is just an orderly downtrend.
- Treating a V-bottom as a saucer — the gradualness *is* the signal (absorbed supply); a V leaves overhead sellers intact.
- Chasing extended rim breaks instead of waiting for the retest state.
- Ignoring the 200-DMA family split — a Classic Reversal saucer needs more proof (it's fighting the long-term trend) than a Constructive Base printing the same geometry.

## Related Concepts
- [[concepts/Reversal-Chart-Patterns]] — sharp-pivot reversal geometry (Double Bottom / Inverse H&S); the saucer is the gradual counterpart.
- [[concepts/Stage-Analysis]] — a Classic Reversal saucer is Stage 1 made visible; the rim break is the Stage 2 transition.
- [[concepts/VCP]] — the lifecycle hand-off: saucer repair that tightens near the rim becomes a VCP/pivot base.
- [[concepts/EMA]] — slope-over-position; the EMA-21 turn is the saucer's momentum confirmation.
- [[concepts/Support-Resistance]] — the rim is a mechanically-defined resistance level; retest logic applies after the clear.

## Examples in This Wiki
- **Scanner**: `scan_rounding_bottom()` in `tools/scanner_templates.py` (added 2026-07-03 from the SwingEdge ingest).
- Live scan 2026-07-02: GROWW, TITAN, MMFL — all Constructive Base, Approaching rim with EMA turn (no confirmed clears visible that day).

## Sources
1. [SwingEdge-Rounding-Bottom-Screener-20260703](../sources/SwingEdge-Rounding-Bottom-Screener-20260703.md) — mechanical definition, bands, lifecycle, family split (ingested 2026-07-03).
