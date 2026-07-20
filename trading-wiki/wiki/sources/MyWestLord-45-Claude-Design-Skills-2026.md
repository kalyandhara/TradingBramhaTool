---
title: "45 Claude Design Skills That Kill AI Slop"
category: source
tags: [claude-code, skills, SKILL-md, design, agentic-ai, llm-engineering, frontend, motion, agent-orchestration]
created: 2026-07-01
updated: 2026-07-01
sources: 1
related:
  - concepts/Claude-Code-Skills.md
  - concepts/Agent-Loop-Design.md
---

# [X/Twitter Thread] 45 Claude Design Skills That Kill AI Slop

## Metadata
- **Author:** @MyWestLord
- **URL:** https://x.com/MyWestLord/status/2068064010600108267
- **Date:** 2026 (exact date estimated July 2026)
- **Format:** Long-form X thread with install commands and prompts

---

## Key Takeaways

1. **The slop tell** — every AI-generated UI has the same fingerprint: purple-to-white gradient, Inter font, 4 cards in a grid, 1 weak hover state. The model ships the median; the median is dead.
2. **SKILL.md = taste override** — plain markdown files that load into Claude Code / Cursor / Codex *before* the first line of CSS, replacing default model aesthetics with deliberate constraints.
3. **3 install methods** — `npx skills add`, `/plugin marketplace add`, `claude mcp add` (for MCP server tools like Figma, Blender, Playwright).
4. **Stack 3-4, not all 45** — recommended core: 1 base taste layer + motion (Emil) + token system (theme factory) + visual feedback loop (Playwright).
5. **Skills set the floor; judgment sets the direction** — the skills prevent slop; choosing *which* aesthetic direction to commit to is still the human's call.

---

## The 3 Install Methods

```bash
# Method 1 — universal (Claude Code, Cursor, Codex, Gemini CLI)
npx skills add <github-repo> --skill <skill-name>

# Method 2 — Claude Code plugin marketplace
/plugin marketplace add <owner/repo>
/plugin install <name>@<marketplace>

# Method 3 — MCP server (Figma, Blender, Playwright, Composio)
claude mcp add <name> -- npx <package>
```

---

## Layer 1 — Frontend & UI (Anti-Slop Core)

### 1. frontend-design (Anthropic)
277,000+ installs. Bans Inter/Roboto/Arial/Space Grotesk. Forces 4-question commitment before CSS.
```bash
npx skills add anthropics/skills --skill frontend-design
```
Prompt: `Build a landing page for an AI security startup. Pick a bold aesthetic direction and commit to it.`
Output: Claude answers purpose/tone/constraints/differentiation, picks 1 extreme (brutalist/editorial/retro-futuristic/luxury/maximalist), produces production HTML/CSS/JS.

### 2. impeccable (Paul Bakaus, creator of jQuery UI)
35,800+ stars. 23 commands, 44 deterministic anti-pattern rules.
```bash
npx impeccable install
# inside agent:
/impeccable init
```
Commands: `polish · critique · typeset · colorize · bolder · quieter · delight · animate · layout`
2 modes: **brand** (marketing/editorial) and **product** (dashboards/internal tools). Enforces 4px/8px grid, OKLCH color, `clamp()` fluid type, WCAG AA contrast.

### 3. design-taste-frontend / taste-skill (Leonxlnx)
102,800+ installs, 31,700+ stars. 3 dial override system:
```bash
npx skills add https://github.com/Leonxlnx/taste-skill --skill design-taste-frontend
```
Prompt: `Build a portfolio. VARIANCE 9, MOTION 7, DENSITY 3.`
- VARIANCE = asymmetry level · MOTION = kinetic energy · DENSITY = info per screen
- Defaults: 8/6/4 (artsy and kinetic). Ships opinionated stack: Next.js, Tailwind, Framer Motion, Radix.

### 4. animate (Emil Kowalski)
Hard timing rules: micro 150-250ms, standard 200-350ms, exits faster than entrances (300ms in, 200ms out), staggers 30-60ms, never >1s, ease-out for entrances, only `transform`+`opacity` for 60fps, always honor `prefers-reduced-motion`.
```bash
npx skills add https://github.com/delphi-ai/animate-skill --skill animate
```

### 5. design-motion-principles (kylezantos)
Blends 3 lenses: Emil Kowalski (restraint), Jakub Krehel (production polish), Jhey Tompkins (playful). Catches `scale(0)` starts, bare `ease`, decorative motion, missing reduced-motion. 2 modes: create or audit.
```bash
npx skills add kylezantos/design-motion-principles
```

### 6. theme factory (Composio)
Generates token systems (colors, spacing scales, type ramps) as CSS variables from 1 brand color — 3 themes: light, dark, high-contrast.
```bash
/plugin marketplace add ComposioHQ/awesome-codex-skills
```

