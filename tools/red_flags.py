"""FR-4 — red-flag aggregation with three-state rendering.

The point of this module is the third state.

A checklist that shows only ✅ and 🚩 is dishonest, because most of the classic
governance red flags — auditor qualifications, related-party transactions,
revenue concentration — live in annual-report *prose* that this stack has no
source for. A page that silently omits them reads as "we looked and it was
clean". So every check reports one of:

    FLAG        we checked, and it is bad
    CLEAN       we checked, and it is fine
    NOT_CHECKED we have no source — this is NOT a pass

and `no_critical_flags()` deliberately refuses to return True unless the
critical checks were actually performed. "No red flags found" and "we did not
look" must never render the same way.

Sources, and what each one costs
--------------------------------
* Working-capital trends and the free-cash-flow streak come from the FR-1
  statement layer — free, no login, already fetched.
* Promoter holding and pledge live on screener.in and need a `sessionid`
  cookie, which this machine has historically found flaky. Without one they
  report NOT_CHECKED rather than disappearing, so the reader can see there is
  an unchecked governance surface rather than assuming there is not.
"""

from __future__ import annotations

from typing import Any

FLAG = "FLAG"
CLEAN = "CLEAN"
NOT_CHECKED = "NOT_CHECKED"

CRITICAL = "critical"
WATCH = "watch"

# A trend flag needs at least this many yearly observations. yfinance returns
# four or five annual columns for most NSE names, so two points is common and
# two points is not a trend.
_MIN_TREND_POINTS = 3

# Percentage deterioration that counts as a trend...
_TREND_RISE_PCT = 30.0
# ...but only once the absolute level is high enough to matter. Debtor days
# going 4 -> 7 is +75% and means nothing; these floors stop arithmetic from
# manufacturing alarm on companies that collect cash quickly.
_DEBTOR_DAYS_FLOOR = 45.0
_WC_DAYS_FLOOR = 120.0

# Promoter stake falling by more than this over the observed window is the
# classic "insiders are leaving" signal.
_PROMOTER_DROP_PP = 2.0
# Pledged promoter shares above this are a financing-stress signal.
_PLEDGE_PCT_MAX = 5.0


def _f(v: Any) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def _mk(key: str, label: str, state: str, severity: str,
        detail: str, source: str) -> dict[str, Any]:
    return {"key": key, "label": label, "state": state,
            "severity": severity, "detail": detail, "source": source}


# ──────────────────────────────────────────────────────────────────────────────
# Statement-based checks (free)
# ──────────────────────────────────────────────────────────────────────────────
def _check_fcf(deep: dict) -> dict[str, Any]:
    hist = deep.get("fcf_history") or []
    if not hist or all(v is None for v in hist):
        return _mk("negative_fcf", "Negative free cash flow", NOT_CHECKED, CRITICAL,
                   "No cash-flow statement returned for this symbol.", "yfinance")
    streak = int(deep.get("fcf_negative_streak") or 0)
    latest = deep.get("fcf")
    if streak >= 2:
        return _mk("negative_fcf", "Negative free cash flow", FLAG, CRITICAL,
                   f"{streak} consecutive years of negative FCF. The business has "
                   f"not funded itself from operations over that span.", "yfinance")
    if streak == 1:
        return _mk("negative_fcf", "Negative free cash flow", FLAG, WATCH,
                   "Most recent year had negative FCF; one year alone can be a "
                   "capex cycle rather than a problem.", "yfinance")
    return _mk("negative_fcf", "Negative free cash flow", CLEAN, CRITICAL,
               "Latest FCF positive"
               + (f" (₹{latest/1e7:,.0f} Cr)" if latest is not None else "") + ".",
               "yfinance")


