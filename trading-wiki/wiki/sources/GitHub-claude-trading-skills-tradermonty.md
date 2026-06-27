---
title: "GitHub — tradermonty/claude-trading-skills"
category: source
tags: [claude-skills, toolkit, vcp, canslim, market-regime, position-sizing, trade-journal, us-equities]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [concepts/VCP, concepts/CANSLIM, concepts/Distribution-Days, concepts/Stage-Analysis, concepts/Capital-Management-Methods, concepts/Trading-Psychology-Champion, analyses/Kalyan-Trading-Philosophy, analyses/VCPBot-Architecture]
---

# Source — GitHub: tradermonty/claude-trading-skills

## Metadata
- **Source type**: Open-source GitHub repository — a Claude Skills toolkit for equity trading/investing workflows
- **URL**: https://github.com/tradermonty/claude-trading-skills
- **Scale**: 70+ skills, 2,000+ stars, 486 forks, 517+ commits, MIT license
- **Market focus**: US equities (S&P 500 / Nasdaq-style screeners, FMP/FINVIZ/Alpaca APIs) — **not** NSE/BSE. Useful as a methodology and architecture reference for this wiki's Indian-market tooling, not a direct drop-in data source.

## Key Takeaways
- This is the most directly relevant external project to this wiki's own `tools/` directory found so far: it's a parallel, far more mature attempt at exactly the kind of thing this vault has been building piecemeal (`sector_rotation.py`, `multibagger_candidates.py`, the SwingEdge stock-analyzer skill) — a Claude-Skills-based trading decision toolkit, explicitly **not** an automated/signal-trading system ("humans retain all buy/sell authority").
- **Organized into 7 functional categories** (Market Regime, Core Portfolio, Swing Opportunity, Trade Planning, Trade Memory, Strategy Research, Advanced/Satellite) plus a **Meta** category of skills that manage the *other* skills — this last category is the most novel part, see below.
- **Embeds the same core methodologies already documented in this wiki, as named, runnable skills**: Minervini's VCP (→ [[concepts/VCP]]), William O'Neil's CANSLIM + Follow-Through Day + Distribution Days (→ [[concepts/CANSLIM]], [[concepts/Distribution-Days]]), Stockbee momentum bursts, and a Druckenmiller-style macro-to-micro conviction score aggregating 8 upstream signals. Confirms these are mainstream, productionized methodologies, not idiosyncratic interpretations.
- **A documented "no-API path"**: five core skills (breadth analysis, uptrend analysis, position sizing, memory tracking, postmortem review) work from public CSVs and local journaling alone, with FMP (Financial Modeling Prep, free tier 250 req/day), FINVIZ Elite, and Alpaca as optional/required upgrades for screening and portfolio-sync features. Worth comparing against this wiki's own screener.in-cookie-based workaround — FMP-style structured APIs would have been a much cleaner data path if a NSE-equivalent existed.
- **Workflows** (YAML manifests in a `workflows/` directory) chain multiple skills into a repeatable sequence with decision gates and named artifacts — e.g. `market-regime-daily` (no API needed), `swing-opportunity-daily` (needs FMP), `trade-memory-loop` (no API), `monthly-performance-review` (no API). This is a more formalized version of what this wiki's own multi-script pipelines (sector_rotation → sector_rotation_trail → promoter_profit_surprise, all merging into one Excel workbook) are already doing informally.

## Notable Skills Worth Studying for This Wiki's Own Tooling

