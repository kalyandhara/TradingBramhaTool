---
title: "Order Block Rules — Test Design (pre-registered)"
category: analysis
tags: [order-blocks, smc, pre-registration, backtest, b-76, target-selection, stacked-bias, rejection-entry]
created: 2026-09-13
updated: 2026-09-13
sources: 0
related: [analyses/Backtest-Harness, analyses/PCR-Sign-Convention-Pre-Registration, concepts/Order-Blocks, analyses/Open-Backlog]
---

# Order Block Rules — Test Design (pre-registered)

**Written before any forward return has been looked at.** B-76 shipped three
rules onto the Order Block chart overlay in a single session, each chosen from
the conventional SMC playbook rather than from anything this repo has measured.
This fixes the test, the data, the floor, the controls and the decision rule —
including what happens on a null — while the answers are still unknown.

## Why this is not a footnote

[[analyses/Backtest-Harness]] already measured the **Order Block Retest** scanner
at **−0.74% @20d vs baseline** over the 49-name liquid universe: the zone itself
did not beat a coin-flip entry in that tape. B-76 then added three *more* rules on
top of that same detector and drew them on the chart as precise numbers — a TP
price, an SL price, an R:R figure, a `BULLISH 3×` badge. Precision of display is
not evidence, and the overlay currently looks more authoritative than the measured
substrate underneath it.

[[analyses/Open-Backlog#B-44r]] is the standing precedent for what happens next:
GEX shipped on a naive convention, was measured, came out backwards for NSE, and
was retired. These three rules get the same treatment.

## What is being tested

All three live in `scanner_templates.detect_order_blocks` and reach the chart via
`/api/order_blocks`. Each is an **unmeasured prior** in code today.

### Rule A — target selection

A live zone's plan is `entry` = the zone edge price retests, `stop` = just past the
far side, and `target` chosen by a three-step ladder:

1. nearest still-live **opposing zone edge** at least 1R away — the "next major zone"
2. else the **displacement extension** (`ext`, the move that created the zone)
3. else a flat **2R**

**H0:** the three target rules are indistinguishable in R-expectancy.
**H1 (as shipped):** the opposing-zone target beats both fallbacks.

Tested **paired** — same zone, same entry, same stop, only the target varies — so
this isolates the target rule and nothing else.

### Rule B — stacked-zone bias

The `.ob-info` gauge tallies live zones per side, weights `fresh` double, and prints
a direction plus a stack count (`BULLISH 3×`). The claim inherited from the playbook
is that stacked same-direction zones confirm a stronger institutional lean.

**H0:** the lean carries no directional information about forward returns.
**H1 (as shipped):** bullish lean → higher forward return than bearish lean.

Two-sided. The desk does not get to pick a direction after seeing the data — if the
sign comes out inverted, that is a B-44r-shaped finding, not a relabelling
opportunity.

Secondary, **pre-registered as secondary so it cannot be promoted after the fact**:
does the stack count grade monotonically (1× < 2× < 3×+)? A bias gauge whose
headline number does not grade is a gauge printing a number for its own sake.

### Rule C — early rejection entry

Two retest markers now fire per zone: `early` (wick into the zone, close back
outside) and `confirmed` (Pine's cross, after price has left the zone).

**H0:** early and confirmed retests have the same forward return.
**H1 (as shipped):** they are genuinely different entries — early trades earlier
for a worse fill rate.

Note the asymmetry being tested: the *shipped* claim is only that they differ
enough to deserve different glyphs. "Early is better" is **not** the hypothesis and
will not be claimed if it merely appears.

## Method

Follows [[analyses/Backtest-Harness]] conventions exactly, because a measurement
that invents its own protocol cannot be compared to the six scanners already on
that page.

- **Universe / window:** `backtest.LIQUID_50`, 1500 calendar days, daily bars.
- **No look-ahead.** At bar `t` the detector is handed **only `df.iloc[:t+1]`**.
- **Stride 5, and only same-bar events count.** A retest or zone is recorded only
  when its defining bar **is** `t`. Detecting at `t > m` would silently drop events
  on zones that were later violated — survivorship dressed as a signal — because
  the detector's retest pass skips violated zones. Striding therefore costs an
  unbiased 1-in-5 sample and buys correctness; it does not buy speed alone.
- **Entry at the next bar's open** (`t+1`), never the signal bar's close.
- **Rule A entry is a pending limit**, because that is what the plan says: wait up
  to 40 bars for price to reach `entry`, then stop-or-target for up to 60 bars.
  Unfilled plans are counted and reported, never dropped.
- **Pessimistic tie-break:** a bar spanning both stop and target counts as the stop.
- **Direction-aware.** The shipped rules are two-sided, so the simulator is too —
  unlike `backtest._simulate_plan`, which is long-only. Bearish zones are simulated
  short rather than discarded.
- **Baseline = random entry in the same tape**, same timing, same costs.
- **Costs:** reported **gross and net** (`COST_INDIAN`). A rule that only works
  gross has not worked.
- **Significance:** t-test on every headline; **n < 30 ⇒ `thin_sample`**, reported
  as directional-only and never quoted as a headline.

## Decision rule — fixed in advance

| Outcome | Action |
|---|---|
| **A** — opposing-zone target wins, net, significant | keep the ladder; record the measured expectancy |
| **A** — no separation | collapse the ladder to the simplest rule (2R) and say why |
| **A** — a fallback wins | reorder the ladder to match the data |
| **B** — lean predicts, net, significant, and grades | keep the gauge; put the measured number on it |
| **B** — null | the gauge keeps the zone counts but **loses the directional word** — it becomes a census, not a verdict |
| **B** — inverted | retire the gauge, B-44r precedent |
| **C** — early and confirmed differ | keep both glyphs; label which is which in measured terms |
| **C** — no difference | collapse to one marker; two glyphs for one signal is a lie about information content |

**A null on all three is an acceptable and expected outcome.** Per
[[investment-desk-not-trading-system]] framing, a measured null here is calibration
of an overlay the desk reads daily, not a failed feature. What is *not* acceptable
is leaving three unmeasured rules drawing precise numbers on a chart.

## Known limitations, stated before the run

Inherited from the harness and not fixed here: survivorship bias (only names listed
today), one universe, one ~6y mostly-constructive window, no walk-forward, and daily
bars — which cannot resolve whether stop or target filled first within a bar, hence
the pessimistic tie-break. Directional evidence, not a verdict.
