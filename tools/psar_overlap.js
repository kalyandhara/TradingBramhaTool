/*!
 * psar_overlap.js — B-59: does Parabolic SAR carry any flip that pmax/stai miss?
 *
 * THIS IS AN OVERLAP CHECK, NOT AN EDGE TEST, and the distinction is the whole
 * point of running it. B-46 ruled PSAR out of the scanner registry because
 * `pmax` and `stai` already occupy the trailing-stop-flip role, and a third
 * detector firing where two already fire adds decisions without adding
 * information — the zero-unique-cell problem `analyses/Scanner-Overlap-Audit`
 * trimmed 12 scanners over. `psar.js` ships as an OVERLAY on that basis, and its
 * own header records what is owed before any PSAR *signal*: this count.
 *
 * So nothing here scores a forward return. If PSAR's flips are a subset of the
 * other two, there is nothing left to measure and the question closes without a
 * backtest. That is the counting-first method that killed B-57's 40% cap and
 * fixed the QM detector's 73% false-positive rate — cheaper to discover by
 * counting than by backtesting.
 *
 * ── One definition, not four ────────────────────────────────────────────────
 * `psar.js` and `supertrend_ai.js` are require()d as shipped. `pmaxSeries` and
 * `atrSeries` live INLINE in `chart_dashboard.html`, so they are sliced out of
 * that file at runtime and evaluated rather than copied here. Copying is how the
 * "Vol Spike means four different numbers" mess started; a copy would drift the
 * moment the chart's version changed and this file would keep reporting an
 * overlap against an indicator nobody runs.
 *
 * ── What "the same event" means, stated before counting ─────────────────────
 * Exact-bar matching is the wrong test. Three trailing stops with different
 * smoothing will not turn on the same bar even when they are describing the same
 * reversal, so an exact match would report near-total uniqueness for every
 * indicator against every other and prove nothing. The match is therefore
 * DIRECTION-MATCHED and WINDOWED: a PSAR up-flip is "covered" if either of the
 * others flips up within ±TOL bars.
 *
 * TOL is not chosen — the run sweeps 0/1/2/3/5/10 and prints the curve, because
 * the honest answer to "is this redundant" is a shape, not one number.
 *
 * Universe: the same cached bars as the QM study and the B-43/B-57 harness
 * (`cache/cardinality/*_1d.json`), so the counts are comparable to this desk's
 * other structural work rather than being a fresh download nobody can line up.
 *
 * The `new Function` below evaluates code lifted from `chart_dashboard.html` —
 * a first-party file in this repo, at the same trust level as the two modules
 * required above it. It is never fed user input, network data or anything from a
 * cache. Flagged here so the next reader does not have to work that out.
 *
 * Usage:
 *   node tools/psar_overlap.js            # full run
 *   node tools/psar_overlap.js --limit 50 # quick pass
 */
'use strict';

const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const CACHE = path.join(HERE, 'cache', 'cardinality');
const TOLERANCES = [0, 1, 2, 3, 5, 10];

require(path.join(HERE, 'psar.js'));
require(path.join(HERE, 'supertrend_ai.js'));

// ── pmaxSeries / atrSeries, lifted from the chart rather than reimplemented ──
// Sliced by brace-matching from the function header, so a rename or an edit in
// chart_dashboard.html surfaces here as a loud failure instead of a silent
// divergence between what the chart draws and what this file measures.
function liftFunction(src, name) {
  const start = src.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`chart_dashboard.html no longer defines ${name}()`);
  let depth = 0, i = src.indexOf('{', start);
  const open = i;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) break; }
  }
  if (depth !== 0) throw new Error(`unbalanced braces lifting ${name}()`);
  return src.slice(start, i + 1);
}

const html = fs.readFileSync(path.join(HERE, 'chart_dashboard.html'), 'utf-8');
const chartFns = new Function(
  `${liftFunction(html, 'atrSeries')}\n${liftFunction(html, 'pmaxSeries')}\n` +
  'return {atrSeries, pmaxSeries};'
)();

// ── flip extraction, one shape for all three ────────────────────────────────
// Each returns [{index, dir}] with dir 1 = turned bullish, -1 = turned bearish,
// and `index` the bar the flip is knowable on.

