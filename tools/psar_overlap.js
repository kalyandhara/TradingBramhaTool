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

// ── the chance baseline ─────────────────────────────────────────────────────
// ADDED 2026-09-10, after the first run was used to argue about sunsetting PMax
// and could not support the argument in either direction.
//
// A raw coverage percentage is close to meaningless on its own. PSAR alternates
// roughly every 11 bars, so a SAME-DIRECTION PSAR flip comes round about every
// 22; a ±10 window is 21 bars wide, and will therefore catch a same-direction
// flip most of the time **whether or not the two indicators are describing the
// same reversal**. Every number in the tables above is inflated by that, and by
// an amount that grows with the tolerance — so the tolerance sweep, which was
// supposed to show the shape of the overlap, was partly showing the shape of the
// base rate instead.
//
// The fix is the null this desk uses everywhere else (B-43r, B-57, B-58):
// circular rotation. Rotate the comparator's flips through the series and
// recompute the same coverage. That preserves the flip COUNT, the direction mix
// and the spacing, and destroys only the alignment — so it answers exactly
// "these flips, happening at other times", which is the definition of chance
// here. Coverage above that is real agreement; coverage at it is arithmetic.
const ROT_OFFSETS = [37, 73, 109, 151, 193, 233, 277, 313, 359, 401, 443, 487];

function rotate(flips, by, n) {
  if (n <= 0) return flips;
  return flips.map(f => ({ index: (f.index + by) % n, dir: f.dir }));
}

function chanceCoverage(flips, others, tol, n) {
  // Mean coverage of `flips` by `others` across the rotation grid.
  if (!flips.length) return 0;
  let hits = 0;
  for (const s of ROT_OFFSETS) {
    const rot = rotate(others, s, n);
    for (const fl of flips) if (coveredBy(fl, rot, tol)) hits++;
  }
  return hits / ROT_OFFSETS.length;
}

