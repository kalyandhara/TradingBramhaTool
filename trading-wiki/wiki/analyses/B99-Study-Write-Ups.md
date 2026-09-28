---
title: "B-99 Study Write-Ups — four indexed backtests documented"
category: analysis
tags: [b-99, backtest, funnel, sbc, muhurat, newmoon, measured]
timeframe: milestone-plan
created: 2026-09-24
updated: 2026-09-24
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/MA-Bias-Edge-Test.md
  - concepts/Sarvatobhadra-Chakra.md
---

# B-99 Study Write-Ups

**Four backtests that ran and left no citable result.** Each had code, ran to
completion, and produced numbers — but those numbers never reached a wiki page,
so `claims_lint` flagged them as stale claims (CHECK 0c). This page closes that
gap by documenting each result with real output.

---

## 1. Funnel Price Sub-Funnel (B-38) — `funnel_backtest.py`

**What it tests:** the TechnoFunda Delete Funnel's three price legs (F6: above
200 DMA, F7: relative strength vs Nifty 50, F8: accumulation via volume) —
individually and stacked. Does the triple-filter survivor set outperform (a) a
random bar in the same tape and (b) each single filter alone?

**Honest limit:** the fundamental legs (F1–F5) are NOT testable point-in-time
because yfinance serves current statements, not historical snapshots.
Survivorship + restatement + as-of bias would invalidate the result.

**Status: MACHINERY ONLY — no live measurement.** The standalone `__main__` runs
on synthetic data (random walks with tunable drift) to verify the framework
functions correctly. A live run requires a fetcher + benchmark injected from the
dashboard, which has not been wired. The synthetic output confirms the code path
works but produces fabricated numbers that are explicitly not a finding.

**Synthetic output (machinery check):**

| Leg | n | 5d edge (p) | 10d edge (p) | 20d edge (p) | 60d edge (p) |
|-----|---|-------------|--------------|--------------|--------------|
| F6 200 DMA | 704 | −0.03 (0.78) | −0.12 (0.47) | −0.27 (0.24) | −0.62 (0.14) |
| F7 Rel. strength | 440 | −0.06 (0.66) | −0.16 (0.40) | −0.32 (0.23) | −1.31 (0.01)* |
| F8 Accumulation | 877 | −0.03 (0.79) | −0.05 (0.73) | −0.07 (0.76) | −0.09 (0.83) |
| F6∧F7∧F8 | 371 | −0.08 (0.54) | −0.16 (0.40) | −0.39 (0.17) | −1.76 (0.00)* |

Combo does NOT beat the best single leg at 20d (−0.39 vs −0.07, p=0.165).

**Next step:** wire the live fetcher in the dashboard to produce a real
measurement. Until then, the funnel's price legs are **UNMEASURED**, not null.

---

## 2. SBC Moon Reversal Windows — `sbc_backtest.py`

**What it tests:** do Sarvatobhadra Chakra reversal windows (Moon pada/nakshatra
boundary crossings) predict actual 15-minute swing reversals on BTC-USD?

**Method:** 60 days of 15m OHLC from yfinance, swing pivots at ±2 bars, windows
matched within ±15 minutes. Lift = recall / random-coverage baseline.

**Result (2026-09-24 run):**

- **5,720 bars, 60 days, 1,574 swing pivots (k=2)**
- Recall: 7.9% (125 of 1,574 pivots hit a window)
- Baseline coverage: 8.3% (expected 130 by chance)
- **Lift: 0.96× — BELOW chance**
- z = −0.45, one-tailed p = 1.000
- Precision: 49.6% of windows contain a pivot (uninformative — half by chance)

**Verdict: NULL.** SBC Moon reversal windows do not cluster real 15-minute swing
pivots any better than random windows of the same duration. The lift is slightly
below 1.0, meaning the windows are, if anything, marginally worse than chance.

**Note:** 60 days is the yfinance 15m data cap. The sample is small but the
signal is not even trending positive — more data would not rescue a lift < 1.0.

---

## 3. Abhijit Muhurat → Nifty Reversal — `sbc_muhurat_backtest.py`

