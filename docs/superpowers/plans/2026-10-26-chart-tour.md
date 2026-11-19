# Chart Tour (B-186) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A "Tour this chart" side panel on the Chart Tool that steps through Now, Stock-or-market? and up to eight detector findings, each driving the chart through a small action protocol and carrying the desk's panel-measured base rate and a Watch level.

**Architecture:** A pure Python engine `tools/chart_tour.py` (17 detectors + two fixed steps + action validation) serves `GET /api/tour` in `chart_server.py`; `tools/tour_base_rates.py` runs the same detectors over the B-165 panel and writes `tools/cache/tour_base_rates.json`; `chart_dashboard.html` gets a Tour button, a right side panel and an action executor on a dedicated tour layer.

**Tech Stack:** Python 3.14 (`Programs\Python314`), pandas/numpy, Flask (`chart_server`), Lightweight Charts in `chart_dashboard.html`, pytest (`testpaths = tools`, tests beside modules).

**Spec:** `docs/superpowers/specs/2026-10-26-chart-tour-design.md` (commits 683ee0b, f16a9f8 + the times amendment in this plan's commit). If spec and plan disagree, the spec wins.

## Global Constraints

- Interpreter: `PY="C:/Users/Owner/AppData/Local/Programs/Python/Python314/python.exe"`; tests `"$PY" -X utf8 -m pytest tools/<file>`; bare `python` lacks pandas.
- Input frames: lowercase `open high low close volume`, DatetimeIndex (as `chart_server._bars_to_df` builds them). Action/finding times are the bars' unix-second `time` values.
- Daily only: `/api/tour` with timeframe ≠ `1d` returns `steps: []` + note "The tour is daily-only: its base rates are measured on daily bars."
- Minimum 80 bars for findings; fewer → Now step only + note "Too little history for findings."
- At most 8 findings; order: newest `time` first (state findings count as the last bar), then higher `weight`.
- Ported thresholds verbatim: 55-session closing high/low; failed at 0.98 / 1.02 × level; breakout scan window last 15 bars; RVOL = bar volume ÷ prior-20 mean; volume expansion mean(last 5) ÷ mean(prior 50) ≥ 1.5; ATR14 (Wilder) now ÷ ATR14 42 bars ago ≥ 1.4; squeeze BB(20,2) width÷mid ≤ 1.05 × min over last 126 bars with > 60 values; divergence: last two 5-bar fractal swings within the last 40 bars (excluding the last 2), RSI14 gap > 4; gap |open/prev close − 1| ≥ 0.03 in the last 10 bars and unfilled.
- Weights verbatim: breakout family 0.7 + (i − (n−15))/50 + min(0.2, (RVOL−1)/5); volume min(0.85, 0.4 + (x−1.5)/3); ATR min(0.8, 0.4 + (x−1.4)/2); squeeze 0.65; divergence 0.7; gap 0.6 + min(0.2, |gap|); SMA200 / crosses 0.6; desk detectors 0.75.
- Action types (only these): `CLEAR`, `ZOOM_TO_RANGE{from,to}`, `PRICE_LEVEL{price,label,tone}`, `HIGHLIGHT_CANDLE{time,tone}`, `HIGHLIGHT_RANGE{from,to,tone}`, `INDICATORS{ids}`, `COMPARE{symbols}`; tone ∈ {up, down, neutral, accent}.
- Base rates: panel `nu.symbols("nifty500")[:300]`, `crt_sweep_overlap._fetch`, last 750 bars; horizons 5/20/60; h=20 decides; floors ≥ 30 symbols and ≥ 100 events; Holm across all detectors at 0.05; thirds rule ≥ 2 of 3; state refractory 20 bars; labels `EDGE | INVERTED | ORDINARY | TOO_FEW` (+ `NOT_MEASURED` at serve time); stale after 45 days.
- Study links (strict): `structure_break_held→B-114`, `liquidity_sweep_bull→B-41m`, `flag_pole_bull→B-92`, `abcd→B-132`, `adx_up_state→ADX`; nothing else.
- **The base-rate pre-registration page lands before the first real panel run (Task 9 before Task 10).**
- Wiki edits to `index.md`, `log.md`, `Open-Backlog.md` stage only this work's lines (the user's B-183 lines stay unstaged): write `HEAD`/index content + our lines via `git hash-object -w --stdin` + `git update-index --cacheinfo`, matching files by exact name.

