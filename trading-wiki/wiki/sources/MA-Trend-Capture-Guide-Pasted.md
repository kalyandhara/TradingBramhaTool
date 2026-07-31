---
title: "Article (pasted) — How to Capture Strong Trends with Moving Averages"
category: source
tags: [education, moving-average, trend, ema, sma, low-yield-ingest]
created: 2026-07-30
updated: 2026-07-30
sources: 1
related: [concepts/EMA, sources/SwingEdge-Learn-Indicators-Deep-Dive, concepts/Multi-Timeframe-Analysis]
---

# Source — "How to Capture Strong Trends with Moving Averages – A Complete Guide" (pasted)

## Metadata
- **Source type**: Long-form article, **pasted into the session** — no file, no URL captured
- **Author / origin**: **Unverified.** It was pasted immediately after a request to capture
  `swingedge.info`, and its content overlaps heavily with the `/learn/moving-averages-deep-dive`
  lesson already ingested in [[sources/SwingEdge-Learn-Indicators-Deep-Dive]] (2026-06-22).
  That is an inference from adjacency, **not** an attribution — the text carries no byline,
  and its register ("Happy trading, and remember…") reads like a generated summary rather
  than the original page. Recorded as its own source so a wrong attribution is not baked
  into the SwingEdge page.
- **Ingested**: 2026-07-30

## Key Takeaways
1. **Mostly already known.** Ten sections, seven "techniques" — price-vs-MA, slope,
   multiple-MA comparison, price crossovers, MA-MA crossovers, dynamic S/R, timeframe
   selection. Six of the seven were already on [[concepts/EMA]]; the repo's **MA Bias**
   chart overlay implements a stricter four-tier version of the whole thing.
2. **The one real contribution: the named no-trade zone.** Requiring *both* fast-above-slow
   **and** price-above-fast, and explicitly naming the state where only the first holds
   (`MA20 > MA200` but price < `MA20`) as a stand-aside condition. Most write-ups stop at
   the crossover and never name the in-between state — which is exactly where whipsaws are
   manufactured. Merged into [[concepts/EMA]].
3. **Two minor gap-fills:** the **100-period** MA (missing from our period table, sits
   between the 50 and the 200) and **MA-as-a-zone** — plot a pair, or offset a single MA by
   a small percentage, and treat the band as support/resistance rather than a line.
4. **One claim rejected on methodological grounds** — the 45° slope rule, see Contradictions.
5. **One risk claim to resist** — "when 10>20>50>100>200 all align, increase position size."

## Detailed Notes
The article's framing is that moving averages are only "lagging" if you use them the
standard way, and that their real job is to **measure trend strength** and decide whether
to be aggressive, flat, or short — not to generate crossover signals. That reframe is
already the wiki's position ([[concepts/EMA]] Common Mistakes: "treating MA crosses as
entries — they are lagging confirmations"), and matches the "regime, not threshold" meta-
pattern recorded across the whole SwingEdge indicator cluster.

Suggested pairings: **20/200 for swing, 50/200 for positional**, with the fast MA's slope
read as the strength gauge and the MA pair used as a dynamic support/resistance zone.
Higher-timeframe confirmation (weekly 20/200 under a daily signal) is recommended —
already covered by [[concepts/Multi-Timeframe-Analysis]].

## Actionable Insights
- Add the **no-trade-zone** cell to how the MA Bias card is read: our overlay already
  computes both conditions, but the *third row of the matrix* is the useful teaching
  artifact, and it is now written down on [[concepts/EMA]].
- The **100-period MA** is a cheap addition wherever the 50 is too twitchy and the 200 too
  slow — no code change made, noted as available.
- Nothing here justifies a new scanner or detector. This was a **low-yield ingest**, and
  saying so is more useful than manufacturing work from it.

## Contradictions with Existing Wiki
- **"Fast MA slope > 45° = strong trend", via `atan(slope) × 180/π`.** Rejected. An angle
  in degrees is **not a property of the data**: it depends on the chart's pixel aspect
  ratio, zoom level, and linear-vs-log price axis. The same series reads 20° or 70° by
  dragging the window edge, and a ₹50 stock cannot share a threshold with a ₹5,000 stock.
  The repo already does this correctly by normalising against **ATR** (`extAtr`,
  `braidAtr` in `MA_BIAS_OPTS`, [chart_dashboard.html](tools/chart_dashboard.html)); the
  scale-free alternatives are % change per bar or ATR-normalised slope. The *idea* — slope
  encodes strength, and a flattening fast MA warns before price does — was already on
  [[concepts/EMA]] since 2026-06-22 and stands.
- **"All MAs stacked → increase position size."** Conflicts with
  [[analyses/Kalyan-Trading-Philosophy]] and [[strategies/Crash-Proof-3-Filter-System]],
  where size follows **market regime and risk-per-trade**, not indicator alignment. A full
  stack is a reason to take the trade, not to enlarge it.

## Pages Updated
- [[concepts/EMA]] — new section "The Two-Condition Gate & the No-Trade Zone", the 100-period
  and MA-as-zone additions, the 45°-slope warning callout, and the sizing caution.
  Frontmatter `sources:` also corrected (read 1 while three were listed).
- This source page.
