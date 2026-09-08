/* Trading Bramha — chart tool service worker (PWA shell caching).
 *
 * Deliberately conservative: it caches ONLY the static app shell (HTML + the
 * indicator JS modules + icons) so the app installs and opens instantly / offline.
 * It NEVER caches live data — anything under /api/, the websocket, and symbol
 * search always go straight to the network, so quotes are never stale. On a failed
 * navigation while offline it falls back to the cached shell.
 *
 * ── Why code is network-first (regression fixed 2026-08-29) ──────────────────
 * The first version cached EVERY static asset cache-first under a fixed cache
 * name. HTML was network-first, so dashboard edits shipped — but the indicator
 * modules never did. A fix to `session_volume_profile.js` was verified working in
 * a fresh browser and still looked broken to an installed client, because that
 * client kept serving the pre-fix module out of `tb-charts-v1` forever. The bug
 * was invisible from the developer's side and permanent from the user's.
 *
 * So the strategy now splits by what the asset IS:
 *
 *   code (.js, .webmanifest, navigations) → NETWORK-FIRST, cache as fallback.
 *       This app is served over localhost / a private Tailscale mesh, so the
 *       network is essentially always there; the cache exists for genuine offline
 *       use, not to pin a build. A shipped fix must never require the user to
 *       know about service workers.
 *
 *   immutable binaries (icons/png) → CACHE-FIRST.
 *       They are content-stable; re-fetching them buys nothing.
 *
 * CACHE_VERSION must still be bumped when the SHELL list itself changes, but a
 * forgotten bump can no longer freeze a code fix — at worst it costs one extra
 * network round trip.
 */
const CACHE_VERSION = 'v2';
const CACHE = 'tb-charts-' + CACHE_VERSION;

// Static shell assets. The indicator JS files are served as individual routes by
// chart_server; list the ones that exist. Missing entries fail soft (addAll is
// wrapped so one 404 doesn't abort the whole install).
const SHELL = [
  '/',
  '/manifest.webmanifest',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-maskable-512.png',
  '/elliott_wave.js',
  '/volume_profile.js',
  '/session_volume_profile.js',
  '/fvg.js',
  '/fibonacci.js',
  '/gann.js',
  '/hm_indicator.js',
  '/supertrend_ai.js',
  '/percent_r_trend_exhaustion.js',
  '/adx_di.js',
  '/obv_divergence.js',
  '/rsi_divergence.js',
  '/evwma_vwap_macd.js',
  '/psar.js',
  '/renko.js',
];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // Add each asset independently so a single 404 doesn't fail the install.
    await Promise.all(SHELL.map(async (url) => {
      try { await cache.add(new Request(url, { cache: 'reload' })); } catch (_) {}
    }));
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    // Drop old caches on version bump.
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

function isLiveData(url) {
  return url.pathname.startsWith('/api/')
      || url.pathname.startsWith('/ws')
      || url.pathname.includes('/search');
}

// Content-stable assets worth pinning. Everything else that reaches the cache
// layer is code, and code must be allowed to change.
function isImmutableAsset(url) {
  return /\.(png|ico|svg|woff2?)$/i.test(url.pathname);
}

async function cacheFirst(req) {
  const cached = await caches.match(req);
  if (cached) return cached;
  const res = await fetch(req);
  if (res && res.status === 200 && res.type === 'basic') {
    (await caches.open(CACHE)).put(req, res.clone());
  }
  return res;
}

async function networkFirst(req) {
  try {
    const res = await fetch(req);
    if (res && res.status === 200 && res.type === 'basic') {
      (await caches.open(CACHE)).put(req, res.clone());
    }
    return res;
  } catch (_) {
    const cached = await caches.match(req);
    return cached || Response.error();
  }
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;                 // never touch POST etc.
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;  // let cross-origin pass through
  if (isLiveData(url)) return;                       // live data → network only

  // Navigation requests: network-first, fall back to the cached shell offline.
  if (req.mode === 'navigate') {
    e.respondWith((async () => {
      try { return await fetch(req); }
      catch (_) { return (await caches.match('/')) || Response.error(); }
    })());
    return;
  }

  e.respondWith(isImmutableAsset(url) ? cacheFirst(req) : networkFirst(req));
});
