"""chart_tour.py — "Tour this chart" (B-186): what the daily chart is doing now,
and what would change the reading next.

Spec: docs/superpowers/specs/2026-10-26-chart-tour-design.md

A tour is two fixed steps (Now, Stock-or-market?) and up to eight findings. Each
step is a plain sentence plus a list of chart ACTIONS from a closed set of seven,
so the chart page can only ever be asked to zoom, draw a level, highlight, toggle
an indicator or overlay a comparison — never to touch the user's own drawings.

The detectors are eVector's (thresholds copied verbatim from its shipped bundle,
REA pass 2026-10-26) and five of the desk's own, called rather than copied. The
same functions feed `tour_base_rates.py`, so the badge on a card always measures
the rule that drew it. Pure: no file or network I/O here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

ACTION_TYPES: dict[str, tuple[str, ...]] = {
    "CLEAR": (),
    "ZOOM_TO_RANGE": ("from", "to"),
    "PRICE_LEVEL": ("price", "label", "tone"),
    "HIGHLIGHT_CANDLE": ("time", "tone"),
    "HIGHLIGHT_RANGE": ("from", "to", "tone"),
    "INDICATORS": ("ids",),
    "COMPARE": ("symbols",),
}
TONES = {"up", "down", "neutral", "accent"}


@dataclass
class Finding:
    id: str
    detector: str
    title: str
    body: str
    facts: dict
    time: int | None            # unix seconds of the anchoring bar; None = a current state
    weight: float               # ordering only, never shown as meaning
    tone: str                   # "up" | "down" | "neutral"
    watch: dict | None          # {"text": str, "level": float | None}
    actions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Detector:
    key: str
    label: str
    family: str                 # "evector" | "desk"
    kind: str                   # "dated" | "state"
    claim: str                  # "directional" | "magnitude"
    fn: Callable[[pd.DataFrame], list[Finding]]


def validate_actions(actions: list[dict]) -> list[dict]:
    """Return `actions` unchanged if every one is a known type with its fields;
    raise ValueError naming the first problem otherwise."""
    for a in actions:
        t = a.get("type")
        if t not in ACTION_TYPES:
            raise ValueError(f"unknown action type {t!r}")
        for f in ACTION_TYPES[t]:
            if f not in a:
                raise ValueError(f"{t} is missing field {f!r}")
        if "tone" in ACTION_TYPES[t] and a["tone"] not in TONES:
            raise ValueError(f"{t} has unknown tone {a['tone']!r}")
    return actions


def t_of(df: pd.DataFrame, i: int) -> int:
    """Unix seconds of bar `i` — the `time` value the chart plots bars at."""
    ts = pd.Timestamp(df.index[i])
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return int(ts.timestamp())


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def _px(x: float) -> str:
    return f"{x:,.2f}"


def rvol(df: pd.DataFrame, i: int = -1, n: int = 20) -> float | None:
    """Bar volume over the mean of the `n` bars before it; None when volume is
    missing or zero (index-like symbols), so no volume clause is ever invented."""
    i = i % len(df)
    if i < n:
        return None
    v = df["volume"].to_numpy(float)
    prior = v[i - n:i]
    if not np.isfinite(v[i]) or not np.all(np.isfinite(prior)) or prior.mean() <= 0 or v[i] <= 0:
        return None
    return float(v[i] / prior.mean())


def now_step(df: pd.DataFrame) -> dict:
    """Where the stock sits now: 63-bar range, trend word, relative volume."""
    last = df.iloc[-1]
    win = df.iloc[-63:]
    hi, lo = float(win["high"].max()), float(win["low"].min())
    close = float(last["close"])
    sma = df["close"].rolling(20).mean()
    slope = sma.iloc[-1] - sma.iloc[-6] if len(sma) >= 26 else np.nan
    if close > sma.iloc[-1] and slope > 0:
        trend = "Uptrend"
    elif close < sma.iloc[-1] and slope < 0:
        trend = "Downtrend"
    else:
        trend = "Sideways"
    rv = rvol(df)
    parts = [f"{_px(close)} · 3-month range {_px(lo)}–{_px(hi)}, "
             f"{_pct(close / hi - 1)} from the top and {_pct(close / lo - 1)} from the bottom.",
             f"{trend} (price against its 20-day average and that average's slope)."]
    if rv is not None:
        parts.append(f"Volume {rv:.1f}× its 20-day average.")
    return {
        "id": "now", "title": "Now", "body": " ".join(parts),
        "facts": {"close": close, "lo63": lo, "hi63": hi,
                  "pct_from_hi": close / hi - 1, "pct_from_lo": close / lo - 1,
                  "trend": trend, "rvol": rv},
        "actions": validate_actions([
            {"type": "CLEAR"},
            {"type": "ZOOM_TO_RANGE", "from": t_of(df, -min(63, len(df))), "to": t_of(df, -1)},
            {"type": "PRICE_LEVEL", "price": hi, "label": "3-month high", "tone": "down"},
            {"type": "PRICE_LEVEL", "price": lo, "label": "3-month low", "tone": "up"},
            {"type": "HIGHLIGHT_CANDLE", "time": t_of(df, -1), "tone": "accent"},
        ]),
    }


#: Registry filled in by the detector sections below.
DETECTORS: dict[str, Detector] = {}


def _register(key, label, family, kind, claim, fn):
    DETECTORS[key] = Detector(key, label, family, kind, claim, fn)


def _zoom63(df) -> dict:
    return {"type": "ZOOM_TO_RANGE", "from": t_of(df, -min(63, len(df))), "to": t_of(df, -1)}


# --------------------------------------------------------------------------- #
# Ported from eVector: 55-session closing breakout / breakdown, unfilled gaps
# --------------------------------------------------------------------------- #

BRK_LOOKBACK = 55          # prior closes the level is taken from
BRK_SCAN = 15              # how far back a cross still counts
BRK_FAIL_UP = 0.98         # a later close under 0.98 x level fails a breakout
BRK_FAIL_DN = 1.02         # a later close over 1.02 x level fails a breakdown


def _cross_55(df: pd.DataFrame, up: bool) -> list[Finding]:
    """The oldest close in the last 15 bars that crosses the prior 55-session
    closing high (low), as eVector scans it. Failed when any LATER close is back
    beyond 2% the other side of the level."""
    c = df["close"].to_numpy(float)
    n = len(c)
    for i in range(n - BRK_SCAN, n):
        if i - BRK_LOOKBACK < 0:
            continue
        prior = c[i - BRK_LOOKBACK:i]
        level = prior.max() if up else prior.min()
        crossed = (c[i] > level and c[i - 1] <= level) if up else (c[i] < level and c[i - 1] >= level)
        if not crossed:
            continue
        later = c[i + 1:]
        failed = bool((later < BRK_FAIL_UP * level).any()) if up else bool((later > BRK_FAIL_DN * level).any())
        rv = rvol(df, i)
        weight = 0.7 + (i - (n - BRK_SCAN)) / 50 + (min(0.2, (rv - 1) / 5) if rv is not None else 0.0)
        vol_txt = f" on {rv:.1f}× usual volume" if rv is not None else ""
        ago = n - 1 - i
        when = "today" if ago == 0 else f"{ago} session{'s' if ago > 1 else ''} ago"
        if up:
            key = "failed_breakout55" if failed else "breakout55"
            tone = "down" if failed else "up"
            title = ("A breakout over its 55-day closing high failed" if failed
                     else "Broke out over its 55-day closing high")
            body = (f"Closed above {_px(level)}{vol_txt} {when}"
                    + (", then closed back more than 2% below it." if failed else "."))
            watch = ({"text": f"A close back above {_px(level)} reclaims the level", "level": float(level)}
                     if failed else
                     {"text": f"A close under {_px(BRK_FAIL_UP * level)} (−2%) turns it into a failed breakout",
                      "level": round(float(BRK_FAIL_UP * level), 2)})
        else:
            key = "failed_breakdown55" if failed else "breakdown55"
            tone = "up" if failed else "down"
            title = ("A breakdown under its 55-day closing low failed" if failed
                     else "Broke down under its 55-day closing low")
            body = (f"Closed below {_px(level)}{vol_txt} {when}"
                    + (", then closed back more than 2% above it." if failed else "."))
            watch = ({"text": f"A close back below {_px(level)} loses the level again", "level": float(level)}
                     if failed else
                     {"text": f"A close over {_px(BRK_FAIL_DN * level)} (+2%) turns it into a failed breakdown",
                      "level": round(float(BRK_FAIL_DN * level), 2)})
        t = t_of(df, i)
        return [Finding(
            id=f"{key}:{t}", detector=key, title=title, body=body,
            facts={"level": float(level), "rvol": rv, "sessions": BRK_LOOKBACK, "bars_ago": ago},
            time=t, weight=weight, tone=tone, watch=watch,
            actions=validate_actions([
                {"type": "CLEAR"}, _zoom63(df),
                {"type": "PRICE_LEVEL", "price": float(level),
                 "label": f"55-day closing {'high' if up else 'low'}", "tone": "up" if up else "down"},
                {"type": "HIGHLIGHT_CANDLE", "time": t, "tone": "accent"},
            ]))]
    return []


def det_breakout55(df: pd.DataFrame) -> list[Finding]:
    return _cross_55(df, up=True)


def det_breakdown55(df: pd.DataFrame) -> list[Finding]:
    return _cross_55(df, up=False)


GAP_MIN = 0.03
GAP_SCAN = 10


def det_gaps(df: pd.DataFrame) -> list[Finding]:
    """The newest open gap of at least 3% in the last 10 bars that price has not
    traded back to (a gap up is filled when any later-or-same bar's low reaches
    the prior close; a gap down when a high does)."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(c)
    for i in range(n - 1, max(0, n - 1 - GAP_SCAN), -1):
        prev = c[i - 1]
        if not prev or not np.isfinite(prev):
            continue
        r = o[i] / prev - 1
        if abs(r) < GAP_MIN:
            continue
        filled = bool((l[i:] <= prev).any()) if r > 0 else bool((h[i:] >= prev).any())
        if filled:
            continue
        up = r > 0
        key = "gap_up" if up else "gap_down"
        t = t_of(df, i)
        ago = n - 1 - i
        return [Finding(
            id=f"{key}:{t}", detector=key,
            title=f"An unfilled gap {'up' if up else 'down'} of {_pct(r)}",
            body=f"Opened {_pct(r)} {'above' if up else 'below'} the prior close {_px(prev)} "
                 f"{ago} session{'s' if ago != 1 else ''} ago and has not traded back to it.",
            facts={"gap": float(r), "level": float(prev), "bars_ago": ago},
            time=t, weight=0.6 + min(0.2, abs(r)), tone="up" if up else "down",
            watch={"text": f"A trade back to {_px(prev)} fills the gap", "level": float(prev)},
            actions=validate_actions([
                {"type": "CLEAR"}, _zoom63(df),
                {"type": "PRICE_LEVEL", "price": float(prev), "label": "gap fill", "tone": "neutral"},
                {"type": "HIGHLIGHT_CANDLE", "time": t, "tone": "accent"},
            ]))]
    return []


