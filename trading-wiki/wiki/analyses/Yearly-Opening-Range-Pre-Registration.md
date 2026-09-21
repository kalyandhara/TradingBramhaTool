---
title: "Yearly Opening Range — Test Design (pre-registered)"
category: analysis
tags: [opening-range, calendar-anchor, pre-registration, gann, backtest, b-98, b-4, b-12]
timeframe: position
created: 2026-09-20
updated: 2026-09-20
sources: 1
related:
  - analyses/Open-Backlog.md
  - analyses/Bilateral-Expansion-Pre-Registration.md
  - analyses/Flag-Pole-Pre-Registration.md
  - sources/Bramesh-TradingView-Gann-Scanners-Product-Line.md
---

# Yearly Opening Range — Test Design (pre-registered)

**Written before any forward return has been looked at.** B-98 built
`tools/calendar_anchor.py` on 2026-09-20: the January high/low as an anchor, a
state (ABOVE / BELOW / INSIDE), and an event (the first close outside). This is
the measurement it was built for.

## Why this construct and not Anchored VWAP

Both are anchored levels. Anchored VWAP has been parked since B-4/B-12 for one
honest reason — **the anchor is a judgement call and nobody has built the UI for
it**. A calendar anchor removes exactly that half: January is January, two
readers get the same level from the same data, and there is nothing to tune.
That is what makes this measurable at all.

## The counted prior — and it is brutal

**Counted before writing anything else here, and before touching a single
forward return** (120 nifty500 names, ~10 years, `tools/calendar_anchor.py`):

| | |
|---|---|
| symbol-years | **972** |
| broke the range | **971 (99.9%)** |
| never left it | **1** |
| median sessions after January to the first break | **7** |
| broke within 5 sessions | **42.2%** |
| up / down | 431 / 540 (**44.4% up**) |
| median January range width | **16.1%** |

**The event is very nearly universal.** A construct that fires on 99.9% of
symbol-years selects nothing — it is a description of what markets do, not a
filter. Whatever else this study finds, a scanner built on "the January range
broke" cannot be a shortlist rule, and **it will not be registered as one**. The
prior for every claim below is therefore that it lands at or near the baseline.

This number is the reason the design changed before the run rather than after it:
the interesting question is not *whether* the range breaks.

## The claims

### A (primary) — does the DIRECTION of the break carry anything?

The event is universal; its direction is not (44.4% up). So: forward return from
the bar after the first break, **signed by the break direction**, against an
every-bar baseline over the same names and window, `COST_INDIAN` on both arms.
**Primary horizon h = 60 sessions** (this is a position-timeframe construct, not
a swing one), reported at 20 / 60 / 120.

Passes only if the signed edge is positive at h = 60 with p < 0.05 **and** the
sign holds at 20 and 120.

### B — does the STATE beat the EVENT?

The state (ABOVE / BELOW / INSIDE at a given date) is what a reader would
actually consult, and it is not the same thing as the break. Sample the state on
the **last session of each quarter** and compare forward returns of ABOVE vs
BELOW names. A state is not an event and cannot be de-duplicated the same way, so
this arm is explicitly secondary and is read as description if A fails.

### C — does HOLDING the break matter?

`still_outside` distinguishes a break that stuck from one that came straight
back. Split A's sample on it. **This is the one arm with a mechanism behind it**:
if the level means anything, the names that stayed outside it should differ from
the ones that did not.

## Pre-committed floors and guards

* **n ≥ 200 signals per arm**, or the arm is INCONCLUSIVE — not a null. The same
  rule that stopped B-101's 28-coil run being written up as a finding.
* **Clustering is the obvious threat here and is handled in advance**: every
  name breaks its range in the same few weeks of the same calendar year, so
  signals are massively correlated by year. The pooled t-test will therefore be
  reported *alongside* a **by-year** breakdown (one mean per calendar year,
  tested across years), and **the by-year test is the one that decides**. A
  pooled p-value on 971 signals that are really ~10 independent years would be
  the most overstated number this desk has ever printed.
* No subgroup rescues a failed primary. B and C are description if A fails.

## What this can and cannot become

Whatever the result, `calendar_anchor` stays a **level and state provider**, not
a shortlist scanner — the 99.9% base rate settles that regardless of edge. The
plausible homes are a chart overlay (the January range as two lines, the way the
session-VP levels already draw) and a context line on a card. If A and C both
fail, the honest outcome is that it stays a drawn level with no claim attached,
which is still more than the desk has today.

## What will be published either way

Into [[analyses/Open-Backlog]] under B-98 and into `named_studies.STUDIES`, with
n, the by-year spread and the p-values — pass, fail or inconclusive.
