"""CORS on /api/ohlcv for the Home rail's hover chart (B-180).

The rail's chart card runs in the desk's page (:8501 / :8502) and reads candles
from the chart server on :5001 — a cross-port fetch the browser blocks unless
the server says the desk may read it. Only the desk, only this route.

    py -3 -m pytest tools/test_chart_server_cors.py -q
"""
import chart_server as cs


def _get(path, origin):
    with cs.app.test_client() as c:
        return c.get(path, headers={"Origin": origin})


def test_desk_origin_is_echoed_on_ohlcv():
    # No `symbol` → 400 before any fetch, so this test needs no network.
    for o in ("http://localhost:8501", "http://localhost:8502"):
        r = _get("/api/ohlcv", o)
        assert r.status_code == 400
        assert r.headers.get("Access-Control-Allow-Origin") == o
        assert "Origin" in r.headers.get("Vary", "")


def test_unknown_origin_gets_no_header():
    r = _get("/api/ohlcv", "http://evil.localhost:9999")
    assert "Access-Control-Allow-Origin" not in r.headers


def test_other_routes_get_no_header():
    r = _get("/manifest.webmanifest", "http://localhost:8501")
    assert "Access-Control-Allow-Origin" not in r.headers


def test_loopback_ip_origin_is_echoed_on_ohlcv():
    # The desk opened as http://127.0.0.1:8501 is the same desk, a different origin.
    for o in ("http://127.0.0.1:8501", "http://127.0.0.1:8502"):
        r = _get("/api/ohlcv", o)
        assert r.headers.get("Access-Control-Allow-Origin") == o
