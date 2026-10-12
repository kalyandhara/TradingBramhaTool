"""Tests for elliott_wave.js, run through node (the shipped engine).

Same pattern as test_fibonacci_levels.py: the JS is what the chart draws, so it
is what gets tested. Until B-133..B-136 (2026-10-08) this module had NO tests.

Covers, in the order the backlog's testing plan requires:
  1. hand-built pivot fixtures - zigzag / flat / expanded flat typing, the
     unusual-B flag (B-134), clean W-X-Y and three "looks like W-X-Y but isn't"
     negatives (B-135), two-degree nesting (B-136);
  2. a no-redraw property test - a structure marked final never changes when
     bars are appended;
  3. one real-data regression fixture (Nifty 15m, 2026-10-03 -> 10-08), which
     SKIPS until captured with `py -3 tools/capture_ew_fixture.py`. It pins
     behaviour; it is not evidence of edge.

Skips cleanly when node is unavailable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
JS = str(HERE / "elliott_wave.js").replace("\\", "/")
FIXTURE = HERE / "cache" / "fixtures" / "nifty_15m_2026-10-03_08.json"
pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available")


def ew(expr: str, **data) -> object:
    """Evaluate a JS expression with EW loaded and `data` bound as globals."""
    binds = "".join(f"const {k} = {json.dumps(v)};\n" for k, v in data.items())
    script = (f"global.window = global; require({JS!r});\n{binds}"
              f"process.stdout.write(JSON.stringify({expr}));")
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def pivots(prices: list[float], first: str, provisional_last: bool = False,
           step: int = 10) -> list[dict]:
    """Alternating high/low pivots at evenly spaced bar indices."""
    other = {"high": "low", "low": "high"}
    out, t = [], first
    for i, p in enumerate(prices):
        out.append({"idx": i * step, "time": 1_000_000 + i * step * 60,
                    "price": p, "type": t})
        t = other[t]
    if provisional_last:
        out[-1]["provisional"] = True
    return out


def bars_from_path(prices: list[float], seg: int = 8, warmup: int = 0,
                   step: float | None = None) -> list[dict]:
    """Bars walking linearly between turning points - the zigzag recovers them.

    `warmup` prepends quiet bars at the first price so the ATR is warm before
    the first real swing. Without it the zigzag's threshold is only minPct for
    the first ~15 bars, and a steep synthetic bar registers a high AND a low
    pivot on the same bar (an existing zigzag property, noted in B-135).
    """
    out, t = [], 1_000_000
    for k in range(warmup):
        p0 = prices[0] + (0.1 if k % 2 else -0.1)
        out.append({"time": t, "open": p0, "high": p0 + 0.6, "low": p0 - 0.6,
                    "close": p0, "volume": 1000})
        t += 900
    for a, b in zip(prices, prices[1:]):
        n = max(2, round(abs(b - a) / step)) if step else seg
        for k in range(n):
            c = a + (b - a) * (k + 1) / n
            o = a + (b - a) * k / n
            out.append({"time": t, "open": o, "high": max(o, c) + 0.05,
                        "low": min(o, c) - 0.05, "close": c, "volume": 1000})
            t += 900
    return out


# A valid bullish impulse 100-120-110-150-140-160, then A down to 140.
IMPULSE = [100, 120, 110, 150, 140, 160]


def corrective_after(b_end: float, c_end: float = 120, b_bars: int = 10) -> dict:
    """Impulse + A(160->140) + B(->b_end) + C(->c_end); returns the corrective."""
    pv = pivots(IMPULSE + [140, b_end, c_end], "low")
    if b_bars != 10:                       # stretch B in time only
        for p in pv[7:]:
            p["idx"] += b_bars - 10
            p["time"] += (b_bars - 10) * 60
    return ew("EW.detectCorrectives(pv, EW.detectImpulses(pv))[0]", pv=pv)


# ── existing behaviour, pinned before anything changes ───────────────────────

def test_impulse_fixture_is_detected():
    imps = ew("EW.detectImpulses(pv)", pv=pivots(IMPULSE, "low"))
    assert len(imps) == 1 and imps[0]["bullish"] is True


@pytest.mark.parametrize("b_end,guess", [(150, "zigzag"), (159, "flat"),
                                         (164, "expanded-flat")])
def test_corrective_typing_is_unchanged(b_end, guess):
    assert corrective_after(b_end)["ratios"]["patternGuess"] == guess


# ── B-134: unusual wave B ────────────────────────────────────────────────────
# A = 20 points (160 -> 140). B retrace 15% = 143, 50% = 150, 90% = 158,
# 140% = 168 (beyond the 138.2% expanded-flat ceiling).

@pytest.mark.parametrize("b_end,abnormal", [(143, True), (150, False),
                                            (158, False), (168, True)])
def test_unusual_B_flag_fires_only_outside_23_6_to_138_2(b_end, abnormal):
    r = corrective_after(b_end)["ratios"]
    assert r["bAbnormal"] is abnormal
    if abnormal:
        assert r["bAbnormalReasons"]


def test_shallow_and_deep_B_say_which():
    assert "shallow" in " ".join(corrective_after(143)["ratios"]["bAbnormalReasons"])
    assert "deep" in " ".join(corrective_after(168)["ratios"]["bAbnormalReasons"])


def test_slow_B_is_reported_but_is_a_separate_flag():
    """B lasting > 2x A is a time note, kept apart from the price flag so the
    pre-registered study can test the price definition alone."""
    r = corrective_after(150, b_bars=25)["ratios"]
    assert r["bAbnormal"] is False
    assert r["bSlow"] is True


def test_assessB_boundaries_are_inclusive_normal():
    lo = ew("EW.assessB(100, 23.6, 10, 10)")
    hi = ew("EW.assessB(100, 138.2, 10, 10)")
    assert lo["abnormal"] is False and hi["abnormal"] is False


def test_B_flag_absent_until_B_exists():
    pv = pivots(IMPULSE + [140], "low")
    c = ew("EW.detectCorrectives(pv, EW.detectImpulses(pv))[0]", pv=pv)
    assert "bAbnormal" not in c["ratios"]


# ── B-135: W-X-Y ─────────────────────────────────────────────────────────────
# Downward double zigzag: 200 -a-> 180 -b-> 190 -c-> 170 (W, net 30)
#   -X-> 185 (50% of W) -a-> 168 -b-> 176 -c-> 160 (Y beyond W's end).
DOWN_WXY = [200, 180, 190, 170, 185, 168, 176, 160]


def complex_(prices, first="high", provisional_last=False):
    return ew("EW.detectComplexCorrectives(pv)",
              pv=pivots(prices, first, provisional_last))


def test_clean_down_wxy_is_detected_and_labelled():
    cx = complex_(DOWN_WXY)
    assert len(cx) == 1
    s = cx[0]
    assert s["type"] == "complex-corrective" and s["direction"] == "down"
    assert [p["label"] for p in s["points"]] == ["", "a", "b", "W", "X", "a", "b", "Y"]
    assert s["subtype"] == "double-zigzag"
    assert s["ratios"]["xRetracePct"] == pytest.approx(0.5, abs=1e-9)
    assert s["final"] is True and s["complete"] is True


def test_up_wxy_mirrors():
    up = [400 - p for p in DOWN_WXY]          # low-start mirror
    cx = complex_(up, first="low")
    assert len(cx) == 1 and cx[0]["direction"] == "up"


def test_single_zigzag_is_not_promoted_to_wxy():
    assert complex_([200, 180, 190, 170]) == []


def test_x_too_shallow_is_not_wxy():
    # X retraces 3/30 = 10% of W: below the 38.2% floor.
    assert complex_([200, 180, 190, 170, 173, 160, 166, 150]) == []


def test_x_beyond_w_origin_is_not_wxy():
    # X rallies to 205, past W's 200 start: not a double correction.
    assert complex_([200, 180, 190, 170, 205, 185, 195, 165]) == []


def test_y_that_fails_to_pass_w_end_is_not_wxy():
    # Y ends at 172, short of W's 170 low: a flat/triangle, not W-X-Y.
    assert complex_([200, 180, 190, 170, 185, 175, 181, 172]) == []


def test_forming_wxy_is_not_final_and_has_an_invalidation():
    s = complex_(DOWN_WXY, provisional_last=True)[0]
    assert s["final"] is False
    inv = ew("EW.invalidation(s)", s=s)
    # Y's c is forming: a return above Y's b high (176) breaks the label.
    assert inv["price"] == 176 and inv["side"] == "above" and inv["wave"] == "Y"


def test_y_targets_are_w_multiples_from_x():
    s = complex_(DOWN_WXY)[0]
    lv = ew("EW.fibLevelsForComplex(s)", s=s)
    got = sorted(round(l["price"], 6) for l in lv)
    # W = 30; from X 185 down: 185-18.54, 185-30, 185-48.54
    assert got == sorted([round(185 - 30 * r, 6) for r in (0.618, 1.0, 1.618)])


def test_analyze_exposes_complex_structures():
    bars = bars_from_path(DOWN_WXY + [165])
    out = ew("EW.analyze(bars)", bars=bars)
    assert "complex" in out


def test_internal_B_flags_reuse_the_B134_rule():
    # W's b is 0.5 of a (normal); Y's b retraces 8/17 (normal).
    s = complex_(DOWN_WXY)[0]
    assert s["ratios"]["wB"]["abnormal"] is False
    assert s["ratios"]["yB"]["abnormal"] is False


# ── no-redraw property test ──────────────────────────────────────────────────

def test_final_structures_never_change_as_bars_are_appended():
    path = DOWN_WXY + [172, 150, 166, 140, 158]
    bars = bars_from_path(path)
    script_expr = """(() => {
      const seen = {}; const bad = [];
      for (let k = 40; k <= bars.length; k++) {
        const a = EW.analyze(bars.slice(0, k));
        const all = [...a.impulses, ...a.correctives, ...(a.complex || [])];
        all.filter(s => s.final).forEach(s => {
          const sig = JSON.stringify(s.points.map(p => [p.idx, p.price, p.label]));
          if (seen[s.id] === undefined) seen[s.id] = sig;
          else if (seen[s.id] !== sig) bad.push([k, s.id]);
        });
      }
      return {bad, n: Object.keys(seen).length};
    })()"""
    res = ew(script_expr, bars=bars)
    assert res["bad"] == [], res
    assert res["n"] >= 1, "fixture produced no final structure to check"


# ── B-136: two degrees ───────────────────────────────────────────────────────

def test_two_degrees_nest_minor_inside_major_leg():
    """A big up move whose pullback is itself a W-X-Y at the small degree."""
    # major: 100 -> 140 up, a pullback to 120 that is a minor W-X-Y, then up.
    # Per-bar moves (0.5) stay under the zigzag threshold, so no bar is wide
    # enough to register two pivots on itself.
    bars = bars_from_path([100, 140, 130, 135, 125, 132.5, 124, 128, 120, 175],
                          warmup=20, step=0.5)
    out = ew("EW.analyzeDegrees(bars, {minorMult: 1.2, majorMult: 25.0})", bars=bars)
    assert set(out) >= {"major", "minor", "nesting"}
    assert len(out["major"]["pivots"]) < len(out["minor"]["pivots"])
    for n in out["nesting"]:
        assert n["fromIdx"] <= n["minorStart"] and n["minorEnd"] <= n["toIdx"]
    wxy = [n for n in out["nesting"] if n["minorType"] == "complex-corrective"]
    assert wxy, out["nesting"]
    assert wxy[0]["legDirection"] == "down"     # the W-X-Y IS the major pullback


def test_major_degree_scales_the_minpct_floor_too():
    """On index-sized prices the 0.5% floor, not the ATR term, sets the zigzag
    threshold; scaling only atrMult left both degrees identical (seen on the
    chart, 2026-10-08)."""
    bars = bars_from_path([22000, 22800, 22500, 22650, 22350, 22575, 22320,
                           22440, 22200, 22300], step=12.0)
    d = ew("(()=>{const x=EW.analyzeDegrees(bars,{minorMult:1.2,majorMult:3.6});"
           "return [x.minor.pivots.length, x.major.pivots.length]})()", bars=bars)
    assert d[1] < d[0], d


def test_two_degrees_minor_count_matches_plain_analyze():
    bars = bars_from_path(DOWN_WXY + [165])
    a = ew("EW.analyze(bars, {atrMult: 1.2}).pivots.length", bars=bars)
    d = ew("EW.analyzeDegrees(bars, {minorMult: 1.2, majorMult: 3.0}).minor.pivots.length",
           bars=bars)
    assert a == d


# ── real-data regression fixture ─────────────────────────────────────────────

@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="capture first: py -3 tools/capture_ew_fixture.py")
def test_nifty_15m_oct_3_to_8_contains_a_down_wxy():
    """The SweeGlu chart's W-X-Y (Oct 5 -> Oct 8 2026). Pins behaviour only."""
    bars = json.loads(FIXTURE.read_text(encoding="utf-8"))["bars"]
    cx = ew("EW.analyze(bars).complex", bars=bars)
    assert any(s["direction"] == "down" for s in cx), \
        f"no downward W-X-Y found in {len(bars)} bars"


