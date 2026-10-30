#!/usr/bin/env python3
"""
chart_server.py — Flask backend for the multi-chart live dashboard.

  REST  GET  /api/ohlcv?symbol=RELIANCE.NS&timeframe=1d&bars=200
  REST  GET  /api/symbols
  WS    ws://localhost:5001/ws   (browser subscribes via JSON messages)

Live feed routing:
  symbol ends with .NS/.BO  →  yfinance 30-second poller
  bare coin name (BTC …)   →  Hyperliquid WebSocket bridge
"""

from __future__ import annotations
import asyncio
import json
import logging
import queue
import re
import sys
import threading
import time
from collections import deque
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_sock import Sock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_source as ds
import symbol_directory as sym_dir
import reversal_calendar as rev_cal
import scanner_templates as sc
import harmonic_patterns as hp
import projection as proj

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("chart_server")

HERE = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(HERE))
sock = Sock(app)

# B-180: the Home rail's hover chart runs in the desk's page and reads candles
# from here — a cross-port fetch the browser blocks without this header. Only
# the desk's own origins, and only /api/ohlcv: nothing else on this server is
# meant to be read by another page.
ALLOWED_ORIGINS = frozenset({"http://localhost:8501", "http://localhost:8502"})


@app.after_request
def _cors_for_ohlcv(resp):
    origin = request.headers.get("Origin")
    if request.path == "/api/ohlcv" and origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.vary.add("Origin")
    return resp

# ── Client registry ───────────────────────────────────────────────────────────
# Each browser WS connection gets an outbound queue; a sender thread drains it.

_lock = threading.Lock()
_client_queues: dict[int, queue.Queue] = {}          # ws_id → Queue[str]
_client_subs:   dict[int, set[tuple]] = {}           # ws_id → {(symbol, tf)}
_sub_clients:   dict[tuple, set[int]] = {}           # (symbol, tf) → {ws_id}


def _register(ws_id: int) -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=500)
    with _lock:
        _client_queues[ws_id] = q
        _client_subs[ws_id] = set()
    return q


def _unregister(ws_id: int) -> None:
    with _lock:
        for key in _client_subs.pop(ws_id, set()):
            _sub_clients.get(key, set()).discard(ws_id)
        _client_queues.pop(ws_id, None)


def _subscribe(ws_id: int, symbol: str, timeframe: str) -> None:
    key = (symbol, timeframe)
    with _lock:
        _client_subs[ws_id].add(key)
        _sub_clients.setdefault(key, set()).add(ws_id)
    _ensure_feed(symbol, timeframe)


def _broadcast(symbol: str, timeframe: str, payload: dict) -> None:
    key = (symbol, timeframe)
    msg = json.dumps(payload)
    with _lock:
        targets = [_client_queues[i]
                   for i in list(_sub_clients.get(key, set()))
                   if i in _client_queues]
    for q in targets:
        try:
            q.put_nowait(msg)
        except queue.Full:
            pass


# ── Hyperliquid WebSocket bridge ──────────────────────────────────────────────

_hl_loop: asyncio.AbstractEventLoop | None = None
_hl_ws_ref: list = [None]      # [websockets.WebSocketClientProtocol | None]
_hl_subs: set[tuple] = set()   # (coin, interval) already subscribed at HL
_hl_lock = threading.Lock()

# ── Trade tape (the ONLY aggressor-side data this server receives) ────────────
# Hyperliquid's `trades` channel carries the taker side per print. Nothing else
# in this stack does: yfinance is OHLCV, the NSE bhavcopy is EOD, and
# intraday.db stores bars. So a real (not estimated) delta / footprint profile
# is possible for HL coins and for nothing else, and the UI must say so.
#
# The buffer starts EMPTY on every server start and fills forward from the
# moment a chart subscribes. There is no historical backfill: HL's REST info
# endpoint does not serve a deep public trade history, so a delta profile here
# covers "since this server subscribed", never the whole chart window. That is
# a real limit of the feed, not a bug, and /api/trades reports it explicitly so
# the client can label it rather than implying coverage it does not have.
_hl_trade_subs: set[str] = set()          # coins subscribed to the trades channel
_hl_trades: dict[str, deque] = {}         # coin -> deque[(ms, px, sz, is_buy)]
_hl_trades_since: dict[str, int] = {}     # coin -> ms of the first trade retained
_hl_trades_seen: dict[str, int] = {}      # coin -> total prints seen (pre-eviction)
_hl_trades_lock = threading.Lock()

#: Ring size per coin. 60k prints is ~a full session on a liquid HL perp and
#: costs a few MB; the deque evicts the oldest silently, which is why
#: `first_ts` is reported from what SURVIVES rather than from what arrived.
HL_TRADE_RING = 60_000


def _hl_start() -> None:
    global _hl_loop
    _hl_loop = asyncio.new_event_loop()
    asyncio.run_coroutine_threadsafe(_hl_maintain(), _hl_loop)
    t = threading.Thread(target=_hl_loop.run_forever, daemon=True, name="hl-loop")
    t.start()
    log.info("Hyperliquid asyncio loop started")


async def _hl_maintain() -> None:
    """Persistent Hyperliquid WS with auto-reconnect and re-subscribe."""
    import websockets
    uri = "wss://api.hyperliquid.xyz/ws"
    backoff = 2
    while True:
        try:
            async with websockets.connect(uri, ping_interval=20,
                                          ping_timeout=15) as ws:
                _hl_ws_ref[0] = ws
                backoff = 2
                log.info("HL WS connected — re-subscribing %d feeds", len(_hl_subs))
                with _hl_lock:
                    subs_snapshot = list(_hl_subs)
                    trade_snapshot = list(_hl_trade_subs)
                for coin, interval in subs_snapshot:
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {"type": "candle", "coin": coin,
                                         "interval": interval},
                    }))
                # The tape must come back on reconnect or the delta profile
                # would quietly stop growing while the candles kept updating.
                for coin in trade_snapshot:
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {"type": "trades", "coin": coin},
                    }))
                async for raw in ws:
                    _hl_on_message(raw)
        except Exception as e:
            log.warning("HL WS error: %s — reconnect in %ds", e, backoff)
        finally:
            _hl_ws_ref[0] = None
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30)


def _hl_on_message(raw: str) -> None:
    try:
        msg = json.loads(raw)
    except Exception:
        return
    channel = msg.get("channel")
    if channel == "trades":
        _hl_on_trades(msg.get("data") or [])
        return
    if channel != "candle":
        return
    d = msg.get("data", {})
    coin, interval = d.get("s", ""), d.get("i", "")
    if not coin or not interval:
        return
    _broadcast(coin, interval, {
        "type": "candle",
        "symbol": coin,
        "timeframe": interval,
        "bar": {
            "time":   int(d["t"]) // 1000,
            "open":   float(d["o"]),
            "high":   float(d["h"]),
            "low":    float(d["l"]),
            "close":  float(d["c"]),
            "volume": float(d["v"]),
        },
    })


def _hl_on_trades(rows: list) -> None:
    """Buffer a `trades` batch. HL sends side as "B" (taker bought) or "A".

    Anything unparseable is dropped rather than defaulted: a trade with an
    unknown side would land in one arm of the delta and silently bias it, which
    is worse than a slightly shorter tape.
    """
    if not isinstance(rows, list):
        return
    with _hl_trades_lock:
        for r in rows:
            try:
                coin = r["coin"]
                side = r["side"]
                if side not in ("B", "A"):
                    continue
                rec = (int(r["time"]), float(r["px"]), float(r["sz"]), side == "B")
            except (KeyError, TypeError, ValueError):
                continue
            buf = _hl_trades.get(coin)
            if buf is None:
                buf = _hl_trades[coin] = deque(maxlen=HL_TRADE_RING)
            buf.append(rec)
            _hl_trades_seen[coin] = _hl_trades_seen.get(coin, 0) + 1
            _hl_trades_since.setdefault(coin, rec[0])


def _hl_subscribe_trades(coin: str) -> None:
    """Subscribe the trades channel for `coin`, once per server lifetime.

    Separate from the candle subscription on purpose: the candle feed is keyed
    (coin, interval) and a chart switching timeframe re-subscribes, but the tape
    is per-coin and must not be torn down and restarted underneath it — that
    would punch a hole in the delta profile every time the user changed
    timeframe.
    """
    with _hl_lock:
        if coin in _hl_trade_subs:
            return
        _hl_trade_subs.add(coin)
    ws = _hl_ws_ref[0]
    if _hl_loop and ws:
        msg = json.dumps({"method": "subscribe",
                          "subscription": {"type": "trades", "coin": coin}})
        asyncio.run_coroutine_threadsafe(ws.send(msg), _hl_loop)


