#!/usr/bin/env python3
"""scanner_plans.py — which scanners actually hand you a trade plan? (PR-2)

Roadmap rung PR-2 from `analyses/Pattern-Reporting-Enhancement-Roadmap`.

── Why this is a measurement capability, not a display nicety ─────────────────
`backtest._simulate_plan` walks **entry -> stop/target** bar by bar. A scanner
that emits no plan therefore **cannot be scored on realised R at all** — only on
raw forward return, which says nothing about whether the trade the scanner
implies was survivable. So plan coverage decides what the harness can even ask.

Censused 2026-09-17 over 45 nifty500 names, every 25th bar, point-in-time:
**47 of 48 registered scanners fired, and 16 of them carry a full
`entry`/`stop`/`target`. Thirty-one do not.** That number is why this rung
outranked building a 47th pattern — and when PR-3 did build one, it arrived with
a plan and the floor rose behind it (14 → 16).

**PARTIAL came back empty, and that is a finding.** Every scanner either always
emits a plan or never does — a plan is a property of the SCANNER, not of the
individual hit. So this is 31 scanners to fix, not 31 scattered gaps, and fixing
one fixes every hit it will ever produce.

── Three states, and the third is the point ──────────────────────────────────
A scanner that never fired in the sample has **not** been shown to lack a plan.
Collapsing that into "no plan" is the FR-4 mistake — NOT_CHECKED reading as a
pass, or here as a fail. So:

    FULL      every observed hit carried entry, stop AND target
    PARTIAL   some hits carried a full plan and some did not
    NONE      it fired, and no hit ever carried a full plan
    UNSEEN    it never fired in this sample — nothing is claimed
    BILATERAL it publishes both legs and no single plan, ON PURPOSE (B-101)

**PARTIAL is worth its own state.** A plan you get on some hits and not others is
harder to use than one you never get, because the reader cannot tell which kind
of row they are looking at without checking every cell.

── Point-in-time, like everything else here ──────────────────────────────────
Each scanner is handed `df.iloc[:t+1]`, never the whole frame, so a scanner that
peeks cannot be rewarded for it. Results are cached to disk because a wide probe
is minutes of fetching and the answer changes only when a scanner does.

CLI:
    py -3 -X utf8 tools/scanner_plans.py --probe --symbols 150   # measure + cache
    py -3 -X utf8 tools/scanner_plans.py                         # print the cache
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

HERE = Path(__file__).resolve().parent

#: The census is a RECORD, not a cache, so it lives beside the code and is
#: committed. `tools/cache/` is gitignored, and a census kept there would leave
#: the ratchet below silently SKIPPING on any fresh checkout -- a ratchet that
#: skips is decoration, which is the B-87 lesson about ceilings set far above
#: reality. Committed, it is also diffable: a scanner losing its plan shows up as
#: a line in a review rather than as a number nobody re-ran.
CACHE = HERE / "scanner_plan_coverage.json"

#: The three fields `_simulate_plan` needs. All three or it cannot run.
PLAN_FIELDS = ("entry", "stop", "target")

#: Bars of history handed to a scanner before its first evaluation. Matches the
#: shared harness so a scanner that fires here would fire there.
WARMUP = 220

FULL, PARTIAL, NONE, UNSEEN = "FULL", "PARTIAL", "NONE", "UNSEEN"

#: A fifth state, for a scanner that emits no `entry`/`stop`/`target` BY DESIGN
#: rather than by omission (B-101). A bilateral pattern — a symmetrical triangle
#: — does not know its direction, so it publishes both legs (`up_*` / `down_*`)
#: and no unqualified triple. Counting that as NONE would put it on the list of
#: things to fix, and the fix would be to pick a direction the pattern does not
#: have; the file's own argument for why UNSEEN is not NONE applies here word for
#: word. It is excluded from `observed`, so it can neither flatter nor damage the
#: coverage ratio it has no opinion about.
BILATERAL = "BILATERAL"

#: Scanner names this applies to. Read from the registry's `category` rather than
#: hard-coded, so a second bilateral scanner is covered the day it is registered.
def _bilateral_names() -> set[str]:
    try:
        import scanner_templates as sc
        return {n for n, spec in sc.SCANNERS.items()
                if spec.get("category") == "Neutral"}
    except Exception:
        return set()


def has_plan(hit: dict[str, Any] | None) -> bool:
    """True when a hit carries all three fields with usable values.

    A present-but-None `stop` is not a stop. The harness would reject it, so
    counting it here would overstate what can actually be scored.
    """
    if not isinstance(hit, dict):
        return False
    for f in PLAN_FIELDS:
        v = hit.get(f)
        if v is None:
            return False
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return False
        if fv != fv:                      # NaN
            return False
    return True


def probe(symbols: Iterable[str], fetch_fn: Callable[[str], Any],
          scanners: Optional[dict] = None, stride: int = 5,
          progress: Optional[Callable[[int, int, str], None]] = None) -> dict:
    """Run every scanner across `symbols` and record what its hits carried.

    `stride` samples evaluation bars rather than walking every one: this is a
    capability census, not an edge test, and the question "does this scanner ever
    emit a stop" does not need every bar to answer.
    """
    import scanner_templates as sc
    scanners = scanners if scanners is not None else sc.SCANNERS

    agg: dict[str, dict[str, Any]] = {
        name: {"fired": 0, "with_plan": 0, "fields": {f: 0 for f in PLAN_FIELDS}}
        for name in scanners
    }
    syms = list(symbols)
    n_used = 0
    for i, sym in enumerate(syms, 1):
        if progress:
            progress(i, len(syms), sym)
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or getattr(df, "empty", True) or len(df) < WARMUP + 20:
            continue
        n_used += 1
        last = len(df) - 2
        for t in range(WARMUP, last, max(1, stride)):
            sub = df.iloc[:t + 1]
            for name, spec in scanners.items():
                try:
                    hit = spec["fn"](sub)
                except Exception:
                    continue
                if not hit:
                    continue
                a = agg[name]
                a["fired"] += 1
                for f in PLAN_FIELDS:
                    if hit.get(f) is not None:
                        a["fields"][f] += 1
                if has_plan(hit):
                    a["with_plan"] += 1
    return {"symbols_used": n_used, "symbols_requested": len(syms),
            "stride": stride, "scanners": agg}


def classify(entry: dict[str, Any], name: str | None = None) -> str:
    """FULL / PARTIAL / NONE / UNSEEN / BILATERAL for one scanner's counts."""
    fired, with_plan = entry.get("fired", 0), entry.get("with_plan", 0)
    if name is not None and name in _bilateral_names():
        return BILATERAL if fired else UNSEEN
    if not fired:
        return UNSEEN
    if with_plan == fired:
        return FULL
    if with_plan:
        return PARTIAL
    return NONE


