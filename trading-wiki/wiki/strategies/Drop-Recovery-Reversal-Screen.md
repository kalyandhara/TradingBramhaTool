---
title: "Drop-Recovery Reversal Screen"
category: strategy
tags: [reversal, drop-recovery, screener, magnitude-filter, tradingview-screener]
created: 2026-07-02
updated: 2026-07-02
sources: 1
timeframe: swing
related:
  - strategies/Parabolic-Short-First-Red-Day.md
  - concepts/Stage-Analysis.md
  - concepts/Percent-R-Trend-Exhaustion.md
  - concepts/Reversal-Chart-Patterns.md
  - strategies/Candlestick-Filtering.md
  - sources/Upside-Reversal-Screener-Pine.md
---

# Drop-Recovery Reversal Screen

## Core Idea

No pattern recognition at all — just two magnitude thresholds. A stock qualifies as an "upside reversal" candidate if (1) it dropped at least X% (or X×ATR) from a recent high, and (2) price has already recovered at least Y% of that drop. This is the mirror image of [[strategies/Parabolic-Short-First-Red-Day]] (which catches exhaustion after a parabolic *up* move via the first red day) — same "measure the move, then measure the reaction" logic, applied to the downside.

## Setup Criteria

1. **Drop**: `(high_before_low − low) / high_before_low ≥ minDropPct` (default 5%), or optionally `(high_before_low − low) / ATR ≥ atrMultiplier` (default 2×ATR-21) instead of a flat percentage.
2. **Recovery**: `(close − low) ≥ recoveryPct × (high_before_low − low)` (default 60% of the drop reclaimed).
3. **Optional**: today's low must be below the previous bar's low (a genuine fresh low, not just a random dip) — off by default.

Only these two (or three) numbers gate the signal — no candlestick shape, no chart pattern, no oscillator. Deliberately the cheapest possible version of "something big happened, then it started reversing."

## Entry Rules
- Enter once both drop and recovery thresholds are met, i.e. price already confirming the reversal is underway, not at the exact low.
- Higher `minRecovery` (e.g. 60%+) trades earlier-but-noisier signals for later-but-more-confirmed ones.

## Exit Rules
- Not specified by the source script (a scanner/screener tool, not a full trading system) — pair with an existing exit method from this wiki, e.g. [[concepts/Capital-Management-Methods]]'s trailing-exit systems or a stop below the reversal low.

## Timeframe
- Daily or Weekly only — the source script explicitly errors out on intraday timeframes.

## Best Market Conditions
- A clean, single decline followed by a decisive recovery (V-shape or fast W-shape) — the simple two-threshold design has nothing to distinguish a real reversal from a dead-cat bounce beyond magnitude, so it works best when the recovery itself is unambiguous.

## Worst Market Conditions
- Choppy, multi-leg declines where "the high before the low" is ambiguous — see the flagged implementation concern below, which appears to make this measurement much shorter-lookback than the strategy's own naming implies.
- Also poor fit wherever a real pattern-quality read matters more than raw magnitude — this method can't distinguish a Double Bottom completing from an unstructured, coincidental bounce.

## Backtest / Track Record
Not provided by the source (no Follow-Through-Proof-style mechanism like [[sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine]]).

## Examples
- 5% drop from a recent high, then a close recovering ≥60% of that drop's dollar amount = qualifies.
- Toggling `useATR` on replaces the flat 5% with "dropped ≥2×ATR(21)" — better normalizes across low-vol vs. high-vol names than one fixed percentage.

## Related Concepts
- [[strategies/Parabolic-Short-First-Red-Day]] — the mirror-image strategy (exhaustion after an up-move, not a down-move)
- [[concepts/Stage-Analysis]] — this is another candidate Stage 1→2 transition signal, alongside %R Trend Exhaustion and the candlestick/chart-pattern triggers already documented
- [[concepts/Percent-R-Trend-Exhaustion]], [[concepts/Reversal-Chart-Patterns]], [[strategies/Candlestick-Filtering]] — sibling reversal-detection techniques surfaced in the same investigation thread; this one is the cheapest/simplest of the four

## Sources
- [[sources/Upside-Reversal-Screener-Pine]] (2026-07-02)
- [[sources/BSEIndia-Public-API-Corporate-Data-2026]] (2026-07-02) — BSE's `CorporateAction` API could distinguish a real drop from an ex-dividend gap, which this screen currently has no way to tell apart
