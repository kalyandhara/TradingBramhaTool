---
title: "Home — Terminal Layout Spec (left watchlist rail · sector picker · three panes)"
category: analysis
tags: [ui, presentation-spec, home, watchlist, sectors, layout, dashboard]
timeframe: milestone-plan
created: 2026-10-18
updated: 2026-10-18
sources: 0
related:
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/Open-Backlog.md
  - analyses/Home-Terminal-Layout-Plan.md
---

# Home — Terminal Layout Spec (B-179)

## Thesis
Home should read like a trading terminal (Kite / TradingView): a **scrollable
watchlist pinned on the left**, with one picker that switches it between *your
watchlist* and *any sector's constituents*, and the existing Home content laid
out around it. **Every section Home shows today keeps a place; nothing is
dropped.** Layout and one small data cache only — no scan, score or verdict
changes.

Owner decisions (2026-10-18): picker = **both** (watchlist + sectors);
prices = **cached close + ↻ on demand**; three-pane layout **approved**.

## Rules this must keep
1. **Home never fetches on load** (existing rule). The rail reads disk only;
   the network is touched only by ↻.
2. **No new raw HTML and no net growth in `dashboard_app.py`** —
   `test_monolith_ratchet` ceilings (lines, raw-HTML renders) must still pass.
   New code goes in a new module, following `desk_pages/stock_panels.py`.
3. **Other pages are unchanged.** Only `current_page == "Home"` gets the
   new layout; every other page keeps today's header.

## Layout

```
┌ top ribbon nav (unchanged) ─────────────────────────────────────────────┐
├ market bar: index strip + breadth · Nifty 50 card · vs 200 SMA card ───┤
├──────────────┬───────────────────────────────────────┬─────────────────┤
│ LEFT RAIL    │ CENTRE                                │ RIGHT RAIL      │
│ ~1.1         │ ~3.4                                  │ ~1              │
│ picker ▾     │ regime + today's verdict card         │ Portfolio P&L   │
│ filter       │ action map                            │ Capital at risk │
│ rows (scroll)│ volume shockers (Darvas)              │ Alerts triggered│
│ ↻ · ♥/✕ ·    │ sector money flow │ institutional vol │ quick actions:  │
│ Open →       │ CPR / volume profile                  │  screener dash  │
│              │ what moved today (Load on click)      │  top movers     │
│              │                                       │  Scanner Hub    │
└──────────────┴───────────────────────────────────────┴─────────────────┘
```

`st.columns([1.1, 3.4, 1])`. Below Streamlit's column breakpoint the panes
stack in source order: rail, centre, right.

### Where each existing piece goes

| Today (Home) | Goes to | Change |
|---|---|---|
| Index strip + breadth (`istrip.render`) | market bar | none |
| Stat cards: Nifty 50, vs 200 SMA | market bar | rendered beside the strip |
| Stat cards: Portfolio P&L, Capital at risk, Alerts triggered | right rail | stacked, one per row |
| Regime + verdict card | centre, first | none |
| CTA row (screener dashboard / top movers / Scanner Hub) | right rail, "Quick actions" | same keys, same handlers |
| Action map | centre | none |
| Volume shockers (Darvas window) | centre | none |
| Sector money flow + Institutional volume | centre, side by side | two inner columns |
| CPR / VP | centre | none |
| What moved today | centre, last | stays lazy (Load / Hide) |
| ♥ Watchlist roster (bottom of Home) | **left rail** | absorbed, so it is not shown twice |

The five-card strip is built once (`_ov_cards`) and today rendered as one
`rs.strip(cols=5)`. Home renders the same cards split 2 + 3; other pages keep
`cols=5`.

## Left rail

**Picker** (`st.selectbox`, key `home_rail_src`):
`♥ Your watchlist (N)` first, then every canonical NSE sector, alphabetical,
with its constituent count (`Banks (41)`). Choice persists in session state.

- *Watchlist* → `db.get_watchlist()`, order as today (newest first).
- *Sector* → symbols whose label in `sectors.lookup()` (the monthly cached
  map, universe `niftytotalmarket`, ~750 names) equals that sector. Names you
  already watch carry ♥.
