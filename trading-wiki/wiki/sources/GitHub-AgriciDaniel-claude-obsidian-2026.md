---
title: "GitHub — AgriciDaniel/claude-obsidian (AI Second Brain for Obsidian)"
category: source
tags: [claude-code, obsidian, agent-loop, wiki, github, tooling]
created: 2026-07-01
updated: 2026-07-01
sources: 1
related:
  - concepts/Agent-Loop-Design.md
  - concepts/Claude-Code-Skills.md
  - sources/Karpathy-LOOPS-md-Agentic-Field-Notes-2026.md
  - sources/GitHub-kepano-obsidian-skills-2026.md
---

# GitHub repo — AgriciDaniel/claude-obsidian

## Metadata
- Author: AgriciDaniel
- URL: https://github.com/AgriciDaniel/claude-obsidian
- License: MIT
- Stars: 8.4k, 969 forks, 35 open issues, 212 commits — latest release v1.9.2 (2026-05-28)
- Ingest trigger: Kalyan pasted a promotional write-up of this repo (claiming "6,800 stars") proposing it as a general knowledge-base system; asked to check kepano/obsidian-skills first (ingested separately, see related), then this repo itself

## Key Takeaways

- **Explicitly built on Karpathy's LLM Wiki pattern** — direct lineage to [[sources/Karpathy-LOOPS-md-Agentic-Field-Notes-2026]], same disk-as-state / append-only-log philosophy this trading wiki already follows independently.
- Same core loop this wiki already implements: `ingest [source]` → entity/concept extraction → cross-reference linking → index + log update. Commands map almost 1:1 onto this wiki's own INGEST/QUERY/LINT operations in `CLAUDE.md`.
- **`wiki/hot.md`** — a ~500-word "recent context" cache refreshed every session, read *before* `index.md` on query. This wiki currently reconstructs recent context by re-reading `log.md`'s tail + `overview.md` each session (per the Session Startup Checklist) — functionally similar, but not condensed into one purpose-built file.
- **Four methodology modes** (Generic/LYT/PARA/Zettelkasten, v1.8+) — organizational philosophy is pluggable. This wiki uses a fifth, undeclared mode: a bespoke trading taxonomy (entities/concepts/strategies/sources/analyses) that none of the four generic modes would naturally produce.
- **Multi-writer advisory locks (v1.7+)** — per-file locks to prevent corruption when multiple agents/sessions ingest in parallel. Not a problem this wiki has hit (single session at a time), but a known failure mode once "ingest all of these" batch-parallel ingestion is attempted here.
- **Hybrid retrieval (v1.7+, opt-in)** — BM25 sparse search + optional Anthropic contextual-prefix + cosine rerank via local ollama. A scaling answer for the "read index.md → read pages" retrieval this wiki uses today, which is still cheap at 119 pages but won't stay cheap indefinitely.
- Star count discrepancy: the pasted promotional post claimed "6,800 stars"; actual is 8.4k. Numbers in secondhand promotional write-ups should be treated as approximate/stale, not quoted — a general pattern worth remembering for future source ingests of this kind (X/Twitter threads, blog posts hyping a repo).

## Detailed Notes

Directory structure is materially richer than this wiki's:
```
wiki/{concepts,entities,sources,sessions}/  index.md  hot.md  log.md  meta/{dashboard.base,dashboard.md}
.raw/          skills/ (15 Claude Code skills)   agents/ (batch processors)   scripts/
```
The `sessions/` folder (conversation logs as first-class wiki citizens) and `meta/dashboard.base` (an Obsidian Bases view — see [[sources/GitHub-kepano-obsidian-skills-2026]]'s `obsidian-bases` skill) are two structural ideas this wiki doesn't have.

Requires Obsidian v1.9.10+ actually installed and running (Local REST API plugin on port 27124 for the "add to existing vault" path) — this wiki has never required Obsidian to be open; it's edited as plain files directly by Claude Code.

## Actionable Insights

- **Adopt `wiki/hot.md` here.** This is the one concrete, low-cost win, and it's now been validated by two independent sources (this repo's v1.x feature, and the earlier chat recommendation before either repo was ingested). Concretely: a `wiki/hot.md` file, rewritten at the end of each session with a short synthesis of what changed + current thesis + open questions, read *first* in the Session Startup Checklist ahead of `index.md`/`log.md` tail.
- **Do not adopt the methodology-mode system or generic directory layout.** This wiki's bespoke entity/concept/strategy/source/analysis schema (with bias tagging, key-level formats, timeframe tags) is more specific and more useful for trading than any of the four generic modes — confirms the standing recommendation not to replace the existing system.
- **Hybrid retrieval and multi-writer locks are "not yet, but noted."** Neither is a problem at 119 pages / single-session usage. Revisit hybrid retrieval if/when `index.md` + per-page reads start consuming a meaningful fraction of context on a typical query; revisit locks only if batch-parallel ingestion (multiple sources at once, multiple agents writing) is actually attempted.
- **`meta/dashboard.base`** (Obsidian Bases view) is only useful if `trading-wiki/` is ever opened in the Obsidian app — same conditional as `obsidian-markdown`/`obsidian-bases` from the kepano skills ingest.

## Contradictions with Existing Wiki

None on trading content (pure tooling repo). One numeric contradiction resolved: the star count in Kalyan's pasted source (6,800) does not match the repo's actual count (8.4k) — noted above as a pattern (discount promotional-thread numbers) rather than a wiki claim to fix.

## Pages Updated

- concepts/Agent-Loop-Design.md — added `wiki/hot.md` as a concrete disk-as-state refinement under Application to This Project
