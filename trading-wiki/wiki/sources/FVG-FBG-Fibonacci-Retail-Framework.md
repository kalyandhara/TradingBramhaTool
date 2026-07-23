---
title: "Framework — FVG + FBG + Fibonacci, Retail-Friendly Actionable Rules"
category: source
tags: [framework, fvg, fbg, breaker-block, fibonacci, fpv, liquidity, displacement, smc, checklist, confluence]
created: 2026-07-22
updated: 2026-07-22
sources: 1
related:
  - concepts/Fair-Value-Gap.md
  - concepts/Fair-Value-Breaker-FBG.md
  - concepts/Fibonacci-Retracement.md
  - concepts/FPV-Flow-Price-Volume-Ownership.md
  - analyses/FVG-FBG-Fibonacci-Chart-Roadmap.md
---

# Source — FVG + FBG + Fibonacci Retail Framework

## Metadata
- **Type:** Written decision framework, pasted by the user 2026-07-22. Two parts: (1) actionable FVG/FBG rules + retail checklist + FPV confirmation; (2) the role of Fibonacci as confluence with FVG/FBG.
- **Author bias:** SMC/ICT retail-education school. Neutral on direction; the whole framework is about *filtering* trades, not calling one.
- **Status:** Educational reference, not a registered-advisor call. Every item is a filter/confluence, not a standalone buy signal.

## Key Takeaways
1. **FVG = continuation tool; FBG = reversal tool.** An FVG is a 3-candle imbalance traded on the retrace *with* the displacement; an FBG is a *failed* FVG whose broken boundary flips into a reversal zone.
2. **The retail checklist is a gate stack.** Liquidity sweep · displacement · structure alignment · volume · clear imbalance · no news in 10 min · not inside HTF chop. **If 2+ are NO → skip** (claimed to avoid "70% of bad trades"). Same veto-stack shape as the crash-proof market-health filter.
3. **Fibonacci is optional confluence, not required** — but three mappings turn FVG/FBG into mechanical rules:
   - **FVG midpoint ≈ Fib 0.50** → best continuation entry.
   - **Breaker retest = Fib 0.618–0.705** → best reversal entry (0.382-only = weak, expect continuation).
   - **Fib 1.272 / 1.618 / 2.0** extensions → mechanical take-profit zones.
4. **Fib 0.618 is the "reaction test"** for FVG strength: a clean rejection there = strong FVG; slicing through it on weak volume = the imbalance is failing (and may be about to become an FBG).
5. **FPV (here: Flow of Price, Volume)** confirms: Price↑+Vol↑ = strong long FVG; a break of the FVG on **high** volume = strong breaker, on **low** volume = fake breaker.
6. **HTF for bias, LTF for entries** — 5m scalp / 15m intraday / 1H swing / 4H-Daily bias.

## Detailed Notes

### FVG actionable rules
- **Valid FVG:** 3-candle sequence, middle = displacement, gap not filled by candle 3 (bull: C1 low > C3 high; bear: C1 high < C3 low).
- **Trade only when:** structure supports direction · liquidity sweep happened before the FVG · price returns to the zone · volume confirms displacement.
- **Entry:** 50% of the FVG (optimal) or full zone (aggressive); SL below/above the sweep or displacement candle.
- **Exit:** TP1 return to origin · TP2 next liquidity pool · TP3 opposite-side FVG.
- **Do NOT trade:** no displacement · no sweep · inside HTF FVG (chop) · during news · low-volume sessions.

### FBG actionable rules
- **Becomes an FBG when:** price returns to the FVG, breaks the opposite side, **closes beyond** the boundary, original direction fails.
- **Entry:** wait for the breaker retest, enter at midpoint (or Fib 0.618–0.705), SL beyond the block, volume confirmation required.
- **Exit:** TP1 previous swing · TP2 opposite liquidity · TP3 HTF imbalance.

### Fibonacci role (part 2 of the source)
- FVG + Fib = *precision entry* (0.50 midpoint), *strength confirmation* (0.618 reaction test), *target selection* (1.272/1.618/2.0).
- FBG + Fib = *reversal confirmation* (strong = reject at 0.618–0.705 with volume; weak = only 0.382).
- **Stacked confluence** = FVG midpoint + Fib 0.50 + Fib 0.618 + breaker block + liquidity sweep + volume all aligning.

## Actionable Insights
- The chart's [fvg.js](tools/fvg.js) detects **raw 3-candle gaps + size filter only** — it lacks the displacement / liquidity-sweep / rejection gates the framework (and the wiki's own [[concepts/Fair-Value-Gap]]) require. Those richer gates exist in the Python `detect_fvg_pullback()` port but not on the chart.
- **FBG has no implementation** anywhere in the stack — new detector.
- The Fibonacci overlay [fibonacci.js](tools/fibonacci.js) (shipped this session) **already computes 0.5 / 0.618 / 1.272 / 1.618** and already scores confluence against zones — so FVG-zone scoring is a clean extension of an existing mechanism, not new math.

## Contradictions with Existing Wiki
- **Close-through vs wick-through** for the FVG→FBG "break": the wiki already carries this exact tension (Quant close-through lifecycle vs LuxAlgo wick-through) in [[concepts/Fair-Value-Gap]]. Resolved by defining the FBG break on a **close** through the opposite boundary.
- **"FPV" — third definition.** Here FPV = *Flow of Price, Volume* (two components). The prior ingest defined it as *Flow of Price, Volume, **Ownership*** (three), and the Fibonacci overlay uses "FPV" for *projection + volume-profile* confluence. Three incompatible meanings — recorded in [[concepts/FPV-Flow-Price-Volume-Ownership]].

## Pages Created
- [[concepts/Fair-Value-Breaker-FBG]]
- [[analyses/FVG-FBG-Fibonacci-Chart-Roadmap]]

## Pages Updated
- [[concepts/Fair-Value-Gap]] (retail rules + Fib confluence + FPV note), [[concepts/FPV-Flow-Price-Volume-Ownership]] (third-definition flag), [[analyses/Dashboard-UI-Roadmap]] (Phase 2 pointer), [[index]], [[log]]
