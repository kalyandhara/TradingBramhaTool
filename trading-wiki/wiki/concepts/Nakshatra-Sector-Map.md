---
title: "Nakshatra Sector Map — Vedic Lunar Mansion Trading Guide"
category: concept
tags: [astro, nakshatra, vedic, lunar, sector, commodity, timing]
created: 2026-08-12
updated: 2026-08-12
sources: 3
related:
  - analyses/Dashboard-UI-Roadmap.md
  - concepts/Chart-Patterns.md
---

# Nakshatra Sector Map

The 27 Vedic lunar mansions (nakshatras) each span 13°20' of the sidereal zodiac. As the Moon transits through each nakshatra (~1 day per nakshatra), Vedic financial astrology associates specific commodities and market sectors with elevated activity or directional bias.

**Use as context, not signal.** A nakshatra does not predict direction — it narrows the field of sectors likely to see unusual volume or volatility during that window.

---

## How the Dashboard Uses This

The Astro Timing page computes the Moon's geocentric ecliptic longitude via PyEphem, subtracts the Lahiri ayanamsa (~23.85° for 2026) for the sidereal zodiac, then divides by 13.333° to identify the nakshatra. A 7-day forward table shows which NSE sectors correspond to each day's lunar mansion.

**Ayanamsa used:** Lahiri, ~23.85° (2026). Update `_AYANAMSA` in `astro_trading.py` annually.

---

## Complete 27-Nakshatra Sector Map

| # | Nakshatra | Ruling Planet | NSE Sectors | Commodity / Industry Theme |
|---|-----------|---------------|-------------|---------------------------|
| 1 | **Ashwini** | Ketu | Pharma, Auto, Metal | Rice, wool, ghee, iron, copper, mining, railways |
| 2 | **Bharani** | Venus | FMCG, Agri | Wheat, edible oils, medicines, tea, agriculture, commodities |
| 3 | **Krittika** | Sun | Metal, Energy, Defence | Gold, diamonds, steel, international trade, military |
| 4 | **Rohini** | Moon | Auto, Banking, Energy, FMCG | Cotton, silver, crude oil, perfumes, auto, shipping |
| 5 | **Mrigashira** | Mars | IT, Pharma, Media | Food grains, pulses, jewelry, cinema, technology stocks |
| 6 | **Ardra** | Rahu | IT, Pharma, Energy | Edible oils, air transport, communication, IT |
| 7 | **Punarvasu** | Jupiter | Banking, Realty | Gold, silver, insurance, banking, real estate |
| 8 | **Pushya** | Saturn | FMCG, Energy, Agri | Dairy, agriculture, petroleum, government securities |
| 9 | **Ashlesha** | Mercury | Pharma, Energy | Pharma, chemicals, petroleum, international trade |
| 10 | **Magha** | Ketu | Banking, Defence | Stock markets, administration, politics, judiciary |
| 11 | **Purva Phalguni** | Venus | Media, FMCG, Realty | Entertainment, beauty, gems, media, hospitality |
| 12 | **Uttara Phalguni** | Sun | Banking, Media | Banking, media, public service, social sectors |
| 13 | **Hasta** | Moon | Banking, Metal | Silver, textiles, hospitals, marketing, brokerage |
| 14 | **Chitra** | Mars | Auto, Realty, Metal | Luxury goods, automobiles, petroleum, real estate |
| 15 | **Swati** | Rahu | Banking, IT, FMCG | Stock exchanges, cosmetics, artificial silk, financial management |
| 16 | **Vishakha** | Jupiter | Banking, FMCG, Agri | Gold, insurance, banking, agriculture, books |
| 17 | **Anuradha** | Saturn | IT, Pharma, Defence | Science, foreign trade, exploration, music |
| 18 | **Jyeshtha** | Mercury | Defence, Media | Military, government, administration, journalism |
| 19 | **Mula** | Ketu | Energy, Pharma, Metal | Petroleum, mining, atomic energy, medicine |
| 20 | **Purva Ashadha** | Venus | Energy, Media, FMCG | Maritime, water industries, aviation, entertainment |
| 21 | **Uttara Ashadha** | Sun | Defence, Infra, Realty | Government, law, military, construction, athletics |
| 22 | **Shravana** | Moon | Energy, Media, FMCG | Milk products, marine, mining, coal, broadcasting |
| 23 | **Dhanishtha** | Mars | Metal, Energy, Realty | Metals, iron, steel, atomic energy, stock markets |
| 24 | **Shatabhisha** | Rahu | Pharma, IT, Energy | Healthcare, electrical, pharma, aviation, film |
| 25 | **Purva Bhadrapada** | Jupiter | Pharma, Metal, Energy | Medicine, metallurgy, leather, pharma, environment |
| 26 | **Uttara Bhadrapada** | Saturn | FMCG, Agri | Jaggery, sugar, sesame, oils, agriculture, research |
| 27 | **Revati** | Mercury | IT, Realty, Media | Gemstones, pearls, shipping, maritime, hospitality |

---

## Sector Frequency by Ruling Planet

| Planet | Nakshatras | Dominant Sectors |
|--------|-----------|-----------------|
| Ketu | Ashwini, Magha, Mula | Pharma, Defence, Energy |
| Venus | Bharani, Purva Phalguni, Purva Ashadha | FMCG, Media, Energy |
| Sun | Krittika, Uttara Phalguni, Uttara Ashadha | Metal, Defence, Infra |
| Moon | Rohini, Hasta, Shravana | Auto, Banking, Energy |
| Mars | Mrigashira, Chitra, Dhanishtha | IT, Auto, Metal |
| Rahu | Ardra, Swati, Shatabhisha | IT, Pharma, Banking |
| Jupiter | Punarvasu, Vishakha, Purva Bhadrapada | Banking, FMCG, Pharma |
| Saturn | Pushya, Anuradha, Uttara Bhadrapada | FMCG, IT, Agri |
| Mercury | Ashlesha, Jyeshtha, Revati | Pharma, Defence, IT |

---

## Notes on Methodology

- **Lahiri ayanamsa** is the Indian government standard and the most widely used in financial astrology applications.
- Moon spends approximately 1 day in each nakshatra (range: 0.8–1.3 days depending on lunar speed).
- A nakshatra transition mid-day means mixed sector influence.
- The "Tikshna" (sharp) nakshatras — Ardra, Ashlesha, Jyeshtha, Mula — are traditionally high-volatility days across all sectors.
- Avoid new positions on Gandanta nakshatras (transition: Ashlesha→Magha, Jyeshtha→Mula, Revati→Ashwini).

---

## Sources

1. Screenshot: "Key Nakshatras for Trading" table (Ashwini through Dhanishtha) — original user source
2. [Nakshatras in the Stock Market — MarketAstroScience](https://www.marketastroscience.com/nakshatras-stock-market)
3. [27 Nakshatras and Profession — VastuGuruji](https://vastuguruji.com/27-nakshatras-and-profession/)
4. [Nakshatras Related Profession — AmbikaAstro](https://www.ambikaastro.com/nakshatras-related-profession/)

## Contradictions with Existing Wiki

None noted yet — this is the first astro-sector map in the vault.

## Pages Updated

- `analyses/Dashboard-UI-Roadmap.md` — Astro Timing Nakshatra feature
- `wiki/index.md` — added concept entry
