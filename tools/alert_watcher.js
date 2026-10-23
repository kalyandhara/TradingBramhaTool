/*!
 * alert_watcher.js — live indicator/pattern alert engine (channel-independent core).
 *
 * Polls the running chart_server (/api/ohlcv) for a watchlist, runs the REAL JS
 * indicator engines headless in Node (the same volume_profile.js +
 * session_volume_profile.js the chart uses — no reimplementation drift), detects
 * *state transitions* in the signal ("indicator-wise pattern buildup"), dedupes
 * against a persisted state file, and DELIVERS the triggered alert.
 *
 * Phase 1 delivery is dry-run only: it logs to the console and appends a JSONL
 * feed. Out-of-band delivery (email / Telegram) is deliberately stubbed — sending
 * messages on the user's behalf needs an explicit channel choice, so those
 * adapters refuse until wired.
 *
 * Usage:
 *   node alert_watcher.js --once                 # single pass, then exit
 *   node alert_watcher.js                        # poll loop (poll_seconds)
 *   node alert_watcher.js --config myalerts.json
 *
 * Config: alert_config.json (see the bundled default).
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

global.window = global;
require(path.join(__dirname, 'volume_profile.js'));
require(path.join(__dirname, 'session_volume_profile.js'));

const CONF_RANK = { low: 0, medium: 1, high: 2 };

function loadJSON(p, fallback) {
  try { return JSON.parse(fs.readFileSync(p, 'utf-8')); }
  catch { return fallback; }
}

function nowISO() { return new Date().toISOString(); }

async function fetchBars(server, symbol, tf, bars) {
  const url = `${server}/api/ohlcv?symbol=${encodeURIComponent(symbol)}`
    + `&timeframe=${encodeURIComponent(tf)}&bars=${bars}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  return d.bars || [];
}

// ── Signal extraction: run the real engine, return a compact state ─────────────
function svpState(bars, tf) {
  const r = window.SVP.analyze(bars, tf);
  if (!r || !r.signal) return null;
  const s = r.signal;
  return {
    dir: s.dir, kind: s.kind || '', conf: s.confidence || 'low',
    score: s.score, agreement: s.agreement,
    target: s.target, invalidation: s.invalidation,
    factors: (s.factors || []).filter(f => f.dir).map(f => (f.dir > 0 ? '+' : '-') + f.name),
  };
}

// ── Rule evaluation: fire only on a genuine transition ─────────────────────────
function evalRules(rules, prev, cur, sym, tf) {
  const fired = [];
  const confOK = (min) => CONF_RANK[cur.conf] >= (CONF_RANK[min] ?? 0);

  // First-ever sight of a symbol (no persisted prev) seeds the baseline
  // silently — a transition alerter must not fire just because state was empty.
  if (!prev) return fired;

  for (const rule of rules) {
    if (rule.type !== 'svp_signal') continue;          // Phase 1: SVP only

    if (rule.on === 'dir_change') {
      const dirs = rule.dirs || ['BUY', 'SELL'];
      const changed = prev.dir !== cur.dir;
      if (changed && dirs.includes(cur.dir) && confOK(rule.min_conf || 'low')) {
        fired.push({
          rule: rule.id, kind: cur.kind || 'signal',
          headline: `${sym} ${tf}: SVP → ${cur.dir}`
            + (cur.kind ? ` (${cur.kind})` : '') + ` · ${cur.conf} conf`,
        });
      }
    }

    if (rule.on === 'kind') {
      const want = rule.kind;                            // e.g. "trap-reversal"
      const isNew = cur.kind === want
        && (prev.kind !== want || prev.dir !== cur.dir);
      if (isNew && cur.dir !== 'NEUTRAL' && confOK(rule.min_conf || 'low')) {
        fired.push({
          rule: rule.id, kind: want,
          headline: `${sym} ${tf}: SVP ${want} ${cur.dir} · ${cur.conf} conf`,
        });
      }
    }
  }
  return fired;
}

// ── Delivery ───────────────────────────────────────────────────────────────────
// `log` fires per alert (console + JSONL feed). `email` is BATCHED once per pass
// (see emailBatch) so a busy pass sends one digest, not a flood. `telegram`
// remains a stub until a channel is chosen.
function deliver(alert, channels, feedPath) {
  const line = `[${alert.ts}] 🔔 ${alert.headline}`;
  if (channels.includes('log') || channels.length === 0) {
    console.log(line);
    if (alert.detail) console.log(`            ${alert.detail}`);
    try { fs.appendFileSync(feedPath, JSON.stringify(alert) + '\n', 'utf-8'); } catch {}
  }
}

// One batched email per pass, via the Python bridge that reuses the daily-digest
// Gmail-SMTP credentials. Alert text goes on STDIN (never in argv).
function emailBatch(alerts, cfg) {
  if (!alerts.length) return;
  const emailCfg = cfg.email || {};
  const py = emailCfg.python || process.env.TB_PYTHON || 'python';
  const script = path.join(__dirname, 'alert_email_send.py');
  // Prices to 2 decimals: the engine's raw floats (2400.5990658333335) read as noise.
  const px = v => (typeof v === 'number' && Number.isFinite(v)) ? v.toFixed(2) : '—';
  // One block per symbol|tf|direction: two rules firing on the same state (a
  // direction change AND a trap-reversal) used to print the same signal twice.
  const seen = new Set();
  const uniq = alerts.filter(a => {
    const k = `${a.symbol}|${a.tf}|${a.dir}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  const n = uniq.length;
  const subject = emailCfg.subject_prefix
    ? `${emailCfg.subject_prefix} · ${n} signal${n > 1 ? 's' : ''}`
    : `Trading Bramha Alert · ${n} signal${n > 1 ? 's' : ''}`;
  const body = uniq.map(a =>
    `${a.headline}\n  ${a.detail || ''}\n  target ${px(a.target)} · `
    + `invalidate ${px(a.invalidation)}`).join('\n\n')
    + `\n\n— Trading Bramha alert bot (${new Date().toISOString()})`;
  try {
    const args = [script, '--subject', subject];
    if (emailCfg.to) args.push('--to', emailCfg.to);
    const out = execFileSync(py, args, { input: body, encoding: 'utf-8' });
    console.log('   ✉  email:', (out || '').trim());
  } catch (e) {
    const err = (e.stderr || e.message || '').toString().trim();
    console.warn('   ✉  email failed:', err);
  }
}

// ── One evaluation pass over the whole watchlist ───────────────────────────────
async function pass(cfg, statePath, feedPath) {
  const state = loadJSON(statePath, {});
  const channels = cfg.delivery || ['log'];
  const passAlerts = [];
  let checked = 0, fired = 0, errs = 0;

  for (const w of cfg.watch) {
    const key = `${w.symbol}|${w.tf}`;
    let bars;
    try { bars = await fetchBars(cfg.server, w.symbol, w.tf, w.bars || 400); }
    catch (e) { console.warn(`  ! ${key} fetch failed: ${e.message}`); errs++; continue; }
    if (!bars.length) { errs++; continue; }

    const cur = svpState(bars, w.tf);
    if (!cur) continue;
    checked++;
    const prev = state[key] || null;

    for (const a of evalRules(cfg.rules, prev, cur, w.symbol, w.tf)) {
      const alert = {
        ts: nowISO(), symbol: w.symbol, tf: w.tf, ...a,
        dir: cur.dir, conf: cur.conf, score: cur.score,
        target: cur.target, invalidation: cur.invalidation,
        detail: cur.factors.join('  '),
      };
      deliver(alert, channels, feedPath);
      passAlerts.push(alert);
      fired++;
    }
    state[key] = { dir: cur.dir, kind: cur.kind, conf: cur.conf, ts: nowISO() };
  }

  if (channels.includes('email')) emailBatch(passAlerts, cfg);

  try { fs.writeFileSync(statePath, JSON.stringify(state, null, 1), 'utf-8'); } catch {}
  console.log(`  · checked ${checked} · fired ${fired}${errs ? ' · errors ' + errs : ''}`);
}

async function main() {
  const args = process.argv.slice(2);
  const once = args.includes('--once');
  const cfgPath = (() => { const i = args.indexOf('--config'); return i >= 0 ? args[i + 1] : path.join(__dirname, 'alert_config.json'); })();

  const cfg = loadJSON(cfgPath, null);
  if (!cfg) { console.error(`no config at ${cfgPath}`); process.exit(1); }

  const dir = path.join(__dirname, 'cache', 'alerts');
  fs.mkdirSync(dir, { recursive: true });
  const statePath = path.join(dir, 'alert_state.json');
  const feedPath = path.join(dir, 'alerts.jsonl');

  console.log(`alert_watcher · ${cfg.watch.length} symbols · rules: `
    + cfg.rules.map(r => r.id).join(', ') + ` · delivery: ${(cfg.delivery || ['log']).join(',')}`);

  if (once) { await pass(cfg, statePath, feedPath); return; }

  const every = (cfg.poll_seconds || 60) * 1000;
  console.log(`polling every ${cfg.poll_seconds || 60}s (Ctrl-C to stop)`);
  for (;;) {
    console.log(`\n${nowISO()} — pass`);
    try { await pass(cfg, statePath, feedPath); }
    catch (e) { console.error('pass error:', e.message); }
    await new Promise(res => setTimeout(res, every));
  }
}

main();
