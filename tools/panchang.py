"""panchang.py — offline Vedic almanac for a trading date (FA-1).

Everything a "morning brief" needs from the panchang, computed locally from
`ephem` plus arithmetic: **no API, no login, no rate limit, no vendor**. That is
the whole point of this module — see ``analyses/Financial-Astrology-Sector-Week-Roadmap``
(FA-1), which established that panchang vendors (ProKerala, VedicRishi,
DrikPanchang) return nothing that cannot be computed here, so taking a
dependency on one would add a failure mode for no capability.

Public API (all pure; a date and a place in, a dict out):
    sun_times(d, place)            -> {"sunrise", "sunset", "day_length"}
    day_parts(d, place)            -> Rahu Kaal / Yamaganda / Gulika windows
    hora_sequence(d, place)        -> 24 planetary-hour blocks, day then night
    hora_at(d, place, when)        -> the block containing `when` (+ the next)
    moon_nakshatra(when)           -> nakshatra, pada, lord, sub-lord, transits
    tithi(when)                    -> tithi number/name/paksha + completion %
    retrogrades(when)              -> which planets are retrograde
    panchang(d, place, now)        -> everything above in one dict

Deliberately NOT here: **the moon phase.** `astro_trading.get_lunar_phase()`
already owns that, reading the 278-event `reversal_calendar.db` store, and the
roadmap's FA-0 is explicit that two surfaces disagreeing about the moon
invalidates anything built on either. `panchang()` delegates to it rather than
computing a second answer. (FA-0 itself was already fixed on 2026-08-02 — the
broken `_lunar_phase_approximate` fallback is gone.)

Verification status (2026-08-09):
  * **Rahu Kaal, Tue 2026-07-28, Mumbai -> 16:00-17:38 IST.** A published card
    prints 04:00 PM - 05:38 PM. Exact to the minute.
  * **Moon nakshatra, same date -> Purva Ashadha pada 3 at 05:30 IST, rolling to
    pada 4 at 06:31 IST.** Matches the same card's transition.
  See `tests/` usage in the accompanying verification script.

Accuracy caveats, stated rather than buried:
  * **Ayanamsa is a Lahiri linear approximation** (`_lahiri_ayanamsa`), good to
    roughly an arc-minute across the years this repo cares about. Nakshatra
    boundaries are 13 deg 20' wide and padas 3 deg 20', so an arc-minute cannot
    move a nakshatra and moves a pada boundary by well under a minute of clock
    time. It is not a full Lahiri series and should not be used for anything
    needing sub-arc-second precision.
  * Sunrise/sunset use the standard -0:34 refraction horizon with `pressure = 0`,
    which is the convention published Indian panchangs follow (it is what makes
    the Rahu Kaal check above land on the minute).
  * The Hindu day runs sunrise-to-sunrise, so the weekday driving the day-part
    and hora tables is the weekday **at sunrise**, not at midnight.

Nothing in this module is a trading signal. Rahu Kaal being inauspicious is a
traditional assertion with no measured backing in this repo — FA-2 (measure the
windows against a random-window baseline) has never been run. Callers should
present these as almanac facts, not as bias.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, NamedTuple

import ephem

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


class Place(NamedTuple):
    """An observing location. Defaults to Mumbai (NSE/BSE)."""
    name: str
    lat: str
    lon: str
    elevation: float = 14.0


MUMBAI = Place("Mumbai", "19.0760", "72.8777", 14.0)

# ── Reference tables ────────────────────────────────────────────────────────
# Chaldean order (classical descending "speed"), the sequence planetary hours
# follow. The first hora of a day belongs to that weekday's ruler, then the
# sequence walks this list cyclically.
CHALDEAN = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")

#: Weekday ruler, keyed by Python's weekday() (Mon=0 … Sun=6).
DAY_LORD = {0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter",
            4: "Venus", 5: "Saturn", 6: "Sun"}

#: Which of the 8 equal day-parts each inauspicious window occupies (1-indexed),
#: keyed by weekday(). These are the standard published tables; the Rahu Kaal
#: row is the one verified to the minute against a published card (Tue -> 7th).
RAHU_KAAL_PART = {0: 2, 1: 7, 2: 5, 3: 6, 4: 4, 5: 3, 6: 8}
YAMAGANDA_PART = {0: 4, 1: 3, 2: 2, 3: 1, 4: 7, 5: 6, 6: 5}
GULIKA_PART = {0: 6, 1: 5, 2: 4, 3: 3, 4: 2, 5: 1, 6: 7}

NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
)

#: Vimshottari dasha sequence and years. Nakshatra lords repeat this 9-cycle,
#: and the same proportions subdivide each nakshatra into KP sub-lords.
VIMSHOTTARI = (("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10),
               ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19),
               ("Mercury", 17))
VIMSHOTTARI_TOTAL = 120

TITHI_NAMES = (
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Purnima",
)

RETRO_BODIES = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")

NAK_SPAN = 360.0 / 27.0          # 13°20'
PADA_SPAN = NAK_SPAN / 4.0       # 3°20'


# ── Time helpers ────────────────────────────────────────────────────────────
def _to_ist(edate: Any) -> dt.datetime:
    """ephem.Date (UTC) -> tz-aware IST datetime.

    Never use `ephem.localtime` here: it converts to the *machine's* timezone,
    which silently produces nonsense on a non-IST host.
    """
    naive_utc = ephem.Date(edate).datetime()
    return naive_utc.replace(tzinfo=dt.timezone.utc).astimezone(IST)


def _to_ephem(when: dt.datetime) -> ephem.Date:
    """tz-aware (or IST-assumed) datetime -> ephem.Date in UTC."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=IST)
    return ephem.Date(when.astimezone(dt.timezone.utc).replace(tzinfo=None))


