---
title: "Renko Charts"
category: concept
family: chart-type
tags: [renko, chart-type, brick-size, time-independent, atr, noise-filtering, measured-null]
created: 2026-08-29
updated: 2026-08-29
sources: 1
related: [concepts/Point-and-Figure-Charts, concepts/SuperTrend, concepts/Capital-Management-Methods, concepts/Support-Resistance, concepts/Multi-Timeframe-Analysis, sources/YT-Devendra-Renko-Intelligence-Commodities]
---

# Renko Charts

Time-independent chart type. A new **brick** is drawn only when price closes a full
*brick size* beyond the previous brick's extreme; a reversal needs **two** bricks in the
opposite direction (the standard construction). Time and volume are discarded — a Renko
chart can print six bricks in ten minutes and none for two days.

Sibling of [[concepts/Point-and-Figure-Charts]]: both replace the time axis with a price
grid. P&F uses columns of X/O with a box size + reversal amount; Renko uses equal bricks
with a fixed 2-brick reversal. Renko is the simpler of the two and maps directly onto an
OHLC series, which is why it is easier to compute inside an existing charting stack.

## Why anyone uses it

Candles are sampled by **time**, and price is not delivered on a schedule. On a quiet,
gapping session a 30-minute bar confirms a move only after it has happened, while a
15-minute bar never develops enough range to be decisive. Renko samples by **price**, so
a sideways market simply stops producing bricks instead of producing noisy ones.

What you give up: volume, time, intrabar structure, and the ability to know the current
brick is final — the in-progress brick can un-print.

## Brick size — the only parameter that matters

Everything about a Renko chart follows from the brick size. Three ways to set it:

| method | definition | problem |
|---|---|---|
| **Fixed points** | e.g. "50 points on Nifty" | Meaningless across instruments and across volatility regimes; a 2019 brick is the wrong size in 2026. |
| **% of price** | e.g. 0.5% of close | Scale-free, but ignores that two ₹1,000 stocks can differ 4× in realised range. |
| **ATR-derived** | brick = a function of ATR | Self-adjusting to the instrument *and* the regime. The version below is the one worth testing. |

### The session-ATR rule (from [[sources/YT-Devendra-Renko-Intelligence-Commodities]])

```
brick = ATR(5) measured on a SESSION-LENGTH bar / (execution bars per session)
      = the average range of one bar on the timeframe you actually trade
```

"Session-length bar" means one bar per trading day for that instrument: **~6 h** for NSE
equities/indices (09:15–15:30), **~14 h** for MCX commodities (09:00–23:30). So the rule
reads: *measure a typical day's range over the last week, then divide it into the number
of bars your execution timeframe carves that day into.*

