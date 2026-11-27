"""Page deep links: ?nav=page&page=<name> opens a registered desk page (used by
the Multi-Chart replay's Back button)."""
from __future__ import annotations

import ui_tables as uit


def test_page_link_round_trips():
    url = uit.page_link("Recommendation Audit")
    assert url == "http://localhost:8501/?nav=page&page=Recommendation%20Audit"
    assert uit.page_from_query({"nav": "page", "page": "Recommendation Audit"},
                               {"Recommendation Audit"}) == "Recommendation Audit"


def test_page_from_query_ignores_unknown_pages_and_other_navs():
    pages = {"Recommendation Audit"}
    assert uit.page_from_query({"nav": "page", "page": "Nope"}, pages) is None
    assert uit.page_from_query({"nav": "analyze", "page": "Recommendation Audit"}, pages) is None
    assert uit.page_from_query({}, pages) is None
