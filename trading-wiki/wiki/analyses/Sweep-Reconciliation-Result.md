---
title: "Sweep Reconciliation (B-186a) — Result: the tour's 260-bar window hides the sweeps that work"
category: analysis
tags: [b-186a, b-41m, liquidity-sweep, reconciliation, chart-tour, result]
created: 2026-10-27
updated: 2026-10-27
sources: 0
related: [analyses/Sweep-Reconciliation-Pre-Registration, analyses/Chart-Tour-Base-Rates-Result, analyses/Open-Backlog]
---

# Sweep Reconciliation (B-186a) — Result

This was run exactly as pre-registered on [[analyses/Sweep-Reconciliation-Pre-Registration]]
(`d05b294`). The script `tools/sweep_reconcile_study.py` was committed at `61a2a47`, before
the run. The output is in `tools/cache/sweep_reconcile.json`.

## Thesis

B-41m found the bullish liquidity sweep at +0.51 % over 20 days, but the chart tour found it
ordinary. The study walks from B-41m's method to the tour's, changing one thing at a time, to
find which difference accounts for the gap.

## The ladder (20-session excess)

| Step | Change | Events | Names | mean20 | Change | p |
|---|---|---|---|---|---|---|
| S1 | B-41m as shipped (net of costs) | 1,434 | 50 | **+0.54 %** | — | 0.003 |
| S2 | the tour's statistic | 1,434 | 50 | +0.80 % | +0.26 pp | 0.0003 |
| S3 | the tour's event rule | 1,809 | 50 | +0.61 % | −0.19 pp | 0.008 |
| S4 | the tour's period (last 750 bars) | 1,135 | 50 | +0.55 % | −0.06 pp | 0.10 |
| S5 | the tour's universe (nifty500[:300]) | 5,119 | 257 | +0.48 % | −0.08 pp | 0.10 |
| **S6** | **the tour's 260-bar detection window** | **2,425** | **252** | **−0.31 %** | **−0.78 pp** | 0.37 |

**Checks:**
- **Reproduction gate passed.** S1 is +0.54 % net (+0.55 % gross), within ±0.25 pp of +0.51 %.
- **S2 parity passed.** The study's own replay found 1,434 signal bars, the same as the
  harness's `n_signals`.
- **S6 matches the published tour number** (−0.31 %) to the hundredth.

## Conclusion

**The main cause is S6, the 260-bar detection window (−0.78 pp).** S2 also counts as
contributing under the rule (+0.26 pp), but it moves *towards* B-41m: per-symbol averaging
makes the sweep look better, not worse.

On the tour's own universe and period, a detector that sees the full history still reads
**+0.48 %** (S5). Cutting its view to the last 260 bars (S6) **halves the events, from 5,119 to
2,425, and turns the mean negative**. The sweeps that disappear are the ones taking out pools of
equal lows formed more than about a year earlier, and those are where the positive excess
lives.

What this means:
- **B-41m's claim stands.** It reproduces on today's data.
- **The tour's ORDINARY badge measures a different, narrower card** than the scanner, because
  of how the tour's detector is fed rather than the pattern itself.

**What this does NOT say.** S4 and S5 (+0.55 %, +0.48 %) have p ≈ 0.10 at the per-symbol
level. Outside LIQUID_50, and over only the last three years, the sweep is positive but **not
established**. Nothing here is promoted (pre-registration rule 4).

## Action taken / plan

- **Pre-registered action for S6:** filed **B-186d**. Widen the detector window for the sweep
  card (and check the other pool- or swing-based desk cards), then re-measure that card's base
  rate as its own pre-registration.
- **The badge is unchanged until then**, and no product threshold changed.
- The scanner docstring and opportunity_hub notes need no change: B-41m reproduced.

## Outcome (fill in later)

## Related Pages

- [[analyses/Sweep-Reconciliation-Pre-Registration]]
- [[analyses/Chart-Tour-Base-Rates-Result]]: the ORDINARY reading explained here
- [[analyses/Open-Backlog]]: B-41m, B-186a, B-186d
