# Policy Event-Study Engine — Design

**Date:** 2026-10-26
**Status:** design approved in chat; spec awaiting review
**Origin:** review of marketontology.com/political — of its ideas, a measurable
policy event study was judged the one worth building first; the policy→sector map,
catalyst calendar and policy-uncertainty regime all depend on it to be measured.

## 1. Purpose

A reusable research tool that answers: *"On these event dates, did NIFTY and the
NSE sector indices move abnormally, compared with ordinary days?"* — and, for
labelled events, *"in the direction theory says?"*

It is a measuring instrument for the investment desk (see memory:
investment-desk-not-trading-system), not a signal generator. A null result is
calibration and is recorded as such. Every study is pre-registered on the wiki
before it runs.

First study: **RBI MPC decisions (Oct 2016 →)** and **Union Budgets (2011 →)**.

### Success criteria

- `event_study_run.py --events mpc,budget` produces a JSON + Markdown report with
  the four primary tests, three secondary tests and exploratory tables.
- On synthetic prices, a planted effect is detected and an un-planted control is not.
- Pre-registration page is committed before the first real run; result page after.

## 2. Architecture

```
data/events/policy_events.csv      seed events (one row per event)
tools/event_study.py               pure library (no file/network I/O except via injected loaders)
tools/event_study_run.py           CLI driver: loads, runs, writes output/event_study/<stamp>_<sets>.{json,md}
tools/test_event_study.py          pytest, no network
trading-wiki/wiki/analyses/Policy-Event-Study-Pre-Registration.md
trading-wiki/wiki/analyses/Policy-Event-Study-Result.md
```

### 2.1 Prices

- Source: Yahoo daily closes (`auto_adjust=True`) from 2010-01-01.
- Universe: `^NSEI` (market), `^NSEBANK`, and sector indices `^CNXIT ^CNXPHARMA
  ^CNXFMCG ^CNXMETAL ^CNXINFRA ^CNXREALTY ^CNXENERGY ^CNXAUTO ^CNXPSUBANK ^CNXPSE
  NIFTY_FIN_SERVICE.NS` (12 non-market series; "sectors" below means these 12).
  `^CNXMEDIA` excluded — Yahoo has no history (probed 2026-10-26).
- Probe 2026-10-26: all of the above have history from 2010–2011, contradicting the
  older rec_audit note that Yahoo serves ~4 days of sector history.
- Cached to `tools/cache/event_study/closes_<start>.csv` (refreshed if older
  than the latest trading day requested). Loader takes an injectable `download`
  callable so tests never hit the network.
- A sector's series starts when its data starts; events before that are dropped
  for that sector only (reported as per-sector n).

### 2.2 Events

`policy_events.csv` columns:

| column | meaning |
|---|---|
| `date` | announcement date (IST, YYYY-MM-DD) |
| `event_type` | `mpc` or `budget` |
| `label` | mpc: `cut` / `hike` / `hold`; budget: `full` / `interim` |
| `scheduled` | 1 = scheduled meeting/budget; 0 = unscheduled (off-cycle) |
| `time_ist` | announcement time, e.g. `10:00`, `14:30`, `11:00` |
| `source_url` | RBI press release / PIB / indiabudget page |
| `notes` | free text (e.g. "Saturday special session") |

- **d0** = the trading session containing the announcement. All announcements are
  intraday, so d0's close-to-close return captures them.
- If Yahoo has no bar for an event date, the session is restored from NSE's
  all-indices file for that day (`patch_sessions`; Yahoo and NSE closes agree to
  the paisa). Yahoo lacks Sat 2015-02-28, Sat 2020-02-01, Sun 2026-02-01 and
  2014-02-17 — all real sessions. *(Amended 2026-10-26 during implementation:
  snapping these to the next session would make d0 a two-session return, ~√2
  larger, inflating the magnitude tests.)* Only a date NSE also has no file for
  is snapped to the next session, with a `snapped` flag.
- Validation: unknown `event_type`/`label` → error; duplicate (date, type) → error.
- Unscheduled MPC moves (27-Mar-2020, 22-May-2020, 4-May-2022) are excluded from
  the primary set and reported separately as an n=3 note.
- Every row is verified against an official source before the pre-registration is
  frozen; unverifiable rows are flagged in `notes`, not guessed.

### 2.3 Abnormal returns

- Daily log returns.
- **Market model** per (event, sector): OLS of sector on NIFTY over estimation
  window [−250, −11] trading days relative to d0 (minimum 120 valid days, else
  that pair is dropped). AR_t = r_sector,t − (α + β·r_NIFTY,t).
- Sensitivity: market-adjusted AR (β = 1, α = 0) reported alongside.
- NIFTY itself is judged on raw return.
- Windows (trading days relative to d0): **pre** [−5,−1], **day** [0,0],
  **post** [+1,+5], **drift** [0,+20]. Multi-day windows use cumulative AR (CAR).

## 3. Statistics

### 3.1 Null A — matched random-date draws (all statistics)

- Draw `n_events` trading days without replacement from the same years as the
  event set, excluding ±10 trading days around every real event of that set.
