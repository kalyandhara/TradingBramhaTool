# Pre-Open Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A "Pre-Open Analysis" desk page that reads NSE's 09:00–09:08 auction (IEP, gap, order imbalance, value), saves it daily, scores what happened after the open, and builds up a track record of gap follow-through and gap fills.

**Architecture:** Pure modules do the work: parse, screen, outcome and score, each tested against fixtures. One SQLite file (`tools/preopen.db`) holds a snapshot table and an outcome table, keyed by trade date. Two scheduled jobs fill them: a capture at 09:10 and an outcome run at 16:05. The page is a registered `desk_pages` module, so `dashboard_app.py` gains no statements. It only reads the DB, and fetches only when ↻ is pressed. Auto-refresh is limited to the 09:00–09:20 IST window.

**Tech Stack:** Python 3.14 (`C:/Users/Owner/AppData/Local/Programs/Python/Python314/python.exe`), requests through `nse_shareholding_fetch._new_session()`, pandas, sqlite3, Streamlit 1.57 (`st.fragment(run_every=…)`), yfinance through `intraday_store`, and pytest.

**Spec:** this plan carries its own spec, the section below. It comes from the 2026-10-22 gap analysis against justticks.in/pre-open-analysis.

## Spec (from the gap analysis)

- **S1 Auction data per symbol:** symbol, series, previous close, IEP, gap %, final quantity, auction value (₹), total buy qty, total sell qty, imbalance, ATO buy/sell, NSE update time.
- **S2 Universe and segment:** F&O (NSE key `FO`, 213 names on 2026-10-22) is the default. "Cash + F&O" uses key `ALL`. Index filter options: All / NIFTY 50 / NIFTY 100 / NIFTY 500, via `nse_universe.symbols()`.
- **S3 Filters:** search symbol, trade date, segment, index, direction (All/Up/Down), min |gap| %, min score (from phase 3), sort column and order.
- **S4 Ready-made screens, each shown with its count:**
  - Phase 1: All, Gap-Up, Gap-Down, High Imbalance, Liquid Auction, Institutional Flow
  - Phase 2: Gap-and-Go, IEP Retest, Fade / Trap Risk
- **S5 Summary tiles:**
  - Phase 1: universe, gap-up, gap-down, flat, auction value (₹ Cr)
  - Phase 2: follow-through %, gap-fill %, IEP-retest entries, average first-hour edge
- **S6 Per-symbol outcomes (phase 2):** open vs IEP, first-hour return, day return, followed (yes/no), gap filled (yes/no), IEP retest (hold/reject/none).
- **S7 Setup score 0–100, pattern read, plan text (phase 3).**
- **S8 Session read:** plain-English sentences built from the tiles (phase 1 auction only, phase 2 adds outcomes).
- **S9 Daily history by trade date.** Track-record rates show their sample size `n`.
- **S10 Freshness:**
  - Auto-refresh only between 09:00 and 09:20 IST.
  - Home's "never fetch on load" rule is unchanged.
  - A non-trading day shows the last session, labelled with its date.
- **S11 PA/SA deep links** per row: `?nav=predict&symbol=` and `?nav=analyze&symbol=`, the existing convention.

## Global Constraints

- New logic lives in new modules. `dashboard_app.py` gets at most +2 lines and **0** new top-level statements. Ratchets in `tools/test_monolith_ratchet.py` (MAX_LINES 11,900; MAX_MODULE_STATEMENTS 304; MAX_RAW_HTML_RENDERS 82) must still pass.
- Network access only through `nse_shareholding_fetch._new_session()` + `nse_shareholding_fetch.HEADERS`. Fetchers never raise: they return `(rows, error_str)`.
- Every threshold and weight is a **named module constant** with a comment saying it is an untested prior. None of them is tuned before the Task 10 study.
- A missing value stays `None`/NaN and shows "—" or an "absent" callout. It is never shown as 0.
- `<style>` never shares an `st.markdown` call with visible markup.
- Run tests with: `C:/Users/Owner/AppData/Local/Programs/Python/Python314/python.exe -m pytest tools/<file> -q` from the repo root.
- Browser checks go on a **fresh** `:8502` ("dashboard-fresh" in `.claude/launch.json`). The running `:8501` keeps old modules loaded.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Holiday or weekend run:** the feed returns the *previous* session. The row must be stored under the feed's own date (from `lastUpdateTime`), never under today's date. The page must label it with that date. → test in Task 2 (`test_trade_date_comes_from_feed_not_clock`).
2. **Capture before 09:08:** the auction is still forming. Rows with `updated_at` before 09:08 are saved `provisional=1`, and a later capture overwrites them. A provisional snapshot must never overwrite a final one. → Task 2 (`test_final_snapshot_is_not_overwritten_by_provisional`).
3. **No auction trade:** IEP is 0 or missing, as with illiquid or ASM names. The gap is None, the row is left out of gap and direction screens and counts, and it still counts toward the universe. → Task 1 (`test_zero_iep_gives_no_gap`), Task 4 (`test_no_gap_rows_are_in_universe_not_in_direction_counts`).
4. **NSE blocked, 403 or HTML instead of JSON:** the page shows an absent callout and the existing snapshot is kept. → Task 1 (`test_fetch_returns_error_on_non_json`), Task 3 (`test_capture_saves_nothing_on_error`).
5. **Symbols with `&` or `-`** (M&M, BAJAJ-AUTO): the Yahoo symbol is `M&M.NS`, and deep links URL-encode the symbol. → Task 6 (`test_yahoo_symbol_keeps_ampersand`), Task 5 (link column uses `urllib.parse.quote`).

