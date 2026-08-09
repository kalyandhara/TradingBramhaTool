---
title: "Volume Profile (POC / Value Area / Delta)"
category: concept
tags: [volume-profile, poc, value-area, vah, val, hvn, lvn, delta, market-profile, order-flow]
created: 2026-07-03
updated: 2026-08-09
sources: 4
related: [concepts/Order-Flow, concepts/Multi-Timeframe-Analysis, concepts/Support-Resistance, concepts/Initial-Balance, concepts/Fair-Value-Gap, concepts/Volume-Analysis, analyses/Backtest-Harness, sources/ForexTester-Volume-Analysis-Guide]
---

# Volume Profile (POC / Value Area / Delta)

## Definition
A histogram of traded volume by *price* (not time): the lookback window's price range is split into rows, and each bar's volume is distributed across the rows its high-low range covers. Where volume clustered, the market found the price "fair" (acceptance); where little traded, price was rejected in transit. Key derived levels:
- **POC (Point of Control)** — the single highest-volume row; the market's consensus fair price for the window.
- **Value Area (VA)** — the rows around the POC enclosing ~70% of total volume; **VAH**/**VAL** are its upper/lower boundaries.
- **HVN / LVN** — high-/low-volume node pockets away from the POC: HVNs act as magnets/support, LVNs as air pockets price crosses quickly.
- **Delta profile** — the same histogram but with each bar's volume *signed* by direction (tick rule `sign(close − close[1])`, or true bid/ask matching when tick data exists): per-row net buying vs selling, i.e. *who* built each node.

## How to Use
- **Acceptance test**: price closing and holding above the POC means the market has re-rated value upward — for a reversal candidate coming off a decline, close above the decline-window's POC is the volume-structure confirmation that the recovery is accepted, not just visited. Above the *entire* VA is stronger still (trading above value).
- **Rejection risk**: price below VAL is trading below value — a recovery that hasn't been accepted by volume yet; expect the VAL/POC band to act as overhead resistance ([[concepts/Support-Resistance]] with mechanically-derived levels).
- **Delta context**: a POC built on positive delta (net buying) marks accumulation; the same node on negative delta marks distribution that must be absorbed. From [[concepts/Order-Flow]]'s footprint logic, applied at daily-screening granularity.
- **Multi-timeframe confluence** (the TradingIQ contribution): compute profiles per timeframe (30m/1h/4h/1D/1W) and read where the POCs/VAs stack — nested value areas agreeing across timeframes mark the levels that matter; [[concepts/Multi-Timeframe-Analysis]] applied to volume structure instead of trend.

### The 80% rule — a testable claim, not a maxim
If price **enters the value area and holds there for two consecutive 30-minute bars**, there is a stated ~**80% probability it traverses the entire VAL→VAH range** ([[sources/ForexTester-Volume-Analysis-Guide]]). The logic: acceptance back inside value implies the prior excursion was rejected, and value tends to be explored fully before it is left again.

Recorded as a **claim with a number attached, from a vendor blog with no data behind it**. Unlike most volume maxims it is fully specified — entry condition, target, and probability — so it can be measured rather than believed. [[analyses/Backtest-Harness]] can test it directly on NSE 30-minute data; until then treat the 80% as unverified.

> [!note] Status 2026-08-09: unblocked in principle, still gated on accumulation
> An [intraday store](tools/intraday_store.py) now exists, so the "nothing persists intraday bars" blocker is gone. But this rule is specified on **two consecutive 30-minute bars**, and Yahoo only serves ~60 days of 30m/15m history — currently **58 sessions**. That is too few, and 1h is too coarse for a rule whose entry condition is a 30-minute hold. **The store accumulates forward, so this becomes testable with time rather than with work** — provided the daily update actually runs. See [[analyses/Intraday-Store]]. The intraday cousin of this rule is already noted under [[concepts/Initial-Balance]].

## Variants / Parameters
- Rows/bins (20–30 typical), lookback window, VA percentage (70% standard).
- **70% vs 68% for the value area** — the Market Profile convention is **70%** (what `volume_profile.py` uses, `value_area_pct: 0.70`). Retail material often prints **~68%**, borrowing the 1-standard-deviation figure (68.2%) because the value area is loosely described as "one SD of the distribution". They are the same idea with different rounding; 70% is the convention and the 68% framing is where it comes from. Not worth changing — but worth knowing which you are looking at when comparing our levels to someone else's chart.
- **Allocation method matters**: proportional range-overlap per bin (the `tools/volume_profile.js` method) is more accurate than even-split-per-row (the TradingIQ Pine's shortcut) — even split over-weights rows a bar barely clipped.
- **VA expansion method matters**: expand from the POC toward the *higher-volume* neighbor until 70% is enclosed (standard); the Pine's alternate-one-row-each-way shortcut can misplace VAH/VAL on asymmetric profiles.
- **HVN/LVN detection parameters** ([volume_profile.py:35](tools/volume_profile.py:35)): a node *seeds* at a local-extremum bin clearing `mean_vol × 1.5` (HVN) or `× 0.5` (LVN), then **expands outward** while neighbours stay within tolerance (`0.85` / `1.30`), and overlapping pockets merge. So a node is a contiguous price **pocket**, not a single row — a meaningful step beyond the "thick bars / thin bars" reading in most retail material.

### Implementations in this repo (corrected 2026-08-09)
| Module | Scope | POC/VA | HVN/LVN | Delta |
|---|---|---|---|---|
| [volume_profile.js](tools/volume_profile.js) | chart-side (reference implementation; boundary math defined here, see VOLUME_PROFILE_MODULE.md) | ✓ | ✓ | — |
| [volume_profile.py](tools/volume_profile.py) | **Python toolchain — 1:1 parity-tested port of the JS** | ✓ | ✓ | — |
| `compute_volume_profile_levels()` in [scanner_templates.py](tools/scanner_templates.py) | screening-side; the "Profile" check (9th) in the Early Reversal validation layer — above-POC passes, below-VAL warns | ✓ | — | ✓ |

> [!warning] This page previously credited HVN/LVN to the JS module only
> Until 2026-08-09 this section named `volume_profile.js` and `compute_volume_profile_levels()` and **never mentioned `tools/volume_profile.py` at all** — despite that module having shipped 2026-07-25 with the full HVN/LVN pocket implementation and being wired into [stock_council.py](tools/stock_council.py). The page understated what was actually available in Python for two weeks, including through its own 2026-08-02 update. Do not "improve" the maths in either implementation without changing both, or the chart and the scanners will silently disagree about where the POC is.

## Common Mistakes
- Dumping each bar's whole volume at one price (its close) — badly distorts the histogram; distribute across the bar's range.
- Treating POC/VA from an arbitrary window as universal levels — they're window-relative; state the lookback (same discipline as timestamping key levels).
- Reading a POC touch as an entry by itself — the POC is *fair* price; edges (VAL in an uptrend, VAH in a downtrend) plus rejection evidence are where the asymmetry is.
- Ignoring delta — two identical-looking volume nodes with opposite delta signatures imply opposite follow-through.

## Related Concepts
- [[concepts/Order-Flow]] — delta, tick rule, bid/ask matching, absorption; volume profile is order flow aggregated by price.
- [[concepts/Multi-Timeframe-Analysis]] — the MTF-stacked-profiles application; value confluence across timeframes.
- [[concepts/Support-Resistance]] — HVN/POC as mechanically-derived S/R zones; LVNs explain fast traverses between zones.
- [[concepts/Initial-Balance]] — session value-area concepts (80% VA fill rule) are the intraday cousin of this page's swing-window profiles.
- [[concepts/Fair-Value-Gap]] — an FVG is a 3-candle LVN: the imbalance/air-pocket idea from the candle side rather than the histogram side.

## Examples in This Wiki
- **Python port (2026-07-03)**: `compute_volume_profile_levels()` in `tools/scanner_templates.py`, wired into the Early Reversal validation layer and the High-Growth Screener Validations column (VP✓/✗).
- Chart rendering: `tools/volume_profile.js` + `drawVolumeProfile()` in `tools/chart_dashboard.html` (POC/VA/HVN/LVN with documented boundary math in VOLUME_PROFILE_MODULE.md).

### HVN/LVN wired into Setup Intelligence (2026-08-09)
`describe_position()` reported value-area location and *counts* of HVN/LVN pockets, but [stock_council.py](tools/stock_council.py:302) copied only the POC/VAH/VAL fields into the evidence — so the panel could say **"above value"** but not **"sitting on an HVN"** or **"air pocket overhead"**, which is the actionable half of the profile. The pockets were computed and drawn on the chart the whole time; only the read-back was missing.

`describe_position()` now also returns `at_hvn` / `at_lvn` plus distance to the nearest pocket **above** (measured to its low) and **below** (to its high), and the council surfaces four factors from them:

| Condition | Read |
|---|---|
| Price **inside an HVN** | Risk — heaviest prior business here; HVNs are magnets, so expect rotation/chop rather than a clean directional move |
| Price **inside an LVN** | Risk — air pocket, poor support underfoot; stops here are unreliable and traverses are fast **both** ways |
| **HVN ≤4% below** | Bullish — a volume shelf to fall back on; the natural stop reference |
| **HVN ≤4% overhead** | Risk — heavy business to absorb; the first real ceiling |
| **LVN ≤4% overhead with no HVN in front** | Bullish — thin air above; breakouts traverse an LVN quickly |

Verified live (1y daily, 2026-08-09): ITC inside an HVN with another 5.0% overhead; TITAN above value but **inside an LVN** with its nearest HVN 13.6% below — the "no shelf underneath" case; TCS with an HVN 0.7% beneath; SBIN firing the shelf-below *and* air-above branches together (HVN 3.7% below, LVN 1.7% above with nothing in front), which is the combination the ordering guard exists for. 9/9 geometry checks on the node-position helper, including edge-touch and empty-zone cases.

**These reads are structural context, not signals, and they are unmeasured** — the same standing caveat as the value-area factors and the 80% rule above. Nothing here has been through [[analyses/Backtest-Harness]].
- **Live below-VAL example (2026-07-03)**: [[entities/EPIGRAL]] at ₹1,021.6 vs VAL ₹1,030.87 / POC ₹1,225.69 / VAH ₹1,312.84, only 43.3% of volume above POC — SwingEdge labels the profile "bearish"; our screening check would raise the "no volume acceptance" warning on exactly this chart. The POC/VAH double as the repair levels to watch.
- No POC-*reclaim* (bullish) live example yet — annotate an entity page when one confirms a tracked reversal.

## Sources
1. [MTF-Volume-Profiles-TradingIQ-Pine](../sources/MTF-Volume-Profiles-TradingIQ-Pine.md) — Pine v6 by KioseffTrading (MPL-2.0), ingested 2026-07-03; MTF stacking, delta model, LTF volume sourcing, POC/VA labeling.
3. [[sources/ForexTester-Volume-Analysis-Guide]] (2026-08-02) — the 80% value-area traverse rule, and the tick-vs-real volume caveat that governs what the histogram is counting in the first place (see [[concepts/Volume-Analysis]]).
2. `tools/volume_profile.js` + VOLUME_PROFILE_MODULE.md (this repo, 2026-06) — reference histogram/POC/VA/HVN/LVN implementation with proportional-overlap allocation and volume-greedy VA expansion (the methods the Python port uses).
4. User-supplied **"Market Profile & Volume Distribution"** infographic (in-conversation image, 2026-08-09) — prompted the implementation audit that produced the corrections above. **Contributed no mechanics this page lacked**: VAH/POC/VAL, the value area, HVN-as-magnet and LVN-as-fast-traverse were all already documented, and our implementation goes further (delta, MTF stacking, expanding node pockets). Its one substantive datapoint is the **~68%** value-area figure vs our 70% — see Variants. Recorded for provenance, not authority: unattributed retail educational graphic.
