# Plan-Odds Baseline (B-183) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score every simulated trade plan against a no-edge baseline (block-bootstrap of the stock's own pre-entry daily bars), measure each scanner against it as pre-registered, and show each Watchlist plan's no-edge odds.

**Architecture:** A pure engine `tools/plan_baseline.py` builds 2,000 vectorised price paths per plan from 5-bar blocks of past OHLC-to-previous-close ratios and scores them with the same rules as `backtest._simulate_plan`. The harness's `keep_trades` records gain the fields the engine needs. A study script `tools/plan_baseline_study.py` runs the pre-registered test; `plan_status.judge` adds the odds to the Watchlist column.

**Tech Stack:** Python 3.11, numpy, pandas, scipy (t-test), pytest (`testpaths = tools`, tests sit next to modules as `tools/test_*.py`).

**Spec:** `trading-wiki/wiki/analyses/Plan-Odds-Baseline-Pre-Registration.md` (B-183). Every number below is copied from it; if they ever disagree, the pre-registration wins and the plan is wrong.

## Global Constraints

- Engine constants: `REPLAYS = 2000`, `BLOCK = 5`, `LOOKBACK = 500`, `MIN_POOL = 250`, `SEED = 19`.
- Per-trade seed: `SEED ^ zlib.crc32(f"{symbol}:{entry_idx}".encode())`.
- Pool = ratio rows describing bars **strictly before** `entry_idx`; never a bar at or after it.
- Scoring mirrors `_simulate_plan` fixed exit: stop before target each bar, tie → stop, fills at the level, R net of the cost model, outcomes `stop|target|time|open`, short = exact mirror, degenerate plan → `None`.
- Path length = `min(horizon, len(df) - 1 - entry_idx) + 1` bars, where `horizon = max_bars if time_stop is None else min(max_bars, int(time_stop))`.
- Study harness: `cost_model=bt.COST_INDIAN`, `signal_mode="fresh"`, `fill_model="market"`, `keep_trades=True`; panel `nu.symbols("nifty500")[0:300]`, `days=1500`.
- Verdict floors: ≥ 30 symbols, ≥ 100 baselined trades; Holm–Bonferroni family α 0.05, two-sided; sign of mean `d` stable in ≥ 2 of 3 entry-date thirds.
- Placebo gate: `|mean d| ≤ 0.05` or `p ≥ 0.05`, else no scanner verdict is written.
- **The pre-registration commit (Task 0) lands before any task runs the study on real data.**
- Run tests with `py -3 -X utf8 -m pytest`; run scripts with `py -3 -X utf8 tools/<script>.py`.

## Review Focus

1. **Trade too early in the history** (fewer than 250 pre-entry ratio rows): engine returns `None`; the study counts it as `unbaselined` and reports it beside the verdict, never drops it. Test in Task 1.
2. **NaN or zero-close bars inside the pool** (data gaps, suspended days): those ratio rows are removed before blocks are drawn, and a block never spans a removed row. Test in Task 1.
3. **Trade near the end of the data** (fewer bars left than the horizon): the null path is shortened to the bars the real trade had, so a late trade's `open` outcome is compared like for like. Test in Task 1.
4. **Short plans:** a stop above the entry is scored as the mirror, not a sign flip. Test in Task 1.
5. **Watchlist row whose bars cannot be baselined:** the cell still shows the status and R; the odds are omitted, never shown as 0 %. Test in Task 4.

---

### Task 0: Commit the pre-registration

**Files:**
- Commit (already written): `trading-wiki/wiki/analyses/Plan-Odds-Baseline-Pre-Registration.md`, `trading-wiki/wiki/analyses/Open-Backlog.md` (B-183 row), `trading-wiki/wiki/index.md`, `trading-wiki/wiki/log.md`, this plan.

- [ ] **Step 1: Confirm nothing has been scored yet**

Run: `git log --oneline -- tools/plan_baseline*.py`
Expected: no output.

- [ ] **Step 2: Commit**

