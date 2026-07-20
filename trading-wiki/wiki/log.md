# Wiki Log
<!-- Append-only. Newest entries at top. Format: ## [YYYY-MM-DD] operation | description -->

## [2026-07-20] build | Phase 0 consolidation + M1 Overall Rating rollup (Scanner Hub)
- **Phase 0 (git de-risk):** consolidated ~35 untracked files + 4 modified into 9 logical commits on `master`. Extended `.gitignore` to exclude `node_modules/`, the **1.9 GB** vendored `tools/indian-trading-agent-main/`, `.playwright-mcp/`, `secrets.toml`. Verified: all `tools/*.py` byte-compile (Py 3.14.4); every local module `dashboard_app.py` imports now resolves to a committed file (closed the "fresh checkout won't launch" risk). Committed to trunk (solo repo), nothing pushed.
- **M1 (SHIPPED & verified):** added `_overall_rating()` to [dashboard_app.py](tools/dashboard_app.py) — one cross-system /100 score fusing Minervini/8 + TechnoFunda/6 + CANSLIM/computable + EW-confidence/100 (default weights 0.35/0.25/0.20/0.20, tunable + auto-normalised in a new Scanner Hub "Overall Rating weights" expander). Each hit card shows a colour-coded **Overall NN/100** badge with an M/TF/C/EW tooltip; results sort by it, with a **Min Overall Rating** floor slider. Computed once at scan time from the scanner's cached OHLCV.
- **Verified live** (launched the app, drove the Scanner Hub): Stage 2 scan over 15 large-caps → TITAN **76/100**, SUNPHARMA **75/100**, correctly sorted, no server errors.
- Roadmap updated: [[analyses/Dashboard-UI-Roadmap]] Outcome. Next recommended PR: **M2** (on-chart pattern boxes — backend endpoints already live).

