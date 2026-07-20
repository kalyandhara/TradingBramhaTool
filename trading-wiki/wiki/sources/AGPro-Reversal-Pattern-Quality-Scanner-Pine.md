---
title: "Pine Script — Reversal Pattern Quality Scanner [AGPro Series] v2.2"
category: source
tags: [pine-script, tradingview, double-top, double-bottom, head-and-shoulders, quality-score]
created: 2026-07-02
updated: 2026-07-02
sources: 1
related:
  - concepts/Reversal-Chart-Patterns.md
  - concepts/Percent-R-Trend-Exhaustion.md
  - sources/TradingView-Goodyear-PMax-Strat-Confluence-2026.md
---

# Pine Script — Reversal Pattern Quality Scanner [AGPro Series] v2.2

## Metadata
- Author: AGProLabs | AGPro Series, Pine v6, indicator (overlay)
- Ingest trigger: Kalyan pasted the full source directly, asking to "ingest this pine script to detect the reversal logic" — following on from the prior message's Early Reversal Detector discussion

## Key Takeaways

- **Detects 4 classic reversal structures from objective swing-pivot geometry**: Double Top, Double Bottom, Head and Shoulders, Inverse Head and Shoulders. Full breakdown of the detection logic is in the new [[concepts/Reversal-Chart-Patterns]] concept page — this source page covers the script-specific implementation and engineering choices.
- **This is a stronger building block for the "early buy sign at scale" goal than anything discussed so far this session.** Double Bottom and Inverse Head and Shoulders are literally bullish-reversal patterns, detected via pure OHLCV math (pivots, ATR, EMA, volume ratios) — no wave-counting subjectivity, and directly portable to Python for bulk screening the same way [[concepts/Percent-R-Trend-Exhaustion]] was ported.
- **The Follow-Through Proof mechanism is the single most valuable idea in this script.** Every confirmed break is registered at confirmation time (close price + ATR); at a fixed horizon later (default 12 bars) it's graded exactly once — did price move ≥0.75×ATR in the break direction? The rolling follow-through rate is a live, per-symbol, self-reported backtest of *this stock's own* recent pattern reliability, not a textbook percentage. Nothing else in this wiki currently does this (existing conviction/quality scores are all forward-looking estimates, never checked against what actually happened).
- **Quality score is a 5-factor weighted composite** (structure/depth/volume/breakout-strength/exhaustion-context, weights 0.28/0.22/0.18/0.17/0.15, output 1-10 with S/A+/A/B/C/D letter grades) — same shape as this project's existing conviction scores (Pre-Breakout Screener, VCP scoring) but with an unusually well-thought-out volume component (compares first-half vs. second-half average volume of the *pattern's own formation window*, not just a generic 20-day average) and an exhaustion-context component that's a lightweight, single-bar cousin of the full %R Trend Exhaustion oscillator.
- **Anti-clutter engineering is genuinely good** and worth remembering as a pattern for future scanners: same-region cooldown (bars + ATR price radius) prevents duplicate/overlapping confirmations of the same reversal pocket; per-pattern-type cooldown gap prevents rapid repeat signals; label de-overlap keeps only the higher-scoring pattern when two labels would collide on-screen.

## Detailed Notes

Pivot detection uses `ta.pivothigh`/`ta.pivotlow` with symmetric lookback/lookforward (default 8 bars each side) — meaning every detected pivot carries an unavoidable ~8-bar confirmation lag, and the overall pattern (needing 2-3 confirmed pivots plus a neckline break after) is detected well after the structure has actually formed. This is an inherent tradeoff of any pivot-based method, not a flaw specific to this script — same lag exists in this project's own `scan_darvas_box`/`scan_vcp` swing-based logic.

The neckline for Double Top/Bottom is a single pivot between the two peaks/troughs; for Head & Shoulders/Inverse H&S it's the *average* of the two troughs/peaks flanking the head — a small but sensible detail (a single-point neckline for a 3-pivot pattern would be arbitrary about which of the two troughs to use).

Volume score has a compounding bonus: beyond the first-half-vs-second-half contraction check, it adds up to +1.5 if the *current* (breakout) bar's volume exceeds 1.5× the 20-bar average, or +0.8 for 1.2×-1.5× — rewarding a breakout that's both preceded by contraction *and* confirmed by expansion, the same two-sided volume signature already documented in [[concepts/VCP]].

## Actionable Insights

This directly changes the recommendation from the prior message's Early Reversal Detector proposal:

- **Add Double Bottom / Inverse Head & Shoulders detection (ported to Python) as a primary signal**, likely stronger evidence of a genuine reversal than the previously-proposed "MA reclaim" signal alone, since it comes with its own built-in quality score.
- **Port the Follow-Through Proof mechanism generically** — it's not specific to these 4 patterns; the same confirmation-anchored "did price move X ATR within N bars" grading could retroactively validate *any* signal already built this session (%R Trend Exhaustion signals, Pre-Breakout Screener conviction scores) against real forward performance, turning static conviction scores into self-correcting ones over time.
- Pivot-based detection needs meaningfully more history per symbol than the oscillator-based signals already built (needs enough bars for 2-3 confirmed pivots at pivotLen=8 lookback/lookforward each) — worth checking against the existing `days=` parameters used when fetching OHLCV for screening (e.g. High-Growth Screener currently fetches 280 days, which should be enough).

## Contradictions with Existing Wiki

None — this reinforces rather than contradicts the Elliott-Wave-automation-skip decision: it demonstrates that an *objective*, pivot-based alternative to subjective wave-counting exists and is directly buildable, which is exactly the gap that decision left open.

## Pages Updated

- concepts/Reversal-Chart-Patterns.md — new concept page, this script is its primary source
