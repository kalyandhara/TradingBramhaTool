/*!
 * vwap_mean_reversion.js — two-sided VWAP mean-reversion BUY/SELL signals.
 *
 * The rule from the "VWAP Mean Reversion + Volume" playbook: price deviates far
 * from VWAP on EXTREME volume, rejects, and reverts to VWAP on RISING volume.
 * Long below VWAP, short above it, exit at VWAP.
 *
 * ── Why this is not `evmacd`, and not `scan_vwap_reclaim` ───────────────────
 * The chart already carries two VWAP-derived things and neither is this rule:
 *
 *   • `evmacd` (evwma_vwap_macd.js) fires when price pulls AWAY from the volume
 *     anchor — a momentum read, the exact opposite trigger. Measured 2026-08-29:
 *     no edge at any horizon, stop-and-reverse median -29% vs buy&hold +827%.
 *   • `scan_vwap_reclaim` (scanner #40, B-40) is LONG-ONLY, WITH-TREND, and uses
 *     volume only as a participation floor.
 *
 * What is new here is the two-sided band excursion and, more importantly, the
 * DOUBLE volume role: extreme volume marking the deviation, then rising volume
 * confirming the turn. A reversion on falling volume is the failure case this
 * rule is supposed to skip, and neither existing tool can express it.
 *
 * ── The timeframe problem, stated up front ──────────────────────────────────
 * This is natively an INTRADAY strategy: "price deviates from session VWAP and
 * reverts" needs a VWAP that resets per session and many bars inside it. On
 * daily bars a session VWAP does not exist — chart_dashboard.vwapSeries measured
 * it equal to (H+L+C)/3 on 24 of 24 daily bars, i.e. a typical-price line
 * wearing a VWAP label. So:
 *
 *   intraday tf  -> true SESSION VWAP, reset per calendar day (the real rule)
 *   1d / 1w / 1M -> ROLLING n-bar VWAP (`source: 'rolling'`)
 *
 * The rolling variant is a DIFFERENT CLAIM, not the same rule on slower bars,
 * and `source` is returned so no caller can conflate them. `scan_vwap_reclaim`
 * hit this same wall from the other side: anchored VWAP sits far below price in
 * any healthy trend, so its not-extended gate always rejected and it never fired
 * (0/8). A mean must be something price actually oscillates around.
 *
 * ── Causality ───────────────────────────────────────────────────────────────
 * Every term is backward-looking: rolling VWAP and its dispersion use bars
 * <= i, the volume average is a trailing SMA, and an excursion is only resolved
 * by a LATER bar closing back inside the band. A signal at bar t is computable
 * at t's close and never revised, so the backtest can walk it in one pass.
 * The one deliberate asymmetry: the deviation extreme is chosen from bars
 * already seen when the confirmation fires, never from bars after it.
 *
 * No DOM / charting-library dependency — rendering is the caller's job, mirroring
 * evwma_vwap_macd.js and adx_di.js.
 *
 * Public API (window.VWMR):
 *   VWMR.compute(bars, opts) -> {
 *     vwap, upper, lower,        // {time,value}[] the mean and its bands
 *     z,                         // {time,value}[] deviation in sigmas
 *     buy, sell,                 // events (see below)
 *     signals,                   // merged chronological, dir +-1
 *     state,                     // open excursion, or null
 *     opts, source, insufficient // echo + 'session'|'rolling' + why-empty
 *   }
 *
 * Each event: {time, index, dir, price, vwap, z, targetPct, stop, target,
 *              devIndex, devZ, devVolMult, confVolMult, bars}
 *   devVolMult  — volume at the deviation extreme, x trailing average
 *   confVolMult — volume on the confirmation bar, x trailing average
 *   targetPct   — distance to VWAP in %, the trade's whole thesis
 *
 * Bar shape: {time, open, high, low, close, volume}
 *
 * MEASURED 2026-09-06 (B-40m) — NULL, AND NEGATIVE AFTER COSTS. 275 signals over
 * 50 symbols: +0.19% forward edge at 5d and 10d (p 0.51 / 0.57), and the rule
 * traded as written returns +0.04R gross, −0.19R at Indian delivery costs, with
 * target hit 50 times against stop 53. The +1.54% at 60d (p=0.053) is a trap —
 * it sits far outside the holding period and measures drift, not this rule.
 *
 * So these arrows are drawn as CONTEXT, not calls. The bands remain a real read
 * ("how stretched is this, for this symbol, lately"); the entries do not beat a
 * coin flip. Third VWAP-derived rule to measure null on this desk. The playbook's
 * actual INTRADAY claim is untested — that needs a session-VWAP store this repo
 * does not have, which is a data gap and not a parameter to tune.
 */