def _check_days_trend(deep: dict, key: str, label: str, hist_key: str,
                      floor: float, severity: str, what: str) -> dict[str, Any]:
    hist = [v for v in (deep.get(hist_key) or []) if v is not None]
    if len(hist) < _MIN_TREND_POINTS:
        return _mk(key, label, NOT_CHECKED, severity,
                   f"Only {len(hist)} yearly observation(s) available — a trend "
                   f"needs at least {_MIN_TREND_POINTS}.", "yfinance")
    latest, oldest = hist[0], hist[-1]          # history is newest-first
    if oldest <= 0:
        return _mk(key, label, NOT_CHECKED, severity,
                   "Earliest observation is not positive, so a % change is undefined.",
                   "yfinance")
    change = (latest / oldest - 1) * 100
    span = len(hist)
    if change >= _TREND_RISE_PCT and latest >= floor:
        return _mk(key, label, FLAG, severity,
                   f"{what} rose {change:+.0f}% over {span} years "
                   f"({oldest:.0f}d → {latest:.0f}d).", "yfinance")
    if change >= _TREND_RISE_PCT:
        return _mk(key, label, CLEAN, severity,
                   f"{what} rose {change:+.0f}% ({oldest:.0f}d → {latest:.0f}d) but "
                   f"stays below the {floor:.0f}d level where it starts to matter.",
                   "yfinance")
    return _mk(key, label, CLEAN, severity,
               f"{what} {change:+.0f}% over {span} years "
               f"({oldest:.0f}d → {latest:.0f}d).", "yfinance")


# ──────────────────────────────────────────────────────────────────────────────
# screener.in checks (need a sessionid cookie)
# ──────────────────────────────────────────────────────────────────────────────
def _screener_holdings(symbol: str, sessionid: str | None) -> dict[str, Any] | None:
    """Promoter + pledge rows from the screener.in company page.

    Returns None when there is no session or the fetch fails, which the callers
    turn into NOT_CHECKED. Never raises into the page.
    """
    if not sessionid:
        return None
    try:
        import screener_scraper as ss
        session = ss._session(sessionid)
        soup = ss.fetch_company_page(session, symbol.upper())
        if soup is None:
            return None
        return {
            "promoter": ss._parse_quarterly_holding(soup, "Promoter"),
            "pledge":   ss._parse_quarterly_holding(soup, "Pledged"),
        }
    except Exception:
        return None


def _check_promoter_holding(holdings: dict | None) -> dict[str, Any]:
    key, label = "promoter_holding", "Promoter stake reduction"
    if not holdings or not holdings.get("promoter"):
        return _mk(key, label, NOT_CHECKED, CRITICAL,
                   "Needs a screener.in session cookie; none available, so promoter "
                   "holding was not read. This is not a clean bill of health.",
                   "screener.in")
    series = holdings["promoter"]
    quarters = list(series.keys())
    latest, oldest = series[quarters[-1]], series[quarters[0]]
    delta = latest - oldest
    if delta <= -_PROMOTER_DROP_PP:
        return _mk(key, label, FLAG, CRITICAL,
                   f"Promoter holding fell {abs(delta):.2f}pp across the reported "
                   f"quarters ({oldest:.2f}% → {latest:.2f}%).", "screener.in")
    return _mk(key, label, CLEAN, CRITICAL,
               f"Promoter holding {latest:.2f}% ({delta:+.2f}pp over the reported "
               f"quarters).", "screener.in")


def _check_promoter_pledge(holdings: dict | None) -> dict[str, Any]:
    key, label = "promoter_pledge", "Promoter share pledging"
    if holdings is None:
        return _mk(key, label, NOT_CHECKED, CRITICAL,
                   "Needs a screener.in session cookie; none available. Never read "
                   "an absent pledge row as 0% pledged.", "screener.in")
    series = holdings.get("pledge") or {}
    if not series:
        return _mk(key, label, NOT_CHECKED, CRITICAL,
                   "Company page carried no pledged-percentage row. Absent is not "
                   "the same as zero.", "screener.in")
    latest = series[list(series.keys())[-1]]
    if latest > _PLEDGE_PCT_MAX:
        return _mk(key, label, FLAG, CRITICAL,
                   f"{latest:.2f}% of promoter holding is pledged (above the "
                   f"{_PLEDGE_PCT_MAX:.0f}% comfort line).", "screener.in")
    return _mk(key, label, CLEAN, CRITICAL,
               f"{latest:.2f}% pledged.", "screener.in")