def _hl_subscribe(coin: str, interval: str) -> None:
    key = (coin, interval)
    with _hl_lock:
        if key in _hl_subs:
            return
        _hl_subs.add(key)
    ws = _hl_ws_ref[0]
    if _hl_loop and ws:
        msg = json.dumps({
            "method": "subscribe",
            "subscription": {"type": "candle", "coin": coin, "interval": interval},
        })
        asyncio.run_coroutine_threadsafe(ws.send(msg), _hl_loop)


# ── yfinance live poller ──────────────────────────────────────────────────────

_yf_active: set[tuple] = set()
_yf_lock = threading.Lock()
_YF_INTERVAL = 30    # seconds between polls while the market is open
_YF_INTERVAL_CLOSED = 600   # back off hard when it is not


def _market_open(symbol: str) -> bool:
    """Rough session check so we don't hammer Yahoo overnight. Deliberately
    generous at both ends (pre-open auction, closing auction settle) and
    holiday-unaware — a holiday just costs a few idle polls, whereas getting
    this too tight would silently freeze a live chart."""
    from datetime import datetime as _dt, time as _t
    from zoneinfo import ZoneInfo
    s = symbol.upper()
    try:
        if s.endswith(".NS") or s.endswith(".BO") or s.endswith(".BSE"):
            tz, open_t, close_t = ZoneInfo("Asia/Kolkata"), _t(9, 0), _t(15, 45)
        else:
            tz, open_t, close_t = ZoneInfo("America/New_York"), _t(9, 0), _t(16, 30)
        now = _dt.now(tz)
    except Exception:
        return True   # unknown venue → keep polling rather than go dark
    if now.weekday() >= 5:
        return False
    return open_t <= now.time() <= close_t


def _yf_poll(symbol: str, timeframe: str) -> None:
    key = (symbol, timeframe)
    with _lock:
        still_needed = bool(_sub_clients.get(key))
    if not still_needed:
        with _yf_lock:
            _yf_active.discard(key)
        return

    is_open = _market_open(symbol)
    try:
        if is_open:
            # bars=3 stays on data_source's cheap "1mo" daily path, and on a
            # daily timeframe the last bar is now the current session rebuilt
            # from intraday — so this genuinely moves during the session
            # instead of re-broadcasting the last completed candle forever.
            bars = ds.SOURCES["yfinance"].get_ohlcv(symbol, timeframe, bars=3)
            if bars:
                _broadcast(symbol, timeframe, {
                    "type": "candle", "symbol": symbol,
                    "timeframe": timeframe, "bar": bars[-1],
                })
    except Exception as e:
        log.debug("yf poll error %s: %s", symbol, e)

    t = threading.Timer(_YF_INTERVAL if is_open else _YF_INTERVAL_CLOSED,
                        _yf_poll, args=(symbol, timeframe))
    t.daemon = True
    t.start()


def _yf_start(symbol: str, timeframe: str) -> None:
    key = (symbol, timeframe)
    with _yf_lock:
        if key in _yf_active:
            return
        _yf_active.add(key)
    t = threading.Timer(1, _yf_poll, args=(symbol, timeframe))
    t.daemon = True
    t.start()


# ── Feed dispatcher ───────────────────────────────────────────────────────────

_HL_TF = ds.HyperliquidSource._TF


def _ensure_feed(symbol: str, timeframe: str) -> None:
    # Same rule as /api/ohlcv: a live feed on the wrong interval is worse than
    # no feed, because the ticks look right and land on the wrong series.
    try:
        timeframe = ds.validate_timeframe(timeframe)
    except ds.UnknownTimeframe as e:
        log.warning("refusing feed subscription: %s", e)
        return
    source = ds.detect_source(symbol)
    if source.name == "hyperliquid":
        hl_interval = _HL_TF[timeframe]
        _hl_subscribe(symbol, hl_interval)
        _hl_subscribe_trades(symbol)
    else:
        _yf_start(symbol, timeframe)


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(HERE, "chart_dashboard.html")


# ── PWA (installable mobile app) — manifest, service worker, icons ────────────
@app.route("/manifest.webmanifest")
def pwa_manifest():
    return send_from_directory(HERE, "manifest.webmanifest",
                               mimetype="application/manifest+json")


@app.route("/sw.js")
def pwa_service_worker():
    # Served from the root scope so it can control the whole app. No-cache so a
    # new SW is picked up on the next visit rather than being pinned by the browser.
    resp = send_from_directory(HERE, "sw.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/icon-192.png")
def pwa_icon_192():
    return send_from_directory(HERE, "icon-192.png", mimetype="image/png")


@app.route("/icon-512.png")
def pwa_icon_512():
    return send_from_directory(HERE, "icon-512.png", mimetype="image/png")


@app.route("/icon-maskable-512.png")
def pwa_icon_maskable():
    return send_from_directory(HERE, "icon-maskable-512.png", mimetype="image/png")


@app.route("/api/indicator_evidence")
def indicator_evidence_api():
    """B-154: key → {verdict, label, line, items} for every INDICATOR_DEFS key, from
    indicator_evidence (which reads named_studies). Small and static per process."""
    import indicator_evidence as ie
    html = (HERE / "chart_dashboard.html").read_text(encoding="utf-8", errors="replace")
    body = html.split("const INDICATOR_DEFS = [", 1)[-1].split("\n];", 1)[0]
    keys = re.findall(r"key:'([a-z0-9_]+)'", body)
    return jsonify(ie.evidence(keys))


