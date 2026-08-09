---
title: "Financial Astrology — weekly sector & stock outlook card (FA roadmap)"
category: analysis
tags: [roadmap, financial-astrology, astro, hora, rahu-kaal, nakshatra, panchang, sector, weekly-card, backlog]
timeframe: milestone-plan
created: 2026-08-07
updated: 2026-08-07
sources: 1
related:
  - analyses/Astro-Weekly-Forecast-Card-Fit.md
  - analyses/Backtest-Harness.md
  - analyses/Opportunity-Hub-Roadmap.md
  - analyses/Dashboard-UI-Roadmap.md
  - concepts/Mercury-Retrograde-Market-Cycle.md
---

# Analysis: Financial Astrology — weekly sector & stock card — 2026-08-07

**Ask (user, 2026-08-07):** produce a *week-forward* infographic in the style of
a published "Bullion Market Outlook — Astro Trading Strategy" card, but for
**impacted sectors and the top stocks inside them**.

## Thesis

**The astrological layer is entirely computable offline. The market layer
already exists. The join between them — planet → sector → stock — is the only
genuinely new thing, and it is also the only part that cannot be derived from
anything.** That asymmetry should decide the build order.

> [!key-insight] The feasibility question is settled, and it was settled by reproducing the source card
> Computing **Rahu Kaal for Tuesday 28 July 2026, Mumbai** from `ephem` locally
> gives **16:00–17:38 IST**. The published card says **04:00 PM – 05:38 PM IST**.
> Exact match, to the minute. Moon nakshatra agrees too — Purva Ashadha pada 3 at
> 05:30 IST, rolling to pada 4 by 06:31, exactly the transition the card prints.
>
> **So the whole panchang layer needs no API, no login, no rate limit and no
> vendor.** `ephem 4.2.1` is installed (backlog B-14, closed 2026-08-07) and a
> lat/lon is all the input required. This is the opposite of the PCR/bhavcopy
> situation — there is nothing to fetch and nothing to be throttled by.

## Field assessment — verified 2026-08-07

### Already here

| Piece | Status | Where |
|---|---|---|
| Yoga + lunar event store | ✅ **278 events, 2026-01-03 → 2027-12-28** | `reversal_calendar.db` (`reversal_events`) |
| Events for a range · day clustering | ✅ `events_in_range` · `coincidence_scores` | [reversal_calendar.py](tools/reversal_calendar.py) |
| Nakshatra yoga dates | ✅ 527 lines | [yoga_dates.py](tools/yoga_dates.py) |
| Lunar phase engine | ✅ and now **runnable** — `ephem` installed | [lunar_phases.py](tools/lunar_phases.py) |
| Classical FA methods | ✅ McWhirter nodal · Gann degree · Dewey cycles · dignity scoring | [financial_astrology_methods.py](tools/financial_astrology_methods.py) |
| Astro Timing dashboard page | ✅ | [dashboard_app.py](tools/dashboard_app.py) |
| Chart overlay for the same events | ✅ | `reversal_calendar` indicator |
| **Sector → constituent → ranked stocks** | ✅ **the market half is done** | `opportunity_hub.build_constituent_table` + `rank_groups` |
| Card renderer pattern (PNG + text + PDF) | ✅ proven twice | [sector_card.py](tools/sector_card.py), [opportunity_report.py](tools/opportunity_report.py) |
| Weekly astro card scope | ✅ already written | [[analyses/Astro-Weekly-Forecast-Card-Fit]] — AW-0…AW-4 |

### Absent — verified by search, zero occurrences each

| Missing | Note |
|---|---|
| **Hora** (planetary hours) | `astrohora_loader.py` is a **CSV parser for the AstroHora desktop app** (birth charts, Vimshottari dasha) — *not* a planetary-hour calculator. The name is a false friend. |
| **Rahu Kaal** | `kaal` → 0 hits repo-wide. (`rahu` appears only as a dasha planet.) |
| **Sub-lord (KP / Krishnamurti Paddhati)** | 0 hits. The source card's "SUB-LORD" column. |
| **Nakshatra pada** | 0 hits. Nakshatra exists; the 4-fold pada subdivision does not. |
| **Planet → sector map** | 0. `sector` appears in 25 modules, all market-data sector tags, none astrological. |
| **Planet → stock map** | 0. Would compose from the sector map + Opportunity Hub. |

