# Pick Re-score Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A nightly job that re-scores every open Opportunity pick (rating + parts, today's scanners, full score, 500-universe rank), plus Pick replay drift / attribution / decay views and a D marker in the Multi-Chart.

**Architecture:** `rating.rating_detail` is the one scorer for the rating's parts. The shortlist job (`opportunity_daily`) rates its whole 500-name universe into `universe_ratings` (trading_bramha.db). A new job `rec_rescore_job.py` (I/O) + `rec_rescore.py` (pure) writes `pick_scores` rows (rec_audit.db) at 17:45. Read-only display helpers live in `rec_audit_replay.py`; the page and `replay_mode.js` render them.

**Tech Stack:** Python 3.14, pandas, sqlite3, Plotly, Streamlit, pytest; vanilla JS tested through node.

**Spec:** `docs/superpowers/specs/2026-11-26-pick-rescore-design.md`

## Global Constraints

- Every stored date is a bar date (NSE session), never `date.today()` — machine is US Eastern, NSE is IST.
- `DOWNGRADE_POINTS = 15` (a named prior, untested — say so wherever D shows).
- `TRACK_SESSIONS = 63` sessions after entry, plus pending picks.
- Pick fetch: `days=400`, `min_turnover=0` (no liquidity floor in an audit).
- Display minus sign is `−` (U+2212); arrows are `→`.
- The universe-rating step must never fail or alter the shortlist.
- No back-filled numbers: older picks show "tracking since <date>".
- Tests: no network; run from `tools/` with `py -3 -m pytest`.
- Commit only with the owner's OK; never push.

## Review Focus

1. A pick whose symbol no longer fetches (renamed, delisted, suspended) → no row, counted in `##RESULT`, the run continues. (Task 4)
2. A pick with no stored pick-day `overall_rating` → `rating_drift` None, `downgrade` 0, the drift line says "no pick-day rating". (Tasks 3, 5)
3. Re-running the job the same night → rows replaced, never duplicated. (Task 4)
4. The Nifty frame fails to fetch → the job writes nothing and exits 1 (never dates rows by the local clock). (Task 4)
5. One symbol with two open episodes (re-picked after a gap) → one fetch, one row per episode. (Task 4)

---

### Task 1: `rating_detail` — the rating's parts as numbers

**Files:**
- Modify: `tools/rating.py:79-107`
- Test: `tools/test_rating_detail.py` (create)

**Interfaces:**
- Produces: `rating.rating_detail(df, nifty_df, weights=None) -> dict | None` with keys `rating:int, minervini:int, technofunda:int, canslim:int, canslim_n:int, ew_conf:int, cs_near_high, cs_volume, cs_market, cs_rs` (each `bool | None`). None when scoring raises.

- [ ] **Step 1: Write the failing tests** — a synthetic 300-bar uptrend frame and a 300-bar Nifty frame built in the test.

```python
def test_detail_matches_overall_rating():
    d = rating.rating_detail(df, nifty)
    r, bd = rating.overall_rating(df, nifty)
    assert d["rating"] == r
    assert bd == {"Minervini": f"{d['minervini']}/8", "TechnoFunda": f"{d['technofunda']}/6",
                  "CANSLIM": f"{d['canslim']}/{d['canslim_n']}", "EW conf": str(d["ew_conf"])}

def test_detail_without_benchmark_has_none_checks():
    d = rating.rating_detail(df, None)
    assert d["cs_market"] is None and d["cs_rs"] is None and d["canslim_n"] == 2

def test_detail_is_none_when_scoring_fails():
    assert rating.rating_detail(df.head(3), nifty) is None
    assert rating.overall_rating(df.head(3), nifty) == (None, {})
```

- [ ] **Step 2:** `py -3 -m pytest test_rating_detail.py -v` → FAIL (`rating_detail` missing).
- [ ] **Step 3:** Implement `rating_detail`; map CANSLIM condition labels to `cs_*` keys by their letter prefix (N, S, M, L). Rewrite `overall_rating` to call it and format today's breakdown strings ("n/a" when `canslim_n == 0`).
- [ ] **Step 4:** `py -3 -m pytest test_rating_detail.py -v` and `py -3 -m pytest -q -k "rating or opportunity"` → PASS.
- [ ] **Step 5:** Commit (`feat(rescore): rating_detail exposes the rating's parts`).

---

### Task 2: Universe ratings in the shortlist job

