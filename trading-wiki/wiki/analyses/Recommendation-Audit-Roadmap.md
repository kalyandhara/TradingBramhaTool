---
title: "Monthly recommendation audit — ground analysis and roadmap"
category: analysis
tags: [audit, track-record, post-mortem, forward-returns, opportunity-hub, roadmap]
timeframe: build-plan
created: 2026-10-22
updated: 2026-10-22
sources: 4
related:
  - analyses/Daily-Pipeline-Morning-Report-Roadmap.md
  - analyses/Open-Backlog.md
---

# Analysis: monthly recommendation audit

**Goal (owner, 2026-10-22):** a portfolio-level monthly audit of every stock
the screener ever recommended. It tracks the price from the recommendation day
onward, shows whether the tool performs consistently, and runs a post-mortem on
what went wrong, so the tool learns from its mistakes.

**Framing:** this is calibration for a research desk, not a hunt for trading
edge (see the investment-desk memory). A NO EDGE month is information, not a
failure.

## Ground truth: what is already recorded (2026-10-22)

| Source | Rows | Dates | What it holds | Usable for audit |
|---|---|---|---|---|
| `daily_opportunities` | 774 | 40 run dates, **2026-07-31 → 10-21** | rank, symbol, score, rating, confluence, scanners, families, sector/industry, close, entry/stop/target, regime, verdict, risk_flags | **Primary source.** Point-in-time: it is what the tool said that day. |
| `daily_opportunity_cards` | 333 | from 08-24 | The full frozen card JSON per pick | Post-mortem evidence ("what we saw") |
| `hidden_treasures` | 925 | 13 runs from 09-01 | Ownership/quality ranking | Second source, on a quarterly horizon |
| `scanner_run_cache` + `cache/scanner_daily_*.json` | 13,634 rows + 27 files | from 09-05 | Raw per-scanner hits | Per-scanner audit (broad sample, noisy) |
| `positions` | 1 | n/a | Actual trades | Too few to audit |

### Episodes after deduplication
- **150 rows are weekend re-runs** of Friday's list, for example 09-20 and 09-21 repeat 09-19 (same Nifty print). Counting them double-counts.
- Merging repeat appearances of a symbol within 14 days into one **episode**:
  **624 weekday rows → 472 episodes.**
- By month: Jul 10 · **Aug 405** · Sep 30 · Oct 27. The list shrank from about 100 to **5 per day** after 08-27, so recent months are thin.
- **429 episodes are at least 21 sessions old.** A first audit can be backfilled today. It doesn't have to wait a month.
- Only **124 episodes carry an entry/stop/target plan.** Stop and target hits can be audited for those only. The price-path audit works for all of them.
- 59 episodes had `risk_flags` at the time of the recommendation, which allows a test of "did ignoring the warning cost us?".

### Things that bias a naive audit
1. **One regime only.** Every run date was in a Nifty below its 200 SMA
   (−0.7% to −7.9%), and the verdict told the user to treat the list as a
   watchlist. Absolute returns mostly measure the falling market. Every number
   must be **relative to a benchmark**.
2. **Small monthly samples.** About 30 new episodes a month since September.
   One month can't support a conclusion. Use rolling 3-month windows and show `n`.
3. **No model version on rows.** Scanners and weights changed during this
   period (B-1xx commits). A change in performance can't be tied to a code
   change unless each row records the version it was produced by.
4. **Survivorship.** A delisted or suspended pick has no yfinance data.
   Dropping it flatters the record, so it must be counted as "no data".
5. **The liquidity floor trap.** Pricing through `screener_pipeline.fetch_ohlcv`
   with the default ₹1 Cr floor silently drops thin picks. The same bug was
   fixed in equity_snapshot today. Use `min_turnover=0`.

## What the web suggests

