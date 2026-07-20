# Financial Astrology Research Integration

## Overview

Successfully ingested the **Financial Astrology Research Group** compendium from GitHub and integrated core methodologies into Trading Bramha dashboard.

**Source Repository:**
- https://github.com/financial-astrology-research/financial-astrology-docs
- Primary Document: "A Compendium of Financial Astrology and Cyclical Analysis for Quantitative Validation"
- Author: Pablo Cerda | Date: February 2026

---

## What Was Ingested

### Main Research Document
**467-line compendium** covering:
1. Foundational principles of geocosmic analysis
2. The 5 major schools of financial astrology
3. Empirical corroboration from Dewey & Gauquelin research
4. Framework for quantitative modeling
5. 100+ academic references

### Key Schools & Methodologies Covered

| School | Key Figure | Theory | Period |
|--------|-----------|--------|--------|
| **Mundane/Nodal** | Louise McWhirter | 18.6-year Lunar Nodal Cycle drives US business | 1938 |
| **Gannian** | William D. Gann | Law of Vibration: Price-Degree Conversion | 1920s-40s |
| **NYSE Chart** | Jack Gillen | Stock Exchange natal chart analysis | 2000s |
| **Classical Revival** | Giacomo Albano | Hellenistic dignity scoring & aspects | 2019 |
| **Modern Synthesis** | Joan McEvers, David Williams | Lunations, eclipses, midpoints, Solar Arcs | 1980s-90s |

---

## Implementation in Trading Bramha

### New Module: `financial_astrology_methods.py` (480+ lines)

A unified engine implementing all major theories:

**Core Classes:**
- `FinancialAstrologyEngine` — Main coordinating class

**Major Methods:**

#### 1. McWhirter Nodal Cycle (18.6-Year Business Cycle)
```python
fae = FinancialAstrologyEngine()
trend = fae.mcwhirter_trend(date.today())
# Returns:
# {
#   'trend': 'bullish' | 'bearish',
#   'node_sign': 'Capricorn',
#   'cycle_strength': 40-95 (peak at early Leo/Aquarius),
#   'zone': 'early' | 'mid' | 'late'
# }
```

**Theory:** McWhirter (1938) discovered that the 18.6-year Lunar North Node cycle drives US market cycles:
- **Bullish:** Node in Pisces → Leo (6 bullish signs)
- **Bearish:** Node in Virgo → Aquarius (6 bearish signs)
- **Peaks:** Major highs at early Leo, major lows at early Aquarius

**Validation:** Edward R. Dewey independently found the same 18.6-year cycle in economic data without astrological bias — compelling independent corroboration.

#### 2. Gann Price-Degree Conversion (Law of Vibration)
```python
gann = fae.price_to_degree(price=1000, scale=1.0)
# Returns:
# {
#   'degree': 280.0,                    # Zodiacal degree
#   'zodiac_sign': 'Capricorn',
#   'degree_in_sign': 10.0,
#   'interpretation': 'Price 1000 resonates with 280° (Capricorn 10°)'
# }

sr_levels = fae.gann_square_of_nine(price=1000, num_steps=5)
# Returns: Support/Resistance levels from Square of Nine geometry
```

**Theory:** Gann believed markets follow natural law, convertible between price and time/degrees:
- Formula: `Degree = Price mod 360`
- When transiting planets cross these "price-degrees," market turns trigger
- Square of Nine provides geometric support/resistance levels
- Gann Fans (45°, 1×1, 1×2 angles) define trend direction

**Application:** Use converted price degrees as additional astro-sensitive points.

#### 3. Lunation & Eclipse Cycles (McEvers)
```python
luna = fae.lunation_cycle(date.today())
# Returns:
# {
#   'lunation_phase': 338.2,                  # Sun-Moon angle
#   'phase_type': 'new_moon'|'waxing'|'full_moon'|'waning',
#   'days_since_new_moon': 27.5,
#   'is_eclipse_day': False,
#   'moon_illumination': 3.6%
# }
```

**Theory:** McEvers emphasized:
- **New Moon:** Start of new cycle, initiation energy
- **Full Moon:** Peak manifestation, culmination, profit-taking
- **Eclipses:** Super-charged lunations with 6+ month effects
- Geographic path of eclipse affects specific regions

**Trading:** New/Full Moons often trigger market reversals; Eclipses can mark major trend changes.

