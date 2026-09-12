---
title: "PCR Sign Convention — Test Design (pre-registered)"
category: analysis
tags: [pcr, sentiment-index, pre-registration, sign-convention, options, backtest, b-22r]
created: 2026-09-11
updated: 2026-09-11
sources: 0
related: [analyses/Open-Backlog, analyses/PCR-in-OI-Momentum, analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14, analyses/SVP-Signal-Backtest-Design]
---

# PCR Sign Convention — Test Design (pre-registered)

**Written before any forward return has been looked at.** B-22 shipped the fifth
sentiment factor (PCR level + slope on NIFTY, weight 20 of 100) with its direction
chosen by assumption. This fixes the test, the data, the floor, the controls and
the decision rule — including what happens on a null — while the answer is still
unknown.

## Why this is not a footnote

[[analyses/Open-Backlog#B-44r]] is the precedent. GEX shipped with the naive sign
convention, was measured, and the convention turned out **backwards for NSE** — the
indicator was retired outright. PCR is the same shape of assumption made by the same
kind of reasoning, and it currently carries **20% of a score the desk reads daily**.

## What is being tested

`sentiment_index.pcr_factor` scores

    factor = PCR_LEVEL_SHARE × level_percentile + (1 − PCR_LEVEL_SHARE) × slope_percentile
           = 0.7 × level_pct + 0.3 × slope_pct          (each in [0,1])

under `PCR_SIGN_CONVENTION = "trend_following"` — **a high or rising NIFTY PCR reads
bullish**. The contrarian convention is the exact opposite: a high PCR means puts are
crowded, which reads as capitulation and therefore bullish-contrarian, or as a
warning, depending on who is telling the story. `pcr.py` deliberately declines to
pick. Both `PCR_SIGN_CONVENTION` and `PCR_LEVEL_SHARE` are recorded in code as
unmeasured priors so this test has something to vary.

**H0:** the factor carries no directional information about NIFTY forward returns.
**H1 (trend-following, as shipped):** high factor → higher forward return.
**H1' (contrarian):** high factor → lower forward return.

The test is two-sided precisely because the desk does not get to claim a direction
after seeing the data.

## The blocker was false — and that is this item's first finding

The backlog carried B-22r as *blocked on data*: `pcr_index_history` began
accumulating 2026-09-11, `MIN_PCR_HISTORY = 60`, so the earliest measurement looked
like **December 2026**.

**It is not blocked.** `nse_oi_momentum._download_bhavcopy(session, day)` takes an
arbitrary date and NSE's F&O bhavcopy archive is date-templated. Probed
2026-09-11 — files return `200` with a valid zip at 3, 30, 90, 180, 365 and **730
days back** (30k–48k rows each). **The baseline is backfillable, so the test can run
now rather than in three months.** Counting first beat waiting, again.

> [!warning] The backfill is a data-collection step and must not touch live state
> Backfilled rows are written to the SAME `pcr_index_history` table the live factor
> ranks against, so a bug there corrupts the daily score rather than just the study.
> The backfill therefore (a) writes only historical dates, (b) is idempotent per
> `(date, symbol)` like `_record_pcr` already is, and (c) is verified by re-deriving
> today's live reading after the backfill and confirming it is unchanged.

## Data

| | |
|---|---|
| **Signal** | NIFTY index PCR (total put OI / total call OI, all expiries) from the NSE F&O bhavcopy, via `pcr.build_pcr_table(raw, CLASS_INDEX)` — the same function the live factor uses, not a reimplementation |
| **Outcome** | `^NSEI` daily close-to-close forward return (yfinance), the same series input #3 already uses |
| **Window** | as deep as the archive serves, target ≥ 2 years of sessions |
| **Liquidity** | `MIN_OPTION_OI[CLASS_INDEX]` applies exactly as in production; illiquid days are excluded, not scored |

## Point-in-time discipline

The live factor ranks today's PCR against **all stored history**, which at run time
is past-only. The study must reproduce that and nothing more: for each session *t*,
percentiles are computed against sessions **strictly before t**, and no day is scored
until **60 prior sessions** exist (`MIN_PCR_HISTORY`), exactly as production refuses
to. Any expanding-window statistic computed over the full sample would leak the
future into the rank and is disqualifying.

## Decision horizon and floor

- **Decision horizon: 5 trading days.** One horizon decides; 1d / 10d / 20d are
  computed and reported as **descriptive only**. Picking the best horizon after the
  fact is how a null becomes a finding.
- **Pre-registered floor: ≥ 200 scored sessions.** Below that the result is
  **UNDERPOWERED, not null** — the same call [[analyses/Open-Backlog#B-58]] earned at
  53 events against this same floor.

## Statistic and significance

Top tercile of the factor vs bottom tercile, difference in mean forward 5d return:

    delta = mean(fwd5 | factor in top third) − mean(fwd5 | factor in bottom third)

- `delta > 0` is evidence for the shipped trend-following convention.
- `delta < 0` is evidence the convention is **backwards**.

Overlapping 5-day windows autocorrelate, so a plain t-test overstates significance.
**Pre-registered: a moving-block bootstrap, block length 10 (2× the horizon), 5,000
resamples, two-sided, α = 0.05.** The t-statistic is reported alongside it for
comparison, and where the two disagree **the bootstrap governs**.

## Controls — both required, and both are tests of the harness, not of PCR

1. **Planted effect.** A synthetic factor built from the actual forward return is run
   through the identical pipeline; the study must detect it at p < 0.01. *A null from
   a detector that cannot see anything is not a null.*
2. **Shuffle.** Factor values are randomly permuted against dates, 200 times; the
   observed `delta` must not be typical of that distribution. This catches a pipeline
   that manufactures a spread out of drift alone.

Failing either control invalidates the run regardless of what PCR scored.

## Secondary, explicitly non-decisive

- **level-only** (`PCR_LEVEL_SHARE = 1.0`) and **slope-only** (`0.0`) — does the
  0.7/0.3 blend hide one informative half behind an uninformative one?
- The same three horizons on each arm.

These describe; they do not rescue. If the primary is null, a secondary that scores
is a hypothesis for a future pre-registration, not a result.

## Decision rule — written now, so the desk does not get to choose later

| Outcome at 5d | What happens to the factor |
|---|---|
| `delta > 0`, p < 0.05 | Convention **confirmed**. `convention_measured: True`, sign stays `trend_following`, the measured numbers go in the docstring. |
| `delta < 0`, p < 0.05 | Convention is **backwards**. Flip `PCR_SIGN_CONVENTION` to `contrarian`, record the measurement, and re-verify the live score changes as expected. This is the B-44r outcome, and flipping is only legitimate because it was pre-registered here. |
| p ≥ 0.05, n ≥ 200 | **NULL.** The factor keeps its place on the page but **stops carrying score**: it reverts to `NOT_CHECKED` and its weight 20 renormalises away, exactly as it does today. A factor whose direction the data cannot support must not push a number the desk reads. **It is not deleted** — a null is not evidence of harm, the standing rule since [[analyses/Open-Backlog#B-66]]. |
| n < 200 | **UNDERPOWERED.** No change to the code, and the item stays open with the shortfall recorded. Not a null. |

**The null branch is the one that matters**, because it is the one the desk has
historically flinched from: four of the five sentiment factors were measured on
2026-09-10 and **none discriminated**, and nothing was re-weighted on that result.
Here the consequence is agreed in advance — an unmeasurable direction does not get to
score 20 points.

## What this test cannot say

- It tests **NIFTY index PCR only**. The stock cross-section PCR (`calibrate_stock`,
  `classify_stock`) is a different instrument class with a structurally different
  ratio and is out of scope.
- It tests the **sign and the blend**, not the **weight**. Whether 20 is the right
  weight is the roadmap's weight-fitting step and is a separate question.
- A confirmed sign is not an edge claim for the composite sentiment score, which
  [[analyses/Open-Backlog#B-66]] already measured as non-discriminating.

## Related Pages

- [[analyses/Open-Backlog]] — B-22, B-22r, B-44r, B-66
- [[analyses/PCR-in-OI-Momentum]] — where the PCR primitive came from
- [[analyses/SVP-Signal-Backtest-Design]] — the pre-registration pattern this follows
