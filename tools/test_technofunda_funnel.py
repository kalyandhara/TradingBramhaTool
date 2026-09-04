"""Tests for technofunda_funnel — the B-38 delete funnel.

Runs two ways so it fits the repo's "__main__ probe" style AND pytest:
    py -3 tools/test_technofunda_funnel.py     # prints PASS/FAIL, exits nonzero on fail
    pytest tools/test_technofunda_funnel.py    # standard collection

Pure, deterministic, no network: every filter is fed a hand-built context so the
pass/delete/caveat decision is pinned. Price legs use tiny synthetic frames.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import technofunda_funnel as tf

TH = tf.Thresholds()


# ── helpers ───────────────────────────────────────────────────────────────────
def _ctx(**kw):
    base = dict(symbol="T", deep={}, flags=None, price=None, close=None,
                volume=None, bench_ret_12m=None, sector_ret_12m=None)
    base.update(kw)
    return base


def _price(closes, vols=None):
    n = len(closes)
    idx = pd.date_range("2022-01-01", periods=n, freq="B")
    v = vols if vols is not None else np.full(n, 1e5)
    c = np.asarray(closes, float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": v}, index=idx)


def _v(oc):   # verdict shortcut
    return oc.verdict


# ── F1 growth ─────────────────────────────────────────────────────────────────
def test_f1_cagr_pass_and_fail():
    assert _v(tf.f1_growth(_ctx(deep={"revenue_cagr_3y": 20, "profit_cagr_3y": 25}), TH, True)) == tf.PASS
    assert _v(tf.f1_growth(_ctx(deep={"revenue_cagr_3y": 3, "profit_cagr_3y": 4}), TH, True)) == tf.DELETE


def test_f1_fading_turned_negative_deletes_even_if_cagr_clears():
    q = [{"profit_yoy": -8}, {"profit_yoy": -3}, {"profit_yoy": 20}, {"profit_yoy": 25}]
    d = {"revenue_cagr_3y": 20, "profit_cagr_3y": 25, "quarters": q}
    assert _v(tf.f1_growth(_ctx(deep=d), TH, True)) == tf.DELETE


def test_f1_quarterly_fallback_and_strict_miss():
    q = [{"profit_yoy": 10}] * 6
    assert _v(tf.f1_growth(_ctx(deep={"quarters": q}), TH, True)) == tf.PASS
    # no cagr, too few quarters → deleted under strict, caveat under lenient
    assert _v(tf.f1_growth(_ctx(deep={}), TH, True)) == tf.DELETE
    assert _v(tf.f1_growth(_ctx(deep={}), TH, False)) == tf.CAVEAT


# ── F2 cash ───────────────────────────────────────────────────────────────────
def test_f2_cfo_pat_ratio_gate():
    assert _v(tf.f2_cash(_ctx(deep={"cfo_pat_ratio": 1.1, "cfo_pat_years": 5}), TH, True)) == tf.PASS
    assert _v(tf.f2_cash(_ctx(deep={"cfo_pat_ratio": 0.4, "cfo_pat_years": 5}), TH, True)) == tf.DELETE


def test_f2_fcf_proxy_fallback():
    assert _v(tf.f2_cash(_ctx(deep={"fcf": 100, "fcf_negative_streak": 0}), TH, True)) == tf.PASS
    assert _v(tf.f2_cash(_ctx(deep={"fcf": -5, "fcf_negative_streak": 2}), TH, True)) == tf.DELETE


# ── F3 leverage ───────────────────────────────────────────────────────────────
def test_f3_deletes_on_evidence_caveat_when_unknown():
    assert _v(tf.f3_leverage(_ctx(deep={"debt_to_equity": 2.5, "interest_coverage": 1.0}), TH, True)) == tf.DELETE
    assert _v(tf.f3_leverage(_ctx(deep={"debt_to_equity": 0.3, "interest_coverage": 9}), TH, True)) == tf.PASS
    # uncomputable leverage must NOT empty the universe — caveat, not delete
    assert _v(tf.f3_leverage(_ctx(deep={}), TH, True)) == tf.CAVEAT


# ── F4 returns ────────────────────────────────────────────────────────────────
def test_f4_gates_both_roce_and_roe():
    assert _v(tf.f4_returns(_ctx(deep={"roce": 22, "roe": 20}), TH, True)) == tf.PASS
    assert _v(tf.f4_returns(_ctx(deep={"roce": 22, "roe": 8}), TH, True)) == tf.DELETE   # ROE fails
    assert _v(tf.f4_returns(_ctx(deep={"roce": 9, "roe": 20}), TH, True)) == tf.DELETE   # ROCE fails


# ── F5 governance ─────────────────────────────────────────────────────────────
def test_f5_critical_flag_deletes_notchecked_is_caveat():
    crit = {"flags": [{"state": "FLAG", "severity": "critical".upper(), "label": "Pledge"}]}
    assert _v(tf.f5_governance(_ctx(flags=crit), TH, True)) == tf.DELETE
    only_unchecked = {"flags": [{"state": "NOT_CHECKED", "severity": "CRITICAL", "label": "Auditor"}]}
    assert _v(tf.f5_governance(_ctx(flags=only_unchecked), TH, True)) == tf.CAVEAT
    watch = {"flags": [{"state": "FLAG", "severity": "watch", "label": "Dilution"}]}
    assert _v(tf.f5_governance(_ctx(flags=watch), TH, True)) == tf.CAVEAT
    clean = {"flags": [{"state": "CLEAN", "severity": "CRITICAL", "label": "Pledge"}]}
    assert _v(tf.f5_governance(_ctx(flags=clean), TH, True)) == tf.PASS


# ── F6 / F7 / F8 price legs ───────────────────────────────────────────────────
def test_f6_200dma():
    up = _price(list(np.linspace(50, 150, 260)))      # rising → last > SMA200
    dn = _price(list(np.linspace(150, 50, 260)))      # falling → last < SMA200
    assert _v(tf.f6_trend(tf.build_context("T", price=up), TH, True)) == tf.PASS
    assert _v(tf.f6_trend(tf.build_context("T", price=dn), TH, True)) == tf.DELETE


def test_f7_relative_strength():
    strong = _price(list(100 * np.exp(np.linspace(0, 0.5, 300))))   # +65% 12m
    weak = _price(list(100 * np.exp(np.linspace(0, 0.02, 300))))    # +2% 12m
    assert _v(tf.f7_rs(tf.build_context("T", price=strong, bench_ret_12m=0.10), TH, True)) == tf.PASS
    assert _v(tf.f7_rs(tf.build_context("T", price=weak, bench_ret_12m=0.10), TH, True)) == tf.DELETE


def test_f8_accumulation_up_vs_down_volume():
    # tight base, more volume on up days → pass; distribution → delete
    closes = [100 + (0.5 if i % 2 else -0.4) for i in range(30)]
    up_vol = np.array([1.6e5 if closes[i] - closes[i-1] > 0 else 0.6e5 for i in range(30)])
    dn_vol = np.array([0.6e5 if closes[i] - closes[i-1] > 0 else 1.6e5 for i in range(30)])
    assert _v(tf.f8_accumulation(tf.build_context("T", price=_price(closes, up_vol)), TH, True)) == tf.PASS
    assert _v(tf.f8_accumulation(tf.build_context("T", price=_price(closes, dn_vol)), TH, True)) == tf.DELETE


# ── funnel orchestration ──────────────────────────────────────────────────────
def test_run_funnel_short_circuits_and_counts():
    fr = tf.run_funnel(tf._demo_contexts())
    assert fr.n_in == 5 and fr.n_out == 1
    assert fr.survivors == ["ALPHAOK"]
    res = fr.results
    assert res["BETAPLEDGE"].deleted_at == "F5"
    assert res["DELTADEBT"].deleted_at == "F3"
    assert res["EPSILONFLAT"].deleted_at == "F1"
    assert res["GAMMADOWN"].deleted_at == "F6"
    # short-circuit: a deleted name records exactly one DELETE outcome
    for r in res.values():
        if not r.survived:
            assert sum(1 for o in r.outcomes if o.verdict == tf.DELETE) == 1


def test_strict_vs_lenient_missing_data():
    empty = _ctx(deep={}, flags=None)   # nothing computable
    assert tf.run_one(empty, TH, strict=True).survived is False
    # lenient: every filter that can't evaluate becomes a caveat, so it survives
    len_res = tf.run_one(empty, TH, strict=False)
    assert len_res.survived is True and len_res.caveats


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
