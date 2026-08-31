#!/usr/bin/env python3
"""
value_screen.py — B-49: a quality-value screen built ENTIRELY on free data.

Reproduces the class of "deep value" card that pairs a cheap multiple with high
capital efficiency and a clean balance sheet (P/E, P/S, OPM, ROE, ROCE, D/E,
revenue & profit growth) over the free NSE small/micro-cap universe, with **no
screener.in cookie**.

Why this module exists
----------------------
Two modules already sat on either side of this gap and neither closed it:

  * ``multibagger_candidates.py`` runs almost exactly this query
    (OPM>10, ROCE>15, D/E<1, 3Y sales growth>15) but is screener.in
    **cookie-gated** — ``build_dataset(sessionid, query)``.
  * ``smallcap_discovery.py`` is free but scores **ownership only**; it carries
    no fundamentals at all.

This is the free fundamentals half, and it reuses rather than re-derives:
universe from :mod:`smallcap_universe`, every metric from
:func:`fundamentals_deep.derive_fundamentals`, governance flags from
:mod:`ownership_cache` when it is warm.

Three-state criteria, never silent drops
----------------------------------------
Each criterion is **PASS / FAIL / UNKNOWN**, following the FR-4 red-flags
convention. This is not decoration. Testing the screen against AGI Greenpac
(the card that prompted it) found yfinance's ``.info`` returns
``returnOnEquity: None`` for that very name — a screen keyed on ``.info`` alone
would have silently dropped its own worked example. So:

  * metrics come from the **statements** path first (``derive_fundamentals``),
    which computes ROE/ROCE itself, with ``.info`` used only for the multiples;
  * a missing figure is reported as UNKNOWN and **never counted as a fail**;
  * names are ranked by criteria passed, with unknowns shown, so a name that is
    merely under-reported is visibly different from one that was rejected.

> [!warning] This is a reading list, not a ranking of edge.
> ``passes``/``unknowns`` order the output so the list can be read top-down. It
> is **not** a conviction score and it is **not backtested**. "Cheap with good
> ROCE" is one of the most crowded screens in existence, so the prior on
> undiscovered edge here is low. Treat output as names to go and read about.
> The measurement that would change that is a forward hit-rate study against a
> Smallcap-250 benchmark — the same test B-34 still owes.

Usage
-----
    from value_screen import screen
    rows = screen(limit=50)

    py -3 tools/value_screen.py --limit 60
    py -3 tools/value_screen.py --min-roce 20 --max-pe 15 --json out.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict, field
from typing import Any, Callable, Iterable

import fundamentals_deep as fd

log = logging.getLogger(__name__)

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"


# ──────────────────────────────────────────────────────────────────────────────
# Thresholds
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Thresholds:
    """Screen bounds. Parameters, deliberately — NOT the numbers off any one card.

    The defaults are the conventional quality-value bounds that
    ``multibagger_candidates``' screener.in query already used (ROCE>15, OPM>10,
    D/E<1), widened only where a hard cutoff would be arbitrary. Tune them at the
    call site rather than editing this class, so a run's bounds are recorded with
    its output.
    """
    max_pe: float | None = 25.0
    max_ps: float | None = 4.0
    min_opm: float | None = 10.0
    min_roe: float | None = 12.0
    min_roce: float | None = 15.0
    max_de: float | None = 1.0
    min_rev_growth: float | None = 8.0      # 3Y revenue CAGR, %
    min_profit_growth: float | None = 8.0   # 3Y profit CAGR, %
    max_dilution: float | None = 10.0       # share-count growth over the window, %
    min_interest_cover: float | None = 3.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


#: (label, payload key, comparison, threshold attribute). One row per criterion;
#: adding a criterion here is the only edit a new bound needs.
CRITERIA: tuple[tuple[str, str, str, str], ...] = (
    ("P/E",              "pe",                "<=", "max_pe"),
    ("P/S",              "ps",                "<=", "max_ps"),
    ("OPM %",            "opm",               ">=", "min_opm"),
    ("ROE %",            "roe",               ">=", "min_roe"),
    ("ROCE %",           "roce",              ">=", "min_roce"),
    ("D/E",              "debt_to_equity",    "<=", "max_de"),
    ("Rev CAGR 3Y %",    "revenue_cagr_3y",   ">=", "min_rev_growth"),
    ("Profit CAGR 3Y %", "profit_cagr_3y",    ">=", "min_profit_growth"),
    ("Dilution %",       "dilution_pct",      "<=", "max_dilution"),
    ("Interest cover",   "interest_coverage", ">=", "min_interest_cover"),
)


def evaluate(payload: dict[str, Any], th: Thresholds) -> dict[str, Any]:
    """Score one derived-fundamentals payload against `th`.

    Pure: no network, no globals. Returns the per-criterion verdicts plus the
    pass/fail/unknown tallies. A criterion whose threshold is ``None`` is not
    applied at all and does not appear in the verdicts.
    """
    verdicts: dict[str, dict[str, Any]] = {}
    for label, key, op, attr in CRITERIA:
        bound = getattr(th, attr)
        if bound is None:
            continue                                   # criterion switched off
        value = payload.get(key)
        if value is None:
            verdicts[label] = {"state": UNKNOWN, "value": None, "bound": bound}
            continue
        try:
            v = float(value)
        except (TypeError, ValueError):
            verdicts[label] = {"state": UNKNOWN, "value": None, "bound": bound}
            continue
        ok = (v <= bound) if op == "<=" else (v >= bound)
        verdicts[label] = {"state": PASS if ok else FAIL,
                           "value": round(v, 2), "bound": bound, "op": op}

    states = [v["state"] for v in verdicts.values()]
    return {
        "verdicts": verdicts,
        "passes":   states.count(PASS),
        "fails":    states.count(FAIL),
        "unknowns": states.count(UNKNOWN),
        "applied":  len(states),
    }


def qualifies(result: dict[str, Any], *, max_fails: int = 0,
              max_unknowns: int = 3) -> bool:
    """Whether a scored name makes the list.

    `max_fails` is the real filter. `max_unknowns` is a **data-quality** guard,
    not a judgement about the company: a name with six missing figures has not
    been screened, it has merely been under-reported, and letting it onto a list
    beside fully-measured names would misrepresent both.
    """
    return result["fails"] <= max_fails and result["unknowns"] <= max_unknowns


#: A 1Y growth rate this many points above the 3Y CAGR means the headline number
#: is one good year, not a trend. Flagged, never screened on -- a genuine
#: inflection looks identical to a flattered one from the outside, and only
#: reading the business tells them apart.
GROWTH_GAP_PP = 6.0


def _growth_gap(yoy: float | None, cagr_3y: float | None) -> float | None:
    """1Y growth minus 3Y CAGR, in percentage points. None if either is missing."""
    if yoy is None or cagr_3y is None:
        return None
    return round(float(yoy) - float(cagr_3y), 1)


# ──────────────────────────────────────────────────────────────────────────────
# Governance overlay (free NSE shareholding) — FLAGS ONLY, never a vote
# ──────────────────────────────────────────────────────────────────────────────
PLEDGE_MAX = 5.0          # matches smallcap_discovery, deliberately
PROMOTER_SELL_PP = 2.0


def governance_flags(symbol: str) -> dict[str, Any]:
    """Pledge / promoter-exit flags from the free NSE shareholding cache.

    Returns ``{}`` when the symbol is not cached — warm it with
    ``smallcap_discovery --backfill``. These are **flags, never votes**: the same
    convention the scanner pipeline applies to ``RISK_SCANNERS``, so a governance
    problem is shown next to a name rather than silently reordering it.
    """
    try:
        import ownership_cache as oc
        import nse_shareholding_fetch as nsf
    except Exception:
        return {}
    try:
        data = oc.load(symbol.replace(".NS", ""))
    except Exception:
        return {}
    quarters = (data or {}).get("quarters") or {}
    if len(quarters) < 2:
        return {}
    try:
        ordered = sorted(quarters.items(),
                         key=lambda t: nsf._period_date(t[0]) or __import__(
                             "datetime").datetime.min)
    except Exception:
        return {}
    (_, old), (_, new) = ordered[0], ordered[-1]

    def _n(v):
        return float(v) if isinstance(v, (int, float)) else None

    pledge = _n(new.get("promoter_pledge_pct"))
    prom_new, prom_old = _n(new.get("promoter")), _n(old.get("promoter"))
    flags: list[str] = []
    if pledge is not None and pledge > PLEDGE_MAX:
        flags.append(f"promoter pledge {pledge:.1f}% > {PLEDGE_MAX:.0f}%")
    delta = (None if prom_new is None or prom_old is None else prom_new - prom_old)
    if delta is not None and delta < -PROMOTER_SELL_PP:
        flags.append(f"promoter stake down {abs(delta):.1f}pp")
    return {"pledge_pct": pledge, "promoter_delta": (None if delta is None
                                                     else round(delta, 2)),
            "flags": flags}


# ──────────────────────────────────────────────────────────────────────────────
# The screen
# ──────────────────────────────────────────────────────────────────────────────
def _universe(kind: str) -> list[str]:
    import smallcap_universe as scu
    return scu.symbols(kind, suffix=".NS")


def screen(symbols: Iterable[str] | None = None, *,
           thresholds: Thresholds | None = None,
           universe_kind: str = "both",
           limit: int | None = None,
           max_fails: int = 0,
           max_unknowns: int = 3,
           with_governance: bool = True,
           max_workers: int = 6,
           derive: Callable[[str], dict[str, Any]] | None = None,
           progress_cb: Callable[[int, int, str], None] | None = None,
           ) -> dict[str, Any]:
    """Run the screen. Returns ``{thresholds, scanned, hits, rows, rejected}``.

    `derive` is injectable so the tests never touch the network; it defaults to
    :func:`fundamentals_deep.derive_fundamentals`, which makes exactly ONE
    yfinance round trip per symbol (statements and `.info` come back together).
    """
    th = thresholds or Thresholds()
    derive_fn = derive or fd.derive_fundamentals
    syms = list(symbols) if symbols is not None else _universe(universe_kind)
    if limit is not None:
        syms = syms[:limit]
    total = len(syms)

    def _one(sym: str) -> dict[str, Any] | None:
        try:
            payload = derive_fn(sym)
        except Exception as exc:                 # one bad symbol must not kill a run
            log.warning("derive failed for %s: %s", sym, exc)
            return None
        if not payload or not payload.get("available"):
            return None
        res = evaluate(payload, th)
        # The 1Y figures are REPORTED, never screened on. The screen tests the
        # 3Y CAGR because it is the harder number to flatter; carrying the 1Y
        # beside it makes the gap visible. AGI Greenpac -- the card that prompted
        # this module -- advertises "+14% revenue growth" and compounds at 5.7%
        # over three years. A screen that showed only one of those would be
        # repeating the card's own framing back at you.
        _a0 = (payload.get("annual") or [{}])[0]
        return {
            "symbol":     payload.get("symbol") or sym,
            "name":       payload.get("long_name"),
            "sector":     payload.get("sector"),
            "price":      payload.get("price"),
            "market_cap": payload.get("market_cap"),
            "pe":         payload.get("pe"),
            "ps":         payload.get("ps"),
            "ps_source":  payload.get("ps_source"),
            "roce":       payload.get("roce"),
            "roe":        payload.get("roe"),
            "opm":        payload.get("opm"),
            "de":         payload.get("debt_to_equity"),
            "rev_cagr_3y":    payload.get("revenue_cagr_3y"),
            "profit_cagr_3y": payload.get("profit_cagr_3y"),
            "rev_yoy":        _a0.get("revenue_yoy"),
            "profit_yoy":     _a0.get("profit_yoy"),
            "growth_gap":     _growth_gap(_a0.get("revenue_yoy"),
                                          payload.get("revenue_cagr_3y")),
            **res,
        }

    rows: list[dict[str, Any]] = []
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for sym, row in zip(syms, pool.map(_one, syms)):
            done += 1
            if progress_cb is not None:
                try:
                    progress_cb(done, total, sym)
                except Exception:
                    pass
            if row is not None:
                rows.append(row)

    hits = [r for r in rows if qualifies(r, max_fails=max_fails,
                                         max_unknowns=max_unknowns)]
    if with_governance:
        for r in hits:
            g = governance_flags(r["symbol"])
            if g:
                r["governance"] = g

    # Ordering, stated plainly: most criteria passed, then fewest unknowns, then
    # capital efficiency. NOT an edge ranking -- see the module docstring.
    hits.sort(key=lambda r: (-r["passes"], r["unknowns"],
                             -(r["roce"] if r["roce"] is not None else -1e9)))
    return {
        "thresholds": th.as_dict(),
        "scanned":    total,
        "derived":    len(rows),
        "hits":       len(hits),
        "rows":       hits,
        "rejected":   len(rows) - len(hits),
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def _fmt(v: Any, nd: int = 1) -> str:
    return "-" if v is None else f"{float(v):.{nd}f}"


def _render(res: dict[str, Any]) -> str:
    """Plain-ASCII report. Printed strings stay ASCII on purpose: this repo's
    console is cp1252 and a stray en-dash raises UnicodeEncodeError mid-run."""
    out = [
        f"Scanned {res['scanned']} symbols | derived {res['derived']} "
        f"| hits {res['hits']} | rejected {res['rejected']}",
        "",
        f"{'SYMBOL':<14}{'P/E':>7}{'P/S':>7}{'ROCE':>7}{'ROE':>7}{'OPM':>7}"
        f"{'D/E':>7}{'REV3Y':>8}{'REV1Y':>8}{'PAT3Y':>8}{'PAT1Y':>8}"
        f"{'PASS':>6}{'UNK':>5}  NAME",
    ]
    for r in res["rows"]:
        out.append(
            f"{r['symbol']:<14}{_fmt(r['pe']):>7}{_fmt(r['ps'], 2):>7}"
            f"{_fmt(r['roce']):>7}{_fmt(r['roe']):>7}{_fmt(r['opm']):>7}"
            f"{_fmt(r['de'], 2):>7}{_fmt(r['rev_cagr_3y']):>8}"
            f"{_fmt(r['rev_yoy']):>8}{_fmt(r['profit_cagr_3y']):>8}"
            f"{_fmt(r['profit_yoy']):>8}"
            f"{r['passes']:>4}/{r['applied']:<1}{r['unknowns']:>5}  "
            f"{(r.get('name') or '')[:30]}")
        gap = r.get("growth_gap")
        if gap is not None and gap >= GROWTH_GAP_PP:
            out.append(f"{'':<14}  NOTE: 1Y revenue growth is {gap:.1f}pp above the "
                       f"3Y CAGR - one good year, not yet a trend")
        for f in (r.get("governance") or {}).get("flags", []):
            out.append(f"{'':<14}  FLAG: {f}")
    if not res["rows"]:
        out.append("  (no names cleared the screen)")
    out += ["",
            "Ranking is passes -> fewest unknowns -> ROCE. NOT a conviction",
            "score and NOT backtested; treat as a reading list."]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", default="both",
                    choices=["both", "smallcap250", "microcap250"])
    ap.add_argument("--symbols", nargs="*", help="explicit tickers, skips the universe")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-fails", type=int, default=0)
    ap.add_argument("--max-unknowns", type=int, default=3)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-governance", action="store_true")
    ap.add_argument("--json", metavar="PATH", help="also write the full result as JSON")
    for label, _key, _op, attr in CRITERIA:
        # argparse runs help through %-formatting, so a label like "OPM %" is a
        # dangling format spec and raises "badly formed help string".
        _help = f"{label} bound (default {getattr(Thresholds(), attr)})".replace("%", "%%")
        ap.add_argument(f"--{attr.replace('_', '-')}", type=float, default=None,
                        help=_help)
    args = ap.parse_args(argv)

    th = Thresholds()
    for _label, _key, _op, attr in CRITERIA:
        v = getattr(args, attr, None)
        if v is not None:
            setattr(th, attr, v)

    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    def _progress(done: int, total: int, sym: str) -> None:
        if done % 25 == 0 or done == total:
            print(f"  ... {done}/{total}", file=sys.stderr)

    res = screen(symbols=args.symbols, thresholds=th, universe_kind=args.kind,
                 limit=args.limit, max_fails=args.max_fails,
                 max_unknowns=args.max_unknowns,
                 with_governance=not args.no_governance,
                 max_workers=args.workers, progress_cb=_progress)
    print(_render(res))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, default=str)
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