---

## File Structure

| File | Responsibility |
|---|---|
| `tools/preopen.py` (new) | `AuctionRow`, `parse_preopen`, `fetch_preopen`. No Streamlit, no DB. |
| `tools/preopen_store.py` (new) | `tools/preopen.db`: snapshot and outcome tables, save/load, trade dates. |
| `tools/preopen_capture.py` (new) | CLI used by the 09:10 job: fetch FO + ALL, then save. |
| `tools/preopen_screens.py` (new) | Screens, counts, summary tiles, session-read sentences. Works on DataFrames. |
| `tools/preopen_outcomes.py` (new) | Pure outcome maths on 5-minute bars, plus the 16:05 job CLI (`main`). |
| `tools/preopen_score.py` (new) | Setup score, pattern read, plan text (phase 3). |
| `tools/preopen_score_study.py` (new) | Score-vs-edge calibration report (phase 3). |
| `tools/desk_pages/pre_open.py` (new) | The page. |
| `tools/desk_pages/__init__.py` | +1 `PAGES` entry. |
| `tools/dashboard_app.py` | Add the label to the `PAGE_GROUPS["Market Intel"]` list, and +1 `PAGE_BLURBS` line. |
| `tools/scheduler_core.py` | +2 `JobSpec`s: `preopen_capture`, `preopen_outcomes`. |
| `tools/fixtures/preopen_fo_sample.json` (new) | A trimmed real `key=FO` payload. |
| `tools/test_preopen*.py` (new) | One test file per module. |

Payload shape, confirmed live on 2026-10-22 (`GET https://www.nseindia.com/api/market-data-pre-open?key=FO`, HTTP 200, 213 rows):

```
{advances, declines, unchanged, timestamp, totalTradedValue, ..., data: [
  {metadata: {symbol, series, previousClose, iep, finalQuantity, totalTurnover, pChange, marketCap, yearHigh, yearLow, ...},
   detail: {preOpenMarket: {IEP, finalPrice, finalQuantity, totalBuyQuantity, totalSellQuantity,
                            atoBuyQty, atoSellQty, perChange, prevClose, lastUpdateTime: "22-Oct-2026 09:08:37",
                            preopen: [{price, buyQty, sellQty, iep?: true}, ...]}}}]}
```

`key=NIFTY` returned a 33-byte body, so the index filter does **not** use NSE index keys. It uses `nse_universe.symbols("nifty50"|"nifty100"|"nifty500")`.

---

# Phase 1: Auction board

### Task 1: Parse and fetch the auction feed

**Files:**
- Create: `tools/preopen.py`, `tools/fixtures/preopen_fo_sample.json`, `tools/test_preopen.py`

**Interfaces:**
- Produces:
  - `AuctionRow` (frozen dataclass) with fields: `symbol: str, series: str, prev_close: float|None, iep: float|None, gap_pct: float|None, final_qty: int|None, turnover: float|None` (₹), `buy_qty: int|None, sell_qty: int|None, imbalance: float|None` (−1..1), `ato_buy: int|None, ato_sell: int|None, updated_at: datetime|None` (naive IST).
  - `parse_preopen(payload: dict|None) -> list[AuctionRow]`
  - `fetch_preopen(key: str = "FO", session=None) -> tuple[list[AuctionRow], str|None]`
  - `PREOPEN_URL = "https://www.nseindia.com/api/market-data-pre-open?key={key}"`