### What must come from the web — almost nothing

| Input | Source | Verdict |
|---|---|---|
| Sunrise / sunset (drives Hora **and** Rahu Kaal) | `ephem` + lat/lon | **local** |
| Moon sidereal longitude → nakshatra + pada | `ephem` + Lahiri ayanamsa | **local** |
| Planetary hour sequence | Chaldean order + weekday | **local, pure arithmetic** |
| Sub-lord | Vimshottari proportions over the nakshatra | **local, pure arithmetic** |
| Tithi / yoga / karana | `ephem` (Sun–Moon elongation) | **local** |
| Retrogrades, ingresses, eclipses | `ephem` | **local** |
| **Economic events** (Fed, CPI — the card's left column) | external calendar | **the only genuine fetch, and it is not astrology** |
| NSE results calendar | ✅ already shipped | [earnings_calendar.py](tools/earnings_calendar.py) |

Panchang APIs (ProKerala, VedicRishi, DrikPanchang) exist and are mostly paid or
rate-limited. **Do not take a dependency on one.** Everything they return is
computable here, and a vendor would add a failure mode for no capability.

## The hard part — and it is not the astronomy

The planet → sector assignments are **traditional, asserted, and mutually
inconsistent across sources.** A common set:

| Planet | Traditionally assigned sectors |
|---|---|
| Sun | government, PSU, power, energy |
| Moon | FMCG, dairy, liquids, hospitality |
| Mars | metals, defence, engineering, real estate |
| Mercury | IT, telecom, media, brokerage |
| Jupiter | banking, financial services, insurance, education |
| Venus | auto, luxury, textiles, entertainment |
| Saturn | oil & gas, mining, infrastructure, labour-heavy |
| Rahu | speculation, commodities, "new" sectors |
| Ketu | pharma, chemicals |

Two problems, and both must be stated in the artifact rather than smoothed over:

1. **No provenance.** These come from classical texts and popular practice, not
   from measurement. Different sources disagree (pharma sits under Ketu, Moon or
   Neptune depending on who is asked).
2. **The mapping target is ours, not theirs.** Our sector tags come from
   yfinance (`Technology`, `Consumer Cyclical`, …). Mapping "Mercury → IT" onto
   that taxonomy is a second layer of judgement on top of an unmeasured first
   one.

**This does not make it unbuildable. It makes it a hypothesis, and this repo has
the machine to test hypotheses.**

## The opportunity nobody has taken — it is falsifiable, cheaply

Every element of the source card is a **precise, pre-registered, time-boxed
claim**, which is exactly what [[analyses/Backtest-Harness]] eats:

- **Rahu Kaal** is a determinate ~90-minute window each day. *Do NIFTY returns
  inside it differ from returns outside it?* Years of intraday data answer that.
- **Hora** partitions the session into ~60-minute planetary blocks. *Do
  "Mercury/Jupiter hora" blocks show different mean returns than "Saturn/Rahu"
  blocks?*
- **Nakshatra transits** — daily resolution, testable on the daily bars we hold.
- **Sector mapping** — *does the Mercury-ruled sector basket outperform in
  Mercury periods?* One RRG-style relative-strength test.

This is the single most valuable thing in this roadmap. The repo's stated
position ([[analyses/Dashboard-UI-Roadmap]] Phase 3) is *"scope the Astro
vertical as a regime/context modifier, **never** a standalone entry signal"* —
and the honest way to hold that line is not caution in the caption, it is a
measurement. **Measure before mapping, and the card either earns its sector
calls or reports that it could not.**

Note the sharp asymmetry with everything else shipped recently: PCR, RSI
divergence and the OI quadrant are all *unmeasured* (backlog B-19/B-25) because
measuring them is real work. **Rahu Kaal is easier to test than any of them** —
the windows are exact, known in advance, and require no detector.

## Evidence Against

- **The framing risk is the highest in the repo.** The source card prints
  *"BEARISH BIAS"*, *"Avoid fresh buying"*, *"Buying interest may return"* against
  clock times. Attaching that to **named stocks** and a shareable PNG is the most
  advice-shaped artifact this project could produce, and it travels without
  context by design. AW-4 already called the honesty layer *"not optional"*;
  here it is load-bearing.
- **Two astro surfaces already disagree about the moon.**
  `astro_trading.get_lunar_phase()` is broken in three ways (AW-0) and is a live
  path on the Astro Timing page. Building a second consumer before fixing it
  repeats the `detect_bullish_rsi_divergence` split (backlog B-24).
- **Intraday data.** Hora and Rahu Kaal are intraday claims; the F&O/cash
  bhavcopy path is **end-of-day**. Testing them needs intraday bars we do not
  routinely store — `chart_server` fetches them, nothing persists them.
- **Scope.** The source card is one commodity (bullion). Extending to ~200 stocks
  across 11 sectors multiplies both compute and the number of ways to be wrong.

## Phased plan — FA-n

**FA-0 · Fix the moon first (prerequisite, = AW-0).** Make
`astro_trading.get_lunar_phase` delegate to `reversal_calendar` and delete the
approximation. Non-negotiable: two surfaces disagreeing about the moon
invalidates anything built on either. `ephem` is now installed, so
`lunar_phases.py` can also rebuild the DB beyond 2027-12-28.

**FA-1 · `panchang.py` — the offline ephemeris layer.** Pure module, no
Streamlit, mirroring `pcr.py`'s shape. For a date + lat/lon: sunrise/sunset,
**Hora sequence**, **Rahu Kaal** (plus Yamaganda/Gulika if cheap), **Moon
nakshatra + pada** with transit timestamps, tithi, and retrograde flags.
Verified against published panchang for several dates — the Rahu Kaal check
above is the template. **No network calls.**

**FA-2 · Measure it before mapping it.** Feed FA-1's windows to the backtest
harness: Rahu Kaal vs rest-of-day, hora blocks, nakshatra days. Report edge vs a
random-window baseline **with a significance test** (backlog B-20a). Needs an
intraday store — that is the real cost of this phase, and it is worth paying
here rather than assuming.

**FA-3 · The planet → sector map, declared as data.** One table, in code, with a
`provenance` field per row saying which tradition asserts it — never presented as
derived. Maps to **our** yfinance sector strings so the join is explicit and
auditable.

**FA-4 · Sector → stock, pure composition.** `opportunity_hub.rank_groups` +
`stocks_in_groups` already turn a sector into ranked constituents. Once FA-3
names the sector, the stock list is the Opportunity Hub's existing output —
**no new market code at all.**

**FA-5 · The weekly card.** `astro_week.py` `build_model` → `render_png` /
`render_text` / `render_pdf`, reusing `opportunity_report.py`'s proven trio and
`report_style` tokens. Seven day-columns, per-day hora/Rahu-Kaal strip, the
sector call, and the top stocks beneath it.

**FA-6 · The honesty layer, rendered INTO the image.** Every claim's *status*
travels with it: which elements are measured (FA-2's findings, with their
numbers), which are traditional assertions (FA-3), the market regime the week
opened in, and *"timing context, not a signal — not investment advice."* If FA-2
finds no edge, **the card says so on its face.** That is the version worth
shipping; a card that hides a null result is a tip sheet.

## Action Taken / Plan

- ✅ Field assessment (2026-08-07) — this page. Rahu Kaal reproduced to the
  minute against the source card; the panchang layer confirmed fetch-free.
- ⏭ **FA-0** first, always — it is a live bug on a shipped page.
- ⏭ **FA-1**, then **FA-2 before FA-3.** Mapping planets to sectors *before*
  testing whether the underlying windows do anything is how this becomes
  astrology-flavoured stock tipping instead of a measured context layer.
- ⏭ FA-3 → FA-4 → FA-5 → FA-6.

**Sequencing note.** [[analyses/Astro-Weekly-Forecast-Card-Fit]] (AW-1…AW-4)
covers a *lunar/yoga day-event* card. This roadmap supersedes it in scope —
same renderer, same DB, but adds the intraday panchang layer and the sector/stock
join. AW-0 and FA-0 are the same item.

## Outcome (fill in later)

## Related Pages

- [[analyses/Astro-Weekly-Forecast-Card-Fit]] — the narrower card this extends
- [[analyses/Backtest-Harness]] — where FA-2 lands, and the reason FA-2 precedes FA-3
- [[analyses/Opportunity-Hub-Roadmap]] — supplies FA-4 entirely
- [[analyses/Dashboard-UI-Roadmap]] — the "context modifier, never a signal" position
