"""Tests for /api/tour (B-186), offline: a stubbed data source, a temp base-rate file."""
import json

import numpy as np
import pandas as pd
import pytest

import chart_server as cs


def _bars(n=320, seed=5):
    c = 100 + np.cumsum(np.random.default_rng(seed).normal(0.1, 1.5, n))
    t0 = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp())
    return [{"time": t0 + 86400 * i, "open": float(x), "high": float(x) * 1.01, "low": float(x) * 0.99,
             "close": float(x), "volume": 1000.0 + i} for i, x in enumerate(c)]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(cs.ds, "detect_source",
                        lambda s: type("S", (), {"get_ohlcv": staticmethod(lambda *a, **k: _bars())})())
    monkeypatch.setattr(cs.sym_dir, "resolve_symbol", lambda s: s)
    monkeypatch.setattr(cs, "TOUR_RATES_PATH", tmp_path / "missing.json")
    cs.app.config["TESTING"] = True
    with cs.app.test_client() as c:
        yield c


def test_tour_requires_symbol(client):
    assert client.get("/api/tour").status_code == 400


def test_tour_non_daily_note(client):
    body = client.get("/api/tour?symbol=TEST&timeframe=15m").get_json()
    assert body["steps"] == []
    assert body["notes"] == ["The tour is daily-only: its base rates are measured on daily bars."]


def test_tour_returns_now_and_context(client):
    body = client.get("/api/tour?symbol=TEST").get_json()
    ids = [s["id"] for s in body["steps"]]
    assert ids[0] == "now" and ids[1] == "context"
    assert isinstance(body["asOf"], int)


def test_tour_missing_base_rates_not_measured(client):
    body = client.get("/api/tour?symbol=TEST").get_json()
    found = [s for s in body["steps"] if s.get("detector")]
    assert found, "the synthetic chart should produce at least one finding"
    assert all(s["badge"]["label"] == "NOT_MEASURED" for s in found)
    assert body["base_rates_asOf"] is None


def test_tour_reads_base_rates_and_survives_a_corrupt_file(client, monkeypatch, tmp_path):
    good = tmp_path / "rates.json"
    good.write_text(json.dumps({"asOf": "2026-10-20", "detectors": {}}), encoding="utf-8")
    monkeypatch.setattr(cs, "TOUR_RATES_PATH", good)
    assert client.get("/api/tour?symbol=TEST").get_json()["base_rates_asOf"] == "2026-10-20"
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(cs, "TOUR_RATES_PATH", bad)
    body = client.get("/api/tour?symbol=TEST").get_json()
    assert body["base_rates_asOf"] is None and body["steps"]