_register("breakout55", "55-day closing-high breakout", "evector", "dated", "directional", det_breakout55)
_register("failed_breakout55", "Failed 55-day breakout", "evector", "dated", "directional", det_breakout55)
_register("breakdown55", "55-day closing-low breakdown", "evector", "dated", "directional", det_breakdown55)
_register("failed_breakdown55", "Failed 55-day breakdown", "evector", "dated", "directional", det_breakdown55)
_register("gap_up", "Unfilled gap up (≥3%)", "evector", "dated", "directional", det_gaps)
_register("gap_down", "Unfilled gap down (≥3%)", "evector", "dated", "directional", det_gaps)


# --------------------------------------------------------------------------- #
# Ported from eVector: volume / ATR expansion, squeeze, divergence; trend lines
# --------------------------------------------------------------------------- #

def _rsi(close: pd.Series) -> pd.Series:
    """RSI14: the desk's own Wilder RSI, so a divergence here is the same RSI
    the chart's `rsi` indicator draws. A module-level hook so tests can pin it."""
    import scanner_templates as sc
    return sc._rsi_series(close, 14)


def wilder_atr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    """ATR as eVector computes it: first TR is high-low, seed = mean of TR[1..n],
    then Wilder smoothing. NaN before the seed."""
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    tr = np.empty(len(c))
    tr[0] = h[0] - l[0]
    tr[1:] = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    s = tr[1:n + 1].mean()
    out[n] = s
    for i in range(n + 1, len(c)):
        s = (s * (n - 1) + tr[i]) / n
        out[i] = s
    return out


