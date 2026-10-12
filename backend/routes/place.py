from fastapi import APIRouter, Query
from typing import Optional
from backend.services.external.location_service import search_location
from backend.services.external.place_service import get_places
from backend.services.external.place_detail_service import get_place_details

router = APIRouter(
    prefix="/places",
    tags=["Places"]
)

@router.get("/")
async def places(place: str):
    location = await search_location(place)

    if location is None:
        return {"error": "Location not found"}

    places = await get_places(
        float(location["lat"]),
        float(location["lon"])
    )

    results = []

    for p in places:
        if not p.get("name"):  # Skip unnamed places
            continue

        results.append({
            "name": p["name"],
            "category": p.get("kinds", "").split(",")[0].replace("_", " ").title(),
            "distance_km": round(p.get("dist", 0) / 1000, 2)
        })
    return results


@router.get("/details")
async def place_details_endpoint(
    name: str = Query(..., description="Name of the place, hotel, or attraction"),
    place_type: str = Query("attraction", description="Type: attraction, hotel, or dining"),
    category: Optional[str] = Query(None, description="Category of the place"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
):
    details = await get_place_details(
        name=name,
        place_type=place_type,
        category=category,
        lat=lat,
        lon=lon,
    )
    return {
        "success": True,
        "details": details,
    }