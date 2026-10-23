---
title: "B-167 — Does confirmation after a liquidity sweep select better trades?"
category: analysis
tags: [b-167, smc, liquidity-sweep, cisd, bos, filter, pre-registration]
created: 2026-10-17
updated: 2026-10-17
sources: 0
related:
  - analyses/Open-Backlog
  - analyses/LuxAlgo-SMC-ICT-Gap-Analysis
  - analyses/HTF-Liquidity-Sweep
---

# B-167 — Sweep + confirmation as a filter

From [[analyses/LuxAlgo-SMC-ICT-Gap-Analysis]] item 3 (LuxAlgo's "smart money reversal" and
"change in state of delivery"). The desk's best signal is the bullish Liquidity Sweep (B-41m).
SMC teaching says to wait for confirmation after the sweep. Does waiting pick a better subset?
**No stop is added in any arm**: B-41p found any stop of the shipped size destroys this edge.

## Pre-registration — written 2026-10-17, BEFORE any forward return was computed

**Events.** The registered `Liquidity Sweep` scanner's swept bars from the B-165/B-166 panel
(nifty500 first 300, last 750 bars), read from `cache/sweep_dates.json`, which B-166 saved from
a full-history replay. Nothing is re-detected.

**Confirmation within 5 sessions after the swept bar *s*** (bars *s+1 … s+5*), the first of:
* **CISD**: the last run of consecutive down-closing candles ending at or before *s*; fires on
  the first bar whose close is above the **open of that run's first candle**.
* **BOS**: a close above the most recent swing high confirmed (pivot 5) as of that bar.

**Arms.**
* **CONF**: entry at the next open **after the confirmation bar**. That is when a trader who waits
  can actually act, so the cost of waiting is included.
* **UNCONF**: sweeps with no confirmation within 5 sessions; entry at the open after *s*+5,
  i.e. at the same "has had its chance to confirm" point.
* **ALL-AT-SWEEP**: every sweep, entry at the open after *s*. This is the B-41m timing, reported as context.

**Outcome.** 20-session return net of `COST_INDIAN`, minus the symbol's all-bars mean over the
span (the `crt_edge_study` machinery). 10 and 60 sessions descriptive.

**Statistic.** Per symbol with both CONF and UNCONF events: mean(CONF) − mean(UNCONF), then a
one-sample t across those symbols. Three calendar windows on CONF − UNCONF, pooled.

**Decision (fixed now).**
* **FILTER HELPS** if mean(CONF − UNCONF) > 0 with p < 0.05, CONF's own 20-session edge
  > 0 (per-symbol t, p < 0.05), positive in ≥ 2 of 3 windows, and ≥ 30 paired symbols. Then file
  **B-167r**: show "confirmed" on Liquidity Sweep cards. A display change; any weighting is a
  separate owner decision.
* **Otherwise NO FILTER.** The sweep card stays as is.

**Prior: NO FILTER.** Waiting moves the entry above the reversal bar, and B-41p showed this edge
lives in the path right after the sweep. Expected: CONF − UNCONF ≈ 0, and CONF no better than
ALL-AT-SWEEP.

## Result

**RUN 2026-10-17: NO FILTER.** `tools/sweep_confirm_study.py` as pre-registered (`26fcbc4`);
5,305 sweeps on 258 names; **54.4% confirm** within 5 sessions (CISD or BOS).

| h | CONF − UNCONF (paired, 242 symbols) | CONF edge | ALL-AT-SWEEP edge |
|---|---|---|---|
| 10 | +0.07 (p 0.80) | +0.03 (p 0.88) | −0.01 (p 0.98) |
| **20** | **−0.02 (p 0.97)** | +0.77 (p 0.067) | +0.64 (p 0.061) |
| 60 | −0.60 (p 0.56) | +2.83 (p 0.015) | +2.59 (p 0.003) |

20-session CONF − UNCONF by window: +0.05 / −0.46 / +0.23.

**Verdict: NO FILTER.** Confirmed and unconfirmed sweeps are the same trade (−0.02pp). Waiting for
CISD or BOS does not select better sweeps; it only moves the entry later. No B-167r; the sweep card
stays as is. Prior held. Consistent with B-41p: this edge is in the sweep itself, not in what
follows it.
