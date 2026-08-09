---
title: "Candlestick Patterns"
category: concept
tags: [candlestick, reversal, continuation, patterns, price-action, psychology, evening-star, doji]
created: 2026-06-19
updated: 2026-08-08
sources: 3
related:
  - concepts/Sakata-Method.md
  - concepts/Support-Resistance.md
  - strategies/Candlestick-Filtering.md
  - strategies/Supply-Demand-Zone-Trading.md
  - concepts/Order-Blocks.md
  - sources/Litchfield-Morris-Candlestick-Charting-Explained-2006.md
  - sources/Forthius-Reversal-Scanner-Pine.md
  - sources/Fingrad-Trading-Infographics-Collection.md
---

# Candlestick Patterns

## Definition
Japanese candlestick patterns are short-term price formations (1–6 bars) that encode the psychology of buyers and sellers through the relationship of open, high, low, and close prices. Each candle body represents the open-to-close range; shadows represent intraday extremes that were rejected.

**Rule #1: Identify the trend first.** A bullish reversal pattern requires a prior downtrend. A bearish reversal requires a prior uptrend. Without trend context, all pattern signals are meaningless.

---

## Candle Anatomy

| Component | Meaning |
|-----------|---------|
| Long white/green body | Bulls dominated; strong close above open |
| Long black/red body | Bears dominated; strong close below open |
| Long lower shadow | Bears initially pushed price down; bulls recovered |
| Long upper shadow | Bulls pushed high; bears rejected the move |
| No shadows (Marubozu) | Complete control open-to-close; no intraday reversal |
| Small body / Doji | Open ≈ close; indecision; power depends on prior trend |

**Long vs Short:** Relative to the most recent 5–10 bars. Context-dependent, not absolute.

---

## Yin (Bearish) and Yang (Bullish) Lines — 9 Basic Types

1. Long white (yang)
2. Long black (yin)
3. Short white
4. Short black
5. Marubozu white (no shadows)
6. Marubozu black
7. Spinning top (small body, long shadows)
8. Doji (open = close)
9. Long-legged doji / Gravestone doji / Dragonfly doji

---

## Reversal Patterns

### Single-Bar Patterns

| Pattern | Setup | Signal |
|---------|-------|--------|
| **Hammer** | Long lower shadow ≥ 2× body; small/no upper shadow | Bullish reversal from downtrend |
| **Hanging Man** | Same shape as hammer | Bearish reversal from uptrend |
| **Inverted Hammer** | Long upper shadow; small body at bottom of range | Bullish reversal (requires confirmation next day) |
| **Shooting Star** | Long upper shadow; small body; gap up at open | Bearish reversal from uptrend |
| **Dragonfly Doji** | Open = close at high; long lower shadow | Bullish reversal |
| **Gravestone Doji** | Open = close at low; long upper shadow | Bearish reversal |
| **Belt Hold (Yang/Yin)** | Open at extreme; no shadow on open side; strong body | Reversal in direction of body color |

### Two-Bar Patterns

| Pattern | Structure | Signal |
|---------|-----------|--------|
| **Engulfing (Bullish)** | Small bearish bar + large bullish bar that engulfs body | Strong bullish reversal |
| **Engulfing (Bearish)** | Small bullish bar + large bearish bar engulfs body | Strong bearish reversal |
| **Harami (Bullish)** | Large bearish bar + small body inside previous body | Bearish momentum slowing |
| **Harami (Bearish)** | Large bullish bar + small body inside | Bullish momentum slowing |
| **Harami Cross** | Harami where second bar is a doji | Stronger indecision signal |
| **Piercing Line** | Gap-down open then close > 50% into prior black body | Bullish reversal |
| **Dark Cloud Cover** | Gap-up open then close < 50% into prior white body | Bearish reversal |
| **Meeting Lines** | Two opposite bars close at same price | Possible reversal |
| **Tweezers (Top/Bottom)** | Same high or same low on consecutive days | Momentum exhaustion |

### Three-Bar Patterns

