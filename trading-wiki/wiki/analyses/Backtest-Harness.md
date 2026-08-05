---
title: "Backtest Harness — point-in-time scanner replay + edge-vs-baseline"
category: analysis
tags: [backtest, scanner, edge, expectancy, methodology, look-ahead, dashboard, phase3]
timeframe: milestone-plan
created: 2026-07-25
updated: 2026-08-05
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
  (pessimistic same-bar tie → stop wins) and an expectancy in R. A plan may also
  declare a **`time_stop`** in bars, reported as a `"time"` exit distinct from
  `"open"` — a planned exit is not the same event as running out of measurement
  window. *(Live since 2026-08-05 on Harmonic Reversal and Falling Wedge; 20 of 24
  scanners still write their plan into reason-text only.)*
- **Plan coverage is reported, never assumed.** The simulator is **long-only**, so
  a short-side plan returns None. Those are counted and printed
  (`plan coverage: 122/248`) rather than silently dropped — an expectancy quoted
  over half the signals must say so.
- **Thin samples flagged, not hidden.** < 30 signals ⇒ `thin_sample`, shown as
  directional-only rather than quoted as a headline.

**Labelled v1 limitations:** survivorship bias (only names that exist today),
no costs/slippage (gross returns — a real edge must survive costs), history depth
varies by listing age.

## v1 findings (49-name liquid universe, ~6y / 1500 bars, gross)

| Scanner | Signals | 20d edge vs baseline | Read |
|---|---|---|---|
| **Falling Wedge** | 256 | **+0.74%** (59.8% hit) | **Positive edge at EVERY horizon**, growing to **+1.03% @60d** (61.7% hit); R-expectancy **+0.14R** (46.5% target-hit). The strongest-edge scanner measured at 20d/60d |
| **Harmonic Reversal (XABCD)** | 245 | **+0.67%** (60% hit) | Consistent positive edge (5–20d); the first scanner found to beat baseline. **R added 2026-08-05: +0.25R, 63.1% win (n=122) — the best R-expectancy of the three scanners measured**, see below |
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
caching + progress before it's an interactive dashboard page; the R path now runs
but reaches only the 4 scanners that emit plans, and only their **long** side; a
single ~6y window can't separate skill from regime — needs multiple windows /
walk-forward before any scanner is "validated."

## Action Taken / Plan

- ✅ **Engine shipped & verified** (2026-07-25). [backtest.py](tools/backtest.py):
  `backtest_scanner()` + `_simulate_plan()` + `format_report()`. Run headless:
  `python tools/backtest.py "RSI 60-40 Setup"`. Look-ahead safety verified by
  construction; `_simulate_plan` unit-verified (target=+2R, stop=−1R, tie→stop);
  forward-return/edge path verified live on 5 scanners.
- ✅ **Structured trade-plans — started 2026-08-05, Harmonic Reversal first.** The
  R path is no longer dormant on the scanner that measured the second-best edge.
  Plus per-plan **`time_stop`** support (backlog **B-5**) and plan-coverage
  counters. See Outcome. **Still open:** 20 of 24 scanners emit no plan — though
  several of those are screens (Stage 2, 52-Week High) that should *not* be given
  a fabricated entry/stop just to make a number appear.
- ⏭ **Dashboard surface** (Ops tab): scanner picker + universe size + progress bar
  + cached results, once the slow-run UX is handled. Engine-first, as with M3/PEAD.
- ⏭ **Multiple windows / walk-forward** + transaction costs before calling any
  scanner "validated"; then feed measured expectancy back into the M1 Overall
  Rating weights and each scanner's thresholds.

## Outcome (fill in later)
- _2026-07-25: engine live; first findings recorded above. No thresholds retuned
  yet — that waits on multi-window confirmation._

### 2026-08-05 — the R path opened on Harmonic Reversal (+0.25R)
`scan_harmonic_reversal` now emits `entry` / `stop` / `target` / `targets` / `rr` /
`direction`. **The plan was never missing — `harmonic_patterns.detect_last_pattern`
had computed all of it since day one, and the scanner rendered it into
reason-*text* and threw the numbers away.** The "dormant R path" was three lines
of dict, not a modelling problem.

| Scanner | Signals | R-expectancy | Win% | Plan coverage |
|---|---|---|---|---|
| **Harmonic Reversal** | 248 | **+0.25R** | 63.1% | **122/248** — bearish half unsimulatable |
| Falling Wedge | 254 | +0.14R | 46.5% | 254/254 |

**Harmonic now has the best measured R of the three scanners with plans**, and it
already had the second-best forward edge. Falling Wedge re-ran unchanged
(+0.14R / 46.5%), confirming no regression.

**Two things this exposed, both about measuring the wrong thing quietly:**
- **The target had to be T2, not the ladder.** The harness reads `target[0]` when
  handed a sequence. Emitting `targets` as a list would have measured to **T1
  (0.382)** while the scanner gates on and advertises **`rr_to_t2` (0.618)** — a
  backtest silently grading a different plan than the card promises is worse than
  no backtest. `target` is the scalar T2; the ladder rides alongside as `targets`.
- **Half the signals cannot be simulated at all.** 126 of 248 harmonics are
  **bearish**, and `_simulate_plan` is long-only (`risk = entry − stop`), so they
  returned `None` and vanished — the expectancy was about to be quoted over 49% of
  signals as though it covered all of them. The simulator now counts them and
  `format_report` prints `plan coverage: 122/248 (126 skipped)`. **+0.25R is the
  bullish subset; the short side is unmeasured, not zero.** Same discipline as
  `market_health`'s coverage floor, applied to a backtest.

**`time_stop` shipped (backlog B-5).** A plan may now declare how many bars it may
run before being closed regardless of price, and a `"time"` exit is reported
distinctly from `"open"` — a deliberate exit and a trade that merely ran out of
measurement window are different events. Unit-verified across seven cases
(time-stop fires at exactly N bars · target and stop still pre-empt it · a
time-stop longer than the data correctly reports `open`, not `time` · same-bar
tie still resolves to the stop · short-side still returns None). **No scanner
declares one yet** — the machinery is in, the numbers wait on evidence rather than
being invented, which is the whole point of this harness.

**Unchanged and still the gate:** gross, survivorship-biased, one ~6y window.
Nothing is retuned until multi-window/walk-forward + costs land.

## Related Pages
- [[analyses/Dashboard-UI-Roadmap]] — Phase 3; this is the backtest-harness item.
- [[strategies/RSI-60-40-Setup]] — first scanner measured (no edge as tuned).
