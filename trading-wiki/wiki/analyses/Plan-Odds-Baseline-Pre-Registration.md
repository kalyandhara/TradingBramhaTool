---
title: "Plan-Odds Baseline — Test Design (pre-registered)"
category: analysis
tags: [pre-registration, backtest, b-183, null-model, block-bootstrap, plan-r, stop-target, baseline]
created: 2026-10-25
updated: 2026-10-25
sources: 0
related: [analyses/Backtest-Harness, analyses/Open-Backlog, analyses/ABCD-Stop-Study, analyses/Order-Block-Rules-Pre-Registration]
---

# Plan-Odds Baseline — Test Design (pre-registered)

**Written before any trade has been scored against the baseline.** B-183 adds a
no-edge baseline for trade plans: for each simulated plan, what would the same
entry, stop, target and time stop have returned if the stock had simply kept moving
the way it moved before the signal? This page fixes the engine, the data, the
statistic, the floors and the decision rule while the answers are still unknown.

Idea source: the `trader-timemachine` skill (Jake Schincariol, MIT), which replays
the rest of a US trading day 10,000 times from the stock's own past 5-minute bars.
Its code does not fit this desk (NYSE hours, Yahoo 5-minute bars, long-only, no
costs) and its replay of past trades duplicates `backtest._simulate_plan` in weaker
form. Only the idea is ported, rebuilt on daily bars.

## Why this is needed

Every plan-R number the harness has published is compared against **zero**. Zero is
the wrong null for a plan. A 1R-stop / 3R-target plan on a calm stock and the same
geometry on a volatile one have different expected R before any signal is involved,
because the stop and target sit at different distances from normal noise. A scanner
whose plan R is −0.05 may be doing better than its geometry deserves; one at +0.10
may be doing worse. The harness cannot tell these apart today.

The baseline answers one question per trade: **given this plan's levels and this
stock's own recent behaviour, what R would a signal with no information have
earned?** A scanner has a plan edge only if its trades beat that number.

## The engine (fixed now)

`tools/plan_baseline.py`, `null_plan_odds(...)`:

- **Pool.** The stock's own daily bars **strictly before the entry bar**, the last
  **500** of them. Each bar becomes four ratios to the previous close: open, high,
  low and close. Fewer than **250** usable ratio rows → no baseline for that trade
  (counted as `unbaselined`, never dropped silently).
- **Resampling.** Paths are built from **blocks of 5 consecutive bars** drawn with
  replacement, which keeps short volatility clusters and short-term autocorrelation
  that single-bar draws would destroy. **2,000 replays** per trade.
- **Path.** Start at the fill price. Each simulated bar is the previous simulated
  close times the drawn ratios. The path runs exactly as many bars as the real trade
  had available: the harness horizon (60), shortened by the card's own time stop and
  by the end of the data.
- **Scoring.** Identical to `backtest._simulate_plan`'s fixed exit: stop checked
  before target on every bar, a bar touching both counts as the stop, a stop or
  target fills at its own level, R net of `COST_INDIAN`, outcomes `stop`, `target`,
  `time` or `open`. Long and short are exact mirrors.
- **Output per trade:** `p_target`, `p_stop`, `p_open` and `exp_r` (the mean R over
  the replays).
- **Determinism.** Seed per trade = `SEED (19) XOR crc32("SYMBOL:entry_idx")`. Same
  data → same numbers on any machine.
- **Drift is kept, not removed.** The pool carries the stock's own pre-signal trend.
  That is deliberate: the baseline is "no information beyond what the tape already
  showed", which is the same null as the harness's random-entry baseline.

## Calibration gates (run first; a failure stops the study)

1. **Synthetic parity (unit test).** On a pool built from one repeated block, the
   null is deterministic and must equal `_simulate_plan` on the same bars to 1e-9.
