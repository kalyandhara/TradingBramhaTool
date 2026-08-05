"""earnings_calendar.py — real NSE result dates and a TRUE SUE for the PEAD scanners.

PEAD Phases 2 + 3. Why this exists
----------------------------------
Phase 1 shipped as *Proxy*-PEAD on an explicit constraint, recorded in
[[analyses/PEAD-Scanner-Roadmap]] and repeated in `scan_pead`'s own docstring:
our Python data sources carry no analyst consensus for NSE, so the earnings event
had to be **inferred** from a large high-volume price reaction and the surprise
could never be a real SUE. Phase 3 was scoped around that limit — scrape ~12
quarters of EPS off screener.in behind a Playwright-captured session and z-score
the YoY EPS change, a *time-series* SUE standing in for the estimate-vs-actual
one we believed unreachable.

**That constraint no longer holds.** yfinance 1.2.1's `get_earnings_dates()`
returns `EPS Estimate`, `Reported EPS` and `Surprise(%)` for `.NS` symbols,
login-free. Coverage probe 2026-08-04 over 15 names spanning the cap spectrum:
**15/15 carried estimates**, small-caps included (MAPMYINDIA 15 quarters,
FINEORG 15, ROUTE 20, GRANULES 25). So the *actual* SUE —
`(reported − consensus) / σ(past surprises)` — is computable today, and the
screener.in scrape Phase 3 was going to build is not needed. This module is that
data layer; the session-capture dependency is dropped, not worked around.

Two traps handled here, both the repo's own recurring bug shape
-----------------------------------------------------------
  * **Duplicate rows per result date.** yfinance returns the same earnings date
    twice for some names — HCLTECH's 2026-07-13 appears at both 06:00 and 08:00,
    one row carrying `Reported EPS` and one all-NaN. Keyed naively into a dict
    the empty row silently overwrites the real one: the identical silent
    overwrite `ownership_cache` hit with NSE's event-driven filings. `_richer`
    below keeps whichever row actually reports.
  * **Timestamps are US/Eastern, not IST.** The index comes back tz-aware in New
    York time, so a result stamped `2026-07-13 20:00 −04:00` is **14 July** in
    India and would reconcile against the wrong NSE bar. Everything is converted
    to Asia/Kolkata before a date is taken.

Coverage travels with the reading
---------------------------------
Per the standing rule in [[analyses/Open-Backlog-2026-08-02]] — *carry coverage
with the data, and refuse to score below a floor* — every reading reports how
many quarters it actually had, and `compute_sue` returns state `NOT_CHECKED`
rather than a number when the history is too thin to z-score. `market_health`
does this with coverage + NOT_CHECKED; `red_flags` degrades trend flags below
three yearly points; this is the same defence one layer along. σ carries a
relative floor for the same reason `_suv_series` clamps: the backlog's thesis
lists "a z-score divided by ~1e-14" among the six silent-partial-result bugs.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

HERE      = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache" / "earnings"
#: Result dates move quarterly, but during a results season a fresh report can
#: land intraday — half a day keeps the scanner current without re-fetching a
#: 25-row table on every rerun of a 200-name universe.
CACHE_TTL = 12 * 3600

IST = "Asia/Kolkata"

#: Rows to request. yfinance returns ~25 for a mature NSE name (~6 years of
#: quarters); anything beyond MIN_SURPRISE_HISTORY is free accuracy on σ.
FETCH_LIMIT = 24

#: Prior *reported* quarters required before a SUE is trustworthy. Four is the
#: floor at which a standard deviation stops being an artefact of two points;
#: below it `compute_sue` returns NOT_CHECKED instead of a confident number.
MIN_SURPRISE_HISTORY = 4

#: SUE is a z-score and inherits the same tail problem as SUV — one freak
#: quarter in the baseline otherwise yields a ±40 reading.
SUE_CLAMP = 10.0

#: Calendar days either side of a result date within which an inferred event bar
#: is accepted as the same event. Must be ≥3: a Friday post-close announcement
#: reacts on Monday's bar. Four absorbs one public holiday on top.
DEFAULT_TOL_DAYS = 4

# Reconciliation states (mirrors market_health's PASS / FAIL / NOT_CHECKED idiom)
CONFIRMED   = "confirmed-earnings"
GAP_ONLY    = "gap-only"
NOT_CHECKED = "NOT_CHECKED"


def _yf_symbol(symbol: str) -> str:
    """Scanner-hub universes carry bare NSE tickers; yfinance needs `.NS`.

    Deliberately duplicated from `scanner_templates._yf_symbol` rather than
    imported: scanner_templates imports *this* module, so reaching back would be
    a cycle.
    """
    return symbol if ("." in symbol or symbol.startswith("^")) else f"{symbol}.NS"


def _num(v: Any) -> float | None:
    """float(v), or None for NaN / None / anything non-numeric."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _richness(row: dict) -> int:
    """How much a duplicate row actually carries. A reported figure is worth more
    than an estimate — the all-NaN twin of a real row must never win."""
    return (2 if row.get("reported") is not None else 0) + \
           (1 if row.get("estimate") is not None else 0)


