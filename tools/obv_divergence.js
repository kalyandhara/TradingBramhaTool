/*!
 * obv_divergence.js — the four divergence types, read off OBV instead of RSI.
 *
 * B-61. Requested from LuxAlgo's OBV-divergence page; the four-variant table
 * below matches theirs exactly, so this is that concept made executable rather
 * than a new claim.
 *
 *   Regular (reversal):
 *     Bullish  price Lower Low   + OBV Higher Low     selling pressure not expanding
 *     Bearish  price Higher High + OBV Lower High     the advance lacks volume support
 *   Hidden (continuation):
 *     Bullish  price Higher Low  + OBV Lower Low
 *     Bearish  price Lower High  + OBV Higher High
 *
 * ── This does NOT contain a divergence walk ─────────────────────────────────
 * It computes OBV and hands it to `RSIDIV.compute` as the injected series. That
 * module already walks confirmed zigzag pivots and applies exactly this table,
 * and it already takes the oscillator from its caller precisely so the line you
 * SEE and the values a divergence is measured from cannot drift apart.
 *
 * A second copy of the walk here would be the same logic maintained twice —
 * which is the shape of the bug `test_renko_parity.py` exists to catch
 * elsewhere in this repo. Load AFTER elliott_wave.js and rsi_divergence.js.
 *
 * ── OBV is not RSI, and the difference changes how to read the output ───────
 * RSI is bounded 0-100 and mean-reverting. **OBV is an unbounded running total,
 * so it trends with the market.** In a sustained advance nearly every OBV swing
 * low is a higher low, which makes "price lower low + OBV higher low" cheaper to
 * satisfy than the RSI equivalent. Expect MORE divergences here than from the
 * RSI module on the same bars, and do not read the extra ones as extra evidence.
 *
 * ── The artifact this module measures rather than merely warning about ──────
 * OBV books a bar's ENTIRE volume by the sign of its close-to-close change, so a
 * single enormous print — a news candle, an index rebalance, a block deal — can
 * bend the line into a divergence no genuine flow produced. LuxAlgo names this
 * as the main false-signal source and suggests inspecting the bars by hand.
 *
 * This desk can do better than "inspect by hand": every divergence carries
 * `volConcentration`, the largest single bar's share of total volume across the
 * divergence's own window. At 0.5 one session IS the divergence. The UI can
 * flag it, and `volume_anomaly` already attributes such spikes to a cause.
 *
 * Nothing here is a signal. LuxAlgo's own advice is to require price
 * confirmation — a reversal bar or a swing break — before acting, and this desk
 * has measured no forward edge for it. Drawn as context.
 *
 * Public API (window.OBVDIV):
 *   OBVDIV.compute(bars, opts) -> {divergences, obv, pivots}
 *   OBVDIV.obvSeries(bars)     -> [{time, value}]
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  /**
   * On-Balance Volume — a running total, causal by construction.
   *
   * Adds the whole bar's volume when the close is up on the prior close,
   * subtracts it when down, leaves it unchanged when flat. Identical to
   * `obvSeries` in chart_dashboard.html; kept here so the module works when the
   * caller has no series of its own, and the caller's wins when it does.
   */
  function obvSeries(bars) {
    const out = [];
    let obv = 0;
    for (let i = 0; i < bars.length; i++) {
      if (i > 0) {
        const c = bars[i].close, p = bars[i - 1].close;
        if (c > p) obv += (bars[i].volume || 0);
        else if (c < p) obv -= (bars[i].volume || 0);
      }
      out.push({time: bars[i].time, value: obv});
    }
    return out;
  }

  /**
   * The largest single bar's share of total volume between two bar indices.
   *
   * The number that says whether a divergence is a flow story or one print. A
   * window of N equal bars scores 1/N; a window where one session carries half
   * the volume scores 0.5. Returned per divergence rather than thresholded here,
   * because "how concentrated is too concentrated" is a judgement the reader
   * should make against a visible number.
   */
  function volConcentration(bars, i0, i1) {
    const lo = Math.max(0, Math.min(i0, i1));
    const hi = Math.min(bars.length - 1, Math.max(i0, i1));
    let total = 0, max = 0;
    for (let i = lo; i <= hi; i++) {
      const v = Math.abs(bars[i].volume || 0);
      total += v;
      if (v > max) max = v;
    }
    return total > 0 ? +(max / total).toFixed(3) : null;
  }

  /**
   * Divergences between price and OBV.
   *
   * `opts` passes straight through to `RSIDIV.compute` (same zigzag settings,
   * same `includeHidden`), so the two divergence panes stay comparable.
   */
  function compute(bars, opts) {
    opts = opts || {};
    const empty = {divergences: [], obv: [], pivots: []};
    if (!bars || bars.length < 20) return empty;
    if (!global.RSIDIV || typeof global.RSIDIV.compute !== 'function') {
      // Fail loudly-but-safely: an empty overlay is recoverable, a silently
      // wrong one is not. Load order is stated in the header.
      return empty;
    }

    const obv = (opts.obv && opts.obv.length) ? opts.obv : obvSeries(bars);
    if (!obv.length) return empty;

    // The oscillator goes in through RSIDIV's injection point. Its output field
    // is named `rsi` because that is its own vocabulary; it is OBV here, and it
    // is renamed on the way out so no caller downstream is misled.
    const res = global.RSIDIV.compute(bars, Object.assign({}, opts, {
      rsi: obv,
      rsiPeriod: 1,          // no warm-up to reserve: OBV is defined from bar 0
    }));

    const divergences = (res.divergences || []).map(d => {
      const out = Object.assign({}, d, {
        from: {idx: d.from.idx, time: d.from.time, price: d.from.price, obv: d.from.rsi},
        to: {idx: d.to.idx, time: d.to.time, price: d.to.price, obv: d.to.rsi},
        volConcentration: volConcentration(bars, d.from.idx, d.to.idx),
      });
      return out;
    });

    return {divergences, obv, pivots: res.pivots || []};
  }

  global.OBVDIV = {
    VERSION: '1.0.0',
    compute,
    obvSeries,
    volConcentration,
    LABEL: (global.RSIDIV && global.RSIDIV.LABEL) || null,
  };
})(typeof window !== 'undefined' ? window : globalThis);
