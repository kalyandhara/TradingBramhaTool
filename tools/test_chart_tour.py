"""Tests for chart_tour.py (B-186, "Tour this chart"), offline.

The tour is a reading of the chart, so the tests pin three things:

  * every detector fires on the rule eVector ships and not one bar or one
    percent either side of it — the badge on a card describes exactly that rule;
  * the chart is only ever asked to do one of seven things, so the page can
    never be told to touch the user's own indicators or drawings;
  * a broken detector costs its own card, never the tour.
"""
import numpy as np
import pandas as pd
import pytest

import chart_tour as ct


def frame(close, *, high=None, low=None, open_=None, volume=None, start="2023-01-02"):
    close = np.asarray(close, float)
    n = len(close)
    idx = pd.bdate_range(start, periods=n, tz="UTC")
    return pd.DataFrame({
        "open": close if open_ is None else np.asarray(open_, float),
        "high": close * 1.005 if high is None else np.asarray(high, float),
        "low": close * 0.995 if low is None else np.asarray(low, float),
        "close": close,
        "volume": np.full(n, 1000.0) if volume is None else np.asarray(volume, float),
    }, index=idx)


# ── actions ───────────────────────────────────────────────────────────────────

ALL_SEVEN = [
    {"type": "CLEAR"},
    {"type": "ZOOM_TO_RANGE", "from": 1, "to": 2},
    {"type": "PRICE_LEVEL", "price": 10.0, "label": "x", "tone": "up"},
    {"type": "HIGHLIGHT_CANDLE", "time": 1, "tone": "accent"},
    {"type": "HIGHLIGHT_RANGE", "from": 1, "to": 2, "tone": "neutral"},
    {"type": "INDICATORS", "ids": ["ema20", "rsi"]},
    {"type": "COMPARE", "symbols": ["^NSEI"]},
]


def test_validate_actions_accepts_the_seven():
    assert ct.validate_actions(ALL_SEVEN) == ALL_SEVEN


def test_validate_actions_rejects_unknown_type():
    with pytest.raises(ValueError, match="DRAW_ARROW"):
        ct.validate_actions([{"type": "DRAW_ARROW"}])


def test_validate_actions_rejects_bad_tone():
    with pytest.raises(ValueError, match="green"):
        ct.validate_actions([{"type": "PRICE_LEVEL", "price": 1.0, "label": "x", "tone": "green"}])


def test_validate_actions_rejects_missing_field():
    with pytest.raises(ValueError, match="price"):
        ct.validate_actions([{"type": "PRICE_LEVEL", "label": "x", "tone": "up"}])


# ── Now ───────────────────────────────────────────────────────────────────────

def test_now_step_range_and_trend():
    df = frame(np.linspace(100, 200, 100))
    s = ct.now_step(df)
    assert s["id"] == "now"
    assert s["facts"]["trend"] == "Uptrend"
    assert s["facts"]["hi63"] == pytest.approx(df["high"].iloc[-63:].max())
    assert s["facts"]["lo63"] == pytest.approx(df["low"].iloc[-63:].min())
    types = [a["type"] for a in s["actions"]]
    assert types.count("PRICE_LEVEL") == 2
    zoom = next(a for a in s["actions"] if a["type"] == "ZOOM_TO_RANGE")
    assert zoom["from"] == ct.t_of(df, -63) and zoom["to"] == ct.t_of(df, -1)
    ct.validate_actions(s["actions"])


def test_now_step_downtrend_and_sideways():
    assert ct.now_step(frame(np.linspace(200, 100, 100)))["facts"]["trend"] == "Downtrend"
    assert ct.now_step(frame(np.full(100, 100.0)))["facts"]["trend"] == "Sideways"


def test_now_step_rvol_skips_zero_volume():
    s = ct.now_step(frame(np.linspace(100, 200, 100), volume=np.zeros(100)))
    assert s["facts"]["rvol"] is None
    assert "volume" not in s["body"].lower()


def test_t_of_is_unix_seconds():
    df = frame(np.full(5, 1.0), start="2024-01-01")
    assert ct.t_of(df, 0) == int(pd.Timestamp("2024-01-01", tz="UTC").timestamp())


# ── breakout / breakdown (55-session closing extremes) ───────────────────────

def _flat_then(n=80, at=-5, value=106.0, after=105.0, base=100.0):
    c = np.full(n, base)
    k = n + at
    c[k] = value
    c[k + 1:] = after
    return c


