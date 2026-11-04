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

## Result — RUN 2026-10-15: SCORES DO NOT RANK → B-172r filed (OWNER)

`tools/score_calibration_study.py`, run as pre-registered (`2092c88`). **132,174 scored
hits** on 139 of 150 names; **41 scanners qualify** (≥ 90 hits, ≥ 15 symbols, ≥ 3
distinct scores), so the interval is two-sided at 1 − 0.05/41 (α = 0.0012).

### Primary, 20 sessions (run 1, the registered run)
| Label | Scanners |
|---|---|
| **RANKS** (2) | **Renko Flip** +1.54pp [+0.21, +2.74] (only 3 distinct score values) · **ATH Breakout** +2.93pp [**+0.03**, +6.08] |
| **INVERTED** (1) | **Downside Risk** (a risk scanner): a higher risk score was followed by a **better** return, +0.93pp [+0.17, +1.68] |
| NO EVIDENCE | the other 38, including 20 EMA Base, Stage 2, Pullback Entry, Near Pivot, VCP Coiling, Momentum Continuation, Darvas, PEAD, Order Block Retest, Harmonic |
| INSUFFICIENT | EMA-50 Coil, Episodic Pivot, Minervini VCP (valchak), RSI-Fibo Hidden Divergence |

**2 of 41 RANK (< ¼) → decision: file B-172r**, an OWNER question: should `best_score` keep
30% of `rank_score`? Inside the prior (≤ 3 RANK, ≥ 1 INVERTED).

### A defect, and the re-run it forced
Run 1's **60-session** column was broken: a hit whose forward window touched a missing
price carried NaN, and one NaN turned a scanner's whole spread and interval into NaN, which
the labelling read as NO EVIDENCE (10 scanners). **The 20-session column had no NaN and is
unaffected.** Fixed (non-finite outcomes dropped per horizon, with a test). Run 1's output was
kept as `cache/score_calibration_study_run1_nan_defect.json` and the census re-run;
raw rows are now saved (`cache/score_calibration_rows.json`).

**The re-run did not reproduce bit for bit**: the fetched bars shifted (132,161 vs 132,174
hits, max spread change 0.65pp; the same yfinance drift B-41p recorded). **One primary label
moved: ATH Breakout RANKS → NO EVIDENCE** (+2.96pp [−0.05, +6.27]). It sat on the
boundary in run 1, so **its RANKS is not robust**. Renko Flip (RANKS) and Downside Risk
(INVERTED, +0.93pp [+0.06, +1.83]) hold in both runs. The decision is the same either way.

### Secondary, 60 sessions (run 2, defect fixed)
RANKS: **Darvas Box** +2.58pp [+0.15, +5.09]. INVERTED: **Downside Risk** +2.34pp
[+0.28, +4.43] and **VCP Coiling** −2.77pp [−5.85, −0.13] (a higher VCP score was followed by a worse 60-day return).
Everything else: NO EVIDENCE.

### What this says
* For 38–39 of 41 scanners, the 0–100 score **does not separate better hits from worse
  ones** within the scanner. The 30% of `rank_score` that spends `best_score` is, on this
  evidence, mostly ordering by noise. This census cannot say whether cross-scanner
  comparison is meaningful either; it does not test that.
* **Downside Risk's score points the wrong way at both horizons and in both runs**: names it
  rates riskier did better. That deserves a look on its own, but it is a risk flag, not
  a ranking input, so B-172r is still the question that matters.
* The no-score scanners (Liquidity Sweep and six others) still count as 0 in the
  `best_score` race. Nothing here changes that; it is part of the B-172r question.

## Owner decision — B-172r, 2026-10-15
**Keep `best_score`'s 30% of `rank_score` for now, and say so.** The Opportunity Hub
shortlist caption and each card's score-chip tooltip state that the scanner-score term is
unmeasured as a ranking input and is kept by decision, not evidence. No weight changed.
