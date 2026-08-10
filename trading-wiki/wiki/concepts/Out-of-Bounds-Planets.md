---
title: "Out of Bounds Planets (OOB)"
category: concept
tags: [astrology, declination, out-of-bounds, oob, financial-astrology, volatility]
created: 2026-07-08
updated: 2026-08-09
sources: 2
related: [sources/CafeAstrology-Ephemeris, sources/AstroSeek-iCal-Planner, sources/BlueprintResearch-Path-of-the-Planets-Pine, concepts/Panchang, analyses/FA-2-Rahu-Kaal-Measured]
---

# Out of Bounds Planets (OOB)

## Definition
A planet is **Out of Bounds (OOB)** when its **declination** (angular distance north or south of the celestial equator) exceeds the Sun's maximum declination of **±23°26′** (the tropic latitudes — Cancer +23°26′, Capricorn −23°26′). By definition the Sun is never OOB; it *defines* the boundary. Every other body — Moon, Mercury, Venus, Mars, and occasionally the outer planets — can go OOB during specific windows in their orbital cycles.

- **Declination ≠ latitude:** declination is measured from the celestial equator, not the ecliptic. Two planets can share a longitude (conjunct) yet have very different declinations.
- **OOB is a *distinct filter* from longitude, sign, or aspect** — a planet can be in mid-Cancer *and* OOB, or on a major aspect *and* OOB. The states compound rather than replace each other.
- **Threshold:** the classical threshold is ±23°26′. Some contemporary astrologers use ±23°28′ or the exact declination for the Sun on a given date, but the ±23°26′ line is the standard.

## How to Use
Financial-astrology traders treat OOB windows as **regime modifiers** — not entry signals in themselves, but tape-widening amplifiers on whatever setup is already in play. Rule of thumb: **an OOB period is when the planet "gets away with more."** The planetary archetype expresses more extremely than baseline.

### Per-planet playbook (from financial-astrology literature)
- **Mercury OOB — outsized news / information windows.** Rumours, guidance shocks, mid-cycle guidance revisions, gap opens on headline flow. Watch for reactive gap-and-go setups; discount narrative smoothing. Common for Mercury OOB windows to line up with earnings-season volatility spikes.
- **Mars OOB — volatility spikes / momentum extremes.** Trend continuation setups run further than expected; reversal-fade setups blow up more than usual. Position size *smaller* not bigger; the tape has more range but also more whipsaw.
- **Venus OOB — outsized moves in consumer / inflation-sensitive / luxury / commodity names.** Look for FMCG, jewellery, discretionary retail (TRENT/TITAN/KALYANKJIL cohort) reacting on wider bands. Also historically associated with sugar, cocoa, precious metals.
- **Moon OOB — Moon spends part of every month OOB; the monthly OOB days are watched for intraday volatility spikes.** Less strategic (recurs every month), more tactical.
- **Outer planets OOB (Jupiter/Saturn/etc.)** — rare, multi-year. When they occur they're context, not tactical trigger.

### Combining OOB with other signals
- **OOB + Retrograde** → double amplification; classic "expect the tape to overshoot in both directions" regime.
- **OOB + station (Rx or D)** → volatility concentration around the station date is heightened.
- **OOB + eclipse** → if the OOB planet is involved in the eclipse chart, treat the eclipse as *high-conviction* regime shift.

## Variants / Parameters
- **Strict definition:** declination > ±23°26′.
- **Extended OOB / "far out of bounds":** declination > ±25°, used by some traders as a stronger filter. Extremely rare for anything but the Moon.
- **In vs out of bounds transitions:** the specific *day* a planet crosses the ±23°26′ line in either direction is the "OOB begins" or "OOB ends" date. Both dates are event candidates for the reversal calendar.
- **Sidereal vs tropical:** OOB is a *declination* concept (astronomical), independent of the zodiac system. Same OOB dates apply whether the trader uses tropical (Cafe Astrology default) or sidereal (Vedic/Lahiri) longitudes.

