---
title: "Home Rail — Hover Chart Implementation Plan (B-180)"
category: analysis
tags: [ui, implementation-plan, home, watchlist, chart, component]
timeframe: milestone-plan
created: 2026-10-18
updated: 2026-10-18
sources: 0
related:
  - analyses/Home-Rail-Hover-Chart-Spec.md
  - analyses/Home-Terminal-Layout-Spec.md
---

# Home Rail Hover Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hovering a ticker in Home's left rail opens a floating daily chart
(candles, volume, SMA 20/50) fed by the :5001 chart server.

**Architecture:** The rail's rows move from `st.dataframe` into a hand-rolled
Streamlit component (`components/watch_rail/index.html`, raw postMessage
protocol like `components/symbol_search`). The component renders rows, returns
ticked symbols, and on hover injects one chart card into the parent page using
lightweight-charts 4.1.3 and `GET :5001/api/ohlcv`. `chart_server.py` allows
that cross-port fetch for :8501/:8502 only. Pure row shaping lives in
`watch_rail.py`.

**Tech Stack:** Python 3.14, Streamlit 1.58 (components v1 `declare_component`),
Flask (chart server), vanilla JS, lightweight-charts 4.1.3 (unpkg), pytest.
Run tests from `tools/`: `py -3 -m pytest <file> -q`.

**Spec:** `trading-wiki/wiki/analyses/Home-Rail-Hover-Chart-Spec.md`

## Global Constraints

- Home never fetches on load; the chart fetch happens only after a 250 ms hover (or a tap on the chart icon).
- `dashboard_app.py` is not touched (ratchet: lines 11,900 · statements 304 · raw HTML 82).
- Nothing in `desk_pages/` imports `dashboard_app`.
- Keep every B-179 hardening guarantee: component `key` = `wr.table_key(source, query, trade_date, nonce)`; Add uses `wr.names_to_add`; ↻ via `wr.refresh_closes`; sectors via `wr.rail_sector_map`.
- Timings: open after **250 ms** hover; close **200 ms** after leaving row and card; fetch timeout **6 s**; `Esc` closes.
- Card ≈ **560 × 340 px**, `position: fixed` in the parent document; one card at a time.
- Data: `http://localhost:5001/api/ohlcv?symbol=<SYM>&timeframe=1d&bars=130`; bare NSE symbols get `.NS`; `^…` and `X.BO`/`X.NS` unchanged; < 5 bars → `Chart unavailable`.
- lightweight-charts **4.1.3** from `https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js`.
- CORS: `Access-Control-Allow-Origin` echoed only for `http://localhost:8501` and `http://localhost:8502`, only on `/api/ohlcv`, plus `Vary: Origin`.
- Copy: `Loading…`, `Chart unavailable`, `Analyze ↗`; missing prices `—`.
- Commits `feat(b180): …` ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Chart server down or slow → card shows `Chart unavailable` within 6 s; rail and page keep working.
2. Mouse sweeps fast over many rows → no fetch for rows crossed in < 250 ms; a late response for a row no longer hovered does not open/replace the card (it is still cached).
3. Streamlit rerun (tick a box, switch source) while a card is open → card removed; no orphan card or duplicate script tags in the parent page.
4. A symbol whose `/api/ohlcv` returns `{"error": …}` or an empty `bars` → `Chart unavailable`, not a JS exception that kills hover for other rows.
5. Unknown `Origin` (e.g. another local app) → no CORS header, so other pages can't read the API.

Items 1, 2, 3, 4 are pinned by Task 5's browser checklist (JS has no unit harness in this repo); item 5 by Task 2's test.

---

### Task 1: Row shaping for the component

**Files:**
- Modify: `tools/watch_rail.py` (append)
- Test: `tools/test_watch_rail.py` (append)

**Interfaces:**
- Consumes: `rail_frame(...) -> DataFrame["Symbol","Close","Day %","♥"]`, `WATCHLIST_KEY`.
- Produces:
  - `chart_symbol(sym: str) -> str`
  - `rail_rows(frame: pd.DataFrame, source: str) -> list[dict]` — each `{"symbol": str, "close": float|None, "day_pct": float|None, "watched": bool|None, "chart": str}`; `watched` is `None` in watchlist mode.

