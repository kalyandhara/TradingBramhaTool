---
title: "Chart — SweeGlu Elliott Wave, NIFTY 50 3D, 'Chart 3' (2026-08-05)"
category: source
tags: [elliott-wave, nifty, chart, wxy, corrective, nested-degrees, fibonacci, projection, sweeglu]
created: 2026-08-09
updated: 2026-08-09
sources: 1
related:
  - concepts/Elliott-Wave.md
  - analyses/EW-Engine-vs-SweeGlu-NIFTY.md
  - strategies/EW-Wave5-Catch.md
  - sources/EW-Techniques-Simplified-McDowell.md
---

# Chart — SweeGlu Elliott Wave, NIFTY 50 3D, "Chart 3"

## Metadata
- **Author:** Deepak Kumar, "SweeGlu Elliott Wave Analysis"
- **Published:** TradingView chart, 2026-08-05 21:55 UTC+5:30
- **Instrument / timeframe:** NIFTY 50 Index, **3-day (3D) bars**, NSE
- **Price at publication:** 24,624.65 (+0.04%)
- **Ingest trigger:** user supplied it asking for a mirror-comparison against this repo's own EW engines

## Key Takeaways

1. **The label is six degrees deep:** *(y) of (b) of (x) of (B or X) of (iv) of Major (3)*. Read outside-in: a Major wave 3, within it wave (iv), within that a (B or X), within that an (x), within that a (b), within that a (y). Every level below Major (3) is **corrective**.
2. **It carries an explicit alternate count** — "(B or X)" — i.e. the author is openly holding two competing labels for the same wave rather than committing.
3. **Upside target is a band, not a point:** a shaded **26,773–27,864** zone, drawn as the 100.0% and 123.6% Fibonacci projections (26,773.35 and 27,864.60).
4. **The projection is up, then down.** A rally from roughly the current level into that band around **Oct–Nov 2026**, labelled (b)/Ⓨ/(c), followed by a decline to **(X) ≈ 22,300** by early 2027.
5. **Downside shelf marked at 22,879–23,078** — the 78.6% and 61.8% retracement levels, shaded grey and touched repeatedly through 2025–26.
6. Prior structure labelled on the chart: **(W)** ≈26,300 (Sep 2024), **Ⓦ** ≈25,700 (May 2025), **Ⓧ** ≈21,900 (Mar 2026), with nested (a)(b)(c) and (w)(x)(y) sequences throughout — i.e. a **WXY combination**, the standard vocabulary for complex corrections.

## Detailed Notes

Levels as drawn:

| Level | Price | Role on the chart |
|---|---|---|
| 123.60% | 27,864.60 | top of the target band |
| 100.00% | 26,773.35 | bottom of the target band |
| — | ~24,625 | price at publication |
| 61.80% | 23,078.40 | upper edge of the grey support shelf |
| 78.60% | 22,879.00 | lower edge of the grey support shelf |
| (X) target | ~22,300 | terminal low of the projected decline |

The whole visible structure is corrective. There is no impulsive 1-2-3-4-5 anywhere on the chart — the only impulse referenced is **Major (3)**, which sits above the entire visible window as context.

## Actionable Insights

- **The target band is a falsifiable, dated claim**: NIFTY reaches 26,773–27,864 around Oct–Nov 2026, then turns down to ~22,300. Both the level and the sequence can be scored later.
- **It is the first EW source here that models nested corrective degrees.** Every other EW artefact in this wiki — the [[concepts/Elliott-Wave]] page, `ew_module.py`, `elliott_wave.js` — is impulse-first and single-degree.
- **The 23,000-ish shelf matters to everyone.** Their 22,879–23,078 support band is within a few hundred points of where *both* our engines independently place their key pivot — see the analysis.

## Contradictions with Existing Wiki

Extensive, and they are structural rather than a difference of opinion about one wave. Full treatment in **[[analyses/EW-Engine-vs-SweeGlu-NIFTY]]**. In brief:

- **Direction of the next major move is opposite.** `ew_module.py` reads NIFTY as **W2 of an impulse** with a primary Wave-3 target of **31,097**; this chart reads the same tape as a **corrective (b)** capped at 27,864 and then reversing to 22,300.
- **Neither of our engines produces any target inside their 26,773–27,864 band.** Our nearest is 28,236 — a 15%-weighted Wave-3 minimum sitting ~370 points *above* their ceiling.
- **Our tooling cannot express this label at all.** Zero occurrences of WXY, double-three, triple-three, combination, degree or nesting in either engine; `detectCorrectives` only labels A-B-C hanging off a detected impulse, so a correction inside a correction has no code path.

## Pages Updated
- [[analyses/EW-Engine-vs-SweeGlu-NIFTY]] — **created**, the mirror comparison
- [[concepts/Elliott-Wave]] — capability gap recorded
- `wiki/index.md`, `wiki/log.md`
- **`wiki/overview.md` untouched** — a third-party projection is not this wiki's market thesis.
