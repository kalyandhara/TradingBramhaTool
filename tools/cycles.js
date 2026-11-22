/* cycles.js — Hurst cycle helpers for the chart (pure computation, no DOM).
 *
 * window.CY.fld(closes, cycle)
 *   Future Line of Demarcation: price displaced forward by half a cycle,
 *   FLD[i] = close[i - floor(cycle/2)] — the same definition as
 *   fld_confluence.py (`_prep`, `fld_series`). Its last cycle/2 values fall on
 *   bars that have not printed yet; that "forward" part is known data shifted
 *   right, not a forecast of price. Drawing aid, not measured.
 *
 * Returns {cycle, shift, known:[{idx,value}], forward:[{idx,value}], drawingAid}
 * or null when there are not more closes than the shift.
 */
(function (root) {
  'use strict';

  function fld(closes, cycle) {
    const s = Math.floor(cycle / 2);
    const n = closes ? closes.length : 0;
    if (!(s >= 1) || n <= s) return null;
    const known = [], forward = [];
    for (let i = s; i < n + s; i++) {
      const v = closes[i - s];
      if (!Number.isFinite(v)) continue;
      (i < n ? known : forward).push({idx: i, value: v});
    }
    return {cycle, shift: s, known, forward, drawingAid: true};
  }

  root.CY = {VERSION: '1.0.0', fld};
})(typeof window !== 'undefined' ? window : globalThis);
