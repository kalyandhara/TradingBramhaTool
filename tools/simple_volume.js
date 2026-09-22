/* simple_volume.js — Simple Volume with Pocket Pivots.
 *
 * INDEPENDENT IMPLEMENTATION from the published DESCRIPTION of "Simple Volume
 * with Pocket Pivots" by finallynitin (TradingView, in.tradingview.com/v/JkB0iCFp).
 * **That script is protected source — no Pine code was available and none was
 * copied.** Everything here is written from the author's own prose, which states
 * the rules precisely enough to implement. The quoted rules, the author's own
 * correction to them, and the features deliberately NOT built are recorded in
 * trading-wiki/wiki/sources/Simple-Volume-Pocket-Pivots-TradingView.md.
 *
 * Why it is worth having next to the plain volume histogram: the idea is
 * SUBTRACTIVE. Ordinary volume draws every bar alike and leaves the reader to
 * compare each one against a moving-average line by eye. This colours the four
 * bars that mean something and greys the rest — so "below average" needs no line
 * to read, because the colour IS the comparison. The MA is intentionally not
 * drawn.
 *
 *   BLUE    Pocket Pivot Volume — an UP day whose volume exceeds the highest
 *           volume of any DOWN day within the last `ppvLen` TRADING days.
 *   GREEN   up day, volume above the volume MA
 *   RED     down day, volume above the volume MA
 *   ORANGE  "dry" volume — at or below MA / dryFrac
 *   GREY    everything else: noise, and deliberately unremarkable
 *
 * NOTHING here is measured on this desk. No forward-return study backs these
 * colours, and the card says so.
 */
(function (global) {
  'use strict';

  const DEFAULTS = {
    maLen: 50,     // volume moving average — the author's default
    ppvLen: 10,    // pocket-pivot lookback, in TRADING days (see below)
    dryFrac: 5,    // dry volume = MA / 5
    colors: {
      ppv:   'rgba(47,129,247,0.95)',
      up:    'rgba(38,166,154,0.85)',
      down:  'rgba(239,83,80,0.85)',
      dry:   'rgba(230,145,56,0.95)',
      noise: 'rgba(120,130,140,0.55)',
    },
  };

  /** Classify every bar. Returns one row per bar: {time, value, kind, ma, color}. */
  function classify(bars, cfg) {
    const c = Object.assign({}, DEFAULTS, cfg || {});
    const out = [];
    let sum = 0;
    for (let i = 0; i < bars.length; i++) {
      const v = bars[i].volume || 0;
      sum += v;
      if (i >= c.maLen) sum -= (bars[i - c.maLen].volume || 0);
      // The average is undefined until its window is FULL. An IPO with 12 bars
      // has no 50-day average, and inventing one from 12 would colour its whole
      // history against a number that does not exist yet.
      const ma = i >= c.maLen - 1 ? sum / c.maLen : null;
      const up = bars[i].close >= bars[i].open;

      let kind = 'noise';
      if (ma !== null && v <= ma / c.dryFrac) {
        kind = 'dry';
      } else if (up) {
        // The lookback is `ppvLen` TRADING days and we take the down days inside
        // it — NOT the last `ppvLen` down days however far back they run. The
        // author corrected his own wording on this point.
        let hiDown = 0;
        for (let j = Math.max(0, i - c.ppvLen); j < i; j++) {
          if (bars[j].close < bars[j].open) hiDown = Math.max(hiDown, bars[j].volume || 0);
        }
        // With no down day in the window there is nothing to beat. We call that
        // "up", not a pivot: the signal is meant to say buyers overwhelmed the
        // recent selling, and ten straight up days contain no selling to
        // overwhelm. Treating an empty comparison as passed would paint the
        // strongest part of a runup blue on no evidence.
        if (hiDown > 0 && v > hiDown) kind = 'ppv';
        else if (ma !== null && v > ma) kind = 'up';
      } else if (ma !== null && v > ma) {
        kind = 'down';
      }
      out.push({time: bars[i].time, value: v, kind, ma, color: c.colors[kind]});
    }
    return out;
  }

  /** The readout for the card. `rvol` is today as a percentage of its own
   *  average — 200% is twice normal — and is null while the MA is still
   *  filling rather than a number computed from a partial window. */
  function stats(rows) {
    if (!rows || !rows.length) return null;
    const last = rows[rows.length - 1];
    const recent = rows.slice(-20);
    return {
      kind: last.kind,
      volume: last.value,
      ma: last.ma,
      rvol: (last.ma && last.ma > 0) ? (last.value / last.ma) * 100 : null,
      ppv20: recent.filter(r => r.kind === 'ppv').length,
      dry20: recent.filter(r => r.kind === 'dry').length,
    };
  }

  global.SimpleVolume = {VERSION: '1.0.0', DEFAULTS, classify, stats};
})(typeof window !== 'undefined' ? window : globalThis);
