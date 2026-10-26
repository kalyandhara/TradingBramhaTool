"""event_study.py — did NIFTY and the NSE sector indices move abnormally on
policy event days, compared with ordinary days?

Spec: docs/superpowers/specs/2026-10-26-policy-event-study-design.md

A measuring instrument, not a signal: every study run through it is
pre-registered on the wiki first, and a null result is calibration. The library
does no file or network I/O of its own except through the loaders, which take
injectable callables so the tests never touch the network.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

#: Allowed labels per event type. A label outside these is an error, not a
#: silently new bucket — a typo would otherwise become its own tiny sample.
EVENT_LABELS: dict[str, set[str]] = {
    "mpc": {"cut", "hike", "hold"},
    "budget": {"full", "interim"},
}

EVENT_COLUMNS = ["date", "event_type", "label", "scheduled", "time_ist",
                 "source_url", "notes"]


# --------------------------------------------------------------------------- #
# Events
# --------------------------------------------------------------------------- #

def load_events(path, types: list[str] | None = None,
                scheduled_only: bool = True) -> pd.DataFrame:
    """Read and validate the events CSV; validation runs on the whole file, so a
    bad row is caught even when it would have been filtered out."""
    df = pd.read_csv(Path(path), dtype=str, keep_default_na=False)
    missing = [c for c in EVENT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"events file missing columns: {missing}")
    df = df[EVENT_COLUMNS].copy()
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df["scheduled"] = df["scheduled"].astype(int)

    for _, r in df.iterrows():
        allowed = EVENT_LABELS.get(r["event_type"])
        if allowed is None:
            raise ValueError(f"unknown event_type {r['event_type']!r} on {r['date'].date()}")
        if r["label"] not in allowed:
            raise ValueError(f"unknown label {r['label']!r} for {r['event_type']} "
                             f"on {r['date'].date()}")
    dup = df.duplicated(["date", "event_type"], keep=False)
    if dup.any():
        raise ValueError("duplicate (date, event_type): "
                         + ", ".join(str(d.date()) for d in df.loc[dup, "date"].unique()))

    if types is not None:
        df = df[df["event_type"].isin(types)]
    if scheduled_only:
        df = df[df["scheduled"] == 1]
    return df.sort_values("date").reset_index(drop=True)
