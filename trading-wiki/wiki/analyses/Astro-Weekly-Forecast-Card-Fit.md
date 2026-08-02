---
title: "Astro Weekly Forecast Card — Fit Assessment (good-to-have)"
category: analysis
tags: [roadmap, astro, lunar, yoga, reversal-calendar, shareable-card, good-to-have, backlog]
timeframe: milestone-plan
created: 2026-08-02
updated: 2026-08-02
sources: 0
related: [analyses/Dashboard-UI-Roadmap, concepts/FPV-Flow-Price-Volume-Ownership]
---

# Analysis: Astro Weekly Forecast Card — Fit Assessment — 2026-08-02

**Verdict: feasible, ~85% composition, and it should be built on `reversal_calendar` — not on `astro_trading`. Filed as good-to-have; nothing here is urgent.**

> [!key-insight] The assessment found a live bug, and it decides the design
> `astro_trading.get_lunar_phase()` is **wrong in three independent ways** and is currently the only lunar path in the repo that runs, because PyEphem is not installed. It reports the **full moon of 2026-07-29 as "waning, 16.7% illuminated"**, and calls 2026-08-08 "**new**" at **99.3% illumination** — a flat self-contradiction. Meanwhile `reversal_calendar.db` holds the correct PyEphem-derived events (New 2026-07-14, Full 2026-07-29, New 2026-08-12, Full 2026-08-28). **Two astro surfaces in the same dashboard would disagree about the moon.** Any card must source from the DB.

## Thesis

A weekly astro forecast card is the natural companion to the sector-breadth card shipped 2026-08-02 ([sector_card.py](tools/sector_card.py)): same shape — a `build_model` → `render_png` / `render_text` pair — over a different dataset, producing something postable rather than another interactive panel that never leaves the tab.

Unlike most feature requests here, the data already exists **and points forward**, which is what makes a *forecast* card possible at all rather than a retrospective one.

## Evidence For — what already exists (verified live 2026-08-02)

| Piece | Status | Where |
|---|---|---|
| Yoga + lunar event store | ✅ **278 events, 2026-01-03 → 2027-12-28** | `reversal_calendar.db` (102 KB, populated) |
| Events for an arbitrary week | ✅ `events_in_range(start, end)` | [reversal_calendar.py](tools/reversal_calendar.py) |
| Per-day clustering score | ✅ `coincidence_scores(start, end)` | same |
| Weekly iteration helper | ✅ `get_weekly_calendar(start, days=7)` | [astro_trading.py](tools/astro_trading.py) — *but see the caveat* |
| Card renderer pattern | ✅ shipped | [sector_card.py](tools/sector_card.py) — Pillow, no new dependency |
| Palette + typography | ✅ | [report_style.py](tools/report_style.py) |
| Chart overlay for the same events | ✅ shipped | `reversal_calendar` indicator in [chart_dashboard.html](tools/chart_dashboard.html) |
| Dashboard surface | ✅ | **Astro Timing** page |

Typical week carries **2–4 events** (measured across the next 8 weeks), so a card has content without being noise. Categories break down as 199 auspicious yoga · 50 lunar phase · 29 nakshatra yoga.

## Evidence Against — three real obstacles

1. **`astro_trading._lunar_phase_approximate` is broken, and it is the live path.** `HAS_EPHEM` is `False` — `ephem` is not installed — so every call falls through to the approximation. Measured against the DB's own dates:
   - **The epoch is wrong.** It anchors on `date(2024, 1, 29)` as a new moon. It is not one; 2024-02-09 is. The error shows up as a constant **~10.8-day offset** — true new moons compute to `cycle_day` 11.10 and 10.57 instead of ~0.
   - **The illumination formula is a quarter-cycle out of phase.** `100·sin(2π·c/29.53)·0.5 + 50` yields **50% at new, 100% at first quarter, 50% at full, 0% at last quarter**. It should be `50·(1 − cos(2π·c/29.53))` → 0 / 50 / 100 / 50. As written it reports the new moon and the full moon as identically half-lit.
   - **Even corrected, a fixed 29.53-day mean synodic month drifts.** With the epoch fixed, 2026-07-14 and 2026-07-29 land correctly (`new` 0.0% / `full` 99.9%), but 2026-08-12 still reads `waning` at cycle 29.1 — 0.4 days short of wrapping. Real lunations vary by hours; over 2.5 years the drift reaches ~±1 day.
   - **Conclusion: do not fix the approximation and build on it. Read the DB.** The exact timestamps are already there.
2. **The DB cannot currently be rebuilt.** `lunar_phases.py` needs `ephem`, which raises `ModuleNotFoundError` on this machine. The existing DB covers to **2027-12-28**, so there is ~17 months of runway, but extending it needs `pip install ephem`. That is a prerequisite with a deadline, not a blocker today.
3. **The framing risk is the whole point of the caution.** [[analyses/Dashboard-UI-Roadmap]] Phase 3 already states the position: *scope the Astro vertical as a regime/context modifier, **never** a standalone entry signal.* A shareable card is exactly the format that invites being read as a prediction, and it will be posted where that context is absent. This is the same overtrust shape the M3 projection guardrails were built for.

## Conclusion — sequence (good-to-have, unscheduled)

