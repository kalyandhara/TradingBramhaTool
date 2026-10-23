"""Tests for sector_lobby (SL-1). Offline: resolution and downloads are injected."""
from __future__ import annotations

import pandas as pd
import pytest

import sector_lobby as sl


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """No test may reach screener.in; the ones that need it inject a fake."""
    monkeypatch.setattr(sl, "screener_peers", lambda *a, **k: None)


def _frame(closes, start="2026-01-01"):
    idx = pd.bdate_range(start, periods=len(closes))
    return pd.DataFrame({"open": closes, "high": [c * 1.01 for c in closes],
                         "low": [c * 0.99 for c in closes], "close": closes,
                         "volume": [1000] * len(closes)}, index=idx)


def _resolver(ok=True, peers=("HAL", "BEL", "PARAS"), label="Aerospace & Defense"):
    def resolve(anchor, max_peers):
        assert max_peers >= 1000, "lobby must not inherit the 12-peer scoring cap"
        return {"ok": ok, "reason": None if ok else "too few peers",
                "group_label": label if ok else None, "group_level": "industry",
                "industry": label, "macro_sector": "Capital Goods",
                "peers": list(peers), "tags": {}}
    return resolve


# ── membership ────────────────────────────────────────────────────────────────
def test_members_start_with_anchor_and_skip_cap():
    out = sl.lobby_members("aequs", resolve=_resolver(), overrides={})
    assert out["ok"] and out["members"] == ["AEQUS", "HAL", "BEL", "PARAS"]


def test_overrides_pin_and_exclude_but_never_evict_anchor():
    ov = {"Aerospace & Defense": {"pin": ["azad", "HAL"], "exclude": ["BEL", "AEQUS"]}}
    out = sl.lobby_members("AEQUS", resolve=_resolver(), overrides=ov)
    assert out["members"] == ["AEQUS", "HAL", "PARAS", "AZAD"]


def test_failed_resolution_carries_reason():
    out = sl.lobby_members("XYZ", resolve=_resolver(ok=False), overrides={})
    assert not out["ok"] and out["members"] == [] and out["reason"]


def test_bad_overrides_file_reads_empty(tmp_path):
    p = tmp_path / "o.json"
    p.write_text("{not json", encoding="utf-8")
    assert sl.load_overrides(p) == {}
    assert sl.load_overrides(tmp_path / "missing.json") == {}


# ── prices ────────────────────────────────────────────────────────────────────
def test_quote_facts_math():
    closes = [100.0] * 200 + [110.0]
    f = sl.quote_facts(_frame(closes))
    assert f["chg_1d"] == pytest.approx(10.0)
    assert f["ret_1m"] == pytest.approx(10.0)
    assert f["hi52"] == pytest.approx(111.1)
    assert len(f["spark"]) == sl.SPARK_BARS


def test_quote_facts_missing_is_none_not_zero():
    f = sl.quote_facts(None)
    assert f["chg_1d"] is None and f["last"] is None and f["spark"] == []
    short = sl.quote_facts(_frame([100.0, 101.0]))
    assert short["ret_1m"] is None and short["ret_6m"] is None


def test_fetch_frames_single_batched_call_and_missing_ticker():
    calls = []
    def download(tickers, **kw):
        calls.append(tickers)
        a, b = _frame([1.0, 2.0]), _frame([3.0, 4.0])
        return pd.concat({"AAA.NS": a, "BBB.NS": b}, axis=1)
    out = sl.fetch_frames(["AAA", "BBB", "CCC"], download=download)
    assert len(calls) == 1 and calls[0] == ["AAA.NS", "BBB.NS", "CCC.NS"]
    assert out["AAA"]["close"].iloc[-1] == 2.0 and out["CCC"] is None


def test_fetch_frames_network_failure_is_all_none():
    def boom(*a, **k): raise OSError("offline")
    assert sl.fetch_frames(["A", "B"], download=boom) == {"A": None, "B": None}


# ── ordering and context ──────────────────────────────────────────────────────
def _cards():
    return [{"symbol": "A", "chg_1d": 2.0, "ret_1m": None, "ret_6m": 5.0, "mcap_cr": 10},
            {"symbol": "B", "chg_1d": None, "ret_1m": 1.0, "ret_6m": None, "mcap_cr": 30},
            {"symbol": "C", "chg_1d": -1.0, "ret_1m": 3.0, "ret_6m": 9.0, "mcap_cr": 20}]


