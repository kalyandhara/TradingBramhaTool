/*!
 * adx_di.js — Wilder's ADX with +DI / −DI directional lines, plain JS.
 *
 * A faithful port of tools/scanner_templates.py `_adx_di_series` so the chart
 * subchart and the Python scanner agree bar-for-bar: Wilder smoothing is
 * ewm(alpha=1/n, adjust=False) — a recursive RMA seeded at the first value.
 *
 * ADX is trend STRENGTH (0–100, direction-agnostic); +DI/−DI carry direction.
 * Per the measured evidence on concepts/ADX.md, DI crosses are LAGGING
 * confirmation, not standalone entries — so this module returns the cross events
 * for context/markers, deliberately labelled as bias/confirmation, not "buy/sell".
 *
 * No DOM / charting-library dependency — rendering is the caller's job
 * (chart_dashboard.html), mirroring percent_r_trend_exhaustion.js.
 *
 * Public API (window.ADXDI):
 *   ADXDI.compute(bars, opts) -> {
 *     adx, plusDI, minusDI,     // {time,value}[] line series (0–100)
 *     bullCross, bearCross,     // +DI/−DI crossover events {time,value}
 *     threshold, chopBelow,     // 25 (trend gate) and 20 (chop floor)
 *   }
 * Bar shape: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    length: 14,       // Wilder default; do NOT tune to fit history (curve-fitting)
    threshold: 25,    // ADX ≥ 25 = actionable trend (see concepts/ADX.md)
    chopBelow: 20,    // ADX < 20 = chop, DI crosses here are noise
  };

  // Wilder's RMA = pandas ewm(alpha, adjust=False): seed at first finite value,
  // then prev += alpha*(x-prev); leading NaN carried until the first finite x.
  function wilderRMA(arr, alpha) {
    const out = new Array(arr.length).fill(NaN);
    let prev = null;
    for (let i = 0; i < arr.length; i++) {
      const x = arr[i];
      if (!isFinite(x)) { out[i] = (prev === null ? NaN : prev); continue; }
      prev = (prev === null) ? x : prev + alpha * (x - prev);
      out[i] = prev;
    }
    return out;
  }

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const n = opts.length, alpha = 1 / n;
    const empty = {adx: [], plusDI: [], minusDI: [], bullCross: [], bearCross: [],
                   threshold: opts.threshold, chopBelow: opts.chopBelow};
    if (!bars || bars.length < 2 * n + 5) return empty;

    const m = bars.length;
    const tr = new Array(m), plusDM = new Array(m), minusDM = new Array(m);
    for (let i = 0; i < m; i++) {
      const b = bars[i];
      if (i === 0) {
        tr[0] = b.high - b.low;          // no prior close → TR = H−L
        plusDM[0] = 0; minusDM[0] = 0;   // no prior H/L → DM = 0
        continue;
      }
      const p = bars[i - 1];
      tr[i] = Math.max(b.high - b.low, Math.abs(b.high - p.close), Math.abs(b.low - p.close));
      const up = b.high - p.high, down = p.low - b.low;
      plusDM[i]  = (up > down && up > 0) ? up : 0;
      minusDM[i] = (down > up && down > 0) ? down : 0;
    }

    const atr = wilderRMA(tr, alpha);
    const sPlus = wilderRMA(plusDM, alpha);
    const sMinus = wilderRMA(minusDM, alpha);

    const plusDI = [], minusDI = [], adx = [], dx = new Array(m).fill(NaN);
    const pdiRaw = new Array(m).fill(NaN), mdiRaw = new Array(m).fill(NaN);
    for (let i = 0; i < m; i++) {
      if (!(atr[i] > 0)) continue;
      const pdi = 100 * sPlus[i] / atr[i];
      const mdi = 100 * sMinus[i] / atr[i];
      pdiRaw[i] = pdi; mdiRaw[i] = mdi;
      const sum = pdi + mdi;
      dx[i] = sum > 0 ? 100 * Math.abs(pdi - mdi) / sum : NaN;
      // Emit DI lines once the directional smoothing has settled (i ≥ n).
      if (i >= n) {
        plusDI.push({time: bars[i].time, value: +pdi.toFixed(2)});
        minusDI.push({time: bars[i].time, value: +mdi.toFixed(2)});
      }
    }
    const adxRaw = wilderRMA(dx, alpha);
    for (let i = 2 * n; i < m; i++) {   // ADX needs a double warm-up to settle
      if (isFinite(adxRaw[i])) adx.push({time: bars[i].time, value: +adxRaw[i].toFixed(2)});
    }

    // +DI/−DI crossovers — bias/confirmation events, not triggers (see header).
    const bullCross = [], bearCross = [];
    for (let i = n + 1; i < m; i++) {
      if (![pdiRaw[i], mdiRaw[i], pdiRaw[i - 1], mdiRaw[i - 1]].every(isFinite)) continue;
      const wasBelow = pdiRaw[i - 1] <= mdiRaw[i - 1];
      if (wasBelow && pdiRaw[i] > mdiRaw[i]) bullCross.push({time: bars[i].time, value: +pdiRaw[i].toFixed(2)});
      if (!wasBelow && pdiRaw[i] < mdiRaw[i]) bearCross.push({time: bars[i].time, value: +mdiRaw[i].toFixed(2)});
    }

    return {adx, plusDI, minusDI, bullCross, bearCross,
            threshold: opts.threshold, chopBelow: opts.chopBelow};
  }

  global.ADXDI = {VERSION: '1.0.0', compute};
})(typeof window !== 'undefined' ? window : globalThis);
