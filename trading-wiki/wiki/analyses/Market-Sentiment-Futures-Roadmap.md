---
title: "Market Sentiment — Futures & Global Cues Roadmap (index futures on the Sentiment page)"
category: analysis
tags: [roadmap, market-sentiment, futures, index-futures, gift-nifty, global-cues, basis, dashboard]
timeframe: milestone-plan
created: 2026-07-25
updated: 2026-07-25
sources: 0
related:
  - analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14.md
  - concepts/Market-Sentiment-Index.md
  - analyses/Dashboard-UI-Roadmap.md
---

# Analysis: Market Sentiment — Futures & Global Cues Roadmap

## Thesis
Add a **"Futures & Global Cues"** section to the **Market Sentiment** page that
displays the *future indexes* traders check for pre-market / overnight bias:
- **NSE index futures** — NIFTY / Bank Nifty / Fin Nifty near-month **premium/
  discount to spot (basis)** + open interest;
- **GIFT Nifty** — the pre-market gauge for the expected NIFTY **gap-up / gap-down**;
- **Global index futures** — Dow / Nasdaq / S&P (and Asian: Nikkei / Hang Seng) for
  overnight cues.

**Interpretation note:** "future indexes" is read here as **index *futures* / global
futures as a sentiment display** (not forward-looking price *forecasts* — that's the
separate projection engine). If forecasts were meant, this roadmap doesn't cover it —
flag and I'll refocus.

**Grounded finding: most of the data is already in hand.** The F&O bhavcopy we
already fetch daily carries index futures; global futures are login-free on yfinance;
NIFTY spot already loads. The one genuine gap is a **live GIFT Nifty** feed.

## Current State (grounded audit, 2026-07-25)
| Piece | What exists today | Where | Gap |
|---|---|---|---|
| **NSE index futures (NIFTY/BankNifty/FinNifty)** — price, OI, basis | The **F&O bhavcopy is already fetched** and it tags **index futures (IDF instrument type)** | [nse_oi_momentum.py](tools/nse_oi_momentum.py) `fetch_fo_bhavcopy` (OI Momentum uses the *stock*-futures slice) | just filter to IDF + join spot for the basis — **EOD** (not live) |
| **NIFTY spot** (for the basis + gap) | `fetch_nifty50` / cached | [screener_pipeline.py](tools/screener_pipeline.py), dashboard | ✅ have |
| **Global index futures** (Dow `YM=F`, Nasdaq `NQ=F`, S&P `ES=F`) + Asian indices (`^N225`, `^HSI`) | yfinance, **login-free** | [data_source.py](tools/data_source.py) yfinance path | ✅ reachable — just fetch %-change |
| **GIFT Nifty (live pre-market)** | — | — | ❌ **not available** — NSE-IX / a vendor / a scraper; the real dependency |
| **Sentiment page to host it** | "Phase 1: 4-input composite gauge" (Adv/Decl · Sector · SMA200 · PMax-1H) | [dashboard_app.py](tools/dashboard_app.py) `Market Sentiment`; [sentiment_index.py](tools/sentiment_index.py) | add a panel; optionally a scored input |

> [!key-insight] The index-futures data is already on disk
> `fetch_fo_bhavcopy()` (built for OI Momentum's *stock* futures) pulls the **whole**
> F&O bhavcopy — index futures included (IDF). The NIFTY/BankNifty basis + OI are a
> filter-and-join away, no new source. Global cues are a login-free yfinance fetch.
> Only **GIFT Nifty live** needs a new feed.

## The gap (what's actually new)
1. **A live GIFT Nifty source** — the pre-market gauge is the most-wanted piece and the
   only hard dependency (EOD bhavcopy can't give the overnight gap). Options: NSE
   International Exchange (GIFT) data, a data vendor, a light scraper, or a **manual
   entry** fallback so the panel never blocks.
2. **A live intraday basis** — the bhavcopy basis is **EOD**; an intraday premium/discount
   needs a live futures quote (yfinance NIFTY-fut coverage is unreliable; may ride the
   same GIFT/vendor source).
3. **The display panel** on the Sentiment page (+ optional scoring integration).

## Evidence For
- **~70% composition** — index-futures data already fetched; global cues login-free;
  NIFTY spot already loaded. Mostly a filter/join + a panel.
- **Directly serves the daily workflow** — the 8:30 AM pre-market step in the dashboard's
  own daily-workflow table is *exactly* "check overnight cues / build watchlist"; GIFT
  Nifty + global futures are what fills it.
- **Natural extension of the Sentiment page's phased plan** — it already reserves Phase 2
  for PCR; futures cues slot in beside it as regime/overnight context.

## Evidence Against
- **GIFT Nifty live data is a real, possibly-fragile dependency** — scrapers/vendors for
  it have historically been flaky (same lesson as the screener.in session in
  [[analyses/PEAD-Scanner-Roadmap]] 5.1). Keep it optional / manual-fallback so it never
  blocks the page.
- **EOD basis ≠ live sentiment** — a bhavcopy premium/discount is yesterday's positioning;
  useful as context, but don't present it as a live intraday read.
- **Global-cue relevance is regime-dependent** — overnight US/Asia cues drive the NIFTY
  open some days and not others; show them as context, don't over-weight into the score.
- **Don't double-count** — if a futures factor is folded into the composite (MSF-4), make
  sure it isn't just re-expressing the SMA200/PMax regime already scored.

## Phased plan (for later — not started)
- **MSF-1 — Global cues strip (login-free, easiest).** A row on the Sentiment page:
  Dow / Nasdaq / S&P futures + Nikkei / Hang Seng — %-change, red/green, "as of" time.
  Pure yfinance fetch; display only. Ships the overnight-cues value with zero new source.
- **MSF-2 — NSE index-futures basis panel.** Filter the already-fetched F&O bhavcopy to
  **index futures (IDF)**, join NIFTY/BankNifty/FinNifty spot → **premium/discount % + OI
  (+ OI change)**; label premium=bullish-carry / discount=bearish. EOD, honestly labelled.
- **MSF-3 — GIFT Nifty pre-market gauge.** Expected NIFTY **gap** = GIFT level − NIFTY
  spot close, with a bull/bear tint. Needs a live source — ship with a **manual-entry /
  best-effort fetch** fallback so the panel degrades gracefully when the feed is down.
- **MSF-4 — (optional) fold a futures factor into the composite score.** A small,
  carefully-weighted "futures & cues" input (basis sign + GIFT gap + global tilt); only
  after it's shown *not* to duplicate the existing regime inputs, and **backtested**
  (via [[analyses/Backtest-Harness]] discipline) to confirm it improves the gauge.
- Sequencing rule (inherited): don't start MSF-N until MSF-(N−1) ships + one live session.
- **Packaging:** native dashboard feature — a section on the Market Sentiment page.

## Action Taken / Plan
- ✅ Roadmap filed (2026-07-25). Cross-linked from the parent
  [[analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14]]. **Nothing built.**
- ⏭ When ready: **MSF-1** first (global cues strip — login-free, no dependency), then
  MSF-2 (index-futures basis off the bhavcopy we already fetch).

## Outcome (fill in later)
- _2026-07-25: filed. Awaiting go-ahead on MSF-1 (and confirmation of the "index futures
  vs forecasts" interpretation)._

## Related Pages
- [[analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14]] — the parent Sentiment-page roadmap this extends.
- [[concepts/Market-Sentiment-Index]] — the composite gauge's definition.
- [[analyses/Dashboard-UI-Roadmap]] — the dashboard this sits in.
