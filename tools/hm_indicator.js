/*!
 * hm_indicator.js — HM Bottoms & Tops (Hilega Milega, reworked).
 *
 * A single-pane momentum composite that flags likely NEAR-bottoms and NEAR-tops
 * by stacking three views of the same short RSI, plus a price-trend gate:
 *
 *   • RSI(9)            — the black "strength" line (0..100). OB/OS collapse to
 *                         the 50 midline, so RSI is read as a regime line:
 *                         >50 = strength up, <50 = strength down.
 *   • EMA(3) of RSI     — the green "momentum" line: direction/slope of strength.
 *   • VWMA(21) of RSI   — the red "volume-adjusted strength" line.
 *   • EMA(34) of price  — trend context (NOT plotted in the 0..100 pane; used as
 *                         an optional signal gate + exposed for a main-chart overlay).
 *
 * ── What changed vs the source (and why) ─────────────────────────────────────
 * The original HM calls its red line a "WMA of RSI" and markets it as the
 * "volume" component. A plain WMA of the RSI line carries NO volume information
 * (see the wiki note on the HM indicator). This port honors the *intent* by
 * making the red line a TRUE VWMA — each RSI value weighted by that bar's
 * volume — so it genuinely is volume-adjusted strength. On zero-volume feeds
 * (some indices) it falls back to a plain mean of the RSI window so the line
 * still renders. The source's "green stays above RSI at a bottom" description is
 * self-contradictory (an EMA of RSI lags RSI on an upturn); this port uses the
 * coherent reading instead: RSI reclaims 50, its EMA is rising, and the slower
 * VWMA is still below 50 (the move is early, not yet exhausted).
 *
 * ── Signals (all on CLOSED bars — no look-ahead) ─────────────────────────────
 *   Bull early  : RSI crosses ABOVE 50, EMA(RSI) rising, VWMA(RSI) still < 50.
 *   Bull confirm: after an early setup, VWMA(RSI) crosses ABOVE 50 (leaves the
 *                 band). Optional trend gate: close > EMA(34).
 *   Exit long   : RSI crosses back BELOW 50 (momentum lost).
 *   Tops are the exact mirror.
 * "Speed" = the vertical spread between the three lines; a wide fan = a fast move.
 *
 * NOT ADVICE. These are interpretive momentum rules, not a measured edge; the
 * source's ~70-75% "accuracy" is an unbacktested promotional claim. Treat the
 * signals as a hypothesis to backtest (the `signals` array is provided exactly so
 * a harness can). Rendering lives in chart_dashboard.html (the `hm` sub-pane block);
 * this module is pure computation, mirroring percent_r_trend_exhaustion.js.
 *
 * Public API (window.HM):
 *   HM.compute(bars, opts) -> {
 *     rsi, emaRsi, vwmaRsi,        // {time,value}[] — the three oscillator lines
 *     priceEma,                    // {time,value}[] — EMA(34) of close (overlay-ready)
 *     bullEarly, bearEarly,        // setup warnings (the 50-cross)
 *     bullConfirm, bearConfirm,    // confirmed reversals (VWMA leaves the band)
 *     exitLong, exitShort,         // momentum-fade exits
 *     signals,                     // flat, time-sorted [{time,type,price,side}] for backtests
 *     midline, opts                // echoed for guide-line drawing / introspection
 *   }
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    rsiLength:      9,      // short RSI = "strength"
    emaLength:      3,      // EMA of RSI = "momentum" (green)
    vwmaLength:     21,     // VWMA of RSI = "volume-adjusted strength" (red)
    priceEmaLength: 34,     // EMA of price = "trend"
    midline:        50,     // the collapsed OB/OS level = the "strength band" edge
    primeWindow:    10,     // bars an early setup stays valid awaiting confirmation
    useTrendFilter: false,  // gate confirmations on close vs EMA(34); off by default
                            // (a genuine bottom usually prints BELOW the trend MA)
    entryOn:        'confirm', // 'confirm' | 'early' — which event populates `signals`
  };

  // ── Wilder RSI aligned to bars (null during warm-up) ─────────────────────────
  // Same formula/neutral-50 handling as chart_dashboard.html's rsiSeries so the
  // black line here means exactly what the standalone RSI pane means.
  function rsiAligned(bars, length) {
    const n = bars.length;
    const out = new Array(n).fill(null);
    if (n < length + 1) return out;
    const alpha = 1 / length;
    let avgGain = 0, avgLoss = 0;
    for (let i = 1; i < n; i++) {
      const diff = bars[i].close - bars[i - 1].close;
      const gain = diff > 0 ?  diff : 0;
      const loss = diff < 0 ? -diff : 0;
      avgGain = alpha * gain + (1 - alpha) * avgGain;
      avgLoss = alpha * loss + (1 - alpha) * avgLoss;
      if (i < length) continue;                       // warm-up
      if (avgGain === 0 && avgLoss === 0)      out[i] = 50;   // flat → neutral
      else if (avgLoss === 0)                  out[i] = 100;
      else                                     out[i] = 100 - 100 / (1 + avgGain / avgLoss);
    }
    return out;
  }

  // ── EMA of an aligned (nullable) series; contiguous once past warm-up ────────
  function emaAligned(src, period) {
    const n = src.length;
    const out = new Array(n).fill(null);
    const k = 2 / (period + 1);
    let prev = null, seen = 0, seed = 0, firstIdx = -1;
    for (let i = 0; i < n; i++) {
      if (src[i] === null) continue;
      if (prev === null) {
        if (firstIdx < 0) firstIdx = i;
        seed += src[i]; seen++;
        if (seen === period) { prev = seed / period; out[i] = prev; }   // SMA seed
        continue;
      }
      prev = src[i] * k + prev * (1 - k);
      out[i] = prev;
    }
    return out;
  }

  // ── VWMA of an aligned RSI series, weighted by bar volume (rolling window) ────
  // Falls back to a plain window mean when the window carries no volume, so the
  // red line renders on volumeless feeds too. O(n): each index enters/leaves once.
  function vwmaAligned(src, bars, period) {
    const n = src.length;
    const out = new Array(n).fill(null);
    let wv = 0, wsum = 0, plain = 0, cnt = 0;   // volume-weighted + plain accumulators
    const idxs = [];                            // indices currently in the window
    for (let i = 0; i < n; i++) {
      if (src[i] === null) continue;
      const vol = Number(bars[i].volume) || 0;
      idxs.push(i);
      wv += src[i] * vol; wsum += vol;
      plain += src[i];    cnt++;
      if (idxs.length > period) {                // evict oldest
        const j = idxs.shift();
        const vj = Number(bars[j].volume) || 0;
        wv -= src[j] * vj; wsum -= vj;
        plain -= src[j];   cnt--;
      }
      if (idxs.length === period) {
        out[i] = wsum > 0 ? wv / wsum : plain / cnt;   // volume-weighted, else plain
      }
    }
    return out;
  }

  // ── EMA of price (close), aligned to bars ────────────────────────────────────
  function priceEmaAligned(bars, period) {
    const n = bars.length;
    const out = new Array(n).fill(null);
    const k = 2 / (period + 1);
    let prev = null;
    for (let i = 0; i < n; i++) {
      const c = bars[i].close;
      if (prev === null) {
        if (i === period - 1) {
          let sum = 0; for (let j = 0; j <= i; j++) sum += bars[j].close;
          prev = sum / period; out[i] = prev;
        }
        continue;
      }
      prev = c * k + prev * (1 - k);
      out[i] = prev;
    }
    return out;
  }

  // Aligned array -> {time,value}[] (drops warm-up nulls).
  function toSeries(bars, arr) {
    const out = [];
    for (let i = 0; i < arr.length; i++) if (arr[i] !== null) out.push({ time: bars[i].time, value: arr[i] });
    return out;
  }

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const empty = {
      rsi: [], emaRsi: [], vwmaRsi: [], priceEma: [],
      bullEarly: [], bearEarly: [], bullConfirm: [], bearConfirm: [],
      exitLong: [], exitShort: [], signals: [], midline: opts.midline, opts,
    };
    const need = opts.rsiLength + opts.vwmaLength + 2;
    if (!bars || bars.length < need) return empty;

    const rsiA   = rsiAligned(bars, opts.rsiLength);
    const emaA   = emaAligned(rsiA, opts.emaLength);
    const vwmaA  = vwmaAligned(rsiA, bars, opts.vwmaLength);
    const priceA = priceEmaAligned(bars, opts.priceEmaLength);

    const mid = opts.midline;
    const bullEarly = [], bearEarly = [], bullConfirm = [], bearConfirm = [];
    const exitLong = [], exitShort = [], signals = [];
    let primeLong = 0, primeShort = 0;   // bars-remaining an early setup stays live

    for (let i = 1; i < bars.length; i++) {
      const r0 = rsiA[i - 1], r1 = rsiA[i];
      const e0 = emaA[i - 1], e1 = emaA[i];
      const v0 = vwmaA[i - 1], v1 = vwmaA[i];
      if (r0 === null || r1 === null || e0 === null || e1 === null || v0 === null || v1 === null) continue;

      const t = bars[i].time, px = bars[i].close;
      const rsiCrossUp = r0 <= mid && r1 > mid;
      const rsiCrossDn = r0 >= mid && r1 < mid;
      const emaRising  = e1 > e0;
      const emaFalling = e1 < e0;
      const vwmaCrossUp = v0 <  mid && v1 >= mid;
      const vwmaCrossDn = v0 >  mid && v1 <= mid;
      const trendUp   = priceA[i] === null || px > priceA[i];
      const trendDown = priceA[i] === null || px < priceA[i];

      if (primeLong  > 0) primeLong--;
      if (primeShort > 0) primeShort--;

      // ── Bottom (bullish) ──────────────────────────────────────────────────
      if (rsiCrossUp && emaRising && v1 < mid) {        // early setup: strength turning, VWMA still low
        bullEarly.push({ time: t, value: r1 });
        primeLong = opts.primeWindow;
        if (opts.entryOn === 'early') signals.push({ time: t, type: 'entryLong', side: 1, price: px });
      }
      if (primeLong > 0 && vwmaCrossUp && (!opts.useTrendFilter || trendUp)) {   // confirmation: VWMA leaves band up
        bullConfirm.push({ time: t, value: v1 });
        primeLong = 0;
        if (opts.entryOn === 'confirm') signals.push({ time: t, type: 'entryLong', side: 1, price: px });
      }
      if (rsiCrossDn) { exitLong.push({ time: t, value: r1 }); signals.push({ time: t, type: 'exitLong', side: 0, price: px }); }

      // ── Top (bearish) ─────────────────────────────────────────────────────
      if (rsiCrossDn && emaFalling && v1 > mid) {
        bearEarly.push({ time: t, value: r1 });
        primeShort = opts.primeWindow;
        if (opts.entryOn === 'early') signals.push({ time: t, type: 'entryShort', side: -1, price: px });
      }
      if (primeShort > 0 && vwmaCrossDn && (!opts.useTrendFilter || trendDown)) {
        bearConfirm.push({ time: t, value: v1 });
        primeShort = 0;
        if (opts.entryOn === 'confirm') signals.push({ time: t, type: 'entryShort', side: -1, price: px });
      }
      if (rsiCrossUp) { exitShort.push({ time: t, value: r1 }); signals.push({ time: t, type: 'exitShort', side: 0, price: px }); }
    }

    signals.sort((a, b) => (a.time > b.time ? 1 : a.time < b.time ? -1 : 0));

    return {
      rsi: toSeries(bars, rsiA),
      emaRsi: toSeries(bars, emaA),
      vwmaRsi: toSeries(bars, vwmaA),
      priceEma: toSeries(bars, priceA),
      bullEarly, bearEarly, bullConfirm, bearConfirm,
      exitLong, exitShort, signals,
      midline: mid, opts,
    };
  }

  global.HM = { VERSION: '1.0.0', compute };
})(typeof window !== 'undefined' ? window : globalThis);
