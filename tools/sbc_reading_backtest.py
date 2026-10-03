#!/usr/bin/env python3
"""sbc_reading_backtest.py — does the Structure Break Chain card's READING hold up?

The card added a plain-English verdict on 2026-09-21 ("Trend change NOT confirmed
— the CHoCH failed", "Trend continuing", …) and shipped with a footer admitting
no forward-return study backed any of it. This is that study.

── PRE-REGISTERED. Thresholds fixed in this file before the first run ────────
**The claim under test is the card's own core distinction**: a break that HELD
means something different from a break that FAILED. If the words are worth
printing, the two buckets should separate.

    PRIMARY   direction-signed forward return at h = 20, HELD events vs FAILED
              events, COST_INDIAN on both. Passes only if HELD > FAILED with
              p < 0.05 AND the sign holds at 5 / 10 / 60.
    FLOOR     >= 30 events per bucket. Below that the answer is INCONCLUSIVE —
              never NULL, and never a pass. (B-101's lesson, at a smaller scale:
              its 28-signal run leaned positive on all four horizons and the
              powered re-run killed every one of them.)
    SECONDARY the three verdict TONES (good / warn / bad) in rank order, and the
              quality label (STRONG / NORMAL / WEAK). Description only when the
              primary fails — no subgroup rescues a failed primary.

── The prior is skeptical and on the record ─────────────────────────────────
B-19 measured 0 of 41 scanners stable after costs. B-56 measured this desk's
OTHER structure read (SVP) as INVERTED. Market-structure labels have not paid
here yet, and one symbol cannot change that: **a single name cannot reach the
floor**, so a single-name run is a description of that name, not a finding
about the method. That is stated before the numbers rather than after them.

── Point-in-time, like everything else here ─────────────────────────────────
`detect_structure_chain` is handed `df.iloc[:t+1]` and an event counts only when
it is confirmed ON bar t, so nothing is scored on a break the detector could not
have seen yet. Entry is the NEXT bar's open, the desk convention.

CLI:
    py -3 -X utf8 tools/sbc_reading_backtest.py --symbol BSE
    py -3 -X utf8 tools/sbc_reading_backtest.py --universe nifty500 --symbols 150
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import backtest as bt
import scanner_templates as sc

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "cache" / "sbc_reading"

HORIZONS = (5, 10, 20, 60)
PRIMARY_H = 20
WARMUP = 220
MIN_PER_BUCKET = 30          # below this: INCONCLUSIVE, never NULL

#: Mirrors `SBC_THRESH` in chart_dashboard.html. Duplicated deliberately — the
#: alternative is the study importing a constant out of an HTML file — and
#: pinned by `test_sbc_reading_backtest.py` so the two cannot drift silently.
CHAIN_CHOPPY, CHAIN_TRENDING = 2.0, 3.0


def verdict_tone(stats: dict, last: dict) -> tuple[str, str]:
    """The card's verdict and tone for one event — a port of `sbcReading`.

    Returns (tone, verdict). Kept in lockstep with the JS by test, because a
    study that scores a DIFFERENT sentence from the one the reader sees is
    measuring nothing anybody will ever act on.
    """
    avg = stats.get("avg_chain")
    env_choppy = avg is not None and avg < CHAIN_CHOPPY
    shift = last["type"] == "CHOCH"
    if last["failed"]:
        return "bad", ("Trend change NOT confirmed — the CHoCH failed" if shift
                       else "Continuation NOT confirmed — the break failed")
    if last["quality"] == "WEAK" or env_choppy:
        return "warn", ("Trend change is TENTATIVE" if shift
                        else "Break held, but weakly")
    return "good", ("Trend change confirmed so far" if shift
                    else "Trend continuing")


def _signed_fwd(df: pd.DataFrame, t: int, h: int, direction: str,
                cm) -> float | None:
    """Direction-signed forward return in %, net of a round trip.

    Signed by the EVENT's direction so a downward break that precedes a fall
    scores positive — otherwise every bearish event would read as an inverted
    bullish one, which is the mistake B-76's bias gauge made.
    """
    close = df["close"].to_numpy(float)
    openp = (df["open"].to_numpy(float) if "open" in df.columns else close)
    if t + 1 + h > len(close) - 1:
        return None
    entry = float(openp[t + 1])
    if entry <= 0:
        return None
    exit_px = float(close[t + 1 + h])
    raw = (exit_px / entry - 1.0) * 100.0
    if direction == "down":
        raw = -raw
    return raw - cm.round_trip_pct(entry, exit_px)


#: Bars to wait after a break before reading the card. NOT a tunable — it is
#: the detector's own `fail_win`, and the reason it exists here is a measurement
#: artifact the first run walked straight into:
#:
#: `failed` is decided by what price does in the bars AFTER the break, so at the
#: break bar it is ALWAYS False. Scoring events at their own bar therefore
#: produced 41 held and 0 failed on BSE — against 11 failures the card shows on
#: the same history — and the "held vs failed" comparison had nothing to compare.
#: The label is only knowable once the window closes, so that is when the card is
#: read and that is where entry goes.
FAIL_WIN = 3


def walk(df: pd.DataFrame, cm=None, stride: int = 1) -> list[dict]:
    """Every structural event in one symbol, scored as a reader could act on it.

    Two bars matter and they are different: the break is CONFIRMED at ``t``, and
    its held/failed label is SETTLED at ``t + FAIL_WIN``. The card is read at the
    second, and entry is the next bar's open after that — because a verdict that
    depends on three bars of hindsight cannot be acted on before those bars.
    """
    cm = cm or bt.COST_INDIAN
    df = df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
    out: list[dict] = []
    max_h = max(HORIZONS)
    for t in range(WARMUP, len(df) - max_h - FAIL_WIN - 2, stride):
        sub = df.iloc[:t + 1]
        try:
            d = sc.detect_structure_chain(sub)
        except Exception:
            continue
        if not d or not d.get("events"):
            continue
        last = d["events"][-1]
        # FRESH events only: the break must be confirmed on this very bar, or
        # the same event would be re-scored on every bar it stays the latest.
        if last["bar"] != len(sub) - 1:
            continue
        # Re-read the SAME event once its window has closed — this is the card
        # the reader actually sees, labels and all.
        read_at = t + FAIL_WIN
        try:
            d2 = sc.detect_structure_chain(df.iloc[:read_at + 1])
        except Exception:
            continue
        if not d2:
            continue
        ev = next((e for e in d2["events"] if e["bar"] == t), None)
        if ev is None:                      # the event did not survive re-detection
            continue
        tone, verdict = verdict_tone(d2["stats"], ev)
        row = {"t": t, "read_at": read_at, "type": ev["type"],
               "direction": ev["direction"], "quality": ev["quality"],
               "failed": bool(ev["failed"]), "tone": tone, "verdict": verdict}
        for h in HORIZONS:
            row[f"r{h}"] = _signed_fwd(df, read_at, h, ev["direction"], cm)
        out.append(row)
    return out


def stats_at(events: list[dict]) -> dict[str, Any]:
    """The card's stats as they stood after ``events`` — no look-ahead.

    Reconstructed from the event prefix rather than re-detected, which is the
    whole point of the fast walk. Only the fields the verdict reads have to be
    right, and `avg_chain` is the one that decides anything; the rest are carried
    so the row is self-describing.

    A chain COMPLETES when a CHoCH turns the structure, and its length is the
    chain counter of the event immediately before that CHoCH — the same quantity
    `detect_structure_chain` averages. Validated against the detector itself by
    `--validate`, which is the only reason to trust a reimplementation of
    somebody else's accumulator.
    """
    if not events:
        return {"avg_chain": None, "max_chain": 0, "total_bos": 0,
                "total_choch": 0, "failed_count": 0, "chain": 0, "trend": 0}
    completed = [events[i - 1]["chain"] for i in range(1, len(events))
                 if events[i]["type"] == "CHOCH"]
    last = events[-1]
    return {
        "avg_chain": round(sum(completed) / len(completed), 1) if completed else None,
        "completed_chains": len(completed),
        "max_chain": max(e["chain"] for e in events),
        "chain": last["chain"],
        "trend": 1 if last["direction"] == "up" else -1,
        "total_bos": sum(1 for e in events if e["type"] == "BOS"),
        "total_choch": sum(1 for e in events if e["type"] == "CHOCH"),
        "failed_count": sum(1 for e in events if e["failed"]),
    }


def walk_fast(df: pd.DataFrame, cm=None) -> list[dict]:
    """The same measurement as `walk`, with ONE detection pass per symbol.

    `walk` re-detects the entire chain twice on every bar, which is minutes per
    symbol and hours per universe — it is why B-114 could only ever be run on one
    name. The detector walks forward and never looks back, so the events it
    reports for bars <= T are the events a run that STOPPED at T would report;
    that is the assumption this path rests on, and `--validate` checks it against
    the slow walk rather than asserting it.

    The `failed` flag is knowable at `bar + fail_win` and not before, so it is
    taken as-of the read bar exactly as the slow walk does.
    """
    cm = cm or bt.COST_INDIAN
    df = df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
    try:
        d = sc.detect_structure_chain(df)
    except Exception:
        return []
    if not d or not d.get("events"):
        return []
    max_h = max(HORIZONS)
    out: list[dict] = []
    for k, ev in enumerate(d["events"]):
        t = ev["bar"]
        read_at = t + FAIL_WIN
        if t < WARMUP or read_at + 1 + max_h > len(df) - 1:
            continue
        # Failure inside the window is visible at the read bar; anything later
        # would be hindsight and is not used. (`detect_structure_chain` only ever
        # sets it inside the window, so this is a guard, not a filter.)
        failed = bool(ev["failed"]) and (ev.get("failed_bar") is None
                                         or ev["failed_bar"] <= read_at)
        seen = [{**e, "failed": bool(e["failed"]) and
                 (e.get("failed_bar") is None or e["failed_bar"] <= read_at)}
                for e in d["events"][:k + 1]]
        tone, verdict = verdict_tone(stats_at(seen), {**ev, "failed": failed})
        row = {"t": t, "read_at": read_at, "type": ev["type"],
               "direction": ev["direction"], "quality": ev["quality"],
               "failed": failed, "tone": tone, "verdict": verdict}
        for h in HORIZONS:
            row[f"r{h}"] = _signed_fwd(df, read_at, h, ev["direction"], cm)
        out.append(row)
    return out


def validate(df: pd.DataFrame, label: str = "") -> bool:
    """Run BOTH walks and report every disagreement. Returns True when identical.

    A fast path that is not checked against the slow one is a rewrite with a
    result attached, and this repo has a rule about believing those.
    """
    slow, fast = walk(df), walk_fast(df)
    ok = True
    print(f"validate {label}: slow {len(slow)} events · fast {len(fast)} events")
    if len(slow) != len(fast):
        ok = False
    by_t = {r["t"]: r for r in fast}
    for r in slow:
        f = by_t.get(r["t"])
        if f is None:
            print(f"  MISSING in fast: bar {r['t']} {r['type']}")
            ok = False
            continue
        for key in ("type", "direction", "quality", "failed", "tone"):
            if r[key] != f[key]:
                print(f"  bar {r['t']} {key}: slow={r[key]} fast={f[key]}")
                ok = False
        for h in HORIZONS:
            a, b = r[f"r{h}"], f[f"r{h}"]
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9):
                print(f"  bar {r['t']} r{h}: slow={a} fast={b}")
                ok = False
    print("  IDENTICAL" if ok else "  MISMATCH")
    return ok


# ── B-115 — the do-nothing baseline ──────────────────────────────────────────
# B-114 compared two BUCKETS of structural events and found a real difference
# (+1.28pp @20d, clustered p=0.0015). It never asked whether a held break beats
# simply owning the same bars, and a two-bucket difference can be entirely a
# statement about the FAILED side being bad. This is that arm.
#
# PRE-REGISTERED, fixed here before it was run:
#
#   BASELINE   every eligible bar in the SAME names and the SAME window the
#              events came from, with the same entry/exit timing (entry at the
#              next bar's open, exit at the close h bars later) and the same
#              COST_INDIAN round trip. Not a market index, not a subset — the
#              same bars, treated identically.
#   PRIMARY    UP-direction HELD breaks vs that baseline at h = 20. Passes only
#              with a positive edge, p < 0.05, and the sign holding at 5/10/60.
#              Up-direction only, because this desk is long-only and "do nothing"
#              means "own it anyway"; a short-side comparison would be scoring a
#              trade the desk does not take.
#   CLUSTERED  the same edge with the SYMBOL as the unit, as in B-114. The
#              pooled p is not believable on its own and never was.
#   FLOOR      >= 200 up-held events, or INCONCLUSIVE.
#   SECONDARY  DOWN-direction held breaks, as description only: does the name
#              fall further than a random bar drifts? An avoid read, not a short.
BASELINE_MIN_N = 200


def baseline_returns(df: pd.DataFrame, cm=None, stride: int = 1) -> dict[int, list]:
    """Every eligible bar's forward return, same timing and costs as an event."""
    cm = cm or bt.COST_INDIAN
    df = df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
    out: dict[int, list] = {h: [] for h in HORIZONS}
    max_h = max(HORIZONS)
    for t in range(WARMUP, len(df) - max_h - FAIL_WIN - 2, stride):
        for h in HORIZONS:
            v = _signed_fwd(df, t, h, "up", cm)     # unsigned: "up" leaves it raw
            if v is not None:
                out[h].append(v)
    return out


