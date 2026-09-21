"""Tests for open vs initial risk — B-106.

The arithmetic these pin used to live inside `dashboard_app.compute_portfolio_summary`,
where it could not be tested at all (importing that module runs the Streamlit
app), and where it computed `(entry_price - stop_loss) * qty` — **initial** risk,
frozen at entry, on a page full of live prices. It fed Home's card and the 6%
caution flag that throttles the desk.

The cases below are the ones that make the two numbers differ, which is the whole
point of having both.
"""
import numpy as np
import pandas as pd
import pytest

import market_verdict as mvd
import portfolio_risk as prisk


def _positions(rows):
    """rows = [(symbol, entry, qty, stop)]"""
    return pd.DataFrame(
        [{"symbol": s, "entry_price": e, "quantity": q, "stop_loss": st}
         for s, e, q, st in rows])


def _prices(mapping):
    return lambda sym: mapping.get(sym)


# ── one position ──────────────────────────────────────────────────────────────
def test_a_flat_position_risks_the_same_either_way():
    r = prisk.position_risk(entry=100, stop=90, last=100, qty=10)
    assert r["initial"] == 100.0 and r["open"] == 100.0


def test_a_winner_with_a_raised_stop_has_retired_its_risk():
    """THE B-106 CASE. Entry 100, stop raised to 110, price 130: this position
    cannot lose money any more, and the old number still reported its day-one
    risk forever."""
    r = prisk.position_risk(entry=100, stop=110, last=130, qty=10)
    assert r["initial"] == 0.0          # a stop above entry never risked anything
    assert r["open"] == 200.0           # (130 - 110) x 10 is what is still at stake


def test_a_loser_with_an_untouched_stop_risks_LESS_than_it_did():
    """The mirror, and the direction people get wrong. Entry 100, stop 90,
    price now 95: only 5 points remain between here and the stop, not 10. The
    initial number OVERSTATES this one."""
    r = prisk.position_risk(entry=100, stop=90, last=95, qty=10)
    assert r["initial"] == 100.0
    assert r["open"] == 50.0


def test_a_position_through_its_stop_contributes_zero_not_negative():
    """Price below the stop (a gap, or a stop that has not filled yet). Open risk
    is floored at zero: a negative would net off against another position's real
    exposure and hide it."""
    r = prisk.position_risk(entry=100, stop=90, last=85, qty=10)
    assert r["open"] == 0.0


def test_no_stop_is_flagged_rather_than_scored_as_zero_risk():
    """Unbounded risk is not zero risk. Counting it as 0 is the exact inversion
    of the truth, so it is reported separately instead."""
    r = prisk.position_risk(entry=100, stop=None, last=95, qty=10)
    assert r["has_stop"] == 0.0 and r["open"] == 0.0
    r_nan = prisk.position_risk(entry=100, stop=float("nan"), last=95, qty=10)
    assert r_nan["has_stop"] == 0.0


# ── the book ──────────────────────────────────────────────────────────────────
def test_the_two_portfolio_numbers_diverge_as_the_book_moves():
    pos = _positions([("A", 100, 10, 90),      # flat: 100 either way
                      ("B", 100, 10, 110)])    # winner, stop raised
    s = prisk.summarise(pos, _prices({"A": (100, 100), "B": (130, 128)}),
                        total_capital=10_000)
    assert s["capital_at_risk_pct"] == pytest.approx(1.0)    # 100 / 10,000
    assert s["open_risk_pct"] == pytest.approx(3.0)          # (100 + 200) / 10,000


def test_risk_retired_is_positive_when_the_book_is_ahead():
    pos = _positions([("A", 100, 10, 95)])
    s = prisk.summarise(pos, _prices({"A": (103, 102)}), total_capital=10_000)
    # initial 50, open 80 → the book is risking MORE than it started with
    assert s["risk_retired_pct"] < 0


