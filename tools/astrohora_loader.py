#!/usr/bin/env python3
"""
astrohora_loader.py
Load and parse AstroHora data for trading integration.

AstroHora generates birth charts, prashna charts (event-based), and can output:
- House positions
- Planetary positions (longitude, latitude)
- Aspects
- Conjunctions
- Dasha periods (Vimshottari mahadasha)

Usage:
  from astrohora_loader import AstroHoraData
  aha = AstroHoraData()
  aha.load_from_csv('chart_data.csv')
  aha.get_vimshottari_dasha_summary()
"""

from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import csv
import json

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class AstroHoraData:
    """Load and analyze AstroHora chart data."""

    # Zodiac signs
    ZODIAC = [
        'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
        'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
    ]

    # Planets in astrological order
    PLANETS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
    NODES = ['Rahu', 'Ketu']  # North & South lunar nodes

    # Vimshottari Mahadasha periods (in years)
    MAHADASHA_PERIODS = {
        'Ketu': 7,
        'Venus': 20,
        'Sun': 6,
        'Moon': 10,
        'Mars': 7,
        'Rahu': 18,
        'Jupiter': 16,
        'Saturn': 19,
        'Mercury': 17,
    }

    # Dasha sequence (Ketu starts regardless of birth position)
    DASHA_SEQUENCE = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']

    def __init__(self):
        """Initialize AstroHora data container."""
        self.chart_data = {}  # Planetary positions
        self.houses = {}      # House cusps
        self.birth_date = None
        self.birth_time = None
        self.location = None
        self.chart_type = None  # 'natal' or 'prashna'

    def load_from_excel(self, filepath: str) -> bool:
        """
        Load data from AstroHora Excel output.

        Returns True if successful, False otherwise.
        """
        if not HAS_PANDAS:
            print("Error: pandas required for Excel loading. Install: pip install openpyxl")
            return False

        try:
            df = pd.read_excel(filepath, sheet_name=0)
            self._parse_astro_dataframe(df)
            return True
        except Exception as e:
            print(f"Error loading Excel: {e}")
            return False

    def load_from_csv(self, filepath: str) -> bool:
        """Load data from CSV export of AstroHora chart."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._parse_row(row)
            return True
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return False

    def load_from_dict(self, data: Dict) -> None:
        """Load data from dictionary (manual or API)."""
        if 'chart_data' in data:
            self.chart_data = data['chart_data']
        if 'houses' in data:
            self.houses = data['houses']
        if 'birth_date' in data:
            self.birth_date = data['birth_date']
        if 'birth_time' in data:
            self.birth_time = data['birth_time']
        if 'location' in data:
            self.location = data['location']
        if 'chart_type' in data:
            self.chart_type = data['chart_type']

    def _parse_row(self, row: Dict) -> None:
        """Parse a single row from CSV."""
        # Expected format: Planet | Sign | Degree | Minutes | Seconds | House
        planet = row.get('Planet', '').strip()
        if not planet:
            return

        try:
            sign = row.get('Sign', '').strip()
            degree = float(row.get('Degree', 0))
            minutes = float(row.get('Minutes', 0))
            seconds = float(row.get('Seconds', 0))
            house = row.get('House', 'N/A')

            # Convert to decimal degrees
            longitude = degree + minutes / 60 + seconds / 3600

            self.chart_data[planet] = {
                'sign': sign,
                'longitude': longitude,
                'house': house,
                'degree': degree,
                'minutes': int(minutes),
                'seconds': int(seconds),
            }
        except ValueError:
            pass

    def _parse_astro_dataframe(self, df: pd.DataFrame) -> None:
        """Parse pandas DataFrame from Excel."""
        for _, row in df.iterrows():
            planet = row.get('Planet', '')
            if pd.notna(planet):
                self.chart_data[str(planet).strip()] = {
                    'sign': str(row.get('Sign', 'N/A')),
                    'longitude': float(row.get('Longitude', 0)),
                    'house': str(row.get('House', 'N/A')),
                }

    def get_planetary_positions(self) -> Dict:
        """Return all planetary positions."""
        return self.chart_data

    def get_planet_in_sign(self, planet: str) -> Optional[Dict]:
        """Get a specific planet's sign and position."""
        return self.chart_data.get(planet)

    def get_planets_by_house(self, house_num: int) -> List[Tuple[str, Dict]]:
        """Get all planets in a specific house."""
        result = []
        for planet, data in self.chart_data.items():
            if str(data.get('house')) == str(house_num):
                result.append((planet, data))
        return result

    def get_strong_planets(self) -> List[Tuple[str, str]]:
        """
        Get planets in their own sign or exaltation.
        Returns list of (planet, status) tuples.
        """
        strong = []

        # Exaltation signs (simplified)
        exaltation_map = {
            'Sun': 'Aries',
            'Moon': 'Taurus',
            'Mars': 'Capricorn',
            'Mercury': 'Virgo',
            'Jupiter': 'Cancer',
            'Venus': 'Pisces',
            'Saturn': 'Libra',
        }

        # Own signs (simplified - each planet rules a sign)
        own_sign_map = {
            'Sun': 'Leo',
            'Moon': 'Cancer',
            'Mars': 'Aries',
            'Mercury': 'Gemini',
            'Jupiter': 'Sagittarius',
            'Venus': 'Taurus',
            'Saturn': 'Capricorn',
        }

        for planet, data in self.chart_data.items():
            sign = data.get('sign', '')
            if sign == exaltation_map.get(planet):
                strong.append((planet, 'Exalted'))
            elif sign == own_sign_map.get(planet):
                strong.append((planet, 'Own Sign'))

        return strong

    def get_vimshottari_dasha(self, birth_date: date, current_date: Optional[date] = None) -> Dict:
        """
        Calculate Vimshottari Mahadasha (major period).

        The sequence cycles through 9 planets, with periods based on Moon's position at birth.
        In simplified form, we start counting from a reference point.
        """
        if current_date is None:
            current_date = date.today()

        days_elapsed = (current_date - birth_date).days
        years_elapsed = days_elapsed / 365.25

        # In reality, the starting dasha depends on birth Moon position
        # This is a simplified approximation
        total_dasha_years = sum(self.MAHADASHA_PERIODS.values())
        position_in_cycle = years_elapsed % total_dasha_years

        current_dasha = None
        dasha_start_year = 0

        for dasha in self.DASHA_SEQUENCE:
            period = self.MAHADASHA_PERIODS[dasha]
            if position_in_cycle < dasha_start_year + period:
                current_dasha = dasha
                break
            dasha_start_year += period

        if current_dasha is None:
            current_dasha = self.DASHA_SEQUENCE[0]

        dasha_period_years = self.MAHADASHA_PERIODS[current_dasha]
        years_in_dasha = position_in_cycle - dasha_start_year
        years_remaining = dasha_period_years - years_in_dasha

        return {
            'current_dasha': current_dasha,
            'period_years': dasha_period_years,
            'years_elapsed': round(years_in_dasha, 1),
            'years_remaining': round(years_remaining, 1),
            'dasha_sequence': self.DASHA_SEQUENCE,
        }

    def get_aspectarian(self) -> List[Dict]:
        """
        Get major aspects between planets.
        Major aspects: conjunction (0°), opposition (180°), trine (120°), square (90°)
        """
        aspects = []
        major_aspects = [
            (0, 8, 'Conjunction'),
            (60, 8, 'Sextile'),
            (90, 8, 'Square'),
            (120, 8, 'Trine'),
            (180, 8, 'Opposition'),
        ]

        planets = [p for p in self.PLANETS if p in self.chart_data]

        for i, p1 in enumerate(planets):
            for p2 in planets[i + 1:]:
                lon1 = self.chart_data[p1]['longitude']
                lon2 = self.chart_data[p2]['longitude']

                diff = abs(lon1 - lon2)
                if diff > 180:
                    diff = 360 - diff

                for angle, orb, aspect_name in major_aspects:
                    if abs(diff - angle) <= orb:
                        aspects.append({
                            'planet1': p1,
                            'planet2': p2,
                            'aspect': aspect_name,
                            'angle': round(diff, 2),
                            'orb': round(abs(diff - angle), 2),
                        })
                        break

        return aspects

    def get_summary(self) -> Dict:
        """Get summary of chart analysis."""
        strong_planets = self.get_strong_planets()
        aspects = self.get_aspectarian()

        return {
            'chart_type': self.chart_type or 'Unknown',
            'birth_date': str(self.birth_date) if self.birth_date else 'N/A',
            'location': self.location or 'N/A',
            'planets_count': len(self.chart_data),
            'strong_planets': strong_planets,
            'major_aspects': aspects,
        }

    def export_to_json(self, filepath: str) -> bool:
        """Export chart data to JSON."""
        try:
            data = {
                'chart_type': self.chart_type,
                'birth_date': str(self.birth_date) if self.birth_date else None,
                'birth_time': str(self.birth_time) if self.birth_time else None,
                'location': self.location,
                'chart_data': self.chart_data,
                'houses': self.houses,
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False


if __name__ == '__main__':
    # Example usage
    from datetime import date, time

    aha = AstroHoraData()

    # Example: Manual entry of a birth chart
    example_chart = {
        'chart_type': 'natal',
        'birth_date': date(1990, 6, 15),
        'birth_time': time(14, 30),
        'location': 'Mumbai, India',
        'chart_data': {
            'Sun': {'sign': 'Gemini', 'longitude': 84.5, 'house': '11'},
            'Moon': {'sign': 'Libra', 'longitude': 207.2, 'house': '3'},
            'Mars': {'sign': 'Leo', 'longitude': 123.8, 'house': '1'},
            'Mercury': {'sign': 'Gemini', 'longitude': 91.3, 'house': '11'},
            'Jupiter': {'sign': 'Cancer', 'longitude': 99.5, 'house': '12'},
            'Venus': {'sign': 'Cancer', 'longitude': 108.7, 'house': '12'},
            'Saturn': {'sign': 'Capricorn', 'longitude': 286.4, 'house': '6'},
        }
    }

    aha.load_from_dict(example_chart)

    print("=== Chart Summary ===")
    summary = aha.get_summary()
    for key, val in summary.items():
        print(f"{key}: {val}")

    print("\n=== Strong Planets ===")
    for planet, status in aha.get_strong_planets():
        print(f"  {planet}: {status}")

    print("\n=== Major Aspects ===")
    for aspect in aha.get_aspectarian():
        print(f"  {aspect['planet1']} {aspect['aspect']} {aspect['planet2']} ({aspect['angle']}°)")

    print("\n=== Vimshottari Dasha ===")
    dasha = aha.get_vimshottari_dasha(date(1990, 6, 15))
    print(f"  Current: {dasha['current_dasha']} (Year {dasha['years_elapsed']:.1f}/{dasha['period_years']})")
    print(f"  Years Remaining: {dasha['years_remaining']:.1f}")
