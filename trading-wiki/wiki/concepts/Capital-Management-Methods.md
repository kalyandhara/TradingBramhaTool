---
title: "Capital Management / Position Sizing Methods"
category: concept
tags: [position-sizing, kelly-criterion, optimal-f, money-management, risk, atr, trailing-stops, r-multiple]
created: 2026-06-15
updated: 2026-06-22
sources: 4
related: [analyses/Kalyan-Trading-Philosophy.md, strategies/Systematic-Strategy-Search.md, concepts/Performance-Metrics.md, concepts/Anchored-VWAP-Pyramiding, sources/SwingEdge-Learn-Process-Risk-Workflow]
---

# Capital Management / Position Sizing Methods

## Definition
A catalogue of position-sizing ("capital management") methods used to translate a strategy's edge into how much capital to risk per trade. Position sizing is treated as a separate, pluggable component from the entry/exit logic — the same signal can be paired with different sizing methods.

## How to Use

### Fixed Position Sizing
- **Fixed amount**: every trade risks/uses the same absolute money amount, regardless of account balance.
- **Fixed percentage of capital**: every trade risks the same % of *current* capital — automatically compounds (position size grows with equity, shrinks with drawdown).

### Kelly Criterion
`f* = win_rate - (1 - win_rate) / (avg_win / avg_loss)`, i.e. `f* = x - (1-x)/z` where `x` = win probability, `z` = avg win / avg loss ratio.
- Worked example: x = 0.48, z ≈ 2.33 → f* ≈ 22.68% of capital per trade.
- **Cautionary example**: if z drops to ≈1.055 (win/loss ratio close to 1, win rate not high enough to compensate), the Kelly formula returns a fraction that leads to ruin — Kelly is highly sensitive to estimation error in `x` and `z`, and full Kelly is rarely used in practice (commonly "half-Kelly" or smaller is used as a safety margin).

### Optimal f (Ralph Vince)
- Searches for the fraction `f* ∈ [0, 1]` (step e.g. 0.01) that maximizes **TWR (Terminal Relative Wealth)** over a sequence of historical trade results — i.e. the position-sizing fraction that would have maximized compounded growth on the actual trade sequence.
- More general than Kelly (works directly off the trade-result distribution, not just win-rate/avg-win/avg-loss), but also more prone to overfitting to the specific historical sequence — should be combined with conservative scaling.

### Martingale — NOT recommended
- Double position size after every loss, reset to base size after a win.
- Author explicitly advises against this: a losing streak causes exponential position growth and ruin risk; included only for completeness.

### Anti-Martingale
- Increase position size after a win, decrease after a loss — the opposite of Martingale.
- Capped at a maximum of ~3 consecutive size-ups to avoid over-concentration after a hot streak.
- Philosophically aligned with "let winners run, cut losers small" / pyramiding logic.

### Fixed Proportional Position Sizing (Ryan Jones "Delta" method)
- Define a **delta** = capital increase required to add one more lot/unit of size.
- Worked example: starting capital $5,000, delta = $4,000 → lot size increases by 1 unit every time equity crosses the next $4,000 threshold ($5,000→1 unit, $9,000→2 units, $13,000→3 units, etc.).
- **Decline delta** can be set smaller than the growth delta (e.g. half of it) so that lot size is *reduced* faster on drawdowns than it was increased on gains — an asymmetric de-risking mechanism.
- Avoids the "all-or-nothing" jumpiness of fixed-fraction sizing at low capital while still scaling with account growth.

## Variants / Parameters
- All methods can be layered with a hard cap (e.g. never risk more than X% regardless of formula output) and with [[concepts/Performance-Metrics]]-based circuit breakers (e.g. disable a strategy if drawdown exceeds a threshold).

## Common Mistakes
- Using full Kelly with noisy/small-sample win-rate and win/loss-ratio estimates — small estimation errors can flip `f*` from "grow aggressively" to "go to zero." Always fractionalize (half-Kelly or less) or use Optimal f with a conservative cap.
- Martingale-style "double down to recover losses" — explicitly flagged as a path to ruin.
- Treating position sizing as an afterthought rather than testing it as its own parameter alongside entry/exit logic — the book treats capital management as a first-class, separately-optimized component of a [[strategies/Systematic-Strategy-Search]] strategy definition.

## Pyramiding (Adding to Winners)