2. **Synthetic calibration (unit test).** On a long Gaussian random walk, random
   plans' realised mean R minus their baseline `exp_r` must be within **±0.03R**
   over ≥ 2,000 plans.
3. **Placebo arm (on real data).** A registered scanner `_B183 Placebo` fires on
   every 5th bar with entry = next open, stop = entry − 1.0×ATR14, target =
   entry + 2.0×ATR14, time stop 10. Its mean per-symbol `d` (below) must satisfy
   **|mean d| ≤ 0.05R or p ≥ 0.05**. If it fails, the baseline is miscalibrated:
   no scanner verdict is published, and any engine change needs a written
   amendment on this page before it is re-run.

## The test

- **Harness:** `backtest.backtest_scanner`, `cost_model=COST_INDIAN`,
  `signal_mode="fresh"`, `fill_model="market"`, `keep_trades=True`, horizons
  unchanged (max 60), fixed exit.
- **Panel:** `nu.symbols("nifty500")[0:300]`, 1500 calendar days.
- **Scanners:** every entry in `scanner_templates.SCANNERS` (excluding names that
  start with `_`) whose hits produced at least one simulated plan.
- **Per trade:** `d = r − exp_r` (realised R minus baseline expected R, both net).
- **Primary statistic per scanner:** the mean of `d` within each symbol, then a
  one-sample t-test across symbols (H0: mean = 0). Clustering by symbol keeps one
  busy stock from deciding the verdict.
- **Multiple comparisons:** Holm–Bonferroni across all scanners that clear the
  floors, family α = **0.05**, two-sided.
- **Floors:** ≥ **30 symbols** and ≥ **100 baselined trades**. Below either →
  `THIN`, reported directional-only.
- **Stability:** trades split into thirds by entry date; the sign of mean `d` must
  agree in **≥ 2 of 3** thirds.

**Secondary, descriptive only (can never be promoted to a verdict):** realised
target-first rate versus mean `p_target`; and the share of each scanner's plans
whose baseline `p_stop` ≥ 0.60 ("stop inside normal noise"). The latter is input for
roadmap step 4 (stop audit), not a finding here.

## Decision rule (fixed in advance)

| Verdict | Condition | Action |
|---|---|---|
| **BEATS BASELINE** | mean d > 0, Holm p < 0.05, floors met, stable in ≥ 2/3 thirds | Scanner Hub and plan cards may say "beats the no-edge baseline (B-183)". No tier or weight change in this item. |
| **BELOW BASELINE** | mean d < 0, same conditions | Card says "plan worse than the no-edge baseline (B-183)"; a follow-up item is filed on that scanner's stop/target geometry. No tier change here. |
| **AT BASELINE** | floors met, not significant or not stable | Label "at no-edge baseline". No claim either way. |
| **THIN** | below floors | Label "baseline unmeasured (thin)". |

What ships **regardless of results**: the engine, the harness hook, and the
Watchlist plan column showing each PENDING or LIVE plan's no-edge odds
(target first / stop first). Those are descriptive numbers about the plan's
geometry, not claims about the scanner.

## Prior (stated before the run)

Most scanners land **AT BASELINE**: at least 80 % of those that clear the floors.
**None** comes out BEATS BASELINE after Holm. This follows B-19 (0 of 41 scanners
with a stable edge after costs) and the run of measured nulls since. A BELOW result
for one or two scanners would not be surprising: some plans place stops inside
normal noise.

## Outcome (fill in later)

Not run.

## Related Pages

- [[analyses/Backtest-Harness]]: the harness and `_simulate_plan`, whose scoring this baseline mirrors
- [[analyses/Open-Backlog]]: B-183
- [[analyses/ABCD-Stop-Study]]: the `keep_trades` per-symbol design this study follows
- [[analyses/Order-Block-Rules-Pre-Registration]]: precedent for a pre-registered plan measurement
- Implementation plan: `docs/superpowers/plans/2026-10-25-plan-odds-baseline.md`
