---
title: "Astro Engine Cross-Check — Local Engine × Astro-Seek × Cafe Astrology"
category: analysis
tags: [astrology, calibration, cross-check, verification, ephemeris, void-of-course, retrograde, lunation]
timeframe: one-off (calibration)
created: 2026-07-08
updated: 2026-07-08
sources: 2
related: [sources/AstroSeek-iCal-Planner, sources/CafeAstrology-Ephemeris, concepts/Out-of-Bounds-Planets]
---

# Analysis: Astro Engine Cross-Check — Local Engine × Astro-Seek × Cafe Astrology

## Thesis
The local astro engine (`tools/lunar_phases.py`, `tools/yoga_dates.py`, `tools/reversal_calendar.py`, `tools/astro_trading.py`) has never been calibrated against an external oracle. With two independent public sources now on the wiki ([[sources/AstroSeek-iCal-Planner]] and [[sources/CafeAstrology-Ephemeris]]), we can run a **three-way triangulation** to (a) find any drift bugs in the local computations, (b) identify which of the three canonical Void-of-Course definitions our engine implements, and (c) build the confidence needed to run event-studies against price using our own tape.

This is a **one-off calibration analysis** — not a recurring task. Once done, the results should shift into a wiki concept/reference page, and the outcome dictates whether we trust the local engine as-is or need targeted patches.

## Evidence For (why cross-check now)
- **Two external oracles now available**, both free, both established (Astro-Seek since ~2010s, Cafe Astrology since 2002). Triangulation is possible with zero paid data.
- **PyEphem is the underlying computation for all local astro tools** — a single library bug (or version mismatch, or timezone regression) would affect *every* downstream output uniformly. Cross-checking against sources that use different back-ends (Astro-Seek uses Swiss Ephemeris, Cafe Astrology uses Io Software) isolates any PyEphem-specific drift.
- **[[sources/OptionTools-in]] + reversal-calendar output are already being combined into daily reads** (see [[analyses/Nifty-Options-EOD-20260707]]). If the reversal calendar is subtly off, every future confluence read inherits the error.
- **VoC is definition-ambiguous.** Modern (10-planet), Traditional (7-planet), and Hellenistic (>30° orb) all give different VoC start/end times for the same day. Our engine implements *one* of them; we don't know which. Astro-Seek exposes all three as separate feeds — a direct match on any of them tells us which definition we're using.

## Evidence Against (why this might not matter yet)
- The reversal calendar is a **coincidence-count filter**, not a precision-timing engine — many downstream uses only need day-level accuracy. A 3-minute drift on a lunation time doesn't change which calendar day the event lands on.
- The local engine's yoga logic pulls from Drik Panchang (not computed locally) — Drik's dates are authoritative for the yogas, so no calibration needed there.
- If the answer is "everything matches," we spend an hour to confirm nothing. Small downside.

## Conclusion — plan to run

### Scope: one calendar month, one anchor timezone
- **Test month:** July 2026 (current month, easy to sanity-check by eye).
- **Anchor timezone:** UTC for all three sources. Convert Cafe Astrology (native ET) and any local-tz outputs from our engine to UTC before diffing.
- **Deliverable:** a diff table for each event category. Discrepancies documented per row; pass/fail per category.

### Category 1 — Planetary retrograde/direct stations (highest calibration value)
Stations are *precise instants*. All three sources should agree to the minute.

| Source | Where |
|---|---|
| Local | `tools/astro_trading.py` (PyEphem-based) — extend if needed to emit precise station times |
| Astro-Seek | Annual iCal: Retrograde/Direct planets |
| Cafe Astrology | 2026 Ephemeris PDF, "Stations" table |

**Pass criterion:** all three agree to within ±2 minutes.
**Fail action:** > 5 min drift = investigate PyEphem version / Δt correction / equation-of-time handling.

### Category 2 — Lunations (New Moon / Full Moon)
Same precision expectation as stations.

