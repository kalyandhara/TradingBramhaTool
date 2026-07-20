---
title: "Humbled Trader — Trend Join Long (US Cash Pre-Market Gapper)"
category: strategy
tags: [humbled-trader, day-trade, premarket, gap-up, rvol, us-equity, trend-join, r-multiple]
timeframe: intraday
created: 2026-07-08
updated: 2026-07-08
sources: 1
related: [sources/PreMarketTool-repo, concepts/VWAP, concepts/EMA]
---

# Humbled Trader — Trend Join Long (US Cash Pre-Market Gapper)

## Core Idea
Long the **gap-up continuation on a large-cap US name** where premarket flow already confirmed real participation (RVOL > 1.5) and price has broken above the prior day's high. Wait for the *regular session* to confirm the pre-market strength (break of PMH + HOD), risk to a defined level below the pre-market high, and pyramid out on R-multiples with a 21-EMA trail on the final third. **Flat by 15:51 ET** — no overnight, no bagholding.

This is the validated day-trade template distilled from the Humbled Trader curriculum and embedded as the "day scan" side of the [[sources/PreMarketTool-repo]] pipeline. The name means what it says: *join the trend that's already there* — not predict, not bottom-fish, not fade. If pre-market has done the work, ride the continuation.

## Setup Criteria — Pre-Market Filters
All six must be satisfied for a name to make the day watchlist:

| # | Filter | Threshold | Why it matters |
|---|--------|-----------|----------------|
| 1 | Gap % vs prior close | **> 3%** | Below this, the "gap" is noise, not a regime |
| 2 | Price | **> $3** | Penny-stock microstructure is a different game |
| 3 | Market cap | **> $1B** | Large-cap = tighter spread, no easy manipulation |
| 4 | Pre-market relative volume | **> 1.5** | Confirms actual participation, not headline noise |
| 5 | Price breaking above prior HOD | **Yes** | Structural — up-only setups only |
| 6 | Catalyst | **Identified** | `catalyst_found:false` = auto-SKIP (see [[sources/PreMarketTool-repo]] prompt guardrails) |

If any of the first five fails, the scanner drops the name. If catalyst is missing but the price setup passes, the Codex prompt in the repo is instructed to downgrade to skip anyway — no thesis is built around an unexplained gap.

## Entry Rules
1. **Time window opens 10:00 ET.** Do not take signals in the opening 30-minute chop. Wait for the auction to settle.
2. **Trigger:** price makes a new high **above the pre-market high (PMH) AND above the prior high of day (HOD)**. Both must be broken; either alone is not enough.
3. Enter on the break with a stop-order at the trigger level, OR a limit-order at PMH-as-support after the trigger prints. Repo default is stop-order semantics.
4. **The 30-minute buffer at open is doing real work** — the same "avoid the news-driven vertical spike at the level" pattern that appears in [[strategies/Koroush-Breakout-Momentum]] as Filter 1. Both strategies reject fast-spike entries into the level; they want the level *earned* over multiple candles.

## Exit Rules

### Stop loss (1R)
- Stop = **1% below the PMH**, OR the intraday LOD (Low of Day) — whichever is **lower**.
- This distance is your 1R.
- If the LOD is more than 1% below PMH, you get a wider stop; if PMH itself is the lower level, you get the tighter 1% floor. Either way, one number defines 1R.

### Scale-out ladder
- **+1R:** exit ⅓
- **+2R:** exit another ⅓
- **Last ⅓:** trail on the **21-EMA** on the trading timeframe

### Hard time exit
- **15:51 ET (9 minutes before close).** Flat by 15:51 no matter what — no exceptions, no overnight, no "let it run into the close" heroics. The exit is *mechanical, not discretionary*.

