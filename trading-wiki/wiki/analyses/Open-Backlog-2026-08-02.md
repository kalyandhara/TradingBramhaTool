---
title: "Open Backlog — as of 2026-08-02"
category: analysis
tags: [backlog, roadmap, open-items, technical-debt, data-quality]
timeframe: milestone-plan
created: 2026-08-02
updated: 2026-08-05
sources: 0
related: [analyses/Sector-Rotation-Orbit-Data-Source-Roadmap, analyses/Astro-Weekly-Forecast-Card-Fit, analyses/Dashboard-UI-Roadmap, analyses/Backtest-Harness, concepts/Mean-Reversion, concepts/Breakout, concepts/Volume-Analysis]
---

# Analysis: Open Backlog — as of 2026-08-02

Everything left open at the end of the 2026-08-02 session, in one place. Items that already live on a dedicated roadmap are **pointers, not copies** — the roadmap stays authoritative.

**Nothing here is pushed.** The entire session sits on local `master`.

---

## P1 — Correctness, and live right now

### B-1 · Sentiment computes on a partial fetch and does not say so
**The sharpest item on this list.** The 2026-08-02 refresh reported sector participation over **3 sector indices**; the reading it replaced used **11**. `sentiment_index._sector_perf` divides by however many it happened to fetch, so a 3-of-11 fetch produces a confident-looking factor from a quarter of the evidence — and that factor fed an **AGGRESSIVE verdict at 100% position size, max 4 trades**.

[market_health.py](tools/market_health.py) already solved this exact problem: it reports coverage and returns `NOT_CHECKED` below 50% rather than scoring whichever names survived. `sentiment_index` has no equivalent.

**Fix:** carry `n_fetched / n_expected` on every component, surface it on the reading, and refuse to score a component below a coverage floor. *Same silent-partial-result shape logged five times already this session — this is the first instance sitting under a live sizing decision.*

> [!key-insight] **B-1 FIXED 2026-08-05 — and the diagnosis was wrong**
> It was never a flaky partial fetch. **Yahoo stopped updating 8 of the 11 NSE
> sector indices on 2026-07-17**; ^CNXIT, ^CNXPHARMA and ^NSEBANK kept going. All
> eight stale feeds carry an *identical* last bar, 19 days old at time of fix.
> So the "3 of 11" was never a random sample — it was **the only three feeds
> still alive**, and on 08-03 all three happened to be green → factor 1.0 → a
> full 25/25.
>
> **The obvious fix would have made it worse.** `period="10d"` returns a single
> stub row for a frozen ticker, so `len(hist) < 2` skipped it *silently* — and
> widening the window to "get more coverage" would have computed a change between
> two **July** closes and presented it as today's move. Coverage counting alone
> would have reported a confident 11/11. **The missing primitive was freshness,
> not coverage.** Both are now enforced: bars older than `MAX_STALE_DAYS` are
> rejected, and stale is reported separately from missing, because a frozen feed
> and a failed fetch call for different responses.
>
> **A second bug was introduced and caught in the same change.** Giving the
> component `score = 0.0` fed `market_verdict._component_flags`' `score / weight`
> fallback, which read `factor = 0.0` — under `CAUTION_AT` — so an input we
> merely could not measure would have cast a *bearish* vote and could have forced
> STAND DOWN. **The exact mirror of B-1.** NOT_CHECKED components now **abstain**,
> per the precedent `market_health` already set ("never counts toward the 2-fail
> gate"), and are surfaced on the verdict card as *Not checked* rather than
> silently thinning the flag lists.
>
> **Measured effect on the live verdict:** old path → sector factor 1.0, a second
> favorable vote, **AGGRESSIVE / 4 trades**. New path → **TRADE / 3 trades**, with
> the sector line reading *"NOT CHECKED — only 3/11 sector indices usable (8 stale
> up to 19d old)"*. Position size stays 100% (TRADE and AGGRESSIVE deliberately
> share it), so the honest headline is **fewer trades and a stated basis**, not a
> smaller position.
>
> The composite now **renormalises over measurable weight** rather than summing a
> silent zero — 59.59 on 75/100 weight, not 44.69 — and the whole reading goes
> `NOT_CHECKED` below the same 50% floor. Verified: 4 renormalisation edge cases
> incl. zero-measurable (no div-by-zero), live component + composite + verdict,
> DB round-trip, and a clean app boot on a throwaway port.
>
> ⚠️ **Wider blast radius, NOT fixed here.** The **RRG and Sector Map read the
> same 11 tickers** (`SECTOR_DISPLAY_NAMES`) with `period="2y"`, so all 11 return
> data and **8 of them are plotted as-of 2026-07-17 against 3 as-of today** — the
> quadrants compare sectors measured 19 days apart, and the page reports "11/11
> sectors, 0 skipped". Same root cause, bigger surface. Needs the same freshness
> check.

### B-2 · chart_server restart pending
`8a5144b` makes an unknown timeframe return **400** instead of silently serving daily. The running process on port 5001 predates it, so `?timeframe=1wk` still answers `200` with daily bars. One restart.

---

## P2 — Capability gaps (the tool contradicts its own advice)

### B-3 · No mean-reversion scanner
`market_verdict.REGIME_PLAYBOOKS["SIDEWAYS"]` tells the user *"Range-bound. Mean-reversion works, breakouts fake out."* The `SCANNERS` registry holds ~24 scanners that are almost entirely breakout/trend/continuation. **On a SIDEWAYS day the dashboard prescribes one playbook and offers two dozen tools for the opposite one.**

