import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

# Base URL can be overridden via environment variable for self-hosted Nominatim or proxy
BASE_URL = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org/search")

HEADERS = {
    "User-Agent": "TravelSyncAI/1.0 (https://travelsync.ai; contact@travelsync.ai)"
}

# --- Cache Configuration ---
CACHE_TTL_SECONDS = 3600  # 1 hour cache TTL for geocoding results
MAX_CACHE_SIZE = 1000
_location_cache: Dict[str, tuple[float, Any]] = {}

# --- Rate Limiter Configuration ---
# Nominatim Usage Policy permits at most 1 request per second to public endpoints.
# NOTE ON MULTI-INSTANCE DEPLOYMENTS:
# The in-process lock below guarantees <= 1 request/second for this Python process.
# When running multiple horizontal application instances sharing the public Nominatim endpoint,
# an external distributed rate limiter (e.g. Redis token bucket) or a self-hosted Nominatim / proxy
# instance MUST be used by configuring the NOMINATIM_BASE_URL environment variable.
MIN_REQUEST_INTERVAL_SECONDS = 1.05
_rate_limit_lock = asyncio.Lock()
_last_request_timestamp = 0.0


def clear_location_cache() -> None:
    """Helper to clear in-memory cache, primarily used in testing."""
    _location_cache.clear()


def reset_rate_limiter() -> None:
    """Helper to reset rate limiter timestamp, primarily used in testing."""
    global _last_request_timestamp
    _last_request_timestamp = 0.0


def _get_from_cache(cache_key: str) -> Optional[Any]:
    now = time.monotonic()
    if cache_key in _location_cache:
        expiry, data = _location_cache[cache_key]
        if now < expiry:
            return data
        else:
            del _location_cache[cache_key]
    return None


def _set_cache(cache_key: str, data: Any) -> None:
    now = time.monotonic()
    if len(_location_cache) >= MAX_CACHE_SIZE:
        # Evict expired or oldest entries
        expired_keys = [k for k, (exp, _) in _location_cache.items() if now >= exp]
        if expired_keys:
            for k in expired_keys:
                del _location_cache[k]
        else:
            # Evict first 10% of items
            keys_to_remove = list(_location_cache.keys())[: MAX_CACHE_SIZE // 10]
            for k in keys_to_remove:
                del _location_cache[k]

    _location_cache[cache_key] = (now + CACHE_TTL_SECONDS, data)


async def _execute_nominatim_request(params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Execute a rate-limited HTTP GET request to Nominatim with retries/timeouts."""
    global _last_request_timestamp

    async with _rate_limit_lock:
        now = time.monotonic()
        elapsed = now - _last_request_timestamp
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            await asyncio.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)
        _last_request_timestamp = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    BASE_URL,
                    params=params,
                    headers=HEADERS,
                )

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                return []
            elif response.status_code == 429:
                logger.warning(
                    "Nominatim geocoding rate limit (HTTP 429) hit for params %s", params
                )
                return None
            else:
                logger.warning(
                    "Nominatim returned status HTTP %s for params %s",
                    response.status_code,
                    params,
                )
                return None
        except httpx.TimeoutException:
            logger.warning("Nominatim geocoding timed out for params %s", params)
            return None
        except Exception as e:
            logger.warning("Nominatim geocoding request failed: %s", e)
            return None


def _normalize_location_item(loc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize raw Nominatim geocoding result into application contract."""
    if not isinstance(loc, dict):
        return None

    try:
        lat = float(loc.get("lat", 0))
        lon = float(loc.get("lon", 0))
    except (ValueError, TypeError):
        return None

    # Skip invalid zero coordinates unless explicitly intended
    if lat == 0 and lon == 0 and "lat" not in loc:
        return None

    address = loc.get("address", {}) if isinstance(loc.get("address"), dict) else {}

    # Extract clean display fields
    display_name = str(loc.get("display_name", "")).strip()
    name = str(loc.get("name", "")).strip()
    if not name and display_name:
        name = display_name.split(",")[0].strip()

    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("hamlet")
        or address.get("suburb")
    )
    region = (
        address.get("state")
        or address.get("region")
        or address.get("state_district")
        or address.get("province")
        or address.get("county")
    )
    country = address.get("country")
    country_code = str(address.get("country_code", "")).upper()

    category = loc.get("category") or loc.get("class")
    place_type = loc.get("type") or loc.get("addresstype")

    return {
        "place_id": str(loc.get("place_id", "")),
        "display_name": display_name,
        "name": name,
        "latitude": lat,
        "longitude": lon,
        "city": city,
        "region": region,
        "country": country,
        "country_code": country_code,
        "category": category,
        "type": place_type,
    }


async def search_locations(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    """Search for locations worldwide with autocomplete normalization, caching, and rate limiting."""
    if not query or not isinstance(query, str) or len(query.strip()) < 2:
        return []

    cleaned = query.strip()
    safe_limit = max(1, min(limit, 10))
    cache_key = f"multi:{cleaned.lower()}:{safe_limit}"

    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    params = {
        "q": cleaned,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": safe_limit,
        "accept-language": "en",
    }

    raw_results = await _execute_nominatim_request(params)
    if raw_results is None:
        return []

    normalized_list = []
    for item in raw_results:
        norm = _normalize_location_item(item)
        if norm:
            normalized_list.append(norm)

    # Cache successful results
    _set_cache(cache_key, normalized_list)
    return normalized_list


async def search_location(place: str) -> Optional[Dict[str, Any]]:
    """Preserve existing search_location() signature and raw return contract for downstream planner services."""
    if not place or not isinstance(place, str) or not place.strip():
        return None

    cleaned = place.strip()
    cache_key = f"single:{cleaned.lower()}"

    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    params = {
        "q": cleaned,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }

    raw_results = await _execute_nominatim_request(params)
    if raw_results and len(raw_results) > 0 and isinstance(raw_results[0], dict):
        loc = raw_results[0]
        if "lat" in loc and "lon" in loc:
            _set_cache(cache_key, loc)
            return loc

    return None