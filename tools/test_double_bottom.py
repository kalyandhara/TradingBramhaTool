"""Tests for `scan_double_bottom` — the AGPro Reversal Pattern Quality Scanner port.

The scanner is NOT measured and claims no edge, so nothing here asserts that a
double bottom works. What is pinned instead is that the detector reads the shape
the spec describes and refuses the shapes it rejects — every gate the source
names (equality, width, pullback depth, ATR break buffer), and the two places
the first build got it wrong:

  * a slow grind straight up off the break was labelled "Retest hold", which
    swapped the pattern-low stop for the much tighter neckline stop on a trade
    that never pulled back to earn it;
  * a break that had already run 6% past the neckline still called itself a BUY,
    against a measured-move target that extension had already spent.

Also pinned: quality and follow-through stay SEPARATE numbers. The source page's
own warning is that a textbook A-grade shape can sit on a 30% real follow-through
rate for that name, and folding one into the other would destroy exactly the
disagreement that makes it worth reading.
"""
import numpy as np
import pandas as pd
import pytest

import scanner_templates as S


# ──────────────────────────────────────────────────────────────────────────────
# Frame builders. Bars carry a symmetric 1% wick so a "low" exists that is not
# the close — the ATR buffer and the retest band are both about lows and highs,
# and a close-only frame cannot exercise either.
# ──────────────────────────────────────────────────────────────────────────────

def _bars(closes, vols=None, wick=0.01):
    c = np.asarray(closes, dtype=float)
    v = (np.asarray(vols, dtype=float) if vols is not None
         else np.full(len(c), 1_000_000.0))
    return pd.DataFrame({"open": c, "high": c * (1 + wick),
                         "low": c * (1 - wick), "close": c, "volume": v})


def _double_bottom(left=70.0, right=70.0, neck=80.0, *, lead=60, leg=20,
                   start=100.0, tail=None, run=14, peak=84.0, wick=0.01):
    """A textbook double bottom: decline, low, rally to the neckline, low, break.

    `tail` overrides the post-break path, which is how the retest and extension
    cases are built from the same shape.
    """
    px = list(np.linspace(start, left + 2, lead))
    px += list(np.linspace(left + 2, left, 10))       # left bottom
    px += list(np.linspace(left, neck, leg))          # rally to the neckline
    px += list(np.linspace(neck, right, leg))         # back down to the right
    px += list(np.linspace(right, peak, run))         # the breakout leg
    px += list(tail if tail is not None else [peak, peak + 0.5, peak + 1.0])
    # Volume contracts through the base and expands on the break — the
    # two-sided signature the volume component scores.
    vol = ([2e6] * lead + [1.5e6] * (10 + leg) + [8e5] * leg
           + [2.5e6] * (run + len(tail if tail is not None else [0, 0, 0])))
    return _bars(px, vol[:len(px)], wick=wick)


def _hit(df):
    return S.scan_double_bottom(df)


def _geo(df):
    r = _hit(df)
    assert r is not None, "expected a double bottom hit"
    return r["geometry"]


# ── the shape is found, and its geometry is real ──────────────────────────────

def test_a_textbook_double_bottom_is_detected():
    g = _geo(_double_bottom())
    assert g["neckline"] > g["left_low"]
    assert g["neckline"] > g["right_low"]
    assert g["eq_pct"] <= S.DB_EQ_TOL_PCT
    assert g["pullback_pct"] >= S.DB_MIN_PULLBACK_PCT


def test_the_pivots_it_reports_are_real_window_extremes():
    """The bar indices are what a chart would draw; if they are not true pivots
    the drawing is fiction."""
    df = _double_bottom()
    g = _geo(df)
    pl = S.DB_PIVOT_LEN
    for key in ("left_bar_idx", "right_bar_idx"):
        i = g[key]
        assert df["low"].iloc[i] == df["low"].iloc[i - pl:i + pl + 1].min()
    nk = g["neck_bar_idx"]
    assert df["high"].iloc[nk] == df["high"].iloc[nk - pl:nk + pl + 1].max()


