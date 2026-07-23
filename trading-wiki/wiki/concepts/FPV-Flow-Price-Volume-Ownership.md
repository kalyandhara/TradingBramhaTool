---
title: "FPV — Flow of Price, Volume, Ownership"
category: concept
tags: [fpv, ownership-flow, volume, price-action, shareholding, confirmation, smart-money]
created: 2026-07-21
updated: 2026-07-21
sources: 1
related:
  - sources/Crash-Proof-Market-Health-Ownership-Framework.md
  - strategies/Crash-Proof-3-Filter-System.md
  - concepts/Order-Flow.md
  - concepts/Stage-Analysis.md
  - analyses/Decision-Support-Gating-Roadmap.md
---

# FPV — Flow of Price, Volume, Ownership

## Definition

FPV reads **three flows together** — price direction, volume behind it, and the direction of institutional ownership change — to judge whether a move is backed by real participation or is running on thin/late money. It is a **timing-confirmation** layer, used *after* the structural filters (market health + stage) already agree, to decide entry.

`FPV = Price + Volume + Ownership`

> [!warning] Naming collision — THREE different "FPV" in this project
> The acronym is used **three incompatible ways** and they must not be conflated:
> 1. **This page (user's definition, 2026-07-21):** Flow of Price, Volume, **Ownership** — ownership = the FII/DII/MF/retail shareholding split. The three-component version.
> 2. **The FVG/FBG framework (user's definition, 2026-07-22):** Flow of Price, **Volume** only — *no ownership*. Used for FVG strength (Price↑+Vol↑ = strong FVG) and breaker validity (break on high vol = strong breaker, low vol = fake). The **two-component** version. See [[sources/FVG-FBG-Fibonacci-Retail-Framework]].
> 3. **The chart Fibonacci overlay** ([fibonacci.js](tools/fibonacci.js)): Fibonacci levels scored against **price projection + volume profile** confluence — no ownership, and the "V" is volume *profile*, not volume flow.
>
> The user's own two definitions (1 and 2) differ by whether ownership is included. Definition 2 is really the price+volume timing leg of definition 1 with the ownership leg dropped — usable standalone for chart/intraday reads where quarterly ownership data doesn't apply. Open question still stands: should the Fibonacci overlay's confluence incorporate ownership flow, or stay pure price-structure? Until resolved, treat all three as separate concepts sharing an unfortunate acronym.

## How to Use

The four combinations that time an entry:

| Price | Volume | Ownership | Reading | Action implication |
|-------|--------|-----------|---------|--------------------|
| ↑ | ↑ | FII ↑ | **Strong trend** | Fresh participation confirms the move — highest-conviction |
| ↑ | ↓ | MF ↓ | **Weak trend** | Rising on thinning volume with institutions leaving — distrust |
| ↓ | — | FII ↑ | **Smart-money accumulation** | Price falling while institutions buy — watchlist, not yet |
| ↑ | — | Retail ↑ | **Late trend** | Retail chasing — be cautious, trend is maturing |

- **FPV confirms, it does not initiate.** It only speaks once market health and stage already permit a trade.
- **Ownership is quarterly and slow.** Price and volume are daily; the shareholding split updates per filing. FPV therefore blends a fast pair (price+volume) with a slow structural anchor (ownership) — the ownership leg sets *bias*, the price+volume leg sets *timing*.

## Variants / Parameters
- **Ownership granularity:** the framework wants the full FII / DII / MF / Retail split. The dashboard's [nse_shareholding_fetch.py](tools/nse_shareholding_fetch.py) currently exposes **FII change only** — the DII/MF/retail legs are a data gap (see [[analyses/Decision-Support-Gating-Roadmap]]).
- **Volume reference:** "volume up/down" is relative to a recent average (e.g. 20-day), consistent with the OI Momentum and CEAVET conventions already in the stack.

## Common Mistakes
- **Conflating the two FPVs** (see the warning above) — scoring a Fibonacci level against ownership, or vice versa.
- **Trading FPV standalone.** Price↓ + FII↑ ("accumulation") is a *watch* signal, not a buy — acting on it without market health + Stage 2 is catching a falling knife.
- **Trusting retail-heavy up-moves.** Price↑ + Retail↑ is explicitly a *late-trend caution*, not confirmation.

## Related Concepts
- [[concepts/Order-Flow]] — intraday order-flow; FPV is the slower, ownership-anchored cousin.
- [[concepts/Stage-Analysis]] — FPV only fires inside a permitted stage.
- The **OI Momentum** page (price vs open-interest, [nse_oi_momentum.py](tools/nse_oi_momentum.py)) is a price+positioning cousin of FPV's price+volume leg — same "is the move built or vacated" question, read through derivatives OI instead of ownership.

## Examples in This Wiki
- [[strategies/Crash-Proof-3-Filter-System]] uses FPV as its confirmation stage.
- [[sources/Crash-Proof-Market-Health-Ownership-Framework]] is the source that defined it.

## Sources
- [[sources/Crash-Proof-Market-Health-Ownership-Framework]]
