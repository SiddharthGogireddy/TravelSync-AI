import httpx

BASE_URL = "https://api.open-meteo.com/v1/forecast"

async def get_weather(lat: float, lon: float):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "weathercode"
        ],
        "forecast_days": 7,
        "timezone": "auto"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, params=params)

    return response.json()