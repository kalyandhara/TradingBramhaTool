"""Tests for sector_indices_table — history assembly and the table. No network."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

import sector_indices_table as sit

COLS = ["Index Name", "Index Date", "Open Index Value", "High Index Value",
        "Low Index Value", "Closing Index Value", "Points Change", "Change(%)"]


def _file(d: date, closes: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame([[n, d.strftime("%d-%m-%Y"), c, c * 1.01, c * 0.99, c, 0, 0]
                         for n, c in closes.items()], columns=COLS)


def _files(n_sessions: int, names: list[str], young: str | None = None) -> dict[date, pd.DataFrame]:
    days = sorted(sit.candidate_days(date(2026, 9, 25), n_sessions))[-n_sessions:]
    rng = np.random.default_rng(1)
    level = {n: 1000.0 for n in names}
    drift = {n: 0.0005 * (i - len(names) / 2) for i, n in enumerate(names)}
    out = {}
    for k, d in enumerate(days):
        row = {}
        for n in names:
            level[n] *= 1 + drift[n] + rng.normal(0, 0.005)
            if n == young and k < n_sessions - 60:
                continue
            row[n] = level[n]
        out[d] = _file(d, row)
    return out


NAMES = sit.SECTORAL_INDICES[:24]


def test_candidate_days_are_weekdays_and_enough():
    days = sit.candidate_days(date(2026, 9, 25), 330)
    assert all(d.weekday() < 5 for d in days)
    assert len(days) >= 330


def test_assemble_builds_dated_ohlc_per_index():
    hist = sit.assemble(_files(40, NAMES), NAMES)
    assert set(NAMES) <= set(hist)
    df = hist["Nifty Bank"]
    assert list(df.columns) == ["open", "high", "low", "close"]
    assert len(df) == 40 and df.index.is_monotonic_increasing


def test_assemble_fills_missing_open_from_close_and_skips_unknown_names():
    d = date(2026, 9, 25)
    f = _file(d, {"Nifty IT": 100.0, "Some Other Index": 5.0})
    f["Open Index Value"] = f["Open Index Value"].astype(object)
    f.loc[0, "Open Index Value"] = "-"
    hist = sit.assemble({d: f}, ["Nifty IT"])
    assert "Some Other Index" not in hist
    assert hist["Nifty IT"]["open"].iloc[0] == 100.0


def test_load_history_keeps_only_sessions_actually_served():
    files = _files(30, NAMES)

    def fake_fetch(d, max_backtrack=0):
        return (files[d], d) if d in files else (None, None)

    hist = sit.load_history(30, today=date(2026, 9, 25), fetch=fake_fetch, workers=2)
    assert len(hist["Nifty 50"]) == 30


def test_table_sorted_by_rs_and_young_index_shows_question_marks():
    young = NAMES[-1]
    hist = sit.assemble(_files(300, NAMES, young=young), NAMES)
    t = sit.build_table(hist, NAMES)
    assert len(t) == len(NAMES)
    ranked = t["RS T0"].dropna().tolist()
    assert ranked == sorted(ranked, reverse=True)
    row = t[t["Index"] == young].iloc[0]
    assert pd.isna(row["RS T0"]) and row["RS walk"] == "? → ? → ? → ?"
    assert t["Index"].iloc[-1] == young


def test_table_columns_match_the_reference_layout():
    hist = sit.assemble(_files(300, NAMES), NAMES)
    t = sit.build_table(hist, NAMES)
    for col in ["Index", "Price", "% Chg 1D", "RSI", "EMAs", "% from 20EMA",
                "10x20 up (days)", "D-Pivot", "W-Pivot", "RS T0", "RS walk", "RS trend"]:
        assert col in t.columns
    assert sit.as_of(hist) == "2026-09-25"
