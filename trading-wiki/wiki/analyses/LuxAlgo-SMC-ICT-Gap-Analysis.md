---
title: "LuxAlgo SMC/ICT concepts vs the desk — gap analysis (2026-10-15)"
category: analysis
tags: [smc, ict, luxalgo, gap-analysis, liquidity-sweep, order-blocks, fvg, unbacktested-prior]
created: 2026-10-15
updated: 2026-10-15
sources: 1
related:
  - analyses/Open-Backlog
  - analyses/Order-Block-Rules-Measured
  - analyses/FVG-FBG-Fibonacci-Chart-Roadmap
  - concepts/ICT-Methodology
  - concepts/Fair-Value-Breaker-FBG
  - concepts/Market-Structure-CHOCH-BOS
---

# LuxAlgo SMC/ICT concepts vs the desk — gap analysis

**Source:** luxalgo.com/library → Concepts → "SMC / ICT", **55 concepts**, every page read 2026-10-15.
Descriptions below are paraphrase, not LuxAlgo text. **Nothing here is built; every
recommendation is an unbacktested prior until it has its own pre-registered measurement.**

## The fact that decides the ranking

This desk has already measured the SMC family harder than most of the concepts on that page
have ever been measured:

| What | Result | Where |
|---|---|---|
| **Liquidity Sweep** (equal-low pool pierced, close back above) | **+0.51% @20d (p=0.005), +0.91% @60d (p=0.002)** net, walk-forward stable — **the desk's best signal** | B-41m |
| …its shipped stop | destroys the edge (−0.06R stopped vs +0.50R time-only) | B-41p |
| "Retrace into a level after a structure break" — ICT Setup (MSS+displacement → OTE → FVG), Order Block Retest, Pullback Entry | **−0.36% / −0.47% / −0.43% @20d** on ~9,000 signals, all negative | B-19 |
| Order-block rules (target ladder, stacked zones, early vs confirmed) | one null, one **inverted**, one undecidable → ladder collapsed, gauge retired | [[analyses/Order-Block-Rules-Measured]] |
| FVG fill rate | gaps are **not** magnets against a width-matched placebo | fvg_fill_study |
| Bullish CHoCH | **no edge**, pipeline-excluded | choch_study |
| Quasimodo (CHoCH geometry) | fails the bar (5,048 events, −0.64%) | B-58 |
| Structure pivot length | scanners (5) vs chart (15) agree on state only **29.6%** — owner decision open | B-42r |

So the ranking rule is: **extend what is measured to work (the sweep), surface state the
reader can use, and do not rebuild more "retrace into a zone" variants** — the family is
measured negative three times over.

A second filter: this is a **daily, NSE cash-equity** desk. Roughly a third of the page is
ICT's New-York-clock intraday machinery for futures/FX (killzones, macros, Silver Bullet,
CBDR/Asian ranges, midnight open, NDOG/NWOG, quarterly theory). It doesn't transfer to EOD bars of
Indian stocks and is out of scope, not a gap.

## Coverage matrix (all 55)

**Legend:** ✅ built · 🟡 partial · ❌ missing · ⛔ out of scope (intraday/futures clock or umbrella term)

