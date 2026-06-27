# Trading Wiki — Schema & Agent Instructions

> This file tells the LLM how this wiki is structured, what conventions to follow,
> and what to do during every operation. Read this file at the start of every session.

## Mission

You are the curator and maintainer of a personal trading knowledge base.
Your job is to read sources, extract trading-relevant knowledge, and integrate it
into a persistent wiki that compounds over time. The human curates sources and
asks questions. You do all the writing, cross-referencing, filing, and maintenance.

---

## Directory Layout

```
C:\Users\dhara\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\
├── CLAUDE.md              ← this file (schema + instructions)
├── wiki/
│   ├── index.md           ← master catalog of all wiki pages
│   ├── log.md             ← append-only operation log
│   ├── overview.md        ← high-level synthesis / current market thesis
│   ├── entities/          ← stocks, indices, ETFs, brokers, people
│   ├── concepts/          ← TA patterns, indicators, macro concepts
│   ├── strategies/        ← trading strategies, setups, systems
│   ├── sources/           ← one summary page per ingested source
│   └── analyses/          ← trade analyses, post-mortems, research outputs
├── raw/
│   ├── assets/            ← downloaded images, charts
│   └── [source files]     ← articles, PDFs, screenshots, notes (immutable)
└── tools/
    └── search.py          ← optional search helper (build when needed)
```

---

## Page Conventions

### Frontmatter (YAML, required on every wiki page)
```yaml
---
title: "Page Title"
category: entity | concept | strategy | source | analysis
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: 0          # number of source documents that informed this page
related: []         # list of linked pages (wiki-relative paths)
---
```

### Cross-linking
- Always use wiki-relative links: `[[concepts/RSI]]` or `[RSI](../concepts/RSI.md)`
- Every page must link to at least 2 other pages when possible
- Orphan pages (no inbound links) should be flagged during lint

### Entity Pages (`wiki/entities/`)
For stocks, indices, ETFs:
```
# TICKER — Full Name
## Profile
## Price & Chart Context
## Key Levels (Support / Resistance)
## Catalysts & News
## Linked Strategies
## Notes & Observations
## Sources
```

### Concept Pages (`wiki/concepts/`)
For indicators, patterns, macro themes:
```
# Concept Name
## Definition
## How to Use
## Variants / Parameters
## Common Mistakes
## Related Concepts
## Examples in This Wiki
## Sources
```

### Strategy Pages (`wiki/strategies/`)
```
# Strategy Name
## Core Idea
## Setup Criteria
## Entry Rules
## Exit Rules (profit target + stop loss)
## Timeframe
## Best Market Conditions
## Worst Market Conditions
## Backtest / Track Record
## Examples
## Related Concepts
## Sources
```

### Source Pages (`wiki/sources/`)
```
# [Source Type] — Title
## Metadata
- Author, Date, URL/file
## Key Takeaways (3–7 bullets)
## Detailed Notes
## Actionable Insights
## Contradictions with Existing Wiki
## Pages Updated
```

### Analysis Pages (`wiki/analyses/`)
For trade post-mortems, market reads, research:
```
# Analysis: Topic — Date
## Thesis
## Evidence For
## Evidence Against
## Conclusion
## Action Taken / Plan
## Outcome (fill in later)
## Related Pages
```

---

## Operations

### 1. INGEST (new source added to raw/)
When told to ingest a source:
1. Read the source fully
2. Discuss key takeaways with the human (unless batch mode)
3. Create a source summary page in `wiki/sources/`
4. Update or create entity/concept/strategy pages touched by this source
5. Update `wiki/index.md` with the new page(s)
6. Update `wiki/overview.md` if the source shifts the overall thesis
7. Append an entry to `wiki/log.md`:
   `## [YYYY-MM-DD] ingest | Source Title`

**Trading-specific ingest checklist:**
- Extract any specific price levels, targets, or stops mentioned
- Note the author's market bias (bullish/bearish/neutral)
- Flag if the source contradicts existing wiki claims
- Identify which tickers/sectors are covered → update entity pages
- Identify which setups/patterns are discussed → update strategy/concept pages

