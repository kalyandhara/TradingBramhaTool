# Market Yoga Cheat‑Sheet (English version)  

*Compiled from the classroom‑style transcript – step‑by‑step explanation of the “yogas”, reverse‑date logic, and how to turn them into trade decisions.*

---

## 1️⃣ What are the “yogas”?

In the context of the discussion a **yoga** is a **specific astrological‑market configuration** that often signals a **reversal** (top or bottom) of the market on the next trading day.  
The most important yogas, in order of strength, are:

| # | Yoga (Hindi) | Literal meaning | Typical market implication |
|---|--------------|----------------|---------------------------|
| 1 | **Indra Yoga** | “Indra” – the king of the gods | **Strongest** reversal signal (usually a bottom, but can be a top). |
| 2 | **Shool Yoga** | “Shool” – the spear | Next‑most powerful, still a clear reversal. |
| 3 | **Dvi Pushkar Yoga** | “Two Pushkar” | Moderate‑strength reversal; appears often with other yogas. |
| 4 | **Tri Pushkar Yoga** | “Three Pushkar” | Weaker than Dvi, still useful when combined with moon phases. |
| 5 | **Guru Pushya Yoga** | “Guru (‑Jupiter) + Pushya” | Can give a **top** signal; strength depends on surrounding yogas. |
| 6 | **Ravi Pushya Yoga** | “Sun + Pushya” | Least strong of the set, often needs confirmation from other factors. |

> **Note:** The term *Pushkar* simply denotes a “pair” of auspicious planetary positions; the number (Dvi = 2, Tri = 3) tells you how many such pairs line up on that day.

---

## 2️⃣ Reverse‑Date Concept  

- **Reverse‑date** = the **trading day immediately after a yoga appears**.  
- The market **tends to reverse direction on that day** (i.e., a bottom becomes a rise, a top becomes a fall).  
- The date is *always* the **next *calendar* day**, regardless of whether the next day is a holiday.  

### How to spot reverse dates

1. **Open the Drik Panchang website** (search “Drik Panchang” on Google).  
2. In the search bar type the yoga name + the year, e.g.  
   ```
   Indra Yoga 2025
   ```
3. A table appears; note the **date column** – that is the **reverse‑date**.  
4. Mark those dates on your calendar (or directly on your trading diary).  

#### Automated alternative — `tools/yoga_dates.py`

The lookup above is also wired up programmatically against the same Drik
Panchang pages. Fetched dates are cached on disk for 30 days, so this is
safe to call repeatedly from screeners / morning-prep scripts:

```bash
# Print Indra Yoga 2026 as a table (and dump a CSV next to the JSON cache)
py -3 tools/yoga_dates.py indra 2026 --csv

# Force a re-fetch (ignore cache)
py -3 tools/yoga_dates.py indra 2026 --refresh
```

```python
from datetime import date
from yoga_dates import upcoming_reverse_dates

for occ in upcoming_reverse_dates(["indra"], from_date=date.today(), days=60):
    print(occ.reverse_date, occ.weekday, "<- Indra @", occ.start)
```

The other five yogas in the cheat-sheet (Shool / Dvi Pushkar / Tri Pushkar /
Guru Pushya / Ravi Pushya) live on different Drik slugs — add the verified
slug to `YOGA_SLUGS` in `tools/yoga_dates.py` to enable them.


> The speaker repeatedly used **24 April 2025** as an example – the Indra Yoga day was the 23rd, so **24 April** became the reverse date.

---

## 3️⃣ Example Walk‑through (the dates mentioned in the transcript)

| Yoga | Yoga Date (2025) | Reverse‑Date (next day) | Market bias noted in the class |
|------|------------------|------------------------|--------------------------------|
| Indra Yoga | 23 April | **24 April** | Bottom → market expected to fall; top identified at 23 April. |
| – | 28 March (a holiday) | **29 March** | Market expected to fall after a holiday‑break. |
| – | 4 March | **5 March** | Similar logic – top identified, market to reverse down. |
| Dvi Pushkar Yoga | 21 January | **22 January** | Reversal expected; used as a reference for the next month. |
| Tri Pushkar Yoga | 15 April (full‑moon/Amavasya day) | **16 April** | Weak reversal; next‑day move smaller, keep target modest. |
| Ravi Pushya Yoga | 13 March (and 26 March) | **14 March / 27 March** | Both dates indicated a potential top; required confirmation. |

