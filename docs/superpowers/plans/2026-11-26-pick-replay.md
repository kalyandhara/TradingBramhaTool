# Pick Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A "Pick replay" view on Recommendation Audit: for one past pick, the chart as it looked on the pick day beside what happened since, a one-line result footer, and a Target/SL scorecard for the filtered picks.

**Architecture:** A new pure module `tools/rec_audit_replay.py` turns one episode row + cached daily bars into a replay frame, footer text, scorecard and a Plotly figure (no Streamlit, fully testable). `rec_audit_job.bars_for` reads `price_bars` only. `desk_pages/rec_audit_page.py` adds a "Pick replay" tab and a Replay button (large `st.dialog`) on post-mortem cards, both rendering the same view.

**Tech Stack:** Python 3.14, pandas, Plotly 6.8 (`make_subplots`, `go.Candlestick`), Streamlit 1.58, pytest (`pytest.ini` → `testpaths = tools`).

**Spec:** `docs/superpowers/specs/2026-11-26-pick-replay-design.md`

## Global Constraints

- Never fetch on page open — read `rec_audit.db › price_bars` only; NIFTY 500 is `rec_audit_job.MARKET` (`"^CRSLDX"`) in the same table.
- Pick-day panel never shows a bar dated after `rec_date` (hindsight leak). Post-pick bars are `index > rec_date`, matching `rec_audit.episode_outcome`.
- Winner = headline excess vs NIFTY 500 ≥ **+5.0%** (`WIN_EXCESS_PCT = 5.0`). Loser = `failure` true with a headline return.
- Pick-day lookback = **60** sessions; volume average = **20** sessions.
- Ambiguous plan outcome counts as SL hit. No cost-to-cost category.
- Footer format: `₹312.00 → ₹523.00 (+67.63%) · Target hit day 14 · exited ₹480.00 (+53.85%)`.
- Scorecard format: `Total N · Target hit T · SL hit S · Neither X · No plan P · Pending Q`.
- No text may render `nan`/`None` for a missing field — show `—` or omit.
- Colours from `report_style.TOKENS` (`good`, `risk`, `accent`, `info`, `text_muted`, `border`).
- Python: `C:/Users/Owner/AppData/Local/Programs/Python/Python314/python.exe` (bash: `/c/Users/Owner/AppData/Local/Programs/Python/Python314/python.exe`), run from repo root.

## Review Focus

1. **Symbol with no cached bars** (renamed/delisted) → `replay_frame(...)["missing"]` names the symbol; the page shows an info line, no exception. *(Task 1 test `test_missing_bars`)*
2. **Pending pick** (no session after `rec_date`) → `post` empty, footer `Picked at ₹X · not entered yet`, figure still draws the pick-day panel. *(Task 1 `test_pending_pick`, Task 2 `test_figure_pending`)*
3. **Suspected split/bonus** (`data_suspect_date` set) → `post` cut before that date, `frame["note"]` says so; no fake −50% crash on the chart. *(Task 1 `test_data_suspect_cut`)*
4. **NIFTY 500 missing or gappy** → `bench` is `None` when `^CRSLDX` is absent, forward-filled over `post` dates when gappy; no crash. *(Task 1 `test_bench_absent_and_gappy`)*
5. **Short history / NaN fields** (early pick, fewer than 20 prior sessions, `stop` NaN, `family_names` NaN, zero volume) → `rvol` `None`, footer `No plan`, no `nan` in any text. *(Task 1 `test_short_history_and_nans`)*

---

### Task 1: Pure replay frame, footer and scorecard

**Files:**
- Create: `tools/rec_audit_replay.py`
- Modify: `tools/rec_audit_job.py` (add `bars_for` after `load_bars`, ~line 192)
- Test: `tools/test_rec_audit_replay.py`

