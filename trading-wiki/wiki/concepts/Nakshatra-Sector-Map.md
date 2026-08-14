---
title: "Nakshatra Sector Map — Vedic Lunar Mansion Trading Guide"
category: concept
tags: [astro, nakshatra, vedic, lunar, sector, commodity, timing, guna, trading-psychology]
created: 2026-08-12
updated: 2026-08-12
sources: 4
related:
  - analyses/Dashboard-UI-Roadmap.md
  - sources/MarketAstroScience-Nakshatras-Stock-Market-2026-08-12.md
  - concepts/Mercury-Retrograde-Market-Cycle.md
  - concepts/Panchang.md
---

# Nakshatra Sector Map

The 27 Vedic lunar mansions (nakshatras) each span 13°20' of the sidereal zodiac. As the Moon transits through each nakshatra (~1 day), two complementary frameworks apply:

1. **Commodity/Sector affinity** (from Vedic tradition): which sectors see elevated activity or directional bias  
2. **Trading psychology** (from [[sources/MarketAstroScience-Nakshatras-Stock-Market-2026-08-12]]): what trading style and timeframe the nakshatra's energy supports

**Use as context, not signal.** Nakshatra does not predict direction — it narrows the field and shapes approach.

---

## How the Dashboard Uses This

The Astro Timing page computes the Moon's geocentric ecliptic longitude via PyEphem, subtracts the Lahiri ayanamsa (~23.85° for 2026) for the sidereal zodiac, then divides by 13.333° to identify the nakshatra. A 7-day forward table shows sectors and trading style for each day.

**Ayanamsa used:** Lahiri, ~23.85° (2026). Update `_AYANAMSA` in `astro_trading.py` annually.

---

## Complete 27-Nakshatra Reference