def test_breakout55_fires_and_watch_is_98pct():
    df = frame(_flat_then())
    f = ct.det_breakout55(df)
    assert len(f) == 1 and f[0].detector == "breakout55" and f[0].tone == "up"
    assert f[0].facts["level"] == pytest.approx(100.0)
    assert f[0].watch["level"] == pytest.approx(98.0)
    assert f[0].time == ct.t_of(df, -5)
    ct.validate_actions(f[0].actions)


def test_breakout_becomes_failed_below_98pct():
    df = frame(_flat_then(after=97.5))
    f = ct.det_breakout55(df)
    assert f[0].detector == "failed_breakout55" and f[0].tone == "down"


def test_breakout_at_exactly_98pct_is_not_failed():
    assert ct.det_breakout55(frame(_flat_then(after=98.0)))[0].detector == "breakout55"


def test_breakout_older_than_15_bars_ignored():
    assert ct.det_breakout55(frame(_flat_then(at=-20))) == []


def test_breakout_weight_formula():
    c = _flat_then(at=-1, value=106.0)
    v = np.full(80, 1000.0)
    v[-1] = 2000.0
    f = ct.det_breakout55(frame(c, volume=v))
    assert f[0].weight == pytest.approx(0.7 + 14 / 50 + 0.2)


def test_breakdown55_mirror_and_failed_at_102pct():
    f = ct.det_breakdown55(frame(_flat_then(value=94.0, after=95.0)))
    assert f[0].detector == "breakdown55" and f[0].tone == "down"
    assert f[0].watch["level"] == pytest.approx(102.0)
    g = ct.det_breakdown55(frame(_flat_then(value=94.0, after=102.5)))
    assert g[0].detector == "failed_breakdown55" and g[0].tone == "up"


# ── gaps ──────────────────────────────────────────────────────────────────────

def _gap_frame(gap=0.035, at=-4, fill=False, n=80):
    c = np.full(n, 100.0)
    k = n + at
    c[k:] = 100.0 * (1 + gap)
    o = c.copy()
    lo = c * 0.995
    hi = c * 1.005
    if fill:
        lo[k + 1] = 99.9 if gap > 0 else lo[k + 1]
        hi[k + 1] = 100.1 if gap < 0 else hi[k + 1]
    return frame(c, open_=o, low=lo, high=hi)


def test_gap_up_unfilled_fires_filled_does_not():
    f = ct.det_gaps(_gap_frame())
    assert len(f) == 1 and f[0].detector == "gap_up"
    assert f[0].watch["level"] == pytest.approx(100.0)
    assert ct.det_gaps(_gap_frame(fill=True)) == []


def test_gap_down_unfilled():
    f = ct.det_gaps(_gap_frame(gap=-0.04))
    assert f[0].detector == "gap_down" and f[0].tone == "down"


def test_gap_below_3pct_ignored():
    assert ct.det_gaps(_gap_frame(gap=0.029)) == []


def test_gap_older_than_10_bars_ignored():
    assert ct.det_gaps(_gap_frame(at=-12)) == []


# ── volume / ATR expansion, squeeze ───────────────────────────────────────────

def _vol_frame(last5):
    v = np.full(80, 1000.0)
    v[-5:] = last5
    return frame(np.linspace(100, 110, 80), volume=v)


def test_volume_expansion_threshold_and_weight():
    f = ct.det_volume_expansion(_vol_frame(1500.0))
    assert f and f[0].detector == "volume_expansion"
    assert f[0].weight == pytest.approx(0.4)
    assert f[0].tone == "up"                          # price rose over the 5 bars
    assert ct.det_volume_expansion(_vol_frame(1490.0)) == []


def test_volume_expansion_skips_nan_or_zero_volume():
    assert ct.det_volume_expansion(frame(np.linspace(100, 110, 80), volume=np.zeros(80))) == []
    assert ct.det_volume_expansion(frame(np.linspace(100, 110, 80), volume=np.full(80, np.nan))) == []


def _range_frame(late_range, n=120, k=42):
    c = np.full(n, 100.0)
    rng = np.full(n, 1.0)
    rng[-k:] = late_range
    return frame(c, high=c + rng / 2, low=c - rng / 2)


