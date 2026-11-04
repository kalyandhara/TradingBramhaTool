#!/usr/bin/env python3
"""portfolio_sim.py — what a signal does to a BOOK, not to one trade (B-159).

The harness scores every trade alone, in R. That answers "is the plan any
good?" and says nothing about what trading it would have done to an account:
two signals on the same day compete for the same capital, ten open positions
leave no room for the eleventh, a 3R winner sized on a shrunken account is
worth less than one sized at the peak, and a run of losers arrives together.
This replays the harness's own simulated trades (``keep_trades=True``) through
an account with the rules below, and reports the account.

    py -3 -X utf8 tools/portfolio_sim.py --rule tools/rules/ema20_reclaim_rsi50.json
    py -3 -X utf8 tools/portfolio_sim.py --scanner "Falling Wedge"
    py -3 -X utf8 tools/portfolio_sim.py --rule R.json --risk 0.5 --max-open 8

── The account rules (all reported in the output) ─────────────────────────────
* **Sizing — fixed fractional on CLOSED equity.** Each trade risks ``risk_pct``
  of the equity realised so far: shares × (entry − stop) = risk amount. Open
  positions are not marked to market for sizing (the usual retail rule, and
  the one the desk's `portfolio_risk` uses for INITIAL risk).
* **Caps.** One position per symbol; at most ``max_open`` positions; no single
  position larger than ``max_position_pct`` of equity; no leverage — a new
  position needs free cash (equity minus the notional already open). A trade
  shrunk by a cap still trades, at the smaller size; one that cannot get even
  ``min_position_pct`` of equity is skipped and counted.
* **Shorts are skipped by default** (``allow_short=False``): overnight shorts
  are not available in NSE cash delivery, and a simulation that books them
  describes an account nobody here can hold.
* **Same-day order.** On each date, entries are taken BEFORE that day's exits
  free their capital — a stop hit at 2pm cannot fund a 9:15 entry. When more
  signals arrive on one date than there are slots, which ones get in is
  decided by a SEEDED shuffle, and the simulation is repeated over
  ``n_seeds`` seeds so the selection luck is visible as a spread rather than
  hidden in one path.
* **P&L** = the trade's R (already net of costs, from the harness) × the risk
  amount actually taken.

── What the numbers do NOT include ────────────────────────────────────────────
* **Drawdown is on the CLOSED-trade curve.** It cannot see a position that
  went deep red before recovering, so it UNDERSTATES the drawdown an account
  holder would have lived through. Stated in the report, every time.
* No cash interest, no taxes, no dividends; gaps are already in the harness's
  fills; survivors only (the universe is today's NIFTY 500).

The portfolio settings are knobs as much as rule thresholds are. Changing them
until the curve looks good is the same overfitting the variant log in
`rule_runner.py` exists to count.
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np
import pandas as pd

import position_sizing as ps


@dataclass
class Settings:
    capital: float = 1_000_000.0
    risk_pct: float = 1.0            # % of closed equity risked per trade
    max_open: int = 10
    max_position_pct: float = 20.0   # % of equity, per position
    min_position_pct: float = 1.0    # below this a capped trade is skipped
    allow_short: bool = False
    n_seeds: int = 20

    def validate(self) -> None:
        if not self.capital > 0:
            raise ValueError("capital must be positive")
        if not 0 < self.risk_pct <= 10:
            raise ValueError("risk_pct must be in (0, 10]")
        if self.max_open < 1:
            raise ValueError("max_open must be at least 1")
        if not 0 < self.max_position_pct <= 100:
            raise ValueError("max_position_pct must be in (0, 100]")
        if not 0 <= self.min_position_pct < self.max_position_pct:
            raise ValueError("min_position_pct must be below max_position_pct")
        if self.n_seeds < 1:
            raise ValueError("n_seeds must be at least 1")


def usable_trades(trades: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Trades the account can replay, and a count of the rest by reason."""
    keep, dropped = [], defaultdict(int)
    for t in trades:
        if t.get("entry_date") is None or t.get("exit_date") is None:
            dropped["no_dates"] += 1
            continue
        ep, st, r = t.get("entry_px"), t.get("stop"), t.get("r")
        if ep is None or st is None or r is None or not math.isfinite(float(r)):
            dropped["no_plan_fields"] += 1
            continue
        if not abs(float(ep) - float(st)) > 0:
            dropped["zero_risk"] += 1
            continue
        keep.append(t)
    return keep, dict(dropped)


