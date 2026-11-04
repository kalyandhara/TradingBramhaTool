"""Qullamaggie setups on daily bars — breakout/continuation, Episodic Pivot, and
the NIFTY SMA10/SMA20 momentum-long switch on the regime read.

Synthetic frames, built so each rule can be broken one at a time.

Run:  python -m pytest tools/test_qullamaggie_scans.py -q
"""
import numpy as np
import pandas as pd

import market_verdict as mv
import opportunity_hub as oh
import scanner_templates as sc


def _ohlcv(close, rng_pct=0.02, vol=1e6, opens=None):
    c = np.asarray(close, dtype=float)
    o = c.copy() if opens is None else np.asarray(opens, dtype=float)
    r = np.full(len(c), rng_pct) if np.isscalar(rng_pct) else np.asarray(rng_pct)
    hi = np.maximum(o, c) * (1 + r / 2)
    lo = np.minimum(o, c) * (1 - r / 2)
    v = np.full(len(c), vol) if np.isscalar(vol) else np.asarray(vol, dtype=float)
    idx = pd.bdate_range("2025-01-01", periods=len(c))
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c,
                         "volume": v}, index=idx)


# ── Breakout / continuation ──────────────────────────────────────────────────

def _breakout_frame(run=0.6, base_rng=0.008, breakout=True, vol_x=2.5,
                    base_drift=-0.003):
    """Flat 150 bars → a `run` rally over 40 bars (wide ranges) → a 10-bar tight
    base drifting slightly lower → today's bar."""
    flat = np.full(150, 100.0)
    leg = 100 * (1 + run) ** (np.arange(1, 41) / 40)
    top = leg[-1]
    base = top * (1 + base_drift) ** np.arange(1, 11)
    pivot_proxy = base.max() * (1 + base_rng / 2)
    today = pivot_proxy * (1.03 if breakout else 0.99)
    close = np.concatenate([flat, leg, base, [today]])
    rng = np.concatenate([np.full(150, 0.02), np.full(40, 0.04),
                          np.full(10, base_rng), [0.03]])
    vol = np.full(len(close), 1e6)
    vol[-1] = 1e6 * vol_x
    return _ohlcv(close, rng, vol)


def test_breakout_fires_with_plan_and_no_target():
    card = sc.scan_qullamaggie_breakout(_breakout_frame())
    assert card and card["pattern_type"] == "Qullamaggie Breakout"
    assert "Breakout" in card["tags"]
    assert card.get("actionable", True) is True
    assert card["stop"] < card["entry"]
    assert "target" not in card          # he trails; the harness must not simulate a plan


def test_light_volume_or_short_of_pivot_is_a_non_actionable_setup():
    for df in (_breakout_frame(vol_x=1.0), _breakout_frame(breakout=False)):
        card = sc.scan_qullamaggie_breakout(df)
        assert card and card["actionable"] is False
        assert "Pre-breakout" in card["tags"]


def test_breakout_needs_a_prior_run():
    assert sc.scan_qullamaggie_breakout(_breakout_frame(run=0.15)) is None


def test_breakout_needs_a_tight_base():
    assert sc.scan_qullamaggie_breakout(_breakout_frame(base_rng=0.05)) is None


def test_breakout_needs_price_above_the_short_mas():
    # A base that bleeds 2%/bar drops under the SMA20 — not "surfing" the MAs.
    assert sc.scan_qullamaggie_breakout(_breakout_frame(base_drift=-0.02)) is None


# ── Episodic Pivot ───────────────────────────────────────────────────────────

def _ep_frame(gap=0.12, vol_x=5.0, prior_run=0.05, bars_after=0,
              undercut=False, weak_close=False):
    n_pre = 130
    pre = 100 * (1 + prior_run) ** (np.arange(n_pre) / (n_pre - 1))
    prev = pre[-1]
    ep_open = prev * (1 + gap)
    ep_close = ep_open * (0.97 if weak_close else 1.03)
    after = np.full(bars_after, ep_close * 1.01)
    if undercut and bars_after:
        after[-1] = ep_open * 0.9
    close = np.concatenate([pre, [ep_close], after])
    opens = close.copy()
    opens[n_pre] = ep_open
    vol = np.full(len(close), 1e6)
    vol[n_pre] = 1e6 * vol_x
    rng = np.full(len(close), 0.01)
    if weak_close:
        rng[n_pre] = 0.06
    return _ohlcv(close, rng, vol, opens=opens)


