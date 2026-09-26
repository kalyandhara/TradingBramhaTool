/*!
 * tpo.js — Time Price Opportunity (Market Profile) overlay.
 *
 * B-47. Pure computation, no DOM dependency. Rendering lives in
 * chart_dashboard.html (drawTPO()).
 *
 * ── What TPO measures ─────────────────────────────────────────────────────────
 * Volume Profile (VP/SVP) shows WHERE volume traded. TPO shows WHERE TIME was
 * spent: each 30-minute bracket gets a letter (A, B, C …), and every price row
 * that bracket visited gets that letter. The result is the classic "bell curve"
 * of letters stacked at each price level.
 *
 * ── Derived structures ────────────────────────────────────────────────────────
 *   POC          — the price row with the most TPO letters (most time spent)
 *   Value Area   — contiguous band around the POC containing ≥70% of all TPOs
 *   Initial Balance (IB) — price range of the first two brackets (A + B)
 *   Single Prints — price rows visited by only one bracket (potential support/resistance)
 *   Profile shape — Normal (D), P-shape, B-shape, or Thin (I)
 *
 * ── Overlay only ──────────────────────────────────────────────────────────────
 * B-47 specifies an overlay. No BUY/SELL signals — the shapes and levels are
 * arithmetic observations, not measured triggers.
 *
 * NOT ADVICE. The letters are arithmetic, shown so they can be checked.
 *
 * Public API (window.TPO):
 *   TPO.compute(bars, opts) -> {sessions: [{key, letters, grid, rows, poc,
 *       pocPrice, vaHigh, vaLow, ibHigh, ibLow, singlePrints, shape,
 *       hi, lo, startTime, endTime, tickSize}], state, opts}
 *
 * Bar shape expected: {time, open, high, low, close} (volume optional)
 */
