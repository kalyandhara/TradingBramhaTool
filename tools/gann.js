/*!
 * gann.js — Gann Square-of-9 support/resistance levels + an HONEST break-odds card.
 *
 * Pure computation library: no DOM, no charting-library dependency. Rendering
 * lives in chart_dashboard.html (renderGann()), matching volume_profile.js /
 * fibonacci.js.
 *
 * ── Why this exists, and what it deliberately does NOT do ────────────────────
 * A Gann fan is drawing, not analysis: its angles are SCALE-dependent (how many
 * index points equal "one time unit" is a free parameter) and ANCHOR-dependent,
 * so with enough fans from enough pivots some line touches any later turn. We
 * do not draw the fan. We draw only the Square-of-9 *horizontal* levels, which
 * are deterministic (a pure function of price), and we attach a break heuristic
 * whose probability is measured from THIS instrument's own history — not a
 * Gann "confidence" number invented to look authoritative.
 *
 * The honest finding this repo already established (new-moon levels backtest,
 * SBC vedha backtest): a line at any recent extreme acts as generic S/R about
 * half the time. So the card's job is not to sell a level — it is to tell you
 * the base-rate odds of follow-through if a level breaks, so the "Gann" framing
 * cannot smuggle in confidence it has not earned.
 *
 * ── The break heuristic (what the card says) ────────────────────────────────
 * "Price P sits between support S and resistance R (nearest SO9 levels).
 *   If R breaks up   -> historical continuation ~ pUp%  (n=nUp)  toward R2.
 *   If S breaks down -> historical continuation ~ pDown% (n=nDn) toward S2."
 * pUp / pDown are the empirical follow-through rates of a prior-N-bar-extreme
 * breakout on this symbol/timeframe; `base` is the unconditional up-rate for
 * comparison. If pUp is not clearly above base, the breakout carries no edge.
 *
 * NOT ADVICE. Levels and odds are arithmetic consequences of the rules below,
 * shown so they can be checked. Not a recommendation to take any trade.
 *
 * Public API (window.GANN):
 *   GANN.sq9Levels(price, bandPct)              -> level[]  ({price, k, deg, cardinal})
 *   GANN.nearestSR(levels, price)               -> {support, resistance}
 *   GANN.breakOdds(bars, lookback, horizon)     -> {pUp,nUp,pDown,nDn,base,nBase}
 *   GANN.analyze(bars, opts)                    -> {price, support, resistance,
 *                                                   secondUp, secondDown, odds, levels, card}
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  // Square-of-9: each 180 degrees of rotation adds 1 to sqrt(price); a 45-degree
  // step is therefore +/-0.25 on the square root. Levels are (sqrt(P)+k*0.25)^2.
  function sq9Levels(price, bandPct) {
    if (!(price > 0)) return [];
    const band = bandPct || 0.18;
    const s = Math.sqrt(price);
    const out = [];
    for (let k = -20; k <= 20; k++) {
      if (k === 0) continue;
      const lvl = Math.pow(s + k * 0.25, 2);
      if (Math.abs(lvl - price) / price > band) continue;
      const rot = k * 45;                       // signed degrees of rotation
      out.push({
        price: lvl, k, deg: rot,
        cardinal: (Math.abs(rot) % 90) === 0,   // 90/180/270/360 = "hard" angles
      });
    }
    out.sort((a, b) => a.price - b.price);
    return out;
  }

  function nearestSR(levels, price) {
    let support = null, resistance = null;
    for (const lv of levels) {
      if (lv.price < price) support = lv;       // keep last below = closest support
      else if (resistance === null) { resistance = lv; break; }
    }
    return { support, resistance };
  }

  // Empirical follow-through: when price closed beyond the prior `lookback`-bar
  // extreme, did it continue `horizon` bars later? This is the honest number —
  // it is this symbol/timeframe's own breakout base rate, not a Gann claim.
  function breakOdds(bars, lookback, horizon) {
    lookback = lookback || 20;
    horizon = horizon || 5;
    let nUp = 0, fUp = 0, nDn = 0, fDn = 0, nBase = 0, fBase = 0;
    for (let i = lookback; i < bars.length - horizon; i++) {
      let hi = -Infinity, lo = Infinity;
      for (let j = i - lookback; j < i; j++) {
        if (bars[j].high > hi) hi = bars[j].high;
        if (bars[j].low < lo) lo = bars[j].low;
      }
      const c = bars[i].close, fut = bars[i + horizon].close;
      nBase++; if (fut > c) fBase++;
      if (c > hi) { nUp++; if (fut > c) fUp++; }
      if (c < lo) { nDn++; if (fut < c) fDn++; }
    }
    return {
      pUp: nUp ? fUp / nUp : 0, nUp,
      pDown: nDn ? fDn / nDn : 0, nDn,
      base: nBase ? fBase / nBase : 0, nBase,
    };
  }

  function analyze(bars, opts) {
    opts = opts || {};
    if (!bars || bars.length < 40) return null;
    const price = bars[bars.length - 1].close;
    const levels = sq9Levels(price, opts.bandPct);
    const { support, resistance } = nearestSR(levels, price);
    // Second targets: the next SO9 level beyond each nearest S/R.
    let secondUp = null, secondDown = null;
    if (resistance) {
      secondUp = levels.find(l => l.price > resistance.price) || null;
    }
    for (const l of levels) {
      if (support && l.price < support.price) secondDown = l; // last below support
    }
    const odds = breakOdds(bars, opts.lookback, opts.horizon);

    // Edge flags: is breakout follow-through clearly above the unconditional
    // base rate? If not, the level carries no directional edge — say so.
    const upEdge = odds.pUp - odds.base;
    const dnEdge = (1 - odds.pDown) < odds.base ? (odds.pDown - (1 - odds.base)) : (odds.pDown - (1 - odds.base));
    const card = {
      price,
      up: resistance ? {
        level: resistance.price, deg: resistance.deg,
        prob: odds.pUp, n: odds.nUp,
        target: secondUp ? secondUp.price : null,
        edge: upEdge,
      } : null,
      down: support ? {
        level: support.price, deg: support.deg,
        prob: odds.pDown, n: odds.nDn,
        target: secondDown ? secondDown.price : null,
        edge: odds.pDown - (1 - odds.base),
      } : null,
      base: odds.base,
    };
    return { price, support, resistance, secondUp, secondDown, odds, levels, card };
  }

  global.GANN = { sq9Levels, nearestSR, breakOdds, analyze };
})(typeof window !== 'undefined' ? window : globalThis);
