/*!
 * evwma_vwap_macd_backtest.js — emit the REAL indicator's signals as CSV.
 *
 * Phase 1 of the EVWMA/VWAP MACD backtest, following the same split the SVP
 * backtest uses (svp_backtest_runner.js): the signal side imports the ACTUAL
 * shipped engine (evwma_vwap_macd.js) so the numbers scored downstream are the
 * numbers the chart draws, and the scoring side (evwma_vwap_macd_backtest.py)
 * never re-implements the rule.
 *
 * Unlike the SVP runner this does NOT need to re-analyze at every bar: every
 * term in the indicator (rolling volume sum, the EVWMA recursion, the two Pine
 * EMAs, the crossover test) is strictly backward-looking, so a single pass over
 * the full series and indexing at bar t is already look-ahead-free — the same
 * argument adx_di_backtest.py makes for Wilder's ADX.
 *
 * Usage:
 *   node evwma_vwap_macd_backtest.js cache/backtest/RELIANCE.NS_1d.json [out.csv]
 *
 * CSV columns: time,index,dir,close,macd,signal,hist,histPct
 *   dir: 1 = crossover(macd, signal) = the Pine strategy's long entry
 *       -1 = crossunder                = its short entry
 */
'use strict';

const fs = require('fs');
const path = require('path');

global.window = global;
require(path.join(__dirname, 'evwma_vwap_macd.js'));

function run() {
  const args = process.argv.slice(2);
  const inPath = args[0];
  if (!inPath) {
    console.error('usage: node evwma_vwap_macd_backtest.js <bars.json> [out.csv]');
    process.exit(1);
  }
  const doc = JSON.parse(fs.readFileSync(inPath, 'utf-8'));
  const bars = doc.bars;
  if (!bars || bars.length < 120) { console.error('too few bars: ' + inPath); process.exit(1); }

  const r = EVMACD.compute(bars, {tf: doc.tf});
  const safe = String(doc.symbol).replace(/[\^=-]/g, '_');
  const outPath = args[1] || path.join(path.dirname(inPath), `${safe}_${doc.tf}_evmacd.csv`);

  const lines = ['time,index,dir,close,macd,signal,hist,histPct'];
  r.signals.forEach(s => {
    lines.push([s.time, s.index, s.dir, s.price, s.macd, s.signal, s.hist, s.histPct].join(','));
  });
  fs.writeFileSync(outPath, lines.join('\n') + '\n', 'utf-8');
  console.error(`${doc.symbol} ${doc.tf}: ${bars.length} bars, ${r.signals.length} signals `
                + `(${r.buy.length} long / ${r.sell.length} short, vwap=${r.source}) -> ${path.basename(outPath)}`);
}

run();