# ── Fetch + normalise ─────────────────────────────────────────────────────────
def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol.upper().replace('.', '_')}.json"


def _read_cache(symbol: str) -> dict | None:
    p = _cache_path(symbol)
    try:
        if not p.exists() or (time.time() - p.stat().st_mtime) > CACHE_TTL:
            return None
        return json.loads(p.read_text(encoding="utf-8")) or None
    except Exception as e:
        log.debug("earnings cache read failed (%s): %s", symbol, e)
        return None


def _write_cache(symbol: str, payload: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(symbol).write_text(json.dumps(payload), encoding="utf-8")
    except Exception as e:
        log.debug("earnings cache write failed (%s): %s", symbol, e)


#: In-process memo over the disk cache — a scan asks for the same symbol once per
#: hit, and the Hub re-runs the same universe repeatedly within a session.
_MEMO: dict[str, dict | None] = {}


def _parse_events(df) -> list[dict]:
    """yfinance earnings frame → newest-first list of one dict per result DATE.

    Converts the tz-aware US/Eastern index to IST before taking a date, and
    collapses yfinance's duplicate rows per date keeping the richer one.
    """
    if df is None or getattr(df, "empty", True):
        return []

    idx = df.index
    try:
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_convert(IST)
    except Exception as e:                       # naive index, or tz db missing
        log.debug("earnings tz-convert failed, using raw index: %s", e)

    cols = {c.lower(): c for c in df.columns}
    est_col = next((cols[c] for c in cols if "estimate" in c), None)
    rep_col = next((cols[c] for c in cols if "reported" in c), None)
    sur_col = next((cols[c] for c in cols if "surprise" in c), None)

    by_date: dict[str, dict] = {}
    for pos in range(len(df)):
        try:
            d = idx[pos].date().isoformat()
        except Exception:
            continue
        row = {
            "date":         d,
            "estimate":     _num(df[est_col].iloc[pos]) if est_col else None,
            "reported":     _num(df[rep_col].iloc[pos]) if rep_col else None,
            "surprise_pct": _num(df[sur_col].iloc[pos]) if sur_col else None,
        }
        prev = by_date.get(d)
        if prev is None or _richness(row) > _richness(prev):
            by_date[d] = row

    return sorted(by_date.values(), key=lambda r: r["date"], reverse=True)


def fetch_earnings(symbol: str, use_cache: bool = True) -> dict | None:
    """Result dates + consensus for `symbol`, or None if the lookup failed.

    Returns ``{symbol, events[], n_events, n_reported, n_with_estimate}``, newest
    first. `n_*` are the coverage counts — a caller that scores off this data is
    expected to look at them rather than trust whatever happened to arrive.
    """
    key = symbol.upper()
    if use_cache:
        if key in _MEMO:
            return _MEMO[key]
        cached = _read_cache(key)
        if cached:
            _MEMO[key] = cached
            return cached

    try:
        import yfinance as yf
        raw = yf.Ticker(_yf_symbol(symbol)).get_earnings_dates(limit=FETCH_LIMIT)
    except Exception as e:
        # A failed fetch is NOT an empty calendar. Cache nothing, return None, and
        # let the caller report NOT_CHECKED — the whole point of this module.
        log.debug("earnings fetch failed (%s): %s", symbol, e)
        if use_cache:
            _MEMO[key] = None
        return None

    events = _parse_events(raw)
    if not events:
        log.debug("earnings: %s returned no usable rows", symbol)
        if use_cache:
            _MEMO[key] = None
        return None

    payload = {
        "symbol":          key,
        "events":          events,
        "n_events":        len(events),
        "n_reported":      sum(1 for e in events if e["reported"] is not None),
        "n_with_estimate": sum(1 for e in events if e["estimate"] is not None),
        "fetched_at":      datetime.now().isoformat(timespec="seconds"),
    }
    if use_cache:
        _write_cache(key, payload)
        _MEMO[key] = payload
    return payload


# ── Phase 3 — true SUE ────────────────────────────────────────────────────────
def compute_sue(events: list[dict],
                on_or_before: str | date | None = None,
                *, min_history: int = MIN_SURPRISE_HISTORY) -> dict:
    """True SUE for the most recent reported quarter at `on_or_before`.

    SUE = (reported − consensus) / σ(prior surprises), the estimate-vs-actual
    standardized unexpected earnings of the PEAD literature — not the YoY-growth
    proxy Phase 1 had to settle for.

    σ is measured over the surprises **strictly before** the quarter being scored,
    never including it. Same anti-leak baseline as `_suv_series`' `shift(1)`
    rolling window, and for the same reason: an outsized event that inflates its
    own denominator reads as unremarkable.

    Returns a dict that always carries `state` and `n_history`. `state` is
    NOT_CHECKED — with `sue: None` — whenever the history is too thin to
    z-score; it never degrades to a guess.
    """
    out: dict[str, Any] = {
        "state": NOT_CHECKED, "sue": None, "surprise": None, "surprise_pct": None,
        "estimate": None, "reported": None, "date": None,
        "n_history": 0, "sigma": None, "note": "",
    }
    if not events:
        out["note"] = "no earnings rows"
        return out

    cutoff = None
    if on_or_before is not None:
        cutoff = on_or_before.isoformat() if isinstance(on_or_before, date) \
            else str(on_or_before)[:10]

    # Reported quarters only, newest first — an announced-but-unreported future
    # date has no surprise to measure.
    reported = [e for e in events
                if e.get("reported") is not None and e.get("estimate") is not None]
    if cutoff:
        reported = [e for e in reported if e["date"] <= cutoff]
    if not reported:
        out["note"] = "no reported quarter with a consensus estimate"
        return out

    target, priors = reported[0], reported[1:]
    surprise = target["reported"] - target["estimate"]

    out.update({
        "date":         target["date"],
        "estimate":     target["estimate"],
        "reported":     target["reported"],
        "surprise":     round(surprise, 4),
        "surprise_pct": target.get("surprise_pct"),
        "n_history":    len(priors),
    })

    if len(priors) < min_history:
        out["note"] = (f"only {len(priors)} prior quarter(s) with both figures; "
                       f"need {min_history} to standardize")
        return out

    errs = [p["reported"] - p["estimate"] for p in priors]
    sigma = statistics.stdev(errs)

    # Relative floor. Surprises are in ₹/share, so an absolute floor alone would
    # be meaningless across a ₹4 EPS and a ₹400 one: a run of near-identical
    # quarters otherwise drives σ→0 and blows SUE up to the clamp on noise.
    scale = abs(target["estimate"]) or abs(target["reported"]) or 1.0
    sigma = max(sigma, 0.01 * scale, 0.01)

    sue = max(-SUE_CLAMP, min(SUE_CLAMP, surprise / sigma))
    out.update({"state": "OK", "sue": round(sue, 2), "sigma": round(sigma, 4)})
    return out


# ── Phase 2 — reconcile an inferred event against the real calendar ───────────
def _as_date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.fromisoformat(str(v)[:10]).date()
    except Exception:
        return None


def reconcile_event(symbol: str, event_date: Any, *,
                    tol_days: int = DEFAULT_TOL_DAYS,
                    use_cache: bool = True) -> dict:
    """Is the price reaction `scan_pead` found actually an earnings reaction?

    Matches the inferred event bar against the real result calendar within
    `tol_days`, and — when it matches — computes the SUE for that quarter.

    Three states, never two: CONFIRMED (a result date is within tolerance),
    GAP_ONLY (calendar fetched fine, nothing near this bar — an honest negative),
    NOT_CHECKED (no calendar; we do not know, which is not the same as "no").
    """
    out: dict[str, Any] = {
        "state": NOT_CHECKED, "earnings_date": None, "days_off": None,
        "sue": None, "sue_state": NOT_CHECKED, "surprise_pct": None,
        "n_history": 0, "coverage": None, "note": "",
    }

    ev_date = _as_date(event_date)
    if ev_date is None:
        out["note"] = "event bar carried no date"
        return out

    data = fetch_earnings(symbol, use_cache=use_cache)
    if not data:
        out["note"] = "no earnings calendar available for this symbol"
        return out

    out["coverage"] = f"{data['n_with_estimate']}/{data['n_events']} quarters with a consensus estimate"

    best, best_off = None, None
    for e in data["events"]:
        d = _as_date(e["date"])
        if d is None:
            continue
        off = abs((d - ev_date).days)
        if off <= tol_days and (best_off is None or off < best_off):
            best, best_off = e, off

    if best is None:
        out["state"] = GAP_ONLY
        out["note"] = (f"no result date within {tol_days} days of the reaction "
                       f"({ev_date.isoformat()})")
        return out

    out.update({"state": CONFIRMED,
                "earnings_date": best["date"],
                "days_off": best_off})

    sue = compute_sue(data["events"], on_or_before=best["date"])
    out.update({
        "sue":          sue["sue"],
        "sue_state":    sue["state"],
        "surprise_pct": sue.get("surprise_pct"),
        "n_history":    sue["n_history"],
    })
    if sue["state"] != "OK":
        out["note"] = sue["note"]
    return out


# ── Enrichment — the symbol-level join scan_pead cannot do itself ─────────────
#: Hand-set, and honest about it. `scan_pead`'s Phase-1 score is the FLOOR: a
#: confirmed result date and a positive SUE can only promote a hit, never demote
#: one, so this cannot silently re-rank what Phase 1 already shipped. Whether the
#: bonus should exist at all — and at what size — is exactly what Phase 4's
#: backtest is for. Do not present these as measured.
#:
#: The bonus is gated on the surprise AGREEING with the price reaction: a
#: confirmed earnings date whose SUE is negative earns nothing, because a rally
#: on a miss contradicts the drift premise rather than confirming it. See the
#: divergence branch in `enrich_pead_hit`.
CONFIRM_BONUS  = 6.0
SUE_BONUS_PER  = 2.5
SUE_BONUS_CAP  = 4.0        # σ beyond this adds nothing


def enrich_pead_hit(hit: dict, symbol: str | None = None, *,
                    tol_days: int = DEFAULT_TOL_DAYS,
                    use_cache: bool = True) -> dict:
    """Fold real earnings confirmation + SUE onto a `scan_pead` result, in place.

    `run_scanner` attaches the symbol only *after* the scan fn returns, so the
    scanner is symbol-blind and cannot fetch this itself — the roadmap's
    pre-enrichment join, applied here at the symbol level exactly as
    `run_quality_pead` applies the fundamentals gate.
    """
    sym = symbol or hit.get("symbol")
    if not sym:
        return hit

    try:
        rec = reconcile_event(sym, hit.get("event_date"),
                              tol_days=tol_days, use_cache=use_cache)
    except Exception as e:                       # never let enrichment kill a hit
        log.debug("PEAD enrichment failed (%s): %s", sym, e)
        return hit

    hit["earnings_state"] = rec["state"]
    hit["earnings_date"]  = rec["earnings_date"]
    hit["sue"]            = rec["sue"]
    hit["sue_state"]      = rec["sue_state"]
    hit["eps_coverage"]   = rec["coverage"]
    hit["score_pead_base"] = hit.get("score")    # keep Phase 1's number for Phase 4

    tags    = hit.setdefault("tags", [])
    reasons = hit.setdefault("reasons", [])

    # Phase 1 stamped every card "Proxy-PEAD" and carried a caveat line saying the
    # event was not a confirmed earnings date. Once reconciled that is simply
    # false, so both are removed rather than left to contradict the confirmation
    # sitting next to them on the same card.
    if rec["state"] == CONFIRMED:
        reasons[:] = [r for r in reasons if "not a confirmed" not in r]
        tags[:]    = [t for t in tags if t != "Proxy-PEAD"]

    # Qualify whatever label the hit already carries rather than replacing it —
    # the composite Phase-5.1 scanner names itself "Zero-Debt Quality PEAD", and
    # overwriting that would hide which scanner produced the card.
    base = str(hit.get("pattern_type") or "PEAD Drift")
    if base == "Proxy-PEAD Drift":
        base = "PEAD Drift"          # reconciled — it is no longer a proxy

    if rec["state"] == CONFIRMED:
        hit["pattern_type"] = f"{base} (confirmed earnings)"
        off = rec["days_off"]
        tags.insert(0, "Confirmed earnings")
        reasons.append(
            f"Confirmed against the result calendar: results dated "
            f"{rec['earnings_date']}, {off} day(s) from the reaction bar — this "
            f"is an earnings move, not an inferred one"
        )
        sue = rec["sue"] if rec["sue_state"] == "OK" else None

        if sue is None:
            tags.append("SUE n/a")
            reasons.append(f"SUE not computed — {rec['note']}")
            bonus = CONFIRM_BONUS       # it IS earnings; we just cannot grade it

        elif sue > 0:
            tags.append(f"SUE {sue:+.1f}σ")
            pct = rec.get("surprise_pct")
            pct_txt = f", {pct:+.1f}% vs consensus" if pct is not None else ""
            reasons.append(
                f"True SUE {sue:+.1f}σ — reported EPS beat analyst consensus{pct_txt}, "
                f"standardized over {rec['n_history']} prior quarters' surprises"
            )
            bonus = CONFIRM_BONUS + min(sue, SUE_BONUS_CAP) * SUE_BONUS_PER

        else:
            # Confirmed earnings, but the surprise points the OTHER WAY from the
            # price reaction — scan_pead is bullish-only, so this is a rally on a
            # MISS. PEAD is the drift that follows a surprise *in its direction*;
            # a positive reaction to a negative surprise is a contradiction of the
            # premise, not evidence for it (guidance, a squeeze, a one-off charge
            # the market looked through). Observed live: BAJFINANCE 2026-07-30,
            # EPS 8.57 vs 13.70 consensus (−37%) into a held +price reaction.
            #
            # So it earns NO confirmation bonus. It is not demoted below the
            # Phase-1 score either — Phase 1 didn't know, and inventing a penalty
            # is the unmeasured-weight habit Phase 4 exists to end — but it is
            # labelled loudly enough that the card cannot be misread as a beat.
            hit["pattern_type"] = f"{base} (surprise diverges)"
            tags.append(f"MISS {sue:+.1f}σ")
            pct = rec.get("surprise_pct")
            pct_txt = f" ({pct:+.1f}% vs consensus)" if pct is not None else ""
            reasons.append(
                f"DIVERGENCE — price rallied but earnings MISSED consensus by "
                f"{sue:+.1f}σ{pct_txt}. PEAD predicts drift in the direction of the "
                f"surprise, so the drift premise does not hold here; treat this as "
                f"a price move needing another explanation, not an earnings setup"
            )
            bonus = 0.0

        hit["score"] = round(min(100.0, float(hit.get("score", 0.0)) + bonus), 2)

    elif rec["state"] == GAP_ONLY:
        tags.append("Gap-only (unconfirmed)")
        reasons.append(
            "Gap-only: the result calendar has no announcement near this bar, so "
            "the reaction is a price event of unknown cause — not confirmed earnings"
        )
    else:
        tags.append("Earnings unchecked")
        reasons.append(f"Earnings calendar unavailable — {rec['note']}")

    return hit


def enrich_pead_results(results: list[dict], **kwargs) -> list[dict]:
    """`enrich_pead_hit` across a result list, re-sorted on the adjusted score."""
    for hit in results:
        try:
            enrich_pead_hit(hit, **kwargs)
        except Exception as e:
            log.debug("PEAD enrichment skipped for %s: %s", hit.get("symbol"), e)
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)