def baseline_arm(rows: list[dict], fetch_fn, stride: int = 1) -> dict[str, Any]:
    """Held breaks vs owning the same bars — pooled and clustered by symbol."""
    syms = sorted({r["symbol"] for r in rows})
    base: dict[int, list] = {h: [] for h in HORIZONS}
    per_symbol: list[float] = []
    wins = 0

    for i, sym in enumerate(syms, 1):
        print(f"  [{i}/{len(syms)}] {sym}", end="\r", flush=True)
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or getattr(df, "empty", True):
            continue
        b = baseline_returns(df, stride=stride)
        for h in HORIZONS:
            base[h] += b[h]
        mine = [r[f"r{PRIMARY_H}"] for r in rows
                if r["symbol"] == sym and r["direction"] == "up"
                and not r["failed"] and r[f"r{PRIMARY_H}"] is not None]
        if len(mine) >= 3 and len(b[PRIMARY_H]) >= 30:
            d = float(np.mean(mine) - np.mean(b[PRIMARY_H]))
            per_symbol.append(d)
            wins += int(d > 0)
    print()

    def _held(direction: str, h: int) -> list[float]:
        return [r[f"r{h}"] for r in rows if r["direction"] == direction
                and not r["failed"] and r[f"r{h}"] is not None]

    primary = {str(h): _arm(_held("up", h), base[h]) for h in HORIZONS}
    # The down side is described, not tested: on a long-only desk the
    # alternative to a bearish read is not a short, it is not being there.
    down = {str(h): {"n": len(_held("down", h)),
                     "mean_signed": (round(float(np.mean(_held("down", h))), 3)
                                     if _held("down", h) else None),
                     "baseline_mean": (round(float(np.mean(base[h])), 3)
                                       if base[h] else None)}
            for h in HORIZONS}
    clustered = {}
    if len(per_symbol) >= 10:
        arr = np.asarray(per_symbol, float)
        t_val, p_val = bt._ttest_1samp(arr, 0.0)
        clustered = {"n_symbols": len(per_symbol),
                     "mean_diff": round(float(arr.mean()), 3),
                     "median_diff": round(float(np.median(arr)), 3),
                     "symbols_positive": wins,
                     "share_positive": round(wins / len(per_symbol), 3),
                     "t": round(float(t_val), 3), "p": round(float(p_val), 4)}

    res = {"n_up_held": len(_held("up", PRIMARY_H)),
           "n_baseline_bars": len(base[PRIMARY_H]),
           "primary": primary, "clustered": clustered, "down_side": down}
    res["verdict"] = baseline_verdict(res)
    return res


