---
title: "SBC card reading — POSITIVE, and it still beats doing nothing (barely)"
category: analysis
tags: [structure-break-chain, choch, bos, market-structure, backtest, bse, b-114, b-115, measured-positive, clustered, baseline]
timeframe: swing
created: 2026-09-21
updated: 2026-09-21
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/SVP-Structure-Signal-Pre-Registration.md
  - concepts/Market-Structure-CHOCH-BOS.md
---

# SBC card reading — BSE, then the universe

The Structure Break Chain card started printing a plain-English verdict on
2026-09-21 ("Trend change NOT confirmed — the CHoCH failed", "Trend
continuing", …) and shipped with a footer admitting nothing backed the words.
This tests them, on the one name that was asked for.

## What was pre-registered, before the run

**The claim under test is the card's own core distinction**: a break that HELD
should mean something different from one that FAILED.

* **Primary** — direction-signed forward return at h = 20, HELD vs FAILED, costs
  on both. Passes only with p < 0.05 **and** the sign holding at 5 / 10 / 60.
* **Floor** — ≥ 30 events per bucket, or the answer is INCONCLUSIVE. Never NULL.
* **Secondary** — verdict tone and quality label, description only if the
  primary fails.

**One symbol cannot reach that floor**, and that was said before the numbers
rather than after them. BSE has 2,383 sessions (2017-02 → 2026-09) and **41
structural events in its entire history**.

## The first run was measuring an artifact — and said so loudly

It returned **41 held, 0 failed**, against the 11 failures the card shows on the
same history. The reason:

> `failed` is decided by what price does in the bars **after** the break, so at
> the break bar it is **always False**.

Verified directly: the first failed event on BSE (bar 174) reads `failed=False`
at its own bar and `failed=True` one bar later. Scoring events at their own bar
left the "held vs failed" comparison with nothing to compare — a 0-event bucket
that a less loud artifact would have hidden as a small one.

**The fix is also the honest trading assumption**: a verdict that depends on
three bars of hindsight cannot be acted on before those bars, so the card is read
at `t + fail_win` and entry is the next open after that.

## Result — INCONCLUSIVE

41 events · **32 held · 9 failed**, direction-signed, net of Indian delivery
costs:

| h | n held | n failed | held | failed | **diff** | p |
|---|---|---|---|---|---|---|
| 5 | 32 | 9 | +1.33% | −5.82% | **+7.14** | 0.064 |
| 10 | 32 | 9 | +4.01% | −8.64% | **+12.65** | 0.009 |
| 20 | 32 | 9 | +4.03% | −12.02% | **+16.05** | 0.039 |
| 60 | 32 | 9 | +4.74% | −11.09% | **+15.84** | 0.064 |

**The lean is large, it points the way the card's wording implies, two horizons
are nominally significant — and it is still INCONCLUSIVE**, because the failed
bucket holds **9 events against a floor of 30**. That is not pedantry: B-101's
28-signal run leaned positive on all four horizons and the powered re-run
(270 signals) killed every one of them, including the 29.2% up-share that looked
most like a discovery.

### Secondaries — reported, and they do NOT rank

Description only, since the primary did not pass:

| verdict tone | n | mean @20d | | quality | n | mean @20d |
|---|---|---|---|---|---|---|
| good | 24 | +3.01% | | STRONG | 21 | +1.06% |
| warn | 8 | **+7.06%** | | NORMAL | 17 | −1.43% |
| bad | 9 | −12.02% | | WEAK | 3 | **+7.52%** |

**Neither ladder is monotonic.** `warn` beats `good`; `WEAK` beats both `STRONG`
and `NORMAL` on three events. If anything survives a powered run it is likely to
be the **failed/held split alone** — the binary the card gets from price coming
back through the level — and not the graded quality score, which is where the
formula's `0.6·dist/ATR + 0.4·body/ATR` sophistication lives.

## What this does and does not license

**Does**: keep the card's wording as a *description*, and keep its footer. On
BSE, breaks that held were followed by a move in their own direction and breaks
that failed by a move against it, which is at least consistent with what the card
says.

**Does not**: any claim that this is an edge, on BSE or anywhere. One symbol, 9
events in the deciding bucket, and a desk whose other structure read (SVP) came
back **inverted** when it was finally measured.

**To settle it**: the same protocol across a universe until the failed bucket
clears 30 — roughly 5–8 names' worth of history at BSE's rate of 9 failures per
2,400 sessions, so a 150-name run would be comfortable. The study takes
`--universe`; what it needs first is a faster walk, because it currently
re-detects the chain twice per bar.

## Run 2 — 150 nifty500 names: POSITIVE, and it survives clustering

The same protocol, same pre-registered bar, 150 names × ~10 years. `walk_fast`
made it runnable: one `detect_structure_chain` pass per symbol instead of two per
bar, **validated against the slow walk on BSE first — 41 events, every field
identical**, because a fast path that is not diffed against the slow one is a
rewrite with a result attached.

**4,608 events · 2,525 held · 2,083 failed** — both buckets far past the floor.

| h | held | failed | **diff** | p (pooled) |
|---|---|---|---|---|
| 5 | +0.15% | −0.20% | +0.35 | 0.065 |
| 10 | +0.53% | −0.34% | **+0.86** | 0.001 |
| 20 | +1.04% | −0.24% | **+1.28** | 0.000 |
| 60 | +1.91% | +0.95% | +0.96 | 0.146 |

**Verdict: POSITIVE** — positive at h = 20 with p < 0.05 and the sign holding at
5 / 10 / 60, which is exactly what was written down before the run.

### The clustering control, because the pooled p is not believable on its own

4,608 events over 150 names are not 4,608 independent observations: events inside
one symbol share its trend, and events across symbols share the same market days.
So the same test with **the SYMBOL as the unit** — one (held − failed) difference
per name, tested across names:

> **133 symbols · mean +1.37pp · median +1.04pp · 79 of 133 positive (59%) ·
> p = 0.0015**

It survives. Mean and median agree, which rules out a handful of names carrying
it, and 59% positive is a modest but real majority.

### What the powered run does to BSE's number

**BSE alone said +16.05pp at h = 20. Across 150 names the same measurement is
+1.28pp — the same direction, one twelfth the size.** That is the entire argument
for the floor, restated in one line: a 9-event bucket did not lie about the
direction, it lied about the magnitude by a factor of twelve.

### The secondaries still do not rank — on ten times the data

| verdict tone | n | mean @20d | | quality | n | mean @20d |
|---|---|---|---|---|---|---|
| good | 1,297 | +0.97% | | STRONG | 1,686 | **+1.33%** |
| warn | 1,228 | **+1.12%** | | NORMAL | 1,844 | **−0.37%** |
| bad | 2,083 | −0.24% | | WEAK | 1,078 | +0.52% |

`warn` still beats `good`, and `NORMAL` still sits **below** `WEAK`. On 4,608
events that is no longer a small-sample wobble: **the graded quality score is not
ranking anything.** What carries the result is the binary — did price come back
through the level — and the `0.6·dist/ATR + 0.4·body/ATR` formula the card prints
is, so far, decoration.

## What this licenses, precisely

**Does**: the card's held/failed wording is now backed by a measurement rather
than by nothing, and the footer can say so. This is the first structure read on
this desk that is neither null nor inverted.

**Does NOT**:

* **It is held-vs-failed, not held-vs-doing-nothing.** No baseline arm was
  pre-registered and none was run, so nothing here says a held break beats buying
  the same bars blind. That is the obvious next test and it is not this one.
* **It is not a trade.** +1.28pp over 20 sessions, net of costs, on a two-bucket
  difference, with 59% of names positive.
* **It says nothing about the quality score**, which the same run shows is not
  ordering outcomes.

Live-data wobble, noted for honesty: two runs an hour apart returned 4,607 and
4,608 events (+1.29pp and +1.28pp). yfinance re-served the frames slightly
differently. Nothing here should be quoted past two significant figures.

## Run 3 (B-115) — held breaks vs DOING NOTHING

Run 2 answered "is a held break different from a failed one?" It never asked the
question a reader actually has: **is a held break different from just owning the
stock?** A two-bucket difference can be entirely a statement about the failed
side being bad.

Pre-registered and committed before the run (`26f3fda`): the baseline is **every
eligible bar in the same names and window**, same entry/exit timing, same costs.
Up-direction only, because this desk is long-only and "do nothing" means "own it
anyway" — scoring the short side would grade a trade the desk does not take.

**1,545 up-direction held breaks against 261,121 eligible bars:**

| h | held | baseline | **edge** | p |
|---|---|---|---|---|
| 5 | +0.27% | +0.05% | +0.21 | 0.183 |
| 10 | +0.83% | +0.52% | +0.31 | 0.139 |
| 20 | +2.29% | +1.47% | **+0.82** | **0.006** |
| 60 | +6.14% | +5.40% | +0.75 | 0.194 |

**Clustered (symbol as the unit): 130 symbols · mean +0.67pp · median +0.36pp ·
75/130 positive (58%) · p = 0.0297.**

**Verdict: POSITIVE at the pre-registered bar** — positive at h = 20 with
p < 0.05 and the sign holding at 5 / 10 / 60.

### Read it thinly, because it is thin

* **Only h = 20 is individually significant.** 5, 10 and 60 are all positive and
  none of them clears p = 0.05. The pass came from a criterion that asked for
  *sign stability* plus significance at the primary — which is what was written
  down, and it is a weaker thing than four significant horizons.
* **The clustered p is 0.0297, not 0.0015.** Run 2's two-bucket difference was
  the stronger result; measured against doing nothing, the same events are less
  impressive.
* **Mean +0.67 against median +0.36** says a minority of names carry more than
  their share. 58% positive is a majority, not a consensus.
* **So B-114's +1.28pp splits roughly in two**: about +0.8pp of "held is better
  than average" and the rest from "failed is worse than average". Both sides are
  real; neither is large.

### The down side, and a sign error worth recording

Description only — a long-only desk does not short it — and the first version of
this line was **wrong in a way worth keeping on the record**. It printed *"held
down-breaks fell −0.94%"*. They did not fall. The stored return is signed by the
event's direction, so −0.94 for a down event means the name **rose 0.94%**:

| h | after a held DOWN break | random bar | gap |
|---|---|---|---|
| 5 | +0.03% | +0.05% | −0.02pp |
| 10 | −0.05% | +0.52% | −0.57pp |
| 20 | **+0.94%** | +1.47% | −0.53pp |
| 60 | **+4.77%** | +5.40% | −0.63pp |

**A held downward break is an UNDERPERFORMANCE read, not a decline.** The name
still goes up; it goes up about half a point less over 20 sessions. As an "avoid"
signal that is weak, and it is not tested. The report now prints raw returns with
the gap, and a test pins the wording so "fell" cannot reappear for a number that
rose.

## Where this leaves the card

The card's held/failed wording is measured twice now: the two buckets differ
(B-114), and the held side genuinely beats owning the same bars (B-115) — by
about **0.8pp over 20 sessions, net of costs, on 58% of names**. That is a real
effect and a small one, and the card should keep describing structure rather than
proposing trades. The quality ladder remains unranked and remains decoration.
