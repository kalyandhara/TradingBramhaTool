#!/usr/bin/env python3
"""
market_health.py — Filter A of the Crash-Proof 3-Filter System (DS-1).

What this is
------------
The framework in wiki/strategies/Crash-Proof-3-Filter-System.md gates the whole
trading day on FIVE named market conditions, and stands you down when **two or
more fail**:

    1. NIFTY above its 50 EMA
    2. Breadth positive
    3. Breakouts working (recent breakouts still holding)
    4. Leaders strong
    5. Volatility low

`market_verdict.py` already runs a 2+-caution ladder, but on different inputs
(200 SMA, PMax, sector participation, A/D) — it answers "how does the composite
feel" rather than "do the framework's five conditions hold". Three of the five
were unmodelled anywhere in the repo. This module models all five by name, so a
STAND DOWN can be argued with *per condition* instead of in aggregate.

Deliberately NOT wired into the overview ribbon's verdict
---------------------------------------------------------
Breadth and regime feed both engines; adding this gate's failures to
`build_verdict`'s caution list would count the same weakness twice and make the
ribbon strictly harsher for reasons no lamp explains. Fusing the two is DS-3's
job (the market × ownership matrix), where the interaction is the point. Until
then this is a second opinion shown beside the verdict, not folded into it.

Three states, never two
-----------------------
Every condition returns PASS / FAIL / **NOT_CHECKED**. A condition we could not
measure must not read as one that held — the same discipline as the three-state
red flags in red_flags.py. NOT_CHECKED never counts toward the 2-fail gate, and
the verdict always reports how many of the five were actually checked, so a
"CLEAR" built on two conditions cannot pass itself off as a clean bill.

Cost
----
Conditions 1, 2 and 5 are nearly free: one ^NSEI fetch, one ^INDIAVIX fetch, and
the advance/decline counts already persisted by the daily sentiment reading.
Conditions 3 and 4 need a basket of individual stocks (the same bhavcopy
top-by-traded-value universe the Opportunity Hub uses), so they are opt-in —
`evaluate()` reports them NOT_CHECKED unless a basket is supplied.
"""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any, Callable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scanner_templates as sc
import market_verdict as mv

log = logging.getLogger("market_health")

PASS        = "PASS"
FAIL        = "FAIL"
NOT_CHECKED = "NOT_CHECKED"

#: The framework's own rule: two failures cancel the day.
STAND_DOWN_FAILS = 2

# ── Thresholds ────────────────────────────────────────────────────────────────
# Starting points, not truths — the same caveat market_verdict carries. None of
# these are backtested; see the Backtest note in the Crash-Proof strategy page.
EMA_LEN               = 50     # condition 1: NIFTY vs its 50 EMA
BREADTH_MIN           = 0.50   # condition 2: share of advancing stocks

BREAKOUT_WINDOW       = 20     # condition 3: a close above the prior N-day high…
BREAKOUT_LOOKBACK     = 10     # …that happened within the last N sessions
BREAKOUTS_HOLDING_MIN = 0.50   # …and this share must still be holding it
MIN_BREAKOUTS         = 5      # below this, the sample is too small to judge

LEADER_QUANTILE       = 0.80   # condition 4: top 20% by trailing RS are "leaders"
MIN_LEADERS           = 5
LEADER_EMA_LEN        = 21
LEADERS_HOLDING_MIN   = 0.60   # share of leaders that must hold their 21 EMA

# condition 5: elevated only when high against its OWN habit AND high outright.
# A ratio test alone flips on any uptick from a calm baseline — the same trap
# market_verdict.classify_regime documents for realized vol.
VIX_HOT_RATIO         = 1.20
VIX_ABS_FLOOR         = 15.0
VIX_BASELINE_DAYS     = 90

#: A basket check needs this share of its symbols to actually return data,
#: otherwise it is measuring whichever names happened to survive the fetch.
MIN_BASKET_COVERAGE   = 0.50

CONDITION_LABELS = {
    "nifty_above_50ema": "NIFTY above 50 EMA",
    "breadth_positive":  "Breadth positive",
    "breakouts_working": "Breakouts working",
    "leaders_strong":    "Leaders strong",
    "volatility_low":    "Volatility low",
}


def _cond(key: str, state: str, reading: str, **detail) -> dict[str, Any]:
    return {"key": key, "label": CONDITION_LABELS[key], "state": state,
            "reading": reading, "detail": detail}


def _closes(df) -> pd.Series | None:
    """Close series with NaN bars dropped.

    yfinance hands back a stub bar for an unfinished session; every comparison
    against a NaN last close silently returns False, which would read here as a
    failed condition rather than as missing data.
    """
    if df is None or getattr(df, "empty", True):
        return None
    col = "close" if "close" in df.columns else ("Close" if "Close" in df.columns else None)
    if not col:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return s if len(s) else None


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


