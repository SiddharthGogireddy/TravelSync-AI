import httpx

BASE_URL = "https://router.project-osrm.org/route/v1/driving"

async def get_route(start_lon, start_lat, end_lon, end_lat):
    url = f"{BASE_URL}/{start_lon},{start_lat};{end_lon},{end_lat}"

    params = {
        "overview": "full",
        "geometries": "geojson"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    return response.json()