#!/usr/bin/env python3
"""
volume_anomaly.py — B-51: whole-market volume spikes, WITH the reason.

Finds NSE equities whose latest-session volume is a large multiple of their own
one-year average, then attributes each spike to a cause read from free NSE feeds:
a corporate filing, proprietary churn in the bulk-deal file, one-sided deal
activity, or nothing at all.

> [!important] A SCREEN, not a trigger. No BUY/SELL implication.
> Wired like the Renko Flip screen: no entry, no stop, no target, and it must
> never become a confluence vote. A volume spike is a **question** ("why did this
> trade 30x normal?"), and the module's job is to hand you the answer alongside
> the question, not to convert it into a position.

Why bhavcopy is the same-day source and yfinance is not
------------------------------------------------------
Verified on 2026-08-28: yfinance had **no bar at all** for MASTEK or OAL that
session and silently served the previous day's. That turned MASTEK's 43.9x volume
day into **0.9x** — not an error, a plausible-looking normal reading. A daily
volume scanner built on that misses exactly the days it exists to find.

The NSE bhavcopy carries the whole market (~2,600 EQ rows) in one free file, with
volume, traded value, close and previous close — so the multiple, the turnover and
the one-day return all come from it. yfinance is used **only** for the one-year
baseline, and only for the shortlist that already cleared the turnover filter.

The cause taxonomy
------------------
``PROP_CHURN`` is the one that earns this module its keep. On 2026-08-28, four of
the five names on a widely-shared "volume is the story" card appeared in the NSE
bulk-deal file with the *same* prop desks on both sides — MASTEK: MICROCURVES
TRADING bought 264,122 and sold 264,122 the same day; OMAXE: JUNOMONETA FINSOL
bought 1,084,016 and sold 1,086,607. Matched same-day two-way flow of near-identical
size is **market-making round-tripping**: the same shares changing hands repeatedly,
inflating the multiple without representing directional interest.

Measure it before believing it, though: MASTEK's visible round-trip is 528,244
shares against 5,449,060 traded — **9.7%**, not the whole story. And because NSE
only requires a bulk deal to be reported when a client trades >0.5% of listed
shares, that 9.7% is a **lower bound**: desks below the threshold never appear.
So churn is reported as a share on every row, and only becomes the headline cause
above `CHURN_SHARE_MIN`.

    CORPORATE_ACTION  a material COMPANY filing lands in the window before the
                      spike -- exchange "Spurt in Volume" notices are excluded,
                      because they are consequences of the spike, not causes
    PROP_CHURN        matched two-way bulk-deal flow explains a large share of it
    DEAL_DRIVEN       bulk/block deals present, but one-sided (real transfer)
    UNEXPLAINED       none of the above -- the interesting bucket, and the one
                      most likely to be an information event nobody filed yet

A spike from a dividend record date is arithmetic. A spike from prop churn is
liquidity provision. Only ``UNEXPLAINED`` (and to a lesser extent ``DEAL_DRIVEN``)
is a question worth carrying further.

> [!warning] Unvalidated, and one hard operational limit.
> No forward return study has been run: nothing here says an UNEXPLAINED spike
> precedes anything. Separately, **the NSE bulk/block deal endpoints return only
> the current day** — there is no history in them — so attribution can only be done
> on the day, or from an archive this module does not yet keep. Running it on a
> past date will find the volume but not the deals.

Usage
-----
    from volume_anomaly import scan
    res = scan(min_multiple=10.0, min_turnover_cr=5.0)

    py -3 tools/volume_anomaly.py --min-multiple 15 --explain
    py -3 tools/volume_anomaly.py --top 40 --json spikes.json
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Callable, Iterable

log = logging.getLogger(__name__)

CORPORATE_ACTION = "CORPORATE_ACTION"
PROP_CHURN = "PROP_CHURN"
DEAL_DRIVEN = "DEAL_DRIVEN"
UNEXPLAINED = "UNEXPLAINED"
CAUSE_ORDER = (UNEXPLAINED, DEAL_DRIVEN, PROP_CHURN, CORPORATE_ACTION)

#: Filings the EXCHANGE initiates *because* volume or price moved. These are
#: CAUSED BY the spike, not causes of it, and counting them is circular: NSE files
#: a "Spurt in Volume" notice for essentially every volume spike, so without this
#: exclusion almost everything classifies as CORPORATE_ACTION and UNEXPLAINED --
#: the bucket that actually deserves attention -- is starved. Found in the first
#: live run: 7 of 9 CORPORATE_ACTION labels were exchange clarification requests.
#: Checked BEFORE the material list, and an announcement matching here is dropped.
REACTIVE_SUBJECTS = (
    "spurt in volume", "spurt in price", "price movement", "volume movement",
    "clarification", "clarification sought", "newspaper publication",
    "trading window", "compliance certificate", "reply to", "surveillance",
    "asm ", "gsm ", "graded surveillance",
)

#: Filing subjects that plausibly move a day's volume. Matched case-insensitively
#: against the announcement subject AND its detail line. Deliberately broad: a
#: false CORPORATE_ACTION merely says "there was a filing, go read it", whereas a
#: missed one promotes a name into UNEXPLAINED, which is the bucket that gets
#: attention. The asymmetry favours over-matching.
MATERIAL_SUBJECTS = (
    "dividend", "record date", "bonus", "stock split", "sub-division", "buyback",
    "buy back", "amalgamation", "merger", "demerger", "acquisition", "open offer",
    "scheme of arrangement", "preferential", "fund rais", "qip", "rights issue",
    "allotment", "financial result", "outcome of board", "order", "contract",
    "letter of intent", "capacity", "expansion", "land", "plant", "credit rating",
    "resignation", "appointment of", "delisting", "show cause", "penalty",
    "insolvency", "nclt", "sebi", "investor presentation",
)

#: Two bulk-deal quantities count as a matched round-trip when the smaller is at
#: least this fraction of the larger. Exact equality is common but not universal --
#: a desk may end the day a few thousand shares long.
CHURN_MATCH_RATIO = 0.80
#: Churn has to explain at least this share of the day's volume before it becomes
#: the HEADLINE cause. Below it the name is DEAL_DRIVEN with the churn share still
#: printed -- because the bulk-deal file only carries trades above NSE's 0.5%-of-
#: listed-shares reporting threshold, so measured churn is always a lower bound and
#: a low reading is weak evidence of absence. Not fitted to any example: on the
#: real 2026-08-28 rows MASTEK's visible churn is 9.7%, i.e. below this line.
CHURN_SHARE_MIN = 0.15


@dataclass
class SpikeParams:
    min_multiple: float = 10.0        # volume vs its own 1-year average
    min_turnover_cr: float = 2.0      # ignore illiquid names where 20x is noise
    baseline_days: int = 250
    min_baseline_days: int = 60       # below this the average means little
    announcement_window_days: int = 7
    prefilter_top_n: int = 400        # bhavcopy names by turnover to fetch history for

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ──────────────────────────────────────────────────────────────────────────────
# Attribution — pure functions, no network
# ──────────────────────────────────────────────────────────────────────────────
def _norm_qty(v: Any) -> float | None:
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def detect_prop_churn(deals: list[dict], day_volume: float | None) -> dict[str, Any]:
    """Matched same-day two-way flow by one client = market-making round-trip.

    `deals` are bulk/block rows for ONE symbol on the spike date. Returns the
    churned quantity and what share of the day's volume it accounts for. The
    churn is counted **twice** against volume on purpose: a round-trip prints on
    the tape as both a buy and a sell, so 100 shares bought and sold contribute
    200 to reported volume.
    """
    by_client: dict[str, dict[str, float]] = {}
    for d in deals:
        client = str(d.get("Client Name") or d.get("client") or "").strip().upper()
        side = str(d.get("Buy/Sell") or d.get("side") or "").strip().upper()
        qty = _norm_qty(d.get("Quantity Traded") or d.get("qty"))
        if not client or qty is None:
            continue
        bucket = by_client.setdefault(client, {"BUY": 0.0, "SELL": 0.0})
        if side.startswith("B"):
            bucket["BUY"] += qty
        elif side.startswith("S"):
            bucket["SELL"] += qty

    churn_qty = 0.0
    churners: list[str] = []
    for client, sides in by_client.items():
        b, s = sides["BUY"], sides["SELL"]
        if b <= 0 or s <= 0:
            continue
        lo, hi = min(b, s), max(b, s)
        if hi > 0 and lo / hi >= CHURN_MATCH_RATIO:
            churn_qty += lo
            churners.append(client)

    share = (churn_qty * 2 / day_volume) if (day_volume and churn_qty) else None
    return {"churn_qty": churn_qty or None,
            "churn_share": None if share is None else round(share, 4),
            "churners": churners}


def match_announcements(anns: list[dict], spike_date: datetime,
                        window_days: int = 7) -> list[dict]:
    """Material filings dated within `window_days` BEFORE the spike (inclusive).

    Filings after the spike are excluded: a scanner that credits tomorrow's
    announcement for today's volume is reading the future.
    """
    lo = spike_date - timedelta(days=window_days)
    hits = []
    for a in anns or []:
        raw = str(a.get("date") or "")
        dt = None
        for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw.strip(), fmt)
                break
            except ValueError:
                continue
        if dt is None or not (lo <= dt <= spike_date + timedelta(days=1)):
            continue
        blob = f"{a.get('subject', '')} {a.get('detail', '')}".lower()
        subj = str(a.get("subject") or "")
        # Exchange-initiated notices are consequences of the spike. Dropping them
        # BEFORE the material test matters, because their detail text quotes the
        # company's reply and routinely contains material keywords.
        if any(k in blob for k in REACTIVE_SUBJECTS):
            continue
        if any(k in blob for k in MATERIAL_SUBJECTS):
            # 160 used to truncate mid-number — SAMBHV's warrant count sat at
            # character 158. The headline builder does its own trimming.
            hits.append({"date": raw, "subject": subj,
                         "detail": str(a.get("detail") or "")[:400]})
    return hits


#: The boilerplate every NSE announcement text opens with. Stripping it is the
#: difference between "Sambhv Steel Tubes Limited has informed the Exchange about
#: the general updates relating to the proposed preferential issue of 8,695,400
#: fully convertible warrants" and the only part a reader needs.
_BOILERPLATE = re.compile(
    r"^\s*(?:the\s+)?(?:company|[\w&.\-' ]{2,60}?(?:limited|ltd\.?|corporation|corp\.?))?"
    r"\s*has\s+(?:informed|submitted|intimated)\s+"
    r"(?:(?:to\s+)?the\s+exchange\s*)?"
    r"(?:about|regarding|that|a\s+copy\s+of|the)?\s*[:\-]?\s*",
    re.I)

#: A detail line that only repeats its own category tells the reader nothing the
#: category did not. Compared after normalising case and punctuation.
def _informative(detail: str, subject: str) -> bool:
    d = re.sub(r"[^a-z0-9 ]", " ", detail.lower()).split()
    s_ = re.sub(r"[^a-z0-9 ]", " ", subject.lower()).split()
    if not d:
        return False
    if len(d) <= len(s_) + 1 and set(d) <= set(s_) | {"general", "updates", "update"}:
        return False
    return True


def filing_headline(subject: str, detail: str, max_len: int = 160) -> str:
    """The most informative line available for one filing (B-51r).

    NSE's `desc` is a CATEGORY — and for a third of filings it is the useless
    "General Updates", which is what this module printed until 2026-09-21. The
    same payload carries `attchmntText`, whose first sentence is often the actual
    event: *"the proposed preferential issue of 8,695,400 fully convertible
    warrants"* against a `desc` of "General Updates". Checked against the
    2026-09-21 card, that single field is the "why" for SAMBHV.

    The amounts in the attachment PDF (order-book totals, contract values) are
    still not here — those need the file itself, which nothing parses.

    Returns `"Category — the specific bit"`, or just the category when the text
    adds nothing to it.
    """
    subject = (subject or "").strip()
    body = _BOILERPLATE.sub("", (detail or "").strip()).strip(" .:-")
    # NSE often opens the text by repeating the category verbatim. Saying it
    # twice in one line is how a 130-character budget gets spent on nothing.
    if subject and body.lower().startswith(subject.lower()):
        body = body[len(subject):].strip(" .:-")
    if not body or not _informative(body, subject):
        return subject or "filing"
    body = body[0].upper() + body[1:] if body else body
    if len(body) > max_len:
        body = body[:max_len].rsplit(" ", 1)[0] + "…"
    return f"{subject} — {body}" if subject else body


def classify_cause(announcements: list[dict], churn: dict[str, Any],
                   n_deals: int) -> tuple[str, list[str]]:
    """Attribute a spike. Order matters: a filing outranks flow, because a filing
    explains WHY the flow happened while the flow only says that it did."""
    reasons: list[str] = []
    if announcements:
        for a in announcements[:3]:
            reasons.append(
                f"filing {a['date']}: "
                f"{filing_headline(a.get('subject', ''), a.get('detail', ''))}")
        return CORPORATE_ACTION, reasons

    share = churn.get("churn_share")
    if share is not None and share >= CHURN_SHARE_MIN:
        who = ", ".join(churn["churners"][:2])
        reasons.append(f"matched two-way bulk-deal flow explains {share:.0%} of "
                       f"the day's volume ({who}) - market-making round-trip, "
                       f"not accumulation")
        return PROP_CHURN, reasons

    if n_deals:
        if share:
            # Partial churn still belongs on the row. NSE only requires a bulk
            # deal to be reported when a client trades >0.5% of listed shares in
            # a day, so what the file shows is a LOWER BOUND on round-tripping --
            # the desks below that threshold never appear at all.
            reasons.append(f"{n_deals} bulk/block deal row(s); matched two-way flow "
                           f"accounts for {share:.0%} of volume - partly churn, and "
                           f"that share is a lower bound (only trades above NSE's "
                           f"0.5% reporting threshold appear)")
        else:
            reasons.append(f"{n_deals} bulk/block deal row(s), one-sided - a real "
                           f"transfer of stock rather than churn")
        return DEAL_DRIVEN, reasons

    reasons.append("no material filing in the window and no bulk/block deals - "
                   "unexplained by the free feeds")
    return UNEXPLAINED, reasons


# ──────────────────────────────────────────────────────────────────────────────
# Data access
# ──────────────────────────────────────────────────────────────────────────────
def _baseline(symbol: str, days: int) -> tuple[float | None, int]:
    """Average daily volume over the prior `days` sessions, EXCLUDING the latest.

    Including the spike day drags the mean up and understates its own multiple.
    """
    try:
        import yfinance as yf
        h = yf.Ticker(f"{symbol}.NS").history(period="2y", auto_adjust=False)
    except Exception:
        return None, 0
    if h is None or h.empty or "Volume" not in h:
        return None, 0
    vols = [float(v) for v in h["Volume"].tolist()[-(days + 1):-1] if v and v > 0]
    if not vols:
        return None, 0
    return sum(vols) / len(vols), len(vols)


def _deals_for_day() -> dict[str, list[dict]]:
    """Bulk + block deal rows keyed by symbol, for the CURRENT day only.

    The NSE endpoints carry no history, so this is same-day or nothing — stated
    in the module docstring because it silently limits back-dated runs.
    """
    out: dict[str, list[dict]] = {}
    try:
        import india_market_intel as imi
    except Exception as exc:
        log.warning("deal feed unavailable: %s", exc)
        return out
    for fn in ("fetch_nse_bulk_deals", "fetch_nse_block_deals"):
        try:
            df = getattr(imi, fn)()
        except Exception as exc:
            log.warning("%s failed: %s", fn, exc)
            continue
        if df is None or df.empty or "Symbol" not in df.columns:
            continue
        for row in df.to_dict("records"):
            sym = str(row.get("Symbol") or "").strip().upper()
            if sym:
                out.setdefault(sym, []).append(row)
    return out


def _announcements_for(symbol: str) -> list[dict]:
    """Filings for ONE symbol.

    The Market Intel page notes the whole-market announcement feed is too high
    volume to wire up. That objection does not apply here: announcements are
    fetched only for the handful of names that already cleared the volume filter,
    so it is tens of calls, after the funnel — not thousands, before it.
    """
    try:
        import nse_announcements as na
        return na.fetch_announcements(symbol) or []
    except Exception as exc:
        log.debug("announcements failed for %s: %s", symbol, exc)
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Scan
# ──────────────────────────────────────────────────────────────────────────────
def scan(*, params: SpikeParams | None = None,
         frame=None,
         deals: dict[str, list[dict]] | None = None,
         announcements_fn: Callable[[str], list[dict]] | None = None,
         baseline_fn: Callable[[str, int], tuple[float | None, int]] | None = None,
         market_caps: dict[str, float] | None = None,
         max_workers: int = 8,
         progress_cb: Callable[[int, int, str], None] | None = None,
         ) -> dict[str, Any]:
    """Find and attribute today's volume spikes.

    Every network dependency is injectable (`frame`, `deals`, `announcements_fn`,
    `baseline_fn`) so the tests run offline.
    """
    p = params or SpikeParams()
    if frame is None:
        import screener_pipeline as sp
        frame = sp.fetch_bhavcopy_frame()
    if frame is None or len(frame) == 0:
        return {"params": p.as_dict(), "error": "no bhavcopy frame", "rows": []}

    turnover_is_qty = bool(getattr(frame, "attrs", {}).get("turnover_is_qty"))
    trade_date = None
    try:
        trade_date = str(frame["trade_date"].dropna().iloc[0])[:10]
    except Exception:
        pass

    # Pre-filter on the bhavcopy alone, so history is fetched for hundreds of
    # names rather than thousands. Ranking by turnover (not by volume) keeps
    # penny stocks with huge share counts out of the shortlist.
    cand = frame.dropna(subset=["volume"]).nlargest(p.prefilter_top_n, "turnover")
    syms = cand["symbol"].tolist()
    base_fn = baseline_fn or _baseline

    def _one(sym: str):
        avg, n = base_fn(sym, p.baseline_days)
        return sym, avg, n

    baselines: dict[str, tuple[float | None, int]] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for sym, avg, n in pool.map(_one, syms):
            baselines[sym] = (avg, n)
            done += 1
            if progress_cb is not None:
                try:
                    progress_cb(done, len(syms), sym)
                except Exception:
                    pass

    rows: list[dict[str, Any]] = []
    skipped_short_history = 0
    for r in cand.to_dict("records"):
        sym = r["symbol"]
        avg, n = baselines.get(sym, (None, 0))
        if avg is None or n < p.min_baseline_days:
            skipped_short_history += 1
            continue
        vol = float(r["volume"])
        mult = vol / avg if avg else None
        turnover_cr = float(r["turnover"]) / 1e7 if not turnover_is_qty else None
        if mult is None or mult < p.min_multiple:
            continue
        if (turnover_cr is not None and p.min_turnover_cr
                and turnover_cr < p.min_turnover_cr):
            continue
        close, prev = r.get("close"), r.get("prev_close")
        day_pct = (None if not (close and prev) else round((close / prev - 1) * 100, 2))
        mcap = (market_caps or {}).get(sym)
        rows.append({
            "symbol": sym, "volume": vol, "avg_volume": round(avg),
            "baseline_days": n, "multiple": round(mult, 1),
            "turnover_cr": None if turnover_cr is None else round(turnover_cr, 1),
            "close": close, "day_pct": day_pct,
            "pct_mcap": (None if not (mcap and turnover_cr)
                         else round(turnover_cr * 1e7 / mcap * 100, 2)),
            "trade_date": trade_date,
        })

    rows.sort(key=lambda x: -x["multiple"])

    # Attribution runs only on names that survived, which is what makes the
    # per-symbol announcement fetch affordable.
    deal_map = _deals_for_day() if deals is None else deals
    ann_fn = announcements_fn or _announcements_for
    spike_dt = datetime.now()
    if trade_date:
        try:
            spike_dt = datetime.strptime(trade_date, "%Y-%m-%d")
        except ValueError:
            pass

    for row in rows:
        sym = row["symbol"]
        sym_deals = deal_map.get(sym, [])
        churn = detect_prop_churn(sym_deals, row["volume"])
        anns = match_announcements(ann_fn(sym), spike_dt, p.announcement_window_days)
        cause, why = classify_cause(anns, churn, len(sym_deals))
        row.update({"cause": cause, "reasons": why, "n_deals": len(sym_deals),
                    "churn_share": churn.get("churn_share")})

    tally = {c: sum(1 for r in rows if r["cause"] == c) for c in CAUSE_ORDER}
    return {"params": p.as_dict(), "trade_date": trade_date,
            "universe": len(frame), "prefiltered": len(syms),
            "skipped_short_history": skipped_short_history,
            "tally": tally, "hits": len(rows), "rows": rows}


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def _f(v, nd=1):
    return "-" if v is None else f"{float(v):,.{nd}f}"


def _render(res: dict[str, Any], explain: bool = False, top: int | None = None) -> str:
    if res.get("error"):
        return f"ERROR: {res['error']}"
    rows = res["rows"][:top] if top else res["rows"]
    out = [f"Session {res.get('trade_date')} | universe {res['universe']} EQ | "
           f"prefiltered {res['prefiltered']} | spikes {res['hits']} "
           f"| skipped (short history) {res['skipped_short_history']}",
           "Cause: " + ", ".join(f"{k}={v}" for k, v in res["tally"].items() if v),
           "",
           f"{'SYMBOL':<14}{'VOL x':>8}{'TURNOVER Cr':>13}{'1-DAY %':>9}"
           f"{'%MCAP':>8}  {'CAUSE':<17}"]
    for r in rows:
        out.append(f"{r['symbol']:<14}{_f(r['multiple']):>8}{_f(r['turnover_cr']):>13}"
                   f"{_f(r['day_pct'], 2):>9}{_f(r['pct_mcap'], 1):>8}  "
                   f"{r['cause']:<17}")
        if explain:
            for why in r.get("reasons", []):
                out.append(f"{'':<14}  - {why}")
    if not rows:
        out.append("  (no spikes cleared the thresholds)")
    out += ["",
            "A SCREEN, not a trigger - no entry, stop or target, and no BUY/SELL",
            "implication. Attribution uses same-day NSE feeds; deal data has no",
            "history, so back-dated runs find the volume but not the deals."]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Whole-market volume spikes, with cause")
    ap.add_argument("--min-multiple", type=float, default=10.0)
    ap.add_argument("--min-turnover-cr", type=float, default=2.0)
    ap.add_argument("--prefilter-top-n", type=int, default=400)
    ap.add_argument("--top", type=int, default=None, help="print only the top N")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--explain", action="store_true")
    ap.add_argument("--json", metavar="PATH")
    args = ap.parse_args(argv)

    p = SpikeParams(min_multiple=args.min_multiple,
                    min_turnover_cr=args.min_turnover_cr,
                    prefilter_top_n=args.prefilter_top_n)
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    def _progress(done, total, _s):
        if done % 50 == 0 or done == total:
            print(f"  ... baselines {done}/{total}", file=sys.stderr)

    res = scan(params=p, max_workers=args.workers, progress_cb=_progress)
    print(_render(res, explain=args.explain, top=args.top))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, default=str)
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
