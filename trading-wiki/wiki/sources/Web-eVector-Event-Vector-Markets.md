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
  - Page text, screenshots and a passive read of the public JavaScript bundle (UI strings and client-side detector logic).
  - Then a full REA pass over a local Chrome DevTools endpoint (see "REA pass" below): the bundle graph, public logged-out endpoint *shapes* (field names, not data), the server-rendered data model and the exact detector thresholds.
  - Nothing behind the login was touched.
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

## REA pass (2026-10-26): how it is built

Method:
- REA attached over CDP to a throwaway Chrome (`127.0.0.1:9222`, separate profile).
- `analyze_web_bundle` covered 18 scripts and 487,828 AST nodes (the parsed-code count), with 0 parse failures.
- The network log came from the logged-out `/markets/TSLA` page.
- The server-rendered payload was read as field names, counts and enum values only.
- REA's `capture_browser_scenario` failed in this environment ("provider is closing") in both connect and launch modes; the passive tools worked.

**Stack.** Next.js (Turbopack) and React. Pages are server-rendered with React Server Components, so the day's events, graph and states arrive inside the HTML (~113 KB of payload on the home page), not from an API. The 737 KB chunk is WebGL/three.js and draws the 3-D vector hero.

**Public endpoints (logged out).**

| Endpoint | Shape |
|---|---|
| `GET /api/markets/bars?symbols=…&days=60` | `{bars: {SYM: [{time, open, high, low, close, volume}…]}, live}`, ~41 sessions for 60 days |
| `GET /api/consensus?ids=q-…` | `{consensus: {id: {questionId, counts{option:n}, total, threshold, revealed, history[{at,label,shares}]}}, votes, voteCount, signedIn}` |
| `GET /api/markets/watchlist` | `{signedIn, symbols}` |
| `GET /api/logo/<SYM>` | logo image |
| `POST /api/track`, `GET /api/me`, `/api/session`, `/api/seen`, `/api/predict`, `/api/signout` | analytics, session and casting a call |

**The crowd is hidden until a threshold.** `revealed` stays false until `total` passes `threshold`, so you make your call before you see anyone else's. That is a deliberate anti-herding device.

**Data model of an event chain** (one record per node; ~158 nodes on the home page):

`{id, kind (event|macro|sector|theme|stock|asset_class|crypto|basket_return|categorical), label, symbol, parent, depth, secondOrder, expectedDirection, direction, strength (Mild|Moderate|Strong|Expected), evidence (observed|hypothesis), measured, measurement, momentum, rationale, questionId}`

- `measurement` = `{asOf, price, change, excess, z, windowLabel ("20 sessions" | "since Oct 22")}`. Each link is scored by its move in excess of the market (`excess`) and that move scaled by the asset's own volatility (`z`).
- An event has `occurredOn`, `impact`, `reaction`, `scenarios`, and `odds` for rate decisions (cut50/cut25/hold/hike). A question has `opensOn`, `resolvesOn` and `metricLabel`.

**The momentum state machine** (per node: `momentum = {state, stateLabel, previousState, stateDuration, score 0–100, leadership 0–100, reasonCode, transitionReason}`). Reason codes seen:

| reasonCode | transitionReason (verbatim) |
|---|---|
| IGNITION_HOLDING | Early evidence present; persistence not yet established. |
| ACCEL_HOLDING | Momentum is broadening but has not yet met the minimum sequence length for Expansion. |
| EXPANSION_HOLDING | Repeated confirmation continues; no controlled retracement and no deterioration. |
| PULLBACK_HOLDING | Retracement remains controlled and the momentum structure is intact. |
| WEAKENING_REPAIRED | Evidence repairs through renewed price discovery and efficient demand. |
| BREAKDOWN_HOLDING | The prior momentum structure remains invalidated. |
| NO_PROCESS | No qualifying momentum evidence. |

The thresholds and the rules for moving between states are computed on the server and are **not** in the bundle; only the outputs are visible. The design itself is the lesson: a named state, how long it has held, the state before it, and a coded reason for the latest transition.

**The "Tour this chart" detectors** (client-side, exact; they need ≥ 80 daily bars):

| Finding | Rule | Weight |
|---|---|---|
| Breakout / failed breakout | in the last 15 bars, a close crosses above the prior 55-session closing high; **failed** if any later close is < 0.98 × the level | 0.7 + recency/50 + min(0.2, (RVOL−1)/5), where RVOL = volume ÷ the 20-bar average |
| Breakdown / failed breakdown | mirror image: under the 55-session closing low; failed if a later close is > 1.02 × the level | same |
| Volume expansion | average volume of the last 5 bars ÷ the 50 bars before ≥ 1.5 | min(0.85, 0.4 + (x−1.5)/3) |
| Volatility expansion | Wilder ATR(14) now ÷ ATR 42 bars ago ≥ 1.4 | min(0.8, 0.4 + (x−1.4)/2) |
| Squeeze | Bollinger(20, 2) width ÷ mid ≤ 1.05 × its minimum over 126 bars | 0.65 |
| Bearish / bullish divergence | the last two 5-bar swing highs (lows) within 40 bars make a higher high (lower low) while RSI is more than 4 points lower (higher) | 0.7 |
| Gap up / down | within the last 10 bars, \|open ÷ prior close − 1\| ≥ 3 % and still **unfilled** | 0.6 + min(0.2, \|gap\|) |
| Crosses, 200-day average | named in the UI strings (outside the captured slice) | — |

