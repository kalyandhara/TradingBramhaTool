---
title: "ScreeningMantis — price/volume column model & sector rotation tabs"
category: source
type: source
source_type: live-web-snapshot
author: "screeningmantis.com (product UI; no named author, no methodology page)"
url: https://screeningmantis.com
fetched: 2026-09-09
tags: [screener, sectors, rotation, turnover, volume, relative-strength, breadth, product-teardown]
related:
  - concepts/Turnover-Share-Rotation.md
  - concepts/Chaikin-Money-Flow.md
  - analyses/Open-Backlog.md
  - analyses/Sector-Rotation-Tool-Architecture.md
  - concepts/Stage-Analysis.md
created: 2026-09-09
updated: 2026-09-09
sources: 0
---

# ScreeningMantis — price/volume column model & sector rotation tabs

Second visit to this product. The **2026-09-07 ingest was a single screenshot**
and produced [[analyses/Open-Backlog#B-60]] (sector money-flow heatmap, built the
same day). This is the **live site**, read on 2026-09-09 (Nifty 50 23,431.5,
-0.86%; 1,538 stocks in the daily scan; 45 NSE sectoral/thematic indices).

Filed for the two things the owner asked to keep: the **PRICE & VOLUME column
group** on the stock table, and the **sector rotation model** behind the Sectors
tab. Everything here is UI observation — the site publishes no formulas, no
backtest, no sample size. Nothing below is evidence of edge; it is a **column
vocabulary** worth stealing or declining deliberately.

## 1 — The PRICE & VOLUME column group (stock table)

The table is organised as named column *groups*, which is itself the transferable
idea: PRICE & VOLUME · EMAS · PIVOTS · BREAKOUT STOCKS · RELATIVE STRENGTH ·
EARNINGS REACTION · PRICE MOVES. One row is a full technical read without a chart.

The **complete header, left to right, exactly as the product prints it** (every
column carries its own `i` tooltip — see the note under the table, that detail is
part of the design, not decoration):

| # | Column (group) | What it holds | Status here |
|---|---|---|---|
| 1 | `#` | rank under the active sort, restated per page | trivial |
| 2 | **MY WATCHLIST** | per-row toggle that adds the name to a saved list, in the leftmost position | have the lists, **not as an in-table control** |
| 3 | CAP | LC / MC / SC / **Mic** bucket | have (`nse_universe`) |
| 4 | TICKER | bare NSE symbol, the row's identity | have |
| 5 | SECTOR | one label per stock — the join key to every Sectors tab | **have three, none joining** (NSE macro 20/22, screener.in ~130, Yahoo 11/150 — the last is the one persisted). Their ~45-50 labels are Yahoo-*industry*-grained, so their sector table is **not** comparable cell-to-cell with ours. [[analyses/Open-Backlog#B-64]] |
| 6 | PRICE (Rs) *+ the date* | close, with **the as-of date in the header** ("09 Sept") | **the dated header is the idea** |
| 7 | 1D% | day change | have |
| 8 | RSI (*price & volume*) | integer, period unstated (assume 14) | [[concepts/RSI]] |
| 9 | **VOL SPIKE 1D/9D** | today's volume / **9-day** average, printed `4.7x` | we have RVOL **four times over** — 20d mean, 50d mean, 5d/20d ratio, 5-session median — and no shared definition |
| 10 | **GAP — Opening** | open vs prior close, signed % | computed, not surfaced as a column |
| 11 | EMAS | 10 / 20 / 50 / 200 as four lit-or-unlit pips | [[concepts/EMA]] |
| 12 | % FROM 20EMA | signed distance from the 20 EMA | computed inline (`scanner_templates.py:4340`), never exposed; note `scan_pullback_to_ema` uses **21**, not 20 |
| 13 | **EMA CROSS 10 x 20** | **age of the cross in days** ("28 days"); blank = no recent cross | the pair is computed nowhere, but cross detection and `_bars_ago` both exist — assembly ([[analyses/Open-Backlog#B-63]]) |
| 14 | D-PIVOT | which *zone* price sits in today: `R1`, `R1-PP`, `PP-S1`, `S1`, `Near R1`, `Near Pivot`, `N/A` | CPR + R1/S1 **are** computed, but **inside `build_chart()` as plot traces** (`dashboard_app.py:3391`) — daily only, no function, no zone label |
| 15 | W-PIVOT | same, weekly pivots | **absent entirely** — needs a weekly resample first |
| 16 | 52W HIGH | signed % from the 52-week high | have |
| 17 | **BO GAIN%** | gain since the breakout **and the breakout date** ("11.1% / 08 Sept"); `--` when there is no live breakout | **the date is the new part** |
| 18 | **STAGE 2** | `x/7` — a count of conditions met, not a yes/no | `scan_stage2_uptrend` is a **hard gate** (returns `None` on any failed leg) — there is no count to surface |
| 19 | RS (momentum) | signed number, method unstated | **have one**: `_rs_raw` = IBD-weighted trailing return (63/126/189/252 @ .4/.2/.2/.2) minus benchmark |
| 20 | **RS RANK HISTORY** | percentile at **T-30 -> T-15 -> T-5 -> T0** as a four-step walk; `?` where history is short (IPOs) | our `rs_rank` is percentile **within a scan's hits**, not the universe, and is not persisted — the walk needs a new measure + a daily table ([[analyses/Open-Backlog#B-63]]) |
| 21 | NEXT EARN. | next scheduled date, `--` if unknown | [[concepts/PEAD]] |
| 22 | PAST EARN. | last reported date | have |
| 23 | -1D% | return the day BEFORE the print | **the anticipation leg — not held** |
| 24 | E-DAY% | return on the print day | partially |
| 25 | +1D% | return the day AFTER | partially |
| 26 | **HIST. PRICE (Rs)** | price at a **user-chosen reference date** | **not held** |
| 27 | **GAIN% SINCE** | return from that chosen date to today | **not held** |
| 28 | **NOTES** | free-text the user writes on the row, persisted | have per-symbol notes, **not in-table** |


> [!note] Careful with the word "pivot" in this repo
> Every `pivot` / `pivot_len` in `scanner_templates.py` is a **swing** pivot, and
> `scan_near_pivot` is swing-high proximity. None of it is a floor pivot.
> Grepping for "pivot" gives false confidence that D-Pivot/W-Pivot are covered.
> The real CPR arithmetic is in `dashboard_app.py:3391-3401` and nowhere else.
> Column-by-column audit: [[analyses/Open-Backlog#B-63]].

Three structural details that are easy to read past:

- **Every column header carries an `i` tooltip.** 28 columns is only legible
  because the definition of each one is one hover away. Streamlit gives this for
  free through `column_config(help=...)` and this repo already passes `help=` in
  121 places — but never as a *reusable* definition, so the same column is
  explained differently, or not at all, on different pages.
- **Columns 26-27 are a user-parameterised pair.** `HIST. PRICE` + `GAIN% SINCE`
  are not a fixed lookback; the reader picks the date and the whole table
  re-bases. That turns a screener into "how has my universe done since the day I
  looked", which is a different question from anything our pages currently answer.
- **Columns 2 and 28 are write-back.** Watchlist toggle and Notes are edits made
  *in the row*, which is what makes a 1,538-row table usable as a working
  surface rather than a report. `st.data_editor` is the Streamlit equivalent, and
  this repo uses `st.dataframe` (read-only) in **42 of 43** places.

**The genuinely new columns are the time-derivative ones.** EMA-cross age,
BO-gain-since-date, the RS-rank walk, and the HIST. PRICE / GAIN% SINCE pair all
answer *"how long has this been true?"* rather than *"is it true now?"* — a state
that is 28 days old reads differently from one that turned this morning, and
every scanner in this repo currently prints only the latter. Cheap to add, no new
data source: they describe bars we already pull.

The `x/7` Stage-2 score is the same move applied to a boolean: it degrades a gate
into a **count of conditions met**, so a name failing on one leg is still visible.
Compare the 6/7, 3/7 and 0/7 values sitting inside the same top-20 — a hard gate
would have hidden most of that list.

> [!warning] 9-day RVOL is a choice, not a standard
> A 9-day mean makes `VOL SPIKE` react roughly twice as fast as a 20-day one and
> lets a single prior spike deflate the ratio for two weeks. Their top rows print
> 4.7x-8.4x, which a 20-day base would rank differently. **Do not copy the number
> without the window**, and do not compare theirs to ours.

## 2 — The sector model (Sectors tab)

Seven sub-tabs: Nifty Indices · **Sector Ranking** · Turnover Rotation · Sector
Turnover · Turnover A/D · **Chaikin Money Flow** · Relative Strength.

### 2a — Sector Ranking, split into two blocks

**SECTOR ROTATION** — `STOCKS #`, `TURNOVER` (Rs Cr), `% CHANGE D/W`,
**`SHARE %`**, **`Δ SHARE (PT) D/W`**.

The load-bearing column is **Δ share in percentage points**: a sector's slice of
*total market turnover* today versus a day and a week ago. This is rotation
measured in **money**, not price — promoted to
[[concepts/Turnover-Share-Rotation]], because it is the one idea on this page
that the vault does not already hold in some form.

**SECTOR HEALTH** — `A/D NET`, `AVG RSI`, `% > 20EMA`, `% BO IN LAST 10 DAYS`,
`LEADERS` (three tickers).

Four breadth statistics over the sector's own constituents plus a named example.
`% BO IN LAST 10 DAYS` is the only one that is not standard breadth — it counts
*participation in the move*, which is what separates a sector rising on two heavy
names from one rising on thirty.

Sample of the 2026-09-09 read (top of a 45-row table):

| Sector | # | Turnover | Share % | Δ share D | Δ share W | A/D net | Avg RSI | % > 20EMA | % BO 10d |
|---|---|---|---|---|---|---|---|---|---|
| Aerospace & Defense | 30 | 3,857.6 Cr | 3.44 | -4.94 | -0.61 | 54 | +63% | +33% | |
| Electrical Equipment | 56 | 5,635.6 Cr | 5.02 | -3.06 | +0.08 | 51 | +48% | +32% | |
| Industrial Products | 43 | 4,153.8 Cr | 3.70 | **+2.95** | +0.62 | 51 | +49% | +28% | |
| Information Technology | 66 | 7,669.5 Cr | 6.83 | **+2.70** | -0.92 | 43 | +24% | +18% | |
| Metals & Mining | 44 | 7,836.3 Cr | 6.98 | +2.07 | +0.72 | 51 | +59% | +25% | |

Note IT: **+2.70 pt of turnover share on a day NIFTY IT fell -3.24%** — inflow of
attention, outflow of price. That combination is exactly what a price-only
rotation view cannot say, and it is the argument for the column.

### 2b — Chaikin Money Flow tab — what B-60 was copied from

Confirmed as **"20-session sector-average CMF across Today, 1 Week Ago, 2 Weeks
Ago, and 1 Month Ago"**, with a categorical **Trend** column taking four values:
**Accumulating · Improving · Neutral · Distributing**.

Three deltas against what we built ([[analyses/Open-Backlog#B-60]]):

1. They say **20-session**; our `money_flow.py` uses the conventional **21-bar**
   window. Immaterial to the reading, material if anyone ever compares cell to cell.
2. They say **"sector-average CMF"** — a mean of constituent CMFs. B-60
   deliberately did **not** do that: it sums money-flow volume across the sector
   and divides by summed volume, because a mean lets a smallcap outvote a
   heavyweight, and a test in this repo shows the naive mean **inverts** at least
   one sector's sign. Our departure stands; the difference is now on the record.
3. Their four-state Trend label is a naming we do not have. Cheap to adopt over a
   bare numeric cell — but it makes the overlapping-window caveat *worse*, not
   better: "Improving" across four windows that share most of their bars is one
   observation wearing four hats. See [[concepts/Chaikin-Money-Flow]].

### 2c — Nifty Indices tab

45 sectoral/thematic indices carrying the same columns as the stock table
(RSI, EMA pips, % from 20EMA, EMA-cross age, D/W pivot zone, **RS rank history**).
The interesting part is only that **the index rows and the stock rows share a
column vocabulary** — one mental model, two levels of aggregation. Our Sector Map
and Scanner Hub currently speak different dialects.

## What was not kept

- **The 1,538-row table itself.** Point-in-time, decays daily, and we run our own scan.
- **RS "momentum" as a number.** Method unstated; we cannot reproduce or check it.
- **The recommended-filter presets** (EMAs Aligned, EMAs Converge, RSI > MA,
  Breakout stocks, IPO stocks) — all already expressible in our screener.
- **Any performance claim.** There are none on the site, which is to its credit.

> [!note] Provenance tier
> Product-UI observation of a commercial screener. No formulas, no backtests, no
> author. Everything above is **a vocabulary of columns**, and the only thing that
> can be verified from it is what we compute ourselves. Same tier as the StockEdge
> teardowns already in this folder.

## Related Pages

- [[concepts/Turnover-Share-Rotation]] — the one concept promoted from this visit
- [[concepts/Chaikin-Money-Flow]] — B-60's indicator; this visit pins their window and aggregation
- [[analyses/Open-Backlog]] — B-60 (built), B-62 (proposed here)
- [[analyses/Sector-Rotation-Tool-Architecture]] — our FII/DII rotation score, a different definition of the same word