Worked, with the numbers recomputed (the source's own arithmetic is inconsistent — see
that page's correction table):

| instrument | session bar | ATR(5) | execution TF | bars/session | **brick** |
|---|---|---|---|---|---|
| Nifty | 6 h | 100 pts | 30-min | 12 | **8.3** |
| Nifty | 6 h | 100 pts | 15-min | 24 | **4.2** |
| Gold (MCX) | 14 h | 1500 pts | 30-min | 28 | **53.6** |

The appeal is that brick size then carries a **unit**: one brick ≈ one execution-bar's
worth of movement, which makes it a natural stop distance and a natural position-sizing
input (cf. the ATR-stop reasoning in [[concepts/Capital-Management-Methods]]).

**Measured 2026-08-29 — see the status section below.** The sizing convention being
principled said nothing about whether signals built on it beat a baseline, and they do not.

## Common mistakes

- **"Renko removes lag."** It does not; it converts *time* lag into *price* lag. No brick
  exists until price has travelled a full brick, so the brick size **is** the lag. Moving
  to a 1-second chart changes nothing — the brick still needs its full move. The real
  claim is that price-lag is better behaved than time-lag, which is defensible.
- **Backtesting on Renko bricks directly.** Bricks are not bars: they have no timestamps
  you can fill against, the last brick repaints, and brick sequences compress multiple
  real bars into one. A Renko rule must be tested against the **underlying OHLC series**,
  entering on the bar the brick completes. Naïve Renko backtests are the single most
  common source of fake equity curves in this chart type.
- **Re-optimising brick size per symbol.** With a free brick-size parameter, almost any
  Renko system can be fit to any history. Derive it (ATR rule above) and leave it alone.
- **Reading volume off a Renko chart.** There isn't any — bricks aggregate arbitrary
  amounts of it.

## Renko + SuperTrend

The natural pairing, and the basis of the "AI-Renko SuperTrend" product in the source:
run [[concepts/SuperTrend]] with its ATR band derived from the same brick size, so trend
flips are quantised to brick multiples rather than to raw price. This repo already ships
an adaptive SuperTrend (`tools/supertrend_ai.js`, factor chosen by k-means over
performance) — a Renko-brick variant would be a sibling of it, not a replacement, and the
two should be measured against each other before either is promoted.

## Status in this repo — BUILT, and the flip came back a NULL

**Shipped 2026-08-29** (B-43): `tools/renko.js` (`window.RENKO`, pure compute),
a rendering plug in `chart_dashboard.html` (`renko` indicator), `renko_backtest.js`
(flip emitter) and `renko_backtest.py` (scorer).

### Three design decisions that made it measurable rather than decorative

1. **Close-based bricks, not high/low.** A brick completed by a *close* has an
   unambiguous bar and is fillable at that bar's next open. A brick completed intrabar by
   a wick completes at a price nobody can prove they'd have received. Wick Renko is
   prettier and untestable.
2. **Causal brick sizing, in epochs.** The obvious `brick = ATR(5)` is a look-ahead trap:
   ATR moves every bar, and rebuilding the grid from the *latest* ATR repaints all of
   history — which is what most charting platforms' ATR-Renko does, fine for looking at,
   fatal for measuring. Here the brick is re-derived only every `epochBars` (default 20)
   from ATR over bars **strictly before** that point, then held fixed. A single fixed
   brick would be worse: a brick sized for RELIANCE at ₹232 is noise at ₹1,316.
3. **Structure on candles, never instead of them.** `pane.bars` is untouched, so every
   other indicator still sees real OHLC — the same rule Heikin Ashi follows here.
   The chart draws the grid as a two-colour **staircase**, flip arrows, and one labelled
   price line carrying the live state (`Renko ▼ 1br · brick 20.27 (1.58%)`).

Engine invariant verified in-browser on live data: across 470 bars the grid never sat
more than `reversal × brick` against the trend without flipping — **zero violations**,
once each bar is checked against *its own epoch's* brick rather than the final one.

### The measured result — no edge in the flip

Scored through the **same harness** as the EVWMA/VWAP MACD cross (its `event_edge` /
`strategy_equity` now take an injected signal source, so there is one scorer and several
engines), on the identical basket: 23 liquid NSE names + NIFTY/BANKNIFTY, ~19 years,
18,595 baseline bars, next-open fills.

```
baseline mean fwd %:  5d +0.31  10d +0.72  20d +1.54  60d +5.05

leg                  n        5d edge (p)     10d edge (p)     20d edge (p)     60d edge (p)
flip_up (LONG)    1862      -0.06 (0.62)     -0.08 (0.60)     -0.04 (0.85)     -0.77 (0.07)
flip_dn (SHORT)   1871      +0.11 (0.35)     +0.05 (0.76)     -0.19 (0.40)     -1.00 (0.01)*
```

The long leg is **negative at every horizon** — entering on an up-flip does slightly
*worse* than being in the market at random. The one starred cell (flip_dn at 60d) should
not be read as a finding: 8 cells were tested, so ~0.4 are expected below p=0.05 by
chance, and it sits at the longest horizon where overlapping windows inflate Welch most —
the exact artefact measured in [[concepts/Gamma-Exposure-GEX]], where a rotation test cut
a p=0.031 down to 0.32.

Strategy equity, zero costs, median across the 23 names:

| variant | median return | beat buy&hold |
|---|---|---|
| stop-and-reverse | **−39%** | **0 / 23** |
| long-only (down-flip = go flat) | +267% | 1 / 23 |
| buy & hold | +827% | — |

At 20 bps/flip: −56% and +223%.

### The sharpest way to state it

Renko **did** deliver the noise reduction it promises — on the same names it fires about
**40% less often** than the EVWMA cross (RELIANCE 202 flips vs 320; TITAN 202 vs 328).
It removed signals. It did not make the surviving ones better: the edge went from
"indistinguishable from zero" to "indistinguishable from zero, slightly negative on the
long leg", and stop-and-reverse beat buy-and-hold **0 times in 23** against the EVWMA
cross's 1. Fewer decisions of the same quality is a real ergonomic benefit and not an
edge, and the two should never be confused.

The neutral-to-skeptical prior recorded in [[analyses/Open-Backlog]] was right: a
*rendering* choice that also removed noise from the *signal* would have been a free lunch.

### Status of the chart feature

Kept, and deliberately labelled **FLIP↑ / FLIP↓** rather than BUY/SELL, with no wording
implying a trigger anywhere in the UI. It is a structure and state read — where the grid
is, how big a brick is, how far the run has travelled — which is what the measurement
supports and nothing more.

## Sources

- [[sources/YT-Devendra-Renko-Intelligence-Commodities]] (2026-08-24 podcast) — the
  session-ATR brick rule; everything performance-related in it is unmeasured and
  commercially motivated.
- **To ingest:** Prashant Shah's published work on Renko / Point-and-Figure for Indian
  markets — a checkable source for the same material.
