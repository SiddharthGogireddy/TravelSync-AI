from fastapi import APIRouter
from services.location_service import search_location

router = APIRouter(
    prefix="/location",
    tags=["Location"]
)

@router.get("/search")
async def get_location(place: str):
    result = await search_location(place)

    if not result:
        return {"message": "Location not found"}

    return result[0]