---
title: "Design Review — 2026-09-14: the debt moved from the code to the ops around it"
category: analysis
tags: [design-review, backlog, ops, scheduler, stale-claims, lint]
timeframe: milestone-plan
created: 2026-09-14
updated: 2026-09-14
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/Python-Environments.md
  - analyses/PCR-Sign-Convention-Pre-Registration.md
---

# Analysis: Design Review — 2026-09-14

## Thesis

The desk measures what it builds and writes the null on the surface. That part is
healthy. The debt has moved **out of the code and into the operations around it**:
nothing scheduled is actually running, two stores disagree about the same PCR
series, and three sentences on the live page say things that were fixed weeks ago.

Reviewed: repo and git history (388 commits), [[analyses/Open-Backlog]] and its last
three passes, the roadmap and UX pages, the uncommitted PEAD-walk diff on
`b76-ob-trade-plan`, the test suite under the app's interpreter (**478 passed, 10 s**),
both lint tools, the bandit report, Task Scheduler, the SQLite stores, and the running
Home page.

## Evidence For — findings

| # | Finding | Evidence | Sev |
|---|---|---|---|
| 1 | **Daily pipeline not scheduled.** Only `TradingBramha-IntradayUpdate` and `TradingBramha_DailyDigest` exist; OpportunityDaily / DailyScanner / AlertWatcher are defined in `scheduler_core.py` but not registered. `daily_opportunities` last run 2026-09-07, gaps before. Home says stale but still ranks week-old names. | `Get-ScheduledTask`; `daily_opportunities` run_dates | P0 |
| 2 | **PCR split-brain.** B-22r's backfill wrote 543 sessions to `cache/pcr/nifty_index_pcr.csv`; the verdict reads `pcr_index_history` (1 row) and says "0 of 60 baseline sessions stored". Score unaffected (factor is no-vote) but the text is wrong. | `sentiment_index.py:641,705` | P1 |
| 3 | **Stale state phrases on the surface.** Footer: "single backtest window … no significance test yet" (B-20a, B-21 closed). Nav tooltip: "24 pattern scanners" vs 46 on Home. `Python-Environments` names `pythoncore-3.14-64` as the app interpreter; launch.json and start.bat now use `Programs\Python314`. `claims_lint` sees figures, not phrases. | `dashboard_app.py:6251`, `:1116` | P1 |
| 4 | **Verdict degrades by construction.** Sentiment 3 days old counts as a caution; sector participation NOT CHECKED on 8/11 indices. Both feed STAND DOWN. | Home page text | P1 |
| 5 | **`wiki_lint.py` crashes** on cp1252 (`UnicodeEncodeError`, line 215). Under `-X utf8`: index 288 vs 293 actual, 33 dead links / 15 pages, 12 orphans, 15 frontmatter gaps. | run output | P2 |
| 6 | **Two dashboards.** `start.bat` launches the Dash astro app on :8050; the desk is Streamlit on :8760 via launch.json. | `start.bat` | P2 |
| 7 | **chart_server restart footgun** — 18 per-file JS routes; recorded twice in the backlog, never fixed. | `chart_server.py` | P2 |
| 8 | **No test runner.** Suite green only under `Programs\Python314`; other 3.14 lacks pytest; bare `python` is a venv with no pandas. No CI, no pytest.ini. | interpreter probe | P2 |
| 9 | **Monolith.** `dashboard_app.py` 13,797 lines, 136 defs, 112 raw-HTML renders, 123 broad excepts (9 silent). Page bodies untestable. | wc / grep | P3 |
| 10 | **Bandit report stale** (2026-08-15): both HIGH `shell=True` hits are gone; MEDIUMs remain (0.0.0.0 bind, one string-built query). | grep | P3 |

**What is working and must be protected:** pre-registration with withheld branches
(B-76 C), nulls that change the surface (PMax −0.50R on the card, gauge retired,
PCR factor lost its vote), absent-renders-absent, the shared `columns.py` /
`report_style.py` libraries, and a backlog that re-verifies against code.