# ── 1 · NIFTY above its 50 EMA ────────────────────────────────────────────────
def check_nifty_above_50ema(nifty_df) -> dict[str, Any]:
    c = _closes(nifty_df)
    if c is None or len(c) < EMA_LEN:
        return _cond("nifty_above_50ema", NOT_CHECKED,
                     "NIFTY history unavailable — not assessed.")
    last = float(c.iloc[-1])
    ema = float(_ema(c, EMA_LEN).iloc[-1])
    dist = (last / ema - 1) * 100.0
    state = PASS if last > ema else FAIL
    return _cond("nifty_above_50ema", state,
                 f"NIFTY {last:,.0f} vs 50 EMA {ema:,.0f} ({dist:+.2f}%)",
                 close=round(last, 2), ema=round(ema, 2), dist_pct=round(dist, 2))


# ── 2 · Breadth positive ──────────────────────────────────────────────────────
def check_breadth(sentiment_reading: dict[str, Any] | None) -> dict[str, Any]:
    """Read the advance/decline counts off the persisted sentiment reading.

    Recomputing them means another full bhavcopy pull for numbers the daily
    sentiment job already stored; market_verdict makes the same call for the
    same reason.
    """
    inputs = (sentiment_reading or {}).get("inputs") or {}
    ad = inputs.get("advance_decline") or {}
    adv, dec = ad.get("advances"), ad.get("declines")
    try:
        adv, dec = int(adv), int(dec)
    except (TypeError, ValueError):
        return _cond("breadth_positive", NOT_CHECKED,
                     "No sentiment reading — refresh Market Sentiment for breadth.")
    total = adv + dec
    if total <= 0:
        return _cond("breadth_positive", NOT_CHECKED,
                     "Advance/decline counts are empty — not assessed.")
    share = adv / total
    state = PASS if share > BREADTH_MIN else FAIL
    return _cond("breadth_positive", state,
                 f"{adv:,} advancing vs {dec:,} declining ({share:.0%} advancing)",
                 advances=adv, declines=dec, share=round(share, 4),
                 as_of=(sentiment_reading or {}).get("reading_date"))


# ── 3 · Breakouts working ─────────────────────────────────────────────────────
def _breakout_state(c: pd.Series) -> tuple[bool, bool]:
    """(broke_out_recently, still_holding) for one name.

    A breakout is a close above the prior `BREAKOUT_WINDOW`-day high (the rolling
    max is shifted, so a bar cannot break out over itself). "Holding" asks only
    that price has not given the breakout close back — the plainest reading of
    "breakouts are working" that does not smuggle in a target.
    """
    if len(c) < BREAKOUT_WINDOW + BREAKOUT_LOOKBACK + 1:
        return False, False
    prior_high = c.rolling(BREAKOUT_WINDOW).max().shift(1)
    broke = (c > prior_high).tail(BREAKOUT_LOOKBACK)
    if not bool(broke.any()):
        return False, False
    last_bo_idx = broke[broke].index[-1]
    return True, float(c.iloc[-1]) >= float(c.loc[last_bo_idx])


def check_breakouts_working(frames: dict[str, Any] | None,
                            requested: int | None = None) -> dict[str, Any]:
    if not frames:
        return _cond("breakouts_working", NOT_CHECKED,
                     "Needs a stock basket — run the basket checks.")
    requested = requested or len(frames)
    if requested and len(frames) / requested < MIN_BASKET_COVERAGE:
        return _cond("breakouts_working", NOT_CHECKED,
                     f"Only {len(frames)}/{requested} names returned data — "
                     f"too thin to judge.", covered=len(frames), requested=requested)

    broke = held = 0
    for c in (_closes(f) for f in frames.values()):
        if c is None:
            continue
        did, holding = _breakout_state(c)
        if did:
            broke += 1
            held += int(holding)
    if broke < MIN_BREAKOUTS:
        # A tape with almost no breakouts is telling you something, but it is not
        # evidence that breakouts fail — say so rather than scoring the silence.
        return _cond("breakouts_working", NOT_CHECKED,
                     f"Only {broke} breakout(s) in {len(frames)} names over the last "
                     f"{BREAKOUT_LOOKBACK} sessions — too few to judge.",
                     breakouts=broke, universe=len(frames))
    share = held / broke
    state = PASS if share >= BREAKOUTS_HOLDING_MIN else FAIL
    return _cond("breakouts_working", state,
                 f"{held}/{broke} recent breakouts still holding ({share:.0%})",
                 breakouts=broke, holding=held, share=round(share, 4),
                 universe=len(frames))