**What it tests:** does the daily Abhijit Muhurat (the 8th of 15 muhurtas, a
~48-minute window centred on local solar noon) precede an intraday Nifty reversal
within the following 60 minutes?

**Method:** 60 days of Nifty 15m data, "extreme" mode (session high or low bar
falls in the forward window). Baseline: same-length window slid across each day's
session.

**Result (2026-09-24 run):**

- **59 trading days, 59 muhurat windows in-session**
- Observed hit rate: 18.6% (11 of 59)
- Baseline (random window): 28.1%
- **Lift: 0.66× — BELOW baseline**
- z = −1.61, one-tailed p = 1.000

**Verdict: NULL.** The Abhijit Muhurat does not precede Nifty daily extremes more
often than a random intraday window. The observed rate is substantially LOWER than
chance (0.66×), meaning the muhurat window is, if anything, an anti-signal for
extremes — though not significantly so (the sample is 59 days).

---

## 4. New-Moon Levels as S/R (B-30r) — `newmoon_levels_backtest.py`

**What it tests:** are new-moon-day high/low levels better support/resistance than
ordinary prior-trading-day high/low levels? The honest null is NOT "random price"
but "the prior day's extremes" — any recent high/low acts as some S/R, so the
test isolates whether the LUNAR label adds anything.

**Method:** ^NSEI daily from 2007 to 2026, 235 new moons. Matched pairs:
new-moon-day H/L vs prior-day H/L. Rejection = price touched the level and
closed back on the approach side N bars later. Null: 5,000 paired permutations
(swap treatment/control within each pair, preserving regime).

**Pre-registered pass bar:** lift ≥ 1.15 AND p < 0.01, robust across ε and
horizon.

**Result (2026-09-24 run):**

| ε | N bars | pairs | NM rej% | PD rej% | lift | diff | p |
|---|--------|-------|---------|---------|------|------|---|
| 0.15 | 3 | 448 | 49.3% | 50.6% | 0.98 | −1.2% | 0.666 |
| 0.15 | 5 | 448 | 50.4% | 51.3% | 0.98 | −0.8% | 0.645 |
| 0.15 | 10 | 446 | 50.7% | 48.1% | 1.05 | +2.5% | 0.135 |
| 0.25 | 3 | 452 | 49.6% | 52.2% | 0.95 | −2.6% | 0.836 |
| 0.25 | 5 | 452 | 50.9% | 50.6% | 1.01 | +0.3% | 0.465 |
| 0.25 | 10 | 450 | 51.6% | 50.0% | 1.03 | +1.6% | 0.259 |
| 0.50 | 3 | 456 | 53.9% | 55.5% | 0.97 | −1.6% | 0.731 |
| 0.50 | 5 | 456 | 56.1% | 53.9% | 1.04 | +2.2% | 0.164 |
| 0.50 | 10 | 454 | 54.6% | 54.3% | 1.01 | +0.3% | 0.426 |

**Verdict: NULL — no lunar S/R edge over prior-day extremes.** Lifts range from
0.95× to 1.05×, all with p > 0.1. New-moon-day highs and lows are perfectly
ordinary support and resistance levels — no better and no worse than the prior
trading day's. The lunar label adds nothing measurable over 235 events and 19
years of data.

---

## Summary

| Study | Item | Verdict | Key number |
|-------|------|---------|------------|
| Funnel price legs | B-38 | **UNMEASURED** (machinery only) | synthetic — needs live wiring |
| SBC Moon windows | SBC-15m | **NULL** | lift 0.96×, p=1.0 |
| Abhijit Muhurat | SBC-muhurat | **NULL** | lift 0.66×, p=1.0 |
| New-moon levels | B-30r | **NULL** | lift 0.95–1.05×, all p>0.1 |

Three clean nulls and one unmeasured. The SBC and lunar results are consistent
with the desk's prior findings on astro-derived signals: [[analyses/SBC-Reading-BSE]]
(SBC vedha on NIFTY: clean negative, no edge). The funnel remains an open item
pending live data wiring.