def test_risk_retired_reads_100_when_every_stop_is_above_the_price():
    pos = _positions([("A", 100, 10, 90)])
    s = prisk.summarise(pos, _prices({"A": (85, 86)}), total_capital=10_000)
    assert s["open_risk_pct"] == 0.0
    assert s["risk_retired_pct"] == pytest.approx(100.0)


def test_an_unpriced_position_is_counted_not_skipped():
    """A book that is half unpriced must not report a comfortable risk number
    without saying so."""
    pos = _positions([("A", 100, 10, 90), ("GONE", 100, 10, 90)])
    s = prisk.summarise(pos, _prices({"A": (100, 100)}), total_capital=10_000)
    assert s["unpriced"] == 1
    assert s["open_count"] == 2          # the book still has two positions


def test_positions_without_stops_are_counted():
    pos = _positions([("A", 100, 10, None), ("B", 100, 10, 90)])
    s = prisk.summarise(pos, _prices({"A": (100, 100), "B": (100, 100)}),
                        total_capital=10_000)
    assert s["no_stop_count"] == 1
    assert s["open_risk_pct"] == pytest.approx(1.0)   # only B contributes


def test_an_empty_book_is_zero_everywhere_and_does_not_divide_by_zero():
    s = prisk.summarise(pd.DataFrame(), _prices({}), total_capital=0)
    assert s["open_risk_pct"] == 0.0 and s["capital_at_risk_pct"] == 0.0
    assert s["open_count"] == 0


def test_zero_capital_does_not_divide_by_zero():
    pos = _positions([("A", 100, 10, 90)])
    s = prisk.summarise(pos, _prices({"A": (100, 100)}), total_capital=0)
    assert s["open_risk_pct"] == 0.0


def test_pl_and_day_pl_still_work():
    """The extraction must not change what it moved."""
    pos = _positions([("A", 100, 10, 90)])
    s = prisk.summarise(pos, _prices({"A": (110, 105)}), total_capital=10_000)
    assert s["invested"] == 1000.0 and s["current_value"] == 1100.0
    assert s["pl"] == pytest.approx(100.0) and s["pl_pct"] == pytest.approx(10.0)
    assert s["day_pl_pct"] == pytest.approx(50 / 1100 * 100)


# ── what the caution flag reads ───────────────────────────────────────────────
def test_live_risk_prefers_open_and_falls_back_to_initial():
    assert prisk.live_risk_pct({"open_risk_pct": 3.0, "capital_at_risk_pct": 9.0}) == 3.0
    assert prisk.live_risk_pct({"capital_at_risk_pct": 9.0}) == 9.0   # older summary
    assert prisk.live_risk_pct({}) is None
    assert prisk.live_risk_pct(None) is None


def test_the_verdict_flags_on_open_risk_not_initial():
    """A book whose initial risk was 9% but which has since retired most of it
    should NOT be told to stand down for risk it no longer carries."""
    retired = {"open_risk_pct": 1.0, "capital_at_risk_pct": 9.0}
    v = mvd.build_verdict(None, retired, None)
    assert not any("Capital at risk" in c for c in v["caution"])

    still_on = {"open_risk_pct": 9.0, "capital_at_risk_pct": 1.0}
    v2 = mvd.build_verdict(None, still_on, None)
    assert any("Capital at risk" in c for c in v2["caution"])


def test_a_stopless_position_raises_its_own_caution():
    """It is not in the risk number at all, so silence would read as safety."""
    v = mvd.build_verdict(None, {"open_risk_pct": 0.0, "no_stop_count": 2}, None)
    assert any("NO STOP" in c for c in v["caution"])


# ── the card the page renders ─────────────────────────────────────────────────
def test_the_card_prefers_open_risk_as_its_value():
    v, sub, tone = prisk.risk_card(
        {"open_risk_pct": 2.0, "capital_at_risk_pct": 9.0,
         "risk_retired_pct": 78.0}, caution_pct=6.0)
    assert v == 2.0 and tone == "neutral"
    assert "78% of initial 9.0% retired" in sub


def test_the_card_goes_risk_toned_over_the_caution_line():
    _, _, tone = prisk.risk_card({"open_risk_pct": 7.5}, caution_pct=6.0)
    assert tone == "risk"


