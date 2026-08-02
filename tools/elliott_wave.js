/*!
 * elliott_wave.js — Adaptive Elliott Wave detection module (plug-in).
 *
 * Pure computation library: takes an OHLCV bar array and returns pivot
 * points, detected Impulse (1-2-3-4-5) and Corrective (A-B-C) wave
 * structures, Fibonacci projection levels, and confidence scores.
 *
 * No DOM / charting-library dependency — rendering is handled by the
 * caller (see chart_dashboard.html: renderElliottWave()). This keeps the
 * detection logic reusable, testable, and swappable independent of the
 * charting layer.
 *
 * Public API (window.EW):
 *   EW.computeZigzag(bars, opts)              -> pivots[]
 *   EW.detectImpulses(pivots)                 -> impulse structures[]
 *   EW.detectCorrectives(pivots, impulses)    -> corrective structures[]
 *   EW.fibLevelsForImpulse(impulse)           -> level[]
 *   EW.fibLevelsForCorrective(corrective)     -> level[]
 *   EW.analyze(bars, opts)                    -> {pivots, impulses, correctives}
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 * Pivot shape:         {idx, time, price, type:'high'|'low', provisional?}
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    atrPeriod: 14,   // ATR lookback used for the volatility-adaptive threshold
    atrMult:   1.2,  // ZigZag reversal threshold = atrMult × ATR
    minPct:    0.5,  // ...floored at minPct% of price (keeps low-ATR/illiquid bars sane)
  };

  // ── Wilder's ATR, index-aligned with bars (nulls before it warms up) ──────────
  function atr(bars, period) {
    const n = bars.length;
    const out = new Array(n).fill(null);
    if (n < period + 1) return out;

    const trs = new Array(n);
    let prevClose = bars[0].close;
    for (let i = 0; i < n; i++) {
      const b = bars[i];
      trs[i] = i === 0
        ? (b.high - b.low)
        : Math.max(b.high - b.low, Math.abs(b.high - prevClose), Math.abs(b.low - prevClose));
      prevClose = b.close;
    }

    let sum = 0;
    for (let i = 0; i < period; i++) sum += trs[i];
    let a = sum / period;
    out[period - 1] = a;
    for (let i = period; i < n; i++) {
      a = (a * (period - 1) + trs[i]) / period;
      out[i] = a;
    }
    return out;
  }

  // ── ZigZag pivot detection — volatility-adaptive, non-repainting ──────────────
  // Every pivot except the very last one represents a CONFIRMED price reversal
  // (already happened, can never change). Only the last pivot is `provisional`:
  // it tracks the still-forming extreme and may extend further until a future
  // bar confirms a reversal away from it. This is what makes downstream wave
  // structures "finalized" once their last point is not the trailing pivot.
  function computeZigzag(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const n = bars.length;
    if (n < opts.atrPeriod + 5) return [];

    const atrArr = atr(bars, opts.atrPeriod);
    let lastAtr = null;
    function threshAt(i) {
      if (atrArr[i] != null) lastAtr = atrArr[i];
      const px = bars[i].close;
      return Math.max(px * (opts.minPct / 100), (lastAtr || 0) * opts.atrMult);
    }

    // Phase 1 — scan forward until the first confirmed leg establishes direction.
    let hi = bars[0].high, lo = bars[0].low, hiIdx = 0, loIdx = 0;
    let dir = 0, seedIdx = -1;

    for (let i = 1; i < n; i++) {
      if (bars[i].high > hi) { hi = bars[i].high; hiIdx = i; }
      if (bars[i].low  < lo) { lo = bars[i].low;  loIdx = i; }
      const t = threshAt(i);
      if (hiIdx > loIdx && hi - bars[i].low >= t) { dir = -1; seedIdx = hiIdx; break; }
      if (loIdx > hiIdx && bars[i].high - lo >= t) { dir = 1;  seedIdx = loIdx; break; }
    }
    if (dir === 0) return []; // not enough movement yet to establish a trend

    const pivots = [];
    pivots.push({
      idx: seedIdx, time: bars[seedIdx].time,
      price: dir === 1 ? bars[seedIdx].low : bars[seedIdx].high,
      type: dir === 1 ? 'low' : 'high',
    });

    let extreme = {idx: seedIdx, price: pivots[0].price};

    // Phase 2 — walk forward confirming alternating reversals.
    for (let i = seedIdx + 1; i < n; i++) {
      const t = threshAt(i);
      if (dir === 1) {
        if (bars[i].high > extreme.price) extreme = {idx: i, price: bars[i].high};
        if (extreme.price - bars[i].low >= t) {
          pivots.push({idx: extreme.idx, time: bars[extreme.idx].time, price: extreme.price, type: 'high'});
          dir = -1;
          extreme = {idx: i, price: bars[i].low};
        }
      } else {
        if (bars[i].low < extreme.price) extreme = {idx: i, price: bars[i].low};
        if (bars[i].high - extreme.price >= t) {
          pivots.push({idx: extreme.idx, time: bars[extreme.idx].time, price: extreme.price, type: 'low'});
          dir = 1;
          extreme = {idx: i, price: bars[i].high};
        }
      }
    }

    // Trailing/forming extreme — provisional, may still extend.
    pivots.push({
      idx: extreme.idx, time: bars[extreme.idx].time, price: extreme.price,
      type: dir === 1 ? 'high' : 'low', provisional: true,
    });

    return pivots;
  }

  // ── Fibonacci confidence scoring helpers ──────────────────────────────────────
  function fibScore(value, idealRatios, tolerance) {
    tolerance = tolerance || 0.18;
    let best = 0;
    idealRatios.forEach(ratio => {
      const diff = Math.abs(value - ratio) / ratio;
      if (diff <= tolerance) {
        const s = 100 * (1 - diff / tolerance);
        if (s > best) best = s;
      }
    });
    return best;
  }

  function scoreImpulse(r) {
    const s2 = fibScore(r.w2retrPct, [0.382, 0.5, 0.618, 0.786]);
    const s3 = fibScore(r.w3extRatio, [1.0, 1.618, 2.618]);
    const s4 = fibScore(r.w4retrPct, [0.236, 0.382, 0.5]);
    const s5 = fibScore(r.w5Ratio, [0.618, 1.0, 1.618]);
    return Math.round((s2 + s3 + s4 + s5) / 4);
  }

  // ── Impulse (1-2-3-4-5) detection ──────────────────────────────────────────────
  // Greedy left-to-right scan over the pivot list: the first valid 6-point
  // window (5 legs) found is accepted, then the scan resumes from its end —
  // producing a clean, non-overlapping sequence of impulses across the chart,
  // the same way a human analyst marks one count at a time.
  function detectImpulses(pivots) {
    const out = [];
    if (pivots.length < 6) return out;

    let s = 0;
    while (s <= pivots.length - 6) {
      const w = pivots.slice(s, s + 6);
      const bullish = w[0].type === 'low';
      const expectedTypes = bullish
        ? ['low', 'high', 'low', 'high', 'low', 'high']
        : ['high', 'low', 'high', 'low', 'high', 'low'];
      const typesOk = w.every((p, i) => p.type === expectedTypes[i]);
      if (!typesOk) { s++; continue; }

      const sign = bullish ? 1 : -1;
      const P = w.map(pt => pt.price);
      const wave1 = (P[1] - P[0]) * sign;
      const wave2 = (P[1] - P[2]) * sign;
      const wave3 = (P[3] - P[2]) * sign;
      const wave4 = (P[3] - P[4]) * sign;
      const wave5 = (P[5] - P[4]) * sign;

      if (wave1 <= 0 || wave2 <= 0 || wave3 <= 0 || wave4 <= 0 || wave5 <= 0) { s++; continue; }

      // ── Hard Elliott rules ──
      const rule1Ok = bullish ? P[2] > P[0] : P[2] < P[0];               // wave2 < 100% retrace of wave1
      const rule2Ok = bullish ? P[3] > P[1] : P[3] < P[1];               // wave3 travels beyond wave1 end
      const rule3Ok = !(wave3 < wave1 && wave3 < wave5);                 // wave3 is not the shortest
      if (!rule1Ok || !rule2Ok || !rule3Ok) { s++; continue; }

      const diagonal = bullish ? P[4] < P[1] : P[4] > P[1];              // wave4 overlaps wave1 territory

      const ratios = {
        w2retrPct:  wave2 / wave1,
        w3extRatio: wave3 / wave1,
        w4retrPct:  wave4 / wave3,
        w5Ratio:    wave5 / wave1,
        w5vsW3:     wave5 / wave3,
      };

      const points = w.map((pt, i) => ({...pt, label: String(i)}));
      const final = !w.some(pt => pt.provisional);

      out.push({
        id: 'imp_' + w[0].time,
        type: 'impulse',
        bullish,
        startIdx: s,
        points,
        ratios,
        diagonal,
        final,
        score: scoreImpulse(ratios),
        lengths: {wave1, wave2, wave3, wave4, wave5},
      });

      s += 5; // resume scanning from this impulse's wave-5 pivot
    }
    return out;
  }

  // ── Corrective (A-B-C) detection ──────────────────────────────────────────────
  // For each impulse, looks at the pivots immediately following its wave-5
  // point and labels up to 3 further legs as A, B, C. Supports partial counts
  // (just A, or A-B) while the correction is still forming in real time.
  function detectCorrectives(pivots, impulses) {
    const out = [];
    impulses.forEach(imp => {
      const endIdx = imp.startIdx + 5;
      const avail = pivots.length - endIdx - 1;
      if (avail < 1) return;

      const legsCount = Math.min(avail, 3);
      const w = pivots.slice(endIdx, endIdx + legsCount + 1);
      const labels = ['5', 'A', 'B', 'C'];
      const points = w.map((pt, i) => ({...pt, label: labels[i]}));

      const ratios = {};
      if (w.length >= 2) ratios.lenA = Math.abs(w[1].price - w[0].price);
      if (w.length >= 3) {
        const lenA = Math.abs(w[1].price - w[0].price);
        const lenB = Math.abs(w[2].price - w[1].price);
        ratios.bRetracePct = lenA > 0 ? lenB / lenA : null;
        ratios.patternGuess = ratios.bRetracePct == null ? null
          : ratios.bRetracePct <= 0.8 ? 'zigzag'
          : ratios.bRetracePct <= 1.05 ? 'flat'
          : 'expanded-flat';
      }
      if (w.length >= 4) {
        const lenA = Math.abs(w[1].price - w[0].price);
        const lenC = Math.abs(w[3].price - w[2].price);
        ratios.cVsA = lenA > 0 ? lenC / lenA : null;
      }

      out.push({
        id: 'corr_' + imp.id,
        type: 'corrective',
        parentImpulseId: imp.id,
        bullishParent: imp.bullish,
        points,
        ratios,
        complete: legsCount === 3,
        final: !w.some(pt => pt.provisional),
      });
    });
    return out;
  }

  // ── Fibonacci projections ──────────────────────────────────────────────────────
  function fibLevelsForImpulse(imp) {
    const [p0, p1, p2, p3] = imp.points;
    const p4 = imp.points[4];
    const sign = imp.bullish ? 1 : -1;
    const wave1Len = Math.abs(p1.price - p0.price);
    const net03 = Math.abs(p3.price - p0.price);
    const levels = [];

    // Wave 3 target, projected from the end of wave 2 (p2).
    [1.0, 1.618, 2.618].forEach(r => {
      levels.push({
        role: 'w3target', ratio: r, fromTime: p2.time,
        price: p2.price + sign * wave1Len * r,
        label: `W3 ${r}×W1`,
      });
    });

    // Wave 5 target(s), projected from the end of wave 4 (p4) — only once wave4 exists.
    if (p4) {
      [0.618, 1.0, 1.618].forEach(r => {
        levels.push({
          role: 'w5target', ratio: r, fromTime: p4.time,
          price: p4.price + sign * wave1Len * r,
          label: `W5 ${r}×W1`,
        });
      });
      levels.push({
        role: 'w5target', ratio: 0.618, fromTime: p4.time,
        price: p0.price + sign * net03 * 0.618,
        label: 'W5 0.618×(0-3)',
      });
    }
    return levels;
  }

  function fibLevelsForCorrective(corr) {
    const pts = corr.points; // [5, A, (B), (C)]
    if (pts.length < 3) return []; // need at least A and B to project C
    const p5 = pts[0], pA = pts[1], pB = pts[2];
    const lenA = Math.abs(pA.price - p5.price);
    const dirA = pA.price >= p5.price ? 1 : -1; // wave C continues in the same direction as wave A

    return [0.618, 1.0, 1.618].map(r => ({
      role: 'cTarget', ratio: r, fromTime: pB.time,
      price: pB.price + dirA * lenA * r,
      label: `C ${r}×A`,
    }));
  }

  // ── Invalidation ("pattern negation") level ───────────────────────────────────
  // The price at which the CURRENT label stops being possible under Elliott's
  // hard rules — the thing an analyst means by "the pattern is negated if X is
  // touched". Targets alone are only half a forecast: a count with a target and
  // no invalidation cannot be wrong, which is precisely what makes it useless.
  //
  // These are the HARD rules only, never the guidelines. A guideline being
  // violated makes a count unattractive; a rule being violated makes it invalid,
  // and only the second belongs on a line labelled "negation".

  function _invalidation(price, side, wave, rule) {
    return {price, side, wave, rule};
  }

  function invalidationForImpulse(imp) {
    const P = imp.points.map(p => p.price);
    const bull = imp.bullish;
    // A detected impulse always has all six pivots, so the live leg is wave 5
    // (its last pivot is provisional until the structure finalises). Wave 5 is
    // negated by a return beyond the end of wave 4 — at that point the move is
    // no longer a fifth wave away from wave 4, whatever else it may be.
    return _invalidation(
      P[4],
      bull ? 'below' : 'above',
      '5',
      bull ? 'Wave 5 negated if price trades back below the wave-4 low'
           : 'Wave 5 negated if price trades back above the wave-4 high');
  }

  function invalidationForCorrective(corr) {
    const pts = corr.points;          // [5, A, (B), (C)]
    const P = pts.map(p => p.price);
    // A correction runs against its parent impulse, so "beyond the origin"
    // means back through the wave-5 extreme.
    const downward = P[1] < P[0];     // wave A fell => corrective of an up impulse
    const beyondOrigin = downward ? 'above' : 'below';

    if (pts.length <= 2) {
      return _invalidation(
        P[0], beyondOrigin, 'A',
        downward ? 'Wave A negated if price trades back above the wave-5 high'
                 : 'Wave A negated if price trades back below the wave-5 low');
    }
    if (pts.length === 3) {
      // Wave B may not carry beyond the start of wave A in a zigzag. (In a
      // running/expanded flat it can, which is why patternGuess is reported
      // beside this rather than hidden.)
      return _invalidation(
        P[0], beyondOrigin, 'B',
        downward ? 'Wave B negated beyond the wave-5 high (zigzag rule; an '
                   + 'expanded flat may exceed it)'
                 : 'Wave B negated beyond the wave-5 low (zigzag rule; an '
                   + 'expanded flat may exceed it)');
    }
    // C is forming: it must continue past B, so a return through B's extreme
    // breaks the label.
    const cDown = P[3] < P[2];
    return _invalidation(
      P[2], cDown ? 'above' : 'below', 'C',
      cDown ? 'Wave C negated if price trades back above the wave-B high'
            : 'Wave C negated if price trades back below the wave-B low');
  }

  /**
   * Invalidation for a structure, optionally measured against live bars.
   *
   * With `bars`, adds `last`, `distance`, `distancePct` and `breached`.
   * `breached: true` means the level has ALREADY been violated — the count on
   * screen is stale and should not be traded off, which is worth stating
   * loudly rather than leaving the reader to compare two numbers.
   */
  function invalidation(structure, bars) {
    if (!structure || !structure.points || !structure.points.length) return null;
    const inv = structure.type === 'corrective'
      ? invalidationForCorrective(structure)
      : invalidationForImpulse(structure);
    if (!inv || inv.price == null) return null;

    if (bars && bars.length) {
      const last = bars[bars.length - 1].close;
      inv.last = last;
      inv.distance = Math.abs(last - inv.price);
      inv.distancePct = inv.price ? (inv.distance / inv.price) * 100 : null;
      inv.breached = inv.side === 'below' ? last < inv.price : last > inv.price;
    }
    return inv;
  }

  // ── Convenience full pipeline ──────────────────────────────────────────────────
  function analyze(bars, opts) {
    const pivots = computeZigzag(bars, opts);
    const impulses = detectImpulses(pivots);
    const correctives = detectCorrectives(pivots, impulses);
    // The live count is the latest structure — the corrective if one has begun
    // since the last impulse, otherwise the impulse itself.
    const lastImp = impulses[impulses.length - 1] || null;
    const lastCorr = correctives[correctives.length - 1] || null;
    const active = lastCorr || lastImp;
    return {
      pivots, impulses, correctives,
      active,
      invalidation: active ? invalidation(active, bars) : null,
    };
  }

  global.EW = {
    VERSION: '1.1.0',
    computeZigzag, detectImpulses, detectCorrectives,
    fibLevelsForImpulse, fibLevelsForCorrective,
    invalidation, invalidationForImpulse, invalidationForCorrective,
    analyze,
  };
})(typeof window !== 'undefined' ? window : globalThis);
