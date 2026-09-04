"""deal_infographic.py — the bulk/block-deal day, as one shareable board.

The India Market Intel page already has every deal row, and CEAVET already says
which of them mean something. What neither produced is the thing you actually
send someone: one image-shaped board with the day's deals ranked by market cap,
each row carrying the context that makes a deal readable — what the price did,
how large the deal was against the day's traded quantity, and how much of that
quantity was actually delivered rather than churned.

Layout is modelled on a public NSE bulk-deal board the user supplied as a
reference. Only the LAYOUT and the choice of columns were taken: the branding,
palette and the wording are this desk's, and no third party's handle, logo or
attribution is reproduced.

── Where each column comes from ──────────────────────────────────────────────

    Buy / Sell / Net qty   aggregated from the deal rows themselves
    Price change %         sec_bhavdata_full  CLOSE_PRICE vs PREV_CLOSE
    Trade %                deal qty / TTL_TRD_QNTY   (the day's whole tape)
    Delivery %             sec_bhavdata_full  DELIV_PER  (exchange-published)
    Delivery amount ₹Cr    DELIV_QTY x CLOSE_PRICE
    Market cap ₹Cr         yfinance, per symbol

One file — `sec_bhavdata_full_DDMMYYYY.csv` — carries price, traded quantity and
delivery in a single unauthenticated request, which is why this module fetches
it directly rather than composing three sources.

── Two limits, stated because they change how the board reads ────────────────

1. **Delivery % is NOT available for every scrip.** The file publishes it blank
   for series where NSE does not compute it. A blank renders as "—" and never as
   0 — a zero would read as "nothing was delivered", which is a different and
   much stronger claim than "not published".

2. **Market cap is a yfinance lookup, one call per symbol.** BSE-only scrips in
   the deal feed do not resolve, so they sort last and show "—". The split
   between the two tables is Nifty Total Market (≈750 names) membership, which
   is a *list*, not a size cut — a name can be large and still sit in table 2 if
   it is not an index constituent.

Nothing here is a signal. A bulk deal is a disclosure that someone traded, not
evidence they were right.

CLI:
    py -3 tools/deal_infographic.py                 # today, writes reports/
    py -3 tools/deal_infographic.py --date 02092026
    py -3 tools/deal_infographic.py --no-mcap       # skip the yfinance pass
    py -3 tools/deal_infographic.py --png           # HTML + PNG
"""
from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date as _date, datetime
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
REPORTS = HERE.parent / "reports"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/csv,*/*",
    "Referer": "https://www.nseindia.com/",
}

DELIVERY_URL = ("https://nsearchives.nseindia.com/products/content/"
                "sec_bhavdata_full_{ddmmyyyy}.csv")

CRORE = 1e7


# ──────────────────────────────────────────────────────────────────────────────
# Sources
# ──────────────────────────────────────────────────────────────────────────────

def fetch_delivery(ddmmyyyy: Optional[str] = None,
                   lookback: int = 5) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """`sec_bhavdata_full` for a session — price, traded qty and delivery in one.

    With no date, walks back from today until a session file exists: the file
    appears only after the close, and weekends/holidays have none. Returns
    (EQ-only frame, DD-Mon-YYYY date string).
    """
    days = [ddmmyyyy] if ddmmyyyy else [
        (pd.Timestamp.today() - pd.Timedelta(days=i)).strftime("%d%m%Y")
        for i in range(lookback)
    ]
    for d in days:
        try:
            r = requests.get(DELIVERY_URL.format(ddmmyyyy=d), headers=HEADERS, timeout=25)
        except Exception as e:
            log.warning("delivery fetch failed for %s: %s", d, e)
            continue
        if r.status_code != 200 or not r.text.strip():
            continue
        # skipinitialspace: every value in this file is written as ", EQ" with a
        # leading space. Stripping afterwards on `dtype == object` silently does
        # NOTHING under pandas' str dtype, which is how an EQ filter can quietly
        # return zero rows — so it is handled at parse time instead.
        df = pd.read_csv(StringIO(r.text), skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]
        for c in ("SYMBOL", "SERIES", "DATE1"):
            df[c] = df[c].astype(str).str.strip()
        df = df[df["SERIES"] == "EQ"].copy()
        if df.empty:
            log.warning("delivery file for %s has no EQ rows", d)
            continue
        for c in ("PREV_CLOSE", "CLOSE_PRICE", "TTL_TRD_QNTY", "DELIV_QTY", "DELIV_PER"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["SYMBOL"] = df["SYMBOL"].str.upper()
        sess = str(df["DATE1"].iloc[0]) if len(df) else d
        return df.set_index("SYMBOL"), sess
    return None, None


def total_market_symbols() -> set[str]:
    """Nifty Total Market constituents — the table 1 / table 2 split."""
    try:
        import nse_universe as nseu
        rows = nseu.fetch_constituents("niftytotalmarket")
        syms = {str(r.get("symbol", "")).upper() for r in rows if r.get("symbol")}
        if syms:
            return syms
    except Exception as e:
        log.warning("total-market list unavailable: %s", e)
    return set()


def _mcap_lookup(symbols: list[str], max_workers: int = 8,
                 mcap_fn: Optional[Callable[[str], Optional[float]]] = None,
                 ) -> dict[str, Optional[float]]:
    """Market cap in rupees per symbol. Injectable so tests never hit network."""
    if not symbols:
        return {}
    if mcap_fn is None:
        try:
            import nse_universe as nseu
            mcap_fn = nseu.market_cap
        except Exception as e:
            log.warning("market cap unavailable: %s", e)
            return {s: None for s in symbols}

    def _one(s):
        try:
            return s, mcap_fn(s)
        except Exception:
            return s, None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return dict(pool.map(_one, symbols))


# ──────────────────────────────────────────────────────────────────────────────
# Assembly
# ──────────────────────────────────────────────────────────────────────────────

def build(deals: pd.DataFrame,
          ddmmyyyy: Optional[str] = None,
          delivery: Optional[pd.DataFrame] = None,
          session: Optional[str] = None,
          index_symbols: Optional[set[str]] = None,
          with_mcap: bool = True,
          mcap_fn: Optional[Callable[[str], Optional[float]]] = None,
          ) -> dict[str, Any]:
    """One row per SYMBOL, split into index / beyond-index tables.

    `deals` is `block_deal_intel.normalize_deals()` output. Everything that
    touches the network is injectable.
    """
    if deals is None or deals.empty:
        return {"error": "no deal rows for this session", "index_rows": [],
                "other_rows": [], "panels": {}}

    if delivery is None:
        delivery, session = fetch_delivery(ddmmyyyy)
    if delivery is None:
        return {"error": "sec_bhavdata_full unreachable — no delivery/price context",
                "index_rows": [], "other_rows": [], "panels": {}}

    d = deals.copy()
    d["symbol"] = d["symbol"].astype(str).str.strip().str.upper()
    d["qty"] = pd.to_numeric(d["qty"], errors="coerce").fillna(0.0)

    # NSE publishes a block deal in BOTH bulk.csv and block.csv when it also
    # clears the bulk threshold — same client, side, quantity and price, twice.
    # Measured 2026-09-02: ASTERDM's 46,09,800 share cross appeared in both files
    # on both legs, which doubled its quantities and printed a 722% share of the
    # day's tape. Identical (venue, scrip, client, side, qty, price) is therefore
    # treated as ONE deal reported twice, not two trades that happened to match.
    _keys = [c for c in ("exchange", "symbol", "client", "side", "qty", "price")
             if c in d.columns]
    n_raw = len(d)
    d = d.drop_duplicates(subset=_keys, keep="first")
    n_dupes = n_raw - len(d)

    grp = d.groupby("symbol")
    buy = grp.apply(lambda g: g.loc[g["side"] == "BUY", "qty"].sum(), include_groups=False)
    sell = grp.apply(lambda g: g.loc[g["side"] == "SELL", "qty"].sum(), include_groups=False)
    # Trade % is a share of the NSE tape, so its numerator must be the NSE legs
    # only — a BSE cross measured against NSE volume is a category error.
    _nse = d[d["exchange"] == "NSE"] if "exchange" in d.columns else d
    _ngrp = _nse.groupby("symbol")
    nse_buy = _ngrp.apply(lambda g: g.loc[g["side"] == "BUY", "qty"].sum(),
                          include_groups=False) if len(_nse) else pd.Series(dtype=float)
    nse_sell = _ngrp.apply(lambda g: g.loc[g["side"] == "SELL", "qty"].sum(),
                           include_groups=False) if len(_nse) else pd.Series(dtype=float)
    names = grp["name"].first()

    syms = sorted(buy.index.tolist())
    mcaps = _mcap_lookup(syms, mcap_fn=mcap_fn) if with_mcap else {s: None for s in syms}

    idx = index_symbols if index_symbols is not None else total_market_symbols()

    rows: list[dict[str, Any]] = []
    for s in syms:
        b, sl = float(buy.get(s, 0.0)), float(sell.get(s, 0.0))
        rec: dict[str, Any] = {
            "symbol": s,
            "name": str(names.get(s, "") or "").title(),
            "buy_qty": b, "sell_qty": sl, "net_qty": b - sl,
            "mcap_cr": None, "chg_pct": None, "trade_pct": None,
            "deliv_pct": None, "deliv_cr": None, "in_index": s in idx,
        }
        mc = mcaps.get(s)
        if mc:
            rec["mcap_cr"] = mc / CRORE

        if s in delivery.index:
            r = delivery.loc[s]
            if isinstance(r, pd.DataFrame):          # duplicate symbol rows
                r = r.iloc[0]
            close, prev = r.get("CLOSE_PRICE"), r.get("PREV_CLOSE")
            if pd.notna(close) and pd.notna(prev) and prev:
                rec["chg_pct"] = (close / prev - 1) * 100
            ttl = r.get("TTL_TRD_QNTY")
            _nb, _ns = float(nse_buy.get(s, 0.0)), float(nse_sell.get(s, 0.0))
            if pd.notna(ttl) and ttl and max(_nb, _ns):
                # Deal quantity against the day's whole tape. Buy and sell legs
                # of the same block are the SAME shares crossing once, so the
                # numerator is the larger leg, not their sum — adding them would
                # double-count and can print >100%.
                rec["trade_pct"] = max(_nb, _ns) / float(ttl) * 100
            dp, dq = r.get("DELIV_PER"), r.get("DELIV_QTY")
            # Blank stays blank: 0 would claim "nothing delivered", which is a
            # much stronger statement than "NSE did not publish it".
            if pd.notna(dp):
                rec["deliv_pct"] = float(dp)
            if pd.notna(dq) and pd.notna(close):
                rec["deliv_cr"] = float(dq) * float(close) / CRORE
        rows.append(rec)

    def _by_mcap(rs):
        return sorted(rs, key=lambda r: (r["mcap_cr"] is None,
                                         -(r["mcap_cr"] or 0)))

    index_rows = _by_mcap([r for r in rows if r["in_index"]])
    other_rows = _by_mcap([r for r in rows if not r["in_index"]])

    def _top5(key, reverse=True):
        vals = [r for r in rows if r.get(key) is not None]
        return sorted(vals, key=lambda r: r[key], reverse=reverse)[:5]

    panels = {
        "deliv_cr": _top5("deliv_cr"),
        "chg_pct": _top5("chg_pct"),
        "trade_pct": _top5("trade_pct"),
        "deliv_pct": _top5("deliv_pct"),
    }

    return {"session": session, "index_rows": index_rows, "other_rows": other_rows,
            "panels": panels, "n_deals": int(len(d)), "n_dupes": int(n_dupes),
            "n_symbols": len(rows),
            "n_index": len(index_rows), "n_other": len(other_rows),
            "with_mcap": with_mcap,
            "n_no_mcap": sum(1 for r in rows if r["mcap_cr"] is None),
            "n_no_deliv": sum(1 for r in rows if r["deliv_pct"] is None)}


# ──────────────────────────────────────────────────────────────────────────────
# Render
# ──────────────────────────────────────────────────────────────────────────────

_CSS = """
:root{--bg:#0b1220;--panel:#111b2e;--line:#1f2f4a;--head:#16233c;
 --ink:#e8eef8;--dim:#8fa3c0;--up:#22c55e;--down:#ef4444;--gold:#f5b301;--cyan:#38bdf8}
*{box-sizing:border-box}
.dib{background:var(--bg);color:var(--ink);font-family:"Segoe UI",Roboto,Arial,sans-serif;
 padding:14px;max-width:1060px;margin:0 auto;border-radius:10px}
.dib h1{font-size:26px;margin:0;letter-spacing:.5px;text-transform:uppercase}
.dib .hero{display:flex;align-items:center;gap:14px;border:1px solid var(--line);
 border-radius:10px;padding:12px 16px;background:linear-gradient(90deg,#0d1729,#132244)}
.dib .hero .sub{font-size:11px;color:var(--dim);letter-spacing:.08em;text-transform:uppercase}
.dib .meta{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0 14px}
.dib .meta div{border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--panel)}
.dib .meta .k{font-size:10px;color:var(--dim);letter-spacing:.08em;text-transform:uppercase}
.dib .meta .v{font-size:13px;font-weight:700;color:var(--gold);margin-top:2px}
.dib .tbl-head{display:flex;justify-content:space-between;align-items:center;
 background:var(--head);border:1px solid var(--line);border-radius:8px 8px 0 0;
 padding:8px 12px;font-weight:800;font-size:14px;letter-spacing:.04em}
.dib .count{background:#14532d;color:#bbf7d0;border-radius:6px;padding:2px 8px;font-size:11px}
.dib table{width:100%;border-collapse:collapse;font-size:11.5px;
 border:1px solid var(--line);border-top:0;margin-bottom:16px}
.dib th{background:#16233c;color:var(--dim);font-weight:600;text-align:right;
 padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
.dib th:nth-child(-n+3),.dib td:nth-child(-n+3){text-align:left}
.dib td{padding:5px 8px;border-bottom:1px solid #16233c;text-align:right;white-space:nowrap}
.dib tbody tr:nth-child(even){background:#0e1830}
.dib .sym{color:var(--cyan);font-weight:700}
.dib .nm{color:var(--dim);max-width:190px;overflow:hidden;text-overflow:ellipsis}
.dib .up{color:var(--up);font-weight:700}.dib .down{color:var(--down);font-weight:700}
.dib .na{color:#64748b}
.dib .over{color:var(--gold);font-weight:700}
.dib .panels{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:4px}
.dib .panel{border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--panel)}
.dib .panel h3{margin:0;font-size:11px;padding:7px 9px;letter-spacing:.04em;
 text-transform:uppercase;background:#16233c;color:var(--ink)}
.dib .panel table{border:0;margin:0;font-size:11px}
.dib .foot{margin-top:14px;border:1px solid var(--line);border-radius:8px;
 padding:10px 12px;font-size:10.5px;color:var(--dim);line-height:1.6;background:var(--panel)}
"""


def _f(v, nd=2, dash="—"):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return f'<span class="na">{dash}</span>'
    return f"{v:,.{nd}f}"


def _pct(v, nd=2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span class="na">—</span>'
    cls = "up" if v > 0 else "down" if v < 0 else ""
    return f'<span class="{cls}">{v:+.{nd}f}%</span>' if cls else f"{v:.{nd}f}%"


def _qty(v):
    if v is None:
        return '<span class="na">—</span>'
    return f"{v:,.0f}"


def _net(v):
    if v is None:
        return '<span class="na">—</span>'
    cls = "up" if v > 0 else "down" if v < 0 else ""
    return f'<span class="{cls}">{v:+,.0f}</span>' if cls else "0"


def _trade(v):
    """Deal share of the tape. >100% is a real reading, not an error: NSE's
    delivery file counts the NORMAL market only, and a block crosses in its own
    window — so a cross larger than the whole regular session prints above 100
    and is flagged gold rather than clipped or hidden."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span class="na">—</span>'
    cls = ' class="over"' if v > 100 else ""
    return f"<span{cls}>{v:,.2f}%</span>"


def _table(title: str, rows: list[dict], n_label: str) -> str:
    head = (f'<div class="tbl-head"><span>{title}</span>'
            f'<span class="count">{n_label}</span></div>')
    if not rows:
        return head + ('<table><tbody><tr><td colspan="10" style="text-align:center;'
                       'padding:14px;color:#8fa3c0">No deals in this bucket.</td>'
                       '</tr></tbody></table>')
    th = ("<tr><th>#</th><th>Symbol</th><th>Stock</th><th>Mkt Cap ₹Cr</th>"
          "<th>Chg %</th><th>Buy Qty</th><th>Sell Qty</th><th>Net Qty</th>"
          "<th>Trade %</th><th>Deliv %</th><th>Deliv ₹Cr</th></tr>")
    body = []
    for i, r in enumerate(rows, 1):
        body.append(
            f'<tr><td>{i}</td><td class="sym">{r["symbol"]}</td>'
            f'<td class="nm">{r["name"]}</td>'
            f'<td>{_f(r["mcap_cr"], 2)}</td><td>{_pct(r["chg_pct"])}</td>'
            f'<td>{_qty(r["buy_qty"])}</td><td>{_qty(r["sell_qty"])}</td>'
            f'<td>{_net(r["net_qty"])}</td><td>{_trade(r["trade_pct"])}</td>'
            f'<td>{_f(r["deliv_pct"])}%</td><td>{_f(r["deliv_cr"])}</td></tr>')
    return head + f"<table><thead>{th}</thead><tbody>{''.join(body)}</tbody></table>"


def _panel(title: str, rows: list[dict], key: str, unit: str, nd: int = 2) -> str:
    body = []
    for i, r in enumerate(rows, 1):
        v = r.get(key)
        cell = (_pct(v, nd) if key == "chg_pct"
                else _trade(v) if key == "trade_pct"
                else f"{v:,.{nd}f}")
        body.append(f'<tr><td>{i}</td><td class="sym">{r["symbol"]}</td>'
                    f'<td>{cell}</td></tr>')
    if not body:
        body = ['<tr><td colspan="3" style="color:#64748b">not published</td></tr>']
    return (f'<div class="panel"><h3>{title}</h3><table><thead>'
            f'<tr><th>#</th><th>Symbol</th><th>{unit}</th></tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def render_html(payload: dict[str, Any], *, standalone: bool = True) -> str:
    """The board. `standalone=False` returns the fragment for embedding."""
    if payload.get("error"):
        inner = (f'<div class="dib"><div class="foot">Could not build the board: '
                 f'{payload["error"]}</div></div>')
        return _wrap(inner) if standalone else f"<style>{_CSS}</style>{inner}"

    sess = payload.get("session") or "—"
    gen = datetime.now().strftime("%d-%b-%Y %H:%M")
    body = [
        '<div class="dib">',
        '<div class="hero"><div>'
        '<div class="sub">Trading Bramha · Market Intel</div>'
        '<h1>Bulk &amp; Block Deal Board</h1>'
        '<div class="sub">Disclosures, ranked by size — not recommendations</div>'
        '</div></div>',
        '<div class="meta">'
        f'<div><div class="k">Source</div><div class="v">NSE + BSE deal feeds</div></div>'
        f'<div><div class="k">Session</div><div class="v">{sess}</div></div>'
        f'<div><div class="k">Deals · Scrips</div>'
        f'<div class="v">{payload.get("n_deals", 0)} · {payload.get("n_symbols", 0)}</div></div>'
        f'<div><div class="k">Sorted by</div><div class="v">Market cap (high → low)</div></div>'
        '</div>',
        _table("TABLE 1 · NIFTY TOTAL MARKET CONSTITUENTS",
               payload["index_rows"], f'{payload.get("n_index", 0)} stocks'),
        _table("TABLE 2 · BEYOND THE INDEX",
               payload["other_rows"], f'{payload.get("n_other", 0)} stocks'),
        '<div class="panels">',
        _panel("Top 5 · delivery amount", payload["panels"].get("deliv_cr", []),
               "deliv_cr", "₹ Cr"),
        _panel("Top 5 · price change", payload["panels"].get("chg_pct", []),
               "chg_pct", "Chg %"),
        _panel("Top 5 · deal share of tape", payload["panels"].get("trade_pct", []),
               "trade_pct", "Trade %"),
        _panel("Top 5 · delivery %", payload["panels"].get("deliv_pct", []),
               "deliv_pct", "Deliv %"),
        '</div>',
        '<div class="foot">'
        '<b>How to read this.</b> A bulk/block deal is a <i>disclosure that someone '
        'traded</i> — not evidence they were right, and not a recommendation. '
        '<b>Trade %</b> is the larger NSE deal leg against the NORMAL-market traded quantity for that session. The delivery file excludes the block window, so a pure block cross legitimately prints above 100% (gold): the block was bigger than the whole regular session. '
        '<b>Delivery %</b> and <b>Delivery &#8377;Cr</b> come from the NSE published delivery file and are shown as &ldquo;&mdash;&rdquo;, never 0, where NSE publishes nothing. '
        f'{payload.get("n_no_deliv", 0)} scrip(s) here have no published delivery figure'
        + (f' and {payload.get("n_no_mcap", 0)} no resolvable market cap (BSE-only '
           f'scrips do not resolve).' if payload.get("with_mcap") else
           ' · market-cap lookup was skipped for this run.')
        + f' Table 1 is Nifty Total Market membership — a list, not a size cut. '
          f'{payload.get("n_dupes", 0)} row(s) were the same deal published in both '
          f'the bulk and block file and were counted once. '
          f'Generated {gen}. Educational use only; nothing here executes trades.'
        '</div>',
        '</div>',
    ]
    inner = "".join(body)
    return _wrap(inner) if standalone else f"<style>{_CSS}</style>{inner}"


def _wrap(inner: str) -> str:
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Bulk &amp; Block Deal Board</title>"
            f"<style>body{{margin:0;background:#0b1220}}{_CSS}</style></head>"
            f"<body>{inner}</body></html>")


# ──────────────────────────────────────────────────────────────────────────────
# PNG
# ──────────────────────────────────────────────────────────────────────────────
# The board is meant to be SENT, and what people send is an image. Playwright is
# already a dependency of this repo, so the HTML is rendered by the same engine
# that displays it — a client-side canvas library (html2canvas) re-implements CSS
# and quietly drops what it does not support, which for a board of numbers means
# shipping a subtly wrong picture rather than failing.
#
# Threaded because Playwright's SYNC api refuses to start inside a thread that
# already owns an asyncio loop, which is exactly the situation inside a Streamlit
# script run. A fresh thread has no loop, so the same call is safe there.

PNG_WIDTH = 1100          # css px; the board's max-width is 1060 + padding
PNG_SCALE = 2             # retina — a 1x board is unreadable when resized


def render_png(html: str, width: int = PNG_WIDTH, scale: int = PNG_SCALE,
               timeout_ms: int = 30_000) -> bytes:
    """Full-page PNG of a rendered board. Raises RuntimeError if unavailable."""
    def _shot() -> bytes:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:                        # pragma: no cover
            raise RuntimeError(
                "Playwright is not installed — `py -3 -m pip install playwright` "
                f"then `playwright install chromium`. ({e})") from e
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    page = browser.new_page(
                        viewport={"width": width, "height": 1400},
                        device_scale_factor=scale)
                    page.set_content(html, wait_until="load", timeout=timeout_ms)
                    # Shoot the BOARD element, not the page: a full-page shot is
                    # padded to the viewport height, so a short session came out
                    # as a small board on a tall empty rectangle.
                    board = page.locator(".dib")
                    if board.count():
                        return board.first.screenshot(type="png")
                    return page.screenshot(full_page=True, type="png")
                finally:
                    browser.close()
        except Exception as e:
            raise RuntimeError(
                "Chromium could not render the board — if this says 'Executable "
                "doesn't exist', run `playwright install chromium`. "
                f"({type(e).__name__}: {e})") from e

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_shot).result()


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def collect_deals() -> pd.DataFrame:
    """Today's deal rows from all four feeds, in the shared schema."""
    import block_deal_intel as bdi
    import india_market_intel as imi

    def _try(fn):
        try:
            return fn()
        except Exception as e:
            log.warning("%s failed: %s", getattr(fn, "__name__", fn), e)
            return pd.DataFrame()

    return bdi.normalize_deals(_try(imi.fetch_nse_bulk_deals),
                               _try(imi.fetch_nse_block_deals),
                               _try(imi.fetch_bse_bulk_deals),
                               _try(imi.fetch_bse_block_deals))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bulk/block deal infographic")
    ap.add_argument("--date", help="session as DDMMYYYY (default: latest available)")
    ap.add_argument("--no-mcap", action="store_true",
                    help="skip the per-symbol market-cap lookup")
    ap.add_argument("--out", help="output HTML path")
    ap.add_argument("--png", action="store_true",
                    help="also write a PNG beside the HTML (needs Chromium)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    deals = collect_deals()
    print(f"{len(deals)} deal rows")
    payload = build(deals, ddmmyyyy=a.date, with_mcap=not a.no_mcap)
    if payload.get("error"):
        print("ERROR:", payload["error"])
        return 1

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = Path(a.out) if a.out else (
        REPORTS / f"deal_board_{_date.today().strftime('%Y%m%d')}.html")
    html = render_html(payload)
    out.write_text(html, encoding="utf-8")
    print(f"{payload['n_symbols']} scrips "
          f"({payload['n_index']} index / {payload['n_other']} beyond) -> {out}")
    if a.png:
        try:
            png = out.with_suffix(".png")
            png.write_bytes(render_png(html))
            print(f"PNG -> {png}")
        except RuntimeError as e:
            print("PNG skipped:", e)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
