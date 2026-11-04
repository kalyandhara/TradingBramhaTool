---
title: "LuxAlgo Machine Learning library vs the desk — gap analysis (2026-10-15)"
category: analysis
tags: [machine-learning, luxalgo, gap-analysis, regime, correlation, calibration, unbacktested-prior]
created: 2026-10-15
updated: 2026-10-15
sources: 1
related:
  - analyses/Open-Backlog
  - analyses/LuxAlgo-SMC-ICT-Gap-Analysis
  - analyses/Backtest-Harness
---

# LuxAlgo Machine Learning library vs the desk — gap analysis

**Source:** luxalgo.com/library, category "Machine Learning": **30 indicators + 25 concepts**,
every page read 2026-10-15. Descriptions are paraphrase, not LuxAlgo text. **Nothing here is
built; every recommendation is an unbacktested prior until it has its own pre-registered
measurement.** Backlog rows: **B-172 … B-178**.

## Two facts that decide the ranking

**1. The desk has almost no ML, and that is not the gap it looks like.** The only learned
component is SuperTrend AI's k-means factor choice (`supertrend_ai.js`), measured **null as a
signal** (B-59r: −1.00% @20d where it alone flipped). scikit-learn is not installed (scipy is).
What the desk DOES have is the part most ML tools skip: a walk-forward harness, a cost model,
point-in-time panels, fresh-signal and fill conventions, a portfolio simulator. That is the
infrastructure for testing a model honestly. Building models without it would be the problem.