- [ ] **Step 1: Capture the fixture.** Fetch `key=FO` once with `nse_shareholding_fetch._new_session()`. Keep the top-level keys and 4 `data` items: one gap-up, one gap-down, one with `IEP` set to 0, and one with `preOpenMarket` deleted. Save to `tools/fixtures/preopen_fo_sample.json`. Create `tools/fixtures/` if it is missing.
- [ ] **Step 2: Write the failing tests**

```python
def test_parses_every_item_with_a_symbol(sample): assert len(parse_preopen(sample)) == 4
def test_gap_is_iep_over_prev_close(sample):
    r = _by_sym(sample)[UP_SYM]; assert r.gap_pct == pytest.approx((r.iep / r.prev_close - 1) * 100, abs=1e-6)
def test_imbalance_is_signed_share(sample):
    r = _by_sym(sample)[UP_SYM]; assert r.imbalance == pytest.approx((r.buy_qty - r.sell_qty) / (r.buy_qty + r.sell_qty))
def test_zero_iep_gives_no_gap(sample): assert _by_sym(sample)[ZERO_SYM].gap_pct is None
def test_missing_preopen_block_keeps_symbol_with_nones(sample):
    r = _by_sym(sample)[BARE_SYM]; assert r.iep is None and r.imbalance is None and r.prev_close is not None
def test_updated_at_parsed_as_ist_naive(sample): assert _by_sym(sample)[UP_SYM].updated_at.strftime("%H:%M") == "09:08"
def test_none_payload_is_empty(): assert parse_preopen(None) == []
def test_fetch_returns_error_on_non_json():
    rows, err = fetch_preopen("FO", session=_FakeSession(text="<html>blocked</html>")); assert rows == [] and err
def test_fetch_never_raises_on_network_error():
    rows, err = fetch_preopen("FO", session=_FakeSession(raise_exc=OSError("x"))); assert rows == [] and "OSError" in err
```

- [ ] **Step 3: Run them and confirm they fail:** `python -m pytest tools/test_preopen.py -q`. Expected: ImportError.
- [ ] **Step 4: Implement.**
  - Prefer the `detail.preOpenMarket` values (IEP, prevClose, totalBuyQuantity…). Fall back to `metadata` for `prev_close`/`iep`/`final_qty`/`turnover`.
  - Compute `gap_pct` yourself. Do not trust `perChange`.
  - Use `_f()`-style coercion that strips commas, as in `index_strip._f`.
  - Parse `lastUpdateTime` with `"%d-%b-%Y %H:%M:%S"`.
  - `fetch_preopen` wraps everything in try/except and returns `([], f"{type(e).__name__}: {e}")`.
- [ ] **Step 5: Run the tests and confirm they pass.** Expected: 9 passed.
- [ ] **Step 6: Commit:** `feat(preopen): parse NSE pre-open auction feed`

### Task 2: Snapshot store

**Files:**
- Create: `tools/preopen_store.py`, `tools/test_preopen_store.py`

**Interfaces:**
- Consumes: `AuctionRow`.
- Produces:
  - `DB_PATH = TOOLS_DIR / "preopen.db"`, `init_db(db_path=DB_PATH)`
  - `FINAL_AFTER = time(9, 8)`
  - `save_snapshot(rows: list[AuctionRow], fo_symbols: set[str], *, captured_at: datetime, db_path=DB_PATH) -> tuple[str|None, int]`. Returns `(trade_date, rows_written)`.
  - `load_snapshot(trade_date: str, db_path=DB_PATH) -> pd.DataFrame`. Columns are the AuctionRow fields plus `fo: bool, provisional: bool, trade_date`.
  - `trade_dates(db_path=DB_PATH) -> list[str]`, newest first.
  - Table `auction_snapshots(trade_date TEXT, symbol TEXT, <AuctionRow fields>, fo INTEGER, provisional INTEGER, captured_at TEXT, PRIMARY KEY(trade_date, symbol))`.

- [ ] **Step 1: Write the failing tests.** They use a `tmp_path` DB, like `test_named_watchlists.py`.

```python
def test_trade_date_comes_from_feed_not_clock(db):
    d, n = save_snapshot([_row("A", updated="2026-10-21 09:08:30")], {"A"}, captured_at=datetime(2026,10,24,9,10), db_path=db)
    assert d == "2026-10-21" and trade_dates(db) == ["2026-10-21"]
def test_rerun_replaces_not_duplicates(db): ...save twice... ; assert len(load_snapshot("2026-10-21", db)) == 1
def test_before_0908_is_provisional(db): ...updated 09:05...; assert load_snapshot(d, db).provisional.all()
def test_final_snapshot_is_not_overwritten_by_provisional(db):
    save final iep=100, then provisional iep=90 for same date+symbol; assert load_snapshot(d, db).iep.iloc[0] == 100
def test_fo_flag_from_fo_set(db): rows A,B; fo_symbols={"A"}; assert dict(zip(df.symbol, df.fo)) == {"A": True, "B": False}
def test_rows_without_updated_at_are_skipped_and_empty_returns_none(db): assert save_snapshot([], set(), captured_at=..., db_path=db) == (None, 0)
```

- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement.** `trade_date` is the most common `updated_at.date()` across the rows. Write with `INSERT … ON CONFLICT(trade_date, symbol) DO UPDATE … WHERE excluded.provisional <= auction_snapshots.provisional`, so final beats provisional and final replaces final.
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 6 passed.
- [ ] **Step 5: Commit:** `feat(preopen): sqlite snapshot store keyed by feed trade date`

### Task 3: Capture CLI and 09:10 scheduled job

**Files:**
- Create: `tools/preopen_capture.py`, `tools/test_preopen_capture.py`
- Modify: `tools/scheduler_core.py` (the `JOBS` dict)

**Interfaces:**
- Consumes: `fetch_preopen`, `save_snapshot`.
- Produces: `capture(keys=("FO", "ALL"), *, fetch=fetch_preopen, now=None, db_path=DB_PATH) -> dict` with keys `{trade_date, written, fo_count, error}`, and `main(argv) -> int`.

- [ ] **Step 1: Write the failing tests:**
  - `test_capture_tags_fo_from_fo_key`: the fake fetch returns FO=[A] and ALL=[A,B]. Assert `fo_count == 1`, `written == 2`.
  - `test_capture_saves_nothing_on_error`: FO returns `([], "403")`. Assert `written == 0`, `error` contains "403", and `trade_dates` is empty.
  - `test_all_failure_still_saves_fo`: ALL errors and FO succeeds. Assert `written == len(FO)` and the error is noted.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement `capture`.**
  - FO is required: if it errors, save nothing.
  - ALL is optional: on error, save the FO rows only.
  - `main` prints one JSON line and returns 0 only when `written > 0`.
- [ ] **Step 4: Add the job:**

```python
"preopen_capture": JobSpec(id="preopen_capture", label="Pre-Open Auction Capture",
    desc="Saves NSE's 09:00–09:08 pre-open auction (FO + ALL) into preopen.db for the "
         "Pre-Open Analysis page. Safe to re-run; a non-trading day re-saves the last session under its own date.",
    task_name="TradingBramha-PreopenCapture", kind="daily",
    command=f'"{PYTHON_EXE}" "{HERE / "preopen_capture.py"}"', default_time="09:10"),
```

- [ ] **Step 5: Run the tests, then do one live run:** `python tools/preopen_capture.py`. Expected: JSON with `fo_count` ≈ 213 and `error` null.
- [ ] **Step 6: Commit:** `feat(preopen): capture CLI + 09:10 scheduler job`

### Task 4: Screens, tiles and session read (auction-only)

**Files:**
- Create: `tools/preopen_screens.py`, `tools/test_preopen_screens.py`

**Interfaces:**
- Consumes: the `load_snapshot` DataFrame.
- Produces:
  - Constants (all untested priors):
    - `FLAT_BAND_PCT = 0.25`
    - `HIGH_IMBALANCE = 0.5`
    - `LIQUID_VALUE_RS = 5e7` (₹5 Cr)
    - `INST_MIN_GAP_PCT = 1.0`, `INST_MIN_IMB = 0.3`, `INST_MIN_VALUE_RS = 1e7`
  - `Screen(key: str, label: str, desc: str, phase: int, mask: Callable[[pd.DataFrame], pd.Series])`
  - `SCREENS: dict[str, Screen]`. Phase-1 keys: `all, gap_up, gap_down, high_imbalance, liquid, institutional`.
  - `apply_screen(df, key) -> pd.DataFrame`
  - `screen_counts(df) -> dict[str, int]`. Includes only screens whose required columns exist.
  - `AuctionSummary(universe, up, down, flat, no_trade, value_cr)` and `summarise(df) -> AuctionSummary`
  - `session_read(s: AuctionSummary, outcomes: "OutcomeSummary|None" = None) -> list[str]`
  - `filter_frame(df, *, search="", direction="All", min_gap=0.0, index_members: set[str]|None=None, fo_only=True) -> pd.DataFrame`

- [ ] **Step 1: Write the failing tests.** Build the DataFrame by hand: 6 rows covering up / down / flat / no-trade / high imbalance / high value.

