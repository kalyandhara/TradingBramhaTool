---
title: "SwingEdge — Process, Risk & Workflow Lessons (Learn series, 12 lessons)"
category: source
tags: [education, risk-management, entries, exits, workflow, psychology, multi-timeframe, pyramiding]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [concepts/Capital-Management-Methods, concepts/Multi-Timeframe-Analysis, concepts/Anchored-VWAP-Pyramiding, concepts/Distribution-Days, concepts/VCP, strategies/False-Break-Buildup-Trading, strategies/Screener-Queries, analyses/Kalyan-Trading-Philosophy, concepts/Trading-Psychology-Champion]
---

# Source — SwingEdge "Learn" Process/Risk/Workflow Cluster (12 lessons)

## Metadata
- **Source type**: Educational articles, 12 of the 22 lessons in SwingEdge's Learn curriculum (see [[sources/SwingEdge-Learn-Intro-Swing-vs-Day]] for the full catalog)
- **URLs**: `/learn/risk-stops-sizing`, `/learn/entries-pivots-pullbacks`, `/learn/advanced-swing-patterns`, `/learn/targets-exits`, `/learn/trade-plan-r-multiple`, `/learn/volume-price-confirmation`, `/learn/market-regime-relative-strength`, `/learn/scanner-to-trade-workflow`, `/learn/psychology-process`, `/learn/multi-timeframe-alignment`, `/learn/advanced-trailing-exits`, `/learn/anchored-vwap-pyramiding`
- **Ingested**: 2026-06-22. Combined with [[sources/SwingEdge-Learn-Indicators-Deep-Dive]] (6 indicator lessons), this completes all 22 lessons in the catalog.

## Where each lesson's content landed

| Lesson | Disposition |
|---|---|
| Risk & position size | Reinforces [[concepts/Capital-Management-Methods]] (fixed-fractional R math, "round-number stops get picked off," correlated-position sizing) and [[analyses/Kalyan-Trading-Philosophy]] (drawdown/emotional-capital calibration) — no new mechanics beyond what's already merged there |
| Entries: pivots & pullbacks | Two entry templates — breakout participation (close through level + range/volume expansion, prefer day-2 hold over one-day spikes) and pullback participation (shallow rising-lows pullback, volume dry-up then re-expand) — cross-references [[strategies/False-Break-Buildup-Trading]] and [[concepts/VCP]]; no new concept page needed |
| Advanced: HTF, VCP & contraction | High-tight-flag, VCP-style contraction counting, cup-with-handle, ascending bases — all already covered by [[concepts/VCP]]'s 3-tier detection; this lesson's contribution is mostly liquidity/float/event-risk caveats layered on top |
| Targets & exits | Target-anchoring to structure (measured moves, prior highs), partial-profit ladders, time/thesis-based exits, gap/event risk on exit day — merged into [[concepts/Capital-Management-Methods]]'s new "Trailing-Exit Systems" section |
| Trade plan & R-multiple | The five-line trade plan template and R-multiple review discipline — merged into [[concepts/Capital-Management-Methods]] |
| Volume & price confirmation | Volume dry-up before a move vs. dry-up after a collapse (different meanings); expansion-on-breakout as proof of institutional participation; weak-volume breakout + close-back-inside-base as a caution flag — directly parallels [[concepts/Distribution-Days]]'s volume z-score framework, just from the bullish-confirmation side rather than the bearish-distribution side |
| Choose setups by market regime | Index/sector/breadth checklist (is the index above key MAs, are sector leaders breaking out together, is the watchlist producing quality setups or only marginal names) — reinforces the index-level ADX regime-gate already added to [[concepts/ADX]] |
| Scanner to trade workflow | 4-step validate→reject→journal workflow ("reject more than you accept" — of 50 candidates, the job is to find the handful with clean structure) — operational elaboration of the "scanners are interns" framing already captured in [[sources/SwingEdge-Learn-Trends-Stages]] |
| Process & mindset | Minimum-viable journal fields (date/symbol/direction/entry/stop/target/size/R, chart screenshot, exit outcome in R, emotional tag) and self-protective rules (max concurrent positions, cooling-off after 2 losses, hard daily/weekly loss cap) — extends the review-cadence checklist already captured in [[sources/SwingEdge-Learn-Intro-Swing-vs-Day]] with concrete journal schema and circuit-breaker rules; worth folding into [[analyses/Kalyan-Trading-Philosophy]] or [[concepts/Trading-Psychology-Champion]] if a journaling system is ever built |
| Multi-timeframe analysis | Full new concept page: [[concepts/Multi-Timeframe-Analysis]] |
| Advanced trailing exits | Merged into [[concepts/Capital-Management-Methods]]'s "Trailing-Exit Systems" section (structural/MA/ATR-chandelier/parabolic-SAR/Supertrend comparison table) |
| Anchored VWAP & pyramiding | Full new concept page: [[concepts/Anchored-VWAP-Pyramiding]] |

## Key Takeaways Worth Calling Out Explicitly
- **"Reject more than you accept"** (scanner-to-trade-workflow): screening is mostly rejection, not selection — if 50 names surface, the job is to eliminate down to a handful with clean structure, acceptable liquidity, and a stop that makes sense, not to trade all 50. Directly actionable against this wiki's own screener tooling (`tools/sector_rotation.py`, `tools/multibagger_candidates.py`) — those produce candidate lists, not trade lists.
- **Journal schema** (psychology-process): a concrete, ready-to-use field set (date, symbol, direction, entry, planned stop, planned target/trail rule, size, R at risk, chart screenshot, actual exit, outcome in R, process-quality note, emotional tag) — worth implementing literally if/when a trade journal is built for this portfolio.
- **Volume dry-up has two different meanings** depending on where in the cycle it occurs: dry-up *while price stays tight* inside a base is constructive (sellers losing willingness to hit bids lower); dry-up *after a collapse* can simply mean lack of demand, not stored energy. This distinction wasn't explicit in [[concepts/Distribution-Days]] and is worth keeping in mind when reading any future "ATR shrinking" / "BB squeeze" flag from a SwingEdge stock-detail page — context (post-advance base vs. post-decline drift) changes the read.
- **Breakout participation vs. pullback participation are explicitly named as the two swing-entry templates** with different psychological costs ("breakouts feel late; pullbacks feel clever until they keep falling") — a clean two-bucket framing for entry-style classification.

## Actionable Insights
- Consider implementing the journal schema literally (it's specific enough to use as-is) the next time a live trade is logged in this wiki via the TRADE LOG operation.
- The "reject more than you accept" framing is worth citing explicitly whenever sector_rotation.py or multibagger_candidates.py output is reviewed — the tool's job ends at the candidate list, not the trade decision.

## Contradictions with Existing Wiki
- None — this batch is uniformly reinforcing/elaborating, not contradicting.

## Pages Updated
- [[concepts/Multi-Timeframe-Analysis]], [[concepts/Anchored-VWAP-Pyramiding]] — created
- [[concepts/Capital-Management-Methods]] — trailing-exits and five-line trade plan sections added
- This source page (no further edits made to Distribution-Days, Screener-Queries, or Trading-Psychology-Champion — captured as cross-references here instead, to avoid over-editing pages for incremental restatements of points already on record)
