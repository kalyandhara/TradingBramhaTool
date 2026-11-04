---
title: "Home — Terminal Layout Implementation Plan (B-179)"
category: analysis
tags: [ui, implementation-plan, home, watchlist, sectors]
timeframe: milestone-plan
created: 2026-10-18
updated: 2026-10-18
sources: 0
related:
  - analyses/Home-Terminal-Layout-Spec.md
  - analyses/Open-Backlog.md
---

# Home Terminal Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Home into a three-pane trading terminal (watchlist/sector rail ·
existing sections · account cards) backed by an on-disk close snapshot.

**Architecture:** Pure logic in `tools/watch_rail.py` (snapshot I/O, picker
options, rail frame). Streamlit glue in `tools/desk_pages/home_layout.py`,
reached through two lazy helpers in `desk_pages/__init__.py`. The shared header
in `dashboard_app.py` creates the panes (`Slots`) where the stat strip is
drawn today; the verdict card, strips and Home body are wrapped in
`with _slots.<pane>:` blocks so no code moves and the top-level statement
count falls.

**Tech Stack:** Python 3.14, Streamlit ≥ 1.57, pandas, pytest. Run tests from
`tools/` with `py -3 -m pytest <file> -q`.

**Spec:** `trading-wiki/wiki/analyses/Home-Terminal-Layout-Spec.md`

## Global Constraints

- Home never fetches on load: the rail reads disk only; network only on ↻.
- `test_monolith_ratchet.py` must pass: `MAX_LINES = 11_950`,
  `MAX_MODULE_STATEMENTS = 316`, `MAX_RAW_HTML_RENDERS = 85`. Add **no
  top-level statement** to `dashboard_app.py`; lower ceilings to the new
  actuals at the end (the test fails if a ceiling sits far above reality).
- No new raw-HTML `st.markdown(..., unsafe_allow_html=True)` in
  `dashboard_app.py`.
- Nothing in `desk_pages/` imports `dashboard_app`.
- Only `current_page == "Home"` changes; other pages render as today.
- Snapshot path `tools/cache/last_close.json` (already git-ignored via
  `tools/cache/`). Format:
  `{"trade_date": str|null, "saved_at": ISO str, "rows": {SYMBOL: [close, prev_close]}}`.
- Column split `[1.1, 3.4, 1]`; rail table height 520 px.
- Watchlist note for sector-rail adds: `"Home sector rail"`.
- Copy: `♥ Your watchlist (N)`, `<Sector> (N)`, `Closes as of <trade_date>`,
  `No prices yet — press ↻`, `Sector map unavailable`.
- Commit messages: `feat(b179): …`, ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. A watchlist symbol absent from the sector map and the snapshot (SME,
   BSE-only) → listed under the watchlist with blank price, no crash.
2. Snapshot file truncated or hand-edited to invalid JSON → treated as no
   prices; Home still renders.
3. Bhavcopy rows with NaN or 0 `close`/`prev_close` → skipped on write, so no
   `NaN`/`Infinity` reaches the JSON and Day % is never ±inf.
4. Filter text with regex characters (`M&M`, `BAJAJ-AUTO`, `(`) → literal
   substring match, no `re.error`.
5. Sector names containing punctuation (`Oil Gas & Consumable Fuels`) → the
   picker key is the raw sector string, never parsed back out of the label.

Each is pinned by a test in Task 1.

---

### Task 1: `watch_rail` — snapshot I/O, picker options, rail frame

**Files:**
- Create: `tools/watch_rail.py`
- Test: `tools/test_watch_rail.py`

**Interfaces:**
- Produces:
  - `CLOSES_PATH: pathlib.Path` = `Path(__file__).resolve().parent / "cache" / "last_close.json"`
  - `WATCHLIST_KEY: str = "__watchlist__"`
  - `write_closes(frame: pd.DataFrame, trade_date: str | None, path: Path = CLOSES_PATH) -> int` — rows written; never raises (logs and returns 0).
  - `read_closes(path: Path = CLOSES_PATH) -> tuple[dict[str, tuple[float, float]], str | None]` — `({}, None)` on missing/corrupt.
  - `sector_options(sector_map: dict[str, str | None], watchlist: list[str]) -> list[tuple[str, str]]` — `(label, key)` pairs.
  - `rail_frame(source: str, watchlist: list[str], sector_map: dict[str, str | None], closes: dict[str, tuple[float, float]], query: str = "") -> pd.DataFrame` — columns exactly `["Symbol", "Close", "Day %", "♥"]`.

