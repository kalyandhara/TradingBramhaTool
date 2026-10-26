---
title: "Web App — eVector: every event as a vector in the market"
category: source
tags: [source, web-app, events, momentum-state, chart-narrative, design, forecasting-record, us-markets]
created: 2026-10-26
updated: 2026-10-26
sources: 1
related: [analyses/Policy-Event-Study-Result, analyses/Home-Terminal-Layout-Spec, analyses/Open-Backlog, sources/Design-Resources-For-Developers]
---

# Web App — eVector: every event as a vector in the market

## Metadata

- **Site:** https://evector.io. Read 2026-10-26: the public home page and `/markets/TSLA`.
- **What it is:** a US-market research app. It is free at the top and has a waitlisted "Research Desk" at $19.99/month (full event map, full picks list, an AI analyst, state-change alerts, and MCP access for your own AI).
- **How it was read:**
  - Page text, screenshots, and a passive read of the public JavaScript bundle (UI strings and client-side detector logic only; no API calls, nothing behind the login).
  - The REA reverse-engineering MCP needs a local Chrome DevTools endpoint, which this session does not have, so the bundle was read through the in-app browser instead.
- **Bias:** neutral. It describes itself as "how prices behave around events … not investment advice".

## Key takeaways

1. **The day as a map of events.** About 10–15 events each morning (macro, geopolitics, earnings, energy, technology…). Each has an impact grade (High/Medium/Low), a "running since" date, and the stocks or ETFs it should touch. It also shows what those prices *actually* did since the news.
2. **Measured vs hypothesis links.** In the event graph, solid edges are measured and dashed edges are hypotheses. The UI copy reads "A hypothesis until <date>. The reaction is measured from the close before the event." There are also second-order links.
3. **A seven-state momentum lifecycle with plain-English glosses**, used on every tile, sector, theme and stock:

| State | Gloss | Colour token |
|---|---|---|
| Neutral | No active trend | `--st-neutral` |
| Ignition | Just broke out | `--st-ignition` |
| Acceleration | Speeding up | `--st-acceleration` |
| Expansion | Trend holding | `--st-expansion` |
| Healthy Pullback | Resting, trend intact | `--st-pullback` |
| Weakening | Losing steam | `--st-weakening` |
| Breakdown | Trend broken | `--st-breakdown` |

   Each state also carries a "Momentum N/100" score and a short reason, e.g. "Momentum is broadening but has not yet met the minimum sequence length for Expansion" and "Early evidence present; persistence not yet established". The market map sizes tiles by whether they are in an active trend (Ignition, Acceleration or Expansion).
4. **A context ladder on every stock page.** Tiles for Market (QQQ, SPY), Sector (XLY), Industry (CARZ) and Themes (ARKQ, BOTZ, DRIV). Each shows a trend word (Uptrend/Downtrend/Sideways: "price against its 20-day average, and that average's slope"), day % and 1-month %, plus "+ Compare" to overlay it on the chart. The stock also gets "vs sector, 20d".
5. **"Tour this chart": a narrated chart.** Client-side detectors each emit a weighted plain-English sentence plus chart actions (draw the level, highlight the candle, switch on indicators). The bundle shows these detectors:
   - breakout over an N-session closing high, with volume ×;
   - failed breakout ("closed back below");
   - a breakdown under the 55-day low, and a failed breakdown;
   - volume expansion (last 5 sessions ≥ 1.5× the 50 before);
   - volatility expansion (ATR ≥ 1.4× two months ago);
   - a squeeze (Bollinger width narrowest in 6 months);
   - bullish and bearish divergence, gap up and gap down;
   - trend turned up or down (crosses), and above or below the 200-day average.
6. **Event markers on the chart.** E (earnings), N (news), M (macro), R (regulation), AI, and ⚡ "detected anomaly", which means found in price and volume. A catalyst is "found in the price, explained from the news". You can step through them with `[` `]`. The agent's prompt chips include "Why did TSLA move here?", "**Was it TSLA or the whole market?**" and "What changed after <date>?"
7. **Calls graded by the market ("Make the call. The market will grade it.").** "Will software be higher or lower 5 sessions from now?" A call is final once made and resolves from closing prices, and each user gets a "My record". It is a public forecasting scorecard.

