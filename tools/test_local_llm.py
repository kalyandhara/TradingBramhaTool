"""local_llm + filing_reader — the LM Studio layer, with a fake transport (no server)."""
from __future__ import annotations

import json

import pytest

import filing_reader as fr
import local_llm as ll


class _Resp:
    def __init__(self, status=200, payload=None):
        self.status_code, self._p = status, payload or {}

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _reply(content: str):
    return _Resp(payload={"choices": [{"message": {"content": content}}],
                          "usage": {"completion_tokens": 9}})


def test_parse_json_tolerates_fences_and_prose():
    assert ll.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert ll.parse_json('Sure! {"a": 2} hope that helps') == {"a": 2}
    assert ll.parse_json("no json here") is None


def test_qwen3_gets_no_think_and_others_do_not():
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    assert ll._prepare(msgs, "qwen3-4b")[-1]["content"].endswith("/no_think")
    assert ll._prepare(msgs, "google/gemma-4-26b-a4b")[-1]["content"] == "u"


def test_chat_json_posts_and_parses(monkeypatch, tmp_path):
    seen = {}

    def post(url, json=None, timeout=None):
        seen.update(url=url, body=json)
        return _reply('{"sentiment": "positive"}')

    monkeypatch.setattr(ll, "CACHE_DIR", tmp_path)
    out, err = ll.chat_json("sys", "user", base_url="http://x/v1", model="qwen3-4b", post=post)
    assert err is None and out == {"sentiment": "positive"}
    assert seen["url"] == "http://x/v1/chat/completions"
    assert seen["body"]["temperature"] == 0 and seen["body"]["model"] == "qwen3-4b"


def test_chat_json_caches_identical_prompts(monkeypatch, tmp_path):
    calls = []

    def post(url, json=None, timeout=None):
        calls.append(1)
        return _reply('{"x": 1}')

    monkeypatch.setattr(ll, "CACHE_DIR", tmp_path)
    for _ in range(2):
        assert ll.chat_json("s", "u", base_url="http://x/v1", model="m", post=post)[0] == {"x": 1}
    assert len(calls) == 1


def test_chat_json_never_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(ll, "CACHE_DIR", tmp_path)

    def boom(url, json=None, timeout=None):
        raise OSError("connection refused")

    out, err = ll.chat_json("s", "u", base_url="http://x/v1", model="m", post=boom)
    assert out is None and "OSError" in err
    out, err = ll.chat_json("s", "u", base_url="http://x/v1", model="m",
                            post=lambda *a, **k: _reply("not json"))
    assert out is None and "JSON" in err


def test_status_reports_down_and_up():
    down = ll.status(bases=("http://a/v1",), get=lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    assert down["ok"] is False and down["base_url"] is None
    up = ll.status(bases=("http://a/v1", "http://b/v1"),
                   get=lambda url, timeout=None: _Resp(payload={"data": [{"id": "qwen3-4b"}]})
                   if url.startswith("http://b") else (_ for _ in ()).throw(OSError("x")))
    assert up["ok"] and up["base_url"] == "http://b/v1" and up["models"] == ["qwen3-4b"]


# ── filing_reader ────────────────────────────────────────────────────────────

ROWS = [
    {"symbol": "ABC", "desc": "Bonus Issue", "an_dt": "02-Nov-2026 18:00:00",
     "attchmntText": "Board approved a 1:1 bonus issue.", "attchmntFile": "https://x/a.pdf"},
    {"symbol": "ABC", "desc": "Trading Window-xbrl", "an_dt": "01-Nov-2026 10:00:00",
     "attchmntText": "Closure of trading window.", "attchmntFile": "https://x/b.pdf"},
    {"symbol": "ABC", "desc": "Newspaper Advertisement", "an_dt": "31-Oct-2026 10:00:00",
     "attchmntText": "", "attchmntFile": None},
]


def _fake_llm(system, user, **kw):
    if "bonus" in user.lower():
        return {"sentiment": "positive", "materiality": "medium",
                "summary": "1:1 bonus approved.", "numbers": ["1:1"]}, None
    return {"sentiment": "neutral", "materiality": "low",
            "summary": "Routine compliance filing.", "numbers": []}, None


def test_reader_reads_logs_and_skips_empty_text(tmp_path):
    db = tmp_path / "r.db"
    got = fr.read_recent("ABC", rows=ROWS, n=5, chat=_fake_llm, model="qwen3-4b", db_path=db)
    assert got["state"] == "OK" and [r["sentiment"] for r in got["reads"]] == ["positive", "neutral"]
    assert got["skipped_no_text"] == 1
    assert got["reads"][0]["file"] == "https://x/a.pdf"
    assert got["reads"][0]["model"] == f"qwen3-4b@v{fr.PROMPT_V}"
    assert got["tone"] == {"positive": 1, "neutral": 1, "negative": 0}
    stored = fr.load_reads("ABC", db_path=db)
    assert len(stored) == 2


def test_reader_does_not_reread_a_logged_filing(tmp_path):
    db = tmp_path / "r.db"
    fr.read_recent("ABC", rows=ROWS, n=5, chat=_fake_llm, model="qwen3-4b", db_path=db)
    calls = []

    def counting(system, user, **kw):
        calls.append(1)
        return _fake_llm(system, user)

    fr.read_recent("ABC", rows=ROWS, n=5, chat=counting, model="qwen3-4b", db_path=db)
    assert calls == []


def test_reader_rejects_invalid_labels(tmp_path):
    bad = lambda s, u, **k: ({"sentiment": "bullish!!", "materiality": "huge",  # noqa: E731
                              "summary": "x"}, None)
    got = fr.read_recent("ABC", rows=ROWS[:1], n=1, chat=bad, model="m", db_path=tmp_path / "r.db")
    assert got["reads"][0]["sentiment"] is None and got["reads"][0]["error"]


def test_reader_feed_down_is_not_checked(tmp_path):
    got = fr.read_recent("ABC", rows=None, n=5, chat=_fake_llm, model="m", db_path=tmp_path / "r.db")
    assert got["state"] == "NOT_CHECKED" and got["reads"] == []


def test_reader_llm_down_is_reported_not_faked(tmp_path):
    down = lambda s, u, **k: (None, "OSError: connection refused")  # noqa: E731
    got = fr.read_recent("ABC", rows=ROWS, n=5, chat=down, model="m", db_path=tmp_path / "r.db")
    assert got["state"] == "LLM_DOWN" and got["reads"] == [] and "refused" in got["note"]
    assert fr.load_reads("ABC", db_path=tmp_path / "r.db").empty


def test_a_prompt_change_does_not_reuse_old_reads(tmp_path, monkeypatch):
    db = tmp_path / "r.db"
    fr.read_recent("ABC", rows=ROWS, n=1, chat=_fake_llm, model="m", db_path=db)
    monkeypatch.setattr(fr, "PROMPT_V", fr.PROMPT_V + 1)
    calls = []
    fr.read_recent("ABC", rows=ROWS, n=1, chat=lambda s, u, **k: (calls.append(1), _fake_llm(s, u))[1],
                   model="m", db_path=db)
    assert calls == [1]
