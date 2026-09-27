"""Tests for pa_chart_focus — pane assignment. No network, no Streamlit."""
from __future__ import annotations

from urllib.parse import parse_qs

import pa_chart_focus as f


def test_context_is_sector_index_only_when_chartable():
    assert f.context_for("Healthcare") == ("^CNXPHARMA", "Nifty Pharma", True)
    assert f.context_for("Realty") == ("^NSEI", "Nifty 50", False)
    assert f.context_for(None)[0] == "^NSEI"


def test_no_pins_gives_two_charts():
    assert f.pane_symbols("SUNPHARMA", "^CNXPHARMA", []) == ["^CNXPHARMA"]


def test_pins_follow_context_and_pad_to_offered_count_with_benchmarks():
    rest = f.pane_symbols("SUNPHARMA", "^CNXPHARMA", ["CIPLA"])
    assert rest == ["^CNXPHARMA", "CIPLA", "^NSEI"]
    assert len(f.pane_symbols("SUNPHARMA", "^CNXPHARMA", ["CIPLA", "LUPIN"])) + 1 == 4


def test_focus_and_duplicates_are_not_repeated_and_pins_capped():
    pins = ["A", "B", "C", "D", "E", "F", "G", "H", "SUNPHARMA"]
    rest = f.pane_symbols("SUNPHARMA", "^NSEI", pins)
    assert "SUNPHARMA" not in rest
    assert len(rest) + 1 == 8 and rest[1:7] == ["A", "B", "C", "D", "E", "F"]


def test_chart_query_shape():
    q = parse_qs(f.chart_query("TCS", "^CNXIT", ["INFY"]))
    assert q["layout"] == ["pa"] and q["charts"] == ["4"]
    assert q["compare"] == ["^CNXIT,INFY.NS,^NSEI"]
