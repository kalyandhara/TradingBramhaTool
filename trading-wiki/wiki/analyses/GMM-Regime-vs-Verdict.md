---
title: "B-174 — Gaussian-mixture regime vs the rule-based verdict"
category: analysis
tags: [b-174, regime, gmm, machine-learning, volatility, pre-registration]
created: 2026-10-15
updated: 2026-10-15
sources: 0
related:
  - analyses/Open-Backlog
  - analyses/LuxAlgo-Machine-Learning-Gap-Analysis
---

# B-174 — Gaussian-mixture regime vs the rule-based verdict

From [[analyses/LuxAlgo-Machine-Learning-Gap-Analysis]] (rank 3). The question is
deliberately about **risk, not direction**: volatility clusters and is forecastable,
direction is not. The test asks whether a learned regime adds information about
forward NIFTY volatility and drawdown that the desk's existing rule does not already
carry.

## Pre-registration — written 2026-10-15, BEFORE any data was loaded

### Data
NIFTY 50 (`^NSEI`) daily closes, full history from `screener_pipeline.fetch_nifty50(days=0)`.
Log returns `r`. Trailing volatility `v_t` = standard deviation of the last 20 log returns
(the same window the verdict uses).

### The three predictors, all point-in-time (day *t* sees only days ≤ *t*)
1. **P(stressed)**, the learned regime (`tools/gmm_regime.py`). A 2-component, full-covariance
   Gaussian mixture on the features (r, v), each standardised with its training-window
   mean and standard deviation, fitted by EM (≤ 200 iterations, tolerance 1e-6), with
   deterministic initialisation: split at the median of v. Training window: the trailing
   **750** days. **Refit every 21 days**; between refits the last fit scores new days. The
   "stressed" component is the one with the higher mean v. The predictor is that
   component's posterior probability on day *t*.
2. **VOLATILE**, the desk's rule: `market_verdict.classify_regime` run on closes up to
   *t*, coded 1 when the label is VOLATILE and 0 otherwise.
3. **Trailing vol `v_t`**, the naive baseline. A learned model that cannot beat the
   number it was fed has added nothing.

### Targets (the 20 days after *t*)
* **Primary: forward volatility**, the standard deviation of log returns *t+1 … t+20*.
* **Secondary: forward drawdown**, −min(close[*t+1 … t+20*] / close[*t*] − 1, 0).

### Statistic and uncertainty
Spearman rank correlation of each predictor with each target, over every day that has a
fitted model and a complete 20-day forward window. Forward windows overlap, so
uncertainty comes from a **moving-block bootstrap**: 60-day blocks, 2,000 draws, seed 174,
applied to the **difference** ρ(P(stressed)) − ρ(competitor).

### Decision rule (fixed now)
* **ADDS INFORMATION** on a target if ρ(P(stressed)) is greater than **both**
  ρ(trailing vol) and ρ(VOLATILE), with each difference's 95% bootstrap interval
  excluding zero.
* If it adds information on the **primary** target: file **B-174r**, an HMM variant and
  whether P(stressed) earns a place on Home as context. The regime gate does **not**
  change on this test alone.
* Otherwise: **close B-174**. The regime stays rule-based, and the result is recorded.

### Prior, stated so the result can be wrong against it
**NO.** P(stressed) is a nonlinear function of the same trailing volatility it is fed, and
volatility clustering is already in `v_t`. Expected: ρ(P(stressed)) ≈ ρ(trailing vol),
both above ρ(VOLATILE), because a binary flag discards most of the information.

## Result

*(appended after the run — the section above is not edited after it)*
