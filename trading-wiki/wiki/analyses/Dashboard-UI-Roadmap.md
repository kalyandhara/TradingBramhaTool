---
title: "Dashboard UI Roadmap — Toward the Predictive Analysis View"
category: analysis
tags: [ui, ux, roadmap, dashboard, prediction, ratings, pattern-annotation, consolidation, backtest]
timeframe: milestone-plan
created: 2026-07-08
updated: 2026-07-19
sources: 1
related: [sources/MarketTerminal-UI-Reference, sources/Fingrad-Trading-Infographics-Collection, analyses/Dashboard-UX-Operational-Requirements]
---

# Analysis: Dashboard UI Roadmap — Toward the Predictive Analysis View

> [!key-insight] 2026-07-19 update — status reconciliation & expanded roadmap
> The original M1–M4 plan below (2026-07-08) still holds, but two things changed since: **M1 never shipped** (the Setup Intelligence panel shipped instead — a per-symbol cousin, not the Scanner Hub /100 rollup), and **almost the entire build is uncommitted**. The re-sequenced roadmap adds a **Phase 0 (consolidate/de-risk)** in front of the milestones, and **Phase 2–4** behind them. Detail in the two new sections directly below; the M1–M4 specifics remain authoritative and are unchanged further down.

## Current State (grounded, 2026-07-19)

**Shipped** — 17 pages across 5 sidebar groups (`PAGE_GROUPS` in [dashboard_app.py](tools/dashboard_app.py)):
- **Screening:** Screener · Other Screeners · Scanner Hub · Breakout Screener · High-Growth Screener · TradingView Screener
- **Market Intel:** Market Sentiment · India Market Intel
- **Research:** Stock Analyzer (+ Setup Intelligence panel, MACD, CANSLIM RS) · Sector Map · Astro Timing · Telegram Signals
- **Portfolio & Risk:** Portfolio · Watchlist · Alerts — **Ops:** Pipeline Log
- Chart-server detectors exposed ([chart_server.py](tools/chart_server.py)): `/api/vcp`, `/api/rounding_bottom`, `/api/trendlines`, `/api/harmonic`, `/api/reversal_events`, `/api/ohlcv`, `/api/tick`.

**Two gaps vs. the 2026-07-08 plan:**
1. **M1 (Overall Rating /100 rollup) never shipped** — grep finds no composite-score column in `dashboard_app.py` / `scanner_templates.py`. Still the highest-ROI, lowest-risk change.
2. **Version-control risk is now the #1 blocker.** Only 5 commits exist; ~35 untracked files including whole subdirs (`breakout_scanner/`, `indian-trading-agent-main/`, `pine_scripts/`). The tracked `dashboard_app.py` imports **untracked** modules (`stock_council`, `harmonic_patterns`, `sentiment_index`, `astro_trading`, `astrohora_loader`, `telegram_signals`) — a fresh checkout at HEAD would fail to launch.

## Expanded Roadmap (phases wrapping the milestones)

### Phase 0 — Consolidate & de-risk *(do first; blocks everything)*
- Commit untracked modules in logical groups (astro suite · pattern detectors · sentiment · telegram · screeners); verify the committed tree launches.
- Pin dependencies (`requirements.txt`) + a one-command smoke test.
- Classify `indian-trading-agent-main/` and `breakout_scanner/` — vendored/fork/dead — then integrate or `.gitignore`.

### Phase 1 — Finish the Predictive Analysis spine
The **M1 → M2 → M4 → M3** sequence detailed further down (M1 first, projection M3 last).