def _one_path(trades: list[dict], s: Settings, seed: int) -> dict:
    rng = random.Random(seed)
    by_entry: dict[Any, list[dict]] = defaultdict(list)
    for t in trades:
        by_entry[pd.Timestamp(t["entry_date"])].append(t)
    dates = sorted(set(by_entry) | {pd.Timestamp(t["exit_date"]) for t in trades})

    equity = s.capital
    open_pos: list[dict] = []          # {symbol, notional, pnl, exit_date}
    curve: list[tuple[pd.Timestamp, float]] = [(dates[0], equity)] if dates else []
    skipped = defaultdict(int)
    taken = 0
    capped = 0
    open_counts: list[int] = []

    for d in dates:
        # 1. Entries at the open (capital freed later today is not yet free).
        todays = list(by_entry.get(d, []))
        rng.shuffle(todays)
        for t in todays:
            if t.get("side") == "short" and not s.allow_short:
                skipped["short"] += 1
                continue
            if any(p["symbol"] == t["symbol"] for p in open_pos):
                skipped["already_holding_symbol"] += 1
                continue
            if len(open_pos) >= s.max_open:
                skipped["no_free_slot"] += 1
                continue
            entry, stop = float(t["entry_px"]), float(t["stop"])
            risk_frac = abs(entry - stop) / entry          # loss per ₹ of notional at the stop
            notional = ps.notional_for_risk(equity, entry, stop, s.risk_pct)
            cash = equity - sum(p["notional"] for p in open_pos)
            cap = min(equity * s.max_position_pct / 100.0, cash)
            if notional > cap:
                notional = cap
                capped += 1
            if notional < equity * s.min_position_pct / 100.0:
                skipped["no_cash"] += 1
                continue
            risk_amt = notional * risk_frac
            open_pos.append({"symbol": t["symbol"], "notional": notional,
                             "pnl": float(t["r"]) * risk_amt,
                             "exit_date": pd.Timestamp(t["exit_date"])})
            taken += 1
        open_counts.append(len(open_pos))
        # 2. Exits during the day.
        still = []
        for p in open_pos:
            if p["exit_date"] <= d:
                equity += p["pnl"]
            else:
                still.append(p)
        if len(still) != len(open_pos):
            curve.append((d, equity))
        open_pos = still
        if equity <= 0:
            break                       # ruin: nothing further can be sized

    eq = np.array([v for _, v in curve], dtype=float)
    peak = np.maximum.accumulate(eq) if len(eq) else eq
    dd = (eq / peak - 1.0) * 100.0 if len(eq) else eq
    # Longest stretch below a prior peak, in calendar days.
    longest, start = 0, None
    for (dt, v), pk in zip(curve, peak):
        if v < pk:
            start = start or dt
            longest = max(longest, (dt - start).days)
        else:
            start = None
    span_years = ((dates[-1] - dates[0]).days / 365.25) if len(dates) > 1 else 0.0
    final = float(eq[-1]) if len(eq) else s.capital
    cagr = ((final / s.capital) ** (1 / span_years) - 1) * 100.0 \
        if span_years > 0 and final > 0 else None
    return {"seed": seed, "final_equity": final,
            "total_return_pct": (final / s.capital - 1.0) * 100.0,
            "cagr_pct": cagr, "max_dd_closed_pct": float(dd.min()) if len(dd) else 0.0,
            "longest_dd_days": longest, "taken": taken, "capped": capped,
            "skipped": dict(skipped),
            "avg_open": float(np.mean(open_counts)) if open_counts else 0.0,
            "first_date": str(dates[0].date()) if dates else None,
            "last_date": str(dates[-1].date()) if dates else None,
            "span_years": round(span_years, 2),
            "curve": [(str(dt.date()), round(v, 2)) for dt, v in curve]}