Every input exists: Wilder `_rsi_series`, ATR, rolling z-scores in [rrg.py](tools/rrg.py). Spec is written on [[concepts/Mean-Reversion]] — stretch in z or ATR, close-back-inside trigger, 2-ATR stop, target at the mean, 10-bar time stop.

### B-4 · Anchored VWAP anchors only to swing lows
Without a high-anchored line the chart cannot express **"no man's land"** — it can say buyers are in profit, never that *neither* side is. That third state is the whole value of the dual-anchor read ([[concepts/Anchored-VWAP-Pyramiding]]). Highest-value change to the indicator.

### B-5 · No time dimension in any scanner plan
Every structured plan emits entry/stop/target and nothing that closes a trade which simply never resolves. [[concepts/Mean-Reversion]] names the ~10-bar time stop as standard and we implement it nowhere.

### B-6 · Retest entries are barely modelled
Both breakout sources call the **retest** the higher-quality entry ([[concepts/Breakout]]); `scan_order_block` is the only scanner that triggers on one rather than on the break itself.

---

## P3 — Measurable claims currently taken on faith

Each of these is fully specified and can go straight through [[analyses/Backtest-Harness]], which has already shown its worth by finding only 1 of 5 scanners beating a random-entry baseline.

### B-7 · Volume-confirmation threshold sweep
**Five numbers for one concept**, every one asserted as a rule: `1.2×`/20 (ForexTester breakout) · `1.5×`/20 (ForexTester volume — *same publisher*) · `1.5×`/20d (our breakout scanners) · `1.5×`/50 (our VCP) · `1.4×`/50-DMA (our structural breakout). No source cites data. Sweep it on our universe and pick one, or document why they differ. See [[concepts/Volume-Analysis]].

### B-8 · Stops in mean reversion — the Connors contradiction
[[strategies/Quantified-MA-Mean-Reversion]] uses **no stop** (its backtests found stops removed the edge); [[sources/ForexTester-Mean-Reversion-Guide]] makes 1–2 ATR stops mandatory. Run one reversion entry with and without a 2-ATR stop and settle it.

### B-9 · Volume Profile 80% rule
Price entering the value area and holding 2 consecutive 30-min bars → claimed ~80% chance of a full VAL→VAH traverse. A vendor claim with no data behind it, but fully specified. Testable on NSE 30-min data.

---

## P4 — Smaller, or already scoped elsewhere

| | Item | Notes |
|---|---|---|
| B-10 | **4 Nifty 500 symbols uncached** | `ABBOTINDIA`, `BAYERCROP`, `MCX` returned *"no filings"* from `corporate-share-holdings-master`; `BSE` has no cache file at all. All four are large and liquid and certainly do file — so **"no filings" is probably our bug, not NSE's**. First suspect: the `f["symbol"].upper() == symbol.upper()` filter in `get_shareholding_filings`. 496/500 cached. |
| B-11 | **MFI absent from the repo** | Volume-weighted RSI; Wilder `_rsi_series` already exists, so it is cheap. [[concepts/Volume-Analysis]] |
| B-12 | **AVWAP has no click-to-anchor** | Anchor selection is *"the most subjective and most critical aspect"*; we automated it away, so earnings / breakout / IPO / macro anchors are unreachable. |
| B-13 | **AW-1…AW-4** — astro weekly card | Good-to-have. AW-0 shipped. [[analyses/Astro-Weekly-Forecast-Card-Fit]] |
| B-14 | **`ephem` not installed** | The reversal calendar cannot be rebuilt; coverage ends **2027-12-28**, so ~17 months of runway. `pip install ephem`. |
| B-15 | **SR-7 — Trendlyne backfill** | Optional, only if XBRL coverage proves short. [[analyses/Sector-Rotation-Orbit-Data-Source-Roadmap]] |
| B-16 | **OI Momentum off-palette colours** | A second `_strength_color` map (`dashboard_app.py` ~5780) with the same hard-coded hexes already removed elsewhere. |
| B-17 | **OBV has no wiki page** | Ships as a chart indicator, undocumented. |
| B-18 | **Nothing pushed** | Whole session local on `master`. |

---

## Thesis
The session's recurring finding is worth stating once, because it now has six instances and predicts where the next bug will be:

> **Nothing here ever threw an exception.** DS-2's regexes matched nothing. `build_dataset` returned an empty frame. A 403 sat behind it. A z-score divided by ~1e-14. A full moon rendered as "waning, 16.7%". Sentiment scored on 3 of 11 indices. **Every one produced a confident-looking number with nothing behind it.**

The defence is the same each time and is cheap: **carry coverage with the data, and refuse to score below a floor.** `market_health` does it; `red_flags` does it with its three-state NOT_CHECKED; `rrg` does it by omitting unmeasurable sectors. B-1 is the same fix applied to the one component still missing it.

## Action Taken / Plan
- **Nothing built.** This page is the index.
- **Suggested order:** B-1 (live, under a sizing decision) → B-2 (one restart) → B-3 (the advice/tooling contradiction) → B-7 (settles five open numbers at once) → the rest.

## Outcome (fill in later)
- *2026-08-02:* Backlog opened with 18 items. 496/500 ownership backfill complete; SR-0…SR-6 and AW-0 shipped this session.
