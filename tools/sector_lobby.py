#!/usr/bin/env python3
"""SL-1 — Sector Lobby: every same-industry peer in one sliding ribbon.

What this module is
-------------------
The logic behind the "Sector Lobby" page. Pick one stock; every listed name in
its industry lines up as a horizontal ribbon of cards (price, day move,
sparkline against previous close), and the page steps through them one at a
time so a whole sector can be read in a single sitting.

What it reuses, and what it deliberately does not
-------------------------------------------------
* **Membership** comes from `peer_comparison.resolve_peers` — the same
  two-stage NSE macro-sector -> yfinance fine-industry resolution, the same
  disk tag cache and the same MIN_PEERS floor the Stock Analyzer uses. A lobby
  that disagreed with the analyzer's peer table about who the peers are would
  be two answers to one question.
* **MAX_PEERS is not applied.** That cap exists because *scoring* a peer costs
  ~4 network calls. The lobby scores nothing; it needs one batched price
  download for the whole group. Capping by market cap here would silently drop
  exactly the small caps a sector scan is usually looking for.
* **Overrides** (`cache/lobby_overrides.json`) let a mis-tagged name be pinned
  in or excluded, keyed by the group label. They are additive to the
  resolution, never a replacement for it.

Honesty rules carried over from the rest of the desk
----------------------------------------------------
* A symbol whose prices did not resolve keeps its card and reads DATA N/A. It
  is never ranked as if it had moved 0%.
* Ranks are computed only over names that have the figure; the denominator is
  stated ("3 / 9"), so a rank out of a thinned field is visible as one.

Pure functions only — no Streamlit import. The page lives in
`desk_pages/sector_lobby.py`.
"""
from __future__ import annotations

import html
import json
import logging
import math
from pathlib import Path
from typing import Any, Callable

import pandas as pd

_log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
OVERRIDES_FILE = HERE / "cache" / "lobby_overrides.json"

#: Trading-day lookbacks for the period returns.
BARS_1M = 21
BARS_6M = 126
BARS_52W = 252
SPARK_BARS = 30

#: Ribbon sort options: label -> (card field, descending?)
SORT_OPTIONS: dict[str, tuple[str, bool]] = {
    "Market cap":   ("mcap_cr", True),
    "Today %":      ("chg_1d", True),
    "1M %":         ("ret_1m", True),
    "6M %":         ("ret_6m", True),
    "Near 52W high": ("off_high", True),   # off_high is <= 0; closest to 0 first
    # Hurst FLD confluence expected value (ATR units), see fld_confluence.py.
    # A stock whose confluence points the other way has no value here and sorts last.
    "FLD EV — longs": ("fld_ev_long", True),
    "FLD EV — shorts": ("fld_ev_short", True),
}

NA = "DATA N/A"


