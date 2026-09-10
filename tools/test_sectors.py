"""Tests for sectors.py (B-64), offline.

The point of this module is that "sector" stops meaning three things. So the
tests pin the two properties that would let it silently start meaning three
things again:

  * every mapping target is IN the canonical vocabulary — a typo in a table must
    fail here rather than invent a 23rd sector at runtime;
  * an unresolvable pair returns None. The failure mode this module exists to
    prevent is a plausible-looking nearest guess, which is invisible forever.
"""
import pytest

import sectors as sc


def test_every_mapping_target_is_canonical():
    for table in (sc._BY_SECTOR, sc._BY_INDUSTRY):
        for key, target in table.items():
            assert target in sc.CANONICAL, f"{key!r} -> {target!r} is not canonical"


def test_canonical_has_no_duplicates():
    assert len(sc.CANONICAL) == len(set(sc.CANONICAL))


def test_industry_beats_sector_where_they_disagree():
    # Yahoo files gas distribution under Utilities; NSE files it under
    # Oil Gas & Consumable Fuels. The industry must win.
    assert sc.from_yahoo("Utilities", "Utilities - Regulated Gas") == "Oil Gas & Consumable Fuels"
    assert sc.from_yahoo("Utilities", "Utilities - Regulated Electric") == "Power"
    # Solar is Technology at Yahoo, Capital Goods at NSE.
    assert sc.from_yahoo("Technology", "Solar") == "Capital Goods"
    # ...and the plain Technology case still lands on IT.
    assert sc.from_yahoo("Technology", "Software - Application") == "Information Technology"


def test_the_four_ambiguous_yahoo_sectors_have_no_sector_level_default():
    """Industrials/Basic Materials/Consumer Cyclical/Utilities must NOT resolve
    from the sector alone — that is the guess this module refuses to make."""
    for s in ("Industrials", "Basic Materials", "Consumer Cyclical", "Utilities"):
        assert s not in sc._BY_SECTOR
        assert sc.from_yahoo(s, None) is None
        assert sc.from_yahoo(s, "Something Yahoo Has Not Invented Yet") is None


def test_unmapped_is_none_not_a_nearest_guess():
    assert sc.from_yahoo(None, None) is None
    assert sc.from_yahoo("", "") is None
    assert sc.from_yahoo("Utter Nonsense", "Also Nonsense") is None


def test_ambiguous_sectors_do_resolve_once_the_industry_is_known():
    assert sc.from_yahoo("Industrials", "Aerospace & Defense") == "Capital Goods"
    assert sc.from_yahoo("Industrials", "Engineering & Construction") == "Construction"
    assert sc.from_yahoo("Basic Materials", "Steel") == "Metals & Mining"
    assert sc.from_yahoo("Basic Materials", "Specialty Chemicals") == "Chemicals"
    assert sc.from_yahoo("Consumer Cyclical", "Auto Parts") == "Automobile and Auto Components"
    assert sc.from_yahoo("Consumer Cyclical", "Textile Manufacturing") == "Textiles"


def test_consumer_defensive_defaults_to_fmcg_but_retail_is_an_exception():
    assert sc.from_yahoo("Consumer Defensive", "Packaged Foods") == "Fast Moving Consumer Goods"
    assert sc.from_yahoo("Consumer Defensive", "Tobacco") == "Fast Moving Consumer Goods"
    assert sc.from_yahoo("Consumer Defensive", "Discount Stores") == "Consumer Services"


def test_whitespace_does_not_defeat_the_lookup():
    assert sc.from_yahoo("  Healthcare  ", "  ") == "Healthcare"
    assert sc.from_yahoo("Basic Materials", " Steel ") == "Metals & Mining"


def test_is_canonical():
    assert sc.is_canonical("Capital Goods")
    assert not sc.is_canonical("Industrials")     # a Yahoo label, not ours
    assert not sc.is_canonical(None)
    assert not sc.is_canonical("")


def test_symbol_map_uses_the_honest_name(monkeypatch):
    """`nse_universe` calls the field `industry` but fills it with SECTOR labels.
    symbol_map must read that key and return it under the right name."""
    fake = [
        {"symbol": "TCS", "industry": "Information Technology"},
        {"symbol": "TITAN", "industry": "Consumer Durables"},
        {"symbol": "BLANK", "industry": ""},          # dropped, not stored empty
        {"symbol": "", "industry": "Capital Goods"},  # dropped
    ]
    import types
    mod = types.SimpleNamespace(fetch_constituents=lambda u: fake)
    monkeypatch.setitem(__import__("sys").modules, "nse_universe", mod)
    m = sc.symbol_map("nifty500")
    assert m == {"TCS": "Information Technology", "TITAN": "Consumer Durables"}


def test_coverage_reports_unknown_labels_rather_than_hiding_them(monkeypatch):
    fake = [
        {"symbol": "A", "industry": "Capital Goods"},
        {"symbol": "B", "industry": "Something NSE Added In 2027"},
    ]
    import types
    mod = types.SimpleNamespace(fetch_constituents=lambda u: fake)
    monkeypatch.setitem(__import__("sys").modules, "nse_universe", mod)
    c = sc.coverage("nifty500")
    assert c["symbols"] == 2
    assert c["unknown_labels"] == ["Something NSE Added In 2027"]
    assert c["canonical_pct"] == 50.0
