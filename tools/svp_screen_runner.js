/*!
 * svp_screen_runner.js — batch the REAL SVP engine over a universe, emit structure.
 *
 * Screens on volume-profile STRUCTURE over the engine's retained window: where
 * price sits against the composite value area and POC, what shape each session
 * printed, and whether a trap/exhaustion run is in progress.
 *
 * NOTE ON "LAST 5 SESSIONS". The engine retains `maxSessions = 12`, not 5, and
 * the composite value area is computed across all of them — so `comp_*` here is
 * a 12-session acceptance range. The card's own prose calls it "the 5-session
 * acceptance range", which is stale relative to the default it ships with. The
 * screen reports `n_sessions` per row so the window is never in doubt, and it is
 * left at the engine's default rather than forced to 5: changing it would make
 * the screen disagree with the chart, which is the one thing reusing the engine
 * is meant to prevent.
 *
 * ── What this deliberately does NOT emit, and why ───────────────────────────
 * **The confluence score and its BUY/SELL direction.** `SVP.buildSignal`'s
 * seven-factor score was measured 2026-08-29 and came back a clean negative:
 * corr(score, 20d fwd) = -0.041, score deciles NON-MONOTONIC, BUY-high confidence
 * performing WORSE than BUY-low, stop-and-reverse median -80%, beat buy&hold 0/8.
 * Five of seven factor families are sign-inverted — cluster -0.94, va -0.71,
 * sequence -0.67, trap -0.51 (the engine's largest weight), regime -0.50 — with
 * only sweep (+0.39) and exhaustion (+0.12) pointing the right way.
 *
 * A screener's whole function is to surface its top-ranked names. Ranking by a
 * score whose highest-confidence band measures worst would systematically surface
 * what the measurement says to avoid, and would contradict the caveat already
 * shipped on the chart card: read the STRUCTURE, ignore the DIRECTION. So this
 * emits structure and no score, and the ordering is left to the caller.
 *
 * The two factors that survived are NOT promoted to a ranking either. +0.12 is
 * near zero, and picking the winners out of an in-sample attribution is the
 * overfit the SVP design pre-registered against. They are emitted as flags for a
 * future pre-registered test, not as a sort key.
 *
 * ── Why Node and not a Python port ──────────────────────────────────────────
 * It imports `volume_profile.js` + `session_volume_profile.js` directly, the same
 * way `svp_backtest_runner.js` does, so the screen sees exactly what the chart
 * draws. A Python reimplementation would be a second copy free to drift — and
 * that is not hypothetical here: on 2026-09-06 the VWAP mean-reversion JS and
 * Python disagreed because one averaged 19 bars over a divisor of 20, a bug
 * neither implementation revealed alone.
 *
 * Usage:
 *   node svp_screen_runner.js cache/backtest/*.json out.csv
 *   node svp_screen_runner.js --dir cache/backtest --out cache/svp_screen.csv
 */
'use strict';

const fs = require('fs');
const path = require('path');

global.window = global;
require(path.join(__dirname, 'volume_profile.js'));
require(path.join(__dirname, 'session_volume_profile.js'));

const COLUMNS = [
  'symbol', 'asof', 'close', 'grain', 'n_sessions',
  'comp_poc', 'comp_vah', 'comp_val',
  'va_state', 'poc_dist_pct', 'va_pos',
  'last_shape', 'shape_seq', 'trap', 'trap_dir', 'accum_dist',
  'sweep_flag', 'sweep_dir', 'exhaustion_flag', 'exhaustion_dir', 'note',
];

function loadBars(file) {
  const doc = JSON.parse(fs.readFileSync(file, 'utf8'));
  const bars = doc.bars || doc;
  if (!Array.isArray(bars) || !bars.length) return null;
  return { symbol: doc.symbol || path.basename(file).replace(/_1d\.json$/, ''), bars };
}

function pct(a, b) { return b ? ((a - b) / b) * 100 : null; }