```bash
git add trading-wiki/wiki/analyses/Plan-Odds-Baseline-Pre-Registration.md trading-wiki/wiki/analyses/Open-Backlog.md trading-wiki/wiki/index.md trading-wiki/wiki/log.md docs/superpowers/plans/2026-10-25-plan-odds-baseline.md
git commit -m "pre-reg(b183): no-edge plan-odds baseline -- fixed before any trade is scored"
```

---

### Task 1: The engine

**Files:**
- Create: `tools/plan_baseline.py`
- Test: `tools/test_plan_baseline.py`

**Interfaces:**
- Consumes: `backtest.COST_GROSS`, `CostModel.round_trip_pct(entry, exit_px)`, `backtest._simulate_plan` (tests only).
- Produces:
  - `ohlc_ratios(df: pd.DataFrame) -> np.ndarray`: shape `(len(df), 4)`; row `i` = open, high, low, close of bar `i` divided by the close of bar `i-1`; row 0 and any row touching a NaN or non-positive price is NaN.
  - `null_plan_odds(df, entry_idx: int, entry: float, stop: float, target: float, max_bars: int, time_stop: float | None = None, side: str = "long", cost_model=None, replays: int = REPLAYS, block: int = BLOCK, lookback: int = LOOKBACK, seed: int = SEED, n_bars: int | None = None) -> dict | None`
    returning `{"p_target", "p_stop", "p_open", "exp_r", "n_pool", "n_bars", "replays", "block", "seed"}`; `p_open` covers both `time` and `open` outcomes. `n_bars=None` means the data-limited length from Global Constraints (the study's like-for-like case); an explicit `n_bars` overrides it for forward-looking use (Task 4), and `entry_idx` may then equal `len(df)`.
  - `trade_seed(symbol: str, entry_idx: int) -> int`.

- [ ] **Step 1: Write the failing tests**

```python
def _walk(n, sigma=0.015, seed=1): ...  # Gaussian random-walk OHLC frame, helper in the test file

def test_parity_with_simulate_plan_on_a_one_block_pool():
    # bars before entry repeat one 5-bar block forever; bars after entry continue the
    # same block, so every replay is that exact path
    r = pb.null_plan_odds(df, entry_idx, entry, stop, target, max_bars=20)
    sim = bt._simulate_plan(df, entry_idx, entry, stop, target, 20)
    assert abs(r["exp_r"] - sim["r"]) < 1e-9
    assert r[{"stop": "p_stop", "target": "p_target"}.get(sim["outcome"], "p_open")] == 1.0

def test_calibrated_on_a_random_walk():
    # >= 2000 random plans (stop 1 x sigma*price, target 2 x) on a 6000-bar walk
    assert abs(np.mean(realised_r) - np.mean(baseline_exp_r)) <= 0.03

def test_pool_never_sees_the_entry_bar_or_later():
    a = pb.null_plan_odds(df, 600, ...); df2 = df.copy(); df2.iloc[600:, :] *= 3.0
    assert pb.null_plan_odds(df2, 600, ...) == a

def test_thin_pool_returns_none():          # entry_idx = 200 -> fewer than 250 rows
def test_nan_rows_dropped_and_blocks_do_not_span_them():
    # NaN injected at bar 300; result equals the run on a frame where that row's
    # ratios are removed, and n_pool == valid rows
def test_path_is_shortened_at_the_end_of_data():   # entry 5 bars from the end -> n_bars == 5
def test_explicit_n_bars_overrides_and_allows_entry_past_the_data():
    r = pb.null_plan_odds(df, len(df), entry, stop, target, max_bars=60, n_bars=61)
    assert r["n_bars"] == 61
def test_short_is_the_mirror():
    # long plan on df vs short plan on the price-inverted frame (1/price, high<->low)
    assert abs(long["p_target"] - short["p_target"]) < 1e-12
def test_degenerate_plan_returns_none():    # stop above a long entry; target behind entry
def test_same_seed_same_numbers_and_trade_seed_is_stable():
    assert pb.trade_seed("RELIANCE", 812) == pb.trade_seed("RELIANCE", 812)
def test_probabilities_sum_to_one():
```

- [ ] **Step 2: Run to verify they fail**

Run: `py -3 -X utf8 -m pytest tools/test_plan_baseline.py -q`
Expected: FAIL, `ModuleNotFoundError: plan_baseline`.

- [ ] **Step 3: Implement `tools/plan_baseline.py`**

Module docstring cites B-183 and the pre-registration page. Validation and degenerate checks copy `_simulate_plan`'s (`risk <= 0`, target on the stop side → `None`).

Block draw and path, vectorised (this is the part the tests do not pin down):

```python
valid = np.flatnonzero(~np.isnan(ratios[lo:entry_idx]).any(axis=1)) + lo   # lo = max(1, entry_idx - lookback)
starts = [i for i in valid if all valid rows i..i+block-1 are consecutive]   # a block never spans a gap
n_blocks = ceil(n_bars / block)
pick = rng.choice(starts, size=(replays, n_blocks))
rows = (pick[:, :, None] + np.arange(block)).reshape(replays, -1)[:, :n_bars]   # (replays, n_bars)
r = ratios[rows]                                     # (replays, n_bars, 4)
prev_close = entry * np.cumprod(np.c_[np.ones(replays), r[:, :-1, 3]], axis=1)
high, low, close = prev_close * r[..., 1], prev_close * r[..., 2], prev_close * r[..., 3]
```

`MIN_POOL` counts valid rows. First-touch per replay: first bar index where the stop is touched and first where the target is touched (`argmax` on the boolean matrix, "never" = `n_bars`); stop wins ties. Exit price: stop, target, or the last close. Cost per exit price via `cost_model.round_trip_pct` (`np.vectorize` over the last-close column is fine). `rng = np.random.default_rng(seed)`.

- [ ] **Step 4: Run to verify they pass**

Run: `py -3 -X utf8 -m pytest tools/test_plan_baseline.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tools/plan_baseline.py tools/test_plan_baseline.py
git commit -m "feat(b183): no-edge plan baseline engine -- block bootstrap scored like _simulate_plan"
```

---

### Task 2: Harness trade records carry the plan's levels

**Files:**
- Modify: `tools/backtest.py` (`backtest_scanner`, the `_tr = {...}` record near line 733)
- Test: `tools/test_backtest_keep_trades_levels.py`

**Interfaces:**
- Produces: each `out["trades"]` dict additionally has `"target": float`, `"time_stop": float | None` (the value actually passed to `_simulate_plan`) and `"max_bars": int` (`max_h`).

- [ ] **Step 1: Write the failing test**

```python
def test_kept_trades_carry_target_time_stop_and_horizon():
    # one-symbol synthetic frame, a test scanner registered in sc.SCANNERS that fires once
    # with entry/stop/target/time_stop = 100/95/110/5
    tr = bt.backtest_scanner(name, ["X"], lambda s: df, keep_trades=True, fill_model="market")["trades"][0]
    assert (tr["target"], tr["time_stop"], tr["max_bars"]) == (110.0, 5.0, 60)
```

- [ ] **Step 2: Run to verify it fails**

Run: `py -3 -X utf8 -m pytest tools/test_backtest_keep_trades_levels.py -q`
Expected: FAIL, `KeyError: 'target'`.

- [ ] **Step 3: Add the three keys to `_tr`**

- [ ] **Step 4: Run it and the existing suite**

Run: `py -3 -X utf8 -m pytest tools -q`
Expected: all pass (the existing `keep_trades` users only read keys, so extra keys change nothing).

- [ ] **Step 5: Commit**

```bash
git add tools/backtest.py tools/test_backtest_keep_trades_levels.py
git commit -m "feat(b183): keep_trades records carry target, time_stop and horizon"
```

---

### Task 3: The pre-registered study

**Files:**
- Create: `tools/plan_baseline_study.py`
- Test: `tools/test_plan_baseline_study.py`
- Output: `tools/cache/plan_baseline_study.json`

**Interfaces:**
- Consumes: `pb.null_plan_odds`, `pb.trade_seed`, Task 2's trade keys, `bt.backtest_scanner`, `sc.SCANNERS`, `nu.symbols`, `sp.fetch_ohlcv`.
- Produces:
  - `scanner_stats(trades: list[dict]) -> dict` with `n_trades`, `n_symbols`, `n_unbaselined`, `mean_d`, `t`, `p`, `thirds` (three mean-d values by entry date), `realised_target_rate`, `mean_p_target`, `noise_stop_share` (share with `p_stop ≥ 0.60`). Each input trade already carries `r`, `exp_r`, `p_target`, `p_stop`, `outcome`, `symbol`, `entry_date`.
  - `holm(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, bool]`.
  - `verdict(stats: dict, significant: bool) -> str`, one of `BEATS BASELINE | BELOW BASELINE | AT BASELINE | THIN`.
  - `main() -> int`, the run.

Placebo scanner `_B183 Placebo`, registered in this module like `abcd_stop_study` registers its arms: fires when `len(df) % 5 == 0`, entry = last close (filled next open by `fill_model="market"`), stop = entry − 1.0×ATR14, target = entry + 2.0×ATR14, `time_stop` 10, using `sc._atr_series(df, 14)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_holm_matches_the_textbook_example():
    assert sps.holm({"a": 0.01, "b": 0.04, "c": 0.03}) == {"a": True, "b": False, "c": False}
def test_stats_cluster_by_symbol():
    # 1 symbol with 200 trades of d=+1 and 40 symbols with 1 trade of d=-0.1
    # -> n_symbols 41, mean_d computed over symbol means (negative), not over trades
def test_verdict_floors_and_stability():
    assert sps.verdict({"n_symbols": 29, "n_trades": 500, ...}, True) == "THIN"
    assert sps.verdict({..., "mean_d": 0.2, "thirds": [0.1, -0.1, -0.2]}, True) == "AT BASELINE"   # 1/3 agree
    assert sps.verdict({..., "mean_d": 0.2, "thirds": [0.1, 0.3, -0.1]}, True) == "BEATS BASELINE"
    assert sps.verdict({..., "mean_d": -0.2, "thirds": [-0.1, -0.3, 0.1]}, True) == "BELOW BASELINE"
    assert sps.verdict({..., "mean_d": 0.2, "thirds": [0.1, 0.3, 0.1]}, False) == "AT BASELINE"
def test_unbaselined_trades_are_counted_not_dropped():
    # trades with exp_r None -> n_unbaselined, excluded from d, present in n_trades
def test_placebo_scanner_is_registered_and_fires_every_fifth_bar():
```

- [ ] **Step 2: Run to verify they fail**

Run: `py -3 -X utf8 -m pytest tools/test_plan_baseline_study.py -q`
Expected: FAIL, `ModuleNotFoundError: plan_baseline_study`.

- [ ] **Step 3: Implement `tools/plan_baseline_study.py`**

Docstring summarises the pre-registration in the `abcd_stop_study.py` style (panel, harness, statistic, floors, decision rule, prior). `main()`: run the placebo first; if it fails the gate, write the JSON with `"placebo_failed": true` and no scanner verdicts, print why, return 1. Otherwise loop every non-`_` scanner, attach `null_plan_odds(...)` to each kept trade (`df` from the shared fetch cache, `seed=pb.trade_seed(symbol, entry_idx)`, `side`, `cost_model=bt.COST_INDIAN`), compute `scanner_stats`, apply `holm` across scanners that meet the floors, then `verdict`. JSON carries `"preregistered": "2026-10-25"`, panel, harness settings, placebo block, and per-scanner stats and verdicts.

- [ ] **Step 4: Run to verify they pass**

Run: `py -3 -X utf8 -m pytest tools/test_plan_baseline_study.py -q`
Expected: all pass.

- [ ] **Step 5: Commit (code only, before the run)**

```bash
git add tools/plan_baseline_study.py tools/test_plan_baseline_study.py
git commit -m "feat(b183): pre-registered plan-baseline study script (not yet run)"
```

---

### Task 4: Watchlist shows each plan's no-edge odds

**Files:**
- Modify: `tools/plan_status.py` (`judge`, `label`)
- Test: `tools/test_plan_status.py` (add tests)

**Interfaces:**
- Consumes: `pb.null_plan_odds`.
- Produces: `judge(...)` output gains `"null_odds": {"p_target", "p_stop"} | None`, filled for `PENDING` (pool before the card-day bar's successor, `entry_idx = sig + 1`, entry at the card's entry) and `LIVE` (`entry_idx` = fill bar, entry = fill price), with `max_bars=MAX_WALK_BARS`, the card's `time_stop`, **`n_bars` = full horizon + 1** (forward odds, not cut at today's bar), the default `SEED`, gross of costs like the rest of `judge`. For LIVE these are the odds as of the fill, and the label says `at entry`. `label()` appends `no-edge T 31% / S 52%` for PENDING and `no-edge at entry T 31% / S 52%` for LIVE, only when `null_odds` is present.