def test_sort_puts_missing_last():
    assert [c["symbol"] for c in sl.sort_cards(_cards(), "Today %")] == ["A", "C", "B"]
    assert [c["symbol"] for c in sl.sort_cards(_cards(), "Market cap")] == ["B", "C", "A"]


def test_sector_context_ranks_over_priced_only():
    ctx = sl.sector_context(_cards(), "C")
    assert ctx["rank_chg_1d"] == (2, 2)
    assert ctx["rank_ret_6m"] == (1, 2)
    assert ctx["advancers"] == 1 and ctx["decliners"] == 1
    assert ctx["avg_1d"] == pytest.approx(0.5)
    assert sl.sector_context(_cards(), "B")["rank_chg_1d"] == (None, 2)


def test_relative_series_excludes_self():
    frames = {"A": _frame([10.0, 20.0]), "B": _frame([10.0, 10.0]), "C": None}
    own, avg = sl.relative_series(frames, "A", ["A", "B", "C"])
    assert list(own) == [100.0, 200.0] and list(avg) == [100.0, 100.0]


# ── rendering ────────────────────────────────────────────────────────────────
def test_ribbon_marks_active_and_escapes():
    cards = [{"symbol": "A&B", "name": "<x>", "last": 1.0, "chg_1d": 1.0,
              "spark": [1, 2, 3]},
             {"symbol": "C", "name": "C Ltd", "last": None, "chg_1d": None, "spark": []}]
    doc = sl.ribbon_html(cards, "C", pill_marker="m")
    assert 'class="card active" data-sym="C"' in doc
    assert "A&amp;B" in doc and "&lt;x&gt;" in doc and sl.NA in doc


def test_sparkline_colour_follows_baseline():
    assert sl.GOOD in sl.sparkline_svg([1, 2, 3], 1)
    assert sl.RISK in sl.sparkline_svg([3, 2, 1], 3)


def test_opener_links_are_real_anchors():
    out = sl.opener_links("M&M")
    assert 'href="?nav=analyze&symbol=M%26M"' in out
    assert 'href="?nav=predict&symbol=M%26M"' in out
    assert "M&amp;M" in out and "<button" not in out


def test_cross_sector_rung_finds_peers_outside_nse_sector():
    """JSLL: NSE says Consumer Services, yfinance says Medical Care Facilities."""
    def resolve(anchor, max_peers):
        return {"ok": False, "reason": "Only 0 tagged peer(s)", "macro_sector": "Consumer Services",
                "tags": {"JSLL": {"industry": "Medical Care Facilities", "sector": "Healthcare"},
                         "IHCL": {"industry": "Lodging", "sector": "Consumer Cyclical"}}}
    universe = {"JSLL": {"macro_sector": "Consumer Services"},
                "IHCL": {"macro_sector": "Consumer Services"},
                **{h: {"macro_sector": "Healthcare"} for h in ("APOLLOHOSP", "MAXHEALTH", "FORTIS", "KIMS", "SUNPHARMA")}}
    hosp = {h: {"industry": "Medical Care Facilities", "sector": "Healthcare", "market_cap_cr": i}
            for i, h in enumerate(("KIMS", "FORTIS", "MAXHEALTH", "APOLLOHOSP"))}
    tagged = []
    def tag(pool):
        tagged.extend(pool)
        return {**hosp, "SUNPHARMA": {"industry": "Drug Manufacturers - Specialty & Generic"}}
    deps = {"universe": universe, "cache": {}, "tag": tag, "family": lambda i: i,
            "min_peers": 4, "pool_cap": 220}
    out = sl.lobby_members("JSLL", resolve=resolve, overrides={}, cross=deps)
    assert out["ok"] and out["cross_sector"]
    assert out["members"] == ["JSLL", "APOLLOHOSP", "MAXHEALTH", "FORTIS", "KIMS"]
    assert "IHCL" not in tagged and "APOLLOHOSP" in tagged
    assert "Healthcare" in out["macro_sector"]


def test_cross_sector_still_honours_floor():
    def resolve(anchor, max_peers):
        return {"ok": False, "reason": "thin", "macro_sector": "X",
                "tags": {"A": {"industry": "Rare", "sector": "Healthcare"}}}
    deps = {"universe": {"A": {"macro_sector": "X"}, "B": {"macro_sector": "Healthcare"}},
            "cache": {}, "tag": lambda pool: {"B": {"industry": "Rare"}},
            "family": lambda i: i, "min_peers": 4, "pool_cap": 220}
    out = sl.lobby_members("A", resolve=resolve, overrides={}, cross=deps)
    assert not out["ok"] and out["reason"] == "thin"