**AW-1 — `astro_week.py` model (~2 h).** Pure module, no Streamlit, mirroring `sector_card`'s split. `build_model(start, end)` reads `reversal_calendar.events_in_range` + `coincidence_scores` and returns `{week, days[], events[], peak_day, counts_by_category}`. **Lunar comes from the DB only.** Days with no event render as "nothing scheduled" rather than being omitted — a quiet day is a finding.

**AW-2 — card renderer (~2 h).** `render_png` / `render_text` reusing `report_style` tokens and the Pillow layout already proven at 1080px. Seven day-columns, event chips coloured by category, the coincidence peak marked. Tone rules carry over: a day with no data must not look like a calm day.

**AW-3 — Astro Timing surface + download (~1 h).** Preview, PNG download, copy-as-text, week picker. Pure composition once AW-1/AW-2 land.

**AW-4 — the honesty layer, and it is not optional (~1 h).** Rendered *into* the PNG, not just the page, because the image travels alone: "context/timing only, not a signal — not investment advice", the event count the week actually had, and the DB's coverage end date so a stale card cannot be mistaken for a current one.

**AW-0 (prerequisite, separable) — decide `astro_trading.get_lunar_phase`.** Either fix it (epoch → 2024-02-09, illumination → `50·(1−cos …)`) or, better, make it delegate to `reversal_calendar` and delete the approximation. It is wrong on the **Astro Timing page today**, independently of whether this card is ever built.

### Recommended order
**AW-0 → AW-1 → AW-2 → AW-3 → AW-4.** AW-0 first because it is a live wrong number on a shipped page, and because leaving two contradictory lunar sources in the repo guarantees the card eventually gets wired to the wrong one.

## Action Taken / Plan
- **Nothing built.** Assessment only; every probe was read-only.
- **Priority: good-to-have.** Behind SR-1…SR-5 follow-ups and anything on [[analyses/Dashboard-UI-Roadmap]] Phase 3. AW-0 is the exception — it is a bug, not an enhancement.
- **Budget:** AW-1…AW-4 ≈ 6 h. AW-0 ≈ 30 min.

## Outcome (fill in later)
- *2026-08-02:* Assessment written. Verified: DB populated to 2027-12-28 with 278 events ✅ · `events_in_range` / `coincidence_scores` / `get_weekly_calendar` all present ✅ · card renderer pattern proven ✅ · **`get_lunar_phase` wrong on epoch, illumination and drift** ❌ · **`ephem` absent so the DB cannot be rebuilt** ⚠️.
- **2026-08-02 — AW-0 SHIPPED. The moon on the Astro Timing page is now the moon in the calendar.** `_lunar_phase_approximate` is **deleted**, not repaired; `get_lunar_phase` reads `reversal_calendar.db` and interpolates between real new-moon instants. Before/after on the live page: **"New · 56% illuminated · cycle day 0.6" → "Waning · 78.1% · cycle day 19.0 of 29.0"** — 2026-08-02 is 4 days past the 29 Jul full moon and 19 days after the 14 Jul new moon, so the new reading is right on all three fields.
  - **Out-of-coverage now reads as unplaced.** Dates the DB does not cover return `phase: 'unknown'` with `None` figures, the page renders `—` plus an actionable warning, and `_generate_recommendations` says the lunar read is *absent, not neutral*. The old code extrapolated a mean cycle indefinitely and produced a confident number for any date at all — which is precisely how a full moon came to render as "waning, 16.7%".
  - **Two more bugs of the same family, found while verifying:**
    - `_calculate_market_intensity`'s interpolation used `50 + 30·sin(…)`, which **peaks at first quarter and sits at 50 on new and full** — the exact opposite of its own docstring and of the hardcoded branches it interpolates between. Now `abs(cos)`: 80 at new, 75 at full, ~52 at the quarters.
    - `_solar_timing_approximate` called `.astimezone()` on a **naive** datetime, so 6 AM was read in the *host machine's* zone and converted — the page was showing **sunrise 15:30 and sunset 03:30 IST**. Now `localize`; reads 06:00/18:00.
  - **The ephem path was wrong too, and is fixed although dormant.** It derived `cycle_day` as `(illumination/100)·29.53`, treating a cosine as a straight line and making day 7 and day 22 — both ~50% lit — collapse onto the same answer. It now measures from `previous_new_moon`.
  - **A labelling subtlety the test caught:** quadrant labels must be **centred** on the events they name, not started at them. With start-aligned bands a full moon landing at fraction 0.483 (any 29-day lunation whose full moon falls on day 14) was labelled `waxing` while its own illumination read 99.7%. **11 of 44** DB events were mislabelled that way; centred bands give **0 of 44**.
  - **Verified:** 6-part self-check passes — the four previously-wrong dates, **all 44 DB lunar events agreeing**, illumination monotone rising new→full, out-of-coverage returning `unknown` without raising, intensity peaking at new/full, and the weekly calendar still building. Live on the Astro Timing page with zero exceptions.
  - **AW-1…AW-4 remain open and remain good-to-have.** AW-0 was the bug; the card is still the enhancement.

## Related Pages
- [[analyses/Dashboard-UI-Roadmap]] — Phase 3 holds the standing rule that Astro is a context modifier, never an entry signal.
- [[analyses/Sector-Rotation-Orbit-Data-Source-Roadmap]] — SR-6/SR-* shipped the card-renderer and honesty-device patterns this reuses.
