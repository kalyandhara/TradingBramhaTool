---
title: "Pipeline Alignment Audit — every page and screener against SCAN → SIGNAL → PLAN → RISK → MONITOR → VERDICT"
category: analysis
tags: [audit, information-architecture, pipeline, pages, scanners, risk, b-105, b-106, b-107, b-108, b-109]
timeframe: milestone-plan
created: 2026-09-21
updated: 2026-09-21
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/Yearly-Opening-Range-Pre-Registration.md
---

# Pipeline Alignment Audit

The owner's reference model is a six-stage pipeline: **SCAN → SIGNAL → PLAN →
RISK → MONITOR → VERDICT**, with the closing line *"AI does the work, YOU make
the final call."* This audit asks one question of the shipped app: **where does
each page and each screener actually sit in that pipeline, and which stages are
thin?**

Counted against the code on 2026-09-21: **23 pages** (plus Home) in 5 nav groups,
**50 registered scanners**, 45 of them in the confluence pipeline.

**The headline: the desk is front-heavy.** SCAN and SIGNAL are covered several
times over. PLAN is covered for fewer than half the scanners. **RISK is the
thinnest stage in the app, and it is the one the reference model puts at the
centre** — three of its four named components do not exist, and the two numbers
that do exist disagree with each other. One live wiring bug was found while
mapping it ([[#B-105]]).

## Stage 1 — SCAN (universe → candidates)

| Page | Role |
|---|---|
| Screener | the core NSE screen with the saved pipeline — the canonical SCAN |
| Other Screeners | ownership pipeline, sector rotation, bulk data |
| High-Growth Screener | quality-growth floors (ROE / ROCE / OPM) |
| Hidden Treasures | small/micro-cap ownership + quality screen |
| Breakout Scans | external new-high feeds (Chartink / TradingView) |
| Delete Funnel | the 8-filter noise sieve — SCAN by subtraction |
| Sector Map | RRG / sector orbit — scans sectors, not names |
| Market Sentiment · India Market Intel · OI Momentum | market-level scan (regime, flows, OI) |

**Nine surfaces for one stage.** This is the most duplicated stage in the app and
the nav says so: the "Screening" group holds 9 of the 23 pages. Nothing here is
broken; the question the owner should answer is whether nine entry points into
the same funnel is a feature (different questions) or drift (the same question
asked five ways) — [[#B-108]].

## Stage 2 — SIGNAL (candidates → graded setups)

| Surface | Role |
|---|---|
| Scanner Hub | the 50 registered scanners, run on any universe |
| Opportunity Hub | ranked daily shortlist, confluence-weighted across scanners |
| SVP Structure | volume-profile structure — explicitly a bystander lens |
| Strategy Hub | patterns + strategies + fundamental scores |
| Telegram Signals | ingested third-party calls |
| Predictive Analysis | per-name consolidated rating |

**The 50 scanners, by what the desk knows about them:**

| Tier | Count | Weight in confluence |
|---|---|---|
| measured (beat a random-entry baseline) | **2** | 1.00 |
| weak (measured at or below baseline) | 5 | 0.25 |
| unmeasured | **37** | 0.50 |
| risk (bearish — never votes) | 5 | 0.00 |
| neutral / bilateral (B-101) | 1 | 0.00 |

By category: Entry 17 · Pattern 15 · Momentum 6 · Risk 6 · Trend 5 · Neutral 1.
Five are excluded from the pipeline by name (Renko Flip, Shallow Flip, Support
Breakdown, VWAP Reclaim/Support, Zero-Debt Quality PEAD).

**37 of the 50 (74%) are unmeasured, and they carry 85% of the vote weight
available before family capping** (18.5 of 21.75 points; the two measured
scanners contribute 2.0). That is a known, deliberate state — unmeasured weight
is 0.5 precisely because it is unproven — but it is the honest headline for
SIGNAL, and it is why family capping exists at all.

## Stage 3 — PLAN (entry / stop / target / invalidation)

Two independent planners, and they do not meet:

* **Scanner plans** — `scanner_plans` census: **20 of 49 observed scanners carry
  a full entry/stop/target**, 29 carry none, 1 is bilateral by design. So **a
  shortlist row has a better-than-even chance of arriving with no plan at all**.
* **`stock_council.build_trade_card`** — the richest PLAN object in the app:
  entry, stop, up to 3 targets with R:R, horizon, invalidations, and a suggested
  size. It renders on **Stock Analyzer** and **Predictive Analysis** only.

**The gap is positional, not technical.** The full trade card exists; it is just
not reachable from the pages where a name is chosen (Opportunity Hub, Scanner
Hub, Watchlist). The reference model has PLAN sitting between SIGNAL and RISK,
and here it sits off to one side — [[#B-109]].

## Stage 4 — RISK — the thin stage

The reference model names four components. What is shipped:

| Component | Status (updated 2026-09-21) |
|---|---|
| **Position size** | **RECONCILED (B-107).** The council's per-trade size now passes through the market verdict's multiplier, and the max-trades cap is checked against the open book. Both numbers already existed; they had never met |
| **Exposure** | **BUILT (B-107).** Deployed %, largest position, top-3 and sector concentration on the Portfolio page — measured against total capital, and with no thresholds, because what counts as too concentrated is the owner's call |
| **Drawdown** | **still absent, and the blocker is DATA** — there is no equity-history table at all, so it is either reconstructed from positions + cached prices or snapshotted daily from today ([[#B-110]]) |
| **Max loss** | **still a flag, not a limit,** and deliberately so: enforcing it means refusing to show something, which is a policy decision rather than a missing feature |

**Position size is defined twice, in two different units, under one label:**

* `market_verdict.VERDICT_SPECS` — a *market-wide multiplier* (0 / 50 / 100%)
  plus a **max-trades cap** (0–4), shown on Home as "Position size" and in the
  daily digest.
* `stock_council.RISK_PER_TRADE_PCT = 2.0` — a *per-trade* size derived from the
  stop distance, shown as "Suggested size" on two research pages.

**Neither knew the other existed** until 2026-09-21: a STAND DOWN day ("no size,
no exceptions") did not change the council's suggested size, and the max-trades
cap was never checked against open positions. `prisk.reconcile_size` now applies
one to the other and the card names the rule that moved the number. Size and cap
are still reported separately, because they fail differently — a halved size
still lets you take the trade; being at the cap does not ([[#B-107]]).

**And the one live risk number was measured from the wrong price — FIXED
2026-09-21.** `compute_portfolio_summary` computed capital-at-risk as
`(entry_price − stop_loss) × qty`: **initial** risk, frozen at entry. A position
up 30% with a raised stop still reported its day-one risk; one under water with
an untouched stop under-reported. `tools/portfolio_risk.py` now returns both —
initial under its original key, `open_risk_pct` for the live question — and the
card and the 6% flag read the open one, with the retired share on the sub-line.
Positions with **no stop** (unbounded risk, not in the number) and **unpriced**
positions now raise their own cautions instead of quietly reading as safety
([[#B-106]]).

## Stage 5 — MONITOR

| Surface | Role |
|---|---|
| Alerts | armed price/metric alerts, triggered count on Home |
| Alert Bot (`alert_watcher.js`) | headless re-evaluation on an interval, 09:15–15:45 |
| Scheduler Hub | job registry, run/status/logs |
| Pipeline Log | what the 4:05 PM batch did, and whether it failed |

**This stage is in better shape than RISK.** Delivery is real (batched email via
`alert_email_send.py`); the console/JSONL feed remains the default, and Telegram
is still named-but-stubbed in the header comment.

## Stage 6 — VERDICT

Two verdicts, two vocabularies, two altitudes:

* **Market** — STAND DOWN / SELECTIVE / TRADE / AGGRESSIVE / NO EDGE, with size
  and trade-cap attached (Home, daily digest).
* **Name** — BUY / WATCH / AVOID from the council (Stock Analyzer, Predictive
  Analysis).

**The page a reader acts from — Opportunity Hub — carries neither.** It ranks by
score and confluence and stops there. The final call the reference model reserves
for the human is made on a page that shows a rank, not a verdict ([[#B-109]]).

## The one thing that was actually broken — FIXED 2026-09-21

`Liquidity Sweep Bear` is registered `category: "Risk"`, runs in the pipeline —
and **is not in `RISK_SCANNERS`**, so it does not raise a risk flag. It falls
through `tally_evidence`'s unmapped branch and **casts a 0.5 bullish confluence
vote**. Verified live:

```
Liquidity Sweep Bear   cat=Risk  tier=unmeasured  weight=0.5
                       → families=['Liquidity Sweep Bear']  points=0.5  riskflags=[]
Downside Risk          cat=Risk  tier=risk        weight=0.0
                       → families=[]  points=0     riskflags=['Downside Risk']
```

A bearish detector was **evidence FOR** a name. This is the exact failure
`test_support_breakdown_retired.py` was written to prevent for a different
scanner — per-scanner, so it did not generalise.

**Fixed the same day** ([[#B-105]]): one line in `RISK_SCANNERS`, and
`tools/test_risk_scanner_invariants.py` now holds the invariant over the whole
registry in both directions (plus the matching one for `Neutral` /
`NEUTRAL_SCANNERS`). Blast radius was counted rather than assumed: **2 stored
shortlist rows, both QUADFUTURE** — 5 families / 2.50 points → 4 / 2.00, and
6 / 2.75 → 5 / 2.25. Both were already at 100% confluence on their bullish
evidence alone, so **no ranking moved**; what moved is that the note stops
listing a bearish detector among the families supporting the name.

## What this audit does NOT recommend

Rebuilding the nav to match the diagram one-for-one. The reference model is a
*trading system*; this desk is a personal research desk, and the stages map to it
loosely on purpose — SCAN is nine
pages because the owner asks nine different questions, not because the IA drifted.
The mapping is worth making **visible**; making it **literal** is a separate
decision and is filed as an owner call, not a task.
