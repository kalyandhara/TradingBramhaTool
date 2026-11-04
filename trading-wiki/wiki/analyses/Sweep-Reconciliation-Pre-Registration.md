---
title: "Sweep Reconciliation (B-186a) — Test Design (pre-registered)"
category: analysis
tags: [pre-registration, b-186a, b-41m, liquidity-sweep, reconciliation, chart-tour, base-rate]
created: 2026-10-27
updated: 2026-10-27
sources: 0
related: [analyses/Chart-Tour-Base-Rates-Result, analyses/Open-Backlog, analyses/Chart-Tour-Base-Rates-Pre-Registration, sources/Web-eVector-Event-Vector-Markets]
---

# Sweep Reconciliation (B-186a) — Test Design (pre-registered)

**Written before any run. At the time of this commit, `tools/sweep_reconcile_study.py`
does not exist and no step below has been computed.**

## Thesis

Two measurements of the same bullish liquidity sweep disagree:

- **B-41m** (2026-09-06, [[analyses/Open-Backlog]] § B-41m): **+0.51 % @20d, p 0.005, net of
  costs**, 1,400 signals on LIQUID_50. This is the desk's one cost-surviving lead.
- **The chart tour's base rate** (2026-10-26, [[analyses/Chart-Tour-Base-Rates-Result]]):
  **ORDINARY**, −0.31 % @20d (p 0.37) on `nifty500[:300]` and −0.11 % on the fresh panel.

This is a **diagnosis**, not a test for an edge. The question is which difference between the
two methods accounts for the gap. Nothing measured here can promote anything.

## Data (fixed)

- One fetch per symbol on the run date: `screener_pipeline.fetch_ohlcv(sym, days=1500)`.
  B-41m's own CLI used this, and the tour's `crt_sweep_overlap._fetch` wraps the same call.
  The same frames are reused by every step.
- **Universe A:** `backtest.LIQUID_50`, as in B-41m.
- **Universe B:** `nse_universe.symbols("nifty500")[0:300]`, keeping names with at least
  810 bars, as the tour did (`EVAL_BARS + 60`).
- **Horizon that decides: 20 sessions.** 5 and 60 are reported, not used.

## The ladder: one change per step, in this order

| Step | Changed from the previous step | Exactly |
|---|---|---|
| **S1** | — (B-41m as shipped) | `backtest.backtest_scanner("Liquidity Sweep", LIQUID_50, fetch, cost_model=COST_INDIAN)`: `signal_mode="all"`, warmup 210, `min_gap` 5, entry at the next open, edge = pooled signal return minus every bar's return, net. Gross is reported beside it. |
| **S2** | **Statistic and timing** → the tour's | The **same signal bars** as S1, re-derived by the study's own replay of the harness loop. Outcome = log(close[t+20] ÷ close[t]) minus that symbol's mean of the same quantity over the same record span, before costs. Averaged per symbol, then across symbols; one-sample t across symbols. |
| **S3** | **Event rule** → the tour's | `tour_base_rates.detector_events` with `det_liquidity_sweep_bull` only: an event is the first bar on which each sweep is visible, and a sweep is identified by its sweep bar. Detection sees the **full history** up to the bar (window 10⁶). Record span unchanged (from bar 210). |
| **S4** | **Period** → the tour's | Record span becomes the last 750 bars of each series (the tour's `EVAL_BARS`). The baseline span follows. |
| **S5** | **Universe** → the tour's | Universe B in place of universe A. |
| **S6** | **Detection window** → the tour's | Each point-in-time evaluation sees only the last 260 bars (`DETECTOR_WINDOW`). This is the tour's method in full and should land near its published −0.31 %. |

Each step reports events, symbols, mean 5/20/60, p20 and the **change in mean20 from the
previous step**.

**Parity checks, reported and not used to tune anything:**
- S2's replay must give the same event count as S1's `n_signals`.
- S6 should be within 0.20 pp of the published −0.31 %. A larger gap is reported as a
  data-date difference, and S1–S6 still stand.

## Decision rules (binding)

1. **Reproduction gate.** S1 "reproduces B-41m" if its 20d net edge is positive and within
   ±0.25 pp of +0.51 %. If it does not, that is the first finding and is reported before
   anything else: B-41m does not hold on today's data. The ladder still runs.
2. **Cause.** The step with the **largest fall in mean20** is named the main cause. Every
   step whose change exceeds **0.25 pp** in either direction is named as contributing.
3. **What each cause leads to.** Fixed now:
   - **S2 (statistic):** B-41m's edge depends on pooling signals, so a few names with many
     signals carry it. Its p-value is overstated. The claim is restated with the
     per-symbol figure.
   - **S3 (event rule):** the tour's card fires on a different bar from the scanner's.
     Follow-up filed: re-measure the card with the scanner's rule. The badge is not changed
     by this study.
   - **S4 (period):** the edge lives before the last 750 bars. B-41m's claim is restated
     as "2020–2023, ordinary since".
   - **S5 (universe):** the edge is a LIQUID_50 (large-cap) result. B-41m's claim is
     restated as "on LIQUID_50; ordinary on NIFTY 500[:300]".
   - **S6 (window):** the tour's 260-bar window misses pools. Follow-up filed: widen the
     detector window for this card and re-measure it.
4. **No promotion, no re-tuning.** No threshold, window or universe is changed in the
   product because of this study. Changes go through the follow-ups above. Claims text
   (the scanner docstring, `opportunity_hub` notes, `named_studies`) is restated to match
   the finding.

## Known limits (stated in advance)

- **The attribution depends on the order.** Changing one thing at a time credits each
  step with any interaction it shares with later steps. The order above was fixed before
  any number was seen. No reverse ladder is run.
- S1 runs on today's data, not 2026-09-06's, so it is about 2.5 months longer at the
  recent end.
- Universe B overlaps universe A. S5 changes the panel, not to a disjoint one.

## Related Pages

- [[analyses/Chart-Tour-Base-Rates-Result]]: the tour's ORDINARY reading
- [[analyses/Open-Backlog]]: B-41m and B-186a
- [[analyses/Chart-Tour-Base-Rates-Pre-Registration]]: the tour's method
