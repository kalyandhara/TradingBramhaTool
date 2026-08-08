---
title: "Open Backlog — the living index"
category: analysis
tags: [backlog, index, roadmap, open-items, measurement-debt]
timeframe: milestone-plan
created: 2026-08-07
updated: 2026-08-07
sources: 0
related:
  - analyses/Open-Backlog-2026-08-02.md
  - analyses/Backtest-Harness.md
  - analyses/OI-Momentum-Gap-Audit.md
  - analyses/Dashboard-UI-Roadmap.md
---

# Analysis: Open Backlog — the living index

**Supersedes [[analyses/Open-Backlog-2026-08-02]]**, which is kept as the
historical snapshot it was.

**This page is deliberately undated in its filename.** The previous one carried
`2026-08-02` and was stale within five days — two items closed, one turned out
worse than recorded, and seven new ones appeared, while `index.md` still
described it as "the single index of everything left open". An index that goes
stale by construction is not an index. This one gets updated in place; dated
snapshots can be cut from it when a session wants one.

Statuses below were **re-verified against the code on 2026-08-07**, not carried
forward from the previous page. Two of them had changed and nobody had noticed.

## Status since 2026-08-02

| | |
|---|---|
| **Closed** | B-1 (2026-08-05), B-14 (`ephem` now installed) |
| **Worse than recorded** | B-5 — the capability is plumbed and used by nothing |
| **Still open** | B-2, B-3, B-4, B-6 … B-13, B-15, B-16, B-17, B-18 |
| **New** | B-19 … B-27, mostly from the 2026-08-07 OI/PCR/divergence session |

---

## P0 — Live right now

### B-2 · chart_server restart pending — now blocking
Was cosmetic, is not any more. The **`/rsi_divergence.js` route added
2026-08-07 does not exist on the running server**, and Flask does not hot-reload,
so the RSI divergence indicator shipped that day cannot load until `start.bat` is
re-run. One restart, and it unblocks work already paid for.

### B-18 · Nothing pushed, and there is nowhere to push to
Verified 2026-08-07: `git remote -v` is **empty**. This is not "a push is
pending" — there is no remote configured at all, so every commit in this repo's
history exists on one machine, on one branch, with no off-site copy. Six commits
landed on 2026-08-07 alone.

### B-16 · OI Momentum off-palette colours
`_strength_color` at [dashboard_app.py:6648](tools/dashboard_app.py:6648) still
carries hard-coded hexes of the kind removed everywhere else. Noted because that
page was edited four times on 2026-08-07 without anyone fixing it — proximity is
not the same as attention.

---

## P1 — The measurement debt

**The dominant theme, and 2026-08-07 made it larger rather than smaller.** Every
feature shipped that day annotates or refines a grade that has itself never been
validated.

### B-19 · Nothing shipped in the 2026-08-07 session is backtested
The OI quadrant, PCR, RSI divergence, family-capped confluence and the level
tags are all unmeasured. Each is *labelled* as such in its own UI, which is the
minimum honest thing, but the stack is now several layers of unvalidated
refinement on an unvalidated base.

### B-25 · Confluence itself is unmeasured
`backtest.py` measures scanners one at a time. **No test exists that co-firing
beats single-firing**, which is the entire premise of the Opportunity Hub's
ranking. Small to close: replay two scanners and compare forward returns on
co-firing versus single-firing bars.

### B-20a · The harness has no significance test
Verified previously: zero occurrences of t-stat / p-value / CI in
`backtest.py`. So *"Falling Wedge +0.74% @20d"* and *"Harmonic +0.25R, n=122"*
are point estimates with **no stated probability of being noise** — in the one
module whose whole purpose is the credibility check.

### B-20b · Edge is not risk-adjusted
Subtracting the average bar implicitly assumes **β = 1 for every name**, so a
scanner that fires on high-beta names shows "edge" that is beta being paid — and
the sample is a mostly-constructive ~6y tape, exactly when that bias is largest.
Closed by a standard market-model event study; `scipy`/`statsmodels` already
installed. See [[analyses/Backtest-Harness]].

### B-21 · Single-window, no costs
One ~6y window, survivorship-biased, gross returns. Needs walk-forward and
transaction costs before any scanner is called validated.

### B-7 · Volume-confirmation threshold sweep
**Five conflicting values** across the repo, including one publisher printing
1.2× and 1.5× weeks apart. Fully specified and directly runnable through the
harness; settles five open numbers at once.