**Interfaces:**
- Consumes: `rec_audit_job.connect(db_path)`, `rec_audit_job.load_bars(conn, symbols)`, `rec_audit_job.MARKET`, `rec_audit.HORIZONS`, `rec_audit.HEADLINE_H`.
- Produces:
  - `rec_audit_job.bars_for(symbols: list[str], db_path=DB_PATH) -> dict[str, pd.DataFrame]` — cache only, OHLCV indexed by date.
  - `rec_audit_replay.WIN_EXCESS_PCT = 5.0`, `LOOKBACK = 60`, `VOL_AVG = 20`.
  - `replay_frame(ep: dict | pd.Series, bars: pd.DataFrame | None, idx_bars: pd.DataFrame | None, h: int = 21, lookback: int = 60) -> dict` with keys:
    `pre` (DataFrame, ≤ lookback rows, index ≤ rec_date, cols open/high/low/close/volume/ema20/vol_avg),
    `post` (same cols, index > rec_date, cut before `data_suspect_date`),
    `bench` (Series rebased to entry_px on `post.index`, or None),
    `levels` (dict `plan_entry, entry_px, stop, target, low20` → float|None),
    `markers` (dict `entry_date, best_date, worst_date, plan_date, window_end` → Timestamp|None),
    `exit_px` (float|None), `last_px` (float|None), `rvol` (float|None, % of 20-session avg),
    `missing` (str|None), `note` (str|None).
  - `footer_line(ep, frame: dict) -> str`
  - `scorecard(eps: pd.DataFrame) -> dict[str, int]` keys `total, target, sl, neither, no_plan, pending`
  - `scorecard_text(sc: dict) -> str`
  - `replay_candidates(eps: pd.DataFrame, kind: str, tag: str | None, h: int) -> pd.DataFrame` (`kind` ∈ `"losers"|"winners"|"all"`)
  - `replay_label(r: pd.Series, h: int) -> str` → `"PAUSHAKLTD · picked 2026-10-16 · 21d -25.4%"` (`· pending` when no return)

- [ ] **Step 1: Write the failing tests** in `tools/test_rec_audit_replay.py`. Build bars with a helper `_bars(start="2026-06-01", n=120, px=100.0, step=1.0)` (business days, open=close-0.5, high=close+1, low=close-1, volume=1000) and an episode dict `rec_date="2026-08-14"`, `close`, `entry`, `stop`, `target`, `status="matured"`, `plan_outcome`, `plan_sessions`, `ret_21`, `excess_21`.
  - `test_no_hindsight_leak`: `f["pre"].index.max() <= pd.Timestamp(rec_date)` and `f["post"].index.min() > pd.Timestamp(rec_date)`; `len(f["pre"]) == 60`.
  - `test_levels_and_markers`: `levels["entry_px"] == post.iloc[0]["open"]`; `markers["window_end"] == post.index[20]`; `markers["best_date"]` is the argmax of `post.head(63)["high"]`.
  - `test_exit_px_target_and_gap`: target_first at plan_sessions=3 → `exit_px == max(target, open of post bar 3)`; stop_first where that bar opens below stop → `exit_px == that open` (gap through stop).
  - `test_rvol`: pick-day volume 3000 vs prior 20 at 1000 → `rvol == pytest.approx(300.0)`.
  - `test_footer_formats`: target_first → `"₹… → ₹… (+…%) · Target hit day 3 · exited ₹… (+…%)"`; stop_first → contains `"SL hit day"`; ambiguous → contains `"SL hit day"` and `"same bar as target"`; neither → `"Neither hit yet"`; stop NaN → `"No plan"`.
  - `test_pending_pick` (Review Focus 2): bars end on rec_date → `post.empty`, footer starts `"Picked at ₹"` and ends `"not entered yet"`.
  - `test_missing_bars` (Review Focus 1): `bars=None` → `missing` contains the symbol, `pre.empty`.
  - `test_data_suspect_cut` (Review Focus 3): `data_suspect_date` = 10th post date → `post.index.max() < that date`, `note` mentions `"split"`.
  - `test_bench_absent_and_gappy` (Review Focus 4): `idx_bars=None` → `bench is None`; idx_bars with every 3rd post date dropped → `bench.index.equals(post.index)`, no NaN, `bench.iloc[0] == pytest.approx(entry_px)`.
  - `test_short_history_and_nans` (Review Focus 5): only 10 bars before rec_date, volume 0, `family_names=float("nan")` → `rvol is None`, `"nan"` not in `footer_line(...)`.
  - `test_scorecard`: rows with plan_outcome `target_first, stop_first, ambiguous, neither, None` + one `status="pending"` → `{"total":6,"target":1,"sl":2,"neither":1,"no_plan":1,"pending":1}`; `scorecard_text` == `"Total 6 · Target hit 1 · SL hit 2 · Neither 1 · No plan 1 · Pending 1"`.
  - `test_candidates_order`: losers sorted by `excess_21` ascending and only `failure` rows; winners only `excess_21 >= 5.0`, descending; `tag` filters on `review_tag`; `all` sorted by `rec_date` descending.
  - `test_label`: matches `"X · picked 2026-10-16 · 21d -25.4%"`; NaN return → ends `"· pending"`.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `python -m pytest tools/test_rec_audit_replay.py -q`
  Expected: FAIL — `ModuleNotFoundError: rec_audit_replay`.

