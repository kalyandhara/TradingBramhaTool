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


def test_merge_badge_confirms_an_edge_only_when_the_fresh_panel_agrees():
    rates = {"detectors": {"liquidity_sweep_bull": {"label": "ORDINARY"}, "gap_up": {"label": "EDGE"}}}
    edge = fw.label(_r(0.006, 0.001))
    out = fw.merge_badge(rates, edge, fw.label(_r(0.006, 0.001)))
    d = out["detectors"]["liquidity_sweep_bull"]
    assert d["label"] == "EDGE" and d["confirm_label"] == "EDGE" and d["confirmed"] is True
    assert d["window"] == "full history (B-186d)"
    assert out["detectors"]["gap_up"] == {"label": "EDGE"}
    out2 = fw.merge_badge(rates, edge, fw.label(_r(0.006, 0.10)))
    assert out2["detectors"]["liquidity_sweep_bull"]["confirmed"] is False


def test_ordinary_main_label_carries_no_confirmation_flag():
    """As tour_base_rates.merge_confirmation: confirmation only applies to EDGE/INVERTED,
    so an ORDINARY card never shows 'not confirmed on a fresh panel'."""
    rates = {"detectors": {"liquidity_sweep_bull": {}}}
    out = fw.merge_badge(rates, fw.label(_r(0.0048, 0.10)), fw.label(_r(0.003, 0.35)))
    assert out["detectors"]["liquidity_sweep_bull"]["confirmed"] is None