def test_bar_indices_are_absolute_into_the_callers_frame():
    """The detector works on a trailing window but must report indices into the
    frame it was handed — `scan_rounding_bottom`'s geometry convention, and what
    the chart endpoint converts to timestamps."""
    df = _double_bottom()
    g = _geo(df)
    for key in ("left_bar_idx", "neck_bar_idx", "right_bar_idx", "breakout_bar_idx"):
        assert 0 <= g[key] < len(df)
    assert g["left_bar_idx"] < g["neck_bar_idx"] < g["right_bar_idx"] < g["breakout_bar_idx"]


# ── the gates the spec names ──────────────────────────────────────────────────

def test_bottoms_outside_the_equality_tolerance_are_rejected():
    """1.4% is the source's number, and 'roughly a double bottom' is not one."""
    assert _hit(_double_bottom(left=70.0, right=64.0)) is None


def _cands(df, **kw):
    kw = {"pivot_len": S.DB_PIVOT_LEN, "eq_tol_pct": S.DB_EQ_TOL_PCT,
          "min_pullback_pct": S.DB_MIN_PULLBACK_PCT, "min_bars": S.DB_MIN_BARS,
          "max_bars": S.DB_MAX_BARS, "atr_buffer": S.DB_ATR_BUFFER, **kw}
    return S._db_candidates(df.tail(260).reset_index(drop=True), **kw)


def test_a_neckline_too_shallow_to_matter_is_rejected():
    """A flat, low-conviction wiggle is not a reversal structure.

    Asserted by MOVING the gate rather than by asserting a miss: the shallow
    pair is found when the floor is dropped to 1% and gone at the spec's 2%, so
    this pins the gate doing the work rather than the fixture happening to be
    quiet. (A whole-frame `is None` would not isolate it — the builder's decline
    leaves deeper pivots elsewhere that legitimately pair.)"""
    # wick=0 so the pullback is the neckline-to-bottom gap and nothing else:
    # a symmetric 1% wick alone puts ~2% between a high and a low, which would
    # lift any pair over the floor and make the fixture untestable.
    df = _double_bottom(left=79.0, right=79.0, neck=80.0, wick=0.0)
    shallow = [c for c in _cands(df, min_pullback_pct=1.0)
               if 1.0 <= c["pullback_pct"] < S.DB_MIN_PULLBACK_PCT]
    assert shallow, "fixture should contain a shallow pair to reject"
    assert all(c["pullback_pct"] >= S.DB_MIN_PULLBACK_PCT for c in _cands(df))


def test_every_reported_pattern_clears_every_gate():
    """One assertion covering the whole gate set, so a future loosening of any
    single threshold cannot slip through on the strength of the others."""
    g = _geo(_double_bottom())
    assert g["eq_pct"] <= S.DB_EQ_TOL_PCT
    assert g["pullback_pct"] >= S.DB_MIN_PULLBACK_PCT
    assert S.DB_MIN_BARS <= g["width_bars"] <= S.DB_MAX_BARS
    assert g["atrs_past"] >= S.DB_ATR_BUFFER


def test_a_pattern_narrower_than_the_width_floor_is_rejected():
    assert _hit(_double_bottom(leg=2)) is None


def test_touching_the_neckline_is_not_a_break():
    """The ATR buffer is the whole reason the spec quotes an ATR multiple: a
    close that merely reaches the neckline has not confirmed anything."""
    df = _double_bottom(neck=80.0, peak=80.05, tail=[80.05, 80.0, 80.02])
    assert _hit(df) is None


def test_giving_the_neckline_back_is_not_a_live_setup():
    df = _double_bottom(tail=[84.0, 80.0, 76.0, 74.0])
    assert _hit(df) is None


def test_a_frame_too_short_for_two_confirmed_pivots_returns_none():
    assert _hit(_bars(list(np.linspace(70, 80, 40)))) is None


def test_a_frame_with_no_volume_column_returns_none():
    df = _double_bottom().drop(columns=["volume"])
    assert S.scan_double_bottom(df) is None


# ── negative controls ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("series,label", [
    (np.linspace(50, 120, 200), "pure uptrend"),
    (np.linspace(120, 50, 200), "pure downtrend"),
    (np.full(200, 75.0), "flat line"),
])
def test_shapes_that_are_not_double_bottoms_do_not_fire(series, label):
    assert _hit(_bars(list(series))) is None, label