## Review Focus

1. **Bars with NaN or zero volume** (index-like symbols, holiday stubs): volume-based detectors (RVOL, volume expansion) must skip, not divide by zero or fire on NaN. Test in Task 3.
2. **A tour opened on an intraday chart, then switched to daily**: the panel must re-fetch on symbol/timeframe change and never show the previous symbol's steps. Check in Task 8 (browser).
3. **User's own indicators and drawings**: `CLEAR` and closing the panel must restore exactly the indicators that were on before the tour and never touch user drawings or other overlays' markers. Check in Task 8 (browser) + a JS-free Python test that action lists never contain anything but the 7 types (Task 1).
4. **Stale or missing base-rate file**: every badge must say `NOT_MEASURED` or show its age, never a silent blank. Test in Task 6.
5. **Underlying desk detector changes shape** (e.g. `detect_liquidity_sweep` returns new keys): the wrapper must degrade to "no finding" + a note, not crash the tour. Test in Task 5 via a detector that raises.

---

### Task 1: Engine core — types, action validation, Now step

**Files:** Create `tools/chart_tour.py`, `tools/test_chart_tour.py`

**Interfaces — Produces:**
- `ACTION_TYPES = {"CLEAR","ZOOM_TO_RANGE","PRICE_LEVEL","HIGHLIGHT_CANDLE","HIGHLIGHT_RANGE","INDICATORS","COMPARE"}`, `TONES = {"up","down","neutral","accent"}`
- `@dataclass Finding` and `@dataclass Detector` exactly as spec §2.1; `Finding.to_dict() -> dict`.
- `validate_actions(actions: list[dict]) -> list[dict]` — raises `ValueError` naming the bad type/field.
- `t_of(df, i) -> int` — unix seconds of bar `i`.
- `now_step(df) -> dict` `{id:"now", title, body, facts:{close, lo63, hi63, pct_from_hi, pct_from_lo, trend, rvol}, actions}` — trend: close > SMA20 and SMA20 rising over 5 bars → "Uptrend"; close < SMA20 and falling → "Downtrend"; else "Sideways".

- [ ] **Step 1: Write failing tests**

```python
def test_validate_actions_accepts_the_seven(): ...      # one of each type, well-formed → returned unchanged
def test_validate_actions_rejects_unknown_type(): ...  # {"type":"DRAW_ARROW"} → ValueError mentioning DRAW_ARROW
def test_validate_actions_rejects_bad_tone(): ...      # PRICE_LEVEL tone "green" → ValueError
def test_now_step_range_and_trend(): ...               # 100 rising bars → trend "Uptrend", hi63 == max(high[-63:]), PRICE_LEVEL ×2, ZOOM from t_of(df,-63)
def test_now_step_rvol_skips_zero_volume(): ...        # volume all 0 → facts["rvol"] is None, body has no "volume" clause
```

