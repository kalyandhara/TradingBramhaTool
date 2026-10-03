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

> [!note] Status 2026-09-17: every rung is DONE — PR-1, PR-1b, PR-1c, PR-2, PR-3, PR-4.
> The remaining debt is not on this roadmap: **B-92's detector has never been
> measured**, and that is a pre-registration and a run, the same shape as B-56.

| # | Rung | Why it is at this rank | Size |
|---|---|---|---|
| ~~**PR-1**~~ | ~~Strategy Hub's pattern table presents frozen numbers as live~~ — **DONE 2026-09-17**: LTP recomputed from the batched price source, Move % derived, scoreboard reports its denominator | one row was counted on the wrong side of its own scoreboard | done |
| ~~**PR-1b**~~ | ~~"Trading Strategies · Live Counts" is also frozen~~ — **DONE 2026-09-17**: the heading no longer says Live, and the computed "Net" line is gone | the heading was the boldest claim on the page and the one thing never true | done |
| ~~**PR-1c**~~ | ~~"Fundamental Scores · Top Picks" is the third frozen literal~~ — **DONE 2026-09-17**: every number computed from `fundamentals_deep` + `fundamental_score`. The /100 shield was **not** recomputed, because this desk deliberately has no overall score | it printed a 62× PE for a loss-making company | done |
| ~~**PR-2**~~ | ~~Trade-plan coverage as a first-class, visible metric~~ — **DONE 2026-09-17**: censused, surfaced on Scanner Hub, and ratcheted. **14 of 45 observed scanners carry a plan; 31 do not** | the census is the baseline a test now asserts against | done |
| ~~**PR-3**~~ | ~~The Flag & Pole detector, both directions~~ — **DONE 2026-09-17**: `tools/flag_pole.py`, two registered scanners, both carrying a full plan. Registry 46 → 48, plan ratchet 14 → 16 | closed a named absence; the bear half was total | done |
| ~~**PR-4**~~ | ~~A flag/pole chart overlay~~ — **DONE 2026-09-17**: `/api/flag_pole` + an inline overlay drawing the pole, the flag and all three plan levels, both directions | the roadmap is now closed except PR-1c | done |

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

### PR-4 — DONE 2026-09-17, and the roadmap closes

`/api/flag_pole` in `chart_server.py` plus an inline overlay in
`chart_dashboard.html`, modelled on the `falling_wedge` pair. Registered as
**Flag & Pole + measured-move plan (both directions)** under Price Patterns.

**What it draws.** The pole as a thick line sloping the way the thrust went; the
flag as its two boundaries; and the three plan levels as **price lines**, so they
extend to the right edge where a trade would actually be managed — `FP trigger`,
`FP stop` and `FP target`, each with its axis label. A marker reads `FLAG BREAK`
when broken and `FLAG` when not, and a corner card carries the geometry.

**The card says what the target is.** *"Target = pole height projected — a
measured move, **not a forecast**. UNMEASURED."* The same sentence the scanner
card carries, in the place someone would actually act on it.

**Both directions in one response.** The route returns `bull` and `bear`
together. They are mutually exclusive in practice but nothing guarantees it, and
asking the client to choose would put the detector's logic in two places.

> [!key-insight] "No pattern" and "could not look" are different answers
> A frame shorter than `WINDOW + ATR_N` cannot be evaluated at all. Returning a
> bare `null` for it would read as *"there is no flag here"* — a claim the server
> is in no position to make.
>
> The route returns a `note` saying how many bars it needed and how many it got,
> and the overlay prints it on the card instead of drawing nothing. A test pins
> the distinction, because it is the kind that quietly disappears in a refactor.

**Verified on the running chart, not reasoned about.** APARINDS carried a live
bull flag: pole 6.99×ATR over 13 bars, flag 24 bars retracing 46%, volume dried
41%, trigger 18331.36 / stop 16015 / target 23496.42 at R:R 2.23 — all three price
lines visible with their labels, no console errors, and a clean teardown on
toggle-off (series, price lines and card all removed; price lines are removed
through the candle series that owns them, or they survive and stack on the next
draw). The bear path was exercised directly with a synthetic payload, since no
live bear flag existed in the sample at the time: it renders the ▼ arrow, the
mirrored levels and an honest "vol ROSE 20%".

**Four route tests**, including that a real pattern's bar indices arrive as chart
**timestamps** rather than indices — the one transformation this route owns.

### PR-1c — DONE 2026-09-17, and one thing deliberately NOT recomputed

