#!/usr/bin/env python3
"""screener_eps_fetch.py — B-141 follow-up: ~10 years of ANNUAL EPS from screener.in.

Why: yfinance gives 4 annual columns (median 5.0y of quarterly TTM EPS), which
failed B-141's pre-committed bar (60% of the NIFTY 500 with >= 8 years). The
company page on screener.in carries the Profit & Loss table for ~10 fiscal years.
This fetches it, for a small list first, and writes one cache file per symbol that
`eps_history_probe.py --annual` re-tests UNCHANGED against the same bar.

RUN ON THE DESK MACHINE. It needs your screener.in login (reuses
browser_cookie_helper.get_screener_sessionid, i.e. the saved session) and outbound
access; it was written where neither exists, so:
  * the HTML PARSER is tested against a fixture (test_screener_eps_fetch.py);
  * the LIVE FETCH has never been run by the author. If screener.in changed its
    markup the parser returns an empty result and says so; it never guesses.

Usage
  py -3 tools/screener_eps_fetch.py                       # 20 liquid names, default
  py -3 tools/screener_eps_fetch.py RELIANCE TCS INFY     # named symbols
  py -3 tools/screener_eps_fetch.py --n 100 --throttle 3  # first 100 of the NIFTY 500
  py -3 tools/eps_history_probe.py --annual               # then re-test the bar

Courtesy: 2s+ between requests, backs off on 429, stops after 3 consecutive
failures (an expired login looks like repeated redirects and hammering helps no one).
Output: tools/cache/screener_eps/<SYMBOL>.json
  {symbol, basis: "consolidated"|"standalone"|"unknown", fetched, periods:
   [{period_end, eps, sales, net_profit}], ttm: {...}|null}
Basis matters: consolidated and standalone EPS are different series. The page
shows consolidated when the company has it; we record which was served and do not
mix a symbol's basis over time.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "cache" / "screener_eps"
N500 = HERE / "cache" / "nse_nifty500_constituents.json"
BASE = "https://www.screener.in"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Accept": "text/html,application/xhtml+xml"}
DEFAULT20 = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "LT",
             "BAJFINANCE", "ASIANPAINT", "MARUTI", "TITAN", "NESTLEIND", "SUNPHARMA",
             "ULTRACEMCO", "TATASTEEL", "ONGC", "COALINDIA", "PIDILITIND", "DMART"]

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _num(txt: str) -> float | None:
    t = (txt or "").replace(",", "").replace("%", "").strip()
    if t in ("", "-", "—"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _period_end(label: str) -> str | None:
    """'Mar 2024' -> '2024-03-31'. Anything else (e.g. 'TTM') -> None."""
    m = re.fullmatch(r"([A-Za-z]{3})\s+(\d{4})", (label or "").strip())
    if not m or m.group(1).lower() not in _MONTHS:
        return None
    mo, yr = _MONTHS[m.group(1).lower()], int(m.group(2))
    nxt = dt.date(yr + (mo == 12), mo % 12 + 1, 1)
    return (nxt - dt.timedelta(days=1)).isoformat()


def parse_profit_loss(html: str) -> dict:
    """Parse the annual Profit & Loss table. Returns {'periods': [...], 'ttm': {...}|None}.

    Empty `periods` means the markup was not recognised — callers must treat that
    as a FAILURE, not as 'a company with no earnings'.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    sec = soup.find(id="profit-loss")
    tbl = sec.find("table") if sec else None
    if tbl is None:
        return {"periods": [], "ttm": None}
    heads = [th.get_text(strip=True) for th in tbl.find("thead").find_all("th")] if tbl.find("thead") else []
    rows = {}
    for tr in (tbl.find("tbody") or tbl).find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        label = re.sub(r"[\s+]+$", "", tds[0].get_text(" ", strip=True)).strip().lower()
        rows[label] = [_num(td.get_text(strip=True)) for td in tds[1:]]

    def pick(*names):
        for n in names:
            for k, v in rows.items():
                if k == n or k.startswith(n):
                    return v
        return None

    eps = pick("eps in rs")
    sales = pick("sales", "revenue")
    npf = pick("net profit")
    periods, ttm = [], None
    cols = heads[1:] if heads and heads[0] == "" else heads[-(len(eps or [])):] if eps else []
    for i, h in enumerate(cols):
        rec = {"eps": eps[i] if eps and i < len(eps) else None,
               "sales": sales[i] if sales and i < len(sales) else None,
               "net_profit": npf[i] if npf and i < len(npf) else None}
        pe = _period_end(h)
        if pe:
            periods.append({"period_end": pe, **rec})
        elif h.strip().upper() == "TTM":
            ttm = rec
    return {"periods": periods, "ttm": ttm}


