"""B-132's arms change the stop and nothing else.

Run:  python -m pytest tools/test_abcd_stop_study.py -q
"""
import numpy as np
import pandas as pd

import abcd_stop_study as s
import scanner_templates as sc


def _frame(n=80):
    rng = np.random.default_rng(1)
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"open": c, "high": c + 1.5, "low": c - 1.5, "close": c,
                         "volume": np.full(n, 1e5)})


CARD = {"pattern_type": "Harmonic AB=CD", "entry": 100.0, "stop": 99.5,
        "target": 106.0, "time_stop": 10, "direction": "bullish"}


def test_control_keeps_the_card_and_arms_only_move_the_stop(monkeypatch):
    df = _frame()
    monkeypatch.setattr(s, "_abcd", lambda d: dict(CARD))
    atr = float(sc._atr_series(df, 14).iloc[-1])
    assert s._arm(None)(df) == CARD
    for k in (1.0, 2.0):
        hit = s._arm(k)(df)
        assert hit["stop"] == round(100.0 - k * atr, 2)
        assert {key: v for key, v in hit.items() if key != "stop"} == \
               {key: v for key, v in CARD.items() if key != "stop"}


def test_no_hit_stays_no_hit(monkeypatch):
    monkeypatch.setattr(s, "_abcd", lambda d: None)
    assert s._arm(1.0)(_frame()) is None


def test_plan_percent_is_r_times_risk_over_entry():
    assert s._pct({"entry_px": 100.0, "stop": 98.0, "r": 1.5}) == 3.0
    assert s._pct({"entry_px": 100.0, "stop": 99.5, "r": -1.0}) == -0.5


def test_panel_is_disjoint_from_b129r():
    import harmonic_bull_remeasure as b129r
    assert s.PANEL[0] >= b129r.N_SYMBOLS


# ── the shipped change (B-132 decided SHIP A2) ────────────────────────────────
def _fake(pattern, stop):
    return {"pattern": pattern, "direction": "bullish", "age_bars": 1,
            "ratios": {"BC/AB": 0.618},
            "trade": {"entry": 100.0, "stop": stop, "targets": [103.0, 106.0, 110.0],
                      "risk": 100.0 - stop, "rr_to_t2": round(6.0 / (100.0 - stop), 2)}}


def test_scanner_ships_the_tested_abcd_stop(monkeypatch):
    import harmonic_patterns as hp
    df = _frame()
    monkeypatch.setattr(hp, "detect_last_pattern", lambda d: _fake("AB=CD", 99.5))
    card = sc.scan_harmonic_reversal(df)
    atr = float(sc._atr_series(df, 14).iloc[-1])
    assert sc.ABCD_STOP_ATR == 2.0
    assert card["stop"] == round(100.0 - 2.0 * atr, 2)


def test_gate_still_uses_the_original_stop(monkeypatch):
    """The R:R gate defines the measured signal set — it must not see the wide stop."""
    import harmonic_patterns as hp
    df = _frame()
    monkeypatch.setattr(hp, "detect_last_pattern", lambda d: _fake("AB=CD", 99.5))
    assert sc.scan_harmonic_reversal(df) is not None          # 6/0.5 = 12 >= 1.5


def test_xabcd_keeps_its_x_stop(monkeypatch):
    import harmonic_patterns as hp
    monkeypatch.setattr(hp, "detect_last_pattern", lambda d: _fake("Gartley", 97.0))
    assert sc.scan_harmonic_reversal(_frame())["stop"] == 97.0


# ── B-132r: the tier re-check reuses B-129r's rule, not a copy ────────────────
def test_tier_recheck_uses_b129r_rule_and_panel():
    import harmonic_bull_remeasure as b129r
    import harmonic_tier_recheck as rc
    assert rc.hb is b129r                                     # decide/clustered/summarise imported
    assert b129r.N_SYMBOLS == 300 and s.PANEL[0] >= b129r.N_SYMBOLS   # B-132 never saw these


def test_tier_recheck_plan_pct_matches_b132():
    import harmonic_tier_recheck as rc
    d = rc.plan_pct([{"entry_px": 100.0, "stop": 98.0, "r": 1.5, "outcome": "target"},
                     {"entry_px": 100.0, "stop": 99.5, "r": -1.0, "outcome": "stop"}])
    assert d["mean_plan_pct"] == 1.25 and d["target_rate"] == 0.5 and d["stop_rate"] == 0.5
