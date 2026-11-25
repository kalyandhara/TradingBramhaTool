# Market Health page — index breadth + composite context score

**Status:** plan, awaiting owner confirmation of the Flows pillar.
**What it is:** a desk page ("Market Health") showing (1) how many constituents of
each index sit above / below their 200-day EMA, and (2) a 0–100 composite
*context* score. The weights are the owner's priors (Trend 30, Breadth 25,
Volume 20, Volatility 15, Liquidity/Flows 10) — **unmeasured, not a signal**.
The page says so.

## Data (all already on the desk, no new paid source)
- Constituent lists: `nse_universe.fetch_constituents` (nifty50, nifty100, nifty500
  — cached 7 days) and `smallcap_universe._load_kind` (midcap150, smallcap250).
- Daily bars: one batched yfinance call over NIFTY 500 via
  `trending_stocks._batch_history(period="2y")` (2y so the 200-EMA is warmed up).
  Every group below is a subset of NIFTY 500, so one download serves all.
- NIFTY 50 + India VIX: `market_health.fetch_indices()`.
- FII index-futures long share: `participant_oi` (NSE participant OI CSV, free).

## Breadth groups
NIFTY 50 · NIFTY Next 50 (= 100 − 50) · Midcap 150 · Smallcap 250 · NIFTY 500 ·
one row per NSE macro-sector *within NIFTY 500* (labelled "NIFTY 500 · <sector>",
not the official sector index — NSE sector index CSVs are not cached here).
Each row: members, with data, above, below, % below. Names without ≥200 bars are
counted as "no data", never as above or below.

## Pillars (each 0–100)
| Pillar | Inputs | Score |
|---|---|---|
| Trend 30 | NIFTY 50 close, 50 & 200 EMA | 25 each: close>50EMA, close>200EMA, 50EMA>200EMA, 200EMA rising over 20 sessions |
| Breadth 25 | NIFTY 500 | 0.6 × % above 200 EMA + 0.4 × % of names that advanced last session |
| Volume 20 | NIFTY 500, last 20 sessions | up-day volume ÷ total volume × 100 |
| Volatility 15 | India VIX, 1y | 100 − VIX percentile rank; fallback NIFTY 20d realized vol percentile |
| Flows 10 | participant OI | FII index-futures long share × 100 (**needs owner OK**) |

Composite = Σ wᵢ·sᵢ / Σ wᵢ over pillars that could be read; a missing pillar is shown
"not assessed" and the total says how much weight it covers. Plain-English read:
≥70 broadly healthy, 50–70 mixed, 30–50 weak, <30 stressed — descriptive only.

## Where it sits
New module `tools/market_breadth_score.py` (pure maths + fetch helpers), page
`tools/desk_pages/market_health_page.py`, registered in `desk_pages.PAGES` and the nav.
Tests: `tools/test_market_breadth_score.py` (breadth counts, pillar maths, renormalised
composite). Verify on fresh :8502.

## Approaches considered
- Extend existing `market_health.py` (the DS-1 pass/fail gate) — rejected: it is a
  gate with its own semantics; mixing a weighted score in would blur both.
- Add to the Home breadth strip — rejected: Home is already three dense panes.
- **New page + new module (chosen).**
