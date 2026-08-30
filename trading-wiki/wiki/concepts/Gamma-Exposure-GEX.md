---
title: "Gamma Exposure (GEX)"
category: concept
family: regime-filter
tags: [gex, gamma, options, dealer-positioning, volatility-regime, market-maker, call-wall, put-wall, gamma-flip, measured-null]
created: 2026-08-29
updated: 2026-08-29
sources: 1
related: [concepts/Put-Call-Ratio, concepts/Volume-Profile, concepts/SuperTrend, concepts/Market-Sentiment-Index, sources/YT-Chris-Kmer-World-Cup-Order-Flow, analyses/Open-Backlog]
---

# Gamma Exposure (GEX)

A **volatility-regime** read derived from options open interest. Not a direction signal —
the single most common misreading is treating "positive gamma / green" as bullish and
"negative gamma / red" as bearish. It says nothing about direction and everything about
whether moves are likely to be **damped** or **amplified**.

## The mechanism

Options dealers and market makers sell options to the market and do **not** want
directional exposure, so they delta-hedge in the underlying (futures or cash). Gamma is
the rate at which their delta changes as spot moves, so it determines *which way they must
trade to stay neutral*:

| dealer gamma | to stay hedged they | effect on price | what the tape feels like |
|---|---|---|---|
| **Positive** (dealers long gamma) | **sell** rallies, **buy** dips | mean-reverting, **vol dampened** | pinning, chop, **failed breakouts** |
| **Negative** (dealers short gamma) | **buy** rallies, **sell** dips | trend-accelerating, **vol amplified** | fast, gappy, squeezes run further |

Dealer hedging is therefore a **feedback loop whose sign flips with positioning**. This is
a genuine structural mechanism, not a sentiment proxy — which is what makes it worth
measuring rather than believing.

Key landmarks on a gamma profile:
- **Gamma flip** — the spot level where net dealer gamma crosses zero. The line in the
  sand between the two regimes above.
- **Call wall** — strike with the largest positive-gamma concentration; tends to act as a
  ceiling while dealers are long gamma there.
- **Put wall** — the equivalent below; tends to act as a floor.

## Naive vs inferred GEX

- **Naive GEX** — assumes a fixed convention for who is long/short each contract (the
  standard shortcut: dealers are short calls and long puts, or simply "customers buy
  options"). Computed from open interest and gamma per strike. Cheap, and available for
  any chain you can read.
- **Inferred GEX** — models actual dealer positioning per strike from trade-level data
  (which side initiated). More granular, and dependent on **CBOE-licensed** data that is
  typically S&P-only and priced around **$300/month** ([[sources/YT-Chris-Kmer-World-Cup-Order-Flow]]).

The practical consequence: if you only need the **regime** (damped vs amplified), naive
GEX is adequate. If you intend to trade *bounces off* a specific call/put wall, the
positioning assumption starts doing real work and naive GEX is not enough. The source
uses it for the former and explicitly declines the latter.

## How it is used (as documented)

Pre-open, alongside higher-timeframe structure: "value-up structure **and** negative
gamma" is a different day-plan from "value-up structure **and** positive gamma" — same
direction, different expectation for how far and how fast moves travel, and how much a
breakout should be trusted. Positive gamma is the regime where breakout strategies bleed,
because dealer hedging is mechanically leaning against every attempt.

## Status in this repo — BUILT, and the claim came back a NULL

**Shipped 2026-08-29** (B-44): `tools/gamma_exposure.py` (engine + CLI),
`tools/gamma_regime_backtest.py`, `tools/test_gamma_exposure.py` (14 tests).

The build was as cheap as predicted: `nse_oi_momentum._download_bhavcopy` already pulls
the whole F&O bhavcopy, and the discarded `IDO` rows carry strike, OI, settlement price,
expiry **and** `UndrlygPric` — so spot comes from the same file and there is no second
source to keep in sync. Per-strike IV is inverted from settlement prices by bisection;
rows that cannot yield an IV are dropped rather than defaulted, and the surviving
fraction is reported as `coverage` (87.5% NIFTY / 89.7% BANKNIFTY across the history).

### The measured result — no gamma-regime effect on NSE indices

480 sessions, 2024-09-19 .. 2026-08-28 (the full UDiFF-format bhavcopy history).
NIFTY: 342 positive-gamma days, 138 negative.

| test | prediction | NIFTY result | p_rot |
|---|---|---|---|
| Forward realised vol 5d | negative gamma higher | +0.28 pp | 0.84 |
| Forward realised vol 10d | negative gamma higher | +0.24 pp | 0.83 |
| Forward realised vol 20d | negative gamma higher | **−0.40 pp** (wrong sign) | 0.67 |
| Next-day absolute move | negative gamma higher | +0.03 pp | 0.69 |
| Directional return (expected null) | no effect | +0.04 … +0.70 pp | 0.22–0.69 ✓ |
| Net/gross **tercile** vol split | extremes separate | +0.06 … +0.63 pp | 0.58–0.95 |
| 20-day-high breakout follow-through | worse in positive gamma | −0.10 pp (49 events) | 0.84 |

BANKNIFTY is directionally friendlier — forward vol runs **+0.77 / +1.02 / +1.59 pp**
higher in negative gamma at 5/10/20d, the right sign at every horizon — but p_rot is
0.75 / 0.68 / 0.58. A consistent sign with no significance is a hint, not a result.

**The prior recorded on this page was wrong.** "Cautiously positive, the most favourable
in the backlog" did not survive contact with the data. The mechanism is real in US index
options; it is not measurable here, in this form, on this history.

### A methodology finding worth more than the result

The first pass used Welch, as every other backtest in this repo does. It reported the
**directional** test — the one pre-registered as an expected null — at **p=0.031**.
That was an artefact: with daily sampling and a 20-day forward window, consecutive
observations share 19/20 of their data, so Welch's independence assumption fails badly.

The harness now leads with an **exact circular-rotation p-value**: every shift of the
label series is enumerated and the statistic recomputed, which preserves the
autocorrelation of both the labels and the outcomes. The same test reads **p_rot = 0.32**.
Both columns are printed side by side so the size of the gap stays visible. Any repo
backtest that samples daily against multi-day forward windows has the same exposure —
`stride=5` (the existing convention) mitigates it; rotation measures it.

### What was deliberately NOT done

No dashboard, no wiring into the `REGIME_GATE`. The backlog item said "test before any
dashboard"; the test failed, so the tool stays a research instrument. It still prints a
useful daily reading (`py -3 tools/gamma_exposure.py`) — a *description* of dealer
positioning, carrying no demonstrated forward information.

Residual: **B-44r** in [[analyses/Open-Backlog]] — the naive convention as the named
suspect.

## Sources

- [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]] (2026-08-29) — regime framing, naive vs
  inferred, call/put wall and gamma flip, and the "positive ≠ bullish" correction.
