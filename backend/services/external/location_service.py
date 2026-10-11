import logging
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://nominatim.openstreetmap.org/search"

HEADERS = {
    "User-Agent": "TravelSyncAI/1.0"
}


async def search_location(place: str):
    if not place or not isinstance(place, str) or not place.strip():
        return None

    params = {
        "q": place.strip(),
        "format": "json",
        "limit": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                BASE_URL,
                params=params,
                headers=HEADERS,
            )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                loc = data[0]
                if "lat" in loc and "lon" in loc:
                    return loc
            return None
        elif response.status_code == 429:
            logger.warning(f"Nominatim geocoding rate limit (HTTP 429) hit for '{place}'")
            return None
        else:
            logger.warning(f"Nominatim returned status HTTP {response.status_code} for '{place}'")
            return None
    except httpx.TimeoutException:
        logger.warning(f"Nominatim geocoding timed out for '{place}'")
        return None
    except Exception as e:
        logger.warning(f"Nominatim geocoding failed for '{place}': {e}")
        return None