#!/usr/bin/env python3
"""rule_engine.py — entry rules as data, replayed by the shared harness (B-158).

The harness (`backtest.backtest_scanner`) can only replay a REGISTERED scanner:
every new idea ("RSI crosses 50 after a close back above EMA20") needs a Python
function in `scanner_templates`. And `backtest_confluence` only asks whether two
scanners fire on the SAME bar. Neither can express a sequence — A, then B within
N bars, cancelled if C happens first — which is how most discretionary entries
are actually described (and what LuxAlgo's Backtester calls "steps").

A rule is a plain dict (or a JSON file):

    {
      "name": "ema20 reclaim then rsi50",
      "hypothesis": "A reclaim of EMA20 confirmed by RSI crossing 50 within 5
                     bars beats a random entry at 20d.",
      "side": "long",
      "steps": [
        {"all": [{"lhs": "close", "op": "crosses_above", "rhs": "ema:20"}]},
        {"all": [{"lhs": "rsi:14", "op": "crosses_above", "rhs": 50}],
         "within": 5}
      ],
      "invalidate": [{"lhs": "close", "op": "<", "rhs": "sma:50"}],
      "plan": {"stop": "atr:14:2", "target_r": 2, "time_stop": 20}
    }

── Operands ───────────────────────────────────────────────────────────────────
A number, or ``name[:p1[:p2[:p3]]]`` with an optional ``[k]`` suffix meaning
"k bars ago" (``close[1]`` is the previous close):

    open high low close volume
    sma:n  ema:n          on close
    rsi:n                 Wilder, the same function the scanners use
    atr:n                 Wilder
    mfi:n                 money flow index
    roc:n                 % change over n bars
    highest:n  lowest:n   highest HIGH / lowest LOW of the n bars BEFORE this one
                          (the current bar is excluded, so ``close > highest:20``
                          is a breakout, not an impossibility)
    vol_sma:n             mean volume of the last n bars (current included)
    macd[:f:s:sig]  macd_signal[:f:s:sig]  macd_hist[:f:s:sig]   default 12:26:9
    bb_upper:n:k  bb_lower:n:k                                   default 20:2

Every series is CAUSAL: its value at bar t uses bars 0..t only. That is what
lets `prepare` compute each series once over a symbol's full history and still
be point-in-time; `test_rule_engine.py` pins it by comparing the full-history
answer at bar t with the answer computed on ``df.iloc[:t+1]``.

── Conditions ─────────────────────────────────────────────────────────────────
``{"lhs": operand, "op": op, "rhs": operand, "mult": optional float}``, with op
one of ``> < >= <= crosses_above crosses_below``. ``mult`` scales the rhs
(``volume > 1.5 × vol_sma:20``). ``crosses_above`` is lhs > rhs now and
lhs <= rhs on the previous bar. A NaN on either side (warm-up) is False.

── Steps (the sequence) ───────────────────────────────────────────────────────
A step is true on a bar when every ``all`` condition holds and, if an ``any``
list is given, at least one of those holds. Steps complete IN ORDER, each on a
strictly LATER bar than the one before. ``within: N`` on a step means it must
complete no more than N bars after the previous step, or the sequence expires
and the bar is evaluated afresh for step 1. The signal fires on the bar the
last step completes, and the sequence resets. A one-step rule is therefore a
plain "all of these on the same bar".

``invalidate`` — any one condition true cancels an UNFINISHED sequence (it has
no effect when no step has completed). The cancelling bar does not itself start
a new sequence: a bar that just broke the setup is not also its first step.

``restart_on_step1`` (default False) — when step 1 fires again before the next
step completes, restart the sequence from the newer bar (LuxAlgo's "Invalidate
On Step 1"). The next step is checked first, so a bar that completes the next
step advances rather than restarts.

── Plan (optional) ────────────────────────────────────────────────────────────
Without a plan the harness measures forward returns against its random-entry
baseline only. With one, every signal carries entry = the signal bar's close,
a stop and a target, and the harness scores R the same way it scores a scanner
card (so ``fill_model``, ``exit_model`` and ``signal_mode`` all apply):

    stop       "atr:n:k"   entry ∓ k × ATR(n)
               "pct:p"     entry ∓ p %
               "swing:n"   below the lowest low (long) / above the highest high
                           (short) of the last n bars, current bar included
    target_r   target = entry ± target_r × (entry − stop distance)
    time_stop  optional, bars

This module states nothing about whether any rule works. It is plumbing; the
measuring is `rule_runner.py`, which refuses a rule with no hypothesis.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Callable

import numpy as np
import pandas as pd

import scanner_templates as sc

OPS = (">", "<", ">=", "<=", "crosses_above", "crosses_below")
SIDES = ("long", "short")
RULE_PREFIX = "Rule: "

_OPERAND_RE = re.compile(r"^([a-z_]+)((?::[0-9.]+)*)(?:\[(\d+)\])?$")

# name -> (number of params allowed, defaults)
_SERIES: dict[str, tuple[int, tuple[float, ...]]] = {
    "open": (0, ()), "high": (0, ()), "low": (0, ()), "close": (0, ()),
    "volume": (0, ()),
    "sma": (1, ()), "ema": (1, ()), "rsi": (1, (14,)), "atr": (1, (14,)),
    "mfi": (1, (14,)), "roc": (1, ()), "highest": (1, ()), "lowest": (1, ()),
    "vol_sma": (1, ()),
    "macd": (3, (12, 26, 9)), "macd_signal": (3, (12, 26, 9)),
    "macd_hist": (3, (12, 26, 9)),
    "bb_upper": (2, (20, 2)), "bb_lower": (2, (20, 2)),
}


class RuleError(ValueError):
    """A rule that cannot be compiled. Raised before any bar is read."""


# ── operands ──────────────────────────────────────────────────────────────────

def _parse_operand(spec: Any) -> tuple:
    """Return ("num", value) or ("series", name, params, lag)."""
    if isinstance(spec, bool):
        raise RuleError(f"operand cannot be a boolean: {spec!r}")
    if isinstance(spec, (int, float)):
        if not math.isfinite(spec):
            raise RuleError(f"operand must be finite: {spec!r}")
        return ("num", float(spec))
    if not isinstance(spec, str):
        raise RuleError(f"operand must be a number or a string, got {spec!r}")
    m = _OPERAND_RE.match(spec.strip().lower())
    if not m:
        raise RuleError(f"cannot read operand {spec!r}")
    name, raw_params, lag = m.group(1), m.group(2), m.group(3)
    if name not in _SERIES:
        raise RuleError(f"unknown series {name!r} in {spec!r}; "
                        f"known: {', '.join(sorted(_SERIES))}")
    n_allowed, defaults = _SERIES[name]
    params = [float(p) for p in raw_params.split(":") if p] if raw_params else []
    if len(params) > n_allowed:
        raise RuleError(f"{name} takes at most {n_allowed} parameter(s): {spec!r}")
    params = params + list(defaults[len(params):])
    if len(params) < n_allowed:
        raise RuleError(f"{name} needs {n_allowed} parameter(s): {spec!r}")
    for i, p in enumerate(params):
        # bb_upper/bb_lower's second parameter is a width (may be fractional);
        # everything else is a bar count.
        is_width = name in ("bb_upper", "bb_lower") and i == 1
        if p <= 0 or (not is_width and p != int(p)):
            raise RuleError(f"bad parameter {p:g} in {spec!r}")
    return ("series", name, tuple(params), int(lag) if lag else 0)


def _compute_series(df: pd.DataFrame, name: str, params: tuple) -> pd.Series:
    c = df["close"].astype(float)
    if name in ("open", "high", "low", "close", "volume"):
        return df[name].astype(float)
    n = int(params[0]) if params else 0
    if name == "sma":
        return c.rolling(n).mean()
    if name == "ema":
        # NaN through the warm-up so a 200-EMA is not "valid" on bar 3.
        e = sc._ema_series(c, n)
        e.iloc[: n - 1] = np.nan
        return e
    if name == "rsi":
        return sc._rsi_series(c, n)
    if name == "atr":
        a = sc._atr_series(df, n)
        a.iloc[: n - 1] = np.nan
        return a
    if name == "mfi":
        return sc._mfi_series(df, n)
    if name == "roc":
        return (c / c.shift(n) - 1.0) * 100.0
    if name == "highest":
        return df["high"].astype(float).shift(1).rolling(n).max()
    if name == "lowest":
        return df["low"].astype(float).shift(1).rolling(n).min()
    if name == "vol_sma":
        return df["volume"].astype(float).rolling(n).mean()
    if name in ("macd", "macd_signal", "macd_hist"):
        f, s, g = (int(x) for x in params)
        line = sc._ema_series(c, f) - sc._ema_series(c, s)
        line.iloc[: s - 1] = np.nan
        sig = line.ewm(span=g, adjust=False).mean()
        sig.iloc[: s + g - 2] = np.nan
        return {"macd": line, "macd_signal": sig, "macd_hist": line - sig}[name]
    if name in ("bb_upper", "bb_lower"):
        k = float(params[1])
        mid = c.rolling(n).mean()
        sd = c.rolling(n).std(ddof=0)
        return mid + k * sd if name == "bb_upper" else mid - k * sd
    raise RuleError(f"unhandled series {name!r}")   # unreachable: parse checks


class _Frame:
    """Per-symbol cache: each distinct series is computed once."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.n = len(df)
        self._cache: dict[tuple, np.ndarray] = {}

    def value(self, op: tuple) -> np.ndarray:
        if op[0] == "num":
            return np.full(self.n, op[1], dtype=float)
        key = op[1:]
        if key not in self._cache:
            _, name, params, lag = op
            base_key = (name, params, 0)
            if base_key not in self._cache:
                s = _compute_series(self.df, name, params)
                self._cache[base_key] = s.to_numpy(dtype=float)
            base = self._cache[base_key]
            if lag:
                shifted = np.full(self.n, np.nan)
                shifted[lag:] = base[:-lag] if lag < self.n else []
                self._cache[key] = shifted
            else:
                self._cache[key] = base
        return self._cache[key]


