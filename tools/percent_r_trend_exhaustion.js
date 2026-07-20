/*!
 * percent_r_trend_exhaustion.js — port of "%R Trend Exhaustion [upslidedown]"
 * (Pine v6) to plain JS.
 *
 * Ported: dual-length Williams %R (fast/slow), MA smoothing (sma/ema),
 * overbought/oversold zone detection, and the headline signal — a reversal
 * arrow printed the bar a trend exhausts (price leaves the OB/OS zone).
 *
 * Not ported (kept the file focused on the core signal, not a 1:1 clone):
 *   - "Average" formula mode, smoothing types other than sma/ema (original
 *     offers hma/rma/wma/vwma/swma/highlow/linreg/median/mom/percentrank)
 *   - on-chart boxes, zero-line crosses, fast/slow crossover dots
 *   - alerts / TTS strategy-signal plumbing (TradingView-specific)
 * These can be added the same way FVG/Elliott Wave grew incrementally if
 * they turn out to matter in practice.
 *
 * No DOM / charting-library dependency — rendering is handled by the caller
 * (see chart_dashboard.html). Mirrors fvg.js's separation of concerns.
 *
 * Public API (window.PRTE):
 *   PRTE.compute(bars, opts) -> {
 *     fast, slow,                 // smoothed %R line series (-100..0)
 *     obReversal, osReversal,     // bearish / bullish exhaustion arrows
 *     obStart, osStart,           // entered-zone warning points
 *     threshold,                  // echoed back for reference-line drawing
 *   }
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    fastLength: 21,
    fastSmoothing: 7,
    slowLength: 112,
    slowSmoothing: 3,
    threshold: 20,       // overbought/oversold zone size (matches Pine default)
    smoothType: 'ema',   // 'ema' | 'sma'
  };

  // ── Williams %R over a trailing window, one value per bar ────────────────────
  function percentR(bars, length) {
    const out = new Array(bars.length);
    for (let i = 0; i < bars.length; i++) {
      const start = Math.max(0, i - length + 1);
      let hh = -Infinity, ll = Infinity;
      for (let j = start; j <= i; j++) {
        if (bars[j].high > hh) hh = bars[j].high;
        if (bars[j].low < ll) ll = bars[j].low;
      }
      const range = hh - ll;
      out[i] = {
        time: bars[i].time,
        value: range === 0 ? 0 : (100 * (bars[i].close - hh) / range),
      };
    }
    return out;
  }

  // ── MA smoothing of a {time,value}[] series (mirrors chart_dashboard.html's
  // own emaSeries/smaSeries: EMA seeds with an SMA of the first `period`
  // values, both trim the leading period-1 points) ────────────────────────────
  function smaOf(series, period) {
    const out = [];
    let sum = 0;
    for (let i = 0; i < series.length; i++) {
      sum += series[i].value;
      if (i >= period) sum -= series[i - period].value;
      if (i >= period - 1) out.push({time: series[i].time, value: sum / period});
    }
    return out;
  }

  function emaOf(series, period) {
    const out = [];
    const k = 2 / (period + 1);
    let prev = null;
    for (let i = 0; i < series.length; i++) {
      if (prev === null) {
        if (i === period - 1) {
          let sum = 0;
          for (let j = 0; j <= i; j++) sum += series[j].value;
          prev = sum / period;
          out.push({time: series[i].time, value: prev});
        }
        continue;
      }
      prev = series[i].value * k + prev * (1 - k);
      out.push({time: series[i].time, value: prev});
    }
    return out;
  }

  function smooth(series, period, type) {
    if (period <= 1) return series;
    return type === 'sma' ? smaOf(series, period) : emaOf(series, period);
  }

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const empty = {fast: [], slow: [], obReversal: [], osReversal: [], obStart: [], osStart: [], threshold: opts.threshold};
    if (!bars || bars.length < opts.slowLength + 5) return empty;

    const fast = smooth(percentR(bars, opts.fastLength), opts.fastSmoothing, opts.smoothType);
    const slow = smooth(percentR(bars, opts.slowLength), opts.slowSmoothing, opts.smoothType);

    // Smoothing trims leading bars, so join fast/slow by time rather than index.
    const fastMap = new Map(fast.map(p => [p.time, p.value]));
    const slowMap = new Map(slow.map(p => [p.time, p.value]));

    const th = opts.threshold;
    const obReversal = [], osReversal = [], obStart = [], osStart = [];
    let wasOB = false, wasOS = false;

    for (const bar of bars) {
      const f = fastMap.get(bar.time);
      const s = slowMap.get(bar.time);
      if (f === undefined || s === undefined) continue;

      const ob = f >= -th && s >= -th;
      const os = f <= (-100 + th) && s <= (-100 + th);

      if (ob && !wasOB) obStart.push({time: bar.time, value: f});
      if (!ob && wasOB) obReversal.push({time: bar.time, value: f});   // bearish exhaustion (▼)
      if (os && !wasOS) osStart.push({time: bar.time, value: s});
      if (!os && wasOS) osReversal.push({time: bar.time, value: s});   // bullish exhaustion (▲)

      wasOB = ob;
      wasOS = os;
    }

    return {fast, slow, obReversal, osReversal, obStart, osStart, threshold: th};
  }

  global.PRTE = {
    VERSION: '1.0.0',
    compute,
  };
})(typeof window !== 'undefined' ? window : globalThis);