# ── confirmedAt: when a pivot became KNOWABLE (needed by the B-134/B-135 studies) ─

def test_confirmedAt_is_causal():
    """Every confirmed pivot carries the bar it was confirmed on, and running the
    zigzag on bars[:confirmedAt+1] already shows it as a confirmed pivot."""
    bars = bars_from_path(DOWN_WXY + [172, 150, 166], step=1.0)
    res = ew("""(() => {
      const pv = EW.computeZigzag(bars); const bad = [];
      pv.forEach((p, j) => {
        if (p.provisional) { if (p.confirmedAt !== undefined) bad.push(['prov', j]); return; }
        if (!(p.confirmedAt >= p.idx)) bad.push(['order', j]);
        const sub = EW.computeZigzag(bars.slice(0, p.confirmedAt + 1));
        const hit = sub.find(q => q.idx === p.idx && !q.provisional);
        if (!hit) bad.push(['notyet', j, p.idx, p.confirmedAt]);
        const early = EW.computeZigzag(bars.slice(0, p.confirmedAt));
        const was = early.find(q => q.idx === p.idx && !q.provisional);
        if (was) bad.push(['late', j]);
      });
      return {bad, n: pv.length};
    })()""", bars=bars)
    assert res["bad"] == [], res
    assert res["n"] >= 8


