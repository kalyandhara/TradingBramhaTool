"""Tests for `scan_symmetrical_triangle` — the desk's first BILATERAL card (B-101).

Nothing here asserts that a symmetrical triangle WORKS. It is unmeasured and
claims no edge, and the whole reason it exists is that the registry had no way to
say "this resolves in a direction nobody knows yet". So what is pinned is:

  * the geometry — converging OPPOSED lines, and a refusal on every neighbouring
    shape (falling wedge, ascending triangle, descending triangle, channel);
  * the flatness gate, which is what keeps this from becoming a second bullish
    vote on an ascending base — the shape that already fires nine scanners here;
  * that the card carries NO bare `entry`/`stop`/`target`. This is the B-101
    failure in one assertion: VCP Coiling reads the same coil correctly and then
    emits an upward-only plan, and any key named `entry` is a key something
    downstream will read as a long;
  * that the hit does not vote in confluence, and is not a risk flag either.
"""
import numpy as np
import pandas as pd
import pytest

import opportunity_hub as oh
import scanner_templates as S

NAME = "Symmetrical Triangle (bilateral)"


# ──────────────────────────────────────────────────────────────────────────────
# Frame builders. The detector fits trendlines through SWING PIVOTS, so a frame
# has to oscillate between its boundaries — a smooth squeeze has no pivots to fit
# and is correctly not a triangle. Each leg is a straight run to the boundary and
# back, with the boundaries closing in bar by bar.
# ──────────────────────────────────────────────────────────────────────────────

def _bars(closes, vols=None, wick=0.004):
    c = np.asarray(closes, dtype=float)
    v = (np.asarray(vols, dtype=float) if vols is not None
         else np.full(len(c), 1_000_000.0))
    return pd.DataFrame({"open": c, "high": c * (1 + wick),
                         "low": c * (1 - wick), "close": c, "volume": v})


def _coil(upper0=140.0, lower0=60.0, up_slope=-0.25, lo_slope=0.25, *,
          n=100, leg=7, vol_dryup=True, tail=None):
    """Price zig-zagging between two lines that close in on each other.

    The default boundaries meet at bar ~160, so a 100-bar read sits about
    two-thirds of the way into the apex — inside the textbook resolution band. A
    frame that runs PAST its own apex is not a triangle any more and the detector
    says so, which is a real gate and not something the fixtures should dodge by
    accident.

    `up_slope`/`lo_slope` are per-bar. Setting one to 0 gives an ascending or
    descending triangle; setting both negative gives a falling wedge — which is
    how the rejection cases below are built from the same generator.
    """
    px = []
    to_upper = True
    i = 0
    while i < n:
        u = upper0 + up_slope * i
        l = lower0 + lo_slope * i
        target = u if to_upper else l
        start = px[-1] if px else (l + u) / 2
        step = max(2, min(leg, n - i))
        px += list(np.linspace(start, target, step + 1))[1:]
        i += step
        to_upper = not to_upper
    px = px[:n]
    if tail is not None:
        px = px[:n - len(tail)] + list(tail)
    if vol_dryup:
        vol = list(np.linspace(3e6, 1.2e6, len(px)))
    else:
        vol = [2e6] * len(px)
    return _bars(px, vol)


def _sym(**kw):
    """A textbook symmetrical triangle: falling highs, rising lows, ~1:1."""
    return _coil(**kw)


# ── the shape ─────────────────────────────────────────────────────────────────
def test_textbook_symmetrical_triangle_fires():
    g = S.detect_symmetrical_triangle_geometry(_sym())
    assert g is not None, "a converging opposed-line coil is the pattern"
    assert g["upper_slope"] < 0 < g["lower_slope"]
    assert g["direction"] == "bilateral"


def test_falling_wedge_is_not_a_symmetrical_triangle():
    """Both lines falling is the WEDGE's shape, and it has its own detector."""
    assert S.detect_symmetrical_triangle_geometry(
        _coil(up_slope=-0.45, lo_slope=-0.15)) is None


