"""Registry-wide invariants for RISK and NEUTRAL scanners — B-105.

`test_support_breakdown_retired.py` already asserted that ONE bearish scanner
stays in `RISK_SCANNERS`, and said why in as many words: *"removing this from
RISK_SCANNERS would let it vote FOR a name"*. That test was right and it did not
generalise, so when `Liquidity Sweep Bear` shipped as `category: "Risk"` and was
never added to the tuple, nothing noticed. It spent its whole life casting a 0.5
BULLISH confluence vote — verified live before the fix:

    Liquidity Sweep Bear  cat=Risk  tier=unmeasured  weight=0.5
                          -> families=['Liquidity Sweep Bear'] points=0.5 riskflags=[]

The bug was never in the detector. Two lists that must agree had drifted, and
only one of them was tested. These tests are over the WHOLE registry, so the next
bearish scanner cannot arrive the same way.
"""
import pytest

import opportunity_hub as oh
import scanner_templates as sc


def _by_category(cat: str) -> set[str]:
    return {n for n, spec in sc.SCANNERS.items() if spec.get("category") == cat}


# ── the invariant that was missing ────────────────────────────────────────────
def test_every_risk_category_scanner_is_a_risk_scanner():
    """`category: "Risk"` is the registry saying which SIDE a detector reads.
    `RISK_SCANNERS` is what the ranking acts on. If they disagree, the ranking
    acts on the wrong side — silently, because a hit still looks like evidence."""
    missing = sorted(_by_category("Risk") - set(oh.RISK_SCANNERS))
    assert not missing, (
        "bearish scanners missing from RISK_SCANNERS, so they VOTE FOR a name "
        "instead of flagging it: " + ", ".join(missing))


def test_no_risk_scanner_is_registered_as_something_else():
    """The mirror. A name in the tuple that is not `category: "Risk"` means the
    two lists drifted the other way, and the Scanner Hub would colour a bullish
    detector as a risk flag."""
    mislabelled = sorted(n for n in oh.RISK_SCANNERS
                         if n in sc.SCANNERS
                         and sc.SCANNERS[n].get("category") != "Risk")
    assert not mislabelled, (
        "in RISK_SCANNERS but not category 'Risk': " + ", ".join(mislabelled))


def test_every_neutral_category_scanner_is_a_neutral_scanner():
    """Same class of drift, other tier (B-101). A bilateral card that fell out of
    NEUTRAL_SCANNERS would start voting for a direction it does not have."""
    missing = sorted(_by_category("Neutral") - set(oh.NEUTRAL_SCANNERS))
    assert not missing, (
        "bilateral scanners missing from NEUTRAL_SCANNERS, so a coil would vote: "
        + ", ".join(missing))


# ── what the invariant is protecting ──────────────────────────────────────────
@pytest.mark.parametrize("name", sorted(_by_category("Risk")))
def test_no_bearish_scanner_carries_confluence_weight(name):
    assert oh.scanner_tier(name) == "risk"
    assert oh.scanner_weight(name) == 0.0


@pytest.mark.parametrize("name", sorted(_by_category("Risk")))
def test_a_bearish_hit_is_a_flag_and_never_a_vote(name):
    """The whole point, stated per scanner: a bearish hit must add nothing to the
    confluence count and must appear in the risk list instead."""
    families, points, risk = oh.tally_evidence([name])
    assert families == [] and points == 0.0
    assert risk == [name]


def test_a_bearish_hit_does_not_change_a_real_confluence():
    """Adding a bearish flag to a name that already has bullish evidence must
    leave the families and the points exactly as they were — the flag is
    surfaced separately, and it must not quietly inflate what it warns about."""
    base = oh.tally_evidence(["Falling Wedge", "Pullback Entry"])
    with_flag = oh.tally_evidence(["Falling Wedge", "Pullback Entry",
                                   "Liquidity Sweep Bear"])
    assert with_flag[0] == base[0]          # same families
    assert with_flag[1] == base[1]          # same points
    assert with_flag[2] == ["Liquidity Sweep Bear"]


def test_the_bull_and_bear_sweeps_are_on_opposite_sides():
    """The pair that exposed this. Same detector family, opposite sides, and the
    registry must treat them as opposites rather than as two votes."""
    bull = oh.tally_evidence(["Liquidity Sweep"])
    bear = oh.tally_evidence(["Liquidity Sweep Bear"])
    assert bull[1] > 0 and bull[2] == []
    assert bear[1] == 0 and bear[2] == ["Liquidity Sweep Bear"]
