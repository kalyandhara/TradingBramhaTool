"""breakout_scan — the cookie-free replacement for the Chartink breakout page."""

import numpy as np
import pandas as pd

import breakout_scan as bks
import opportunity_hub as oh
import scanner_templates as sc


def _base_then_break(n_bars: int, ceiling: float = 100.0, seed: int = 0) -> pd.DataFrame:
    """A long range under `ceiling`, then today's close 5% above it on volume."""
    rng = np.random.default_rng(seed)
    close = ceiling * 0.8 + rng.uniform(-8, 8, n_bars)
    close = np.clip(close, 70, ceiling * 0.97)
    close[-60:] = np.linspace(close[-60], ceiling * 0.96, 60)  # rise into the ceiling
    close[-1] = ceiling * 1.05
    high = close * 1.01
    high[-(n_bars // 2)] = ceiling                             # the level to break
    vol = np.full(n_bars, 1_000_000.0)
    vol[-1] = 3_000_000.0
    idx = pd.bdate_range(end="2026-10-05", periods=n_bars)
    return pd.DataFrame({"open": close * 0.995, "high": high, "low": close * 0.99,
                         "close": close, "volume": vol}, index=idx)


def test_hub_scanner_gets_full_history():
    # Without this flag the 1Y/5Y/10Y tiers can never fire on the hub's ~300 bars.
    assert sc.SCANNERS["Consolidation Breakout (6M–10Y)"].get("needs_full_history")


def test_hub_scanner_is_visible_and_in_pipeline():
    assert "Consolidation Breakout (6M–10Y)" in oh.core_scanners()
    assert "Consolidation Breakout (6M–10Y)" in oh.pipeline_scanners()


def test_tiers_longest_first():
    days = [d for d, _l, _f in sc.BREAKOUT_TIERS]
    assert days == sorted(days, reverse=True)


def test_ten_year_break_reports_longest_and_all_cleared():
    rows = bks.breakouts({"AAA": _base_then_break(2600)})
    assert rows and rows[0]["longest"] == "10-Year"
    assert "1-Year" in rows[0]["tiers"]


def test_short_history_cannot_claim_ten_years():
    rows = bks.breakouts({"BBB": _base_then_break(1300)})
    assert rows and rows[0]["longest"] == "5-Year"
    assert bks.short_history({"BBB": _base_then_break(1300)}, 2520) == ["BBB"]


def test_tier_filter_respected():
    rows = bks.breakouts({"AAA": _base_then_break(2600)}, tiers=["1-Year"])
    assert rows and rows[0]["longest"] == "1-Year" and rows[0]["tiers"] == "1-Year"


def test_no_break_no_row():
    df = _base_then_break(2600)
    df.iloc[-1, df.columns.get_loc("close")] = 80.0
    assert bks.breakouts({"CCC": df}) == []


def test_pre_breakout_gate_rejects_a_breakout_bar():
    # Already above the 20-day high: not a PRE-breakout.
    assert not sc.pre_breakout_gate(_base_then_break(300))