| Pattern | Structure | Signal |
|---------|-----------|--------|
| **Morning Star** | Large black → small body gap lower → large white > 50% into black | Strong bullish reversal |
| **Evening Star** | Large white → small body gap higher → large black > 50% into white | Strong bearish reversal — **see deep-dive below** |
| **Doji Star (Morning/Evening)** | Star bar is a doji | Stronger than regular star — **see deep-dive below** |
| **Abandoned Baby** | Large body → doji gaps completely away from both sides → large reversal body | Rare; very strong reversal |
| **Three White Soldiers** | 3 consecutive long white bodies; each opens inside prior body; closes near high | Strong bullish reversal (after downtrend) or trend exhaustion (in uptrend) |
| **Three Black Crows** | 3 consecutive long black bodies | Strong bearish reversal |
| **Upside Gap Two Crows** | White body → gap-up small black → larger black that closes gap | Bearish reversal |
| **Unique Three River Bottom** | Three-bar bullish reversal; third closes black but above second low | Bullish reversal |

---

## Deep-Dive: Evening Doji Star (2026-08-08)

Expanded because this is the highest-rated *bearish* three-bar pattern in the data below, and because the repo contains **three mutually inconsistent implementations of it**. Mirror-image of the Morning Doji Star throughout.

### Geometry (strict / sourced definition)
1. **Candle 1** — a long white body in an established uptrend. Trend context is mandatory (Rule #1); the same three shapes mid-range are noise.
2. **Candle 2 (the star)** — a small body **that gaps above candle 1's body**. When that small body is a *doji* (open ≈ close), it is an Evening **Doji** Star — rated stronger than the plain Evening Star because the indecision is unambiguous.
3. **Candle 3** — a long black body closing **below the 50% midpoint of candle 1's body**. This is the confirmation; without it there is no pattern, only a stalled advance.

Psychology: buyer dominance (1) → sudden loss of momentum at a new high (2) → sellers taking back more than half the advance (3).

### Location gate — the pattern is a trigger, not a setup
Per Litchfield via [[strategies/Candlestick-Filtering]], the pattern only earns a trade **inside a pre-identified structural zone**: a supply zone ([[strategies/Supply-Demand-Zone-Trading]]), a bearish [[concepts/Order-Blocks|order block]], or established resistance ([[concepts/Support-Resistance]]) — ideally with RSI 55–65 as the presignal. That page's bearish recipe already names this pattern explicitly.

### Trade mechanics
- **Entry**: short on the break below the pattern's low (or at the close of candle 3).
- **Stop**: above the star's high — the tightest invalidation the structure offers.
- **Target**: next support / S&D level, or the measured move; assess at the **2-day horizon**, the statistically strongest window per Morris.

> [!contradiction] Does the star have to gap? Our sources say yes; the retail version says no; our code says three different things
> **Gap required (sourced):** [[sources/Litchfield-Morris-Candlestick-Charting-Explained-2006]] defines the pattern as "3-bar; **middle bar gaps away** (small body/doji), third bar confirms" — and the classic Abandoned Baby is precisely the extreme case where the doji gaps clear of *both* neighbours. The three-bar table above has always said "gap higher".
>
> **Gap not required (retail):** a widely-circulated infographic (user-supplied, 2026-08-08) specifies only "a tiny Doji at the top" and shows no gap in its diagram. Dropping the gap requirement materially loosens the pattern — far more signals, each weaker. This is the same strict-vs-loose split as the [[concepts/Fair-Value-Gap]] mitigation spectrum, and it should be a **parameter, not a hard-coded choice**.
>
> **What the repo actually does — three ways, none matching the page:**
> - [`pmax.pine:282`](tools/pmax.pine:282) requires the gap (`low[1] > high[2]`) ✓, but also requires the star to be **green** (`close[1] > open[1]`), which can reject the doji variant outright; applies **no small-body test at all**, so a large candle passes as the "star"; and demands `close < open[2]`, far stricter than the documented 50%-midpoint rule.
> - [`scan_candlestick`](tools/scanner_templates.py:2948) does not detect it — **bullish patterns only** (see Examples below).
> - [`is_morning_star()`](tools/scanner_templates.py:2988), the bullish mirror that *is* implemented, checks **no gap** and does **not** require the middle bar to be a doji — so the repo's one shipped star detector silently uses the loose definition.
>
> **Unresolved:** which definition produced the 72% figure below. See the provenance note in Statistical Reliability — it cannot be settled from any source currently in this wiki.

---

## Continuation Patterns

### Two-Bar

| Pattern | Signal |
|---------|--------|
| **Separating Lines (Ikichigaisen)** | Same open, opposite colors; confirms trend resumption after one-bar contra move |
| **On Neck Line** | Second bar closes at low of first; bearish continuation |
| **In Neck Line** | Second bar closes slightly into first body; bearish continuation |
| **Thrusting Line** | Closes below midpoint of prior bar; bearish continuation |

### Three-Bar

| Pattern | Signal |
|---------|--------|
| **Upside/Downside Tasuki Gap** | Gap maintained; partial fill via contra bar; gap hold = continuation |
| **Side-by-Side White Lines** | Two same-color bars at same level; bullish continuation |
| **Upside/Downside Gap Three Method** | Gap → two small contra bars → gap still intact | continuation |

### Four+ Bar

| Pattern | Signal |
|---------|--------|
| **Rising Three Methods** | Long white → 3 small black inside range → long white above; strongest bullish continuation |
| **Falling Three Methods** | Long black → 3 small white inside range → long black below; strongest bearish continuation |
| **Mat Hold** | Variant of three methods with gap preserved through consolidation |
| **Three-Line Strike** | 3 bars + a 4th that engulfs all three; implies exhaustion pause then resumption |

---

## Statistical Reliability (Morris, 2006 — 7,275 stocks, 13+ years, 14.6M days)

- Average %Win across all patterns: **41–64%**
- Only **5 patterns** exceed 59% win rate
- Best prediction horizon: **2 days after pattern** → ranked #1 vs 14 technical indicators
- At 1-day horizon: ranked 5th
- **Key implication:** Candle patterns alone provide a modest edge; filtering with a second indicator is required for consistent outperformance

### Bulkowski's Top-10 — a second dataset (2026-07-19)

A ranked list attributed to Thomas Bulkowski, where % is how often the pattern resolves in the listed direction. **The direction is frequently the opposite of the name** — the single biggest lesson here.

> [!warning] Provenance is one step weaker than "Encyclopedia of Candlestick Charts" implies (corrected 2026-08-08)
> These figures did **not** come from Bulkowski's book. The wiki's actual source is a **screenshot of a FINGRAD infographic that credits Bulkowski** ([[sources/Fingrad-Trading-Infographics-Collection]], image 16). The Encyclopedia itself has never been ingested here. Consequences, which matter for anything built on these numbers:
> - **No pattern definitions accompany the percentages.** We cannot tell whether the 72% Evening Star was measured on the gapped (strict) or gapless (loose) definition — so that figure **cannot be transferred to a detector** until the primary source is checked. Quoting it against a loose implementation would be measuring one pattern and citing another.
> - No sample size, universe, date range, holding period, or definition of "resolves" is recorded.
> - **Open item:** ingest the primary source (or another with published methodology) before these numbers are used to justify or weight an implementation.

| Pattern | Behaves as | Accuracy |
|---------|-----------|----------|
| **Bearish** Three-Line Strike | Bullish **Reversal** | 84% |
| Three Black Crows | Bearish Reversal | 78% |
| Evening Star | Bearish Reversal | 72% |
| Abandoned Baby | Bullish Reversal | 70% |
| Two Black Gapping | Bearish Continuation | 68% |
| **Bullish** Three-Line Strike | Bearish **Reversal** | 65% |
| Inverted Hammer | Bearish Continuation | 65% |
| Bearish Breakaway | Bearish Reversal | 63% |
| Matching Low | Bearish Continuation | 61% |
| Upside Tasuki Gap | Bullish Continuation | 57% |

- **Names lie.** A *bearish* three-line strike acts *bullish* 84% of the time; a *bullish* three-line strike acts *bearish* 65%. Trade the measured behavior, not the label.
- These figures reflect frequency-of-direction in Bulkowski's sample, not expectancy — a high-hit-rate pattern can still lose money if the adverse moves are large. Consistent with the Morris finding: use candles as a filtered input, never alone.

---

## How to Use

1. **Establish trend** (EMA is simplest: price above/below 10–21 day EMA)
2. **Identify a pre-signal condition** in a second indicator (RSI near oversold, price at S/R zone, MACD diverging)
3. **Wait for candle pattern confirmation** within the pre-signal zone
4. **Measure reliability**: long shadows, volume expansion, gap from prior bar all increase signal strength
5. **Target 2-day horizon** for initial profit assessment; manage with trailing stop

---

## Common Mistakes
- Trading reversal patterns mid-trend (no prior trend context)
- Treating doji as a signal without trend exhaustion (doji in the middle of a trend = noise)
- Ignoring volume — high-volume confirmation dramatically improves reliability
- Over-relying on pattern alone without a filter
- Using candle patterns on intraday data below daily: overnight gap psychology is the core mechanic; intraday bars don't have this

---

## Variants / Parameters
- **Intraday application:** authors note Japanese tradition firmly places candlestick analysis on daily data; the overnight sentiment shift between close and open is the psychological driver; 10-minute candles don't carry this
- **Open price unavailability:** if open is unavailable, previous close substitutes; this eliminates some patterns (Inverted Hammer, Dark Cloud Cover, Kicking, etc.)
- **CandleVolume/CandlePower:** body width proportional to volume; visually confirms volume-backed moves

---

## Examples in This Wiki (2026-08-08, updated 2026-08-09)

### Python — the bearish mirror, shipped 2026-08-09
[`scan_bearish_reversal_candle`](tools/scanner_templates.py:3043) ("Bearish Reversal Candle", category **Risk**) closes the asymmetry below. Detects **Evening Doji Star · Evening Star · Three Black Crows · Dark Cloud Cover · Bearish Engulfing · Shooting Star**, reporting the strictest that fires. Three properties, each tracing to a decision on this page:

- **`require_gap` is a parameter** (default = the sourced strict reading), not a hard-coded rule — the resolution recorded in the contradiction callout above.
- **Trend context is evaluated at the bar the pattern started forming**, never at the current bar (the Forthius anti-lookback rule).
- **The resistance location gate is mandatory** — near a *prior* swing-high pivot or the 60-bar high. (First implementation had a real bug here: a star is itself a local high, so scanning the full window let every pattern qualify as "near a pivot" and the gate rejected nothing. The pivot search now excludes the pattern's own bars.)

Base scores are ordered by **geometric strictness**, deliberately *not* by the accuracy percentages above — those carry no definitions and cannot be attached to an implementation.

> [!key-insight] Measured base rate: the gap switch is near-irrelevant in aggregate and decisive for the stars
> 2026-08-09, 17 NSE large-caps, 3y daily, **11,628 bar-observations**:
>
> | Pattern | Strict (gap required) | Loose (no gap) |
> |---|---|---|
> | **All** | **303 — 2.61% of bars** | **320 — 2.75%** |
> | Shooting Star | 158 | 157 |
> | Bearish Engulfing | 99 | 93 |
> | Dark Cloud Cover | 30 | 30 |
> | Three Black Crows | 9 | 9 |
> | Evening Star | 5 | **23** |
> | Evening Doji Star | **2** | **8** |
>
> The gap requirement changes the total by 5.6% but **quadruples both star counts** — the aggregate hides it because Shooting Star and Bearish Engulfing dominate either way. (The small dips in those two under the loose rule are the scanner correctly preferring the higher-strictness star on the same bar.)
>
> **Operational consequence: Evening Doji Star is too rare to matter on its own** — 2 hits in 11,628 bar-observations strict, roughly one per 8.5 stock-years. The infographic presents it as a workhorse setup; on this universe it is a curiosity, and the risk flag earns its keep through the commoner shapes. Anyone waiting specifically for this pattern will wait years.
>
> **This is frequency, not edge.** Whether a hit predicts anything is unmeasured until it goes through [[analyses/Backtest-Harness]].

### Python — the bullish side (unchanged)
[`scan_candlestick`](tools/scanner_templates.py:2948) ("Candlestick Patterns", category Entry) fires on the latest bar for **Morning Star (70) · Bullish Engulfing (62) · Piercing Line (55) · Hammer (52)**, preferring formations at/below EMA20 with volume confirmation. Its own docstring holds the right principle: *"a candlestick is a trigger, not a system: score stays modest."*

Its `is_morning_star()` still checks **no gap** and does not require the middle bar to be a doji — the loose reading, and now inconsistent with the bearish mirror's strict default. Worth reconciling, but it changes a shipped detector's hit rate, so it should be measured rather than simply flipped.

> [!key-insight] Until 2026-08-09 the repo implemented the patterns this page had the *least* evidence for
> By the Bulkowski table above, the best-rated candle patterns are **bearish** — Three Black Crows 78%, **Evening Star 72%** — and **none were implemented**, while not one of the four bullish patterns that *were* implemented appears in that top-10 at all. The selection was inverted relative to our own recorded evidence. `scan_bearish_reversal_candle` closes that gap.
>
> It is deliberately **not** a short signal. `RISK_SCANNERS` in [opportunity_hub.py](tools/opportunity_hub.py:228) treats a bearish hit as evidence *against* a shortlisted long, barred from adding confluence — so an Evening Doji Star at resistance on a name about to be bought lands as a risk flag without touching the confluence maths.
>
> Note the asymmetry this leaves standing: the bearish detector is gated on trend-at-formation and a mandatory resistance location; the older bullish one is not. That is a defensible difference (a risk flag should be conservative) but it is a difference, not a design.

### Pine
- [`pmax.pine:282`](tools/pmax.pine:282) — an `eveningStarPattern` used inside `bearPatternConfirm`, diverging from this page three ways (see the contradiction callout above).

### Port target
[[sources/Forthius-Reversal-Scanner-Pine]] detects ~15 patterns **including Morning/Evening Star**, each with a geometry-based quality score rather than a boolean, composited 0–10 and graded A/B/C. Two details worth taking outright:
- **Trend context is evaluated as of when the pattern started forming** (`downCtx[N]`/`upCtx[N]`), not at the current bar — avoiding the lookback bias of confirming the trend *after* the reversal already happened.
- **Same geometry, context flips the label** — one wick/body measurement, then directional gating (Hammer in a downtrend = Hanging Man in an uptrend). Halves the detection code for mirrored patterns.
- Its **RSI divergence** check is ~2 lines of pandas and is still absent from `scanner_templates.py`.

---

## Related Concepts
- [[concepts/Sakata-Method]] — the historical 5-formation system underlying continuation patterns
- [[concepts/Support-Resistance]] — the most effective filter for candle signals (Litchfield's framework)
- [[strategies/Candlestick-Filtering]] — systematic methodology for combining candles with indicators
- [[concepts/Elliott-Wave]] — can provide trend context for candle pattern identification
- [[concepts/RSI]] — common presignal filter; RSI oversold + hammer = high-quality entry

## Sources
- [Litchfield-Morris-Candlestick-Charting-Explained-2006](../sources/Litchfield-Morris-Candlestick-Charting-Explained-2006.md)
- [[sources/Forthius-Reversal-Scanner-Pine]] (2026-07-02) — working Pine implementation detecting ~15 of these patterns with per-pattern geometry-based quality scores
- [[sources/Fingrad-Trading-Infographics-Collection]] (2026-07-19) — Bulkowski top-10 accuracy percentages (name-vs-behavior mismatch). **Screenshot of an infographic crediting Bulkowski, not the Encyclopedia itself** — no definitions or methodology; see the provenance warning above.
- User-supplied **"The Evening Doji Star Pattern"** infographic (in-conversation image, 2026-08-08) — source for the Deep-Dive section's 3-step framing, the sniper-entry location gate, and the entry/stop mechanics. **Provenance: unattributed retail educational graphic**, and it **omits the gap requirement** our book source specifies — credited for the framing, not as authority on the geometry.
