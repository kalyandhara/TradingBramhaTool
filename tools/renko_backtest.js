/*!
 * renko_backtest.js — emit the REAL Renko engine's brick flips as CSV.
 *
 * Phase 1 of the B-43 measurement, same split as the SVP and EVWMA backtests: the signal
 * side imports the ACTUAL shipped engine (renko.js) so the flips scored downstream are
 * the flips the chart draws, and the Python side never re-implements the rule.
 *
 * ── The trap this file exists to avoid ───────────────────────────────────────
 * A Renko backtest run on the BRICK series is the classic way this chart type
 * manufactures a fake equity curve: bricks have no fillable timestamp, several can print
 * from one bar, and the newest one is provisional. So what is emitted here is not a brick
 * index but the **underlying bar index that completed the flip** — `index` — which the
 * scorer fills at that bar's NEXT open, exactly like every other signal in this repo.
 *
 * Usage:
 *   node renko_backtest.js cache/backtest/RELIANCE.NS_1d.json [out.csv]
 *
 * CSV columns: time,index,dir,close,brick,bricks_in_prior
 *   dir: 1 = flip up (long), -1 = flip down (short/exit)
 */
'use strict';

const fs = require('fs');
const path = require('path');

global.window = global;
require(path.join(__dirname, 'renko.js'));

function run() {
  const args = process.argv.slice(2);
  const inPath = args[0];
  if (!inPath) {
    console.error('usage: node renko_backtest.js <bars.json> [out.csv]');
    process.exit(1);
  }
  const doc = JSON.parse(fs.readFileSync(inPath, 'utf-8'));
  const bars = doc.bars;
  if (!bars || bars.length < 120) { console.error('too few bars: ' + inPath); process.exit(1); }

  const r = RENKO.compute(bars);
  const safe = String(doc.symbol).replace(/[\^=-]/g, '_');
  const outPath = args[1] || path.join(path.dirname(inPath), `${safe}_${doc.tf}_renko.csv`);

  const byIndex = new Map(r.bricks.map(b => [b.index, b.brick]));
  const lines = ['time,index,dir,close,brick,bricks_in_prior'];
  r.flips.forEach(f => {
    lines.push([f.time, f.index, f.dir, bars[f.index].close,
                (byIndex.get(f.index) || 0).toFixed(4), f.bricksInPrior].join(','));
  });
  fs.writeFileSync(outPath, lines.join('\n') + '\n', 'utf-8');
  console.error(`${doc.symbol} ${doc.tf}: ${bars.length} bars, ${r.bricks.length} bricks, `
                + `${r.flips.length} flips across ${r.epochs.length} brick epochs `
                + `-> ${path.basename(outPath)}`);
}

run();
