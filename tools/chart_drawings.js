// chart_drawings.js — user drawing tools for the chart (trend line, horizontal
// ray, rectangle zone, text note, Fibonacci retracement).
//
// Lightweight Charts ships NO drawing tools — those live in TradingView's paid
// Advanced Charts — so all of this is hand-built.
//
// Design, matching the rest of this repo's overlay modules (elliott_wave.js,
// fvg.js): this file is the pure part — the model, the geometry, hit-testing and
// the canvas painting. It knows nothing about Lightweight Charts. The caller
// supplies a tiny coordinate adapter:
//
//     {toX(time) -> px|null, toY(price) -> px|null,
//      fromX(px) -> time|null, fromY(px) -> price|null}
//
// so swapping charting libraries only means rewriting that adapter, exactly as
// the Elliott Wave integration layer is arranged.
//
// EVERY drawing is stored in DATA coordinates (time + price), never pixels. That
// is what keeps a trendline pinned to its bars across pan, zoom, resize and
// theme changes — the recurring failure mode when overlays are stored in screen
// space.
(function (global) {
  'use strict';

  // Tools that need two anchor points before they are complete.
  const TWO_POINT = new Set(['trend', 'rect', 'fib']);

  // Fibonacci retracement levels. 0 and 1 are the anchors themselves; the rest
  // are the retracements traders actually watch. 0.618 is the "golden pocket"
  // edge and is emphasised when drawn.
  const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];

  const HIT_PX = 6;          // click tolerance when selecting/erasing
  const MIN_DRAG_PX = 3;     // below this a drag is treated as a click, not a shape

  let _seq = 0;
  function _id() { return 'd' + (Date.now().toString(36)) + (_seq++).toString(36); }

  // ── model ──────────────────────────────────────────────────────────────────

  /** Create a drawing. Points are {t, y} in data coordinates. */
  function make(type, p1, p2, opts) {
    opts = opts || {};
    return {
      id: _id(),
      type: type,
      p1: p1 ? {t: p1.t, y: p1.y} : null,
      p2: p2 ? {t: p2.t, y: p2.y} : null,
      text: opts.text || '',
      color: opts.color || null,   // null = use the palette default for the type
      created: Date.now(),
    };
  }

  /** A drawing is renderable once it has the anchors its type requires. */
  function isComplete(d) {
    if (!d || !d.p1) return false;
    if (TWO_POINT.has(d.type)) return !!d.p2;
    return true;
  }

  // ── serialisation ──────────────────────────────────────────────────────────
  // Stored per symbol under a `tb-` key, matching the theme/indicator convention
  // already in chart_dashboard.html.

  function storageKey(symbol) {
    return 'tb-draw-' + String(symbol || '').toUpperCase();
  }

  function load(symbol) {
    try {
      const raw = localStorage.getItem(storageKey(symbol));
      if (!raw) return [];
      const arr = JSON.parse(raw);
      if (!Array.isArray(arr)) return [];
      // Drop anything malformed rather than let one bad record break the layer.
      return arr.filter(d => d && d.type && isComplete(d));
    } catch (e) { return []; }
  }

  function save(symbol, drawings) {
    try {
      const keep = (drawings || []).filter(isComplete);
      if (!keep.length) localStorage.removeItem(storageKey(symbol));
      else localStorage.setItem(storageKey(symbol), JSON.stringify(keep));
      return true;
    } catch (e) { return false; }   // quota/private-mode: drawing still works this session
  }

  // ── magnet ─────────────────────────────────────────────────────────────────

  /**
   * Snap a price to the nearest OHLC value of the bar nearest `time`, when it is
   * within `tolPx` on screen. Traders anchor to highs and lows, not to wherever
   * the pointer happened to land, so this is on by default in the UI.
   */
  function snap(bars, adapter, time, price, tolPx) {
    tolPx = tolPx == null ? 8 : tolPx;
    if (!bars || !bars.length) return {t: time, y: price};
    // Nearest bar by time.
    let best = null, bestDt = Infinity;
    for (let i = 0; i < bars.length; i++) {
      const dt = Math.abs(bars[i].time - time);
      if (dt < bestDt) { bestDt = dt; best = bars[i]; }
    }
    if (!best) return {t: time, y: price};

    const py = adapter.toY(price);
    if (py == null) return {t: best.time, y: price};

    let snapY = price, bestD = Infinity;
    ['high', 'low', 'open', 'close'].forEach(k => {
      const v = best[k];
      if (typeof v !== 'number') return;
      const c = adapter.toY(v);
      if (c == null) return;
      const d = Math.abs(c - py);
      if (d < bestD) { bestD = d; snapY = v; }
    });
    return {t: best.time, y: (bestD <= tolPx ? snapY : price)};
  }

  // ── geometry / hit-testing ─────────────────────────────────────────────────

  function _distToSegment(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1;
    const len2 = dx * dx + dy * dy;
    if (len2 === 0) return Math.hypot(px - x1, py - y1);
    let t = ((px - x1) * dx + (py - y1) * dy) / len2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
  }

  /** Screen-space points for a drawing, or null when it is off-scale. */
  function project(d, adapter, width) {
    const x1 = d.p1 ? adapter.toX(d.p1.t) : null;
    const y1 = d.p1 ? adapter.toY(d.p1.y) : null;
    if (x1 == null || y1 == null) return null;
    if (!TWO_POINT.has(d.type)) {
      // A horizontal ray has one anchor and runs to the right edge; the text
      // note is anchored at its point.
      return {x1: x1, y1: y1, x2: (d.type === 'hline' ? width : x1), y2: y1};
    }
    const x2 = adapter.toX(d.p2.t);
    const y2 = adapter.toY(d.p2.y);
    if (x2 == null || y2 == null) return null;
    return {x1: x1, y1: y1, x2: x2, y2: y2};
  }

  /** Topmost drawing under (px, py), or null. Later drawings win. */
  function hitTest(drawings, adapter, px, py, width, ctx) {
    for (let i = drawings.length - 1; i >= 0; i--) {
      const d = drawings[i];
      const p = project(d, adapter, width);
      if (!p) continue;
      let hit = false;
      if (d.type === 'trend' || d.type === 'hline') {
        hit = _distToSegment(px, py, p.x1, p.y1, p.x2, p.y2) <= HIT_PX;
      } else if (d.type === 'rect' || d.type === 'fib') {
        const lo = Math.min(p.x1, p.x2), hi = Math.max(p.x1, p.x2);
        const t = Math.min(p.y1, p.y2), b = Math.max(p.y1, p.y2);
        // Edges only for a rect (its middle must stay clickable for the chart);
        // a fib is grabbed anywhere in its band since its lines fill it.
        if (d.type === 'fib') {
          hit = px >= lo - HIT_PX && px <= hi + HIT_PX && py >= t - HIT_PX && py <= b + HIT_PX;
        } else {
          const nearX = (px >= lo - HIT_PX && px <= hi + HIT_PX);
          const nearY = (py >= t - HIT_PX && py <= b + HIT_PX);
          hit = (nearX && nearY) && (
            Math.abs(px - lo) <= HIT_PX || Math.abs(px - hi) <= HIT_PX ||
            Math.abs(py - t) <= HIT_PX || Math.abs(py - b) <= HIT_PX);
        }
      } else if (d.type === 'text') {
        const w = ctx ? ctx.measureText(d.text || '').width : 60;
        hit = px >= p.x1 - HIT_PX && px <= p.x1 + w + HIT_PX &&
              py >= p.y1 - 14 && py <= p.y1 + HIT_PX;
      }
      if (hit) return d;
    }
    return null;
  }

  // ── painting ───────────────────────────────────────────────────────────────

  const DEFAULT_COLORS = {
    trend: '#42a5f5',
    hline: '#ffa726',
    rect:  '#ab47bc',
    text:  '#eaeff7',
    fib:   '#26c6da',
  };

  function _color(d) { return d.color || DEFAULT_COLORS[d.type] || '#42a5f5'; }

  function _fmt(v) {
    if (!isFinite(v)) return '';
    const a = Math.abs(v);
    return a >= 1000 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
  }

  /**
   * Paint every drawing. `opts`:
   *   selectedId  — drawn thicker with its handles shown
   *   preview     — an in-progress drawing painted dashed
   *   textColor   — theme-dependent colour for labels
   */
  function render(ctx, drawings, adapter, width, height, opts) {
    opts = opts || {};
    ctx.clearRect(0, 0, width, height);
    ctx.save();
    ctx.lineJoin = 'round';
    ctx.font = '11px system-ui, -apple-system, Segoe UI, sans-serif';

    const all = drawings.slice();
    if (opts.preview) all.push(opts.preview);

    all.forEach(d => {
      const isPreview = opts.preview && d === opts.preview;
      if (!isComplete(d) && !isPreview) return;
      const p = project(d, adapter, width);
      if (!p) return;
      const col = _color(d);
      const selected = !isPreview && d.id === opts.selectedId;

      ctx.strokeStyle = col;
      ctx.fillStyle = col;
      ctx.lineWidth = selected ? 2.5 : 1.5;
      ctx.setLineDash(isPreview ? [5, 4] : []);
      ctx.globalAlpha = isPreview ? 0.8 : 1;

      if (d.type === 'trend' || d.type === 'hline') {
        ctx.beginPath();
        ctx.moveTo(p.x1, p.y1);
        ctx.lineTo(p.x2, p.y2);
        ctx.stroke();
        if (d.type === 'hline') {
          // Price tag at the right edge, the way a chart's own price line reads.
          const label = _fmt(d.p1.y);
          const w = ctx.measureText(label).width + 8;
          ctx.globalAlpha = isPreview ? 0.6 : 0.9;
          ctx.fillRect(width - w - 2, p.y1 - 8, w, 16);
          ctx.fillStyle = '#0d1117';
          ctx.fillText(label, width - w + 2, p.y1 + 4);
          ctx.fillStyle = col;
          ctx.globalAlpha = 1;
        }
      } else if (d.type === 'rect') {
        const x = Math.min(p.x1, p.x2), y = Math.min(p.y1, p.y2);
        const w = Math.abs(p.x2 - p.x1), h = Math.abs(p.y2 - p.y1);
        ctx.globalAlpha = isPreview ? 0.10 : 0.14;
        ctx.fillRect(x, y, w, h);
        ctx.globalAlpha = isPreview ? 0.8 : 1;
        ctx.strokeRect(x, y, w, h);
      } else if (d.type === 'fib') {
        // Anchors: p1 is the 0 level, p2 the 1 level, so dragging low->high
        // gives a normal retracement and high->low an inverted one.
        const xa = Math.min(p.x1, p.x2), xb = Math.max(p.x1, p.x2);
        const span = d.p2.y - d.p1.y;
        FIB_LEVELS.forEach(lv => {
          const price = d.p1.y + span * lv;
          const yy = adapter.toY(price);
          if (yy == null) return;
          const golden = (lv === 0.618);
          ctx.globalAlpha = isPreview ? 0.7 : (golden ? 1 : 0.75);
          ctx.lineWidth = golden ? 2 : 1;
          ctx.beginPath();
          ctx.moveTo(xa, yy);
          ctx.lineTo(xb, yy);
          ctx.stroke();
          ctx.globalAlpha = 1;
          ctx.fillText(`${(lv * 100).toFixed(1)}%  ${_fmt(price)}`, xa + 4, yy - 3);
        });
        // Connecting leg, so the swing being measured is visible.
        ctx.globalAlpha = 0.5;
        ctx.setLineDash([4, 4]);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p.x1, p.y1);
        ctx.lineTo(p.x2, p.y2);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
      } else if (d.type === 'text') {
        ctx.fillStyle = opts.textColor || col;
        ctx.font = '12px system-ui, -apple-system, Segoe UI, sans-serif';
        ctx.fillText(d.text || '', p.x1 + 4, p.y1 - 4);
        ctx.font = '11px system-ui, -apple-system, Segoe UI, sans-serif';
        ctx.fillStyle = col;
        // A small tick marks the exact anchor, since text sits offset from it.
        ctx.beginPath();
        ctx.moveTo(p.x1, p.y1 - 3);
        ctx.lineTo(p.x1, p.y1 + 3);
        ctx.stroke();
      }

      if (selected) {
        ctx.setLineDash([]);
        ctx.fillStyle = col;
        const pts = (d.type === 'hline') ? [[p.x1, p.y1]] : [[p.x1, p.y1], [p.x2, p.y2]];
        pts.forEach(([hx, hy]) => {
          ctx.beginPath();
          ctx.arc(hx, hy, 4, 0, Math.PI * 2);
          ctx.fill();
        });
      }
    });

    ctx.restore();
  }

  global.Drawings = {
    make, isComplete, load, save, storageKey, snap,
    hitTest, project, render,
    TWO_POINT, FIB_LEVELS, DEFAULT_COLORS, MIN_DRAG_PX,
  };
})(window);