### 7. figma implement design (Figma MCP)
Faithful Figma → React translation. Generates multiple states per design in 1 pass. Pairs with Playwright for viewport fidelity checks.
```bash
claude mcp add figma -- npx figma-developer-mcp --stdio
```

### 8. webapp-testing / Playwright (highest leverage)
> "Without it you're trusting a blind model. With it, the model grades itself."
Screenshots every page at 1920px and 390px, compares against reference targets, iterates until match.
```bash
claude mcp add playwright -s user -- npx @playwright/mcp@latest
```

### 9. brandkit (Leonxlnx, taste-skill repo)
One-shot brand identity boards: logo directions, palette, typography, category mockups.
```bash
npx skills add https://github.com/Leonxlnx/taste-skill --skill brandkit
```

### 10. designer skills collection (Owl Listener)
63 skills + 27 commands across 8 plugins: research, systems, strategy, UI, interaction, prototyping, design ops, toolkit.
```bash
/plugin marketplace add Owl-Listener/designer-skills
```
Commands: `/discover · /strategize · /handoff` — strong on process (handoff specs, QA checklists), weaker on taste; pair with #1-#3.

---

## Layer 2 — Image, Graphics, 3D & Video

### 11. nano banana (Gemini image gen, ~$0.04/image)
```bash
/plugin marketplace add devonjones/devon-claude-skills
/plugin install nano-banana@devon-claude-skills
# needs Gemini API key from Google AI Studio
```
`/banana redesign this room like a professional interior designer`
Multi-turn image editing: room redesigns, thumbnails, product shots.

### 12. banana claude (Claude as Creative Director)
Applies Google's 5-component formula: Subject, Action, Location, Composition, Style. `/banana inspire` browses 2,500+ prompt database. 13 modes including style transfer, inpainting, 4K.
```bash
/plugin marketplace add AgriciDaniel/banana-claude
```

### 13. canvas-design (social graphics → real files)
Outputs actual PNG/PDF carousels, quote cards, infographics built in code (editable fonts/colors/logos).
```bash
npx skills add anthropics/skills --skill canvas-design
```

### 14. algorithmic-art (generative backgrounds)
Flow fields, noise, particles in code — unique per render, never looks like stock.
```bash
npx skills add anthropics/skills --skill algorithmic-art
```

### 15. remotion superpowers (full video studio)
13 commands, 5 MCP servers. AI voiceovers, music, stock footage, image/video gen, TikTok captions, scene transitions, render→review→fix loop. Hit 13M views in 1 week.
```bash
/plugin marketplace add DojoCodingLabs/remotion-superpowers
/plugin install remotion-superpowers@remotion-superpowers
/setup
```

### 16. claude remotion kickstart (official lighter entry)
```bash
npx create-video@latest
```
Describe video → Claude writes TypeScript → Remotion renders frame-by-frame.

### 17. blender-motion (Blender MCP, drive 3D via text)
```bash
# Install Blender MCP add-on from projects.blender.org/lab/blender_mcp
npx skills add LobzyJay/motion-design-with-claude --skill blender-motion
```
Claude writes `bpy` Python keyframes, F-curve modifiers, geometry nodes, render setup.

### 18. aftereffects-motion (AE via MCP)
Live commands into AE + JSX scripting bridge with ExtendScript patterns, expressions, effects catalog.
```bash
npx skills add LobzyJay/motion-design-with-claude --skill aftereffects-motion
```

---

## Layer 3 — Claude Design (claude.ai/design product)
Web-only, paid Claude plan. Chat pane + live design canvas. Everything built in code (editable, not flat JPEG).

### 19. High-fidelity web & app mockups
`Design a SaaS pricing page, 3 tiers, my design system, ready-to-build fidelity.`

### 20. Design systems (train it on your brand)
`Create a design system: my logo, header font, body font, and these 4 brand colors.`
Feed it structure first — the product barely works without this.

### 21. Templates (lock the structure)
`Turn this finished Instagram carousel into a template I can reuse every week.`

### 22. Slide decks
`Build a 10-slide pitch deck from this outline, using my deck template and brand colors.`

### 23. Composio MCP (1,000+ app integrations)
Figma → code → GitHub PR in 1 chat session.
```bash
claude mcp add composio -- npx @composio/mcp@latest
```

---

## Layer 4 — AI Product Interaction Design
Source: `Owl-Listener/ai-design-skills` (MIT, 42-skill open repo). Install all with:
```bash
npx skills add https://github.com/Owl-Listener/ai-design-skills --skill <name>
```

### 24. context-window-design
Token budget allocation: system prompt, history, retrieval, tool results. Picks summarization vs retrieval, orders by priority (recency bias), specifies graceful degradation.