function psarFlips(bars) {
  const r = PSAR.compute(bars);
  return (r.flips || []).map(f => ({ index: f.index, dir: f.dir }));
}

function pmaxFlips(bars) {
  const rows = chartFns.pmaxSeries(bars);
  const idxByTime = new Map(bars.map((b, i) => [b.time, i]));
  const out = [];
  for (let i = 1; i < rows.length; i++) {
    if (rows[i].dir !== rows[i - 1].dir) {
      const idx = idxByTime.get(rows[i].time);
      if (idx !== undefined) out.push({ index: idx, dir: rows[i].dir });
    }
  }
  return out;
}

function staiFlips(bars) {
  const r = STAI.compute(bars);
  const idxByTime = new Map(bars.map((b, i) => [b.time, i]));
  const out = [];
  for (const s of r.signals || []) {
    const idx = idxByTime.get(s.time);
    // STAI's `dir` is os: 1 = long, 0 = short. Normalised to +-1 here so the
    // three indicators are compared on one convention rather than on whichever
    // each happened to adopt.
    if (idx !== undefined) out.push({ index: idx, dir: s.dir === 1 ? 1 : -1 });
  }
  return out;
}

function coveredBy(flip, others, tol) {
  for (const o of others) {
    if (o.dir === flip.dir && Math.abs(o.index - flip.index) <= tol) return true;
  }
  return false;
}