| # | Nakshatra | Planet | Guna | NSE Sectors | Commodity Theme | Timeframe | Trading Style |
|---|-----------|--------|------|-------------|-----------------|-----------|---------------|
| 1 | **Ashwini** | Ketu | Sattva | Pharma, Auto, Metal | Rice, iron, copper, mining, railways | Intraday | Momentum, scalp, high-vol sectors |
| 2 | **Bharani** | Venus | Rajas | FMCG, Agri | Wheat, edible oils, food, medicines | Long-term | Value investing, dividends, real estate |
| 3 | **Krittika** | Sun | Rajas | Metal, Energy, Defence | Gold, diamonds, steel, int'l trade | Swing | Growth stocks, tech/innovation, options |
| 4 | **Rohini** | Moon | Rajas | Auto, Banking, Energy, FMCG | Cotton, silver, crude oil, auto, shipping | Long-term | Blue-chip, real estate, agriculture |
| 5 | **Mrigashira** | Mars | Sattva | IT, Pharma, Media | Tech, cinema, jewelry, food grains | Swing | Technical analysis, pharma, internet tech |
| 6 | **Ardra** | Rahu | Tamas | IT, Energy | Edible oils, air transport, communication | Intraday | Volatility/crisis trading, contrarian options |
| 7 | **Punarvasu** | Jupiter | Sattva | Banking, Realty | Gold, silver, insurance, real estate | Positional | Recovery plays, value investing, large-caps |
| 8 | **Pushya** | Saturn | Sattva | FMCG, Energy, Agri | Dairy, agriculture, petroleum, govt bonds | Long-term | Conservative, blue-chip, bonds, ETFs |
| 9 | **Ashlesha** | Mercury | Tamas | Pharma, Energy | Pharma, chemicals, petroleum, int'l trade | Intraday | Event-driven, HFT, stealth analytical |
| 10 | **Magha** | Ketu | Tamas | Banking, Defence | Stock markets, admin, politics | Positional | Trend-following, sector leaders, Nifty50 |
| 11 | **Purva Phalguni** | Venus | Rajas | Media, FMCG, Realty | Entertainment, luxury, consumer spending | Swing | Thematic, sentiment-driven, popular trends |
| 12 | **Uttara Phalguni** | Sun | Sattva | Banking, Media | Public service, social sectors, finance | Long-term | SIPs, index investing, rule-based systems |
| 13 | **Hasta** | Moon | Rajas | Banking, Metal | Silver, textiles, hospitals, brokerage | Intraday | Systematic entries, patterns, back-tested |
| 14 | **Chitra** | Mars | Tamas | Auto, Realty, Metal | Luxury goods, brand identity, automobiles | Positional | Rotational, multi-sector, precision entries |
| 15 | **Swati** | Rahu | Rajas | Banking, IT, FMCG | Stock exchanges, cosmetics, financial mgmt | Swing | Policy-driven, data-driven, algorithmic |
| 16 | **Vishakha** | Jupiter | Rajas | Banking, FMCG, Agri | Gold, insurance, agriculture, breakouts | Swing | Goal-oriented trend-following, earnings plays |
| 17 | **Anuradha** | Saturn | Sattva | IT, Pharma, Defence | Science, foreign trade, exploration | Positional | Value investing, defensive, low-volatility |
| 18 | **Jyeshtha** | Mercury | Rajas | Defence, Media | Military, government, administration | Swing | Contrarian, reversal (VWAP, MACD div, Fib) |
| 19 | **Mula** | Ketu | Tamas | Energy, Pharma, Metal | Petroleum, mining, atomic energy, medicine | Intraday | Bottom-fishing, event-driven, macro/EW |
| 20 | **Purva Ashadha** | Venus | Rajas | Energy, Media, EV/Clean | Maritime, water, aviation, EV, green energy | Swing | Thematic (EV, green), volume breakouts |
| 21 | **Uttara Ashadha** | Sun | Sattva | Defence, Infra, Realty | Government, law, military, construction | Long-term | SIPs, diversified, fundamental, balanced |
| 22 | **Shravana** | Moon | Sattva | Energy, Media, FMCG | Milk products, marine, mining, broadcasting | Long-term | Data-driven, earnings-based, news-reactive |
| 23 | **Dhanishtha** | Mars | Tamas | Metal, Energy, Realty | Metals, iron, steel, stock markets | Intraday | Momentum, high-vol intraday, swing |
| 24 | **Shatabhisha** | Rahu | Tamas | Pharma, IT, Energy | Healthcare, pharma, electrical, film | Positional | Contrarian, derivatives (options/futures) |
| 25 | **Purva Bhadrapada** | Jupiter | Tamas | Pharma, Metal, Energy | Medicine, metallurgy, pharma, environment | Positional | Thematic, sector rotation, ethics/ESG |
| 26 | **Uttara Bhadrapada** | Saturn | Tamas | FMCG, Agri | Jaggery, sugar, sesame, oils, agriculture | Long-term | Wealth preservation, deep value, diversified |
| 27 | **Revati** | Mercury | Sattva | IT, Realty, Media | Gemstones, pearls, shipping, maritime | Swing | Intuitive scalping, sentiment analysis |

---

## Guna — Market Condition Key

The Guna of each nakshatra provides a daily market-condition proxy:

| Guna | Count | Market Character | Recommended Approach |
|------|-------|-----------------|---------------------|
| **Sattva** | 9 | Clear, analytical, balanced | Systematic, research-driven, good for initiating new positions |
| **Rajas** | 9 | Active, volatile, passionate | Momentum, swing trading, news/event driven |
| **Tamas** | 9 | Heavy, slow, or chaotic | Contrarian, defensive, or avoid — not trend-following days |

**Tamas nakshatras:** Ardra, Ashlesha, Magha, Chitra, Mula, Dhanishtha, Shatabhisha, Purva Bhadrapada, Uttara Bhadrapada

---

## Trading Timeframe by Nakshatra