#: B-157 "Learn more": the indicator's wiki concept page, rendered read-only. The
#: key → page map is the catalogue's own `concept` field, so only the ~44 pages
#: an indicator names are reachable — not the wiki, not a path the caller picks.
WIKI_DIR = HERE.parent / "trading-wiki" / "wiki"
_LEARN_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>
:root{{--bg:#fffdf8;--fg:#2b2118;--mut:#6b5b4b;--line:#e5cfae;--acc:#a14a0b}}
@media (prefers-color-scheme:dark){{:root{{--bg:#131722;--fg:#e6edf3;--mut:#8b949e;--line:#30363d;--acc:#58a6ff}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 'Segoe UI Variable Text','Segoe UI',system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:24px 16px 48px}} a{{color:var(--acc)}}
.note{{font-size:12px;color:var(--mut);border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:16px}}
table{{border-collapse:collapse;display:block;overflow-x:auto}} th,td{{border:1px solid var(--line);padding:4px 8px;vertical-align:top}}
code{{font-family:ui-monospace,Consolas,monospace;font-size:.9em}} h1{{font-size:24px}} h2{{font-size:19px;margin-top:28px}}
</style></head><body><main><div class="note">From the desk's wiki: <code>{path}</code> · read-only.
Wiki links are shown as plain text.</div>{body}</main></body></html>"""


def _concept_for(key: str) -> str | None:
    js = (HERE / "indicator_catalogue.js").read_text(encoding="utf-8", errors="replace")
    info = json.loads(js.split("/*JSON-BEGIN*/", 1)[1].split("/*JSON-END*/", 1)[0])
    c = (info.get(key) or {}).get("concept")
    return c if c and re.fullmatch(r"concepts/[A-Za-z0-9_.-]+\.md", c) else None


@app.route("/learn/<key>")
def learn_more(key: str):
    from html import escape
    from markdown_it import MarkdownIt
    if not re.fullmatch(r"[a-z0-9_]+", key):
        abort(404)
    rel = _concept_for(key)
    page = (WIKI_DIR / rel) if rel else None
    if page is None or not page.is_file():
        abort(404)
    text = page.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---"):
        text = text.split("---", 2)[-1]                     # drop the frontmatter
    text = re.sub(r"\[\[([^\]|]+)\|?([^\]]*)\]\]", lambda m: m.group(2) or m.group(1).split("/")[-1], text)
    # html=False: anything that looks like markup in a wiki page is shown, not run.
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(text)
    m = re.search(r"<h1>(.*?)</h1>", body)
    title = re.sub(r"<[^>]+>", "", m.group(1)) if m else rel
    return _LEARN_PAGE.format(title=escape(title), path=escape(rel), body=body)


#: B-151 indicator preview pictures, written by gen_indicator_thumbs.py. Only the
#: manifest and hash-named webp files are reachable — the name pattern is the
#: gate, as `_page_modules` is for scripts. The pictures never change under one
#: name (a redraw gets a new hash), so they cache forever; the manifest, which
#: says which hash is current, must not.
THUMBS_DIR = HERE / "ind-thumbs"
_THUMB_NAME = re.compile(r"[a-z0-9_]+\.[0-9a-f]{10}\.webp")


@app.route("/ind-thumbs/<name>")
def indicator_thumb(name: str):
    if name == "manifest.json":
        resp = send_from_directory(THUMBS_DIR, name, mimetype="application/json")
        resp.headers["Cache-Control"] = "no-cache"
        return resp
    if not _THUMB_NAME.fullmatch(name):
        abort(404)
    resp = send_from_directory(THUMBS_DIR, name, mimetype="image/webp")
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


# Bhavcopy is one file per session and every strike-level read comes out of it,
# so the download is cached process-wide rather than repeated per request. Keyed
# by nothing but recency: a new session simply replaces it.
_OPT_CACHE: dict[str, object] = {"raw": None, "date": None, "at": 0.0}
_OPT_TTL = 30 * 60


#: Browser modules are served by ONE route, and the ALLOW-LIST is read from the
#: page itself (B-85).
#:
#: Before this there were 17 near-identical routes, one per module, and the cost
#: was not the duplication -- it was that a running server 404s a module added
#: after it started. That was observed live on 2026-09-07 (`/psar.js`) and the
#: backlog carried "restart the chart server" as an operational note on two
#: separate sessions. A restart is not a fix for a routing table that has to be
#: edited to learn about a file already on disk.
#:
#: A blanket `/<anything>.js` would have been the obvious move and is WRONG here:
#: `tools/` also holds nine NODE-side scripts -- `alert_watcher.js`,
#: `svp_backtest_runner.js`, the emit and backtest runners -- and serving those
#: over HTTP would publish internal tooling, including the shape of the alert
#: delivery config. The browser needs exactly what `chart_dashboard.html` asks
#: for, so the page is the authority and nothing else is reachable.
#:
#: Cached on the HTML's mtime, so adding a module and its `<script src>` line
#: works on a RUNNING server, which is the whole point of the change.
_MODULE_CACHE: dict[str, object] = {"mtime": None, "names": frozenset()}


def _page_modules() -> frozenset:
    """`{"elliott_wave.js", ...}` — every module `chart_dashboard.html` loads."""
    page = HERE / "chart_dashboard.html"
    try:
        mtime = page.stat().st_mtime
    except OSError:
        return frozenset()
    if _MODULE_CACHE["mtime"] != mtime:
        try:
            html = page.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return frozenset()
        _MODULE_CACHE["names"] = frozenset(
            re.findall(r'src="/([A-Za-z0-9_]+\.js)"', html))
        _MODULE_CACHE["mtime"] = mtime
    return _MODULE_CACHE["names"]


@app.route("/<name>.js")
def chart_module_js(name: str):
    """Serve a chart module the page actually references, or 404.

    Flask's string converter never matches a `/`, and membership in the page's own
    list is the real gate, so neither traversal nor a guessed filename reaches
    disk. The explicit `/sw.js` route above wins over this one: a static rule
    outranks a converter rule in Flask's map.
    """
    fname = f"{name}.js"
    if fname not in _page_modules():
        abort(404)
    return send_from_directory(HERE, fname, mimetype="application/javascript")


@app.route("/api/option_levels")
def api_option_levels():
    """Strike-level option OI — max pain and OI walls (B-23).

    See option_chain.py. LEVELS WITH CONTEXT, NOT A SIGNAL: "price gravitates to
    max pain" and "a wall rejects the first touch" are both untested, and the
    payload carries `unmeasured: true` so a consumer cannot forget it.

    Query: symbol (required), expiry (YYYY-MM-DD or "all"), walls (default 3).
    {"levels": null} when the underlying has no options in the latest bhavcopy —
    the common case for a non-F&O stock, not an error.
    """
    symbol = request.args.get("symbol", "").strip().upper()
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    expiry = request.args.get("expiry") or None
    walls = max(1, min(int(request.args.get("walls", 3)), 10))

    # The chart sends NSE-suffixed tickers; the bhavcopy keys on the bare symbol.
    base = symbol.split(":")[-1]
    for suffix in (".NS", ".NSE", ".BO"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break

    try:
        import option_chain as ochain
        now = time.time()
        if _OPT_CACHE["raw"] is None or (now - float(_OPT_CACHE["at"] or 0)) > _OPT_TTL:
            import nse_oi_momentum as oi_mod
            raw, td = oi_mod.fetch_fo_bhavcopy_raw()
            _OPT_CACHE.update({"raw": raw, "date": td, "at": now})
        raw, td = _OPT_CACHE["raw"], _OPT_CACHE["date"]
        if raw is None or getattr(raw, "empty", True):
            return jsonify({"symbol": symbol, "levels": None,
                            "note": "no F&O bhavcopy reachable"})
        levels = ochain.read_levels(base, expiry=expiry, walls=walls,
                                    raw=raw, trade_date=td)
    except Exception as e:                      # a data outage must not 500 the chart
        log.warning("option_levels failed for %s: %s", symbol, e)
        return jsonify({"symbol": symbol, "levels": None, "note": str(e)})

    return jsonify({"symbol": symbol, "levels": levels})


@app.route("/api/ohlcv")
def api_ohlcv():
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars      = min(int(request.args.get("bars", 300)), 3000)  # 3000 covers 10Y+ daily
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    # Reject an unservable timeframe instead of quietly serving daily under its
    # name — `?timeframe=1wk` used to return daily bars labelled "1wk".
    try:
        timeframe = ds.validate_timeframe(timeframe)
    except ds.UnknownTimeframe as e:
        return jsonify({"error": str(e), "timeframes": list(ds.TIMEFRAMES)}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    requested = symbol          # remember it so a swap below can be reported
    source = ds.detect_source(symbol)
    data   = source.get_ohlcv(symbol, timeframe, bars)
    # Fallback chain when the primary fetch returns empty. Handles three cases:
    #   • BSE-only bare tickers (DOLPHMED, ADON, MARINE) not in the NSE-first
    #     directory → try .BO / .NS
    #   • Company-name inputs from BSE feeds ("GALLANTT ISPAT LTD.BO" or the
    #     raw multi-word name) → strip suffix, take the first token, search
    #     the symbol directory, try .NS / .BO
    #   • Anything else that returned empty → cross-exchange retry (BSE ↔ NSE)
    # Sparse-history guard: Yahoo returns a 1–3 bar stub for many BSE tickers
    # (e.g. GRAPHITE.BO) even when the NSE variant has full history. Treat any
    # tiny result on a multi-year request as "empty" and run the same fallback.
    _sparse = data is not None and 0 < len(data) < 5 and bars >= 20
    if (not data or _sparse) and not symbol.startswith("^"):
        yf_source = ds.SOURCES["yfinance"]
        # Strip any trailing suffix so we can re-derive the ticker from the
        # base name (fixes the case where URL handler appended '.BO' to a
        # company name like "GALLANTT ISPAT LTD.BO").
        import re
        bare = re.sub(r"\.(NS|BO|BSE)$", "", symbol, flags=re.IGNORECASE)
        first_token = bare.split()[0] if " " in bare else bare
        candidates: list[str] = []
        # Search the FULL name before the first token. Searching only the first
        # token silently answers about a different company: "BCC FUBA INDIA LTD"
        # reduced to "BCC", whose top directory hit is BCCL.BO (Bhatia Colour
        # Chem) — a chart for the wrong business, rendered without complaint.
        # The full string matches BCCFUBA.BO exactly; the first token stays as a
        # second pass so partial/misspelled input still resolves.
        try:
            queries = [bare] if bare == first_token else [bare, first_token]
            for q in queries:
                for h in sym_dir.search(q, limit=5):
                    if h["symbol"] not in candidates:
                        candidates.append(h["symbol"])
        except Exception:
            pass
        # Generic cross-exchange suffixes as a last resort.
        candidates.extend([f"{first_token}.NS", f"{first_token}.BO"])
        seen = {symbol}
        for cand in candidates:
            if cand in seen:
                continue
            seen.add(cand)
            try:
                cand_data = yf_source.get_ohlcv(cand, timeframe, bars)
            except Exception:
                cand_data = None
            # Prefer a candidate only if it clearly beats the sparse original —
            # otherwise a same-sparse candidate would replace the real ticker.
            if cand_data and len(cand_data) >= max(5, len(data or [])):
                symbol, source, data = cand, yf_source, cand_data
                break
    # Previous *daily* close, independent of the requested timeframe — this
    # is the benchmark Google Finance / exchanges use for "today's change".
    # One extra call per pane-load (not per WS tick), so the cost is cheap.
    try:
        prev_close = source.get_previous_close(symbol)
    except Exception as e:
        log.warning("get_previous_close failed for %s: %s", symbol, e)
        prev_close = None
    # A cross-exchange swap is a legitimate rescue (Yahoo's BSE feed is often a
    # 1-3 bar stub while the NSE line has full history), but doing it silently
    # means you can ask for .BO, get .NS, and never be told — the chart just
    # quietly answers a different question. Report it so the client can say so.
    resp = {"symbol": symbol, "timeframe": timeframe, "bars": data,
            "prev_close": prev_close, "source": source.name}
    if symbol != requested:
        resp["requested_symbol"] = requested
        resp["exchange_fallback"] = (
            f"{requested} had no usable history on this feed — showing {symbol}")
    return jsonify(resp)


def _bars_to_df(bars: list[dict]):
    """Convert an /api/ohlcv-shaped bars list into a DataFrame with a
    DatetimeIndex, which is what scanner_templates functions expect.
    Kept here rather than in each endpoint so future pattern endpoints
    (auto-trendlines, structural resistance, fib swing) share the shape."""
    import pandas as pd
    if not bars:
        return None
    df = pd.DataFrame(bars)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time")
    return df


@app.route("/api/rounding_bottom")
def api_rounding_bottom():
    """Rounding Bottom / saucer geometry for chart overlay rendering. Runs
    the same detector as the Scanner Hub's "Rounding Bottom" card (see
    scanner_templates.scan_rounding_bottom + concepts/Rounding-Bottom.md),
    but returns bar timestamps and geometry instead of a card. When no
    qualifying saucer is present the endpoint returns {"saucer": null} —
    the client hides the overlay in that case."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < 60:
        return jsonify({"symbol": symbol, "saucer": None})

    hit = sc.scan_rounding_bottom(df)
    if not hit or "geometry" not in hit:
        return jsonify({"symbol": symbol, "saucer": None})

    g = hit["geometry"]
    # Map bar indices to unix timestamps using the bars list the client
    # already has — keeps the detector implementation index-based (simpler
    # to test) while the wire format uses timestamps (what LWC needs).
    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    saucer = {
        "rim": g["rim"],
        "trough_time":       _t(g["trough_bar_idx"]),
        "trough_price":      g["trough_price"],
        "base_start_time":   _t(g["base_start_bar_idx"]),
        "last_time":         int(bars[-1]["time"]),
        "breakout_time":     _t(g["breakout_bar_idx"]),
        "state":             g["state"],
        "family":            g["family"],
        "decline_pct":       g["decline_pct"],
        "symmetry_pct":      g["symmetry_pct"],
        "trough_days":       g["trough_days"],
        "ema_turn":          g["ema_turn"],
        "vol_confirmed":     g["vol_confirmed"],
        "score":             g["score"],
        "reasons":           hit.get("reasons", []),
        # Actionable trade plan — see scan_rounding_bottom for the derivation.
        "verdict":           g["verdict"],
        "entry":             g["entry"],
        "stop":              g["stop"],
        "target":            g["target"],
        "risk_reward":       g["risk_reward"],
    }
    return jsonify({"symbol": symbol, "saucer": saucer})


@app.route("/api/double_bottom")
def api_double_bottom():
    """Double Bottom geometry for chart overlay rendering. Runs the same
    detector as the Scanner Hub's "Double Bottom" card (see
    scanner_templates.scan_double_bottom + concepts/Reversal-Chart-Patterns.md,
    ported from sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine.md).
    Returns {"double_bottom": null} when no confirmed pattern is live — the
    client hides the overlay in that case.

    Two numbers ride out separately and must stay that way on the wire as well
    as in the detector: `quality`/`grade` describe the SHAPE, `follow_through`
    describes whether this symbol has been honouring these breaks. The source
    page's warning is that a textbook A-grade shape can sit on a poor real
    follow-through rate, so the client renders both rather than one blended
    number."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    # The detector needs enough bars for two CONFIRMED pivots (8 each side)
    # plus the pattern width plus the break; below that it returns None anyway.
    if df is None or len(df) < 90:
        return jsonify({"symbol": symbol, "double_bottom": None})

    hit = sc.scan_double_bottom(df)
    if not hit or "geometry" not in hit:
        return jsonify({"symbol": symbol, "double_bottom": None})

    g = hit["geometry"]

    # Bar indices -> unix timestamps, same convention as /api/rounding_bottom:
    # the detector stays index-based (simpler to test) and the wire format uses
    # timestamps (what LightweightCharts needs).
    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    dbl = {
        "neckline":        g["neckline"],
        "left_time":       _t(g["left_bar_idx"]),
        "left_low":        g["left_low"],
        "right_time":      _t(g["right_bar_idx"]),
        "right_low":       g["right_low"],
        "neck_time":       _t(g["neck_bar_idx"]),
        "breakout_time":   _t(g["breakout_bar_idx"]),
        "last_time":       int(bars[-1]["time"]),
        "state":           g["state"],
        "quality":         g["quality"],
        "grade":           g["grade"],
        "parts":           g["parts"],
        "eq_pct":          g["eq_pct"],
        "pullback_pct":    g["pullback_pct"],
        "width_bars":      g["width_bars"],
        "atrs_past":       g["atrs_past"],
        "breakout_vol_x":  g["breakout_vol_x"],
        "extended_pct":    g["extended_pct"],
        "bars_since_break": g["bars_since_break"],
        # Descriptive history for THIS symbol, always with its sample size.
        "follow_through":  g["follow_through"],
        "score":           hit["score"],
        "reasons":         hit.get("reasons", []),
        # Actionable trade plan — see detect_double_bottom for the derivation.
        "verdict":         g["verdict"],
        "entry":           g["entry"],
        "stop":            g["stop"],
        "target":          g["target"],
        "risk_reward":     g["risk_reward"],
    }
    return jsonify({"symbol": symbol, "double_bottom": dbl})


@app.route("/api/vcp")
def api_vcp():
    """VCP (Volatility Contraction Pattern) coiling geometry for chart
    overlay use. See scanner_templates.detect_vcp_geometry + concepts/VCP.md.
    Returns per-contraction bar timestamps + prices + a Minervini-style
    trade plan (BUY/WEAK BUY/READY/WATCH with entry/stop/target/RR)."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < 110:
        return jsonify({"symbol": symbol, "vcp": None})

    g = sc.detect_vcp_geometry(df)
    if g is None:
        return jsonify({"symbol": symbol, "vcp": None})

    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    # Convert every bar_idx to a unix timestamp so the client can render
    # without knowing the raw DataFrame index. Same convention as /api/
    # rounding_bottom — keeps the detector implementation index-based.
    contractions_wire = []
    for cc in g["contractions"]:
        contractions_wire.append({
            "high_time":  _t(cc["high_bar_idx"]),
            "high_price": cc["high_price"],
            "low_time":   _t(cc["low_bar_idx"]),
            "low_price":  cc["low_price"],
            "depth_pct":  cc["depth_pct"],
            "in_progress": cc["in_progress"],
        })

    vcp = {
        "pivot":             g["pivot"],
        "base_low":          g["base_low"],
        "base_start_time":   _t(g["base_start_bar_idx"]),
        "base_end_time":     int(bars[-1]["time"]),
        "contractions":      contractions_wire,
        "footprint":         g["footprint"],
        "base_weeks":        g["base_weeks"],
        "n_contractions":    g["n_contractions"],
        "vol_drying":        g["vol_drying"],
        "vol_confirmed":     g["vol_confirmed"],
        "vol_expansion":     g["vol_expansion"],
        "dist_to_pivot_pct": g["dist_to_pivot_pct"],
        "verdict":           g["verdict"],
        "entry":             g["entry"],
        "stop":              g["stop"],
        "target":            g["target"],
        "risk_reward":       g["risk_reward"],
    }
    return jsonify({"symbol": symbol, "vcp": vcp})


@app.route("/api/falling_wedge")
def api_falling_wedge():
    """Falling-wedge geometry for chart overlay (FW-3). See
    scanner_templates.detect_falling_wedge_geometry + concepts/Falling-Wedge.md.
    Returns the two converging trendline endpoints (times + prices), the breakout
    state, confidence and the metric surface, or {"falling_wedge": null}."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < 60:
        return jsonify({"symbol": symbol, "falling_wedge": None})

    g = sc.detect_falling_wedge_geometry(df)
    if g is None:
        return jsonify({"symbol": symbol, "falling_wedge": None})

    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    fw = {
        "upper": {"t0": _t(g["upper_x0"]), "y0": g["upper_y0"],
                  "t1": _t(g["upper_x1"]), "y1": g["upper_y1"]},
        "lower": {"t0": _t(g["lower_x0"]), "y0": g["lower_y0"],
                  "t1": _t(g["lower_x1"]), "y1": g["lower_y1"]},
        "breakout_time":   _t(g["breakout_bar"]),
        "last_close":      g["last_close"],
        "state":           g["state"],
        "state_label":     g["state_label"],
        "confidence":      round(g["confidence"], 1),
        "containment_pct": round(g["containment"] * 100, 1),
        "convergence_pct": round(g["conv_ratio"] * 100, 1),
        "touches_h":       g["touches_h"],
        "touches_l":       g["touches_l"],
        "vol_dry":         g["vol_dry"],
        "vol_trend":       round(g["vol_trend"], 2),
        "entry":           g["entry"],
        "stop":            g["stop"],
        "target":          g["target"],
        "rr":              round(g["rr"], 2),
    }
    return jsonify({"symbol": symbol, "falling_wedge": fw})


@app.route("/api/flag_pole")
def api_flag_pole():
    """Flag & pole geometry for the chart overlay (B-92 / PR-4).

    See `flag_pole.detect_flag_pole` and
    `analyses/Pattern-Reporting-Enhancement-Roadmap`. Returns BOTH directions so
    the overlay can draw whichever exists without a second round trip — they are
    mutually exclusive in practice but nothing guarantees it, and asking the
    client to choose would put the detector's logic in two places.

    Bar indices are mapped to chart timestamps here, as every other overlay route
    does. {"bull": null, "bear": null} when nothing qualifies.
    """
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)

    import flag_pole as fpm
    need = fpm.WINDOW + fpm.ATR_N
    if df is None or len(df) < need:
        # Say WHY rather than returning a bare null: an overlay that silently
        # draws nothing on a short frame is indistinguishable from one that
        # found no pattern, and the two need different reactions from the user.
        return jsonify({"symbol": symbol, "bull": None, "bear": None,
                        "note": f"needs {need} bars, has {0 if df is None else len(df)}"})

    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    out = {"symbol": symbol, "bull": None, "bear": None}
    for d in ("bull", "bear"):
        g = fpm.detect_flag_pole(df, direction=d)
        if g is None:
            continue
        out[d] = {
            **{k: g[k] for k in (
                "direction", "pole_low", "pole_high", "pole_bars", "pole_atr",
                "pole_monotonicity", "flag_bars", "flag_high", "flag_low",
                "retrace", "vol_contract", "broken", "entry", "stop",
                "target", "rr", "atr")},
            "pole_t0": _t(g["pole_start"]), "pole_t1": _t(g["pole_end"]),
            "flag_t0": _t(g["flag_start"]), "flag_t1": _t(g["flag_end"]),
            "last_t":  _t(len(df) - 1),
        }
    return jsonify(out)


@app.route("/api/structure_chain")
def api_structure_chain():
    """Market-structure break chain for the chart overlay — SBC-4. See
    scanner_templates.detect_structure_chain (port of Structure Break Chain [SBC],
    © SharpStrat, MPL 2.0) + concepts/Market-Structure-CHOCH-BOS.md.

    Returns every BOS/CHOCH event with its ATR-normalised quality grade, chain
    position and failed flag, the recent swing levels, and the run statistics —
    all bar indices mapped to chart timestamps. {"structure_chain": null} when no
    structural break exists in the window."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    # A pivot is pivot_len bars on each side, so intraday needs a tighter window
    # or the whole session gets swallowed by one swing (same shape as /api/trendlines).
    piv_default = {
        "1m": 5, "5m": 6, "15m": 8, "30m": 10,
        "1h": 10, "4h": 12, "6h": 13, "1d": 15, "1w": 15,
    }.get(timeframe, 15)
    pivot_len  = max(2, min(int(request.args.get("pivot_len", piv_default)), 100))
    confirm    = request.args.get("confirm", "close")
    fail_win   = max(0, min(int(request.args.get("fail_win", 3)), 100))
    max_swings = max(0, min(int(request.args.get("max_swings", 15)), 60))
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < pivot_len * 2 + 20:
        return jsonify({"symbol": symbol, "structure_chain": None})

    r = sc.detect_structure_chain(df, pivot_len=pivot_len, confirm=confirm,
                                  fail_win=fail_win, max_swings=max_swings)
    if r is None:
        return jsonify({"symbol": symbol, "structure_chain": None})

    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    last_t = _t(len(bars) - 1)
    events = []
    for e in r["events"]:
        t = _t(e["bar"])
        if t is None:
            continue
        events.append({
            "time":        t,
            "pivot_time":  _t(e["pivot_bar"]),
            "failed_time": _t(e["failed_bar"]),
            "type":        e["type"],
            "direction":   e["direction"],
            "level":       e["level"],
            "quality":     e["quality"],
            "score":       e["score"],
            "chain":       e["chain"],
            "failed":      e["failed"],
        })
    # B-42 · the shared structure read, reusing the walk above rather than
    # repeating it. Adds the HH/HL/LH/LL sequence, the state it implies, the
    # premium/discount location, and whether the sequence and the breaks agree.
    ms = sc.read_market_structure(df, pivot_len=pivot_len, confirm=confirm,
                                  fail_win=fail_win, max_swings=max_swings,
                                  chain=r)

    # Each swing is drawn from its pivot bar to the right edge, as in the source.
    # Labels come from the same read, matched by bar so the chart and the state
    # cannot drift apart.
    labels = {s["bar"]: s.get("label") for s in (ms or {}).get("swings", [])}
    swings = [{"t0": _t(s["bar"]), "t1": last_t, "level": s["level"],
               "kind": s["kind"], "label": labels.get(s["bar"])}
              for s in r["swings"] if _t(s["bar"]) is not None]

    return jsonify({"symbol": symbol, "structure_chain": {
        "events": events,
        "swings": swings,
        "live_swing_high": r["live_swing_high"],
        "live_swing_low": r["live_swing_low"],
        "stats": r["stats"],
        "structure": ({
            "state":      ms["state"],
            "agreement":  ms["agreement"],
            "sequence":   ms["sequence"],
            "zone":       ms["zone"],
            "zone_pct":   ms["zone_pct"],
            "swing_high": ms["swing_high"],
            "swing_low":  ms["swing_low"],
            "invariant_ok": ms["invariant_ok"],
        } if ms else None),
    }})


@app.route("/api/order_blocks")
def api_order_blocks():
    """SMC order blocks (bullish demand + bearish supply) for the chart overlay.
    See scanner_templates.detect_order_blocks (multi-zone sibling of
    scan_order_block) + concepts/Order-Blocks.

    Each block carries its zone (low/high), BOS/CHOCH label, ATR displacement,
    break-bar volume multiple, and mitigation state — bar indices mapped to
    timestamps, with the box spanning the OB candle to its mitigation bar (or the
    right edge while still unmitigated), plus an entry/stop/target trade plan on
    every live zone — measured at ~0R, see detect_order_blocks.
    {"order_blocks": []} when none exist."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    # Order blocks are more LOCAL than major structure swings, so a tighter pivot
    # than /api/structure_chain — otherwise a daily chart surfaces almost none.
    # Daily/weekly use 5 = scan_order_block's pivot (B-171, owner 2026-10-17), so
    # the chart draws the zones the scanner reads.
    piv_default = {
        "1m": 3, "5m": 4, "15m": 5, "30m": 5,
        "1h": 6, "4h": 6, "6h": 6, "1d": 5, "1w": 5,
    }.get(timeframe, 5)
    pivot_len = max(2, min(int(request.args.get("pivot_len", piv_default)), 100))
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < pivot_len * 4 + 20:
        return jsonify({"symbol": symbol, "order_blocks": []})

    blocks, retests = sc.detect_order_blocks(df, pivot_len=pivot_len)

    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    last_t = _t(len(bars) - 1)
    out = []
    for b in blocks:
        t0 = _t(b["ob_idx"])
        if t0 is None:
            continue
        # Violated zones end where price closed through; fresh/mitigated run to
        # the right edge (still-relevant levels).
        end_idx = b["vio_idx"] if b["state"] == "violated" else None
        out.append({
            "dir":        b["dir"],
            "signal":     b["signal"],
            "state":      b["state"],          # fresh | mitigated | violated
            "low":        round(b["low"], 2),
            "high":       round(b["high"], 2),
            "start_time": t0,
            "break_time": _t(b["break_idx"]),
            "end_time":   _t(end_idx) if end_idx is not None else last_t,
            "disp_atr":   b["disp_atr"],
            "vol_x":      b["vol_x"],
            "buy_pct":    b.get("buy_pct", 50.0),
            "sell_pct":   b.get("sell_pct", 50.0),
            # Trade plan — present on every live zone (see detect_order_blocks).
            # The overlay draws stop/target lines from these. No `rr`: the target
            # is a flat 2R since 2026-09-13, so a ratio would be a constant
            # dressed up as information.
            "entry":      b.get("entry"),
            "stop":       b.get("stop"),
            "target":     b.get("target"),
        })

    retest_out = []
    for rt in retests:
        t = _t(rt["idx"])
        if t is None:
            continue
        retest_out.append({
            "dir":   rt["dir"],
            # early = wick rejection at the zone; confirmed = price left the zone.
            "kind":  rt.get("kind", "confirmed"),
            "ob_idx": rt.get("ob_idx"),
            "time":  t,
            "price": round(rt["price"], 2),
            "buy_pct":  rt.get("buy_pct"),
            "sell_pct": rt.get("sell_pct"),
        })

    return jsonify({"symbol": symbol, "order_blocks": out, "retests": retest_out})


@app.route("/api/bull_trap")
def api_bull_trap():
    """Bull traps (B-182) for the `bulltrap` chart overlay.

    Calls the SAME `scanner_templates.bull_trap_events` the `Bull Trap` risk
    scanner and `bull_trap_study.py` use, so the chart, the scanner and the
    measurement cannot disagree. Every failed breakout in the window comes back,
    graded: `full` (weak volume AND RSI divergence) is a bull trap; the rest are
    plain failed breakouts, drawn as context. `fired` is the scanner's own
    freshness gate (trap within 3 bars, level not reclaimed).

    {"events": [...], "fired": bool}. Bar indices are mapped to timestamps.
    """
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < sc.BT_RES_LOOKBACK + 20:
        return jsonify({"symbol": symbol, "events": [], "fired": False})

    def _t(idx):
        return int(bars[idx]["time"]) if idx is not None and 0 <= idx < len(bars) else None

    events = []
    for e in sc.bull_trap_events(df):
        events.append({
            "level": e["level"], "peak_high": e["peak_high"],
            "res_time": _t(e["res_bar"]), "breakout_time": _t(e["breakout_bar"]),
            "trap_time": _t(e["trap_bar"]), "peak_time": _t(e["peak_bar"]),
            "vol_x": e["vol_x"], "div_pts": e["div_pts"],
            "rsi_old": e["rsi_old"], "rsi_new": e["rsi_new"],
            "weak_vol": e["weak_vol"], "divergence": e["divergence"], "full": e["full"],
        })
    try:
        fired = sc.scan_bull_trap(df) is not None
    except Exception:
        fired = False
    return jsonify({"symbol": symbol, "events": events, "fired": fired})


#: B-186: the tour's measured base rates, written by tour_base_rates.py. Re-read
#: when its mtime changes, so a refresh needs no server restart.
TOUR_RATES_PATH = HERE / "cache" / "tour_base_rates.json"
_tour_rates_cache: dict = {"mtime": None, "path": None, "data": None}


def _tour_rates() -> dict | None:
    p = Path(TOUR_RATES_PATH)
    try:
        mt = p.stat().st_mtime
    except OSError:
        return None
    if _tour_rates_cache["path"] == str(p) and _tour_rates_cache["mtime"] == mt:
        return _tour_rates_cache["data"]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        data = data if isinstance(data, dict) else None
    except (OSError, ValueError):
        data = None                       # a corrupt file reads as "not measured"
    _tour_rates_cache.update(mtime=mt, path=str(p), data=data)
    return data


def _jsonable(o):
    """numpy scalars inside finding facts -> plain Python for jsonify."""
    import numpy as np
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    if isinstance(o, np.bool_):
        return bool(o)
    return o


@app.route("/api/tour")
def api_tour():
    """"Tour this chart" (B-186): Now, Stock-or-market?, then up to eight
    findings, each with chart actions, a Watch line and its measured base-rate
    badge. Daily only — the base rates are measured on daily bars. All logic is
    in chart_tour.build_tour; this route only gathers bars and the rates file."""
    import pandas as pd
    import chart_tour as ct
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    if timeframe != "1d":
        return jsonify({"symbol": symbol, "asOf": None, "steps": [], "base_rates_asOf": None,
                        "notes": ["The tour is daily-only: its base rates are measured on daily bars."]})
    symbol = sym_dir.resolve_symbol(symbol)

    def _daily(sym: str):
        try:
            return _bars_to_df(ds.detect_source(sym).get_ohlcv(sym, "1d", 400))
        except Exception:
            return None

    df = _daily(symbol)
    if df is None or df.empty:
        return jsonify({"symbol": symbol, "asOf": None, "steps": [], "base_rates_asOf": None,
                        "notes": ["No daily price history for this symbol."]})
    market_df = _daily("^NSEI")
    sector_df = sector_label = sector_symbol = None
    try:
        import pa_chart_focus as pcf
        sector = pcf.stock_sector(symbol.split(".")[0])
        tkr, label, is_sector = pcf.context_for(sector)
        if is_sector:
            sector_df, sector_label, sector_symbol = _daily(tkr), label, tkr
    except Exception:
        pass
    rates = _tour_rates()
    tour = ct.build_tour(df, market_df=market_df, sector_df=sector_df, sector_label=sector_label,
                         base_rates=rates, today=pd.Timestamp.today(), sector_symbol=sector_symbol)
    return jsonify(_jsonable({"symbol": symbol, "asOf": tour["asOf"], "steps": tour["steps"],
                              "base_rates_asOf": (rates or {}).get("asOf"), "notes": tour["notes"]}))


@app.route("/api/liquidity")
def api_liquidity():
    """Liquidity pools (equal highs/lows) + the most recent sweep-and-reclaim.

    Backs the `liquidity` chart overlay. Calls the SAME
    `scanner_templates.detect_liquidity_pools` / `detect_liquidity_sweep` that
    `scan_liquidity_sweep` fires on, so the zones drawn here and the scanner's
    hits cannot disagree - the drift B-24 was raised over. Nothing is recomputed
    in JS.

    Why this overlay exists at all: B-41m measured `Liquidity Sweep` at +0.51%
    @20d (p=0.005) net of costs, the only scanner on this desk whose edge survives
    them, and until now it was the one SMC component with a measured edge and no
    way to see it on a chart.

    {"pools": [...], "sweep": {...} | None}. Bar indices are mapped to
    timestamps; a pool spans its first touch to the right edge, because a pool is
    a level that is still there until price takes it out.
    """
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    # Same pivot default as /api/order_blocks: pools are local structure, and the
    # major-swing pivot used by /api/structure_chain surfaces almost none on daily.
    piv_default = {
        "1m": 3, "5m": 4, "15m": 5, "30m": 5,
        "1h": 6, "4h": 6, "6h": 6, "1d": 5, "1w": 5,
    }.get(timeframe, 5)
    pivot_len = max(2, min(int(request.args.get("pivot_len", piv_default)), 100))
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < pivot_len * 2 + 25:
        return jsonify({"symbol": symbol, "pools": [], "sweep": None})

    pools = sc.detect_liquidity_pools(df, pivot_len=pivot_len)
    sweep = sc.detect_liquidity_sweep(df, pivot_len=pivot_len)

    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    last_t = _t(len(bars) - 1)
    pools_out = []
    for pool in pools:
        t0 = _t(pool.get("first_bar"))
        if t0 is None:
            continue
        pools_out.append({
            "kind":       pool["kind"],            # "high" = buy-side, "low" = sell-side
            "level":      round(float(pool["level"]), 2),
            "touches":    int(pool["touches"]),
            "width_pct":  pool.get("width_pct"),
            "start_time": t0,
            "last_time":  _t(pool.get("last_bar")),
            "end_time":   last_t,
            "touch_times": [t for t in (_t(b) for b in pool.get("bars", [])) if t],
        })

    sweep_out = None
    if sweep:
        # bars_ago is counted from the LAST bar, which is how the detector reports
        # freshness; the chart needs the bar itself.
        idx = len(bars) - 1 - int(sweep.get("bars_ago", 0))
        sweep_out = {
            "direction":   sweep["direction"],     # bullish = sell-side pool swept
            "level":       round(float(sweep["level"]), 2),
            "time":        _t(idx),
            "close":       sweep.get("close"),
            "touches":     sweep.get("touches"),
            "bars_ago":    sweep.get("bars_ago"),
            "pierce_atr":  sweep.get("pierce_atr"),
            "wick_ratio":  sweep.get("wick_ratio"),
            "reclaimed":   sweep.get("reclaimed"),
            "pool_times":  [t for t in (_t(b) for b in sweep.get("pool_bars", [])) if t],
        }

    # THE BUY SIGNAL, and it is the scanner's own -- not a second plan invented for
    # the chart. `scan_liquidity_sweep` fires only while the sweep is fresh
    # (max_bars_ago=3), which is the right gate for something drawn as actionable:
    # an older sweep is context, not a signal.
    #
    # Bullish only, deliberately. `scan_liquidity_sweep_bear` is a RISK read whose
    # B-41m arm never reached significance AND emits target=None, so there is no
    # measured plan to draw. Rendering a SELL arrow from it would be inventing one.
    plan = None
    try:
        hit = sc.scan_liquidity_sweep(df)
    except Exception:
        hit = None
    if hit:
        plan = {
            "side": "BUY",
            "entry": hit.get("entry"),
            "stop": hit.get("stop"),
            "target": hit.get("target"),
            "score": hit.get("score_base"),
            "reasons": hit.get("reasons") or [],
            # Travels with the plan so the chart cannot render it without the
            # measurement attached. B-41m measured the SIGNAL positive and B-41p
            # measured THIS PLAN at +0.06R -- both facts, one string.
            "measured": ("B-41m: signal +0.51% @20d (p=0.005) net of costs. "
                         "B-41p: this entry/stop/target returns +0.06R -- the stop "
                         "is what spends the edge, not where it sits."),
        }

    return jsonify({"symbol": symbol, "pools": pools_out, "sweep": sweep_out,
                    "plan": plan})


@app.route("/api/trendlines")
def api_trendlines():
    """Supply / demand trendlines via scanner_templates.detect_trendline_break
    (port of "Trend Lines by Kris" Pine). Returns two-point anchors + a
    projected end-of-data point for each active line so the client can draw
    them as extended-forward line series."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    # Pivot lookback tuning per timeframe — daily uses the Pine default of
    # 20; intraday needs a smaller window or all recent pivots get swallowed.
    prd_default = {
        "1m": 6, "5m": 8, "15m": 10, "30m": 10,
        "1h": 12, "4h": 15, "6h": 16, "1d": 20, "1w": 20,
    }.get(timeframe, 20)
    prd = int(request.args.get("prd", prd_default))
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < prd * 4 + 5:
        return jsonify({"symbol": symbol, "trendlines": None})

    tl = sc.detect_trendline_break(df, prd=prd)
    if tl is None:
        return jsonify({"symbol": symbol, "trendlines": None})

    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    def _wire(side: dict | None) -> dict | None:
        if side is None:
            return None
        return {
            "t1": _t(side["x1"]), "y1": side["y1"],
            "t2": _t(side["x2"]), "y2": side["y2"],
            "t3": _t(side["x3"]), "y3": side["y3"],
            "broken":   side["broken"],
            "bars_ago": side["bars_ago"],
            "level":    side["level"],
            "angle":    side["angle"],
        }

    return jsonify({
        "symbol": symbol,
        "trendlines": {
            "supply": _wire(tl["supply"]),
            "demand": _wire(tl["demand"]),
            "prd":    prd,
        },
    })


@app.route("/api/harmonic")
def api_harmonic():
    """Harmonic (Gartley/Bat/Butterfly/Crab) pattern geometry for overlay.
    See harmonic_patterns.detect_last_pattern. Returns X-A-B-C-D pivot
    times + prices and the entry/stop/targets trade plan, or {"harmonic": null}."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    # Timeframe-aware default: ZigZag confirmation eats bars, so the D pivot
    # rarely sits within 10 bars of the tail on daily data. Autopsy 2026-07-14
    # showed HDFCBANK carrying a valid Gartley at age_bars=44 that was filtered
    # out by the old max_age=10. Loosen to a horizon that matches how a trader
    # would still act on the pattern.
    _default_max_age = {
        "1m": 8, "5m": 12, "15m": 15, "30m": 20,
        "1h": 25, "4h": 30, "6h": 35, "1d": 50, "1w": 20,
    }.get(timeframe, 30)
    max_age = int(request.args.get("max_age", _default_max_age))
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < 30:
        return jsonify({"symbol": symbol, "harmonic": None})

    m = hp.detect_last_pattern(df, max_age_bars=max_age)
    if m is None:
        return jsonify({"symbol": symbol, "harmonic": None})

    def _t(idx):
        if idx is None or idx < 0 or idx >= len(bars):
            return None
        return int(bars[idx]["time"])

    pts = m["points"]
    harmonic = {
        "pattern":   m["pattern"],
        "direction": m["direction"],
        "ratios":    m["ratios"],
        "age_bars":  m["age_bars"],
        "points": {
            k: {"time": _t(v["idx"]), "price": v["price"]}
            for k, v in pts.items()
        },
        "trade": m["trade"],
        "status": m.get("status"),
    }
    return jsonify({"symbol": symbol, "harmonic": harmonic})


@app.route("/api/projection")
def api_projection():
    """Forward price-projection line (Milestone 3). Composes deterministic,
    inspectable projected-price candidates (Elliott Wave Fib targets + VCP /
    Rounding Bottom / Harmonic measured-moves) into a single primary projection
    with a confidence band + confluence count. Returns {"projection": null}
    when nothing clears the Medium confidence floor — the anti-overtrust
    guardrail: show nothing rather than a weak number. See projection.py +
    concepts wiki/analyses/Dashboard-UI-Roadmap.md M3."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    source = ds.detect_source(symbol)
    bars   = source.get_ohlcv(symbol, timeframe, bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < 30:
        return jsonify({"symbol": symbol, "projection": None})

    p = proj.compute_projection(df, timeframe)
    # Anchor the projection line to the last bar's time so the client can draw a
    # forward slope without needing future timestamps on the axis.
    if p is not None:
        p["anchor_time"] = int(bars[-1]["time"])
    return jsonify({"symbol": symbol, "projection": p})


@app.route("/api/tick")
def api_tick():
    symbol = request.args.get("symbol", "").strip().upper()
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    price = ds.detect_source(symbol).get_latest_price(symbol)
    return jsonify({"symbol": symbol, "price": price})


@app.route("/api/delta_profile")
def api_delta_profile():
    """Real buy/sell volume by price for a Hyperliquid coin.

    REAL, not estimated: every row is bucketed by the taker side Hyperliquid
    publishes with the print. Nothing else this server serves can do this, so
    the response always carries `source` and the caller is expected to refuse to
    draw a delta profile for a symbol that is not on this feed rather than
    falling back to a bar-derived guess under the same label.

    Query:
      coin   HL coin, e.g. BTC (required)
      lo,hi  price range to bin over. Defaults to the tape's own min/max.
      bins   bin count, 10..400 (default 48)
      from   only trades at or after this epoch-ms

    The window is bounded by what the ring holds, and `coverage` says so: the
    tape starts empty at server start and there is no historical backfill, so a
    profile can legitimately cover far less than the chart's visible range.
    """
    coin = (request.args.get("coin") or "").strip()
    if not coin:
        return jsonify({"error": "coin is required"}), 400
    if ds.detect_source(coin).name != "hyperliquid":
        return jsonify({"error": f"{coin} is not a Hyperliquid symbol - no "
                                 "aggressor-side data exists for it on this server",
                        "source": None}), 400

    try:
        nbins = max(10, min(int(request.args.get("bins", 48)), 400))
    except ValueError:
        nbins = 48
    try:
        t_from = int(request.args.get("from", 0))
    except ValueError:
        t_from = 0

    with _hl_trades_lock:
        rows = list(_hl_trades.get(coin, ()))
        seen = _hl_trades_seen.get(coin, 0)
        subscribed = coin in _hl_trade_subs
    if t_from:
        rows = [r for r in rows if r[0] >= t_from]

    if not rows:
        # An empty tape is the NORMAL state for the first minutes after a
        # subscription, so it is a 200 with an empty profile and an explanation,
        # not an error the UI has to special-case as a failure.
        return jsonify({
            "coin": coin, "source": "hyperliquid-trades", "subscribed": subscribed,
            "bins": [], "n_trades": 0, "seen": seen,
            "note": ("tape is empty - subscribed and waiting for prints"
                     if subscribed else "not subscribed; open this coin on a chart first"),
        })

    prices = [r[1] for r in rows]
    try:
        lo = float(request.args.get("lo", min(prices)))
        hi = float(request.args.get("hi", max(prices)))
    except ValueError:
        lo, hi = min(prices), max(prices)
    if not (hi > lo):
        hi = lo + max(lo * 1e-6, 1e-9)

    width = (hi - lo) / nbins
    buy = [0.0] * nbins
    sell = [0.0] * nbins
    n_in = 0
    for ms, px, sz, is_buy in rows:
        if px < lo or px > hi:
            continue
        i = min(int((px - lo) / width), nbins - 1)
        (buy if is_buy else sell)[i] += sz
        n_in += 1

    out = [{"lo": round(lo + i * width, 10),
            "hi": round(lo + (i + 1) * width, 10),
            "buy": round(buy[i], 8),
            "sell": round(sell[i], 8),
            "delta": round(buy[i] - sell[i], 8)}
           for i in range(nbins)]
    tb, ts_ = sum(buy), sum(sell)
    return jsonify({
        "coin": coin,
        "source": "hyperliquid-trades",
        "subscribed": subscribed,
        "bins": out,
        "n_trades": n_in,
        "n_tape": len(rows),
        "seen": seen,
        # True once eviction has begun: the profile no longer starts where the
        # subscription did, and any "since" label drawn from first_ts is the
        # ring's horizon rather than the session's.
        "ring_full": len(rows) >= HL_TRADE_RING,
        "first_ts": rows[0][0],
        "last_ts": rows[-1][0],
        "buy_vol": round(tb, 8),
        "sell_vol": round(ts_, 8),
        "cum_delta": round(tb - ts_, 8),
    })


@app.route("/api/symbols/search")
def api_symbols_search():
    """TradingView-style typeahead search across NSE/BSE/US/Crypto."""
    q     = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 20)), 50)
    if not q:
        return jsonify({"results": []})
    return jsonify({"results": sym_dir.search(q, limit=limit)})


@app.route("/api/reversal_events")
def api_reversal_events():
    """Reversal-candidate days (yoga + lunar) from the SQLite calendar.

    Query params:
      from  YYYY-MM-DD  (required)
      to    YYYY-MM-DD  (required)

    Returns a list of {event_date, event_type, display_name, category,
    start_ts, end_ts, weekday} sorted by date+time, plus a parallel
    `coincidence` list of {event_date, score, events} for the same window.
    The chart can use the coincidence list to highlight "sharper reversal"
    days (score ≥ 2) without re-aggregating client-side.
    """
    from datetime import date as _date
    try:
        d_from = _date.fromisoformat(request.args.get("from", ""))
        d_to   = _date.fromisoformat(request.args.get("to", ""))
    except ValueError:
        return jsonify({"error": "from/to must be YYYY-MM-DD"}), 400

    events = rev_cal.events_in_range(d_from, d_to)
    coincidence = rev_cal.coincidence_scores(d_from, d_to)
    return jsonify({"events": events, "coincidence": coincidence,
                    "from": d_from.isoformat(), "to": d_to.isoformat()})


_EVENTS_ANN_CACHE: dict[tuple[str, str], list] = {}


@app.route("/api/events")
def api_events():
    """B-188 event markers (E results, N material filing, M Budget/MPC,
    A anomaly) for the daily chart, each with its measured/hypothesis status
    and the event-day / 5-session move. See tools/chart_events.py."""
    import datetime as _dt
    import chart_events as ce
    from nse_announcements import fetch_announcements
    symbol = request.args.get("symbol", "").strip().upper()
    bars_n = min(int(request.args.get("bars", 300)), 3000)
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    symbol = sym_dir.resolve_symbol(symbol)
    if symbol.startswith("^"):
        return jsonify({"symbol": symbol, "events": [], "missing": []})
    bare = re.sub(r"\.(NS|BO)$", "", symbol, flags=re.IGNORECASE)
    bars = ds.detect_source(symbol).get_ohlcv(symbol, "1d", bars_n)
    df = _bars_to_df(bars)
    if df is None or len(df) < 2:
        return jsonify({"symbol": symbol, "events": [], "missing": []})
    df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None).normalize()
    times = {str(ts.date()): int(b["time"]) for ts, b in zip(df.index, bars)}

    def ann(sym):
        key = (sym, _dt.date.today().isoformat())
        if key not in _EVENTS_ANN_CACHE:
            _EVENTS_ANN_CACHE[key] = fetch_announcements(sym)
        return _EVENTS_ANN_CACHE[key]

    res = ce.collect(bare, df, ann_fn=ann)
    for e in res["events"]:
        e["time"] = times.get(e["session"])
    res["symbol"] = symbol
    return jsonify(res)


@app.route("/api/symbols")
def api_symbols():
    return jsonify({
        "nse": [
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
            "SBIN.NS","HINDUNILVR.NS","ITC.NS","KOTAKBANK.NS","LT.NS",
            "BHARTIARTL.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS",
            "WIPRO.NS","HCLTECH.NS","SUNPHARMA.NS","TITAN.NS","NTPC.NS",
            "POWERGRID.NS","BAJFINANCE.NS","ONGC.NS","COALINDIA.NS","JSWSTEEL.NS",
            "TATASTEEL.NS","M&M.NS","ULTRACEMCO.NS","TECHM.NS","ADANIENT.NS",
            "ADANIPORTS.NS","HINDALCO.NS","DRREDDY.NS","DIVISLAB.NS","CIPLA.NS",
        ],
        "crypto": [
            "BTC","ETH","SOL","AVAX","ARB","OP","MATIC","DOGE","LINK","UNI",
            "AAVE","APT","SUI","INJ","TIA","JUP","WIF","PEPE","BNB","TON",
            "SEI","NEAR","FTM","ATOM","DOT","LTC","XRP","ADA","TRUMP","HYPE",
        ],
    })


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@sock.route("/ws")
def ws_handler(ws):
    ws_id = id(ws)
    q = _register(ws_id)
    log.info("WS client connected  id=%d", ws_id)

    def sender():
        while True:
            try:
                msg = q.get(timeout=20)
                if msg is None:
                    return
                ws.send(msg)
            except queue.Empty:
                try:
                    ws.send(json.dumps({"type": "ping"}))
                except Exception:
                    return
            except Exception:
                return

    sender_t = threading.Thread(target=sender, daemon=True, name=f"ws-send-{ws_id}")
    sender_t.start()

    try:
        while True:
            raw = ws.receive()
            if raw is None:
                break
            try:
                msg = json.loads(raw)
                if msg.get("action") == "subscribe":
                    sym = sym_dir.resolve_symbol(msg.get("symbol", "").strip().upper())
                    tf  = msg.get("timeframe", "1d")
                    if sym and tf:
                        _subscribe(ws_id, sym, tf)
                        log.debug("subscribe  %s/%s  client=%d", sym, tf, ws_id)
            except Exception as e:
                log.debug("WS parse error: %s", e)
    except Exception as e:
        log.debug("WS recv error: %s", e)
    finally:
        _unregister(ws_id)
        q.put(None)   # stop sender thread
        log.info("WS client disconnected  id=%d", ws_id)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # --port so a second instance can be run alongside the live one (verifying a
    # feed change without dropping the websocket clients of the running chart).
    import argparse as _argparse
    _ap = _argparse.ArgumentParser(description="Trading Bramha chart server")
    _ap.add_argument("--port", type=int, default=5001)
    # ── Why the default is still 0.0.0.0 (B-86) ──────────────────────────────
    # bandit flags this as B104, and the design review's recommendation was to
    # default to loopback. That recommendation was made without checking what
    # binds here, and it is WRONG for this server: the chart is a PWA -- it ships
    # a service worker, a manifest and maskable icons, and there are INSTALLED
    # clients (the 2026-08-29 cache regression was found precisely because a fix
    # never reached one). A phone on the same wifi cannot reach 127.0.0.1, so
    # defaulting to loopback would silently break the surface the PWA exists for.
    #
    # The finding is therefore ACCEPTED rather than fixed, and made explicit:
    # `--host 127.0.0.1` is one flag away for anyone who wants it. What makes the
    # exposure tolerable is the rest of the shape -- read-only market endpoints,
    # no credentials, no writes, and a module route that serves only what the
    # page references (B-85) rather than anything in `tools/`.
    _ap.add_argument("--host", default="0.0.0.0",
                     help="bind address; use 127.0.0.1 to keep it off the LAN "
                          "(the installed PWA on a phone then cannot reach it)")
    _args = _ap.parse_args()
    _hl_start()
    log.info("Chart server → http://localhost:%d  (bound %s)",
             _args.port, _args.host)
    app.run(host=_args.host, port=_args.port, debug=False, threaded=True)