def test_a_stopless_position_outranks_the_retired_note():
    """Priority, not formatting: unbounded risk is the thing to say first."""
    _, sub, tone = prisk.risk_card(
        {"open_risk_pct": 1.0, "capital_at_risk_pct": 5.0,
         "risk_retired_pct": 80.0, "no_stop_count": 1}, caution_pct=6.0)
    assert "NO STOP" in sub and tone == "risk"


def test_an_unpriced_position_says_the_number_is_understated():
    _, sub, tone = prisk.risk_card(
        {"open_risk_pct": 1.0, "capital_at_risk_pct": 5.0, "unpriced": 2},
        caution_pct=6.0)
    assert "could not be priced" in sub and tone == "risk"


def test_an_empty_book_falls_back_to_the_threshold_line():
    _, sub, tone = prisk.risk_card({}, caution_pct=6.0)
    assert "caution above 6%" in sub and tone == "neutral"


# ── EXPOSURE (B-107) ──────────────────────────────────────────────────────────
def test_exposure_measures_against_capital_not_against_the_book():
    """40% 'of what I have deployed' flatters a book that is mostly cash. The
    question a concentration number answers is what happens to the ACCOUNT."""
    pos = _positions([("A", 100, 10, 90), ("B", 100, 10, 90)])
    e = prisk.exposure(pos, _prices({"A": (100, 100), "B": (100, 100)}),
                       total_capital=10_000)
    assert e["deployed_pct"] == pytest.approx(20.0)      # 2,000 of 10,000
    assert e["largest_pct"] == pytest.approx(10.0)       # not 50% of the book
    assert e["cash_pct"] == pytest.approx(80.0)


def test_largest_and_top3_pick_the_biggest_positions():
    pos = _positions([("A", 100, 10, None), ("B", 100, 50, None),
                      ("C", 100, 20, None), ("D", 100, 5, None)])
    e = prisk.exposure(pos, _prices({s: (100, 100) for s in "ABCD"}),
                       total_capital=100_000)
    assert e["largest_symbol"] == "B"
    assert e["largest_pct"] == pytest.approx(5.0)        # 5,000 / 100,000
    assert e["top3_pct"] == pytest.approx(8.0)           # B + C + A


def test_sector_concentration_sums_by_sector():
    pos = _positions([("A", 100, 10, None), ("B", 100, 10, None),
                      ("C", 100, 10, None)])
    e = prisk.exposure(pos, _prices({s: (100, 100) for s in "ABC"}),
                       total_capital=10_000,
                       sectors={"A": "Banks", "B": "Banks", "C": "Pharma"})
    assert e["by_sector"]["Banks"] == pytest.approx(20.0)
    assert e["largest_sector"] == "Banks"


def test_an_unmapped_symbol_is_not_invented_into_a_sector():
    """The same rule `sector_column` holds: a blank is honest, 'Other' is not."""
    pos = _positions([("A", 100, 10, None), ("MYSTERY", 100, 10, None)])
    e = prisk.exposure(pos, _prices({"A": (100, 100), "MYSTERY": (100, 100)}),
                       total_capital=10_000, sectors={"A": "Banks"})
    assert e["by_sector"] == {"Banks": 10.0}
    assert e["unmapped_pct"] == pytest.approx(10.0)
    assert "Other" not in e["by_sector"]


def test_exposure_falls_back_to_share_of_book_without_capital():
    pos = _positions([("A", 100, 10, None), ("B", 100, 30, None)])
    e = prisk.exposure(pos, _prices({"A": (100, 100), "B": (100, 100)}),
                       total_capital=0)
    assert e["largest_pct"] == pytest.approx(75.0)       # 3,000 of 4,000


def test_exposure_of_an_empty_book_is_all_cash():
    e = prisk.exposure(pd.DataFrame(), _prices({}), total_capital=10_000)
    assert e["deployed_pct"] == 0.0 and e["cash_pct"] == 100.0


