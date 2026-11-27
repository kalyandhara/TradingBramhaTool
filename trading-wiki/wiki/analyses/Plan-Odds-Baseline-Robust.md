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

**Measured 2026-11-03, run exactly as pre-registered (`plan_baseline_study.py --procs 7
--d-cap 3 --strict-gate`). The strict gate passed: 8 BEATS, 8 AT, 6 BELOW, 1 THIN.**

| Placebo (clipped d) | Trades / names | Mean d | p | Thirds |
|---|---|---|---|---|
| Gate, `nifty500[300:500]` | 41,030 / 187 | +0.0013R | 0.89 | −0.015 / +0.036 / +0.006 |
| Main, `nifty500[0:300]` (context) | 62,812 / 286 | −0.0045R | 0.63 | −0.035 / +0.017 / +0.013 |

The gate's mean fell from +0.31R to +0.001R and the main panel's offset from +0.04R to
−0.004R. Clipping alone did that, which confirms the heavy tail was the placebo problem.
Twice the main placebo is 0.009R, so **no scanner is within placebo noise**.

| Verdict | Scanner | d (R) | B-183 | Holm p | Trades / names | Thirds |
|---|---|---|---|---|---|---|
| BEATS | Flag & Pole | +0.369 | BEATS +0.534 | 0.0097 | 311 / 171 | +0.50 / +0.33 / +0.19 |
| BEATS | Bullish CHoCH | +0.184 | BEATS +0.184 | 9e-12 | 3,338 / 283 | +0.19 / +0.22 / +0.09 |
| BEATS | %R Bottoming | +0.175 | BEATS +0.178 | 3e-05 | 2,834 / 280 | +0.06 / +0.05 / +0.07 |
| BEATS | Failed Breakdown (2-bar sweep) | +0.083 | BEATS +0.134 | 0.0074 | 6,535 / 281 | +0.08 / +0.03 / +0.06 |
| BEATS | HM Buy | +0.070 | BEATS +0.075 | 0.0023 | 7,835 / 283 | +0.08 / +0.04 / +0.04 |
| BEATS | RSI 60-40 | +0.068 | BEATS +0.068 | 0.0064 | 8,833 / 283 | +0.12 / +0.16 / −0.01 |
| BEATS | FVG Pullback | +0.068 | BEATS +0.092 | 0.036 | 7,448 / 284 | +0.18 / +0.05 / −0.01 |
| BEATS | Harmonic Reversal | +0.068 | BEATS +0.079 | 0.011 | 2,292 / 278 | −0.01 / +0.09 / +0.08 |
| BELOW | Liquidity Sweep | −0.087 | AT −1.410 | 0.032 | 6,073 / 280 | −0.03 / −0.13 / −0.13 |
| BELOW | VWAP Mean Reversion | −0.156 | AT −0.101 | 0.0009 | 1,630 / 271 | −0.05 / −0.27 / −0.14 |
| BELOW | RSI Divergence Bull | −0.220 | BELOW −0.208 | 0.0009 | 737 / 256 | −0.15 / −0.26 / −0.16 |
| BELOW | Support Breakdown | −0.325 | AT +0.215 | 2e-48 | 15,035 / 282 | −0.27 / −0.33 / −0.38 |
| BELOW | Inverted Flag & Pole | −0.405 | AT −0.272 | 6e-05 | 256 / 163 | −0.60 / −0.06 / −0.46 |
| BELOW | Connors RSI2 | −0.406 | BELOW −0.329 | 7e-05 | 310 / 182 | −0.17 / −0.50 / −0.32 |

AT BASELINE: Rounding Bottom (+0.152, was BEATS, Holm 0.29), Falling Wedge, ICT Setup,
Breakout Retest, Order Block Retest, Double Bottom, RSI Divergence Bear, VCP Coiling
(−0.176, Holm 0.29). THIN: RSI-Fibo Hidden Divergence (35 trades). The 35 never-plan
scanners from the census were skipped, as pre-registered.

**The prior was half right.** RSI Divergence Bull and Connors RSI2 kept BELOW, and
Flag & Pole, Bullish CHoCH and %R Bottoming kept BEATS. Rounding Bottom was the one
robust name to fall. The fragile four (FVG Pullback, Harmonic, HM Buy, RSI 60-40) were
expected to drop and did not: clipping barely moved them. The surprise is the four new
BELOWs, where outliers had masked a consistent shortfall: Support Breakdown went from
+0.215 to −0.325, and Liquidity Sweep from −1.410 to −0.087 with its noise gone.

**How to read it:**
- **A verdict is about the plan's levels, not the signal.** Failed Breakdown's plan
  BEATS while its signal is NULL ([[analyses/Failed-Breakdown-Sweep]]), and Bullish
  CHoCH's plan BEATS although its signal study failed.
- **It grades a plan against a no-edge plan.** It does not show that a plan makes money
  after costs.
- **Liquidity Sweep's BELOW fits B-41p:** the defect is its stop, and the signal's
  edge is separate.
- **Support Breakdown and Inverted Flag & Pole are short plans.** Their BELOW agrees
  with B-19 and B-92, where the names they flagged went up. A drift-free null is also
  harder on shorts than on longs, because a real short pays the stock's upward drift.
  That part has not been separated out (B-183e).
- **Means are per symbol,** so a name with few trades counts as much as one with many.
  %R Bottoming's thirds near +0.06 are trade-weighted and sit well under its +0.175.
- **The 2-of-3 rule allows one flipped third:** RSI 60-40, FVG Pullback and Harmonic
  each have one third just below zero.

**Card labels, applied by the pre-registered rule:** the 14 BEATS and BELOW scanners
above carry a line via `plan_odds_labels.py`, on every scanner card. The line says it
concerns the levels, not the signal. Nothing else is labelled, and no tier changed.
