---
title: "CVD Data Probe — the answer is FAIL, and it is about the data not the code"
category: analysis
tags: [cumulative-volume-delta, order-flow, data-probe, intraday, b-48, measured-fail]
timeframe: intraday
created: 2026-09-21
updated: 2026-09-21
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/Pipeline-Alignment-Audit.md
  - concepts/Volume-Profile.md
---

# CVD Data Probe — B-48

B-48 sat in the BUILD tier with an instruction rather than a task: **"answer the
DATA question first, before any indicator."** This is that answer.

## What CVD requires, and what the desk has

Cumulative volume delta sums **signed** volume — buy-initiated minus
sell-initiated. Deciding which side initiated a trade needs the trade printed
against the book: the aggressor flag, or at minimum the bid/ask it crossed.

**The desk has no such data and no route to it.** `intraday_store` holds OHLCV
bars (5m and 15m for ~87 sessions, 1h for three years); yfinance serves no tick
stream and no bid/ask history. So a true CVD is not computable here — settled by
the data, not by effort.

What *is* computable is a **proxy**: sign each bar's volume by the bar's own
direction. Every charting package offering "CVD" on OHLC data does this, usually
without saying so.

## The question, and the bar set before the run

A proxy is worth having only if its answer is a property of the **market** rather
than of the **bar size you happen to hold**. Pre-committed in
`tools/cvd_data_probe.py` before the first run:

> **PASS** — session proxy CVD agrees in sign between 5m and 15m bars on ≥ 90%
> of symbol-sessions *and* correlates ≥ 0.90.
> **FAIL** — below either.

## Result — FAIL

435 symbol-sessions, 5 names, 87 sessions each, same store, same sessions:

| proxy | symbol-sessions | sign agreement | correlation |
|---|---|---|---|
| **sign** (close vs open) | 435 | **75.6%** | **0.80** |
| **range** (close's position in the bar) | 435 | 77.2% | 0.72 |

| symbol | sessions | agree | r | sign flips | 15m magnitude ÷ 5m |
|---|---|---|---|---|---|
| HDFCBANK | 87 | 80% | 0.75 | 17 | 1.39× |
| ICICIBANK | 87 | **68%** | 0.82 | **28** | 1.83× |
| INFY | 87 | 75% | 0.88 | 22 | 1.40× |
| RELIANCE | 87 | 78% | 0.81 | 19 | 1.63× |
| TCS | 87 | 77% | 0.84 | 20 | 1.41× |

**One session in four changes its mind about who was in control when you switch
from 5-minute to 15-minute bars** — 28 of 87 on ICICIBANK. And the coarser bars
do not merely re-sign the day, they **inflate it**: 15m keeps 1.4–1.8× the
magnitude of the 5m total, because aggregation hides the intra-bar reversals that
cancel out at finer resolution.

### The two proxies do not agree with each other either

On the **same** 5-minute bars, `sign` and `range` disagree about the session's
direction on **26% of symbol-sessions** (73.8% agreement, 435 sessions). The
unstated choice between two equally conventional formulas moves the answer about
as much as changing the timeframe does.

### One correction, made before publishing

The first run reported 79.7% and included **`^NSEI`, which has no volume at
all**: every delta is zero, every session "agrees" trivially, and it contributed
87 free sessions of 100% to the pooled number. Excluding it drops the headline
four points to 75.6%. A symbol that *cannot* have a volume delta is not evidence
that volume deltas are stable.

## What this means for the indicator

**Do not build a CVD indicator on this data as if it measured order flow.** It
would measure the chart's resolution about as much as the tape, and the reader
would have no way to see that from the line.

Three honest options, in the order they are worth doing:

1. **Drop it.** The desk already has volume-profile surfaces built on the same
   bars and measured three times without support ([[analyses/SVP-Structure-Signal-Pre-Registration]]).
   A fourth volume-derived read with a known instability is a hard sell.
2. **Ship it only as a named, bar-size-explicit proxy** — labelled *"delta proxy
   (5m bars, close-vs-open)"*, never "CVD", with the 76% figure on the card. That
   is the FR-4 rule applied to an indicator: a number that cannot be checked must
   say so where it is read.
3. **Get the data.** A tick or bid/ask feed makes the real thing computable and
   makes this page obsolete. That is a subscription decision, not a coding one.

**None of these is chosen here.** The probe was asked to decide whether the data
supports the indicator, and the answer is no.
