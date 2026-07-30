---
title: "Dashboard UI Roadmap — Toward the Predictive Analysis View"
category: analysis
tags: [ui, ux, roadmap, dashboard, prediction, ratings, pattern-annotation, consolidation, backtest]
timeframe: milestone-plan
created: 2026-07-08
updated: 2026-07-29
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
- **RSI 60-40 setup** → ✅ **fully shipped 2026-07-25** across all three surfaces: Scanner Hub scanner (`scan_rsi_60_40`, "RSI 60-40 Setup", Entry, both hubs); **Pattern alert** (`rsi_60_40` metric in `ALERT_METRICS["Pattern"]` + a `check_alert` branch — `rsi_60_40 >= N` alerts on a live setup ≥ that quality); and a **Setup Intelligence factor** ("RSI 60-40 setup live — pullback/breakout" via `gather_evidence`+`setup_intelligence`). See [[strategies/RSI-60-40-Setup]].
- **Wire orphaned detectors into Setup Intelligence scoring** — the recurring log TODO: `volume_profile.py` (POC/VAH/VAL) ✅ *shipped 2026-07-25* (wired into `gather_evidence`/`setup_intelligence` in [stock_council.py](tools/stock_council.py): a Value-area location chip + POC-acceptance bullish/risk factors; fixed the trailing-NaN gap-bar bug that was silently nulling the profile). **Order blocks** ✅ *shipped 2026-07-25 as a greenfield detector* — `scan_order_block` ("Order Block Retest", Entry) in [scanner_templates.py](tools/scanner_templates.py), a bullish SMC demand-zone retest with a structured entry/stop/target (also the first scanner to exercise the [[analyses/Backtest-Harness]] R-path). Concept: [[concepts/Order-Block]].
- **Ingested feature foundations (2026-07-25, scoped for later — nothing built):** four sources filed as their own roadmaps — a **fundamental radar** ([[analyses/Radar-Chart-Analyzer-Fit]], RC-1…RC-4), an enhanced **Setup Intelligence panel** with a technical setup-quality radar + gauges + VCP-coil ([[analyses/Setup-Intelligence-Visual-Spec]], SV-1…SV-4), a **peer-comparison** table ([[analyses/Peer-Comparison-Roadmap]], PC-1…PC-4, the Opportunity Hub inverted), and a **falling-wedge scanner** ([[analyses/Falling-Wedge-Scanner-Fit]], FW-1…FW-4 — extract the algorithm into `scan_falling_wedge`, *not* the prompt's standalone app). All are ~80–85% composition of already-computed signals / existing scanner+chart infra + Plotly (already a dependency); packaging = native dashboard feature.
- **Structure-break enrichment (2026-07-29, scoped for later — nothing built):** ingested the **Structure Break Chain [SBC]** Pine indicator ([[sources/Structure-Break-Chain-SBC-Pine]], MPL 2.0 so a port is fine with attribution). Our `detect_bos_choch` walks the same rule but returns only `{signal, level, bars_ago}`; SBC contributes **break quality** (ATR-normalised distance + candle body → STRONG/NORMAL/WEAK), a **chain counter** (consecutive BOS since the last CHoCH), and a **time-boxed failed-break** flag. Plan SBC-1 (additive keys — the three existing consumers keep working) → SBC-2 (gate the SMC Structure check on quality, chain → Setup Intelligence persistence factor, failed → fail-risk chip) → **SBC-3 (backtest first, adopt second** — [[analyses/Backtest-Harness]] measured Structural Breakout at ≤0 edge and `scan_order_block` at +0.11R, both of which these filters would touch) → SBC-4 (chart overlay, only if SBC-3 pays).
  > **SBC-4 SHIPPED 2026-07-29, out of sequence** (user asked for the chart first). New `detect_structure_chain()` in [scanner_templates.py](tools/scanner_templates.py) (full event walk, both directions, with quality/chain/failed — `detect_bos_choch` untouched), new `/api/structure_chain` on [chart_server.py](tools/chart_server.py) with per-timeframe pivot defaults, and a `structure_chain` overlay in [chart_dashboard.html](tools/chart_dashboard.html) (dashed swing levels + BOS/CHoCH/FAILED markers + a chain card in the `.action-stack`, quality encoded as marker opacity). Live-verified on TITAN (47 markers read back off the series, clean teardown, zero console errors); `confirm=wick` measured as materially noisier than close (CHoCH 6→13, failed 7→15). **Displayed only — nothing is scored or gated by it yet, so SBC-1/2 and the load-bearing SBC-3 backtest are still open.** ✅ **Committed & deployed 2026-07-30** (`bc0d95a` tools + `2fded18` wiki) — it had been working-tree-only until then; re-verified from the committed tree on a cold chart_server (47 markers, 12 swing lines, clean teardown, zero console errors). Note the **name collision**: SBC is swing-structure BOS/CHoCH chaining, *not* our existing `scan_structural_breakout` horizontal-base scanner.
- **Fundamental deep-dive report on the Stock Analyzer (2026-07-29, scoped for later — nothing built):** ingested from a 4-screenshot long-horizon research page → [[analyses/Fundamental-Deep-Dive-Report-Roadmap]] (FR-1…FR-6). ~75% composition, but with **one genuinely new data layer**: yfinance annual/quarterly statements + balance sheet + cashflow are *login-free and completely unused in the repo today* — FR-1 adds them and thereby retires the screener.in dependency blocking [[analyses/Radar-Chart-Analyzer-Fit]] RC-2 and [[analyses/PEAD-Scanner-Roadmap]] 5.2 (ROCE + 3Y/5Y CAGRs become computable). The report's tab shell composes work already sequenced elsewhere (Peers → PC-1…PC-4, Ownership → DS-2), and its **honesty devices** (data-coverage dial, `DATA N/A` axes, "consensus unavailable — here's what we checked", inline projection derivations, three-state red flags incl. "not checked") are the cheapest, most transferable part. Narrative/LLM sections deferred to FR-6 — no LLM is configured (the M3 finding).

### Phase 3 — Depth & trust
- **Backtest harness** — ✅ *engine shipped 2026-07-25* ([backtest.py](tools/backtest.py); full write-up [[analyses/Backtest-Harness]]). Look-ahead-safe point-in-time replay + edge-vs-random-entry baseline, generic over all 22 scanners; unit-verified R-simulation (dormant until scanners expose structured plans). First finding: of 5 scanners measured, only **Harmonic Reversal** beat baseline; RSI-60-40 / VCP / Structural Breakout showed ≤0 edge. **Still open:** structured trade-plan fields (unlocks R-expectancy), a dashboard Ops surface, and multi-window/walk-forward + costs before retuning thresholds.
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
- **2026-07-23 — M4 SHIPPED & verified. ALL FOUR MILESTONES COMPLETE.** New **Predictive Analysis** page in [dashboard_app.py](tools/dashboard_app.py) (Research group, first entry) — pure composition, no new backend, exactly as scoped: left rail of candidates from the last Scanner Hub run ranked by M1 Overall Rating (compact badge cards → click to analyze; manual symbol input as fallback); right pane with the **/100 badge + M/TF/C/EW breakdown chips**, the **Chart Tool embedded via iframe** (carries M2 base-zone overlays + M3 projection + all saved indicators, with a graceful warning when chart_server is down), and the **Setup Intelligence + Council drill-down** reused from the Stock Analyzer. **Verified live:** TITAN → 81/100 (M 7/8 · TF 6/6 · C 2/4 · EW 75), iframe embedded at `?symbol=TITAN.NS`, Setup Intelligence rendered (RS Strong / Breakout readiness High / Accumulation Constructive), council expander present, no exceptions. Candidates rail verified in empty state only (no hub scan in the verification session — the rail reuses the same card/badge machinery as Scanner Hub, so risk is low).
- **Roadmap spine + composition done (M1→M4).** Next frontier per the expanded phases: **Phase 2** (RSI-60-40 scanner; wire orphaned detectors — volume-profile POC, order blocks — into Setup Intelligence; note the Fibonacci overlay largely arrived via the chart's "Fibonacci + Trade Plan" entry) and **Phase 3** (the backtest harness — now the single biggest credibility upgrade, since every verdict/threshold/weight in M1–M4 remains hand-set until measured).
- **2026-07-25 — Phase 2 started: RSI 60-40 scanner SHIPPED.** `scan_rsi_60_40` + `_rsi_series` (Wilder) in [scanner_templates.py](tools/scanner_templates.py), registered "RSI 60-40 Setup" (Entry, 22 scanners now), live in both hubs. Trend-regime gate (price>EMA21&EMA50, EMA21>EMA50, RSI in a real 40-60 band) → RSI-40 pullback (stop<EMA50) or RSI-60 breakout (stop<EMA21), each with a 2R plan + `score_base`/`rs_raw` RS-blend. Live-verified (M&M RSI-60 Breakout → run_scanner score 64.5/Moderate; branch A confirmed via sweep; downtrend/short/RSI-pinned negatives reject).
- **2026-07-25 — Phase 2 cont'd: Volume Profile wired into Setup Intelligence.** The orphaned `volume_profile.py` (POC/VAH/VAL, chart-only until now) now feeds `gather_evidence`/`setup_intelligence` in [stock_council.py](tools/stock_council.py): a **Value-area location** chip + POC-acceptance factors (above VAH → POC support; below VAL → POC overhead; on-POC → tight-stop pivot). Fixed the recurring trailing-NaN gap-bar bug (nulled the profile for 3/5 test names) with a `dropna` before the VP call. Live-verified on 5 names (reads coherent with each verdict); dashboard boots clean (HTTP 200); py_compile clean.
- **2026-07-25 — PHASE 2 COMPLETE.** Closed the final three items: the RSI-60-40 **Pattern alert** (`rsi_60_40` metric + `check_alert` branch) and **Setup Intelligence factor** (reuses `scan_rsi_60_40`), and the **order-block detector** (`scan_order_block`, "Order Block Retest", Entry — greenfield SMC demand-zone retest with a structured entry/stop/target; new concept [[concepts/Order-Block]]). The order block emits a real trade plan, so it became the first scanner to exercise the [[analyses/Backtest-Harness]] R-simulation in integration (734 signals, win% 28.9, **+0.11R expectancy**). All verified (9 live OB hits; factor+alert positive/negative paths; dashboard boots clean). Phase 2 features remaining are only the deferred items folded elsewhere (Fibonacci arrived via the chart; decision-support & FVG/FBG have their own roadmaps). **Next frontier is Phase 3** (backtest depth + alert-taxonomy unification + Astro scoping).
- **2026-07-25 — Phase 3 started: Backtest Harness engine SHIPPED.** [backtest.py](tools/backtest.py) — look-ahead-safe point-in-time replay (scanner sees only `df.iloc[:t+1]`, entry next-bar-open), edge-vs-random-entry baseline, generic over all 22 scanners; `_simulate_plan` R-sim unit-verified but dormant until scanners expose structured plan fields. Verified live on 5 scanners (49-name universe, 1500 bars): **only Harmonic Reversal beat baseline** (+0.67% @20d, n=245); RSI-60-40/VCP/Structural Breakout all ≤0 edge — the measured credibility check the roadmap wanted. Full write-up: [[analyses/Backtest-Harness]]. Phase 3 still open: unify alert taxonomy; scope Astro as a regime modifier; plus the harness follow-ons (structured plans → R, Ops UI surface, multi-window/walk-forward + costs).
- **2026-07-23 — M5 track opened (new *scanner*, beyond the UI spine): NSE Proxy-PEAD.** Phase 1 shipped — `scan_pead()` "Proxy-PEAD Drift" in [scanner_templates.py](tools/scanner_templates.py), live-verified over 30 NSE names in Q1 earnings season (HCLTECH/TCS/INFY real drifts; NaN-bar bug caught & fixed). Honest by design (no free NSE consensus estimate → event inferred from price, labelled "Proxy"). Full phased plan: [[analyses/PEAD-Scanner-Roadmap]].
- **2026-07-24 — M5 Phase 5.1 SHIPPED: "Zero-Debt Quality PEAD" scanner.** User asked for a scanner over **Zero-Debt + high ROE/ROCE/OPM** names carrying the PEAD drift edge. Built as a new Scanner Hub entry combining a **yfinance** fundamentals gate (no login) with `scan_pead` at the symbol level (`run_quality_pead` in [scanner_templates.py](tools/scanner_templates.py); sliders + progress bar in [dashboard_app.py](tools/dashboard_app.py)). Pivoted off the intended screener.in query after the session-capture path was abandoned as too fragile. **Cap-agnostic** (all caps by default, optional ceiling toggle) with **ROE · OPM · PE · PEG · mcap** on each card (per same-day user revision). Live-verified (MAPMYINDIA score 84; large-cap/high-debt names correctly dropped). True ROCE + deeper fundamentals deferred to 5.2 (needs a working screener.in session). Full record: [[analyses/PEAD-Scanner-Roadmap]] Phase 5.

## Related Pages
- [[sources/MarketTerminal-UI-Reference]] — the design source this roadmap targets.
- [[sources/PreMarketTool-repo]] — provider of the LLM projection input for Milestone 3.
