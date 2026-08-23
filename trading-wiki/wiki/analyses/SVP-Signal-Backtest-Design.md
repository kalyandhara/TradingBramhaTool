---
title: "SVP Confluence Signal — Backtest Design (pre-registered)"
category: analysis
tags: [volume-profile, session-volume-profile, backtest, triple-barrier, confluence, pre-registration, factor-weights]
created: 2026-08-23
updated: 2026-08-23
sources: 0
related: [concepts/Volume-Analysis, analyses/Backtest-Harness, concepts/Order-Flow]
---

# SVP Confluence Signal — Backtest Design (pre-registered)

Pre-registration for testing the confluence BUY/SELL/trap-reversal engine
`SVP.buildSignal` (in `tools/session_volume_profile.js`). **Written before any
forward returns are looked at.** Same discipline as the SBC vedha event study:
fix the signal, the labels, the null, and the decision rule up front; a clean
negative is a valid, useful result.

## What is being tested

`SVP.buildSignal(sessions, bars, composite, trap, ad)` scores 7 factors, each a
signed ±1 × a hand-set prior weight (`SIG_W`): **regime** 1.0, **va** 1.2,
**trap** 1.5, **exhaustion** 1.0, **sequence** 0.8, **sweep** 1.0, **cluster**
0.5. Net = bullW − bearW → BUY / SELL / NEUTRAL, with `kind` ∈ {trap-reversal,
breakout, continuation} and a target + invalidation. **Every weight is an
unbacktested prior.** Two questions:

- **Q1 — edge:** does the composite BUY/SELL read have directional edge over the
  base rate?
- **Q2 — weights:** which of the 7 factors actually carry signal, and do fitted
  weights beat the equal-prior baseline *out-of-sample*?

## Architecture — backtest the real engine, don't reimplement it

The engine is pure JS on `globalThis` and runs headless in Node. The harness
imports the **actual** `volume_profile.js` + `session_volume_profile.js` and
walks it forward bar-by-bar — no Python port, zero reimplementation drift (see
the Elliott-Wave "documented-but-not-coded gap" lesson). Python does only stats,
reusing yfinance as the single price source.

```
svp_backtest_export.py  (yfinance) → cache/backtest/<sym>_<tf>.json  (bars)
svp_backtest_runner.js  (Node)     → at bar i: SVP.analyze(bars[0..i])
                                     → <sym>_<tf>_signals.csv (signal + per-factor family features)
svp_backtest.py         (Python)   → triple-barrier + fixed-horizon study, base rate,
                                     permutation null, factor attribution, (gated) fitted weights
```

## No look-ahead / repainting

- `SVP.analyze(bars[0..i])` sees only bars ≤ i; barrier outcomes use strictly
  bars > i. Clean.
- **Repainting caveat:** the *current* (last) session is still forming at bar i,
  so its shape/POC is provisional and can change as it completes. This is the
  live reality, so the primary run evaluates the **provisional** read; a
  secondary run recomputes signals using only **settled** sessions (drop the
  in-progress session) to measure how much the provisional last session matters.

## Instruments & timeframes (locked)

- **Primary (daily, 1d):** `^NSEI`, `^NSEBANK`, `RELIANCE.NS`, `TCS.NS`,
  `INFY.NS`, `HDFCBANK.NS`, `ICICIBANK.NS`, `SBIN.NS`.
- **Secondary (1h):** `BTC`, `ETH`.
- Warmup: no signal recorded until ≥ 12 completed sessions exist (daily ⇒ ~12
  ISO weeks; the engine's `maxSessions` default).

## Labels (locked)

- **Primary — triple-barrier first-touch.** From the signal bar i, with the
  engine's own `target` (profit barrier) and `invalidation` (stop barrier) and a
  vertical barrier at H = 20 bars: WIN if target touched first, LOSS if
  invalidation touched first, TIMEOUT classified by the sign of the H-bar return
  in the signal's direction. NEUTRAL signals are not traded (measured as base
  rate). Breakout signals with open target use a synthetic target =
  entry ± (entry − invalidation) (1R) so every trade has both barriers.
- **Secondary — fixed-horizon signed return.** ret(h) = dir × (close[i+h] −
  close[i]) / close[i], for h ∈ {5, 10, 20}.

## Metrics

- **Win rate** and **mean signed return** for BUY, SELL, and BUY∪SELL, vs the
  all-bars base rate → **lift** = conditional / base.
- Signals/year, average bars-to-barrier, and a cost haircut (per-side slippage
  assumption, stated in the run) — a read that fires every bar is not tradeable.
- Per-`kind` and per-`confidence` breakdowns.

## Null (locked)

Circular-rotation permutation of the signal series against the price path (as in
`sbc_vedha_backtest.study`): preserves signal frequency and clustering, breaks
price alignment. 5000 rotations → empirical p = fraction of null lifts ≥
observed. Pooling across the correlated equity basket uses a **block** rotation
(rotate the whole panel together), not per-name shuffle, so cross-sectional
correlation cannot inflate significance. Per-instrument results reported
alongside the pooled read.

## Q2 method — attribution first, fitted weights gated

- **Phase A — attribution (descriptive, safe):** for each factor family, when it
  fires, the conditional win-rate and mean signed return vs base rate → an
  empirical per-factor lift table. Reported for both directions. Low overfit
  risk; often the whole answer.
- **Phase B — fitted weights (prescriptive, gated):** ONLY if Phase A shows real
  per-factor signal. Logistic regression of WIN/LOSS on the 7 signed factor
  features (the CSV emits one netted signed column per family), fit under
  **purged, embargoed walk-forward CV** with a final untouched out-of-sample
  hold-out. Factors are correlated (VA/sweep/cluster co-fire), so naive fitting
  overfits. **Adopt fitted weights over priors only if they beat the equal-prior
  baseline on the OOS hold-out.**

## Decision rule (pre-registered)

> Promote the composite signal to "measured edge" only if, out-of-sample:
> triple-barrier win-rate lift ≥ **1.3×** base **and** p < **0.01** **and** it
> holds across ≥2 instruments and ≥2 label definitions. Promote fitted weights
> over the hand-set priors only if they beat equal-priors on the OOS hold-out.
> A lift ~1.0× with p > 0.1 is a **clean negative** — keep the priors, mark the
> engine "descriptive, unvalidated", and stop. Educational, not investment
> advice.

## Data provenance / limits

- Daily basket: yfinance `1d` from 2007-09-17 (~4,650 bars/name, 19y). Full
  depth on all 8.
- Secondary 1h: yfinance caps intraday history at ~730 days, so BTC/ETH `1h`
  are only ~2y (~17,400 bars). Treat crypto as a **short, out-of-regime**
  cross-check, not a co-equal sample. (BTC/ETH via the `-USD` yfinance proxy.)
- Signals staged 2026-08-23 into `tools/cache/backtest/*_signals.csv` — these
  hold the signal + per-factor features ONLY; no forward returns / outcomes have
  been computed yet, so the pre-registration above is still intact.

## Status

- [x] Phase 0 — this design page (pre-registration locked 2026-08-23)
- [x] Phase 1 — `svp_backtest_export.py` + `svp_backtest_runner.js`; signals CSV
      staged for all 10 instruments (8 daily + 2 crypto-1h), zero engine errors
- [ ] Phase 2 — `svp_backtest.py` (Q1 edge + Phase A attribution) — **awaiting
      sign-off on the locked design before any forward returns are computed**
- [ ] Phase 3 — Phase B fitted weights (gated on Phase A)
