/*!
 * fibonacci.js — auto-anchored Fibonacci levels + an entry/stop/target plan
 * built from confluence with the Price Projection and the Volume Profile.
 *
 * Pure computation library: no DOM, no charting-library dependency. Rendering
 * lives in chart_dashboard.html (drawFibonacci()), matching the separation of
 * concerns in volume_profile.js and elliott_wave.js.
 *
 * ── Why this exists ─────────────────────────────────────────────────────────
 * A Fibonacci grid on its own is drawing, not analysis: every chart has a
 * 0.618 somewhere and price will touch it eventually. A level only earns
 * attention when something INDEPENDENT of Fibonacci agrees with it. So the
 * levels here are scored against two sources the repo already computes:
 *
 *   • Volume Profile (volume_profile.js) — POC / Value Area edges / HVN / LVN.
 *     Real traded volume at a price is evidence that price is defended there.
 *   • Price Projection (projection.py via /api/projection) — a deterministic
 *     forward target that already carries its own `invalidation` stop level.
 *
 * A level backed by neither is drawn faintly and never becomes an entry.
 *
 * ── Anchoring ───────────────────────────────────────────────────────────────
 * Swings come from EW.computeZigzag (elliott_wave.js), NOT a second pivot
 * finder written here. That detector is volatility-adaptive and non-repainting,
 * and reusing it means the Fibonacci grid and the Elliott overlay can never
 * disagree about where the swing is — which they would, immediately and
 * visibly, if each found its own pivots.
 *
 * Its trailing pivot is PROVISIONAL: it tracks a still-forming extreme and can
 * extend until a future bar confirms a reversal. A swing anchored on it can
 * therefore move. That is surfaced as `swing.provisional` rather than hidden,
 * because a trade plan measured off a level that may shift is a materially
 * different thing from one measured off a confirmed pivot.
 *
 * ── Guardrails ──────────────────────────────────────────────────────────────
 * Mirrors projection.py's anti-overtrust stance. `buildPlan()` returns a plan
 * whose `actionable` flag is false, with a stated reason, when:
 *   • no Fibonacci level has any independent confluence;
 *   • the projection points against the swing direction;
 *   • reward-to-risk falls below MIN_RR.
 * It reports the conflict instead of quietly picking the flattering read.
 *
 * NOT ADVICE. Entry / stop / target are the arithmetic consequences of the
 * rules below, shown so they can be checked. They are not a recommendation to
 * take the trade.
 *
 * Public API (window.FIB):
 *   FIB.detectSwing(bars, opts)                -> swing | null
 *   FIB.computeLevels(swing, opts)             -> level[]
 *   FIB.scoreLevels(levels, profile, tolPct)   -> level[]  (adds .matches/.score)
 *   FIB.buildPlan(swing, levels, ctx)          -> plan | null
 *   FIB.analyze(bars, ctx, opts)               -> {swing, levels, plan}
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  // Retracements of the impulse leg. 0.236 is included for completeness but is
  // never eligible as an entry: a 23.6% pullback is noise inside the leg, not a
  // structural test of it. 0.886 is the deep end — see DEEP_RETRACEMENT.
  const RETRACEMENTS = [0.236, 0.382, 0.5, 0.618, 0.786, 0.886];

  // 0.886 exists because the QM / CHOCH setups price their deepest entry there,
  // and 1.13 because those same setups put the stop there. Both were missing, so
  // a reader following that method had to compute them by hand off a grid that
  // stopped at 0.786.
  //
  // They are DRAWN AND COMPUTED, and deliberately NOT wired into buildPlan:
  //
  //   • 0.886 is not entry-eligible by default. A retracement that deep is the
  //     stop-hunt read, not "the leg is still intact" — and on this desk the
  //     stop-hunt read already has a measured home in the Liquidity Sweep
  //     scanner (B-41m: +0.51% @20d, p=0.005), which is a different and better
  //     tested way to express it. Pass {deepEntry: true} to computeLevels to
  //     make it eligible.
  //   • 1.13 never becomes the plan's stop automatically. It sits 13% of the leg
  //     BEYOND the origin, so adopting it would widen every existing stop and
  //     silently change the reward-to-risk — and therefore the `actionable`
  //     flag — on plans that have nothing to do with QM. Changing what a stop
  //     means is a measurement, not a default.
  //
  // In short: the levels are now available to look at and to build on; which of
  // them may move money is unchanged until something measures it.
  const DEEP_RETRACEMENT = 0.886;

  // Entry can only come from this band — the region where a pullback is deep
  // enough to be a real test yet shallow enough that the leg is still intact.
  const ENTRY_BAND = [0.382, 0.786];
  const DEEP_ENTRY_BAND = [0.382, 0.886];

  // Beyond the leg ORIGIN, in the retracement direction — an overshoot of the
  // swing rather than a projection past it. This is where invalidation lives:
  // at 1.13 the leg that defined the setup has been fully given back and then
  // some. Distinct from EXTENSIONS, which run the other way and are targets.
  const OVERSHOOTS = [1.13];

  // Projections beyond the swing, measured from the leg origin.
  const EXTENSIONS = [1.272, 1.618];

  // Proximity for "this Fibonacci level and that volume node are the same
  // level". Matches volume_profile.js's own default so the two modules agree on
  // what counts as touching.
  const DEFAULT_TOL_PCT = 0.004; // 0.4%

  // Below this reward-to-risk the plan is reported but marked not actionable.
  const MIN_RR = 1.5;

  // Stop placement when the projection supplies no invalidation: just beyond
  // the leg origin, far enough that ordinary noise at the extreme does not
  // trigger it.
  const STOP_BUFFER_PCT = 0.005; // 0.5% past the swing extreme

  // ── Why the trailing pivot is not used as the swing endpoint ────────────────
  // EW.computeZigzag ends with a PROVISIONAL pivot that tracks the running
  // extreme since the last confirmed reversal. It is not a swing endpoint: it
  // re-seats onto any new extreme, so it sits on or within a bar or two of the
  // last bar almost always. Measured over rolling windows of real daily data it
  // was 0 bars old in 73% of cases and never older than 4.
  //
  // Anchoring the grid there would therefore move the entry and the stop on
  // nearly every new bar — a plan you cannot hold, and the specific failure
  // mode that makes automated Fibonacci untrustworthy.
  //
  // So the default anchor is the last CONFIRMED leg: both endpoints are pivots
  // the zigzag has already validated and can never revise. The levels stop
  // moving, and where price currently sits relative to them is handled
  // separately by the `missed` check.

  // ── Swing detection ─────────────────────────────────────────────────────────

  /**
   * Dominant recent swing: the last CONFIRMED leg between two zigzag pivots.
   *
   * Pass `{useProvisional: true}` to anchor on the still-forming trailing
   * extreme instead — closer to what a trader drawing by hand would use, at the
   * cost of levels that move as the extreme extends. Off by default; see the
   * FORMING note above for the measurement behind that choice.
   *
   * Returns null when there is not enough movement to establish a leg.
   */
  function detectSwing(bars, opts) {
    if (!global.EW || typeof global.EW.computeZigzag !== 'function') return null;
    if (!bars || bars.length < 20) return null;
    opts = opts || {};

    const pivots = global.EW.computeZigzag(bars, opts);
    if (!pivots || pivots.length < 2) return null;

    // Drop the trailing provisional tracker unless explicitly asked for it. With
    // only two pivots available there is no confirmed leg to fall back to, so
    // the provisional one is used and flagged.
    const confirmed = pivots.filter(p => !p.provisional);
    let usable = pivots, provisionalAnchor = true;
    if (!opts.useProvisional && confirmed.length >= 2) {
      usable = confirmed;
      provisionalAnchor = false;
    }

    const b = usable[usable.length - 1];
    const a = usable[usable.length - 2];
    if (a.type === b.type) return null; // zigzag alternates; defensive only

    const up = b.type === 'high';
    const high = up ? b.price : a.price;
    const low  = up ? a.price : b.price;
    const range = high - low;
    if (!(range > 0)) return null;

    return {
      direction: up ? 'up' : 'down',   // direction of the leg being retraced
      high, low, range,
      highIdx:  up ? b.idx  : a.idx,
      lowIdx:   up ? a.idx  : b.idx,
      highTime: up ? b.time : a.time,
      lowTime:  up ? a.time : b.time,
      startTime: a.time, endTime: b.time,
      // True only when no confirmed leg existed and the forming extreme had to
      // be used — in which case the levels below CAN still move.
      provisional: provisionalAnchor,
      // Bars elapsed since the leg ended. A leg that closed long ago may have
      // been superseded by structure the grid does not describe; surfaced so
      // that staleness is visible rather than assumed away.
      barsSinceSwing: (bars.length - 1) - b.idx,
    };
  }

  // ── Levels ──────────────────────────────────────────────────────────────────

  /**
   * Retracement and extension prices for a swing.
   *
   * Retracements are measured back from the leg's terminal extreme; extensions
   * are measured forward from the leg's origin. For an up-leg that means
   * retracements fall from the high and extensions project above it, and the
   * mirror for a down-leg.
   */
  function computeLevels(swing, opts) {
    if (!swing) return [];
    const up = swing.direction === 'up';
    const out = [];
    const band = (opts && opts.deepEntry) ? DEEP_ENTRY_BAND : ENTRY_BAND;

    RETRACEMENTS.forEach(r => {
      const price = up ? swing.high - swing.range * r
                       : swing.low  + swing.range * r;
      out.push({
        ratio: r, price, kind: 'retracement',
        label: `${(r * 100).toFixed(1)}%`,
        // Golden pocket: the 0.5-0.618 band traders actually watch.
        golden: r === 0.5 || r === 0.618,
        // The deep rung is flagged so a caller can style or reason about it
        // without re-testing the ratio and drifting from this definition.
        deep: r === DEEP_RETRACEMENT,
        entryEligible: r >= band[0] && r <= band[1],
      });
    });

    OVERSHOOTS.forEach(r => {
      const price = up ? swing.high - swing.range * r
                       : swing.low  + swing.range * r;
      out.push({
        ratio: r, price, kind: 'overshoot',
        label: `${(r * 100).toFixed(1)}%`,
        golden: false, deep: true,
        // Never an entry: past the origin the leg is gone, and this level is
        // where the setup is wrong rather than where it is cheap.
        entryEligible: false,
      });
    });

    EXTENSIONS.forEach(r => {
      const price = up ? swing.low  + swing.range * r
                       : swing.high - swing.range * r;
      out.push({
        ratio: r, price, kind: 'extension',
        label: `${(r * 100).toFixed(1)}%`,
        golden: false, deep: false, entryEligible: false,
      });
    });

    // The leg's own boundaries matter as much as the ratios between them.
    out.push({ratio: 0, price: up ? swing.high : swing.low, kind: 'anchor',
              label: '0%', golden: false, deep: false, entryEligible: false});
    out.push({ratio: 1, price: up ? swing.low : swing.high, kind: 'anchor',
              label: '100%', golden: false, deep: false, entryEligible: false});

    return out.sort((x, y) => y.price - x.price);
  }

  // ── Confluence scoring ──────────────────────────────────────────────────────

  /**
   * Annotate each level with the Volume Profile zones it coincides with.
   *
   * Delegates to VP.findConfluence rather than re-deriving proximity, so the
   * definition of "touching" stays in one place. Levels with no match keep an
   * empty `matches` and a zero `score`; they are drawn, but can never be
   * promoted to an entry.
   */
  function scoreLevels(levels, profile, tolPct) {
    if (!levels) return [];
    const scored = levels.map(l => Object.assign({}, l, {matches: [], score: 0}));
    if (!profile || !global.VP || typeof global.VP.findConfluence !== 'function') {
      return scored;
    }
    const points = scored.map((l, i) => ({price: l.price, label: l.label, _i: i}));
    const hits = global.VP.findConfluence(points, profile,
                                          tolPct == null ? DEFAULT_TOL_PCT : tolPct);
    hits.forEach(h => {
      const l = scored[h._i];
      if (!l) return;
      l.matches = h.matches;
      l.score = h.matches.length;
    });
    return scored;
  }

  // ── Trade plan ──────────────────────────────────────────────────────────────

  function nearestLevel(levels, price) {
    let best = null, bestD = Infinity;
    levels.forEach(l => {
      const d = Math.abs(l.price - price);
      if (d < bestD) { bestD = d; best = l; }
    });
    return best;
  }

  /**
   * Entry / stop / target derived from the scored levels, the projection, and
   * the swing. `ctx` carries {projection, lastClose}.
   *
   * Every field is accompanied by a reason string naming what produced it, so
   * the plan can be audited on the chart rather than trusted.
   */
  function buildPlan(swing, levels, ctx) {
    if (!swing || !levels || !levels.length) return null;
    ctx = ctx || {};
    const proj = ctx.projection || null;
    const up = swing.direction === 'up';
    const lastClose = ctx.lastClose != null ? ctx.lastClose : null;
    const reasons = [];
    const blockers = [];

    // ── Direction ────────────────────────────────────────────────────────────
    // The swing sets the bias; the projection can only confirm or contradict it.
    // A contradiction is reported, never averaged away.
    let conflict = false;
    if (proj && proj.direction && proj.direction !== swing.direction) {
      conflict = true;
      blockers.push(
        `Price Projection points ${proj.direction} while the swing is ${swing.direction}. ` +
        `Two independent methods disagree on direction, so no entry is proposed.`);
    } else if (proj) {
      reasons.push(
        `Price Projection agrees with the ${swing.direction} swing ` +
        `(${proj.band} confidence, ${proj.source}).`);
    }

    // ── Entry ────────────────────────────────────────────────────────────────
    // The eligible retracement with the most independent backing. Confluence
    // count wins; a deeper retracement breaks ties, since a deeper pullback that
    // still holds is the stronger test.
    const eligible = levels.filter(l => l.kind === 'retracement' && l.entryEligible);
    const ranked = eligible.slice().sort((a, b) =>
      (b.score - a.score) || (b.ratio - a.ratio));
    const entryLevel = ranked[0] || null;

    if (!entryLevel) {
      blockers.push('No retracement level fell inside the 38.2%-78.6% entry band.');
    } else if (entryLevel.score === 0) {
      blockers.push(
        'No Fibonacci level coincides with a volume node (POC, Value Area edge, ' +
        'HVN or LVN). The grid is unconfirmed by traded volume, which is exactly ' +
        'the case where a Fibonacci level means nothing on its own.');
    } else {
      reasons.push(
        `Entry at the ${entryLevel.label} retracement, backed by ` +
        `${entryLevel.matches.map(m => m.type).join(' + ')} from the Volume Profile.`);
    }

    // ── Stop ─────────────────────────────────────────────────────────────────
    // Two independent levels can invalidate this trade: the swing structure
    // breaking, and the projection's own stated invalidation. The stop goes at
    // the FURTHER of the two, because the trade is only demonstrably wrong once
    // both have failed.
    //
    // Taking the tighter one instead would flatter the reward-to-risk — the
    // number the guardrail below is judged on — by placing the stop inside a
    // zone where the thesis is still intact. That is the classic way to be
    // right about direction and still lose: stopped out by noise at a level
    // neither method called invalidation.
    const swingStop = up ? swing.low  * (1 - STOP_BUFFER_PCT)
                         : swing.high * (1 + STOP_BUFFER_PCT);
    let stop = swingStop;
    let stopSource = `${STOP_BUFFER_PCT * 100}% beyond the swing ` +
                     `${up ? 'low' : 'high'} (the level that breaks this swing)`;

    if (proj && typeof proj.invalidation === 'number' && entryLevel) {
      const valid = up ? proj.invalidation < entryLevel.price
                       : proj.invalidation > entryLevel.price;
      if (valid) {
        const wider = up ? Math.min(proj.invalidation, swingStop)
                         : Math.max(proj.invalidation, swingStop);
        stop = wider;
        stopSource = (wider === proj.invalidation)
          ? 'Price Projection invalidation (further than the swing break, so it wins)'
          : `${STOP_BUFFER_PCT * 100}% beyond the swing ${up ? 'low' : 'high'} ` +
            `(further than the projection invalidation, so it wins)`;
      }
    }

    // ── Target ───────────────────────────────────────────────────────────────
    const ext = levels.find(l => l.kind === 'extension' && l.ratio === 1.272);
    let target = ext ? ext.price : null;
    let targetSource = ext ? '127.2% Fibonacci extension' : null;
    if (proj && !conflict && typeof proj.projected_price === 'number') {
      target = proj.projected_price;
      targetSource = `Price Projection target (${proj.source}, ${proj.band} confidence)`;
      const near = nearestLevel(levels.filter(l => l.kind === 'extension'), target);
      if (near && Math.abs(near.price - target) / target <= DEFAULT_TOL_PCT) {
        targetSource += ` — confirmed by the ${near.label} extension`;
        reasons.push(
          `Projection target and the ${near.label} extension land on the same ` +
          `price, which is the strongest form of agreement available here.`);
      }
    }

    // ── Reward / risk ────────────────────────────────────────────────────────
    let rr = null;
    if (entryLevel && target != null) {
      const reward = Math.abs(target - entryLevel.price);
      const risk   = Math.abs(entryLevel.price - stop);
      rr = risk > 0 ? reward / risk : null;
      if (rr != null && rr < MIN_RR) {
        blockers.push(
          `Reward-to-risk is ${rr.toFixed(2)}:1, below the ${MIN_RR}:1 floor. ` +
          `The level structure is real but does not pay for the risk it requires.`);
      }
    }

    // Entry already passed is worth saying plainly: the plan is a record of a
    // level that has been and gone, not a live setup.
    let missed = false;
    if (entryLevel && lastClose != null) {
      missed = up ? lastClose < entryLevel.price * (1 - DEFAULT_TOL_PCT)
                  : lastClose > entryLevel.price * (1 + DEFAULT_TOL_PCT);
      if (missed) {
        blockers.push(
          `Price has already traded through the ${entryLevel.label} entry ` +
          `(last ${lastClose.toFixed(2)} vs ${entryLevel.price.toFixed(2)}). ` +
          `The level is behind price, not ahead of it.`);
      }
    }

    if (swing.provisional) {
      reasons.push(
        'No confirmed leg was available, so the grid is anchored on the ' +
        'still-forming extreme and every level here can shift.');
    } else {
      reasons.push(
        `Anchored on a confirmed leg that ended ${swing.barsSinceSwing} bar(s) ` +
        `ago, so these levels do not move as new bars arrive.`);
    }

    return {
      direction: up ? 'long' : 'short',
      entry:  entryLevel ? entryLevel.price : null,
      entryLabel: entryLevel ? entryLevel.label : null,
      entryMatches: entryLevel ? entryLevel.matches : [],
      stop, stopSource,
      target, targetSource,
      rr, missed, conflict,
      provisional: !!swing.provisional,
      barsSinceSwing: swing.barsSinceSwing,
      actionable: !!(entryLevel && entryLevel.score > 0 && target != null &&
                     rr != null && rr >= MIN_RR && !conflict && !missed),
      reasons, blockers,
    };
  }

  // ── Convenience ─────────────────────────────────────────────────────────────

  function analyze(bars, ctx, opts) {
    const swing = detectSwing(bars, opts);
    if (!swing) return {swing: null, levels: [], plan: null};
    ctx = ctx || {};
    const levels = scoreLevels(computeLevels(swing), ctx.profile, ctx.tolPct);
    const plan = buildPlan(swing, levels, ctx);
    return {swing, levels, plan};
  }

  global.FIB = {
    VERSION: '1.0.0',
    RETRACEMENTS, EXTENSIONS, ENTRY_BAND, MIN_RR,
    detectSwing, computeLevels, scoreLevels, buildPlan, analyze,
  };
})(typeof window !== 'undefined' ? window : globalThis);