def test_ascending_triangle_is_refused():
    """A flat top with rising lows is a bullish base — nine scanners already
    read it, and an accidental tenth vote is exactly what B-101 warns about."""
    assert S.detect_symmetrical_triangle_geometry(
        _coil(up_slope=0.0, lo_slope=0.35)) is None


def test_descending_triangle_is_refused():
    """The mirror case: falling highs on a flat base is directional too."""
    assert S.detect_symmetrical_triangle_geometry(
        _coil(up_slope=-0.35, lo_slope=0.0)) is None


def test_parallel_channel_is_refused():
    """Lines that never converge are a channel; there is no apex and no coil."""
    assert S.detect_symmetrical_triangle_geometry(
        _coil(up_slope=0.20, lo_slope=0.20)) is None


def test_lopsided_triangle_is_refused():
    """Lows rising five times faster than highs fall is an ascending triangle
    wearing a downtilt. 1:3 is the documented limit."""
    assert S.detect_symmetrical_triangle_geometry(
        _coil(up_slope=-0.06, lo_slope=0.45)) is None


def test_volume_rising_into_the_apex_is_refused():
    """A coil is a contraction. Expansion into the apex is something else."""
    df = _sym(vol_dryup=True)
    df["volume"] = np.linspace(1e6, 4e6, len(df))
    assert S.detect_symmetrical_triangle_geometry(df) is None


def test_short_frame_returns_none():
    assert S.detect_symmetrical_triangle_geometry(_sym(n=40)) is None


# ── the apex ──────────────────────────────────────────────────────────────────
def test_apex_is_ahead_of_the_last_bar():
    g = S.detect_symmetrical_triangle_geometry(_sym())
    assert g["bars_to_apex"] > 0
    assert 0.0 < g["apex_progress"] <= 1.0


def test_apex_progress_grows_as_price_coils_further_in():
    """The same triangle read later is further into its own apex. This is the
    number a reader uses to decide whether to keep watching, so it has to move
    in the one direction time moves."""
    df = _sym(n=110)
    early = S.detect_symmetrical_triangle_geometry(df.iloc[:100].reset_index(drop=True))
    late = S.detect_symmetrical_triangle_geometry(df.iloc[10:].reset_index(drop=True))
    assert early and late
    assert late["apex_progress"] > early["apex_progress"]


# ── state ─────────────────────────────────────────────────────────────────────
def test_break_up_and_break_down_are_both_first_class():
    """Neither side is the 'real' outcome. The detector must name both, and a
    coil that has done neither is a legitimate state rather than a near-miss —
    the falling wedge returns None for price in the lower half; here there is no
    half price is supposed to be in."""
    up = S.detect_symmetrical_triangle_geometry(_sym(tail=[125.0, 128.0]))
    dn = S.detect_symmetrical_triangle_geometry(_sym(tail=[80.0, 77.0]))
    mid = S.detect_symmetrical_triangle_geometry(_sym())
    assert up and up["state"] == "breakout-up"
    assert dn and dn["state"] == "breakout-down"
    assert mid and mid["state"] in ("coiling", "pre-breakout-up", "pre-breakout-down")


# ── the card, and the one key that must not exist ─────────────────────────────
def test_card_publishes_both_legs():
    card = S.scan_symmetrical_triangle(_sym())
    assert card is not None
    assert card["up_target"] > card["up_entry"] > card["up_stop"]
    assert card["down_target"] < card["down_entry"] < card["down_stop"]


def test_card_has_no_bare_entry_stop_or_target():
    """THE B-101 ASSERTION. A key named `entry` is a key something downstream
    reads as a long — `backtest._simulate_plan` walks entry → stop/target and is
    long-only, `scanner_plans` counts the triple as a trade plan, and the hub
    card renders it as the trade to take. A pattern whose direction is unknown
    must not hand any of them one. Both legs are published; neither is promoted
    to the unqualified name."""
    card = S.scan_symmetrical_triangle(_sym())
    for key in ("entry", "stop", "target"):
        assert key not in card, (
            f"bilateral card exposes a bare {key!r} — that is the VCP failure "
            "B-101 was raised about")


