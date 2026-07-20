---
title: "X Article — Koroush AK: My Breakout Trading Strategy"
category: source
tags: [breakout, momentum, mean-reversion, 1-minute, support-resistance, volume, sma, risk-reward]
created: 2026-07-06
updated: 2026-07-06
sources: 1
related: [strategies/Koroush-Breakout-Momentum, concepts/VWAP, concepts/Support-Resistance, concepts/EMA]
---

# X Article — Koroush AK: My Breakout Trading Strategy

## Metadata
- **Author:** Koroush AK (@KoroushAK)
- **URL:** https://x.com/KoroushAK/status/2016502313230504233 (X long-form article)
- **Posted:** 2026-01-28
- **Title:** "My Breakout Trading Strategy"
- **Engagement:** 869 likes, 2202 bookmarks, 385K views
- **Format:** X long-form article — 4 lessons (framework, environment, setup, execution) with real coach trade examples
- **Date accessed:** 2026-07-06
- **Author bias:** long-volatility momentum trader on crypto; explicitly reverse of the retail "buy support / short resistance" instinct.

## Key Takeaways
- **Two-strategy taxonomy:** every trade is either **momentum** (bets a level breaks) or **mean reversion** (bets a level holds). Same chart, opposite trades — edge comes from matching strategy to *environment*, not from picking the "right" strategy.
- **3-filter environment checklist** for taking a momentum long (all must align for full size):
  1. **Price approach:** slow grinding staircase into resistance — NOT a fast vertical spike (spike = exhaustion, not momentum).
  2. **Volume:** gradually increasing as price approaches the level. Flat volume = no conviction; sudden spike = climax/exhaustion.
  3. **MA crossovers:** use **30-period Smoothed MA (SMMA-30)** — minimal price↔MA crossovers = clean trend; frequent = chop, skip.
- **Execution recipe (crypto, 1-minute chart):**
  - Draw S/R on primary timeframe → drop to 1m for entry.
  - **Trigger:** two consecutive 1m candle closes fully above resistance.
  - **Entry:** limit order **AT** prior resistance (now support), NOT above it — pullback fill, no chasing.
  - **Stop:** most recent valid swing low before the breakout. If distance < 1%, drop to the next swing low down (avoid stop-hunt on normal volatility).
  - **Target:** **1R** (equal distance to stop) — 1:1 R/R baseline; extend later using journal data.
- **Partial-size rule:** if any of the 3 filters fails, take reduced risk, not zero — but full size only on A-grade all-three-align setups.
- **Practice protocol:** 30 journalled trades on this method before evaluating; use 1m chart because it compresses reps and psychology exposure.

## Detailed Notes

### Lesson 1 — The only 2 strategies
- Momentum = bet the level breaks; mean reversion = bet it holds. Neither is "better."
- The failure mode retail traders hit: applying breakout logic in a mean-reversion environment (choppy, tight, low-volume) and getting chopped out on every fake break.

### Lesson 2 — Optimal environment (the "rowing with the current" analogy)
- **Filter 1 — approach shape.** Staircase of higher lows into the level = sustained absorption of supply; fast candle into the level = one-shot buyer group whose ammo is spent by the time price touches resistance.
- **Filter 2 — volume signature.** Wants *gradual* increase (or at worst steady). Explicitly flags decreasing volume as disqualifying ("why would price break out now if volume was lower than before?"). A sharp spike near the level is a *climax*, not a fuel-up.
- **Filter 3 — MA crossover count.** SMMA-30 on the trading TF; count how often price crosses the MA. Few crossovers = directional regime; many = chop.

### Lesson 3 — Setup identification
- **Step 1:** draw consistent S/R levels (references his separate S/R masterclass — not in this article).
- **Step 2:** drop to 1-minute for entry timing once the primary-TF level is identified.
- **Step 3:** re-run the 3-filter checklist immediately before pulling the trigger. Reduce size on any partial fail; skip if two or more fail.

### Lesson 4 — Execution mechanics
- **Entry trigger:** 2 consecutive 1m closes fully above resistance. This is the "break confirmed" signal.
- **Limit-at-level, not market-above-level.** The article calls out the specific retail mistake of confirmation-then-chase. Preset the limit order AT the broken resistance (now support) and wait for the pullback fill.
- **Swing-low stop with 1% floor.** Swing low = lowest wick of the most recent pullback. If measured stop distance < 1%, use the *previous* swing low. Rationale: normal volatility eats sub-1% stops from stop-hunt wicks.
- **1R target as baseline.** Baseline exit at same distance as stop, in profit direction. Rationale for starting conservative: momentum breakouts hit 1R fast because of continuation follow-through; 1R gives a repeatable, high-probability slice rather than trying to catch the entire move. Extend targets only after journal data justifies it.

## Actionable Insights
- **Adopt the 3-filter checklist as a gate** on the dashboard's breakout scanners (Scanner Hub, Breakout Screener). Right now those scanners emit candidates on structural pattern alone — adding the "approach shape" (staircase vs spike), "volume slope" (increasing vs flat/spike), and "MA-30 crossover count" filters would separate A-grade from noise before a signal ever reaches the Telegram/UI layer.
- **Codify the "limit AT prior resistance" entry** in any breakout playbook page — it's a concrete rule that prevents the chase-after-confirmation failure mode. Different from and complementary to Minervini pivot-buy logic (which is "buy at pivot ± tick").
- **The 1% stop floor is a numeric commitment** worth carrying into risk-sizing code — any scanner that outputs a stop level < 1% away from entry should either downgrade the setup or bump to the next swing low automatically.
- **SMMA-30 is a new concept for this wiki.** Different from EMA/SMA — worth adding as a variant note on [[concepts/EMA]] rather than a whole new page.
- **Article's 1R baseline maps directly** to the R-multiple framework already implied in [[strategies/Minervini-SEPA]] and [[strategies/Parabolic-Short-First-Red-Day]] — but Koroush's version is *systematic-first* (always 1R until journal data expands it), rather than structural (target = next resistance).

## Contradictions with Existing Wiki
- **1-minute execution timeframe** is a sharper stance than most swing/position-focused strategies already on the wiki. Not a contradiction so much as a *scope extension* into intraday crypto. Flag on the new strategy page so it doesn't accidentally get applied to Indian equity swing scans.
- **"Limit AT the level, not above"** contradicts a common textbook rule of buying stop-orders slightly above the pivot to require confirmation. Koroush's argument: 2-candle-close already confirmed the break, so the pullback fill is safer than the chase fill. Worth flagging on any future page comparing entry philosophies.
- **"Staircase good, spike bad" approach filter** overlaps semantically with the new [[concepts/VWAP]] concept's "flat slope + tight bands + many crossovers → fakeout guard" — both are trying to distinguish real breakouts from exhaustion pops. Cross-reference.

## Pages Updated
- Created: `wiki/strategies/Koroush-Breakout-Momentum.md`
- Updated: `wiki/index.md` (new source + strategy rows), `wiki/log.md`
- Cross-references: [[concepts/VWAP]] (crossover-count filter is thematically identical to VWAP slope/crossovers)
