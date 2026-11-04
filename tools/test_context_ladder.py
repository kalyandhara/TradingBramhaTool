"""B-187 — context ladder: market → sector rungs + 'was it the stock or the market?'."""
import numpy as np
import pandas as pd
import pytest

import context_ladder as cl


def _series(values) -> pd.Series:
    idx = pd.bdate_range("2026-01-01", periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


def _ramp(start, step, n=60):
    return _series(start + step * np.arange(n))


# ── trend word ────────────────────────────────────────────────────────────────
def test_trend_word_up_down_mixed():
    assert cl.trend_word(_ramp(100, 1)) == "Up"
    assert cl.trend_word(_ramp(200, -1)) == "Down"
    # rose for 50 bars, then one sharp drop: close under a still-rising average
    s = _series(list(100 + np.arange(50.0)) + [135.0])
    assert cl.trend_word(s) == "Mixed"


def test_trend_word_needs_enough_bars():
    assert cl.trend_word(_ramp(100, 1, n=10)) is None
    assert cl.trend_word(None) is None


def test_pct_change_over_bars():
    s = _ramp(100, 1, n=30)                     # last 129, 21 bars back 108
    assert cl.pct_change(s, 21) == pytest.approx((129 / 108 - 1) * 100)
    assert cl.pct_change(s, 40) is None


# ── attribution ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("stock,sector,market,verdict", [
    (8.2, 3.1, 1.0, "mostly the stock"),        # +5.1 stock-specific
    (4.0, 3.6, 0.5, "mostly the sector"),       # +3.1 sector over market
    (3.0, 3.1, 2.9, "mostly the market"),
    (4.0, 2.0, 0.0, "mixed"),                   # 2.0 stock vs 2.0 sector
])
def test_attribution_verdicts(stock, sector, market, verdict):
    v, text = cl.attribution(stock, sector, market)
    assert v == verdict
    assert verdict in text


def test_attribution_without_sector_compares_stock_to_market_only():
    v, text = cl.attribution(6.0, None, 1.0)
    assert v == "mostly the stock"
    assert "sector" in text.lower()             # says the sector is unknown


def test_attribution_unknown_when_stock_or_market_missing():
    assert cl.attribution(None, 2.0, 1.0)[0] is None
    assert cl.attribution(2.0, 1.0, None)[0] is None


# ── sector lookup + ladder ────────────────────────────────────────────────────
def test_sector_for_maps_nse_sector_and_misses_off_index():
    imap = {"HAL": "Capital Goods", "XYZ": "Textiles"}
    assert cl.sector_for("HAL", imap) == ("^CNXINFRA", "Capital Goods")
    assert cl.sector_for("XYZ", imap) == (None, "Textiles")     # unmapped sector
    assert cl.sector_for("PREMIERPOL", imap) == (None, None)    # not in NIFTY 500


def test_ladder_says_when_sector_frame_is_missing():
    stock, mkt = _ramp(100, 1), _ramp(100, 0.2)
    lad = cl.build_ladder(stock, mkt, None, sector_label="Capital Goods",
                          sector_ticker="^CNXINFRA")
    rungs = {r["rung"]: r for r in lad["rungs"]}
    assert rungs["Market"]["trend"] == "Up"
    assert rungs["Sector"]["missing"]            # shown, not silently dropped
    assert lad["verdict"] == "mostly the stock"


def test_ladder_reads_capitalised_close_columns():
    """Snapshot sector frames come from yf.download (Close); stock frames from
    the scanner (close). Both must work."""
    stock = pd.DataFrame({"close": _ramp(100, 1)})
    sector = pd.DataFrame({"Close": _ramp(100, 0.8)})
    lad = cl.build_ladder(stock, _ramp(100, 0.1), sector,
                          sector_label="Capital Goods", sector_ticker="^CNXINFRA")
    rungs = {r["rung"]: r for r in lad["rungs"]}
    assert rungs["Sector"]["trend"] == "Up" and not rungs["Sector"]["missing"]
