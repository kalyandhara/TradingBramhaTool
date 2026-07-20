---
title: "VCP — Volatility Contraction Pattern"
category: concept
tags: [breakout, contraction, swing, Mark-Minervini, algorithmic]
created: 2026-06-14
updated: 2026-07-06
sources: 4
related:
  - concepts/Darvas-Box.md
  - concepts/Stage-Analysis.md
  - strategies/TechnoFunda-Swing.md
  - concepts/ADX.md
  - analyses/VCPBot-Architecture.md
  - strategies/VCPBot-Trend-Template.md
  - strategies/Minervini-SEPA.md
  - sources/Minervini-Think-Trade-Champion.md
  - sources/TV-VCP-Scanner-Minervini-valchak.md
---

# VCP — Volatility Contraction Pattern

## Definition
A pre-breakout setup where price makes progressively tighter corrections on decreasing volume — a "squeeze" before expansion. Developed by Mark Minervini. The pattern requires a prior uptrend, a base, and tightening contractions each shallower than the last.

## Visual Structure
```
PRICE
  │  - - - - - - - - - - - - - - -   🎯 +20% TARGET
  │                              /
  │  ═════════════════════════ /   ← BUY STOP (pivot + $0.05)
  │  /\          /\      /\   /
  │ /  \        /  \    /  \ /    ← Breakout on HIGH VOLUME
  │/    \      /  C2 \ / C3 \/
  │      \    /  ~15% \/  <8%    RISK ≤ 7%
  │  C1   \  /           - - -  STOP (low of C3)
  │ ~25%   \/

VOLUME
  │ █                              █ █  ← surge at breakout
  │ █  █        ← drying up →    ██ █ █
```

## The 3-Tier Detection (Algorithmic — VCPBot)

### Pass 1 — Macro (n=15): Left Side High (LSH)
- Find most recent macro swing high preceded by **≥30% advance**
- LSH must be followed by **≥15% pullback** (anchor for base start)
- Base must be **≥20 trading days (4 weeks)** from LSH to today

### Pass 2 — Contraction (n=8): Tightening Swings Within Base
- Find swing high→low pairs within the base window
- **Rules for valid VCP:**
  1. Final contraction must be the **tightest** (absolute requirement)
  2. Regression slope of contraction depths must be **negative** (compressing)
  3. Final must be **≥15% shallower** than first (compression ratio ≤ 0.85)
- Adaptive n: base ≥60 days → n=8; base ≥35 days → n=5; shorter → n=3
- **VCP_1C path:** single contraction allowed if base < 35 days AND post-contraction range is ≥40% tighter

### Pass 3 — Micro (n=3): Exact Entry + Stop
- Window: from the final swing LOW forward (not from swing high — prevents inflated stop)
- **Pivot** = highest High in post-contraction window
- **Stop** = lowest Low in post-contraction window
- **Hard reject:** (pivot - stop) / pivot > 7%

## Entry Rules
- **Entry:** GTC buy stop at pivot + $0.05 (slippage buffer: limit at pivot + $0.25)
- **RVOL check at 10:30 AM:** cancel if intraday volume < 1.5× expected
- **Gap check at open:** cancel if price gaps >2% above pivot
- **Earnings blackout:** reject if earnings within N days

## Exit Rules
- **Stop loss:** low of final contraction (server-side bracket order on Alpaca)
- **Target:** +20% from pivot (server-side bracket order)
- Risk:Reward = 1:2.8+ minimum

## Volume Dry-Up Rules
- Final contraction avg volume vs 50-day avg volume:
  - Final contraction ≤8% deep → standard threshold (80%)
  - Final contraction >8% deep → strict threshold (70%)
- Reject if vol_ratio ≥ threshold (volume not drying up)

## Key Parameters
| Parameter | Value |
|-----------|-------|
| Min base duration | 4 weeks (20 trading days) |
| Min contractions | 2 (VCP_2C+) or 1 (VCP_1C short base) |
| Max contractions tracked | 4 most recent |
| Final contraction max (standard) | 8% |
| Final contraction max (high beta ATR>3.5%) | higher ceiling |
| Stop max from pivot | 7% |
| Target | +20% |

## Manual vs Algorithmic VCP (Key Difference)
Manual DarvaX: uses "lollipop low" on closing basis as stop.
Algorithmic VCPBot: uses micro-pivot stop from the post-contraction window specifically — avoids prior deep lows inflating the stop when price has already partially recovered.

## Relationship to Darvas Box
Both find contraction-before-expansion. Darvas uses a visual "box" concept; VCP tracks percentage depths across successive swings with strict tightening rules. The DarvaX "High Dry Fry" pattern overlaps heavily with VCP_1C (single contraction, short base).

