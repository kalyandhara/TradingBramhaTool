---
title: "B-203 — Does the two-candle stop run (failed breakdown) carry an edge?"
category: analysis
tags: [b-203, liquidity-sweep, failed-breakdown, stop-run, sl-candle, pre-registration]
created: 2026-11-03
updated: 2026-11-03
sources: 1
related:
  - analyses/Open-Backlog
  - analyses/Bull-Trap-Detector
  - analyses/Sweep-Confirmation-Filter
---

# B-203: Failed Breakdown (the two-candle stop run)

From an owner-shared gold chart, 2026-11-03. A large red candle closes **below**
support (the stop-loss candle) and the next candle closes straight back above it.
The desk's `Liquidity Sweep` only sees the **one-candle** form: a wick below an
equal-lows pool with a close back above in the same bar. That form is measured at
+0.51% @20d net (B-41m), the desk's one edge that survives costs. The two-candle form
was invisible. B-203 adds it as a scanner and a chart overlay, and measures it.

## Pre-registration: written 2026-11-03, BEFORE any forward return was computed

**Detector:** `scanner_templates.failed_breakdown_events`. Every threshold is a named
`FB_*` constant.

- **Event:**
  - *S* = the lowest low of the 20 sessions before the break bar *b*.
  - close[*b*] < *S* and close[*b*−1] ≥ *S*: the first close below support.
  - *t* = the first bar in *b*+1 … *b*+3 that closes back **above** *S*. The event is dated *t*.
- **Grades:**
  - **pool:** at least 2 lows of that window within 0.75% of *S*, at least 3 sessions apart.
  - **weak volume:** volume[*b*] < 1.0 × the prior 20-session mean.
  - **bullish RSI divergence:** RSI(14) at the lowest low of *b* … *t* is at least 3 points above RSI at the bar that set *S*. That bar must be at least 5 sessions before *b* and past the 100-bar warm-up.
- **Spacing**, as amended for B-182: a pool event must be at least 10 sessions after the previous pool event; any other event at least 10 sessions after the previous event of either kind.
- **No look-ahead:** pinned by a test.

**Panel:** nifty500 first 300, last 750 bars (the B-165 panel). Events whose reclaim bar
falls in that span count.

**Arms:**
- **ALL**: every two-candle failed breakdown. Decision arm.
- **POOL**: the support was a pool of equal lows (resting stops). Decision arm.
- **Context only, never a verdict:**
  - the WEAK_VOL and DIVERGENCE subsets
  - the registered one-candle Liquidity Sweep on the same panel and span

**Outcome:** entry at the next open after *t*, exit at the close 20 sessions later, net of
`COST_INDIAN`, minus the symbol's all-bars mean over the span (the `crt_edge_study`
machinery). 10 and 60 sessions are descriptive.

**Statistic:** per-symbol mean edge, then a one-sample t across symbols, α = 0.025 per
decision arm. Three calendar windows.

**Decision (fixed now):** a long signal wants a **positive** edge.
- **TOO FEW**: fewer than 30 symbols, or fewer than 300 events (ALL) / 100 events (POOL) at 20 sessions.
- **EDGE**: mean > 0 with p < 0.025, and positive in at least 2 of 3 windows.
- Otherwise **NULL**.

**Consequences:**
- **Until the verdict**, the scanner is registered to screen and draw, but sits in
  `PIPELINE_EXCLUDED`, so it never votes in the Opportunity ranking. A new entry
  scanner would otherwise vote at the unmeasured weight on day one.
- **EDGE** (either arm): file **B-203r**. The owner decides whether it votes, and at
  what tier. Nothing changes automatically.
- **NULL / TOO FEW:** it stays screen-only, and the card states the result.

**Prior: NULL for ALL.** B-182's plain failed breakouts showed nothing (+0.11%, p 0.47,
3,563 events), and requiring a close beyond the level drops the wick rejection that
gives the one-candle sweep its edge. POOL is the arm with a chance, because it keeps
the "resting stops" premise.

## Result

*Not yet run.*