### Phase 2 — Turn ingested knowledge into features
- **Decision-support gating (market-health + ownership-flow)** — the crash-proof 3-filter system. Extends `market_verdict.py`'s existing STAND DOWN ladder to the framework's five market-health conditions, adds the full FII/DII/MF/Retail ownership split, then the market×ownership decision matrix and an FPV confirmation chip. Sequenced separately in **[[analyses/Decision-Support-Gating-Roadmap]]** (DS-1…DS-4). See [[strategies/Crash-Proof-3-Filter-System]].
- **Fibonacci overlay** — *shipped 2026-07-21* as a client-side overlay ([fibonacci.js](tools/fibonacci.js)): swing-anchored 0.236–0.786 grid + 1.272/1.618 extensions, scored against Volume-Profile confluence and the price projection into an entry/stop/target plan (not the originally-planned `/api/fibonacci` server route — done client-side to reuse `EW.computeZigzag` + `VP.findConfluence`). See [[concepts/Fibonacci-Retracement]]. NB: this feature's "confluence" is price+volume-profile, **not** the ownership-flow FPV in [[concepts/FPV-Flow-Price-Volume-Ownership]].
- **FVG + FBG + Fibonacci confluence** — extend the Fibonacci overlay to score FVG zones (midpoint ≈ 0.50), upgrade the chart's raw `fvg.js` to the quality-gated definition, add a **FBG (breaker) detector** (the one greenfield piece), and a price+volume + retail-checklist gate. Sequenced as FF-1…FF-5 in **[[analyses/FVG-FBG-Fibonacci-Chart-Roadmap]]**. See [[concepts/Fair-Value-Breaker-FBG]].
- **RSI 60-40 setup** → Scanner Hub scanner + Pattern alert + Setup Intelligence factor. See [[strategies/RSI-60-40-Setup]].
- **Wire orphaned detectors into Setup Intelligence scoring** — the recurring log TODO: `volume_profile.py` (POC/VAH/VAL), order blocks.

### Phase 3 — Depth & trust
- **Backtest harness** — Setup Intelligence thresholds are hand-set; RSI-60-40 + scanners are flagged unbacktested. Measured expectancy is the biggest credibility upgrade available.
- **Unify alert taxonomy** across the Pine side and the Alerts tab (open item in [[analyses/Dashboard-UX-Operational-Requirements]]).
- **Scope the Astro vertical** as a regime/context modifier, never a standalone entry signal.

### Phase 4 — Surface polish *(only on real need)*
Live data / auto-refresh / mobile / push. The React/FastAPI rebuild stays deferred until multi-device or sub-second needs actually appear.

## Thesis
The Predictive Analysis view from Market Terminal ([[sources/MarketTerminal-UI-Reference]] §Predictive Analysis View) is the target end-state for our Stock Analyzer tab. It answers *"should I take this trade, and if so, what's the target and confidence"* on a single screen by fusing ratings + pattern detection + AI projection + fundamentals context.

We already have ~80% of the underlying capability — Minervini/TechnoFunda/CANSLIM scores, `/api/vcp` + `/api/rounding_bottom` + `/api/trendlines` pattern detectors, the Pree Market Tool two-brain LLM pipeline, screener_pipeline fundamentals. What's missing is **the surface** — the rating rollup, the on-chart annotation, the projection line, and the layout that puts them on one screen.

This page sequences the work so each milestone is independently useful (each ships value even if the next never ships).

## Evidence For (why do this, why now)
- **All backend pieces exist.** No new data source, no new model, no new dependency. Every ingredient is already computed somewhere in the stack — it's a UI/wiring exercise, not a research one.
- **Highest single ROI change in the dashboard right now.** Roll-up scoring turns the Scanner Hub from "columns of numbers" into "triage by color." Every other flagged UI change compounds on top.
- **The user has explicitly targeted this** (2026-07-08 conversation) as the direction — not speculative UI polish.
- **Direct competitor benchmark.** Market Terminal is a paid product with this exact layout; matching-then-exceeding gives an honest measuring stick.

## Evidence Against (why this could wait)
- **Ratings composite is a design decision, not just implementation.** Weighting Minervini vs TechnoFunda vs CANSLIM vs EW requires picking a philosophy. Getting it wrong means users don't trust the number.
- **The AI Prediction line is the *hardest* piece** and users tend to over-index on it. If we ship the projection before the ratings/patterns land, they'll trust the projection alone, which is exactly the wrong risk shape.
- **Existing users have muscle memory** on the current Stock Analyzer layout. Big re-layouts have adoption friction.

