---
title: "Panchang (Hora · Rahu Kaal · Nakshatra · Tithi · KP Sub-lord)"
category: concept
tags: [panchang, astro, financial-astrology, hora, rahu-kaal, nakshatra, pada, tithi, sub-lord, kp, ephem, morning-brief]
created: 2026-08-09
updated: 2026-08-09
sources: 2
related:
  - analyses/Financial-Astrology-Sector-Week-Roadmap.md
  - analyses/Astro-Weekly-Forecast-Card-Fit.md
  - analyses/Backtest-Harness.md
  - concepts/Mercury-Retrograde-Market-Cycle.md
  - concepts/Market-Sentiment-Index.md
  - concepts/Out-of-Bounds-Planets.md
---

# Panchang (Hora · Rahu Kaal · Nakshatra · Tithi · KP Sub-lord)

## Definition
The **panchang** is the Vedic almanac for a day at a place. The elements this repo computes:

| Element | What it is |
|---|---|
| **Sunrise / sunset** | Drives everything below; the Hindu day runs sunrise-to-sunrise, not midnight-to-midnight |
| **Rahu Kaal** | One of 8 equal divisions of sunrise→sunset, assigned by weekday. Traditionally inauspicious for beginnings |
| **Yamaganda · Gulika** | Two more 1/8 windows on the same mechanism, different weekday tables |
| **Hora** | Planetary hours — 12 equal blocks across the day and 12 across the night, each ruled by a planet in **Chaldean order** starting from the weekday's ruler. Seasonal, so a "hora" is rarely 60 clock minutes |
| **Nakshatra + pada** | The Moon's sidereal position: 27 lunar mansions of 13°20', each split into 4 padas of 3°20' |
| **Tithi** | Lunar day — Moon-minus-Sun elongation in 12° steps, 30 per lunation, with **paksha** (Shukla waxing / Krishna waning) |
| **Sub-lord (KP)** | Krishnamurti Paddhati subdivision: Vimshottari dasha proportions applied *inside* one nakshatra |
| **Retrogrades** | Which planets are moving backwards in longitude |

## How to Use
In this repo, **as displayed context on the Morning Market Brief and nothing more.** The panchang is printed as fact: these are the day's windows, exact and known in advance. No entry, exit, or bias is derived from them.

That restraint is deliberate and is the repo's stated position ([[analyses/Dashboard-UI-Roadmap]] Phase 3): scope the astro vertical as a regime/context modifier, **never** a standalone entry signal. The honest way to hold that line is a measurement, not a cautious caption — and the measurement has not been run (see below).

## Variants / Parameters
- **Place** — sunrise/sunset are location-dependent, so every window is. Default is Mumbai (NSE/BSE); `panchang.Place` takes any lat/lon.
- **Ayanamsa** — the sidereal/tropical offset that converts an ecliptic longitude into a nakshatra. `panchang.py` uses a **Lahiri linear approximation** (23.85° at J2000 drifting at ~50.29″/yr → ~24.22° in 2026), good to roughly an arc-minute. Nakshatras are 13°20' wide and padas 3°20', so an arc-minute cannot move a nakshatra and shifts a pada boundary by well under a minute of clock time. Not suitable for anything needing finer precision.
- **Sunrise convention** — the standard −0:34 refraction horizon with `pressure = 0`. This is what published Indian panchangs use, and it is what makes the verification below land on the minute rather than a few minutes out.
- **Weekday at sunrise, not midnight** — because the Hindu day begins at sunrise. Gets the day-part and hora tables right for early-morning timestamps.