# ── B-137: never two pivots on one bar ───────────────────────────────────────

def _calm_then(path_bars: list[tuple[float, float, float, float]]) -> list[dict]:
    """40 calm bars (range ~1) to warm the ATR, then explicit OHLC bars."""
    out, t = [], 1_000_000
    for k in range(40):
        p = 100 + (0.2 if k % 2 else -0.2)
        out.append({"time": t, "open": p, "high": p + 0.5, "low": p - 0.5,
                    "close": p, "volume": 1000}); t += 900
    for o, h, l, c in path_bars:
        out.append({"time": t, "open": o, "high": h, "low": l, "close": c,
                    "volume": 1000}); t += 900
    return out


def _ramp(a, b, n):
    return [(a + (b - a) * k / n, a + (b - a) * (k + 1) / n + 0.3,
             a + (b - a) * k / n - 0.3, a + (b - a) * (k + 1) / n) for k in range(n)]


# Up-run 100 -> 120, ONE wide bar (high 126, low 114, closes 119), up-run to 140.
WIDE_IN_TREND = _calm_then(_ramp(100, 120, 20) + [(120, 126, 114, 119)] + _ramp(119, 140, 20))
# Up-run to 120, a wide TOP bar (high 128, low 116), then a fall to 100.
WIDE_TOP = _calm_then(_ramp(100, 120, 20) + [(120, 128, 116, 117)] + _ramp(117, 100, 20))


