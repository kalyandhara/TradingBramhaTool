---
title: "SVP Structure Signal — Test Design (pre-registered) — MEASURED INVERTED"
category: analysis
tags: [svp, volume-profile, pre-registration, structure-signal, backtest, b-56, measured-inverted]
timeframe: milestone-plan
created: 2026-09-17
updated: 2026-09-17
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/SVP-Signal-Backtest-Design.md
  - analyses/PCR-Sign-Convention-Pre-Registration.md
---

# SVP Structure Signal — Test Design (pre-registered)

**Written before any forward return has been looked at.** B-56 built
`svp_structure_signal.js` on 2026-09-06 and it has never been scored. It is the
last built-but-unmeasured signal on the desk, it is gated as a bystander by
B-55's rule, and this fixes the test, the floor, the controls and the decision
rule — including what happens on a null — while the answer is still unknown.

## The prior is skeptical, and it is on the record

This is not a neutral hypothesis. The 2026-08-29 attribution of the SVP
*composite* scored the two factor families this signal is built from at
**`sequence` −0.67** and **`va` −0.71**, and the composite as a whole was a clean
negative (corr −0.041, non-monotonic deciles, 5 of 7 families sign-inverted).

**The structure signal uses shape-series and value-area logic — exactly those
inputs.** It is a genuinely different construction (named boolean rules, no
weights, no score, and it does not read the composite), which is why it was worth
building. It is not thereby absolved. **The honest prior is that this fails**, and
stating that now is what stops a marginal result from being read as a success.

## What is being tested

`SVPSTRUCT.read` returns one of three standing reads per bar:

* **BUY** — POC migration rising **AND** price at/above composite POC **AND** the
  nearest structure below is an HVN not an LVN **AND** last session shape P or D
* **SELL** — the mirror, with the nearest structure above being an HVN
* **HOLD** — everything else, explicitly including balance-dominant sequences

**H0:** the read carries no directional information about forward returns.
**H1:** BUY days are followed by higher returns than SELL days.

Two-sided. The desk does not get to claim a direction after seeing the data.

## It is a STATE, not an event — and that decides the statistic

The card is read as a standing condition ("today it says BUY"), so state days are
the primary unit. A state series is **heavily autocorrelated**: the same read
persists for runs of bars, so the effective sample is far smaller than the row
count and Welch would badly overstate significance.

Measured precedent, and the reason this is not a judgement call:
`gamma_regime_backtest` ran a **pre-registered null that printed p=0.031 under
Welch and p=0.32 under rotation**. The same statistic is reused here rather than
reimplemented — `gamma_regime_backtest._rotation_p`, imported.

## Data

The locked Phase-1 daily basket, unchanged from the composite's test so the two
findings are directly comparable:

    ^NSEI, ^NSEBANK, RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ICICIBANK.NS, SBIN.NS

Bars come from the JSON the existing exporter already wrote. The runner calls
`SVP.analyze(bars[0..i])` and `SVPSTRUCT.read(...)` at each bar *i*, so a row at
*i* uses nothing after *i*. Every forward window starts at the **next bar's open**.

## Primary statistic, horizon and floor

* **Primary:** `spread = mean(fwd | BUY) − mean(fwd | SELL)` at **h = 20 sessions**.
* **Reported at** h = 5, 10, 20, 60 — one primary, the rest descriptive.
* **Significance:** circular-rotation p on the pooled state series, two-sided.
* **Floor: 200 BUY days and 200 SELL days.** Below either, the result is reported
  **INCONCLUSIVE — UNDERPOWERED**, not as a null. This is the B-58 precedent: 53
  QM events against a floor of 200 was not evidence of absence, and calling it one
  would have been the error.

## Controls — tests of the harness, not of the signal

1. **HOLD ≈ baseline.** HOLD is the residual class and should sit near the
   every-bar mean. If HOLD departs from baseline while BUY and SELL do not, the
   rules are selecting unusual bars without selecting a direction — that is a
   finding about the filter, not about the read.
2. **Baseline is computed on the same bars**, not on the full series, so the
   comparison cannot be contaminated by the warmup window or by which symbols
   happened to produce rows.

## Decision rule — written now, so the desk does not get to choose later

| Outcome at h=20 | Verdict | Consequence |
|---|---|---|
| spread **> 0** and p_rot **< 0.05** | **PASS** | promoted from bystander to a **reported** read. Still **no weight, no vote, no confluence entry** — passing one test buys visibility, not authority |
| spread ≤ 0, or p_rot ≥ 0.05, with both floors met | **NULL** | stays a bystander permanently. **The card must say it was measured and failed** — the null goes on the surface, not in the drawer |
| either floor unmet | **INCONCLUSIVE** | stays a bystander. Recorded as underpowered, **not** as a null |
| spread **< 0** and p_rot **< 0.05** | **INVERTED** | do **not** flip the rules and ship the mirror. A significant inversion on a skeptical prior is a reason to re-read the construction, and any flipped version is a new hypothesis needing its own pre-registration |

**Nothing is deleted on a null.** The engine stays, the chart keeps drawing the
levels, and the HVN/LVN role naming stays — that correction is right independently
of whether the BUY/SELL read carries edge.