### Structure & liquidity
| Concept | Desk today | Status |
|---|---|---|
| Smart Money Concepts (umbrella) | chart group "Smart Money & Structure" + 6 scanners | ✅ |
| BOS / CHoCH / MSS | `detect_bos_choch`, Structure Break Chain overlay, `Bullish CHoCH` scanner (no edge) | ✅ (B-42r open) |
| Displacement | `require_displacement` in ICT Setup; body-ratio in `fvg.js` | ✅ |
| Liquidity pool / Equal highs-lows / BSL / SSL | `detect_liquidity_pools`, chart `liquidity` overlay | ✅ |
| Liquidity sweep | `Liquidity Sweep` (+0.51% @20d) and `Liquidity Sweep Bear` (unmeasured) | ✅ |
| Smart money reversal (sweep → displacement → BOS) | sweep scanner without the BOS confirmation step | 🟡 |
| Change in State of Delivery (CISD) | nothing — body-close over the last opposing run's open | ❌ |
| Draw on liquidity | sweep target = nearest opposing pool; OB target ladder measured **null** (Rule A) | 🟡 |
| Internal vs external range liquidity | nothing | ❌ |
| Inducement (IDM) | nothing | ❌ |
| Premium & discount | `market_structure` labels PREMIUM >70% / DISCOUNT <30% of the swing band | ✅ (not shown on Watchlist) |
| Optimal Trade Entry (62–79%) | ICT Setup + `fibonacci.js` | ✅ (measured negative) |
| PD arrays (umbrella) | OB + FVG + pools | 🟡 |
| HTF liquidity (weekly/monthly pools) | pools are single-timeframe — **deferred gap in B-58** | ❌ |
| Prior day/week/month extremes as pools | D/W/M/Q/Y pivot sides exist (B-96), not as pool levels | 🟡 |
| Trendline liquidity | trendline overlay exists, no "stops behind the line" read | 🟡 |
| SMT divergence | nothing (cross-instrument non-confirmation) | ❌ |
| Low- vs high-resistance liquidity runs | nothing | ❌ (low value) |
| Institutional order flow | narrative term over structure state | ⛔ |
| IPDA & price delivery theory | framework narrative | ⛔ |

### Zones (order blocks and gaps)
| Concept | Desk today | Status |
|---|---|---|
| Bullish/bearish order block, anatomy & refinement | chart `orderblock` + `Order Block Retest` (−0.47%), rules measured | ✅ |
| Mitigation (as a zone *state*) | OB mitigated / violated states | ✅ |
| Mitigation block (failed-swing OB variant) | nothing | ❌ |
| Breaker block / **Inversion FVG** (FBG) | wiki concept + roadmap (FF items), **never built** | 🟡 |
| Reclaimed OB / propulsion block / rejection block | nothing | ❌ |
| Fair value gap | `fvg.js` + `FVG Pullback` scanner | ✅ |
| FVG behaviour rules | size filter + rejection requirement | 🟡 |
| Consequent encroachment (gap / wick 50%) | used inside `fvg_fill_study`, not drawn | 🟡 |
| Implied FVG / volume imbalance / balanced price range / immediate rebalance | nothing | ❌ |
| Opening gap (NSE daily gap) | `gap_pct` column; unfilled-gap levels not tracked | 🟡 |
| Unicorn (breaker + FVG overlap) | needs breakers first | ❌ |
| Standard-deviation projections (range-height multiples) | `projection` overlay is EW/pattern-based | ❌ |