## [2026-07-19] analysis | Dashboard roadmap reconciled + expanded (Phase 0–4)
- Updated [[analyses/Dashboard-UI-Roadmap]] with a grounded 2026-07-19 current-state pass: 17 pages across 5 sidebar groups; chart-server detectors (vcp/rounding_bottom/trendlines/harmonic/reversal_events) all exposed.
- Two findings: **M1 (Overall Rating /100 rollup) never shipped** (Setup Intelligence panel shipped instead — per-symbol, not the Scanner Hub rollup); **~35 untracked files, only 5 commits** — tracked `dashboard_app.py` imports untracked modules, so HEAD wouldn't launch → version control is the #1 blocker.
- Added Phase 0 (consolidate/de-risk) ahead of M1–M4, and Phase 2 (Fibonacci overlay + RSI-60-40 scanner from today's ingest; wire orphaned detectors), Phase 3 (backtest harness + alert unification + astro scoping), Phase 4 (surface polish, deferred) behind them.
- Plan: execute (a) file roadmap [done] → (b) Phase 0 git consolidation → (c) M1 rollup.

## [2026-07-19] ingest | Fingrad et al. — Trading Infographics Collection (Obsidian note "Fibonacci the")
- Source: 16-image screenshot dump pasted into `Fibonacci the.md` (vault root). Fingrad watermark on most; Haseeb Badar (@HB_STOCKS) trader-taxonomy; Bulkowski candlestick-accuracy chart. Read all 16 images via vision.
- Summary: [[sources/Fingrad-Trading-Infographics-Collection]]
- Pages created: [[concepts/Fibonacci-Retracement]] (retracement+extension+golden-zone 0.5–0.786 + Fib/RSI confluence — filled the wiki's biggest hub gap: Fibonacci was linked from 23 pages but had no page), [[strategies/RSI-60-40-Setup]] (RSI 40 pullback / RSI 60 breakout on 21/50 EMA stack — the most self-contained system in the set)
- Pages updated: [[concepts/SuperTrend]] (SuperTrend+5/20-EMA and SuperTrend+RSI+ADX confluence setups), [[concepts/EMA]] (50/200 golden-death cross + 5-8-13 ribbon), [[concepts/RSI]] (Fib+RSI + 40–60-band setup links), [[concepts/ADX]] (ADX>25 gate in SuperTrend+RSI+ADX), [[concepts/Bollinger-Bands-Squeeze]] (corroborating source), [[concepts/Candlestick-Patterns]] (Bulkowski top-10 accuracy table), [[index]], [[log]]
- Key insight: **names lie** — Bulkowski's data shows a *bearish* three-line-strike acts as a bullish reversal 84% of the time; trade measured behavior, not the label. Also: the note's Fibonacci theme exposed that our most-cross-referenced concept had no home page.
- Editorial call: the other ~9 images (Bollinger guide, MACD price-action, confirmation checklist, trend-is-your-friend, trader taxonomy) restate existing pages — filed as source/cross-ref links, not new pages, to avoid diluting stronger existing content.

## [2026-07-16] build+file | Setup Intelligence panel in the Stock Analyzer (SwingEdge-style card)
- Trigger: user asked for a SwingEdge "Swing Edge Intelligence"-style card in the analyzer output.
- Filed: [[analyses/Setup-Intelligence-Panel-2026-07-16]] — build record, design rationale, verification table, deferred work.
- Code (not wiki): `tools/stock_council.py` — new `SetupIntel` dataclass + `setup_intelligence()` pure function over the existing evidence bundle; `tools/dashboard_app.py` — new `render_setup_intelligence()` rendered **above** the Council verdict.
- Key insight: **the analytics already existed — only the presentation was missing.** The council's `facts`/`subscores`/`TradeCard` supplied every element of SwingEdge's panel, so this was a zero-new-computation build. Status badge derives from `card.verdict`, making it structurally impossible for the summary to contradict the Judge.
- Verified on 3 synthetic scenarios (uptrend/risk-on → BUY 10 bullish·1 risk; downtrend/risk-off → AVOID 2·12; flat → BUY 10·2). Testing caught real duplication between bear thesis-breakers and risk factors — fixed via `⚠️ Thesis-breaker —` prefix.
- Contradiction found in the reference: SwingEdge's own card lists "MACD below zero — weak trend (−2)" under **BULLISH** factors — a negatively-scored item in the positive column. Reinforces the [[sources/SwingEdge-INDSWFTLAB-20260621]] caution: SwingEdge is a UI reference, not a logic gold standard.
- Deferred (ranked): (1) port `volume_profile.js` → Python to unlock POC/value-area factors (serves whole toolchain, not just this panel); (2) wire `scanner_templates.py` pivot/VCP-compression/pre-breakout factors; (3) revisit hand-set thresholds.
- Also this session: added **🔄 Regenerate** button + **snapshot dropdown** to the Sector Map orbit chart (`tools/dashboard_app.py`) — previously the page force-showed only the newest `sector_rotation_orbit_*.html` with no in-page way to rebuild it.

## [2026-07-16] ingest | Pine Script — Smart Money Concepts [LuxAlgo]
- Source: LuxAlgo SMC indicator (Pine v5, CC BY-NC-SA 4.0) — pasted source code. The canonical/most-forked SMC superset on TradingView.
- Summary: [[sources/LuxAlgo-Smart-Money-Concepts-Pine]]
- Pages created: [[concepts/Order-Blocks]], [[concepts/Equal-Highs-Lows]], [[concepts/Premium-Discount-Zones]], [[entities/LuxAlgo]]
- Pages updated: [[concepts/Market-Structure-CHOCH-BOS]] (internal-vs-swing two-tier model + Strong/Weak High-Low + structure→OB linkage), [[concepts/Fair-Value-Gap]] (MTF + auto-threshold variant + wick-through mitigation contradiction), [[index]], [[log]]
- Key insight: SMC is **nested structure on one chart** — the same swing algo run at 5-bar (internal) and 50-bar (swing) lookbacks; every SMC zone (order block, premium/discount) is *derived from* a BOS/CHoCH break, not drawn independently.
- Contradiction filed: LuxAlgo retires FVGs on any wick-through (clean-chart visualizer) vs the Quant script's close-through survival rule (entry-signal engine) — see both on [[concepts/Fair-Value-Gap]].
- Highest-value TODO: **order-block port** into `tools/scanner_templates.py` — nothing in the repo computes OBs yet.

- Source: Investopedia article 073001 on Lane's Stochastic Oscillator. **WebFetch blocked** — filed from canonical Lane reference; re-ingest when investopedia.com is accessible.
- Filed:
  - [[sources/Investopedia-Stochastic-Oscillator]] — source stub with fetch-blocked flag.
  - [[concepts/Stochastic-Oscillator]] — concept page with formulas, variants (Fast/Slow/Full), Lane's bull/bear setup, common mistakes.
- Wired: added **Stochastic (14,3,3)** as a sub-pane oscillator in [`tools/chart_dashboard.html`](../../tools/chart_dashboard.html) — `stochSeries()` compute helper + render block with cyan %K, dashed orange %D, 80/50/20 guide lines. Follows the same pattern as RSI/MACD/ROC.

## [2026-07-14] ingest | Madhur Raut — Market Sentiment Index Infographic (5-indicator composite)
- Source: Social-media infographic by [[Madhur-Raut]] — 0-100 composite gauge for NIFTY sentiment. Weights: PCR Trend (30) + Advance/Decline (20) + Sector Performance (20) + Hourly Technical Trend (15) + 3-Min Technical Trend (15). Sample reading 14 Jul 2026 = 34/100 SELL.
- Filed:
  - [[sources/Madhur-Raut-Market-Sentiment-Index-Infographic]] — source summary with breakdown table and cross-references.
  - [[concepts/Market-Sentiment-Index]] — concept page with composition, use as regime gate, common mistakes, Trading Bramha variant.
  - [[entities/Madhur-Raut]] — author entity page.
  - [[analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14]] — feasibility + effort estimate + 3-phase roadmap plan.
- Key insight: **Medium-value, low-effort addition** — three of five inputs (A/D, Sector, Technical Trend on NIFTY) are already home data via bhavcopy + `sector_rotation.py` + PMax. PCR is the only new fetch. Recommended v1 substitutes NIFTY-vs-SMA200 + PMax-on-NIFTY-1H for the vague "Technical Trend" rows.

## [2026-07-12] ingest | YT — Kaushik Akkiwakar: True Strength Index (TSI) for Momentum
- Source: YouTube transcript by [[Kaushik-Akkiwakar]] (SEBI RA) covering TSI from first principles — formula (double-smoothed ΔClose over 25 then 13, ×100), 13/7-EMA signal line, 4-quadrant trend×momentum matrix using [[SuperTrend]] (or MAST = MA+SuperTrend) as trend filter, TSI vs [[RSI]] comparison, six worked examples on [[Point-and-Figure-Charts]], zero-line confirmation, and the author's live deployment at [[MarkUp-Platform]] on daily + 5-min timeframes.
- Filed:
  - [[sources/YT-Kaushik-Akkiwakar-TSI-Momentum]] — source summary with 4-quadrant matrix and 6 examples.
  - [[concepts/True-Strength-Index-TSI]] — first-class concept page with formula derivation, RSI contrast table, signal taxonomy, best pairings, common mistakes.
  - [[concepts/SuperTrend]] — first-class concept page (Factor=3, ATR=10) with MAST variant.
  - [[concepts/Point-and-Figure-Charts]] — chart-type page introducing Turtle / Broadening Top / Double Bottom Sell patterns referenced in TSI examples.
  - [[entities/Kaushik-Akkiwakar]] — SEBI RA entity page.
  - [[entities/MarkUp-Platform]] — signals platform entity page.
- **Key insight**: TSI is a *trend-momentum confluence* tool, not a standalone oscillator. Reading TSI crossovers conditional on trend (via SuperTrend) is the entire edge — a bullish trend + negative TSI crossover is a pause/profit-book signal, not a reversal.
- **Local fit / actionable**: TSI slots naturally as a 5th chart pane alongside [[MACD-Divergence]] and [[RSI]] (same "oscillator below price" convention established after `87a49c6` RS Line and `fcb3faa` MACD). Scanner rule "negative TSI crossover in bullish trend" fits the SwingEdge Momentum Buildup family. Check redundancy against [[KST]] before adding both.
- **Contradictions**: none with existing wiki. Author's "95% of traders don't know TSI" is rhetorical; no backtest stats given for the 4-quadrant matrix.
- Index updated (161→167 pages, 68→69 sources).

## [2026-07-08] ingest | Pine v4 — CPR with MAs, Super Trend & VWAP (GuruprasadMeduri)
- Source: MPL-2.0 Pine v4 script bundling CPR + multi-TF floor pivots (D/W/M) + Supertrend + duplicated SMA/EMA/VWAP.
- **Distinctive elements missing from our chart:** (1) **CPR (Central Pivot Range)** — Pivot=(H+L+C)/3, BC=(H+L)/2, TC=2·Pivot−BC — three-line intraday band, Indian-retail staple; (2) **multi-timeframe floor pivots** — D/W/M × S1-3/R1-3 with style-coding (D=solid, W=`+`, M=`o`) for confluence readability; (3) **Supertrend** — HL2 ± Factor×ATR trailing stop with directional flip.
- **Elements duplicated:** SMA(50), EMA(50), session VWAP — all three already in our INDICATOR_DEFS.
- Filed:
  - [[sources/CPR-GuruprasadMeduri-Pine]] — full formula preservation, config surface, style-code cheat-sheet, pre-checked implementation plan.
  - [[concepts/CPR-Central-Pivot-Range]] — first-class concept page with the 3-step read protocol (band width for regime forecast, today-vs-yesterday CPR for structural bias, level-by-level trade zones), MTF confluence rules, common mistakes, VWAP composition ("VWAP inside CPR = chop, outside = directional bias confirmed").
- **CPR ranked as #1 pending indicator** for the chart — the single most-used indicator in Indian intraday retail community; ~4-5h to build end-to-end (server endpoint `/api/pivots` + client PriceLine rendering + INDICATOR_DEFS entry under new "Levels & Pivots" group). Recommend shipping alongside standalone Supertrend since both are on the "game-changer missing" list.
- **Contradiction flagged:** the script's `vwap(close)` differs from our HLC/3-volume-weighted VWAP — cross-check comparisons would need calibration.
- **Follow-ups queued (not created):** `concepts/Floor-Pivots.md` (shared classical S/R formulas), `concepts/Supertrend.md` (once the indicator ships).
- Index updated (159→161 pages, 67→68 sources).

## [2026-07-08] extend + create | Predictive Analysis view target locked in
- **Extended** [[sources/MarketTerminal-UI-Reference]] with a new "Predictive Analysis View" section documenting the META screenshot: AI Prediction toggle, forward-projection dashed line with paired `$693.80 / +9.87%` label, Breakout + Breakdown pattern boxes, click-for-metadata tooltip exposing detector geometry (Consolidation 88 days · Breakout Pivot $581.25 · Breakdown Pivot $744.00 · Depth 21.88%). This is the concrete future build target the user flagged.
- **Created** [[analyses/Dashboard-UI-Roadmap]] — 4-milestone plan sequenced by ROI-and-risk-and-sequencing-rule (don't start N until N-1 shipped):
  - **M1** — Overall Rating /100 rollup in Scanner Hub. 1-2h. Weights first-draft: Minervini 0.35 / TechnoFunda 0.25 / CANSLIM 0.20 / EW 0.20. Color scale ≥85 green, 70-84 amber, 50-69 grey, <50 red. Every downstream milestone compounds on this.
  - **M2** — Pattern boxes on chart (semi-transparent filled rectangles) + click-for-metadata tooltip. 3-4h. `/api/vcp` + `/api/rounding_bottom` + `/api/trendlines` already expose the geometry.
  - **M3** — AI Prediction line + % move on chart, sourced from extending Pree Market Tool prompts. 6-8h. Ships last on purpose — projection is the most seductive and most brittle number; land the honest ratings + patterns first so users don't overtrust the projection alone. Confidence-badge guardrails documented.
  - **M4** (stretch) — consolidated Predictive Analysis tab composing M1+M2+M3 into one Market-Terminal-META-view equivalent. 4-6h pure composition.
- Prerequisites table on the analysis page shows every ingredient already present in the stack — nothing new to build backend-side, it's a wiring exercise. Total budget ~15-20h; M1 alone is 1-2h.
- Index updated (158→159 pages, sources unchanged at 67).

## [2026-07-08] ingest | Market Terminal — UI/UX design reference (competitor screenshot)
- Source: Market Terminal (marketterminal.com), Ex Hours Breakouts + AAPL Chart split-view screenshot. Filed as [[sources/MarketTerminal-UI-Reference]].
- **Design intelligence, not methodology.** Extracted the layout skeleton, the rating system, the chart annotation language, the freemium UX pattern, and the AI-accent color code (purple gradient).
- **The core design idea worth stealing: universal `n/100` composite rating.** Every stock attribute (Future Earnings, Current Strength, Inst. Accumulation, Industry Leadership, Sector Strength) becomes an /100 score; those roll up to a headline "Overall Rating" that the user actually decides on. Directly maps to our Minervini/8 + TechnoFunda/6 + CANSLIM/4 stack — flagged as **highest-ROI dashboard change** (Scanner Hub becomes triageable at a glance).
- **Ranked adoption list (top 7 of a longer list on the source page):** composite Overall Rating rollup · auto-Play through candidate charts · semi-transparent regime overlay for VCP/Rounding Bottom/Trendline pattern boxes · info stack docked left of chart · anchored price labels (rating badge on price series) · value+delta styled pair everywhere · Show Less collapse on info-heavy panels.
- **Not-worth-copying list:** aggressive paywall gating (personal-use tool), emoji-heavy nav (power-user tool), and AI Prediction as a headline chart feature (LLM output belongs in the Pree Market Tool report, not on the price chart).
- **Follow-up flagged (not created):** `analyses/Dashboard-UI-Roadmap.md` — prioritised ticket plan for the top 3–4 ideas.
- Index updated (157→158 pages, 66→67 sources).

## [2026-07-08] create | strategies/Humbled-Trader-Trend-Join-Long (US cash pre-market gapper)
- Extracted the day-trade rule set from [[sources/PreMarketTool-repo]] (`WATCHLIST_CRITERIA.md`) into a first-class strategy page. Filled the wiki's Strategy convention in full: Core Idea / Setup Criteria / Entry Rules / Exit Rules / Timeframe / Best & Worst Conditions / Backtest / Examples / Related / Contradictions.
- **Setup Criteria table** (all six required): gap > 3% · price > $3 · mcap > $1B · pre-market RVOL > 1.5 · price above prior HOD · catalyst identified (else auto-SKIP per the repo's Claude+Codex prompt guardrails).
- **Entry:** trade window opens 10:00 ET (30-min buffer avoids opening chop); trigger = break of PMH **and** prior HOD together (either alone insufficient). Both stop-order and limit-at-PMH entry mechanics supported.
- **Exit ladder:** stop = 1% below PMH or LOD, whichever lower (= 1R); ⅓ off at +1R, ⅓ at +2R, trail last ⅓ on 21-EMA; **hard time-flat at 15:51 ET** — mechanical, not discretionary.
- **Backtest preserved:** 54.6% WR / PF 1.59 / 280 trades (flagged as un-audited — sample period, universe, and slippage not documented in the repo; noted as gap).
- **Cross-links:** [[concepts/VWAP]] as compatible confluence check on entry day, [[concepts/EMA]] for the 21-EMA trail logic, [[strategies/Koroush-Breakout-Momentum]] as the crypto-side analogue (same "reject fast-spike approaches" philosophy).
- **Contradictions flagged**: rules are US large-cap cash equity only — do NOT port the 1% PMH stop, PMH+HOD trigger, or 15:51 ET time-flat to Indian equity swings or crypto without independent re-testing. The "flat by 15:51 ET, no overnight" rule is a *scope* difference (day-trade vs swing), not a real conflict.
- Index updated (156→157 pages, sources unchanged at 66; Strategies table row added under Koroush-Breakout-Momentum).

## [2026-07-08] create | Concept + Analysis pages for astro cross-check follow-through
- Created [[concepts/Out-of-Bounds-Planets]] — first-class concept page. Defines OOB (planet declination > ±23°26′), distinguishes from longitude/latitude, gives per-planet playbook (Mercury=news, Mars=volatility, Venus=consumer/inflation, Moon=monthly recurring), documents amplification stacking (OOB × Rx / × station / × eclipse), lists common mistakes, and points at [[sources/CafeAstrology-Ephemeris]]'s OOB Dates Table as the primary data source plus PyEphem `body.dec` for local computation. Flagged first candidate event-study: Nifty realised vol on OOB-Mars vs non-OOB baseline 2015-2025.
- Created [[analyses/Astro-Engine-Cross-Check]] — three-way triangulation plan for local engine (PyEphem-based). Five diff categories: (1) Rx/D stations ±2 min, (2) Lunations ±2 min, (3) Planet ingresses exact, (4) VoC as *definition identifier* (match local against Astro-Seek's Modern/Traditional/Hellenistic — reveals which our engine implements), (5) OOB transitions day-level (Cafe Astrology-only source; local extension via `body.dec` needed). Scope: July 2026 first pass, extendable to 12 months. Deferred pending user kick-off (~60-90 min).
- Both pages cross-link the two source pages ingested earlier today ([[sources/AstroSeek-iCal-Planner]] and [[sources/CafeAstrology-Ephemeris]]). Index updated (154→156 pages, sources unchanged at 66).

## [2026-07-08] ingest | Cafe Astrology — 2026 Ephemeris (annual tables + PDF)
- Source: https://cafeastrology.com/2026-ephemeris.html — 2026 tropical ephemeris page with monthly Io-Software tables, full-year PDF, and 2005-2030 year archive.
- **Second astro source** — complements [[sources/AstroSeek-iCal-Planner]]. Different consumption model: static tables + PDF vs live subscribable iCal feeds. Same underlying events (longitudes, ingresses, stations, lunations, eclipses, VoC).
- **New concept surfaced: Out of Bounds (OOB)** — planet declination beyond ±23°26′. Cafe Astrology exposes this as a dedicated "Out of Bounds: Dates Table" that Astro-Seek doesn't. OOB Mercury (news windows), OOB Mars (volatility extremes), OOB Venus (consumer/inflation moves) are financial-astrology filters worth capturing.
- **Cross-check plan upgrade:** Three-way triangulation for local astro engine calibration — our engine × Cafe Astrology PDF × Astro-Seek iCal feed. Diff targets: Rx/D stations (should match to the minute), lunations (same), ingresses (should match exactly), VoC (differs by definition — use Astro-Seek's three variants to identify which our engine implements).
- **Historical archive value:** 2005-2030 clean ephemerides + 2012-2027 asteroid ephemerides gives ~20 years of backtesting substrate for reversal-calendar signals vs price.
- Created [[sources/CafeAstrology-Ephemeris.md]]. Updated index (153→154 pages, 65→66 sources) and log. Cross-link added to [[sources/AstroSeek-iCal-Planner]] comparison table.
- **Flagged for future ingest:** `concepts/Out-of-Bounds-Planets.md` (new concept, includes OOB Mercury/Mars/Venus interpretations); extension of the previously-flagged `analyses/Astro-Engine-Cross-Check.md` to include Cafe Astrology as second oracle.
- No contradictions except timezone convention (Cafe Astrology = midnight ET; recommend converting both external sources to UTC before diffing our engine).

## [2026-07-08] ingest | Astro-Seek — Digital Astrology iCal Planner
- Source: https://horoscopes.astro-seek.com/digital-astrology-calendar-planner — free web tool exporting `.ICS` iCalendar feeds importable into iOS/Outlook/Google Calendar.
- **First astro-related source ingested.** Wiki previously had no astro concept/source pages despite our local infra (`tools/astro_trading.py`, `tools/lunar_phases.py`, `tools/yoga_dates.py`, `tools/reversal_calendar.py`, `tools/financial_astrology_methods.py`). Vocabulary established: Modern (10-planet) vs Traditional (7-planet) vs Hellenistic (>30° orb) VoC; sidereal ayanamsa options incl. Lahiri (matches our Vedic yoga logic).
- **Available feed categories** (mundane): Moon aspects+ingresses, Full/New Moons+Eclipses (annual), three VoC variants + Benefic Enclosures, Sun Sign ingresses, Planet Conjunctions/Aspects/Ingresses, Retrograde/Direct planets, and a **Monthly Overall Summary** that consolidates the high-signal set into one feed.
- **Personal feeds** (need natal chart): personal transits (4 variants), Solar Return monthly revolutions, Profections, Zodiacal Releasing L1/L4.
- **Actionable use for our stack** (recorded in [[sources/AstroSeek-iCal-Planner]]):
  - Cross-check target for our internal engine — VoC (three definitions) and retrograde stations are the highest-leverage diffs.
  - Calendar surface: subscribing to the Monthly Overall Summary puts astro-context inside Google Calendar alongside market open times, no dashboard context-switch. Recommended trader subset: Summary + Retrograde/Direct + Full/New/Eclipse (+ optional Modern VoC).
- **Flagged for future ingests** (not created this pass): `concepts/Void-of-Course-Moon.md`, `concepts/Retrograde-Planets.md`, `analyses/Astro-Engine-Cross-Check.md` (one-time month-window diff local vs Astro-Seek to calibrate our VoC/retrograde definitions).
- No contradictions with existing wiki — this establishes the vocabulary.

## [2026-07-08] ingest | Local repo — Pree Market Tool (US + India pre-market scanner)
- Source: `C:\python_project\Pree_Market_Tool\` — Python pre-market scanner + two-AI-brain (Claude + Codex) report generator producing a Humbled-Trader-style HTML report following a fixed template.
- **Pipeline:** `scan.py` (yfinance + RSS + FF econ calendar) → `packet.json` → parallel Claude/Codex passes → `prompt_merge.md` reconciler → `render_report.py` fills `REPORT_TEMPLATE.md` → `deliver.py` writes HTML + delivery note into `reports/`.
- **Region-aware:** `MARKET_REGION=US` (default) or `IN`. IN mode already wired for ^NSEI/^BSESN/^NSEBANK/^INDIAVIX/USDINR=X + ET Markets/Moneycontrol/BQ/BS RSS + IST session times.
- **Validated Humbled Trader rules preserved in [[sources/PreMarketTool-repo]]:**
  - Day (Trend Join Long): gap>3% + price>$3 + mcap>$1B + RVOL>1.5 + break of prior high; trigger break of PMH+HOD, stop 1% below PMH/LOD = 1R, scale ⅓ at +1R/+2R + trail last ⅓ on 21EMA, flat by 15:51 ET. Backtest 54.6% WR / PF 1.59 / 280 trades.
  - Swing: gap≥8% + open>prior-high + open>200SMA + mcap≥$800M + real catalyst. Backtest 57.6% WR / PF 5.34 on news; 44.7% WR / PF 2.57 on earnings.
- **Complementarity with existing OptionTools.in ingest:** Pree Market Tool covers cash-equity gappers + macro (US + India); [[sources/OptionTools-in]] covers NIFTY/BANKNIFTY options positioning tape. Together they form a full pre-market stack.
- **Follow-up flagged (not created this ingest):** `strategies/Humbled-Trader-Trend-Join-Long.md` — extract the day-trade rule set as a first-class strategy page. Also flagged the India-mode universe extension using our existing `screener_pipeline.fetch_bhavcopy_top_volume` (currently only 20 hard-coded mega-caps).
- **Contradictions:** none — different market (US cash pre-market) and different timeframe from the intraday-crypto and daily-Indian-swing strategies already on the wiki.

## [2026-07-08] ingest | OptionTools.in — OI vs Price Trend (NIFTY 07-07 intraday time-series)
- Source: OptionTools.in `/analysis/oi-price-trend` — NIFTY 2026-07-07 full-day chart. Spot + Bullish OI change + Bearish OI change overlaid.
- **Key discovery — two-regime session.** AM was bullish (Bullish OI ramp 0→~14 Cr, spot 24,435→24,520). PM flipped hard: 12:30–13:00 saw Bullish OI collapse ~12 Cr → ~1 Cr in 30 min *before* bears entered. Bearish OI only started climbing 13:00 onwards and accelerated 14:30 into close (~4 Cr).
- **This is long-side capitulation followed by opportunistic bear layering, not a bear-driven sell-off.** Reconciles the earlier EOD ambiguity (PE long unwinding) with the overnight LB ladder (fresh puts entering after close).
- **New actionable levels for tomorrow** (added to [[analyses/Nifty-Options-EOD-20260707]]):
  - **24,520** = the ceiling — any retest without fresh Bullish OI ramp is a rejection.
  - **24,440–24,470** = drift-zone floor — where the intraday bears built their positions; if held from open, bears are trapped and short-cover fuel emerges.
  - **Tomorrow's confirming/invalidating tell:** early Bullish OI ramp before 10:30 IST = ladder defused (range-pin restored); Bearish OI climbing on bounces = continued bear layering (sell rallies).
- No new files created; extended the same-day EOD analysis with a new "Update — OI vs Price Trend" section. `sources: 5`.

## [2026-07-08] ingest | OptionTools.in — OI Spurts Underlyings (aggregated across contracts, 04:54 IST)
- Source: OptionTools.in `/analysis/oi-spurts` (Underlyings view) — F&O names ranked by aggregated OI change across all contracts. Complements the earlier strike-level LB bucket by showing *which underlyings* the OI is stacking on.
- **NIFTY +21,37,463 (+23.11%)** dominates the entire panel — dark green, ~29× the next-largest single-stock OI add. This is the aggregated version of the strike-level put ladder.
- **BANKNIFTY +73,514 (+7.84%)** — second-biggest, confirms the 59,000 PUT LB seen in strike panel.
- **TRENT +61,763 (+86.88%)** on -12.64% price = massive **short buildup on the crash** — dealers/HNIs pressing shorts, not fading. Reinforces the queued [[entities/TRENT]] priority.
- **Cross-panel confluence (short-buildup pattern):** 7 of top-20 losers show heavy OI adds — TRENT, COCHINSHIP, KALYANKJIL, MCX, BSE, ADANIENT, VEDL. Not a buy-the-dip tape.
- **Only two reds** in the top 30: HEROMOTOCO -7,543 (-9.15% OI drop; big long-position unwind on 2W leader — worth watching for auto-2W-cohort decoupling), INFY -3,142 (-0.64%, tiny). Appended full 30-row table to [[analyses/Nifty-Options-EOD-20260707]] with cross-panel read.
- **Three-panel confluence** (LB bucket / Losers heatmap / Underlyings OI) all agree → range-with-downside-tilt confidence **high**.

## [2026-07-08] ingest | OptionTools.in — F&O Losers heatmap (05:05 IST snapshot)
- Source: OptionTools.in `/analysis/gainers-losers` — Losers heatmap, top 20 F&O names.
- Cash-market confluence for the 04:54 OI spurts read: **broad cross-sector weakness, not a single-sector rotation.** Full 20-row table appended to [[analyses/Nifty-Options-EOD-20260707]] with sector-bucket tags.
- **TRENT -12.64%** is a 4× outlier — flagged for a dedicated [[entities/TRENT]] entity page (queued, not created this ingest).
- Cluster reads: cap-goods/defence PSU (6 names), metals (3), realty+exchanges+broker risk-off (5), pharma (2), plus jewellery (KALYANKJIL -6.49%). The cap-goods/defence cluster overlap with 2025-26 winners is the specific tell — this is distribution in the leaders, matching where hedgers are stacking the put ladder.
- **Regime call confirmation:** 04:54 spurts (options-flow) + 05:05 losers (cash-market) = two independent panels, same read. Base case stays range-with-downside-tilt; **confidence raised** on the downgrade from range-pin.

## [2026-07-08] ingest | OptionTools.in — OI Spurts (Long Build bucket, 04:54 IST snapshot)
- Source: OptionTools.in `/analysis/oi-spurts` — LB (OI ↑ + price ↑) buildup bucket, snapshot after EOD 2026-07-07.
- **Contradiction with yesterday's EOD read — flagged as gold.** Yesterday's [[analyses/Nifty-Options-EOD-20260707]] concluded put side was folding (long unwinding + short covering, range-pin base case). This snapshot shows the *opposite*: full NIFTY PUT LB ladder from 24,000 → 24,600 for 14-Jul-2026 expiry — fresh directional put buildup across a contiguous strike ladder, not scattered noise.
- Appended an "Update — 2026-07-08 04:54 IST — OI Spurts Panel" section to [[analyses/Nifty-Options-EOD-20260707]] with the full 14-row table (14 LB entries, 12 of them NIFTY PUTS, +1 BANKNIFTY 59,000 PE LB, +1 KOTAKBANK stock-fut LB, +1 INFY 1,100 CE LB single-stock anomaly). **Base case downgraded from range-bound to range-with-downside-tilt.**
- **Confirming/invalidating tell for next session:** watch whether top NIFTY PUT LB strikes flip to LU (defused) or extend further OTM to 24,700/24,800 (confirmed leg-down). Also cross-check EOD brief for fresh 24,400/24,450 CE short-buildup — that would confirm writers pressing on the way down.
- Index and analysis-row summary updated to flag the intraday regime-shift call.

## [2026-07-07] ingest | OptionTools.in — Nifty Trade Brief (2026-07-07 EOD)
- Source: https://www.optiontools.in/analysis/brief?date=2026-07-07 (Google sign-in gated; content pasted from user's browser session)
- Created [[sources/OptionTools-in]] as a **recurring** source page — describes the tool, cheat-sheet for its SB/SC/LB/LU labels, protocol for filing future daily briefs into `analyses/Nifty-Options-EOD-YYYYMMDD.md`.
- Created [[analyses/Nifty-Options-EOD-20260707]] — first EOD tape read. Headline: **Nifty 24,353.7 (-0.37%) closed at session low, pinned to 24,400 max-pain, PCR 0.98 neutral.** Structural signal is 24,400 CE writer wall (highest OI 3.79 Cr + biggest OI add +2.58 Cr since open, short buildup); counter-signal is put-side long-unwinding + ITM PE short-covering (-4.68 Cr on 24,450 PE in last 30 min) → base case is range-bound expiry pin, not a directional break.
- Full raw snapshot preserved in the analysis page for future re-read (session range, path Up→Down→Down, all top-OI/ΔOI/volume tables, ATM signals, aggregate outer-OTM CE OI +7.00 Cr).
- No entities/NIFTY page created yet — flagged in [[sources/OptionTools-in]] as the natural next step once enough daily briefs accumulate a persistent level book.
- No contradictions with existing wiki (first options-flow source; establishes terminology).

## [2026-07-06] ingest | X article — Koroush AK: My Breakout Trading Strategy
- Source: https://x.com/KoroushAK/status/2016502313230504233 (X long-form article, posted 2026-01-28)
- Created [[strategies/Koroush-Breakout-Momentum]] — full-executable strategy page with entry (2-candle close on 1m + limit AT prior resistance), stop (swing low with 1% floor), and target (1R baseline). First intraday-crypto strategy on this wiki that specifies a numeric stop-distance floor.
- **New taxonomy concept:** every trade is either momentum (bet the level breaks) or mean reversion (bet it holds). Same chart, opposite trades — edge is environment matching, not strategy selection. This framing is now cross-linked from [[concepts/VWAP]] (whose decision matrix uses the same taxonomy) and worth propagating to [[strategies/TechnoFunda-Swing]] and the Scanner Hub scanners.
- **3-filter environment checklist** (approach shape / volume slope / SMMA-30 crossover count) is a candidate gate for the dashboard's breakout screeners — currently they emit candidates on structural pattern alone.
- **SMMA-30** noted as a new indicator variant — flagged for a future addition on [[concepts/EMA]] rather than a new page (not enough differentiation to warrant its own).
- Cross-reference: the SMMA-30 crossover-count filter is thematically identical to the VWAP-slope/crossover-count read from the earlier ingest today ([[sources/X-KoroushAK-VWAP-Masterclass-20260506]]). Confluence signal — both articles reject choppy tape via crossover frequency.
- Scope guard flagged: strategy is designed for **crypto 1-minute**; do NOT port the 1m/1R execution to Indian-equity swing strategies without independent testing.
- Source page: [[sources/X-KoroushAK-Breakout-Strategy-20260128]]

## [2026-07-06] ingest | X article — Koroush AK: VWAP Masterclass
- Source: https://x.com/KoroushAK/status/2052011140410925333 (X long-form article, posted 2026-05-06)
- Created [[concepts/VWAP]] (new) — first dedicated VWAP concept page in the wiki; previously only [[concepts/Anchored-VWAP-Pyramiding]] existed. Concept page codifies the **3-signal read** (position / slope / bandwidth) and a **decision matrix**: steep-slope + widening bands → momentum/continuation; flat slope + tight bands → reversal/mean-reversion; flat slope + multiple price↔VWAP crossovers → fakeout guard (override apparent breakouts).
- Author's TradingView defaults captured — Session anchor, ±1 SD bands. This is the "level 3" filter in his roadmap: a regime classifier, not a signal generator.
- Cross-link opportunity flagged on [[strategies/TechnoFunda-Swing]]: the strategy uses `close > VWAP` as a binary gate; per the new concept page, that gate could be tightened by also requiring non-flat slope on entry day.
- Cross-link confirmed on [[strategies/Hyperliquid-Momentum-Screener]]: its EMA9/21/50+VWAP trend stack is consistent with the position-signal half of Koroush's read.
- No contradictions with existing wiki. Session-anchored (this source) and event-anchored ([[concepts/Anchored-VWAP-Pyramiding]]) VWAPs are complementary — intraday vs swing.
- Source page: [[sources/X-KoroushAK-VWAP-Masterclass-20260506]]

## [2026-07-06] ingest | TradingView — VCP Scanner (Minervini Method) by valchak
- Source: `raw/TV-VCP-Scanner-Minervini-valchak-2026-07-06.md` (URL: https://www.tradingview.com/script/XKX8RJNc-VCP-Scanner-Minervini-Method/)
- **6-gate signal engine** extracted — Trend Template ∧ VCP Valid ∧ VDU ∧ BreakingOut ∧ VolumeSurge ∧ **NotExtended** (anti-chase, ≤ 12% above pivot). NotExtended as a discrete rejection code is new to this wiki — our VCPBot handles chase-avoidance loosely via the gap-check-at-open.
- **Numeric commitments on Minervini's Trend Template**: 200-day slope positive = ≥ 22 trading days; price ≥ **30%** above 52-week low (script tightens the book's 25% — flagged as contradiction on [[sources/TV-VCP-Scanner-Minervini-valchak]]); pivot confirmation 3 bars L/R before pivot is drawn.
- **Contraction numeric ranges** — first pullback 10–35%, final 3–10%, tightening ratio ≤ 0.9× (practical) or ≤ 0.5× (textbook-strict). More permissive than our [[analyses/VCPBot-Architecture]] micro-pivot (final ≤ 8%), tighter than raw book. Filed as second reference implementation.
- **Two-preset pattern** ("Practical Defaults" for US mega-cap growth vs "Textbook-Strict") worth cloning to our Scanner Hub `scan_vcp()` as a strict/lenient switch — one for archival "does this still work" backtests, one for "am I missing the current cohort" scans.
- **RS Rating proxy formula** — 40% recent quarter + 20% each of quarters 2-4 (weighted 12mo excess return vs SP:SPX). Cheap IBD-mirroring proxy; worth adding as a second RS column alongside our Mansfield-RS-style calc.
- **Access limitation**: script is invite-only → cannot pull exact Pine source. Have criteria and defaults from the published description; exact tightening-ratio calc and pivot logic remain black-boxed until we get access.
- Contradictions filed: (1) 25% vs 30% above 52w low — book vs valchak; book is source-of-truth, valchak is a tightening. (2) Pivot confirmation lag — 3-bar L/R vs immediate breakout entry; resolved as "scanner design ≠ signal timing".
- Pages created: sources/TV-VCP-Scanner-Minervini-valchak.md (wiki now 145 pages, 60 sources)
- Pages updated: concepts/VCP.md (added valchak preset table + divergences from book), strategies/Minervini-SEPA.md (added "Public Pine Implementation" section + source), index.md

## [2026-07-03] ingest | SwingEdge — Rounding Bottom Scanner (saucer bases) — completes scanner-family coverage
- Trigger: Kalyan asked to ingest https://www.swingedge.info/rounding-bottom — the last un-ingested SwingEdge scanner family. Captured via Playwright; scan data 2026-07-02 20:48 IST.
- **Methodology extracted**: saucer mapped mechanically ("swing lows and linear slope stats, not curve fitting") — trough from confirmed swing lows with minimum width; 12–40% decline band; linear-fit quality required on both legs; time symmetry scored (extreme asymmetry = V-bottom, fails); EMA-21 slope flat at trough → turning up on the right = the falling-knife filter; rim breakout lifecycle (Approaching/Confirmed on 50-DMA volume/Retest) with score floors 70/65; two families scored separately — Classic Reversal (below falling 200-DMA) vs Constructive Base (near/above rising 200-DMA).
- **Terminology quirk flagged**: concepts panel cites 30–90 bar trough windows while live cards show 6–13d troughs — "trough duration" counts only the flat bottom, the 30–90 bars is the full pattern window.
- **Adopted**: `scan_rounding_bottom()` added to the Scanner Hub in `tools/scanner_templates.py` (all gates above; V-bottom control with symmetry 0.16 correctly rejected, textbook saucer scores 79.2 "Approaching rim · EMA turn"). Scanner Hub now covers every SwingEdge pattern family: Darvas, VCP, structural, saucer, HTF, plus our own Early Reversal composite.
- **Confluence idea noted, not built**: names passing both the saucer geometry and the Early Reversal drop-recovery composite are stronger candidates than either list alone.
- Live cards: GROWW / TITAN / MMFL — all Constructive Base, Approaching rim, EMA turn (no confirmed clears visible).
- Pages created: sources/SwingEdge-Rounding-Bottom-Screener-20260703.md, concepts/Rounding-Bottom.md (wiki now 144 pages, 59 sources)
- Pages updated: index.md

## [2026-07-03] ingest | SwingEdge — Structural Breakout Scanner (flat bases & neckline reversals)
- Trigger: Kalyan asked to ingest https://www.swingedge.info/structural-breakout (one of the two scanner families flagged as missing analogs in the Momentum Buildup ingest). Captured via Playwright; scan data 2026-07-02 20:48 IST — note boards don't refresh together (Momentum Buildup was 07-03).
- **Methodology extracted**: multi-week (20–120 bar) horizontal resistance; cluster = daily highs within ~1.5% (more touches = stronger; live cards 9–19 touches); ATR(14)-scaled break buffer for price-independent confirmation; Approaching → Confirmed → Retest lifecycle with an explicit anti-chase cap (extended clears scored down); weekly-confirm bonus; per-state score floors — 72 for confirmed/retest vs 65 for approaching (a claim of a done breakout must clear a higher bar than a forming setup — carry into the Confirm-Before-Entry doctrine).
- **Adopted**: `scan_structural_breakout()` added to the Scanner Hub in `tools/scanner_templates.py` — cluster/touches, base-compression ratio, flat-base vs neckline-reversal classification from the pre-base trend, three states, breakout-volume check vs 50-DMA, weekly confirm, and the page's score floors. Verified: synthetic +60% run-up → 11w tested base → buffered breakout on 3× volume scores 86 "Confirmed break · Weekly ✓"; trimming the breakout bars correctly degrades to "Approaching".
- **Two more watch-note loops closed** (3 today with IOLCP): entities/AUBANK.md (06-14 descending-channel candidate → Confirmed Neckline Reversal, 19 touches, Weekly ✓) and entities/AADHARHFC.md (06-21 grade-C skip-flag → Confirmed Neckline Reversal, 9w base, Weekly ✓ — the distribution-day caution resolved as early-base noise, not thesis failure).
- Remaining un-ingested SwingEdge scanner family: Rounding Bottom (/rounding-bottom).
- Pages created: sources/SwingEdge-Structural-Breakout-Screener-20260703.md (wiki now 142 pages, 58 sources)
- Pages updated: entities/AUBANK.md, entities/AADHARHFC.md, index.md

## [2026-07-03] ingest | SwingEdge — Momentum Buildup Screener (HTF / Active Breakout / Fresh Turnaround)
- Trigger: Kalyan asked to ingest https://www.swingedge.info/momentum-buildup. Captured via Playwright; scan data 2026-07-03 20:47 IST.
- **Methodology extracted**: three "first clear" tags — High Tight Flag (90–120% pole in 4–8wk, 10–25% flag on contracting volume), Active Breakout (first clear of 5–15wk base on 1.5×+ volume — Stage 2 launch), Fresh Turnaround Breakout (early reversal clear ≈ our Early Reversal Detector, no port needed). Hard volume gate vs 50-DMA on every tagged row. Two-axis card verdicts: status (At trigger / Watch, with the blocking reason named) × quality (A/B) — adopt when building Confirm-Before-Entry card verdicts.
- **Adopted**: `scan_high_tight_flag()` added to the Scanner Hub in `tools/scanner_templates.py` (≥90% pole ≤40 bars, 5–25 bar flag ≤25% deep, flag volume < pole volume mandatory — rising-volume flag rejected as distribution; scores for pole strength/tightness/dry-up/pivot proximity). Verified: synthetic 104% pole + 13% flag on 45% volume scores 71.8; rising-volume variant correctly rejected.
- **IOLCP follow-through**: flagged "breakout soon on volume buildup" 2026-06-14 (FinanceWithSunil) → prints today as Active Breakout / Stage 2 / RS 100 / Quality B / Watch (extended past pivot — pullback entry preferred, not a chase). Entity page updated; first wiki watch-note → scan-confirmation loop closed.
- **Inconsistency flagged**: focus #1 ATHERENERG carries score 100 at Vol 0.8× despite the page's own "low-volume clears are scored down" rule — reinforces the EPIGRAL lesson: trust fields, not prose/rankings.
- Pages created: sources/SwingEdge-Momentum-Buildup-Screener-20260703.md, concepts/High-Tight-Flag.md (first dedicated HTF page; wiki now 141 pages, 57 sources)
- Pages updated: entities/IOLCP.md (bias stays watching — extended), index.md

## [2026-07-03] ingest | SwingEdge — EPIGRAL stock detail page (Downside Risk scan)
- Trigger: Kalyan asked to ingest https://www.swingedge.info/stocks/EPIGRAL. Site 403s plain fetches — captured via Playwright browser; scan data dated 2026-07-03.
- **First bearish-scan SwingEdge page in the wiki** (priors were Base Formation / Momentum Continuation / skip-flag): Stage 4 breakdown, −51.7% from 52w high, RS ~23–35, RSI 32, 5 distribution days, failure risk 78/100, SEI grade F "No Edge", phase DISTRIBUTE, setup window 0/20.
- **Two live validations of today's own work**: (1) price ₹1,021.6 sits below the entire value area (VAL ₹1,030.87 / POC ₹1,225.69 / VAH ₹1,312.84) — exactly the below-VAL warning the new `compute_volume_profile_levels()` check raises; filed as the Volume-Profile page's first live example. (2) SwingEdge ships "Reasons to skip — disqualifiers that apply even if the score looks good" — an independent product implementing the veto tier from today's Confirm-Before-Entry doctrine discussion.
- **Other keepers**: failed-VCP anatomy (16w base 42.4% deep, contraction ladder 13.1%→28.8%→69%→28.8% — expanding, not tightening); RS-laggard-in-healthy-sector as the inverse of the KDDL "RS leader in lagging sector" pattern; price below institutions' avg cost (₹1,063) = every rally is supply.
- **Trust fields, not sentences**: page's generated prose contradicts its own data repeatedly ("Bullish factors: price below 150DMA"; "strong technical characteristics" on a grade-F chart; invalidation level quoted 23% above current price; "contender at 91" vs grade F). Flagged on the source page.
- Pages created: sources/SwingEdge-EPIGRAL-20260703.md, entities/EPIGRAL.md (bias: bearish; wiki now 139 pages, 56 sources)
- Pages updated: concepts/Volume-Profile.md (first live example), index.md

## [2026-07-03] query | How to build an actionable "Confirm Before Entry" philosophy (from infographic example)
- Kalyan shared a generic 5-indicator confirmation infographic (Volume/VWAP/RSI/EMA/ADX) and asked how to build an actionable philosophy like it.
- Answer given: upgrade the flat checklist into a tiered doctrine — Regime gate → Structure confirmations → Trigger → hard Vetoes — where every line maps to an already-computed check (the 9-check validation layer + Nifty 200-DMA regime), and every outcome maps to a position-size action using the sizing rules already in analyses/Kalyan-Trading-Philosophy.md (pilot buy, exponential sizing on A+, Varmer half-size regime filter). Offered to file as a doctrine page + surface the verdict on scanner cards.

## [2026-07-03] ingest | Pine Script — Multi Timeframe Volume Profiles [TradingIQ] (KioseffTrading)
- Trigger: Kalyan pasted the Pine v6 source — fourth item in today's ingest-and-adopt series for the Early Reversal validation layer.
- **What's genuinely new**: up to 5 simultaneous HTF volume profiles (30m→1W) built from *lower-timeframe* volume (`request.security_lower_tf`), the on-chart embodiment of MTF value confluence; a Delta model signing volume by tick rule with a graceful upgrade to real bid/ask matching on tick charts; POC + 70% VA per profile with a live "where is price vs value per timeframe" dot.
- **Two methodological weaknesses flagged (contradictions with our own module)**: even-split volume allocation per row (vs `volume_profile.js`'s proportional range overlap) and alternating VA expansion (vs the standard volume-greedy rule) — both can distort the profile/VAH/VAL. The wiki's existing methods are better; the Pine's value is MTF stacking + delta + LTF sourcing.
- **Adopted with the better math**: `compute_volume_profile_levels()` in `tools/scanner_templates.py` — POC/VAH/VAL + per-bin delta, proportional allocation, greedy VA expansion (deviations documented in the docstring). Wired as the 9th validation check ("Profile"): close accepted above POC passes (noting above-entire-VA and buy-side delta at the node when true); close below VAL raises ⚠ "no volume acceptance of the recovery yet". Verified: recovery scenario passes above POC (78.85, above whole VA, positive delta), heavy-base-then-slide scenario correctly warns below VAL.
- Pages created: sources/MTF-Volume-Profiles-TradingIQ-Pine.md, concepts/Volume-Profile.md (first dedicated volume-profile page; wiki now 137 pages, 55 sources)
- Pages updated: concepts/Multi-Timeframe-Analysis.md (volume-structure application cross-link), index.md

## [2026-07-03] ingest | Pine Script — BOS & FVG Pullback Signals (Quant)
- Trigger: Kalyan pasted the Pine v6 source for ingest — third item in today's ingest-and-adopt series for the Early Reversal validation layer.
- **Contradiction flagged first**: the title claims BOS but the code contains zero market-structure logic — it's a pure FVG detector + pullback-rejection entry signal. Filed under FVG accordingly.
- **What's worth keeping**: quality-filtered FVG definition (directional middle candle + gap > 0.5×ATR(14) — auto-adapts to volatility, unlike `fvg.js`'s optional fixed-% filter); newest-unmitigated-zone-per-side tracking; full-close-through-only invalidation (partial fill = the entry, not the kill); 3-condition pullback rejection — touch inside zone + close back above with dominant lower wick + *opened* above the zone (anti-gap-down trap, same trapped-trader spirit as yesterday's body-close trendline rule).
- **Quirk found while testing the port**: the zone top is candle 3's own low, so touch is trivially true on the formation bar — a hammer-shaped candle 3 fires BUY and consumes its zone with no pullback ever happening. Documented on the source page; port reproduces it faithfully.
- **Adopted**: `detect_fvg_pullback()` in `tools/scanner_templates.py`, wired as the 8th validation check ("FVG") — recent bullish FVG rejection passes, recent bearish rejection raises a ⚠ warning. Verified on hand-built bars (signal fired exactly on the pullback bar) alongside the full regression of the other 7 checks.
- Pages created: sources/BOS-FVG-Pullback-Signals-Pine.md, concepts/Fair-Value-Gap.md (first dedicated FVG page; wiki now 135 pages, 54 sources)
- Pages updated: concepts/Market-Structure-CHOCH-BOS.md (FVG mention now links to the new page), index.md

## [2026-07-03] ingest | Pine Script — Trend Lines by Kris (KRISTRADER1)
- Trigger: Kalyan pasted the Pine v6 source for ingest, following the validation-layer build earlier today (the "will provide Pine logic to ingest and adopt" path from that request).
- **Core mechanics worth keeping**: fully mechanical trendlines from confirmed pivots (supply = falling pivot highs, demand = rising pivot lows, ≤7×prd bars apart); clean-line validation (rejected if any close already crossed it); normalized angle filter ≤30° (slope mapped onto a 500-bar 3:1-aspect box → scale-independent steepness cap); break requires the candle *body* to close beyond the line — wick pierces don't count, which independently converges on the False-Break-Buildup-Trading wick-vs-body false-break rule.
- **Adopted, not just filed**: ported as `detect_trendline_break()` in `tools/scanner_templates.py` and wired as the 7th validation check ("Trendline") — recent supply-line break passes (bullish: downtrend's supply structure objectively ended, the diagonal cousin of a CHOCH), recent demand-line break raises a ⚠ warning on Early Reversal cards. High-Growth Screener Validations column picks it up automatically (TL✓/✗).
- Verified on a synthetic staircase-decline → breakout: correctly *rejected* a steep staircase via the angle filter (working as designed), detected the break on gentle geometry (20.5° line, break 6 bars ago → 6/7 validations).
- Pages created: sources/Trend-Lines-by-Kris-Pine.md, concepts/Trend-Lines.md (first dedicated trendline concept page; wiki now 133 pages, 53 sources)
- Pages updated: concepts/Market-Structure-CHOCH-BOS.md (cross-link: diagonal supply-line break vs horizontal swing break), index.md

## [2026-07-03] build | Six-check validation layer for the Early Reversal Detector + High-Growth Screener
- Trigger: Kalyan asked for six additional validation measures on every Early Reversal scanner card and in the screener logic (alongside the existing %R Trend Exhaustion), sourced from the vault where Python-equivalent logic exists.
- Vault coverage check: 4 of 6 validators ported directly from existing wiki pages — concepts/Market-Structure-CHOCH-BOS.md (structure), concepts/Multi-Timeframe-Analysis.md (weekly-regime alignment), strategies/False-Break-Buildup-Trading.md (fakeout/retest), strategies/TPT-Thrust-Pullback-Thrust.md (pullback-after-breakout). Volume confirmation (breakout-volume rule + up/down volume ratio, per Stage-Analysis/Minervini) and the ATR volatility band are textbook — no Pine ingest needed.
- Implemented in `tools/scanner_templates.py`: `detect_bos_choch` (SMC swing-labeling walk; bearish break invalidates a prior bullish event), `detect_volume_confirmation` (≥1.5× RVOL up-day or 10-day up/down volume ratio ≥1.2), `compute_atr_filter` (ATR% in 1–8% band + contraction flag), `detect_mtf_alignment` (weekly resample: 10-wk EMA / weekly RSI ≥45 / weekly higher low, pass = 2 of 3), `detect_pullback_entry` (breakout → pullback held → turning up), `detect_fakeout` (false break vs confirmed retest), plus `compute_validation_summary` combining all six.
- Wiring: Early Reversal cards now show a "✔ n/6 validations" tag, per-check reasons, and an orange ⚠ fakeout warning (score impact deliberately modest: +2/check, −8 on fakeout — validations confirm a candidate, they can't create one). High-Growth Screener gained a compact "Validations" column (`5/6 · Str✓ Vol✓ ATR✓ MTF✓ PB✓ RT✗`) next to the Exhaustion column.
- Verified with a synthetic decline→base→breakout→pullback scenario (5/6 checks fired correctly) plus edge cases (short history, missing volume, flat prices, non-datetime index all degrade gracefully).

## [2026-07-03] ingest | BSE + NSE — block deal, bulk deal, insider trading data sources
- Trigger: Kalyan asked how to get block deal / insider trading data from bseindia.com and nseindia.com, directly following the prior bseindia.com API ingest.
- **BSE: all 3 confirmed live, whole-market, no auth** — `BulkDeal_Beta/w` and `BlockDeal_Beta/w` (today's deals, zero parameters needed) and `InsiderTrade15/w?fromdt=&todt=&scripcode=` (SEBI PIT disclosures, whole-market when scripcode is blank) — all verified with real data (e.g. ICICI Prudential Mutual Fund's actual bulk buy in AWL).
- **NSE: confirmed the existing `nse_shareholding_fetch.py` warning still holds** — even the plain homepage 403's from this sandbox's IP (Akamai block). But found a working alternative: NSE's static archive subdomain (`archives.nseindia.com` — the same one `screener_pipeline.py`'s bhavcopy fetcher already uses) is **not** behind that protection. `archives.nseindia.com/content/equities/bulk.csv` and `.../block.csv` both work today, plain CSV, whole market, zero auth — found by pattern-matching the existing bhavcopy URL convention. `fo_secban.csv` also confirmed to exist opportunistically.
- **NSE insider trading not resolved** — guessed static-archive paths (sast.csv, insider_trading.csv, pit.csv) all 404'd; likely only available via the blocked interactive API, needs testing from a real (non-sandboxed) IP.
- **New use case surfaced, not built**: cross-referencing a stock already flagged by the Early Reversal Detector (or any other scanner) against same-week institutional bulk-deal buying or insider acquisitions would be a materially stronger "smart money confirmation" signal than either alone — natural next scanner-composite candidate.
- Pages created: sources/BSE-NSE-BlockDeal-InsiderTrading-APIs-2026.md (wiki now 131 pages, 52 sources)
- Pages updated: sources/BSEIndia-Public-API-Corporate-Data-2026.md (follow-up cross-link), concepts/Order-Flow.md (cross-link — bulk/block/insider feeds as a coarser institutional-footprint proxy)

## [2026-07-02] ingest | bseindia.com — reverse-engineered public API for announcements/actions/shareholding pattern
- Trigger: Kalyan asked to ingest bseindia.com; since a live JS-rendered portal isn't a single readable document, clarified scope first — landed on corporate announcements/actions data (mirroring what `tools/nse_shareholding_fetch.py` already does for NSE).
- **Found 3 genuine, working, unauthenticated public JSON API endpoints** on `api.bseindia.com/BseIndiaAPI/api/` by reading BSE's own minified frontend JS bundle for internal path names, then testing directly with curl (same technique used for screener.in's `/api/ratio/search/` and `/screen/raw/` earlier this session) — all verified live against Reliance Industries (scripcode 500325):
  - `AnnSubCategoryGetData/w` — corporate announcements, filterable by scrip/date
  - `CorporateAction/w` — dividend + bonus history, verified against Reliance's actual known history
  - `CorporatesSHPSecuritybeta/w` — full shareholding pattern **including a real `Fld_PledgeEncumberedPercentage` numeric field**
- **This closes a real gap from earlier today**: building the Pre-Breakout Screener's pledge filter, screener.in was confirmed to have no analyst-surprise field and its `Pledged percentage` field needed an authenticated query. BSE's shareholding-pattern endpoint gives the same figure for free, no login, straight from the regulatory filing itself — no cookie/session needed at all (just an `Origin`/`Referer` header), simpler than the screener.in flow.
- **Not yet solved**: NSE-symbol → BSE-scripcode mapping (a `ListScripSmartSearch_ng/w` endpoint exists but the first parameter guess didn't return data) — needed before this can actually plug into the existing NSE-symbol-keyed pipeline.
- **New use case surfaced, not built**: `CorporateAction/w` could let the Drop-Recovery-Reversal-Screen / Early Reversal Detector distinguish a real price decline from an ex-dividend gap — currently neither has any such adjustment.
- Pages created: sources/BSEIndia-Public-API-Corporate-Data-2026.md (wiki now 130 pages, 51 sources)
- Pages updated: strategies/Drop-Recovery-Reversal-Screen.md (cross-link to the ex-dividend-gap use case)

## [2026-07-02] ingest | GitHub repo — Shubhamsaboo/awesome-llm-apps
- Trigger: Kalyan pasted the repo URL directly, no other context.
- 116k★, Apache-2.0, 100+ AI-agent tutorial templates across 15 categories (Starter/Advanced Agents, Multi-agent Teams, Always-on Agents, RAG Tutorials, Agent Skills, MCP integrations) by the creator of the Agno/Phidata framework.
- **Checked the flagship finance example directly instead of trusting the category label**: "AI Finance Agent Team" is its own README's words "a team of AI agents... using GPT-4o in just 20 lines of Python code" — a framework-orchestration demo (Web Agent + Finance Agent + Team coordinator, yfinance + DuckDuckGo, SQLite for history). No documented methodology, no buy/sell logic, no backtesting.
- **Materially shallower than the 3 trading-agent repos already in this wiki** ([[sources/GitHub-claude-trading-skills-tradermonty]], [[sources/GitHub-ai-trading-claude-zubair]], [[sources/GitHub-TradingAgents-TauricResearch]]) — all three have actual documented methodology; this repo's finance folder reads as similarly shallow framework demos, not independently verified beyond the one checked.
- Not recommended as a trading-methodology source. The only potentially reusable part is architectural (Multi-agent Teams / Always-on Agents patterns for this project's own automation) — not confirmed to add anything beyond [[concepts/Agent-Loop-Design]] already covers, would need a dedicated follow-up look rather than assumed value from the category name.
- Pages created: sources/GitHub-awesome-llm-apps-Shubhamsaboo-2026.md (wiki now 129 pages, 50 sources)
- Pages updated: none — nothing strong enough here to act on yet

## [2026-07-02] ingest | GitHub repo — Panniantong/Agent-Reach (multi-platform content fetcher for AI agents)
- Trigger: Kalyan pasted the repo URL directly, no other context.
- 15+ platform backends (Web/Jina, YouTube/yt-dlp, RSS, semantic search/Exa, GitHub/gh, Twitter, Bilibili, Reddit, Facebook, Instagram, Xiaohongshu, LinkedIn, V2EX, Xueqiu, Xiaoyuzhou podcast), 49k★, MIT, one-command agent-driven install with automatic per-platform backend fallback.
- **Two backends fix real, already-hit gaps, not hypothetical ones**: (1) `yt-dlp` for YouTube directly targets the exact pain point logged on 2026-06-29 (YT-Breakout-Screener ingest needed a manually-pasted transcript after YouTube's signed `timedtext` URL returned an empty body for non-browser requests); (2) `gh` CLI setup fixes a gap hit earlier this very session — `gh repo view` failed in both Bash and PowerShell during the kepano/obsidian-skills ingest, forcing a WebFetch fallback.
- **Most of the platform suite doesn't apply here**: origin skews Chinese-language/social (install instructions given in Chinese; Bilibili/Xiaohongshu/V2EX/Xiaoyuzhou are Chinese platforms). Xueqiu is the one finance-flavored channel but is a Chinese stock forum, not Indian-market relevant.
- Recommendation: install `yt-dlp` and `gh` directly as standalone CLIs rather than adopting the full Agent-Reach wrapper, unless the auto-fallback routing/SKILL.md auto-invocation is itself wanted — consistent with the "cherry-pick, don't adopt wholesale" pattern already applied to kepano/obsidian-skills (`defuddle` only) and AgriciDaniel/claude-obsidian (`hot.md` only).
- Pages created: sources/GitHub-Panniantong-Agent-Reach-2026.md (wiki now 128 pages, 49 sources)
- Pages updated: concepts/Claude-Code-Skills.md (cross-link + actionable-insights note)

## [2026-07-02] build | Early Reversal Detector (Scanner Hub)
- Implements the detector proposed across the 4 reversal-signal ingests earlier today. Lives in `tools/scanner_templates.py`, registered in `SCANNERS` as "Early Reversal Detector" (category Entry) — reuses all of Scanner Hub's existing universe-selection UI and the warm-themed result cards.
- **Composite of all 4 signals**: `compute_drop_recovery_signal()` (gate — must show a real decline + partial reclaim, fixes the Upside-Reversal-Screener's likely highBeforeLow bug by using a genuine N-day rolling high) → `compute_recent_exhaustion_signal()` (reused as-is from the Pre-Breakout/High-Growth screeners) → `detect_bullish_candlestick()` (new: Bullish Engulfing/Hammer/Bullish Harami/Piercing Line/Morning Star, geometry-scored per the Forthius ingest) + `detect_bullish_rsi_divergence()` (new, cheap) → `detect_bullish_reversal_structure()` (new: simplified Double Bottom/Inverse H&S, pivot-based per the AGPro ingest). Combined into `compute_early_reversal_signal()`, 0-100 score, ≥35 to surface as a card.
- **Applied the Forthius design lesson directly**: no leg of this requires a strict prior downtrend — the drop-recovery gate alone establishes "a real decline happened," so the detector doesn't go quiet during the ranging Stage 4→1→2 transition window the way Forthius's own default config does.
- **Tested against live data before trusting it**: ran all 4 sub-functions + the composite against 9 real NSE symbols via yfinance directly (bypassing Streamlit) — zero exceptions, plausible drop/recovery percentages, Double Bottom quality scores 6.7-9.0 on 3 genuine candidates (Goodyear India, HDFCBank, SBIN). Caught and fixed a calibration issue this way: the initial ≥40 threshold made it nearly impossible for a single non-exhaustion signal to qualify alone (SBIN's genuinely strong 9.0/10 Double Bottom scored 38.5, just under the bar) — lowered to ≥35. Confirmed the fix in the actual dashboard UI afterward (Scanner Hub → Early Reversal Detector → SBIN/HDFCBANK both surfaced correctly).
- Not built: TradingView-native screener-column distribution (would need checking Kalyan's plan tier) and the full Forthius/AGPro pattern catalogs (scoped down to the 5 most common candlestick patterns and 2 of the 4 chart-pattern types, per the "reuse the idea, not the whole script" principle already applied throughout this thread).

## [2026-07-02] ingest | Pine Script — Upside Reversal Screener
- Trigger: Kalyan pasted the full Pine v6 source directly — 4th reversal-detection script this session, and by far the simplest: no candlestick shapes, no chart patterns, no oscillator, just drop % (or ATR-multiple) from a recent high then recovery % of that drop reclaimed. New [[strategies/Drop-Recovery-Reversal-Screen]] strategy page, cross-linked as the mirror image of the existing [[strategies/Parabolic-Short-First-Red-Day]].
- **New distribution mechanism, not just new logic**: unlike the other 3 scripts (visual chart overlays), this one's `isScreenerMode` output is raw numeric columns (Open/High/Low/Close/Change%/Drop%/Recovery%/Reversed) meant for TradingView's own native Stock Screener, filterable whole-market with no external plumbing (Chartink/screener.in/Python) at all — though custom-script screener columns are typically a paid TradingView tier, not confirmed available on Kalyan's plan. Flagged as worth checking directly before assuming a Python port is needed.
- **Flagged a likely implementation issue, not silently trusted**: the `highBeforeLow` lookback loop only accumulates while consecutive bars share the same calendar day (daily)/week (weekly) — a condition that appears to break immediately at the first iteration on *both* timeframes the script is restricted to (`runtime.error` blocks intraday). If correct, `highBeforeLow` collapses to just `max(prior close, today's open)` rather than a meaningful recent swing high — reads like leftover logic from an intraday-session-aggregation version. Documented as a static-reading concern requiring live verification, not a confirmed bug.
- Proposed role: the cheapest possible pre-filter for the Early Reversal Detector — pure OHLCV magnitude check ahead of the more expensive candlestick/chart-pattern/oscillator signals, not a replacement for them.
- Pages created: sources/Upside-Reversal-Screener-Pine.md, strategies/Drop-Recovery-Reversal-Screen.md (wiki now 127 pages, 48 sources)
- Pages updated: strategies/Parabolic-Short-First-Red-Day.md (cross-link to mirror strategy)

## [2026-07-02] ingest | Live chart — Forthius Reversal Scanner v5 running on 6yr Goodyear India daily
- Trigger: Kalyan shared a second screenshot, this time of the actual rendered scanner over 2020-2026, asking to note anything new about the *visual/runtime* implementation beyond the source-code read already ingested.
- **Most important finding — a real gap for the Early Reversal Detector design**: at the current bar (the exact low/recovery point the earlier %R Trend Exhaustion screenshot flagged bullish), the dashboard reads **Trend: RANGE**, not DOWN — and since bullish candlestick patterns require `downCtx = downTrend or (relaxTrend and ranging)` with `relaxTrend` defaulting false, Forthius's own default config would suppress bullish signals at exactly the Stage 4→1→2 transition moment this whole thread is trying to catch. Documented as a design rule in [[concepts/Stage-Analysis]]: any detector built here must treat "ranging after a decline" as first-class permissive, not opt-in.
- **Near S/R also lags at the worst moment**: shows "—" at the current bar despite sitting at an obvious multi-year low, because pivot confirmation needs `pvtLen` (5) bars of look-ahead — a pivot at the exact low can't confirm until 5+ bars later.
- **No label de-overlap exists** in this script (unlike AGPro's) — confirmed visually: 3 labels stack/overlap in the dense 2026-low reversal zone.
- **Grade distribution in real use skews low**: only 1 of ~16 visible signals across 6 years reached grade A; most are B/C. Bearish Engulfing fires far more often than any other pattern (loosest geometric bar to clear).
- **Convergence evidence**: bullish candlestick cluster (BullHarami ×2, 3Soldiers) lines up on the same bar as the earlier-ingested bullish %R Trend Exhaustion signal and an 8.6× volume spike — three independently-built signals agreeing strengthens the case for combining them rather than picking one.
- Pages updated: sources/Forthius-Reversal-Scanner-Pine.md (new Live Behavior Observations section), concepts/Stage-Analysis.md (design-rule note)

## [2026-07-02] ingest | Pine Script — Forthius Reversal Scanner v5
- Trigger: Kalyan pasted the full Pine v6 source directly, continuing the same Early Reversal Detector thread (third reversal-detection script this session, after %R Trend Exhaustion and the AGPro chart-pattern scanner).
- **This is a concrete, working implementation of a strategy this wiki already had in the abstract**: [[strategies/Candlestick-Filtering]] (sourced from a 7,275-stock backtest study) describes trend context → presignal/filter zone → candlestick trigger. Forthius codes exactly that: EMA20/EMA50 trend context → 5-factor confluence pre-condition (volume, S/R proximity, RSI zone, ADX strength, RSI divergence) → ~15 candlestick patterns as the trigger, each with its own geometry-based quality score. Linked directly as a concrete reference implementation rather than just conceptually related.
- **Detects far more patterns with more precise formulas than this wiki's existing [[concepts/Candlestick-Patterns]] page documents** — e.g. Piercing Line/Dark Cloud Cover quality uses an actual penetration *ratio* into the prior candle's body, not the commonly-simplified "closed past the midpoint" textbook rule.
- **Clever design detail worth reusing**: identical wick/body geometry gets different directional labels purely from trend context (Hammer in a downtrend vs. the same shape as Hanging Man in an uptrend) — geometry computed once, context-gating applied separately, rather than duplicating detection logic per label.
- **RSI divergence detection flagged as a cheap, high-value gap** in this project's own Python scanners — 2 lines of pandas, not currently computed anywhere in `scanner_templates.py`.
- Now 3 independently-sourced, non-Elliott-Wave reversal signals exist for the proposed Early Reversal Detector (candlestick trigger, chart-pattern trigger, oscillator-exhaustion trigger) — framed as parallel inputs rather than needing to pick just one.
- Pages created: sources/Forthius-Reversal-Scanner-Pine.md (wiki now 125 pages, 47 sources)
- Pages updated: strategies/Candlestick-Filtering.md (concrete reference implementation section), concepts/Candlestick-Patterns.md (cross-link), concepts/Reversal-Chart-Patterns.md (cross-link to the candlestick-scale sibling script)

## [2026-07-02] ingest | Pine Script — Reversal Pattern Quality Scanner [AGPro Series] v2.2
- Trigger: Kalyan pasted the full Pine v6 source directly, asking to "ingest this pine script to detect the reversal logic," continuing the Early Reversal Detector thread from the prior ingest.
- **Detects 4 classic reversal patterns from objective swing-pivot geometry** — Double Top, Double Bottom, Head and Shoulders, Inverse Head and Shoulders — full mechanics (pivot detection, neckline construction, validation gates, confirmation) written up in a new [[concepts/Reversal-Chart-Patterns]] concept page, a real gap in this wiki (only passing mentions existed before, in Minervini/VCP pages).
- **This changes the Early Reversal Detector recommendation from the prior ingest**: Double Bottom / Inverse Head & Shoulders detection is a stronger, equally-objective alternative/complement to the previously-proposed "MA reclaim" signal — it comes with its own built-in 5-factor quality score (structure/depth/volume/breakout-strength/exhaustion-context) and is directly portable to Python the same way %R Trend Exhaustion was.
- **Follow-Through Proof is the standout idea, and it's generic** — not specific to these 4 patterns. Every confirmed break is registered at confirmation (close + ATR), then graded exactly once at a fixed horizon (default 12 bars): did price move ≥0.75×ATR in the break direction? The resulting live per-symbol follow-through rate is a self-reported backtest of *that stock's own* recent signal reliability. Proposed as a generic mechanism to retroactively grade this project's other signals (%R Trend Exhaustion, Pre-Breakout Screener conviction scores) against real forward performance, turning static scores into self-correcting ones.
- Confirms rather than contradicts the Elliott-Wave-automation-skip decision from two ingests ago: this is the objective, pivot-based alternative that decision left open, now identified.
- Pages created: sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine.md, concepts/Reversal-Chart-Patterns.md (wiki now 124 pages, 46 sources)
- Pages updated: concepts/VCP.md, concepts/Percent-R-Trend-Exhaustion.md (cross-links to the new concept)

## [2026-07-02] ingest | TradingView screenshot — Goodyear India, "PMax+Strat" confluence dashboard
- Trigger: Kalyan shared a chart while asking for a "handy method to detect the early buy sign on large scale," right after this wiki's own analysis recommended skipping Elliott Wave automation.
- **Real-world validation for a gap this wiki had**: the %R Trend Exhaustion indicator was built and ported twice this session (JS for the chart dashboard, Python for bulk screening — see `tools/percent_r_trend_exhaustion.js` and `scanner_templates.compute_recent_exhaustion_signal`) but was never actually documented as a wiki concept. Fixed now: new [[concepts/Percent-R-Trend-Exhaustion]] page, with this screenshot as its motivating example — the exact same indicator, confirmed by its on-chart parameter label, fired a clean bullish exhaustion right at Goodyear India's multi-month low, immediately ahead of a fresh Wave 1-2 impulse.
- **Answers the "early buy sign at scale" question without reopening Elliott Wave automation**: the screenshot's own wave-target table simultaneously implies further downside (W3/W5 targets below current price) even as its wave label and the %R signal both read bullish — a concrete example of the same EW subjectivity problem already used to justify not automating wave-counting. Proposed instead: an "Early Reversal / Stage 1→2 Transition Detector" combining signals already built or cheap to add — bullish %R Trend Exhaustion (built), price reclaiming a key MA after a decline (not yet built), RS trend turning up from a low base as a second-derivative signal distinct from already-high RS (not yet built), and volume drying up into the low then picking up on reversal (cheap, OHLCV already fetched everywhere). Proposed, not yet built — pending threshold/scope confirmation.
- The chart's full indicator stack (Trend Align/Momentum/Vol-Stage/Volatility/Breakout/MACD/EMA-Cross/VWAP/ATR-Break/RSI-Div/Extension-Risk/Valuation/Earnings-Power/ADX+RSI/Rel-Strength/CONFLUENCE) is a per-chart "kitchen sink" confluence dashboard — same shape as this wiki's own conviction-score pattern (Pre-Breakout Screener, VCP scoring) but applied to one symbol at a time rather than bulk-screened; not something to replicate wholesale.
- Pages created: sources/TradingView-Goodyear-PMax-Strat-Confluence-2026.md, concepts/Percent-R-Trend-Exhaustion.md (wiki now 122 pages, 45 sources)

## [2026-07-01] ingest | GitHub repo — AgriciDaniel/claude-obsidian (AI second brain for Obsidian)
- Trigger: Kalyan pasted a promotional write-up of this repo earlier the same session (claiming "6,800 stars" — actual is 8.4k, understated). This is the repo the promo post was actually about; kepano/obsidian-skills (ingested just before this) was a related-but-separate tool mentioned in the same post.
- **Direct lineage to [[sources/Karpathy-LOOPS-md-Agentic-Field-Notes-2026]]**: explicitly built on Karpathy's LLM Wiki pattern — same disk-as-state / append-only-log philosophy this trading wiki already follows independently. Confirms convergent design rather than teaching something new about the core loop.
- **One concrete adoption: `wiki/hot.md`.** A ~500-word recent-context cache rewritten every session, read before `index.md`. Sharper than this wiki's current approach (re-reading `log.md` tail + `overview.md`). Added as a noted improvement to [[concepts/Agent-Loop-Design]]'s Application to This Project section — not yet implemented as an actual file, just captured as the next small upgrade.
- **Explicitly not adopting**: the four generic methodology modes (Generic/LYT/PARA/Zettelkasten) and generic directory layout — this wiki's bespoke entity/concept/strategy/source/analysis schema with bias tagging and key-level formats is more specific and more useful for trading than any generic mode would produce.
- **Noted but not needed yet**: multi-writer advisory locks (only matters for parallel batch ingestion, not attempted here) and hybrid BM25+embedding retrieval (only matters once index+page reads get expensive — not the case at 120 pages).
- Confirms the standing recommendation from the pre-ingest chat discussion: don't replace the existing trading-wiki system with either generic tool; cherry-pick specific ideas (`defuddle` from the skills repo, `hot.md` from this one).
- Pages created: sources/GitHub-AgriciDaniel-claude-obsidian-2026.md (wiki now 120 pages, 44 sources)
- Pages updated: concepts/Agent-Loop-Design.md (added `hot.md` cache idea + source cross-link)

## [2026-07-01] ingest | GitHub repo — kepano/obsidian-skills (official Obsidian agent skills)
- Trigger: Kalyan asked to check the repo for "anything new" after this wiki's Claude-Code-Skills page recommended cherry-picking rather than full adoption in an earlier same-day conversation.
- 5 skills under the official Agent Skills spec (works with Claude Code/Codex/OpenCode): `obsidian-markdown`, `obsidian-bases`, `json-canvas`, `obsidian-cli`, `defuddle`. MIT, ~39.2k★ (was ~35k when first mentioned — confirms active growth). No GitHub Releases/changelog exists, so "what's new" reduces to "what exists" since this was a first-time ingest.
- **Only `defuddle` has a concrete win for this wiki**: wraps the `defuddle` npm CLI (`defuddle parse <url> --md`) to strip a web page down to clean, token-efficient Markdown before Claude reads it — directly applicable to this wiki's own ingest pipeline, which has previously needed manual transcript pasting when automated fetch got blocked (see 2026-06-29 YT-Breakout-Screener entry below).
- `obsidian-markdown`/`obsidian-bases`/`json-canvas`/`obsidian-cli` have no current use case — this vault is edited as plain files by Claude Code directly, not through a running Obsidian app instance, and no page needs database-style filtered views.
- Confirms rather than contradicts the earlier chat assessment: don't adopt the generic vault tooling wholesale, cherry-pick `defuddle` only if web-page ingest volume increases.
- Pages created: sources/GitHub-kepano-obsidian-skills-2026.md (wiki now 119 pages, 43 sources)
- Pages updated: concepts/Claude-Code-Skills.md (added source to related, noted `defuddle` as a candidate ingest-pipeline tool)

## [2026-07-01] ingest | X thread — 45 Claude Design Skills That Kill AI Slop (@MyWestLord)
- Source: Long-form X thread cataloguing 45 SKILL.md installs across 6 layers with exact install commands and prompts.
- **Core mechanism:** SKILL.md files (plain markdown) load into Claude Code / Cursor / Codex and override model default taste *before* the first line of CSS or code — they are the practical implementation of contract-first (see LOOPS.md ingest same date).
- **The slop tell** documented: purple-to-white gradient + Inter font + 4 cards in grid + 1 weak hover state = median AI output. Skills overwrite the prior toward an intentional aesthetic commitment.
- **Recommended stack:** `frontend-design` (base taste) + `animate/Emil` (motion) + `theme factory` (token system) + **Playwright MCP** (visual feedback loop). Playwright identified as highest-leverage single addition — gives model eyes to grade its own visual output.
- **Key constraint rule** from `constraint-specification` (#39): if you can't verify the model followed a rule, rewrite the rule. Directly applicable to scanner card rubrics.
- **Cross-links with LOOPS.md** (same-session ingest): `system-prompt-structure` + `constraint-specification` are the prompt-engineering equivalents of Karpathy's contract.md. `task-decomposition` + `handoff-protocols` implement Planner→Generator→Evaluator handoff in concrete form.
- **Project application:** Playwright MCP could be wired to `chart_dashboard.html` for visual regression testing; `output-quality-rubrics` is the missing formal definition for scanner result card quality.
- No trading strategy content — pure AI-engineering/tooling thread.
- Pages created: sources/MyWestLord-45-Claude-Design-Skills-2026.md, concepts/Claude-Code-Skills.md (wiki now 118 pages, 42 sources)

## [2026-07-01] ingest | Paper — LOOPS.md: Field Notes on Agents That Run for Days (Andrej Karpathy, 2026)
- Source: conference-style reformatting of Karpathy's working notes on long-running agent loops (v060726). 9 principles extracted.
- **Core insight:** the unit of leverage is the loop, not the prompt. Agent roles (Planner / Generator / Evaluator) must never mix — mixing produces sycophancy and silent convergence on slop. The contract (testable checklist on disk, ~27 assertions) is what gets evaluated, not the original prompt.
- **Disk-state convention** (`## [YYYY-MM-DD] op | title` in append-only log) is already followed by this wiki — positive confirmation.
- **Harness deletion principle** applied: the existing `dashboard_app.py` Streamlit harness and wiki CLAUDE.md should be audited against each Claude model release and anything the model now handles natively should be removed.
- **Role separation note:** this wiki already follows the pattern — human (planner/curator) defines what to ingest; Claude (generator/evaluator) reads, writes, cross-references. Human should never be asked to update pages.
- **Bottleneck diagnosis:** trading system bottleneck has moved from data access → screening → charting → signal quality; next is likely execution discipline / trade-log feedback loop.
- No contradictions with existing trading wiki pages (engineering paper, not a trading strategy paper).
- Pages created: sources/Karpathy-LOOPS-md-Agentic-Field-Notes-2026.md, concepts/Agent-Loop-Design.md (wiki now 116 pages, 41 sources)

## [2026-06-29] ingest | YouTube — Crypto Momentum Screener + Telegram Bot on Hyperliquid (The AI University)
- URL: https://www.youtube.com/watch?v=vZ8usGRL_h8. Full transcript pasted by Kalyan after automated caption fetch was blocked (YouTube's signed `timedtext` URL returns HTTP 200 with an empty body for non-browser requests — confirmed across multiple Invidious mirrors too).
- **Title/content mismatch flagged**: the YouTube page's oEmbed title says "Claude Code Built a FREE Breakout Stock Screener (2 of My Rules Were Wrong)" but the actual transcript is entirely about a crypto momentum screener + Telegram alert bot on Hyperliquid perpetuals — no stock screener, no "8 rules/2 wrong" content anywhere in it. Documented as a known discrepancy in the source page rather than silently ingesting under a misleading title.
- New strategy: 3-filter screener — volume/mcap>0.1 (participation) + momentum floor-and-ceiling (timing: 1h +1–5%, 24h +5–15%, the ceiling specifically preventing chasing overextended moves) + EMA9/21/50 ascending stack & price>VWAP (direction). Day↔swing mode switch is just widening the momentum band and lengthening the scan interval, no code change — a reusable design principle.
- Cross-linked into [[concepts/EMA]] as cross-asset (crypto/intraday) confirmation of the stacked-EMA trend-direction principle already documented there for equities.
- Flagged as reusable for the existing pipeline: Hyperliquid data source already exists in `tools/data_source.py`/`tools/chart_server.py` (from the earlier multi-chart dashboard ingest) — this screener's filter math could layer on top instead of a fresh integration. Telegram bot-token/chat-ID alerting is cheap, zero-cost infra worth considering for existing screener outputs (Chartink scanners, `screener_pipeline.py`, sector rotation flips).
- Pages created: strategies/Hyperliquid-Momentum-Screener.md (wiki now 114 pages, 40 sources)
- Pages updated: sources/YT-Breakout-Screener-AIUniversity-20260629.md (stub → full ingest), concepts/EMA.md (cross-asset confirmation note + link)

## [2026-06-25] ingest | YouTube (via 3 AI-generated docs) — Minervini Market 360 Dashboard for Indian Markets
- Source: 3 AI-generated implementation docs (MINERVINI_DASHBOARD_GUIDE.md, TECHNICAL_IMPLEMENTATION.md, QUICK_START.md) dropped at the repo root, summarizing a YouTube video about rebuilding Minervini Market 360 for Indian markets. Not previously in the wiki structure — properly folded in now.
- **Two contradictions found and resolved/flagged**: (1) the source's "RS Rating" formula has no benchmark term at all (just a stock's own 52-week range position) — flagged as wrong in concepts/Mansfield-RS.md, with the correct benchmark-relative and percentile-rank alternatives already documented pointed to instead. (2) the source's VCP criteria are a generic 7-point restatement, already superseded in rigor by concepts/VCP.md's 3-tier algorithmic detection — no merge needed.
- **Major open item, deliberately left unresolved**: the source assumes building a brand-new React/FastAPI/PostgreSQL/Redis/WebSocket stack from zero, with no awareness that `tools/screener_pipeline.py` already runs Minervini+TechnoFunda+Elliott Wave scoring daily and `tools/dashboard_app.py` (Streamlit) — built and verified working the day before this ingest — already covers the screener and per-stock chart use cases. Documented as an explicit fork decision in the new source page rather than silently picking a side.
- The genuinely reusable material — a 6-section dashboard layout spec, a 5-category alert taxonomy (price/pattern/volume/news/performance), and an IST-timed daily operational workflow — extracted into a new analysis page as forward-looking requirements against the existing Streamlit dashboard, rather than left buried in a video-summary source page.
- Pages created: sources/Minervini-Market360-Dashboard-Video.md, analyses/Dashboard-UX-Operational-Requirements.md (wiki now 112 pages, 39 sources)
- Pages updated: concepts/Mansfield-RS.md (flagged non-standard RS Rating formula)

## [2026-06-22] ingest | GitHub repo — TauricResearch/TradingAgents
- Source: https://github.com/TauricResearch/TradingAgents — academically-grounded (arXiv 2412.20138 + Trading-R1 arXiv 2509.11420) multi-agent LangGraph framework modeling a full simulated trading firm: 4 parallel analysts (Fundamentals/Sentiment/News/Technical) -> bull vs bear researcher debate (max_debate_rounds config) -> Trader agent -> Risk Management -> Portfolio Manager veto gate -> simulated exchange execution
- **Most actionable finding**: README explicitly confirms NSE/BSE ticker compatibility (RELIANCE.NS, .BO examples) alongside HK/Tokyo/London/Canada/Australia/China A-shares/crypto — the only one of three trading-agent repos ingested this session that's directly usable for Indian equities without modification, since it works on "any market Yahoo Finance covers" via exchange-suffixed tickers (same .NS convention already used in tools/sector_rotation.py)
- Completed a three-way automation-spectrum comparison across all GitHub repos ingested this session: tradermonty (advisory-only, no verdict) -> zubair/ai-trading-claude (explicit buy/sell verdict + target price + winner) -> TradingAgents (actually executes a simulated trade via Portfolio Manager approval). Cross-linked both prior repo source pages back to this comparison.
- Notable design pattern: persistent trading_memory.md injects realized return (vs SPY alpha) and cross-ticker lessons into future Portfolio Manager prompts on repeat runs for the same ticker — an automated analogue to the trade-journal/R-multiple review discipline already in concepts/Capital-Management-Methods.md
- Pages created: sources/GitHub-TradingAgents-TauricResearch.md (wiki now 110 pages, 38 sources)
- Pages updated: sources/GitHub-claude-trading-skills-tradermonty.md, sources/GitHub-ai-trading-claude-zubair.md (added cross-links to the new three-way comparison)

## [2026-06-22] ingest | GitHub repo — zubair-trabzada/ai-trading-claude
- Source: https://github.com/zubair-trabzada/ai-trading-claude — 16-command Claude Code skill package (`/trade analyze`, `compare`, `thesis`, `risk`, `screen`, etc.), no API keys required, relies on live web search at analysis time. 5 parallel agents (Technical/Fundamental/Sentiment/Risk/Thesis) feed a weighted Trade Score (0-100) mapped to letter grades and explicit Buy/Hold/Avoid signals
- **Flagged a deliberate design contradiction**: this repo's entire output style (explicit buy/sell signal, target price + stop, an explicit "winner" in Compare mode) is the opposite philosophy from this project's own stock-analysis Claude Skill, whose non-negotiable rule #4 forbids exactly those things. Documented as a contrast to prevent accidentally blending the two philosophies if ideas are ever borrowed from this repo — the 5-dimension scoring structure is reusable, the verdict-generation is not.
- Pages created: sources/GitHub-ai-trading-claude-zubair.md (wiki now 109 pages, 37 sources)
- **Cross-links**: sources/GitHub-claude-trading-skills-tradermonty (data-sourcing-model contrast: web-search-only vs FMP/FINVIZ/Alpaca), concepts/Capital-Management-Methods, concepts/Support-Resistance

## [2026-06-22] ingest | GitHub repo — tradermonty/claude-trading-skills
- Source: https://github.com/tradermonty/claude-trading-skills — open-source toolkit of 70+ Claude Skills for US-equity trading/investing workflows (2,000+ stars). Not an Indian-market data source (FMP/FINVIZ/Alpaca are US-specific), but the most directly relevant external project found so far — a mature parallel to this vault's own tools/ directory and the stock-analysis Claude Skill
- Confirms this wiki's existing methodologies (VCP, CANSLIM, Distribution Days, institutional-flow tracking, position sizing) are mainstream and already productionized elsewhere as runnable skills, not idiosyncratic interpretations
- Notable design patterns worth borrowing: kanchi-dividend-review-monitor's "forced review trigger without auto-sell" pattern (safer automation than a trade-trigger); trader-memory-core's full-lifecycle thesis tracking (productionized version of the journal-schema idea from sources/SwingEdge-Learn-Process-Risk-Workflow.md); dual-axis-skill-reviewer's idea of quality-scoring the analysis tooling itself, not just the trades it produces
- Pages created: sources/GitHub-claude-trading-skills-tradermonty.md (wiki now 108 pages, 36 sources)
- No existing concept pages edited — this source confirms rather than extends current methodology; cross-links point to where each skill's underlying concept already lives in this wiki

## [2026-06-22] ingest | SwingEdge.info stock detail page (IZMO)
- Source: https://www.swingedge.info/stocks/IZMO — IT-Software, Momentum Continuation scan, 2026-06-22 snapshot. High headline score (82/100, grade B/64) but volume sub-score is a literal 0.0 despite RS 100 and ADX 43 — confirms the three meter sub-scores move independently
- **Key finding**: the "why not 100" panel only lists 1 gap (volume quality), but the page separately contains 4 overlapping risk signals — overextended 34% above MA50, RSI 69 at 77th percentile, an explicit "Failure flags: Overextended, Distribution cluster" line, and 6 distribution days. The headline score alone significantly understates the actual risk profile; all sections need to be read together, reinforcing the lesson from RELAXO's internal-contradiction finding.
- Third clean "RS leader in lagging sector" example (sector ranked #41/42, worst seen yet) — now roughly 3-vs-3 balanced against non-divergent tickers across 8 total SwingEdge ingests
- Pages created: entities/IZMO.md, sources/SwingEdge-IZMO-20260622.md (wiki now 107 pages, 35 sources)
- **Cross-links**: entities/KDDL, entities/NRBBEARING, concepts/ADX, concepts/Distribution-Days

## [2026-06-22] ingest | SwingEdge.info stock detail page (RELAXO)
- Source: https://www.swingedge.info/stocks/RELAXO — Footwear, microcap, 2026-06-22 snapshot. Setup readiness 34/100, decision-quality grade C/46
- **First clear internal contradiction found on this source across 7 ingests**: the page's FAQ schema states RELAXO is "in a confirmed Stage 2 uptrend, trading above its rising 50- and 200-day moving averages," while its own bullish-factors list separately states "Price trades below the long-term trend anchor (200DMA)" — same page, same snapshot date, directly opposing claims. The Context & regime panel sides with the FAQ. Escalated the existing "read bullet items individually" guidance to "cross-check any single bullet against the structured panels/FAQ before trusting it."
- Also a milder mismatch: meta-description summarizes the stock as "Weak" while the on-page verdict reads "Wait and Watch" / "Early Trend" — three different short summaries on one page.
- Confirmed overhead-supply % as a real recurring metric (2nd ticker after SIGMA to show it: 68% here vs SIGMA's 73%)
- Pages created: entities/RELAXO.md, sources/SwingEdge-RELAXO-20260622.md (wiki now 105 pages, 34 sources)
- **Cross-links**: entities/SIGMA, entities/INDSWFTLAB, concepts/Stage-Analysis, concepts/Distribution-Days

## [2026-06-22] ingest | SwingEdge.info Learn series — remaining 19 lessons (full 22-lesson catalog complete)
- Fetched all 19 remaining lessons from the catalog first captured in sources/SwingEdge-Learn-Intro-Swing-vs-Day.md. Unlike the first two lessons (mostly introductory), this batch contained substantial new, concrete mechanics — merged directly into existing concept pages rather than left in source pages, so each indicator/topic has one canonical home
- **Updated concept pages**: RSI.md (regime-aware ranges, hidden divergence, swing-failure swings), MACD-Divergence.md (zero-line filter, histogram accel/decel, crossover-location table, MTF template), ADX.md (refined 5-band value table replacing the old 3-band split, slope-over-level rule, stock+index regime filter), EMA.md (SMA vs EMA, per-period role breakdown, slope rule, stretch heuristic), Capital-Management-Methods.md (ATR-based stops/chandelier/Supertrend, trailing-exit system comparison table, five-line trade plan + R-multiple discipline)
- **New concept pages created**: Bollinger-Bands-Squeeze.md, Multi-Timeframe-Analysis.md, Anchored-VWAP-Pyramiding.md
- **Resolved an open caveat**: sources/SwingEdge-Position-Sizing-Tool.md's original ingest couldn't capture the live scanner-context-card data (client-side rendered); the position-sizing-calculator-guide lesson explains exactly what that card shows (trade quality score, green/grey checks, sector RS/liquidity/volume-ratio pills, ATR-based stop suggestion) — added as an update note rather than re-fetching
- Pages created: sources/SwingEdge-Learn-Indicators-Deep-Dive.md, sources/SwingEdge-Learn-Process-Risk-Workflow.md, concepts/Bollinger-Bands-Squeeze.md, concepts/Multi-Timeframe-Analysis.md, concepts/Anchored-VWAP-Pyramiding.md (wiki now 103 pages, 33 sources)
- Pages updated: concepts/RSI.md, concepts/MACD-Divergence.md, concepts/ADX.md, concepts/EMA.md, concepts/Capital-Management-Methods.md, sources/SwingEdge-Position-Sizing-Tool.md
- Deliberately did NOT spawn separate pages for entries-pivots-pullbacks, advanced-swing-patterns, targets-exits, trade-plan-r-multiple, volume-price-confirmation, market-regime-relative-strength, scanner-to-trade-workflow, psychology-process, advanced-trailing-exits, risk-stops-sizing — these lessons' content either restated existing wiki coverage (VCP, Stage-Analysis, Distribution-Days, Kalyan-Trading-Philosophy) or was fully absorbed into the Capital-Management-Methods additions; mapped explicitly in sources/SwingEdge-Learn-Process-Risk-Workflow.md's disposition table so nothing is silently dropped

## [2026-06-22] ingest | SwingEdge.info Learn lesson — "Trends & Stages"
- Source: https://www.swingedge.info/learn/trends-stages — lesson 2/22. Mostly restates existing Stage-Analysis/Support-Resistance content already in this wiki, so kept as a single source page rather than new concept pages
- **Resolved an open tension**: SwingEdge's own stated philosophy — "[RS] surfaces context; use it to narrow a list, not to skip your own chart read" — explains why RS 100 was framed as pure leadership on NRBBEARING but as "overowned, chase risk" on INDSWFTLAB. Updated sources/SwingEdge-INDSWFTLAB-20260621.md's Contradictions section to mark this resolved rather than left as an open question.
- Other notes worth keeping: "scanners are interns that fetch candidates—you still interview each chart" (citable framing for how to use all prior SwingEdge screener ingests); failed-breakdown-precedes-squeeze pattern cross-confirmed with strategies/False-Break-Buildup-Trading.md and concepts/Distribution-Days.md's failed-retest pattern
- Pages created: sources/SwingEdge-Learn-Trends-Stages.md (wiki now 98 pages, 31 sources)
- Pages updated: sources/SwingEdge-INDSWFTLAB-20260621.md (resolved contradiction note)

## [2026-06-22] ingest | SwingEdge.info Learn lesson — "What is swing trading?"
- Source: https://www.swingedge.info/learn/intro-swing-vs-day — lesson 1 of a 22-lesson curriculum. Mostly introductory (swing vs day, OHLC, candle-pattern caveats), already well-covered elsewhere in this wiki, so kept as a single source page rather than spawning new concept pages
- Two things worth keeping: (1) a concrete review-cadence checklist (pre-market/post-close/weekly/monthly), a process-layer addition complementary to the philosophy-level analyses/Kalyan-Trading-Philosophy.md; (2) the full 22-lesson catalog with topic tags and read times, captured as a reference map so future targeted ingests don't need to re-fetch the index — flagged 3 lessons as highest-priority for follow-up (HTF/VCP/contraction, Anchored VWAP & pyramiding, Scanner-to-trade workflow)
- Pages created: sources/SwingEdge-Learn-Intro-Swing-vs-Day.md (wiki now 97 pages, 30 sources)
- No entity/concept pages created or updated — content didn't add anything not already captured

## [2026-06-22] ingest | SwingEdge.info stock detail page (SIGMA)
- Source: https://www.swingedge.info/stocks/SIGMA — BPO/ITeS, 2026-06-21 snapshot. Weakest setup of any SwingEdge ticker ingested so far: Stage 4 (fails Stage-2 gate entirely), setup readiness 0.0/100, decision-quality grade D/4, 5 skip reasons (new high)
- Three new metric types not seen on prior tickers: thin liquidity in absolute ₹/day terms (slippage risk), overhead supply % (trapped sellers above current price), and an explicit numeric failure-risk score (66/100) — a third independent scoring dimension alongside readiness score and decision-quality grade
- Noted an unusual "negative risk distance" quirk: the stated stop (₹44.8) sits above the current price (₹38.7) since the entry zone is forward-looking — flagged as a general caution for reading any SwingEdge entry/stop pair
- Useful as a negative-control example confirming the source's scoring system meaningfully differentiates quality rather than rating everything moderately positive
- Pages created: entities/SIGMA.md, sources/SwingEdge-SIGMA-20260621.md (wiki now 96 pages, 29 sources)
- **Cross-links**: entities/INDSWFTLAB, entities/AADHARHFC, concepts/Distribution-Days, concepts/Stage-Analysis

## [2026-06-22] ingest | "CHOCH vs BOS" trading infographic (pasted image)
- Source: pasted social-media infographic, no URL/author attribution. Defines CHOCH (Change of Character — counter-trend swing break, reversal warning) vs BOS (Break of Structure — same-direction swing break, trend continuation confirm), plus adjacent SMC terms MSS, FVG, LIQ, HTF POI shown in the same annotated chart sequence
- This fills the market-structure-labeling half of Smart Money Concepts vocabulary; the zone-based half (RBR/DBD/RBD/DBR, flip zones) was already covered by strategies/Supply-Demand-Zone-Trading.md from a 2022 SMC book — the two together now cover most mainstream SMC vocabulary
- Pages created: concepts/Market-Structure-CHOCH-BOS.md, sources/CHOCH-vs-BOS-Infographic.md (wiki now 94 pages, 28 sources)
- Pages updated: strategies/Supply-Demand-Zone-Trading.md (cross-link: flip zone confirmed by later BOS = S&D-framework equivalent of a CHOCH)
- **Cross-links**: concepts/Support-Resistance (HH/HL/LH/LL = same swing-point marking method), concepts/Order-Flow (liquidity grabs/stop hunts), concepts/Elliott-Wave (CHOCH often coincides with start of a corrective wave)

## [2026-06-22] ingest | SwingEdge.info Sector Momentum Map
- Source: https://www.swingedge.info/sectors/momentum — unlike the position-sizing and breakdowns tool pages, this one IS server-rendered with live data: ~140 NSE sector/thematic/factor indices in a Leading/Improving/Weakening/Lagging quadrant map vs Nifty 500
- **Major finding**: this is the same 4-quadrant naming as our own strategies/Sector-Liquidity-Rotation.md tooling, but computed from price relative-strength (3mo RS vs Nifty500 x recent "Pace") rather than FII/DII holding-change flow — a genuinely independent, comparable sector-strength read using a totally different data source
- Snapshot (2026-06-22): 14 Leading (top: Nifty IPO, Media, Realty, EV&NewAge Auto), 34 Improving (PSU Bank, Bank, Consumer Durables), 56 Weakening (Capital Markets, Metal, Pharma — relevant given entities/INDSWFTLAB's recent cautious pharma-stock verdict), 35 Lagging (IT, CPSE, plus VIX/inverse products that aren't real sectors)
- Pages created: sources/SwingEdge-Sector-Momentum-Map-20260622.md (wiki now 92 pages, 27 sources)
- Pages updated: strategies/Sector-Liquidity-Rotation.md — added cross-reference note recommending a side-by-side comparison run (flow-based bias vs this page's price-RS bias) the next time the screener.in export is refreshed; divergence between the two would itself be a signal (institutional accumulation often precedes price strength)
- **Cross-links**: entities/INDSWFTLAB (pharma sector context), analyses/Sector-Watchlist

## [2026-06-22] ingest | SwingEdge.info stock detail page (INDSWFTLAB)
- Source: https://www.swingedge.info/stocks/INDSWFTLAB — Pharmaceuticals & Drugs, 2026-06-21 snapshot. Lowest setup-readiness (55/100, "Extended") and most skip reasons (4) of any SwingEdge ticker ingested so far; verdict "Wait and Watch"
- **Key new finding**: RS rank 100/100 explicitly framed as "overowned (NSE: 21-25% win rate, operators distribute here)" — the opposite framing from NRBBEARING's pure-leader read of the same max RS score. Confirms the source treats RS rank as context-dependent on extension/timing, not a context-free quality score. Flagged a mild tension with this wiki's existing Minervini Stage-2 criterion (RS≥70 as a pure positive filter) on entities/INDSWFTLAB.md and sources/SwingEdge-INDSWFTLAB-20260621.md.
- Also: second confirmed real-world distribution-days example (4 flagged, after AADHARHFC's 6), and a "sloppy pivot" quality flag — the negative counterpart to KDDL's "flat-top/premium" pivot, confirming pivot-shape scoring is a real separate dimension in this source's model
- Pages created: entities/INDSWFTLAB.md, sources/SwingEdge-INDSWFTLAB-20260621.md (wiki now 91 pages, 26 sources)
- **Cross-links**: entities/KDDL, entities/NRBBEARING, entities/AADHARHFC, concepts/Distribution-Days, concepts/Stage-Analysis, concepts/RSI

## [2026-06-22] ingest | SwingEdge.info Downside Risk screener (/breakdowns)
- Source: https://www.swingedge.info/breakdowns — methodology page only, same client-side-rendered-results limitation as the position-sizing tool ingest (no live flagged tickers captured, just the screener's rules/definitions)
- Captured precise, falsifiable formulas not previously documented in this wiki: support-loss detection (pivot low = local min with 2+ confirming candles each side; close >0.5% below triggers a break), distribution-day volume z-score model (down close + vol ≥50d avg+0.5σ + wide spread + close near low), Severe(80+)/High(65-80)/Moderate(50-65) composite-score tiers, and confirmation that "bearish DMA stack" = the explicit inverse of the Stage 2 trend template already in this wiki
- Pages created: concepts/Distribution-Days.md (new concept, formally defines a term used loosely on entities/AADHARHFC.md before this), sources/SwingEdge-Downside-Risk-Screener.md (wiki now 89 pages, 25 sources)
- Pages updated: concepts/Stage-Analysis.md (cross-link: bearish DMA stack = inverse Stage 2/Stage 4), concepts/Support-Resistance.md (cross-link: falsifiable support-loss rule + failed-retest pattern)
- **Cross-links**: entities/AADHARHFC (retroactively formalizes its distribution-day flag), concepts/ADX

## [2026-06-22] ingest | SwingEdge.info Position Sizing tool (requested as ?symbol=CGPOWER)
- Source: https://www.swingedge.info/tools/position-sizing?symbol=CGPOWER — requested as a CGPOWER-specific page, but the `?symbol=` param only pre-fills the stock-search box client-side; no CGPOWER scanner data (entry/stop/ATR) is present in the static HTML, so this was filed as a generic tool/methodology ingest rather than a CGPOWER entity update. Noted explicitly in the source page that a real CGPOWER-specific sizing read would require fetching /stocks/CGPOWER instead (the stock-detail page format used in prior 3 ingests).
- Captured: fixed-fractional sizing formula, default 0.5% risk/trade + 20% max allocation cap, gap-risk fill simulation (worse-than-stop-limit stress test, not previously documented in this wiki), 6 R-multiple exit-style templates including a pyramid mode
- Pages created: sources/SwingEdge-Position-Sizing-Tool.md (wiki now 87 pages, 24 sources)
- Pages updated: concepts/Capital-Management-Methods.md — added "Gap-Risk Simulation" subsection and a "Reference Defaults" subsection citing this source
- **Cross-links**: concepts/Kelly-Criterion, concepts/Capital-Management-Methods, prior SwingEdge stock-page ingests

## [2026-06-22] ingest | SwingEdge.info stock detail page (AADHARHFC)
- Source: https://www.swingedge.info/stocks/AADHARHFC — Finance - Housing, 2026-06-21 snapshot. Decision-quality grade C/51 (weakest of 3 SwingEdge tickers ingested), skip reason: "6 distribution days recently — institutional selling" (a different risk type than KDDL's wide-stop or NRBBEARING's overextension)
- **Breaks the "RS leader in lagging sector" pattern** noted on KDDL/NRBBEARING: here individual RS (55) and sector RS both lag, in agreement. Updated the running note on sources/SwingEdge-KDDL-20260621.md — now 2 of 3 tickers show the divergence, confirming it's real but not universal.
- Also confirmed a third time: the site's "Bullish factors" card mixes true positives with explicit score penalties (e.g. "1 prior pivot rejection, -8 pts" listed as bullish) — now a known structural quirk of this source's template across all 3 ingests.
- Pages created: entities/AADHARHFC.md, sources/SwingEdge-AADHARHFC-20260621.md (wiki now 86 pages, 23 sources)
- Pages updated: sources/SwingEdge-KDDL-20260621.md (revised pattern-tracking note: 2 of 3, not universal)
- **Cross-links**: entities/KDDL, entities/NRBBEARING, concepts/VCP, concepts/Stage-Analysis, concepts/ADX, concepts/RSI

## [2026-06-22] ingest | SwingEdge.info stock detail page (NRBBEARING)
- Source: https://www.swingedge.info/stocks/NRBBEARING — Momentum Continuation scan (different scan bucket than KDDL's Base Formation), 2026-06-21 snapshot
- RS rank 100/100, ADX 51, Stage 2 score 8/8 — strongest readings seen from this source yet, but flagged "Overextended" (25% above MA50, RSI 71 at 90th pct 1yr) — a chase-risk profile, distinct from KDDL's wide-stop/un-triggered-pivot risk
- **Confirms a recurring pattern first noted on KDDL**: an individually RS-leading stock sitting inside a sector the source's own model rates "Lagging" — now 2 of 2 SwingEdge ingests. Hypothesis: their sector-RS score averages across constituents, which one standout stock can sit well above. Flagged for a dedicated analysis page if a 3rd ticker confirms it.
- Pages created: entities/NRBBEARING.md, sources/SwingEdge-NRBBEARING-20260621.md (wiki now 84 pages, 22 sources)
- Pages updated: sources/SwingEdge-KDDL-20260621.md (added cross-link + pattern-confirmation note)
- **Cross-links**: entities/KDDL, concepts/VCP, concepts/Stage-Analysis, concepts/ADX, concepts/RSI

## [2026-06-22] ingest | SwingEdge.info stock detail page (KDDL)
- Source: https://www.swingedge.info/stocks/KDDL — a free NSE swing-trading scanner/setup site (Base Formation scan), fetched via curl with a standard browser User-Agent (default WebFetch gets a 403; no auth needed for the public scan data)
- Key finding: the site splits a raw "setup readiness" score (100/100 for KDDL) from a separate, more conservative "decision quality" grade (B, 61/100) — driven down here by an 8%-wide stop the source itself flags as "too wide to size well for a swing"
- Notable contradiction worth tracking: KDDL is rated an RS leader (76/100) individually, but its own sector (Watches & Accessories) is ranked #26/32 "Lagging/headwind" by Swing Edge's own sector model — a different sector-strength methodology (RS/momentum-based) than this wiki's FII/DII-flow-based sector-rotation tooling. Worth comparing the two methodologies' sector rankings side-by-side in a future analysis.
- Pages created: entities/KDDL.md, sources/SwingEdge-KDDL-20260621.md (wiki now 82 pages, 21 sources)
- **Cross-links**: KDDL entity links to concepts/VCP, concepts/Stage-Analysis, concepts/ADX; source page links to strategies/Sector-Liquidity-Rotation and analyses/Sector-Watchlist for the sector-methodology cross-check

## [2026-06-20] query | Document sector_rotation.py tool architecture
- User requested a dedicated page for tools/sector_rotation.py rather than leaving it referenced only inline in the strategy page
- Pages created: analyses/Sector-Rotation-Tool-Architecture.md (wiki now 80 pages, 20 sources) — documents the cap-weighted aggregation formula, 4-way bias classification table, SECTOR_INDEX_MAP limitations, and the unvalidated NSE XBRL fallback (tools/nse_shareholding_fetch.py)
- Pages updated: strategies/Sector-Liquidity-Rotation.md (added cross-link to the new architecture page)
- **Cross-links**: follows the same documentation pattern as [[analyses/VCPBot-Architecture]] for tool/system internals

## [2026-06-20] query | Sector-wise FII/DII liquidity rotation strategy
- User drafted a screener.in query to detect stocks with recent FII/DII holding changes, trace to sector, rank top sectors
- Refined query: widened threshold from >0.1% to >0.5% (noise filter), made FII clause bidirectional (>0.5 OR <-0.5) instead of OR'd with DII — rotation requires seeing both inflow and outflow sectors in one pass
- Confirmed screener.in blocks unauthenticated/automated fetches (WebFetch returned login page, not results) — pipeline integration deferred; built as manual-export-driven tool instead
- Pages created: strategies/Sector-Liquidity-Rotation.md (wiki now 79 pages, 20 sources)
- Tooling created: tools/sector_rotation.py — aggregates FII holding change % weighted by market cap per sector (Industry column required in export), pulls trailing-1Y sector index returns via yfinance, classifies 4-way rotation bias (confirmed bullish / early accumulation / distribution into strength / confirmed bearish), exports colour-coded Excel
- Not yet run with real data — awaiting a screener.in CSV/XLSX export (with Industry column added) from the user
- **Cross-links**: extends [[strategies/Screener-Queries]] (query #7 Re-Rating Candidates already uses FII/DII holding change); will validate or contradict static lists in [[analyses/Sector-Watchlist]]

## [2026-06-19] ingest | Book — The Professional Price Action Trading Book (Kenny Brandon, 2023, Kindle Scribe)
- Source: PDF, 66 pages but image-heavy (~48K chars extractable text, 4 chapters); raw/Price-Action-Trading-MTF-Brandon-Kenny-2023.pdf
- Pages created: sources/Price-Action-Trading-MTF-Brandon-Kenny-2023, strategies/False-Break-Buildup-Trading (wiki now 78 pages, 20 sources)
- Pages updated: concepts/Stage-Analysis (added Brandon's plain-language 200-MA-gated 4-stage variant + fractal-timeframe note), concepts/Support-Resistance (added "area of value" / rubber band snap entry veto)
- Key extractions: false break (trapped breakout traders fuel the reversal); buildup (volatility-contraction zone giving a tighter stop than the wider range — discretionary analog of VCP/Darvas); pre-breakout multi-TF technique (HTF buildup + LTF false break = enter before breakout fires); rubber band snap (don't trend-trade far from area of value — stop too wide, price tends to pull back first); 4-stage market cycle gated purely on 200-day MA slope/flatness; M.A.E. formula (Market Structure → Area of Value → Entry trigger); candlestick basics (Hammer/Shooting Star/Engulfing) + 2-question heuristic (close-in-range, size-vs-recent-candles) for reading any pattern without memorizing it; philosophy (price action traders enter/exit earlier than indicator traders; trend rarely reverses on one news item)
- **Primary actionable insight**: pre-breakout multi-TF technique (HTF buildup + LTF false break) is a concretely testable entry refinement for existing VCP/Darvas/breakout setups; rubber band snap is a bolt-on entry filter (skip trend entries far from MA/trendline)
- **Cross-links**: false break/buildup mechanics map onto [[concepts/Stage-Analysis]] Stage 1/3 ranges; rubber band snap extends [[concepts/Support-Resistance]]'s area-of-value concept; buildup = discretionary restatement of [[concepts/VCP]]/[[concepts/Darvas-Box]] volatility contraction
- No contradictions with existing wiki — book's 4-stage and S/R frameworks are simplified restatements of Minervini's and Dhruv & Emily's more rigorous versions already in the wiki

## [2026-06-19] ingest | Book — Candlestick Charting Explained (Litchfield & Morris, 3rd ed, 2006, McGraw-Hill)
- Source: epub; Gregory L. Morris (original 1992) + Ryan Litchfield (Ch.10); 30 HTML chapters
- Pages created: sources/Litchfield-Morris-Candlestick-Charting-Explained-2006, concepts/Candlestick-Patterns, concepts/Sakata-Method, strategies/Candlestick-Filtering (wiki now 76 pages, 19 sources)
- Key extractions: candle anatomy (body/shadow/marubozu/doji/yin-yang); 50+ reversal patterns (Hammer/Engulfing/Morning Star/Abandoned Baby/Three Soldiers etc.); 5 continuation families (Separating Lines/Tasuki Gap/Three Methods/Mat Hold/Three-Line Strike); Sakata's Method history (Honma 1750, Sakata port, 160 rules, 5 core formations); reliability stats (7,275 stocks, 14.6M days, 1.7M patterns; avg %Win 41–64%; candles(2) = #1 vs 14 indicators at 2-day horizon); filtering concept (presignal zone + candle = dramatic improvement); Litchfield Ch.10 (candles as entry trigger within S/R zones, not standalone); CandlePower/CandleVolume (body width = volume)
- **Primary actionable insight**: S&D Zone (supply-demand-zone-trading filter) + RSI presignal + candle pattern = best-evidence entry sequence for swing trades
- **Cross-links**: Litchfield's S/R-as-filter framework directly maps to [[strategies/Supply-Demand-Zone-Trading]]; Honma's 3-day patience rule echoes [[concepts/Trading-Psychology-Champion]]; filtering concept reinforces [[concepts/RSI]] and [[concepts/MACD-Divergence]] usage
- No contradictions with existing wiki

## [2026-06-18] ingest | YouTube — David Hannan (Laptop Legend): Pyramiding, Parabolic Shorts, Exponential Sizing (Titans of Tomorrow)
- Source: https://www.youtube.com/watch?v=PBhrBnrtbxs — 106K chars; David Hannan, small cap trader $2K→$9M, 41% win rate, first red day specialist
- Pages created: sources/YT-David-Hannan-Laptop-Legend, strategies/Parabolic-Short-First-Red-Day (wiki now 72 pages, 18 sources)
- Pages updated: concepts/Capital-Management-Methods (pyramiding via wash-and-reclaim; exponential bet sizing 8–20x; Pareto 14%=82%), analyses/Kalyan-Trading-Philosophy (Pareto data, exponential sizing progression, pyramiding application to sweep-reverse scalp, mean reversion on Nifty, break-even validation)
- Key extractions: pyramiding = recycling same dollar risk as trade moves in your favor (tighten stop → add to same R); $10K risk → $1M gain in 4 days on Bitcoin; exponential sizing (1x/2-3x/8-20x for C/B/A+ setups); Pareto: top 14% days = 82% profits; first red day setup (6+ consecutive gap-up days + blow-off volume + accelerating gap size + price extended far above MAs + large cap behaving like small cap); win rate higher on mean reversion than breakouts because overextended stocks MUST revert; dynamic break-even (if returns to average in big size = exit); broken slot machine (find your edge niche, stay there); 2-min bar trailing / 5-min 9 EMA trailing; time of day (open cleaner than 1-2pm)
- **Cross-links**: wash-and-reclaim add = Kalyan's second sweep-reverse on next level; tap-and-go philosophy validated (if hanging around = not working); Pareto is real and argues for variable sizing not uniform
- No contradictions with existing wiki

## [2026-06-18] ingest | Book — How To Win in The Trading Game (Dhruv & Emily, 2022) — S&R, SMC, Supply & Demand
- Source: epub ~24K chars; concise practical guide for S&R zones, Smart Money concept, Supply & Demand formations
- Pages created: sources/SR-SMC-Supply-Demand-Dhruv-Emily-2022, concepts/Support-Resistance, strategies/Supply-Demand-Zone-Trading (wiki now 70 pages, 17 sources)
- Key extractions: 3 Smart Money signatures (sideways price action / aggressive initiation / strong rejection); 4 S&D formations (RBR/DBD continuation; RBD/DBR reversal; flip zones); zone strength factors (freshness #1, exit-move strength, time at zone, distance before return, volume); 3-group S&R psychology (longs/shorts/uncommitted all defend the same zone on first retest → self-fulfilling); zones not lines (undershoot + overshoot problem solved by zone width); two-step zone drawing (line chart → candlestick zone); multi-TF hierarchy (weekly first, trade off daily/hourly); breakout conditions (ascending/descending triangles; trend alignment; tight range; repeated touches weaken level); day trading = prior day H/L as S&D zones
- **Cross-link to Varmer**: Smart Money accumulation (sideways, low volume) = Varmer's iceberg order placement; aggressive initiation = VWAP algo acceleration. Same mechanism from different perspectives — strongly validates the leech-on-whale model
- **Cross-link to Kalyan**: sweep-reverse scalp is formally a DBR formation + spring (false breakdown confirming zone holds); stop at sweep low = stop below zone base
- No contradictions with existing wiki

## [2026-06-18] ingest | YouTube — Samir Varmer: PhD Physicist to 8-Figure Futures Trader (Titans of Tomorrow)
- Source: https://www.youtube.com/watch?v=itRL9v67v9I — 104K-char transcript; Samir Varmer, #5 US futures trader, systematic fund manager 30+ years
- Pages created: sources/YT-Samir-Varmer-Physicist-Trader, strategies/Opening-Range-Breakout (wiki now 67 pages, 16 sources)
- Pages updated: concepts/Order-Flow (iceberg/VWAP algo stop hunt mechanics; double-tap explanation; leech on whale; order placement tactics), concepts/Kelly-Criterion (Varmer's drawdown-tolerance sizing; 200-day MA regime scaling; leptokurtic returns), analyses/Kalyan-Trading-Philosophy (Varmer direct validation of Kalyan's sweep-reverse scalp; regime filter; noise stress test; double-tap tolerance)
- Key extractions: reactive not predictive (system reacts to today's data, holds ~1 year); 200-day MA regime filter (2/3 returns above line / 2/3 risk below = cut size to half below line); stop hunt = VWAP algo slowing buys near stop clusters to improve execution (not conspiracy); leech on whale = trade alongside institutional VWAP direction; noise injection stress test for system robustness; Kelly via drawdown tolerance (not formula); leptokurtic returns / potentially infinite SD for individual stocks; opening range breakout (10–20 min) statistically sound for equities; never use round number stops; pod shop drawdown limits are statistically stupid (paper in JPM); Grossman-Stiglitz paradox; personality-strategy congruency framework
- **Major insight for Kalyan**: Varmer explicitly confirmed Kalyan's sweep-reverse scalp is the correct implementation of leech-on-whale; double-taps normal; protected low is the right stop; avoid round-number stops; halve size when index below 200-day MA
- No contradictions with existing wiki

## [2026-06-18] ingest | Actowiz Solutions — BSE/NSE/Moneycontrol Financial Data Scraping (India)
- Source: https://www.actowizsolutions.com/bse-nse-moneycontrol-financial-data-scraping-india.php — marketing/product page for commercial Indian financial data vendor
- Pages created: sources/Actowiz-Indian-Financial-Data-Scraping (wiki now 65 pages, 15 sources)
- Key extractions: covers BSE/NSE/Moneycontrol/Screener/Tickertape/AMFI/SEBI/MCA; data types = EOD + real-time prices, corporate actions, quarterly financials, shareholding patterns (promoter/FII/DII/retail), insider trading, mutual fund NAVs; 5,000+ companies; delivery via REST API / S3-GCS-Azure batch / warehouse load; pricing ~₹2L/month for EOD
- **Backtesting quality**: four critical features — corporate action adjustments, symbol history tracking, survivorship bias elimination, point-in-time provenance — directly solve integrity gaps in VCPBot and Screener-Queries backtesting pipelines
- **Alignment**: complements VCPBot-Architecture (yfinance limitation identified: no adjustments, no survivorship bias correction); shareholding data relevant to Minervini SEPA institutional sponsorship filter
- No contradictions; no overview.md update

## [2026-06-17] ingest | Image — 6 Filters Saved Me From Hundreds of Bad Charts (Haseeb Badar @hb_stocks)
- Source: Social media infographic, slide 1/7 — only slide 1 ingested; remaining 6 slides not available
- Pages created: sources/HB-Stocks-6-Filters (wiki now 64 pages, 14 sources)
- Pages updated: concepts/Stage-Analysis (added Haseeb Badar 6-filter framework as simplified visual Stage 2 check; sources 1→2)
- Key extractions: 6 rejection filters (linear mover / near 52W high / high ADR / above 20+50+150+200 MAs / quality consolidation / good volume activity); rejection-filter philosophy ("remove everything that doesn't deserve your capital"); ADR filter new to wiki — `ATR(14)/Close * 100 > 2%` as screener condition
- **Alignment**: filters 1/2/4/5/6 map directly to Minervini Trend Template criteria and VCP base phase already in wiki. Filter 3 (ADR) is the only genuinely new element — a minimum daily range/volatility guard
- No contradictions; no overview.md update — methodology, no market-thesis change

## [2026-06-17] ingest | Book — Prop Trading Secrets (Kathy Lien & Etienne Crete, 2025)
- Source: epub file `Prop Trading Secrets _ How Successful Traders are Living off the Markets{Kathy Lien_ Etienne Crete}(2025){107728260} libgen.li.epub`; extracted all 17 chapters via Python zipfile + HTML stripping
- Pages created: sources/Prop-Trading-Secrets-Lien-Crete-2025, concepts/Prop-Trading-Funded-Model, concepts/Order-Flow, concepts/Initial-Balance, strategies/TPT-Thrust-Pullback-Thrust, strategies/Prop-Scalp-NQ-Initial-Balance (6 new pages; wiki now 63 pages, 13 sources)
- Pages updated: concepts/Trading-Psychology-Champion (added prop trading psychology section: 3-strikes rule, first-trade tone, daily goal protection, resilience as differentiator, overfunded+underleveraged), analyses/Kalyan-Trading-Philosophy (added multi-trader convergence section: 3-strikes rule, first trade sizing, video review, daily goal protection)
- Key extractions: prop firm funded model mechanics (eval fee → funded → profit split; trailing drawdown mechanics); 14 trader profiles (Rob Hoffman/TPT, Davide Biocchi/TWbook order flow, David Floyd/positive convexity, Sunny Harris/SunnyBands, Ali Crooks/market condition formula, Aatu Kokkila/event trading $32M AUM, Andres Granger/market-neutral arbitrage $10M, Matt Miller/IB scalping $309K/85 days, Nick Syiek/3-pillar scoring, Vince Koehn/scale with accounts $1M); 10-step prop trading checklist; 15 common traits of successful prop traders
- **No contradictions with existing wiki**: book reinforces hard stops (Minervini-consistent), small position sizing (<1% = Kelly/philosophy alignment), process over outcome (Trading-Psychology-Champion alignment)
- **New contribution**: prop firm-specific rules (trailing drawdown mechanics, daily goal management, evaluation vs. funded strategy differences) are not covered elsewhere in wiki

## [2026-06-16] ingest | YouTube — Free TradingView Plus Alternative (AI University / Nitin)
- Source: https://www.youtube.com/watch?v=LnyjLNizKHw — transcript extracted via youtube-transcript-api (379 segments, 14,439 chars)
- Pages created: sources/YT-MultiChart-TradingView-Alternative
- Key extractions: Free charting stack = Lightweight Charts (TradingView OSS) + yfinance + Hyperliquid WebSocket; 8-pane responsive layout; premium indicators (Volume Profile VAH/POC/VAL, Fair Value Gap) + unlimited standard indicators (RSI, MACD, BB, VWAP, Williams %R); covers NSE/BSE, US stocks, crypto on one screen; runs locally on localhost:5000; Claude Code + one prompt builds it in <15 minutes
- Integration opportunity: screener_pipeline.py already uses yfinance → a Lightweight Charts frontend dashboard would add live multi-pane charting to the existing pipeline output. Volume Profile overlay confirms VCP "overhead supply cleared." Fair Value Gap adds entry-timing context on Minervini SEPA pivot breaks.
- No contradictions with existing wiki

## [2026-06-16] ingest | Book — Frequently Asked Questions in Quantitative Finance (Paul Wilmott, Wiley 2009)
- Source: PDF (625 pages), extracted via pdfplumber to `C:\Users\dhara\AppData\Local\Temp\wilmott_faq.txt`; read in targeted chunks at key FAQ sections (Kelly #15, Perf Measures #19, Dynamic Hedging #41, Autocorrelation #42, Dispersion #43) and Chapters 3, 5
- Pages created: sources/Wilmott-FAQ-Quantitative-Finance, concepts/Kelly-Criterion, strategies/Dispersion-Trading
- Pages updated: concepts/Performance-Metrics (added Sortino, Treynor, M², Information Ratio, Wilmott's meta-critique), wiki/index.md (pages 52→55, sources 10→11)
- Key extractions: Kelly fraction f*=μ/σ² (continuous) or 2p−1 (binary); use half-Kelly in practice; Sharpe penalizes upside equally → use Sortino for skewed breakout strategies; dynamic hedging at implied vol → smooth P&L but path-dependent total; at actual vol → guaranteed profit but random daily swings; long gamma loses 68% of days (chi-square); dispersion = short index options + long stock options = short implied correlation; SAC (serial autocorrelation) identifies trend vs mean-reversion regime; 12 commonest mistakes (diversification, supply/demand, Jensen, parameter sensitivity, correlation, discrete hedging, feedback, closed-form reliance, non-linearity, calibration, precision, complexity); Modellers' Manifesto: no fundamental laws in finance, models are tools not world
- **Contradiction noted**: Wilmott's Lesson 5 (Correlation) warns that correlation breaks down in crises precisely when you depend on it. Dispersion trading is net short correlation → extreme tail risk in crashes. Not contradicted by other wiki content but flags that dispersion needs crash-protection sizing.
- **Alignment**: Wilmott's "no single trade should make or break you" = Kelly foundation for Minervini's 1.25–2.5% rule and Kalyan's 10% single-stock limit. All converge on the same principle.
- No overview.md update — foundational concepts ingest, no market thesis change

## [2026-06-15] ingest | Book — Think and Trade Like a Champion (Mark Minervini, Access Publishing 2017)
- Source: PDF (82 pages), extracted via pdftotext to `C:\Users\dhara\AppData\Local\Temp\minervini_champion.txt`, read in 8 chunks
- Pages created: sources/Minervini-Think-Trade-Champion, concepts/Stage-Analysis, strategies/Minervini-SEPA, concepts/Trading-Psychology-Champion
- Pages updated: concepts/VCP (footprint notation, base patterns, supply dynamics; sources 2→3), strategies/VCPBot-Trend-Template (corrected 7→8 conditions, full 8-criterion table), analyses/Kalyan-Trading-Philosophy (Minervini alignment section, 50/80 Rule, Trading Triangle, base count), wiki/index.md (pages 47→52, sources 9→10)
- Key extractions: SEPA framework (Stage Analysis + Trend Template + VCP + entry/exit rules); 8-condition Trend Template (prior wiki had 7 — missing RS rank ≥70 with uptrend ≥6 weeks, and price above 50-day on base emergence); VCP footprint notation `WW depth/final T_count`; 50/80 Rule for topped market leaders; Trading Triangle (avg win / avg loss / batting average); 8 Keys to Superperformance; champion mindset (mental rehearsal, box breathing, NLP pain/pleasure conditioning)
- **Contradiction flagged and resolved**: Minervini REQUIRES hard stops on every trade; Connors (ingested earlier) says stop-losses remove edge. Resolution: strategy-specific — Connors rule applies only to mean-reversion dip-buying, NOT to SEPA growth breakout trades. Documented in source page Contradictions section and Kalyan-Trading-Philosophy.
- No overview.md update — methodology ingest, no shift to current market thesis

## [2026-06-15] ingest | Chartink Screener — Darvas Volume Shockers (Amitabh Jha3)
- Source: https://chartink.com/screener/copy-amitabh-jha3-volume-shockers-stocks-with-rising-volumes-darvas-100; HTML fetched via curl, scan clause extracted from embedded `atlas_query` field in `scan-json` Vue prop
- Scan clause: `latest volume > sma(volume,10) * 2 AND (latest close > 1 day ago close * 1.05 OR latest close < 1 day ago close * 0.95)`
- Pages created: sources/Chartink-Darvas-Volume-Shockers-Screener
- Pages updated: strategies/Screener-Queries (new Chartink scanner #9), concepts/Darvas-Box (cross-link to screener)
- Key contrast with existing Chartink scanner #5 (Nimblr Volume Shocker): same 2× volume floor but this Darvas variant replaces CCI(34)>110 / volume upper cap / close>100 with a ±5% bidirectional price-move filter — broader activity radar, higher false-positive rate, requires trend/box filtering before acting
- No contradictions

## [2026-06-15] ingest | Guidebook — Trading Stocks and Options with Moving Averages: A Quantified Approach (Connors/Radtke, Connors Research 2013)
- Source: PDF (40 pages), extracted via `py -3` + pdfplumber to a temp .txt file and read in full (pdftoppm-based Read tool extraction failed; established as fallback pattern for future PDF ingests)
- Pages created: source page (Connors-MA-Quantified-Approach-2013), strategies/Quantified-MA-Mean-Reversion, concepts/ConnorsRSI
- Pages updated: concepts/RSI (cross-linked to ConnorsRSI, sources 0→1)
- Key extractions: dual-MA "Quantified MA Mean-Reversion" system (Setup: price>$5, avg vol>=250k, HV(100)>30, Close>MA(200), Fast MA >=Y% below Slow MA across 5 MA-pair scenarios; Entry: limit buy X% below prior close; Exit: First Up Close / ConnorsRSI>50 / ConnorsRSI>70 / Close>MA(3) / Close>MA(5)); ConnorsRSI(3,2,100) = avg(RSI(Close,3), RSI(Streak,2), PercentRank(ROC(1),100)); options section — front-month 1-2-strikes-ITM long call as stock substitute, 1 contract per 100 shares, same exit signal
- **Contradiction flagged**: book's backtests found stop-losses tend to reduce or remove this system's edge, in tension with stop-centric risk management in analyses/Kalyan-Trading-Philosophy, analyses/VCPBot-Risk-System, and sources/Dolzhenko-Algorithmic-Trading-Systems-2024 — documented in the new source page's Contradictions section, not yet resolved
- No overview.md update — new strategy methodology, no shift to current market thesis

## [2026-06-15] ingest | Book — Algorithmic Trading Systems and Strategies (Viktoria Dolzhenko, Apress 2024)
- Source: epub, copied to raw/ (Dolzhenko-Algorithmic-Trading-Systems-2024.epub), converted to text via Calibre (16,845 lines, ~25-30% read in depth, remainder skimmed — heavy software-architecture/.NET chapters deliberately not extracted)
- Pages created: source page (Dolzhenko-Algorithmic-Trading-Systems-2024), concepts/Capital-Management-Methods, concepts/Performance-Metrics, concepts/Genetic-Algorithm-Optimization, strategies/Systematic-Strategy-Search
- Pages updated: concepts/PMax (added "Trailing System Order" trailing-stop algorithm as an alternative to the ATR/Chandelier approach)
- Key extractions: Theory→SubTheory→Strategy entity model + 3-step coarse-to-fine strategy search with separate "quality condition" filter; full position-sizing catalogue (Kelly Criterion incl. ruin case study, Optimal f, Martingale/Anti-Martingale, Fixed Proportional/Ryan Jones delta); performance metrics (profit factor, 5 drawdown types, Sharpe, expected value); genetic algorithm operator catalogue (mutation/crossover/filtering/selection + constraint handling); "many modest strategies in parallel" portfolio philosophy
- No contradictions; book's diversification guidelines (<=10% per asset, <=20% per sector) independently match Kalyan's existing portfolio rules in analyses/Kalyan-Trading-Philosophy
- No overview.md update — methodology/system-design content, no market-thesis shift

## [2026-06-15] ingest | Chartink Dashboard — Atlas / Nimblr's Dashboard (7 screener widgets)
- Source: https://chartink.com/dashboard/261357 (widget opened: 4788842), HTML fetched via curl (JS-rendered dashboard, embedded `widgets` JSON attribute parsed for full scan-clause formulas)
- Pages created: source page (Chartink-Atlas-Nimblr-Dashboard), concepts/CCI (new — Commodity Channel Index, central to 6/7 scanners)
- Pages updated: strategies/Screener-Queries.md — Chartink Scanners section rewritten with full formulas for 8 scanners (4 previously link-only: Blockbuster 2.0, Accumulation Breakout, FII-DII Volume Interest, Volume Shocker; 3 new: Fundamental Multibagger+Breakout, 1Y All-Time Breakout, 3Y Breakout Scanner; Early Breakout left link-only)
- Key extractions: CCI(34)>100/110/133 as the common momentum trigger across scanners; Accumulation Breakout = CCI-gated VCP_1C variant; Blockbuster 2.0 embeds a PEG<1.5 (Lynch-style) valuation filter on top of golden-cross + YoY growth + CCI; 1Y/3Y Breakout scanners are looser chartink-native equivalents of EW-Flat-Bottom-Breakout; Volume Shocker and FII-DII Volume Interest both contain redundant no-op clauses (authoring quirks, not contradictions)
- No contradictions with existing wiki; CCI(34) and existing RSI bands noted as distinct oscillators usable in confluence
- No overview.md update — this is methodology/screener content, no market-thesis shift

## [2026-06-15] ingest | Book — Elliott Wave Techniques Simplified (Bennett McDowell, McGraw-Hill 2016)
- Source: epub, copied to raw/ (`Bennett McDowell - Elliot Wave Techniques Simplified (2015, McGraw Hill LLC) - libgen.li.epub`), converted to text via Calibre for full read
- Pages created: source page (EW-Techniques-Simplified-McDowell), concepts/McDowell-Probability-Matrix, strategies/EW-Flat-Bottom-Breakout, strategies/EW-Wave5-Catch
- Pages updated: concepts/Elliott-Wave (added classic Fibonacci percentile statistics for W2-W5, re-labeling trigger for >76.4% W4 retracements, OWL price-oscillator settings 5/35/low/histogram, PTF/RSI(9,80/20) band-penetration logic, 144-bar lookback, cross-links to MPM and new strategies)
- Key extractions: McDowell Probability Matrix (6-factor 0-5 wave-count confidence score, max 30, "grounded vs ungrounded" assessment principle); two named grounded setups (Flat Bottom Channel Breakout for Wave 3, Wave 5 Catch with 2:1 R:R + 3-bar trailing stop); crowd-psychology basis for the 5-3 wave structure
- No contradictions with existing wiki; RSI 80/20 band-penetration convention noted as distinct from existing concepts/RSI 40-80/20-60 regime ranges (both usable in separate panes)

## [2026-06-14] ingest | Pine Script — pmax_optimization.pine (Profit Maximizer Enhanced Strategy)
- Source: C:\Users\dhara\OneDrive\Documents\Python Scripts\pmax_optimization.pine (TradingView Pine v6, personal strategy by Kalyan)
- Pages created: source page (PMax-Optimization-Pine), concepts/PMax, concepts/Mansfield-RS, strategies/PMax-Confluence-Strategy
- Pages updated: concepts/Elliott-Wave (major addition — v2 pivot engine, forward projections, EW validity rules, Extension/Valuation/Earnings Power/Stage Analysis)
- Key extractions: PMax = adaptive MA ± 3xATR10 trailing stop; 16-factor confluence score (max 18 pts) drives graded decision matrix (STRONG BUY 100% @ ≥85% confluence down to EXIT @ <25%); stops = 2xATR10, targets = 2.5R; Mansfield RS vs benchmark (default SPY, should be NIFTY for Indian use); EW v2 engine auto-detects wave position and projects 36 forward Fibonacci targets

## [2026-06-14] ingest | Telegram channel — Finance With Sunil (t.me/FinanceWithSunil)
- Source: Public preview (t.me/s/FinanceWithSunil), SEBI-registered price-action channel, ~90.2K subs
- Pages created: source page (FinanceWithSunil-telegram), 5 entity pages (JAYBARMARU, SHRIRAMFIN, IOLCP, AUBANK, JASH) — all bias: watching
- Updated: wiki/index.md (sources + entities tables), wiki/overview.md (current watchlist)
- Key extractions: 5 pre-trigger momentum/breakout candidates with consistent "stop = breakout candle low" risk rule; educational topics (order blocks, gap up/down, consolidation, Fibonacci retracements) noted but full text not accessible via public preview — flagged for future re-ingest if fuller access is available

## [2026-06-14] init | Wiki initialized
- Directory structure created
- CLAUDE.md schema written
- Stub pages created: index.md, log.md, overview.md
- Wiki ready for first ingest

## [2026-06-14] ingest | trading_learning_raw.pdf (104 pages)
- Source: Personal trading research notes by Kalyan Dhara
- Pages created: 12 new wiki pages
- Concepts: Darvas-Box, CANSLIM, VCP, Elliott-Wave, KST, ADX, MACD-Divergence (+ updated RSI, EMA)
- Strategies: TechnoFunda-Swing (7-condition system), Screener-Queries (21 master screens)
- Analyses: Kalyan-Trading-Philosophy, Sector-Watchlist (15 sectors, defence zones)
- Key extractions: 21 Screener.in queries, Chartink scanner links, RSI regime rules, portfolio loss lesson (Jan 2025)

## [2026-06-14] ingest | VCPBot GitHub (https://github.com/blacckbeard4/VCPBot)
- Source: Open-source Python VCP trading bot by blacckbeard4
- Files read: README.md, vcp_detector.py (538 lines), scanner.py (525 lines)
- Pages created: VCPBot-github (source), VCPBot-Architecture (analysis), VCPBot-Risk-System (analysis), VCPBot-Trend-Template (strategy)
- Pages updated: VCP concept (major update — algorithmic 3-tier detection logic added)
- Key extractions: 3-tier hierarchical VCP algorithm, Minervini 7-condition trend template, RS rank dual-gate formula, regime-aware risk sizing, RVOL/gap confirmation filters, full tech stack