**Files:**
- Modify: `tools/portfolio_db.py` (table in `init_db`; `save_universe_ratings`, `get_universe_ratings`)
- Modify: `tools/opportunity_daily.py` (`rate_universe`; call in `run()` after tagging)
- Test: `tools/test_universe_ratings.py` (create)

**Interfaces:**
- Consumes: `rating.rating_detail`.
- Produces:
  - `opportunity_daily.rate_universe(symbols: list[str], fetch, nifty_df, version: str) -> list[dict]` — one dict per rated symbol: the `rating_detail` keys + `symbol, universe_rank, universe_size, model_version`. Rank: rating descending, `method="min"`, 1 = best; unrated names are left out.
  - `portfolio_db.save_universe_ratings(rows: list[dict], session_date: str, run_date: str) -> int` — replaces that `session_date`.
  - `portfolio_db.get_universe_ratings(session_date: str, symbols: list[str] | None = None) -> pd.DataFrame` — empty frame when none.
  - Table `universe_ratings` with the columns in spec §2, PK `(session_date, symbol)`.

- [ ] **Step 1: Write the failing tests** (monkeypatch `portfolio_db.DB_PATH` to `tmp_path`, call `init_db()`; stub `rating.rating_detail` with a lookup).

```python
def test_rank_is_descending_with_shared_ties():
    rows = od.rate_universe(["A", "B", "C", "D"], fetch, None, "v1")   # ratings 80, 60, 80, None
    got = {r["symbol"]: (r["universe_rank"], r["universe_size"]) for r in rows}
    assert got == {"A": (1, 3), "C": (1, 3), "B": (3, 3)}

def test_save_replaces_the_session(tmp_db):
    db.save_universe_ratings(rows_a, "2026-11-26", "2026-11-26")
    db.save_universe_ratings(rows_b, "2026-11-26", "2026-11-26")
    assert sorted(db.get_universe_ratings("2026-11-26")["symbol"]) == sorted(r["symbol"] for r in rows_b)

def test_a_rating_failure_never_breaks_the_shortlist(monkeypatch):
    monkeypatch.setattr(od, "rate_universe", boom)   # raises RuntimeError("boom")
    # every network call in run() stubbed: fetch_bhavcopy_top_volume, fetch_nifty50,
    # build_constituent_table, rank_groups, stocks_in_groups, run_scanner_pipeline,
    # overall_rating, save_daily_opportunities / save_opportunity_cards (recorders)
    res = od.run(universe_size=4, top_n=10, save=True, run_date="2026-11-26")
    assert res["ok"] and saved_shortlist
    assert res["universe_ratings"] == {"ok": False, "error": "boom"}
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. In `run()`, only when `save`: `session_date` = last index date of `nifty_df` (when None, record `{"ok": False, "error": "no benchmark"}` and skip). Call `rate_universe(universe, fetch, nifty_df, version)` then `save_universe_ratings`, inside `try/except Exception` that logs and records `{"ok": False, "error": str(e)}`; success records `{"ok": True, "n": len(rows), "session_date": ...}` in `res["universe_ratings"]` (every return path that reaches the step). Move `version = model_version()` above the call. Append `· universe ratings N` to the `##RESULT` line.
- [ ] **Step 4:** `py -3 -m pytest test_universe_ratings.py -v` and `py -3 -m pytest -q -k opportunity` → PASS.
- [ ] **Step 5:** Commit (`feat(rescore): shortlist job stores the 500-universe ratings`).

---

### Task 3: `rec_rescore.py` — pick selection and row building (pure)

**Files:**
- Create: `tools/rec_rescore.py`
- Test: `tools/test_rec_rescore.py` (create)

**Interfaces:**
- Consumes: Task 1's detail dict; a scanner hit as returned by `opportunity_hub.run_scanner_pipeline` (`scanners, families, edge_points, best_score`); a universe row (`universe_rank, universe_size`).
- Produces:
  - Constants `DOWNGRADE_POINTS = 15`, `TRACK_SESSIONS = 63`.
  - `select_open(eps: pd.DataFrame) -> pd.DataFrame` — `source == "opportunity"` and (`status == "pending"` or (`status in ("open", "matured")` and `sessions <= TRACK_SESSIONS`)).
  - `build_row(ep: Mapping, bars: pd.DataFrame, session: pd.Timestamp, detail: dict | None, hit: dict | None, uni: Mapping | None, universe_available: bool, version: str) -> dict | None` — None when `bars` has no bar on `session` or `detail` is None. Keys = spec §3's `pick_scores` columns plus `universe_status` ∈ `"ranked" | "not_in_universe" | "no_universe"` (`no_universe` when `universe_available` is False). `sessions_since_entry` = bars dated after `rec_date` up to `session`. `original_still_firing` = how many of the episode's `scanners` (comma list) appear in `hit["scanners"]`; 0 when `hit` is None. `score_today` = `round(W_RATING·rating + W_SCANNER·min(best_score,100) + W_CONFLUENCE·confluence_pct(edge_points), 1)` with `opportunity_daily`'s weights; scanner and confluence parts 0 with no hit. `rating_drift` None when `overall_rating` is missing.
  - `first_downgrade(scores: pd.DataFrame) -> str | None` — earliest `session_date` with `downgrade == 1`.