def test_valuation_facts():
    v = sl.valuation_facts({"trailingPE": 42.5, "trailingEps": 29.0, "operatingMargins": 0.2134})
    assert v == {"pe": 42.5, "eps": 29.0, "opm": pytest.approx(21.34)}
    loss = sl.valuation_facts({"trailingEps": -3.05, "operatingMargins": -0.1}, last=266.95)
    assert loss["pe"] is None and loss["eps"] == -3.05 and loss["opm"] == pytest.approx(-10.0)
    derived = sl.valuation_facts({"trailingEps": 10.0}, last=250.0)
    assert derived["pe"] == pytest.approx(25.0) and derived["opm"] is None
    assert sl.valuation_facts(None) == {"pe": None, "eps": None, "opm": None}


def test_fetch_valuations_survives_failures():
    def info(sym):
        if sym == "BAD":
            raise OSError("offline")
        return {"trailingPE": 10, "trailingEps": 2, "operatingMargins": 0.1}
    out = sl.fetch_valuations(["OK", "BAD"], info_fn=info)
    assert out["OK"]["pe"] == 10 and out["BAD"] == {"pe": None, "eps": None, "opm": None}


def test_median_ignores_missing():
    assert sl.median([3, None, 1, 2]) == 2
    assert sl.median([1, 4]) == 2.5 and sl.median([None]) is None


def test_off_index_anchor_is_tagged_and_matched_by_industry():
    """PREMIERPOL: not in the constituent files, so resolve_peers has no pool."""
    def resolve(anchor, max_peers):
        return {"ok": False, "reason": "not in the cached lists", "macro_sector": None, "tags": {}}
    universe = {s: {"macro_sector": "Chemicals"} for s in ("SUPREMEIND", "ASTRAL", "FINPIPE", "PRINCEPIPE", "PIDILITIND")}
    cache = {"SUPREMEIND": {"industry": "Specialty Chemicals", "sector": "Basic Materials"}}
    def tag(pool):
        if pool == ["PREMIERPOL"]:
            return {"PREMIERPOL": {"industry": "Specialty Chemicals", "sector": "Basic Materials",
                                   "market_cap_cr": 300}}
        return {s: {"industry": "Specialty Chemicals", "market_cap_cr": i}
                for i, s in enumerate(("SUPREMEIND", "ASTRAL", "FINPIPE", "PRINCEPIPE"))}
    deps = {"universe": universe, "cache": cache, "tag": tag, "family": lambda i: i,
            "min_peers": 4, "pool_cap": 220}
    out = sl.lobby_members("PREMIERPOL", resolve=resolve, overrides={}, cross=deps)
    assert out["ok"] and out["off_index"] and out["members"][0] == "PREMIERPOL"
    assert set(out["members"][1:]) == {"SUPREMEIND", "ASTRAL", "FINPIPE", "PRINCEPIPE"}
    assert out["tags"]["PREMIERPOL"]["market_cap_cr"] == 300


def test_off_index_untaggable_keeps_original_reason():
    def resolve(anchor, max_peers):
        return {"ok": False, "reason": "not in the cached lists", "tags": {}}
    deps = {"universe": {}, "cache": {}, "tag": lambda pool: {}, "family": lambda i: i,
            "min_peers": 4, "pool_cap": 220}
    out = sl.lobby_members("NOPE", resolve=resolve, overrides={}, cross=deps)
    assert not out["ok"] and out["reason"] == "not in the cached lists"


# ── screener.in fallback ─────────────────────────────────────────────────────
COMPANY_PAGE = """
<a href="/market/IN07/" target="_blank" title="Broad Sector">Industrials</a>
<a href="/market/IN07/IN0702/" title="Sector">Capital Goods</a>
<a href="/market/IN07/IN0702/IN070205/" title="Industry">Industrial Products</a>
<a href="/market/IN07/IN0702/IN070205/IN070205009/" title="Basic">Plastic Products - Industrial</a>
<a href="/market/IN07/" >Industrials</a>
"""

