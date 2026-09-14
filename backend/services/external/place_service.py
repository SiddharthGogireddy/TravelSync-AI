import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENTRIPMAP_API_KEY")

BASE_URL = "https://api.opentripmap.com/0.1/en/places/radius"

async def get_places(lat, lon):
    base_params = {
        "radius": 50000,
        "lon": lon,
        "lat": lat,
        "apikey": API_KEY,
        "limit": 100,
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:

        # Main attractions
        attraction_params = {
            **base_params,
            "kinds": "interesting_places",
        }

        attraction_response = await client.get(
            BASE_URL,
            params=attraction_params
        )

        attraction_response.raise_for_status()
        attractions = attraction_response.json()

        # Food-related places
        food_params = {
            **base_params,
            "kinds": "foods",
        }

        food_response = await client.get(
            BASE_URL,
            params=food_params
        )

        food_response.raise_for_status()
        food_places = food_response.json()

    if not isinstance(attractions, list):
        attractions = []

    if not isinstance(food_places, list):
        food_places = []

    # Combine both results
    combined = attractions + food_places

    # Remove duplicate places
    unique_places = {}
    for place in combined:
        place_id = place.get("xid")

        if place_id:
            unique_places[place_id] = place

    places = list(unique_places.values())

    print(
        f"Fetched {len(attractions)} attractions + "
        f"{len(food_places)} food places = "
        f"{len(places)} unique places."
    )

    return places
async def find_place(
    name,
    lat,
    lon,
):
    places = await get_places(
        lat,
        lon,
    )

    search_name = name.lower().strip()

    for place in places:

        place_name = place.get(
            "name",
            ""
        ).lower().strip()

        if search_name == place_name:
            return place

    for place in places:

        place_name = place.get(
            "name",
            ""
        ).lower().strip()

        if search_name in place_name:
            return place

    return None