def test_a_random_walk_does_not_routinely_fire():
    """Not a claim about edge — a claim about selectivity. A detector that hits
    on noise is describing noise."""
    fired = 0
    for seed in range(30):
        walk = 70 + np.random.RandomState(seed).randn(220).cumsum() * 0.4
        if _hit(_bars(list(walk))) is not None:
            fired += 1
    assert fired <= 3, f"{fired}/30 random walks fired"


# ── the retest regression ─────────────────────────────────────────────────────

def test_a_grind_straight_up_off_the_break_is_not_a_retest():
    """The bug this pins: checking only 'did a low come back within 1%' marks the
    early bars of an uninterrupted rally as a retest, because they are still
    inside the band. Price must LEAVE the neckline before it can return to it."""
    g = _geo(_double_bottom(neck=80.0, peak=84.0,
                            tail=[84.5, 85.0, 85.5, 86.0, 86.5]))
    assert g["state"] == "Confirmed"


def test_a_real_pullback_to_the_neckline_is_a_retest_hold():
    g = _geo(_double_bottom(neck=80.0, peak=83.0,
                            tail=[83.0, 82.0, 81.2, 80.9, 81.5, 82.3, 83.1]))
    assert g["state"] == "Retest hold"


def test_the_retest_stop_is_tighter_than_the_pattern_low_stop():
    """The point of distinguishing the states. A held retest invalidates at the
    neckline; a fresh break has nothing above the pattern low to lean on."""
    retest = _geo(_double_bottom(neck=80.0, peak=83.0,
                                 tail=[83.0, 82.0, 81.2, 80.9, 81.5, 82.3, 83.1]))
    assert retest["state"] == "Retest hold"
    assert retest["stop"] > retest["right_low"]


# ── the extension guard ───────────────────────────────────────────────────────

def test_a_break_that_has_already_run_does_not_call_itself_a_buy():
    """A measured-move target is fixed by the pattern's own height, so every bar
    of extension spends the reward without touching the risk. Same 'a plan with
    no room is not a plan' rule MIN_SWEEP_RR exists for."""
    g = _geo(_double_bottom(neck=80.0, peak=84.0,
                            tail=[84.5, 85.0, 85.5, 86.0, 86.5]))
    assert g["risk_reward"] < S.MIN_SWEEP_RR
    assert g["verdict"] == "EXTENDED (no room)"
    assert g["extended_pct"] > 0


def test_the_pattern_is_still_reported_when_it_is_extended():
    """Extended is a verdict, not a filter — the shape is real and worth seeing."""
    r = _hit(_double_bottom(neck=80.0, peak=84.0,
                            tail=[84.5, 85.0, 85.5, 86.0, 86.5]))
    assert r is not None and r["pattern_type"] == "Double Bottom"


# ── the trade plan ────────────────────────────────────────────────────────────

def test_the_target_is_the_measured_move_off_the_neckline():
    g = _geo(_double_bottom())
    height = g["neckline"] - min(g["left_low"], g["right_low"])
    assert g["target"] == pytest.approx(g["neckline"] + height, abs=0.02)


def test_the_stop_sits_below_the_level_that_makes_the_pattern_wrong():
    g = _geo(_double_bottom())
    if g["state"] != "Retest hold":
        assert g["stop"] < min(g["left_low"], g["right_low"])


def test_the_plan_is_internally_consistent():
    g = _geo(_double_bottom())
    assert g["stop"] < g["entry"] < g["target"]


# ── quality score ─────────────────────────────────────────────────────────────

def test_the_weights_are_the_sources_and_sum_to_one():
    assert S.DB_WEIGHTS == {"structure": 0.28, "depth": 0.22, "volume": 0.18,
                            "breakout": 0.17, "context": 0.15}
    assert sum(S.DB_WEIGHTS.values()) == pytest.approx(1.0)


def test_quality_is_bounded_and_carries_its_parts():
    g = _geo(_double_bottom())
    assert 1.0 <= g["quality"] <= 10.0
    assert set(g["parts"]) == set(S.DB_WEIGHTS)
    assert all(0.0 <= v <= 10.0 for v in g["parts"].values())


def test_the_grade_follows_the_quality_number():
    g = _geo(_double_bottom())
    q, grade = g["quality"], g["grade"]
    expected = ("S" if q >= 9 else "A+" if q >= 8 else "A" if q >= 7
                else "B" if q >= 6 else "C" if q >= 4.5 else "D")
    assert grade == expected


