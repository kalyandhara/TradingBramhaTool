/*!
 * session_volume_profile.js — Session Volume Profile HD: one volume profile per
 * session, each classified D / P / B / I, with accumulation/distribution +
 * trap-stack sensing. Pure computation (window.SVP); rendering lives in
 * chart_dashboard.html (drawSessionVP()).
 *
 * Builds on volume_profile.js (window.VP) — it reuses VP.computeProfile per
 * session rather than re-implementing the histogram, so a session's POC / value
 * area mean exactly what they mean on the single-profile overlay.
 *
 * ── Session grouping ────────────────────────────────────────────────────────
 *   intraday (1m..4h) -> one profile per calendar day
 *   1d               -> per ISO week
 *   1w               -> per month
 *
 * ── Shape classification (Manish's D/P/B/I; standard market-profile shapes) ──
 * From the POC's position inside the session range + how spread the value area
 * is (all OBSERVED, not drawn):
 *   I-Profile : value area spans most of the range (thin, even) -> balance -> sideways.
 *   P-Profile : POC in the upper third -> fat top -> aggressive buying / short-covering.
 *   B-Profile : POC in the lower third -> fat bottom -> aggressive selling.
 *   D-Profile : POC mid-range -> directional / normal day.
 *
 * ── Accumulation / Distribution + trap ──────────────────────────────────────
 * A run of >=3 P-profiles at consecutively HIGHER POCs = buyers being walked up
 * = distribution / exhaustion -> reversal-DOWN risk (Manish's trap rule). The
 * mirror (>=3 B at lower POCs) = accumulation / seller exhaustion -> bounce risk.
 *
 * NOT ADVICE. Shapes and the trap rule are interpretive; the trap rule in
 * particular is a countable hypothesis that should be backtested (see the wiki
 * New-Moon / SBC backtests for the discipline). Reported so it can be checked.
 *
 * Public API (window.SVP):
 *   SVP.segment(bars, tf)              -> [{key, i0, i1, startTime, endTime, bars}]
 *   SVP.classify(profile, hi, lo)      -> {shape, pocPos, vaFrac, label}
 *   SVP.analyze(bars, tf, opts)        -> {sessions[], trap, ad, levels, card}
 *
 * Bar shape: {time, open, high, low, close, volume}
 */
