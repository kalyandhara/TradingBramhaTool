---
title: "GitHub — Panniantong/Agent-Reach (multi-platform content-fetching layer for AI agents)"
category: source
tags: [claude-code, skills, web-scraping, youtube, github-cli, tooling]
created: 2026-07-02
updated: 2026-07-02
sources: 1
related:
  - concepts/Claude-Code-Skills.md
  - sources/GitHub-kepano-obsidian-skills-2026.md
---

# GitHub repo — Panniantong/Agent-Reach

## Metadata
- Author: Panniantong
- URL: https://github.com/Panniantong/Agent-Reach
- License: MIT
- Stars: ~49k, 3.9k forks — latest release v1.5.0 (June 2026)
- Language: Python 95.5%, Shell 4.5%
- Ingest trigger: Kalyan pasted the repo URL directly, no other context given

## Key Takeaways

- **A modular, multi-backend content-fetching layer for AI agents** (Claude Code, OpenClaw, Cursor, Windsurf): one `agent-reach` CLI install registers a SKILL.md so Claude Code automatically reaches for the right backend per platform, with automatic fallback to a secondary tool if the primary one fails. 15+ platforms covered: Web (Jina Reader), YouTube (yt-dlp), RSS, web-wide semantic search (Exa via MCP), GitHub (gh CLI), Twitter/X, Bilibili, Reddit, Facebook, Instagram, Xiaohongshu, LinkedIn, V2EX, Xueqiu, Xiaoyuzhou podcast.
- **Two backends fix real, already-hit gaps in this exact project — not hypothetical ones**:
  1. **YouTube via `yt-dlp`** directly targets the pain point already logged in this wiki: the 2026-06-29 YT-Breakout-Screener ingest needed Kalyan to manually paste a full transcript after automated caption fetch failed (YouTube's signed `timedtext` URL returns HTTP 200 with an empty body for non-browser requests, confirmed across multiple Invidious mirrors too). `yt-dlp` (154k★ itself) is purpose-built to handle exactly this kind of YouTube anti-bot friction, unlike a generic HTTP fetch.
  2. **GitHub via the `gh` CLI** — Agent-Reach's setup installs `gh` as part of its bootstrap. This session independently hit the exact absence of `gh`: earlier today, both `Bash` (`gh: command not found`) and `PowerShell` (`gh: not recognized`) failed when I tried `gh repo view kepano/obsidian-skills` for a source ingest, forcing a fallback to WebFetch for GitHub research. Not a hypothetical gap — a real one from earlier the same session.
- **Most of the other 12+ platforms are not relevant to this project**: the tool's origin skews toward Chinese-language platforms and audiences (install instructions given in Chinese: "帮我安装 Agent Reach"; Bilibili, Xiaohongshu, V2EX, Xiaoyuzhou podcast are Chinese platforms with no bearing on NSE-focused English-language trading research). Xueqiu ("stock data and forum searches") is the one finance-flavored channel but is a Chinese-market stock forum, not applicable to Indian equities.
- **Semantic search via Exa (MCP, free tier)** is a genuine alternative to the `WebSearch` tool already available in this environment — AI-native/semantic rather than keyword-based — but not a clear improvement, just a different option; not adopted here.

## Detailed Notes

Installation is agent-driven, not manual: the user tells their agent "帮我安装 Agent Reach: [URL to install.md]" and the agent fetches the install script, installs the `agent-reach` CLI via pip, auto-detects personal-computer vs. server environment, installs Node.js/`gh`/`mcporter` as needed, registers the SKILL.md, and runs `agent-reach doctor` for diagnostics. This is the same "point an agent at a URL and let it self-configure" pattern already seen in the `claude-obsidian` ingest's `/wiki` setup flow.

GitHub access is explicitly tiered: public repo viewing/searching needs zero configuration; private repo access, issue creation, PRs, and forking need the user to separately say "帮我登录 GitHub" (help me log into GitHub) to authenticate the CLI.

## Actionable Insights

- **Installing just the YouTube (`yt-dlp`) and GitHub (`gh`) backends would fix two real, previously-hit gaps** — this doesn't require adopting the whole 15-platform suite, consistent with the "cherry-pick what's needed" pattern already applied to `kepano/obsidian-skills` (only `defuddle` was judged worth it there). Simplest version: just install `yt-dlp` and `gh` directly (both are standalone, well-known CLIs) rather than the full Agent-Reach wrapper, unless the automatic-fallback routing and SKILL.md auto-invocation are themselves valued.
- **`gh` CLI absence is worth fixing directly regardless of Agent-Reach** — it's a genuine, recurring friction point for GitHub-repo research in this project's own ingest workflow (hit at least once already this session).
- **Not recommended**: adopting Agent-Reach for its non-YouTube, non-GitHub channels — Twitter/Reddit/Facebook/Instagram/LinkedIn/Bilibili/Xiaohongshu/V2EX/Xiaoyuzhou have no clear use case for NSE-focused trading research, and several require login/authentication overhead for no corresponding benefit here.

## Contradictions with Existing Wiki

None — reinforces the standing pattern from prior tooling ingests this session (adopt narrowly, not wholesale).

## Pages Updated

None yet — this is a "worth doing" flag, not yet installed or wired into this project's own ingest workflow. Revisit `concepts/Claude-Code-Skills.md` if/when `yt-dlp`/`gh` are actually installed.
