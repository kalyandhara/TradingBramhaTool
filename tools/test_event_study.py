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
