"""exit_plan.py — profit-booking engine composing only measured exit rules.

LuxAlgo Risk & Exits step 7.  The desk has accumulated several exit
measurements; they are scattered across individual study files.  This module
is the single point of truth that maps a scanner to the exit configuration
that evidence supports, and flags when that evidence is thin or pending.

== Design contract ==

  compose_exit_plan(scanner, card, df) -> ExitPlanResult

  A result is ALWAYS returned.  If no measured rule exists for the scanner,
  the card's own plan is returned as DEFAULT — the caller is never left without
  numbers.  `verdict_level` says how much evidence stands behind it:

      MEASURED    a BEATS or POSITIVE study exists for this scanner / rule
      PROMOTED    a POSITIVE study exists (single-panel, not Bonferroni-pooled)
      DEFAULT     no exit-rule measurement; card's own levels used unchanged
      GEOMETRY    the card's plan has degenerate levels (zero risk, etc.)

  `pending` lists studies that are pre-registered but UNRECORDED and whose
  result could change the recommendation.  It is for display only — it never
  changes the returned rule.

== Evidence registry ==

  _RULES maps scanner name → ExitRule.  A scanner MUST have a BEATS or
  POSITIVE verdict in named_studies before an entry appears here.  Every entry
  carries the study item that backs it.  When a future study upgrades a rule,
  update the entry AND add the new item to `basis`.

  Scanners not in the registry fall through to DEFAULT.

== ATR convention ==

  "ATR14" throughout means the 14-bar Average True Range on daily bars,
  computed from the bars UP TO AND INCLUDING the signal bar.  This matches
  the convention in scanner_templates (ATR_N = 14) and backtest.py.

== What this is NOT ==

  This module does not backtest, does not modify the scanner, and does not
  change any entry rule.  `compose_exit_plan` is a read-only recommender.
  The caller is responsible for applying the returned stop / exit_model to
  an actual trade.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

VerdictLevel = Literal["MEASURED", "PROMOTED", "DEFAULT", "GEOMETRY"]


@dataclass
class ExitRule:
    """A single measured exit rule for one scanner."""
    scanner: str
    stop_formula: str           # human-readable description
    exit_model: str             # "fixed", "breakeven:k", etc. — backtest.py keys
    exit_model_param: float | None = None   # k for breakeven, n for ema_close, etc.
    basis: list[str] = field(default_factory=list)   # named_studies items
    verdict_level: VerdictLevel = "MEASURED"
    note: str = ""


@dataclass
class ExitPlanResult:
    """What compose_exit_plan() returns."""
    scanner: str
    stop_formula: str
    exit_model: str
    exit_model_param: float | None
    verdict_level: VerdictLevel
    basis: list[str]
    note: str
    pending: list[str]          # pre-registered studies that may update this
    # Computed stop price (None when df is not supplied or computation fails)
    stop_price: float | None = None
    entry: float | None = None
    target: float | None = None


# ---------------------------------------------------------------------------
# Evidence registry — only scanners with BEATS or POSITIVE studies
# ---------------------------------------------------------------------------

_RULES: dict[str, ExitRule] = {
    # B-183i (BEATS, 2026-11-19): wider stop wick_low−1.5×ATR for Liquidity Sweep.
    # The shipped wick_low stop had 64.9% noise_stop_share and returned −0.06R
    # (B-41p NEGATIVE).  Widening to wick_low−1.5×ATR gives +0.126R (p=0.0008).
    # B-205 (breakeven:k) and B-206 (disaster stop) are pre-registered pending —
    # they may add a secondary rule once measured.
    "Liquidity Sweep": ExitRule(
        scanner="Liquidity Sweep",
        stop_formula="wick_low - 1.5 * ATR14",
        exit_model="fixed",
        exit_model_param=None,
        basis=["B-183i"],
        verdict_level="MEASURED",
        note="B-41p: shipped stop destroys edge; B-183i: wider stop +0.126R",
    ),
    # B-132 (POSITIVE, 2026-10-14): AB=CD pattern stop at D−2×ATR14 gives
    # +0.56%/trade vs +0.01% at the card's own D−0.5% stop (p=0.0019,
    # 1,385 trades, 183 symbols).  Shipped as A2 for Harmonic Reversal (XABCD).
    # B-132r confirmed the tier holds with the new stop on the out-of-sample
    # nifty500 first-300 panel.
    "Harmonic Reversal (XABCD)": ExitRule(
        scanner="Harmonic Reversal (XABCD)",
        stop_formula="D - 2.0 * ATR14",
        exit_model="fixed",
        exit_model_param=None,
        basis=["B-132", "B-132r"],
        verdict_level="PROMOTED",   # single-panel positive, not Bonferroni-pooled
        note="B-132: D-2×ATR14 stop +0.56%/trade vs card's D-0.5% (p=0.0019)",
    ),
}

# Pre-registered studies that could update specific scanners when they run.
# Key = scanner name; value = list of UNRECORDED study items.
_PENDING: dict[str, list[str]] = {
    "Liquidity Sweep": ["B-205", "B-206"],   # breakeven:k and disaster stop
    "Falling Wedge":   ["B-205"],             # breakeven:k also covers FW
    "Harmonic Reversal (XABCD)": ["B-205"],
}

# Trail arms: none beat fixed (B-124).  Explicitly excluded so callers
# looking at the registry know this was checked, not overlooked.
_TRAILS_REJECTED: dict[str, list[str]] = {
    "Falling Wedge":           ["B-124"],
    "Harmonic Reversal (XABCD)": ["B-124"],
}


# ---------------------------------------------------------------------------
# ATR helper
# ---------------------------------------------------------------------------

def _atr14(df: pd.DataFrame) -> float | None:
    """14-bar ATR from bars up to the last row (the signal bar)."""
    if df is None or len(df) < 2:
        return None
    hi = df["high"].values
    lo = df["low"].values
    cl = df["close"].values
    trs = []
    for i in range(1, len(df)):
        trs.append(max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1])))
    n = min(14, len(trs))
    return float(sum(trs[-n:]) / n) if n else None


def _wick_low(df: pd.DataFrame, card: dict) -> float | None:
    """The low of the swept bar for Liquidity Sweep plans."""
    # scanner_templates stores it in the card as 'swept_low' or 'wick_low'
    for key in ("wick_low", "swept_low", "stop_reference"):
        v = card.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    # Fall back to the second-to-last bar's low as a reasonable proxy
    if df is not None and len(df) >= 2:
        return float(df["low"].iloc[-2])
    return None


def _d_level(card: dict) -> float | None:
    """The D-point price for Harmonic XABCD plans."""
    for key in ("d_price", "d_level", "d_point", "stop"):
        v = card.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_exit_plan(
    scanner: str,
    card: dict,
    df: pd.DataFrame | None = None,
) -> ExitPlanResult:
    """Return the evidence-backed exit configuration for this scanner / card.

    Parameters
    ----------
    scanner:  scanner name, e.g. "Falling Wedge"
    card:     scanner card dict (entry, stop, target, and scanner-specific keys)
    df:       daily OHLCV up to and including the signal bar — required for
              stop price computation; pass None to skip price computation

    Returns
    -------
    ExitPlanResult with stop_formula, exit_model, verdict_level, basis,
    pending, and (when df is supplied) the computed stop_price.
    """
    pending = _PENDING.get(scanner, [])

    # Validate card geometry
    try:
        entry = float(card.get("entry") or 0)
        stop_card = float(card.get("stop") or 0)
        target = float(card.get("target") or 0)
    except (TypeError, ValueError):
        entry = stop_card = target = 0.0
    risk = abs(entry - stop_card)

    if entry <= 0 or risk <= 0:
        return ExitPlanResult(
            scanner=scanner,
            stop_formula="card_stop",
            exit_model="fixed",
            exit_model_param=None,
            verdict_level="GEOMETRY",
            basis=[],
            note="card has degenerate levels (zero or missing entry/stop)",
            pending=pending,
            stop_price=stop_card or None,
            entry=entry or None,
            target=target or None,
        )

    rule = _RULES.get(scanner)

    if rule is None:
        # No measured rule — use the card's own plan
        return ExitPlanResult(
            scanner=scanner,
            stop_formula="card_stop",
            exit_model="fixed",
            exit_model_param=None,
            verdict_level="DEFAULT",
            basis=[],
            note="no exit rule measured for this scanner; card's own plan unchanged",
            pending=pending,
            stop_price=stop_card,
            entry=entry,
            target=target,
        )

    # Compute stop price from the measured formula
    stop_price: float | None = None
    if df is not None:
        atr = _atr14(df)
        if rule.scanner == "Liquidity Sweep" and atr is not None:
            wl = _wick_low(df, card)
            if wl is not None:
                stop_price = round(wl - 1.5 * atr, 2)
        elif rule.scanner == "Harmonic Reversal (XABCD)" and atr is not None:
            d = _d_level(card)
            if d is not None:
                stop_price = round(d - 2.0 * atr, 2)

    if stop_price is None:
        stop_price = stop_card   # fall back to card's own stop

    return ExitPlanResult(
        scanner=scanner,
        stop_formula=rule.stop_formula,
        exit_model=rule.exit_model,
        exit_model_param=rule.exit_model_param,
        verdict_level=rule.verdict_level,
        basis=list(rule.basis),
        note=rule.note,
        pending=pending,
        stop_price=stop_price,
        entry=entry,
        target=target,
    )


def summary(scanner: str) -> str:
    """One-line evidence summary for a scanner's exit rule."""
    rule = _RULES.get(scanner)
    pending = _PENDING.get(scanner, [])
    pending_str = f"  pending: {', '.join(pending)}" if pending else ""
    if rule is None:
        trails = _TRAILS_REJECTED.get(scanner, [])
        t_str = f" (trails rejected: {', '.join(trails)})" if trails else ""
        return f"{scanner}: DEFAULT — no measured exit rule{t_str}{pending_str}"
    return (f"{scanner}: {rule.verdict_level} — {rule.stop_formula} "
            f"[{', '.join(rule.basis)}]{pending_str}")
