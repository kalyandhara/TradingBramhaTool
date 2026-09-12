/**
 * pmax_bands_emit.js — B-74: emit the PMax BAND per bar, not just its flips.
 *
 * B-65 scored the PMax SIGNAL and only needed flip indices, so `psar_overlap.js
 * --emit` writes `[index, dir]` pairs. B-74 scores the PLAN the chart draws, and
 * the plan is defined by the band's VALUE: the initial stop is the band on the
 * flip bar (so it sets R), and the "Trail SL" line the card shows is the band as
 * it ratchets. Neither is recoverable from flip indices.
 *
 * The series is NOT recomputed here. `chart_lift.js` slices `pmaxSeries` out of
 * chart_dashboard.html, so this emits exactly the numbers the chart draws — the
 * same discipline B-65 used, and the reason the two studies can be compared.
 *
 * Output: { SYM: { n, start, band: [...], dir: [...] } }
 *   `start` is the first bar pmaxSeries emits (it skips ATR/EMA warm-up), and
 *   band/dir are index-aligned from there, so bar i reads band[i - start].
 *
 * CLI:
 *   node tools/pmax_bands_emit.js tools/cache/pmax_bands.json
 *   node tools/pmax_bands_emit.js out.json --limit 5      # smoke test
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { chartFns, CACHE } = require('./chart_lift.js');

function main() {
  const args = process.argv.slice(2);
  const out = args[0];
  if (!out) { console.error('usage: pmax_bands_emit.js <out.json> [--limit N]'); process.exit(1); }
  const li = args.indexOf('--limit');
  const limit = li >= 0 ? parseInt(args[li + 1], 10) : Infinity;

  let files;
  try {
    files = fs.readdirSync(CACHE).filter(f => f.endsWith('_1d.json'));
  } catch (e) {
    console.error(`no cached bars in ${CACHE} — run renko_quality_cardinality.py first`);
    process.exit(1);
  }
  files = files.slice(0, limit === Infinity ? files.length : limit);

  const emitted = {};
  let skipped = 0;
  for (const f of files) {
    let doc;
    try { doc = JSON.parse(fs.readFileSync(path.join(CACHE, f), 'utf-8')); }
    catch { skipped++; continue; }
    // Same finiteness filter and 120-bar floor psar_overlap.js applies, so the
    // two studies see the same panel rather than two different subsets of it.
    const bars = (doc.bars || []).filter(b => b && isFinite(b.high) && isFinite(b.low) && isFinite(b.close));
    if (bars.length < 120) { skipped++; continue; }

    const rows = chartFns.pmaxSeries(bars);
    if (!rows.length) { skipped++; continue; }
    const idxByTime = new Map(bars.map((b, i) => [b.time, i]));

    const first = idxByTime.get(rows[0].time);
    if (first === undefined) { skipped++; continue; }
    const band = new Array(rows.length).fill(null);
    const dir = new Array(rows.length).fill(0);
    let contiguous = true;
    for (let k = 0; k < rows.length; k++) {
      const idx = idxByTime.get(rows[k].time);
      // pmaxSeries emits one row per bar from warm-up on; if that ever stops
      // being true the index alignment below is silently wrong, so check rather
      // than assume.
      if (idx !== first + k) { contiguous = false; break; }
      band[k] = rows[k].pmax;
      dir[k] = rows[k].dir;
    }
    if (!contiguous) {
      console.error(`  ${doc.symbol}: pmaxSeries rows are not bar-contiguous — skipped`);
      skipped++;
      continue;
    }
    emitted[doc.symbol] = { n: bars.length, start: first, band, dir };
  }

  fs.writeFileSync(out, JSON.stringify(emitted), 'utf-8');
  console.error(`pmax bands for ${Object.keys(emitted).length} names (${skipped} skipped) -> ${out}`);
}

main();
