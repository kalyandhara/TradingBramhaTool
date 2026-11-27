"""local_llm.py — the desk's one door to a local LLM (LM Studio, OpenAI-compatible).

Until 2026-11-03 the repo had no LLM: `concalls.py` lists documents and stops,
because "a generated narrative over a concall would be invention". A local
model changes what is possible, not that rule: everything an LLM writes here is
labelled as a model's reading, keeps the link to the primary document, and is
logged so it can be measured like any other signal (see `filing_reader.py`).

  * Endpoint: LM Studio's OpenAI-compatible server. This machine runs it on
    :5173 (LM Studio's default is :1234); both are probed, LLM_BASE_URL overrides.
  * Model: LLM_MODEL, default `qwen3-4b` — small, already downloaded, and with
    reasoning switched off ("/no_think") it answers a filing in ~1.5 s. The
    larger models on disk spent every token on hidden reasoning in a probe.
  * temperature 0 and a disk cache keyed on (model, messages): the same prompt
    returns the same answer, which a logged, audited signal needs.
  * Never raises: every call returns (value, error).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache" / "llm"
BASES: tuple[str, ...] = tuple(b for b in (os.environ.get("LLM_BASE_URL"),
                                           "http://localhost:5173/v1",
                                           "http://localhost:1234/v1") if b)
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "qwen3-4b")
TIMEOUT = 120


def _requests():
    import requests
    return requests


def status(bases: tuple[str, ...] = BASES, get=None) -> dict:
    """{ok, base_url, models} — the first endpoint that lists its models."""
    get = get or _requests().get
    for b in bases:
        try:
            r = get(f"{b}/models", timeout=3)
            r.raise_for_status()
            return {"ok": True, "base_url": b,
                    "models": [m.get("id") for m in (r.json().get("data") or [])]}
        except Exception:
            continue
    return {"ok": False, "base_url": None, "models": []}


def parse_json(text: str | None) -> dict | None:
    """The first JSON object in a model's reply (code fences and chatter allowed)."""
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        v = json.loads(text[start:i + 1])
                        return v if isinstance(v, dict) else None
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    return None


def _prepare(messages: list[dict], model: str) -> list[dict]:
    """Qwen3 reasons by default and spends the token budget on it; '/no_think'
    on the last user turn switches that off. Other models are left alone."""
    out = [dict(m) for m in messages]
    if "qwen3" in model.lower() and out and not out[-1]["content"].rstrip().endswith("/no_think"):
        out[-1]["content"] = out[-1]["content"].rstrip() + " /no_think"
    return out


def chat_json(system: str, user: str, *, model: str | None = None,
              base_url: str | None = None, max_tokens: int = 300,
              post=None, use_cache: bool = True) -> tuple[dict | None, str | None]:
    """Ask for a JSON object. Returns (dict, None) or (None, error text)."""
    model = model or DEFAULT_MODEL
    messages = _prepare([{"role": "system", "content": system},
                         {"role": "user", "content": user}], model)
    key = hashlib.sha1(json.dumps([model, messages], sort_keys=True).encode()).hexdigest()
    path = CACHE_DIR / f"{key}.json"
    if use_cache and path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")), None
        except ValueError:
            pass
    if base_url is None:
        st = status()
        if not st["ok"]:
            return None, "no LM Studio server answered on " + ", ".join(BASES)
        base_url = st["base_url"]
    post = post or _requests().post
    try:
        r = post(f"{base_url}/chat/completions", timeout=TIMEOUT,
                 json={"model": model, "messages": messages, "temperature": 0,
                       "max_tokens": max_tokens})
        r.raise_for_status()
        content = (r.json()["choices"][0]["message"].get("content") or "")
    except Exception as e:                        # noqa: BLE001 — reported, never raised
        return None, f"{type(e).__name__}: {e}"
    out = parse_json(content)
    if out is None:
        return None, f"model reply was not JSON: {content[:120]!r}"
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out), encoding="utf-8")
    return out, None
