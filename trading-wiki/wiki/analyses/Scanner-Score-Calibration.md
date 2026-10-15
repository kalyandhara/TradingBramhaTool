---
title: "B-172 — Does each scanner's own score rank its hits? (calibration census)"
category: analysis
tags: [b-172, scanners, score, calibration, opportunity-hub, pre-registration]
created: 2026-10-15
updated: 2026-10-15
sources: 0
related:
  - analyses/Open-Backlog
  - analyses/LuxAlgo-Machine-Learning-Gap-Analysis
  - analyses/Backtest-Harness
---

# B-172 — Does each scanner's own score rank its hits?

From [[analyses/LuxAlgo-Machine-Learning-Gap-Analysis]] (rank 1; LuxAlgo's "logistic
signal calibration", asked as a measurement with no model fitted).

**Why it matters, read from the code:** `rank_score` = 0.45 × overall rating + **0.30 ×
`best_score`** + 0.25 × confluence (`opportunity_daily.W_*`), and `best_score` is the
**maximum score across every scanner that hit the name**. So 30% of the Opportunity Hub's
ranking assumes each scanner's 0–100 score means "better setup", and that scores from
different scanners are comparable. Only SVP's score has ever been checked against returns
(corr −0.041, a clean negative). This census checks the first assumption, within each
scanner. It does not test cross-scanner comparability.

**Descriptive fact, from the code, not the run:** at least seven registered scanners
emit **no** `score` (Liquidity Sweep, Liquidity Sweep Bear, FVG Pullback, Flag & Pole,
Inverted Flag & Pole, Support Breakdown, ICT Setup; also No-Supply, from a 3-name probe). In the `best_score` max they count as 0, so the
desk's best-measured signal (Liquidity Sweep, B-41m) never contributes to the 30%
scanner-score part of the rank.

## Pre-registration — written 2026-10-15, BEFORE the census was run

### Panel and replay
* `nse_universe` "nifty500", **first 150 names**, 1500 days daily (`screener_pipeline.fetch_ohlcv`).
* **Every registered scanner**, as shipped, called on `df.iloc[:t+1]` for every **5th** bar
  *t* from bar 300 (warm-up) to the last bar with 60 sessions ahead. Hits at consecutive
  strides of one setup are correlated, so all uncertainty is clustered by symbol.
* A hit enters the census if its card carries a numeric `score`.

### Outcome
* **Primary:** 20-session forward return, from the next session's open to the close 20
  sessions later, **minus that symbol's mean 20-session return over the same evaluation
  span** (removes each name's own drift). Costs are a constant per trade, so they cancel in a
  within-scanner spread and are not applied.
* **Secondary:** the same at 60 sessions.

### Statistic, per scanner
* Terciles of the scanner's **own** score distribution in the sample (rank-based, ties
  broken by order of occurrence). **Spread = mean outcome of the top tercile − mean outcome of the bottom tercile.**
* Uncertainty: **symbol-cluster bootstrap** (resample symbols with replacement), 2,000
  draws, seed 172. The interval is two-sided at **1 − 0.05/K**, Bonferroni over the K
  scanners that qualify.
* Direction: for bullish scanners a useful score has spread > 0. For scanners in
  `opportunity_hub.RISK_SCANNERS` a useful score has spread < 0 (a higher risk score means a worse
  forward return).

### Labels (fixed now)
* **RANKS**: the interval excludes 0 on the useful side.
* **INVERTED**: the interval excludes 0 on the wrong side.
* **NO EVIDENCE**: the interval includes 0.
* **INSUFFICIENT**: fewer than 90 scored hits or fewer than 15 symbols.
* **NO SPREAD**: fewer than 3 distinct score values, so terciles do not exist.

### Consequence (fixed now)
**Report only; no code changes in this item.** If **fewer than a quarter** of the
qualifying scanners RANK on the primary horizon, file **B-172r** as an OWNER decision:
should `best_score` keep its 30% of `rank_score`? Any scanner labelled INVERTED is listed
for review by name.

### Prior, stated so the result can be wrong against it
**Most scores do not rank.** Expected: RANKS for **at most 3** of the K scanners, at least
one INVERTED. The desk's single scored-composite check (SVP) was a clean negative, and most
scanner signals measured near-null in B-19. A score built from the same ingredients has
little room to separate good hits from bad.

## Result

*(appended after the run — the section above is not edited after it)*
