---
title: "SBC card reading — BSE Ltd: INCONCLUSIVE, and the first run was measuring an artifact"
category: analysis
tags: [structure-break-chain, choch, bos, market-structure, backtest, bse, b-114, inconclusive]
timeframe: swing
created: 2026-09-21
updated: 2026-09-21
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/SVP-Structure-Signal-Pre-Registration.md
  - concepts/Market-Structure-CHOCH-BOS.md
---

# SBC card reading — BSE Ltd

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
