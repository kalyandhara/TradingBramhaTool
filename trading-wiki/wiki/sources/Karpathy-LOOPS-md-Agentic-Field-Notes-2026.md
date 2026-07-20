---
title: "LOOPS.md: Field Notes on Agents That Run for Days"
category: source
tags: [agentic-ai, agent-loop, harness-design, llm-engineering, claude-code]
created: 2026-07-01
updated: 2026-07-01
sources: 1
related:
  - concepts/Agent-Loop-Design.md
---

# [Paper] LOOPS.md — Field Notes on Agents That Run for Days

## Metadata
- **Author:** Andrej Karpathy (Independent Researcher)
- **Date:** 2026 (v060726)
- **Format:** Conference-style reformatting of working notes (loops.md)
- **Context:** Karpathy's personal field notes on building and running long-lived agentic systems, condensed to 9 principles

---

## Key Takeaways

1. **The loop, not the prompt, is the unit of work** — prompts are one-shots; loops run while you sleep. Model leverage now lives in the procedure, not the message.
2. **Separate the roles strictly** — Planner (turns vague intent into a spec), Generator (writes code, never grades itself), Evaluator (reads diffs, runs tests, proves things work). Mixing them produces sycophancy; the loop converges silently on slop.
3. **Negotiate the contract before a line is code is written** — Generator proposes, Evaluator pushes back via markdown files on disk. ~27 testable assertions is a reasonable contract for a small app. The contract is the boundary; it is what gets graded, not the original prompt.
4. **Write to disk, not to context** — context windows lie, compact, rot. Keep `feature_list.json`, `progress.md`, `contract.md`, and an append-only `log.md` (`## [YYYY-MM-DD] op | title`). If you can't describe your state in three files, your state is too complicated.
5. **Let the loop restart** — best frontier model behavior is throwing everything away and starting clean when a run goes sideways. Don't interrupt. Insert a human only when the *contract* is wrong, not when the *build* is wrong.
6. **Score the subjective by writing it down** — taste is gradable if you produce a rubric first. Four axes: design, originality, craft, functionality. Output is 0–1 plus a paragraph. The model converges toward whatever taste *you described*, so write the rubric carefully.
7. **Read the traces** — every debugging insight comes from reading raw transcripts, not from running more experiments. Grep for the moment judgment diverged, edit the prompt for that exact moment, run again. It's stack-trace reading, written in English.
8. **Delete the harness** — re-read your harness against each new model release. Anything the model now does natively is dead weight. A harness that grows monotonically is a harness you've stopped reading.
9. **The bottleneck always moves** — coding → planning → verification → taste → next unknown. The loop exists to make the *next* bottleneck visible.

---

## Detailed Notes

### Role Separation (§II)
Three context windows, three system prompts:
- **Planner** → sprint spec from vague sentence; never touches code
- **Generator** → writes everything; forbidden from grading its own work
- **Evaluator** → reads diffs, launches `playwright`, plays the app; told from message one that code is broken, job is to prove it

Mixing roles = sycophancy = quiet convergence on slop. This is the most common failure mode in deployed agent systems.

### Contract Negotiation (§III)
Before the generator writes a single line:
- Generator proposes what "done" looks like
- Evaluator pushes back
- They argue via markdown files on disk
- Agreement = checklist of testable assertions
- **The contract, not the prompt, is what gets graded**
- 27 criteria = reasonable for a small app; 10 = too few (evaluator rubber-stamps)
- This is the single change that moved Karpathy's runs from broken demos to working products

### Disk-as-State (§IV)
- Context windows: compact, rot, hide what you said an hour ago
- `feature_list.json` — immutable spec
- `progress.md` — current implementation state
- `contract.md` — the negotiated rubric
- `log.md` — append-only (`## [YYYY-MM-DD] op | title` format)
- Model should be able to crash, lose session, pick up where it left off from these three files
- **If state can't be described in three files, state is too complicated**

### Restart Behavior (§V)
Counter-intuitive finding: best current models throw everything away and start over when runs go sideways. Older models patch-and-patch until the codebase resembles archaeology. Newer ones, given a clean evaluator + contract, delete the project at iteration 9 and ship a working version at iteration 11. **Do not interrupt this.**

### Trace Reading (§VII)
All debugging insight comes from reading raw transcripts, not from running more experiments:
1. Pipe agent output to a file
2. Grep for the moment judgment diverged from yours
3. Edit the prompt for that exact moment
4. Run again
> "This is the same muscle as reading a stack trace; the difference is that the trace is written in English and most of it is the model talking to itself."

### Harness Deletion (§VIII)
Context resetting between sessions was load-bearing for one model generation — now it's dead weight. Sprint decomposition was the only thing keeping a four-hour build coherent — now a constraint. Re-read harness against each new release; delete anything the model now does for free. **A harness that grows monotonically is a harness you've stopped reading.**

---

## Actionable Insights for This Project

- **`wiki/log.md`** already follows the `## [YYYY-MM-DD] op | title` disk-state convention from §IV — this is correct and should stay.
- **Scanner Hub + Breakout Screener tabs** are generator-output; their contracts are implicit. Formalizing as `contract.md` checklist files (e.g., "screener returns ≥1 result on RELIANCE.NS test run") would make evaluating changes safer.
- **The `dashboard_app.py` harness** (Streamlit wiring, cached fetch, db layer) should be audited periodically — any boilerplate that newer Streamlit versions or Streamlit-native components now handle for free should be deleted.
- **Role separation principle applies to this wiki** — the human (planner) defines what to ingest and what questions matter; Claude (generator + evaluator) does all reading, writing, cross-referencing. Don't ask the human to update pages.
- The **"bottleneck always moves"** principle is a useful frame for the trading system: the bottleneck has moved from data access → screening → charting → signal quality. The next bottleneck is probably execution discipline / trade log feedback loop.

---

## Contradictions with Existing Wiki

None direct — this is an AI-engineering paper, not a trading-strategy paper. The disk-state conventions in §IV are already followed by this wiki's `log.md` format, which is a positive confirmation.

---

## Pages Updated

- `sources/Karpathy-LOOPS-md-Agentic-Field-Notes-2026.md` ← this page (new)
- `concepts/Agent-Loop-Design.md` ← new concept page created
- `wiki/index.md` ← updated counts and entries
- `wiki/log.md` ← ingest entry appended
