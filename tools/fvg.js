/*!
 * fvg.js — Fair Value Gap (3-candle imbalance) detection module.
 *
 * Pure computation library: takes an OHLCV bar array and returns Fair Value
 * Gap zones — the classic ICT/SMC 3-candle imbalance where candle[i-2] and
 * candle[i] don't overlap, leaving a gap that candle[i-1] "raced through".
 *
 * No DOM / charting-library dependency — rendering is handled by the caller
 * (see chart_dashboard.html: drawFVG()). Mirrors volume_profile.js /
 * elliott_wave.js's separation of concerns.
 *
 * Public API (window.FVG):
 *   FVG.compute(bars, opts) -> zone[]
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 * Zone shape: {
 *   bullish: bool,
 *   startIdx, startTime,        // candle[i-2] — the gap's left edge
 *   top, bottom,                 // price boundaries of the gap
 *   filledIdx, filledTime,       // index/time the gap was first touched, or null if still open
 *   sizePct,                     // gap size as % of price, for minSizePct filtering
 * }
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    minSizePct: 0,        // ignore gaps smaller than this % of price (0 = keep all)
    maxZones:   60,        // cap how many zones compute() returns (most recent first)
  };

  // ── Step 1: scan every 3-candle window for an unfilled-on-arrival gap ────────
  function findZones(bars, opts) {
    const zones = [];
    const n = bars.length;
    for (let i = 2; i < n; i++) {
      const left = bars[i - 2], mid = bars[i - 1], right = bars[i];

      // Bullish FVG: right candle's low sits above left candle's high.
      if (right.low > left.high) {
        const top = right.low, bottom = left.high;
        const sizePct = ((top - bottom) / bottom) * 100;
        if (sizePct >= opts.minSizePct) {
          zones.push({
            bullish: true,
            startIdx: i - 2, startTime: left.time,
            top, bottom, sizePct,
            filledIdx: null, filledTime: null,
          });
        }
      }
      // Bearish FVG: right candle's high sits below left candle's low.
      else if (right.high < left.low) {
        const top = left.low, bottom = right.high;
        const sizePct = ((top - bottom) / bottom) * 100;
        if (sizePct >= opts.minSizePct) {
          zones.push({
            bullish: false,
            startIdx: i - 2, startTime: left.time,
            top, bottom, sizePct,
            filledIdx: null, filledTime: null,
          });
        }
      }
    }
    return zones;
  }

  // ── Step 2: mark each zone filled the first time price trades back into it ──
  // A zone is "filled" the first bar (after it forms) whose range overlaps the
  // gap's [bottom, top] band. Bullish gaps act as support (filled from above by
  // a low dipping into the band); bearish gaps act as resistance (filled from
  // below by a high poking into the band) — but either direction of overlap
  // counts as a fill, matching how traders read "the gap got tagged."
  function markFills(bars, zones) {
    zones.forEach(z => {
      for (let i = z.startIdx + 3; i < bars.length; i++) {
        const b = bars[i];
        if (b.low <= z.top && b.high >= z.bottom) {
          z.filledIdx = i;
          z.filledTime = b.time;
          break;
        }
      }
    });
  }

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    if (!bars || bars.length < 3) return [];
    const zones = findZones(bars, opts);
    markFills(bars, zones);
    return zones.slice(-opts.maxZones);
  }

  global.FVG = {
    VERSION: '1.0.0',
    compute,
  };
})(typeof window !== 'undefined' ? window : globalThis);
