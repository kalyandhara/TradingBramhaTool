---
title: "Chart Tour Base Rates — Test Design (pre-registered)"
category: analysis
tags: [pre-registration, b-186, chart-tour, base-rate, evector, detectors, null-model]
created: 2026-10-26
updated: 2026-10-26
sources: 1
related: [sources/Web-eVector-Event-Vector-Markets, analyses/Open-Backlog, analyses/Bull-Trap-Detector, analyses/Bilateral-Expansion-Pre-Registration]
---

# Chart Tour Base Rates — Test Design (pre-registered)

**Written before any real-data run. No real-data run has been made at the time of
this commit.** `tools/tour_base_rates.py` has only seen synthetic panels in its
tests.

B-186 adds a "Tour this chart" panel to the Chart Tool. Each card on it carries a
**badge**: what that exact detector has been followed by on NSE, compared with the
same stock's ordinary day. This page fixes how that number is measured before
any of it is known.

- **Origin:** [[sources/Web-eVector-Event-Vector-Markets]]. eVector's detectors
  were reverse-engineered there (exact thresholds); eVector itself shows hand-set
  weights and no evidence.
- **Spec:** `docs/superpowers/specs/2026-10-26-chart-tour-design.md`, §3.

## Detectors (17 badges)

**Ported from eVector, thresholds verbatim:**
- `breakout55` / `failed_breakout55` (failed below 0.98 × the level)
- `breakdown55` / `failed_breakdown55` (failed above 1.02 × the level)
- `gap_up` / `gap_down`: at least 3 %, unfilled, within the last 10 bars
- `volume_expansion`: last 5 bars ≥ 1.5 × the 50 before
- `atr_expansion`: Wilder ATR14 ≥ 1.4 × its value 42 bars ago
- `squeeze`: Bollinger(20, 2) width within 5 % of its 126-bar minimum
- `bearish_div` / `bullish_div`: 5-bar fractal swings, RSI14 gap > 4
- `above_sma200` / `below_sma200`
- `golden_cross` / `death_cross`

**The desk's own detectors, called rather than copied:**
- `structure_break_held` (B-114's detector)
- `liquidity_sweep_bull` (B-41m)
- `flag_pole_bull` (B-92)
- `abcd` (B-132's scanner set, stop D − 2 × ATR14)
- `adx_up_state` (the ADX study's `state_bull_adx_rising`)

## Design (fixed now)

- **Panel:** `nse_universe.symbols("nifty500")[:300]`, using
  `crt_sweep_overlap._fetch`, evaluated on the last 750 daily bars. This is the
  B-165 / B-182 panel.
- **Event:** the first bar on which the card would have been visible, computed
  using only the bars up to that one (each evaluation sees a trailing 260-bar
  window).
  - A failed breakout counts on the day it fails.
  - A state card (volume / ATR expansion, squeeze, 200-day average, ADX up-state)
    counts when it turns on, and not again within 20 bars.
- **Outcome:** the forward log return over 5, 20 and 60 sessions, minus the same
  stock's mean forward return over the evaluated bars.
  - **Directional cards** are sign-aligned to their tone, so a bearish card
    that "works" scores positive.
  - **Magnitude cards** (squeeze, ATR expansion) use |return| minus the stock's
    mean |return|.
  - All returns are **gross of costs**.
- **Statistic:** each stock's mean excess, then a one-sample t-test across
  stocks. The 20-session horizon decides; 5 and 60 are reported.
- **Labels:** all detectors form one family, Holm-corrected at α 0.05.

  | Label | Rule |
  |---|---|
  | `EDGE` | ≥ 30 names and ≥ 100 events; Holm p < 0.05; mean > 0; sign held in ≥ 2 of 3 equal time-thirds |
  | `INVERTED` | the same, but mean < 0 |
  | `ORDINARY` | floors met, nothing significant |
  | `TOO_FEW` | floors not met |
  | `NOT_MEASURED` | shown when the file or the row is absent |

- **Disagreements:** a desk detector's panel number is shown beside its
  pre-registered study. Neither overrides the other; any disagreement is written
  on the result page.

## Priors (recorded before the run)

- **Most ported detectors come out ORDINARY.** The desk's earlier tests on close
  relatives were null:
  - failed breakouts: B-182, +0.11 %, p 0.47;
  - the coil: B-101, an ordinary-sized move;
  - unfilled gaps: FVG-fill, "not magnets";
  - breakouts: B-147, failed its bar.
- **`squeeze` comes out ORDINARY on magnitude**, which contradicts eVector's own
  claim that "a large move often follows" (see B-101).
- **The desk detectors may not reproduce their studies on this panel and
  window.** The events here are first-visible bars, not the studies' own
  entries.
- **Any EDGE label is a surprise** and gets a confirmatory re-run on a fresh
  panel (`nifty500[300:500]`) before it is trusted.

## Run

```
py -X utf8 tools/tour_base_rates.py --symbols 300
```

Output: `tools/cache/tour_base_rates.json`, which `/api/tour` serves as each
card's badge. The result goes on [[analyses/Chart-Tour-Base-Rates-Result]].
