---
title: "B-183c — Plan-odds baseline, heavy-tail-robust re-run (pre-registered)"
category: analysis
tags: [b-183c, plan-r, null-model, robustness, winsorize, pre-registration]
created: 2026-11-03
updated: 2026-11-03
sources: 0
related:
  - analyses/Plan-Odds-Baseline-Measured
  - analyses/Plan-Odds-Baseline-Pre-Registration
  - analyses/Open-Backlog
---

# B-183c: the plan-odds baseline, robust to heavy tails

B-183's amended run gave 8 BEATS / 11 AT / 2 BELOW (see [[analyses/Plan-Odds-Baseline-Measured]]).
Two problems kept those verdicts off the cards:

1. **Heavy tails.** R is measured per unit of risk, so a plan whose stop sits a hair
   from its entry turns a 1% price move into tens of R. One such trade moves a symbol's
   mean. The gate panel's placebo had a third at +1.00R, and Liquidity Sweep's mean d
   was −1.73R off one third of −3.80R.
2. **A gate with an escape hatch.** The placebo rule was "|mean d| ≤ 0.05R **or**
   p ≥ 0.05". A large, noisy mean passes on the p clause, and that is how the amended
   gate passed (+0.31R, p 0.24).

## Pre-registration: written 2026-11-03, before any B-183c number exists

**Unchanged from B-183 amendment 2:**
- the engine (`plan_baseline.py`, zero-drift pool, 2,000 replays, 5-bar blocks, seed 19)
- the harness settings
- both panels
- the scanner set (census never-plan skip)
- Holm (family α 0.05), the floors (30 symbols / 100 baselined trades)
- the 2-of-3 thirds stability rule and the decision table

**Changed, and only this:**
- **Per-trade d is winsorized at ±3R:** `d = clip(r − exp_r, −3, +3)`. A fixed plan's
  real R is bounded by its geometry, about −1R at the stop and the target's multiple.
  A |d| above 3R only arises from tiny-risk plans. Clipping keeps their sign and drops
  their leverage. The per-symbol mean, the t-test across symbols, Holm and the thirds
  all use the clipped d.
- **Placebo gate, strict (no escape):** the `_B183 Placebo` on `nifty500[300:500]`
  must have **|mean clipped d| ≤ 0.05R**, with no p clause. If it fails, no scanner
  verdict is written.
- **The main panel's placebo is context**, and so is its *offset*. A scanner whose
  |mean d| is within 2× the main placebo's |mean d| is labelled "**within placebo
  noise**" in the results, beside its verdict. That label is descriptive and does not
  change the verdict.

**Card labels, decided now:** after the run, a "beats / below the no-edge baseline
(B-183c)" line goes on a scanner's card only if all three hold:
- the strict gate passes
- the B-183c verdict is BEATS or BELOW
- the scanner is **not** "within placebo noise"

Everything else carries no label.

**Prior:** the four robust B-183 BEATS (Flag & Pole, Rounding Bottom, Bullish CHoCH,
%R Bottoming) and the two BELOW (RSI Divergence Bull, Connors RSI2) keep their verdicts.
The fragile four drop to AT or "within placebo noise". The strict gate is the risk: if
the heavy tail was the whole problem, clipped placebo d should land near 0.

## Result

*Not yet run.*