function row(symbol, bars) {
  let res;
  try {
    res = global.SVP.analyze(bars, {});
  } catch (e) {
    return { symbol, note: `analyze failed: ${e.message}` };
  }
  const last = bars[bars.length - 1];
  const close = last.close;
  const c = res.composite;

  // Where price sits against the composite acceptance range. This is the whole
  // structural read: inside = accepted, outside = rejected or breaking out, and
  // the engine's own factor attribution says the DIRECTION you draw from that is
  // not to be trusted — so the state is reported and not interpreted.
  let vaState = 'n/a', vaPos = null, pocDist = null;
  if (c && isFinite(c.vah) && isFinite(c.val) && c.vah > c.val) {
    vaPos = (close - c.val) / (c.vah - c.val);
    vaState = close > c.vah ? 'above_va' : close < c.val ? 'below_va' : 'inside_va';
    pocDist = pct(close, c.poc);
  }

  const seq = res.sessions.map(s => s.shape).join('');
  const lastShape = res.sessions.length
    ? res.sessions[res.sessions.length - 1].shape : null;

  // The two factor families that measured POSITIVE (sweep +0.39, exhaustion
  // +0.12), emitted as flags only. Not a score, not a sort key — see the header.
  const sig = res.signal || {};
  const factors = Array.isArray(sig.factors) ? sig.factors : [];
  // Direction is kept as DATA even though it is not ranked on. Dropping it would
  // lose the one thing the attribution says these two factors get right, and the
  // page does not sort by it, so there is no reason to discard it.
  const find = (re) => factors.find(f => re.test(String(f.name || f))) || null;
  const sweep = find(/sweep/i);
  const exh = find(/exhaust/i);

  return {
    symbol,
    asof: last.time ? new Date(last.time * 1000).toISOString().slice(0, 10) : '',
    close,
    grain: res.grain || '',
    n_sessions: res.sessions.length,
    comp_poc: c ? c.poc : null,
    comp_vah: c ? c.vah : null,
    comp_val: c ? c.val : null,
    va_state: vaState,
    poc_dist_pct: pocDist === null ? null : +pocDist.toFixed(2),
    va_pos: vaPos === null ? null : +vaPos.toFixed(3),
    last_shape: lastShape,
    shape_seq: seq,
    trap: res.trap ? 1 : 0,
    trap_dir: res.trap ? (res.trap.dir || res.trap.direction || '') : '',
    accum_dist: res.ad ? (res.ad.label || res.ad.state || '') : '',
    sweep_flag: sweep ? 1 : 0,
    sweep_dir: sweep ? sweep.dir : '',
    exhaustion_flag: exh ? 1 : 0,
    exhaustion_dir: exh ? exh.dir : '',
    note: res.note || '',
  };
}

function toCsv(rows) {
  const esc = (v) => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [COLUMNS.join(',')]
    .concat(rows.map(r => COLUMNS.map(c => esc(r[c])).join(',')))
    .join('\n') + '\n';
}

function main(argv) {
  let files = [], out = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--dir') {
      const d = argv[++i];
      files = files.concat(fs.readdirSync(d)
        .filter(f => f.endsWith('.json'))
        .map(f => path.join(d, f)));
    } else if (argv[i] === '--out') {
      out = argv[++i];
    } else if (argv[i].endsWith('.csv')) {
      out = argv[i];
    } else {
      files.push(argv[i]);
    }
  }
  if (!files.length) {
    console.error('usage: node svp_screen_runner.js --dir <bars-dir> --out <csv>');
    return 1;
  }
  const rows = [];
  for (const f of files) {
    const loaded = loadBars(f);
    if (!loaded) { console.error(`  skip ${path.basename(f)} (no bars)`); continue; }
    rows.push(row(loaded.symbol, loaded.bars));
  }
  const csv = toCsv(rows);
  if (out) {
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, csv, 'utf8');
    const ok = rows.filter(r => r.n_sessions > 0).length;
    console.log(`wrote ${rows.length} rows (${ok} with sessions) -> ${out}`);
  } else {
    process.stdout.write(csv);
  }
  return 0;
}

if (require.main === module) process.exit(main(process.argv.slice(2)));
module.exports = { row, toCsv, COLUMNS };
