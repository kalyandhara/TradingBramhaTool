---
title: "GitHub — Shubhamsaboo/awesome-llm-apps"
category: source
tags: [claude-code, llm-agents, github, tutorial-collection, finance-demo]
created: 2026-07-02
updated: 2026-07-02
sources: 1
related:
  - sources/GitHub-claude-trading-skills-tradermonty
  - sources/GitHub-ai-trading-claude-zubair
  - sources/GitHub-TradingAgents-TauricResearch
  - concepts/Agent-Loop-Design.md
---

# GitHub repo — Shubhamsaboo/awesome-llm-apps

## Metadata
- Author: Shubhamsaboo (creator of the Agno/Phidata agent framework)
- URL: https://github.com/Shubhamsaboo/awesome-llm-apps
- License: Apache-2.0
- Stars: ~116k, 17.3k forks — very large "awesome list"-style repo, 1,000+ commits, actively maintained
- Ingest trigger: Kalyan pasted the repo URL directly, no other context

## Key Takeaways

- **This is a tutorial/template catalog, not a trading system** — 100+ small, standalone example agents across 15 categories (Starter Agents, Advanced Agents, Always-on Agents, Multi-agent Teams, Voice Agents, RAG Tutorials, Agent Skills, MCP integrations), each demonstrating an agent-framework pattern using finance (or another domain) as a convenient example, not because the finance content itself is the point.
- **Checked the flagship finance example directly rather than trusting the category label**: "AI Finance Agent Team" is explicitly described by its own README as "a team of AI agents... using GPT-4o in just 20 lines of Python code" — a framework-orchestration demo (Web Agent + Finance Agent + a coordinating Team Agent, yfinance + DuckDuckGo as data sources, SQLite for interaction history). No stated methodology, no explicit buy/sell logic documented, no backtesting — a wiring demonstration, not a strategy.
- **Materially shallower than the three trading-agent repos already in this wiki** ([[sources/GitHub-claude-trading-skills-tradermonty]], [[sources/GitHub-ai-trading-claude-zubair]], [[sources/GitHub-TradingAgents-TauricResearch]]), all of which have actual documented methodology (VCP/CANSLIM rules, a 5-agent weighted scoring system, an academically-grounded bull/bear-debate pipeline respectively). This repo's finance folder (AI Finance Agent Team, AI Investment Agent, AI Financial Coach Agent, xAI Finance Agent, Earnings Call Analyst Agent, AI VC Due Diligence Agent Team) reads as a set of similarly shallow framework demos, not independently verified here beyond the one checked.
- **The genuinely reusable part is architectural, not financial**: the "Multi-agent Teams" and "Always-on Agents" categories are potentially relevant to this project's own automation (the daily Screener Pipeline already runs on a schedule via Task Scheduler) — but not confirmed to contain anything beyond what [[concepts/Agent-Loop-Design]] already covers from the Karpathy LOOPS.md ingest.

## Detailed Notes

Technical stack: Python 53.9% (core agent logic), TypeScript 21.9% + JavaScript 16.6% (frontend/generative-UI examples). Supports multiple model providers (Claude, Gemini, OpenAI, xAI, Llama, Qwen) — genuinely provider-agnostic rather than tied to one vendor. Everything links out to tutorials on the author's "Unwind AI" platform, confirming the educational/reference intent over a production trading claim.

## Actionable Insights

- **Not recommended as a trading-methodology source** — the finance examples are shallow relative to what's already documented in this wiki from more substantive repos. Don't treat "100+ apps, 116k stars" as a signal of trading depth; it's a signal of framework-tutorial breadth.
- **Worth a narrower look only if**: (a) evaluating the Agno/Phidata framework itself for building a new multi-agent tool in this project, or (b) specifically checking the "Always-on Agents" or "MCP AI Agents" categories for a scheduling/persistence pattern better than what `screener_pipeline.py` + Task Scheduler already does — neither confirmed here, both would need a dedicated follow-up look rather than assuming value from the category name.

## Contradictions with Existing Wiki

None — no methodology claims made strongly enough here to conflict with anything.

## Pages Updated

None — this ingest didn't surface anything strong enough to warrant changing another page; recorded as a source for future reference (e.g. if evaluating the Agno framework specifically) rather than acted on now.
