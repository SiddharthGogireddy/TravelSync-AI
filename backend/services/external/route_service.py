import math
import httpx

BASE_URL = "https://router.project-osrm.org/route/v1/driving"


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1.25  # account for road curvature


async def get_route(start_lon, start_lat, end_lon, end_lat):
    url = f"{BASE_URL}/{start_lon},{start_lat};{end_lon},{end_lat}"

    params = {
        "overview": "full",
        "geometries": "geojson"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if "routes" in data and len(data["routes"]) > 0:
                return data
    except Exception:
        pass

    est_km = _haversine_distance(float(start_lat), float(start_lon), float(end_lat), float(end_lon))
    return {
        "routes": [
            {
                "distance": est_km * 1000,
                "duration": (est_km / 60.0) * 3600,
                "geometry": {
                    "coordinates": [
                        [float(start_lon), float(start_lat)],
                        [float(end_lon), float(end_lat)],
                    ]
                },
            }
        ]
    }