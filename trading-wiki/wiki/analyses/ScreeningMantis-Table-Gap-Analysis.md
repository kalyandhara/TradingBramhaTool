---
title: "ScreeningMantis table — gap analysis, and what is worth copying"
category: analysis
tags: [ui, tables, design-system, columns, gap-analysis]
timeframe: build-plan
created: 2026-09-10
updated: 2026-09-10
sources: 1
related:
  - analyses/Open-Backlog.md
  - sources/ScreeningMantis-Price-Volume-Sector-Rotation-2026-09-09.md
---

# Analysis: ScreeningMantis table — gap analysis

Captured live from `screeningmantis.com` on **2026-09-10**, computed styles and
DOM read directly rather than eyeballed from a screenshot. Their table: **28
columns, 1,538 rows, a two-tier grouped header, 408 sticky cells.**

This page separates three things that are usually muddled together: **which
columns we lack**, **which craft we lack**, and **which of their choices we
should decline**.

## 1 · Columns — where we actually stand

[[analyses/Open-Backlog#B-63b]] already built most of this set on 2026-09-09.
The gap is smaller than it looks.

### Already shipped

| their column | ours |
|---|---|
| PRICE (₹) + as-of date | `close` with a dated header |
| 1D% | `chg_pct` |
| GAP (opening) | `gap_pct` |
| EMA CROSS 10x20 | `ema_cross_age`, signed, with `searched` |
| D-PIVOT / W-PIVOT | `pivot_levels()` + `weekly_frame()`, zone-labelled |
| 52W HIGH | `pct_from_52w_high` |
| BO GAIN% | `breakout()` gain **and date** |
| RS RANK HISTORY T-30→T0 | `rs_walk` — universe-wide, guests marked `*` |
| HIST. PRICE + GAIN% SINCE | `since()` re-base |
| NOTES | Watchlist `st.data_editor`, persisted |
| SECTOR | `sectors.py` canonical vocabulary (B-64) |
| VOL SPIKE | `rvol` — **ours is 20-day, theirs 9-day; deliberately not copied** |

### Genuinely missing

| column | cost | note |
|---|---|---|
| **CAP badge** (Mic / SC / MC / LC) | trivial | `cap_bucket` id exists in the registry with no renderer. Theirs is a coloured chip — purple micro, amber small |
| **RSI** | trivial | `_rsi_series` exists (Wilder 14, one implementation). Never surfaced as a column |
| **% FROM 20EMA** | trivial | computed at `scanner_templates.py:4340`, **never exposed** — the B-63b audit flagged exactly this |
| **EMAS alignment chips** (10/20/50/200) | small | four boolean above/below marks in one cell. We compute every span; nothing renders them together. **The best idea on their page** — four facts in one glance-width |
| **STAGE 2 as x/7** | none | we already have `score_minervini` → x/8 on the Watchlist. Theirs is x/7. Do not add a second scorer |
| **RS (momentum) value** | small | we have `rs_raw` / `rs_rank`; theirs shows the raw momentum figure beside the rank walk |
| **EARNINGS REACTION group** — NEXT EARN, PAST EARN, −1D%, E-DAY%, +1D% | **medium** | the one substantial data gap. We have an earnings cache; we do not have the **three-day reaction triplet**, which is the actual content |
| **In-row watchlist star** | small | deliberately declined in B-63b — the page already has an add form and row-select → ♥, and a third way is not a feature. **Still declined** |

**So the column gap is: five cheap ones, one alignment widget, and one real
build (earnings reaction).**

## 2 · Craft — this is the actual gap, and it is bigger than the columns

Measured off their computed styles:

| | ScreeningMantis | Trading Bramha today |
|---|---|---|
| body font | Inter Variable 13px | Segoe UI Variable 14px+ |
| **table font** | **11px** | Streamlit default (~14px) |
| **header** | **9px, 700, UPPERCASE, letter-spacing .09px** | default weight, sentence case |
| **row height** | **36px** | Streamlit default (~35px, but with far bigger type) |
| cell padding | 0 4–8px | default |
| borders | 1px hairline `#e1e8e4` | default grid lines |
| **semantics** | **tint PAIRS** — `#11795d` on `#dff1ea`, `#b43d49` on `#f8e1e3` | coloured text only, no tint |
| chips | cap badges, EMA marks, pivot zones | none |
| sticky | header **and** left columns (408 cells) | header only |
| grouped header | 7 colspan bands | none |
| tooltip | `i` on **every** column | ✅ already enforced by B-63a's test |

**The single biggest visual difference is type size.** Their table is 11px
against our ~14px — that is what makes 28 columns readable at all, and it is why
ours "looks old" at 12 columns. Second is **tint pairs**: colouring the cell, not
just the number, is what turns a wall of figures into a scannable field.

## 3 · What we should NOT copy

- **Their 9-day RVOL base.** Ours is 20-day. A 9-day mean reacts twice as fast
  and lets one prior spike deflate the ratio for a fortnight. Keeping 20 keeps
  our numbers comparable to our own history. *(Already recorded in B-63b.)*
- **Their green palette.** The desk's identity is the warm cream/amber
  `report_style.TOKENS`, and those tokens are shared with the PNG exports, cards
  and chips. Adopting their green in tables only would desynchronise the desk
  from itself. **Decision 2026-09-10: take the craft, keep the palette.**
- **1,538 rows on one page.** Their product is a screener; this desk's is a
  research surface with measured scanners behind it. A full-universe table is a
  different page, not a restyle.
- **The in-row watchlist star** — see above.
- **Stage 2 as x/7** — we have x/8 already. One scorer.

## 4 · The build, in the order it should land

1. **Theme + density** — `dataframeHeaderBackgroundColor` / `dataframeBorderColor`
   in `config.toml`, `row_height` on the shared render path, and the 9px
   uppercase header treatment. One change, every migrated table inherits it.
2. **Tint pairs** — a `tone` on `ColSpec` and a Styler builder in `columns.py`,
   so semantics are defined **once per column id** exactly like labels and
   tooltips already are. This is the B-63a rule extended to colour.
3. **Cheap columns** — CAP badge, RSI, % from 20EMA, EMA alignment chips.
4. **Notes, editable and stored, on the Scanner Hub as well as the Watchlist** —
   with **one** note store, not two.
5. **Earnings reaction group** — its own build, its own entry.

> [!warning] The trap in step 4
> The Watchlist already persists notes via `portfolio_db.update_watchlist_notes`,
> which deliberately updates the note only so an edit cannot reset `added_date`.
> Adding a second note store for the Hub would be the "Vol Spike means four
> different numbers" failure all over again — **one note per symbol, one table,
> both surfaces reading it.**
