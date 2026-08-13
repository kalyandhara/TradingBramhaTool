---
title: "Jupiter Market Crash Thesis — Shashtashtak + Ketu Nakshatra Framework"
category: concept
tags: [astro, jupiter, ketu, shashtashtak, crash, market-timing, vedic, risk]
created: 2026-08-12
updated: 2026-08-12
sources: 1
related:
  - concepts/Nakshatra-Sector-Map.md
  - concepts/Panchang.md
  - concepts/Mercury-Retrograde-Market-Cycle.md
---

# Jupiter Market Crash Thesis

> [!key-insight] Core Thesis
> **Jupiter (Guru) is the primary planetary driver of major market rallies and crashes.**
> A high-probability crash signal fires when ALL three conditions align:
> 1. Jupiter transiting a **Ketu-ruled nakshatra** (Ashwini, Magha, or Mula)
> 2. Jupiter in **Shashtashtak Yoga** (6/8 axis relationship) with one or more malefics: Saturn, Sun, or Mars
> 3. Jupiter influenced by the **Rahu-Ketu axis** (nodal affliction)
>
> When fewer than all three conditions are met, the market may still show volatility but crashes are avoided (see Exceptions below).

---

## Key Definitions

| Term | Meaning |
|------|---------|
| **Shashtashtak Yoga** | 6th/8th house axis relationship between two planets — considered highly malefic, associated with sudden disruption, hidden crises |
| **Ketu's Nakshatras** | Ashwini (0°–13°20' Aries), Magha (0°–13°20' Leo), Mula (0°–13°20' Sagittarius) |
| **Rahu-Ketu Axis** | The lunar nodes; their influence on Jupiter amplifies sudden, unexpected shocks |
| **Jupiter transit speed** | ~1 year per sign; stays in each nakshatra ~40–45 days |

---

## Historical Evidence Table

| Period | Market Event | Jupiter's Nakshatra | Key Combinations | Outcome |
|--------|-------------|---------------------|-----------------|---------|
| **1992** | Harshad Mehta Crash | Magha (Ketu's star) | Shashtashtak with Saturn & Sun; aspected by Rahu & Mars | **CRASH** — Sensex −57% (4546→1980). Recovery: 20 months |
| **2000** | Dot-com Bust | Ashwini (Ketu's star) | Conjunction with Saturn; Rahu-Ketu axis | **CRASH** — Nifty −53% (1812→849). Recovery: 34 months |
| **2008** | Global Financial Crisis | Mula (Ketu's star) | With Sun; aspected by Mars & Ketu; 8th from Saturn | **CRASH** — Nifty −64% (6357→2520). Recovery: 71 months |
| **2020** | Covid Crash | Mula (Ketu's star) | With Saturn, Sun, Mercury; eclipse influence; Ketu affliction | **CRASH** — Nifty −39% in 2.5 months. Fast recovery once Jupiter cleared Saturn/Ketu |
| **1995** | Positive trend | Mula (Ketu's star) | Jupiter + Mars only; **no Shashtashtak, no malefic in 6/8** | **+7%** — Exception; partial condition only |
| **2003** | Bull Run | Magha (Ketu's star) | Jupiter + Mercury + Moon (Gajakesari/Laxmi Yoga); no malefic in 6/8 | **+20%** — Exception; benefic override |
| **2011** | Flat/Negative | Mula (Ketu's star) | Aspected by Rahu; 8th from Saturn | **−12%** — Partial crash signal; no full confluence |
| **2015** | Minor correction | Magha (Ketu's star) | Aspected by Saturn; 8th from Ketu | **−7%** — Partial signal |
| **2023** | Bull Run | Mula (Ketu's star) | **No Shashtashtak with malefics** | **+12%** — Exception; Ketu nakshatra alone is insufficient |
| **Oct 2024** | Short-term volatility | Visakha (Jupiter's own) | Shashtashtak with Sun, Saturn, Mars; but **not** in Ketu's nakshatra | Correction Oct 18–Dec 4; not a major crash |

---

## The Signal: Three-Factor Model

```
CRASH PROBABILITY = (Ketu Nakshatra) × (Shashtashtak w/ malefic) × (Rahu-Ketu nodal influence)
```

- **All 3 factors** → Major crash (1992, 2000, 2008, 2020)
- **2 factors** → Significant correction (2011 −12%, 2015 −7%)
- **1 factor (Ketu nakshatra alone)** → Positive or neutral possible (1995 +7%, 2003 +20%, 2023 +12%)
- **Shashtashtak alone (no Ketu nakshatra)** → Short-term volatility, not systemic (Oct 2024)

### Exception Pattern (Benefic Override)
When Jupiter forms **Gajakesari Yoga** (Jupiter + Moon) or **Laxmi Yoga** (Jupiter + Mercury/Moon in angle), it can neutralise even Ketu nakshatra influence, producing a bull run (2003).

---

## Forward Predictions

| Period | Jupiter Position | Condition | Signal |
|--------|-----------------|-----------|--------|
| **Jun 2026** | Cancer (Kark) | Shashtashtak with Rahu | Turbulence begins; not full crash signal |
| **⚠️ Nov 2026** | **Leo (Singh) / Magha** | **Rahu-Ketu axis + 8th from Saturn** | **FULL CRASH SIGNAL — mirrors 1992 & 2008 setup** |
| **2027–2032** | Various / Ketu influence | Recurring Shashtashtak with Saturn; Saturn in Aries (global disturbance) | Bearish/slow; difficult recovery |
| **Post-2033** | — | Shashtashtak persists but without affliction | Recovery begins |

---

## Dashboard Integration

- The **Astro Timing page** currently tracks Moon nakshatra daily via `get_nakshatra()`.
- **Jupiter position is NOT yet tracked** — adding it would enable live flagging of the three-factor crash signal.
- Proposed addition to `astro_trading.py`: `get_jupiter_position(date)` returning sign, nakshatra, and whether Shashtashtak with Saturn/Sun/Mars is active.
- When all three factors align, the Astro Timing page should display a red `> [!warning] Jupiter Crash Signal Active` banner.

---

## Methodology Limitations

> [!note] Interpret as context, not signal
> This framework is a **qualitative overlay**, not a mechanical trading signal. Specific limitations:
> - Sample size: 10 historical data points across 32 years
> - Post-hoc selection: the "exceptions" demonstrate the model requires all three factors, but that flexibility also makes it hard to falsify
> - **Ketu nakshatra alone is clearly insufficient** (3 out of 4 such cases were positive)
> - The Shashtashtak yoga definition requires an ephemeris source; calculation methodology is not specified in the source
> - Magnitude of crash varies widely (−39% to −64%) even with identical signal
> - **Recovery timeline** is the most practically useful prediction: 2020 was fast (fundamentals strong + stimulus); 2008 was slowest (71 months); 1992 took 20 months. The thesis suggests 2027–2032 recovery will be slow — most likely because no fiscal/monetary override is assumed.

---

## Sources

1. Jupiter Market Crash Thesis — user-provided historical analysis table (2026-08-12)
2. [[concepts/Nakshatra-Sector-Map]] — Ketu's nakshatras and their characteristics
