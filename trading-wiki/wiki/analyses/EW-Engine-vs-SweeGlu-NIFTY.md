---
title: "Our EW engines vs a discretionary count on NIFTY — and our two engines disagree with each other first"
category: analysis
tags: [elliott-wave, nifty, comparison, engine-audit, wxy, nested-degrees, internal-contradiction, measured]
timeframe: position
created: 2026-08-09
updated: 2026-08-09
sources: 1
related:
  - sources/SweeGlu-EW-NIFTY-Chart3-2026-08-05.md
  - concepts/Elliott-Wave.md
  - strategies/EW-Wave5-Catch.md
  - strategies/EW-Flat-Bottom-Breakout.md
  - analyses/Backtest-Harness.md
---

# Analysis: EW engines vs SweeGlu on NIFTY — 2026-08-09

**Ask:** ingest the SweeGlu NIFTY chart, mirror-compare against our own chart tool, find the gap asymmetry in the wave projection, and say whether we run a fundamentally different algorithm.

Both runnable engines were **actually run** on NIFTY for this — `ew_module.py` on daily bars and `elliott_wave.js` (the chart tool's engine, via node) on the same 3-day bars the source chart uses. A **third** engine exists in [pmax.pine](tools/pmax.pine) (Pine, not runnable here) and is covered under point 2 of the conclusion — checking it changed one of my findings.

## Thesis

Yes, fundamentally different — but that is the second finding. **The first is that our two engines disagree with each other**, so "our answer" was not a well-defined thing to compare against until now.

## The three reads, same instrument, overlapping data

| | **SweeGlu** (discretionary) | **`ew_module.py`** (daily) | **`elliott_wave.js`** (3D, chart tool) |
|---|---|---|---|
| Current label | (y) of (b) of (x) of (B or X) of (iv) of Major (3) | **W2** of an impulse | **C of an expanded-flat**, complete |
| Degrees tracked | **6, nested** | 1 | 1 (+ its parent impulse) |
| Counts emitted | **1** global count + an explicit alternate | 1 | **18 impulses + 18 correctives** |
| Next move | up to 26,773–27,864, **then down to ~22,300** | **up**, W3 primary **31,097** | correction already complete |
| Key invalidation | below the 22,879–23,078 shelf | **21,744** (W1 start) | **23,606** (wave-B low) |
| Confidence | none stated | 70/100 | max 59/100, median 40 |

`ew_module.py` detail: W1 = 21,743.65 → 26,373.20 (4,629.55 points), W2 low 23,606.30 (59.8% retrace), Wave-3 targets **31,097 (45%) · 35,726 (30%) · 28,236 (15%) · 40,356 (10%)**, note *"watch for W3 launch above 26,373.2"*.

`elliott_wave.js` detail: active structure 5:23,805 → A:24,367 → B:23,606 → C:24,774, expanded-flat, complete. C targets 23,954 / 24,168 / 24,516 — **all already exceeded** by the 24,571 close.

## The gap asymmetry, concretely

> [!key-insight] Nothing we produce lands anywhere near their target band
> Their zone is **26,773–27,864**. Our full Wave-3 target set is 28,236 / 31,097 / 35,726 / 40,356. **Not one of them falls inside the band.** The nearest, 28,236, is the *15%-weighted minimum* case and sits ~370 points **above** their ceiling. Our primary (45%) target of 31,097 is **3,233 points — 11.6% — above their upper bound.**
>
> This is not a disagreement about magnitude. It is two models whose output ranges barely intersect.

**Direction diverges after the near term.** Both readings are up over the next few months — but ours is up *because* a Wave 3 is starting (target 31,097, no ceiling nearby), theirs is up *because* a corrective (b) is finishing before reversing to 22,300. The same next three months, opposite meanings, opposite exits.

**The one genuine convergence is the 23,000 shelf.** Three methods, three routes, one neighbourhood:
- `ew_module.py`: W2 low **23,606** — the level whose loss reshapes the count
- `elliott_wave.js`: invalidation **23,606** — wave-B low, "Wave C negated below"
- SweeGlu: support shelf **22,879–23,078** (78.6% / 61.8% retracements)

That both our engines land on the *identical* 23,606 pivot from different logic, and the discretionary count draws its shelf 500–700 points below it, is the most useful thing in this comparison. **It is the level all three agree decides something.**

**Their bear case does not invalidate our bull case, which is its own asymmetry.** Their terminal (X) at ~22,300 is *above* our stop of 21,744. So NIFTY could complete their entire projected decline without formally breaking our count — our W2 low would simply be re-marked lower and the count re-labelled. Two models that appear opposed are not actually mutually exclusive at the invalidation level, which means **watching for one to be "proved wrong" will not resolve them.**

## Evidence Against — read our own engines critically first

> [!warning] Our two engines contradict each other, and one contradicts itself
> **Engine vs engine:** `ew_module.py` says *W2 of a large impulse, next stop 31,097*. `elliott_wave.js` says *an expanded-flat correction just completed, targets already met, invalidation 23,606*. Those are not two views of one structure; they are different structures. The dashboard surfaces an "EW" chip from the Python side while the chart draws the JS side — **so the same page can show two incompatible counts**, which is the `detect_bullish_rsi_divergence` split all over again.
>
> **And inside the Python engine:** it returns `wave_pos: W2` alongside `owl_signal: "W3-past"`. The pivot structure says Wave 3 has not begun; the OWL histogram says its peak has already passed. `ew_summary_row` prints both, unreconciled.

**Our engine's own confidence says its NIFTY count is weak.** On 3D bars the JS engine found 18 impulses with a **median score of 40 and a maximum of 59** out of 100, and flagged **14 of 18 as diagonal** (Wave 4 overlapping Wave 1). The highest-scoring structure it found is a *bearish* 5-wave in Jan 2026. A tool reporting 78% marginal structures and a best score under 60 is telling you it has no strong count here — which is a reason to distrust our 31,097, not just theirs.

**Resolution is not the explanation.** Running `ew_module.py` across 1D / 2D / 3D returned the **identical** count each time (W2, 21,744→26,373, W2 low 23,606, primary 31,097); only 4D shifted slightly (W2 low 23,070, 71.3% retrace, confidence 60). So the disagreement with SweeGlu is methodological, not an artefact of them using 3-day bars.

**Bug found while doing this:** `ew_module.analyze_ew` **raises `TypeError` on weekly bars** (NoneType passed to a format string) — the timeframe a position-degree count would most naturally use.

## Conclusion — do we run a hugely different algorithm?

Yes, in five specific senses, all verifiable in the source:

1. **Impulse-first vs correction-first.** Both our engines *search for* 1-2-3-4-5 and treat A-B-C as an afterthought: `detectCorrectives` iterates over already-found impulses and labels the pivots that follow. SweeGlu's entire chart is corrective, with the impulse (Major 3) off-screen as context.
2. **Single-degree vs six-deep — with one nuance found late, and it matters.** There is a **third** EW implementation: [pmax.pine](tools/pmax.pine)'s v2 engine, which maps a 9-position cycle and *alternates* impulse and corrective cycles, appending prime marks (`'`, `''`, `'''`) for repeats. So we are not purely impulse-only. **But its corrective branch emits `(a) (ax) (ay) (b) (c) (az) (ax) (d) (e)` — an ABCDE triangle, not a WXY combination** (`f_waveLabel`, line 196). A triangle is one corrective pattern; WXY is two or three patterns *joined by X waves*, which is exactly what SweeGlu's Ⓦ/Ⓧ and (w)(x)(y) sequences are. So the conclusion survives — **no engine here can express a WXY combination** — but the accurate reason is "none implements combinations", not "none has corrective labels".

> [!contradiction] The wiki documents WXY support for pmax that the code does not have
> [[concepts/Elliott-Wave]] line 72 and [[sources/PMax-Optimization-Pine]] both state pmax's corrective cycles are labelled **`W, w1, x1, X, Y, y1, z1, XX, Z`** — unmistakably WXY vocabulary. `tools/pmax.pine` actually emits **`(a)(ax)(ay)(b)(c)(az)(ax)(d)(e)`**. The WXY string appears **only in those two markdown files and nowhere in any source file.**
>
> Most likely the original TradingView script had it and our port simplified to a triangle, with the docs written from the source rather than the port. Either way it is the **fourth documented-but-not-coded gap found this week**, after the order-block selection rule, the volume-profile HVN/LVN read, and the evening-star gap requirement. That recurrence is itself the finding: **this repo's pages describe upstream sources more faithfully than they describe its own code.**
3. **Many local counts vs one global count.** The JS engine deliberately resumes scanning after each Wave 5, producing a non-overlapping chain — 18 counts across two years, roughly one per six weeks. SweeGlu maintains a single hierarchy over the entire window.
4. **One answer vs an explicit alternate.** Their title says "(B or X)" — two live labels for one wave. Our engines return a single structure with a score; there is no alternate-count mechanism to hold both.
5. **Scored vs argued.** We emit 0–100 confidence and a diagonal flag. They emit a narrative whose support is internal consistency. Neither is self-validating — but only one of them tells you when it is unsure, and on NIFTY ours is saying it is.

**None of this makes either count right.** No Elliott projection in this repo — ours or theirs — has ever been scored against outcomes. [[analyses/Backtest-Harness]] has never run on EW output, and the SweeGlu chart carries no track record. The honest status is **two unvalidated models that disagree, plus a third (our own JS engine) that disagrees with both.**

## Action Taken / Plan

- ✅ Both engines run on NIFTY; numbers above are outputs, not descriptions.
- ✅ Confirmed the disagreement is methodological, not a timeframe artefact (identical count on 1D/2D/3D).
- ⏭ **Reconcile the two engines, or declare one canonical.** A dashboard that can show a Python "W2" chip beside a JS "expanded-flat complete" overlay is worse than having one engine. This is the highest-value fix here.
- ⏭ **Reconcile `wave_pos` against `owl_signal` inside `ew_module.py`**, or state on the panel that they are independent reads that can conflict.
- ⏭ **Fix the weekly `TypeError`.**
- ⏭ **Score the target band.** Their 26,773–27,864 by Oct–Nov 2026 then 22,300 is precise and dated; our 31,097 is precise and undated. Both can be checked later — record the outcome here.
- ⏭ Nested-corrective (WXY) support is a real capability gap, but **should not be built before EW output is measured at all** — same ordering argument as FA-2 before FA-3.

## Outcome (fill in later)

## Related Pages
- [[sources/SweeGlu-EW-NIFTY-Chart3-2026-08-05]] — the chart
- [[concepts/Elliott-Wave]] — the doctrine both engines implement
- [[analyses/Backtest-Harness]] — where an EW score would have to come from