- [ ] **Step 1: Write the failing tests** in `tools/test_watch_rail.py`

```python
import json, math
import pandas as pd
import watch_rail as wr

SMAP = {"TCS": "Information Technology", "INFY": "Information Technology",
        "HDFCBANK": "Financial Services", "ONGC": "Oil Gas & Consumable Fuels",
        "XYZ": None}

def test_write_then_read_round_trip(tmp_path):
    p = tmp_path / "c.json"
    f = pd.DataFrame({"symbol": ["TCS", "INFY"], "close": [100.0, 50.0],
                      "prev_close": [80.0, 50.0]})
    assert wr.write_closes(f, "2026-10-17", p) == 2
    rows, td = wr.read_closes(p)
    assert td == "2026-10-17" and rows["TCS"] == (100.0, 80.0)

def test_write_skips_nan_and_zero(tmp_path):
    p = tmp_path / "c.json"
    f = pd.DataFrame({"symbol": ["A", "B", "C"], "close": [float("nan"), 0.0, 10.0],
                      "prev_close": [5.0, 5.0, 0.0]})
    assert wr.write_closes(f, None, p) == 0
    assert "NaN" not in p.read_text() and "Infinity" not in p.read_text()

def test_read_missing_or_corrupt_is_empty(tmp_path):
    assert wr.read_closes(tmp_path / "nope.json") == ({}, None)
    bad = tmp_path / "bad.json"; bad.write_text('{"rows": {"TCS": [1')
    assert wr.read_closes(bad) == ({}, None)

def test_write_never_raises(tmp_path):
    assert wr.write_closes(pd.DataFrame({"x": [1]}), None, tmp_path / "c.json") == 0

def test_sector_options_order_counts_and_raw_keys():
    opts = wr.sector_options(SMAP, ["TCS", "XYZ"])
    assert opts[0] == ("♥ Your watchlist (2)", wr.WATCHLIST_KEY)
    assert opts[1:] == [("Financial Services (1)", "Financial Services"),
                        ("Information Technology (2)", "Information Technology"),
                        ("Oil Gas & Consumable Fuels (1)", "Oil Gas & Consumable Fuels")]

def test_watchlist_frame_keeps_unmapped_names_blank():
    df = wr.rail_frame(wr.WATCHLIST_KEY, ["XYZ", "TCS"], SMAP, {})
    assert list(df.columns) == ["Symbol", "Close", "Day %", "♥"]
    assert list(df["Symbol"]) == ["XYZ", "TCS"]          # source order, no prices
    assert df["♥"].all() and df["Close"].isna().all()

def test_sector_frame_marks_watched_and_sorts_by_day_pct():
    closes = {"TCS": (110.0, 100.0), "INFY": (90.0, 100.0)}
    df = wr.rail_frame("Information Technology", ["INFY"], SMAP, closes)
    assert list(df["Symbol"]) == ["TCS", "INFY"]
    assert list(df["♥"]) == [False, True]
    assert math.isclose(df.iloc[0]["Day %"], 10.0)

def test_unpriced_rows_sort_last():
    df = wr.rail_frame("Information Technology", [], SMAP, {"INFY": (90.0, 100.0)})
    assert list(df["Symbol"]) == ["INFY", "TCS"]

def test_filter_is_literal_case_insensitive():
    smap = {"M&M": "Automobile and Auto Components", "BAJAJ-AUTO": "Automobile and Auto Components"}
    df = wr.rail_frame("Automobile and Auto Components", [], smap, {}, query="m&")
    assert list(df["Symbol"]) == ["M&M"]
    assert wr.rail_frame("Automobile and Auto Components", [], smap, {}, query="(").empty
```

- [ ] **Step 2: Run to verify they fail**

Run: `py -3 -m pytest test_watch_rail.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'watch_rail'`

