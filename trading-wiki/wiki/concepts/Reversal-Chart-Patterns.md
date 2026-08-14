---
title: "Reversal Chart Patterns (Double Top/Bottom, Head & Shoulders)"
category: concept
tags: [chart-patterns, double-top, double-bottom, head-and-shoulders, pivot-detection, quality-score]
created: 2026-07-02
updated: 2026-07-02
sources: 1
related:
  - concepts/Percent-R-Trend-Exhaustion.md
  - concepts/Stage-Analysis.md
  - concepts/VCP.md
  - sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine.md
---

# Reversal Chart Patterns (Double Top/Bottom, Head & Shoulders)

## Definition

Four classic reversal structures, all detected the same objective way — from swing pivots, not subjective wave-counting:

- **Double Top** (bearish): two similar-height swing highs with a swing low (neckline) between them; confirmed when price closes below the neckline.
- **Double Bottom** (bullish): mirror image — two similar-depth swing lows with a swing high (neckline) between them; confirmed on a close above the neckline.
- **Head and Shoulders** (bearish): three swing highs where the middle (head) is higher than both outer ones (shoulders), roughly equal to each other; neckline = average of the two troughs flanking the head; confirmed on a neckline break down.
- **Inverse Head and Shoulders** (bullish): mirror image — three swing lows, head lower than both shoulders, neckline = average of the two peaks flanking the head; confirmed on a neckline break up.

Unlike Elliott Wave, every input here is a mechanical calculation (pivot detection, %, ATR, volume ratios) — there's no equivalent of "is this Wave 3 or Wave C" judgment call. This is the key reason it's a better fit for bulk/automated screening than wave-counting.

## How to Use

**1. Pivot detection**: a bar is a swing high/low if its high/low is the max/min within a symmetric window (`pivotLen` bars on each side, default 8). This needs `pivotLen` bars of *look-ahead* to confirm — a real, unavoidable lag (a pivot 8 bars back can only be confirmed once those 8 following bars exist).

**2. Pattern validation gates** (all four patterns share the same shape of checks):
- Peak/trough equality: the two (or three) key pivots must be within a tolerance % of each other (default 1.4%, doubled to 2.8% for the 3-pivot H&S/IHS patterns).
- Minimum pullback depth: neckline must be far enough from the peak/trough (default ≥2%) to reject flat, low-conviction structures.
- Pattern width: total bars between the first and last key pivot must fall within [minBars, maxBars] (default 10-90) — rejects both noise-sized and multi-year-sized structures.
- Time symmetry: the two legs of the pattern (first pivot→neckline, neckline→second pivot) should take roughly similar time.

**3. Confirmation**: requires a close beyond the neckline by a minimum ATR buffer (default 0.15×ATR) — not just touching it — with an optional breakout-volume multiple filter.

**4. Quality score (1-10, weighted composite)** — this is the most reusable part of the design:
- **Structure** (default weight 0.28): symmetry of peaks/shoulders + time symmetry + neckline flatness.
- **Depth** (0.22): deeper pullback from peak/trough to neckline = higher score (bucketed, e.g. ≥5% = 10/10, ≥2% = 5.5/10).
- **Volume** (0.18): compares average volume in the first half vs. second half of the pattern's formation — contraction into the pattern (second half quieter) scores higher, echoing the same "volume dries up before the move" idea as [[concepts/VCP]] and [[concepts/Percent-R-Trend-Exhaustion]]; bonus points if breakout-bar volume exceeds the 20-bar average.
- **Breakout strength** (0.17): how many ATRs past the neckline the confirmation close reaches.
- **Exhaustion context** (0.15): how stretched the pattern's extreme point was from an EMA(34) reference, *plus* how strongly the confirmation bar closed in the break direction within its own range — a distinct, cheaper cousin of the %R Trend Exhaustion idea, applied only to the single confirmation bar rather than a full oscillator history.

**5. Follow-Through Proof** — the standout idea. Every confirmed break is registered with its close price and ATR at confirmation time. At a fixed horizon later (default 12 bars), each one is graded exactly once: did price move ≥0.75×ATR (configurable) in the break direction? The rolling follow-through rate (follows / resolved, over a recent window) is a **live, self-reported, backtested hit rate for that specific symbol's pattern signals** — not a generic "70% of double bottoms work" claim from a book, but this stock's own recent track record.

**6. Anti-clutter / dedup**: a same-region cooldown (bars + ATR price radius) prevents overlapping/duplicate confirmations around the same reversal pocket; a separate per-pattern-type cooldown gap prevents rapid repeat signals of the same kind.

## Variants / Parameters

- Pivot length: 8 (default) — larger = fewer, more significant pivots; smaller = more, noisier ones.
- Equality tolerance: 1.4% (default) — how "double" the two tops/bottoms must be.
- Break confirmation: 0.15×ATR minimum distance past the neckline, optional volume multiple gate.
- Quality weights are all independently tunable (struct/depth/volume/breakout/context) — a stock or timeframe that whipsaws on volume, for example, could down-weight the volume component.

## Common Mistakes

- Treating the pattern's *formation* (before the neckline actually breaks) as tradeable — the whole design is built around **confirmed** breaks only; nothing is signaled while the pattern is still forming.
- Ignoring the Follow-Through Proof number — a high quality score describes how textbook-clean the *shape* is, not whether *this stock specifically* has been honoring these breaks recently. A pattern can be a textbook "A" grade shape with a 30% real follow-through rate on that name.
- Assuming pivot-based patterns have zero lag — confirming a pivot needs `pivotLen` bars of hindsight, so a "detected" pattern's key points are already `pivotLen` bars stale by the time it's recognized.

## Related Concepts

- [[concepts/Percent-R-Trend-Exhaustion]] — a full-history oscillator version of the same "how stretched is this move" idea that this pattern's context-score component applies only at the single confirmation bar
- [[concepts/VCP]] — shares the "volume contracts before the real move" logic with this pattern's volume-score component
- [[concepts/Stage-Analysis]] — Double Bottom / Inverse H&S completing near a stock's lows is a candidate Stage 1→2 transition confirm, same role proposed for %R Trend Exhaustion
- [[strategies/Candlestick-Filtering]] — same "trend context + trigger" shape, one level up in structure size (multi-week chart patterns here vs. single/few-bar candlesticks there); [[sources/Forthius-Reversal-Scanner-Pine]] is the candlestick-scale sibling of this script

## Examples in This Wiki

- [[sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine]] — the Pine v6 script this page documents

## Sources

- [[sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine]] (2026-07-02)