- Symbols with no NSE sector (outside the universe) appear only under the
  watchlist, as today.

**Filter** (`st.text_input`): case-insensitive substring on symbol.

**Rows** (`st.dataframe`, fixed height ≈ 520 px, so it scrolls inside the
rail): `Symbol` (link → Stock Analyzer, the same `?symbol=` link the roster
uses now) · `Close` · `Day %` (green/red) · `♥`. Sorted by Day % descending
when prices exist; otherwise in source order.

**Footer:**
- `↻` — refresh prices (below).
- Watchlist mode: `✕ Remove N` for selected rows (as today).
  Sector mode: `♥ Add N` for selected rows → `db.add_watchlist_symbol(sym,
  "Home sector rail")`.
- `Open Watchlist →` (as today).

## Prices — the cache this needs

**Finding (2026-10-18):** no closing-price cache exists on disk. The whole-
market bhavcopy (`screener_pipeline.fetch_bhavcopy_frame`, ~2,600 EQ rows, one
free NSE file) is fetched into memory by `_trend_bhav` (`st.cache_data`, 15
min) and never persisted. On a cold start the rail would have no prices.

**Design:** a tiny snapshot file, `tools/cache/last_close.json`:
`{"trade_date": "...", "saved_at": "...", "rows": {SYMBOL: [close, prev_close]}}`.

- **Written** whenever a bhavcopy frame is loaded — in `trending_stocks.
  load_bhav()`, so volume shockers, What moved today and ↻ all refresh it
  for free. Write failures are logged, never raised.
- **Read** by the rail on every render (disk only, no fetch).
- **↻** calls `trending_stocks.load_bhav()` once (one NSE request for the
  whole market), which rewrites the file, then reruns. (`_trend_bhav`'s
  in-memory copy lives in `dashboard_app` and is left to expire on its 15-min
  TTL — `desk_pages` must not import the monolith.) It does **not**
  pull per-symbol intraday quotes: during market hours Close is the last
  published bhavcopy (end of the previous session) and the rail says so —
  caption `Closes as of <trade_date>`.
- No file yet → Close / Day % show `—` and the caption reads
  `No prices yet — press ↻`.

Intraday LTP is out of scope (it would mean a per-symbol quote fetch for up
to ~750 names); revisit only if the owner asks.

## Modules

- `tools/watch_rail.py` — **pure logic, no Streamlit**:
  `sector_options(sector_map, watchlist) -> list[(label, key)]`,
  `rail_frame(source, watchlist_df, sector_map, closes, query) -> DataFrame`,
  `read_closes(path) / write_closes(frame, path)`.
- `tools/desk_pages/home_rail.py` — `render_home_rail(db)`: Streamlit
  widgets around `watch_rail`.
- `dashboard_app.py` — Home branch becomes three columns that call the
  existing renderers; the old watchlist block (≈ 50 lines) moves out; the
  header strip splits on Home. Net lines must not grow.
- `trending_stocks.load_bhav` — one call to `watch_rail.write_closes`.

## Errors and edges
- Empty watchlist → rail shows the current hint ("tick rows in a scan and
  press ♥") and the picker still offers sectors.
- `sectors.lookup()` empty (cache unreadable) → picker shows only the
  watchlist; caption `Sector map unavailable`.
- Symbol in the snapshot missing from the watchlist/sector → ignored; symbol
  in the list missing from the snapshot → `—`.
- ↻ failure (NSE down) → `st.toast` with the reason; the old snapshot stays.

## Testing
- `tools/test_watch_rail.py`: option ordering and counts; watchlist vs sector
  frames; ♥ marking; filter; sort with and without prices; snapshot
  round-trip; missing/corrupt snapshot → empty, no raise.
- Existing suites stay green, including `test_monolith_ratchet` and
  `test_desk_pages`.
- Browser check on a **fresh :8502** process (the running :8501 keeps stale
  modules): cold load makes no network call from the rail; picker switches;
  ↻ fills prices; Remove/Add work; phone width stacks rail first; other pages
  unchanged.

## Out of scope
Intraday live quotes; a chart pane in the centre; changing any section's
content; new sectors vocabulary (NSE macro stays canonical, per `sectors.py`).