## Common Mistakes
- **Confusing declination with latitude.** They're different measurements. OOB uses declination.
- **Treating OOB as a trade signal.** It's a *regime modifier*, not an entry trigger. Enter on your usual setup; adjust sizing / target / stop based on OOB context.
- **Ignoring that Sun is never OOB.** Every list of OOB planets excludes the Sun — this is not an omission.
- **Assuming OOB is rare.** Moon goes OOB ~11 days each month (roughly). Mercury/Venus/Mars go OOB in multi-week windows periodically. Only the outer planets going OOB is genuinely rare.
- **Chasing OOB windows without a baseline.** The right question is *"how did this same setup behave on non-OOB days for comparable price/regime?"* — not *"OOB is happening, therefore go bigger."*

## Related Concepts
- [[concepts/PMax]] and [[concepts/EMA]] — the *setup* layer OOB modulates. OOB doesn't replace them, it amplifies their read.
- [[concepts/Multi-Timeframe-Analysis]] — OOB is a *daily/date-based* filter that combines cleanly with intraday TA.
- [[concepts/Mercury-Retrograde-Market-Cycle]] — the *other* Mercury filter: apparent motion (retrograde/direct) vs OOB's declination. Distinct states that can co-occur and compound; same "regime modifier, not signal" discipline.
- Lunations and eclipses — OOB near a lunation/eclipse is a heightened-conviction context.

## Examples in This Wiki

> [!key-insight] Declination is computable here as of 2026-08-09 — this page waited a month for it
> [planet_positions.py](tools/planet_positions.py) ships `out_of_bounds(when, bodies)` for all ten bodies. Before that, **declination had zero occurrences repo-wide** — this page had existed since 2026-07-08 describing a concept nothing could calculate, and its own "Examples" section said *"worth checking once the local engine can compute declination."*
>
> Live at 2026-08-09: **Moon +26.84° and Mars +23.65° are both out of bounds.** Mars only marginally, which is itself instructive — a body sitting within ~0.2° of the limit will flicker in and out, so any event study needs a **minimum-duration or hysteresis rule** rather than a bare threshold test.
>
> Note the threshold: this page used **23.4344°**, the module uses **23.4392911°** (the J2000 mean obliquity, and the Sun's own maximum declination — which is what makes the limit meaningful). The ~0.005° difference cannot change a verdict except for a body sitting exactly on the boundary, but the two should be reconciled to one constant.

- No historical OOB event studies yet — the wiki has no back-tested OOB × Nifty statistics. First candidate for study: an event-study of Nifty realised volatility on OOB-Mars vs non-OOB baseline over 2015-2025, using [[sources/CafeAstrology-Ephemeris]]'s Out of Bounds Dates Table as the input.
- The current NIFTY tape (2026-07-07/08) is a candidate qualitative test: [[analyses/Nifty-Options-EOD-20260707]] flagged a downgrade to "range-with-downside-tilt" with high confidence. If that period coincides with an OOB Mercury or Mars window, that's a data point supporting OOB-as-volatility-amplifier — worth checking once the local engine can compute declination.

## Data Sources
- [[sources/CafeAstrology-Ephemeris]] — has a dedicated **"Out of Bounds: Dates Table"** ready-made for import. First-choice source for the OOB filter.
- [[sources/AstroSeek-iCal-Planner]] — does *not* expose OOB as a feed. Use for cross-checking longitudes/stations/lunations, not for OOB.
- **Internal engine — SHIPPED 2026-08-09** as [planet_positions.py](tools/planet_positions.py), not in `reversal_calendar.py` as planned: `out_of_bounds(when, bodies)` over all ten bodies, with per-planet selection. The transition-day event emission described below is still **not** built — the module answers "is it OOB now", not "when did it start". Original plan text: PyEphem exposes body declination via `ephem.Body.dec` in radians; adding OOB computation to `tools/reversal_calendar.py` is a small extension — for each day, check whether abs(dec) > 23.4344° for each of Mercury/Venus/Mars/Moon and emit an "OOB start"/"OOB end" event on the transition days.

## Sources
- [[sources/CafeAstrology-Ephemeris]] — primary reference; ready-made OOB Dates Table.
- [[sources/AstroSeek-iCal-Planner]] — companion astro source (does not cover OOB, useful for cross-checking longitudes).
