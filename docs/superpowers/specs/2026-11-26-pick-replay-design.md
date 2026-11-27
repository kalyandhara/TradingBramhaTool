# Pick Replay — Recommendation Audit (short design)

**Date:** 2026-11-26 · **Page:** Portfolio & Risk › Recommendation Audit · **Size:** small change

## Intent
For any past pick, show the chart *as it looked on the pick day* beside *what the
price did since*, with the gain/loss and what went wrong — so one pick can be
understood in depth. Owner goal: the clearest historical impression of how the
recommendations played out, including what needs improvement.

## Goals
- One pick at a time, in depth (owner chose this over a small-multiples grid).
- Two panels: **Pick day** and **Since then**, plus an outcome strip.
- Reachable from a new **Pick replay** tab (picker) and from a **Replay** button on
  each post-mortem card.

## Non-goals
- No grid of small charts (rejected option B).
- No change to audit scoring, failure tags, or the scheduled job.
- No fetching on page open — reads `price_bars` only (same rule as the rest of the page).

## Anti-goals
- **Hindsight leak:** the Pick-day panel must never show a bar after `rec_date`.
  Tested.
- A blank or broken chart with no explanation when bars are missing — say what is
  missing instead.

## Constraints / data (all already stored)
- `rec_audit.db › price_bars` — daily OHLCV, 2,407 symbols, 2026-06-01 → latest;
  NIFTY 500 is `^CRSLDX` in the same table.
- `audit_episodes*` — rec_date, close, entry, stop, target, entry_date, entry_px,
  ret_h/excess_h, ret_to_date, mfe/mae, days_to_mfe, plan_outcome, plan_sessions,
  ext_vs_ema20, low20_at_rec, risk_flags, scanners, family_names, rank, score,
  market_regime, primary_tag, tags, note.
- Frozen cards exist only from 2026-08-24; the pick-day reasons come from the
  episode row, which covers all picks.
- Streamlit 1.58 (`st.dialog(width="large")` available), Plotly 6.8 — house style
  is Plotly candlesticks.

## Approaches
- **A. One pick in depth — picked.** Picker tab + two-panel view + card dialog.
  Best for the "why did this fail" question.
- **B. Small-multiples grid** — 12 mini "since pick" charts per page. Faster
  scanning, too little detail per pick. Not chosen.

## Design
**Pure helper (tested)** `replay_frame(bars, ep, idx_bars, lookback=60)` →
`pre` (≤ lookback sessions ending at rec_date), `post` (entry_date → latest),
levels (entry, stop, target, low20), markers (entry, best/MFE day, worst/MAE day,
stop/target hit day from plan_sessions, end of headline window), NIFTY 500 rebased
to entry_px over `post`. Plus `bars_for(symbol, start, end)` in `rec_audit_job`
reading the cache only.

**Pick day panel** — candles for `pre` + 20 EMA; dashed lines for entry, stop,
target, 20-day low; caption: rank, score, scanners/families, risk flags,
stretch vs 20 EMA, plan source, market regime.

**Since then panel** — `pre` faded + `post` in full colour; vertical line at entry;
shaded headline window (21 sessions, or source headline); same level lines;
markers for best, worst, stop/target hit; NIFTY 500 rebased dotted line.

**Outcome strip** — entry price → latest close, return to date, headline return,
vs NIFTY 500, vs sector, best/worst, plan outcome, failure cause (+ other tags),
owner note, Analyzer ↗.

**Volume pane** (added 2026-11-26, from the owner's reference chart) — volume
bars under both panels with a 20-session average line; pick-day relative volume
("RVol 314%") in the Pick-day caption. `price_bars.volume` is filled for ~99% of rows.

**Per-pick footer** (owner's format) — one line under the two panels:
`₹312 → ₹523 (+69%) · Target hit day 14` — entry price → latest close (return to
date), then the plan result: Target hit day N / SL hit day N / Neither hit yet /
No plan. Exit price shown when the plan closed it: `exited ₹480 (+54%)`.

**Scorecard footer** (owner's format) — under the picker, for the current filter:
`Total 382 · Target hit 61 · SL hit 124 · Neither 195 · No plan 431 · Pending N`.
Ambiguous (stop and target in the same bar) counts as SL hit, as the audit already
does. *Cost-to-cost* is not shown: no plan has a move-stop-to-breakeven rule, so
there is nothing honest to count — it can be added if that rule is ever built.
The counts above are today's real numbers for the Opportunity shortlist: unlike
the reference card (25 of 31 targets), stops are hit about twice as often as
targets. The scorecard reports that as measured.

**Pick replay tab** — filter pills: Losers (failures) · Winners (headline excess
≥ +5%) · All; optional cause filter; selectbox "SYMBOL · picked date · 21d ±x%",
losers sorted worst first, winners best first. **Replay** button on post-mortem
cards opens the same view in a large dialog.

**Missing data** — no bars → info line naming the symbol and date range; pending
pick → Since-then panel shows "not entered yet".

## Left to the builder
Colours from `rs.TOKENS`; exact marker glyphs; panel heights; which file holds the
figure builder (page module or a small `rec_audit_charts.py`).
