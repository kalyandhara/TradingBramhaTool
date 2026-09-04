#!/usr/bin/env python3
"""
nse_shareholding_fetch.py
Shareholding-pattern reader — the ownership leg (Filter C) of the Crash-Proof
3-Filter System, plus the FII-change input sector_rotation.py expects.

Source: NSE's public `corporate-share-holdings-master` endpoint lists every
quarterly shareholding filing per symbol with a link to its XBRL, and the XBRL
is the SEBI-mandated `in-bse-shp` taxonomy — the regulatory filing itself, not a
third-party recomputation. No login, no cookie.

DS-2 (2026-08-01) — what changed and why it matters
---------------------------------------------------
This module used to guess. `parse_fii_pct` tried four regexes that assumed the
category name sat inside the fact's own tag, and the docstring admitted none of
it had ever run against live NSE. Run against a real filing, all four match
NOTHING and return None — which means `build_dataset` returned an EMPTY frame
for every symbol it was ever pointed at, silently, because a None just skips.

The actual XBRL is **dimensional**: one repeated fact tag,
`ShareholdingAsAPercentageOfTotalNumberOfShares`, whose category lives in the
`contextRef` it points at, as an `explicitMember` on `CategoryOfShareholdersAxis`.
So the parse is: build contextRef -> member from the context definitions, then
read each fact through it. That yields the WHOLE split — promoter, FPI, DII,
mutual funds, insurance, banks, pension, retail — not just an FII number.

Verified live 2026-08-01 against RELIANCE, TCS, TITAN, CUPID and SHADOWFAX
(large / mid / small / recent listing). Every one reconciles: the parsed
promoter and public percentages equal the `pr_and_prgrp` / `public_val` fields
the filing-master endpoint reports independently, and the categories total
100.00%. `parse_shareholding` returns those cross-checks with the data so a
caller can refuse a filing that does not reconcile rather than trust it.

Values in the XBRL are fractions (0.5048); everything here is percent (50.48).

Caveats that remain
  - Filers omit zero rows, so a category absent from a filing comes back None,
    not 0.0 — a category nobody filed is not a measured zero.
  - Ownership is QUARTERLY and lags the market by weeks. Every reading carries
    its filing period; never present it as current positioning.
  - NSE rate-limits aggressively; the fetchers sleep between requests.

Run manually:
  py -3 tools/nse_shareholding_fetch.py --ownership RELIANCE TCS
  py -3 tools/nse_shareholding_fetch.py SYMBOL1 SYMBOL2 ...
  py -3 tools/nse_shareholding_fetch.py --top200    # use Bhavcopy top-200 list

Output (the non-`--ownership` modes): nse_fii_change_<date>.csv in the shape
sector_rotation.py expects (Name, Mar Cap, Change in FII holding %, Industry):
  py -3 tools/sector_rotation.py nse_fii_change_<date>.csv
"""

import re
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nse_universe as nseu

BASE_DIR = Path(__file__).resolve().parent.parent

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
    "X-Requested-With": "XMLHttpRequest",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
log = logging.getLogger(__name__)


def _new_session() -> requests.Session:
    s = requests.Session()
    try:
        s.get("https://www.nseindia.com/", headers=HEADERS, timeout=15)
        s.get("https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
              headers=HEADERS, timeout=15)
    except Exception as e:
        log.warning("Session warmup failed: %s", e)
    return s