### 2. QUERY (human asks a question)
1. Read `wiki/index.md` to find relevant pages
2. Read those pages in full
3. Synthesize an answer with citations to wiki pages and/or sources
4. If the answer is valuable, offer to file it as an analysis page
5. Append to log: `## [YYYY-MM-DD] query | Question summary`

**Output formats available:**
- Markdown narrative (default)
- Comparison table (e.g. two strategies side-by-side)
- Trade plan (entry / stop / target / rationale)
- Markdown chart notes (describe chart levels and patterns in text)

### 3. LINT (wiki health check)
Run periodically or on request:
- Flag pages not updated in 30+ days with stale info
- Find orphan pages (no inbound links)
- Find concepts mentioned without their own page
- Find contradictions between pages (note source dates)
- Suggest new sources to investigate
- Suggest new questions to explore
- Append to log: `## [YYYY-MM-DD] lint | Summary of findings`

### 4. TRADE LOG (record a trade or trade idea)
When the human shares a trade or idea:
1. Create or update the entity page for the ticker
2. Record the setup under the relevant strategy page as an example
3. If post-mortem: create an analysis page with outcome and lessons
4. Update `wiki/log.md`

---

## Trading-Specific Conventions

### Bias Tagging
Mark every entity page with current bias:
`bias: bullish | bearish | neutral | watching`

### Timeframe Tags
Tag all strategy/analysis pages with their applicable timeframe:
`timeframe: scalp | intraday | swing | position | long-term`

### Market Regime
`wiki/overview.md` should always reflect the current market regime:
- Trending (bull/bear)
- Range-bound
- High volatility
- Low volatility / chop

Update this whenever a source or analysis shifts the view.

### Key Level Format
Always express key levels consistently:
```
Support: 185.50 (prior high reclaimed, 3 touches)
Resistance: 192.00 (gap fill from Apr 3)
Stop zone: below 183.80 (daily swing low)
Target 1: 190.50 (50% of range)
Target 2: 194.00 (prior structure)
```

### Indicator Conventions
When documenting indicator readings, always specify:
- Indicator name + parameters (e.g. RSI 14, EMA 21)
- Timeframe the reading applies to
- What action/signal it implies

---

## Index Format (`wiki/index.md`)

```markdown
# Wiki Index
_Last updated: YYYY-MM-DD | Pages: N | Sources ingested: N_

## Entities
| Page | Ticker | Bias | Updated | Sources |
|------|--------|------|---------|---------|
| [AAPL](entities/AAPL.md) | AAPL | bullish | 2026-06-01 | 3 |

## Concepts
| Page | Summary | Updated |
|------|---------|---------|

## Strategies
| Page | Timeframe | Summary | Updated |
|------|-----------|---------|---------|

## Sources
| Page | Type | Date | Author |
|------|------|------|--------|

## Analyses
| Page | Date | Topic |
|------|------|-------|
```

---

## Log Format (`wiki/log.md`)

```markdown
# Wiki Log
<!-- append-only, newest entries at top -->

## [2026-06-14] init | Wiki created
- Directory structure initialized
- Schema written
- Stub pages created: index, log, overview
```

---

## Working Directory

All paths are relative to the vault root:
```
C:\Users\dhara\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\
```

**Claude Code session opener** (paste this at the start of every Claude Code session):
```
Your working directory is C:\Users\dhara\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\
Read CLAUDE.md and load the wiki. Show me the last 5 log entries and the current market thesis.
```

---

## Session Startup Checklist

At the start of every new session:
1. Read `CLAUDE.md` (this file)
2. Read `wiki/index.md` (know what's in the wiki)
3. Read `wiki/log.md` tail (last 5 entries — know what was done recently)
4. Read `wiki/overview.md` (know the current market thesis)
5. Confirm ready: "Wiki loaded. [N] pages indexed. Last activity: [date]. Current thesis: [one sentence]."

---

## Principles

- **You write, the human thinks.** Never ask the human to update a page — do it yourself.
- **Always cross-reference.** Every ingest should touch multiple pages.
- **Contradictions are gold.** Flag them explicitly — they force clearer thinking.
- **Price levels decay.** Always timestamp key levels. Old levels without dates are meaningless.
- **File good answers.** If an analysis is worth generating, it's worth keeping.
- **Bias your updates.** New information should update existing pages, not just add new ones.