def baseline_verdict(res: dict) -> str:
    if res["n_up_held"] < BASELINE_MIN_N:
        return (f"INCONCLUSIVE — {res['n_up_held']} up-held events, under the "
                f"pre-registered floor of {BASELINE_MIN_N}")
    p = res["primary"][str(PRIMARY_H)]
    if p.get("diff") is None:
        return "INCOMPLETE"
    diffs = [res["primary"][str(h)]["diff"] for h in HORIZONS]
    if p["diff"] > 0 and p["p"] < 0.05 and all(d is not None and d > 0 for d in diffs):
        return (f"POSITIVE — a held upward break beat owning the same bars by "
                f"{p['diff']:+.2f}pp @{PRIMARY_H}d (p={p['p']:.3f})")
    if p["diff"] < 0 and p["p"] < 0.05:
        return (f"NEGATIVE — a held upward break did WORSE than owning the same "
                f"bars by {p['diff']:+.2f}pp @{PRIMARY_H}d (p={p['p']:.3f})")
    return ("NULL — a held upward break is not separable from owning the same "
            "bars at the pre-registered bar")


def baseline_report(res: dict) -> str:
    L = ["SBC held breaks vs DOING NOTHING (B-115)", "",
         f"{res['n_up_held']} up-direction held breaks vs "
         f"{res['n_baseline_bars']:,} eligible bars in the same names/window", "",
         f"{'h':>4}{'held %':>10}{'baseline %':>12}{'edge':>9}{'p':>8}"]
    for h in HORIZONS:
        m = res["primary"][str(h)]
        if m.get("diff") is None:
            L.append(f"{h:>4}{'—':>10}")
            continue
        L.append(f"{h:>4}{m['mean_a']:>10.2f}{m['mean_b']:>12.2f}"
                 f"{m['diff']:>+9.2f}{m['p']:>8.3f}")
    c = res.get("clustered") or {}
    if c:
        L += ["", f"CLUSTERED (symbol as the unit, @{PRIMARY_H}d): {c['n_symbols']} symbols · "
                  f"mean {c['mean_diff']:+.2f}pp · median {c['median_diff']:+.2f}pp · "
                  f"{c['symbols_positive']}/{c['n_symbols']} positive "
                  f"({c['share_positive']:.0%}) · p={c['p']:.4f}"]
    L += ["", "DOWN side — description only (a long-only desk does not short it).",
          "   Printed RAW, not direction-signed: the first cut of this line said "
          "'fell -0.94%' when the name had actually RISEN 0.94%, because the stored "
          "value is signed by the event's direction. An underperformance read is not "
          "a decline, and the two must not be printed in the same words."]
    for h in HORIZONS:
        d = res["down_side"][str(h)]
        if d["mean_signed"] is None:
            continue
        raw = -d["mean_signed"]          # stored signed; undo it for display
        L.append(f"   @{h}d: after a held DOWN break the name returned "
                 f"{raw:+.2f}% vs a random bar's {d['baseline_mean']:+.2f}% "
                 f"→ {raw - d['baseline_mean']:+.2f}pp")
    L += ["", f"VERDICT: {res['verdict']}"]
    return "\n".join(L)


