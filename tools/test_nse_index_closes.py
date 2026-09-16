"""Tests for the NSE all-indices close feed and the sector factor on top of it — B-80.

WHY THIS SOURCE EXISTS AT ALL. `sentiment_index._sector_perf` read the eleven
sector indices from yfinance and 8 of them went dark. Probed 2026-09-15: those
eight return **exactly one row at every period from `1mo` to `max`**, dated today,
while ^CNXIT / ^CNXPHARMA / ^NSEBANK still return full history. No second bar at
any width means no 1-day change at any width — which is why the fix recorded on
2026-09-10 ("widen the window AND bound the gap between the two bars") could not
be built as written, and why counting first is the only reason that was found
before it was built.

NSE publishes every index's close and `Change(%)` for the session in one CSV. It
is the SAME quantity the factor always claimed, from the exchange that computes
it, so this is a repair rather than a redefinition.

Nothing here touches the network: the session is a stub.

Run:  python -m pytest tools/test_nse_index_closes.py -q
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

import sector_rotation as sr
import sentiment_index as si


HEADER = ("Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,"
          "Closing Index Value,Points Change,Change(%)\n")


def _csv(rows: dict[str, float], day: str = "15-09-2026") -> bytes:
    """An NSE-shaped indices CSV carrying `{index name: change%}`."""
    body = "".join(
        f"{name},{day},100,101,99,{100 + chg},{chg},{chg}\n" for name, chg in rows.items())
    return (HEADER + body).encode()


ALL_ELEVEN = {name: (1.0 if i % 2 == 0 else -1.0)
              for i, name in enumerate(sr.NSE_INDEX_NAMES.values())}


class _Resp:
    def __init__(self, content: bytes, status: int = 200):
        self.content, self.status_code = content, status


class _Session:
    """Serves a canned response per `ddmmyyyy` in the URL; records what was asked."""

    def __init__(self, by_ddmmyyyy: dict[str, _Resp]):
        self._by = by_ddmmyyyy
        self.asked: list[str] = []

    def get(self, url, timeout=None):
        key = url.rsplit("_", 1)[-1].replace(".csv", "")
        self.asked.append(key)
        r = self._by.get(key)
        if r is None:
            return _Resp(b"", 404)
        return r


@pytest.fixture(autouse=True)
def _no_cache(tmp_path, monkeypatch):
    """Point the disk cache at a temp dir so tests never read or write the real one."""
    monkeypatch.setattr(sr, "_NSE_CACHE_DIR", tmp_path / "nse_indices")


# ── The map ──────────────────────────────────────────────────────────────────

def test_every_sector_ticker_has_an_nse_index_name():
    """The eleven the factor scores and the eleven this map names are the same set.
    A ticker added to SECTOR_INDEX_MAP without a name here would silently go
    unscored — the failure mode B-80 exists to end."""
    used = set(sr.SECTOR_INDEX_MAP.values())
    assert used == set(sr.NSE_INDEX_NAMES), used ^ set(sr.NSE_INDEX_NAMES)


def test_all_eleven_resolve_from_a_full_file():
    sess = _Session({"15092026": _Resp(_csv(ALL_ELEVEN))})
    got = sr.nse_index_changes(date(2026, 9, 15), session=sess)
    assert len(got) == 11
    assert set(got) == set(sr.NSE_INDEX_NAMES)


def test_an_index_absent_from_the_file_is_omitted_not_zeroed():
    """Absent must render absent. A missing sector scored as 0.0% would count as
    a FLAT toward the factor — an unmeasured input masquerading as a measurement."""
    partial = dict(list(ALL_ELEVEN.items())[:9])
    sess = _Session({"15092026": _Resp(_csv(partial))})
    got = sr.nse_index_changes(date(2026, 9, 15), session=sess)
    assert len(got) == 9
    assert all(v["chg_pct"] is not None for v in got.values())


def test_the_change_and_date_travel_with_each_index():
    # A full file, not a one-row one: the real CSV carries 166 indices and the
    # fetcher rejects a short body precisely so a truncated or error response
    # cannot be parsed as data.
    sess = _Session({"15092026": _Resp(_csv({**ALL_ELEVEN, "Nifty Bank": -1.43}))})
    got = sr.nse_index_changes(date(2026, 9, 15), session=sess)
    assert got["^NSEBANK"]["chg_pct"] == -1.43
    assert got["^NSEBANK"]["index_date"] == "2026-09-15"
    assert got["^NSEBANK"]["name"] == "Nifty Bank"


# ── Finding a session file ───────────────────────────────────────────────────

def test_a_weekend_walks_back_to_friday():
    """NSE publishes nothing on Saturday. "No file today" is the normal Sunday
    state and must not read as an outage."""
    sess = _Session({"11092026": _Resp(_csv(ALL_ELEVEN, day="11-09-2026"))})
    df, got_day = sr.fetch_nse_index_closes(date(2026, 9, 13), session=sess)  # a Sunday
    assert got_day == date(2026, 9, 11)
    assert df is not None
    assert "12092026" not in sess.asked and "13092026" not in sess.asked


def test_a_holiday_html_error_page_is_not_mistaken_for_data():
    """NSE serves a holiday as an HTML error page with status 200, so the status
    code is not the test — the content is."""
    html = b"<html><head><title>Error</title></head><body>" + b"x" * 900 + b"</body></html>"
    sess = _Session({"15092026": _Resp(html),
                     "14092026": _Resp(_csv(ALL_ELEVEN, day="14-09-2026"))})
    _, got_day = sr.fetch_nse_index_closes(date(2026, 9, 15), session=sess)
    assert got_day == date(2026, 9, 14)


def test_a_short_body_is_rejected():
    sess = _Session({"15092026": _Resp(b"Index Name\n"),
                     "14092026": _Resp(_csv(ALL_ELEVEN, day="14-09-2026"))})
    _, got_day = sr.fetch_nse_index_closes(date(2026, 9, 15), session=sess)
    assert got_day == date(2026, 9, 14)


def test_nothing_found_within_the_backtrack_returns_none_not_an_exception():
    sess = _Session({})
    df, got_day = sr.fetch_nse_index_closes(date(2026, 9, 15), session=sess)
    assert df is None and got_day is None
    assert sr.nse_index_changes(date(2026, 9, 15), session=sess) == {}


def test_the_file_is_cached_per_session_and_not_refetched(tmp_path):
    """The published file is immutable, so a second call must not hit the network."""
    sess = _Session({"15092026": _Resp(_csv(ALL_ELEVEN))})
    sr.fetch_nse_index_closes(date(2026, 9, 15), session=sess)
    n_first = len(sess.asked)
    sr.fetch_nse_index_closes(date(2026, 9, 15), session=sess)
    assert len(sess.asked) == n_first


# ── The factor on top of it ──────────────────────────────────────────────────

def test_the_factor_scores_all_eleven_from_nse(monkeypatch):
    monkeypatch.setattr(sr, "nse_index_changes",
                        lambda *a, **k: {t: {"chg_pct": 1.0, "close": 100.0,
                                             "index_date": date.today().isoformat(),
                                             "name": n}
                                         for t, n in sr.NSE_INDEX_NAMES.items()})
    out = si._sector_perf()
    assert out["state"] == "OK"
    assert out["n_scored"] == out["n_expected"] == 11
    assert out["by_source"] == {"nse": 11}
    assert out["greens"] == 11 and out["factor"] == 1.0


def test_a_stale_nse_session_is_reported_stale_not_scored(monkeypatch):
    """The SAME age rule the yfinance path applies. A file found by walking back
    over a long shutdown is stale for exactly the reason a stale bar is, and must
    not be scored just because it came from a better source."""
    old = date.today().replace(year=date.today().year - 1).isoformat()
    monkeypatch.setattr(sr, "nse_index_changes",
                        lambda *a, **k: {t: {"chg_pct": 1.0, "close": 100.0,
                                             "index_date": old, "name": n}
                                         for t, n in sr.NSE_INDEX_NAMES.items()})
    monkeypatch.setattr(si.yf, "Ticker", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("no fallback in this test")))
    out = si._sector_perf()
    assert out["n_stale"] == 11 and out["n_scored"] == 0
    assert out["state"] == si.NOT_CHECKED


def test_yfinance_covers_only_what_nse_did_not_answer(monkeypatch):
    """The fallback is kept for the day NSE's archive is unreachable, and must not
    re-fetch a ticker NSE already answered."""
    nse_half = dict(list(sr.NSE_INDEX_NAMES.items())[:7])
    monkeypatch.setattr(sr, "nse_index_changes",
                        lambda *a, **k: {t: {"chg_pct": 1.0, "close": 100.0,
                                             "index_date": date.today().isoformat(),
                                             "name": n}
                                         for t, n in nse_half.items()})
    asked: list[str] = []

    class _T:
        def __init__(self, tkr):
            asked.append(tkr)

        def history(self, **kw):
            idx = pd.to_datetime([date.today(), date.today()])
            return pd.DataFrame({"Close": [100.0, 99.0]}, index=idx)

    monkeypatch.setattr(si.yf, "Ticker", _T)
    out = si._sector_perf()
    assert sorted(asked) == sorted(set(sr.NSE_INDEX_NAMES) - set(nse_half))
    assert out["by_source"] == {"nse": 7, "yfinance": 4}
    assert out["n_scored"] == 11


def test_a_total_nse_outage_falls_all_the_way_back_to_yfinance(monkeypatch):
    monkeypatch.setattr(sr, "nse_index_changes", lambda *a, **k: {})

    class _T:
        def __init__(self, tkr):
            pass

        def history(self, **kw):
            idx = pd.to_datetime([date.today(), date.today()])
            return pd.DataFrame({"Close": [100.0, 101.0]}, index=idx)

    monkeypatch.setattr(si.yf, "Ticker", _T)
    out = si._sector_perf()
    assert out["by_source"] == {"yfinance": 11}


def test_an_nse_exception_does_not_take_the_factor_down(monkeypatch):
    """A new upstream must not be able to break a component that worked without it."""
    def _boom(*a, **k):
        raise RuntimeError("nsearchives unreachable")

    monkeypatch.setattr(sr, "nse_index_changes", _boom)

    class _T:
        def __init__(self, tkr):
            pass

        def history(self, **kw):
            idx = pd.to_datetime([date.today(), date.today()])
            return pd.DataFrame({"Close": [100.0, 101.0]}, index=idx)

    monkeypatch.setattr(si.yf, "Ticker", _T)
    assert si._sector_perf()["n_scored"] == 11


def test_green_red_flat_thresholds_are_unchanged_by_the_source_swap(monkeypatch):
    """The repair must not move the boundaries: ±0.05% stays the flat band."""
    changes = {"Nifty Bank": 0.04, "Nifty IT": 0.06, "Nifty Auto": -0.06}
    tick = {n: t for t, n in sr.NSE_INDEX_NAMES.items()}
    monkeypatch.setattr(sr, "nse_index_changes",
                        lambda *a, **k: {tick[n]: {"chg_pct": c, "close": 100.0,
                                                   "index_date": date.today().isoformat(),
                                                   "name": n}
                                         for n, c in changes.items()})
    monkeypatch.setattr(si.yf, "Ticker", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("no fallback")))
    out = si._sector_perf()
    assert (out["greens"], out["reds"], out["flats"]) == (1, 1, 1)