- [ ] **Step 2: Run, verify FAIL** (`ModuleNotFoundError: chart_tour`)
- [ ] **Step 3: Implement** the types, `validate_actions`, `t_of`, `now_step`.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(b186): chart tour engine core — types, action schema, Now step`

### Task 2: Breakout / breakdown family and gaps (ported)

**Files:** Modify `tools/chart_tour.py`, `tools/test_chart_tour.py`

**Interfaces — Produces:** detector functions `det_breakout55(df)`, `det_breakdown55(df)` (each returns 0–1 `Finding`, key `breakout55`/`failed_breakout55` resp. `breakdown55`/`failed_breakdown55` decided by the failed rule), `det_gaps(df)` (`gap_up`/`gap_down`, most recent qualifying unfilled gap only). Registered in `DETECTORS`. Each finding: `PRICE_LEVEL` at the level, `HIGHLIGHT_CANDLE` at the event bar, `ZOOM_TO_RANGE` last 63 bars; watch per spec §2.4.

- [ ] **Step 1: Write failing tests**

```python
def test_breakout55_fires_and_watch_is_98pct(): ...       # flat 70 bars then close above 55d high 5 bars ago, no later close < .98×L → key breakout55, watch level == round(.98*L,2), tone up
def test_breakout_becomes_failed_below_98pct(): ...        # same, then a close at .975×L → key failed_breakout55, tone down
def test_breakout_older_than_15_bars_ignored(): ...         # cross 20 bars ago → []
def test_breakout_weight_formula(): ...                     # known RVOL 2.0 at i=n-1 → weight == .7 + 14/50 + .2
def test_breakdown55_mirror_and_failed_at_102pct(): ...
def test_gap_up_unfilled_fires_filled_does_not(): ...       # +3.5% gap 4 bars ago never touched prev close → gap_up; same but a later low ≤ prev close → []
def test_gap_below_3pct_ignored(): ...                      # +2.9% → []
```

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement** the three detector functions.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(b186): ported breakout/breakdown and gap detectors`

### Task 3: Volume/ATR expansion, squeeze, divergence, SMA200, crosses (ported)

**Files:** Modify `tools/chart_tour.py`, `tools/test_chart_tour.py`

**Interfaces — Produces:** `det_volume_expansion`, `det_atr_expansion`, `det_squeeze`, `det_divergence` (returns bearish_div and/or bullish_div), `det_sma200` (`above_sma200`/`below_sma200` as current state with the cross bar as `time` if within 20 bars, else state `time=None`), `det_crosses` (`golden_cross`/`death_cross` within the last 20 bars). Use `scanner_templates`' own RSI if one exists (`_rsi` / `rsi`), else Wilder RSI14 locally; ATR Wilder 14.

- [ ] **Step 1: Write failing tests**

```python
def test_volume_expansion_threshold_and_weight(): ...   # ratio exactly 1.5 → fires, weight .4; 1.49 → []
def test_volume_expansion_skips_nan_or_zero_volume(): ... # all-NaN / all-zero volume → []
def test_atr_expansion_threshold(): ...                  # ATR ratio 1.4 → fires tone neutral; 1.39 → []
def test_squeeze_narrowest_in_126(): ...                 # constant-width bands then narrowing to ≤1.05×min → fires; widening → []
def test_bearish_divergence_needs_rsi_gap_over_4(): ...  # higher high with RSI 6 lower → fires; RSI 3 lower → []
def test_sma200_state_and_cross_time(): ...              # cross 10 bars ago → above_sma200 with time; 50 bars ago → state, time None
def test_golden_cross_within_20(): ...
```

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement** the six functions; register all in `DETECTORS` with `kind`/`claim` per spec §2.2.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(b186): ported expansion, squeeze, divergence and trend detectors`

### Task 4: Desk detectors (wrappers)

**Files:** Modify `tools/chart_tour.py`, `tools/test_chart_tour.py`

**Interfaces — Consumes:** `scanner_templates.detect_structure_chain(df, pivot_len=15, confirm="close", fail_win=3, max_swings=15)`, `scanner_templates.detect_liquidity_sweep(df, pivot_len=5)`, `flag_pole.detect_flag_pole(df, "bull")`, `harmonic_patterns.detect_last_pattern(df, max_age_bars=50)` (bullish + `"AB=CD"` in `pattern`; stop `D − scanner_templates.ABCD_STOP_ATR × ATR14`), `scanner_templates._adx_di_series(df)` (up-state: +DI > −DI and ADX ≥ 25 and ADX rising vs 5 bars ago, per `adx_di_backtest.state_bull_adx_rising`).
**Produces:** `det_structure_break_held`, `det_liquidity_sweep_bull`, `det_flag_pole_bull`, `det_abcd`, `det_adx_up_state`; `STUDY_LINKS = {"structure_break_held":"B-114","liquidity_sweep_bull":"B-41m","flag_pole_bull":"B-92","abcd":"B-132","adx_up_state":"ADX"}`. Each wrapper reads only documented keys; a missing key → no finding.

- [ ] **Step 1: Write failing tests** (monkeypatch the underlying detector to return a canned dict; one real smoke test per wrapper on a synthetic frame asserting no exception)

```python
def test_structure_break_held_from_chain(monkeypatch): ...   # canned chain with last event failed=False → finding, watch level == break level
def test_structure_break_failed_gives_nothing(monkeypatch): ...
def test_liquidity_sweep_bull_only(monkeypatch): ...         # bear sweep → []; bull sweep → finding, watch == swept level
def test_abcd_requires_bullish_abcd(monkeypatch): ...        # Gartley bullish → []; bullish AB=CD → finding, watch == D - 2*ATR
def test_adx_up_state_rule(): ...                            # synthetic strong uptrend → fires; flat → []
def test_wrapper_tolerates_missing_keys(monkeypatch): ...    # underlying returns {} → []
def test_study_links_are_exactly_five(): ...
```

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement** the wrappers + `STUDY_LINKS`; register in `DETECTORS` with `family="desk"`, weight 0.75.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(b186): desk detectors in the tour (structure, sweep, flag, AB=CD, ADX)`