- **Benchmark-relative success plus significance.** TipRanks scores calls by
  success rate *and* average return against a benchmark, and uses a Z-test, so
  that many consistent calls outrank a few lucky ones
  ([TipRanks firm ranking](https://www.tipranks.com/news/labs/these-are-the-most-successful-firms-on-wall-street-right-now-compared-to-the-sp)).
  Their current profile pages define success as "profitable after one year" with
  no benchmark by default. That is the weaker definition, and we should avoid it.
- **Excursions, not just end points.** MFE/MAE (best and worst move after the
  signal) show whether a stop or target was realistic. Report the median
  alongside the mean, compare against a baseline, require about 30 or more
  samples and a t-stat around 2, and correct for testing many slices at once
  ([Signal Expectancy Analyzer](https://www.tradingview.com/script/3VhmQvob)).
- **Point-in-time, no look-ahead, keep the dead names.** Use data as it was
  known on the day, and keep delisted names in the universe
  ([sharpely methodology](https://sharpely.in/knowledge-base/data-and-methodology/back-testing-methodology/avoiding-biases-and-handling-delisting),
  [AnalystPrep](https://analystprep.com/study-notes/cfa-level-2/problems-in-backtesting/)).
  Our stored lists are point-in-time by construction, which is a strength. The
  look-ahead risk is on the *entry price* only: the list is made after the
  close, so the realistic fill is the **next session's open**.
- **Post-mortem by root-cause tag, reviewed monthly.** Journaling practice tags
  each loss by cause and reviews setup-level results monthly, which is when
  setups get added or retired
  ([TradeZella guide](https://www.tradezella.com/blog/trading-journal-guide),
  [Curved Trading routine](https://curvedtrading.com/articles/en/how/how-to-review-your-trades/)).
  Their taxonomy is behavioural (FOMO, revenge). A screener needs a different
  one: **market drag / sector drag / setup failure / event / data**. That
  taxonomy is designed below.

## Design

### Unit: the recommendation episode
`(source, symbol, first_rec_date)`:
- `rec_date` is the last trading session on or before `run_date`, so a weekend run maps to Friday.
- Reappearances within 14 days extend the episode (`days_on_list`, `last_rec_date`).
- Fields copied from the first appearance: rank, score, rating, confluence, families, scanners, sector, risk_flags, verdict, regime, plan levels, and a card reference.

### Prices and benchmarks
- **Entry:** the next session's open after `rec_date`. The stored `close` is shown as a reference.
- **Benchmarks:**
  - NIFTY 500 for the market (Yahoo `^CRSLDX`; verify the symbol before relying on it).
  - The sector index via `nse_universe.NSE_SECTOR_INDEX_MAP` for the sector.
  - An equal-weight **universe baseline** for the same day: the average forward return of the screened universe. It answers "would a random pick from the same pool have done as well?"
- **Horizons (sessions):** 5 · 10 · 21 · 63, plus "to date".

### Per-episode outcome
- Return and **excess vs NIFTY 500 / sector / baseline** at each horizon
- MFE and MAE to date, and days to MFE
- **Plan outcome** where levels exist: target-first / stop-first / neither / ambiguous. Ambiguous means both were hit in one daily bar, which is scored as stop-first to stay conservative.
- Status: open (horizon not reached), matured, or no-data (delisted or suspended, counted, never dropped)

### Portfolio-level view (the "monthly audit")
1. **Paper portfolio:** each episode is an equal ₹1 position from its entry,
   held for H = 21 sessions. That gives a daily equity curve of the basket
   against NIFTY 500, with the cumulative excess, maximum drawdown, hit rate,
   median, and average win/loss ratio.
2. **Cohort (vintage) table:** rows are recommendation months, columns are
   5/10/21/63-day median excess and hit rate, each with `n`. This is the
   "continuity" view: is each month's batch better or worse than earlier ones?
3. **Attribution:** median excess, hit rate, `n` and t-stat sliced by:
   - scanner family and scanner
   - confluence count
   - rating band and score quintile
   - rank (top 5 vs the rest)
   - sector
   - risk_flags present or absent
   - verdict and regime
   - days on list

   Cells with n < 30 are greyed out as "insufficient". A note on testing many slices sits on the page.
4. **Post-mortem queue:** every *failure*, meaning 21-day excess ≤ −5% or
   stop-first, gets an auto-tagged card.

### Post-mortem taxonomy (rule-based, each threshold a named prior)

| Tag | Rule | Whose fault |
|---|---|---|
| `MARKET_DRAG` | NIFTY 500 fell more than 3% over the window and excess vs NIFTY 500 > −2% | the market, not the pick |
| `SECTOR_DRAG` | the sector index fell and excess vs the sector index > −2% | sector rotation |
| `SETUP_FAILED` | close below the recommended stop, or below the 20-day low at rec, within 5 sessions | the setup |
| `EVENT_GAP` | a single-day move ≤ −7%, or results inside the window (`earnings_calendar`) | event risk |
| `WARNING_IGNORED` | risk_flags were non-empty at rec | the ranking let a flagged name through |
| `CHASED` | the rec close was more than 10% above EMA 20 (an extended entry) | entry timing |
| `ILLIQUID` | 10-day turnover below ₹1 Cr at rec | universe hygiene |
| `NO_DATA` | no bars after rec | survivorship |

The tags are **not exclusive**. The first matching row is the *primary* tag.
The owner can add a free-text note and override the tag. Notes are stored with
the episode and feed the next month's review.

### The learning loop (human-approved, never automatic)
1. The monthly report ends with **"proposed changes"**. These are generated only
   from attribution cells with n ≥ 30 and |t| ≥ 2. Example: *"Family X: n=64,
   median 21-day excess −3.1%, t=−2.4 → propose weight down."*
2. The owner accepts or rejects each one. Decisions go into `audit_decisions(date, proposal, decision, note)`.
3. Accepted changes are made in code (weights in `opportunity_hub`), and `claims_lint` is run.
4. Each row from then on carries `model_version` (git short SHA plus a weights
   hash), so the next audit can compare **before vs after** the change.
5. Only a backtest or a later audit changes a weight. One bad month on its own
   never does (the priors-need-backtest rule).

## Roadmap

### A0: Point-in-time hygiene going forward (½ day)
- Add `model_version` to `daily_opportunities` (and `hidden_treasures`). opportunity_daily writes the git SHA plus a weights hash.
- Stop the weekend duplicates. This comes free with R0's weekday schedules (the 09-20/21-style rows end), and the audit's dedupe handles history.
- Store `entry/stop/target` on every row. Today only 182 of 774 rows have them, spread across 07-31 to 10-20. Find out which picks skip the plan and why.

### A1: Audit engine plus backfill (2 days)
- New `rec_audit.py` (pure). The interfaces below are proposed names, not settled:
  - `build_episodes(df) -> DataFrame`
  - `episode_outcomes(ep, bars, bench, sector_bench) -> dict`
  - `plan_outcome(...)`
  - `postmortem_tags(...)`
  - `attribution(df, by)`
  - `paper_portfolio(df, hold=21)`
- Prices come from yfinance with `min_turnover=0`, cached in a `price_cache` table keyed (symbol, date). Missing data is marked, never dropped.
- Store results in `rec_audit_episodes` and `rec_audit_runs(audit_date, as_of, n, summary_json)`.
- **Backfill all 472 episodes now.** About 430 are mature, which gives a first real reading on 21-day results.
- Tests use synthetic bars for: excess math, next-open entry, the weekend → Friday mapping, 14-day merge, stop-first ambiguity, MFE/MAE, tag precedence, and a delisted symbol counted as NO_DATA.

### A2: Monthly audit page plus scheduled run (1–2 days)
- New desk page **"Recommendation Audit"** under Portfolio & Risk. It reads only the stored audit.
- Sections:
  - headline tiles (n, hit rate, median 21-day excess, paper-portfolio excess, max drawdown)
  - equity curve vs NIFTY 500
  - cohort table
  - attribution grid
  - post-mortem queue (cards, with the tag override and note)
  - proposed changes
- Scheduler job `rec_audit_monthly`: the first trading day of each month at 17:30, plus a daily light refresh that only updates open episodes.
- Export: a monthly PDF/markdown snapshot saved under `reports/audit/YYYY-MM`, so each month's verdict is frozen, as the opportunity cards are.

### A3: More sources and the learning loop (2 days)
- Add `hidden_treasures` (horizons 63/126/252 sessions) and the raw per-scanner hits from `scanner_run_cache` as separate sources, never mixed into the Opportunity numbers.
- Proposed-changes generator plus `audit_decisions` log, and before/after comparison by `model_version`.
- Add a "track record" line to each Opportunity Hub card and the morning report: "this family: 21-day median excess +1.2%, n=88".

### A4: First wiki result (after A1)
- Write the backfilled 21-day result to the wiki with `n` and the regime caveat (all picks below the 200 SMA), then run `tools/claims_lint.py`.

## First result: A1 backfill (run 2026-10-22, as of 2026-10-21)

Built: `tools/rec_audit.py` (pure), `tools/rec_audit_job.py` (prices, store,
CLI), and `tools/rec_audit.db`. Re-run with:
`py -3 tools/rec_audit_job.py --as-of YYYY-MM-DD`.

**Episodes: 558.** That's more than the 472 counted above, because the Sunday
2026-08-09 list held 100 *unique* picks. Mapping weekend runs to Friday keeps
them, where dropping weekend rows lost them.
- 510 have reached 21 sessions.
- 1 is pending (KMEW, recommended on the audit date).
- 0 have no data.

| Measure (21 sessions, entry = next open) | Value |
|---|---|
| Hit rate (raw return > 0) | 42.9% |
| Median raw return | −1.72% |
| Beat NIFTY 500 | 54.9% of picks, median excess **+1.18%** |
| vs Smallcap 250 | median excess **−1.36%** |
| Significance, per pick | t = 4.97 vs NIFTY 500 (overstated, see next row) |
| **Significance, grouped by entry week (8 weeks)** | **t = 1.57 vs NIFTY 500, 1.12 vs Smallcap 250** |
| Paper basket (₹1 per pick, 21-session hold) | **−0.17%** vs NIFTY 500 shadow −2.73% (max DD −1.81% vs −3.75%) |
| Median best / worst move (MFE / MAE) | +7.08% / −12.61% |
| Plans decided target-first | 32.8% (n=130 with levels) |
| Failures (21-session return or excess ≤ −5%, or stop first) | 220 of 510 (43%) |

**Cohorts (median 21-session excess vs NIFTY 500):**
- Jul: +4.91% (n=10)
- Aug: +1.04% (n=483)
- Sep: −1.21% (n=17)
- Oct: too early. At 10 sessions it reads −8.79% (n=10).

**Failure primary tags (n=220):**

| Tag | Count |
|---|---|
| SETUP_FAILED | 50 |
| STOCK_SPECIFIC | 47 |
| WARNING_IGNORED | 31 |
| SECTOR_DRAG | 31 |
| EVENT_GAP | 26 |
| MARKET_DRAG | 19 |
| CHASED | 16 |

**Reading:**
- In a falling tape (every pick below the 200 SMA), the list lost less than
  the large-cap index. It did about as well as **small caps in general**: the
  edge vs NIFTY 500 is mostly a size effect.
- Grouped by entry week, neither edge is statistically significant.
- This **agrees with B-32's RISK-OFF finding**: bullish signals below the 200
  SMA show no edge, which is why the regime gate caps the list at 5 and calls
  it a watchlist.
- Calibration, not failure: the tool did what the gate said. It produced a
  watchlist that held up no worse than its size class.

**Slices to watch (per-pick t, so overstated; none acted on):**
- Healthcare: +4.16%, n=56
- Industrials: +2.86%, n=122
- Technology: −2.39%, n=42
- Consumer Defensive: −2.40%, n=40
- Rank 1–5 vs 21+: median +2.39% vs +0.61%
- Flagged picks (risk_flags) were *not* worse: +1.49%, n=54

Nearly all of this is one August cohort, so no weight changes are proposed.

### Where the build departed from the design above
- **Sector bars come from NSE's daily all-indices file**
  (`sector_rotation.fetch_nse_index_closes`, disk-cached). Yahoo serves only
  about 4 days of history for FMCG, Infra, Fin Services, Metal, Realty, Energy,
  Consumption and Media. Sector coverage went from 98 to 504 of 510 picks.
- **Benchmarks:**
  - Smallcap 250 (`NIFTYSMLCAP250.NS`) was added next to NIFTY 500 (`^CRSLDX`), because most picks are small caps.
  - The equal-weight universe baseline is deferred to A3. The screened pool isn't stored per day.
- **Paper portfolio is buy-and-hold per pick.** The first version rebalanced to
  equal weights daily and showed −14%, because of volatility drag on small
  caps. That contradicted the per-pick numbers.
- **Tag precedence:** NO_DATA, MARKET_DRAG, SECTOR_DRAG, EVENT_GAP,
  SETUP_FAILED, CHASED, WARNING_IGNORED, ILLIQUID, then STOCK_SPECIFIC. A gap
  causes a stop, so EVENT_GAP comes before SETUP_FAILED.
- **New `pending` status:** a pick made on the audit date isn't entered yet,
  and is not counted as NO_DATA.
- **A0:**
  - `daily_opportunities` and `hidden_treasures` gained `model_version` (git sha + weights fingerprint). `daily_opportunities` also gained `plan_source`.
  - A pick whose scanner card has no levels gets a default plan: stop at the 20-session low, target at 2R.

## Open owner decisions
1. **Failure line:** a 21-day excess of −5%, or stop-first? Both are proposed as defaults.
2. **Holding period for the paper portfolio:** 21 sessions as the default. The investment desk may prefer 63.
3. **Main benchmark:** NIFTY 500 or the same-day universe baseline. The proposal is to show both and headline the baseline.

## Related
- [Daily-Pipeline-Morning-Report-Roadmap](Daily-Pipeline-Morning-Report-Roadmap.md). R4 there (track record) is delivered by A1–A3 here.
- [Open-Backlog](Open-Backlog.md)