| Source | Where |
|---|---|
| Local | `tools/lunar_phases.py` `lunar_events_for_range()` |
| Astro-Seek | Annual iCal: Full Moons, New Moons and Eclipses |
| Cafe Astrology | 2026 Ephemeris page, "Lunar Phases & Eclipses" table |

**Pass criterion:** agree to ±2 minutes.
**Fail action:** debug lunar-phase solver.

### Category 3 — Planet sign ingresses
Astronomical, deterministic.

| Source | Where |
|---|---|
| Local | *Not currently computed* — this diff also tells us whether to add ingress emission to the reversal calendar |
| Astro-Seek | Annual iCal: Planet Ingresses |
| Cafe Astrology | "Ingresses" table in monthly ephemeris |

**Pass criterion:** the two external sources should agree exactly. If they do, we have a reference; adding local ingress computation is straightforward via PyEphem.

### Category 4 — Void-of-Course Moon (definition-identifier)
The **most valuable diff** because it's the only one that reveals a design decision, not just a bug.

| Source | Where | Definition |
|---|---|---|
| Astro-Seek variant 1 | Monthly iCal: Modern VoC | 10 planets Sun-Pluto |
| Astro-Seek variant 2 | Monthly iCal: Traditional VoC | 7 planets Sun-Saturn |
| Astro-Seek variant 3 | Annual iCal: Hellenistic VoC | >30° orb |
| Cafe Astrology | Monthly ephemeris "Void Moon" column | Not specified (likely Modern) |
| Local | If our engine emits VoC events, compare against all three | ? |

**Pass criterion:** local engine matches *at least one* of Astro-Seek's three variants on all July 2026 VoC windows.
**Fail action:** if no match on any of the three, our engine implements a fourth (or custom, or buggy) definition — document what it actually does.

### Category 5 — Out of Bounds transitions (new category, per [[concepts/Out-of-Bounds-Planets]])
Since we don't yet emit OOB, the diff is **local vs Cafe Astrology only** (Astro-Seek doesn't expose OOB).

| Source | Where |
|---|---|
| Local | *Not currently computed* — extend `reversal_calendar.py` to emit OOB start/end events per Moon/Mercury/Venus/Mars using PyEphem `body.dec` |
| Cafe Astrology | "Out of Bounds: Dates Table" |

**Pass criterion:** OOB start/end dates match Cafe Astrology's table to the day.
**Fail action:** debug declination computation (unit / epoch / obliquity of the ecliptic).

## Action Taken / Plan
- **Owner:** deferred — user-driven kick-off. Approx 60-90 min of work for a full first-pass diff.
- **Steps:**
  1. Download Cafe Astrology's July 2026 PDF ephemeris page.
  2. Subscribe to (or one-shot download) the three Astro-Seek VoC iCal feeds + Retrograde iCal + Lunations iCal.
  3. Run local engine over July 2026 UTC range, emit CSV per event category.
  4. Manual diff (small enough for one month) → tabulate results into a follow-up wiki page: `analyses/Astro-Engine-Cross-Check-Results-2026-07.md`.
  5. If any category fails, file a `wiki/log.md` entry and a targeted issue for the engine.
- **Nice-to-have extension:** once the base diff is clean, extend to a **twelve-month diff for 2026** to catch any date-dependent drift (leap-year edge, DST boundary handling in Cafe Astrology's March/November ET representations, etc.).

## Outcome (fill in later)
_To be completed after the diff is run. Placeholder for the per-category pass/fail matrix and any drift documented._

## Related Pages
- [[sources/AstroSeek-iCal-Planner]] — primary calibration oracle #1 (three VoC variants make this the most useful VoC source).
- [[sources/CafeAstrology-Ephemeris]] — primary calibration oracle #2 (only source with OOB table).
- [[concepts/Out-of-Bounds-Planets]] — the OOB category to add to the local engine as part of this calibration.