# ── conditions and steps ──────────────────────────────────────────────────────

def _compile_condition(c: Any, where: str) -> dict:
    if not isinstance(c, dict):
        raise RuleError(f"{where}: a condition must be an object, got {c!r}")
    unknown = set(c) - {"lhs", "op", "rhs", "mult"}
    if unknown:
        raise RuleError(f"{where}: unknown key(s) {sorted(unknown)}")
    for k in ("lhs", "op", "rhs"):
        if k not in c:
            raise RuleError(f"{where}: missing {k!r}")
    if c["op"] not in OPS:
        raise RuleError(f"{where}: op must be one of {OPS}, got {c['op']!r}")
    mult = c.get("mult", 1.0)
    if isinstance(mult, bool) or not isinstance(mult, (int, float)) \
            or not math.isfinite(mult) or mult <= 0:
        raise RuleError(f"{where}: mult must be a positive number, got {mult!r}")
    return {"lhs": _parse_operand(c["lhs"]), "op": c["op"],
            "rhs": _parse_operand(c["rhs"]), "mult": float(mult)}


def _eval_condition(frame: _Frame, cond: dict) -> np.ndarray:
    a = frame.value(cond["lhs"])
    b = frame.value(cond["rhs"]) * cond["mult"]
    ok = ~(np.isnan(a) | np.isnan(b))
    op = cond["op"]
    with np.errstate(invalid="ignore"):
        if op == ">":
            out = a > b
        elif op == "<":
            out = a < b
        elif op == ">=":
            out = a >= b
        elif op == "<=":
            out = a <= b
        else:
            pa = np.concatenate(([np.nan], a[:-1]))
            pb = np.concatenate(([np.nan], b[:-1]))
            ok = ok & ~(np.isnan(pa) | np.isnan(pb))
            if op == "crosses_above":
                out = (a > b) & (pa <= pb)
            else:
                out = (a < b) & (pa >= pb)
    return out & ok