## Minervini's Original VCP Framework (Manual)

From [Minervini-Think-Trade-Champion](../sources/Minervini-Think-Trade-Champion.md):

- **Contraction count (T)**: each successive pullback is referred to as a "T"; most patterns have 2–4T, sometimes up to 6T
- **Contraction depth rule**: each T is roughly half (±reasonable) the prior T; e.g., 28% → 16% → 8% → 3%
- **VCP footprint notation**: `WW depth/final T_count` — e.g., `27W 28/6 3T` = 27-week base, first contraction 28%, final 6%, 3 contractions total
- **Volume at pivot**: look for at least 1 day of extremely low volume (below 50-day avg, ideally near the lowest since the base began); this is a "selling vacuum"
- **Pivot buy point**: when price breaks above the high of the tightest contraction on expanding volume — this is the "line of least resistance" (Jesse Livermore's concept)
- **Overhead supply dynamics**: each contraction wrings out more weak holders (wet towel analogy); by the pivot, supply is exhausted; even small demand moves price sharply

### valchak's Pine Screener Preset (2026-07-06)

Second reference implementation — TradingView invite-only script ([[sources/TV-VCP-Scanner-Minervini-valchak]]). Commits numeric ranges the book leaves discretionary:

| Parameter | Practical Defaults | Textbook-Strict |
|-----------|-------------------|-----------------|
| Contraction count | 2–6 | 2–6 |
| First contraction depth | 10–35% | 10–35% |
| Final contraction depth | 3–10% | tighter |
| Tightening ratio (each vs prior) | ≤ 0.9× | ≤ 0.5× |
| Base duration | 15–325 bars (~3–65 weeks) | same |
| Pivot confirmation bars (L/R) | 3 | 5 |
| Breakout volume vs 50d avg | ≥ 1.4× | ≥ 1.4× |
| VDU threshold | 1.0× (off) | 0.7× |
| Max extension above pivot | 12% | 5% |

Six-gate signal engine (all must be true on same bar): Trend Template ∧ VCP Valid ∧ VDU ∧ BreakingOut ∧ VolumeSurge ∧ **NotExtended** (anti-chase, ≤ 12% above pivot).

Divergences from Minervini's book:
- **200-day slope**: valchak requires ≥ 22 trading days uptrend (book says "≥ 1 month, prefer 4–5")
- **Above 52-week low**: valchak defaults to ≥ 30% (book says ≥ 25%) — tightened
- **Pivot confirmation lag**: 3 bars L/R before pivot is drawn (safer, but structurally later than book's intraday breakout entry)

Compared to [[analyses/VCPBot-Architecture]] (our internal 3-tier): valchak has no explicit "left-side high + prior ≥30% advance" macro anchor — relies entirely on Trend Template to gate for Stage 2.

### Base Patterns Containing VCP Characteristics
| Pattern | Notes |
|---------|-------|
| Classic cup-with-handle | Most reliable; VCP within the handle |
| 3-C (Cup Completion Cheat) | Earlier entry; 4 steps: downtrend → upturn → pause (5–10%) → breakout |
| Low Cheat | Entry in lower ⅓ of base; riskier; good for large caps and IPOs |
| Double Bottom ("W") | Undercut preferred to shake weak hands |
| Power Play (High Tight Flag) | Stock up ≥100% in ≤8 weeks → tight flag ≤20% over 3–6 weeks |

## Related
- [[concepts/Darvas-Box]] — Manual equivalent of VCP
- [[concepts/Stage-Analysis]] — VCP only valid inside Stage 2 uptrend
- [[strategies/Minervini-SEPA]] — Complete trading framework built around VCP
- [[strategies/VCPBot-Trend-Template]] — Pre-filter that all stocks must pass before VCP detection
- [[analyses/VCPBot-Architecture]] — Full bot architecture and pipeline
- [[analyses/VCPBot-Risk-System]] — Risk sizing and regime logic
- [[concepts/Reversal-Chart-Patterns]] — shares the same "volume contracts before the real move" signature, applied to Double Top/Bottom and Head & Shoulders necklines instead of VCP contractions

## Sources
1. VCPBot GitHub (algorithmic 3-tier detection)
2. Personal notes PDF (Darvas/VCP discussion)
3. [Minervini-Think-Trade-Champion](../sources/Minervini-Think-Trade-Champion.md) — Sections 6, 7; original VCP definition, footprint notation, supply/demand dynamics
4. [TV-VCP-Scanner-Minervini-valchak](../sources/TV-VCP-Scanner-Minervini-valchak.md) — Pine v5 invite-only scanner; 6-gate signal engine; numeric contraction/extension defaults; RS proxy formula
