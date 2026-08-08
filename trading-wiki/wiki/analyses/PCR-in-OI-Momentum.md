---
title: "Should PCR join the OI Momentum verdict?"
category: analysis
tags: [pcr, oi-momentum, options, verdict, sentiment, architecture]
timeframe: milestone-plan
created: 2026-08-07
updated: 2026-08-07
sources: 1
related:
  - concepts/Put-Call-Ratio.md
  - concepts/Market-Sentiment-Index.md
  - analyses/Market-Sentiment-Futures-Roadmap.md
  - analyses/Backtest-Harness.md
  - sources/Fingrad-PCR-Infographic.md
---

# Analysis: Should PCR join the OI Momentum verdict? — 2026-08-07

## Thesis

**Yes to computing PCR. No to putting it inside the verdict.** It should sit
*beside* the verdict as a confirm/diverge tag, not inside the label.

The data is free, the wiring is small, and the reading is genuinely useful — but
folding it into `classify()` would blend two different position bases into one
word and import an ambiguous signal into a currently unambiguous one.

## What the OI Momentum verdict currently is

`nse_oi_momentum.py` produces a **futures-positioning quadrant**: near-month
price change against series-total futures OI change, yielding Long Buildup /
Short Covering / Short Buildup / Long Unwinding, plus a `strength` tier gated on
turnover, days-to-expiry and rollover contamination.

Its virtue is that it is **mechanically derivable**: every output traces to two
named bhavcopy fields and a set of published floors. There is no opinion in it
that cannot be checked.

## Feasibility — better than the roadmap assumed

