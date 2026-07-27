---
title: "Falling-Wedge Scanner Fit — algorithm into our scanner framework (not a new app)"
category: analysis
tags: [roadmap, falling-wedge, scanner, trendline, chart-overlay, dashboard, architecture]
timeframe: milestone-plan
created: 2026-07-25
updated: 2026-07-25
sources: 1
related:
  - sources/Obsidian-Falling-Wedge-Screener-Prompt.md
  - concepts/Falling-Wedge.md
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/FVG-FBG-Fibonacci-Chart-Roadmap.md
---

# Analysis: Falling-Wedge Scanner Fit

## Thesis
The ingested note ([[sources/Obsidian-Falling-Wedge-Screener-Prompt]]) is a prompt to
build a **separate full-stack app** (FastAPI + APScheduler + React + Docker + CI) for a
falling-wedge screener. **The valuable part is the detection algorithm; the app
scaffolding duplicates infrastructure we already run.** The right move is to port the
algorithm ([[concepts/Falling-Wedge]]) into **one `scan_falling_wedge(df)` function** in
our existing framework — where it instantly inherits the universe, scheduler, both hubs,
and the chart overlay — **not** to fork a parallel stack.

> [!key-insight] We already are the app the prompt asks to build
> Streamlit dashboard + `chart_server` + yfinance fetch + the `SCANNERS` registry (feeds
> the Scanner Hub *and* Opportunity Hub) + a 4:05 PM scheduled batch + a chart overlay that
> already draws trendlines/VCP-zones/harmonics. Re-implementing that as FastAPI/React/Docker
> would maintain two of everything.

