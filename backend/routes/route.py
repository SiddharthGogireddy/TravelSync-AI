from fastapi import APIRouter
from services.external.location_service import search_location
from services.external.route_service import get_route as get_route_data

router = APIRouter(prefix="/route", tags=["Route"])

@router.get("/")
async def get_route(source: str, destination: str):
    # Convert source and destination to coordinates
    source_result = await search_location(source)
    destination_result = await search_location(destination)

    if not source_result or not destination_result:
        return {"message": "Location not found"}

    start = source_result[0]
    end = destination_result[0]

    # Get route from OSRM
    route_data = await get_route_data(
        start["lon"],
        start["lat"],
        end["lon"],
        end["lat"]
    )

    if "routes" not in route_data or not route_data["routes"]:
        return {"message": "No route found", "details": route_data}

    route = route_data["routes"]

    return {
        "source": source,
        "destination": destination,
        "distance_km": round(route["distance"] / 1000, 2),
        "duration_hours": round(route["duration"] / 3600, 2)   
    }