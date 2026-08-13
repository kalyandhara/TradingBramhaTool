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
        Lunar phase for a date, from the reversal-calendar DB.

        Returns {phase, illumination, cycle_day, cycle_length, source}. Outside
        the DB's coverage `phase` is 'unknown' and the numbers are None — see
        `_lunar_phase_from_calendar` for why that is the only honest answer.

        AW-0 (2026-08-02). This used to fall back to `_lunar_phase_approximate`
        whenever PyEphem was missing — which is always, on this machine — and
        that fallback was wrong three ways at once:

          * its epoch, `date(2024, 1, 29)`, is not a new moon (2024-02-09 is),
            leaving a constant ~10.8-day offset: real new moons landed on
            cycle_day 11.10 and 10.57 instead of ~0;
          * its illumination, `100·sin(2πc/L)·0.5 + 50`, is a quarter-cycle out
            of phase — 50% at new, 100% at FIRST QUARTER, 50% at full — so the
            new moon and the full moon both read half-lit;
          * a fixed 29.53-day mean month drifts against real lunations anyway.

        The visible symptom: the 2026-07-29 full moon rendered on the Astro
        Timing page as "waning, 16.7% illuminated", and 2026-08-08 as "new" at
        99.3% — a self-contradiction on the face of it. The correct events were
        already sitting in `reversal_calendar.db`, PyEphem-derived, which is why
        the approximation is deleted rather than repaired: two lunar sources in
        one dashboard is how they end up disagreeing.
        """
        if not HAS_EPHEM:
            return self._lunar_phase_from_calendar(d)

        try:
            observer = Observer()
            observer.date = datetime.combine(d, time(12, 0))
            observer.lat, observer.lon = str(self.lat), str(self.lon)

            moon = Moon(observer)
            illumination = moon.phase          # ephem: percent illuminated

            # cycle_day is measured from the ACTUAL preceding new moon. It used
            # to be `(illumination / 100) * LUNAR_CYCLE`, which treats a cosine
            # as a straight line and is symmetric about full — day 7 and day 22
            # are both ~50% lit and would have collapsed onto the same answer.
            from ephem import previous_new_moon, next_new_moon
            prev_new = previous_new_moon(observer.date)
            nxt_new = next_new_moon(observer.date)
            cycle_length = float(nxt_new) - float(prev_new)
            cycle_day = float(observer.date) - float(prev_new)

            return {
                'phase': self._phase_label(cycle_day, cycle_length),
                'illumination': round(illumination, 2),
                'cycle_day': round(cycle_day, 1),
                'cycle_length': round(cycle_length, 2),
                'source': 'ephem',
            }
        except Exception as e:
            print(f"Ephem calculation error: {e}")
            return self._lunar_phase_from_calendar(d)

    @staticmethod
    def _phase_label(cycle_day: float, cycle_length: float) -> str:
        """Quadrant label, CENTRED on the event each name refers to.

        'new' brackets f=0 and 'full' brackets f=0.5, rather than starting
        there. The distinction is not cosmetic: with start-aligned bands a full
        moon that lands at f=0.483 — which happens whenever the lunation is 29
        whole days and the full moon falls on day 14 — gets labelled 'waxing'
        while its own illumination reads 99.7%. Checked against all 44 lunar
        events in the reversal calendar; start-aligned bands mislabelled 11.
        """
        f = (cycle_day / cycle_length) % 1.0
        if f < 0.125 or f >= 0.875:
            return 'new'
        if f < 0.375:
            return 'waxing'
        if f < 0.625:
            return 'full'
        return 'waning'

    def _lunar_phase_from_calendar(self, d: date) -> Dict:
        """Lunar phase interpolated between the DB's real new-moon timestamps.

        `reversal_calendar.db` stores PyEphem-derived new/full moons with exact
        instants, so the cycle is measured against the lunation the date is
        actually in rather than against a mean 29.53-day month drifting from a
        mis-chosen epoch.

        Outside the DB's coverage this returns `phase: 'unknown'` with None
        figures. That is deliberate: the previous behaviour extrapolated a mean
        cycle indefinitely and produced confident numbers for any date you
        asked about, which is exactly how a full moon came to render as
        "waning, 16.7%". A date we cannot place must read as unplaced.
        """
        try:
            import sys as _sys
            from pathlib import Path as _Path
            _sys.path.insert(0, str(_Path(__file__).resolve().parent))
            import reversal_calendar as _rc

            # Widen enough to bracket d with a new moon on each side (a lunation
            # is ~29.5 days; 45 either way is comfortable even at the edges).
            evs = _rc.events_in_range(d - timedelta(days=45), d + timedelta(days=45))
            news = sorted(datetime.fromisoformat(e['start_ts']).date()
                          for e in evs if e['event_type'] == 'new_moon')
            prev_new = max((n for n in news if n <= d), default=None)
            next_new = min((n for n in news if n > d), default=None)
            if prev_new is None or next_new is None:
                return self._lunar_unknown(d)

            cycle_length = (next_new - prev_new).days
            cycle_day = (d - prev_new).days
            if cycle_length <= 0:
                return self._lunar_unknown(d)

            # 0% at new, 100% at full — the standard relation. The old formula
            # used sin() instead of (1 - cos()), which peaks a quarter-cycle
            # early and reports both new and full as half-lit.
            frac = cycle_day / cycle_length
            illumination = round(50.0 * (1 - math.cos(2 * math.pi * frac)), 1)

            return {
                'phase': self._phase_label(cycle_day, cycle_length),
                'illumination': illumination,
                'cycle_day': round(float(cycle_day), 1),
                'cycle_length': round(float(cycle_length), 2),
                'source': 'reversal_calendar',
            }
        except Exception as e:
            print(f"Lunar calendar lookup failed: {e}")
            return self._lunar_unknown(d)

    @staticmethod
    def _lunar_unknown(d: date) -> Dict:
        return {
            'phase': 'unknown',
            'illumination': None,
            'cycle_day': None,
            'cycle_length': None,
            'source': 'unavailable',
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
            'market_intensity': None if intensity is None else round(intensity, 1),
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
        """Approximate sunrise/sunset (India standard: ~6:00 AM - 6:00 PM IST).

        `localize`, not `astimezone`. `datetime.combine` returns a NAIVE
        datetime, and calling `.astimezone()` on one makes Python assume the
        HOST machine's zone and convert from it — so on a US-Eastern host this
        rendered sunrise at 15:30 and sunset at 03:30 IST on the Astro Timing
        page. The 6am/6pm figures are already meant to be IST; they need
        attaching, not converting.
        """
        sr = self.market_tz.localize(datetime.combine(d, time(6, 0)))
        ss = self.market_tz.localize(datetime.combine(d, time(18, 0)))

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

    def _calculate_market_intensity(self, d: date):
        """
        Expected volatility from the lunar cycle: higher near new/full, lower
        near the quarters. Returns None when the phase could not be placed —
        an intensity number for a date we cannot date would be invented.
        """
        lunar = self.get_lunar_phase(d)
        cycle_day = lunar['cycle_day']
        cycle_length = lunar['cycle_length'] or self.LUNAR_CYCLE
        if cycle_day is None:
            return None

        if cycle_day < 1 or cycle_day > 28:            # new moon
            intensity = 80
        elif 14 < cycle_day < 16:                      # full moon
            intensity = 75
        elif 7 < cycle_day < 8 or 21 < cycle_day < 22:  # quarters
            intensity = 40
        else:
            # abs(cos) peaks at BOTH new (0) and full (~half), and troughs at the
            # quarters — which is what the docstring and the branches above both
            # say. The previous `50 + 30·sin(…)` did the exact opposite: it
            # peaked at first quarter and sat at 50 on new and full, so the
            # interpolation contradicted the endpoints it was interpolating
            # between. Same sin-for-cos slip as the illumination bug above.
            intensity = 50 + 30 * abs(math.cos(2 * math.pi * cycle_day / cycle_length))

        return max(20, min(100, intensity))

    def _generate_recommendations(self, lunar: Dict, solar: Dict, intensity) -> List[str]:
        """Generate trading recommendations based on astro indicators.

        A date the calendar cannot place gets the solar window and an explicit
        statement that the lunar read is missing — not lunar advice derived from
        a phase nobody computed.
        """
        recs = []

        if lunar.get('phase') == 'unknown':
            recs.append('Lunar phase unavailable for this date — the reversal '
                        'calendar does not cover it. Solar timing below still '
                        'applies; treat the lunar read as absent, not neutral.')

        # Lunar phase recommendations
        if lunar['phase'] == 'new':
            recs.append('New Moon: High volatility expected. Use tight stops.')
        elif lunar['phase'] == 'full':
            recs.append('Full Moon: Market peaks. Consider profit-taking.')
        elif lunar['phase'] == 'waxing':
            recs.append('Waxing Moon: Rising energy. Good for longs.')
        elif lunar['phase'] == 'waning':
            recs.append('Waning Moon: Declining energy. Favor shorts.')

        # Intensity-based. None means it was not computed, which is not the same
        # as "not high" — say nothing rather than imply a calm reading.
        if intensity is not None:
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

    # ── Nakshatra sector map ───────────────────────────────────────────────────
    # 27 lunar mansions, each 13°20' of the sidereal zodiac.
    # Lahiri ayanamsa for 2026: ~23.85°.  Tuple: (name, ruling_planet, [NSE sectors], commodity_theme)
    NAKSHATRA_DATA: List[Tuple] = [
        ("Ashwini",          "Ketu",    ["Pharma", "Auto", "Metal"],          "Medical, transport, mining, railways"),
        ("Bharani",          "Venus",   ["FMCG", "Agri"],                     "Wheat, edible oils, food, medicines, tea"),
        ("Krittika",         "Sun",     ["Metal", "Energy", "Defence"],       "Gold, diamonds, steel, international trade"),
        ("Rohini",           "Moon",    ["Auto", "Banking", "Energy", "FMCG"],"Silver, crude oil, cotton, auto, shipping"),
        ("Mrigashira",       "Mars",    ["IT", "Pharma", "Media"],            "Tech, cinema, jewelry, food grains, pulses"),
        ("Ardra",            "Rahu",    ["IT", "Pharma", "Energy"],           "Edible oils, air transport, communication, IT"),
        ("Punarvasu",        "Jupiter", ["Banking", "Realty"],                "Gold, silver, insurance, banking, real estate"),
        ("Pushya",           "Saturn",  ["FMCG", "Energy", "Agri"],          "Dairy, agriculture, petroleum, govt securities"),
        ("Ashlesha",         "Mercury", ["Pharma", "Energy"],                 "Pharma, chemicals, petroleum, international trade"),
        ("Magha",            "Ketu",    ["Banking", "Defence"],               "Stock markets, administration, politics, judiciary"),
        ("Purva Phalguni",   "Venus",   ["Media", "FMCG", "Realty"],         "Entertainment, beauty, gems, media, hospitality"),
        ("Uttara Phalguni",  "Sun",     ["Banking", "Media"],                 "Banking, media, public service, social sectors"),
        ("Hasta",            "Moon",    ["Banking", "Metal"],                 "Silver, textiles, hospitals, marketing, brokerage"),
        ("Chitra",           "Mars",    ["Auto", "Realty", "Metal"],          "Luxury goods, automobiles, petroleum, real estate"),
        ("Swati",            "Rahu",    ["Banking", "IT", "FMCG"],           "Stock exchanges, cosmetics, silk, financial mgmt"),
        ("Vishakha",         "Jupiter", ["Banking", "FMCG", "Agri"],         "Gold, insurance, banking, agriculture, books"),
        ("Anuradha",         "Saturn",  ["IT", "Pharma", "Defence"],         "Science, foreign trade, exploration, music"),
        ("Jyeshtha",         "Mercury", ["Defence", "Media"],                 "Military, government, administration, journalism"),
        ("Mula",             "Ketu",    ["Energy", "Pharma", "Metal"],        "Petroleum, mining, atomic energy, medicine"),
        ("Purva Ashadha",    "Venus",   ["Energy", "Media", "FMCG"],         "Maritime, water industries, aviation, entertainment"),
        ("Uttara Ashadha",   "Sun",     ["Defence", "Infra", "Realty"],      "Government, law, military, construction, athletics"),
        ("Shravana",         "Moon",    ["Energy", "Media", "FMCG"],         "Milk products, marine, mining, coal, broadcasting"),
        ("Dhanishtha",       "Mars",    ["Metal", "Energy", "Realty"],        "Metals, iron, steel, atomic energy, stock markets"),
        ("Shatabhisha",      "Rahu",    ["Pharma", "IT", "Energy"],           "Healthcare, electrical, pharma, aviation, film"),
        ("Purva Bhadrapada", "Jupiter", ["Pharma", "Metal", "Energy"],        "Medicine, metallurgy, leather, pharma, environment"),
        ("Uttara Bhadrapada","Saturn",  ["FMCG", "Agri"],                    "Jaggery, sugar, sesame, oils, agriculture, research"),
        ("Revati",           "Mercury", ["IT", "Realty", "Media"],            "Gemstones, pearls, shipping, maritime, hospitality"),
    ]

    # Lahiri ayanamsa — updated periodically; ~23.85° for 2026
    _AYANAMSA = 23.85

    def get_nakshatra(self, d: date) -> Dict:
        """
        Return the Moon's nakshatra for date d (noon IST).

        Uses PyEphem to get the geocentric ecliptic longitude, then applies the
        Lahiri ayanamsa to convert tropical → sidereal before dividing into the
        27-nakshatra grid (each 13°20').  Returns a dict with nakshatra metadata
        and the sectors to watch; falls back to a note when ephem is absent.
        """
        if not HAS_EPHEM:
            return {"error": "ephem not installed — run: pip install ephem"}

        import ephem as _ephem

        observer = _ephem.Observer()
        observer.date = datetime.combine(d, time(5, 30))  # noon IST = 06:30 UTC
        observer.lat = str(self.lat)
        observer.lon = str(self.lon)
        observer.elevation = 0
        observer.pressure = 0  # no refraction

        moon = _ephem.Moon(observer)
        moon.compute(observer)

        # Tropical ecliptic longitude (radians → degrees)
        ec = _ephem.Ecliptic(moon, epoch=observer.date)
        tropical_lon = math.degrees(ec.lon) % 360

        # Sidereal longitude (Lahiri)
        sidereal_lon = (tropical_lon - self._AYANAMSA) % 360

        # Nakshatra index 0-26 and degree within the nakshatra (0-13.33)
        each = 360 / 27
        idx = int(sidereal_lon / each)
        deg_in = sidereal_lon - idx * each
        pct = deg_in / each  # 0.0 → 1.0 progress through nakshatra

        name, planet, sectors, theme = self.NAKSHATRA_DATA[idx]
        return {
            "nakshatra":    name,
            "index":        idx + 1,          # 1-27 for display
            "planet":       planet,
            "sectors":      sectors,
            "theme":        theme,
            "sidereal_lon": round(sidereal_lon, 2),
            "deg_in":       round(deg_in, 2),
            "pct":          round(pct * 100, 1),   # % through nakshatra
        }

    # India Independence Chart sensitive degrees (degree within sign, 0–29°)
    # Source: Aug 15, 1947, 12:00 AM, New Delhi — D1 (Rashi) and D9 (Navamsa)
    INDIA_CHART_DEGREES: Dict[str, float] = {
        "Lagna D1":  8.0,
        "Lagna D9":  12.0,
        "Sun":       27.18,
        "Moon":      3.08,
        "Mars":      7.0,
        "Mercury":   13.0,
        "Jupiter":   25.0,
        "Venus":     22.0,
        "Saturn":    20.0,
        "Rahu/Ketu": 5.0,
    }

    # Trading bias per transiting planet (financial astrology convention:
    # malefics = bullish, benefics = bearish)
    _PLANET_BIAS: Dict[str, str] = {
        "Sun":     "bullish",
        "Moon":    "bearish",
        "Mars":    "bullish",
        "Mercury": "bearish",
        "Jupiter": "bearish",
        "Venus":   "bearish",
        "Saturn":  "bullish",
        "Rahu":    "bullish",
        "Ketu":    "ambiguous",
    }

    # NSE karaka sectors per planet
    _PLANET_KARAKA: Dict[str, str] = {
        "Sun":     "Govt / PSU / Defence / Energy",
        "Moon":    "Petroleum / Retail / FMCG / Agri",
        "Mars":    "Auto / Defence / Steel / Realty",
        "Mercury": "IT / Telecom / Media / Banking",
        "Jupiter": "Banking / Finance / Gold / FMCG",
        "Venus":   "Textiles / Luxury / Vehicles / Finance",
        "Saturn":  "Oil & Gas / Infra / Mining / IT Services",
        "Rahu":    "IT / Pharma / Aviation / Derivatives",
        "Ketu":    "Pharma / Defence / Niche",
    }

    def get_india_chart_alerts(self, d: date, orb: float = 2.0) -> List[Dict]:
        """
        Return degree-matching alerts for date d (9:15 AM IST — NSE open).

        For each transiting planet, extracts the degree within its current sign
        (lon % 30) and checks against every sensitive degree in India's Independence
        Chart (D1 + D9). An alert fires when |transiting_deg - india_deg| <= orb.

        Returns a list of alert dicts sorted by orb (tightest first):
          planet, transiting_deg, india_point, india_deg, orb_actual,
          bias, karaka, sign, sidereal_lon
        """
        if not HAS_EPHEM:
            return [{"error": "ephem not installed"}]

        import ephem as _ephem

        # 9:15 AM IST = 03:45 UTC
        observer = _ephem.Observer()
        observer.date = datetime.combine(d, time(3, 45))
        observer.lat = str(self.lat)
        observer.lon = str(self.lon)
        observer.elevation = 0
        observer.pressure = 0

        def _planet_data(body_class, name):
            body = body_class()
            body.compute(observer)
            ec = _ephem.Ecliptic(body, epoch=observer.date)
            sid_lon = (math.degrees(ec.lon) - self._AYANAMSA) % 360
            sign_idx = int(sid_lon / 30)
            deg_in_sign = sid_lon % 30
            return {
                "planet":       name,
                "sidereal_lon": round(sid_lon, 2),
                "sign":         self._SIGNS[sign_idx],
                "deg_in_sign":  round(deg_in_sign, 2),
                "bias":         self._PLANET_BIAS.get(name, "unknown"),
                "karaka":       self._PLANET_KARAKA.get(name, ""),
            }

        planets = [
            _planet_data(_ephem.Sun,     "Sun"),
            _planet_data(_ephem.Moon,    "Moon"),
            _planet_data(_ephem.Mars,    "Mars"),
            _planet_data(_ephem.Mercury, "Mercury"),
            _planet_data(_ephem.Jupiter, "Jupiter"),
            _planet_data(_ephem.Venus,   "Venus"),
            _planet_data(_ephem.Saturn,  "Saturn"),
        ]

        # Rahu (mean lunar node) — same J2000 formula used in get_jupiter_position
        _j2000 = datetime(2000, 1, 1, 12, 0, 0)
        _days = (datetime.combine(d, time(3, 45)) - _j2000).total_seconds() / 86400
        rahu_tropical = (125.04455501 - 0.05295392 * _days) % 360
        rahu_sid = (rahu_tropical - self._AYANAMSA) % 360
        ketu_sid = (rahu_sid + 180) % 360

        for name, sid_lon in [("Rahu", rahu_sid), ("Ketu", ketu_sid)]:
            sign_idx = int(sid_lon / 30)
            planets.append({
                "planet":       name,
                "sidereal_lon": round(sid_lon, 2),
                "sign":         self._SIGNS[sign_idx],
                "deg_in_sign":  round(sid_lon % 30, 2),
                "bias":         self._PLANET_BIAS.get(name, "ambiguous"),
                "karaka":       self._PLANET_KARAKA.get(name, ""),
            })

        alerts = []
        for p in planets:
            for india_point, india_deg in self.INDIA_CHART_DEGREES.items():
                diff = abs(p["deg_in_sign"] - india_deg)
                # wrap at 30° boundary (e.g. 29° vs 1° of next sign)
                if diff > 15:
                    diff = 30 - diff
                if diff <= orb:
                    alerts.append({
                        **p,
                        "india_point":  india_point,
                        "india_deg":    india_deg,
                        "orb_actual":   round(diff, 2),
                        "exact":        diff <= 0.5,
                    })

        return sorted(alerts, key=lambda x: x["orb_actual"])

    # Zodiac sign names (sidereal / Vedic)
    _SIGNS = [
        "Aries (Mesha)", "Taurus (Vrishabha)", "Gemini (Mithuna)",
        "Cancer (Karka)", "Leo (Simha)", "Virgo (Kanya)",
        "Libra (Tula)", "Scorpio (Vrishchika)", "Sagittarius (Dhanu)",
        "Capricorn (Makara)", "Aquarius (Kumbha)", "Pisces (Meena)",
    ]

    # Nakshatras ruled by Ketu (index 0-based: Ashwini=0, Magha=9, Mula=18)
    _KETU_NAKSHATRA_IDX = {0, 9, 18}

    def get_jupiter_position(self, d: date) -> Dict:
        """
        Return Jupiter's sidereal position for date d (noon IST) and evaluate
        the Jupiter Market Crash Signal (three-factor model).

        Factor 1 — Ketu nakshatra: Jupiter in Ashwini, Magha, or Mula.
        Factor 2 — Shashtashtak Yoga: Saturn, Sun, or Mars is 5 or 7 signs
                   away from Jupiter (6th/8th house axis in Vedic astrology).
        Factor 3 — Rahu-Ketu nodal influence: Rahu or Ketu is within ±30°
                   of Jupiter's ecliptic longitude (1-sign orb).

        All three active simultaneously = historical crash signal (1992/2000/2008/2020).
        """
        if not HAS_EPHEM:
            return {"error": "ephem not installed — run: pip install ephem"}

        import ephem as _ephem

        observer = _ephem.Observer()
        observer.date = datetime.combine(d, time(5, 30))  # noon IST = 06:30 UTC
        observer.lat = str(self.lat)
        observer.lon = str(self.lon)
        observer.elevation = 0
        observer.pressure = 0

        def _sidereal(body_class):
            body = body_class()
            body.compute(observer)
            ec = _ephem.Ecliptic(body, epoch=observer.date)
            return (math.degrees(ec.lon) - self._AYANAMSA) % 360

        jup_lon = _sidereal(_ephem.Jupiter)
        sat_lon = _sidereal(_ephem.Saturn)
        sun_lon = _sidereal(_ephem.Sun)
        mar_lon = _sidereal(_ephem.Mars)
        # Rahu (mean north node); Ketu is always 180° opposite
        # Mean lunar ascending node (Rahu) — J2000.0 epoch formula
        # J2000.0 = 2000-Jan-1.5 TT; node was 125.04455501° tropical, retrograde
        _j2000 = datetime(2000, 1, 1, 12, 0, 0)
        _days_j2000 = (datetime.combine(d, time(5, 30)) - _j2000).total_seconds() / 86400
        rahu_tropical = (125.04455501 - 0.05295392 * _days_j2000) % 360
        rahu_lon = (rahu_tropical - self._AYANAMSA) % 360
        ketu_lon = (rahu_lon + 180) % 360

        each_sign = 30.0
        each_nak  = 360 / 27

        jup_sign_idx = int(jup_lon / each_sign)
        jup_nak_idx  = int(jup_lon / each_nak)

        name, nk_planet, sectors, theme = self.NAKSHATRA_DATA[jup_nak_idx]

        # Factor 1: Ketu nakshatra
        f1_ketu_nak = jup_nak_idx in self._KETU_NAKSHATRA_IDX

        # Factor 2: Shashtashtak — malefic is 5 or 7 signs from Jupiter
        def _sign_sep(a_lon, b_lon):
            """Signs from a to b (forward)."""
            return int(((b_lon - a_lon) % 360) / 30)

        f2_malefics = []
        for planet_name, mal_lon in [("Saturn", sat_lon), ("Sun", sun_lon), ("Mars", mar_lon)]:
            sep = _sign_sep(jup_lon, mal_lon)
            if sep in (5, 7):
                f2_malefics.append(planet_name)

        f2_shashtashtak = len(f2_malefics) > 0

        # Factor 3: Rahu-Ketu within 30° of Jupiter
        def _arc(a, b):
            return min(abs(a - b) % 360, 360 - abs(a - b) % 360)

        rahu_arc = _arc(jup_lon, rahu_lon)
        ketu_arc = _arc(jup_lon, ketu_lon)
        f3_nodal = rahu_arc <= 30 or ketu_arc <= 30

        factors_active = sum([f1_ketu_nak, f2_shashtashtak, f3_nodal])

        if factors_active == 3:
            signal = "CRASH SIGNAL"
            signal_color = "red"
        elif factors_active == 2:
            signal = "ELEVATED RISK"
            signal_color = "orange"
        elif factors_active == 1:
            signal = "WATCH"
            signal_color = "yellow"
        else:
            signal = "CLEAR"
            signal_color = "green"

        return {
            "date":             d,
            "nakshatra":        name,
            "nakshatra_index":  jup_nak_idx + 1,
            "nakshatra_planet": nk_planet,
            "sign":             self._SIGNS[jup_sign_idx],
            "sign_index":       jup_sign_idx + 1,
            "sidereal_lon":     round(jup_lon, 2),
            "is_ketu_nakshatra": f1_ketu_nak,
            "shashtashtak_with": f2_malefics,        # list of planet names
            "nodal_influence":  f3_nodal,
            "rahu_arc":         round(rahu_arc, 1),
            "ketu_arc":         round(ketu_arc, 1),
            "factors_active":   factors_active,
            "signal":           signal,
            "signal_color":     signal_color,
        }

    def get_nakshatra_forecast(self, start_date: date, days: int = 7) -> "pd.DataFrame":
        """Return a DataFrame of nakshatra + sector forecasts for `days` ahead."""
        rows = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            nk = self.get_nakshatra(d)
            if "error" in nk:
                break
            rows.append({
                "Date":         d.strftime("%a %d %b"),
                "Nakshatra":    nk["nakshatra"],
                "Ruling Planet":nk["planet"],
                "Watch Sectors":  " / ".join(nk["sectors"]),
                "Commodity Theme": nk["theme"],
                "Progress %":   nk["pct"],
            })
        if HAS_PANDAS:
            import pandas as pd
            return pd.DataFrame(rows)
        return rows


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
