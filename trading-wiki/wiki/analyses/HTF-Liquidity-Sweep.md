---
title: "B-166 — Higher-timeframe liquidity sweeps vs the daily sweep"
category: analysis
tags: [b-166, smc, liquidity-sweep, htf, pre-registration]
created: 2026-10-16
updated: 2026-10-16
sources: 0
related:
  - analyses/Open-Backlog
  - analyses/LuxAlgo-SMC-ICT-Gap-Analysis
  - analyses/Weekly-CRT-Sweep-Overlap
---

# B-166 — Higher-timeframe liquidity sweeps vs the daily sweep

From [[analyses/LuxAlgo-SMC-ICT-Gap-Analysis]] item 1, and the "HTF LQ" gap B-58
deferred. `detect_liquidity_pools` builds pools from **daily** equal lows only. The question:
does a sweep of a **higher-timeframe** pool carry more forward edge than the daily sweep the
scanner already trades (B-41m)?

## Pre-registration — written 2026-10-16, BEFORE any forward return was computed

**Panel and span.** The B-165 / B-165r panel: nifty500 first 300, 1500 days, the last 750 bars
of each name, net `COST_INDIAN`, entry next open, exit close +*h*. Edge = event return minus the
symbol's all-bars mean over the span (`crt_edge_study` machinery).

**HTF pools, known before the sweep bar *t*:**
* **PWL**: the prior completed calendar week's low.
* **PML**: the prior completed calendar month's low.
* **WEQL**: weekly equal lows, i.e. `detect_liquidity_pools` run on **weekly** bars (pivot 2,
  tolerance 0.75%, ≥ 2 touches), using completed weeks only.

**HTF sweep on daily bar *t*** against any HTF pool level L below the prior close. The
**same rules the daily detector uses**: the low pierces L by 0.05–2.0 ATR(14), the close is back
above L, and the lower shadow (body to low, the daily detector's own wick measure) is ≥ 50% of the bar's range. One event per symbol per 5 sessions.

**Arms.**
* **D**: the registered `Liquidity Sweep` scanner as shipped. Events are swept bars from a
  full-history replay (B-165's `sweep_dates`), saved this time to `cache/sweep_dates.json`.
* **H**: HTF sweeps with **no** D event within ± 2 sessions, i.e. what HTF pools would add.

**Statistic.** Per-symbol mean 20-session edge, one-sample t across symbols, for H and for D.
10 and 60 sessions descriptive. Three equal calendar windows.

**Decision (fixed now).**
* **HTF ADDS** if H's 20-session edge is > 0 with p < 0.025, **and** H's mean edge ≥ D's,
  **and** H is positive in ≥ 2 of 3 windows, with ≥ 30 symbols / ≥ 300 events. Then file
  **B-166r**: add HTF pools to `detect_liquidity_pools` (a scanner change, so the owner decides).
* **Otherwise NO CHANGE.** Pools stay daily.
* D's edge is reported as context, a re-measure of B-41m on this panel. It is **not** a
  verdict on the scanner.

**Prior: NO CHANGE.** B-165r found that sweeps of the prior week's range (weekly CRT, a looser
cousin of PWL) carried no edge and leaned negative. Expected: H edge ≈ 0 or slightly negative.

## Result

**RUN 2026-10-17: NO CHANGE.** `tools/htf_sweep_study.py` as pre-registered (`21efeab`); 258 names.

| Arm | events | 10d | 20d (primary) | 60d | 20d windows |
|---|---|---|---|---|---|
| **H**, HTF sweeps the scanner misses | 2,858 | +0.18% (p 0.21) | **+0.21% (p 0.35)** | −0.03% (p 0.94) | +2.63 / −1.27 / −0.80 |
| D, registered Liquidity Sweep (context) | 5,066 | −0.01% (p 0.98) | +0.64% (p 0.062) | **+2.59% (p 0.003)** | +3.53 / −0.01 / −0.54 |

**Verdict: NO CHANGE.** H fails every condition (p 0.35, 1 of 3 windows, below D). Pools stay daily;
no B-166r. Prior held.

**Context worth keeping:** on this fresh 258-name panel the registered sweep reads **+2.59% at 60
sessions (p = 0.003)** and +0.64% at 20 (p = 0.062), consistent with B-41m's +0.91% @60d /
+0.51% @20d on its own panel. The edge, where it exists, is the daily equal-lows pool; a sweep of
last week's or month's low does not inherit it.