def _arm(a: list[float], b: list[float]) -> dict[str, Any]:
    a = [x for x in a if x is not None]
    b = [x for x in b if x is not None]
    if len(a) < 2 or len(b) < 2:
        return {"n_a": len(a), "n_b": len(b), "diff": None, "p": None}
    t_val, p_val = bt._ttest_ind(np.asarray(a, float), np.asarray(b, float))
    return {"n_a": len(a), "n_b": len(b),
            "mean_a": round(float(np.mean(a)), 3),
            "mean_b": round(float(np.mean(b)), 3),
            "diff": round(float(np.mean(a) - np.mean(b)), 3),
            "t": round(float(t_val), 3), "p": round(float(p_val), 4)}


def by_symbol(rows: list[dict], h: int = PRIMARY_H) -> dict[str, Any]:
    """The clustering control the pooled t-test cannot supply.

    4,607 events over 150 names are not 4,607 independent observations: events
    inside one symbol share its trend, and events across symbols share the same
    market days. A pooled p-value over them is the most overstated number this
    study can print — the same objection B-98's pre-registration raised against
    itself, and the one `ob_bias_clustered` (B-76c) was written to answer for the
    order-block gauge.

    So: one (held − failed) difference per SYMBOL, then a one-sample test across
    symbols. The unit becomes the name, and 150 names are far closer to
    independent than 4,607 events are.
    """
    per: list[float] = []
    wins = 0
    for sym in {r.get("symbol") for r in rows}:
        mine = [r for r in rows if r.get("symbol") == sym]
        held = [r[f"r{h}"] for r in mine if not r["failed"] and r[f"r{h}"] is not None]
        fail = [r[f"r{h}"] for r in mine if r["failed"] and r[f"r{h}"] is not None]
        if len(held) < 3 or len(fail) < 3:        # a name with no comparison
            continue
        d = float(np.mean(held) - np.mean(fail))
        per.append(d)
        wins += int(d > 0)
    if len(per) < 10:
        return {"n_symbols": len(per), "mean_diff": None, "p": None}
    arr = np.asarray(per, float)
    t_val, p_val = bt._ttest_1samp(arr, 0.0)
    return {"n_symbols": len(per),
            "mean_diff": round(float(arr.mean()), 3),
            "median_diff": round(float(np.median(arr)), 3),
            "symbols_positive": wins,
            "share_positive": round(wins / len(per), 3),
            "t": round(float(t_val), 3), "p": round(float(p_val), 4)}


