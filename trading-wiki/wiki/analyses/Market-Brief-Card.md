---
title: "Morning Market Brief card — build notes and the two honest departures"
category: analysis
tags: [morning-brief, card, market-sentiment, breadth, panchang, astro, data-quality, yahoo-feeds]
timeframe: intraday
created: 2026-08-09
updated: 2026-08-09
sources: 1
related:
  - concepts/Panchang.md
  - concepts/Market-Sentiment-Index.md
  - concepts/Volume-Profile.md
  - analyses/Financial-Astrology-Sector-Week-Roadmap.md
  - analyses/Backtest-Harness.md
---

# Analysis: Morning Market Brief card — 2026-08-09

**Ask (user, 2026-08-09):** reproduce a published "Morning Market Brief" infographic — global cues, India open, commodities/FX, sector breadth, overall sentiment — **including the finest astro detail of the day**, on the Market Sentiment page.

## Thesis

Most of the card was already reproducible: the composite gauge exists, US indices were already fetched, and the remaining quotes are ordinary yfinance rows. **The two parts that needed real thought were the two the source card gets away with cheaply** — sector breadth, and the astro layer. Both were built by refusing the cheap version.

## Delivered

| Piece | Where |
|---|---|
| Offline panchang engine | [panchang.py](tools/panchang.py) — see [[concepts/Panchang]] |
| Global quotes + breadth + composition | [market_brief.py](tools/market_brief.py) |
| Rendered section | **Market Sentiment** page, [dashboard_app.py](tools/dashboard_app.py) |

Live run, 2026-08-09: tone **CAUTIOUS**, 13/13 quotes fresh, breadth **12/19 sectors red** on **500/500** constituents scored, full panchang (Sunday · lord Sun · Rahu Kaal 17:33–19:10 · Mrigashira pada 4, sub-lord Venus · Krishna Ekadashi 92% · hora Mercury→Moon at 09:30 · Saturn retrograde).

## Departure 1 — breadth from constituents, because the sector indices are dead

The obvious implementation is to read the NSE sector indices and count the red ones. **That number would be fiction.** `sentiment_index._sector_perf` already documents that Yahoo stopped updating **8 of the 11** NSE sector index feeds on **2026-07-17**, and the failure is silent: a frozen feed returns an old bar rather than erroring. It had already caused a real mis-read — a 2026-08-03 sentiment reading scored 3 surviving indices, all green, and fed a full 25/25 into the composite.

So breadth is computed from the **Nifty 500 constituents**, grouped by NSE's own macro-industry tag (20 of them, from the exchange's published CSV via `nse_universe.fetch_constituents`, cached 7 days — no per-symbol `.info` calls, so it is one batched download).

Two choices inside that:
- **Median, not mean.** A sector is red when its *median* constituent is down, so one collapsing name cannot paint a sector.
- **Thin sectors are reported, not counted.** Fewer than 5 scored constituents and the sector is named separately (currently `Diversified`, n=3). A two-stock "sector" is not breadth.

Cost: ~6 seconds for 500 names. Coverage on the first live run was **500/500, zero stale, zero missing** — so the expensive path is also the reliable one here.

> [!key-insight] The staleness check paid for itself on its first run — and found the same 2026-07-17 date
> The quote strip age-checks every row. On the first live run it flagged **China CSI 300 (`000300.SS`) as 23 days stale** — last bar **2026-07-17**, while every live China ticker printed 08-07. Without the check the card would have shown **−3.60% as today's move**.
>
> That is the *same date* the 8 NSE sector index feeds froze. Two unrelated index families, one date — this looks like a single batched Yahoo index-feed drop, not flakiness. **Working assumption going forward: any `^`-style index ticker can go quietly stale, and only an age check will tell you.** The row now uses `510300.SS` (CSI 300 ETF) and is labelled with a `*` to mark it a proxy rather than the index.

## Departure 2 — the astro layer states facts and makes no call

The source card pairs its readings with directional language. The equivalent here would be "avoid fresh buying during Rahu Kaal". **That line is not printed, and its absence is the point.**

Rahu Kaal being inauspicious is a *traditional assertion*. This repo has never measured whether NIFTY behaves differently inside it — that is **FA-2**, and it has not run. The repo's stated position is astro-as-context-modifier, never a signal, and per the FA roadmap the honest way to hold that line "is not caution in the caption, it is a measurement."

So the panchang block prints windows, lords, padas and transit times, with an explicit note that **no window here carries a measured market effect**. The card's tone badge (WEAK / CAUTIOUS / STRONG) is derived **only** from Nifty's change and breadth — `overall_tone()` takes no astro input at all.

This is also why the astro layer is *more* falsifiable than most of what the repo ships: every window is exact and pre-registered. Rahu Kaal is easier to test than PCR or the OI quadrant, both of which remain unmeasured.

## Evidence Against / open risks

- **Nothing on this card is measured.** The composite gauge, the breadth cut, and the panchang are all unvalidated against forward returns. The card reports state, not edge, and should not be read as either.
- **FA-2 still needs an intraday store.** Hora and Rahu Kaal are intraday claims; `chart_server` fetches intraday bars and nothing persists them. That gap is the binding constraint on measuring the astro layer — the same constraint blocking the [[concepts/Volume-Profile]] 80% rule.
- **Sharing risk.** A brief card is inherently shareable and travels without context. It is currently in-page only; **a PNG export would need the disclaimer rendered into the image**, not placed beside it.
- **Ayanamsa is an approximation** (~1 arcmin) — fine for nakshatra/pada, not for finer work. Stated in the module docstring.

## Action Taken / Plan

- ✅ FA-1 shipped and verified to the minute against a published card ([[concepts/Panchang]]).
- ✅ Constituent-based breadth, with coverage and staleness surfaced.
- ✅ Card section on the Market Sentiment page, facts-only astro.
- ⏭ **Correct the FA roadmap's FA-0 entry** — it lists a blocker that was already fixed on 2026-08-02, five days before that roadmap was written.
- ⏭ **FA-2**: an intraday store, then Rahu Kaal / hora windows vs a random-window baseline with a significance test. Until then no interpretive astro language ships.
- ⏭ Optional: PNG export via the proven `sector_card.py` / `opportunity_report.py` renderer trio, disclaimer rendered *into* the image.

## Outcome (fill in later)

## Related Pages

- [[concepts/Panchang]] — the almanac engine and its verification
- [[analyses/Financial-Astrology-Sector-Week-Roadmap]] — FA-0…FA-6; this delivers FA-1
- [[analyses/Backtest-Harness]] — where FA-2 lands
- [[concepts/Market-Sentiment-Index]] — the composite the card reuses rather than duplicating