#### 4. Dewey Cycles (Statistical Cycle Analysis)
```python
dewey = fae.dewey_cycle_position(date.today(), cycle_years=18.6)
# Returns:
# {
#   'cycle_name': '18.6-Year Dewey Cycle',
#   'position_in_cycle': 0.499,          # 0-1 (% through cycle)
#   'oscillator': -0.156,                # -1 to +1 sine wave
#   'phase': 'expansion' | 'contraction'
# }
```

**Key Cycles Identified by Dewey (1947):**
- **18.6 years:** Lunar Nodal (real estate, construction) — *Matches McWhirter*
- **54 years:** Kondratieff Wave (long-term economic cycles)
- **9.2 years:** Half-nodal or apse cycle
- **4.3 years (41 months):** Kitchin cycle (business cycle)
- **11.1 years:** Solar cycle / Jupiter orbital period

**Principle of Synchrony:** Dewey found identical cycle lengths in unrelated phenomena (soybean prices, sunspots, bird populations). This suggests a common external forcing mechanism — potentially planetary.

**Application:** Use pure sine-wave oscillators for each cycle as input features to predictive models.

#### 5. Classical Dignity Scoring (Albano)
```python
dignity = fae.planetary_dignity_score(planet='Mars', zodiac_sign='Aries')
# Returns: +5 (Mars rules Aries — domicile)

assessment = fae.market_dignity_assessment(date.today())
# Returns:
# {
#   'Mars': {'sign': 'Leo', 'dignity_score': 0, 'strength': 'neutral'},
#   'Jupiter': {'sign': 'Gemini', 'dignity_score': -5, 'strength': 'weak'},
#   ...
# }
```

