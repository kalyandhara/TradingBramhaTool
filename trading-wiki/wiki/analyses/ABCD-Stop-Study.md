---
title: "AB=CD Stop Study (B-132) — is the edge lost to a stop that is too tight?"
category: analysis
tags: [b-132, harmonic, abcd, stop-placement, plan, edge-study, pre-registered]
timeframe: swing
created: 2026-10-14
updated: 2026-10-14
sources: 0
related:
  - analyses/Open-Backlog.md
  - concepts/Chart-Patterns.md
---

# AB=CD Stop Study (B-132)

## Pre-registration — written 2026-10-14, BEFORE any run

**Why.** The B-129 re-measure (`tools/harmonic_bull_remeasure.py`, 2026-10-05) found
bullish AB=CD signals positive @20d in 3 of 3 windows (clustered p = 0.0066), yet the
card's plan returned −0.17R with 68% of plans stopped out. The card's stop is D − 0.5% of
D — on a typical NSE name, a fraction of one day's range. The question: **is the signal's
edge being given away by the stop?** Owner chose to pursue it (2026-10-14).

**What is held fixed.** The signal set is the AB=CD-only arm of B-129r, unchanged: the
registered `Harmonic Reversal (XABCD)` scanner (bullish only, R:R-to-T2 ≥ 1.5 gate on the
card's own stop), filtered to `AB=CD` hits. Entry = the card's entry (D); target = T2
(0.618 of CD); time stop = 10 bars; harness = `backtest.backtest_scanner` with
`COST_INDIAN`, `signal_mode="fresh"`, `fill_model="market"` (next open) — B-129r's settings.
**Only the stop changes.** A bullish AB=CD has no point below D (there is no X), so a
structural stop "beyond the BC leg" does not exist for it; the alternative is a stop sized
to the stock's volatility.

**Arms.** ATR14 = Wilder ATR on the signal bar (`scanner_templates._atr_series`).
- **A0 (control)** — the card's stop, D − 0.5%·D.
- **A1** — D − 1.0 × ATR14.
- **A2** — D − 2.0 × ATR14.

**Fresh panel.** `nse_universe.symbols("nifty500")` names **301–500** (B-129r used the
first 300), 1,500 days, daily, fetched the same way as B-129r.

**Measure.** Because a wider stop makes R bigger, R is not comparable across arms; the
primary measure is the plan's return in **percent of entry**, net of costs:
R × (entry − stop) / entry for each simulated trade.

**Primary tests (decide).** For each of A1 and A2: per symbol, mean plan % on that arm
minus mean plan % on A0 (symbols with trades on both); one-sample t-test across symbols,
two-sided. α = 0.05 / 2 = **0.025** per arm.

**Decision rule.**
- An arm **SHIPS** as the AB=CD card's stop if (i) it beats A0 with p < 0.025, AND (ii) its
  own plan % is positive: pooled mean > 0 and the per-symbol mean > 0 with one-sample
  p < 0.05, AND (iii) ≥ 30 symbols and ≥ 150 trades on that arm. If both arms ship, the one
  with the larger mean difference.
- Otherwise **NO CHANGE** — the card keeps D − 0.5%.
- Tier: this study does **not** change the Harmonic scanner's tier. If an arm ships, the
  B-129r promotion check is re-run on the full scanner with the new stop before any tier
  talk — and that is the owner's call.

**Reported beside the decision (descriptive).** Per arm: n trades, target / stop / time-exit
rates, avg R, mean plan %. The AB=CD **signal** edge @10/20/60d on the fresh panel — B-132's
premise, re-read out of sample. Plans unfilled / filled through the stop.

**Prior (written down so a positive has to beat it).** A1 or A2 beats A0 on plan % — a
wider stop should convert many of the 68% stop-outs — but whether the plan turns positive
is open: the 10-bar time stop and a T2 target were set for the tight stop.

## Results

*(appended after the run — nothing above this line is edited once the run starts)*

**Run 2026-10-14** — `tools/abcd_stop_study.py`, result `tools/cache/abcd_stop_study.json`.
200 names requested, 183 with AB=CD trades; 1,405 fresh signals. **Decision: SHIP A2.**

| Arm | Stop | Trades | Plan % / trade | Per-symbol p (own) | vs A0 | Target / stop / time exits | avg R |
|---|---|---|---|---|---|---|---|
| A0 | card, D − 0.5% | 1,315 | **+0.01%** | 0.81 | — | 25% / 67% / 8% | −0.16R |
| A1 | D − 1 × ATR14 | 1,374 | **+0.40%** | 0.039 | +0.37pp, p 0.010 | 34% / 40% / 26% | +0.04R |
| A2 | D − 2 × ATR14 | 1,385 | **+0.56%** | 0.012 | **+0.52pp, p 0.0019** | 36% / 21% / 43% | +0.04R |

Both wider stops pass every pre-registered condition; A2 has the larger gain and ships.
The control reproduces the B-129r picture out of sample (−0.16R vs −0.17R, 67% vs 68%
stopped), and the **signal** edge holds on the fresh names too: +0.84 / +0.89 / +1.12% at
10 / 20 / 60d — B-132's premise confirmed on data it was not found on.

**Read with care.**
- The win is in the plan, not a new signal: same 1,405 signals, only the stop moved.
- With the stop wider, 43% of A2 trades now leave on the **10-bar time stop** — the
  pattern's resolution window, set for the tight stop. The time stop was held fixed here
  by design; whether it is now too short is a separate question, not answered here.
- avg R reads +0.04 for both wide arms because R itself grew; the percent figure is the
  comparable one.

**What changed.** `scanner_templates.scan_harmonic_reversal`: for AB=CD only, the card's
stop is now D − `ABCD_STOP_ATR` (2.0) × ATR14; the R:R gate still uses the original stop,
so the signal set is the measured one. XABCD stops unchanged. The Harmonic scanner's
tier is **not** changed — re-running B-129r's promotion check with the new stop is the
next step if wanted, and the tier is the owner's call.
