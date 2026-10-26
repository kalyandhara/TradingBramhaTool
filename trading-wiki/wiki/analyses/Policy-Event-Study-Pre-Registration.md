---
title: "Policy Event Study — RBI MPC and Union Budget (pre-registered)"
category: analysis
tags: [pre-registration, event-study, b-184, rbi, mpc, budget, sector-indices, null-model, macro]
created: 2026-10-26
updated: 2026-10-26
sources: 0
related: [analyses/Open-Backlog, analyses/Plan-Odds-Baseline-Pre-Registration, analyses/Sector-Rotation-Tool-Architecture]
---

# Policy Event Study — RBI MPC and Union Budget (pre-registered)

**Written before any real-data run. No real-data run has been made at the time
of this commit.** The engine (`tools/event_study.py`) has only ever seen
synthetic prices in its tests.

B-184 asks two questions of the desk's two scheduled policy events:

1. **Magnitude.** On RBI MPC decision days and Union Budget days, do NIFTY and the
   NSE sector indices move more than on ordinary days?
2. **Direction (MPC only).** On cut and hike days, do the rate-sensitive sectors move
   the way the textbook says?

Idea source: a review of marketontology.com/political (2026-10-26). Its political
page is a US policy-to-market product whose ranking is AI-written, not measured.
The one idea worth building first was a measurable **policy event study**,
because the other ideas (a policy→sector map, a catalyst calendar, a
policy-uncertainty regime) all need it to be measured before they are used.
Design: `docs/superpowers/specs/2026-10-26-policy-event-study-design.md`.

This is a measuring instrument for an investment desk (context and filtering), not
a trading signal. A null is calibration.

## Data

- **Prices.** Yahoo daily closes from 2010-01-01. Market is `^NSEI`. The 12 sectors
  are `^NSEBANK ^CNXIT ^CNXPHARMA ^CNXFMCG ^CNXMETAL ^CNXINFRA ^CNXREALTY ^CNXENERGY
  ^CNXAUTO ^CNXPSUBANK ^CNXPSE NIFTY_FIN_SERVICE.NS`. `^CNXMEDIA` is excluded
  because Yahoo serves one bar of it. Sector series start 2010-07 to 2011-09.
- **Special sessions restored from NSE.** Yahoo has no bar for four real budget
  sessions: Sat 2015-02-28, Sat 2020-02-01, Sun 2026-02-01 and 2014-02-17. Those
  closes are taken from NSE's all-indices file for the day (`patch_sessions`).
  Yahoo and NSE closes were checked equal to the paisa on 2026-10-23 for all 13
  series. Snapping instead would make day 0 a two-session return, about √2
  larger, which would bias the magnitude tests upward. This was found and fixed
  during implementation, before any real run.
- **Events.** The events file is `data/events/policy_events.csv` (81 rows):

| set | label | n |
|---|---|--:|
| MPC, scheduled | cut | 11 |
| MPC, scheduled | hike | 8 |
| MPC, scheduled | hold | 40 |
| MPC, unscheduled (27-Mar-2020, 22-May-2020, 4-May-2022) | cut 2 / hike 1 | 3 |
| Budget | full | 16 |
| Budget | interim | 3 |

- **How labels were made.** Each MPC label is derived mechanically from the change
  in repo rate versus the previous meeting.
- **How rows were checked.**
  - MPC dates and rates come from two independent historical tables (tradingqna,
    stableinvestor) and RBI's own FY2026-27 policy page, plus press coverage.
  - The two tables agree everywhere except two weekend dates printed by one of them
    (09-Oct-2021, 08-Oct-2023), which are typos; the other gives 08-Oct-2021 and
    06-Oct-2023.
  - **8 rows rest on a single source** and are marked `SINGLE-SOURCE` in `notes`.
    They are kept in the sample: 2016-12-07, 2017-04-06, 2017-06-07, 2017-10-04,
    2018-10-05 (all holds), 2024-08-08 (hold), 2025-02-07 (cut) and 2025-04-09 (cut).
  - RBI's pre-FY27 archive could not be read row by row.
