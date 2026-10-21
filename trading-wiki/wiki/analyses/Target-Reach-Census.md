---
title: "B-116 — Are the targets this desk prints reachable? (target-reach census)"
category: analysis
tags: [b-116, scanners, targets, trade-plan, census, pre-registration]
created: 2026-10-21
updated: 2026-10-21
sources: 0
related:
  - analyses/Open-Backlog
  - analyses/Scanner-Score-Calibration
  - analyses/Backtest-Harness
---

# B-116 — Are the targets this desk prints reachable?

**The question, from [[analyses/Open-Backlog#B-116]]:** 22 of the 56 registered scanners
put an entry, a stop and a target on their cards (`tools/scanner_plan_coverage.json`,
B-171 re-run). The SIGNAL of most of them has been measured; the TARGET of almost none
has. A target hit rate on its own says little — a target 1% away is "reached" from almost
anywhere. So the census asks the two questions that matter:

1. **How often is each scanner's target reached before its stop**, from its own entry,
   with the harness's realistic fill and Indian costs?
2. **Is that more often than the same bracket would be reached from a random bar** of the
   same stock? If not, the target's placement carries no information — the card is
   printing a distance, not a destination.

The plumbing (B-116 2026-09-21), the fresh-signal mode (B-120), the fill models (B-121)
and the WATCH-card contract (B-128) are what the earlier attempts were missing; the
control that failed on 2026-09-21 reproduced on 2026-09-23 once WATCH cards stopped
being traded.

## Pre-registration — written 2026-10-21, BEFORE the census was run

### Panel
* `nse_universe.symbols("nifty500")[150:300]` — **150 names used by neither B-172's
  census (`[:150]`) nor the AB=CD stop study (`[300:500]`)**, the two recent studies
  whose results were chosen on a panel. 1500 trading days daily from
  `screener_pipeline.fetch_ohlcv`, fetched once and frozen for the run.

### Replay (the shared harness, unchanged except one additive field)
* `backtest.backtest_scanner` on **every scanner whose cards carry entry, stop and
  target** (the 22 in `scanner_plan_coverage.json`), with `signal_mode="fresh"`,
  `fill_model="market"`, `exit_model` fixed, `cost_model=COST_INDIAN`,
  `honor_time_stop=True`, stride 1, default warm-up (210) and horizons (max 60).
  Cards with `actionable: False` are counted and not traded (B-128). Side is read off
  the plan geometry (B-102).
* `keep_trades=True`; the only harness change is that each kept trade also records its
  `target` and `time_stop`, so the placebo below can rebuild the bracket.

### Placebo (the baseline), per real trade
* **K = 20 random entry bars** from the same symbol, uniform over the bars the harness
  could have entered on (warm-up+1 … last bar with 60 ahead), seed derived from
  (116, scanner, symbol).
* Entry at that bar's **open**; stop and target at the **same percentage distances** from
  the entry as the real plan, on the same side; same `time_stop`, same 60-bar cap, same
  cost model, same `_simulate_plan`.
* The trade's placebo hit rate and placebo R are the means over its 20 draws.

### Statistics, per scanner
* **Primary:** target-hit rate difference = mean over trades of
  (1 if the real trade ended at its target else 0) − (its placebo hit rate).
* **Secondary:** mean R difference = real R − placebo R, same pairing.
* Uncertainty: **symbol-cluster bootstrap**, 2,000 draws, seed 116; two-sided interval at
  **1 − 0.05/K**, Bonferroni over the K scanners that qualify.
* **Qualifies:** ≥ 30 simulated trades from ≥ 10 symbols. Others are reported as
  counts only, labelled TOO FEW.
* Descriptive, always reported: target / stop / time / open shares, mean R, median bars
  to target, and the counts the harness keeps (signals, not-actionable, unfilled,
  fill-through-stop, fill-past-target).

### Labels (fixed now), on the primary statistic
* **INFORMATIVE** — the interval lies above 0: the target is reached more often than the
  same bracket from a random bar.
* **NO BETTER THAN CHANCE** — the interval contains 0.
* **WORSE THAN CHANCE** — the interval lies below 0.
* **TOO FEW** — does not qualify.

The secondary (R) is reported beside the label and never changes it. A scanner can be
INFORMATIVE on the target and still lose money (a close target with a far stop); the R
column is there so that is visible, not argued away.

### Control, run FIRST — the census does not start unless it passes
* Flag & Pole on `nifty500[:150]`, same settings. It must land within **±5 pp** of the
  2026-09-23 reproduction (**33.8% target / 54.0% stop, n = 645**) on both rates and
  within **±0.10 R** of **+0.26R**, with n within ±15%. Bars are refetched, so exact
  equality is not expected (B-172's re-run drifted 13 hits). A miss stops the run for
  diagnosis, as on 2026-09-21.

### What this may and may not claim
* It measures the **first** target on each card (the harness reads `target[0]`), with the
  card's own stop. It says nothing about later targets, trailing exits (B-124) or
  position sizing.
* INFORMATIVE is not "has an edge": a scanner's signal edge is a separate, already
  published measurement. This census only says whether the printed target is a better
  than random place to expect price to reach.
* 150 survivors (current constituents), ~6 years, one market. No result here changes any
  card, target rule or ranking by itself; any change is its own pre-registered item.
* Not re-run with different settings if the numbers disappoint. A deviation found during
  the run is recorded below with its reason, before the census numbers are read.

## Deviations

*(none yet)*

## Result

*(not run yet)*
