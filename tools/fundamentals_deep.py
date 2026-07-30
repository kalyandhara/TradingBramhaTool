"""Fundamental deep-dive data layer — annual & quarterly financial statements.

Why this module exists
----------------------
Every fundamental figure the dashboard shows today comes from yfinance's `.info`
snapshot (`fetch_fundamentals` in stock_council.py): a single point-in-time P/E,
ROE, D/E and so on. The *statements* behind those numbers — income statement,
balance sheet, cash-flow — were never fetched anywhere in the repo, even though
yfinance serves them free and login-free. This module makes that one call and
derives the history-dependent figures the snapshot cannot give:

  * 3Y / 5Y revenue and profit CAGR
  * per-year net & operating margin (is the margin trend improving or eroding?)
  * **ROCE** = EBIT / (equity + total debt) — the metric that has blocked
    Radar-Chart-Analyzer-Fit RC-2 and PEAD-Scanner-Roadmap 5.2, both of which
    were waiting on a flaky screener.in session for it
  * debtor days, working-capital days, free cash flow and negative-FCF streaks
    (the working capital red flags)

Honesty rules this module follows (see Fundamental-Deep-Dive-Report-Roadmap)
---------------------------------------------------------------------------
1. **Missing is None, never a default.** A company with four annual columns
   genuinely cannot produce a 5Y CAGR, and a neutral-looking placeholder would
   read as a measured value. Callers render "DATA N/A", never a filled-in 50.
2. **CAGR through a loss is undefined**, so a non-positive base year returns
   None rather than a nonsense root.
3. **`coverage` is a coverage meter, not a quality score.** It counts how many
   of COVERAGE_FIELDS we actually resolved, so the UI can say "8/11 fields" and
   let the reader discount accordingly.
4. Fetch failures degrade to an empty result — the analyzer must keep working
   technical-only, the same contract `fetch_fundamentals` already honours.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

import pandas as pd

# Fields the coverage dial counts. Deliberately the *derived* figures a reader
# would look for on a deep-dive page — not the raw statement rows.
COVERAGE_FIELDS = (
    "revenue_cagr_3y", "revenue_cagr_5y", "profit_cagr_3y", "profit_cagr_5y",
    "roce", "net_margin", "debtor_days", "wc_days", "fcf", "eps_ttm",
    "book_value",
)

# yfinance label aliases. The row names differ between statements, sectors and
# occasionally between refreshes, so every lookup tries a list rather than
# assuming one spelling.
_REVENUE   = ("Total Revenue", "Operating Revenue", "Revenue")
_NET_INC   = ("Net Income", "Net Income Common Stockholders",
              "Net Income Continuous Operations",
              "Net Income Including Noncontrolling Interests")
_EBIT      = ("EBIT", "Operating Income")   # quarterly frames often lack EBIT
_EQUITY    = ("Stockholders Equity", "Common Stock Equity",
              "Total Equity Gross Minority Interest")
_TOT_DEBT  = ("Total Debt",)
_RECV      = ("Accounts Receivable", "Receivables", "Gross Accounts Receivable")
_WORK_CAP  = ("Working Capital",)
_CUR_ASSET = ("Current Assets", "Total Current Assets")
_CUR_LIAB  = ("Current Liabilities", "Total Current Liabilities")
_FCF       = ("Free Cash Flow",)
_OCF       = ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
_CAPEX     = ("Capital Expenditure",)
_BASIC_EPS = ("Basic EPS", "Diluted EPS")


# ──────────────────────────────────────────────────────────────────────────────
# Fetch
# ──────────────────────────────────────────────────────────────────────────────
def _ticker_symbol(symbol: str) -> str:
    """`TITAN` -> `TITAN.NS`; an explicit `.NS`/`.BO` suffix is respected.

    Mirrors the convention in stock_council.fetch_fundamentals, which appends
    `.NS` unconditionally — here a caller analysing a BSE-only name can pass
    `DIACABS.BO` and have it work.
    """
    s = (symbol or "").strip().upper()
    return s if ("." in s) else f"{s}.NS"


def fetch_statements(symbol: str) -> dict[str, Any]:
    """Raw statement frames from yfinance. `{}` on any failure.

    Returns the frames as yfinance gives them (rows = line items, columns =
    period end dates, newest first) plus the `.info` fields FR-1 maps in
    (`trailingEps`, `bookValue`, currency, long name).
    """
    try:
        import yfinance as yf
        t = yf.Ticker(_ticker_symbol(symbol))
    except Exception:
        return {}

    out: dict[str, Any] = {}
    for key, attr in (("income", "income_stmt"),
                      ("income_q", "quarterly_income_stmt"),
                      ("balance", "balance_sheet"),
                      ("cashflow", "cashflow")):
        try:
            df = getattr(t, attr)
            out[key] = df if (df is not None and not df.empty) else None
        except Exception:
            out[key] = None

    try:
        info = t.info or {}
    except Exception:
        info = {}
    out["eps_ttm"] = _num(info.get("trailingEps"))
    out["book_value"] = _num(info.get("bookValue"))
    out["currency"] = info.get("financialCurrency") or info.get("currency")
    out["long_name"] = info.get("longName") or info.get("shortName")
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Small numeric helpers
# ──────────────────────────────────────────────────────────────────────────────
def _num(v: Any) -> float | None:
    """Coerce to float, mapping NaN/inf/non-numeric to None."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(f) or math.isinf(f)) else f