def basis_of(html: str) -> str:
    # screener.in shows a "View Standalone" link on a consolidated page and a
    # "View Consolidated" link on a standalone one. If neither (or both) is present
    # we say "unknown" rather than guess: the two series are different numbers.
    low = html.lower()
    has_sa, has_co = "view standalone" in low, "view consolidated" in low
    if has_sa and not has_co:
        return "consolidated"
    if has_co and not has_sa:
        return "standalone"
    return "unknown"


def years(periods: list[dict]) -> float:
    ps = [p for p in periods if p.get("eps") is not None]
    if len(ps) < 2:
        return 0.0
    return (dt.date.fromisoformat(ps[-1]["period_end"]) - dt.date.fromisoformat(ps[0]["period_end"])).days / 365.25


def fetch_one(session, symbol: str, throttle: float):
    import requests
    for attempt in range(3):
        r = session.get(f"{BASE}/company/{symbol}/", headers=HEADERS, timeout=30, allow_redirects=True)
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        if any(s in (r.url or "") for s in ("/login/", "/register/")):
            raise RuntimeError("redirected to login — the saved screener.in session is expired")
        if r.status_code == 404:
            return None, "not found (symbol may need its BSE code)"
        r.raise_for_status()
        return r.text, None
    return None, "rate-limited after 3 tries"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--n", type=int, help="first N of the NIFTY 500 list instead of the default 20")
    ap.add_argument("--throttle", type=float, default=2.0)
    ap.add_argument("--force", action="store_true", help="refetch even if cached <30 days")
    a = ap.parse_args()

    if a.symbols:
        syms = [s.upper() for s in a.symbols]
    elif a.n:
        syms = [r["symbol"] for r in json.loads(N500.read_text(encoding="utf-8"))][:a.n]
    else:
        syms = DEFAULT20

    import requests
    sys.path.insert(0, str(HERE))
    import browser_cookie_helper as bch
    sid, src = bch.get_screener_sessionid()
    if not sid:
        print("No screener.in login available. Run: py -3 tools/screener_login.py --use-profile")
        return 2
    s = requests.Session()
    s.cookies.set("sessionid", sid, domain="www.screener.in")
    OUT.mkdir(parents=True, exist_ok=True)

    fails = ok = 0
    consecutive = 0
    for i, sym in enumerate(syms, 1):
        p = OUT / f"{sym}.json"
        if p.exists() and not a.force:
            age = time.time() - p.stat().st_mtime
            if age < 30 * 86400:
                print(f"[{i}/{len(syms)}] {sym}: cached"); continue
        try:
            html, err = fetch_one(s, sym, a.throttle)
        except RuntimeError as e:
            print(f"STOP: {e}"); return 3
        except Exception as e:
            html, err = None, f"{type(e).__name__}: {e}"
        if html is None:
            print(f"[{i}/{len(syms)}] {sym}: FAIL {err}")
            fails += 1; consecutive += 1
            if consecutive >= 3:
                print("STOP: 3 failures in a row — check the login/connection before retrying"); return 4
            time.sleep(a.throttle); continue
        parsed = parse_profit_loss(html)
        if not parsed["periods"]:
            print(f"[{i}/{len(syms)}] {sym}: FAIL profit-loss table not recognised (markup changed?)")
            fails += 1; consecutive += 1
            if consecutive >= 3:
                print("STOP: parser found nothing 3 times — screener.in markup likely changed"); return 5
            time.sleep(a.throttle); continue
        consecutive = 0
        doc = {"symbol": sym, "basis": basis_of(html), "fetched": dt.date.today().isoformat(), **parsed}
        p.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        ok += 1
        print(f"[{i}/{len(syms)}] {sym}: {len(parsed['periods'])} fiscal years, "
              f"{years(parsed['periods']):.1f}y span, basis={doc['basis']}")
        time.sleep(a.throttle)
    print(f"\ndone: {ok} fetched, {fails} failed -> {OUT}\nnext: py -3 tools/eps_history_probe.py --annual")
    return 0


if __name__ == "__main__":
    sys.exit(main())
