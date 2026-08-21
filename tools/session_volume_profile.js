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

  function periodKey(t, tf) {
    const d = toDate(t);
    if (tf === '1w') return d.getUTCFullYear() + '-M' + (d.getUTCMonth() + 1);
    if (tf === '1d') {                                   // ISO week
      const dt = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
      const dayNum = (dt.getUTCDay() + 6) % 7;
      dt.setUTCDate(dt.getUTCDate() - dayNum + 3);
      const firstThu = new Date(Date.UTC(dt.getUTCFullYear(), 0, 4));
      const wk = 1 + Math.round(((dt - firstThu) / 864e5 - 3 + ((firstThu.getUTCDay() + 6) % 7)) / 7);
      return dt.getUTCFullYear() + '-W' + wk;
    }
    return d.getUTCFullYear() + '-' + (d.getUTCMonth() + 1) + '-' + d.getUTCDate();
  }

  function segment(bars, tf) {
    const out = [];
    let cur = null;
    for (let i = 0; i < bars.length; i++) {
      const k = periodKey(bars[i].time, tf);
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
    let segs = segment(bars, tf);
    segs = segs.slice(-maxSessions);

    const sessions = [];
    for (const s of segs) {
      if (s.bars.length < 3) continue;
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

    return { sessions, trap, ad, levels, card: buildCard(sessions, trap, ad) };
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

  function buildCard(sessions, trap, ad) {
    const last = sessions[sessions.length - 1] || null;
    const seq = sessions.slice(-6).map(s => s.shape).join(' ');
    return {
      current: last ? { shape: last.shape, label: last.shapeLabel, poc: last.poc,
                        vah: last.vah, val: last.val } : null,
      sequence: seq,
      trap, ad,
      levels: sessions.slice(-4).reverse().map(s => ({ poc: s.poc, shape: s.shape })),
    };
  }

  global.SVP = { segment, classify, analyze };
})(typeof window !== 'undefined' ? window : globalThis);
