/*!
 * ichimoku.js — Ichimoku Kinko Hyo (one-look equilibrium chart), as a chart overlay.
 *
 * B-46. Pure computation, no DOM and no charting-library dependency, mirroring
 * psar.js / renko.js / supertrend_ai.js. Rendering lives in chart_dashboard.html.
 *
 * ── Why this is an OVERLAY and not a scanner ──────────────────────────────────
 * B-46 specifies: "Ship the overlay first; any BUY/SELL reading is a separate,
 * measured question." The five lines are arithmetic; the signals they produce
 * (TK cross, Kumo breakout, Chikou confirmation) are claims that nobody here has
 * measured, and this desk does not ship unmeasured claims as triggers.
 *
 * ── The five components, stated so the parameters are not quietly invented ────
 *   Tenkan-sen  (conversion line)  = midpoint of highest high and lowest low over 9 bars
 *   Kijun-sen   (base line)        = midpoint of highest high and lowest low over 26 bars
 *   Senkou A    (leading span A)   = (Tenkan + Kijun) / 2, plotted 26 bars AHEAD
 *   Senkou B    (leading span B)   = midpoint of highest high and lowest low over 52,
 *                                     plotted 26 bars AHEAD
 *   Chikou Span (lagging span)     = close, plotted 26 bars BEHIND
 *
 * The 9/26/52 are Hosoda's originals (1968, from the Japanese trading week).
 * Every number here is named rather than inlined.
 *
 * ── The forward shift is the non-trivial part ─────────────────────────────────
 * Senkou A and B are displaced FORWARD by `displacement` bars (default 26).
 * Their last computed value sits 26 bars into the future — past the current bar.
 * The caller is responsible for extending the time axis (padSeries / whitespace)
 * to show these projected points. Chikou is displaced backward: its last value
 * sits at bar[n - displacement], and the most recent `displacement` bars have
 * no Chikou point.
 *
 * NOT ADVICE. The lines are arithmetic, shown so they can be checked.
 *
 * Public API (window.ICHIMOKU):
 *   ICHIMOKU.compute(bars, opts) -> {tenkan, kijun, senkouA, senkouB, chikou,
 *                                    kumoUp, kumoDn, state, opts}
 *
 * Bar shape expected: {time, open, high, low, close}
 */