def _observer(place: Place, when_utc: ephem.Date) -> ephem.Observer:
    o = ephem.Observer()
    o.lat, o.lon, o.elevation = place.lat, place.lon, place.elevation
    # Published Indian panchangs use the standard refraction horizon; this pair
    # is what reproduces their sunrise to the minute.
    o.pressure = 0
    o.horizon = "-0:34"
    o.date = when_utc
    return o


# ── Sun ─────────────────────────────────────────────────────────────────────
def sun_times(d: dt.date, place: Place = MUMBAI) -> dict[str, Any]:
    """Sunrise and sunset (IST) for the civil date `d` at `place`."""
    midnight_ist = dt.datetime(d.year, d.month, d.day, 0, 0, tzinfo=IST)
    o = _observer(place, _to_ephem(midnight_ist))
    sun = ephem.Sun()
    sunrise = _to_ist(o.next_rising(sun))
    o.date = _to_ephem(sunrise)
    sunset = _to_ist(o.next_setting(sun))
    return {"sunrise": sunrise, "sunset": sunset,
            "day_length": sunset - sunrise}


def _next_sunrise(after: dt.datetime, place: Place) -> dt.datetime:
    o = _observer(place, _to_ephem(after))
    return _to_ist(o.next_rising(ephem.Sun()))


# ── Day parts: Rahu Kaal / Yamaganda / Gulika ───────────────────────────────
def day_parts(d: dt.date, place: Place = MUMBAI) -> dict[str, Any]:
    """The three classical inauspicious windows, as 1/8 divisions of the day.

    Sunrise->sunset is split into 8 equal parts and each window takes a fixed
    part per weekday (see the *_PART tables). The weekday is taken at sunrise
    because the Hindu day runs sunrise-to-sunrise.
    """
    t = sun_times(d, place)
    sunrise, sunset = t["sunrise"], t["sunset"]
    part = (sunset - sunrise) / 8
    wd = sunrise.date().weekday()

    def window(table: dict[int, int]) -> dict[str, Any]:
        i = table[wd] - 1
        start = sunrise + part * i
        return {"start": start, "end": start + part, "part": table[wd]}

    return {
        "sunrise": sunrise,
        "sunset": sunset,
        "weekday": sunrise.strftime("%A"),
        "part_length": part,
        "rahu_kaal": window(RAHU_KAAL_PART),
        "yamaganda": window(YAMAGANDA_PART),
        "gulika": window(GULIKA_PART),
    }