- [ ] **Step 1: Write the failing tests.**

```python
def test_select_open_window_and_sources():
    assert set(rr.select_open(eps)["episode_id"]) == {"pending_today", "open_5", "matured_63"}
    # excluded: matured_64, a scanner-source row, data_suspect, no_data

def test_drift_and_downgrade_threshold():
    assert rr.build_row(ep(overall_rating=70), bars, S, det(rating=55), None, None, True, "v")["downgrade"] == 1
    r = rr.build_row(ep(overall_rating=70), bars, S, det(rating=56), None, None, True, "v")
    assert r["rating_drift"] == -14 and r["downgrade"] == 0

def test_no_pick_day_rating_gives_no_drift():
    r = rr.build_row(ep(overall_rating=None), bars, S, det(rating=50), None, None, True, "v")
    assert r["rating_drift"] is None and r["downgrade"] == 0

def test_no_bar_tonight_gives_no_row():
    assert rr.build_row(ep(), bars_ending_day_before, S, det(), None, None, True, "v") is None

def test_scanner_part_and_rank():
    r = rr.build_row(ep(scanners="A, B, C"), bars, S, det(rating=60),
                     {"scanners": ["B", "X"], "families": ["f1"], "edge_points": 1.0, "best_score": 80},
                     {"universe_rank": 146, "universe_size": 500}, True, "v")
    assert r["original_still_firing"] == 1 and r["scanners_today"] == "B, X"
    assert (r["universe_rank"], r["universe_size"], r["universe_status"]) == (146, 500, "ranked")
    assert r["score_today"] == round(0.45 * 60 + 0.30 * 80 + 0.25 * oh.confluence_pct(1.0), 1)

def test_universe_status():
    assert rr.build_row(ep(), bars, S, det(), None, None, True, "v")["universe_status"] == "not_in_universe"
    assert rr.build_row(ep(), bars, S, det(), None, None, False, "v")["universe_status"] == "no_universe"

def test_first_downgrade():
    assert rr.first_downgrade(scores_d_on("2026-12-03", "2026-12-05")) == "2026-12-03"
    assert rr.first_downgrade(scores_without_d) is None
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** `py -3 -m pytest test_rec_rescore.py -v` → PASS.
- [ ] **Step 5:** Commit (`feat(rescore): pick selection and score rows`).

---

### Task 4: `rec_rescore_job.py` — fetch, score, store, schedule

**Files:**
- Create: `tools/rec_rescore_job.py`
- Modify: `tools/opportunity_daily.py` (`_FrameCache` / `_FetchRouter` gain `min_turnover: float | None = None`, passed through to `sp.fetch_ohlcv`; default behaviour unchanged)
- Modify: `tools/scheduler_core.py` (job `rec_rescore`)
- Test: `tools/test_rec_rescore_job.py` (create); `tools/test_scheduler_core.py` (one test)

**Interfaces:**
- Consumes: Tasks 1–3; `rec_audit_job.load_latest`; `portfolio_db.get_universe_ratings`.
- Produces:
  - `DB_PATH = rec_audit_job.DB_PATH`; `connect(db_path=DB_PATH)` creating `pick_scores` (PK `(episode_id, session_date)`).
  - `run(*, eps=None, fetch_for=None, nifty_df=None, scan=None, universe=None, db_path=DB_PATH) -> dict` returning `{"ok", "session", "written", "skipped": {symbol: reason}, "not_in_universe", "downgrades"}` (plus `"reason"` when not ok). Defaults: `eps = select_open(load_latest()["episodes"])`; `fetch_for = _FetchRouter(days=400, min_turnover=0)`; `nifty_df = sp.fetch_nifty50(days=400)` (NaN closes dropped); `scan = lambda syms, ff, bench: oh.run_scanner_pipeline(syms, ff, benchmark_df=bench, attach_pead=False)`; `universe = portfolio_db.get_universe_ratings`.
  - `load_scores(episode_ids: list[str] | None = None, db_path=DB_PATH) -> pd.DataFrame` — sorted by `episode_id, session_date`; empty frame with the columns before the first run (and when the DB file is new).
  - `pick_day_universe(symbol: str, rec_date: str) -> dict | None` — the symbol's `universe_ratings` row on `rec_date`.
  - `main(argv=None) -> int` — `--db` option; prints `##RESULT <session> · N picks re-scored · K skipped · U not in today's 500 · D downgrades` and returns 0; returns 1 with `FAILED: <reason>` when `run` is not ok.
  - `scheduler_core.JOBS["rec_rescore"]`: `label="Pick Re-score"`, `kind="daily"`, `default_time="17:45"`, `task_name="TradingBramha-RecRescore"`, command runs `rec_rescore_job.py`; desc says what it stores and that D is a prior.

