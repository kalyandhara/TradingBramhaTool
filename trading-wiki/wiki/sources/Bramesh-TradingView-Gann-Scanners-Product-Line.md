---
title: "Bramesh Tech Analysis — the TradingView Gann scanner product line (5 paid Pine scanners)"
category: source
type: source
source_type: commercial product page (paid subscription, closed-source Pine)
author: Bramesh Bhandari (Bramesh Tech Analysis)
url: https://brameshtechanalysis.com/tradingview-gann-scanners/
fetched: 2026-09-18
tags: [gann, scanners, pine-script, tradingview, commercial, closed-source, no-backtest, pivots, multi-timeframe, opening-range, product-page]
related: [sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18, concepts/Gann-Angles-And-Trend-Change-Levels, concepts/CPR-Central-Pivot-Range, concepts/Multi-Timeframe-Analysis, concepts/Support-Resistance, analyses/Open-Backlog]
created: 2026-09-18
updated: 2026-09-18
sources: 0
---

# Bramesh Tech Analysis — TradingView Gann scanner product line

Same author as [[sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18]], read the day
after, to answer one question: **is there anything worth taking out of the Gann scanners?**

**Verdict: nothing worth buying, three ideas worth stealing.** Ingested as a *column-and-
construct inventory*, exactly the way
[[sources/ScreeningMantis-Price-Volume-Sector-Rotation-2026-09-09]] was — not as evidence.

## The product line

| Scanner | ₹/month | What it is |
|---|---|---|
| **Brahmand Levels: Professional Market Matrix** | 6,666 | D/W/M/Q/Y "equilibrium" sync; 180°/360°/540°/720° extensions; a 0.125-increment micro grid; anchored rolling VWAP; "Strait Buy/Sell" around the pivot |
| **Gann Trend Engine Scanner (v6)** | 4,999 | filters names within **0.5%** of "Gann Precision Zones"; layers named Institutional Floor (**= the 200 EMA**), Gann Level 1, Gann Level 2, momentum zones |
| **Gann Levels Scanner** | 4,444 | "triple-layer vibration detection" off **square and cube numbers** → Swing Levels / Gravity Points / Momentum Zones; 0.5% threshold |
| **Gann TC & SAP Scanner** | 4,444 | annual / monthly / SAP "time-cycle averages" as a value zone; 4 SMA/EMA toggles; a **drift table** (absolute + % distance to level); fresh-signal alerts on bar close |
| **Dhruva Drishti: Monthly Breakout Terminal** | 3,777 | anchors to a **fixed January high/low**; states FRESH BUY / FRESH SELL / NEAR BUY / NEAR SELL |

**Total ₹24,330/month — ₹2.92 lakh/year for the set.**

## What is missing, across all five

**No backtest. No win rate. No sample size. No losing example.** Five products, zero
evidence, and the only quantitative claims on the page are *prices*. Every scanner is
**closed-source Pine**, so the construction cannot be inspected either — which is the
same finding as the author's daily letter, but harder: there, a level's scaling was
undisclosed; here it is undisclosed **and** behind a subscription.

Disclaimer carried on every product: *"merely for educational purposes and are not
recommendations or tips."*

> [!warning] Every scanner is capped at 40 symbols
> That is the product's binding constraint — and it is one this desk has already beaten.
> B-92 ran across **248 names**; the scanner hub covers the cash universe. A 40-name cap
> is a Pine platform limit, not a design choice, and nothing here should inherit it.

## What is not worth anything

* **"Vibration", square/cube numbers, 180°/360°/540°/720° extensions.** Unfalsifiable as
  sold: no anchor rule, no scaling, no construction. Same verdict as
  [[concepts/Gann-Angles-And-Trend-Change-Levels]] — *a level you cannot derive is a level
  you cannot backtest*, and paying for it does not change that.
* **"Institutional Floor"** is the **200 EMA**, renamed. The page says so itself.
* **"Time-cycle averages"** is a moving average with a longer lookback.
* **FRESH vs NEAR state labels** — this is the *"how long has this been true"* idea, and
  it is **already shipped here as B-63b**. This desk's version is strictly better: it
  prints the **age** (`ema_cross_age`, `bo_date`, the RS-rank walk) rather than a
  two-state flag. Their 0.5% proximity band is also looser than `row_metrics.PIVOT_NEAR`
  at **0.15%**.
* **The drift table** (distance to level, absolute and %) — the arithmetic a `pivot_zone`
  label exists to remove.

## The three ideas worth taking — and none of them is a Gann idea

### 1. Higher-timeframe pivots (→ B-96)

`row_metrics.pivot_levels()` **already accepts any frame** — its own docstring says
*"Feed it a weekly-resampled frame to get weekly pivots."* `timeframe_board.py` already
resamples daily bars to `ME` / `2QE` / `YE`, exactly and from one download.

**And the only two call sites in the entire toolchain are `pivot_d` and `pivot_w`**
(`row_metrics.py:510-511`, verified by grep across `tools/`). Monthly, quarterly and
yearly pivot zones are a **composition of two things already built**, with no new data,
no new arithmetic and no new download. Brahmand charges ₹6,666/month for the idea of
looking at more than one timeframe's equilibrium.

### 2. Whether those timeframes agree — scored (→ B-97)

Brahmand's one non-mystical construct is *syncing* equilibrium across horizons. This desk
already emits `pivot_d` and `pivot_w` side by side and **nothing has ever scored whether
they agree.**

That is measurable **today**, with no build at all — and the prior says it matters:
**B-42r found `pivot_len` 5 and 15 agreed on `state` only 29.6% of the time**, with 17.6%
of names reading *opposite directions*. Knowing the daily/weekly agreement rate is
information worth having **before** B-96 adds three more timeframes that may disagree with
each other and with the chart.

### 3. A calendar-anchored reference level (→ B-98)

Dhruva Drishti's "fixed January high/low" is a **yearly opening-range breakout** under a
Sanskrit name. Stripped of the branding it is the **only construct on this page that is
fully specified, reproducible, and measurable on cached daily history today** — an anchor
rule ("the January range"), a state ("above / below / inside"), and an event ("first close
outside").

Nothing in `tools/` holds a calendar anchor: no `opening_range`, no year-open reference.
It is also the natural partner for **B-4 / B-12**, where *anchor choice* is the unsolved
subjective half of Anchored VWAP — **a calendar anchor needs no UI and no judgement.**

## Contradictions with existing wiki

**None.** Nothing here contradicts an existing claim; the Gann material is undefined
rather than wrong, and the three usable constructs were simply absent.

## Provenance tier

**Low for evidence, useful for vocabulary.** Named author and a live URL, but it is a
**sales page** — every performance-adjacent claim is commercially motivated and none is
supported. Its value here is as a **catalogue of constructs to check against our own**,
which is precisely what produced B-96 / B-97 / B-98, and two of those three came from
noticing something *this desk already had and was not using*.