def analyse(rows: list[dict]) -> dict[str, Any]:
    held = [r for r in rows if not r["failed"]]
    failed = [r for r in rows if r["failed"]]
    primary = {str(h): _arm([r[f"r{h}"] for r in held],
                            [r[f"r{h}"] for r in failed]) for h in HORIZONS}
    by_tone = {}
    for tone in ("good", "warn", "bad"):
        vals = [r[f"r{PRIMARY_H}"] for r in rows
                if r["tone"] == tone and r[f"r{PRIMARY_H}"] is not None]
        by_tone[tone] = {"n": len(vals),
                         "mean": round(float(np.mean(vals)), 3) if vals else None}
    by_quality = {}
    for q in ("STRONG", "NORMAL", "WEAK"):
        vals = [r[f"r{PRIMARY_H}"] for r in rows
                if r["quality"] == q and r[f"r{PRIMARY_H}"] is not None]
        by_quality[q] = {"n": len(vals),
                         "mean": round(float(np.mean(vals)), 3) if vals else None}
    res = {"n_events": len(rows), "n_held": len(held), "n_failed": len(failed),
           "primary": primary, "by_tone": by_tone, "by_quality": by_quality,
           "clustered": by_symbol(rows)}
    res["verdict"] = verdict_of(res)
    return res


