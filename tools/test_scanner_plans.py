"""Tests for the trade-plan census (PR-2), offline — and the ratchet on it.

Two jobs here, and the second is the one with teeth.

**The census must not lie in either direction.** A scanner that never fired has
not been shown to lack a plan; collapsing UNSEEN into NONE is the FR-4 mistake of
letting NOT_CHECKED read as a verdict. And a hit carrying `stop: None` does not
carry a stop, because `backtest._simulate_plan` would reject it.

**The ratchet.** `backtest._simulate_plan` walks entry -> stop/target, so a
scanner with no plan cannot be scored on realised R at all. Plan coverage is
therefore a measurement capability, and the count may go UP freely and may not go
DOWN without someone editing this file and saying why. That is the B-87 shape,
applied to a different kind of debt.
"""
import json

import pytest

import scanner_plans as sp


# ── the census semantics ──────────────────────────────────────────────────────

def test_a_hit_needs_all_three_fields():
    assert sp.has_plan({"entry": 100, "stop": 95, "target": 110})
    assert not sp.has_plan({"entry": 100, "stop": 95})
    assert not sp.has_plan({"entry": 100, "target": 110})
    assert not sp.has_plan({"stop": 95, "target": 110})


def test_a_present_but_none_field_is_not_a_plan():
    # The harness would reject it, so counting it would overstate what can be
    # scored -- which is the whole quantity this census exists to report.
    assert not sp.has_plan({"entry": 100, "stop": None, "target": 110})


def test_a_nan_field_is_not_a_plan():
    assert not sp.has_plan({"entry": 100, "stop": float("nan"), "target": 110})


def test_a_non_numeric_field_is_not_a_plan():
    assert not sp.has_plan({"entry": 100, "stop": "below the low", "target": 110})


def test_a_non_dict_hit_is_not_a_plan():
    assert not sp.has_plan(None)
    assert not sp.has_plan(False)


def test_classification_has_four_states():
    assert sp.classify({"fired": 10, "with_plan": 10}) == sp.FULL
    assert sp.classify({"fired": 10, "with_plan": 4}) == sp.PARTIAL
    assert sp.classify({"fired": 10, "with_plan": 0}) == sp.NONE
    assert sp.classify({"fired": 0, "with_plan": 0}) == sp.UNSEEN


def test_a_scanner_that_never_fired_is_unseen_not_none():
    """The distinction the FR-4 work exists to protect.

    UNSEEN says "not shown"; NONE says "shown to lack one". Collapsing the first
    into the second would report absence of evidence as evidence of absence, and
    would do it about 46 scanners at once.
    """
    assert sp.classify({"fired": 0, "with_plan": 0}) != sp.NONE


def test_partial_is_its_own_state():
    # A plan you get on some hits and not others is harder to use than one you
    # never get, so it must not be rounded to either neighbour.
    assert sp.classify({"fired": 10, "with_plan": 9}) == sp.PARTIAL
    assert sp.classify({"fired": 10, "with_plan": 1}) == sp.PARTIAL


def _result(**counts):
    return {"symbols_used": 5, "stride": 5,
            "scanners": {n: {"fired": f, "with_plan": w,
                             "fields": {k: f for k in sp.PLAN_FIELDS}}
                         for n, (f, w) in counts.items()}}


def test_summarise_partitions_every_scanner_exactly_once():
    res = _result(A=(10, 10), B=(10, 5), C=(10, 0), D=(0, 0))
    s = sp.summarise(res)
    assert s["total"] == 4
    assert s["counts"] == {sp.FULL: 1, sp.PARTIAL: 1, sp.NONE: 1, sp.UNSEEN: 1}
    assert s["observed"] == 3          # UNSEEN is not an observation


def test_rows_sort_the_gaps_to_the_top():
    res = _result(Good=(10, 10), Missing=(10, 0), Half=(10, 5), Never=(0, 0))
    order = [r["Plan"] for r in sp.rows(res)]
    assert order[0] == sp.NONE
    assert order[-1] == sp.FULL