Distinct from all fixed-sizing methods: **pyramiding is dynamic sizing that scales with trade progress**, not with account equity.

**Mechanism** (David Hannan / Laptop Legend):
1. Enter initial position with defined dollar risk R (e.g. $10K)
2. Trade moves in your favor → price develops a new structure (higher low for longs, lower high for shorts)
3. Tighten stop to that new structure → dollar risk at new stop is now < R
4. Add to position until dollar risk at new tighter stop = R (original)
5. Repeat → position size grows while dollar risk stays constant
6. Final position can be 10–100x initial; same R has been recycled many times

**When to add** (critical): at a "wash and reclaim" — price dips below a support level (clearing stops, improving average), then reclaims it. Add vs. the low of the wash with a tight stop. NOT on the initial break through resistance (that gives a bad average).

**Result**: $10K initial risk → $1M gain is possible with 4–5 well-timed pyramid adds on a sustained move (Bitcoin ETF example, 4 days).

**Anti-pyramid mistake**: adding aggressively on the initial breakout through resistance → bad average → stopped out on first pullback → missed the sustained move.

## Exponential Bet Sizing

**Core principle** (David Hannan / Lance Brightman): not all setups have equal EV; size should reflect EV, not be standardized.

**Framework**:
- **Normal setup** (C-tier): 1x base risk
- **Good setup** (B-tier): 2–3x base risk
- **A+ setup** (rare, high conviction): 8–20x base risk

**Poker analogy**: Pocket Aces vs. Jack-Jack — don't bet the same amount on both just because both are positive EV.

