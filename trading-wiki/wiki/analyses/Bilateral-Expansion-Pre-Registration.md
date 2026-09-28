---
title: "Bilateral Expansion — Test Design (pre-registered) — NULL, and the framing SURVIVES"
category: analysis
tags: [symmetrical-triangle, bilateral, pre-registration, volatility-expansion, backtest, b-101, b-102, b-103, measured-null, framing-survives]
timeframe: swing
created: 2026-09-20
updated: 2026-09-20
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/Flag-Pole-Pre-Registration.md
  - analyses/Order-Block-Rules-Pre-Registration.md
  - concepts/Chart-Patterns.md
---

# Bilateral Expansion — Test Design (pre-registered)

**Written before any forward return has been looked at.** B-101 shipped
`Symmetrical Triangle (bilateral)` on 2026-09-20 deliberately unmeasured, because
the harness was long-only and could not score a pattern with no side. B-102 fixed
that (`backtest._simulate_plan(side=…)` and `backtest.absolute_move`). This is the
measurement both were built for.

## The claim under test is EXPANSION, not direction

Every other scanner here is graded on a directional edge. **That grading is
meaningless for this one**, and saying so before the run is the point of writing
this down: a coil that resolves both ways *should* produce a directional edge near
zero, and reading that number as "NO EDGE" would retire a detector that is working
exactly as described.

What a symmetrical triangle actually claims is that **price is about to leave a
range it has been compressing inside**. That claim is directionless and has a
unit: the absolute forward move, net of a round trip (`backtest.absolute_move`).

## The prior is skeptical, and it is on the record

* **B-19 measured 0 of 41 scanners stable after costs.** A 50th pattern is not
  expected to break that.
* The one prior on file is weak and is not being inherited:
  [[concepts/Chart-Patterns]] records triangles as the most common pattern in
  Indian equities (**2,179** instances vs 221 H&S) and StockEdge 2026's **5 of 7
  symmetrical entries resolved upward** — seven trades, which the page itself
  already flags as a hypothesis rather than a finding.
* **Volatility clusters.** A coil is a low-volatility state, and low volatility
  is followed by low volatility more often than not. The honest prior is that a
  coil predicts *less* near-term movement, not more — i.e. that this test comes
  back NEGATIVE, not merely null. Saying that now is what stops a small positive
  from being read as a discovery.

## The event

The **detection bar**: the first bar on which `scan_symmetrical_triangle` returns
a hit for a symbol, having returned none on the previous evaluated bar. Not the
breakout — at the breakout the pattern has already resolved and the direction is
known, which is a different (and directional) question.

Deduplicated with the harness's `min_gap`, so one coil contributes one signal
rather than one per bar while it sits there.

**Entry at the NEXT bar's open**, the desk convention.

## Three separable claims

### A. Expansion — does a coil precede a bigger move than a random bar?

Mean `absolute_move` from entry, against an every-bar baseline over the same
symbols and window, `COST_INDIAN` on both arms. **Primary horizon h = 20
sessions**, reported at 5 / 10 / 20 / 60. Welch t-test, two-sided.

### B. Does the apex band matter?

The card tells the reader that the textbook resolution band is 50–75% of the way
to the apex. That is an inherited claim and it has never been checked here. Split
the signals at `apex_progress` and compare the bands. **If the band carries
nothing, the card should stop implying it does.**

### C. Is it actually bilateral?

The framing itself is falsifiable. Record the up/down split of the resolution
(which line is broken first, or the sign of the move at h=20 when neither is).
**Pre-committed threshold: if the up-share falls outside 40–60% with n ≥ 200, the
"no direction" framing is wrong** and the card has to say what it really sees.
This is the one result that would change the scanner's design rather than just
its verdict.

## What counts as a pass

**A is the primary.** It passes only if the absolute-move edge is positive at
h = 20 with p < 0.05 AND the sign holds at every one of 5 / 10 / 20 / 60.
Anything else is NULL or NEGATIVE, and B and C are read as description rather
than as findings if A does not pass.

**No subgroup rescues a failed primary.** If A fails, B's bands are reported for
the record and explicitly not treated as a result — that is the multiple-
comparisons hole this desk has fallen into before.

## Sample and power

150 nifty500 names, ~900 sessions, stride 5 — the same protocol as the PR-2 plan
census, where this detector fired **32 times over 147 names**. That is the
expected order of magnitude for the full-history walk, and it is small. **If the
final n is under 200, the result is INCONCLUSIVE, not a null** — the same rule
B-19 applies at n < 20 per scanner, and the reason "TOO FEW SIGNALS" is its own
verdict there.

## What will be published either way

The result goes into [[analyses/Open-Backlog]] under B-101 and into
`named_studies.STUDIES` regardless of which way it lands, with the n and the
p-values, so CHECK 0c cannot see a study that ran and left no trace.

## Run 1 — 2026-09-20: INCONCLUSIVE (28 signals against a floor of 200)

**Superseded by run 2 below, and kept because it is the reason run 2 exists.**
Every number here is what an underpowered sample looks like, including one
that looked like a finding and was not.

Run: `tools/bilateral_expansion_study.py --run --symbols 150`, 146 usable names,
~900 sessions, stride 5, `COST_INDIAN` on both arms.

