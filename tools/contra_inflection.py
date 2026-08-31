#!/usr/bin/env python3
"""
contra_inflection.py — B-50: a CONTRA screen for margin/earnings inflection.

Where :mod:`value_screen` (B-49) looks for businesses that are **already good and
cheap**, this looks for the opposite shape: businesses whose *trailing* numbers
are mediocre — so a quality-value screen rejects them — but whose *most recent*
numbers have turned. The signal is **change, not level**. Everything is derived
from free data (yfinance statements), no screener.in cookie.

Why the level/change distinction is the whole design
----------------------------------------------------
Run OCCL Ltd through :mod:`value_screen` and it fails: ROCE 11.6% and ROE 11.1%
are below any sane quality bar. Yet its June-2026 quarter shows OPM 25.6% against
16.0% a year earlier and PAT up 206%. A level screen cannot see that, because the
annual frame averages the bad quarters in. A contra screen has to read the
*quarterly* series, which is why this module added quarterly OPM to
``fundamentals_deep._quarterly_history``.

The four traps this module exists to avoid
------------------------------------------
A naive "profit up 200%" filter finds mostly garbage. Each guard below is a
separate, reported test rather than a term folded into one score:

1. **Low base.** +206% off a collapsed quarter is arithmetic, not a turnaround.
   Two independent tests: ``base_depressed`` (was the year-ago quarter below the
   trailing median?) and ``new_high_pat`` (is the latest quarter above *every*
   prior quarter, i.e. a genuine new high rather than a return to trend?).
2. **One-off gains.** A jump driven by other income, asset sales or a tax writeback
   moves PAT without moving EBIT. ``operating_led`` requires EBIT to grow at least
   as fast as PAT.
3. **Accounting profit without cash.** ``cash_backed`` uses the existing
   ``cfo_pat_ratio`` (sum OCF / sum PAT over up to five matched years).
4. **One good quarter.** ``persistence_q`` counts consecutive sequential OPM
   improvements. One quarter is noise.

> [!warning] Sequential persistence is seasonality-exposed, and that is stated.
> yfinance returns ~5-6 quarters, and ``_year_ago_index`` only matches a year-ago
> quarter for the newest one or two. So persistence is measured **quarter-on-
> quarter**, which in a seasonal business reads seasonality as improvement. It is
> reported as a count, never as a pass/fail, precisely because it cannot be
> cleaned up with the data available.

Grounding, and its limit
------------------------
The drift half of the thesis is real: post-earnings-announcement drift is
documented in Indian equities over 2002-2017 and survives controls for beta, size,
book-to-market, illiquidity and idiosyncratic volatility. That is evidence that
*prices under-react to earnings surprises*. It is **not** evidence that this
particular combination of filters finds multibaggers, and nothing here has been
backtested.

> [!important] This is a candidate generator, not a recommendation engine.
> Output is a shortlist to go and read about. The verdict labels
> (``INFLECTING`` / ``RECOVERING`` / ``ONE_OFF_SUSPECT`` / ``SINGLE_QUARTER`` /
> ``NO_INFLECTION``) are descriptions of a data shape, not judgements about a
> business or its price. The measurement owed is a forward event study: buy at
> the first INFLECTING print, hold N days, against a matched non-inflecting
> control — the same shape of test ``funnel_backtest`` already runs.

Usage
-----
    from contra_inflection import classify, screen
    res = screen(limit=100)

    py -3 tools/contra_inflection.py --symbols OCCLLTD.NS --explain
    py -3 tools/contra_inflection.py --limit 120 --verdicts INFLECTING RECOVERING
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from typing import Any, Callable, Iterable

import fundamentals_deep as fd

log = logging.getLogger(__name__)

#: EBIT growth must be at least this fraction of PAT growth for the jump to count
#: as operating-led. Set low on purpose -- see `operating_led` in extract_signals:
#: the test is participation, not parity, because deleveraging and tax changes
#: legitimately make PAT outgrow EBIT.
EBIT_PARTICIPATION = 0.25

INFLECTING = "INFLECTING"
#: Margin improved but the top line did not. Cost-cutting or mix, not a rising
#: star -- separated from INFLECTING because conflating them is how a shrinking
#: business gets sold as a growth story.
MARGIN_LED = "MARGIN_LED"
RECOVERING = "RECOVERING"
ONE_OFF_SUSPECT = "ONE_OFF_SUSPECT"
SINGLE_QUARTER = "SINGLE_QUARTER"
NO_INFLECTION = "NO_INFLECTION"
#: The improvement is visible but the SAFETY CHECKS COULD NOT RUN -- typically a
#: loss-making base, which makes every growth percentage undefined and leaves
#: operating_led and cfo_pat_ratio as None. Deliberately not INFLECTING: an
#: unevaluated guard is not a passed guard.
UNVERIFIED = "UNVERIFIED"
INSUFFICIENT = "INSUFFICIENT_DATA"

#: Verdicts in the order a reader should work down them.
VERDICT_ORDER = (INFLECTING, MARGIN_LED, RECOVERING, SINGLE_QUARTER,
                 UNVERIFIED, ONE_OFF_SUSPECT, NO_INFLECTION, INSUFFICIENT)


@dataclass
class ContraParams:
    """Bounds. Parameters on purpose — none of these are measured optima.

    The defaults are deliberately loose: a contra screen that demands a large
    margin jump only finds names the market has already repriced. The job here is
    to *widen* the candidate set relative to :mod:`value_screen`, then let the
    guards throw out the arithmetic artefacts.
    """
    min_opm_gain_pp: float = 3.0      # latest quarter OPM minus its comparison base
    min_pat_yoy: float = 25.0         # latest quarter PAT growth, %
    min_persistence_q: int = 2        # consecutive sequential OPM improvements
    min_cfo_pat: float = 0.8          # sum OCF / sum PAT
    max_de: float | None = 1.5        # contra, not distressed
    min_interest_cover: float | None = 1.5
    min_quarters: int = 4             # below this there is no series to read

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ──────────────────────────────────────────────────────────────────────────────
# Signal extraction — pure, no network
# ──────────────────────────────────────────────────────────────────────────────
def _median(vals: list[float]) -> float | None:
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def extract_signals(payload: dict[str, Any]) -> dict[str, Any]:
    """Pull the inflection signals out of a derive_fundamentals payload.

    Returns ``{}`` when there is no quarterly series to read. Every field is
    either a number or None; nothing is imputed.
    """
    quarters = payload.get("quarters") or []
    # Newest first. Drop empty trailing columns yfinance sometimes returns.
    qs = [q for q in quarters if q.get("revenue") or q.get("net_income")]
    if len(qs) < 2:
        return {}

    latest, prior = qs[0], qs[1:]
    opm_now = latest.get("opm")

    # Comparison base for the margin, in preference order. The year-ago quarter
    # is the honest one; the trailing median is a fallback that compares across
    # seasons, so which was used is REPORTED rather than hidden.
    opm_base, opm_base_src = latest.get("opm_yoy_base"), "year_ago_q"
    if opm_base is None:
        opm_base, opm_base_src = _median([q.get("opm") for q in prior]), "prior_median"
    opm_gain = (None if (opm_now is None or opm_base is None)
                else round(opm_now - opm_base, 2))

    pats = [q.get("net_income") for q in qs]
    revs = [q.get("revenue") for q in qs]
    prior_pats = [v for v in pats[1:] if v is not None]
    prior_revs = [v for v in revs[1:] if v is not None]

    # Low-base tests, deliberately two of them measuring different things.
    new_high_pat = (None if (pats[0] is None or not prior_pats)
                    else bool(pats[0] > max(prior_pats)))
    new_high_rev = (None if (revs[0] is None or not prior_revs)
                    else bool(revs[0] > max(prior_revs)))
    med_pat = _median(prior_pats)
    # A loss anywhere in the comparison window makes every growth PERCENTAGE
    # undefined or meaningless, and is exactly the state in which the guards below
    # return None. Surfaced so `classify` can refuse rather than assume.
    loss_in_base = (None if not prior_pats else bool(min(prior_pats) <= 0))
    # A year-ago quarter below the trailing median means the YoY % is flattered by
    # the denominator. True does NOT disqualify -- a depressed base is what a
    # turnaround looks like -- it changes what the percentage MEANS.
    base_depressed = None
    if med_pat is not None and pats[0] is not None and latest.get("profit_yoy"):
        try:
            _yr_ago_pat = pats[0] / (1 + latest["profit_yoy"] / 100.0)
            base_depressed = bool(_yr_ago_pat < med_pat)
        except ZeroDivisionError:
            base_depressed = None

    # Operating-led? The question is whether OPERATING profit participated in the
    # jump -- NOT whether it kept pace with PAT. PAT outgrowing EBIT is normal and
    # often healthy: debt paid down shrinks the interest line, or the effective tax
    # rate falls. (The AGI Greenpac card's own pitch, "debt cut by over half", is
    # precisely that shape.) The one-off signature is EBIT barely moving while PAT
    # multiplies -- other income, an asset sale, a tax writeback.
    ebits = [q.get("ebit") for q in qs]
    operating_led = None
    if ebits[0] is not None:
        prior_ebit = _median([e for e in ebits[1:] if e is not None])
        if prior_ebit is not None and prior_ebit > 0:
            ebit_growth = ebits[0] / prior_ebit - 1
            pat_growth = ((pats[0] / med_pat - 1)
                          if (pats[0] is not None and med_pat and med_pat > 0) else None)
            if pat_growth is None or pat_growth <= 0:
                operating_led = None          # nothing to attribute
            else:
                operating_led = bool(ebit_growth >= EBIT_PARTICIPATION * pat_growth)

    # Sequential OPM improvement streak, newest backwards. Seasonality-exposed --
    # see the module docstring; reported as a count, never as a pass/fail.
    streak = 0
    for a, b in zip(qs, qs[1:]):
        if a.get("opm") is None or b.get("opm") is None:
            break
        if a["opm"] > b["opm"]:
            streak += 1
        else:
            break

    return {
        "quarters_seen":   len(qs),
        "latest_period":   latest.get("period"),
        "opm_now":         opm_now,
        "opm_base":        None if opm_base is None else round(opm_base, 2),
        "opm_base_source": opm_base_src,
        "opm_gain_pp":     opm_gain,
        "pat_yoy":         latest.get("profit_yoy"),
        "rev_yoy":         latest.get("revenue_yoy"),
        "new_high_pat":    new_high_pat,
        "new_high_rev":    new_high_rev,
        "base_depressed":  base_depressed,
        "loss_in_base":    loss_in_base,
        "operating_led":   operating_led,
        "persistence_q":   streak,
        "cfo_pat_ratio":   payload.get("cfo_pat_ratio"),
        "debt_to_equity":  payload.get("debt_to_equity"),
        "interest_coverage": payload.get("interest_coverage"),
    }


def classify(signals: dict[str, Any], p: ContraParams | None = None) -> dict[str, Any]:
    """Turn signals into a verdict plus the reasons for it.

    A **label, not a score.** The order of tests matters: disqualifiers are
    checked before merits, so a name is never called INFLECTING on the strength of
    a number that a later guard would have rejected.
    """
    p = p or ContraParams()
    reasons: list[str] = []

    if not signals or signals.get("quarters_seen", 0) < p.min_quarters:
        return {"verdict": INSUFFICIENT,
                "reasons": [f"only {signals.get('quarters_seen', 0)} usable quarters "
                            f"(need {p.min_quarters})"]}

    opm_gain = signals.get("opm_gain_pp")
    pat_yoy = signals.get("pat_yoy")
    improving = ((opm_gain is not None and opm_gain >= p.min_opm_gain_pp)
                 or (pat_yoy is not None and pat_yoy >= p.min_pat_yoy))
    if not improving:
        return {"verdict": NO_INFLECTION,
                "reasons": [f"OPM gain {opm_gain}pp and PAT YoY {pat_yoy}% both "
                            f"below thresholds"]}

    # ── Disqualifiers, checked first ────────────────────────────────────────────
    de, cover = signals.get("debt_to_equity"), signals.get("interest_coverage")
    if p.max_de is not None and de is not None and de > p.max_de:
        return {"verdict": ONE_OFF_SUSPECT,
                "reasons": [f"D/E {de} above {p.max_de} - distressed, not contra"]}
    if (p.min_interest_cover is not None and cover is not None
            and cover < p.min_interest_cover):
        return {"verdict": ONE_OFF_SUSPECT,
                "reasons": [f"interest cover {cover}x below {p.min_interest_cover}x"]}

    if signals.get("operating_led") is False:
        return {"verdict": ONE_OFF_SUSPECT,
                "reasons": ["operating profit barely moved while PAT jumped - the "
                            "gain came from below the operating line (other income "
                            "/ tax / exceptional), not from the business"]}
    cfo = signals.get("cfo_pat_ratio")
    if cfo is not None and cfo < p.min_cfo_pat:
        return {"verdict": ONE_OFF_SUSPECT,
                "reasons": [f"OCF/PAT {cfo} below {p.min_cfo_pat} - reported profit "
                            f"is not turning into cash"]}

    # Evidence gate. The two guards that distinguish a real turnaround from an
    # accounting event are `operating_led` and `cfo_pat_ratio`. If NEITHER could be
    # computed there is nothing behind the headline, so the name is reported as
    # UNVERIFIED rather than promoted on a margin number alone.
    if signals.get("operating_led") is None and cfo is None:
        why = ["neither the operating-led nor the cash-conversion check could be "
               "computed - the improvement is unverified, not confirmed"]
        if signals.get("loss_in_base"):
            why.append("a prior quarter in the window was loss-making, which makes "
                       "every growth percentage here undefined")
        return {"verdict": UNVERIFIED, "reasons": why}

    if signals.get("persistence_q", 0) < p.min_persistence_q:
        return {"verdict": SINGLE_QUARTER,
                "reasons": [f"only {signals.get('persistence_q', 0)} consecutive "
                            f"quarter(s) of margin improvement - not yet a trend"]}

    # ── Merits ──────────────────────────────────────────────────────────────────
    if opm_gain is not None:
        reasons.append(f"OPM {signals['opm_now']}% vs {signals['opm_base']}% "
                       f"({signals['opm_base_source']}), +{opm_gain}pp")
    if pat_yoy is not None:
        reasons.append(f"PAT +{pat_yoy}% YoY")
    if signals.get("persistence_q"):
        reasons.append(f"{signals['persistence_q']} consecutive quarters of "
                       f"margin improvement (sequential)")
    if cfo is not None:
        reasons.append(f"OCF/PAT {cfo}")

    # The line between a rising star and a rebound: is this a NEW high, or merely
    # a return to where the business already was? Both are contra; only one is a
    # "rising star", and conflating them is how a mean-reversion trade gets sold
    # as a growth story.
    if signals.get("new_high_pat") is False:
        reasons.append("latest PAT still below an earlier quarter - recovery "
                       "toward trend, not a breakout")
        if signals.get("base_depressed"):
            reasons.append("year-ago base was below the trailing median, so the "
                           "YoY % is flattered by the denominator")
        return {"verdict": RECOVERING, "reasons": reasons}

    if signals.get("new_high_pat"):
        reasons.append("latest PAT above every prior quarter in the window")

    # Margin up while the top line is flat or shrinking is cost-cutting or mix.
    # It can be a fine business outcome and it is NOT a rising star, so it gets
    # its own label instead of sharing one.
    rev_yoy = signals.get("rev_yoy")
    growing = (signals.get("new_high_rev") is True
               or (rev_yoy is not None and rev_yoy > 0))
    if not growing:
        _rev_txt = ("not at a window high" if rev_yoy is None
                    else f"{'down' if rev_yoy < 0 else 'up only'} {abs(rev_yoy):.1f}% YoY")
        reasons.append(f"revenue {_rev_txt} - the gain is margin, not growth")
        return {"verdict": MARGIN_LED, "reasons": reasons}

    if signals.get("new_high_rev"):
        reasons.append("revenue also at a window high - margin gain is not "
                       "cost-cutting on a shrinking base")
    return {"verdict": INFLECTING, "reasons": reasons}


# ──────────────────────────────────────────────────────────────────────────────
# Screen
# ──────────────────────────────────────────────────────────────────────────────
def _universe(kind: str) -> list[str]:
    import smallcap_universe as scu
    return scu.symbols(kind, suffix=".NS")


def screen(symbols: Iterable[str] | None = None, *,
           params: ContraParams | None = None,
           universe_kind: str = "both",
           limit: int | None = None,
           verdicts: Iterable[str] | None = None,
           max_workers: int = 6,
           derive: Callable[[str], dict[str, Any]] | None = None,
           progress_cb: Callable[[int, int, str], None] | None = None,
           ) -> dict[str, Any]:
    """Classify a universe. `derive` is injectable so tests never hit the network."""
    p = params or ContraParams()
    derive_fn = derive or fd.derive_fundamentals
    wanted = set(verdicts) if verdicts else {INFLECTING, RECOVERING}
    syms = list(symbols) if symbols is not None else _universe(universe_kind)
    if limit is not None:
        syms = syms[:limit]

    def _one(sym: str) -> dict[str, Any] | None:
        try:
            payload = derive_fn(sym)
        except Exception as exc:
            log.warning("derive failed for %s: %s", sym, exc)
            return None
        if not payload or not payload.get("available"):
            return None
        sig = extract_signals(payload)
        verdict = classify(sig, p)
        return {"symbol": payload.get("symbol") or sym,
                "name": payload.get("long_name"),
                "sector": payload.get("sector"),
                "price": payload.get("price"),
                "pe": payload.get("pe"),
                "roce": payload.get("roce"),
                **sig, **verdict}

    rows: list[dict[str, Any]] = []
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for row in pool.map(_one, syms):
            done += 1
            if progress_cb is not None:
                try:
                    progress_cb(done, len(syms), "")
                except Exception:
                    pass
            if row is not None:
                rows.append(row)

    tally = {v: sum(1 for r in rows if r["verdict"] == v) for v in VERDICT_ORDER}
    hits = [r for r in rows if r["verdict"] in wanted]
    hits.sort(key=lambda r: (VERDICT_ORDER.index(r["verdict"]),
                             -(r.get("opm_gain_pp") or -1e9)))
    return {"params": p.as_dict(), "scanned": len(syms), "derived": len(rows),
            "tally": tally, "hits": len(hits), "rows": hits}


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def _f(v: Any, nd: int = 1) -> str:
    return "-" if v is None else f"{float(v):.{nd}f}"


def _render(res: dict[str, Any], explain: bool = False) -> str:
    out = [f"Scanned {res['scanned']} | derived {res['derived']} | hits {res['hits']}",
           "Tally: " + ", ".join(f"{k}={v}" for k, v in res["tally"].items() if v),
           "",
           f"{'SYMBOL':<14}{'VERDICT':<18}{'OPM':>7}{'BASE':>7}{'+pp':>7}"
           f"{'PATyoy':>9}{'REVyoy':>9}{'STRK':>5}{'CFO/PAT':>9}  NAME"]
    for r in res["rows"]:
        out.append(
            f"{r['symbol']:<14}{r['verdict']:<18}{_f(r.get('opm_now')):>7}"
            f"{_f(r.get('opm_base')):>7}{_f(r.get('opm_gain_pp')):>7}"
            f"{_f(r.get('pat_yoy')):>9}{_f(r.get('rev_yoy')):>9}"
            f"{r.get('persistence_q', 0):>5}{_f(r.get('cfo_pat_ratio'), 2):>9}  "
            f"{(r.get('name') or '')[:26]}")
        if explain:
            for reason in r.get("reasons", []):
                out.append(f"{'':<14}  - {reason}")
    if not res["rows"]:
        out.append("  (nothing matched the requested verdicts)")
    out += ["",
            "Verdicts describe a DATA SHAPE, not a business or a price.",
            "Nothing here is backtested. Candidate generator, not a recommendation."]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Contra margin/earnings inflection screen")
    ap.add_argument("--kind", default="both",
                    choices=["both", "smallcap250", "microcap250"])
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--verdicts", nargs="*", default=None, choices=list(VERDICT_ORDER))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--explain", action="store_true", help="print the reasons per name")
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--min-opm-gain-pp", type=float, default=None)
    ap.add_argument("--min-pat-yoy", type=float, default=None)
    ap.add_argument("--min-persistence-q", type=int, default=None)
    args = ap.parse_args(argv)

    p = ContraParams()
    for attr in ("min_opm_gain_pp", "min_pat_yoy", "min_persistence_q"):
        v = getattr(args, attr, None)
        if v is not None:
            setattr(p, attr, v)

    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    def _progress(done: int, total: int, _s: str) -> None:
        if done % 25 == 0 or done == total:
            print(f"  ... {done}/{total}", file=sys.stderr)

    res = screen(symbols=args.symbols, params=p, universe_kind=args.kind,
                 limit=args.limit, verdicts=args.verdicts,
                 max_workers=args.workers, progress_cb=_progress)
    print(_render(res, explain=args.explain))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, default=str)
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
