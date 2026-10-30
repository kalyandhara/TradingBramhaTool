"""Tests for fld_confluence (FLD-1). Offline, synthetic series only."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

import fld_confluence as fc


def _df(close, start="2023-01-02"):
    close = np.asarray(close, float)
    idx = pd.bdate_range(start, periods=len(close))
    return pd.DataFrame({"open": close, "high": close * 1.005, "low": close * 0.995,
                         "close": close, "volume": 1}, index=idx)


def _cyclic(n=700, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    s = (100 + 8 * np.sin(2 * np.pi * t / 80) + 4 * np.sin(2 * np.pi * t / 40)
         + 12 * np.sin(2 * np.pi * t / 160) + rng.normal(0, 0.6, n).cumsum() * 0.3)
    return _df(s)


# ── FLD itself ────────────────────────────────────────────────────────────────
def test_fld_is_price_shifted_half_cycle_and_forward_is_last_half():
    df = _df(np.arange(1, 101, dtype=float))
    known, fwd = fc.fld_series(df, 20)
    assert known.iloc[10] == df["close"].iloc[0] and np.isnan(known.iloc[9])
    assert list(fwd.values) == list(df["close"].iloc[-10:].values)
    assert fwd.index[0] > df.index[-1] and len(fwd) == 10


def test_cross_target_formula():
    # rise to 120, fall through the FLD: target = cross - (peak - cross)
    close = np.r_[np.linspace(100, 120, 21), np.linspace(119, 90, 30)]
    p = fc._prep(close, 20)
    down = [(i, t) for i, t, d in zip(p["x_idx"], p["x_tgt"], p["x_dir"]) if d < 0]
    assert down, "expected a down-cross"
    i, tgt = down[0]
    peak = close[max(0, i - 10):i].max()
    assert tgt == pytest.approx(close[i] - (peak - close[i]))


# ── outcome resolution ──────────────────────────────────────────────────────
def test_outcome_hit_miss_and_open():
    close = np.array([100, 101, 103, 106, 99, 98], float)
    hi, lo = close + 0.5, close - 0.5
    assert fc._outcome(close, hi, lo, 0, 1, 105, 97, 10) == (1, 3)
    assert fc._outcome(close, hi, lo, 0, 1, 200, 100.5, 10) == (0, 4)     # stopped at bar 4
    assert fc._outcome(close, hi, lo, 0, 1, 200, 50, 10) == (None, None)  # still open
    assert fc._outcome(close, hi, lo, 0, 1, 200, 50, 3) == (0, 3)         # timed out
    assert fc._outcome(close, hi, lo, 0, -1, 98.5, 110, 10) == (1, 4)


# ── no lookahead ────────────────────────────────────────────────────────────
def test_snapshots_do_not_read_the_future():
    df = _cyclic()
    full, _ = fc.history(df)
    cut = 520
    part, _ = fc.history(df.iloc[:cut + 1])
    full_by_t = {r["t"]: r for r in full}
    checked = 0
    for r in part:
        f = full_by_t[r["t"]]
        for k in ("D", "TC", "PA", "target", "stop", "P", "side"):
            assert f[k] == pytest.approx(r[k]), (r["t"], k)
        checked += 1
    assert checked > 10


def test_p_hit_counts_only_outcomes_resolved_before_t():
    rows, _ = fc.history(_cyclic())
    for r in rows:
        prior = [x for x in rows if x["resolve_bar"] is not None and x["resolve_bar"] < r["t"]]
        hits = sum(x["hit"] for x in prior)
        expect = (hits + fc.PRIOR_STRENGTH * fc.PRIOR_HIT) / (len(prior) + fc.PRIOR_STRENGTH)
        assert r["p_hit"] == pytest.approx(expect)


# ── score ───────────────────────────────────────────────────────────────────
def _with_setup():
    """A cut of the synthetic series whose last bar has a target ahead."""
    df = _cyclic()
    for cut in range(400, 700, 7):
        if fc.score(df.iloc[:cut]) is not None:
            return df.iloc[:cut]
    raise AssertionError("no setup found in synthetic series")


def test_score_shape_and_ev_sides():
    s = fc.score(_with_setup())
    assert s is not None and s["calibrated"] is False
    assert 0 < s["P"] < 1 and s["side"] in (1, -1)
    assert (s["target"] - s["price"]) * s["side"] > 0                 # target is ahead
    assert s["EV"] == pytest.approx(s["P"] * s["reward"] - (1 - s["P"]) * s["risk"])
    assert (s["ev_long"] is None) != (s["ev_short"] is None)


def test_score_needs_history():
    assert fc.score(_df(np.linspace(100, 110, 100))) is None
    assert fc.score(None) is None


def test_model_beta_is_used():
    df = _with_setup()
    a = fc.score(df)
    b = fc.score(df, {"beta": [3.0, 0, 0, 0, 0]})
    assert b["calibrated"] and b["P"] == pytest.approx(float(fc._sigmoid(3.0)))
    assert a["target"] == b["target"]                                 # only P/EV move


# ── calibration ─────────────────────────────────────────────────────────────
def test_fit_logistic_recovers_direction():
    rng = np.random.default_rng(1)
    X = np.c_[np.ones(4000), rng.normal(size=(4000, 2))]
    y = (rng.random(4000) < fc._sigmoid(X @ np.array([0.2, 2.0, -1.0]))).astype(float)
    b = fc.fit_logistic(X, y)
    assert b[1] > 1.2 and b[2] < -0.5


def test_reliability_buckets():
    P = np.array([0.05, 0.15, 0.15, 0.95])
    y = np.array([0, 1, 0, 1])
    rel = fc.reliability(P, y)
    assert [r["n"] for r in rel] == [1, 2, 1]
    assert rel[1]["actual"] == 0.5


def test_calibrate_writes_model_and_refuses_thin_data(tmp_path):
    frames = {f"S{i}": _cyclic(seed=i) for i in range(12)}
    out = tmp_path / "m.json"
    res = fc.calibrate(frames, label="synthetic", min_rows=50, save_to=out)
    assert res["ok"] and res["n"] >= 50 and len(res["beta"]) == 5
    saved = json.loads(out.read_text())
    assert saved["universe"] == "synthetic" and fc.load_model(out)["beta"] == saved["beta"]
    thin = fc.calibrate({"A": _cyclic()}, min_rows=10_000, save_to=None)
    assert not thin["ok"] and "at least" in thin["reason"]


def test_load_model_rejects_bad_files(tmp_path):
    p = tmp_path / "m.json"
    assert fc.load_model(p) is None
    p.write_text('{"beta": [1, 2]}')
    assert fc.load_model(p) is None
