---
title: "EVWMA/VWAP MACD — the QuantNomad crossover, measured"
category: concept
tags: [EVWMA, VWAP, MACD, crossover, volume-weighted, measured-null, pine-port]
created: 2026-08-29
updated: 2026-08-29
sources: 1
related: [concepts/ADX.md, concepts/VWAP.md, concepts/MACD-Divergence.md, analyses/Open-Backlog.md]
---

# EVWMA/VWAP MACD

## What it is
A MACD built not on price but on the **gap between price and a volume-paced anchor**.
Port of QuantNomad's Pine v4 `EVWMA_VWAP_MACD[QN]` strategy, defaults 30 / 5 / 20:

```
vol_period = sum(volume, 30)
evwma     := ((vol_period - volume) * nz(evwma[1], close) + volume * close) / vol_period
diff       = vwap - evwma
macd = ema(diff, 5)     signal = ema(diff, 20)     hist = macd - signal
long on crossover(macd, signal)      short on crossunder(macd, signal)
```

**EVWMA** (elastic volume-weighted MA) advances only as fast as traded volume lets
it — each bar gets weight `volume / Σvolume(30)`, so a high-volume bar drags the
anchor hard and a quiet bar barely moves it. It is a *volume* clock, not a time
clock. `diff` is therefore "how far has price run ahead of where volume actually
transacted", in price units, and zero is a real level.

Shipped as `tools/evwma_vwap_macd.js` (`window.EVMACD`) + the `evmacd` oscillator
in the chart tool: 4-state Pine histogram, macd/signal lines, and BUY/SELL arrows
mirrored onto the candles.

## The VWAP trap in this formula
Pine's `vwap` is the **session** VWAP. On a 1D chart each bar *is* its own session,
so TradingView's `vwap` silently collapses to that bar's `hlc3` — the reference
chart is plotting price-vs-anchor, not price-vs-VWAP. The port reproduces this
exactly: session VWAP on intraday timeframes, `hlc3` on 1d+. Same finding already
recorded in `chart_dashboard.vwapSeries` (daily "session VWAP" measured equal to
(H+L+C)/3 on 24 of 24 bars).

Sensitivity check: swapping the daily source between `hlc3`, `close`, `ohlc4` and
`hl2` moves macd/signal by <5 points on a ~4,400 price — **the source choice is
not what drives this indicator**; the EVWMA anchor is.

## Port verification (HAL.NS 1d, vs the TradingView reference chart)
| bar | TradingView | port |
|---|---|---|
| 2025-12-24 | macd −200.81 · signal −207.14 · hist 6.33 | −182.73 · −200.43 · 17.70 |
| 2026-08-28 | macd 193.33 · signal 251.76 · hist −58.43 | 166.25 · 231.55 · −65.30 |
| signal dates | LONG 2025-12-24, SHORT 2026-08-24 | same bars ✓ |

**Cross timing matches bar-for-bar**; levels sit ~0.4–0.6% of price apart. The gap
traces to the EVWMA anchor, whose long-memory volume recursion amplifies small
feed differences (yfinance vs TradingView's NSE OHLC — the Dec-24 bar's low/open
differ between feeds even though volume matches to the share). Not a formula
difference; do not "fix" it by tuning constants.

## Measured evidence — the crossover has NO edge
`tools/evwma_vwap_macd_backtest.py` (signals from the shipped JS engine via
`evwma_vwap_macd_backtest.js`, so the tested rule *is* the shipped rule).
23 liquid NSE names + NIFTY + BANKNIFTY, ~19 years, 18,595 baseline samples,
next-open entry, Welch two-sample p vs the every-bar baseline.

```
baseline mean fwd %:  5d +0.31  10d +0.72  20d +1.54  60d +5.05

leg                  n        5d edge (p)     10d edge (p)     20d edge (p)     60d edge (p)
cross_up (BUY)    3098      +0.10 (0.32)     +0.04 (0.75)     +0.17 (0.36)     +0.04 (0.91)
cross_dn (SELL)   3106      +0.07 (0.49)     +0.11 (0.42)     -0.13 (0.50)     +0.04 (0.91)
```

Every cell is inside noise. The BUY cross does not beat simply being in the market;
the SELL cross does not mark underperformance (its 20d edge is −0.13% at p=0.50).

Strategy equity, zero costs, next-open fills, median across the 23 names:

| variant | median return | beat buy&hold |
|---|---|---|
| stop-and-reverse (the Pine script) | **−29%** | 1 / 23 |
| long-only (short cross = go flat) | +314% | 1 / 23 |
| buy & hold | +827% | — |

At 20 bps per flip the stop-and-reverse median falls to −64% and long-only to
+204%. With ~17 flips a year, cost is not a rounding error here.

## Verdict
**Context indicator, not a trigger.** Same shelf as the DI cross in
[[concepts/ADX]]: legitimate to read — the histogram's 4-state colouring shows
momentum fading before it flips, and macd crossing zero means price crossed its
volume anchor — but the crossover itself carries no measurable forward edge on
NSE dailies, and trading it mechanically underperforms holding by a wide margin.
Any future use should be as a **filter/confluence leg inside a rule that already
has edge**, tested as such, not as a standalone entry.

## Sources
- QuantNomad, "EVWMA VWAP MACD Strategy" (Pine v4) — the reference script.
- Measured 2026-08-29 in this repo; re-run with
  `py -3 tools/evwma_vwap_macd_backtest.py --export`.