```python
def test_gap_up_excludes_flat_band(): assert set(apply_screen(df, "gap_up").symbol) == {"UP", "INST"}
def test_no_gap_rows_are_in_universe_not_in_direction_counts():
    s = summarise(df); assert s.universe == 6 and s.no_trade == 1 and s.up + s.down + s.flat == 5
def test_institutional_needs_aligned_imbalance(): assert "CONTRA" not in set(apply_screen(df, "institutional").symbol)
def test_value_cr_sums_turnover(): assert summarise(df).value_cr == pytest.approx(df.turnover.sum() / 1e7)
def test_counts_skip_phase2_screens_without_outcome_columns(): assert "gap_and_go" not in screen_counts(df)
def test_session_read_names_breadth(): assert "gap-down breadth" in session_read(_summary(up=14, down=183, flat=16))[0]
def test_filter_direction_and_min_gap(): assert set(filter_frame(df, direction="Down", min_gap=1.0).symbol) == {"DOWN"}
def test_filter_index_members(): assert set(filter_frame(df, index_members={"UP"}, fo_only=False).symbol) == {"UP"}
```

- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement.** Breadth wording:
  - up > 1.5 × down → "gap-up breadth"
  - down > 1.5 × up → "gap-down breadth"
  - otherwise → "mixed breadth"

  The first sentence reads: `"Auction opened with {up} gap-up, {down} gap-down and {flat} flat names: {breadth}."`
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 8 passed.
- [ ] **Step 5: Commit:** `feat(preopen): auction screens, tiles and session read`

### Task 5: Pre-Open Analysis page (phase-1 view)

**Files:**
- Create: `tools/desk_pages/pre_open.py`
- Modify: `tools/desk_pages/__init__.py` (`PAGES`: `"Pre-Open Analysis": "pre_open",`)
- Modify: `tools/dashboard_app.py`:
  - Append `"Pre-Open Analysis"` to `PAGE_GROUPS["Market Intel"]`.
  - Add a `PAGE_BLURBS` line: `"Pre-Open Analysis": "SCAN · market · NSE 09:00–09:08 auction — gap, IEP, imbalance, outcomes",`
- Test: `tools/test_preopen_page.py`

**Interfaces:**
- Consumes: `preopen_store.load_snapshot/trade_dates`, `preopen_screens.*`, `preopen_capture.capture`, `nse_universe.symbols`, `live_chrome.fresh_dot`.
- Produces:
  - `render() -> None`
  - `in_auto_window(now: datetime) -> bool` (09:00 ≤ IST time < 09:20, Mon–Fri)
  - `link_frame(df) -> pd.DataFrame`, which adds `pa`/`sa` URL columns `"?nav=predict&symbol=" + quote(sym)`

- [ ] **Step 1: Write the failing tests:**
  - `test_auto_window_bounds`: 08:59 → False, 09:00 → True, 09:19 → True, 09:20 → False, Saturday 09:05 → False.
  - `test_link_frame_encodes_ampersand`: `"M&M"` gives a `pa` value ending in `symbol=M%26M`.
  - `test_page_is_registered`: `"Pre-Open Analysis" in desk_pages.PAGES` and it is in `dashboard_app` `PAGE_GROUPS` (read the file text with `ast` the way `test_monolith_ratchet` does; do not import the app).
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement the layout, top to bottom:**
  1. Control row: trade date (selectbox over `trade_dates()`, newest first), segment (F&O / Cash + F&O), index (All / NIFTY 50 / NIFTY 100 / NIFTY 500), direction, min |gap| %, search, and a ↻ button that calls `capture()` and then `st.rerun()`.
  2. Caption with `fresh_dot`:
     - `stale` = the selected date is older than the latest weekday.
     - `live` = `in_auto_window`.
     - It shows "Session of {trade_date}" whenever that date ≠ today.
  3. Screen chips: `st.segmented_control` labels `"{label} {count}"`, phase-1 screens only.
  4. Tiles: `st.metric` ×5 from `summarise`.
  5. Session read: `st.markdown` bullets.
  6. Table: `st.dataframe` with `column_config` (₹ formats, `LinkColumn` for PA/SA, gap/imbalance as `NumberColumn` with `%.2f`).
  7. If there are no snapshots at all, show a callout: "No auction saved yet — press ↻ after 09:08 or enable Pre-Open Auction Capture in Scheduler Hub".
  8. If `capture` returns an error, show the absent callout with the error text and keep the old snapshot.

  Wrap the board in a function decorated with `st.fragment(run_every=60 if in_auto_window(now) else None)`, which calls `capture()` at most once per minute while the window is open.