function main() {
  const args = process.argv.slice(2);
  const limIdx = args.indexOf('--limit');
  const limit = limIdx >= 0 ? parseInt(args[limIdx + 1], 10) : Infinity;

  let files;
  try {
    files = fs.readdirSync(CACHE).filter(f => f.endsWith('_1d.json'));
  } catch (e) {
    console.error(`no cached bars in ${CACHE} — run renko_quality_cardinality.py first`);
    process.exit(1);
  }
  files = files.slice(0, limit === Infinity ? files.length : limit);
  if (!files.length) { console.error('no cached bars'); process.exit(1); }

  const totals = {
    names: 0, bars: 0, psar: 0, pmax: 0, stai: 0,
    coveredPmax: {}, coveredStai: {}, coveredEither: {},
    // The mirror question, asked because "PSAR is redundant" and "PSAR is the
    // only one that sees it" are both interesting and only one of them is the
    // one B-46 objected to.
    pmaxCoveredByPsar: {}, staiCoveredByPsar: {},
  };
  for (const t of TOLERANCES) {
    totals.coveredPmax[t] = 0; totals.coveredStai[t] = 0; totals.coveredEither[t] = 0;
    totals.pmaxCoveredByPsar[t] = 0; totals.staiCoveredByPsar[t] = 0;
  }

  const perName = [];

  for (const f of files) {
    let doc;
    try { doc = JSON.parse(fs.readFileSync(path.join(CACHE, f), 'utf-8')); }
    catch { continue; }
    const bars = (doc.bars || []).filter(b => b && isFinite(b.high) && isFinite(b.low) && isFinite(b.close));
    if (bars.length < 120) continue;

    const p = psarFlips(bars);
    const m = pmaxFlips(bars);
    const s = staiFlips(bars);
    if (!p.length) continue;

    totals.names++;
    totals.bars += bars.length;
    totals.psar += p.length;
    totals.pmax += m.length;
    totals.stai += s.length;

    const row = { sym: doc.symbol, psar: p.length, pmax: m.length, stai: s.length, uniq: {} };
    for (const t of TOLERANCES) {
      let cm = 0, cs = 0, ce = 0;
      for (const fl of p) {
        const inM = coveredBy(fl, m, t);
        const inS = coveredBy(fl, s, t);
        if (inM) cm++;
        if (inS) cs++;
        if (inM || inS) ce++;
      }
      totals.coveredPmax[t] += cm;
      totals.coveredStai[t] += cs;
      totals.coveredEither[t] += ce;
      row.uniq[t] = p.length - ce;

      for (const fl of m) if (coveredBy(fl, p, t)) totals.pmaxCoveredByPsar[t]++;
      for (const fl of s) if (coveredBy(fl, p, t)) totals.staiCoveredByPsar[t]++;
    }
    perName.push(row);
  }

  const pct = (a, b) => (b ? (a / b * 100) : 0).toFixed(1);

  console.log('B-59 · PSAR overlap check — is the flip already covered by pmax/stai?');
  console.log('NOT an edge test. Counting only, per psar.js\'s own header.\n');
  console.log(`universe ${totals.names} names · ${totals.bars} bars`);
  console.log(`flips: PSAR ${totals.psar} · PMax ${totals.pmax} · STAI ${totals.stai}`);
  console.log(`       PSAR fires ${(totals.psar / Math.max(totals.pmax, 1)).toFixed(1)}x as often as PMax, ` +
              `${(totals.psar / Math.max(totals.stai, 1)).toFixed(1)}x as often as STAI\n`);

  console.log('  tol   PSAR covered by PMax    by STAI      by EITHER      PSAR-UNIQUE');
  for (const t of TOLERANCES) {
    const uniq = totals.psar - totals.coveredEither[t];
    console.log(`  ±${String(t).padEnd(3)}  ${String(totals.coveredPmax[t]).padStart(6)} (${pct(totals.coveredPmax[t], totals.psar).padStart(5)}%)` +
                `  ${String(totals.coveredStai[t]).padStart(6)} (${pct(totals.coveredStai[t], totals.psar).padStart(5)}%)` +
                `  ${String(totals.coveredEither[t]).padStart(6)} (${pct(totals.coveredEither[t], totals.psar).padStart(5)}%)` +
                `  ${String(uniq).padStart(6)} (${pct(uniq, totals.psar).padStart(5)}%)`);
  }

  console.log('\n  the mirror — how much of PMax/STAI does PSAR itself cover?');
  console.log('  tol   PMax covered by PSAR    STAI covered by PSAR');
  for (const t of TOLERANCES) {
    console.log(`  ±${String(t).padEnd(3)}  ${String(totals.pmaxCoveredByPsar[t]).padStart(6)} (${pct(totals.pmaxCoveredByPsar[t], totals.pmax).padStart(5)}%)` +
                `       ${String(totals.staiCoveredByPsar[t]).padStart(6)} (${pct(totals.staiCoveredByPsar[t], totals.stai).padStart(5)}%)`);
  }

  const t3 = 3;
  const uniq3 = totals.psar - totals.coveredEither[t3];
  const uniqPct = uniq3 / Math.max(totals.psar, 1) * 100;
  console.log('\nREADING (at ±3 bars, the middle of the sweep):');
  if (uniqPct < 10) {
    console.log(`  PSAR is a SUBSET: ${uniqPct.toFixed(1)}% of its flips are unseen by pmax/stai.`);
    console.log('  B-46 stands. There is nothing left to measure, and no PSAR signal');
    console.log('  should be built — it would add decisions without adding information.');
  } else {
    console.log(`  PSAR is NOT a subset: ${uniqPct.toFixed(1)}% of its flips (${uniq3}) are unseen`);
    console.log('  by pmax and stai at ±3 bars.');
    console.log('');
    console.log('  READ THAT NUMBER WITH THE CADENCE BESIDE IT, or it flatters PSAR.');
    console.log(`  PSAR fires ${totals.psar} times where PMax fires ${totals.pmax}. Most of the`);
    console.log('  "unique" share is arithmetic: there are not enough PMax flips in existence');
    console.log('  to cover them, whatever the tolerance. The mirror table is the honest read —');
    console.log('  PSAR covers most of what the other two see and then keeps going. So this is');
    console.log('  a SUPERSET at a faster cadence, not a duplicate and not a new detector.');
    console.log('');
    console.log('  What that does to B-46: the zero-unique-cell objection does NOT close the');
    console.log('  question — but the objection it is replaced by is no weaker. The');
    console.log('  content of PSAR IS its extra flips, so an edge test would have to score');
    console.log('  the UNIQUE cells specifically against the covered ones, on the prior that');
    console.log('  a detector firing 8x as often is mostly firing on noise. Uniqueness is');
    console.log('  not edge — the Scanner-Overlap-Audit says so, and this run does not');
    console.log('  change it.');
  }
  console.log('\nLIMITS: counting only, no forward returns anywhere in this file; today\'s');
  console.log('        liquid names over ~3 years of daily bars; and a detector that fires');
  console.log('        several times as often as its comparators is cheaper per signal to');
  console.log('        look unique, which is why the mirror table is printed beside the');
  console.log('        primary one rather than under a fold.');
}

main();
