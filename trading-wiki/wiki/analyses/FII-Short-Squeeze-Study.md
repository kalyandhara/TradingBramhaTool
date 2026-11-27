---
title: "FII Short-Squeeze Study (B-95) — does an extreme FII index-futures short precede NIFTY gains?"
category: analysis
tags: [b-95, fii, participant-positioning, short-squeeze, state-series, rotation-test, pre-registered]
timeframe: swing
created: 2026-10-14
updated: 2026-10-14
sources: 0
related:
  - concepts/Participant-Positioning-FII-DII.md
  - sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18.md
  - analyses/Open-Backlog.md
---

# FII Short-Squeeze Study (B-95)

## Data probe — 2026-10-14
NSE's participant-wise F&O OI file (`fao_participant_oi_DDMMYYYY.csv`, nsearchives) is
fetchable for every date tried back to 2016. `tools/participant_oi.py` fetches, caches
(`cache/participant_oi/`) and parses it. On 2026-10-13 FIIs held 9.8% of their index-futures
OI long — "90% short", the claim's zone.

## Pre-registration — written 2026-10-14, BLIND
Written while the cache was still filling: **no return and not even the distribution of the
ratio had been looked at.** The threshold below comes from the claim, not from the data.

**Claim under test** ([[sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18]]): an extreme
FII index-futures short (~88%) is squeeze fuel — NIFTY tends to rise from it.

**State.** `L` = FII index-futures long ÷ (long + short), per session.
**Extreme short** = `L ≤ 0.15` (≥ 85% short — the letters' zone, rounded generously).

**Market series.** NIFTYBEES daily close (`cache/cardinality_deep/`, the NIFTY 50 proxy the
desk used in B-147), joined to the OI sessions by date. Forward return = close in N sessions
÷ close today − 1. No costs (an index read, not a trade).

**Why rotation, and why a control** ([[concepts/Participant-Positioning-FII-DII]]): `L` is a
slow, autocorrelated STATE, so day-by-day t-tests manufacture significance (desk precedent:
a known null at p=0.031 Welch vs 0.32 rotation). And extremes cluster in falling markets by
construction, so a raw comparison mixes the state with what the market already did.

**Tests** (statistic = mean forward return on extreme-short days minus all other days;
p-value = exact circular rotation of the state labels, `gamma_regime_backtest._rotation_p`,
two-sided):
- **T1 — raw**: forward 20-session return.
- **T2 — controlled (DECISIVE)**: the forward 20-session return minus the mean forward
  return of all sessions in the same tercile of the PRIOR 20-session NIFTY return (terciles
  fixed on the full sample). This asks: given how far the market has already fallen, does
  the FII short add anything?
- Reported, not decisive: T1 and T2 at 10 sessions; T2 restricted to the FIRST day of each
  extreme episode (entry after ≥ 10 sessions outside the state), with its own rotation p.

**Verdict on T2 @20 sessions, α = 0.05:**
- **POSITIVE** (supports the squeeze claim): difference > 0, rotation p < 0.05.
- **NEGATIVE**: difference < 0, rotation p < 0.05.
- **NULL**: otherwise.
- **INCONCLUSIVE**: fewer than 30 extreme-short sessions or fewer than 3 separate episodes.

**Not claimed either way:** that FIIs are "trapped" (nothing forces a hedged short to cover —
the mechanism GEX has and this ratio lacks), or any reading for the client side, which is
reported descriptively only.

## Results

*(appended after the run — nothing above this line is edited once the run starts)*

**Run 2026-10-15** — `tools/participant_oi_study.py`, result `tools/cache/participant_oi_study.json`.
2,445 sessions joined to NIFTYBEES (2016-10-14 → 2026-09-10). FII index-futures long share:
min 6%, median 49%, max 89%. **261 extreme-short sessions in 12 episodes.**

### Verdict (pre-registered T2 @20 sessions): **NULL**

| Test | Extreme short | All other | Difference | Rotation p |
|---|---|---|---|---|
| T1 raw, 10d | +0.09% | +1.29% | −1.20 pts | 0.28 |
| T1 raw, 20d | +0.69% | +1.83% | −1.14 pts | 0.47 |
| T2 controlled, 10d | −1.29% | +0.15% | −1.44 pts | 0.22 |
| **T2 controlled, 20d (decisive)** | −1.28% | +0.14% | **−1.42 pts** | **0.38** |
| T2 entry days only, 20d (12 episodes) | −3.53% | +0.02% | −3.55 pts | 0.052 |

**Plain reading.** Nothing supports "88% short is squeeze fuel" on NIFTY. Every reading points
the *other* way — NIFTY did worse after extreme FII shorts, even after allowing for how far it
had already fallen — but none of it clears the bar, and the entry-day test (the claim's
sharpest form) has only 12 events. NULL, leaning against the claim; not evidence of the
opposite.

### Descriptive
- **The state is recent.** All 12 episodes start in 2020 or later, 11 of them from mid-2022:
  FIIs have carried much heavier index-futures shorts in recent years (hedging alongside cash
  holdings is the usual reading). A "normal" range from older years would mislead.
- **Client is the mirror:** client long share correlates −0.88 with the FII's. Reported only.
- Episode starts: 2020-02-27, 2022-06-13, 2022-09-29, 2023-03-02, 2023-10-26, 2024-05-30,
  2024-12-30, 2025-01-30, 2025-07-22, 2025-11-06, 2026-03-04, 2026-04-28.

### Data notes
- `tools/participant_oi.py` caches one file per session (`cache/participant_oi/`): 2,470
  sessions, 139 dates missing (holidays). Some 2017 files use bare-CR line endings; the
  parser normalises them (a test pins it) — that crash had silently stopped the first backfill.
- No forcing mechanism was tested or claimed (a hedged FII short is not obliged to cover).