`tools/fundamental_panel.py`. Every number now comes from `fundamentals_deep` +
`fundamental_score` at load: sector, market cap, profit CAGR, PE, the PE band,
LTP and the day change. The six NAMES stay a fixed August watch list — nothing
re-picks them — and the caption says exactly that.

> [!key-insight] The /100 shield was not recomputed, because this desk decided not to have one
> The owner asked to recompute the scores. The honest answer to part of that
> request is **"that number should not exist"**, and the reason is already written
> down in `fundamental_score`'s own docstring:
>
> *"There is no overall /100 here. The dashboard already carries the M1 technical
> Overall Rating, the council verdict, and Setup Intelligence; a fourth number
> badged 'Overall' would be read as a competing master score."*
>
> It emits business quality as a **word** specifically *"so it cannot be mistaken
> for a fourth Overall Rating"*. The frozen block's `🛡 81 /100` is precisely the
> number that decision forbids. **Recomputing it would have meant inventing it.**
>
> So the shield is replaced by the two readings the scorer does produce —
> **business quality** and **entry price**, scored separately. Strictly more
> informative, and the split exists because *"a good business at a bad price is
> the single most common way a fundamentals page misleads."* CRISIL is that case
> today: **GOOD QUALITY 74 at a STRETCHED entry 42**, which one number badged 81
> cannot express. A test pins that no `overall` field can come back under another
> name.

> [!warning] The frozen row printed a PE for a company with no earnings
> **Piramal Pharma's TTM EPS is −2.4** — it is loss-making, so its PE is
> undefined. The frozen literal printed **PE 62.0×** and a **40–95× band**, plus
> a fundamental score of 59/100.
>
> That is worse than the SPLPETRO case PR-1 found. SPLPETRO's number was stale;
> this one was never meaningful at any price. The panel now reads
> **"no PE — not profitable on TTM earnings"**, and `pe_at_year_ends` skips any
> year whose EPS is not positive rather than producing a band point from it.

**Two labels corrected on the way:**
* **"EPS 3Y CAGR" → "Profit CAGR 3Y"**, because `profit_cagr_3y` is what is
  computed. The two differ by dilution, which the same payload measures
  separately. A profit CAGR under an EPS label is a small lie that compounds on
  any name that issued stock.
* **"PE 3Y range" → "PE at N year-ends"**, with N shown. A true range needs EPS
  at every point in time; what exists is EPS at each annual period end. Hyundai
  correctly reports **2** year-ends rather than pretending to four — it listed in
  2024.

**Coverage is on the surface.** Each row shows how many of the scorer's 17 metric
inputs resolved (CRISIL 16/17, Piramal 13/17), so a confident-looking verdict
built on half the inputs cannot pass for a complete one.

**The monolith shrank** 13,881 → 13,784 lines: the ~100-line frozen block became
one call, with the rendering in the module (the B-87 rule). 15 tests.

### PR-1's original statement, kept for the record

The honest minimum is **one caption change and one deletion**: say the block is a
**fixed sample captured in August**, and remove the "N above / M below" footer,
because a scoreboard computed from frozen prices is a claim about outcomes that
nothing is measuring. The better version recomputes LTP from the cache the rest
of the desk already uses, at which point the scoreboard becomes real.

