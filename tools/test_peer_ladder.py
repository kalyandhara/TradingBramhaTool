"""peer_comparison.build falls back through the Sector Lobby's ladder.

Offline: the first rung (`resolve_peers`) and the lobby fallback are injected,
and scoring is a stub, so nothing here reaches yfinance or screener.in.
"""
from __future__ import annotations

import pytest

import peer_comparison as pcmp


def _score(sym: str) -> dict:
    return {}


@pytest.fixture
def first_rung(monkeypatch):
    """Make resolve_peers return a canned result."""
    def set_(res):
        monkeypatch.setattr(pcmp, "resolve_peers", lambda a, **k: dict(res))
    return set_


@pytest.fixture(autouse=True)
def _stub_scoring(monkeypatch):
    monkeypatch.setattr(pcmp, "score_peer_group",
                        lambda anchor, peers, fn, tags=None, progress_cb=None:
                        pcmp.pd.DataFrame({"symbol": [anchor, *peers]}))
    monkeypatch.setattr(pcmp, "peer_median", lambda df: {})
    monkeypatch.setattr(pcmp, "rank_report", lambda df, a: {})


_FAILED = {"ok": False, "anchor": "UTTAMSUGAR", "peers": [], "tags": {},
           "industry": None, "macro_sector": None, "n_same_industry": 0,
           "reason": "UTTAMSUGAR is not in the cached NIFTY-500 / Total-Market lists."}


def test_first_rung_ok_never_touches_the_ladder(first_rung):
    first_rung({"ok": True, "peers": ["A", "B", "C", "D"], "tags": {},
                "group_level": "industry", "group_label": "Sugar"})
    def boom(*a, **k):
        raise AssertionError("ladder must not run when the first rung succeeds")
    res = pcmp.build("X", _score, lobby=boom)
    assert res["ok"] and res["source"] == "yfinance"
    assert res["peers"] == ["A", "B", "C", "D"]


def test_screener_rung_scores_top_twelve_by_market_cap(first_rung):
    first_rung(_FAILED)
    tags = {f"P{i}": {"market_cap_cr": float(i), "industry": "Sugar"} for i in range(20)}
    tags["UTTAMSUGAR"] = {"market_cap_cr": 999.0, "industry": "Sugar"}
    lob = {"ok": True, "label": "Sugar", "level": "nse_basic", "source": "screener.in",
           "cross_sector": False, "macro_sector": "FMCG › Agricultural Food",
           "tags": tags, "members": ["UTTAMSUGAR", *tags.keys() - {"UTTAMSUGAR"}]}
    res = pcmp.build("uttamsugar", _score, lobby=lambda a, r: lob)
    assert res["ok"] and res["reason"] is None
    assert res["source"] == "screener.in" and res["group_level"] == "nse_basic"
    assert res["group_label"] == "Sugar"
    assert res["peers"] == [f"P{i}" for i in range(19, 7, -1)]   # 12, biggest first
    assert res["n_in_group"] == 20
    assert "UTTAMSUGAR" not in res["peers"]
    assert list(res["table"]["symbol"])[0] == "UTTAMSUGAR"


def test_cross_sector_rung_is_reported_as_such(first_rung):
    first_rung({**_FAILED, "anchor": "JSLL"})
    tags = {s: {"market_cap_cr": 1.0, "industry": "Medical Care Facilities"}
            for s in ("JSLL", "APOLLOHOSP", "MAXHEALTH", "FORTIS", "KIMS")}
    lob = {"ok": True, "label": "Medical Care Facilities", "level": "industry",
           "source": "yfinance", "cross_sector": True,
           "macro_sector": "Consumer Services + Healthcare", "tags": tags,
           "members": list(tags)}
    res = pcmp.build("JSLL", _score, lobby=lambda a, r: lob)
    assert res["ok"] and res["source"] == "yfinance-cross-sector"
    assert res["peers"] == ["APOLLOHOSP", "MAXHEALTH", "FORTIS", "KIMS"]


def test_ladder_failure_keeps_first_reason_and_says_fallbacks_failed(first_rung):
    first_rung(_FAILED)
    res = pcmp.build("UTTAMSUGAR", _score,
                     lobby=lambda a, r: {"ok": False, "members": []})
    assert not res["ok"] and res["table"] is None
    assert res["reason"].startswith("UTTAMSUGAR is not in the cached")
    assert "screener.in" in res["reason"]


def test_ladder_exception_is_a_failed_group_not_a_crash(first_rung):
    first_rung(_FAILED)
    def boom(a, r):
        raise RuntimeError("screener.in timed out")
    res = pcmp.build("UTTAMSUGAR", _score, lobby=boom)
    assert not res["ok"] and "screener.in" in res["reason"]


@pytest.mark.parametrize("res,needle", [
    ({"source": "yfinance", "group_level": "industry", "industry": "Sugar",
      "group_label": "Sugar", "n_same_industry": 6}, "yfinance"),
    ({"source": "yfinance-cross-sector", "group_level": "industry",
      "group_label": "Medical Care Facilities",
      "macro_sector": "Consumer Services + Healthcare"}, "across NSE sectors"),
    ({"source": "screener.in", "group_level": "nse_basic", "group_label": "Sugar",
      "macro_sector": "FMCG › Agricultural Food"}, "screener.in"),
])
def test_source_label_names_the_source(res, needle):
    assert needle in pcmp.source_label(res)
