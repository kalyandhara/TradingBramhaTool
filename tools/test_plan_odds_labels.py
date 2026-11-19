"""plan_odds_labels — B-183c card lines follow the pre-registered rule."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import plan_odds_labels as pol
import scanner_templates as st

RESULT = Path(__file__).resolve().parent / "cache" / "plan_baseline_robust_study.json"


def test_every_label_names_a_registered_scanner():
    assert set(pol.PLAN_ODDS_D) <= set(st.SCANNERS)


def test_lines_say_it_is_about_the_levels():
    up, down = pol.card_lines("Flag & Pole"), pol.card_lines("Support Breakdown")
    assert len(up) == len(down) == 1
    assert "+0.37R" in up[0] and "levels, not the signal" in up[0]
    assert down[0].startswith("⚠") and "0.33R below" in down[0]


def test_unlabelled_scanners_get_nothing():
    assert pol.card_lines("Rounding Bottom") == []     # BEATS in B-183, AT in B-183c
    assert pol.card_lines("RSI-Fibo Hidden Divergence") == []   # THIN
    assert pol.card_lines("no such scanner") == []


def test_labels_match_the_preregistered_rule_on_the_stored_result():
    if not RESULT.exists():
        pytest.skip("B-183c result not on this machine (tools/cache is ignored)")
    res = json.loads(RESULT.read_text(encoding="utf-8"))
    assert res["placebo_failed"] is False
    assert abs(res["placebo_gate"]["mean_d"]) <= 0.05
    want = {k: v["mean_d"] for k, v in res["scanners"].items()
            if v["verdict"] in ("BEATS BASELINE", "BELOW BASELINE")
            and not v["within_placebo_noise"]}
    assert set(pol.PLAN_ODDS_D) == set(want)
    for name, d in want.items():
        assert pol.PLAN_ODDS_D[name] == pytest.approx(d, abs=0.006)
