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
