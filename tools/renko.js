/*!
 * renko.js — price-sampled (time-independent) brick series computed from OHLC bars.
 *
 * B-43. Renko replaces the time axis with a price grid: a brick prints only when price
 * has travelled a full brick, so a quiet market stops producing bars instead of producing
 * noisy ones. See concepts/Renko-Charts.md.
 *
 * This module computes Renko STRUCTURE and hands it back keyed to the underlying bars —
 * it never asks the caller to plot bricks instead of candles. That is the whole point of
 * "Renko intelligence on candles": the bricks are the analysis, the candles stay the
 * chart. No DOM / charting-library dependency, mirroring adx_di.js and evwma_vwap_macd.js.
 *
 * ── Three decisions that make this backtestable rather than decorative ────────
 *
 * 1. CLOSE-BASED bricks, not high/low. A brick completed by a CLOSE has an unambiguous
 *    bar and is fillable at that bar's next open. A brick completed intrabar by a wick
 *    completes at a price nobody can prove they would have received, which is how Renko
 *    backtests manufacture fake equity curves. Wick-based Renko is prettier and untestable.
 *
 * 2. CAUSAL brick sizing, recomputed in EPOCHS. The obvious "brick = ATR(5)" is a
 *    look-ahead trap: ATR moves every bar, and rebuilding the whole grid from the LATEST
 *    ATR repaints all of history (this is what most charting platforms' ATR-Renko does,
 *    and it is fine for looking at, fatal for measuring). Here the brick is recomputed
 *    only every `epochBars` bars, from ATR over bars STRICTLY BEFORE that point, and then
 *    held fixed until the next epoch. Every brick in the output was therefore computable
 *    at the time it printed. A single fixed brick for all history would be worse: a brick
 *    sized for RELIANCE at Rs 232 is noise at Rs 1,316.
 *
 * 3. The brick is DERIVED, not tuned. `brick = ATR(atrPeriod)` of the timeframe being
 *    traded — the generalisation of the source's rule ("ATR(5) on a session-length bar
 *    divided by the execution bars in a session" is exactly "the average range of one
 *    execution bar"). On a daily chart the session-length bar IS the daily bar, so the
 *    divisor is 1 and the rule reduces to ATR of the chart's own bars. Leave it alone:
 *    with a free brick size almost any Renko system can be fitted to any history.
 *
 * Public API (window.RENKO):
 *   RENKO.compute(bars, opts) -> {
 *     bricks,      // {time,index,open,close,dir,brick}[] — `index`/`time` = the BAR that
 *                  //   completed it, so several bricks can share one bar
 *     flips,       // direction changes: {time,index,dir,price,bricksInPrior}[]
 *     path,        // {time,value}[] step series (last brick close per bar) for drawing
 *     epochs,      // {index,time,brick}[] — brick size in force from each point
 *     state,       // {dir, bricks, brick, lastClose} at the final bar
 *     opts
 *   }
 * Bar shape: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    atrPeriod: 5,      // the source's lookback: "ATR for the last five trading sessions"
    epochBars: 20,     // re-size the brick roughly monthly on a daily chart
    warmup: 30,        // bars consumed before the first brick can print
    reversal: 2,       // bricks needed to turn — the classic Renko definition
  };

  // Wilder ATR, matching chart_dashboard.atrSeries bar-for-bar so the brick size the
  // chart draws is the brick size the backtest scores.
  function atrArray(bars, period) {
    const out = new Array(bars.length).fill(NaN);
    let prevClose = null, atr = null;
    const trs = [];
    for (let i = 0; i < bars.length; i++) {
      const b = bars[i];
      const tr = prevClose === null
        ? b.high - b.low
        : Math.max(b.high - b.low, Math.abs(b.high - prevClose), Math.abs(b.low - prevClose));
      trs.push(tr);
      prevClose = b.close;
      if (i === period - 1) {
        atr = trs.slice(0, period).reduce((a, v) => a + v, 0) / period;
        out[i] = atr;
      } else if (i > period - 1) {
        atr = (atr * (period - 1) + tr) / period;
        out[i] = atr;
      }
    }
    return out;
  }

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const empty = {bricks: [], flips: [], path: [], epochs: [], state: null, opts};
    if (!bars || bars.length < opts.warmup + opts.atrPeriod + 5) return empty;

    const atr = atrArray(bars, opts.atrPeriod);
    const bricks = [], flips = [], path = [], epochs = [];

    let brick = null;                 // current brick size
    let lastClose = null;             // close of the last completed brick
    let dir = 0;                      // +1 up, -1 down, 0 before the first brick
    let bricksInDir = 0;

    for (let i = 0; i < bars.length; i++) {
      // Epoch boundary: re-derive the brick from ATR at the PREVIOUS bar. Using atr[i]
      // would fold the current bar's own range into the size of the brick that bar is
      // about to complete — small, but it is look-ahead, and this module exists to be
      // measured.
      if (i >= opts.warmup && (lastClose === null || (i - opts.warmup) % opts.epochBars === 0)) {
        const a = atr[i - 1];
        if (isFinite(a) && a > 0) {
          brick = a;
          epochs.push({index: i, time: bars[i].time, brick: +a.toFixed(4)});
          if (lastClose === null) {
            lastClose = bars[i].close;   // anchor the grid at the first usable close
            dir = 0;
          }
        }
      }
      if (lastClose === null || !(brick > 0)) { path.push({time: bars[i].time, value: null}); continue; }

      const c = bars[i].close;
      // Emit every brick this close completes. A single bar can complete several — a gap
      // through four bricks prints four, all stamped with this bar, because that is the
      // bar you could have acted on.
      for (let guard = 0; guard < 1000; guard++) {
        let moved = false;
        const rev = opts.reversal;
        if (dir >= 0 && c >= lastClose + brick) {
          const from = lastClose; lastClose += brick;
          if (dir !== 1) { dir = 1; bricksInDir = 0; }
          bricksInDir++;
          bricks.push({time: bars[i].time, index: i, open: from, close: lastClose, dir: 1, brick});
          moved = true;
        } else if (dir <= 0 && c <= lastClose - brick) {
          const from = lastClose; lastClose -= brick;
          if (dir !== -1) { dir = -1; bricksInDir = 0; }
          bricksInDir++;
          bricks.push({time: bars[i].time, index: i, open: from, close: lastClose, dir: -1, brick});
          moved = true;
        } else if (dir === 1 && c <= lastClose - rev * brick) {
          // Reversal: the turn costs `reversal` bricks of travel, and the new brick's
          // body starts one brick back from the old close (the classic offset).
          const from = lastClose - brick; lastClose -= rev * brick;
          flips.push({time: bars[i].time, index: i, dir: -1, price: c, bricksInPrior: bricksInDir});
          dir = -1; bricksInDir = 1;
          bricks.push({time: bars[i].time, index: i, open: from, close: lastClose, dir: -1, brick});
          moved = true;
        } else if (dir === -1 && c >= lastClose + rev * brick) {
          const from = lastClose + brick; lastClose += rev * brick;
          flips.push({time: bars[i].time, index: i, dir: 1, price: c, bricksInPrior: bricksInDir});
          dir = 1; bricksInDir = 1;
          bricks.push({time: bars[i].time, index: i, open: from, close: lastClose, dir: 1, brick});
          moved = true;
        }
        if (!moved) break;
      }
      path.push({time: bars[i].time, value: +lastClose.toFixed(4)});
    }

    const state = lastClose === null ? null : {
      dir, bricks: bricksInDir, brick: brick ? +brick.toFixed(4) : null,
      lastClose: +lastClose.toFixed(4),
    };
    return {bricks, flips, path, epochs, state, opts};
  }

  global.RENKO = {VERSION: '1.0.0', compute};
})(typeof window !== 'undefined' ? window : globalThis);
