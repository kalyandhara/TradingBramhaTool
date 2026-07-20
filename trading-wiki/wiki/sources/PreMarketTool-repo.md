---
title: "Pree Market Tool — Local Repo (US + India pre-market scanner)"
category: source
tags: [premarket, scanner, gappers, humbled-trader, watchlist, two-brain, us-equity, india-equity]
created: 2026-07-08
updated: 2026-07-08
sources: 1
related: [strategies/Humbled-Trader-Trend-Join-Long, sources/OptionTools-in]
---

# Pree Market Tool — Local Repo (US + India pre-market scanner)

## Metadata
- **Location:** `C:\python_project\Pree_Market_Tool\` (local, not in trading-bramha working tree)
- **Author:** Kalyan (personal repo)
- **Format:** Python scanner + two-AI-brain report generator (Claude pass + Codex pass → merged HTML report)
- **Regions supported:** `MARKET_REGION=US` (default) or `MARKET_REGION=IN`
- **Date accessed:** 2026-07-08
- **Sample output on disk:** `reports/premarket_2026-07-04.html`, `reports/delivery_2026-07-04.txt`

## What This Tool Does
Runs a pre-market scan (yfinance + RSS news + Forex Factory econ calendar), packages the state into `packet.json`, then routes that packet through **two independent AI passes** (Claude via `prompt_claude.md`, Codex via `prompt_codex.md`) and merges their reads into a Humbled-Trader-style report following `REPORT_TEMPLATE.md`. Delivery step writes an HTML report and a text delivery note to `reports/`.

### Pipeline
1. `scan.py` — fetches market snapshot, gappers, RSS headlines (with catalyst matching), econ calendar, macro instruments; writes `packet.json`.
2. `prompt_claude.md` + `prompt_codex.md` — independent LLM analyses of the packet (no cross-pollination).
3. `prompt_merge.md` — reconciles the two into a single report following `REPORT_TEMPLATE.md`.
4. `render_report.py` — fills the template, produces `REPORT.md` for the date.
5. `deliver.py` — writes a delivery note next to the HTML.

### Region wiring
- **US mode:** ^GSPC / ^DJI / ^IXIC / ^RUT / ^VIX / ^TNX / ^IRX / CL=F / DX-Y.NYB; static universe of 40 mega-cap/momentum names; MarketWatch + CNBC + Yahoo + Google News RSS; ET session times.
- **IN mode:** ^NSEI / ^BSESN / ^NSEBANK / ^INDIAVIX / USDINR=X / CL=F; static universe of top-20 NSE names; ET Markets + Moneycontrol + BloombergQuint + Business Standard + Google News India RSS; IST session times.
- Region selection: env var `MARKET_REGION=IN` (or `$env:MARKET_REGION = 'IN'` on PowerShell). Region flag flows into `packet.scan_params.market_region` so the prompts branch on it.

## Watchlist Rules (from `WATCHLIST_CRITERIA.md`)

### Day trade — "Trend Join Long"
**Premarket filters:** gap > 3% · price > $3 · mcap > $1B · premarket RVOL > 1.5 · price above prior-day high.
**Intraday plan:** trade window 10:00–15:30 ET · trigger break of premarket high + prior HOD · stop 1% below PMH or LOD (whichever is lower) = 1R · scale ⅓ at +1R, ⅓ at +2R, trail last ⅓ on 21 EMA · flat by 15:51 ET.
**Backtest:** 54.6% win rate, PF 1.59, 280 trades.

### Swing — "Gap-up + Real Catalyst"
**Premarket filters:** gap ≥ 8% · price > $3 · open > prior-day high · open > 200-day SMA · mcap ≥ $800M · **real catalyst** (earnings on gap day, or news with no earnings).
**Entry note:** starter ideas only — entry/exit management still being built, no fake stops/targets.
**Backtest:** 57.6% WR / PF 5.34 on news catalysts; 44.7% WR / PF 2.57 on earnings catalysts.

## Key Design Choices Worth Preserving
- **`packet.json` is source of truth** — both AI passes are explicitly forbidden from inventing catalysts/numbers/headlines. This is the correct guardrail for LLM-generated trader-facing reports.
- **`catalyst_found: false` = automatic SKIP.** No thesis is built around a gap without an identified catalyst. This alone eliminates most "up on nothing" chase traps.
- **Two independent brains, then merge.** Explicit rule in `prompt_codex.md`: *"trade where both agree, stand down or size down where they disagree, and never average."* This is a real edge protocol, not decoration.
- **Voice discipline:** Humbled Trader style, no em dashes, tight — the report format is scannable in <60 seconds.

## Actionable Insights
- **This tool + OptionTools.in = a complete pre-market stack.**
  - Pree Market Tool covers: **cash-equity gappers, macro instruments, econ calendar, news catalysts** (US + India).
  - OptionTools.in covers: **NIFTY/BANKNIFTY options positioning tape** (OI spurts, PCR, max pain, underlyings heatmap).
  - Together they give: cash-equity pre-market watchlist + options-flow bias → one full report per session.
- **India-mode is already wired but not yet the primary use.** The scanner produces the same-shape packet for NSE names using India VIX + USDINR context. Run `$env:MARKET_REGION = 'IN'; python scan.py` daily to bootstrap the India pre-market watchlist that fits our existing wiki bias (Indian equity swing).
- **The Humbled Trader "Trend Join Long" rule set is a validated day-trade template** (54.6% WR / PF 1.59 / 280 trades) — worth extracting into a first-class strategy page even though the tool documents it. Filed as [[strategies/Humbled-Trader-Trend-Join-Long]] follow-up (queued, not this ingest).
- **Static universe is a limitation.** Only 20 India names are scanned (top mega-caps). The mid-cap gappers where actual daily edge exists (which is where the OptionTools.in losers list finds them) aren't in scope. Extending the India universe using our existing NSE bhavcopy top-volume list (from `screener_pipeline.fetch_bhavcopy_top_volume`) would be a high-leverage change.
- **`packet.json` is a natural join point to the trading-bramha dashboard.** Reading it from Streamlit and rendering the two-brain report inline (as a new dashboard tab) would fold this repo's output into the existing workflow — no daily context-switch to `C:\python_project`.

## Contradictions with Existing Wiki
- **Rule collision on "flat by 15:51 ET" vs Indian equity swing pages** — trivial (different timeframes / different markets), noted so future readers know the tool's day-trade rules are US-market specific.
- **No overlap with [[strategies/Koroush-Breakout-Momentum]]** — that's a crypto 1m breakout; this is a US-cash pre-market gapper on a rule-based confluence. Different game, no conflict.

## Pages Updated
- Created: `wiki/sources/PreMarketTool-repo.md` (this page)
- Updated: `wiki/index.md`, `wiki/log.md`
- Flagged (not created this ingest): `strategies/Humbled-Trader-Trend-Join-Long.md` — worth extracting the rule set as a first-class strategy page.
