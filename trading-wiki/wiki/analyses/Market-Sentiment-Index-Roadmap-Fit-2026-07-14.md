---
title: "Analysis: Market Sentiment Index — Roadmap Fit for Trading Bramha"
category: analysis
tags: [roadmap, sentiment, breadth, feature-planning]
created: 2026-07-14
updated: 2026-07-14
sources: 1
related:
  - concepts/Market-Sentiment-Index.md
  - sources/Madhur-Raut-Market-Sentiment-Index-Infographic.md
  - analyses/Market-Sentiment-Futures-Roadmap.md
---

# Analysis: Market Sentiment Index — Roadmap Fit
_14 July 2026_

## Thesis
The Raut-style composite ([[concepts/Market-Sentiment-Index]]) is a **medium-value, low-effort** addition to Trading Bramha. Three of the five inputs are already computable from data we ingest today; the other two need a modest options-data pull. Total build ≈ **2-3 focused sessions**. Highest leverage is as a **top-of-dashboard regime gauge** that also gates position sizing in the screener pipeline.

## Evidence For

### 1. Three inputs are already-earned
| Input | Where we have it |
|-------|------------------|
| **Advance / Decline** | Daily bhavcopy already pulled by `tools/screener_pipeline.py` — one groupby on `close vs prev_close`. |
| **Sector Performance** | `tools/sector_rotation.py` + `sector_rotation_trail.py` compute 22-sector daily returns. Green-vs-red count is a one-line reducer. |
| **Technical Trend on NIFTY** | We already compute per-symbol EMA/RSI/MACD/PMax. Point it at `^NSEI` on 1H and 3M — same pipeline, different symbol. |

### 2. Fills a real gap
- Our stack is **bottom-up** (VCP, Rounding Bottom, PMax, Harmonic) — no market-wide regime gauge.
- Existing sources push for a regime gate: [[sources/Minervini-Think-Trade-Champion]] (200-MA regime rule), [[sources/YT-Samir-Varmer-Physicist-Trader]] (Varmer regime), [[sources/Prop-Trading-Secrets-Lien-Crete-2025]] (3-strikes/regime discipline).
- Screener output today shows *what* to buy but not *whether to be buying at all*.

### 3. Composes with existing surfaces
- **Dashboard header card**: gauge + sentiment band (already have colour-coded chips in the app).
- **Screener conviction multiplier**: score in ["Sell", "Strong Sell"] → cap position size at half; ≥ "Buy" → full size. Slots into [[concepts/Kelly-Criterion]] / position-sizing tool.
- **Reversal Calendar overlay**: publishing a daily sentiment stamp alongside yoga/lunar days lets us backtest whether reversals cluster at low-sentiment prints.

### 4. Low ongoing cost
Once wired, the daily update is a cron behind the existing screener pipeline (already fires 4:05 PM). No new infra.

## Evidence Against

### 1. PCR data is the friction point
- We don't currently pull raw NSE option-chain data — [[sources/OptionTools-in]] is scraped narratively, not as a numeric feed.
- Options fetch means either NSE option-chain endpoint (throttled, occasionally IP-blocked) or a paid source. **~1 session of scraping + resilience**.

### 2. The card is descriptive, not predictive
- No visible backtest of the composite → next-day NIFTY return relationship. We'd be adopting the *format* on faith.
- **Mitigation**: build the same gauge but log daily readings so we can validate after 30-60 days before letting it gate real trades.

### 3. Weight scheme is arbitrary
- 30/20/20/15/15 has no derivation. Any weighting would work equally well without a fit.
- **Mitigation**: expose weights as a config; run a small optimiser (fit against 5-day forward NIFTY return) after a month of logged data.

### 4. "Technical Trend" rows look decorative
- Both TT rows scored 8/15 for "Neutral" on the sample card, and the impact bars matched — suggests a fixed midpoint when the trend model isn't strongly directional. Adds noise, not information.
- **Mitigation**: replace both TT rows with **PMax direction on NIFTY 1H** + **NIFTY vs SMA200** — cleaner, disclosed, and already-computed.

## Conclusion

**Yes, add it. Add it as v1 with substitutions.**

### Suggested v1 (Trading Bramha variant)
| # | Input | Weight | Data source | Rule |
|---|-------|--------|-------------|------|
| 1 | Advance / Decline (NIFTY-500) | 25 | bhavcopy | ratio → 0-1 factor |
| 2 | Sector Performance (22 sectors) | 20 | sector_rotation | (green - red + 22) / 44 |
| 3 | NIFTY vs SMA200 (regime) | 20 | yfinance | above=1.0, below=0.0, distance-scaled |
| 4 | PMax direction on NIFTY 1H | 15 | our PMax port | up=1.0, down=0.0 |
| 5 | PCR + PCR-slope on NIFTY | 20 | NSE option chain (new fetch) | absolute + direction blend |

Weight = 100. Same gauge bands as Raut's card. **Ships without input #5** on day one — bhavcopy + sector + regime + PMax are already home data. PCR added when the option-chain scraper lands.

## Action Taken / Plan

### Roadmap slot — Phase 1 (this week)
1. Create `tools/sentiment_index.py` with the four home inputs. Reuse existing modules; no new dependencies.
2. Add a top-of-dashboard **Market Sentiment** gauge card in `tools/dashboard_app.py` (`streamlit`).
3. Persist daily readings into `trading_bramha.db` (new table `sentiment_history`).
4. Add a `sentiment` column to screener output — lets the "Chart" column and the eye-icon flow inherit today's regime tag.

### Roadmap slot — Phase 2 (once option-chain fetch lands)
5. PCR + PCR-slope input.
6. Backtest weights vs 5-day forward NIFTY return over ≥60 days of logged data.
7. Regime-gated conviction multiplier in screener + position-sizing tool.

### Roadmap slot — Phase 3 (nice-to-have)
8. Overlay daily sentiment stamp on the Reversal Calendar; test whether reversal days cluster in low-sentiment prints.
9. Add distribution-days sub-signal ([[concepts/Distribution-Days]]) as a sixth optional input.

## Outcome
_To be filled in after Phase 1 ships._

## Related Pages
- [[concepts/Market-Sentiment-Index]]
- [[sources/Madhur-Raut-Market-Sentiment-Index-Infographic]]
- [[concepts/Stage-Analysis]]
- [[concepts/Kelly-Criterion]]
- [[concepts/Distribution-Days]]
