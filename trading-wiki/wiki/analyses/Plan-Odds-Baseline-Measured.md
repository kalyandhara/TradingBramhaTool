---
title: "Plan-Odds Baseline — Measured (B-183)"
category: analysis
tags: [b-183, plan-r, null-model, block-bootstrap, baseline, measured]
created: 2026-11-03
updated: 2026-11-03
sources: 0
related:
  - analyses/Plan-Odds-Baseline-Pre-Registration
  - analyses/Open-Backlog
  - analyses/Backtest-Harness
---

# Plan-Odds Baseline — Measured (B-183)

Run 2026-11-03, `tools/plan_baseline_study.py`. Sources:
- pre-registration `082f73f`
- procedure amendment `aa2f3d0`
- amendment 2, the zero-drift pool with the gate on a disjoint panel, `7613769`

The first run failed its placebo gate on the drift-carrying pool. See the
pre-registration page, Outcome. This page is the amended run.

## Placebo first

| Panel | trades / symbols | mean d (R) | p | thirds | realised vs predicted target-first |
|---|---|---|---|---|---|
| **Gate: nifty500[300:500]** (disjoint, untouched by the diagnosis) | 41,032 / 187 | +0.310 | 0.24 | −0.02 / +0.05 / **+1.00** | 30.9% vs 31.0% |
| Main nifty500[0:300] (context only) | 62,817 / 286 | **+0.040** | **0.0006** | −0.02 / +0.04 / +0.12 | 30.6% vs 31.0% |

**The gate passed, by the letter.** The rule was |d| ≤ 0.05 or p ≥ 0.05, and the gate
panel passed on p ≥ 0.05.

Two things weaken that pass:
- **The gate panel's mean is +0.31R, driven by one third (+1.00R).** That is the
  signature of a few huge-R trades: plans whose risk (stop distance) is tiny make R,
  and therefore d, explode. The rule's "or p ≥ 0.05" clause lets a heavy-tailed mean
  through.
- **The main panel's placebo shows a small, significant pessimism in the baseline:
  +0.04R.** Inside the ±0.05 band, but real.

Any scanner whose d is not well clear of about 0.04R is not clearly beating the
baseline: its whole margin could be this tilt.

The target-first odds are well calibrated on both panels: predicted 31.0% against 30.6%
and 30.9% realised. The engine's *probabilities* are right; its *R* is the heavy-tailed
part.

## Verdicts (pre-registered rule, nifty500[0:300], Holm across 21 scanners clearing the floors)

| Verdict | Scanner | trades | symbols | mean d (R) | Holm p | thirds | robust? |
|---|---|---|---|---|---|---|---|
| **BEATS** | Flag & Pole | 314 | 170 | **+0.49** | 0.003 | +0.59 / +0.49 / +0.34 | yes: large, all thirds |
| **BEATS** | Rounding Bottom | 552 | 223 | **+0.32** | 0.012 | +0.37 / +0.49 / +0.23 | yes |
| **BEATS** | Bullish CHoCH (last 5 sessions) | 3,344 | 283 | **+0.18** | 1e-11 | +0.19 / +0.22 / +0.09 | yes |
| **BEATS** | %R Bottoming | 2,836 | 280 | **+0.18** | 2e-5 | +0.06 / +0.05 / +0.07 | likely: thirds small |
| BEATS | FVG Pullback | 7,442 | 284 | +0.09 | 0.003 | +0.22 / +0.08 / +0.01 | fragile: about 2× the placebo tilt |
| BEATS | Harmonic Reversal (XABCD) | 2,292 | 278 | +0.08 | 0.007 | +0.01 / +0.10 / +0.09 | fragile |
| BEATS | HM Buy (Hilega Milega) | 7,842 | 283 | +0.08 | 0.001 | +0.09 / +0.04 / +0.04 | fragile |
| BEATS | RSI 60-40 Setup | 8,841 | 283 | +0.07 | 0.007 | +0.11 / +0.16 / −0.01 | fragile |
| AT | Breakout Retest, VCP Coiling, RSI Divergence Bear, Order Block Retest, Inverted Flag & Pole, Falling Wedge, Double Bottom, ICT Setup, Support Breakdown, VWAP Mean Reversion, Liquidity Sweep | | | | | | Liquidity Sweep: d −1.73 with a −3.80 third (heavy tail) |
| **BELOW** | RSI Divergence Bull | 736 | 256 | **−0.20** | 0.014 | −0.11 / −0.23 / −0.19 | yes, all thirds |
| **BELOW** | Mean Reversion (Connors RSI2) | 310 | 182 | **−0.33** | 0.012 | +0.02 / −0.45 / −0.23 | yes |
| THIN | RSI-Fibo Hidden Divergence | 35 | 33 | −0.23 | — | | |

35 scanners were skipped because the census shows they never carry a plan (listed in the JSON).

**Prior vs outcome:** the prior was "≥ 80% AT, none BEATS". The outcome is 11 of 22 AT
and 8 BEATS. Half of those 8 are within about 2× the placebo's own tilt.

## What this measures, and what it does not

**B-183 compares each scanner's PLAN** (its entry, stop, target and time stop) with
what the same geometry earns on a drift-free version of the stock's own past. A BEATS
says "this plan's levels are better placed than noise". It does **not** say "the signal
predicts direction". Bullish CHoCH failed its *signal* measurement (choch_study,
`PIPELINE_EXCLUDED`), yet its *plan* beats the no-edge baseline. The two questions are
different.

## Actions (decision table) and what is held back

- **BELOW:** file follow-ups on stop/target geometry. **B-183a** for RSI Divergence Bull
  (−0.20R, all thirds) and **B-183b** for Mean Reversion (Connors RSI2) (−0.33R). No
  tier change.
- **BEATS:** the decision table *allows* a card line ("beats the no-edge baseline").
  It is **held for the owner**, because of the placebo caveats above. The suggestion is
  to label only the four robust ones (Flag & Pole, Rounding Bottom, Bullish CHoCH,
  %R Bottoming), and only after a heavy-tail check.
- **Follow-up B-183c (robustness, a new pre-registration):** cap per-trade |R| or use
  a median-of-d per symbol, and re-gate the placebo with a rule that has no "or p ≥
  0.05" escape for large |d|.
- **The Watchlist no-edge odds** (target-first / stop-first probabilities) are the
  well-calibrated part, at 31.0% predicted vs 30.6–30.9% realised, so they stand.