## Timeframe
- **Execution:** intraday. Repo default is agnostic on the exact chart, but the 21-EMA trail and PMH/HOD structural levels suggest 1m–5m.
- **Trade window:** 10:00–15:30 ET; hard exit at 15:51 ET.
- **Asset class:** US large-cap cash equity. Does *not* apply to crypto (different microstructure, no premarket concept), Indian equity (different session times / no comparable PMH structure), or options.

## Best Market Conditions
- **Trending market on the daily.** Gap-up continuations follow through best when the broader tape has bias.
- **Real earnings/M&A/FDA/index-inclusion catalyst** on the name. The [[sources/PreMarketTool-repo]] prompt file orders catalyst types explicitly: earnings/guidance > M&A > FDA > index inclusion > sympathy > analyst upgrade > none. Higher up the ladder = higher conviction.
- **RVOL > 1.5 and rising** — flat RVOL after the pre-market print is a warning that participation was one-shot.
- **VWAP-side confluence** (see [[concepts/VWAP]]): if the session VWAP slope is steep and bands are widening on the pane, that agrees with the trend-join thesis.

## Worst Market Conditions
- **Choppy / range-bound daily tape.** Gap-ups that fail immediately are more common when the index itself is going nowhere.
- **"Up on bad news" traps.** The Claude prompt in the repo flags this explicitly: dilution announcement, SEC probe, earnings miss, guidance cut — if the gap is *up* despite bad news, treat as TRAP, not opportunity. The market will usually fade these into the session.
- **Pre-market vertical spike into the trigger** (as opposed to a graduated build). Same failure mode as Koroush's Filter 1 rejection — the fast-spike-then-fade pattern.
- **Missing or thin catalyst.** `catalyst_found: false` = mandatory skip. No exceptions.

## Backtest / Track Record
- **54.6% win rate**
- **Profit factor 1.59**
- **280 trades** in the backtest sample

Source: `WATCHLIST_CRITERIA.md` in [[sources/PreMarketTool-repo]]. Timeframe of the sample, exact universe, and slippage assumptions are not documented in the repo — flagged as a known gap; if you want to rely on the numbers for sizing decisions, re-run the backtest against the current universe with realistic transaction costs.

## Examples
No specific trade examples are yet in the wiki. The Pree Market Tool produces one `reports/premarket_YYYY-MM-DD.html` per session (sample on disk: `reports/premarket_2026-07-04.html`) — each report's Day Trading Watchlist table is a live example of the setup applied to that day's tape. As sessions accumulate, notable wins/losses can be filed as `analyses/HT-TrendJoin-YYYY-MM-DD-TICKER.md` post-mortems.

## Related Concepts
- [[concepts/VWAP]] — session VWAP is a compatible confluence check on the entry day. If VWAP slope agrees with the trend-join thesis (steep, widening bands, price > VWAP), conviction is higher.
- [[concepts/EMA]] — the 21-EMA trail on the last ⅓ is standard EMA-trailing exit logic.
- [[strategies/Koroush-Breakout-Momentum]] — a crypto 1-minute analogue with the same "reject fast-spike approaches, prefer earned levels" philosophy. Different asset class, same structural principle.

## Contradictions with Existing Wiki
- **Asset class scope.** Rules are US large-cap cash equity only. Do NOT port the 1% PMH stop, PMH+HOD trigger, or 15:51 ET time-flat to Indian equity swings (different session, different structural levels) or crypto 1m (different microstructure) without independent re-testing.
- **"15:51 ET flat, no overnight"** contradicts the Indian-equity swing strategies on this wiki ([[strategies/Minervini-SEPA]], [[strategies/TechnoFunda-Swing]], VCP scanners) which explicitly hold multi-day / multi-week. Not a contradiction so much as *scope* — these are day-trades on a different market, not a competing swing philosophy.

## Sources
- [[sources/PreMarketTool-repo]] — the Pree Market Tool repo where these rules are canonicalised (`WATCHLIST_CRITERIA.md`, `AGENTS.md`, and the two AI-brain prompt files enforce the rule set inside the pipeline).
