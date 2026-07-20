---
title: "Claude Code Skills (SKILL.md)"
category: concept
tags: [claude-code, skills, SKILL-md, agentic-ai, llm-engineering, prompt-engineering]
created: 2026-07-01
updated: 2026-07-01
sources: 1
related:
  - concepts/Agent-Loop-Design.md
  - sources/MyWestLord-45-Claude-Design-Skills-2026.md
  - sources/Karpathy-LOOPS-md-Agentic-Field-Notes-2026.md
  - sources/GitHub-kepano-obsidian-skills-2026.md
  - sources/GitHub-Panniantong-Agent-Reach-2026.md
---

# Claude Code Skills (SKILL.md)

## Definition

A **Skill** is a `SKILL.md` file — plain markdown — that loads into Claude Code (or Cursor/Codex/Gemini CLI) and overrides the model's default behavior *before* the first line of code or CSS is generated. Skills are the mechanism by which you install persistent taste, constraints, and procedures into an agent session without rewriting a system prompt every time.

> *"Skills are SKILL.md files — plain markdown rules that load into Claude Code, Cursor, or Codex and overwrite the model's default taste before a single line of CSS gets written."*

They are the practical implementation of the contract-first principle from [[concepts/Agent-Loop-Design]] applied to taste and behavior rather than task completion.

---

## How to Use

### 3 Install Methods

```bash
# Method 1 — universal (works across Claude Code, Cursor, Codex, Gemini CLI)
npx skills add <github-repo> --skill <skill-name>

# Method 2 — Claude Code plugin marketplace
/plugin marketplace add <owner/repo>
/plugin install <name>@<marketplace>

# Method 3 — MCP server (for Figma, Blender, Playwright, Composio integrations)
claude mcp add <name> -- npx <package>
```

### Stacking Rules
- Don't install all at once — stack 3-4 that fight slop at the source
- Recommended minimum stack: **base taste + motion + token system + visual feedback loop**
- Skills set the aesthetic/behavioral floor; judgment about *which direction* to commit to remains the human's

---

## 6 Layers of Skills

### Layer 1 — Frontend & UI (Anti-Slop Core)
The slop fingerprint: purple-to-white gradient, Inter font, 4 cards in a grid, 1 weak hover state.

| Skill | Key Rule | Install |
|---|---|---|
| `frontend-design` (Anthropic, 277k installs) | 4-question commitment before CSS; bans Inter/Roboto/Arial/Space Grotesk | `npx skills add anthropics/skills --skill frontend-design` |
| `impeccable` (Paul Bakaus) | 23 commands, 44 anti-pattern rules; 4px/8px grid, OKLCH, `clamp()`, WCAG AA | `npx impeccable install` |
| `design-taste-frontend` (Leonxlnx, 102k installs) | VARIANCE/MOTION/DENSITY dials; opinionated Next.js+Tailwind+Framer+Radix stack | `npx skills add https://github.com/Leonxlnx/taste-skill --skill design-taste-frontend` |
| `animate` (Emil Kowalski) | 150-250ms micro, only transform+opacity, exits faster than entrances | `npx skills add https://github.com/delphi-ai/animate-skill --skill animate` |
| `theme factory` (Composio) | Token system from 1 brand color; no one-off hex values | `/plugin marketplace add ComposioHQ/awesome-codex-skills` |
| Playwright MCP | Visual feedback loop — model screenshots its own output and compares | `claude mcp add playwright -s user -- npx @playwright/mcp@latest` |

**Playwright is the highest-leverage single addition** — it gives the model eyes to grade its own visual output, closing the loop that all other skills leave open.

### Layer 2 — Image, Graphics, 3D & Video
- `nano-banana` — Gemini image gen in terminal (~$0.04/image)
- `remotion superpowers` — full video studio (voiceover, music, captions, stock footage, MP4 render)
- `blender-motion` — drive Blender 3D scenes via text (MCP)
- `aftereffects-motion` — live commands + JSX scripting into After Effects

### Layer 3 — Claude Design Product (claude.ai/design)
Web-only, paid. Chat + live design canvas. Everything built in editable code, not flat JPEG.
Best for: infographics, mockups, carousels, decks. Feed it a design system first.

### Layer 4 — AI Product Interaction Design
From `Owl-Listener/ai-design-skills` (MIT). Skills that design *AI product behavior*, not pixels:

| Skill | What it designs |
|---|---|
| `context-window-design` | Token budget allocation, summarization vs retrieval, graceful degradation |
| `conversation-patterns` | Turn-taking, repair sequences, grounding checkpoints |
| `generative-ui` | When AI renders UI components vs plain text |
| `progressive-disclosure` | Staged capability reveal matching user readiness |
| `frustration-detection` | Detects signals (caps, punctuation density, repetition) → adaptation playbook |
| `feedback-loops` | Ambient signals first; explicit ratings sparingly |

### Layer 5 — System Behavior & Prompt Architecture

| Skill | Core principle |
|---|---|
| `system-prompt-structure` | Important instructions first AND last (where model attends most) |
| `constraint-specification` | **Rule: if you can't verify the model followed it, rewrite the rule** |
| `few-shot-patterns` | Target failure modes and edge cases, not happy paths |
| `output-quality-rubrics` | Concrete pass/fail per dimension — powers regression testing |

### Layer 6 — Trust, Evaluation & Agent Orchestration

| Skill | Purpose |
|---|---|
| `guardrail-design` | Enforceable behavioral lines, not vibes |
| `trust-calibration` | Flag uncertainty instead of bluffing; deliberate confidence signaling |
| `task-decomposition` | Complex goals → agent-sized subtasks with clear role and boundary |
| `handoff-protocols` | What context passes between agents, what gets confirmed, where human reviews |

---

## Variants / Parameters

- **VARIANCE / MOTION / DENSITY** dials (taste-skill): 1-10 scale for asymmetry, kinetic energy, information density
- **Brand vs Product mode** (impeccable): opposite rules for marketing sites vs dashboards
- **Dial overrides in chat**: `Build a portfolio. VARIANCE 9, MOTION 7, DENSITY 3.`

---

## Common Mistakes

- **Installing too many at once** — skills can conflict; stack 3-4, not 45
- **Expecting skills to replace judgment** — they prevent slop; the direction to commit to is still yours
- **Skipping Playwright** — without visual feedback, you're trusting a blind model
- **Treating Layer 4-6 skills as plug-and-play** — they are conceptual frameworks; production-verify before relying on them
- **Not feeding the Claude Design canvas a design system first** — the product barely works without structure

---

## Related Concepts

- [[concepts/Agent-Loop-Design]] — skills are the taste layer of the contract-first pattern; `constraint-specification` and `output-quality-rubrics` are the prompt-engineering equivalents of contract.md
- [[sources/Karpathy-LOOPS-md-Agentic-Field-Notes-2026]] — harness deletion principle applies: audit installed skills against new model releases and remove what the model now does natively
- [[sources/MyWestLord-45-Claude-Design-Skills-2026]] — primary source with all 45 install commands
- [[sources/GitHub-kepano-obsidian-skills-2026]] — official Obsidian agent-skills pack (5 skills, 39k★); confirms the "stack what you need, not everything" rule — only 1 of the 5 (`defuddle`) has a concrete use case for this wiki today

---

## Application to This Project

- **Playwright MCP** should be wired to `chart_dashboard.html` — screenshot after every significant change, compare to reference baseline, catch visual regressions before they ship
- **`output-quality-rubrics`** is the missing piece for scanner result cards — no formal rubric currently exists for what a "good" breakout hit card looks like
- **`task-decomposition` + `handoff-protocols`** formalize the Scanner Hub → Breakout Screener → Chart Dashboard pipeline as an agent handoff chain
- **`frontend-design`'s 4-question commitment** (purpose, tone, constraints, differentiation) should be applied before any new dashboard tab or UI widget is built
- **`defuddle`** (from `kepano/obsidian-skills`) is a candidate fix for this wiki's own ingest pipeline — past ingests have needed manual transcript pasting when automated fetch got blocked (see `wiki/log.md`, YT-Breakout-Screener entry); `defuddle parse <url> --md` gives clean, token-efficient Markdown for web-page/blog sources specifically (not video transcripts)
- **`yt-dlp` and `gh` CLI** (surfaced via [[sources/GitHub-Panniantong-Agent-Reach-2026]]) fix the video-transcript half of that same gap (`defuddle` only covers web pages) and a `gh`-CLI-absence gap hit directly in this same session (GitHub research had to fall back to WebFetch when `gh repo view` wasn't available in either Bash or PowerShell)