# ── Hora (planetary hours) ──────────────────────────────────────────────────
def hora_sequence(d: dt.date, place: Place = MUMBAI) -> list[dict[str, Any]]:
    """24 planetary-hour blocks: 12 across the day, 12 across the night.

    Day horas divide sunrise->sunset into 12 equal parts; night horas divide
    sunset->next sunrise. Unequal in length unless it happens to be an equinox,
    which is the point — they are *seasonal* hours, not clock hours.
    """
    t = sun_times(d, place)
    sunrise, sunset = t["sunrise"], t["sunset"]
    next_sr = _next_sunrise(sunset, place)

    lord = DAY_LORD[sunrise.date().weekday()]
    start_idx = CHALDEAN.index(lord)

    # Build the 25 boundaries first, then pair them. Deriving each block from
    # adjacent boundaries makes the sequence contiguous *by construction* —
    # `start + length` repeated 12 times accumulates microsecond rounding and
    # leaves visible gaps, and the day/night seam drifts off sunset.
    day_total, night_total = sunset - sunrise, next_sr - sunset
    bounds = [sunrise + day_total * k / 12 for k in range(12)]
    bounds.append(sunset)                                   # exact seam
    bounds += [sunset + night_total * k / 12 for k in range(1, 12)]
    bounds.append(next_sr)                                  # exact end

    return [{
        "index": k + 1,
        "lord": CHALDEAN[(start_idx + k) % 7],
        "start": bounds[k],
        "end": bounds[k + 1],
        "phase": "day" if k < 12 else "night",
    } for k in range(24)]


def hora_at(d: dt.date, place: Place = MUMBAI,
            when: dt.datetime | None = None) -> dict[str, Any]:
    """The hora block containing `when`, plus the one after it.

    Returns `{"current": block|None, "next": block|None}`. `current` is None when
    `when` falls outside this date's sunrise->next-sunrise span (e.g. the small
    hours, which belong to the previous Hindu day).
    """
    blocks = hora_sequence(d, place)
    if when is None:
        when = dt.datetime.now(IST)
    elif when.tzinfo is None:
        when = when.replace(tzinfo=IST)
    for i, b in enumerate(blocks):
        if b["start"] <= when < b["end"]:
            return {"current": b, "next": blocks[i + 1] if i + 1 < len(blocks) else None}
    return {"current": None, "next": None}


# ── Sidereal moon: nakshatra, pada, sub-lord ────────────────────────────────
def _lahiri_ayanamsa(when: dt.datetime) -> float:
    """Lahiri ayanamsa in degrees — linear approximation.

    23.85 deg at J2000 drifting at the precession rate (~50.29"/yr). Good to
    roughly an arc-minute over this repo's date range; see the module docstring
    for why that is sufficient for nakshatra/pada work and insufficient for
    anything finer.
    """
    year = when.year + (when.timetuple().tm_yday - 1) / 365.25
    return 23.85 + (year - 2000.0) * (50.29 / 3600.0)


def _ecliptic_lon_of_date(body_factory: Any, when: dt.datetime) -> float:
    """Geocentric ecliptic longitude in degrees, referred to the ecliptic OF DATE.

    The `epoch=` argument is load-bearing and easy to omit. `ephem` defaults to
    J2000, and an ayanamsa is defined against the ecliptic of date — mixing the
    two leaves the precession between J2000 and now (~0.36 deg by 2026, about 40
    minutes of lunar motion) in the answer. That is large enough to put a pada
    boundary in the wrong half-hour while still looking plausible, which is
    exactly the kind of error a published-value check catches and eyeballing
    does not.
    """
    e = _to_ephem(when)
    body = body_factory()
    body.compute(e, epoch=e)
    return float(ephem.Ecliptic(body, epoch=e).lon) * 180.0 / ephem.pi


def _sidereal_moon_longitude(when: dt.datetime) -> float:
    tropical = _ecliptic_lon_of_date(ephem.Moon, when)
    return (tropical - _lahiri_ayanamsa(when)) % 360.0


