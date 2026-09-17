"""Tests for B-42r's agreement count, offline.

This study makes no forward-return claim, so there is no p-value to protect. What
can go wrong is the counting and the reading of it:

  * the comparison must run BOTH settings on the SAME frame — comparing two
    different windows would manufacture disagreement;
  * the verdict thresholds must be applied as written, because the whole point of
    stating them in advance is that the reading is not invented from the number
    that came back.
"""
import numpy as np
import pandas as pd

import pivot_len_agreement as pl


def _frame(n=400, seed=0):
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c,
                         "volume": np.full(n, 1e6)})


def test_compare_runs_both_settings_on_one_frame():
    r = pl.compare(_frame())
    assert r is not None
    assert r["a"]["params"]["pivot_len"] == pl.SCANNER_PL
    assert r["b"]["params"]["pivot_len"] == pl.CHART_PL


def test_compare_reports_a_same_flag_for_every_field():
    r = pl.compare(_frame())
    for f in pl.FIELDS:
        assert f"same_{f}" in r
        assert isinstance(r[f"same_{f}"], bool)


def test_identical_settings_agree_on_everything():
    # The null case: if both sides use the same pivot_len, every field must match.
    # A failure here would mean the comparison itself introduces disagreement.
    r = pl.compare(_frame(), a=10, b=10)
    assert all(r[f"same_{f}"] for f in pl.FIELDS)
    assert r["zone_pct_gap"] == 0


def test_compare_returns_none_on_an_unusable_frame():
    assert pl.compare(pd.DataFrame({"open": [], "high": [], "low": [],
                                    "close": [], "volume": []})) is None


def _summary(state_agree_pct, n=199):
    same = {f: 50.0 for f in pl.FIELDS}
    same["state"] = state_agree_pct
    return {"n": n, "same": same, "pairs": {}, "zone_gap": [],
            "zone_gap_median": 10.0}


def test_high_agreement_reads_as_cosmetic():
    v, _ = pl.verdict(_summary(95.0))
    assert v == "COSMETIC"


def test_middling_agreement_reads_as_real_but_narrow():
    v, _ = pl.verdict(_summary(80.0))
    assert v == "REAL BUT NARROW"


def test_low_agreement_reads_as_two_different_readings():
    v, why = pl.verdict(_summary(29.6))
    assert v == "TWO DIFFERENT READINGS"
    assert "what structure MEANS" in why


def test_a_thin_universe_is_inconclusive():
    v, _ = pl.verdict(_summary(29.6, n=10))
    assert v == "INCONCLUSIVE"


def test_summarise_counts_state_pairs():
    rows = [{"a": {"state": "UPTREND"}, "b": {"state": "RANGE"},
             "zone_pct_gap": 5.0, **{f"same_{f}": False for f in pl.FIELDS}},
            {"a": {"state": "UPTREND"}, "b": {"state": "UPTREND"},
             "zone_pct_gap": 1.0, **{f"same_{f}": True for f in pl.FIELDS}}]
    s = pl.summarise(rows)
    assert s["n"] == 2
    assert s["same"]["state"] == 50.0
    assert s["pairs"][("UPTREND", "RANGE")] == 1
