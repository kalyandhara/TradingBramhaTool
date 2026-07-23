/*!
 * fvg.js — Fair Value Gap (3-candle imbalance) detection module.
 *
 * Pure computation library: takes an OHLCV bar array and returns Fair Value
 * Gap zones — the classic ICT/SMC 3-candle imbalance where candle[i-2] and
 * candle[i] don't overlap, leaving a gap that candle[i-1] "raced through".
 *
 * No DOM / charting-library dependency — rendering is handled by the caller
 * (see chart_dashboard.html: drawFVG()). Mirrors volume_profile.js /
 * elliott_wave.js's separation of concerns.
 *
 * Public API (window.FVG):
 *   FVG.compute(bars, opts) -> zone[]
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 * Zone shape: {
 *   bullish: bool,
 *   startIdx, startTime,        // candle[i-2] — the gap's left edge
 *   top, bottom,                 // price boundaries of the gap
 *   filledIdx, filledTime,       // index/time the gap was first touched, or null if still open
 *   sizePct,                     // gap size as % of price, for minSizePct filtering
 * }
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    minSizePct: 0,        // ignore gaps smaller than this % of price (0 = keep all)
    maxZones:   60,        // cap how many zones compute() returns (most recent first)
  };

  // ── Step 1: scan every 3-candle window for an unfilled-on-arrival gap ────────
  function findZones(bars, opts) {
    const zones = [];
    const n = bars.length;
    for (let i = 2; i < n; i++) {
      const left = bars[i - 2], mid = bars[i - 1], right = bars[i];

      // Bullish FVG: right candle's low sits above left candle's high.
      if (right.low > left.high) {
        const top = right.low, bottom = left.high;
        const sizePct = ((top - bottom) / bottom) * 100;
        if (sizePct >= opts.minSizePct) {
          zones.push({
            bullish: true,
            startIdx: i - 2, startTime: left.time,
            top, bottom, sizePct,
            filledIdx: null, filledTime: null,
          });
        }
      }
      // Bearish FVG: right candle's high sits below left candle's low.
      else if (right.high < left.low) {
        const top = left.low, bottom = right.high;
        const sizePct = ((top - bottom) / bottom) * 100;
        if (sizePct >= opts.minSizePct) {
          zones.push({
            bullish: false,
            startIdx: i - 2, startTime: left.time,
            top, bottom, sizePct,
            filledIdx: null, filledTime: null,
          });
        }
      }
    }
    return zones;
  }

  // ── Step 2: mark each zone filled the first time price trades back into it ──
  // A zone is "filled" the first bar (after it forms) whose range overlaps the
  // gap's [bottom, top] band. Bullish gaps act as support (filled from above by
  // a low dipping into the band); bearish gaps act as resistance (filled from
  // below by a high poking into the band) — but either direction of overlap
  // counts as a fill, matching how traders read "the gap got tagged."
  function markFills(bars, zones) {
    zones.forEach(z => {
      for (let i = z.startIdx + 3; i < bars.length; i++) {
        const b = bars[i];
        if (b.low <= z.top && b.high >= z.bottom) {
          z.filledIdx = i;
          z.filledTime = b.time;
          break;
        }
      }
    });
  }

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    if (!bars || bars.length < 3) return [];
    const zones = findZones(bars, opts);
    markFills(bars, zones);
    return zones.slice(-opts.maxZones);
  }

  // ── Actionable buy/sell signals (FF-2 + FF-5) ───────────────────────────────
  // compute() above is a pure *visualizer* — every raw 3-candle gap, no verdict.
  // signals() is the *entry engine*: a faithful JS port of the Python
  // detect_fvg_pullback() state machine (tools/scanner_templates.py, from
  // sources/BOS-FVG-Pullback-Signals-Pine.md), plus the price+volume "FPV"
  // read (concepts/FPV-Flow-Price-Volume-Ownership.md, two-component chart
  // variant) and Zeiierman's in-gap bull/bear power
  // (sources/FVG-Zeiierman-MTF-Pine.md). It answers "should I act, and how
  // strong is it" rather than "where are the gaps".

  const SIGNAL_OPTS = {
    atrMult: 0.5,   // gap must exceed atrMult × ATR(atrLen) to qualify (displacement)
    atrLen:  14,
    volLen:  20,    // trailing window for the volume-flow average
    recent:  10,    // a signal ≤ recent bars old is "live"; older is historical context
  };

  // Wilder-smoothed ATR, index-aligned with bars (NaN until seeded).
  function atrSeries(bars, len) {
    const n = bars.length;
    const tr = new Array(n);
    for (let i = 0; i < n; i++) {
      if (i === 0) { tr[i] = bars[0].high - bars[0].low; continue; }
      const h = bars[i].high, l = bars[i].low, pc = bars[i - 1].close;
      tr[i] = Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc));
    }
    const atr = new Array(n).fill(NaN);
    if (n < len) return atr;
    let sum = 0;
    for (let i = 0; i < len; i++) sum += tr[i];
    atr[len - 1] = sum / len;
    for (let i = len; i < n; i++) atr[i] = (atr[i - 1] * (len - 1) + tr[i]) / len;
    return atr;
  }

  // Price+Volume read for the bar that fired a signal. Price direction is given
  // by the signal side (a buy is a bullish move); volume is graded against its
  // trailing average; bull/bear "power" is the close's position within the bar's
  // range (Zeiierman: buy effort = low→close, sell effort = high→close).
  function fpvRead(bars, i, bullish, volLen) {
    const b = bars[i];
    let vsum = 0, cnt = 0;
    for (let j = Math.max(0, i - volLen); j < i; j++) {
      const v = bars[j].volume;
      if (v != null && isFinite(v)) { vsum += v; cnt++; }
    }
    const avg = cnt ? vsum / cnt : 0;
    const vol = (b.volume != null && isFinite(b.volume)) ? b.volume : null;
    const hasVolume = avg > 0 && vol != null;
    const volRatio = hasVolume ? vol / avg : null;
    const volUp = volRatio != null ? volRatio >= 1 : null;

    const range = (b.high - b.low) || 1e-9;
    const buyEff = (b.close - b.low) / range;    // 0..1
    const sellEff = (b.high - b.close) / range;  // 0..1
    const tot = (buyEff + sellEff) || 1;
    const buyPct = Math.round((buyEff / tot) * 100);
    const sellPct = 100 - buyPct;

    // Strength = the framework's Price↑+Vol↑ = strong / Price↑+Vol↓ = weak rule.
    // With no volume data (e.g. some indices) we can't grade — say so.
    let strength;
    if (!hasVolume) strength = 'UNKNOWN';
    else strength = volUp ? 'STRONG' : 'WEAK';

    // Recommendation: the actionable verdict the chart surfaces.
    const side = bullish ? 'BUY' : 'SELL';
    const rec = strength === 'STRONG' ? `STRONG ${side}`
              : strength === 'WEAK'   ? `WEAK ${side}`
              :                         side;
    return { bullish, volRatio, volUp, buyPct, sellPct, strength, hasVolume, rec };
  }

  function signals(bars, opts) {
    opts = Object.assign({}, SIGNAL_OPTS, opts || {});
    if (!bars || bars.length < opts.atrLen + 10) return null;
    const atr = atrSeries(bars, opts.atrLen);
    const n = bars.length;

    let bullTop = null, bullBot = null, bearTop = null, bearBot = null;
    let lastBuy = null, lastSell = null;

    for (let i = 2; i < n; i++) {
      const a = atr[i];
      if (!isFinite(a) || a <= 0) continue;
      const b = bars[i], b1 = bars[i - 1], b2 = bars[i - 2];

      // (1) A qualifying gap (directional middle candle + displacement > ATR×mult)
      //     replaces the active zone on its side.
      if (b.low > b2.high && b1.close > b1.open && (b.low - b2.high) > a * opts.atrMult) {
        bullTop = b.low; bullBot = b2.high;
      }
      if (b.high < b2.low && b1.close < b1.open && (b2.low - b.high) > a * opts.atrMult) {
        bearTop = b2.low; bearBot = b.high;
      }

      // (2) A close fully through the zone invalidates it (the FBG-failure edge).
      if (bullTop !== null && b.close < bullBot) { bullTop = bullBot = null; }
      if (bearTop !== null && b.close > bearTop) { bearTop = bearBot = null; }

      // (3) Rejection entry: opened beyond the zone, dipped in, closed back out
      //     with a dominant wick. One signal per zone (the zone is consumed).
      if (bullTop !== null) {
        const touch = b.low <= bullTop && b.low >= bullBot;
        const reject = b.close > bullTop && (b.close - b.low) > (b.high - b.close);
        if (touch && reject && b.open > bullTop) {
          lastBuy = { idx: i, zone: { top: bullTop, bottom: bullBot } };
          bullTop = bullBot = null;
        }
      }
      if (bearTop !== null) {
        const touch = b.high >= bearBot && b.high <= bearTop;
        const reject = b.close < bearBot && (b.high - b.close) > (b.close - b.low);
        if (touch && reject && b.open < bearBot) {
          lastSell = { idx: i, zone: { top: bearTop, bottom: bearBot } };
          bearTop = bearBot = null;
        }
      }
    }

    const pack = (sig, bullish) => {
      if (!sig) return null;
      const b = bars[sig.idx];
      return {
        idx: sig.idx,
        time: b.time,
        price: b.close,
        low: b.low, high: b.high,
        zone: sig.zone,
        barsAgo: (n - 1) - sig.idx,
        live: ((n - 1) - sig.idx) <= opts.recent,
        fpv: fpvRead(bars, sig.idx, bullish, opts.volLen),
      };
    };

    const buy = pack(lastBuy, true);
    const sell = pack(lastSell, false);
    if (!buy && !sell && bullTop === null && bearTop === null) return null;

    return {
      buy, sell,
      activeBull: bullTop !== null ? { top: bullTop, bottom: bullBot } : null,
      activeBear: bearTop !== null ? { top: bearTop, bottom: bearBot } : null,
      recent: opts.recent,
    };
  }

  global.FVG = {
    VERSION: '1.1.0',
    compute,
    signals,
  };
})(typeof window !== 'undefined' ? window : globalThis);
