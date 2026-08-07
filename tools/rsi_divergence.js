/*!
 * rsi_divergence.js — the four RSI divergence types, read off confirmed swing
 * pivots.
 *
 * Regular divergence (trend reversal):
 *   Bullish  price Lower Low   + RSI Higher Low
 *   Bearish  price Higher High + RSI Lower High
 * Hidden divergence (trend continuation):
 *   Bullish  price Higher Low  + RSI Lower Low
 *   Bearish  price Lower High  + RSI Higher High
 *
 * Same four-variant table the wiki's concepts/RSI.md has carried since
 * 2026-06-22 — this module is that page made executable, not a new claim.
 *
 * Two things it deliberately does NOT do
 * --------------------------------------
 * 1. It does not invent its own pivots. Swings come from EW.computeZigzag
 *    (elliott_wave.js), the same ATR-adaptive detector Elliott Wave and
 *    Fibonacci already read, so every structure tool on the chart agrees about
 *    where the swings are. Load order matters: after elliott_wave.js, exactly
 *    as fibonacci.js does.
 *
 * 2. It does not compute its own RSI when the caller has one. The dashboard
 *    passes its own `rsiSeries(bars,14)` in, so the line you SEE in the RSI
 *    pane and the values the divergence is measured from cannot drift apart.
 *    The internal fallback is a faithful copy of that Wilder implementation,
 *    including its both-zero -> 50 branch (the fix for the phantom-plunge bug
 *    on near-monotonic series, LIQUIDCASE.NS 2026-07-03).
 *
 * Repainting, stated rather than hidden
 * -------------------------------------
 * A zigzag's LAST pivot is provisional: no reversal has confirmed it yet, so it
 * can move or vanish as bars arrive, taking any divergence anchored to it with
 * it. That is the standard failure of divergence indicators on retail
 * platforms, where the line silently disappears and the screenshot no longer
 * matches the chart. Every divergence here carries `provisional`, and the
 * renderer draws those differently. A tool that repaints is fine; one that
 * repaints quietly is not.
 *
 * Public API (window.RSIDIV):
 *   RSIDIV.compute(bars, opts) -> {divergences, rsi, pivots}
 *
 * Divergence shape:
 *   {kind:'regular'|'hidden', dir:'bull'|'bear', label,
 *    from:{idx,time,price,rsi}, to:{idx,time,price,rsi},
 *    priceDeltaPct, rsiDelta, bars, provisional}
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    rsiPeriod: 14,
    //: A COARSER zigzag than the Elliott overlay's {atrMult:1.2, minPct:0.5}.
    //: Deliberate, and measured: at EW's setting a 300-bar daily chart yields
    //: ~132 pivots — a swing every other bar — and the divergences that fall
    //: out have a median span of 8 bars and ±0.4% price legs. Divergence
    //: between two 2-bar wiggles is not a momentum story, it is noise with a
    //: label on it. At 2.0/1.5 the same charts give ~43 pivots and a 27-bar
    //: median span, which is the multi-week scale the concept actually means.
    //: Elliott solves its own clutter downstream by scoring structures; this
    //: has no such filter, so it has to be solved at the pivot level.
    zigzag: {atrMult: 2.0, minPct: 1.5},
    //: Minimum separation between the two swings. Adjacent pivots a couple of
    //: bars apart are noise, not a momentum story.
    minBars: 5,
    //: Beyond this the two swings are not really the same move any more.
    maxBars: 120,
    //: A divergence needs BOTH legs to actually diverge. Without a floor, a
    //: 0.02% price difference and a 0.1-point RSI difference qualify, and the
    //: chart fills with lines that mean nothing.
    minRsiDelta: 2.0,
    minPricePct: 0.4,
    //: Newest-first cap. Every divergence over 300 bars is unreadable; the
    //: renderer wants the ones still in play.
    maxResults: 6,
    //: Hidden divergence is a continuation signal and only means anything
    //: inside an existing trend, so it is reported but flagged when the
    //: trend context is absent (see `trendOk`).
    includeHidden: true,
  };

  // ── Wilder RSI — mirrors chart_dashboard.html's rsiSeries exactly ────────────
  function rsiSeries(bars, period) {
    if (!bars || bars.length < period + 1) return [];
    const out = [];
    const alpha = 1 / period;
    let avgGain = 0, avgLoss = 0;
    for (let i = 1; i < bars.length; i++) {
      const diff = bars[i].close - bars[i - 1].close;
      avgGain = alpha * (diff > 0 ?  diff : 0) + (1 - alpha) * avgGain;
      avgLoss = alpha * (diff < 0 ? -diff : 0) + (1 - alpha) * avgLoss;
      if (i < period) continue;
      let value;
      if (avgGain === 0 && avgLoss === 0)      value = 50;
      else if (avgLoss === 0)                  value = 100;
      else                                     value = 100 - 100 / (1 + avgGain / avgLoss);
      out.push({time: bars[i].time, value});
    }
    return out;
  }

  const LABEL = {
    'regular:bull': 'Regular Bullish',
    'regular:bear': 'Regular Bearish',
    'hidden:bull':  'Hidden Bullish',
    'hidden:bear':  'Hidden Bearish',
  };

  function compute(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const empty = {divergences: [], rsi: [], pivots: []};
    if (!bars || bars.length < opts.rsiPeriod + 10) return empty;

    // RSI: the caller's series wins, so the pane and the lines cannot disagree.
    const rsi = (opts.rsi && opts.rsi.length) ? opts.rsi
                                              : rsiSeries(bars, opts.rsiPeriod);
    if (!rsi.length) return empty;

    // Join by TIME, never by index: rsiSeries drops warm-up bars, so index i in
    // the RSI array is not bar i. Getting this wrong shifts every reading by
    // `period` bars and still looks plausible — the same class of bug the OBV
    // sub-pane hit.
    const rsiAt = new Map(rsi.map(p => [p.time, p.value]));

    const pivots = (opts.pivots && opts.pivots.length)
      ? opts.pivots
      : (global.EW && typeof global.EW.computeZigzag === 'function'
          ? global.EW.computeZigzag(bars, Object.assign({}, opts.zigzag))
          : []);
    if (pivots.length < 3) return {divergences: [], rsi, pivots};

    // A pivot is only usable if RSI exists at its bar (warm-up) — drop rather
    // than substitute, because a fabricated RSI reading is a fabricated signal.
    const usable = pivots
      .map(p => ({...p, rsi: rsiAt.get(p.time)}))
      .filter(p => p.rsi !== undefined);

    const found = [];
    for (let i = 0; i < usable.length; i++) {
      const a = usable[i];
      // Same-type pivots are two apart in an alternating zigzag. Also compare
      // against the next-but-two, so a divergence spanning a deeper structure
      // is not missed when one intervening swing is small.
      for (const step of [2, 4]) {
        const b = usable[i + step];
        if (!b || b.type !== a.type) continue;

        const gap = b.idx - a.idx;
        if (gap < opts.minBars || gap > opts.maxBars) continue;

        const rsiDelta = b.rsi - a.rsi;
        const pricePct = (b.price - a.price) / Math.abs(a.price) * 100;
        if (Math.abs(rsiDelta) < opts.minRsiDelta) continue;
        if (Math.abs(pricePct) < opts.minPricePct) continue;

        let kind = null, dir = null;
        if (a.type === 'low') {
          // Price direction vs RSI direction across two swing LOWS.
          if (pricePct < 0 && rsiDelta > 0)      { kind = 'regular'; dir = 'bull'; }
          else if (pricePct > 0 && rsiDelta < 0) { kind = 'hidden';  dir = 'bull'; }
        } else {
          // ...and across two swing HIGHS.
          if (pricePct > 0 && rsiDelta < 0)      { kind = 'regular'; dir = 'bear'; }
          else if (pricePct < 0 && rsiDelta > 0) { kind = 'hidden';  dir = 'bear'; }
        }
        if (!kind) continue;
        if (kind === 'hidden' && !opts.includeHidden) continue;

        found.push({
          kind, dir,
          label: LABEL[`${kind}:${dir}`],
          from: {idx: a.idx, time: a.time, price: a.price, rsi: a.rsi},
          to:   {idx: b.idx, time: b.time, price: b.price, rsi: b.rsi},
          priceDeltaPct: round2(pricePct),
          rsiDelta: round2(rsiDelta),
          bars: gap,
          // Provisional if EITHER endpoint is still unconfirmed by the zigzag.
          provisional: !!(a.provisional || b.provisional),
        });
      }
    }

    // Newest last-pivot first; de-duplicate the step-2/step-4 pairs that landed
    // on the same ending swing with the same reading.
    found.sort((x, y) => y.to.idx - x.to.idx || y.from.idx - x.from.idx);
    const seen = new Set();
    const divergences = [];
    for (const d of found) {
      const key = `${d.kind}:${d.dir}:${d.to.idx}`;
      if (seen.has(key)) continue;
      seen.add(key);
      divergences.push(d);
      if (divergences.length >= opts.maxResults) break;
    }

    return {divergences, rsi, pivots};
  }

  function round2(v) { return Math.round(v * 100) / 100; }

  /**
   * A straight line from `from` to `to` projected onto the FULL bar grid:
   * one entry per bar, interpolated between the endpoints, whitespace outside.
   *
   * Two reasons it is built this way rather than as a bare two-point series.
   * Sub-panes are pinned by LOGICAL range, so a series whose point count
   * differs from the bar grid makes logical index i mean a different bar and
   * draws visibly out of step (the invariant padToBars exists to protect).
   * And Lightweight Charts breaks a line across whitespace, so a two-point
   * series padded with gaps would render as two dots and no line.
   */
  function lineOnGrid(bars, fromIdx, fromVal, toIdx, toVal) {
    const out = new Array(bars.length);
    const span = toIdx - fromIdx;
    for (let i = 0; i < bars.length; i++) {
      if (i < fromIdx || i > toIdx || span <= 0) {
        out[i] = {time: bars[i].time};                    // whitespace
      } else {
        const t = (i - fromIdx) / span;
        out[i] = {time: bars[i].time, value: fromVal + (toVal - fromVal) * t};
      }
    }
    return out;
  }

  global.RSIDIV = {
    VERSION: '1.0.0',
    compute,
    lineOnGrid,
    rsiSeries,
    LABEL,
  };
})(typeof window !== 'undefined' ? window : globalThis);