### Task 5: Context step and `build_tour`

**Files:** Modify `tools/chart_tour.py`, `tools/test_chart_tour.py`

**Interfaces — Produces:**
- `context_step(df, market_df, sector_df, sector_label) -> dict` `{id:"context", title, body, facts:{stock20, nifty20, sector20|None, verdict: "ahead"|"in line"|"behind"}, actions:[COMPARE, ZOOM_TO_RANGE 20]}`; verdict uses stock − max(nifty, sector) vs ±5 pp; `sector_df` None → NIFTY only.
- `badge_for(key, base_rates: dict|None, today) -> dict` `{label, text, stale, study}` — `NOT_MEASURED` when file/key absent; `stale` when `asOf` older than 45 days; text per spec §3; `study` from `STUDY_LINKS` + `named_studies` headline/date.
- `build_tour(df, *, market_df, sector_df, sector_label, base_rates, today, max_findings=8) -> dict` `{asOf, steps, notes}`.

- [ ] **Step 1: Write failing tests**

```python
def test_context_verdict_bands(): ...                 # stock +12, nifty +2, sector +4 → "ahead"; +6/+2/+4 → "in line"
def test_context_without_sector(): ...
def test_badge_not_measured_when_missing(): ...
def test_badge_stale_after_45_days(): ...
def test_badge_text_format(): ...                     # ORDINARY row → "Ordinary · +0.2% vs a normal day @20d · 3412 events / 287 names · p 0.41 · as of 2026-10"
def test_build_tour_order_and_cap(monkeypatch): ...   # 10 fake detectors → 8 findings, newest first then weight
def test_build_tour_short_history(): ...              # 60 bars → steps == [now], note "Too little history for findings."
def test_build_tour_skips_raising_detector(monkeypatch): ...  # one raises → others present, note names it
def test_every_action_in_a_tour_is_valid(): ...       # real build on a synthetic frame → validate_actions on all steps passes
```

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement** the three functions.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(b186): context step, badges, build_tour`

### Task 6: Base-rate job

**Files:** Create `tools/tour_base_rates.py`, `tools/test_tour_base_rates.py`

**Interfaces — Consumes:** `chart_tour.DETECTORS`.
**Produces:**
- `detector_events(df, key) -> list[int]` — bar positions where the detector fires when run point-in-time (slide the frame: evaluate on `df.iloc[:i+1]` only at candidate bars; dated detectors report their own bar, state detectors the first true bar, 20-bar refractory). Must not look ahead.
- `measure(frames: dict[str, DataFrame], keys, horizons=(5,20,60)) -> dict` per key `{n_events, n_symbols, mean5, mean20, mean60, p20, thirds:[+1|-1|0]×3}` using the spec §3 outcome (sign-aligned / magnitude) and per-symbol t.
- `label(rows) -> rows` adding `p20_holm`, `label`.
- `main(argv)` CLI: `--symbols 300 --out tools/cache/tour_base_rates.json`; writes `{asOf, panel, horizons, detectors}`.

- [ ] **Step 1: Write failing tests**

```python
def test_events_point_in_time_no_lookahead(): ...  # a breakout that later fails: event recorded at the breakout bar with key decided only from bars ≤ that bar (failed variant appears at its own later bar)
def test_state_refractory_20(): ...                # squeeze true for 30 consecutive bars → 1 event; true again 25 bars later → 2
def test_planted_edge_labelled_edge(): ...         # 40 synthetic symbols, +3% 20d drift after each planted event → EDGE
def test_null_panel_labelled_ordinary(): ...       # same without drift → ORDINARY
def test_floors_give_too_few(): ...                # 10 symbols → TOO_FEW
def test_bearish_detector_sign_aligned(): ...      # planted -3% after breakdown events → EDGE (not INVERTED)
def test_magnitude_detector_uses_abs(): ...        # squeeze with planted ±5% moves, zero mean → EDGE on |ret|
def test_holm_across_detectors(): ...              # hand-built p-values → expected p20_holm
def test_thirds_rule_blocks_one_period_edge(): ...  # effect only in the first third → not EDGE
```

Point-in-time evaluation is expensive (750 bars × 300 names × 17 detectors); evaluate only at bars where a cheap pre-filter could fire (e.g. a new 55-day extreme, a ≥3% open gap, a volume/ATR ratio crossing) and cache per-symbol indicators. Target: full run < 30 min.

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(b186): tour base-rate job`