- [ ] **Step 1: Write the failing tests** (fake frames, a fake `scan`, `tmp_path` DB).

```python
def test_run_writes_one_row_per_open_episode(tmp_path):
    rep = job.run(eps=eps, fetch_for=fake_fetch_for, nifty_df=nifty, scan=fake_scan,
                  universe=fake_universe, db_path=tmp_path / "r.db")
    got = job.load_scores(db_path=tmp_path / "r.db")
    assert rep["ok"] and rep["written"] == len(got) == 3
    assert set(got["session_date"]) == {nifty.index[-1].strftime("%Y-%m-%d")}

def test_rerun_replaces(tmp_path):
    for _ in range(2):
        job.run(eps=eps, fetch_for=fake_fetch_for, nifty_df=nifty, scan=fake_scan,
                universe=fake_universe, db_path=tmp_path / "r.db")
    assert len(job.load_scores(db_path=tmp_path / "r.db")) == 3

def test_unfetchable_symbol_is_counted_not_fatal(tmp_path):
    rep = job.run(eps=eps_plus_GONE, ...)
    assert rep["skipped"] == {"GONE": "no bars"} and rep["written"] == 3

def test_two_episodes_one_symbol_fetch_once(tmp_path):
    rep = job.run(eps=eps_same_symbol_twice, fetch_for=counting_fetch_for, ...)
    assert counting_fetch_for.calls["SAME"] == 1 and rep["written"] == 2

def test_no_benchmark_writes_nothing(tmp_path):
    rep = job.run(eps=eps, nifty_df=empty_frame, ...)
    assert not rep["ok"] and job.load_scores(db_path=tmp_path / "r.db").empty

def test_main_exits_1_when_run_fails(monkeypatch):
    monkeypatch.setattr(job, "run", lambda **k: {"ok": False, "reason": "no benchmark"})
    assert job.main([]) == 1

def test_load_scores_before_first_run_is_empty(tmp_path):
    assert job.load_scores(db_path=tmp_path / "none.db").empty

# test_scheduler_core.py
def test_rescore_runs_after_the_audit():
    j = sc.JOBS["rec_rescore"]
    assert j.kind == "daily" and j.default_time > sc.JOBS["rec_audit"].default_time
    assert "rec_rescore_job.py" in j.command
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. Session = `nifty_df.index[-1]` normalised; empty/None frame → not ok, nothing written. Fetch each distinct symbol once through `fetch_for(oh.DEFAULT_WINDOW)`; rate with `rating_detail(df, nifty_df)`; run `scan` once over the distinct fetched symbols; `universe(session_iso, symbols)` once — `universe_available = not frame.empty`. Write with `INSERT OR REPLACE`, adding `created_at`. `main` reconfigures stdout/stderr to UTF-8 like `rec_audit_job.main`.
- [ ] **Step 4:** `py -3 -m pytest test_rec_rescore_job.py test_scheduler_core.py -v` → PASS.
- [ ] **Step 5:** Commit (`feat(rescore): nightly re-score job and scheduler entry`).

---

### Task 5: Replay display helpers

**Files:**
- Modify: `tools/rec_audit_replay.py` (new section "Re-score: drift, attribution, decay"; `multichart_url` gains `ddate`)
- Test: `tools/test_rec_audit_replay.py`

**Interfaces:**
- Consumes: `pick_scores` rows (Task 4 `load_scores`), `pick_day_universe` dict, `rec_rescore.DOWNGRADE_POINTS`.
- Produces:
  - `drift_line(ep, scores: pd.DataFrame, pick_uni: dict | None) -> str`
  - `what_moved(ep, scores: pd.DataFrame, pick_uni: dict | None) -> str` — "" with fewer than two points to compare
  - `scanners_line(ep, scores: pd.DataFrame) -> str` — "" without rows or without original scanners
  - `decay_figure(ep, scores: pd.DataFrame)` — Plotly, two rows: rating vs sessions since entry (dashed pick-day line, dotted D line at pick − 15, D point at the first downgrade, "tracking since" annotation); universe rank with `autorange="reversed"`
  - `decay_table(eps: pd.DataFrame, scores: pd.DataFrame, h: int) -> pd.DataFrame` — columns `sessions_since_entry, winners_median, losers_median, n_winners, n_losers` over judged picks (`ret_{h}` present; loser = `failure`), median `rating_drift`
  - `multichart_url(ep, f, ddate: str | None = None)` — adds `ddate` when given

- [ ] **Step 1: Write the failing tests** (exact copy pinned):

```python
def test_drift_line_with_pick_rank():
    s = rows(rating=[60, 54], rank=[120, 146], size=[500, 500], status=["ranked"] * 2,
             dates=["2026-11-26", "2026-11-27"])
    assert rp.drift_line(ep(overall_rating=72), s, {"universe_rank": 9}) == \
        "Rating drift −18 (72 → 54) · rank #9 → #146 of 500 · tracking since 2026-11-26"

