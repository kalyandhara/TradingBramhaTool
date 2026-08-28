/* Trading Bramha — chart tool service worker (PWA shell caching).
 *
 * Deliberately conservative: it caches ONLY the static app shell (HTML + the
 * indicator JS modules + icons) so the app installs and opens instantly / offline.
 * It NEVER caches live data — anything under /api/, the websocket, and symbol
 * search always go straight to the network, so quotes are never stale. On a failed
 * navigation while offline it falls back to the cached shell.
 */
const CACHE = 'tb-charts-v1';

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

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;                 // never touch POST etc.
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;  // let cross-origin pass through
  if (isLiveData(url)) return;                       // live data → network only

  // Navigation requests: network-first, fall back to cached shell offline.
  if (req.mode === 'navigate') {
    e.respondWith((async () => {
      try { return await fetch(req); }
      catch (_) { return (await caches.match('/')) || Response.error(); }
    })());
    return;
  }

  // Static assets: cache-first, then network (and populate the cache).
  e.respondWith((async () => {
    const cached = await caches.match(req);
    if (cached) return cached;
    try {
      const res = await fetch(req);
      if (res && res.status === 200 && res.type === 'basic') {
        const cache = await caches.open(CACHE);
        cache.put(req, res.clone());
      }
      return res;
    } catch (_) {
      return cached || Response.error();
    }
  })());
});
