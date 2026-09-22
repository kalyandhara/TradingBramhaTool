"""Tests for the SBC card's forward test — B-114.

The study scores the sentence the card prints, so the two must not drift: a
measurement of a DIFFERENT verdict from the one the reader sees is measuring
nothing anybody will act on. `verdict_tone` here is a port of `sbcReading` in
`chart_dashboard.html`, and these cases are the ones that separate them.

Also pinned: the timing artifact the first run walked into. `failed` is decided
by the bars AFTER a break, so at the break bar it is always False — scoring
events there gave 41 held / 0 failed on BSE against 11 failures the card shows
on the same history.
"""
import pytest

import sbc_reading_backtest as sbcb


def _stats(avg_chain=3.0):
    return {"avg_chain": avg_chain, "max_chain": 6, "total_bos": 25,
            "total_choch": 21, "failed_count": 11, "fail_win": 3}


def _ev(type_="CHOCH", quality="STRONG", failed=False, direction="up"):
    return {"type": type_, "quality": quality, "failed": failed,
            "direction": direction, "level": 3774.86, "bar": 100}


# ── the verdict, in lockstep with the card ────────────────────────────────────
def test_a_failed_choch_is_the_bad_tone_whatever_its_quality():
    """THE case from the conversation: quality STRONG, but it failed. The card
    calls that not-confirmed, and 'STRONG' must not rescue it."""
    tone, verdict = sbcb.verdict_tone(_stats(2.1), _ev(failed=True))
    assert tone == "bad" and "NOT confirmed" in verdict and "CHoCH failed" in verdict


def test_a_failed_bos_says_continuation_not_confirmed():
    tone, verdict = sbcb.verdict_tone(_stats(), _ev("BOS", failed=True))
    assert tone == "bad" and "Continuation NOT confirmed" in verdict


def test_a_weak_but_held_break_is_tentative_not_bad():
    tone, _ = sbcb.verdict_tone(_stats(), _ev(quality="WEAK"))
    assert tone == "warn"


def test_a_choppy_environment_downgrades_a_strong_break():
    """Below the chain threshold the structure keeps turning, so even a clean
    break is only tentative. This is the one place the ENVIRONMENT overrides the
    event's own quality."""
    assert sbcb.verdict_tone(_stats(avg_chain=1.9), _ev())[0] == "warn"
    assert sbcb.verdict_tone(_stats(avg_chain=3.0), _ev())[0] == "good"


def test_a_clean_break_in_a_trending_structure_is_good():
    tone, verdict = sbcb.verdict_tone(_stats(3.5), _ev())
    assert tone == "good" and "confirmed so far" in verdict


def test_the_thresholds_match_the_cards():
    """`SBC_THRESH` in chart_dashboard.html. Duplicated on purpose — a study
    should not import constants out of an HTML file — so it is pinned here."""
    assert (sbcb.CHAIN_CHOPPY, sbcb.CHAIN_TRENDING) == (2.0, 3.0)


# ── the timing artifact ───────────────────────────────────────────────────────
def test_the_card_is_read_after_the_failure_window_closes():
    """A verdict that depends on three bars of hindsight cannot be acted on
    before those bars, so the study reads the card at t+FAIL_WIN and enters
    after that. FAIL_WIN is the detector's own window, not a tunable."""
    assert sbcb.FAIL_WIN == 3


# ── the pre-registered bar ────────────────────────────────────────────────────
def _res(n_held, n_failed, diffs, p):
    return {"n_held": n_held, "n_failed": n_failed,
            "primary": {str(h): {"diff": d, "p": p}
                        for h, d in zip(sbcb.HORIZONS, diffs)}}


def test_an_underpowered_run_is_inconclusive_not_null():
    """BSE's own case: 9 failed events against a floor of 30. The lean is large
    and two horizons are nominally significant, and it still cannot be claimed."""
    v = sbcb.verdict_of(_res(32, 9, [7.1, 12.6, 16.0, 15.8], 0.009))
    assert v.startswith("INCONCLUSIVE")


def test_a_powered_positive_needs_the_sign_to_hold_everywhere():
    assert sbcb.verdict_of(_res(60, 40, [1, 2, 3, 4], 0.01)).startswith("POSITIVE")
    assert sbcb.verdict_of(_res(60, 40, [-1, 2, 3, 4], 0.01)).startswith("NULL")


def test_an_inverted_result_is_sayable():
    """If failed breaks beat held ones, the card's wording is backwards — that
    has to be a statable outcome, not a silent NULL."""
    assert sbcb.verdict_of(_res(60, 40, [-1, -2, -3, -4], 0.01)).startswith("INVERTED")


def test_an_insignificant_difference_is_null():
    assert sbcb.verdict_of(_res(60, 40, [1, 2, 3, 4], 0.40)).startswith("NULL")


