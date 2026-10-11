import json
import logging
import os
import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("OPENTRIPMAP_API_KEY")

BASE_URL = "https://api.opentripmap.com/0.1/en/places/radius"
SEARCH_URL = "https://api.opentripmap.com/0.1/en/places/autosuggest"


async def _fetch_places_kind(client: httpx.AsyncClient, params: dict, kind_label: str) -> list:
    try:
        response = await client.get(BASE_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
            logger.warning(f"OpenTripMap {kind_label} returned non-list data: {type(data).__name__}")
            return []
        elif response.status_code == 429:
            logger.warning(f"OpenTripMap rate limit (HTTP 429) reached for {kind_label}")
            return []
        elif response.status_code == 401:
            logger.warning(f"OpenTripMap unauthorized (HTTP 401) for {kind_label}. Check OPENTRIPMAP_API_KEY.")
            return []
        else:
            logger.warning(f"OpenTripMap {kind_label} returned HTTP {response.status_code}")
            return []
    except httpx.TimeoutException:
        logger.warning(f"OpenTripMap request timed out for {kind_label}")
        return []
    except (httpx.RequestError, json.JSONDecodeError, Exception) as e:
        logger.warning(f"OpenTripMap request failed for {kind_label}: {e}")
        return []


async def get_places(lat, lon):
    if lat is None or lon is None:
        return []

    base_params = {
        "radius": 50000,
        "lon": lon,
        "lat": lat,
        "apikey": API_KEY or "",
        "limit": 100,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            attraction_params = {
                **base_params,
                "kinds": "interesting_places",
            }
            attractions = await _fetch_places_kind(client, attraction_params, "attractions")

            food_params = {
                **base_params,
                "kinds": "foods",
            }
            food_places = await _fetch_places_kind(client, food_params, "food")
    except Exception as e:
        logger.warning(f"OpenTripMap client session error: {e}")
        attractions = []
        food_places = []

    # Combine both results
    combined = attractions + food_places

    # Remove duplicate places
    unique_places = {}
    for place in combined:
        if isinstance(place, dict):
            place_id = place.get("xid")
            if place_id:
                unique_places[place_id] = place

    places = list(unique_places.values())
    return places


async def find_place(
    name,
    lat,
    lon,
):
    if not name or lat is None or lon is None:
        return None

    places = await get_places(
        lat,
        lon,
    )

    search_name = str(name).lower().strip()

    for place in places:
        if isinstance(place, dict):
            place_name = str(place.get("name") or "").lower().strip()
            if search_name in place_name:
                return place

    # Fallback: search by place name
    search_name_query = str(name).strip()

    if search_name_query.lower() == "golconda":
        search_name_query = "Golconda Fort"

    search_params = {
        "name": search_name_query,
        "radius": 50000,
        "lon": lon,
        "lat": lat,
        "apikey": API_KEY or "",
        "limit": 10,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                SEARCH_URL,
                params=search_params,
            )

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list):
                for candidate in result:
                    if not isinstance(candidate, dict):
                        continue
                    result_lat = candidate.get("point", {}).get("lat")
                    result_lon = candidate.get("point", {}).get("lon")

                    if result_lat is None or result_lon is None:
                        continue

                    try:
                        distance = (
                            (float(result_lat) - float(lat)) ** 2
                            + (float(result_lon) - float(lon)) ** 2
                        ) ** 0.5

                        if distance < 1.0:
                            return candidate
                    except (ValueError, TypeError):
                        continue
    except Exception as e:
        logger.warning(f"OpenTripMap find_place search error for '{name}': {e}")

    return None