- [ ] **Step 1: Write the failing tests**

```python
def test_chart_symbol_suffix_rule():
    assert wr.chart_symbol("TCS") == "TCS.NS"
    assert wr.chart_symbol(" tcs ") == "TCS.NS"
    assert wr.chart_symbol("^NSEI") == "^NSEI"
    assert wr.chart_symbol("MARINE.BO") == "MARINE.BO"

def test_rail_rows_are_json_safe_and_mode_aware():
    import json
    closes = {"TCS": (110.0, 100.0)}
    f = wr.rail_frame("Information Technology", ["INFY"], SMAP, closes)
    rows = wr.rail_rows(f, "Information Technology")
    assert [r["symbol"] for r in rows] == ["TCS", "INFY"]
    assert rows[0]["close"] == 110.0 and math.isclose(rows[0]["day_pct"], 10.0)
    assert rows[1]["close"] is None and rows[1]["day_pct"] is None
    assert [r["watched"] for r in rows] == [False, True]
    assert rows[0]["chart"] == "TCS.NS"
    json.dumps(rows, allow_nan=False)            # no NaN reaches the browser
    wl = wr.rail_rows(wr.rail_frame(wr.WATCHLIST_KEY, ["INFY"], SMAP, {}), wr.WATCHLIST_KEY)
    assert wl[0]["watched"] is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `py -3 -m pytest test_watch_rail.py -q -k "chart_symbol or rail_rows"`
Expected: FAIL — `AttributeError: module 'watch_rail' has no attribute 'chart_symbol'`

- [ ] **Step 3: Implement both in `tools/watch_rail.py`.** `chart_symbol`: strip + upper; return as-is when it starts with `^` or contains `.`, else append `.NS` (same rule as `ui_tables.chart_url`). `rail_rows`: iterate `frame` in order; NaN → `None` via `math.isnan`; `watched` from the `♥` column unless `source == WATCHLIST_KEY`.

- [ ] **Step 4: Run to verify they pass**

Run: `py -3 -m pytest test_watch_rail.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tools/watch_rail.py tools/test_watch_rail.py
git commit -m "feat(b180): rail_rows and chart_symbol for the rail component"
```

---

### Task 2: CORS for `/api/ohlcv` on the chart server

**Files:**
- Modify: `tools/chart_server.py` (one `@app.after_request` function near the other app setup, after `sock = Sock(app)`)
- Test: `tools/test_chart_server_cors.py` (new)

**Interfaces:**
- Produces: `chart_server.ALLOWED_ORIGINS: frozenset[str]` = `{"http://localhost:8501", "http://localhost:8502"}`; hook `_cors_for_ohlcv(resp)`.

- [ ] **Step 1: Write the failing tests** (no network: `/api/ohlcv` without `symbol` returns 400 before any fetch)

```python
"""CORS on /api/ohlcv for the Home rail's hover chart (B-180).

    py -3 -m pytest tools/test_chart_server_cors.py -q
"""
import chart_server as cs

def _get(path, origin):
    with cs.app.test_client() as c:
        return c.get(path, headers={"Origin": origin})

def test_desk_origin_is_echoed_on_ohlcv():
    for o in ("http://localhost:8501", "http://localhost:8502"):
        r = _get("/api/ohlcv", o)
        assert r.status_code == 400
        assert r.headers.get("Access-Control-Allow-Origin") == o
        assert "Origin" in r.headers.get("Vary", "")

def test_unknown_origin_gets_no_header():
    r = _get("/api/ohlcv", "http://evil.localhost:9999")
    assert "Access-Control-Allow-Origin" not in r.headers

def test_other_routes_get_no_header():
    r = _get("/manifest.webmanifest", "http://localhost:8501")
    assert "Access-Control-Allow-Origin" not in r.headers
