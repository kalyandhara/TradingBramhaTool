#!/usr/bin/env python3
"""equity_curve.py — the portfolio's equity history, and its drawdown (B-110).

The reference pipeline names drawdown as a RISK component and the desk had no
peak-to-trough number at all, because nothing stored the equity curve:
`positions` holds entry/exit prices and dates, and there was no equity-history
table. The blocker was data, not arithmetic.

── Two sources, and they are not the same claim ──────────────────────────────
**reconstructed** — rebuilt from `positions` + cached daily closes. History is
available immediately, and it inherits everything the cache does: price
adjustments, survivorship, a missing bar. It also replays TODAY's view of the
book: a position deleted from the table, or edited after the fact, rewrites the
past.

**recorded** — one row per trading day written after the close by the
`equity_snapshot` job (`equity_snapshot.py`). Worth little until it has run for a
while, and then it stops depending on a reconstruction.

`combined()` uses recorded rows wherever they exist and reconstructed rows only
for the dates BEFORE the first recording, and every row keeps its `source`.
`drawdown()` reports which sources the numbers rest on, because a drawdown that
peaks in the reconstruction and troughs in the record is a mix of the two.

── What equity means here ────────────────────────────────────────────────────
    equity = capital + realised P&L (closed positions) + unrealised P&L (open)

`capital` is the `total_capital` setting — treated as the money put IN, not the
account's current value. That setting has no history of its own: the
reconstruction holds today's value constant over the whole past, so a deposit
made last month reads as if it had always been there. Recorded rows store the
capital of their day, and `drawdown()` lists every date it changed, because a
withdrawal would otherwise show up as a loss. Costs and taxes are NOT deducted;
the positions table does not carry them.

Pure: frames and a price lookup in, frames and dicts out. No Streamlit, no DB.
"""
from __future__ import annotations

from typing import Any, Callable

import pandas as pd

SOURCE_RECON = "reconstructed"
SOURCE_RECORDED = "recorded"
#: peak_date when the peak is the starting capital, before any close.
START = "start"

COLUMNS = ["date", "equity", "capital", "deployed", "realised", "unrealised",
           "n_open", "unpriced", "source"]


def _d(x) -> pd.Timestamp | None:
    if x is None or (isinstance(x, float) and x != x) or x == "":
        return None
    try:
        return pd.Timestamp(x).normalize()
    except (ValueError, TypeError):
        return None


def _closes(df: "pd.DataFrame | None") -> pd.Series:
    """Daily closes indexed by normalised date, or an empty series (still
    date-indexed, so `s.index <= d` compares instead of raising)."""
    none = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    if df is None or getattr(df, "empty", True) or "close" not in df.columns:
        return none
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        if "date" not in df.columns:
            return none
        idx = pd.DatetimeIndex(pd.to_datetime(df["date"]))
    s = pd.Series(df["close"].to_numpy(dtype=float), index=idx.normalize())
    s = s[~s.index.duplicated(keep="last")].dropna().sort_index()
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    return s