def test_exposure_counts_unpriced_positions():
    pos = _positions([("A", 100, 10, None), ("GONE", 100, 10, None)])
    e = prisk.exposure(pos, _prices({"A": (100, 100)}), total_capital=10_000)
    assert e["unpriced"] == 1 and e["n_positions"] == 2


# ── SIZING RECONCILIATION (B-107) ─────────────────────────────────────────────
def test_a_stand_down_day_takes_the_size_to_zero():
    """'No size, no exceptions' — the verdict's own words. Before this, the
    council's suggested size ignored the verdict entirely."""
    r = prisk.reconcile_size(20.0, {"verdict": "STAND DOWN", "size_pct": 0,
                                    "max_trades": 0}, open_count=0)
    assert r["size_pct"] == 0.0 and r["throttled"] is True


def test_a_selective_day_halves_the_size_and_says_which_rule_did_it():
    r = prisk.reconcile_size(20.0, {"verdict": "SELECTIVE", "size_pct": 50,
                                    "max_trades": 2}, open_count=0)
    assert r["size_pct"] == 10.0 and r["raw_size_pct"] == 20.0
    note = prisk.size_note(r)
    assert "10.0%" in note and "SELECTIVE" in note and "20.0%" in note


def test_a_normal_day_leaves_the_council_number_alone():
    r = prisk.reconcile_size(20.0, {"verdict": "TRADE", "size_pct": 100,
                                    "max_trades": 3}, open_count=0)
    assert r["size_pct"] == 20.0 and r["throttled"] is False
    assert "scaled" not in prisk.size_note(r)


def test_the_trade_cap_is_checked_against_open_positions():
    """The cap existed and was displayed; nothing ever compared it to the book."""
    r = prisk.reconcile_size(20.0, {"verdict": "SELECTIVE", "size_pct": 50,
                                    "max_trades": 2}, open_count=2)
    assert r["at_cap"] is True and r["slots_left"] == 0
    assert "at today's cap" in prisk.size_note(r)


def test_slots_left_counts_down():
    r = prisk.reconcile_size(20.0, {"verdict": "TRADE", "size_pct": 100,
                                    "max_trades": 3}, open_count=1)
    assert r["slots_left"] == 2 and r["at_cap"] is False


def test_size_and_cap_fail_separately():
    """A halved size still lets you take the trade; being at the cap does not.
    Reporting them as one number would lose that."""
    r = prisk.reconcile_size(20.0, {"verdict": "SELECTIVE", "size_pct": 50,
                                    "max_trades": 2}, open_count=5)
    assert r["size_pct"] == 10.0          # still sized
    assert r["at_cap"] is True            # and still not allowed


def test_no_council_size_stays_none_rather_than_becoming_zero():
    """A card with no size (no stop, so no risk-based size) must not read as
    'size zero' once the multiplier is applied to it."""
    r = prisk.reconcile_size(None, {"verdict": "TRADE", "size_pct": 100}, 0)
    assert r["size_pct"] is None and prisk.size_note(r) == ""


def test_a_missing_verdict_does_not_throttle():
    r = prisk.reconcile_size(20.0, None, open_count=0)
    assert r["size_pct"] == 20.0 and r["throttled"] is False
    assert r["slots_left"] is None and r["at_cap"] is False


def test_the_exposure_strip_renders_and_says_what_it_does_not_judge():
    cards, caps = prisk.exposure_strip(prisk.exposure(
        _positions([("A", 100, 10, None)]), _prices({"A": (100, 100)}),
        total_capital=10_000, sectors={"A": "Banks"}))
    assert "Deployed" in cards and "Largest sector" in cards
    assert any("Banks 10.0%" in c for c in caps)
    assert any("yours to set" in c for c in caps)


def test_the_exposure_strip_warns_when_a_position_could_not_be_priced():
    cards, caps = prisk.exposure_strip(prisk.exposure(
        _positions([("A", 100, 10, None), ("GONE", 100, 10, None)]),
        _prices({"A": (100, 100)}), total_capital=10_000))
    assert any("understated" in c for c in caps)
