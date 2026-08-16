#!/usr/bin/env python3
"""
sbc_nama.py — Nama-nakshatra: map a name/instrument to its nakshatra by sound.

In SBC tradition, the first syllable (akshara) of a name places it on a
nakshatra. Each nakshatra owns 4 padas, each pada carries one naming syllable
(27 x 4 = 108 — the "108 Badra grid"). An instrument's first sound therefore
resolves to a nakshatra, and whatever vedhas strike that nakshatra apply to it.

The 108-pada syllable table below is the standard published Vedic naming table
(Janma-nakshatra aksharas). This is public and exact — no proprietary guess.

Resolver: normalise the name, then match the longest naming syllable that its
first sound begins with. Language-agnostic in spirit ("Silver"/"Chandi" both
resolve by their leading sound), though transliteration is imperfect for
non-Sanskrit names — see SECTOR_OVERRIDES for curated market mappings.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# 27 nakshatras x 4 pada syllables (standard transliteration).
PADA_SYLLABLES: Dict[str, List[str]] = {
    "Ashwini": ["chu", "che", "cho", "la"],
    "Bharani": ["li", "lu", "le", "lo"],
    "Krittika": ["a", "i", "u", "e"],
    "Rohini": ["o", "va", "vi", "vu"],
    "Mrigashira": ["ve", "vo", "ka", "ki"],
    "Ardra": ["ku", "gha", "nga", "chha"],
    "Punarvasu": ["ke", "ko", "ha", "hi"],
    "Pushya": ["hu", "he", "ho", "da"],
    "Ashlesha": ["di", "du", "de", "do"],
    "Magha": ["ma", "mi", "mu", "me"],
    "Purva Phalguni": ["mo", "ta", "ti", "tu"],
    "Uttara Phalguni": ["te", "to", "pa", "pi"],
    "Hasta": ["pu", "sha", "na", "tha"],
    "Chitra": ["pe", "po", "ra", "ri"],
    "Swati": ["ru", "re", "ro", "ta"],
    "Vishakha": ["ti", "tu", "te", "to"],
    "Anuradha": ["na", "ni", "nu", "ne"],
    "Jyeshtha": ["no", "ya", "yi", "yu"],
    "Mula": ["ye", "yo", "bha", "bhi"],
    "Purva Ashadha": ["bhu", "dha", "pha", "dha"],
    "Uttara Ashadha": ["bhe", "bho", "ja", "ji"],
    "Shravana": ["ju", "je", "jo", "gha"],
    "Dhanishta": ["ga", "gi", "gu", "ge"],
    "Shatabhisha": ["go", "sa", "si", "su"],
    "Purva Bhadrapada": ["se", "so", "da", "di"],
    "Uttara Bhadrapada": ["du", "tha", "jha", "da"],
    "Revati": ["de", "do", "cha", "chi"],
}

# syllable -> (nakshatra, pada). Longer syllables win on prefix match.
_SYL_INDEX: List[Tuple[str, str, int]] = sorted(
    ((syl, nak, i + 1)
     for nak, syls in PADA_SYLLABLES.items()
     for i, syl in enumerate(syls)),
    key=lambda t: -len(t[0]),
)

# Curated market/instrument -> nakshatra overrides. English brand/ticker names
# don't transliterate cleanly, so the tradeable universe is pinned by first
# sound where the auto-resolver would be unreliable. Extend freely.
SECTOR_OVERRIDES: Dict[str, str] = {
    # Metals / commodities — safe-havens use the Sanskrit/Hindi name (nama is
    # language-agnostic): Sona (gold) -> Purva Bhadrapada; Chandi (silver) ->
    # Revati. This matches the reference tool's "Gold (Sona)" nakshatra.
    "Gold": "Purva Bhadrapada",  # Sona -> So
    "Silver": "Revati",          # Chandi -> Cha
    "Crude Oil": "Ardra",        # Ku~Cru
    "Copper": "Mrigashira",      # Ka~Co
    "Natural Gas": "Hasta",      # Na
    "Aluminium": "Krittika",     # A
    "Zinc": "Shatabhisha",       # Si~Zi
    "Nickel": "Anuradha",        # Ni
    "Lead": "Ashwini",           # La~Le
    # Indices
    "NIFTY 50": "Anuradha",      # Ni
    "Bank NIFTY": "Mula",        # Bha~Ba
    "NIFTY IT": "Anuradha",
    "Sensex": "Purva Bhadrapada",  # Se
    "Nasdaq": "Hasta",           # Na
    "Dow Jones": "Pushya",       # Da~Do
    "FTSE": "Uttara Phalguni",   # Pa~F
    # Crypto
    "Bitcoin": "Mula",           # Bhi~Bi
    "Ethereum": "Krittika",      # E
    "Solana": "Shatabhisha",     # So~Sa
    "Ripple XRP": "Chitra",      # Ri
    "Dogecoin": "Pushya",        # Da~Do
    # Forex
    "USD/INR": "Krittika",       # U
    "Euro EUR": "Krittika",      # E~U
    "Pound GBP": "Uttara Phalguni",  # Pa~Po
    "Yen JPY": "Mula",           # Ye
    # Sectors
    "NIFTY Auto": "Krittika",    # A
    "NIFTY FMCG": "Uttara Phalguni",  # Pa~F
    "NIFTY Pharma": "Uttara Phalguni",  # Pa
    "NIFTY Metal": "Magha",      # Me
    "NIFTY Energy": "Krittika",  # E
    "Defense": "Pushya",         # De~Da
}


# Categorised instrument catalogue for the Nama name-analysis panel (mirrors
# the SBC tool's left column). Each entry is (display, resolver-name); resolver
# name is what resolve_nakshatra() maps by first sound (via override or auto).
NAMA_CATALOG: Dict[str, List[str]] = {
    "Commodities": ["Silver", "Gold", "Crude Oil", "Copper", "Aluminium",
                    "Zinc", "Nickel", "Lead", "Natural Gas"],
    "Indices": ["NIFTY 50", "Bank NIFTY", "Sensex", "Midcap", "FinNifty",
                "Dow Jones", "Nasdaq", "S&P 500", "DAX", "FTSE"],
    "Crypto": ["Bitcoin", "Ethereum", "Solana", "Ripple XRP", "Dogecoin",
               "BNB", "Cardano ADA", "Polygon MATIC", "Tether USDT",
               "Shiba SHIB"],
    "Forex": ["USD/INR", "Euro EUR", "Pound GBP", "Yen JPY", "Swiss CHF",
              "AUD", "Dirham AED", "Yuan CNY", "Ruble RUB"],
    "Indian Stocks": ["Reliance", "Tata", "Infosys", "HDFC Bank", "SBI",
                      "Bajaj", "Wipro", "Adani", "Maruti", "HUL", "ICICI",
                      "Kotak", "Axis Bank", "L&T", "BHEL", "PowerGrid",
                      "Zomato", "Paytm", "Nykaa", "DMart"],
}

# Deterministic first-sound overrides for catalogue items the auto-resolver
# would miss or map ambiguously (brand/ticker names).
SECTOR_OVERRIDES.update({
    "Midcap": "Magha",             # Mi
    "FinNifty": "Uttara Phalguni",  # Fi~Pi
    "S&P 500": "Shatabhisha",      # Sa
    "DAX": "Pushya",               # Da
    "Solana": "Purva Bhadrapada",  # So
    "Dogecoin": "Revati",          # Do
    "BNB": "Mula",                 # Ba~Bha
    "Cardano ADA": "Mrigashira",   # Ka~Ca
    "Polygon MATIC": "Chitra",     # Po
    "Tether USDT": "Uttara Phalguni",  # Te
    "Shiba SHIB": "Hasta",         # Shi~Sha
    "Swiss CHF": "Swati",          # Swa~Sa
    "AUD": "Krittika",             # A
    "Dirham AED": "Ashlesha",      # Di
    "Yuan CNY": "Jyeshtha",        # Yu
    "Ruble RUB": "Swati",          # Ru
    "Reliance": "Swati",           # Re
    "Tata": "Swati",               # Ta
    "Infosys": "Krittika",         # I
    "HDFC Bank": "Punarvasu",      # Ha
    "SBI": "Shatabhisha",          # Sa
    "Bajaj": "Mula",               # Ba~Bha
    "Wipro": "Rohini",             # Wi~Vi
    "Adani": "Krittika",           # A
    "Maruti": "Magha",             # Ma
    "HUL": "Pushya",               # Hu
    "ICICI": "Krittika",           # I
    "Kotak": "Punarvasu",          # Ko
    "Axis Bank": "Krittika",       # A
    "L&T": "Ashwini",              # La
    "BHEL": "Uttara Ashadha",      # Bhe
    "PowerGrid": "Chitra",         # Po
    "Zomato": "Uttara Ashadha",    # Zo~Jo
    "Paytm": "Uttara Phalguni",    # Pa
    "Nykaa": "Hasta",              # Ny~Na
    "DMart": "Pushya",             # Da
})


def _normalise(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalpha())


def resolve_nakshatra(name: str) -> Optional[Tuple[str, int]]:
    """(nakshatra, pada) for a name via its leading syllable, or None."""
    if name in SECTOR_OVERRIDES:
        nak = SECTOR_OVERRIDES[name]
        # pada = first pada whose syllable the override intends; default 1
        return nak, 1
    norm = _normalise(name)
    for syl, nak, pada in _SYL_INDEX:
        if norm.startswith(syl):
            return nak, pada
    return None


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    total = sum(len(v) for v in PADA_SYLLABLES.values())
    print(f"108-pada table: {len(PADA_SYLLABLES)} nakshatras x 4 = {total} padas")
    for m in ["Gold", "Silver", "Bitcoin", "NIFTY 50", "Crude Oil", "Reliance"]:
        print(f"  {m:12s} -> {resolve_nakshatra(m)}")