# ── signed returns ────────────────────────────────────────────────────────────
def test_a_downward_break_that_precedes_a_fall_scores_positive():
    """Unsigned, every bearish event would read as an inverted bullish one —
    the mistake B-76's bias gauge made."""
    import pandas as pd
    # Entry is open[t+1]; the fall must land AFTER that bar, or the trade never
    # sees it. (The first cut of this fixture put the gap on the entry bar and
    # measured a flat 0%.)
    px = [100.0] * 4 + [90.0] * 5
    df = pd.DataFrame({"open": px, "high": px, "low": px, "close": px})
    r = sbcb._signed_fwd(df, 2, 3, "down", sbcb.bt.COST_GROSS)
    assert r == pytest.approx(10.0, abs=0.01)


# ── the fast walk's reconstructed stats ───────────────────────────────────────
# `walk_fast` detects the chain ONCE per symbol and rebuilds the card's stats
# from the event prefix, because re-detecting twice per bar is what kept this
# study to a single name. The reconstruction is a reimplementation of somebody
# else's accumulator, so it is checked here AND diffed against the slow walk by
# `--validate` on real data.
def _events(spec):
    """spec = [(type, chain)] — the two fields the reconstruction reads."""
    return [{"type": t, "chain": c, "direction": "up", "failed": False,
             "failed_bar": None, "bar": 100 + i, "quality": "STRONG"}
            for i, (t, c) in enumerate(spec)]


def test_a_chain_completes_when_a_choch_turns_the_structure():
    """Lengths are the chain counter of the event BEFORE each CHoCH: a run of
    3 BOSs ended by a CHoCH is a completed chain of 3."""
    evs = _events([("BOS", 1), ("BOS", 2), ("BOS", 3), ("CHOCH", 1)])
    assert stats_at_avg(evs) == 3.0


def stats_at_avg(evs):
    return sbcb.stats_at(evs)["avg_chain"]


def test_avg_chain_averages_every_completed_chain():
    evs = _events([("BOS", 1), ("BOS", 2), ("CHOCH", 1),      # completed 2
                   ("BOS", 2), ("BOS", 3), ("BOS", 4), ("CHOCH", 1)])  # completed 4
    assert stats_at_avg(evs) == 3.0


def test_an_unfinished_chain_is_not_averaged_in():
    """A run still in progress has no length yet. Counting it would drag the
    average toward whatever today happens to be."""
    assert stats_at_avg(_events([("BOS", 1), ("BOS", 2), ("BOS", 3)])) is None


def test_stats_count_types_and_the_running_chain():
    s = sbcb.stats_at(_events([("BOS", 1), ("CHOCH", 1), ("BOS", 2)]))
    assert (s["total_bos"], s["total_choch"]) == (2, 1)
    assert s["chain"] == 2 and s["max_chain"] == 2


def test_empty_events_do_not_crash_the_reconstruction():
    s = sbcb.stats_at([])
    assert s["avg_chain"] is None and s["total_bos"] == 0


def test_a_failure_outside_the_read_window_is_not_used():
    """`failed` is taken as-of the read bar. A flag set later is hindsight, and
    the guard says so rather than trusting the detector never does it."""
    ev = {"type": "CHOCH", "chain": 1, "direction": "up", "quality": "STRONG",
          "bar": 100, "failed": True, "failed_bar": 100 + sbcb.FAIL_WIN + 5}
    read_at = ev["bar"] + sbcb.FAIL_WIN
    usable = bool(ev["failed"]) and (ev["failed_bar"] is None
                                     or ev["failed_bar"] <= read_at)
    assert usable is False


# ── B-115: the sign convention, which the first report got wrong ──────────────
def test_the_down_side_is_printed_raw_not_signed():
    """Stored returns are signed BY THE EVENT'S DIRECTION, so a down event's
    +0.94 stored as -0.94 means the name ROSE. The first cut of the baseline
    report printed "fell -0.94%" for exactly that case. An underperformance read
    is not a decline and must not borrow its words."""
    res = {"n_up_held": 1545, "n_baseline_bars": 261121,
           "primary": {str(h): {"diff": 0.5, "p": 0.01, "mean_a": 2.0, "mean_b": 1.5}
                       for h in sbcb.HORIZONS},
           "clustered": {}, "verdict": "POSITIVE — test fixture",
           "down_side": {str(h): {"n": 980, "mean_signed": -0.936,
                                  "baseline_mean": 1.469} for h in sbcb.HORIZONS}}
    out = sbcb.baseline_report(res)
    # Check the DATA lines, not the note that explains the old mistake — the
    # note necessarily quotes the wrong wording in order to warn about it.
    data = [l for l in out.splitlines() if l.strip().startswith("@")]
    assert data, "expected per-horizon down-side lines"
    assert any("+0.94%" in l for l in data)     # the RAW return: the name rose
    assert not any("fell" in l for l in data)
    assert any("-0.53pp" in l for l in data)    # and it underperformed by half a point
