"""filing_reader.py — NSE announcements read by a local LLM, logged for audit.

The first use of `local_llm`. For a symbol's latest NSE announcements it asks
the model, per filing, for a sentiment (positive / neutral / negative), a
materiality (high / medium / low), a one-line summary and the figures quoted.

What it reads, and what it does not:
  * Only the text NSE carries with the filing (`attchmntText`, the company's
    own one-paragraph description). Not the PDF. A filing with no text is
    skipped and counted, never guessed at.
  * Every read keeps the link to the primary document and the model's name.
    It is a model's reading of a summary, not analysis of the filing.

Every read is stored in `tools/llm_reads.db` (one row per filing and model), so
a filing is read once, and so whether "positive" filings precede better returns
can be measured later the way every other signal here is. Until that study
exists, these labels are unmeasured.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "llm_reads.db"
SENTIMENTS = ("positive", "neutral", "negative")
MATERIALITY = ("high", "medium", "low")
MAX_TEXT = 1500
#: Bumped whenever SYSTEM changes; stored with each read (model@vN), so reads
#: under different prompts are never mixed or reused. v2 (2026-11-03): v1 called
#: "Board approved the results" positive/high with no figures in the text.
PROMPT_V = 2

SYSTEM = (
    "You read filings that Indian listed companies make to the stock exchange (NSE), "
    "for a long-only investor. Use ONLY the text given; do not use outside knowledge. "
    "Routine compliance (trading-window closure, newspaper advertisements, compliance "
    "certificates, loss of share certificates, investor-meet schedules with no content) "
    "is materiality low and sentiment neutral. Sentiment is positive or negative ONLY when "
    "the text itself states a direction: higher/lower profit or revenue with figures, an "
    "order win, a default, a downgrade, a penalty, a resignation of a key person. A board "
    "approving or adopting results, a dividend date or a meeting outcome WITHOUT figures "
    "is neutral. Reply with one JSON object and nothing "
    "else: {\"sentiment\": \"positive\"|\"neutral\"|\"negative\", "
    "\"materiality\": \"high\"|\"medium\"|\"low\", \"summary\": one plain sentence, "
    "\"numbers\": [figures quoted in the text, as strings]}"
)


def _key(symbol: str, row: dict) -> str:
    blob = "|".join(str(row.get(k) or "") for k in ("an_dt", "desc", "attchmntFile",
                                                    "attchmntText"))
    return hashlib.sha1(f"{symbol}|{blob}".encode()).hexdigest()[:20]


def _date(row: dict) -> str | None:
    v = row.get("an_dt") or row.get("sort_date") or row.get("dt")
    for fmt in ("%d-%b-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%b-%Y"):
        try:
            return datetime.strptime(str(v), fmt).date().isoformat()
        except (TypeError, ValueError):
            continue
    return None


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE IF NOT EXISTS llm_reads (
        key TEXT NOT NULL, model TEXT NOT NULL, symbol TEXT NOT NULL, an_date TEXT,
        subject TEXT, file TEXT, sentiment TEXT, materiality TEXT, summary TEXT,
        numbers TEXT, error TEXT, created_at TEXT NOT NULL, PRIMARY KEY (key, model))""")
    return conn


def load_reads(symbol: str | None = None, db_path: Path | str = DB_PATH) -> pd.DataFrame:
    conn = connect(db_path)
    try:
        q, p = "SELECT * FROM llm_reads", ()
        if symbol:
            q, p = q + " WHERE symbol = ?", (symbol.upper(),)
        return pd.read_sql_query(q + " ORDER BY an_date DESC", conn, params=p)
    finally:
        conn.close()


def read_recent(symbol: str, *, rows: list[dict] | None = ..., n: int = 8, chat=None,
                model: str | None = None, db_path: Path | str = DB_PATH) -> dict:
    """{state, reads[], tone{}, skipped_no_text, note}. state: OK / NOT_CHECKED
    (the NSE feed could not be read) / LLM_DOWN (nothing new could be read)."""
    import local_llm as ll
    sym = symbol.upper()
    model = model or ll.DEFAULT_MODEL
    tag = f"{model}@v{PROMPT_V}"                  # what is stored and reused
    chat = chat or ll.chat_json
    if rows is ...:
        import concalls
        rows = concalls.fetch_announcements(sym)
    out = {"state": "OK", "reads": [], "tone": {s: 0 for s in SENTIMENTS},
           "skipped_no_text": 0, "note": "", "model": tag}
    if rows is None:
        out.update(state="NOT_CHECKED", note="NSE announcements feed unavailable")
        return out
    conn = connect(db_path)
    try:
        for row in list(rows)[:n]:
            text = str(row.get("attchmntText") or "").strip()
            if not text:
                out["skipped_no_text"] += 1
                continue
            key = _key(sym, row)
            hit = conn.execute("SELECT sentiment, materiality, summary, numbers, error FROM "
                               "llm_reads WHERE key=? AND model=?", (key, tag)).fetchone()
            if hit is None:
                user = (f"Company: {sym}\nSubject: {row.get('desc') or ''}\n"
                        f"Filing text: {text[:MAX_TEXT]}")
                got, err = chat(SYSTEM, user, model=model)
                if got is None:
                    out.update(state="LLM_DOWN" if not out["reads"] else "OK", note=err or "")
                    if not out["reads"]:
                        return out
                    break
                sent = str(got.get("sentiment", "")).lower()
                mat = str(got.get("materiality", "")).lower()
                bad = [f for f, v, ok in (("sentiment", sent, SENTIMENTS),
                                          ("materiality", mat, MATERIALITY)) if v not in ok]
                hit = (sent if sent in SENTIMENTS else None,
                       mat if mat in MATERIALITY else None,
                       str(got.get("summary") or "")[:300],
                       ", ".join(map(str, got.get("numbers") or []))[:200],
                       ("invalid " + "/".join(bad)) if bad else None)
                conn.execute("INSERT OR REPLACE INTO llm_reads VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                             (key, tag, sym, _date(row), str(row.get("desc") or ""),
                              row.get("attchmntFile"), *hit,
                              datetime.now().isoformat(timespec="seconds")))
                conn.commit()
            sent, mat, summary, numbers, err = hit
            out["reads"].append({"date": _date(row), "subject": row.get("desc"),
                                 "file": row.get("attchmntFile"), "sentiment": sent,
                                 "materiality": mat, "summary": summary, "numbers": numbers,
                                 "error": err, "model": tag})
            if sent in out["tone"]:
                out["tone"][sent] += 1
    finally:
        conn.close()
    return out