### Models and timing
| Concept | Desk today | Status |
|---|---|---|
| Model 2022 (raid → shift → FVG entry) | ≈ ICT Setup, measured negative | ✅ (negative) |
| Candle Range Theory (C2 sweeps C1's extreme, closes back inside) | nothing, but it is a sweep on a *candle's* range | ❌ — **in the sweep family** |
| Market maker models, Seek & destroy, One-shot-one-kill, AMD / Power of 3, Judas swing | nothing | ⛔ (intraday templates) |
| Killzones, ICT macros, Silver Bullet, session ranges, time anchors, session liquidity, session & weekly profiles, quarterly theory, NDOG, NWOG | nothing | ⛔ (New-York clock, futures) |

**Count:** ✅ 15 · 🟡 12 · ❌ 15 · ⛔ 13.

## Recommendations — ranked

### Worth doing (sweep family first, then visibility)

**1. HTF liquidity pools for the sweep — measure first.** *(the B-58 deferred gap)*
Add weekly equal lows and prior-week / prior-month lows as pool sources in
`detect_liquidity_pools` (`scanner_templates.py`). Pre-register: does a sweep of an
HTF pool beat a sweep of a daily pool on the B-41m panel? This extends the one
signal with an edge instead of re-deriving a negative one.
→ Wires into: `scan_liquidity_sweep`, chart `liquidity` overlay, Scanner Hub card tag.

**2. Candle Range Theory on the weekly candle — measure first.**
CRT is a sweep of the prior candle's range: week 2 trades below week 1's low and
closes back inside. It is mechanical, has no free parameters beyond the timeframe,
and runs on bars the desk already has. Pre-register against `Liquidity Sweep`'s own
forward-return test. If it is a near-subset of the sweep scanner (overlap check first, as with PSAR),
it adds nothing.
→ New detector beside `detect_liquidity_sweep`; Scanner Hub; chart marker.

**3. Confirmation filters on the sweep (smart-money reversal, CISD) — measure as filters, never as stops.**
Test whether "sweep **and** a CISD or BOS within N bars" selects a better subset of
B-41 signals than the sweep alone. Report it as a gate (like B-122's No-Supply study), and
keep the B-41p lesson: no added stop.
→ `scan_liquidity_sweep` option flag; the result decides whether the card shows it.

**4. SMC state columns on the Watchlist and Scanner Hub — plumbing, no edge claim.**
The desk already computes structure state, premium/discount and pools; the
Watchlist shows none of them. Add: *structure* (UP/DOWN/RANGE), *P/D %* in the
live swing band, *nearest unswept SSL / BSL* (distance in ATR), *swept ≤5d* flag.
**Blocked on B-42r**: the column must say which pivot length it uses, or the owner
picks one first (29.6% agreement otherwise makes the column contradict the chart).
→ `row_metrics` / `columns.py` / Watchlist + Scanner Hub; Opportunity Hub card tags.

**5. Breaker / Inversion-FVG overlay — display only, with an "unmeasured" card.**
Already specified in [[concepts/Fair-Value-Breaker-FBG]] and the FF roadmap: a gap
violated by a close flips polarity. Cheap on top of `fvg.js` state. **No scanner**:
it is another retrace-into-a-zone entry, the family measured negative three times.
Draw consequent encroachment (50% lines) on FVG and OB zones in the same pass.
→ `fvg.js` + chart `fvg` overlay; `TRAIL_STATUS`-style status card.

### Worth it only as targets (ties into Risk & Exits step 6)
**6. Standard-deviation projections of the dealing range + prior D/W/M extremes as target levels.**
They are target anchors (geometry and liquidity, in the profit-target taxonomy), not
signals. Tag them, then let the plan scoreboard report reach rates once B-116 is
unblocked. → `fibonacci.js` / `projection` overlay; plan target tags.

### Maybe later
**7. SMT-style divergence against the stock's sector index:** the stock sweeps its low while
the sector index holds its own. This is genuinely new information (cross-instrument), but it
needs sector-index alignment per bar. File as a pre-registered *filter* on the sweep, after 1–3.

**8. NSE opening-gap levels:** track unfilled daily opening gaps as levels. Low priority:
the FVG fill study already found gaps are not magnets. Only worth it if someone wants
the levels on the chart.

### Not recommended
- **More order-block variants** (mitigation, reclaimed, propulsion, rejection blocks) and **Unicorn**:
  more variations on a family measured negative, and the OB rule study already inverted one gauge.
- **FVG micro-variants** (implied FVG, volume imbalance, BPR, immediate rebalance): the parent
  concept's own premise (gaps attract price) measured null on this desk.
- **Re-building OTE / Model 2022**: that is `ICT Setup`, measured −0.36% @20d.
- **All ⛔ session/clock concepts**: they assume an intraday futures/FX clock; the desk is daily NSE cash.
- **Inducement, low/high-resistance runs, IPDA, institutional order flow**: narrative over
  structure the desk already labels; no mechanical definition worth measuring.

## Implementation order
1. Overlap check: weekly CRT vs `Liquidity Sweep` (½ session). If it is not a subset, run the CRT pre-registration. → **B-165**
2. HTF pools pre-registration + build (1–2 sessions). → **B-166**
3. Sweep confirmation filter study, CISD/BOS (1 session). → **B-167**
4. ~~**Owner decision B-42r** → then SMC state columns~~ — **DONE 2026-10-15** (Option C; `smc_state.py`, 5 Watchlist columns).
5. Breaker / IFVG + CE overlay, display-only (1 session). → **B-168**
6. Target tags (rides on Risk & Exits step 6). → **B-169**
7. Later / declined items → **B-170**; housekeeping found along the way → **B-171**.
