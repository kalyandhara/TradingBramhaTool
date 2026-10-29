"""Tests for the digest's timezone-safe lookups and its filings/alerts sections.

What is pinned:
  * the shortlist lookup falls back to the newest stored date, because the
    digest dates itself in IST while opportunity_daily stores the machine's
    US-Eastern date (an exact lookup found nothing);
  * the filings/alerts sections read a rolling 24h window, not "today";
  * filing text is HTML-escaped and a held name is listed first.
"""
import json
from datetime import datetime, timedelta, timezone

import daily_digest_email as dde


def test_latest_run_date_falls_back(monkeypatch):
    monkeypatch.setattr(dde.db, "get_opportunity_run_dates",
                        lambda: ["2026-10-28", "2026-10-26"])
    assert dde._latest_run_date("2026-10-30") == "2026-10-28"
    assert dde._latest_run_date("2026-10-27") == "2026-10-26"


def test_recent_jsonl_keeps_last_24h(tmp_path, monkeypatch):
    monkeypatch.setattr(dde, "ALERT_DIR", tmp_path)
    now = datetime.now()
    rows = [{"symbol": "OLD", "ts": (now - timedelta(hours=30)).isoformat()},
            {"symbol": "NEW", "ts": (now - timedelta(hours=2)).isoformat()},
            {"symbol": "UTC", "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}]
    (tmp_path / "x.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\nnot json\n", encoding="utf-8")
    assert [r["symbol"] for r in dde._collect_recent_jsonl("x.jsonl")] == ["NEW", "UTC"]


def test_filings_html_escapes_and_orders():
    html = dde._filings_html([
        {"symbol": "TRF", "why": "watchlist", "bucket": "RESULTS", "headline": "<b>x</b>"},
        {"symbol": "HERANBA", "why": "held", "bucket": "GOVERNANCE", "headline": "y"}])
    assert "<b>x</b>" not in html and "&lt;b&gt;" in html
    assert html.index("HERANBA") < html.index("TRF")