| Timeframe | Nakshatras |
|-----------|-----------|
| **Intraday / Scalp** | Ashwini, Ardra, Hasta, Ashlesha, Mula, Dhanishtha |
| **Swing (days–weeks)** | Mrigashira, Krittika, Purva Phalguni, Swati, Vishakha, Jyeshtha, Purva Ashadha, Revati |
| **Positional (weeks–months)** | Magha, Punarvasu, Chitra, Anuradha, Shatabhisha, Purva Bhadrapada |
| **Long-term / SIP** | Bharani, Rohini, Pushya, Uttara Phalguni, Uttara Ashadha, Shravana, Uttara Bhadrapada |

---

## Sector Frequency by Ruling Planet

| Planet | Nakshatras | Dominant Sectors |
|--------|-----------|-----------------|
| Ketu | Ashwini, Magha, Mula | Pharma, Defence, Energy |
| Venus | Bharani, Purva Phalguni, Purva Ashadha | FMCG, Media, Energy/EV |
| Sun | Krittika, Uttara Phalguni, Uttara Ashadha | Metal, Defence, Infra |
| Moon | Rohini, Hasta, Shravana | Auto, Banking, Energy |
| Mars | Mrigashira, Chitra, Dhanishtha | IT, Auto, Metal |
| Rahu | Ardra, Swati, Shatabhisha | IT, Pharma, Banking |
| Jupiter | Punarvasu, Vishakha, Purva Bhadrapada | Banking, FMCG, Pharma |
| Saturn | Pushya, Anuradha, Uttara Bhadrapada | FMCG, IT, Agri |
| Mercury | Ashlesha, Jyeshtha, Revati | Pharma, Defence, IT |

---

## Special Classifications

### Tikshna (Sharp/Cruel) — High-Volatility Days
Ardra, Ashlesha, Jyeshtha, Mula. Traditionally unfavorable for new long-term investments; suited for contrarian short-term plays or avoid entirely.

### Gandanta — Avoid New Positions
Junction nakshatras at water-fire sign boundaries:
- **Ashlesha → Magha** (Cancer–Leo)
- **Jyeshtha → Mula** (Scorpio–Sagittarius)
- **Revati → Ashwini** (Pisces–Aries)

These transitions carry "unresolved karma" in Vedic tradition; practically, they often coincide with whipsaw price action near open/close.

### New-Age Sector Links (MarketAstroScience source)
- **Purva Ashadha** → EV, Green Energy, Sustainability (Venus/water energy; first source to explicitly name NSE's emerging clean-energy theme)
- **Shatabhisha** → Healthcare + derivatives/leverage (Rahu; contrarian buy-when-others-fear)
- **Chitra** → Luxury brand identity (Mars; premium consumer names like Titan, Page Industries)

---

## Notes on Methodology

- **Lahiri ayanamsa** is the Indian government standard; ~23.85° for 2026.
- Moon spends ~1 day per nakshatra (range: 0.8–1.3 days depending on lunar speed).
- A transition mid-market-day means mixed energy for that session.
- The two frameworks (commodity affinity vs trading psychology) are **complementary, not competing**. Commodity map answers "which sectors?" — psychology map answers "how to trade them?"
- **Ashwini divergence noted:** commodity tradition = Pharma/Auto/Metal; MarketAstroScience = intraday momentum/crypto. Ketu's explosive energy supports both — different time horizons.

---

## Sources

1. Screenshot: "Key Nakshatras for Trading" table (Ashwini–Dhanishtha) — commodity tradition, user source
2. [[sources/MarketAstroScience-Nakshatras-Stock-Market-2026-08-12]] — trading psychology + guna + timeframe for all 27
3. [27 Nakshatras and Profession — VastuGuruji](https://vastuguruji.com/27-nakshatras-and-profession/)
4. [Nakshatras Related Profession — AmbikaAstro](https://www.ambikaastro.com/nakshatras-related-profession/)
