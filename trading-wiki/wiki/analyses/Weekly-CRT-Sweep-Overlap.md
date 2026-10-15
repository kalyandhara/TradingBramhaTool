---
title: "B-165 — Weekly Candle Range Theory vs Liquidity Sweep: overlap check"
category: analysis
tags: [b-165, smc, crt, liquidity-sweep, overlap-check, pre-registration]
created: 2026-10-15
updated: 2026-10-15
sources: 0
related:
  - analyses/Open-Backlog
  - analyses/LuxAlgo-SMC-ICT-Gap-Analysis
  - analyses/Backtest-Harness
---

# B-165 — Weekly CRT vs Liquidity Sweep: overlap check

**This is an OVERLAP CHECK, not an edge test.** It follows the B-59 precedent
(`psar_overlap.js`): count first, because if weekly CRT fires where `Liquidity Sweep`
already fires there is nothing new to measure, and the question closes without a
backtest. No forward return is computed anywhere in this item.

## Pre-registration — written 2026-10-15, BEFORE the script was first run

### The two event sets
**Weekly CRT, bullish** (`tools/crt_weekly.py`, built for this item):
* Daily bars resampled to calendar weeks ending Friday (open = first, high = max, low = min,
  close = last). Only **completed** weeks: the final, possibly partial, week of the panel is dropped.
* Week *t* is a bullish CRT when, against week *t−1* (candle 1):
  1. `low[t] < low[t−1]`: candle 2 traded below candle 1's low (the sweep);
  2. `low[t−1] < close[t] < high[t−1]`: candle 2 closed back **inside** candle 1's range;
  3. `high[t] <= high[t−1]`: **outside weeks are excluded**. A week that ran both
     extremes swept both sides, which is not a directional sweep.
* No pierce-size floor, because LuxAlgo's definition has none. The pierce in ATR is recorded
  as a description, not a filter.
* An event spans the trading days of week *t*.

**Liquidity Sweep, bullish**: the registered scanner `scan_liquidity_sweep`, run **as
shipped** (pivot 5, its own gates), replayed point-in-time on every daily bar of the
evaluation span. A firing is identified by its **swept bar** (`t − bars_ago` from
`detect_liquidity_sweep`), so the 1–4 consecutive days one sweep keeps firing count as one event.

### Panel
`nse_universe` "nifty500", first 300 names (the B-124 panel), 1500 days daily via
`screener_pipeline.fetch_ohlcv`. Evaluation span: the **last 750 trading days** of each
name. Both event sets come only from that span.

**Speed concession, declared before running:** each scanner call sees a trailing
**500-bar** window rather than full history. A **parity check** on 10 names compares the
swept-bar event sets from the 500-bar window against full history. If they differ on more than
2% of events, the run uses full history instead.

### What "covered" means
Direction-matched and windowed, as in B-59. A CRT event is **covered at tolerance d** if a
Liquidity Sweep event's swept bar falls within the CRT week extended by *d* trading days on
each side. *d* is swept over **0, 2, 5, 10** and the whole curve is printed. The reverse
containment (sweeps covered by a CRT week ± d) is printed too.

### Decision rule (fixed now)
* **SUBSET**: if **≥ 80%** of CRT events are covered at **d = 5**, CRT adds nothing over the
  sweep. **B-165 closes; no edge test is owed.**
* **NOT A SUBSET**: if coverage is below 80%, CRT carries events the sweep scanner never sees.
  File **B-165r**: a separately pre-registered forward-return test of weekly CRT, on all events and on
  the uncovered ones. It is **not** run in this item.
* **TOO RARE**: if there are fewer than **150** CRT events on the panel, close B-165 as not worth a measurement.

### Prior, stated so the result can be wrong against it
**NOT A SUBSET, with coverage around 20–40% at d = 5.** The sweep scanner needs a
multi-touch equal-lows pool (≥ 2 touches), a dominant rejection wick and a pierce of
0.05–2 ATR. A weekly CRT needs only one prior week's low, which is a far looser condition, so most CRT weeks
should have no daily sweep inside them.

## Result — RUN 2026-10-15: NOT A SUBSET → B-165r filed

**Deviation, applied as pre-registered:** the 500-bar window **failed** its parity check
(10 names: 161 window events vs 208 full-history events, 27.4% apart, bar 2%), so the
registered run used **full history**, the fallback the pre-registration names.
`tools/crt_sweep_overlap.py`; output `cache/crt_sweep_overlap.json`.

**258 of 300 names** usable (the rest failed to fetch or had under 810 bars). **6,502 weekly
CRT events, 5,316 Liquidity Sweep events**, last 750 bars each. Median CRT pierce **0.45 ATR**.

| d (trading days) | CRT covered by a sweep | sweeps inside a CRT week ± d |
|---|---|---|
| 0 | 14.9% | 21.4% |
| 2 | 20.7% | 32.8% |
| **5 (decides)** | **28.1%** | 47.5% |
| 10 | 37.5% | 66.3% |

**Verdict: NOT A SUBSET** (28.1% < 80%; 6,502 ≥ 150 events). Inside the prior's 20–40% band.
Per the rule, **B-165 closes and B-165r is filed**: a separately pre-registered forward-return
test of weekly CRT. It is not run here.

**Descriptive, not pre-registered:** sweeps fire on 2.75% of symbol-days, so a random
15-session window (a week ± 5) holds at least one about **34%** of the time. CRT weeks are covered
**28%** of the time, i.e. no more often than chance. The two detectors are not loosely nested
versions of one event: a weekly CRT is, statistically, a different event from a daily
equal-lows sweep. That is why an edge test is owed, and also why the sweep's B-41m
result says nothing about whether CRT has an edge.
