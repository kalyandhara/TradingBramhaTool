"""Tests for the chart server's module route and bind — B-85, B-86.

The server used to carry **17 near-identical routes**, one per browser module.
The cost was not the duplication: a running server 404s a module added after it
started, which was observed live on 2026-09-07 (`/psar.js`) and sat in the backlog
as "restart the chart server" on two separate sessions. A restart is not a fix for
a routing table that has to be edited to learn about a file already on disk.

The obvious replacement — a blanket `/<anything>.js` — is **wrong here**, and that
is what these tests mostly exist to hold. `tools/` also holds nine NODE-side
scripts: `alert_watcher.js`, the backtest and emit runners, the shared SVP engine.
Serving those over HTTP would publish internal tooling, including the shape of the
alert delivery config. So the allow-list is read from `chart_dashboard.html` — the
page is the authority on what the browser needs, and nothing else is reachable.

Run:  python -m pytest tools/test_chart_routes.py -q
"""
from __future__ import annotations

import pathlib

import pytest

import chart_server as cs

HERE = pathlib.Path(__file__).resolve().parent

#: Node-side scripts that live beside the browser modules and must never serve.
NODE_ONLY = [
    "alert_watcher.js",
    "svp_backtest_runner.js",
    "svp_screen_runner.js",
    "renko_backtest.js",
    "evwma_vwap_macd_backtest.js",
    "pmax_bands_emit.js",
    "psar_overlap.js",
]


@pytest.fixture
def client():
    cs.app.config["TESTING"] = True
    with cs.app.test_client() as c:
        yield c


# ── the allow-list comes from the page ───────────────────────────────────────

def test_the_allow_list_is_what_the_page_actually_loads():
    mods = cs._page_modules()
    assert mods, "no modules found — the scan or the page shape changed"
    html = (HERE / "chart_dashboard.html").read_text(encoding="utf-8", errors="replace")
    for m in mods:
        assert f'src="/{m}"' in html


def test_every_allowed_module_exists_on_disk():
    """A page referencing a module that is not there is a 404 in the browser; the
    test says so here instead."""
    missing = [m for m in cs._page_modules() if not (HERE / m).is_file()]
    assert not missing, missing


def test_node_side_scripts_are_on_disk_but_not_allowed():
    """The reason a blanket route was not used. If this ever fails, internal
    tooling just became reachable over HTTP."""
    mods = cs._page_modules()
    for name in NODE_ONLY:
        if (HERE / name).is_file():
            assert name not in mods, f"{name} would be served"


# ── what the route actually serves ───────────────────────────────────────────

def test_a_page_module_is_served(client):
    name = sorted(cs._page_modules())[0]
    r = client.get(f"/{name}")
    assert r.status_code == 200
    assert "javascript" in r.headers["Content-Type"]


def test_every_page_module_is_served(client):
    bad = [m for m in sorted(cs._page_modules()) if client.get(f"/{m}").status_code != 200]
    assert not bad, bad


@pytest.mark.parametrize("name", NODE_ONLY)
def test_a_node_script_is_404_even_though_it_exists(client, name):
    if not (HERE / name).is_file():
        pytest.skip(f"{name} not in this checkout")
    assert client.get(f"/{name}").status_code == 404


def test_an_unknown_module_is_404(client):
    assert client.get("/definitely_not_a_module.js").status_code == 404


def test_the_service_worker_keeps_its_own_route(client):
    """`/sw.js` is NOT in the page's script tags — it is registered by
    `navigator.serviceWorker.register`. It needs no-cache headers and root scope,
    so it keeps a dedicated route, and a static rule outranks the converter rule."""
    assert "sw.js" not in cs._page_modules()
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert "no-cache" in r.headers.get("Cache-Control", "").lower()


def test_a_traversal_attempt_does_not_reach_disk(client):
    """Flask's string converter never matches a `/`, and membership in the page's
    list is the real gate. Both are checked rather than assumed."""
    for probe in ("../chart_server.py", "..%2fchart_server.py", "....//alert_watcher.js"):
        assert client.get(f"/{probe}").status_code in (301, 308, 404)


# ── the cache that makes a running server pick up a new module ───────────────

def test_the_allow_list_refreshes_when_the_page_changes(tmp_path, monkeypatch):
    """The whole point of B-85: add a module and its script tag, and a RUNNING
    server serves it. Verified against the real server too — 404 before the tag
    was added, 200 after, with no restart."""
    page = tmp_path / "chart_dashboard.html"
    page.write_text('<script src="/one.js"></script>', encoding="utf-8")
    monkeypatch.setattr(cs, "HERE", tmp_path)
    monkeypatch.setattr(cs, "_MODULE_CACHE", {"mtime": None, "names": frozenset()})

    assert cs._page_modules() == frozenset({"one.js"})

    import os
    import time
    time.sleep(0.01)
    page.write_text('<script src="/one.js"></script>\n<script src="/two.js"></script>',
                    encoding="utf-8")
    os.utime(page, (time.time() + 1, time.time() + 1))
    assert cs._page_modules() == frozenset({"one.js", "two.js"})


