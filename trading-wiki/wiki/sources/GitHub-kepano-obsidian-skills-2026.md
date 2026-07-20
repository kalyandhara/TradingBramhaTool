---
title: "GitHub — kepano/obsidian-skills (Official Obsidian Agent Skills)"
category: source
tags: [claude-code, skills, obsidian, agent-skills, github, tooling]
created: 2026-07-01
updated: 2026-07-01
sources: 1
related:
  - concepts/Claude-Code-Skills.md
  - concepts/Agent-Loop-Design.md
---

# GitHub repo — kepano/obsidian-skills

## Metadata
- Author: kepano (Steph Ango, Obsidian.md CEO)
- URL: https://github.com/kepano/obsidian-skills
- License: MIT
- Stars: ~39.2k (up from ~35k when first mentioned to Kalyan a session ago — actively growing)
- Ingest trigger: Kalyan asked to check the repo for anything new after this wiki's own [[concepts/Claude-Code-Skills]] page recommended it as a "worth borrowing" add-on rather than a full adoption

## Key Takeaways

- 5 skills total, all implementing the official "Agent Skills specification" — works with Claude Code, Codex, and OpenCode, not Claude-Code-only.
- **`obsidian-markdown`** — writes Obsidian Flavored Markdown correctly: wikilinks, embeds, callouts, YAML properties. Directly relevant to this wiki's own `[[wiki-relative-link]]` convention.
- **`obsidian-bases`** — Obsidian's newer database-like views (filters/formulas/summaries over notes) — not currently used anywhere in this wiki.
- **`json-canvas`** — visual node/edge/group canvas format — no current use case here.
- **`obsidian-cli`** — talks to a *running* Obsidian app instance (create/search/append notes, daily notes, tasks, backlinks, plugin/theme dev tools with screenshot/DOM/console inspection). Requires Obsidian actually open with the vault loaded, not just plain files on disk.
- **`defuddle`** — wraps the `defuddle` npm CLI to extract clean Markdown from a live URL, stripping nav/ads/clutter before the content reaches the model. Explicitly *not* for `.md` URLs (use WebFetch directly there).

## Detailed Notes

Install is a 2-liner exactly like this wiki already uses for other skills:
```
/plugin marketplace add kepano/obsidian-skills
/plugin install obsidian@obsidian-skills
```
No repo clone needed for Claude Code (marketplace route); npx/manual routes exist for Codex/OpenCode.

No dated "recent changes" are published (no GitHub Releases) — the repo is just 46 commits total, actively maintained via issues/PRs rather than versioned releases. So "what's new" is really "what exists" — there's no changelog to diff against a prior known state, since this wiki had never ingested it before.

## Actionable Insights

- **`defuddle` is the one skill with a direct workflow win for this wiki.** The INGEST operation in `CLAUDE.md` currently relies on Kalyan pasting raw text/transcripts (see the YT-Breakout-Screener ingest log entry — captions had to be pasted manually after automated fetch was blocked) or on WebFetch's own summarization. `defuddle parse <url> --md` would give a clean, token-efficient Markdown dump of an article/blog/doc page *before* Claude reads it — useful for future web-page and blog-post sources, though it needs `npm install -g defuddle` first and doesn't help with YouTube transcripts or paywalled pages.
- **`obsidian-markdown` only pays off if this vault is actually opened in the Obsidian app.** Right now `trading-wiki/` is plain Markdown edited by Claude Code directly (Read/Write/Edit tools) — the wikilinks already used (`[[concepts/RSI]]`) are correct syntax regardless of whether Obsidian renders them, so this skill is polish (graph view rendering, callout syntax correctness) rather than a functional gap.
- **`obsidian-cli` and `obsidian-bases` have no current use case** — this wiki doesn't run a live Obsidian instance as part of any workflow, and no page currently needs database-style filtered views. Worth revisiting only if the vault gets opened in the Obsidian app for browsing.
- **Recommendation: install `defuddle` alone (skip the other 4) if/when web-page ingest volume increases.** Installing all 5 for 1 useful skill violates the "stack 3-4 you need, not everything" principle already documented in [[concepts/Claude-Code-Skills]] Common Mistakes.

## Contradictions with Existing Wiki

None. This confirms rather than contradicts the prior assessment in the chat that prompted this ingest: the generic vault tooling isn't worth adopting wholesale, but specific pieces (this ingest narrows it down to just `defuddle`) are worth cherry-picking.

## Pages Updated

- concepts/Claude-Code-Skills.md — added this source to `related`, noted `defuddle` as a candidate ingest-pipeline tool under Application to This Project