def reconstruct(positions: pd.DataFrame,
                ohlcv_fn: Callable[[str], "pd.DataFrame | None"],
                capital: float,
                end: "str | pd.Timestamp | None" = None) -> pd.DataFrame:
    """Rebuild a daily equity curve from every position, open and closed.

    The calendar is the union of the trading dates of the symbols held, from the
    first entry to ``end`` (default: the last priced bar). On each date:

    * a position is OPEN from its entry date (marked at that day's close against
      its entry price) until the day before its ``closed_date``;
    * from ``closed_date`` on it is REALISED at ``closed_price``, whether or not
      the symbol still trades;
    * an open position with no close on or before the date is NOT valued at its
      entry price — that would print a flat line exactly where the data is
      missing. The row's ``unpriced`` count goes up instead, and `drawdown()`
      skips rows with unpriced > 0.
    """
    if positions is None or positions.empty:
        return pd.DataFrame(columns=COLUMNS)
    cap = float(capital or 0.0)
    rows = []
    for _, p in positions.iterrows():
        e = _d(p.get("entry_date"))
        if e is None:
            continue
        c = _d(p.get("closed_date")) if str(p.get("status", "")) == "closed" else None
        cp = p.get("closed_price")
        cp = None if cp is None or (isinstance(cp, float) and cp != cp) else float(cp)
        rows.append(dict(symbol=str(p["symbol"]), entry=float(p["entry_price"]),
                         qty=float(p["quantity"]), entry_date=e,
                         closed_date=c if cp is not None else None, closed_price=cp))
    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    closes = {r["symbol"]: _closes(ohlcv_fn(r["symbol"])) for r in rows}
    start = min(r["entry_date"] for r in rows)
    cal = sorted({d for s in closes.values() for d in s.index if d >= start})
    end_ts = _d(end)
    if end_ts is not None:
        cal = [d for d in cal if d <= end_ts]
    # Closing dates are on the calendar even when the symbol no longer trades,
    # so a realised P&L lands on the day it was realised.
    cal = sorted(set(cal) | {r["closed_date"] for r in rows
                             if r["closed_date"] is not None
                             and (end_ts is None or r["closed_date"] <= end_ts)})

    out = []
    for d in cal:
        realised = unreal = deployed = 0.0
        n_open = unpriced = 0
        for r in rows:
            if d < r["entry_date"]:
                continue
            if r["closed_date"] is not None and d >= r["closed_date"]:
                realised += (r["closed_price"] - r["entry"]) * r["qty"]
                continue
            n_open += 1
            s = closes[r["symbol"]]
            s = s[s.index <= d]
            if s.empty:
                unpriced += 1
                continue
            px = float(s.iloc[-1])
            unreal += (px - r["entry"]) * r["qty"]
            deployed += px * r["qty"]
        out.append(dict(date=d, equity=cap + realised + unreal, capital=cap,
                        deployed=deployed, realised=realised, unrealised=unreal,
                        n_open=n_open, unpriced=unpriced, source=SOURCE_RECON))
    return pd.DataFrame(out, columns=COLUMNS)


def snapshot_row(positions: pd.DataFrame,
                 ohlcv_fn: Callable[[str], "pd.DataFrame | None"],
                 capital: float, open_risk: float | None = None) -> dict | None:
    """Today's recorded row: the LAST date of the reconstruction, re-labelled.

    Same arithmetic as the reconstruction on purpose — two formulas for one
    number is how a recorded curve ends up disagreeing with its own back-fill.
    Dated by the last PRICED bar, not the wall clock, so a run on a holiday or
    before the close does not invent a session. Returns None when nothing is
    priced to date the row by.
    """
    cur = reconstruct(positions, ohlcv_fn, capital)
    if cur.empty:
        return None
    row = cur.iloc[-1].to_dict()
    row["source"] = SOURCE_RECORDED
    row["open_risk"] = open_risk
    row["date"] = pd.Timestamp(row["date"]).date().isoformat()
    return row


def combined(recorded: "pd.DataFrame | None",
             recon: "pd.DataFrame | None") -> pd.DataFrame:
    """Recorded rows where they exist; reconstructed rows only BEFORE the first
    recording. After recording starts a missing day is a gap, not something to
    back-fill — filling it would quietly mix the sources mid-series."""
    parts = []
    first_rec = None
    if recorded is not None and not recorded.empty:
        r = recorded.copy()
        r["date"] = pd.to_datetime(r["date"]).dt.normalize()
        r["source"] = SOURCE_RECORDED
        first_rec = r["date"].min()
        parts.append(r)
    if recon is not None and not recon.empty:
        b = recon.copy()
        b["date"] = pd.to_datetime(b["date"]).dt.normalize()
        if first_rec is not None:
            b = b[b["date"] < first_rec]
        parts.append(b)
    if not parts:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.concat(parts, ignore_index=True)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = 0 if c == "unpriced" else None
    return df.sort_values("date").reset_index(drop=True)[COLUMNS]