**Empirical confirmation** (David Hannan's 2024 P&L data): top 14% of trading days = 82% of annual profits. This Pareto distribution is the reason exponential sizing produces dramatically better results than uniform sizing.

**When to apply maximum sizing**:
- Mean reversion setups (first red day on parabolic): HIGH win rate = exponential sizing is "safe"
- Breakout setups: LOWER win rate → less suitable for max exponential sizing

**Why still take lower-conviction setups?**
1. Still positive EV — accumulates gains
2. Keeps trader in market flow / sharp
3. Builds P&L cushion before the big opportunities
4. Reduces psychological pressure of waiting for only 2 setups per year

**Caution**: ironic outcome — if biggest bets hit string of losses while small bets win, drawdown exceeds what equal-sizing would have produced. Mitigated by strict checklist discipline (only apply max sizing when ALL factors confirmed).

## Related Concepts
- [[concepts/Performance-Metrics]] — drawdown/Sharpe/profit-factor metrics used to evaluate the effect of a sizing method on a strategy's equity curve
- [[strategies/Systematic-Strategy-Search]] — a Strategy = Theory + concrete parameters + capital management method + risk control method
- [[analyses/Kalyan-Trading-Philosophy]] — Kalyan's existing rules (single stock <10%, SME <20% of portfolio) are a simple fixed-percentage-cap approach; could be formalized via Fixed Proportional sizing as the portfolio scales

## Gap-Risk Simulation (new, 2026-06-22)

A distinct failure mode from ordinary stop-loss sizing: **a stop-loss is intent, not a guaranteed fill**. Overnight gaps (news, earnings, broad sell-offs) can open a stock below the stop price — especially in smallcaps/illiquid names on NSE/BSE.

**Mechanism**: simulate a worse fill than the stop limit using a gap-buffer % (e.g. 5%) and slippage % (e.g. 0.5%), then compute the realistic loss in ₹ and in R-multiples if that worse fill happens — not just the "clean stop" loss assumed by standard fixed-fractional sizing.

**Why it matters**: standard position sizing (risk = entry − stop) implicitly assumes the stop fills at or near the stated price. For volatile/illiquid names this assumption can be badly wrong, understating real risk. Worth stress-testing position size against a gapped-fill scenario, not just the ideal one, before sizing up.

## ATR-Based Stops & Sizing (new, 2026-06-22)

ATR (Average True Range, default 14-period) is expressed in ₹, not %. ATR of ₹8 means the stock moves ₹8 in a typical day including gaps; ATR of ₹24 means it moves three times as much. Giving two stocks like this the same fixed-₹ or fixed-% stop distance treats them as equally volatile when they aren't — the volatile name gets stopped out by normal noise.

**Multiplier choice**:
| Multiplier | Use case |
|---|---|
| 1× ATR | Very tight — momentum entries with clear invalidation right under the entry bar |
| 1.5–2× ATR | Most common swing-trader range — wide enough to absorb normal noise, tight enough to size meaningfully |
| 2.5–3× ATR | Wide — position trades or volatile names; forces a smaller share count but avoids normal whipsaw |

**The real value of ATR isn't where to place the stop — it's that it forces correct position sizing.** Commit to "stop = 1.5× ATR below entry" and "risk ₹R per trade," and share count follows automatically: volatile stocks get smaller positions, quiet stocks get larger ones, without manual judgment calls each time.

**Chandelier stop** — an ATR-based trailing stop: `highest high since entry − N × ATR`. Steps up as new highs form, never moves down. Common defaults: 3× ATR for swing trades, 2× ATR for shorter holds. Loosens automatically in volatile names, tightens in quiet ones.

**ATR-based targets**: e.g. first target at 2× ATR, second at 4× ATR — mechanical and avoids hindsight target-setting, but ignores structural targets (prior highs, measured moves). A hybrid — "target the lower of 3× ATR or the prior swing high" — tends to outperform either pure approach.

**Pitfalls**: ATR jumps after a gap (refresh sizing before reloading a position post-gap); very illiquid stocks show artificially low ATR (no trades = no range — don't size up on micro-caps just because ATR looks small); ATR says nothing about direction, only typical movement size.

## Trailing-Exit Systems (new, 2026-06-22)

A trailing stop is a pre-defined rule for moving the stop forward as price advances — never backward. Define the trail *before* entry and follow it; mid-trade tightening out of nervousness is "the trade managing you," not the reverse.

| System | Mechanism | Character |
|---|---|---|
| Structural (swing-low) | Stop moves to just below the most recent swing low after each new swing high | Loose enough to ride trends; requires subjective swing-point recognition |
| 20 EMA trail | Exit on daily close below the 20 EMA | Tightest — good for fast momentum trades, exits on most normal pullbacks |
| 50 EMA trail | Exit on daily close below the 50 EMA | Medium — standard for intermediate swings, survives 5–10% pullbacks |
| 21 EMA on weekly | Exit on weekly close below | Loosest — survives normal swing-to-swing pullbacks, exits only on real trend changes |
| ATR/Chandelier | `highest high − 3×ATR` (see above) | Mechanical, volatility-adjusted — the math decides, no manual debate |
| Parabolic SAR | Dots step up as price runs | Works in clean trends (ADX > 25); fails badly in chop, flips constantly |
| Supertrend (10, 3) | ATR-based trail with a flip-on-cross | Smoother than parabolic SAR but still whips in chop |

Close-based trails (exit on daily close through the level) are far less whippy than touch-based trails (exit on any intraday wick through).

**Partial profits / scaling out**: trailing the entire position is psychologically hard. Common compromise — take partials at a defined R-multiple or structural target (e.g. 2R, or the prior swing high), then trail the remainder. Example ladder: 1/3 at 2R, 1/3 at 4R, trail the final 1/3. Locks in some gain, reduces the pain of giving back open profit, at the cost of capping maximum reward.

**Time stops**: if the thesis was "resolution within two weeks" and three weeks pass with no movement, the opportunity cost is real even without a stop hit. Mechanical and unpopular precisely because they force admitting a timing error rather than a directional one — but they free capital for better setups.

**Common mistakes**: moving a stop backward (only allowed direction is forward); mixing multiple trail systems mid-trade (pick one — structural, MA, or ATR — and stay consistent); mismatching trail timeframe to entry timeframe (a daily-setup trade managed on a 5-min trail gets whipsawed for no reason).

## The Five-Line Trade Plan & R-Multiple Discipline (new, 2026-06-22)

A complete trade plan answers four questions *before* capital is exposed — where is entry, where is the idea wrong, how much account risk is allowed, what causes profit-taking or exit:

1. **Setup** — what pattern/scanner context surfaced the stock, and why is it interesting now?
2. **Entry trigger** — the exact condition that activates the trade (breakout close, retest hold, reclaim, planned pullback).
3. **Invalidation** — the chart condition that proves the idea wrong, not just a convenient ₹ loss figure.
4. **Position size** — shares = account risk ÷ per-share risk.
5. **Management** — where you reduce, trail, hold, or exit if the trade does nothing.

**Why think in R, not raw %**: a 5% move can be huge or mediocre depending on the risk taken to earn it. If initial risk was 2%, a 5% move is ~2.5R before costs; if the stop was 8% away, the same 5% move is under 1R. R-multiple thinking also makes cross-stock review honest — a volatile pharma name, a bank stock, and a smallcap momentum leader can't be compared by raw ₹ or %, but they can be compared by whether each trade risked 1R and produced/lost/protected some multiple of that R.

**Common plan failures**: moving the stop lower after entry because the chart "still looks interesting"; taking full profits too early then re-entering higher out of FOMO; using the same share quantity for every stock regardless of differing stop distance/volatility; skipping the plan entirely for the strongest-looking chart — exactly where emotion runs highest.

**Template**: *"I am interested because ___. I enter if ___. I am wrong below ___. I risk __R or ₹___. First management decision happens at ___."* If any blank is hard to fill, the setup isn't ready.

## Reference Defaults (SwingEdge Position Sizing Calculator, 2026-06-22)
A concrete, named fixed-fractional implementation worth comparing against the methods above:
- Default risk per trade: **0.5%** of capital (allowed range 0.1%–5%); guidance to drop to 0.25% "in uncertain or bearish environments"
- Default max allocation per trade: **20%** of capital — a hard concentration cap independent of the risk-per-trade calc
- 6 exit-style templates selectable at entry: Fixed R:R (50% at +2R, trail rest), Partial at +1R, Trailing ATR (1.5x ATR below highs), Swing low trail, EMA trail (below 20 EMA), and a **Pyramid mode** (adds only after +1R) — directly analogous to the wash-and-reclaim pyramiding mechanism documented above from David Hannan's interview.
- See [[sources/SwingEdge-Position-Sizing-Tool]] for full detail.

## Trade from stability, not scarcity — and the streak maths (2026-08-29)

From [[sources/YT-Pro-Trader-Amygdala-Options-Philosophy]]. The sizing argument that
sits *underneath* every method on this page:

> "Most traders trade like they've got everything to lose, because they do. Everything
> hinges on that next trade working out."

**The claim, checked exactly.** *"You could have a 55% win rate and still lose seven trades
in a row."* Computed as a Bernoulli run probability:

| win rate | P(≥7 consecutive losses) in 100 trades | in 200 | in 500 |
|---|---|---|---|
| 55% | 17.9% | **33.4%** | 64.4% |
| 60% | 8.9% | 17.5% | 38.7% |
| 65% | 3.9% | 7.8% | 18.7% |

A genuinely profitable 55%-win-rate trader taking ~200 trades a year has a **one-in-three
chance of a seven-loss streak in any given year**, and better-than-even odds across two and
a half years. This is not rhetoric — it is the arithmetic of variance, and it is the whole
argument for the **0.5% risk-per-trade default** recorded above. Size so that the streak
that *will* arrive is an inconvenience rather than an ending.

**The financial-position argument.** *"Trading is what's going to make me wealthy; it's not
what's going to make me rich in the here and now."* The source describes his most stressful
years as the ones spent 100% reliant on trading income — hoarding cash, unable to commit to
a rent cheque, with no working sense of personal finance. Childhood conditioning around
**resources** (parents arguing about money) installs a scarcity setting that reappears as
loss aversion at the screen; see [[concepts/Trading-Neurobehavioral-Loop]].

Traders who built everything from nothing are *"exceptions to the rule, and yet everyone
thinks they're going to be the next exception."*

## Examples in This Wiki
- None yet implemented in code — candidate addition to position-sizing logic in `tools/nse_wave_scanner.py` if/when automated sizing is added.

## Sources
- [[sources/Dolzhenko-Algorithmic-Trading-Systems-2024]] (2026-06-15)
- [[sources/YT-David-Hannan-Laptop-Legend]] (2026-06-18) — pyramiding (wash-and-reclaim add technique); exponential bet sizing; Pareto P&L distribution (14% of days = 82% of profits)
- [[sources/SwingEdge-Position-Sizing-Tool]] (2026-06-22) — fixed-fractional calculator defaults (0.5% risk / 20% allocation cap), gap-risk simulation, R-multiple exit-style templates
- [[sources/SwingEdge-Learn-Process-Risk-Workflow]] (2026-06-22) — ATR-based stops/chandelier/Supertrend, trailing-exit system comparison table, five-line trade plan template, R-multiple review discipline