(function (global) {
  'use strict';

  const TICK_SIZE = 0.05;
  const BRACKET_MINUTES = 30;
  const VALUE_AREA_PCT = 0.70;
  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';

  function toDate(t) {
    if (typeof t === 'number') return new Date(t * 1000);
    if (typeof t === 'string') return new Date(t.length <= 10 ? t + 'T00:00:00Z' : t);
    if (t && t.year) return new Date(Date.UTC(t.year, (t.month || 1) - 1, t.day || 1));
    return new Date();
  }

  function dayKey(t) {
    const d = toDate(t);
    return d.getUTCFullYear() + '-' + (d.getUTCMonth() + 1) + '-' + d.getUTCDate();
  }

  function weekKey(t) {
    const d = toDate(t);
    const dt = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    const dayNum = (dt.getUTCDay() + 6) % 7;
    dt.setUTCDate(dt.getUTCDate() - dayNum + 3);
    const firstThu = new Date(Date.UTC(dt.getUTCFullYear(), 0, 4));
    const wk = 1 + Math.round(((dt - firstThu) / 864e5 - 3 + ((firstThu.getUTCDay() + 6) % 7)) / 7);
    return dt.getUTCFullYear() + '-W' + wk;
  }

  function monthKey(t) {
    const d = toDate(t);
    return d.getUTCFullYear() + '-M' + (d.getUTCMonth() + 1);
  }

  function chooseGrain(bars) {
    if (!bars.length) return 'day';
    const t0 = toDate(bars[0].time).getTime();
    const t1 = toDate(bars[bars.length - 1].time).getTime();
    const span = (t1 - t0) / 1000;
    const avgBar = span / Math.max(1, bars.length - 1);
    if (avgBar <= 3600) return 'day';
    if (avgBar <= 86400) return 'week';
    return 'month';
  }

  function segmentBars(bars, grain) {
    const keyFn = grain === 'month' ? monthKey : grain === 'week' ? weekKey : dayKey;
    const groups = [];
    let cur = null;
    for (let i = 0; i < bars.length; i++) {
      const k = keyFn(bars[i].time);
      if (!cur || cur.key !== k) {
        cur = {key: k, bars: [], i0: i};
        groups.push(cur);
      }
      cur.bars.push(bars[i]);
      cur.i1 = i;
    }
    return groups;
  }

  function autoTickSize(hi, lo) {
    const range = hi - lo;
    if (range <= 0) return TICK_SIZE;
    const target = range / 60;
    const mag = Math.pow(10, Math.floor(Math.log10(target)));
    const steps = [1, 2, 2.5, 5, 10];
    for (const s of steps) {
      if (mag * s >= target * 0.8) return +(mag * s).toPrecision(4);
    }
    return +(mag * 10).toPrecision(4);
  }

  function bracketIndex(bar, sessionStart, bracketMin) {
    const t = toDate(bar.time).getTime();
    return Math.floor((t - sessionStart) / (bracketMin * 60000));
  }

  function buildSession(seg, opts) {
    const bars = seg.bars;
    if (bars.length < 2) return null;

    const bracketMin = opts.bracketMinutes;
    const vaPct = opts.valueAreaPct;

    let hi = -Infinity, lo = Infinity;
    for (const b of bars) {
      if (b.high > hi) hi = b.high;
      if (b.low < lo) lo = b.low;
    }
    if (hi <= lo) return null;

    const tick = opts.tickSize === 'auto' ? autoTickSize(hi, lo) : opts.tickSize;
    const priceLow = Math.floor(lo / tick) * tick;
    const priceHigh = Math.ceil(hi / tick) * tick;
    const nRows = Math.round((priceHigh - priceLow) / tick) + 1;
    if (nRows < 2 || nRows > 2000) return null;

    const sessionStart = toDate(bars[0].time).getTime();

    // Assign each bar to a bracket
    const barBrackets = bars.map(b => bracketIndex(b, sessionStart, bracketMin));
    const maxBracket = Math.max(...barBrackets);
    const nBrackets = Math.min(maxBracket + 1, LETTERS.length);

    // grid[row] = set of bracket indices that visited this row
    const grid = new Array(nRows);
    for (let r = 0; r < nRows; r++) grid[r] = new Set();

    for (let bi = 0; bi < bars.length; bi++) {
      const b = bars[bi];
      const bracket = barBrackets[bi];
      if (bracket >= LETTERS.length) continue;

      const rLo = Math.max(0, Math.round((b.low - priceLow) / tick));
      const rHi = Math.min(nRows - 1, Math.round((b.high - priceLow) / tick));
      for (let r = rLo; r <= rHi; r++) {
        grid[r].add(bracket);
      }
    }

    // TPO count per row
    const tpoCounts = grid.map(s => s.size);
    const totalTPO = tpoCounts.reduce((a, b) => a + b, 0);

    // POC: row with most TPOs
    let pocRow = 0, pocMax = 0;
    for (let r = 0; r < nRows; r++) {
      if (tpoCounts[r] > pocMax) { pocMax = tpoCounts[r]; pocRow = r; }
    }
    const pocPrice = +(priceLow + pocRow * tick).toFixed(6);

    // Value Area: expand from POC until ≥ vaPct of total TPOs
    let vaUp = pocRow, vaDown = pocRow;
    let vaTPO = tpoCounts[pocRow];
    const target = totalTPO * vaPct;
    while (vaTPO < target && (vaUp < nRows - 1 || vaDown > 0)) {
      const above = vaUp < nRows - 1 ? tpoCounts[vaUp + 1] : -1;
      const below = vaDown > 0 ? tpoCounts[vaDown - 1] : -1;
      if (above >= below) { vaUp++; vaTPO += tpoCounts[vaUp]; }
      else { vaDown--; vaTPO += tpoCounts[vaDown]; }
    }
    const vaHigh = +(priceLow + vaUp * tick).toFixed(6);
    const vaLow = +(priceLow + vaDown * tick).toFixed(6);

    // Initial Balance: brackets 0 and 1
    let ibHigh = null, ibLow = null;
    for (let r = 0; r < nRows; r++) {
      if (grid[r].has(0) || grid[r].has(1)) {
        const pr = priceLow + r * tick;
        if (ibHigh == null || pr > ibHigh) ibHigh = +pr.toFixed(6);
        if (ibLow == null || pr < ibLow) ibLow = +pr.toFixed(6);
      }
    }

    // Single prints: rows visited by exactly one bracket
    const singlePrints = [];
    for (let r = 0; r < nRows; r++) {
      if (tpoCounts[r] === 1) {
        singlePrints.push(+(priceLow + r * tick).toFixed(6));
      }
    }

    // Profile shape (same taxonomy as SVP: D/P/B/I)
    const pocPos = nRows > 1 ? pocRow / (nRows - 1) : 0.5;
    const vaFrac = (vaUp - vaDown + 1) / nRows;
    // Uniform distribution (all counts equal) = balance by definition
    const uniform = pocMax > 0 && tpoCounts.every(c => c === pocMax || c === 0);
    let shape;
    if (vaFrac >= 0.75 || uniform) shape = 'I';
    else if (pocPos >= 0.67) shape = 'P';
    else if (pocPos <= 0.33) shape = 'B';
    else shape = 'D';

    // Build letter strings per row for display
    const letters = [];
    for (let r = 0; r < nRows; r++) {
      const sorted = Array.from(grid[r]).sort((a, b) => a - b);
      letters.push(sorted.map(bi => LETTERS[bi]).join(''));
    }

    return {
      key: seg.key,
      startTime: bars[0].time,
      endTime: bars[bars.length - 1].time,
      hi, lo, tickSize: tick, priceLow, priceHigh, nRows,
      nBrackets,
      grid: grid.map(s => Array.from(s).sort((a, b) => a - b)),
      letters,
      tpoCounts,
      pocRow, pocPrice, pocMax,
      vaHigh, vaLow,
      ibHigh, ibLow,
      singlePrints,
      shape,
    };
  }

  function compute(bars, opts) {
    opts = Object.assign({
      tickSize: 'auto',
      bracketMinutes: BRACKET_MINUTES,
      valueAreaPct: VALUE_AREA_PCT,
    }, opts || {});

    if (!bars || bars.length < 4) {
      return {sessions: [], state: null, opts};
    }

    const grain = chooseGrain(bars);
    const segments = segmentBars(bars, grain);
    const sessions = [];
    for (const seg of segments) {
      const s = buildSession(seg, opts);
      if (s) sessions.push(s);
    }

    let state = null;
    if (sessions.length > 0) {
      const last = sessions[sessions.length - 1];
      const lastClose = bars[bars.length - 1].close;
      let priceVsPoc = null;
      if (lastClose > last.vaHigh) priceVsPoc = 'above_va';
      else if (lastClose < last.vaLow) priceVsPoc = 'below_va';
      else if (Math.abs(lastClose - last.pocPrice) <= last.tickSize * 2) priceVsPoc = 'at_poc';
      else priceVsPoc = 'in_va';

      state = {
        pocPrice: last.pocPrice,
        vaHigh: last.vaHigh,
        vaLow: last.vaLow,
        ibHigh: last.ibHigh,
        ibLow: last.ibLow,
        shape: last.shape,
        priceVsPoc,
        nSinglePrints: last.singlePrints.length,
      };
    }

    return {sessions, state, opts};
  }

  global.TPO = {
    VERSION: '1.0.0', compute,
    TICK_SIZE, BRACKET_MINUTES, VALUE_AREA_PCT, LETTERS,
  };
})(typeof window !== 'undefined' ? window : globalThis);