> **Take‑away:** Whenever you see a yoga on the calendar, **look at the next day** – that’s the day you plan your entry/exit.

---

## 4️⃣ Trading Rules Derived from the Yoga Theory  

| Situation | Action | Rationale |
|-----------|--------|-----------|
| **Yoga appears** (any of the six) | **Do not take a large position**. Enter only a **small or “quick‑swing” trade** (1–2 % of account). | Yogas often lead to a **single‑day reversal**; a big position can get stopped out by the very move you’re trying to capture. |
| **Two yogas within 2‑3 days** (e.g., Indra Yoga on 23 Apr and Shool Yoga on 24 Apr) | **Enter the first yoga, exit on the reverse‑date of the *second* yoga** (i.e., take profit early). | Overlap increases volatility – you want to capture the early leg. |
| **Yoga + strong candle break (green breakout after a bottom)** | **Take the trade** – the breakout confirms the reversal. | A strong candle validates the yoga signal. |
| **Yoga + weak candle / no breakout** | **Avoid the trade** or **exit immediately** if already in. | Without price confirmation the yoga alone is insufficient. |
| **Yoga coincides with a Moon‑phase (New Moon, Full Moon, Amavasya)** | **Increase confidence** – treat the signal as **high‑weight**. | The speaker emphasized that moon phases amplify the yoga’s power. |
| **Yoga near a “major” planetary conjunction (e.g., Sun + Jupiter)** | **Treat as a “top” signal** – prepare for a fall. | Guru Pushya and Ravi Pushya often indicate tops rather than bottoms. |
| **Holiday or weekend after a yoga** | **The reverse‑date still counts** – even if markets are closed, the next **trading day** will reflect the reversal. | The concept is calendar‑based, not trading‑session‑based. |

### Position‑size guideline (example)

| Yoga strength | Suggested risk |
|---------------|----------------|
| **Indra (strongest)** | 1–1.5 % of account |
| **Shool / Dvi** | 0.8–1 % |
| **Tri / Guru / Ravi (weaker)** | 0.5–0.8 % |

---

## 5️⃣ Practical Workflow (Step‑by‑Step)

1. **Morning prep**  
   - Open **Drik Panchang**.  
   - Search the six yoga names for the current year.  
   - Write the dates in a **simple table** in a notebook or a spreadsheet.  

2. **Mark the reverse dates** (the day after each yoga).  
   - Highlight in **red** if you expect a **top** (sell) and **green** for a **bottom** (buy).  

3. **Pre‑market scan** (15 min before market opens)  
   - Check the **previous day’s candle** (did a green breakout happen? a red breakdown?).  
   - If the candle **confirms** the yoga direction → plan the entry.  

4. **Trade execution**  
   - Use a **limit order** at the *breakout* price.  
   - Set a **tight stop‑loss** (e.g., 0.5 % of entry price).  
   - Target: **small profit** (0.5–1 % of entry) *or* exit at the **reverse‑date’s open** if the move is still ongoing.  

5. **Post‑trade review**  
   - Record: yoga name, date, entry price, exit price, outcome.  
   - Over time you’ll build a **personal performance log** – essential for refining the system.  

---

## 6️⃣ Moon‑Phase Overlay (Optional but Powerful)

| Moon Phase | Typical effect on yoga strength |
|------------|--------------------------------|
| **New Moon** | Reinforces *bottom* yogas (e.g., Indra Yoga). |
| **Full Moon** | Reinforces *top* yogas (e.g., Guru Pushya). |
| **Amavasya** (new‑moon night) | Adds extra volatility – **tighten stops**. |
| **Purnima** (full‑moon night) | May cause an **early reversal** – consider exiting before the full‑moon candle closes. |

