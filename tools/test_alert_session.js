// Tests for alert_watcher's IST session gate.  Run: node --test tools/test_alert_session.js
//
// Pinned: NSE symbols are evaluated only Mon-Fri 09:15-15:45 IST, whatever the
// machine's own time zone or US daylight saving says; crypto is never gated.
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { marketOf, sessionOpen } = require('./alert_watcher.js');

test('market is inferred from the symbol, and config can override it', () => {
  assert.strictEqual(marketOf({ symbol: 'RELIANCE.NS' }), 'NSE');
  assert.strictEqual(marketOf({ symbol: '^NSEI' }), 'NSE');
  assert.strictEqual(marketOf({ symbol: '^NSEBANK' }), 'NSE');
  assert.strictEqual(marketOf({ symbol: 'BTC' }), '24X7');
  assert.strictEqual(marketOf({ symbol: 'HDFC', market: 'nse' }), 'NSE');
});

// UTC instants: IST = UTC + 5:30.
const at = s => new Date(s);

test('NSE is open inside 09:15-15:45 IST on a weekday', () => {
  assert.ok(sessionOpen('NSE', at('2026-10-29T03:45:00Z')));   // Thu 09:15 IST
  assert.ok(sessionOpen('NSE', at('2026-10-29T10:15:00Z')));   // Thu 15:45 IST
  assert.ok(!sessionOpen('NSE', at('2026-10-29T03:44:00Z')));  // 09:14 IST
  assert.ok(!sessionOpen('NSE', at('2026-10-29T10:16:00Z')));  // 15:46 IST
});

test('the old local 09:15-15:45 ET window is entirely closed for NSE', () => {
  // 09:15 EDT = 13:15 UTC = 18:45 IST
  assert.ok(!sessionOpen('NSE', at('2026-10-29T13:15:00Z')));
});

test('weekends are closed, judged by the IST day', () => {
  assert.ok(!sessionOpen('NSE', at('2026-10-31T05:00:00Z')));  // Sat 10:30 IST
  // Sun 23:45 EST = Mon 10:15 IST -> open
  assert.ok(sessionOpen('NSE', at('2026-11-02T04:45:00Z')));
});

test('the gate does not move when US clocks change on Nov 1', () => {
  assert.ok(sessionOpen('NSE', at('2026-10-30T04:00:00Z')));   // Fri, EDT
  assert.ok(sessionOpen('NSE', at('2026-11-02T04:00:00Z')));   // Mon, EST
});

test('crypto is never gated', () => {
  assert.ok(sessionOpen('24X7', at('2026-10-31T05:00:00Z')));
});
