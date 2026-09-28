---
title: "Astro-Seek — Digital Astrology iCal Planner"
category: source
tags: [astrology, ical, calendar, moon, transits, retrograde, void-of-course, sidereal, financial-astrology]
created: 2026-07-08
updated: 2026-07-08
sources: 1
related: [sources/OptionTools-in, sources/PreMarketTool-repo]
---

# Astro-Seek — Digital Astrology iCal Planner

## Metadata
- **URL:** https://horoscopes.astro-seek.com/digital-astrology-calendar-planner
- **Site:** Astro-Seek.com (established free astrology calculator platform)
- **Format:** Web tool — generates downloadable `.ICS` (iCalendar) feeds for import into iOS Calendar, Outlook, Google Calendar.
- **Cost:** Free.
- **Access:** No login required for mundane calendars; personal calendars need natal chart input.
- **Date accessed:** 2026-07-08.

## What This Tool Does
Exports astrological event feeds as `.ICS` files so they show up as native calendar events alongside meetings and deadlines. For traders who already use astro-timing overlays, this puts the events *where they'll actually be seen* — the phone/desktop calendar — without needing to open the dashboard.

## Mundane (World) iCal Feeds — Downloadable Categories

### Moon (monthly feeds)
- **Moon Aspects + Moon Sign Ingresses** — every aspect and sign-change
- **Moon Aspects only** — narrower feed for aspect-only workflows

### Full Moons, New Moons, Eclipses (annual)
- Consolidated feed of all lunations plus solar/lunar eclipses for the year

### Void of Course Moon — three variants
- **Modern VoC** — 10 planets (Sun through Pluto). Widest definition, most VoC windows flagged.
- **Traditional VoC** — 7 classical planets (Sun through Saturn). Fewer, more selective windows.
- **Hellenistic VoC** — > 30° orb definition. Narrowest, most restrictive.
- **Benefic Enclosures** — separate feed for Jupiter/Venus enclosures.

### Sun / Planet events (annual)
- **Sun Zodiac Signs** — each seasonal ingress
- **Planet Conjunctions** — the biggest slow-moving-planet meetings
- **Planet Major aspects** — squares/trines/oppositions between the outer set
- **Planet Ingresses** — every sign-change for every planet
- **Retrograde / Direct planets** — Rx station-in and station-direct dates

### Monthly Overall Summary
Consolidated "one feed for everything mundane" — Moon ingresses + lunations + planet aspects + planet ingresses + retrograde stations. This is the highest-signal single feed if you don't want to subscribe to five separate ones.

## Personal iCal Feeds (require natal chart)
- **Personal Transit Calendar** — 4 variants:
  - All transit planets, all aspects to natal
  - All transit planets + Moon, all aspects to natal
  - All transit planets + Moon, positions in natal houses
  - Single transit planet, all aspects to natal (annual)
- **Solar Return (SR) monthly revolutions**
- **Annual Profections + SR daily profections**
- **Zodiacal Releasing** — L1 / L4 periods (Hellenistic timing technique)

## Sidereal System Options
Rare and useful: the tool supports multiple ayanamsas so Vedic-oriented users can subscribe to the *sidereal* version of the same events. Options include:
- **Lahiri** (default for Indian Vedic astrology)
- Raman, Krishnamurti, Fagan-Bradley, De Luce, Larry Ely
- True Citra, True Mula, True Pushya, True Revati
- Aldebaran 15° Tau, Vettius Valens
- Multiple Galactic Center anchors (mid-Mula, 0° Sag / 0° Cap variants)
- J2000 / J1900 / B1950 astronomical epochs

For our stack, **Lahiri sidereal** is the one that matches the Vedic yoga / nakshatra logic already in `tools/yoga_dates.py` and `tools/reversal_calendar.py` (implied by our existing infra).

## Actionable Insights

### Cross-check for our internal astro engine
We already have local astro infra — `tools/astro_trading.py`, `tools/reversal_calendar.py`, `tools/lunar_phases.py`, `tools/yoga_dates.py`. Astro-Seek is an independent, established public source. Two immediate uses:
1. **Sanity-check our VoC calculations.** Modern vs Traditional vs Hellenistic VoC give three different answers; comparing our engine's output against Astro-Seek's three feeds triangulates our definition. If our engine matches "Traditional" (7 classical planets), that's a load-bearing calibration point.
2. **Retrograde station dates** — one small feed can be diffed against our local retrograde calc for verification.

### Calendar surface for pre-market prep
The pre-market stack we've built ([[sources/PreMarketTool-repo]] + [[sources/OptionTools-in]]) is dashboard-facing. Adding the **Monthly Overall Summary** iCal to Google Calendar puts astro-context (upcoming lunation, next Rx station, big transit) *in the same view* as market open times — no context-switch required. Zero cost to add.

### Trader-specific subset worth subscribing to
For financial-astrology trading, the useful subset is narrower than the full menu:
- **Monthly Overall Summary** (one feed catches most of what matters)
- **Retrograde / Direct planets** (annual — Mercury Rx / Mars Rx windows most cited in market lore)
- **Full Moons, New Moons, Eclipses** (annual — used in a lot of reversal calendars)
- Optional: **Modern VoC** (10 planets) if VoC is part of your entry-filter

Skip: personal transit feeds (unless natal is being run against a portfolio anchor, which is out of scope for this wiki), Zodiacal Releasing (technique-specific), Sun Zodiac Signs (only 12 events/year, rarely load-bearing).

## Related Local Tools (for cross-reference on future ingests)
- `tools/astro_trading.py` — internal astro-trading calc
- `tools/lunar_phases.py` — internal lunar-phase calc
- `tools/yoga_dates.py` — Vedic yoga occurrence calc
- `tools/reversal_calendar.py` — combines yoga + lunar into reversal-candidate days
- `tools/financial_astrology_methods.py` — internal method catalog

None of these have wiki entities/concepts pages yet — flagged as a follow-up ingest task.

## Contradictions with Existing Wiki
None — this is the first astrology/calendar-tool source ingested. Establishes the vocabulary (Modern/Traditional/Hellenistic VoC, sidereal ayanamsa options, Zodiacal Releasing) that future astro ingests should hew to.

## Pages Updated
- Created: `wiki/sources/AstroSeek-iCal-Planner.md` (this page)
- Updated: `wiki/index.md`, `wiki/log.md`
- **Flagged (not created this ingest):**
  - `concepts/Void-of-Course-Moon.md` — worth a dedicated concept page cross-linking the three definitions and pointing at both this tool and the internal engine
  - `concepts/Retrograde-Planets.md` — Mercury Rx / Mars Rx cycles as trading filters
  - `analyses/Astro-Engine-Cross-Check.md` — a one-time diff of our local engine's output against Astro-Seek's feeds for a fixed month, to calibrate our VoC/retrograde definitions
