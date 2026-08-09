---
title: "Agent Loop Design"
category: concept
tags: [agentic-ai, agent-loop, harness, llm-engineering, automation]
created: 2026-07-01
updated: 2026-07-01
sources: 1
related:
  - sources/Karpathy-LOOPS-md-Agentic-Field-Notes-2026.md
  - sources/GitHub-AgriciDaniel-claude-obsidian-2026.md
---

# Agent Loop Design

## Definition

An **agent loop** is a procedure — not a prompt — that runs a language model repeatedly in a structured cycle: **gather → reason → act → verify → repeat**. The unit of leverage shifted from the prompt (a one-shot message) to the loop (a persistent, restartable process) once models became capable enough to follow multi-step procedures unsupervised.

> *"If you find yourself iterating on a single message at three in the morning, you are still in the prompting era. Close the tab. Write the loop."*
> — Karpathy, LOOPS.md (2026)

---

## Core Architecture

### Three Roles (must not be mixed)

| Role | Responsibility | Forbidden from |
|---|---|---|
| **Planner** | Turns vague human intent into a sprint spec and testable contract | Touching code |
| **Generator** | Writes all code and artifacts | Grading its own output |
| **Evaluator** | Reads diffs, runs the app, verifies against contract | Generating code |

**Mixing roles = sycophancy.** The generator grades itself charitably; the loop converges silently on slop. This is the most common failure in deployed agent systems.

### The Contract
Before the generator writes a single line, planner and evaluator negotiate a **contract** — a markdown checklist of testable assertions written to disk. This contract, not the original prompt, is what gets evaluated.

- ~27 criteria = reasonable for a small app
- ~10 criteria = too few (evaluator rubber-stamps)
- Contract lives in `contract.md` on disk alongside `feature_list.json`, `progress.md`, `log.md`

### Disk as State
Context windows compact, rot, and hide recent history. All state must live on disk:
```
feature_list.json   ← immutable spec
progress.md         ← current implementation state
contract.md         ← negotiated rubric (testable assertions)
log.md              ← append-only  ## [YYYY-MM-DD] op | title
```
**Rule:** if the agent's state cannot be described in three files, the state is too complicated. The agent should be able to crash, lose its session, and resume cold from these files alone.

---

## How to Use

### Restart Protocol
When a run goes sideways, the correct behavior is to **let the model restart clean** rather than patch-and-continue. Given a clean evaluator + contract on disk:
- Iteration 9: model deletes everything
- Iteration 11: working product ships

Do not interrupt restart behavior. Insert a human only when the **contract is wrong**, not when the **build is wrong**.

### Trace Reading (Debugging)
All debugging insight comes from reading raw transcripts, not running more experiments:
1. Pipe agent output to a log file
2. `grep` for the exact turn where agent judgment diverged from expected
3. Edit the prompt at that specific moment
4. Run again

This is identical to reading a stack trace — it's just written in English.

### Harness Hygiene
Re-read the agent harness (scaffolding, boilerplate, context-management code) against each new model release. Delete anything the model now handles natively. **A harness that grows monotonically is a harness you've stopped reading.**

---

## Scoring Subjective Quality

Taste is gradable if you write the rubric before the run:
- **Four axes:** design, originality, craft, functionality
- **Output format:** 0–1 score + paragraph explaining the gap
- The model converges toward whatever taste *the rubric describes* — write it carefully

---

## Common Mistakes

- **Mixing evaluator and generator** in the same context — produces sycophancy and silent quality decay
- **Leaving state in context** — context compacts; state on disk persists across crashes
- **Interrupting restarts** — let the model throw everything away when it decides to; this is the loop working correctly
- **Growing the harness** — adding scaffolding without periodically deleting what's no longer needed
- **Prompting instead of looping** — iterating on a single message rather than building a restartable procedure

---

## The Bottleneck Progression

The bottleneck always moves once you fix the current one:

```
Coding → Planning → Verification → Taste → [next unknown]
```

The loop's purpose is to make the *next* bottleneck visible. If everything is going smoothly, you are not looking carefully enough.

---

## Application to This Project

This trading system already follows several LOOPS.md principles:
- `wiki/log.md` uses the exact `## [YYYY-MM-DD] op | title` format from §IV
- The wiki's role separation (human = planner/curator; Claude = generator/evaluator) mirrors the three-role architecture
- Screener pipeline → dashboard → chart server → wiki form a feedback loop, not a one-shot pipeline

**Gap identified:** scanner contracts are implicit. Making them explicit (e.g., a `contract.md` per tool: "scanner returns ≥1 result for RELIANCE.NS", "chart pane syncs on resize") would allow evaluation to be more rigorous and allow clean restarts.

**Disk-as-state refinement (from [[sources/GitHub-AgriciDaniel-claude-obsidian-2026]]):** that project's `wiki/hot.md` — a ~500-word recent-context cache rewritten each session, read before the index — is a sharper version of this wiki's current approach (re-reading `log.md`'s tail + `overview.md`). Worth adding a `wiki/hot.md` to the Session Startup Checklist.

---

## Related Concepts

- [[sources/Karpathy-LOOPS-md-Agentic-Field-Notes-2026]] — primary source
- [[sources/GitHub-AgriciDaniel-claude-obsidian-2026]] — independent production implementation of the same disk-as-state pattern; source of the `hot.md` cache idea
- [[strategies/Hyperliquid-Momentum-Screener]] — example of a generator-output artifact that needs a contract
- [[log]] — this wiki's own disk-state log, consistent with §IV