## Conclusion — sequence in three milestones

Each milestone is independently valuable and can be shipped without the next one.

### Milestone 1 — Overall Rating rollup in Scanner Hub (highest ROI, lowest risk)
**Goal:** Every row in the Scanner Hub result set gets one **Overall Rating /100** column with color, plus the existing per-system scores as sub-columns.

- **Data:** already computed. `score_minervini` (returns /8), `score_technofunda` (returns /6), `_compute_canslim` (returns /4), `ew_module.analyze_ew` (returns confidence %). Roll-up formula, first draft:
  - Overall = 100 × ( (Minervini/8) × w_M + (TechnoFunda/6) × w_TF + (CANSLIM/4) × w_C + (EW.confidence/100) × w_EW )
  - Initial weights: w_M=0.35, w_TF=0.25, w_C=0.20, w_EW=0.20 — bias toward Minervini as the most-referenced framework on this wiki.
  - Weights configurable via a Streamlit sidebar for tuning.
- **UI:** Overall Rating becomes the leftmost after Symbol; existing per-system columns move behind an "Expand row" toggle.
- **Color scale:** ≥85 green, 70-84 amber, 50-69 grey, <50 red. Same as the source.
- **Effort:** 1-2 hours. `tools/dashboard_app.py` changes only; nothing on the chart side.
- **Ships value:** Scanner Hub becomes triageable at a glance. Everything else compounds on this.

### Milestone 2 — Pattern boxes with click-for-metadata tooltip on the chart
**Goal:** When VCP / Rounding Bottom / Trendline detectors fire, render each detection as a **semi-transparent filled rectangle** on the chart canvas labelled with the pattern name; clicking the box opens a **tooltip with the detection metadata** (pivot levels, depth, duration).

- **Data:** endpoints already return the geometry. VCP returns `pivot`, `base_low`, `base_start_time`, `base_end_time`, contractions[], `verdict`, `entry`, `stop`, `target`. Rounding Bottom returns the arc anchors. Trendlines return the two anchor points + projected endpoint.
- **UI:** overlay canvas (already exists for volume-profile and FVG at chart_dashboard.html) — extend to render pattern-name-labelled rectangles. Click handler on the box → floating card with the geometry table (Consolidation N days · Breakout Pivot $X · Breakdown Pivot $Y · Depth Z%).
- **Effort:** 3-4 hours. `tools/chart_dashboard.html` only; endpoints unchanged.
- **Ships value:** the "where on the chart" answer becomes visual. Also makes existing detectors more useful — most users don't currently look at the raw `verdict` field.

### Milestone 3 — AI Prediction line + % on the chart
**Goal:** A dashed forward-projection line from current price to a projected price at N days out, labelled with the projected price and % move on the right edge. Sourced from an LLM analysis of the same packet the Pree Market Tool already produces.

- **Data:** extend the Pree Market Tool's Claude/Codex prompts to emit, for each Day watchlist name, a structured `{projected_price, days_out, confidence_%}` block. Alternatively, run a smaller per-symbol projection pass on demand from the dashboard.
- **UI:** dashed blue line series (lightweight-charts LineSeries with dashed style) from current bar → projected bar; right-edge label with two numbers stacked.
- **Guardrails to prevent projection-overtrust:**
  - Never show the projection without the Ratings rail visible on the same screen (Milestones 1+2 must ship first).
  - Show a **confidence badge** (High / Medium / Low) alongside the projection; hide the projection entirely if confidence is Low.
  - Show the *reasoning* (LLM output text) in a collapsible below the projection — never a naked number.
- **Effort:** 6-8 hours if leveraging existing Pree Market Tool; adds a new endpoint on chart_server.
- **Ships value:** the "what next" answer. The order Milestone 3 last is deliberate — the projection is the most seductive number and the most brittle; landing it after the honest ratings + patterns keeps users grounded.

