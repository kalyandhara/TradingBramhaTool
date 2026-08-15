#!/usr/bin/env python3
"""
financial_astrology_methods.py
Integration of financial astrology research methodologies into Trading Bramha.

Implements core theories from:
- Louise McWhirter (Nodal Cycle)
- William D. Gann (Price-Degree Conversion, Law of Vibration)
- Jack Gillen (NYSE Chart Analysis)
- Edward R. Dewey (Cycle Analysis)
- Joan McEvers (Lunations & Eclipses)
- David Williams (Midpoints, Solar Arcs)
- Giacomo Albano (Classical Dignity Scoring)

Reference:
  Cerda, P. (2026). "A Compendium of Financial Astrology and Cyclical Analysis
  for Quantitative Validation." Financial Astrology Research Group.

Usage:
  from financial_astrology_methods import FinancialAstrologyEngine
  fae = FinancialAstrologyEngine()
  signals = fae.generate_trading_signals(date.today(), price=1000)
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
import math

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from ephem import Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Observer
    HAS_EPHEM = True
except ImportError:
    HAS_EPHEM = False


class FinancialAstrologyEngine:
    """
    Unified engine implementing major financial astrology methodologies.

    Theories covered:
    1. McWhirter Nodal Cycle (18.6-year U.S. business cycle)
    2. Gann Price-Degree Conversion (price as zodiacal longitude)
    3. Gillen NYSE Analysis (stock exchange natal chart)
    4. Dewey Cycles (statistical cycle analysis)
    5. McEvers Lunations (moon phases & eclipses)
    6. Classical Dignity Scoring (planetary strength assessment)
    """

    # Zodiac signs and degrees
    ZODIAC_SIGNS = [
        'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
        'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
    ]

    # Planetary orbital periods (years) for cycle analysis
    PLANETARY_PERIODS = {
        'Mercury': 0.24,
        'Venus': 0.62,
        'Mars': 1.88,
        'Jupiter': 11.86,
        'Saturn': 29.46,
        'Uranus': 84.01,
        'Neptune': 164.79,
        'Pluto': 247.94,
    }

    # Key synodic cycles (years)
    SYNODIC_CYCLES = {
        'Jupiter_Saturn': 20.0,  # Business cycle
        'Jupiter_Uranus': 13.8,  # Bull markets
        'Saturn_Neptune': 36.4,  # Bear markets
        'Lunar_Nodal': 18.6,     # McWhirter cycle
    }

    # Planetary dignities (essential dignity scoring)
    DIGNITIES = {
        'Aries': {'Sun': 5, 'Moon': 0, 'Mercury': 0, 'Venus': -5, 'Mars': 5, 'Jupiter': 0, 'Saturn': -5},
        'Taurus': {'Sun': 0, 'Moon': 5, 'Mercury': -5, 'Venus': 5, 'Mars': -5, 'Jupiter': 0, 'Saturn': 0},
        'Gemini': {'Sun': 0, 'Moon': 0, 'Mercury': 5, 'Venus': 0, 'Mars': 0, 'Jupiter': 0, 'Saturn': 0},
        'Cancer': {'Sun': 0, 'Moon': 5, 'Mercury': 0, 'Venus': 0, 'Mars': 0, 'Jupiter': 0, 'Saturn': -5},
        'Leo': {'Sun': 5, 'Moon': 0, 'Mercury': 0, 'Venus': 0, 'Mars': 0, 'Jupiter': 5, 'Saturn': -5},
        'Virgo': {'Sun': -5, 'Moon': 0, 'Mercury': 5, 'Venus': -5, 'Mars': -5, 'Jupiter': -5, 'Saturn': 0},
        'Libra': {'Sun': 0, 'Moon': 0, 'Mercury': 0, 'Venus': 5, 'Mars': -5, 'Jupiter': 0, 'Saturn': 0},
        'Scorpio': {'Sun': -5, 'Moon': 0, 'Mercury': 0, 'Venus': -5, 'Mars': 5, 'Jupiter': 0, 'Saturn': 0},
        'Sagittarius': {'Sun': 0, 'Moon': 0, 'Mercury': -5, 'Venus': 0, 'Mars': 0, 'Jupiter': 5, 'Saturn': 0},
        'Capricorn': {'Sun': -5, 'Moon': 0, 'Mercury': 0, 'Venus': 0, 'Mars': 0, 'Jupiter': -5, 'Saturn': 5},
        'Aquarius': {'Sun': 0, 'Moon': 0, 'Mercury': 0, 'Venus': 0, 'Mars': 0, 'Jupiter': 0, 'Saturn': 0},
        'Pisces': {'Sun': 0, 'Moon': 0, 'Mercury': -5, 'Venus': 5, 'Mars': 0, 'Jupiter': 5, 'Saturn': -5},
    }

    def __init__(self):
        """Initialize the engine."""
        pass

    # ========================================================================
    # MCWHIRTER NODAL CYCLE (18.6-Year U.S. Business Cycle)
    # ========================================================================

    def mcwhirter_trend(self, d: date) -> Dict:
        """
        Determine U.S. market trend based on Lunar Node position (McWhirter, 1938).

        Theory: The North Node's transit through the zodiac drives an 18.6-year
        business cycle. Bullish when in Pisces-Leo, bearish in Virgo-Aquarius.

        Returns:
            {
                'trend': 'bullish' | 'bearish',
                'node_sign': 'Leo', etc.,
                'cycle_strength': 0-100 (peak at early Leo or Aquarius),
                'zone': 'early' | 'mid' | 'late'
            }
        """
        # Approximate Lunar Node position
        # Reference: Jan 1, 2000, North Node at ~19° Taurus
        ref_date = date(2000, 1, 1)
        ref_node_degree = 19 + (4 * 30)  # Taurus = ~149°

        days_elapsed = (d - ref_date).days
        years_elapsed = days_elapsed / 365.25
        cycle_period = 18.6

        # Node travels ~20° per year through zodiac (360° / 18.6 = 19.35°/year)
        node_degree = (ref_node_degree + (years_elapsed * 360 / cycle_period)) % 360
        node_sign_idx = int(node_degree / 30)
        node_sign = self.ZODIAC_SIGNS[node_sign_idx]
        degree_in_sign = node_degree % 30

        # McWhirter zones
        bullish_signs = [0, 1, 2, 3, 4, 5]  # Aries-Leo
        bearish_signs = [6, 7, 8, 9, 10, 11]  # Libra-Pisces

        trend = 'bullish' if node_sign_idx in bullish_signs else 'bearish'

        # Cycle strength peaks at early Leo (major high) or early Aquarius (major low)
        if (node_sign_idx == 4 and degree_in_sign < 10) or (node_sign_idx == 10 and degree_in_sign < 10):
            strength = 95
            zone = 'peak'
        elif degree_in_sign < 10:
            strength = 80
            zone = 'early'
        elif degree_in_sign < 20:
            strength = 60
            zone = 'mid'
        else:
            strength = 40
            zone = 'late'

        return {
            'trend': trend,
            'node_sign': node_sign,
            'degree_in_sign': round(degree_in_sign, 1),
            'cycle_strength': strength,
            'zone': zone,
            'years_in_cycle': round(years_elapsed % cycle_period, 1),
        }

    # ========================================================================
    # GANN PRICE-DEGREE CONVERSION (Law of Vibration)
    # ========================================================================

    def price_to_degree(self, price: float, scale: float = 1.0) -> Dict:
        """
        Convert price to zodiacal degree (Gann's Law of Vibration).

        Formula: D = (Price / scale) mod 360

        Returns:
            {
                'price': price,
                'price_scaled': price / scale,
                'degree': 0-360,
                'zodiac_sign': 'Leo',
                'degree_in_sign': 15.5,
                'interpretation': 'Support/Resistance at this degree'
            }
        """
        scaled_price = price / scale
        degree = math.fmod(scaled_price, 360)

        sign_idx = int(degree / 30)
        degree_in_sign = degree % 30

        return {
            'price': price,
            'price_scaled': scaled_price,
            'degree': round(degree, 2),
            'zodiac_sign': self.ZODIAC_SIGNS[sign_idx],
            'degree_in_sign': round(degree_in_sign, 2),
            'interpretation': f'Price {price} resonates with {round(degree, 1)}° ({self.ZODIAC_SIGNS[sign_idx]})',
        }

    def gann_square_of_nine(self, price: float, num_steps: int = 5) -> List[Dict]:
        """
        Calculate Square of Nine support/resistance levels around a price.

        The Square of Nine creates S/R through specific geometric relationships.
        Key angles: 0°, 45°, 90°, 135°, 180°, etc.

        Returns list of S/R levels.
        """
        sqrt_price = math.sqrt(price)
        levels = []

        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            # Simplified: treat each 45° as a specific multiplier
            multiplier = 1 + (angle / 360) * 0.2  # Example scaling
            level = price * multiplier
            levels.append({
                'angle_degrees': angle,
                'level': round(level, 2),
                'distance_from_price': round(level - price, 2),
            })

        return sorted(levels, key=lambda x: abs(x['distance_from_price']))[:num_steps]

    # ========================================================================
    # MCEVER'S LUNATIONS & ECLIPSES
    # ========================================================================

    def lunation_cycle(self, d: date) -> Dict:
        """
        Determine position in lunar month cycle (McEvers methodology).

        New Moon (conjunction) and Full Moon (opposition) are key turning points.
        Eclipses are super-charged lunations with longer-term effects.

        Returns:
            {
                'lunation_phase': 0-360° (Sun-Moon angle),
                'phase_type': 'new_moon' | 'waxing' | 'full_moon' | 'waning',
                'days_since_new_moon': float,
                'is_eclipse_day': bool,
                'eclipse_type': 'solar' | 'lunar' | None
            }
        """
        if not HAS_EPHEM:
            return self._lunation_cycle_approximate(d)

        try:
            observer = Observer()
            observer.date = datetime.combine(d, datetime.min.time())

            sun = Sun(observer)
            moon = Moon(observer)

            # Calculate Sun-Moon angle
            sun_lon = float(sun.hlon) * 180 / math.pi
            moon_lon = float(moon.hlon) * 180 / math.pi

            phase = (moon_lon - sun_lon) % 360
            days_since_new = (phase / 360) * 29.53

            # Simplified eclipse detection (actual detection requires detailed calculations)
            is_eclipse = abs(phase) < 2 or abs(phase - 180) < 2

            if phase < 2 or phase > 358:
                phase_type = 'new_moon'
            elif phase < 90:
                phase_type = 'waxing'
            elif abs(phase - 180) < 5:
                phase_type = 'full_moon'
            else:
                phase_type = 'waning'

            return {
                'lunation_phase': round(phase, 1),
                'phase_type': phase_type,
                'days_since_new_moon': round(days_since_new, 1),
                'is_eclipse_day': is_eclipse,
                'moon_illumination': round((1 - math.cos(math.radians(phase))) / 2 * 100, 1),
            }
        except Exception as e:
            return self._lunation_cycle_approximate(d)

    def _lunation_cycle_approximate(self, d: date) -> Dict:
        """Approximate lunation cycle using known reference dates."""
        ref_new_moon = date(2000, 1, 6)  # Reference new moon
        days_since_ref = (d - ref_new_moon).days
        lunation_cycle_days = 29.53
        cycle_position = (days_since_ref % lunation_cycle_days) / lunation_cycle_days
        phase = cycle_position * 360

        if phase < 2 or phase > 358:
            phase_type = 'new_moon'
        elif phase < 90:
            phase_type = 'waxing'
        elif abs(phase - 180) < 5:
            phase_type = 'full_moon'
        else:
            phase_type = 'waning'

        return {
            'lunation_phase': round(phase, 1),
            'phase_type': phase_type,
            'days_since_new_moon': round(days_since_ref % lunation_cycle_days, 1),
            'is_eclipse_day': False,
            'moon_illumination': round((1 + math.cos(math.radians(phase))) / 2 * 100, 1),
        }

    # ========================================================================
    # DEWEY CYCLES (Statistical Cycle Analysis)
    # ========================================================================

    def dewey_cycle_position(self, d: date, cycle_years: float, ref_date: date = None) -> Dict:
        """
        Calculate position within Dewey's identified economic cycles.

        Key cycles identified by Dewey:
        - 18.6 years: Lunar Nodal (real estate, construction)
        - 9.2 years: Half-nodal or apse cycle
        - 4.3 years (41 months): Kitchin cycle (short business cycle)
        - 54 years: Kondratieff wave (long-term)

        Returns:
            {
                'cycle_name': '18.6-Year Nodal Cycle',
                'cycle_period': 18.6,
                'position_in_cycle': 0.0-1.0,
                'years_elapsed': float,
                'oscillator': -1.0 to +1.0 (sine wave)
            }
        """
        if ref_date is None:
            ref_date = date(1980, 1, 1)

        days_elapsed = (d - ref_date).days
        years_elapsed = days_elapsed / 365.25
        position = (years_elapsed % cycle_years) / cycle_years
        oscillator = math.sin(2 * math.pi * position)

        return {
            'cycle_name': f'{cycle_years}-Year Dewey Cycle',
            'cycle_period': cycle_years,
            'position_in_cycle': round(position, 3),
            'years_elapsed_in_cycle': round(years_elapsed % cycle_years, 2),
            'oscillator': round(oscillator, 3),
            'phase': 'expansion' if oscillator > 0 else 'contraction',
        }

    # ========================================================================
    # CLASSICAL DIGNITY SCORING (Albano Methodology)
    # ========================================================================

    def planetary_dignity_score(self, planet: str, zodiac_sign: str) -> int:
        """
        Score a planet's essential dignity in a given sign (Albano, 1-5 scale).

        Scoring:
         +5 = Domicile (home sign)
         +4 = Exaltation
         +3 = Triplicity (element affinity)
         +2 = Term/Decan
         +1 = Face
         -5 = Detriment (opposite home)
         -4 = Fall (opposite exaltation)
          0 = Neutral
        """
        if planet not in self.DIGNITIES.get(zodiac_sign, {}):
            return 0
        return self.DIGNITIES[zodiac_sign][planet]

    def market_dignity_assessment(self, d: date) -> Dict:
        """
        Assess the dignity of key trading planets on a given date.

        Returns strength scores for Sun, Moon, Mars, Jupiter, Saturn.
        """
        # Simplified: use approximate planetary positions
        # For production, use actual ephemeris data

        assessments = {}
        for planet in ['Sun', 'Moon', 'Mars', 'Jupiter', 'Saturn']:
            # Approximate: each planet in its home sign on specific dates
            # This is a placeholder; actual implementation needs ephemeris

            sign_idx = hash(f"{d.isoformat()}_{planet}") % 12
            sign = self.ZODIAC_SIGNS[sign_idx]
            score = self.planetary_dignity_score(planet, sign)

            assessments[planet] = {
                'planet': planet,
                'sign': sign,
                'dignity_score': score,
                'strength': 'strong' if score > 0 else ('weak' if score < 0 else 'neutral'),
            }

        return assessments

    # ========================================================================
    # UNIFIED TRADING SIGNAL GENERATION
    # ========================================================================

    def generate_trading_signals(self, d: date, price: float = None) -> Dict:
        """
        Generate comprehensive trading signals based on all methods.

        Combines:
        1. McWhirter Nodal Trend (long-term regime)
        2. Lunation Cycle (short-term timing)
        3. Gann Price-Degree (support/resistance)
        4. Dewey Cycles (multi-timeframe)
        5. Dignity Assessment (planetary strength)

        Returns:
            {
                'date': date,
                'price': price,
                'signals': {
                    'mcwhirter': {...},
                    'lunation': {...},
                    'gann': {...},
                    'dewey': {...},
                    'dignity': {...}
                },
                'overall_bias': 'bullish' | 'bearish' | 'neutral',
                'strength': 0-100
            }
        """
        signals = {
            'date': str(d),
            'price': price,
            'mcwhirter': self.mcwhirter_trend(d),
            'lunation': self.lunation_cycle(d),
            'dewey_18y': self.dewey_cycle_position(d, 18.6),
            'dewey_4y': self.dewey_cycle_position(d, 4.3),
            'dignity': self.market_dignity_assessment(d),
        }

        if price is not None:
            signals['gann_price_degree'] = self.price_to_degree(price)
            signals['gann_sr_levels'] = self.gann_square_of_nine(price)

        # Overall bias
        mcwhirter_bias = 1 if signals['mcwhirter']['trend'] == 'bullish' else -1
        lunation_bias = 0.5 if signals['lunation']['phase_type'] == 'waxing' else -0.5
        dewey_18_bias = 1 if signals['dewey_18y']['oscillator'] > 0 else -1
        dewey_4_bias = 0.5 if signals['dewey_4y']['oscillator'] > 0 else -0.5

        composite_score = mcwhirter_bias + lunation_bias + dewey_18_bias + dewey_4_bias

        if composite_score > 1.5:
            overall_bias = 'bullish'
            strength = min(95, 50 + (composite_score * 15))
        elif composite_score < -1.5:
            overall_bias = 'bearish'
            strength = min(95, 50 - (composite_score * 15))
        else:
            overall_bias = 'neutral'
            strength = 30

        signals['overall_bias'] = overall_bias
        signals['signal_strength'] = round(strength, 0)

        return signals


def main():
    """Demo/test the financial astrology engine."""
    fae = FinancialAstrologyEngine()
    today = date.today()

    print("=== Financial Astrology Engine Demo ===\n")

    # McWhirter
    mcw = fae.mcwhirter_trend(today)
    print(f"McWhirter Trend: {mcw['trend'].upper()}")
    print(f"  Node in {mcw['node_sign']} ({mcw['degree_in_sign']}°)")
    print(f"  Cycle Strength: {mcw['cycle_strength']}/100\n")

    # Lunation
    luna = fae.lunation_cycle(today)
    print(f"Lunation Cycle: {luna['phase_type'].upper()}")
    print(f"  Phase: {luna['lunation_phase']}° | Illumination: {luna['moon_illumination']}%\n")

    # Gann (test with price)
    price = 1000
    gann = fae.price_to_degree(price)
    print(f"Gann Price-Degree (${price}):")
    print(f"  {gann['degree']}° = {gann['zodiac_sign']} {gann['degree_in_sign']}°\n")

    # Dewey
    dewey = fae.dewey_cycle_position(today, 18.6)
    print("Dewey 18.6-Year Cycle:")
    print(f"  Position: {dewey['position_in_cycle']*100:.1f}% | Phase: {dewey['phase']}\n")

    # Unified signal
    signals = fae.generate_trading_signals(today, price=price)
    print(f"Overall Trading Bias: {signals['overall_bias'].upper()}")
    print(f"Signal Strength: {signals['signal_strength']}/100")


if __name__ == '__main__':
    main()