def test_the_hub_score_is_the_quality_number_on_a_hundred_point_scale():
    r = _hit(_double_bottom())
    assert r["score"] == int(round(r["geometry"]["quality"] * 10))


def test_a_cleaner_shape_scores_no_worse_than_a_sloppier_one():
    """Equality is the structure component's own input, so a pattern whose
    bottoms match exactly must not grade below one whose bottoms barely clear
    the tolerance, all else equal."""
    clean = _geo(_double_bottom(left=70.0, right=70.0))
    sloppy = _geo(_double_bottom(left=70.0, right=70.9))
    assert clean["parts"]["structure"] >= sloppy["parts"]["structure"]


# ── follow-through proof ──────────────────────────────────────────────────────

def test_follow_through_is_reported_with_its_sample_size():
    """A bare '67%' off n=3 reads as a measurement when it is an anecdote."""
    df = _double_bottom()
    g = _geo(df)
    ft = g["follow_through"]
    if ft is not None:
        assert set(ft) >= {"rate", "n", "follows", "horizon", "atr_mult"}
        assert ft["n"] >= 1 and 0 <= ft["follows"] <= ft["n"]


def test_a_break_too_recent_to_grade_is_not_counted_as_a_failure():
    """Grading early would score the newest and most interesting signals as
    failures by construction."""
    df = _double_bottom()
    w = df.tail(260).reset_index(drop=True)
    cands = S._db_candidates(w, S.DB_PIVOT_LEN, S.DB_EQ_TOL_PCT,
                             S.DB_MIN_PULLBACK_PCT, S.DB_MIN_BARS,
                             S.DB_MAX_BARS, S.DB_ATR_BUFFER)
    assert cands, "fixture should contain at least one confirmed break"
    unresolved = [c for c in cands if c["break_idx"] + S.DB_FOLLOW_HORIZON >= len(w)]
    ft = S._db_follow_through(w, cands)
    resolved = len(cands) - len(unresolved)
    assert (ft["n"] if ft else 0) == resolved


def test_follow_through_grades_each_break_exactly_once():
    w = _double_bottom().tail(260).reset_index(drop=True)
    cands = S._db_candidates(w, S.DB_PIVOT_LEN, S.DB_EQ_TOL_PCT,
                             S.DB_MIN_PULLBACK_PCT, S.DB_MIN_BARS,
                             S.DB_MAX_BARS, S.DB_ATR_BUFFER)
    ft = S._db_follow_through(w, cands)
    if ft is not None:
        assert ft["n"] <= len(cands)


def test_follow_through_never_moves_the_quality_score():
    """Shape and reliability are two numbers on purpose — a textbook A+ can sit
    on a poor follow-through rate, and that disagreement is the read."""
    df = _double_bottom()
    w = df.tail(260).reset_index(drop=True)
    cands = S._db_candidates(w, S.DB_PIVOT_LEN, S.DB_EQ_TOL_PCT,
                             S.DB_MIN_PULLBACK_PCT, S.DB_MIN_BARS,
                             S.DB_MAX_BARS, S.DB_ATR_BUFFER)
    q = S._db_quality(w, cands[-1])
    assert "follow_through" not in q
    assert "rate" not in q


def test_the_dedup_keeps_one_shape_per_left_bottom():
    """One left low pairs with several later lows inside the tolerance; those are
    the same reversal pocket described three ways."""
    w = _double_bottom().tail(260).reset_index(drop=True)
    cands = S._db_candidates(w, S.DB_PIVOT_LEN, S.DB_EQ_TOL_PCT,
                             S.DB_MIN_PULLBACK_PCT, S.DB_MIN_BARS,
                             S.DB_MAX_BARS, S.DB_ATR_BUFFER)
    lefts = [c["left_idx"] for c in cands]
    assert len(lefts) == len(set(lefts))


# ── registry wiring ───────────────────────────────────────────────────────────

def test_it_is_registered_and_wired_to_the_right_function():
    assert S.SCANNERS["Double Bottom"]["fn"] is S.scan_double_bottom
    assert S.SCANNERS["Double Bottom"]["category"] == "Pattern"