### B-8 · Stops in mean reversion — the Connors contradiction
### B-9 · Volume Profile 80% rule
Both fully specified, both still taken on faith.

---

## P2 — Capability gaps (the tool contradicts its own advice)

### B-3 · No mean-reversion scanner
`REGIME_PLAYBOOKS["SIDEWAYS"]` prescribes one and nothing implements it.
Re-checked 2026-08-07: the registry's nearest names — Pullback Entry, Early
Reversal Detector, Harmonic Reversal — are with-trend entries or reversal
*structure*, not the Connors-style stretch-and-revert the playbook means.

### B-5 · Time stops: plumbed, and emitted by nothing — *worse than recorded*
The previous page called this "no time dimension in any scanner plan" and
[[analyses/Backtest-Harness]] recorded `time_stop` support as shipped 2026-08-05.
Verified 2026-08-07: **`time_stop` appears in `backtest.py` only — five
occurrences, all consuming it — and in `scanner_templates.py` zero times.** The
harness faithfully reads a field no scanner has ever written. A trade that
neither works nor fails is still a loss with the loss deferred, and nothing here
can express that.

### B-19b · No support-breakdown detector exists anywhere
New 2026-08-07, found while building the OI level linkage. Verified: **zero
occurrences** of breakdown detection in the codebase. We detect resistance
breaks and have nothing for the mirror, so the **bearish half** of the standard
confirmation rule (price down + OI up + volume up + *support breakdown*) has
nothing behind it but range position. This also explains why composing
`scan_structural_breakout` into the OI table reached only 7% of rows.

### B-4 / B-12 · AVWAP anchors only to swing lows, no click-to-anchor
Anchor choice is the most subjective and most critical part of AVWAP and we
automated it away, so earnings / breakout / IPO / macro anchors are unreachable.

### B-6 · Retest entries barely modelled
Recorded repo asymmetry: **we detect breaks well and retests poorly.**

### B-11 · MFI absent
Verified absent 2026-08-07. Wilder `_rsi_series` already exists, so it is cheap.

---

## P3 — Consistency and correctness debt

### B-24 · Two RSI-divergence implementations that disagree
`detect_bullish_rsi_divergence` in `scanner_templates.py` uses a **rolling-mean
RSI** (not Wilder), tests *last bar vs min of prior 10* rather than swing pivots,
and covers **1 of the 4** variants — while `rsi_divergence.js` shipped
2026-08-07 does all four off shared zigzag pivots. The Python one feeds Early
Reversal's score, so the chart and the scanner will disagree about the same
chart. The JS/Python split is unavoidable; the *definitions* diverging is not.

### B-26 · `MIN_PRICE_PCT` contradicts its own stated rationale
The comment says the floors "sit just above those medians". Measured over 12
sessions that is true of `MIN_OI_PCT` (1.5 against a 1.43 median) and **false of
`MIN_PRICE_PCT` (0.5 against a 0.90 median)** — the price floor is far more
permissive than documented. Deliberately left unchanged, because altering it
would silently re-grade the whole stock universe; recorded in the module so the
rationale stops misleading. Decide it on purpose rather than by inheritance.

### B-21b · Every floor set on 2026-08-07 came from one session
PCR percentile cuts and liquidity floors, the 1.0× rvol veto, the 5-session
volume window, and the index OI floors were each calibrated on a single day's
cross-section (or 12 sessions in the index case). All are labelled as such in
code. **One session is not a distribution** — re-measure before trusting them.

### B-10 · Four Nifty-500 symbols uncached
Re-verified 2026-08-07: still **496** symbols cached. `ABBOTINDIA`, `BAYERCROP`,
`MCX` return *"no filings"* and `BSE` has no cache file, though all four are
large, liquid and certainly file. First suspect remains the
`f["symbol"].upper() == symbol.upper()` filter in `get_shareholding_filings` —
**probably our bug, not NSE's.**

---

## P4 — Scoped elsewhere, or small

