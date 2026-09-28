"""Tests for exit_model_bakeoff.py (B-124): pairing, clustering, verdict floors.

The pairing is the part that can go silently wrong: if trades were matched by
position instead of by (symbol, signal bar), two arms with different trade
counts would compare unrelated trades and still print a tidy dR.
"""
import pytest

import exit_model_bakeoff as eb


def _t(sym, t, r):
    return {"symbol": sym, "t": t, "r": r, "bars": 1}


def test_pairs_on_symbol_and_bar_not_on_position():
    ctl = [_t("A", 1, 0.0), _t("A", 2, 1.0), _t("B", 5, -1.0)]
    trt = [_t("A", 2, 2.0), _t("B", 5, 0.0), _t("C", 9, 9.0)]   # C has no control
    pr = eb.paired(ctl, trt)
    assert pr["pairs"] == 2 and pr["symbols"] == 2
    assert pr["mean_dR"] == pytest.approx(1.0)                  # A:+1, B:+1


def test_a_prolific_symbol_is_one_opinion():
    ctl = [_t("A", i, 0.0) for i in range(30)] + [_t("B", 0, 0.0)]
    trt = [_t("A", i, 1.0) for i in range(30)] + [_t("B", 0, -1.0)]
    assert eb.paired(ctl, trt)["mean_dR"] == pytest.approx(0.0)   # not +0.94


def test_floors_make_small_samples_inconclusive_never_null():
    assert eb.verdict({"symbols": 29, "pairs": 500, "p": 0.0, "mean_dR": 1}) == "INCONCLUSIVE"
    assert eb.verdict({"symbols": 100, "pairs": 149, "p": 0.0, "mean_dR": 1}) == "INCONCLUSIVE"


def test_bonferroni_alpha_is_applied():
    base = {"symbols": 100, "pairs": 500}
    assert eb.verdict({**base, "p": 0.02, "mean_dR": 0.5}) == "NO DIFFERENCE"
    assert eb.verdict({**base, "p": 0.001, "mean_dR": 0.5}) == "TRAIL BETTER"
    assert eb.verdict({**base, "p": 0.001, "mean_dR": -0.5}) == "TRAIL WORSE"