# ──────────────────────────────────────────────────────────────────────────────
# Checks with no source at all
# ──────────────────────────────────────────────────────────────────────────────
#: These are the reason this module exists. Each is a genuine red flag that
#: professional analysts check and that we cannot: all three live in
#: annual-report and filing prose, which nothing in this stack parses. They are
#: rendered explicitly as NOT CHECKED so their absence is visible.
_UNSOURCED = (
    ("auditor_qualification", "Auditor qualification / resignation",
     "Lives in the annual report's audit opinion — no machine-readable source here."),
    ("related_party_txns", "Related-party transactions",
     "Disclosed in annual-report schedules; not parsed by this stack."),
    ("revenue_concentration", "Customer / revenue concentration",
     "Disclosed narratively in the annual report; no structured feed."),
)


def evaluate(symbol: str, fundamentals: dict | None, deep: dict | None,
             sessionid: str | None = None) -> dict[str, Any]:
    """Run every red-flag check and return them with a three-state summary."""
    deep = deep or {}
    holdings = _screener_holdings(symbol, sessionid)

    flags = [
        _check_fcf(deep),
        _check_days_trend(deep, "debtor_days_trend", "Rising debtor days",
                          "debtor_days_history", _DEBTOR_DAYS_FLOOR, WATCH,
                          "Receivable days"),
        _check_days_trend(deep, "wc_days_trend", "Rising working-capital days",
                          "wc_days_history", _WC_DAYS_FLOOR, WATCH,
                          "Working-capital days"),
        _check_promoter_holding(holdings),
        _check_promoter_pledge(holdings),
    ]
    flags += [_mk(k, lbl, NOT_CHECKED, CRITICAL, why, "no source")
              for k, lbl, why in _UNSOURCED]

    counts = {
        "flagged":     sum(1 for f in flags if f["state"] == FLAG),
        "clean":       sum(1 for f in flags if f["state"] == CLEAN),
        "not_checked": sum(1 for f in flags if f["state"] == NOT_CHECKED),
        "critical_flagged": sum(1 for f in flags
                                if f["state"] == FLAG and f["severity"] == CRITICAL),
    }
    return {"symbol": symbol.upper(), "flags": flags, "counts": counts,
            "no_critical_flags": no_critical_flags(flags)}


def no_critical_flags(flags: list[dict]) -> bool:
    """True only when every CRITICAL check actually ran and came back clean.

    The source mockup shows a green "✅ No Critical Red Flags" panel. That panel
    is a lie whenever an unchecked governance item exists, so this returns False
    if any critical check is NOT_CHECKED — and because the three unsourced items
    are always critical and always unchecked, it currently returns False for
    every symbol. That is the correct answer, not a bug: this stack cannot
    clear a company of auditor or related-party risk.
    """
    criticals = [f for f in flags if f["severity"] == CRITICAL]
    return bool(criticals) and all(f["state"] == CLEAN for f in criticals)


if __name__ == "__main__":   # py -3 tools/red_flags.py ITC MAPMYINDIA
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import fundamentals_deep as fdeep
    import stock_council as council
    try:
        import browser_cookie_helper as bch
        sid, _browser = bch.get_screener_sessionid()
    except Exception:
        sid = None
    print("screener.in session:", "found" if sid else "NOT available")
    for s in (sys.argv[1:] or ["ITC"]):
        res = evaluate(s, council.fetch_fundamentals(s), fdeep.derive_fundamentals(s), sid)
        print(f"\n=== {s} ===  {res['counts']}")
        for f in res["flags"]:
            print(f"  [{f['state']:<11}] {f['severity']:<8} {f['label']:<38} {f['detail']}")
        print("  no_critical_flags:", res["no_critical_flags"])