> The speaker emphasized that when a yoga **co‑exists with a lunar phase** the signal becomes **“high weight”** – treat it as a **higher‑probability trade**.

---

## 7️⃣ Quick Reference Table (2025 – key yogas)

| Yoga | Calendar Date (2025) | Reverse‑Date | Expected Direction | Example Market Action |
|------|---------------------|-------------|--------------------|-----------------------|
| Indra Yoga | 23 Apr | **24 Apr** | Bottom → rise then fall (top at 23 Apr) | Sell at open on 24 Apr if market opened lower. |
| Shool Yoga | 4 Mar | **5 Mar** | Bottom → rise | Long at open on 5 Mar after green breakout. |
| Dvi Pushkar Yoga | 21 Jan | **22 Jan** | Bottom → rise | Buy on 22 Jan if previous day closed high. |
| Tri Pushkar Yoga | 15 Apr (Full Moon) | **16 Apr** | Moderate bottom → small rise | Enter only if a strong green candle appears. |
| Guru Pushya Yoga | 13 Mar | **14 Mar** | Top → fall | Short at open on 14 Mar if market opened lower. |
| Ravi Pushya Yoga | 26 Mar | **27 Mar** | Top → fall | Short if a red candle breaks below prior low. |

*(These are the dates mentioned in the transcript; the full yearly list can be generated from Drik Panchang.)*

---

## 8️⃣ Final Take‑aways  

1. **Yogas ≈ “One‑day reversal signals.”** The day **after** the yoga is the one to watch.  
2. **Indra Yoga is the most powerful**; treat it as a high‑confidence entry/exit.  
3. **Combine yoga with price action** (breakout candle) and **moon phase** to increase reliability.  
4. **Keep position size small** and **exit quickly** – the market often reverses sharply and then stabilises.  
5. **Maintain a simple log** – over time you’ll see which yogas work best for the particular indices you trade.  

---

*Prepared for anyone who wants to turn the astrological‑market “yoga” theory into a practical, repeatable trading routine.*
# Astrology-Based Trading Integration Guide

## Overview

The Trading Bramha dashboard has been enhanced with Vedic astrology-based trading indicators. This integration provides:

1. **Daily Lunar Timing** — Optimal entry/exit windows based on lunar phases
2. **Market Intensity Forecasting** — Volatility predictions using lunar cycles
3. **Vimshottari Dasha Analysis** — Career/market cycles for individuals
4. **Solar Timing** — Sunrise/sunset based market windows
5. **AstroHora Chart Integration** — Load birth charts for deeper analysis

## Files Created

### 1. `astro_trading.py`
Core module for real-time astrological calculations.

**Key Functions:**
- `AstroIndicators.get_trading_timing(date)` — Daily timing recommendation
- `AstroIndicators.get_lunar_phase(date)` — Lunar cycle position
- `AstroIndicators.get_weekly_calendar(start_date, days)` — Multi-day forecast
- `AstroIndicators._calculate_market_intensity(date)` — Volatility score (0-100)

**Usage:**
```python
from astro_trading import AstroIndicators
from datetime import date

ai = AstroIndicators(city='Mumbai')  # or other major Indian cities
timing = ai.get_trading_timing(date.today())

# Access results:
print(timing['lunar_phase'])      # {'phase': 'waxing', 'illumination': 97.81, ...}
print(timing['market_intensity'])  # 80 (scale: 0-100)
print(timing['recommendations'])   # List of trading tips
```

### 2. `astrohora_loader.py`
Parser for AstroHora birth chart data. Supports:

- CSV/Excel exports from AstroHora software
- Birth chart analysis (Natal charts via KP System)
- Prashna charts (event-based queries)
- Vimshottari Mahadasha calculation
- Planetary aspects and conjunctions

**Key Methods:**
- `AstroHoraData.load_from_csv(filepath)` — Load exported data
- `AstroHoraData.load_from_excel(filepath)` — Load from Excel
- `AstroHoraData.get_vimshottari_dasha(birth_date, current_date)` — Calculate dasha period
- `AstroHoraData.get_strong_planets()` — Find planets in exaltation/own sign
- `AstroHoraData.get_aspectarian()` — Major planetary aspects

