/*!
 * volume_profile.js — Volume Profile (POC / Value Area / HVN / LVN) module.
 *
 * Pure computation library: takes an OHLCV bar array and returns the binned
 * volume histogram plus derived structures — Point of Control, Value Area,
 * High-Volume Node pockets, Low-Volume Node pockets — with exact, documented
 * boundary math (see VOLUME_PROFILE_MODULE.md for the full write-up; this
 * file is the reference implementation those boundaries are defined by).
 *
 * No DOM / charting-library dependency — rendering is handled by the caller
 * (see chart_dashboard.html: drawVolumeProfile()). Mirrors elliott_wave.js's
 * separation of concerns so the two modules can be combined for confluence
 * analysis without either depending on the other.
 *
 * Public API (window.VP):
 *   VP.computeProfile(bars, opts)        -> profile
 *   VP.findConfluence(points, profile, tolPct) -> confluence[]
 *
 * Bar shape expected: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  const DEFAULT_OPTS = {
    bins:          30,    // number of price rows spanning [lookbackLow, lookbackHigh]
    lookback:      null,  // null = use every bar passed in; else last N bars only
    valueAreaPct:  0.70,  // fraction of total volume the Value Area must enclose
    hvnMult:       1.5,   // a bin qualifies as an HVN seed if vol >= meanVol * hvnMult
    lvnMult:       0.5,   // a bin qualifies as an LVN seed if vol <= meanVol * lvnMult
    hvnExpandTol:  0.85,  // absorb neighbor bins into an HVN pocket while vol >= seedVol * this
    lvnExpandTol:  1.30,  // absorb neighbor bins into an LVN pocket while vol <= threshold * this
  };

  // ── Step 1: binned histogram with proportional intrabar volume distribution ──
  // Each bar's volume is split across every bin its [low, high] range overlaps,
  // weighted by the fraction of the bar's range inside that bin. This is the
  // standard approximation used when only OHLCV (not tick-level) data is
  // available, and is far more accurate than dumping a whole bar's volume into
  // a single "close price" bin.
  function buildHistogram(bars, opts) {
    const lo = Math.min(...bars.map(b => b.low));
    const hi = Math.max(...bars.map(b => b.high));
    if (!(hi > lo)) return null;

    const nBins = opts.bins;
    const binSize = (hi - lo) / nBins;
    const binEdges = new Array(nBins + 1);
    for (let i = 0; i <= nBins; i++) binEdges[i] = lo + i * binSize;

    const bins = new Array(nBins).fill(0);
    const clampBin = i => Math.max(0, Math.min(nBins - 1, i));

    bars.forEach(b => {
      const range = b.high - b.low;
      const vol = b.volume || 0;
      if (vol === 0) return;

      if (range <= 0) {
        // Flat/doji bar: all volume lands in the single bin containing the price.
        bins[clampBin(Math.floor((b.close - lo) / binSize))] += vol;
        return;
      }

      const i0 = clampBin(Math.floor((b.low - lo) / binSize));
      const i1 = clampBin(Math.floor((b.high - lo) / binSize));
      for (let i = i0; i <= i1; i++) {
        const binLow = binEdges[i], binHigh = binEdges[i + 1];
        const overlap = Math.max(0, Math.min(b.high, binHigh) - Math.max(b.low, binLow));
        if (overlap > 0) bins[i] += vol * (overlap / range);
      }
    });

    return {binEdges, bins, lo, hi, binSize};
  }

  // ── Step 2: Point of Control ──────────────────────────────────────────────────
  // POC = the single bin with the most volume. Its price boundaries are the
  // bin's own [low, high) edges; the quoted "POC price" is the bin midpoint.
  function findPOC(hist) {
    const {bins, binEdges} = hist;
    let pocIdx = 0;
    for (let i = 1; i < bins.length; i++) if (bins[i] > bins[pocIdx]) pocIdx = i;
    return {
      idx: pocIdx,
      price: (binEdges[pocIdx] + binEdges[pocIdx + 1]) / 2,
      low: binEdges[pocIdx], high: binEdges[pocIdx + 1],
      volume: bins[pocIdx],
    };
  }

  // ── Step 3: Value Area (single-bin, greater-of-two-neighbors expansion) ──────
  // Starting from the POC bin, repeatedly add whichever immediately adjacent
  // bin (one step above the current top, one step below the current bottom)
  // holds more volume, until the cumulative volume reaches valueAreaPct of the
  // total. VAH = the upper edge of the topmost included bin; VAL = the lower
  // edge of the bottommost included bin. This is the standard Market/Volume
  // Profile Value Area algorithm.
  function findValueArea(hist, poc, valueAreaPct) {
    const {bins, binEdges} = hist;
    const total = bins.reduce((a, v) => a + v, 0);
    const target = total * valueAreaPct;

    let low = poc.idx, high = poc.idx;
    let cum = bins[poc.idx];

    while (cum < target && (low > 0 || high < bins.length - 1)) {
      const volBelow = low > 0 ? bins[low - 1] : -Infinity;
      const volAbove = high < bins.length - 1 ? bins[high + 1] : -Infinity;
      if (volBelow >= volAbove) { low -= 1; cum += bins[low]; }
      else                       { high += 1; cum += bins[high]; }
    }

    return {
      low: binEdges[low], high: binEdges[high + 1],
      lowIdx: low, highIdx: high,
      volume: cum, pct: total > 0 ? cum / total : 0,
    };
  }

  // ── Step 4/5: HVN / LVN pocket detection ──────────────────────────────────────
  // A "node" starts at a local-extremum bin that clears a significance
  // threshold (relative to the mean bin volume across the whole profile), then
  // *expands* outward while neighboring bins remain within a tolerance of the
  // seed — turning a single peak/trough row into the full contiguous price
  // *pocket* it actually spans. Overlapping pockets from adjacent seeds are
  // then merged. See VOLUME_PROFILE_MODULE.md for the exact threshold values
  // and worked examples.
  function findNodes(hist, {mult, expandTol, mode}) {
    const {bins, binEdges} = hist;
    const n = bins.length;
    const total = bins.reduce((a, v) => a + v, 0);
    const meanVol = total / n;
    const threshold = meanVol * mult;

    const isSeed = i => {
      const v = bins[i];
      const left  = i > 0 ? bins[i - 1] : (mode === 'hvn' ? -Infinity : Infinity);
      const right = i < n - 1 ? bins[i + 1] : (mode === 'hvn' ? -Infinity : Infinity);
      return mode === 'hvn'
        ? (v >= threshold && v >= left && v >= right)
        : (v <= threshold && v <= left && v <= right);
    };

    const pockets = [];
    for (let i = 0; i < n; i++) {
      if (!isSeed(i)) continue;
      let lo = i, hi = i;
      const seedVol = bins[i];
      if (mode === 'hvn') {
        while (lo > 0 && bins[lo - 1] >= seedVol * expandTol) lo--;
        while (hi < n - 1 && bins[hi + 1] >= seedVol * expandTol) hi++;
      } else {
        while (lo > 0 && bins[lo - 1] <= threshold * expandTol) lo--;
        while (hi < n - 1 && bins[hi + 1] <= threshold * expandTol) hi++;
      }
      pockets.push({lowIdx: lo, highIdx: hi, seedIdx: i, seedVolume: seedVol});
    }

    // Merge overlapping/adjacent pockets (sorted by lowIdx).
    pockets.sort((a, b) => a.lowIdx - b.lowIdx);
    const merged = [];
    pockets.forEach(p => {
      const prev = merged[merged.length - 1];
      if (prev && p.lowIdx <= prev.highIdx + 1) {
        prev.highIdx = Math.max(prev.highIdx, p.highIdx);
        prev.seedVolume = Math.max(prev.seedVolume, p.seedVolume);
      } else {
        merged.push({...p});
      }
    });

    return merged.map(p => ({
      low: binEdges[p.lowIdx], high: binEdges[p.highIdx + 1],
      volume: bins.slice(p.lowIdx, p.highIdx + 1).reduce((a, v) => a + v, 0),
      peakVolume: p.seedVolume,
    }));
  }

  // ── Convenience full pipeline ──────────────────────────────────────────────────
  function computeProfile(bars, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const windowBars = opts.lookback ? bars.slice(-opts.lookback) : bars;
    if (!windowBars || windowBars.length < 2) return null;

    const hist = buildHistogram(windowBars, opts);
    if (!hist) return null;

    const poc = findPOC(hist);
    const valueArea = findValueArea(hist, poc, opts.valueAreaPct);
    const hvnZones = findNodes(hist, {mult: opts.hvnMult, expandTol: opts.hvnExpandTol, mode: 'hvn'});
    const lvnZones = findNodes(hist, {mult: opts.lvnMult, expandTol: opts.lvnExpandTol, mode: 'lvn'});

    return {
      binEdges: hist.binEdges, bins: hist.bins,
      lo: hist.lo, hi: hist.hi, binSize: hist.binSize,
      totalVolume: hist.bins.reduce((a, v) => a + v, 0),
      poc, valueArea, hvnZones, lvnZones,
      opts,
    };
  }

  // ── Confluence: do Elliott Wave points line up with Volume Profile zones? ────
  // For each {time, price, label} point, checks proximity (within tolPct of
  // price) to the POC, Value Area edges, and inside-ness to any HVN/LVN
  // pocket. Returns only points that matched at least one zone.
  function findConfluence(points, profile, tolPct) {
    tolPct = tolPct == null ? 0.004 : tolPct; // 0.4% default tolerance
    if (!profile || !points || !points.length) return [];

    const out = [];
    points.forEach(p => {
      const tol = p.price * tolPct;
      const matches = [];

      if (Math.abs(p.price - profile.poc.price) <= tol) {
        matches.push({type: 'POC', detail: profile.poc.price});
      }
      if (Math.abs(p.price - profile.valueArea.high) <= tol) {
        matches.push({type: 'VAH', detail: profile.valueArea.high});
      }
      if (Math.abs(p.price - profile.valueArea.low) <= tol) {
        matches.push({type: 'VAL', detail: profile.valueArea.low});
      }
      profile.hvnZones.forEach(z => {
        if (p.price >= z.low - tol && p.price <= z.high + tol) {
          matches.push({type: 'HVN', detail: [z.low, z.high]});
        }
      });
      profile.lvnZones.forEach(z => {
        if (p.price >= z.low - tol && p.price <= z.high + tol) {
          matches.push({type: 'LVN', detail: [z.low, z.high]});
        }
      });

      if (matches.length) out.push({...p, matches});
    });
    return out;
  }

  // ── Shape classification: D / P / b / I ──────────────────────────────────────
  // Auction-theory silhouettes of the volume-by-price histogram:
  //   D — balanced normal, fat middle           (rotational / value)
  //   P — bulge at the TOP  = buying then balance (long covering / bullish)
  //   b — bulge at the BOTTOM = selling then bal. (short covering / bearish)
  //   I — thin, one-sided, volume spread evenly  (trend / initiative move)
  // Heuristic, not gospel: split the range into thirds by price, find the
  // dominant third + where the POC sits, and how concentrated the peak is.
  function classifyShape(profile) {
    const { bins, poc, lo, hi } = profile;
    const total = bins.reduce((a, v) => a + v, 0);
    if (total <= 0) return { shape: 'I', pocPos: 0.5, domFrac: 0 };
    const n = bins.length, t = Math.max(1, Math.floor(n / 3));
    let botV = 0, midV = 0, topV = 0;
    for (let i = 0; i < n; i++) {
      if (i < t) botV += bins[i];
      else if (i < 2 * t) midV += bins[i];
      else topV += bins[i];
    }
    const dom = Math.max(botV, midV, topV);
    const domFrac = dom / total;                       // how lopsided the mass is
    const pocPos = (hi > lo) ? (poc.price - lo) / (hi - lo) : 0.5;  // 0 bottom..1 top
    const active = bins.filter(v => v > (total / n) * 0.5).length / n;
    let shape;
    if (domFrac < 0.42 && active > 0.55) shape = 'I';  // spread ~ evenly => trend/balance
    else if (topV === dom && pocPos >= 0.58) shape = 'P';
    else if (botV === dom && pocPos <= 0.42) shape = 'b';
    else shape = 'D';
    return { shape, pocPos: +pocPos.toFixed(2), domFrac: +domFrac.toFixed(2) };
  }

  // ── Periodic profiles: one profile per fixed-length window, not one composite.
  // This is the "multiple occurrence instead of one projection" view: each
  // period gets its own POC / value area / shape, so the sequence of shapes is
  // readable across the chart and the trap rule can scan it.
  function periodicProfiles(bars, opts) {
    opts = opts || {};
    const per = Math.max(6, opts.periodBars || 21);
    const bins = opts.bins || 24;
    const vaPct = opts.valueAreaPct || 0.70;
    const out = [];
    for (let start = 0; start < bars.length; start += per) {
      const seg = bars.slice(start, Math.min(start + per, bars.length));
      if (seg.length < Math.max(5, per * 0.4)) break;  // drop a stubby trailing chunk
      const prof = computeProfile(seg, Object.assign({}, DEFAULT_OPTS, { bins, valueAreaPct: vaPct }));
      if (!prof) continue;
      const cls = classifyShape(prof);
      out.push({
        index: out.length,
        t0: seg[0].time, t1: seg[seg.length - 1].time,
        poc: prof.poc.price, vah: prof.valueArea.high, val: prof.valueArea.low,
        shape: cls.shape, pocPos: cls.pocPos, lo: prof.lo, hi: prof.hi,
      });
    }
    return out;
  }

  // ── Trap rule, ALL occurrences: a run of >= minRun P-profiles at consecutively
  // RISING POCs = buyers exhausting => reversal-down risk (buyer trap). The
  // mirror for b-profiles at falling POCs = seller trap => reversal-up.
  function detectTraps(profiles, opts) {
    opts = opts || {};
    const minRun = opts.minRun || 3;
    const out = [];
    const scan = (isShape, rising, type) => {
      let i = 0;
      while (i < profiles.length) {
        if (!isShape(profiles[i])) { i++; continue; }
        let j = i, cnt = 1;
        while (j + 1 < profiles.length && isShape(profiles[j + 1]) &&
               (rising ? profiles[j + 1].poc > profiles[j].poc
                       : profiles[j + 1].poc < profiles[j].poc)) { j++; cnt++; }
        if (cnt >= minRun) {
          out.push({ type, run: cnt, startIndex: i, endIndex: j,
                     t: profiles[j].t1, poc: profiles[j].poc, fromPoc: profiles[i].poc });
        }
        i = j + 1;
      }
    };
    scan(p => p.shape === 'P', true, 'buyer_trap');
    scan(p => p.shape === 'b', false, 'seller_trap');
    out.sort((a, b) => a.t - b.t);
    return out;
  }

  global.VP = {
    VERSION: '1.1.0',
    computeProfile, findConfluence,
    classifyShape, periodicProfiles, detectTraps,
  };
})(typeof window !== 'undefined' ? window : globalThis);
