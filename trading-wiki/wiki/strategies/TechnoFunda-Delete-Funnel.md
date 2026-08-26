---
title: "TechnoFunda Delete-Funnel (8-filter noise sieve)"
category: strategy
tags: [technofunda, funnel, veto-stack, noise-reduction, fundamentals, cash-flow, governance, pledge, 200dma, relative-strength, accumulation, indian-markets]
timeframe: swing / position
bias: neutral
created: 2026-08-25
updated: 2026-08-25
sources: 1
related:
  - strategies/TechnoFunda-Swing.md
  - strategies/Crash-Proof-3-Filter-System.md
  - strategies/Minervini-SEPA.md
  - analyses/Noise-Regime-Coverage-Postmortem.md
  - analyses/Open-Backlog.md
  - concepts/VCP.md
  - concepts/Stage-Analysis.md
---

# TechnoFunda Delete-Funnel

## Core Idea

A **watchlist noise sieve**, not a scorer. Eight filters applied in order, each of
which can only **delete** a name — what survives all eight is the shortlist. The
framing is deliberately subtractive ("delete businesses that aren't growing")
because the job is *reducing* a large universe to a very short list, which is
exactly the owner's stated problem in [[analyses/Noise-Regime-Coverage-Postmortem]]
(too many names / pages under a hostile tape → worse decisions).

Two questions, both required:

> Fundamental investors ask "is this a good company?"; traders ask "is this
> moving?"; technofunda asks both. A good business bought at the wrong point
> tests your patience for years; a good chart on a rotting balance sheet ends the
> same way every time.

**Where this sits among the three siblings already on file:**

| Strategy | Shape | What it is |
|---|---|---|
| [[strategies/TechnoFunda-Swing]] | **Scorer** — 7 conditions must all be true | Entry-timing system (VWAP/EMA/RSI/ADX/VCP/ATR) with a light fundamental pre-filter |
| [[strategies/Crash-Proof-3-Filter-System]] | **Gate stack** — 3 vetoes (market → stage → ownership) | Capital-preservation gate; market-health can cancel the whole day |
| **This page** | **Delete funnel** — 8 sequential vetoes, fundamentals *then* chart | The *widest* fundamental leg (adds cash-flow, leverage, capital-efficiency, governance) feeding a 3-filter chart confirm |

It is Crash-Proof's veto philosophy with a much deeper fundamental sieve, and it
shares TechnoFunda-Swing's "price must confirm" discipline (filters 6–8). The
governance leg (filter 5) is a **hard NO, not a discount** — the same stance
`red_flags.py` (FR-4) already takes on pledging and auditor exits.

> **Count caveat (honesty):** the source thread closes by calling it "ten
> filters" but numbers only **eight** (Filter 1–8); the closing list adds "sane
> valuation" and "defined risk" as survivors, which are a 9th screen and an
> execution rule, not filters in the sieve. This page keeps the eight it
> actually specifies and treats valuation/risk as the coda they are.

## Setup Criteria — the eight deletes

Evaluated top to bottom. A name that fails any filter is **removed**, not
penalised. Fundamentals first (1–5), then price takes over (6–8).

### Filter 1 — Delete businesses that aren't actually growing
One good quarter is noise. Read **6–8 quarters** of sales and PAT: is the trend up
and to the right, is growth **accelerating or fading**, is a base effect doing the
work? No growth engine → next.

### Filter 2 — Delete profits that never become cash
PAT is an opinion; cash flow is a fact. Check **CFO vs PAT over 3–5 years**. If
profit rises but operating cash flow doesn't follow, the money is stuck in
receivables and inventory — an accounting story, not a business.

### Filter 3 — Delete stretched balance sheets
D/E above comfort, **interest coverage under 3×**, debt rising faster than
revenue. Leverage is fine when the cycle is kind and fatal when it isn't. You are
not paid to carry someone else's borrowing risk.

### Filter 4 — Delete poor capital efficiency
**ROCE and ROE consistently above ~15%** is a business; consistently below the
cost of capital is a hobby. Growth without returns burns shareholder money slowly.

### Filter 5 — Delete governance red flags *(hard NO, not a discount)*
Promoter **pledging**, **falling promoter holding**, **auditor resignations**,
frequent **related-party transactions**, constant **equity dilution**. You survive
a bad quarter; you do not survive bad intent.

### Filter 6 — Delete anything below the 200 DMA
You may be early; you may also be wrong. Great fundamentals + falling price usually
means someone knows something the spreadsheet doesn't. Let price confirm.

### Filter 7 — Delete relative laggards
If the stock is flat while Nifty **and its sector** make highs, institutions
aren't buying it. The target isn't the cheapest good company — it's the good
company money is **already** choosing (relative strength vs both index and sector).

### Filter 8 — Delete charts with no accumulation footprint
Want to see: **tight consolidation / base formation** (not wild swings, not a
late-stage cup) with **volume expanding on up-moves**. Institutions can't hide —
they leave volume behind.

## What survives

Growing business · real cash flows · clean balance sheet · high returns on capital
· honest management · outperforming its index and sector · volume behind it —
then, as the coda, sane valuation and a defined risk point. A very short list.

## Coverage map — what the tool already computes vs. the gaps