- [ ] **Step 1: Write the failing tests**

```python
def test_live_plan_carries_no_edge_odds():          # 600-bar walk, plan filled, still open
    st = ps.judge(card, run_date, df)
    assert st["status"] == "LIVE" and 0 <= st["null_odds"]["p_target"] <= 1
    assert "no-edge T" in ps.label(st)
def test_pending_plan_carries_no_edge_odds():
def test_unbaselineable_row_omits_odds_not_zero():  # 60 bars of history -> pool too thin
    st = ps.judge(card, run_date, short_df)
    assert st["null_odds"] is None and "no-edge" not in ps.label(st)
def test_closed_plans_show_no_odds():                # TARGET HIT / STOP HIT rows unchanged
```

- [ ] **Step 2: Run to verify they fail**

Run: `py -3 -X utf8 -m pytest tools/test_plan_status.py -q`
Expected: the four new tests FAIL.

- [ ] **Step 3: Implement in `judge` and `label`**

- [ ] **Step 4: Run the file and the full suite**

Run: `py -3 -X utf8 -m pytest tools -q`
Expected: all pass.

- [ ] **Step 5: Verify in the app on a fresh process**

Start the desk on :8502 (the running :8501 keeps old modules), open the Watchlist, and confirm a PENDING or LIVE row shows `no-edge T x% / S y%` and a closed row does not. Screenshot it.