def test_drift_line_without_pick_rank():
    s = rows(rating=[55], rank=[146], size=[500], status=["ranked"], dates=["2026-11-26"])
    assert rp.drift_line(ep(overall_rating=50), s, None) == \
        "Rating drift +5 (50 → 55) · rank #146 of 500 today · tracking since 2026-11-26"

def test_drift_line_universe_states():
    out = rows(rating=[55], status=["not_in_universe"], dates=["2026-11-26"])
    none = rows(rating=[55], status=["no_universe"], dates=["2026-11-26"])
    assert rp.drift_line(ep(overall_rating=50), out, None) == \
        "Rating drift +5 (50 → 55) · not in today's 500 · tracking since 2026-11-26"
    assert rp.drift_line(ep(overall_rating=50), none, None) == \
        "Rating drift +5 (50 → 55) · rank starts with the next shortlist run · tracking since 2026-11-26"

def test_drift_line_edge_cases():
    assert rp.drift_line(ep(), empty_scores, None) == "Re-score tracking starts with the next nightly run."
    assert rp.drift_line(ep(overall_rating=None), rows(rating=[55], status=["ranked"], rank=[3],
                         size=[500], dates=["2026-11-26"]), None).startswith("Rating 55 (no pick-day rating)")

def test_what_moved_names_the_biggest_weighted_change():
    s = rows(minervini=[7, 4], technofunda=[5, 5], canslim=[3, 1], canslim_n=[4, 4], ew_conf=[35, 35],
             cs_rs=[1, 0], cs_volume=[1, 0], cs_near_high=[1, 1], cs_market=[1, 1],
             dates=["2026-11-26", "2026-11-27"])
    assert rp.what_moved(ep(), s, None) == \
        "Minervini 7/8 → 4/8 led the drop · lost: RS leader, volume · since 2026-11-26"

def test_scanners_line():
    assert rp.scanners_line(ep(scanners="A, B, C"), rows(original_still_firing=[2])) == \
        "2 of 3 original scanners still fire"

def test_multichart_url_carries_ddate():
    assert "ddate=2026-12-03" in rp.multichart_url(ep(), frame, ddate="2026-12-03")
    assert "ddate" not in rp.multichart_url(ep(), frame)

def test_decay_table_and_figure():
    t = rp.decay_table(judged_eps, scores, 21)
    assert list(t.columns) == ["sessions_since_entry", "winners_median", "losers_median",
                               "n_winners", "n_losers"]
    assert rp.decay_figure(ep(overall_rating=70), scores_one).data
