#!/usr/bin/env python3
"""rule_runner.py — measure a rule file through the shared harness (B-158).

    py -3 -X utf8 tools/rule_runner.py tools/rules/ema20_reclaim_rsi50.json
    py -3 -X utf8 tools/rule_runner.py RULE.json --symbols 100 --windows 3
    py -3 -X utf8 tools/rule_runner.py RULE.json --check     # compile only
    py -3 -X utf8 tools/rule_runner.py --history             # every rule run so far

The run is the desk's standard one, not a menu of conveniences: NIFTY 500
names, daily bars, Indian delivery costs, FRESH signals (B-120), next-open fills
(B-121), walk-forward windows (B-21), compared with the random-entry baseline on
the same bars. ``--exit-model`` is offered because B-123 made it a harness
option; it is reported in the header like everything else.

── Two guards, because a rule language is a machine for overfitting ───────────
1. **No hypothesis, no run.** The rule file must say, in words, what it expects
   before any number exists. It is printed at the top of the report.
2. **Every distinct rule is logged** (`cache/rule_runs/runs.jsonl`, keyed on the
   rule's LOGIC hash — renaming a rule or rewording its hypothesis is not a new
   variant, changing a threshold is). The report prints how many distinct rules
   have been measured to date and the Bonferroni bar that count implies. Tuning
   a threshold until the 14th try clears p < 0.05 is fourteen tries, and the
   report says so.

Nothing here is a verdict machine: ``*`` in the window table is the harness's
uncorrected p < 0.05; the corrected bar is printed beneath it for the reader.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

import backtest as bt
import rule_engine as rengine

RUN_LOG = Path(__file__).resolve().parent / "cache" / "rule_runs" / "runs.jsonl"
DEFAULT_SYMBOLS = 300
DEFAULT_DAYS = 1500
DEFAULT_WINDOWS = 3


def read_log(path: Path = RUN_LOG) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue       # a torn line must not hide the rest of the history
    return out


def distinct_rules(entries: list[dict]) -> int:
    return len({e.get("logic_hash") for e in entries if e.get("logic_hash")})


def append_log(entry: dict, path: Path = RUN_LOG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def headline(result: dict) -> dict:
    """The few numbers worth keeping beside the hash. The full result is not
    logged: the log is for COUNTING variants, not a second results store."""
    pooled = result.get("pooled") or {}
    hz = {str(h): (m or {}).get("edge")
          for h, m in (pooled.get("horizons") or {}).items()}
    plans = result.get("plans") or {}
    return {"n_signals": pooled.get("n_signals"), "edge_by_horizon": hz,
            "avg_R": plans.get("avg_R"), "n_with_plan": plans.get("n_with_plan"),
            "stability": (result.get("stability") or {}).get("verdict")}


def multiple_testing_note(k: int) -> str:
    if k <= 1:
        return ("rules measured to date: 1 — this is the first, so p < 0.05 "
                "is the bar.")
    return (f"rules measured to date: {k} distinct — a single result among {k} "
            f"tries needs p < {0.05 / k:.4f} (0.05 / {k}) before it counts.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("rule", nargs="?", help="path to a rule .json file")
    ap.add_argument("--symbols", type=int, default=DEFAULT_SYMBOLS)
    ap.add_argument("--universe", default="nifty500")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--windows", type=int, default=DEFAULT_WINDOWS)
    ap.add_argument("--exit-model", default=None,
                    help="harness exit model (B-123), e.g. atr_trail:3")
    ap.add_argument("--check", action="store_true",
                    help="compile the rule and stop; nothing is run or logged")
    ap.add_argument("--history", action="store_true",
                    help="list every rule run so far and stop")
    a = ap.parse_args(argv)

    if a.history:
        entries = read_log()
        if not entries:
            print("no rule runs logged yet")
            return 0
        for e in entries:
            hl = e.get("headline") or {}
            print(f"{e.get('when', '?')[:16]}  {e.get('logic_hash')}  "
                  f"{e.get('name')!r:40}  n={hl.get('n_signals')}  "
                  f"edge={hl.get('edge_by_horizon')}  R={hl.get('avg_R')}")
        print(multiple_testing_note(distinct_rules(entries)))
        return 0

    if not a.rule:
        ap.error("a rule file is required (or --history)")
    try:
        rule = rengine.load_rule(a.rule)
    except (OSError, rengine.RuleError) as e:
        print(f"rule rejected: {e}", file=sys.stderr)
        return 2
    if not rule.hypothesis:
        print("rule rejected: no 'hypothesis'. Write down what you expect, and "
              "at which horizon, BEFORE the first run.", file=sys.stderr)
        return 2
    print(f"rule      {rule.name}  [{rule.logic_hash()}]  side={rule.side}  "
          f"steps={len(rule.steps)}  plan={'yes' if rule.plan else 'no'}")
    print(f"hypothesis {rule.hypothesis}")
    if a.check:
        print("compiled OK (--check: nothing run, nothing logged)")
        return 0

    import nse_universe as nu
    import screener_pipeline as sp
    syms = list(nu.symbols(a.universe))[:a.symbols]
    cache: dict = {}

    def fetch(s):
        if s not in cache:
            try:
                cache[s] = sp.fetch_ohlcv(s, days=a.days)
            except Exception:
                cache[s] = None
        return cache[s]

    name = rengine.register(rule)
    res = bt.walk_forward_scanner(name, syms, fetch, n_windows=a.windows,
                                  cost_model=bt.COST_INDIAN,
                                  signal_mode="fresh", fill_model="market",
                                  exit_model=a.exit_model)

    prior = read_log()
    entry = {"when": _dt.datetime.now().isoformat(timespec="seconds"),
             "name": rule.name, "logic_hash": rule.logic_hash(),
             "hypothesis": rule.hypothesis, "rule": rule.raw,
             "settings": {"universe": a.universe, "symbols": len(syms),
                          "days": a.days, "windows": a.windows,
                          "exit_model": a.exit_model or "fixed",
                          "signal_mode": "fresh", "fill_model": "market",
                          "cost": "COST_INDIAN"},
             "headline": headline(res)}
    append_log(entry)
    k = distinct_rules(prior + [entry])

    print()
    print(bt.format_walk_forward(res))
    print()
    print(multiple_testing_note(k))
    print(f"logged to {RUN_LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
