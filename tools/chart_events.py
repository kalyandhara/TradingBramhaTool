"""B-188 — event markers for the chart.

Four kinds, one row shape ``{date, kind, label, status_key, note}``:

  E  results date            earnings_calendar.fetch_earnings (cached)
  N  material NSE filing     nse_announcements.fetch_announcements, kept only
                             when it matches volume_anomaly.MATERIAL_SUBJECTS
  M  Budget / RBI MPC day    data/events/policy_events.csv
  A  price/volume anomaly    (drawn as ⚡) volume >= 3x its prior 50-day mean
                             AND |return| >= 2 sigma of the prior 50 returns

Every marker carries what the desk actually knows about its kind (STATUS).
Only Budget and MPC days are measured (B-184); everything else is labelled a
hypothesis. The anomaly thresholds are conventions, not measured cut-offs.
Idea from the eVector review ([[sources/Web-eVector-Event-Vector-Markets]]).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

POLICY_CSV = Path(__file__).resolve().parent.parent / "data" / "events" / "policy_events.csv"

ANOMALY_LOOKBACK = 50
ANOMALY_VOL_MULT = 3.0
ANOMALY_SIGMA = 2.0
LABEL_MAX = 60

#: Routine filings whose subject happens to contain a material word.
CHART_SKIP_SUBJECTS = (
    "loss of share certificate", "duplicate share certificate", "updates",
    "esop", "esps", "news verification", "takeover regulations",
    "analysts/institutional", "investor meet",
)

# Changes only when a study is filed in named_studies (claims_lint keeps it honest).
STATUS = {
    "M:budget": "measured (B-184): sectors re-sort on Budget days, dispersion 1.65x "
                "a normal day. Direction not measured.",
    "M:mpc":    "measured (B-184): RBI MPC days are ordinary days.",
    "E":        "hypothesis: results-day reaction not measured on this desk.",
    "N":        "hypothesis: filing impact not measured on this desk.",
    "A":        "hypothesis: anomaly rule is a convention (3x volume, 2 sigma), not measured.",
}


def status_for(key: str) -> str:
    return STATUS.get(key) or STATUS.get(key.split(":")[0], "hypothesis: not measured.")


def _row(date: str, kind: str, label: str, key: str | None = None, note: str = "") -> dict:
    return {"date": date, "kind": kind, "label": label[:LABEL_MAX],
            "status_key": key or kind, "note": note}


# ── sources → rows ────────────────────────────────────────────────────────────
def earnings_rows(payload: dict | None) -> list[dict]:
    out = []
    for e in (payload or {}).get("events") or []:
        s = e.get("surprise_pct")
        label = "Results" + (f" · surprise {s:+.1f} %" if s is not None else "")
        out.append(_row(e["date"], "E", label))
    return out


def announcement_rows(items: list[dict]) -> list[dict]:
    from nse_announcements import _parse_dt
    from volume_anomaly import MATERIAL_SUBJECTS, REACTIVE_SUBJECTS
    out = []
    for a in items or []:
        subj = (a.get("subject") or "").strip()
        low = subj.lower()
        # Subject only, unlike volume_anomaly: that module over-matches on
        # purpose (a missed filing is the costly error there), but on a chart
        # every false match is a marker. RELIANCE over 10 years drew 936.
        if any(r in low for r in REACTIVE_SUBJECTS + CHART_SKIP_SUBJECTS):
            continue
        if not any(m in low for m in MATERIAL_SUBJECTS):
            continue
        dt = _parse_dt(a.get("date"))
        if dt is not None:
            out.append(_row(dt.date().isoformat(), "N", subj))
    return out


def policy_rows(events: pd.DataFrame) -> list[dict]:
    out = []
    for _, r in events.iterrows():
        et = str(r["event_type"]).lower()
        label = (f"Budget ({r['label']})" if et == "budget"
                 else f"RBI MPC {r['label']}" if et == "mpc" else et)
        out.append(_row(str(pd.Timestamp(r["date"]).date()), "M", label, f"M:{et}"))
    return out


def anomaly_rows(df: pd.DataFrame) -> list[dict]:
    if df is None or len(df) <= ANOMALY_LOOKBACK + 1:
        return []
    close = df["close"].astype(float)
    vol = df["volume"].astype(float)
    ret = close.pct_change()
    vol_base = vol.shift(1).rolling(ANOMALY_LOOKBACK).mean()
    sig = ret.shift(1).rolling(ANOMALY_LOOKBACK).std()
    hit = (vol >= ANOMALY_VOL_MULT * vol_base) & (ret.abs() >= ANOMALY_SIGMA * sig)
    out = []
    for ts in df.index[hit.fillna(False).to_numpy()]:
        out.append(_row(str(ts.date()), "A",
                        f"Volume {vol[ts] / vol_base[ts]:.1f}x · move {ret[ts] * 100:+.1f} %"))
    return out


# ── merge / moves ─────────────────────────────────────────────────────────────
def merge(rows: list[dict]) -> list[dict]:
    """One marker per kind per day; extra rows become '+n more'. A filing on a
    results day folds into the E marker's note rather than stacking."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r["date"], r["kind"]), []).append(r)
    out = []
    for (date, kind), g in groups.items():
        if kind == "N" and (date, "E") in groups:
            continue
        head = {"note": "", **g[0]}
        if len(g) > 1:
            head["label"] = f"{head['label']} (+{len(g) - 1} more)"
            head["note"] = "; ".join(x["label"] for x in g[1:])
        if kind == "E" and (date, "N") in groups:
            filed = "; ".join(x["label"] for x in groups[(date, "N")])
            head["note"] = (head["note"] + "; " if head["note"] else "") + f"Filed: {filed}"
        out.append(head)
    return sorted(out, key=lambda r: (r["date"], r["kind"]))


