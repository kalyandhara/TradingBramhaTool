---
title: "B-175 — Residual (market-neutral) momentum vs the desk's RS rank"
category: analysis
tags: [b-175, relative-strength, momentum, residual, cross-section, pre-registration]
created: 2026-10-16
updated: 2026-10-16
sources: 0
related:
  - analyses/Open-Backlog
  - analyses/LuxAlgo-Machine-Learning-Gap-Analysis
---

# B-175 — Residual momentum vs RS rank

From [[analyses/LuxAlgo-Machine-Learning-Gap-Analysis]] (rank 4, the PCA concept, in
its simplest single-factor form). The desk's RS rank (`scanner_templates._weighted_trailing_return`,
IBD-style 63/126/189/252-session returns weighted .4/.2/.2/.2) ranks on **total** return,
so a high-beta name rises in a strong tape for reasons that have nothing to do with the name. Residual
momentum ranks on the part of the return the market does not explain.

## Pre-registration — written 2026-10-16, BEFORE any forward return was computed

**Panel.** nifty500 first 300, 1500 days daily (`screener_pipeline.fetch_ohlcv`); NIFTY
from `fetch_nifty50(days=0)`. Survivorship: today's membership, the same bias `rs_walk`
documents; it applies equally to both predictors.

**Rebalance dates.** Every 21st session, from the first date with 273 sessions of history
to the last date with 21 sessions ahead. Non-overlapping forward windows.

**Predictors, point-in-time on each date *d*:**
* **RS** (the desk's): `_weighted_trailing_return(close[:d])`.
* **RESID**: regress the stock's daily log returns on NIFTY's over sessions *d−251 … d*
  (OLS **through the origin**, ≥ 200 shared days). Residuals *e* = r − β·m. No intercept,
  deliberately: with one, residuals sum to ≈ 0 over the fit window, so the 12-1 sum would be
  minus the latest month, i.e. a reversal signal. *(Caught by a unit test while writing; the
  spec was corrected before this page was committed or any data was loaded.)* Score = **sum of e over
  sessions d−251 … d−21** (12-1 month, skipping the latest month) **divided by the std of e
  over the same span**. That is the standard residual-momentum form.

**Outcome.** Return from the open of *d+1* to the close of *d+21*. Costs are omitted: this
is a ranking test, and costs are the same across the cross-section.

**Statistic.** On each date, the Spearman rank correlation (IC) of each predictor with the
outcome, across names with both. Then the mean IC across dates, with a t-test across dates, and the mean of
**ΔIC = IC(RESID) − IC(RS)** with its own t-test.

**Decision (fixed now).**
* **RESID ADDS** if mean ΔIC > 0 with p < 0.05 **and** mean IC(RESID) > 0 with p < 0.05,
  **and** ΔIC is positive in ≥ 2 of 3 equal calendar windows. Then file **B-175r**: an
  RS-resid column beside `rs_walk` (description, not a vote) and whether the scanner RS
  blend should use it. Owner's call.
* **Otherwise NO CHANGE.** RS stays as is; the result is recorded. (If RS's own IC is
  reported ≈ 0, that is a separate finding about RS, recorded but not acted on here.)

**Prior: NO CHANGE.** Six years of a strong Indian mid/small-cap tape, where beta has
mostly been rewarded. Expected: IC(RS) slightly positive, IC(RESID) similar, ΔIC within
±0.02 and not significant.

## Result — RUN 2026-10-16: NO CHANGE

`tools/residual_momentum_study.py`, run as pre-registered (`2879611`); output
`cache/residual_momentum_study.json`. **58 monthly dates** (2021-11-01 → 2026-09-03), median
**258 names** per date.

| Predictor | mean IC | t | p | % dates > 0 |
|---|---|---|---|---|
| RS (desk, total return) | 0.036 | 1.86 | 0.067 | 62.1% |
| RESID (12-1 residual momentum) | **0.044** | 2.81 | **0.007** | 63.8% |
| **ΔIC = RESID − RS** | **+0.008** | 0.81 | **0.420** | 43.1% |

ΔIC by calendar window: **−0.007 / −0.003 / +0.033**.

**Verdict: NO CHANGE.** RESID's own IC clears p < 0.05, but its advantage over RS does not
(p = 0.42), and it is positive in only 1 of 3 windows. All three conditions were needed. RS stays as it is; no
B-175r. Prior held.

**What it does say (descriptive):** both momentum flavours carry a little cross-sectional
information on this panel. ICs of 0.04 are small but typical of equity momentum, and the
market-neutral version is not worse than the desk's total-return RS. RS's own IC is only marginal
here (p = 0.067). Survivorship (today's membership) flatters both equally.