## Current State (grounded audit, 2026-07-25)
| Screener piece (from the prompt) | We already have | Where | Gap |
|---|---|---|---|
| **Swing-pivot detection** | `detect_bos_choch` (pivot-len swing highs/lows); `_darvas_box` fractal pivots | [scanner_templates.py](tools/scanner_templates.py) | reuse |
| **Trendline fitting (regression)** | `scan_rounding_bottom` uses `np.polyfit` linear legs; `/api/trendlines` endpoint | scanner_templates / [chart_server.py](tools/chart_server.py) | reuse `np.polyfit` on swing highs/lows |
| **yfinance data (120→60 bars)** | `sp.fetch_ohlcv(days=…)` | [screener_pipeline.py](tools/screener_pipeline.py) | reuse |
| **Universe (NIFTY / S&P) + filter** | bhavcopy / screener / manual universes; both hubs iterate them | dashboard_app | reuse (S&P optional) |
| **Scheduler (every 30 min)** | 4:05 PM daily batch + on-demand scans | Task Scheduler / hubs | reuse (daily is enough for 1D) |
| **Scanner → results UI** | `run_scanner` → card grid (Scanner Hub) + Opportunity Hub | scanner_templates / dashboard_app | reuse (cards, not the prompt's table) |
| **Chart modal w/ drawn wedge** | `patternCanvas` overlay already draws VCP base-zones, harmonics, **trendlines** | [chart_dashboard.html](tools/chart_dashboard.html) | add a wedge (2 lines + fill) draw |
| **Confidence 0–100 + states** | every graded scanner emits `score_base`; VCP/OB emit entry/stop/target + verdict states | scanner_templates | new: wedge-specific confidence factors |

## The gap (what's actually new)
1. **The wedge geometry function** — fit upper/lower lines from the last 2–3 swing
   highs/lows, validate (both negative, upper steeper, converging, ≥2 touches), and score
   confidence (touch-ratio · convergence · steepness · **containment** · recency). ~1 new
   `scan_*` function using `np.polyfit` + our pivot helper.
2. **Breakout state** — confirmed (>upper) / pre-breakout (within 0.5%) / none, plus a
   **volume-declining-into-apex** gate (our VCP dry-up logic transfers directly).
3. **Chart overlay** — draw the two trendlines + a translucent wedge fill + the breakout
   marker on the existing `patternCanvas` (mirrors the VCP-zone / harmonic draw already
   there). Optionally surface Containment% / Convergence% / Pivots like the screenshot.

## Evidence For
- **~85% is reuse** — pivots, `np.polyfit` trendlines, yfinance, the scanner registry,
  both hubs, the scheduler, and the chart overlay all exist; the wedge is one detector +
  one draw.
- **Instant distribution** — as a registered scanner it appears in the Scanner Hub *and*
  the Opportunity Hub with zero extra wiring, and becomes backtestable via
  [[analyses/Backtest-Harness]].
- **Algorithm is fully specified** — the ingested spec is exact (no research needed), and
  it pairs cleanly with our existing VCP volume dry-up logic.

## Evidence Against
- **Don't fork the stack** — the biggest risk is taking the prompt literally and building
  the FastAPI/React/Docker app; that maintains two screeners, two schedulers, two chart
  renderers. Extract the algorithm only.
- **Wedge fitting is finicky** — pivot look-back 1 is noisy; touch-tolerance and the
  regression window need tuning or the detector over-fires. Keep the confidence gate strict
  and backtest before trusting it.
- **Presentation** — the prompt's UI is a *table*; our Scanner Hub standard is **cards**
  (standing rule). Render wedge hits as cards in the hub; a table would only be right on a
  dedicated comparison surface (cf. [[analyses/Peer-Comparison-Roadmap]]).
- **Unbacktested confidence weights** — like every hand-set score here; route through the
  backtest harness before believing the 0–100.

## Phased plan (for later — not started)
- **FW-1 — `scan_falling_wedge(df)`** ✅ **SHIPPED 2026-07-25** in [scanner_templates.py](tools/scanner_templates.py):
  pivots → `np.polyfit` upper/lower → geometry gates (both-negative, upper-steeper, span ≥15,
  converging ≥10%, **containment ≥55%**, ≥2 touches/side) → confidence 0-100 → breakout state
  (Breakout/Pre-Breakout/Forming, deep-in-wedge → no fire) → structured entry/stop/target
  (measured move). Registered "Falling Wedge" (Pattern), in both hubs as cards. **Verified:**
  ITC live confirmed breakout (conf 100 → graded 87.5/Very Strong); containment gate dropped a
  28%-containment false positive (DABUR); all three states fire on a synthetic wedge; negatives
  reject. See [[log]] 2026-07-25.
- **FW-2 — Volume + state polish** ✅ **SHIPPED 2026-07-25:** volume-declining-into-apex
  soft gate (rejects `vol_trend>1.30`) + a volume factor in the confidence (dry-up scores
  above flat), and a metric surface — `Contain% · Conv% · {n}H/{n}L touches · Vol dry↓/flat`
  tags + structured `containment_pct/convergence_pct/touches_h/l/vol_trend/vol_dry` fields
  (which also seed FW-3). Verified: ITC live vol_trend 0.68 (drying) + 1.7× breakout
  expansion; rising-into-apex synthetic gated out.
- **FW-3 — Chart overlay** ✅ **SHIPPED 2026-07-25:** refactored the scanner over a shared
  `detect_falling_wedge_geometry` core (bar-index endpoints, the `detect_vcp_geometry`
  convention); new `/api/falling_wedge` endpoint; client overlay draws the two converging
  green trendlines + a translucent fill on `patternCanvas` + a breakout/state marker + a stat
  label. Live-verified in the browser (ITC: fill painted 2133px, stat panel + marker, clean
  toggle on/off, zero console errors).
- **FW-4 — Backtest** ✅ **SHIPPED 2026-07-25:** measured via [[analyses/Backtest-Harness]]
  (49 names, 1500 bars). **Positive forward-return edge at every horizon** — +0.14/+0.24/
  +0.74/+1.03% at 5/10/20/60d, ~60% hit, growing with time — plus **+0.14R expectancy**
  (46.5% target-hit) from the structured plan. **One of only two scanners (with Harmonic)
  that beat random entry, and the strongest at 20d/60d.** Caveat: gross, survivorship-biased,
  one ~6y window — encouraging, not proof; confirm on more windows before retuning weights.
- **Explicitly out of scope:** the standalone FastAPI/React/Docker/CI app — redundant with
  our stack.
- Packaging = native dashboard scanner (consistent with prior decisions).

## Action Taken / Plan
- ✅ Ingested the note (algorithm → [[concepts/Falling-Wedge]]; prompt →
  [[sources/Obsidian-Falling-Wedge-Screener-Prompt]]); this fit filed. **Nothing built.**
- ⏭ When ready: **FW-1** first (the scanner), then the chart overlay.

## Outcome (fill in later)
- **2026-07-25: FW-1 SHIPPED & verified** (ITC live confirmed breakout, graded 87.5/Very
  Strong; containment ≥55% gate added after a live false positive). Scanner live in both hubs.
- **2026-07-25: FW-2 SHIPPED & verified** — volume dry-up soft gate + confidence factor +
  metric surface (containment/convergence/touches/vol_trend on the card, structured fields
  for FW-3). ITC: drying (0.68×) + breakout expansion (1.7×); rising-volume synthetic gated.
- **2026-07-25: FW-3 SHIPPED & verified** — shared `detect_falling_wedge_geometry` core +
  `/api/falling_wedge` + client overlay (two green trendlines + translucent fill + breakout
  marker + stat label). Refactor kept the hub card byte-identical. Live browser-verified on
  ITC (fill drawn, panel + marker, clean teardown, no errors).
- **2026-07-25: FW-4 SHIPPED — and the wedge has measured edge.** Backtest over 49 names/1500
  bars: **positive forward-return edge at all horizons** (+0.14/+0.24/+0.74/+1.03% @5/10/20/60d,
  ~60% hit) + **+0.14R expectancy** (46.5% target-hit, n=256). One of only two scanners (with
  Harmonic) to beat random entry; strongest at 20d/60d. **ALL FOUR FALLING-WEDGE PHASES
  COMPLETE.** Gross/one-window caveat stands — confirm across windows before retuning.

## Related Pages
- [[concepts/Falling-Wedge]] · [[sources/Obsidian-Falling-Wedge-Screener-Prompt]] — pattern + source.
- [[analyses/Dashboard-UI-Roadmap]] — the scanner framework this extends.
- [[analyses/FVG-FBG-Fibonacci-Chart-Roadmap]] — sibling chart-overlay work (the wedge draw reuses the same `patternCanvas` path).
