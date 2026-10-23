"""The Indicator Browser's NSE evidence line stays true to the study index — B-154.

* every mapped key is a real indicator, every mapped subject is in
  named_studies, and each hand-written line still matches the verdict it was
  written for (the same check claims_lint runs as CHECK 0d);
* every indicator gets a payload; unmapped ones read "Not measured on NSE yet";
* the label never claims more than the verdict: only POSITIVE says "edge";
* the lines carry no promise words;
* the deliberate non-mappings (oiwalls→B-94, cpr→B-97, deltaprofile→B-48,
  vwap/ema20→B-90, ew2deg→B-134/135, simplevol→B-122, structure_chain→CHoCH) hold;
* the server route answers for all 59 keys.

Run:  python -m pytest tools/test_indicator_evidence.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import indicator_evidence as ie

HERE = Path(__file__).resolve().parent
_defs = (HERE / "chart_dashboard.html").read_text(encoding="utf-8") \
    .split("const INDICATOR_DEFS = [", 1)[1].split("\n];", 1)[0]
KEYS = re.findall(r"key:'([a-z0-9_]+)'", _defs)


def test_self_check_is_clean():
    assert ie.self_check() == []


def test_mapped_keys_are_real_indicators():
    assert set(ie.EVIDENCE) <= set(KEYS)


def test_every_indicator_gets_a_payload():
    ev = ie.evidence(KEYS)
    assert set(ev) == set(KEYS)
    for k in set(KEYS) - set(ie.EVIDENCE):
        assert ev[k]["verdict"] is None and ev[k]["line"] == ie.UNMEASURED_LINE


@pytest.mark.parametrize("key", sorted(ie.EVIDENCE))
def test_label_matches_verdict(key):
    e = ie.evidence([key])[key]
    assert e["items"], "a mapped key must cite at least one study"
    if e["verdict"] != "POSITIVE":
        assert "edge" not in e["label"].lower() or e["label"] == "No edge found"


@pytest.mark.parametrize("key", sorted(ie.EVIDENCE))
def test_no_promise_words(key):
    assert not re.search(r"\b(guaranteed?|high[- ]probability|winning|best)\b",
                         ie.EVIDENCE[key]["line"], re.I)


@pytest.mark.parametrize("key", ["oiwalls", "cpr", "deltaprofile", "vwap", "ema20",
                                 "ew2deg", "simplevol"])
def test_near_misses_stay_unmapped(key):
    """Checked a computation or a different quantity — not the overlay's effect."""
    assert key not in ie.EVIDENCE


def test_structure_chain_is_not_scored_by_the_choch_scanner():
    """The CHoCH studies scored the scanner's pivot-5 walk, not the overlay."""
    assert "Bullish CHoCH (last 5 sessions)" not in ie.EVIDENCE["structure_chain"]["subjects"]


def test_combined_rules():
    assert ie.combined(["NEGATIVE", "NULL"]) == "NEGATIVE"
    assert ie.combined(["MIXED", "NEGATIVE"]) == "MIXED"
    assert ie.combined(["POSITIVE", "NULL"]) == "MIXED"
    assert ie.combined(["POSITIVE"]) == "POSITIVE"
    assert ie.combined(["UNRECORDED"]) is None


def test_route_answers_for_every_key():
    import chart_server as cs
    cs.app.config["TESTING"] = True
    r = cs.app.test_client().get("/api/indicator_evidence")
    assert r.status_code == 200
    assert set(r.get_json()) == set(KEYS)
