import httpx

BASE_URL = "https://nominatim.openstreetmap.org/search"

HEADERS = {
    "User-Agent": "TravelSyncAI/1.0"
}

async def search_location(place: str):
    params = {
        "q": place,
        "format": "json",
        "limit": 1
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            BASE_URL,
            params=params,
            headers=HEADERS
        )

    return response.json()