- [ ] **Step 3: Implement `bars_for` and the module.** Notes the tests do not pin:
  - `ema20` = `close.ewm(span=20, adjust=False).mean()` over the full bar history (causal, so the pre slice carries no future); `vol_avg` = rolling 20 mean of volume.
  - `rvol` = pick-day volume ÷ mean of the 20 sessions before it × 100; `None` when fewer than 20 prior sessions or the mean is 0.
  - `low20` = `ep["low20_at_rec"]` if present, else min low of the 20 sessions ending rec_date.
  - `bench` = `idx_bars["close"].reindex(post.index).ffill()` / its first value × `entry_px`; None if idx_bars empty/None or the first value is NaN.
  - `exit_px`: `plan_date = post.index[plan_sessions-1]`; target_first → `max(target, open)`; stop_first/ambiguous → `min(stop, open)`.
  - Money format `₹{:,.2f}`; percent `{:+.2f}%`. Every field read through a `_num(v) -> float|None` that maps NaN/None/"" to None.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `python -m pytest tools/test_rec_audit_replay.py -q`
  Expected: all pass.

- [ ] **Step 5: Commit**
  ```bash
  git add docs/superpowers/specs/2026-11-26-pick-replay-design.md docs/superpowers/plans/2026-11-26-pick-replay.md tools/rec_audit_replay.py tools/rec_audit_job.py tools/test_rec_audit_replay.py
  git commit -m "feat(rec-audit): pick replay frame, footer and scorecard helpers"
  ```

### Task 2: Replay figure

**Files:**
- Modify: `tools/rec_audit_replay.py`
- Test: `tools/test_rec_audit_replay.py`

**Interfaces:**
- Consumes: `replay_frame` output (Task 1).
- Produces: `replay_figure(frame: dict, ep, h: int = 21) -> plotly.graph_objects.Figure`.

Layout: `make_subplots(rows=2, cols=2, shared_xaxes="columns", row_heights=[0.75, 0.25], column_widths=[0.4, 0.6], horizontal_spacing=0.04, vertical_spacing=0.03, subplot_titles=("Pick day · <rec_date>", "Since then · to <last post date>", "", ""))`.
- Col 1 row 1: candlestick `name="pick day"` from `pre`; `ema20` line; dashed horizontal lines for plan entry (`accent`), stop (`risk`), target (`good`), low20 (`text_muted`), each labelled.
- Col 2 row 1: candlestick `name="before pick"` from `pre` at opacity 0.35; candlestick `name="since pick"` from `post`; vertical line at `entry_date`; `vrect` entry_date → window_end (fill `info`, opacity 0.08, label `"<h>-session window"`); same stop/target lines plus entry_px; marker scatter `name="best"` (▲ `good`), `"worst"` (▼ `risk`), `"target hit"`/`"SL hit"` (✕) at plan_date; `bench` as dotted line `name="NIFTY 500 (rebased)"`.
- Row 2 both cols: volume bars (green/red by close vs open) + `vol_avg` line.
- `xaxis rangebreaks=[dict(bounds=["sat", "mon"])]`, `showlegend=False` on candles, `height=620`, `xaxis_rangeslider_visible=False` on every x axis, `margin=dict(l=10, r=10, t=40, b=10)`.

- [ ] **Step 1: Write the failing tests**
  - `test_figure_no_leak`: every trace on col 1 (`xaxis == "x"`) has `max(x) <= rec_date`.
  - `test_figure_traces`: trace names include `"pick day"`, `"since pick"`, `"NIFTY 500 (rebased)"`, `"best"`, `"worst"`; with `plan_outcome="stop_first"` a trace named `"SL hit"` exists.
  - `test_figure_pending` (Review Focus 2): pending frame → figure builds, no `"since pick"` trace, an annotation text contains `"not entered yet"`.

- [ ] **Step 2: Run to verify failure** — `python -m pytest tools/test_rec_audit_replay.py -q -k figure` → FAIL (`replay_figure` undefined).

- [ ] **Step 3: Implement `replay_figure`** as laid out above.

- [ ] **Step 4: Run to verify pass** — same command → PASS; then full file → PASS.

- [ ] **Step 5: Commit** — stage `tools/rec_audit_replay.py tools/test_rec_audit_replay.py`; `git commit -m "feat(rec-audit): pick replay two-panel figure with volume"`.

### Task 3: Page wiring — Pick replay tab and card dialog