The tour also always opens with a **"now" step**: the 63-bar high-low range and the distance from each end, the momentum state and score, RVOL, and support/resistance lines. A **context step** says whether the stock is ahead of, in line with, or behind its ladder peers, using a ±5 % band, and overlays them with `COMPARE`.

Each finding drives the chart through a small action language: `CLEAR`, `ZOOM_TO_RANGE`, `PRICE_LEVEL{price,label,tone}`, `HIGHLIGHT_CANDLE`, `HIGHLIGHT_RANGE`, `INDICATORS{ids}`, `COMPARE{symbols}`, `CONTEXT`, `SELECT_EVENT`. This finding-plus-actions protocol is the most portable piece of the whole site.

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

1. **The momentum lifecycle state as a desk vocabulary.** *REA adds:* copy the record shape (`state, previousState, stateDuration, score, leadership, reasonCode, transitionReason`). eVector's transition rules are on its server and are not visible, so ours must be written and pre-registered from scratch. It names where a move is in its life, which directly encodes the "current + forward-looking" view. The desk today has scanner hits and an RRG quadrant, but no single per-name/per-sector *state*. It has to be measured before it is trusted: do the transitions (e.g. Ignition → Expansion vs Ignition → Breakdown) carry forward returns? That needs a pre-registered study.
2. **"Tour this chart" narration.** *REA adds:* the exact rules (table above) port to Python or `chart_tool` JS directly, and the finding-plus-chart-actions protocol is the part to copy. Its weights are hand-set and never measured; ours would use measured base rates instead. Turn the existing indicator and scanner overlays into ranked plain-English findings that drive the chart (draw the level, highlight the candle). This fits the beginner-readable direction (B-148–B-157 Indicator Browser v2) and the Stock Analyzer. The desk has already measured several of the same detectors (failed breakout B-182, squeeze/coil B-101, divergence), so each sentence can carry its own measured base rate. eVector does not do that.
3. **A context ladder with "was it the stock or the market?"** Market → sector → industry → theme tiles with trend words, plus an attribution line (stock move vs sector vs NIFTY). The Sector Lobby and peers table hold most of the pieces; this is mostly a presentation layer on the Stock Analyzer.
4. **Event markers on the chart, plus measured-vs-hypothesis event links.** B-184 just built the measurement half (`event_study.py`: the reaction measured from the close before the event). Plotting RBI and Budget days, earnings, block deals and corporate announcements as E/N/M/⚡ markers is the visual half. The "hypothesis until measured" edge wording fits the desk's pre-registration habit well.
   *REA adds:* store each link as `{expectedDirection, direction, excess, z, evidence: observed|hypothesis}`, which is the same measurement `event_study.py` already makes for each event. A link becomes "measured" when its excess return has been computed, not when someone asserts it.
5. **Calls graded by the market.** This is the same idea as rec_audit (recommendations scored by later prices), but run forward and personal: "My record". A 5-session up/down call on a sector or name, final once made and resolved from closes, would give the owner a calibration score on their own reads. *REA adds:* hide any comparison number (the crowd there; for us, the model's own score or the scanner verdict) until the call is made, as with eVector's `threshold`/`revealed`.

## Contradictions / cautions vs the wiki

- **Nothing is measured publicly.** eVector shows no base rates for its states, picks or event arrows, and the "momentum engine" thresholds are not disclosed. Per [[analyses/Policy-Event-Study-Result]], our own MPC "events" turned out to be ordinary days, so a link only counts as measured once something like `event_study.py` has measured it.
- **The detectors are classic TA.** Squeeze, failed breakout and divergence are textbook detectors; on this desk, failed breakouts did not warn (B-182) and the coil carried no edge (B-101). Adopt the presentation, not an implied edge.
- **It covers US markets only.** Every ETF in the ladder needs an NSE equivalent: NIFTY/NIFTY 500, the sector indices, and thematic indices (Nifty India Defence, Nifty EV & New Age Automotive, Nifty CPSE, Railways PSU…). All of these exist in NSE's all-indices file.

## Pages updated

- [[analyses/Open-Backlog]]: B-185 to B-189 filed (eVector adoption candidates)
- `index.md`, `log.md`
