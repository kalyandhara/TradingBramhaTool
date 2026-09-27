"""NSE index CSVs carry DUMMY<TICKER> placeholder rows during corporate actions
(seen: DUMMYHEG). Both universe loaders must drop them at the source."""
from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CSV = ("Company Name,Industry,Symbol,Series,ISIN Code\n"
       "HEG Limited,Capital Goods,HEG,EQ,INE545A01016\n"
       "Dummy HEG,Capital Goods,DUMMYHEG,EQ,INE545A01024\n"
       "Reliance,Oil Gas,RELIANCE,EQ,INE002A01018\n")


class _Resp:
    text = CSV
    def raise_for_status(self): pass


def test_nse_universe_drops_dummy_rows(monkeypatch, tmp_path):
    import nse_universe as nu
    monkeypatch.setattr(nu.requests, "get", lambda *a, **k: _Resp())
    monkeypatch.setattr(nu, "_write_cache", lambda *a, **k: None)
    nu._MEMO.clear()
    syms = [r["symbol"] for r in nu.fetch_constituents("nifty500", use_cache=False)]
    assert syms == ["HEG", "RELIANCE"]


def test_smallcap_universe_drops_dummy_rows(monkeypatch):
    import smallcap_universe as su
    sess = types.SimpleNamespace(get=lambda *a, **k: _Resp())
    monkeypatch.setattr(su._nsf, "_new_session", lambda: sess)
    kind = next(iter(su.INDEX_CSV))
    syms = [r["symbol"] for r in su._fetch_index_csv(kind)]
    assert syms == ["HEG", "RELIANCE"]
