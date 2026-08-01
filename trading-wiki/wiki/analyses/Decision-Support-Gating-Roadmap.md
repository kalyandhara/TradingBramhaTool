---
title: "Decision-Support Roadmap — Market-Health + Ownership-Flow Gating"
category: analysis
tags: [roadmap, decision-support, market-health, ownership-flow, fpv, gating, shareholding, dashboard]
timeframe: milestone-plan
created: 2026-07-21
updated: 2026-08-01
sources: 1
related:
  - sources/Crash-Proof-Market-Health-Ownership-Framework.md
  - strategies/Crash-Proof-3-Filter-System.md
  - concepts/FPV-Flow-Price-Volume-Ownership.md
  - analyses/Dashboard-UI-Roadmap.md
---

# Analysis: Decision-Support Roadmap — Market-Health + Ownership-Flow Gating

## Thesis
The [[strategies/Crash-Proof-3-Filter-System]] is a **gate stack**: Market health → Stage → Ownership, each able only to veto. The dashboard already computes most of the pieces in isolation — a market verdict, Stage-2 scans, an FII-change fetch, an OI-momentum read. What's missing is the **gating surface** that fuses them into one "may I trade today, and this name?" answer, plus the two genuine data gaps (full ownership split; a market-health gate on the framework's own five conditions).

This roadmap sequences that as a distinct workstream, feeding [[analyses/Dashboard-UI-Roadmap]] Phase 2 ("turn ingested knowledge into features"). Like that roadmap, each item ships value alone.

## Current State (grounded, 2026-07-21)

| Framework filter | Nearest existing surface | Gap |
|---|---|---|
| **A · Market health** ("2 of 5 fail → stand down") | Market Sentiment page + [market_verdict.py](tools/market_verdict.py) already emits **STAND DOWN / SELECTIVE / TRADE / AGGRESSIVE** on a "2+ caution flags → STAND DOWN" ladder | Verdict uses Nifty vs **200 SMA**, PMax trend, sector participation, advance/decline. Framework wants Nifty vs **50 EMA**, "breakouts working", "leaders strong", "volatility low" — partial overlap; three conditions unmodelled |
| **B · Stock stage** | Scanner Hub Stage-2 scan + **Overall Rating /100** (M1, shipped 2026-07-20); Setup Intelligence panel | Largely built. Stage-2 is a scanner template; rating rollup exists |
| **C · Ownership flow** | [nse_shareholding_fetch.py](tools/nse_shareholding_fetch.py) fetches **FII holding change only** | **DII / MF / Retail legs missing** — the framework's rotation read (MF↓ supply, retail↓ noise, DII stable) can't be computed yet |
| **FPV confirmation** (price+volume+ownership) | **OI Momentum** ([nse_oi_momentum.py](tools/nse_oi_momentum.py), new) reads price vs OI — a price+positioning cousin | The unified price+volume+ownership readout is not built as one panel |
| **Combination matrix** (market × ownership) | — | **Not built.** This is the novel decision surface the framework is really about |

> [!key-insight] The market-health kill switch is ~80% built
> [market_verdict.py](tools/market_verdict.py) already collapses breadth + regime + participation into a STAND DOWN verdict on the exact "2+ conditions fail" logic the framework specifies. This roadmap extends an existing engine, it does not start one.

## Conclusion — four phases

Sequenced cheapest-and-most-grounded first. Effort in the house style of [[analyses/Dashboard-UI-Roadmap]].

### DS-1 — Align the market-health gate to the framework's five conditions — ✅ SHIPPED 2026-08-01
**Goal:** the Market Sentiment verdict explicitly reports the framework's five conditions (Nifty>50 EMA · breadth positive · breakouts working · leaders strong · volatility low) and applies the **2-of-5 → STAND DOWN** rule.
- **Data:** breadth + regime + sector participation already feed `market_verdict`. Add: Nifty-vs-50-EMA (trivial), a volatility read (India VIX or realised vol — VIX fetch may be new), "breakouts working" (share of recent Scanner Hub breakouts still holding — derivable), "leaders strong" (leadership-basket trend — derivable from sector map / RS).
- **UI:** a 5-lamp checklist on the Market Sentiment page above the existing verdict; the verdict's caution ladder already renders.
- **Effort:** 2–3h if VIX/vol is the only new fetch. Mostly wiring existing signals into named lamps.
- **Ships value:** turns the framework's master rule into a glanceable go/no-go, reusing the verdict engine.

### DS-2 — Full ownership split (close the data gap for Filter C)
**Goal:** fetch the whole shareholding pattern — **FII / DII / MF / Retail / Promoter** quarter-over-quarter — not just FII change.
- **Data:** extend [nse_shareholding_fetch.py](tools/nse_shareholding_fetch.py); the BSE/NSE shareholding-pattern XBRL already parsed for FII carries the other categories (see [[sources/BSEIndia-Public-API-Corporate-Data-2026]]).
- **UI:** an ownership-rotation card on the Stock Analyzer / India Market Intel: four arrows (FII↑ MF↓ Retail↓ DII→) with the smart-money-rotation interpretation from [[concepts/FPV-Flow-Price-Volume-Ownership]].
- **Effort:** 3–5h — mostly XBRL tag discovery for DII/MF/retail, mirroring the existing FII parser.
- **Ships value:** unlocks Filter C and the whole ownership leg of FPV. Prerequisite for DS-3.

