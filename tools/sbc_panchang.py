#!/usr/bin/env python3
"""
sbc_panchang.py — Panchang header + Bhadra (Vishti karana) detection for SBC.

The SBC pre-trade filter is: check the Panchang first. If Bhadra (the Vishti
karana) is active, or the tithi is inauspicious, avoid buy-side entries. This
module computes the five limbs needed for the header and the Bhadra flag from
live Sun/Moon longitudes (PyEphem, sidereal Lahiri via sarvatobhadra_chakra).

Definitions
-----------
* Tithi   = ceil( ((moon_lon - sun_lon) mod 360) / 12 )      -> 1..30
            Shukla (waxing) 1..15, Krishna (waning) 16..30.
* Karana  = half a tithi; 60 per lunar month. Index k = int(elong / 6).
            k=0 -> Kimstughna (fixed); k=1..56 -> the 7 movable karanas
            cycling (Bava, Balava, Kaulava, Taitila, Gara, Vanija, VISHTI);
            k=57..59 -> Shakuni, Chatushpada, Naga (fixed).
            VISHTI == Bhadra, the malefic karana, at k in {7,14,...,56}.
* Nakshatra/Vara come from the Moon's nakshatra and the civil weekday.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from sarvatobhadra_chakra import compute_planets, IST_OFFSET

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Purnima/Amavasya",
]

MOVABLE_KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Gara",
                   "Vanija", "Vishti"]

VARA_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
              "Saturday", "Sunday"]  # Python weekday(): Mon=0


@dataclass
class Panchang:
    when_ist: datetime
    tithi_num: int             # 1..30
    tithi_name: str            # e.g. "Krishna Ashtami"
    paksha: str                # Shukla | Krishna
    karana: str
    bhadra_active: bool
    nakshatra: str             # Moon's nakshatra
    vara: str                  # weekday
    moon_lon: float
    sun_lon: float


def _elongation(dt_utc: datetime) -> tuple[float, float, float, str]:
    p = compute_planets(dt_utc)
    moon = p["Moon"].sidereal_lon
    sun = p["Sun"].sidereal_lon
    elong = (moon - sun) % 360.0
    return elong, moon, sun, p["Moon"].nakshatra


def karana_of(elong: float) -> tuple[str, bool]:
    """Return (karana_name, is_bhadra) for an elongation in degrees."""
    k = int(elong // 6.0)  # 0..59
    if k == 0:
        return "Kimstughna", False
    if k <= 56:
        name = MOVABLE_KARANAS[(k - 1) % 7]
        return name, name == "Vishti"
    return ["Shakuni", "Chatushpada", "Naga"][k - 57], False


def tithi_of(elong: float) -> tuple[int, str, str]:
    """Return (tithi_num 1..30, full_name, paksha)."""
    num = int(elong // 12.0) + 1          # 1..30
    paksha = "Shukla" if num <= 15 else "Krishna"
    idx = (num - 1) % 15
    return num, f"{paksha} {TITHI_NAMES[idx]}", paksha


def compute_panchang(when_ist: Optional[datetime] = None) -> Panchang:
    if when_ist is None:
        when_ist = datetime.utcnow() + IST_OFFSET
    dt_utc = when_ist - IST_OFFSET
    elong, moon, sun, nak = _elongation(dt_utc)
    tnum, tname, paksha = tithi_of(elong)
    karana, bhadra = karana_of(elong)
    vara = VARA_NAMES[when_ist.weekday()]
    return Panchang(
        when_ist=when_ist, tithi_num=tnum, tithi_name=tname, paksha=paksha,
        karana=karana, bhadra_active=bhadra, nakshatra=nak, vara=vara,
        moon_lon=round(moon, 2), sun_lon=round(sun, 2),
    )


def trading_note(p: Panchang) -> str:
    """One-line SBC pre-trade guidance from the Panchang."""
    if p.bhadra_active:
        return (f"BHADRA (Vishti karana) ACTIVE — {p.tithi_name} on {p.vara}. "
                "Inauspicious: avoid new buy-side entries; prefer sell/no-trade.")
    if p.tithi_name.endswith("Ashtami") and p.paksha == "Krishna":
        return ("Krishna Ashtami — traditionally weak for fresh longs. "
                "Trade light on the buy side.")
    return f"No Bhadra. {p.tithi_name}, {p.vara} — normal Panchang filter."


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    p = compute_panchang()
    print(f"Panchang @ {p.when_ist:%Y-%m-%d %H:%M} IST")
    print(f"  Tithi   : {p.tithi_name} (#{p.tithi_num})")
    print(f"  Karana  : {p.karana}  {'[BHADRA]' if p.bhadra_active else ''}")
    print(f"  Nakshatra: {p.nakshatra}")
    print(f"  Vara    : {p.vara}")
    print(f"  Moon/Sun: {p.moon_lon} / {p.sun_lon}")
    print(f"  Note    : {trading_note(p)}")
