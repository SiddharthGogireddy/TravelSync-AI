from fastapi import APIRouter
from services.external.location_service import search_location
from services.external.weather_service import get_weather

router = APIRouter(
    prefix="/weather",
    tags=["Weather"]
)

@router.get("/")
async def weather(place: str):
    result = await search_location(place)

    if not result:
        return {"message": "Location not found"}

    location = result

    weather = await get_weather(
        float(location["lat"]),
        float(location["lon"])
    )

    return weather