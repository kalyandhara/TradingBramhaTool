/*!
 * svp_backtest_runner.js — walk the REAL SVP engine forward, emit a signals CSV.
 *
 * Phase 1 of the SVP Confluence Signal backtest (see the wiki design page
 * "SVP Confluence Signal — Backtest Design"). This imports the ACTUAL engine
 * (volume_profile.js + session_volume_profile.js) rather than re-implementing
 * it, so the numbers the backtest scores are the numbers the chart shows.
 *
 * At each bar i (from a warmup index onward) it calls SVP.analyze(bars[0..i])
 * and records the resulting signal plus one NETTED signed feature per factor
 * family, so the Python side (svp_backtest.py) can attribute edge to factors and
 * (Phase B) fit weights. No forward information is used here — the label /
 * barrier outcome is computed downstream from bars strictly after i.
 *
 * Usage:
 *   node svp_backtest_runner.js cache/backtest/_NSEI_1d.json [out.csv]
 *   node svp_backtest_runner.js cache/backtest/_NSEI_1d.json --settled   # drop in-progress session
 */
'use strict';

const fs = require('fs');
const path = require('path');

// The engine modules attach to globalThis via `(typeof window !== 'undefined' …)`.
global.window = global;
require(path.join(__dirname, 'volume_profile.js'));
require(path.join(__dirname, 'session_volume_profile.js'));

// Map a factor's display name to its family column (matches SIG_W keys).
function familyOf(name) {
  if (name.indexOf('regime') >= 0)     return 'regime';
  if (name.indexOf('VA ') === 0)       return 'va';
  if (name.indexOf('trap') >= 0)       return 'trap';
  if (name.indexOf('exhaustion') >= 0) return 'exhaustion';
  if (name.indexOf('sequence') >= 0)   return 'sequence';
  if (name.indexOf('sweep') >= 0)      return 'sweep';
  if (name.indexOf('cluster') >= 0)    return 'cluster';
  return null;
}
const FAMILIES = ['regime', 'va', 'trap', 'exhaustion', 'sequence', 'sweep', 'cluster'];

function run() {
  const args = process.argv.slice(2);
  const inPath = args[0];
  if (!inPath) { console.error('usage: node svp_backtest_runner.js <bars.json> [out.csv] [--settled]'); process.exit(1); }
  const settled = args.indexOf('--settled') >= 0;
  const outArg = args.find(a => a !== inPath && a !== '--settled');

  const doc = JSON.parse(fs.readFileSync(inPath, 'utf-8'));
  const symbol = doc.symbol, tf = doc.tf, bars = doc.bars;
  if (!bars || bars.length < 80) { console.error('too few bars'); process.exit(1); }

  const safe = symbol.replace(/[\^=-]/g, '_');
  const outPath = outArg || path.join(path.dirname(inPath), `${safe}_${tf}_signals.csv`);

  // Warmup: need >=12 completed sessions. Daily groups per ISO week (~5 bars),
  // 1h/… group per calendar day. Use a generous bar warmup so the first analyze
  // has a full session stack; analyze() itself returns null below 20 bars.
  const WARM = tf === '1d' ? 70 : (tf === '1w' ? 60 : 60);

  const cols = ['ts', 'symbol', 'tf', 'i', 'price', 'dir', 'kind', 'conf',
    'score', 'bullW', 'bearW', 'agreement', 'target', 'invalidation',
    ...FAMILIES.map(f => 'f_' + f)];
  const rows = [cols.join(',')];

  let nSig = 0, nBuy = 0, nSell = 0, nNeutral = 0, nErr = 0;
  for (let i = WARM; i < bars.length; i++) {
    let slice = bars.slice(0, i + 1);
    // Settled variant: drop the still-forming last session so only completed
    // sessions inform the read (measures the repainting sensitivity).
    if (settled) {
      const segs = window.SVP.segment(slice, tf);
      if (segs.length >= 2) slice = slice.slice(0, segs[segs.length - 1].i0);
      if (slice.length < 40) continue;
    }
    let r;
    try { r = window.SVP.analyze(slice, tf); }
    catch (e) { nErr++; continue; }
    if (!r || !r.signal) continue;
    const s = r.signal;

    const fam = {}; FAMILIES.forEach(f => fam[f] = 0);
    for (const fct of (s.factors || [])) {
      const k = familyOf(fct.name);
      if (k) fam[k] += fct.dir * fct.w;   // NET signed contribution per family
    }

    const price = bars[i].close;
    rows.push([
      bars[i].time, symbol, tf, i, price, s.dir, s.kind || '', s.confidence || '',
      s.score, s.bullW, s.bearW, s.agreement,
      s.target == null ? '' : s.target,
      s.invalidation == null ? '' : s.invalidation,
      ...FAMILIES.map(f => fam[f].toFixed(3)),
    ].join(','));

    nSig++;
    if (s.dir === 'BUY') nBuy++; else if (s.dir === 'SELL') nSell++; else nNeutral++;
  }

  fs.writeFileSync(outPath, rows.join('\n') + '\n', 'utf-8');
  console.log(`${symbol} ${tf}: ${bars.length} bars → ${nSig} rows `
    + `(BUY ${nBuy} · SELL ${nSell} · NEUTRAL ${nNeutral}${nErr ? ' · err ' + nErr : ''})`
    + `${settled ? ' [settled]' : ''} → ${path.basename(outPath)}`);
}

run();