(function (global) {
  'use strict';

  var DEFAULTS = {
    tf: '1d',
    n: 20,            // rolling-VWAP / dispersion window (daily+ only)
    bandK: 2.0,       // sigmas from VWAP that count as "deviated"
    devVolMult: 1.5,  // volume at the extreme, x trailing average ("extreme")
    confVolMult: 1.2, // volume on the reversal bar, x trailing average ("rising")
    volAvgLen: 20,
    maxExcursion: 15, // bars an excursion may stay outside before it is abandoned
    minTargetPct: 0.5 // skip signals whose whole move back to VWAP is noise
  };

  // Timeframes where a session holds several bars, so a session VWAP means
  // something. Mirrors chart_dashboard.INTRADAY_TFS deliberately — if that set
  // changes, this one must change with it.
  var INTRADAY = {'1m': 1, '5m': 1, '15m': 1, '30m': 1, '1h': 1, '4h': 1, '6h': 1};

  function typical(b) { return (b.high + b.low + b.close) / 3; }

  function sessionVwap(bars) {
    var out = new Array(bars.length).fill(NaN);
    var cumPV = 0, cumVol = 0, curDay = null;
    for (var i = 0; i < bars.length; i++) {
      var b = bars[i];
      var day = new Date(b.time * 1000).toISOString().slice(0, 10);
      if (day !== curDay) { curDay = day; cumPV = 0; cumVol = 0; }
      cumPV += typical(b) * (b.volume || 0);
      cumVol += (b.volume || 0);
      // No fallback to close. A VWAP drawn as the price line on a feed missing
      // volume is the most convincing way possible to be wrong.
      if (cumVol > 0) out[i] = cumPV / cumVol;
    }
    return out;
  }

  function rollingVwap(bars, n) {
    var out = new Array(bars.length).fill(NaN);
    var pv = 0, vol = 0;
    for (var i = 0; i < bars.length; i++) {
      pv += typical(bars[i]) * (bars[i].volume || 0);
      vol += (bars[i].volume || 0);
      if (i >= n) {
        pv -= typical(bars[i - n]) * (bars[i - n].volume || 0);
        vol -= (bars[i - n].volume || 0);
      }
      if (i >= n - 1 && vol > 0) out[i] = pv / vol;
    }
    return out;
  }

  // Dispersion of price around the mean, NOT stdev of price. The band has to
  // answer "how far from VWAP is far, for this symbol, lately" — using stdev of
  // close would measure the trend instead and the bands would never be touched
  // in exactly the trending conditions where a reversion trade is most dangerous.
  function dispersion(bars, vwapArr, n) {
    var out = new Array(bars.length).fill(NaN);
    for (var i = 0; i < bars.length; i++) {
      if (i < n - 1 || !isFinite(vwapArr[i])) continue;
      var s = 0, k = 0;
      for (var j = i - n + 1; j <= i; j++) {
        if (!isFinite(vwapArr[j])) continue;
        var d = bars[j].close - vwapArr[j];
        s += d * d; k++;
      }
      if (k >= 2) out[i] = Math.sqrt(s / k);
    }
    return out;
  }

  // Mean volume over the `len` bars BEFORE i, excluding i itself: comparing a
  // bar's volume to an average that already contains it dilutes exactly the
  // spike being tested.
  //
  // The first cut subtracted the current bar from a window that included it and
  // still divided by `len` — 19 bars of volume over a divisor of 20. That made
  // every multiplier ~5% too high and fired one signal on TATASTEEL that the
  // Python scanner correctly rejected (devVol 3.21x vs a true 3.05x). Caught by
  // cross-checking the two implementations against each other rather than by
  // either one looking wrong on its own, which is the whole reason both exist.
  function trailingVolAvg(bars, len) {
    var out = new Array(bars.length).fill(NaN);
    var sum = 0;
    for (var i = 0; i < bars.length; i++) {
      if (i > 0) sum += (bars[i - 1].volume || 0);
      if (i > len) sum -= (bars[i - len - 1].volume || 0);
      if (i >= len) out[i] = sum / len;
    }
    return out;
  }

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULTS, opts || {});
    var empty = {vwap: [], upper: [], lower: [], z: [], buy: [], sell: [],
                 signals: [], state: null, opts: opts, source: null,
                 insufficient: null};

    if (!Array.isArray(bars) || bars.length < opts.n + opts.volAvgLen + 2) {
      empty.insufficient = 'need >= ' + (opts.n + opts.volAvgLen + 2) + ' bars';
      return empty;
    }
    var volSum = 0;
    for (var v = 0; v < bars.length; v++) volSum += (bars[v].volume || 0);
    if (!(volSum > 0)) {
      empty.insufficient = 'no volume on this feed — VWAP is undefined';
      return empty;
    }

    var intraday = !!INTRADAY[opts.tf];
    var source = intraday ? 'session' : 'rolling';
    var vwapArr = intraday ? sessionVwap(bars) : rollingVwap(bars, opts.n);
    var sigma = dispersion(bars, vwapArr, opts.n);
    var volAvg = trailingVolAvg(bars, opts.volAvgLen);

    var vwap = [], upper = [], lower = [], z = [];
    for (var i = 0; i < bars.length; i++) {
      if (!isFinite(vwapArr[i])) continue;
      var t = bars[i].time;
      vwap.push({time: t, value: +vwapArr[i].toFixed(4)});
      if (!isFinite(sigma[i]) || sigma[i] <= 0) continue;
      upper.push({time: t, value: +(vwapArr[i] + opts.bandK * sigma[i]).toFixed(4)});
      lower.push({time: t, value: +(vwapArr[i] - opts.bandK * sigma[i]).toFixed(4)});
      z.push({time: t, value: +((bars[i].close - vwapArr[i]) / sigma[i]).toFixed(3)});
    }

    // ── Excursion walk ───────────────────────────────────────────────────────
    // An excursion opens when a bar CLOSES beyond the band and closes when a
    // later bar closes back inside it. The extreme is the furthest bar reached
    // while outside; the confirmation is the bar that comes back in.
    var buy = [], sell = [], open = null;

    for (var b = 1; b < bars.length; b++) {
      if (!isFinite(vwapArr[b]) || !isFinite(sigma[b]) || sigma[b] <= 0) continue;
      var bar = bars[b];
      var zb = (bar.close - vwapArr[b]) / sigma[b];
      var outside = Math.abs(zb) >= opts.bandK;
      var dir = zb < 0 ? 1 : -1;   // below VWAP -> long side

      if (open && open.dir !== dir && outside) open = null;  // flipped sides; start over

      if (outside) {
        if (!open) {
          open = {dir: dir, startIdx: b, extIdx: b, extZ: zb,
                  extPrice: dir === 1 ? bar.low : bar.high};
        } else {
          // Track the furthest point of the SAME excursion.
          if (Math.abs(zb) > Math.abs(open.extZ)) { open.extIdx = b; open.extZ = zb; }
          if (dir === 1) open.extPrice = Math.min(open.extPrice, bar.low);
          else           open.extPrice = Math.max(open.extPrice, bar.high);
        }
        continue;
      }

      if (!open) continue;
      if (b - open.startIdx > opts.maxExcursion) { open = null; continue; }

      // Back inside the band — this is the reversal candle. Everything below is
      // a filter on THIS bar plus the excursion already behind it.
      var d = open.dir;
      var ext = bars[open.extIdx];
      var devMult = isFinite(volAvg[open.extIdx]) && volAvg[open.extIdx] > 0
        ? (ext.volume || 0) / volAvg[open.extIdx] : 0;
      var confMult = isFinite(volAvg[b]) && volAvg[b] > 0
        ? (bar.volume || 0) / volAvg[b] : 0;

      var candleAgrees = d === 1 ? (bar.close > bar.open && bar.close > bars[b - 1].close)
                                 : (bar.close < bar.open && bar.close < bars[b - 1].close);
      var target = vwapArr[b];
      var targetPct = bar.close > 0 ? 100 * (target - bar.close) / bar.close : 0;

      var ok = candleAgrees
        && devMult >= opts.devVolMult      // extreme volume ON the deviation
        && confMult >= opts.confVolMult    // rising volume ON the reversal
        && Math.abs(targetPct) >= opts.minTargetPct;

      if (ok) {
        var ev = {
          time: bar.time, index: b, dir: d, price: bar.close,
          vwap: +target.toFixed(4), z: +zb.toFixed(3),
          target: +target.toFixed(4), targetPct: +targetPct.toFixed(2),
          // Stop sits beyond the excursion extreme — the level the market
          // already rejected. If that breaks, the deviation was a trend.
          stop: +(d === 1 ? open.extPrice : open.extPrice).toFixed(4),
          devIndex: open.extIdx, devZ: +open.extZ.toFixed(3),
          devVolMult: +devMult.toFixed(2), confVolMult: +confMult.toFixed(2),
          bars: b - open.startIdx + 1
        };
        (d === 1 ? buy : sell).push(ev);
      }
      open = null;
    }

    var signals = buy.concat(sell).sort(function (a, c) { return a.time - c.time; });

    return {
      vwap: vwap, upper: upper, lower: lower, z: z,
      buy: buy, sell: sell, signals: signals,
      // An excursion still open at the last bar is a WATCH, not a signal: the
      // confirmation bar has not happened. Reporting it as a trigger would be
      // the look-ahead this module is built to avoid.
      state: open ? {dir: open.dir, since: bars[open.startIdx].time,
                     bars: bars.length - open.startIdx,
                     extZ: +open.extZ.toFixed(3), pending: true} : null,
      opts: opts, source: source, insufficient: null
    };
  }

  global.VWMR = {VERSION: '1.0.0', compute: compute, DEFAULTS: DEFAULTS};
})(typeof window !== 'undefined' ? window : globalThis);