def verdict_of(res: dict) -> str:
    """The pre-registered bar, applied mechanically."""
    if min(res["n_held"], res["n_failed"]) < MIN_PER_BUCKET:
        return (f"INCONCLUSIVE — {res['n_held']} held / {res['n_failed']} failed, "
                f"under the pre-registered floor of {MIN_PER_BUCKET} per bucket")
    p = res["primary"][str(PRIMARY_H)]
    if p["diff"] is None:
        return "INCOMPLETE"
    diffs = [res["primary"][str(h)]["diff"] for h in HORIZONS]
    if p["diff"] > 0 and p["p"] < 0.05 and all(d is not None and d > 0 for d in diffs):
        return (f"POSITIVE — a break that HELD beat one that failed by "
                f"{p['diff']:+.2f}pp @{PRIMARY_H}d (p={p['p']:.3f})")
    if p["diff"] < 0 and p["p"] < 0.05:
        return (f"INVERTED — a FAILED break beat one that held by "
                f"{-p['diff']:+.2f}pp @{PRIMARY_H}d (p={p['p']:.3f})")
    return "NULL — held and failed breaks are not separable at the pre-registered bar"


def report(res: dict, label: str) -> str:
    L = [f"SBC card reading — {label}", "",
         f"{res['n_events']} structural events · {res['n_held']} held · "
         f"{res['n_failed']} failed", "",
         "PRIMARY — direction-signed forward return, HELD vs FAILED (net of costs)",
         f"{'h':>4}{'n held':>8}{'n fail':>8}{'held %':>9}{'fail %':>9}{'diff':>9}{'p':>8}"]
    for h in HORIZONS:
        m = res["primary"][str(h)]
        if m["diff"] is None:
            L.append(f"{h:>4}{m['n_a']:>8}{m['n_b']:>8}{'—':>9}")
            continue
        L.append(f"{h:>4}{m['n_a']:>8}{m['n_b']:>8}{m['mean_a']:>9.2f}"
                 f"{m['mean_b']:>9.2f}{m['diff']:>+9.2f}{m['p']:>8.3f}")
    c = res.get("clustered") or {}
    if c.get("mean_diff") is not None:
        L += ["", f"CLUSTERED — one (held − failed) difference per SYMBOL, "
                  f"tested across names (@{PRIMARY_H}d):",
              f"   {c['n_symbols']} symbols · mean {c['mean_diff']:+.2f}pp · "
              f"median {c['median_diff']:+.2f}pp · "
              f"{c['symbols_positive']}/{c['n_symbols']} positive "
              f"({c['share_positive']:.0%}) · p={c['p']:.4f}"]
    elif c:
        L += ["", f"CLUSTERED — only {c.get('n_symbols', 0)} symbols had both "
                  f"buckets; not tested"]
    L += ["", f"By card verdict tone (@{PRIMARY_H}d, signed):"]
    for tone, m in res["by_tone"].items():
        L.append(f"   {tone:<5} n={m['n']:<4} "
                 + (f"{m['mean']:+.2f}%" if m["mean"] is not None else "—"))
    L += ["", f"By quality label (@{PRIMARY_H}d, signed):"]
    for q, m in res["by_quality"].items():
        L.append(f"   {q:<7} n={m['n']:<4} "
                 + (f"{m['mean']:+.2f}%" if m["mean"] is not None else "—"))
    L += ["", f"VERDICT: {res['verdict']}"]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="SBC card reading — forward test")
    ap.add_argument("--symbol", default=None)
    ap.add_argument("--universe", default=None)
    ap.add_argument("--symbols", type=int, default=150)
    ap.add_argument("--days", type=int, default=2500)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--fast", action="store_true",
                    help="one detection pass per symbol (validated against --slow)")
    ap.add_argument("--validate", action="store_true",
                    help="run both walks on the symbol and diff them")
    ap.add_argument("--baseline", default=None, metavar="CACHED_JSON",
                    help="B-115: held breaks vs owning the same bars, from a cached run")
    a = ap.parse_args()

    import screener_pipeline as sp

    if a.baseline:
        cached = json.loads((OUT_DIR / a.baseline).read_text(encoding="utf-8"))
        res = baseline_arm(cached["rows"],
                           lambda s_: sp.fetch_ohlcv(s_, days=a.days),
                           stride=a.stride)
        (OUT_DIR / f"baseline_{a.baseline}").write_text(
            json.dumps({k: v for k, v in res.items()}, indent=1, sort_keys=True),
            encoding="utf-8")
        print(baseline_report(res))
        return 0

    if a.universe:
        import nse_universe as nu
        syms = list(nu.symbols(a.universe))[:a.symbols]
        label = f"{a.universe}[:{a.symbols}]"
    else:
        syms = [a.symbol or "BSE"]
        label = syms[0]

    rows: list[dict] = []
    for i, sym in enumerate(syms, 1):
        if len(syms) > 1:
            print(f"  [{i}/{len(syms)}] {sym}", end="\r", flush=True)
        try:
            df = sp.fetch_ohlcv(sym, days=a.days)
        except Exception:
            continue
        if df is None or getattr(df, "empty", True):
            continue
        if a.validate:
            validate(df, sym)
            continue
        _w = walk_fast if (a.fast or a.universe) else walk
        rows += [{**r, "symbol": sym} for r in
                 (_w(df) if _w is walk_fast else _w(df, stride=a.stride))]
    if len(syms) > 1:
        print()

    if a.validate:
        return 0
    res = analyse(rows)
    res["label"] = label
    # Keep the rows. The next question asked of this run should not cost another
    # walk over 150 symbols, and an aggregate cannot answer a question nobody
    # thought of when it was written.
    res["rows"] = [{k: v for k, v in r.items() if k != "verdict"} for r in rows]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{label.replace('[', '_').replace(']', '').replace(':', '')}.json"
     ).write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
    print(report(res, label))
    return 0


if __name__ == "__main__":
    sys.exit(main())
