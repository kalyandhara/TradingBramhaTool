#!/usr/bin/env python3
"""
astro_trading.py
Astrology-based trading indicators and timing signals.
Integrates with AstroHora data and provides market-timing analysis.

Usage:
  from astro_trading import AstroIndicators
  ai = AstroIndicators(market_tz='Asia/Kolkata')
  timing = ai.get_trading_timing(date(2024, 12, 20))
"""

from datetime import date, datetime, timedelta, time
from typing import Dict, List, Tuple
import math
import pytz

try:
    from ephem import Sun, Moon, Mars, Venus, Mercury, Jupiter, Saturn, Observer
    HAS_EPHEM = True
except ImportError:
    HAS_EPHEM = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class AstroIndicators:
    """Calculate astrological timing and trading signals."""

    # Lunar cycle phases (days)
    LUNAR_CYCLE = 29.53

    # Sacred astrological timings
    SUNRISE_BUFFER_MINS = 15  # Minutes after sunrise for optimal entry
    SUNSET_BUFFER_MINS = 15   # Minutes before sunset for exit

    # Latitude/Longitude for major Indian cities (for birth chart lookups)
    CITIES = {
        'Mumbai': (19.0760, 72.8777),
        'Delhi': (28.7041, 77.1025),
        'Bangalore': (12.9716, 77.5946),
        'Chennai': (13.0827, 80.2707),
        'Kolkata': (22.5726, 88.3639),
        'Hyderabad': (17.3850, 78.4867),
    }

    def __init__(self, market_tz: str = 'Asia/Kolkata', city: str = 'Mumbai'):
        """
        Initialize astrology calculator.

        Args:
            market_tz: Timezone for market timing (default: IST)
            city: Default city for calculations
        """
        self.market_tz = pytz.timezone(market_tz)
        self.city = city
        if city not in self.CITIES:
            raise ValueError(f"Unknown city: {city}. Use: {list(self.CITIES.keys())}")
        self.lat, self.lon = self.CITIES[city]

    def get_lunar_phase(self, d: date) -> Dict:
        """
        Get lunar phase for a given date.

        Returns:
            {phase: 'new'|'waxing'|'full'|'waning', illumination: 0-100, days_in_cycle}
        """
        if not HAS_EPHEM:
            return self._lunar_phase_approximate(d)

        try:
            observer = Observer()
            observer.date = datetime.combine(d, time(12, 0))
            observer.lat, observer.lon = str(self.lat), str(self.lon)

            moon = Moon(observer)
            next_full = self._next_phase(observer.date, 'full')
            next_new = self._next_phase(observer.date, 'new')

            # Estimate illumination
            illumination = moon.phase

            # Determine phase
            if next_new < next_full:
                phase = 'waning'
            else:
                phase = 'waxing'

            cycle_day = (illumination / 100) * self.LUNAR_CYCLE

            return {
                'phase': phase,
                'illumination': round(illumination, 2),
                'cycle_day': round(cycle_day, 1),
                'cycle_length': self.LUNAR_CYCLE,
            }
        except Exception as e:
            print(f"Ephem calculation error: {e}")
            return self._lunar_phase_approximate(d)

    def _lunar_phase_approximate(self, d: date) -> Dict:
        """Approximate lunar phase using known reference dates."""
        # New Moon: Jan 29, 2024 (IST)
        ref_new_moon = date(2024, 1, 29)
        days_since = (d - ref_new_moon).days
        cycle_day = days_since % self.LUNAR_CYCLE

        if cycle_day < 7.4:
            phase = 'new'
        elif cycle_day < 14.75:
            phase = 'waxing'
        elif cycle_day < 22.1:
            phase = 'full'
        else:
            phase = 'waning'

        illumination = round(100 * math.sin(2 * math.pi * cycle_day / self.LUNAR_CYCLE) * 0.5 + 50, 1)

        return {
            'phase': phase,
            'illumination': illumination,
            'cycle_day': round(cycle_day, 1),
            'cycle_length': self.LUNAR_CYCLE,
        }

    def _next_phase(self, obs_date, phase_type):
        """Find next lunar phase (ephem helper)."""
        from ephem import next_full_moon, next_new_moon, previous_full_moon, previous_new_moon

        if phase_type == 'full':
            return next_full_moon(obs_date)
        elif phase_type == 'new':
            return next_new_moon(obs_date)
        return obs_date

    def get_trading_timing(self, d: date) -> Dict:
        """
        Get optimal trading timing for a given date based on astrology.

        Returns:
            {
                lunar_phase: {...},
                solar_timing: {sunrise, sunset, optimal_entry, optimal_exit},
                vimshottari_intensity: 0-100 (market volatility indicator),
                recommendations: [...]
            }
        """
        lunar = self.get_lunar_phase(d)
        solar = self._get_solar_timing(d)
        intensity = self._calculate_market_intensity(d)

        recommendations = self._generate_recommendations(lunar, solar, intensity)

        return {
            'date': str(d),
            'city': self.city,
            'lunar_phase': lunar,
            'solar_timing': solar,
            'market_intensity': round(intensity, 1),
            'recommendations': recommendations,
        }

    def _get_solar_timing(self, d: date) -> Dict:
        """Calculate sunrise/sunset and optimal trading windows."""
        if not HAS_EPHEM:
            return self._solar_timing_approximate(d)

        try:
            observer = Observer()
            observer.date = datetime.combine(d, time(0, 0))
            observer.lat, observer.lon = str(self.lat), str(self.lon)

            sun = Sun(observer)
            sunrise = observer.next_rising(sun)
            sunset = observer.next_setting(sun)

            # Convert to market timezone
            sr_time = self._ephem_to_datetime(sunrise).astimezone(self.market_tz)
            ss_time = self._ephem_to_datetime(sunset).astimezone(self.market_tz)

            optimal_entry = sr_time + timedelta(minutes=self.SUNRISE_BUFFER_MINS)
            optimal_exit = ss_time - timedelta(minutes=self.SUNSET_BUFFER_MINS)

            return {
                'sunrise': sr_time.strftime('%H:%M'),
                'sunset': ss_time.strftime('%H:%M'),
                'optimal_entry': optimal_entry.strftime('%H:%M'),
                'optimal_exit': optimal_exit.strftime('%H:%M'),
            }
        except Exception:
            return self._solar_timing_approximate(d)

    def _solar_timing_approximate(self, d: date) -> Dict:
        """Approximate sunrise/sunset (India standard: ~6:00 AM - 6:00 PM)."""
        # Rough approximation for India
        sr = datetime.combine(d, time(6, 0)).astimezone(self.market_tz)
        ss = datetime.combine(d, time(18, 0)).astimezone(self.market_tz)

        optimal_entry = sr + timedelta(minutes=self.SUNRISE_BUFFER_MINS)
        optimal_exit = ss - timedelta(minutes=self.SUNSET_BUFFER_MINS)

        return {
            'sunrise': sr.strftime('%H:%M'),
            'sunset': ss.strftime('%H:%M'),
            'optimal_entry': optimal_entry.strftime('%H:%M'),
            'optimal_exit': optimal_exit.strftime('%H:%M'),
        }

    def _ephem_to_datetime(self, ephem_date) -> datetime:
        """Convert ephem date to Python datetime (UTC)."""
        ts = ephem.Date(ephem_date)
        return datetime.utcfromtimestamp(ts.timestamp()).replace(tzinfo=pytz.UTC)

    def _calculate_market_intensity(self, d: date) -> float:
        """
        Calculate expected market volatility based on lunar cycle.
        Higher during full/new moon, lower during quarters.
        """
        lunar = self.get_lunar_phase(d)
        cycle_day = lunar['cycle_day']

        # Peak volatility at new moon (day 0) and full moon (day ~14.75)
        if cycle_day < 1 or cycle_day > 28:  # New moon
            intensity = 80
        elif 14 < cycle_day < 16:  # Full moon
            intensity = 75
        elif 7 < cycle_day < 8 or 21 < cycle_day < 22:  # Quarter moons
            intensity = 40
        else:
            # Smooth curve between extremes
            intensity = 50 + 30 * math.sin(2 * math.pi * cycle_day / self.LUNAR_CYCLE)

        return max(20, min(100, intensity))

    def _generate_recommendations(self, lunar: Dict, solar: Dict, intensity: float) -> List[str]:
        """Generate trading recommendations based on astro indicators."""
        recs = []

        # Lunar phase recommendations
        if lunar['phase'] == 'new':
            recs.append('New Moon: High volatility expected. Use tight stops.')
        elif lunar['phase'] == 'full':
            recs.append('Full Moon: Market peaks. Consider profit-taking.')
        elif lunar['phase'] == 'waxing':
            recs.append('Waxing Moon: Rising energy. Good for longs.')
        elif lunar['phase'] == 'waning':
            recs.append('Waning Moon: Declining energy. Favor shorts.')

        # Intensity-based
        if intensity > 70:
            recs.append('High market intensity: Reduce position size, focus on quality setups.')
        elif intensity < 40:
            recs.append('Low market intensity: Range-bound conditions likely.')

        # Timing recommendations
        if solar.get('optimal_entry'):
            recs.append(f"Optimal entry window: {solar['optimal_entry']} (post-sunrise)")
            recs.append(f"Exit by: {solar['optimal_exit']} (pre-sunset)")

        return recs

    def get_weekly_calendar(self, start_date: date, days: int = 7) -> pd.DataFrame:
        """Get astro indicators for a week."""
        if not HAS_PANDAS:
            return self._weekly_calendar_dict(start_date, days)

        data = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            timing = self.get_trading_timing(d)
            data.append({
                'date': d,
                'lunar_phase': timing['lunar_phase']['phase'],
                'illumination': timing['lunar_phase']['illumination'],
                'market_intensity': timing['market_intensity'],
                'sunrise': timing['solar_timing'].get('sunrise', 'N/A'),
                'sunset': timing['solar_timing'].get('sunset', 'N/A'),
            })

        return pd.DataFrame(data)

    def _weekly_calendar_dict(self, start_date: date, days: int = 7) -> List[Dict]:
        """Return weekly calendar as list of dicts."""
        data = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            timing = self.get_trading_timing(d)
            data.append({
                'date': str(d),
                'lunar_phase': timing['lunar_phase']['phase'],
                'illumination': timing['lunar_phase']['illumination'],
                'market_intensity': timing['market_intensity'],
                'sunrise': timing['solar_timing'].get('sunrise', 'N/A'),
                'sunset': timing['solar_timing'].get('sunset', 'N/A'),
            })
        return data


if __name__ == '__main__':
    from datetime import date

    ai = AstroIndicators(city='Mumbai')
    today = date.today()

    print("=== Today's Astro-Trading Timing ===")
    timing = ai.get_trading_timing(today)

    print(f"\nDate: {timing['date']}")
    print(f"Location: {timing['city']}")
    print(f"\nLunar Phase: {timing['lunar_phase']['phase'].title()}")
    print(f"Illumination: {timing['lunar_phase']['illumination']}%")
    print(f"Cycle Day: {timing['lunar_phase']['cycle_day']}/{timing['lunar_phase']['cycle_length']}")

    print(f"\nSolar Timing:")
    for key, val in timing['solar_timing'].items():
        print(f"  {key.replace('_', ' ').title()}: {val}")

    print(f"\nMarket Intensity: {timing['market_intensity']}/100")

    print(f"\nRecommendations:")
    for rec in timing['recommendations']:
        print(f"  • {rec}")

    print("\n=== Weekly Calendar ===")
    if HAS_PANDAS:
        df = ai.get_weekly_calendar(today, days=7)
        print(df.to_string(index=False))
    else:
        for entry in ai._weekly_calendar_dict(today, days=7):
            print(entry)
