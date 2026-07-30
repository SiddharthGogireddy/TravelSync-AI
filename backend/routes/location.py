from fastapi import APIRouter
from services.external.place_service import get_places
from services.external.location_service import search_location

router = APIRouter(
    prefix="/location",
    tags=["Location"]
)

@router.get("/search")
async def get_location(place: str):
    result = await search_location(place)

    if not result:
        return {"error": "Location not found"}

    location = result

    places = await get_places(
        float(location["lat"]),
        float(location["lon"])
    )
    return result