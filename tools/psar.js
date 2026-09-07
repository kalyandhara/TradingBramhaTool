/*!
 * psar.js — Wilder's Parabolic SAR (stop and reverse), as a chart overlay.
 *
 * B-59. Pure computation, no DOM and no charting-library dependency, mirroring
 * renko.js / supertrend_ai.js / fibonacci.js. Rendering lives in
 * chart_dashboard.html.
 *
 * ── Why this is an OVERLAY and not a scanner ────────────────────────────────
 * B-46 already ruled Parabolic SAR out of the registry: `pmax` and `stai`
 * occupy the trailing-stop-flip role, and a third would risk another zero-unique
 * entry of the kind analyses/Scanner-Overlap-Audit trimmed. That objection is
 * about a SCANNER — a detector that fires where others already fire adds
 * decisions without adding information. An overlay makes no claim and votes in
 * nothing, which is the same split B-46 itself applied to Ichimoku ("ship the
 * overlay first; any BUY/SELL reading is a separate, measured question").
 *
 * So: this draws. Before any PSAR *signal* ships, what is owed first is an
 * OVERLAP CHECK against pmax and stai — not an edge test. If its flips are a
 * subset of PMax's there is nothing left to measure.
 *
 * ── Causality, which is the whole reason to write this carefully ────────────
 * `path[i]` is computed from bar i-1's SAR, EP and AF, and clamped by the lows
 * (or highs) of bars i-1 and i-2. **It uses nothing from bar i**, so the dot is
 * known at bar i's OPEN. That is what makes it honest to plot and honest to
 * backtest later.
 *
 * A naive implementation seats today's dot from today's extreme. It looks almost
 * identical on a chart and it repaints: every measurement built on it inherits a
 * peek at the bar it is supposed to be trading. `flips` is the one thing that
 * uses bar i's own range — a reversal is only knowable once the bar has traded —
 * so each flip carries its bar index and is fillable at that bar's NEXT open,
 * the same treatment renko.js gives its brick flips.
 *
 * ── Wilder's rule, stated so the parameters are not quietly invented ────────
 *   SAR(next) = SAR + AF x (EP - SAR)
 *   AF starts at 0.02, steps 0.02 on each NEW extreme, caps at 0.20
 *   On a flip: SAR seats at the prior EP, EP becomes the new extreme, AF resets
 *
 * And the clamp everyone omits: **SAR may not penetrate the range of either of
 * the last two bars** on the side it is trailing. Without it the dot can jump
 * inside recent price and manufacture a reversal that never happened.
 *
 * NOT ADVICE. The dots are arithmetic, shown so they can be checked.
 *
 * Public API (window.PSAR):
 *   PSAR.compute(bars, opts) -> {path, up, dn, flips, state, opts}
 *
 * Bar shape expected: {time, open, high, low, close}
 */
(function (global) {
  'use strict';

  // Wilder's originals. Named rather than inlined so a caller overriding them is
  // visibly departing from the standard rather than quietly retuning it.
  const AF_START = 0.02;
  const AF_STEP = 0.02;
  const AF_MAX = 0.20;

  /**
   * Parabolic SAR over `bars`.
   *
   * Returns:
   *   path   [{time, value, dir}]  one dot per bar from the seed onward
   *   up     [{time, value}]       dots while long (below price) — for colouring
   *   dn     [{time, value}]       dots while short (above price)
   *   flips  [{time, index, dir, price}]  dir 1 = to long, -1 = to short.
   *          `index` is the bar whose range triggered it, fillable at index+1's open.
   *   state  {dir, sar, ep, af} after the last bar, or null
   */
  function compute(bars, opts) {
    opts = opts || {};
    const afStart = opts.afStart != null ? opts.afStart : AF_START;
    const afStep = opts.afStep != null ? opts.afStep : AF_STEP;
    const afMax = opts.afMax != null ? opts.afMax : AF_MAX;

    const path = [], up = [], dn = [], flips = [];
    if (!bars || bars.length < 3) {
      return {path, up, dn, flips, state: null, opts: {afStart, afStep, afMax}};
    }

    // ── Seed ──────────────────────────────────────────────────────────────────
    // Direction from the first two bars, SAR at the opposite extreme of bar 0,
    // EP at the favourable extreme of bar 1. Deterministic and uses no future
    // data; a longer warmup would only move where the arbitrary start sits, and
    // SAR converges away from its seed within a few bars regardless.
    let dir = bars[1].close >= bars[0].close ? 1 : -1;
    let sar = dir === 1 ? bars[0].low : bars[0].high;
    let ep = dir === 1 ? bars[1].high : bars[1].low;
    let af = afStart;

    for (let i = 2; i < bars.length; i++) {
      const b = bars[i];
      const p1 = bars[i - 1];
      const p2 = bars[i - 2];

      // The dot for THIS bar, from state that predates it entirely.
      let next = sar + af * (ep - sar);

      // Wilder's two-bar clamp. Trailing a long, the stop may not sit above
      // either recent low; trailing a short, not below either recent high.
      if (dir === 1) {
        next = Math.min(next, p1.low, p2.low);
      } else {
        next = Math.max(next, p1.high, p2.high);
      }

      path.push({time: b.time, value: +next.toFixed(4), dir});
      (dir === 1 ? up : dn).push({time: b.time, value: +next.toFixed(4)});

      // ── Now the bar trades, and only now can a reversal be known ───────────
      if (dir === 1) {
        if (b.low < next) {
          // Flip to short: SAR seats at the extreme the long run reached.
          dir = -1;
          sar = ep;
          ep = b.low;
          af = afStart;
          flips.push({time: b.time, index: i, dir: -1, price: +b.close.toFixed(4)});
        } else {
          if (b.high > ep) { ep = b.high; af = Math.min(af + afStep, afMax); }
          sar = next;
        }
      } else {
        if (b.high > next) {
          dir = 1;
          sar = ep;
          ep = b.high;
          af = afStart;
          flips.push({time: b.time, index: i, dir: 1, price: +b.close.toFixed(4)});
        } else {
          if (b.low < ep) { ep = b.low; af = Math.min(af + afStep, afMax); }
          sar = next;
        }
      }
    }

    return {
      path, up, dn, flips,
      state: {dir, sar: +sar.toFixed(4), ep: +ep.toFixed(4), af: +af.toFixed(4)},
      opts: {afStart, afStep, afMax},
    };
  }

  global.PSAR = {VERSION: '1.0.0', compute, AF_START, AF_STEP, AF_MAX};
})(typeof window !== 'undefined' ? window : globalThis);
