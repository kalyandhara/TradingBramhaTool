---
title: "Gamma Exposure (GEX)"
category: concept
family: regime-filter
tags: [gex, gamma, options, dealer-positioning, volatility-regime, market-maker, call-wall, put-wall, gamma-flip, measured-null, retired]
created: 2026-08-29
updated: 2026-09-05
sources: 2
related: [concepts/Put-Call-Ratio, concepts/Volume-Profile, concepts/SuperTrend, concepts/Market-Sentiment-Index, sources/YT-Chris-Kmer-World-Cup-Order-Flow, sources/YT-GEX-Dealer-Hedging-Volatility-Primer, analyses/GEX-Strategy-Mapping-PoC-Probe, analyses/Open-Backlog]
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

## B-44r — the convention was the suspect. It is now eliminated. *(2026-09-05)*

**Shipped:** `tools/gamma_magnitude_backtest.py`. **No re-download was needed** — the
backlog assumed a fresh 480-session pass over the raw chains, but the quantity the
alternative convention needs is `gross_gex_cr`, the sum of absolute gamma notional, which
`compute_gex` has persisted all along.

The pre-registered hypothesis: if Indian dealers are short gamma on **both** sides, the
sign is constant and only the **magnitude** can predict, with bigger book → more hedging
flow with the move → **higher** forward vol.

### The direction came back inverted, on both indices, at every horizon

| test | NIFTY | p_rot | BANKNIFTY | p_rot |
|---|---|---|---|---|
| **PRIMARY** fwd 5d vol, high vs low gross | **−2.47 pp** | 0.042 | **−4.27 pp** | 0.004 |
| fwd 10d vol | −2.17 | 0.098 | −3.78 | 0.015 |
| fwd 20d vol | −1.77 | 0.158 | −3.03 | 0.058 |
| next-day absolute move | −0.15 % | 0.048 | −0.18 % | 0.073 |
| tercile split, 5d vol | −3.39 | 0.027 | −5.80 | 0.002 |
| *expected null:* fwd 5d return | −0.04 % | 0.773 ✓ | +0.30 % | 0.571 ✓ |

High gross gamma goes with **lower** forward vol — the opposite of what was predicted. The
expected-null control behaved, so the harness is sound.

### Most of that is mechanical, and the rest is not stable

Black-Scholes gamma carries **1/σ**: high implied vol mechanically produces low gamma per
contract, and realised vol clusters. That alone manufactures the observed sign.

- corr(gross, trailing 20d vol) = **−0.44** NIFTY / **−0.24** BANKNIFTY
- corr(trailing vol, fwd 5d vol) = **+0.43** / **+0.49**
- corr(gross, fwd 5d vol) = −0.29 / −0.17 — close to the product of the two paths

Controlling for trailing vol roughly halves NIFTY's effect (−1.24 to −1.64 pp,
p_rot 0.029–0.067) and it survives on BANKNIFTY (−3.2 to −3.7 pp, p_rot 0.021–0.033),
including against **1/trailing-vol**, the artefact's own functional form.

But the stratified test is the one that decides it:

| trailing-vol stratum | NIFTY | p_rot | BANKNIFTY | p_rot |
|---|---|---|---|---|
| low | −1.01 pp | 0.429 | **+1.23 pp** (sign flips) | 0.442 |
| high | −3.00 pp | 0.054 | −9.25 pp | 0.010 |

The relationship exists **only when volatility is already high**, and on BANKNIFTY it
reverses in the calm half. A predictor that works in one vol regime and inverts in the
other is not a regime signal; it is a description of the vol regime it is conditioned on.

### Verdict — B-44r closed, and the pre-agreed clause applies

The hypothesis as specified is **falsified**, not merely null: the sign is wrong. What is
left is a conditionally unstable residual, largely mechanical, that would flip a trader's
prescription depending on which half of the vol distribution the day happens to sit in.
The backlog said, in advance: *"if it also nulls, GEX gets retired as a research instrument
that prints a daily description and nothing more."* That clause is now triggered.

One thing this DOES settle: the convention is no longer a live excuse. Under both the US
sign convention (B-44) and the both-sides-short magnitude convention (B-44r), NSE index
gamma carries no dependable forward volatility information. The remaining gap is
positioning data this repo does not have — per-strike dealer inventory, not another
assumption about it.

## Second source — corroboration, plus one new claim (2026-09-05)

[[sources/YT-GEX-Dealer-Hedging-Volatility-Primer]] restates the mechanism above
independently and adds nothing to it: same dealer behaviour, same flip/wall landmarks, same
"pair it with price action" caveats. Its one new claim is **strategy selection by regime** —
premium selling (condors, credit spreads, CSPs) in positive gamma, long options in negative
gamma.

That claim is downstream of the vol difference **this page already measured to a null**, so
it inherits the null: a strategy split that exists to harvest a vol spread has nothing to
harvest if the spread is not there. The source names no market, and the evidence base for
dealer hedging is US index options.

Two things it is missing that the first source has: the "positive ≠ bullish" correction
(its "shock absorber" framing arguably invites the error), and the naive-vs-inferred
distinction — which is the named suspect in **B-44r**.

Feasibility of testing it anyway, with costs: [[analyses/GEX-Strategy-Mapping-PoC-Probe]].
Short version — the cheap decisive test is **RV−IV by regime**, not a strategy simulation;
it is blocked on `atm_iv` not being persisted (a small code change) and a 480-session
rebuild with **no F&O bhavcopy cache** (~480 NSE downloads).

## Sources

- [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]] (2026-08-29) — regime framing, naive vs
  inferred, call/put wall and gamma flip, and the "positive ≠ bullish" correction.
- [[sources/YT-GEX-Dealer-Hedging-Volatility-Primer]] (2026-09-05) — unattributed primer;
  corroborates the mechanism, adds the strategy-by-regime prescription.
