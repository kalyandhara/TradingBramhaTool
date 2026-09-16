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
