import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENTRIPMAP_API_KEY")

BASE_URL = "https://api.opentripmap.com/0.1/en/places/radius"


async def get_hotels(lat, lon):
    params = {
        "radius": 15000,
        "lon": lon,
        "lat": lat,
        "limit": 20,
        "format": "json",
        "apikey": API_KEY
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, params=params)



    data = response.json()

    return data