def _row(df: pd.DataFrame | None, names: Iterable[str]) -> pd.Series | None:
    """First matching row as a newest-first Series, or None.

    Matching is case-insensitive on the exact label; yfinance capitalisation has
    changed across releases and a silent miss here would look like missing data.
    """
    if df is None or df.empty:
        return None
    lookup = {str(i).strip().lower(): i for i in df.index}
    for n in names:
        idx = lookup.get(n.strip().lower())
        if idx is not None:
            s = df.loc[idx]
            if isinstance(s, pd.DataFrame):     # duplicate labels — take the first
                s = s.iloc[0]
            return s
    return None


def _at(series: pd.Series | None, i: int) -> float | None:
    """Value at column position `i` (0 = most recent period)."""
    if series is None or i >= len(series):
        return None
    return _num(series.iloc[i])


def _cagr(latest: float | None, earliest: float | None, years: int) -> float | None:
    """Compound annual growth rate in %, or None when it is undefined.

    A non-positive base makes the root meaningless (you cannot express "grew
    from a loss" as a CAGR), so that case returns None rather than a number the
    reader would take at face value.
    """
    if latest is None or earliest is None or years <= 0:
        return None
    if earliest <= 0 or latest <= 0:
        return None
    return round(((latest / earliest) ** (1.0 / years) - 1.0) * 100, 2)


def _pct(numer: float | None, denom: float | None) -> float | None:
    if numer is None or denom is None or denom == 0:
        return None
    return round(numer / denom * 100, 2)


def _period_label(col: Any) -> str:
    try:
        return pd.Timestamp(col).date().isoformat()
    except Exception:
        return str(col)


