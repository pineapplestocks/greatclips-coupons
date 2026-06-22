const INDEX_SOURCE = 'https://raw.githubusercontent.com/pineapplestocks/greatclips-coupons/main/docs/index.html';

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  if (request.mode !== 'navigate') {
    return;
  }

  event.respondWith((async () => {
    try {
      const fresh = await fetch(`${INDEX_SOURCE}?v=${Date.now()}`, {
        cache: 'no-store',
        credentials: 'omit'
      });
      const html = await fresh.text();

      if (fresh.ok && html.includes('MINIMUM_UNLOCK_MS')) {
        return new Response(html, {
          status: 200,
          headers: {
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-store, no-cache, must-revalidate'
          }
        });
      }
    } catch (_) {}

    return fetch(request, { cache: 'reload' });
  })());
});
