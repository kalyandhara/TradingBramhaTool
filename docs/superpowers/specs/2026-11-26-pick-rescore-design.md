# Pick re-score — score drift, rank drift, attribution, confidence decay

Date: 2026-11-26 · Status: approved by the owner 2026-11-26 · Branch: `feat/pa-pdf-and-yf-breakouts`
Plan: `docs/superpowers/plans/2026-11-26-pick-rescore.md`
Follows: `2026-11-26-pick-replay-design.md`, `2026-11-26-multichart-dual-replay-design.md`

## Why

Pick replay shows what a pick did after the desk picked it. It cannot show what
the desk *would have thought* of the pick on any later evening, because a pick's
score is stored only on the nights it stays on the shortlist (PAUSHAKLTD: two runs,
then nothing) and only since 2026-08-24. Without that history there is no score
drift, no rank drift, no way to say which factor moved, and no confidence-decay
curve. None of it can be rebuilt for past evenings, so it has to accrue forward
from a nightly job.

This is a research desk, not a trading system: the point is to see whether picks
deteriorate before they fail, not to generate exit signals.

## Goals

1. A nightly job that writes one dated row per open pick: the rating and its parts,
   today's scanner read, today's full score, and the pick's rank in the 500-name
   universe.
2. The shortlist job also stores the rating of every name in its 500-name universe,
   once per night, so rank has a stable pool.
3. Pick replay shows rating drift, rank drift, which factor moved, a D (downgrade)
   marker in the Multi-Chart after-pick pane, and a confidence-decay chart.
4. Picks made before tracking began say "tracking since <date>"; nothing is
   back-filled or estimated.

## Non-goals

- No back-filled history and no reconstructed past ratings.
- No change to how picks are chosen, scored or gated.
- No alerts, emails or exits on a downgrade.

## Anti-goals (would be a failure even if it works)

- A downgrade that fires on nearly every pick by day 2. That is what drift on the
  full composite score would do, because scanners fire on one day and then go
  quiet. Hence the split below.
- Presenting D as a tested sell signal. Its threshold is a named prior.
- Making the shortlist job slower in a way that risks the shortlist itself: the
  universe-rating step must never fail the run.

## Decisions (made with the owner)

| Question | Decision |
|---|---|
| What "score" drifts | **Store both, split.** Rating and its sub-scores, the scanner part, confluence and today's full score each in their own column. Headline drift and D use the **rating** (0–100 M1 Overall Rating) against its stored pick-day value. |
| What rank ranks against | **The whole 500-name universe**, rated nightly inside the shortlist job. |
| How it is built | **A. A separate nightly job, `rec_rescore`, after the audit.** |

The factor breakdown the brief imagined (Trend / Volume / RS / Breadth / Sector)
does not exist in the code. The real parts of the rating are Minervini x/8,
TechnoFunda x/6, CANSLIM x/n (four yes/no checks: near 52-week high, volume ≥ 50-day
average, market above its 200 SMA, RS leader vs Nifty) and EW confidence 0–100.
Those are stable (fixed in `rating.overall_rating`) and are what gets stored.

## Approaches considered

- **A. Separate job after the audit (chosen).** Runs at ~17:45 once `rec_audit`
  (17:30) has rebuilt the episode list, so today's picks get a day-0 row the same
  night. Fetches its own bars, so a failed shortlist run loses only the rank that
  night. Costs a second Yahoo fetch for names the shortlist already pulled.
- **B. Inside the shortlist job.** Reuses its bar cache, but adds the audit's
  concerns and ~10 minutes to the most fragile job on the desk, and runs before the
  audit, so it works from the previous night's episode list.
- **C. Inside `rec_audit_job`.** The audit runs from cached bars in ~3 min; adding
  per-pick fetches and scanner runs slows it and tangles two failure paths.

## Design

### 1. One scorer for the rating parts — `tools/rating.py`

Add `rating_detail(df, nifty_df, weights=None) -> dict | None` returning numbers:
`rating, minervini (0–8), technofunda (0–6), canslim (passes), canslim_n (computable),
ew_conf (0–100), cs_near_high, cs_volume, cs_market, cs_rs` (booleans or None).
`overall_rating` is rebuilt on top of it and returns exactly what it returns today
(same rating, same breakdown strings). A test pins that equality.

