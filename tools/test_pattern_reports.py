"""Tests for the Strategy Hub pattern roster (PR-1), offline.

This block's whole history is a table that presented frozen numbers as live, so
what these pin is that it cannot happen again in a new form:

  * **Move % must be DERIVED, never stored.** The frozen version drifted until
    SPLPETRO's row read -13.0% while the live move was +2.4% -- counted on the
    wrong side of its own scoreboard. Deriving it makes that class of drift
    unrepresentable.
  * **A move needs a baseline.** Three rows have no publish price and previously
    carried a hardcoded move anyway. Blank, not a number.
  * **An unpriced symbol renders blank**, never carrying forward a stale value.
  * **The scoreboard counts only what it could score**, and reports the
    denominator.
"""
import pattern_reports as pr


def test_every_roster_row_has_a_symbol_and_a_name():
    assert pr.PATTERNS
    for row in pr.PATTERNS:
        sym, name = row[0], row[1]
        assert isinstance(sym, str) and sym.strip() == sym and sym.isupper() is not None
        assert sym and name


def test_symbols_are_deduplicated_but_keep_roster_order():
    syms = pr.symbols()
    assert len(syms) == len(set(syms))
    # ZEEL and SPLPETRO each appear twice on the roster with different patterns.
    assert syms.count("ZEEL") == 1
    assert syms[0] == pr.PATTERNS[0][0]


def test_move_is_derived_from_the_two_prices():
    assert pr.move_pct(100.0, 110.0) == 10.0
    assert pr.move_pct(100.0, 90.0) == -10.0
    assert pr.move_pct(100.0, 100.0) == 0.0


def test_a_move_without_a_baseline_is_none_not_zero():
    assert pr.move_pct(None, 500.0) is None
    assert pr.move_pct(0.0, 500.0) is None
    assert pr.move_pct(-5.0, 500.0) is None


def test_a_move_without_a_price_is_none():
    assert pr.move_pct(100.0, None) is None


def test_rows_with_no_publish_price_carry_no_move():
    rows = pr.build_rows({s: 1000.0 for s in pr.symbols()})
    noprice = [r for r in rows if r["Pub Price ₹"] is None]
    assert noprice, "the roster should still contain price-less detections"
    for r in noprice:
        assert r["Move %"] is None
        # The detection itself is still a record, so the row survives.
        assert r["Pattern"] and r["Stock"]


def test_an_unpriced_symbol_renders_blank_rather_than_stale():
    rows = pr.build_rows({})           # nothing priced at all
    assert all(r["LTP ₹"] is None for r in rows)
    assert all(r["Move %"] is None for r in rows)


def test_move_tracks_the_price_it_was_given():
    # The regression that motivated PR-1: a stored move that disagrees with the
    # prices beside it. Derivation makes the two inseparable.
    sym, pub = pr.PATTERNS[0][0], pr.PATTERNS[0][5]
    for ltp in (pub * 0.5, pub, pub * 1.5):
        row = next(r for r in pr.build_rows({sym: ltp}) if r["Symbol"] == sym)
        assert row["Move %"] == pr.move_pct(pub, ltp)


def test_scoreboard_counts_only_scored_rows_and_reports_the_denominator():
    rows = pr.build_rows({s: 1000.0 for s in pr.symbols()})
    sb = pr.scoreboard(rows)
    assert sb["total"] == len(pr.PATTERNS)
    assert sb["scored"] < sb["total"]          # the price-less rows drop out
    assert sb["above"] + sb["below"] + sb["flat"] == sb["scored"]


def test_scoreboard_is_empty_when_nothing_could_be_priced():
    sb = pr.scoreboard(pr.build_rows({}))
    assert sb["scored"] == 0
    assert sb["above"] == sb["below"] == 0
    assert sb["total"] == len(pr.PATTERNS)


def test_fetch_prices_returns_empty_rather_than_raising_when_the_feed_is_down(monkeypatch):
    import trending_stocks as ts
    monkeypatch.setattr(ts, "_batch_history", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    assert pr.fetch_prices(["CRISIL"]) == {}


def test_fetch_prices_reads_capitalised_close(monkeypatch):
    # B-60's live run was bitten by exactly this on the same helper: lowercase
    # indexing would silently price nothing.
    import pandas as pd
    import trending_stocks as ts
    df = pd.DataFrame({"Open": [1.0, 2.0], "Close": [10.0, 12.5]})
    monkeypatch.setattr(ts, "_batch_history", lambda syms, period=None: {"CRISIL": df})
    assert pr.fetch_prices(["CRISIL"]) == {"CRISIL": 12.5}


def test_scoreboard_survives_a_round_trip_through_a_dataframe():
    """The bug the live page caught and these tests did not.

    pandas turns a None into a float NaN, and `is not None` is true of NaN. The
    price-less rows were therefore counted as SCORED while falling out of both
    above and below, so the footer read "12 above, 5 below, scored on 20 of 20".
    Going through a DataFrame is what the dashboard actually does, so the test
    has to as well.
    """
    import pandas as pd
    rows = pr.build_rows({s: 1000.0 for s in pr.symbols()})
    df = pd.DataFrame(rows, columns=list(pr.COLUMNS))
    sb = pr.scoreboard(df.to_dict("records"))
    assert sb["above"] + sb["below"] + sb["flat"] == sb["scored"]
    assert sb["scored"] == sum(1 for r in rows if r["Move %"] is not None)
    assert sb["scored"] < sb["total"]


def test_columns_match_what_build_rows_emits():
    row = pr.build_rows({})[0]
    assert set(row) == set(pr.COLUMNS)