**Do not silently refresh the numbers in place.** Whichever route is taken, the
block should say which it is — the [[analyses/Open-Backlog#B-26]] lesson about
changing what a displayed number means.

### PR-2 — DONE 2026-09-17

`tools/scanner_plans.py` censuses every registered scanner point-in-time, caches
the result as a **committed record**, renders it on the Scanner Hub, and a test
ratchets it.

**The measurement, firmer than the estimate that motivated this rung.** 45
nifty500 names, every 25th bar, 45 of 46 scanners observed:

| state | count |
|---|---|
| **FULL** — every hit carried entry, stop and target | **14** |
| **PARTIAL** — some hits did, some did not | **0** |
| **NONE** — fired, never carried a full plan | **31** |
| **UNSEEN** — never fired; nothing claimed | 1 |

> [!key-insight] PARTIAL came back empty, and that changes the shape of the work
> Every scanner **either always emits a plan or never does**. A plan is a property
> of the SCANNER, not of the individual hit.
>
> So this is **31 scanners to fix, not 31 scattered gaps** — and fixing one fixes
> every hit it will ever produce. It also means the census is cheap to trust: a
> scanner's state will not flicker between runs on sampling luck.

**Four states, because three would lie.** A scanner that never fired has not been
shown to lack a plan. Collapsing `UNSEEN` into `NONE` is the FR-4 mistake —
NOT_CHECKED reading as a verdict — and here it would make that mistake about the
whole registry at once. The surface says so in as many words.

**The ratchet, and the thing that nearly made it decoration.** `MIN_FULL_PLAN_SCANNERS
= 14` may rise freely and may not fall without someone editing the line and saying
why; a second test fails if a scanner is registered but missing from the census,
because otherwise a new planless scanner would simply not appear rather than
lowering the count.

The census first landed in `tools/cache/`, which is **gitignored** — so on any
fresh checkout `load()` returned None and the ratchet **silently skipped**. That is
[[analyses/Open-Backlog#B-87]]'s own lesson in a new costume: a ceiling nothing
asserts against is decoration. It now lives at `tools/scanner_plan_coverage.json`
with an explicit `.gitignore` negation, which also makes it **diffable** — a
scanner losing its plan shows up as a line in a review rather than as a number
nobody re-ran.

**What this unlocks, and what it does not.** `_simulate_plan` walks entry →
stop/target, so those 31 scanners cannot be scored on realised R at all today.
Giving them plans is the follow-up; **this rung only makes the gap visible and
stops it widening.** No scanner gained a plan in this pass, and none should have
— inventing a stop for 31 detectors in one commit is exactly the kind of change
that needs measuring one at a time.

### PR-3 — DONE 2026-09-17

`tools/flag_pole.py` — `detect_flag_pole` plus two registered cards, **Flag &
Pole** and **Inverted Flag & Pole**. Both emit the card's three levels, so the
plan ratchet rose **14 → 16** behind them; the registry is **46 → 48**.

> [!key-insight] The count found a bug that no "does it detect a flag" test would have
> The first `--count` returned **189 patterns and `broken 0`** — not one breakout,
> ever.
>
> The flag boundary was the max high over the whole flag **including the live
> bar**, and the breakout test asked whether that bar's *close* exceeded it. A
> close cannot exceed its own bar's high, so the condition was **unsatisfiable by
> construction**. The detector would have shipped finding flags and never once
> saying one had broken.
>
> Counting first is what caught it, exactly as B-58 intended — and the fix is a
> better rule anyway: the boundary is now formed strictly **before** the bar that
> breaks it, so it does not move under the trade once set. A test pins that the
> trigger is identical in the watch and broken cases.

**The counts, published as promised.** 60 names, every 15th bar, 2,216 evaluated:

| | present | of bars | of symbols | broken out |
|---|---|---|---|---|
| bull | 114 | **5.1%** | 52/60 | 10 (**0.45%** of bars) |
| bear | 74 | **3.3%** | 41/60 | 7 (0.32%) |

**Read those two columns differently.** The pattern being *present* on 5% of bars
is a WATCH state — a flag that has not broken is not a signal. What is actionable
is the **broken-out** rate of **0.45%**, which is selective. Neither number is
"any pullback in an uptrend": the trap named before the build did not open.

**The coverage argument, made concrete.** On the same 45-name plan census,
`High Tight Flag` fired **4** times; `Flag & Pole` fired **66** and the inverted
half **48**. The rare cousin stays registered and unchanged — this does not
replace it — but the family is now measurable, which is the whole justification.
**Justified on coverage, never on edge**: B-19's 0-of-41 stands, and both cards
say UNMEASURED in their own reasons.

**Three parameter decisions, each recorded in the module:**
* **Pole in ATR (≥4× in ≤15 bars), not per cent** — one threshold means one thing
  across a universe of different volatilities.
* **Flag retrace capped at 50%**, the loose end of the classic 38-50% range.
  Tightening it is what made HTF unmeasurable, so it is the one gate deliberately
  left wide.
* **Volume contraction measured, NOT gated.** HTF rejects a rising-volume flag and
  its reasoning is sound — that is distribution into strength — but enforcing it
  costs the signals this detector exists to provide. `vol_contract` is reported so
  a later test can ask whether it matters instead of assuming it. A test pins that
  a rising-volume flag is still detected.

**The bear half is scoped as EXIT / AVOID**, not entry, in the docstring, the
registry description and a test — shorting NSE cash for a swing hold is not
available to most users here.

**What is still owed:** a measurement. The target is the pole height projected and
is labelled a projection rather than a forecast; nothing about either card has
been backtested, and neither votes in confluence.

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