def test_atr_expansion_fires_on_a_widening_range():
    f = ct.det_atr_expansion(_range_frame(3.0))
    assert f and f[0].detector == "atr_expansion" and f[0].tone == "neutral"
    assert f[0].facts["ratio"] >= 1.4


def test_atr_expansion_quiet_on_a_small_widening():
    assert ct.det_atr_expansion(_range_frame(1.2)) == []


def _wave(amp_early, amp_late, n=200, k=20):
    i = np.arange(n)
    amp = np.where(i < n - k, amp_early, amp_late)
    return frame(100 + amp * np.where(i % 2 == 0, 1, -1))


def test_squeeze_narrowest_in_126():
    f = ct.det_squeeze(_wave(2.0, 0.5))
    assert f and f[0].detector == "squeeze" and f[0].tone == "neutral"
    assert f[0].weight == pytest.approx(0.65)
    assert ct.det_squeeze(_wave(0.5, 2.0)) == []


# ── divergence ────────────────────────────────────────────────────────────────

def _swing_frame(bearish=True, n=80, p1=-30, p2=-10):
    base = 100 + 0.1 * np.arange(n) if bearish else 100 - 0.1 * np.arange(n)
    hi = base + 0.5
    lo = base - 0.5
    a, b = n + p1, n + p2
    if bearish:
        hi[a] = base[a] + 5
        hi[b] = base[b] + 5
    else:
        lo[a] = base[a] - 5
        lo[b] = base[b] - 5
    return frame(base, high=hi, low=lo), a, b


def _pin_rsi(monkeypatch, n, a, b, ra, rb):
    r = np.full(n, 50.0)
    r[a], r[b] = ra, rb
    monkeypatch.setattr(ct, "_rsi", lambda close: pd.Series(r, index=close.index))


def test_bearish_divergence_needs_rsi_gap_over_4(monkeypatch):
    df, a, b = _swing_frame(True)
    _pin_rsi(monkeypatch, len(df), a, b, 70, 64)
    f = [x for x in ct.det_divergence(df) if x.detector == "bearish_div"]
    assert f and f[0].tone == "down" and f[0].weight == pytest.approx(0.7)
    assert f[0].watch["level"] == pytest.approx(df["high"].iloc[b])
    _pin_rsi(monkeypatch, len(df), a, b, 70, 67)
    assert [x for x in ct.det_divergence(df) if x.detector == "bearish_div"] == []


def test_bullish_divergence_mirror(monkeypatch):
    df, a, b = _swing_frame(False)
    _pin_rsi(monkeypatch, len(df), a, b, 30, 36)
    f = [x for x in ct.det_divergence(df) if x.detector == "bullish_div"]
    assert f and f[0].tone == "up"


# ── 200-day average, crosses ──────────────────────────────────────────────────

def _step(n=260, k=10, to=105.0):
    c = np.full(n, 100.0)
    c[-k:] = to
    return frame(c)


def test_sma200_state_and_cross_time():
    df = _step(k=10)
    f = ct.det_sma200(df)
    assert f[0].detector == "above_sma200" and f[0].time == ct.t_of(df, -10)
    assert f[0].watch["level"] == pytest.approx(df["close"].rolling(200).mean().iloc[-1])
    g = ct.det_sma200(_step(k=50))
    assert g[0].detector == "above_sma200" and g[0].time is None
    h = ct.det_sma200(_step(k=10, to=95.0))
    assert h[0].detector == "below_sma200" and h[0].tone == "down"


def test_golden_and_death_cross_within_20():
    up = np.r_[np.full(245, 100.0), np.linspace(101, 130, 15)]
    f = ct.det_crosses(frame(up))
    assert f and f[0].detector == "golden_cross"
    dn = np.r_[np.full(245, 100.0), np.linspace(99, 70, 15)]
    assert ct.det_crosses(frame(dn))[0].detector == "death_cross"
    old = np.r_[np.full(200, 100.0), np.linspace(101, 130, 60)]
    assert ct.det_crosses(frame(old)) == []


# ── desk detectors (wrappers) ─────────────────────────────────────────────────

import scanner_templates as sc  # noqa: E402
import flag_pole as fp  # noqa: E402
import harmonic_patterns as hp  # noqa: E402


def _base(n=120):
    return frame(np.linspace(100, 120, n))