def _sub_lord(longitude: float) -> dict[str, Any]:
    """KP sub-lord: Vimshottari proportions applied inside one nakshatra.

    The nakshatra's own lord starts the sequence, and each sub-span is
    `years/120` of the 13 deg 20' nakshatra width.
    """
    nak_idx = int(longitude // NAK_SPAN)
    offset = longitude - nak_idx * NAK_SPAN
    start_lord = nak_idx % 9
    cursor = 0.0
    for step in range(9):
        name, years = VIMSHOTTARI[(start_lord + step) % 9]
        span = NAK_SPAN * years / VIMSHOTTARI_TOTAL
        if offset < cursor + span or step == 8:
            return {"sub_lord": name,
                    "sub_start_deg": nak_idx * NAK_SPAN + cursor,
                    "sub_end_deg": nak_idx * NAK_SPAN + cursor + span}
        cursor += span
    raise AssertionError("unreachable")       # pragma: no cover


def _crossing_time(target_deg: float, when: dt.datetime,
                   max_hours: float = 120.0) -> dt.datetime | None:
    """When does the sidereal moon next reach `target_deg`? Bisection.

    The moon moves ~13.2 deg/day and never retrogrades in longitude, so a
    monotonic bisection on "degrees travelled since `when`" is exact enough to
    the second and needs no derivative.
    """
    start = _sidereal_moon_longitude(when)
    need = (target_deg - start) % 360.0
    if need == 0:
        return when

    def travelled(h: float) -> float:
        lon = _sidereal_moon_longitude(when + dt.timedelta(hours=h))
        return (lon - start) % 360.0

    lo, hi = 0.0, 1.0
    while hi <= max_hours and travelled(hi) < need:
        lo, hi = hi, hi * 2
    if hi > max_hours:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if travelled(mid) < need:
            lo = mid
        else:
            hi = mid
    return when + dt.timedelta(hours=(lo + hi) / 2)


def moon_nakshatra(when: dt.datetime | None = None) -> dict[str, Any]:
    """Nakshatra, pada, lords and the transit times out of each.

    `pada_ends` / `nakshatra_ends` are the clock times the moon leaves the
    current pada and the current nakshatra — the "rolling to pada 4 by 06:31"
    detail a published card prints.
    """
    if when is None:
        when = dt.datetime.now(IST)
    lon = _sidereal_moon_longitude(when)
    nak_idx = int(lon // NAK_SPAN)
    into_nak = lon - nak_idx * NAK_SPAN
    pada = int(into_nak // PADA_SPAN) + 1

    sub = _sub_lord(lon)
    pada_end_deg = nak_idx * NAK_SPAN + pada * PADA_SPAN
    nak_end_deg = (nak_idx + 1) * NAK_SPAN

    return {
        "longitude": lon,
        "nakshatra": NAKSHATRAS[nak_idx],
        "nakshatra_index": nak_idx + 1,
        "pada": pada,
        "lord": VIMSHOTTARI[nak_idx % 9][0],
        "sub_lord": sub["sub_lord"],
        "degrees_into_nakshatra": into_nak,
        "pct_through_nakshatra": into_nak / NAK_SPAN * 100.0,
        "pada_ends": _crossing_time(pada_end_deg % 360.0, when),
        "nakshatra_ends": _crossing_time(nak_end_deg % 360.0, when),
        "ayanamsa": _lahiri_ayanamsa(when),
    }


# ── Tithi ───────────────────────────────────────────────────────────────────
def tithi(when: dt.datetime | None = None) -> dict[str, Any]:
    """Lunar day: Moon-minus-Sun elongation in 12-degree steps.

    Ayanamsa-free — a *difference* of two longitudes, so the sidereal offset
    cancels and no approximation enters here.
    """
    if when is None:
        when = dt.datetime.now(IST)
    e = _to_ephem(when)
    moon = float(ephem.Ecliptic(ephem.Moon(e)).lon) * 180.0 / ephem.pi
    sun = float(ephem.Ecliptic(ephem.Sun(e)).lon) * 180.0 / ephem.pi
    elong = (moon - sun) % 360.0
    number = int(elong // 12.0) + 1              # 1..30
    paksha = "Shukla" if number <= 15 else "Krishna"
    within = number if number <= 15 else number - 15
    if number == 15:
        name = "Purnima"
    elif number == 30:
        name = "Amavasya"
    else:
        name = TITHI_NAMES[within - 1]
    return {
        "number": number,
        "name": name,
        "paksha": paksha,
        "elongation": elong,
        "pct_complete": (elong % 12.0) / 12.0 * 100.0,
    }


# ── Retrogrades ─────────────────────────────────────────────────────────────
def retrogrades(when: dt.datetime | None = None) -> dict[str, bool]:
    """Which classical planets are retrograde, by finite difference in longitude.

    Compares ecliptic longitude across +-6h. Sidereal vs tropical is irrelevant
    for a sign test, so no ayanamsa is involved.
    """
    if when is None:
        when = dt.datetime.now(IST)
    out: dict[str, bool] = {}
    for name in RETRO_BODIES:
        body = getattr(ephem, name)
        before = float(ephem.Ecliptic(
            body(_to_ephem(when - dt.timedelta(hours=6)))).lon)
        after = float(ephem.Ecliptic(
            body(_to_ephem(when + dt.timedelta(hours=6)))).lon)
        delta = (after - before + ephem.pi) % (2 * ephem.pi) - ephem.pi
        out[name] = delta < 0
    return out


# ── Everything, one call ────────────────────────────────────────────────────
def panchang(d: dt.date | None = None, place: Place = MUMBAI,
             now: dt.datetime | None = None) -> dict[str, Any]:
    """The full day's almanac, ready for a brief card.

    `now` (default: the current IST moment) selects which hora is "current" and
    the instant the nakshatra/tithi are read at. Moon phase is delegated to
    `astro_trading.get_lunar_phase` — this module never computes a second answer
    for it (roadmap FA-0).
    """
    if d is None:
        d = dt.datetime.now(IST).date()
    if now is None:
        now = dt.datetime.now(IST)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=IST)

    parts = day_parts(d, place)
    horas = hora_sequence(d, place)
    at = hora_at(d, place, now)

    # Moon phase: single source of truth lives elsewhere (roadmap FA-0). Narrow
    # the failure to the DB/coverage case only — an over-broad `except Exception`
    # here silently swallowed a *wrong class name* during development and made a
    # plain bug look like an empty data field, which is precisely how a moon
    # disagreement would go unnoticed.
    from astro_trading import AstroIndicators       # hard import: name must exist
    try:
        lunar: dict[str, Any] | None = AstroIndicators().get_lunar_phase(d)
    except (OSError, ValueError, KeyError):         # DB missing / date uncovered
        lunar = None

    return {
        "date": d,
        "place": place.name,
        "as_of": now,
        "sunrise": parts["sunrise"],
        "sunset": parts["sunset"],
        "weekday": parts["weekday"],
        "day_lord": DAY_LORD[parts["sunrise"].date().weekday()],
        "rahu_kaal": parts["rahu_kaal"],
        "yamaganda": parts["yamaganda"],
        "gulika": parts["gulika"],
        "hora_current": at["current"],
        "hora_next": at["next"],
        "hora_sequence": horas,
        "nakshatra": moon_nakshatra(now),
        "tithi": tithi(now),
        "retrogrades": retrogrades(now),
        "lunar_phase": lunar,
    }


# ── Self-check against published values ─────────────────────────────────────
def verify() -> bool:
    """Re-derive the two values a published panchang card printed.

    Run with `python tools/panchang.py`. This exists because the failure mode
    here is *plausible wrong answers*, not exceptions: an early version mixed
    J2000 and of-date ecliptic longitudes and put the pada transition at 07:15
    instead of 06:31 — a 44-minute error that looked entirely reasonable on its
    own. Only a published reference catches that, so the reference lives here.
    """
    ok = True

    def check(label: str, got: Any, want: Any) -> None:
        nonlocal ok
        good = got == want
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':4}  {label}: {got}"
              + ("" if good else f"  (expected {want})"))

    d = dt.date(2026, 7, 28)                      # Tuesday
    rk = day_parts(d)["rahu_kaal"]
    check("Rahu Kaal start (card: 04:00 PM)", rk["start"].strftime("%H:%M"), "16:00")
    check("Rahu Kaal end   (card: 05:38 PM)", rk["end"].strftime("%H:%M"), "17:38")

    nk = moon_nakshatra(dt.datetime(2026, 7, 28, 5, 30, tzinfo=IST))
    check("05:30 IST nakshatra", nk["nakshatra"], "Purva Ashadha")
    check("05:30 IST pada", nk["pada"], 3)
    check("pada 3 ends (card: 06:31)", nk["pada_ends"].strftime("%H:%M"), "06:31")

    print("\nverify():", "all published values reproduced" if ok else "MISMATCH")
    return ok


if __name__ == "__main__":                        # pragma: no cover
    import sys as _sys
    _sys.exit(0 if verify() else 1)