**Usage:**
```python
from astrohora_loader import AstroHoraData
from datetime import date

aha = AstroHoraData()
aha.load_from_csv('my_birth_chart.csv')

summary = aha.get_summary()
print(summary['strong_planets'])  # Exalted/powerful planets

dasha = aha.get_vimshottari_dasha(date(1990, 6, 15))
print(f"Current: {dasha['current_dasha']}, {dasha['years_remaining']:.1f} years left")
```

## Dashboard Integration

### New Tab: "Astro Timing"

**Section 1: Daily Summary**
- Lunar Phase (new/waxing/full/waning)
- Moon Illumination %
- Lunar Cycle Day (out of 29.53)
- Market Intensity Score

**Section 2: Solar Timing**
- Sunrise/Sunset times (IST)
- Optimal Entry Window (15 min post-sunrise)
- Optimal Exit Window (15 min pre-sunset)

**Section 3: Trading Recommendations**
AI-generated advice based on:
- Lunar phase energy (bullish during waxing, consolidation during waning)
- Market volatility (reduce size during peaks)
- Optimal trading hours

**Section 4: Weekly Calendar**
7-day forecast showing:
- Date | Lunar Phase | Illumination | Market Intensity | Sunrise | Sunset

**Section 5: 30-Day Forecast Chart**
Visual overlay of:
- Lunar illumination curve (gold)
- Market intensity forecast (red)

**Section 6: AstroHora Integration**
Two ways to load chart data:

**Option A: Upload Export**
1. Open AstroHora software → Generate chart
2. Export as CSV or Excel
3. Upload via "Astro Timing" tab → "Upload AstroHora Data"

**Option B: Manual Entry**
- Use the "Load Example Chart" button to see format
- Enter your birth details manually or integrate via API

## Astrological Concepts

### Lunar Phases & Trading

| Phase | Days | Market Character | Trading Bias |
|-------|------|------------------|--------------|
| **New Moon** | 0-1 | High volatility, reversals | Use tight stops, watch reversals |
| **Waxing** | 1-14 | Rising energy, bullish | Favor longs, hold winners |
| **Full Moon** | 14-16 | Peaks, profit-taking | Take profits, consider shorts |
| **Waning** | 16-29 | Declining energy, bearish | Favor shorts, reduce longs |

**Market Intensity** (0-100):
- **80+:** High volatility — reduce position size
- **40-79:** Normal conditions
- **<40:** Low volatility — range-bound

### Vimshottari Mahadasha

A 120-year cycle of 9 planetary periods (in order):
1. Ketu (7 years)
2. Venus (20 years)
3. Sun (6 years)
4. Moon (10 years)
5. Mars (7 years)
6. Rahu (18 years)
7. Jupiter (16 years)
8. Saturn (19 years)
9. Mercury (17 years)

Each period carries different traits (eg. Rahu = risk-taking, Jupiter = expansion).
**Application:** Track your current dasha period—if you're in a bullish period (Venus, Jupiter),
favor aggressive strategies; if in Saturn, prefer defensive positioning.

## Supported Cities

Built-in coordinates for:
- Mumbai (19.08°N, 72.88°E)
- Delhi (28.70°N, 77.10°E)
- Bangalore (12.97°N, 77.59°E)
- Chennai (13.08°N, 80.27°E)
- Kolkata (22.57°N, 88.36°E)
- Hyderabad (17.39°N, 78.49°E)

*(More cities can be added via the CITIES dict in astro_trading.py)*

## Installation Notes

### Required Packages
```bash
py -3 -m pip install ephem pandas streamlit plotly
```