def get_shareholding_filings(session: requests.Session, symbol: str) -> list[dict]:
    """Returns recent shareholding-pattern filings for a symbol, newest first."""
    url = "https://www.nseindia.com/api/corporate-share-holdings-master"
    try:
        r = session.get(url, headers=HEADERS, params={"index": "equities", "symbol": symbol}, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("[%s] filing-master fetch failed: %s", symbol, e)
        return []

    filings = data if isinstance(data, list) else data.get("data", [])
    filings = [f for f in filings if f.get("symbol", "").upper() == symbol.upper()]

    # These records carry `date` ("30-JUN-2026"), not `toDate` — the old sort key
    # was absent on every row, so this list was ordered only by luck. Sort on the
    # parsed period, then drop revisions of a period we already have (a revised
    # filing is republished under the SAME date and would otherwise read as an
    # extra quarter with zero change).
    filings.sort(key=lambda f: (_period_date(f.get("date")) or datetime.min,
                                str(f.get("broadcastDate") or "")), reverse=True)
    deduped, seen = [], set()
    for f in filings:
        d = f.get("date")
        if d in seen:
            continue
        seen.add(d)
        deduped.append(f)
    return deduped


def _period_date(s: str | None) -> datetime | None:
    """'30-JUN-2026' -> datetime. Returns None on anything unexpected."""
    if not s:
        return None
    try:
        return datetime.strptime(str(s).strip(), "%d-%b-%Y")
    except ValueError:
        return None


# ── XBRL parse ────────────────────────────────────────────────────────────────
#: Our key -> the `CategoryOfShareholdersAxis` member that carries it, in SEBI's
#: in-bse-shp taxonomy. Confirmed present across five live filings 2026-08-01.
#
# Values are ALIAS TUPLES, first match wins, because the taxonomy is not stable
# across vintages. The one that cost real debugging time: filings up to about
# Q4-2024 spell it `...PortfolioInvestorCat**er**goryOneMember` — "Catergory",
# a typo in SEBI's own schema — and later ones spell it correctly. Matching only
# the correct spelling returned `fii: None` for every older filing, which the
# DS-2 verification never saw because it only ever read *latest* filings.
CATEGORY_MEMBERS = {
    "promoter":         ("ShareholdingOfPromoterAndPromoterGroupMember",),
    "public":           ("PublicShareholdingMember",),
    "total":            ("ShareholdingPatternMember",),
    # foreign
    "fpi_cat1":         ("InstitutionsForeignPortfolioInvestorCategoryOneMember",
                         "InstitutionsForeignPortfolioInvestorCatergoryOneMember"),
    "fpi_cat2":         ("InstitutionsForeignPortfolioInvestorCategoryTwoMember",
                         "InstitutionsForeignPortfolioInvestorCatergoryTwoMember"),
    "fdi":              ("ForeignDirectInvestmentMember",),
    "foreign_total":    ("InstitutionsForeignMember",),
    # domestic institutions
    "dii":              ("InstitutionsDomesticMember",),
    "mf":               ("MutualFundsOrUTIMember",),
    "insurance":        ("InsuranceCompaniesMember",),
    "banks":            ("BanksMember",),
    "pension":          ("ProvidentFundsOrPensionFundsMember",),
    "aif":              ("AlternativeInvestmentFundsMember",),
    # non-institutional
    "retail_small":     ("ResidentIndividualShareholdersHoldingNominalShareCapitalUpToRsTwoLakhMember",),
    "retail_large":     ("ResidentIndividualShareholdersHoldingNominalShareCapitalInExcessOfRsTwoLakhMember",),
    "nri":              ("NonResidentIndiansMember",),
    "bodies_corporate": ("BodiesCorporateMember",),
    "non_institutions": ("NonInstitutionsMember",),
}

#: Headline legs the ownership card reads, in display order.
HEADLINE_LEGS = ("fii", "dii", "mf", "retail", "promoter")

_PCT_FACT = re.compile(
    r'<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares\s+contextRef="([^"]+)"'
    r'[^>]*>([\d.eE+-]+)<')
# Share COUNT, for SR-5's historical cap weighting. `NumberOfFullyPaidUpEquity
# Shares` and not `NumberOfShares`: the latter is the wider fully-diluted figure
# (warrants, ESOPs, depository receipts) and on RELIANCE the category counts sum
# to only 0.983 of it, where they sum to 1.0000 of the fully-paid-up count.
_SHARES_FACT = re.compile(
    r'<in-bse-shp:NumberOfFullyPaidUpEquityShares\s+contextRef="([^"]+)"'
    r'[^>]*>([\d.eE+-]+)<')
_CONTEXT = re.compile(r'<xbrli:context id="([^"]+)">(.*?)</xbrli:context>', re.S)
_MEMBER = re.compile(r'<xbrldi:explicitMember[^>]*>([^<]+)</xbrldi:explicitMember>')
# Promoter pledge. In the PROMOTER-only context this fact = pledged shares ÷
# promoter holding (verified on ADANIENT Jul-2026: 0.0079 = 7.70M / 974.23M =
# 0.79%), i.e. the standard "promoter pledge %". Same per-filing fraction/percent
# scale as the holding percentages.
_PLEDGE_PCT_FACT = re.compile(
    r'<in-bse-shp:EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares'
    r'\s+contextRef="([^"]+)"[^>]*>([\d.eE+-]+)<')


def parse_shareholding(xbrl_text: str) -> dict | None:
    """Every shareholding category in one filing, as percentages.

    Only contexts carrying EXACTLY ONE category member are read. Filings also
    describe individual shareholders (a name dimension stacked on the category
    one); those multi-dimension contexts are the per-shareholder rows and would
    otherwise be double-counted into their own category.

    Returns None when the file yields no categories at all — an unparseable
    filing must not read as a company with no institutional holders.
    """
    if not xbrl_text:
        return None
    contexts = dict(_CONTEXT.findall(xbrl_text))
    raw: dict[str, float] = {}
    for cid, val in _PCT_FACT.findall(xbrl_text):
        members = _MEMBER.findall(contexts.get(cid, ""))
        if len(members) != 1:
            continue
        try:
            raw[members[0].split(":")[-1]] = float(val)
        except ValueError:
            continue
    if not raw:
        return None

    # SCALE IS PER FILING, read from the filing itself.
    #
    # Recent filings express these as fractions (total = 1.0); filings up to
    # roughly mid-2025 express them as percentages already (total = 100.0). The
    # parser used to multiply by 100 unconditionally, which is right for the
    # newer vintage and off by 100× for the older one — RELIANCE's Jun-2025
    # promoter stake came out as 5007% against a filed 50.07%. Invisible until a
    # backfill reached back past the changeover, because DS-2 only ever verified
    # *latest* filings.
    #
    # The filing's own total is the scale marker: ~1 means fractions, ~100 means
    # percent. Anything else is a file we do not understand, and returning None
    # is the only safe answer — a guessed scale is a 100× error wearing a
    # plausible number's clothes.
    total_raw = raw.get("ShareholdingPatternMember")
    if total_raw is None:
        pr, pu = (raw.get("ShareholdingOfPromoterAndPromoterGroupMember"),
                  raw.get("PublicShareholdingMember"))
        total_raw = (pr + pu) if (pr is not None and pu is not None) else None
    if total_raw is None:
        return None
    if 0.98 <= total_raw <= 1.02:
        scale = 100.0
    elif 98.0 <= total_raw <= 102.0:
        scale = 1.0
    else:
        log.warning("unrecognised shareholding scale (total=%s) — refusing to guess",
                    total_raw)
        return None

    by_member = {k: v * scale for k, v in raw.items()}

    # Shares outstanding at this filing period, read through the same
    # single-member context rule. This is what lets SR-5 weight a historical
    # quarter by the cap it actually had rather than by today's.
    shares_total = None
    for cid, val in _SHARES_FACT.findall(xbrl_text):
        members = _MEMBER.findall(contexts.get(cid, ""))
        if len(members) == 1 and members[0].split(":")[-1] == "ShareholdingPatternMember":
            try:
                shares_total = float(val)
            except ValueError:
                pass
            break

    def _first(aliases):
        for a in aliases:
            if by_member.get(a) is not None:
                return by_member[a]
        return None

    out: dict = {k: _first(aliases) for k, aliases in CATEGORY_MEMBERS.items()}
    out["shares_total"] = shares_total

    def _sum(*keys):
        vals = [out[k] for k in keys if out.get(k) is not None]
        return round(sum(vals), 4) if vals else None

    # "FII" today means SEBI's FPI Category I + II. FDI is deliberately excluded
    # — a strategic foreign stake is not the portfolio flow the framework reads.
    out["fii"] = _sum("fpi_cat1", "fpi_cat2")
    out["retail"] = _sum("retail_small", "retail_large")

    # Promoter pledge %, read from the promoter-only context (see _PLEDGE_PCT_FACT).
    pledge = None
    for cid, val in _PLEDGE_PCT_FACT.findall(xbrl_text):
        m = _MEMBER.findall(contexts.get(cid, ""))
        if len(m) == 1 and m[0].split(":")[-1] == "ShareholdingOfPromoterAndPromoterGroupMember":
            try:
                pledge = float(val) * scale
            except ValueError:
                pledge = None
            break
    out["promoter_pledge_pct"] = pledge

    out = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}

    # Cross-checks travel WITH the data so a caller can reject a filing that does
    # not reconcile instead of quietly trusting a bad parse.
    total = out.get("total")
    out["checks"] = {
        "categories_parsed": len(by_member),
        "total_pct": total,
        "totals_to_100": (total is not None and abs(total - 100.0) <= 0.5),
    }
    return out


