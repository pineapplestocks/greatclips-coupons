const INDEX_SOURCE = 'https://raw.githubusercontent.com/pineapplestocks/greatclips-coupons/main/docs/index.html';
const SW_VERSION = 'remove-6bWu89Y-v2';

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    await self.clients.claim();
    const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of clients) {
      try {
        const url = new URL(client.url);
        if (url.origin === self.location.origin && !url.searchParams.has('sw-refresh')) {
          url.searchParams.set('sw-refresh', SW_VERSION);
          client.navigate(url.href);
        }
      } catch (_) {}
    }
  })());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  if (request.mode !== 'navigate') {
    return;
  }

  event.respondWith((async () => {
    try {
      const fresh = await fetch(`${INDEX_SOURCE}?v=${SW_VERSION}-${Date.now()}`, {
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
