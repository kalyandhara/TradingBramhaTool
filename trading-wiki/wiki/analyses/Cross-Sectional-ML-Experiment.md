---
title: "B-177 — Is anything learnable that single-feature tests missed?"
category: analysis
tags: [b-177, machine-learning, cross-sectional, walk-forward, pre-registration]
created: 2026-10-17
updated: 2026-10-17
sources: 0
related:
  - analyses/Open-Backlog
  - analyses/LuxAlgo-Machine-Learning-Gap-Analysis
  - analyses/Residual-Momentum-vs-RS
---

# B-177 — One cross-sectional supervised-learning experiment

From [[analyses/LuxAlgo-Machine-Learning-Gap-Analysis]] (rank 6). The owner gave the go-ahead
on 2026-10-17, and scikit-learn 1.9.1 was installed for it. The question is narrow: given
price/volume features the desk already computes, can a model that combines them rank next-month
returns better than the desk's RS rank alone? This is **one** experiment. It is not a model
search: there is no feature selection, no hyperparameter tuning, and no second try.

## Pre-registration — written 2026-10-17, BEFORE any forward return was computed

**Panel.** The B-175 panel: nifty500 first 300 names, 1500 days daily
(`screener_pipeline.fetch_ohlcv`), with NIFTY from `fetch_nifty50(days=0)`. Survivorship bias
comes from using today's membership; the bias is the same for every predictor.

**Rebalance dates.** Every 21st session, from the first date with 273 sessions of history to
the last date with 21 sessions ahead, so the forward windows don't overlap.

**Features** (point-in-time at date *d*, using data up to *d* only), fixed now:
1. `rs`: the desk's `_weighted_trailing_return`.
2. `resid`: B-175's 12-1 residual momentum.
3. `r21`: the 21-session return, a reversal candidate.
4. `vol63`: the std of daily log returns over 63 sessions.
5. `dist_hi`: close / 252-session high − 1.
6. `atr_pct`: ATR14 / close.
7. `vol_ratio`: mean volume over 20 sessions / mean volume over 120 sessions.
8. `beta`: the B-175 through-origin β to NIFTY over 252 sessions.

On each date every feature is converted to its **cross-sectional percentile rank**, and a
missing value is set to 0.5. Names with fewer than 6 of the 8 features are dropped on that date.

**Label.** The return from the open of *d+1* to the close of *d+21*. The training target is
the label's cross-sectional percentile rank, and for the classifier, whether the name is in the
top third.

**Models** (2, fixed settings):
* **LOGIT**: `LogisticRegression(C=1.0)` on the top-third label.
* **GBM**: `HistGradientBoostingRegressor(max_depth=3, max_iter=200, learning_rate=0.05,
  random_state=0)` on the label rank.

**Walk-forward, purged + embargoed.** Training is expanding-window. To predict date *t*, a
model trains only on rebalance dates whose label window ends at least 21 sessions before *t*.
That means dates ≤ *t* − 2 rebalances: one period is purged for the overlapping label and one
is the embargo. The model is refit at every *t*. The first prediction needs ≥ 24 training dates.

**Outcome statistic.** On each test date, the Spearman IC of the model's prediction with the
forward return, and the same for **RS** alone (the baseline) on the same names.
ΔIC = IC(model) − IC(RS). The t-test is taken across test dates.

**Economic check** (descriptive gate). Each month the top quintile by prediction is compared
with the equal-weight universe. The top quintile's turnover is charged `COST_INDIAN`
round-trip on the names that change.

**Decision (fixed now).** Each model is tested at Bonferroni α = 0.025.
* **LEARNABLE** if, for at least one model: mean ΔIC > 0 with p < 0.025 **and** mean
  IC(model) > 0 with p < 0.025, **and** ΔIC is positive in ≥ 2 of 3 equal calendar windows,
  **and** the net top-quintile excess is > 0. Then file **B-177r**, a research column that
  is described and has no vote. Whether anything ships is the owner's call.
* **Otherwise NOTHING LEARNABLE.** No model ships. The result is recorded, and that closes
  the desk's ML line except B-119.

**Prior: NOTHING LEARNABLE.** Most of these inputs measured null on their own. On roughly 50
monthly test dates, a mean ΔIC of about 0.02 is all a combined model could plausibly add, and
that is under the noise floor. Expected: IC(model) ≈ IC(RS) ± 0.02, not significant.

## Result

*Not run yet.*