def test_ep_fires_on_a_quiet_stock_gapping_on_volume():
    card = sc.scan_episodic_pivot(_ep_frame())
    assert card and card["pattern_type"] == "Episodic Pivot"
    assert card["stop"] < card["entry"]
    assert card["event_date"]
    assert "EP today" in card["tags"]


def test_ep_still_fires_days_later_while_holding():
    card = sc.scan_episodic_pivot(_ep_frame(bars_after=2))
    assert card and "EP 2d ago" in card["tags"]


def test_ep_rejects_each_broken_rule():
    assert sc.scan_episodic_pivot(_ep_frame(gap=0.05)) is None          # small gap
    assert sc.scan_episodic_pivot(_ep_frame(vol_x=2.0)) is None         # no volume
    assert sc.scan_episodic_pivot(_ep_frame(prior_run=0.6)) is None     # not quiet
    assert sc.scan_episodic_pivot(_ep_frame(bars_after=3, undercut=True)) is None
    assert sc.scan_episodic_pivot(_ep_frame(weak_close=True)) is None   # gap faded
    assert sc.scan_episodic_pivot(_ep_frame(bars_after=6)) is None      # too old


def test_a_nan_price_stub_bar_cannot_fire_either_scanner():
    """yfinance's unfinished-session bar: NaN prices, real volume. Seen live
    2026-10-12 — 16 'EP today' cards with a nan% gap before the dropna."""
    for scan, df in ((sc.scan_episodic_pivot, _ep_frame(gap=0.01)),
                     (sc.scan_qullamaggie_breakout, _breakout_frame(run=0.1))):
        stub = df.iloc[[-1]].copy()
        stub.index = [df.index[-1] + pd.offsets.BDay()]
        stub[["open", "high", "low", "close"]] = np.nan
        stub["volume"] = 9e7
        assert scan(pd.concat([df, stub])) is None


# ── Registry / confluence placement ──────────────────────────────────────────

def test_registered_and_capped_inside_existing_families():
    assert sc.SCANNERS["Qullamaggie Breakout"]["fn"] is sc.scan_qullamaggie_breakout
    assert sc.SCANNERS["Episodic Pivot"]["fn"] is sc.scan_episodic_pivot
    for name in ("Qullamaggie Breakout", "Episodic Pivot"):
        # B-147 measured both (NULL at 20d), so the description cites it and
        # the tier is "weak" — measured, not shown to beat an ordinary bar.
        assert "MEASURED NULL" in sc.SCANNERS[name]["description"]
        assert "B-147" in sc.SCANNERS[name]["description"]
        assert oh.scanner_tier(name) == "weak"
    # One fact, one vote: a base breakout votes with the base family, an EP
    # with PEAD — never as an extra family of its own.
    assert oh.scanner_family("Qullamaggie Breakout") == "Base/Contraction"
    assert oh.scanner_family("Episodic Pivot") == "Event"


# ── Regime: the SMA10/SMA20 momentum-long switch ─────────────────────────────

def test_momentum_longs_switch_follows_sma10_vs_sma20():
    up = pd.DataFrame({"close": np.linspace(100, 130, 120)})
    down = pd.DataFrame({"close": np.concatenate([np.linspace(100, 130, 100),
                                                  np.linspace(130, 120, 20)])})
    r_up, r_down = mv.classify_regime(up), mv.classify_regime(down)
    assert r_up["momentum_longs"] is True and r_up["sma10"] > r_up["sma20"]
    # Still above the 50 SMA (label unchanged) but the short switch is off.
    assert r_down["momentum_longs"] is False
    assert mv.classify_regime(None)["momentum_longs"] is None