def summarise(result: dict) -> dict:
    """Counts per state, plus the scanner lists behind them."""
    out: dict[str, list[str]] = {FULL: [], PARTIAL: [], NONE: [], UNSEEN: [],
                                 BILATERAL: []}
    for name, e in result.get("scanners", {}).items():
        out[classify(e, name)].append(name)
    for k in out:
        out[k].sort()
    return {
        "counts": {k: len(v) for k, v in out.items()},
        "scanners": out,
        "total": sum(len(v) for v in out.values()),
        "observed": sum(len(out[k]) for k in (FULL, PARTIAL, NONE)),
    }


def rows(result: dict) -> list[dict[str, Any]]:
    """One row per scanner, ready for a table. Sorted worst-first.

    Worst-first on purpose: the useful reading of this table is "what am I NOT
    getting levels for", and burying that under the healthy rows would make the
    page a reassurance rather than a census.
    """
    order = {NONE: 0, PARTIAL: 1, UNSEEN: 2, BILATERAL: 3, FULL: 4}
    out = []
    for name, e in result.get("scanners", {}).items():
        state = classify(e, name)
        fired = e.get("fired", 0)
        out.append({
            "Scanner": name,
            "Plan": state,
            "Hits seen": fired,
            "With plan": e.get("with_plan", 0),
            "Plan %": (round(100.0 * e["with_plan"] / fired, 1) if fired else None),
            "entry": e.get("fields", {}).get("entry", 0),
            "stop": e.get("fields", {}).get("stop", 0),
            "target": e.get("fields", {}).get("target", 0),
        })
    out.sort(key=lambda r: (order[r["Plan"]], -r["Hits seen"], r["Scanner"]))
    return out