def drawdown(curve: pd.DataFrame) -> dict[str, Any]:
    """Current and maximum peak-to-trough drawdown over an equity curve.

    Percentages are of the PEAK equity. Rows with any unpriced position are
    skipped (counted in ``skipped``), not valued at a guess.
    """
    empty = dict(n_points=0, skipped=0, current_dd_pct=None, current_dd_amt=None,
                 peak_date=None, peak_equity=None, max_dd_pct=None,
                 max_dd_amt=None, max_peak_date=None, max_trough_date=None,
                 recovered_date=None, first_date=None, last_date=None,
                 sources=[], max_dd_sources=[], capital_changes=[])
    if curve is None or curve.empty:
        return empty
    df = curve.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values("date")
    unp = pd.to_numeric(df.get("unpriced", 0), errors="coerce").fillna(0)
    skipped = int((unp > 0).sum())
    df = df[unp.to_numpy() == 0].reset_index(drop=True)
    if df.empty:
        return {**empty, "skipped": skipped}

    eq = df["equity"].astype(float)
    # The peak starts at the CAPITAL put in, not at the first close: a book that
    # loses money on its first day is in drawdown from the money it started with,
    # and seeding the peak with that first close would hide exactly that loss.
    # Seen on the real book 2026-10-06: HERANBA bought at 187.60, first close
    # 179.94, and the unseeded curve called the first close the peak.
    seed = pd.to_numeric(df["capital"], errors="coerce").iloc[0]
    seed = float(seed) if pd.notna(seed) and seed > 0 else float("-inf")
    peak = eq.cummax().clip(lower=seed)
    dd_amt = eq - peak
    dd_pct = (dd_amt / peak.where(peak > 0)) * 100.0
    i_t = int(dd_pct.fillna(0).idxmin())
    from_start = seed > eq.iloc[:i_t + 1].max()
    i_p = int(eq.iloc[:i_t + 1].idxmax())
    peak_val = seed if from_start else float(eq.iloc[i_p])
    rec = None
    if dd_amt.iloc[i_t] < 0:
        after = df.index[(df.index > i_t) & (eq >= peak_val)]
        rec = df.loc[after[0], "date"].date().isoformat() if len(after) else None
    i_cp = int(eq.idxmax())
    cur_from_start = seed > float(eq.max())

    cap = pd.to_numeric(df["capital"], errors="coerce")
    changes = [dict(date=df.loc[i, "date"].date().isoformat(),
                    from_=float(cap.iloc[i - 1]), to=float(cap.iloc[i]))
               for i in range(1, len(df))
               if pd.notna(cap.iloc[i]) and pd.notna(cap.iloc[i - 1])
               and cap.iloc[i] != cap.iloc[i - 1]]

    iso = lambda i: df.loc[i, "date"].date().isoformat()
    return dict(
        n_points=int(len(df)), skipped=skipped,
        current_dd_pct=round(float(dd_pct.iloc[-1] or 0.0), 2),
        current_dd_amt=round(float(dd_amt.iloc[-1]), 2),
        peak_date=START if cur_from_start else iso(i_cp),
        peak_equity=round(seed if cur_from_start else float(eq.iloc[i_cp]), 2),
        max_dd_pct=round(float(dd_pct.iloc[i_t] or 0.0), 2),
        max_dd_amt=round(float(dd_amt.iloc[i_t]), 2),
        max_peak_date=START if from_start else iso(i_p), max_trough_date=iso(i_t),
        recovered_date=rec,
        first_date=iso(0), last_date=iso(len(df) - 1),
        sources=sorted(df["source"].dropna().unique().tolist()),
        max_dd_sources=sorted(df.loc[i_p:i_t, "source"].dropna().unique().tolist()),
        capital_changes=changes,
    )


