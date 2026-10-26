"""Tests for event_study.py (policy event-study engine), offline.

The engine is a measuring instrument, so the tests are about it measuring the
right thing and nothing else:

  * events are validated, not trusted — an unknown label or a duplicate date is
    an error, never a silently different sample;
  * a planted effect must be found and an unplanted control must not;
  * the null must be reproducible from its seed and must never draw a day that
    sits next to a real event.
"""
import textwrap

import numpy as np
import pandas as pd
import pytest

import event_study as es


HEADER = "date,event_type,label,scheduled,time_ist,source_url,notes\n"


def _csv(tmp_path, body):
    p = tmp_path / "events.csv"
    p.write_text(HEADER + textwrap.dedent(body).strip() + "\n", encoding="utf-8")
    return p


# ── events ────────────────────────────────────────────────────────────────────

def test_load_events_filters_and_sorts(tmp_path):
    p = _csv(tmp_path, """
        2020-02-06,mpc,hold,1,11:45,u,
        2020-02-01,budget,full,1,11:00,u,
        2019-12-05,mpc,hold,1,11:45,u,
    """)
    ev = es.load_events(p, types=["mpc"])
    assert list(ev["event_type"]) == ["mpc", "mpc"]
    assert list(ev["date"]) == [pd.Timestamp("2019-12-05"), pd.Timestamp("2020-02-06")]


def test_load_events_drops_unscheduled_by_default(tmp_path):
    p = _csv(tmp_path, """
        2020-03-27,mpc,cut,0,10:00,u,off-cycle
        2020-02-06,mpc,hold,1,11:45,u,
    """)
    assert len(es.load_events(p)) == 1
    allev = es.load_events(p, scheduled_only=False)
    assert len(allev) == 2
    assert allev["scheduled"].tolist() == [1, 0]


def test_load_events_rejects_unknown_label(tmp_path):
    p = _csv(tmp_path, "2020-02-06,mpc,pause,1,11:45,u,\n")
    with pytest.raises(ValueError, match="pause"):
        es.load_events(p)


def test_load_events_rejects_duplicate(tmp_path):
    p = _csv(tmp_path, """
        2020-02-06,mpc,hold,1,11:45,u,
        2020-02-06,mpc,cut,1,11:45,u,
    """)
    with pytest.raises(ValueError, match="duplicate"):
        es.load_events(p)


# ── prices, returns, sessions ────────────────────────────────────────────────

def _yf_frame(tickers, idx, closes):
    """A frame shaped like yfinance.download(group_by="ticker"): (ticker, field)."""
    cols = pd.MultiIndex.from_product([tickers, ["Open", "High", "Low", "Close", "Volume"]])
    df = pd.DataFrame(np.nan, index=idx, columns=cols)
    for t, c in zip(tickers, closes):
        df[(t, "Close")] = c
    return df


