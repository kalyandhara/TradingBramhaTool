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
import sys
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
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
                for coin, interval in subs_snapshot:
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {"type": "candle", "coin": coin,
                                         "interval": interval},
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
    if msg.get("channel") != "candle":
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


@app.route("/elliott_wave.js")
def elliott_wave_js():
    return send_from_directory(HERE, "elliott_wave.js", mimetype="application/javascript")


@app.route("/volume_profile.js")
def volume_profile_js():
    return send_from_directory(HERE, "volume_profile.js", mimetype="application/javascript")


@app.route("/fvg.js")
def fvg_js():
    return send_from_directory(HERE, "fvg.js", mimetype="application/javascript")


@app.route("/fibonacci.js")
def fibonacci_js():
    return send_from_directory(HERE, "fibonacci.js", mimetype="application/javascript")


@app.route("/gann.js")
def gann_js():
    return send_from_directory(HERE, "gann.js", mimetype="application/javascript")


@app.route("/session_volume_profile.js")
def session_volume_profile_js():
    return send_from_directory(HERE, "session_volume_profile.js",
                               mimetype="application/javascript")


@app.route("/hm_indicator.js")
def hm_indicator_js():
    return send_from_directory(HERE, "hm_indicator.js",
                               mimetype="application/javascript")


@app.route("/supertrend_ai.js")
def supertrend_ai_js():
    return send_from_directory(HERE, "supertrend_ai.js",
                               mimetype="application/javascript")


@app.route("/percent_r_trend_exhaustion.js")
def percent_r_trend_exhaustion_js():
    return send_from_directory(HERE, "percent_r_trend_exhaustion.js", mimetype="application/javascript")


@app.route("/adx_di.js")
def adx_di_js():
    return send_from_directory(HERE, "adx_di.js", mimetype="application/javascript")


@app.route("/evwma_vwap_macd.js")
def evwma_vwap_macd_js():
    return send_from_directory(HERE, "evwma_vwap_macd.js",
                               mimetype="application/javascript")


@app.route("/renko.js")
def renko_js():
    return send_from_directory(HERE, "renko.js", mimetype="application/javascript")


@app.route("/rsi_divergence.js")
def rsi_divergence_js():
    return send_from_directory(HERE, "rsi_divergence.js", mimetype="application/javascript")


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
    right edge while still unmitigated). {"order_blocks": []} when none exist."""
    symbol    = request.args.get("symbol", "").strip().upper()
    timeframe = request.args.get("timeframe", "1d")
    bars_n    = min(int(request.args.get("bars", 300)), 3000)
    # Order blocks are more LOCAL than major structure swings, so a tighter pivot
    # than /api/structure_chain — otherwise a daily chart surfaces almost none.
    piv_default = {
        "1m": 3, "5m": 4, "15m": 5, "30m": 5,
        "1h": 6, "4h": 6, "6h": 6, "1d": 6, "1w": 6,
    }.get(timeframe, 6)
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
        })

    retest_out = []
    for rt in retests:
        t = _t(rt["idx"])
        if t is None:
            continue
        retest_out.append({
            "dir":   rt["dir"],
            "time":  t,
            "price": round(rt["price"], 2),
            "buy_pct":  rt.get("buy_pct"),
            "sell_pct": rt.get("sell_pct"),
        })

    return jsonify({"symbol": symbol, "order_blocks": out, "retests": retest_out})


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
    _hl_start()
    log.info("Chart server → http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
