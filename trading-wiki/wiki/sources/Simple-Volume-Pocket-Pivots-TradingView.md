---
title: "Simple Volume with Pocket Pivots (TradingView, finallynitin)"
category: source
tags: [volume, pocket-pivot, relative-volume, dry-volume, tradingview, protected-source, chart-module, unmeasured]
created: 2026-09-22
updated: 2026-09-22
sources: 1
related: [concepts/Volume-Analysis, sources/Chartink-Darvas-Volume-Shockers-Screener, analyses/Open-Backlog]
---

# Simple Volume with Pocket Pivots

## Metadata
- Author: finallynitin (TradingView)
- URL: https://in.tradingview.com/v/JkB0iCFp/
- Licence: **PROTECTED SOURCE — the Pine code is not published.**
- Format: TradingView indicator, described in prose by the author + a long
  changelog of later additions
- Ingested: 2026-09-22 (page read; **no code was available and none was copied**)

> **Provenance note, and it is the load-bearing one.** Everything below is taken
> from the author's own DESCRIPTION, not from source. The build that came out of
> this ingest (`tools/simple_volume.js`) is therefore an **independent
> implementation from a published specification** — where the prose is ambiguous
> we chose, and the choices are recorded here so a later reader can tell our
> decision from his.

## Key Takeaways

1. **The idea is SUBTRACTIVE, and that is the whole contribution.** Ordinary
   volume draws every bar alike and leaves the reader to compare each one against
   a moving-average line by eye. This colours the four bars that mean something
   and greys the rest. The author **deliberately does not plot the MA** — once
   "above average" is a colour, the line is redundant furniture. That is a
   presentation idea, not a signal idea, and it is the part worth taking.

2. **Pocket Pivot Volume (blue)** — an UP day whose volume exceeds the highest
   volume of any DOWN day within the last 10 days. Borrowed from the
   O'Neil/Morales–Kacher literature, where it is read as institutional
   accumulation showing up before a conventional breakout.

3. **The author corrected his own published wording, and the correction is
   strictly tighter.** The original text says "the last 10 **down** days"; the
   rule he states on correction is the down days **inside the last 10 TRADING
   days**. These are very different lookbacks — in a quiet uptrend "the last 10
   down days" can reach back two months and import a stale high-volume selloff as
   the bar to beat. We implement the corrected reading.

4. **Dry volume (orange)** — volume at or below MA/5. This is the half of the
   indicator that gets ignored and is arguably the more useful one: a name that
   has stopped trading is a different observation from a name that is falling.

5. **Green / red** are simply up-day and down-day volume above the 50-period MA;
   **grey** is everything else, and is meant to be unremarkable.

6. **The changelog is where the scope creep lives.** Later versions added RVol %,
   "Bull Snort" (3× average + close in the top 35% of the bar + close above the
   previous close), HVE/HVY/HVQ and LVQ/LVY labels (highest volume ever / this
   year / this quarter), a turnover table in Crores, "power volumes", projected
   volume and a 1-minute-liquidity read. **None of it is specified precisely
   enough in prose to implement faithfully**, and most of it is a different
   indicator wearing the same name.

## What we built, and what we deliberately did not

Built — `tools/simple_volume.js` + `tools/test_simple_volume.py` (14 tests),
wired into the chart as **Simple Volume (Pocket Pivots)** with a small card:

- the five colour classes, with the **corrected** pocket-pivot lookback
- RVol as a percentage of the bar's own 50-day average
- pocket-pivot and dry-bar counts over the last 20 bars — the clustering is the
  thing the author's "accumulation" claim actually rests on, and a single blue
  bar says much less than four in a fortnight

Three judgement calls the prose does not settle, recorded so they are ours:

- **The average is null until its window is full.** A 12-bar IPO has no 50-day
  average; inventing one from 12 bars would colour its entire history against a
  number that does not exist. Bars before bar 50 are grey, all of them.
- **Dry outranks everything.** A dry bar on an up day is dry, not "up" — the
  quiet is the observation.
- **An empty comparison is not a pass.** With no down day inside the 10-bar
  window there is nothing for the up volume to have overwhelmed, so we call that
  bar "up", not a pivot. The opposite choice would paint the strongest stretch of
  a runup blue on no evidence.

Declined: Bull Snort, the HV/LV labels, the turnover table, power/projected
volume, 1mL. Named here rather than half-built.

## Contradictions with existing wiki

- **None mechanical** — the 50-period volume MA and the relative-volume ratio
  agree with what [[sources/Chartink-Darvas-Volume-Shockers-Screener]] screens on
  (that one uses a shorter base and a hard multiple; this one uses the ratio as a
  colour).
- **One of emphasis.** The pocket pivot is sold as an *early* accumulation tell —
  a reason to be in before the breakout. This desk's own measured position is
  that volume-confirmed events are where the null results keep landing, and
  nothing here changes that.

## Status on this desk

**UNMEASURED.** No forward-return study backs any of these colours here, the card
says so on the chart, and the indicator carries no vote anywhere in confluence —
it is not in `opportunity_hub`, not in a scanner, and not in a plan. It is a
better way to *look* at the volume histogram, and that is all it claims to be
until someone runs it.

The obvious study, if it is ever worth the bars: **do pocket pivots cluster
before breakouts more than chance**, with the symbol as the unit of clustering
(the `ob_bias_clustered` precedent) — because "blue bars appear in strong names"
is true by construction and would otherwise read as a result.
