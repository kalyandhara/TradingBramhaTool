---
title: "B-182 — Does a bull trap warn of a weak next month?"
category: analysis
tags: [b-182, bull-trap, failed-breakout, rsi-divergence, volume, risk-flag, pre-registration]
created: 2026-10-23
updated: 2026-10-23
sources: 1
related:
  - analyses/Open-Backlog
  - analyses/Sweep-Confirmation-Filter
  - concepts/RSI
---

# B-182 — Bull Trap detector

From an owner-shared infographic, "Outsmart bull traps in stocks". It shows a fake breakout
above a resistance zone that runs long stops and then reverses, and gives two tells: a
**bearish RSI divergence** (price higher high, RSI lower high) and a **breakout on weak volume**.

The desk already had each tell on its own, but never all of them together:

| Existing piece | Earlier measurement |
|---|---|
| `Liquidity Sweep Bear` (equal highs pierced and closed back below) | B-41m: negative at every horizon but never significant |
| `RSI Divergence Bear` | B-19: −0.84% @20d, unstable across windows |
| OBV divergence overlay | not measured |

B-182 combines them into one detector, registers it as a **Risk** flag (`Bull Trap`, weight 0, it
only flags), draws it on the chart, and measures it.

## Pre-registration: written 2026-10-23, BEFORE any forward return was computed

**Detector:** `scanner_templates.bull_trap_events`. Every threshold is a named constant.
* **Failed breakout** at breakout bar *b* and trap bar *t*:
  * *R* = the highest high of the 20 sessions before *b* (`BT_RES_LOOKBACK`).
  * close[*b*] > *R* and close[*b*−1] ≤ *R*: the first close above resistance.
  * *t* = the first bar in *b*+1 … *b*+3 (`BT_FAIL_BARS`) that closes back below *R*. The event is dated *t*, the close at which the trap is known.
* **Weak volume:** volume[*b*] < 1.0 × the mean of the prior 20 sessions (`BT_WEAK_VOL_X`).
* **Bearish divergence:** RSI(14) at the highest high of *b* … *t* is at least 3 points (`BT_DIV_MIN_PTS`) below RSI(14) at the bar that set *R*. That bar must be at least 5 sessions (`BT_MIN_RES_AGE`) before *b*.
* **TRAP (full)** = failed breakout AND weak volume AND divergence. Events are at least 10 sessions apart (`BT_MIN_GAP`).
* No look-ahead: an event uses only bars up to *t*. This is pinned by `test_no_look_ahead_the_event_is_known_at_the_trap_close`.

**Panel:** nifty500, first 300 names, last 750 bars (the B-165 panel, `crt_sweep_overlap._fetch`).
Events whose trap bar falls inside that span count.

**Arms**
* **TRAP**: full bull traps. This is the decision arm.
* **FB_ONLY**: failed breakouts that are *not* full traps. Context: do volume and divergence add anything over a plain failed breakout?

**Outcome:** entry at the next open after *t*, exit at the close 20 sessions later, net of
`COST_INDIAN`, minus the symbol's all-bars mean over the span (the `crt_edge_study` machinery).
10 and 60 sessions are descriptive.

**Statistic:** per-symbol mean edge, then a one-sample t across symbols. Three calendar windows on
the pooled 20-session edges. TRAP − FB_ONLY is paired per symbol, and is descriptive only.

**Decision (fixed now).** A risk flag wants a **negative** edge.
* **TOO FEW** if TRAP has fewer than 30 symbols or fewer than 100 events at 20 sessions.
* **WARNS** if the TRAP 20-session mean edge is < 0 with p < 0.025, and negative in ≥ 2 of 3 windows.
* Otherwise **NOT ESTABLISHED**.

**Consequences.** All three keep `Bull Trap` registered as a Risk flag (weight 0) and keep the
chart overlay, because both are display. Only the card's wording changes:
* "MEASURED (B-182): WARNS", or
* "measured, not established", or
* "too few to read; re-run when the panel grows".

No verdict changes any ranking weight.

**Amendment, 2026-10-23, still before any forward return was computed.** Spacing as first
written ("events at least 10 sessions apart") let a *plain* failed breakout suppress a *full* trap
that followed it within 10 sessions. This was spotted while checking the overlay. The SUNPHARMA case
that prompted it turned out to be the RSI warm-up in amendment 2, but the suppression is real by
construction.
* **Amended spacing:** a full trap must be 10 sessions after the previous *full* trap. A plain failed breakout must be 10 sessions after the previous event of either kind.
* Pinned by `test_a_plain_failed_breakout_does_not_suppress_a_full_trap`.
* Nothing else changes: thresholds, arms, outcome and decision are as above.

**Amendment 2, 2026-10-23, still before any forward return was computed.** On SUNPHARMA a
300-bar window called 2025-10-14 a full trap with a 4.5-point divergence. The full history reads
the same event at 0.3 points. The prior high sat about 30 bars into the short window, where
Wilder's RSI has not yet forgotten its seed.
* **Amended:** no divergence is read at a prior high in the first 100 bars of the frame (`BT_RSI_WARMUP`).
* Pinned by `test_no_divergence_is_read_inside_the_rsi_warm_up`.
* The study panel's evaluation span starts about 290 bars into each frame, so the guard does not shrink the measured sample. It protects the chart (300-bar windows) and short scanner frames.
* Nothing else changes.

**Prior: NOT ESTABLISHED.** The components are weak or unstable on their own (B-19, B-41m), and
requiring all three makes events rare. Expected: a small negative edge, not significant.

## Result

**RUN 2026-10-23: TOO FEW.** `tools/bull_trap_study.py` as pre-registered (`0f716ff`,
amendments `971d303` and `e77b924`, all committed before the run). 258 of 300 names loaded.

| Arm | events (20 s) | symbols | 10 s | **20 s** | 60 s | 20 s by window |
|---|---|---|---|---|---|---|
| **TRAP** (full) | 55 | 49 | +1.05 (p 0.32) | **+0.03 (p 0.98)** | −0.24 (p 0.91) | +2.02 / −0.51 / −2.40 |
| FB_ONLY (plain failed breakouts) | 3,563 | 258 | +0.26 (p 0.051) | +0.11 (p 0.47) | +0.12 (p 0.68) | +3.17 / −0.99 / −2.17 |

Paired TRAP − FB_ONLY at 20 sessions: −0.38pp over 49 symbols (p 0.77).

**Verdict: TOO FEW.** 55 events is under the pre-registered 100.

**Reading:**
- Even ignoring the gate, the full trap shows **no warning**: +0.03% at 20 sessions, a coin flip.
- The powered arm is the informative one. Plain failed breakouts, 3,563 of them on 258 names, are **not followed by weakness**: +0.11%, p 0.47.
- So the infographic's premise ("fake breakout, so exit, then short below resistance") does not hold on NSE daily bars over this span. Adding the weak-volume and divergence tells did not change that (−0.38pp, p 0.77).
- Both arms swing with the tape: positive in the first window, negative in the last. That is regime, not the pattern.

**Consequence, as pre-registered:**
- `Bull Trap` stays a registered Risk flag (weight 0), and the chart overlay stays, because both are display.
- The card now reads "too few to measure". No ranking weight changes.
- Re-run when the panel grows. At this rate (about 0.2 full traps per name over 750 bars) reaching 100 events needs about 1.8× the panel.

This is calibration, not failure: it says to read a bull-trap arrow as context, not as a sell.