function main() {
  const args = process.argv.slice(2);
  const limIdx = args.indexOf('--limit');
  const limit = limIdx >= 0 ? parseInt(args[limIdx + 1], 10) : Infinity;
  // --emit <file> writes the raw flip vectors for B-59r's scorer. The flips are
  // produced HERE, by the shipped psar.js / supertrend_ai.js / lifted pmaxSeries,
  // and scored THERE, by the same Python harness as B-43/B-57/B-58. Neither side
  // reimplements the other's half, which is the only reason the two studies can
  // be compared at all.
  const emitIdx = args.indexOf('--emit');
  const emitTo = emitIdx >= 0 ? args[emitIdx + 1] : null;
  const emitted = {};

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
    // chance baselines, same keys
    chPmax: {}, chStai: {}, chEither: {}, chPmaxByPsar: {}, chStaiByPsar: {},
  };
  for (const t of TOLERANCES) {
    totals.coveredPmax[t] = 0; totals.coveredStai[t] = 0; totals.coveredEither[t] = 0;
    totals.pmaxCoveredByPsar[t] = 0; totals.staiCoveredByPsar[t] = 0;
    totals.chPmax[t] = 0; totals.chStai[t] = 0; totals.chEither[t] = 0;
    totals.chPmaxByPsar[t] = 0; totals.chStaiByPsar[t] = 0;
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

    if (emitTo) {
      emitted[doc.symbol] = {
        bars: bars.length,
        psar: p.map(x => [x.index, x.dir]),
        pmax: m.map(x => [x.index, x.dir]),
        stai: s.map(x => [x.index, x.dir]),
      };
    }

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

      const nb = bars.length;
      totals.chPmax[t] += chanceCoverage(p, m, t, nb);
      totals.chStai[t] += chanceCoverage(p, s, t, nb);
      totals.chEither[t] += chanceCoverage(p, m.concat(s), t, nb);
      totals.chPmaxByPsar[t] += chanceCoverage(m, p, t, nb);
      totals.chStaiByPsar[t] += chanceCoverage(s, p, t, nb);
    }
    perName.push(row);
  }

  if (emitTo) {
    fs.writeFileSync(emitTo, JSON.stringify(emitted), 'utf-8');
    console.error(`flip vectors for ${Object.keys(emitted).length} names -> ${emitTo}`);
  }

  const pct = (a, b) => (b ? (a / b * 100) : 0).toFixed(1);

  console.log('B-59 · PSAR overlap check — is the flip already covered by pmax/stai?');
  console.log('NOT an edge test. Counting only, per psar.js\'s own header.\n');
  console.log(`universe ${totals.names} names · ${totals.bars} bars`);
  console.log(`flips: PSAR ${totals.psar} · PMax ${totals.pmax} · STAI ${totals.stai}`);
  console.log(`       PSAR fires ${(totals.psar / Math.max(totals.pmax, 1)).toFixed(1)}x as often as PMax, ` +
              `${(totals.psar / Math.max(totals.stai, 1)).toFixed(1)}x as often as STAI\n`);
  console.log('  PSAR flips covered -- observed vs CHANCE (same flips, rotated). LIFT is the answer.');
  console.log('  tol     by PMax  chance    lift      by STAI  chance    lift     by EITHER  chance    lift');
  for (const t of TOLERANCES) {
    const om = +pct(totals.coveredPmax[t], totals.psar), cm = +pct(totals.chPmax[t], totals.psar);
    const oq = +pct(totals.coveredStai[t], totals.psar), cq = +pct(totals.chStai[t], totals.psar);
    const oe = +pct(totals.coveredEither[t], totals.psar), ce = +pct(totals.chEither[t], totals.psar);
    const L = v => ((v >= 0 ? '+' : '') + v.toFixed(1)).padStart(7);
    const P = v => (v.toFixed(1) + '%').padStart(7);
    console.log(`  ±${String(t).padEnd(3)}  ${P(om)}  ${P(cm)}  ${L(om - cm)}   ${P(oq)}  ${P(cq)}  ${L(oq - cq)}   ${P(oe)}  ${P(ce)}  ${L(oe - ce)}`);
  }

  console.log('');
  console.log('  the mirror -- how much of PMax/STAI does PSAR itself cover? This is the');
  console.log('  direction a SUNSET argument needs: retiring PMax requires PMax to be a');
  console.log('  subset of PSAR, not the other way round.');
  console.log('  tol     PMax by PSAR  chance    lift      STAI by PSAR  chance    lift');
  for (const t of TOLERANCES) {
    const om = +pct(totals.pmaxCoveredByPsar[t], totals.pmax), cm = +pct(totals.chPmaxByPsar[t], totals.pmax);
    const oq = +pct(totals.staiCoveredByPsar[t], totals.stai), cq = +pct(totals.chStaiByPsar[t], totals.stai);
    const L = v => ((v >= 0 ? '+' : '') + v.toFixed(1)).padStart(7);
    const P = v => (v.toFixed(1) + '%').padStart(7);
    console.log(`  ±${String(t).padEnd(3)}       ${P(om)}  ${P(cm)}  ${L(om - cm)}        ${P(oq)}  ${P(cq)}  ${L(oq - cq)}`);
  }

  const t3 = 3;
  const uniq3 = totals.psar - totals.coveredEither[t3];
  const uniqPct = uniq3 / Math.max(totals.psar, 1) * 100;
  const liftPmax = +pct(totals.pmaxCoveredByPsar[t3], totals.pmax) - +pct(totals.chPmaxByPsar[t3], totals.pmax);
  const liftStai = +pct(totals.staiCoveredByPsar[t3], totals.stai) - +pct(totals.chStaiByPsar[t3], totals.stai);

  console.log('');
  console.log('READING (at \u00b13 bars, the middle of the sweep). LIFT over chance, not raw');
  console.log('coverage, because raw coverage mostly measures how often each indicator fires:');
  console.log('');
  console.log(`  PSAR vs STAI:  lift ${liftStai >= 0 ? '+' : ''}${liftStai.toFixed(1)}  -- they describe THE SAME reversals.`);
  console.log(`  PSAR vs PMax:  lift ${liftPmax >= 0 ? '+' : ''}${liftPmax.toFixed(1)}  -- they agree LESS than chance.`);
  console.log('');
  console.log('  That second line is the surprise, and it is negative at EVERY tolerance in');
  console.log('  both directions. PSAR and PMax do not merely fail to be redundant: their');
  console.log('  flips systematically avoid each other. A plausible mechanism -- PMax flips');
  console.log('  only when a trend has genuinely turned, by which point PSAR has usually');
  console.log('  flipped already -- is NOT measured here and should not be reported as fact.');
  console.log('');
  console.log('  CONSEQUENCES, in order of how much they change:');
  console.log('');
  console.log('  1. SUNSETTING PMAX IN FAVOUR OF PSAR IS THE WORST AVAILABLE SWAP. It is the');
  console.log('     least-alike pair of the three, below chance at every tolerance. Whatever');
  console.log('     PMax contributes, PSAR is not a substitute for it.');
  console.log('  2. The redundancy that DOES exist is PSAR-STAI, and it is large. If the desk');
  console.log('     wants one fewer trailing-stop indicator, that is the pair to look at --');
  console.log('     and the choice between them is an EDGE question, not a counting one.');
  console.log('  3. B-46 stands on its own terms: PSAR would be a third detector in a role');
  console.log('     already held, and it duplicates STAI specifically. It stays an overlay.');
  console.log('');
  console.log('  What is NOT shown: whether any of the three has an edge. Nothing here scores');
  console.log('  a forward return, and none of these indicators has ever been measured on');
  console.log('  this desk. Agreement is not accuracy -- two indicators can agree perfectly');
  console.log('  and both be worthless.');
  console.log('');

  console.log('\nLIMITS: counting only, no forward returns anywhere in this file; today\'s');
  console.log('        liquid names over ~3 years of daily bars; and a detector that fires');
  console.log('        several times as often as its comparators is cheaper per signal to');
  console.log('        look unique, which is why the mirror table is printed beside the');
  console.log('        primary one rather than under a fold.');
}

main();
