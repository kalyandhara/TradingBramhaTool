---
title: "Daily after-hours pipeline → morning report — gap analysis and roadmap"
category: analysis
tags: [pipeline, scheduler, confluence, morning-report, gap-analysis, roadmap]
timeframe: build-plan
created: 2026-10-22
updated: 2026-10-22
sources: 1
related:
  - analyses/Open-Backlog.md
---

# Analysis: daily pipeline → morning report

**Goal (owner, 2026-10-22):** every trading day after the close, run every
screener on its own, sort the results, cut the noise, score confluence, and
show one **morning report** of the latest run. Today the user has to run
screeners by hand to see anything.

The four-step "guide" format the owner pointed to (JustTicks) is used here
as the **shape of each report card**:

1. **What the signal is**: which scanners fired, in plain terms.
2. **How to confirm it**: confluence count, sector/industry location, rating, volume.
3. **Where it fails**: invalidation level, liquidity, earnings soon, pledge,
   conflicting scanners, market verdict.
4. **See it live**: links to Stock Analyzer, Predictive Analysis and the chart.

## What actually ran: Task Scheduler evidence (2026-10-22)

Read with `scheduler_core.status()` / `run_summary()` / `tail_log()`.

| Job | Registered | Record | What it produces | Who reads it |
|---|---|---|---|---|
| `daily_scanner` 16:15 | yes | 26/26 ok | `cache/scanner_daily_<ts>.json` (56 scanners, **1,171 hits** on 10-21) | **nobody**: no page or job loads it |
| `opportunity_daily` 16:20 | yes | 26 ok, 1 hung | `daily_opportunities` top 100 (sector → industry → scanners → rating) | Opportunity Hub run-date selector; digest email |
| `batch_screener` 16:25 | **no** | **never ran** | Category batches + confluence xlsx (last manual run 2026-10-12) | nobody |
| `snapshot_refresh` 16:30 | yes | **0 ok / 7 failed** | 16 report snapshots | pages, which show **stale** snapshots |
| `sentiment_daily` 16:30 | yes | 27/27 ok | `sentiment_history` | Home verdict |
| `equity_snapshot` 16:10 | yes | 5 ok / 6 failed | `equity_snapshots` | Portfolio |
| `hidden_treasures_daily` 16:45 | yes | 7 ok / 1 hung | `hidden_treasures` | Hidden Treasures page |
| `daily_digest_email` | **no job** | never scheduled | HTML digest email | n/a |

## Why it "didn't materialise": root causes

1. **The confluence job never ran.** `batch_screener` is in the registry but
   was never registered with Task Scheduler. Its bat also hard-codes
   `--regime MIXED` and writes xlsx files into `reports/batch/` that no page reads.
2. **The scanner run that does work is a dead end.** `daily_scanner` saves
   1,171 raw hits to JSON every day, and nothing reads it. Scanner Hub always
   re-runs live. This is the "user has to manually run the screener" symptom.
3. **The snapshot refresh crashes every day at step 6/16.** A progress label
   contains `≥`, and the scheduled console is cp1252, which can't print it:
   `UnicodeEncodeError: 'charmap' codec can't encode character '≥'` in
   `snapshot_refresh.py:76`. The later snapshots (gap & volume, deals, market
   brief…) are never refreshed on schedule. A one-line fix:
   `sys.stdout.reconfigure(encoding="utf-8")` or `PYTHONIOENCODING=utf-8` in the bat.
4. **There are four outputs and no single report.** The scanner JSON,
   `daily_opportunities`, the batch xlsx and the snapshots each live in a
   different place. Nothing merges them into "today's picks", and Home shows
   none of them.
5. **Scheduling hygiene.**
   - Daily jobs use `/sc DAILY`, so they run on Saturdays, Sundays and holidays
     (equity_snapshot "failed" on 10-17 and 10-18).
   - Missed runs while the PC sleeps are not retried (no StartWhenAvailable;
     the logs show `^C` and "running" ghosts).
   - Ordering is by clock time only. Nothing checks that the 16:15 output exists
     before the 16:20 job starts.
   - A no-op ("no priced bar for any position") counts as a failure, so real
     failures are drowned out.