```

- [ ] **Step 2: Run to verify they fail**

Run: `py -3 -m pytest test_chart_server_cors.py -q`
Expected: FAIL on the first test — header is `None`

- [ ] **Step 3: Add `ALLOWED_ORIGINS` and `@app.after_request def _cors_for_ohlcv(resp)`**: when `request.path == "/api/ohlcv"` and `request.headers.get("Origin") in ALLOWED_ORIGINS`, set `Access-Control-Allow-Origin` to that origin and add `Origin` to `Vary`; return `resp`. Comment: why only this route and only these origins (the desk reads candles; nothing else should).

- [ ] **Step 4: Run to verify they pass**

Run: `py -3 -m pytest test_chart_server_cors.py test_chart_routes.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tools/chart_server.py tools/test_chart_server_cors.py
git commit -m "feat(b180): chart server allows the desk to read /api/ohlcv cross-port"
```

---

### Task 3: The `watch_rail` component

**Files:**
- Create: `tools/components/watch_rail/index.html`
- Test: `tools/test_desk_pages.py` (append)

**Interfaces:**
- Args (from Python): `rows` (Task 1 dicts), `show_heart: bool`, `good: str`, `risk: str` (hex colours), `chart_api: str` (`"http://localhost:5001/api/ohlcv"`), `analyze_base: str` (`ui_tables.DASHBOARD_BASE + "/?nav=analyze&symbol="`), `height: int` (520).
- Value (to Python): `{"picked": [symbol, …]}` — set on every checkbox change.

- [ ] **Step 1: Write the failing test**

```python
def test_watch_rail_component_ships():
    """B-180: the rail's rows are a component; its folder must ship index.html
    or home_layout falls back to the hover-less table."""
    html = (HERE / "components" / "watch_rail" / "index.html").read_text(encoding="utf-8")
    assert "streamlit:componentReady" in html
    assert "lightweight-charts@4.1.3" in html
    assert "/api/ohlcv" not in html          # the URL comes from Python (chart_api arg)
