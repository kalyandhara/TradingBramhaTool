import datetime as dt

import own_history_valuation as oh


def _series(n=36, eps0=10.0, g=1.02, mult=20.0):
    d0 = dt.date(2018, 3, 31)
    ttm, px = [], {}
    e = eps0
    for i in range(n):
        d = (d0 + dt.timedelta(days=91 * i)).isoformat()
        ttm.append((d, round(e, 4)))
        px[d] = mult * e
        e *= g
    return ttm, px


def test_refuses_below_min_years():
    ttm, px = _series(n=12)
    b = oh.band(ttm, px, 300.0)
    assert b["ok"] is False and "needs 8+ years" in b["reason"]


def test_refuses_with_no_history():
    assert oh.band([], {}, 100.0)["ok"] is False


def test_median_multiple_and_fair_price():
    ttm, px = _series(n=36, mult=20.0)
    b = oh.band(ttm, px, price_now=px[ttm[-1][0]])
    assert b["ok"] and b["normal_multiple"] == 20.0
    assert abs(b["fair_price"] - 20.0 * ttm[-1][1]) < 0.02
    assert abs(b["price_vs_fair_pct"]) < 0.2


def test_median_resists_one_outlier_multiple():
    ttm, px = _series(n=36, mult=20.0)
    px[ttm[3][0]] = 20000.0 * ttm[3][1]            # one absurd multiple
    assert oh.band(ttm, px, 100.0)["normal_multiple"] == 20.0


def test_refuses_on_split_like_jump():
    ttm, px = _series(n=36)
    ttm[15] = (ttm[15][0], ttm[14][1] * 5)
    b = oh.band(ttm, px, 100.0)
    assert b["ok"] is False and "jump" in b["reason"]


def test_refuses_when_current_eps_not_positive():
    ttm, px = _series(n=36)
    ttm[-1] = (ttm[-1][0], -1.0)
    b = oh.band(ttm, px, 100.0)
    assert b["ok"] is False and "not positive" in b["reason"]


def test_loss_quarters_are_excluded_not_zeroed():
    ttm, px = _series(n=36, mult=20.0)
    # A loss quarter mid-series: it must drop out of the multiples, not enter as a
    # zero. (A negative TTM is not a >4x jump, so the split guard ignores it.)
    ttm[5] = (ttm[5][0], -2.0)
    b = oh.band(ttm, px, 100.0)
    assert b["ok"] and b["normal_multiple"] == 20.0 and b["points"] == 35


def test_caption_states_a_refusal_and_never_a_target_claim():
    ttm, px = _series(n=12)
    assert oh.caption(oh.band(ttm, px, 1.0)).startswith("Own-history valuation not shown")
    ttm, px = _series(n=36)
    c = oh.caption(oh.band(ttm, px, 100.0)).lower()
    assert "not a target" in c and "not intrinsic value" in c
    assert "buy" not in c and "undervalued" not in c
