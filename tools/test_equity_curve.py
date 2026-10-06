"""Tests for the equity curve and its drawdown — B-110.

The cases are the ones where a plausible implementation prints a plausible wrong
number: a missing price valued at entry (a flat line exactly where the data is
missing), a realised trade booked on the wrong day, a deposit read as a recovery,
and the two sources silently interleaved.
"""
import pandas as pd
import pytest

import equity_curve as ec


def _bars(closes: dict[str, float]) -> pd.DataFrame:
    idx = pd.DatetimeIndex(pd.to_datetime(list(closes)))
    return pd.DataFrame({"close": list(closes.values())}, index=idx)


def _pos(rows):
    """rows = [(symbol, entry, qty, entry_date, status, closed_price, closed_date)]"""
    return pd.DataFrame([dict(symbol=s, entry_price=e, quantity=q, entry_date=d,
                              status=st, closed_price=cp, closed_date=cd)
                         for s, e, q, d, st, cp, cd in rows])


DAYS = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07"]


def test_an_open_position_is_marked_to_each_close():
    px = {"AAA": _bars(dict(zip(DAYS, [100, 110, 90, 95, 120])))}
    c = ec.reconstruct(_pos([("AAA", 100, 10, "2026-09-01", "open", None, None)]),
                       px.get, capital=1000)
    assert c["equity"].tolist() == [1000, 1100, 900, 950, 1200]
    assert set(c["source"]) == {ec.SOURCE_RECON}


def test_an_entry_on_a_weekend_starts_on_the_next_session():
    px = {"AAA": _bars(dict(zip(DAYS, [100, 110, 90, 95, 120])))}
    c = ec.reconstruct(_pos([("AAA", 100, 1, "2026-09-05", "open", None, None)]),
                       px.get, capital=0)
    assert c["date"].tolist() == [pd.Timestamp("2026-09-07")]


def test_a_closed_trade_is_realised_from_its_close_date_on():
    px = {"AAA": _bars(dict(zip(DAYS, [100, 110, 90, 95, 120])))}
    c = ec.reconstruct(_pos([("AAA", 100, 10, "2026-09-01", "closed", 105,
                              "2026-09-03")]), px.get, capital=1000)
    # 09-01 / 09-02 marked to close; from 09-03 on the 105 exit, not the 90 close
    assert c["equity"].tolist() == [1000, 1100, 1050, 1050, 1050]
    assert c["n_open"].tolist() == [1, 1, 0, 0, 0]


def test_a_missing_price_is_counted_not_valued_at_entry():
    """Valuing an unpriced position at its entry price draws a flat line exactly
    where the data is missing — a plausible zero drawdown that is not one."""
    px = {"AAA": _bars(dict(zip(DAYS, [100, 110, 90, 95, 120]))), "BBB": None}
    c = ec.reconstruct(_pos([("AAA", 100, 1, "2026-09-01", "open", None, None),
                             ("BBB", 50, 1, "2026-09-01", "open", None, None)]),
                       px.get, capital=0)
    assert (c["unpriced"] == 1).all()
    dd = ec.drawdown(c)
    assert dd["n_points"] == 0 and dd["skipped"] == 5


def test_drawdown_peak_trough_and_recovery():
    px = {"AAA": _bars(dict(zip(DAYS, [100, 110, 90, 95, 120])))}
    c = ec.reconstruct(_pos([("AAA", 100, 10, "2026-09-01", "open", None, None)]),
                       px.get, capital=1000)
    dd = ec.drawdown(c)
    # peak 1100 (09-02) -> trough 900 (09-03): -200, -18.18%
    assert dd["max_dd_amt"] == -200.0
    assert dd["max_dd_pct"] == pytest.approx(-18.18, abs=0.01)
    assert (dd["max_peak_date"], dd["max_trough_date"]) == ("2026-09-02", "2026-09-03")
    assert dd["recovered_date"] == "2026-09-07"
    assert dd["current_dd_pct"] == 0.0 and dd["peak_date"] == "2026-09-07"


def test_an_unrecovered_drawdown_says_so():
    px = {"AAA": _bars(dict(zip(DAYS, [100, 110, 90, 95, 100])))}
    c = ec.reconstruct(_pos([("AAA", 100, 10, "2026-09-01", "open", None, None)]),
                       px.get, capital=1000)
    dd = ec.drawdown(c)
    assert dd["recovered_date"] is None
    assert dd["current_dd_amt"] == -100.0


