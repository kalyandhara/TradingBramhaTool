---
title: "Falling Wedge (converging downtrend → bullish breakout)"
category: concept
tags: [falling-wedge, wedge, trendline, breakout, reversal, pattern, price-action]
created: 2026-07-25
updated: 2026-07-25
sources: 1
related:
  - sources/Obsidian-Falling-Wedge-Screener-Prompt.md
  - analyses/Falling-Wedge-Scanner-Fit.md
  - concepts/VCP.md
  - concepts/Order-Blocks.md
---

# Falling Wedge

## Definition
A **falling wedge** is a bullish pattern bounded by **two downward-sloping,
converging trendlines** — a **resistance** line through the swing highs and a
**support** line through the swing lows, where **resistance falls faster than
support** (the range narrows toward an apex). Price makes lower highs *and* lower
lows but the *selling pressure is decelerating*; a close **above the upper line**
is the breakout trigger, usually with volume expanding as volume had been drying
into the apex. Works as both a reversal (after a downtrend) and a continuation
(bullish pullback) pattern.

## Detection Algorithm (from the ingested screener spec)
Operates on the **last ~60 candles**. See [[sources/Obsidian-Falling-Wedge-Screener-Prompt]].
1. **Swings** — pivot look-back 1: swing high if `high[i] > high[i-1]` and
   `high[i] > high[i+1]`; swing low symmetrically. Collect the **last 5–10** of each,
   chronological.
2. **Trendlines** — linear-regress the **last 2–3 swing highs** → upper line
   (`slope`, `intercept`); the **last 2–3 swing lows** → lower line.
3. **Geometric validation** (all required):
   - both slopes **negative** (downward);
   - **upper steeper** (more negative) than lower;
   - vertical gap between the lines **decreases** oldest→newest (**convergence**);
   - each line **touched ≥ 2×** by wicks/closes in the window.
4. **Confidence 0–100** — weighted blend of: **touch ratio** (touches vs required),
   **convergence** (how much the gap narrows), **steepness ratio** (upper vs lower),
   **cleanliness / "containment"** (penalise candles piercing outside the wedge beyond
   tolerance), **recency** (newer wedges boosted).
5. **Breakout state** (latest candle): close **> upper line** → **confirmed
   ("Breakout")**; within **0.5%** of upper line → **pre-breakout ("Forming")**;
   else **none**.

The screener's chart modal surfaces these as **Confidence · Containment% · Convergence% ·
Pivots (H/L) · volume-declining** (verified from the ingested screenshots — e.g.
TATACONSUM.NS: confidence 93, containment 98%, convergence 93%, pivots 5/6, vol↓).

## How to Use
- **Entry:** on the confirmed breakout close above the upper line (or anticipate at
  "pre-breakout" within 0.5%), ideally with volume expanding.
- **Stop:** below the lower trendline / the last swing low inside the wedge.
- **Target:** a common measured move is the wedge's **height at its widest** projected
  from the breakout; or manage with the trend.
- **Volume tell:** healthy wedges show volume **contracting into the apex** then a
  **surge on breakout** (the same dry-up→expansion signature as [[concepts/VCP]]).

## Variants / Parameters
- **Window** ~60 bars; **touch tolerance** and the **0.5%** pre-breakout band are tunable.
- **Timeframe** — the spec runs 15m / 1h / 1d; higher TFs = more reliable, fewer signals.
- Contrast the **rising wedge** (bearish mirror) and the **descending channel** (parallel,
  not converging — *not* a wedge).

## Common Mistakes
- **Confusing it with a descending channel** (parallel lines) or a falling flag — the
  wedge *must converge*; without narrowing it isn't a wedge.
- **Trading before the breakout** — lower highs/lows still look bearish until the upper
  line breaks; the pre-breakout state is a watch, not a fill.
- **Ignoring volume** — a breakout on limp volume is the classic wedge fakeout.
- **Too few touches** — a line drawn through 1 point isn't a trendline; require ≥2 touches
  per side (the algorithm enforces it).

## Related Concepts
- [[concepts/VCP]] — a contraction cousin (volatility drying into a pivot); shares the
  volume dry-up→expansion breakout tell. (The two converging wedge lines are trendlines
  fitted by linear regression through the swing highs/lows.)
- [[concepts/Order-Blocks]] · other SMC pieces — different structural entries on the same charts.

## Examples in This Wiki
- **`scan_falling_wedge(df)`** ✅ *shipped 2026-07-25* ([scanner_templates.py](tools/scanner_templates.py),
  "Falling Wedge", Pattern) — the algorithm above ported into our scanner framework (reusing
  `np.polyfit` trendlines + pivot detection), with a **containment ≥55% quality gate**,
  breakout-state labelling, and a measured-move entry/stop/target. Live in both hubs; ITC
  verified as a clean confirmed breakout. Roadmap: [[analyses/Falling-Wedge-Scanner-Fit]].
- **Measured edge** ([[analyses/Backtest-Harness]], 49 names/~6y): **positive forward-return
  edge at every horizon** (+0.14/+0.24/+0.74/+1.03% @5/10/20/60d, ~60% hit) + **+0.14R
  expectancy** — one of only two scanners that beat random entry, the strongest at 20d/60d.
  Encouraging but single-window/gross — not yet proof.

## Sources
- [[sources/Obsidian-Falling-Wedge-Screener-Prompt]] (2026-07-25) — the ingested screener
  prompt + UI screenshots this algorithm is drawn from.
