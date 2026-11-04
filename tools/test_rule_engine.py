"""Tests for rule_engine — B-158.

Pinned here:

* the rule grammar fails LOUDLY on a typo (an unknown series, a bad parameter,
  an unknown key) before any bar is read — a misspelt rule that silently never
  fires would look like "no edge";
* ``crosses_above`` needs the previous bar on the other side; ``highest:n``
  excludes the current bar;
* the step state machine: strictly later bars, ``within`` expiry, ``invalidate``
  cancels an unfinished sequence and the cancelling bar does not start one,
  ``restart_on_step1``;
* NO LOOKAHEAD: the answer at bar t from the full history equals the answer
  computed on ``df.iloc[:t+1]`` — the contract the harness's ``prepare`` hook
  relies on and cannot check itself;
* the harness gives the same signals and R through ``prepare`` as through the
  ordinary per-bar ``fn`` path.

Run:  python -m pytest tools/test_rule_engine.py -q
"""
import numpy as np
import pandas as pd
import pytest

import backtest as bt
import rule_engine as re_
import scanner_templates as sc


def _walk(n=600, seed=7):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.018, n)))
    openp = close * (1 + rng.normal(0, 0.004, n))
    high = np.maximum(openp, close) * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = np.minimum(openp, close) * (1 - np.abs(rng.normal(0, 0.006, n)))
    vol = rng.integers(5e5, 2e6, n).astype(float)
    return pd.DataFrame({"open": openp, "high": high, "low": low,
                         "close": close, "volume": vol})


def _closes(vals):
    c = np.asarray(vals, dtype=float)
    return pd.DataFrame({"open": c, "high": c + 0.5, "low": c - 0.5,
                         "close": c, "volume": np.full(len(c), 1e6)})


def _rule(**kw):
    base = {"name": "t", "hypothesis": "h", "side": "long",
            "steps": [{"all": [{"lhs": "close", "op": ">", "rhs": 0}]}]}
    base.update(kw)
    return re_.compile_rule(base)


# ── grammar ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("operand", ["rsii:14", "sma", "sma:0", "sma:2.5",
                                     "ema:5:5", "close[x]", "", True])
def test_bad_operand_is_rejected(operand):
    with pytest.raises(re_.RuleError):
        _rule(steps=[{"all": [{"lhs": operand, "op": ">", "rhs": 1}]}])


@pytest.mark.parametrize("bad", [
    {"steps": []},
    {"steps": [{"all": [{"lhs": "close", "op": "=>", "rhs": 1}]}]},
    {"steps": [{"all": [{"lhs": "close", "op": ">", "rhs": 1, "x": 1}]}]},
    {"steps": [{"all": [{"lhs": "close", "op": ">", "rhs": 1}], "within": 3}]},
    {"steps": [{"all": []}]},
    {"side": "both"},
    {"colour": "red"},
    {"plan": {"stop": "atr:14", "target_r": 2}},
    {"plan": {"stop": "pct:3", "target_r": 0}},
    {"plan": {"stop": "pct:3", "target_r": 2, "time_stop": 0}},
])
def test_bad_rule_is_rejected(bad):
    with pytest.raises(re_.RuleError):
        _rule(**bad)


def test_defaults_fill_in():
    r = _rule(steps=[{"all": [{"lhs": "rsi", "op": ">", "rhs": 50},
                              {"lhs": "macd_hist", "op": ">", "rhs": 0},
                              {"lhs": "bb_upper", "op": ">", "rhs": "close"}]}])
    assert r.steps[0]["all"][0]["lhs"] == ("series", "rsi", (14.0,), 0)
    assert r.steps[0]["all"][1]["lhs"][2] == (12.0, 26.0, 9.0)


# ── operators and series ──────────────────────────────────────────────────────

def test_crosses_above_needs_previous_bar_below():
    df = _closes([9, 11, 12, 9, 10, 11])
    r = _rule(steps=[{"all": [{"lhs": "close", "op": "crosses_above", "rhs": 10}]}])
    assert list(np.flatnonzero(r.fire_mask(df))) == [1, 5]   # not 2 (already above)


def test_highest_excludes_current_bar():
    df = _closes([10, 11, 12, 13, 14])
    r = _rule(steps=[{"all": [{"lhs": "close", "op": ">", "rhs": "highest:2"}]}])
    # high = close+0.5; close 12 > max(highs of bars 0,1)=11.5 → bars 2,3,4 fire.
    assert list(np.flatnonzero(r.fire_mask(df))) == [2, 3, 4]