Other features: a "Who's leading the market" panel built from prices alone (industries crowding the top of the ranking, sector breakouts, retail-chatter names); "Today's system picks" (#1 of 5,619 screened, score 77, state Expansion, vs S&P 20 sessions); a "Your stocks" view where you pick a stock and today's events gather around it; and a rate-cycle panel ("If the Fed surprises with a hike…").

## Design and presentation notes (owner likes these)

- **Look.** Warm off-white canvas, a large serif display face for headlines ("Every event creates a vector in the market."), a small all-caps eyebrow above each section, and generous whitespace.
- **One idea per section,** each a plain question: "What's moving the world today", "Who's leading the market", "What happens next?"
- **Signature visual:** a 3-D axis with one vector arrow (direction plus magnitude) and floating glass cards.
- **Writing style:**
  - Every number has a unit and a window ("+26.2% · 20 sessions", "since Oct 22").
  - Every state has a one-line plain gloss.
  - Disclaimers are short and honest.
- **Colour.** Colour tokens per state and per category (`--cat-macro`, `--cat-energy`…), with directional `--up`, `--down` and `--flat`; dark mode via a theme toggle.
- **Chart page:**
  - Dense but calm.
  - A context-tile strip above the chart.
  - The chart on the left, the agent and event list on the right.
  - Keyboard shortcuts listed under the chart (←/→ pan, 1–7 timeframe, [ ] events, F full screen).

## Actionable insights (ranked for this desk)

1. **The momentum lifecycle state as a desk vocabulary.** It names where a move is in its life, which directly encodes the "current + forward-looking" view. The desk today has scanner hits and an RRG quadrant, but no single per-name/per-sector *state*. It has to be measured before it is trusted: do the transitions (e.g. Ignition → Expansion vs Ignition → Breakdown) carry forward returns? That needs a pre-registered study.
2. **"Tour this chart" narration.** Turn the existing indicator and scanner overlays into ranked plain-English findings that drive the chart (draw the level, highlight the candle). This fits the beginner-readable direction (B-148–B-157 Indicator Browser v2) and the Stock Analyzer. The desk has already measured several of the same detectors (failed breakout B-182, squeeze/coil B-101, divergence), so each sentence can carry its own measured base rate. eVector does not do that.
3. **A context ladder with "was it the stock or the market?"** Market → sector → industry → theme tiles with trend words, plus an attribution line (stock move vs sector vs NIFTY). The Sector Lobby and peers table hold most of the pieces; this is mostly a presentation layer on the Stock Analyzer.
4. **Event markers on the chart, plus measured-vs-hypothesis event links.** B-184 just built the measurement half (`event_study.py`: the reaction measured from the close before the event). Plotting RBI and Budget days, earnings, block deals and corporate announcements as E/N/M/⚡ markers is the visual half. The "hypothesis until measured" edge wording fits the desk's pre-registration habit well.
5. **Calls graded by the market.** This is the same idea as rec_audit (recommendations scored by later prices), but run forward and personal: "My record". A 5-session up/down call on a sector or name, final once made and resolved from closes, would give the owner a calibration score on their own reads.

## Contradictions / cautions vs the wiki

- **Nothing is measured publicly.** eVector shows no base rates for its states, picks or event arrows, and the "momentum engine" thresholds are not disclosed. Per [[analyses/Policy-Event-Study-Result]], our own MPC "events" turned out to be ordinary days, so a link only counts as measured once something like `event_study.py` has measured it.
- **The detectors are classic TA.** Squeeze, failed breakout and divergence are textbook detectors; on this desk, failed breakouts did not warn (B-182) and the coil carried no edge (B-101). Adopt the presentation, not an implied edge.
- **It covers US markets only.** Every ETF in the ladder needs an NSE equivalent: NIFTY/NIFTY 500, the sector indices, and thematic indices (Nifty India Defence, Nifty EV & New Age Automotive, Nifty CPSE, Railways PSU…). All of these exist in NSE's all-indices file.

## Pages updated

- [[analyses/Open-Backlog]]: B-185 to B-189 filed (eVector adoption candidates)
- `index.md`, `log.md`
