---
title: "Guidebook — Trading Stocks and Options with Moving Averages: A Quantified Approach"
category: source
tags: [book, connors, mean-reversion, moving-average, connors-rsi, options]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [strategies/Quantified-MA-Mean-Reversion.md, concepts/ConnorsRSI.md, concepts/RSI.md, concepts/EMA.md]
---

# Guidebook — Trading Stocks and Options with Moving Averages: A Quantified Approach

## Metadata
- Authors: Larry Connors, Matt Radtke (Connors Research Trading Strategy Series)
- Publisher: Connors Research, 2013
- Format: PDF, 40 pages, extracted via `py -3` + pdfplumber to `C:\Users\dhara\AppData\Local\Temp\connors_ma_book.txt` (all 40 pages read in full)
- Date ingested: 2026-06-15

## Key Takeaways
- Core thesis: classic trend-following moving-average crossovers are largely ineffective; the book instead presents a **dual-MA mean-reversion** system where divergence *between* a fast and slow MA (fast MA dropping well below slow MA, in an overall uptrend) is the signal — see new strategy [[strategies/Quantified-MA-Mean-Reversion]].
- Introduces **ConnorsRSI(3,2,100)**, a composite oscillator (RSI(Close,3) + RSI(Streak,2) + PercentRank(ROC(1),100), averaged) used as an exit trigger — new concept page [[concepts/ConnorsRSI]].
- Full Setup → Entry → Exit specification with 5 MA-pair scenarios (5/10, 5/20, 5/50, 10/20, 10/50), 4 "MA Stretch" (Y%) values, 5 "Limit%" (X%) values, and 5 exit methods — over 100 systematically backtested parameter combinations (Jan 2001 - Sept 2013).
- **Significant finding flagged as a contradiction below**: the book's own testing found that adding a stop-loss to this system tends to *reduce or eliminate* its statistical edge.
- A complete "Using Options" section describes substituting a front-month ITM long call for the stock position (1 contract per 100 shares, same exit signal, rationale for ITM over OTM/ATM due to delta ~1).
- Historical Volatility HV(100) > 30 is used as a volatility pre-filter — a worked numeric HV calculation example is given in the Appendix alongside the ConnorsRSI derivation.

## Detailed Notes

### Section 1 — Introduction
Critiques simple MA crossover/trend-following systems as having weak, inconsistent historical edges. Proposes instead that the *relationship* between two MAs (fast vs. slow, measured as a % divergence) on stocks already in a long-term uptrend (Close > MA(200)) is a more robust mean-reversion signal.

### Section 2 — Strategy Rules
Full Setup/Entry/Exit specification — captured in [[strategies/Quantified-MA-Mean-Reversion]]. Two worked trade examples (SWHC and SPRD) walk through the Percent Below / Limit Price / Profit formulas end-to-end.

### Section 3 — Test Results
Defines "Average % P/L" (the per-trade edge) and "Win Rate" as the two headline statistics, with "Avg Days Held" as a secondary descriptor. Presents Top-20-by-Average-Gain and Top-20-by-Win-Rate tables across all tested MA-scenario / Y% / X% / exit-method combinations, Jan 2001 - Sept 2013.

### Section 4 — Selecting Strategy Parameters
General principles for tuning: stricter Setup/Entry criteria (higher MA Stretch %, higher Limit %) → fewer trades but higher average gain; stricter Exit criteria (ConnorsRSI>70 or Close>MA(5) vs. First Up Close) → longer average hold and higher average gain per trade, but lower win rate and trade frequency. Three sensitivity tables isolate the effect of MA Stretch, Limit%, and Exit method independently.

### Section 5 — Using Options
Front-month, 1-2-strikes ITM long call as a stock substitute. Sizing: 1 contract per 100 shares. Same exit signal as the stock version applies to the option. Liquidity/spread screening guidance, and rolling to the next front month if held into expiration week. Rationale: ITM delta near 1 minimizes time-decay drag over the strategy's short (typically <10 day) holding periods while reducing capital outlay vs. owning shares outright.