- [ ] **Step 3: Implement `tools/watch_rail.py`** with the signatures above.
  Module docstring in the repo's style (why the snapshot exists: no on-disk
  close cache before B-179). `write_closes`: coerce numerics, keep rows with
  both > 0, write atomically (`path.with_suffix(".tmp")` then `replace`),
  `json.dump(..., allow_nan=False)`, wrap the body in `try/except Exception`
  → `log.warning` + `return 0`. Day % = `(close - prev) / prev * 100`.
  Sector members in alphabetical order before the price sort; sort is stable
  descending on Day % with NaN last (`sort_values(na_position="last",
  kind="stable")`). Filter with `str.contains(query, case=False, regex=False)`.

- [ ] **Step 4: Run to verify they pass**

Run: `py -3 -m pytest test_watch_rail.py -q`
Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add tools/watch_rail.py tools/test_watch_rail.py
git commit -m "feat(b179): watch_rail — close snapshot, sector picker, rail frame"
```

---

### Task 2: Persist the snapshot whenever the bhavcopy loads

**Files:**
- Modify: `tools/trending_stocks.py:75-83` (`load_bhav`)
- Test: `tools/test_watch_rail.py` (append)

**Interfaces:**
- Consumes: `watch_rail.write_closes(frame, trade_date, path)`.
- Produces: `trending_stocks.load_bhav()` unchanged signature
  `-> tuple[pd.DataFrame | None, str | None]`; side effect writes `CLOSES_PATH`.

- [ ] **Step 1: Write the failing test**

```python
def test_load_bhav_writes_snapshot(tmp_path, monkeypatch):
    import trending_stocks as ts
    frame = pd.DataFrame({"symbol": ["TCS"], "close": [110.0], "prev_close": [100.0],
                          "trade_date": ["2026-10-17"]})
    monkeypatch.setattr(ts.sp, "fetch_bhavcopy_frame", lambda: frame)
    monkeypatch.setattr(wr, "CLOSES_PATH", tmp_path / "c.json")
    df, td = ts.load_bhav()
    assert td == "2026-10-17"
    assert wr.read_closes(tmp_path / "c.json")[0]["TCS"] == (110.0, 100.0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `py -3 -m pytest test_watch_rail.py::test_load_bhav_writes_snapshot -q`
Expected: FAIL — `KeyError: 'TCS'` (nothing written)

- [ ] **Step 3: In `load_bhav`, after `date` is resolved, call
  `watch_rail.write_closes(df, date, watch_rail.CLOSES_PATH)`** — import
  `watch_rail` inside the function and read `CLOSES_PATH` at call time (so the
  monkeypatch applies). A one-line comment: the snapshot is what lets Home's
  rail show prices without fetching.

- [ ] **Step 4: Run to verify it passes**

Run: `py -3 -m pytest test_watch_rail.py -q`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add tools/trending_stocks.py tools/test_watch_rail.py
git commit -m "feat(b179): load_bhav persists the close snapshot"
```

---

### Task 3: `home_layout` — panes and the left rail

**Files:**
- Create: `tools/desk_pages/home_layout.py`
- Modify: `tools/desk_pages/__init__.py` (two helpers after `render`)
- Test: `tools/test_desk_pages.py` (append)

**Interfaces:**
- Consumes: Task 1 names; `report_style.strip(cards, cols)`;
  `ui_tables.with_chart_family(df, "Symbol")` (adds an `Analyze` link column);
  `sectors.lookup() -> dict[str, str | None]`; `trending_stocks.load_bhav()`;
  `portfolio_db`'s `get_watchlist()`, `add_watchlist_symbol(sym, notes)`,
  `remove_watchlist_symbol(sym)`.
- Produces:
  - `home_layout.Slots` — `@dataclass` with `market, left, centre, right`
    (Streamlit containers).
  - `home_layout.header(cards: list[str], is_home: bool) -> Slots`
  - `home_layout.render_rail(db) -> None`
  - `desk_pages.home_header(cards, is_home) -> Slots` and
    `desk_pages.home_rail(db) -> None` — lazy `importlib` delegates, same
    pattern as `render`.

- [ ] **Step 1: Write the failing tests** (append to `test_desk_pages.py`)

```python
def test_home_layout_does_not_import_the_monolith():
    tree = ast.parse((HERE / "desk_pages" / "home_layout.py").read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        names = ([a.name for a in n.names] if isinstance(n, ast.Import)
                 else [n.module or ""] if isinstance(n, ast.ImportFrom) else [])
        assert "dashboard_app" not in names

def test_home_helpers_exist_and_home_is_not_a_registered_page():
    assert callable(desk_pages.home_header) and callable(desk_pages.home_rail)
    assert not desk_pages.handles("Home")
```

- [ ] **Step 2: Run to verify they fail**

Run: `py -3 -m pytest test_desk_pages.py -q`
Expected: FAIL — `FileNotFoundError … home_layout.py`

- [ ] **Step 3: Implement `header`**
  - Not Home: `st.markdown(rs.strip(cards, cols=5), unsafe_allow_html=True)`;
    `c = st.container()`; return `Slots(c, c, c, c)`.
  - Home: `market = st.container()`; `market.markdown(rs.strip(cards[:2], cols=2), …)`;
    `left, centre, right = st.columns([1.1, 3.4, 1], gap="small")`;
    `right.markdown(rs.strip(cards[2:], cols=1), …)`; return `Slots(market, left, centre, right)`.
  - `cards` order is fixed by `_ov_cards`: Nifty 50, vs 200 SMA, Portfolio
    P&L, Capital at Risk, Alerts Triggered.

- [ ] **Step 4: Implement `render_rail(db)`**, top to bottom:
  1. `smap = sectors.lookup()` in `try/except` → `{}`; `wl = list(db.get_watchlist()["symbol"])` (empty frame → `[]`).
  2. `opts = watch_rail.sector_options(smap, wl)`; `st.selectbox("Watch", opts, format_func=lambda o: o[0], key="home_rail_src", label_visibility="collapsed")`; `source = choice[1]`. If `not smap`: `st.caption("Sector map unavailable")`.
  3. `q = st.text_input("Filter", key="home_rail_q", placeholder="TCS", label_visibility="collapsed")`.
  4. `closes, td = watch_rail.read_closes()`; caption `Closes as of {td}` or `No prices yet — press ↻`.
  5. Empty watchlist and `source == WATCHLIST_KEY` → `st.info("Watchlist is empty — tick rows in a scan and press ♥.")` and skip the table.
  6. `frame = watch_rail.rail_frame(source, wl, smap, closes, q)`; display copy: `ui_tables.with_chart_family(frame, "Symbol")`, then `Symbol = pop("Analyze")`, keep `["Symbol", "Close", "Day %", "♥"]`. Colour Day % with a pandas `Styler.map` using `rs.tone_colors("good")[0]` / `rs.tone_colors("risk")[0]`. `st.dataframe(..., height=520, hide_index=True, key="home_rail_tbl", on_select="rerun", selection_mode="multi-row")` with `LinkColumn("Symbol", display_text=r"symbol=([^&]+)")`, `NumberColumn("Close", format="%.2f")`, `NumberColumn("Day %", format="%+.2f%%")`, `CheckboxColumn("♥")`. Map selected rows back to `frame.iloc[i]["Symbol"]`.
  7. Footer, one row of three: `↻` (key `home_rail_refresh`) → `with st.spinner(...)`: `df, _ = trending_stocks.load_bhav()`; `None` → `st.toast("Couldn't reach NSE for prices. The last snapshot stays.")`, else `st.rerun()`. Watchlist mode → `✕ Remove N` (key `home_rail_rm`) calls `db.remove_watchlist_symbol`; sector mode → `♥ Add N` (key `home_rail_add`) calls `db.add_watchlist_symbol(sym, "Home sector rail")`; both toast then `st.rerun()`. `Open Watchlist →` (key `home_wl_open`) sets `st.session_state["current_page"] = "Watchlist"` and reruns.

- [ ] **Step 5: Add the two delegates to `desk_pages/__init__.py`**: each does
  `importlib.import_module(f"{__name__}.home_layout")` and calls through. One
  docstring line: Home is not a registered page, it only borrows panes.

- [ ] **Step 6: Run to verify they pass**

Run: `py -3 -m pytest test_desk_pages.py test_watch_rail.py -q`
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add tools/desk_pages/home_layout.py tools/desk_pages/__init__.py tools/test_desk_pages.py
git commit -m "feat(b179): home_layout panes and watchlist/sector rail"
```

---

### Task 4: Wire Home into the panes in `dashboard_app.py`

**Files:**
- Modify: `tools/dashboard_app.py` — header strip (~3286), verdict block
  (~3289–3466), strips block (~3472–3476), Home branch (~5503–5737)
- Modify: `tools/test_monolith_ratchet.py:33-45` (lower ceilings)

**Interfaces:**
- Consumes: `dpages.home_header(_ov_cards, is_home) -> Slots`,
  `dpages.home_rail(db)`.

- [ ] **Step 1: Header strip.** Replace
  `st.markdown(rs.strip(_ov_cards, cols=5), unsafe_allow_html=True)` with
  `_slots = dpages.home_header(_ov_cards, current_page == "Home")`.

- [ ] **Step 2: Verdict into the centre.** Keep `_show_regime = current_page == "Home"`
  at top level; wrap every following top-level statement up to and including
  the `Set total capital` expander block in one `with _slots.centre:`
  (re-indent only, no edits inside).

- [ ] **Step 3: Strips into the market bar.** Inside the existing
  `if _show_regime:` that calls `istrip.render()` / `bstrip.render(...)` /
  `st.divider()`, wrap those three calls in `with _slots.market:`.

- [ ] **Step 4: Home branch.** Inside `if current_page == "Home":`
  - `with _slots.left: dpages.home_rail(db)`.
  - `with _slots.right:` — `st.caption("Quick actions")`, the three existing
    buttons stacked (same keys, labels, handlers; drop the `st.columns([1.15, 1, 1, 3])`),
    then the existing disclaimer markdown.
  - `with _slots.centre:` — in this order: `render_action_map()`,
    `_darvas_window("home_vs", compact=True)`, then
    `_mf, _iv = st.columns(2)` with `_money_flow_window("home_smf", compact=True)`
    in `_mf` and `_render_institutional_volume("home_iv")` in `_iv`, then
    `_render_cpr_vp("home_cpr")`, then the whole `#### 📈 What moved today`
    block unchanged.
  - Delete the `#### ♥ Watchlist` block through the `Open Watchlist →` button
    (the rail replaces it). Keep every existing explanatory comment that still
    applies; drop those that described the deleted roster.

- [ ] **Step 5: Run the structural suites**

Run: `py -3 -m pytest test_monolith_ratchet.py test_desk_pages.py -q`
Expected: line / raw-HTML / statement checks pass; the slack check may FAIL
naming the ceilings that are now too high.

- [ ] **Step 6: Lower the ceilings** in `test_monolith_ratchet.py` to the
  actuals the failure message prints, each comment reading
  `# actual N — B-179 Home terminal layout (2026-10-18)`. Re-run Step 5 →
  all pass.

- [ ] **Step 7: Full suite**

Run: `py -3 -m pytest -q -x` (from repo root, uses `pytest.ini`)
Expected: no new failures versus `master` (compare against a run on the
parent commit if anything fails).

- [ ] **Step 8: Commit**

```bash
git add tools/dashboard_app.py tools/test_monolith_ratchet.py
git commit -m "feat(b179): Home renders as three panes with the watchlist rail"
```

---

### Task 5: Verify in the browser and close the backlog row

**Files:**
- Modify: `trading-wiki/wiki/analyses/Open-Backlog.md` (B-179 status),
  `trading-wiki/wiki/log.md`

- [ ] **Step 1: Start a fresh process** — `preview_start {name: "dashboard-fresh"}`
  (port 8502; the running :8501 keeps stale modules).
- [ ] **Step 2: Cold-load check.** Delete `tools/cache/last_close.json` if
  present, load Home: rail shows `No prices yet — press ↻`;
  `read_network_requests` shows no NSE/yfinance call caused by the rail.
- [ ] **Step 3: Interactions.** Press ↻ → prices and `Closes as of …` appear.
  Switch picker to a sector → constituents with ♥ on watched names; select
  one unwatched → `♥ Add 1` → it appears under the watchlist; remove it again.
  Filter `ba` narrows rows.
- [ ] **Step 4: Layout.** Screenshot at desktop width (three panes, verdict
  first in centre, cards right); `resize_window {preset: "mobile"}` → panes
  stack rail-first; reset to desktop. Open one other page (e.g. Scanner Hub)
  → five-card strip unchanged.
- [ ] **Step 5: Wiki.** Set B-179's status to
  `built 2026-10-18 — <commit>`; add a log line under today's entry.
- [ ] **Step 6: Commit**

```bash
git add trading-wiki/wiki
git commit -m "docs(b179): Home terminal layout built and verified"
```