def test_structure_break_held_from_chain(monkeypatch):
    df = _base()
    n = len(df)
    monkeypatch.setattr(sc, "detect_structure_chain", lambda d, **k: {"events": [
        {"bar": n - 3, "type": "BOS", "direction": "up", "level": 105.0, "quality": "STRONG",
         "failed": False, "failed_bar": None}]})
    f = ct.det_structure_break_held(df)
    assert f and f[0].detector == "structure_break_held" and f[0].tone == "up"
    assert f[0].watch["level"] == pytest.approx(105.0)
    assert f[0].time == ct.t_of(df, n - 3)


def test_structure_break_failed_or_old_gives_nothing(monkeypatch):
    df = _base()
    n = len(df)
    monkeypatch.setattr(sc, "detect_structure_chain", lambda d, **k: {"events": [
        {"bar": n - 3, "type": "BOS", "direction": "up", "level": 105.0, "failed": True}]})
    assert ct.det_structure_break_held(df) == []
    monkeypatch.setattr(sc, "detect_structure_chain", lambda d, **k: {"events": [
        {"bar": n - 40, "type": "BOS", "direction": "up", "level": 105.0, "failed": False}]})
    assert ct.det_structure_break_held(df) == []


def test_liquidity_sweep_bull_only(monkeypatch):
    df = _base()
    monkeypatch.setattr(sc, "detect_liquidity_sweep",
                        lambda d, **k: {"direction": "bearish", "level": 130.0, "bars_ago": 1})
    assert ct.det_liquidity_sweep_bull(df) == []
    monkeypatch.setattr(sc, "detect_liquidity_sweep",
                        lambda d, **k: {"direction": "bullish", "level": 95.0, "bars_ago": 2,
                                        "touches": 3})
    f = ct.det_liquidity_sweep_bull(df)
    assert f and f[0].tone == "up" and f[0].watch["level"] == pytest.approx(95.0)
    assert f[0].time == ct.t_of(df, -3)


def test_flag_pole_bull(monkeypatch):
    df = _base()
    n = len(df)
    monkeypatch.setattr(fp, "detect_flag_pole", lambda d, direction="bull", **k: {
        "direction": "bull", "flag_end": n - 2, "pole_low": 100.0, "pole_high": 115.0,
        "flag_high": 114.0, "flag_low": 110.0, "entry": 114.0, "stop": 110.0, "target": 129.0,
        "broken": False})
    f = ct.det_flag_pole_bull(df)
    assert f and f[0].watch["level"] == pytest.approx(110.0)


def test_abcd_requires_bullish_abcd(monkeypatch):
    df = _base()
    monkeypatch.setattr(sc, "scan_harmonic_reversal", lambda d: {
        "pattern_type": "Harmonic Gartley", "direction": "bullish", "entry": 100.0, "stop": 95.0})
    assert ct.det_abcd(df) == []
    monkeypatch.setattr(sc, "scan_harmonic_reversal", lambda d: {
        "pattern_type": "Harmonic AB=CD", "direction": "bullish", "entry": 100.0, "stop": 92.0})
    monkeypatch.setattr(hp, "detect_last_pattern",
                        lambda d, **k: {"points": {"D": {"idx": len(d) - 3, "price": 100.0}}})
    f = ct.det_abcd(df)
    assert f and f[0].watch["level"] == pytest.approx(92.0)
    assert f[0].time == ct.t_of(df, len(df) - 3)


def test_adx_up_state_rule():
    # chop, then a trend: ADX climbs (a trend with no down-moves pins ADX at 100,
    # which is not "rising")
    up = np.r_[100 + np.where(np.arange(60) % 2 == 0, 1.0, -1.0), np.linspace(100, 160, 60)]
    assert [f.detector for f in ct.det_adx_up_state(frame(up))] == ["adx_up_state"]
    flat = 100 + np.where(np.arange(120) % 2 == 0, 1.0, -1.0)
    assert ct.det_adx_up_state(frame(flat)) == []


def test_wrapper_tolerates_missing_keys(monkeypatch):
    df = _base()
    monkeypatch.setattr(sc, "detect_liquidity_sweep", lambda d, **k: {})
    monkeypatch.setattr(sc, "detect_structure_chain", lambda d, **k: {})
    monkeypatch.setattr(fp, "detect_flag_pole", lambda d, direction="bull", **k: {})
    assert ct.det_liquidity_sweep_bull(df) == []
    assert ct.det_structure_break_held(df) == []
    assert ct.det_flag_pole_bull(df) == []


