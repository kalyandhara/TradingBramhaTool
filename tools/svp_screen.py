#!/usr/bin/env python3
"""svp_screen.py — read the SVP screen file for the desk's tables.

The session-volume-profile screen is produced by a JS pipeline
(`svp_universe_export.py` → `svp_screen_runner.js` → `cache/svp_screen.csv`)
because `session_volume_profile.js` is the reference implementation of the
profile math. This module is the READ side: it lets the Python tables show two
columns off that file without reimplementing anything.

── What is safe to surface, and what is not ───────────────────────────────────
The SVP **composite score and its BUY/SELL direction were measured on
2026-08-29 as a clean negative** — corr(score, 20d fwd) = −0.041, deciles
non-monotonic, BUY-high confidence performing WORSE than BUY-low, 5 of 7 factor
families sign-inverted. The SVP page says so in its own opening callout and
deliberately does not display them.

So this module exposes **structure only**:

  * `shape_seq` — the weekly session shapes, which are a description of what the
    profile looked like, not a prediction;
  * `n_factors` — HOW MANY named factors fired, not which way they point.

`sig_dir`, `sig_conf`, `agreement`, `bull_w` and `bear_w` are deliberately NOT
read here. Adding them would put the measured-negative composite back onto the
desk's main tables, reversing a recorded decision.

── Shapes (Manish's D/P/B/I, standard market-profile vocabulary) ──────────────
    P  POC high in the range   buying / short-covering
    B  POC low in the range    selling / liquidation
    D  neither                 directional
    I  value area ≥78% of range  balance → sideways

`shape_seq` is written OLDEST → NEWEST by the runner
(`res.sessions.map(s => s.shape)`), so the last character is the most recent
session and `history()` preserves that order.

── Staleness is the main hazard ───────────────────────────────────────────────
This file is written by a manual two-command pipeline, not a scheduled job. A
row describes the structure as of ITS OWN last bar (`asof`), which can be days
older than today. `load()` therefore returns the file's age and every caller is
expected to show it — a three-week-old profile presented as today's structure is
the failure mode this docstring exists to prevent.

CLI:
    py -3 tools/svp_screen.py            # coverage + a sample of the columns
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

#: Where the JS runner writes. Same path the SVP page reads.
DEFAULT_PATH = Path(__file__).resolve().parent / "cache" / "svp_screen.csv"

#: How many weekly sessions the history column shows. The file carries 12; eight
#: is what the desk asked to read, and a shorter window is a cheaper glance.
HISTORY_WEEKS = 8

#: For the tooltip, so the vocabulary lives next to the data that uses it.
SHAPE_MEANING = {
    "P": "buying / short-covering",
    "B": "selling / liquidation",
    "D": "directional",
    "I": "balance → sideways",
}

#: Columns this module will read. Everything else in the file — and in
#: particular sig_dir / sig_conf / agreement / bull_w / bear_w — is left where
#: it is on purpose; see the module docstring.
SAFE_COLUMNS = ("symbol", "asof", "grain", "n_sessions", "shape_seq",
                "last_shape", "va_state", "n_factors")


def history(shape_seq: Optional[str], weeks: int = HISTORY_WEEKS) -> Optional[str]:
    """The last `weeks` session shapes, oldest → newest, spaced to be read.

    Returns None for an empty sequence rather than an empty string, so a caller
    can tell "no structure on file" from "structure that happens to be blank".
    A sequence SHORTER than `weeks` is returned in full rather than padded: the
    cell then shows what exists, and its length says how much that is.
    """
    s = "" if shape_seq is None else str(shape_seq).strip().upper()
    s = "".join(ch for ch in s if ch in SHAPE_MEANING)
    if not s:
        return None
    return " ".join(s[-weeks:])


def load(path: Path | str | None = None) -> dict[str, Any]:
    """`{"rows": {symbol: {...}}, "age_hours": float, "path": str, "n": int}`.

    Missing file returns an empty `rows` and `age_hours=None` — the caller shows
    nothing rather than a column of blanks that looks like every name lacks
    structure.
    """
    import pandas as pd

    p = Path(path) if path is not None else DEFAULT_PATH
    out: dict[str, Any] = {"rows": {}, "age_hours": None, "path": str(p), "n": 0,
                           "asof_min": None, "asof_max": None, "asof_spread": 0}
    if not p.exists():
        return out
    try:
        df = pd.read_csv(p)
    except Exception:
        return out

    keep = [c for c in SAFE_COLUMNS if c in df.columns]
    if "symbol" not in keep:
        return out
    rows: dict[str, dict[str, Any]] = {}
    for rec in df[keep].to_dict("records"):
        sym = str(rec.get("symbol") or "").strip().upper()
        if not sym:
            continue
        rec["svp_hist_8w"] = history(rec.get("shape_seq"))
        rows[sym] = rec
    out["rows"] = rows
    out["n"] = len(rows)
    # The file's mtime says when the CSV was WRITTEN; `asof` says which bar each
    # row describes, and those diverge the moment the screen is extended with
    # freshly-downloaded names on top of older ones. The as-of RANGE is the
    # honest staleness measure, so it is computed here rather than left to each
    # caller to rediscover.
    asofs = sorted({str(r.get("asof")) for r in rows.values()
                    if r.get("asof") and str(r.get("asof")) != "nan"})
    out["asof_min"] = asofs[0] if asofs else None
    out["asof_max"] = asofs[-1] if asofs else None
    out["asof_spread"] = len(asofs)
    try:
        out["age_hours"] = round(
            (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime))
            .total_seconds() / 3600.0, 1)
    except OSError:                                          # pragma: no cover
        pass
    return out


def cells(symbol: str, screen: dict[str, Any]) -> dict[str, Any]:
    """The two table cells for one symbol: `svp_hist_8w` and `svp_factors`.

    Both are empty/None for a symbol absent from the file — the screen covers
    one index, and a name outside it has no structure on file, which is not the
    same as having flat structure.
    """
    r = (screen or {}).get("rows", {}).get(str(symbol).strip().upper())
    if not r:
        return {"svp_hist_8w": "", "svp_factors": None}
    n = r.get("n_factors")
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = None
    return {"svp_hist_8w": r.get("svp_hist_8w") or "", "svp_factors": n}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    s = load()
    if not s["n"]:
        print(f"no screen file at {s['path']}\n")
        print("Build one with:")
        print("  py -3 tools/svp_universe_export.py --index nifty500")
        print("  node tools/svp_screen_runner.js --dir tools/cache/svp_bars "
              "--out tools/cache/svp_screen.csv")
        return 1
    print(f"{s['n']} symbols · file written {s['age_hours']}h ago · "
          f"history window {HISTORY_WEEKS} weeks\n")
    print(f"{'symbol':14} {'history (oldest → newest)':26} {'factors':>7}  asof")
    for sym, r in list(s["rows"].items())[:15]:
        c = cells(sym, s)
        print(f"{sym:14} {c['svp_hist_8w']:26} {str(c['svp_factors']):>7}  "
              f"{r.get('asof', '')}")
    print("\nShapes: " + " · ".join(f"{k} {v}" for k, v in SHAPE_MEANING.items()))
    print("Structure only. The SVP composite score and its direction measured a "
          "clean negative on 2026-08-29 and are deliberately not read here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