def parse_fii_pct(xbrl_text: str) -> float | None:
    """FII/FPI holding % for one filing. Kept for callers of the old API."""
    parsed = parse_shareholding(xbrl_text)
    return None if not parsed else parsed.get("fii")


def _fetch_filing(session: requests.Session, filing: dict, symbol: str) -> dict | None:
    """Fetch + parse one filing, and reconcile it against the master record.

    The master row independently reports promoter and public percentages, so a
    parse that disagrees with them is a parse we should not use — this is the
    one free correctness check available without a second data source.
    """
    url = filing.get("xbrl") or filing.get("xbrlFile")
    if not url:
        return None
    try:
        r = session.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        log.warning("[%s] XBRL fetch failed (%s): %s", symbol, filing.get("date"), e)
        return None
    parsed = parse_shareholding(r.text)
    if not parsed:
        log.warning("[%s] XBRL for %s yielded no categories", symbol, filing.get("date"))
        return None

    def _close(a, b):
        # An absent category and a master value of 0 AGREE. Filers omit zero
        # rows, so a company with no promoter — HDFCBANK, and every other widely
        # held bank — parses `promoter: None` against a master `pr_and_prgrp: 0`.
        # Treating that as unverifiable marked five perfectly good quarters as
        # non-reconciling and would have dropped the symbol from the chart. The
        # stored value stays None (an unfiled category is still not a measured
        # zero); it is only this cross-check that treats them as equal.
        try:
            if a is None:
                return float(b) == 0.0
            return abs(float(a) - float(b)) <= 0.05
        except (TypeError, ValueError):
            return None

    parsed["period"] = filing.get("date")
    parsed["period_date"] = _period_date(filing.get("date"))
    parsed["filed_on"] = filing.get("broadcastDate")
    parsed["checks"]["promoter_matches_master"] = _close(
        parsed.get("promoter"), filing.get("pr_and_prgrp"))
    parsed["checks"]["public_matches_master"] = _close(
        parsed.get("public"), filing.get("public_val"))
    return parsed