**2. LuxAlgo's ML tools are per-chart learners.** A Pine indicator retrains on one symbol's last
100–300 bars and predicts the next 5–10. That is a tiny, overlapping sample. The desk
already declined the same idea once (B-126: k-NN and sigmoid trails "add parameters, not
information"), and its record on added parameters is B-65 / B-59r2. Where ML is worth trying here,
it is **cross-sectional** (500 names × years, scored point-in-time), or it is aimed at
**risk** (volatility, correlation, regime), where the target is forecastable, not at
direction. LuxAlgo's own LSTM page says volatility is the friendlier target.

## Coverage matrix

**Legend:** ✅ built · 🟡 partial / the desk does the same job another way · ❌ missing · 🚫 declined (see below)

### Indicators (30)
| LuxAlgo indicator | What it does (paraphrase) | Desk | |
|---|---|---|---|
| SuperTrend AI (Clustering) | k-means picks the SuperTrend factor from per-factor performance | `stai` overlay; signal measured null (B-59r) | ✅ |
| AI SuperTrend Clustering Oscillator | k-means centroids of close-minus-SuperTrend across a factor sweep | same family as STAI | 🚫 |
| kNN Supertrend Horizon | kNN on RSI/ATR features must agree with SuperTrend | SuperTrend family null; kNN declined (B-126) | 🚫 |
| kNN Market Architecture | kNN keeps only pivots whose features resemble past "good" pivots | structure state has no edge (CHoCH) | 🚫 |
| Structural SVM Ranker | scores each BOS/CHoCH 0–100 from rel. volume, RSI distance, ATR break distance | Structure Break Chain already grades break quality | 🟡 |
| Neighboring Trailing Stop | kNN percentile of nearby prices as a ratcheting stop | declined (B-126 / B-160) | 🚫 |
| AI Channels (Clustering) | k-means centroids of the price window as channel lines | — | 🚫 |
| ML Trendlines Cluster | k-means groups bars, regression line per cluster | trendlines overlay | 🚫 |
| Nadaraya-Watson Envelope / Smoothers | Gaussian kernel regression ± MAD; default mode repaints | — | 🚫 |
| ML Moving Average, GPR, Anchored GPR | Gaussian-process smoother + forward projection | — | 🚫 |
| Recursive Least Squares Forecast | adaptive linear fit + forward "ghost line" and bands | — | 🚫 |
| The Echo Forecast, MACD-Based Forecasting, Indicator Configuration Forecasting, Historical Price Projection | analog forecasts: replay what followed similar past windows/signals | `projection` overlay is EW/pattern-based | ❌ → B-176 |
| Dynamic Time Warping Similarity, Matrix Profile | shape search across history (DTW / all-pairs z-normalized) | — | ❌ → B-176 (parked part) |
| Gaussian Volume Profile, KDE Value Clouds | smooth (fitted / kernel) volume-by-price instead of bins | Volume Profile + SVP (SVP composite measured negative) | 🟡 |
| Gaussian Mixture Models | EM-fitted calm/stressed regimes on returns + volatility | rule-based `classify_regime` + regime gate (B-32 premise proven) | 🟡 → B-174 |
| Correlation Clusters | k-means groups tickers by correlation to a reference | sector exposure only (B-107); no correlation anywhere in the book | ❌ → B-173 |
| Ensemble Voting of Signals | 9 classic indicators vote, netted to −100..+100 | Opportunity Hub already votes scanners, with measured-edge weights and family caps | ✅ (better form) |
| Logistic Signal Calibration | features → sigmoid probability, graded by a reliability table | score-vs-return checked for SVP only (corr −0.041) | ❌ → B-172 |
| Decision Trees, Gradient Boosting, Bagging, Model Stacking | per-symbol supervised learners retrained on 100–300 bars | — | ❌ → B-177 (parked) |

### Concepts (25)
| Concept | Desk | |
|---|---|---|
| K-means regime clustering | STAI uses it for parameters, not regimes | 🟡 |
| Gaussian mixture models, Hidden Markov / Markov-switching regimes, Spectral clustering, Self-organizing maps | rule-based regime only | ❌ → B-174 (GMM first, HMM as its variant; spectral/SOM not needed) |
| PCA | no market-factor decomposition; RS is vs NIFTY only | ❌ → B-175 |
| kNN analog forecasting, Dynamic time warping, Matrix profile | none | ❌ → B-176 |
| Kernel density estimation | VP/SVP binned | 🟡 |
| Kernel regression, Gaussian process regression, Online/incremental learning | none | 🚫 |
| Logistic signal calibration, Bayesian classifiers | none | ❌ → B-172 (calibration as measurement, not a model) |
| Ensemble voting of signals | Opportunity Hub tally | ✅ |
| Decision trees, Random forest, Gradient boosting, Bagging, Model stacking, Support vector machines, Neural networks, LSTM | none | ❌ → B-177 (parked, gated) |
| Reinforcement-learning policies | none | 🚫 |

**Count (55 = 30 indicators + 25 concepts):** ✅ 3 · 🟡 6 · ❌ 30 · 🚫 16. The 30 ❌ items collapse into five backlog rows (B-172 … B-177).

## Recommendations — ranked

### Worth doing
**1. Score calibration census (B-172). Measure only, no model.** Many scanners emit a 0–100
score and the Opportunity Hub ranks by it. Only SVP's score has ever been checked against
returns, and it came out a clean negative. For every scanning model that emits a score:
score terciles → forward return, per-symbol clustered, plus a reliability table. That is the
logistic-calibration page's question asked without fitting anything. It decides whether
"rank by score" within a scanner means anything. Uses the existing harness; no new dependency.

**2. Correlation clusters for the book and the watchlist (B-173). Plumbing.**
`portfolio_risk` reports sector exposure and nothing else; correlation appears nowhere in the
book. Compute 60/120-day return correlations among open positions and watchlist names, group
them (scipy hierarchical clustering), and report the **effective number of independent
bets**, plus which names move as one. That is risk information an investment desk needs, and
it pairs with the sizing helper (LuxAlgo R&E step 1). No edge claim.

**3. Probabilistic regime vs the rule-based verdict (B-174). Measure first.**
Fit a 2–3 component Gaussian mixture (numpy EM, no new dependency) on NIFTY daily returns +
realised volatility, rolling, point-in-time. Pre-register one question: does the
"stressed" probability explain forward NIFTY **volatility and drawdown** better than
`classify_regime`? Volatility, not direction, because volatility clusters and direction
does not. An HMM is the variant to try only if the GMM adds information.

### Measure first, lower priority
**4. Market-factor-neutral (residual) momentum (B-175).** First principal component of
universe returns ≈ the market. Rank names on the return left after removing it (or NIFTY
beta) and pre-register against the existing `rs_rank` on the same cross-section. Residual
momentum is a documented effect elsewhere; here it is a prior.

**5. Analog outcome panel (B-176).** For the chart symbol, find the k most similar past windows
(z-normalised returns; Euclidean first, DTW only if Euclidean shows anything) across its own
history and the universe, and draw the **distribution** of what followed **beside the
unconditional distribution**, never a single path. Display-only with an "unmeasured" card,
then a pre-registered test: does the analog median beat the unconditional one, out of
sample? This covers Echo / MACD / Indicator-Configuration forecasting and Historical Price
Projection in one honest tool.

### Parked (owner gate)
**6. One cross-sectional supervised-learning experiment (B-177).** If ever: a single logistic
regression or shallow gradient-boosted model over features the desk already computes,
labelled by forward return, trained cross-sectionally with **purged, embargoed** walk-forward,
one pre-registration, costs on. Needs a dependency decision (scikit-learn). The prior is low:
most of those features measured null one at a time, and a model combining nulls usually
finds overfitting rather than an edge. It is worth running once only to answer "is anything
learnable here that single-feature tests missed?"

### Declined (B-178, recorded so they aren't re-proposed)
- **ML smoothers and forecasts.** Nadaraya-Watson envelope/smoothers, ML moving average,
  GPR (plain and anchored), RLS forecast. They repaint by default or extrapolate a fit, and
  the desk's trend and MA signals measured null.
- **The SuperTrend / k-means channel family.** AI SuperTrend oscillator, kNN Supertrend,
  AI channels, ML trendlines, kNN market architecture, neighboring stop. STAI already
  measured null (B-59r) and B-126 already declined kNN trails.
- **Structural SVM ranker.** The Structure Break Chain already grades breaks, and CHoCH
  measured no edge.
- **A 9-indicator ensemble vote.** The Opportunity Hub already votes, with measured weights
  and family caps. Voting null signals together doesn't create an edge.
- **KDE value clouds / Gaussian volume profile as new tools.** VP and SVP exist; at most a
  display option for smoother nodes.
- **Per-symbol retrained classifiers** (trees, forests, boosting, bagging, stacking, SVM,
  neural nets, LSTM, Bayes). The sample is too small and overlapping; B-177 is the only form
  worth trying.
- **Matrix profile, online learning, RL policies, SOM, spectral clustering.** Research
  curiosities with no question on this desk that needs them.

## Implementation order
1. **B-172** score calibration census (1 session, measurement only).
2. **B-173** correlation clusters on the book + watchlist (1 session, plumbing).
3. **B-174** GMM regime vs `classify_regime`, pre-registered (1–2 sessions).
4. **B-175** residual momentum vs `rs_rank`, pre-registered (1 session).
5. **B-176** analog outcome panel, display then measure (1–2 sessions).
6. **B-177** only on an explicit owner go-ahead.
