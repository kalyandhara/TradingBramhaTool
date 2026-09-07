/*!
 * svp_structure_signal.js — a structural read from POC / HVN / LVN and shape series.
 *
 * A SECOND, separate construction from `SVP.buildSignal`. That one is a
 * seven-factor weighted composite and it measured a clean negative on 2026-08-29
 * (corr(score, 20d fwd) = -0.041, deciles non-monotonic, BUY-high confidence
 * worse than BUY-low, 5 of 7 families sign-inverted). This is NOT that engine
 * re-skinned and it does not import its score: different inputs, different rules,
 * auditable instead of weighted.
 *
 * It is also NOT absolved by being different. `sequence` scored -0.67 and `va`
 * -0.71 in that attribution, and shape-series and value-area logic are exactly
 * what this uses. So the prior evidence points AGAINST this working, the rules
 * below are a hypothesis, and B-56 is the pre-registered test that settles it.
 * Nothing here is wired into the pipeline until then.
 *
 * ══ THE ONE THING MOST STRUCTURAL SIGNALS GET BACKWARDS ═════════════════════
 *
 * HVN and LVN are NOT "resistance" and "support". They are ACCEPTANCE and
 * REJECTION, and which one acts as a barrier depends on the side price
 * approaches from:
 *
 *   HVN  heavy trade = price ACCEPTED here. Congestion. Approached from BELOW it
 *        is resistance; from ABOVE it is support. Either way price STALLS and
 *        rotates in it — it is a decision zone, and the natural place for a
 *        target or a stop to sit BEHIND.
 *
 *   LVN  thin trade = price REJECTED here. Nobody transacted, so there is no
 *        inventory to defend it. Price traverses an LVN FAST. It is therefore
 *        NOT support and NOT resistance — it is an accelerant and a boundary
 *        between two value areas.
 *
 * Putting a stop below an LVN is putting it in the one place the market moves
 * through quickest; the stop is hit on the way to somewhere else. Stops belong
 * behind an HVN, targets belong at the far side of an LVN.
 *
 * ══ TREND FROM THE SHAPE SERIES ═════════════════════════════════════════════
 *
 * The shapes (P buying / B selling / D directional / I balance) are read TWO
 * ways, and the second is weighted more:
 *
 *   1. SHAPE SEQUENCE — what the recent sessions printed. Informative but noisy;
 *      a single P after four Bs means little.
 *   2. POC MIGRATION — the path of the per-session POCs. This is the cleaner
 *      trend read and the one auction theory actually rests on: a rising POC
 *      means buyers are ACCEPTING higher prices session after session, which is
 *      trend by definition rather than by pattern-matching. Falling POCs mirror.
 *
 * Migration is measured by monotonicity fraction rather than by first-vs-last:
 * two POCs 10% apart with chaos in between is not a trend, and first-vs-last
 * cannot tell the difference.
 *
 * ══ THE RULES, STATED SO THEY CAN BE ARGUED WITH ════════════════════════════
 *
 *   BUY    POC migration RISING (>= MIGRATION_MIN monotonic)
 *      AND price at or above the composite POC (acceptance, not hope)
 *      AND the nearest structure BELOW price is an HVN, not an LVN
 *          (there is inventory under the trade to defend it)
 *      AND the last session shape is P or D (not B, not balance)
 *
 *   SELL   the mirror, with the nearest structure ABOVE being an HVN.
 *
 *   HOLD   everything else — explicitly including "balance" (I-shape dominant)
 *          and any case where migration and shape disagree. A structural read
 *          that fires on every bar is describing the market, not reading it.
 *
 * No weights, no score. Each rule is a named boolean and `why` lists which ones
 * fired, so a disagreement is about a stated rule rather than about a number
 * nobody can decompose. That is the specific failure of the composite this
 * replaces: `trap` carried weight 1.5 and attributed at -0.51, and no reader
 * could have seen that from the card.
 *
 * Public API (window.SVPSTRUCT):
 *   SVPSTRUCT.read(analyzeResult, bars) -> { read, why, levels, trend, ... }
 */
