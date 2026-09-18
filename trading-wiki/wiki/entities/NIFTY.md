---
title: "NIFTY 50 — NSE benchmark index"
category: entity
ticker: NIFTY
bias: neutral
tags: [nifty, index, nse, benchmark, india, spot]
created: 2026-09-18
updated: 2026-09-18
sources: 1
related: [sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18, concepts/Gann-Angles-And-Trend-Change-Levels, concepts/Participant-Positioning-FII-DII, concepts/Put-Call-Ratio, concepts/Volume-Profile, analyses/Open-Backlog]
---

# NIFTY — NSE Nifty 50

Created 2026-09-18. **The index had no page**, despite being the reference this desk's
baselines, breadth readings and index-option tooling are all computed against — a gap worth
recording as the reason this page exists.

## Profile

NSE's 50-constituent free-float-market-cap benchmark. On this desk it appears as:

* the **baseline** most measured claims are scored against (the +5.05%/60d figure cited in
  [[sources/YT-Devendra-Renko-Intelligence-Commodities]]),
* the index side (**IDO**) of `tools/option_chain.py` — max pain and OI walls,
* the breadth denominator: a 36:14 advance–decline is 50 names, the index's own.

## Price & chart context

| As of | Close | Change |
|---|---|---|
| 2026-09-17 | **23,270** | +61 |

Context per [[sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18]]: **seven consecutive
weeks of decline**, with the 2026-09-17 session claimed as **the first higher high in 20
sessions**. PCR **0.99**, recovered from 0.65.

**This is a dated snapshot and nothing more.** It is not maintained daily and should be
re-derived from the price cache before use.

## Key levels — SNAPSHOT 2026-09-18, one source, decayed on sight

> [!warning] These are one analyst's levels for one session
> Recorded so the source is auditable, **not** as this desk's view. Unbacktested method
> (Gann angles, undisclosed scaling), no hit rate published. Do not trade from this table.

```
Resistance:  23,500 (highest call OI — the only level here we can recompute)
Resistance:  23,440 (overhead descending trendline)
TCL:         23,372 (positional trend-change level — bull case needs a close above)
Max pain:    23,300
Spot:        23,270
Support:     23,244 (claimed Gann inflection)
Support:     23,189 (claimed Gann harmonic)
Stop zone:   below 23,135 (invalidation; opens 23,070 / 23,000)
Support:     23,100 (highest put OI — recomputable)
Target 1:    23,484  Target 2: 23,550 (contingent on a short squeeze that has not occurred)
```

**Of these ten levels, exactly two — the OI walls at 23,500 and 23,100 and the 23,300 max
pain — are derivable from data this desk already holds.** The rest require a method that
was not disclosed. That asymmetry is the point, and it is what **B-94** tests.

## Positioning (same snapshot)

FII index futures **12:88 long:short**; client **84:16**; FII cash **−₹3,208 cr** against
DII **+₹3,617 cr**, i.e. **net institutional +₹409 cr**. See
[[concepts/Participant-Positioning-FII-DII]] for why the 88% short figure is **not** read
here as a squeeze trigger: it is an autocorrelated state that persisted throughout the
seven-week decline it is now offered as the bottom of.

## Catalysts & news

None recorded.

## Linked strategies

None. No strategy on this desk trades the index directly — the scanners are
cash-equity-universe tools, and NIFTY enters only as baseline and as option-chain
underlying.

## Notes & observations

* **Bias is `neutral`, deliberately.** The source is labelled bullish, but by its own rules
  spot (23,270) sat below the trigger (23,372) and above the invalidation (23,135). Copying
  the label without the trigger would be the exact error
  [[concepts/Gann-Angles-And-Trend-Change-Levels]] warns about.
* This page should stay **thin**. It is a reference anchor and a snapshot ledger; the index
  changes daily and the wiki is not a price feed.

## Sources

* [[sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18]] — 2026-09-18