(function (global) {
  'use strict';

  const TENKAN_PERIOD = 9;
  const KIJUN_PERIOD = 26;
  const SENKOU_B_PERIOD = 52;
  const DISPLACEMENT = 26;

  function midpoint(bars, end, period) {
    let hi = -Infinity, lo = Infinity;
    const start = Math.max(0, end - period + 1);
    for (let i = start; i <= end; i++) {
      if (bars[i].high > hi) hi = bars[i].high;
      if (bars[i].low < lo) lo = bars[i].low;
    }
    return +(((hi + lo) / 2).toFixed(4));
  }

  function compute(bars, opts) {
    opts = opts || {};
    const tenkanP = opts.tenkanPeriod != null ? opts.tenkanPeriod : TENKAN_PERIOD;
    const kijunP = opts.kijunPeriod != null ? opts.kijunPeriod : KIJUN_PERIOD;
    const senkouBP = opts.senkouBPeriod != null ? opts.senkouBPeriod : SENKOU_B_PERIOD;
    const disp = opts.displacement != null ? opts.displacement : DISPLACEMENT;

    const tenkan = [], kijun = [], senkouA = [], senkouB = [], chikou = [];
    const kumoUp = [], kumoDn = [];

    if (!bars || bars.length < 2) {
      return {tenkan, kijun, senkouA, senkouB, chikou, kumoUp, kumoDn,
              state: null, opts: {tenkanP, kijunP, senkouBP, disp}};
    }

    const rawTenkan = new Array(bars.length);
    const rawKijun = new Array(bars.length);
    const rawSenkouA = new Array(bars.length);
    const rawSenkouB = new Array(bars.length);

    for (let i = 0; i < bars.length; i++) {
      rawTenkan[i] = i >= tenkanP - 1 ? midpoint(bars, i, tenkanP) : null;
      rawKijun[i] = i >= kijunP - 1 ? midpoint(bars, i, kijunP) : null;
      rawSenkouB[i] = i >= senkouBP - 1 ? midpoint(bars, i, senkouBP) : null;

      if (rawTenkan[i] != null && rawKijun[i] != null) {
        rawSenkouA[i] = +((rawTenkan[i] + rawKijun[i]) / 2).toFixed(4);
      } else {
        rawSenkouA[i] = null;
      }
    }

    for (let i = 0; i < bars.length; i++) {
      if (rawTenkan[i] != null) {
        tenkan.push({time: bars[i].time, value: rawTenkan[i]});
      }
      if (rawKijun[i] != null) {
        kijun.push({time: bars[i].time, value: rawKijun[i]});
      }
    }

    // Chikou: close plotted `disp` bars behind.
    for (let i = 0; i < bars.length; i++) {
      const target = i - disp;
      if (target >= 0) {
        chikou.push({time: bars[target].time, value: +bars[i].close.toFixed(4)});
      }
    }

    // Senkou A and B: plotted `disp` bars ahead.
    // For bars within the data range, use the future bar's time.
    // For bars beyond the data range (projected into the future), generate
    // synthetic timestamps. The caller's padSeries / chart whitespace handles
    // the rest.
    const lastTime = bars[bars.length - 1].time;
    function futureTime(offset) {
      // Timestamps are either epoch seconds (number) or 'YYYY-MM-DD' strings.
      if (typeof lastTime === 'number') {
        return lastTime + offset * 86400;
      }
      const d = new Date(lastTime);
      d.setDate(d.getDate() + offset);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    }

    for (let i = 0; i < bars.length; i++) {
      const targetIdx = i + disp;
      const time = targetIdx < bars.length
        ? bars[targetIdx].time
        : futureTime(targetIdx - bars.length + 1);

      if (rawSenkouA[i] != null) {
        senkouA.push({time, value: rawSenkouA[i]});
      }
      if (rawSenkouB[i] != null) {
        senkouB.push({time, value: rawSenkouB[i]});
      }

      // Cloud colour series: split by which span leads, for the filled kumo.
      if (rawSenkouA[i] != null && rawSenkouB[i] != null) {
        if (rawSenkouA[i] >= rawSenkouB[i]) {
          kumoUp.push({time, value: rawSenkouA[i], base: rawSenkouB[i]});
        } else {
          kumoDn.push({time, value: rawSenkouB[i], base: rawSenkouA[i]});
        }
      }
    }

    // State at the last bar: where price sits relative to the cloud and lines.
    const lastBar = bars[bars.length - 1];
    const lastTenkan = rawTenkan[bars.length - 1];
    const lastKijun = rawKijun[bars.length - 1];
    const cloudA = rawSenkouA[bars.length - 1 - disp];
    const cloudB = rawSenkouB[bars.length - 1 - disp];
    let priceVsCloud = null;
    if (cloudA != null && cloudB != null) {
      const cloudTop = Math.max(cloudA, cloudB);
      const cloudBot = Math.min(cloudA, cloudB);
      if (lastBar.close > cloudTop) priceVsCloud = 'above';
      else if (lastBar.close < cloudBot) priceVsCloud = 'below';
      else priceVsCloud = 'inside';
    }
    let tkCross = null;
    if (lastTenkan != null && lastKijun != null) {
      tkCross = lastTenkan > lastKijun ? 'bullish' : lastTenkan < lastKijun ? 'bearish' : 'flat';
    }

    return {
      tenkan, kijun, senkouA, senkouB, chikou, kumoUp, kumoDn,
      state: {
        tenkan: lastTenkan, kijun: lastKijun,
        cloudA, cloudB, priceVsCloud, tkCross,
      },
      opts: {tenkanP, kijunP, senkouBP, disp},
    };
  }

  global.ICHIMOKU = {
    VERSION: '1.0.0', compute,
    TENKAN_PERIOD, KIJUN_PERIOD, SENKOU_B_PERIOD, DISPLACEMENT,
  };
})(typeof window !== 'undefined' ? window : globalThis);
