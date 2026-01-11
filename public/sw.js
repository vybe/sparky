// DGX Spark PWA Service Worker
const CACHE_NAME = 'dgx-spark-v3'
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/config.js',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
]

// Install - cache static assets and force activate
self.addEventListener('install', (event) => {
  console.log('SW: Installing v3...')
  // Skip waiting immediately - don't wait for old SW to stop
  self.skipWaiting()
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS)
    })
  )
})

// Activate - clean ALL old caches and take control immediately
self.addEventListener('activate', (event) => {
  console.log('SW: Activating v3, clearing old caches...')
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => {
          console.log('SW: Deleting old cache:', key)
          return caches.delete(key)
        })
      )
    }).then(() => {
      // Take control of all clients immediately
      return self.clients.claim()
    })
  )
})

// Fetch - network first, fallback to cache for static assets
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)

  // Don't cache API calls
  if (url.pathname.startsWith('/api') ||
      url.hostname !== location.hostname ||
      event.request.method !== 'GET') {
    return
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful responses
        if (response.ok) {
          const clone = response.clone()
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, clone)
          })
        }
        return response
      })
      .catch(() => {
        // Fallback to cache
        return caches.match(event.request)
      })
  )
})
