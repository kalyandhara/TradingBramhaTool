# Policy Event-Study Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether RBI MPC and Union Budget days move NIFTY and NSE sector indices abnormally (and, for MPC, in the theorised direction) against a matched random-date null, as a pre-registered study.

**Architecture:** A pure library `tools/event_study.py` (events, prices, abnormal returns, nulls, corrections, `run_study`) with injectable loaders; a thin CLI `tools/event_study_run.py` that downloads, runs and writes JSON + Markdown; a verified seed file `data/events/policy_events.csv`; wiki pre-registration (frozen before the first real run) and result pages.

**Tech Stack:** Python 3.14 (`Programs\Python314`), numpy, pandas, yfinance, pytest (`testpaths = tools`, tests sit next to modules as `tools/test_*.py`).

**Spec:** `docs/superpowers/specs/2026-10-26-policy-event-study-design.md` (commit a255a1f). If spec and plan disagree, the spec wins.

## Global Constraints

- Interpreter: `PY="C:/Users/Owner/AppData/Local/Programs/Python/Python314/python.exe"`; tests: `"$PY" -X utf8 -m pytest tools/test_event_study.py`. A bare `python` resolves to a venv without pandas.
- Market ticker `^NSEI`. Sectors (exactly 12): `^NSEBANK ^CNXIT ^CNXPHARMA ^CNXFMCG ^CNXMETAL ^CNXINFRA ^CNXREALTY ^CNXENERGY ^CNXAUTO ^CNXPSUBANK ^CNXPSE NIFTY_FIN_SERVICE.NS`. `^CNXMEDIA` excluded.
- Rate-sensitive basket: `^NSEBANK ^CNXPSUBANK ^CNXREALTY ^CNXAUTO NIFTY_FIN_SERVICE.NS`, equal-weighted.
- Price start `2010-01-01`, Yahoo `auto_adjust=True`, daily log returns.
- Estimation window `[-250, -11]`, `min_obs = 120`.
- Windows: `pre (-5,-1)`, `day (0,0)`, `post (1,5)`, `drift (0,20)`.
- Null A: 10,000 draws, seed 7, exclusion ±10 trading days around every real event of the set, same years; `calendar_match` for Budget = same calendar months as the real events.
- Null C: 10,000 label permutations of cut/hike, bucket sizes preserved.
- p = (1 + #{null ≥ real}) / (1 + draws), one-sided. Bootstrap CI 90%, 5,000 reps.
- Primary family P1, P2 × {mpc, budget} = 4 tests, Holm, α = 0.05. Exploratory: BH q-values.
- Split-half boundary: `2019-01-01`; robustness = each half p < 0.10 and ratio ≥ 1.2×; promotion ratio ≥ 1.3×.
- Bucket with n < 5 → `"n/a (n<5)"`, not tested.
- Unscheduled MPC (`scheduled=0`) excluded from primary/secondary; reported as a separate note.
- No network in tests: every loader takes an injected `download` callable.
- **Task 6 (pre-registration commit) lands before Task 7 runs on real data.**

## Review Focus

1. **Calendar gaps between series** (a sector index missing a day NIFTY has, or vice versa): returns are computed on the inner-joined date index per (sector, market) pair, never on forward-filled prices, so a gap does not manufacture a zero return. Test in Task 2.
2. **Event too close to the end of the data** (drift window `+20` beyond the last bar): that event is dropped for that window only, and the per-window n reflects it; the day window still uses it. Test in Task 3.
3. **Two events inside one estimation window** (e.g. a Budget 8 trading days before an MPC): the estimation window is used as is (no event-masking); the report's per-set exclusion zone is what keeps the *null* clean. Documented behaviour, test pins that it does not crash or drop the event. Test in Task 3.
4. **Saturday / holiday event dates** (Budget 2015-02-28, 2020-02-01, 2025-02-01): snapped to the next session with `snapped=True` surfaced in the output table. Test in Task 2.
5. **yfinance shape drift** (MultiIndex columns for multi-ticker downloads, a ticker returning empty): the loader flattens to a wide `Close` frame and omits empty tickers with a logged warning; the report lists omitted sectors. Test in Task 2.

---

### Task 1: Event file loader and seed schema

**Files:**
- Create: `tools/event_study.py`
- Create: `tools/test_event_study.py`
- Create: `data/events/policy_events.csv` (header row only; Task 6 fills it)

**Interfaces:**
- Produces: `EVENT_LABELS: dict[str, set[str]] = {"mpc": {"cut","hike","hold"}, "budget": {"full","interim"}}`; `load_events(path, types: list[str] | None = None, scheduled_only: bool = True) -> pd.DataFrame` with columns `date (datetime64), event_type, label, scheduled (int), time_ist, source_url, notes`, sorted by date.

- [ ] **Step 1: Write failing tests**

```python
def test_load_events_filters_and_sorts(tmp_path): ...   # 3 rows out of order, types=["mpc"] → only mpc rows, ascending dates
def test_load_events_drops_unscheduled_by_default(tmp_path): ...  # scheduled=0 row absent; present with scheduled_only=False
def test_load_events_rejects_unknown_label(tmp_path): ...  # mpc,"pause" → ValueError mentioning "pause"
def test_load_events_rejects_duplicate(tmp_path): ...      # same (date, event_type) twice → ValueError
```

- [ ] **Step 2: Run, verify FAIL** (`ImportError: event_study`)
- [ ] **Step 3: Implement `load_events` in `tools/event_study.py`** — `pd.read_csv(..., dtype=str)`, parse `date`, validate against `EVENT_LABELS`, then filter.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(event-study): event file loader`

### Task 2: Prices, returns and session snapping

**Files:** Modify `tools/event_study.py`, `tools/test_event_study.py`

**Interfaces:**
- Produces:
  - `MARKET = "^NSEI"`, `SECTORS: list[str]` (the 12), `BASKET: list[str]` (the 5).
  - `load_closes(tickers: list[str], start: str, download=None, cache_dir: Path | None = None) -> tuple[pd.DataFrame, list[str]]` — wide Close frame (DatetimeIndex, one column per ticker, NaN where a series has no bar) and the list of omitted tickers. `download(tickers, start) -> pd.DataFrame` defaults to a `yfinance.download(..., auto_adjust=True, group_by="ticker", progress=False)` wrapper. Cache file `closes_<start>.csv` in `cache_dir` (default `tools/cache/event_study/`), reused if its last date ≥ the last weekday before today.
  - `pair_returns(closes, ticker, market=MARKET) -> pd.DataFrame` — columns `r`, `m`: log returns on the inner-joined non-NaN dates of the two series.
  - `snap_to_sessions(dates: pd.Series, index: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]` — position of first session ≥ date, and bool `snapped` (True where session date ≠ event date). A date after the last session → position −1.

- [ ] **Step 1: Write failing tests**

```python
def test_load_closes_flattens_multiindex_and_omits_empty(): ...  # stub returns MultiIndex frame for ["A","B"], "B" all-NaN → columns == ["A"], omitted == ["B"]
def test_load_closes_uses_cache(tmp_path): ...                  # 2nd call with a download stub that raises → still returns frame
def test_pair_returns_inner_joins_gaps(): ...                   # sector NaN on day 3 → no row dated day 3; day-4 row's r == log(close4/close2), m == log(mkt4/mkt2)
def test_snap_saturday_to_monday(): ...                         # 2020-02-01 (Sat) → Monday position, snapped True; weekday date → snapped False
def test_snap_after_last_session_is_minus_one(): ...
```

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement** the four functions above.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(event-study): price loader, pair returns, session snapping`

### Task 3: Abnormal returns per event and window

**Files:** Modify `tools/event_study.py`, `tools/test_event_study.py`

**Interfaces:**
- Consumes: `pair_returns`, `snap_to_sessions`, `SECTORS`, `MARKET`.
- Produces:
  - `WINDOWS = {"pre": (-5,-1), "day": (0,0), "post": (1,5), "drift": (0,20)}`
  - `market_model_ar(pr: pd.DataFrame, d0_pos: int, est=(-250,-11), min_obs=120, model="market") -> pd.Series | None` — AR series indexed by relative day for the whole span `[-5, +20]` that exists; `model="adjusted"` uses β=1, α=0. `None` if fewer than `min_obs` estimation rows.
  - `event_ar_table(closes, events, sectors=SECTORS, windows=WINDOWS, model="market") -> pd.DataFrame` — long table with columns `event_date, event_type, label, snapped, ticker, window, car`; plus rows `ticker=MARKET` holding the raw NIFTY return (`car` = summed raw log return). A (event, ticker, window) whose window runs past the data is omitted.

- [ ] **Step 1: Write failing tests**

```python
def test_market_model_recovers_beta(): ...      # synthetic r = 0.001 + 1.5*m + small noise; AR on day 0 where planted +0.03 ≈ 0.03 ± 0.003
def test_market_model_too_short_returns_none(): ...  # 100 estimation rows → None
def test_adjusted_model_is_sector_minus_market(): ...
def test_event_near_end_drops_only_drift(): ...  # event 3 bars from the end → "day" row present, "drift" row absent
def test_overlapping_events_both_kept(): ...     # two events 8 bars apart → both have "day" rows
```

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement** — OLS via `np.polyfit(m, r, 1)` on estimation rows; positions are relative to the pair's own index.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(event-study): market-model abnormal returns`

### Task 4: Nulls, corrections and confidence intervals

**Files:** Modify `tools/event_study.py`, `tools/test_event_study.py`

**Interfaces:**
- Produces:
  - `candidate_positions(index: pd.DatetimeIndex, event_pos: np.ndarray, exclude=10, years: set[int] | None = None, months: set[int] | None = None, margin=(250, 20)) -> np.ndarray` — positions eligible as pseudo-events: not within ±`exclude` of any event, in `years`/`months` if given, and with ≥250 bars before and ≥20 after.
  - `date_null(stat_fn: Callable[[np.ndarray], float], candidates: np.ndarray, n_events: int, draws=10_000, seed=7) -> np.ndarray` — `stat_fn` receives an array of pseudo-event positions.
  - `p_greater(real: float, null: np.ndarray) -> float` — `(1 + (null >= real).sum()) / (1 + len(null))`. For "less" hypotheses callers negate both.
  - `label_permutation(values: np.ndarray, labels: np.ndarray, a="cut", b="hike", draws=10_000, seed=7) -> tuple[float, np.ndarray]` — real and null of mean(a) − mean(b).
  - `bootstrap_ci(values: np.ndarray, stat=np.mean, reps=5_000, level=0.90, seed=7) -> tuple[float, float]`
  - `holm(p: list[float]) -> np.ndarray`, `bh(p: list[float]) -> np.ndarray` (adjusted values, capped at 1, original order).

- [ ] **Step 1: Write failing tests**

```python
def test_candidates_exclude_window_and_months(): ...   # no candidate within 10 of an event; months={2} → all candidates in Feb
def test_date_null_deterministic(): ...                # same seed → np.array_equal
def test_p_greater_formula(): ...                      # real=5, null=[1,2,6] → (1+1)/4 == 0.5
def test_label_permutation_preserves_sizes(): ...      # stat_fn spy: each draw has same count of a and b
def test_holm_matches_hand(): ...                      # [0.01,0.04,0.03,0.005] → [0.03,0.06,0.06,0.02]
def test_bh_matches_hand(): ...                        # [0.01,0.04,0.03,0.005] → [0.02,0.04,0.04,0.02]
```

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement** the six functions.
- [ ] **Step 4: Run, verify PASS**
- [ ] **Step 5: Commit** `feat(event-study): date null, label permutation, Holm/BH, bootstrap CI`

### Task 5: `run_study`, planted-effect validation, CLI and report

**Files:**
- Modify: `tools/event_study.py`, `tools/test_event_study.py`
- Create: `tools/event_study_run.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces:
  - `StudyConfig` dataclass: `draws=10_000, seed=7, boot=5_000, exclude=10, split="2019-01-01", calendar_match: dict[str,bool] = {"mpc": False, "budget": True}`.
  - `run_study(closes: pd.DataFrame, events: pd.DataFrame, cfg: StudyConfig, omitted: list[str] = []) -> dict` — JSON-serialisable: `{"meta", "primary": [rows], "secondary": [rows], "exploratory": [rows], "split_half": [rows], "unscheduled": [rows], "verdicts": [str]}`; every test row has `test, set, n, real, null_mean, ratio, p, p_adj, ci_lo, ci_hi`.
    - P1 stat on positions: mean |raw NIFTY log return| on day 0.
    - P2 stat: mean over events of std across sectors of day-0 AR (market model, estimated per pseudo-event).
    - S1/S2/S3 as spec §3.3; S2 tested on negated values.
    - Verdict strings built from the spec §3.4 rule — exact wording: `"PROMOTE: <set> policy days are volatility events (P<k> ratio <x>x)"`, `"PROMOTE: MPC directional tilt (decision-conditional - not tradeable before the announcement)"`, otherwise `"CALIBRATION: <set> <test> - no promotable effect"`.
  - `render_markdown(result: dict) -> str`.
  - CLI `event_study_run.py --events mpc,budget --start 2010-01-01 --draws 10000 --seed 7 --out output/event_study --no-cache` → writes `<YYYY-MM-DD>_<sets>.json` and `.md`, prints the md path. Unscheduled events loaded separately with `scheduled_only=False`.
  - Performance note: P2's null re-estimates market models per pseudo-event; precompute per-ticker rolling OLS (or AR for every position once) so 10,000 draws finish in < 2 min.

- [ ] **Step 1: Write failing tests**

```python
def test_planted_volatility_detected(): ...   # synthetic 13 series × 3000 days; 40 events with NIFTY ±3σ and sector dispersion ×3 → P1 and P2 p < 0.01, ratio > 1.3, verdict starts "PROMOTE"
def test_unplanted_control_not_detected(): ...  # same, no plant → P1 p > 0.05, verdict "CALIBRATION"
def test_planted_directional_cut_effect(): ...  # basket +2σ on 12 cut days, −2σ on 12 hike days → S1, S3 p < 0.05
def test_small_bucket_is_na(): ...              # 3 hike events → S2 row p == "n/a (n<5)"
def test_run_study_json_serialisable(): ...     # json.dumps(result) succeeds; omitted list echoed in meta
```

Use `StudyConfig(draws=500, boot=200)` in tests to keep them fast.

- [ ] **Step 2: Run, verify FAIL**
- [ ] **Step 3: Implement** `StudyConfig`, `run_study`, `render_markdown`, and the CLI.
- [ ] **Step 4: Run the whole file, verify PASS** — `"$PY" -X utf8 -m pytest tools/test_event_study.py` → all pass.
- [ ] **Step 5: Commit** `feat(event-study): run_study, report, CLI`

### Task 6: Seed events and freeze the pre-registration

**Files:**
- Modify: `data/events/policy_events.csv`
- Create: `trading-wiki/wiki/analyses/Policy-Event-Study-Pre-Registration.md`
- Modify: `trading-wiki/wiki/index.md`, `trading-wiki/wiki/log.md`, `trading-wiki/wiki/analyses/Open-Backlog.md` (append entries only — these files have unrelated uncommitted edits; stage hunks for this task only with `git add -p`)

- [ ] **Step 1: Fill the CSV** — every scheduled MPC decision from 2016-10-04 to the latest held meeting (label from repo-rate change), the 3 unscheduled moves (`scheduled=0`), and every Union Budget from 2011 (full + interim, incl. July 2014/2019/2024 full budgets). `time_ist`: copy each announcement time from its RBI press release (it changed over the years); Budget `11:00`.
- [ ] **Step 2: Verify every row** against RBI press releases (rbi.org.in "Monetary Policy Statement") and PIB / indiabudget.gov.in; put the page URL in `source_url`. Unverifiable rows: keep, write `UNVERIFIED` in `notes`, and the pre-registration states how many.
- [ ] **Step 3: Validate** — `"$PY" -X utf8 -c "import sys; sys.path.insert(0,'tools'); import event_study as e; d=e.load_events('data/events/policy_events.csv', scheduled_only=False); print(d.groupby(['event_type','label']).size())"` → counts print, no error.
- [ ] **Step 4: Write the pre-registration page** — hypotheses P1, P2, S1–S3, exploratory list, null designs, windows, the decision rule (spec §3.4 verbatim), event counts per bucket from Step 3, and "No real-data run has been made at the time of this commit."
- [ ] **Step 5: Commit** CSV + wiki page + index/log/backlog hunks: `docs(event-study): seed policy events, pre-register study`. Record the commit hash for Task 7.

### Task 7: Run on real data and record the result

**Files:**
- Create: `output/event_study/<date>_mpc_budget.{json,md}` (generated)
- Create: `trading-wiki/wiki/analyses/Policy-Event-Study-Result.md`
- Modify: `trading-wiki/wiki/index.md`, `trading-wiki/wiki/log.md`, `trading-wiki/wiki/analyses/Open-Backlog.md`; the stale rec_audit note about Yahoo sector history (`tools/rec_audit_job.py:54-57` comment) — correct it to the 2026-10-26 probe.

- [ ] **Step 1: Run** — `"$PY" -X utf8 tools/event_study_run.py --events mpc,budget` → prints the md path; runtime < 5 min.
- [ ] **Step 2: Sanity-check** the report: per-sector n roughly equals event count minus pre-2011 sector-start losses; `snapped` rows are exactly the Saturday/holiday dates; no `NaN` in primary rows.
- [ ] **Step 3: Write the result page** — link the pre-registration commit hash, paste primary/secondary tables, verdict lines as produced (no re-interpretation), exploratory highlights labelled exploratory, limitations (decision ≠ surprise; small buckets).
- [ ] **Step 4: Run claims lint** — `"$PY" -X utf8 tools/claims_lint.py` → no new stale claims (fix any it flags in the pages touched).
- [ ] **Step 5: Run full suite** — `run_tests.bat` → all green.
- [ ] **Step 6: Commit** `feat(event-study): first MPC/Budget run and result`