The funnel maps almost 1:1 onto data already in the repo. Recorded so a build
(B-38, see [[analyses/Open-Backlog]]) reuses rather than rebuilds.

| Filter | Have | Gap to close |
|---|---|---|
| 1 · Growth 6–8Q | `fundamentals_deep.py` + dashboard YoY quarters | The **acceleration/fading trend read** across 6–8Q (not just latest YoY) |
| 2 · CFO vs PAT | `fundamentals_deep.py` OCF/FCF + the "Cash-Flow Safe" pre-breakout screener | A stored **CFO/PAT ratio over 3–5y**, not a single-period check |
| 3 · Leverage | debt in `fundamentals_deep.py`; **interest coverage + D/E now shipped** (`interest_coverage`, `debt_to_equity` keys, 2026-08-25) | debt-vs-revenue growth rate check |
| 4 · Capital efficiency | `fundamentals_deep.roce` (EBIT/capital employed); `multibagger_candidates` uses ROCE>15+OPM>10 | **ROE** consistency alongside ROCE; the "consistently ≥15%" multi-year test |
| 5 · Governance | `red_flags.py` (FR-4): promoter-stake-reduction, pledge veto, **auditor-resignation** NSE scan; pledge% from free NSE + screener.in | **Related-party** and **equity-dilution** flags |
| 6 · 200 DMA | `SMA200` computed in dashboard + `rating.py` trend template | — (present) |
| 7 · Relative strength | `rating.py` `rs_pct` (vs Nifty); `rrg.py` sector RS | Combine into a single **vs-index AND vs-sector** laggard veto |
| 8 · Accumulation | volume-expansion in `scanner_templates`; `detect_vcp_geometry`; SVP | An explicit **base/consolidation-tightness** detector as a first-class filter |

## Entry / Exit

This is a **shortlisting** funnel, not a trigger — it decides *what* is worth
watching, not *when* to buy. Hand the survivors to an entry system:
- **Entry timing:** [[strategies/TechnoFunda-Swing]] (the 7-condition align) or the
  [[strategies/Minervini-SEPA]] VCP-pivot on the filter-8 base.
- **Stop:** below the filter-8 base / breakout pivot (structure break), same as
  Crash-Proof and Minervini.
- **The coda screens** (sane valuation, defined risk) belong at this handoff, not
  inside the sieve.

## Best / Worst Conditions

- **Best:** a broad, noisy universe in a mixed-or-hostile tape — the more names to
  cut, the more a subtractive funnel earns its keep. Pairs with the regime
  throttle (B-32) and conviction-sized list (B-33).
- **Worst:** treating survivors as a buy list. Passing all eight filters says a
  name is *investable and confirmed*, not that today is the entry. The funnel has
  **no measured edge yet** — see below.

## Backtest / Track Record

**Unvalidated.** Like every signal in this repo, the funnel is a hypothesis until
the harness says otherwise. The measurable claim to test (B-38): does the
survivor set out-perform, forward, both (a) the un-filtered leading-sector
universe and (b) each single filter applied alone — i.e. does stacking the eight
deletes beat any one of them? Same discipline the confluence work (B-25) applies:
agreement is not evidence until measured.

**Engine shipped 2026-08-25:** `technofunda_funnel.py` — a Streamlit-free,
data-injected engine (`build_context` → `run_funnel`) that applies the eight
filters as short-circuiting deletes and returns survivors + a per-stage drop-off
report. Missing-data policy is `strict` (unverifiable filter deletes the name),
with governance-NOT_CHECKED and uncomputable-D/E held as caveats so the universe
can't be emptied by absence. F2 (CFO/PAT) and F8 (base tightness) are first-cut
heuristics pending their gap fills.

**Backtest shipped 2026-08-25 — with an honest scope limit:** `funnel_backtest.py`
answers the claim for the part that *can* be answered. Point-in-time replay is
only valid for signals computable from data available at the bar, so it covers the
**price sub-funnel (F6 ∧ F7 ∧ F8)** and each leg alone: enter next open, exit
next-open + h close, edge = mean(signal fwd) − mean(baseline fwd) with a **Welch
two-sample t-test**, and a "does stacking beat the best single leg?" verdict at
the primary horizon. The filter predicates are imported from
`technofunda_funnel`, so the tested rule is the shipped rule (no drift). **The
fundamental legs F1–F5 are NOT point-in-time testable** — yfinance serves only
*current* statements, so replaying them historically is look-ahead
(survivorship/restatement/as-of bias). The full-funnel forward test is therefore
blocked on **point-in-time fundamental data acquisition**, not code — the one
genuinely open item on the measurable claim.

## Sources

- Unattributed X / Twitter thread (10 tweets, technofunda "delete" funnel),
  supplied by the owner 2026-08-25. Methodology only; no performance data given,
  so its own claims earn zero weight here (repo measurement-first ethos).

## Related

- [[strategies/TechnoFunda-Swing]] — the scorer sibling (entry timing)
- [[strategies/Crash-Proof-3-Filter-System]] — the veto-gate sibling (capital preservation)
- [[strategies/Minervini-SEPA]] — Stage-2 + VCP pivot for the handoff
- [[analyses/Noise-Regime-Coverage-Postmortem]] — the noise problem this addresses
- [[analyses/Open-Backlog]] — B-38 build item
