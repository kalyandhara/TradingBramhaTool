---
title: "Volume Analysis — Confirmation, Divergence and the Tick-Volume Caveat"
category: concept
tags: [volume, tick-volume, obv, mfi, vsa, wyckoff, breakout-confirmation, divergence, climax-volume]
created: 2026-08-02
updated: 2026-08-02
sources: 1
related: [concepts/Volume-Profile, concepts/VWAP, concepts/Anchored-VWAP-Pyramiding, concepts/FPV-Flow-Price-Volume-Ownership, concepts/VCP, concepts/Order-Flow]
---

# Volume Analysis — Confirmation, Divergence and the Tick-Volume Caveat

## Definition
The study of how much traded — contracts, lots or shares — inside a bar, used to judge whether a price move is *supported*. Price says where the market went; volume says how many participants had to agree to move it there. Neither is sufficient alone, which is the premise the whole discipline rests on.

This page is the umbrella. The structural applications live elsewhere: [[concepts/Volume-Profile]] (volume distributed by *price* rather than time), [[concepts/VWAP]] and [[concepts/Anchored-VWAP-Pyramiding]] (volume-weighted average cost), [[concepts/Order-Flow]] (volume signed by aggressor).

> [!caution] Not all "volume" is volume
> **Equities and futures** trade on a central exchange, so reported volume is real: an actual count of shares or contracts.
> **Forex is OTC with no central exchange**, so *"true volume data doesn't exist the way it does in stocks or futures"*. Platforms display **tick volume** — the number of price *changes* per bar — which correlates with real volume at **~90%+ on liquid majors** (EUR/USD, GBP/USD) and **measurably worse on exotics and illiquid pairs**.
> **Crypto venues** are somewhere between: real, but venue-local and not consolidated across exchanges.
> A volume-derived indicator inherits whatever its feed actually counts. Say which you have before trusting the reading.

## How to Use

### The price + volume matrix
| Price | Volume | Reading |
|---|---|---|
| Rising | Rising | Strong, believable trend |
| Rising | Falling | Weak trend — possible reversal ahead |
| Breaks resistance | **≥1.5× average** | High-probability breakout |
| Breaks resistance | Below average | Likely false breakout |
| At a key level | High | Confirmed support/resistance |
| At resistance | **500%+ of average** | **Climactic — reversal risk, not continuation** |

The last row is the one that catches people: past a certain magnitude, volume stops meaning conviction and starts meaning capitulation or a completed transfer. More is not monotonically better.

### Divergence
- **Bearish** — price makes a new high, OBV/MFI makes a lower high: fewer participants behind each new high.
- **Bullish** — price makes a new low, OBV/MFI holds higher: selling pressure drying up.

**A divergence is not an entry.** It flags a weakening trend and needs a price pattern to become a trade — the same relationship [[concepts/MACD-Divergence]] documents for momentum divergence.

### Wyckoff Volume Spread Analysis (VSA)
Reads three things per bar together — **spread** (range), **close position within that range**, and **volume**:
- Wide spread up, close near the high, above-average volume → genuine buying strength.
- Narrow spread up, close mid-bar, above-average volume → potential **distribution**.

Identical volume, opposite implication. What separates them is where the bar closed — i.e. whether that volume was absorbed.

### Volume dry-up: the same measurement, two opposite meanings
| Where | Falling volume means |
|---|---|
| On an **impulse leg** | Demand is failing — trend weakening |
| Inside a **base / consolidation** | Supply is exhausted — **constructive**, and the defining feature of [[concepts/VCP]] |

This looks like a contradiction and is not. Context — trending vs consolidating — decides which reading applies, and any rule that measures volume contraction has to state which one it is testing. Our own VCP scanner treats `base_vol_ratio ≤ 0.7` as a *positive*; the same contraction on a breakout leg would be a warning.

## Variants / Parameters
- **"Above average" threshold:** `1.5×` the **20-period** average is the stated standard; `2×` for higher conviction. Climax at `500%+`.
- **Relative, never absolute.** A million shares is meaningless without the baseline it is being compared to; always express volume as a multiple of a stated lookback.
- **Indicators:** **OBV** (cumulative — add volume on up-bars, subtract on down-bars; directional flow) · **MFI** (volume-weighted RSI, 0–100, >80 overbought / <20 oversold) · **Volume Profile** (by price) · **VWAP / AVWAP / rolling VWAP** (volume-weighted cost).
- **Volume Profile 80% rule:** price entering the value area and holding **two consecutive 30-minute bars** implies ~80% probability of traversing the full VAL→VAH range. A testable claim with an entry, a target and a probability — see [[concepts/Volume-Profile]].

## Common Mistakes
- **Trading breakouts on low volume** — the single most cited failure; a breakout nobody participated in is a level being tested, not broken.
- **Applying equity/futures volume logic to FX** without acknowledging tick volume.
- **Treating divergence as a signal** rather than as context requiring a price trigger.
- **Confusing absolute with relative volume** — always a multiple of a stated average.
- **Assuming more volume is always more bullish** — see the 500% climax row above.
- **Trusting volume on illiquid instruments at all** — the weighting is the point; on a thin name it is noise. ([[concepts/VWAP]] makes the same warning.)

## In this repo
- **Breakout confirmation already matches the standard**: `vol_ratio >= 1.5` against the 20-day average in `scan_*` (`scanner_templates.py` ~1191, ~1276) — same multiple, same lookback, arrived at independently.
- **But three thresholds coexist**: `1.5×`/20d (breakout scanners), `1.5×`/50d (VCP `~755`), `1.4×`/50-DMA (structural breakout `~1032`). Nothing records why they differ. Reconciling them — or documenting the reason — is an open item.
- **Volume dry-up** is used constructively at `base_vol_ratio <= 0.7` (`~294`), per the context rule above.
- **OBV** ships as a chart indicator (`chart_dashboard.html`) but has no wiki page of its own.
- **MFI is absent from the repo entirely** — and is cheap to add, being RSI weighted by volume with `_rsi_series` (Wilder) already present.
- **Volume Profile** is implemented twice: `volume_profile.js` (chart) and `compute_volume_profile_levels()` (screening).

## Related Concepts
- [[concepts/Volume-Profile]] — volume by price; POC/VAH/VAL/HVN/LVN and the 80% rule.
- [[concepts/VWAP]] · [[concepts/Anchored-VWAP-Pyramiding]] — volume-weighted average cost, session and anchored.
- [[concepts/FPV-Flow-Price-Volume-Ownership]] — volume is the **V** of that framework; this page is the mechanics behind it.
- [[concepts/VCP]] — where volume contraction is the constructive signal.
- [[concepts/Order-Flow]] — volume signed by aggressor; the finer-grained view.

## Sources
- [[sources/ForexTester-Volume-Analysis-Guide]] (2026-08-02) — tick-vs-real volume caveat, the price+volume matrix, the 1.5×/2×/500% thresholds, Wyckoff VSA, and the Volume Profile 80% rule.
