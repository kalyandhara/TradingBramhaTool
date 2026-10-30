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
 *   EW.detectComplexCorrectives(pivots)       -> W-X-Y structures[]        (B-135)
 *   EW.fibLevelsForComplex(complex)           -> Y-target level[]           (B-135)
 *   EW.assessB(lenA, lenB, durA, durB)        -> unusual-B verdict          (B-134)
 *   EW.analyze(bars, opts)                    -> {pivots, impulses, correctives, complex}
 *   EW.analyzeDegrees(bars, opts)             -> {minor, major, nesting}    (B-136)
 *
 * B-134..B-136 (2026-10-08) are DRAWING AIDS. None of them has been measured
 * for edge; the pre-registered studies live in the Open Backlog and nothing
 * here votes in any shortlist.
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
    let dir = 0, seedIdx = -1, seedAt = -1;

    for (let i = 1; i < n; i++) {
      if (bars[i].high > hi) { hi = bars[i].high; hiIdx = i; }
      if (bars[i].low  < lo) { lo = bars[i].low;  loIdx = i; }
      const t = threshAt(i);
      // B-137: `< i` — the bar that set the extreme cannot also confirm the
      // reversal from it (its high/low ORDER is unknowable from OHLC).
      if (hiIdx > loIdx && hiIdx < i && hi - bars[i].low >= t) { dir = -1; seedIdx = hiIdx; seedAt = i; break; }
      if (loIdx > hiIdx && loIdx < i && bars[i].high - lo >= t) { dir = 1;  seedIdx = loIdx; seedAt = i; break; }
    }
    if (dir === 0) return []; // not enough movement yet to establish a trend

    // `confirmedAt` (2026-10-08): the first bar k at which computeZigzag(
    // bars[0..k]) reports this pivot as confirmed — the reversal bar, but never
    // earlier than the minimum series length this function needs (it returns []
    // below atrPeriod+5 bars). The provisional trailing pivot has none. Studies
    // use it to stay causal.
    const minLast = opts.atrPeriod + 4;
    const known = i => Math.max(i, minLast);
    const pivots = [];
    pivots.push({
      idx: seedIdx, time: bars[seedIdx].time,
      price: dir === 1 ? bars[seedIdx].low : bars[seedIdx].high,
      type: dir === 1 ? 'low' : 'high', confirmedAt: known(seedAt),
    });

    let extreme = {idx: seedIdx, price: pivots[0].price};

    // Phase 2 — walk forward confirming alternating reversals.
    //
    // B-137 (2026-10-08): a reversal is confirmed only by a bar AFTER the bar
    // that set the extreme. Before this, one wide bar could set a new high and
    // "confirm" a reversal from its own low, then the next bar confirmed a low
    // on that same bar — a top and a bottom on one candle, from an intra-bar
    // order OHLC cannot show. Measured on cache/cardinality_deep before the fix:
    // 132,258 same-bar pivot pairs in 613,942 pivots, every one of 459 names.
    for (let i = seedIdx + 1; i < n; i++) {
      const t = threshAt(i);
      if (dir === 1) {
        if (bars[i].high > extreme.price) extreme = {idx: i, price: bars[i].high};
        if (extreme.idx < i && extreme.price - bars[i].low >= t) {
          pivots.push({idx: extreme.idx, time: bars[extreme.idx].time, price: extreme.price, type: 'high', confirmedAt: known(i)});
          dir = -1;
          extreme = {idx: i, price: bars[i].low};
        }
      } else {
        if (bars[i].low < extreme.price) extreme = {idx: i, price: bars[i].low};
        if (extreme.idx < i && bars[i].high - extreme.price >= t) {
          pivots.push({idx: extreme.idx, time: bars[extreme.idx].time, price: extreme.price, type: 'low', confirmedAt: known(i)});
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

  // ── B-134: is wave B unusual? ─────────────────────────────────────────────────
  // Price: B retracing less than 23.6% of A, or more than 138.2% (past the
  // expanded-flat range), is outside every textbook corrective. Time: B taking
  // more than twice as long as A is reported SEPARATELY (`slow`), because the
  // pre-registered study tests the price definition alone and a combined flag
  // would blur which one it measured. Boundaries are inclusive-normal.
  const B_MIN = 0.236, B_MAX = 1.382, B_SLOW = 2.0, EPS = 1e-9;

  function assessB(lenA, lenB, durA, durB) {
    const retrace = lenA > 0 ? lenB / lenA : null;
    const timeRatio = (durA > 0 && durB != null) ? durB / durA : null;
    const reasons = [];
    if (retrace != null && retrace < B_MIN - EPS)
      reasons.push(`shallow B: ${(retrace * 100).toFixed(1)}% of A (< 23.6%)`);
    if (retrace != null && retrace > B_MAX + EPS)
      reasons.push(`deep B: ${(retrace * 100).toFixed(1)}% of A (> 138.2%, beyond the expanded-flat range)`);
    const slow = timeRatio != null && timeRatio > B_SLOW + EPS;
    return {retrace, timeRatio, abnormal: reasons.length > 0, reasons, slow,
            slowNote: slow ? `slow B: ${timeRatio.toFixed(1)}x as long as A (> 2x)` : null};
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
        const b = assessB(lenA, lenB, w[1].idx - w[0].idx, w[2].idx - w[1].idx);
        ratios.bAbnormal = b.abnormal;
        ratios.bAbnormalReasons = b.reasons;
        ratios.bSlow = b.slow;
        ratios.bTimeRatio = b.timeRatio;
        if (b.slowNote) ratios.bSlowNote = b.slowNote;
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

  // ── B-135: W-X-Y (double zigzag / double three) ───────────────────────────────
  // Eight consecutive pivots: an A-B-C (W), a counter-move (X), a second A-B-C
  // (Y) that carries the correction PAST W's end. Constraints, all stated:
  //   • each of W and Y is a real A-B-C — its b retraces <= 138.2% of its a,
  //     and its c is at least 61.8% of its a;
  //   • X retraces 38.2%..100% of W (beyond 100% X has passed W's origin and
  //     this is not one correction any more);
  //   • Y ends beyond W's end, and Y is 0.382x..2.618x of W in size, so two
  //     unrelated swings of very different scale are not stitched together.
  // Greedy left-to-right like detectImpulses: confirmed pivots never re-segment,
  // which is what keeps `final` structures fixed as bars arrive.
  const X_MIN = 0.382, X_MAX = 1.0, C_MIN = 0.618, YW_MIN = 0.382, YW_MAX = 2.618;
  const CX_LABELS = ['', 'a', 'b', 'W', 'X', 'a', 'b', 'Y'];

  function detectComplexCorrectives(pivots) {
    const out = [];
    if (!pivots || pivots.length < 8) return out;
    let s = 0;
    while (s <= pivots.length - 8) {
      const w = pivots.slice(s, s + 8);
      const down = w[0].type === 'high';
      const sign = down ? -1 : 1;                 // correction direction
      const P = w.map(pt => pt.price);
      const m = (i, j) => (P[j] - P[i]) * sign;   // + = with the correction

      const a = m(0, 1), b = -m(1, 2), c = m(2, 3), wNet = m(0, 3);
      const x = -m(3, 4);
      const ya = m(4, 5), yb = -m(5, 6), yc = m(6, 7), yNet = m(4, 7);
      const legsOk = [a, b, c, x, ya, yb, yc].every(v => v > 0) && wNet > 0 && yNet > 0;
      if (!legsOk) { s++; continue; }

      const wB = assessB(a, b, w[1].idx - w[0].idx, w[2].idx - w[1].idx);
      const yB = assessB(ya, yb, w[5].idx - w[4].idx, w[6].idx - w[5].idx);
      const xRetracePct = x / wNet;
      const yVsW = yNet / wNet;
      const ok = wB.retrace <= B_MAX + EPS && yB.retrace <= B_MAX + EPS
        && c >= C_MIN * a - EPS && yc >= C_MIN * ya - EPS
        && xRetracePct >= X_MIN - EPS && xRetracePct <= X_MAX + EPS
        && m(3, 7) > 0
        && yVsW >= YW_MIN - EPS && yVsW <= YW_MAX + EPS;
      if (!ok) { s++; continue; }

      const zz = r => r <= 0.8;
      out.push({
        id: 'cx_' + w[0].time,
        type: 'complex-corrective',
        subtype: zz(wB.retrace) && zz(yB.retrace) ? 'double-zigzag' : 'double-three',
        direction: down ? 'down' : 'up',
        startIdx: s,
        points: w.map((pt, i) => ({...pt, label: CX_LABELS[i]})),
        ratios: {wNet, yNet, xRetracePct, yVsW, wB, yB},
        complete: true,
        final: !w.some(pt => pt.provisional),
      });
      s += 7;          // resume from Y's end, as detectImpulses does from wave 5
    }
    return out;
  }

  function fibLevelsForComplex(cx) {
    const P = cx.points.map(p => p.price);
    const lenW = Math.abs(P[3] - P[0]);
    const dir = cx.direction === 'down' ? -1 : 1;
    return [0.618, 1.0, 1.618].map(r => ({
      role: 'yTarget', ratio: r, fromTime: cx.points[4].time,
      price: P[4] + dir * lenW * r,
      label: `Y ${r}×W`,
    }));
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

  function invalidationForComplex(cx) {
    const P = cx.points.map(p => p.price);
    const down = cx.direction === 'down';
    if (!cx.final) {
      // Y's c is the live leg: it must keep going past Y's b, so a return
      // through b's extreme breaks the label (the A-B-C rule, one degree in).
      return _invalidation(P[6], down ? 'above' : 'below', 'Y',
        down ? "Y negated if price trades back above Y's b high"
             : "Y negated if price trades back below Y's b low");
    }
    // Final: the W-X-Y is counted as COMPLETE at Y's extreme. A new extreme in
    // the correction's direction means it was not complete - it is extending.
    return _invalidation(P[7], down ? 'below' : 'above', 'Y',
      down ? 'W-X-Y completion negated if price trades below the Y low (still extending)'
           : 'W-X-Y completion negated if price trades above the Y high (still extending)');
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
      : structure.type === 'complex-corrective'
      ? invalidationForComplex(structure)
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
    const complex = detectComplexCorrectives(pivots);
    // The live count is the latest structure — the corrective if one has begun
    // since the last impulse, otherwise the impulse itself; a W-X-Y takes over
    // only when it ends at or after that structure's last pivot.
    const lastImp = impulses[impulses.length - 1] || null;
    const lastCorr = correctives[correctives.length - 1] || null;
    const lastCx = complex[complex.length - 1] || null;
    let active = lastCorr || lastImp;
    const endIdx = st => st.points[st.points.length - 1].idx;
    if (lastCx && (!active || endIdx(lastCx) >= endIdx(active))) active = lastCx;
    return {
      pivots, impulses, correctives, complex,
      active,
      invalidation: active ? invalidation(active, bars) : null,
    };
  }

  // ── B-138: which count is LIVE ───────────────────────────────────────────────
  // The chart draws the best-SCORED impulses, but the count a reader acts on is
  // the most RECENT one — and only while it is current. Before this the chart
  // took the last of a score-sorted list, i.e. the lowest-scored of the top
  // three, often months old (RELIANCE 1d, 2026-10-08: a Wave C negation 19%
  // above price). `shownImpulses` restricts the choice to what is drawn, so the
  // panel never describes a structure the chart does not show.
  //
  // live = the active structure ends at the latest CONFIRMED pivot or at the
  // forming one. Anything older is history: describe it, never negate it.
  function liveCount(an, shownImpulses) {
    const piv = (an && an.pivots) || [];
    const end = st => st.points[st.points.length - 1].idx;
    const pool = (shownImpulses || (an && an.impulses) || []).slice()
      .sort((a, b) => end(a) - end(b));
    const impulse = pool[pool.length - 1] || null;
    const corrective = impulse
      ? ((an.correctives || []).find(c => c.parentImpulseId === impulse.id) || null) : null;
    const cxs = (an && an.complex) || [];
    const complex = cxs[cxs.length - 1] || null;
    let active = corrective || impulse;
    if (complex && (!active || end(complex) >= end(active))) active = complex;
    const lastConfirmed = piv.length >= 2 ? piv[piv.length - 2].idx
                        : piv.length ? piv[0].idx : -1;
    const live = !!active && end(active) >= lastConfirmed;
    return {impulse, corrective, complex, active, live,
            endedAt: active ? active.points[active.points.length - 1].time : null};
  }

  // ── B-136: two wave degrees ───────────────────────────────────────────────────
  // The same pipeline at two zigzag sizes. `minor` with the default threshold is
  // identical to plain analyze(); `major` uses a larger ATR multiple, so its
  // pivots are a subset of the big turns. `nesting` lists every minor structure
  // that sits entirely inside one major leg — that is what lets a chart say
  // "this W-X-Y is wave (b) of the larger move" without inventing a count.
  function analyzeDegrees(bars, opts) {
    opts = Object.assign({minorMult: DEFAULT_OPTS.atrMult, majorMult: 3.0}, opts || {});
    const base = Object.assign({}, opts);
    delete base.minorMult; delete base.majorMult;
    // The zigzag threshold is max(minPct% of price, atrMult x ATR). On index
    // prices the minPct floor usually dominates, so scaling only atrMult would
    // leave both degrees seeing the SAME swings. Both terms scale together.
    const k = opts.majorMult / opts.minorMult;
    const minPct = base.minPct != null ? base.minPct : DEFAULT_OPTS.minPct;
    const minor = analyze(bars, Object.assign({}, base, {atrMult: opts.minorMult, minPct}));
    const major = analyze(bars, Object.assign({}, base, {atrMult: opts.majorMult,
                                                         minPct: minPct * k}));
    const nesting = [];
    const minorAll = [...minor.impulses, ...minor.correctives, ...minor.complex];
    for (let i = 0; i + 1 < major.pivots.length; i++) {
      const from = major.pivots[i].idx, to = major.pivots[i + 1].idx;
      minorAll.forEach(st => {
        const a = st.points[0].idx, b = st.points[st.points.length - 1].idx;
        if (a >= from && b <= to && b > a) {
          nesting.push({majorLeg: i, fromIdx: from, toIdx: to,
                        legDirection: major.pivots[i + 1].price > major.pivots[i].price ? 'up' : 'down',
                        minorId: st.id, minorType: st.type,
                        minorStart: a, minorEnd: b});
        }
      });
    }
    return {minor, major, nesting};
  }

  global.EW = {
    VERSION: '1.4.0',
    computeZigzag, detectImpulses, detectCorrectives, detectComplexCorrectives,
    fibLevelsForImpulse, fibLevelsForCorrective, fibLevelsForComplex,
    invalidation, invalidationForImpulse, invalidationForCorrective,
    invalidationForComplex, assessB,
    analyze, analyzeDegrees, liveCount,
  };
})(typeof window !== 'undefined' ? window : globalThis);
