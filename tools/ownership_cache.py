"""ownership_cache.py — quarterly ownership history, cached and backfillable.

SR-2, SR-3 and SR-5 of [[analyses/Sector-Rotation-Orbit-Data-Source-Roadmap]].

What this replaces
------------------
The Historical Sector Rotation Orbit chart takes a *wide* frame — one
`FII_<quarter>` column per quarter — which until now could only come from a
hand-driven screener.in export behind a browser session. Everything it needs is
in NSE's SEBI shareholding XBRL, which `nse_shareholding_fetch` already parses
and which needs no login. The only thing missing was somewhere to put ~8
quarters × ~500 symbols without re-fetching it on every run.

Why a cache is the whole design
-------------------------------
**A filing is immutable once filed.** RELIANCE's 30-JUN-2026 shareholding pattern
will never change, so a `(symbol, period)` entry is valid forever and the ~2-hour
first backfill is paid exactly once. Later runs cost one filing-master request
per symbol plus one XBRL for whatever quarter is new — roughly 25 minutes a
quarter, not two hours.

Revised filings are the one exception, and `get_shareholding_filings` already
de-duplicates them by period keeping the newest broadcast, so a revision
overwrites its period rather than appearing as an extra quarter with zero change.

NSE rate-limits aggressively, so every network call is paced and the backfill is
**resumable**: it writes each symbol's file as soon as that symbol completes, so
an interrupted run resumes with only the symbols it had not reached.

Run it
------
    py -3 tools/ownership_cache.py --backfill --quarters 8            # Nifty 500
    py -3 tools/ownership_cache.py --backfill --limit 25 --quarters 6 # bounded
    py -3 tools/ownership_cache.py --status
    py -3 tools/ownership_cache.py --emit sector_rotation_input.csv
"""

from __future__ import annotations

import argparse
import calendar
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nse_shareholding_fetch as nsf
import nse_universe as nseu

log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
BASE_DIR = HERE.parent
CACHE_DIR = HERE / "cache" / "ownership"

#: Seconds between network calls. `nse_shareholding_fetch` uses the same pacing;
#: NSE starts refusing well before this becomes a throughput problem.
SLEEP = 1.5

#: Legs stored per quarter. The wide frame only needs `fii`, but the marginal
#: cost of keeping the rest is zero — it is already parsed — and DS-3/DS-4 want
#: DII and retail. Re-fetching two years of filings to add a column later would
#: not be.
STORE_LEGS = ("fii", "dii", "mf", "retail", "promoter", "public",
              "fpi_cat1", "fpi_cat2", "shares_total")


# ──────────────────────────────────────────────────────────────────────────────
# Cache primitives
# ──────────────────────────────────────────────────────────────────────────────
def _path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol.upper()}.json"


def load(symbol: str) -> dict:
    """{"symbol", "quarters": {period: legs}, "updated"}; empty shell if absent."""
    p = _path(symbol)
    if not p.exists():
        return {"symbol": symbol.upper(), "quarters": {}, "updated": None}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("[%s] cache unreadable, treating as empty: %s", symbol, e)
        return {"symbol": symbol.upper(), "quarters": {}, "updated": None}


