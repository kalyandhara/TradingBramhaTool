# Wiki Log
<!-- Append-only. Newest entries at top. Format: ## [YYYY-MM-DD] operation | description -->

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
