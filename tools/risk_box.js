/*!
 * risk_box.js — entry / stop / ±R levels and a position size, as a chart overlay.
 *
 * LuxAlgo Risk & Exits step 1 (R-multiple framework + fixed-fractional sizing).
 * Pure computation, no DOM and no charting-library dependency, mirroring
 * psar.js / renko.js. Rendering lives in chart_dashboard.html.
 *
 * ── This is bookkeeping, not a signal ───────────────────────────────────────
 * It draws what a trade WOULD risk and how many shares keep a stop-out to a
 * fixed slice of capital. It says nothing about whether the trade is good. The
 * default 2% risk is the owner's PRIOR, not a measured number.
 *
 * ── One rule, two languages ─────────────────────────────────────────────────
 * `size()` mirrors `position_sizing.shares_for_risk` and `defaultStop()` mirrors
 * the stop `stock_council.judge` prints. test_risk_box.py runs both and holds
 * them equal, so the chart cannot quietly size differently from the trade card.
 */
(function (global) {
  'use strict';

  const RISK_PER_TRADE_PCT = 2.0;   // == position_sizing.RISK_PER_TRADE_PCT
  const MAX_POSITION_PCT = 100.0;   // == position_sizing.MAX_POSITION_PCT
  const ATR_STOP_MULT = 1.5;        // == stock_council.ATR_STOP_MULT
  const SWING_LOOKBACK = 10;        // == stock_council's swing_low_10
  const ATR_PERIOD = 14;
  const TARGETS_R = [1, 2, 3];

  const ok = v => typeof v === 'number' && Number.isFinite(v);

  // Wilder ATR, seeded with the simple mean of the first `period` true ranges.
  function atr(bars, period) {
    if (!bars || bars.length < period) return null;
    let prev = null, val = null, sum = 0;
    for (let i = 0; i < bars.length; i++) {
      const b = bars[i];
      const tr = prev === null ? b.high - b.low
        : Math.max(b.high - b.low, Math.abs(b.high - prev), Math.abs(b.low - prev));
      prev = b.close;
      if (i < period) { sum += tr; if (i === period - 1) val = sum / period; }
      else val = (val * (period - 1) + tr) / period;
    }
    return val;
  }

  // The trade card's stop: the lower of the 10-bar swing low and close − 1.5×ATR14,
  // or close − 1.5×ATR14 when the swing low is not below price.
  function defaultStop(bars) {
    if (!bars || !bars.length) return null;
    const price = bars[bars.length - 1].close;
    const a = atr(bars, ATR_PERIOD);
    const swing = Math.min(...bars.slice(-SWING_LOOKBACK).map(b => b.low));
    if (ok(swing) && swing < price) {
      return Math.min(swing, price - ATR_STOP_MULT * (a || 0));
    }
    return ok(a) ? price - ATR_STOP_MULT * a : null;
  }

  // Whole shares so a stop-out costs at most riskPct of capital (floored), capped
  // so the position never exceeds capPct of capital. Same fields as the Python.
  function size(capital, entry, stop, riskPct = RISK_PER_TRADE_PCT,
                capPct = MAX_POSITION_PCT) {
    if (![capital, entry, stop].every(ok) || capital <= 0 || entry <= 0 ||
        stop <= 0 || entry === stop) return null;
    const r = Math.abs(entry - stop);
    const budget = capital * riskPct / 100;
    const qtyRisk = Math.floor(budget / r);
    const qtyCap = Math.floor(capital * capPct / 100 / entry);
    const qty = Math.max(0, Math.min(qtyRisk, qtyCap));
    return {
      qty, r_per_share: r, risk_amount: qty * r, risk_budget: budget,
      notional: qty * entry, position_pct: qty * entry / capital * 100,
      capped: qtyCap < qtyRisk,
    };
  }

  // Full box: side from where the stop sits, ±R target prices, the size, and
  // where `last` stands in R (null without a last price).
  function compute({capital, riskPct = RISK_PER_TRADE_PCT, entry, stop, last,
                    targetsR = TARGETS_R} = {}) {
    if (![entry, stop].every(ok) || entry <= 0 || stop <= 0 || entry === stop) return null;
    const long = stop < entry;
    const r = Math.abs(entry - stop);
    const sgn = long ? 1 : -1;
    return {
      side: long ? 'long' : 'short',
      entry, stop, r,
      stop_pct: r / entry * 100,
      targets: targetsR.map(m => ({r: m, price: entry + sgn * m * r})),
      size: size(capital, entry, stop, riskPct),
      last_r: ok(last) ? sgn * (last - entry) / r : null,
    };
  }

  global.RISKBOX = {
    VERSION: '1.0.0', compute, size, defaultStop, atr,
    RISK_PER_TRADE_PCT, MAX_POSITION_PCT, ATR_STOP_MULT, TARGETS_R,
  };
})(typeof window !== 'undefined' ? window : globalThis);