def _compile_step(s: Any, i: int) -> dict:
    where = f"step {i + 1}"
    if not isinstance(s, dict):
        raise RuleError(f"{where}: must be an object")
    unknown = set(s) - {"all", "any", "within"}
    if unknown:
        raise RuleError(f"{where}: unknown key(s) {sorted(unknown)}")
    all_ = [_compile_condition(c, f"{where}.all[{j}]")
            for j, c in enumerate(s.get("all") or [])]
    any_ = [_compile_condition(c, f"{where}.any[{j}]")
            for j, c in enumerate(s.get("any") or [])]
    if not all_ and not any_:
        raise RuleError(f"{where}: needs at least one condition in 'all' or 'any'")
    within = s.get("within")
    if within is not None:
        if i == 0:
            raise RuleError("step 1 cannot have 'within' — it has no previous step")
        if isinstance(within, bool) or not isinstance(within, int) or within < 1:
            raise RuleError(f"{where}: within must be a positive integer")
    return {"all": all_, "any": any_, "within": within}


def _step_mask(frame: _Frame, step: dict) -> np.ndarray:
    m = np.ones(frame.n, dtype=bool)
    for c in step["all"]:
        m &= _eval_condition(frame, c)
    if step["any"]:
        anym = np.zeros(frame.n, dtype=bool)
        for c in step["any"]:
            anym |= _eval_condition(frame, c)
        m &= anym
    return m