### DS-3 — The combination matrix (the novel decision surface)
**Goal:** one panel that crosses **market health × ownership flow** and prints the framework's action cell:
- Weak + FII↑ → *Accumulate watchlist, don't buy yet*
- Strong + FII↑ → *High-conviction breakouts allowed*
- Weak + MF↓ → *Avoid fresh trades*
- **Data:** market-health state from DS-1, ownership state from DS-2. No new source.
- **UI:** a small matrix on the Stock Analyzer, with the current cell highlighted and the instruction spelled out; gated so it only turns "trade" green when Stage (Filter B) also passes.
- **Effort:** 3–4h composition once DS-1 + DS-2 land.
- **Ships value:** this is the "reference for action decision" the user asked for — the three filters resolved to one instruction.

### DS-4 — FPV confirmation readout (timing)
**Goal:** a price+volume+ownership panel emitting the four FPV combinations (strong trend / weak trend / smart-money accumulation / late trend) per [[concepts/FPV-Flow-Price-Volume-Ownership]].
- **Data:** price+volume daily (already in every chart), ownership from DS-2, positioning cross-check from **OI Momentum**.
- **UI:** an FPV chip on the Stock Analyzer, shown only after DS-3 permits a trade — timing after permission, never before.
- **Effort:** 2–3h once DS-2 lands.
- **Ships value:** entry timing, the last leg. Deliberately last so FPV can't be read as a standalone buy signal — the same overtrust discipline that put M3 (projection) last in the main roadmap.

## Evidence For
- **The kill switch is nearly free** — DS-1 extends `market_verdict.py`, which already does the 2+-conditions logic.
- **One real data gap (DS-2)** unblocks two features (Filter C + FPV ownership leg); everything else is composition of signals already computed.
- **The user asked for exactly this** — an actionable decision reference, not another indicator.

## Evidence Against
- **Ownership is quarterly and lagging.** DS-2/DS-3/DS-4 lean on data that updates per filing; a stale ownership read could imply conviction that has already rotated. Timestamp every ownership reading (wiki convention: "price levels decay").
- **Gate stacks can over-filter.** Three vetoes plus FPV may keep the user flat so often that good trades are missed; DS-1's thresholds need one live regime to calibrate before trusting the STAND DOWN count.
- **"80% of losses prevented" is unmeasured** — see the backtest note in [[strategies/Crash-Proof-3-Filter-System]]. DS-work should not present the gate as validated until [[analyses/Dashboard-UI-Roadmap]] Phase 3 measures it.

## Action Taken / Plan
- **Sequencing rule (inherited):** don't start DS-N until DS-(N−1) ships and gets one session of live use. Prevents shipping the FPV chip before the ownership data that makes it honest.
- ✅ **DS-1 SHIPPED 2026-08-01** — [market_health.py](tools/market_health.py) + a five-lamp panel on the Market Sentiment page. See Outcome.
- ⏭ **DS-2 is next and is the real work** — the FII/DII/MF/Retail split is the only genuine data gap in this roadmap, and it gates both DS-3 and DS-4.
- **Relationship to the main roadmap:** this is the concrete expansion of [[analyses/Dashboard-UI-Roadmap]] Phase 2's "turn ingested knowledge into features" line, for the market-health/ownership theme specifically.

## Outcome (fill in later)
- _2026-07-21: filed from the crash-proof framework ingest. Nothing built yet._
- **2026-08-01 — DS-1 SHIPPED, verified & deployed.** [market_health.py](tools/market_health.py)
  models all five conditions by name with the framework's 2-of-5 rule. The estimate held
  (India VIX was the only new fetch, and `^INDIAVIX` resolves on yfinance login-free), but
  two things were worth more than the wiring:
  - **The third state.** Every condition returns PASS / FAIL / **NOT_CHECKED**, the last
    never counting toward the gate, and a gate with **nothing** measured returns
    **NOT ASSESSED** rather than CLEAR. Two guard rails enforce it: a basket under 50%
    fetch coverage refuses to judge, and a tape with fewer than 5 breakouts refuses to
    read its own silence as "breakouts fail". Both are the *data-fault-wearing-a-market-
    result's-clothes* shape this repo keeps hitting (the throttled fan-out, the NaN
    forming bar).
  - **It is NOT folded into the ribbon verdict**, against the letter of the plan above.
    Breadth and regime feed both engines; adding these failures to `build_verdict`'s
    caution count double-penalises the same weakness with no lamp to explain it. Fusion
    is DS-3's job, where the interaction is the actual product. It renders beside the
    composite as a second opinion.
  - **The two engines disagreed immediately, and that is the point.** On 2026-08-01 the
    ribbon read **STAND DOWN** while Filter A read **CLEAR (1 of 5 failed)**: NIFTY was
    **+1.52% above its 50 EMA** (the framework's level) and **−2.17% below its 200 SMA**
    (the ribbon's). A single aggregate verdict could not have surfaced that; five named
    lamps make it arguable per condition.
  - **Live read** (60-name basket, 56/60 coverage): 50 EMA PASS · breadth **FAIL**
    (700 adv / 1,682 decl) · breakouts PASS (32/50 holding) · leaders PASS (11/11 above
    their 21 EMA) · volatility PASS (VIX 11.76 vs 16.41 median). Conditions 1/2/5 are
    nearly free and render on load; 3/4 sit behind a button, cached 30 min.
  - **Still hand-set.** No threshold here is backtested — the caveat in
    [[strategies/Crash-Proof-3-Filter-System]] stands, and the "prevents 80% of losses"
    claim remains the source author's.

## Related Pages
- [[strategies/Crash-Proof-3-Filter-System]] — the system this roadmap surfaces.
- [[concepts/FPV-Flow-Price-Volume-Ownership]] — the confirmation concept (and the FPV naming-collision flag).
- [[analyses/Dashboard-UI-Roadmap]] — the parent roadmap; this is its Phase 2 expansion.
- [[sources/Crash-Proof-Market-Health-Ownership-Framework]] — the source.