# ── 4 · Leaders strong ────────────────────────────────────────────────────────
def check_leaders_strong(frames: dict[str, Any] | None,
                         requested: int | None = None) -> dict[str, Any]:
    """Leadership = the top quintile by the SAME trailing-RS primitive the
    scanners and the Opportunity Hub rank with, so "leader" means one thing
    across the app. Strong = still trading above its 21 EMA."""
    if not frames:
        return _cond("leaders_strong", NOT_CHECKED,
                     "Needs a stock basket — run the basket checks.")
    requested = requested or len(frames)
    if requested and len(frames) / requested < MIN_BASKET_COVERAGE:
        return _cond("leaders_strong", NOT_CHECKED,
                     f"Only {len(frames)}/{requested} names returned data — "
                     f"too thin to judge.", covered=len(frames), requested=requested)

    scored: list[tuple[str, float, pd.Series]] = []
    for sym, f in frames.items():
        c = _closes(f)
        if c is None or len(c) < max(LEADER_EMA_LEN, 30):
            continue
        try:
            rs = sc._weighted_trailing_return(c)
        except Exception:
            rs = None
        if rs is None or pd.isna(rs):
            continue
        scored.append((sym, float(rs), c))
    if len(scored) < MIN_LEADERS:
        return _cond("leaders_strong", NOT_CHECKED,
                     f"Only {len(scored)} names had a computable RS — not assessed.",
                     scored=len(scored))

    scored.sort(key=lambda t: t[1], reverse=True)
    n_lead = max(MIN_LEADERS, int(round(len(scored) * (1 - LEADER_QUANTILE))))
    leaders = scored[:n_lead]
    holding = sum(1 for _, _, c in leaders
                  if float(c.iloc[-1]) > float(_ema(c, LEADER_EMA_LEN).iloc[-1]))
    share = holding / len(leaders)
    state = PASS if share >= LEADERS_HOLDING_MIN else FAIL
    return _cond("leaders_strong", state,
                 f"{holding}/{len(leaders)} leaders above their {LEADER_EMA_LEN} EMA "
                 f"({share:.0%})",
                 leaders=len(leaders), holding=holding, share=round(share, 4),
                 top=[s for s, _, _ in leaders[:5]])


# ── 5 · Volatility low ────────────────────────────────────────────────────────
def check_volatility_low(vix_df=None, nifty_df=None) -> dict[str, Any]:
    """India VIX against its own 90-day median, with an absolute floor.

    Falls back to the realized-vol regime read in market_verdict when the VIX
    fetch fails, and says which one it used — a volatility lamp that quietly
    changed its definition would be worse than one that admits it.
    """
    c = _closes(vix_df)
    if c is not None and len(c) >= 20:
        last = float(c.iloc[-1])
        base = float(c.tail(VIX_BASELINE_DAYS).median())
        hot = (last >= base * VIX_HOT_RATIO) and (last >= VIX_ABS_FLOOR)
        return _cond("volatility_low", FAIL if hot else PASS,
                     f"India VIX {last:.2f} vs {VIX_BASELINE_DAYS}d median "
                     f"{base:.2f}" + (" — elevated" if hot else " — calm"),
                     vix=round(last, 2), baseline=round(base, 2), source="India VIX")

    regime = mv.classify_regime(nifty_df)
    if regime.get("vol") is None:
        return _cond("volatility_low", NOT_CHECKED,
                     "India VIX unavailable and NIFTY history too short — not assessed.")
    hot = regime.get("label") == "VOLATILE"
    return _cond("volatility_low", FAIL if hot else PASS,
                 f"India VIX unavailable — realized vol {regime['vol']:.1f}% vs "
                 f"baseline {regime['vol_baseline']:.1f}%"
                 + (" — elevated" if hot else " — calm"),
                 vol=regime.get("vol"), baseline=regime.get("vol_baseline"),
                 source="realized vol (VIX fallback)")


# ── Basket loading (conditions 3 + 4 share one fetch) ─────────────────────────
def load_basket(symbols: list[str], fetch_ohlcv: Callable,
                *, max_workers: int = 4, progress_cb=None) -> dict[str, Any]:
    """Fetch the basket once for both stock-level conditions.

    4 workers, not 8: the Opportunity Hub's fan-out at 8 drew HTTP 401 "Invalid
    Crumb" from Yahoo and returned a half-empty result that looked like a market
    reading. Coverage is checked by the callers above for the same reason.
    """
    out: dict[str, Any] = {}
    total, done = len(symbols), 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fetch_ohlcv, s): s for s in symbols}
        for fut in as_completed(futures):
            sym = futures[fut]
            done += 1
            if progress_cb is not None:
                try:
                    progress_cb(done, total)
                except Exception:
                    pass
            try:
                df = fut.result()
            except Exception:
                df = None
            if df is not None and not getattr(df, "empty", True):
                out[sym] = df
    return out


