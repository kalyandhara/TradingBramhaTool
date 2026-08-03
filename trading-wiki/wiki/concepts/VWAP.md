---
title: "VWAP — Volume Weighted Average Price"
category: concept
tags: [indicator, vwap, intraday, mean-reversion, momentum, session-anchor]
created: 2026-07-06
updated: 2026-08-02
sources: 2
related: [concepts/Anchored-VWAP-Pyramiding, strategies/TechnoFunda-Swing, strategies/Hyperliquid-Momentum-Screener, sources/ForexTester-Anchored-VWAP-Guide]
---

# VWAP — Volume Weighted Average Price

## Definition
VWAP is the average price of a session weighted by traded volume at each price. It is the anchor price that intraday participants gravitate around: the level at which the *typical* traded share/coin changed hands today, not merely the arithmetic mid.

- **Formula (running):** VWAP_t = Σ(Price_i × Volume_i) / Σ(Volume_i), summed from session open to time t.
- **Reset behavior:** classic session VWAP resets at each session open. Anchored VWAP (AVWAP) resets at a chosen event and is covered separately — see [[concepts/Anchored-VWAP-Pyramiding]].
- **Bands:** ±1 standard deviation bands around VWAP visualise how far price is stretched from the anchor and act as a proxy for realized intraday volatility.

## How to Use
Read three signals off VWAP jointly — a single signal in isolation is low-conviction ([[sources/X-KoroushAK-VWAP-Masterclass-20260506]]):

1. **Position** — where is price relative to VWAP?
   - Above VWAP → uptrend bias, favours breakouts / momentum longs.
   - Below VWAP → downtrend bias, favours breakdowns / momentum shorts.
   - Above the *upper* band (or below the *lower*) → extra strength / weakness.
2. **Slope** — is VWAP itself trending?
   - Steep slope → price is trending, favours continuation trades.
   - Flat slope → price is ranging, favours mean-reversion trades.
   - Fewer price↔VWAP crossovers = cleaner trend; frequent crossovers = chop.
3. **Bandwidth** — how wide are the ±1 SD bands?
   - Widening bands → strength/conviction behind the move, favours continuation.
   - Tight bands → hesitation, favours reversal / mean reversion.

### Decision matrix
| Slope | Bands | Position | Play |
|-------|-------|----------|------|
| Steep up | Widening | Price > VWAP (best: > upper band) | Momentum long / breakout |
| Steep down | Widening | Price < VWAP (best: < lower band) | Momentum short / breakdown |
| Flat | Tight | Either side | Reversal / mean reversion |
| Flat | Tight + many crossovers | Price faking a breakout | Fade the fakeout |

## Session VWAP vs Anchored VWAP
Independent confirmation of this page's "don't swing-trade off session VWAP" rule ([[sources/ForexTester-Anchored-VWAP-Guide]]):

| | Session VWAP | Anchored VWAP |
|---|---|---|
| Start | Fixed at session open | Any candle you choose |
| Reset | Daily | Never — cumulative from the anchor |
| Use case | Intraday mean reversion | Multi-day trend, event-driven |
| Timeframe | **Intraday only** | Any |
| Weakness | *"Useless for swing analysis; gaps overnight"* | Requires judgement picking anchors |

This is not a stylistic preference — it is arithmetic. On a daily chart each bar *is* a session, so a session-reset VWAP collapses to that bar's own typical price and stops being volume-weighted at all. Our chart tool therefore draws session VWAP only on `1m`–`4h` and refuses it on `1d`/`1w`; measured on daily RELIANCE bars before that guard, the line equalled `(H+L+C)/3` on **24 of 24** bars. See [[concepts/Anchored-VWAP-Pyramiding]] for what to use instead.

## Variants / Parameters
- **Anchor:**
  - *Session* — resets each day (default for intraday).
  - *Anchored (AVWAP)* — reset at a chosen event (earnings, swing low, IPO). See [[concepts/Anchored-VWAP-Pyramiding]].
  - *Rolling / weekly / monthly* — accumulates over a longer window; more of a swing tool.
- **Bands:** ±1 SD is the working default. Some traders add ±2 SD for extreme-stretch signals. Wider bands = less sensitive to noise.
- **Timeframe:** intraday chart (1m–15m) is where session VWAP is most meaningful. On daily charts, prefer AVWAP or an EMA.

## Common Mistakes
- **Using VWAP as a signal, not a filter.** VWAP alone does not tell you when to enter — it tells you which *kind* of setup has edge right now (momentum vs reversal).
- **Ignoring slope and bandwidth.** Reading only price-vs-VWAP direction misses the strategy-bias half of the signal and leads to fading strong trends or chasing choppy tape.
- **Applying session VWAP to swing trades.** Session VWAP resets daily and does not carry information across sessions; for multi-day setups use AVWAP from a meaningful anchor.
- **Fading price above VWAP just because it's "extended."** In a widening-band, steep-slope regime, "extended" above VWAP is exactly where momentum trades pay — bandwidth tells you whether extension is exhaustion or conviction.
- **Trusting VWAP on low-volume instruments.** The whole point of the weighting is volume; on illiquid names, VWAP is noise.

## Related Concepts
- [[concepts/Anchored-VWAP-Pyramiding]] — event-anchored variant used for swing pyramiding.
- [[concepts/EMA]] — comparable trend filter without volume weighting.
- [[concepts/Multi-Timeframe-Analysis]] — session VWAP is a lower-timeframe tool; combine with higher-timeframe structure.

## Examples in This Wiki
- [[strategies/TechnoFunda-Swing]] — uses `close > VWAP` as one of its 7 gate conditions. Per this concept page, that gate can be tightened by also requiring non-flat slope on entry day.
- [[strategies/Hyperliquid-Momentum-Screener]] — requires price > VWAP as part of the EMA9/21/50+VWAP trend stack for crypto momentum candidates.
- [[sources/X-KoroushAK-VWAP-Masterclass-20260506]] — Koroush AK's 3-signal framework (position / slope / bandwidth) with real coach trade examples (Brandon breakdown short, Josh crypto momentum long, Kim fakeout avoidance).

## Sources
- [[sources/X-KoroushAK-VWAP-Masterclass-20260506]]
- [[sources/ForexTester-Anchored-VWAP-Guide]] (2026-08-02) — session-vs-anchored comparison, the explicit AVWAP formula, and Brian Shannon as the originator of the anchored variant
