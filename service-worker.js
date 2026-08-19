const CACHE_NAME = 'finance-tracker-v1';
const urlsToCache = [
  '/'
];

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
