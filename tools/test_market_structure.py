"""Tests for the B-42 shared market-structure read.

Runs two ways so it fits the repo's "__main__ probe" style AND pytest:
    py -3 tools/test_market_structure.py     # prints PASS/FAIL, exits nonzero on fail
    pytest tools/test_market_structure.py    # standard collection

Pure, deterministic, no network. Sequence labelling is pinned against hand-built
swing lists; the state machine and the reconciliation invariant are exercised on
synthetic frames whose structure is known by construction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import scanner_templates as sc


# ── helpers ───────────────────────────────────────────────────────────────────
def _sw(*pairs):
    """Build a swings list from (kind, level) pairs, bars auto-numbered."""
    return [{"bar": i * 10, "level": float(lv), "kind": k}
            for i, (k, lv) in enumerate(pairs)]


def _frame(closes, spread=1.0):
    """OHLCV frame from a close path; highs/lows straddle the close."""
    c = np.asarray(closes, dtype=float)
    return pd.DataFrame({
        "open": c,
        "high": c + spread,
        "low": c - spread,
        "close": c,
        "volume": np.full(len(c), 100_000.0),
    })


def _zigzag(legs, step=1.0):
    """Concatenate linear legs: legs = [(start, end, n_bars), ...].

    The junction value is emitted once — repeating it would create a 2-bar flat
    plateau, which `detect_structure_chain` legitimately reads as two pivots
    (see `test_plateau_duplicates_are_collapsed` for that case on purpose).
    """
    out: list[float] = []
    for start, end, n in legs:
        seg = np.linspace(start, end, n).tolist()
        if out and out[-1] == seg[0]:
            seg = seg[1:]
        out.extend(seg)
    return out


# ── label_swing_sequence ──────────────────────────────────────────────────────
def test_labels_uptrend_sequence():
    got = sc.label_swing_sequence(_sw(("low", 100), ("high", 110),
                                      ("low", 105), ("high", 120)))
    assert [s["label"] for s in got] == [None, None, "HL", "HH"]


def test_labels_downtrend_sequence():
    got = sc.label_swing_sequence(_sw(("high", 120), ("low", 105),
                                      ("high", 115), ("low", 95)))
    assert [s["label"] for s in got] == [None, None, "LH", "LL"]


def test_first_of_each_kind_is_unlabelled():
    got = sc.label_swing_sequence(_sw(("high", 100), ("low", 90)))
    assert got[0]["label"] is None and got[1]["label"] is None
    assert got[0]["prev_level"] is None and got[1]["prev_level"] is None


def test_labels_compare_to_same_kind_only():
    # The low at 105 must be compared to the prior LOW (100), not the high (110).
    got = sc.label_swing_sequence(_sw(("low", 100), ("high", 110), ("low", 105)))
    assert got[2]["label"] == "HL" and got[2]["prev_level"] == 100.0


def test_equal_tolerance_produces_eqh_eql():
    got = sc.label_swing_sequence(_sw(("high", 100), ("high", 100.2)), tol_pct=0.5)
    assert got[1]["label"] == "EQH"
    strict = sc.label_swing_sequence(_sw(("high", 100), ("high", 100.2)), tol_pct=0.0)
    assert strict[1]["label"] == "HH"


def test_equal_lows_flagged_as_eql():
    got = sc.label_swing_sequence(_sw(("low", 50), ("low", 50.1)), tol_pct=1.0)
    assert got[1]["label"] == "EQL"


def test_input_not_mutated():
    src = _sw(("low", 100), ("low", 110))
    sc.label_swing_sequence(src)
    assert "label" not in src[0] and "label" not in src[1]


def test_plateau_duplicates_are_collapsed():
    """A flat top registers once per bar in the underlying walk; the sequence
    must describe the market, not the sampling. Without this the duplicate is
    always EQH/EQL and every trend read degrades to TRANSITION."""
    got = sc.label_swing_sequence(_sw(("high", 100), ("high", 120), ("high", 120)))
    assert got[1]["label"] == "HH"
    assert got[2]["label"] is None and got[2]["duplicate_of"] == got[1]["bar"]
    # The collapsed copy must not become the reference for what follows.
    more = sc.label_swing_sequence(_sw(("high", 100), ("high", 120),
                                       ("high", 120), ("high", 130)))
    assert more[3]["label"] == "HH" and more[3]["prev_level"] == 120.0


def test_empty_and_malformed_swings():
    assert sc.label_swing_sequence([]) == []
    weird = sc.label_swing_sequence([{"bar": 0, "level": None, "kind": "high"},
                                     {"bar": 1, "kind": "sideways", "level": 5}])
    assert all(s["label"] is None for s in weird)


# ── the invariant ─────────────────────────────────────────────────────────────
def test_invariant_passes_on_own_output():
    labelled = sc.label_swing_sequence(_sw(("low", 100), ("high", 110),
                                           ("low", 105), ("high", 120)))
    assert sc._verify_swing_sequence(labelled)["ok"] is True


def test_invariant_catches_a_corrupted_label():
    labelled = sc.label_swing_sequence(_sw(("low", 100), ("low", 105)))
    labelled[1]["label"] = "LL"          # pivots say HL
    res = sc._verify_swing_sequence(labelled)
    assert res["ok"] is False and "pivots imply HL" in res["violations"][0]


# ── read_market_structure ─────────────────────────────────────────────────────
def test_read_returns_none_on_short_history():
    assert sc.read_market_structure(_frame([100.0] * 10), pivot_len=15) is None


def test_read_uptrend_state_and_invariant():
    # Rising zigzag: each leg tops and bottoms above the last.
    path = _zigzag([(100, 130, 40), (130, 115, 40), (115, 160, 40),
                    (160, 145, 40), (145, 200, 40)])
    r = sc.read_market_structure(_frame(path), pivot_len=5)
    assert r is not None
    assert r["invariant_ok"] is True
    assert r["state"] in ("UPTREND", "TRANSITION", "BROADENING")
    assert r["last_low_label"] == "HL"


def test_read_downtrend_state():
    path = _zigzag([(200, 160, 40), (160, 180, 40), (180, 130, 40),
                    (130, 150, 40), (150, 100, 40)])
    r = sc.read_market_structure(_frame(path), pivot_len=5)
    assert r is not None
    assert r["invariant_ok"] is True
    assert r["last_high_label"] == "LH"


def test_zone_is_discount_near_the_low():
    # Breaks out to 170, then retraces deep into the 119–171 band.
    path = _zigzag([(100, 150, 50), (150, 120, 50), (120, 170, 50), (170, 132, 50)])
    r = sc.read_market_structure(_frame(path), pivot_len=5)
    assert r is not None and r["zone"] == "DISCOUNT"
    assert r["zone_pct"] < 30.0


def test_zone_survives_a_consumed_swing_high():
    """After a break consumes the live swing high, the band must fall back to the
    last high pivot — including when that pivot is the first of its kind and so
    carries no HH/LH label."""
    path = _zigzag([(100, 150, 50), (150, 120, 50), (120, 170, 50)])
    r = sc.read_market_structure(_frame(path), pivot_len=5)
    assert r is not None
    assert r["swing_high"] is not None and r["swing_low"] is not None
    assert r["zone"] == "PREMIUM"


def test_zone_pct_is_not_clamped_outside_the_band():
    """Price beyond its last band is breakout information, not an error."""
    path = _zigzag([(100, 150, 50), (150, 120, 50), (120, 170, 50)])
    r = sc.read_market_structure(_frame(path), pivot_len=5)
    assert r is not None and r["zone_pct"] > 100.0


def test_read_reports_its_params_and_shape():
    path = _zigzag([(100, 140, 50), (140, 110, 50), (110, 170, 50)])
    r = sc.read_market_structure(_frame(path), pivot_len=5, eq_tol_pct=0.25)
    assert r is not None
    assert r["params"] == {"pivot_len": 5, "confirm": "close",
                           "fail_win": 3, "eq_tol_pct": 0.25}
    for key in ("state", "agreement", "sequence", "swings", "zone", "last_event",
                "invariant_ok", "trend_from_breaks"):
        assert key in r


def test_agreement_reconciles_state_against_breaks():
    path = _zigzag([(100, 140, 50), (140, 110, 50), (110, 170, 50), (170, 140, 50)])
    r = sc.read_market_structure(_frame(path), pivot_len=5)
    assert r is not None
    assert r["agreement"] in ("CONFIRMED", "DIVERGING", "UNDECIDED")
    seq_dir = {"UPTREND": 1, "DOWNTREND": -1}.get(r["state"], 0)
    brk = r["trend_from_breaks"]
    if seq_dir == 0 or brk in (0, None):
        assert r["agreement"] == "UNDECIDED"
    else:
        assert r["agreement"] == ("CONFIRMED" if seq_dir == brk else "DIVERGING")


def test_sequence_is_labels_only_and_matches_swings():
    path = _zigzag([(100, 140, 50), (140, 110, 50), (110, 170, 50), (170, 130, 50)])
    r = sc.read_market_structure(_frame(path), pivot_len=5)
    assert r is not None
    assert r["sequence"] == [s["label"] for s in r["swings"] if s["label"]]
    assert all(lab in ("HH", "HL", "LH", "LL", "EQH", "EQL") for lab in r["sequence"])


def test_flat_tape_does_not_crash():
    r = sc.read_market_structure(_frame([100.0] * 200), pivot_len=5)
    # Either no structural break at all (None) or a coherent read.
    assert r is None or r["invariant_ok"] is True


def test_passing_a_prebuilt_chain_matches_computing_it():
    """The chart endpoint reuses its own walk. If that path diverged from the
    standalone one, chart and scanners would disagree — the exact failure B-42
    exists to prevent."""
    path = _zigzag([(100, 140, 50), (140, 110, 50), (110, 170, 50), (170, 140, 50)])
    df = _frame(path)
    fresh = sc.read_market_structure(df, pivot_len=5)
    chain = sc.detect_structure_chain(df, pivot_len=5, confirm="close",
                                      fail_win=3, max_swings=15)
    reused = sc.read_market_structure(df, pivot_len=5, chain=chain)
    assert fresh == reused


def test_additive_existing_detectors_unchanged():
    """B-42 was scoped additive: the existing walks must still answer the same."""
    path = _zigzag([(100, 140, 50), (140, 110, 50), (110, 170, 50)])
    df = _frame(path)
    before = sc.detect_bos_choch(df)
    sc.read_market_structure(df, pivot_len=5)
    after = sc.detect_bos_choch(df)
    assert before == after


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


if __name__ == "__main__":
    import traceback
    failed = 0
    for t in ALL_TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(ALL_TESTS) - failed}/{len(ALL_TESTS)} passed")
    raise SystemExit(1 if failed else 0)
