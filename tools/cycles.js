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

  // Quantile with linear interpolation (numpy's default), on a sorted copy.
  function quantile(xs, q) {
    const s = xs.slice().sort((a, b) => a - b);
    const pos = (s.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
    return s[lo] + (s[hi] - s[lo]) * (pos - lo);
  }

  /* CY.dominantCycle(pivots, lastIdx, opts)
   *   Measures the trough-to-trough spacing (in bars) of confirmed swing lows,
   *   e.g. pivots from EW.computeZigzag(bars). Returns the median spacing, its
   *   inter-quartile range and the count, plus the next expected trough as a
   *   window [last low + q1, last low + q3] rather than one exact bar, and the
   *   half-cycle mark. `overdue` is true when the window has already closed
   *   by lastIdx (the latest bar) — the count is then stale, not extended.
   *   Needs at least opts.minSpacings (default 3) spacings, else null.
   *   Drawing aid, not measured.
   */
  function dominantCycle(pivots, lastIdx, opts) {
    const minSpacings = (opts && opts.minSpacings) || 3;
    const lows = (pivots || []).filter(p => p.type === 'low' && !p.provisional)
                               .map(p => p.idx).sort((a, b) => a - b);
    const gaps = [];
    for (let i = 1; i < lows.length; i++) if (lows[i] > lows[i - 1]) gaps.push(lows[i] - lows[i - 1]);
    if (gaps.length < minSpacings) return null;
    const median = quantile(gaps, 0.5), q1 = quantile(gaps, 0.25), q3 = quantile(gaps, 0.75);
    const last = lows[lows.length - 1];
    const r = Math.round;
    return {
      median, q1, q3, n: gaps.length, lastTrough: last,
      next: {idx: r(last + median), from: r(last + q1), to: r(last + q3)},
      half: r(last + median / 2),
      overdue: Number.isFinite(lastIdx) && r(last + q3) < lastIdx,
      drawingAid: true,
    };
  }

  /* CY.swingBox(pivots)
   *   Copies the last completed trough-to-peak swing forward from the latest
   *   confirmed trough: same bars, same price rise. `source` is the swing it
   *   copies (previous low -> highest high before the latest low), `projected`
   *   the box from the latest low. Returns null with fewer than two confirmed
   *   lows or no high between them. Drawing aid, not measured.
   */
  function swingBox(pivots) {
    const pv = (pivots || []).filter(p => !p.provisional).slice().sort((a, b) => a.idx - b.idx);
    const lows = pv.filter(p => p.type === 'low');
    if (lows.length < 2) return null;
    const L = lows[lows.length - 1], L0 = lows[lows.length - 2];
    const highs = pv.filter(p => p.type === 'high' && p.idx > L0.idx && p.idx < L.idx);
    if (!highs.length) return null;
    const H0 = highs.reduce((a, b) => (b.price > a.price ? b : a));
    const bars = H0.idx - L0.idx, rise = H0.price - L0.price;
    if (!(bars > 0) || !(rise > 0)) return null;
    return {
      bars, rise,
      source:    {from: {idx: L0.idx, price: L0.price}, to: {idx: H0.idx, price: H0.price}},
      projected: {from: {idx: L.idx,  price: L.price},  to: {idx: L.idx + bars, price: L.price + rise}},
      drawingAid: true,
    };
  }

  root.CY = {VERSION: '1.2.0', fld, dominantCycle, swingBox};
})(typeof window !== 'undefined' ? window : globalThis);
