"""Tests for gamma_exposure — the B-44 naive dealer GEX engine.

Runs two ways, matching test_technofunda_funnel's style:
    py -3 tools/test_gamma_exposure.py     # prints PASS/FAIL, exits nonzero on fail
    pytest tools/test_gamma_exposure.py    # standard collection

Pure, deterministic, no network. The Black-Scholes layer is checked against identities
that must hold exactly (put-call parity, gamma symmetry, IV round-trip) rather than
against hardcoded numbers copied out of a calculator — an identity catches a sign error,
a memorised constant only catches a typo.

The GEX layer is checked on a hand-built option chain where the correct answer is known
by construction, including the one thing most likely to be wrong: the SIGN convention.
"""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd

import gamma_exposure as gx

S, K, T, R, SIG = 24000.0, 24000.0, 30 / 365.0, 0.065, 0.14


# ── Black-Scholes identities ──────────────────────────────────────────────────

def test_put_call_parity():
    """C - P = S - K*exp(-rT). If the two branches disagree, one of them is wrong."""
    c = gx.bs_price(S, K, T, R, SIG, "CE")
    p = gx.bs_price(S, K, T, R, SIG, "PE")
    assert abs((c - p) - (S - K * math.exp(-R * T))) < 1e-6


def test_gamma_is_side_independent():
    """Gamma is identical for calls and puts — which is why GEX needs only a sign.

    Verified numerically (second difference of price) rather than by re-deriving the
    closed form, so an error in bs_gamma cannot hide behind the same error twice.
    """
    for kind in ("CE", "PE"):
        h = 1.0
        num = (gx.bs_price(S + h, K, T, R, SIG, kind)
               - 2 * gx.bs_price(S, K, T, R, SIG, kind)
               + gx.bs_price(S - h, K, T, R, SIG, kind)) / (h * h)
        assert abs(num - gx.bs_gamma(S, K, T, R, SIG)) < 1e-6, kind


def test_gamma_peaks_near_atm_and_decays():
    atm = gx.bs_gamma(S, K, T, R, SIG)
    assert atm > gx.bs_gamma(S, K * 1.10, T, R, SIG)
    assert atm > gx.bs_gamma(S, K * 0.90, T, R, SIG)


def test_implied_vol_roundtrip():
    for kind in ("CE", "PE"):
        for k in (0.92, 1.0, 1.08):
            price = gx.bs_price(S, K * k, T, R, SIG, kind)
            iv = gx.implied_vol(price, S, K * k, T, R, kind)
            assert iv is not None, (kind, k)
            assert abs(iv - SIG) < 1e-4, (kind, k, iv)


def test_implied_vol_rejects_uninvertible_prices():
    """No vol is fabricated where the price carries none — the rows are dropped."""
    assert gx.implied_vol(0.0, S, K, T, R, "CE") is None            # zero price
    intrinsic = max(0.0, S - K * 0.5)
    assert gx.implied_vol(intrinsic, S, K * 0.5, T, R, "CE") is None  # at intrinsic
    assert gx.implied_vol(S * 0.99, S, K, T, R, "CE") is None        # above the vol ceiling


# ── chain fixture ─────────────────────────────────────────────────────────────

TRADE_DATE = datetime(2026, 8, 28)
EXPIRY = "2026-09-24"


def _chain(rows, symbol="NIFTY", spot=S):
    """Build a bhavcopy-shaped frame. `rows` = [(strike, kind, oi)] priced at SIG."""
    t = (datetime(2026, 9, 24) - TRADE_DATE).days / 365.0
    recs = []
    for strike, kind, oi in rows:
        recs.append({
            "FinInstrmTp": "IDO", "TckrSymb": symbol, "StrkPric": float(strike),
            "OptnTp": kind, "OpnIntrst": float(oi),
            "SttlmPric": gx.bs_price(spot, float(strike), t, gx.RISK_FREE, SIG, kind),
            "XpryDt": EXPIRY, "UndrlygPric": spot,
        })
    return pd.DataFrame(recs)