def test_study_links_are_exactly_five():
    assert ct.STUDY_LINKS == {"structure_break_held": "B-114", "liquidity_sweep_bull": "B-41m",
                              "flag_pole_bull": "B-92", "abcd": "B-132", "adx_up_state": "ADX"}
    assert all(ct.DETECTORS[k].family == "desk" for k in ct.STUDY_LINKS)


def test_desk_wrappers_run_on_real_detectors():
    df = frame(100 + np.cumsum(np.random.default_rng(3).normal(0, 1, 300)))
    for k in ct.STUDY_LINKS:
        for f in ct.DETECTORS[k].fn(df):
            ct.validate_actions(f.actions)


# ── Stock or market? ─────────────────────────────────────────────────────────

def _ret_frame(total, n=80):
    return frame(np.r_[np.full(n - 21, 100.0), np.linspace(100, 100 * (1 + total), 21)])


def test_context_verdict_bands():
    s = ct.context_step(_ret_frame(0.12), _ret_frame(0.02), _ret_frame(0.04), "Energy",
                        sector_symbol="^CNXENERGY")
    assert s["id"] == "context" and s["facts"]["verdict"] == "ahead"
    assert s["facts"]["stock20"] == pytest.approx(0.12)
    cmp_ = next(a for a in s["actions"] if a["type"] == "COMPARE")
    assert cmp_["symbols"] == ["^NSEI", "^CNXENERGY"]
    s2 = ct.context_step(_ret_frame(0.06), _ret_frame(0.02), _ret_frame(0.04), "Energy")
    assert s2["facts"]["verdict"] == "in line"
    s3 = ct.context_step(_ret_frame(-0.05), _ret_frame(0.02), _ret_frame(0.04), "Energy")
    assert s3["facts"]["verdict"] == "behind"


def test_context_without_sector():
    s = ct.context_step(_ret_frame(0.12), _ret_frame(0.02), None, None)
    assert s["facts"]["sector20"] is None and s["facts"]["verdict"] == "ahead"
    assert next(a for a in s["actions"] if a["type"] == "COMPARE")["symbols"] == ["^NSEI"]


# ── badges ────────────────────────────────────────────────────────────────────

RATES = {"asOf": "2026-10-20", "detectors": {
    "breakout55": {"label": "ORDINARY", "n_events": 3412, "n_symbols": 287, "mean20": 0.002,
                   "p20": 0.41, "p20_holm": 1.0},
    "liquidity_sweep_bull": {"label": "EDGE", "n_events": 900, "n_symbols": 210, "mean20": 0.0051,
                             "p20": 0.001, "p20_holm": 0.01}}}
TODAY = pd.Timestamp("2026-10-26")


def test_badge_not_measured_when_missing():
    assert ct.badge_for("breakout55", None, TODAY)["label"] == "NOT_MEASURED"
    assert ct.badge_for("squeeze", RATES, TODAY)["label"] == "NOT_MEASURED"
    assert ct.badge_for("squeeze", RATES, TODAY)["text"] == "Not measured"


def test_badge_text_format():
    b = ct.badge_for("breakout55", RATES, TODAY)
    assert b["label"] == "ORDINARY" and not b["stale"]
    assert b["text"] == "Ordinary · +0.2% vs a normal day @20d · 3412 events / 287 names · p 0.41 · as of 2026-10"
    assert b["study"] is None


def test_badge_stale_after_45_days():
    assert ct.badge_for("breakout55", RATES, pd.Timestamp("2026-12-10"))["stale"] is True
    assert ct.badge_for("breakout55", RATES, pd.Timestamp("2026-11-30"))["stale"] is False


def test_badge_study_link_for_desk_detector():
    b = ct.badge_for("liquidity_sweep_bull", RATES, TODAY)
    assert b["label"] == "EDGE" and b["text"].startswith("Edge ·")
    assert b["study"]["id"] == "B-41m" and "0.51" in b["study"]["headline"]


# ── build_tour ────────────────────────────────────────────────────────────────

def _fake(key, t, w):
    return ct.Finding(id=f"{key}:{t}", detector=key, title=key, body="", facts={}, time=t,
                      weight=w, tone="up", watch=None, actions=[{"type": "CLEAR"}])


