# One card per ticker in Recommendation Audit — short design

Date: 2026-11-27 · Status: draft for the owner's approval · Size: small change

## Why
In the Post-mortems view the same ticker appears many times: under "Raw scanner
hits" each scanner that fired is its own pick (MOTISONS: 5 cards for 13 Oct), and
a ticker re-picked weeks later gets another card. The owner wants one card per
ticker, at its latest pick date. The Pick replay pop-up also does not name the
ticker on the stale :8501 (the current code does, in its header).

## Decision (owner, 2026-11-27)
"One card per ticker" — group in the views; no SCD2 storage change. Measured:
SCD2 on `scanner_run_cache` would drop only ~14% of rows (levels move with price
daily) and needs five readers rewritten.

## Design
- `group_by_ticker(eps)` (pure, `desk_pages/rec_audit_page.py`): one row per symbol,
  the one with the latest `rec_date`; ties on that date keep the incoming order
  (worst excess first in the queue). Adds `scanners_all` (every scanner that fired
  on that latest date, from all its rows), `earlier_dates` (the ticker's other pick
  dates in the set) and `n_picks`.
- Applied to: the Post-mortems queue and its cause counts, the Pick replay picker,
  and the All picks table. Each source (Opportunity / Hidden Treasures / scanner
  hits) is grouped on its own.
- Card header: `MOTISONS · picked 2026-10-13 · 5 scanners: Base Formation, VCP
  Coiling, …`, then `Also picked: 2026-08-14` when there are earlier picks.
- Pop-up: the two chart titles carry the ticker (`MOTISONS · Pick day · 2026-10-13`).

## Non-goals
- Statistics (tiles, cohorts, slices, lessons, proposals, per-scanner track record)
  keep counting every pick; per-scanner attribution needs per-scanner picks.
- No storage change; no SCD2.

## Calls I made (check these)
1. A ticker's older picks leave the card views; they stay in the statistics and in
   the "Also picked" line. The review note is saved on the latest pick shown.
2. On one date, the card's outcome numbers (return, excess, best/worst) are the same
   for every scanner; the plan result shown is the first row's (worst-first order).
