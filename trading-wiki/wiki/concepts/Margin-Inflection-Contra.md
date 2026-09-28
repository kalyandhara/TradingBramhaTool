---
title: "Margin Inflection (contra screening)"
category: concept
family: fundamental-screening
tags: [contra, turnaround, opm, margin, pead, quarterly, unvalidated]
created: 2026-08-31
updated: 2026-08-31
related: [concepts/PEAD, concepts/Mean-Reversion, concepts/Stage-Analysis, analyses/Open-Backlog, concepts/FPV-Flow-Price-Volume-Ownership]
sources: 0
---

# Margin Inflection (contra screening)

A quality-value screen asks **what level** a business operates at. A contra screen
asks **which direction it just turned**. The two select disjoint sets, and a
business in the middle of a turnaround will fail the first while passing the second.

Worked example, both measured from free data on 2026-08-31:

| | AGI Greenpac | OCCL Ltd |
|---|---|---|
| ROCE / ROE | 19.4 / 14.6 | **11.6 / 11.1** |
| quality-value verdict | 9 of 10 criteria | **fails** |
| latest-quarter OPM vs year ago | 17.7 vs 19.6 (**down**) | **25.6 vs 16.0** |
| PAT YoY | +11.8% | **+206%** |
| contra verdict | NO_INFLECTION | **INFLECTING** |

Neither is "better". They are different shapes, and one screen cannot see both.

## Why the signal must be quarterly

The annual frame averages the turn away. OCCL's last four annual OPMs read
12.0 / 11.1 / — / 15.5: flat to declining. The quarterly series over the same
period reads 16.0 -> 10.8 -> 8.5 -> 12.2 -> **25.6**. The inflection is only
visible at quarterly grain, which is why `fundamentals_deep._quarterly_history`
had to gain an `opm` field for [[analyses/Open-Backlog]] B-50 to exist.

## The four traps

A naive "profit up 200%" filter finds mostly artefacts. Each has to be tested
**separately** and reported, not folded into one score:

1. **Low base.** +206% off a collapsed quarter is arithmetic. Two distinct tests:
   was the year-ago base below the trailing median, and is the latest print above
   *every* prior quarter (a new high, versus a return to trend)?
2. **One-off gains.** Other income, an asset sale or a tax writeback moves PAT
   without moving EBIT. **But PAT outgrowing EBIT is normal and often healthy** --
   debt paid down shrinks the interest line. The red flag is EBIT *not
   participating at all*, not EBIT failing to keep pace.
3. **Profit without cash.** `cfo_pat_ratio` (sum OCF / sum PAT).
4. **One good quarter.** Noise. Persistence must be counted.

> [!warning] The trap behind the traps: an unevaluated guard is not a passed guard.
> The first live run put **ITI Limited** at the top of the INFLECTING list on
> OPM 72.7% against 3.9%. Its four prior quarters all lost money and revenue was
> **down 40%**. Because the base was negative, `pat_yoy`, `operating_led` and
> `cfo_pat_ratio` were all `None` -- every guard silently no-opped and the silence
> read as approval. The fix is an explicit evidence gate and an `UNVERIFIED`
> verdict. This is the same failure mode as the `.info` ROE hole in B-49, and it
> is the one to watch for in any screen built on optional fields.

## Margin-led is not the same as growing

Margin up on flat or shrinking revenue is cost-cutting or mix. It can be a fine
outcome and it is not a rising star; conflating the two is how a shrinking
business gets sold as a growth story. The screen labels it `MARGIN_LED`
separately -- Bayer CropScience cleared every other test with revenue down 4.2%.

## Status: UNVALIDATED

[[concepts/PEAD]] is documented in Indian equities and survives controls for beta,
size, book-to-market, illiquidity and idiosyncratic volatility -- so *prices
under-react to earnings surprises* is a real effect. That is **not** evidence this
combination of filters finds multibaggers. The owed measurement is a forward event
study: enter at the first `INFLECTING` print, hold N days, against a matched
non-inflecting control, with the exact rotation p-value the repo now uses wherever
forward windows overlap.
