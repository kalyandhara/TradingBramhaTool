"""Tests for industry_map — parser and cache behaviour. No network."""
from __future__ import annotations

import industry_map as im

PAGE = """
<a href="/market/IN04/" title="Broad Sector">Fast Moving Consumer Goods</a>
<a href="/market/IN04/IN0401/" title="Sector">Fast Moving Consumer Goods</a>
<a href="/market/IN04/IN0401/IN040101/" title="Industry">Agricultural Food &amp; other Products</a>
<a href="/market/IN04/IN0401/IN040101/IN040101004/" title="Industry">Sugar</a>
"""


def test_parse_reads_four_levels_and_unescapes():
    c = im.parse(PAGE)
    assert c == {"macro": "Fast Moving Consumer Goods", "sector": "Fast Moving Consumer Goods",
                 "industry": "Agricultural Food & other Products", "basic": "Sugar"}


def test_parse_returns_none_without_breadcrumb():
    assert im.parse("<html>login required</html>") is None


def test_load_fetches_only_missing_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(im, "CACHE", tmp_path / "m.json")
    calls = []

    def fake(sym):
        calls.append(sym)
        return None if sym == "BAD" else {"macro": "M", "sector": "S", "industry": "I", "basic": sym}

    first = im.load(["A", "B", "BAD"], fetch=fake)
    assert set(first) == {"A", "B"}
    calls.clear()
    second = im.load(["A", "C"], fetch=fake)
    assert calls == ["C"]
    assert second["A"]["basic"] == "A"