### 2. Universe ratings — `tools/opportunity_daily.py` + `tools/portfolio_db.py`

After tagging, while its bar cache is warm, the shortlist job rates every universe
name that has bars and writes `universe_ratings` in `trading_bramha.db`:

`universe_ratings(run_date, session_date, symbol, rating, minervini, technofunda,
canslim, canslim_n, ew_conf, cs_near_high, cs_volume, cs_market, cs_rs,
universe_rank, universe_size, model_version, created_at)`, PK `(session_date, symbol)`.

- `session_date` = the last bar date of the Nifty frame (the NSE session the ratings
  describe, which is IST by construction). Joins use `session_date`, never the
  machine's local date.
- `universe_rank` = rank by rating, highest = 1, ties share the better rank
  (`method="min"`); `universe_size` = names that got a rating.
- Replace-on-rerun per `session_date`, like `daily_opportunities`.
- Wrapped so any exception is logged and the shortlist still runs and saves.
- Only when `save=True`.
- Cost: tagging already fetches 400 days of bars for every universe name into the
  job's cache, so this adds no fetch. The rating measured ~16 ms per name
  (2026-11-26, four frames), so ~10 s for 500.
- First night: the shortlist job has already run today, so the first re-score has no
  universe rank. The page says "rank starts with the next shortlist run". The
  shortlist is not re-run to fill it, because that would replace today's picks.

### 3. The nightly re-score — `tools/rec_rescore.py` (pure) + `tools/rec_rescore_job.py` (I/O)

Same split as `rec_audit.py` / `rec_audit_job.py`.

**Which picks.** Opportunity-source episodes from `audit_episodes` whose entry is at
most 63 sessions back (the longest audit horizon), plus pending ones (picked today,
no entry yet). About 440 tonight.

**Per pick, per night:**
- Bars: `screener_pipeline.fetch_ohlcv(symbol, days=400, min_turnover=0)` — the same
  fetch the pick-day rating used, minus the liquidity floor (an audit never drops a
  thin pick). Full-history fetch for the two `needs_full_history` scanners, as the
  shortlist's `_FetchRouter` does (reuse it).
- `rating_detail` → rating and parts.
- `opportunity_hub.run_scanner_pipeline` over all open picks at once → scanners firing
  today, families, best scanner score, edge points, and how many of the pick's
  original scanners still fire.
- Today's full score with the shortlist's own formula and weights
  (`W_RATING·rating + W_SCANNER·min(best,100) + W_CONFLUENCE·confluence_pct`).
- `universe_rank` / `universe_size` from `universe_ratings` for that session, or
  NULL when the name is not in tonight's universe (shown as "not in today's 500").

**Row:** `pick_scores` in `rec_audit.db`, PK `(episode_id, session_date)`,
INSERT OR REPLACE on rerun:

`episode_id, session_date, symbol, rec_date, sessions_since_entry, rating, minervini,
technofunda, canslim, canslim_n, ew_conf, cs_near_high, cs_volume, cs_market, cs_rs,
scanners_today, families_today, best_scanner_score, edge_points, original_still_firing,
score_today, universe_rank, universe_size, universe_status, rating_at_pick,
rating_drift, downgrade, model_version, created_at`.

`universe_status` is `ranked`, `not_in_universe` (tonight's universe has ratings but
not this name) or `no_universe` (no universe ratings for the session at all).

- `session_date` = the pick's last bar date. A pick with no bar for tonight's session
  (suspended, fetch failed) gets no row; the job counts and reports these.
- `rating_at_pick` = `overall_rating` stored on the pick day (exists for every pick).
- `rating_drift` = `rating − rating_at_pick`.
- `downgrade` = `rating_drift ≤ −DOWNGRADE_POINTS`.

**Downgrade threshold:** `DOWNGRADE_POINTS = 15`. A named prior, untested: one
Minervini check is worth ~4.4 rating points, one TechnoFunda check ~4.2, one CANSLIM
check ~5, so 15 is roughly three checks lost. Stated as a prior wherever it shows.