- [ ] **Step 4: Run the tests plus the ratchet:** `python -m pytest tools/test_preopen_page.py tools/test_monolith_ratchet.py -q`. Expected: all pass.
- [ ] **Step 5: Browser check on a fresh :8502.**
  - Open Market Intel → Pre-Open Analysis. Universe ≈ 213, and the chips show counts.
  - Switch to Cash + F&O; the universe grows.
  - Pick NIFTY 50; at most 50 rows.
  - Click a PA link; Predictive Analysis opens on that symbol.
  - Take a phone-width screenshot (375px); no horizontal scroll.
- [ ] **Step 6: Commit:** `feat(preopen): Pre-Open Analysis desk page (auction board)`

---

# Phase 2: Outcomes after the open

### Task 6: Outcome maths on 5-minute bars

**Files:**
- Create: `tools/preopen_outcomes.py` (pure part), `tools/test_preopen_outcomes.py`

**Interfaces:**
- Consumes: a bars DataFrame shaped like `intraday_store.session_slice` output (lowercase `open, high, low, close, volume`, naive-IST index of bar-open times), and `FLAT_BAND_PCT` imported from `preopen_screens`. Do not redefine it.
- Produces:
  - `FIRST_HOUR_END = time(10, 15)`, `OPEN_BAR = time(9, 15)`
  - `Outcome` dataclass: `symbol, open_px, open_vs_iep_pct, first_hour_ret_pct, day_ret_pct, followed: bool|None, gap_filled: bool|None, iep_retest: str|None` (`"hold"|"reject"|None`), `retest_at: datetime|None, edge_1h_pct: float|None`
  - `compute_outcome(symbol, iep, prev_close, gap_pct, bars, *, flat_band=FLAT_BAND_PCT) -> Outcome`
  - `yahoo_symbol(nse: str) -> str`, which returns `nse + ".NS"`
  - `OutcomeSummary(n, follow_through_pct, gap_fill_pct, iep_entries, avg_edge_1h_pct)` and `summarise_outcomes(df) -> OutcomeSummary`

Definitions. `d` is the direction: `sign(gap_pct)`, or None inside ±`flat_band`. First-hour bars start before 10:15, and `fh_close` is the close of the last of them.

- `open_vs_iep_pct = (open_px / iep - 1) * 100`
- `first_hour_ret_pct = (fh_close / iep - 1) * 100`
- `day_ret_pct = (last close / iep - 1) * 100`
- `followed = d * (fh_close - iep) > 0`
- `gap_filled`: `d > 0` → `min(low) <= prev_close`; `d < 0` → `max(high) >= prev_close`. Over the whole session.
- `iep_retest`: the first first-hour bar after the open bar where `low <= iep <= high`. It is `"hold"` if that bar's close is on the auction side (`d * (close - iep) >= 0`), otherwise `"reject"`. None if no bar touches.
- `edge_1h_pct = d * first_hour_ret_pct`
- Flat (`d` None) → followed / gap_filled / iep_retest / edge are all None.

- [ ] **Step 1: Write the failing tests with synthetic bars:**
  - `test_gap_up_continuation_followed_no_fill`
  - `test_gap_up_filled_when_low_hits_prev_close`
  - `test_gap_down_followed_sign`, which checks that `edge_1h_pct > 0` when price falls.
  - `test_iep_retest_hold_vs_reject`: the same touch, with close above vs below the IEP.
  - `test_open_bar_touch_is_not_a_retest`
  - `test_flat_gap_gives_none_outcomes`
  - `test_empty_bars_gives_all_none_but_symbol`
  - `test_yahoo_symbol_keeps_ampersand`: `yahoo_symbol("M&M") == "M&M.NS"`
  - `test_summary_rates_ignore_none`: 3 followed, 1 not, 1 None → `follow_through_pct == 75.0`, `n == 4`.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement exactly the definitions above.**
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 9 passed.
- [ ] **Step 5: Commit:** `feat(preopen): opening-drive outcome maths (follow-through, gap fill, IEP retest)`

### Task 7: Outcome store and 16:05 job

**Files:**
- Modify: `tools/preopen_store.py`, `tools/preopen_outcomes.py` (add `run_day` + `main`), `tools/scheduler_core.py`
- Test: `tools/test_preopen_store.py`, `tools/test_preopen_outcomes.py`