def fetch_ownership(symbol: str, session: requests.Session | None = None,
                    quarters: int = 2) -> dict | None:
    """The full ownership split for `symbol` over the last `quarters` filings.

    Returns the quarters newest-first plus the quarter-over-quarter change in
    each headline leg. None when nothing could be read at all.
    """
    session = session or _new_session()
    filings = get_shareholding_filings(session, symbol)
    if not filings:
        log.warning("[%s] no shareholding filings found", symbol)
        return None

    parsed_quarters = []
    for f in filings[:max(1, quarters)]:
        p = _fetch_filing(session, f, symbol)
        if p:
            parsed_quarters.append(p)
        time.sleep(1)
    if not parsed_quarters:
        return None

    latest = parsed_quarters[0]
    previous = parsed_quarters[1] if len(parsed_quarters) > 1 else None
    change = {}
    if previous:
        for leg in HEADLINE_LEGS:
            a, b = latest.get(leg), previous.get(leg)
            change[leg] = (round(a - b, 4)
                           if isinstance(a, float) and isinstance(b, float) else None)

    return {
        "symbol": symbol.upper(),
        "quarters": parsed_quarters,
        "latest": latest,
        "previous": previous,
        "change": change,
        "as_of": latest.get("period"),
        "prev_as_of": previous.get("period") if previous else None,
        "reconciles": bool(latest["checks"].get("promoter_matches_master")
                           and latest["checks"].get("totals_to_100")),
    }


def fetch_fii_change(session: requests.Session, symbol: str) -> float | None:
    own = fetch_ownership(symbol, session=session, quarters=2)
    if not own or not own.get("previous"):
        log.warning("[%s] fewer than 2 readable filings — cannot compute change", symbol)
        return None
    return own["change"].get("fii")


# ── Filter C — the ownership-rotation read ────────────────────────────────────
#: Quarterly holdings drift in tenths of a percent; a move smaller than this is
#: filing noise, not a rotation. A starting point, not a measured threshold.
FLAT_BAND_PP = 0.10

MET, NOT_MET, UNKNOWN = "MET", "NOT_MET", "UNKNOWN"

#: Filter C as the framework states it: FII increasing · MF stable or increasing
#: · Retail decreasing · DII stable.
FILTER_C_CRITERIA = {
    "fii":    ("FII increasing",          lambda d: d > FLAT_BAND_PP),
    "mf":     ("MF stable or increasing", lambda d: d >= -FLAT_BAND_PP),
    "retail": ("Retail decreasing",       lambda d: d < -FLAT_BAND_PP),
    "dii":    ("DII stable",              lambda d: abs(d) <= FLAT_BAND_PP),
}


