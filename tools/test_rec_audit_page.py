"""Recommendation Audit page — pure helpers and registration (A2)."""
from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

from desk_pages import rec_audit_page as page

HERE = Path(__file__).resolve().parent


def _eps():
    return pd.DataFrame({
        "episode_id": ["a", "b", "c", "d"], "symbol": ["A", "B", "C", "M&M"],
        "rank": [1, 7, 30, 2], "risk_flags": ["", "Downside Risk", None, ""],
        "appearances": [1, 3, 6, 1],
        "ret_21": [-9.0, -6.0, 2.0, None], "excess_21": [-4.0, -12.0, 1.0, None],
        "failure": [True, True, False, False],
        "review_tag": ["MARKET_DRAG", "EVENT_GAP", None, None]})


def test_with_slices_bands():
    d = page.with_slices(_eps()).set_index("symbol")
    assert d.loc["A", "rank_band"] == "1-5" and d.loc["C", "rank_band"] == "21+"
    assert d.loc["B", "flagged"] == "flagged" and d.loc["C", "flagged"] == "clean"
    assert d.loc["B", "list_band"] == "2-3 runs" and d.loc["C", "list_band"] == "4+ runs"


def test_review_queue_is_matured_failures_worst_first():
    q = page.review_queue(_eps())
    assert q["symbol"].tolist() == ["B", "A"]
    assert page.review_queue(_eps(), "MARKET_DRAG")["symbol"].tolist() == ["A"]


def test_tag_counts():
    assert page.tag_counts(_eps()) == {"MARKET_DRAG": 1, "EVENT_GAP": 1}


def test_link_encodes_symbol():
    assert page.link("analyze", "M&M").endswith("/?nav=analyze&symbol=M%26M")


def test_page_is_registered_in_registry_and_nav():
    import desk_pages
    assert desk_pages.PAGES["Recommendation Audit"] == "rec_audit_page"
    tree = ast.parse((HERE / "dashboard_app.py").read_text(encoding="utf-8"))
    groups = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  and any(getattr(t, "id", None) == "PAGE_GROUPS" for t in n.targets))
    assert "Recommendation Audit" in ast.literal_eval(groups)["Portfolio & Risk"]


def test_audit_job_is_in_the_scheduler_registry():
    import scheduler_core as sch
    job = sch.JOBS["rec_audit"]
    assert job.default_time == "17:30" and "rec_audit_job.py" in job.command