### Section 6 — Additional Thoughts
Notes that "hundreds of variations" of this strategy can be built by combining the MA scenarios, Y%, X%, and exit methods (125+ combinations from the core parameters alone) — readers are encouraged to test combinations relevant to their own watchlists. Also states the **stop-loss finding** (see Contradictions below).

### Appendix
- Full derivation of ConnorsRSI(3,2,100), including a worked streak-duration table (showing how consecutive up/down day counts feed RSI(Streak,2)) and a worked PercentRank(ROC(1),100) example.
- Worked numeric example of Historical Volatility (HV) calculation, supporting the HV(100)>30 setup filter.

### Pages 37-40 (not extracted)
Promotional material for other Connors Research guidebooks (Bollinger Bands strategies, ETF Gap Trading, Long Pullbacks / "5x5x5" strategy) — noted only as potential future sources, not extracted.

## Actionable Insights
- [[strategies/Quantified-MA-Mean-Reversion]] is a fully quantified, parameter-swept mean-reversion system that could be backtested on Indian large/mid-cap names with sufficient liquidity (avg volume, HV(100)) — distinct in philosophy from the trend-following MA pullback approach already in [[concepts/EMA]] / [[strategies/EMA-Pullback]].
- [[concepts/ConnorsRSI]] is a ready-made composite oscillator that could be added as an additional exit filter alongside existing exit logic in [[strategies/PMax-Confluence-Strategy]] or [[strategies/TechnoFunda-Swing]].
- The 125+ parameter-combination backtest table is a concrete example of the coarse-to-fine optimization process described abstractly in [[strategies/Systematic-Strategy-Search]] — could serve as a template for organizing future parameter sweeps.
- The ITM-call stock-substitution rules (Section 5) are the wiki's first documented options-trading technique; could be generalized to other mean-reversion or swing strategies where capital efficiency matters.

## Contradictions with Existing Wiki
- **Stops reduce/remove edge vs. existing stop-centric risk management.** This book's Section 6 explicitly states that adding a stop-loss to the Quantified MA Mean-Reversion system tended to *lessen performance and in many cases completely remove the strategy's edge* in backtesting — the published system relies on no stop-loss, only the time/indicator-based exits (First Up Close, ConnorsRSI thresholds, MA(3)/MA(5) reclaim).
  - This is in direct tension with [[analyses/Kalyan-Trading-Philosophy]] and [[analyses/VCPBot-Risk-System]], both of which treat a hard stop-loss as a non-negotiable risk-control element, and with [[sources/Dolzhenko-Algorithmic-Trading-Systems-2024]]'s risk-control chapter (Maximum Loss Amount sizing assumes a defined stop).
  - **Both views can be correct in context**: a tight, well-defined mean-reversion system with strict setup filters (Close>MA(200), HV(100)>30, no-stop exits all indicator/time-based) may have a bounded worst-case loss by construction — the "stop hurts edge" finding may reflect that stops convert normal noise/drawdown *within* the expected reversion window into forced losses. Whereas for trend-following/breakout systems (VCP, TechnoFunda-Swing) without a similarly bounded adverse-excursion profile, a hard stop remains essential.
  - **Flagged, not resolved** — if [[strategies/Quantified-MA-Mean-Reversion]] is ever implemented, this tension should be tested directly (with vs. without stop) before deciding whether to override Kalyan's general "always use a stop" rule for this specific system.

## Pages Updated
- Created: wiki/sources/Connors-MA-Quantified-Approach-2013.md (this page)
- Created: wiki/strategies/Quantified-MA-Mean-Reversion.md
- Created: wiki/concepts/ConnorsRSI.md
- Updated: wiki/concepts/RSI.md (cross-link to ConnorsRSI)
- Updated: wiki/index.md, wiki/log.md
