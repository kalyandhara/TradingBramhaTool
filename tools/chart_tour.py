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