def with_moves(rows: list[dict], df: pd.DataFrame) -> list[dict]:
    """Snap each event to the first session on/after its date; add the event-day
    move (r1) and the move through 5 sessions later (r5), both from the prior close."""
    close = df["close"].astype(float)
    idx = df.index
    out = []
    for r in rows:
        pos = int(idx.searchsorted(pd.Timestamp(r["date"])))
        if pos >= len(idx) or pos == 0:
            continue
        base = close.iloc[pos - 1]
        r = dict(r, session=str(idx[pos].date()),
                 r1=float((close.iloc[pos] / base - 1) * 100),
                 r5=(float((close.iloc[pos + 5] / base - 1) * 100)
                     if pos + 5 < len(idx) else None))
        out.append(r)
    return out


def _load_policy() -> pd.DataFrame:
    return pd.read_csv(POLICY_CSV)


def collect(symbol: str, df: pd.DataFrame, *,
            earnings_fn: Callable | None = None, ann_fn: Callable | None = None,
            policy_fn: Callable | None = None) -> dict:
    """All markers inside the bars' date range. A failing source is reported in
    `missing` and the others still draw."""
    if earnings_fn is None:
        from earnings_calendar import fetch_earnings as earnings_fn
    if ann_fn is None:
        from nse_announcements import fetch_announcements as ann_fn
    policy_fn = policy_fn or _load_policy

    rows, missing = [], []
    for kind, fn in (("E", lambda: earnings_rows(earnings_fn(symbol))),
                     ("N", lambda: announcement_rows(ann_fn(symbol))),
                     ("M", lambda: policy_rows(policy_fn())),
                     ("A", lambda: anomaly_rows(df))):
        try:
            rows += fn()
        except Exception:
            missing.append(kind)
    lo, hi = str(df.index[0].date()), str(df.index[-1].date())
    rows = [r for r in rows if lo < r["date"] <= hi]
    events = with_moves(merge(rows), df)
    for e in events:
        e["status"] = status_for(e.pop("status_key"))
    return {"symbol": symbol, "events": events, "missing": missing}
