---
title: "YouTube — Crypto Momentum Screener + Telegram Alert Bot (Hyperliquid, Claude Code)"
category: source
tags: [tools, screener, crypto, hyperliquid, telegram, claude-code, day-trading, swing-trading]
created: 2026-06-29
updated: 2026-06-29
sources: 1
related:
  - strategies/Hyperliquid-Momentum-Screener.md
  - sources/YT-MultiChart-TradingView-Alternative.md
  - concepts/EMA.md
---

# [YouTube] — Crypto Momentum Screener + Telegram Alert Bot (Hyperliquid, built via Claude Code)

## Metadata
- **YouTube page title** (via oEmbed): "Claude Code Built a FREE Breakout Stock Screener (2 of My Rules Were Wrong) | FREE PROMPT SHARED"
- **Channel**: The AI University ("Nan" / Nitin)
- **URL**: https://www.youtube.com/watch?v=vZ8usGRL_h8
- **Ingested**: 2026-06-29 (full transcript pasted by Kalyan after automated fetch was blocked)
- **Relevance**: Direct companion build to [[sources/YT-MultiChart-TradingView-Alternative]] (same channel,
  same Hyperliquid data source) — adds a screening/alerting layer on top of live multi-pane charting.

**Note on title mismatch**: the actual transcript content is a **crypto momentum
screener + Telegram bot** (Hyperliquid perpetuals), not a stock breakout screener. The
oEmbed-reported page title talks about "2 of My Rules Were Wrong" and a stock screener —
that content is not present anywhere in the supplied transcript. Treat the content below
as authoritative (it's the actual transcript); the title may belong to a different
upload, a retitled video, or a YouTube metadata caching quirk. Flagging the discrepancy
rather than silently picking one.

## Key Takeaways

1. **Don't trade on a single signal.** Price-up, high-volume, or EMA-cross alone all fire
   on fake pumps/dead-cat bounces/wash trades. Three *independent* filters confirming
   different dimensions (participation, timing, direction) simultaneously = a
   meaningfully better setup, not a guarantee.

2. **Filter 1 — Volume/market-cap ratio > 0.10** normalizes volume across coins of very
   different sizes; >10% of market cap traded in a day = real capital moving.

3. **Filter 2 — Momentum needs a floor AND a ceiling**, not just a floor. Floor (+1%/1h,
   +5%/24h) confirms the move started; ceiling (+5%/1h, +15%/24h) prevents chasing an
   already-overextended move. Most screeners skip the ceiling — that's the gap this one
   closes.

4. **Filter 3 — EMA9 > EMA21 > EMA50 stack + price > VWAP** confirms direction across
   three timeframes simultaneously and confirms buyer control since session open. Fake
   pumps almost always fail this.

5. **Same screening logic flips between day trading and swing trading** just by widening
   the momentum floor/ceiling band and lengthening the scan timeframe — no code changes,
   only config/threshold changes.

6. **Free, no-API-key data source**: Hyperliquid's public API gives live price, 24h
   change, volume, and candle history for every perpetual market with no signup and no
   cost. This is the same data source the dashboard's `tools/data_source.py`
   (`HyperliquidSource`) already implements.

7. **Telegram alerting is essentially free infrastructure**: create a bot via
   @BotFather, grab the bot token, get your chat ID from `getUpdates`, done — no paid
   service needed for push alerts.

8. **Built with one detailed Claude Code prompt** (Opus 4.7) plus follow-up prompts for
   UI refinements — FastAPI backend + simple web UI, running locally on port 8000.

## Detailed Notes

### Setup Steps (replication)
1. **Telegram bot**: Telegram → search `@BotFather` → `/newbot` → display name (e.g.
   "my crypto screener and alert presenter") → unique username ending in `_bot` (e.g.
   `momentum_day_trading_crypto_bot`) → BotFather returns a bot token.
2. **Chat ID**: open the bot's link, click Start, send any message (e.g. "hello") →
   visit `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser → find the `"id"`
   field in the JSON response.
3. **VS Code + Claude Code extension**: install from the VS Code marketplace, log in with
   Claude Code credentials, open a project folder.
4. **Init prompt**: "please initialize the project and create necessary CLAUDE.md file
   as well as .env file" → Claude Code asks: language runtime (Python chosen), data
   source (Hyperliquid, described as "other"), alert destination (Telegram bot), and
   alert logic (cleaner/custom — "other based on cleaner").
5. Paste bot token + chat ID into the generated `.env` file (never hardcode secrets in
   the prompt/command line).
6. **Build prompt**: one detailed prompt (shared in creator's description/School
   community, not reproduced verbatim in the transcript) builds the full two-phase
   screener: FastAPI backend, simple web UI, Hyperliquid screener, Telegram alert bot.
7. Follow-up prompts added: timeframe selector (1m/5m/15m/1h/1d), auto-refresh + alert
   toggle, per-coin chart-icon drill-down, adjustable filter controls, reset-to-default
   button.

### UI / Runtime Behavior Observed
- Runs at `localhost:8000`.
- Auto-refresh + alert checkbox re-screens on the selected timeframe interval and
  re-fires Telegram alerts on each pass if new coins qualify.
- Live demo on a 5-minute timeframe: 2 coins passed all 3 filters → Telegram alert
  fired instantly; 5 minutes later, re-scan found 2 more qualifying coins → second
  alert fired automatically.
- All thresholds exposed as UI controls: relative volume, min/max 24h %, min/max move for
  selected timeframe, EMA periods (9/21/50 default), above/below-VWAP toggle (long vs.
  short bias).

## Actionable Insights for Kalyan's Setup

1. **Reuse, don't rebuild, the Hyperliquid connection.** `tools/data_source.py`'s
   `HyperliquidSource` and `tools/chart_server.py`'s WS bridge already pull live
   Hyperliquid candles/prices for the multi-chart dashboard — the volume/cap, EMA, and
   VWAP math from this screener could be layered on top of that existing connection
   instead of standing up a second Hyperliquid integration.

2. **The floor+ceiling momentum band is a generally reusable pattern**, not crypto-
   specific. The existing CCI-gated equity scanners in [[strategies/Screener-Queries]]
   mostly use a floor-only momentum trigger (CCI(34) > 100) with no explicit ceiling —
   this video's "ceiling prevents chasing an overextended move" logic is worth
   considering as an addition there too.

3. **Telegram alerting is cheap, proven infrastructure** for any of the existing
   screener/scanner outputs (Chartink scanners, `screener_pipeline.py` shortlist, sector
   rotation flips) — the bot-token + chat-ID setup here is a 5-minute, zero-cost pattern
   that generalizes beyond crypto.

4. **Day↔swing mode switch via threshold widening, not new code** — a useful design
   principle if/when `screener_pipeline.py` or the dashboard ever need both an intraday
   and a swing variant of the same screen.

## Contradictions with Existing Wiki
- None directly — this is a tooling/implementation video like
  [[sources/YT-MultiChart-TradingView-Alternative]], not a strategy/methodology claim
  that conflicts with existing wiki content.
- Flagged above: a metadata discrepancy between the YouTube page's reported title (stock
  breakout screener, "2 rules were wrong") and the actual transcript content (crypto
  momentum screener). Not a wiki contradiction, but worth knowing if this source is
  revisited later — the title may not describe the content accurately.

## Pages Updated
- Created: `wiki/strategies/Hyperliquid-Momentum-Screener.md`
- Updated: `wiki/index.md` (pages +2, sources +1)
- Updated: `wiki/log.md`