def fetch_indices() -> tuple[Any, Any]:
    """(nifty_df, vix_df) — the two index frames conditions 1 and 5 need.

    Exposed separately from `evaluate` so a caller with its own cache (the
    dashboard) can pay for these once per session rather than per rerun.
    """
    return _fetch_index("^NSEI", "1y"), _fetch_index("^INDIAVIX", "6mo")


def _fetch_index(ticker: str, period: str) -> Any:
    try:
        import yfinance as yf
        h = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
        return None if h is None else h.dropna(subset=["Close"])
    except Exception as e:
        log.warning("%s fetch failed: %s", ticker, e)
        return None


# ── The gate ──────────────────────────────────────────────────────────────────
def evaluate(*, nifty_df=None, vix_df=None, sentiment_reading=None,
             basket_frames=None, basket_requested: int | None = None,
             fetch_indices: bool = True) -> dict[str, Any]:
    """Run the five conditions and apply the 2-of-5 gate.

    Every input is injectable so this is testable without a network, and so the
    dashboard can hand over frames it has already cached. With `fetch_indices`
    the missing index frames are pulled here.
    """
    if nifty_df is None and fetch_indices:
        nifty_df = _fetch_index("^NSEI", "1y")
    if vix_df is None and fetch_indices:
        vix_df = _fetch_index("^INDIAVIX", "6mo")

    conditions = [
        check_nifty_above_50ema(nifty_df),
        check_breadth(sentiment_reading),
        check_breakouts_working(basket_frames, basket_requested),
        check_leaders_strong(basket_frames, basket_requested),
        check_volatility_low(vix_df, nifty_df),
    ]

    n_fail = sum(1 for c in conditions if c["state"] == FAIL)
    n_pass = sum(1 for c in conditions if c["state"] == PASS)
    n_unchecked = sum(1 for c in conditions if c["state"] == NOT_CHECKED)
    n_checked = n_pass + n_fail
    stand_down = n_fail >= STAND_DOWN_FAILS

    # Nothing measured is NOT a clear gate. Returning CLEAR here would be the
    # exact failure market_verdict guards against: a green light nobody computed.
    if n_checked == 0:
        verdict = "NOT ASSESSED"
        instruction = ("None of the five conditions could be measured — this says "
                       "nothing about the market, only that the inputs are missing.")
    elif stand_down:
        verdict = "STAND DOWN"
        instruction = ("Filter A fails — no trades today, regardless of how good "
                       "any individual setup looks.")
    else:
        verdict = "CLEAR"
        parts = []
        if n_fail:
            parts.append(f"{n_fail} condition failed — one more cancels the day")
        if n_unchecked:
            parts.append(f"{n_unchecked} could not be measured, so this is a partial "
                         f"reading, not a green light")
        instruction = ("The market-health gate is open. " + "; ".join(parts) + "."
                       if parts else
                       "All five conditions measured and none failed — the gate is open.")

    return {
        "verdict": verdict,
        "conditions": conditions,
        "n_fail": n_fail, "n_pass": n_pass, "n_unchecked": n_unchecked,
        "n_checked": n_checked,
        "instruction": instruction,
        "rule": f"{STAND_DOWN_FAILS} or more of the 5 conditions fail → STAND DOWN",
        "as_of": date.today().isoformat(),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> int:
    import argparse
    import screener_pipeline as sp
    import sentiment_index as senti

    ap = argparse.ArgumentParser(description="Crash-Proof Filter A — market health gate")
    ap.add_argument("--basket", type=int, default=0,
                    help="stocks to fetch for the breakouts/leaders conditions "
                         "(0 = skip them, the default)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    reading = None
    try:
        hist = senti.history(days=1)
        if not hist.empty:
            import json
            row = hist.iloc[-1]
            reading = {"reading_date": row["reading_date"].date().isoformat(),
                       "inputs": json.loads(row["inputs_json"])}
    except Exception as e:
        log.warning("no persisted sentiment reading: %s", e)

    frames, requested = None, None
    if args.basket > 0:
        symbols = sp.fetch_bhavcopy_top_volume(args.basket)
        requested = len(symbols)
        print(f"Fetching {requested} symbols for the basket conditions…")
        frames = load_basket(symbols, lambda s: sp.fetch_ohlcv(s, days=260))
        print(f"  {len(frames)}/{requested} returned data.")

    res = evaluate(sentiment_reading=reading, basket_frames=frames,
                   basket_requested=requested)
    mark = {PASS: "PASS ", FAIL: "FAIL ", NOT_CHECKED: "  -  "}
    print(f"\nFilter A — market health · {res['as_of']}")
    for c in res["conditions"]:
        print(f"  [{mark[c['state']]}] {c['label']:<20} {c['reading']}")
    print(f"\n  {res['verdict']} — {res['n_fail']} failed of {res['n_checked']} checked"
          + (f", {res['n_unchecked']} not checked" if res["n_unchecked"] else ""))
    print(f"  {res['instruction']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
