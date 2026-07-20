---
title: "Cafe Astrology — 2026 Ephemeris (annual tables + PDF)"
category: source
tags: [astrology, ephemeris, retrograde, void-of-course, eclipse, lunation, tropical, sidereal, out-of-bounds]
created: 2026-07-08
updated: 2026-07-08
sources: 1
related: [sources/AstroSeek-iCal-Planner]
---

# Cafe Astrology — 2026 Ephemeris (annual tables + PDF)

## Metadata
- **URL:** https://cafeastrology.com/2026-ephemeris.html
- **Site:** Cafe Astrology (cafeastrology.com), run by astrologer Annie; established free-content site.
- **Format:** Web page showing monthly tropical ephemeris tables as embedded Io-Software graphics; **full-year PDF** downloadable.
- **Copyright:** © 2002-2026 Cafe Astrology.
- **Cost:** Free.
- **Archive depth:** Year-by-year ephemerides available for **2005 → 2030**; asteroid ephemerides **2012 → 2027**; separate Declinations, Sidereal, Semi-sextile, and Black Moon Lilith/Selena ephemerides.
- **Timezone:** Midnight Eastern Time (with caveat — the March PDF is EDT for the full month, November PDF is EST for the full month, so DST-boundary days should be shifted by one hour per user's local convention).
- **Date accessed:** 2026-07-08.

## What This Source Provides
The core 2026 ephemeris page renders monthly tables (Io Software graphics — not extractable as text, download the PDF for machine-readable form) showing, per day:

- **Daily tropical longitudes** for Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, and the North Node.
- **Sign ingresses** (planets or bodies changing sign) — separate table for planetary ingresses.
- **Planetary stations** — precise date/time each planet turns retrograde (Rx) or direct (D).
- **Lunar sign ingresses** — separate from planetary due to frequency.
- **Void Moon times.**
- **Lunar phases** — New / First Quarter / Full / Last Quarter with dates, times, and zodiacal positions.
- **Eclipses** — solar or lunar, when present in a given month, with date and position.

Adjacent pages linked from this ephemeris (worth knowing for future ingests):
- **Retrograde Cycles / Stations** — dedicated retrograde tables.
- **Eclipses: Tables** — multi-year eclipse tables.
- **Lunations: Tables** — multi-year lunation (New/Full Moon) tables.
- **Declinations Ephemeris** + **Out of Bounds: Dates Table** — planet declinations beyond ±23°26′ (a *distinct concept* from longitude, worth its own concept page — see follow-up below).
- **Sidereal Ephemeris** — sidereal-zodiac version of the same data (matches use case for Vedic/Lahiri workflows).
- **Semi-sextile Ephemeris.**
- **Asteroid Ephemeris** (Ceres, Juno, Vesta, Pallas) and **Black Moon Lilith / Selena Ephemeris.**
- **Lunar Cycles Graph** (Io Software graphic).
- **Best Days of the Month / Best Days Summary / Good Days for Electing Activities** — pre-computed electional astrology day lists.

## Cross-reference vs [[sources/AstroSeek-iCal-Planner]]
Both sources cover the same event universe (planet longitudes, ingresses, stations, lunations, eclipses, VoC), differ in *consumption model*:

| Aspect | Astro-Seek | Cafe Astrology |
|--------|-----------|---------------|
| Delivery | Live `.ICS` feeds (subscribable) | Static monthly tables + full-year PDF |
| Integration | iOS / Outlook / Google Calendar | Offline reference / manual scan |
| VoC variants | 3 explicit (Modern/Traditional/Hellenistic + Benefic Enclosures) | Single "Void Moon" definition (not specified — likely Modern default) |
| Sidereal | 20+ ayanamsa options incl. Lahiri | Separate "Sidereal Ephemeris" page (single system) |
| Out of Bounds | Not exposed as a feed | Dedicated **Out of Bounds: Dates Table** ★ |
| Asteroid coverage | Basic | Rich — Ceres/Juno/Vesta/Pallas/Chiron + Lilith/Selena |
| Personal calendars | Yes (Solar Return, Profections, ZR) | No |

★ **Out of Bounds** is the specific concept Cafe Astrology exposes that Astro-Seek doesn't — a planet is "out of bounds" when its declination exceeds ±23°26′ (the Sun's max declination). Financial-astrology traders sometimes use OOB Mercury / Mars windows as volatility / extremes filters. This is our first mention of OOB in the wiki — flagged for a concept page.

## Actionable Insights

### Second cross-check source for the local astro engine
For the calibration diff flagged in [[sources/AstroSeek-iCal-Planner]] (VoC + retrograde stations against our local engine), **use Cafe Astrology as the second independent source**. Three-way triangulation:

- **Retrograde/Direct stations** → date/time should match to the minute across all three (our engine, Cafe Astrology PDF, Astro-Seek annual feed). Any drift is a bug in our engine.
- **Lunations (New/Full Moon)** → same. If our lunar_phases.py output differs from both external sources by > 1 min, calibrate.
- **VoC start/end times** → will *differ by definition* between sources. Astro-Seek exposes the three definitions explicitly; Cafe Astrology uses one (probably Modern). Match our engine's output to whichever of the three Astro-Seek variants it agrees with — that tells us which definition we implement.
- **Ingresses** → these are astronomical, should match exactly.

### Backup / offline reference
The **full-year PDF download** makes this a good offline reference for a trading desk. In the event the internal astro engine is offline or being refactored, the PDF is a hand-usable fallback for the day's ingresses, stations, and lunations.

### Out of Bounds — new concept for the wiki
Out of Bounds (planet declination > ±23°26′) is a technique category we haven't captured. Uses in trading-astro literature:
- **OOB Mercury** → outsized information / news impact windows
- **OOB Mars** → volatility spikes / momentum extremes
- **OOB Venus** → outsized moves in inflation-sensitive / consumer names
- **Sun OOB is impossible** (defines the boundary), so no such filter.

Cafe Astrology's "Out of Bounds: Dates Table" is the ready-made input for building this filter.

### Historical archive value
Cafe Astrology's 2005-2030 year-by-year ephemerides plus its 2012-2027 asteroid ephemerides give us **~20 years of clean historical astro tape** for backtesting reversal-calendar signals against price. Combined with our existing `reversal_calendar.py` output, this enables event-study back-tests (e.g. Nifty behaviour on OOB-Mars days vs baseline).

## Contradictions with Existing Wiki
- Timezone: Cafe Astrology is Midnight ET; Astro-Seek defaults are user-timezone. When cross-checking, convert both to a common frame (UTC recommended) before diffing.

## Pages Updated
- Created: `wiki/sources/CafeAstrology-Ephemeris.md` (this page)
- Updated: `wiki/index.md`, `wiki/log.md`
- Cross-links added to: [[sources/AstroSeek-iCal-Planner]] (companion cross-check target)

**Flagged (not created this ingest):**
- `concepts/Out-of-Bounds-Planets.md` — new concept, not in wiki yet. Definition, financial-astrology usage, data source (this page's OOB table).
- `analyses/Astro-Engine-Cross-Check.md` — extend the diff plan from Astro-Seek to also include Cafe Astrology PDF as a second independent oracle.
