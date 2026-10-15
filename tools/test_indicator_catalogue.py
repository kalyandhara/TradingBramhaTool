"""Every indicator in the Chart Tool panel has its plain-words entry — B-149.

The catalogue (indicator_catalogue.js) is what the beginner panel (B-150), the
goal chips (B-156) and the "new" badge read. Pinned here:

* every INDICATOR_DEFS key has an entry, and every entry is a real key;
* each entry has short (≤ 90 chars), desc (2–4 sentences), a known level,
  known goal ids, an ISO `added` date and a concept page that exists (or null);
* no promise words — "guaranteed", "high probability", "winning", "best" — until
  B-154 holds a POSITIVE measured verdict for that key (none does yet).

Run:  python -m pytest tools/test_indicator_catalogue.py -q
"""
import json
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
WIKI = HERE.parent / "trading-wiki" / "wiki"
JS = (HERE / "indicator_catalogue.js").read_text(encoding="utf-8")
HTML = (HERE / "chart_dashboard.html").read_text(encoding="utf-8")

INFO = json.loads(JS.split("/*JSON-BEGIN*/", 1)[1].split("/*JSON-END*/", 1)[0])
GOALS = set(json.loads(re.search(r"window\.INDICATOR_GOALS = (\{.*?\});", JS, re.S).group(1)))
_defs = HTML.split("const INDICATOR_DEFS = [", 1)[1].split("\n];", 1)[0]
KEYS = re.findall(r"key:'([a-z0-9_]+)'", _defs)

LEVELS = {"Beginner", "Intermediate", "Advanced"}
PROMISE = re.compile(r"\b(guaranteed?|high[- ]probability|winning|best)\b", re.I)
#: Keys with a POSITIVE B-154 verdict may use promise words — read from the
#: evidence index, so the exemption follows the measurement, not a hand list.
import indicator_evidence  # noqa: E402
POSITIVE_VERDICT: set[str] = indicator_evidence.positive_keys()


def test_every_def_has_an_entry_and_no_orphans():
    assert len(KEYS) == len(set(KEYS)) == 60
    assert set(KEYS) == set(INFO), (
        f"missing: {sorted(set(KEYS) - set(INFO))}, orphan: {sorted(set(INFO) - set(KEYS))}")


def test_page_loads_the_catalogue():
    assert '<script src="/indicator_catalogue.js"></script>' in HTML
    assert "Object.assign(d, (window.INDICATOR_INFO || {})[d.key]" in HTML


@pytest.mark.parametrize("key", sorted(INFO))
def test_entry_fields(key):
    e = INFO[key]
    assert set(e) == {"short", "desc", "level", "goals", "added", "concept"}
    assert 0 < len(e["short"]) <= 90, f"short is {len(e['short'])} chars"
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", e["desc"].strip()) if s]
    assert 2 <= len(sentences) <= 4, f"desc has {len(sentences)} sentences"
    assert e["level"] in LEVELS
    assert set(e["goals"]) <= GOALS
    assert re.fullmatch(r"2026-\d\d-\d\d", e["added"])
    if e["concept"] is not None:
        assert (WIKI / e["concept"]).is_file(), e["concept"]


@pytest.mark.parametrize("key", sorted(INFO))
def test_no_promise_words(key):
    if key in POSITIVE_VERDICT:
        return
    text = INFO[key]["short"] + " " + INFO[key]["desc"]
    m = PROMISE.search(text)
    assert not m, f"{key}: {m.group(0)!r} needs a positive B-154 verdict first"


def test_every_goal_is_reachable():
    """B-156's chips are useless if one returns nothing."""
    used = {g for e in INFO.values() for g in e["goals"]}
    assert used == GOALS
