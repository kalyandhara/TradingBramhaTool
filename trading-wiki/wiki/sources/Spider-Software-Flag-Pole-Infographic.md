---
title: "Infographic — Spider Software: Trading Continuations with Flag & Pole"
category: source
tags: [flag-and-pole, bull-flag, bear-flag, continuation, measured-move, infographic, spider-software, b-92, b-93]
timeframe: swing
created: 2026-09-17
updated: 2026-09-17
sources: 1
related:
  - concepts/High-Tight-Flag.md
  - concepts/Falling-Wedge.md
  - analyses/Pattern-Reporting-Enhancement-Roadmap.md
  - analyses/Open-Backlog.md
---

# Infographic — Spider Software: Trading Continuations with Flag & Pole

## Metadata

- **Publisher:** Spider Software (charting vendor)
- **Type:** Promotional infographic, supplied by the owner 2026-09-17
- **Bias:** Symmetric — presents the bull and bear cases side by side
- **Provenance:** Vendor marketing card. No data, no sample, no hit rate claimed.
  Unlike [[sources/Spider-Software-VWAP-EMA-Infographic]] it makes **no numeric
  claim at all**, so there is nothing here to falsify — it is a *specification*,
  not a result. That is the right way to read it.

## Key Takeaways

1. **Flag & Pole (bullish):** a strong upward move forms a **vertical pole**,
   then a **small downward consolidation** shaped as a **channel, wedge or
   triangle** — the flag.
2. **Inverted Flag & Pole (bearish):** the exact mirror — a strong downward pole,
   then a **small upward consolidation**.
3. **The plan geometry, which is the whole content of the card:**
   - **Entry** — the break of the flag boundary, in the pole's direction.
   - **Stop loss** — the opposite flag boundary (below the flag on a long,
     above it on a short).
   - **Profit target** — the **pole height projected from the breakout**. Both
     panels draw the target arrow as the same length as the pole arrow.
4. The flag is explicitly allowed to be **any of three shapes** — channel, wedge
   or triangle. The pattern is defined by the *sequence* (impulse → shallow
   counter-trend pause → resumption), not by the flag's exact geometry.

## Detailed Notes

The card is a **measured-move continuation** template. What distinguishes it from
a generic breakout is that **all three plan levels are derived from the pattern's
own geometry** — none is a parameter someone picked. That is unusually
falsifiable for a vendor card: the target is not "a good risk-reward", it is the
pole height, and the stop is not "a sensible distance", it is the flag's far
boundary.

No pole-steepness threshold, flag-depth cap, volume condition, or maximum flag
duration is given. Those are exactly the parameters a detector has to choose, and
choosing them is where a "flag" either stays rare and meaningful or degenerates
into "any pullback in an uptrend".

## Contradictions with Existing Wiki

**None** — and that is worth stating explicitly, because the card contains no
claim to contradict. It is a construction spec, not a finding.

Two things on this desk **qualify** it rather than contradict it:

- **[[analyses/Open-Backlog#B-19]]: 0 of 41 scanners stable after costs.** Any new
  continuation detector inherits that prior. Building it is justified by
  *coverage* (a named absence), not by expected edge.
- **The nearest relative here is rare to the point of being unmeasurable.**
  `scan_high_tight_flag` was one of **three scanners B-19 could not score for too
  few signals**. That is an argument *for* the general version, not against it —
  see below.

## Validation Against What Ships — 2026-09-17

| The card specifies | The desk has | Gap |
|---|---|---|
| Bullish pole + flag | `High Tight Flag` — **one extreme variant** (pole ≥90% in ~8 weeks, flag ≤25%) | the **general** bull flag is absent |
| **Inverted** (bearish) flag & pole | — | **entirely absent** |
| Flag as channel / wedge / triangle | `Falling Wedge` (a reversal read), `VCP Coiling` | no flag-shaped consolidation *after a pole* |
| Entry at flag break | HTF emits **no entry** | absent |
| Stop at the far flag boundary | HTF emits **no stop** | absent |
| Target = pole height projected | HTF emits **no target** | absent |
| Draw it on the chart | `falling_wedge`, `vcp`, `roundbottom`, `harmonic` overlays exist | **no flag/pole overlay** |

> [!key-insight] The card's whole content is the plan, and that is exactly what this desk's scanners mostly do not emit
> `scan_high_tight_flag` returns `pattern_type`, `tags`, `reasons` and `score` —
> **and nothing else**. No entry, no stop, no target.
>
> It is not alone. Measured across 60 nifty500 names on 2026-09-17: **31 scanners
> fired, and only 7 of them emitted a full `entry`/`stop`/`target`.** Twenty-four
> did not, including `Structural Breakout`, `VCP Coiling`, `Stage 2 Uptrend`,
> `Pullback Entry`, `Darvas Box`, `Momentum Continuation` and `Near Pivot`.
>
> So the card's real contribution is not "here is a pattern you lack" — it is a
> reminder that **a detected pattern without levels is a notification, not a
> plan**, and that this desk's own `_simulate_plan` harness can only score the
> seven that carry one.

## Actionable Insights

- **[[analyses/Open-Backlog#B-92]]** — build the general Flag & Pole detector,
  **both directions**, emitting the card's three levels. The bear side is the
  larger absence.
- **[[analyses/Pattern-Reporting-Enhancement-Roadmap]]** — a pattern reporting
  page already exists (two, in fact), so this is scoped as an enhancement
  roadmap rather than a new page. Its P0 finding: Strategy Hub's "Chart Patterns"
  table is **20 hardcoded rows of August StockEdge detections**, not a live report.

## Pages Updated

- [[analyses/Open-Backlog]] — B-92, B-93
- [[analyses/Pattern-Reporting-Enhancement-Roadmap]] — new
- [[concepts/High-Tight-Flag]] — positioned as the extreme case of a family
