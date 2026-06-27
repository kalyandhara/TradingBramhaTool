---
title: "GitHub — zubair-trabzada/ai-trading-claude"
category: source
tags: [claude-skills, composite-score, trade-score, multi-agent, buy-sell-signal, design-contrast]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [sources/GitHub-claude-trading-skills-tradermonty, concepts/Capital-Management-Methods, concepts/Support-Resistance]
---

# Source — GitHub: zubair-trabzada/ai-trading-claude

## Metadata
- **Source type**: Open-source GitHub repository — a Claude Code skills package for stock analysis/research
- **URL**: https://github.com/zubair-trabzada/ai-trading-claude
- **Install**: single-command shell installer; Python 3.8+ and `reportlab` for PDF generation; no proprietary data subscriptions or brokerage API keys — relies on "publicly available information gathered via web search" at analysis time, plus the Anthropic Claude API itself.
- Explicitly positioned as "a research and analysis tool," "not a trading bot" — does not execute trades or connect to a brokerage.

## Key Takeaways

### What it does
16 commands under a `/trade` namespace, grouped into Analysis & Research (`analyze`, `quick`, `technical`, `fundamental`, `sentiment`, `sector`), Thesis & Strategy (`thesis`, `compare`, `options`, `earnings`), Portfolio & Risk (`portfolio`, `risk`, `screen`, `watchlist`), and Reporting (`report-pdf`, a 6-page PDF with score gauges).

`/trade analyze <ticker>` is the flagship command: it dispatches **5 parallel agents** (Technical, Fundamental, Sentiment, Risk, Thesis), each scoring its own dimension, then combines them into a single composite **Trade Score (0–100)**:

| Category | Weight | Measures |
|---|---|---|
| Technical Strength | 25% | Trend, momentum, volume, patterns, support/resistance |
| Fundamental Quality | 25% | Valuation, growth, profitability, balance sheet, moat |
| Sentiment & Momentum | 20% | News tone, social buzz, analyst consensus, insider signals |
| Risk Profile | 15% | Volatility, drawdown, correlation, liquidity |
| Thesis Conviction | 15% | Catalyst clarity, timeline, asymmetry, edge |

That score maps directly to a letter grade and an explicit trading signal: 85–100 → A+/Strong Buy, 70–84 → A/Buy, 55–69 → B/Hold, 40–54 → C/Caution, 25–39 → D/Caution, 0–24 → F/Avoid. Example output shown in the README for AAPL: Trade Score 74/100 (Grade A, Signal BUY), entry range $178–182, target $198–205, stop $168, 2.8:1 risk/reward.

### ⚠ Important design contrast — worth flagging explicitly
This tool's entire output format is **the opposite design philosophy** from the stock-analysis Claude Skill already built in this project (`skills/stock-analysis/SKILL.md`). That skill's non-negotiable rule #4 is *"No buy / sell / hold / target price. Ever... The decision is always the user's"* — explicitly because a fundamentals view should inform, not replace, the user's own judgment. This repo does the reverse on every axis:
- Produces an explicit **Buy/Hold/Avoid signal**, not just a fundamentals read.
- Produces an explicit **target price and stop**, not just levels for the user's own study.
- `/trade compare <t1> <t2>` issues "an explicit winner recommendation" — directly contrary to this wiki's own stock-analysis skill, which was deliberately built to **never** name a winner in Compare mode ("Do not name a 'winner' or say which to buy").

This isn't a flaw in either tool — they're solving different problems for different users. But it's worth being deliberate: if any ideas from this repo are ever borrowed into the project's own skill, the verdict/signal/winner-declaration parts should **not** be ported, only the underlying analytical structure (the five-dimension scoring framework, the parallel-agent architecture, the report format).

### Other structural notes
- **Data sourcing model differs sharply from the tradermonty repo** ([[sources/GitHub-claude-trading-skills-tradermonty]]): no FMP/FINVIZ/Alpaca integration at all — this tool leans entirely on live web search at analysis time, which is faster to set up (no API keys) but has no structured-data guarantees and is presumably more exposed to the same "aggregator silently omits a field" failure mode already documented from this project's own screener-scraping work.
- The Risk Profile dimension (volatility, drawdown, correlation, liquidity) and the dedicated `/trade risk` command (position sizing, max drawdown, scenario analysis, R:R) overlap conceptually with [[concepts/Capital-Management-Methods]]'s ATR-stop and trade-plan sections, though the repo doesn't specify its exact sizing formula.
- `/trade sector <sector>` (sector momentum, relative strength, fund flows, top/bottom performers) is functionally similar in spirit to this wiki's own [[strategies/Sector-Liquidity-Rotation]] and to SwingEdge's Sector Momentum Map, though again with no specified data methodology — can't compare formulas without deeper inspection of the skill files themselves.

## Actionable Insights
- If extending the stock-analysis skill with a Compare or sector-level mode, this repo's five-dimension weighting table (Technical 25 / Fundamental 25 / Sentiment 20 / Risk 15 / Thesis 15) is a reasonable structural reference for *organizing* an analysis — but the existing skill's no-verdict rule should be kept, overriding this repo's buy/sell/winner output style.
- Worth a closer look at the actual skill files (not just the README) if a deeper structural comparison is wanted — this ingest is based on the README and didn't inspect the individual `/trade *` skill implementations themselves.

## Contradictions with Existing Wiki
- **Direct philosophical contradiction with this project's own stock-analysis Claude Skill**: that skill explicitly forbids buy/sell/hold calls, target prices, and naming a "winner" in comparisons — this repo's entire value proposition is producing exactly those things. Not an error in either source, but flagged here so future work doesn't accidentally blend the two design philosophies without a deliberate decision.
- See [[sources/GitHub-TradingAgents-TauricResearch]] for a three-way automation-spectrum comparison (advisory-only → verdict-generating → execution-simulating) across all three trading-related GitHub repos ingested into this wiki.

## Pages Updated
- This source page only.
