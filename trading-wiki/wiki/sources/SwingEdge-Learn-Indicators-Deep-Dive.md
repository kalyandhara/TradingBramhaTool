---
title: "SwingEdge — Indicator Deep-Dive Lessons (Learn series, 6 lessons)"
category: source
tags: [education, indicators, rsi, macd, adx, ema, bollinger-bands, atr]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [concepts/RSI, concepts/MACD-Divergence, concepts/ADX, concepts/EMA, concepts/Bollinger-Bands-Squeeze, concepts/Capital-Management-Methods]
---

# Source — SwingEdge "Learn" Indicator Deep-Dive Cluster (6 lessons)

## Metadata
- **Source type**: Educational articles, 6 of the 22 lessons in SwingEdge's Learn curriculum (see [[sources/SwingEdge-Learn-Intro-Swing-vs-Day]] for the full catalog)
- **URLs**: `/learn/moving-averages-deep-dive`, `/learn/rsi-momentum-deep-dive`, `/learn/macd-deep-dive`, `/learn/bollinger-bands-squeeze`, `/learn/adx-trend-strength`, `/learn/atr-stops-position-sizing`
- **Ingested**: 2026-06-22

## Key Takeaways
This cluster was substantially richer than the first two Learn lessons ingested earlier ([[sources/SwingEdge-Learn-Intro-Swing-vs-Day]], [[sources/SwingEdge-Learn-Trends-Stages]]), which were mostly introductory. These six contained genuinely new, concrete mechanics that have been **merged directly into the relevant existing concept pages** rather than left in this source page, so the wiki's per-indicator pages stay the single source of truth:

| Lesson | Merged into | What was added |
|---|---|---|
| Moving averages 20/50/200 | [[concepts/EMA]] | SMA vs EMA distinction, per-period role (20=trend rail, 50=pullback magnet, 200=regime line), slope-over-position rule, 7–10% stretch/mean-reversion heuristic |
| RSI — momentum & divergence | [[concepts/RSI]] | Regime-aware ranges (40–80 up / 20–60 down), hidden/continuation divergence (the inverse of classic divergence), swing-failure-swing pattern, period selection by use case |
| MACD — line, signal & histogram | [[concepts/MACD-Divergence]] | Zero-line as the primary trend filter, histogram acceleration/deceleration as a leading edge, crossover-location table (above/below zero changes the read entirely), weekly/daily/intraday MACD template |
| Bollinger Bands & squeeze | [[concepts/Bollinger-Bands-Squeeze]] (new page) | Squeeze/bandwidth formula, band-walk continuation framing, %B and bandwidth-percentile as scan features |
| ADX — trend strength filter | [[concepts/ADX]] | Refined 5-band value table (replacing the old 3-band split), slope-matters-more-than-level rule, two-level (stock + index) regime-filter application |
| ATR stops & sizing | [[concepts/Capital-Management-Methods]] | Multiplier-choice table, chandelier stop formula, ATR-based target setting, gap/illiquidity pitfalls |

## Detailed Notes
A recurring meta-pattern across all six lessons, worth naming explicitly: **every indicator is reframed from "crossover/threshold = signal" to "regime/context = filter."** RSI 70 isn't a sell signal, it's a description of how stretched momentum is *given the current regime*. MACD crossovers mean different things above vs. below zero. ADX doesn't pick direction, it gates whether trend-following setups make sense at all. Bollinger touches are reversal signals in chop and continuation signals in trend — same touch, opposite read depending on context. This is the same underlying lesson as the "scanners are interns, you interview each chart" framing from [[sources/SwingEdge-Learn-Trends-Stages]], applied at the indicator level instead of the screener level.

Also worth noting: how SwingEdge's own scanners reportedly use several of these (per the moving-averages and ADX lessons) — pre-breakout scans gate on price above a *rising* 50 EMA; market-regime gating uses Nifty's position vs. its 200 SMA to soften/boost bullish-setup scoring; ADX filters apply at both the stock and index level. This is useful context for interpreting any future SwingEdge stock-detail ingest's "why not 100" reasons.

## Actionable Insights
- The "regime, not threshold" reframe is worth applying retroactively when reading the 6 stock-detail pages already ingested from this source (KDDL, NRBBEARING, AADHARHFC, INDSWFTLAB, SIGMA) — e.g. INDSWFTLAB's RSI 78 "hot" flag and SIGMA's RSI 38 "weak" flag should be read against each stock's own trend regime, not against the textbook 70/30 lines.
- No further indicator lessons remain un-ingested from the 22-lesson catalog after this batch and the process/workflow batch ([[sources/SwingEdge-Learn-Process-Risk-Workflow]]) — the only ones not yet covered are the introductory two already done and these two consolidated batches account for the rest.

## Contradictions with Existing Wiki
- None. ADX's value-band table supersedes (refines, doesn't contradict) the coarser 3-band table that was in [[concepts/ADX]] before this update.

## Pages Updated
- [[concepts/RSI]], [[concepts/MACD-Divergence]], [[concepts/ADX]], [[concepts/EMA]] — updated in place with new sections
- [[concepts/Bollinger-Bands-Squeeze]] — created
- [[concepts/Capital-Management-Methods]] — added ATR-stops section (alongside trailing-exits and trade-plan sections from the companion process/workflow batch)
- This source page
