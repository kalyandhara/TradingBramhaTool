/*!
 * cpr.js — Central Pivot Range from the PRIOR bar: TC / Pivot / BC plus R1 / S1.
 *
 * Pure computation module (no DOM / chart dependency), same shape as psar.js.
 * The arithmetic is the desk's `row_metrics.pivot_levels`, so the Chart Tool,
 * the classic Plotly chart and the Python tables agree on where TC and BC are:
 *
 *   PP = (H + L + C) / 3       BC = (H + L) / 2       TC = 2·PP − BC
 *   R1 = 2·PP − L              S1 = 2·PP − H          (all from bar i−1)
 *
 * TC / BC are normalised so `tc >= bc` whatever the prior close did; the raw
 * formula swaps them when the close sits below the bar's midpoint.
 *
 * Overlay only. Nothing here is a signal: the "hold above / reject / break"
 * reads are descriptions of the last bar against the levels, and none of them
 * has been measured for forward return in this repo.
 *
 * Public API (window.CPR):
 *   CPR.compute(bars) -> {tc, p, bc, r1, s1, last, widthPct, band, position}
 *     each series is [{time, value}] aligned to bars[1..]
 *   CPR.confluence(levels, profile, tolPct) -> {TC:[types], P:[...], BC:[...]}
 *     via VP.findConfluence when the Volume Profile module is loaded
 */
(function (root) {
  'use strict';

  const NARROW_PCT = 0.5, WIDE_PCT = 1.5, TOL_PCT = 0.004;

  function compute(bars) {
    const tc = [], p = [], bc = [], r1 = [], s1 = [];
    let last = null;
    for (let i = 1; i < bars.length; i++) {
      const b = bars[i - 1];
      if (!(b.high > 0) || !(b.low > 0) || !(b.close > 0)) continue;
      const pp = (b.high + b.low + b.close) / 3;
      let bcv = (b.high + b.low) / 2;
      let tcv = 2 * pp - bcv;
      if (bcv > tcv) { const t = tcv; tcv = bcv; bcv = t; }
      const t = bars[i].time;
      tc.push({time: t, value: tcv}); p.push({time: t, value: pp}); bc.push({time: t, value: bcv});
      r1.push({time: t, value: 2 * pp - b.low}); s1.push({time: t, value: 2 * pp - b.high});
      last = {tc: tcv, p: pp, bc: bcv, r1: 2 * pp - b.low, s1: 2 * pp - b.high, bar: bars[i]};
    }
    let widthPct = null, band = null, position = null;
    if (last) {
      widthPct = (last.tc - last.bc) / last.p * 100;
      band = widthPct < NARROW_PCT ? 'narrow' : widthPct > WIDE_PCT ? 'wide' : 'normal';
      const c = last.bar.close;
      position = c > last.tc ? 'above_tc' : c < last.bc ? 'below_bc' : 'inside';
    }
    return {tc, p, bc, r1, s1, last, widthPct, band, position};
  }

  function confluence(last, profile, tolPct) {
    if (!last || !profile || typeof root.VP === 'undefined' || !root.VP.findConfluence) return {};
    const pts = [{name: 'TC', price: last.tc}, {name: 'P', price: last.p}, {name: 'BC', price: last.bc}];
    const out = {};
    for (const r of root.VP.findConfluence(pts, profile, tolPct || TOL_PCT)) {
      out[r.name] = Array.from(new Set(r.matches.map(m => m.type)));
    }
    return out;
  }

  root.CPR = {compute, confluence, NARROW_PCT, WIDE_PCT, TOL_PCT};
})(typeof window !== 'undefined' ? window : globalThis);