## Common Mistakes
- **Mixing J2000 and of-date ecliptic longitudes.** `ephem.Ecliptic` defaults to J2000 while an ayanamsa is defined against the ecliptic *of date*. Omitting `epoch=` leaves the intervening precession in the answer — ~0.36° by 2026, about **40 minutes of lunar motion** — which is enough to put a pada boundary in the wrong half-hour while looking entirely plausible. This bit the first implementation here; see Examples.
- **`ephem.localtime`.** It converts to the *machine's* timezone. On any non-IST host that silently yields nonsense (it produced a 20:43 "sunrise"). Convert UTC→IST explicitly.
- **Building hora blocks by repeated addition.** `start + length` twelve times accumulates rounding and drifts off the sunset seam. Compute boundaries once and pair them.
- **Treating a window as a signal.** The entire tradition asserts Rahu Kaal is inauspicious; nothing in this repo has tested it. Printing a directional call next to a clock time is how a context layer becomes a tip sheet.
- **Taking a vendor dependency.** Panchang APIs (ProKerala, VedicRishi, DrikPanchang) are mostly paid or rate-limited and return nothing that cannot be computed locally — a vendor adds a failure mode for no capability.

## Related Concepts
- [[concepts/Mercury-Retrograde-Market-Cycle]] — the one astro claim in this wiki with an actual cycle study attached; the retrograde flags here feed the same idea.
- [[concepts/Out-of-Bounds-Planets]] — another declination/longitude-derived astro context layer.
- [[concepts/Market-Sentiment-Index]] — the page the brief is rendered on; the composite gauge supplies the market-side tone.
- [[analyses/Backtest-Harness]] — where FA-2 must land before any of these windows earns interpretive language.

## Examples in This Wiki

### `tools/panchang.py` — shipped 2026-08-09 (roadmap FA-1)
Pure offline module: **no API, no login, no rate limit, no vendor.** `panchang(date, place, now)` returns every element in the table above in one call. Run `python tools/panchang.py` for the self-check.

> [!key-insight] Verified against a published card, to the minute
> For **Tuesday 2026-07-28, Mumbai**:
> - **Rahu Kaal → 16:00–17:38 IST.** The published card printed 04:00 PM – 05:38 PM.
> - **Nakshatra → Purva Ashadha pada 3 at 05:30, rolling to pada 4 at 06:31.** Same card, same transition.
>
> Both exact. Those two references live in `verify()` inside the module, because **the failure mode here is plausible wrong answers, not exceptions** — the precession bug above put the pada transition at 07:15 and looked perfectly reasonable in isolation. Tithi passed throughout while nakshatra was wrong, which is what identified the cause: tithi is a *difference* of two longitudes, so precession cancels.

**Moon phase is deliberately absent from this module.** `astro_trading.AstroIndicators.get_lunar_phase()` owns it via the `reversal_calendar` store, and `panchang()` delegates. Two surfaces disagreeing about the moon would invalidate anything built on either.

> [!warning] The roadmap's FA-0 blocker is stale — it was already fixed
> [[analyses/Financial-Astrology-Sector-Week-Roadmap]] lists FA-0 (`get_lunar_phase` broken three ways, live on the Astro Timing page) as a **non-negotiable prerequisite**. It was fixed on **2026-08-02**, five days before that roadmap was written: `_lunar_phase_approximate` is gone and both paths route through `_lunar_phase_from_calendar`. Verified 2026-08-09 — it returns `{'phase': 'new', 'illumination': 14.41, 'source': 'ephem'}` for 2026-08-09 and `full`/99.95% for the 2026-07-29 full moon. **FA-1 was therefore not blocked.** That roadmap should be corrected when it is next touched.

### `tools/market_brief.py` + the Morning Market Brief section
Renders on the **Market Sentiment** page: global quote strip, constituent-based sector breadth, the full panchang, and the existing composite reading. Modelled on a published morning-brief card, with two deliberate departures documented in [[analyses/Market-Brief-Card]].

## Sources
1. `tools/panchang.py` self-verification against a published panchang card for 2026-07-28 (Rahu Kaal window and nakshatra pada transition, both to the minute). Standard weekday tables for Rahu Kaal / Yamaganda / Gulika, Chaldean hora order, Vimshottari proportions for nakshatra lords and KP sub-lords.
2. [[analyses/Financial-Astrology-Sector-Week-Roadmap]] (2026-08-07) — established that the whole panchang layer is computable offline and that a vendor dependency is not worth taking; specifies FA-1, which this implements. **Its FA-0 prerequisite is stale, see the warning above.**