def simulate(trades: list[dict], settings: Settings | None = None) -> dict:
    s = settings or Settings()
    s.validate()
    usable, dropped = usable_trades(trades)
    out: dict[str, Any] = {"settings": asdict(s), "n_trades_in": len(trades),
                           "n_usable": len(usable), "dropped": dropped}
    if not usable:
        out["error"] = "no usable trades (does the rule/scanner emit a plan?)"
        return out
    paths = [_one_path(usable, s, seed) for seed in range(s.n_seeds)]

    def q(key, p):
        vals = [x[key] for x in paths if x[key] is not None]
        return float(np.percentile(vals, p)) if vals else None

    out["paths"] = [{k: v for k, v in p.items() if k != "curve"} for p in paths]
    out["median_curve"] = sorted(paths, key=lambda p: p["final_equity"])[len(paths) // 2]["curve"]
    out["summary"] = {
        k: {"p10": q(k, 10), "median": q(k, 50), "p90": q(k, 90)}
        for k in ("total_return_pct", "cagr_pct", "max_dd_closed_pct",
                  "longest_dd_days", "taken", "avg_open")}
    first = paths[0]
    out["span"] = {"first": first["first_date"], "last": first["last_date"],
                   "years": first["span_years"]}
    # Every seed sees the same signals, so skip reasons differ only in which
    # trade lost the race; report seed 0's as representative.
    out["skipped_seed0"] = first["skipped"]
    out["capped_seed0"] = first["capped"]
    return out


def format_report(res: dict, benchmark_cagr: float | None = None) -> str:
    s = res["settings"]
    lines = [f"=== Portfolio simulation (B-159) — {s['n_seeds']} seeds ===",
             f"account: ₹{s['capital']:,.0f} · risk {s['risk_pct']:g}% of closed equity per trade · "
             f"max {s['max_open']} open · ≤{s['max_position_pct']:g}% per position · "
             f"no leverage · shorts {'allowed' if s['allow_short'] else 'skipped'}"]
    lines.append(f"trades: {res['n_trades_in']} from the harness, {res['n_usable']} replayable"
                 + (f" (dropped: {res['dropped']})" if res["dropped"] else ""))
    if res.get("error"):
        lines.append(f"ERROR: {res['error']}")
        return "\n".join(lines)
    sp = res["span"]
    lines.append(f"span: {sp['first']} → {sp['last']} ({sp['years']} years)")
    lines.append("")
    lines.append(f"{'':24}{'p10':>10}{'median':>10}{'p90':>10}")
    fmt = {"total_return_pct": ("total return %", "{:+.1f}"),
           "cagr_pct": ("CAGR %", "{:+.1f}"),
           "max_dd_closed_pct": ("max drawdown % (closed)", "{:.1f}"),
           "longest_dd_days": ("longest drawdown, days", "{:.0f}"),
           "taken": ("trades taken", "{:.0f}"),
           "avg_open": ("avg positions open", "{:.1f}")}
    for k, (label, f) in fmt.items():
        row = res["summary"][k]
        cells = [(f.format(row[p]) if row[p] is not None else "n/a") for p in ("p10", "median", "p90")]
        lines.append(f"{label:24}" + "".join(f"{c:>10}" for c in cells))
    if benchmark_cagr is not None:
        lines.append(f"{'NIFTY 50 CAGR, same span':24}{'':>10}{benchmark_cagr:>+10.1f}")
    else:
        lines.append("NIFTY 50 benchmark: unavailable (fetch failed) — no comparison shown")
    lines.append("")
    lines.append(f"skipped (seed 0): {res['skipped_seed0'] or 'none'} · "
                 f"shrunk by a cap: {res['capped_seed0']}")
    lines.append("drawdown is on the CLOSED-trade curve: it cannot see open losses that "
                 "later recovered, so the lived drawdown was deeper.")
    lines.append("survivors only (today's index members); no tax, interest or dividends.")
    return "\n".join(lines)


def benchmark_cagr(first: str, last: str) -> float | None:
    """NIFTY 50 price CAGR over the same span (no dividends — the account gets
    none either). Fetched straight from yfinance, as `market_health` does:
    `screener_pipeline.fetch_ohlcv` is the STOCK fetcher and cannot load an
    index symbol. None when unavailable; the report then says so."""
    try:
        import yfinance as yf
        end = (pd.Timestamp(last) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        df = yf.download("^NSEI", start=first, end=end, interval="1d",
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        c = df["Close"].dropna()
        yrs = (c.index[-1] - c.index[0]).days / 365.25
        return ((float(c.iloc[-1]) / float(c.iloc[0])) ** (1 / yrs) - 1) * 100.0 if yrs > 0 else None
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--rule", help="a rule .json (rule_engine)")
    src.add_argument("--scanner", help="a registered scanner name")
    ap.add_argument("--symbols", type=int, default=300)
    ap.add_argument("--universe", default="nifty500")
    ap.add_argument("--days", type=int, default=1500)
    ap.add_argument("--exit-model", default=None)
    d = Settings()
    ap.add_argument("--capital", type=float, default=d.capital)
    ap.add_argument("--risk", type=float, default=d.risk_pct, help="%% of equity risked per trade")
    ap.add_argument("--max-open", type=int, default=d.max_open)
    ap.add_argument("--max-position", type=float, default=d.max_position_pct)
    ap.add_argument("--allow-short", action="store_true")
    ap.add_argument("--seeds", type=int, default=d.n_seeds)
    a = ap.parse_args(argv)

    import backtest as bt
    import nse_universe as nu
    import screener_pipeline as sp

    if a.rule:
        import rule_engine as rengine
        try:
            rule = rengine.load_rule(a.rule)
        except (OSError, rengine.RuleError) as e:
            print(f"rule rejected: {e}", file=sys.stderr)
            return 2
        if not rule.plan:
            print("rule rejected: no 'plan' — a portfolio needs a stop to size from.",
                  file=sys.stderr)
            return 2
        name = rengine.register(rule)
        print(f"rule {rule.name} [{rule.logic_hash()}] — hypothesis: {rule.hypothesis or '(none)'}")
    else:
        import scanner_templates as sc
        if a.scanner not in sc.SCANNERS:
            print(f"unknown scanner {a.scanner!r}", file=sys.stderr)
            return 2
        name = a.scanner

    syms = list(nu.symbols(a.universe))[:a.symbols]
    cache: dict = {}

    def fetch(s):
        if s not in cache:
            try:
                cache[s] = sp.fetch_ohlcv(s, days=a.days)
            except Exception:
                cache[s] = None
        return cache[s]

    res_bt = bt.backtest_scanner(name, syms, fetch, cost_model=bt.COST_INDIAN,
                                 signal_mode="fresh", fill_model="market",
                                 exit_model=a.exit_model, keep_trades=True)
    settings = Settings(capital=a.capital, risk_pct=a.risk, max_open=a.max_open,
                        max_position_pct=a.max_position, allow_short=a.allow_short,
                        n_seeds=a.seeds)
    try:
        res = simulate(res_bt.get("trades") or [], settings)
    except ValueError as e:
        print(f"settings rejected: {e}", file=sys.stderr)
        return 2
    bcagr = benchmark_cagr(res["span"]["first"], res["span"]["last"]) \
        if res.get("span") else None
    print(f"harness: {name} · signals=fresh · fill=market · exit={res_bt.get('exit_model')} · "
          f"Indian costs · {res_bt.get('n_symbols_used')} symbols")
    print(format_report(res, bcagr))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