### 25. conversation-patterns
Deliberate turn-length, who speaks first, repair sequences (self-repair, clarification, graceful misunderstanding), grounding checkpoints.

### 26. generative-ui
Rules for when AI renders UI components (date pickers, cards, charts) vs plain text, consistency, safe fallback.

### 27. progressive-disclosure
Staged reveal of capability — users not overwhelmed on turn 1, not underusing by turn 50. Maps features to user readiness.

### 28. multimodal-orchestration
Sequencing modalities — when to look, when to call a tool, when to speak — for single interactions blending vision, text, and actions.

### 29. mixed-initiative-flow
Explicit rules for AI-led (guided workflows) vs user-led (exploration) with clean handoff signals.

### 30. frustration-detection
Detects from caps, punctuation density, repetition, latency → adaptation playbook: simplify, slow down, offer a human.

### 31. feedback-loops
Ambient signals first (edits, regenerations, abandonment), explicit ratings sparingly, inline editing and partial acceptance.

---

## Layer 5 — System Behavior & Prompt Architecture

### 32. system-prompt-structure
Labeled sections: identity, context, behavioral rules, output spec, examples. Important instructions first and last (where model attends most).

### 33. persona-architecture
Consistent AI character: traits, voice, boundaries specified once. Prevents drift per reply.

### 34. tone-calibration
Per-context dials: formal for legal, warm for onboarding, terse for power users.

### 35. emotional-design
Response map for emotional states: validate without amplifying, de-escalate, hand off when needed.

### 36. template-design
Named, typed, bounded variables (`{user_query}` not `{input1}`), conditional sections, defaults.

### 37. few-shot-patterns
Example sets targeting failure modes and edge cases — moves behavior more than 10 lines of instruction.

### 38. chain-of-thought-design
Deliberate reasoning chains for multi-step tasks, structured not improvised.

### 39. constraint-specification
Testable boundaries — format, length, tone, content limits. **Rule: if you can't verify the model followed it, rewrite the rule.**

---

## Layer 6 — Trust, Evaluation & Agent Orchestration

### 40. guardrail-design
Explicit behavioral boundaries and refusal patterns — enforceable lines, not vibes.

### 41. trust-calibration
Deliberate confidence and citation signaling — flags uncertainty instead of bluffing.

### 42. transparency-patterns
Surface knowledge edges and model confidence so users calibrate reliance.

### 43. output-quality-rubrics
Concrete definition of quality (accuracy, relevance, helpfulness) with pass/fail per dimension. Powers regression testing.

### 44. task-decomposition + agent-role-design
Complex goals → agent-sized subtasks with clear role and boundary. Backbone of multi-agent systems that don't collide.

### 45. handoff-protocols
Smooth transitions between agents and between AI↔human: what context passes, what gets confirmed, where a person reviews.

---

## Recommended Starter Stack

| Slot | Skill | Purpose |
|---|---|---|
| Base taste | `frontend-design` OR `impeccable` OR `taste-skill` (pick 1) | Prevent slop |
| Motion | `animate` (Emil) | Non-cheap motion |
| Token system | `theme factory` | No one-off hex values |
| Visual feedback | `playwright` MCP | Model grades its own work |

---

## Contradictions / Gaps

- Layer 4-6 skills are conceptual SKILL.md files, not production-verified tools — treat as prompt-engineering frameworks, not plug-and-play.
- The Figma MCP bridge (#7) and Composio (#23) require external API setup and paid accounts; not zero-friction installs.
- No mention of testing methodology — #8 (Playwright) solves visual regression but not functional correctness or accessibility auditing beyond WCAG AA contrast.

---

## Actionable Insights for This Project

- **`playwright` MCP** (#8) is directly applicable to verifying `chart_dashboard.html` changes — could screenshot the dashboard after code edits and compare against a reference baseline, catching visual regressions automatically.
- **`system-prompt-structure`** (#32) and **`constraint-specification`** (#39) match the LOOPS.md contract-first principle already ingested — these are the prompt-engineering equivalents of Karpathy's contract.md.
- **`output-quality-rubrics`** (#43) + **`feedback-loops`** (#31) are the missing pieces for the screener pipeline — currently there's no formal rubric for what a "good" scanner result card looks like.
- **`task-decomposition` + `handoff-protocols`** (#44-#45) directly complement [[concepts/Agent-Loop-Design]] — they're the implementation details of the Planner→Generator→Evaluator handoff.
- The `frontend-design` skill's 4-question commitment pattern (purpose, tone, constraints, differentiation) is a useful frame for any new dashboard feature request — apply it before writing CSS.

---

## Pages Updated
- `sources/MyWestLord-45-Claude-Design-Skills-2026.md` ← this page (new)
- `concepts/Claude-Code-Skills.md` ← new concept page created
- `wiki/index.md` ← updated counts and entries
- `wiki/log.md` ← ingest entry appended
