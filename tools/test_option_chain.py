"""Tests for option_chain — B-23 strike-level OI, max pain and OI walls.

Runs two ways so it fits the repo's "__main__ probe" style AND pytest:
    py -3 tools/test_option_chain.py     # prints PASS/FAIL, exits nonzero on fail
    pytest tools/test_option_chain.py    # standard collection

Pure, deterministic, no network — every test builds a synthetic bhavcopy frame,
so the expected max-pain strike is known by hand-computation rather than by
trusting the implementation that is under test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import option_chain as oc


# ── helpers ───────────────────────────────────────────────────────────────────
def _rows(symbol, cls, expiry, spot, legs):
    """legs = [(strike, 'CE'|'PE', oi), ...] -> bhavcopy-shaped rows."""
    return [{
        "FinInstrmTp": cls, "TckrSymb": symbol, "XpryDt": expiry,
        "StrkPric": k, "OptnTp": t, "OpnIntrst": o,
        "SttlmPric": 10.0, "UndrlygPric": spot,
    } for (k, t, o) in legs]


def _raw(*rowsets):
    out = []
    for rs in rowsets:
        out.extend(rs)
    return pd.DataFrame(out)


def _simple_chain(legs, symbol="NIFTY", cls="IDO", expiry="2026-09-24", spot=100.0):
    return oc.load_chain(_raw(_rows(symbol, cls, expiry, spot, legs)), symbol)


def _pain_bruteforce(legs, K):
    """Independent re-implementation of the payout, used to pin max_pain."""
    tot = 0.0
    for (k, t, o) in legs:
        tot += o * (max(0.0, K - k) if t == "CE" else max(0.0, k - K))
    return tot


# ── loading ───────────────────────────────────────────────────────────────────
def test_returns_none_for_unknown_symbol():
    raw = _raw(_rows("NIFTY", "IDO", "2026-09-24", 100.0, [(100, "CE", 5)]))
    assert oc.load_chain(raw, "RELIANCE") is None


def test_returns_none_on_empty_frame():
    assert oc.load_chain(pd.DataFrame(), "NIFTY") is None
    assert oc.load_chain(None, "NIFTY") is None


def test_index_vs_stock_instrument_type():
    """NIFTY must be read from IDO rows and a stock from STO — mixing them up
    would silently return an empty chain for one whole class."""
    idx = _rows("NIFTY", "IDO", "2026-09-24", 100.0, [(100, "CE", 5), (100, "PE", 5)])
    stk = _rows("RELIANCE", "STO", "2026-09-24", 500.0, [(500, "CE", 7), (500, "PE", 7)])
    raw = _raw(idx, stk)
    ci = oc.load_chain(raw, "NIFTY")
    cs = oc.load_chain(raw, "RELIANCE")
    assert ci and ci["class"] == "INDEX"
    assert cs and cs["class"] == "STOCK"
    assert float(cs["spot"]) == 500.0


def test_call_and_put_oi_land_in_separate_columns():
    ch = _simple_chain([(100, "CE", 11), (100, "PE", 22)])
    row = ch["strikes"].iloc[0]
    assert row["call_oi"] == 11 and row["put_oi"] == 22
    assert row["total_oi"] == 33


def test_missing_side_is_zero_not_nan():
    ch = _simple_chain([(100, "CE", 11), (110, "PE", 22)])
    df = ch["strikes"].set_index("strike")
    assert df.loc[100, "put_oi"] == 0
    assert df.loc[110, "call_oi"] == 0


def test_duplicate_strike_rows_are_summed():
    ch = _simple_chain([(100, "CE", 5), (100, "CE", 7)])
    assert ch["strikes"].iloc[0]["call_oi"] == 12


def test_strikes_are_sorted():
    ch = _simple_chain([(120, "CE", 1), (100, "CE", 1), (110, "CE", 1)])
    assert list(ch["strikes"]["strike"]) == [100.0, 110.0, 120.0]


# ── expiry handling ───────────────────────────────────────────────────────────
def test_defaults_to_nearest_expiry():
    near = _rows("NIFTY", "IDO", "2026-09-24", 100.0, [(100, "CE", 5)])
    far  = _rows("NIFTY", "IDO", "2026-12-31", 100.0, [(200, "CE", 9)])
    ch = oc.load_chain(_raw(near, far), "NIFTY")
    assert ch["expiry"] == "2026-09-24"
    assert list(ch["strikes"]["strike"]) == [100.0]
    assert ch["expiries"] == ["2026-09-24", "2026-12-31"]


def test_explicit_expiry_selects_that_month():
    near = _rows("NIFTY", "IDO", "2026-09-24", 100.0, [(100, "CE", 5)])
    far  = _rows("NIFTY", "IDO", "2026-12-31", 100.0, [(200, "CE", 9)])
    ch = oc.load_chain(_raw(near, far), "NIFTY", expiry="2026-12-31")
    assert list(ch["strikes"]["strike"]) == [200.0]


def test_unknown_expiry_returns_none():
    raw = _raw(_rows("NIFTY", "IDO", "2026-09-24", 100.0, [(100, "CE", 5)]))
    assert oc.load_chain(raw, "NIFTY", expiry="2030-01-01") is None


def test_all_pools_every_expiry():
    near = _rows("NIFTY", "IDO", "2026-09-24", 100.0, [(100, "CE", 5)])
    far  = _rows("NIFTY", "IDO", "2026-12-31", 100.0, [(200, "CE", 9)])
    ch = oc.load_chain(_raw(near, far), "NIFTY", expiry="all")
    assert ch["expiry"] == "all"
    assert list(ch["strikes"]["strike"]) == [100.0, 200.0]


# ── max pain ──────────────────────────────────────────────────────────────────
def test_max_pain_refuses_pooled_expiry():
    """Payoff settles per expiry, so a pooled number is a different quantity —
    returning one would be worse than returning nothing."""
    near = _rows("NIFTY", "IDO", "2026-09-24", 100.0, [(100, "CE", 5)])
    far  = _rows("NIFTY", "IDO", "2026-12-31", 100.0, [(200, "CE", 9)])
    ch = oc.load_chain(_raw(near, far), "NIFTY", expiry="all")
    assert oc.max_pain(ch) is None


def test_max_pain_symmetric_chain_sits_in_the_middle():
    """Equal OI at 90/100/110 both sides — the middle strike pays out least."""
    legs = [(90, "CE", 10), (100, "CE", 10), (110, "CE", 10),
            (90, "PE", 10), (100, "PE", 10), (110, "PE", 10)]
    mp = oc.max_pain(_simple_chain(legs))
    assert mp["strike"] == 100.0


def test_max_pain_matches_an_independent_brute_force():
    """The vectorised outer-difference must agree with a naive loop over every
    candidate strike — the actual formula, computed a different way."""
    rng = np.random.default_rng(7)
    legs = []
    for k in range(80, 125, 5):
        legs.append((k, "CE", float(rng.integers(0, 5000))))
        legs.append((k, "PE", float(rng.integers(0, 5000))))
    ch = _simple_chain(legs)
    mp = oc.max_pain(ch)
    strikes = sorted({k for (k, _, _) in legs})
    expect = min(strikes, key=lambda K: _pain_bruteforce(legs, K))
    assert mp["strike"] == float(expect)
    assert abs(mp["pain"] - _pain_bruteforce(legs, expect)) < 1e-6


def test_max_pain_pulls_toward_the_heavy_side():
    """Heavy call OI at 110 makes settling high expensive, so max pain sits low."""
    legs = [(90, "PE", 10), (100, "PE", 10), (110, "CE", 5000), (100, "CE", 10)]
    mp = oc.max_pain(_simple_chain(legs))
    assert mp["strike"] <= 100.0


def test_max_pain_curve_covers_every_strike():
    legs = [(90, "CE", 3), (100, "CE", 3), (110, "PE", 3)]
    mp = oc.max_pain(_simple_chain(legs))
    assert list(mp["curve"]["strike"]) == [90.0, 100.0, 110.0]
    assert (mp["curve"]["pain"] >= 0).all()


def test_max_pain_none_when_all_oi_zero():
    assert oc.max_pain(_simple_chain([(100, "CE", 0), (100, "PE", 0)])) is None


# ── OI walls ──────────────────────────────────────────────────────────────────
def test_call_walls_are_above_spot_and_puts_below():
    """A big call OI far BELOW spot is deep-ITM inventory, not a ceiling. Ranking
    it as resistance would put the strongest resistance under the price."""
    legs = [(80, "CE", 9999), (120, "CE", 100),      # huge call OI below spot
            (120, "PE", 9999), (80, "PE", 100)]      # huge put  OI above spot
    w = oc.oi_walls(_simple_chain(legs), n=3)
    assert all(x["strike"] >= 100.0 for x in w["resistance"]), w["resistance"]
    assert all(x["strike"] <= 100.0 for x in w["support"]), w["support"]
    assert w["resistance"][0]["strike"] == 120.0
    assert w["support"][0]["strike"] == 80.0


def test_walls_ranked_by_oi_descending():
    legs = [(110, "CE", 10), (120, "CE", 50), (130, "CE", 30)]
    w = oc.oi_walls(_simple_chain(legs), n=3)
    assert [x["strike"] for x in w["resistance"]] == [120.0, 130.0, 110.0]


def test_wall_count_is_capped_by_n():
    legs = [(k, "CE", k) for k in (110, 120, 130, 140, 150)]
    assert len(oc.oi_walls(_simple_chain(legs), n=2)["resistance"]) == 2


def test_walls_report_distance_from_spot():
    w = oc.oi_walls(_simple_chain([(110, "CE", 10)]), n=1)
    assert w["resistance"][0]["dist_pct"] == 10.0


def test_walls_unfiltered_when_side_filter_off():
    legs = [(80, "CE", 9999)]
    w = oc.oi_walls(_simple_chain(legs), n=3, above_below_spot=False)
    assert w["resistance"] and w["resistance"][0]["strike"] == 80.0


def test_walls_empty_on_empty_chain():
    assert oc.oi_walls(None)["resistance"] == []


def test_near_strikes_excludes_far_otm():
    """B-100: far-OTM inventory must not appear as a wall when near_strikes is set."""
    legs = [
        (110, "CE", 10), (120, "CE", 20), (130, "CE", 30),
        (200, "CE", 9999),  # far OTM, huge OI
    ]
    chain = _simple_chain(legs)
    w_all = oc.oi_walls(chain, n=1)
    assert w_all["resistance"][0]["strike"] == 200.0  # without window: far OTM wins

    w_near = oc.oi_walls(chain, n=1, near_strikes=3)
    assert w_near["resistance"][0]["strike"] == 130.0  # with window: nearest 3 only


def test_near_strikes_support_side():
    legs = [
        (10, "PE", 9999),  # far OTM put
        (80, "PE", 30), (90, "PE", 20), (100, "PE", 10),
    ]
    chain = _simple_chain(legs)
    w_near = oc.oi_walls(chain, n=1, near_strikes=3)
    assert w_near["support"][0]["strike"] == 80.0  # not 10


def test_read_levels_includes_wall_window():
    legs = [(90, "PE", 500), (100, "CE", 300), (100, "PE", 300), (110, "CE", 700)]
    raw = _raw(_rows("NIFTY", "IDO", "2026-09-24", 100.0, legs))
    r = oc.read_levels("NIFTY", raw=raw)
    assert r["wall_window"] == oc.NEAR_STRIKES


# ── composed read ─────────────────────────────────────────────────────────────
def test_read_levels_composes_without_network():
    legs = [(90, "PE", 500), (100, "CE", 300), (100, "PE", 300), (110, "CE", 700)]
    raw = _raw(_rows("NIFTY", "IDO", "2026-09-24", 100.0, legs))
    r = oc.read_levels("NIFTY", raw=raw)
    assert r["symbol"] == "NIFTY" and r["class"] == "INDEX"
    assert r["spot"] == 100.0
    assert r["max_pain"] is not None
    assert r["n_strikes"] == 3
    assert r["unmeasured"] is True
    # PCR from the same rows must agree with the totals reported beside it.
    assert abs(r["pcr_oi"] - (r["total_put_oi"] / r["total_call_oi"])) < 1e-9


def test_read_levels_none_for_symbol_without_options():
    raw = _raw(_rows("NIFTY", "IDO", "2026-09-24", 100.0, [(100, "CE", 5)]))
    assert oc.read_levels("NOSUCH", raw=raw) is None


def test_format_handles_missing_and_populated():
    assert "No option chain" in oc.format_levels(None)
    raw = _raw(_rows("NIFTY", "IDO", "2026-09-24", 100.0,
                     [(90, "PE", 500), (110, "CE", 700)]))
    txt = oc.format_levels(oc.read_levels("NIFTY", raw=raw))
    assert "max pain" in txt and "Call walls" in txt
    assert "NOT a signal" in txt        # the unmeasured label must survive


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


if __name__ == "__main__":
    import traceback
    failed = 0
    for t in ALL_TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(ALL_TESTS) - failed}/{len(ALL_TESTS)} passed")
    raise SystemExit(1 if failed else 0)