- **Budget dates.** These come from Wikipedia's Union Budget table plus press.
  2024-07-23 is the budget day; Wikipedia prints the 22nd, which was the Economic
  Survey.
- **Not used.** `time_ist` is informational only. All announcements fall inside the
  session, so a close-to-close day-0 return captures each of them.

## Method

- **Abnormal return (AR).** A market model per sector, with OLS on NIFTY over days
  [−250, −11] before each day and at least 120 observations.
  - A β = 1 version (sector minus NIFTY) is reported alongside as a sensitivity
    check.
  - NIFTY itself is judged on its raw log return.
- **Windows.** pre [−5,−1], day [0], post [+1,+5], drift [0,+20].
- **Null A (every statistic).** 10,000 draws of the same number of trading days, at
  seed 7.
  - Draws come from the same years as the real events and exclude ±10 trading days
    around every event of the set, unscheduled ones included.
  - Budget is calendar-matched: draws come only from the months budgets fall in.
  - p = (1 + #null ≥ real) / (1 + draws), one-sided.
  - A 90 % bootstrap CI (5,000 reps) is given on the real statistic.
- **Null C (cut vs hike only).** 10,000 permutations of the cut/hike labels, with
  bucket sizes preserved.
- **Same computation for real and null.** Real and null statistics are read from the
  same per-session arrays, so they differ only in which days they look at.

## Hypotheses

**Primary — a family of 4, Holm, α 0.05, scheduled events only, day window.**

- **P1:** mean |NIFTY return| on event days is greater than under Null A.
- **P2:** mean cross-sector dispersion (the std of the 12 sectors' AR on the day,
  needing ≥ 6 sectors present) is greater than under Null A.

Each is tested on both sets (MPC, Budget).

**Secondary — MPC scheduled, raw p, power warning.** The basket is an
equal-weighted AR of `^NSEBANK ^CNXPSUBANK ^CNXREALTY ^CNXAUTO NIFTY_FIN_SERVICE.NS`,
needing ≥ 3 members present.

- **S1:** cut days give basket AR > 0 (Null A).
- **S2:** hike days give basket AR < 0 (Null A, tested on negated values).
- **S3:** cut minus hike > 0 (Null C).

Each bucket has 8–11 events. The label is the *decision*, not the *surprise*: a
decision the market expected is priced in before the day, so a null result here
does not rule out a surprise effect.

**Exploratory — no claims.** Per ticker × window × {|CAR|, up, down}, with BH
q-values within each set. Multi-day exploratory windows sum each day's own
rolling-model AR.

**Split half.** Each primary test is re-run on events before 2019-01-01 and on
events from that date, each half with its own null.

## Decision rule (fixed now)

- **"Policy days are volatility events" → desk context flag.** For example, a
  calendar badge reading "RBI day: NIFTY moves ~X× a normal day". Promoted only if:
  - P1 or P2 survives Holm, **and**
  - its ratio (real / null mean) ≥ 1.3×, **and**
  - it holds in both halves, each with p < 0.10 and ratio ≥ 1.2×.
- **"Directional tilt."** Promoted only if S3 p < 0.05 **and** the S1/S2 signs match
  theory (S1 > 0, S2 < 0). Even then it is labelled "decision-conditional, not
  tradeable before the announcement".
- **Anything else is recorded as calibration.** For example, that the market prices
  these events in advance.
- Verdict lines are printed by `run_study` mechanically from these rules. The
  result page copies them and does not re-interpret them.

## Priors (recorded before the run)

- **Budget P1:** likely PROMOTE. Budget days are known high-variance sessions; I
  expect a ratio of ~1.5–2×.
- **Budget P2:** plausible. Budgets re-sort sectors (capex, PSU, consumption).
- **MPC P1:** a weak effect at best, ratio ~1.0–1.3×. Most decisions are
  well-telegraphed holds (40 of 59).
- **MPC directional:** likely CALIBRATION. Decisions are mostly expected, and the
  buckets are small.

## Run

```
py -X utf8 tools/event_study_run.py --events mpc,budget
```

The result goes on [[analyses/Policy-Event-Study-Result]] once the run is done.
