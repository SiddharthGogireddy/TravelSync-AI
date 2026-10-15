/**
 * TravelSync AI Service Worker (Step 81)
 *
 * Implements safe, privacy-preserving static caching for installable PWA.
 *
 * SECURITY & PRIVACY CONSTRAINTS (Requirement 3 & 9):
 * 1. ONLY safe static application assets are cached (HTML shell, styles, scripts, icons).
 * 2. NEVER caches private API responses, authenticated trip records, JWT tokens,
 *    invitations, group chat messages, private memories, or journal PDFs.
 * 3. NO background synchronization is registered, preventing silent state mutations
 *    or duplicate messaging.
 */

const CACHE_NAME = "travelsync-static-v2";

// Safe static shell assets to pre-cache on service worker installation
const STATIC_PRECACHE_URLS = [
  "/",
  "/index.html",
  "/offline.html",
  "/favicon.svg",
  "/manifest.webmanifest",
  "/pwa-192x192.png",
  "/pwa-512x512.png",
  "/maskable-icon-512x512.png",
];

// Patterns for dynamic API or authenticated data that MUST NEVER be stored in the cache
const SENSITIVE_PATH_PATTERNS = [
  /\/trip\//,
  /\/auth\//,
  /\/chat\//,
  /\/notifications\//,
  /\/memories\//,
  /\/journal\//,
  /\/planner\//,
  /\/invitation\//,
  /\/expense\//,
  /\/pdf\//,
  /\/place\//,
  /\/weather\//,
  /\/currency\//,
  /\/explanation\//,
  /token=/,
];

function isSensitiveOrApiRequest(request) {
  // Navigation requests for HTML documents are top-level SPA page loads, NOT API requests.
  if (request.mode === "navigate" || request.destination === "document") {
    return false;
  }

  // Non-GET requests should always bypass cache
  if (request.method !== "GET") {
    return true;
  }

  // Check for authenticated or sensitive header indicators
  const authHeader = request.headers.get("authorization") || request.headers.get("Authorization");
  const userHeader = request.headers.get("x-user-id") || request.headers.get("X-User-ID");
  if (authHeader || userHeader) {
    return true;
  }

  // Check URL against sensitive patterns
  for (const pattern of SENSITIVE_PATH_PATTERNS) {
    if (pattern.test(request.url)) {
      return true;
    }
  }

  return false;
}

// 1. Install event: pre-cache static application shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        return cache.addAll(STATIC_PRECACHE_URLS);
      })
      .then(() => {
        return self.skipWaiting();
      })
      .catch((err) => {
        console.warn("[ServiceWorker] Pre-cache installation warning:", err);
      })
  );
});

// 2. Activate event: clean up stale cache versions and claim clients
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((name) => {
            if (name !== CACHE_NAME) {
              return caches.delete(name);
            }
          })
        );
      })
      .then(() => {
        return self.clients.claim();
      })
  );
});

// 3. Fetch event: privacy-preserving cache routing
self.addEventListener("fetch", (event) => {
  const request = event.request;

  // 1. Navigation requests (e.g. loading or refreshing any SPA page route)
  // Always serve the static HTML application shell so React Router handles the route.
  // Never cache dynamic trip URLs to prevent leaking private data or stale auth state.
  if (request.mode === "navigate" || request.destination === "document") {
    event.respondWith(
      fetch(request).catch(async () => {
        // Offline fallback: serve cached app shell or offline fallback page
        const cachedShell = (await caches.match("/index.html")) || (await caches.match("/"));
        if (cachedShell) {
          return cachedShell;
        }
        const offlineFallback = await caches.match("/offline.html");
        if (offlineFallback) {
          return offlineFallback;
        }
        return new Response(
          "<!DOCTYPE html><html><body><h1>Offline</h1><p>Please connect to the internet.</p></body></html>",
          { status: 503, headers: { "Content-Type": "text/html" } }
        );
      })
    );
    return;
  }

  // 2. Direct bypass for API endpoints and sensitive data (network-only)
  if (isSensitiveOrApiRequest(request)) {
    event.respondWith(
      fetch(request).catch(() => {
        // Return 503 Service Unavailable when offline for API requests
        return new Response(
          JSON.stringify({
            detail: "Network connection unavailable. Live features require an active internet connection.",
            offline: true,
          }),
          {
            status: 503,
            statusText: "Service Unavailable (Offline)",
            headers: { "Content-Type": "application/json" },
          }
        );
      })
    );
    return;
  }

  // 3. Static assets (CSS, JS bundles, fonts, static public images): Stale-While-Revalidate
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      const fetchPromise = fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === "basic") {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // Fall back gracefully if offline and not in cache
          return cachedResponse;
        });

      return cachedResponse || fetchPromise;
    })
  );
});
