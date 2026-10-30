---
title: "Home Rail — Hover Chart Popup Spec (B-180)"
category: analysis
tags: [ui, presentation-spec, home, watchlist, chart, component]
timeframe: milestone-plan
created: 2026-10-18
updated: 2026-10-18
sources: 0
related:
  - analyses/Home-Terminal-Layout-Spec.md
  - analyses/Open-Backlog.md
---

# Home Rail — Hover Chart Popup Spec (B-180)

## Thesis
Hovering a ticker in Home's left rail (B-179) opens a Chartink-style floating
chart card: daily candles, volume and 20/50 SMA. It's for the glance "is this
worth a look", not analysis — clicking the ticker still opens Stock Analyzer.

Owner decisions (2026-10-18): popup content = **candles + volume + SMA**;
design approved; hardening branch (`51a8bdc`) merged first (`2ab7e02`).

## Why the rail's table has to change
`st.dataframe` draws on a canvas (glide-data-grid) and reports no hover to
Python or to page scripts. A hover feature therefore needs the rail's ROWS to
be HTML the page controls. The rows become a small custom component; the
picker, filter, caption and footer buttons stay Streamlit widgets.

## Rules this must keep
1. **Home never fetches on load.** The chart fetch happens only on hover (a
   user action), per symbol, cached in the browser for the session.
2. Everything B-179 + its hardening guarantee still holds: selection resets on
   source / filter / snapshot date / completed action (`wr.table_key` nonce);
   Add skips already-watched names (`wr.names_to_add`); ↻ toasts; disk-only
   sector map; the rail can't blank the centre pane.
3. No new top-level statement or raw-HTML render in `dashboard_app.py`
   (`test_monolith_ratchet`). All new code lives in `desk_pages/home_layout.py`,
   `watch_rail.py`, the component folder and `chart_server.py`.
4. Nothing in `desk_pages/` imports `dashboard_app`.

## Behaviour

**Rows** (component, fixed height 520 px, scrolls inside itself):
checkbox · Symbol (link → Stock Analyzer, same `analyze_url` as today, new
tab) · Close · Day % (green / red, `—` when missing) · ♥ (sector mode only) ·
a small chart icon. Same order and data as `wr.rail_frame`.

**Popup trigger**
- Desktop: pointer rests on a row's Symbol cell for **250 ms** → card opens.
  Leaving both the row and the card for **200 ms** closes it. Moving onto the
  card keeps it open (crosshair works). `Esc` closes it.
- Touch / no hover (`matchMedia("(hover: none)")`): the chart icon toggles
  the card; tapping outside closes it.
- One card at a time; hovering another ticker replaces it.

**Card** (~560 × 340 px, `position: fixed` in the parent page so the narrow
component frame can't clip it; placed to the right of the rail, clamped to the
viewport, flipped above/below to stay on screen):
- Header: `SYMBOL · Daily · O … H … L … C … · +x.xx%` (last bar vs previous
  close; green/red), plus an `Analyze ↗` link.
- Body: lightweight-charts **4.1.3** (the version `chart_dashboard.html`
  already loads from unpkg): candlesticks, volume histogram in the bottom
  ~20 %, SMA 20 and SMA 50 lines computed in the browser from the closes.
  ~130 daily bars (≈ 6 months), so SMA 50 has ~80 points.
- Colours from the desk's tones (`rs.tone_colors("good"/"risk")`), passed to
  the component as args, so the card matches the rest of the page.
- States: `Loading…` while fetching; `Chart unavailable` + the Analyze link
  when the server is down, errors, or returns < 5 bars.

**Data**
`GET http://localhost:5001/api/ohlcv?symbol=<SYM>.NS&timeframe=1d&bars=130`
→ `{symbol, timeframe, bars:[{time, open, high, low, close, volume}], prev_close, source}`
(verified 2026-10-18). Bare NSE symbols get `.NS` — the same rule as
`ui_tables.chart_url`. The chart server is started by the desk if it isn't up
(`_chart_server_autostart`); the popup never starts it.

`chart_server.py` gains one `after_request` hook adding
`Access-Control-Allow-Origin` for **`/api/ohlcv` only**, echoing the request's
`Origin` when it is `http://localhost:8501` or `http://localhost:8502`
(nothing for other origins). The component's frame is served by Streamlit, so
without this the browser blocks the cross-port fetch.

**Selection round-trip**
The component returns `{"picked": [symbols…]}` via `setComponentValue`; Python
feeds it to the existing Remove / Add buttons. The component's `key` is
`wr.table_key(...)`, so a changed source, filter, snapshot date or a completed
action gives a fresh component with nothing ticked — the hardening rule.

## Modules
- `tools/components/watch_rail/index.html` — new component (plain HTML/JS,
  Streamlit's raw postMessage protocol, as `components/symbol_search` does).
  Renders rows, owns hover/tap, injects the card + lightweight-charts into
  `window.parent.document` once (same-origin; the repo already reaches into
  the parent for the movers scroll and ⌘K binding).
- `tools/watch_rail.py` — pure helpers: `rail_rows(frame, source) -> list[dict]`
  (JSON-safe rows: NaN → None, ♥ only in sector mode, `chart_symbol`),
  `chart_symbol(sym) -> str` (`.NS` rule). SMAs are computed in the
  browser, so there is no Python SMA helper.
- `tools/desk_pages/home_layout.py` — declares the component (lazily, like the
  rest of the module), replaces the `st.dataframe` block, falls back to the
  current `st.dataframe` if the component folder is missing.
- `tools/chart_server.py` — the CORS hook.

## Errors and edges
- Component folder missing → fall back to today's `st.dataframe` rail (no
  hover), log a warning.
- Chart server down / slow → card shows `Chart unavailable` after a **6 s**
  fetch timeout; the rail itself is unaffected.
- Symbol with no NSE data (BSE-only) → whatever `/api/ohlcv`'s own fallback
  chain returns; < 5 bars → `Chart unavailable`.
- Fast mouse sweep over many rows → the 250 ms delay means no fetch for rows
  merely crossed; an in-flight fetch for a row no longer hovered is ignored
  when it lands (results still cached).
- Page rerun while a card is open → card is removed on the component's next
  render (no orphaned card in the parent page).

## Testing
- `tools/test_watch_rail.py`: `rail_rows` — NaN → None, ♥ present only in
  sector mode, order preserved, `chart_symbol` (`TCS`→`TCS.NS`, `^NSEI`
  unchanged, `X.BO` unchanged).
- `tools/test_chart_server_cors.py` (Flask test client): `/api/ohlcv` with
  `Origin: http://localhost:8501` echoes it; an unknown origin gets no
  header; another route gets no header.
- `tools/test_desk_pages.py`: component folder exists with `index.html`;
  `home_layout` still imports no monolith.
- Browser check on a fresh :8502 with the chart server up: hover → card with
  candles/volume/SMA within ~1 s; leave → closes; second hover of the same
  symbol is instant (cached); chart server stopped → `Chart unavailable`;
  selection → Remove/Add counts update; switching source clears ticks;
  mobile preset → chart icon opens the card. Don't press Add/Remove against
  the real watchlist.

## Out of scope
Popups on other tables (Scanner Hub, Opportunity Hub, …); indicator panes
(ADX, OBV-MACD); timeframe switch in the card; intraday/live candles.