### A — expansion (primary)

| h | n | coil \|move\| | baseline | edge | p |
|---|---|---|---|---|---|
| 5 | 28 | 4.83% | 3.81% | **+1.02** | 0.191 |
| 10 | 28 | 6.85% | 5.22% | **+1.63** | 0.096 |
| 20 | 28 | 9.00% | 7.28% | **+1.72** | 0.196 |
| 60 | 28 | 17.80% | 13.33% | **+4.47** | 0.074 |

**All four horizons lean the same way and not one of them is significant.**
Under the bar set above this is INCONCLUSIVE — *not* a null, and not a pass
either. The registered prior (volatility clusters, so a coil should precede a
SMALLER move) is not supported by the direction of these numbers, but 28 signals
cannot rule it out and nothing here is claimed against it.

### B — the apex band

Reported for the record only, because A did not pass. With 5 in-band against 23
out, nothing is separable (p 0.11–0.33), and the in-band arm is *smaller* at
5/10/20d and larger at 60d — which is what noise looks like at n=5. **The card's
50–75% band remains an inherited claim, still unchecked.**

### C — is it actually bilateral?

**up 7 · down 17 · 4 undecidable — a 29.2% up-share.** That is outside the
40–60% band this page pre-committed as a falsifier of the "no direction"
framing. **The falsifier does not fire**, because it was registered at n ≥ 200
and this run has 24 resolutions. It is recorded here so the next run has
something to confirm or kill, and it is the single most interesting number in
this table.

The 4 undecidable cases are their own small finding: they are coils detected at
~99% apex progress, where the two boundaries have converged to within a few
rupees and one daily bar spans both. At the tip, "which line broke first" is not
answerable from daily bars at all.

### What it would take to settle this

28 coils came from 146 names × ~900 sessions — about **0.19 coils per name per
900 sessions**. Reaching n = 200 therefore needs roughly **1,000 name-900-session
blocks**: the full nifty500 over about four years, or a wider universe over the
same window. That is a runnable extension of this exact protocol, and the
analysis plan above does not change when it runs — only the sample does.

## Run 2 — 2026-09-20 (B-103): POWERED, and the answer is NULL

Run: `--symbols 500 --days 2500`. **482 usable names, ~10 years, 270 coils** —
above the floor of 200, so this run gets a verdict. Same protocol, same analysis
plan, same file; only the sample changed.

### A — expansion (primary): NULL

| h | n | coil \|move\| | baseline | edge | p |
|---|---|---|---|---|---|
| 5 | 270 | 4.44% | 4.12% | +0.32 | 0.265 |
| 10 | 270 | 5.83% | 5.84% | **−0.01** | 0.980 |
| 20 | 270 | 8.66% | 8.43% | +0.23 | 0.652 |
| 60 | 270 | 15.19% | 15.93% | **−0.74** | 0.396 |

**A coil precedes an ordinary move.** Not a bigger one, not a smaller one. The
edge at h = 10 is one hundredth of a percentage point on 270 signals, and the
sign is not even stable across horizons. This is a NULL that is adequately
powered, which is a result rather than an absence of one — and it is a different
statement from the registered prior, which expected coils to precede *smaller*
moves. That prior is not supported either.

**Run 1's lean was noise, and this is what the floor was for.** All four of its
horizons leaned positive (+1.02 to +4.47pp) and three would have been tempting to
write up. At n = 270 they collapse to ±0.3pp. Nothing was retracted, because the
pre-registered floor stopped it being claimed in the first place.

### B — the apex band: carries nothing

| h | in-band (n=73) | outside (n=197) | p |
|---|---|---|---|
| 5 | 4.06% | 4.58% | 0.367 |
| 10 | 5.45% | 5.96% | 0.494 |
| 20 | 8.00% | 8.90% | 0.371 |
| 60 | 14.81% | 15.33% | 0.790 |

With a failed primary this is description, not a finding — but it is well-powered
description and it points one way at every horizon: coils inside the textbook
50–75% band expand **slightly less**, never more. **The card's inherited
"textbook resolution band" line has no measured expansion edge behind it**, and
the card now says so rather than implying one.

Note precisely what this does and does not test. It tests whether in-band coils
*move more*. It does **not** test whether they *resolve more often* — that is a
different measurement, and nothing here licenses a claim about it either way.

### C — is it actually bilateral? YES, the framing survives

**up 105 · down 141 · 24 undecidable — a 42.7% up-share**, inside the 40–60%
band pre-committed as the falsifier. **The falsifier does not fire, at a sample
that could have fired it.** The "no direction" framing is kept on evidence rather
than on taste, and `Symmetrical Triangle (bilateral)` stays a non-voting neutral
card.

**Run 1's 29.2% was noise.** It is the single most valuable thing in this pair of
runs: the number that looked most like a discovery at n = 24 is the one the
powered sample killed. Had it been acted on, the card would have been rewritten
as a bearish pattern on 24 resolutions.

### What this means for the scanner

It stays registered, running, visible, and **non-voting** — and now with a
measured reason rather than a structural one. A detector that fires 270 times in
a decade and predicts an ordinary-sized move is not a trade; it is context, which
is what a non-voting card is for. The remaining honest use is what the card
already does: name both levels and refuse to pick a side.