def test_mult_scales_rhs_and_lag_reads_back():
    df = _closes([10, 10, 16, 10])
    r = _rule(steps=[{"all": [{"lhs": "close", "op": ">", "rhs": "close[1]",
                               "mult": 1.5}]}])
    assert list(np.flatnonzero(r.fire_mask(df))) == [2]


def test_rsi_is_the_scanners_rsi():
    df = _walk(300)
    f = re_._Frame(df)
    ours = f.value(("series", "rsi", (14.0,), 0))
    theirs = sc._rsi_series(df["close"], 14).to_numpy()
    np.testing.assert_allclose(ours, theirs, equal_nan=True)


def test_warmup_nan_never_fires():
    df = _walk(300)
    r = _rule(steps=[{"all": [{"lhs": "close", "op": ">", "rhs": "sma:200"}]}])
    assert not r.fire_mask(df)[:199].any()


# ── the step machine (on hand-made masks) ─────────────────────────────────────

def _m(bits):
    return np.array([b == "1" for b in bits])


def test_two_steps_need_strictly_later_bars():
    s1, s2 = _m("1000"), _m("1000")
    assert not re_.run_sequence([s1, s2], [None, None], None).any()
    s2 = _m("0100")
    assert list(np.flatnonzero(re_.run_sequence([s1, s2], [None, None], None))) == [1]


def test_within_expires_and_bar_can_restart():
    s1, s2 = _m("10001000"), _m("00000110")
    # step 1 at 0; step 2 at 5 is 5 bars later > within 3 → expired at bar 4,
    # bar 4 restarts step 1, bar 5 completes (1 bar later).
    out = re_.run_sequence([s1, s2], [None, 3], None)
    assert list(np.flatnonzero(out)) == [5]


def test_within_expiry_without_restart_never_fires():
    s1, s2 = _m("100000"), _m("000011")
    assert not re_.run_sequence([s1, s2], [None, 3], None).any()


def test_invalidate_cancels_and_cancelling_bar_does_not_start():
    s1, s2 = _m("10100"), _m("00011")
    inv = _m("00100")
    # bar 2 is both invalidating and a step-1 bar: cancelled, NOT restarted,
    # so step 2 at bars 3-4 has nothing to complete.
    assert not re_.run_sequence([s1, s2], [None, None], inv).any()


def test_invalidate_is_inert_when_nothing_started():
    s1, s2 = _m("00100"), _m("00010")
    inv = _m("11000")
    assert list(np.flatnonzero(re_.run_sequence([s1, s2], [None, None], inv))) == [3]


def test_restart_on_step1():
    s1, s2 = _m("10100"), _m("00001")
    keep = re_.run_sequence([s1, s2], [None, 3], None, restart_on_step1=False)
    restart = re_.run_sequence([s1, s2], [None, 3], None, restart_on_step1=True)
    assert not keep.any()                         # 4 bars after bar 0: expired
    assert list(np.flatnonzero(restart)) == [4]   # 2 bars after the restart


def test_three_steps_fire_once_then_reset():
    s1, s2, s3 = _m("1000100"), _m("0100010"), _m("0010001")
    out = re_.run_sequence([s1, s2, s3], [None, None, None], None)
    assert list(np.flatnonzero(out)) == [2, 6]


# ── plan ──────────────────────────────────────────────────────────────────────

def test_pct_plan_long_and_short():
    df = _closes([100, 100, 100])
    for side, stop, tgt in (("long", 97.0, 106.0), ("short", 103.0, 94.0)):
        r = _rule(side=side, plan={"stop": "pct:3", "target_r": 2, "time_stop": 10})
        h = r.prepare(df)(2)
        assert (h["entry"], h["stop"], h["target"], h["time_stop"]) == (100, stop, tgt, 10)


def test_swing_plan_degenerate_is_dropped_not_faked():
    df = _closes([100, 100, 100])
    df["low"] = df["close"]          # the swing low IS the close: zero risk
    r = _rule(plan={"stop": "swing:3", "target_r": 2})
    h = r.prepare(df)(2)
    assert h is not None and "stop" not in h


