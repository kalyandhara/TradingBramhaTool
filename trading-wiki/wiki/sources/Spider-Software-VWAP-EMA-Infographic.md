---
title: "Infographic — Spider Software: Trading with VWAP & EMA"
category: source
tags: [vwap, ema, infographic, spider-software, intraday, short-setup, b-89, b-90, b-91]
timeframe: intraday
created: 2026-09-17
updated: 2026-09-17
sources: 1
related:
  - analyses/Open-Backlog.md
  - concepts/VWAP.md
  - concepts/Volume-Analysis.md
---

# Infographic — Spider Software: Trading with VWAP & EMA

## Metadata

- **Publisher:** Spider Software (charting vendor, "25 Years" badge)
- **Type:** Promotional infographic, supplied by the owner 2026-09-17
- **Bias:** Bearish in the worked example; the rule itself is symmetric
- **Provenance:** A vendor marketing card. **No data, no sample, no backtest** —
  which is the standing weight this wiki gives such sources: zero, until measured.

## Key Takeaways

1. **Entry (SHORT):** price **closes below both VWAP and the EMA**.
2. **Exit (SHORT):** price **closes above both VWAP and the EMA**.
3. **Caveat stated on the card:** *"For indices VWAP is applicable only on futures
   charts, but not on spot charts."*
4. No EMA period is given, no VWAP anchor is specified, no stop, no target, no
   holding period, and no hit rate is claimed. It is a **state-agreement rule**
   between two lagging averages.

## Detailed Notes

The card's construction is **trend-following state agreement**: it does not trade
a cross of the two lines against each other, but price being on the same side of
both. The chart shows a short held for the width of a downtrend and closed on the
first close back above both lines.

It is a **short-side** rule, which matters for this desk: shorting NSE cash for a
swing hold is not available to most of this repo's users (recorded in
`evwma_vwap_macd_backtest.py`). Its usable form here is **exit / avoid**, not
entry.

## Validation Against What Ships — 2026-09-17

Full validation in [[analyses/Open-Backlog#VWAP + EMA — validated against a Spider Software infographic, 2026-09-17]].

| The card says | The desk has | Verdict |
|---|---|---|
| VWAP on the chart | `vwap` — session VWAP, intraday-only | **present, stricter** |
| EMA on the chart | `ema9 / ema20 / ema50 / ema200` | present |
| "indices: futures only, not spot" | a **volume guard**, not a symbol list | **present, better founded** |
| EMA cross BUY/SELL | `mabias` — 9/20 arrows, 50/200 GC/DC, verdict card | **present, richer — but unmeasured** |
| price on the same side of BOTH | — | **absent** |

## Contradictions with Existing Wiki

**None on the mechanics — but the card's central claim runs against three measured
results already on this desk**, and that is worth stating plainly rather than
filing the card as neutral context:

| Measured here | Verdict |
|---|---|
| `evmacd` — EVWMA/**VWAP** MACD cross | **NEGATIVE**: no edge; stop-and-reverse −29% vs buy&hold +827% |
| ADX/DI bare cross | **the bare DI cross LOSES** (−0.93% @10d, p=0.02) |
| all 41 scanners, walk-forward (B-19) | **0 of 41 stable** after costs |

The card's rule is the same *shape* of construct — two lagging averages read as a
state. The prior is therefore **skeptical**, and that is recorded before any
measurement so a marginal result cannot later be read as a success.

**Where the card is right and useful:** its index caveat is real. Verified —
`^NSEI` carries **zero volume on all 2,125 stored 15-minute bars**, so VWAP is
genuinely uncomputable on NSE index spot. The desk already handles this, by
checking the data rather than naming the instrument.

## Actionable Insights

Three backlog items, all raised from this card:

- **[[analyses/Open-Backlog#B-89]] (P1)** — `mabias` ships a LONG/SHORT verdict
  badge on the chart and **nothing has ever scored it**. The card's question
  ("is EMA cross BUY/SELL adopted?") exposed it.
- **[[analyses/Open-Backlog#B-90]] (P2)** — the card's own rule, to be
  **measured before it is built**, framed as exit/avoid for a cash book.
- **[[analyses/Open-Backlog#B-91]] (P3)** — VWAP draws nothing on index spot and
  does not say why. The card is evidence readers expect the line to be there.

## Pages Updated

- [[analyses/Open-Backlog]] — validation section + B-89 / B-90 / B-91