def _row(i, sym, name, pe, mcap):
    return (f'<tr> <td class="text">{i}.</td> <td class="text"> <a href="/company/{sym}/consolidated/" '
            f'target="_blank">{name}</a> </td> <td>100.00</td><td>{pe}</td><td>{mcap}</td>'
            f'<td>1.0</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td> </tr>')

LISTING = ("<table><tr><th>S.No.</th></tr>"
           + _row(1, "SUPREMEIND", "Supreme Inds.", "42.58", "43,980.51")
           + _row(2, "ASTRAL", "Astral", "64.38", "38121.50")
           + _row(3, "540693", "BSE only", "10", "50")
           + _row(4, "PREMIERPOL", "Premier Polyfilm", "18.20", "312.40")
           + _row(5, "PPL", "Prakash Pipes", "", "600")
           + _row(6, "KRITI", "Kriti Inds.", "30", "700")
           + "</table>")


def test_parse_company_classification_picks_deepest_chain():
    c = sl.parse_company_classification(COMPANY_PAGE)
    assert c["path"] == "/market/IN07/IN0702/IN070205/IN070205009/"
    assert c["labels"] == ["Industrials", "Capital Goods", "Industrial Products",
                           "Plastic Products - Industrial"]
    assert sl.parse_company_classification("<html></html>") is None


def test_parse_market_rows_drops_bse_codes_and_reads_numbers():
    rows = sl.parse_market_rows(LISTING)
    assert [r["symbol"] for r in rows] == ["SUPREMEIND", "ASTRAL", "PREMIERPOL", "PPL", "KRITI"]
    assert rows[0]["mcap_cr"] == pytest.approx(43980.51) and rows[0]["pe"] == pytest.approx(42.58)
    assert rows[3]["pe"] is None



def test_screener_peers_real_function(tmp_path):
    import importlib
    fresh = importlib.reload(sl)              # undo the autouse stub for this test
    calls = []
    def get(url):
        calls.append(url)
        return COMPANY_PAGE if "/company/" in url else LISTING
    p = tmp_path / "c.json"
    out = fresh.screener_peers("premierpol", get=get, cache_path=p, now=1000.0)
    assert out["label"] == "Plastic Products - Industrial" and len(out["rows"]) == 5
    assert "limit=50&page=1" in calls[1] and len(calls) == 2      # short page -> stop
    again = fresh.screener_peers("PREMIERPOL", get=lambda u: None, cache_path=p, now=2000.0)
    assert again["rows"] == out["rows"]                            # served from cache
    stale = fresh.screener_peers("PREMIERPOL", get=lambda u: None, cache_path=p,
                                 now=1000.0 + fresh.SCREENER_TTL + 1)
    assert stale is None


def test_lobby_falls_back_to_screener_when_yfinance_rungs_fail():
    def resolve(anchor, max_peers):
        return {"ok": False, "reason": "not in the cached lists", "tags": {}}
    deps = {"universe": {}, "cache": {}, "tag": lambda pool: {}, "family": lambda i: i,
            "min_peers": 4, "pool_cap": 220}
    sp = {"label": "Plastic Products - Industrial",
          "labels": ["Industrials", "Capital Goods", "Industrial Products", "Plastic Products - Industrial"],
          "rows": sl.parse_market_rows(LISTING)}
    out = sl.lobby_members("PREMIERPOL", resolve=resolve, overrides={}, cross=deps,
                           screener=lambda a: sp)
    assert out["ok"] and out["source"] == "screener.in" and out["level"] == "nse_basic"
    assert out["members"] == ["PREMIERPOL", "SUPREMEIND", "ASTRAL", "PPL", "KRITI"]
    assert out["tags"]["PREMIERPOL"]["market_cap_cr"] == pytest.approx(312.4)
    assert out["macro_sector"] == "Industrials › Capital Goods › Industrial Products"


def test_screener_source_skips_yfinance():
    def resolve(anchor, max_peers):
        raise AssertionError("yfinance resolution must not run for source=screener")
    sp = {"label": "X", "labels": ["A", "X"], "rows": sl.parse_market_rows(LISTING)}
    out = sl.lobby_members("PREMIERPOL", resolve=resolve, overrides={}, source="screener",
                           screener=lambda a: sp)
    assert out["ok"] and out["source"] == "screener.in"
    thin = sl.lobby_members("PREMIERPOL", resolve=resolve, overrides={}, source="screener",
                            screener=lambda a: None)
    assert not thin["ok"] and "screener.in" in thin["reason"]
