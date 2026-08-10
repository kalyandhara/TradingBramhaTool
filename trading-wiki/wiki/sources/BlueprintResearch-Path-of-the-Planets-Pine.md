---
title: "Pine — Path of the Planets [BlueprintResearch] v2.1"
category: source
tags: [pine, astro, ephemeris, declination, heliocentric, longitude, out-of-bounds, projection, vsop87, blueprint-research]
created: 2026-08-09
updated: 2026-08-09
sources: 1
related:
  - concepts/Out-of-Bounds-Planets.md
  - concepts/Panchang.md
  - concepts/Mercury-Retrograde-Market-Cycle.md
  - analyses/FA-2-Rahu-Kaal-Measured.md
  - analyses/Financial-Astrology-Sector-Week-Roadmap.md
---

# Pine — Path of the Planets [BlueprintResearch] v2.1

## Metadata
- **Author:** BlueprintResearch (Javonnii) · **License:** CC BY-NC-SA 4.0 · **Version:** 2.1, Feb 2026
- **Type:** Pine v6 `indicator`, overlay, `scale=scale.left`
- **Ephemeris:** VSOP87, ELP2000-82 and Meeus algorithms via the author's `blueprint_ephemeris_lib/1`
- **Ingest trigger:** user supplied the full source, noting *"we should have option for selection of planet"*

## Key Takeaways

1. **Three data series per planet, ten bodies:** geocentric ecliptic longitude, **heliocentric** longitude, and **declination** — for Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto.
2. **Per-planet, per-series toggles are the entire UI.** Roughly 30 boolean inputs grouped into *Inner Planets Longitudes*, *Outer Planets Longitudes* and *Declinations*, each planet carrying an independent Geo / Helio / Dec switch. **This is the "selection of planet" capability requested.**
3. **Future projection up to 500 bars** (`look_ahead`, default 250), drawn with `polyline`. Because an ephemeris is deterministic, projecting forward is exact — not a forecast.
4. **`foldTo180()`** maps 0–360° onto 0–180° by reflecting past 180°, so a longitude line stays on a compact axis instead of sawtoothing at the 360→0 wrap. A display transform, not an astronomical one.
5. **Mirror and shift controls:** `mirror_in` negates longitude; `shiftLongitudeCycles` adds ±N×360° — both purely for aligning the curve against price on a shared axis.
6. **Declinations are drawn as closed polygons against a zero line** (`style_area` + `closed=true`), which makes the zero-declination crossing the visual event rather than the value.
7. **Positions table** shows current geo / helio / declination per planet with the zodiac sign glyph.

## Detailed Notes

The computation surface is small — everything derives from two library calls:

```
eph.get_longitude(eph.Planet.X, time, preferGeo)   // true = geocentric, false = heliocentric
eph.get_declination(eph.Planet.X, time)
```

Everything else in ~700 lines is presentation: per-planet colour constants, the fold/mirror/shift transforms, table rendering, and the projection loop that re-calls both functions for each future bar.

**Notable that it is tropical, not sidereal.** `f_degsignf` buckets raw longitude into 30° signs with no ayanamsa, so its ♈–♓ labels are Western/tropical. Our [[concepts/Panchang]] work is **sidereal** (Lahiri) because nakshatras require it. The two will disagree by roughly 24° — about one whole sign — and that is a definitional difference, not an error in either.

## Actionable Insights

> [!key-insight] The entire data layer is reproducible offline with the `ephem` we already have — verified before writing anything
> Tested 2026-08-09 across all ten bodies: `ephem` yields geocentric longitude, declination, and heliocentric lon/lat directly. Same conclusion as the panchang work: **no vendor, no API, no rate limit.** Shipped as [planet_positions.py](tools/planet_positions.py).

**The audit that prompted building rather than just documenting** — before this, repo-wide:

| Capability | Status before 2026-08-09 |
|---|---|
| **Declination** | **zero occurrences anywhere** — despite [[concepts/Out-of-Bounds-Planets]] being a purely declination-based concept |
| **Heliocentric** | **zero occurrences** |
| **Outer planets** | present only as *orbital-period constants* in `financial_astrology_methods.py` (Uranus 84.01y, Neptune 164.79y, Pluto 247.94y) — never as positions |
| **Planetary longitude** | either parsed from an AstroHora CSV export (`astrohora_loader.py`) or computed for the **Moon only**, for nakshatra (`panchang.py`) |

Writing a page about an indicator we could not compute would have made a **fifth documented-but-not-coded gap this week**, after the order-block selection rule, volume-profile HVN/LVN, the evening-star gap and the pmax WXY labels. So the module was built with the ingest.

## Contradictions with Existing Wiki

- **No contradiction on the astronomy** — the script's method (VSOP87/ELP2000/Meeus) is the same family `ephem` implements, and our spot values agree with its described behaviour.
- **Tropical vs sidereal**, as above: this source's sign labels are tropical; ours are sidereal. Both correct within their own convention; ~24° apart. Recorded so nobody "fixes" one to match the other.
- **It makes no market claim at all**, which is unusual for astro material and worth crediting — it plots positions and stops. That is the same line this repo holds, and unlike most sources it does not need the caveat added on ingest.

## Pages Updated
- [[concepts/Out-of-Bounds-Planets]] — now computable; `out_of_bounds()` added
- [[concepts/Panchang]] — cross-referenced (shared conventions, sidereal-vs-tropical note)
- `tools/planet_positions.py` — **created**
- `wiki/index.md`, `wiki/log.md`
- **`wiki/overview.md` untouched** — an ephemeris shifts no market thesis.
