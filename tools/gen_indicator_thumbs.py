"""gen_indicator_thumbs.py — preview pictures for the Indicator Browser (B-151).

Opens the Chart Tool in headless Chromium, puts ONE reference chart on screen
(same symbol, timeframe and window for every indicator, so the pictures compare),
turns on one indicator at a time through the pane's own checkbox, waits for its
data to land, and captures the chart body. Each picture is saved as
`ind-thumbs/<key>.<hash10>.webp` — the hash is of the image bytes, so a redraw is
a new URL and the service worker's cache-first rule can never pin a stale one —
and `ind-thumbs/manifest.json` maps key → file. Old pictures for a key are
deleted when a new one is written.

Exceptions to the one reference chart, because the indicator draws nothing on a
daily NSE chart: session tools (VWAP, VWAP bands, Session Volume Profile, TPO)
use the same stock on 1h, and Delta Profile, which needs Hyperliquid taker data,
uses BTC 1h. The manifest records the chart each picture came from.

Rerun when an indicator's drawing changes. Needs a running chart server
(default http://localhost:5001) and Python Playwright with Chromium.

    python tools/gen_indicator_thumbs.py                 # all 59
    python tools/gen_indicator_thumbs.py --only rsi,macd # just these
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "ind-thumbs"

REF_SYMBOL, REF_TF, REF_RANGE = "RELIANCE.NS", "1d", "6M"
#: key → (symbol, timeframe) where the reference chart cannot show the indicator.
OVERRIDES = {
    "vwap": (REF_SYMBOL, "1h"), "vwmr": (REF_SYMBOL, "1h"),
    "svp": (REF_SYMBOL, "1h"), "tpo": (REF_SYMBOL, "1h"),
    "deltaprofile": ("BTC", "1h"),
}
VIEWPORT = {"width": 1280, "height": 800}
THUMB_W, THUMB_H = 640, 360
QUALITY = 72
SETTLE_MS = 900          # quiet time after the last fetch before capturing
MAX_WAIT_MS = 20000

# Counts in-flight fetches so we can wait for an indicator's own data, not a
# fixed sleep. Live WebSocket ticks are not fetches and do not hold it open.
_INIT = """
(() => {
  window.__inflight = 0; window.__lastNet = Date.now();
  const f = window.fetch;
  window.fetch = function (...a) {
    window.__inflight++; window.__lastNet = Date.now();
    return f.apply(this, a).finally(() => { window.__inflight--; window.__lastNet = Date.now(); });
  };
})();
"""
# Chrome that is not the indicator: the drawing toolbar and the browser overlay.
_HIDE = ".draw-tools, .ib-overlay { display: none !important; }"


def _keys(html: str) -> list[str]:
    body = html.split("const INDICATOR_DEFS = [", 1)[1].split("\n];", 1)[0]
    return re.findall(r"key:'([a-z0-9_]+)'", body)


def _settle(page) -> None:
    t0 = time.time()
    page.wait_for_timeout(250)
    while (time.time() - t0) * 1000 < MAX_WAIT_MS:
        busy, since = page.evaluate("[window.__inflight, Date.now() - window.__lastNet]")
        if busy == 0 and since >= SETTLE_MS:
            return
        page.wait_for_timeout(150)


def _set_chart(page, symbol: str, tf: str) -> None:
    cur = page.evaluate("[panes[0].symbol, panes[0].tf]")
    if cur[0] != symbol:
        page.fill(".pane .sym-in", symbol)
        page.press(".pane .sym-in", "Enter")
        _settle(page)
        # The typeahead can stay open over the toolbar after Enter.
        page.evaluate("closeAllSymbolDropdowns(); document.activeElement && document.activeElement.blur()")
    if page.evaluate("panes[0].tf") != tf:
        page.select_option(".pane .tf-sel", tf)
        _settle(page)
    page.evaluate(f"document.querySelector('.pane .range-btn[data-range=\"{REF_RANGE}\"]').click()")
    _settle(page)


def _only(page, key: str) -> None:
    """Exactly `key` on, through the classic checkboxes (same path as a click)."""
    page.evaluate("""key => {
      const p = panes[0];
      p.el.querySelectorAll('.ind-panel .ind-chk').forEach(c => {
        const want = c.dataset.key === key;
        if (c.checked !== want) { c.checked = want; c.dispatchEvent(new Event('change', {bubbles: true})); }
      });
      // A companion switched on WITHOUT its checkbox (obvdiv adds OBV that way)
      // survives the loop above and would leak into every later picture. The
      // divergence tools' own oscillator is part of THEIR picture, so it stays.
      const keepWith = {rsidiv: 'rsi', obvdiv: 'obv'};
      [...p.indicators].forEach(k => {
        if (k !== key && k !== keepWith[key]) removeIndicatorByKey(p, k);
      });
    }""", key)
    _settle(page)


#: Share of the picture given to oscillator panes when an indicator opens one.
SUB_SHARE = 0.40


def _capture(page):
    """The chart as a PIL image. Oscillator panes sit BELOW the visible chart
    body (they extend its scroll height), so a plain element shot misses them:
    capture the price chart and the pane stack separately and stack them, the
    price chart squeezed to make room."""
    from PIL import Image
    main = Image.open(io.BytesIO(page.locator(".pane .chart-main").first.screenshot())).convert("RGB")
    if page.evaluate("panes[0].el.querySelectorAll('.sub-pane').length") == 0:
        return main
    subs = Image.open(io.BytesIO(page.locator(".pane .sub-panes").first.screenshot())).convert("RGB")
    w, h = main.size
    sub_h = int(h * SUB_SHARE)
    out = Image.new("RGB", (w, h))
    out.paste(main.resize((w, h - sub_h), Image.LANCZOS), (0, 0))
    out.paste(subs.resize((w, sub_h), Image.LANCZOS), (0, h - sub_h))
    return out


#: Below this share of changed pixels (vs the same chart with nothing on), the
#: indicator found nothing to draw on the reference chart — a pattern detector
#: on a chart with no pattern. A bare chart captioned "Double Bottom" would
#: mislead, so that key gets no picture and the browser shows its swatch.
MIN_CHANGED = 0.0005


def _changed_share(a, b) -> float:
    """Share of pixels that differ visibly, ignoring the legend strip at the top
    (it always changes: it names the indicator)."""
    from PIL import ImageChops
    w, h = a.size
    box = (0, int(h * 0.06), w, h)
    d = ImageChops.difference(a.crop(box).convert("L"), b.resize(a.size).crop(box).convert("L"))
    hist = d.histogram()
    return sum(hist[24:]) / max(1, sum(hist))


def _to_webp(im) -> bytes:
    from PIL import Image
    # Centre-crop to 16:9, then downscale.
    w, h = im.size
    target = THUMB_W / THUMB_H
    if w / h > target:
        nw = int(h * target)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im = im.resize((THUMB_W, THUMB_H), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=QUALITY, method=6)
    return buf.getvalue()


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default="http://localhost:5001/")
    ap.add_argument("--only", default="", help="comma-separated keys")
    a = ap.parse_args(argv)

    from playwright.sync_api import sync_playwright

    keys = _keys((HERE / "chart_dashboard.html").read_text(encoding="utf-8"))
    want = [k for k in keys if not a.only or k in a.only.split(",")]
    OUT.mkdir(exist_ok=True)
    man_path = OUT / "manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    manifest = {k: v for k, v in manifest.get("thumbs", {}).items() if k in keys}

    with sync_playwright() as pw:
        br = pw.chromium.launch()
        ctx = br.new_context(viewport=VIEWPORT, color_scheme="dark", device_scale_factor=1)
        ctx.add_init_script(_INIT)
        page = ctx.new_page()
        page.goto(a.url, wait_until="domcontentloaded")
        page.wait_for_function("typeof panes !== 'undefined' && panes.length > 0 && panes[0].bars && panes[0].bars.length > 0",
                               timeout=60000)
        page.select_option("#header select", "1")
        page.wait_for_function("panes.length === 1 && panes[0].bars && panes[0].bars.length > 0", timeout=60000)
        page.add_style_tag(content=_HIDE)
        # Info cards (verdicts, plans, odds) are text, and docked they take a
        # third of the chart; the picture is what the indicator DRAWS. This is
        # the headless profile's own setting — nobody's saved layout changes.
        page.evaluate("setCardMode(panes[0], 'off'); applyCardMode(panes[0])")
        bare = {}
        for i, key in enumerate(want, 1):
            sym, tf = OVERRIDES.get(key, (REF_SYMBOL, REF_TF))
            _set_chart(page, sym, tf)
            # A bare capture right before each indicator, not one per chart: live
            # ticks and autoscale drift over a run and swamp a thin line's few pixels.
            _only(page, "__none__")
            bare[(sym, tf)] = _capture(page)
            _only(page, key)
            img = _capture(page)
            chart = f"{sym} · {tf} · {REF_RANGE}"
            share = _changed_share(img, bare[(sym, tf)])
            if share < MIN_CHANGED:
                for old in OUT.glob(f"{key}.*.webp"):
                    old.unlink()
                manifest[key] = {"file": None, "chart": chart,
                                 "reason": "nothing drawn on the reference chart"}
                print(f"[{i}/{len(want)}] {key:18s}  --   nothing drawn ({share:.2%} changed) {sym} {tf}")
                continue
            webp = _to_webp(img)
            h = hashlib.sha256(webp).hexdigest()[:10]
            name = f"{key}.{h}.webp"
            for old in OUT.glob(f"{key}.*.webp"):
                if old.name != name:
                    old.unlink()
            (OUT / name).write_bytes(webp)
            manifest[key] = {"file": name, "chart": chart, "bytes": len(webp)}
            print(f"[{i}/{len(want)}] {key:18s} {len(webp) // 1024:3d} KB  {share:6.1%} changed  {sym} {tf}")
        _only(page, "__none__")
        br.close()

    man_path.write_text(json.dumps({"generated": date.today().isoformat(), "thumbs": dict(sorted(manifest.items()))},
                                   indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(v.get("bytes", 0) for v in manifest.values())
    print(f"manifest: {sum(1 for v in manifest.values() if v.get('file'))} pictures, {total / 1024 / 1024:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
