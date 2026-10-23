---
title: "B-116 — Are the targets this desk prints reachable? (target-reach census)"
category: analysis
tags: [b-116, scanners, targets, trade-plan, census, pre-registration]
created: 2026-10-21
updated: 2026-10-21
sources: 1
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

**1 · 2026-10-21 — the control failed, and the cause is the `fresh` rule; census
switched to a new `fresh_plan` mode. Recorded before any census number was read.**

* **The miss:** Flag & Pole on `nifty500[:150]` gave **134 trades** (29.1% target / 63.4%
  stop / +0.22R) against the registered 645 (33.8% / 54.0% / +0.26R): n off by 79%, stop
  rate off by 9.4 pp. The run stopped there, as registered.
* **The cause, counted:** `signal_mode="fresh"` counts a signal only on the first bar
  a scanner hits. Since B-128 a flag fires as a non-actionable WATCH card for several bars
  before it breaks, so **the breakout bar is almost never fresh** and its trade is dropped.
  On 25 control names, of 99 first-actionable cards **81 came straight after a WATCH bar**
  (lost) and 18 on a fresh bar. 1,399 of 1,535 signals were WATCH cards. The 2026-09-23
  reproduction filtered to broken cards ad hoc, outside the harness, so it never met this.
* **The change:** `backtest.SIGNAL_MODES` gains `fresh_plan` — freshness is judged on the
  *tradeable* card: a card with `actionable: False` counts as no tradeable state and is
  counted, not signalled; the first actionable card after it is a fresh trade. Plain
  `fresh` is unchanged, so no published number moves. Test:
  `test_fresh_plan_trades_the_break_that_follows_a_watch_card`.
* **Everything else in the registration stands**, including the control and its
  tolerances, which `fresh_plan` must now pass before the census runs.
* **Consequence beyond this study, filed not fixed:** every run since B-128 that used
  `fresh` on a scanner that emits WATCH cards undercounted its breaks — at least B-124's
  exit bake-off and B-128's Falling Wedge re-measurement. Whether that moves either
  verdict is a re-run question for the backlog, not for this census.

## Result

**Run date:** 2026-10-21. Panel: `nifty500[150:300]`, 150 symbols (149 with data).
Qualifying K = 21, Bonferroni α = 0.0024. RSI-Fibo Hidden Divergence: TOO FEW (n=22).

**Verdict: every qualifying scanner is NO BETTER THAN CHANCE.**

No scanner's target-hit-rate interval lies above 0. None lies below 0 either.
The printed targets carry no detectable placement information relative to a
random bracket of the same width drawn from the same stock at a random bar.

### Per-scanner table

