---
title: "Volume Profile (POC / Value Area / Delta)"
category: concept
tags: [volume-profile, poc, value-area, vah, val, hvn, lvn, delta, market-profile, order-flow]
created: 2026-07-03
updated: 2026-08-02
sources: 3
related: [concepts/Order-Flow, concepts/Multi-Timeframe-Analysis, concepts/Support-Resistance, concepts/Initial-Balance, concepts/Fair-Value-Gap, concepts/Volume-Analysis, sources/ForexTester-Volume-Analysis-Guide]
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

Recorded as a **claim with a number attached, from a vendor blog with no data behind it**. Unlike most volume maxims it is fully specified — entry condition, target, and probability — so it can be measured rather than believed. [[analyses/Backtest-Harness]] can test it directly on NSE 30-minute data; until then treat the 80% as unverified. The intraday cousin of this rule is already noted under [[concepts/Initial-Balance]].

## Variants / Parameters
- Rows/bins (20–30 typical), lookback window, VA percentage (70% standard).
- **Allocation method matters**: proportional range-overlap per bin (the `tools/volume_profile.js` method) is more accurate than even-split-per-row (the TradingIQ Pine's shortcut) — even split over-weights rows a bar barely clipped.
- **VA expansion method matters**: expand from the POC toward the *higher-volume* neighbor until 70% is enclosed (standard); the Pine's alternate-one-row-each-way shortcut can misplace VAH/VAL on asymmetric profiles.
- Implementations in this repo: `tools/volume_profile.js` (chart-side: full histogram, POC/VA/HVN/LVN, confluence finder; see VOLUME_PROFILE_MODULE.md) and `compute_volume_profile_levels()` in `tools/scanner_templates.py` (screening-side: POC/VAH/VAL + delta; the "Profile" check, 9th, in the Early Reversal validation layer — above-POC passes, below-VAL warns).

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
- **Live below-VAL example (2026-07-03)**: [[entities/EPIGRAL]] at ₹1,021.6 vs VAL ₹1,030.87 / POC ₹1,225.69 / VAH ₹1,312.84, only 43.3% of volume above POC — SwingEdge labels the profile "bearish"; our screening check would raise the "no volume acceptance" warning on exactly this chart. The POC/VAH double as the repair levels to watch.
- No POC-*reclaim* (bullish) live example yet — annotate an entity page when one confirms a tracked reversal.

## Sources
1. [MTF-Volume-Profiles-TradingIQ-Pine](../sources/MTF-Volume-Profiles-TradingIQ-Pine.md) — Pine v6 by KioseffTrading (MPL-2.0), ingested 2026-07-03; MTF stacking, delta model, LTF volume sourcing, POC/VA labeling.
3. [[sources/ForexTester-Volume-Analysis-Guide]] (2026-08-02) — the 80% value-area traverse rule, and the tick-vs-real volume caveat that governs what the histogram is counting in the first place (see [[concepts/Volume-Analysis]]).
2. `tools/volume_profile.js` + VOLUME_PROFILE_MODULE.md (this repo, 2026-06) — reference histogram/POC/VA/HVN/LVN implementation with proportional-overlap allocation and volume-greedy VA expansion (the methods the Python port uses).
