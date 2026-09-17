/*!
 * svp_structure_runner.js — walk the REAL structure engine forward, emit a CSV.
 *
 * Phase 1 of B-56's pre-registered test (see the wiki page "SVP Structure Signal
 * — Test Design (pre-registered)"). Same shape as `svp_backtest_runner.js`, which
 * scores the seven-factor COMPOSITE: this one scores `SVPSTRUCT.read`, the
 * separate rule-based structural construction, and the two are deliberately kept
 * as two runners rather than one with a flag — they emit different columns and
 * the composite's runner is a published measurement's input, which should not
 * change shape because a second study arrived.
 *
 * It imports the ACTUAL engine (volume_profile.js + session_volume_profile.js +
 * svp_structure_signal.js), so the reads scored here are the reads the chart
 * shows.
 *
 * LOOK-AHEAD: at each bar i it calls SVP.analyze(bars[0..i]) and passes that same
 * slice to SVPSTRUCT.read, so a row at i uses nothing after i. The forward return
 * is computed downstream from bars strictly after i.
 *
 * Usage:
 *   node svp_structure_runner.js cache/backtest/_NSEI_1d.json [out.csv]
 */
'use strict';

const fs = require('fs');
const path = require('path');

global.window = global;
require(path.join(__dirname, 'volume_profile.js'));
require(path.join(__dirname, 'session_volume_profile.js'));
require(path.join(__dirname, 'svp_structure_signal.js'));

function run() {
  const args = process.argv.slice(2);
  const inPath = args[0];
  if (!inPath) {
    console.error('usage: node svp_structure_runner.js <bars.json> [out.csv]');
    process.exit(1);
  }
  const outArg = args.find(a => a !== inPath);

  const doc = JSON.parse(fs.readFileSync(inPath, 'utf-8'));
  const symbol = doc.symbol, tf = doc.tf, bars = doc.bars;
  if (!bars || bars.length < 80) { console.error('too few bars'); process.exit(1); }

  const safe = symbol.replace(/[\^=-]/g, '_');
  const outPath = outArg || path.join(path.dirname(inPath), `${safe}_${tf}_struct.csv`);

  // Same warmup as the composite runner: the structure read needs >= 3 sessions
  // for a migration call and analyze() itself returns null below 20 bars, but the
  // basket and the window are shared with the composite study so the two results
  // are comparable bar-for-bar.
  const WARM = tf === '1d' ? 70 : 60;

  const cols = ['ts', 'symbol', 'tf', 'i', 'price', 'read',
    'trend_dir', 'trend_frac', 'last_shape', 'shape_seq', 'n_why'];
  const rows = [cols.join(',')];

  let nBuy = 0, nSell = 0, nHold = 0, nErr = 0, nNull = 0;
  for (let i = WARM; i < bars.length; i++) {
    const slice = bars.slice(0, i + 1);
    let r, st;
    try {
      r = window.SVP.analyze(slice, tf);
      if (!r) { nNull++; continue; }
      st = window.SVPSTRUCT.read(r, slice);
    } catch (e) { nErr++; continue; }
    if (!st) { nNull++; continue; }

    rows.push([
      bars[i].time, symbol, tf, i, bars[i].close, st.read,
      st.trend ? st.trend.dir : '', st.trend ? st.trend.frac : '',
      st.last_shape || '', st.shape_seq || '', (st.why || []).length,
    ].join(','));

    if (st.read === 'BUY') nBuy++;
    else if (st.read === 'SELL') nSell++;
    else nHold++;
  }

  fs.writeFileSync(outPath, rows.join('\n') + '\n', 'utf-8');
  console.error(`${symbol} ${tf}: ${bars.length} bars → ${rows.length - 1} rows `
    + `(BUY ${nBuy} · SELL ${nSell} · HOLD ${nHold}`
    + `${nNull ? ' · null ' + nNull : ''}${nErr ? ' · err ' + nErr : ''})`
    + ` → ${path.basename(outPath)}`);
}

run();