def det_volume_expansion(df: pd.DataFrame) -> list[Finding]:
    v = df["volume"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = len(v)
    if n < 56:
        return []
    last, prior = v[n - 5:], v[n - 55:n - 5]
    if not (np.all(np.isfinite(last)) and np.all(np.isfinite(prior))) or prior.mean() <= 0:
        return []
    x = last.mean() / prior.mean()
    if x < 1.5:
        return []
    up = c[-1] >= c[-6]
    return [Finding(
        id="volume_expansion:state", detector="volume_expansion",
        title="Volume is expanding",
        body=f"The last five sessions traded {x:.1f}x the 50 before, while price "
             f"{'rose' if up else 'fell'} {_pct(c[-1] / c[-6] - 1)}.",
        facts={"ratio": float(x)}, time=None, weight=min(0.85, 0.4 + (x - 1.5) / 3),
        tone="up" if up else "down", watch=None,
        actions=validate_actions([
            {"type": "CLEAR"}, _zoom63(df),
            {"type": "INDICATORS", "ids": ["volume"]},
            {"type": "HIGHLIGHT_RANGE", "from": t_of(df, -5), "to": t_of(df, -1), "tone": "accent"},
        ]))]


def det_atr_expansion(df: pd.DataFrame) -> list[Finding]:
    a = wilder_atr(df)
    n = len(a)
    if n < 43 or not np.isfinite(a[-1]) or not np.isfinite(a[-43]) or a[-43] <= 0:
        return []
    x = a[-1] / a[-43]
    if x < 1.4:
        return []
    close = float(df["close"].iloc[-1])
    return [Finding(
        id="atr_expansion:state", detector="atr_expansion",
        title="Volatility is expanding",
        body=f"The daily range (ATR14 {a[-1] / close * 100:.1f}% of price) is {x:.1f}x "
             f"what it was two months ago.",
        facts={"ratio": float(x), "atr": float(a[-1])}, time=None,
        weight=min(0.8, 0.4 + (x - 1.4) / 2), tone="neutral", watch=None,
        actions=validate_actions([{"type": "CLEAR"}, _zoom63(df),
                                  {"type": "INDICATORS", "ids": ["atr"]}]))]


def det_squeeze(df: pd.DataFrame) -> list[Finding]:
    c = df["close"]
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std(ddof=0)
    width = ((mid + 2 * sd) - (mid - 2 * sd)) / mid
    hist = width.iloc[-126:].dropna()
    p = width.iloc[-1]
    if len(hist) <= 60 or not np.isfinite(p) or p > 1.05 * hist.min():
        return []
    upper, lower = float(mid.iloc[-1] + 2 * sd.iloc[-1]), float(mid.iloc[-1] - 2 * sd.iloc[-1])
    return [Finding(
        id="squeeze:state", detector="squeeze",
        title="A squeeze: the Bollinger Bands are the narrowest in six months",
        body=f"Band width {p * 100:.1f}% of price, within 5% of its 126-session minimum.",
        facts={"width": float(p), "upper": upper, "lower": lower}, time=None, weight=0.65,
        tone="neutral",
        watch={"text": f"Whichever breaks first: the upper band {_px(upper)} or the lower band {_px(lower)}",
               "level": None},
        actions=validate_actions([{"type": "CLEAR"}, _zoom63(df),
                                  {"type": "INDICATORS", "ids": ["bollinger"]}]))]


def _swings(df: pd.DataFrame, highs: bool) -> list[int]:
    """The last two 5-bar fractal swings (a bar at least as extreme as the two
    either side) in bars n-40 .. n-3, as eVector scans them."""
    x = df["high" if highs else "low"].to_numpy(float)
    n = len(x)
    out = []
    for s in range(max(2, n - 40), n - 2):
        nb = [x[s + k] for k in (-2, -1, 1, 2)]
        ok = all(x[s] >= v for v in nb) if highs else all(x[s] <= v for v in nb)
        if ok:
            out.append(s)
    return out[-2:]


def det_divergence(df: pd.DataFrame) -> list[Finding]:
    r = _rsi(df["close"]).to_numpy(float)
    found = []
    for highs in (True, False):
        sw = _swings(df, highs)
        if len(sw) != 2 or not np.isfinite(r[sw[0]]) or not np.isfinite(r[sw[1]]):
            continue
        a, b = sw
        col = "high" if highs else "low"
        pa, pb = float(df[col].iloc[a]), float(df[col].iloc[b])
        if highs and not (pb > pa and r[b] < r[a] - 4):
            continue
        if not highs and not (pb < pa and r[b] > r[a] + 4):
            continue
        key = "bearish_div" if highs else "bullish_div"
        tone = "down" if highs else "up"
        t0, t1 = t_of(df, a), t_of(df, b)
        found.append(Finding(
            id=f"{key}:{t1}", detector=key,
            title="Bearish divergence" if highs else "Bullish divergence",
            body=(f"Price made a {'higher high' if highs else 'lower low'} ({_px(pa)} -> {_px(pb)}) "
                  f"while RSI14 made a {'lower' if highs else 'higher'} one ({r[a]:.0f} -> {r[b]:.0f})."),
            facts={"p1": pa, "p2": pb, "r1": float(r[a]), "r2": float(r[b])},
            time=t1, weight=0.7, tone=tone,
            watch={"text": f"A {'close above' if highs else 'close below'} the swing {col} {_px(pb)} "
                           f"overrides the divergence", "level": pb},
            actions=validate_actions([
                {"type": "CLEAR"},
                {"type": "ZOOM_TO_RANGE", "from": t_of(df, max(0, a - 10)), "to": t_of(df, -1)},
                {"type": "INDICATORS", "ids": ["ema20", "rsi"]},
                {"type": "HIGHLIGHT_CANDLE", "time": t0, "tone": tone},
                {"type": "HIGHLIGHT_CANDLE", "time": t1, "tone": tone},
            ])))
    return found


CROSS_RECENT = 20


def _run_start(flags: np.ndarray) -> int | None:
    """Index where the run of True ending at the last bar began (None if the last
    bar is False)."""
    if not flags[-1]:
        return None
    i = len(flags) - 1
    while i > 0 and flags[i - 1]:
        i -= 1
    return i


def det_sma200(df: pd.DataFrame) -> list[Finding]:
    c = df["close"].to_numpy(float)
    sma = df["close"].rolling(200).mean().to_numpy(float)
    if len(c) < 200 or not np.isfinite(sma[-1]):
        return []
    above = c[-1] > sma[-1]
    side = (c > sma) if above else (c < sma)
    start = _run_start(np.where(np.isfinite(sma), side, False))
    if start is None:
        return []
    ago = len(c) - 1 - start
    recent = ago < CROSS_RECENT
    key = "above_sma200" if above else "below_sma200"
    t = t_of(df, start) if recent else None
    lvl = float(sma[-1])
    dist = c[-1] / lvl - 1
    return [Finding(
        id=f"{key}:{t or 'state'}", detector=key,
        title=f"{'Above' if above else 'Below'} its 200-day average",
        body=(f"{_pct(dist)} {'above' if above else 'below'} the 200-day average ({_px(lvl)})"
              + (f"; crossed {ago} sessions ago." if recent else ".")
              + (" The long trend is up." if above else " The long trend is down.")),
        facts={"sma200": lvl, "dist": float(dist)}, time=t, weight=0.6,
        tone="up" if above else "down",
        watch={"text": f"A close {'under' if above else 'over'} the 200-day average {_px(lvl)}", "level": lvl},
        actions=validate_actions(
            [{"type": "CLEAR"}, _zoom63(df), {"type": "INDICATORS", "ids": ["sma200"]}]
            + ([{"type": "HIGHLIGHT_CANDLE", "time": t, "tone": "accent"}] if t else [])))]


def det_crosses(df: pd.DataFrame) -> list[Finding]:
    s50 = df["close"].rolling(50).mean().to_numpy(float)
    s200 = df["close"].rolling(200).mean().to_numpy(float)
    n = len(s50)
    for i in range(n - 1, max(0, n - CROSS_RECENT) - 1, -1):
        if i < 1 or not np.isfinite(s200[i - 1]):
            break
        gold = s50[i] > s200[i] and s50[i - 1] <= s200[i - 1]
        death = s50[i] < s200[i] and s50[i - 1] >= s200[i - 1]
        if not (gold or death):
            continue
        key = "golden_cross" if gold else "death_cross"
        t = t_of(df, i)
        return [Finding(
            id=f"{key}:{t}", detector=key,
            title=("Trend turned up: the 50-day average crossed above the 200-day" if gold
                   else "Trend turned down: the 50-day average crossed below the 200-day"),
            body=f"{n - 1 - i} sessions ago; 50-day {_px(s50[-1])}, 200-day {_px(s200[-1])}.",
            facts={"sma50": float(s50[-1]), "sma200": float(s200[-1])}, time=t, weight=0.6,
            tone="up" if gold else "down",
            watch={"text": f"The 50-day crossing back {'under' if gold else 'over'} the 200-day "
                           f"({_px(s200[-1])})", "level": float(s200[-1])},
            actions=validate_actions([
                {"type": "CLEAR"}, _zoom63(df), {"type": "INDICATORS", "ids": ["sma50", "sma200"]},
                {"type": "HIGHLIGHT_CANDLE", "time": t, "tone": "accent"}]))]
    return []


_register("volume_expansion", "Volume expansion (5 vs 50 sessions, at least 1.5x)", "evector", "state",
          "directional", det_volume_expansion)
_register("atr_expansion", "Volatility expansion (ATR14 at least 1.4x two months ago)", "evector", "state",
          "magnitude", det_atr_expansion)
_register("squeeze", "Bollinger squeeze (narrowest in 126 sessions)", "evector", "state", "magnitude",
          det_squeeze)
_register("bearish_div", "Bearish RSI divergence", "evector", "dated", "directional", det_divergence)
_register("bullish_div", "Bullish RSI divergence", "evector", "dated", "directional", det_divergence)
_register("above_sma200", "Above the 200-day average", "evector", "state", "directional", det_sma200)
_register("below_sma200", "Below the 200-day average", "evector", "state", "directional", det_sma200)
_register("golden_cross", "Golden cross (50/200)", "evector", "dated", "directional", det_crosses)
_register("death_cross", "Death cross (50/200)", "evector", "dated", "directional", det_crosses)
