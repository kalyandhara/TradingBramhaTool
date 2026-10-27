"""Tests for the B-186d label rule and badge merge."""
import sweep_full_window_study as fw


def _r(mean20, p20, thirds=(1, 1, -1), n=500, syms=100):
    return {"mean20": mean20, "p20": p20, "thirds": list(thirds), "n_events": n, "n_symbols": syms}


def test_edge_needs_bonferroni_over_20():
    assert fw.label(_r(0.005, 0.002))["label"] == "EDGE"          # 0.04 < 0.05
    assert fw.label(_r(0.005, 0.003))["label"] == "ORDINARY"      # 0.06
    assert fw.label(_r(0.005, 0.002))["p20_bonf"] == 0.04


def test_inverted_and_thirds_and_floors():
    assert fw.label(_r(-0.005, 0.001, (-1, -1, 1)))["label"] == "INVERTED"
    assert fw.label(_r(0.005, 0.001, (1, -1, -1)))["label"] == "ORDINARY"
    assert fw.label(_r(0.005, 0.001, n=99))["label"] == "TOO_FEW"
    assert fw.label(_r(0.005, 0.001, syms=29))["label"] == "TOO_FEW"


def test_merge_badge_sets_confirmed_only_on_fresh_edge():
    rates = {"detectors": {"liquidity_sweep_bull": {"label": "ORDINARY"}, "gap_up": {"label": "EDGE"}}}
    main = fw.label(_r(0.0048, 0.10))
    fresh = fw.label(_r(0.006, 0.001))
    out = fw.merge_badge(rates, main, fresh)
    d = out["detectors"]["liquidity_sweep_bull"]
    # the pre-registration: `confirmed` is the fresh panel's EDGE, whatever the main label
    assert d["label"] == "ORDINARY" and d["confirm_label"] == "EDGE" and d["confirmed"] is True
    assert d["window"] == "full history (B-186d)"
    assert out["detectors"]["gap_up"] == {"label": "EDGE"}
    out2 = fw.merge_badge(rates, main, fw.label(_r(0.006, 0.10)))
    assert out2["detectors"]["liquidity_sweep_bull"]["confirmed"] is False
