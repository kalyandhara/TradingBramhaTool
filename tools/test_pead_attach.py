"""Tests for the PEAD walk's PIPELINE stage and its render round-trip — B-81.

`test_earnings_reaction.py` pins the measurement (drift from the reaction bar, an
unfinished window as None, a stale calendar yielding nothing). This file pins the
two things around it that the review found untested:

  * **`_attach_pead` is context and must behave like it.** It runs after the
    filter, so it may not change which names survive or in what order, and it may
    not take the pipeline down when the earnings side fails.

  * **The frame is no longer chosen by registry order.** The first version used
    ``next(n for n in sc.SCANNERS if not ...needs_full_history)`` — whichever
    scanner happened to sit first in the dict. It worked and it was wrong:
    adding a scanner at the top of the registry would have silently changed which
    fetch backed the walk. `DEFAULT_WINDOW` says what is wanted instead of naming
    a scanner that happens to want the same thing.

  * **The renderer sees two shapes of date.** A live hit carries `datetime.date`;
    an archived card (`daily_opportunity_cards`) has been through JSON and carries
    a string. Both reach the same renderer.

Run:  python -m pytest tools/test_pead_attach.py -q
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pytest

import opportunity_hub as oh


def _frame(n: int = 300, start: float = 100.0) -> pd.DataFrame:
    idx = pd.bdate_range("2025-06-02", periods=n)
    return pd.DataFrame({"close": [start + i for i in range(n)]}, index=idx)


def _walk(events=1):
    return {"symbol": "ACME", "measured": events, "consistency": events,
            "agreeable": events,
            "events": [{"date": date(2026, 7, 17), "snapped_days": 0,
                        "d1": 2.0, "d5": 1.0, "d20": 3.0, "complete": True}] * events}


@pytest.fixture
def hits():
    return {"AAA": {"best_card": {}, "scanners": ["x"]},
            "BBB": {"best_card": {}, "scanners": ["y"]}}


# ── The frame is asked for by CONTRACT, not by registry position ─────────────

def test_the_default_window_sentinel_is_not_a_scanner_name():
    """If it ever became one, asking for it would start meaning something else."""
    import scanner_templates as sc
    assert oh.DEFAULT_WINDOW not in sc.SCANNERS


def test_the_pipeline_asks_the_factory_for_the_default_window(monkeypatch):
    asked: list[str] = []

    def _factory(name):
        asked.append(name)
        return lambda s: _frame()

    monkeypatch.setattr(oh, "_attach_pead", lambda h, f: None)
    monkeypatch.setattr(oh, "pipeline_scanners", lambda: [])
    oh.run_scanner_pipeline([], _factory)
    assert asked == [oh.DEFAULT_WINDOW]


def test_a_factory_that_raises_on_an_unknown_name_does_not_break_the_pipeline(monkeypatch):
    """The docstring asks factories to answer for names they do not recognise.
    One that refuses breaks the contract — and the walk goes quiet rather than
    taking a scan of hundreds of names down with it."""
    def _factory(name):
        raise KeyError(name)

    monkeypatch.setattr(oh, "pipeline_scanners", lambda: [])
    assert oh.run_scanner_pipeline([], _factory) == {}


def test_both_shipped_factories_answer_the_sentinel_with_the_cheap_fetch():
    """The daily job's router is importable; the dashboard's `_scanner_fetch_fn`
    is not (importing it runs a Streamlit app), but both discriminate on the same
    single flag via `SCANNERS.get(name, {})`."""
    import opportunity_daily as od
    r = od._FetchRouter()
    assert r(oh.DEFAULT_WINDOW) is r.default
    assert r("ATH Breakout (all-time high)") is r.full


# ── Attaching is context: it may not change the shortlist ────────────────────

def test_attach_adds_the_walk_only_where_there_are_events(hits, monkeypatch):
    import earnings_reaction as er
    monkeypatch.setattr(er, "pead_walk",
                        lambda sym, df, **kw: _walk(1) if sym == "AAA" else _walk(0))
    oh._attach_pead(hits, lambda s: _frame())
    assert "pead" in hits["AAA"]
    assert "pead" not in hits["BBB"], "an empty walk must leave NO key at all"


def test_attach_never_adds_or_removes_a_name(hits, monkeypatch):
    import earnings_reaction as er
    monkeypatch.setattr(er, "pead_walk", lambda sym, df, **kw: _walk(1))
    before = list(hits)
    oh._attach_pead(hits, lambda s: _frame())
    assert list(hits) == before


def test_a_failing_walk_for_one_symbol_does_not_stop_the_rest(hits, monkeypatch):
    import earnings_reaction as er

    def _walk_fn(sym, df, **kw):
        if sym == "AAA":
            raise RuntimeError("calendar exploded")
        return _walk(1)

    monkeypatch.setattr(er, "pead_walk", _walk_fn)
    oh._attach_pead(hits, lambda s: _frame())
    assert "pead" not in hits["AAA"] and "pead" in hits["BBB"]


def test_a_failing_fetch_is_survivable(hits):
    def _fetch(sym):
        raise RuntimeError("no frame")

    oh._attach_pead(hits, _fetch)
    assert not any("pead" in h for h in hits.values())


def test_an_empty_frame_is_skipped_without_calling_the_walk(hits, monkeypatch):
    import earnings_reaction as er
    called: list[str] = []
    monkeypatch.setattr(er, "pead_walk",
                        lambda sym, df, **kw: called.append(sym) or _walk(1))
    oh._attach_pead(hits, lambda s: pd.DataFrame())
    assert called == [] and not any("pead" in h for h in hits.values())


def test_attach_can_be_switched_off(monkeypatch):
    """`attach_pead=False` exists so a caller that never renders the walk does not
    pay for it — and so a test of ranking is not perturbed by it."""
    monkeypatch.setattr(oh, "pipeline_scanners", lambda: [])
    called: list[int] = []
    monkeypatch.setattr(oh, "_attach_pead", lambda h, f: called.append(1))
    oh.run_scanner_pipeline([], lambda n: (lambda s: _frame()), attach_pead=False)
    assert called == []


# ── The renderer's two date shapes ───────────────────────────────────────────

def test_a_walk_survives_the_json_round_trip_the_archive_puts_it_through():
    """`daily_opportunity_cards` stores the frozen card as JSON, so `date` comes
    back as a string. The renderer formats the date only when it still IS one —
    this pins the shape it has to cope with rather than the rendering itself,
    which lives in dashboard_app and cannot be imported without Streamlit."""
    walk = _walk(1)
    assert isinstance(walk["events"][0]["date"], date)

    revived = json.loads(json.dumps(walk, default=str))
    d = revived["events"][0]["date"]
    assert isinstance(d, str)
    # What the renderer does with each shape.
    assert (f"{walk['events'][0]['date']:%Y-%m-%d}") == "2026-07-17"
    assert str(d)[:10] == "2026-07-17"


def test_a_none_leg_survives_the_round_trip_as_none_not_a_string():
    """An unfinished +20 window is None and must not come back as "None" — the
    difference between "still running" and a rendered value."""
    walk = _walk(1)
    walk["events"][0]["d20"] = None
    revived = json.loads(json.dumps(walk, default=str))
    assert revived["events"][0]["d20"] is None