def test_load_closes_flattens_multiindex_and_omits_empty(tmp_path):
    idx = pd.bdate_range("2024-01-01", periods=5)
    stub = lambda tickers, start: _yf_frame(["A", "B"], idx, [np.arange(5.0) + 1, np.nan])
    closes, omitted = es.load_closes(["A", "B"], "2024-01-01", download=stub,
                                     cache_dir=tmp_path, min_obs=1)
    assert list(closes.columns) == ["A"]
    assert omitted == ["B"]
    assert closes["A"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_load_closes_omits_short_series(tmp_path):
    """^CNXMEDIA on Yahoo is one bar: too short to estimate anything, so omitted."""
    idx = pd.bdate_range("2024-01-01", periods=300)
    short = np.full(300, np.nan); short[-1] = 5.0
    stub = lambda tickers, start: _yf_frame(["A", "M"], idx, [np.arange(300.0) + 1, short])
    closes, omitted = es.load_closes(["A", "M"], "2024-01-01", download=stub, cache_dir=tmp_path)
    assert omitted == ["M"]


def test_load_closes_uses_cache(tmp_path):
    idx = pd.bdate_range("2024-01-01", periods=5)
    stub = lambda tickers, start: _yf_frame(["A"], idx, [np.arange(5.0) + 1])
    es.load_closes(["A"], "2024-01-01", download=stub, cache_dir=tmp_path, min_obs=1,
                   today=pd.Timestamp("2024-01-06"))

    def boom(tickers, start):
        raise AssertionError("cache should have been used")
    closes, _ = es.load_closes(["A"], "2024-01-01", download=boom, cache_dir=tmp_path,
                               min_obs=1, today=pd.Timestamp("2024-01-06"))
    assert closes["A"].iloc[-1] == 5.0


def test_load_closes_refetches_stale_cache(tmp_path):
    idx = pd.bdate_range("2024-01-01", periods=5)
    calls = []
    def stub(tickers, start):
        calls.append(1)
        return _yf_frame(["A"], idx, [np.arange(5.0) + 1])
    es.load_closes(["A"], "2024-01-01", download=stub, cache_dir=tmp_path, min_obs=1,
                   today=pd.Timestamp("2024-01-06"))
    es.load_closes(["A"], "2024-01-01", download=stub, cache_dir=tmp_path, min_obs=1,
                   today=pd.Timestamp("2024-03-01"))
    assert len(calls) == 2


def test_pair_returns_inner_joins_gaps():
    idx = pd.bdate_range("2024-01-01", periods=5)
    closes = pd.DataFrame({"^NSEI": [100.0, 101, 102, 104, 105],
                           "S": [50.0, 51, np.nan, 53, 54]}, index=idx)
    pr = es.pair_returns(closes, "S")
    assert idx[2] not in pr.index
    assert pr.loc[idx[3], "r"] == pytest.approx(np.log(53 / 51))
    assert pr.loc[idx[3], "m"] == pytest.approx(np.log(104 / 101))
    assert len(pr) == 3


def test_snap_saturday_to_monday():
    idx = pd.bdate_range("2020-01-27", "2020-02-07")
    pos, snapped = es.snap_to_sessions(pd.Series(pd.to_datetime(["2020-02-01", "2020-02-06"])), idx)
    assert idx[pos[0]] == pd.Timestamp("2020-02-03") and snapped[0]
    assert idx[pos[1]] == pd.Timestamp("2020-02-06") and not snapped[1]


def test_snap_after_last_session_is_minus_one():
    idx = pd.bdate_range("2020-01-27", "2020-02-07")
    pos, _ = es.snap_to_sessions(pd.Series(pd.to_datetime(["2020-03-01"])), idx)
    assert pos[0] == -1


# ── abnormal returns ─────────────────────────────────────────────────────────

def _pair(n=400, beta=1.5, alpha=0.001, plant=None, seed=0):
    """Synthetic pair returns: r = alpha + beta*m + small noise, optional plant {pos: amount}."""
    rng = np.random.default_rng(seed)
    m = rng.normal(0, 0.01, n)
    r = alpha + beta * m + rng.normal(0, 0.0005, n)
    for p, amt in (plant or {}).items():
        r[p] += amt
    idx = pd.bdate_range("2015-01-01", periods=n)
    return pd.DataFrame({"r": r, "m": m}, index=idx)


def test_market_model_recovers_beta():
    pr = _pair(plant={300: 0.03})
    ar = es.market_model_ar(pr, 300)
    assert ar.loc[0] == pytest.approx(0.03, abs=0.003)
    assert abs(ar.loc[-3]) < 0.003          # an unplanted day is ~0 once beta is removed


def test_market_model_too_short_returns_none():
    pr = _pair(n=400)
    assert es.market_model_ar(pr, 110) is None   # only 100 estimation rows exist


def test_adjusted_model_is_sector_minus_market():
    pr = _pair(plant={300: 0.03})
    ar = es.market_model_ar(pr, 300, model="adjusted")
    assert ar.loc[0] == pytest.approx(pr["r"].iloc[300] - pr["m"].iloc[300])


def _closes_from(pr_by_ticker, market_m):
    """Price levels whose log returns are exactly the given returns."""
    idx = market_m.index
    out = {es.MARKET: 1000 * np.exp(np.r_[0, np.cumsum(market_m.to_numpy())])}
    for t, r in pr_by_ticker.items():
        out[t] = 100 * np.exp(np.r_[0, np.cumsum(r.to_numpy())])
    full = idx.insert(0, idx[0] - pd.offsets.BDay(1))
    return pd.DataFrame(out, index=full)


def _events(dates, etype="mpc", label="hold"):
    return pd.DataFrame({"date": pd.to_datetime(dates), "event_type": etype,
                         "label": label, "scheduled": 1})


def test_event_near_end_drops_only_drift():
    pr = _pair(n=400)
    closes = _closes_from({"S": pr["r"]}, pr["m"])
    ev = _events([pr.index[397]])
    t = es.event_ar_table(closes, ev, sectors=["S"])
    s = t[t["ticker"] == "S"]
    assert "day" in set(s["window"])
    assert "drift" not in set(s["window"])


def test_overlapping_events_both_kept():
    pr = _pair(n=400)
    closes = _closes_from({"S": pr["r"]}, pr["m"])
    ev = _events([pr.index[300], pr.index[308]])
    t = es.event_ar_table(closes, ev, sectors=["S"])
    day = t[(t["ticker"] == "S") & (t["window"] == "day")]
    assert len(day) == 2


def test_event_table_market_rows_are_raw_returns():
    pr = _pair(n=400)
    closes = _closes_from({"S": pr["r"]}, pr["m"])
    ev = _events([pr.index[300]])
    t = es.event_ar_table(closes, ev, sectors=["S"])
    mk = t[(t["ticker"] == es.MARKET) & (t["window"] == "day")]
    assert mk["car"].iloc[0] == pytest.approx(pr["m"].iloc[300])
    assert not mk["snapped"].iloc[0]


# ── nulls, corrections, intervals ────────────────────────────────────────────

def test_candidates_exclude_window_and_months():
    idx = pd.bdate_range("2012-01-02", periods=1500)
    ev = np.array([400, 800])
    cand = es.candidate_positions(idx, ev, exclude=10)
    assert not any(abs(c - e) <= 10 for c in cand for e in ev)
    assert cand.min() >= 250 and cand.max() <= len(idx) - 21
    feb = es.candidate_positions(idx, ev, exclude=10, months={2})
    assert len(feb) > 0 and all(idx[c].month == 2 for c in feb)
    y = es.candidate_positions(idx, ev, exclude=10, years={2014})
    assert all(idx[c].year == 2014 for c in y)


def test_date_null_deterministic():
    cand = np.arange(300, 1000)
    f = lambda pos: float(pos.mean())
    a = es.date_null(f, cand, 20, draws=200, seed=7)
    b = es.date_null(f, cand, 20, draws=200, seed=7)
    assert np.array_equal(a, b) and len(a) == 200


def test_date_null_draws_without_replacement():
    seen = []
    es.date_null(lambda pos: seen.append(pos) or 0.0, np.arange(300, 1000), 20, draws=50, seed=1)
    assert all(len(set(p)) == 20 for p in seen)


def test_p_greater_formula():
    assert es.p_greater(5.0, np.array([1.0, 2.0, 6.0])) == pytest.approx(0.5)


def test_label_permutation_preserves_sizes():
    vals = np.array([1.0, 2, 3, 4, 5, 6, 7])
    labs = np.array(["cut"] * 4 + ["hike"] * 3)
    real, null = es.label_permutation(vals, labs, draws=300, seed=3)
    assert real == pytest.approx(np.mean([1, 2, 3, 4]) - np.mean([5, 6, 7]))
    # With 4 "cut" and 3 "hike" drawn from 1..7, d = a - b and 4a + 3b = 28 give
    # sum_cut = 4a = 4(3d + 28)/7. Sizes preserved <=> sum_cut is a whole number
    # between 1+2+3+4 and 4+5+6+7 on every draw.
    sum_cut = 4 * (3 * null + 28) / 7
    assert np.allclose(sum_cut, np.round(sum_cut))
    assert sum_cut.min() >= 10 - 1e-9 and sum_cut.max() <= 22 + 1e-9


def test_holm_matches_hand():
    assert es.holm([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_bh_matches_hand():
    assert es.bh([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.02, 0.04, 0.04, 0.02])


def test_bootstrap_ci_brackets_mean():
    v = np.random.default_rng(0).normal(1.0, 0.1, 200)
    lo, hi = es.bootstrap_ci(v, reps=500)
    assert lo < v.mean() < hi and hi - lo < 0.05


# ── run_study: planted effects must be found, unplanted must not ─────────────

FAST = dict(draws=500, boot=200)


def _synthetic(n=3000, events=40, vol_plant=False, dir_plant=False, seed=11,
               n_hike=12, n_cut=12):
    """13 index series on n business days; `events` MPC dates spread across the
    sample. vol_plant: NIFTY +/-3 sigma and sector idiosyncratic noise x3 on
    event days. dir_plant: basket +2 sigma on cut days, -2 sigma on hike days."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-04", periods=n + 1)
    m = rng.normal(0.0003, 0.01, n)
    ev_pos = np.linspace(300, n - 30, events).astype(int)
    labels = (["cut"] * n_cut + ["hike"] * n_hike + ["hold"] * events)[:events]
    labels = list(rng.permutation(labels))
    if vol_plant:
        m[ev_pos] += rng.choice([-1, 1], events) * 0.03
    rets = {es.MARKET: m}
    for i, t in enumerate(es.SECTORS):
        beta = 0.8 + 0.05 * i
        idio = rng.normal(0, 0.006, n)
        if vol_plant:
            idio[ev_pos] *= 3
        r = beta * m + idio
        if dir_plant and t in es.BASKET:
            for p, lab in zip(ev_pos, labels):
                if lab == "cut":
                    r[p] += 2 * 0.006
                elif lab == "hike":
                    r[p] -= 2 * 0.006
        rets[t] = r
    closes = pd.DataFrame({t: 100 * np.exp(np.r_[0, np.cumsum(r)]) for t, r in rets.items()},
                          index=idx)
    ev = pd.DataFrame({"date": idx[ev_pos + 1], "event_type": "mpc", "label": labels,
                       "scheduled": 1, "time_ist": "10:00", "source_url": "", "notes": ""})
    return closes, ev


def _row(result, section, test, set_="mpc"):
    return next(r for r in result[section] if r["test"] == test and r["set"] == set_)


def test_planted_volatility_detected():
    closes, ev = _synthetic(vol_plant=True)
    res = es.run_study(closes, ev, es.StudyConfig(**FAST))
    for t in ("P1", "P2"):
        r = _row(res, "primary", t)
        assert r["p"] < 0.01 and r["ratio"] > 1.3, r
    assert any(v.startswith("PROMOTE: mpc policy days are volatility events") for v in res["verdicts"])


def test_unplanted_control_not_detected():
    closes, ev = _synthetic(vol_plant=False)
    res = es.run_study(closes, ev, es.StudyConfig(**FAST))
    assert _row(res, "primary", "P1")["p"] > 0.05
    assert not any(v.startswith("PROMOTE") for v in res["verdicts"])
    assert any(v.startswith("CALIBRATION: mpc") for v in res["verdicts"])


def test_planted_directional_cut_effect():
    closes, ev = _synthetic(dir_plant=True)
    res = es.run_study(closes, ev, es.StudyConfig(**FAST))
    assert _row(res, "secondary", "S1")["p"] < 0.05
    assert _row(res, "secondary", "S3")["p"] < 0.05


def test_small_bucket_is_na():
    closes, ev = _synthetic(n_hike=3, n_cut=12)
    res = es.run_study(closes, ev, es.StudyConfig(**FAST))
    assert _row(res, "secondary", "S2")["p"] == "n/a (n<5)"


def test_run_study_json_serialisable():
    import json
    closes, ev = _synthetic()
    res = es.run_study(closes, ev, es.StudyConfig(**FAST), omitted=["^CNXMEDIA"],
                       patched=[pd.Timestamp("2020-02-01")])
    json.dumps(res)
    assert res["meta"]["omitted"] == ["^CNXMEDIA"]
    assert res["meta"]["patched"] == ["2020-02-01"]
    md = es.render_markdown(res)
    assert "P1" in md and "Verdicts" in md


def test_unscheduled_events_reported_not_tested():
    closes, ev = _synthetic()
    extra = ev.iloc[[0]].copy()
    extra["date"] = closes.index[1500]; extra["scheduled"] = 0; extra["label"] = "cut"
    res = es.run_study(closes, pd.concat([ev, extra], ignore_index=True), es.StudyConfig(**FAST))
    assert len(res["unscheduled"]) == 1
    assert _row(res, "primary", "P1")["n"] == 40


def test_rolling_ar_matches_single_event_model():
    """The null reads a vectorised day-0 AR; it must be the same number
    market_model_ar gives for that day, or real and null measure different things."""
    pr = _pair(n=400, plant={330: 0.02})
    rolled = es._rolling_ar(pr, "market")
    for p in (150, 260, 330, 399):
        assert rolled.iloc[p] == pytest.approx(es.market_model_ar(pr, p).loc[0], abs=1e-10)
    assert np.isnan(rolled.iloc[100])        # < 120 estimation rows, like market_model_ar -> None


# ── special sessions Yahoo never printed (Saturday/Sunday budgets) ───────────

def test_patch_sessions_inserts_missing_event_day():
    """Yahoo has no bar for the 2020-02-01 Saturday budget session; NSE does.
    Without the patch, d0 would be Monday and its return would span two
    sessions — about sqrt(2) larger, which inflates a magnitude test."""
    idx = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-04"])
    closes = pd.DataFrame({es.MARKET: [100.0, 101, 95, 96], "^NSEBANK": [50.0, 51, 47, 48]},
                          index=idx)
    nse = pd.DataFrame({"Index Name": ["Nifty 50", "Nifty Bank", "Nifty IT"],
                        "Closing Index Value": ["98.0", "49.5", "-"]})
    calls = []
    def fetch(day):
        calls.append(day)
        return nse if day == pd.Timestamp("2020-02-01").date() else None
    out, patched = es.patch_sessions(closes, pd.Series(pd.to_datetime(["2020-02-01", "2020-01-31"])),
                                     fetch=fetch)
    assert patched == [pd.Timestamp("2020-02-01")]
    assert out.loc["2020-02-01", es.MARKET] == 98.0
    assert out.loc["2020-02-01", "^NSEBANK"] == 49.5
    assert out.index.is_monotonic_increasing and len(out) == 5
    assert calls == [pd.Timestamp("2020-02-01").date()]    # dates Yahoo has are not fetched


def test_patch_sessions_reads_legacy_cnx_names():
    idx = pd.to_datetime(["2015-02-27", "2015-03-02"])
    closes = pd.DataFrame({es.MARKET: [100.0, 102], "NIFTY_FIN_SERVICE.NS": [10.0, 11]}, index=idx)
    nse = pd.DataFrame({"Index Name": ["CNX Nifty", "CNX Finance"],
                        "Closing Index Value": ["101.0", "10.5"]})
    out, patched = es.patch_sessions(closes, pd.Series(pd.to_datetime(["2015-02-28"])),
                                     fetch=lambda d: nse)
    assert out.loc["2015-02-28", "NIFTY_FIN_SERVICE.NS"] == 10.5


def test_patch_sessions_leaves_non_trading_day_alone():
    idx = pd.to_datetime(["2020-01-30", "2020-01-31"])
    closes = pd.DataFrame({es.MARKET: [100.0, 101]}, index=idx)
    out, patched = es.patch_sessions(closes, pd.Series(pd.to_datetime(["2020-02-02"])),
                                     fetch=lambda d: None)
    assert patched == [] and len(out) == 2


def test_patch_sessions_fills_nan_market_on_existing_row():
    """2014-02-17: Yahoo prints Bank Nifty that day but NIFTY is NaN. The row
    exists, so a date-presence check skipped it and the event was snapped."""
    idx = pd.to_datetime(["2014-02-14", "2014-02-17", "2014-02-18"])
    closes = pd.DataFrame({es.MARKET: [100.0, np.nan, 102], "^NSEBANK": [50.0, 51.0, 52]},
                          index=idx)
    nse = pd.DataFrame({"Index Name": ["CNX Nifty", "CNX Bank"],
                        "Closing Index Value": ["101.0", "99.0"]})
    out, patched = es.patch_sessions(closes, pd.Series(pd.to_datetime(["2014-02-17"])),
                                     fetch=lambda d: nse)
    assert patched == [pd.Timestamp("2014-02-17")]
    assert out.loc["2014-02-17", es.MARKET] == 101.0
    assert out.loc["2014-02-17", "^NSEBANK"] == 51.0       # Yahoo's own value kept


def test_patch_sessions_fills_sector_gap_when_market_printed():
    """Sat 2025-02-01: Yahoo printed NIFTY but no sector index, so that budget
    silently fell out of the dispersion test. A series missing on an event day
    it has history on both sides of is a gap and is filled; a series that had
    not started yet is left NaN."""
    idx = pd.to_datetime(["2025-01-31", "2025-02-01", "2025-02-03"])
    closes = pd.DataFrame({es.MARKET: [100.0, 101, 102],
                           "^NSEBANK": [50.0, np.nan, 52],
                           "^CNXAUTO": [np.nan, np.nan, 30.0]}, index=idx)
    nse = pd.DataFrame({"Index Name": ["Nifty 50", "Nifty Bank", "Nifty Auto"],
                        "Closing Index Value": ["999", "51.0", "29.0"]})
    out, patched = es.patch_sessions(closes, pd.Series(pd.to_datetime(["2025-02-01"])),
                                     fetch=lambda d: nse)
    assert patched == [pd.Timestamp("2025-02-01")]
    assert out.loc["2025-02-01", "^NSEBANK"] == 51.0
    assert out.loc["2025-02-01", es.MARKET] == 101.0       # Yahoo's value kept
    assert np.isnan(out.loc["2025-02-01", "^CNXAUTO"])     # not started: not a gap