def test_recorded_rows_win_and_reconstruction_only_fills_before_them():
    recon = pd.DataFrame([dict(date=d, equity=e, capital=1000, unpriced=0,
                               source=ec.SOURCE_RECON)
                          for d, e in zip(DAYS, [1000, 1100, 900, 950, 1200])])
    rec = pd.DataFrame([dict(date="2026-09-03", equity=901, capital=1000, unpriced=0),
                        dict(date="2026-09-07", equity=1201, capital=1000, unpriced=0)])
    c = ec.combined(rec, recon)
    # 09-04 is NOT back-filled: after recording starts, a gap is a gap
    assert [d.date().isoformat() for d in c["date"]] == \
        ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-07"]
    assert c["source"].tolist() == [ec.SOURCE_RECON] * 2 + [ec.SOURCE_RECORDED] * 2
    dd = ec.drawdown(c)
    assert dd["max_dd_sources"] == sorted([ec.SOURCE_RECON, ec.SOURCE_RECORDED])


def test_a_capital_change_is_listed_so_it_is_not_read_as_performance():
    rec = pd.DataFrame([dict(date="2026-09-01", equity=1000, capital=1000, unpriced=0),
                        dict(date="2026-09-02", equity=600, capital=600, unpriced=0)])
    dd = ec.drawdown(ec.combined(rec, None))
    assert dd["capital_changes"] == [dict(date="2026-09-02", from_=1000.0, to=600.0)]
    _, caps = ec.drawdown_strip(dd)
    assert any("Capital changed on 2026-09-02" in c for c in caps)


def test_snapshot_row_uses_the_same_arithmetic_and_the_bar_date():
    px = {"AAA": _bars(dict(zip(DAYS, [100, 110, 90, 95, 120])))}
    pos = _pos([("AAA", 100, 10, "2026-09-01", "open", None, None)])
    row = ec.snapshot_row(pos, px.get, capital=1000, open_risk=50.0)
    last = ec.reconstruct(pos, px.get, capital=1000).iloc[-1]
    assert row["date"] == "2026-09-07"            # the bar, not the wall clock
    assert row["equity"] == last["equity"] == 1200
    assert row["source"] == ec.SOURCE_RECORDED and row["open_risk"] == 50.0


def test_the_card_labels_a_reconstruction_as_one():
    px = {"AAA": _bars(dict(zip(DAYS, [100, 110, 90, 95, 120])))}
    c = ec.reconstruct(_pos([("AAA", 100, 10, "2026-09-01", "open", None, None)]),
                       px.get, capital=1000)
    html, caps = ec.drawdown_strip(ec.drawdown(c))
    assert "Max drawdown" in html
    assert caps[0].startswith("⚠ RECONSTRUCTED")
    assert any("Only 5 trading days" in c for c in caps)


def test_no_positions_is_empty_not_an_error():
    assert ec.reconstruct(pd.DataFrame(), lambda s: None, 1000).empty
    dd = ec.drawdown(pd.DataFrame())
    assert dd["n_points"] == 0
    html, caps = ec.drawdown_strip(dd)
    assert html == "" and "no equity history yet" in caps[0]


def test_a_stale_db_module_degrades_to_a_caption_not_a_crash():
    """Seen live 2026-10-06: the running desk held a portfolio_db imported before
    this card existed and the Portfolio page raised AttributeError."""
    class Old:
        @staticmethod
        def get_setting(k, d=None):
            return "1000"
    html, caps = ec.portfolio_strip(Old, lambda s: None)
    assert html == "" and "restart the desk" in caps[0]


def test_a_first_day_loss_is_drawdown_from_the_capital_put_in():
    """Seen on the real book 2026-10-06: bought at 187.60, first close 179.94.
    Seeding the peak with the first close called a losing book 'at the peak'."""
    px = {"AAA": _bars(dict(zip(DAYS, [90, 95, 92, 94, 96])))}
    c = ec.reconstruct(_pos([("AAA", 100, 10, "2026-09-01", "open", None, None)]),
                       px.get, capital=1000)
    dd = ec.drawdown(c)
    assert dd["max_dd_amt"] == -100.0 and dd["max_peak_date"] == ec.START
    assert dd["current_dd_amt"] == -40.0 and dd["peak_date"] == ec.START
    assert dd["recovered_date"] is None
    html, _ = ec.drawdown_strip(dd)
    assert "below starting capital" in html