def test_rows_report_no_percentage_for_an_unseen_scanner():
    r = next(r for r in sp.rows(_result(Never=(0, 0))) if r["Scanner"] == "Never")
    assert r["Plan %"] is None          # not 0.0 -- nothing was measured


def test_load_returns_none_when_there_is_no_cache(tmp_path):
    assert sp.load(tmp_path / "absent.json") is None


def test_save_and_load_round_trip(tmp_path):
    res = _result(A=(3, 3))
    p = sp.save(res, tmp_path / "c.json")
    assert json.loads(p.read_text(encoding="utf-8")) == sp.load(p)


def test_probe_hands_scanners_only_past_bars():
    """Point-in-time: a scanner must never see a bar after the one being tested.

    A scanner that peeked would look better on every downstream measurement, so
    this is checked rather than trusted.
    """
    import numpy as np
    import pandas as pd
    seen = []

    def spy(df):
        seen.append(len(df))
        return None

    n = sp.WARMUP + 60
    c = np.linspace(100, 120, n)
    frame = pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c,
                          "volume": np.full(n, 1e6)})
    sp.probe(["X"], lambda s: frame, scanners={"spy": {"fn": spy}}, stride=10)
    assert seen, "the spy scanner was never called"
    assert max(seen) <= n - 1, "a scanner was handed the final bar or beyond"
    assert min(seen) == sp.WARMUP + 1


def test_probe_survives_a_scanner_that_raises():
    import numpy as np
    import pandas as pd

    def boom(df):
        raise RuntimeError("bad scanner")

    n = sp.WARMUP + 40
    c = np.linspace(100, 110, n)
    frame = pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c,
                          "volume": np.full(n, 1e6)})
    res = sp.probe(["X"], lambda s: frame, scanners={"boom": {"fn": boom}}, stride=10)
    assert res["scanners"]["boom"]["fired"] == 0


def test_probe_skips_a_symbol_whose_fetch_fails():
    def dead(sym):
        raise RuntimeError("no data")

    res = sp.probe(["X"], dead, scanners={"a": {"fn": lambda df: None}})
    assert res["symbols_used"] == 0


# ── the ratchet ───────────────────────────────────────────────────────────────

#: Measured 2026-09-17 by `scanner_plans.py --probe`. This may go UP freely and
#: may not go DOWN without editing this line and saying why.
#:
#: It is a DEBT, not a target: most registered scanners hand the reader a name
#: and no levels, and `_simulate_plan` cannot score any of them on realised R.
#:
#: 14 -> 16 on 2026-09-17 when PR-3 added `Flag & Pole` and `Inverted Flag &
#: Pole`, both FULL. That is the ratchet working in the direction it is supposed
#: to: new detectors arrive with a plan, and the floor rises behind them.
MIN_FULL_PLAN_SCANNERS = 16


def _census():
    res = sp.load()
    if res is None:
        pytest.skip("no plan census cached — run tools/scanner_plans.py --probe")
    return res


def test_the_number_of_full_plan_scanners_does_not_fall():
    s = sp.summarise(_census())
    n = s["counts"][sp.FULL]
    assert n >= MIN_FULL_PLAN_SCANNERS, (
        f"only {n} scanners emit a full entry/stop/target, down from the "
        f"{MIN_FULL_PLAN_SCANNERS} recorded on 2026-09-17. A scanner lost its "
        f"plan, or a new one shipped without one.")


def test_the_census_covers_every_registered_scanner():
    """A scanner added after the last probe is invisible to the ratchet.

    Without this, shipping a planless scanner would not lower the FULL count —
    it simply would not appear — and the ratchet would pass while the debt grew.
    """
    import scanner_templates as sc
    res = _census()
    missing = sorted(set(sc.SCANNERS) - set(res["scanners"]))
    assert not missing, (
        "scanners missing from the plan census: " + ", ".join(missing) +
        " — re-run tools/scanner_plans.py --probe")