**Job output:** a `##RESULT` line for the Scheduler Hub: rows written, picks
skipped with reasons, picks not in tonight's universe, downgrades tonight.

**Scheduler:** `rec_rescore` in `scheduler_core.JOBS`, daily, default 17:45 (after
`rec_audit` at 17:30).

### 4. Pick replay — `tools/rec_audit_replay.py` + `tools/desk_pages/rec_audit_page.py`

Read-only helpers (`rec_rescore.load_scores(episode_id)` etc.); the page never
fetches.

- **Snapshot line:** `Rating drift −18 (72 → 54) · rank #9 → #146 of 500 · tracking since 2026-11-26`.
  Pick-day rank comes from `universe_ratings` on the pick's session; picks made before
  tracking have none, so the line reads `rank #146 of 500 today` plus the tracking
  note. With no row yet: `Re-score tracking starts with the next nightly run.`
- **What moved:** the sub-score with the largest change from the first tracked row
  (or the pick day, when that row exists), e.g. `Minervini 7/8 → 4/8 led the drop`.
  For older picks the comparison is from the first tracked row and says so. The
  CANSLIM checks show as which flipped (`lost: RS leader, volume`).
- **Setup still valid:** `2 of 3 original scanners still fire` from the latest row.
- **Confidence-decay chart** (right column, under the MFE/MAE ladder): x = sessions
  since entry, y = rating; dashed line at the pick-day rating, dotted line at the D
  threshold, D marked where it first tripped; second panel = universe rank (inverted
  axis). The gap between pick day and tracking start is left empty, with a
  "tracking since" annotation.
- **Multi-Chart link:** adds `ddate=YYYY-MM-DD` (first session D tripped) to
  `multichart_url`.
- **Aggregate decay** (Lessons tab, new section): median rating drift by session
  since entry across tracked picks, judged winners vs losers, with the count per
  session. It says it fills in over weeks and is descriptive.

### 5. Multi-Chart — `tools/replay_mode.js`

`parseReplay` reads `ddate`; `markers` adds `{text: 'D', position: 'aboveBar',
shape: 'arrowDown'}` on that session in the after-pick pane. The header comment
documents D as the re-score downgrade (rating ≥ 15 below the pick day; a prior).
`sw.js` is network-first for code, so no cache bump is needed (verify).

## Constraints

- Machine is US Eastern, NSE is IST: every stored date is a bar date, never
  `date.today()`.
- Running :8501 keeps stale modules: verify on a fresh :8502 (`dashboard-fresh`).
- Commit on the current branch only with the owner's OK; never push.

## Testing

pytest, no network: fake bars and fake scanner hits injected.
- `rating_detail` equals `overall_rating` on the same frames.
- Universe ranking: order, ties, size, and that a rating failure leaves the shortlist
  untouched.
- Episode selection: the 63-session window, pending picks included, other sources
  excluded.
- Row building: drift, downgrade threshold edge (−15 trips, −14 does not), not in
  universe → NULL rank, missing bar → no row and counted, rerun replaces.
- Page helpers: snapshot line with and without pick-day rank, with no rows, the
  "what moved" text, decay figure builds, first-D date.
- `replay_mode.js`: `ddate` parsed and the D marker placed (existing node test).
- Scheduler registry includes `rec_rescore` after `rec_audit`.

## Left to the builder

Exact column order, the decay chart's styling within `report_style` tokens, the
wording of captions within the rules above, and how the universe-rating loop
reports progress.

## Calls I made (for the owner to check)

1. Tracking window = 63 sessions after entry, plus pending picks.
2. `DOWNGRADE_POINTS = 15`, labelled a prior.
3. No row for a pick without tonight's bar; counted in the job's result line.
4. The universe is the shortlist job's own 500 by traded value (not the NIFTY 500
   index); a name that falls out shows "not in today's 500".
5. Pick-day rank uses the same universe pool, so it exists only for picks made from
   the first tracked night on; the existing shortlist rank stays in the header.
6. New tables: `universe_ratings` in `trading_bramha.db` (written by the shortlist
   job), `pick_scores` in `rec_audit.db` (written by the re-score job).
