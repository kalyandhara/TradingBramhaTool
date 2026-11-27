/* replay_mode.js — Multi-Chart dual pick replay (pure computation, no DOM).
 *
 * Opened from Recommendation Audit › Pick replay with
 *   ?symbol=X&replay=YYYY-MM-DD&entry=&stop=&target=&sdate=&skind=S|T&sector=&rank=&label=&ddate=
 * pane 1 shows the chart as it stood on the pick day (bars cut at the pick
 * date, so every indicator is computed without hindsight), pane 2 everything
 * since, with the plan's levels, NIFTY 500 and the sector index rebased to the
 * entry, and event letters:
 *   PICK  the entry session (the open after the pick day — the audit's entry)
 *   S / T stop / target hit first, as the audit measured it
 *   V     volume breakdown: first close below the prior 20-session low on at
 *         least 1.5× the prior 20-session average volume. A desk rule for
 *         reading the chart, not a measured signal.
 *   D     re-score downgrade (`ddate=`): the first session the nightly pick
 *         re-score found the Overall Rating 15+ points below the pick day.
 *         A prior, not a measured signal (rec_rescore.DOWNGRADE_POINTS).
 *   E     results days come from the existing Event Markers indicator.
 *
 * Daily bars are stamped 00:00 UTC on the trading date (chart_server /api/ohlcv).
 */
(function (root) {
  'use strict';

  const DATE = /^\d{4}-\d{2}-\d{2}$/;

  function dayTime(iso) {
    const [y, m, d] = iso.split('-').map(Number);
    return Date.UTC(y, m - 1, d) / 1000;
  }

  function num(v) {
    if (v == null || v === '') return null;
    const f = parseFloat(v);
    return Number.isFinite(f) ? f : null;
  }

  function parseReplay(search) {
    const q = new URLSearchParams(search || '');
    const date = q.get('replay');
    if (!date || !DATE.test(date)) return null;
    const sdate = q.get('sdate');
    const skind = q.get('skind');
    const ddate = q.get('ddate');
    const rank = parseInt(q.get('rank') || '', 10);
    return {
      date, cut: dayTime(date),
      entry: num(q.get('entry')), stop: num(q.get('stop')), target: num(q.get('target')),
      sdate: sdate && DATE.test(sdate) ? sdate : null,
      skind: skind === 'S' || skind === 'T' ? skind : null,
      ddate: ddate && DATE.test(ddate) ? ddate : null,
      sector: q.get('sector') || null,
      rank: Number.isFinite(rank) ? rank : null,
      label: q.get('label') || '',
    };
  }

  /** Bars on or before the pick day only — nothing the desk could not have seen. */
  function cutBars(bars, cut) {
    return (bars || []).filter(b => b.time <= cut);
  }

  /** Another series' closes rebased so it starts at `entryPx` on the entry day.
   *  Base = that series' OPEN on the entry day (the audit measures excess from the
   *  entry-day open), else its last close before the entry day. */
  function rebase(other, entryTime, entryPx) {
    if (!other || !other.length || !(entryPx > 0)) return [];
    const at = other.find(b => b.time === entryTime);
    let base = at ? at.open : null;
    if (!(base > 0)) {
      const prior = other.filter(b => b.time < entryTime);
      base = prior.length ? prior[prior.length - 1].close : null;
    }
    if (!(base > 0)) return [];
    return other.filter(b => b.time >= entryTime)
      .map(b => ({time: b.time, value: entryPx * b.close / base}));
  }

  /** First session after the pick that closes below the prior `look`-session low
   *  on at least `mult`× the prior average volume; null when none. */
  function volumeBreakdown(bars, cut, look = 20, mult = 1.5) {
    for (let i = look; i < (bars || []).length; i++) {
      const b = bars[i];
      if (b.time <= cut) continue;
      const prior = bars.slice(i - look, i);
      const lo = Math.min(...prior.map(x => x.low));
      const avgV = prior.reduce((s, x) => s + (x.volume || 0), 0) / look;
      if (b.close < lo && avgV > 0 && b.volume >= mult * avgV) return b.time;
    }
    return null;
  }

  /** Lightweight-Charts markers for the after-pick pane, sorted by time. */
  function markers(r, bars, vTime) {
    const out = [];
    const entryBar = (bars || []).find(b => b.time > r.cut);
    if (entryBar) out.push({time: entryBar.time, position: 'belowBar', shape: 'arrowUp',
                            color: '#ffb020', text: 'PICK'});
    if (r.skind && r.sdate) {
      out.push({time: dayTime(r.sdate), position: 'aboveBar', shape: 'arrowDown',
                color: r.skind === 'S' ? '#f85149' : '#3fb950', text: r.skind});
    }
    if (vTime != null) out.push({time: vTime, position: 'aboveBar', shape: 'circle',
                                 color: '#ff9800', text: 'V'});
    if (r.ddate) out.push({time: dayTime(r.ddate), position: 'aboveBar', shape: 'arrowDown',
                           color: '#d29922', text: 'D'});
    return out.sort((a, b) => a.time - b.time);
  }

  /** Legend for the after-pick pane (HTML). D appears only when the link carries
   *  one, and always with its caveat: it is a named prior, never a tested signal. */
  function afterLegend(r) {
    return '<b>AFTER PICK</b> · PICK entry · S stop / T target hit · V volume breakdown ' +
      '(desk rule) · E results' +
      (r && r.ddate ? ' · D rating downgrade (a prior, untested)' : '') +
      '<br>dotted: NIFTY 500 (grey) and sector (blue) rebased to the entry';
  }

  root.RPM = {dayTime, parseReplay, cutBars, rebase, volumeBreakdown, markers, afterLegend};
})(typeof window !== 'undefined' ? window : globalThis);
