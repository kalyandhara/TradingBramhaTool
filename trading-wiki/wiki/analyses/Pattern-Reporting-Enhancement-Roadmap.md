---
title: "Pattern Reporting — Enhancement Roadmap (the page exists; it is the content that is thin)"
category: analysis
tags: [patterns, scanner-hub, strategy-hub, roadmap, trade-plan, flag-and-pole, b-92, b-93]
timeframe: milestone-plan
created: 2026-09-17
updated: 2026-09-17
sources: 1
related:
  - sources/Spider-Software-Flag-Pole-Infographic.md
  - analyses/Open-Backlog.md
  - analyses/Dashboard-UI-Roadmap.md
  - concepts/High-Tight-Flag.md
---

# Analysis: Pattern Reporting — Enhancement Roadmap

## Thesis

The owner asked for a pattern reporting page, and to write an enhancement
roadmap instead if one already exists. **Two already exist**, so this is the
roadmap.

**The pages are not the problem. The content behind them is.** Counted rather
than asserted, 2026-09-17:

| | |
|---|---|
| Registered pattern scanners | **46** |
| …that fired at all on a 60-name nifty500 slice | **31** |
| …that emitted a full `entry`/`stop`/`target` | **7** |
| Rows in Strategy Hub's "Chart Patterns" table | **20, all hardcoded** |
| Flag-family detectors | **1** (`High Tight Flag`), and B-19 could not score it for too few signals |
| Bear continuation detectors | **0** |

So a reader on the pattern surface sees a long list of names with no levels, and
on the other page a frozen table of someone else's August detections.

## Evidence For — what actually ships

### Two pages, both real

* **Scanner Hub** — *"46 pattern scanners, run on any universe"*. This is the
  genuine pattern reporting page: a real run, summary + confluence tables, chart
  icons, notes, pledge and price enrichment. **Nothing here needs replacing.**
* **Strategy Hub § Chart Patterns** — a bordered card titled "Chart Patterns ·
  Major Stocks".

### The Strategy Hub pattern table is static — this is the P0

`dashboard_app.py` holds `_PATTERNS` as a **Python literal of 20 tuples**:

```
("CE Info Systems",   "Double Top", "Bearish", "04 Aug", 1231.95, 1013.30, -17.7),
("Zee Entertainment", "Double Top", "Bearish", "03 Aug",  118.35,   91.56, -22.6),
…
```

Stock, pattern, bias, publish date, publish price, LTP and move — **all frozen**.
The caption says *"Past detections from StockEdge (EOD, AI + Human hybrid)"*, so
it is honest about being third-party and historical. It is **not** honest about
being **static**: the "LTP ₹" column and the "Move %" it drives are baked-in
numbers that will read as live to anyone who does not open the source, and the
footer computes "N above publish price / M below" from them — **a scoreboard over
frozen data**.

