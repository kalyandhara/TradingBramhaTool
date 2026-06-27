---
title: "GitHub — TauricResearch/TradingAgents"
category: source
tags: [multi-agent, llm-trading, bull-bear-debate, langgraph, nse-compatible, research-framework, trade-memory]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [sources/GitHub-claude-trading-skills-tradermonty, sources/GitHub-ai-trading-claude-zubair, concepts/Capital-Management-Methods]
---

# Source — GitHub: TauricResearch/TradingAgents

## Metadata
- **Source type**: Open-source, academically-grounded multi-agent LLM trading framework (LangGraph-based)
- **URL**: https://github.com/TauricResearch/TradingAgents
- **Research basis**: Published on arXiv (2412.20138), with a follow-up technical report "Trading-R1" (arXiv 2509.11420) — unlike the two prior GitHub ingests, this one has an actual academic paper behind it, not just a README.
- **Requirements**: Python 3.12, API keys for whichever LLM provider is configured; Docker Compose support included.
- **LLM provider support is unusually broad**: OpenAI, Google Gemini, Anthropic Claude, xAI Grok, DeepSeek, Qwen, GLM, MiniMax, OpenRouter, Ollama, AWS Bedrock, or any OpenAI-compatible endpoint — this is provider-agnostic infrastructure, not a Claude-specific skill package like the two prior ingests.

## Key Takeaways

### Architecture — a simulated trading firm, not just an analysis tool
This is structurally the most ambitious of the three trading-related repos ingested so far. It models an entire firm hierarchy as a LangGraph pipeline:

1. **Analyst Team** (4 roles, parallel): Fundamentals Analyst, Sentiment Analyst (aggregates news/StockTwits/Reddit), News Analyst (global news + macro indicators), Technical Analyst (MACD/RSI-style indicators — cf. this wiki's [[concepts/MACD-Divergence]] and [[concepts/RSI]]).
2. **Researcher Team**: explicit **bullish researcher vs. bearish researcher**, who run a structured, multi-round debate (`max_debate_rounds` config) over the Analyst Team's findings — the closest thing in any of these three repos to a genuine adversarial self-check built into the architecture itself, rather than a single-pass composite score.
3. **Trader Agent**: synthesizes the analyst reports and the debate outcome into a trade decision (timing + magnitude).
4. **Risk Management**: assesses portfolio-level volatility/liquidity/risk factors.
5. **Portfolio Manager**: the final gate — approves or rejects the Trader's proposal, and only approved orders reach the (simulated) exchange.

This is a genuine multi-stage approval pipeline with a built-in adversarial step (bull vs. bear debate) before any decision — structurally different from both prior ingests, which compute a single weighted composite score without an internal disagreement step.

### ⚠ Third point on the buy/sell-verdict design-philosophy spectrum
Now three GitHub repos compared on this axis:
| Repo | Verdict style |
|---|---|
| [[sources/GitHub-claude-trading-skills-tradermonty]] | No automated verdict — skills inform a human-authored decision; explicitly "humans retain all buy/sell authority" |
| [[sources/GitHub-ai-trading-claude-zubair]] | Explicit Buy/Hold/Avoid signal + target price + named "winner" in Compare mode |
| **TradingAgents** | **Actually executes the trade decision** (on a simulated exchange) — this isn't even an advisory verdict, it's a full closed-loop paper-trading pipeline with its own Portfolio Manager veto gate |

TradingAgents sits at the far end of automation among the three: it doesn't just recommend, it runs a simulated execution step. Worth keeping this spectrum in mind (advisory-only → verdict-generating → execution-simulating) when evaluating any future framework against this project's own stock-analysis skill, which sits firmly at the advisory-only end by design.

### Data sources and market coverage
- **Market data**: Yahoo Finance, Alpha Vantage. **Social/news**: StockTwits, Reddit, news headlines. **Alternative data**: FRED (macro), Polymarket (prediction markets).
- **Explicitly confirmed NSE/BSE compatibility**: the README lists Indian tickers with exchange suffixes — `RELIANCE.NS, .BO` — alongside Hong Kong, Tokyo, London, Canada, Australia, China A-shares, and crypto. The framework works on "any market Yahoo Finance covers, using the exchange-suffixed ticker," which is the same Yahoo Finance ticker convention this project's own `tools/sector_rotation.py` already relies on for sector-index data (`.NS` suffix). **This is the most directly actionable finding from this ingest** — it means this framework could in principle be pointed at NSE tickers without modification, unlike the prior two repos which are US-equity-only.
- **Persistent decision memory**: logs to `~/.tradingagents/memory/trading_memory.md`. On a later run for the *same* ticker, it retrieves the realized return (raw and alpha vs. SPY) from the prior decision and injects "recent same-ticker decisions plus recent cross-ticker lessons" into the Portfolio Manager's prompt on the next run — a learning-across-runs mechanism. This is conceptually the same idea as `trader-memory-core` from the tradermonty repo and the journal-schema captured from [[sources/SwingEdge-Learn-Process-Risk-Workflow]], but implemented as an automatic prompt-injection loop rather than a human-reviewed journal.
- **Checkpoint/resume**: LangGraph persists state after each node, so an interrupted run resumes rather than restarts — a practical engineering detail worth noting for any long multi-agent pipeline.
- **No benchmark numbers are published** — the repo explicitly disclaims that backtest results aren't guaranteed to reproduce any published figure; treat any performance claims about this framework found elsewhere with appropriate skepticism until verified directly.

## Actionable Insights
- The **bull-vs-bear structured debate** step is a genuinely different idea from anything in the two prior repo ingests or this wiki's existing tooling — worth considering as a design pattern for any future analysis skill in this project: instead of one model producing a single read, have two adversarial passes (one arguing the bull case, one the bear case) and force them to engage with each other's points before a synthesis step. This maps loosely to "Evidence For / Evidence Against" sections already used in this wiki's `analyses/` page template, just automated and adversarial rather than a single author's two-column list.
- The alpha-vs-SPY realized-return tracking on repeat runs is worth comparing against this wiki's own R-multiple review discipline ([[concepts/Capital-Management-Methods]]) — both are trying to solve "did this call actually work," just one is automatic/per-run and the other is manual/per-trade.
- Confirmed NSE/BSE ticker compatibility (`.NS`/`.BO` suffixes) makes this the only one of the three ingested trading-agent repos that's directly relevant to Indian equities without modification — worth a deeper look if a multi-agent debate-style analysis pipeline is ever wanted for this project, rather than building one from scratch.

## Contradictions with Existing Wiki
- None directly, but reinforces the advisory-only design choice already made for this project's stock-analysis skill by showing the far end of the automation spectrum (simulated execution) as a deliberate contrast, not a model to imitate without modification — that framework's Portfolio Manager veto gate and simulated exchange execution go further than this project's tooling is meant to go.

## Pages Updated
- This source page only.