def test_card_says_bilateral_out_loud():
    """The reader's habit, built by every other pattern in this registry, is to
    read a pattern hit as a reason to buy. The card has to break that habit on
    its own face, not only in a tier colour the reader may never hover."""
    card = S.scan_symmetrical_triangle(_sym())
    assert card["direction"] == "bilateral" and card["neutral"] is True
    assert "BILATERAL" in card["tags"]
    assert any("BILATERAL" in r for r in card["reasons"])


def test_time_stop_is_the_apex_not_a_horizon():
    card = S.scan_symmetrical_triangle(_sym())
    assert card["time_stop"] == max(5, card["bars_to_apex"])


# ── the registry, and the vote it must not cast ───────────────────────────────
def test_registered_as_neutral():
    assert NAME in S.SCANNERS
    assert S.SCANNERS[NAME]["category"] == "Neutral"
    assert oh.scanner_tier(NAME) == "neutral"


def test_neutral_scanner_carries_no_weight():
    assert oh.scanner_weight(NAME) == 0.0


def test_a_bilateral_hit_does_not_vote_in_confluence():
    """The fall-through in `tally_evidence` gives an unmapped, non-risk scanner
    its own family of one — the right default for a new directional scanner and
    exactly wrong here, which is why NEUTRAL_SCANNERS is checked explicitly."""
    fams, points, risk = oh.tally_evidence([NAME])
    assert fams == [] and points == 0.0


def test_it_does_not_dilute_a_real_confluence_either():
    """Adding a coil to a name that already has evidence must change nothing —
    not the families, not the points."""
    base = oh.tally_evidence(["Falling Wedge", "Pullback Entry"])
    with_coil = oh.tally_evidence(["Falling Wedge", "Pullback Entry", NAME])
    assert base == with_coil


def test_it_is_not_a_risk_flag():
    """A risk hit argues AGAINST the name. A coil argues for nothing. Folding
    the new state into RISK_SCANNERS would have been the cheap way to stop it
    voting, and would print a bearish flag on a pattern that is not bearish."""
    assert NAME not in oh.RISK_SCANNERS
    _, _, risk = oh.tally_evidence([NAME])
    assert risk == []


def test_it_is_in_the_pipeline():
    """Excluded from voting, not from running — a coil about to resolve is
    exactly the thing to have on a watchlist."""
    assert NAME in oh.pipeline_scanners()


# ── the plan census ───────────────────────────────────────────────────────────
def test_the_census_calls_it_bilateral_not_planless():
    """`scanner_plans` counts entry/stop/target, and a scanner with none of them
    is normally NONE — a thing to go fix. Here the fix would be to invent a
    direction, so the census gets a fifth state instead. Same argument the file
    already makes for why UNSEEN is not NONE."""
    import scanner_plans as sp
    res = sp.load()
    if res is None:
        pytest.skip("no plan census cached — run tools/scanner_plans.py --probe")
    assert sp.classify(res["scanners"][NAME], NAME) == sp.BILATERAL
    s = sp.summarise(res)
    assert NAME in s["scanners"][sp.BILATERAL]
    assert NAME not in s["scanners"][sp.NONE]


def test_bilateral_is_outside_the_coverage_ratio():
    """It can neither flatter nor damage a ratio it has no opinion about."""
    import scanner_plans as sp
    res = sp.load()
    if res is None:
        pytest.skip("no plan census cached")
    s = sp.summarise(res)
    assert s["observed"] == s["total"] - s["counts"][sp.UNSEEN] - s["counts"][sp.BILATERAL]


def test_it_fires_on_real_data_without_flooding():
    """32 hits over 147 symbols at stride 5 (probed 2026-09-20). A detector that
    never fires is decoration; one that fires on everything is noise. This pins
    the census row itself, so a tolerance change that silently turns it into
    either shows up as a failed test rather than as a quieter watchlist."""
    import scanner_plans as sp
    res = sp.load()
    if res is None:
        pytest.skip("no plan census cached")
    fired = res["scanners"][NAME]["fired"]
    assert 5 <= fired <= 500, f"{fired} hits — re-read the gates before re-pinning"
    assert res["scanners"][NAME]["with_plan"] == 0