The blocker recorded against PCR (`sentiment_index.py` factor 5: "requires NSE
option-chain feed") **is stale.** The F&O bhavcopy the module already downloads
contains, on 2026-08-06:

| `FinInstrmTp` | Rows | What |
|---|---|---|
| STO | 27,277 | stock options |
| IDO | 5,026 | index options |
| **STF** | **622** | **stock futures — the only rows currently used** |
| IDF | 15 | index futures |

with `OptnTp` (CE/PE), `OpnIntrst` and `ChngInOpnIntrst` present. Both index and
per-stock PCR are computable from a file already on disk at **zero additional
network cost**. The option rows are discarded solely by the
`FinInstrmTp == "STF"` filter.

Same shape as the PEAD "no consensus estimate for NSE" episode: *a data-source
limitation is a measurement with a date on it, not a property of the world.*

## Evidence For (why compute it)

- **Free.** No new fetch, no new failure mode, no new rate-limit surface.
- **It answers a question futures OI cannot.** Futures OI says whether a move
  was built or unwound. PCR says how the *option* book is positioned around it.
  A long buildup into a falling PCR is a different tape from one into a rising
  PCR.
- **The price × PCR grid is the same shape we already use.** Confirm / diverge
  against price is exactly the OI quadrant's logic, so it composes naturally as
  a second column.
- **It closes a documented gap** — [[concepts/Market-Sentiment-Index]] factor 5
  has been unbuilt since inception for a reason that no longer holds.

## Evidence Against (why not in the verdict)

**1. It blends two position bases into one label.** The quadrant is a statement
about *futures* OI. PCR is a statement about *options* OI. Merging them produces
a label that cannot be inverted back into its inputs — "BULLISH" would no longer
tell you whether futures or options drove it. The quadrant's inspectability is
its main asset and this spends it.

**2. PCR has no fixed sign.** Trend-following reads PCR > 1 as bullish;
contrarian reads extreme PCR as crowding and reversal-prone. Both are standard,
and [[sources/Fingrad-PCR-Infographic]] asserts both without reconciling them.
Nothing inside PCR says which regime applies. **Folding a directionally
ambiguous input into an unambiguous verdict makes the verdict worse, not
better.**

**3. The obvious thresholds are measurably wrong here.** The textbook bands
label **59% of 208 NSE underlyings "bearish" and 5% "bullish"** on an ordinary
session, median stock PCR being 0.675 (full distribution on
[[concepts/Put-Call-Ratio]]). Any verdict wired to those bands would inherit a
permanent bearish tilt. Percentile thresholds fix this, but they must be
*measured first* — which is work, not a wiring change.

**4. It is unmeasured.** [[analyses/Backtest-Harness]] has never tested PCR.
This repo has just spent a commit removing unmeasured and correlated inputs from
a score that was quietly over-counting them (the family-capped confluence work).
Adding a fresh unmeasured input to a different verdict the same week would undo
that lesson rather than apply it.

**5. PCR already has an assigned owner.** It is factor 5 of
[[concepts/Market-Sentiment-Index]] at weight ~20. Implementing it *inside*
`nse_oi_momentum.py` instead would create a second implementation of the same
quantity — the drift this codebase keeps paying to remove (`rating.py`,
`fundamental_score.py`, `run_scanner_pipeline`).

## Conclusion — the recommended shape

**One PCR primitive, two consumers, and it never touches `classify()`.**

1. **Build `pcr.py`** (or extend `nse_oi_momentum.fetch_fo_bhavcopy` to return
   option rows as well). One function: series-total put/call OI → PCR, per
   underlying and per index, plus the day-over-day change from
   `ChngInOpnIntrst`. Pure, no opinion.
2. **Calibrate thresholds from the cross-section**, per instrument class
   (index vs stock), exactly as `MIN_OI_PCT` and friends already are. Publish the
   percentiles in the module the way the existing floors are published.
3. **In OI Momentum, render PCR as a second column with a confirm/diverge tag** —
   never as an input to the quadrant:
   - Long Buildup + PCR rising → *options positioning agrees*
   - Long Buildup + PCR falling → *options positioning diverges*
   The quadrant stays exactly as derivable as it is today; the reader gets the
   extra dimension explicitly labelled as a separate opinion.
4. **Prefer PCR *change* over PCR *level*** for the tag. Level is structural
   (hedging habits, strike coverage, listing age); change differences most of
   that out. The sentiment roadmap already specifies "PCR + PCR-slope".
5. **Feed the same primitive into `sentiment_index.py` factor 5**, which is where
   a weighted PCR opinion is supposed to live.
6. **Measure before promoting.** If PCR is ever to *move* a verdict rather than
   annotate one, it goes through the backtest harness first — with the caveat
   already on record that the harness has no significance test yet.

**One-line answer:** PCR can and should be computed — it is free — but it belongs
*next to* the OI-momentum verdict as an options-side confirm/diverge tag, and
*inside* the Market Sentiment Index as a weighted factor. It should not be
allowed to change the futures quadrant, which is currently clean, unambiguous
and fully inspectable.

## Action Taken / Plan

- ✅ Ingested [[sources/Fingrad-PCR-Infographic]]; created
  [[concepts/Put-Call-Ratio]] with the measured cross-section (2026-08-07).
- ✅ Established that the option-chain blocker on `sentiment_index.py` factor 5
  is stale — the data is already downloaded.
- ✅ **`pcr.py` primitive SHIPPED 2026-08-07, stock-first**, with stock and index
  kept structurally distinct (own filters, own floors, own calibration
  machinery). `nse_oi_momentum.fetch_fo_bhavcopy_raw()` added so one download
  serves both consumers; the existing `fetch_fo_bhavcopy()` API is unchanged.
- ✅ **OI Momentum second column SHIPPED** — `PCR / PCR %ile / ΔPCR / Options`
  plus a per-name line, explicitly outside the verdict, with the index table in
  its own expander so the two scales are never side by side.
- ⏭ Sentiment Index factor 5 wired to the same primitive.
- ⏭ **Store an index PCR history** — the one thing blocking an index band.
- ⏭ Re-measure the liquidity floors and percentile cuts across more sessions;
  both were set from a single day.
- ⏭ Backtest before PCR is allowed to move any verdict.

## Outcome

**2026-08-07 — shipped as designed, and the stock/index split turned out to be
forced rather than merely tidy.** The intended reason for separating them was
*level* (index puts carry hedging demand single-stock options do not, so index
PCR sits near 1.0 against a 0.675 stock median). The stronger reason emerged
while building: the two classes cannot share a calibration **method**. Stock PCR
self-calibrates against 208 same-day peers and needs no stored history; index
PCR has 5 observations a day, one of them (NIFTYNXT50, PCR 2.014 off 5,200
contracts) pure noise, so it can only be ranked against its own past — which
nothing here stores. Hence `index_reading()` ships deliberately unbanded with a
`band_reason` rather than borrowing the stock cuts.

Verified on the 2026-08-06 session: 208 stock underlyings (186 liquid,
calibration median 0.675, quintile cuts 0.577/0.639/0.701/0.800); bands split
37/37/37/37/38 as percentile cuts must; 5 index underlyings with FINNIFTY
(786,600 OI) and NIFTYNXT50 (5,200) correctly excluded by the index floor with
an explicit reason; join into OI Momentum covered **52 of 57 readings (91%)**,
the remaining 5 blank rather than fabricated; confirm/diverge fired 13 times and
stayed silent 44. The existing `fetch_fo_bhavcopy()` contract was re-checked
after the refactor and returns the same 622 STF-only rows.

## Outcome (fill in later)

## Related Pages

- [[concepts/Put-Call-Ratio]] — the concept, thresholds and measured distribution
- [[concepts/Market-Sentiment-Index]] — PCR's assigned home (factor 5)
- [[analyses/Backtest-Harness]] — why an unmeasured input does not get a vote