## What this test cannot say

It scores the **read**, not the **levels**. `support_hvn` / `fast_zone_below` and
the stops-behind-HVN / targets-beyond-LVN reasoning are a separate claim with a
separate test, and a null here does not touch them.

It is eight liquid daily names. It cannot speak to intraday, to small caps, or to
any regime the 2023–2026 window does not contain.

## RESULT — measured 2026-09-17: **INVERTED**

`svp_structure_runner.js` + `svp_structure_backtest.py`, 8 symbols, ~4,600 bars
each, 36,829 scored rows.

| h | n BUY | n SELL | BUY % | SELL % | HOLD % | base % | spread | p_rot |
|---|---|---|---|---|---|---|---|---|
| 5 | 4,595 | 2,891 | 0.26 | 0.83 | 0.17 | 0.23 | **−0.57** | 0.046 |
| 10 | 4,592 | 2,886 | 0.64 | 1.45 | 0.40 | 0.52 | **−0.81** | 0.079 |
| **20** | **4,576** | **2,876** | **0.99** | **2.75** | **0.95** | **1.10** | **−1.77** | **0.041** |
| 60 | 4,542 | 2,834 | 3.32 | 4.95 | 3.38 | 3.50 | **−1.64** | 0.362 |

**Both floors cleared comfortably** — 4,576 BUY and 2,876 SELL days against 200
each — so this is a result, not an underpowered non-answer.

**The read is backwards from its own hypothesis.** SELL days were followed by
**+2.75%** at 20 sessions; BUY days by **+0.99%**. The spread is **−1.77%** at
p_rot 0.041, and the primary horizon was fixed in advance, so that is the number
that counts.

### The consistency is stronger evidence than the p-value

| symbol | n BUY | BUY | n SELL | SELL |
|---|---|---|---|---|
| ^NSEI | 582 | +1.05% | 170 | +1.10% |
| ^NSEBANK | 352 | +1.36% | 352 | +1.80% |
| RELIANCE.NS | 504 | +0.33% | 417 | +2.08% |
| TCS.NS | 661 | +1.36% | 333 | +1.52% |
| INFY.NS | 645 | +1.13% | 310 | +2.58% |
| HDFCBANK.NS | 675 | +0.98% | 447 | +2.04% |
| ICICIBANK.NS | 552 | +0.88% | 413 | +5.17% |
| SBIN.NS | 605 | +0.79% | 434 | +4.33% |

**SELL beat BUY in 8 of 8.** A single p-value near 0.04 across four horizons is
the kind of thing that dissolves on re-measurement; eight independent symbols
leaning the same way is not. The direction is the finding.

### The control passed, which matters

**HOLD came in at −0.146pp from baseline** — near it, as pre-registered. So the
rules are not merely selecting unusual bars: the residual class behaves like the
market, and the BUY/SELL classes are where the departure lives. That rules out
the "filter, not a read" explanation the control existed to catch.

### Consequence applied, exactly as pre-registered

**The mirror was NOT shipped.** The decision table fixed that before the run, and
the reasoning holds up on the numbers: **every arm is positive** — BUY +0.99%,
SELL +2.75%, HOLD +0.95%, baseline +1.10% — because the window is a rising
market. "SELL is followed by a bigger bounce" in a bull market is the signature of
**mean reversion**, not of a working short signal. What the rules appear to detect
is a pullback; the label on it is simply wrong.

Flipping BUY and SELL would therefore be fitting a label to a bull-market
artifact, and it is a new hypothesis owing its own pre-registration and its own
window — ideally one containing a real drawdown.

**Unchanged, as promised:** nothing deleted, the engine stays, the chart keeps
drawing the levels, and the HVN/LVN role naming stays — that correction is right
independently of this result. The signal **stays a bystander: no vote, no score,
no confluence weight.**

**On the surface, not in the drawer.** The SVP screen's caption now states the
inversion, the numbers and the reason the mirror was not shipped; the `struct`
column's tooltip carries the one-line version.

### What this closes and what it opens

**Closes:** B-56, and with it the last built-but-unmeasured signal on the desk.

**Opens** (neither is claimed, both are recorded):
* the **mean-reversion reading** — if the rules detect pullbacks, the honest test
  is a pullback test, in a window with a drawdown in it;
* the **levels** — `support_hvn` / `fast_zone_below` and the stops-behind-HVN
  reasoning were never in scope here and remain untested.

### Where this sits in the SVP ledger

Third measurement of volume-profile-derived direction on this desk, and the third
that does not support it: the **composite** (2026-08-29, clean negative), the
**per-factor attribution** (`sequence` −0.67, `va` −0.71), and now the
**structure read** (inverted). Three constructions, two of them deliberately
independent, one conclusion. The prior recorded at the top of this page was
right, and writing it down beforehand is what makes saying so afterwards worth
anything.

## Related Pages

- [[analyses/Open-Backlog]] — B-56's entry and the bystander gate
- [[analyses/SVP-Signal-Backtest-Design]] — the composite's design, reused here
- [[analyses/PCR-Sign-Convention-Pre-Registration]] — the same shape of test
