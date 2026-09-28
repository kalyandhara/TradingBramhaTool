---
title: "MA Bias Edge Test — NULL (B-89)"
category: analysis
tags: [mabias, ema, moving-average, pre-registration, backtest, b-89, measured-null]
timeframe: milestone-plan
created: 2026-09-24
updated: 2026-09-24
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/SVP-Structure-Signal-Pre-Registration.md
---

# MA Bias Edge Test — NULL (B-89)

**MEASURED 2026-09-24. The MA Bias verdict carries no directional edge.**

## What was tested

`maBiasCompute` in `chart_dashboard.html` ships five verdicts — LONG, SHORT,
COUNTER-TREND, CHOP, MIXED — based on a 9/20 EMA cross, 50/200 SMA regime,
stack alignment, and chop/whipsaw gates. It has been rendering badges on the
chart since it was built and was **never scored**. This test fixes that.

**H0:** LONG days and SHORT days are followed by the same forward returns.
**H1:** LONG days are followed by higher returns than SHORT days.

## Design (pre-registered, following [[analyses/SVP-Structure-Signal-Pre-Registration]])

* **Arms:** LONG (A) vs SHORT (B). COUNTER-TREND, CHOP and MIXED are SKIP.
* **Primary:** spread = mean(fwd | LONG) − mean(fwd | SHORT) at **h = 20 sessions**.
* **Reported at** h = 5, 10, 20, 60 — one primary, the rest descriptive.
* **Significance:** circular rotation p, never Welch (state series, autocorrelated).
* **Floor:** 200 LONG days AND 200 SHORT days per arm.
* **Control:** SKIP verdicts should sit near baseline.
* **Basket:** the locked Phase-1 daily set (^NSEI, ^NSEBANK, RELIANCE, TCS, INFY,
  HDFCBANK, ICICIBANK, SBIN), identical to SVP composite and structure tests.

## Results

### Verdict distribution (~4,450 bars per symbol after 200-bar warmup)

The indicator is heavily LONG-biased: ~1,400–1,800 LONG days vs ~430–680 SHORT
days per symbol. CHOP is the second-largest bucket (~1,000–1,600). This is
expected — the Indian market has been in a secular uptrend for most of the sample.

### Forward returns

| h  | n LONG | n SHORT | LONG %  | SHORT % | SKIP %  | base %  | spread  | p_rot |
|----|--------|---------|---------|---------|---------|---------|---------|-------|
|  5 | 12,268 |   4,313 |  +0.14  |  +0.54  |  +0.33  |  +0.29  |  −0.40  | 0.222 |
| 10 | 12,267 |   4,308 |  +0.37  |  +1.18  |  +0.64  |  +0.61  |  −0.82  | 0.185 |
| 20 | 12,257 |   4,297 |  +0.76  |  +2.44  |  +1.31  |  +1.26  |  −1.68  | 0.165 |
| 60 | 12,252 |   4,173 |  +2.41  |  +6.57  |  +4.16  |  +3.84  |  −4.16  | 0.214 |

### Per symbol at h=20

| Symbol       | n LONG | LONG %  | n SHORT | SHORT % |
|-------------|--------|---------|---------|---------|
| ^NSEI        | 1,786  |  +0.69  |    487  |  +2.10  |
| ^NSEBANK     | 1,705  |  +0.90  |    465  |  +3.41  |
| RELIANCE.NS  | 1,184  |  −0.21  |    599  |  +1.16  |
| TCS.NS       | 1,527  |  +1.30  |    553  |  +0.27  |
| INFY.NS      | 1,426  |  +0.51  |    679  |  +2.66  |
| HDFCBANK.NS  | 1,754  |  +1.19  |    407  |  +3.78  |
| ICICIBANK.NS | 1,513  |  +0.29  |    486  |  +3.75  |
| SBIN.NS      | 1,362  |  +1.16  |    621  |  +3.00  |

SHORT outperforms LONG in 7 of 8 symbols.

### Control

SKIP vs baseline at h=20: +0.054pp — near baseline, as expected.

## Decision

**NULL** — spread −1.68%, p_rot 0.165.

The spread is negative (SHORT days are followed by higher returns than LONG days,
i.e. the direction is inverted), but p=0.165 is not significant under the rotation
null. The verdict is NULL, not INVERTED: the evidence is insufficient to claim even
the wrong direction.

## Interpretation

The MA Bias verdict is a **trend-following filter** applied to a sample dominated
by a secular uptrend. SHORT days — when the regime is bearish and all EMAs align
down — are followed by bounce-backs because the market is rising over most of the
window. LONG days — the large majority — capture the average-and-below return
that a crowded bucket always gets. This is the same mean-reversion-in-a-trending-
market artifact that the SVP structure signal showed (B-56).

The indicator is useful for **chart reading** — knowing whether the EMA stack is
aligned, braided, or whipsawing is genuinely informative for context. What it
does not do is generate a directional edge from its verdict labels.

## Consequence

* The MA Bias badge **stays on the chart** — it is a visual aid, not a signal.
* It is **NOT entered into the confluence pipeline** and contributes no score.
* No mirror is shipped. −1.68% at p=0.165 is not evidence of a reverse signal.
* B-89 is **closed as a measured null**.