### Milestone 4 (stretch) — Consolidated Predictive Analysis tab
**Goal:** A dedicated "Predictive Analysis" tab in the dashboard that composes M1 + M2 + M3 into one screen (Market Terminal META view equivalent). Layout:

- Left: screener table (like the current Scanner Hub) with Overall Rating column.
- Right (dominant): chart pane with pattern boxes + AI Prediction line, plus a docked left rail with the Ratings breakdown + Revenue/Earnings/Institutional mini-charts (data available from screener_pipeline).

This milestone is *purely composition* — no new backend, no new detection, no new LLM work. It's the surface that makes M1+M2+M3 add up to more than the sum of parts.

- **Effort:** 4-6 hours of Streamlit + chart_dashboard integration once the prerequisites ship.

## Action Taken / Plan
- **Sequencing rule:** don't start Milestone N until N-1 is shipped and validated with one session of live use. This prevents the M3-projection-first anti-pattern.
- **Owner:** user-driven; not started. Milestone 1 recommended as the first pull request.
- **Time budget total (M1-M4):** ~15-20 hours. Milestone 1 alone is 1-2 hours and delivers most of the daily-use benefit.

### Prerequisites already in place
| Piece | Status | Where |
|---|---|---|
| Minervini score | ✅ Computed | [screener_pipeline.py](tools/screener_pipeline.py) `score_minervini` |
| TechnoFunda score | ✅ Computed | [screener_pipeline.py](tools/screener_pipeline.py) `score_technofunda` |
| CANSLIM RS score | ✅ Computed | [dashboard_app.py](tools/dashboard_app.py) `_compute_canslim` |
| EW confidence | ✅ Computed | [ew_module.py](tools/ew_module.py) `analyze_ew` |
| VCP detection + geometry | ✅ Exposed | `/api/vcp` on [chart_server.py](tools/chart_server.py) |
| Rounding Bottom detection | ✅ Exposed | `/api/rounding_bottom` |
| Trendline detection | ✅ Exposed (2026-07-08) | `/api/trendlines` |
| Annual fundamentals for mini-charts | Partial | screener_pipeline has some; may need extension |
| Two-brain LLM analysis | ✅ | `C:\python_project\Pree_Market_Tool` — see [[sources/PreMarketTool-repo]] |
| Chart overlay canvas | ✅ | volCanvas/fvgCanvas pattern in `chart_dashboard.html` |
| Semi-transparent filled shapes on canvas | ✅ Pattern exists | drawVolumeProfile + drawFVG |

Everything the plan needs is either already present or is a small extension of an existing piece. No architecture changes required.