def drawdown_strip(dd: dict[str, Any], cols: int = 4) -> tuple[str, list[str]]:
    """(cards HTML, caption lines) for the Portfolio page. Lives here, not on
    the page, for the same reason `portfolio_risk.exposure_strip` does."""
    import report_style as rs

    if not dd.get("n_points"):
        return "", ["Drawdown — no equity history yet: no position has a priced bar."]
    money = lambda v: f"₹{v:,.0f}"
    _peak = lambda d: "starting capital" if d == START else f"the {d} peak"
    # A real loss that rounds to -0.00% must not read as no loss.
    pct = lambda p, amt: ("<0.01%" if amt < 0 and abs(p) < 0.005 else f"{p:.2f}%")
    rec = dd["recovered_date"] or ("not yet" if dd["max_dd_amt"] < 0 else "—")
    cards = [
        rs.stat_card("Current drawdown", pct(dd["current_dd_pct"], dd["current_dd_amt"]),
                     (f"{money(-dd['current_dd_amt'])} below " + _peak(dd["peak_date"])
                      if dd["current_dd_amt"] < 0 else "at the peak")),
        rs.stat_card("Max drawdown", pct(dd["max_dd_pct"], dd["max_dd_amt"]),
                     (f"{money(-dd['max_dd_amt'])} · " + ("start" if dd["max_peak_date"] == START else dd["max_peak_date"]) + " → "
                      f"{dd['max_trough_date']}" if dd["max_dd_amt"] < 0
                      else "none in this history")),
        rs.stat_card("Recovered", rec, "back to the prior peak"),
        rs.stat_card("History", f"{dd['n_points']} days",
                     f"{dd['first_date']} → {dd['last_date']}"),
    ]
    src = dd["sources"]
    caps = []
    if src == [SOURCE_RECON]:
        caps.append("⚠ RECONSTRUCTED from the positions table and cached closes — "
                    "not a recorded history. It replays today's book: an edited or "
                    "deleted position rewrites the past, and today's capital is "
                    "assumed for every day.")
    elif SOURCE_RECON in src:
        caps.append(f"Mixed history — recorded snapshots, back-filled by "
                    f"reconstruction before the first one. The max drawdown rests "
                    f"on: {', '.join(dd['max_dd_sources'])}.")
    else:
        caps.append("Recorded history — one snapshot per trading day.")
    if dd["n_points"] < 20:
        caps.append(f"Only {dd['n_points']} trading days — a drawdown over this "
                    f"little history says almost nothing about the next one.")
    for ch in dd["capital_changes"]:
        caps.append(f"Capital changed on {ch['date']} ({money(ch['from_'])} → "
                    f"{money(ch['to'])}) — a deposit or withdrawal moves equity "
                    f"without being performance.")
    if dd["skipped"]:
        caps.append(f"{dd['skipped']} day(s) skipped: a held position had no price.")
    caps.append("Equity = capital + realised + unrealised P&L, before costs and "
                "taxes (B-110).")
    return rs.strip(cards, cols=cols), caps


def portfolio_strip(db, ohlcv_fn) -> tuple[str, list[str]]:
    """Everything the Portfolio page needs in one call: recorded snapshots, the
    reconstruction behind them, the drawdown and its card. Takes the db module
    and a price lookup so the page carries one line, not a block no test reaches."""
    if not (hasattr(db, "get_all_positions") and hasattr(db, "get_equity_snapshots")):
        # A long-running desk process can hold a portfolio_db imported before
        # the B-110 functions existed; say so instead of breaking the page.
        return "", ["Drawdown — restart the desk to load the equity-history "
                    "functions (portfolio_db is older than this card)."]
    capital = float(db.get_setting("total_capital", "0") or 0)
    recon = reconstruct(db.get_all_positions(), ohlcv_fn, capital)
    return drawdown_strip(drawdown(combined(db.get_equity_snapshots(), recon)))