- [ ] **Step 6: Commit**

```bash
git add tools/plan_status.py tools/test_plan_status.py
git commit -m "feat(b183): Watchlist plan column shows the plan's no-edge odds"
```

---

### Task 5: Run the study and record the outcome

**Files:**
- Output: `tools/cache/plan_baseline_study.json`
- Create: `trading-wiki/wiki/analyses/Plan-Odds-Baseline-Measured.md`
- Modify: the pre-registration page (banner + Outcome), `Open-Backlog.md` (B-183 row), `index.md`, `log.md`

- [ ] **Step 1: Confirm Task 0's commit precedes this run**

Run: `git log --oneline -1 -- trading-wiki/wiki/analyses/Plan-Odds-Baseline-Pre-Registration.md`
Expected: the `pre-reg(b183)` commit.

- [ ] **Step 2: Run in the background (long)**

Run: `py -3 -X utf8 tools/plan_baseline_study.py`
Expected: exit 0 with a per-scanner verdict table, or exit 1 with "placebo failed" and no verdicts.

- [ ] **Step 3: Write the results page** in the house style of `Order-Block-Rules-Measured`: placebo result first, then each verdict with n, symbols, mean d, Holm p and thirds, then the descriptive secondaries flagged as non-promotable, then the prior versus the outcome. Apply only the decision-table actions; file a follow-up item for each BELOW BASELINE scanner.

- [ ] **Step 4: Update the pre-registration banner and Outcome, the B-183 backlog row, index and log.**

- [ ] **Step 5: Run the stale-claims lint**

Run: `py -3 -X utf8 tools/claims_lint.py`
Expected: no new stale figures; fix any that cite the old zero-null plan R as an edge.

- [ ] **Step 6: Commit**

```bash
git add tools/cache/plan_baseline_study.json trading-wiki/wiki/analyses/Plan-Odds-Baseline-Measured.md trading-wiki/wiki/analyses/Plan-Odds-Baseline-Pre-Registration.md trading-wiki/wiki/analyses/Open-Backlog.md trading-wiki/wiki/index.md trading-wiki/wiki/log.md
git commit -m "measure(b183): plan-odds baseline -- <headline verdict>"
```