**Interfaces:**
- Consumes: `load_snapshot`, `compute_outcome`, `intraday_store.fetch_and_store(symbol, "5m", period="5d")`, `intraday_store.session_slice(symbol, "5m", day, time(9,15), time(15,30))`.
- Produces:
  - `save_outcomes(trade_date: str, outcomes: list[Outcome], db_path=DB_PATH) -> int`, writing to table `auction_outcomes(trade_date, symbol, <Outcome fields>, computed_at, PK(trade_date, symbol))`. A re-run replaces rows.
  - `load_outcomes(trade_date, db_path=DB_PATH) -> pd.DataFrame`
  - `load_board(trade_date, db_path=DB_PATH) -> pd.DataFrame`: the snapshot LEFT JOIN outcomes. Outcome columns are NaN when none exist.
  - `run_day(trade_date: str, *, fetch=intraday_store.fetch_and_store, slice_=intraday_store.session_slice, fo_only=True, db_path=DB_PATH) -> dict` with keys `{n, written, missing: list[str]}`

- [ ] **Step 1: Write the failing tests:**
  - `test_load_board_left_joins_outcomes`: 2 snapshot rows, 1 outcome. 2 rows come back, and one has NaN `followed`.
  - `test_run_day_records_missing_bars`: the fake slice returns empty for "B". Assert `missing == ["B"]` and the outcome for B is still saved with Nones.
  - `test_run_day_uses_yahoo_symbol`: the fake fetch records calls, and they include `"M&M.NS"`.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement.**
  - `run_day` loops over the snapshot's symbols: F&O only by default, since ALL would be about 2,000 Yahoo calls.
  - It calls `fetch` and then `slice_`, catching per-symbol errors.
  - `main(argv)` accepts `--date YYYY-MM-DD`, defaulting to the latest `trade_dates()[0]`.
  - Add a job:

```python
"preopen_outcomes": JobSpec(id="preopen_outcomes", label="Pre-Open Outcomes",
    desc="After close, pulls 5m bars for the day's F&O auction names and scores follow-through, "
         "gap fill and IEP retest into preopen.db. Yahoo keeps 5m bars ~60 days — a missed day can "
         "be re-run with --date inside that window.",
    task_name="TradingBramha-PreopenOutcomes", kind="daily",
    command=f'"{PYTHON_EXE}" "{HERE / "preopen_outcomes.py"}"', default_time="16:05"),
```

- [ ] **Step 4: Run the tests, then do one live run** for the latest saved date: `python tools/preopen_outcomes.py`. Expected: `written` ≈ the F&O count, with a short `missing` list.
- [ ] **Step 5: Commit:** `feat(preopen): outcome store + 16:05 outcomes job`

### Task 8: Outcome screens, tiles and history on the page

**Files:**
- Modify: `tools/preopen_screens.py`, `tools/preopen_store.py`, `tools/desk_pages/pre_open.py`
- Test: `tools/test_preopen_screens.py`, `tools/test_preopen_store.py`

**Interfaces:**
- Consumes: `load_board`, `summarise_outcomes`, `OutcomeSummary`.
- Produces:
  - Phase-2 entries in `SCREENS`:
    - `gap_and_go`: |gap| ≥ `INST_MIN_GAP_PCT` & imbalance aligned & `followed` & not `gap_filled`
    - `iep_retest`: `iep_retest` notna
    - `fade_trap`: |gap| ≥ `FADE_MIN_GAP_PCT = 1.5` & (`gap_filled` | `followed == False`)
  - `preopen_store.history(db_path=DB_PATH, sessions=20) -> pd.DataFrame`, one row per trade date with columns `n, follow_through_pct, gap_fill_pct, avg_edge_1h_pct`. It lives in the store, which keeps `preopen_screens` free of DB code; its test goes in `test_preopen_store.py`.
  - `session_read(..., outcomes=OutcomeSummary)` adds two sentences: follow-through / gap-fill, and IEP entries with the first-hour lean.

- [ ] **Step 1: Write the failing tests:**
  - `test_gap_and_go_excludes_filled`
  - `test_fade_trap_includes_contra_follow`
  - `test_phase2_counts_present_with_outcome_columns`
  - `test_session_read_outcome_sentence`: input 43.2 / 52.1 gives `"43.2% of symbols followed their pre-open direction"`.
  - `test_history_orders_newest_first_and_carries_n`
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement the page changes.**
  - Show the phase-2 chips only when the board has outcome rows.
  - Before outcomes exist (same day before 16:05), the four outcome tiles show "after close" with an absent tone, never 0.
  - Add the outcome columns to the table.
  - Add an expander titled "Track record (last 20 sessions)" containing the `history` frame plus a line chart of `follow_through_pct` and `gap_fill_pct`, captioned with total `n`.