def run_sequence(step_masks: list[np.ndarray], within: list[int | None],
                 invalidate: np.ndarray | None,
                 restart_on_step1: bool = False) -> np.ndarray:
    """The step state machine over precomputed per-step masks. Returns a bool
    array, True on the bar each completed sequence fires. Causal: the state at
    bar t depends on bars 0..t only."""
    n = len(step_masks[0])
    S = len(step_masks)
    fire = np.zeros(n, dtype=bool)
    k = 0           # steps completed in the current sequence
    last = -1       # bar of the most recent completed step
    for t in range(n):
        if k > 0:
            if invalidate is not None and invalidate[t]:
                k, last = 0, -1
                continue
            w = within[k]
            if w is not None and t - last > w:
                k, last = 0, -1            # expired; this bar may start afresh
        if step_masks[k][t]:
            k += 1
            last = t
            if k == S:
                fire[t] = True
                k, last = 0, -1
        elif k > 0 and restart_on_step1 and step_masks[0][t]:
            k, last = 1, t
    return fire


# ── plan ──────────────────────────────────────────────────────────────────────

def _compile_plan(p: Any) -> dict | None:
    if p is None:
        return None
    if not isinstance(p, dict):
        raise RuleError("plan must be an object")
    unknown = set(p) - {"stop", "target_r", "time_stop"}
    if unknown:
        raise RuleError(f"plan: unknown key(s) {sorted(unknown)}")
    stop = p.get("stop")
    if not isinstance(stop, str):
        raise RuleError("plan.stop is required: 'atr:n:k', 'pct:p' or 'swing:n'")
    parts = stop.lower().split(":")
    kind = parts[0]
    try:
        nums = [float(x) for x in parts[1:]]
    except ValueError:
        raise RuleError(f"plan.stop: cannot read {stop!r}") from None
    if kind == "atr" and len(nums) == 2 and nums[0] == int(nums[0]) and nums[0] > 0 \
            and nums[1] > 0:
        stop_c = ("atr", int(nums[0]), nums[1])
    elif kind == "pct" and len(nums) == 1 and 0 < nums[0] < 100:
        stop_c = ("pct", nums[0])
    elif kind == "swing" and len(nums) == 1 and nums[0] == int(nums[0]) and nums[0] > 0:
        stop_c = ("swing", int(nums[0]))
    else:
        raise RuleError(f"plan.stop: cannot read {stop!r}")
    tr = p.get("target_r")
    if isinstance(tr, bool) or not isinstance(tr, (int, float)) or not tr > 0:
        raise RuleError("plan.target_r must be a positive number")
    ts = p.get("time_stop")
    if ts is not None and (isinstance(ts, bool) or not isinstance(ts, int) or ts < 1):
        raise RuleError("plan.time_stop must be a positive integer")
    return {"stop": stop_c, "target_r": float(tr), "time_stop": ts}


def _plan_at(df: pd.DataFrame, frame: _Frame, plan: dict, side: str,
             t: int) -> dict | None:
    entry = float(df["close"].iat[t])
    kind = plan["stop"][0]
    if kind == "atr":
        _, n, k = plan["stop"]
        a = frame.value(("series", "atr", (n,), 0))[t]
        if not np.isfinite(a) or a <= 0:
            return None
        dist = k * a
        stop = entry - dist if side == "long" else entry + dist
    elif kind == "pct":
        dist = entry * plan["stop"][1] / 100.0
        stop = entry - dist if side == "long" else entry + dist
    else:
        n = plan["stop"][1]
        lo = max(0, t - n + 1)
        if side == "long":
            stop = float(df["low"].iloc[lo:t + 1].min())
        else:
            stop = float(df["high"].iloc[lo:t + 1].max())
    risk = (entry - stop) if side == "long" else (stop - entry)
    if not np.isfinite(risk) or risk <= 0:
        return None       # degenerate (e.g. swing low AT the close): no plan
    target = entry + plan["target_r"] * risk if side == "long" \
        else entry - plan["target_r"] * risk
    out = {"entry": round(entry, 4), "stop": round(stop, 4),
           "target": round(target, 4)}
    if plan["time_stop"]:
        out["time_stop"] = plan["time_stop"]
    return out