# ── no lookahead ──────────────────────────────────────────────────────────────

PARITY_RULE = {
    "name": "parity", "hypothesis": "h", "side": "long",
    "steps": [
        {"all": [{"lhs": "close", "op": "crosses_above", "rhs": "ema:20"}]},
        {"all": [{"lhs": "rsi:14", "op": ">", "rhs": 50}],
         "any": [{"lhs": "volume", "op": ">", "rhs": "vol_sma:20", "mult": 1.1},
                 {"lhs": "macd_hist", "op": ">", "rhs": 0}],
         "within": 8},
    ],
    "invalidate": [{"lhs": "close", "op": "<", "rhs": "lowest:10"}],
    "restart_on_step1": True,
    "plan": {"stop": "atr:14:2", "target_r": 2, "time_stop": 20},
}


def test_full_history_equals_point_in_time():
    df = _walk(600)
    r = re_.compile_rule(PARITY_RULE)
    full = r.prepare(df)
    fired = [t for t in range(len(df)) if full(t)]
    assert len(fired) >= 5, "fixture too quiet to test anything"
    sample = fired + list(range(30, 600, 37))
    for t in sample:
        assert full(t) == r.prepare(df.iloc[:t + 1])(t), f"lookahead at bar {t}"


# ── harness integration ───────────────────────────────────────────────────────

def test_harness_prepare_path_matches_per_bar_path():
    data = {f"S{i}": _walk(500, seed=i) for i in range(3)}
    r = re_.compile_rule(PARITY_RULE)
    fast = re_.register(r)
    slow = fast + " (per-bar)"
    sc.SCANNERS[slow] = {"fn": r.scan, "description": "", "category": "Rule"}
    try:
        kw = dict(horizons=(5, 20), signal_mode="fresh", fill_model="market",
                  keep_trades=True)
        a = bt.backtest_scanner(fast, list(data), data.get, **kw)
        b = bt.backtest_scanner(slow, list(data), data.get, **kw)
    finally:
        sc.SCANNERS.pop(fast, None)
        sc.SCANNERS.pop(slow, None)
    assert a["n_signals"] > 0
    assert a["n_signals"] == b["n_signals"]
    assert [(x["symbol"], x["t"]) for x in a["trades"]] == \
           [(x["symbol"], x["t"]) for x in b["trades"]]


def test_logic_hash_ignores_name_and_hypothesis():
    a = re_.compile_rule(PARITY_RULE)
    b = re_.compile_rule({**PARITY_RULE, "name": "other", "hypothesis": "x"})
    c = re_.compile_rule({**PARITY_RULE, "plan": {**PARITY_RULE["plan"], "target_r": 3}})
    assert a.logic_hash() == b.logic_hash() != c.logic_hash()


# ── the runner's guards (rule_runner) ───────────────────────────────────────

import json as _json
from pathlib import Path as _Path

import rule_runner as rb


def test_runner_refuses_rule_without_hypothesis(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text(_json.dumps({k: v for k, v in PARITY_RULE.items()
                              if k != "hypothesis"}), encoding="utf-8")
    assert rb.main([str(p)]) == 2
    assert "hypothesis" in capsys.readouterr().err


def test_runner_check_compiles_without_logging(tmp_path, monkeypatch):
    log = tmp_path / "runs.jsonl"
    monkeypatch.setattr(rb, "RUN_LOG", log)
    p = tmp_path / "r.json"
    p.write_text(_json.dumps(PARITY_RULE), encoding="utf-8")
    assert rb.main([str(p), "--check"]) == 0
    assert not log.exists()


def test_shipped_example_rule_compiles():
    r = re_.load_rule(_Path(__file__).parent / "rules" / "ema20_reclaim_rsi50.json")
    assert r.hypothesis and r.plan


def test_variant_count_is_by_logic_and_survives_a_torn_line(tmp_path):
    log = tmp_path / "runs.jsonl"
    rb.append_log({"logic_hash": "a"}, log)
    rb.append_log({"logic_hash": "a"}, log)      # same rule re-run: not a variant
    rb.append_log({"logic_hash": "b"}, log)
    with log.open("a", encoding="utf-8") as fh:
        fh.write('{"logic_hash": "c"\n')         # torn write
    assert rb.distinct_rules(rb.read_log(log)) == 2
    assert "0.0250" in rb.multiple_testing_note(2)
