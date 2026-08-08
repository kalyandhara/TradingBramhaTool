---
title: "Fingrad — Open Interest (OI) Analysis / Trend Confirmation Infographic"
category: source
tags: [infographic, open-interest, oi, futures, volume, trend-confirmation, hindi]
created: 2026-08-07
updated: 2026-08-07
sources: 1
related:
  - analyses/OI-Momentum-Gap-Audit.md
  - concepts/Put-Call-Ratio.md
  - concepts/Order-Flow.md
---

# Source — Fingrad OI Analysis Infographic

## Metadata
- **Type:** Single social-media infographic (image), Hindi/English mixed.
- **Title:** "Open Interest (OI) Analysis से Trend Confirmation कैसे करें?"
- **Watermark/house style:** FINGRAD. Third from this publisher, after
  [[sources/Fingrad-Trading-Infographics-Collection]] and
  [[sources/Fingrad-PCR-Infographic]].
- **Supplied:** 2026-08-07, pasted into chat.
- **Bias:** Educational reference. Generic technique material, no market call.

## Key Takeaways

- **Definition:** OI is the total number of futures & options contracts still
  open. It tells you whether **fresh positions are arriving or existing ones are
  leaving** — the question price alone cannot answer.
- **The four-quadrant grid** (the core, and the same one
  [nse_oi_momentum.py](tools/nse_oi_momentum.py) already implements):

  | Price | OI | Signal | Meaning |
  |---|---|---|---|
  | ↑ | ↑ | Long Build-up | new buyers entering, bullish trend may strengthen |
  | ↓ | ↑ | Short Build-up | new sellers positioning, bearish trend may strengthen |
  | ↑ | ↓ | Short Covering | sellers closing; a sharp rally is possible |
  | ↓ | ↓ | Long Unwinding | buyers closing; bullish momentum weakening |

- **Volume is the confirmation axis, and it is stated as a rule:**
  **High Volume + OI increase = Strong Signal**;
  **Low Volume + OI increase = Weak Confirmation.**
- **Market psychology** per quadrant: build-ups are expectation, covering and
  unwinding are exits (bulls profit-booking in the long-unwinding case).
- **Strategy panel:** bullish confirmation = price up + OI up + volume up +
  **resistance breakout**; bearish = price down + OI up + volume up + **support
  breakdown**. "Always watch together": Price Action · Open Interest · Volume ·
  **Option Chain** · Support & Resistance.
- **Worked examples** are index-level: NIFTY 25,200 with +180 points and OI +12%
  on high volume → strong long build-up; −150 points with OI +10% on high volume
  → strong short build-up.

## Contradictions with Existing Wiki

**None on the quadrant logic** — it matches `nse_oi_momentum.py` exactly,
including the sign convention on the two down-move cases. That is worth
recording as corroboration rather than news: our four quadrants were derived
from NSE's own "Change in Open Interest" page, and an independent teaching
source reproduces them identically.

Two places where the sheet is *looser* than our implementation, and we are
right:

- It never mentions **rollover**. Its examples read OI at face value, which near
  expiry turns ordinary contract-rolling into a fictitious covering signal —
  the exact trap our module was built to avoid by summing OI across the whole
  series. A teaching sheet omitting this is how the trap propagates.
- It never mentions **liquidity floors**. An OI percentage on a thinly traded
  contract swings on a handful of lots; our `MIN_TURNOVER` and materiality
  floors exist for that.

## Actionable Insights

Recorded in full in [[analyses/OI-Momentum-Gap-Audit]]. The headline is that the
sheet's volume rule points at a real hole: **we aggregate `TtlTradgVol` and then
never read it.**

## Pages Updated

- Created [[analyses/OI-Momentum-Gap-Audit]]
- `wiki/index.md`, `wiki/log.md`