def test_it_joins_the_reversal_family_rather_than_voting_alone():
    """Rounding Bottom and Early Reversal read the same underlying fact about a
    chart, so they must not each contribute a vote to confluence."""
    import opportunity_hub as oh
    assert oh.scanner_family("Double Bottom") == "Reversal"


def test_it_arrives_unmeasured_and_claims_no_edge():
    import opportunity_hub as oh
    assert oh.scanner_tier("Double Bottom") == "unmeasured"
    assert oh.scanner_weight("Double Bottom") == oh.WEIGHT_UNMEASURED
    assert "NOT MEASURED" in S.SCANNERS["Double Bottom"]["description"]


def test_the_loose_early_reversal_detector_is_left_alone():
    """`detect_bullish_reversal_structure` is a sub-signal of a scanner whose
    numbers are already on record. This port does not tighten it in place."""
    import inspect
    loose = inspect.signature(S.detect_bullish_reversal_structure).parameters
    assert loose["eq_tol_pct"].default == 3.0      # still the loose tolerance
    assert loose["pivot_len"].default == 5         # still the loose pivot
    assert S.DB_EQ_TOL_PCT == 1.4                  # the spec's, on the new one
    assert S.DB_PIVOT_LEN == 8


# ── component direction ───────────────────────────────────────────────────────
# Each factor must move the score the way the spec says. Written after a
# mislabelled fixture made the volume component look inverted — it was not, but
# "which half of the pattern is the second half" is exactly the kind of thing
# that should be pinned rather than re-derived by hand each time.

def _vol_case(mutate):
    df = _double_bottom()
    g0 = _geo(df)
    v = df["volume"].to_numpy(dtype=float).copy()
    mutate(v, g0["left_bar_idx"], g0["right_bar_idx"])
    df = df.copy()
    df["volume"] = v
    return _geo(df)["parts"]["volume"]


def test_volume_contracting_into_the_pattern_scores_above_expansion():
    """VCP's two-sided signature: quiet through the base, loud on the break."""
    mid = lambda a, b: a + (b - a) // 2

    def quieter(v, a, b):
        v[:] = 2e6
        v[mid(a, b):b] = 5e5

    def louder(v, a, b):
        v[:] = 5e5
        v[mid(a, b):b] = 2e6

    assert _vol_case(quieter) > _vol_case(louder)


def test_a_weak_break_scores_below_a_decisive_one():
    strong = _geo(_double_bottom(neck=80.0, peak=84.0))["parts"]["breakout"]
    weak = _geo(_double_bottom(neck=80.0, peak=80.9,
                               tail=[80.9, 81.0, 81.1]))["parts"]["breakout"]
    assert strong > weak


def test_sloppier_bottoms_score_below_matched_ones():
    clean = _geo(_double_bottom(left=70.0, right=70.0))["parts"]["structure"]
    sloppy = _geo(_double_bottom(left=70.0, right=70.9))["parts"]["structure"]
    assert clean > sloppy


# ── the plan must be where the MEASUREMENT harness looks ─────────────────────

def test_the_plan_is_emitted_at_the_top_level_not_only_in_geometry():
    """`backtest.py` reads hit["entry"/"stop"/"target"] and
    `scanner_plans.has_plan` checks the same three keys. A plan nested only in
    `geometry` is readable by a human on the chart card and invisible to the
    R-simulator — which is exactly why the plan census scores Rounding Bottom
    and VCP Coiling as planless despite both emitting a plan on every hit.

    This scanner is `unmeasured`, and the only route out of that is a harness
    that can score it. So this is not a formatting preference; it is the
    difference between measurable and permanently unmeasurable.
    """
    import scanner_plans as sp
    r = _hit(_double_bottom())
    assert sp.has_plan(r), "the census would score this scanner as planless"
    for k in ("entry", "stop", "target"):
        assert r[k] == r["geometry"][k], f"{k} disagrees with the geometry payload"


def test_the_geometry_payload_keeps_its_own_copy():
    """The chart overlay and /api/double_bottom both read geometry; surfacing
    the plan at the top level must not move it out from under them."""
    g = _geo(_double_bottom())
    for k in ("entry", "stop", "target", "risk_reward", "verdict"):
        assert k in g