### Task 7: `/api/tour`

**Files:** Modify `tools/chart_server.py`; Test `tools/test_chart_routes.py` (or a new `tools/test_chart_tour_route.py` following its stub pattern)

**Interfaces — Consumes:** `chart_tour.build_tour`, `_bars_to_df`, `ds.detect_source(...).get_ohlcv(symbol, "1d", 400)`, `pa_chart_focus.stock_sector(sym)`, `pa_chart_focus.context_for(sector) -> (ticker, label, is_sector)`, base-rate JSON at `tools/cache/tour_base_rates.json` (read once per process, re-read when its mtime changes).
**Produces:** `GET /api/tour?symbol=&timeframe=1d` → `{symbol, asOf, steps, base_rates_asOf, notes}`; 400 without symbol.

- [ ] **Step 1: Write failing tests**

```python
def test_tour_requires_symbol(client): ...
def test_tour_non_daily_note(client): ...            # timeframe=15m → steps [], the daily-only note
def test_tour_returns_now_and_context(client, monkeypatch): ...  # stub source with 300 synthetic bars → steps[0].id=="now", steps[1].id=="context"
def test_tour_missing_base_rates_not_measured(client, monkeypatch, tmp_path): ...
```

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement** the route.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(b186): /api/tour`

### Task 8: Side panel and action executor

**Files:** Modify `tools/chart_dashboard.html`

**Interfaces — Consumes:** `/api/tour`; existing `pane.series` (candles), `pane.series.createPriceLine/removePriceLine`, `setPaneMarkers(pane, key, markers)`, `pane.indicators` + `applyIndicators(pane)`, `chart.timeScale().setVisibleRange({from,to})`, `/api/ohlcv` for COMPARE.
**Produces (JS):** `openTour(pane)`, `closeTour(pane)`, `runTourStep(pane, i)`, `runTourActions(pane, actions)`; state `pane.tour = {data, idx, priceLines, compareSeries, savedIndicators}`; markers under key `'tour'`.

- Tour button in the chart toolbar; right side panel (layout A): header "Tour · SYMBOL · daily · as of DATE"; step cards with title, body, badge (Edge green, Inverted red "worked backwards", Ordinary grey, Too few / Not measured amber; stale → amber date), Watch line; `[` `]` keys and click.
- Executor: `CLEAR` removes tour price lines, tour markers, compare series, and restores `savedIndicators`; `ZOOM_TO_RANGE` → `setVisibleRange`; `PRICE_LEVEL` → `createPriceLine` (dashed, label); `HIGHLIGHT_CANDLE` → a tour marker; `HIGHLIGHT_RANGE` → markers at both ends + shaded via a background area series on the tour layer; `INDICATORS` → save current set once, add ids, `applyIndicators`; `COMPARE` → fetch each symbol's daily bars, add a line series rebased to the stock's close at the visible-range start; unknown type → ignored.
- Re-fetch on symbol or timeframe change; closing the panel runs `CLEAR`.

- [ ] **Step 1:** Start a fresh chart server with `preview_start {name: "chart-fresh"}` (port 5002, so the live :5001 instance keeps its old module; see the Streamlit stale-module memory) and open a daily chart on it.
- [ ] **Step 2: Implement** button, panel, executor.
- [ ] **Step 3: Browser-verify** on :5002: open the tour on RELIANCE.NS; step through every step; confirm each action type visibly works; switch symbol mid-tour (Review Focus 2); turn on two indicators before opening, step, close → the same two remain and user drawings are untouched (Review Focus 3); 15m chart shows the daily-only note. Read console for errors.
- [ ] **Step 4:** Run `"$PY" -X utf8 -m pytest tools/test_chart_routes.py tools/test_chart_control_sizes.py tools/test_chart_tour.py` → pass.
- [ ] **Step 5: Commit** `feat(b186): Tour side panel and chart action executor`

### Task 9: Pre-register the base-rate run

**Files:** Create `trading-wiki/wiki/analyses/Chart-Tour-Base-Rates-Pre-Registration.md`; Modify `index.md`, `log.md`, `Open-Backlog.md` (our lines only)

- [ ] **Step 1:** Write the page: detectors (17, with keys and rules), panel, event definition and refractory, outcome (sign-aligned / magnitude), statistic, floors, Holm family, thirds rule, labels, gross of costs, "No real-data run has been made at the time of this commit", and priors (most ported detectors ORDINARY; desk positives may not reproduce on this panel; squeeze ORDINARY on magnitude per B-101).
- [ ] **Step 2:** Update B-186 backlog row to "PRE-REGISTERED, building", index row, log entry.
- [ ] **Step 3: Commit** `docs(b186): pre-register tour base rates`

### Task 10: Real run, result page, wiring

**Files:** Generate `tools/cache/tour_base_rates.json`; Create `trading-wiki/wiki/analyses/Chart-Tour-Base-Rates-Result.md`; Modify `index.md`, `log.md`, `Open-Backlog.md`; `tools/named_studies.py` only if `tour_base_rates.py` is picked up by `study_files()` (it is not — `*_study.py`/`*_backtest.py` only — so no entry unless renamed).

- [ ] **Step 1:** `"$PY" -X utf8 tools/tour_base_rates.py --symbols 300` (run in background; < 30 min) → JSON written.
- [ ] **Step 2:** Sanity: every detector present; n/s plausible; desk detectors' panel numbers vs their studies listed side by side.
- [ ] **Step 3:** Write the result page (table of 17 rows, labels as produced, disagreements with studies called out); update backlog/index/log.
- [ ] **Step 4:** Browser re-check: badges now show real labels.
- [ ] **Step 5:** `"$PY" -X utf8 tools/claims_lint.py`; full suite `"$PY" -X utf8 -m pytest` → only the 8 known pre-existing failures (or fewer if the test-fix session has merged).
- [ ] **Step 6: Commit** `feat(b186): tour base rates measured; badges live`
