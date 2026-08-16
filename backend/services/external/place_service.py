import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENTRIPMAP_API_KEY")

BASE_URL = "https://api.opentripmap.com/0.1/en/places/radius"

async def get_places(lat, lon):
    params = {
        "radius": 50000,
        "lon": lon,
        "lat": lat,
        "apikey": API_KEY,
        "limit": 100,
        "format": "json",
        "kinds": "interesting_places"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            BASE_URL,
            params=params
        )
    data = response.json()
    print(f"Fetched {len(data)} places from OpenTripMap API.")
    return data