def test_no_two_pivots_ever_share_a_bar():
    for bars in (WIDE_IN_TREND, WIDE_TOP, bars_from_path(DOWN_WXY, seg=3)):
        idx = [p["idx"] for p in ew("EW.computeZigzag(bars)", bars=bars)]
        assert len(idx) == len(set(idx)), idx


def test_a_wide_bar_inside_a_trend_is_not_read_as_a_top_AND_a_bottom():
    """The spike to 126 followed by a bar trading 7 points lower IS a swing high.
    What the bug added was a swing LOW on the same candle - an intra-bar order
    OHLC cannot show. Before B-137 this bar carried both."""
    pv = ew("EW.computeZigzag(bars)", bars=WIDE_IN_TREND)
    wide = 40 + 20                     # index of the wide bar
    kinds = [p["type"] for p in pv if p["idx"] == wide]
    assert kinds in ([], ["high"]), kinds


def test_a_wide_top_bar_is_the_high_but_is_confirmed_by_a_later_bar():
    pv = ew("EW.computeZigzag(bars)", bars=WIDE_TOP)
    wide = 40 + 20
    top = [p for p in pv if p["type"] == "high" and p["idx"] == wide]
    assert top, pv
    assert top[0]["confirmedAt"] > wide


# ── B-138: the LIVE count is the most recent structure, and only if current ──
# Two bullish impulses: an early one (clean ratios, higher score) and a later one.
EARLY = [100, 120, 110, 150, 140, 160]
LATER = [150, 175, 165, 200, 190, 212]            # starts after a 160 -> 150 dip


