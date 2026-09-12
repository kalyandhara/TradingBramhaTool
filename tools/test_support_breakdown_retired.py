"""Pins the 2026-09-11 retirement of `Support Breakdown`.

    py -3 -m pytest tools/test_support_breakdown_retired.py -q

It is a RISK flag that B-19 measured at **+0.47% @20d / +1.22% @60d** on 2,880
signals: names it warned about went UP on average. It never voted — risk scanners
cannot — but it was DISPLAYED as a bearish warning on shortlisted names, and a
warning with no support steers a reader away from names that outperformed.

Retired the way B-44r retired GEX: **removed as a decision input, kept as a view.**
It stays registered, runnable in the Scanner Hub and backtestable. What changed is
that the pipeline no longer runs it, so no flag is shown.

These tests exist because a retirement expressed as one string in one tuple is
exactly the kind of thing a later refactor undoes without noticing.
"""

from __future__ import annotations

import opportunity_hub as oh
import scanner_templates as sc

NAME = "Support Breakdown"


def test_the_pipeline_no_longer_runs_it():
    """The retirement itself. If this fails, the bearish flag is back on cards."""
    assert NAME in oh.PIPELINE_EXCLUDED


def test_it_is_absent_from_the_pipeline_scanner_list():
    """Belt and braces: the exclusion has to actually reach the list builder."""
    runnable = [n for n in sc.SCANNERS if n not in oh.PIPELINE_EXCLUDED]
    assert NAME not in runnable


def test_it_is_still_registered_and_runnable():
    """Retired is NOT deleted -- the desk's standing rule, and the GEX precedent.

    The measurement rules out the WARNING, not the view: the scanner stays in the
    registry so it can still be run by hand and re-measured.
    """
    assert NAME in sc.SCANNERS
    assert callable(sc.SCANNERS[NAME]["fn"])


def test_it_still_colours_as_a_risk_entry():
    """It stays in RISK_SCANNERS on purpose.

    Dropping it there would make `scanner_tier()` report "unmeasured", which is the
    opposite of what happened to it -- it was measured, and that is why it retired.
    """
    assert NAME in oh.RISK_SCANNERS
    assert oh.scanner_tier(NAME) == "risk"


def test_it_can_never_become_a_positive_vote():
    """The failure mode of a careless un-retirement: removing it from RISK_SCANNERS
    to 'clean up' would turn a measured-bearish-flag-that-isn't into a BULLISH
    confluence vote, because unmapped non-risk scanners count as a family of one."""
    assert NAME in oh.RISK_SCANNERS, (
        "removing this from RISK_SCANNERS would let it vote FOR a name")


def test_the_description_carries_the_measurement_and_the_retirement():
    d = sc.SCANNERS[NAME]["description"]
    assert "RETIRED" in d
    assert "+0.47%" in d and "+1.22%" in d
    assert "PIPELINE_EXCLUDED" in d
    # The evidence is [UNSTABLE]; the description must not overclaim a significant
    # inversion the way B-44r's GEX result genuinely was.
    assert "UNSTABLE" in d
