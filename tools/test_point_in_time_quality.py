"""Tests for the point-in-time quality gate (offline).

The property worth pinning is the one the module exists for: a fiscal year must
be invisible until it has been published. Everything else here guards a way that
guarantee has been quietly broken before — positional indexing that turns a
2-year gap into a 3-year CAGR, and "unknown" collapsing into "failed".
"""
import datetime as dt

import pytest

import point_in_time_quality as pit

FY = {  # period end -> (revenue, ocf), a company growing steadily
    "2021-03-31": (100.0, 10.0),
    "2022-03-31": (120.0, 12.0),
    "2023-03-31": (140.0, 14.0),
    "2024-03-31": (170.0, 18.0),
}


def _stmts(fy=None):
    fy = fy or FY
    rev = [(dt.date.fromisoformat(k), v[0]) for k, v in fy.items()]
    ocf = [(dt.date.fromisoformat(k), v[1]) for k, v in fy.items()]
    rev.sort(reverse=True)
    ocf.sort(reverse=True)
    return {"income": pit._Frameish(rev), "cashflow": pit._Frameish(ocf)}


# ── the one rule ──────────────────────────────────────────────────────────────

def test_a_fiscal_year_is_invisible_until_the_filing_lag_has_passed():
    s = _stmts()
    # FY2024 ends 31-Mar-2024, so with a 60-day lag it is public ~30-May-2024.
    before = pit.quality_as_of(s, "2024-05-15")
    after = pit.quality_as_of(s, "2024-06-15")
    assert before["latest_fy"] == "2023-03-31"
    assert after["latest_fy"] == "2024-03-31"


def test_the_lag_is_configurable_and_actually_moves_the_boundary():
    s = _stmts()
    assert pit.quality_as_of(s, "2024-06-15", lag_days=120)["latest_fy"] == "2023-03-31"
    assert pit.quality_as_of(s, "2024-06-15", lag_days=30)["latest_fy"] == "2024-03-31"


def test_asking_in_2022_cannot_see_2024():
    """The whole lookahead trap in one assertion."""
    r = pit.quality_as_of(_stmts(), "2022-07-01")
    assert r["latest_fy"] == "2022-03-31"
    assert r["n_years_known"] == 2
    assert r["verdict"] is None          # two years is not enough to judge


# ── unknown is not failure ────────────────────────────────────────────────────

def test_too_few_published_years_is_unknown_not_a_fail():
    r = pit.quality_as_of(_stmts(), "2022-07-01")
    assert r["verdict"] is None
    assert "need 3" in r["reason"]


def test_no_statements_is_unknown_not_a_fail():
    r = pit.quality_as_of({}, "2024-06-15")
    assert r["verdict"] is None
    assert r["reason"] == "no statements"


def test_a_real_failure_is_False_and_distinguishable_from_unknown():
    shrinking = {"2021-03-31": (200.0, 20.0), "2022-03-31": (180.0, 16.0),
                 "2023-03-31": (160.0, 14.0), "2024-03-31": (150.0, 12.0)}
    r = pit.quality_as_of(_stmts(shrinking), "2024-06-15")
    assert r["verdict"] is False
    assert r["revenue_cagr"] is not None and r["revenue_cagr"] < 0


# ── the base year is chosen by date, not by position ──────────────────────────

def test_a_missing_middle_year_does_not_become_a_three_year_cagr():
    """FY22 dropped: positional indexing would call a 2-year span a 3-year one."""
    gapped = {"2022-03-31": (120.0, 12.0), "2023-03-31": (140.0, 14.0),
              "2024-03-31": (170.0, 18.0)}
    r = pit.quality_as_of(_stmts(gapped), "2024-06-15")
    # Base must be FY2022 (2 years back), so the CAGR is the 2-year rate.
    expected = round(((170.0 / 120.0) ** (1 / ((dt.date(2024, 3, 31) - dt.date(2022, 3, 31)).days / 365.25)) - 1) * 100, 2)
    assert r["revenue_cagr"] == pytest.approx(expected, abs=0.05)
    # And it must SAY the span was 2 years, so no caller reads it as a 3Y rate.
    assert r["window_years"] == pytest.approx(2.0, abs=0.02)


def test_no_base_year_within_tolerance_is_unknown():
    sparse = {"2015-03-31": (50.0, 5.0), "2023-03-31": (140.0, 14.0),
              "2024-03-31": (170.0, 18.0)}
    r = pit.quality_as_of(_stmts(sparse), "2024-06-15")
    assert r["verdict"] is None
    assert "base year" in r["reason"]


# ── OCF growth survives a negative base, which a CAGR cannot ─────────────────

def test_ocf_turning_from_negative_to_positive_is_measured_not_dropped():
    turnaround = {"2021-03-31": (100.0, -10.0), "2022-03-31": (120.0, -4.0),
                  "2023-03-31": (140.0, 5.0), "2024-03-31": (170.0, 20.0)}
    r = pit.quality_as_of(_stmts(turnaround), "2024-06-15")
    # Base FY2021 OCF = -10 -> +20 is +300% of |base|; a CAGR would be undefined.
    assert r["ocf_growth"] == pytest.approx(300.0, abs=0.1)
    assert r["verdict"] is True


def test_revenue_growing_but_cash_flow_shrinking_fails_the_gate():
    diverging = {"2021-03-31": (100.0, 30.0), "2022-03-31": (120.0, 25.0),
                 "2023-03-31": (140.0, 20.0), "2024-03-31": (170.0, 15.0)}
    r = pit.quality_as_of(_stmts(diverging), "2024-06-15")
    assert r["revenue_cagr"] > 0
    assert r["ocf_growth"] < 0
    assert r["verdict"] is False


# ── the gate returns continuous measures, for B-57's rank secondary ──────────

def test_continuous_measures_are_returned_alongside_the_verdict():
    r = pit.quality_as_of(_stmts(), "2024-06-15")
    assert r["verdict"] is True
    assert isinstance(r["revenue_cagr"], float)
    assert isinstance(r["ocf_growth"], float)
    assert r["n_years_known"] == 4
