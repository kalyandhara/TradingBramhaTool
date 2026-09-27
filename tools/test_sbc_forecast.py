"""Tests for sbc_forecast (ported SBC_Tool heatmap / crash / commentary).

    py -3 -m pytest test_sbc_forecast.py -q
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace as NS

import pytest

pytest.importorskip("ephem")

import sbc_forecast as f
import sbc_scoring as sbcs


def _p(lon, nak="Rohini", nature="malefic"):
    return NS(sidereal_lon=lon, nakshatra=nak, nature=nature)


def _planets(**over):
    base = {n: _p(i * 40.0) for i, n in enumerate(
        ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])}
    base.update(over)
    return base


def test_angle_wraps():
    assert f._angle(355, 5) == pytest.approx(10)
    assert f._angle(0, 180) == pytest.approx(180)


def test_lunar_events():
    assert f.lunar_events(15) == ["Purnima"]
    assert f.lunar_events(30) == ["Amavasya"]
    assert f.lunar_events(11) == ["Ekadashi"]
    assert f.lunar_events(5) == []


def test_crash_signature_geometry():
    s = f.crash_signatures(_planets(Jupiter=_p(10, "Ashwini"), Saturn=_p(15),
                                    Mars=_p(200), Ketu=_p(205)))
    assert s["jupiter_ketu_nakshatra"][0]
    assert s["jupiter_saturn_conjunction"][0]
    assert not s["jupiter_saturn_opposition"][0]
    assert s["mars_ketu_conjunction"][0]
    assert f.crash_score(s) == pytest.approx(35 + 30 + 15)


def test_bands():
    assert f.crash_band(0) == "NORMAL"
    assert f.crash_band(35) == "CORRECTION RISK"
    assert f.crash_band(65) == "CRASH RISK"


def test_sector_nets_match_stress_panel_arithmetic():
    """Heatmap cells must equal the Broad Vedha Pressure net."""
    vedas = sbcs.cast_vedas(f._planets_at(date(2026, 8, 18)))
    nets = f.sector_nets(vedas)
    assert set(nets) == set(sbcs.SECTORS)
    assert all(-6 <= v <= 6 for v in nets.values())
    assert nets["NIFTY Metal"] == pytest.approx(-1.0)   # verified live 2026-08-18


def test_heatmap_skips_weekends_and_has_all_sectors():
    days = f.monthly_heatmap(date(2026, 9, 28), days=7)
    assert [d.day.weekday() for d in days] == [0, 1, 2, 3, 4]
    assert all(set(d.nets) == set(sbcs.SECTORS) for d in days)


def test_commentary_carries_caveat():
    txt = f.weekly_commentary(date(2026, 9, 28))
    assert "WEEK AHEAD" in txt and "none of this is a signal" in txt


def test_backtest_reports_base_rate():
    r = f.crash_backtest(start=date(2019, 1, 1), end=date(2021, 1, 1), step_days=30)
    assert 0 <= r["flag_rate_all"] <= 1
    assert len(r["crashes"]) == len(f.HISTORICAL_CRASHES)
    assert {s["signature"] for s in r["signatures"]} == set(f.CRASH_SIGNATURES)
