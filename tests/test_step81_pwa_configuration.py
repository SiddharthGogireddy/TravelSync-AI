import json
import os
import sys
import re
from pathlib import Path
from PIL import Image

sys.path.insert(0, os.path.abspath("."))

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
PUBLIC_DIR = FRONTEND_DIR / "public"
DIST_DIR = FRONTEND_DIR / "dist"


def test_manifest_webmanifest_validity():
    """Validates manifest.webmanifest structure, required PWA fields, and standalone mode."""
    manifest_path = PUBLIC_DIR / "manifest.webmanifest"
    assert manifest_path.exists(), "manifest.webmanifest must exist in frontend/public"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Core required manifest attributes for an installable PWA
    assert manifest.get("name") and len(manifest["name"]) > 3
    assert manifest.get("short_name") and len(manifest["short_name"]) > 2
    assert manifest.get("start_url") == "/"
    assert manifest.get("display") == "standalone", "PWA display mode must be standalone"
    assert manifest.get("theme_color")
    assert manifest.get("background_color")

    # Icons validation
    icons = manifest.get("icons", [])
    assert len(icons) >= 3, "Manifest must specify multiple icon sizes and purposes"

    sizes = [icon.get("sizes") for icon in icons]
    assert "192x192" in sizes, "Must include 192x192 icon"
    assert "512x512" in sizes, "Must include 512x512 icon"

    purposes = [icon.get("purpose") for icon in icons if icon.get("purpose")]
    assert "maskable" in purposes, "Must include maskable icon for Android adaptive icons"


def test_icon_files_exist_and_dimensions_valid():
    """Verifies icon files exist on disk and have exact required pixel dimensions."""
    icon_192 = PUBLIC_DIR / "pwa-192x192.png"
    icon_512 = PUBLIC_DIR / "pwa-512x512.png"
    icon_maskable = PUBLIC_DIR / "maskable-icon-512x512.png"

    assert icon_192.exists(), "pwa-192x192.png must exist"
    assert icon_512.exists(), "pwa-512x512.png must exist"
    assert icon_maskable.exists(), "maskable-icon-512x512.png must exist"

    with Image.open(icon_192) as img:
        assert img.size == (192, 192), f"Expected 192x192, got {img.size}"
        assert img.format == "PNG"

    with Image.open(icon_512) as img:
        assert img.size == (512, 512), f"Expected 512x512, got {img.size}"
        assert img.format == "PNG"

    with Image.open(icon_maskable) as img:
        assert img.size == (512, 512), f"Expected 512x512 for maskable, got {img.size}"
        assert img.format == "PNG"


def test_service_worker_privacy_and_security_rules():
    """Service worker must cache only safe static assets and strictly exclude private APIs & trip data."""
    sw_path = PUBLIC_DIR / "sw.js"
    assert sw_path.exists(), "sw.js must exist in frontend/public"

    with open(sw_path, "r", encoding="utf-8") as f:
        sw_code = f.read()

    # 1. Must define static cache name
    assert "travelsync-static" in sw_code or "CACHE_NAME" in sw_code

    # 2. Must forbid caching of sensitive endpoints
    assert "SENSITIVE_PATH_PATTERNS" in sw_code or "trip" in sw_code
    assert "chat" in sw_code
    assert "notifications" in sw_code
    assert "memories" in sw_code or "journal" in sw_code
    assert "pdf" in sw_code

    # 3. Must check authorization headers
    assert "authorization" in sw_code.lower()
    assert "x-user-id" in sw_code.lower()

    # 4. Requirement 9: No silent mutating background sync
    assert "sync" not in sw_code or "backgroundSync" not in sw_code
    assert "periodicSync" not in sw_code
    # Ensure no 'sync' event listener is added
    assert not re.search(r'addEventListener\(\s*["\']sync["\']', sw_code), "Must not register background sync"


def test_offline_fallback_html_validity():
    """Verifies the offline fallback page explains required online features."""
    offline_path = PUBLIC_DIR / "offline.html"
    assert offline_path.exists(), "offline.html must exist in frontend/public"

    with open(offline_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Explains offline state clearly
    assert "Offline" in html or "offline" in html.lower()

    # Explains online features requiring connection
    assert "AI Itinerary" in html or "AI" in html
    assert "Chat" in html or "chat" in html.lower()
    assert "Notification" in html or "notification" in html.lower()
    assert "Upload" in html or "upload" in html.lower()

    # Action to reconnect / reload
    assert "reload" in html or "Reconnecting" in html or "Reconnect" in html


def test_index_html_pwa_meta_tags():
    """Verifies index.html has viewport-fit=cover, theme-color, and manifest links."""
    index_path = FRONTEND_DIR / "index.html"
    assert index_path.exists()

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'rel="manifest"' in content
    assert 'manifest.webmanifest' in content
    assert 'viewport-fit=cover' in content
    assert 'theme-color' in content
    assert 'apple-mobile-web-app-capable' in content
    assert 'rel="apple-touch-icon"' in content


def test_production_build_pwa_assets_present():
    """Verifies production build output in dist/ includes all required PWA assets."""
    assert (DIST_DIR / "manifest.webmanifest").exists()
    assert (DIST_DIR / "sw.js").exists()
    assert (DIST_DIR / "offline.html").exists()
    assert (DIST_DIR / "pwa-192x192.png").exists()
    assert (DIST_DIR / "pwa-512x512.png").exists()


def test_service_worker_navigation_never_blocked_as_api_or_cached_dynamically():
    """Verifies that navigation requests (SPA page routes) are excluded from API checks and not cached per trip."""
    sw_path = PUBLIC_DIR / "sw.js"
    with open(sw_path, "r", encoding="utf-8") as f:
        sw_code = f.read()

    # Must distinguish navigation requests from API requests
    assert 'request.mode === "navigate"' in sw_code
    assert 'request.destination === "document"' in sw_code

    # Must not store dynamic trip URLs in cache under the dynamic request URL
    # Look at the navigation handler: it must not call cache.put(request, ...)
    nav_match = re.search(r'if\s*\(\s*request\.mode\s*===\s*["\']navigate["\'].*?\)\s*\{(.*?)\}', sw_code, re.DOTALL)
    assert nav_match, "Must have an explicit navigation handler"
    nav_body = nav_match.group(1)
    assert "cache.put(request" not in nav_body, "Navigation handler must not cache dynamic trip URLs"


def test_vite_proxy_bypasses_html_navigation():
    """Verifies that Vite dev proxy rules for /trip, /trips, and /auth bypass HTML document navigations."""
    vite_config_path = FRONTEND_DIR / "vite.config.ts"
    with open(vite_config_path, "r", encoding="utf-8") as f:
        config_code = f.read()

    assert "bypass" in config_code
    assert "text/html" in config_code
    assert "req.url" in config_code

