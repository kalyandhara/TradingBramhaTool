---
title: "High Tight Flag (HTF)"
category: concept
tags: [high-tight-flag, htf, momentum, pole-and-flag, volume-dry-up, market-leaders, oneil]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [concepts/VCP, concepts/Stage-Analysis, strategies/Minervini-SEPA, concepts/Darvas-Box, concepts/Candlestick-Patterns]
---

# High Tight Flag (HTF)

## Definition
The rarest and most aggressive bullish continuation pattern: a near-vertical **pole** — roughly a **90–120% advance in 4–8 weeks** — followed by a **tight flag** that corrects only **10–25%** on **contracting volume**, then breaks out of the flag to continue. The shallow pullback after a double is the tell: sellers can't knock it down even after a 100% run, meaning supply is absorbed and demand is institutional. O'Neil called it the signature of new market leaders; it appears at most a handful of times per cycle in any market.

## How to Use
1. **Qualify the pole first** — ≥90% gain inside ≤8 weeks. A 40% "strong move" is not an HTF; diluting the pole spec dilutes the edge (the pattern's statistics come from its strictness).
2. **Qualify the flag** — drawdown from the pole high stays within 10–25%, duration typically 1–5 weeks, and **volume dries up** through the flag (flag volume below pole volume; quiet trade near the highs = supply fading — the same accumulation tell as [[concepts/VCP]] dry-up, compressed in time).
3. **Entry** = break above the flag high with volume returning (1.5×+ average participation, per the SwingEdge Active-Breakout volume rule). No anticipatory entries — the flag can extend or fail into a deeper base.
4. **Invalidation** — flag depth exceeding ~25%, or flag duration stretching past ~8 weeks, converts the pattern into an ordinary (and usually deeper) base; re-evaluate under normal base rules instead.

## Variants / Parameters
- Reference spec (SwingEdge / O'Neil): pole 90–120% in 4–8 weeks; flag 10–25% deep, contracting volume.
- Python implementation: `scan_high_tight_flag()` in `tools/scanner_templates.py` (Scanner Hub "High Tight Flag") — ≥90% pole within ≤40 bars, flag 5–25 bars old and ≤25% deep, flag volume < pole volume, scored higher when tight (<15%), drying up hardest, and within 5% of (or clearing) the flag high.
- Related-but-different: **Active Breakout** (first clear of a 5–15 week base on 1.5×+ volume — Stage 2 launch without the pole requirement) and **Fresh Turnaround Breakout** (early reversal clear — covered in this repo by the Early Reversal Detector).

## Common Mistakes
- Calling any strong rally + pause an HTF — without the ≥90%/≤8-week pole the historical stats don't apply.
- Buying inside the flag "early" — the pattern's edge is at the flag-high break with volume, not during the drift.
- Ignoring flag volume — a flag on *rising* volume is distribution into strength, not supply absorption.
- Forgetting rarity — scanning daily for HTFs yields mostly false positives; treat a genuine hit as an event, and grade it against [[strategies/Minervini-SEPA]] trend-template context before acting.

## Related Concepts
- [[concepts/VCP]] — same supply-absorption logic; VCP contracts over months, HTF compresses it into weeks after a vertical pole.
- [[concepts/Stage-Analysis]] — a valid HTF is by construction early Stage 2; the pole often *is* the Stage 1→2 transition move.
- [[strategies/Minervini-SEPA]] — HTF discussed as a rare leadership pattern; SEPA risk rules (stop below flag low, pilot-then-add) apply directly.
- [[concepts/Darvas-Box]] — the flag is a one-box Darvas consolidation at the top of a runaway move.

## Examples in This Wiki
- **Scanner**: `scan_high_tight_flag()` in `tools/scanner_templates.py` (added 2026-07-03 from the SwingEdge Momentum Buildup ingest).
- No live NSE example yet — the pattern is rare by definition; annotate an entity page when the scanner produces a genuine hit.

## Sources
1. [SwingEdge-Momentum-Buildup-Screener-20260703](../sources/SwingEdge-Momentum-Buildup-Screener-20260703.md) — pattern parameters, volume rules, and tag taxonomy (ingested 2026-07-03).