```

- [ ] **Step 2: Run to verify it fails**

Run: `py -3 -m pytest test_desk_pages.py -q -k component_ships`
Expected: FAIL — `FileNotFoundError`

- [ ] **Step 3: Write `index.html`.** Decisions the implementer cannot infer:
  - **Protocol:** copy `send / setHeight / setValue` and the `message` listener shape from `components/symbol_search/index.html`; `componentReady` with `apiVersion: 1`; `setHeight(args.height)` on each render.
  - **Rows:** a scrolling `<div>` of rows styled like the dataframe it replaces (sticky header `Symbol · Close · Day % · [♥]`, 30 px rows, 12 px font, Close `toFixed(2)`, Day % `±x.xx%` coloured `good`/`risk`, `—` for `null`). Symbol is an `<a target="_blank">` to `analyze_base + encodeURIComponent(symbol)`. Each row ends with a 16 px chart-icon button (`title="Chart"`). Re-render rows only when `JSON.stringify(args.rows)` changed; keep ticks in a `Set` that resets when rows change.
  - **Card host:** on first need, in `const P = window.parent.document`, create once `<div id="tb-hover-card">` (fixed, z-index 10000, hidden) and, if `window.parent.LightweightCharts` is undefined and no `script#tb-lwc` exists, append `<script id="tb-lwc" src="…4.1.3…">` to `P.head`; await its `load`. Build charts with `window.parent.LightweightCharts.createChart(container, …)`.
  - **Card layout:** header line (symbol, `Daily`, O H L C of the last bar, % vs previous bar's close coloured good/risk, `Analyze ↗` link); chart area fills the rest; candle series up=`good` down=`risk`; volume histogram on its own price scale with `scaleMargins {top: 0.8, bottom: 0}`; SMA 20 and SMA 50 line series (thin, two neutral colours) computed in JS from closes, starting at bar index n-1.
  - **Positioning:** `fr = window.frameElement.getBoundingClientRect()`, row rect from the iframe; left = `fr.right + 8`, top = `fr.top + row.top`, then clamp into `window.parent.innerWidth/innerHeight` (flip up if it would overflow the bottom).
  - **Timers:** `mouseenter` on a Symbol cell starts a 250 ms open timer for that symbol; `mouseleave` of row or card starts a 200 ms close timer; `mouseenter` on the card cancels the close timer. A token per open request: when a fetch resolves, render only if its token is still current.
  - **Fetch:** `AbortController` with 6 s timeout; cache `Map(symbol → bars)` for the session (cache errors as `null` for 60 s, then retry). Treat non-OK status, `data.error`, or `bars.length < 5` as unavailable.
  - **Touch:** if `matchMedia("(hover: none)").matches`, the chart-icon click toggles the card; a `pointerdown` outside closes it.
  - **Cleanup:** on every `streamlit:render` and on `pagehide`, hide the card and `chart.remove()`; `Esc` (listener on both documents) closes it. Never leave two `#tb-hover-card` elements.

- [ ] **Step 4: Run to verify it passes**

Run: `py -3 -m pytest test_desk_pages.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tools/components/watch_rail/index.html tools/test_desk_pages.py
git commit -m "feat(b180): watch_rail component — rows, selection, hover chart card"
```

---

### Task 4: Use the component in the rail

**Files:**
- Modify: `tools/desk_pages/home_layout.py` (the `st.dataframe` block inside `render_rail`, ~lines 96–131)

**Interfaces:**
- Consumes: Task 1 `wr.rail_rows`, Task 3 args/value, `uit.DASHBOARD_BASE`, `rs.tone_colors`.
- Produces: `_rail_component()` (cached declare, `None` if the folder is missing), `_rail_table_fallback(frame, source, key) -> list[str]` (today's `st.dataframe` code moved verbatim).

- [ ] **Step 1: Move the current `st.dataframe` block, unchanged, into `_rail_table_fallback(frame, source, key) -> list[str]`** returning `picked`. Run `py -3 -m pytest test_desk_pages.py test_watch_rail.py -q` → pass.
- [ ] **Step 2: Add `_rail_component()`** — `components.declare_component("tb_watch_rail", path=<HERE>/components/watch_rail)` inside `try`, memoised in a module global; on failure `log.warning` and return `None`.
- [ ] **Step 3: In `render_rail`**, when `_rail_component()` is not `None`: call it with `rows=wr.rail_rows(frame, source)`, `show_heart=source != wr.WATCHLIST_KEY`, `good`/`risk` from `rs.tone_colors(...)[0]`, `chart_api="http://localhost:5001/api/ohlcv"`, `analyze_base=uit.DASHBOARD_BASE + "/?nav=analyze&symbol="`, `height=520`, `key=wr.table_key(source, query, trade_date, st.session_state.get("home_rail_nonce", 0))`, `default={"picked": []}`; `picked = [s for s in value.get("picked", []) if s in set(frame["Symbol"])]`. Otherwise `picked = _rail_table_fallback(...)` with the same key.
- [ ] **Step 4: Run**

Run: `py -3 -m pytest test_desk_pages.py test_watch_rail.py test_monolith_ratchet.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tools/desk_pages/home_layout.py
git commit -m "feat(b180): Home rail renders through the watch_rail component"
```

---

### Task 5: Browser verification and wiki

**Files:**
- Modify: `trading-wiki/wiki/analyses/Open-Backlog.md` (B-180 status), `trading-wiki/wiki/log.md`

- [ ] **Step 1:** Restart the chart server so it has the CORS hook (`preview_stop`/`preview_start` name `chart`, or confirm via `curl -sI -H "Origin: http://localhost:8502" "http://localhost:5001/api/ohlcv"` showing the header). Start a fresh `dashboard-fresh` (:8502).
- [ ] **Step 2: Hover:** rest on a ticker → card with candles, volume, two SMA lines and the OHLC header within ~1 s; leave → closes; hover same ticker again → instant; move onto the card → stays, crosshair moves.
- [ ] **Step 3: Review Focus 2–4:** sweep quickly across 10 rows → `read_network_requests` shows at most the final row's fetch; tick a box while a card is open → card gone after the rerun and `document.querySelectorAll('#tb-hover-card').length === 1`, `script#tb-lwc` count 1; hover a symbol that errors (e.g. type a junk symbol via devtools fetch check, or one with no data) → `Chart unavailable`, other rows still open charts.
- [ ] **Step 4: Review Focus 1:** stop the chart server → hover → `Chart unavailable` within 6 s; restart it.
- [ ] **Step 5: Rail behaviour unchanged:** tick → `✕ Remove 1`; switch to a sector → ticks cleared, `♥ Add` shows without a count; filter narrows rows; mobile preset → chart icon opens the card. Do not press Add/Remove.
- [ ] **Step 6: Wiki** — B-180 status `built 2026-10-18 — <commit range>`; log line; commit `docs(b180): hover chart built and verified`.
