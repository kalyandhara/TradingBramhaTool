"""Indicator preview pictures are complete, honest and safely served — B-151.

* The manifest names every INDICATOR_DEFS key and nothing else. A key either
  points at a picture that exists, is named `<key>.<hash10>.webp` and whose
  hash matches its bytes (so the service worker's cache-first rule can never
  pin a stale one), or carries a reason it has none ("nothing drawn on the
  reference chart" — the browser then shows the colour swatch).
* No orphan pictures sit in ind-thumbs/, and the set stays small.
* The route serves only the manifest (no-cache) and hash-named webp files
  (immutable); any other name, or a traversal attempt, is a 404.

Regenerate:  python tools/gen_indicator_thumbs.py   (chart server running)
Run:         python -m pytest tools/test_indicator_thumbs.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
THUMBS = HERE / "ind-thumbs"
MANIFEST = json.loads((THUMBS / "manifest.json").read_text(encoding="utf-8"))["thumbs"]
_defs = (HERE / "chart_dashboard.html").read_text(encoding="utf-8") \
    .split("const INDICATOR_DEFS = [", 1)[1].split("\n];", 1)[0]
KEYS = re.findall(r"key:'([a-z0-9_]+)'", _defs)


def test_manifest_covers_exactly_the_defs():
    assert set(MANIFEST) == set(KEYS)


@pytest.mark.parametrize("key", sorted(MANIFEST))
def test_entry_is_a_real_picture_or_says_why_not(key):
    e = MANIFEST[key]
    assert e.get("chart")
    if not e.get("file"):
        assert e.get("reason"), f"{key}: no picture and no reason"
        return
    m = re.fullmatch(r"([a-z0-9_]+)\.([0-9a-f]{10})\.webp", e["file"])
    assert m and m.group(1) == key, e["file"]
    data = (THUMBS / e["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest()[:10] == m.group(2), "hash does not match bytes"
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def test_no_orphans_and_small_total():
    named = {e["file"] for e in MANIFEST.values() if e.get("file")}
    on_disk = {p.name for p in THUMBS.glob("*.webp")}
    assert on_disk == named
    assert sum(p.stat().st_size for p in THUMBS.glob("*.webp")) < 2 * 1024 * 1024


@pytest.fixture
def client():
    import chart_server as cs
    cs.app.config["TESTING"] = True
    return cs.app.test_client()


def test_route_serves_manifest_uncached(client):
    r = client.get("/ind-thumbs/manifest.json")
    assert r.status_code == 200 and r.headers["Cache-Control"] == "no-cache"


def test_route_serves_pictures_immutable(client):
    name = next(e["file"] for e in MANIFEST.values() if e.get("file"))
    r = client.get(f"/ind-thumbs/{name}")
    assert r.status_code == 200 and r.mimetype == "image/webp"
    assert "immutable" in r.headers["Cache-Control"]


@pytest.mark.parametrize("bad", ["evil.webp", "rsi.webp", "RSI.0123456789.webp",
                                 "..%2Fchart_server.py", "rsi.0123456789.png"])
def test_route_refuses_anything_else(client, bad):
    assert client.get(f"/ind-thumbs/{bad}").status_code == 404