**Note on System DLLs:**
The AstroHora software requires `swedll32.dll` and `swedll64.dll` to be copied to `C:\Windows\System32\`.
This requires admin privileges. If you don't have admin access:
1. Ask your system administrator to copy the DLLs
2. Or run AstroHora directly to generate charts, then export as CSV

## Workflow Examples

### Example 1: Daily Pre-Market Timing Check
```
1. Open Trading Bramha → Astro Timing tab
2. Check "Today's Astro-Trading Timing"
3. Note optimal entry/exit times
4. Review recommendations for market conditions
5. Adjust position sizing if market_intensity > 70
```

### Example 2: Track Your Dasha Period
```
1. Generate your birth chart in AstroHora
2. Export as CSV
3. Upload to Astro Timing tab
4. Check "Dasha Analysis" section
5. Reference dasha characteristics when choosing strategies
```

### Example 3: Plan Weekly Trading
```
1. Check "Weekly Astro Calendar"
2. Identify new/full moon dates (high volatility days)
3. Adjust watchlist/trade frequency accordingly
4. Plan to be defensive 1-2 days before full moon
```

## Limitations & Disclaimers

1. **Astronomical vs. Vedic:** Using Western ephemeris (PyEphem). Vedic astrology uses Ayanamsa correction (~23°26'). For precision, use AstroHora's native calculations.

2. **Market causation not proven:** Lunar cycles correlate with some market patterns historically, but causation is speculative. Use as ONE of many tools, never sole decision criterion.

3. **Timezone sensitivity:** All timings are IST-adjusted. Adjust if trading in other timezones.

4. **Approximations:** Without actual birth chart positions (Moon's exact degree), Dasha calculations are approximated. Use AstroHora for precise personal charts.

## Future Enhancements

- [ ] Integrate real AstroHora API (if available)
- [ ] Add Navamsha chart (9-fold division) analysis
- [ ] Transits (current planetary positions vs. birth chart)
- [ ] Nakshatra (lunar mansion) analysis for timing
- [ ] Export timing signals to webhook for auto-trading bots

## References

- **AstroHora**: Vedic astrology software (KP System + Prashna)
- **PyEphem**: Astronomical calculations library
- **Vimshottari Dasha**: 120-year cyclical period system

---

## 8️⃣ Combined Reversal Calendar (yogas + lunar phases → SQLite → chart)

The 6-yoga cheat-sheet above is now backed by an end-to-end pipeline that
ingests every yoga from Drik Panchang plus the exact astronomical Full/New
Moon timestamps, persists them once-per-2-years into a local SQLite DB,
and renders them on the live candlestick chart as a single toggleable
indicator. The pieces:

| File | Role |
|---|---|
| `tools/yoga_dates.py` | Scrapes the 9 supported yogas — Indra from `/panchang/yoga/daily/`, plus the 8 auspicious yogas (Ravi, Sarvartha Siddhi, Amrit Siddhi, Dwipushkar, Tripushkar, Ravi Pushya, Guru Pushya, Maitreya) from `/yoga/`. 30-day disk cache. |
| `tools/lunar_phases.py` | PyEphem-derived Full Moon (Purnima) and New Moon (Amavasya) timestamps in IST. No network, deterministic. |
| `tools/reversal_calendar.py` | One-table SQLite with idempotent `build` + range/coincidence queries. |
| `tools/chart_server.py` → `/api/reversal_events` | Returns events + coincidence scores for a date window. |
| `tools/chart_dashboard.html` → "Reversal Calendar" indicator | Per-pane toggle under the new **Calendar** group; markers under each candle, brighter/larger when ≥2 events coincide. |

### Build the calendar (one-off per 2 years)

```bash
# Default: build 2026 and 2027 in one go
py -3 tools/reversal_calendar.py build --years 2026 2027

# Force re-scrape (ignores yoga_dates.py's 30-day cache)
py -3 tools/reversal_calendar.py build --years 2026 2027 --refresh-yoga