# ── the compiled rule ─────────────────────────────────────────────────────────

class Rule:
    def __init__(self, raw: dict):
        if not isinstance(raw, dict):
            raise RuleError("a rule must be an object")
        known = {"name", "hypothesis", "side", "steps", "invalidate",
                 "restart_on_step1", "plan", "notes"}
        unknown = set(raw) - known
        if unknown:
            raise RuleError(f"unknown rule key(s) {sorted(unknown)}")
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise RuleError("rule needs a non-empty 'name'")
        self.name = name.strip()
        self.side = raw.get("side", "long")
        if self.side not in SIDES:
            raise RuleError(f"side must be one of {SIDES}")
        steps = raw.get("steps")
        if not isinstance(steps, list) or not steps:
            raise RuleError("rule needs a non-empty 'steps' list")
        self.steps = [_compile_step(s, i) for i, s in enumerate(steps)]
        inv = raw.get("invalidate") or []
        if not isinstance(inv, list):
            raise RuleError("'invalidate' must be a list of conditions")
        self.invalidate = [_compile_condition(c, f"invalidate[{j}]")
                           for j, c in enumerate(inv)]
        r1 = raw.get("restart_on_step1", False)
        if not isinstance(r1, bool):
            raise RuleError("'restart_on_step1' must be true or false")
        self.restart_on_step1 = r1
        self.plan = _compile_plan(raw.get("plan"))
        self.hypothesis = (raw.get("hypothesis") or "").strip()
        self.raw = raw

    # Logic only: renaming a rule or rewording its hypothesis is not a new
    # variant; changing a threshold is.
    def logic_hash(self) -> str:
        logic = {k: self.raw.get(k) for k in
                 ("side", "steps", "invalidate", "restart_on_step1", "plan")}
        blob = json.dumps(logic, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:12]

    def fire_mask(self, df: pd.DataFrame, frame: _Frame | None = None) -> np.ndarray:
        frame = frame or _Frame(df)
        masks = [_step_mask(frame, s) for s in self.steps]
        inv = None
        if self.invalidate:
            inv = np.zeros(frame.n, dtype=bool)
            for c in self.invalidate:
                inv |= _eval_condition(frame, c)
        within = [s["within"] for s in self.steps]
        return run_sequence(masks, within, inv, self.restart_on_step1)

    def prepare(self, df: pd.DataFrame) -> Callable[[int], dict | None]:
        """Once per symbol: compute everything, return ``hit_at(t)``."""
        frame = _Frame(df)
        fire = self.fire_mask(df, frame)

        def hit_at(t: int) -> dict | None:
            if t < 0 or t >= frame.n or not fire[t]:
                return None
            hit: dict[str, Any] = {"rule": self.name, "side": self.side}
            if self.plan:
                p = _plan_at(df, frame, self.plan, self.side, t)
                if p:
                    hit.update(p)
            return hit
        return hit_at

    def scan(self, df: pd.DataFrame) -> dict | None:
        """The ordinary scanner signature (last bar of ``df``). Slow when called
        bar by bar — the harness uses ``prepare`` instead."""
        if df is None or df.empty:
            return None
        return self.prepare(df.reset_index(drop=True))(len(df) - 1)

    def scanner_spec(self) -> dict:
        return {"fn": self.scan, "prepare": self.prepare,
                "description": (f"User rule ({self.side}, {len(self.steps)} step(s)). "
                                f"Hypothesis: {self.hypothesis or '— none given —'} "
                                "UNMEASURED unless a rule_runner run says otherwise."),
                "category": "Rule"}


def compile_rule(raw: dict) -> Rule:
    return Rule(raw)


def load_rule(path) -> Rule:
    with open(path, encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as e:
            raise RuleError(f"{path}: not valid JSON ({e})") from None
    return Rule(raw)


def register(rule: Rule) -> str:
    """Put ``rule`` into ``scanner_templates.SCANNERS`` for this process only, so
    every harness entry point can replay it by name. Never written to disk."""
    name = RULE_PREFIX + rule.name
    sc.SCANNERS[name] = rule.scanner_spec()
    return name