| Skill | What it does | Relevance here |
|---|---|---|
| `kanchi-dividend-review-monitor` | Forces a periodic portfolio review **without ever auto-selling** — a review trigger, not a trade trigger | Directly applicable design pattern: a "check this" alert is safer to automate than a "do this" action |
| `trader-memory-core` | Tracks an investment thesis across its full lifecycle (entry rationale → updates → exit → outcome) | Matches the journal-schema idea already captured from [[sources/SwingEdge-Learn-Process-Risk-Workflow]] — this is effectively the productionized version of that journal concept |
| `signal-postmortem` / `trade-performance-coach` | Structured post-trade review, separate from raw P&L — process quality over outcome | Same spirit as the review-cadence checklist from [[sources/SwingEdge-Learn-Intro-Swing-vs-Day]] |
| `dual-axis-skill-reviewer` | Scores a *skill itself* (not a trade) on deterministic code checks + optional LLM review | A genuinely new idea for this wiki's context: applying the same rigor to the analysis tooling as to the trades it produces — directly relevant to maintaining `tools/*.py` and the stock-analysis Claude Skill in this project |
| `position-sizer` | Risk-based position sizing for long stock trades | Worth comparing formula/defaults against [[concepts/Capital-Management-Methods]]'s ATR-stop and fixed-fractional sections |
| `institutional-flow-tracker` | Tracks institutional ownership changes from US 13F filings | The US-market equivalent of this wiki's own FII/DII holding-change self-sourcing methodology (see [[strategies/Sector-Liquidity-Rotation]]) — same underlying idea, different regulatory filing |
| `vcp-screener`, `canslim-screener`, `breakout-trade-planner` | Automated VCP/CANSLIM screening + Minervini-style breakout trade-plan generation | Direct implementation reference for anything extending this wiki's [[concepts/VCP]] coverage into actual screening code |
| `macro-regime-detector`, `market-top-detector`, `us-market-bubble-detector` | Structural macro regime shifts, market-top probability scoring, Minsky/Kindleberger bubble-risk framework | A more systematic version of the "market regime" checklist already captured from SwingEdge's Learn series |

## The "Meta" Skill Category — Self-Maintaining Tooling
The most structurally novel part of this repo: skills whose job is to manage the other skills, not analyze markets —
- **Skill Idea Miner**: mines Claude Code session logs for skill-idea candidates (a direct analogue to this wiki's own "ingest a source → notice a pattern → spawn a new concept page" workflow, just automated)
- **Skill Designer**: designs new skills from structured specs
- **Dual-Axis Skill Reviewer**: quality-scores skills (0–100), with an automated daily pipeline applying improvements when scores fall below 90 and opening a GitHub PR for human review
- **Skill Integration Tester**: validates multi-skill workflows and data contracts between them
- **Trading Skills Navigator**: recommends which workflow/skillset fits a natural-language goal

This "self-improvement loop" pattern (mine → design → review → auto-PR) is worth keeping in mind if this project's own tooling (`tools/*.py`, the stock-analysis skill) grows large enough to need the same kind of meta-maintenance.

## Actionable Insights
- If this project ever needs a US-equity reference implementation (e.g. for the Compare mode in the stock-analysis skill, or to sanity-check methodology against a more mature codebase), this repo is the best external reference found so far — it implements the same VCP/CANSLIN/Distribution-Days/position-sizing concepts already in this wiki as actual runnable code with FMP-backed data.
- The "review trigger without an auto-sell trigger" pattern from `kanchi-dividend-review-monitor` is a safer automation template than anything that initiates a trade — worth adopting as a design principle for any future automation added to this project's own tools.
- Not a data source for Indian equities — its API integrations (FMP, FINVIZ, Alpaca) are US-market-specific. The methodology transfers; the plumbing does not.

## Contradictions with Existing Wiki
- None — this is independent confirmation that the wiki's existing core methodologies (VCP, CANSLIM, Distribution Days, FII/DII-style institutional flow tracking, position sizing) are mainstream and already productionized elsewhere, not idiosyncratic.
- See [[sources/GitHub-TradingAgents-TauricResearch]] for a three-way automation-spectrum comparison across all three trading-related GitHub repos ingested into this wiki — this repo sits at the advisory-only end ("humans retain all buy/sell authority").

## Pages Updated
- This source page only — no existing concept pages required edits, since this repo confirms rather than extends the underlying methodology; cross-links recorded here point to where each skill's concept already lives in this wiki.