def direction(delta: float | None) -> str:
    """'up' / 'down' / 'flat' / 'unknown' for one leg's quarterly change."""
    if delta is None:
        return "unknown"
    if delta > FLAT_BAND_PP:
        return "up"
    if delta < -FLAT_BAND_PP:
        return "down"
    return "flat"


ARROWS = {"up": "↑", "down": "↓", "flat": "→", "unknown": "?"}


def interpret_rotation(change: dict | None) -> dict:
    """Read the quarter-over-quarter rotation — ownership ONLY.

    This deliberately stops short of the FPV combinations and of the framework's
    market × ownership gate ("FII accumulating into a WEAK market = watchlist,
    not a buy"). Both need a second axis this function cannot see: market health
    is DS-3's job, price+volume is DS-4's. Reading a rotation as a buy signal on
    its own is the exact mistake the FPV concept page warns about.
    """
    change = change or {}
    criteria, met, unknown = [], 0, 0
    for leg, (label, test) in FILTER_C_CRITERIA.items():
        d = change.get(leg)
        if d is None:
            state = UNKNOWN
            unknown += 1
        else:
            state = MET if test(d) else NOT_MET
            met += int(state == MET)
        criteria.append({"leg": leg, "label": label, "state": state, "delta": d,
                         "direction": direction(d)})

    fii, retail, mf = (direction(change.get(k)) for k in ("fii", "retail", "mf"))
    if fii == "up" and retail in ("down", "flat"):
        headline, tone = "SMART MONEY IN", "good"
        detail = ("Foreign portfolio money increased while retail did not — the "
                  "structural leg supports a long, once market health and stage agree.")
    elif fii == "down" and retail == "up":
        headline, tone = "DISTRIBUTION", "risk"
        detail = ("Institutions reduced while retail increased — supply moving from "
                  "informed to uninformed hands. The framework's avoid case.")
    elif mf == "down" and fii != "up":
        headline, tone = "MF SELLING", "risk"
        detail = ("Mutual funds reduced with no offsetting foreign buying — the "
                  "framework treats domestic-fund selling as a structural veto.")
    elif fii == "unknown" and retail == "unknown":
        headline, tone = "NOT ASSESSED", "absent"
        detail = "No comparable pair of filings — nothing can be said about rotation."
    else:
        headline, tone = "MIXED", "warn"
        detail = ("No clean rotation this quarter — the ownership leg neither "
                  "supports nor vetoes.")

    return {"headline": headline, "tone": tone, "detail": detail,
            "criteria": criteria, "n_met": met, "n_unknown": unknown,
            "flat_band_pp": FLAT_BAND_PP}


def fetch_industry_and_cap(session: requests.Session, symbol: str) -> tuple[str | None, float | None]:
    """(NSE macro-sector, market cap in ₹ crore) for a symbol. Either may be None.

    SR-0: this used to read both from `api/quote-equity`, which now returns
    **403 for every symbol** (verified 2026-08-01, 6 of 6) — and since
    `build_dataset` skips any symbol missing either field, that one dead endpoint
    was silently emptying the entire Sector Rotation pipeline. Industry now comes
    from NSE's index-constituent archive CSV (not behind the API gateway) and the
    cap from yfinance.

    `session` is kept in the signature for the existing callers; nothing here
    needs it any more.
    """
    industry = nseu.industry_map().get(symbol.upper())
    if industry is None:
        log.debug("[%s] not in the Nifty 500 constituent list", symbol)

    cap_rupees = nseu.market_cap(symbol)
    # Rupees crore, matching the old quote-equity computation and screener.in's
    # own units — the cap is only ever used as a relative weight, but the column
    # is written to CSV and read by humans.
    mar_cap = round(cap_rupees / 1e7, 2) if cap_rupees else None

    return industry, mar_cap