| Scanner | n | sym | tgt% | stop% | R | placebo tgt% | Δhit [lo,hi] | ΔR [lo,hi] | Label |
|---------|---|-----|------|-------|---|---|---|---|---|
| %R Bottoming | 1423 | 141 | 34.9 | 58.3 | +0.06 | 34.0 | +0.008 [−0.028,+0.048] | +0.00 [−0.11,+0.13] | NO BETTER THAN CHANCE |
| Breakout Retest | 909 | 132 | 8.9 | 39.3 | +0.09 | 9.4 | −0.005 [−0.033,+0.025] | +0.07 [−0.09,+0.30] | NO BETTER THAN CHANCE |
| Bullish CHoCH (last 5 sessions) | 1677 | 143 | 27.4 | 40.6 | +0.18 | 27.0 | +0.003 [−0.023,+0.033] | −0.02 [−0.09,+0.06] | NO BETTER THAN CHANCE |
| Double Bottom | 1163 | 133 | 34.4 | 63.8 | +0.13 | 33.0 | +0.014 [−0.038,+0.069] | +0.07 [−0.12,+0.26] | NO BETTER THAN CHANCE |
| Falling Wedge | 375 | 123 | 34.9 | 44.3 | +0.01 | 33.4 | +0.015 [−0.053,+0.086] | −0.02 [−0.19,+0.16] | NO BETTER THAN CHANCE |
| Flag & Pole | 636 | 134 | 37.3 | 52.8 | +0.35 | 31.4 | +0.059 [−0.004,+0.115] | +0.15 [−0.07,+0.36] | NO BETTER THAN CHANCE |
| FVG Pullback | 3752 | 143 | 34.3 | 60.2 | +0.05 | 35.2 | −0.009 [−0.029,+0.013] | −0.06 [−0.13,+0.00] | NO BETTER THAN CHANCE |
| Harmonic Reversal (XABCD) | 1141 | 141 | 36.4 | 22.7 | +0.06 | 34.0 | +0.024 [−0.008,+0.060] | +0.06 [−0.03,+0.15] | NO BETTER THAN CHANCE |
| HM Buy (Hilega Milega) | 3835 | 142 | 20.5 | 40.3 | +0.04 | 20.9 | −0.004 [−0.022,+0.013] | +0.02 [−0.04,+0.07] | NO BETTER THAN CHANCE |
| ICT Setup | 380 | 101 | 25.0 | 72.9 | +0.49 | 24.1 | +0.009 [−0.079,+0.113] | +0.49 [−0.33,+2.12] | NO BETTER THAN CHANCE |
| Inverted Flag & Pole | 561 | 136 | 8.4 | 77.7 | −0.43 | 10.4 | −0.020 [−0.061,+0.016] | −0.14 [−0.35,+0.04] | NO BETTER THAN CHANCE |
| Liquidity Sweep | 2819 | 142 | 34.3 | 65.1 | −1.04 | 33.8 | +0.005 [−0.020,+0.030] | +0.03 [−0.08,+0.16] | NO BETTER THAN CHANCE |
| Mean Reversion (Connors RSI2) | 153 | 86 | 14.4 | 73.2 | −0.31 | 17.4 | −0.030 [−0.097,+0.040] | −0.18 [−0.58,+0.21] | NO BETTER THAN CHANCE |
| Order Block Retest | 4893 | 144 | 14.9 | 40.0 | +0.01 | 14.4 | +0.004 [−0.008,+0.018] | +0.01 [−0.05,+0.08] | NO BETTER THAN CHANCE |
| RSI 60-40 Setup | 4443 | 144 | 17.4 | 33.7 | +0.06 | 16.9 | +0.005 [−0.015,+0.027] | −0.00 [−0.06,+0.06] | NO BETTER THAN CHANCE |
| RSI Divergence Bear | 965 | 141 | 5.7 | 35.2 | −0.14 | 6.9 | −0.012 [−0.032,+0.009] | −0.00 [−0.09,+0.09] | NO BETTER THAN CHANCE |
| RSI Divergence Bull | 379 | 125 | 47.8 | 47.8 | −0.26 | 45.4 | +0.024 [−0.034,+0.082] | −0.08 [−0.36,+0.19] | NO BETTER THAN CHANCE |
| RSI-Fibo Hidden Divergence | 22 | 21 | 45.5 | 27.3 | −0.10 | 48.0 | — | — | TOO FEW |
| Rounding Bottom | 695 | 137 | 33.5 | 57.1 | +0.42 | 28.8 | +0.047 [−0.006,+0.117] | +0.24 [−0.03,+0.53] | NO BETTER THAN CHANCE |
| Support Breakdown | 7672 | 143 | 3.1 | 72.6 | −0.38 | 3.5 | −0.004 [−0.009,+0.002] | −0.08 [−0.45,+0.14] | NO BETTER THAN CHANCE |
| VCP Coiling | 1704 | 144 | 31.5 | 56.9 | +0.11 | 32.5 | −0.010 [−0.045,+0.023] | −0.06 [−0.18,+0.06] | NO BETTER THAN CHANCE |
| VWAP Mean Reversion | 848 | 138 | 33.3 | 58.7 | −0.26 | 32.7 | +0.005 [−0.040,+0.051] | −0.12 [−0.28,+0.05] | NO BETTER THAN CHANCE |

### What this means — and does not mean

* **Targets are not wrong places.** The interval contains 0 for every scanner: the
  target is reached about as often as a random bracket of the same width would be.
  That is the null result, not a negative one. Price does reach these targets; the
  scanner is simply not selecting bars from which it reaches them *more* reliably.
* **R varies widely.** ICT Setup (+0.49R) and Rounding Bottom (+0.42R) have
  economically meaningful positive R despite NO BETTER THAN CHANCE on the target
  itself, because their stop distances are well-placed relative to the bracket.
  Inverted Flag & Pole (−0.43R) and Liquidity Sweep (−1.04R) are the opposite.
  This is a stop-placement finding, not a signal finding.
* **Flag & Pole is the closest to INFORMATIVE** (Δhit lower bound −0.004, just
  below 0 after Bonferroni). On the census panel (150:300) it ran 636 trades vs
  629 in the control (150 names); the gap is consistent with the panel overlap from
  one delisted name (BAGMANE).
* **This census says nothing about signal edge.** Signal edge (does the scanner
  identify a better entry?) is separately measured for most scanners and is not
  reopened here. A scanner can have a real entry edge and still have NO BETTER THAN
  CHANCE targets — the target placement rule may simply be a heuristic.
* **Action:** no card, target rule or scanner ranking changes as a result of this
  census alone. Any change is a separate pre-registered item. The census is on file
  for use as prior evidence in future target-placement studies.
