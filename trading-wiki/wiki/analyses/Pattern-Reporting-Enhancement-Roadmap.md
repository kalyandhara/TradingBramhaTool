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
| **PR-1** | **Strategy Hub's pattern table must stop presenting frozen numbers as live.** Either recompute LTP/Move from the price cache, or label the block as a fixed historical sample and drop the computed scoreboard | the only item where the surface currently misleads | small |
| **PR-2** | **Trade-plan coverage as a first-class, visible metric.** Show which scanners carry `entry`/`stop`/`target`; treat a plan as part of a scanner's definition | unlocks R-based scoring for 24 scanners; absence currently invisible | medium |
| **PR-3** | **The Flag & Pole detector, both directions** ([[analyses/Open-Backlog#B-92]]) — emitting the card's three levels | closes a named absence; the bear half is total | medium |
| **PR-4** | **A flag/pole chart overlay**, after PR-3 | `falling_wedge` / `vcp` / `roundbottom` set the precedent; no point drawing before detecting | small |

### PR-1, stated precisely

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