# ──────────────────────────────────────────────────────────────────────────────
# Derive
# ──────────────────────────────────────────────────────────────────────────────
def _annual_history(stmts: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-year revenue / net income / EBIT with margins, newest first."""
    inc = stmts.get("income")
    rev, ni, ebit = _row(inc, _REVENUE), _row(inc, _NET_INC), _row(inc, _EBIT)
    if inc is None or rev is None:
        return []
    rows = []
    for i, col in enumerate(inc.columns):
        r, n, e = _at(rev, i), _at(ni, i), _at(ebit, i)
        rows.append({
            "period":     _period_label(col),
            "revenue":    r,
            "net_income": n,
            "ebit":       e,
            "net_margin": _pct(n, r),
            "opm":        _pct(e, r),
        })
    return rows


def _year_ago_index(columns: Any, i: int, tol_days: int = 45) -> int | None:
    """Position of the column closest to one year before `columns[i]`.

    Deliberately NOT `i + 4`. yfinance's quarterly frames have gaps — TITAN's is
    missing 2025-09-30 — and counting four columns back then silently compares
    March against the previous December, inflating "YoY" by a whole quarter of
    seasonality (it read 80% where the true figure was 17%). Matching on the
    date and returning None when no quarter lands within the tolerance keeps a
    gap looking like a gap.
    """
    try:
        target = pd.Timestamp(columns[i]) - pd.DateOffset(years=1)
    except Exception:
        return None
    best, best_gap = None, None
    for j in range(len(columns)):
        if j == i:
            continue
        try:
            gap = abs((pd.Timestamp(columns[j]) - target).days)
        except Exception:
            continue
        if gap <= tol_days and (best_gap is None or gap < best_gap):
            best, best_gap = j, gap
    return best


def _quarterly_history(stmts: dict[str, Any]) -> list[dict[str, Any]]:
    """Quarterly revenue / net income / EPS with YoY, newest first.

    YoY compares against the same quarter a year earlier — matched by date, not
    by column offset — because sequential comparison would read seasonality as
    growth and offset counting breaks on gapped frames. No match, no YoY.
    """
    inc = stmts.get("income_q")
    rev, ni, eps = _row(inc, _REVENUE), _row(inc, _NET_INC), _row(inc, _BASIC_EPS)
    if inc is None or (rev is None and ni is None):
        return []
    cols = list(inc.columns)
    rows = []
    for i, col in enumerate(cols):
        r, n = _at(rev, i), _at(ni, i)
        j = _year_ago_index(cols, i)
        r_yoy = None if j is None else _at(rev, j)
        n_yoy = None if j is None else _at(ni, j)
        rows.append({
            "period":      _period_label(col),
            "revenue":     r,
            "net_income":  n,
            "eps":         _at(eps, i),
            "net_margin":  _pct(n, r),
            "revenue_yoy": (round((r / r_yoy - 1) * 100, 2)
                            if (r is not None and r_yoy not in (None, 0) and r_yoy > 0) else None),
            "profit_yoy":  (round((n / n_yoy - 1) * 100, 2)
                            if (n is not None and n_yoy not in (None, 0) and n_yoy > 0) else None),
        })
    return rows


def _fcf_series(stmts: dict[str, Any]) -> list[float | None]:
    """Free cash flow per year, newest first.

    Prefers yfinance's own `Free Cash Flow` row; falls back to
    OCF + capex (capex is reported negative, so this is a subtraction).
    """
    cf = stmts.get("cashflow")
    fcf = _row(cf, _FCF)
    if fcf is not None:
        return [_num(v) for v in fcf.tolist()]
    ocf, capex = _row(cf, _OCF), _row(cf, _CAPEX)
    if ocf is None:
        return []
    out = []
    for i in range(len(ocf)):
        o, c = _at(ocf, i), _at(capex, i)
        out.append(None if o is None else (o + c if c is not None else None))
    return out


def derive_fundamentals(symbol: str, stmts: dict[str, Any] | None = None) -> dict[str, Any]:
    """The FR-1 payload: statement history + derived long-horizon figures.

    Pass `stmts` to derive from an already-fetched bundle (keeps tests and the
    cached dashboard path from re-hitting the network).
    """
    stmts = fetch_statements(symbol) if stmts is None else stmts
    if not stmts:
        return {"symbol": symbol.upper(), "available": False,
                "coverage": {"have": 0, "total": len(COVERAGE_FIELDS),
                             "missing": list(COVERAGE_FIELDS)}}

    inc, bal = stmts.get("income"), stmts.get("balance")

    # `available` means we actually got statements — not merely that the fetch
    # returned without raising. An unknown ticker yields a populated dict of
    # Nones, and reporting that as available would let the UI print a deep-dive
    # frame around nothing.
    if all(stmts.get(k) is None for k in ("income", "income_q", "balance", "cashflow")):
        return {"symbol": symbol.upper(), "available": False,
                "long_name": stmts.get("long_name"),
                "coverage": {"have": 0, "total": len(COVERAGE_FIELDS),
                             "missing": list(COVERAGE_FIELDS)}}

    annual = _annual_history(stmts)
    quarters = _quarterly_history(stmts)

    rev, ni = _row(inc, _REVENUE), _row(inc, _NET_INC)
    # _EBIT already falls back to "Operating Income" — note a truthiness test on
    # a Series raises, so the alias list is the fallback mechanism, not `or`.
    ebit = _row(inc, _EBIT)
    equity, debt = _row(bal, _EQUITY), _row(bal, _TOT_DEBT)

    # CAGRs. n annual columns span n-1 years of growth, so a 5Y CAGR needs six
    # columns; yfinance commonly returns four or five and the answer is then
    # honestly None.
    rev_3y = _cagr(_at(rev, 0), _at(rev, 3), 3)
    rev_5y = _cagr(_at(rev, 0), _at(rev, 5), 5)
    pro_3y = _cagr(_at(ni, 0), _at(ni, 3), 3)
    pro_5y = _cagr(_at(ni, 0), _at(ni, 5), 5)

    # ROCE = EBIT / capital employed, capital employed = equity + total debt.
    # (The equivalent total-assets-minus-current-liabilities form needs two more
    # rows that are missing more often; this form matches the screener.in
    # definition the radar roadmap was waiting on.)
    e0, eq0, dt0 = _at(ebit, 0), _at(equity, 0), _at(debt, 0)
    cap_employed = None if eq0 is None else eq0 + (dt0 or 0.0)
    roce = _pct(e0, cap_employed)
    roce_prev = _pct(_at(ebit, 1),
                     (None if _at(equity, 1) is None
                      else _at(equity, 1) + (_at(debt, 1) or 0.0)))

    # Working-capital red-flag inputs.
    rev0 = _at(rev, 0)
    recv0 = _at(_row(bal, _RECV), 0)
    debtor_days = (round(recv0 / rev0 * 365, 1)
                   if (recv0 is not None and rev0 not in (None, 0) and rev0 > 0) else None)
    wc = _at(_row(bal, _WORK_CAP), 0)
    if wc is None:
        ca, cl = _at(_row(bal, _CUR_ASSET), 0), _at(_row(bal, _CUR_LIAB), 0)
        wc = None if (ca is None or cl is None) else ca - cl
    wc_days = (round(wc / rev0 * 365, 1)
               if (wc is not None and rev0 not in (None, 0) and rev0 > 0) else None)

    fcf_hist = _fcf_series(stmts)
    fcf = fcf_hist[0] if fcf_hist else None
    neg_streak = 0
    for v in fcf_hist:
        if v is not None and v < 0:
            neg_streak += 1
        else:
            break

    out: dict[str, Any] = {
        "symbol":        symbol.upper(),
        "available":     True,
        "long_name":     stmts.get("long_name"),
        "currency":      stmts.get("currency"),
        "as_of":         annual[0]["period"] if annual else None,
        "annual":        annual,
        "quarters":      quarters,
        "revenue_cagr_3y": rev_3y,
        "revenue_cagr_5y": rev_5y,
        "profit_cagr_3y":  pro_3y,
        "profit_cagr_5y":  pro_5y,
        "roce":          roce,
        "roce_prev":     roce_prev,
        "net_margin":    annual[0]["net_margin"] if annual else None,
        "opm":           annual[0]["opm"] if annual else None,
        "debtor_days":   debtor_days,
        "wc_days":       wc_days,
        "fcf":           fcf,
        "fcf_history":   fcf_hist,
        "fcf_negative_streak": neg_streak,
        "eps_ttm":       stmts.get("eps_ttm"),
        "book_value":    stmts.get("book_value"),
        "annual_periods":    len(annual),
        "quarterly_periods": len(quarters),
    }

    missing = [f for f in COVERAGE_FIELDS if out.get(f) is None]
    out["coverage"] = {
        "have":    len(COVERAGE_FIELDS) - len(missing),
        "total":   len(COVERAGE_FIELDS),
        "missing": missing,
    }
    return out


if __name__ == "__main__":  # manual probe: py -3 tools/fundamentals_deep.py TITAN
    import sys, json
    for s in (sys.argv[1:] or ["TITAN"]):
        d = derive_fundamentals(s)
        slim = {k: v for k, v in d.items() if k not in ("annual", "quarters", "fcf_history")}
        print(json.dumps(slim, indent=2, default=str))
        print(f"  annual periods: {d.get('annual_periods')}  "
              f"quarters: {d.get('quarterly_periods')}")