## Outcome (fill in later)
- **2026-07-19:** M1 still not shipped as of this review — the Setup Intelligence panel (2026-07-16) covered the *per-symbol* synthesis but not the Scanner Hub /100 rollup. M2 backend (pattern geometry endpoints) is fully in place; only the on-chart overlay remains. Phase 0 (git consolidation) identified as the true first step. Execution started this session — see [[log]].
- **2026-07-20 — Phase 0 done, M1 SHIPPED & verified.** Phase 0: repo consolidated into 9 logical commits (1.9 GB vendored dir + node_modules gitignored; HEAD now self-consistent — all `dashboard_app.py` local imports resolve). M1: `_overall_rating()` fuses Minervini/8 + TechnoFunda/6 + CANSLIM/computable + EW-confidence/100 (weights 0.35/0.25/0.20/0.20, tunable via a Scanner Hub "Overall Rating weights" expander that re-normalises to 1.0). Each scanner-hit card now shows an **Overall NN/100 colour badge** (≥85 green / 70–84 amber / 50–69 grey / <50 red) with an M/TF/C/EW breakdown tooltip; results **sort by Overall Rating** with a **Min Overall Rating** floor slider. Computed once at scan time (reuses the scanner's cached OHLCV). **Verified live:** Stage 2 scan over 15 large-caps → TITAN 76/100, SUNPHARMA 75/100, correctly sorted, no errors. Rendered in [dashboard_app.py](tools/dashboard_app.py) `_overall_rating`/`_rating_badge_html`.
- **2026-07-20 — M2 essentially pre-built; completed with base-zone shading & verified.** Investigation found the four pattern overlays (VCP, Rounding Bottom, Harmonic, Trendlines) were **already implemented** in [chart_dashboard.html](tools/chart_dashboard.html) — added after this roadmap was written and only committed today in Phase 0. They render *more* than the original M2 spec: contraction ladders / XABCD zigzags / rim+trough markers + entry/stop/target lines + collapsible info panels with full trade plans. So the literal "filled box + click-tooltip" model was **not** rebuilt (it would duplicate the superior info panels and risk regression). The one genuinely missing M2 visual — a **semi-transparent shaded base/consolidation zone** — was added for VCP (base_start→base_end × base_low→pivot, cyan) and Rounding Bottom (base window × trough→rim, gold), on a new `patternCanvas` layer mirroring the FVG box style, redrawn on pan/zoom/resize and cleared on teardown. **Verified live** on TITAN (VCP `WATCH`, footprint 4/8/5/3): painted box pixel-bounds matched `timeToCoordinate`/`priceToCoordinate` of the base window to ±1px, correct cyan, 19,141px; toggling off cleared the canvas to 0px. RB shares the identical verified `box()` path (no live RB pattern in the market to demo). Harmonic/Trendlines pre-existing and unchanged.
- **2026-07-23 — M3 SHIPPED (analytical engine, not LLM) & verified with guardrail fixes.** Engine decision: no LLM is configured anywhere in the repo (the Pree Market Tool is a separate un-integrated project), and the repo already computes probabilistic price targets — so M3 shipped as a **deterministic, inspectable projection** instead of the roadmap's literal "LLM prediction": [projection.py](tools/projection.py) composes candidates from **Elliott Wave Fib targets** (price + prob% + count confidence) and **VCP / Rounding Bottom / Harmonic measured-moves** (target + verdict), picks the highest-confidence primary, and reports **confluence** ("N methods agree" within 3%). New `/api/projection` on [chart_server.py](tools/chart_server.py); chart UI draws a dashed forward slope from the last close to the target, a price+% label, and a bottom-right panel with **High/Medium badge, source, reasoning, invalidation stop, and a not-investment-advice disclaimer**. Guardrails held: anything below Medium floor returns `null` → nothing draws (verified: RELIANCE = 0 painted px, panel hidden). **Live verification caught a real overtrust bug**: with the client's 2600-bar (10Y) fetch, EW ran over the decade and produced TITAN "+137.9% High confidence." Fixed three ways: `ANALYSIS_BARS=300` fixed analysis window (2600-bar ≡ 300-bar now), `MAX_MOVE_PCT` per-TF plausibility cap (>60% daily rejected), and EW effective confidence = count_conf × (0.4 + 0.6×target_prob) so a 35%-prob Fib level can't read "High." Post-fix TITAN: **Medium 58, VCP target ₹5,409.76 (+15.2%), R:R 3.39×, stop ₹4,487** — rendered end-to-end in the browser. LLM narration remains an optional later layer if an API key is ever configured.
- **Spine complete: M1 + M2 + M3 all shipped.** Remaining composition milestone: **M4** (consolidated Predictive Analysis tab — pure composition of M1's ratings + M2/M3's annotated chart; no new backend). Then Phase 2 of the expanded roadmap (Fibonacci overlay — since partially built via the "Fibonacci + Trade Plan" chart entry — RSI-60-40 scanner, orphaned-detector wiring).

## Related Pages
- [[sources/MarketTerminal-UI-Reference]] — the design source this roadmap targets.
- [[sources/PreMarketTool-repo]] — provider of the LLM projection input for Milestone 3.