## Evidence Against — the uncommitted diff

PEAD walk (`earnings_reaction.pead_walk`, `opportunity_hub._attach_pead`,
`_render_pead_walk`, 5 tests). Measurement choices are right: drift from the
reaction bar, unfinished window is `None`, stale calendar yields nothing, context
not vote, runs after the filter. Weaknesses: the plain fetch is chosen by registry
order (not a contract); no test covers `_attach_pead` or the renderer's JSON
date round-trip; all four files warn LF→CRLF. Commit it.

## Conclusion — new backlog items

| Item | P | What | First step |
|---|---|---|---|
| **B-77** | P0 | Register the three Scheduler Hub jobs | Register, verify one run lands, add a red Home chip when the newest run is older than one session |
| **B-78** | P1 | One PCR store, one reader | Backfill writes `pcr_index_history`, or the factor reads the CSV |
| **B-79** | P1 | Fix the three stale strings; extend `claims_lint` to state phrases in UI strings | Three edits, then the lint class |
| **B-80** | P1 | Sentiment refresh on the daily job; probe the 8 unavailable sector indices | Job + data probe |
| **B-81** | P1 | Land the PEAD walk | Name the plain fetch, test attach + renderer, `.gitattributes`, commit |
| **B-82** | P2 | `wiki_lint` encoding fix, then the dead-link/orphan list (extends B-27) | `sys.stdout.reconfigure` like `claims_lint` |
| **B-83** | P2 | `run_tests.bat` pinned to the launch.json interpreter + `pytest.ini` | Minutes |
| **B-84** | P2 | Owner decision: retire or document the Dash app; point `start.bat` at the desk | Decision |
| **B-85** | P2 | Static route on `chart_server` for JS modules | Small |
| **B-86** | P3 | Re-run bandit; bind chart_server to loopback by default | Minutes |
| **B-87** | P3 | Extract one page per session into `tools/pages/`; log the 9 silent excepts | Ongoing |
| **B-88** | P3 | Move the 43 generated workbooks/renders out of the repo root | Small |

**Carried forward, unchanged verdicts:** B-73 (needs the cadence decision), B-75
(ready, small), B-76 residuals, B-56 (the only built-but-unscored signal left),
B-34r2, B-32r/B-21b/B-26 (gate cleared by B-21), B-35/B-31/B-30 (parked), B-46/47/48,
and the four August P2 items B-4/12, B-6, B-8, B-9 — schedule one or mark deferred.

## Action Taken / Plan

This session: B-77, B-81, B-79. This week: B-78, B-80, B-83, B-82. Pending owner:
B-84, B-73 cadence, the August P2 four.

## Outcome — 2026-09-16

**All twelve items raised here are closed** (B-77…B-88), plus B-75, the one
carried-forward item that was ready rather than blocked. Three of the twelve did
not close the way they were written, and those are the useful ones:

* **B-84's premise was wrong.** There are three apps, not two, and `start.bat`
  was never pointing at the wrong one. The retire candidate is a different file
  and remains the owner's call.
* **B-87 became a ratchet, not an extraction** — and it earned its keep
  immediately: the very next change (B-75) tripped it, and the code moved out of
  the monolith instead of into it.
* **B-82 found its own clock had stopped**, which was a bigger finding than the
  encoding crash it was raised for.

**What is left is not a session's work.** Everything under "carried forward"
needs either an owner decision (B-73's cadence, the Dash app's retirement, the
four August P2 items) or a measurement (B-56's pre-registered test, B-87's
extraction). None of it is blocked on code.

## Related Pages

- [[analyses/Open-Backlog]] — the living index these items extend
- [[analyses/Dashboard-UI-Roadmap]] — the M1–M4 spine, now complete
- [[analyses/Python-Environments]] — stale on which interpreter runs the app (finding 3)
