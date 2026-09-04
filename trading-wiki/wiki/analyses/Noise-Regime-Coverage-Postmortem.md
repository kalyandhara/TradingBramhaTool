---
title: "Post-Mortem: Noise, Regime Blindness & the Small-Cap Coverage Gap"
category: analysis
tags: [post-mortem, opportunity-hub, scanner-hub, regime, small-cap, multibagger, noise-reduction, behavioral, roadmap]
timeframe: milestone-plan
created: 2026-08-23
updated: 2026-08-23
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/Backtest-Harness.md
  - concepts/Market-Sentiment-Index.md
---

# Post-Mortem: Noise, Regime Blindness & the Small-Cap Coverage Gap

End-to-end review triggered by a behavioral observation: **too many stocks and
too many pages, in a market where analytics work least (bear regimes), lead to
worse decisions.** Three theses from the owner, checked against the code
2026-08-23. All three hold.

## Finding 1 — The universe is structurally large-cap; small/micro-caps are unreachable

`opportunity_daily.run()` builds its universe with
`sp.fetch_bhavcopy_top_volume(universe_size)` — **top N by TRADED VALUE**. Traded
value ≈ price × volume ≈ liquidity ≈ market cap, so the funnel only ever sees the
**top liquid layer**. Every scanner then runs on that same set. The owner's read
is exactly right: *the scanners are the best eyes on the top of the market; the
hidden small/micro-cap multibaggers never enter the field of view.*

The concept is not absent — `multibagger_candidates.py` is a genuine small/mid-cap
screen (MCap < ₹20,000 Cr, ROCE > 15, OPM > 10, D/E < 1, 3-yr sales > 15%, fresh
FII+DII buying) — **but it is a standalone, screener.in-cookie-gated entry under
"Other Screeners"**, not part of the daily funnel, its persistence, or its ranking.
And it predates the free NSE promoter/pledge work: its own header says pledge is
"not reliably scrapable" — which is **no longer true** (we now read promoter % and
pledge % free from NSE, see [[analyses/Open-Backlog]] red-flags work).

## Finding 2 — Regime is described, never acted on

`_market_context()` computes a real regime — **RISK-ON / MIXED / RISK-OFF** from
Nifty vs its 50/200 SMA — and writes a `market_verdict` string. But the regime is
**purely descriptive**: it does not shrink the shortlist, does not suppress long
setups in RISK-OFF, does not elevate the bearish `RISK_SCANNERS`, does not raise
the quality bar. In a bear tape the tool still emits **~100 long candidates** with
the same confidence as in a bull tape. The one good instinct already present: when
no sector has positive momentum the funnel says *"nothing is going up"* rather than
ranking the least-bad — that reflex should become the whole posture, not a footnote.

This is the crux of the behavioral complaint: **the tool's output volume is
regime-invariant, but the edge of technical/fundamental signals is not.**

## Finding 3 — The surface is wide enough to cause paralysis

- **38 scanners** — 6 Momentum, 2 Trend, **13 Entry, 12 Pattern**, 5 Risk. Half of
  them are Entry/Pattern variants that read overlapping facts. The confluence
  **family** de-dup fixes the *scoring* (correlated scanners are capped), but the
  **UI still presents all 38 as independent choices**.
- **~21 pages across 6 nav groups.** A first-time decision ("what do I do today?")
  has too many doors.

More options do not add edge here; they add the cognitive load that, under stress
(a falling market), converts into over-trading — the exact failure mode named.

## Recommended changes (prioritized) → backlog B-32…B-36

Each is framed the way this vault requires — **a build with a measurable claim**,
not a vibe. Nothing below is asserted as edge until it is measured.

1. **B-32 · Make the regime PRESCRIPTIVE (highest leverage).** RISK-OFF caps the
   shortlist hard (or to zero longs) and elevates defensive/RISK scanners; MIXED
   tightens thresholds; RISK-ON runs full. *Measure first:* does following the
   shortlist in RISK-OFF actually underperform RISK-ON out-of-sample (the premise)?
   If yes, the throttle is earned; the same [[analyses/Backtest-Harness]] machinery
   scores it. "In a bear market the best trade is fewer trades" is a hypothesis with
   a p-value, not a slogan.
2. **B-33 · Conviction-sized shortlist.** Replace fixed `top_n=100` with a
   confluence+rating **quality gate**, so the list shrinks by itself when breadth is
   thin. *Measure:* forward return of the gated top-quality subset vs the dropped
   tail — if the tail carries no edge, cutting it is free noise reduction.
3. **B-34 · Small/micro-cap "hidden treasures" lane.** A FREE small-cap universe
   (NSE Smallcap-250 / Microcap-250 constituents — no screener.in) run through the
   `multibagger_candidates` logic **plus the now-free NSE promoter/pledge checks**,
   surfaced as a deliberately SMALL, high-conviction lane. *Measure:* coverage
   (names outside the top-value universe) and a forward hit-rate of the criteria vs
   a small-cap benchmark. Directly closes Finding 1.
4. **B-35 · Collapse 38 scanners into family "lenses" in the UI.** Default the
   Scanner Hub to a curated core; long tail behind "advanced". *Check:* no unique
   hit is lost (every family still reachable) — a verifiable invariant, not a taste
   call.
5. **B-36 · Regime "posture" header + page consolidation.** A one-line posture on the
   Opportunity Hub ("Bear regime — capital preservation; N high-conviction names")
   and fewer nav doors. The anti-over-trading nudge that makes Findings 2 & 3 felt.

## Sequencing & honesty

B-32 and B-34 are the two that change the tool's *behavior*, not just its chrome —
do those first, each gated on its own measurement. B-35/B-36 are low-risk UI and can
land in parallel. **Distinct from [[analyses/Open-Backlog]] B-31** (regime-adaptive
confluence *weights*, deliberately parked): B-32 throttles *output volume* by regime,
which is simpler, testable now, and does not require the unvalidated weight-learning
B-31 depends on.
