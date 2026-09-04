/*!
 * supertrend_ai.js — Adaptive-factor SuperTrend (window.STAI).
 *
 * An ORIGINAL implementation of the "adaptive SuperTrend via K-means clustering"
 * technique popularised by LuxAlgo's "SuperTrend AI (Clustering)". This is a
 * clean-room reimplementation of the documented METHOD — not a port of LuxAlgo's
 * Pine source (which is CC BY-NC-SA 4.0). Credit: technique © LuxAlgo. See the
 * wiki concept "Adaptive SuperTrend (K-means Clustering)".
 *
 * The idea: instead of one fixed ATR multiple (as in PMax), run a SuperTrend at
 * many factors, score each factor on how well its trend side predicted the next
 * bar, K-means-cluster those scores into Best / Average / Worst, and drive the
 * live trailing stop with the average factor of the chosen cluster. The line
 * flips side + colour on a trend change (the signal), and a 0..1 performance
 * index grades each flip.
 *
 * Rendering (switching line, flip markers) lives in chart_dashboard.html; this
 * module is pure computation, mirroring hm_indicator.js / percent_r_trend_exhaustion.js.
 *
 * NOT ADVICE. Still a lagging trend indicator: it confirms trends late, whipsaws
 * in ranges, and live factor-selection is in-sample tuning that can overfit the
 * recent regime. Read on closed bars. Unmeasured — backtest before relying on it.
 *
 * Public API (window.STAI):
 *   STAI.compute(bars, opts) -> {
 *     trail,                 // {time,value,dir}[] adaptive trailing stop (dir 1=up/below price, 0=down/above)
 *     up, dn,                // {time,value}[] the trail split by dir, for a colour-switching line
 *     signals,               // flip bars: {time, dir, price, stop, perf, strength}  (strength 0..10)
 *     perfIndex,             // {time,value}[] 0..~1 performance index (candle-gradient ready)
 *     factorLine,            // {time,value}[] the chosen adaptive factor over time
 *     last,                  // {dir, factor, perf, cluster} snapshot for an info panel
 *     opts
 *   }
 *
 * Bar shape: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    atrLen:      10,
    minMult:     1,
    maxMult:     5,
    step:        0.5,
    perfAlpha:   10,          // performance-memory (higher = smoother/slower)
    fromCluster: 'Best',      // 'Best' | 'Average' | 'Worst'
    maxIter:     30,          // k-means iterations (converges in a few)
  };

  // Wilder ATR, one value per bar (NaN through warm-up), matching pmaxSeries.
  function atrSeries(bars, len) {
    const n = bars.length, out = new Array(n).fill(NaN);
    let prevClose = null, atr = null;
    for (let i = 0; i < n; i++) {
      const b = bars[i];
      const tr = prevClose === null ? (b.high - b.low)
        : Math.max(b.high - b.low, Math.abs(b.high - prevClose), Math.abs(b.low - prevClose));
      if (i < len) {
        atr = atr === null ? tr : atr + tr;           // running sum for the seed
        if (i === len - 1) { atr /= len; out[i] = atr; }
      } else {
        atr = (atr * (len - 1) + tr) / len;           // Wilder smoothing
        out[i] = atr;
      }
      prevClose = b.close;
    }
    return out;
  }

  // 1-D K-means for k=3, seeded at the 25/50/75 percentiles. Returns the cluster
  // assignment per input value and the (ascending) centroids, so cluster 2 = the
  // "best" (highest-score) group, 1 = average, 0 = worst.
  function kmeans3(values, maxIter) {
    const sorted = values.slice().sort((a, b) => a - b);
    const pct = q => {
      const idx = (sorted.length - 1) * q, lo = Math.floor(idx), hi = Math.ceil(idx);
      return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
    };
    let cent = [pct(0.25), pct(0.50), pct(0.75)];
    let assign = new Array(values.length).fill(1);
    for (let it = 0; it < maxIter; it++) {
      // assign
      for (let i = 0; i < values.length; i++) {
        let best = 0, bestD = Infinity;
        for (let c = 0; c < 3; c++) {
          const d = Math.abs(values[i] - cent[c]);
          if (d < bestD) { bestD = d; best = c; }
        }
        assign[i] = best;
      }
      // update
      const sum = [0, 0, 0], cnt = [0, 0, 0];
      for (let i = 0; i < values.length; i++) { sum[assign[i]] += values[i]; cnt[assign[i]]++; }
      const next = cent.slice();
      let moved = false;
      for (let c = 0; c < 3; c++) {
        if (cnt[c] > 0) { const m = sum[c] / cnt[c]; if (m !== cent[c]) moved = true; next[c] = m; }
      }
      cent = next;
      if (!moved) break;
    }
    return { assign, centroids: cent };
  }

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const empty = { trail: [], up: [], dn: [], signals: [], perfIndex: [], factorLine: [], last: null, opts };
    const n = bars ? bars.length : 0;
    if (!bars || n < opts.atrLen + 5 || opts.minMult > opts.maxMult) return empty;

    const factors = [];
    for (let f = opts.minMult; f <= opts.maxMult + 1e-9; f += opts.step) factors.push(+f.toFixed(6));
    if (factors.length < 3) { factors.length = 0; factors.push(opts.minMult, (opts.minMult + opts.maxMult) / 2, opts.maxMult); }

    const atr = atrSeries(bars, opts.atrLen);
    const k = 2 / (opts.perfAlpha + 1);
    const fromIdx = opts.fromCluster === 'Best' ? 2 : opts.fromCluster === 'Worst' ? 0 : 1;

    // Per-factor SuperTrend state.
    const st = factors.map(f => ({ upper: null, lower: null, trend: 0, perf: 0, output: null, factor: f }));
    // Live adaptive state.
    let aUpper = null, aLower = null, aOs = 0, targetFactor = factors[Math.floor(factors.length / 2)];
    let denEma = null;   // EMA of |Δclose| for the performance-index denominator

    const trail = [], up = [], dn = [], signals = [], perfIndex = [], factorLine = [];
    let prevOs = null, lastCluster = null;

    for (let i = 0; i < n; i++) {
      const b = bars[i];
      const hl2 = (b.high + b.low) / 2;
      const a = atr[i];
      const cPrev = i > 0 ? bars[i - 1].close : b.close;
      const dClose = b.close - cPrev;
      denEma = denEma === null ? Math.abs(dClose) : denEma + k * (Math.abs(dClose) - denEma);
      if (isNaN(a)) continue;   // warm-up

      // Update every factor's SuperTrend + its performance score.
      for (const s of st) {
        const upB = hl2 + a * s.factor, dnB = hl2 - a * s.factor;
        if (s.upper === null) { s.upper = upB; s.lower = dnB; s.output = hl2; }
        s.trend = b.close > s.upper ? 1 : b.close < s.lower ? 0 : s.trend;
        s.upper = cPrev < s.upper ? Math.min(upB, s.upper) : upB;
        s.lower = cPrev > s.lower ? Math.max(dnB, s.lower) : dnB;
        const diff = Math.sign(cPrev - s.output) || 0;   // did the factor's line sit below/above prior close
        s.perf += k * (dClose * diff - s.perf);          // reward agreement with the next move
        s.output = s.trend === 1 ? s.lower : s.upper;
      }

      // Cluster the factor scores, pick the chosen cluster's mean factor.
      const perfs = st.map(s => s.perf);
      const { assign } = kmeans3(perfs, opts.maxIter);
      let fSum = 0, fCnt = 0, pSum = 0;
      for (let j = 0; j < st.length; j++) if (assign[j] === fromIdx) { fSum += st[j].factor; pSum += perfs[j]; fCnt++; }
      if (fCnt > 0) targetFactor = fSum / fCnt;
      lastCluster = { size: fCnt, from: opts.fromCluster };
      const perfIdxVal = denEma > 0 ? Math.max(fCnt > 0 ? pSum / fCnt : 0, 0) / denEma : 0;

      // Live adaptive SuperTrend with the chosen factor.
      const upB = hl2 + a * targetFactor, dnB = hl2 - a * targetFactor;
      if (aUpper === null) { aUpper = upB; aLower = dnB; }
      aUpper = cPrev < aUpper ? Math.min(upB, aUpper) : upB;
      aLower = cPrev > aLower ? Math.max(dnB, aLower) : dnB;
      aOs = b.close > aUpper ? 1 : b.close < aLower ? 0 : aOs;
      const ts = aOs ? aLower : aUpper;

      trail.push({ time: b.time, value: ts, dir: aOs });
      (aOs ? up : dn).push({ time: b.time, value: ts });
      perfIndex.push({ time: b.time, value: +perfIdxVal.toFixed(4) });
      factorLine.push({ time: b.time, value: +targetFactor.toFixed(3) });

      if (prevOs !== null && aOs !== prevOs) {
        signals.push({
          time: b.time, dir: aOs, price: b.close, stop: ts,
          perf: +perfIdxVal.toFixed(3),
          strength: Math.max(0, Math.min(10, Math.round(perfIdxVal * 10))),
        });
      }
      prevOs = aOs;
    }

    const last = trail.length
      ? { dir: aOs, factor: +targetFactor.toFixed(2),
          perf: perfIndex.length ? perfIndex[perfIndex.length - 1].value : 0,
          cluster: lastCluster }
      : null;

    return { trail, up, dn, signals, perfIndex, factorLine, last, opts };
  }

  global.STAI = { VERSION: '1.0.0', compute };
})(typeof window !== 'undefined' ? window : globalThis);
