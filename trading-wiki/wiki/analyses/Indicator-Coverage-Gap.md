---
title: "Indicator Coverage Gap — what top traders use vs what the chart tool implements"
category: analysis
type: analysis
created: 2026-08-30
updated: 2026-08-30
tags: [gap-analysis, indicators, chart-tool, backlog, coverage]
related: [concepts/Indicator-Selection-By-Regime, concepts/Order-Flow, concepts/CCI, concepts/KST, concepts/True-Strength-Index-TSI, concepts/CPR-Central-Pivot-Range, analyses/Open-Backlog, analyses/Scanner-Overlap-Audit]
sources: 0
---

# Indicator Coverage Gap

Inventory of `INDICATOR_DEFS` in `tools/chart_dashboard.html` (**44 selectable indicators**,
6 groups) and `scan_*` in `tools/scanner_templates.py` (**44 scanners**), set against the
indicator sets that public sources and prop-desk tooling consistently name.

> [!warning] On the quality of the "what top traders use" evidence
> Every 2026-dated "most used indicators" listicle surfaced by search is SEO content with
> **no named survey, no sample, and no methodology** — several are affiliate pages for
> brokers or prop firms. They agree with each other because they copy each other, not
> because they measured anything. The only claim in that corpus worth carrying is the
> *composition* one (trend + momentum + volume, 2–4 tools, confluence required), and even
> that is folklore repeated confidently. **Treat the "commonly cited" column below as a
> popularity prior, not evidence of edge.** This repo's own null results on
> [[concepts/EVWMA-VWAP-MACD]], [[concepts/Renko-Charts]] and [[concepts/Gamma-Exposure-GEX]]
> are the standing reminder that popularity and edge are unrelated.

## Already covered — no gap

| Family | Commonly cited | This repo |
|---|---|---|
| Trend / MA | SMA, EMA, VWAP, SuperTrend | `sma20/50/200`, `ema9/20/50/200`, `vwap`, `avwap`, `mabias`, `pmax`, `stai` (adaptive SuperTrend via K-means) |
| Bands | Bollinger, Keltner, Donchian | `bollinger`, `donchian`, `keltner` |
| Momentum | RSI, MACD, Stochastic, ROC, ADX/DMI, Williams %R | `rsi`, `macd`, `stoch`, `roc`, `adxdi`, `prte`, `hm`, `evmacd`, `rsidiv` |
| Volume | Volume Profile, OBV, VWAP | `volume`, `volprofile`, `svp` (session HD), `obv` |
| Structure | Fib, Elliott, S/R, patterns | `fib`, `elliott`, `trendlines`, `vcp`, `roundbottom`, `falling_wedge`, `structure_chain`, `harmonic`, `orderblock`, `fvg`, `gann`, `projection` |
| Chart type | Renko, Heikin Ashi | `renko` overlay + HA candle mode |

Coverage of the conventional retail indicator set is **already unusually complete** — the
tool carries several things the listicles do not (session volume profile, order blocks,
structure-break chains, adaptive-factor SuperTrend, relative strength vs benchmark).

## Real gaps, ranked

### Tier 1 — a wiki page exists but there is no code

The wiki already argues these matter; nothing implements them. Cheapest possible additions,
and the gap is embarrassing rather than debatable.

| Indicator | Wiki page | Code | Note |
|---|---|---|---|
| **CCI** | [[concepts/CCI]] | none | absent from chart *and* scanners |
| **KST** | [[concepts/KST]] | none | the source summary calls it over-rated; the wiki page is neutral |
| **TSI** | [[concepts/True-Strength-Index-TSI]] | none | double-smoothed momentum; formula already written out |
| **CPR / pivots** | [[concepts/CPR-Central-Pivot-Range]] | none in chart | standard intraday reference in Indian markets; `grep cpr chart_dashboard.html` → 0 |
| **MFI** | — | `scan_mfi_oversold`, `_mfi_series` | computed for a scanner, **never plottable**; a one-line reuse |

### Tier 2 — commonly cited, entirely absent

| Indicator | Why it is named | Assessment |
|---|---|---|
| **Ichimoku Cloud** | The single most-cited "complete system" indicator; the source summary calls it a lifetime favourite | Genuine gap. Five lines, forward-shifted cloud — the forward shift is the only non-trivial part and Lightweight Charts handles it via whitespace padding already used by `padSeries` |
| **Parabolic SAR** | Named as the trailing-stop / flip tool | Genuine gap, but note `pmax` and `stai` already occupy the trailing-stop-flip role. Adding SAR risks another zero-unique entry of the kind [[analyses/Scanner-Overlap-Audit]] just trimmed |
| **ATR (visible)** | Volatility sizing | ATR is computed 32× in the dashboard (Keltner, PMax, Renko) but is **not selectable**. Exposing the existing series is near-free and stop-sizing needs it |
| **Chaikin Money Flow / A-D** | Volume-flow family | Partially redundant with OBV + volume profile |
| **Vortex, RVI, MAMA, Awesome Osc., TTM Squeeze** | Named in the source summary as under-rated | Low priority — all are momentum/trend restatements, and the repo already has eight oscillators |

### Tier 3 — the gap that actually matters

**Order flow.** Footprint / volumetric bars, **cumulative volume delta (CVD)**, and
Market-Profile **TPO** are what the prop-desk tooling literature (NinjaTrader Order Flow+,
Tradovate, ATAS, GoCharting) actually converges on, and they are the tools
[[entities/Chris-Kmer]] describes using — see [[concepts/Order-Flow]]. The repo has
`volprofile` and `svp`, which are the *volume-at-price* half. It has **none** of the
buy/sell-aggressor half.

> [!important] The blocker is data, not code
> CVD and footprint need **tick or bid/ask-classified trade data**. `data_source.py` serves
> OHLCV bars from yfinance and Hyperliquid. Bar-level delta proxies (close-position-in-range
> × volume) exist and are *not* the same measurement — they would produce a plausible-looking
> chart of something that is not delta. Any B-item here must state the data source first.
> Hyperliquid is the one feed in this stack that could plausibly supply real trade-side data.

**TPO / Market Profile** has no such blocker — it is a time-based reorganisation of bars the
tool already has, and it is a genuinely different lens from `svp`'s volume-based one.

## Recommended backlog items

- **B-45 — expose ATR + MFI as chart indicators.** Both series already exist in the codebase;
  this is wiring, not maths. Do first.
- **B-46 — Ichimoku Cloud.** The largest single named gap; self-contained.
- **B-47 — TPO / Market Profile pane.** No data blocker, and complements `svp` rather than
  duplicating it.
- **B-48 — CVD feasibility spike.** *Answer the data question before writing an indicator.*
  Deliverable is a note on whether Hyperliquid (and any NSE path) exposes trade-side data,
  not a chart.
- **CCI / KST / TSI / CPR** — implement only if something asks for them. Four wiki pages
  with no code is a documentation gap, not necessarily a product one.

> [!key-insight]
> The honest headline: **this tool is not short of indicators.** It carries 44, has just
> hidden 9 of 41 scanners for redundancy, and has measured three of its four newest
> indicators to **no edge**. Adding Vortex or RVI would add rows, not information. The one
> direction with a real information gain is **order flow's aggressor side**, and that is
> gated on data this stack does not currently receive.