def test_a_missing_page_yields_an_empty_list_not_an_exception(tmp_path, monkeypatch):
    """A server whose page is absent should serve nothing, not crash on request."""
    monkeypatch.setattr(cs, "HERE", tmp_path)
    monkeypatch.setattr(cs, "_MODULE_CACHE", {"mtime": None, "names": frozenset()})
    assert cs._page_modules() == frozenset()


# ── the bind (B-86) ──────────────────────────────────────────────────────────

def test_the_bind_is_configurable_and_its_default_is_explained():
    """bandit's B104 is ACCEPTED here, not fixed: the chart is a PWA with
    installed clients, and a phone cannot reach 127.0.0.1. What the fix adds is a
    `--host` flag and the reasoning, so the exposure is a decision on the record
    rather than a default nobody chose."""
    src = (HERE / "chart_server.py").read_text(encoding="utf-8")
    assert '"--host"' in src
    assert "host=_args.host" in src
    assert "PWA" in src.split('"--host"')[0][-1200:]

# ── /api/flag_pole (B-92 / PR-4) ─────────────────────────────────────────────
#
# The overlay is inline in `chart_dashboard.html`, so it needs no allow-list
# entry -- but the API it reads does need to behave. What matters here is that a
# short frame and a genuine no-pattern are DISTINGUISHABLE: an overlay that draws
# nothing in both cases gives the reader no way to tell "there is no flag" from
# "I could not look", and those want different reactions.

def test_flag_pole_requires_a_symbol(client):
    r = client.get("/api/flag_pole")
    assert r.status_code == 400


def test_flag_pole_returns_both_directions(client, monkeypatch):
    """Both keys are always present, so the client never has to guess."""
    import flag_pole as fpm
    monkeypatch.setattr(cs, "_bars_to_df", lambda bars: None)
    monkeypatch.setattr(cs.ds, "detect_source",
                        lambda sym: type("S", (), {"get_ohlcv": staticmethod(lambda *a: [])})())
    r = client.get("/api/flag_pole?symbol=TEST")
    assert r.status_code == 200
    body = r.get_json()
    assert "bull" in body and "bear" in body


def test_a_short_frame_says_why_rather_than_reporting_no_pattern(client, monkeypatch):
    """"No pattern" and "could not look" must not be the same answer.

    A bare null on a short frame reads as "there is no flag here", which is a
    claim the server is in no position to make.
    """
    import pandas as pd
    import flag_pole as fpm
    short = pd.DataFrame({"open": [1.0] * 10, "high": [1.0] * 10,
                          "low": [1.0] * 10, "close": [1.0] * 10,
                          "volume": [1.0] * 10})
    monkeypatch.setattr(cs, "_bars_to_df", lambda bars: short)
    monkeypatch.setattr(cs.ds, "detect_source",
                        lambda sym: type("S", (), {"get_ohlcv": staticmethod(lambda *a: [])})())
    body = client.get("/api/flag_pole?symbol=TEST").get_json()
    assert body["bull"] is None and body["bear"] is None
    assert "note" in body
    assert str(fpm.WINDOW + fpm.ATR_N) in body["note"]


def test_a_real_pattern_carries_its_plan_and_mapped_times(client, monkeypatch):
    import numpy as np
    import pandas as pd

    # A clean bull flag & pole, the same shape test_flag_pole.py builds.
    base = [100.0] * 120
    up = list(np.linspace(100.0, 120.0, 11))[1:]
    flag = list(np.linspace(120.0, 114.0, 6))
    closes = np.array(base + up + flag + [flag[-1]], float)
    frame = pd.DataFrame({"open": closes, "high": closes * 1.005,
                          "low": closes * 0.995, "close": closes,
                          "volume": np.full(len(closes), 1e6)})
    bars = [{"time": 1_700_000_000 + i * 86400} for i in range(len(closes))]
    monkeypatch.setattr(cs, "_bars_to_df", lambda b: frame)
    monkeypatch.setattr(cs.ds, "detect_source",
                        lambda sym: type("S", (), {"get_ohlcv": staticmethod(lambda *a: bars)})())

    g = client.get("/api/flag_pole?symbol=TEST").get_json()["bull"]
    assert g is not None
    for k in ("entry", "stop", "target", "rr"):
        assert g[k] is not None
    # Bar indices must arrive as CHART TIMESTAMPS, not as indices.
    for k in ("pole_t0", "pole_t1", "flag_t0", "flag_t1", "last_t"):
        assert g[k] >= 1_700_000_000
    assert g["pole_t0"] < g["pole_t1"] < g["flag_t0"] <= g["flag_t1"]
