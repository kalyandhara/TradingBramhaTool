"""NSE participant-wise OI parsing — B-95. Offline; fixture text mirrors the real file.

Run:  python -m pytest tools/test_participant_oi.py -q
"""
import participant_oi as p

FILE = (
    '"Participant wise Open Interest (no. of contracts) in Equity Derivatives as on Oct 13, 2026",,,,\n'
    "Client Type,Future Index Long,Future Index Short,Future Stock Long,Future Stock Short\t\n"
    "Client,200000,100000,3000000,1000000\n"
    "DII,50000,10000,200000,4000000\n"
    "FII,25000,225000,1500000,1200000\n"
    "Pro,30000,20000,500000,400000\n"
    "TOTAL,305000,355000,5200000,6600000\n"
)


def test_parse_reads_every_class_and_normalises_headers():
    r = p.parse(FILE)
    assert set(p.CLASSES) <= set(r)
    assert r["FII"]["future index long"] == 25000
    assert r["FII"]["future stock short"] == 1200000      # trailing tab in the header


def test_fii_long_share_is_long_over_long_plus_short():
    r = p.parse(FILE)
    assert p.index_futures_long_share(r, "FII") == 0.1        # "90% short"
    assert round(p.index_futures_long_share(r, "Client"), 4) == round(200000 / 300000, 4)


def test_not_a_participant_file_is_none():
    assert p.parse("<html>Not found</html>") is None
    assert p.parse("Client Type,Future Index Long\nClient,1\n") is None   # classes missing


def test_zero_book_has_no_share():
    assert p.index_futures_long_share({"FII": {"future index long": 0, "future index short": 0}}) is None


def test_bare_cr_line_endings_parse():
    """2017 files use '\r' alone; the csv module raised on them and killed a backfill."""
    assert p.parse(FILE.replace("\n", "\r"))["FII"]["future index long"] == 25000