That is a stale-claim of exactly the class [[analyses/Open-Backlog#B-79]]
addressed, and `claims_lint` cannot see it because the numbers live in a tuple
rather than in prose.

### Only 7 of 31 firing scanners carry a trade plan

Measured on 60 nifty500 names. The 24 without include `Structural Breakout`,
`VCP Coiling`, `Stage 2 Uptrend`, `Pullback Entry`, `Darvas Box`,
`Momentum Continuation`, `Near Pivot`, `VWAP Reclaim/Support` and
`High Tight Flag`.

**This is not cosmetic.** `backtest._simulate_plan` walks entry → stop/target, so
a scanner with no plan **cannot be scored on realised R at all** — only on raw
forward return. Plan coverage is a measurement capability, not a display nicety.

### The flag family is one rare special case

`scan_high_tight_flag` demands a **≥90% pole inside ~40 bars** and a flag
correcting **≤25%** on contracting volume. That is the rarest member of the
family, and B-19 confirms the consequence: it was one of **three scanners with
too few signals to measure**.

The general flag — a *proportionate* pole and a shallow pause — would fire often
enough to be measurable, which is the strongest argument for building it. **The
bear side does not exist in any form.**

## Evidence Against — reasons to keep this small

1. **B-19: 0 of 41 scanners stable after costs.** Adding a 47th pattern is not
   expected to find edge. Justify on **coverage and plan quality**, never on
   expected return, and keep it out of any scoring path until measured.
2. **A loose flag definition is worse than no flag.** Drop the pole threshold far
   enough and "flag" becomes "any pullback in an uptrend", which the desk already
   has as `Pullback Entry` — **and has measured NEGATIVE** (−0.43% / −1.12%).
   B-58's quasimodo work is the precedent: independent pivot search reported the
   pattern on **73%** of names; requiring adjacency cut it to 44%, and the real
   count was **3%**. Count the hits before trusting the detector.
3. **Bear continuation is largely unusable on NSE cash.** This repo already
   records that shorting for a swing hold is not available to most of its users.
   The inverted flag's value here is **exit and avoid**, not entry — the same
   scoping applied to [[analyses/Open-Backlog#B-90]].

## Conclusion — the roadmap

Four rungs, ordered by *reader harm*, not by build size. **PR-1 is the only one
that fixes something currently misleading.**

| # | Rung | Why it is at this rank | Size |
|---|---|---|---|
| ~~**PR-1**~~ | ~~Strategy Hub's pattern table presents frozen numbers as live~~ — **DONE 2026-09-17**: LTP recomputed from the batched price source, Move % derived, scoreboard reports its denominator | one row was counted on the wrong side of its own scoreboard | done |
| ~~**PR-1b**~~ | ~~"Trading Strategies · Live Counts" is also frozen~~ — **DONE 2026-09-17**: the heading no longer says Live, and the computed "Net" line is gone | the heading was the boldest claim on the page and the one thing never true | done |
| **PR-1c** | **"Fundamental Scores · Top Picks" is the third frozen literal** — `_FS_DATA` carries `ltp` and `ltp_chg`, under a caption saying *"computed from the last fundamental data pull"* | same defect again; scores need a source decision, but the LTP half is the PR-1 fix verbatim | owner |
| **PR-2** | **Trade-plan coverage as a first-class, visible metric.** Show which scanners carry `entry`/`stop`/`target`; treat a plan as part of a scanner's definition | unlocks R-based scoring for 24 scanners; absence currently invisible | medium |
| **PR-3** | **The Flag & Pole detector, both directions** ([[analyses/Open-Backlog#B-92]]) — emitting the card's three levels | closes a named absence; the bear half is total | medium |
| **PR-4** | **A flag/pole chart overlay**, after PR-3 | `falling_wedge` / `vcp` / `roundbottom` set the precedent; no point drawing before detecting | small |

### PR-1 — DONE 2026-09-17, by the second route

**The prices are recomputed.** `tools/pattern_reports.py` owns the roster; the
dashboard block is now a thin call. The detections stay frozen — pattern, bias,
publish date and publish price are a record of what a third party called and
when, and rewriting those would invent detections this desk never made. **Only
LTP moves, and Move % is DERIVED from it rather than stored**, so the printed
move and the printed prices can never disagree again.

> [!key-insight] It was not merely stale — one row was on the wrong side of its own scoreboard
> | | publish | frozen LTP | live LTP |
> |---|---|---|---|
> | **SPLPETRO** | 788.00 | 685.25 (**−13.0%**) | 807.00 (**+2.4%**) |
> | MAPMYINDIA | 1231.95 | 1013.30 (−17.7%) | 889.80 (−27.8%) |
> | ZEEL | 118.35 | 91.56 (−22.6%) | 78.31 (−33.8%) |
>
> Supreme Petrochem was being counted as **below** its publish price while it was
> trading **above** it. The frozen footer read **12 above / 8 below over 20**; the
> live one reads **12 above / 5 below, scored on 17 of 20** — and it now says the
> denominator, because three detections have no publish price and therefore
> cannot carry a move at all.

**Three things this pass got right only because they were checked on the running
page, not reasoned about:**

1. **The symbol is pinned per row, never fuzzy-matched.** The closest name matches
   on this very roster include **INFY for "CE Info Systems"** (correct:
   MAPMYINDIA) and **M&MFIN for "Mahindra & Mahindra"**. A mis-resolved symbol
   shows another company's price under this company's name — worse than the
   frozen number it replaces. The symbol is now a visible column so a reader can
   check the mapping rather than trust it.
2. **A scoreboard bug the unit tests could not see.** `scoreboard` filtered on
   `is not None`, but a `None` becomes a float **NaN** on the way through a
   DataFrame, and NaN *is not* None — so the price-less rows counted as SCORED
   while falling out of both arms. The live footer read *"12 above, 5 below,
   scored on 20 of 20"*. Fixed, and the regression test now goes through a
   DataFrame because that is what the dashboard actually does.
3. **The three price-less rows render a grey "None", not an empty cell** — and
   that is Streamlit's missing-value placeholder, not our data. The values are
   verified NaN before they reach the grid, and removing the printf format does
   not change it; both were tested on the running page. The caption names those
   rows and why they cannot carry a move. The same placeholder appears on the
   Watchlist's SVP column and is tracked separately.

**Still frozen, and now the larger one:** the block immediately below is titled
**"Trading Strategies · Live Counts"** and its caption says *"Counts as of 11 Aug
2026"*. `_STRATEGIES` is another hardcoded literal, and the *"Net: 20 bullish
signals vs 2 bearish"* line is computed over those frozen counts — the identical
defect PR-1 just fixed, under a heading that asserts **"Live"**. Raised as
**PR-1b**; it needs a source decision first, since there is no obvious live feed
for a third party's strategy-scan counts.

### PR-1b — DONE 2026-09-17, the owner's call

Owner chose the honest-minimum route here rather than finding a source, and it
was the right call: unlike LTP there is no live feed for a third party's
strategy-scan counts, so the only options were to stop claiming they were live or
to stop showing them.

**Three edits.** The heading `Trading Strategies · Live Counts` becomes
`· Snapshot`. The caption now opens with *"A fixed snapshot from 11 Aug 2026, not
a live count — these scans are a third party's and nothing on this desk re-runs
them"*, and separates what is a record (the descriptions and horizons) from what
is a dated observation (the counts). And the **`Net: 20 bullish signals vs 2
bearish · bullish skew in strategy engine is consistent`** line is deleted
outright — it summed the frozen counts and read as a finding about the market
when it was a finding about a literal.

**The page header was corrected too**, because PR-1 had made it wrong in the
other direction: it said `Snapshot: 11 Aug 2026` over everything, while the
pattern block is now live-priced. It reads
`Chart patterns (detections 11 Aug 2026, prices live) · trading strategies +
fundamental scores (11 Aug 2026 snapshot)` — one date per claim.

> [!warning] PR-1c — a third frozen literal in the same page, found while doing this
> `_FS_DATA` under **"Fundamental Scores · Top Picks"** carries hardcoded `ltp`
> and `ltp_chg`, beneath a caption reading *"Scores computed from the last
> fundamental data pull"*. That is the same defect a third time.
>
> Not fixed, and not bundled in: the **LTP half is the PR-1 fix verbatim** and
> could be done today, but the **scores** need a source decision — whether they
> are recomputed from `fundamentals_deep` or relabelled as a dated sample. That is
> an owner call, exactly as PR-1 and PR-1b were.
>
> **Three for three.** Every hardcoded block on this page presented itself as
> current. That is the pattern worth naming, not the individual rows.

### PR-1's original statement, kept for the record

The honest minimum is **one caption change and one deletion**: say the block is a
**fixed sample captured in August**, and remove the "N above / M below" footer,
because a scoreboard computed from frozen prices is a claim about outcomes that
nothing is measuring. The better version recomputes LTP from the cache the rest
of the desk already uses, at which point the scoreboard becomes real.

**Do not silently refresh the numbers in place.** Whichever route is taken, the
block should say which it is — the [[analyses/Open-Backlog#B-26]] lesson about
changing what a displayed number means.

### PR-3, the parameters that decide whether it is a detector or noise

Left open deliberately; each is a decision, and the count comes before the choice:

* **Pole:** minimum move **in ATR**, not per cent — a 20% pole means something
  different on a low-vol large cap and a micro cap.
* **Flag:** maximum retracement of the pole (the classic cap is ~38–50%; HTF's
  own is 25%), maximum duration, and whether contracting volume is **required**
  (HTF rejects a rising-volume flag outright, and that rule is well argued —
  a flag on rising volume is distribution into strength).
* **Breakout:** close beyond the flag boundary vs intrabar touch. This desk's
  convention is close-confirmed.
* **Target:** pole height projected from the breakout, exactly as the card draws
  it — and reported as a **projection**, never as a forecast.

**Count first, as B-58 forced.** If the chosen gates fire on more than a few per
cent of a 500-name universe, they are too loose and the number should be
published before any edge is claimed.

## Action Taken / Plan

Raised as **[[analyses/Open-Backlog#B-92]]** (the detector) and
**[[analyses/Open-Backlog#B-93]]** (this roadmap, PR-1 first). Nothing built in
this pass — the survey is the deliverable, and PR-1 is a decision about how to
label an existing block rather than a coding task.

## Outcome (fill in later)

## Related Pages

- [[sources/Spider-Software-Flag-Pole-Infographic]] — the source that prompted this
- [[analyses/Open-Backlog]] — B-92, B-93 and the B-19 prior
- [[concepts/High-Tight-Flag]] — the rare extreme of the family
- [[analyses/Dashboard-UI-Roadmap]] — the M1–M4 spine this sits beside