def test_build_tour_order_and_cap(monkeypatch):
    dets = {}
    for k in range(10):
        key = f"d{k}"
        dets[key] = ct.Detector(key, key, "evector", "dated", "directional",
                                (lambda df, key=key, k=k: [_fake(key, 1000 + (k // 2), 0.1 * k)]))
    monkeypatch.setattr(ct, "DETECTORS", dets)
    tour = ct.build_tour(_base(), market_df=None, sector_df=None, sector_label=None,
                         base_rates=None, today=TODAY)
    found = [s for s in tour["steps"] if s["id"] not in ("now", "context")]
    assert len(found) == 8
    assert [s["detector"] for s in found[:3]] == ["d9", "d8", "d7"]   # newest, then weight
    assert all(s["badge"]["label"] == "NOT_MEASURED" for s in found)


def test_build_tour_short_history():
    tour = ct.build_tour(frame(np.linspace(100, 110, 60)), market_df=None, sector_df=None,
                         sector_label=None, base_rates=None, today=TODAY)
    assert [s["id"] for s in tour["steps"]] == ["now"]
    assert "Too little history for findings." in tour["notes"]


def test_build_tour_skips_raising_detector(monkeypatch):
    def boom(df):
        raise KeyError("pattern")
    dets = {"ok": ct.Detector("ok", "ok", "evector", "dated", "directional", lambda df: [_fake("ok", 5, 0.5)]),
            "bad": ct.Detector("bad", "bad", "desk", "dated", "directional", boom)}
    monkeypatch.setattr(ct, "DETECTORS", dets)
    tour = ct.build_tour(_base(), market_df=None, sector_df=None, sector_label=None,
                         base_rates=None, today=TODAY)
    assert [s["detector"] for s in tour["steps"] if s.get("detector")] == ["ok"]
    assert any("bad" in n for n in tour["notes"])


def test_build_tour_keeps_one_card_per_finding_when_a_fn_backs_two_keys(monkeypatch):
    f = lambda df: [_fake("breakout55", 7, 0.5)]  # noqa: E731
    dets = {"breakout55": ct.Detector("breakout55", "b", "evector", "dated", "directional", f),
            "failed_breakout55": ct.Detector("failed_breakout55", "fb", "evector", "dated", "directional", f)}
    monkeypatch.setattr(ct, "DETECTORS", dets)
    tour = ct.build_tour(_base(), market_df=None, sector_df=None, sector_label=None,
                         base_rates=None, today=TODAY)
    assert len([s for s in tour["steps"] if s.get("detector")]) == 1


def test_every_action_in_a_tour_is_valid():
    df = frame(100 + np.cumsum(np.random.default_rng(7).normal(0.1, 1.5, 320)))
    tour = ct.build_tour(df, market_df=_ret_frame(0.02, 320), sector_df=None, sector_label=None,
                         base_rates=RATES, today=TODAY)
    assert tour["steps"][0]["id"] == "now" and tour["steps"][1]["id"] == "context"
    for s in tour["steps"]:
        ct.validate_actions(s["actions"])


# ── security review: a malformed base-rate file never blanks or crashes a badge ──

@pytest.mark.parametrize("bad", [
    {"detectors": {"breakout55": RATES["detectors"]["breakout55"]}},                 # no asOf
    {"asOf": "not-a-date", "detectors": {"breakout55": RATES["detectors"]["breakout55"]}},
    {"asOf": "2026-10-20", "detectors": {"breakout55": {"label": "ORDINARY", "mean20": 0.01}}},
    {"asOf": "2026-10-20", "detectors": {"breakout55": "not a dict"}},
])
def test_badge_survives_malformed_rates(bad):
    b = ct.badge_for("breakout55", bad, TODAY)
    assert b["label"] in ct.LABEL_TEXT and b["text"]


def test_badge_label_clamped_to_known_set():
    bad = {"asOf": "2026-10-20", "detectors": {"breakout55": {**RATES["detectors"]["breakout55"],
                                                              "label": "<script>x</script>"}}}
    assert ct.badge_for("breakout55", bad, TODAY)["label"] == "NOT_MEASURED"


def test_build_tour_survives_a_badge_failure(monkeypatch):
    monkeypatch.setattr(ct, "badge_for", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    df = frame(100 + np.cumsum(np.random.default_rng(7).normal(0.1, 1.5, 320)))
    tour = ct.build_tour(df, market_df=None, sector_df=None, sector_label=None, base_rates=RATES, today=TODAY)
    found = [s for s in tour["steps"] if s.get("detector")]
    assert all(s["badge"]["label"] == "NOT_MEASURED" for s in found)


def test_flag_identity_is_its_pole_not_its_moving_flag_end(monkeypatch):
    """A flag grows a bar at a time; if its card id followed flag_end, one pattern
    would be counted as a new event every day in the base rates."""
    df = _base()
    n = len(df)
    def geo(end):
        return lambda d, direction="bull", **k: {"pole_end": n - 12, "flag_end": end, "entry": 114.0,
                                                 "stop": 110.0, "target": 129.0, "broken": False}
    monkeypatch.setattr(fp, "detect_flag_pole", geo(n - 3))
    a = ct.det_flag_pole_bull(df)[0].id
    monkeypatch.setattr(fp, "detect_flag_pole", geo(n - 2))
    assert ct.det_flag_pole_bull(df)[0].id == a


# ── badge wording: the number reads in the stock's own direction ──────────────

def test_badge_bearish_card_shows_the_real_direction():
    rates = {"asOf": "2026-10-20", "detectors": {"below_sma200": {
        "label": "EDGE", "n_events": 1646, "n_symbols": 258, "mean20": 0.0101, "p20": 0.0004}}}
    b = ct.badge_for("below_sma200", rates, TODAY, tone="down")
    assert b["text"].startswith("Edge · -1.0% vs a normal day @20d")
    assert "p < 0.001" in b["text"]


def test_badge_magnitude_card_reads_as_larger_moves():
    rates = {"asOf": "2026-10-20", "detectors": {"atr_expansion": {
        "label": "EDGE", "n_events": 1593, "n_symbols": 258, "mean20": 0.0059, "p20": 0.0022}}}
    b = ct.badge_for("atr_expansion", rates, TODAY, tone="neutral")
    assert b["text"].startswith("Edge · moves 0.6 pts larger than a normal day @20d")
    assert "p 0.002" in b["text"]


def test_badge_unconfirmed_edge_is_flagged():
    rates = {"asOf": "2026-10-20", "detectors": {"below_sma200": {
        "label": "EDGE", "n_events": 1646, "n_symbols": 258, "mean20": 0.0101, "p20": 0.0004, "confirmed": False}}}
    b = ct.badge_for("below_sma200", rates, TODAY, tone="down")
    assert b["unconfirmed"] is True and b["text"].endswith("not confirmed on a fresh panel")
    rates["detectors"]["below_sma200"]["confirmed"] = True
    assert ct.badge_for("below_sma200", rates, TODAY, tone="down")["unconfirmed"] is False


# ── final review I-4 / M-4 ────────────────────────────────────────────────────

def test_build_tour_runs_detectors_on_the_measured_window(monkeypatch):
    seen = []
    det = ct.Detector("w", "w", "evector", "dated", "directional", lambda d: seen.append(len(d)) or [])
    monkeypatch.setattr(ct, "DETECTORS", {"w": det})
    ct.build_tour(frame(np.linspace(100, 150, 400)), market_df=None, sector_df=None, sector_label=None,
                  base_rates=None, today=TODAY)
    assert seen == [ct.DETECTOR_WINDOW] and ct.DETECTOR_WINDOW == 260


def test_badge_magnitude_negative_reads_smaller():
    rates = {"asOf": "2026-10-20", "detectors": {"squeeze": {
        "label": "ORDINARY", "n_events": 1570, "n_symbols": 258, "mean20": -0.0046, "p20": 0.008}}}
    assert "moves 0.5 pts smaller than a normal day" in ct.badge_for("squeeze", rates, TODAY, tone="neutral")["text"]


def test_sweep_card_sees_full_history_others_the_window(monkeypatch):
    """B-186d: pools older than 260 bars are what the sweep trades, so its card gets
    the whole series; every other card keeps DETECTOR_WINDOW."""
    seen = {}

    def rec(key):
        def fn(df):
            seen[key] = len(df)
            return []
        return fn
    dets = {k: ct.Detector(k, k, "desk", "dated", "directional", rec(k))
            for k in ("liquidity_sweep_bull", "gap_up")}
    monkeypatch.setattr(ct, "DETECTORS", dets)
    ct.build_tour(_base(600), market_df=None, sector_df=None, sector_label=None,
                  base_rates=None, today=TODAY)
    assert seen == {"liquidity_sweep_bull": 600, "gap_up": ct.DETECTOR_WINDOW}
