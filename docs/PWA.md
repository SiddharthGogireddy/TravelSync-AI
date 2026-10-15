# TravelSync AI — Progressive Web App (PWA) Architecture & Deployment (Step 81)

TravelSync AI is an installable, responsive Progressive Web App designed to provide a native app experience across desktop (Chrome, Edge, Safari, Brave) and mobile platforms (iOS Safari, Android Chrome/Samsung Internet).

---

## 1. PWA Architecture Overview

```
TravelSync AI Frontend
│
├── Web App Manifest (public/manifest.webmanifest & public/manifest.json)
│   ├── Standalone display mode (hides browser address bar)
│   ├── Brand theme colors (#0284c7 / #f8fafc)
│   └── Multi-resolution icons (192x192, 512x512, 512x512 maskable)
│
├── Service Worker (public/sw.js)
│   ├── Pre-caches static application shell
│   ├── Stale-While-Revalidate for static script & style bundles
│   └── Network-only bypass for private APIs & sensitive trip data
│
├── Offline Fallback (public/offline.html)
│   ├── Clean offline notification
│   ├── Explicit list of features requiring active connectivity
│   └── Reconnection action button
│
└── In-App Offline Banner (src/components/OfflineBanner.tsx)
    ├── Real-time online/offline network detection
    └── One-click PWA installation prompt trigger
```

---

## 2. Privacy & Security Rules

To ensure user confidentiality and prevent cross-user data leakage on shared devices:

1. **Static Assets Only in Cache:**
   - Caching is restricted strictly to client shell files (`/index.html`, `/offline.html`, styles, JS chunks, icons).
2. **Absolute API & Data Bypass:**
   - The Service Worker intercepts and bypasses cache for all requests matching:
     - `/trip/` (trip itineraries, members, notes)
     - `/chat/` (group chat & attraction comments)
     - `/notifications/` (in-app notification state)
     - `/memories/` & `/journal/` (journal reflections & photo memories)
     - `/pdf/` (generated itinerary & journal PDFs)
     - `/auth/` (credentials, tokens, session claims)
     - Any request containing `Authorization` or `X-User-ID` headers or `?token=` query parameters.
3. **No Background Synchronization:**
   - Per security requirements, background sync handlers (`sync` and `periodicsync`) are deliberately omitted to prevent silent data mutations or duplicate chat messages while offline.

---

## 3. Offline Capabilities & Degraded Features

| Feature | Offline Availability | Reason / Fallback |
|---|---|---|
| **App Shell & UI Layout** | ✅ Available | Cached in CacheStorage via Service Worker |
| **Trip Itinerary (Already Loaded)** | ✅ Available | Cached in memory / React state during active session |
| **Offline Notification Banner** | ✅ Available | Informs user that network is disconnected |
| **Offline Fallback Page** | ✅ Available | Serves `/offline.html` if user navigates without connection |
| **AI Itinerary Planner** | ⚠️ Online Only | Requires LLM API processing |
| **Collaborative Group Chat** | ⚠️ Online Only | Requires real-time SQLite sync |
| **In-App Notifications** | ⚠️ Online Only | Requires backend notification store |
| **Journal Photo Uploads** | ⚠️ Online Only | Requires server validation and storage |
| **PDF Journal Export** | ⚠️ Online Only | Requires backend ReportLab compilation |
| **Weather & Currency Feeds** | ⚠️ Online Only | Requires live external API updates |

---

## 4. Mobile Layout & Touch Ergonomics

- **Safe Area Insets:** Configured with `viewport-fit=cover` and CSS safe-area padding:
  ```css
  padding-top: env(safe-area-inset-top, 0px);
  padding-bottom: env(safe-area-inset-bottom, 0px);
  ```
- **Accessible Touch Targets:** Minimum 44px height for interactive buttons, selects, and inputs on screens below 768px.
- **iOS Auto-Zoom Prevention:** Form inputs guarantee `font-size: 16px` on mobile screens to prevent mobile Safari viewport shifting.
- **Responsive Modals:** Modals adapt to `95vw` on mobile screens with touch-friendly dismiss buttons.
- **Horizontal Navigation:** Section navigation anchors support smooth horizontal touch panning (`-webkit-overflow-scrolling: touch;`).

---

## 5. HTTPS & Production Deployment Requirements

### Browser PWA Installation Criteria
Modern browsers (Chrome, Edge, Safari, Android) enforce strict security criteria before offering installation:

1. **Secure Context (HTTPS):**
   - Service Workers will **not** register over insecure HTTP connections.
   - In production, your domain must terminate TLS (HTTPS) using a valid certificate (e.g. Let's Encrypt, Cloudflare, or AWS ACM).
   - Local development is permitted exclusively over `http://localhost` or `http://127.0.0.1`.
2. **Web App Manifest:**
   - Must be linked in `<head>` via `<link rel="manifest" href="/manifest.webmanifest">`.
   - Served with MIME type `application/manifest+json` or `application/json`.
3. **Service Worker HTTP Headers (Recommended Nginx / Cloudflare Config):**
   ```nginx
   # Do NOT cache service worker script
   location /sw.js {
       add_header Cache-Control "no-cache, no-store, must-revalidate";
       add_header Service-Worker-Allowed "/";
   }

   # Manifest caching
   location ~* \.(webmanifest|json)$ {
       add_header Cache-Control "public, max-age=3600";
   }

   # Hashed production static assets
   location /assets/ {
       add_header Cache-Control "public, max-age=31536000, immutable";
   }
   ```