def save(result: dict, path: Path = CACHE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    return path


def load(path: Path = CACHE) -> Optional[dict]:
    """The cached census, or None. None means NOT MEASURED, never 'no plans'."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


#: How each state reads to someone deciding whether to act on a hit.
STATE_HELP = {
    FULL:    "every observed hit carried entry, stop and target",
    PARTIAL: "some hits carried a full plan and some did not — check the row",
    NONE:    "it fired, and no hit ever carried a full plan",
    BILATERAL: ("it publishes BOTH legs and no single plan, on purpose — the "
                "pattern does not know its direction (B-101)"),
    UNSEEN:  "never fired in the census — nothing is claimed either way",
}


def render(expanded: bool = False) -> None:
    """The census as a Streamlit expander. Safe to call when nothing is cached.

    Rendering lives here rather than in `dashboard_app` so the monolith gains one
    call instead of a block (the B-87 ratchet).
    """
    import streamlit as st

    res = load()
    if res is None:
        st.caption(
            "**Trade-plan coverage: not measured.** Run "
            "`py -3 -X utf8 tools/scanner_plans.py --probe` to build the census. "
            "Absent means unmeasured, not that the scanners lack plans."
        )
        return

    s = summarise(res)
    c = s["counts"]
    with st.expander(
        f"Trade-plan coverage — {c[FULL]} of {s['observed']} observed scanners "
        f"hand you entry / stop / target", expanded=expanded
    ):
        st.caption(
            "**Why this matters more than it looks.** `backtest._simulate_plan` "
            "walks entry → stop/target bar by bar, so a scanner with no plan "
            "**cannot be scored on realised R at all** — only on raw forward "
            "return, which says nothing about whether the trade was survivable. "
            "Plan coverage decides what the harness can even ask."
        )
        st.caption(
            " · ".join(f"**{k}** — {v}" for k, v in STATE_HELP.items())
        )
        import pandas as pd
        df = pd.DataFrame(rows(res))
        st.dataframe(
            df, width="stretch", hide_index=True,
            column_config={
                "Scanner":   st.column_config.TextColumn("Scanner", width="medium"),
                "Plan":      st.column_config.TextColumn("Plan", width="small"),
                "Hits seen": st.column_config.NumberColumn(
                    "Hits seen",
                    help="Hits observed in the census sample, NOT a live count."),
                "With plan": st.column_config.NumberColumn("With plan"),
                "Plan %":    st.column_config.NumberColumn("Plan %", format="%.0f%%"),
                "entry":     st.column_config.NumberColumn("entry", width="small"),
                "stop":      st.column_config.NumberColumn("stop", width="small"),
                "target":    st.column_config.NumberColumn("target", width="small"),
            },
        )
        st.caption(
            f"Census: **{res['symbols_used']} symbols**, every "
            f"{res['stride']}th bar, point-in-time. "
            f"FULL {c[FULL]} · PARTIAL {c[PARTIAL]} · NONE {c[NONE]} · "
            f"UNSEEN {c[UNSEEN]} · BILATERAL {c[BILATERAL]} of {s['total']} "
            f"registered. "
            f"**UNSEEN is not a verdict** — those scanners never fired in the "
            f"sample, so nothing is claimed about them."
        )


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(description="PR-2 · scanner trade-plan census")
    ap.add_argument("--probe", action="store_true", help="re-measure and cache")
    ap.add_argument("--symbols", type=int, default=150)
    ap.add_argument("--stride", type=int, default=5)
    a = ap.parse_args()

    if a.probe:
        import nse_universe as nu
        import screener_pipeline as sp
        syms = list(nu.symbols("nifty500"))[:a.symbols]

        def _p(i, n, sym):
            print(f"  [{i}/{n}] {sym}", end="\r", flush=True)

        res = probe(syms, lambda s: sp.fetch_ohlcv(s, days=900),
                    stride=a.stride, progress=_p)
        print()
        save(res)
        print(f"cached -> {CACHE}")
    else:
        res = load()
        if res is None:
            print("No census cached. Run with --probe.")
            return 1

    s = summarise(res)
    print(f"\n{res['symbols_used']} symbols, stride {res['stride']}\n")
    print(f"{'Scanner':<38}{'Plan':<9}{'hits':>7}{'w/plan':>8}{'%':>7}")
    for r in rows(res):
        pct = "-" if r["Plan %"] is None else f"{r['Plan %']:.0f}"
        print(f"{r['Scanner']:<38}{r['Plan']:<9}{r['Hits seen']:>7}"
              f"{r['With plan']:>8}{pct:>7}")
    c = s["counts"]
    print(f"\nFULL {c[FULL]} · PARTIAL {c[PARTIAL]} · NONE {c[NONE]} · "
          f"UNSEEN {c[UNSEEN]} · BILATERAL {c[BILATERAL]}  (of {s['total']})")
    print(f"{c[FULL]} of {s['observed']} OBSERVED scanners carry a full plan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
