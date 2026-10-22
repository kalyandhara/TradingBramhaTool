"""rec_audit_job — fetch splitting, storage and an end-to-end run on fake prices."""
from __future__ import annotations

import sqlite3
from datetime import date

import pandas as pd

import rec_audit_job as job


def _frame(n=40, start="2026-08-03", step=0.0, base=100.0):
    idx = pd.bdate_range(start, periods=n)
    c = pd.Series([base + step * i for i in range(n)], index=idx)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c,
                         "volume": 1e6})


def test_split_download_handles_single_ticker_multiindex():
    raw = pd.concat({"A.NS": _frame(3).rename(columns=str.title)}, axis=1)
    out = job._split_download(raw, ["A.NS", "MISSING.NS"])
    assert list(out) == ["A.NS"] and list(out["A.NS"].columns)[:4] == ["open", "high", "low", "close"]


def test_yahoo_symbol_keeps_indices_and_ampersand():
    assert job.yahoo_symbol("M&M") == "M&M.NS"
    assert job.yahoo_symbol("^CRSLDX") == "^CRSLDX"


def test_sector_bars_come_from_nse_daily_files_and_skip_missing_days():
    def fetch(d):
        if d.day == 4:
            return None, None                       # holiday / not published
        return pd.DataFrame({"Index Name": ["Nifty IT", "Nifty 50"],
                             "Open Index Value": [10.0, 1.0], "High Index Value": [11.0, 1.0],
                             "Low Index Value": [9.0, 1.0],
                             "Closing Index Value": [10.5, 1.0]}), d
    out = job.nse_sector_bars("2026-08-03", "2026-08-05", fetch=fetch)
    assert list(out) == ["^CNXIT"]
    assert [d.day for d in out["^CNXIT"].index] == [3, 5]
    assert out["^CNXIT"]["close"].iloc[0] == 10.5


def test_end_to_end_run_stores_episodes_and_marks_no_data(tmp_path):
    recs = pd.DataFrame({"run_date": pd.to_datetime(["2026-08-03", "2026-08-03"]),
                         "symbol": ["UP", "GONE"], "rank": [1, 2], "sector": ["Technology", ""],
                         "family_names": ["Trend", "Trend"], "risk_flags": ["", ""],
                         "stop": [None, None], "target": [None, None]})

    def fake(tickers, start, end):
        return {job.MARKET: _frame(), job.SMALLCAP: _frame(),
                "^CNXIT": _frame(), "UP.NS": _frame(step=1.0)}

    rep = job.run_audit(recs, as_of=date(2026, 9, 25), download=fake,
                        sector_fetch=lambda d: (None, None), db_path=tmp_path / "a.db")
    df = rep["episodes_df"].set_index("symbol")
    assert df.loc["GONE", "status"] == "no_data" and bool(df.loc["GONE", "failure"])
    assert df.loc["UP", "excess_21"] > 0
    assert rep["summary"]["n"] == 1 and rep["summary"]["no_data"] == 1
    conn = sqlite3.connect(tmp_path / "a.db")
    assert conn.execute("select count(*) from audit_episodes").fetchone()[0] == 2
    assert conn.execute("select count(*) from audit_runs").fetchone()[0] == 1
    assert "Recommendation audit" in job.format_report(rep)