def save(symbol: str, data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    tmp = _path(symbol).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(_path(symbol))   # atomic, so an interrupted write cannot truncate


def quarter_label(period: str) -> str | None:
    """'30-JUN-2026' -> '2026Q2'. The label `sector_rotation_trail` parses."""
    d = nsf._period_date(period)
    return None if d is None else f"{d.year}Q{(d.month - 1) // 3 + 1}"


def is_quarter_end(period: str) -> bool:
    """True only for a regular quarterly filing period.

    Companies also file a shareholding pattern on capital-change events, and NSE
    returns those in the same list: RELIANCE has 29-OCT-2024, HDFCBANK
    28-AUG-2025, INFY 04-DEC-2025. They are real filings but they are not
    quarters, and `quarter_label` maps them onto the *same* label as the true
    quarter end — 29-OCT-2024 and 31-DEC-2024 both read 2024Q4. In a dict-keyed
    wide frame the second one silently overwrites the first, so a chart would
    have been drawn from whichever happened to be written last.

    Dropping them also keeps `--quarters N` meaning N quarters, rather than N
    filings of which some are events.
    """
    d = nsf._period_date(period)
    if d is None or d.month not in (3, 6, 9, 12):
        return False
    return d.day == calendar.monthrange(d.year, d.month)[1]


# ──────────────────────────────────────────────────────────────────────────────
# SR-2 — fetch one symbol, fetching only what the cache lacks
# ──────────────────────────────────────────────────────────────────────────────
def fetch_symbol(symbol: str, session=None, quarters: int = 8,
                 force: bool = False) -> dict:
    """Ensure the newest `quarters` filings for `symbol` are cached; return it.

    Only periods absent from the cache are fetched. The filing-master call is
    unavoidable — it is how we learn a new quarter exists — but it is one request
    against `quarters` XBRLs saved.
    """
    symbol = symbol.upper()
    data = load(symbol)
    session = session or nsf._new_session()

    filings = nsf.get_shareholding_filings(session, symbol)
    if not filings:
        data.setdefault("quarters", {})
        data["no_filings"] = True
        save(symbol, data)
        return data
    data.pop("no_filings", None)

    # Quarter ends only, filtered BEFORE the top-N slice so `quarters` counts
    # quarters rather than filings (see is_quarter_end).
    wanted = [f for f in filings if is_quarter_end(f.get("date", ""))][:max(1, quarters)]
    fetched = 0
    for f in wanted:
        period = f.get("date")
        if not force and period in data["quarters"]:
            continue                      # immutable — never re-fetch
        parsed = nsf._fetch_filing(session, f, symbol)
        time.sleep(SLEEP)
        if not parsed:
            continue
        row = {leg: parsed.get(leg) for leg in STORE_LEGS}
        row["reconciles"] = bool(parsed["checks"].get("promoter_matches_master")
                                 and parsed["checks"].get("totals_to_100"))
        row["filed_on"] = parsed.get("filed_on")
        row["quarter"] = quarter_label(period)
        data["quarters"][period] = row
        fetched += 1

    # Purge anything a previous run cached that this filter now rejects, so an
    # existing cache is corrected in place rather than carrying event filings
    # forward forever.
    stale = [p for p in data["quarters"] if not is_quarter_end(p)]
    for p in stale:
        del data["quarters"][p]
    if stale:
        fetched += 1   # force a save

    if fetched:
        save(symbol, data)
    return data


def backfill(symbols: list[str], quarters: int = 8, force: bool = False,
             progress_every: int = 10) -> dict:
    """Walk `symbols`, caching each. Resumable: a symbol is written as it lands.

    Returns counts rather than raising, because a backfill that stops on the
    first unreachable symbol is useless — but a run where *nothing* succeeded is
    a broken run and says so.
    """
    session = nsf._new_session()
    stats = {"symbols": len(symbols), "ok": 0, "no_filings": 0, "errors": 0,
             "quarters_cached": 0, "started": datetime.now().isoformat(timespec="seconds")}
    t0 = time.time()

    for i, sym in enumerate(symbols, 1):
        try:
            before = len(load(sym).get("quarters", {}))
            data = fetch_symbol(sym, session=session, quarters=quarters, force=force)
            after = len(data.get("quarters", {}))
            stats["quarters_cached"] += max(0, after - before)
            if data.get("no_filings"):
                stats["no_filings"] += 1
            elif after:
                stats["ok"] += 1
            else:
                stats["errors"] += 1
        except Exception as e:
            log.warning("[%s] backfill error: %s", sym, e)
            stats["errors"] += 1
        time.sleep(SLEEP)

        if i % progress_every == 0 or i == len(symbols):
            rate = (time.time() - t0) / i
            left = (len(symbols) - i) * rate
            log.info("%d/%d  ok=%d no-filings=%d err=%d  +%d quarters  ~%.0f min left",
                     i, len(symbols), stats["ok"], stats["no_filings"],
                     stats["errors"], stats["quarters_cached"], left / 60)

    stats["elapsed_min"] = round((time.time() - t0) / 60, 1)
    if symbols and stats["ok"] == 0:
        raise RuntimeError(
            f"Backfill cached nothing from {len(symbols)} symbols "
            f"({stats['no_filings']} had no filings, {stats['errors']} errored). "
            "NSE is most likely blocking or rate-limiting this host.")
    return stats


def status() -> dict:
    """What the cache currently holds."""
    if not CACHE_DIR.exists():
        return {"symbols": 0, "quarters_total": 0, "periods": [], "dir": str(CACHE_DIR)}
    syms, periods, total, unrec = 0, set(), 0, 0
    for p in CACHE_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        qs = d.get("quarters", {})
        if not qs:
            continue
        syms += 1
        total += len(qs)
        periods.update(qs)
        unrec += sum(1 for r in qs.values() if not r.get("reconciles"))
    return {"symbols": syms, "quarters_total": total,
            "periods": sorted(periods, key=lambda s: nsf._period_date(s) or datetime.min),
            "non_reconciling": unrec, "dir": str(CACHE_DIR)}


# ──────────────────────────────────────────────────────────────────────────────
# SR-5 — quarter-end prices, so a historical quarter is weighted by the cap it
# actually had rather than by today's
# ──────────────────────────────────────────────────────────────────────────────
def quarter_end_prices(symbols: list[str], periods: list[str],
                       batch: int = 40) -> dict[str, dict[str, float]]:
    """{symbol: {period: close on/just before that quarter end}}.

    Batched: yfinance takes many tickers per request, so 500 names cost ~13 calls
    rather than 500. A symbol whose history does not reach a period simply has no
    entry for it, and the caller falls back rather than inventing a price.
    """
    import yfinance as yf

    dates = sorted({d for d in (nsf._period_date(p) for p in periods) if d})
    if not dates or not symbols:
        return {}
    start = (min(dates) - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    out: dict[str, dict[str, float]] = {}

    for i in range(0, len(symbols), batch):
        chunk = [f"{s}.NS" for s in symbols[i:i + batch]]
        try:
            df = yf.download(chunk, start=start, interval="1d",
                             progress=False, auto_adjust=True, group_by="ticker")
        except Exception as e:
            log.warning("price batch %d failed: %s", i // batch, e)
            continue
        if df is None or df.empty:
            continue
        for tkr in chunk:
            sym = tkr[:-3]
            try:
                closes = df[tkr]["Close"] if isinstance(df.columns, pd.MultiIndex) else df["Close"]
            except Exception:
                continue
            closes = closes.dropna()
            if closes.empty:
                continue
            closes.index = pd.to_datetime(closes.index).tz_localize(None)
            per_sym = {}
            for p in periods:
                d = nsf._period_date(p)
                if d is None:
                    continue
                # asof: the last close at or before the quarter end, so a quarter
                # ending on a weekend or holiday still gets a real traded price.
                v = closes.asof(pd.Timestamp(d))
                if pd.notna(v):
                    per_sym[p] = float(v)
            if per_sym:
                out[sym] = per_sym
    return out


# ──────────────────────────────────────────────────────────────────────────────
# SR-3 — the wide frame the orbit chart consumes
# ──────────────────────────────────────────────────────────────────────────────
def build_wide_frame(symbols: list[str] | None = None, quarters: int = 8,
                     index: str = "nifty500",
                     historical_caps: bool = True) -> pd.DataFrame:
    """The `FII_<quarter>` wide frame `sector_rotation_trail.load_wide_export`
    reads, built from the cache with no network call for the ownership side.

    Emits, per symbol: Name · Industry · Mar Cap · FII_<q>… and, when
    `historical_caps`, CAP_<q>… so the trail can weight each quarter by the cap
    that quarter actually had (SR-5) instead of by today's.
    """
    ind_map = nseu.industry_map(index)
    if symbols is None:
        symbols = [s for s in nseu.symbols(index)]

    rows, all_periods = [], set()
    per_symbol: dict[str, dict] = {}
    for sym in symbols:
        qs = load(sym).get("quarters", {})
        if not qs:
            continue
        # Newest `quarters` periods only, oldest-first for stable column order.
        ordered = sorted(qs, key=lambda p: nsf._period_date(p) or datetime.min)[-quarters:]
        # A row that failed its own promoter/public cross-check against the
        # filing master does not enter a chart. That check is the only free
        # correctness signal available here, and it is what caught the 100×
        # scale bug — honouring it costs a few rows and buys the axis.
        keep = {p: qs[p] for p in ordered
                if qs[p].get("fii") is not None and qs[p].get("reconciles")}
        if len(keep) < 2:          # a trail needs at least one delta
            continue
        per_symbol[sym] = keep
        all_periods.update(keep)

    if not per_symbol:
        return pd.DataFrame()

    periods = sorted(all_periods, key=lambda p: nsf._period_date(p) or datetime.min)
    prices = quarter_end_prices(list(per_symbol), periods) if historical_caps else {}

    for sym, keep in per_symbol.items():
        row = {"Name": sym, "Industry": ind_map.get(sym)}
        latest = max(keep, key=lambda p: nsf._period_date(p) or datetime.min)
        for p, legs in keep.items():
            q = legs.get("quarter") or quarter_label(p)
            if not q:
                continue
            row[f"FII_{q}"] = legs.get("fii")
            sh, px = legs.get("shares_total"), prices.get(sym, {}).get(p)
            if sh and px:
                row[f"CAP_{q}"] = round(sh * px / 1e7, 2)     # rupees crore
        # Static Mar Cap stays, both as the legacy column every existing reader
        # expects and as the fallback for any quarter with no historical cap.
        sh_l, px_l = keep[latest].get("shares_total"), prices.get(sym, {}).get(latest)
        row["Mar Cap"] = (round(sh_l * px_l / 1e7, 2) if sh_l and px_l
                          else nseu.market_cap(sym) and round(nseu.market_cap(sym) / 1e7, 2))
        rows.append(row)

    df = pd.DataFrame(rows)
    fii_cols = sorted([c for c in df.columns if c.startswith("FII_")],
                      key=lambda c: pd.Period(c[4:], freq="Q"))
    cap_cols = sorted([c for c in df.columns if c.startswith("CAP_")],
                      key=lambda c: pd.Period(c[4:], freq="Q"))
    return df[["Name", "Industry", "Mar Cap"] + fii_cols + cap_cols]


def emit_csv(path: Path, **kw) -> pd.DataFrame:
    df = build_wide_frame(**kw)
    if df.empty:
        raise RuntimeError(
            "Cache produced no usable rows. Run --backfill first, or widen "
            "--quarters: a symbol needs at least two quarters with an FII "
            "reading before it can contribute a delta.")
    df.to_csv(path, index=False)
    return df


# ──────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--emit", metavar="CSV")
    ap.add_argument("--symbols", nargs="*", help="explicit symbols (default: the index)")
    ap.add_argument("--index", default="nifty500")
    ap.add_argument("--limit", type=int, help="first N symbols only — for a bounded run")
    ap.add_argument("--quarters", type=int, default=8)
    ap.add_argument("--force", action="store_true", help="re-fetch cached periods")
    ap.add_argument("--no-historical-caps", action="store_true")
    a = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    if a.status:
        st = status()
        print(f"{st['symbols']} symbols · {st['quarters_total']} cached quarters "
              f"· {st.get('non_reconciling', 0)} not reconciling")
        print(f"periods: {', '.join(st['periods'])}" if st["periods"] else "empty")
        print(f"dir: {st['dir']}")
        return 0

    if a.backfill:
        syms = a.symbols or nseu.symbols(a.index)
        if a.limit:
            syms = syms[:a.limit]
        if not syms:
            print("No symbols — the constituent list did not load.", file=sys.stderr)
            return 1
        log.info("backfilling %d symbols × %d quarters (~%.0f min if nothing cached)",
                 len(syms), a.quarters, len(syms) * (a.quarters + 1) * SLEEP / 60)
        st = backfill(syms, quarters=a.quarters, force=a.force)
        print(json.dumps(st, indent=1))
        return 0

    if a.emit:
        df = emit_csv(Path(a.emit), symbols=a.symbols, quarters=a.quarters,
                      index=a.index, historical_caps=not a.no_historical_caps)
        print(f"wrote {a.emit}: {len(df)} rows × {len(df.columns)} cols")
        print(f"columns: {', '.join(df.columns)}")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
