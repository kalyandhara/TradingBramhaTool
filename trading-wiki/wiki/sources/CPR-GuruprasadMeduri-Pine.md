---
title: "TradingView Pine — CPR with MAs, Super Trend & VWAP (by GuruprasadMeduri)"
category: source
tags: [pine-script, cpr, pivots, supertrend, vwap, indian-intraday, multi-timeframe, floor-pivots]
created: 2026-07-08
updated: 2026-07-08
sources: 1
related: [concepts/CPR-Central-Pivot-Range, concepts/VWAP]
---

# TradingView Pine — CPR with MAs, Super Trend & VWAP (by GuruprasadMeduri)

## Metadata
- **Author:** GuruprasadMeduri
- **Version:** Pine v4
- **License:** Mozilla Public License 2.0
- **Format:** Single-file Pine script bundling CPR, multi-TF floor pivots, SMA, EMA, VWAP, and Supertrend into one overlay indicator.
- **Distinctive elements (not in our stack):**
  - **CPR (Central Pivot Range)** — Pivot / BC / TC three-line intraday range.
  - **Multi-timeframe floor pivots** — Daily/Weekly/Monthly S1-S3 + R1-R3, style-coded per timeframe (daily = solid line, weekly = crosses `+`, monthly = circles `o`).
  - **Supertrend** — HL2 ± (Factor × ATR) trailing stop with directional flip.
- **Elements duplicated in our stack:** SMA(50), EMA(50), session VWAP — all three already in [INDICATOR_DEFS](tools/chart_dashboard.html:588).
- **Date accessed:** 2026-07-08.

## What This Source Provides

### The CPR calculation (previous day's H/L/C)
```
Pivot = (High + Low + Close) / 3       // central pivot
BC    = (High + Low) / 2                // bottom central
TC    = (Pivot - BC) + Pivot            // top central = 2*Pivot - BC
```
Three horizontal levels that persist for the whole trading session. The band width (TC - BC) is itself a signal — **narrow CPR = expect trending day**, **wide CPR = expect range-bound day**. See [[concepts/CPR-Central-Pivot-Range]].

### The classical floor-pivot support/resistance (previous day's H/L/C)
```
S1 = 2*Pivot - High                    R1 = 2*Pivot - Low
S2 = Pivot - (High - Low)              R2 = Pivot + (High - Low)
S3 = Low - 2*(High - Pivot)            R3 = High + 2*(Pivot - Low)
```
Standard floor-trader pivot formula. Same math applied across three timeframes — daily/weekly/monthly — for MTF confluence reading.

### Config surface (checkbox toggles in the script)
| Toggle | Default |
|---|---|
| Plot CPR (BC + TC) | ✅ ON |
| Daily S1/R1 | ✅ ON |
| Daily S2/R2 | ⬜ OFF |
| Daily S3/R3 | ⬜ OFF |
| Weekly Pivot | ⬜ OFF |
| Weekly S1/R1, S2/R2, S3/R3 | ⬜ OFF |
| Monthly Pivot | ⬜ OFF |
| Monthly S1/R1, S2/R2, S3/R3 | ⬜ OFF |
| SMA (50, close) | ✅ ON |
| EMA (50, close) | ✅ ON |
| VWAP (close) | ✅ ON |
| Supertrend (Factor=3, Length=10) | ✅ ON |

### Style code across timeframes
| Timeframe | Line style | Distinguishing shape |
|---|---|---|
| Daily | solid line | plain |
| Weekly | solid line | `+` cross markers |
| Monthly | solid line | `o` circle markers |

This is the small design touch that makes MTF-pivot confluence readable at a glance — you can immediately see whether price is testing a daily-R1, weekly-R2, and monthly-R1 all at the same level without squinting at labels.

### Supertrend formula
```
BasicUpper = HL2 - Factor × ATR(Length)
BasicLower = HL2 + Factor × ATR(Length)
```
With trend-flip logic: when close crosses the finalized lower band → bullish (green line below price, arrow up); when close crosses upper band → bearish (red line above price, arrow down). Default `Factor=3, Length=10` — the canonical Supertrend settings.

## Actionable Insights

### CPR is a real gap for our chart
CPR is the single most-used indicator in the Indian intraday retail community (Rakesh Bansal / Vishal Malkan / Sudhanshu Aggarwal all teach off it). Every Indian trader who opens a chart looks for the CPR first. We have zero pivots system in the chart right now — session VWAP is the closest analogue, but VWAP + CPR are used together, not as substitutes.

**Adoption plan (rank 1 of the pending indicator queue):**
- New chart indicator `cpr` in [INDICATOR_DEFS](tools/chart_dashboard.html:588) under a new "Levels & Pivots" group.
- Server-side: extend `chart_server.py` with `/api/pivots?symbol=…&timeframe=…&tfs=D,W,M` that fetches daily/weekly/monthly bars from data_source and computes P/BC/TC + S1-3/R1-3 for the current period.
- Client-side: render each level as a `PriceLine` on the main candle series (they're horizontal). Per-timeframe styling (line style, color, dashed for W/M).
- Effort: ~4-5 hours end-to-end.

### Multi-timeframe pivots — the confluence layer
Once CPR ships, the daily/weekly/monthly pivot toggles are trivial extensions of the same endpoint. The **confluence reading** (daily-R1 + weekly-R1 stacked at the same price = high-conviction rejection level) is where the real edge lives, not any single pivot line.

### Supertrend — separately worth having
Supertrend is on the "game-changer indicators still missing" list from the 2026-07-08 stack review. Cross-market favorite, tiny to compute, plays cleanly with the existing chart. Recommend shipping as its own indicator rather than bundled with CPR (Pine bundles are cheaper than JS bundles for us; splitting on our side keeps the INDICATOR_DEFS checkbox surface clean).

### What NOT to port from this script
- **SMA(50), EMA(50), VWAP** — all three duplicate our existing indicators. Skip.
- The **single-file bundle** approach — Pine's checkbox-forest is fine for one script; on our side, each capability wants its own INDICATOR_DEFS entry so users can compose.

## Contradictions with Existing Wiki
- **VWAP formula in the script uses `close` as the source** (`vwap(close)`), which is *not* the standard textbook VWAP. Standard is `HLC/3` weighted by volume. Our existing session VWAP in [chart_dashboard.html](tools/chart_dashboard.html) uses the standard formulation. Flagging so if we ever cross-check against a chart running this Pine script, the two won't agree exactly.
- **Pine v4** — the script is written in v4 (deprecated as of TradingView's v5/v6 push). Formulas are timeless; the `security()` + `barmerge.gaps_off` + `barmerge.lookahead_on` mechanics we don't need on our side since we can fetch daily/weekly/monthly bars directly from the server.

## Pages Updated
- Created: `wiki/sources/CPR-GuruprasadMeduri-Pine.md` (this page)
- Created: `wiki/concepts/CPR-Central-Pivot-Range.md` — first-class concept page for CPR (the distinctive contribution of this script)
- Updated: `wiki/index.md`, `wiki/log.md`
- **Flagged (not created this ingest):**
  - `concepts/Floor-Pivots.md` — the classical S/R formulas are shared across all pivot systems; a concept page cross-linked from CPR is worth having.
  - `concepts/Supertrend.md` — worth a dedicated page once we implement the indicator; from the 2026-07-08 game-changer list.
