/*!
 * evwma_vwap_macd.js — EVWMA/VWAP MACD oscillator + BUY/SELL crossover signals.
 *
 * A faithful port of QuantNomad's Pine v4 "EVWMA VWAP MACD Strategy"
 * (EVWMA_VWAP_MACD[QN], defaults 30 / 5 / 20):
 *
 *   vol_period = sum(volume, 30)
 *   evwma     := ((vol_period - volume) * nz(evwma[1], close) + volume * close) / vol_period
 *   diff       = vwap - evwma
 *   macd       = ema(diff, 5)      signal = ema(diff, 20)      hist = macd - signal
 *   long  on crossover(macd, signal)      short on crossunder(macd, signal)
 *
 * What it actually measures: EVWMA ("elastic" volume-weighted MA) advances only
 * as fast as traded volume lets it — it is a volume-paced anchor, not a time MA.
 * `diff` is therefore price-vs-volume-anchor in PRICE units, and the MACD on it
 * asks "is price pulling away from where volume has been transacting, faster
 * than it was 20 bars ago?". Zero is meaningful: diff > 0 = price above the
 * volume anchor.
 *
 * ── The VWAP subtlety (the one thing a naive port gets wrong) ────────────────
 * Pine's `vwap` is the SESSION VWAP: it resets every session. On a 1D chart each
 * bar IS its own session, so TradingView's `vwap` collapses to that bar's own
 * hlc3 — which is exactly what the reference chart is plotting. So:
 *   • intraday tf → true session VWAP (cumulative hlc3·vol / vol, reset per day)
 *   • 1d / 1w / 1M → hlc3 of the bar, the exact Pine degenerate case
 * This mirrors the same finding already recorded in chart_dashboard.vwapSeries
 * (daily "session VWAP" measured equal to (H+L+C)/3 on 24 of 24 bars).
 *
 * Causality: every term (rolling volume sum, the EVWMA recursion, Pine EMAs) is
 * backward-looking only, so indexing the returned series at bar t uses nothing
 * after t — the backtest can walk it in one pass without look-ahead.
 *
 * No DOM / charting-library dependency — rendering is the caller's job
 * (chart_dashboard.html), mirroring adx_di.js and percent_r_trend_exhaustion.js.
 *
 * Public API (window.EVMACD):
 *   EVMACD.compute(bars, opts) -> {
 *     evwma, vwap, macd, signal, hist,   // {time,value}[] series
 *     buy, sell,                         // crossover events {time,index,price,hist,histPct}
 *     signals,                           // buy+sell merged, chronological, dir ±1
 *     state,                             // {dir, since, bars} current stance
 *     opts, source                       // echo of settings + 'session'|'hlc3'
 *   }
 * Bar shape: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    sumLength: 30,   // EVWMA volume window   (Pine: sum_length)
    fast: 5,         // "macd" line EMA       (Pine: signal_length1)
    slow: 20,        // "signal" line EMA     (Pine: signal_length2)
    tf: '1d',        // drives the VWAP mode — see header
  };

  const INTRADAY_TFS = new Set(['1m', '5m', '15m', '30m', '1h', '4h']);

  // Pine's ta.ema — seeded with the SMA of the first `len` values, then
  // recursive at alpha = 2/(len+1). Seeding matters: a raw recursive EMA
  // started at the first value drifts from TradingView for ~3·len bars, and
  // this indicator's whole read is a 5-vs-20 EMA distance.
  // NaN inputs (pre-warmup diff) are skipped, never treated as 0.
  function pineEma(src, len) {
    const out = new Array(src.length).fill(NaN);
    const alpha = 2 / (len + 1);
    let prev = null;
    const seed = [];
    for (let i = 0; i < src.length; i++) {
      const x = src[i];
      if (!isFinite(x)) continue;
      if (prev === null) {
        seed.push(x);
        if (seed.length < len) continue;
        prev = seed.reduce((a, b) => a + b, 0) / len;   // SMA seed
      } else {
        prev = alpha * x + (1 - alpha) * prev;
      }
      out[i] = prev;
    }
    return out;
  }

  // VWAP source per the header: session-cumulative intraday, hlc3 on 1d+.
  function vwapSource(bars, tf) {
    const hlc3 = b => (b.high + b.low + b.close) / 3;
    if (!INTRADAY_TFS.has(tf)) return {src: bars.map(hlc3), mode: 'hlc3'};
    const out = new Array(bars.length).fill(NaN);
    let cumPV = 0, cumVol = 0, curDay = null;
    for (let i = 0; i < bars.length; i++) {
      const b = bars[i];
      const day = new Date(b.time * 1000).toISOString().slice(0, 10);
      if (day !== curDay) { curDay = day; cumPV = 0; cumVol = 0; }
      cumPV  += hlc3(b) * (b.volume || 0);
      cumVol += (b.volume || 0);
      // No volume yet → no average yet. Falling back to close here would draw
      // the price line wearing a VWAP label (the bug vwapSeries already fixed).
      if (cumVol > 0) out[i] = cumPV / cumVol;
    }
    return {src: out, mode: 'session'};
  }

  // EVWMA. Emitted only once a FULL sumLength volume window exists — a partial
  // window makes the elastic denominator too small and the anchor jumps.
  function evwmaSeries(bars, sumLength) {
    const out = new Array(bars.length).fill(NaN);
    let roll = 0, prev = null;
    for (let i = 0; i < bars.length; i++) {
      roll += (bars[i].volume || 0);
      if (i >= sumLength) roll -= (bars[i - sumLength].volume || 0);
      if (i < sumLength - 1) continue;
      const v = bars[i].volume || 0;
      // Zero-volume window (holiday feed, dead instrument): the formula divides
      // by it. Hold the previous anchor rather than emitting Infinity.
      if (!(roll > 0)) { out[i] = (prev === null ? NaN : prev); continue; }
      const base = (prev === null) ? bars[i].close : prev;     // Pine nz(evwma[1], close)
      prev = ((roll - v) * base + v * bars[i].close) / roll;
      out[i] = prev;
    }
    return out;
  }

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const empty = {evwma: [], vwap: [], macd: [], signal: [], hist: [],
                   buy: [], sell: [], signals: [], state: null, opts, source: null};
    const need = opts.sumLength + opts.slow + 5;
    if (!bars || bars.length < need) return empty;
    // Volume is not optional here — EVWMA IS the volume term. A feed with no
    // volume would silently degenerate to a flat close line.
    let volSum = 0;
    for (let i = 0; i < bars.length; i++) volSum += (bars[i].volume || 0);
    if (!(volSum > 0)) return empty;

    const vw = vwapSource(bars, opts.tf);
    const vwapArr = vw.src;
    const evwmaArr = evwmaSeries(bars, opts.sumLength);

    const diff = new Array(bars.length).fill(NaN);
    for (let i = 0; i < bars.length; i++) {
      if (isFinite(vwapArr[i]) && isFinite(evwmaArr[i])) diff[i] = vwapArr[i] - evwmaArr[i];
    }
    const macdArr   = pineEma(diff, opts.fast);
    const signalArr = pineEma(diff, opts.slow);

    const evwma = [], vwap = [], macd = [], signal = [], hist = [];
    for (let i = 0; i < bars.length; i++) {
      const t = bars[i].time;
      if (isFinite(evwmaArr[i])) evwma.push({time: t, value: +evwmaArr[i].toFixed(4)});
      if (isFinite(vwapArr[i]))  vwap.push({time: t, value: +vwapArr[i].toFixed(4)});
      if (!isFinite(macdArr[i]) || !isFinite(signalArr[i])) continue;
      macd.push({time: t, value: +macdArr[i].toFixed(4)});
      signal.push({time: t, value: +signalArr[i].toFixed(4)});
      hist.push({time: t, value: +(macdArr[i] - signalArr[i]).toFixed(4)});
    }

    // Crossovers = the strategy's entries. Pine's strategy is stop-and-reverse
    // (always in the market), so every cross is BOTH an exit and an entry.
    const buy = [], sell = [];
    for (let i = 1; i < bars.length; i++) {
      if (![macdArr[i], signalArr[i], macdArr[i - 1], signalArr[i - 1]].every(isFinite)) continue;
      const wasBelow = macdArr[i - 1] <= signalArr[i - 1];
      const isBelow  = macdArr[i] < signalArr[i];
      if (wasBelow === isBelow) continue;               // no cross this bar
      const h = macdArr[i] - signalArr[i];
      const ev = {time: bars[i].time, index: i, price: bars[i].close,
                  macd: +macdArr[i].toFixed(4), signal: +signalArr[i].toFixed(4),
                  hist: +h.toFixed(4),
                  // Separation as % of price — the only cross-symbol-comparable
                  // read of "how decisive was this cross".
                  histPct: bars[i].close > 0 ? +(100 * h / bars[i].close).toFixed(3) : 0};
      (wasBelow ? buy : sell).push(ev);
    }

    const signals = buy.map(e => Object.assign({dir: 1}, e))
      .concat(sell.map(e => Object.assign({dir: -1}, e)))
      .sort((a, b) => a.time - b.time);

    const last = signals.length ? signals[signals.length - 1] : null;
    const state = last ? {dir: last.dir, since: last.time,
                          bars: bars.length - 1 - last.index} : null;

    return {evwma: evwma, vwap: vwap, macd: macd, signal: signal, hist: hist,
            buy: buy, sell: sell, signals: signals, state: state,
            opts: opts, source: vw.mode};
  }

  global.EVMACD = {VERSION: '1.0.0', compute: compute};
})(typeof window !== 'undefined' ? window : globalThis);
