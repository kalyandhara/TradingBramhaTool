"""Tests for B-92's edge study, offline.

Three things here could turn a null into a finding, and they are what these pin:

  * the **event must be the transition**, not the state. Counting every bar on
    which a flag is already broken would score a persistent condition as if it
    were a stream of fresh entries, inflating n by the length of each breakout;
  * the **plan walk must be conservative and must mirror correctly** for the bear
    side, which `backtest._simulate_plan` cannot do at all (it is long-only);
  * the **window slice must be equivalent to the full frame**. The study hands the
    detector `WINDOW+ATR_N` bars rather than all history -- 35x faster -- and that
    is only legitimate if the answer is identical.
"""
import numpy as np
import pandas as pd

import flag_pole as fp
import flag_pole_edge as fpe


class _NoCost:
    def round_trip_pct(self, a, b):
        return 0.0


def _arr(vals):
    return np.asarray(vals, float)


# ── the plan walk ─────────────────────────────────────────────────────────────

def test_target_before_stop_is_a_win():
    h = _arr([100, 112, 112]); l = _arr([99, 108, 108]); c = _arr([100, 111, 111])
    r = fpe.walk_plan(h, l, c, 0, 100.0, 95.0, 110.0, True, _NoCost())
    assert r["outcome"] == "target"
    assert abs(r["r"] - 2.0) < 1e-9          # +10 on 5 of risk


def test_stop_before_target_is_a_loss():
    h = _arr([100, 101]); l = _arr([99, 94]); c = _arr([100, 95])
    r = fpe.walk_plan(h, l, c, 0, 100.0, 95.0, 110.0, True, _NoCost())
    assert r["outcome"] == "stop"
    assert abs(r["r"] + 1.0) < 1e-9


def test_a_bar_spanning_both_fills_the_stop_first():
    """The pessimistic assumption -- daily bars cannot prove which came first."""
    h = _arr([120]); l = _arr([80]); c = _arr([100])
    r = fpe.walk_plan(h, l, c, 0, 100.0, 95.0, 110.0, True, _NoCost())
    assert r["outcome"] == "stop"


def test_the_bear_walk_mirrors_the_levels():
    # Short from 100, stop ABOVE at 105, target BELOW at 90.
    h = _arr([100, 101]); l = _arr([99, 89]); c = _arr([100, 90])
    r = fpe.walk_plan(h, l, c, 0, 100.0, 105.0, 90.0, False, _NoCost())
    assert r["outcome"] == "target"
    assert r["r"] > 0                        # a short that fell is a WIN


def test_a_bear_stop_is_a_rise():
    h = _arr([100, 106]); l = _arr([99, 100]); c = _arr([100, 105])
    r = fpe.walk_plan(h, l, c, 0, 100.0, 105.0, 90.0, False, _NoCost())
    assert r["outcome"] == "stop"
    assert r["r"] < 0


def test_an_untouched_plan_times_out_rather_than_scoring_a_win():
    n = 80
    h = _arr([101] * n); l = _arr([99] * n); c = _arr([100] * n)
    r = fpe.walk_plan(h, l, c, 0, 100.0, 95.0, 110.0, True, _NoCost(), max_bars=20)
    assert r["outcome"] == "timeout"


def test_a_degenerate_plan_is_refused_rather_than_scored():
    h = _arr([100]); l = _arr([100]); c = _arr([100])
    assert fpe.walk_plan(h, l, c, 0, 100.0, 100.0, 110.0, True, _NoCost()) is None


# ── forward return timing ─────────────────────────────────────────────────────

def test_forward_return_enters_at_the_next_open():
    c = np.arange(100.0, 130.0)
    o = np.concatenate([[100.0], c[:-1]])
    got = fpe._fwd(o, c, 5, 3, _NoCost())
    assert abs(got - (c[9] / o[6] - 1) * 100) < 1e-9


def test_forward_return_is_none_off_the_end():
    c = np.arange(100.0, 110.0)
    o = np.concatenate([[100.0], c[:-1]])
    assert fpe._fwd(o, c, len(c) - 2, 20, _NoCost()) is None


# ── the verdict, applied mechanically ─────────────────────────────────────────

def _scored(direction, n, edge, p):
    return {"directions": {direction: {
        "horizons": {fpe.PRIMARY_H: {"n": n, "edge": edge, "p": p}}}}}


def test_a_thin_sample_is_inconclusive_not_null():
    v, _ = fpe.verdict(_scored("bull", 12, 5.0, 0.001), "bull")
    assert v.startswith("INCONCLUSIVE")


def test_a_positive_significant_bull_edge_passes():
    v, _ = fpe.verdict(_scored("bull", 1000, 0.7, 0.04), "bull")
    assert v == "PASS"


def test_a_negative_significant_bull_edge_is_inverted_not_a_mirror_to_ship():
    v, why = fpe.verdict(_scored("bull", 1000, -0.7, 0.01), "bull")
    assert v == "INVERTED"
    assert "do NOT ship the mirror" in why


def test_the_bear_sign_convention_is_not_flipped_silently():
    """Bear signals are scored as LONG returns, so negative means teeth.

    The verdict states which it means rather than flipping the number, or the
    printed table and the verdict word would disagree.
    """
    good, _ = fpe.verdict(_scored("bear", 1000, -1.3, 0.001), "bear")
    assert good.startswith("PASS")
    bad, why = fpe.verdict(_scored("bear", 1000, +1.3, 0.001), "bear")
    assert bad == "INVERTED"
    assert "went UP" in why


def test_an_insignificant_edge_is_a_null_either_way():
    assert fpe.verdict(_scored("bull", 1000, 0.7, 0.40), "bull")[0] == "NULL"
    assert fpe.verdict(_scored("bear", 1000, -0.7, 0.40), "bear")[0] == "NULL"


# ── the optimisation that makes the study runnable ───────────────────────────

VALUE_KEYS = ("direction", "pole_low", "pole_high", "pole_bars", "pole_atr",
              "pole_monotonicity", "flag_bars", "flag_high", "flag_low",
              "retrace", "vol_contract", "broken", "entry", "stop", "target",
              "rr", "atr")


def test_a_window_slice_answers_identically_to_the_full_frame():
    """`collect` hands the detector WINDOW+ATR_N bars, not all history.

    That is 35x faster and is only legitimate because `detect_flag_pole` reads
    its last WINDOW bars and nothing else. If that ever stops being true this
    test fails before the study quietly measures a different thing.
    """
    rng = np.random.default_rng(7)
    n = 600
    c = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, n)))
    frame = pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                          "close": c, "volume": rng.uniform(1e5, 1e6, n)})
    need = fp.WINDOW + fp.ATR_N
    compared = 0
    for t in range(need + 10, n - 5, 13):
        for d in ("bull", "bear"):
            full = fp.detect_flag_pole(frame.iloc[:t + 1], d)
            win = fp.detect_flag_pole(frame.iloc[t + 1 - need:t + 1], d)
            assert (full is None) == (win is None)
            if full is None:
                continue
            compared += 1
            assert {k: full[k] for k in VALUE_KEYS} == {k: win[k] for k in VALUE_KEYS}
    assert compared > 0, "the fixture produced no patterns to compare"