- [ ] **Step 4: Run the tests and confirm they pass. Then do a browser check on a fresh :8502** with the date from the Task 7 live run: phase-2 chips, tiles, outcome columns and history are visible.
- [ ] **Step 5: Commit:** `feat(preopen): outcome screens, tiles and track record`

---

# Phase 3: Score, read and calibration

### Task 9: Setup score, pattern read and plan text

**Files:**
- Create: `tools/preopen_score.py`, `tools/test_preopen_score.py`
- Modify: `tools/desk_pages/pre_open.py` (score / read / plan columns, min-score filter, sort by score)

**Interfaces:**
- Consumes: a `load_board` row (`pd.Series`).
- Produces:
  - `WEIGHTS = {"gap": 25, "imbalance": 25, "liquidity": 20, "followed": 15, "retest": 15}`, untested priors.
  - `setup_score(row) -> int|None`, scaled 0–100. Only the components that are present count, and the total is rescaled over their weights. Returns None if gap is None.
  - `pattern_read(row) -> str`, one of `"Gap-and-go" | "IEP retest — held" | "IEP retest — rejected" | "Fade / trap risk" | "Auction drift" | "No auction trade"`
  - `plan_text(row) -> str`

Components, each 0..1:
- gap = `min(|gap_pct| / 3, 1)`
- imbalance = `max(0, sign(gap) * imbalance)`
- liquidity = `clip(log10(turnover / 1e6) / 2, 0, 1)`. ₹10 L → 0, ₹10 Cr → 1.
- followed = 1/0
- retest = hold 1, reject 0, none 0.5

Plan text:
- Long side (d > 0): `"Above IEP ₹{iep:.2f}; invalid below prev close ₹{prev_close:.2f}"`
- Short side: mirrored.
- Flat or no trade: `"No auction edge"`.

The plan text describes context, not an order.

- [ ] **Step 1: Write the failing tests:**
  - `test_score_preopen_only_rescales`: no outcome columns, a perfect auction → 100.
  - `test_score_none_without_gap`
  - `test_contra_imbalance_scores_zero_on_that_part`
  - `test_pattern_priority`: gap filled and followed False → "Fade / trap risk", even when there was a retest.
  - `test_plan_text_mirrors_for_gap_down`
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement.** Pattern priority order: no trade → fade/trap → gap-and-go → retest held/rejected → auction drift.
- [ ] **Step 4: Run the tests and confirm they pass. Then do a browser check:** sort by score, min-score filter, and the read/plan columns are visible.
- [ ] **Step 5: Commit:** `feat(preopen): setup score, pattern read and plan text`

### Task 10: Calibration study

**Files:**
- Create: `tools/preopen_score_study.py`, `tools/test_preopen_score_study.py`

**Interfaces:**
- Consumes: every `trade_date` in `preopen.db`, plus `setup_score` computed from **pre-open components only**. This means calling `setup_score` on a row with the outcome columns dropped, so the score cannot see the result it is being tested against.
- Produces: `calibrate(db_path=DB_PATH, min_sessions=20) -> dict` with keys `{sessions, n, by_quintile: DataFrame[quintile, n, mean_edge_1h, follow_pct], spearman, verdict}`. `verdict` is one of `"INSUFFICIENT"` (fewer than `min_sessions`), `"NO EDGE"`, `"WEAK"` or `"EDGE"`, with thresholds as named constants (`EDGE_RHO = 0.10`, `WEAK_RHO = 0.05`).

- [ ] **Step 1: Write the failing tests:**
  - `test_insufficient_below_min_sessions`
  - `test_score_ignores_outcome_columns`: the same pre-open row with different outcomes gives an identical score.
  - `test_monotone_synthetic_gives_edge`
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement.** Pool all rows, cut into score quintiles, and compute Spearman rank correlation of score vs `edge_1h_pct`.
- [ ] **Step 4: Run the tests and confirm they pass.**
- [ ] **Step 5: Commit:** `feat(preopen): score-vs-first-hour-edge calibration study`
- [ ] **Step 6: After 20 or more saved sessions (not part of this build):** run `python tools/preopen_score_study.py`, write the result to the trading wiki, and run `python tools/claims_lint.py`. Adjust `WEIGHTS` only from this result. A NO EDGE result is calibration, not failure.

---

## Out of scope (deliberately)

- Home hero tile, Open=High/Low page and opening-range breakout page. These can follow once the 5-minute outcome data exists.
- Outcomes for the whole Cash universe (about 2,000 Yahoo calls a day). Cash snapshots are still saved.
- Any alerting or Telegram delivery from pre-open screens.
