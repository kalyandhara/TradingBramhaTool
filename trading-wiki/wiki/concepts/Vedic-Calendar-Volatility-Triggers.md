---
title: "Vedic Calendar Volatility Triggers — Adhik-Masa & Panchaka"
category: concept
tags: [astro, vedic, calendar, adhik-masa, panchaka, volatility, correction, event-study, unvalidated]
created: 2026-08-26
updated: 2026-08-26
sources: 1
related:
  - concepts/Vedic-Planet-Trading-Aspects.md
  - concepts/Sarvatobhadra-Chakra.md
  - concepts/Panchang.md
  - analyses/Open-Backlog.md
---

# Vedic Calendar Volatility Triggers — Adhik-Masa & Panchaka

Two **calendar-based** Vedic timing claims that are genuinely new granularity vs
the rest of this vault's astro material (the planet/sign/pada *bias* framework
already lives in [[concepts/Vedic-Planet-Trading-Aspects]]; the intraday reversal
grid in [[concepts/Sarvatobhadra-Chakra]]). Both are **unvalidated hypotheses**
recorded here so they can be *tested*, not traded on faith — this vault's astro
track record is a string of clean negatives (SBC daily-vedha, new-moon levels,
muhurat), so the prior on any new astro claim is ~no edge until measured.

## Definition

### Adhik-Masa (अधिक मास — the extra/leap lunar month)
A lunar year is ~11 days shorter than a solar year, so roughly every **2.5–3
years** an extra lunar month is inserted to re-sync the calendars. Astronomically
it is the month in which **no solar sankranti (sign ingress) occurs** — i.e. **two
new moons fall within the same zodiac sign**. In the ~19-year Metonic cycle there
are **7 such months**, so an Adhik-Masa *year* recurs about that often.

**Market claim (from the source):** Adhik-Masa years have historically carried
**strong corrections (10–30%)** in equity indices, with the bearish pressure
concentrated in the extra month itself *if cruel (malefic) planets dominate* that
window (the planet/sign/pada tally in [[concepts/Vedic-Planet-Trading-Aspects]]).

### Panchaka (पंचक — the "five" inauspicious days)
The **~5-day window each lunar month** while the Moon transits the **last five
nakshatras** — Dhanishtha (2nd half), Shatabhisha, Purva Bhadrapada, Uttara
Bhadrapada, Revati — i.e. the last ~5 nakshatras spanning late Aquarius → Pisces.
Traditionally treated as inauspicious for new beginnings.

**Market claim (from the source):** Panchaka days — **especially a Full Moon
landing on a Panchaka day** — mark **heightened volatility**; keep stops tight and
avoid fresh "all-in" entries into the window.

## How to Use (as claimed — not endorsed)

- **Adhik-Masa year:** hedge (options) or reduce leveraged exposure ahead of / during
  the extra month; the risk is framed as a *major correction*, not a wobble.
- **Panchaka window:** treat as a volatility-spike flag — tighten stops, size down,
  don't initiate large positions; watch the Full-Moon-on-Panchaka overlap most.
- Both are **context/timing overlays**, not entry signals — the same stance the
  measured evidence forces on every astro tool here.

## Testability — this is the point of recording them

Both are **event-study shaped**, reusing the harness already built for the astro
nulls (`newmoon_levels_backtest.py`, `sbc_vedha_backtest`):

| Trigger | Observations | Testable? | Prior |
|---|---|---|---|
| **Panchaka window** | ~12/yr × 5 days → **plenty** | Yes — index forward vol/return in-window vs a **matched non-Panchaka control**, permutation null; Full-Moon-on-Panchaka as a sub-cut | Base-rate trap (5 of every ~27 days) → **expect ~no excess vol**, mirroring the SBC/new-moon nulls |
| **Adhik-Masa correction** | **~7 in 19 years** → tiny | Barely — too few events for significance; can *describe* past Adhik-Masa-year drawdowns but not establish edge (survivorship + tiny-n) | Cherry-pick risk is severe; a 10–30% band is wide enough to "hit" most years |

**Recommended first test:** Panchaka volatility (enough observations to be
falsifiable). Adhik-Masa should be treated as **narrative until a longer index
history and a pre-registered drawdown definition exist** — a candidate for the
backlog's astro event-study lane alongside B-30 (Moon-in-Pushya), with the same
expected-null framing.

## Common Mistakes

- **Confirmation on a wide band.** "10–30% correction sometime in an Adhik-Masa
  year" is nearly unfalsifiable — most years touch a 10% drawdown intra-year.
- **Base-rate blindness on Panchaka.** 5 of ~27 days are Panchaka every month;
  volatility will "cluster" there by chance alone. A matched control is mandatory.
- **Trading it before measuring it.** The vault's astro nulls are the reason this
  page is a hypothesis, not a rule.

## Related Concepts

- [[concepts/Vedic-Planet-Trading-Aspects]] — the planet/sign/pada bias tally that
  the source says decides *direction* during these windows
- [[concepts/Sarvatobhadra-Chakra]] — intraday reversal-window sibling (clean-negative on backtest)
- [[concepts/Panchang]] — tithi/nakshatra calendar these windows are read from
- [[analyses/Open-Backlog]] — astro event-study lane (B-30 et al.)

## Sources

1. "Astrological Market-Prediction Theory (Time-Agnostic)" — video summary,
   user-provided 2026-08-26. See [[sources/Astro-Market-Prediction-Time-Agnostic]].
