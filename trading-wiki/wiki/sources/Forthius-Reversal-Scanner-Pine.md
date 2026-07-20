---
title: "Pine Script — Forthius Reversal Scanner v5"
category: source
tags: [pine-script, tradingview, candlestick-patterns, confluence-score, reversal]
created: 2026-07-02
updated: 2026-07-02
sources: 1
related:
  - strategies/Candlestick-Filtering.md
  - concepts/Candlestick-Patterns.md
  - concepts/Reversal-Chart-Patterns.md
  - concepts/Percent-R-Trend-Exhaustion.md
---

# Pine Script — Forthius Reversal Scanner v5

## Metadata
- Pine v6, indicator (overlay), no published author/license info beyond the in-script name "Forthius"
- Ingest trigger: Kalyan pasted the full source directly, continuing the same-session Early Reversal Detector thread (after the AGPro chart-pattern scanner ingest)

## Key Takeaways

- **This is a working, concrete implementation of a strategy this wiki already documented in the abstract.** [[strategies/Candlestick-Filtering]] describes exactly this shape — trend context, then a presignal/filter zone, then a candlestick pattern as the trigger — sourced from a 7,275-stock backtest study. Forthius codes that same idea end-to-end: EMA20/EMA50 trend context gate → a 5-factor confluence pre-condition (volume, S/R proximity, RSI zone, ADX trend strength, RSI divergence) → ~15 candlestick patterns as the trigger, each with its own geometry-based quality score.
- **Detects far more candlestick patterns than [[concepts/Candlestick-Patterns]] currently has formulas for**: Bullish/Bearish Engulfing, Morning/Evening Star, Three White Soldiers/Three Black Crows, Dragonfly/Gravestone Doji, Hammer/Inverted Hammer/Hanging Man/Shooting Star, Piercing Line/Dark Cloud Cover, Bullish/Bearish Harami, Tweezer Top/Bottom — each gated to only fire in the correct trend context (e.g. Hammer only counts in a downtrend context; the same wick shape in an uptrend is scored as Hanging Man instead, a bearish read).
- **Composite Strength (0-10) = pattern quality (0-3) + confluence score (0-5) + volume score (0-2)**, graded A (≥8) / B (≥5) / C (≥3) — same 3-tier grading shape as AGPro's S/A+/A/B/C/D, a recurring pattern worth standardizing on across this wiki's own scoring work.
- **Per-pattern quality formulas are genuinely detailed and reusable**: e.g. Hammer quality = lower-wick-in-ATR-multiples (0-2) + body position in upper 35% of range (0-1) + clean upper wick (0-1); Piercing Line / Dark Cloud Cover quality = how far the second candle's close penetrates into the first candle's body (a ratio, not just "closed past midpoint" as commonly simplified) + body-vs-doji-ness of the setup. This penetration-ratio detail is more precise than the standard textbook "closes above the midpoint" rule.
- **RSI divergence detection is a genuinely separate signal folded into the confluence score**, not a candlestick concept at all: `low < lowest(low, N)[1] and rsi > lowest(rsi, N)[1]` (price makes a new low, RSI doesn't) for bullish, mirrored for bearish. Cheap, standard, and not yet present anywhere in this project's own Python scanners.

## Detailed Notes

Trend context is graded three ways, not two: `upTrend`, `downTrend`, and `ranging` (neither), using EMA20 > EMA50 with an EMA20-slope-over-3-bars check normalized by ATR (`emaSlope = (ema20 - ema20[3]) / (atr*3)`, must exceed ±0.1) — a slope-over-position rule matching the same principle already documented in [[concepts/EMA]]. An explicit `relaxTrend` toggle allows patterns to fire in `ranging` context too, trading precision for recall.

Patterns are context-gated asymmetrically and cleverly: the *same* candle geometry means different things depending on trend context and which "slot" fires first. A long-lower-wick candle is `bullDFD` (Dragonfly Doji, bullish) only if it also occurs in `downCtx`; the identical shape check (`shapeHammer`) becomes `bullHam` in a downtrend but `bearHM` ("Hanging Man", bearish) in an uptrend — the geometry is identical, only the context flips the read. This is a clean way to avoid writing the same wick-measurement logic twice for what are, geometrically, mirror-image-labeled patterns.

Multi-candle patterns (Morning/Evening Star, Three Soldiers/Crows, Piercing/Dark Cloud) all reference `downCtx[N]`/`upCtx[N]` — i.e. the trend context is checked as of *when the pattern started forming*, not the current bar, avoiding the lookback bias of checking trend context after the reversal has already happened.

Cooldown (default 3 bars) is a single global per-direction cooldown (`lastBullBar`/`lastBearBar`), simpler than AGPro's per-pattern-type + same-region ATR-radius cooldown — a reasonable simplification for a candlestick scanner (patterns are single/few-bar events, not multi-week structures needing spatial dedup).

## Actionable Insights

- **[[strategies/Candlestick-Filtering]] now has a concrete reference implementation** — worth linking directly rather than just conceptually; if this project ever ports candlestick-pattern screening to Python, this script's per-pattern quality formulas (not just pattern detection booleans) are the right level of detail to replicate, not the simpler textbook versions.
- **RSI divergence detection is a cheap, high-value addition** to any of this project's own scanners — it's 2 lines of pandas (rolling min/max comparison between price and RSI) and isn't currently computed anywhere in `scanner_templates.py`.
- **The "same geometry, context flips the label" pattern** (Hammer vs. Hanging Man, Dragonfly Doji vs. a bullish-context-only read) is a good general principle for any future Python port: compute the wick/body geometry once, then apply trend-context gating separately, rather than writing separate detection functions per directional label.
- Combined with the AGPro chart-pattern scanner and %R Trend Exhaustion, this is now the **third independently-built, non-Elliott-Wave reversal signal** surfaced this session — all three could feed the same proposed Early Reversal Detector as parallel, cheaply-computed inputs (candlestick trigger + chart-pattern trigger + oscillator-exhaustion trigger), rather than needing to pick just one.

## Live Behavior Observations (from a rendered chart, 2020-2026 Goodyear India)

Kalyan shared a second screenshot of this exact script actually running (6 years of daily bars) — these are runtime observations that reading the source alone wouldn't surface:

- **No label de-overlap logic exists in this script** (unlike [[sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine]], which explicitly tracks and skips/replaces colliding labels). In a dense reversal zone — visible right at the 2026 low in the screenshot — 3 labels (`BullHarami`, `BullHarami` again, `3Soldiers`) stack and partially overlap, becoming hard to read. Confirmed visual limitation, not just a theoretical gap.
- **Grade distribution skews low in real use**: of ~16 visible signals across 6 years, only **one** reached grade A (8/10, a BearEng at the Sept-2025 top); the rest are B (5-7/10) or C (4-5/10). A-grade signals are rare — worth knowing before setting `minGrade` expectations.
- **Bearish Engulfing dominates by frequency** — it fires far more often than any other pattern (6+ times visible vs. 1-2 for most others), consistent with it having the loosest geometric bar to clear (just a body-size + close/open relationship check, vs. 3-candle alignment for Three Soldiers/Crows or Morning/Evening Star).
- **Important operational gap, confirmed live**: at the current bar (the actual bottom/recovery point — the same low the earlier %R Trend Exhaustion screenshot flagged as bullish), the dashboard reads **Trend: RANGE**, not DOWN. Because bullish candlestick patterns require `downCtx = downTrend or (relaxTrend and ranging)`, and `relaxTrend` defaults to **false**, the script's own trend gate would suppress bullish signals at exactly this moment unless the user manually enables `relaxTrend`. In other words: the default configuration goes quiet precisely during the Stage 4→Stage 1→Stage 2 transition window — the exact "early buy" moment this whole investigation thread is trying to catch. This is the single most important finding for the proposed Early Reversal Detector: **"ranging after a prior decline" must be treated as a first-class permissive state, not an opt-in relaxation**, or the detector will systematically miss the moment it's designed to catch.
- **Near S/R also lags at the worst possible moment**: the dashboard shows "Near S/R: —" (neither) at the current bar, despite price sitting at an obvious multi-year low. This is a direct consequence of pivot-confirmation lag (`pvtLen=5` needs 5 bars of look-ahead) — a pivot *at* the very low can't be confirmed until 5 bars after it, so "near support" can't fire until the low is already 5+ bars in the past.
- **Convergence evidence**: the cluster of bullish signals at the 2026 low (`BullHarami` ×2, `3Soldiers`) lines up with the same window the earlier screenshot showed a bullish %R Trend Exhaustion signal firing, and with an 8.6× average-volume spike shown in the dashboard panel — three independently-built signals agreeing on the same bar strengthens confidence in combining them for the Early Reversal Detector rather than relying on any one alone.

## Contradictions with Existing Wiki

None — this is confirmation and concrete detail added to an existing strategy page ([[strategies/Candlestick-Filtering]]), not a new claim.

## Pages Updated

- strategies/Candlestick-Filtering.md — added this script as a concrete reference implementation
- concepts/Candlestick-Patterns.md — cross-link