**Files:**
- Modify: `tools/desk_pages/rec_audit_page.py` (`render` tabs ~line 132; `_card` ~line 261; new functions after `_postmortems`)
- Test: `tools/test_rec_audit_page.py`

**Interfaces:**
- Consumes: `rec_audit_replay.{replay_frame, replay_figure, footer_line, scorecard, scorecard_text, replay_candidates, replay_label, WIN_EXCESS_PCT}`, `rec_audit_job.bars_for`, `rec_audit_job.MARKET`.
- Produces (in `rec_audit_page`):
  - `_replay_bars(symbol: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None]` — `@st.cache_data(ttl=600, show_spinner=False)`, returns (symbol bars, NIFTY 500 bars) via one `bars_for([symbol, job.MARKET])`.
  - `_replay_tab(eps: pd.DataFrame, h: int) -> None`
  - `_replay_view(r: pd.Series, h: int, key: str) -> None`
  - `_replay_dialog(r: pd.Series, h: int) -> None` decorated `@st.dialog("Pick replay", width="large")`.

Behaviour:
- Tabs become `["Monthly batches", "What worked", "Post-mortems", "Pick replay", "All picks", "Proposed changes", "Run history"]`; Pick replay gets `head` (the source headline), like Post-mortems.
- `_replay_tab`: `st.pills("Show", ["Losers", "Winners", "All"], default="Losers", key="ra_rp_kind")`; cause `st.selectbox("Cause", ["Any", *tags present], key="ra_rp_tag")` shown only for Losers; scorecard caption `scorecard_text(scorecard(candidates))` under the pills; `st.selectbox("Pick", candidates.index, format_func=replay_label…, key="ra_rp_pick")`; empty candidates → `st.info("No picks match this filter.")`; then `_replay_view(row, h, "tab")`.
- `_replay_view`: frame from `_replay_bars`; `missing` → `st.info(missing)` and return; caption line (rank, score, families or scanners, risk flags, `+x.x% vs 20 EMA` from `ext_vs_ema20`, plan source, market regime, `RVol 314%`) — omit absent parts; `st.plotly_chart(replay_figure(...), use_container_width=True, key=f"ra_rp_fig_{key}_{episode_id}")`; `note` → `st.caption("⚠️ " + note)`; footer `st.markdown(f"**{footer_line(...)}**")`; detail caption `"<h>d ret · vs NIFTY 500 · vs sector · best / worst · cause (+others) · 📝 note"`; `st.link_button("Analyzer ↗", link("analyze", symbol))`.
- `_card`: add `st.button("Replay", key=f"ra_rp_btn_{key}", use_container_width=True)` beside Analyzer (two columns) → `_replay_dialog(r, h)`.

- [ ] **Step 1: Write the failing test** in `tools/test_rec_audit_page.py`:
  - `test_pick_replay_tab_registered`: parse `rec_audit_page.py` with `ast`; the `st.tabs` list literal in `render` contains `"Pick replay"` right after `"Post-mortems"`, and a function `_replay_dialog` exists whose decorator source contains `dialog`.

- [ ] **Step 2: Run to verify failure** — `python -m pytest tools/test_rec_audit_page.py -q` → FAIL on the new test.

- [ ] **Step 3: Implement** the tab, view, dialog and card button as described.

- [ ] **Step 4: Run** `python -m pytest tools/test_rec_audit_page.py tools/test_rec_audit_replay.py -q` → PASS.

- [ ] **Step 5: Commit** — stage the two files; `git commit -m "feat(rec-audit): Pick replay tab and post-mortem Replay dialog"`.

### Task 4: Verify in the real app

- [ ] **Step 1:** Start a fresh process — `preview_start {name: "dashboard-fresh"}` (:8502; the running :8501 keeps stale modules).
- [ ] **Step 2:** Portfolio & Risk › Recommendation Audit › Pick replay. Check: Losers default; scorecard line shows real counts; selecting PAUSHAKLTD (2026-10-16) draws both panels, SL-hit marker, shaded 21-session window, NIFTY 500 dotted line, volume pane; footer reads `₹… → ₹… (…) · SL hit day N · exited ₹…`.
- [ ] **Step 3:** Winners filter → best pick first, `Target hit` or `Neither hit yet` footer. Pick a 2026-11-2x pending pick under All → pick-day panel only, "not entered yet".
- [ ] **Step 4:** Post-mortems → Replay on a card opens the large dialog with the same view.
- [ ] **Step 5:** `read_console_messages` (errors) and `preview_logs` level error → none. Screenshot the replay for the owner. Stop the :8502 server. Tell the owner to restart :8501 to pick up the change.
