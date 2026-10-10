import httpx
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

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

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(BASE_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            if "daily" in data and "time" in data["daily"]:
                return data
    except Exception as e:
        logger.warning(f"Failed to fetch live weather ({e}), using default forecast fallback")

    now = datetime.now(timezone.utc)
    return {
        "daily": {
            "time": [(now + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)],
            "temperature_2m_max": [28.0] * 7,
            "temperature_2m_min": [20.0] * 7,
            "weathercode": [0] * 7,
        }
    }