6. **Noise isn't reduced in one place.** `opportunity_hub` already has the
   right machinery (`SCANNER_FAMILIES`, `scanner_weight`, so correlated
   scanners don't vote twice). The 56-scanner nightly run and the batch runner
   don't use it.

## Roadmap

Ordered so that each step makes something visible the next morning.

### R0: Make the existing jobs trustworthy (½ day)
- Fix the cp1252 crash in `snapshot_refresh` (UTF-8 stdout), and set
  `PYTHONIOENCODING=utf-8` for every generated bat in `write_bat`.
- Weekday-only schedules: reuse the existing `_TRADING_DAYS` WEEKLY branch for
  daily jobs too. Skip NSE holidays inside each job by checking the bhavcopy date.
- Turn on StartWhenAvailable when registering, so a sleeping PC catches up on wake.
- equity_snapshot: "nothing to price" exits 0 with a SKIPPED line.
- Clear the "running" ghost records.
- **Done when** Scheduler Hub shows 5 consecutive green weekdays for every job.

### R1: One orchestrated nightly run (1–2 days)
- New `nightly_pipeline.py` plus **one** scheduled job at 16:15 that runs the
  stages in order and stops a stage if its input is missing:
  1. bhavcopy present for today, otherwise exit "holiday/not published", retry at 18:00
  2. daily_scanner (all 56)
  3. opportunity_daily
  4. sentiment_daily
  5. snapshot_refresh
  6. hidden_treasures (weekly is enough)
- Writes one `pipeline_runs` row per stage (start, end, status, rows, error).
  The **Pipeline Log** page reads it.
- Retire `batch_screener` (or fold in its category grouping), and retire the
  separate clock-chained jobs.
- **Done when** a single row says "2026-10-23 pipeline ok, 6/6 stages, 23 min".

### R2: Noise reduction and confluence in one ranker (2–3 days)
- New `morning_rank.py` reads the **stored** outputs, with no fetching:
  - scanner hits (from the nightly JSON, moved into a DB table `scanner_hits(run_date, scanner, symbol, …)`)
  - `daily_opportunities`
  - sentiment and verdict
- Noise rules, each a named constant and an untested prior:
  - one vote per scanner family (`SCANNER_FAMILIES`)
  - drop illiquid names (below ₹1 Cr average turnover, matching the existing skip)
  - drop names with results within 3 sessions
  - drop names flagged for pledge
  - drop conflicting bull/bear signals on the same name
  - cap the list at 15
- Confluence score = weighted family votes + location (leading sector/industry)
  + M1 rating. The verdict caps the list: STAND DOWN shows a "watch only" list.
- Stores `morning_report(run_date, rank, symbol, score, signal, confirm,
  fails, links)`. Each row carries the four guide fields as text.
- **Done when** the table holds 10–15 rows per day and every row has all four
  fields filled, never blank.

### R3: The morning report the user sees (1–2 days)
- A **Home card** ("Morning report · run 2026-10-22 16:38 ●"), opened from
  the latest run with a freshness dot, keeps Home's no-fetch rule intact. It
  shows the top 5, with a link to a full **Morning Report** page.
- The page shows one card per pick, in the four-step layout (signal, confirm,
  where it fails, see it live), plus a header with the verdict, breadth and
  "what changed since yesterday" (new / dropped / still on the list).
- Scanner Hub opens on the **latest stored run** by default. "Run live" stays
  as a button.
- Cards stay cards, never a table (matching the Scanner Hub card rule).

### R4: Delivery and the track record (1–2 days)
- Schedule `daily_digest_email` (or Telegram, still an open owner decision)
  to send the morning report at 08:30. It only sends once the pipeline
  reports ok; otherwise it sends "pipeline failed at stage X".
- Track record: for each past `morning_report` row, record 1/5/20-day
  forward returns, and show the hit rate by score band with `n`. These are
  calibration numbers, not an edge claim.
- After 20 or more sessions, run a study: does the confluence score rank
  forward returns? Adjust weights only from that study. Run `claims_lint`.

### Later (optional)
- Fold the parked Pre-Open plan's 09:10 auction capture into the morning
  report as a "pre-open check" line (see `docs/superpowers/plans/2026-10-22-pre-open-analysis.md`).

## Order of value

R0 is the cheapest step and on its own makes the existing snapshots fresh every
morning. R1 and R2 are where the real gap is. R3 is what the owner actually
asked to see. R4 makes it reach the owner without opening the dashboard, and
starts measuring it.
