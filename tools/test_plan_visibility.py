"""A plan the measurement harness cannot see is not a plan — B-64r2.

`backtest.py` reads a hit's trade plan from `hit["entry"/"stop"/"target"]`
(backtest.py:354) and `scanner_plans.has_plan` checks the same three keys. A
scanner that tucks its plan inside `geometry` hands a complete, correct
entry/stop/target to the chart card and to a human reading it, and hands the
R-simulator nothing.

That is not a formatting preference. The registry's whole tier system —
`measured` / `weak` / `unmeasured` — is downstream of whether the harness can
score a scanner at all, so an invisible plan is the difference between a
scanner that can earn a measurement and one that is permanently stuck at
`unmeasured`.

Found because `Double Bottom` shipped with the same shape, which made the plan
census read it as planless. `Rounding Bottom` had been carrying an invisible
plan on 39/39 hits since it was written.

The general test below is the point of the file: it asserts the RULE rather
than the three instances, so the next detector that returns a `geometry` payload
cannot reintroduce the gap quietly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import scanner_plans as sp
import scanner_templates as S

PLAN = ("entry", "stop", "target")


def _frames():
    """Shapes chosen to fire the pattern scanners, not random walks — a random
    walk fires almost none of them and would make this file vacuously green."""
    out = []
    # A saucer that actually clears `scan_rounding_bottom`'s gates: a 28%
    # decline (inside its 12-40% band), a shallow rounded trough, and an
    # orderly recovery back through the rim. Tuned by search rather than by
    # eye — an untuned saucer shape simply does not fire, and a skipped test
    # guards nothing.
    px = (list(np.linspace(100, 72, 28))
          + list(72 + 1.5 * np.sin(np.linspace(0, np.pi, 12)))
          + list(np.linspace(72, 104, 30)))
    px = [100.0] * (95 - len(px)) + px
    out.append(np.array(px, float))
    # A double bottom: decline, low, rally to a neckline, low, break.
    px = (list(np.linspace(100, 72, 60)) + list(np.linspace(72, 70, 10))
          + list(np.linspace(70, 80, 20)) + list(np.linspace(80, 70, 20))
          + list(np.linspace(70, 84, 14)) + [84.0, 84.5, 85.0])
    out.append(np.array(px, float))
    # A coil: uptrend into three tightening ranges.
    base = list(np.linspace(60, 100, 120))
    coil = []
    for amp in (6.0, 3.0, 1.2):
        coil += list(100 + amp * np.sin(np.linspace(0, 2 * np.pi, 10)))
    out.append(np.array(base + coil, float))
    return [pd.DataFrame({"open": c, "high": c * 1.012, "low": c * 0.988,
                          "close": c, "volume": np.full(len(c), 1e6)})
            for c in out]


def _hits():
    """(scanner_name, hit) for every scanner that fires on the fixtures."""
    found = []
    for name, meta in S.SCANNERS.items():
        for df in _frames():
            for cut in (len(df), len(df) - 12):
                try:
                    h = meta["fn"](df.iloc[:cut])
                except Exception:
                    continue
                if isinstance(h, dict):
                    found.append((name, h))
    return found


# ── the rule ──────────────────────────────────────────────────────────────────

def test_no_scanner_hides_a_complete_plan_inside_its_geometry():
    """If `geometry` carries all three plan fields, the top level must too.

    This is the guard. A new detector that returns a geometry payload gets this
    for free, and a regression names the scanner rather than showing up months
    later as an unexplained 0/N in the plan census.
    """
    offenders = []
    for name, hit in _hits():
        g = hit.get("geometry")
        if not isinstance(g, dict):
            continue
        if all(g.get(k) is not None for k in PLAN) and not sp.has_plan(hit):
            offenders.append(name)
    assert not offenders, (
        "these scanners emit a plan the R-simulator cannot see: "
        + ", ".join(sorted(set(offenders))))


def test_a_surfaced_plan_agrees_with_the_geometry_it_came_from():
    """Two copies of one plan must not drift — the chart card reads geometry and
    the harness reads the top level, and they describe the same trade."""
    for name, hit in _hits():
        g = hit.get("geometry")
        if not isinstance(g, dict) or not sp.has_plan(hit):
            continue
        for k in PLAN:
            if g.get(k) is not None:
                assert hit[k] == g[k], f"{name}: {k} disagrees with geometry"


# ── the three instances, named so a failure is legible ───────────────────────

def _first_hit(fn):
    for df in _frames():
        h = fn(df)
        if h:
            return h
    return None


def test_rounding_bottom_emits_a_visible_plan():
    hit = _first_hit(S.scan_rounding_bottom)
    if hit is None:
        pytest.skip("no saucer in the fixtures on this build")
    assert sp.has_plan(hit)


def test_double_bottom_emits_a_visible_plan():
    hit = _first_hit(S.scan_double_bottom)
    if hit is None:
        pytest.skip("no double bottom in the fixtures on this build")
    assert sp.has_plan(hit)


# ── VCP: the gates WERE replaced, on request, and it cost a measurement ──────

def test_vcp_delegates_to_the_strict_detector():
    """`scan_vcp` no longer owns a hit rule. It fires exactly when
    `detect_vcp_geometry` sees a base — one detector, so the Scanner Hub card
    and the /api/vcp chart overlay can no longer disagree about a name.

    The coarse three-window range test it used to carry is gone, not bypassed.
    """
    import inspect
    src = inspect.getsource(S.scan_vcp)
    assert "detect_vcp_geometry(df)" in src
    for gone in ("if not (r2 > r1 > r0):", "if contraction < 20:", "_range_pct"):
        assert gone not in src, f"the old coarse gate {gone!r} is still deciding hits"

    for df in _frames():
        assert (S.scan_vcp(df) is None) == (S.detect_vcp_geometry(df) is None)


def test_vcp_lost_its_measured_tier_with_its_old_detector():
    """B-19 measured the three-window test. That detector no longer exists, so
    the tier it earned does not transfer.

    This is the test that would fail if someone re-added `VCP Coiling` to
    MEASURED_WEAK_SCANNERS without re-running the measurement — which would be
    the cheap move and the wrong one.
    """
    import opportunity_hub as oh
    assert "VCP Coiling" not in oh.MEASURED_WEAK_SCANNERS
    assert oh.scanner_tier("VCP Coiling") == "unmeasured"
    assert "NOT MEASURED" in S.SCANNERS["VCP Coiling"]["description"]


def test_the_swap_raised_vcps_confluence_weight():
    """Pinned because it is counter-intuitive and easy to lose track of:
    replacing a measured detector with an unmeasured one makes it vote MORE.
    `unmeasured` is 0.5 ("plausible, unproven"), `weak` was 0.25 ("measured, and
    it was not good"). Not a bug — but it should not go unnoticed either."""
    import opportunity_hub as oh
    assert oh.scanner_weight("VCP Coiling") == oh.WEIGHT_UNMEASURED
    assert oh.WEIGHT_UNMEASURED > oh.WEIGHT_WEAK


def test_vcp_now_emits_a_plan_on_every_hit():
    """It reported NONE in the plan census while the coarse gates carried no
    plan at all. Delegating gives every hit a pivot-anchored entry/stop/target."""
    fired = 0
    for df in _frames():
        hit = S.scan_vcp(df)
        if hit is None:
            continue
        fired += 1
        assert sp.has_plan(hit)
    if not fired:
        pytest.skip("no coil in the fixtures on this build")


def test_vcp_scores_with_the_shared_base_quality_not_a_new_definition():
    """One id, one definition. `scan_base_formation` already scores a base
    0-100; a second VCP-only scoring function would be the drift `columns.py`
    and the scanner registry both exist to stop."""
    import inspect
    src = inspect.getsource(S.scan_vcp)
    assert "_base_quality(" in src
    for df in _frames():
        hit = S.scan_vcp(df)
        if hit:
            assert 0.0 <= hit["score"] <= 100.0


def test_vcp_still_returns_its_card_fields():
    """The swap must not disturb what the Scanner Hub already renders."""
    for df in _frames():
        hit = S.scan_vcp(df)
        if hit is None:
            continue
        assert hit["pattern_type"] == "VCP Coiling"
        assert "score" in hit and "reasons" in hit and "tags" in hit