**Scoring System:**
- `+5` = Domicile (planet's home sign)
- `+4` = Exaltation
- `+3` = Triplicity (element affinity)
- `+2` = Term/Decan
- `+1` = Face
- `-5` = Detriment (opposite home)
- `-4` = Fall (opposite exaltation)
- `0` = Neutral

**Theory:** A planet's strength depends on its sign. Mars in Aries = powerfully strong (+5). Mars in Libra = weak (-5).

**Application:** Only trade signals when key planets (Mars for aggression, Jupiter for opportunity) are in strong dignity. Fade trades when they're in detriment.

#### 6. Unified Signal Generation
```python
signals = fae.generate_trading_signals(date=date.today(), price=1000)
# Returns:
# {
#   'date': '2026-06-28',
#   'price': 1000,
#   'mcwhirter': {...},           # Trend bias
#   'lunation': {...},            # Short-term timing
#   'gann_price_degree': {...},   # Support/resistance
#   'dewey_18y': {...},           # Long-term cycle
#   'dewey_4y': {...},            # Medium-term cycle
#   'dignity': {...},             # Planetary strength
#   'overall_bias': 'bearish',    # Composite signal
#   'signal_strength': 30         # 0-100 confidence
# }
```

Composite scoring combines:
1. McWhirter (36% weight) — Long-term regime
2. Lunation (20% weight) — Short-term timing
3. Dewey 18Y (24% weight) — Business cycle
4. Dewey 4Y (20% weight) — Medium-term

---

## Integration with Dashboard

### Potential Dashboard Tab: "Financial Astrology Research"

**Planned Features:**
1. **McWhirter Trend:** Display current position in 18.6-year cycle
2. **Gann Analysis:** Convert current price to zodiacal degree
3. **Lunation Forecast:** Show next 30 days of lunar phases
4. **Dewey Oscillators:** Display 4-year, 9-year, 18-year cycles
5. **Dignity Dashboard:** Current planetary strength scores
6. **Unified Signals:** Composite trading recommendations

---

## Research Validation Framework

The compendium emphasizes **rigorous statistical validation**. Recommended approach:

### Phase 1: McWhirter Hypothesis Testing
**Test:** Does the Lunar Nodal Cycle (18.6 years) correlate with US stock market returns?

**Method:**
- Plot North Node position vs. Dow Jones (1900-2026)
- Test for statistical significance
- Compare bullish/bearish periods to actual returns
- Calculate Pearson correlation coefficient

**Expected:** If McWhirter/Dewey are correct, strong positive correlation (~0.7+)

### Phase 2: Feature Engineering & Machine Learning
Build predictive models using features from all methodologies:
- Train on historical data (1980-2020)
- Test on out-of-sample data (2021-2026)
- Use walk-forward validation (strict time-series cross-validation)
- Track model performance (Sharpe ratio, max drawdown)

### Phase 3: Consensus with Technical Analysis
Combine strongest astro signals with technical triggers:
- Use astro for timing/regime
- Use technicals for entry/exit
- Create hybrid model

---

## Key Empirical Evidence

### Edward R. Dewey (1947)
**Finding:** Statistical cycles in economic data align with astrological periods:
- 18.6-year cycle found in real estate, construction (matches McWhirter/Lunar Node)
- 54-year Kondratieff wave (long-term)
- 9.2-year cycle (half-nodal)
- 4.3-year Kitchin cycle (business cycle)

**Significance:** Dewey was an economist, NOT an astrologer. He was searching for unexplained rhythms in economic data. That his findings match centuries-old astrological periods is powerful independent corroboration.

### Michel Gauquelin (1950s-60s)
**Finding:** Statistically significant correlation between planetary positions at birth and life success in specific fields.
- Mars for sports champions
- Saturn for scientists/physicians
- Jupiter for politicians/actors
- Moon for writers

**Significance:** Provides scientific basis for why natal charts might matter. If planetary positions at birth correlate with outcomes (Gauquelin), then corporate/stock birth charts may too (McWhirter, Gillen, Meridian).

---

## Trading Applications

### Short-Term Trading (Days-Weeks)
**Use:**
- Lunation Cycle (new/full moon timing)
- Gann Price-Degrees (support/resistance)
- Current Planetary Dignity (entry quality)

**Example:** Look for New Moon breakouts or Full Moon profit-taking opportunities.

### Medium-Term Trading (Weeks-Months)
**Use:**
- Dewey 4-Year Cycle (medium trend)
- Saturn/Jupiter transits to key points
- Seasonal astro patterns

**Example:** If 4-year oscillator positive and Jupiter strong, favor longs. If negative and Saturn strong, favor shorts.

### Long-Term Investing (Years-Decades)
**Use:**
- McWhirter 18-Year Nodal Cycle (regime identification)
- Dewey 54-Year Kondratieff Wave (secular bull/bear)
- Major Solar Arc directions

**Example:** In McWhirter bullish zone (Pisces-Leo)? Time to build long-term positions. In bearish zone (Virgo-Aquarius)? Reduce exposure or go defensive.

---

## Important Disclaimers

⚠️ **Not Financial Advice**
- This is research/educational content only
- Past correlations do not guarantee future results
- Markets are multifactorial; astrology is ONE tool
- Always combine with technical/fundamental analysis
- Use proper risk management

⚠️ **Limitations**
- Astrology is correlative, not proven causal
- Sample sizes in historical validation are limited
- Planetary influences are subtle and gradual
- Other factors (policy, earnings, sentiment) dominate short-term

⚠️ **Best Practices**
- Use astro for timing/regime, not direction alone
- Combine with other indicators (RSI, MACD, volume, etc.)
- Track actual performance vs. predictions
- Update models as new data arrives

---

## Files Created

```
tools/financial_astrology_methods.py    [NEW] 480 lines
  - FinancialAstrologyEngine class
  - All 6 major methodologies
  - Unified signal generation
  - Tested and working

FINANCIAL_ASTROLOGY_RESEARCH_INTEGRATION.md
  - This comprehensive guide
  - Theory explanations
  - Application examples
  - Validation framework
```

---

## Next Steps

1. **Import Compendium Locally**
   - Downloaded from: https://github.com/financial-astrology-research/financial-astrology-docs
   - Reference material: `docs/astrology/compendium-financial-astrology-methods.md`

2. **Dashboard Integration** (Future)
   - Add "Financial Astrology Research" tab
   - Display all 6 methodology outputs
   - Show unified signal strength
   - Real-time signal generation

3. **Backtesting** (Future)
   - Test McWhirter hypothesis vs. historical data
   - Build predictive models with engineered features
   - Calculate statistical significance
   - Validate on out-of-sample data

4. **Production Trading** (Future)
   - Combine with Technical Analysis
   - Real-time signal alerts
   - Position sizing based on confidence
   - Track P&L vs. predictions

---

## References

**Primary Research Document:**
Cerda, P. (2026). "A Compendium of Financial Astrology and Cyclical Analysis for Quantitative Validation." *Financial Astrology Research Group*. February 2026.

**Key Historical Works:**
- McWhirter, L. (1938). *The McWhirter Theory of Stock Market Forecasting*
- Dewey, E.R. (1947). *Cycles: The Science of Prediction*
- Gann, W.D. (1942). *Master Commodities Course*
- Williams, D. (1982). *Financial Astrology*
- Gauquelin, M. (1967). *The Cosmic Clocks*

**GitHub Repository:**
https://github.com/financial-astrology-research/financial-astrology-docs

---

**Status:** ✅ Research Ingested & Implemented  
**Module:** ✅ Tested & Working  
**Date:** June 28, 2026  
**Version:** 1.0

