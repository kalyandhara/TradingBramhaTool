---
title: "Turnover-Share Rotation (Δ share of market turnover)"
category: concept
tags: [sectors, rotation, turnover, liquidity, breadth, unvalidated]
timeframe: daily
created: 2026-09-09
updated: 2026-09-09
sources: 1
related:
  - sources/ScreeningMantis-Price-Volume-Sector-Rotation-2026-09-09.md
  - analyses/Sector-Rotation-Tool-Architecture.md
  - concepts/Chaikin-Money-Flow.md
  - analyses/Open-Backlog.md
  - concepts/Volume-Analysis.md
---

# Turnover-Share Rotation

Rotation stated in **money traded**, not price. A sector's turnover is expressed
as its **share of the whole market's turnover**, and the signal is the **change in
that share, in percentage points**, over a day and over a week.

Ingested 2026-09-09 from
[[sources/ScreeningMantis-Price-Volume-Sector-Rotation-2026-09-09]].

## The arithmetic

```
share_s(t)      = turnover_s(t) / SUM_over_sectors turnover(t)          # a fraction of 1
delta_share_D   = 100 * (share_s(t) - share_s(t-1))                     # percentage POINTS
delta_share_W   = 100 * (share_s(t) - share_s(t-5))
```

Two properties follow from the definition and both matter:

- **It is zero-sum by construction.** The shares sum to 1, so the Δ column sums to
  zero. Every sector that gains attention takes it from named others. A
  price-return column has no such constraint — on a broad rally every sector is
  green and the ranking says little.
- **It is scale-free.** A sector holding 6.83% of turnover on a heavy day and on a
  quiet one is doing the same thing; raw Rs-crore turnover would call the heavy
  day inflow.

Both are the reason to prefer share over turnover, and the reason the units are
**points, not percent** — a move from 3.70% to 6.65% is +2.95 pt, not +80%.

## Why it is not a price signal

The observed day makes the point better than any argument. On 2026-09-09
Information Technology took **+2.70 pt of turnover share** while **NIFTY IT fell
-3.24%**, its worst sectoral print of the session. Money arrived; price left.

Two readings are available and this concept **cannot distinguish them**:

- accumulation into weakness (buyers absorbing), or
- distribution (holders exiting into whoever will take it).

Turnover is unsigned. That is the whole limitation, and it is why this pairs
naturally with a **signed** flow measure — [[concepts/Chaikin-Money-Flow]] places
each bar's close inside its own range, so CMF supplies the direction that Δ share
cannot. Δ share says *where the attention went*; CMF says *which side of the
range it closed on*. Neither is a signal alone.

## How it differs from what this vault already has

`sector_rotation.py` ([[analyses/Sector-Rotation-Tool-Architecture]]) computes a
market-cap-weighted **FII holding change** per sector. Same word, different
measurement:

| | FII rotation score | Turnover-share rotation |
|---|---|---|
| Measures | ownership change by one participant class | total traded attention, all participants |
| Cadence | quarterly filings, manual screener.in export | daily, from data we already pull |
| Signed | yes (buy vs sell) | **no** |
| Blocked on | authenticated screener.in export | nothing |

They are complements. The FII score is slow and directional; Δ share is daily and
directionless.

## Built 2026-09-09

`tools/turnover_share.py` (+12 tests), on the Sector Map page directly beneath
the money-flow grid. Buckets come from `tools/sectors.py`, the canonical NSE
macro vocabulary adopted in [[analyses/Open-Backlog#B-64]].

Turnover there is a **proxy** — `close x volume` from daily bars, not exchange
traded value; it differs by the close-to-VWAP gap.

**First live run corroborates the measure across taxonomies.** nifty500, 20
sectors: **IT +2.73 pt**, against ScreeningMantis's **+2.70 pt** for the same
sector on the same date, computed over a different universe, a different sector
vocabulary and probably true turnover. Robust to the taxonomy — and still no
evidence of edge, since both are descriptions of one session.

## Status: UNVALIDATED, and note what "validating" would mean

Nothing here is measured. The source publishes no backtest, and neither have we.

The honest prior is **low**: turnover concentration is well known to spike on
news, index rebalances, block deals and expiry, none of which is rotation in the
sense a trader means. Before this becomes anything but a **view**, the test is a
plain event study, pre-registered in the shape [[analyses/Backtest-Harness]]
already supports:

> Rank sectors by Δ share (D and W). Score forward 5/20-day sector-index returns
> of the top and bottom quintile against a random-sector null. **Expected result:
> no lift** — the interesting outcome is if the *W* column has any and the *D*
> column has none, which would say the measure needs a week to shed one-day
> event noise.

Until that is run this stays a **context column**, never a confluence vote —
the same rule [[analyses/Open-Backlog#B-60]] ships under.

## Related Pages

- [[sources/ScreeningMantis-Price-Volume-Sector-Rotation-2026-09-09]] — where this came from
- [[concepts/Chaikin-Money-Flow]] — the signed partner measure
- [[analyses/Sector-Rotation-Tool-Architecture]] — the vault's other, slower "rotation"
- [[analyses/Open-Backlog#B-62]] — the proposed build