def test_all_calls_is_positive_gamma():
    """The naive convention: dealers are LONG call gamma. Calls only -> positive."""
    res = gx.compute_gex(_chain([(24000, "CE", 100000)]), "NIFTY", TRADE_DATE)
    assert res is not None
    assert res["net_gex_cr"] > 0
    assert res["regime"] == "positive"


def test_all_puts_is_negative_gamma():
    """...and SHORT put gamma. Puts only -> negative. This is the sign that matters."""
    res = gx.compute_gex(_chain([(24000, "PE", 100000)]), "NIFTY", TRADE_DATE)
    assert res is not None
    assert res["net_gex_cr"] < 0
    assert res["regime"] == "negative"


def test_symmetric_chain_nets_to_zero():
    """Equal call and put OI at the same strike cancel exactly — gamma is side-free."""
    res = gx.compute_gex(_chain([(24000, "CE", 50000), (24000, "PE", 50000)]),
                         "NIFTY", TRADE_DATE)
    assert res is not None
    assert abs(res["net_gex_cr"]) < 1e-6
    assert abs(res["net_to_gross"]) < 1e-6
    assert res["gross_gex_cr"] > 0            # gross is NOT zero — the sides are real


def test_walls_are_the_largest_gamma_strikes():
    res = gx.compute_gex(_chain([
        (23800, "CE", 10000), (24200, "CE", 900000),      # call wall at 24200
        (23600, "PE", 800000), (24400, "PE", 5000),       # put wall at 23600
    ]), "NIFTY", TRADE_DATE)
    assert res["call_wall"] == 24200
    assert res["put_wall"] == 23600


def test_gamma_flip_sits_between_the_two_sides():
    """Puts below spot, calls above -> net gamma rises with spot -> a flip in between."""
    res = gx.compute_gex(_chain([
        (23000, "PE", 400000), (25000, "CE", 400000),
    ]), "NIFTY", TRADE_DATE)
    assert res["gamma_flip"] is not None
    assert 23000 < res["gamma_flip"] < 25000


def test_zero_oi_rows_are_ignored():
    """Listed-but-empty strikes are most of the chain and must contribute nothing."""
    live = _chain([(24000, "CE", 100000)])
    padded = pd.concat([live, _chain([(21000, "CE", 0), (27000, "PE", 0)])],
                       ignore_index=True)
    a = gx.compute_gex(live, "NIFTY", TRADE_DATE)
    b = gx.compute_gex(padded, "NIFTY", TRADE_DATE)
    assert abs(a["net_gex_cr"] - b["net_gex_cr"]) < 1e-9
    assert b["n_contracts"] == 1


def test_other_symbols_and_instrument_types_are_excluded():
    mixed = pd.concat([
        _chain([(24000, "CE", 100000)], symbol="NIFTY"),
        _chain([(57000, "PE", 900000)], symbol="BANKNIFTY", spot=57000.0),
    ], ignore_index=True)
    nifty = gx.compute_gex(mixed, "NIFTY", TRADE_DATE)
    assert nifty["n_contracts"] == 1 and nifty["net_gex_cr"] > 0
    stock_only = mixed.copy()
    stock_only["FinInstrmTp"] = "STO"            # stock options must not leak in
    assert gx.compute_gex(stock_only, "NIFTY", TRADE_DATE) is None


def test_oi_scales_gex_linearly():
    """OI is in index UNITS and enters linearly — doubling OI doubles GEX, nothing else."""
    a = gx.compute_gex(_chain([(24000, "CE", 100000)]), "NIFTY", TRADE_DATE)
    b = gx.compute_gex(_chain([(24000, "CE", 200000)]), "NIFTY", TRADE_DATE)
    assert abs(b["net_gex_cr"] - 2 * a["net_gex_cr"]) < 1e-6


def test_empty_and_missing_input_return_none():
    assert gx.compute_gex(pd.DataFrame(), "NIFTY", TRADE_DATE) is None
    assert gx.compute_gex(_chain([(24000, "CE", 100000)]), "SENSEX", TRADE_DATE) is None


def _main() -> int:
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {name}  {e}")
        except Exception as e:                       # noqa: BLE001 - report, don't mask
            failed += 1
            print(f"  ERROR {name}  {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
