---
title: "Sweep Card, Full Window (B-186d) — Test Design (pre-registered)"
category: analysis
tags: [pre-registration, b-186d, liquidity-sweep, chart-tour, base-rate]
created: 2026-10-27
updated: 2026-10-27
sources: 0
related: [analyses/Sweep-Reconciliation-Result, analyses/Chart-Tour-Base-Rates-Result, analyses/Open-Backlog]
---

# Sweep Card, Full Window (B-186d) — Test Design (pre-registered)

**Written before the run. At the time of this commit, `tools/sweep_full_window_study.py`
does not exist and the fresh-panel number has not been computed.**

## Thesis

[[analyses/Sweep-Reconciliation-Result]] showed that the tour's 260-bar detection window
removes the sweeps of older pools of equal lows, and those carry the positive excess. This
study re-measures the **bullish liquidity sweep card** with the detector seeing the **full
history** up to each bar.

## Not blind on the main panel

The main panel (`nifty500[:300]`, last 750 bars, full history) **is already known**:
reconciliation step S5 read +0.48 %, p 0.10, over 5,119 events. It is reported here again
but **does not decide anything**.

## The deciding test: the fresh panel

- **Panel:** `nifty500[300:500]`, unseen with a full window. The tour's confirmatory panel
  was only ever run with the 260-bar window.
- **Method:** the tour's own, with one change, `window = full history`:
  - an event is the first bar each sweep is visible;
  - the last 750 bars are measured;
  - outcome = 20-day log excess over the stock's own span mean;
  - the statistic is averaged per stock, with a t-test across stocks.
- **Label (fixed now):**
  - **EDGE** if mean20 > 0, the **Bonferroni p** (p × 20, the size of the tour's detector
    family) is < 0.05, at least 2 of 3 thirds are positive, and the tour's floors are met
    (≥ 30 names, ≥ 100 events);
  - **INVERTED** is the mirror of EDGE;
  - **ORDINARY** otherwise.

## Pre-registered actions

1. **Either way,** the live tour feeds this card the full history, so the card fires on the
   same sweeps the scanner does. The window for all other cards stays at 260 bars. This
   follows from the reconciliation, not from this study's result.
2. **The badge entry** for `liquidity_sweep_bull` in `tools/cache/tour_base_rates.json` is
   replaced with the full-window numbers:
   - the main-panel figures are shown;
   - `confirm_label` is the fresh-panel label;
   - `confirmed` is true only if the fresh panel says EDGE.
   
   The main-panel label is computed by the same rule, with Bonferroni over 20.
3. **No other card changes.** The other pool- or swing-based desk cards (structure break,
   AB=CD, flag) are not re-measured here.

## Related Pages

- [[analyses/Sweep-Reconciliation-Result]]
- [[analyses/Chart-Tour-Base-Rates-Result]]
- [[analyses/Open-Backlog]]: B-186d