def coverage_summary(results: list[dict]) -> dict:
    """How much of a scan was actually confirmed — the counts a caller should
    print rather than quietly averaging over whatever resolved."""
    n = len(results)
    conf = sum(1 for r in results if r.get("earnings_state") == CONFIRMED)
    gap  = sum(1 for r in results if r.get("earnings_state") == GAP_ONLY)
    unk  = sum(1 for r in results if r.get("earnings_state") == NOT_CHECKED)
    sue  = sum(1 for r in results if r.get("sue") is not None)
    return {"total": n, "confirmed": conf, "gap_only": gap,
            "not_checked": unk, "with_sue": sue}


if __name__ == "__main__":                       # python earnings_calendar.py TCS ...
    import sys
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    for s in (sys.argv[1:] or ["TCS", "INFY", "HCLTECH"]):
        d = fetch_earnings(s)
        if not d:
            print(f"{s}: NO DATA")
            continue
        sue = compute_sue(d["events"])
        print(f"{s}: {d['n_events']} dates, {d['n_reported']} reported, "
              f"{d['n_with_estimate']} with estimate")
        print(f"   latest {sue['date']}  est={sue['estimate']} rep={sue['reported']} "
              f"SUE={sue['sue']} ({sue['state']}, n_hist={sue['n_history']}) {sue['note']}")