# Verify
py -3 tools/reversal_calendar.py stats
py -3 tools/reversal_calendar.py query --from 2026-06-28 --days 90 --coincidence
```

The build is idempotent — re-running for an already-ingested year skips
duplicates rather than crashing or doubling rows (UNIQUE constraint on
`event_date + event_type + start_ts`).

### Read on the chart

1. Restart `chart_server.py` once after a build (so it sees the new DB).
2. In any pane's **INDICATORS** dropdown, tick **Reversal Calendar (Yogas + Lunar)** under the *Calendar* group.
3. Markers appear under candles:
   - **Single muted-gold circle** with a short glyph (e.g. `I` Indra, `F` Full Moon, `AS` Amrit Siddhi) — one event that day.
   - **Bright-gold up-arrow with combined glyphs** (e.g. `I+F` for Indra + Full Moon on the same date) — **coincidence ≥ 2**, the "sharper reversal" candidate days per the cheat-sheet.
4. A small bottom-right panel auto-summarises today's and tomorrow's events in plain English so you don't have to memorise glyphs.

### How to trade off these markers

Per the cheat-sheet's §2 (reverse-date concept) and the user-supplied
clarifications:

1. **The yoga day itself = reversal *candidate* day, not a guaranteed reversal.**
   Mark it on the chart but don't pre-position into it.
2. **Wait for the *next* day's H/L break to confirm.** A break of the yoga
   day's high → long-side reversal active; a break of its low → short-side
   reversal active.
3. **Coincidence ≥ 2 = upgrade the conviction.** When the bright-gold
   marker appears (e.g. Indra Yoga + Full Moon on 30 Jun 2026), the
   reversal that follows tends to be **sharper and more sustained** —
   the user's "sometimes if more than one muhurat coincides it usually
   triggers way sharper reversal trend" observation.
4. **Position size still scales by yoga strength.** Indra is the
   strongest single signal in the original cheat-sheet; the 8 auspicious
   yogas in the new ingest are typically weaker than Indra individually,
   but stack well together. See §4's position-size table.

### Glyph reference

| Glyph | Event |
|---|---|
| `I` | Indra Yoga |
| `R` | Ravi Yoga |
| `SS` | Sarvartha Siddhi Yoga |
| `AS` | Amrit Siddhi Yoga |
| `DP` | Dwipushkar Yoga |
| `TP` | Tripushkar Yoga |
| `RP` | Ravi Pushya Yoga |
| `GP` | Guru Pushya Yoga |
| `M` | Maitreya Yoga |
| `F` | Full Moon (Purnima) |
| `N` | New Moon (Amavasya) |

Coincidence days combine glyphs with `+` (e.g. `I+F` = Indra + Full Moon).

Here is the summary of the video transcript translated into English and presented in a tabular form.

### Astrological Analysis of Market Crashes & Future Predictions**

**Core Thesis:** Jupiter (Guru) is the primary planet driving market rallies and crashes. Major crashes historically occur when Jupiter is in a "Nakshatra" (constellation) of Ketu, afflicted by the "Shashtashtak" Yoga (6/8 axis relationship) with malefic planets like Saturn, Sun, or Mars.

| Period / Year   | Market Event / Trend           | Jupiter's Position (Sign/Nakshatra)                 | Key Planetary Combinations (Yogas/Aspects)                                                                                                 | Market Outcome                                                                                                                                          |
| :-------------- | :----------------------------- | :-------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1992**        | **Harshad Mehta Scam Crash**   | Singh (Leo) / Magha Nakshatra (Ketu's star)         | • Jupiter in Shashtashtak with Saturn & Sun.<br>• Aspected by Rahu & Mars.<br>• Afflicted by Ketu's constellation.                         | **High Crash:** Sensex fell 57% (4546 to 1980). Recovery took 20 months.                                                                                |
| **2000**        | **Dot-com Bubble Burst**       | Mesh (Aries) / Ashwini Nakshatra (Ketu's star)      | • Jupiter conjunction with Saturn.<br>• Jupiter in Rahu-Ketu axis.<br>• Severe affliction on Jupiter.                                      | **High Crash:** Nifty fell 53% (1812 to 849). Recovery took 34 months.                                                                                  |
| **2008**        | **Global Financial Crisis**    | Dhanu (Sagittarius) / Moola Nakshatra (Ketu's star) | • Jupiter with Sun; aspected by Mars & Ketu.<br>• Jupiter in 8th house from Saturn.<br>• Debilitated in own sign due to Ketu's star.       | **High Crash:** Nifty fell 64% (6357 to ~2520). Recovery was very slow (71 months).                                                                     |
| **2020**        | **Covid-19 Crash**             | Dhanu (Sagittarius) / Moola Nakshatra (Ketu's star) | • Jupiter with Saturn, Sun, Mercury.<br>• Under eclipse influence.<br>• Afflicted by Ketu's star.                                          | **Sharp Crash:** Nifty fell 39% in 2.5 months.<br>**Fast Recovery:** Fundamentals were strong; market rallied once Jupiter moved away from Saturn/Ketu. |
| **1995**        | **Positive Trend** (Exception) | Dhanu (Sagittarius) / Moola Nakshatra               | • No malefic aspect or Shashtashtak.<br>• Jupiter with Mars.                                                                               | **Positive:** Market returned ~7% despite Jupiter being in Ketu's star.                                                                                 |
| **2003**        | **Bull Run** (Exception)       | Simha (Leo) / Magha Nakshatra                       | • Jupiter with Mercury & Moon (Gajakesari/Laxmi Yoga).<br>• No malefic in 6th/8th house.                                                   | **Highly Positive:** Nifty jumped ~20%.                                                                                                                 |
| **2011**        | **Sideways / Negative**        | Mesh (Aries) / Moola Nakshatra                      | • Jupiter aspected by Rahu.<br>• 8th house from Saturn.                                                                                    | **Negative:** Nifty returns were -12%. Market remained flat.                                                                                            |
| **2015**        | **Minor Correction**           | Simha (Leo) / Magha Nakshatra                       | • Aspected by Saturn.<br>• 8th from Ketu.                                                                                                  | **Negative:** Nifty fell ~7%.                                                                                                                           |
| **2023**        | **Bull Run** (Exception)       | Mesh (Aries) / Moola Nakshatra                      | • No Shashtashtak with malefic planets.                                                                                                    | **Highly Positive:** Nifty rallied ~12%.                                                                                                                |
| **Oct 2024**    | **Short-term Volatility**      | Tula (Libra) / Visakha                              | • Jupiter in Shashtashtak with Sun, Saturn, Mars.<br>• Not in Ketu's Nakshatra.                                                            | **Prediction:** Market correction expected (Oct 18 - Dec 4), but not a major crash.                                                                     |
| **June 2026**   | **Trend Reversal Starts**      | Kark (Cancer)                                       | • Jupiter in Shashtashtak with Rahu.                                                                                                       | **Prediction:** Market may begin to show turbulence.                                                                                                    |
| **Nov 2026**    | **Major Crash Prediction**     | Singh (Leo) / Magha Nakshatra (Ketu's star)         | • Jupiter moves to Rahu-Ketu axis.<br>• Enters Magha Nakshatra.<br>• 8th house from Saturn.<br>• Resembles the 2008 setup.                 | **Prediction:** Major Market Crash expected.                                                                                                            |
| **2027 - 2032** | **Bearish / Slow Recovery**    | Various / Ketu Influence                            | • Recurring Shashtashtak with Saturn.<br>• Jupiter under Ketu/Rahu influence repeatedly.<br>• Saturn transiting Mesh (Global disturbance). | **Prediction:** Difficult period for markets. Recovery will be very slow.                                                                               |
| **Post-2033**   | **Recovery Starts**            | -                                                   | • Jupiter-Saturn Shashtashtak persists but without affliction.                                                                             | **Prediction:** Market trend likely to turn positive.                                                                                                   |

### **Key Investment Advice:**
*   **Diversification:** Investors should diversify portfolios rather than putting all "eggs in one basket" (equity).
*   **Caution Period:** Be cautious after **November 2026**. Do not stay in a one-sided bullish position during this time.

---

**Last Updated:** June 28, 2026  
**Status:** Production (Daily pre-market use recommended)