def build_dataset(symbols: list[str]) -> pd.DataFrame:
    """The (Name, Mar Cap, Change in FII holding %, Industry) frame
    `sector_rotation.py` consumes.

    Raises RuntimeError when every symbol failed. Returning an empty frame is
    what let the 403 hide for as long as it did: the caller printed "No data
    fetched", which reads like a quiet market rather than a broken endpoint.
    """
    session = _new_session()
    rows = []
    missed = {"fii": [], "industry": [], "cap": []}

    for i, sym in enumerate(symbols, 1):
        log.info("[%d/%d] %s", i, len(symbols), sym)
        fii_chg = fetch_fii_change(session, sym)
        if fii_chg is None:
            missed["fii"].append(sym)
            continue
        industry, mar_cap = fetch_industry_and_cap(session, sym)
        if industry is None or mar_cap is None:
            missed["industry" if industry is None else "cap"].append(sym)
            log.warning("[%s] missing %s — skipping", sym,
                        "industry" if industry is None else "market cap")
            continue
        rows.append({
            "Name": sym,
            "Mar Cap": mar_cap,
            "Change in FII holding %": fii_chg,
            "Industry": industry,
        })
        time.sleep(1.5)

    if symbols and not rows:
        raise RuntimeError(
            f"No rows built from {len(symbols)} symbol(s). "
            f"Shareholding unavailable for {len(missed['fii'])}, "
            f"industry unknown for {len(missed['industry'])}, "
            f"market cap unavailable for {len(missed['cap'])}. "
            "If industry is the whole count, the Nifty 500 constituent list did "
            "not load; if shareholding is, NSE is rate-limiting or blocking."
        )

    dropped = sum(len(v) for v in missed.values())
    if dropped:
        log.warning("built %d row(s); dropped %d (fii=%d, industry=%d, cap=%d)",
                    len(rows), dropped, len(missed["fii"]),
                    len(missed["industry"]), len(missed["cap"]))
    return pd.DataFrame(rows)


def _bhav_top200_symbols() -> list[str]:
    from screener_pipeline import fetch_bhavcopy_top_volume
    return fetch_bhavcopy_top_volume(200)


def _print_ownership(symbols: list[str]) -> int:
    session = _new_session()
    for sym in symbols:
        own = fetch_ownership(sym, session=session)
        if not own:
            print(f"\n{sym}: no readable shareholding filing.")
            continue
        latest, chg = own["latest"], own["change"]
        rot = interpret_rotation(chg)
        # ASCII only — the Windows console is cp1252 and dies on the arrows the
        # dashboard card uses.
        print(f"\n{own['symbol']} - shareholding as of {own['as_of']}"
              + (f" (vs {own['prev_as_of']})" if own["prev_as_of"] else " - no prior quarter")
              + f"   [{'reconciles' if own['reconciles'] else 'DOES NOT RECONCILE'}]")
        ascii_dir = {"up": "up  ", "down": "down", "flat": "flat", "unknown": "?   "}
        print(f"  {'leg':<10}{'held %':>9}{'chg q/q':>9}")
        for leg in HEADLINE_LEGS:
            v, d = latest.get(leg), chg.get(leg)
            print(f"  {leg:<10}{('-' if v is None else f'{v:.2f}'):>9}"
                  f"{('-' if d is None else f'{d:+.2f}'):>9}  {ascii_dir[direction(d)]}")
        print(f"  => {rot['headline']}: {rot['detail']}")
        for c in rot["criteria"]:
            mark = {MET: "yes", NOT_MET: "no ", UNKNOWN: " ? "}[c["state"]]
            print(f"      [{mark}] {c['label']}")
        time.sleep(1)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: py -3 tools/nse_shareholding_fetch.py SYMBOL1 SYMBOL2 ...\n"
                  "       py -3 tools/nse_shareholding_fetch.py --ownership SYM ...\n"
                  "       py -3 tools/nse_shareholding_fetch.py --top200")

    if sys.argv[1] == "--ownership":
        syms = [s.upper() for s in sys.argv[2:]]
        if not syms:
            sys.exit("Give at least one symbol after --ownership.")
        raise SystemExit(_print_ownership(syms))

    if sys.argv[1] == "--top200":
        symbols = _bhav_top200_symbols()
    else:
        symbols = [s.upper() for s in sys.argv[1:]]

    if not symbols:
        sys.exit("No symbols to process.")

    df = build_dataset(symbols)
    if df.empty:
        sys.exit("No data fetched — check pipeline.log-style output above for per-symbol failures.")

    out_path = BASE_DIR / f"nse_fii_change_{datetime.today().strftime('%Y%m%d')}.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved -> {out_path}")
    print(f"\nFetched {len(df)}/{len(symbols)} symbols successfully.")
    print("Next: py -3 tools/sector_rotation.py", out_path)
