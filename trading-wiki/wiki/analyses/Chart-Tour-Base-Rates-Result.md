---
title: "Chart Tour Base Rates — Result: gaps up, AB=CD and ATR carry; 15 of 20 are ordinary"
category: analysis
tags: [b-186, chart-tour, base-rate, result, evector, gaps, abcd, squeeze, calibration]
created: 2026-10-26
updated: 2026-10-26
sources: 1
related: [analyses/Chart-Tour-Base-Rates-Pre-Registration, sources/Web-eVector-Event-Vector-Markets, analyses/Open-Backlog, analyses/Bull-Trap-Detector]
---

# Chart Tour Base Rates — Result (B-186)

Run as pre-registered on [[analyses/Chart-Tour-Base-Rates-Pre-Registration]],
committed at `6f6ba7c` before any real run. Code: `tools/tour_base_rates.py`.
Output, both versioned:
- `tools/cache/tour_base_rates.json`: the main panel, which the tour's badges
  serve;
- `tools/cache/tour_base_rates_confirm.json`: the confirmatory panel.

## Thesis

What has each "Tour this chart" card actually been followed by on NSE, compared
with the same stock's ordinary day?

## Verdicts (labels as computed; confirmation per the pre-registration)

| Card | Main panel `nifty500[:300]` | Fresh panel `nifty500[300:500]` | Shown on the card |
|---|---|---|---|
| **Unfilled gap up (≥3%)** | **EDGE** +2.85% @20d (+1.43 @5, +3.78 @60), Holm p 4e-13, all 3 thirds | **EDGE** +2.48%, Holm p 5e-9 | Edge, confirmed |
| **Bullish AB=CD (B-132 stop)** | **EDGE** +1.18% @20d, Holm p 0.019 | **EDGE** +1.64%, Holm p 0.013 | Edge, confirmed |
| **Volatility expansion (ATR14 ≥1.4×)** | **EDGE**: moves 0.59 pts larger @20d, Holm p 0.035 | **EDGE**: 1.12 pts larger, Holm p 0.0008 | Edge, confirmed |
| **55-day breakdown** | **INVERTED**: the stock *outperformed* by 0.81% @20d (2.56% @60d), Holm p 0.002 | **INVERTED** −0.77%, Holm p 0.018 | Worked backwards, confirmed |
| **Below the 200-day average** | **EDGE**: fell a further 1.01% vs normal, Holm p 0.007 | ORDINARY (same sign, −1.03%, Holm p 0.16) | Edge, **not confirmed on a fresh panel** (amber) |
| The other 15 | ORDINARY | ORDINARY except the two leads below | Ordinary |

The main panel had 258 names with data (60,577 events); the fresh panel had 170
names (39,913 events). Every label cleared the floors, so none is TOO_FEW.

**Ordinary on both panels:**
- the 55-day breakout and the failed breakout;
- the failed breakdown;
- volume expansion;
- both RSI divergences;
- above the 200-day average;
- the golden and death crosses;
- structure break holding;
- bullish liquidity sweep;
- bull flag & pole;
- ADX up-state.

## Evidence against / limitations

- **Gross of costs**, and these are 20-session holding numbers from the first bar
  the card is visible, not a trade plan.
- **Gap up is the large one, and its direction is plausible.** Gaps on news or
  results tend to keep going (post-earnings drift). But +2.85% at p 4e-13 is big
  enough to deserve a look for data causes. A split or bonus done on unadjusted
  prices would look like a gap *down*, not up, so it can't create this effect.
  Even so, it has not been tested against a news-matched control.
- **The desk detectors disagree with their own studies in three places.** The
  question here is "first visible bar against a normal day", not each study's own
  entry, so the panel number and the study number sit side by side on the card:
  - **Bullish liquidity sweep:** ORDINARY here (−0.28%), against B-41m's +0.51%
    at 20 days net of costs. B-41m used the scanner's signal bar on a different
    window. This **needs reconciling**, because B-41m was the desk's one
    cost-surviving edge.
  - **Structure break holding:** ORDINARY. B-114 compared held breaks with failed
    breaks, not with a normal day, so the two measured different things.
  - **Flag & pole:** ORDINARY. B-92 measured *breakouts* only, while this card
    fires on every detected flag, broken or not.
  - **AB=CD agrees with B-132.**
  - **ADX up-state:** ORDINARY at 20 days and −0.56% at 60 days, against the
    ADX study's +1.82% at 60 days. Different window and different entry.
- **Miscount in the pre-registration.** It says "17 badges" but enumerates 20
  detector keys (15 ported + 5 desk). The run used the enumerated 20 as the Holm
  family, which is what the page's list fixed.

## Leads (exploratory, NOT promoted: significant on the fresh panel only)

- **Squeeze:** INVERTED on the fresh panel. Moves after a squeeze were 0.79 pts
  *smaller* than normal (Holm p 0.0008). The main panel gave the same sign
  (−0.45 pts, p 0.008) but not after Holm. That runs against eVector's "a large
  move often follows", and matches B-101 (a coil precedes an ordinary move).
- **Unfilled gap down:** INVERTED on the fresh panel. Stocks outperformed by 1.54%
  over 20 days, the same sign as the main panel (−0.77%, p 0.04). Together with
  the 55-day breakdown, it reads as **downside events mean-reverting**.

## Conclusion

- **The tour now carries measured badges.** Most cards are honestly **ordinary**:
  the textbook breakout, divergence, cross, squeeze and volume reads add nothing
  over a normal day on NSE over 2023–2026.
- **Three cards carry confirmed information:**
  - an unfilled gap up tends to keep going;
  - a bullish AB=CD tends to rise;
  - an ATR expansion tends to be followed by bigger moves.
- **One card works backwards:** a fresh 55-day breakdown tends to bounce.

## Action taken / plan

- **Badges are live** on the Chart Tool's TOUR panel. A badge shows the number in
  the stock's own direction and flags any result the fresh panel didn't confirm.
- **Follow-ups** (filed under B-186, not started):
  - reconcile the bullish-sweep result with B-41m;
  - test gap-up with a news- or earnings-matched control;
  - pre-register the two exploratory leads (squeeze smaller moves, gap-down
    bounce) on a third panel before they are shown as anything but ordinary.
- **Refresh:** re-run `tour_base_rates.py`, then `--merge-confirm`, monthly. A
  badge goes amber once its file is more than 45 days old.

## Outcome (fill in later)

## Related Pages

- [[analyses/Chart-Tour-Base-Rates-Pre-Registration]]
- [[sources/Web-eVector-Event-Vector-Markets]]: the detectors' origin
- [[analyses/Open-Backlog]]: B-186
