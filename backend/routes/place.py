from fastapi import APIRouter
from backend.services.external.location_service import search_location
from backend.services.external.place_service import get_places

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