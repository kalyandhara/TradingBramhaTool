---
title: "Backtest Harness — point-in-time scanner replay + edge-vs-baseline"
category: analysis
tags: [backtest, scanner, edge, expectancy, methodology, look-ahead, dashboard, phase3]
timeframe: milestone-plan
created: 2026-07-25
updated: 2026-07-25
sources: 0
related:
  - analyses/Dashboard-UI-Roadmap.md
  - strategies/RSI-60-40-Setup.md
---

# Analysis: Backtest Harness — point-in-time scanner replay

## Thesis

Every threshold, weight, and verdict across the M1–M4 spine and the 22 Scanner
Hub scanners is **hand-set** — flagged repeatedly as the single biggest
credibility gap ([[analyses/Dashboard-UI-Roadmap]] Phase 3). [backtest.py](tools/backtest.py)
is the measurement layer: it replays any `scan_*(df) -> dict | None` scanner over
history, bar by bar, and answers the only question that matters — **did firing
actually precede above-baseline forward returns, or does it just look good in a
bull tape?**

## Method (the honesty-critical parts)

- **No look-ahead.** At bar `t` the scanner is handed **only `df.iloc[:t+1]`** — it
  physically cannot see the future. Entry is taken at the **next bar's open**
  (`t+1`), never the signal bar's own close, so a close-dependent signal can't be
  "traded" on that same close.
- **Baseline = random entry in the same tape.** Every scanner looks green in an
  up market. *Edge* here = the signal's average forward return **minus** the
  average forward return of **all bars** over the same symbols/window — i.e. did
  firing beat a coin-flip entry on the same names over the same period.
- **De-duplication.** A trending scanner fires on many consecutive bars; each
  recorded signal is spaced by `min_gap` (default 5 bars) so a single run isn't
  counted as dozens of correlated "trades."
- **R-expectancy only where a structured plan exists.** Scanners that expose
  top-level `entry`/`stop`/`target` get a stop-or-target-first simulation
  (pessimistic same-bar tie → stop wins) and an expectancy in R. **v1 limitation:**
  today essentially every scanner writes its plan into *reason-text*, not
  structured fields, so the R path — though unit-verified correct — stays dormant
  until scanners expose the plan as fields (the clear follow-on).
- **Thin samples flagged, not hidden.** < 30 signals ⇒ `thin_sample`, shown as
  directional-only rather than quoted as a headline.

**Labelled v1 limitations:** survivorship bias (only names that exist today),
no costs/slippage (gross returns — a real edge must survive costs), history depth
varies by listing age.

## v1 findings (49-name liquid universe, ~6y / 1500 bars, gross)

| Scanner | Signals | 20d edge vs baseline | Read |
|---|---|---|---|
| **Falling Wedge** | 256 | **+0.74%** (59.8% hit) | **Positive edge at EVERY horizon**, growing to **+1.03% @60d** (61.7% hit); R-expectancy **+0.14R** (46.5% target-hit). The strongest-edge scanner measured at 20d/60d |
| **Harmonic Reversal (XABCD)** | 245 | **+0.67%** (60% hit) | Consistent positive edge (5–20d); the first scanner found to beat baseline |
| Order Block Retest | 734 | −0.74% | Slightly +ve R (+0.11R) from 2R targets, but raw forward-edge ≤ baseline |
| RSI 60-40 Setup | 1766 | −0.50% | No edge vs random entry as currently tuned |
| VCP Coiling | 1994 | −0.44% | Coiling ≠ tradeable edge on its own |
| Structural Breakout | 1137 | −0.45% (−1.37% @60d) | Fades over longer horizons |

> [!key-insight] The harness sorts the scanners by measured edge
> Of the scanners tested, **only two beat a coin-flip entry in the same tape:
> Falling Wedge and Harmonic Reversal** — and the Falling Wedge is the strongest
> at 20d/60d (+0.74% / +1.03%, ~60% hit, +0.14R). The rest (Order Block, RSI-60-40,
> VCP, Structural Breakout) show **negative or negligible** forward-return edge.
> This is exactly the credibility check the roadmap wanted — the numbers are now
> *measured*, not asserted. Caveat: gross, survivorship-biased, one universe,
> one ~6y window (mostly constructive tape) — directional, not a verdict.

## Evidence For / Against

**For:** the look-ahead-safe replay is generic (works on all 22 scanners with
zero per-scanner code); the baseline makes "edge" honest; findings already
contradict the implicit assumption that every scanner has edge.

**Against:** ~90s per scanner over 50 names (stride=1) — fine headless, needs
caching + progress before it's an interactive dashboard page; the R path is
dormant until plans are structured; a single ~6y window can't separate skill from
regime — needs multiple windows / walk-forward before any scanner is "validated."

## Action Taken / Plan

- ✅ **Engine shipped & verified** (2026-07-25). [backtest.py](tools/backtest.py):
  `backtest_scanner()` + `_simulate_plan()` + `format_report()`. Run headless:
  `python tools/backtest.py "RSI 60-40 Setup"`. Look-ahead safety verified by
  construction; `_simulate_plan` unit-verified (target=+2R, stop=−1R, tie→stop);
  forward-return/edge path verified live on 5 scanners.
- ⏭ **Expose scanner trade-plans as structured fields** → unlocks the R-expectancy
  path across the hub (small, high-value follow-on).
- ⏭ **Dashboard surface** (Ops tab): scanner picker + universe size + progress bar
  + cached results, once the slow-run UX is handled. Engine-first, as with M3/PEAD.
- ⏭ **Multiple windows / walk-forward** + transaction costs before calling any
  scanner "validated"; then feed measured expectancy back into the M1 Overall
  Rating weights and each scanner's thresholds.

## Outcome (fill in later)
- _2026-07-25: engine live; first findings recorded above. No thresholds retuned
  yet — that waits on multi-window confirmation._

## Related Pages
- [[analyses/Dashboard-UI-Roadmap]] — Phase 3; this is the backtest-harness item.
- [[strategies/RSI-60-40-Setup]] — first scanner measured (no edge as tuned).