(function (global) {
  'use strict';

  function toDate(t) {
    if (typeof t === 'number') return new Date(t * 1000);
    if (typeof t === 'string') return new Date(t.length <= 10 ? t + 'T00:00:00Z' : t);
    if (t && t.year) return new Date(Date.UTC(t.year, (t.month || 1) - 1, t.day || 1));
    return new Date();
  }

  //: A profile built from fewer than this many bars is noise wearing a profile's
  //: clothes, so `analyze` discards such segments. That guard used to interact badly
  //: with a fixed per-timeframe grouping — see chooseGrain.
  const MIN_SESSION_BARS = 3;

  function periodKey(t, grain) {
    const d = toDate(t);
    if (grain === 'month') return d.getUTCFullYear() + '-M' + (d.getUTCMonth() + 1);
    if (grain === 'week') {                              // ISO week
      const dt = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
      const dayNum = (dt.getUTCDay() + 6) % 7;
      dt.setUTCDate(dt.getUTCDate() - dayNum + 3);
      const firstThu = new Date(Date.UTC(dt.getUTCFullYear(), 0, 4));
      const wk = 1 + Math.round(((dt - firstThu) / 864e5 - 3 + ((firstThu.getUTCDay() + 6) % 7)) / 7);
      return dt.getUTCFullYear() + '-W' + wk;
    }
    return d.getUTCFullYear() + '-' + (d.getUTCMonth() + 1) + '-' + d.getUTCDate();
  }

  function medianBarsPerPeriod(bars, grain) {
    const counts = new Map();
    for (const b of bars) {
      const k = periodKey(b.time, grain);
      counts.set(k, (counts.get(k) || 0) + 1);
    }
    const v = Array.from(counts.values()).sort((a, b) => a - b);
    return v.length ? v[Math.floor(v.length / 2)] : 0;
  }

  //: Grouping grain is MEASURED from the bars, not read off a timeframe table.
  //:
  //: The old code grouped every intraday timeframe by calendar day. That silently
  //: broke 4h charts on exchange-hours instruments: an NSE cash session is ~6.25h,
  //: so a day holds TWO 4h bars, every segment failed the MIN_SESSION_BARS guard,
  //: and `sessions` came back empty — which rendered as a card with a composite POC
  //: and nothing else, and a profile overlay that drew nothing at all. Crypto was
  //: unaffected (24h day = six 4h bars), which is why it survived review.
  //:
  //: Measuring instead of tabulating fixes every such combination at once — any
  //: exchange, any session length, any future timeframe — and matches how
  //: `isLikelyLiquidETF` already detects instrument character in this repo.
  const GRAIN_LADDER = ['day', 'week', 'month'];

  function chooseGrain(bars, tf) {
    // Daily/weekly charts keep their established meaning: one "session" is the
    // period ABOVE the bar, so a 1d bar groups per week and a 1w bar per month.
    if (tf === '1w') return 'month';
    if (tf === '1d') return 'week';
    for (const g of GRAIN_LADDER) {
      if (medianBarsPerPeriod(bars, g) >= MIN_SESSION_BARS) return g;
    }
    return 'month';
  }

  function segment(bars, tf) {
    const grain = chooseGrain(bars, tf);
    const out = segmentByGrain(bars, grain);
    out.grain = grain;                 // informational; array semantics unchanged
    return out;
  }

  function segmentByGrain(bars, grain) {
    const out = [];
    let cur = null;
    for (let i = 0; i < bars.length; i++) {
      const k = periodKey(bars[i].time, grain);
      if (!cur || cur.key !== k) {
        cur = { key: k, i0: i, i1: i, startTime: bars[i].time, endTime: bars[i].time, bars: [] };
        out.push(cur);
      }
      cur.i1 = i; cur.endTime = bars[i].time; cur.bars.push(bars[i]);
    }
    return out;
  }

  function classify(profile, hi, lo) {
    const range = hi - lo;
    if (!(range > 0) || !profile) return { shape: 'I', pocPos: 0.5, vaFrac: 1, label: 'balance' };
    const pocPos = (profile.poc.price - lo) / range;
    const vaFrac = (profile.valueArea.high - profile.valueArea.low) / range;
    // Thin/even value area covering most of the range = balance.
    if (vaFrac >= 0.78) return { shape: 'I', pocPos, vaFrac, label: 'balance → sideways' };
    if (pocPos >= 0.62) return { shape: 'P', pocPos, vaFrac, label: 'buying / short-covering' };
    if (pocPos <= 0.38) return { shape: 'B', pocPos, vaFrac, label: 'selling / liquidation' };
    return { shape: 'D', pocPos, vaFrac, label: 'directional' };
  }

  function analyze(bars, tf, opts) {
    opts = opts || {};
    if (typeof global.VP === 'undefined' || !bars || bars.length < 20) return null;
    const maxSessions = opts.maxSessions || 12;
    const binsPerSession = opts.bins || 24;
    const grain = opts.grain || chooseGrain(bars, tf);
    let segs = segmentByGrain(bars, grain);
    segs = segs.slice(-maxSessions);

    const sessions = [];
    for (const s of segs) {
      if (s.bars.length < MIN_SESSION_BARS) continue;
      const prof = global.VP.computeProfile(s.bars, { bins: binsPerSession });
      if (!prof) continue;
      let hi = -Infinity, lo = Infinity;
      for (const b of s.bars) { if (b.high > hi) hi = b.high; if (b.low < lo) lo = b.low; }
      const cls = classify(prof, hi, lo);
      sessions.push({
        key: s.key, startTime: s.startTime, endTime: s.endTime,
        hi, lo, poc: prof.poc.price, vah: prof.valueArea.high, val: prof.valueArea.low,
        bins: prof.bins, binEdges: prof.binEdges, pocIdx: prof.poc.idx,
        shape: cls.shape, shapeLabel: cls.label, pocPos: cls.pocPos,
      });
    }

    // Trap / exhaustion: a run of >=3 same-shape sessions with monotonic POC.
    const trap = detectTrap(sessions);
    const ad = readAccumDist(sessions, trap);
    // Critical levels = the POCs ("where the gods reside"), most recent first.
    const levels = sessions.slice().reverse().map(s => ({ price: s.poc, shape: s.shape, key: s.key }));

    // Composite value area across the whole retained window — the "5-session
    // acceptance range" the confluence model reads for VA acceptance/rejection.
    const windowBars = [];
    for (const s of segs) for (const b of s.bars) windowBars.push(b);
    let composite = null;
    const cp = global.VP.computeProfile(windowBars, { bins: opts.compositeBins || 40 });
    if (cp) composite = { poc: cp.poc.price, vah: cp.valueArea.high, val: cp.valueArea.low };

    // Confluence BUY / SELL / TRAP-REVERSAL signal (see buildSignal).
    const signal = buildSignal(sessions, windowBars, composite, trap, ad);

    // If nothing survived the bar-count guard, say so rather than returning a
    // half-populated object the caller will render as a blank card.
    const note = sessions.length ? null
      : `no ${grain} segment reached ${MIN_SESSION_BARS} bars — profile not computable at this timeframe`;

    // `compositeProfile` is the FULL profile object behind `composite` -- bins,
    // hvnZones, lvnZones. Additive: `composite` keeps its {poc,vah,val} shape so
    // every existing caller is untouched. Exposed because a structural read needs
    // the NODES, and recomputing them outside would be a second profile free to
    // disagree with the one the card draws.
    return { sessions, trap, ad, levels, composite, compositeProfile: cp,
             signal, grain, note,
             card: buildCard(sessions, trap, ad, composite, signal, grain, note) };
  }

  function detectTrap(sessions) {
    // Longest trailing run ending at the last session.
    if (sessions.length < 3) return null;
    const last = sessions[sessions.length - 1];
    let run = 1;
    for (let i = sessions.length - 2; i >= 0; i--) {
      const a = sessions[i], b = sessions[i + 1];
      if (a.shape === last.shape &&
          ((last.shape === 'P' && b.poc > a.poc) ||
           (last.shape === 'B' && b.poc < a.poc))) run++;
      else break;
    }
    if (run < 3) return null;
    if (last.shape === 'P') return { type: 'buyer-exhaustion', dir: 'down', count: run,
      note: `${run} P-profiles at rising POCs → buyers walked up → reversal-DOWN risk` };
    if (last.shape === 'B') return { type: 'seller-exhaustion', dir: 'up', count: run,
      note: `${run} B-profiles at falling POCs → sellers exhausting → bounce-UP risk` };
    return null;
  }

  function readAccumDist(sessions, trap) {
    if (!sessions.length) return { state: '—', note: '' };
    if (trap && trap.type === 'buyer-exhaustion')
      return { state: 'DISTRIBUTION', note: 'buyers being distributed into at the highs' };
    if (trap && trap.type === 'seller-exhaustion')
      return { state: 'ACCUMULATION', note: 'sellers being absorbed at the lows' };
    const recent = sessions.slice(-4);
    const c = { P: 0, B: 0, D: 0, I: 0 };
    recent.forEach(s => c[s.shape]++);
    if (c.I >= 2) return { state: 'BALANCE', note: 'range / low participation — sideways' };
    if (c.P > c.B && c.P >= 2) return { state: 'ACCUMULATION→MARKUP', note: 'buying pressure building' };
    if (c.B > c.P && c.B >= 2) return { state: 'DISTRIBUTION→MARKDOWN', note: 'selling pressure building' };
    return { state: 'DIRECTIONAL', note: 'trending — no clear stack yet' };
  }

  // ── Confluence signal engine ────────────────────────────────────────────────
  //
  // A transparent multi-factor rules engine over the session structure. Each
  // factor is a COUNTABLE boolean with a NAMED PRIOR weight; fired factors sum
  // into a signed score (bull +, bear −) that maps to BUY / SELL / NEUTRAL, plus
  // a distinct TRAP-REVERSAL kind when a rejection/exhaustion factor dominates.
  //
  // This is NOT a validated system. The factor list mirrors standard auction /
  // market-profile confluence (D-anchor regime, composite value-area accept/
  // reject, the 3-4× POC trap rule, exhaustion stacks, session-sequence tilt,
  // liquidity sweeps, POC clustering) but every WEIGHT and THRESHOLD below is a
  // prior to be backtested — same honesty stance as the trap rule itself. The
  // point of the design is that each factor is individually checkable, so the
  // model can be scored against outcomes rather than believed.
  const SIG_W = {                 // prior weights — tune / backtest, don't trust
    regime:     1.0,   // price vs Direction-session POC (trend anchor)
    va:         1.2,   // composite value-area acceptance / rejection
    trap:       1.5,   // 3-4× POC rejection (the headline reversal setup)
    exhaustion: 1.0,   // >=3 same-shape stack (buyer/seller exhaustion)
    sequence:   0.8,   // recent P/B session-shape tilt (accum/dist)
    sweep:      1.0,   // liquidity sweep of prior-session extreme + reclaim
    cluster:    0.5,   // POC cluster acting as a support/resistance shelf
  };
  const TRAP_MIN = 3;             // "3-4×" rule: rejections needed to call a trap
  const NET_TRIGGER = 1.5;        // |net| below this = NEUTRAL / watch
  const MIN_EVIDENCE = 1.0;       // total weight below this = not enough to call

  // Count distinct rejection EVENTS at a level (consecutive touching bars = one
  // event). support=true → price dipped to the level and closed back above it;
  // support=false → price tagged the level from below and closed back under.
  function countRejections(bars, level, tol, support) {
    let events = 0, inTouch = false;
    for (const b of bars) {
      const touched = support
        ? (b.low <= level + tol && b.close > level - tol * 0.25)   // pierced & held above
        : (b.high >= level - tol && b.close < level + tol * 0.25);  // tagged & held below
      if (touched && !inTouch) { events++; inTouch = true; }
      else if (!touched) inTouch = false;
    }
    return events;
  }

  function buildSignal(sessions, bars, composite, trap, ad) {
    if (!sessions || sessions.length < 3 || !bars || bars.length < 5)
      return { dir: 'NEUTRAL', kind: null, reason: 'insufficient sessions', factors: [] };

    const price     = bars[bars.length - 1].close;
    const prevClose = bars[bars.length - 2].close;
    if (!(price > 0)) return { dir: 'NEUTRAL', kind: null, reason: 'no price', factors: [] };

    // Two tolerances, both scaled to typical session range:
    //   tol      — WIDE: level grouping / cluster / regime "near" band.
    //   tolTight — NARROW: a rejection must actually tag the level and then pull
    //              away, so distinct probes separate into distinct trap counts
    //              (a wide band merges an oscillation into one false "test").
    const ranges = sessions.map(s => s.hi - s.lo).filter(r => r > 0);
    const avgRange = ranges.length ? ranges.reduce((a, r) => a + r, 0) / ranges.length : 0;
    const tol = Math.max(avgRange * 0.2, price * 0.0015);
    const tolTight = Math.max(avgRange * 0.06, price * 0.0006);

    const factors = [];   // {name, dir:+1/-1, w, detail}
    const add = (name, dir, w, detail) => factors.push({ name, dir, w, detail });

    // Candidate level set: every session POC (tagged by shape) + composite edges.
    const levels = sessions.map(s => ({ price: s.poc, shape: s.shape }));
    if (composite) {
      levels.push({ price: composite.vah, shape: 'VAH' });
      levels.push({ price: composite.val, shape: 'VAL' });
      levels.push({ price: composite.poc, shape: 'cPOC' });
    }
    const supports    = levels.filter(l => l.price < price - tol * 0.25).sort((a, b) => b.price - a.price);
    const resistances = levels.filter(l => l.price > price + tol * 0.25).sort((a, b) => a.price - b.price);
    const nearSup = supports[0] || null;
    const nearRes = resistances[0] || null;

    // 1) Trend anchor — most recent Direction-session POC (else composite POC).
    let dAnchor = null;
    for (let i = sessions.length - 1; i >= 0; i--) if (sessions[i].shape === 'D') { dAnchor = sessions[i].poc; break; }
    if (dAnchor == null && composite) dAnchor = composite.poc;
    if (dAnchor != null) {
      if (price > dAnchor + tol)      add('D-anchor regime', +1, SIG_W.regime, `price ${fmt(price)} above Direction-POC ${fmt(dAnchor)} → bull regime`);
      else if (price < dAnchor - tol) add('D-anchor regime', -1, SIG_W.regime, `price ${fmt(price)} below Direction-POC ${fmt(dAnchor)} → bear regime`);
    }

    // 2) Composite value-area acceptance / rejection.
    if (composite) {
      const { vah, val } = composite;
      if (prevClose < val && price >= val)
        add('VA re-entry', +1, SIG_W.va, `reclaimed composite VAL ${fmt(val)} from below → acceptance`);
      else if (prevClose > vah && price <= vah)
        add('VA re-entry', -1, SIG_W.va, `rejected back inside from above VAH ${fmt(vah)} → distribution`);
      else if (price > vah && prevClose > vah)
        add('VA breakout', +1, SIG_W.va, `holding above composite VAH ${fmt(vah)} → acceptance higher`);
      else if (price < val && prevClose < val)
        add('VA breakdown', -1, SIG_W.va, `holding below composite VAL ${fmt(val)} → acceptance lower`);
    }

    // 3) 3-4× trap rule — rejection count at the nearest support / resistance.
    let trapFired = 0;
    if (nearSup) {
      const n = countRejections(bars, nearSup.price, tolTight, true);
      if (n >= TRAP_MIN && price > nearSup.price)
        { add('POC trap (support)', +1, SIG_W.trap, `${n}× rejection of ${nearSup.shape}-level ${fmt(nearSup.price)} held → reversal-UP`); trapFired = +1; }
    }
    if (nearRes) {
      const n = countRejections(bars, nearRes.price, tolTight, false);
      if (n >= TRAP_MIN && price < nearRes.price)
        { add('POC trap (resistance)', -1, SIG_W.trap, `${n}× rejection of ${nearRes.shape}-level ${fmt(nearRes.price)} failed → reversal-DOWN`); trapFired = trapFired || -1; }
    }

    // 4) Exhaustion stack (existing detectTrap): buyer→down, seller→up.
    if (trap && trap.type === 'buyer-exhaustion')
      add('exhaustion stack', -1, SIG_W.exhaustion, trap.note);
    else if (trap && trap.type === 'seller-exhaustion')
      add('exhaustion stack', +1, SIG_W.exhaustion, trap.note);

    // 5) Session-sequence tilt (accum/dist read).
    if (ad) {
      if (/ACCUM|MARKUP/.test(ad.state))       add('sequence tilt', +1, SIG_W.sequence, `${ad.state}: ${ad.note}`);
      else if (/DISTRIB|MARKDOWN/.test(ad.state)) add('sequence tilt', -1, SIG_W.sequence, `${ad.state}: ${ad.note}`);
    }

    // 6) Liquidity sweep of the prior completed session's extreme + reclaim.
    if (sessions.length >= 2) {
      const cur = sessions[sessions.length - 1], prev = sessions[sessions.length - 2];
      if (cur.lo < prev.lo && price > prev.lo)
        add('liquidity sweep', +1, SIG_W.sweep, `swept prior-session low ${fmt(prev.lo)} and reclaimed → bull sweep`);
      else if (cur.hi > prev.hi && price < prev.hi)
        add('liquidity sweep', -1, SIG_W.sweep, `swept prior-session high ${fmt(prev.hi)} and rejected → bear sweep`);
    }

    // 7) POC cluster shelf — >=2 POCs within tol form a support/resistance shelf.
    const clusterAt = (arr) => {
      for (let i = 0; i < arr.length; i++) {
        let c = 1;
        for (let j = i + 1; j < arr.length; j++) if (Math.abs(arr[j].price - arr[i].price) <= tol) c++;
        if (c >= 2) return { price: arr[i].price, count: c };
      }
      return null;
    };
    const supClust = clusterAt(supports), resClust = clusterAt(resistances);
    if (supClust) add('POC cluster', +1, SIG_W.cluster, `${supClust.count} POCs stacked at ${fmt(supClust.price)} → support shelf below`);
    if (resClust) add('POC cluster', -1, SIG_W.cluster, `${resClust.count} POCs stacked at ${fmt(resClust.price)} → resistance shelf above`);

    // ── Aggregate ──────────────────────────────────────────────────────────────
    let bullW = 0, bearW = 0;
    for (const f of factors) (f.dir > 0 ? (bullW += f.w) : (bearW += f.w));
    const net = bullW - bearW;
    const total = bullW + bearW;
    const agreement = total > 0 ? Math.abs(net) / total : 0;   // 1 = one-sided

    let dir = 'NEUTRAL';
    if (total >= MIN_EVIDENCE && net >= NET_TRIGGER) dir = 'BUY';
    else if (total >= MIN_EVIDENCE && net <= -NET_TRIGGER) dir = 'SELL';

    let confidence = 'low';
    if (Math.abs(net) >= 3 && agreement >= 0.6) confidence = 'high';
    else if (Math.abs(net) >= 1.8) confidence = 'medium';

    // Kind: trap-reversal if a rejection/exhaustion factor drives, and it agrees
    // with the net direction; breakout if a VA break drove it; else continuation.
    let kind = null;
    if (dir !== 'NEUTRAL') {
      const dirSign = dir === 'BUY' ? 1 : -1;
      const hasTrap = trapFired === dirSign
        || factors.some(f => f.name === 'exhaustion stack' && f.dir === dirSign);
      const hasBreak = factors.some(f => /VA breakout|VA breakdown/.test(f.name) && f.dir === dirSign);
      kind = hasTrap ? 'trap-reversal' : hasBreak ? 'breakout' : 'continuation';
    }

    // Target / invalidation from the nearest opposing & protective levels. The
    // target must sit on the correct side of price — if price has already broken
    // past all overhead/underfoot levels (a breakout), there is no level to aim
    // at, so target is left null ("open") rather than pointing backwards.
    let target = null, invalidation = null;
    if (dir === 'BUY') {
      target = nearRes ? nearRes.price
             : (composite && composite.vah > price ? composite.vah : null);
      invalidation = nearSup ? nearSup.price - tol : null;
    }
    if (dir === 'SELL') {
      target = nearSup ? nearSup.price
             : (composite && composite.val < price ? composite.val : null);
      invalidation = nearRes ? nearRes.price + tol : null;
    }

    return {
      dir, kind, confidence, price,
      score: +net.toFixed(2), bullW: +bullW.toFixed(2), bearW: +bearW.toFixed(2),
      agreement: +agreement.toFixed(2),
      factors: factors.sort((a, b) => b.w - a.w),
      target, invalidation,
      // MEASURED 2026-08-29 and it failed: corr(score, 20d fwd) = -0.041, deciles
      // non-monotonic, BUY-high confidence worse than BUY-low, 5 of 7 factor
      // families sign-inverted. This string used to say 'unbacktested', which
      // became false that day. chart_dashboard.html already overrode it at the
      // RENDER layer -- but an override only protects the one renderer that
      // knows to apply it, and the screener reading `signal.caveat` would have
      // picked up the stale claim. The engine now carries the truth itself.
      caveat: 'Read the structure, not the BUY/SELL word — the direction call \nwas measured (2026-08-29) and has no edge. Not advice.',
    };
  }

  function fmt(v) { return Number.isFinite(v) ? v.toFixed(2) : '—'; }

  function buildCard(sessions, trap, ad, composite, signal, grain, note) {
    const last = sessions[sessions.length - 1] || null;
    const seq = sessions.slice(-6).map(s => s.shape).join(' ');
    return {
      current: last ? { shape: last.shape, label: last.shapeLabel, poc: last.poc,
                        vah: last.vah, val: last.val } : null,
      sequence: seq,
      grain: grain || null, note: note || null,
      trap, ad, composite, signal,
      levels: sessions.slice(-4).reverse().map(s => ({ poc: s.poc, shape: s.shape })),
    };
  }

  global.SVP = { segment, classify, analyze, buildSignal, chooseGrain,
                 MIN_SESSION_BARS };
})(typeof window !== 'undefined' ? window : globalThis);
