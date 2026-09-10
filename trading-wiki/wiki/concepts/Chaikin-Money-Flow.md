---
title: "Chaikin Money Flow (CMF)"
category: concept
tags: [indicator, volume, money-flow, accumulation-distribution, sector-analysis]
timeframe: daily
created: 2026-09-07
updated: 2026-09-09
sources: 4
related:
  - analyses/Open-Backlog.md
  - concepts/Volume-Profile.md
  - analyses/Indicator-Coverage-Gap.md
---

# Chaikin Money Flow (CMF)

Marc Chaikin's volume-weighted average of accumulation and distribution over a
window. It answers one question: **over the last N bars, did closes tend to
happen near the top of their bar's range on volume, or near the bottom?**

Ingested 2026-09-07 for [[analyses/Open-Backlog#B-60]] — the sector money-flow
heatmap.

## The arithmetic

Per bar, a **Money Flow Multiplier** placing the close inside its own range:

```
MFM = ((Close - Low) - (High - Close)) / (High - Low)          in [-1, +1]
MFV = MFM x Volume                                              "money flow volume"

CMF(N) = sum(MFV, N) / sum(Volume, N)
```

`MFM = +1` means the close *was* the high; `-1` means it was the low; `0` is a
close at the midpoint. **CMF is therefore bounded in [-1, +1]**, and in practice
lives inside roughly **±0.25** — which is why a heatmap of it needs a colour
scale clipped near that range, not one stretched to the theoretical bounds.

**N = 21** is Chaikin's standard (roughly a trading month).

## Reading it

| CMF | reading |
|---|---|
| `> 0` | accumulation — closes clustering in the upper half of their ranges, on volume |
| `< 0` | distribution — closes clustering in the lower half |
| crossing 0 | a change in who is winning the day, not a trade trigger |
| distance from 0 | strength; ±0.25 is already a strong reading |

A zero line is the whole interpretive frame: the sign says accumulation or
distribution, the magnitude says how one-sided it has been.

> [!warning] The structural flaw, and it is not small
> **CMF ignores the previous close entirely.** The multiplier places the close
> inside the CURRENT bar's high-low range, so **gaps are invisible to it**.
>
> A stock can gap down hard, close sharply lower on heavy volume, and still print
> *rising* CMF — because within that day's range the close happened to sit above
> the midpoint. The reverse also holds: a gap up that fades to mid-range prints
> weak or negative money flow on a day price rose.
>
> This is inherent to the formula, not an implementation bug, and it is why CMF
> must be read beside price rather than instead of it. On a **sector aggregate**
> the effect partly washes out — individual gaps do not align across a sector —
> but an index-level gap (budget day, a global risk event) hits every constituent
> at once and CMF will misread that session for the whole board.

## Why this is worth having at SECTOR level specifically

The desk already has stock-level volume tools — `volume_anomaly` (spikes with
cause attribution), MFI via `scan_mfi_oversold`, Volume Profile, Session VP.
What it does not have is **where money is going at the sector level, over time.**

CMF suits that better than a spike detector because it is a *bounded ratio*: it
divides by total volume, so a ₹40,000cr sector and a ₹400cr sector produce
directly comparable numbers. Raw traded value cannot be compared across sectors
without normalising; CMF is normalised by construction. That is the single
property that makes a sector heatmap legible.

## What it is NOT

- **Not a trade trigger.** Chaikin designed it as a confirmation tool. This desk's
  own record on volume-derived signals is a caution: `volume_anomaly` spikes ship
  as attention lists, and B-19 measured most single-condition scanners negative
  after costs.
- **Not order flow.** It infers accumulation from where a close landed. It does
  not see the tape, the bid/ask, or who traded. A close near the high on volume
  is *consistent with* accumulation, not evidence of it.
- **Not FII/DII flow.** Institutional flow data is a separate, reported series
  (`sector_rotation.py` reads an FII export). CMF is derived from price and
  volume alone and can disagree with reported flows — when it does, the reported
  series is the fact and CMF is the inference.


## What the source product actually does (checked 2026-09-09)

B-60 was built from a screenshot. Reading the live site
([[sources/ScreeningMantis-Price-Volume-Sector-Rotation-2026-09-09]]) pins down
three things it had to guess at:

- Their window is **20 sessions**; ours is the conventional **21 bars**. No
  practical difference in the reading, but the cells are not comparable one to one.
- They compute a **sector-average CMF** — a mean of constituent CMFs. We
  deliberately do not: `money_flow.py` sums money-flow volume across the sector
  and divides by summed volume, because the mean lets a smallcap outvote a
  heavyweight, and a test here shows the naive mean **inverts** a sector's sign.
  The departure is intentional and stays.
- They label each row **Accumulating / Improving / Neutral / Distributing**. A
  usable naming for our numeric cell — but note it *amplifies* the caveat below:
  four overlapping 20-bar windows that share most of their bars are close to one
  observation, so "Improving" is a shape read off correlated cells, not four
  independent confirmations.

## Related

- [[analyses/Open-Backlog#B-60]] — the sector money-flow heatmap this was ingested for
- [[concepts/Turnover-Share-Rotation]] — the unsigned partner: WHERE attention went; CMF says which side of the range it closed on
- [[concepts/Volume-Profile]] — volume at PRICE; CMF is volume at CLOSE-LOCATION over TIME
- `tools/scanner_templates.py::_mfi_series` — the desk's existing Money Flow Index,
  a different indicator: MFI is an RSI-style 0-100 oscillator on typical price,
  CMF is a -1..+1 ratio on close location. Do not conflate them.

## Sources

- [StockCharts ChartSchool — Chaikin Money Flow](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chaikin-money-flow-cmf)
- [Fidelity — Chaikin Money Flow (CMF)](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/cmf)
- [TradingView — Chaikin Money Flow (CMF)](https://www.tradingview.com/support/solutions/43000501974-chaikin-money-flow-cmf/)
- [LuxAlgo — Chaikin Money Flow concept](https://www.luxalgo.com/library/concept/chaikin-money-flow/)