```

Rules the tests pin and the implementer needs:
- No pick-day rating: the line starts `Rating 55 (no pick-day rating)` and keeps the rank and tracking parts.
- Weighted change per part, to pick what "led": Minervini Δ/8·35, TechnoFunda Δ/6·25, CANSLIM Δ(passes/n)·20, EW Δ/100·20. "led the drop" when negative, "led the rise" when positive. Base = `pick_uni` when given (then no suffix), else the first tracked row (suffix ` · since <first tracked date>`). CANSLIM flips named: near high, volume, market, RS leader; ` · lost: …` and/or ` · gained: …`.

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** `py -3 -m pytest test_rec_audit_replay.py -v` → PASS.
- [ ] **Step 5:** Commit (`feat(rescore): drift, attribution and decay helpers for Pick replay`).

---

### Task 6: D marker in the Multi-Chart

**Files:**
- Modify: `tools/replay_mode.js` (header comment, `parseReplay`, `markers`)
- Test: `tools/test_replay_mode.py`

**Interfaces:**
- Produces: `parseReplay(...).ddate` (`YYYY-MM-DD` or null); `markers(r, bars, vTime)` adds `{time: dayTime(r.ddate), position: 'aboveBar', shape: 'arrowDown', color: '#d29922', text: 'D'}` when `r.ddate` is set.

- [ ] **Step 1: Write the failing tests.**

```python
def test_parse_replay_reads_ddate():
    assert rpm("RPM.parseReplay(q).ddate", q="?replay=2026-10-16&ddate=2026-10-30") == "2026-10-30"
    assert rpm("RPM.parseReplay(q).ddate", q="?replay=2026-10-16&ddate=junk") is None

def test_d_marker_is_placed_and_sorted():
    r = rpm("RPM.markers(RPM.parseReplay(q), bars, null)",
            q="?replay=2026-08-07&ddate=2026-08-20", bars=_bars())
    d = [m for m in r if m["text"] == "D"]
    assert d and d[0]["time"] == rpm("RPM.dayTime('2026-08-20')")
    assert r == sorted(r, key=lambda m: m["time"])
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement; the header comment documents D as "re-score downgrade: rating ≥ 15 points below the pick day — a prior, not a measured signal". Confirm `tools/sw.js` serves `.js` network-first; change nothing there if so.
- [ ] **Step 4:** `py -3 -m pytest test_replay_mode.py -v` → PASS.
- [ ] **Step 5:** Commit (`feat(rescore): D downgrade marker in the Multi-Chart replay`).

---

### Task 7: Page wiring

**Files:**
- Modify: `tools/desk_pages/rec_audit_page.py` (`_snapshot`, `_replay_view`, `_lessons_tab`)
- Test: `tools/test_rec_audit_page.py`

**Interfaces:**
- Consumes: Task 4 `load_scores`, `pick_day_universe`; Task 5 helpers; `rec_rescore.first_downgrade`.
- Produces: `_rescore_for(ep) -> tuple[pd.DataFrame, dict | None]` (this pick's scores and pick-day universe row).

- [ ] **Step 1: Write the failing test** — `_rescore_for` returns an empty frame and None against an empty tmp DB (monkeypatch `rec_rescore_job.DB_PATH` and `portfolio_db.DB_PATH`).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement:
  - `_snapshot`: under the header line, `st.caption(drift_line)`, then `what_moved` and `scanners_line` when non-empty. Right column, under the MFE ladder: `decay_figure` when scores exist, captioned "D = rating 15+ points below the pick day — a prior, not a tested signal."
  - `_replay_view`: pass `ddate=first_downgrade(scores)` to `multichart_url`.
  - `_lessons_tab`: a "Confidence decay" subsection — `decay_table` as a line chart (winners vs losers median drift by session since entry) with the counts, captioned "Fills in as the nightly re-score accrues; descriptive, not causal." Empty state: "No re-scored picks yet — tracking starts with the next nightly run."
  - Scores read once per render via `st.cache_data(ttl=600)`.
- [ ] **Step 4:** `py -3 -m pytest test_rec_audit_page.py -v` → PASS.
- [ ] **Step 5:** Commit (`feat(rescore): Pick replay shows drift, what moved and the decay curve`).

---

### Task 8: First run and verification

- [ ] **Step 1:** Before Task 1, record the baseline: `py -3 -m pytest -q` (failures noted). Now rerun → no new failures.
- [ ] **Step 2:** Run the job for real: `py -3 tools/rec_rescore_job.py` → a `##RESULT` line with ~440 picks re-scored, every row `no_universe` (today's shortlist ran before the universe table existed).
- [ ] **Step 3:** Register the scheduled task the way the other jobs are registered (Scheduler Hub) — only with the owner's OK.
- [ ] **Step 4:** `preview_start {name: "dashboard-fresh"}` (:8502). Recommendation Audit › Pick replay on an open pick: drift line, scanners line, decay chart with one point and "tracking since"; the Multi-Chart link carries no `ddate`; Lessons tab shows the empty-state decay text. Screenshot for the owner.
- [ ] **Step 5:** Hand-over note in the shared notes folder.