(function (global) {
  'use strict';

  //: Fraction of consecutive POC steps that must agree in sign to call a trend.
  //: 0.6 = "clearly more one-way than not" without demanding a monotone series,
  //: which almost never occurs on real sessions.
  var MIGRATION_MIN = 0.6;

  //: A level nearer than this (in % of price) counts as "price is AT it".
  var AT_TOL_PCT = 1.0;

  function _migration(sessions) {
    if (!sessions || sessions.length < 3) {
      return { dir: 'unknown', frac: 0, n: (sessions || []).length };
    }
    var up = 0, dn = 0, steps = 0;
    for (var i = 1; i < sessions.length; i++) {
      var d = sessions[i].poc - sessions[i - 1].poc;
      if (!isFinite(d) || d === 0) continue;
      steps++;
      if (d > 0) up++; else dn++;
    }
    if (!steps) return { dir: 'flat', frac: 0, n: sessions.length };
    var fUp = up / steps, fDn = dn / steps;
    if (fUp >= MIGRATION_MIN) return { dir: 'rising', frac: +fUp.toFixed(2), n: steps };
    if (fDn >= MIGRATION_MIN) return { dir: 'falling', frac: +fDn.toFixed(2), n: steps };
    return { dir: 'mixed', frac: +Math.max(fUp, fDn).toFixed(2), n: steps };
  }

  function _nearest(zones, price, side) {
    // side: 'above' | 'below'. Zones are {low, high, ...} price pockets.
    var best = null;
    (zones || []).forEach(function (z) {
      var ref = side === 'above' ? z.low : z.high;
      if (side === 'above' ? ref < price : ref > price) return;
      if (!best) { best = z; return; }
      var bref = side === 'above' ? best.low : best.high;
      if (Math.abs(ref - price) < Math.abs(bref - price)) best = z;
    });
    return best;
  }

  function _shapeRun(sessions, n) {
    return (sessions || []).slice(-n).map(function (s) { return s.shape; }).join('');
  }

  function read(res, bars) {
    var out = {
      read: 'HOLD', why: [], against: [], trend: null, levels: {},
      shape_seq: '', last_shape: null, note: null,
    };
    if (!res || !res.sessions || !res.sessions.length || !bars || !bars.length) {
      out.note = 'no sessions — structure not computable';
      return out;
    }
    var price = bars[bars.length - 1].close;
    var sessions = res.sessions;
    var comp = res.composite;

    out.shape_seq = _shapeRun(sessions, 6);
    out.last_shape = sessions[sessions.length - 1].shape;
    var trend = _migration(sessions);
    out.trend = trend;

    // Structure around price. The composite profile is the right one for this:
    // per-session pockets are too fine to act as barriers across sessions.
    var prof = res.compositeProfile || null;
    var hvns = prof ? prof.hvnZones : [];
    var lvns = prof ? prof.lvnZones : [];

    var hvnAbove = _nearest(hvns, price, 'above');
    var hvnBelow = _nearest(hvns, price, 'below');
    var lvnAbove = _nearest(lvns, price, 'above');
    var lvnBelow = _nearest(lvns, price, 'below');

    out.levels = {
      poc: comp ? comp.poc : null,
      vah: comp ? comp.vah : null,
      val: comp ? comp.val : null,
      // Named by ROLE, not by node type, so the caller cannot re-introduce the
      // "LVN = support" error downstream.
      resistance_hvn: hvnAbove ? hvnAbove.low : null,
      support_hvn: hvnBelow ? hvnBelow.high : null,
      fast_zone_above: lvnAbove ? lvnAbove.low : null,
      fast_zone_below: lvnBelow ? lvnBelow.high : null,
    };

    // Which structure is nearer below: an HVN (inventory to defend) or an LVN
    // (a trapdoor)? This is the rule the classic phrasing gets backwards.
    var dBelowHvn = hvnBelow ? price - hvnBelow.high : Infinity;
    var dBelowLvn = lvnBelow ? price - lvnBelow.high : Infinity;
    var floorIsHvn = dBelowHvn < dBelowLvn;

    var dAboveHvn = hvnAbove ? hvnAbove.low - price : Infinity;
    var dAboveLvn = lvnAbove ? lvnAbove.low - price : Infinity;
    var ceilIsHvn = dAboveHvn < dAboveLvn;

    var abovePoc = comp && isFinite(comp.poc) ? price >= comp.poc : false;
    var belowPoc = comp && isFinite(comp.poc) ? price <= comp.poc : false;
    var lastS = out.last_shape;
    var balance = out.shape_seq.split('').filter(function (c) { return c === 'I'; }).length
                  >= Math.ceil(out.shape_seq.length / 2);

    function rule(name, ok, detail) {
      (ok ? out.why : out.against).push(name + (detail ? ' — ' + detail : ''));
      return ok;
    }

    if (balance) {
      out.read = 'HOLD';
      out.why.push('balance dominant (' + out.shape_seq + ') — rotation, not trend');
      return out;
    }

    var buy = [
      rule('POC migration rising', trend.dir === 'rising',
           trend.dir + ' ' + trend.frac),
      rule('price accepted at/above composite POC', abovePoc),
      rule('floor below is an HVN, not an LVN', floorIsHvn,
           floorIsHvn ? 'inventory under the trade' : 'nearest structure below is a fast zone'),
      rule('last session shape P or D', lastS === 'P' || lastS === 'D', lastS),
    ];
    if (buy.every(Boolean)) {
      out.read = 'BUY';
      return out;
    }

    // Reset the ledger for the short side so `why` describes the read returned.
    out.why = []; out.against = [];
    var sell = [
      rule('POC migration falling', trend.dir === 'falling',
           trend.dir + ' ' + trend.frac),
      rule('price rejected at/below composite POC', belowPoc),
      rule('ceiling above is an HVN, not an LVN', ceilIsHvn,
           ceilIsHvn ? 'supply overhead' : 'nearest structure above is a fast zone'),
      rule('last session shape B or D', lastS === 'B' || lastS === 'D', lastS),
    ];
    if (sell.every(Boolean)) {
      out.read = 'SELL';
      return out;
    }

    out.read = 'HOLD';
    return out;
  }

  global.SVPSTRUCT = { VERSION: '0.1.0', read: read, MIGRATION_MIN: MIGRATION_MIN,
                       AT_TOL_PCT: AT_TOL_PCT };
})(typeof window !== 'undefined' ? window : globalThis);