def _an(prices, first="low", provisional_last=True):
    pv = pivots(prices, first, provisional_last)
    return ew("""(() => { const imps = EW.detectImpulses(pv);
        return {pivots: pv, impulses: imps,
                correctives: EW.detectCorrectives(pv, imps),
                complex: EW.detectComplexCorrectives(pv)}; })()""", pv=pv)


def test_liveCount_picks_the_most_recent_shown_impulse_not_the_best_scored():
    an = _an(EARLY + LATER[0:1] + LATER[1:] + [205])
    imps = an["impulses"]
    assert len(imps) >= 2
    by_score = sorted(imps, key=lambda i: -i["score"])     # the chart's order
    lc = ew("EW.liveCount(an, shown)", an=an, shown=by_score)
    latest = max(imps, key=lambda i: i["points"][-1]["idx"])
    assert lc["impulse"]["id"] == latest["id"]


def test_structure_ending_at_the_latest_swing_is_live():
    an = _an(IMPULSE + [150])                # wave 5 at 160, then one forming leg
    lc = ew("EW.liveCount(an)", an=an)
    assert lc["live"] is True


def test_structure_that_ended_swings_ago_is_not_live():
    """The only known structure is an impulse whose wave 5 is six swings back.
    (Built by hand: real detectors tend to find a newer structure in any six
    later swings, which would rightly be live.)"""
    pv = pivots(IMPULSE + [140, 150, 130, 145, 135, 142, 138], "low", True)
    an = ew("""({pivots: pv, impulses: EW.detectImpulses(pv.slice(0, 6)),
                 correctives: [], complex: []})""", pv=pv)
    lc = ew("EW.liveCount(an)", an=an)
    assert lc["active"] is not None
    assert lc["live"] is False
    assert lc["endedAt"] is not None


def test_a_wxy_at_the_latest_swing_is_the_live_count():
    """Y is the forming swing. The same pivots also read as a 1-5 plus a partial
    A-B ending at Y, so the two tie on recency; the W-X-Y wins the tie. (With a
    further leg after Y, the A-B-C ending on THAT leg is more recent, and is
    correctly chosen instead.)"""
    an = _an(DOWN_WXY, first="high")
    lc = ew("EW.liveCount(an)", an=an)
    assert lc["active"]["type"] == "complex-corrective" and lc["live"] is True
