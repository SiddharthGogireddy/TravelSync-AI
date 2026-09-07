from fastapi import APIRouter, Query

from backend.services.external.location_service import (
    search_location,
)

router = APIRouter(
    prefix="/locations",
    tags=["Locations"],
)


@router.get("/search")
async def location_search(
    q: str = Query(
        ...,
        min_length=2,
    ),
):
    locations = await search_location(q)

    if locations is None:
        return []

    return [locations]