| | Item | Notes |
|---|---|---|
| B-20 | **Index PCR has no history, so no band** | `index_reading()` ships deliberately unbanded. Five same-day observations cannot be ranked; an index can only be ranked against its own past. Storing a daily index PCR is the whole fix. |
| B-22 | **Sentiment Index factor 5 unwired** | `pcr.py` exists and is the primitive that factor was always waiting for; nothing consumes it there yet. |
| B-23 | **Strike-level option OI** (OI audit Gap 3) | The largest remaining OI item. Needs per-strike treatment, not an underlying-level sum — its own design pass. |
| B-13 | AW-1…AW-4 astro weekly card | Good-to-have; AW-0 shipped. |
| B-15 | SR-7 Trendlyne backfill | Optional, only if XBRL coverage proves short. |
| B-17 | OBV has no wiki page | Verified absent; ships as a chart indicator, undocumented. |
| B-27 | **Wiki hygiene** | Index counters had drifted to two *different* wrong numbers (frontmatter 204/78, body 198/81, actual 226/91) — corrected 2026-08-07, but a lint should **compute** these rather than trust them. Also an empty brace-expansion artifact directory `{entities,concepts,strategies,sources,analyses}` in the vault, untracked and harmless. |
| B-14 | ~~`ephem` not installed~~ | **CLOSED** — verified `ephem 4.2.1` present 2026-08-07. The reversal calendar can now be rebuilt; that rebuild has not been run, and coverage still ends **2027-12-28**. |

---

## Not started — each has a scoped first PR

| Track | First step | Roadmap |
|---|---|---|
| Falling Wedge | FW-1 scanner, then chart overlay | [[analyses/Falling-Wedge-Scanner-Fit]] |
| Market Sentiment Futures | MSF-1 global cues strip (login-free) | [[analyses/Market-Sentiment-Futures-Roadmap]] |
| Peer Comparison | PC-1 peer resolution + table | [[analyses/Peer-Comparison-Roadmap]] |
| Radar Chart | RC-1 single-stock radar, yfinance-only | [[analyses/Radar-Chart-Analyzer-Fit]] |
| Setup Intelligence | SV-1 radar + heatmap off existing subscores | [[analyses/Setup-Intelligence-Visual-Spec]] |
| Decision Support | DS-3 market × ownership matrix (both axes exist) | [[analyses/Decision-Support-Gating-Roadmap]] |
| Opportunity Hub | Phase 2 industry RRG · Phase 4 presets + backtest | [[analyses/Opportunity-Hub-Roadmap]] |
| PEAD | Phase 4 backtest · ADX filter | [[analyses/PEAD-Scanner-Roadmap]] |
| Backtest Harness | Dashboard surface (Ops tab) | [[analyses/Backtest-Harness]] |
| Fundamental Deep Dive | FR-6② LLM narration — **genuinely blocked, no API key** | [[analyses/Fundamental-Deep-Dive-Report-Roadmap]] |

---

## Thesis

The 2026-08-02 page's thesis was *"six bugs, zero exceptions — every one a
confident number with nothing behind it."* Five days on, that still holds and has
acquired a second half.

**Every bug found on 2026-08-07 was a number that could not be wrong out loud.**
A confluence count that treated five correlated scanners as five votes. A STRONG
index grade whose threshold sat above the p90 of the only population that could
earn it. A share card that clipped the sentence saying the market was RISK-OFF.
An "all-time high" computed from 400 bars. None threw an exception; all four
would have read as results.

The defence has not changed and is still cheap: **carry coverage with the data,
refuse to score below a floor, and calibrate on the population the grade can
actually apply to.**

The new half is this. **Measurement debt now exceeds feature debt.** The tools
built on 2026-08-07 are each individually honest about being unmeasured — and
that is exactly the problem, because the honest labels are accumulating faster
than the measurements. B-19, B-25 and B-20a/b are one coherent piece of work, and
until it is done every new refinement makes the stack taller rather than better.

## Action Taken / Plan

**Suggested order:**

1. **B-2** — one restart, unblocks shipped work.
2. **B-18** — a remote. Six commits a day on one unbacked machine.
3. **B-20a + B-20b** — significance test and market-model edge. Turns the
   harness into something whose answers can be trusted.
4. **B-25** — measure confluence, the premise the Hub ranks on.
5. **B-7** — settles five open numbers at once.
6. Then the capability gaps: **B-5**, **B-19b**, **B-3**.

## Outcome (fill in later)

## Related Pages

- [[analyses/Open-Backlog-2026-08-02]] — the snapshot this supersedes
- [[analyses/Backtest-Harness]] — where most of P1 lands
- [[analyses/OI-Momentum-Gap-Audit]] — source of B-19b and B-23
- [[analyses/Dashboard-UI-Roadmap]] — the M1–M4 spine
