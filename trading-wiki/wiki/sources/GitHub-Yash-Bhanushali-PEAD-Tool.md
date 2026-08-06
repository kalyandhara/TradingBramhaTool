---
title: "GitHub — Yash-Bhanushali-21/stock-research-tool (NSE PEAD event-study tool)"
category: source
tags: [pead, event-study, abnormal-returns, CAR, market-model, significance-testing, NSE, backtest, data-sources, github]
created: 2026-08-05
updated: 2026-08-05
sources: 1
related:
  - analyses/PEAD-Scanner-Roadmap.md
  - analyses/Backtest-Harness.md
  - analyses/Open-Backlog-2026-08-02.md
---

# Source — GitHub: Yash-Bhanushali-21/stock-research-tool

## Metadata
- **URL:** https://github.com/Yash-Bhanushali-21/stock-research-tool
- **Description (author's):** *"a python pead tool for analyzing NSE scripts with latest posted quaterly earnings"*
- **Default branch:** `claude/quant-code-structure-01RznrcoXoytchaEwLtteW4M` (not `main`)
- **Signals:** 2 stars · 2 forks · last push **2026-05-01** · **no license specified**
- **Stack:** Python (FastAPI, statsmodels, pandas) · React 18 + Vite + Tailwind ·
  SQLite · PydanticAI + OpenAI (optional) · yfinance / NSE / jugaad-data

> [!warning] **No licence — read it, do not copy it**
> The repo declares no licence, which means **all rights reserved**. Nothing here
> may be lifted into this codebase. The one thing worth taking is **methodology**,
> and that methodology is not theirs: the event study is textbook financial
> econometrics (MacKinlay 1997, which their own code cites; Brown & Warner 1985).
> **Implement from the literature, not from their source.**

## Key Takeaways

- Solves **the same problem we do** — PEAD on NSE quarterly earnings — but from
  the **academic event-study** direction rather than the scanner direction.
- Its core is three small modules: `models/market_model.py`,
  `models/abnormal_returns.py`, `models/car.py`, plus `utils/statistical.py`.
- **It answers a question our backtest harness cannot currently answer at all:
  is the measured drift statistically distinguishable from noise?**
- Its composite-score design contains **the exact bug this repo fixed in B-1 on
  the same day this was ingested** — see Contradictions.
- Its OHLCV data-source doc **independently corroborates the B-1 root cause**.

## Detailed Notes — the event-study method

**Market model.** OLS of `R_stock = α + β·R_market + ε`, estimated over a
**120-trading-day window ending strictly before the announcement** — enforced by
filtering `data.index < announcement_date`, the same look-ahead discipline our
harness enforces by slicing `df.iloc[:t+1]`. Requires ≥80% of the window
(~96 observations); warns but proceeds below that.

**Abnormal return.** `AR = actual return − (α + β·R_market)` — the return left
over once the stock's *own* market sensitivity is removed.

**CAR + significance.** CAR is AR summed over post-event windows, default
**[1, 10, 30, 60, 90]** trading days. Significance is a **two-tailed t-test**
with `SE(CAR) = σ·√n`, where σ is preferentially the **estimation-period residual
standard deviation** (the MacKinlay standard), falling back to in-window sample σ
and *flagging which was used*. `t = CAR / SE(CAR)`; p from the t-distribution.

**Composite score.** Five weighted components — earnings surprise 25%, drift
confirmation 25%, price reaction 20%, earnings quality 15%, contextual 15% —
mapped to STRONG BUY … STRONG SELL bands.

## Actionable Insights — what is worth adding, and what is not

### ✅ Worth taking: risk-adjusted returns and a significance test

**This is the whole value of the ingest.** [[analyses/Backtest-Harness]] measures
edge as *"signal average forward return **minus** the average forward return of
all bars over the same symbols/window"*. That has two holes an event study closes:

1. **It is not risk-adjusted.** Subtracting the *average* bar implicitly assumes
   β = 1 for every name. A scanner that preferentially fires on **high-beta**
   names in a rising tape will show "edge" that is simply beta being paid — and
   our whole ~6y sample is a mostly-constructive tape, which is exactly when that
   bias is largest. `α + β·R_market` removes it by construction.
2. **There is no significance test anywhere in the harness.** `_aggregate`
   reports hit-rate, average, median, baseline and edge — and **no t-statistic,
   no p-value, no confidence interval**. So *"Harmonic Reversal +0.25R on n=122"*
   and *"Falling Wedge +0.74% edge at 20d"* are point estimates with **no stated
   probability of being noise**. For a harness whose stated purpose is *"the
   credibility check the roadmap wanted"*, that is the missing half.

**The build is cheap because we already hold the expensive parts.** Point-in-time
look-ahead-safe replay: built. Benchmark series: built (`fetch_nifty50`,
`_BENCHMARK_WRET`). What is missing is a per-signal OLS over the prior ~120 bars
and a t-stat on the aggregate — bounded work against machinery that already runs.

It also sharpens two questions already on the roadmap: **Phase 4's** *"does a
confirmed positive SUE drift harder than an inferred gap"* becomes testable with a
p-value rather than a comparison of two point estimates, and the **divergence
penalty** question gets a real test instead of a judgement call.

### ✅ Worth noting: the data-source doc corroborates B-1
`docs/indian-equity-ohlcv-data-sources.md` rates yfinance a **"convenience
baseline only; unsuitable as sole production source"**, *"not a primary tape"*,
with *"depth and quality vary by symbol"*. That is an **independent second
observer** reaching the conclusion B-1 reached the hard way when Yahoo froze 8 of
11 NSE sector indices on 2026-07-17.

**But it is corroboration, not a solution.** The doc **does not evaluate NSE
indices at all** — only equities — and it rates `jugaad-data` as itself fragile
(*"can break when NSE changes pages/APIs"*, *"does not guarantee deeper history
than Yahoo"*). Its actual recommendation for reliable coverage is **paid vendors**.
So it validates the diagnosis without offering a free fix.

### ❌ Not worth taking
- **React 18 + Vite + Tailwind + FastAPI.** [[analyses/Dashboard-UI-Roadmap]]
  Phase 4 defers exactly this rebuild until *"multi-device or sub-second needs
  actually appear"*. Nothing here changes that.
- **PydanticAI / OpenAI agents, `digest_llm`, `ai_verdict`.** No LLM key is
  configured — the standing FR-6② block.
- **News + TextBlob sentiment pipeline, NewsAPI, article scraping.** Different
  scope; lexical sentiment on financial headlines is weak, and we already have a
  four-input sentiment composite with a coverage floor.
- **Their composite score and rating bands.** We already have `market_verdict`,
  and ours is now strictly better on missing data — see below.

## Contradictions with Existing Wiki

> [!key-insight] Their composite makes the mistake we fixed the same day
> Their `composite_score` **defaults a missing component to 0 and weights it into
> the average anyway**, adjusting only a separate `confidence` field. A component
> that could not be measured therefore drags the score **down** — it is read as
> *bearish evidence* rather than *no evidence*.
>
> That is precisely the bug caught and fixed here on **2026-08-05** while closing
> **B-1**: giving an unmeasurable component `score = 0.0` fed
> `market_verdict._component_flags`' `score/weight` fallback as `factor = 0.0`,
> below `CAUTION_AT`, casting a false **bearish** vote. Ours now **renormalises
> over measurable weight** and lets NOT_CHECKED components **abstain**.
>
> **Two independent NSE PEAD tools reached the same design and it is wrong in
> both.** Theirs is unfalsified because it was never run against a feed that
> froze; ours was, on live data, and moved a verdict from AGGRESSIVE to TRADE.
> A separate "confidence" field does not repair a contaminated score — the score
> is what gets read.

Their **estimation-window σ** preference is also a sharper version of an
instinct already in our code: `_suv_series` and `earnings_calendar.compute_sue`
both measure dispersion over a **pre-event** baseline so an event cannot inflate
its own denominator. Same principle, and they apply it one level further out — to
the *standard error of the test statistic itself*.

## Pages Updated
- [[analyses/Backtest-Harness]] — new open item: market-model AR/CAR + significance.
- This page is the durable record; nothing was copied from the repository.