- Optional `calendar_match` (used for Budget): draw only from the same calendar
  months as the real events (Jan–Mar, plus July for July budgets).
- Recompute the identical statistic on each draw; 10,000 draws, fixed seed.
- p-value = (1 + #{null ≥ real}) / (1 + draws) (one-sided in the hypothesised
  direction; magnitude stats are one-sided "greater").
- Real statistic also gets a bootstrap 90% CI (resampling events, 5,000 reps).

### 3.2 Null C — label permutation (cut-vs-hike contrast only)

- Shuffle the `cut`/`hike` labels among the cut+hike events, preserving bucket
  sizes; recompute mean(basket AR | cut) − mean(basket AR | hike); 10,000 draws.

### 3.3 Tests

**Primary (magnitude, day window, per event set, scheduled events only):**

- **P1:** mean |r_NIFTY| on event days vs Null A.
- **P2:** mean cross-sector dispersion — per event, the std of the 12 sectors' AR
  on d0; averaged over events — vs Null A.

4 tests (2 sets × 2 stats), **Holm-corrected, family α = 0.05**.

**Secondary (directional, MPC scheduled only):**

Rate-sensitive basket = equal-weighted AR of `^NSEBANK ^CNXPSUBANK ^CNXREALTY
^CNXAUTO NIFTY_FIN_SERVICE.NS`, day window.

- **S1:** cut days, basket AR > 0 (Null A, one-sided).
- **S2:** hike days, basket AR < 0 (Null A, one-sided).
- **S3:** cut − hike > 0 (Null C).

Reported with raw p-values and a power warning (each bucket ~10–15 events). The
label is the *decision*, not the *surprise*; a null here does not rule out a
surprise effect.

**Exploratory (no claims):** per-sector |AR| and signed AR for every window and
both sets, Benjamini–Hochberg q-values; budget per-sector signed AR (descriptive,
no direction label exists).

Every row reports: n, real statistic, null mean, ratio (real / null mean),
p (or q), 90% CI.

### 3.4 Decision rule (pre-registered)

- **"Policy days are volatility events" → desk context flag** (e.g. a calendar
  badge "RBI day — NIFTY moves ~X× a normal day") only if P1 or P2 survives Holm
  **and** ratio ≥ 1.3× **and** the effect holds in both halves of the sample
  (event dates before vs from 2019-01-01, each half p < 0.10 with ratio ≥ 1.2×).
- **"Directional tilt"** promoted only if S3 p < 0.05 **and** S1/S2 signs match
  theory; even then labelled "decision-conditional — not tradeable before the
  announcement."
- Anything else is recorded as calibration (e.g. "the market prices these").

## 4. Interfaces

```python
# tools/event_study.py
load_events(path, types=None, scheduled_only=True) -> pd.DataFrame
load_closes(tickers, start, download=None, cache_dir=None) -> pd.DataFrame   # wide, DatetimeIndex
snap_to_sessions(dates, index) -> (positions: np.ndarray, snapped: np.ndarray)
market_model_ar(r_sec, r_mkt, d0_pos, est=(-250, -11), min_obs=120) -> np.ndarray | None
event_ar_table(returns, events, sectors, market, windows, model="market") -> pd.DataFrame
date_null(stat_fn, returns, n_events, candidate_pos, draws, seed) -> np.ndarray
candidate_positions(index, event_pos, exclude=10, years=None, months=None) -> np.ndarray
label_permutation(values, labels, a, b, draws, seed) -> (real, null)
holm(pvals) -> np.ndarray ; bh(pvals) -> np.ndarray
run_study(closes, events, cfg) -> dict          # everything the report needs, JSON-serialisable
```

`event_study_run.py` flags: `--events mpc,budget`, `--start 2010-01-01`,
`--draws 10000`, `--seed 7`, `--out output/event_study`, `--no-cache`.

## 5. Error handling

- Missing price series for a sector → that sector omitted, logged, report notes it.
- Event with insufficient estimation history → dropped for that sector; per-sector n
  reported.
- Fewer than 5 events in a bucket → statistic reported as `n/a (n<5)`, not tested.
- Yahoo download failure → hard error from the CLI (no silent partial run); cache
  used if present.

## 6. Testing

`tools/test_event_study.py`, run via `run_tests.bat` (Python314 interpreter):

- Synthetic random-walk prices with a planted 3σ move on known dates → P1 p < 0.01,
  correct sign for a planted directional effect; un-planted control → p not small
  (seeded, so deterministic).
- `market_model_ar` recovers a known β within tolerance.
- `snap_to_sessions` handles weekend/holiday dates and sets `snapped`.
- `candidate_positions` excludes ±window and respects year/month filters.
- Same seed → identical null arrays.
- `holm` / `bh` match hand-computed values.
- `label_permutation` preserves bucket sizes.
- `load_events` rejects unknown labels and duplicates.
- No network: loaders receive stub `download` callables.

## 7. Out of scope

Desk/Streamlit page; surprise/consensus labelling; intraday data; other event types
(GST council, elections, SEBI, PLI) — the CSV schema accepts them later with no
code change; stock-level (non-index) events.
