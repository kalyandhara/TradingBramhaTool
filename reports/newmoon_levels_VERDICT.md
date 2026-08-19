# New-Moon Levels Backtest — Verdict (2026-08-18)

**Question:** are new-moon-day highs/lows better support/resistance than an ordinary
adjacent trading day's highs/lows? (The wiki flagged this as the make-or-break test:
the null MUST be a prior-day extreme, not a random price, because any recent extreme
acts as some S/R.)

**Answer: No. Clean null. New-moon levels are ordinary S/R.**

Pipeline: `tools/newmoon_levels_backtest.py`. Treatment = new-moon trading day H & L;
control = the immediately-preceding trading day's H & L (matched by H/L type). Metric =
first-touch rejection rate (did the level hold?). Null = paired permutation swapping the
lunar/ordinary label within each (event, H/L) pair, 5,000x. Look-ahead-free.

| Run (2007-09 .. 2026-08) | lift range | p range |
|---|---|---|
| ^NSEI, new-moon | 0.94–1.05x | 0.13–0.87 |
| ^NSEI, full-moon (Purnima) | 0.95–1.06x | 0.10–0.84 |
| ^NSEBANK, new-moon | 1.00–1.06x | 0.12–0.52 |

Grid: eps ∈ {0.15, 0.25, 0.50}% × horizon ∈ {3, 5, 10} days. ~445 matched level-pairs
per config. Pre-registered pass bar: **lift ≥ 1.15 AND p < 0.01, robust across eps/horizon.**
Nothing clears it in any of the 27 cells.

Key observations:
- Both new-moon AND prior-day extremes reject ≈ 49–56% of first touches — essentially a
  coin flip. A horizontal line at *any* recent extreme "holds about half the time".
- That ~50% is exactly the base-rate S/R behaviour that makes the method *feel* like it
  works. The lunar framing adds **nothing** over an ordinary adjacent day.
- Full-moon behaves identically to new-moon. Bank NIFTY behaves like NIFTY.

**Honest stop:** the prior-day-extreme control is the whole point — against a random-price
null the method would have looked "good" purely from generic S/R. Controlled properly, the
lunar edge vanishes. Prior retired with evidence.

Tests S/R reaction only; direction and PnL were not modelled. Educational, not investment
advice.

Reproduce:
```
py -3 tools/newmoon_levels_backtest.py
py -3 tools/newmoon_levels_backtest.py --phase full
py -3 tools/newmoon_levels_backtest.py --symbol ^NSEBANK
```