# ──────────────────────────────────────────────────────────────────────────────
# Membership
# ──────────────────────────────────────────────────────────────────────────────
def load_overrides(path: Path = OVERRIDES_FILE) -> dict[str, dict]:
    """{group_label: {"pin": [...], "exclude": [...]}} — empty when absent or bad."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        _log.warning("sector_lobby: unreadable overrides file %s", path)
        return {}


def apply_overrides(members: list[str], label: str | None,
                    overrides: dict[str, dict]) -> list[str]:
    """Pin extra names in and drop excluded ones for this group. Order kept;
    pins append at the end (they get re-sorted on the page anyway)."""
    rule = overrides.get(label or "", {}) if label else {}
    excl = {s.strip().upper() for s in rule.get("exclude", [])}
    out = [s for s in members if s not in excl]
    for s in rule.get("pin", []):
        s = s.strip().upper()
        if s and s not in out and s not in excl:
            out.append(s)
    return out


def _cross_sector(anchor: str, res: dict, deps: dict | None) -> dict | None:
    """Second rung when the NSE-sector pool is too thin: search where the
    anchor's *industry* actually lives.

    NSE's macro sector and yfinance's industry disagree often enough to matter —
    JSLL is "Consumer Services" to NSE (hotels, restaurants) and "Medical Care
    Facilities" to yfinance, so its real peers (hospitals) sit in NSE's
    "Healthcare" and the first rung never sees them. The extra NSE sectors are
    the ones where already-tagged names share the anchor's industry or yfinance
    sector, plus any NSE sector named like the yfinance sector (covers a cold
    cache). Returns the fields to merge into the lobby, or None.
    """
    if deps is None:
        import peer_comparison as pcmp
        deps = {"universe": pcmp._constituents(), "cache": pcmp._load_tags(),
                "tag": pcmp.tag_symbols, "family": pcmp._family,
                "min_peers": pcmp.MIN_PEERS, "pool_cap": pcmp.POOL_CAP}
    tags = dict(res.get("tags") or {})
    own = tags.get(anchor)
    if not own:
        # Off-index anchor (small/micro-caps such as PREMIERPOL are not in the
        # NIFTY-500 / Total-Market files): it has no NSE pool, but it can still
        # be tagged on its own, and its yfinance industry then says where to look.
        try:
            own = (deps["tag"]([anchor]) or {}).get(anchor)
        except Exception:
            own = None
        if own:
            tags[anchor] = own
    if not own or not own.get("industry"):
        return None
    universe, cache = deps["universe"], deps["cache"]
    ind, ysec = own["industry"], (own.get("sector") or "").strip().lower()
    home = res.get("macro_sector")
    macros = {r.get("macro_sector") for s, r in universe.items()
              if (t := cache.get(s)) and (t.get("industry") == ind
                                          or (ysec and (t.get("sector") or "").lower() == ysec))}
    macros |= {r.get("macro_sector") for r in universe.values()
               if ysec and (r.get("macro_sector") or "").strip().lower() == ysec}
    macros.discard(None)
    macros.discard(home)
    if not macros:
        return None
    pool = [s for s, r in universe.items() if r.get("macro_sector") in macros]
    merged = dict(tags)
    merged.update(deps["tag"](pool[:deps["pool_cap"]]))
    same = [s for s, t in merged.items() if t.get("industry") == ind and s != anchor]
    label, level = ind, "industry"
    if len(same) < deps["min_peers"]:
        fam = deps["family"](ind)
        same = [s for s, t in merged.items()
                if deps["family"](t.get("industry")) == fam and s != anchor]
        label, level = fam, "family"
        if len(same) < deps["min_peers"]:
            return None
    same.sort(key=lambda s: (merged[s].get("market_cap_cr") or -1), reverse=True)
    return {"ok": True, "reason": None, "label": label, "level": level,
            "macro_sector": " + ".join(sorted(m for m in macros | {home} if m)),
            "cross_sector": True, "off_index": anchor not in universe,
            "tags": merged, "_peers": same}


# ──────────────────────────────────────────────────────────────────────────────
# Third-party fallback — screener.in's NSE basic-industry listing
# ──────────────────────────────────────────────────────────────────────────────
# Why screener.in: its public company page carries NSE's own four-level
# classification (the repo already reads it in `industry_map.py`), and each
# basic-industry page lists EVERY company in it — micro-caps included — sorted by
# market cap, with P/E and market cap in the row. That is exactly the gap the
# yfinance rungs leave: names outside NIFTY Total Market, and names yfinance
# cannot tag. No login is needed for either page.
#
# Trendlyne was considered and not used: it gates its pages behind bot checks,
# and scraping around those is not something this desk should depend on.
SCREENER = "https://www.screener.in"
SCREENER_CACHE = HERE / "cache" / "screener_peers.json"
SCREENER_TTL = 7 * 24 * 3600
SCREENER_PAGES = 3                  # 50 rows a page -> at most 150 names
_HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 Chrome/126 Safari/537.36"}

import re as _re
_MARKET_LINK = _re.compile(r'href="(/market/[A-Z0-9/]+/)"[^>]*>\s*([^<]+?)\s*</a>')
_ROW = _re.compile(r'<tr[^>]*>(.*?)</tr>', _re.S)
_CO = _re.compile(r'href="/company/([^/"]+)/[^"]*"[^>]*>\s*([^<]+?)\s*</a>')
_TD = _re.compile(r'<td[^>]*>(.*?)</td>', _re.S)


def parse_company_classification(page: str) -> dict | None:
    """{path, labels} for the deepest /market/ link on a company page."""
    seen: dict[str, str] = {}
    for href, label in _MARKET_LINK.findall(page):
        seen.setdefault(href, html.unescape(label).strip())
    if not seen:
        return None
    deepest = max(seen, key=lambda h: h.count("/"))
    chain = sorted((h for h in seen if deepest.startswith(h)), key=lambda h: h.count("/"))
    return {"path": deepest, "labels": [seen[h] for h in chain]}


def parse_market_rows(page: str) -> list[dict]:
    """Company rows from a /market/ listing: symbol, name, P/E, market cap (Cr).
    BSE-only scrips (numeric codes) are dropped — the lobby prices via `.NS`."""
    out = []
    for row in _ROW.findall(page):
        m = _CO.search(row)
        if not m:
            continue
        sym, name = m.group(1).strip().upper(), html.unescape(m.group(2)).strip()
        if sym.isdigit():
            continue
        cells = [_re.sub(r"<[^>]+>", "", c).strip() for c in _TD.findall(row)]
        # S.No., Company, CMP, P/E, Mar Cap, ...
        out.append({"symbol": sym, "name": name,
                    "pe": _num(cells[3].replace(",", "")) if len(cells) > 3 else None,
                    "mcap_cr": _num(cells[4].replace(",", "")) if len(cells) > 4 else None})
    return out


def screener_peers(anchor: str, *, get: Callable[[str], str | None] | None = None,
                   cache_path: Path | None = None, now: float | None = None) -> dict | None:
    """Anchor's NSE basic-industry peer list from screener.in, disk-cached 7 days.
    Returns {label, labels, rows} or None when either page cannot be read."""
    import time as _time
    cache_path = cache_path or SCREENER_CACHE
    now = _time.time() if now is None else now
    a = anchor.strip().upper()
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    except Exception:
        cache = {}
    hit = cache.get(a)
    if hit and now - hit.get("ts", 0) < SCREENER_TTL:
        return hit
    if get is None:
        import requests
        sess = requests.Session()
        sess.headers.update(_HDRS)
        def get(url: str) -> str | None:
            try:
                r = sess.get(url, timeout=20)
                return r.text if r.status_code == 200 else None
            except Exception:
                return None
    page = get(f"{SCREENER}/company/{a}/")
    cls = parse_company_classification(page or "")
    if not cls:
        return None
    rows: list[dict] = []
    for n in range(1, SCREENER_PAGES + 1):
        listing = get(f"{SCREENER}{cls['path']}?limit=50&page={n}")
        got = parse_market_rows(listing or "")
        rows += [r for r in got if r["symbol"] not in {x["symbol"] for x in rows}]
        if len(got) < 50:
            break
    if not rows:
        return None
    out = {"label": cls["labels"][-1], "labels": cls["labels"], "rows": rows, "ts": now}
    cache[a] = out
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
    except Exception as e:
        _log.warning("sector_lobby: could not write screener cache: %s", e)
    return out


def _from_screener(anchor: str, sp: dict | None, min_peers: int) -> dict | None:
    """Lobby fields from a screener_peers result, or None when too thin."""
    if not sp:
        return None
    rows = sp["rows"]
    peers = [r["symbol"] for r in rows if r["symbol"] != anchor]
    if len(peers) < min_peers:
        return None
    tags = {r["symbol"]: {"name": r["name"], "market_cap_cr": r["mcap_cr"],
                          "industry": sp["label"], "screener_pe": r["pe"]} for r in rows}
    return {"ok": True, "reason": None, "label": sp["label"], "level": "nse_basic",
            "macro_sector": " › ".join(sp["labels"][:-1]), "source": "screener.in",
            "cross_sector": False, "tags": tags, "_peers": peers}


def lobby_members(anchor: str, *, resolve: Callable[..., dict] | None = None,
                  overrides: dict[str, dict] | None = None,
                  cross: dict | None = None, source: str = "auto",
                  screener: Callable[[str], dict | None] | None = None) -> dict[str, Any]:
    """Resolve the anchor's full lobby: anchor + every peer in its group.

    Returns `{ok, reason, anchor, label, level, macro_sector, members, tags}`.
    `members` always starts with the anchor.

    `source`: "auto" tries yfinance industry (NSE sector, then across sectors)
    and falls back to screener.in's NSE basic industry; "screener" goes to
    screener.in directly.
    """
    if resolve is None:
        import peer_comparison as pcmp
        resolve = pcmp.resolve_peers
    a = (anchor or "").strip().upper()
    screener = screener or screener_peers
    if source == "screener":
        res = {"ok": False, "reason": None, "tags": {}}
    else:
        res = resolve(a, max_peers=10_000)
    out: dict[str, Any] = {
        "ok": bool(res.get("ok")), "reason": res.get("reason"), "anchor": a,
        "label": res.get("group_label") or res.get("industry"),
        "level": res.get("group_level"), "macro_sector": res.get("macro_sector"),
        "tags": res.get("tags") or {}, "members": [], "cross_sector": False,
    }
    out["source"] = "yfinance"
    if not out["ok"]:
        widened = _cross_sector(a, res, cross) if source != "screener" else None
        if widened is None:
            try:
                widened = _from_screener(a, screener(a), (cross or {}).get("min_peers", 4))
            except Exception as e:
                _log.warning("sector_lobby: screener fallback failed for %s: %s", a, e)
                widened = None
        if widened is None:
            if source == "screener":
                out["reason"] = (f"screener.in has no NSE basic-industry listing with at "
                                 f"least 4 NSE peers for {a}.")
            return out
        out.update(widened)
    ov = load_overrides() if overrides is None else overrides
    peers = apply_overrides([a] + [p for p in out.pop("_peers", None) or res.get("peers", [])
                                   if p != a],
                            out["label"], ov)
    if a not in peers:              # an override cannot evict the anchor itself
        peers.insert(0, a)
    out["members"] = peers
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Prices — one batched download for the whole lobby
# ──────────────────────────────────────────────────────────────────────────────
def fetch_frames(symbols: list[str], *, download: Callable[..., Any] | None = None,
                 period: str = "1y") -> dict[str, pd.DataFrame | None]:
    """symbol -> daily OHLCV frame (lower-case columns) or None. ONE call."""
    if not symbols:
        return {}
    if download is None:
        import yfinance as yf
        download = yf.download
    tickers = [s if s.endswith(".NS") else f"{s}.NS" for s in symbols]
    out: dict[str, pd.DataFrame | None] = {s: None for s in symbols}
    try:
        raw = download(tickers, period=period, interval="1d", group_by="ticker",
                       auto_adjust=True, progress=False, threads=True)
    except Exception as e:                       # network: every card goes N/A
        _log.warning("sector_lobby: batch download failed: %s", e)
        return out
    if raw is None or getattr(raw, "empty", True):
        return out
    multi = isinstance(raw.columns, pd.MultiIndex)
    avail = set(raw.columns.get_level_values(0)) if multi else set()
    for sym, tk in zip(symbols, tickers):
        try:
            if multi:
                if tk not in avail:
                    continue
                f = raw[tk].copy()
            else:                                 # single ticker -> flat columns
                f = raw.copy()
            f.columns = [str(c).lower() for c in f.columns]
            f = f.dropna(subset=["close"])
            out[sym] = f if not f.empty else None
        except Exception:
            out[sym] = None
    return out


def _ret(closes: pd.Series, bars: int) -> float | None:
    if len(closes) <= bars:
        return None
    base = float(closes.iloc[-1 - bars])
    return None if base <= 0 else (float(closes.iloc[-1]) / base - 1) * 100


def quote_facts(frame: pd.DataFrame | None) -> dict[str, Any]:
    """Price facts for one card. Every field is None when it cannot be computed."""
    blank = {"last": None, "prev": None, "chg_1d": None, "chg_abs": None,
             "ret_1m": None, "ret_6m": None, "hi52": None, "lo52": None,
             "off_high": None, "spark": [], "asof": None}
    if frame is None or frame.empty or "close" not in frame:
        return blank
    c = frame["close"].astype(float).dropna()
    if c.empty:
        return blank
    last = float(c.iloc[-1])
    prev = float(c.iloc[-2]) if len(c) >= 2 else None
    win = c.iloc[-BARS_52W:]
    hi_src = frame["high"].iloc[-BARS_52W:] if "high" in frame else win
    lo_src = frame["low"].iloc[-BARS_52W:] if "low" in frame else win
    hi52, lo52 = float(hi_src.max()), float(lo_src.min())
    out = dict(blank)
    out.update({
        "last": last, "prev": prev,
        "chg_abs": None if prev is None else last - prev,
        "chg_1d": None if not prev else (last / prev - 1) * 100,
        "ret_1m": _ret(c, BARS_1M), "ret_6m": _ret(c, BARS_6M),
        "hi52": hi52, "lo52": lo52,
        "off_high": None if hi52 <= 0 else (last / hi52 - 1) * 100,
        "spark": [round(float(v), 2) for v in c.iloc[-SPARK_BARS:]],
        "asof": str(c.index[-1])[:10],
    })
    return out


def build_cards(members: list[str], frames: dict[str, Any],
                tags: dict[str, dict]) -> list[dict]:
    cards = []
    for s in members:
        t = tags.get(s) or {}
        card = {"symbol": s, "name": t.get("name") or s,
                "mcap_cr": t.get("market_cap_cr"), "industry": t.get("industry")}
        card.update(quote_facts(frames.get(s)))
        cards.append(card)
    return cards


def attach_fld(cards: list[dict], scores: dict[str, dict | None]) -> list[dict]:
    """Copy the FLD confluence reading onto each card (None where there is none)."""
    for c in cards:
        f = scores.get(c["symbol"]) or {}
        c["fld_side"] = f.get("side")
        c["fld_P"] = f.get("P")
        c["fld_ev"] = f.get("EV")
        c["fld_ev_long"] = f.get("ev_long")
        c["fld_ev_short"] = f.get("ev_short")
    return cards


def sort_cards(cards: list[dict], option: str) -> list[dict]:
    """Sort by a SORT_OPTIONS label. Cards missing the figure go last, in their
    original order — a missing number is never ranked as a zero."""
    field, desc = SORT_OPTIONS.get(option, SORT_OPTIONS["Market cap"])
    have = [c for c in cards if c.get(field) is not None]
    miss = [c for c in cards if c.get(field) is None]
    have.sort(key=lambda c: c[field], reverse=desc)
    return have + miss


# ──────────────────────────────────────────────────────────────────────────────
# Valuation & margin — P/E, EPS, OPM (TTM, from yfinance .info)
# ──────────────────────────────────────────────────────────────────────────────
def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def valuation_facts(info: dict | None, last: float | None = None) -> dict[str, float | None]:
    """{pe, eps, opm} from one `.info` dict. OPM is operatingMargins as a percent.

    P/E is None for a loss-maker — yfinance omits trailingPE there, and a
    negative multiple is not a valuation, so it is never derived from a negative
    EPS. When trailingPE is merely missing but EPS is positive, it is computed
    from the last close so the card does not read N/A for a data gap.
    """
    info = info or {}
    eps = _num(info.get("trailingEps"))
    pe = _num(info.get("trailingPE"))
    if pe is not None and pe <= 0:
        pe = None
    if pe is None and eps and eps > 0 and last:
        pe = last / eps
    opm = _num(info.get("operatingMargins"))
    return {"pe": pe, "eps": eps, "opm": None if opm is None else opm * 100}


def fetch_valuations(symbols: list[str], *, info_fn: Callable[[str], dict] | None = None,
                     last: dict[str, float | None] | None = None,
                     workers: int = 8) -> dict[str, dict]:
    """symbol -> valuation_facts, one `.info` call per symbol in parallel.
    A failed call yields all-None for that symbol, never an exception."""
    if info_fn is None:
        def info_fn(sym: str) -> dict:
            import yfinance as yf
            return yf.Ticker(f"{sym}.NS").info or {}
    last = last or {}

    def one(sym: str) -> tuple[str, dict]:
        try:
            info = info_fn(sym)
        except Exception:
            info = {}
        return sym, valuation_facts(info, last.get(sym))

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(symbols) or 1))) as ex:
        return dict(ex.map(one, symbols))


def median(values: list[float | None]) -> float | None:
    v = sorted(x for x in values if x is not None)
    if not v:
        return None
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


# ──────────────────────────────────────────────────────────────────────────────
# Sector context for the active card
# ──────────────────────────────────────────────────────────────────────────────
def _rank(cards: list[dict], sym: str, field: str) -> tuple[int | None, int]:
    pool = sorted((c for c in cards if c.get(field) is not None),
                  key=lambda c: c[field], reverse=True)
    for i, c in enumerate(pool, 1):
        if c["symbol"] == sym:
            return i, len(pool)
    return None, len(pool)


def _mean(vals: list[float]) -> float | None:
    vals = [v for v in vals if v is not None and not math.isnan(v)]
    return sum(vals) / len(vals) if vals else None


def sector_context(cards: list[dict], sym: str) -> dict[str, Any]:
    day = [c["chg_1d"] for c in cards if c.get("chg_1d") is not None]
    out = {
        "n": len(cards), "n_priced": len(day),
        "avg_1d": _mean(day),
        "avg_1m": _mean([c.get("ret_1m") for c in cards]),
        "avg_6m": _mean([c.get("ret_6m") for c in cards]),
        "advancers": sum(1 for v in day if v > 0),
        "decliners": sum(1 for v in day if v < 0),
    }
    for f in ("chg_1d", "ret_1m", "ret_6m"):
        out[f"rank_{f}"] = _rank(cards, sym, f)
    return out


def relative_series(frames: dict[str, Any], sym: str, members: list[str],
                    bars: int = BARS_6M) -> tuple[pd.Series | None, pd.Series | None]:
    """(symbol, equal-weight sector average) rebased to 100 over `bars` days.
    The average excludes the symbol itself, so it is 'the rest of the lobby'."""
    def _rebased(f):
        if f is None or f.empty:
            return None
        c = f["close"].astype(float).dropna().iloc[-bars:]
        return None if c.empty or c.iloc[0] <= 0 else c / c.iloc[0] * 100
    own = _rebased(frames.get(sym))
    rest = [r for s in members if s != sym and (r := _rebased(frames.get(s))) is not None]
    avg = pd.concat(rest, axis=1).mean(axis=1, skipna=True) if rest else None
    if own is not None and avg is not None:
        avg = avg.reindex(own.index).ffill()
    return own, avg


# ──────────────────────────────────────────────────────────────────────────────
# Rendering helpers (HTML strings; the page decides where they go)
# ──────────────────────────────────────────────────────────────────────────────
GOOD, RISK, MUTED = "#16a34a", "#dc2626", "#9ca3af"


def fmt_pct(v: float | None, signed: bool = True) -> str:
    if v is None:
        return NA
    return f"{v:+.2f}%" if signed else f"{v:.2f}%"


def fmt_price(v: float | None) -> str:
    return NA if v is None else f"₹{v:,.2f}"


def tone(v: float | None) -> str:
    if v is None:
        return MUTED
    return GOOD if v > 0 else RISK if v < 0 else MUTED


def sparkline_svg(values: list[float], prev: float | None,
                  w: int = 150, h: int = 34) -> str:
    """Line + soft fill, with a dotted previous-close baseline. Colour follows
    the last value against the previous close (the Google Finance convention)."""
    if len(values) < 2:
        return (f'<svg width="{w}" height="{h}"><text x="0" y="{h-10}" '
                f'font-size="10" fill="{MUTED}">{NA}</text></svg>')
    ref = prev if prev is not None else values[0]
    lo, hi = min(values + [ref]), max(values + [ref])
    span = (hi - lo) or 1.0
    def y(v): return round(h - 3 - (v - lo) / span * (h - 6), 2)
    step = w / (len(values) - 1)
    pts = " ".join(f"{round(i * step, 2)},{y(v)}" for i, v in enumerate(values))
    col = GOOD if values[-1] >= ref else RISK
    yref = y(ref)
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
        f'<polygon points="0,{h} {pts} {w},{h}" fill="{col}" fill-opacity="0.10"/>'
        f'<line x1="0" y1="{yref}" x2="{w}" y2="{yref}" stroke="#7a6858" '
        f'stroke-width="0.8" stroke-dasharray="2,3"/>'
        f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.5"/>'
        f'</svg>')


def opener_links(sym: str) -> str:
    """Two anchor-styled openers for the active peer. Being <a href> elements is
    the point: they get the browser's native right-click / middle-click /
    Ctrl-click "open in new tab" behaviour, which a Streamlit button cannot."""
    from urllib.parse import quote
    q = quote(sym, safe="")
    style = ("display:inline-block;padding:7px 14px;margin:4px 10px 4px 0;"
             "border:1px solid #e5cfae;border-radius:8px;background:#fffdf8;"
             "color:#3a2a1e;text-decoration:none;font-weight:600;font-size:14px")
    s = html.escape(sym)
    return (f'<div><a href="?nav=analyze&symbol={q}" target="_self" style="{style}" '
            f'title="Right-click to open in a new tab">Open {s} in Stock Analyzer ↗</a>'
            f'<a href="?nav=predict&symbol={q}" target="_self" style="{style}" '
            f'title="Right-click to open in a new tab">Open {s} in Predictive Analysis ↗</a>'
            f'</div>')


def _card_html(c: dict, active: bool, pos: int) -> str:
    sym = html.escape(c["symbol"])
    name = html.escape(c["name"])
    chg = c.get("chg_1d")
    col = tone(chg)
    arrow = "▲" if (chg or 0) > 0 else "▼" if (chg or 0) < 0 else "•"
    pill = (f'<span class="pill" style="color:{col};background:{col}14">'
            f'{fmt_pct(chg)} {arrow if chg is not None else ""}</span>')
    # The sparkline's baseline is the start of its own window, so its colour
    # reads the 30-day trend; the pill above it is the day move.
    spark = sparkline_svg(c.get("spark") or [], (c.get("spark") or [None])[0])
    fld = ""
    if c.get("fld_side"):
        fcol = GOOD if c["fld_side"] > 0 else RISK
        fld = (f'<div class="fld"><b style="color:{fcol}">FLD {"▲" if c["fld_side"] > 0 else "▼"}'
               f'</b> P {c["fld_P"]:.0%} · EV {c["fld_ev"]:+.1f}</div>')
    return (
        f'<div class="card{" active" if active else ""}" data-sym="{sym}" '
        f'title="{name}">'
        f'<div class="pos">{pos}</div>'
        f'<div class="sym">{sym}</div><div class="name">{name}</div>'
        f'<div class="px">{fmt_price(c.get("last"))}</div>{pill}'
        f'<div class="spark">{spark}</div>{fld}</div>')


def ribbon_html(cards: list[dict], active: str, *, pill_marker: str) -> str:
    """Self-contained document for `components.html`.

    Clicking a card clicks the matching jump-pill in the parent page (the pills
    are the real Streamlit widget; the ribbon is their face), so selection goes
    through Streamlit state rather than a page reload. Arrow keys anywhere on the
    page (outside text inputs) click Prev / Next. `pill_marker` is the id of the
    sentinel element that precedes the pill row, so the script cannot click a
    same-named button elsewhere on the page.
    """
    body = "".join(_card_html(c, c["symbol"] == active, i)
                   for i, c in enumerate(cards, 1))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
  body {{ margin:0; font-family:'Segoe UI Variable Text','Segoe UI',system-ui,sans-serif;
         background:transparent; }}
  .wrap {{ position:relative; }}
  .track {{ display:flex; gap:12px; overflow-x:auto; scroll-snap-type:x mandatory;
            scroll-behavior:smooth; padding:6px 36px 10px; scrollbar-width:thin; }}
  .card {{ flex:0 0 172px; scroll-snap-align:center; position:relative;
           background:#fffdf8; border:1px solid #f0e0cc; border-radius:12px;
           padding:10px 12px 6px; cursor:pointer; transition:transform .12s, box-shadow .12s; }}
  .card:hover {{ transform:translateY(-2px); box-shadow:0 4px 12px rgba(58,42,30,.10); }}
  .card.active {{ border:2px solid #d97706; background:#fff8e1;
                  box-shadow:0 4px 14px rgba(217,119,6,.18); }}
  .pos {{ position:absolute; top:8px; right:10px; font-size:10px; color:#9ca3af; }}
  .sym {{ font-size:11px; letter-spacing:.04em; color:#7a6858; font-weight:600; }}
  .name {{ font-size:13px; color:#3a2a1e; font-weight:600; white-space:nowrap;
           overflow:hidden; text-overflow:ellipsis; margin:2px 0 4px; }}
  .px {{ font-family:ui-monospace,'Cascadia Mono',Consolas,monospace; font-size:12px;
         color:#5c4a3a; }}
  .pill {{ display:inline-block; margin-top:4px; padding:1px 7px; border-radius:10px;
           font-size:12px; font-weight:600; font-family:ui-monospace,Consolas,monospace; }}
  .spark {{ margin-top:4px; }}
  .fld {{ font-size:10.5px; color:#7a6858; margin-top:1px; white-space:nowrap;
          font-family:ui-monospace,Consolas,monospace; }}
  .nav {{ position:absolute; top:50%; transform:translateY(-50%); z-index:2;
          width:28px; height:28px; border-radius:50%; border:1px solid #e5cfae;
          background:#fffdf8; color:#5c4a3a; cursor:pointer; font-size:14px; }}
  .nav.l {{ left:2px; }} .nav.r {{ right:2px; }}
</style></head><body><div class="wrap">
<button class="nav l" id="sl">‹</button><div class="track" id="tr">{body}</div>
<button class="nav r" id="sr">›</button></div>
<script>
(function() {{
  const tr = document.getElementById('tr');
  const act = tr.querySelector('.card.active');
  if (act) act.scrollIntoView({{inline:'center', block:'nearest', behavior:'instant'}});
  document.getElementById('sl').onclick = () => tr.scrollBy({{left:-tr.clientWidth*0.8}});
  document.getElementById('sr').onclick = () => tr.scrollBy({{left: tr.clientWidth*0.8}});
  let P; try {{ P = window.parent.document; }} catch (e) {{ return; }}
  function pillRow() {{
    const m = P.getElementById({json.dumps(pill_marker)});
    if (!m) return null;
    let el = m.closest('[data-testid="stElementContainer"]') || m.parentElement;
    for (let i = 0; i < 4 && el; i++) {{
      el = el.nextElementSibling;
      if (el && el.querySelector('button')) return el;
    }}
    return null;
  }}
  function clickByText(root, txt) {{
    if (!root) return false;
    for (const b of root.querySelectorAll('button')) {{
      if (b.innerText.trim() === txt) {{ b.click(); return true; }}
    }}
    return false;
  }}
  tr.querySelectorAll('.card').forEach(c => c.addEventListener('click', () => {{
    clickByText(pillRow(), c.dataset.sym);
  }}));
  if (!P.__slKeys) {{
    P.__slKeys = true;
    P.addEventListener('keydown', ev => {{
      const t = ev.target, tag = (t && t.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || (t && t.isContentEditable)) return;
      if (!P.getElementById({json.dumps(pill_marker)})) return;   // lobby not on screen
      const want = ev.key === 'ArrowRight' ? 'Next ›' : ev.key === 'ArrowLeft' ? '‹ Prev' : null;
      if (!want) return;
      if (clickByText(P, want)) ev.preventDefault();
    }});
  }}
}})();
</script></body></html>"""
