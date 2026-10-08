from fastapi import APIRouter
from backend.models.trip import TripRequest
from backend.services.gemini_service import generate
from backend.services.planner.itinerary import build_trip

router = APIRouter(
    prefix="/planner",
    tags=["Trip Planner"]
)


@router.post("/")
async def planner(request: TripRequest):

    result = await build_trip(request)
    if not isinstance(result, dict) or "trip" not in result:
        return result

    trip_info = result["trip"]
    destination_title = trip_info.get("destination", request.destination)
    trip_days = trip_info.get("days", request.days)

    place_names = [
        p["name"]
        for p in trip_info.get("places", [])[:10]
    ]

    hotel_names = [
        h["name"]
        for h in trip_info.get("hotels", [])[:5]
    ]

    prompt = f"""
Generate a {trip_days}-day travel itinerary.

Source: {request.source}

Destination: {destination_title}

Travel mode: {request.travel_mode}


Traveler interests:

{[t.interests for t in request.travelers]}

Recommended attractions:

{place_names}

Recommended hotels:

{hotel_names}

Return ONLY valid JSON.

Format:

{{
    "days": [
        {{
            "day": 1,
            "title": "",
            "activities": [],
            "food": [],
            "budget": ""
        }}
    ]
}}
"""

    try:
        itinerary = generate(prompt)

    except Exception as e:
        print("Gemini error:", e)

        itinerary = {
            "days": []
        }

    result["itinerary"] = itinerary

    return result